from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path
from typing import Any, Mapping, Sequence


LIGAND_PREP_VERSION = "2026-07-12"
LIGAND_OUTPUT_DIR = "data/compounds/pdbqt"
EMBED_SEED = 42

# Ligands are docked as their dominant microspecies at physiological pH, not as the
# neutral PubChem depiction. The custom set is dominated by amidines and guanidines
# (pKa ~11.6-13.6), which are cations at pH 7.4; the S1 salt bridge is the entire
# binding rationale for that chemotype, so docking them neutral removes the
# interaction the study is meant to test.
PHYSIOLOGICAL_PH = 7.4


class LigandPreparationError(RuntimeError):
    """Raised when a ligand cannot be embedded or converted to PDBQT."""


def _largest_fragment(mol):
    """Return the largest fragment by heavy-atom count, stripping salts/counterions."""
    from rdkit import Chem

    fragments = Chem.GetMolFrags(mol, asMols=True, sanitizeFrags=True)
    if len(fragments) <= 1:
        return mol
    return max(fragments, key=lambda fragment: fragment.GetNumHeavyAtoms())


def protonate_at_ph(smiles: str, *, ph: float = PHYSIOLOGICAL_PH) -> str:
    """Return the dominant microspecies of `smiles` at `ph` as canonical SMILES."""
    from spycep_drug_discovery.protonation import PROTONATION_PH, protonate

    if ph != PROTONATION_PH:
        raise LigandPreparationError(
            f"The protonation rule set is defined at pH {PROTONATION_PH}, not {ph}."
        )
    try:
        return protonate(smiles)
    except ValueError as exc:
        raise LigandPreparationError(str(exc)) from exc


def docked_species_smiles(smiles: str, *, ph: float = PHYSIOLOGICAL_PH) -> str:
    """Desalt then protonate: the exact species that gets embedded and docked."""
    from rdkit import Chem

    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise LigandPreparationError(f"RDKit could not parse SMILES: {smiles!r}")
    desalted = Chem.MolToSmiles(_largest_fragment(mol))
    return protonate_at_ph(desalted, ph=ph)


def undefined_stereocenters(smiles: str) -> list[int]:
    """Atom indices of stereocenters the input SMILES leaves unspecified.

    ETKDG assigns these arbitrarily, so the docked molecule is one arbitrary
    diastereomer. Reporting them keeps that visible instead of silent.
    """
    from rdkit import Chem

    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise LigandPreparationError(f"RDKit could not parse SMILES: {smiles!r}")
    centers = Chem.FindMolChiralCenters(mol, includeUnassigned=True, useLegacyImplementation=False)
    return [index for index, label in centers if label == "?"]


def smiles_to_sdf(
    smiles: str,
    out_sdf: Path,
    *,
    seed: int = EMBED_SEED,
    ph: float = PHYSIOLOGICAL_PH,
) -> dict[str, Any]:
    """Desalt, protonate at `ph`, embed one deterministic 3D conformer, write SDF.

    Returns a record of what was actually embedded, including the post-embedding
    isomeric SMILES (which pins any stereocentre ETKDG had to assign itself).
    """
    from rdkit import Chem
    from rdkit.Chem import AllChem

    species = docked_species_smiles(smiles, ph=ph)
    mol = Chem.MolFromSmiles(species)
    if mol is None:
        raise LigandPreparationError(f"RDKit could not parse protonated SMILES: {species!r}")

    mol = Chem.AddHs(mol)
    params = AllChem.ETKDGv3()
    params.randomSeed = seed
    if AllChem.EmbedMolecule(mol, params) != 0:
        raise LigandPreparationError(f"RDKit could not embed a 3D conformer for SMILES: {species!r}")

    # -1 means MMFF could not be parameterised and no optimisation ran at all; 1 means
    # it ran but did not converge. Both previously passed silently as "prepared".
    mmff_status = AllChem.MMFFOptimizeMolecule(mol)
    if mmff_status == -1:
        raise LigandPreparationError(
            f"MMFF94 has no parameters for {species!r}; geometry would be an unoptimised "
            "ETKDG embedding. Refusing to emit it as a prepared ligand."
        )

    out_sdf.parent.mkdir(parents=True, exist_ok=True)
    writer = Chem.SDWriter(str(out_sdf))
    writer.write(mol)
    writer.close()

    embedded = Chem.RemoveHs(Chem.Mol(mol))
    return {
        "input_smiles": smiles,
        "docked_smiles": species,
        "embedded_isomeric_smiles": Chem.MolToSmiles(embedded),
        "protonation_ph": ph,
        "formal_charge": Chem.GetFormalCharge(embedded),
        "undefined_stereocenter_count": len(undefined_stereocenters(species)),
        "mmff_converged": mmff_status == 0,
        "sdf_atom_count": mol.GetNumAtoms(),
        "heavy_atom_count": embedded.GetNumHeavyAtoms(),
        "embed_seed": seed,
    }


def heavy_atom_count(smiles: str, *, ph: float = PHYSIOLOGICAL_PH) -> int:
    """Heavy atoms of the docked species. Protonation adds hydrogens only, so this
    equals the desalted heavy-atom count; it is computed on the docked species so the
    ligand-efficiency denominator can never drift from what was docked."""
    from rdkit import Chem

    mol = Chem.MolFromSmiles(docked_species_smiles(smiles, ph=ph))
    if mol is None:
        raise LigandPreparationError(f"RDKit could not parse SMILES: {smiles!r}")
    return mol.GetNumHeavyAtoms()


def prepare_ligand(
    compound: Mapping[str, Any],
    *,
    project_root: Path,
    work_dir: Path,
    output_dir: Path,
    meeko_command: Sequence[str | Path],
    seed: int = EMBED_SEED,
    ph: float = PHYSIOLOGICAL_PH,
) -> dict[str, Any]:
    ligand_id = str(compound["ligand_id"])
    work_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    sdf_path = work_dir / f"{ligand_id}.sdf"
    pdbqt_path = output_dir / f"{ligand_id}.pdbqt"

    embedding = smiles_to_sdf(str(compound["smiles"]), sdf_path, seed=seed, ph=ph)

    # Remove any previous output first: otherwise a converter that exits 0 without
    # writing leaves a stale PDBQT that gets hashed and recorded as this run's output.
    pdbqt_path.unlink(missing_ok=True)

    command = [str(part) for part in meeko_command] + ["-i", str(sdf_path), "-o", str(pdbqt_path)]
    completed = subprocess.run(command, cwd=project_root, capture_output=True, text=True, check=False)
    if completed.returncode != 0 or not pdbqt_path.is_file():
        raise LigandPreparationError(
            f"{ligand_id} ligand PDBQT preparation failed "
            f"(exit {completed.returncode}): {_tail(completed.stderr) or _tail(completed.stdout)}"
        )
    return {
        "ligand_id": ligand_id,
        "smiles": compound["smiles"],
        "role": compound.get("role"),
        "set": compound.get("set"),
        **embedding,
        "pdbqt_path": _relative_path(pdbqt_path, project_root),
        "pdbqt_sha256": _sha256(pdbqt_path),
        "pdbqt_atom_records": _count_atom_records(pdbqt_path),
    }


def prepare_ligands(
    compounds: Sequence[Mapping[str, Any]],
    *,
    project_root: Path,
    work_dir: Path,
    output_dir: Path,
    meeko_command: Sequence[str | Path],
    seed: int = EMBED_SEED,
    ph: float = PHYSIOLOGICAL_PH,
) -> dict[str, Any]:
    ligands = [
        prepare_ligand(
            compound,
            project_root=project_root,
            work_dir=work_dir,
            output_dir=output_dir,
            meeko_command=meeko_command,
            seed=seed,
            ph=ph,
        )
        for compound in compounds
    ]
    return {
        "ligand_prep_version": LIGAND_PREP_VERSION,
        "embed_seed": seed,
        "protonation_ph": ph,
        "protonation_tool": "explicit pKa rule set (spycep_drug_discovery.protonation)",
        "tool": "meeko mk_prepare_ligand",
        "ligands": ligands,
    }


def _count_atom_records(path: Path) -> int:
    with path.open(encoding="utf-8") as handle:
        return sum(1 for line in handle if line.startswith(("ATOM", "HETATM")))


def _tail(text: str, line_count: int = 15) -> str:
    return "\n".join(text.splitlines()[-line_count:])


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _relative_path(path: Path, project_root: Path) -> str:
    try:
        return path.resolve().relative_to(project_root.resolve()).as_posix()
    except ValueError:
        return str(path)

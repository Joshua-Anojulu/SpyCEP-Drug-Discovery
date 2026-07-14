from __future__ import annotations

import hashlib
import re
import subprocess
from pathlib import Path
from typing import Any, Mapping, Sequence


LIGAND_PREP_VERSION = "2026-07-13-stage1"
LIGAND_OUTPUT_DIR = "data/compounds/pdbqt"
EMBED_SEED = 42
MMFF_VARIANT = "MMFF94s"
MMFF_MAX_ITERATIONS = 2000

# Ligands are docked as their audited physiological-pH species.  Ambiguous states are
# supplied verbatim by the catalog and therefore cannot be reconstructed from a SMILES
# string after compound identity has been discarded.
PHYSIOLOGICAL_PH = 7.4


class LigandPreparationError(RuntimeError):
    """Raised when a ligand cannot be embedded, optimised, or converted to PDBQT."""


def _largest_fragment(mol):
    """Return the largest fragment by heavy-atom count, stripping salts/counterions."""
    from rdkit import Chem

    fragments = Chem.GetMolFrags(mol, asMols=True, sanitizeFrags=True)
    if len(fragments) <= 1:
        return mol
    return max(fragments, key=lambda fragment: fragment.GetNumHeavyAtoms())


def protonate_at_ph(smiles: str, *, ph: float = PHYSIOLOGICAL_PH) -> str:
    """Return the generic-rule microspecies of `smiles` at `ph`."""
    from spycep_drug_discovery.protonation import PROTONATION_PH, protonate

    if ph != PROTONATION_PH:
        raise LigandPreparationError(
            f"The protonation rule set is defined at pH {PROTONATION_PH}, not {ph}."
        )
    try:
        return protonate(smiles)
    except ValueError as exc:
        raise LigandPreparationError(str(exc)) from exc


def docked_species_smiles(
    smiles: str,
    *,
    entity_id: str | None = None,
    state_id: str | None = None,
    species_catalog: Mapping[str, Any] | None = None,
    ph: float = PHYSIOLOGICAL_PH,
) -> str:
    """Return the exact catalog state (or legacy generic-rule state) to be docked.

    A catalog lookup requires both identity components.  AMBIGUOUS rows are consumed
    verbatim; no protonation rule or tautomer normalisation is applied here.
    """
    from rdkit import Chem

    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise LigandPreparationError(f"RDKit could not parse SMILES: {smiles!r}")
    desalted = Chem.MolToSmiles(_largest_fragment(mol), canonical=True, isomericSmiles=True)

    if species_catalog is None:
        if (entity_id is None) != (state_id is None):
            raise LigandPreparationError("entity_id and state_id must be supplied together.")
        return protonate_at_ph(desalted, ph=ph)

    if not entity_id or not state_id:
        raise LigandPreparationError(
            "Catalog-backed preparation requires both entity_id and state_id."
        )
    from spycep_drug_discovery.species import (
        SpeciesCatalogError,
        catalog_state,
        unmapped_canonical_smiles,
    )

    try:
        row = catalog_state(species_catalog, entity_id, state_id)
        catalog_source_mol = Chem.MolFromSmiles(str(row["source_smiles"]))
        if catalog_source_mol is None:
            raise LigandPreparationError(
                f"Catalog source SMILES does not parse for ({entity_id}, {state_id})."
            )
        catalog_source = unmapped_canonical_smiles(
            Chem.MolToSmiles(
                _largest_fragment(catalog_source_mol),
                canonical=True,
                isomericSmiles=True,
            )
        )
        actual_source = unmapped_canonical_smiles(desalted)
        if actual_source != catalog_source:
            raise LigandPreparationError(
                f"Source SMILES mismatch for ({entity_id}, {state_id}); refusing to "
                "apply a state to a different molecule."
            )
        return unmapped_canonical_smiles(str(row["atom_mapped_canonical_smiles"]))
    except SpeciesCatalogError as exc:
        raise LigandPreparationError(str(exc)) from exc


def undefined_stereocenters(smiles: str) -> list[int]:
    """Atom indices of stereocenters a SMILES representation leaves unspecified."""
    from rdkit import Chem

    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise LigandPreparationError(f"RDKit could not parse SMILES: {smiles!r}")
    centers = Chem.FindMolChiralCenters(
        mol,
        includeUnassigned=True,
        useLegacyImplementation=False,
    )
    return [index for index, label in centers if label == "?"]


def smiles_to_sdf(
    smiles: str,
    out_sdf: Path,
    *,
    entity_id: str | None = None,
    state_id: str | None = None,
    species_catalog: Mapping[str, Any] | None = None,
    seed: int = EMBED_SEED,
    ph: float = PHYSIOLOGICAL_PH,
    mmff_variant: str = MMFF_VARIANT,
    mmff_max_iterations: int = MMFF_MAX_ITERATIONS,
) -> dict[str, Any]:
    """Resolve one species, embed it, require MMFF94s convergence, and write SDF."""
    from rdkit import Chem
    from rdkit.Chem import AllChem

    if mmff_variant != MMFF_VARIANT:
        raise LigandPreparationError(
            f"MMFF variant is frozen at {MMFF_VARIANT}, not {mmff_variant!r}."
        )
    if mmff_max_iterations != MMFF_MAX_ITERATIONS:
        raise LigandPreparationError(
            f"MMFF iteration cap is frozen at {MMFF_MAX_ITERATIONS}, "
            f"not {mmff_max_iterations}."
        )

    species = docked_species_smiles(
        smiles,
        entity_id=entity_id,
        state_id=state_id,
        species_catalog=species_catalog,
        ph=ph,
    )
    # Preserve source-depiction evidence before canonicalisation/3-D assignment.
    source_undefined = undefined_stereocenters(smiles)
    mol = Chem.MolFromSmiles(species)
    if mol is None:
        raise LigandPreparationError(f"RDKit could not parse docked SMILES: {species!r}")

    mol = Chem.AddHs(mol)
    params = AllChem.ETKDGv3()
    params.randomSeed = seed
    if AllChem.EmbedMolecule(mol, params) != 0:
        raise LigandPreparationError(
            f"RDKit could not embed a 3D conformer for ({entity_id}, {state_id}): "
            f"{species!r}"
        )

    mmff_status = AllChem.MMFFOptimizeMolecule(
        mol,
        mmffVariant=mmff_variant,
        maxIters=mmff_max_iterations,
    )
    if mmff_status == -1:
        raise LigandPreparationError(
            f"{mmff_variant} has no parameters for ({entity_id}, {state_id}) "
            f"{species!r}; refusing to emit an unoptimised ETKDG embedding."
        )
    if mmff_status != 0:
        raise LigandPreparationError(
            f"{mmff_variant} did not converge for ({entity_id}, {state_id}) within "
            f"the hard cap of {mmff_max_iterations} iterations."
        )

    # Pin the arbitrary stereoisomer selected during 3-D embedding, but retain the
    # pre-embedding undefined-center inventory separately as methodological evidence.
    Chem.AssignAtomChiralTagsFromStructure(mol, confId=0, replaceExistingTags=True)
    Chem.AssignStereochemistryFrom3D(mol, confId=0, replaceExistingTags=True)
    embedded = Chem.RemoveHs(Chem.Mol(mol))
    Chem.AssignStereochemistry(embedded, cleanIt=True, force=True)
    embedded_smiles = Chem.MolToSmiles(
        embedded,
        canonical=True,
        isomericSmiles=True,
    )
    embedded_unassigned = undefined_stereocenters(embedded_smiles)
    if embedded_unassigned:
        raise LigandPreparationError(
            f"Embedded species ({entity_id}, {state_id}) still has unassigned "
            f"stereocenters: {embedded_unassigned}."
        )

    out_sdf.parent.mkdir(parents=True, exist_ok=True)
    writer = Chem.SDWriter(str(out_sdf))
    writer.write(mol)
    writer.close()

    return {
        "entity_id": entity_id,
        "state_id": state_id,
        "species_key": [entity_id, state_id] if entity_id and state_id else None,
        "input_smiles": smiles,
        "docked_smiles": species,
        "embedded_isomeric_smiles": embedded_smiles,
        "protonation_ph": ph,
        "formal_charge": Chem.GetFormalCharge(embedded),
        "source_undefined_centers": source_undefined,
        "embedded_unassigned_centers": embedded_unassigned,
        # Compatibility count, explicitly tied to the source rather than the embedded
        # representation so the prior 13-compound limitation cannot disappear.
        "undefined_stereocenter_count": len(source_undefined),
        "mmff_variant": mmff_variant,
        "mmff_max_iterations": mmff_max_iterations,
        "mmff_status": mmff_status,
        "mmff_converged": True,
        "sdf_atom_count": mol.GetNumAtoms(),
        "heavy_atom_count": embedded.GetNumHeavyAtoms(),
        "embed_seed": seed,
    }


def heavy_atom_count(
    smiles: str,
    *,
    entity_id: str | None = None,
    state_id: str | None = None,
    species_catalog: Mapping[str, Any] | None = None,
    ph: float = PHYSIOLOGICAL_PH,
) -> int:
    from rdkit import Chem

    species = docked_species_smiles(
        smiles,
        entity_id=entity_id,
        state_id=state_id,
        species_catalog=species_catalog,
        ph=ph,
    )
    mol = Chem.MolFromSmiles(species)
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
    species_catalog: Mapping[str, Any] | None = None,
    seed: int = EMBED_SEED,
    ph: float = PHYSIOLOGICAL_PH,
) -> dict[str, Any]:
    entity_id = str(compound.get("entity_id") or compound.get("ligand_id"))
    state_id = str(compound.get("state_id") or "state_01")
    if not entity_id:
        raise LigandPreparationError("Compound lacks entity_id/ligand_id.")
    basename = _species_basename(entity_id, state_id)

    work_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    sdf_path = work_dir / f"{basename}.sdf"
    pdbqt_path = output_dir / f"{basename}.pdbqt"

    embedding = smiles_to_sdf(
        str(compound["smiles"]),
        sdf_path,
        entity_id=entity_id,
        state_id=state_id,
        species_catalog=species_catalog,
        seed=seed,
        ph=ph,
    )

    pdbqt_path.unlink(missing_ok=True)
    command = [str(part) for part in meeko_command] + [
        "-i",
        str(sdf_path),
        "-o",
        str(pdbqt_path),
    ]
    completed = subprocess.run(
        command,
        cwd=project_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0 or not pdbqt_path.is_file():
        raise LigandPreparationError(
            f"({entity_id}, {state_id}) ligand PDBQT preparation failed "
            f"(exit {completed.returncode}): "
            f"{_tail(completed.stderr) or _tail(completed.stdout)}"
        )
    return {
        "entity_id": entity_id,
        "state_id": state_id,
        "species_key": [entity_id, state_id],
        # Legacy alias for readers not yet migrated; never used as a unique key.
        "ligand_id": entity_id,
        "smiles": compound["smiles"],
        "role": compound.get("role"),
        "set": compound.get("set"),
        **embedding,
        "sdf_path": _relative_path(sdf_path, project_root),
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
    species_catalog: Mapping[str, Any] | None = None,
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
            species_catalog=species_catalog,
            seed=seed,
            ph=ph,
        )
        for compound in compounds
    ]
    return {
        "ligand_prep_version": LIGAND_PREP_VERSION,
        "embed_seed": seed,
        "protonation_ph": ph,
        "protonation_tool": "authoritative species catalog plus frozen generic pKa rules",
        "mmff_variant": MMFF_VARIANT,
        "mmff_max_iterations": MMFF_MAX_ITERATIONS,
        "tool": "meeko mk_prepare_ligand",
        "ligands": ligands,
    }


def _species_basename(entity_id: str, state_id: str) -> str:
    def clean(value: str) -> str:
        cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("._")
        if not cleaned:
            raise LigandPreparationError(f"Unsafe empty filename component from {value!r}.")
        return cleaned

    return f"{clean(entity_id)}__{clean(state_id)}"


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

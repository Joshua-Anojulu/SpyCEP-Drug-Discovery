from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path
from typing import Any, Mapping, Sequence


LIGAND_PREP_VERSION = "2026-07-02"
LIGAND_OUTPUT_DIR = "data/compounds/pdbqt"
EMBED_SEED = 42


class LigandPreparationError(RuntimeError):
    """Raised when a ligand cannot be embedded or converted to PDBQT."""


def smiles_to_sdf(smiles: str, out_sdf: Path, *, seed: int = EMBED_SEED) -> int:
    """Embed a single deterministic 3D conformer and write it as SDF. Returns atom count."""
    from rdkit import Chem
    from rdkit.Chem import AllChem

    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise LigandPreparationError(f"RDKit could not parse SMILES: {smiles!r}")
    mol = Chem.AddHs(mol)
    params = AllChem.ETKDGv3()
    params.randomSeed = seed
    if AllChem.EmbedMolecule(mol, params) != 0:
        raise LigandPreparationError(f"RDKit could not embed a 3D conformer for SMILES: {smiles!r}")
    AllChem.MMFFOptimizeMolecule(mol)
    out_sdf.parent.mkdir(parents=True, exist_ok=True)
    writer = Chem.SDWriter(str(out_sdf))
    writer.write(mol)
    writer.close()
    return mol.GetNumAtoms()


def heavy_atom_count(smiles: str) -> int:
    from rdkit import Chem

    mol = Chem.MolFromSmiles(smiles)
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
) -> dict[str, Any]:
    ligand_id = str(compound["ligand_id"])
    work_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    sdf_path = work_dir / f"{ligand_id}.sdf"
    pdbqt_path = output_dir / f"{ligand_id}.pdbqt"
    atom_count = smiles_to_sdf(str(compound["smiles"]), sdf_path, seed=seed)

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
        "embed_seed": seed,
        "heavy_atom_count": heavy_atom_count(str(compound["smiles"])),
        "sdf_atom_count": atom_count,
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
) -> dict[str, Any]:
    ligands = [
        prepare_ligand(
            compound,
            project_root=project_root,
            work_dir=work_dir,
            output_dir=output_dir,
            meeko_command=meeko_command,
            seed=seed,
        )
        for compound in compounds
    ]
    return {
        "ligand_prep_version": LIGAND_PREP_VERSION,
        "embed_seed": seed,
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

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence


CONTACT_CUTOFF_ANGSTROM = 4.0


@dataclass(frozen=True)
class Atom:
    residue_key: str
    x: float
    y: float
    z: float


def parse_pdbqt_atoms(text: str, *, first_model_only: bool = False) -> tuple[Atom, ...]:
    atoms: list[Atom] = []
    for line in text.splitlines():
        if first_model_only and line.startswith("ENDMDL") and atoms:
            break
        if not line.startswith(("ATOM", "HETATM")):
            continue
        residue_number = line[22:26].strip()
        if not residue_number:
            continue
        residue_key = f"{line[21].strip()}:{int(residue_number)}:{line[17:20].strip()}"
        atoms.append(Atom(residue_key, float(line[30:38]), float(line[38:46]), float(line[46:54])))
    return tuple(atoms)


def contact_residue_keys(
    receptor_atoms: Sequence[Atom],
    ligand_atoms: Sequence[Atom],
    *,
    cutoff: float = CONTACT_CUTOFF_ANGSTROM,
) -> list[str]:
    if not receptor_atoms or not ligand_atoms:
        return []
    import numpy as np
    from scipy.spatial import cKDTree

    receptor_coords = np.array([[a.x, a.y, a.z] for a in receptor_atoms])
    ligand_coords = np.array([[a.x, a.y, a.z] for a in ligand_atoms])
    tree = cKDTree(receptor_coords)
    hit_groups = tree.query_ball_point(ligand_coords, r=cutoff)
    hit_indices: set[int] = set()
    for group in hit_groups:
        hit_indices.update(group)
    return sorted({receptor_atoms[index].residue_key for index in hit_indices})


def active_site_residue_keys(active_site_residues: Sequence[Mapping[str, Any]]) -> list[str]:
    return [
        f"{residue['chain_id']}:{int(residue['residue_number'])}:{residue['residue_name']}"
        for residue in active_site_residues
    ]


def analyze_pose_interactions(
    receptor_pdbqt_path: Path,
    pose_pdbqt_path: Path,
    active_site_residues: Sequence[Mapping[str, Any]],
    *,
    cutoff: float = CONTACT_CUTOFF_ANGSTROM,
) -> dict[str, Any]:
    receptor_atoms = parse_pdbqt_atoms(receptor_pdbqt_path.read_text(encoding="utf-8"))
    ligand_atoms = parse_pdbqt_atoms(pose_pdbqt_path.read_text(encoding="utf-8"), first_model_only=True)
    contacts = contact_residue_keys(receptor_atoms, ligand_atoms, cutoff=cutoff)
    active_keys = active_site_residue_keys(active_site_residues)
    contacted_active = [key for key in active_keys if key in set(contacts)]
    return {
        "contact_cutoff_angstrom": cutoff,
        "best_pose_ligand_atom_count": len(ligand_atoms),
        "contacted_residue_count": len(contacts),
        "contacted_active_site_residues": contacted_active,
        "contacts_catalytic_triad": len(contacted_active) == len(active_keys) and len(active_keys) > 0,
    }

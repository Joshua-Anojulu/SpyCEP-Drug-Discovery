from __future__ import annotations

from pathlib import Path

from spycep_drug_discovery.pdb_summary import AtomCoordinate, box_from_coordinates, coordinates_for_residue


ACTIVE_SITE_RESIDUES = (
    {"chain_id": "A", "residue_name": "ASP", "residue_number": 151},
    {"chain_id": "A", "residue_name": "HIS", "residue_number": 279},
    {"chain_id": "A", "residue_name": "SER", "residue_number": 617},
)
CATALYTIC_SIDE_CHAIN_ATOMS = {
    "ASP": frozenset({"CG", "OD1", "OD2"}),
    "HIS": frozenset({"CG", "ND1", "CD2", "CE1", "NE2"}),
    "SER": frozenset({"CB", "OG"}),
}
POCKET_PADDING_ANGSTROM = 6.0
MINIMUM_BOX_SIZE_ANGSTROM = 22.0


def build_spycep_pocket_definition(structure_dir: Path) -> dict:
    return {
        "definition_version": "2026-07-02",
        "target_id": "spycep_scpC",
        "decision_status": "approved_candidate_pockets",
        "padding_angstrom": POCKET_PADDING_ANGSTROM,
        "minimum_box_size_angstrom": MINIMUM_BOX_SIZE_ANGSTROM,
        "active_site_residues": list(ACTIVE_SITE_RESIDUES),
        "pockets": [
            _build_pocket(
                structure_dir=structure_dir,
                pdb_id="5XYA",
                pocket_id="spycep_5xya_aes_active_site",
                role="primary_ligand_anchor",
                coordinate_source="AES A1701 plus D151/H279/S617 catalytic side-chain atoms",
                notes=(
                    "Primary SpyCEP pocket candidate. AES is covalently linked to S617 in the PDB file "
                    "and anchors the active-site box."
                ),
                include_aes=True,
            ),
            _build_pocket(
                structure_dir=structure_dir,
                pdb_id="7EDD",
                pocket_id="spycep_7edd_native_active_site",
                role="native_coverage_comparator",
                coordinate_source="D151/H279/S617 catalytic side-chain atoms",
                notes=(
                    "Native active-site comparator with better coordinate coverage than 5XYA, "
                    "but no co-crystallized active-site ligand."
                ),
                include_aes=False,
            ),
        ],
        "supporting_structures": [
            {
                "pdb_id": "5XYR",
                "reason": "Native D151/H279/S617 coordinates are present, but no active-site ligand anchor is available.",
            }
        ],
        "excluded_structures": [
            {"pdb_id": "5XXZ", "reason": "H279A and S617A active-site mutations"},
        ],
        "preparation_notes": [
            "Treat these as receptor-preparation candidates, not completed docking results.",
            "Remove crystallographic solvent, salts, and non-anchor heterogens during receptor preparation.",
            "Record all receptor-preparation commands before any docking run.",
        ],
    }


def _build_pocket(
    structure_dir: Path,
    pdb_id: str,
    pocket_id: str,
    role: str,
    coordinate_source: str,
    notes: str,
    include_aes: bool,
) -> dict:
    path = structure_dir / f"{pdb_id}.pdb"
    coordinates = list(_active_site_side_chain_coordinates(path))
    if include_aes:
        coordinates.extend(
            coordinates_for_residue(path, chain_id="A", residue_number=1701, residue_name="AES", include_heterogens=True)
        )
    box = box_from_coordinates(
        coordinates,
        padding_angstrom=POCKET_PADDING_ANGSTROM,
        minimum_size_angstrom=MINIMUM_BOX_SIZE_ANGSTROM,
    )
    return {
        "pocket_id": pocket_id,
        "pdb_id": pdb_id,
        "chain_id": "A",
        "role": role,
        "coordinate_source": coordinate_source,
        "box_center_angstrom": _axis_dict(box.center),
        "box_size_angstrom": _axis_dict(box.size),
        "selected_atom_count": len(coordinates),
        "readiness": "approved_for_receptor_preparation",
        "notes": notes,
    }


def _active_site_side_chain_coordinates(path: Path) -> tuple[AtomCoordinate, ...]:
    coordinates: list[AtomCoordinate] = []
    for residue in ACTIVE_SITE_RESIDUES:
        residue_atoms = coordinates_for_residue(
            path,
            chain_id=residue["chain_id"],
            residue_number=int(residue["residue_number"]),
            residue_name=str(residue["residue_name"]),
        )
        side_chain_atoms = CATALYTIC_SIDE_CHAIN_ATOMS[str(residue["residue_name"])]
        selected = [atom for atom in residue_atoms if atom.atom_name in side_chain_atoms]
        if len(selected) != len(side_chain_atoms):
            raise ValueError(
                f"{path.name} is missing expected side-chain atoms for "
                f"{residue['residue_name']} {residue['chain_id']} {residue['residue_number']}."
            )
        coordinates.extend(selected)
    return tuple(coordinates)


def _axis_dict(values: tuple[float, float, float]) -> dict[str, float]:
    return {"x": values[0], "y": values[1], "z": values[2]}

import json
from pathlib import Path

from scripts.define_spycep_pockets import write_pocket_definition
from spycep_drug_discovery.pocket_definition import build_spycep_pocket_definition


def test_build_spycep_pocket_definition_selects_anchor_and_comparator_pockets(tmp_path):
    _write_pdb(
        tmp_path / "5XYA.pdb",
        [
            _atom("ATOM", 1, "CG", "ASP", "A", 151, 0.0, 0.0, 0.0),
            _atom("ATOM", 2, "OD1", "ASP", "A", 151, 1.0, 0.0, 0.0),
            _atom("ATOM", 3, "OD2", "ASP", "A", 151, 0.0, 1.0, 0.0),
            _atom("ATOM", 4, "CG", "HIS", "A", 279, 2.0, 0.0, 0.0),
            _atom("ATOM", 5, "ND1", "HIS", "A", 279, 2.0, 1.0, 0.0),
            _atom("ATOM", 6, "CD2", "HIS", "A", 279, 2.0, 0.0, 1.0),
            _atom("ATOM", 7, "CE1", "HIS", "A", 279, 2.0, 1.0, 1.0),
            _atom("ATOM", 8, "NE2", "HIS", "A", 279, 3.0, 1.0, 1.0),
            _atom("ATOM", 9, "CB", "SER", "A", 617, 4.0, 0.0, 0.0),
            _atom("ATOM", 10, "OG", "SER", "A", 617, 4.0, 1.0, 0.0),
            _atom("HETATM", 11, "S", "AES", "A", 1701, 5.0, 0.0, 0.0),
            _atom("HETATM", 12, "N8", "AES", "A", 1701, 5.0, 1.0, 1.0),
        ],
    )
    _write_pdb(
        tmp_path / "7EDD.pdb",
        [
            _atom("ATOM", 1, "CG", "ASP", "A", 151, -1.0, -1.0, -1.0),
            _atom("ATOM", 2, "OD1", "ASP", "A", 151, 0.0, -1.0, -1.0),
            _atom("ATOM", 3, "OD2", "ASP", "A", 151, -1.0, 0.0, -1.0),
            _atom("ATOM", 4, "CG", "HIS", "A", 279, 1.0, -1.0, -1.0),
            _atom("ATOM", 5, "ND1", "HIS", "A", 279, 1.0, 0.0, -1.0),
            _atom("ATOM", 6, "CD2", "HIS", "A", 279, 1.0, -1.0, 0.0),
            _atom("ATOM", 7, "CE1", "HIS", "A", 279, 1.0, 0.0, 0.0),
            _atom("ATOM", 8, "NE2", "HIS", "A", 279, 2.0, 0.0, 0.0),
            _atom("ATOM", 9, "CB", "SER", "A", 617, 3.0, -1.0, -1.0),
            _atom("ATOM", 10, "OG", "SER", "A", 617, 3.0, 0.0, -1.0),
        ],
    )

    definition = build_spycep_pocket_definition(tmp_path)
    pockets = {pocket["pocket_id"]: pocket for pocket in definition["pockets"]}

    assert definition["target_id"] == "spycep_scpC"
    assert definition["decision_status"] == "approved_candidate_pockets"
    assert pockets["spycep_5xya_aes_active_site"]["role"] == "primary_ligand_anchor"
    assert pockets["spycep_5xya_aes_active_site"]["selected_atom_count"] == 12
    assert pockets["spycep_5xya_aes_active_site"]["box_center_angstrom"] == {"x": 2.5, "y": 0.5, "z": 0.5}
    assert pockets["spycep_5xya_aes_active_site"]["box_size_angstrom"] == {"x": 22.0, "y": 22.0, "z": 22.0}
    assert pockets["spycep_7edd_native_active_site"]["role"] == "native_coverage_comparator"
    assert pockets["spycep_7edd_native_active_site"]["selected_atom_count"] == 10
    assert {"pdb_id": "5XXZ", "reason": "H279A and S617A active-site mutations"} in definition["excluded_structures"]


def test_write_pocket_definition_writes_reproducible_json(tmp_path):
    structure_dir = tmp_path / "structures"
    structure_dir.mkdir()
    _write_pdb(
        structure_dir / "5XYA.pdb",
        [
            _atom("ATOM", 1, "CG", "ASP", "A", 151, 0.0, 0.0, 0.0),
            _atom("ATOM", 2, "OD1", "ASP", "A", 151, 1.0, 0.0, 0.0),
            _atom("ATOM", 3, "OD2", "ASP", "A", 151, 0.0, 1.0, 0.0),
            _atom("ATOM", 4, "CG", "HIS", "A", 279, 2.0, 0.0, 0.0),
            _atom("ATOM", 5, "ND1", "HIS", "A", 279, 2.0, 1.0, 0.0),
            _atom("ATOM", 6, "CD2", "HIS", "A", 279, 2.0, 0.0, 1.0),
            _atom("ATOM", 7, "CE1", "HIS", "A", 279, 2.0, 1.0, 1.0),
            _atom("ATOM", 8, "NE2", "HIS", "A", 279, 3.0, 1.0, 1.0),
            _atom("ATOM", 9, "CB", "SER", "A", 617, 4.0, 0.0, 0.0),
            _atom("ATOM", 10, "OG", "SER", "A", 617, 4.0, 1.0, 0.0),
            _atom("HETATM", 11, "S", "AES", "A", 1701, 5.0, 0.0, 0.0),
            _atom("HETATM", 12, "N8", "AES", "A", 1701, 5.0, 1.0, 1.0),
        ],
    )
    _write_pdb(
        structure_dir / "7EDD.pdb",
        [
            _atom("ATOM", 1, "CG", "ASP", "A", 151, -1.0, -1.0, -1.0),
            _atom("ATOM", 2, "OD1", "ASP", "A", 151, 0.0, -1.0, -1.0),
            _atom("ATOM", 3, "OD2", "ASP", "A", 151, -1.0, 0.0, -1.0),
            _atom("ATOM", 4, "CG", "HIS", "A", 279, 1.0, -1.0, -1.0),
            _atom("ATOM", 5, "ND1", "HIS", "A", 279, 1.0, 0.0, -1.0),
            _atom("ATOM", 6, "CD2", "HIS", "A", 279, 1.0, -1.0, 0.0),
            _atom("ATOM", 7, "CE1", "HIS", "A", 279, 1.0, 0.0, 0.0),
            _atom("ATOM", 8, "NE2", "HIS", "A", 279, 2.0, 0.0, 0.0),
            _atom("ATOM", 9, "CB", "SER", "A", 617, 3.0, -1.0, -1.0),
            _atom("ATOM", 10, "OG", "SER", "A", 617, 3.0, 0.0, -1.0),
        ],
    )
    output_path = tmp_path / "pocket_definition.json"

    definition = write_pocket_definition(structure_dir, output_path)

    assert json.loads(output_path.read_text(encoding="utf-8")) == definition


def test_tracked_pocket_definition_records_approved_candidate_receptor_set():
    definition = json.loads(Path("docs/methods/pocket_definition.json").read_text(encoding="utf-8"))
    pockets = {pocket["pdb_id"]: pocket for pocket in definition["pockets"]}

    assert definition["decision_status"] == "approved_candidate_pockets"
    assert set(pockets) == {"5XYA", "7EDD"}
    assert pockets["5XYA"]["role"] == "primary_ligand_anchor"
    assert pockets["7EDD"]["role"] == "native_coverage_comparator"
    assert all(pocket["readiness"] == "approved_for_receptor_preparation" for pocket in pockets.values())
    assert {"pdb_id": "5XXZ", "reason": "H279A and S617A active-site mutations"} in definition["excluded_structures"]


def _write_pdb(path: Path, lines: list[str]) -> None:
    path.write_text("\n".join(lines + ["END"]), encoding="utf-8")


def _atom(
    record: str,
    serial: int,
    atom_name: str,
    residue_name: str,
    chain_id: str,
    residue_number: int,
    x: float,
    y: float,
    z: float,
) -> str:
    element = atom_name[0]
    return (
        f"{record:<6}{serial:5d} {atom_name:>4} {residue_name:>3} {chain_id}{residue_number:4d}"
        f"    {x:8.3f}{y:8.3f}{z:8.3f}  1.00 10.00          {element:>2}"
    )


def test_side_chain_selector_excludes_backbone_atoms(tmp_path):
    # A box described as a "side-chain centroid" must not average backbone atoms in.
    # define_tight_pockets previously read the PDBQT, which carries no atom names, and
    # so silently included backbone N/CA/C/O and polar hydrogens.
    from spycep_drug_discovery.pocket_definition import active_site_side_chain_coordinates

    pdb = tmp_path / "x.pdb"
    pdb.write_text(_triad_pdb_text(), encoding="utf-8")

    atoms = active_site_side_chain_coordinates(pdb)

    names = {atom.atom_name for atom in atoms}
    assert names == {"CG", "OD1", "OD2", "ND1", "CD2", "CE1", "NE2", "CB", "OG"}
    assert not names & {"N", "CA", "C", "O"}


def _triad_pdb_text() -> str:
    rows = [
        ("ASP", 151, [("N", 0.0), ("CA", 1.0), ("C", 2.0), ("O", 3.0), ("CG", 4.0), ("OD1", 5.0), ("OD2", 6.0)]),
        ("HIS", 279, [("N", 0.0), ("CA", 1.0), ("C", 2.0), ("O", 3.0), ("CG", 4.0), ("ND1", 5.0),
                      ("CD2", 6.0), ("CE1", 7.0), ("NE2", 8.0)]),
        ("SER", 617, [("N", 0.0), ("CA", 1.0), ("C", 2.0), ("O", 3.0), ("CB", 4.0), ("OG", 5.0)]),
    ]
    lines = []
    serial = 1
    for residue_name, number, atoms in rows:
        for atom_name, value in atoms:
            lines.append(
                f"ATOM  {serial:>5} {atom_name:<4}{residue_name:>4} A{number:>4}    "
                f"{value:>8.3f}{value:>8.3f}{value:>8.3f}  1.00  0.00"
            )
            serial += 1
    lines.append("END")
    return "\n".join(lines) + "\n"

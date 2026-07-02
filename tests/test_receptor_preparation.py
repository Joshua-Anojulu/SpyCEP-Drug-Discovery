import hashlib
import json

from scripts.prepare_receptors import write_receptor_preparation
from spycep_drug_discovery.receptor_preparation import clean_receptor_pdb_text, prepare_receptors


def test_clean_receptor_pdb_text_keeps_chain_and_converts_mse():
    pdb_text = "\n".join(
        [
            _atom("ATOM", 1, "CA", "SER", "A", 10, 1.0, 2.0, 3.0, "C"),
            _atom("ATOM", 2, "CA", "SER", "B", 10, 4.0, 5.0, 6.0, "C"),
            _atom("HETATM", 3, "SE", "MSE", "A", 11, 7.0, 8.0, 9.0, "SE"),
            _atom("HETATM", 4, "S", "AES", "A", 1701, 10.0, 11.0, 12.0, "S"),
            "CONECT    3    4",
            "END",
        ]
    )

    cleaned = clean_receptor_pdb_text(pdb_text, chain_id="A")

    assert "SER A  10" in cleaned.pdb_text
    assert "SER B  10" not in cleaned.pdb_text
    assert "MET A  11" in cleaned.pdb_text
    assert " SD  MET" in cleaned.pdb_text
    assert "AES A1701" not in cleaned.pdb_text
    assert "CONECT" not in cleaned.pdb_text
    assert cleaned.pdb_text.endswith("END\n")
    assert cleaned.retained_atom_records == 2
    assert cleaned.converted_mse_records == 1
    assert cleaned.removed_heterogen_records == 1


def test_prepare_receptors_writes_cleaned_pdbs_and_manifest(tmp_path):
    structure_dir = tmp_path / "structures"
    output_dir = tmp_path / "processed" / "receptors"
    structure_dir.mkdir()
    source_pdb = structure_dir / "5XYA.pdb"
    source_pdb.write_text(
        "\n".join(
            [
                _atom("ATOM", 1, "CA", "SER", "A", 10, 1.0, 2.0, 3.0, "C"),
                _atom("HETATM", 2, "S", "AES", "A", 1701, 10.0, 11.0, 12.0, "S"),
                "END",
            ]
        ),
        encoding="utf-8",
    )
    pocket_definition = {
        "pockets": [
            {
                "pocket_id": "spycep_5xya_aes_active_site",
                "pdb_id": "5XYA",
                "chain_id": "A",
                "box_center_angstrom": {"x": -43.74, "y": 28.233, "z": 26.561},
                "box_size_angstrom": {"x": 22.0, "y": 22.0, "z": 27.5},
            }
        ]
    }

    manifest = prepare_receptors(pocket_definition, structure_dir, output_dir)

    receptor = manifest["receptors"][0]
    output_text = (output_dir / "spycep_5xya_aes_active_site.pdb").read_text(encoding="utf-8")
    assert receptor["prepared_pdb_path"] == "data/processed/receptors/spycep_5xya_aes_active_site.pdb"
    assert receptor["sha256"] == hashlib.sha256(output_text.encode("utf-8")).hexdigest()
    assert receptor["box_center_angstrom"] == {"x": -43.74, "y": 28.233, "z": 26.561}
    assert receptor["removed_heterogen_records"] == 1


def test_write_receptor_preparation_writes_manifest_json(tmp_path):
    structure_dir = tmp_path / "structures"
    output_dir = tmp_path / "processed" / "receptors"
    manifest_path = tmp_path / "docs" / "methods" / "receptor_preparation.json"
    structure_dir.mkdir()
    (structure_dir / "5XYA.pdb").write_text(
        "\n".join(
            [
                _atom("ATOM", 1, "CA", "SER", "A", 10, 1.0, 2.0, 3.0, "C"),
                _atom("HETATM", 2, "S", "AES", "A", 1701, 10.0, 11.0, 12.0, "S"),
                "END",
            ]
        ),
        encoding="utf-8",
    )
    pocket_definition_path = tmp_path / "docs" / "methods" / "pocket_definition.json"
    pocket_definition_path.parent.mkdir(parents=True)
    pocket_definition_path.write_text(
        json.dumps(
            {
                "pockets": [
                    {
                        "pocket_id": "spycep_5xya_aes_active_site",
                        "pdb_id": "5XYA",
                        "chain_id": "A",
                        "box_center_angstrom": {"x": -43.74, "y": 28.233, "z": 26.561},
                        "box_size_angstrom": {"x": 22.0, "y": 22.0, "z": 27.5},
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    manifest = write_receptor_preparation(pocket_definition_path, structure_dir, output_dir, manifest_path)

    assert json.loads(manifest_path.read_text(encoding="utf-8")) == manifest
    assert (output_dir / "spycep_5xya_aes_active_site.pdb").is_file()


def test_tracked_receptor_preparation_manifest_records_cleaned_receptors():
    manifest = json.loads(open("docs/methods/receptor_preparation.json", encoding="utf-8").read())
    receptors = {receptor["pdb_id"]: receptor for receptor in manifest["receptors"]}

    assert set(receptors) == {"5XYA", "7EDD"}
    assert receptors["5XYA"]["prepared_pdb_path"] == "data/processed/receptors/spycep_5xya_aes_active_site.pdb"
    assert receptors["7EDD"]["prepared_pdb_path"] == "data/processed/receptors/spycep_7edd_native_active_site.pdb"
    assert all(len(receptor["sha256"]) == 64 for receptor in receptors.values())
    assert "PDBQT conversion remains a later" in " ".join(manifest["rules"])


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
    element: str,
) -> str:
    return (
        f"{record:<6}{serial:5d} {atom_name:>4} {residue_name:>3} {chain_id}{residue_number:4d}"
        f"    {x:8.3f}{y:8.3f}{z:8.3f}  1.00 10.00          {element:>2}"
    )

import hashlib
import json
import sys

import pytest

from scripts.convert_receptors_to_pdbqt import write_pdbqt_conversion
from spycep_drug_discovery.pdbqt_conversion import PdbqtConversionError, convert_receptors_to_pdbqt


def test_convert_receptors_to_pdbqt_invokes_converter_and_records_outputs(tmp_path):
    project_root = _project_with_prepared_receptor(tmp_path)
    fake_converter = _write_fake_converter(tmp_path)
    receptor_manifest = _receptor_manifest()

    manifest = convert_receptors_to_pdbqt(
        receptor_manifest,
        project_root=project_root,
        output_dir=project_root / "data" / "processed" / "pdbqt",
        converter_command=(sys.executable, str(fake_converter)),
        tool_info={"name": "fake mk_prepare_receptor", "meeko_version": "test"},
    )

    conversion = manifest["receptors"][0]
    pdbqt_bytes = (project_root / "data" / "processed" / "pdbqt" / "spycep_fake.pdbqt").read_bytes()

    assert manifest["allow_bad_res"] is True
    assert "SpyCEP crystal structures contain incomplete residues" in manifest["allow_bad_res_reason"]
    assert conversion["pocket_id"] == "spycep_fake"
    assert conversion["source_prepared_pdb_path"] == "data/processed/receptors/spycep_fake.pdb"
    assert conversion["output_paths"]["pdbqt"] == "data/processed/pdbqt/spycep_fake.pdbqt"
    assert conversion["output_sha256"]["pdbqt"] == hashlib.sha256(pdbqt_bytes).hexdigest()
    assert conversion["pdbqt_atom_records"] == 1
    assert conversion["exit_code"] == 0
    assert "--read_pdb" in conversion["command"]
    assert "--write_pdbqt" in conversion["command"]
    assert "--write_json" in conversion["command"]
    assert "--write_vina_box" in conversion["command"]
    assert "--allow_bad_res" in conversion["command"]
    assert conversion["command"][-9:] == [
        "--box_center",
        "-43.740",
        "28.233",
        "26.561",
        "--box_size",
        "22.000",
        "22.000",
        "27.500",
        "--allow_bad_res",
    ]


def test_convert_receptors_to_pdbqt_raises_when_converter_fails(tmp_path):
    project_root = _project_with_prepared_receptor(tmp_path)
    failing_converter = tmp_path / "failing_converter.py"
    failing_converter.write_text("import sys\nprint('template mismatch', file=sys.stderr)\nsys.exit(3)\n", encoding="utf-8")

    with pytest.raises(PdbqtConversionError, match="template mismatch"):
        convert_receptors_to_pdbqt(
            _receptor_manifest(),
            project_root=project_root,
            output_dir=project_root / "data" / "processed" / "pdbqt",
            converter_command=(sys.executable, str(failing_converter)),
            tool_info={"name": "fake mk_prepare_receptor"},
        )


def test_write_pdbqt_conversion_writes_manifest_json(tmp_path):
    project_root = _project_with_prepared_receptor(tmp_path)
    fake_converter = _write_fake_converter(tmp_path)
    receptor_manifest_path = project_root / "docs" / "methods" / "receptor_preparation.json"
    output_dir = project_root / "data" / "processed" / "pdbqt"
    manifest_path = project_root / "docs" / "methods" / "pdbqt_conversion.json"

    manifest = write_pdbqt_conversion(
        receptor_manifest_path=receptor_manifest_path,
        project_root=project_root,
        output_dir=output_dir,
        manifest_path=manifest_path,
        converter_command=(sys.executable, str(fake_converter)),
        tool_info={"name": "fake mk_prepare_receptor", "meeko_version": "test"},
    )

    assert json.loads(manifest_path.read_text(encoding="utf-8")) == manifest
    assert (output_dir / "spycep_fake.pdbqt").is_file()


def test_tracked_pdbqt_conversion_manifest_records_approved_receptors():
    manifest = json.loads(open("docs/methods/pdbqt_conversion.json", encoding="utf-8").read())
    receptors = {receptor["pdb_id"]: receptor for receptor in manifest["receptors"]}

    assert manifest["tool"]["name"] == "Meeko mk_prepare_receptor"
    assert manifest["allow_bad_res"] is True
    assert set(receptors) == {"5XYA", "7EDD"}
    assert receptors["5XYA"]["output_paths"]["pdbqt"] == "data/processed/pdbqt/spycep_5xya_aes_active_site.pdbqt"
    assert receptors["7EDD"]["output_paths"]["pdbqt"] == "data/processed/pdbqt/spycep_7edd_native_active_site.pdbqt"
    assert all(len(receptor["output_sha256"]["pdbqt"]) == 64 for receptor in receptors.values())
    assert all(receptor["exit_code"] == 0 for receptor in receptors.values())


def _project_with_prepared_receptor(tmp_path):
    project_root = tmp_path / "project"
    receptor_dir = project_root / "data" / "processed" / "receptors"
    docs_dir = project_root / "docs" / "methods"
    receptor_dir.mkdir(parents=True)
    docs_dir.mkdir(parents=True)
    (receptor_dir / "spycep_fake.pdb").write_text("ATOM      1  CA  SER A 617\nEND\n", encoding="utf-8")
    (docs_dir / "receptor_preparation.json").write_text(json.dumps(_receptor_manifest()), encoding="utf-8")
    return project_root


def _write_fake_converter(tmp_path):
    fake_converter = tmp_path / "fake_converter.py"
    fake_converter.write_text(
        "\n".join(
            [
                "from pathlib import Path",
                "import sys",
                "args = sys.argv[1:]",
                "stem = Path(args[args.index('-o') + 1])",
                "assert '--read_pdb' in args",
                "assert '--write_pdbqt' in args",
                "assert '--write_json' in args",
                "assert '--write_vina_box' in args",
                "assert '--allow_bad_res' in args",
                "stem.parent.mkdir(parents=True, exist_ok=True)",
                "(stem.parent / f'{stem.name}.pdbqt').write_text('ATOM      1  CA  SER A 617     0.000   0.000   0.000  1.00  0.00     0.100 C\\n', encoding='utf-8')",
                "(stem.parent / f'{stem.name}.json').write_text('{}\\n', encoding='utf-8')",
                "(stem.parent / f'{stem.name}.box.txt').write_text('center_x = -43.740\\n', encoding='utf-8')",
                "(stem.parent / f'{stem.name}.box.pdb').write_text('REMARK box\\n', encoding='utf-8')",
            ]
        ),
        encoding="utf-8",
    )
    return fake_converter


def _receptor_manifest():
    return {
        "preparation_version": "2026-07-02",
        "source_pocket_definition": "docs/methods/pocket_definition.json",
        "receptors": [
            {
                "pocket_id": "spycep_fake",
                "pdb_id": "FAKE",
                "chain_id": "A",
                "prepared_pdb_path": "data/processed/receptors/spycep_fake.pdb",
                "sha256": "a" * 64,
                "box_center_angstrom": {"x": -43.74, "y": 28.233, "z": 26.561},
                "box_size_angstrom": {"x": 22.0, "y": 22.0, "z": 27.5},
            }
        ],
    }

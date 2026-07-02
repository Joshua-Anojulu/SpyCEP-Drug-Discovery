import json

from scripts.review_pdbqt_conversion import write_pdbqt_quality_review
from spycep_drug_discovery.pdbqt_quality import build_pdbqt_quality_review, parse_ignored_residue_keys


def test_parse_ignored_residue_keys_reads_meeko_warning_tail():
    stderr_tail = "- Template matching failed for: ['A:118', 'A:604', 'A:613'] Ignored due to allow_bad_res."

    assert parse_ignored_residue_keys(stderr_tail) == ("A:118", "A:604", "A:613")


def test_build_pdbqt_quality_review_records_catalytic_residue_status(tmp_path):
    project_root = _project_with_pdbqt(tmp_path, active_site_residues=("A:151:ASP", "A:279:HIS", "A:617:SER"))

    review = build_pdbqt_quality_review(
        conversion_manifest=_conversion_manifest(ignored_residues=("A:604", "A:613")),
        pocket_definition=_pocket_definition(),
        project_root=project_root,
    )

    receptor = review["receptors"][0]
    assert review["decision_status"] == "reviewed_caution_not_docking_approval"
    assert receptor["quality_status"] == "reviewed_caution"
    assert receptor["ignored_residue_count"] == 2
    assert receptor["ignored_active_site_residue_keys"] == []
    assert receptor["missing_active_site_residue_keys"] == []
    assert receptor["pdbqt_active_site_residue_keys"] == ["A:151:ASP", "A:279:HIS", "A:617:SER"]
    assert receptor["pdbqt_active_site_atom_counts"] == {"A:151:ASP": 1, "A:279:HIS": 1, "A:617:SER": 1}
    assert receptor["box_matches_conversion_manifest"] is True
    assert "not docking approval" in receptor["review_notes"]


def test_build_pdbqt_quality_review_blocks_active_site_omissions(tmp_path):
    project_root = _project_with_pdbqt(tmp_path, active_site_residues=("A:151:ASP", "A:279:HIS"))

    review = build_pdbqt_quality_review(
        conversion_manifest=_conversion_manifest(ignored_residues=("A:617",)),
        pocket_definition=_pocket_definition(),
        project_root=project_root,
    )

    receptor = review["receptors"][0]
    assert review["decision_status"] == "blocked_before_docking"
    assert receptor["quality_status"] == "blocked"
    assert receptor["ignored_active_site_residue_keys"] == ["A:617"]
    assert receptor["missing_active_site_residue_keys"] == ["A:617:SER"]


def test_write_pdbqt_quality_review_writes_manifest_json(tmp_path):
    project_root = _project_with_pdbqt(tmp_path, active_site_residues=("A:151:ASP", "A:279:HIS", "A:617:SER"))
    conversion_path = project_root / "docs" / "methods" / "pdbqt_conversion.json"
    pocket_path = project_root / "docs" / "methods" / "pocket_definition.json"
    manifest_path = project_root / "docs" / "methods" / "pdbqt_quality_review.json"
    conversion_path.write_text(json.dumps(_conversion_manifest(ignored_residues=("A:604",))), encoding="utf-8")
    pocket_path.write_text(json.dumps(_pocket_definition()), encoding="utf-8")

    review = write_pdbqt_quality_review(
        conversion_manifest_path=conversion_path,
        pocket_definition_path=pocket_path,
        project_root=project_root,
        manifest_path=manifest_path,
    )

    assert json.loads(manifest_path.read_text(encoding="utf-8")) == review


def test_tracked_pdbqt_quality_review_records_no_active_site_omissions():
    review = json.loads(open("docs/methods/pdbqt_quality_review.json", encoding="utf-8").read())
    receptors = {receptor["pdb_id"]: receptor for receptor in review["receptors"]}

    assert review["decision_status"] == "reviewed_caution_not_docking_approval"
    assert set(receptors) == {"5XYA", "7EDD"}
    assert all(receptor["quality_status"] == "reviewed_caution" for receptor in receptors.values())
    assert all(receptor["ignored_active_site_residue_keys"] == [] for receptor in receptors.values())
    assert all(receptor["missing_active_site_residue_keys"] == [] for receptor in receptors.values())
    assert all(receptor["box_matches_conversion_manifest"] is True for receptor in receptors.values())


def _project_with_pdbqt(tmp_path, active_site_residues):
    project_root = tmp_path / "project"
    pdbqt_dir = project_root / "data" / "processed" / "pdbqt"
    docs_dir = project_root / "docs" / "methods"
    pdbqt_dir.mkdir(parents=True)
    docs_dir.mkdir(parents=True)
    pdbqt_dir.joinpath("spycep_fake.pdbqt").write_text(
        "\n".join(_pdbqt_line(residue_key, index) for index, residue_key in enumerate(active_site_residues, start=1))
        + "\n",
        encoding="utf-8",
    )
    return project_root


def _conversion_manifest(ignored_residues):
    return {
        "conversion_version": "2026-07-02",
        "allow_bad_res": True,
        "receptors": [
            {
                "pocket_id": "spycep_fake",
                "pdb_id": "FAKE",
                "chain_id": "A",
                "box_center_angstrom": {"x": -43.74, "y": 28.233, "z": 26.561},
                "box_size_angstrom": {"x": 22.0, "y": 22.0, "z": 27.5},
                "stderr_tail": f"- Template matching failed for: {list(ignored_residues)!r} Ignored due to allow_bad_res.",
                "output_paths": {"pdbqt": "data/processed/pdbqt/spycep_fake.pdbqt"},
            }
        ],
    }


def _pocket_definition():
    return {
        "definition_version": "2026-07-02",
        "active_site_residues": [
            {"chain_id": "A", "residue_name": "ASP", "residue_number": 151},
            {"chain_id": "A", "residue_name": "HIS", "residue_number": 279},
            {"chain_id": "A", "residue_name": "SER", "residue_number": 617},
        ],
        "pockets": [
            {
                "pocket_id": "spycep_fake",
                "pdb_id": "FAKE",
                "box_center_angstrom": {"x": -43.74, "y": 28.233, "z": 26.561},
                "box_size_angstrom": {"x": 22.0, "y": 22.0, "z": 27.5},
            }
        ],
    }


def _pdbqt_line(residue_key: str, serial: int) -> str:
    chain_id, residue_number, residue_name = residue_key.split(":")
    return (
        f"ATOM  {serial:5d}  CA  {residue_name:>3} {chain_id}{int(residue_number):4d}"
        "     0.000   0.000   0.000  1.00  0.00     0.100 C"
    )

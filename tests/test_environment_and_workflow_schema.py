import copy
from pathlib import Path

from spycep_drug_discovery.docking import (
    RUN_RECORD_REQUIRED_FIELDS,
    RUN_SCHEMA_VERSION,
    _json_sha256,
    build_run_manifest,
)
from spycep_drug_discovery.environment import (
    PINNED_MEEKO_VERSION,
    PINNED_RDKIT_VERSION,
    require_pinned_chemistry_environment,
)


def _run_record(workflow):
    payload = {
        "run_schema_version": RUN_SCHEMA_VERSION,
        "command": ["tools/vina.exe", "--cpu", "1", "--scoring", "vina"],
        "entity_id": "entity",
        "state_id": "state_01",
        "ligand_pdbqt_sha256": "a" * 64,
        "receptor_pdbqt_sha256": "b" * 64,
        "vina_binary_sha256": "c" * 64,
        "box_center_angstrom": {"x": 1.0, "y": 2.0, "z": 3.0},
        "box_size_angstrom": {"x": 18.0, "y": 18.0, "z": 18.0},
        "seed": 42,
        "exhaustiveness": 8,
        "num_modes": 9,
        "cpu": 1,
        "scoring": "vina",
        "timeout_seconds": 1800.0,
        "species_catalog_sha256": "d" * 64,
        "attempt_manifest_sha256": "e" * 64,
    }
    return {
        "run_schema_version": RUN_SCHEMA_VERSION,
        "fingerprint": _json_sha256(payload),
        "fingerprint_payload": payload,
        "workflow": workflow,
        "claim_key": f"{workflow}:entity:state_01:pocket",
        "entity_id": "entity",
        "state_id": "state_01",
        "species_key": ["entity", "state_01"],
        "pocket_id": "pocket",
        "pdb_id": "PDB",
        "command": payload["command"],
        "ligand_pdbqt_path": "ligand.pdbqt",
        "ligand_pdbqt_sha256": payload["ligand_pdbqt_sha256"],
        "receptor_pdbqt_path": "receptor.pdbqt",
        "receptor_pdbqt_sha256": payload["receptor_pdbqt_sha256"],
        "vina_binary_sha256": payload["vina_binary_sha256"],
        "box_center_angstrom": payload["box_center_angstrom"],
        "box_size_angstrom": payload["box_size_angstrom"],
        "seed": 42,
        "exhaustiveness": 8,
        "num_modes": 9,
        "cpu": 1,
        "scoring": "vina",
        "timeout_seconds": 1800.0,
        "species_catalog_sha256": payload["species_catalog_sha256"],
        "attempt_manifest_sha256": payload["attempt_manifest_sha256"],
        "software_versions": {
            "rdkit": PINNED_RDKIT_VERSION,
            "meeko": PINNED_MEEKO_VERSION,
            "vina": "AutoDock Vina v1.2.7",
        },
        "elapsed_seconds": 1.0,
        "status": "valid_fit",
        "cause": None,
        "exit_code": 0,
        "out_path": "pose.pdbqt",
        "out_sha256": "f" * 64,
        "sidecar_path": "pose.run.json",
        "resumed": False,
        "valid_fit": True,
        "modes": [
            {
                "mode": 1,
                "affinity_kcal_mol": -5.0,
                "rmsd_lb": 0.0,
                "rmsd_ub": 0.0,
            }
        ],
        "best_affinity_kcal_mol": -5.0,
        "mean_affinity_kcal_mol": -5.0,
        "mode_count": 1,
    }


def test_runtime_chemistry_environment_matches_exact_pins():
    assert require_pinned_chemistry_environment() == {
        "rdkit": PINNED_RDKIT_VERSION,
        "meeko": PINNED_MEEKO_VERSION,
    }
    pyproject = Path("pyproject.toml").read_text(encoding="utf-8")
    assert '"rdkit==2025.9.6"' in pyproject
    assert '"meeko==0.7.1"' in pyproject


def test_all_four_workflows_serialize_one_shared_run_record_schema():
    for workflow in ("wide", "tight", "speb", "boron"):
        record = _run_record(workflow)
        manifest = build_run_manifest(
            workflow=workflow,
            run_records=[record],
            species_catalog_sha256="d" * 64,
            attempt_manifest_sha256="e" * 64,
            software_versions=record["software_versions"],
        )

        assert manifest["run_schema_version"] == RUN_SCHEMA_VERSION
        assert RUN_RECORD_REQUIRED_FIELDS.issubset(manifest["run_records"][0])
        assert manifest["software_versions"]["rdkit"] == PINNED_RDKIT_VERSION
        assert manifest["run_records"][0]["vina_binary_sha256"] == "c" * 64


def test_each_workflow_entry_point_uses_shared_manifest_and_content_hashes():
    scripts = (
        "scripts/run_docking.py",
        "scripts/run_speb_positive_control.py",
        "scripts/dock_boron_surrogates.py",
    )
    for script in scripts:
        text = Path(script).read_text(encoding="utf-8")
        assert "build_run_manifest(" in text
        assert "species_catalog_sha256=" in text
        assert "attempt_manifest_sha256=" in text
        assert "software_versions=versions" in text
        assert "DEFAULT_CPU" in text
        assert "DEFAULT_SCORING" in text
        assert "DEFAULT_TIMEOUT_SECONDS" in text


def test_speb_docking_entry_point_cannot_convert_receptor_or_bypass_qc():
    text = Path("scripts/run_speb_positive_control.py").read_text(encoding="utf-8")

    assert "prepare_speb_receptor.py" in text
    assert "validate_pdbqt_quality_gate(" in text
    assert "mk_prepare_receptor" not in text
    assert "--allow_bad_res" not in text
    assert "clean_receptor_pdb_text" not in text



def test_tracked_stage1_manifests_contain_no_user_specific_absolute_paths():
    manifests = (
        "docs/methods/species_audit.json",
        "docs/methods/attempt_manifest.json",
        "docs/methods/mmff_preparation_audit.json",
        "docs/methods/pdbqt_conversion.json",
        "docs/methods/pdbqt_quality_review.json",
        "docs/methods/speb_receptor_preparation.json",
        "docs/methods/speb_pocket_definition.json",
        "docs/methods/speb_pdbqt_conversion.json",
        "docs/methods/speb_pdbqt_quality_review.json",
    )
    for path in manifests:
        text = Path(path).read_text(encoding="utf-8").lower()
        assert "c:\\\\users\\" not in text, path
        assert "josha" not in text, path

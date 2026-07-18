import hashlib
import json
import sys
import threading
from pathlib import Path

import pytest

import spycep_drug_discovery.docking as docking
from spycep_drug_discovery.docking import (
    WAIT_OBJECT_0,
    InfrastructureError,
    SupervisedResult,
    build_run_manifest,
    campaign_lock,
    campaign_output_dir,
    dock_ligand,
    initialize_spawn_retry_ledger,
    require_campaign_seal,
    require_unsealed,
    seal_campaign,
)


POSE_PDBQT = """MODEL 1
REMARK VINA RESULT:      -5.367      0.000      0.000
ATOM      1  C   LIG A 900      10.0  1.0  0.0  1.00  0.00     0.000 C
ENDMDL
"""


@pytest.fixture(autouse=True)
def _guard_against_unmocked_native_supervisor(monkeypatch):
    def forbidden(*_args, **_kwargs):
        raise AssertionError("unit test reached the real CreateProcessW supervisor")

    monkeypatch.setattr(docking, "_run_vina_supervised", forbidden)


def _supervised(exit_code=0):
    return SupervisedResult(
        disposition_basis="wait_signaled",
        wait_result=WAIT_OBJECT_0,
        termination_action="none",
        exit_code=exit_code,
        unbiased_seconds=0.007 if exit_code else 1.0,
        wall_seconds=0.007 if exit_code else 1.0,
    )


def _runner(outcomes):
    iterator = iter(outcomes)

    def fake(command, _timeout_seconds, **_kwargs):
        result = next(iterator)
        if result.exit_code == 0:
            Path(command[command.index("--out") + 1]).write_text(
                POSE_PDBQT, encoding="utf-8"
            )
        return result

    return fake


def _stage_inputs(tmp_path, campaign_id, workflow):
    ligand = tmp_path / f"{workflow}.ligand.pdbqt"
    receptor = tmp_path / "receptor.pdbqt"
    ligand.write_text("ATOM ligand\n", encoding="utf-8")
    receptor.write_text("ATOM receptor\n", encoding="utf-8")
    return {
        "vina_executable": sys.executable,
        "receptor": {
            "pocket_id": "fake_pocket",
            "pdb_id": "FAKE",
            "receptor_pdbqt_path": receptor,
            "box_center_angstrom": {"x": 1, "y": 2, "z": 3},
            "box_size_angstrom": {"x": 18, "y": 18, "z": 18},
        },
        "entity_id": f"entity-{workflow}",
        "state_id": "state_a",
        "ligand_pdbqt": ligand,
        "project_root": tmp_path,
        "output_dir": campaign_output_dir(tmp_path, campaign_id, workflow),
        "workflow": workflow,
        "species_catalog_sha256": "a" * 64,
        "attempt_manifest_sha256": "b" * 64,
        "software_versions": {"vina": "test"},
        "campaign_id": campaign_id,
    }


def _write_four_stage_manifests(
    tmp_path,
    monkeypatch,
    *,
    campaign_id="seal-test",
    retried_workflow=None,
):
    initialize_spawn_retry_ledger(tmp_path, campaign_id)
    paths = []
    for workflow in ("wide", "tight", "speb", "boron"):
        outcomes = (
            (_supervised(0xC0000142), _supervised())
            if workflow == retried_workflow
            else (_supervised(),)
        )
        monkeypatch.setattr(docking, "_run_vina_supervised", _runner(outcomes))
        record = dock_ligand(
            **_stage_inputs(tmp_path, campaign_id, workflow),
            spawn_retry_sleep=lambda _seconds: None,
        )
        manifest = build_run_manifest(
            workflow=workflow,
            run_records=[record],
            species_catalog_sha256="a" * 64,
            attempt_manifest_sha256="b" * 64,
            software_versions={"vina": "test"},
            project_root=tmp_path,
        )
        path = tmp_path / f"{workflow}.manifest.json"
        path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        paths.append(path)
    return tuple(paths)


def test_zero_retry_campaign_seals_canonical_empty_ledger(tmp_path, monkeypatch):
    campaign_id = "zero-retry"
    paths = _write_four_stage_manifests(
        tmp_path, monkeypatch, campaign_id=campaign_id
    )

    seal = seal_campaign(tmp_path, campaign_id, paths)

    empty_hash = hashlib.sha256(b"[]").hexdigest()
    assert seal["spawn_retry_claim_count"] == 0
    assert seal["ledger_content_sha256"] == empty_hash
    assert require_campaign_seal(tmp_path, campaign_id) == seal
    ledger_dir = (
        campaign_output_dir(tmp_path, campaign_id, "wide")
        / "_operational"
        / "spawn_retry"
    )
    assert ledger_dir.is_dir()
    assert list(ledger_dir.iterdir()) == []


def test_nonempty_seal_requires_exact_ledger_manifest_claim_equality(
    tmp_path, monkeypatch
):
    campaign_id = "one-retry"
    paths = _write_four_stage_manifests(
        tmp_path,
        monkeypatch,
        campaign_id=campaign_id,
        retried_workflow="wide",
    )

    seal = seal_campaign(tmp_path, campaign_id, paths)

    assert seal["spawn_retry_claim_count"] == 1
    require_campaign_seal(tmp_path, campaign_id)


def test_seal_rejects_ledger_claim_absent_from_terminal_manifests(
    tmp_path, monkeypatch
):
    campaign_id = "ledger-manifest-mismatch"
    paths = _write_four_stage_manifests(
        tmp_path, monkeypatch, campaign_id=campaign_id
    )
    docking._register_spawn_retry_claim(
        tmp_path, campaign_id, "wide:stray:state:pocket"
    )

    with pytest.raises(InfrastructureError, match="ledger and terminal manifests differ"):
        seal_campaign(tmp_path, campaign_id, paths)

    seal_path = (
        campaign_output_dir(tmp_path, campaign_id, "wide")
        / "_operational"
        / "SEALED.json"
    )
    assert not seal_path.exists()


def test_downstream_seal_gate_detects_postseal_ledger_tampering(
    tmp_path, monkeypatch
):
    campaign_id = "seal-hash-tamper"
    paths = _write_four_stage_manifests(
        tmp_path, monkeypatch, campaign_id=campaign_id
    )
    seal_campaign(tmp_path, campaign_id, paths)
    docking._register_spawn_retry_claim(
        tmp_path, campaign_id, "wide:tampered:state:pocket"
    )

    with pytest.raises(InfrastructureError, match="ledger count mismatch"):
        require_campaign_seal(tmp_path, campaign_id)


def test_stage_sealer_race_is_lock_ordered_and_stage_rechecks_seal_inside_lock(
    tmp_path, monkeypatch
):
    campaign_id = "lock-race"
    paths = _write_four_stage_manifests(
        tmp_path, monkeypatch, campaign_id=campaign_id
    )
    stage_checked = threading.Event()
    release_stage = threading.Event()
    stage_errors = []

    def stage():
        try:
            with campaign_lock(tmp_path, campaign_id):
                require_unsealed(tmp_path, campaign_id)
                stage_checked.set()
                if not release_stage.wait(timeout=5):
                    raise AssertionError("test stage release timed out")
        except BaseException as exc:
            stage_errors.append(exc)

    thread = threading.Thread(target=stage)
    thread.start()
    assert stage_checked.wait(timeout=5)
    unreadable_paths = (*paths[:3], tmp_path / "must-not-be-read.json")
    with pytest.raises(InfrastructureError, match="lock already exists"):
        seal_campaign(tmp_path, campaign_id, unreadable_paths)
    release_stage.set()
    thread.join(timeout=5)
    assert not thread.is_alive()
    assert stage_errors == []

    seal_campaign(tmp_path, campaign_id, paths)
    with campaign_lock(tmp_path, campaign_id):
        with pytest.raises(InfrastructureError, match="is sealed"):
            require_unsealed(tmp_path, campaign_id)


def test_stage_and_downstream_entry_points_wire_the_seal_barriers():
    for script in (
        "scripts/run_docking.py",
        "scripts/run_speb_positive_control.py",
        "scripts/dock_boron_surrogates.py",
    ):
        text = Path(script).read_text(encoding="utf-8")
        lock = text.index("with campaign_lock(PROJECT_ROOT, campaign_id):")
        unsealed = text.index("require_unsealed(PROJECT_ROOT, campaign_id)", lock)
        run = text.index("_run_campaign(campaign_id, pose_dir)", unsealed)
        assert lock < unsealed < run

    for script in (
        "scripts/compute_statistics.py",
        "scripts/make_figures.py",
        "scripts/write_docking_methods.py",
    ):
        assert "require_campaign_seal(" in Path(script).read_text(encoding="utf-8")

    launcher = Path("run_campaign.sh").read_text(encoding="utf-8")
    seal_call = 'run_stage "[SEAL] CAMPAIGN BARRIER"'
    assert seal_call in launcher
    assert launcher.index(seal_call) < launcher.index("CAMPAIGN DONE")

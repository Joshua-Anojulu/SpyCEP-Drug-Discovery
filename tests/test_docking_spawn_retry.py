import copy
import hashlib
import json
import sys
from dataclasses import replace
from pathlib import Path

import pytest

import spycep_drug_discovery.docking as docking
from spycep_drug_discovery.docking import (
    CAMPAIGN_TRANSIENT_SPAWN_BUDGET,
    MAX_TRANSIENT_SPAWN_RETRIES,
    TRANSIENT_SPAWN_BACKOFF_SECONDS,
    TRANSIENT_SPAWN_STATUS_ALLOWLIST,
    WAIT_OBJECT_0,
    DockingError,
    InfrastructureError,
    SupervisedResult,
    _json_sha256,
    build_run_manifest,
    build_timeout_qc_report,
    campaign_output_dir,
    dock_ligand,
    initialize_spawn_retry_ledger,
    is_transient_spawn_failure,
    validate_manifest_timeout_qc,
    validate_run_record,
    validate_timeout_qc_gate,
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


def _transient(*, unbiased=0.0068, wall=0.007, stdout="", stderr=""):
    return SupervisedResult(
        disposition_basis="wait_signaled",
        wait_result=WAIT_OBJECT_0,
        termination_action="none",
        exit_code=0xC0000142,
        unbiased_seconds=unbiased,
        wall_seconds=wall,
        stdout=stdout,
        stderr=stderr,
    )


def _success(*, unbiased=1.0, wall=1.0):
    return SupervisedResult(
        disposition_basis="wait_signaled",
        wait_result=WAIT_OBJECT_0,
        termination_action="none",
        exit_code=0,
        unbiased_seconds=unbiased,
        wall_seconds=wall,
    )


def _inputs(tmp_path, *, campaign_id="spawn-test", entity_id="entity"):
    ligand = tmp_path / f"{entity_id}.ligand.pdbqt"
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
        "entity_id": entity_id,
        "state_id": "state_a",
        "ligand_pdbqt": ligand,
        "project_root": tmp_path,
        "output_dir": campaign_output_dir(tmp_path, campaign_id, "wide"),
        "workflow": "wide",
        "species_catalog_sha256": "a" * 64,
        "attempt_manifest_sha256": "b" * 64,
        "software_versions": {"vina": "test"},
        "campaign_id": campaign_id,
    }


def _sequence_runner(outcomes, calls):
    iterator = iter(outcomes)

    def fake(command, _timeout_seconds, **_kwargs):
        result = next(iterator)
        calls.append(result)
        if result.disposition_basis == "wait_signaled" and result.exit_code == 0:
            Path(command[command.index("--out") + 1]).write_text(
                POSE_PDBQT, encoding="utf-8"
            )
        return result

    return fake


def _run_exhaustion(tmp_path, monkeypatch):
    inputs = _inputs(tmp_path)
    initialize_spawn_retry_ledger(tmp_path, inputs["campaign_id"])
    calls = []
    outcomes = (
        _transient(),
        _transient(),
        _success(unbiased=0.5, wall=6.0),
        _transient(),
        _transient(),
    )
    monkeypatch.setattr(docking, "_run_vina_supervised", _sequence_runner(outcomes, calls))
    backoffs = []
    with pytest.raises(InfrastructureError) as caught:
        dock_ligand(**inputs, spawn_retry_sleep=backoffs.append)
    return caught.value.run_record, calls, backoffs


def test_classifier_accepts_exact_sildenafil_loader_signature():
    assert TRANSIENT_SPAWN_STATUS_ALLOWLIST == frozenset({0xC0000142})
    assert is_transient_spawn_failure(_transient(), 1800.0)


@pytest.mark.parametrize(
    "variant",
    (
        replace(_transient(), exit_code=0xC0000005),
        replace(_transient(), exit_code=0xC000013A),
        replace(_transient(), stdout="loader output"),
        replace(_transient(), stderr="loader error"),
        replace(_transient(), unbiased_seconds=1.0, wall_seconds=1.0),
        replace(_transient(), wall_seconds=5.0068),
        replace(_transient(), exit_code=0),
        replace(_transient(), exit_code=17),
        replace(_transient(), unbiased_seconds=0.5, wall_seconds=0.5),
    ),
    ids=(
        "access-violation",
        "ctrl-c",
        "stdout-present",
        "stderr-present",
        "one-second",
        "threshold-suspend",
        "success",
        "small-exit-code",
        "at-test-timeout",
    ),
)
def test_classifier_rejects_every_non_allowlisted_or_ambiguous_variant(variant):
    timeout = 0.5 if variant.unbiased_seconds == 0.5 else 1800.0
    assert not is_transient_spawn_failure(variant, timeout)


def test_nonallowlisted_instant_crash_is_fatal_and_never_retried(tmp_path, monkeypatch):
    inputs = _inputs(tmp_path)
    initialize_spawn_retry_ledger(tmp_path, inputs["campaign_id"])
    calls = []
    crash = replace(_transient(), exit_code=0xC0000005)
    monkeypatch.setattr(docking, "_run_vina_supervised", _sequence_runner((crash,), calls))
    backoffs = []

    with pytest.raises(DockingError) as caught:
        dock_ligand(**inputs, spawn_retry_sleep=backoffs.append)

    assert caught.value.run_record["cause"] == "vina_exit_nonzero"
    assert len(calls) == 1
    assert backoffs == []
    assert list((campaign_output_dir(tmp_path, inputs["campaign_id"], "wide") / "_operational" / "spawn_retry").glob("*.json")) == []


def test_retry_backoff_is_injected_and_all_three_values_are_frozen(tmp_path, monkeypatch):
    inputs = _inputs(tmp_path)
    initialize_spawn_retry_ledger(tmp_path, inputs["campaign_id"])
    calls = []
    monkeypatch.setattr(
        docking,
        "_run_vina_supervised",
        _sequence_runner((*(_transient() for _ in range(3)), _success()), calls),
    )
    backoffs = []

    record = dock_ligand(**inputs, spawn_retry_sleep=backoffs.append)

    assert backoffs == list(TRANSIENT_SPAWN_BACKOFF_SECONDS) == [2.0, 5.0, 10.0]
    assert record["spawn_retry_count"] == MAX_TRANSIENT_SPAWN_RETRIES == 3
    assert len(calls) == 4


def test_spawn_budget_is_cumulative_across_suspend_iterations_and_exhaustion_aborts(
    tmp_path, monkeypatch
):
    record, calls, backoffs = _run_exhaustion(tmp_path, monkeypatch)

    assert len(calls) == 5
    assert backoffs == [2.0, 5.0, 10.0]
    assert record["failure_stage"] == "transient_spawn_failure_exhausted"
    assert record["spawn_retry_count"] == 3
    assert len(record["spawn_failures"]) == 3
    validate_run_record(record, allow_infrastructure=True)
    selection = json.loads(
        (tmp_path / record["selection_manifest_path"]).read_text(encoding="utf-8")
    )
    assert selection["status"] == "blocked_infrastructure_failure"
    assert len(selection["quarantined_attempts"]) == 1
    assert len(selection["spawn_failure_attempts"]) == 3


def test_exhaustion_terminal_never_overwrites_transient_predecessors(
    tmp_path, monkeypatch
):
    record, _, _ = _run_exhaustion(tmp_path, monkeypatch)

    for predecessor in record["spawn_failures"]:
        path = tmp_path / predecessor["sidecar_path"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == predecessor[
            "sidecar_sha256"
        ]
        sidecar = json.loads(path.read_text(encoding="utf-8"))
        assert sidecar["status"] == "failed"
        assert sidecar["cause"] == "transient_spawn_failure"
        assert sidecar["exit_code"] == 0xC0000142
        assert sidecar["failure_stage"] is None


def test_independent_retry_budgets_have_a_six_supervisor_call_ceiling(
    tmp_path, monkeypatch
):
    inputs = _inputs(tmp_path)
    initialize_spawn_retry_ledger(tmp_path, inputs["campaign_id"])
    calls = []
    outcomes = (
        _transient(),
        _transient(),
        _transient(),
        _success(unbiased=0.5, wall=6.0),
        _success(unbiased=0.5, wall=6.0),
        _success(),
    )
    monkeypatch.setattr(docking, "_run_vina_supervised", _sequence_runner(outcomes, calls))

    record = dock_ligand(**inputs, spawn_retry_sleep=lambda _seconds: None)

    assert len(calls) == 6
    assert record["spawn_retry_count"] == 3
    assert len(record["quarantined_predecessors"]) == 2


def test_every_selection_write_carries_both_histories_through_interleave(
    tmp_path, monkeypatch
):
    inputs = _inputs(tmp_path)
    initialize_spawn_retry_ledger(tmp_path, inputs["campaign_id"])
    calls = []
    outcomes = (
        _success(unbiased=0.5, wall=6.0),
        _transient(),
        _success(),
    )
    monkeypatch.setattr(docking, "_run_vina_supervised", _sequence_runner(outcomes, calls))
    real_atomic_json = docking._atomic_json
    selections = []

    def capture(path, value):
        if path.name.endswith(".selection.json"):
            selections.append(copy.deepcopy(value))
        real_atomic_json(path, value)

    monkeypatch.setattr(docking, "_atomic_json", capture)
    record = dock_ligand(**inputs, spawn_retry_sleep=lambda _seconds: None)

    assert [selection["status"] for selection in selections] == [
        "retrying",
        "retrying_spawn",
        "authoritative_selected",
    ]
    assert all(
        "quarantined_attempts" in selection
        and "spawn_failure_attempts" in selection
        and selection["selection_schema_version"] == "docking-selection-manifest-v2"
        for selection in selections
    )
    assert [
        (len(selection["quarantined_attempts"]), len(selection["spawn_failure_attempts"]))
        for selection in selections
    ] == [(1, 0), (1, 1), (1, 1)]
    assert record["spawn_retry_count"] == 1


def test_generic_supervisor_raise_finalizes_bound_helper_context(tmp_path, monkeypatch):
    inputs = _inputs(tmp_path)
    initialize_spawn_retry_ledger(tmp_path, inputs["campaign_id"])

    def fail(*_args, **_kwargs):
        raise RuntimeError("synthetic unexpected supervisor failure")

    monkeypatch.setattr(docking, "_run_vina_supervised", fail)
    with pytest.raises(InfrastructureError) as caught:
        dock_ligand(**inputs, spawn_retry_sleep=lambda _seconds: None)

    record = caught.value.run_record
    assert record["failure_stage"] == "supervisor_exception"
    assert record["attempt_instance_id"] in record["sidecar_path"]
    assert (tmp_path / record["sidecar_path"]).is_file()
    selection = json.loads(
        (tmp_path / record["selection_manifest_path"]).read_text(encoding="utf-8")
    )
    assert selection["quarantined_attempts"] == []
    assert selection["spawn_failure_attempts"] == []


def test_ledger_filename_is_sha256_of_full_colon_claim_key(tmp_path):
    campaign_id = "ledger-name"
    ledger_dir = initialize_spawn_retry_ledger(tmp_path, campaign_id)
    claim_key = "wide:entity:state_a:fake_pocket"

    docking._register_spawn_retry_claim(tmp_path, campaign_id, claim_key)

    path = next(ledger_dir.iterdir())
    assert path.name == hashlib.sha256(claim_key.encode("utf-8")).hexdigest() + ".json"
    assert json.loads(path.read_text(encoding="utf-8"))["claim_key"] == claim_key
    assert ":" not in path.name


def test_corrupt_spawn_retry_ledger_aborts_fail_closed(tmp_path):
    campaign_id = "ledger-corrupt"
    ledger_dir = initialize_spawn_retry_ledger(tmp_path, campaign_id)
    (ledger_dir / "corrupt.json").write_text("{not json", encoding="utf-8")

    with pytest.raises(InfrastructureError, match="Unreadable"):
        docking._register_spawn_retry_claim(tmp_path, campaign_id, "wide:e:s:p")


def test_per_campaign_distinct_claim_budget_aborts_before_eleventh_write(tmp_path):
    campaign_id = "ledger-budget"
    ledger_dir = initialize_spawn_retry_ledger(tmp_path, campaign_id)
    for index in range(CAMPAIGN_TRANSIENT_SPAWN_BUDGET):
        docking._register_spawn_retry_claim(
            tmp_path, campaign_id, f"wide:entity-{index}:state:pocket"
        )

    with pytest.raises(InfrastructureError, match="host is degrading"):
        docking._register_spawn_retry_claim(
            tmp_path, campaign_id, "wide:entity-11:state:pocket"
        )

    assert len(list(ledger_dir.glob("*.json"))) == CAMPAIGN_TRANSIENT_SPAWN_BUDGET


def test_degrading_host_budget_persists_valid_infrastructure_terminal_and_aborts(
    tmp_path, monkeypatch
):
    inputs = _inputs(tmp_path, campaign_id="degrading-host", entity_id="blocked")
    initialize_spawn_retry_ledger(tmp_path, inputs["campaign_id"])
    for index in range(CAMPAIGN_TRANSIENT_SPAWN_BUDGET):
        docking._register_spawn_retry_claim(
            tmp_path,
            inputs["campaign_id"],
            f"wide:earlier-{index}:state:pocket",
        )
    calls = []
    monkeypatch.setattr(
        docking,
        "_run_vina_supervised",
        _sequence_runner((_transient(),), calls),
    )

    with pytest.raises(InfrastructureError) as caught:
        dock_ligand(**inputs, spawn_retry_sleep=lambda _seconds: None)

    record = caught.value.run_record
    assert len(calls) == 1
    assert record["failure_stage"] == "campaign_transient_spawn_budget_exceeded"
    assert record["status"] == record["cause"] == "infrastructure_failure"
    assert record["spawn_retry_count"] == 0
    validate_run_record(record, allow_infrastructure=True)
    assert json.loads(
        (tmp_path / record["sidecar_path"]).read_text(encoding="utf-8")
    ) == record


def test_generation_qc_verifies_predecessor_sidecar_hash_and_signature(
    tmp_path, monkeypatch
):
    inputs = _inputs(tmp_path)
    initialize_spawn_retry_ledger(tmp_path, inputs["campaign_id"])
    calls = []
    monkeypatch.setattr(
        docking,
        "_run_vina_supervised",
        _sequence_runner((_transient(), _success()), calls),
    )
    record = dock_ligand(**inputs, spawn_retry_sleep=lambda _seconds: None)

    report = build_timeout_qc_report([record], project_root=tmp_path)
    validate_timeout_qc_gate(report)
    assert report["spawn_failure_attempt_count"] == 1
    assert report["spawn_failure_attempts"][0]["sidecar_sha256"] == record[
        "spawn_failures"
    ][0]["sidecar_sha256"]

    predecessor_path = tmp_path / record["spawn_failures"][0]["sidecar_path"]
    predecessor_path.write_text(
        predecessor_path.read_text(encoding="utf-8") + " ", encoding="utf-8"
    )
    invalid = build_timeout_qc_report([record], project_root=tmp_path)
    with pytest.raises(DockingError, match="invalid records"):
        validate_timeout_qc_gate(invalid)


def test_downstream_manifest_gate_recomputes_spawn_history_from_embedded_hashes(
    tmp_path, monkeypatch
):
    inputs = _inputs(tmp_path)
    initialize_spawn_retry_ledger(tmp_path, inputs["campaign_id"])
    calls = []
    monkeypatch.setattr(
        docking,
        "_run_vina_supervised",
        _sequence_runner((_transient(), _success()), calls),
    )
    record = dock_ligand(**inputs, spawn_retry_sleep=lambda _seconds: None)
    manifest = build_run_manifest(
        workflow="wide",
        run_records=[record],
        species_catalog_sha256="a" * 64,
        attempt_manifest_sha256="b" * 64,
        software_versions={"vina": "test"},
        project_root=tmp_path,
    )
    validate_manifest_timeout_qc(manifest)

    tampered = copy.deepcopy(manifest)
    report = tampered["timeout_qc"]
    report["spawn_failure_attempts"] = []
    report["spawn_failure_attempt_count"] = 0
    report["attempts"] = [
        row
        for row in report["attempts"]
        if row.get("selection_status") != "spawn_retry_predecessor"
    ]
    payload = {key: value for key, value in report.items() if key != "report_sha256"}
    report["report_sha256"] = _json_sha256(payload)
    tampered["timeout_qc_sha256"] = report["report_sha256"]

    with pytest.raises(DockingError, match="run records and timeout-QC"):
        validate_manifest_timeout_qc(tampered)

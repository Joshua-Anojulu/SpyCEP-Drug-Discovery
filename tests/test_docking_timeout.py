import copy
import json
import sys
from pathlib import Path

import pytest

import spycep_drug_discovery.docking as docking_module

from spycep_drug_discovery.docking import (
    CLOCK_SOURCE,
    DEFAULT_TIMEOUT_MS,
    DEFAULT_TIMEOUT_SECONDS,
    MAX_SUSPENDED_RETRIES,
    RUN_SCHEMA_VERSION,
    STILL_ACTIVE,
    SUSPEND_THRESHOLD,
    TIMEOUT_BASIS,
    WAIT_MECHANISM,
    WAIT_OBJECT_0,
    WAIT_TIMEOUT,
    DockingError,
    InfrastructureError,
    SupervisedResult,
    _SupervisorInfrastructureError,
    _query_unbiased_interrupt_time,
    _run_vina_supervised,
    build_timeout_qc_report,
    dock_ligand,
    is_continuable_scientific_disposition,
    validate_run_record,
    validate_suspend_calibration,
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

    monkeypatch.setattr(
        "spycep_drug_discovery.docking._run_vina_supervised", forbidden
    )


def _inputs(tmp_path):
    ligand = tmp_path / "ligand.pdbqt"
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
        "entity_id": "entity",
        "state_id": "state_a",
        "ligand_pdbqt": ligand,
        "project_root": tmp_path,
        "output_dir": tmp_path / "campaign" / "wide",
        "workflow": "wide",
        "species_catalog_sha256": "a" * 64,
        "attempt_manifest_sha256": "b" * 64,
        "software_versions": {"vina": "test"},
        "campaign_id": "test-campaign",
    }


def _result(
    *,
    basis="wait_signaled",
    exit_code=0,
    unbiased=1.0,
    wall=1.0,
):
    return SupervisedResult(
        disposition_basis=basis,
        wait_result=WAIT_TIMEOUT if basis == "deadline_timeout" else WAIT_OBJECT_0,
        termination_action=(
            "TerminateJobObject" if basis == "deadline_timeout" else "none"
        ),
        exit_code=None if basis == "deadline_timeout" else exit_code,
        unbiased_seconds=unbiased,
        wall_seconds=wall,
    )


def _pose_then(result):
    def fake(command, _timeout_seconds, **_kwargs):
        if result.disposition_basis == "wait_signaled" and result.exit_code == 0:
            out_path = Path(command[command.index("--out") + 1])
            out_path.write_text(POSE_PDBQT, encoding="utf-8")
        return result

    return fake


def _valid_record(tmp_path, monkeypatch, *, unbiased=1.0, wall=1.0):
    monkeypatch.setattr(
        "spycep_drug_discovery.docking._run_vina_supervised",
        _pose_then(_result(unbiased=unbiased, wall=wall)),
    )
    return dock_ligand(**_inputs(tmp_path))


def test_frozen_timeout_method_constants_are_exact():
    assert RUN_SCHEMA_VERSION == "docking-run-record-v2"
    assert DEFAULT_TIMEOUT_SECONDS == 1800.0
    assert DEFAULT_TIMEOUT_MS == 1800000
    assert SUSPEND_THRESHOLD == 5.0
    assert MAX_SUSPENDED_RETRIES == 2
    assert TIMEOUT_BASIS == "unbiased_wall_seconds"
    assert CLOCK_SOURCE == "QueryUnbiasedInterruptTime"
    assert WAIT_MECHANISM == "single_armed_WaitForSingleObject"


def test_calibration_is_an_abort_gate_and_never_changes_threshold():
    calibration = {
        "calibration_schema_version": "docking-suspend-calibration-v1",
        "duration_seconds": 600.0,
        "load": "single_core_docking_equivalent",
        "cpu": 1,
        "max_observed_drift_seconds": 0.5,
        "suspend_threshold_seconds": 5.0,
    }
    validate_suspend_calibration(calibration)

    calibration["max_observed_drift_seconds"] = 0.500001
    with pytest.raises(InfrastructureError, match="0.5 s abort gate"):
        validate_suspend_calibration(calibration)

    calibration["max_observed_drift_seconds"] = 0.1
    calibration["suspend_threshold_seconds"] = 6.0
    with pytest.raises(InfrastructureError, match="fixed threshold"):
        validate_suspend_calibration(calibration)


def test_wait_timeout_is_canonical_scientific_timeout(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "spycep_drug_discovery.docking._run_vina_supervised",
        _pose_then(_result(basis="deadline_timeout", unbiased=1800.0, wall=1800.0)),
    )
    with pytest.raises(DockingError) as caught:
        dock_ligand(**_inputs(tmp_path))

    record = caught.value.run_record
    assert record["status"] == "no_fit"
    assert record["cause"] == "timeout"
    assert record["disposition_basis"] == "deadline_timeout"
    assert record["wait_result"] == WAIT_TIMEOUT
    assert record["termination_action"] == "TerminateJobObject"
    assert is_continuable_scientific_disposition(record)


def test_timely_signaled_completion_is_valid_not_timeout(tmp_path, monkeypatch):
    record = _valid_record(tmp_path, monkeypatch, unbiased=1799.0, wall=1799.0)

    assert record["status"] == "valid_fit"
    assert record["disposition_basis"] == "wait_signaled"
    assert record["wait_result"] == WAIT_OBJECT_0
    assert record["exit_code"] == 0
    assert record["timing_ambiguous"] is False


def test_signaled_nonzero_exit_preserves_vina_exit_nonzero(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "spycep_drug_discovery.docking._run_vina_supervised",
        _pose_then(_result(exit_code=17, unbiased=3.0, wall=3.0)),
    )
    with pytest.raises(DockingError) as caught:
        dock_ligand(**_inputs(tmp_path))

    record = caught.value.run_record
    assert record["status"] == "failed"
    assert record["cause"] == "vina_exit_nonzero"
    assert record["disposition_basis"] == "wait_signaled"
    assert record["exit_code"] == 17
    assert not is_continuable_scientific_disposition(record)


def test_sleep_touched_attempt_is_quarantined_and_new_instance_selected(
    tmp_path, monkeypatch
):
    outcomes = iter(
        (
            _result(unbiased=10.0, wall=1000.0),
            _result(unbiased=11.0, wall=11.0),
        )
    )

    def fake(command, _timeout_seconds, **_kwargs):
        result = next(outcomes)
        Path(command[command.index("--out") + 1]).write_text(
            POSE_PDBQT, encoding="utf-8"
        )
        return result

    monkeypatch.setattr(
        "spycep_drug_discovery.docking._run_vina_supervised", fake
    )
    record = dock_ligand(**_inputs(tmp_path))

    predecessor = record["quarantined_predecessors"][0]
    assert predecessor["suspend_detected"] is True
    assert predecessor["quarantine_reason"] == "suspend_detected"
    assert predecessor["selection_status"] == "quarantined_superseded"
    assert predecessor["attempt_instance_id"] != record["attempt_instance_id"]
    assert record["authoritative_selected"] is True


@pytest.mark.parametrize("ambiguous_exit_code", [0, 23])
def test_over_ceiling_signaled_result_is_ambiguous_and_never_accepted(
    tmp_path, monkeypatch, ambiguous_exit_code
):
    outcomes = iter(
        (
            _result(exit_code=ambiguous_exit_code, unbiased=1800.0, wall=1800.0),
            _result(unbiased=1.0, wall=1.0),
        )
    )

    def fake(command, _timeout_seconds, **_kwargs):
        result = next(outcomes)
        if result.exit_code == 0:
            Path(command[command.index("--out") + 1]).write_text(
                POSE_PDBQT, encoding="utf-8"
            )
        return result

    monkeypatch.setattr(
        "spycep_drug_discovery.docking._run_vina_supervised", fake
    )
    record = dock_ligand(**_inputs(tmp_path))

    predecessor = record["quarantined_predecessors"][0]
    assert predecessor["timing_ambiguous"] is True
    assert predecessor["quarantine_reason"] == "timing_ambiguous"
    assert predecessor["selection_status"] == "quarantined_superseded"


@pytest.mark.parametrize(
    "failure_stage",
    ["CreateJobObjectW", "CreateProcessW", "GetExitCodeProcess"],
)
def test_supervisor_failure_writes_infrastructure_record_and_aborts(
    tmp_path, monkeypatch, failure_stage
):
    def fail(*_args, **_kwargs):
        raise _SupervisorInfrastructureError(
            "synthetic native failure",
            failure_stage=failure_stage,
            win32_error=5,
            cleanup_outcome={"job_terminated": True, "child_reaped": True},
        )

    monkeypatch.setattr(
        "spycep_drug_discovery.docking._run_vina_supervised", fail
    )
    with pytest.raises(InfrastructureError) as caught:
        dock_ligand(**_inputs(tmp_path))

    record = caught.value.run_record
    assert record["status"] == "infrastructure_failure"
    assert record["cause"] == "infrastructure_failure"
    assert record["disposition_basis"] == "infrastructure_failure"
    assert record["failure_stage"] == failure_stage
    assert record["win32_error"] == 5
    assert record["authoritative_selected"] is False
    assert json.loads(
        (tmp_path / record["sidecar_path"]).read_text(encoding="utf-8")
    )["failure_stage"] == failure_stage
    assert not is_continuable_scientific_disposition(record)


def test_validator_rejects_bidirectional_canonical_mapping_violation(
    tmp_path, monkeypatch
):
    record = _valid_record(tmp_path, monkeypatch)
    record.update(
        {
            "disposition_basis": "deadline_timeout",
            "wait_result": WAIT_TIMEOUT,
            "termination_action": "TerminateJobObject",
            "exit_code": None,
        }
    )

    with pytest.raises(DockingError, match="canonical no_fit/timeout"):
        validate_run_record(record)


def test_validator_recomputes_timing_ambiguity_and_bars_selection(
    tmp_path, monkeypatch
):
    record = _valid_record(tmp_path, monkeypatch)
    record.update(
        {
            "elapsed_seconds": 1800.0,
            "wall_seconds": 1800.0,
            "unbiased_seconds": 1800.0,
            "suspend_gap_seconds": 0.0,
            "timing_ambiguous": False,
        }
    )
    with pytest.raises(DockingError, match="timing_ambiguous"):
        validate_run_record(record)

    record["timing_ambiguous"] = True
    with pytest.raises(DockingError, match="cannot be authoritative"):
        validate_run_record(record)

    record["authoritative_selected"] = False
    validate_run_record(record)


def test_validator_accepts_signaled_record_strictly_under_timeout(
    tmp_path, monkeypatch
):
    record = _valid_record(tmp_path, monkeypatch, unbiased=1799.999, wall=1799.999)
    validate_run_record(record)


def _deadline_record_from(record):
    value = copy.deepcopy(record)
    value.update(
        {
            "elapsed_seconds": 10.0,
            "wall_seconds": 10.0,
            "unbiased_seconds": 3.0,
            "suspend_gap_seconds": 7.0,
            "suspend_detected": False,
            "timing_ambiguous": False,
            "status": "no_fit",
            "cause": "timeout",
            "valid_fit": False,
            "disposition_basis": "deadline_timeout",
            "wait_result": WAIT_TIMEOUT,
            "termination_action": "TerminateJobObject",
            "exit_code": None,
            "authoritative_selected": False,
        }
    )
    return value


def test_validator_recomputes_suspend_for_deadline_timeout(tmp_path, monkeypatch):
    record = _deadline_record_from(_valid_record(tmp_path, monkeypatch))
    with pytest.raises(DockingError, match="suspend_detected"):
        validate_run_record(record)

    record["suspend_detected"] = True
    validate_run_record(record)
    record["authoritative_selected"] = True
    with pytest.raises(DockingError, match="cannot be authoritative"):
        validate_run_record(record)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("wall_seconds", float("nan")),
        ("unbiased_seconds", float("inf")),
        ("unbiased_seconds", -1.0),
    ],
)
def test_validator_rejects_invalid_numeric_domains(
    tmp_path, monkeypatch, field, value
):
    record = _valid_record(tmp_path, monkeypatch)
    record[field] = value
    with pytest.raises(DockingError):
        validate_run_record(record)


def test_infrastructure_record_always_blocks_validator(tmp_path, monkeypatch):
    def fail(*_args, **_kwargs):
        raise _SupervisorInfrastructureError(
            "failure",
            failure_stage="WaitForSingleObject",
            cleanup_outcome={"job_terminated": True},
        )

    monkeypatch.setattr(
        "spycep_drug_discovery.docking._run_vina_supervised", fail
    )
    with pytest.raises(InfrastructureError) as caught:
        dock_ligand(**_inputs(tmp_path))
    record = caught.value.run_record

    validate_run_record(record, allow_infrastructure=True)
    with pytest.raises(InfrastructureError, match="blocks the campaign"):
        validate_run_record(record)


def test_qc_report_is_content_addressed_and_gate_rejects_unresolved(
    tmp_path, monkeypatch
):
    record = _valid_record(tmp_path, monkeypatch)
    report = build_timeout_qc_report([record])
    validate_timeout_qc_gate(report)

    report = copy.deepcopy(report)
    report["unresolved_quarantine_count"] = 1
    payload = {key: value for key, value in report.items() if key != "report_sha256"}
    from spycep_drug_discovery.docking import _json_sha256

    report["report_sha256"] = _json_sha256(payload)
    with pytest.raises(DockingError, match="unresolved quarantines"):
        validate_timeout_qc_gate(report)


def test_wait_signaled_rejects_still_active_exit_code(tmp_path, monkeypatch):
    record = _valid_record(tmp_path, monkeypatch)
    record["exit_code"] = STILL_ACTIVE
    with pytest.raises(DockingError, match="terminal exit code"):
        validate_run_record(record)


@pytest.mark.skipif(sys.platform != "win32", reason="Win32 supervisor smoke test")
def test_win32_supervisor_smoke_success_and_error_cleanup(tmp_path):
    first = _query_unbiased_interrupt_time()
    second = _query_unbiased_interrupt_time()
    assert isinstance(first, int) and 0 <= first <= second < 2**64

    result = _run_vina_supervised(
        [sys.executable, "-c", "print('win32 supervisor smoke')"],
        10.0,
        cwd=tmp_path,
        temp_dir=tmp_path,
    )
    assert result.disposition_basis == "wait_signaled"
    assert result.exit_code == 0
    assert "win32 supervisor smoke" in result.stdout
    assert result.cleanup_outcome["attribute_list_deleted"] is True
    assert result.cleanup_outcome["child_reaped"] is True
    assert {"job", "process", "thread", "stdin", "stdout", "stderr"}.issubset(
        result.cleanup_outcome["handles_closed"]
    )

    with pytest.raises(_SupervisorInfrastructureError) as caught:
        _run_vina_supervised(
            [tmp_path / "does-not-exist.exe"],
            10.0,
            cwd=tmp_path,
            temp_dir=tmp_path,
        )
    assert caught.value.failure_stage == "CreateProcessW"
    assert caught.value.cleanup_outcome["attribute_list_deleted"] is True
    assert caught.value.cleanup_outcome["job_terminated"] is True
    assert {"job", "stdin", "stdout", "stderr"}.issubset(
        caught.value.cleanup_outcome["handles_closed"]
    )
    assert not list(tmp_path.glob("vina-supervisor-*.log"))


@pytest.mark.skipif(sys.platform != "win32", reason="Win32 Job accounting test")
def test_job_accounting_is_default_disabled_for_ordinary_calls(tmp_path):
    result = _run_vina_supervised(
        [sys.executable, "-c", "pass"],
        10.0,
        cwd=tmp_path,
        temp_dir=tmp_path,
    )
    assert result.disposition_basis == "wait_signaled"
    assert result.job_cpu_seconds is None
    assert result.load_window_unbiased_seconds is None


@pytest.mark.skipif(sys.platform != "win32", reason="Win32 Job accounting test")
def test_job_accounting_prestart_cpu_cannot_escape_denominator_and_end_follows_reap(
    tmp_path, monkeypatch
):
    real_bindings_type = docking_module._Win32Bindings
    events = []

    class TracingBindings:
        def __init__(self):
            self._real = real_bindings_type()

        def __getattr__(self, name):
            return getattr(self._real, name)

        def QueryUnbiasedInterruptTime(self, *args):
            events.append("unbiased")
            return self._real.QueryUnbiasedInterruptTime(*args)

        def ResumeThread(self, *args):
            events.append("resume")
            return self._real.ResumeThread(*args)

        def WaitForSingleObject(self, handle, timeout_ms):
            events.append("reap" if timeout_ms == 5000 else "armed_wait")
            return self._real.WaitForSingleObject(handle, timeout_ms)

        def TerminateJobObject(self, *args):
            events.append("terminate")
            return self._real.TerminateJobObject(*args)

        def QueryInformationJobObject(self, *args):
            events.append("accounting_query")
            return self._real.QueryInformationJobObject(*args)

    monkeypatch.setattr(docking_module, "_Win32Bindings", TracingBindings)
    result = _run_vina_supervised(
        [sys.executable, "-c", "while True: pass"],
        0.2,
        cwd=tmp_path,
        temp_dir=tmp_path,
        collect_job_accounting=True,
    )

    assert result.disposition_basis == "deadline_timeout"
    assert result.job_cpu_seconds is not None and result.job_cpu_seconds > 0
    assert result.load_window_unbiased_seconds is not None
    assert result.load_window_unbiased_seconds >= 0.2
    assert result.cleanup_outcome["job_terminated"] is True
    assert result.cleanup_outcome["child_reaped"] is True

    resume = events.index("resume")
    terminate = events.index("terminate")
    reap = events.index("reap")
    query = events.index("accounting_query")
    assert events[resume - 1] == "unbiased"
    assert terminate < reap < query
    assert events[query + 1] == "unbiased"
    assert not list(tmp_path.glob("vina-supervisor-*.log"))

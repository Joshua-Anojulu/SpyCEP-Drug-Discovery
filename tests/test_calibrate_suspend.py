import importlib
import json
import os
import sys
import threading
import time
from contextlib import contextmanager
from pathlib import Path

import pytest

from scripts import calibrate_suspend as calibration
from spycep_drug_discovery.docking import (
    WAIT_TIMEOUT,
    InfrastructureError,
    SupervisedResult,
    validate_suspend_calibration,
)


def _sample(
    ordinal,
    wall,
    nonprecise,
    *,
    precise=None,
    nonprecise_width=0.0,
    precise_width=0.0,
    terminal=False,
):
    precise = nonprecise if precise is None else precise
    return calibration.ClockSample(
        ordinal=ordinal,
        scheduled_index=None if terminal else ordinal,
        terminal=terminal,
        nonprecise_1_seconds=nonprecise - nonprecise_width / 2.0,
        precise_1_seconds=precise - precise_width / 2.0,
        wall_seconds=wall,
        precise_2_seconds=precise + precise_width / 2.0,
        nonprecise_2_seconds=nonprecise + nonprecise_width / 2.0,
    )


def _series(count=590, step=600.0 / 589.0):
    return [
        _sample(i, i * step, i * step, terminal=i == count - 1)
        for i in range(count)
    ]


def _supervised(cpu, window, *, basis="deadline_timeout"):
    return SupervisedResult(
        disposition_basis=basis,
        wait_result=WAIT_TIMEOUT,
        termination_action="TerminateJobObject",
        exit_code=None,
        unbiased_seconds=600.0,
        wall_seconds=600.0,
        job_cpu_seconds=cpu,
        load_window_unbiased_seconds=window,
        cleanup_outcome={"job_terminated": True, "child_reaped": True},
    )


def _install_successful_calibration_seams(monkeypatch):
    @contextmanager
    def no_results_lock(_project_root, _campaign_id):
        yield

    def emit_valid_pass(_project_root, campaign_id, target):
        record = {
            "calibration_schema_version": calibration.CALIBRATION_SCHEMA_VERSION,
            "duration_seconds": 600.0,
            "load": calibration.LOAD_NAME,
            "cpu": 1,
            "max_observed_drift_seconds": 0.001,
            "suspend_threshold_seconds": 5.0,
            "campaign_id": campaign_id,
        }
        validate_suspend_calibration(record)
        calibration._atomic_json_no_replace(target, record)
        return target

    monkeypatch.setenv("SPYCEP_CAMPAIGN_ID", "lock-release-test")
    monkeypatch.setattr(calibration, "_require_windows", lambda: None)
    monkeypatch.setattr(calibration, "campaign_lock", no_results_lock)
    monkeypatch.setattr(
        calibration, "_perform_locked_calibration", emit_valid_pass
    )


def test_frozen_measurement_constants_are_exact():
    assert calibration.CPU_UTILIZATION_FLOOR == 0.90
    assert calibration.CPU_UTILIZATION_CEILING == 1.10
    assert calibration.SAMPLE_CADENCE_SECONDS == 1.0
    assert calibration.MAX_INTERSAMPLE_GAP_SECONDS == 5.0
    assert calibration.MIN_SAMPLE_COUNT == 590
    assert calibration.NEGATIVE_EXCURSION_TOLERANCE_SECONDS == 0.5


@pytest.mark.skipif(sys.platform != "win32", reason="real Windows clock binding")
def test_real_kernelbase_precise_clock_binding_is_nonzero_and_monotonic():
    bindings = calibration._Win32Bindings()
    calibration._configure_precise_clock(bindings)

    first = calibration._query_precise_unbiased_interrupt_time(bindings)
    second = calibration._query_precise_unbiased_interrupt_time(bindings)

    assert bindings.QueryUnbiasedInterruptTimePrecise.restype is None
    assert isinstance(first, int) and 0 < first <= second < 2**64


def test_precise_clock_binding_failure_has_an_explicit_stage():
    class BrokenCtypes:
        @staticmethod
        def WinDLL(*_args, **_kwargs):
            raise OSError("synthetic missing KernelBase export")

    class BrokenBindings:
        ctypes = BrokenCtypes

    with pytest.raises(
        calibration.CalibrationFailure,
        match="QueryUnbiasedInterruptTimePrecise",
    ) as caught:
        calibration._configure_precise_clock(BrokenBindings())
    assert caught.value.failure_stage == "precise-clock-binding"


def test_precise_clock_binding_failure_emits_staged_invalid_artifact(
    tmp_path, monkeypatch
):
    class BrokenCtypes:
        @staticmethod
        def WinDLL(*_args, **_kwargs):
            raise OSError("synthetic missing KernelBase export")

    class BrokenBindings:
        ctypes = BrokenCtypes

    @contextmanager
    def no_results_lock(_project_root, _campaign_id):
        yield

    def fail_during_binding(*_args, **_kwargs):
        calibration._configure_precise_clock(BrokenBindings())

    monkeypatch.setenv("SPYCEP_CAMPAIGN_ID", "binding-failure-test")
    monkeypatch.setattr(calibration, "_require_windows", lambda: None)
    monkeypatch.setattr(calibration, "campaign_lock", no_results_lock)
    monkeypatch.setattr(
        calibration, "_perform_locked_calibration", fail_during_binding
    )

    with pytest.raises(calibration.CalibrationFailure) as caught:
        calibration.run_calibration(tmp_path)

    artifact = caught.value.artifact_path
    assert artifact is not None and artifact.is_file()
    record = json.loads(artifact.read_text(encoding="utf-8"))
    assert record["failure_stage"] == "precise-clock-binding"
    with pytest.raises(InfrastructureError):
        validate_suspend_calibration(record)


def test_transient_launcher_lock_release_permission_error_retries_and_passes(
    tmp_path, monkeypatch, capsys
):
    _install_successful_calibration_seams(monkeypatch)
    real_remove = calibration._remove_launcher_lock_directory
    calls = []
    sleeps = []

    def transient_remove(lock_path):
        calls.append(lock_path)
        if len(calls) < 3:
            raise PermissionError(5, "synthetic OneDrive handle", str(lock_path))
        real_remove(lock_path)

    monkeypatch.setattr(
        calibration, "_remove_launcher_lock_directory", transient_remove
    )
    monkeypatch.setattr(calibration.time, "sleep", sleeps.append)

    artifact = calibration.run_calibration(tmp_path)

    assert artifact.is_file()
    validate_suspend_calibration(json.loads(artifact.read_text(encoding="utf-8")))
    assert len(calls) == 3
    assert sleeps == [
        calibration.LAUNCHER_LOCK_RELEASE_BACKOFF_SECONDS,
        calibration.LAUNCHER_LOCK_RELEASE_BACKOFF_SECONDS,
    ]
    assert not (tmp_path / ".campaign.lock").exists()
    assert "LOCK-CLEANUP WARNING" not in capsys.readouterr().err


def test_persistent_launcher_lock_release_error_warns_but_preserves_pass(
    tmp_path, monkeypatch, capsys
):
    _install_successful_calibration_seams(monkeypatch)
    calls = []
    sleeps = []

    def persistent_remove(lock_path):
        calls.append(lock_path)
        raise PermissionError(5, "synthetic persistent handle", str(lock_path))

    monkeypatch.setattr(
        calibration, "_remove_launcher_lock_directory", persistent_remove
    )
    monkeypatch.setattr(calibration.time, "sleep", sleeps.append)

    artifact = calibration.run_calibration(tmp_path)
    warning = capsys.readouterr().err

    assert artifact.is_file()
    validate_suspend_calibration(json.loads(artifact.read_text(encoding="utf-8")))
    assert len(calls) == calibration.LAUNCHER_LOCK_RELEASE_ATTEMPTS
    assert len(sleeps) == calibration.LAUNCHER_LOCK_RELEASE_ATTEMPTS - 1
    assert (tmp_path / ".campaign.lock").is_dir()
    assert "CALIBRATION PASSED AND THE VALIDATOR-ACCEPTED ARTIFACT IS INTACT" in warning
    assert "NOT HOST DRIFT OR CALIBRATION FAILURE" in warning
    assert str(tmp_path / ".campaign.lock") in warning
    assert "rmdir .campaign.lock" in warning

    # The production code deliberately does not force-delete a persistent lock.
    (tmp_path / ".campaign.lock").rmdir()


def test_launcher_lock_acquisition_failure_still_aborts(tmp_path, monkeypatch):
    monkeypatch.setenv("SPYCEP_CAMPAIGN_ID", "lock-acquisition-test")
    monkeypatch.setattr(calibration, "_require_windows", lambda: None)
    lock_path = tmp_path / ".campaign.lock"
    lock_path.mkdir()
    called = False

    def forbidden_perform(*_args, **_kwargs):
        nonlocal called
        called = True
        raise AssertionError("calibration ran despite acquisition failure")

    monkeypatch.setattr(
        calibration, "_perform_locked_calibration", forbidden_perform
    )

    with pytest.raises(
        calibration.CalibrationFailure,
        match="Launcher lock already exists",
    ) as caught:
        calibration.run_calibration(tmp_path)

    assert caught.value.failure_stage == "lock"
    assert caught.value.artifact_path is not None
    assert caught.value.artifact_path.is_file()
    assert called is False
    assert lock_path.is_dir()


def test_each_sample_read_order_is_nonprecise_precise_wall_precise_nonprecise():
    events = []

    class Cell:
        def __init__(self):
            self.value = 0

    class FakeCtypes:
        c_ulonglong = Cell

        @staticmethod
        def byref(value):
            return value

        @staticmethod
        def set_last_error(_value):
            pass

        @staticmethod
        def get_last_error():
            return 0

    class Bindings:
        ctypes = FakeCtypes

        def QueryUnbiasedInterruptTime(self, value):
            events.append("n")
            value.value = 10 if events.count("n") == 1 else 20
            return True

        def QueryUnbiasedInterruptTimePrecise(self, value):
            events.append("p")
            value.value = 11 if events.count("p") == 1 else 12
            return True

    def wall_clock():
        events.append("w")
        return 1.5

    sample = calibration._take_clock_sample(
        Bindings(),
        ordinal=0,
        scheduled_index=0,
        terminal=False,
        wall_clock=wall_clock,
    )
    assert events == ["n", "p", "w", "p", "n"]
    assert sample.wall_seconds == 1.5


def test_negative_preload_drift_then_load_window_rise_uses_subintervals():
    samples = [
        _sample(0, 0.0, 0.0),
        _sample(1, 1.0, 1.4),  # wall-minus-unbiased fell by 0.4
        _sample(2, 2.0, 1.8),  # then rose by 0.6 over [1, 2]
    ]
    analysis = calibration._analyze_drift(samples)
    assert analysis.outcome == "FAIL"
    assert analysis.excursion_estimate_seconds == pytest.approx(0.6)
    assert analysis.excursion_estimate_interval == (1, 2)


def test_late_window_peak_is_not_replaced_by_final_only_measurement():
    samples = [
        _sample(0, 0.0, 0.0),
        _sample(1, 1.0, 0.4),  # drift peak = 0.6
        _sample(2, 2.0, 1.8),  # final drift = 0.2
    ]
    analysis = calibration._analyze_drift(samples)
    assert analysis.outcome == "FAIL"
    assert analysis.excursion_estimate_seconds == pytest.approx(0.6)
    assert analysis.excursion_estimate_interval == (0, 1)


def test_excursion_upper_arithmetic_uses_n1j_n2i_and_measured_lag():
    samples = [
        _sample(
            0,
            0.0,
            0.01,
            precise=0.02,
            nonprecise_width=0.02,
            precise_width=0.02,
        ),
        _sample(
            1,
            1.0,
            0.71,
            precise=0.72,
            nonprecise_width=0.02,
            precise_width=0.02,
        ),
    ]
    analysis = calibration._analyze_drift(samples)
    assert analysis.measured_lag_seconds == pytest.approx(0.03)
    assert analysis.excursion_upper_seconds == pytest.approx(0.35)
    assert analysis.excursion_estimate_seconds == pytest.approx(0.30)
    assert analysis.excursion_lower_seconds == pytest.approx(0.25)


@pytest.mark.parametrize(
    ("samples", "outcome"),
    [
        ([_sample(0, 0.0, 0.0), _sample(1, 1.0, 0.6)], "PASS"),
        ([_sample(0, 0.0, 0.0), _sample(1, 1.0, 0.4)], "FAIL"),
        (
            [
                _sample(
                    0,
                    0.0,
                    0.0,
                    nonprecise_width=0.1,
                    precise_width=0.1,
                ),
                _sample(
                    1,
                    1.0,
                    0.6,
                    nonprecise_width=0.1,
                    precise_width=0.1,
                ),
            ],
            "INDETERMINATE",
        ),
    ],
)
def test_three_way_classification_including_upper_bound_only_crossing(
    samples, outcome
):
    assert calibration._analyze_drift(samples).outcome == outcome


def test_precise_crosscheck_compares_midpoints_on_each_identical_interval():
    samples = [
        _sample(0, 0.0, 0.0, precise=0.0),
        _sample(1, 1.0, 0.9, precise=0.9),
        _sample(2, 2.0, 1.8, precise=1.2),
    ]
    analysis = calibration._analyze_drift(samples)
    assert analysis.outcome == "INDETERMINATE"
    assert analysis.crosscheck_interval == (0, 2)
    assert analysis.max_crosscheck_disagreement_seconds == pytest.approx(0.6)


def test_forward_nonprecise_step_inside_five_read_bracket_fails_closed():
    samples = [
        _sample(0, 0.0, 0.0),
        _sample(
            1,
            1.0,
            1.4,
            precise=1.4,
            nonprecise_width=0.8,
        ),
    ]
    analysis = calibration._analyze_drift(samples)
    assert analysis.outcome == "INDETERMINATE"
    assert (
        analysis.excursion_lower_seconds
        < -calibration.NEGATIVE_EXCURSION_TOLERANCE_SECONDS
    )


def test_reversed_clock_bracket_is_measurement_indeterminate():
    malformed = calibration.ClockSample(
        ordinal=1,
        scheduled_index=1,
        terminal=False,
        nonprecise_1_seconds=1.1,
        precise_1_seconds=1.0,
        wall_seconds=1.0,
        precise_2_seconds=1.0,
        nonprecise_2_seconds=1.0,
    )
    analysis = calibration._analyze_drift([_sample(0, 0.0, 0.0), malformed])
    assert analysis.clocks_well_formed is False
    assert analysis.outcome == "INDETERMINATE"


def test_sampler_ready_handshake_precedes_supervisor(monkeypatch, tmp_path):
    def reader(ordinal, scheduled_index, terminal):
        return _sample(ordinal, time.perf_counter(), time.perf_counter(), terminal=terminal)

    sampler = calibration.ClockSampler(reader, cadence_seconds=10.0)
    observed = {}

    def supervisor(*_args, **kwargs):
        observed["baseline_count"] = len(sampler.samples)
        observed["accounting"] = kwargs["collect_job_accounting"]
        observed["timeout"] = kwargs["timeout_seconds"]
        return _supervised(600.0, 600.0)

    monkeypatch.setattr(calibration, "_run_vina_supervised", supervisor)
    monkeypatch.setattr(calibration, "_validate_sampling", lambda *_a, **_k: (600.0, 600.0))
    calibration._run_measurement(
        ["fake-vina"], project_root=tmp_path, temp_dir=tmp_path, sampler=sampler
    )
    assert observed == {"baseline_count": 1, "accounting": True, "timeout": 600.0}
    assert sampler.samples[-1].terminal is True


def test_sampler_death_midwait_does_not_bypass_supervisor_cleanup(
    monkeypatch, tmp_path
):
    state = {"process_live": False, "supervisor_returned": False}

    def reader(ordinal, scheduled_index, terminal):
        if ordinal:
            raise RuntimeError("synthetic sampler death")
        now = time.perf_counter()
        return _sample(0, now, now)

    sampler = calibration.ClockSampler(reader, cadence_seconds=0.001)

    def supervisor(*_args, **_kwargs):
        state["process_live"] = True
        time.sleep(0.02)
        state["process_live"] = False
        state["supervisor_returned"] = True
        return _supervised(600.0, 600.0)

    monkeypatch.setattr(calibration, "_run_vina_supervised", supervisor)
    with pytest.raises(calibration.CalibrationFailure, match="Sampler raised"):
        calibration._run_measurement(
            ["fake-vina"],
            project_root=tmp_path,
            temp_dir=tmp_path,
            sampler=sampler,
        )
    assert state == {"process_live": False, "supervisor_returned": True}


def test_missing_terminal_sample_is_indeterminate():
    samples = _series()
    samples[-1] = _sample(589, 600.0, 600.0, terminal=False)
    with pytest.raises(calibration.CalibrationFailure, match="terminal sample"):
        calibration._validate_sampling(
            samples, sampler_error=None, sampler_joined=True
        )


def test_post_sleep_overdue_deadlines_are_skipped_not_backfilled():
    assert calibration._first_future_deadline_index(42.4, 1.0) == 43
    assert calibration._first_future_deadline_index(42.4, 1.0) != 2


def test_excessive_unbiased_intersample_gap_is_indeterminate():
    samples = _series(step=1.1)
    for index in range(300, len(samples)):
        original = samples[index]
        samples[index] = _sample(
            index,
            original.wall_seconds + 5.1,
            original.nonprecise_midpoint_seconds + 5.1,
            terminal=original.terminal,
        )
    with pytest.raises(calibration.CalibrationFailure, match="intersample gap"):
        calibration._validate_sampling(
            samples, sampler_error=None, sampler_joined=True
        )


def test_short_unbiased_coverage_is_indeterminate():
    with pytest.raises(calibration.CalibrationFailure, match="cover 600"):
        calibration._validate_sampling(
            _series(step=1.0), sampler_error=None, sampler_joined=True
        )


def test_sample_count_below_frozen_minimum_is_indeterminate():
    with pytest.raises(calibration.CalibrationFailure, match="589 samples"):
        calibration._validate_sampling(
            _series(count=589, step=600.0 / 588.0),
            sampler_error=None,
            sampler_joined=True,
        )


def test_stalled_but_unsignaled_vina_fails_load_evidence():
    with pytest.raises(calibration.CalibrationFailure, match="utilization bounds"):
        calibration._validate_utilization(_supervised(0.0, 600.0))


def test_point_89_mean_fails_frozen_floor():
    with pytest.raises(calibration.CalibrationFailure, match="utilization bounds"):
        calibration._validate_utilization(_supervised(534.0, 600.0))


def test_sustained_multicore_load_uses_nominal_ceiling_denominator():
    # 663/605 would pass 1.10; the required 663/600 nominal ratio must fail.
    with pytest.raises(calibration.CalibrationFailure, match="utilization bounds"):
        calibration._validate_utilization(_supervised(663.0, 605.0))


@pytest.mark.parametrize("match_count", [0, 2])
def test_attempt_row_requires_exactly_one_match(match_count):
    row = {
        "workflow": "wide",
        "entity_id": "azithromycin",
        "state_id": "state_01",
        "pocket_id": "spycep_5xya_aes_active_site",
    }
    with pytest.raises(calibration.CalibrationFailure, match=f"found {match_count}"):
        calibration._select_attempt_row({"attempts": [row] * match_count})


def test_canonical_attempt_row_resolves_from_real_validated_manifest():
    resolved = calibration._resolve_inputs(calibration.PROJECT_ROOT)
    assert resolved["row"]["pdb_id"] == "5XYA"
    assert resolved["paths"]["ligand_pdbqt"].name == "azithromycin__state_01.pdbqt"
    assert resolved["row"]["box_size_angstrom"] == {"x": 22.0, "y": 22.0, "z": 27.5}


def test_species_catalog_mutation_changes_pre_post_hash(tmp_path):
    species = tmp_path / "species_audit.json"
    species.write_text('{"version": 1}\n', encoding="utf-8")
    before = calibration._hash_inputs({"species_catalog": species})
    species.write_text('{"version": 2}\n', encoding="utf-8")
    after = calibration._hash_inputs({"species_catalog": species})
    assert before != after


def test_any_input_mutation_changes_pre_post_hash(tmp_path):
    receptor = tmp_path / "receptor.pdbqt"
    receptor.write_text("ATOM 1\n", encoding="utf-8")
    before = calibration._hash_inputs({"receptor_pdbqt": receptor})
    receptor.write_text("ATOM 2\n", encoding="utf-8")
    after = calibration._hash_inputs({"receptor_pdbqt": receptor})
    assert before != after


def test_concurrent_writers_cannot_replace_same_artifact(tmp_path):
    target = tmp_path / "calibration.json"
    outcomes = []
    barrier = threading.Barrier(2)

    def writer(value):
        barrier.wait()
        try:
            calibration._atomic_json_no_replace(target, {"writer": value})
            outcomes.append("written")
        except FileExistsError:
            outcomes.append("refused")

    threads = [threading.Thread(target=writer, args=(value,)) for value in (1, 2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert sorted(outcomes) == ["refused", "written"]
    assert json.loads(target.read_text(encoding="utf-8"))["writer"] in (1, 2)
    assert not list(tmp_path.glob("*.tmp"))


@pytest.mark.parametrize(
    "module_name",
    [
        "scripts.run_docking",
        "scripts.run_speb_positive_control",
        "scripts.dock_boron_surrogates",
    ],
)
def test_direct_entry_campaign_id_mismatch_aborts(module_name, monkeypatch):
    module = importlib.import_module(module_name)
    monkeypatch.setattr(module, "require_campaign_id", lambda: "campaign-new")
    monkeypatch.setattr(
        module,
        "require_suspend_calibration",
        lambda _root: {"campaign_id": "campaign-old"},
    )
    with pytest.raises(InfrastructureError, match="does not match"):
        module.main()


def test_local_schema_and_load_literals_are_accepted_by_real_validator():
    record = {
        "calibration_schema_version": calibration.CALIBRATION_SCHEMA_VERSION,
        "duration_seconds": 600.0,
        "load": calibration.LOAD_NAME,
        "cpu": 1,
        "max_observed_drift_seconds": 0.5,
        "suspend_threshold_seconds": 5.0,
    }
    validate_suspend_calibration(record)


@pytest.mark.parametrize("failure_stage", calibration.FAILURE_STAGES)
def test_every_failure_artifact_is_invalid_under_campaign_schema(failure_stage):
    failure = calibration.CalibrationFailure(
        "synthetic failure", failure_stage=failure_stage
    )
    record = calibration._failure_record("campaign-test", failure)
    assert record["failure_stage"] == failure_stage
    assert record["valid_for_campaign_gate"] is False
    with pytest.raises(InfrastructureError):
        validate_suspend_calibration(record)


def test_non_windows_platform_raises_infrastructure_failure(monkeypatch):
    monkeypatch.setattr(calibration.os, "name", "posix")
    with pytest.raises(
        calibration._SupervisorInfrastructureError,
        match="requires Windows",
    ) as caught:
        calibration._require_windows()
    assert caught.value.failure_stage == "platform_gate"

"""Produce the operator-run pre-campaign suspend calibration artifact.

This Windows-only instrument deliberately reuses the campaign supervisor and its
non-precise unbiased clock.  It is a preflight measurement, never a docking result.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import platform
import shutil
import socket
import sys
import tempfile
import threading
import time
import uuid
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterator, Mapping, Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from spycep_drug_discovery import docking as docking_module
from spycep_drug_discovery.attempt_manifest import validate_attempt_manifest
from spycep_drug_discovery.docking import (
    CALIBRATION_DURATION_SECONDS,
    DEFAULT_CPU,
    DEFAULT_EXHAUSTIVENESS,
    DEFAULT_NUM_MODES,
    DEFAULT_SCORING,
    DEFAULT_SEED,
    DOCKING_OUTPUT_DIR,
    MAX_AWAKE_CALIBRATION_DRIFT_SECONDS,
    SUSPEND_THRESHOLD,
    InfrastructureError,
    SupervisedResult,
    _SupervisorInfrastructureError,
    _Win32Bindings,
    _query_unbiased_interrupt_time,
    _run_vina_supervised,
    build_vina_command,
    campaign_lock,
    require_campaign_id,
    supervisor_source_sha256,
    validate_suspend_calibration,
)


CALIBRATION_SCHEMA_VERSION = "docking-suspend-calibration-v1"
FAILURE_SCHEMA_VERSION = "docking-suspend-calibration-failure-v1"
LOAD_NAME = "single_core_docking_equivalent"

# Prospectively approved measurement-validity constants.  They are intentionally
# local and must not be tuned in response to calibration data.
CPU_UTILIZATION_FLOOR = 0.90
CPU_UTILIZATION_CEILING = 1.10
SAMPLE_CADENCE_SECONDS = 1.0
MAX_INTERSAMPLE_GAP_SECONDS = 5.0
MIN_SAMPLE_COUNT = 590
NEGATIVE_EXCURSION_TOLERANCE_SECONDS = 0.5

ATTEMPT_MANIFEST_RELATIVE = Path("docs/methods/attempt_manifest.json")
SPECIES_CATALOG_RELATIVE = Path("docs/methods/species_audit.json")
VINA_RELATIVE = Path("tools/vina.exe")
LIGAND_DIRECTORY_RELATIVE = Path("data/compounds/pdbqt_stage2")

FAILURE_STAGES = (
    "input-resolution",
    "pre-hash",
    "lock",
    "sampler-start",
    "supervisor-infra",
    "early-finish",
    "utilization",
    "measurement-indeterminate",
    "drift-fail",
    "hash-mutation",
    "campaign-root-recheck",
    "emission",
)


class CalibrationFailure(InfrastructureError):
    """A staged failure which must never satisfy the campaign validator."""

    def __init__(
        self,
        message: str,
        *,
        failure_stage: str,
        outcome: str = "ERROR",
        evidence: Mapping[str, Any] | None = None,
    ) -> None:
        if failure_stage not in FAILURE_STAGES:
            raise ValueError(f"Unknown calibration failure stage: {failure_stage}")
        super().__init__(message)
        self.failure_stage = failure_stage
        self.outcome = outcome
        self.evidence = dict(evidence or {})
        self.artifact_path: Path | None = None


@dataclass(frozen=True)
class ClockSample:
    ordinal: int
    scheduled_index: int | None
    terminal: bool
    nonprecise_1_seconds: float
    precise_1_seconds: float
    wall_seconds: float
    precise_2_seconds: float
    nonprecise_2_seconds: float

    @property
    def nonprecise_midpoint_seconds(self) -> float:
        return (self.nonprecise_1_seconds + self.nonprecise_2_seconds) / 2.0

    @property
    def precise_midpoint_seconds(self) -> float:
        return (self.precise_1_seconds + self.precise_2_seconds) / 2.0

    @property
    def lag_lower_seconds(self) -> float:
        return self.precise_1_seconds - self.nonprecise_2_seconds

    @property
    def lag_upper_seconds(self) -> float:
        return self.precise_2_seconds - self.nonprecise_1_seconds


@dataclass(frozen=True)
class DriftAnalysis:
    outcome: str
    reason: str
    measured_lag_seconds: float
    excursion_upper_seconds: float
    excursion_estimate_seconds: float
    excursion_lower_seconds: float
    max_crosscheck_disagreement_seconds: float
    excursion_upper_interval: tuple[int, int]
    excursion_estimate_interval: tuple[int, int]
    excursion_lower_interval: tuple[int, int]
    crosscheck_interval: tuple[int, int]
    clocks_well_formed: bool


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _relative_display(path: Path, project_root: Path) -> str:
    try:
        return path.resolve().relative_to(project_root.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def _require_windows() -> None:
    if os.name != "nt":
        raise _SupervisorInfrastructureError(
            "Suspend calibration requires Windows 10 build 10240 or newer.",
            failure_stage="platform_gate",
        )
    _Win32Bindings()


def _configure_precise_clock(bindings: Any) -> None:
    precise = bindings.kernel32.QueryUnbiasedInterruptTimePrecise
    precise.argtypes = [bindings.ctypes.POINTER(bindings.ctypes.c_ulonglong)]
    precise.restype = bindings.wintypes.BOOL
    bindings.QueryUnbiasedInterruptTimePrecise = precise


def _query_precise_unbiased_interrupt_time(bindings: Any) -> int:
    value = bindings.ctypes.c_ulonglong()
    bindings.ctypes.set_last_error(0)
    if not bindings.QueryUnbiasedInterruptTimePrecise(bindings.ctypes.byref(value)):
        raise _SupervisorInfrastructureError(
            "QueryUnbiasedInterruptTimePrecise failed.",
            failure_stage="QueryUnbiasedInterruptTimePrecise",
            win32_error=bindings.ctypes.get_last_error(),
        )
    return int(value.value)


def _take_clock_sample(
    bindings: Any,
    *,
    ordinal: int,
    scheduled_index: int | None,
    terminal: bool,
    wall_clock: Callable[[], float] = time.perf_counter,
) -> ClockSample:
    # The order is load-bearing: n1, p1, wall, p2, n2.
    n1 = _query_unbiased_interrupt_time(bindings) / 10_000_000.0
    p1 = _query_precise_unbiased_interrupt_time(bindings) / 10_000_000.0
    wall = wall_clock()
    p2 = _query_precise_unbiased_interrupt_time(bindings) / 10_000_000.0
    n2 = _query_unbiased_interrupt_time(bindings) / 10_000_000.0
    return ClockSample(
        ordinal=ordinal,
        scheduled_index=scheduled_index,
        terminal=terminal,
        nonprecise_1_seconds=n1,
        precise_1_seconds=p1,
        wall_seconds=wall,
        precise_2_seconds=p2,
        nonprecise_2_seconds=n2,
    )


class ClockSampler:
    """One external absolute-deadline sampler with a ready baseline."""

    def __init__(
        self,
        sample_reader: Callable[[int, int | None, bool], ClockSample],
        *,
        cadence_seconds: float = SAMPLE_CADENCE_SECONDS,
        wall_clock: Callable[[], float] = time.perf_counter,
    ) -> None:
        self._sample_reader = sample_reader
        self._cadence_seconds = cadence_seconds
        self._wall_clock = wall_clock
        self._ready = threading.Event()
        self._stop = threading.Event()
        self._terminal_requested = threading.Event()
        self._thread = threading.Thread(
            target=self._run,
            name="suspend-calibration-sampler",
            daemon=True,
        )
        self.samples: list[ClockSample] = []
        self.error: BaseException | None = None
        self.missed_deadline_count = 0

    def start_and_wait_ready(self) -> None:
        self._thread.start()
        if not self._ready.wait(MAX_INTERSAMPLE_GAP_SECONDS):
            self._stop.set()
            self._thread.join(MAX_INTERSAMPLE_GAP_SECONDS)
            raise CalibrationFailure(
                "Sampler did not persist a ready baseline in time.",
                failure_stage="sampler-start",
            )
        if self.error is not None or not self.samples:
            raise CalibrationFailure(
                f"Sampler baseline failed: {self.error}",
                failure_stage="sampler-start",
            )

    def request_terminal_and_join(self) -> bool:
        self._terminal_requested.set()
        self._stop.set()
        self._thread.join(MAX_INTERSAMPLE_GAP_SECONDS)
        return not self._thread.is_alive()

    def _run(self) -> None:
        baseline_wall: float | None = None
        try:
            baseline = self._sample_reader(0, 0, False)
            self.samples.append(baseline)
            baseline_wall = baseline.wall_seconds
        except BaseException as exc:
            self.error = exc
        finally:
            self._ready.set()

        if self.error is None and baseline_wall is not None:
            scheduled_index = 1
            try:
                while not self._stop.is_set():
                    deadline = baseline_wall + scheduled_index * self._cadence_seconds
                    remaining = deadline - self._wall_clock()
                    if remaining > 0 and self._stop.wait(remaining):
                        break
                    if self._stop.is_set():
                        break
                    self.samples.append(
                        self._sample_reader(
                            len(self.samples), scheduled_index, False
                        )
                    )
                    next_index = scheduled_index + 1
                    elapsed = max(0.0, self._wall_clock() - baseline_wall)
                    first_future_index = _first_future_deadline_index(
                        elapsed, self._cadence_seconds
                    )
                    if first_future_index > next_index:
                        self.missed_deadline_count += first_future_index - next_index
                    scheduled_index = max(next_index, first_future_index)
            except BaseException as exc:
                self.error = exc

        if self._terminal_requested.is_set() and self.error is None:
            try:
                self.samples.append(
                    self._sample_reader(len(self.samples), None, True)
                )
            except BaseException as exc:
                self.error = exc


def _first_future_deadline_index(
    elapsed_seconds: float, cadence_seconds: float
) -> int:
    """Return one future deadline index; overdue deadlines are never replayed."""
    return math.floor(max(0.0, elapsed_seconds) / cadence_seconds) + 1


def _analyze_drift(samples: Sequence[ClockSample]) -> DriftAnalysis:
    if len(samples) < 2:
        raise CalibrationFailure(
            "At least two samples are required for drift analysis.",
            failure_stage="measurement-indeterminate",
            outcome="INDETERMINATE",
        )

    lag_series = [sample.lag_upper_seconds for sample in samples]
    measured_lag = max(lag_series)
    well_formed = measured_lag >= 0 and all(
        sample.nonprecise_1_seconds <= sample.nonprecise_2_seconds
        and sample.precise_1_seconds <= sample.precise_2_seconds
        for sample in samples
    )

    upper = -math.inf
    estimate = -math.inf
    lower = math.inf
    crosscheck = -math.inf
    upper_pair = estimate_pair = lower_pair = crosscheck_pair = (0, 1)

    for i, start in enumerate(samples[:-1]):
        for j in range(i + 1, len(samples)):
            end = samples[j]
            wall_delta = end.wall_seconds - start.wall_seconds
            interval_upper = wall_delta - (
                end.nonprecise_1_seconds - start.nonprecise_2_seconds
            ) + measured_lag
            interval_estimate = wall_delta - (
                end.nonprecise_midpoint_seconds
                - start.nonprecise_midpoint_seconds
            )
            interval_lower = wall_delta - (
                end.nonprecise_2_seconds - start.nonprecise_1_seconds
            ) - measured_lag
            precise_estimate = wall_delta - (
                end.precise_midpoint_seconds - start.precise_midpoint_seconds
            )
            disagreement = abs(interval_estimate - precise_estimate)

            if interval_upper > upper:
                upper, upper_pair = interval_upper, (i, j)
            if interval_estimate > estimate:
                estimate, estimate_pair = interval_estimate, (i, j)
            if interval_lower < lower:
                lower, lower_pair = interval_lower, (i, j)
            if disagreement > crosscheck:
                crosscheck, crosscheck_pair = disagreement, (i, j)

    if not well_formed:
        outcome = "INDETERMINATE"
        reason = "clock reads or the measured lag were not well formed"
    elif crosscheck > measured_lag:
        outcome = "INDETERMINATE"
        reason = "precise/non-precise midpoint cross-check exceeded measured lag"
    elif lower < -NEGATIVE_EXCURSION_TOLERANCE_SECONDS:
        outcome = "INDETERMINATE"
        reason = "negative excursion lower bound exceeded tolerance"
    elif upper <= MAX_AWAKE_CALIBRATION_DRIFT_SECONDS:
        outcome = "PASS"
        reason = "maximum observed excursion was within the fixed gate"
    elif estimate > MAX_AWAKE_CALIBRATION_DRIFT_SECONDS:
        outcome = "FAIL"
        reason = "host drift midpoint estimate exceeded the fixed gate"
    else:
        outcome = "INDETERMINATE"
        reason = "only the conservative upper bound crossed the fixed gate"

    return DriftAnalysis(
        outcome=outcome,
        reason=reason,
        measured_lag_seconds=measured_lag,
        excursion_upper_seconds=upper,
        excursion_estimate_seconds=estimate,
        excursion_lower_seconds=lower,
        max_crosscheck_disagreement_seconds=crosscheck,
        excursion_upper_interval=upper_pair,
        excursion_estimate_interval=estimate_pair,
        excursion_lower_interval=lower_pair,
        crosscheck_interval=crosscheck_pair,
        clocks_well_formed=well_formed,
    )


def _sampling_windows(samples: Sequence[ClockSample]) -> tuple[float, float]:
    return (
        samples[-1].nonprecise_midpoint_seconds
        - samples[0].nonprecise_midpoint_seconds,
        samples[-1].wall_seconds - samples[0].wall_seconds,
    )


def _validate_sampling(
    samples: Sequence[ClockSample],
    *,
    sampler_error: BaseException | None,
    sampler_joined: bool,
) -> tuple[float, float]:
    if not sampler_joined:
        raise CalibrationFailure(
            "Sampler did not stop within the bounded join.",
            failure_stage="measurement-indeterminate",
            outcome="INDETERMINATE",
        )
    if sampler_error is not None:
        raise CalibrationFailure(
            f"Sampler raised or exited early: {sampler_error}",
            failure_stage="measurement-indeterminate",
            outcome="INDETERMINATE",
        )
    if not samples or not samples[-1].terminal:
        raise CalibrationFailure(
            "The mandatory post-supervisor terminal sample is missing.",
            failure_stage="measurement-indeterminate",
            outcome="INDETERMINATE",
        )
    if sum(sample.terminal for sample in samples) != 1:
        raise CalibrationFailure(
            "The sample series has an invalid terminal-sample count.",
            failure_stage="measurement-indeterminate",
            outcome="INDETERMINATE",
        )
    if len(samples) < MIN_SAMPLE_COUNT:
        raise CalibrationFailure(
            f"Only {len(samples)} samples were recorded; {MIN_SAMPLE_COUNT} required.",
            failure_stage="measurement-indeterminate",
            outcome="INDETERMINATE",
        )
    gaps = [
        end.nonprecise_midpoint_seconds - start.nonprecise_midpoint_seconds
        for start, end in zip(samples, samples[1:])
    ]
    if gaps and max(gaps) > MAX_INTERSAMPLE_GAP_SECONDS:
        raise CalibrationFailure(
            "An unbiased intersample gap exceeded the fixed sampler-health limit.",
            failure_stage="measurement-indeterminate",
            outcome="INDETERMINATE",
        )
    unbiased_window, wall_window = _sampling_windows(samples)
    if unbiased_window < CALIBRATION_DURATION_SECONDS:
        raise CalibrationFailure(
            "The sampling series did not cover 600 unbiased seconds.",
            failure_stage="measurement-indeterminate",
            outcome="INDETERMINATE",
        )
    return unbiased_window, wall_window


def _validate_utilization(supervised: SupervisedResult) -> tuple[float, float]:
    if (
        supervised.disposition_basis != "deadline_timeout"
        or supervised.job_cpu_seconds is None
        or supervised.load_window_unbiased_seconds is None
        or supervised.load_window_unbiased_seconds < CALIBRATION_DURATION_SECONDS
    ):
        raise CalibrationFailure(
            "Deadline disposition, Job accounting, or enclosing window is invalid.",
            failure_stage="utilization",
        )
    floor_ratio = (
        supervised.job_cpu_seconds / supervised.load_window_unbiased_seconds
    )
    ceiling_ratio = supervised.job_cpu_seconds / 600.0
    if (
        floor_ratio < CPU_UTILIZATION_FLOOR
        or ceiling_ratio > CPU_UTILIZATION_CEILING
    ):
        raise CalibrationFailure(
            "The two mean-load utilization bounds were not satisfied.",
            failure_stage="utilization",
        )
    return floor_ratio, ceiling_ratio


def _select_attempt_row(manifest: Mapping[str, Any]) -> Mapping[str, Any]:
    matches = [
        row
        for row in manifest.get("attempts", ())
        if row.get("workflow") == "wide"
        and row.get("entity_id") == "azithromycin"
        and row.get("state_id") == "state_01"
        and row.get("pocket_id") == "spycep_5xya_aes_active_site"
    ]
    if len(matches) != 1:
        raise CalibrationFailure(
            "The canonical calibration attempt row must match exactly once; "
            f"found {len(matches)}.",
            failure_stage="input-resolution",
        )
    return matches[0]


def _resolve_inputs(project_root: Path) -> dict[str, Any]:
    manifest_path = project_root / ATTEMPT_MANIFEST_RELATIVE
    species_path = project_root / SPECIES_CATALOG_RELATIVE
    try:
        species = json.loads(species_path.read_text(encoding="utf-8"))
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        validate_attempt_manifest(manifest, species)
        row = _select_attempt_row(manifest)
        receptor = (project_root / str(row["receptor_pdbqt_path"])).resolve()
        ligand = (
            project_root
            / LIGAND_DIRECTORY_RELATIVE
            / f"{row['entity_id']}__{row['state_id']}.pdbqt"
        ).resolve()
        vina = (project_root / VINA_RELATIVE).resolve()
        for label, path in (
            ("vina", vina),
            ("receptor", receptor),
            ("ligand", ligand),
        ):
            if not path.is_file():
                raise FileNotFoundError(f"Resolved {label} input does not exist: {path}")
    except CalibrationFailure:
        raise
    except BaseException as exc:
        raise CalibrationFailure(
            f"Could not resolve the canonical calibration inputs: {exc}",
            failure_stage="input-resolution",
        ) from exc

    paths = {
        "calibrator_script": Path(__file__).resolve(),
        "supervisor_source": Path(docking_module.__file__).resolve(),
        "vina_binary": vina,
        "receptor_pdbqt": receptor,
        "ligand_pdbqt": ligand,
        "attempt_manifest": manifest_path.resolve(),
        "species_catalog": species_path.resolve(),
    }
    return {"manifest": manifest, "species": species, "row": row, "paths": paths}


def _hash_inputs(paths: Mapping[str, Path]) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for name, path in paths.items():
        hashes[name] = (
            supervisor_source_sha256()
            if name == "supervisor_source"
            else _sha256(path)
        )
    return hashes


@contextmanager
def _launcher_lock(project_root: Path) -> Iterator[None]:
    lock_path = project_root / ".campaign.lock"
    try:
        lock_path.mkdir()
    except FileExistsError as exc:
        raise CalibrationFailure(
            f"Launcher lock already exists: {lock_path}",
            failure_stage="lock",
        ) from exc
    try:
        yield
    finally:
        lock_path.rmdir()


def _failure_record(
    campaign_id: str,
    failure: CalibrationFailure,
    evidence: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    combined = dict(evidence or {})
    combined.update(failure.evidence)
    return {
        "calibration_schema_version": FAILURE_SCHEMA_VERSION,
        "outcome": failure.outcome,
        "failure_stage": failure.failure_stage,
        "message": str(failure),
        "measured_at_utc": _utc_now(),
        "campaign_id": campaign_id,
        "partial_evidence": combined or None,
        "valid_for_campaign_gate": False,
    }


def _atomic_json_no_replace(path: Path, record: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.parent / f".{path.name}.{uuid.uuid4().hex}.tmp"
    descriptor = -1
    try:
        descriptor = os.open(
            temporary,
            os.O_CREAT | os.O_EXCL | os.O_WRONLY,
            0o600,
        )
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            descriptor = -1
            json.dump(record, handle, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        # On the pinned Windows platform os.rename is atomic and refuses an existing
        # destination.  The uniquely-created temp prevents writer temp collisions.
        os.rename(temporary, path)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        temporary.unlink(missing_ok=True)


def _emit_failure(
    project_root: Path,
    campaign_id: str,
    failure: CalibrationFailure,
    evidence: Mapping[str, Any] | None = None,
) -> Path:
    filename = (
        f"suspend_calibration_{campaign_id}."
        f"{failure.failure_stage}.{uuid.uuid4().hex}.FAILED.json"
    )
    path = project_root / "docs" / "methods" / filename
    _atomic_json_no_replace(path, _failure_record(campaign_id, failure, evidence))
    failure.artifact_path = path
    return path


def _sample_records(samples: Sequence[ClockSample]) -> list[dict[str, Any]]:
    return [
        {
            **asdict(sample),
            "nonprecise_midpoint_seconds": sample.nonprecise_midpoint_seconds,
            "precise_midpoint_seconds": sample.precise_midpoint_seconds,
        }
        for sample in samples
    ]


def _assemble_record(
    *,
    project_root: Path,
    campaign_id: str,
    resolved: Mapping[str, Any],
    command: Sequence[str],
    supervised: SupervisedResult,
    sampler: ClockSampler,
    sampling_window_unbiased_seconds: float,
    sampling_window_wall_seconds: float,
    hashes_before: Mapping[str, str],
    hashes_after: Mapping[str, str],
    analysis: DriftAnalysis,
) -> dict[str, Any]:
    assert supervised.job_cpu_seconds is not None
    assert supervised.load_window_unbiased_seconds is not None
    floor_ratio = (
        supervised.job_cpu_seconds / supervised.load_window_unbiased_seconds
    )
    ceiling_ratio = supervised.job_cpu_seconds / CALIBRATION_DURATION_SECONDS
    row = resolved["row"]
    samples = sampler.samples
    record = {
        "calibration_schema_version": CALIBRATION_SCHEMA_VERSION,
        "duration_seconds": 600.0,
        "load": LOAD_NAME,
        "cpu": 1,
        "max_observed_drift_seconds": max(
            0.0, analysis.excursion_upper_seconds
        ),
        "suspend_threshold_seconds": SUSPEND_THRESHOLD,
        "measured_at_utc": _utc_now(),
        "hostname": socket.gethostname(),
        "os_build": {
            "platform": platform.platform(),
            "windows_build": sys.getwindowsversion().build,
        },
        "campaign_id": campaign_id,
        "sampling_window_unbiased_seconds": sampling_window_unbiased_seconds,
        "sampling_window_wall_seconds": sampling_window_wall_seconds,
        "load_window_unbiased_seconds": supervised.load_window_unbiased_seconds,
        "disposition_basis": supervised.disposition_basis,
        "job_cpu_seconds": supervised.job_cpu_seconds,
        "utilization_floor_ratio": floor_ratio,
        "utilization_ceiling_ratio": ceiling_ratio,
        "input_paths": {
            name: _relative_display(path, project_root)
            for name, path in resolved["paths"].items()
        },
        "input_hashes_before": dict(hashes_before),
        "input_hashes_after": dict(hashes_after),
        "resolved_box": {
            "pocket_id": row["pocket_id"],
            "pdb_id": row["pdb_id"],
            "box_center_angstrom": row["box_center_angstrom"],
            "box_size_angstrom": row["box_size_angstrom"],
        },
        "load_command": list(command),
        "sample_count": len(samples),
        "missed_deadline_count": sampler.missed_deadline_count,
        "sample_series": _sample_records(samples),
        "read_skew_series_seconds": [
            {
                "ordinal": sample.ordinal,
                "nonprecise": (
                    sample.nonprecise_2_seconds
                    - sample.nonprecise_1_seconds
                ),
                "precise": sample.precise_2_seconds - sample.precise_1_seconds,
            }
            for sample in samples
        ],
        "precise_vs_nonprecise_lag_series_seconds": [
            {
                "ordinal": sample.ordinal,
                "lower": sample.lag_lower_seconds,
                "upper": sample.lag_upper_seconds,
            }
            for sample in samples
        ],
        "drift_analysis": asdict(analysis),
        "frozen_constants": {
            "CPU_UTILIZATION_FLOOR": CPU_UTILIZATION_FLOOR,
            "CPU_UTILIZATION_CEILING": CPU_UTILIZATION_CEILING,
            "SAMPLE_CADENCE_SECONDS": SAMPLE_CADENCE_SECONDS,
            "MAX_INTERSAMPLE_GAP_SECONDS": MAX_INTERSAMPLE_GAP_SECONDS,
            "MIN_SAMPLE_COUNT": MIN_SAMPLE_COUNT,
            "NEGATIVE_EXCURSION_TOLERANCE_SECONDS": (
                NEGATIVE_EXCURSION_TOLERANCE_SECONDS
            ),
            "CALIBRATION_DURATION_SECONDS": CALIBRATION_DURATION_SECONDS,
            "MAX_AWAKE_CALIBRATION_DRIFT_SECONDS": (
                MAX_AWAKE_CALIBRATION_DRIFT_SECONDS
            ),
            "SUSPEND_THRESHOLD": SUSPEND_THRESHOLD,
            "seed": DEFAULT_SEED,
            "exhaustiveness": DEFAULT_EXHAUSTIVENESS,
            "num_modes": DEFAULT_NUM_MODES,
            "cpu": DEFAULT_CPU,
        },
    }
    validate_suspend_calibration(record)
    return record


def _run_measurement(
    command: Sequence[str],
    *,
    project_root: Path,
    temp_dir: Path,
    sampler: ClockSampler,
) -> tuple[SupervisedResult, float, float]:
    sampler.start_and_wait_ready()
    supervisor_failure: BaseException | None = None
    result: SupervisedResult | None = None
    try:
        result = _run_vina_supervised(
            command,
            timeout_seconds=600.0,
            cwd=project_root,
            temp_dir=temp_dir,
            collect_job_accounting=True,
        )
    except BaseException as exc:
        supervisor_failure = exc
    finally:
        sampler_joined = sampler.request_terminal_and_join()

    # Infrastructure has precedence, but Vina has already been terminated/reaped and
    # the sampler has received its bounded shutdown before this propagates.
    if supervisor_failure is not None:
        if isinstance(supervisor_failure, _SupervisorInfrastructureError):
            evidence = {
                "native_failure_stage": supervisor_failure.failure_stage,
                "win32_error": supervisor_failure.win32_error,
                "cleanup_outcome": supervisor_failure.cleanup_outcome,
                "sample_series": _sample_records(sampler.samples),
            }
        else:
            evidence = {
                "native_failure_stage": "unexpected",
                "exception": repr(supervisor_failure),
                "sample_series": _sample_records(sampler.samples),
            }
        raise CalibrationFailure(
            f"The Vina supervisor failed: {supervisor_failure}",
            failure_stage="supervisor-infra",
            evidence=evidence,
        ) from supervisor_failure

    sampling_windows = _validate_sampling(
        sampler.samples,
        sampler_error=sampler.error,
        sampler_joined=sampler_joined,
    )
    assert result is not None
    return result, *sampling_windows


def _perform_locked_calibration(
    project_root: Path,
    campaign_id: str,
    target: Path,
) -> Path:
    evidence: dict[str, Any] = {}
    campaign_root = project_root / DOCKING_OUTPUT_DIR / f"campaign_{campaign_id}"
    if campaign_root.exists():
        raise CalibrationFailure(
            f"Campaign root already exists: {campaign_root}",
            failure_stage="campaign-root-recheck",
        )

    resolved = _resolve_inputs(project_root)
    evidence["input_paths"] = {
        name: _relative_display(path, project_root)
        for name, path in resolved["paths"].items()
    }
    try:
        hashes_before = _hash_inputs(resolved["paths"])
    except BaseException as exc:
        raise CalibrationFailure(
            f"Could not hash all calibration inputs before the run: {exc}",
            failure_stage="pre-hash",
            evidence=evidence,
        ) from exc
    evidence["input_hashes_before"] = hashes_before

    temp_dir = Path(tempfile.mkdtemp(prefix="spycep-suspend-calibration-"))
    record: dict[str, Any] | None = None
    try:
        out_path = temp_dir / "calibration-load.pdbqt"
        row = resolved["row"]
        command = build_vina_command(
            vina_executable=resolved["paths"]["vina_binary"],
            receptor_pdbqt=resolved["paths"]["receptor_pdbqt"],
            ligand_pdbqt=resolved["paths"]["ligand_pdbqt"],
            box_center=row["box_center_angstrom"],
            box_size=row["box_size_angstrom"],
            out_path=out_path,
            seed=42,
            exhaustiveness=8,
            num_modes=9,
            cpu=1,
            scoring=DEFAULT_SCORING,
        )
        evidence["load_command"] = command

        try:
            bindings = _Win32Bindings()
            _configure_precise_clock(bindings)
        except _SupervisorInfrastructureError as exc:
            raise CalibrationFailure(
                f"Could not initialize the calibration clocks: {exc}",
                failure_stage="sampler-start",
                evidence={
                    **evidence,
                    "native_failure_stage": exc.failure_stage,
                    "win32_error": exc.win32_error,
                },
            ) from exc

        def read_sample(
            ordinal: int, scheduled_index: int | None, terminal: bool
        ) -> ClockSample:
            return _take_clock_sample(
                bindings,
                ordinal=ordinal,
                scheduled_index=scheduled_index,
                terminal=terminal,
            )

        sampler = ClockSampler(read_sample)
        supervised, sampling_unbiased, sampling_wall = _run_measurement(
            command,
            project_root=project_root,
            temp_dir=temp_dir,
            sampler=sampler,
        )
        evidence["sample_series"] = _sample_records(sampler.samples)
        evidence["supervised_result"] = {
            "disposition_basis": supervised.disposition_basis,
            "job_cpu_seconds": supervised.job_cpu_seconds,
            "load_window_unbiased_seconds": (
                supervised.load_window_unbiased_seconds
            ),
            "cleanup_outcome": supervised.cleanup_outcome,
        }

        try:
            hashes_after = _hash_inputs(resolved["paths"])
        except BaseException as exc:
            raise CalibrationFailure(
                f"Could not hash all calibration inputs after the run: {exc}",
                failure_stage="hash-mutation",
                evidence=evidence,
            ) from exc
        evidence["input_hashes_after"] = hashes_after
        if hashes_before != hashes_after:
            raise CalibrationFailure(
                "One or more calibration inputs changed during the run.",
                failure_stage="hash-mutation",
                evidence=evidence,
            )

        analysis = _analyze_drift(sampler.samples)
        evidence["drift_analysis"] = asdict(analysis)
        if analysis.outcome == "INDETERMINATE":
            raise CalibrationFailure(
                analysis.reason,
                failure_stage="measurement-indeterminate",
                outcome="INDETERMINATE",
                evidence=evidence,
            )
        if supervised.disposition_basis != "deadline_timeout":
            raise CalibrationFailure(
                "Vina completed before the nominal calibration deadline.",
                failure_stage="early-finish",
                evidence=evidence,
            )
        try:
            floor_ratio, ceiling_ratio = _validate_utilization(supervised)
        except CalibrationFailure as failure:
            failure.evidence.update(evidence)
            raise
        evidence["utilization_floor_ratio"] = floor_ratio
        evidence["utilization_ceiling_ratio"] = ceiling_ratio
        if analysis.outcome == "FAIL":
            raise CalibrationFailure(
                analysis.reason,
                failure_stage="drift-fail",
                outcome="FAIL",
                evidence=evidence,
            )

        record = _assemble_record(
            project_root=project_root,
            campaign_id=campaign_id,
            resolved=resolved,
            command=command,
            supervised=supervised,
            sampler=sampler,
            sampling_window_unbiased_seconds=sampling_unbiased,
            sampling_window_wall_seconds=sampling_wall,
            hashes_before=hashes_before,
            hashes_after=hashes_after,
            analysis=analysis,
        )
    finally:
        try:
            shutil.rmtree(temp_dir)
        except OSError as exc:
            raise CalibrationFailure(
                f"Could not remove the temporary calibration directory: {exc}",
                failure_stage="emission",
                evidence=evidence,
            ) from exc

    assert record is not None
    if campaign_root.exists():
        raise CalibrationFailure(
            f"Campaign root appeared during calibration: {campaign_root}",
            failure_stage="campaign-root-recheck",
            evidence=evidence,
        )
    try:
        _atomic_json_no_replace(target, record)
    except BaseException as exc:
        raise CalibrationFailure(
            f"Could not emit the passing calibration artifact: {exc}",
            failure_stage="emission",
            evidence=evidence,
        ) from exc
    return target


def run_calibration(project_root: Path = PROJECT_ROOT) -> Path:
    project_root = project_root.resolve()
    campaign_id = require_campaign_id()
    target = (
        project_root
        / "docs"
        / "methods"
        / f"suspend_calibration_{campaign_id}.json"
    )
    evidence: dict[str, Any] = {}
    try:
        _require_windows()
        if target.exists():
            raise CalibrationFailure(
                f"Target calibration artifact already exists: {target}",
                failure_stage="emission",
            )
        with _launcher_lock(project_root):
            try:
                with campaign_lock(project_root, campaign_id):
                    try:
                        return _perform_locked_calibration(
                            project_root, campaign_id, target
                        )
                    except CalibrationFailure as failure:
                        _emit_failure(
                            project_root, campaign_id, failure, evidence
                        )
                        raise
            except CalibrationFailure:
                raise
            except InfrastructureError as exc:
                raise CalibrationFailure(
                    str(exc), failure_stage="lock"
                ) from exc
    except CalibrationFailure as failure:
        if failure.artifact_path is None:
            _emit_failure(project_root, campaign_id, failure, evidence)
        raise
    except _SupervisorInfrastructureError as exc:
        failure = CalibrationFailure(
            str(exc),
            failure_stage="input-resolution",
            evidence={"native_failure_stage": exc.failure_stage},
        )
        _emit_failure(project_root, campaign_id, failure, evidence)
        raise failure from exc


def main() -> None:
    try:
        path = run_calibration()
    except CalibrationFailure as exc:
        evidence = (
            _relative_display(exc.artifact_path, PROJECT_ROOT)
            if exc.artifact_path is not None
            else "unavailable"
        )
        print(f"CALIBRATION {exc.outcome}: {exc}", file=sys.stderr)
        print(f"Failure evidence: {evidence}", file=sys.stderr)
        print(
            "The prospectively frozen threshold is not to be raised; investigate "
            "the host or measurement failure.",
            file=sys.stderr,
        )
        raise SystemExit(1)

    relative = _relative_display(path, PROJECT_ROOT)
    campaign_id = require_campaign_id()
    print(f"Calibration PASS: {relative}")
    print(
        f"SPYCEP_CAMPAIGN_ID={campaign_id} "
        f"SPYCEP_SUSPEND_CALIBRATION_PATH={relative} ./run_campaign.sh"
    )


if __name__ == "__main__":
    main()

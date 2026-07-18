from __future__ import annotations

import hashlib
import json
import math
import os
import platform
import re
import subprocess
import sys
import tempfile
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from statistics import mean
from typing import Any, Callable, Iterator, Mapping, Sequence


DOCKING_VERSION = "2026-07-13-stage1"
RUN_SCHEMA_VERSION = "docking-run-record-v3"
DOCKING_OUTPUT_DIR = "results/docking"
DEFAULT_SEED = 42
DEFAULT_EXHAUSTIVENESS = 8
DEFAULT_NUM_MODES = 9
DEFAULT_CPU = 1
DEFAULT_SCORING = "vina"
DEFAULT_TIMEOUT_SECONDS = 1800.0
DEFAULT_TIMEOUT_MS = 1800000
TIMEOUT_BASIS = "unbiased_wall_seconds"
CLOCK_SOURCE = "QueryUnbiasedInterruptTime"
WAIT_MECHANISM = "single_armed_WaitForSingleObject"
SUSPEND_THRESHOLD = 5.0
MAX_SUSPENDED_RETRIES = 2
MINIMUM_WINDOWS_BUILD = 10240
CALIBRATION_DURATION_SECONDS = 600.0
MAX_AWAKE_CALIBRATION_DRIFT_SECONDS = 0.5
TRANSIENT_SPAWN_STATUS_ALLOWLIST = frozenset({0xC0000142})
TRANSIENT_SPAWN_MAX_ELAPSED_SECONDS = 1.0
MAX_TRANSIENT_SPAWN_RETRIES = 3
TRANSIENT_SPAWN_BACKOFF_SECONDS = (2.0, 5.0, 10.0)
CAMPAIGN_TRANSIENT_SPAWN_BUDGET = 10
SPAWN_RETRY_LEDGER_SCHEMA_VERSION = "docking-spawn-retry-ledger-v1"
CAMPAIGN_SEAL_SCHEMA_VERSION = "docking-campaign-seal-v1"

WAIT_OBJECT_0 = 0x00000000
WAIT_TIMEOUT = 0x00000102
WAIT_FAILED = 0xFFFFFFFF
STILL_ACTIVE = 0x00000103
INFINITE = 0xFFFFFFFF

RUN_RECORD_REQUIRED_FIELDS = frozenset(
    {
        "run_schema_version",
        "fingerprint",
        "fingerprint_payload",
        "workflow",
        "claim_key",
        "entity_id",
        "state_id",
        "species_key",
        "pocket_id",
        "pdb_id",
        "command",
        "ligand_pdbqt_path",
        "ligand_pdbqt_sha256",
        "receptor_pdbqt_path",
        "receptor_pdbqt_sha256",
        "vina_binary_sha256",
        "box_center_angstrom",
        "box_size_angstrom",
        "seed",
        "exhaustiveness",
        "num_modes",
        "cpu",
        "scoring",
        "timeout_seconds",
        "species_catalog_sha256",
        "attempt_manifest_sha256",
        "software_versions",
        "elapsed_seconds",
        "wall_seconds",
        "unbiased_seconds",
        "suspend_gap_seconds",
        "suspend_detected",
        "disposition_basis",
        "wait_result",
        "termination_action",
        "timing_ambiguous",
        "attempt_instance_id",
        "authoritative_selected",
        "timeout_basis",
        "clock_source",
        "timeout_ms",
        "wait_mechanism",
        "supervisor_source_sha256",
        "suspend_threshold_seconds",
        "campaign_id",
        "status",
        "cause",
        "exit_code",
        "out_path",
        "out_sha256",
        "sidecar_path",
        "resumed",
        "valid_fit",
        "spawn_retry_count",
        "spawn_failures",
    }
)

_MODE_ROW = re.compile(
    r"^\s*(\d+)\s+(-?\d+\.\d+)\s+(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)\s*$"
)
_POSE_RESULT = re.compile(
    r"^REMARK VINA RESULT:\s+(-?\d+\.\d+)\s+(-?\d+\.\d+)\s+(-?\d+\.\d+)"
)


class DockingError(RuntimeError):
    """Raised when a docking attempt is invalid or does not yield a valid fit."""

    def __init__(self, message: str, *, run_record: Mapping[str, Any] | None = None):
        super().__init__(message)
        self.run_record = dict(run_record) if run_record is not None else None


class InfrastructureError(DockingError):
    """Raised after a structured infrastructure-failure record is persisted."""


class _SupervisorInfrastructureError(InfrastructureError):
    """Native-supervisor failure details consumed by :func:`dock_ligand`."""

    def __init__(
        self,
        message: str,
        *,
        failure_stage: str,
        win32_error: int | None = None,
        exit_code: int | None = None,
        cleanup_outcome: Mapping[str, Any] | None = None,
        wall_seconds: float | None = None,
        unbiased_seconds: float | None = None,
    ):
        super().__init__(message)
        self.failure_stage = failure_stage
        self.win32_error = win32_error
        self.exit_code = exit_code
        self.cleanup_outcome = dict(cleanup_outcome or {})
        self.wall_seconds = wall_seconds
        self.unbiased_seconds = unbiased_seconds


@dataclass(frozen=True)
class SupervisedResult:
    """Result of the single-wait, sleep-excluding Windows supervisor."""

    disposition_basis: str
    wait_result: int
    termination_action: str
    exit_code: int | None
    unbiased_seconds: float
    wall_seconds: float
    stdout: str = ""
    stderr: str = ""
    stdout_temp_path: str | None = None
    stderr_temp_path: str | None = None
    cleanup_outcome: Mapping[str, Any] | None = None
    job_cpu_seconds: float | None = None
    load_window_unbiased_seconds: float | None = None


@dataclass
class SpawnRetryState:
    """Mutable retry budget and immutable-predecessor history for one claim."""

    retry_count: int = 0
    failures: list[dict[str, Any]] = field(default_factory=list)


class _SpawnRetryLedgerError(InfrastructureError):
    """Fail-closed operational-ledger error with a structured failure stage."""

    def __init__(self, message: str, *, failure_stage: str):
        super().__init__(message)
        self.failure_stage = failure_stage


def is_transient_spawn_failure(
    supervised: SupervisedResult,
    timeout_seconds: float,
) -> bool:
    """Match only the observed silent, near-instant DLL-init failure signature."""
    return (
        supervised.disposition_basis == "wait_signaled"
        and supervised.exit_code is not None
        and (int(supervised.exit_code) & 0xFFFFFFFF)
        in TRANSIENT_SPAWN_STATUS_ALLOWLIST
        and supervised.stdout.strip() == ""
        and supervised.stderr.strip() == ""
        and float(supervised.unbiased_seconds)
        < TRANSIENT_SPAWN_MAX_ELAPSED_SECONDS
        and float(supervised.unbiased_seconds) < float(timeout_seconds)
        and (
            float(supervised.wall_seconds) - float(supervised.unbiased_seconds)
        )
        < SUSPEND_THRESHOLD
    )


def supervisor_source_sha256() -> str:
    """Hash the complete source file containing the native supervisor."""
    return _sha256(Path(__file__))


def _query_unbiased_interrupt_time(bindings: Any | None = None) -> int:
    """Return sleep-excluding system uptime in 100 ns units."""
    if os.name != "nt":
        raise _SupervisorInfrastructureError(
            "The docking supervisor requires Windows 10 build 10240 or newer.",
            failure_stage="platform_gate",
        )
    bindings = bindings or _Win32Bindings()
    value = bindings.ctypes.c_ulonglong()
    bindings.ctypes.set_last_error(0)
    if not bindings.QueryUnbiasedInterruptTime(bindings.ctypes.byref(value)):
        error = bindings.ctypes.get_last_error()
        raise _SupervisorInfrastructureError(
            "QueryUnbiasedInterruptTime failed.",
            failure_stage="QueryUnbiasedInterruptTime",
            win32_error=error,
        )
    return int(value.value)


class _Win32Bindings:
    """Explicit 64-bit-safe Win32 ABI used by the docking supervisor."""

    def __init__(self) -> None:
        if os.name != "nt":
            raise _SupervisorInfrastructureError(
                "The docking supervisor requires Windows 10 build 10240 or newer.",
                failure_stage="platform_gate",
            )
        if sys.getwindowsversion().build < MINIMUM_WINDOWS_BUILD:
            raise _SupervisorInfrastructureError(
                "The docking supervisor requires Windows 10 build 10240 or newer.",
                failure_stage="platform_gate",
            )

        import ctypes
        from ctypes import wintypes

        self.ctypes = ctypes
        self.wintypes = wintypes
        self.kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

        ULONG_PTR = wintypes.WPARAM
        SIZE_T = ctypes.c_size_t

        class SECURITY_ATTRIBUTES(ctypes.Structure):
            _fields_ = [
                ("nLength", wintypes.DWORD),
                ("lpSecurityDescriptor", wintypes.LPVOID),
                ("bInheritHandle", wintypes.BOOL),
            ]

        class STARTUPINFOW(ctypes.Structure):
            _fields_ = [
                ("cb", wintypes.DWORD),
                ("lpReserved", wintypes.LPWSTR),
                ("lpDesktop", wintypes.LPWSTR),
                ("lpTitle", wintypes.LPWSTR),
                ("dwX", wintypes.DWORD),
                ("dwY", wintypes.DWORD),
                ("dwXSize", wintypes.DWORD),
                ("dwYSize", wintypes.DWORD),
                ("dwXCountChars", wintypes.DWORD),
                ("dwYCountChars", wintypes.DWORD),
                ("dwFillAttribute", wintypes.DWORD),
                ("dwFlags", wintypes.DWORD),
                ("wShowWindow", wintypes.WORD),
                ("cbReserved2", wintypes.WORD),
                ("lpReserved2", ctypes.POINTER(wintypes.BYTE)),
                ("hStdInput", wintypes.HANDLE),
                ("hStdOutput", wintypes.HANDLE),
                ("hStdError", wintypes.HANDLE),
            ]

        class STARTUPINFOEXW(ctypes.Structure):
            _fields_ = [
                ("StartupInfo", STARTUPINFOW),
                ("lpAttributeList", wintypes.LPVOID),
            ]

        class PROCESS_INFORMATION(ctypes.Structure):
            _fields_ = [
                ("hProcess", wintypes.HANDLE),
                ("hThread", wintypes.HANDLE),
                ("dwProcessId", wintypes.DWORD),
                ("dwThreadId", wintypes.DWORD),
            ]

        class JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):
            _fields_ = [
                ("PerProcessUserTimeLimit", ctypes.c_longlong),
                ("PerJobUserTimeLimit", ctypes.c_longlong),
                ("LimitFlags", wintypes.DWORD),
                ("MinimumWorkingSetSize", SIZE_T),
                ("MaximumWorkingSetSize", SIZE_T),
                ("ActiveProcessLimit", wintypes.DWORD),
                ("Affinity", ULONG_PTR),
                ("PriorityClass", wintypes.DWORD),
                ("SchedulingClass", wintypes.DWORD),
            ]

        class IO_COUNTERS(ctypes.Structure):
            _fields_ = [
                ("ReadOperationCount", ctypes.c_ulonglong),
                ("WriteOperationCount", ctypes.c_ulonglong),
                ("OtherOperationCount", ctypes.c_ulonglong),
                ("ReadTransferCount", ctypes.c_ulonglong),
                ("WriteTransferCount", ctypes.c_ulonglong),
                ("OtherTransferCount", ctypes.c_ulonglong),
            ]

        class JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
            _fields_ = [
                ("BasicLimitInformation", JOBOBJECT_BASIC_LIMIT_INFORMATION),
                ("IoInfo", IO_COUNTERS),
                ("ProcessMemoryLimit", SIZE_T),
                ("JobMemoryLimit", SIZE_T),
                ("PeakProcessMemoryUsed", SIZE_T),
                ("PeakJobMemoryUsed", SIZE_T),
            ]

        class JOBOBJECT_BASIC_ACCOUNTING_INFORMATION(ctypes.Structure):
            _fields_ = [
                ("TotalUserTime", ctypes.c_longlong),
                ("TotalKernelTime", ctypes.c_longlong),
                ("ThisPeriodTotalUserTime", ctypes.c_longlong),
                ("ThisPeriodTotalKernelTime", ctypes.c_longlong),
                ("TotalPageFaultCount", wintypes.DWORD),
                ("TotalProcesses", wintypes.DWORD),
                ("ActiveProcesses", wintypes.DWORD),
                ("TotalTerminatedProcesses", wintypes.DWORD),
            ]

        self.SECURITY_ATTRIBUTES = SECURITY_ATTRIBUTES
        self.STARTUPINFOEXW = STARTUPINFOEXW
        self.PROCESS_INFORMATION = PROCESS_INFORMATION
        self.JOBOBJECT_EXTENDED_LIMIT_INFORMATION = JOBOBJECT_EXTENDED_LIMIT_INFORMATION
        self.JOBOBJECT_BASIC_ACCOUNTING_INFORMATION = (
            JOBOBJECT_BASIC_ACCOUNTING_INFORMATION
        )

        self.QueryUnbiasedInterruptTime = self.kernel32.QueryUnbiasedInterruptTime
        self.QueryUnbiasedInterruptTime.argtypes = [ctypes.POINTER(ctypes.c_ulonglong)]
        self.QueryUnbiasedInterruptTime.restype = wintypes.BOOL

        self.CreateJobObjectW = self.kernel32.CreateJobObjectW
        self.CreateJobObjectW.argtypes = [wintypes.LPVOID, wintypes.LPCWSTR]
        self.CreateJobObjectW.restype = wintypes.HANDLE

        self.SetInformationJobObject = self.kernel32.SetInformationJobObject
        self.SetInformationJobObject.argtypes = [
            wintypes.HANDLE,
            ctypes.c_int,
            wintypes.LPVOID,
            wintypes.DWORD,
        ]
        self.SetInformationJobObject.restype = wintypes.BOOL

        self.QueryInformationJobObject = self.kernel32.QueryInformationJobObject
        self.QueryInformationJobObject.argtypes = [
            wintypes.HANDLE,
            ctypes.c_int,
            wintypes.LPVOID,
            wintypes.DWORD,
            ctypes.POINTER(wintypes.DWORD),
        ]
        self.QueryInformationJobObject.restype = wintypes.BOOL

        self.InitializeProcThreadAttributeList = (
            self.kernel32.InitializeProcThreadAttributeList
        )
        self.InitializeProcThreadAttributeList.argtypes = [
            wintypes.LPVOID,
            wintypes.DWORD,
            wintypes.DWORD,
            ctypes.POINTER(SIZE_T),
        ]
        self.InitializeProcThreadAttributeList.restype = wintypes.BOOL

        self.UpdateProcThreadAttribute = self.kernel32.UpdateProcThreadAttribute
        self.UpdateProcThreadAttribute.argtypes = [
            wintypes.LPVOID,
            wintypes.DWORD,
            SIZE_T,
            wintypes.LPVOID,
            SIZE_T,
            wintypes.LPVOID,
            ctypes.POINTER(SIZE_T),
        ]
        self.UpdateProcThreadAttribute.restype = wintypes.BOOL

        self.DeleteProcThreadAttributeList = self.kernel32.DeleteProcThreadAttributeList
        self.DeleteProcThreadAttributeList.argtypes = [wintypes.LPVOID]
        self.DeleteProcThreadAttributeList.restype = None

        self.CreateProcessW = self.kernel32.CreateProcessW
        self.CreateProcessW.argtypes = [
            wintypes.LPCWSTR,
            wintypes.LPWSTR,
            wintypes.LPVOID,
            wintypes.LPVOID,
            wintypes.BOOL,
            wintypes.DWORD,
            wintypes.LPVOID,
            wintypes.LPCWSTR,
            wintypes.LPVOID,
            ctypes.POINTER(PROCESS_INFORMATION),
        ]
        self.CreateProcessW.restype = wintypes.BOOL

        self.ResumeThread = self.kernel32.ResumeThread
        self.ResumeThread.argtypes = [wintypes.HANDLE]
        self.ResumeThread.restype = wintypes.DWORD

        self.TerminateJobObject = self.kernel32.TerminateJobObject
        self.TerminateJobObject.argtypes = [wintypes.HANDLE, wintypes.UINT]
        self.TerminateJobObject.restype = wintypes.BOOL

        self.WaitForSingleObject = self.kernel32.WaitForSingleObject
        self.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        self.WaitForSingleObject.restype = wintypes.DWORD

        self.GetExitCodeProcess = self.kernel32.GetExitCodeProcess
        self.GetExitCodeProcess.argtypes = [
            wintypes.HANDLE,
            ctypes.POINTER(wintypes.DWORD),
        ]
        self.GetExitCodeProcess.restype = wintypes.BOOL

        self.CloseHandle = self.kernel32.CloseHandle
        self.CloseHandle.argtypes = [wintypes.HANDLE]
        self.CloseHandle.restype = wintypes.BOOL

        self.CreateFileW = self.kernel32.CreateFileW
        self.CreateFileW.argtypes = [
            wintypes.LPCWSTR,
            wintypes.DWORD,
            wintypes.DWORD,
            ctypes.POINTER(SECURITY_ATTRIBUTES),
            wintypes.DWORD,
            wintypes.DWORD,
            wintypes.HANDLE,
        ]
        self.CreateFileW.restype = wintypes.HANDLE


def _run_vina_supervised(
    cmd: Sequence[str | Path],
    timeout_seconds: float,
    *,
    cwd: Path,
    temp_dir: Path,
    collect_job_accounting: bool = False,
) -> SupervisedResult:
    """Launch one child atomically in a Job and arm one sleep-excluding wait."""
    if not math.isfinite(float(timeout_seconds)) or timeout_seconds <= 0:
        raise _SupervisorInfrastructureError(
            "Supervisor timeout must be finite and positive.",
            failure_stage="input_validation",
        )
    timeout_ms = round(float(timeout_seconds) * 1000)
    if timeout_ms <= 0 or timeout_ms >= INFINITE:
        raise _SupervisorInfrastructureError(
            "Supervisor timeout cannot be represented by WaitForSingleObject.",
            failure_stage="input_validation",
        )

    bindings = _Win32Bindings()
    ctypes = bindings.ctypes
    wintypes = bindings.wintypes
    temp_dir.mkdir(parents=True, exist_ok=True)
    log_paths: list[Path] = []
    owned_handles: list[tuple[str, Any]] = []
    job_handle = None
    process_handle = None
    thread_handle = None
    attribute_list = None
    attribute_initialized = False
    child_created = False
    job_terminated = False
    unbiased_start: int | None = None
    load_window_unbiased_start: int | None = None
    wall_start: float | None = None
    failure: _SupervisorInfrastructureError | None = None
    disposition_basis: str | None = None
    wait_result: int | None = None
    termination_action = "none"
    exit_code: int | None = None
    stdout = ""
    stderr = ""
    wall_seconds: float | None = None
    unbiased_seconds: float | None = None
    job_cpu_seconds: float | None = None
    load_window_unbiased_seconds: float | None = None
    cleanup: dict[str, Any] = {
        "job_terminated": False,
        "child_reaped": False,
        "attribute_list_deleted": False,
        "handles_closed": [],
        "temp_logs_removed": [],
    }

    def fail(stage: str, message: str, error: int | None = None) -> None:
        raise _SupervisorInfrastructureError(
            message,
            failure_stage=stage,
            win32_error=error,
            exit_code=exit_code,
        )

    def last_error() -> int:
        return int(ctypes.get_last_error())

    def create_inheritable_file(path: Path, access: int) -> Any:
        attributes = bindings.SECURITY_ATTRIBUTES()
        attributes.nLength = ctypes.sizeof(attributes)
        attributes.bInheritHandle = True
        ctypes.set_last_error(0)
        handle = bindings.CreateFileW(
            str(path),
            access,
            0x00000001 | 0x00000002 | 0x00000004,
            ctypes.byref(attributes),
            3,
            0x00000100,
            None,
        )
        if not handle or handle == ctypes.c_void_p(-1).value:
            fail("CreateFileW", f"Could not open inherited handle for {path}.", last_error())
        return handle

    try:
        limit = bindings.JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
        limit.BasicLimitInformation.LimitFlags = 0x00002000
        ctypes.set_last_error(0)
        job_handle = bindings.CreateJobObjectW(None, None)
        if not job_handle:
            fail("CreateJobObjectW", "CreateJobObjectW failed.", last_error())
        owned_handles.append(("job", job_handle))

        ctypes.set_last_error(0)
        if not bindings.SetInformationJobObject(
            job_handle,
            9,
            ctypes.byref(limit),
            ctypes.sizeof(limit),
        ):
            fail(
                "SetInformationJobObject",
                "Could not set JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE.",
                last_error(),
            )

        for label in ("stdout", "stderr"):
            descriptor, name = tempfile.mkstemp(
                prefix="vina-supervisor-",
                suffix=f".{label}.log",
                dir=temp_dir,
            )
            os.close(descriptor)
            log_paths.append(Path(name))

        stdout_handle = create_inheritable_file(log_paths[0], 0x40000000)
        owned_handles.append(("stdout", stdout_handle))
        stderr_handle = create_inheritable_file(log_paths[1], 0x40000000)
        owned_handles.append(("stderr", stderr_handle))
        stdin_handle = create_inheritable_file(Path("NUL"), 0x80000000)
        owned_handles.append(("stdin", stdin_handle))

        attribute_size = ctypes.c_size_t()
        ctypes.set_last_error(0)
        bindings.InitializeProcThreadAttributeList(
            None, 2, 0, ctypes.byref(attribute_size)
        )
        if last_error() != 122 or attribute_size.value == 0:
            fail(
                "InitializeProcThreadAttributeList(size)",
                "Could not size the process attribute list.",
                last_error(),
            )
        attribute_list = ctypes.create_string_buffer(attribute_size.value)
        ctypes.set_last_error(0)
        if not bindings.InitializeProcThreadAttributeList(
            attribute_list, 2, 0, ctypes.byref(attribute_size)
        ):
            fail(
                "InitializeProcThreadAttributeList",
                "Could not initialize the process attribute list.",
                last_error(),
            )
        attribute_initialized = True

        job_values = (wintypes.HANDLE * 1)(job_handle)
        inherited_values = (wintypes.HANDLE * 3)(
            stdin_handle, stdout_handle, stderr_handle
        )
        for stage, attribute, values in (
            ("UpdateProcThreadAttribute(JOB_LIST)", 0x0002000D, job_values),
            ("UpdateProcThreadAttribute(HANDLE_LIST)", 0x00020002, inherited_values),
        ):
            ctypes.set_last_error(0)
            if not bindings.UpdateProcThreadAttribute(
                attribute_list,
                0,
                attribute,
                ctypes.cast(values, wintypes.LPVOID),
                ctypes.sizeof(values),
                None,
                None,
            ):
                fail(stage, f"{stage} failed.", last_error())

        startup = bindings.STARTUPINFOEXW()
        startup.StartupInfo.cb = ctypes.sizeof(startup)
        startup.StartupInfo.dwFlags = 0x00000100
        startup.StartupInfo.hStdInput = stdin_handle
        startup.StartupInfo.hStdOutput = stdout_handle
        startup.StartupInfo.hStdError = stderr_handle
        startup.lpAttributeList = ctypes.cast(attribute_list, wintypes.LPVOID)
        process_info = bindings.PROCESS_INFORMATION()
        application = str(Path(cmd[0]).resolve())
        command_line = ctypes.create_unicode_buffer(
            subprocess.list2cmdline([str(part) for part in cmd])
        )
        ctypes.set_last_error(0)
        if not bindings.CreateProcessW(
            application,
            command_line,
            None,
            None,
            True,
            0x00000004 | 0x00080000,
            None,
            str(cwd),
            ctypes.byref(startup),
            ctypes.byref(process_info),
        ):
            fail("CreateProcessW", "CreateProcessW failed.", last_error())
        child_created = True
        process_handle = process_info.hProcess
        thread_handle = process_info.hThread
        owned_handles.append(("process", process_handle))
        owned_handles.append(("thread", thread_handle))

        unbiased_start = _query_unbiased_interrupt_time(bindings)
        wall_start = time.perf_counter()
        ctypes.set_last_error(0)
        if collect_job_accounting:
            # The accounting numerator is cumulative over the entire Job.  Take the
            # enclosing denominator start before the child can execute so numerator
            # time can never precede the denominator.
            load_window_unbiased_start = _query_unbiased_interrupt_time(bindings)
        previous_suspend_count = int(bindings.ResumeThread(thread_handle))
        if previous_suspend_count != 1:
            fail(
                "ResumeThread",
                "ResumeThread did not report the required previous suspend count of 1.",
                last_error() if previous_suspend_count == WAIT_FAILED else None,
            )

        ctypes.set_last_error(0)
        wait_result = int(bindings.WaitForSingleObject(process_handle, timeout_ms))
        if wait_result == WAIT_TIMEOUT:
            disposition_basis = "deadline_timeout"
            termination_action = "TerminateJobObject"
            ctypes.set_last_error(0)
            if not bindings.TerminateJobObject(job_handle, 1):
                fail(
                    "TerminateJobObject",
                    "TerminateJobObject failed at the deadline.",
                    last_error(),
                )
            job_terminated = True
            cleanup["job_terminated"] = True
        elif wait_result == WAIT_OBJECT_0:
            disposition_basis = "wait_signaled"
            code = wintypes.DWORD()
            ctypes.set_last_error(0)
            if not bindings.GetExitCodeProcess(process_handle, ctypes.byref(code)):
                fail(
                    "GetExitCodeProcess",
                    "GetExitCodeProcess failed.",
                    last_error(),
                )
            exit_code = int(code.value)
            if exit_code == STILL_ACTIVE:
                fail(
                    "GetExitCodeProcess",
                    "A signaled process reported STILL_ACTIVE.",
                )
        else:
            fail(
                "WaitForSingleObject",
                f"WaitForSingleObject returned unexpected value {wait_result}.",
                last_error() if wait_result == WAIT_FAILED else None,
            )

        unbiased_end = _query_unbiased_interrupt_time(bindings)
        wall_end = time.perf_counter()
        unbiased_seconds = (unbiased_end - unbiased_start) / 10_000_000.0
        wall_seconds = wall_end - wall_start
    except BaseException as exc:
        if isinstance(exc, _SupervisorInfrastructureError):
            failure = exc
        else:
            failure = _SupervisorInfrastructureError(
                f"Supervisor interrupted by {type(exc).__name__}: {exc}",
                failure_stage="interruption",
            )
    finally:
        if job_handle and not job_terminated:
            ctypes.set_last_error(0)
            if bindings.TerminateJobObject(job_handle, 1):
                cleanup["job_terminated"] = True
            elif failure is None:
                failure = _SupervisorInfrastructureError(
                    "TerminateJobObject failed during cleanup.",
                    failure_stage="cleanup.TerminateJobObject",
                    win32_error=last_error(),
                )
        if child_created and process_handle:
            ctypes.set_last_error(0)
            reap_result = int(bindings.WaitForSingleObject(process_handle, 5000))
            cleanup["child_reaped"] = reap_result == WAIT_OBJECT_0
            if reap_result != WAIT_OBJECT_0 and failure is None:
                failure = _SupervisorInfrastructureError(
                    "Child could not be reaped during supervisor cleanup.",
                    failure_stage="cleanup.WaitForSingleObject",
                    win32_error=last_error() if reap_result == WAIT_FAILED else None,
                )
        if (
            collect_job_accounting
            and job_handle
            and load_window_unbiased_start is not None
        ):
            accounting = bindings.JOBOBJECT_BASIC_ACCOUNTING_INFORMATION()
            returned_length = wintypes.DWORD()
            ctypes.set_last_error(0)
            accounting_ok = bool(
                bindings.QueryInformationJobObject(
                    job_handle,
                    1,
                    ctypes.byref(accounting),
                    ctypes.sizeof(accounting),
                    ctypes.byref(returned_length),
                )
            )
            if accounting_ok:
                job_cpu_seconds = (
                    int(accounting.TotalUserTime) + int(accounting.TotalKernelTime)
                ) / 10_000_000.0
            elif failure is None:
                failure = _SupervisorInfrastructureError(
                    "QueryInformationJobObject failed for Job accounting.",
                    failure_stage="QueryInformationJobObject",
                    win32_error=last_error(),
                )
            try:
                # This endpoint follows termination, reap, and the accounting query,
                # while the Job handle is still live.  Thus numerator ⊆ denominator.
                load_window_unbiased_end = _query_unbiased_interrupt_time(bindings)
                load_window_unbiased_seconds = (
                    load_window_unbiased_end - load_window_unbiased_start
                ) / 10_000_000.0
            except _SupervisorInfrastructureError as exc:
                if failure is None:
                    failure = exc
        if attribute_initialized and attribute_list is not None:
            bindings.DeleteProcThreadAttributeList(attribute_list)
            cleanup["attribute_list_deleted"] = True
        for label, handle in reversed(owned_handles):
            ctypes.set_last_error(0)
            if bindings.CloseHandle(handle):
                cleanup["handles_closed"].append(label)
            elif failure is None:
                failure = _SupervisorInfrastructureError(
                    f"CloseHandle failed for {label}.",
                    failure_stage="cleanup.CloseHandle",
                    win32_error=last_error(),
                )
        if len(log_paths) == 2:
            try:
                stdout = log_paths[0].read_text(encoding="utf-8", errors="replace")
                stderr = log_paths[1].read_text(encoding="utf-8", errors="replace")
            except OSError as exc:
                if failure is None:
                    failure = _SupervisorInfrastructureError(
                        f"Could not read supervisor temp logs: {exc}",
                        failure_stage="cleanup.read_temp_logs",
                    )
        for path in log_paths:
            try:
                path.unlink(missing_ok=True)
                cleanup["temp_logs_removed"].append(path.name)
            except OSError as exc:
                if failure is None:
                    failure = _SupervisorInfrastructureError(
                        f"Could not remove supervisor temp log: {exc}",
                        failure_stage="cleanup.remove_temp_log",
                    )

    if failure is not None:
        if wall_seconds is None and wall_start is not None:
            wall_seconds = time.perf_counter() - wall_start
        if unbiased_seconds is None and unbiased_start is not None:
            try:
                unbiased_seconds = (
                    _query_unbiased_interrupt_time(bindings) - unbiased_start
                ) / 10_000_000.0
            except _SupervisorInfrastructureError:
                pass
        failure.cleanup_outcome = cleanup
        failure.wall_seconds = wall_seconds
        failure.unbiased_seconds = unbiased_seconds
        failure.exit_code = exit_code
        raise failure

    assert disposition_basis is not None
    assert wait_result is not None
    assert wall_seconds is not None
    assert unbiased_seconds is not None
    return SupervisedResult(
        disposition_basis=disposition_basis,
        wait_result=wait_result,
        termination_action=termination_action,
        exit_code=exit_code,
        unbiased_seconds=unbiased_seconds,
        wall_seconds=wall_seconds,
        stdout=stdout,
        stderr=stderr,
        stdout_temp_path=str(log_paths[0]) if log_paths else None,
        stderr_temp_path=str(log_paths[1]) if len(log_paths) > 1 else None,
        cleanup_outcome=cleanup,
        job_cpu_seconds=job_cpu_seconds,
        load_window_unbiased_seconds=load_window_unbiased_seconds,
    )


def build_vina_command(
    *,
    vina_executable: str | Path,
    receptor_pdbqt: str | Path,
    ligand_pdbqt: str | Path,
    box_center: Mapping[str, Any],
    box_size: Mapping[str, Any],
    out_path: Path,
    seed: int = DEFAULT_SEED,
    exhaustiveness: int = DEFAULT_EXHAUSTIVENESS,
    num_modes: int = DEFAULT_NUM_MODES,
    cpu: int = DEFAULT_CPU,
    scoring: str = DEFAULT_SCORING,
) -> list[str]:
    return [
        str(vina_executable),
        "--receptor",
        str(receptor_pdbqt),
        "--ligand",
        str(ligand_pdbqt),
        "--center_x",
        _fmt(box_center["x"]),
        "--center_y",
        _fmt(box_center["y"]),
        "--center_z",
        _fmt(box_center["z"]),
        "--size_x",
        _fmt(box_size["x"]),
        "--size_y",
        _fmt(box_size["y"]),
        "--size_z",
        _fmt(box_size["z"]),
        "--seed",
        str(seed),
        "--exhaustiveness",
        str(exhaustiveness),
        "--num_modes",
        str(num_modes),
        "--cpu",
        str(cpu),
        "--scoring",
        scoring,
        "--out",
        str(out_path),
    ]


def parse_vina_modes(stdout: str) -> tuple[dict[str, Any], ...]:
    modes: list[dict[str, Any]] = []
    in_table = False
    for line in stdout.splitlines():
        if line.strip().startswith("-----+"):
            in_table = True
            continue
        if not in_table:
            continue
        match = _MODE_ROW.match(line)
        if not match:
            if modes:
                break
            continue
        modes.append(
            {
                "mode": int(match.group(1)),
                "affinity_kcal_mol": float(match.group(2)),
                "rmsd_lb": float(match.group(3)),
                "rmsd_ub": float(match.group(4)),
            }
        )
    return tuple(modes)


def parse_pose_pdbqt_modes(text: str) -> tuple[dict[str, Any], ...]:
    """Recover docked modes from a Vina output pose file."""
    modes: list[dict[str, Any]] = []
    for line in text.splitlines():
        match = _POSE_RESULT.match(line.strip())
        if match:
            modes.append(
                {
                    "mode": len(modes) + 1,
                    "affinity_kcal_mol": float(match.group(1)),
                    "rmsd_lb": float(match.group(2)),
                    "rmsd_ub": float(match.group(3)),
                }
            )
    return tuple(modes)


def summarize_docking(modes: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    if not modes:
        raise DockingError("Docking produced no scored poses.")
    affinities = [float(mode["affinity_kcal_mol"]) for mode in modes]
    return {
        "best_affinity_kcal_mol": min(affinities),
        "mean_affinity_kcal_mol": mean(affinities),
        "mode_count": len(affinities),
    }


def dock_ligand(
    *,
    vina_executable: str | Path,
    receptor: Mapping[str, Any],
    entity_id: str | None = None,
    state_id: str = "state_01",
    ligand_id: str | None = None,
    ligand_pdbqt: str | Path,
    project_root: Path,
    output_dir: Path,
    workflow: str = "unspecified",
    species_catalog_sha256: str = "",
    attempt_manifest_sha256: str = "",
    software_versions: Mapping[str, Any] | None = None,
    seed: int = DEFAULT_SEED,
    exhaustiveness: int = DEFAULT_EXHAUSTIVENESS,
    num_modes: int = DEFAULT_NUM_MODES,
    cpu: int = DEFAULT_CPU,
    scoring: str = DEFAULT_SCORING,
    resume: bool = False,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    campaign_id: str | None = None,
    spawn_retry_sleep: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    """Dock one state in immutable attempt directories and select one authority."""
    entity_id = str(entity_id or ligand_id or "")
    state_id = str(state_id)
    if not entity_id:
        raise DockingError("dock_ligand requires entity_id.")
    if not state_id:
        raise DockingError("dock_ligand requires state_id.")
    if not math.isfinite(float(timeout_seconds)) or timeout_seconds <= 0:
        raise DockingError("timeout_seconds must be finite and positive.")

    project_root = project_root.resolve()
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    campaign_id = str(campaign_id or f"local-{_json_sha256({'output_dir': str(output_dir)})[:12]}")
    if _filename_component(campaign_id) != campaign_id:
        raise DockingError("campaign_id must be a safe immutable path component.")
    base = (
        f"{_filename_component(entity_id)}__{_filename_component(state_id)}"
        f"__{_filename_component(str(receptor['pocket_id']))}"
    )
    selection_path = output_dir / f"{_filename_component(workflow)}__{base}.selection.json"

    ligand_path = _resolve_project_path(ligand_pdbqt, project_root)
    receptor_path = _resolve_project_path(receptor["receptor_pdbqt_path"], project_root)
    vina_path = _resolve_project_path(vina_executable, project_root)
    for label, path in (
        ("ligand PDBQT", ligand_path),
        ("receptor PDBQT", receptor_path),
        ("Vina binary", vina_path),
    ):
        if not path.is_file():
            raise DockingError(f"{label} does not exist: {path}")

    ligand_hash = _sha256(ligand_path)
    receptor_hash = _sha256(receptor_path)
    vina_hash = _sha256(vina_path)
    timeout_ms = round(float(timeout_seconds) * 1000)
    supervisor_hash = supervisor_source_sha256()

    def attempt_context(attempt_instance_id: str) -> dict[str, Any]:
        attempt_dir = output_dir / attempt_instance_id
        out_path = attempt_dir / f"{base}.pdbqt"
        marker_path = attempt_dir / f"{base}.no_fit"
        sidecar_path = attempt_dir / f"{base}.run.json"
        command = build_vina_command(
            vina_executable=vina_path,
            receptor_pdbqt=receptor_path,
            ligand_pdbqt=ligand_path,
            box_center=receptor["box_center_angstrom"],
            box_size=receptor["box_size_angstrom"],
            out_path=out_path,
            seed=seed,
            exhaustiveness=exhaustiveness,
            num_modes=num_modes,
            cpu=cpu,
            scoring=scoring,
        )
        normalized_command = normalize_command(command, project_root)
        fingerprint_payload = {
            "run_schema_version": RUN_SCHEMA_VERSION,
            "command": normalized_command,
            "entity_id": entity_id,
            "state_id": state_id,
            "ligand_pdbqt_sha256": ligand_hash,
            "receptor_pdbqt_sha256": receptor_hash,
            "vina_binary_sha256": vina_hash,
            "box_center_angstrom": _axis_dict(receptor["box_center_angstrom"]),
            "box_size_angstrom": _axis_dict(receptor["box_size_angstrom"]),
            "seed": int(seed),
            "exhaustiveness": int(exhaustiveness),
            "num_modes": int(num_modes),
            "cpu": int(cpu),
            "scoring": str(scoring),
            "timeout_basis": TIMEOUT_BASIS,
            "clock_source": CLOCK_SOURCE,
            "timeout_seconds": float(timeout_seconds),
            "timeout_ms": timeout_ms,
            "wait_mechanism": WAIT_MECHANISM,
            "supervisor_source_sha256": supervisor_hash,
            "suspend_threshold_seconds": SUSPEND_THRESHOLD,
            "campaign_id": campaign_id,
            "species_catalog_sha256": species_catalog_sha256,
            "attempt_manifest_sha256": attempt_manifest_sha256,
        }
        fingerprint = _json_sha256(fingerprint_payload)
        return {
            "attempt_dir": attempt_dir,
            "out_path": out_path,
            "marker_path": marker_path,
            "sidecar_path": sidecar_path,
            "command": command,
            "common": {
                "run_schema_version": RUN_SCHEMA_VERSION,
                "fingerprint": fingerprint,
                "fingerprint_payload": fingerprint_payload,
                "workflow": workflow,
                "claim_key": f"{workflow}:{entity_id}:{state_id}:{receptor['pocket_id']}",
                "entity_id": entity_id,
                "state_id": state_id,
                "species_key": [entity_id, state_id],
                "ligand_id": entity_id,
                "pocket_id": receptor["pocket_id"],
                "pdb_id": receptor.get("pdb_id"),
                "command": normalized_command,
                "ligand_pdbqt_path": _relative_path(ligand_path, project_root),
                "ligand_pdbqt_sha256": ligand_hash,
                "receptor_pdbqt_path": _relative_path(receptor_path, project_root),
                "receptor_pdbqt_sha256": receptor_hash,
                "vina_binary_sha256": vina_hash,
                "box_center_angstrom": fingerprint_payload["box_center_angstrom"],
                "box_size_angstrom": fingerprint_payload["box_size_angstrom"],
                "seed": seed,
                "exhaustiveness": exhaustiveness,
                "num_modes": num_modes,
                "cpu": cpu,
                "scoring": scoring,
                "timeout_basis": TIMEOUT_BASIS,
                "clock_source": CLOCK_SOURCE,
                "timeout_seconds": float(timeout_seconds),
                "timeout_ms": timeout_ms,
                "wait_mechanism": WAIT_MECHANISM,
                "supervisor_source_sha256": supervisor_hash,
                "suspend_threshold_seconds": SUSPEND_THRESHOLD,
                "campaign_id": campaign_id,
                "species_catalog_sha256": species_catalog_sha256,
                "attempt_manifest_sha256": attempt_manifest_sha256,
                "software_versions": dict(software_versions or {}),
                "attempt_instance_id": attempt_instance_id,
                "sidecar_path": _relative_path(sidecar_path, project_root),
                "selection_manifest_path": _relative_path(selection_path, project_root),
            },
        }

    if resume:
        if not selection_path.is_file():
            raise DockingError(
                f"Resume refused: missing selection manifest {selection_path.name}."
            )
        try:
            selection = json.loads(selection_path.read_text(encoding="utf-8"))
            if selection["status"] != "authoritative_selected":
                raise KeyError("status")
            if selection["campaign_id"] != campaign_id:
                raise KeyError("campaign_id")
            selected_id = str(selection["selected_attempt_instance_id"])
        except (OSError, json.JSONDecodeError, KeyError) as exc:
            raise DockingError("Resume refused: invalid selection manifest.") from exc
        context = attempt_context(selected_id)
        return _resume_exact(
            common=context["common"],
            fingerprint=context["common"]["fingerprint"],
            out_path=context["out_path"],
            marker_path=context["marker_path"],
            sidecar_path=context["sidecar_path"],
            project_root=project_root,
        )

    if selection_path.exists():
        raise DockingError(
            "Fresh run refused: this campaign claim already has a selection manifest; "
            "use resume or a new campaign ID."
        )

    quarantined: list[dict[str, Any]] = []
    state = SpawnRetryState(retry_count=0, failures=[])

    def _run_one_spawn(
        state: SpawnRetryState,
        quarantined: Sequence[Mapping[str, Any]],
    ) -> tuple[SupervisedResult, dict[str, Any]]:
        while True:
            attempt_instance_id = uuid.uuid4().hex
            context = attempt_context(attempt_instance_id)
            attempt_dir = context["attempt_dir"]
            out_path = context["out_path"]
            marker_path = context["marker_path"]
            sidecar_path = context["sidecar_path"]
            common = context["common"]
            attempt_dir.mkdir(parents=False, exist_ok=False)
            try:
                supervised = _run_vina_supervised(
                    context["command"],
                    timeout_seconds,
                    cwd=project_root,
                    temp_dir=attempt_dir,
                )
            except BaseException as exc:
                if isinstance(exc, _SupervisorInfrastructureError):
                    failure_stage = exc.failure_stage
                    win32_error = exc.win32_error
                    cleanup_outcome = exc.cleanup_outcome
                    failure_exit_code = exc.exit_code
                    wall_seconds = exc.wall_seconds
                    unbiased_seconds = exc.unbiased_seconds
                else:
                    failure_stage = "supervisor_exception"
                    win32_error = None
                    cleanup_outcome = {"exception_type": type(exc).__name__}
                    failure_exit_code = None
                    wall_seconds = None
                    unbiased_seconds = None
                out_path.unlink(missing_ok=True)
                _atomic_text(
                    marker_path,
                    f"status=infrastructure_failure\nfailure_stage={failure_stage}\n",
                )
                record = _final_record(
                    common,
                    wall_seconds=wall_seconds,
                    unbiased_seconds=unbiased_seconds,
                    disposition_basis="infrastructure_failure",
                    wait_result=WAIT_FAILED,
                    termination_action="TerminateJobObject",
                    timing_ambiguous=False,
                    authoritative_selected=False,
                    status="infrastructure_failure",
                    cause="infrastructure_failure",
                    exit_code=failure_exit_code,
                    output_path=marker_path,
                    project_root=project_root,
                    resumed=False,
                    modes=(),
                    failure_stage=failure_stage,
                    win32_error=win32_error,
                    cleanup_outcome=cleanup_outcome,
                    spawn_failures=state.failures,
                    validate=False,
                )
                validate_run_record(record, allow_infrastructure=True)
                _atomic_json(sidecar_path, record)
                _atomic_json(
                    selection_path,
                    _selection_manifest(
                        common,
                        status="blocked_infrastructure_failure",
                        selected_attempt_instance_id=None,
                        quarantined=quarantined,
                        spawn_failures=state.failures,
                        blocking_attempt=record,
                    ),
                )
                raise InfrastructureError(
                    f"Docking infrastructure failed at {failure_stage}: {exc}",
                    run_record=record,
                ) from exc

            if is_transient_spawn_failure(supervised, timeout_seconds):
                if state.retry_count >= MAX_TRANSIENT_SPAWN_RETRIES:
                    out_path.unlink(missing_ok=True)
                    failure_stage = "transient_spawn_failure_exhausted"
                    _atomic_text(
                        marker_path,
                        f"status=infrastructure_failure\nfailure_stage={failure_stage}\n",
                    )
                    record = _final_record(
                        common,
                        wall_seconds=supervised.wall_seconds,
                        unbiased_seconds=supervised.unbiased_seconds,
                        disposition_basis="infrastructure_failure",
                        wait_result=supervised.wait_result,
                        termination_action=supervised.termination_action,
                        timing_ambiguous=False,
                        authoritative_selected=False,
                        status="infrastructure_failure",
                        cause="infrastructure_failure",
                        exit_code=0xC0000142,
                        output_path=marker_path,
                        project_root=project_root,
                        resumed=False,
                        modes=(),
                        stdout_tail=_tail(supervised.stdout),
                        stderr_tail=_tail(supervised.stderr),
                        failure_stage=failure_stage,
                        win32_error=None,
                        cleanup_outcome=supervised.cleanup_outcome,
                        spawn_failures=state.failures,
                        validate=False,
                    )
                    validate_run_record(record, allow_infrastructure=True)
                    _atomic_json(sidecar_path, record)
                    _atomic_json(
                        selection_path,
                        _selection_manifest(
                            common,
                            status="blocked_infrastructure_failure",
                            selected_attempt_instance_id=None,
                            quarantined=quarantined,
                            spawn_failures=state.failures,
                            blocking_attempt=record,
                        ),
                    )
                    raise InfrastructureError(
                        "Docking infrastructure exhausted the transient spawn-retry budget.",
                        run_record=record,
                    )

                if state.retry_count == 0:
                    try:
                        _register_spawn_retry_claim(
                            project_root,
                            campaign_id,
                            common["claim_key"],
                        )
                    except _SpawnRetryLedgerError as exc:
                        out_path.unlink(missing_ok=True)
                        failure_stage = exc.failure_stage
                        _atomic_text(
                            marker_path,
                            f"status=infrastructure_failure\nfailure_stage={failure_stage}\n",
                        )
                        record = _final_record(
                            common,
                            wall_seconds=supervised.wall_seconds,
                            unbiased_seconds=supervised.unbiased_seconds,
                            disposition_basis="infrastructure_failure",
                            wait_result=supervised.wait_result,
                            termination_action=supervised.termination_action,
                            timing_ambiguous=False,
                            authoritative_selected=False,
                            status="infrastructure_failure",
                            cause="infrastructure_failure",
                            exit_code=0xC0000142,
                            output_path=marker_path,
                            project_root=project_root,
                            resumed=False,
                            modes=(),
                            stdout_tail=_tail(supervised.stdout),
                            stderr_tail=_tail(supervised.stderr),
                            failure_stage=failure_stage,
                            win32_error=None,
                            cleanup_outcome=supervised.cleanup_outcome,
                            spawn_failures=state.failures,
                            validate=False,
                        )
                        validate_run_record(record, allow_infrastructure=True)
                        _atomic_json(sidecar_path, record)
                        _atomic_json(
                            selection_path,
                            _selection_manifest(
                                common,
                                status="blocked_infrastructure_failure",
                                selected_attempt_instance_id=None,
                                quarantined=quarantined,
                                spawn_failures=state.failures,
                                blocking_attempt=record,
                            ),
                        )
                        raise InfrastructureError(
                            f"Docking campaign spawn-retry ledger failed: {exc}",
                            run_record=record,
                        ) from exc

                out_path.unlink(missing_ok=True)
                _atomic_text(
                    marker_path,
                    "status=transient_spawn_failure\nexit_code=0xC0000142\n",
                )
                predecessor = _final_record(
                    common,
                    wall_seconds=supervised.wall_seconds,
                    unbiased_seconds=supervised.unbiased_seconds,
                    disposition_basis=supervised.disposition_basis,
                    wait_result=supervised.wait_result,
                    termination_action=supervised.termination_action,
                    timing_ambiguous=False,
                    authoritative_selected=False,
                    status="failed",
                    cause="transient_spawn_failure",
                    exit_code=0xC0000142,
                    output_path=marker_path,
                    project_root=project_root,
                    resumed=False,
                    modes=(),
                    stdout_tail=_tail(supervised.stdout),
                    stderr_tail=_tail(supervised.stderr),
                    cleanup_outcome=supervised.cleanup_outcome,
                    spawn_failures=state.failures,
                )
                _atomic_json(sidecar_path, predecessor)
                state.failures.append(
                    {
                        "attempt_instance_id": attempt_instance_id,
                        "exit_code": 0xC0000142,
                        "unbiased_seconds": float(supervised.unbiased_seconds),
                        "sidecar_path": common["sidecar_path"],
                        "sidecar_sha256": _sha256(sidecar_path),
                    }
                )
                _atomic_json(
                    selection_path,
                    _selection_manifest(
                        common,
                        status="retrying_spawn",
                        selected_attempt_instance_id=None,
                        quarantined=quarantined,
                        spawn_failures=state.failures,
                        blocking_attempt=None,
                    ),
                )
                spawn_retry_sleep(
                    TRANSIENT_SPAWN_BACKOFF_SECONDS[state.retry_count]
                )
                state.retry_count += 1
                continue

            return supervised, context

    for retry_index in range(MAX_SUSPENDED_RETRIES + 1):
        supervised, context = _run_one_spawn(state, quarantined)
        attempt_instance_id = context["common"]["attempt_instance_id"]
        out_path = context["out_path"]
        marker_path = context["marker_path"]
        sidecar_path = context["sidecar_path"]
        common = context["common"]

        wall_seconds = float(supervised.wall_seconds)
        unbiased_seconds = float(supervised.unbiased_seconds)
        suspend_gap = wall_seconds - unbiased_seconds
        suspend_detected = suspend_gap >= SUSPEND_THRESHOLD
        timing_ambiguous = (
            supervised.disposition_basis == "wait_signaled"
            and unbiased_seconds >= float(timeout_seconds)
        )
        quarantine_reason = (
            "suspend_detected"
            if suspend_detected
            else "timing_ambiguous" if timing_ambiguous else None
        )
        authoritative_selected = quarantine_reason is None

        modes: tuple[dict[str, Any], ...] = ()
        if supervised.disposition_basis == "deadline_timeout":
            out_path.unlink(missing_ok=True)
            _atomic_text(
                marker_path,
                f"status=timeout\ntimeout_seconds={float(timeout_seconds):.3f}\n",
            )
            status, cause, output_path = "no_fit", "timeout", marker_path
        elif supervised.disposition_basis != "wait_signaled":
            raise AssertionError("The supervisor returned a non-canonical disposition.")
        elif supervised.exit_code != 0:
            out_path.unlink(missing_ok=True)
            _atomic_text(
                marker_path,
                f"status=vina_exit_nonzero\nexit_code={supervised.exit_code}\n",
            )
            status, cause, output_path = "failed", "vina_exit_nonzero", marker_path
        elif not out_path.is_file():
            _atomic_text(marker_path, "status=missing_pose\n")
            status, cause, output_path = "failed", "missing_pose", marker_path
        else:
            modes = parse_pose_pdbqt_modes(out_path.read_text(encoding="utf-8"))
            if not modes:
                out_path.unlink(missing_ok=True)
                _atomic_text(marker_path, "status=unparseable_pose\n")
                status, cause, output_path = "failed", "unparseable_pose", marker_path
            elif summarize_docking(modes)["best_affinity_kcal_mol"] >= 0:
                marker_path.unlink(missing_ok=True)
                status = "operational_non_fit"
                cause = "non_negative_best_affinity"
                output_path = out_path
            else:
                marker_path.unlink(missing_ok=True)
                status, cause, output_path = "valid_fit", None, out_path

        record = _final_record(
            common,
            wall_seconds=wall_seconds,
            unbiased_seconds=unbiased_seconds,
            disposition_basis=supervised.disposition_basis,
            wait_result=supervised.wait_result,
            termination_action=supervised.termination_action,
            timing_ambiguous=timing_ambiguous,
            authoritative_selected=authoritative_selected,
            status=status,
            cause=cause,
            exit_code=supervised.exit_code,
            output_path=output_path,
            project_root=project_root,
            resumed=False,
            modes=modes,
            stdout_tail=_tail(supervised.stdout),
            stderr_tail=_tail(supervised.stderr),
            cleanup_outcome=supervised.cleanup_outcome,
            spawn_failures=state.failures,
        )
        _atomic_json(sidecar_path, record)

        if quarantine_reason is not None:
            quarantined.append(_attempt_qc_row(record, quarantine_reason, "quarantined"))
            halted = retry_index == MAX_SUSPENDED_RETRIES
            _atomic_json(
                selection_path,
                _selection_manifest(
                    common,
                    status="halted_quarantine_limit" if halted else "retrying",
                    selected_attempt_instance_id=None,
                    quarantined=quarantined,
                    spawn_failures=state.failures,
                    blocking_attempt=record if halted else None,
                ),
            )
            if not halted:
                continue
            raise InfrastructureError(
                f"Docking halted after {MAX_SUSPENDED_RETRIES} quarantined retries.",
                run_record=record,
            )

        resolved_quarantines = [
            {**row, "selection_status": "quarantined_superseded"}
            for row in quarantined
        ]
        record["quarantined_predecessors"] = resolved_quarantines
        _atomic_json(sidecar_path, record)
        _atomic_json(
            selection_path,
            _selection_manifest(
                common,
                status="authoritative_selected",
                selected_attempt_instance_id=attempt_instance_id,
                quarantined=resolved_quarantines,
                spawn_failures=state.failures,
                blocking_attempt=None,
            ),
        )

        if status == "valid_fit":
            return record
        message = f"{entity_id}/{state_id} vs {receptor['pocket_id']}: {cause}."
        raise DockingError(message, run_record=record)

    raise AssertionError("Unreachable suspended-retry state.")


def build_run_manifest(
    *,
    workflow: str,
    run_records: Sequence[Mapping[str, Any]],
    species_catalog_sha256: str,
    attempt_manifest_sha256: str,
    software_versions: Mapping[str, Any],
    project_root: Path,
    preparation_records: Sequence[Mapping[str, Any]] = (),
    metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Serialize the same validated run-record schema for every workflow."""
    records = [dict(record) for record in run_records]
    for record in records:
        validate_run_record(record)
        if record["workflow"] != workflow:
            raise DockingError(
                f"Run record workflow {record['workflow']!r} does not match {workflow!r}."
            )
        if record["species_catalog_sha256"] != species_catalog_sha256:
            raise DockingError("Run record species-catalog hash mismatch.")
        if record["attempt_manifest_sha256"] != attempt_manifest_sha256:
            raise DockingError("Run record attempt-manifest hash mismatch.")
        if float(record["timeout_seconds"]) != DEFAULT_TIMEOUT_SECONDS:
            raise DockingError("Campaign records must freeze the 1800 s timeout.")
        if int(record["timeout_ms"]) != DEFAULT_TIMEOUT_MS:
            raise DockingError("Campaign records must freeze timeout_ms=1800000.")
    vina_hashes = {record["vina_binary_sha256"] for record in records}
    if len(vina_hashes) > 1:
        raise DockingError("A workflow manifest cannot mix Vina binaries.")
    campaign_ids = {record["campaign_id"] for record in records}
    timeout_bases = {record["timeout_basis"] for record in records}
    supervisor_hashes = {record["supervisor_source_sha256"] for record in records}
    if len(campaign_ids) > 1:
        raise DockingError("A workflow manifest cannot mix campaigns.")
    if timeout_bases - {TIMEOUT_BASIS}:
        raise DockingError("A workflow manifest cannot mix timeout bases.")
    if len(supervisor_hashes) > 1:
        raise DockingError("A workflow manifest cannot mix supervisor source revisions.")
    timeout_qc = build_timeout_qc_report(records, project_root=project_root)
    validate_timeout_qc_gate(timeout_qc)
    from spycep_drug_discovery.ligand_preparation import (
        MMFF_MAX_ITERATIONS,
        MMFF_VARIANT,
    )

    return {
        "run_schema_version": RUN_SCHEMA_VERSION,
        "workflow": workflow,
        "status": "complete" if all(record["valid_fit"] for record in records) else "complete_with_dispositions",
        "species_catalog_sha256": species_catalog_sha256,
        "attempt_manifest_sha256": attempt_manifest_sha256,
        "software_versions": dict(software_versions),
        "campaign_id": next(iter(campaign_ids), None),
        "timeout_basis": TIMEOUT_BASIS,
        "clock_source": CLOCK_SOURCE,
        "timeout_seconds": DEFAULT_TIMEOUT_SECONDS,
        "timeout_ms": DEFAULT_TIMEOUT_MS,
        "wait_mechanism": WAIT_MECHANISM,
        "supervisor_source_sha256": next(iter(supervisor_hashes), supervisor_source_sha256()),
        "suspend_threshold_seconds": SUSPEND_THRESHOLD,
        "max_suspended_retries": MAX_SUSPENDED_RETRIES,
        "vina_binary_sha256": next(iter(vina_hashes), None),
        "mmff_variant": MMFF_VARIANT,
        "mmff_max_iterations": MMFF_MAX_ITERATIONS,
        "attempt_count": len(records),
        "disposition_counts": dict(
            sorted(
                {
                    status: sum(record["status"] == status for record in records)
                    for status in {record["status"] for record in records}
                }.items()
            )
        ),
        "ligand_preparation": [dict(record) for record in preparation_records],
        "run_records": records,
        "timeout_qc": timeout_qc,
        "timeout_qc_sha256": timeout_qc["report_sha256"],
        "metadata": dict(metadata or {}),
    }


def _spawn_failure_qc_row(
    failure: Mapping[str, Any],
    project_root: Path,
) -> dict[str, Any]:
    _validate_spawn_failure_entry(failure)
    sidecar_path = _resolve_project_path(failure["sidecar_path"], project_root)
    if not sidecar_path.is_file():
        raise DockingError("Spawn-failure predecessor sidecar is missing.")
    if _sha256(sidecar_path) != failure["sidecar_sha256"]:
        raise DockingError("Spawn-failure predecessor sidecar SHA-256 mismatch.")
    try:
        sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DockingError("Spawn-failure predecessor sidecar is unreadable.") from exc
    validate_run_record(sidecar)
    if sidecar["attempt_instance_id"] != failure["attempt_instance_id"]:
        raise DockingError("Spawn-failure predecessor attempt ID mismatch.")
    if sidecar["sidecar_path"] != failure["sidecar_path"]:
        raise DockingError("Spawn-failure predecessor sidecar path mismatch.")
    if (int(sidecar["exit_code"]) & 0xFFFFFFFF) != (
        int(failure["exit_code"]) & 0xFFFFFFFF
    ):
        raise DockingError("Spawn-failure predecessor exit code mismatch.")
    if not math.isclose(
        float(sidecar["unbiased_seconds"]),
        float(failure["unbiased_seconds"]),
        rel_tol=0.0,
        abs_tol=1e-9,
    ):
        raise DockingError("Spawn-failure predecessor duration mismatch.")
    if sidecar["status"] != "failed" or sidecar["cause"] != "transient_spawn_failure":
        raise DockingError("Spawn-failure predecessor lacks the transient disposition.")
    if sidecar["authoritative_selected"] is not False:
        raise DockingError("Spawn-failure predecessor cannot be authoritative.")
    supervised = SupervisedResult(
        disposition_basis=sidecar["disposition_basis"],
        wait_result=sidecar["wait_result"],
        termination_action=sidecar["termination_action"],
        exit_code=sidecar["exit_code"],
        unbiased_seconds=sidecar["unbiased_seconds"],
        wall_seconds=sidecar["wall_seconds"],
        stdout=sidecar.get("stdout_tail", ""),
        stderr=sidecar.get("stderr_tail", ""),
    )
    if not is_transient_spawn_failure(supervised, sidecar["timeout_seconds"]):
        raise DockingError("Spawn-failure predecessor sidecar is not allowlisted.")
    return {
        **dict(failure),
        "claim_key": sidecar["claim_key"],
        "status": sidecar["status"],
        "cause": sidecar["cause"],
        "disposition_basis": sidecar["disposition_basis"],
        "wait_result": sidecar["wait_result"],
        "termination_action": sidecar["termination_action"],
        "wall_seconds": sidecar["wall_seconds"],
        "timeout_seconds": sidecar["timeout_seconds"],
        "stdout_empty": sidecar.get("stdout_tail", "").strip() == "",
        "stderr_empty": sidecar.get("stderr_tail", "").strip() == "",
        "suspend_detected": sidecar["suspend_detected"],
        "timing_ambiguous": sidecar["timing_ambiguous"],
        "selection_status": "spawn_retry_predecessor",
    }


def _validate_embedded_spawn_failure_qc_row(row: Mapping[str, Any]) -> None:
    required = {
        "attempt_instance_id",
        "exit_code",
        "unbiased_seconds",
        "sidecar_path",
        "sidecar_sha256",
        "claim_key",
        "status",
        "cause",
        "disposition_basis",
        "wait_result",
        "termination_action",
        "wall_seconds",
        "timeout_seconds",
        "stdout_empty",
        "stderr_empty",
        "suspend_detected",
        "timing_ambiguous",
        "selection_status",
    }
    if set(row) != required:
        raise DockingError("Timeout-QC spawn-failure row fields mismatch.")
    _validate_spawn_failure_entry({key: row[key] for key in (
        "attempt_instance_id",
        "exit_code",
        "unbiased_seconds",
        "sidecar_path",
        "sidecar_sha256",
    )})
    if not isinstance(row["claim_key"], str) or not row["claim_key"]:
        raise DockingError("Timeout-QC spawn-failure row lacks a claim_key.")
    if row["status"] != "failed" or row["cause"] != "transient_spawn_failure":
        raise DockingError("Timeout-QC spawn-failure row disposition mismatch.")
    if row["stdout_empty"] is not True or row["stderr_empty"] is not True:
        raise DockingError("Timeout-QC spawn-failure row contains process output.")
    if row["suspend_detected"] is not False or row["timing_ambiguous"] is not False:
        raise DockingError("Timeout-QC spawn-failure row violates quarantine precedence.")
    if row["selection_status"] != "spawn_retry_predecessor":
        raise DockingError("Timeout-QC spawn-failure selection status mismatch.")
    supervised = SupervisedResult(
        disposition_basis=str(row["disposition_basis"]),
        wait_result=int(row["wait_result"]),
        termination_action=str(row["termination_action"]),
        exit_code=int(row["exit_code"]),
        unbiased_seconds=float(row["unbiased_seconds"]),
        wall_seconds=float(row["wall_seconds"]),
    )
    if not is_transient_spawn_failure(supervised, float(row["timeout_seconds"])):
        raise DockingError("Timeout-QC spawn-failure row is not allowlisted.")


def build_timeout_qc_report(
    run_records: Sequence[Mapping[str, Any]],
    *,
    project_root: Path,
) -> dict[str, Any]:
    """Build the content-addressed QC artifact consumed by the analysis gate."""
    attempts: list[dict[str, Any]] = []
    spawn_failure_attempts: list[dict[str, Any]] = []
    invalid: list[dict[str, str]] = []
    unresolved_quarantines = 0
    for raw in run_records:
        record = dict(raw)
        try:
            validate_run_record(record)
            for failure in record["spawn_failures"]:
                row = _spawn_failure_qc_row(failure, project_root)
                if row["claim_key"] != record["claim_key"]:
                    raise DockingError(
                        "Spawn-failure predecessor claim_key does not match its terminal."
                    )
                spawn_failure_attempts.append(row)
                attempts.append(row)
        except DockingError as exc:
            invalid.append(
                {
                    "attempt_instance_id": str(record.get("attempt_instance_id", "")),
                    "reason": str(exc),
                }
            )
        attempts.extend(dict(row) for row in record.get("quarantined_predecessors", ()))
        attempts.append(_attempt_qc_row(record, None, "authoritative_selected"))
    for row in attempts:
        if row.get("selection_status") in {"quarantined", "retrying"}:
            unresolved_quarantines += 1
        if row.get("disposition_basis") == "infrastructure_failure":
            unresolved_quarantines += 1
    payload = {
        "qc_schema_version": "docking-timeout-qc-v2",
        "run_schema_version": RUN_SCHEMA_VERSION,
        "timeout_basis": TIMEOUT_BASIS,
        "timeout_seconds": DEFAULT_TIMEOUT_SECONDS,
        "timeout_ms": DEFAULT_TIMEOUT_MS,
        "suspend_threshold_seconds": SUSPEND_THRESHOLD,
        "max_suspended_retries": MAX_SUSPENDED_RETRIES,
        "attempts": attempts,
        "spawn_failure_attempts": spawn_failure_attempts,
        "spawn_failure_attempt_count": len(spawn_failure_attempts),
        "invalid_records": invalid,
        "invalid_record_count": len(invalid),
        "unresolved_quarantine_count": unresolved_quarantines,
    }
    return {**payload, "report_sha256": _json_sha256(payload)}


def validate_timeout_qc_gate(report: Mapping[str, Any]) -> None:
    """Refuse analysis when timeout QC has invalid or unresolved attempts."""
    payload = {key: value for key, value in report.items() if key != "report_sha256"}
    if report.get("report_sha256") != _json_sha256(payload):
        raise DockingError("Timeout-QC content hash mismatch.")
    if report.get("run_schema_version") != RUN_SCHEMA_VERSION:
        raise DockingError("Timeout-QC run schema mismatch.")
    if report.get("timeout_basis") != TIMEOUT_BASIS:
        raise DockingError("Timeout-QC timeout basis mismatch.")
    if report.get("qc_schema_version") != "docking-timeout-qc-v2":
        raise DockingError("Timeout-QC schema mismatch.")
    spawn_failure_attempts = report.get("spawn_failure_attempts")
    if not isinstance(spawn_failure_attempts, list):
        raise DockingError("Timeout-QC lacks spawn-failure attempts.")
    if int(report.get("spawn_failure_attempt_count", -1)) != len(
        spawn_failure_attempts
    ):
        raise DockingError("Timeout-QC spawn-failure count mismatch.")
    for row in spawn_failure_attempts:
        if not isinstance(row, Mapping):
            raise DockingError("Timeout-QC spawn-failure row is not an object.")
        _validate_embedded_spawn_failure_qc_row(row)
    attempts = report.get("attempts")
    if not isinstance(attempts, list):
        raise DockingError("Timeout-QC attempts must be a list.")
    embedded_spawn_rows = [
        row
        for row in attempts
        if isinstance(row, Mapping)
        and row.get("selection_status") == "spawn_retry_predecessor"
    ]
    if embedded_spawn_rows != spawn_failure_attempts:
        raise DockingError("Timeout-QC attempts omit or alter spawn predecessors.")
    if int(report.get("invalid_record_count", -1)) != 0:
        raise DockingError("Timeout-QC gate found invalid records.")
    if int(report.get("unresolved_quarantine_count", -1)) != 0:
        raise DockingError("Timeout-QC gate found unresolved quarantines.")


def write_timeout_qc_report(
    output_dir: Path,
    run_records: Sequence[Mapping[str, Any]],
    *,
    project_root: Path,
) -> tuple[Path, dict[str, Any]]:
    """Persist one immutable, content-addressed timeout-QC artifact."""
    report = build_timeout_qc_report(run_records, project_root=project_root)
    validate_timeout_qc_gate(report)
    qc_dir = output_dir / "timeout_qc"
    qc_dir.mkdir(parents=True, exist_ok=True)
    path = qc_dir / f"timeout-qc-{report['report_sha256']}.json"
    if path.exists():
        try:
            stored = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise DockingError("Existing timeout-QC artifact is unreadable.") from exc
        if stored != report:
            raise DockingError("Content-addressed timeout-QC artifact collision.")
    else:
        _atomic_json(path, report)
    return path, report


def validate_manifest_timeout_qc(manifest: Mapping[str, Any]) -> None:
    """Analysis entry-point gate for schema-v3 docking manifests."""
    if manifest.get("run_schema_version") != RUN_SCHEMA_VERSION:
        raise DockingError("Analysis requires a schema-v3 docking manifest.")
    report = manifest.get("timeout_qc")
    if not isinstance(report, Mapping):
        raise DockingError("Analysis requires the timeout-QC artifact payload.")
    if manifest.get("timeout_qc_sha256") != report.get("report_sha256"):
        raise DockingError("Manifest timeout-QC hash mismatch.")
    validate_timeout_qc_gate(report)
    records = manifest.get("run_records", ())
    expected_spawn_rows: list[dict[str, Any]] = []
    for record in records:
        validate_run_record(record)
        expected_spawn_rows.extend(
            {
                **dict(failure),
                "claim_key": record["claim_key"],
            }
            for failure in record["spawn_failures"]
        )
    actual_spawn_rows = [
        {
            **{key: row[key] for key in (
                "attempt_instance_id",
                "exit_code",
                "unbiased_seconds",
                "sidecar_path",
                "sidecar_sha256",
            )},
            "claim_key": row["claim_key"],
        }
        for row in report["spawn_failure_attempts"]
    ]
    sort_key = lambda row: (
        row["claim_key"],
        row["attempt_instance_id"],
    )
    if sorted(expected_spawn_rows, key=sort_key) != sorted(
        actual_spawn_rows, key=sort_key
    ):
        raise DockingError(
            "Manifest run records and timeout-QC spawn predecessors differ."
        )


def validate_campaign_manifest_set(manifests: Sequence[Mapping[str, Any]]) -> None:
    """Block aggregate analysis across campaigns or timeout methods."""
    if not manifests:
        raise DockingError("Aggregate analysis requires at least one workflow manifest.")
    for manifest in manifests:
        validate_manifest_timeout_qc(manifest)
    for field in (
        "campaign_id",
        "timeout_basis",
        "clock_source",
        "timeout_seconds",
        "timeout_ms",
        "wait_mechanism",
        "supervisor_source_sha256",
        "run_schema_version",
    ):
        values = {manifest.get(field) for manifest in manifests}
        if len(values) != 1:
            raise DockingError(f"Aggregate manifests mix {field} values.")


def normalize_command(command: Sequence[str | Path], project_root: Path) -> list[str]:
    """Remove machine-specific absolute path prefixes from recorded commands."""
    normalized: list[str] = []
    root = project_root.resolve()
    for part in command:
        text = str(part)
        path = Path(text)
        if path.is_absolute():
            try:
                normalized.append(path.resolve().relative_to(root).as_posix())
            except ValueError:
                normalized.append(f"<ABSOLUTE>/{path.name}")
        else:
            normalized.append(text.replace("\\", "/"))
    return normalized


def _validate_spawn_failure_entry(entry: Mapping[str, Any]) -> None:
    required = {
        "attempt_instance_id",
        "exit_code",
        "unbiased_seconds",
        "sidecar_path",
        "sidecar_sha256",
    }
    if set(entry) != required:
        raise DockingError(
            "Spawn-failure predecessor fields do not match the schema."
        )
    if not isinstance(entry["attempt_instance_id"], str) or not entry[
        "attempt_instance_id"
    ]:
        raise DockingError("Spawn-failure predecessor lacks an attempt instance ID.")
    if (
        not isinstance(entry["exit_code"], int)
        or isinstance(entry["exit_code"], bool)
        or (int(entry["exit_code"]) & 0xFFFFFFFF)
        not in TRANSIENT_SPAWN_STATUS_ALLOWLIST
    ):
        raise DockingError("Spawn-failure predecessor exit code is not allowlisted.")
    unbiased_seconds = _finite_number(
        entry["unbiased_seconds"], "spawn_failures.unbiased_seconds"
    )
    if not 0 <= unbiased_seconds < TRANSIENT_SPAWN_MAX_ELAPSED_SECONDS:
        raise DockingError("Spawn-failure predecessor duration is outside the limit.")
    if not isinstance(entry["sidecar_path"], str) or not entry["sidecar_path"]:
        raise DockingError("Spawn-failure predecessor lacks a sidecar path.")
    if not re.fullmatch(r"[0-9a-f]{64}", str(entry["sidecar_sha256"])):
        raise DockingError("Spawn-failure predecessor lacks a valid sidecar SHA-256.")


def validate_run_record(
    record: Mapping[str, Any],
    *,
    allow_infrastructure: bool = False,
) -> None:
    """Validate v3 provenance, kernel disposition, and recomputed eligibility."""
    missing = RUN_RECORD_REQUIRED_FIELDS - set(record)
    if missing:
        raise DockingError(f"Run record lacks required provenance fields: {sorted(missing)}")
    if record["run_schema_version"] != RUN_SCHEMA_VERSION:
        raise DockingError("Run-record schema version mismatch.")
    if record["command"] == ["<resumed from existing pose file>"]:
        raise DockingError("Placeholder resume commands are forbidden.")
    if record["fingerprint"] != _json_sha256(record["fingerprint_payload"]):
        raise DockingError("Run-record fingerprint does not match its payload.")
    payload = record["fingerprint_payload"]
    mirrored_fields = (
        "run_schema_version",
        "command",
        "entity_id",
        "state_id",
        "ligand_pdbqt_sha256",
        "receptor_pdbqt_sha256",
        "vina_binary_sha256",
        "box_center_angstrom",
        "box_size_angstrom",
        "seed",
        "exhaustiveness",
        "num_modes",
        "cpu",
        "scoring",
        "timeout_basis",
        "clock_source",
        "timeout_seconds",
        "timeout_ms",
        "wait_mechanism",
        "supervisor_source_sha256",
        "suspend_threshold_seconds",
        "campaign_id",
        "species_catalog_sha256",
        "attempt_manifest_sha256",
    )
    missing_payload = set(mirrored_fields) - set(payload)
    if missing_payload:
        raise DockingError(
            f"Run-record fingerprint lacks v3 provenance: {sorted(missing_payload)}"
        )
    for field in mirrored_fields:
        if payload[field] != record[field]:
            raise DockingError(f"Run-record payload/top-level mismatch for {field}.")
    if int(record["cpu"]) != DEFAULT_CPU:
        raise DockingError("Run record did not freeze --cpu 1.")
    if record["scoring"] != DEFAULT_SCORING:
        raise DockingError("Run record did not freeze --scoring vina.")
    if record["timeout_basis"] != TIMEOUT_BASIS:
        raise DockingError("Run record timeout basis mismatch.")
    if record["clock_source"] != CLOCK_SOURCE:
        raise DockingError("Run record clock source mismatch.")
    if record["wait_mechanism"] != WAIT_MECHANISM:
        raise DockingError("Run record wait mechanism mismatch.")
    if float(record["suspend_threshold_seconds"]) != SUSPEND_THRESHOLD:
        raise DockingError("Run record suspend threshold mismatch.")
    timeout_seconds = _finite_number(record["timeout_seconds"], "timeout_seconds")
    if timeout_seconds <= 0:
        raise DockingError("Run-record timeout_seconds must be positive.")
    if int(record["timeout_ms"]) != round(timeout_seconds * 1000):
        raise DockingError("Run-record timeout_ms does not match timeout_seconds.")
    if record["status"] == "valid_fit" and not record["valid_fit"]:
        raise DockingError("valid_fit status is internally inconsistent.")
    if record["status"] != "valid_fit" and record["valid_fit"]:
        raise DockingError("Non-fit status is internally inconsistent.")

    spawn_retry_count = record["spawn_retry_count"]
    if (
        not isinstance(spawn_retry_count, int)
        or isinstance(spawn_retry_count, bool)
        or not 0 <= spawn_retry_count <= MAX_TRANSIENT_SPAWN_RETRIES
    ):
        raise DockingError("spawn_retry_count is outside the frozen retry budget.")
    spawn_failures = record["spawn_failures"]
    if not isinstance(spawn_failures, list):
        raise DockingError("spawn_failures must be a list.")
    if spawn_retry_count != len(spawn_failures):
        raise DockingError("spawn_retry_count does not match spawn_failures.")
    predecessor_ids: set[str] = set()
    predecessor_sidecars: set[str] = set()
    for failure in spawn_failures:
        if not isinstance(failure, Mapping):
            raise DockingError("spawn_failures entries must be objects.")
        _validate_spawn_failure_entry(failure)
        attempt_instance_id = str(failure["attempt_instance_id"])
        sidecar_path = str(failure["sidecar_path"])
        if attempt_instance_id in predecessor_ids or sidecar_path in predecessor_sidecars:
            raise DockingError("spawn_failures contains a duplicate predecessor.")
        predecessor_ids.add(attempt_instance_id)
        predecessor_sidecars.add(sidecar_path)

    disposition = record["disposition_basis"]
    if disposition not in {
        "wait_signaled",
        "deadline_timeout",
        "infrastructure_failure",
    }:
        raise DockingError("Run record has an unexpected disposition_basis.")
    if not isinstance(record["authoritative_selected"], bool):
        raise DockingError("authoritative_selected must be boolean.")

    if disposition == "infrastructure_failure":
        if record["status"] != "infrastructure_failure" or record["cause"] != "infrastructure_failure":
            raise DockingError("Infrastructure disposition has a scientific status/cause.")
        for field in ("failure_stage", "win32_error", "cleanup_outcome"):
            if field not in record:
                raise DockingError(f"Infrastructure record lacks {field}.")
        if record["authoritative_selected"]:
            raise DockingError("Infrastructure records can never be authoritative.")
        if not allow_infrastructure:
            raise InfrastructureError(
                "Infrastructure-failure record blocks the campaign.",
                run_record=record,
            )
        return

    wall_seconds = _finite_number(record["wall_seconds"], "wall_seconds")
    unbiased_seconds = _finite_number(record["unbiased_seconds"], "unbiased_seconds")
    elapsed_seconds = _finite_number(record["elapsed_seconds"], "elapsed_seconds")
    if min(wall_seconds, unbiased_seconds, elapsed_seconds) < 0:
        raise DockingError("Scientific record durations must be non-negative.")
    if not math.isclose(elapsed_seconds, wall_seconds, rel_tol=0.0, abs_tol=1e-9):
        raise DockingError("elapsed_seconds must equal wall_seconds in schema v3.")
    recomputed_gap = wall_seconds - unbiased_seconds
    persisted_gap = _finite_number(record["suspend_gap_seconds"], "suspend_gap_seconds")
    if not math.isclose(persisted_gap, recomputed_gap, rel_tol=0.0, abs_tol=1e-9):
        raise DockingError("Persisted suspend_gap_seconds does not recompute.")
    recomputed_suspend = recomputed_gap >= SUSPEND_THRESHOLD
    if not isinstance(record["suspend_detected"], bool):
        raise DockingError("suspend_detected must be boolean.")
    if record["suspend_detected"] != recomputed_suspend:
        raise DockingError("Persisted suspend_detected does not recompute.")

    canonical_timeout = record["status"] == "no_fit" and record["cause"] == "timeout"
    if disposition == "deadline_timeout":
        if not canonical_timeout:
            raise DockingError("deadline_timeout must carry canonical no_fit/timeout status.")
        if record["wait_result"] != WAIT_TIMEOUT:
            raise DockingError("deadline_timeout must carry WAIT_TIMEOUT.")
        if record["termination_action"] != "TerminateJobObject":
            raise DockingError("deadline_timeout must terminate the Job Object.")
        if record["timing_ambiguous"] is not False:
            raise DockingError("deadline_timeout cannot be timing_ambiguous.")
    else:
        if canonical_timeout:
            raise DockingError("Canonical no_fit/timeout must be deadline_timeout.")
        if record["wait_result"] != WAIT_OBJECT_0:
            raise DockingError("wait_signaled must carry WAIT_OBJECT_0.")
        if record["exit_code"] is None or int(record["exit_code"]) == STILL_ACTIVE:
            raise DockingError("wait_signaled must carry a retrieved terminal exit code.")
        if record["termination_action"] != "none":
            raise DockingError("wait_signaled cannot carry a deadline termination action.")
        recomputed_ambiguous = unbiased_seconds >= timeout_seconds
        if not isinstance(record["timing_ambiguous"], bool):
            raise DockingError("timing_ambiguous must be boolean.")
        if record["timing_ambiguous"] != recomputed_ambiguous:
            raise DockingError("Persisted timing_ambiguous does not recompute.")

    if (recomputed_suspend or bool(record["timing_ambiguous"])) and record[
        "authoritative_selected"
    ]:
        raise DockingError("A quarantined record cannot be authoritative.")


def _resume_exact(
    *,
    common: Mapping[str, Any],
    fingerprint: str,
    out_path: Path,
    marker_path: Path,
    sidecar_path: Path,
    project_root: Path,
) -> dict[str, Any]:
    if not sidecar_path.is_file():
        raise DockingError(
            f"Resume refused: missing sidecar {sidecar_path.name}; file existence is not provenance."
        )
    try:
        stored = json.loads(sidecar_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DockingError(f"Resume refused: unreadable sidecar {sidecar_path.name}.") from exc
    validate_run_record(stored)
    if stored.get("fingerprint") != fingerprint or stored.get("fingerprint_payload") != common.get(
        "fingerprint_payload"
    ):
        raise DockingError("Resume refused: run fingerprint does not exactly match.")
    if stored.get("command") != common.get("command"):
        raise DockingError("Resume refused: normalized effective command mismatch.")

    output_path_text = stored.get("out_path")
    if not output_path_text or not stored.get("out_sha256"):
        raise DockingError("Resume refused: sidecar lacks output path/hash.")
    output_path = _resolve_project_path(output_path_text, project_root)
    if not output_path.is_file() or _sha256(output_path) != stored["out_sha256"]:
        raise DockingError("Resume refused: sidecar/output hash agreement failed.")
    if out_path.is_file() and marker_path.is_file():
        raise DockingError("Resume refused: both pose and no-fit marker exist.")

    record = dict(stored)
    if stored.get("authoritative_selected") is not True:
        raise DockingError("Resume refused: selected sidecar is not authoritative.")
    record["resumed"] = True
    if stored["status"] == "valid_fit":
        if output_path != out_path:
            raise DockingError("Resume refused: valid-fit sidecar does not address the pose path.")
        modes = parse_pose_pdbqt_modes(output_path.read_text(encoding="utf-8"))
        if not modes:
            raise DockingError("Resume refused: pose no longer contains parseable modes.")
        record["modes"] = list(modes)
        record.update(summarize_docking(modes))
        validate_run_record(record)
        return record

    if stored["status"] in {"no_fit", "failed"} and output_path != marker_path:
        raise DockingError("Resume refused: failure sidecar does not address its marker.")
    if stored["status"] == "operational_non_fit" and output_path != out_path:
        raise DockingError("Resume refused: operational non-fit does not address its pose.")
    raise DockingError(
        f"Exact resumed attempt remains {stored['status']}: {stored.get('cause')}.",
        run_record=record,
    )


def _final_record(
    common: Mapping[str, Any],
    *,
    wall_seconds: float | None,
    unbiased_seconds: float | None,
    disposition_basis: str,
    wait_result: int | None,
    termination_action: str,
    timing_ambiguous: bool,
    authoritative_selected: bool,
    status: str,
    cause: str | None,
    exit_code: int | None,
    output_path: Path,
    project_root: Path,
    resumed: bool,
    modes: Sequence[Mapping[str, Any]],
    stdout_tail: str = "",
    stderr_tail: str = "",
    failure_stage: str | None = None,
    win32_error: int | None = None,
    cleanup_outcome: Mapping[str, Any] | None = None,
    spawn_failures: Sequence[Mapping[str, Any]] = (),
    validate: bool = True,
) -> dict[str, Any]:
    suspend_gap_seconds = (
        float(wall_seconds) - float(unbiased_seconds)
        if wall_seconds is not None and unbiased_seconds is not None
        else None
    )
    record = {
        **common,
        "elapsed_seconds": wall_seconds,
        "wall_seconds": wall_seconds,
        "unbiased_seconds": unbiased_seconds,
        "suspend_gap_seconds": suspend_gap_seconds,
        "suspend_detected": (
            suspend_gap_seconds is not None and suspend_gap_seconds >= SUSPEND_THRESHOLD
        ),
        "disposition_basis": disposition_basis,
        "wait_result": wait_result,
        "termination_action": termination_action,
        "timing_ambiguous": timing_ambiguous,
        "authoritative_selected": authoritative_selected,
        "status": status,
        "cause": cause,
        "exit_code": exit_code,
        "out_path": _relative_path(output_path, project_root),
        "out_sha256": _sha256(output_path),
        "resumed": resumed,
        "valid_fit": status == "valid_fit",
        "stdout_tail": stdout_tail,
        "stderr_tail": stderr_tail,
        "failure_stage": failure_stage,
        "win32_error": win32_error,
        "cleanup_outcome": dict(cleanup_outcome or {}),
        "modes": [dict(mode) for mode in modes],
        "spawn_retry_count": len(spawn_failures),
        "spawn_failures": [dict(failure) for failure in spawn_failures],
    }
    if modes:
        record.update(summarize_docking(modes))
    else:
        record.update(
            {
                "best_affinity_kcal_mol": None,
                "mean_affinity_kcal_mol": None,
                "mode_count": 0,
            }
        )
    if validate:
        validate_run_record(record)
    return record


def _selection_manifest(
    common: Mapping[str, Any],
    *,
    status: str,
    selected_attempt_instance_id: str | None,
    quarantined: Sequence[Mapping[str, Any]],
    spawn_failures: Sequence[Mapping[str, Any]],
    blocking_attempt: Mapping[str, Any] | None,
) -> dict[str, Any]:
    return {
        "selection_schema_version": "docking-selection-manifest-v2",
        "run_schema_version": RUN_SCHEMA_VERSION,
        "campaign_id": common["campaign_id"],
        "claim_key": common["claim_key"],
        "status": status,
        "selected_attempt_instance_id": selected_attempt_instance_id,
        "quarantined_attempts": [dict(row) for row in quarantined],
        "spawn_failure_attempts": [dict(row) for row in spawn_failures],
        "blocking_attempt_instance_id": (
            blocking_attempt.get("attempt_instance_id") if blocking_attempt else None
        ),
        "max_suspended_retries": MAX_SUSPENDED_RETRIES,
    }


def _attempt_qc_row(
    record: Mapping[str, Any],
    quarantine_reason: str | None,
    selection_status: str,
) -> dict[str, Any]:
    return {
        "attempt_instance_id": record.get("attempt_instance_id"),
        "claim_key": record.get("claim_key"),
        "unbiased_seconds": record.get("unbiased_seconds"),
        "wall_seconds": record.get("wall_seconds"),
        "suspend_gap_seconds": record.get("suspend_gap_seconds"),
        "suspend_detected": record.get("suspend_detected"),
        "timing_ambiguous": record.get("timing_ambiguous"),
        "disposition_basis": record.get("disposition_basis"),
        "status": record.get("status"),
        "cause": record.get("cause"),
        "quarantine_reason": quarantine_reason,
        "selection_status": selection_status,
        "sidecar_path": record.get("sidecar_path"),
    }


def is_continuable_scientific_disposition(record: Mapping[str, Any] | None) -> bool:
    """Return whether a workflow may append this disposition and continue."""
    if record is None or record.get("disposition_basis") == "infrastructure_failure":
        return False
    return (
        record.get("status") == "no_fit" and record.get("cause") == "timeout"
    ) or (
        record.get("status") == "operational_non_fit"
        and record.get("cause") == "non_negative_best_affinity"
    )


def require_campaign_id(value: str | None = None) -> str:
    """Require an explicit immutable campaign identifier at workflow entry points."""
    campaign_id = str(value or os.environ.get("SPYCEP_CAMPAIGN_ID", ""))
    if not campaign_id:
        raise DockingError("Set SPYCEP_CAMPAIGN_ID for a new isolated v3 campaign.")
    if _filename_component(campaign_id) != campaign_id:
        raise DockingError("SPYCEP_CAMPAIGN_ID must be a safe path component.")
    return campaign_id


def validate_suspend_calibration(record: Mapping[str, Any]) -> None:
    """Apply the immutable pre-campaign calibration abort gate."""
    required = {
        "calibration_schema_version",
        "duration_seconds",
        "load",
        "cpu",
        "max_observed_drift_seconds",
        "suspend_threshold_seconds",
    }
    missing = required - set(record)
    if missing:
        raise InfrastructureError(
            f"Suspend calibration lacks required fields: {sorted(missing)}"
        )
    if record["calibration_schema_version"] != "docking-suspend-calibration-v1":
        raise InfrastructureError("Suspend calibration schema mismatch.")
    if float(record["duration_seconds"]) != CALIBRATION_DURATION_SECONDS:
        raise InfrastructureError("Suspend calibration must run for exactly 10 minutes.")
    if record["load"] != "single_core_docking_equivalent" or int(record["cpu"]) != 1:
        raise InfrastructureError("Suspend calibration load is not docking-equivalent CPU 1.")
    if float(record["suspend_threshold_seconds"]) != SUSPEND_THRESHOLD:
        raise InfrastructureError("Suspend calibration attempted to change the fixed threshold.")
    drift = _finite_number(
        record["max_observed_drift_seconds"], "max_observed_drift_seconds"
    )
    if drift < 0 or drift > MAX_AWAKE_CALIBRATION_DRIFT_SECONDS:
        raise InfrastructureError(
            "Suspend calibration drift exceeds the fixed 0.5 s abort gate."
        )


def require_suspend_calibration(project_root: Path) -> dict[str, Any]:
    """Load and validate the operator-produced pre-campaign calibration artifact."""
    value = os.environ.get("SPYCEP_SUSPEND_CALIBRATION_PATH", "")
    if not value:
        raise InfrastructureError(
            "Set SPYCEP_SUSPEND_CALIBRATION_PATH after the required awake calibration."
        )
    path = _resolve_project_path(value, project_root)
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise InfrastructureError("Suspend calibration artifact is unreadable.") from exc
    validate_suspend_calibration(record)
    return record


def campaign_output_dir(project_root: Path, campaign_id: str, workflow: str) -> Path:
    """Return the shared no-reuse campaign root after validating the workflow key."""
    _filename_component(workflow)
    return project_root / DOCKING_OUTPUT_DIR / f"campaign_{_filename_component(campaign_id)}"


def _campaign_operational_dir(project_root: Path, campaign_id: str) -> Path:
    return campaign_output_dir(project_root, campaign_id, "operational") / "_operational"


def _spawn_retry_ledger_dir(project_root: Path, campaign_id: str) -> Path:
    return _campaign_operational_dir(project_root, campaign_id) / "spawn_retry"


def _spawn_retry_ledger_filename(claim_key: str) -> str:
    return hashlib.sha256(claim_key.encode("utf-8")).hexdigest() + ".json"


def _read_spawn_retry_ledger(
    project_root: Path,
    campaign_id: str,
) -> list[dict[str, Any]]:
    ledger_dir = _spawn_retry_ledger_dir(project_root, campaign_id)
    if not ledger_dir.is_dir():
        raise _SpawnRetryLedgerError(
            "The campaign spawn-retry ledger directory is absent or invalid.",
            failure_stage="spawn_retry_ledger_corrupt",
        )
    try:
        paths = sorted(ledger_dir.iterdir(), key=lambda path: path.name)
    except OSError as exc:
        raise _SpawnRetryLedgerError(
            f"Could not enumerate the campaign spawn-retry ledger: {exc}",
            failure_stage="spawn_retry_ledger_io",
        ) from exc
    entries: list[dict[str, Any]] = []
    claim_keys: set[str] = set()
    required_fields = {"ledger_schema_version", "campaign_id", "claim_key"}
    for path in paths:
        if not path.is_file() or path.suffix != ".json":
            raise _SpawnRetryLedgerError(
                f"Unexpected spawn-retry ledger entry: {path.name}",
                failure_stage="spawn_retry_ledger_corrupt",
            )
        try:
            entry = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise _SpawnRetryLedgerError(
                f"Unreadable spawn-retry ledger entry: {path.name}",
                failure_stage="spawn_retry_ledger_corrupt",
            ) from exc
        if not isinstance(entry, dict) or set(entry) != required_fields:
            raise _SpawnRetryLedgerError(
                f"Spawn-retry ledger entry schema mismatch: {path.name}",
                failure_stage="spawn_retry_ledger_corrupt",
            )
        if entry["ledger_schema_version"] != SPAWN_RETRY_LEDGER_SCHEMA_VERSION:
            raise _SpawnRetryLedgerError(
                f"Spawn-retry ledger schema mismatch: {path.name}",
                failure_stage="spawn_retry_ledger_corrupt",
            )
        if entry["campaign_id"] != campaign_id:
            raise _SpawnRetryLedgerError(
                f"Spawn-retry ledger campaign mismatch: {path.name}",
                failure_stage="spawn_retry_ledger_corrupt",
            )
        claim_key = entry["claim_key"]
        if not isinstance(claim_key, str) or not claim_key:
            raise _SpawnRetryLedgerError(
                f"Spawn-retry ledger claim_key is invalid: {path.name}",
                failure_stage="spawn_retry_ledger_corrupt",
            )
        if path.name != _spawn_retry_ledger_filename(claim_key):
            raise _SpawnRetryLedgerError(
                f"Spawn-retry ledger filename/hash mismatch: {path.name}",
                failure_stage="spawn_retry_ledger_corrupt",
            )
        if claim_key in claim_keys:
            raise _SpawnRetryLedgerError(
                f"Duplicate spawn-retry ledger claim_key: {claim_key}",
                failure_stage="spawn_retry_ledger_corrupt",
            )
        claim_keys.add(claim_key)
        entries.append(entry)
    if len(entries) > CAMPAIGN_TRANSIENT_SPAWN_BUDGET:
        raise _SpawnRetryLedgerError(
            "The campaign spawn-retry ledger exceeds the frozen host-degradation budget.",
            failure_stage="campaign_transient_spawn_budget_exceeded",
        )
    return sorted(entries, key=lambda entry: entry["claim_key"])


def initialize_spawn_retry_ledger(project_root: Path, campaign_id: str) -> Path:
    """Create the canonical empty ledger once; later absence is corruption."""
    campaign_root = campaign_output_dir(project_root, campaign_id, "operational")
    ledger_dir = _spawn_retry_ledger_dir(project_root, campaign_id)
    if not campaign_root.exists():
        try:
            ledger_dir.mkdir(parents=True, exist_ok=False)
        except OSError as exc:
            raise _SpawnRetryLedgerError(
                f"Could not initialize the campaign spawn-retry ledger: {exc}",
                failure_stage="spawn_retry_ledger_io",
            ) from exc
    elif not ledger_dir.is_dir():
        raise _SpawnRetryLedgerError(
            "Existing campaign root lacks its spawn-retry ledger directory.",
            failure_stage="spawn_retry_ledger_corrupt",
        )
    _read_spawn_retry_ledger(project_root, campaign_id)
    return ledger_dir


def _register_spawn_retry_claim(
    project_root: Path,
    campaign_id: str,
    claim_key: str,
) -> dict[str, Any]:
    """Exclusively register the first retry for one claim under the campaign lock."""
    entries = _read_spawn_retry_ledger(project_root, campaign_id)
    if any(entry["claim_key"] == claim_key for entry in entries):
        raise _SpawnRetryLedgerError(
            f"Duplicate spawn-retry ledger registration for {claim_key}.",
            failure_stage="spawn_retry_ledger_duplicate",
        )
    if len(entries) >= CAMPAIGN_TRANSIENT_SPAWN_BUDGET:
        raise _SpawnRetryLedgerError(
            "Transient spawn failures reached the frozen per-campaign budget; "
            "the host is degrading and the campaign is aborted.",
            failure_stage="campaign_transient_spawn_budget_exceeded",
        )
    entry = {
        "ledger_schema_version": SPAWN_RETRY_LEDGER_SCHEMA_VERSION,
        "campaign_id": campaign_id,
        "claim_key": claim_key,
    }
    path = _spawn_retry_ledger_dir(project_root, campaign_id) / (
        _spawn_retry_ledger_filename(claim_key)
    )
    try:
        _exclusive_json(path, entry)
    except FileExistsError as exc:
        raise _SpawnRetryLedgerError(
            f"Spawn-retry ledger entry already exists for {claim_key}.",
            failure_stage="spawn_retry_ledger_duplicate",
        ) from exc
    except OSError as exc:
        raise _SpawnRetryLedgerError(
            f"Could not write the spawn-retry ledger entry for {claim_key}: {exc}",
            failure_stage="spawn_retry_ledger_io",
        ) from exc
    verified = _read_spawn_retry_ledger(project_root, campaign_id)
    if len(verified) != len(entries) + 1 or entry not in verified:
        raise _SpawnRetryLedgerError(
            "Spawn-retry ledger did not verify after exclusive creation.",
            failure_stage="spawn_retry_ledger_corrupt",
        )
    return entry


def spawn_retry_ledger_content_sha256(project_root: Path, campaign_id: str) -> str:
    """Hash canonical ledger entries sorted by their full, unsanitized claim_key."""
    entries = _read_spawn_retry_ledger(project_root, campaign_id)
    return _canonical_json_sha256(entries)


def require_unsealed(project_root: Path, campaign_id: str) -> None:
    """Refuse a docking stage after the campaign completion barrier is sealed."""
    seal_path = _campaign_operational_dir(project_root, campaign_id) / "SEALED.json"
    if seal_path.exists():
        raise InfrastructureError(
            f"Campaign {campaign_id} is sealed and cannot accept docking writes."
        )


def seal_campaign(
    project_root: Path,
    campaign_id: str,
    stage_manifest_paths: Sequence[Path],
) -> dict[str, Any]:
    """Validate all four stages and exclusively create the campaign barrier seal."""
    with campaign_lock(project_root, campaign_id):
        seal_path = _campaign_operational_dir(project_root, campaign_id) / "SEALED.json"
        if seal_path.exists():
            raise InfrastructureError(f"Campaign {campaign_id} is already sealed.")
        if len(stage_manifest_paths) != 4:
            raise InfrastructureError("Campaign sealing requires exactly four stage manifests.")
        manifests: list[dict[str, Any]] = []
        for raw_path in stage_manifest_paths:
            path = _resolve_project_path(raw_path, project_root)
            try:
                manifest = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise InfrastructureError(
                    f"Campaign stage manifest is unreadable: {path}"
                ) from exc
            manifests.append(manifest)
        validate_campaign_manifest_set(manifests)
        workflows = [manifest.get("workflow") for manifest in manifests]
        if len(set(workflows)) != 4 or set(workflows) != {
            "wide",
            "tight",
            "speb",
            "boron",
        }:
            raise InfrastructureError(
                "Campaign sealing requires one WIDE, TIGHT, SpeB, and BORON manifest."
            )
        if any(manifest.get("campaign_id") != campaign_id for manifest in manifests):
            raise InfrastructureError("Campaign stage manifest ID does not match the seal.")

        ledger_entries = _read_spawn_retry_ledger(project_root, campaign_id)
        ledger_claim_keys = {entry["claim_key"] for entry in ledger_entries}
        manifest_claim_keys = {
            record["claim_key"]
            for manifest in manifests
            for record in manifest["run_records"]
            if int(record["spawn_retry_count"]) > 0
        }
        if ledger_claim_keys != manifest_claim_keys:
            raise InfrastructureError(
                "Campaign seal refused: spawn-retry ledger and terminal manifests differ."
            )
        ledger_hash = _canonical_json_sha256(ledger_entries)
        seal = {
            "seal_schema_version": CAMPAIGN_SEAL_SCHEMA_VERSION,
            "run_schema_version": RUN_SCHEMA_VERSION,
            "ledger_schema_version": SPAWN_RETRY_LEDGER_SCHEMA_VERSION,
            "campaign_id": campaign_id,
            "ledger_content_sha256": ledger_hash,
            "spawn_retry_claim_count": len(ledger_entries),
            "stage_workflows": sorted(workflows),
        }
        try:
            _exclusive_json(seal_path, seal)
        except FileExistsError as exc:
            raise InfrastructureError(
                f"Campaign {campaign_id} was sealed concurrently."
            ) from exc
        except OSError as exc:
            raise InfrastructureError("Could not create the campaign seal.") from exc
        return seal


def require_campaign_seal(project_root: Path, campaign_id: str) -> dict[str, Any]:
    """Require an immutable seal whose ledger hash still matches canonical content."""
    seal_path = _campaign_operational_dir(project_root, campaign_id) / "SEALED.json"
    try:
        seal = json.loads(seal_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise InfrastructureError(
            f"Campaign {campaign_id} lacks a readable completion seal."
        ) from exc
    required_fields = {
        "seal_schema_version",
        "run_schema_version",
        "ledger_schema_version",
        "campaign_id",
        "ledger_content_sha256",
        "spawn_retry_claim_count",
        "stage_workflows",
    }
    if not isinstance(seal, dict) or set(seal) != required_fields:
        raise InfrastructureError("Campaign completion seal schema mismatch.")
    if seal["seal_schema_version"] != CAMPAIGN_SEAL_SCHEMA_VERSION:
        raise InfrastructureError("Campaign completion seal version mismatch.")
    if seal["run_schema_version"] != RUN_SCHEMA_VERSION:
        raise InfrastructureError("Campaign completion seal run-schema mismatch.")
    if seal["ledger_schema_version"] != SPAWN_RETRY_LEDGER_SCHEMA_VERSION:
        raise InfrastructureError("Campaign completion seal ledger-schema mismatch.")
    if seal["campaign_id"] != campaign_id:
        raise InfrastructureError("Campaign completion seal ID mismatch.")
    if seal["stage_workflows"] != ["boron", "speb", "tight", "wide"]:
        raise InfrastructureError("Campaign completion seal workflow set mismatch.")
    ledger_entries = _read_spawn_retry_ledger(project_root, campaign_id)
    if seal["spawn_retry_claim_count"] != len(ledger_entries):
        raise InfrastructureError("Campaign completion seal ledger count mismatch.")
    if seal["ledger_content_sha256"] != _canonical_json_sha256(ledger_entries):
        raise InfrastructureError("Campaign completion seal ledger hash mismatch.")
    return seal


@contextmanager
def campaign_lock(project_root: Path, campaign_id: str) -> Iterator[None]:
    """Acquire the exclusive single-runner lock for all docking workflows."""
    lock_root = project_root / DOCKING_OUTPUT_DIR
    lock_root.mkdir(parents=True, exist_ok=True)
    lock_path = lock_root / ".docking-campaign.lock"
    try:
        descriptor = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as exc:
        raise InfrastructureError(
            f"Docking campaign lock already exists: {lock_path}."
        ) from exc
    try:
        os.write(
            descriptor,
            json.dumps(
                {
                    "campaign_id": campaign_id,
                    "pid": os.getpid(),
                    "created_unix_seconds": time.time(),
                },
                sort_keys=True,
            ).encode("utf-8"),
        )
        os.close(descriptor)
        descriptor = -1
        yield
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        lock_path.unlink(missing_ok=True)


def _finite_number(value: Any, field: str) -> float:
    if isinstance(value, bool):
        raise DockingError(f"Run-record {field} must be numeric.")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise DockingError(f"Run-record {field} must be numeric.") from exc
    if not math.isfinite(number):
        raise DockingError(f"Run-record {field} must be finite.")
    return number


def _axis_dict(values: Mapping[str, Any]) -> dict[str, float]:
    return {axis: float(_fmt(values[axis])) for axis in ("x", "y", "z")}


def _resolve_project_path(path: str | Path, project_root: Path) -> Path:
    value = Path(path)
    return value.resolve() if value.is_absolute() else (project_root / value).resolve()


def _delete_attempt_artifacts(*paths: Path) -> None:
    for path in paths:
        path.unlink(missing_ok=True)


def _atomic_text(path: Path, text: str) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    os.replace(temporary, path)


def _atomic_json(path: Path, value: Mapping[str, Any]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _exclusive_json(path: Path, value: Mapping[str, Any]) -> None:
    descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    try:
        payload = (json.dumps(value, indent=2) + "\n").encode("utf-8")
        offset = 0
        while offset < len(payload):
            written = os.write(descriptor, payload[offset:])
            if written <= 0:
                raise OSError("Exclusive JSON write made no progress.")
            offset += written
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _filename_component(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("._")
    if not cleaned:
        raise DockingError(f"Unsafe empty filename component from {value!r}.")
    return cleaned


def _fmt(value: Any) -> str:
    return f"{float(value):.3f}"


def _tail(text: str, line_count: int = 15) -> str:
    return "\n".join(text.splitlines()[-line_count:])


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_json_sha256(value: Any) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _json_sha256(value: Mapping[str, Any]) -> str:
    return _canonical_json_sha256(value)


def _relative_path(path: Path, project_root: Path) -> str:
    try:
        return path.resolve().relative_to(project_root.resolve()).as_posix()
    except ValueError:
        return f"<ABSOLUTE>/{path.name}"

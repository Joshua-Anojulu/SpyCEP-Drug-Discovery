# ADR-0001: Sleep-excluding wall-clock docking timeout

- Status: Accepted prospective post-incident amendment
- Date: 2026-07-15
- Decision owner: Joshua Anojulu
- Schema introduced: `docking-run-record-v2`

## Context

The frozen method specified a 1,800-second wall-clock ceiling but did not say whether time while the host was suspended counted. On 2026-07-15 that ambiguity became material: the recorded 7EDD sidecar for the sleep-touched azithromycin attempt reported 29,287 wall seconds and serialized a scientific `no_fit`/`timeout`. Suspended time therefore produced a scientific classification even though it was not docking opportunity.

The verified comparison evidence is limited to existing records: the affected 7EDD sidecar records 29,287 wall seconds, while the current azithromycin/5XYA record is a `valid_fit` at 1,429 seconds. A contemporaneous estimate of CPU time was not recorded and is not evidence for this decision. This ADR predicts no rerun outcome.

## Decision

Treat the frozen 1,800-second value prospectively as a sleep-excluding wall-clock ceiling. `QueryUnbiasedInterruptTime` measures the budgeted duration; raw `perf_counter` wall time remains recorded as `wall_seconds` and `elapsed_seconds` for observation. Suspended time may enlarge raw wall time, but cannot consume the timeout budget or create a scientific timeout.

On Windows, Vina is created suspended and atomically inside a Job Object using `CreateProcessW` with a `STARTUPINFOEX` `JOB_LIST` and restricted `HANDLE_LIST`. After the required `ResumeThread` result of exactly one, the supervisor enters one `WaitForSingleObject` call for 1,800,000 ms. `WAIT_TIMEOUT` is the only scientific timeout basis and triggers `TerminateJobObject`; `WAIT_OBJECT_0` is a signaled result. A signaled result observed at or beyond 1,800 unbiased seconds is timing-ambiguous and is quarantined, not accepted and not relabeled as a timeout.

Every execution has an immutable attempt instance directory. Attempts with a suspend gap of at least 5.0 seconds or with timing ambiguity are quarantined and rerun, up to two quarantined retries. Authority is assigned only through an atomic selection manifest. Infrastructure failures are recorded distinctly and abort the campaign.

The fixed 5.0-second suspend threshold is never auto-raised. Before a campaign, a 10-minute awake baseline under a single-core docking-equivalent load is an abort gate: maximum observed wall-minus-unbiased drift above 0.5 seconds requires investigation or a new signed amendment.

## Platform constraint

The implementation is Windows-pinned, stdlib-only `ctypes`, with a runtime minimum of Windows 10 build 10240. The `PROC_THREAD_ATTRIBUTE_JOB_LIST` launch mechanism sets that minimum. Non-Windows hosts and older Windows builds fail as infrastructure errors rather than falling back to different timeout semantics.

## Alternatives considered

- Process or Job CPU time was rejected because CPU time excludes awake scheduling, blocking, and I/O time. It would alter ordinary awake-wall behavior, not only sleep handling.
- Vina `max_evals` was rejected because it changes the search stop rule and would require separate prospective calibration and preregistration.
- `subprocess.Popen` followed by Job assignment was rejected because the child can run before assignment.
- Polling elapsed time or chunking waits was rejected because supervisor scheduling gaps can change the disposition.
- Raw wall time was rejected as the prospective basis because host suspension can fabricate a timeout.

## Consequences

Schema v2 records the kernel wait result, termination action, exit code, raw and unbiased durations, recomputed suspend/timing flags, supervisor fingerprint, and campaign identity. Validators reject cross-paired dispositions and bar quarantined or infrastructure records from authority. Boundary ligands completing very near exactly 1,800 awake seconds remain an inherent, pre-existing ceiling limitation; no deterministic outcome is asserted for them.

Signed: Joshua Anojulu, 2026-07-15

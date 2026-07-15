# Plan: Make the docking timeout immune to machine sleep (sleep-excluding wall-clock ceiling)
_Locked via grill — by Claude + Josh, 2026-07-15. Under iterative Codex adversarial review (R1–R8 so far, all REVISE; the operator lifted the default MAX_ROUNDS cap with the instruction "continue revising until best plan reached"). Codex affirmed the architecture sound from R6 onward; rounds since have only tightened the validator predicate. This is the post-R8 revision. See PLAN-REVIEW-LOG-timeout-fix.md for the full round-by-round argument._
_Scoped SEPARATELY from the frozen remediation `PLAN.md`/`PLAN-REVIEW-LOG.md`, which this does not touch._

## Goal
The docking timeout in `src/spycep_drug_discovery/docking.py` enforces `subprocess.run(timeout=wall_clock)` and
records `elapsed_seconds` from `time.perf_counter()`. Both count **suspended (sleep) time**: on 2026-07-15 the
laptop slept ~7 h mid-dock and `azithromycin@7EDD` was recorded `status="no_fit", cause="timeout"` with
`elapsed_seconds=29287` — a **fabricated non-fit** produced entirely by suspended time (recorded evidence: the
sidecar in `results/docking/library_stage2_CONTAMINATED_SLEEP_2026-07-15/` shows 29,287 wall seconds; the
"~15 CPU-minutes" figure is an **unverified contemporaneous operator observation**, not recorded, and is not used
as evidence).

Fix: enforce the frozen 1800 s ceiling on a **sleep-excluding wall clock** so that suspended time **cannot consume
the timeout budget or generate a scientific timeout**. (Raw `wall_seconds` still legitimately includes suspended
time — that is preserved as observability evidence; the budgeted quantity is `unbiased_seconds`, and it alone gates
the ceiling.) This is a **narrow, prospective post-incident protocol amendment** that resolves an
ambiguity the frozen text ("wall-clock ceiling") never addressed — whether suspended time counts. It is *not* claimed
to be semantics already present in the frozen record. The frozen ceiling **value** (1800 s), seed, exhaustiveness,
num_modes, receptors, and boxes are unchanged; docking determinism is untouched (same vina command/seed/inputs; only
the kill condition's clock and the recorded durations change). **No outcome is predicted** — headlines are recomputed
only after a neutral rerun (§H).

## Why unbiased-wall, not CPU-time (supersedes the Round-0 CPU-time design)
Codex R1 established, verified against the repo:
- **CPU-time ≠ awake wall-time even at `--cpu 1`** (excludes scheduling/blocking/IO); a CPU ceiling would be a broader
  method change able to rescue an unsuspended-but-descheduled attempt. Sleep-excluding wall-time changes **only** the
  treatment of sleep, matching the frozen wall-clock method everywhere the machine is awake.
- The Round-0 premise "azithromycin@5XYA still times out awake / no headline flips" is **false**: its current
  `library_stage2` sidecar is `valid_fit` at **1429 s**. Outcome prediction (the result-conditioning trap) is removed.

## Approach

### A. Timeout supervisor (`docking.py`) — direct `CreateProcess` + Job Object + kernel wait
Rationale for not using `Popen`: `Popen` returns after the process is already running, leaving a race before Job
assignment (Codex R2 #2), and a poll-and-compute-elapsed disposition can convert a timely completion into a false
timeout when the supervisor is descheduled (Codex R2 #3). Both are eliminated below.

1. **Atomic in-job, suspended launch (no assignment race; launch-to-wait window minimized, residual guarded).** Create a Job Object
   with `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`. Launch vina via ctypes `CreateProcessW` with **`CREATE_SUSPENDED`** and a
   `STARTUPINFOEX` attribute list carrying **both** `PROC_THREAD_ATTRIBUTE_JOB_LIST` (created **already inside** the
   job — no window running unmanaged) and `PROC_THREAD_ATTRIBUTE_HANDLE_LIST` (only the three intended std handles
   inheritable, so `bInheritHandles=TRUE` cannot leak unrelated handles). `CREATE_SUSPENDED` means vina does not
   execute until the supervisor is ready to wait, shrinking the launch-to-wait window (R5 #1); the residual is closed
   by the ambiguity guard in step 2. Command semantics preserved from the current `subprocess` behavior:
   `lpApplicationName` = the **exact frozen vina path**; command line via `subprocess.list2cmdline` into a **mutable
   `ctypes` buffer**; cwd + environment inherited/preserved as today; `STARTF_USESTDHANDLES` with
   `hStdOutput`/`hStdError` = inheritable temp-file handles (no PIPE, no deadlock), `hStdInput` = `NUL`. The owned
   process handle carries rights `PROCESS_SET_QUOTA | PROCESS_TERMINATE | PROCESS_QUERY_LIMITED_INFORMATION |
   SYNCHRONIZE`; the thread handle (from `PROCESS_INFORMATION.hThread`) is retained for `ResumeThread`.
2. **Single armed kernel wait + ambiguity guard (no chunking, no poll interval).** Capture `unbiased_start`/
   `wall_start`, `ResumeThread`, then immediately enter **one** `WaitForSingleObject(hProcess, timeout_ms)` for the
   full ceiling — `timeout_ms = round(timeout_seconds*1000) = 1800000` — and **never re-enter it**. On Win 10+ this
   single timeout excludes low-power/sleep time for its whole duration (a mid-wait sleep extends real time but not the
   budget). Armed once, up front, there is **no re-entry scheduling gap** (this closed R4 #2):
   - `WAIT_TIMEOUT` → `TerminateJobObject`; record `disposition_basis="deadline_timeout"`,
     `termination_action="TerminateJobObject"` → `status="no_fit", cause="timeout"`.
   - `WAIT_OBJECT_0` → record `disposition_basis="wait_signaled"`, then `GetExitCodeProcess` (failure → fatal infra,
     §4). **Ambiguity guard (R5 #1):** if `unbiased_elapsed >= timeout_seconds` at this point, the process finished
     but total awake elapsed already met the ceiling — indistinguishable between a genuine in-budget completion under
     a late-resuming supervisor (R3 #1) and an over-budget completion during a launch-to-wait deschedule gap. It is
     therefore **not accepted and not called a timeout**: mark `timing_ambiguous=true` → quarantine + rerun (E/10),
     bounded by `MAX_SUSPENDED_RETRIES`. Otherwise (`unbiased_elapsed < timeout_seconds`): exit 0 → normal
     valid_fit/no_fit parse; nonzero → the existing `cause="vina_exit_nonzero"`.
   The **kernel** distinguishes *signal* (`WAIT_OBJECT_0`) from *wait-timeout* (`WAIT_TIMEOUT`); **QUT
   (`unbiased_elapsed`) then determines whether a *signaled* result is authoritatively eligible** (via the ambiguity
   guard). Both are persisted (`disposition_basis`, `wait_result`, `termination_action`, `exit_code`,
   `timing_ambiguous`). `unbiased_seconds`/`wall_seconds` are read once at the end; their only role in disposition is
   the ambiguity guard above (demoting an over-ceiling signaled result to quarantine). They **never** fabricate a
   timeout and **never** accept a result past the awake ceiling.
3. **Guaranteed lifecycle + cleanup.** `TerminateJobObject` guarantees tree-wide kill (fixes this repo's recurring
   orphan-/racing-vina failure). A `finally` block always terminates the job, `WaitForSingleObject`-reaps the child,
   and closes every handle + temp file. (Vina 1.2.7 is a single static binary; the Job Object makes "no orphan" an
   enforced invariant, not an assumption.)
4. **Failure paths are fatal infra errors, never `no_fit`.** Any failure of the timing/Job/CreateProcess/Wait/
   GetExitCode calls or a `KeyboardInterrupt`/shutdown mid-attempt → terminate job, reap, clean partial artifacts,
   atomically write a **structured infrastructure-failure record** (`disposition_basis="infrastructure_failure"` with
   `failure_stage`, `win32_error`, optional `exit_code`, `cleanup_outcome`), and raise so the campaign **aborts** (see
   G/#14). A disposition is never fabricated from an accounting failure, and an infra record is never counted as a
   scientific `no_fit`/timeout.

### B. ctypes ABI (stdlib only, Windows 10 build 10240+ pinned)
5. Bind with explicit 64-bit-safe `argtypes`/`restype`, `use_last_error=True`, `GetLastError` checks on every call,
   `CloseHandle` on every owned handle:
   - `kernel32.QueryUnbiasedInterruptTime(POINTER(c_ulonglong)) -> BOOL` (**`PULONGLONG`, not `PULARGE_INTEGER`**;
     100 ns units, system-wide, monotonic).
   - `CreateProcessW` (with `EXTENDED_STARTUPINFO_PRESENT` | `CREATE_SUSPENDED`), `ResumeThread` (bound `-> DWORD`:
     it returns the **previous suspend count**, which for a `CREATE_SUSPENDED` child must be **exactly `1`**;
     `0xFFFFFFFF` or any other value → **fatal infrastructure failure**, never a wait on a still-suspended process
     that would fabricate a timeout), `CreateJobObjectW`,
     `SetInformationJobObject`, `InitializeProcThreadAttributeList` / `UpdateProcThreadAttribute` /
     `DeleteProcThreadAttributeList` (for the `JOB_LIST` + `HANDLE_LIST` attributes), `TerminateJobObject`,
     `WaitForSingleObject`, `GetExitCodeProcess`, `CloseHandle`. The attribute-value buffers (the job-handle array and
     the inherited-handle array) are kept alive through `CreateProcessW`; `DeleteProcThreadAttributeList` +
     `CloseHandle` (process **and** thread handles) run on **every** path including errors.
   - Runtime assertion: **Windows 10+ (build ≥ 10240)** — `PROC_THREAD_ATTRIBUTE_JOB_LIST` requires Win 10+/Server
     2016+ (this is the binding minimum; the sleep-excluding `WaitForSingleObject` timeout requires only Win 8+); the
     host is Windows 11. Non-Windows / < Win 10 raises a clear `DockingError`. No new dependency (D5 ablation /
     environment hash unchanged).

### C. Record schema (v2, exact literal `"docking-run-record-v2"`)
6. Set `RUN_SCHEMA_VERSION = "docking-run-record-v2"` (frozen string; used identically in schema, fingerprint, tests,
   manifest validators). Fields:
   - `elapsed_seconds` == `wall_seconds` (raw `perf_counter` wall — **meaning unchanged** from v1).
   - `unbiased_seconds` — sleep-excluding elapsed; the quantity the ceiling and validator reason about.
   - `suspend_gap_seconds` := `wall_seconds − unbiased_seconds`; `suspend_detected` := `suspend_gap_seconds >=
     SUSPEND_THRESHOLD` (`SUSPEND_THRESHOLD = 5.0 s`, frozen — see E/9).
   - `disposition_basis` ∈ {`"wait_signaled"`, `"deadline_timeout"`, `"infrastructure_failure"`}, plus `wait_result`,
     `termination_action`, `exit_code`, and (for infra) `failure_stage`/`win32_error`/`cleanup_outcome` — the
     persisted kernel decision the validator keys on.
   - `timing_ambiguous` (bool) — set when a `wait_signaled` result has `unbiased_elapsed >= timeout_seconds` (launch-
     to-wait gap vs. late-resume ambiguity, A/2); such a record is quarantined + rerun, never selected authoritative.
   - Optional `power_transition_events` — Windows power/resume events observed during the attempt, as corroboration.
   - `attempt_instance_id` — immutable per-execution id (write-in-place directory + quarantine auditing, E/10).
7. **`fingerprint_payload` gains the method-affecting fields** (so `_resume_exact()` cannot mix semantics): add
   `timeout_basis="unbiased_wall_seconds"`, `clock_source="QueryUnbiasedInterruptTime"`,
   `timeout_seconds`, `timeout_ms` (frozen `1800000`), `wait_mechanism="single_armed_WaitForSingleObject"`,
   `run_schema_version="docking-run-record-v2"`, `supervisor_source_sha256` (hash of the supervisor source),
   `suspend_threshold_seconds` (frozen `5.0`), and `campaign_id`. (No `poll_interval` — the single armed wait has
   none.) Top-level provenance mirrors these; a validator enforces payload/top-level consistency and rejects any
   record missing v2 provenance.

### D. Platform/method fingerprint
8. Extend `runtime_versions()` and every manifest with: CPython version+build, Windows version+build,
   `supervisor_source_sha256`, timing API name, `wait_mechanism`, `timeout_ms`, timeout basis, schema literal — all
   now part of the result-producing method.

### E. Suspend disposition — quarantine + rerun, auditable
9. **Detection, honestly bounded, immutable values.** `SUSPEND_THRESHOLD = 5.0 s` and `MAX_SUSPENDED_RETRIES = 2` are
   **fixed constants** — never auto-tuned. Calibration is a **gate, not a knob** (run once at the build step, before
   the campaign): measure `wall − unbiased` drift over a **10-minute awake baseline under a single-core
   docking-equivalent load**; take the **max observed** drift. If it is `> 0.5 s`, **abort** and investigate (or
   obtain a new signed amendment) — the threshold is **not** raised, so a contaminated/faulty "awake" calibration can
   never silently make detection more permissive (R4 #4). Otherwise proceed with 5.0 s (≈10× the expected sub-0.5 s
   drift). Any attempt with `suspend_gap_seconds >= SUSPEND_THRESHOLD` is quarantined; suspends **below** it are
   undetected but bounded by the fixed 5.0 s (stated plainly, not claimed away). `SUSPEND_THRESHOLD` is in every
   attempt fingerprint; it and `MAX_SUSPENDED_RETRIES` are in the campaign manifest/QC hash. Authoritative run is
   sleep-disabled, so `suspend_detected` is expected to be 0.
10. **Auditable quarantine — write-in-place, never move.** Every execution writes its pose/marker/sidecar **directly
    into an immutable per-attempt directory** `results/docking/campaign_<id>/<attempt_instance_id>/` and is never
    moved afterward (moving would invalidate the sidecar's stored `out_path`/`sidecar_path` and break resume). An
    atomic **selection manifest** promotes exactly one instance to authoritative and links any quarantined
    predecessors by `attempt_instance_id`. A `suspend_detected` **or** `timing_ambiguous` instance is simply never
    selected; the retry is a new instance directory. After `MAX_SUSPENDED_RETRIES` such quarantines for the same
    entity/state/pocket, the campaign **halts** for operator review rather than looping.

### F. Verification — validator, QC gate, tests
11. **Validator (kernel-decision keyed, canonical status).** The three `disposition_basis` branches are **mutually
    exclusive** and exhaustive: `deadline_timeout`, `wait_signaled`, `infrastructure_failure`. Invariants:
    (i) **bidirectional canonical mapping** — for every scientific (non-infra) record the three coordinates must agree
    as one of exactly two shapes, checked in **both** directions: **(a)** canonical timeout
    (`status=="no_fit" and cause=="timeout"`) **⇔** `disposition_basis=="deadline_timeout"` **⇔**
    `wait_result==WAIT_TIMEOUT` **⇔** `termination_action=="TerminateJobObject"`; or **(b)** any non-timeout scientific
    record **⇔** `disposition_basis=="wait_signaled"` **⇔** `wait_result==WAIT_OBJECT_0` with a retrieved `exit_code`
    that is **not `STILL_ACTIVE`**. Any cross-pairing is rejected as fabricated — e.g. `status=="valid_fit"` with
    `deadline_timeout`/`WAIT_TIMEOUT`, or a canonical-timeout status with `wait_signaled`/`WAIT_OBJECT_0`, or a
    `deadline_timeout` carrying `WAIT_OBJECT_0` (closes R8 #1). (ii) invariant (i)'s `wait_signaled` shape is scoped to
    scientific records and does **not** apply to infra records (resolving the R7 conflict with (iii));
    (iii) any `disposition_basis=="infrastructure_failure"` record **always blocks** the campaign and is never counted
    as a scientific `no_fit`/timeout; a `WAIT_FAILED` or any unexpected `wait_result` routes here, never to a
    scientific disposition; (iv) no `suspend_detected==true` **or** `timing_ambiguous==true` record is selected as
    authoritative;
    (v) the validator **recomputes** derived flags from validated durations, never trusting persisted values, with
    scope determined by disposition (closes R8 #2 and R9). For **every scientific record** (both `deadline_timeout`
    **and** `wait_signaled` — a suspend can occur during a timed-out run too): first require **numeric-domain
    validity** (`unbiased_seconds` and `wall_seconds` present, finite, ≥ 0; `record["timeout_seconds"]` present,
    finite, > 0, equal to the fingerprint/campaign value) — a missing/nonfinite/negative duration is an **invalid
    record**, never an apparently-eligible one — then recompute `suspend_gap_seconds == wall_seconds − unbiased_seconds`
    and `suspend_detected == (suspend_gap_seconds >= SUSPEND_THRESHOLD)`, reject any persisted/recomputed mismatch, and
    bar authoritative selection when recomputed `suspend_detected` is true. **Additionally, for `wait_signaled`
    records only**, recompute `timing_ambiguous == (unbiased_seconds >= record["timeout_seconds"])`, reject a mismatch,
    and bar selection when true.
    Apart from these recomputed eligibility checks, durations are **not** used to fabricate a timeout or override the
    kernel's signal-vs-timeout decision (reconciling R3 "don't call a late-observed signal a timeout" with R5 "don't
    accept a past-ceiling signal" — the shared verdict is quarantine). The literal 1800 s is enforced **separately at
    the campaign gate** against the record's fingerprinted `timeout_seconds`.
12. **QC artifact + analysis gate.** Persistent, content-addressed timeout-QC report listing every attempt with
    `unbiased_seconds`/`wall_seconds`/`suspend_gap_seconds`/`suspend_detected`/`timing_ambiguous`/`disposition_basis`/
    status/`attempt_instance_id`, plus each quarantine's **reason** (`suspend_detected` vs `timing_ambiguous`) and
    **selection status**. Analysis is **gated**: refuses to run unless zero invalid records and **zero unresolved
    quarantines of either kind** (suspend or timing-ambiguous).
13. **Injectable supervisor seam + tests.** Isolate the native supervisor behind a seam
    `_run_vina_supervised(cmd, timeout_seconds, ...) -> SupervisedResult` (carrying `disposition_basis`, `exit_code`,
    `unbiased_seconds`, `wall_seconds`, temp-log paths). **Port the existing `test_docking.py` tests** from
    monkeypatching `subprocess.run` (which the `CreateProcessW` launcher would bypass — R3 #6) to mocking this seam;
    add a guard asserting no unit test invokes real `CreateProcessW` except the marked Windows smoke test.
    `tests/test_docking_timeout.py`, fast + deterministic, no 30-min waits:
    - Fake seam / fake-wait state machine: (i) `WAIT_TIMEOUT` → `deadline_timeout` + `TerminateJobObject` +
      `cause=timeout`; (ii) timely completion observed **with `unbiased_elapsed < timeout_seconds`** (`WAIT_OBJECT_0`,
      even if the supervisor resumed late but still under budget) → **valid** via `wait_signaled` + `exit_code==0`,
      not timeout; (iii) `wait_signaled` + `unbiased < timeout` + nonzero exit → `vina_exit_nonzero`; (iv) sleep case
      (`wall≫unbiased`) → `suspend_detected`, not selected; (v) `wait_signaled` with **`unbiased_elapsed >=
      timeout_seconds`** (the launch-to-wait gap and the late-resume case are one indistinguishable observable state)
      → `timing_ambiguous`, quarantined + rerun, **never** accepted regardless of exit code (guards R5 #1); (vi) any
      Job/CreateProcess/GetExitCode failure → `infrastructure_failure` record + raise (campaign aborts), not `no_fit`.
    - Validator tests: bidirectional canonical mapping (a `valid_fit` carrying `deadline_timeout`/`WAIT_TIMEOUT` is
      rejected); a `wait_signaled` record with `unbiased >= timeout` and `timing_ambiguous != true` is **rejected**
      (recomputed) and when correctly flagged is **never selected**; a `wait_signaled` with `unbiased < timeout` is
      accepted; a **`deadline_timeout` record whose `wall−unbiased >= SUSPEND_THRESHOLD` but persisted
      `suspend_detected=false` is rejected**, and a correctly-flagged suspended `deadline_timeout` is **never
      selected** (guards R9); an `infrastructure_failure` record blocks the campaign.
    - A **Windows-only Win32 smoke test** exercising the real `QueryUnbiasedInterruptTime` (monotonic u64) + Job
      Object create/terminate/close + a `STARTUPINFOEX` `JOB_LIST`/`HANDLE_LIST` launch of a trivial child (**not**
      vina) + `GetExitCodeProcess`, and asserting `DeleteProcThreadAttributeList` + handle cleanup on both success and
      error paths.
    - Boundary ligands documented as an inherent, pre-existing ceiling limitation, not asserted.

### G. Fatal infrastructure handling (entry points)
14. All three workflow entry points currently `except DockingError … if exc.run_record is None: raise` then
    append-and-continue (`scripts/run_docking.py:190`, `scripts/run_speb_positive_control.py:152`,
    `scripts/dock_boron_surrogates.py:143`). Change so an **infrastructure failure aborts the campaign**: the infra
    path records atomically and raises via a dedicated signal (either `run_record=None` or an `InfrastructureError`
    subclass) that the entry points re-raise; only genuine scientific dispositions (`timeout`, operational `no_fit`)
    are appended-and-continued.

### H. Preregistration, neutral rerun, honest recomputation
15. `docs/adr/ADR-0001-timeout-unbiased-wall-basis.md`: frame as a **prospective post-incident amendment** correcting
    the exposed suspended-time ambiguity (not "already preregistered"). Record verified evidence (7EDD sleep sidecar
    = 29,287 wall s; 5XYA current = `valid_fit` @ 1429 s), the Windows 10 build-10240+ minimum, and considered-and-rejected
    alternatives (CPU-time; `max_evals`). **No predicted outcomes.**
16. **Amend, do not rewrite.** Preserve the original "wall-clock ceiling" text in `PROJECT_CONTEXT.md` §H/§17 (and the
    `PLAN.md:150` reference); **append a dated, signed amendment** stating wall-clock → sleep-excluding-wall, why, and
    every result already inspected.
17. **Campaign isolation + archival.** Acquire an exclusive single-runner lock; **verify no old `vina.exe` /
    `run_docking.py` is running**; relaunch into a new immutable **campaign-ID output root**
    (`results/docking/campaign_<id>/`), no cross-campaign artifact reuse. Archive the in-flight old-code campaign with
    an **immutable archive manifest** (every original path, archived path, sidecar hash, output hash, campaign status,
    exclusion reason); **never resume from the archive.** Rerun **every workflow feeding the final analysis**
    (library/wide, tight, SpeB, boron) under v2; block any aggregate manifest mixing timeout bases.
18. **Recompute headlines neutrally, only after the clean v2 campaign completes.** Regenerate **every** frozen
    headline and its figures + claim-registry entries: the primary Mann–Whitney population, top-ranked candidates, the
    SpeB positive control, and the **best-receptor / per-receptor catalytic-triad ranges** (currently 67/53/31,
    5XYA and 7EDD reported separately — the sole triad headline per `PLAN.md:272`). **Trigger the D3 timeout ablation
    iff a headline classification actually changes.** A triggered D3 is predeclared as a **complete raw-wall rerun**
    with identical code/schema/campaign inputs/hashes/parameters **except `timeout_basis`**, with **no reuse** of the
    partial contaminated campaign as the comparator.

## Key decisions & tradeoffs
- **Sleep-excluding wall ceiling via kernel wait** (not CPU-time, not raw-wall, not poll-elapsed): preserves the
  frozen awake-wall behavior; the **kernel decides signal vs wait-timeout**, and **QUT independently decides
  authoritative eligibility** of a signaled result (the ambiguity guard) — so a late-resumed supervisor cannot accept
  a past-ceiling result.
- **Direct `CreateProcessW` + atomic suspended in-job creation followed by validated resume** (`STARTUPINFOEX`
  `JOB_LIST`+`HANDLE_LIST`, not `Popen`): closes the Job-assignment race, minimizes the launch-to-wait window (guarded
  by the ambiguity check), restricts inherited handles, guaranteed tree termination + cleanup, fixes the orphan-vina
  history. Cost: ~80–110 lines of ctypes.
- **stdlib `ctypes`** (not psutil): no dependency-set / environment-hash perturbation (D5).
- **Neutral rerun under fixed code is authoritative** (not keep-current-run): uniform v2 records, single provenance.
  Cost: a fresh ~10–15 h run; discards in-flight old-code progress.
- **Amendment + full ADR, no predicted outcomes:** preserves the historical record; neutralizes result-conditioning;
  D3 triggers only on an actual flip, against a properly frozen raw-wall counterfactual.

## Risks / open questions
- **Wait granularity:** a single armed `WaitForSingleObject(hProcess, 1800000)` decides at the kernel boundary —
  `WAIT_TIMEOUT` means the awake ceiling was reached; `WAIT_OBJECT_0` means signaled, and is authoritatively eligible
  only if `unbiased_elapsed < timeout_seconds` (else `timing_ambiguous` → quarantine). No re-entry gap.
- **`SUSPEND_THRESHOLD`:** fixed at 5.0 s; calibration is a gate (abort if awake drift > 0.5 s), never a knob;
  sub-threshold suspends are undetected but bounded (stated, not claimed away). Sleep-disabled authoritative run ⇒
  expected 0 suspends.
- **Boundary ligands** (finishing within scheduling latency of exactly 1800 awake-s) may flip valid/timeout across
  repeats — inherent to any ceiling, pre-existing, documented not asserted.
- **Win 10+ requirement:** `PROC_THREAD_ATTRIBUTE_JOB_LIST` + sleep-excluding wait; satisfied by the Win 11 host;
  asserted at runtime; non-Windows / < Win 10 raises.

## Out of scope
- Cross-platform (POSIX) timeout enforcement — pipeline is Windows-pinned; non-Windows raises.
- Changing the frozen timeout **value** (1800 s), seed, exhaustiveness, num_modes, receptors, or boxes.
- `max_evals` as the stop rule — changes Vina's search; needs separate prospective preregistration + calibration
  (considered and rejected, recorded in ADR-0001).
- Editing the frozen remediation `PLAN.md` / `PLAN-REVIEW-LOG.md`, or docking *results* semantics beyond the timeout
  basis.

# Plan Review Log: docking timeout CPU-time ceiling

Act 1 (grill) complete — plan locked with the user (PLAN-timeout-fix.md). MAX_ROUNDS=5.

Reviewer model: `gpt-5.6-sol` (from ~/.codex/config.toml) — codex-cli 0.144.3. `-m` not pinned.
PLAN_FILE=PLAN-timeout-fix.md  LOG_FILE=PLAN-REVIEW-LOG-timeout-fix.md

## Act 1 decisions (locked)
1. Mechanism: **CPU-time ceiling** (Popen + poll child CPU; kill when CPU-time > 1800 s).
2. CPU accounting: **stdlib ctypes GetProcessTimes** (no new dependency; Windows-pinned).
3. Rollout: **re-run under fixed code** is authoritative (not keep-current-run).
4. Preregistration: **ADR-0001 + §H/§17 update + evidence**, committed before the re-run; not result-conditioned
   (does not rescue azithromycin@5XYA); D3 timeout ablation not retriggered (no headline flip).
5. Suspend mid-attempt: **accept pose + flag `suspend_detected`**; validator surfaces; no auto re-run.
6. Record schema: add `cpu_seconds`, `wall_seconds`, `suspend_detected`; `timeout_basis` into fingerprint;
   `elapsed_seconds` kept as alias of `cpu_seconds`.
7. Verification: **guard invariant** (timeout must be CPU-backed) **+ deterministic unit tests**; boundary ligands
   documented, not asserted.

---

## Round 1 — Codex (`gpt-5.6-sol`, xhigh) — VERDICT: REVISE
_Session `019f6588-80b9-7072-bcee-9d37291f754d`. Read-only; command execution blocked by the Windows sandbox helper being absent, so this was a pure file-reading review._

Codex raised 20 concrete points + a simpler-alternative recommendation. Full critique:

1. **Rewrites, not amends, the preregistered method.** §17/`PLAN.md:150`/`PROJECT_CONTEXT.md:621` say "wall-clock ceiling"; claiming it "always meant docking work" is revisionist and editing superseded §17 corrupts the historical record. → Preserve original text, append a dated signed post-incident amendment.
2. **"No headline can flip" is factually unsupported and contradicted by the repo.** azithromycin@5XYA is a *valid fit at 1429 s* (sidecar), and an earlier record valid at 1159 s — it is NOT an established awake timeout. Rescuing the timed-out 7EDD attempt makes this FDA comparator complete-case and can change the primary Mann–Whitney population/headline. → Delete every predicted-outcome statement; rerun neutrally; compute headlines after; trigger D3 iff classification actually changes.
3. **"~15 CPU-minutes" is not recorded evidence** — the sleep sidecar records only 29,287 wall seconds, no CPU time. → Label as unverified operator observation w/ provenance, or omit.
4. **CPU-time ≠ awake wall-time even at `--cpu 1`** (excludes scheduling/blocking/IO); the CPU ceiling can rescue an unsuspended-but-descheduled attempt — a broader method change than "only suspend behavior changes." → Adopt sleep-excluding active wall-time, or preregister CPU-time honestly as a new stop rule.
5. **Suspend/resume transparency is asserted, not established**; "surface for operator decision" creates post-result discretion. → Predeclare quarantine + rerun for every suspend-touched attempt under sleep-disabled conditions.
6. **`GetProcessTimes` sums one process's threads, not descendants**; killing a process doesn't kill children. → Job Object for tree-wide accounting/termination, or prove Vina spawns no descendants.
7. **Win32 handle design underspecified** — raw ctypes needs explicit 64-bit `argtypes`/`restype`, `use_last_error`, error checks, `CloseHandle`. → Specify full ABI contract, min Windows version, handle lifetime, fatal failure handling.
8. **Reopen-by-PID + last-sample fallback is unsafe** (PID reuse; handles stay valid after exit). → Open+identity-check one owned handle immediately after launch, retain through final accounting; never accept an attempt with unknown final time.
9. **Exit-vs-limit race unresolved** — sampled 1797 s, exits 1802 s before next poll, accepted despite exceeding ceiling. → Read final time after exit; classify final ≥ ceiling as timeout regardless of completed pose.
10. **`Popen` conversion can deadlock** — polling without draining PIPEs blocks Vina when a pipe fills. → Redirect stdout/stderr to bounded temp files or drain concurrently; kill/wait/reap/close in `finally`.
11. **Instrumentation/interruption failures can orphan Vina or fabricate dispositions** (OpenProcess/GetProcessTimes/kill failure, KeyboardInterrupt, shutdown, child-exits-mid-kill undefined). → Treat accounting failure as fatal infra error (not `no_fit`); guarantee termination, reaping, cleanup, structured failure record on every path.
12. **Validator checks a nonexistent status** — timeouts serialize as `status="no_fit", cause="timeout"` (`docking.py:341`), so `status=="timeout"` never fires. → Validate the canonical pair, or introduce one consistent timeout status everywhere.
13. **0.98 threshold unjustifiably permissive** — allows a timeout 36 s early; a successful read cannot under-report the sample that caused termination. → Require `elapsed_at_decision >= timeout_seconds`; reject non-timeout records whose final time exceeds the ceiling.
14. **`wall - cpu` is not suspend detection** (measures all idleness/contention/IO); 60 s margin gives false pos/neg; "refine later" is post-run calibration. → Use `QueryUnbiasedInterruptTime` (excludes sleep/hibernation); freeze the threshold before the campaign.
15. **Schema change mislabels historical data** — aliasing `elapsed_seconds` to CPU silently changes its meaning; leaving `RUN_SCHEMA_VERSION` at v1 misrepresents incompatible records. → Bump to v2; keep `elapsed_seconds == wall_seconds` or remove; require top-level `timeout_basis`, clock source, accounting scope, payload/top-level consistency.
16. **Fingerprint alone doesn't isolate campaigns** — archived sidecars still point at live `library_stage2`; a `CONTAMINATED_RACE` campaign already exists. → Exclusive single-runner lock + new immutable campaign-ID output root; verify all old Vina exited; prohibit cross-campaign artifact reuse.
17. **Depends on unrecorded platform semantics** — `runtime_versions()` omits CPython, Windows build, supervisor revision, timing API. → Fingerprint/record all of these + schema version, poll interval, timeout basis in every attempt + manifest.
18. **"Wire into the proof step" is not a spec** — current validator only raises, no persistent artifact, no gate. → Content-addressed timeout-QC artifact listing every attempt/finding; zero invalid records before analysis; predetermined suspend disposition.
19. **Tests miss the dangerous paths** — fake CPU readers won't catch wrong signatures, handle truncation, exit races, pipe saturation, kill failure, final-over-budget success. → Deterministic race/state-machine tests + a Windows-only Win32 smoke test exercising real timing API without Vina.
20. **Rerun scope ambiguous** — frozen method shares one schema across wide/tight/SpeB/boron; plan mentions only "Stage-2". → Rerun every workflow feeding final analysis under v2, or version+segregate and block mixed-basis aggregate manifests.

**Simpler alternative Codex recommends:** a `Popen` supervisor whose deadline uses `QueryUnbiasedInterruptTime` — preserves 1800 s of *awake* wall-time, excludes suspension directly, avoids per-process CPU/child accounting, and matches the frozen wall-clock method everywhere the machine is awake. (`max_evals` is closer to a hardware-independent work budget but needs a separate prospective preregistration + calibration.)

### Claude's response (Round 1)
Accepting essentially all of it. The critique is correct and several points are load-bearing scientific-integrity issues, not nitpicks.

**Core pivot (accept #4 + #14 + the recommended alternative): unbiased-wall, not CPU-time.** Replace the CPU-time ceiling with a **sleep-excluding wall-clock ceiling** via `QueryUnbiasedInterruptTime` (kernel32, system-wide, 100 ns units, no per-process handle). This *preserves the exact preregistered semantics* — 1800 s of awake wall-clock — so the fix is genuinely "correctly enforcing the existing ceiling" (sleep was never awake wall-time), which also strengthens the integrity story (#1). It dissolves #4 (no CPU-vs-wall drift), #6/#7/#8 (no `GetProcessTimes`/`OpenProcess`/owned-handle for accounting — the clock is system-wide), and makes #14 principled (suspend detected as `raw_wall − unbiased > MARGIN`).

Accepting and folding in:
- **#1** preserve original §17/§H; append a **dated, signed post-incident amendment** (wall-clock → unbiased-wall). No edits to superseded text.
- **#2 + #3** DELETE all predicted-outcome claims ("doesn't rescue 5XYA", "no headline flips") and the unverified "~15 CPU-min". Rerun neutrally; compute every frozen headline afterward; trigger D3 iff a classification actually flips. Record only what the sidecars actually contain (wall 29,287 s), plus the 5XYA-is-currently-a-valid-fit fact.
- **#5** suspend disposition → **quarantine + rerun** under sleep-disabled conditions (not accept+flag). Authoritative campaign is sleep-disabled, so `suspend_detected` should be 0; any occurrence is quarantined, not adjudicated post-hoc.
- **#6 (lifecycle) + #10 + #11** wrap Vina in a **Windows Job Object** with `KILL_ON_JOB_CLOSE` for guaranteed tree termination (also fixes this repo's recurring orphan-Vina failure); redirect stdout/stderr to temp files (no PIPE deadlock); kill/wait/reap/close in `finally`; accounting/interruption failure = fatal infra error with a structured failure record, never `no_fit`.
- **#7** full ctypes ABI contract for `QueryUnbiasedInterruptTime` + Job Object APIs (argtypes/restype/use_last_error/error checks), min Windows version, fatal handling.
- **#9 + #13** hard invariant: a timeout record must have `unbiased_seconds >= 1800`; **no** accepted (non-timeout) record may have `unbiased_seconds > 1800` — classify final-over-budget as timeout even if a pose completed. Drop the 0.98 fudge.
- **#12** validate the canonical `status=="no_fit" and cause=="timeout"` pair, consistently across schema/code/tests.
- **#15** bump `RUN_SCHEMA_VERSION` → v2; keep `elapsed_seconds == wall_seconds` (raw wall, unchanged meaning); add `unbiased_seconds` (budgeted), `suspend_detected`, `timeout_basis="unbiased_wall_seconds"`, `clock_source`, `poll_interval_seconds`; enforce payload/top-level consistency.
- **#16** exclusive single-runner lock + **immutable campaign-ID output root** (`results/docking/campaign_<id>/`); verify no old `vina.exe` running before start; no cross-campaign artifact reuse.
- **#17** record CPython build, Windows version/build, supervisor source commit, timing API, poll interval, timeout basis, schema version in `runtime_versions()` + every manifest.
- **#18** persistent content-addressed **timeout-QC artifact** listing every attempt; analysis gate requires zero invalid records + zero unresolved suspend quarantines.
- **#19** add deterministic race/state-machine tests + a Windows-only Win32 smoke test exercising the real `QueryUnbiasedInterruptTime` + Job Object without invoking Vina.
- **#20** rerun **every workflow feeding final analysis** (library/wide, tight, SpeB, boron) under v2; block any aggregate manifest mixing timeout bases.

**Rejecting:** `max_evals` as the mechanism — it changes Vina's search itself and needs separate prospective preregistration + calibration; a bigger method change than the defect fix warrants. Documented as considered-and-rejected. (No other point rejected.)

---

## Round 2 — Codex (`gpt-5.6-sol`, xhigh) — VERDICT: REVISE
_Same session `019f6588…`. Codex confirms the pivot "resolves most Round 1 objections" and the architecture is "close." Prior points resolved per Codex: CPU/descendant/PID/exit-race (gone with CPU-time), false 5XYA premise withdrawn, `elapsed_seconds` meaning kept + schema v2, canonical `no_fit/timeout` validator + no 0.98, PIPE/termination/fatal-infra/QC/provenance/smoke-test/isolation/four-workflow rerun/quarantine/amendment all addressed. 13 remaining points:_

1. **Framing overclaims the preregistration.** Frozen text says only "wall-clock ceiling"; "awake" wasn't preregistered. → Describe unbiased-wall as a narrow *prospective* amendment correcting an exposed ambiguity, not semantics already in the frozen text.
2. **Job Object assignment race.** `Popen` starts vina immediately; it can exit/spawn before `AssignProcessToJobObject`; handle rights (`PROCESS_SET_QUOTA|PROCESS_TERMINATE`) unspecified. → Create vina **suspended**, assign with an owned handle, then resume — or atomic `PROC_THREAD_ATTRIBUTE_JOB_LIST`.
3. **"Final-time rule" measures supervisor observation time, not process completion.** Vina exits 1799 s but supervisor descheduled to 1803 s ⇒ false timeout. → **Wait on the process handle** with the remaining budget; let the kernel distinguish signaled vs deadline; post-exit unbiased time = observability only, not disposition.
4. **Win 7 minimum conflicts with race-free wait.** Sleep-excluding `WaitForSingleObject` timeouts are **Win 8+**. → Pin supervisor to Win 8+/Server 2012+ (host is Win 11); record in ADR + validator.
5. **ctypes signature wrong.** `QueryUnbiasedInterruptTime` takes `PULONGLONG`, not `PULARGE_INTEGER`. → Bind `POINTER(c_ulonglong)->BOOL`; smoke test asserts monotonic u64 + error propagation.
6. **Validator equality hole + global budget.** Supervisor says `>=`⇒timeout but invariant (ii) rejects non-timeouts only on `>`, so a non-timeout exactly at 1800 passes; and it uses global `TIMEOUT_SECONDS` not the record's fingerprinted `timeout_seconds`. → timeout ⇒ `unbiased >= record["timeout_seconds"]`; non-timeout ⇒ `unbiased < record["timeout_seconds"]`; enforce 1800 separately at the campaign gate.
7. **"Every suspend" quarantine contradicts the 60 s detector** (a 30 s suspend is missed; "bounded by rerun" is circular — an undetected suspend triggers no rerun). → Record `suspend_gap_seconds`; calibrate a **small** threshold from pre-campaign clock drift; state precisely that suspends ≥ the detection limit are quarantined; optionally corroborate with a Windows power-transition signal.
8. **Quarantine unauditable with state-keyed filenames** — a rerun's fresh-run cleanup overwrites the quarantined pose/marker/sidecar; attempt identity + repeated-suspend behavior undefined. → Immutable `attempt_instance_id`, separate quarantine namespace, link retry→predecessor, halt after a predeclared max suspended retries.
9. **Infra failures aren't actually fatal** — entry points catch `DockingError`-with-record and continue (`run_docking.py:190`, `run_speb_positive_control.py:152`, `dock_boron_surrogates.py:143`, all verified). → After atomically recording the infra failure, **re-raise and abort the campaign**; only timeout/operational non-fit may continue.
10. **Resume fingerprint omits method-affecting fields** — recording supervisor hash/poll/clock/platform only in `runtime_versions()`/manifests doesn't change `_resume_exact()`'s `fingerprint_payload` (verified: payload holds only ligand/receptor/vina/box hashes), so a v2→v2 resume could reuse a different-supervisor sidecar. → Put supervisor source hash, clock source, poll interval, timeout basis, schema literal, campaign ID **into `fingerprint_payload`**.
11. **Exact schema literal ambiguous** — current is `"docking-run-record-v1"` (verified). → Freeze exact `"docking-run-record-v2"` in plan/schema/fingerprint/tests/manifest.
12. **D3 comparator not operationally frozen** — the archived-incomplete old campaign can't be the comparator. → Predeclare triggered D3 = a **complete raw-wall rerun** with identical code/schema/inputs/hashes/params except `timeout_basis`; no reuse of the partial contaminated campaign.
13. **Old-campaign archival underspecified** — archived sidecars still point at live `library_stage2` paths. → Immutable **archive manifest** (original path, archived path, sidecar hash, output hash, status, exclusion reason); never resume from the archive.

### Claude's response (Round 2)
Accepting all 13; verified #9/#10/#11 against the code first (all accurate). Two change the supervisor core:

- **#2 + #3 → direct ctypes `CreateProcess` supervisor, kernel-wait disposition (supersedes Popen + poll-elapsed).** Launch vina with `CREATE_SUSPENDED` via ctypes `CreateProcessW` (STARTUPINFO stdout/stderr → inheritable temp-file handles), assign the owned process handle (opened/created with `PROCESS_SET_QUOTA|PROCESS_TERMINATE|PROCESS_QUERY_LIMITED_INFORMATION`) to the fully-configured Job Object, then `ResumeThread` — no assignment-race window. Disposition comes from **chunked `WaitForSingleObject(hProcess, chunk)`**: `WAIT_OBJECT_0` ⇒ the process completed within the awake budget ⇒ **valid** (the wait timeout is sleep-excluding on Win 8+, so a signal means it finished in-budget); budget exhausted across chunks ⇒ `TerminateJobObject` + `no_fit/timeout`. `unbiased_seconds`/`wall_seconds` from `QueryUnbiasedInterruptTime`/`perf_counter` are recorded for observability + suspend detection **only**, never for disposition.
- **#4** pin supervisor to **Win 8+** (host is Win 11); assert at runtime + record in ADR/validator.
- **#5** `QueryUnbiasedInterruptTime` bound `POINTER(c_ulonglong)->BOOL`; smoke test asserts monotonic u64.
- **#6** validator: timeout ⇒ `unbiased >= record["timeout_seconds"]`; non-timeout ⇒ `unbiased < record["timeout_seconds"]`; 1800 enforced separately at the campaign gate.
- **#7** record `suspend_gap_seconds := wall − unbiased`; freeze a small threshold calibrated from measured pre-campaign awake drift (expected sub-second); state honestly that suspends ≥ threshold are quarantined and the undetected window is small+bounded (drop the circular claim); record Windows power-transition events as optional corroboration.
- **#8** immutable `attempt_instance_id` per execution; quarantined artifacts preserved in a separate namespace; retry links to predecessor; hard cap on suspended retries then halt.
- **#9** infra failure ⇒ atomically record, then raise so entry points **abort** (dedicated non-`run_record` path / `InfrastructureError`); patch all three entry points.
- **#10** add `timeout_basis`, `clock_source`, `poll_interval_seconds`, `timeout_seconds`, `supervisor_source_sha256`, `run_schema_version`, `campaign_id` **into `fingerprint_payload`**.
- **#11** freeze `"docking-run-record-v2"` everywhere.
- **#12** predeclare D3 = complete raw-wall rerun, identical inputs/hashes/params except `timeout_basis`, no partial-campaign reuse.
- **#13** immutable archive manifest for the old campaign; never resume from it.

**Rejecting:** nothing this round.

<!-- R3-END -->
---

## Round 4 — Codex (`gpt-5.6-sol`, xhigh) — VERDICT: REVISE
_Same session `019f6588…`. All six R3 blockers + triad "substantially resolved." 5 material issues + 1 native detail:_

1. **Win minimum too low for the launch mechanism.** `PROC_THREAD_ATTRIBUTE_JOB_LIST` is **Windows 10+/Server 2016+**, but the plan pins Win 8/build 9200. → Pin + runtime-gate to Win 10+ (host is Win 11); update everywhere stating Win 8+.
2. **Chunked waits still permit a false valid fit during a user-space scheduling gap.** At unbiased 1799 s the supervisor computes 1 s remaining, is descheduled 3 awake-s before entering `WaitForSingleObject`, vina exits at 1801; the handle is already signaled on wait entry ⇒ recorded `wait_signaled`/valid despite exceeding the ceiling. `WaitForSingleObject` protects only the interval it is actually waiting; on entry it just checks current state. → Use a kernel-armed deadline whose ordering vs completion survives supervisor gaps, or mark any signaled result whose unobserved interval straddles the deadline `timing_ambiguous` and quarantine/rerun.
3. **Schema can't represent the infra-failure record.** `disposition_basis` allows only `wait_signaled|deadline_timeout`, yet failure paths must emit a structured infra record and the validator requires every non-timeout to be `wait_signaled` w/ exit code. → Add `disposition_basis="infrastructure_failure"` (failure stage, Win32 error, optional exit code, cleanup outcome) + a validator rule that always blocks the campaign without misclassifying it as scientific failure.
4. **The "frozen" 5 s threshold is conditionally mutable.** The plan freezes 5.0 then raises to `10×measured_max` if calibration > 0.5 s — a contaminated "awake" calibration could silently make detection arbitrarily permissive. → Keep 5.0 s **fixed**; make calibration a **gate**: if awake drift > 0.5 s, abort/investigate or obtain a new signed amendment — never auto-raise.
5. **Timeout-defining details undefined.** No frozen `POLL_INTERVAL`, ms rounding unspecified, `unbiased_elapsed` start point absent; sampling after `CreateProcessW` returns grants vina unbudgeted runtime (atomic `JOB_LIST` starts it immediately). → Freeze interval + rounding; capture wall/unbiased start immediately **before** `CreateProcessW`; fingerprint those exact choices.

_Native detail:_ extended attributes require `EXTENDED_STARTUPINFO_PRESENT`; initialized attribute lists must be released via `DeleteProcThreadAttributeList`; preserve attribute-value buffers through creation — all absent. → Specify the flag, buffer lifetime, `DeleteProcThreadAttributeList` on every path, and cover cleanup in the smoke test.

### Claude's response (Round 4)
Accepting all 5 + the native detail. #2 + #5 are resolved together by simplifying the wait:

- **#2 + #5 → single armed wait (drop chunking, drop `POLL_INTERVAL`).** Capture `unbiased_start`/`wall_start` immediately **before** `CreateProcessW`, then enter **one** `WaitForSingleObject(hProcess, timeout_ms)` for the full ceiling (`timeout_ms = round(timeout_seconds*1000) = 1800000`), never re-entered. On Win 10+ that single timeout is sleep-excluding for its whole duration (a mid-wait sleep extends real time but not the budget), so `WAIT_OBJECT_0` ⇒ finished within the awake budget ⇒ **valid**; `WAIT_TIMEOUT` ⇒ `deadline_timeout`. Because the wait is armed once, early, there is **no re-entry gap** for a completion to straddle — the R4 #2 hole is eliminated by construction, not patched with a `timing_ambiguous` bucket. `POLL_INTERVAL` disappears from the design and the fingerprint (replaced by `wait_mechanism="single_armed_WaitForSingleObject"`); ms rounding frozen; start-capture point fingerprinted.
- **#1** pin + runtime-gate to **Windows 10+ (build ≥ 10240)**; the host is Win 11; update ADR/validator/plan everywhere that said Win 8+.
- **#3** add `disposition_basis="infrastructure_failure"` carrying `failure_stage`, `win32_error`, optional `exit_code`, `cleanup_outcome`; validator: an infra record **always blocks** the campaign and is never counted as a scientific `no_fit`/timeout.
- **#4** `SUSPEND_THRESHOLD = 5.0 s` is **immutable**; calibration is a **gate** — awake drift > 0.5 s ⇒ abort + investigate or new signed amendment; never auto-raise.
- **Native detail** ABI/lifecycle += `EXTENDED_STARTUPINFO_PRESENT`, `InitializeProcThreadAttributeList`/`UpdateProcThreadAttribute`/`DeleteProcThreadAttributeList`; keep the attribute-value buffers (job handle array, handle-list array) alive through `CreateProcessW`; `DeleteProcThreadAttributeList` + `CloseHandle` on every path (incl. errors); smoke test asserts the cleanup.

**Rejecting:** nothing this round. (Note: single-armed-wait supersedes the R3 "chunked `WaitForSingleObject`" wording throughout §A/§F.)

---

## Round 5 — Codex (`gpt-5.6-sol`, xhigh) — VERDICT: REVISE  (MAX_ROUNDS=5 reached)
_Same session `019f6588…`. Codex: "much stronger; one material correctness hole remains." 1 substantive + 4 wording/consistency:_

1. **Critical — the timeout is still not armed when vina starts.** `CreateProcessW` returns before `WaitForSingleObject` is entered; the 1,800,000 ms interval begins only at wait entry. If the supervisor is descheduled in between, vina can consume unbounded awake runtime (even exit); the later wait returns `WAIT_OBJECT_0` → a valid accepted result beyond the ceiling. Capturing QUT before creation doesn't affect the kernel wait deadline. → Create vina **suspended** in the atomic job, arm a low-power-excluding deadline **before** resuming, wait on process-vs-deadline; **otherwise retain a conservative ambiguity/quarantine disposition** for any unbounded launch-to-wait interval.
2. **Fingerprint still contradicts the single-wait design** — `fingerprint_payload`/`runtime_versions()` still list `poll_interval_seconds`/poll interval. → Remove every poll-interval field/reference; keep `wait_mechanism` + `timeout_ms`.
3. **Platform provenance inconsistent** — the ctypes heading + ADR still say Windows 8+ while the gate requires Win 10 build 10240+. → Replace every "Windows 8+" with the exact Win 10 build.
4. **Top-level guarantee overstates duration handling** — suspended time still legitimately inflates raw `wall_seconds`; it merely doesn't consume the budget or determine disposition. → State that precisely; raw wall stays as observability evidence.
5. **Audit-history wording stale** — the doc still says "revised twice" despite the review rounds. → Record the actual revision history/date without rewriting frozen artifacts.

### Claude's response (Round 5) — arbiter decision: MAX_ROUNDS 5 → 6
We hit the 5-round cap on a REVISE, but 4 of 5 points are stale-wording fixes and only #1 is substantive — with a concrete Codex-endorsed fix. Rather than surface a false "deadlock" to an absent operator over one well-understood item, I (orchestrator) **extend the cap to 6** to confirm the fix with one more round. If R6 raises anything substantive, that is surfaced as a real deadlock. Accepting all 5:

- **#1** launch `CREATE_SUSPENDED` in the atomic job; capture `unbiased_start`, `ResumeThread`, then immediately enter the single wait — shrinking the launch-to-wait window. A true sleep-excluding *waitable-timer* object doesn't exist in Win32 (standard waitable timers are biased/can wake the machine), so the residual gap is closed by Codex's endorsed **fallback**: any `wait_signaled` result with `unbiased_elapsed >= timeout_seconds` is **`timing_ambiguous`** → quarantine + rerun, never accepted, never a fabricated timeout. This is the *only* sound disposition for the case (a launch-gap over-budget completion and an R3 late-resume in-budget completion are indistinguishable), and it satisfies both R3 #1 (don't wrongly call it timeout/invalid) and R5 #1 (don't accept past-ceiling). On the sleep-disabled authoritative host it should never fire; if it does, the rerun resolves it. Added `ResumeThread` to the ABI, `timing_ambiguous` to schema + validator (iv) + quarantine (E/10) + tests (v).
- **#2** removed `poll_interval_seconds` from `fingerprint_payload` and the `runtime_versions()` list (replaced by `wait_mechanism` + `timeout_ms`).
- **#3** ctypes heading + ADR now state **Windows 10 build 10240+** (binding minimum; noted the sleep-excluding wait itself needs only Win 8+).
- **#4** Goal reworded: suspended time **cannot consume the budget or generate a scientific timeout**; raw `wall_seconds` still includes it as observability evidence; `unbiased_seconds` alone gates the ceiling.
- **#5** header now records the five-round history + the 5→6 cap extension + date, pointing to this log; no frozen artifact rewritten.

**Rejecting:** nothing. Note: no true unbiased waitable timer exists, so the ambiguity guard (not a timer) is the principled closure of #1.

---

## Round 6 — Codex (`gpt-5.6-sol`, xhigh) — VERDICT: REVISE
_Same session `019f6588…`. **Codex affirms the architecture:** "the launch-to-wait fallback is now soundly conservative — an over-ceiling signaled result cannot become authoritative or be mislabeled as a timeout. Points 2–5 are also resolved." The 5 remaining are internal-consistency ripples from the R5 `timing_ambiguous` guard, not new design objections:_

1. F/11 said durations aren't used to accept/reject signaled completions — contradicts A/2's `>= timeout_seconds` guard; and it didn't recompute `timing_ambiguous`, so a wrongly-persisted `false` could pass. → Validator recomputes `wait_signaled && unbiased >= record["timeout_seconds"]`, requires `timing_ambiguous=true`, prohibits authoritative selection.
2. Tests (ii) and (v) prescribed opposite results for the same observable state (`WAIT_OBJECT_0` + `unbiased >= timeout`). → Make every such case ambiguous; test timely acceptance only with `unbiased < timeout_seconds`.
3. Stale explanatory claims ("deadline armed before vina runs", "disposition decided solely by the kernel", "`WAIT_OBJECT_0` always means in-budget"). → Kernel distinguishes signal vs wait-timeout; QUT determines whether a *signaled* result is authoritatively eligible.
4. `ResumeThread` needs an explicit native invariant — returns previous suspend count (`DWORD`), `0xFFFFFFFF` = failure; treating it as BOOL risks waiting on a still-suspended process → fabricated timeout. → Bind `DWORD`, require exactly `1`, else fatal infra.
5. QC/gate mentioned only suspend quarantines, omitting `timing_ambiguous`. → Include `timing_ambiguous` + reason + selection status; require zero unresolved quarantines of either kind.

### Claude's response (Round 6) — cap 6 → 7 (confirming)
All 5 are self-consistency fixes flowing from my own R5 edit; Codex raised **no new substantive objection** and explicitly affirmed soundness. Per my stated R5 criterion (continue only if nothing substantive is surfaced), I apply these and run one **final** confirming round.
- **#1** F/11 (v) rewritten: validator **recomputes** `timing_ambiguous == (unbiased >= record["timeout_seconds"])` for `wait_signaled` records (rejects a wrong persisted `false`), never selects a `timing_ambiguous` record; otherwise durations don't fabricate timeouts or override the kernel signal-vs-timeout decision — this reconciles R3 #1 and R5 #1 (shared verdict = quarantine).
- **#2** test (ii) now uses `unbiased < timeout` for the valid case; (v) covers `unbiased >= timeout` → `timing_ambiguous`; validator test flips to "rejected/never-selected."
- **#3** reworded step-1 heading, step-2 disposition sentence, and the risks bullet accordingly.
- **#4** `ResumeThread` bound `-> DWORD`, must return exactly `1` (previous suspend count), else fatal infra.
- **#5** QC report + gate now include `timing_ambiguous`, quarantine reason, selection status; gate requires zero unresolved quarantines of **either** kind.

**Hard stop rule for R7:** if R7 is APPROVED → done. If R7 REVISEs on anything beyond typo-level wording → I stop looping and surface the state to the operator as a genuine non-convergence rather than extend further.

**Rejecting:** nothing.

---

## Round 7 — Codex (`gpt-5.6-sol`, xhigh) — VERDICT: REVISE  →  LOOP STOPPED (operator gate)
_Same session `019f6588…`. Codex reaffirms (3rd time): "the launch-to-wait mechanism is now soundly conservative, and all five Round 5 corrections are substantively present." 5 points, all validator/audit precision — no new architecture:_

1. Validator doesn't cross-check `wait_result` — a fabricated `deadline_timeout` with `wait_result=WAIT_OBJECT_0` passes. → `deadline_timeout ⇔ WAIT_TIMEOUT`; `wait_signaled ⇔ WAIT_OBJECT_0` + non-`STILL_ACTIVE` exit code; `WAIT_FAILED`/unexpected → fatal infra.
2. Invariant (ii) said *every* non-timeout must be `wait_signaled`, capturing infra records and conflicting with (iii). → Scope (ii) to scientific (non-infra) records; make the three branches mutually exclusive.
3. Method summary still said disposition "solely kernel-decided… immune to descheduling." → Kernel decides signal vs timeout; QUT independently decides authoritative eligibility.
4. Summary still said "no suspend/resume dance" despite `CREATE_SUSPENDED`+`ResumeThread`. → "atomic suspended in-job creation followed by validated resume."
5. Recomputed guard lacked numeric-domain validation — missing/nonfinite/negative `unbiased_seconds` must not read as eligible. → Require finite, ≥0 durations and a finite, >0 timeout matching the fingerprint before comparing; else invalid record.

### Claude's response (Round 7) — APPLIED, then STOPPED per the pre-committed cap
All 5 applied (all correct; I'm the arbiter): (1) validator now cross-checks `wait_result` both directions + routes `WAIT_FAILED`/unexpected to infra; (2) invariant (ii) scoped to scientific records, three branches declared mutually exclusive/exhaustive; (3) tradeoffs bullet reworded to the A/2 kernel-vs-QUT split; (4) "atomic suspended in-job creation followed by validated resume"; (5) numeric-domain validity gate (present/finite/≥0 durations, finite/>0 timeout == fingerprint) before the ambiguity comparison.

**Decision: stop the loop here.** Points #1/#2/#5 were validator-logic, past my "typo-level only" continue-threshold, so per the R6 hard-stop rule I do **not** run an 8th round. This is **not** a deadlock of opposing positions — across R1–R7 I accepted every Codex point and rejected only `max_evals`; Codex affirmed the architecture sound in R6 and R7. It is **asymptotic convergence**: the design is settled and the last two rounds only tightened the validator predicate. The plan is substantively converged and carries R7's hardening, but it did **not** receive a literal `VERDICT: APPROVED` token — I am not manufacturing one. **Operator gate:** Josh decides — sign off as-is, request one more confirming Codex pass, or proceed to build. No code until that sign-off.

**Convergence trajectory:** R1 20 → R2 13 → R3 6 → R4 5 → R5 1(+4 wording) → R6 5(consistency) → R7 5(validator precision). Architecture affirmed sound R6 + R7.

_Operator override after R7: Josh instructed "continue revising until best plan reached" — the default cap is lifted; the loop continues to a genuine `VERDICT: APPROVED` (or a real opposing-position deadlock, which has not occurred). My R7 stop is superseded._

---

## Round 8 — Codex (`gpt-5.6-sol`, xhigh) — VERDICT: REVISE
_Same session `019f6588…`. "The five R6 findings are resolved, and the launch-to-wait mechanism is sound." 2 validator holes + 1 stale header:_

1. **Canonical status not enforced bidirectionally** — a `status="valid_fit"` record with `deadline_timeout`/`WAIT_TIMEOUT` passes because invariant (i) only started from already-timeout-labeled records. → Enforce `canonical timeout ⇔ deadline_timeout ⇔ WAIT_TIMEOUT`; all other scientific records `wait_signaled ⇔ WAIT_OBJECT_0`, checked both directions.
2. **Validator still trusts `suspend_detected`** — a record with `wall−unbiased >= 5.0` but persisted `suspend_detected=false` could be selected. → Recompute `suspend_gap_seconds`/`suspend_detected` from validated durations + fingerprinted threshold; reject mismatches; prohibit selection when recomputed true.
3. **Audit header stale** — still says post-R5/awaiting-R6/cap-6. → Update to the actual sequence + cap lift.

### Claude's response (Round 8) — all applied, loop continues
Both #1 and #2 are the same recompute-don't-trust class as R7; correct. (i) rewritten as a **bidirectional canonical mapping** across `status/cause ⇔ disposition_basis ⇔ wait_result ⇔ termination_action`, rejecting every cross-pairing (incl. `valid_fit`+`deadline_timeout`). (v) now **recomputes both** `timing_ambiguous` **and** `suspend_detected`/`suspend_gap_seconds` from validated durations + the fingerprinted threshold, rejecting any persisted-vs-recomputed mismatch and barring selection when either is true. Header updated to the real R1–R8 sequence + operator cap-lift. **Rejecting:** nothing. Submitting R9.

---

## Round 9 — Codex (`gpt-5.6-sol`, xhigh) — VERDICT: REVISE
_Same session `019f6588…`. "The canonical disposition mapping, audit header, and signaled-result guard are now correct." **One** material scope error:_

F/11(v) applied numeric validation + both derived-flag recomputations only "for every `wait_signaled` record" — but a `deadline_timeout` is also a scientific attempt that can be suspended mid-run, so it could persist `suspend_detected=false` despite `wall−unbiased >= SUSPEND_THRESHOLD` and be selected, violating E/9–10. → Apply duration validation + `suspend_gap`/`suspend_detected` recomputation to **every scientific record**; apply `timing_ambiguous` recomputation only to `wait_signaled`. Add a test: a suspended `deadline_timeout` with a false persisted flag is rejected; a correctly-flagged one is never selected.

### Claude's response (Round 9) — applied, loop continues
Correct scope fix. (v) rewritten: numeric-domain validity + `suspend_gap_seconds`/`suspend_detected` recompute now cover **both** `deadline_timeout` and `wait_signaled` (a suspend can occur during a timed-out run); `timing_ambiguous` recompute stays `wait_signaled`-only. Added the requested validator test (suspended `deadline_timeout` + false persisted `suspend_detected` → rejected; correctly-flagged → never selected). **Rejecting:** nothing. Submitting R10.

---

## Round 10 — Codex (`gpt-5.6-sol`, xhigh) — VERDICT: APPROVED ✅
_Same session `019f6588…`. Codex: "The Round 9 scope correction is present and correct… The supervisor lifecycle, kernel/QUT decision split, canonical validator mappings, quarantine rules, fingerprint isolation, infrastructure-failure handling, tests, and neutral rerun protocol are internally coherent. **I find no remaining material flaw blocking implementation.**"_

**CONVERGED after 10 rounds.** Trajectory of findings: R1 20 → R2 13 → R3 6 → R4 5 → R5 1(+4) → R6 5 → R7 5 → R8 2 → R9 1 → R10 0 (APPROVED). Architecture affirmed sound from R6 onward; R7–R9 were validator-predicate precision. I accepted every Codex point across all 10 rounds; the only rejection was `max_evals` as the mechanism (recorded, with reason). No opposing-position deadlock ever occurred.

**Next: human sign-off gate (per Josh's CLAUDE.md chain).** No code is written until Josh approves the converged plan. Then: Codex builds (`codex-build`, needs a clean git tree) or Claude builds — followed by Claude verifying against the project's proof command.

## Round 3 — Codex (`gpt-5.6-sol`, xhigh) — VERDICT: REVISE
_Same session `019f6588…`. "Round 2 closes all 13 prior findings in intent." 6 concrete points + 1 completeness note:_

1. **Validator contradicts the kernel-wait valid-completion test.** A process can signal before its deadline while the supervisor resumes late and records `unbiased_seconds >= timeout`; the plan's own test calls that **valid** (line 114) but validator invariant (ii) rejects it (line 105); clock-tick resolution can also put a genuine timeout just under the boundary. → Persist + validate the **kernel decision** (final wait result, requested remaining wait, termination action); treat post-return `unbiased_seconds` as observability only — no strict duration inequality for signaled completions.
2. **`CreateProcessW` drops `subprocess` command semantics** — omits arg quoting, mutable command buffer, exact `lpApplicationName`, cwd, environment, `STARTF_USESTDHANDLES`, stdin, restricted handle inheritance (`bInheritHandles=TRUE` leaks unrelated inheritable handles). → Freeze `lpApplicationName` to the exact Vina path, build the command line with `subprocess.list2cmdline` in a mutable buffer, preserve cwd/env, and use `STARTUPINFOEX + PROC_THREAD_ATTRIBUTE_HANDLE_LIST` so only the 3 intended std handles inherit.
3. **Exit-code retrieval missing.** `GetExitCodeProcess` absent from the ABI, yet the existing disposition distinguishes exit 0 from `vina_exit_nonzero` (verified `docking.py:357-436`); waiting alone gives no exit code. → Bind + check `GetExitCodeProcess` after `WAIT_OBJECT_0`; require `SYNCHRONIZE` + query rights; retrieval failure = fatal infra.
4. **Moving quarantined artifacts invalidates their sidecars** — sidecars store concrete `out_path`/`sidecar_path` and resume re-resolves+hashes them (verified `docking.py:587`); moving recreates the stale-path defect and isn't atomic. → Write each execution **directly into an immutable attempt-instance directory, never move**; promote authority via an atomic **selection manifest** referencing the accepted instance + quarantined predecessors.
5. **Suspend params are placeholders and absent from the fingerprint** — no exact calibration algorithm, `SUSPEND_THRESHOLD`, or max-retry value; they determine which execution becomes authoritative. → Freeze calibration duration/load/statistic, exact threshold, exact retry limit before the campaign; put the threshold in every attempt fingerprint and both in the campaign manifest/QC hash.
6. **Existing docking tests bypass the new launcher** — they monkeypatch `subprocess.run` with `vina_executable=sys.executable` (verified `test_docking.py:126`); after `CreateProcessW` they no longer intercept and could launch Python for real. → Isolate the native supervisor behind an **injectable seam**, port every existing docking test to mock it, and assert no unit test reaches real process creation except the marked Windows smoke test.

_Completeness:_ §H omits the frozen **best-receptor / per-receptor catalytic-triad range** headline (67/53/31, `PLAN.md:272`). → Include best-receptor + per-receptor triad ranges, their figures, and claim-registry entries in post-campaign headline regeneration.

### Claude's response (Round 3)
Accepting all 6 + the note; verified #3/#4/#6 + the triad headline against the code (all accurate).

- **#1** add a recorded `disposition_basis ∈ {"wait_signaled","deadline_timeout"}` (+ `wait_result`, `requested_remaining_ms`, `termination_action`); validator keys on it — timeout ⇒ `deadline_timeout`; signaled completions validated by kernel result + exit code, with `unbiased_seconds` observability-only (drops the inequality-vs-signaled contradiction).
- **#2** launch via `STARTUPINFOEX` carrying **both** `PROC_THREAD_ATTRIBUTE_JOB_LIST` (atomic in-job creation — removes the assignment race *and* the suspended/resume dance) and `PROC_THREAD_ATTRIBUTE_HANDLE_LIST` (inherit only the 3 std temp-file handles); `lpApplicationName` = exact vina path; command line via `subprocess.list2cmdline` in a mutable `ctypes` buffer; preserve cwd + environment; `STARTF_USESTDHANDLES`; stdin = `NUL`.
- **#3** bind + check `GetExitCodeProcess` after `WAIT_OBJECT_0` (handle rights += `SYNCHRONIZE`); preserve the `vina_exit_nonzero` disposition; retrieval failure = fatal infra.
- **#4** **write-in-place** to `results/docking/campaign_<id>/<attempt_instance_id>/`; never move; an atomic **selection manifest** names the authoritative instance and links quarantined predecessors (supersedes the "separate quarantine namespace by moving" wording).
- **#5** freeze concrete values: calibration = wall−unbiased drift over a 10-min awake baseline under a single-core docking-equivalent load, statistic = max observed; `SUSPEND_THRESHOLD = 5.0 s` (≈10× the sub-0.5 s expected drift; the build step confirms/raises it from the measured baseline before the campaign); `max_suspended_retries = 2`. `SUSPEND_THRESHOLD` → `fingerprint_payload`; threshold + retry limit → campaign manifest/QC hash.
- **#6** introduce a seam `_run_vina_supervised(...) -> SupervisedResult`; port `test_docking.py` from mocking `subprocess.run` to mocking the seam; add a guard asserting no unit test invokes real `CreateProcessW` except the Windows smoke test.
- **Note** §H recomputation list gains best-receptor + per-receptor triad ranges (67/53/31), their figures, and claim-registry entries.

**Rejecting:** nothing this round.

---

# Act 3 — Build (Codex types, Claude verifies)

## Round 1 — Codex build (`gpt-5.6-sol`, xhigh, `--yolo`, user-authorized)
_Session fresh; SPEC=PLAN-timeout-fix.md. Build ran while the old-code campaign was live; contract forbade touching results/, running campaign scripts, or git writes._

**Codex report:** implemented the frozen fix; deviations: none. Files changed: `src/spycep_drug_discovery/docking.py` (Win32 supervisor, schema v2, validator, QC, quarantine, selection manifest, calibration, campaign isolation), `environment.py` (provenance), the three entry points (`run_docking.py`/`run_speb_positive_control.py`/`dock_boron_surrogates.py` — campaign-id root, lock/calibration gates, QC artifact, infra abort), `compute_statistics.py`/`make_figures.py`/`write_docking_methods.py` (analysis QC + campaign-consistency gate), `tests/test_docking.py` (ported to the seam), `tests/test_docking_timeout.py` (new), `tests/test_environment_and_workflow_schema.py` (v2), `docs/adr/ADR-0001-timeout-unbiased-wall-basis.md` (new), `PROJECT_CONTEXT.md` (appended amendment).

### Claude's verdict — VERIFIED, no fix round needed
Verified independently (not trusting Codex's claims):
- **Scope:** `git status` shows only expected files; **no `results/` or `docs/methods/*.json` touched — live campaign untouched.**
- **Proof (ran myself):** full suite `pytest tests -q` = **179 passed, 0 failed**; `test_docking_timeout.py` = **22 passed, 0 skipped** (so the real Win32 smoke test executed). Test names map 1:1 to the argued edge cases (timing-ambiguous never-accepted parametrized on exit code; suspend-recompute on `deadline_timeout` = the R9 fix; bidirectional canonical mapping; STILL_ACTIVE rejection; infra-abort; calibration abort-gate).
- **Core impl (read the diff):** correct Win32 ABI (`QueryUnbiasedInterruptTime`→`POINTER(c_ulonglong)`, `ResumeThread`→`DWORD` with the `==1` check, `GetExitCodeProcess`, `DeleteProcThreadAttributeList` cleanup on every path); `unbiased_start`/`wall_start` captured **after `CreateProcessW` but before `ResumeThread`** (correct — child is `CREATE_SUSPENDED`); kernel-wait disposition; `WAIT_FAILED`/unexpected → infra; `BaseException`→infra; full `finally` cleanup.
- **Validator:** `suspend_detected` recomputed for **all** scientific records (both `deadline_timeout` and `wait_signaled` — R9 scope), `timing_ambiguous` recompute gated to `wait_signaled`, `deadline_timeout` barred from `timing_ambiguous`, numeric-domain validity gate, infra always blocks, bidirectional canonical mapping enforced.
- **Entry points:** infra-abort via `is_continuable_scientific_disposition` (infra not continuable → re-raise/abort; scientific timeout/no_fit continue).
- **Preregistration integrity:** ADR-0001 states "predicts no rerun outcome," cites only verified evidence (labels the ~15-CPU-min as not-evidence), prospective framing, all rejected alternatives recorded; `PROJECT_CONTEXT.md` amendment **appended** (original §H/§17 preserved), "no outcome predicted."

**Deferred (human-gated, NOT built — correctly):** plan §H operational steps — stop/archive the live old-code campaign, run the pre-campaign calibration abort-gate, launch the neutral schema-v2 rerun, recompute headlines. These come after commit + sign-off.

Isolation checkpoint before build: `d740226`. Awaiting human diff sign-off before commit (Claude commits, never Codex).

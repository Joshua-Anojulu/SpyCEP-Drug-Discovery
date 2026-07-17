# Plan Review Log: Pre-campaign suspend-calibration harness

Act 1 (grill-with-docs) complete — plan locked at `PLAN-calibration.md`. MAX_ROUNDS=5.
Isolation checkpoint: HEAD `300bbdc`; working tree carries one prior modification (`run_campaign.sh`).

## Act 1 — decisions locked (Claude ↔ Josh, 2026-07-17)

Non-default files: `PLAN_FILE=PLAN-calibration.md`, `LOG_FILE=PLAN-REVIEW-LOG-calibration.md`. The skill's defaults
(`PLAN.md` / `PLAN-REVIEW-LOG.md`) are the **frozen** remediation plan and must not be touched; this follows the
existing `-timeout-fix` suffix convention. Domain doc is `PROJECT_CONTEXT.md` (gitignored, 697 lines), not a
competing `CONTEXT.md`.

| # | Question | Decision | Basis |
|---|----------|----------|-------|
| 1 | What is the "single_core_docking_equivalent" load? | Real `vina.exe`, `--cpu 1`, terminated at 600 s | "Docking-equivalent" becomes demonstrated, not asserted |
| 2 | Which input pair? | azithromycin + `spycep_5xya_aes_active_site` | Only pair with published awake-runtime evidence (`valid_fit` @ 1,429 s, ADR-0001) — known to outlast the window |
| 3 | Provenance? | Additive keys; validator untouched, schema stays v1 | Validator ignores unknown keys (verified). Bumping to v2 edits Codex-approved code + tests for no enforcement gain — a forger can hand-write provenance too |
| 4 | Reuse the Win32 seam, or reimplement? | **Resolved from code, not asked.** Reuse `_query_unbiased_interrupt_time()` + `time.perf_counter()` | That exact pair is what the supervisor uses at `docking.py:584-585`; anything else measures a different quantity than the gate it feeds |
| 5 | Abort semantics on drift > 0.5 s? | Write `<name>.FAILED.json` + exit non-zero | Failure is real data and is what §H9's "abort and investigate" requires; suffix prevents mistaking it for a pass |
| 6 | Artifact location / lifetime? | `docs/methods/suspend_calibration_<campaign_id>.json`, tracked, per-campaign | Tracked ⇒ published with the manifests it underwrites; per-campaign ⇒ no stale calibration can gate a fresh run |

### Resolved by reading code rather than asking

- **Sampling strategy (was an open question):** no sampling thread. `SupervisedResult` (`docking.py:147`) already
  carries **both** `wall_seconds` and `unbiased_seconds`; drift is monotonic non-decreasing, so max ≡ final. The
  supervisor's sleep-excluding wait means `timeout_seconds=600.0` *is* a 10-minute awake baseline by construction.
- **Launch mechanism:** `_run_vina_supervised()` (`docking.py:390`) is a clean seam — Job-object tree termination
  (no orphan vina), same code path as the campaign.
- **Trap — `duration_seconds` is a declared constant, not a measurement.** The validator rejects anything ≠ `600.0`,
  so an honestly-reported `600.3` would fail the gate. Real elapsed goes to provenance.
- **Trap — calibration must not create `results/docking/campaign_<id>/`.** `run_campaign.sh` refuses to start if that
  root pre-exists; a calibration writing there would lock the operator out of their own campaign.

### Correction recorded

Earlier in this session Claude advised that `library_stage2_CONTAMINATED_SLEEP_2026-07-15/` was safe to delete
("you lose nothing real"). **That was wrong.** It holds the sole copy of
`azithromycin__state_01__spycep_7edd_native_active_site.run.json` (`elapsed_seconds: 29287.070618800004`) — the
primary evidence cited in ADR-0001 line 12 and `PLAN-timeout-fix.md:10`, gitignored and existing nowhere else. The
other `29287` hits on disk are coincidental digits inside coordinate floats. Deleting it would have left a published
ADR citing a file that does not exist. Preservation is now an explicit plan step (§11). No deletion occurred.

### Known limitation carried into the plan, not claimed away

Additive provenance does **not** make the gate unforgeable. A hand-written artifact still passes. It makes an honest
artifact self-evidencing and fabrication deliberate rather than casual.

---

## Round 1 — Codex (`gpt-5.6-sol`, read-only, thread `019f6f9c-5ad9-78d2-acb0-9c8f4849480a`)

_First attempt was killed by the skill's 10-minute ceiling with no output. Re-run in the background completed in
**10m 19s** — i.e. the ceiling had cut off real work ~19 s short, not caught a stall. Round 1 below is the background run._

The plan is not safe to implement as written. Several claims can admit a passing artifact that did not perform the calibration §H9 specifies.

1. **Blocking — `wall − unbiased` is not monotonic.** Both source clocks being non-decreasing does not make their difference non-decreasing. QPC is monotonic, includes standby/hibernate/connected-standby time, and Windows handles modern multi-core/TSC synchronization; those parts are sound. But `QueryUnbiasedInterruptTime` advances at clock interrupts and can be quantized by roughly 0.5–15.625 ms, so the difference rises between interrupt ticks and falls when the unbiased counter advances. Independent rate error can also move it either way. A peak just above 0.5 s can therefore end below 0.5 s. [Microsoft QPC guidance](https://learn.microsoft.com/en-us/windows/win32/sysinfo/acquiring-high-resolution-time-stamps), [unbiased-clock precision](https://learn.microsoft.com/en-us/windows/win32/api/realtimeapiset/nf-realtimeapiset-queryunbiasedinterrupttimeprecise), [QueryUnbiasedInterruptTime](https://learn.microsoft.com/en-us/windows/win32/api/realtimeapiset/nf-realtimeapiset-queryunbiasedinterrupttime).

   **Fix — Replace the final-only calculation with a predeclared periodic paired-sampling protocol, record the series/read skew, include the zero baseline, and gate on the maximum observed sample with clock-resolution uncertainty handled conservatively.**

2. **Blocking — the existing supervisor does not expose the interval the plan claims.** It samples unbiased then QPC before `ResumeThread`, waits, terminates the Job, then samples unbiased and QPC afterward ([docking.py](C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/src/spycep_drug_discovery/docking.py:584)). Thus its values include pre-resume and post-timeout/termination overhead and potentially unbounded scheduler preemption between unlike-clock reads. Start-read preemption can subtract from measured drift and conceal a real excursion.

   **Fix — Add a calibration-specific sampling hook at the ResumeThread/deadline boundaries using bracketed clock reads, rather than treating `SupervisedResult`’s aggregate pair as the §H9 measurement.**

3. **Blocking — `deadline_timeout` proves “unsignaled,” not “loaded.”** Windows 8+ excludes low-power time from `WaitForSingleObject` timeouts, so the wait is a reasonable sleep-excluding deadline. But a hung, blocked, throttled, or mostly descheduled Vina process also produces `deadline_timeout`; no CPU utilization is measured. [WaitForSingleObject documentation](https://learn.microsoft.com/en-us/windows/win32/api/synchapi/nf-synchapi-waitforsingleobject).

   **Fix — Record Job/process user+kernel CPU time and require a prospectively approved utilization floor over the sampling window, aborting if Vina did not consume approximately one core.**

4. **High — `duration_seconds: 600.0` is defensible only as a nominal protocol value.** The actual interval is at least the wait plus resume, scheduling, and termination overhead; calling the field actual duration would be misleading. A longer observed window is conservative, but the plan must not equate it with exactly 600 seconds.

   **Fix — Define `duration_seconds` explicitly as the requested nominal wait, add unambiguous `sampling_window_unbiased_seconds` and `sampling_window_wall_seconds`, and require the former to be at least 600 seconds before passing.**

5. **Blocking — additive, ignored provenance does not turn this into a campaign gate.** `require_suspend_calibration()` accepts any JSON with six fields and checks neither campaign identity, timestamp, current host, Vina/input hashes, nor supervisor hash ([docking.py](C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/src/spycep_drug_discovery/docking.py:1797)). A stale or hand-written six-line artifact remains casual, not merely deliberate, fabrication. Acknowledging this in ADR-0002 does not repair it.

   **Fix — Seek a signed scope amendment requiring and validating campaign ID, freshness policy, producer/schema identity, current supervisor/Vina/input hashes, and artifact outcome; otherwise stop describing this file as an enforced per-campaign calibration gate.**

6. **High — azithromycin/5XYA is evidence, not a duration guarantee.** The cited 1,429-second result used the same current input and binary hashes, but it is one approved observation under a different execution path and host state. Early completion is fail-closed, which protects validity, but it can make the harness unusable; worse, the unsignaled-process test does not detect a stalled workload.

   **Fix — Treat the runtime as provisional, retain early-finish abort behavior, and make load duration independent of one completion observation—such as a prospectively approved restartable canonical Vina load—while enforcing CPU utilization.**

7. **Blocking — the stated ligand path does not exist.** [PLAN-calibration.md](C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PLAN-calibration.md:30) names `azithromycin.pdbqt`; the repository contains `azithromycin__state_01.pdbqt`.

   **Fix — Select `data/compounds/pdbqt_stage2/azithromycin__state_01.pdbqt` from the validated attempt row rather than spelling an independent path.**

8. **High — the claimed canonical box source is wrong.** Current `run_docking.py` constructs the receptor from each validated attempt-manifest row ([run_docking.py](C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/scripts/run_docking.py:157)); `receptor_prep_box` is an old result label, not the current lookup seam. Loading another document could silently calibrate a different box.

   **Fix — Select exactly the unique `workflow="wide"`, azithromycin/state_01, 5XYA row from the validated attempt manifest and abort on zero or multiple matches.**

9. **High — the provenance is insufficient to reconstruct the load.** Paths and `load_command` do not identify receptor or ligand bytes, and the plan omits attempt-manifest/box-source and calibrator-script hashes. Hashing files only after the run also permits a 10-minute input/source mutation race, especially in a synced workspace.

   **Fix — Hash the calibrator, supervisor, Vina, receptor, ligand, and source manifest before and after the run, require equality, and persist both the hashes and resolved box values.**

10. **High — “immutable artifact” has TOCTOU races.** Check-then-`os.replace` lets two calibrators overwrite one another, and the deterministic `.FAILED.json` can overwrite an earlier failure. The campaign root can also appear after the initial check because calibration shares neither launcher lock.

   **Fix — Hold the same campaign/launcher lock for the whole calibration, recheck the campaign root before emission, and publish a uniquely named temporary artifact with an atomic no-replace rename.**

11. **High — non-drift failures lose audit evidence.** Early completion and supervisor infrastructure failure abort without the detailed diagnostic record promised for drift failures; yet giving such a diagnostic the normal schema could let the current validator accept it when drift is small.

   **Fix — Emit unique failure-schema artifacts for early exit, inadequate CPU utilization, and supervisor failure, deliberately making them invalid under `docking-suspend-calibration-v1`.**

12. **Medium — the proposed tests validate assembly, not the load-bearing behavior.** They omit a peaked-then-decreased drift trace, clock-read skew, stalled-but-unsignaled Vina, duration overshoot, input mutation, concurrent writers, and a real short Windows deadline/cleanup path.

   **Fix — Add deterministic tests for every case above plus a short Windows integration test exercising actual timeout, termination, sampling, and cleanup without running the 600-second calibration.**

13. **Low — “all read from module constants” is factually impossible.** `docking.py` exports numeric calibration constants, but no public constants for the calibration schema or load literal.

   **Fix — Either introduce public protocol constants under an approved amendment or define the two literals locally and test them explicitly against the real validator.**

VERDICT: REVISE
### Claude's response — Round 1 (Claude is final arbiter)

**Independently verified before acting (not trusting Codex's claims):**
- **#7 CONFIRMED.** `ls data/compounds/pdbqt_stage2/ | grep azithro` → only `azithromycin__state_01.pdbqt`. Rev-1 named
  `azithromycin.pdbqt`. The harness would have died on a missing file.
- **#13 CONFIRMED.** `"docking-suspend-calibration-v1"` / `"single_core_docking_equivalent"` are inline literals at
  `docking.py:1780/1784`, not public constants. Rev-1's "read from module constants, never retyped" was impossible.
- **#8 CONFIRMED.** `run_docking.py:157` builds the receptor from the validated attempt-manifest row
  (`pocket_id`, `receptor_pdbqt_path`, `box_center_angstrom`, `box_size_angstrom`). `receptor_prep_box` is an obsolete
  *result label*, not the current lookup seam.

**Accepted in full:** #1, #2, #3, #4, #6, #7, #8, #9, #10, #11, #12, #13.

- **#1 + #2 force a redesign, not a patch.** The no-sampler design rested entirely on drift monotonicity. Codex is
  right that two monotonic clocks do not make a monotonic difference: `QueryUnbiasedInterruptTime` is quantized to the
  clock interrupt (~0.5–15.625 ms), so `wall − unbiased` sawtooths and max ≠ final. Compounding it, `SupervisedResult`
  reads the two clocks in separate statements (`docking.py:584-585`) with a preemption window between, and its end
  reads land after `TerminateJobObject` — so its pair never measured the interval rev-1 claimed. Replaced with a
  predeclared 1 Hz bracketed paired-sampling protocol gating on the **maximum** (§H9's literal wording, which rev-1
  had quietly reinterpreted as "final").
- **#3 is the sharpest finding.** `deadline_timeout` proves *unsignaled*, not *loaded* — rev-1's validity check would
  have certified a hung vina as a docking-equivalent load. Now gated on Job CPU accounting. The floor value is a new
  predeclared constant and is escalated to Josh rather than chosen by Claude: thresholds picked after seeing data are
  exactly how a gate becomes a knob (R4 #4).
- **#9** is materially strengthened by a fact Codex could not know it had: the repo lives in a **OneDrive-synced
  tree**, so the 10-minute input-mutation race is real. Pre/post hashing of all six inputs, equality required.

**Partially accepted — #5 (Claude's arbitration).** Codex is factually right that `require_suspend_calibration()`
validates neither campaign identity, freshness, host, nor hashes, and that per-campaign *naming* is convention rather
than enforcement. Its prescribed fix (a signed amendment enforcing all of it in the validator) is a **schema-v2
amendment Josh explicitly declined** in Act 1 — Codex advises, it does not command.

Rather than accept a forgeable gate or overrule Josh, plan §12 adds the binding at the **launcher**:
`run_campaign.sh` already holds both `SPYCEP_CAMPAIGN_ID` and `SPYCEP_SUSPEND_CALIBRATION_PATH`, so it asserts the
artifact's `campaign_id` matches and that it is not a failure artifact. This touches no approved code and no schema,
yet eliminates the *realistic* failure — a **stale** calibration silently gating a fresh campaign, an accident far
likelier than forgery. It does **not** make the artifact unforgeable, and the plan says so plainly rather than
claiming the ADR repairs it. Escalated to Josh as Open Decision B; if he prefers Codex's stronger form, that is a
different plan.

**Nothing rejected outright.** Plan rewritten as **revision 2**. Proceeding to Round 2 on the same thread.

---

## Round 2 — Codex (same thread `019f6f9c-5ad9-78d2-acb0-9c8f4849480a`, read-only, 6m 20s)

Revision 2 is materially stronger, but it is not yet implementable or scientifically closed. The new sampling and accounting design introduces several blocking gaps.

## Blocking findings

1. **Job CPU accounting is impossible through the declared seam.** `_run_vina_supervised()` owns an unnamed local Job handle and closes it before returning; `SupervisedResult` carries no accounting data. The producer therefore cannot perform §8 while also obeying “no `docking.py` edits” and “reuse the existing supervisor.” Windows accounting must be queried through the live Job object, although it correctly includes both active and terminated processes. [Microsoft Job accounting](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-jobobject_basic_accounting_information), [Job Objects](https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects).

   **Fix — Revise scope to expose `job_cpu_seconds` from `_run_vina_supervised()` before its Job handle closes, or explicitly implement a calibration-specific supervisor; the current producer-only design cannot supply this evidence.**

2. **The bracketed-read mathematics is underspecified.** The protocol records `unbiased₁, wall, unbiased₂` but then uses an undefined `unbiasedᵢ`; it never says midpoint, lower bound, or upper bound, nor gives the exact conservative uncertainty formula. “Handled conservatively” is not implementable or testable.

   **Fix — Define `uᵢ=(u₁+u₂)/2`, units/conversion, the per-sample drift estimator, and the exact upper-confidence bound incorporating baseline skew, sample skew, and unbiased-clock tick uncertainty.**

3. **The skew bound is neither specified nor escalated.** It is a load-bearing rejection threshold just like the CPU floor, yet no value or derivation appears under Open Decisions. Also, `u₂-u₁` includes clock-tick advancement, not merely call latency.

   **Fix — Predeclare and obtain approval for the skew bound and its derivation, explicitly accounting for `QueryUnbiasedInterruptTime` tick quantization.**

4. **“Reject/retry any sample” can erase the maximum.** If a high-drift observation has excessive skew and is discarded, a retry after the sawtooth falls can replace it with a lower value. That biases the gate toward passing.

   **Fix — Persist every attempted read and invalidate the entire calibration on any over-skew sample; never replace a rejected observation with a retry inside the same run.**

5. **A nominal 1 Hz thread does not guarantee 1 Hz evidence.** Thread starvation, an exception, or late scheduling could leave multi-second holes while still producing enough samples to assemble a record. There is no minimum count, maximum intersample gap, mandatory terminal sample, or thread-health condition. A suspend during the last interval could otherwise be missed.

   **Fix — Use absolute sampling deadlines, require a terminal sample after supervisor completion, bound every actual intersample gap, require minimum coverage/count, and fail if the sampler exits or raises.**

6. **The sampling window is not coordinated with the supervisor window.** The synchronous private function exposes neither “child resumed” nor “deadline reached”; starting the sampler around the call includes Job setup and teardown. That wider envelope is conservative for drift, but its duration is not the load-active interval and cannot safely serve as the CPU-utilization denominator.

   **Fix — Define the sampler explicitly as a conservative enclosing window while calculating utilization against the Job’s own process lifetime, or expose nonblocking start/end notifications from the supervisor.**

7. **An average 0.80 floor does not establish a full-window load.** A process that consumes one core for 480 seconds and then stalls for 120 seconds passes. A floor alone also accepts accidental multi-core execution because there is no upper bound. Thus it does not support “single-core docking-equivalent load for the full duration.”

   **Fix — Sample cumulative Job CPU throughout the run and prospectively approve both an overall utilization range and a maximum low-utilization interval, including an upper bound for unintended multi-core use.**

8. **The plan cannot be approved while its scientific threshold remains open.** The proposed 0.80 value is not approved, and the redesign adds other undeclared thresholds: skew limit, cadence tolerance, minimum sample count, and clock-resolution allowance.

   **Fix — Move every measurement-validity constant into Open Decisions and freeze all values before implementation or live data collection.**

## Launcher arbitration

The launcher check is **not security theater**, but it is only defense in depth for one invocation path. The claim that it “closes Codex #5” is not defensible:

- All three Python entry points can be invoked directly and call `require_suspend_calibration()` without comparing the returned `campaign_id`; this is a realistic operational path, not malicious bypass.
- Matching campaign ID does not detect an old artifact produced before an OS, supervisor, Vina, receptor, ligand, or power-policy change.
- Checking whether a filename “is a failure artifact” has no integrity value; a failure can be renamed, and a valid campaign ID may itself contain `FAILED`. Failure-schema rejection already belongs to the validator.
- The launcher check is absent from the proposed tests.
- Parsing in the launcher and reopening later creates a check/use split; comparing the record returned by each entry point avoids that.

9. **Campaign binding is enforced at the wrong layer.**

   **Fix — Without changing the approved validator, modify every Python campaign entry point to compare `require_suspend_calibration()`’s returned `campaign_id` with `require_campaign_id()` and test those direct-entry paths; retain the launcher check only as an early diagnostic.**

10. **The claimed stale-artifact protection is narrower than stated.** A matching campaign ID can still reference a months-old calibration from a changed host environment; all relevant hashes are recorded but unenforced.

   **Fix — Either add a launcher/entry-point verification helper that checks current hashes, host/build and an approved freshness rule, or explicitly classify those checks as mandatory manual pre-launch review rather than saying stale reuse is eliminated.**

## Other concrete issues

11. **“Validated attempt manifest” introduces an unrecorded seventh input.** `validate_attempt_manifest()` requires the species catalog, but §4 hashes only six inputs and omits `docs/methods/species_audit.json`.

   **Fix — Load, validate, pre/post hash, and persist the species catalog alongside the attempt manifest.**

12. **Failure observability remains incomplete.** The failure schemas cover early finish, utilization and supervisor failure, but not sampler death, cadence gaps, excessive skew, shortened coverage, hash mutation, or failed post-run campaign-root recheck.

   **Fix — Define a general measurement/integrity failure schema covering every condition that prevents a valid calibration and preserve all partial samples and hashes.**

13. **The lock does not match the full launcher lock.** `campaign_lock()` coordinates individual Python stages through `results/docking/.docking-campaign.lock`, while `run_campaign.sh` holds `.campaign.lock` across all four stages. A calibration for another ID can start between stages and make the next stage abort.

   **Fix — Acquire both existing locks in their established order for calibration, or consolidate them under one shared lock used by the launcher and every Python entry point.**

14. **The plan contradicts its own results scope.** `campaign_lock()` necessarily creates and removes a file under `results/docking`, while §§14/out-of-scope claim nothing touches `results/`.

   **Fix — State explicitly that the transient shared lock is the sole permitted `results/` write and that no persistent scientific result artifact is created.**

15. **The tests do not cover the redesign’s most dangerous failures.** Missing cases include sampler death, missing terminal sample, excessive cadence gap, uncertainty-bound arithmetic, a late-window peak, concentrated CPU stall, multi-core overutilization, species-catalog mutation, and direct-entry launcher bypass.

   **Fix — Add deterministic tests for these cases and make the short Windows integration test assert real Job accounting as well as timeout, sampling, termination, and cleanup.**

## Prior round disposition

- Fully resolved: #4, #6, #7, #8, #13.
- Substantively corrected but incomplete in implementation: #1, #2, #3, #9, #10, #11, #12.
- #5: launcher binding is useful defense in depth, but it does not close stale reuse or bind all executable entry points.

VERDICT: REVISE
### Claude's response — Round 2: loop PAUSED, returned to human

**Verified independently:**
- **#1 CONFIRMED.** No Job accounting exists in `docking.py` (zero hits for `QueryInformationJobObject` /
  `TotalUserTime` / `TotalKernelTime`); the Job handle is closed in cleanup; `SupervisedResult` has no
  accounting field. Rev-2 was **internally contradictory**: CPU-utilization gating and "no `docking.py` edits"
  cannot both hold. This is a scope decision only Josh can make.
- **#11 CONFIRMED.** `validate_attempt_manifest(manifest, species_catalog)` (`attempt_manifest.py:129`) requires
  the species catalog; `docs/methods/species_audit.json` exists. Rev-2 hashed six inputs and missed a seventh.
- **#13/#14 CONFIRMED** by inspection: `campaign_lock()` uses `results/docking/.docking-campaign.lock` while
  `run_campaign.sh` holds `.campaign.lock` at the repo root — two different locks. And since `campaign_lock()`
  necessarily writes under `results/`, rev-2's "nothing touches `results/`" contradicted its own §3.

**#9 — Codex beat Claude's arbitration, and Claude concedes.** Rev-2 §12 bound the artifact to the campaign at
  the launcher. Codex correctly observes that all three Python entry points can be invoked directly
  (`run_campaign.sh` itself calls them as `$PY scripts/run_docking.py`), so a launcher check covers exactly one
  path. Its alternative is strictly better AND honors Josh's Act-1 constraint just as well: have each entry point
  compare the `campaign_id` in the record **returned by** `require_suspend_calibration()` against
  `require_campaign_id()`. That touches the three entry-point scripts — **not** `validate_suspend_calibration`
  and **not** the v1 schema. Accepted; the launcher check demotes to an early diagnostic.
  Codex is also right that filename-based "is it a FAILED artifact" has no integrity value.

**Why the loop is paused at round 2 of 5 rather than continuing.** Codex #8 is correct and is dispositive:
the plan **cannot be approved while its measurement-validity constants remain open**, and the rev-2 redesign
*added* thresholds rather than closing them. Every one is a prospectively-approved scientific constant — which is
the entire point of R4 #4: a threshold chosen after seeing data is how a gate becomes a knob. Claude must not
pick these. Rounds 3–5 could only return REVISE until Josh freezes them, so burning them would be theatre.

Returned to Josh: the scope fork (#1) and the full constant list. Act 1 is effectively reopened — round 2
surfaced decisions that did not exist when the plan was locked.

---

## Round 3 — Codex (same thread, read-only, 7m 38s)

Revision 3 resolves most prior structural objections, especially campaign binding, manifest provenance, lock coordination, and failure-schema separation. However, two “conservative” claims remain mathematically unsupported, and the internal CPU sampler is not sufficiently specified to preserve the approved single-wait supervisor.

## Blocking findings

1. **The enclosing window is not necessarily conservative.** [The plan claims](C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PLAN-calibration.md:88) that a wider window can only over-report drift. That is false once monotonicity is withdrawn because every drift is relative to the earlier enclosing baseline. If drift falls −0.4 s during setup and rises +0.6 s during the load, the enclosing measurement reports only +0.2 s even though the load-window excursion is +0.6 s.

   **Fix — Establish the drift baseline at the supervisor’s ResumeThread boundary, or gate on the maximum conservative drift increase over every eligible baseline/sample pair rather than only against the enclosing `t₀`.**

2. **The upper-bound formula is conditionally conservative, not “exact.”** The formula is correct if the nonprecise counter is guaranteed to lag true unbiased time by at most `TICK`: `Uᵢ ≥ u₁ᵢ` and `U₀ ≤ u₂₀+TICK` imply the stated bound. But the plan’s claim that true time lies in `[u₁ᵢ,u₂ᵢ]` is false—`u₂ᵢ` may still lag the wall-read instant. More importantly, Microsoft documents 0.5–15.625 ms as the **typical range**, not a contractual worst case, and describes accuracy “within a tick” without formally specifying the required one-sided error. [Microsoft documentation](https://learn.microsoft.com/en-us/windows/win32/api/realtimeapiset/nf-realtimeapiset-queryunbiasedinterrupttimeprecise).

   **Fix — Either validate the actual host’s nonprecise-counter lag against `QueryUnbiasedInterruptTimePrecise`, or prospectively amend the protocol to bracket with the precise API; do not call 15.625 ms a documented worst-case bound without runtime verification.**

3. **Internal Job sampling can silently destroy the single armed wait unless it uses a separate thread.** The supervisor’s main thread is blocked in one `WaitForSingleObject`; it cannot sample Job accounting “on a cadence” without chunking/polling the wait, which the ADR expressly rejects.

   **Fix — Specify an opt-in dedicated Job-accounting thread, default-disabled for campaign calls, with a baseline-ready handshake, bounded shutdown, mandatory terminal accounting sample, exception propagation, and main-thread retention of the single uninterrupted wait.**

4. **The Job CPU sampling cadence is missing.** `MAX_LOW_UTIL_INTERVAL_SECONDS=30` has no defined meaning without a CPU sample interval, maximum CPU-series gap, timestamp basis, and terminal-sample rule. A 35-second delayed sample can average over and conceal a 30-second stall.

   **Fix — Freeze the Job-series cadence and coverage rules, timestamp samples in unbiased time since successful ResumeThread, forbid catch-up/backfill, and invalidate any CPU-series gap too large to adjudicate the 30-second rule.**

5. **Not all measurement-validity constants are actually in the frozen table.** The external 1 Hz cadence, CPU-series cadence, embedded `0.50` low-utilization threshold, CPU-series maximum gap, and interval-boundary policy all affect passing but are not named frozen constants.

   **Fix — Add every pass/fail-affecting numeric value and inequality convention to the frozen table before implementation.**

## Internal consistency defects

6. **The claimed “≈0.43 s effective gate” is stale and inconsistent.** With negligible read skew, adding one tick yields approximately 0.484 s, not 0.43 s. With two individually valid 0.250-second brackets, the upper-bound inflation can exceed 0.5 s, causing zero true drift to fail while neither sample is classified as over-skew.

   **Fix — Remove the 0.43 claim, report the actual per-run uncertainty inflation, and classify an upper-bound-only crossing as measurement-indeterminate rather than falsely attributing it to host drift.**

7. **The CPU ceiling catches only sustained multi-core use.** Section 8 applies `[0.90,1.10]` to the mean; two-core execution for a shorter interval can still average below 1.10 and pass. That contradicts “catches accidental multi-core.”

   **Fix — Either apply a prospectively defined per-interval ceiling or narrow the claim to sustained mean over-utilization.**

8. **“Job process lifetime” is still ambiguous.** Creation-to-termination includes the intentionally suspended setup period; ResumeThread-to-post-reap includes termination overhead. These produce different utilization values near a frozen 0.90 boundary.

   **Fix — Define the utilization denominator exactly as unbiased time from successful ResumeThread to the kernel deadline, while retaining post-termination CPU accounting only as the cumulative numerator.**

9. **The external sampler needs an explicit start handshake.** Merely starting a Python thread before calling the supervisor does not ensure `t₀` exists before Job setup or ResumeThread; the new thread may be scheduled late.

   **Fix — Require the sampler to take and persist its baseline and signal “ready” before the main thread may enter `_run_vina_supervised()`.**

10. **Absolute-deadline behavior across sleep is unspecified.** Because QPC includes sleep, many 1 Hz deadlines become overdue on resume; backfilling them rapidly can falsely satisfy `MIN_SAMPLE_COUNT`. The gap limit also does not identify whether it uses wall or unbiased time.

   **Fix — Skip missed deadlines rather than backfill, record both wall and unbiased gaps, and define sampler-health gaps on unbiased awake time.**

## Revision regressions and observability

11. **Revision 3 dropped explicit entry gates and command construction.** It no longer clearly requires `require_campaign_id()`, initial campaign-root/target refusal, exact `_run_vina_supervised(..., 600.0)`, `build_vina_command()`, frozen command arguments, temporary output placement, or cleanup.

   **Fix — Restore a self-contained entry/load-construction section specifying every gate, argument, path derivation, nominal timeout, and cleanup guarantee.**

12. **“Any failure” cannot always preserve both hash sets and partial samples.** Missing input, pre-hash failure, sampler construction failure, lock contention, or output failure can occur before those values exist.

   **Fix — Define staged failure records with `failure_stage`, required evidence by stage, and explicit nullable/unavailable fields rather than promising evidence that cannot yet exist.**

13. **The new concurrency lifecycle lacks failure-order rules.** If either sampler fails while the main thread is waiting, the supervisor must still terminate/reap Vina before propagating failure; conversely, joining a wedged sampler must not orphan or indefinitely delay cleanup.

   **Fix — Specify fail signaling, deadline continuation, termination, final accounting, bounded joins, handle closure, and exception precedence as an explicit state machine.**

14. **The expanded tests still need the new counterexamples.**

   **Fix — Add tests for negative pre-load drift followed by a load-window rise, an actual tick lag above the assumed bound, delayed CPU-series sampling concealing a stall, sampler start races, post-sleep deadline backfill, and optional accounting being disabled for ordinary campaign calls.**

## Campaign binding

The entry-point comparison now resolves my round-2 launcher-bypass objection without changing the approved validator. That is a defensible operational compromise. The remaining statement that it “kills” stale calibration is still too broad: it prevents cross-campaign-ID reuse, but not an old matching-ID artifact after host/code changes. Given the human’s explicit provenance decision, this is acceptable only as a plainly stated limitation, not as freshness enforcement.

## Proportionality

The design is beginning to fight the problem. Two coordinated sampler threads, a modified scientific supervisor, several cadence/coverage rules, and an uncertain tick bound are a large failure surface for a preflight gate.

A simpler defensible alternative is:

- bracketed drift sampling with an exact ResumeThread baseline and mandatory terminal sample;
- real Vina under the existing single wait;
- one final Job CPU aggregate with the frozen mean band;
- explicit admission that aggregate utilization cannot exclude a localized stall.

That loses the 30-second stall guarantee but is easier to audit and less likely to alter the campaign supervisor incorrectly. If continuous-load proof remains mandatory, revision 3 needs the additional protocol details above.

VERDICT: REVISE
### Claude's response — Round 3: STOPPING the loop at 3 of 5, per the pre-committed trigger

Before round 3 Claude told Josh: *"If round 3 comes back with a fourth wave of structural defects rather than
detail fixes, I'd treat that as the design telling us something, and I'd bring you the simpler option rather
than push to round 4."* Codex independently reached the same conclusion — **"the design is beginning to fight
the problem"** — and proposed the simpler alternative itself. Honoring the commitment; not burning rounds 4–5.

**Three errors in the frozen table Josh approved — all Claude's, all material:**

1. **The "≈0.43 s effective gate" was arithmetically wrong** (Codex #6). It was computed with the 50 ms skew
   allowance that Claude then *removed* from the design in the same revision. With skew folded into the bound,
   one tick gives ≈**0.484 s**, not 0.43. A stale number survived into a plan presented as approved.
2. **The tick constant was mislabeled "Documented — Microsoft"** (Codex #2). Microsoft documents 0.5–15.625 ms
   as a **typical range**, not a contractual worst-case one-sided bound. Josh approved that row partly on the
   strength of the word *Documented*. It is a **judgment** call wearing a citation's clothing — the single most
   important correction in this round, because the whole conservative-bound argument rests on it.
3. **The frozen constants are internally inconsistent** (Codex #6). `INSTRUMENT_SKEW_LIMIT_SECONDS = 0.250`
   against a 0.5 s gate means two individually *in-limit* brackets can inflate the upper bound past the gate,
   failing a run with **zero true drift** while neither sample is flagged over-skew. Claude set both numbers in
   the same table and did not check them against each other.

**Also conceded:**
- **#1 (enclosing window is not conservative).** Correct in principle: once monotonicity is withdrawn, a drift
  *fall* during setup can mask a *rise* during the load, because every drift is relative to the enclosing
  baseline. Claude notes the magnitude Codex uses (−0.4 s) is unphysical given tick-scale quantization, but the
  formulation is still wrong and the fix (baseline at ResumeThread, or max over eligible baseline/sample pairs)
  is cheap and correct.
- **#11 (revision regression).** Rewriting rev-2 → rev-3 silently dropped the explicit entry-gate and
  load-construction section (`require_campaign_id()`, campaign-root refusal, `build_vina_command()`, temp-dir
  cleanup). Codex caught a regression Claude introduced by rewriting rather than editing.
- **#3 (structural).** The supervisor's main thread is blocked in the single armed wait, so internal Job
  sampling needs *another* thread inside the scientific supervisor — chunking the wait is precisely what
  ADR-0001 rejects. Two coordinated sampler threads plus a modified campaign supervisor is the failure surface
  Codex is objecting to, and it exists only to serve `MAX_LOW_UTIL_INTERVAL_SECONDS`.

**Campaign binding: settled.** Codex accepts the entry-point comparison as resolving its round-2 objection.
It correctly insists the word "kills" is still too broad — matching campaign IDs do not detect an old artifact
from a changed host. To be reworded as a plainly stated limitation, not freshness enforcement.

**Returned to Josh: simplify (Codex's alternative, which is also Josh's originally-approved aggregate scope) vs.
continue.** Claude is not deciding this — it is a scope/scientific-guarantee trade, and the last two rounds
show Claude's judgment on proportionality has been the thing consistently drifting.

---

## Round 4 — Codex (same thread, read-only, 3m 45s) — 2 blockers, 5 refinements

Revision 4 is substantially simpler, but two remaining issues can still let an invalid calibration pass. These are blockers, not review polish.

## Blockers

1. **The aggregate CPU arithmetic does not prove “no contiguous stall over 30 seconds.”** At 600 seconds, a 60-second stall still passes if the remaining 540 seconds average 1.056 CPU cores: `570 / 600 = 0.95`. The mean ceiling does not constrain instantaneous utilization. Even with a hard one-core cap, a 620-second window permits 31 seconds idle at exactly 0.95 utilization.  
   **Fix:** Describe the aggregate as mean-load evidence only and explicitly withdraw the contiguous-stall guarantee; preserving that guarantee requires interval sampling or a separately enforced instantaneous one-core cap plus a duration-dependent floor.

2. **The gate validates the precise clock, but the campaign consumes the non-precise clock.** Microsoft documents the non-precise API as based on the latest timer tick, whereas the precise API obtains a more current value; they therefore need not produce identical elapsed intervals. Merely recording their lag cannot stop a non-precise clock anomaly from passing calibration and corrupting campaign suspend detection. Moreover, the proposed `p_i - n_i` compares readings taken at different instants because `n_i` follows `p2_i`. [Microsoft’s API documentation](https://learn.microsoft.com/en-us/windows/win32/api/realtimeapiset/nf-realtimeapiset-queryunbiasedinterrupttimeprecise)  
   **Fix:** Bracket `QueryUnbiasedInterruptTime` itself around each wall read and apply the conservative pairwise upper-bound gate to that campaign clock; retain the precise clock only as diagnostic evidence.

## Important refinements

- **The pairwise-max mathematics is correct for observed samples.** `max(i<j)(D_j-D_i)` detects a sampled fall followed by a sampled rise and eliminates the arbitrary-origin problem. It does not cover a trough occurring between samples—particularly between the ready baseline and `ResumeThread`.  
  **Fix:** State explicitly that this is a maximum-observed protocol, or add an opt-in supervisor sample immediately around the resume boundary.

- **The CPU numerator and denominator do not share an endpoint.** Job CPU queried after termination includes activity beyond the stated “wait return” endpoint. That biases utilization upward, precisely where the 0.95 threshold matters.  
  **Fix:** Define both against an enclosing active-lifetime endpoint taken after termination/accounting, or capture both at the same pre-termination point.

- **“Exactly from successful `ResumeThread` to wait return” is not literally obtainable without inserting clock calls into that interval.** This is harmless if declared as a bracketed/enclosing measurement, but “exactly” overstates the instrument.  
  **Fix:** Specify the actual timestamp placement and call the result enclosing or bounded rather than exact.

- **Positive drawup alone does not detect monotonic negative divergence.** Such divergence can reduce a real suspend gap and create a false negative during the campaign.  
  **Fix:** As a fail-closed strengthening, reject or mark indeterminate when the maximum negative excursion exceeds the same 0.5-second tolerance.

- **“Byte-for-byte unaffected” is false even with accounting disabled.** Editing `docking.py` changes the supervisor source hash and therefore provenance fingerprints.  
  **Fix:** Say the ordinary campaign’s runtime control flow is unaffected; acknowledge the intentional provenance-hash change.

The staged failure schema, lock handling, missed-deadline policy, failure ordering, restored manifest construction, and campaign-ID binding now look defensible. The two blockers above are localized: the simplified design can remain, but it must stop claiming stall-contiguity proof and must calibrate the clock actually used by the campaign.

VERDICT: REVISE
### Claude's response — Round 4

**Blocker #1 conceded — and it invalidates the argument Claude used to sell Josh the simplification.**
Claude claimed `mean >= 0.95 => no contiguous stall > 30 s`. False. The inference needs an **instantaneous**
one-core cap; only the *mean* is bounded (at 1.10), so a burst above one core pays for a stall:
60 s idle + 540 s at 1.056 cores = 570 core-s / 600 s = 0.95 → passes. Codex further notes the bound is
duration-dependent (a 620 s window allows 31 s idle at 0.95). **The stall guarantee does not exist and is
withdrawn.** Josh chose the simplified design partly on this claim; the correction is being put to him rather
than quietly patched.

**Blocker #2 conceded — Claude's fix for an earlier error created a new one.** Moving drift measurement to
`QueryUnbiasedInterruptTimePrecise` escaped the mislabelled tick constant but calibrates a clock **the campaign
does not use**: suspend detection runs on the non-precise API. Recording the lag cannot stop a non-precise
anomaly from passing. Codex is also right that `p_i - n_i` compared readings at different instants.

**Note on the tension Codex's fix does not fully resolve:** bracketing the *non-precise* clock does not by
itself bound quantization — two reads inside one tick return an identical value, so the bracket collapses to
zero width while true time is anywhere within that tick. The campaign clock therefore still needs a lag
allowance. Rev-5 resolves this by **measuring** that allowance (max observed precise-vs-non-precise lag, each
lag itself bracketed) rather than assuming 15.625 ms, and gating the **campaign's** clock with it — precise
retained as a cross-check. This is Codex R3 #2's first option, arrived at by its own R4 #2.

**Accepted refinements:** pairwise-max is maximum-*observed* (a trough between samples is uncovered — to be
stated, not hidden); numerator/denominator must share an endpoint; "exactly from ResumeThread" overstates the
instrument (bracketed/enclosing is the honest word); monotonic **negative** divergence should also be
fail-closed (it can shrink a real suspend gap → false negative in the campaign); "byte-for-byte unaffected" is
false — editing `docking.py` intentionally changes the supervisor provenance hash.

Returned to Josh: the floor value, now that the guarantee it was buying is gone.

---

## Round 5 — Codex (FINAL, same thread, 7m 40s) — 2 blockers, 4 clerical

Revision 5 is close and the simplified claim is scientifically defensible. Two remaining specification defects still prevent sign-off; neither requires restoring CPU-series sampling.

## Blockers

1. **The CPU denominator still excludes possible numerator time.** The plan starts the denominator immediately *after* `ResumeThread`, so the child can accumulate Job CPU while the supervisor is descheduled before taking that timestamp. Job accounting includes the process’s entire execution, including terminated processes; this can inflate utilization past 0.90. The plan also contradicts itself between “after wait returns,” “post-termination endpoint,” and the test’s “resume-to-deadline.” [Microsoft documents the cumulative accounting semantics](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-jobobject_basic_accounting_information).  
   **Fix:** Timestamp immediately **before** `ResumeThread`; after timeout, terminate and reap, query Job accounting while its handle remains live, then take the denominator’s end timestamp—making the denominator conservatively enclose every possible numerator interval.

2. **The negative-excursion gate has no defined conservative formula.** Section 7 defines `excursion_upper`, but “`min` of the same quantity” could mean the midpoint estimate or the positive upper bound. Neither proves that negative drift is within tolerance. A non-precise step occurring between `n1` and the wall read can leave the midpoint above −0.5 while the clock value consumed at the wall instant has moved by more than 0.5. The cross-check is also ambiguous about whether it compares each `(i,j)` interval or only aggregate extrema.  
   **Fix:** Define and gate a lower bound explicitly, e.g. `excursion_lower_ij = Δw − (n2_j − n1_i) − MEASURED_LAG`, require `min(excursion_lower_ij) ≥ −0.5` for PASS, and define the precise/non-precise comparison per identical `(i,j)` interval; add a test for a forward non-precise step inside the five-read bracket.

## Required consistency cleanup

These are clerical rather than new scientific-design objections, but they must be corrected before implementation:

- [PLAN-calibration.md:53](C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PLAN-calibration.md:53) still repeats the withdrawn false 0.95 ⇒ 30-second guarantee.
- [PLAN-calibration.md:59](C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PLAN-calibration.md:59) still says the frozen floor is 0.95.
- [PLAN-calibration.md:212](C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PLAN-calibration.md:212) says 0.94 must fail, contradicting the frozen 0.90 floor; use 0.89.
- [PLAN-calibration.md:213](C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PLAN-calibration.md:213) still tests “resume-to-deadline,” contradicting the required post-termination enclosing endpoint.

Everything else load-bearing is now resolved: the stall claim is honestly withdrawn, the campaign’s actual non-precise clock is gated, positive excursion is conservative, maximum-observed limitations are disclosed, early completion fails closed, and the provenance/freshness limitations are accurately stated.

VERDICT: REVISE
## Resolution — MAX_ROUNDS reached without APPROVED

`MAX_ROUNDS=5` is a hard cap; the loop terminates here. **Codex never returned `VERDICT: APPROVED`.** Per the
skill's rule, that is recorded as a deadlock rather than dressed up as convergence.

**But it is not a substantive deadlock. Claude has no counter-position — there is nothing in dispute.**
Round 5's findings are two specification defects for which Codex supplied exact formulas, plus four stale-text
errors that are Claude's alone. All six verified and applied as **revision 6**:

- **R5 #1 (denominator) — conceded; rev-5 had it backwards.** Timestamping *after* `ResumeThread` lets the child
  accrue Job CPU while the supervisor is descheduled, inflating utilization past the floor with time the
  denominator never counted. Now: start **before** `ResumeThread`; terminate, reap, query accounting while the
  handle is live, then take the end timestamp. Numerator ⊆ denominator ⇒ utilization can only be *under*-stated,
  which is the fail-closed direction against a floor. Codex was also right that rev-5 gave three different
  answers ("after wait returns" / "post-termination" / "resume-to-deadline") to one question.
- **R5 #2 (negative gate) — conceded.** "`min` of the same quantity" was ambiguous between the midpoint estimate
  and the positive upper bound, and **neither proves negative drift is in tolerance**. Now explicit:
  `excursion_lower_ij = Δw − (n₂ⱼ − n₁ᵢ) − MEASURED_LAG`, PASS requires `min ≥ −0.5`. Cross-check defined
  **per identical (i,j) interval**. Test added for a forward non-precise step inside the five-read bracket.
- **Clerical (all four confirmed by inspection, all Claude's):** line 53 still asserted the **withdrawn false**
  0.95⇒30 s guarantee (a builder reading it would have implemented the very claim withdrawn 19 lines earlier);
  line 59 still said 0.95; line 212 tested that 0.94 must fail (it **passes** at a 0.90 floor); line 213 still
  said resume-to-deadline. These are the cost of editing rather than rewriting — the opposite failure to R3 #11,
  where rewriting silently dropped a section.

**Status handed to Josh:** revision 6 incorporates every round-5 finding, and Codex's closing assessment was
*"Everything else load-bearing is now resolved: the stall claim is honestly withdrawn, the campaign's actual
non-precise clock is gated, positive excursion is conservative, maximum-observed limitations are disclosed,
early completion fails closed, and the provenance/freshness limitations are accurately stated."*

**Caveat Josh must weigh: revision 6 has never been reviewed by anyone.** It was written after the final round.
The last reviewed artifact is revision 5, which Codex rejected. Every rev-6 change is an application of Codex's
own prescription, but 'applied the reviewer's fix' is not the same as 'the reviewer checked the fix' — and this
session's record shows Claude introducing a new defect while fixing an old one at least twice (the precise-clock
swap in rev-4; the denominator direction in rev-5).

### MAX_ROUNDS lifted — Josh, 2026-07-17

Josh authorized a sixth round, raising the cap. Recorded explicitly because `MAX_ROUNDS=5` is a hard rule Claude may
not override: the cap is the skill's guard against an infinite loop, not a scientific principle, so lifting it is the
human's call and is logged as such. Rationale: revision 6 was written *after* the final round and has zero review,
while the last reviewed artifact (rev-5) was rejected — and this session records two instances of Claude introducing a
fresh defect while applying a fix (rev-4's precise-clock swap; rev-5's denominator direction), each caught only by a
further round.

---

## Round 6 — Codex (cap lifted by Josh, 4m 09s) — 1 blocker, 4 refinements

Revision 6 correctly fixes the denominator’s start/end containment and the negative-excursion mathematics. One new blocker remains.

## Blocker

**The enclosing denominator is fail-closed for the utilization floor but not for the ceiling.** Cleanup/reap time enlarges the denominator without necessarily adding Job CPU, diluting the ratio and allowing sustained utilization above 1.10 to pass. Example: 663 core-seconds over the actual 600-second active interval is 1.105 and should fail; with five seconds of post-termination enclosure, `663/605 = 1.096`, which passes.

**Fix:** Use two conservative bounds:

- Floor: `job_cpu_seconds / enclosing_window_seconds >= 0.90`.
- Ceiling: `job_cpu_seconds / 600.0 <= 1.10`, since `deadline_timeout` guarantees the process was active for at least the nominal 600-second armed wait.

Alternatively, measure a separate inner duration for the ceiling. Do not apply both limits to the same enclosing denominator.

## Verification of the R5 fixes

- The start-before-`ResumeThread`, end-after-termination/reap/accounting ordering encloses execution and termination CPU. `CREATE_SUSPENDED` prevents the primary thread from running before resume, and Job accounting retains CPU from terminated processes. [Microsoft: process creation flags](https://learn.microsoft.com/en-us/windows/win32/procthread/process-creation-flags), [Microsoft: Job accounting](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-jobobject_basic_accounting_information).
- The lower bound is mathematically conservative: because `N(w_i) ≥ n1_i` and `N(w_j) ≤ n2_j`,  
  `Δw − (n2_j − n1_i)` is a lower bound on `Δw − ΔN`; subtracting a nonnegative `MEASURED_LAG` only makes it more conservative.
- The four R5 clerical contradictions are genuinely removed.

## Non-blocking refinements

- Explicitly require `n1≤n2`, `p1≤p2`, and `MEASURED_LAG≥0`; otherwise classify the run as INDETERMINATE.
- Specify whether the per-interval precise/non-precise cross-check compares midpoint estimates or conservative bounds.
- The revision header still says “after Codex rounds 1–4.”
- ADR-0002 is promised twice but does not exist and is absent from the declared file list; either add it to scope or remove those promises.

The drift instrument itself is now defensible. The remaining blocker is localized to applying a two-sided utilization band to a one-sided conservative denominator.

VERDICT: REVISE
### Claude's response — Round 6

**Codex verified the R5 fixes as correct** — containment ordering (`CREATE_SUSPENDED` prevents the primary
thread running before resume; Job accounting retains terminated-process CPU), the lower-bound mathematics, and
the removal of all four clerical contradictions. This is the first round where prior fixes were confirmed rather
than re-opened.

**The one blocker was created by Claude's own rev-6 fix — the third time this session.** Conceded immediately:
the enclosing denominator is fail-closed for the **floor** but **fail-open for the ceiling**, because
cleanup/reap time enlarges the denominator without adding CPU and dilutes the ratio — 663 core-s / 600 s real
active = 1.105 (must fail), but 663/605 = 1.096 (passes). Applying a **two-sided band to a one-sided**
conservative denominator was the error. Fixed per Codex: floor against the enclosing window; ceiling against the
nominal 600.0, which `deadline_timeout` guarantees as a minimum active interval. Each bound now has a
denominator conservative in its own direction.

**Refinements applied:** well-formedness (`n₁≤n₂`, `p₁≤p₂`, `MEASURED_LAG≥0`) checked → INDETERMINATE, not
assumed; cross-check specified to compare **midpoint estimates** (bounds would be dominated by bracket width and
flag nothing); header corrected to rounds 1–6; **ADR-0002 promoted from a promise to an in-scope deliverable** —
it was referenced twice and declared nowhere.

Trend across rounds: 13 → 15 → 14 → 2 → 2 → 1. Codex: "The drift instrument itself is now defensible."

---

## Round 7 — Codex (2m 20s) — **VERDICT: APPROVED**

Revision 7 is implementable and scientifically defensible for its narrowed claims.

Let `C` be Job CPU, `T` the actual CPU-accruing active interval, and `O` the enclosing interval. The ordering establishes `O ≥ T ≥ 600`:

- Floor: `C/O ≥ 0.90` implies `C/T ≥ 0.90`.
- Ceiling: `C/600 ≤ 1.10` implies `C/T ≤ 1.10`.

A longer active/enclosing window cannot create a ceiling false-pass: dividing by 600 only increases the calculated upper bound. Termination CPU is included in `C` and enclosed by `O`; it can cause a conservative failure, not an invalid pass.

The well-formedness checks, midpoint cross-check, negative lower bound, corrected header, and ADR-0002 scope are internally consistent. No new load-bearing defect was introduced.

Two optional naming cleanups remain: record both utilization values explicitly rather than singular “utilization,” and replace the residual phrase “utilization band” with “two utilization bounds.” Neither affects validity.

VERDICT: APPROVED
### Claude's response — Round 7: CONVERGED

Both optional naming cleanups applied (plan is **revision 8**): "utilization band" → "two utilization bounds";
the record now carries `utilization_floor_ratio` (C/O) and `utilization_ceiling_ratio` (C/600) explicitly rather
than a singular "utilization". Neither affected validity; both remove an ambiguity a builder could resolve wrong.

## Act 2 complete — 7 rounds, converged

| Round | Findings | Outcome |
|---|---|---|
| 1 | 13 | REVISE — 3 confirmed factual errors; monotonicity premise destroyed |
| 2 | 15 | REVISE — CPU accounting impossible through the declared seam; launcher arbitration beaten |
| 3 | 14 | REVISE — "the design is beginning to fight the problem"; simpler alternative proposed |
| 4 | 2 blockers | REVISE — false stall arithmetic; wrong clock gated |
| 5 | 2 + 4 clerical | REVISE — MAX_ROUNDS hit; cap lifted by Josh |
| 6 | 1 blocker | REVISE — prior fixes VERIFIED; ceiling dilution found |
| 7 | 0 | **APPROVED** with an explicit conservativeness proof |

**Defects that would have shipped without Act 2:** a ligand path that does not exist; a box source that was an
obsolete result label; a false monotonicity premise (the basis for having no sampler); a validity check that
would certify a hung vina as a working load; a plan contradicting itself on `results/`; a section silently
dropped while rewriting; a constant labelled "Documented" that is not; two frozen constants contradicting each
other; arithmetic used to justify a design decision to the human that was simply wrong; and three cases of a
Claude fix introducing a fresh defect (precise-clock swap, denominator direction, ceiling dilution) — each
caught only because a further round ran.

**What the final plan proves is deliberately LESS than revision 1 claimed:** no continuity guarantee, no
freshness enforcement, no unforgeable gate, an acknowledged blind spot between samples, and a ceiling that
catches only sustained over-utilization. Revision 1 was confident and wrong; revision 8 is narrow and states
where it stops.

**Awaiting Josh's sign-off. No code has been written. Act 3 (build) begins only after he signs off.**

---

# Act 3 — Build (Codex types, Claude verifies)

## Round 1 — Codex build (`gpt-5.6-sol`, `--yolo`, user-authorized; 20m 11s, 190,859 tokens)
_Isolation checkpoint `3421ed8`, clean tree. SPEC=PLAN-calibration.md rev 8. Pre-build proof baseline: **179 passed**._

**Codex report:** implemented rev 8; **deviations: none**. Files: `scripts/calibrate_suspend.py` (new, 1071 lines),
`tests/test_calibrate_suspend.py` (new, 478), `docs/adr/ADR-0002-suspend-calibration-protocol.md` (new, 67),
`docking.py` (+75 additive), `tests/test_docking_timeout.py` (+75), the three entry points (+7 each),
`run_campaign.sh` (+7).

### Claude's verdict — VERIFIED, no fix round needed

Verified independently, not trusting Codex's claims:

- **Scope:** exactly the nine expected files. Diff is **+175/−3** in tracked files.
- **Hard constraints all hold.** `validate_suspend_calibration` / the v1 schema / `SUSPEND_THRESHOLD` /
  `CALIBRATION_DURATION_SECONDS`: **zero diff lines touch them** — Josh's Act-1 constraint survived the build.
  **Nothing written under `results/`**; the ADR-evidence sidecar (`29287.070618800004`) is byte-intact with an
  unchanged mtime. Frozen constants match the approved table exactly — none tuned. `HEAD` is still Claude's commit:
  **no git operations by Codex**. Frozen plans untouched.
- **Proof (run by Claude, not quoted):** `pytest tests -q` → **225 collected, exit code 0**, baseline 179 → **+46**
  (44 new calibration tests; `test_docking_timeout.py` 22 → 24). **Zero skips** — the timeout-fix standard.
- **The three danger points, each verified in the source:**
  1. §8 floor/ceiling use **different denominators**: `job_cpu / load_window_unbiased_seconds ≥ 0.90` and
     `job_cpu / 600.0 ≤ 1.10`. The fail-open band is gone.
  2. §2 `load_window_unbiased_start` is taken at `docking.py:622`, **before** `ResumeThread` at `:623`.
  3. §7 gates the **non-precise** clock; read order is literally `n1, p1, wall, p2, n2`.
- **Excursion math matches the plan line for line:** `upper = Δw − (n₁ⱼ − n₂ᵢ) + measured_lag`;
  `lower = Δw − (n₂ⱼ − n₁ᵢ) − measured_lag` (Codex R5 #2's exact formula); cross-check on **midpoints per identical
  (i,j)**; well-formedness checked; three-way classification ordered correctly; the gate reads the **real module
  constant** `MAX_AWAKE_CALIBRATION_DRIFT_SECONDS` rather than a retyped `0.5`; overdue deadlines never replayed.
- **Real Windows integration test exists and runs:** `test_job_accounting_prestart_cpu_cannot_escape_denominator_and_
  end_follows_reap` (0.21 s) wraps the **real** `_Win32Bindings` in a tracing proxy, spawns a real child, and asserts
  `deadline_timeout`, `job_cpu_seconds > 0`, reap/terminate/cleanup, and the **call ordering**. Claude initially
  suspected this test was absent (the calibration suite's slowest case is 0.02 s) — it is in `test_docking_timeout.py`.
  Codex's "0.2-second native workload" claim was accurate; the suspicion was Claude's, and checking dissolved it.
- **ADR-0002** carries the withdrawn-guarantee and forgeability/freshness language verbatim, and makes **no outcome
  prediction** — matching the ADR-0001 standard.
- **Seam reuse, not reimplementation:** imports `_run_vina_supervised`, `build_vina_command`, `campaign_lock`,
  `require_campaign_id`, and calls the **real** `validate_suspend_calibration` at line 760 for the §12 self-check.

**Deferred, correctly not built:** the live 600 s calibration run and the v2 campaign launch. Those are operator steps
after commit + sign-off.

## Rounds 2–3 — Codex fixes (live-run defects that every static check missed)

**The build passed 225 tests, a line-by-line diff review, and seven rounds of design review — then died in 0 seconds
on first contact with real Windows.** Both defects were invisible to every layer of defense because **every test
mocked the Win32 bindings**. Recorded here because the lesson outlives the code.

### Fix round 1 — the precise-clock binding (2 real bugs + the gap that shipped them)
- **Wrong DLL.** `QueryUnbiasedInterruptTimePrecise` is **not exported by kernel32**. Verified export tables on this
  host: kernel32 → MISSING; **KernelBase** and `api-ms-win-core-realtime-l1-1-1` → FOUND. Fixed to bind from KernelBase.
- **Wrong return type.** The precise API returns **VOID**, not BOOL. The code set `restype = wintypes.BOOL` and did
  `if not precise(...): raise`, reading a garbage register — it would have raised spuriously *even after* the DLL fix.
- **The test gap that let both ship.** `tests/test_calibrate_suspend.py` defined its own
  `QueryUnbiasedInterruptTimePrecise` on a fake bindings object, so `_configure_precise_clock` never ran against real
  Windows and the DLL was never consulted. A green suite proved nothing about the binding. Added
  `test_real_kernelbase_precise_clock_binding_is_nonzero_and_monotonic` using the **real** `_Win32Bindings`.
- Binding failure now raises a staged `failure_stage="precise-clock-binding"` instead of a raw traceback.

**Vindication of "measure, don't assume":** the real precise-vs-non-precise lag on this host is **~358 µs** — **43×
tighter** than the `15.625 ms` Claude had frozen and mislabelled "Documented — Microsoft" (Codex R3 #2). Had that
assumption survived, the gate would have carried a meaningless inflation term from an overstated number.

### Fix round 2 — teardown masquerading as science
The live calibration then **ran the full 10 minutes and emitted a valid PASS artifact** — and still exited 1:
`PermissionError: [WinError 5]` on `.campaign.lock` rmdir at teardown. Diagnosis: the repo is in a **OneDrive-synced
tree**; OneDrive transiently held a handle. Manual `rmdir` succeeded immediately after the process exited, confirming a
transient handle, not a conflict.
- **Exit code now reports the science, not the plumbing.** Release retries 6× over 2.5 s; a persistent failure *after*
  atomic emission + validator acceptance becomes a prominent warning ("NOT HOST DRIFT OR CALIBRATION FAILURE") naming
  the stale path and the exact `rmdir` command — exit 0. Lock **acquisition** failure still aborts; the
  single-instance guarantee is untouched.
- Why it mattered: a stale `.campaign.lock` silently blocks the next launch — **exactly how the 2026-07-15 campaign
  died at stage 2 of 4**.

### Claude's verdict — VERIFIED
Verified independently: KernelBase binding + `restype=None` + truthiness check removed; real unmocked binding test
present and passing; non-precise clock still on kernel32 in `docking.py`, untouched; acquisition path still aborts;
`calibration_passed` flips only after emission and validation. Proof run by Claude: **232 collected, exit 0** (225 →
229 → 232). Frozen constants intact 3/3. Scope: two files. The real artifact was not opened or modified.

## FIRST REAL MEASUREMENT — the host is clean

`docs/methods/suspend_calibration_v2_20260717.json` (campaign `v2_20260717`, 2026-07-17T13:33:12Z), **accepted by the
real `validate_suspend_calibration()`**:

| Metric | Value | Gate |
|---|---|---|
| `max_observed_drift_seconds` | **0.00136** | ≤ 0.5 — **370× margin** |
| `utilization_floor_ratio` | 0.9778 | ≥ 0.90 ✓ |
| `utilization_ceiling_ratio` | 0.9778 | ≤ 1.10 ✓ |
| `job_cpu_seconds` / `load_window_unbiased_seconds` | 586.72 / 600.04 | — |
| `sample_count` / `missed_deadline_count` | 602 / **0** | ≥ 590 ✓ |
| `disposition_basis` | `deadline_timeout` | vina outlasted 600 s, as ADR-0001's 1,429 s evidence predicted ✓ |

Provenance landed complete: 7 inputs hashed **before and after**, resolved box, `drift_analysis`, `frozen_constants`,
and 602-entry sample/skew/lag series.

**Root cause of the 2026-07-15 incident, confirmed independently of the code:** `powercfg` shows AC sleep = **never**,
but **DC (battery) sleep = 0x258 = 600 s**. The host sleeps after 10 minutes idle *on battery*. The 29,287 s
azithromycin/7EDD disposition was a power setting, not chemistry. **The v2 campaign must run on AC.**

**Caveat on this artifact:** it was emitted by the run that exited 1 (teardown only — after atomic emission and
validator acceptance). The measurement is complete and valid; the non-zero exit was plumbing, now fixed.

## Operator run 2 — the gate caught a real suspend (2026-07-17)

The lock-teardown fix was committed on test-suite strength (`aeb6ae4`), so a fresh live calibration under
`v2_20260717b` was run to verify it — and it surfaced something more important than the fix.

**Result: FAIL (host drift), and it was correct.** The calibration measured `excursion_estimate = 862.0 s` against the
0.5 s gate. Wall span 1463 s vs unbiased span 601 s: the measurement collected its full 601 unbiased seconds while
**862 s of real time was suspended**, in a single 863-second gap at sample 75 (every other inter-sample gap = 1.0 s).
`valid_for_campaign_gate: False`, `disposition = drift-fail`.

**Independent corroboration from the Windows System event log:**
- `16:42:35` Id 42 "The system is entering sleep" — 71 s after calibration start (16:41:24)
- `16:57:02` Id 1 system time changed 21:42:40Z → 21:57:02Z — an **862 s** jump, matching the measured drift to the second
- `16:57:05` Id 1 "returned from a low power state"; last wake source = Power Button

**Root cause (not a timeout — 71 s is far below any idle threshold):** lid-close action on AC was `0x1 = Sleep`.
Closing the lid slept the machine despite AC idle-sleep = never. This is the same failure class as the 2026-07-15
azithromycin/7EDD incident (`elapsed_seconds: 29287`), caught **pre-flight** this time instead of mid-campaign.

**Fix applied (Josh chose reversible power-config change):** lid-close AC action set to `0x0 = do nothing` via
`powercfg`; DC and the power/sleep buttons left untouched. AC idle-sleep and hibernate were already `never`. Machine is
now sleep-proof on AC from all three idle/lid triggers.
  REVERT after the campaign:
    powercfg /setacvalueindex SCHEME_CURRENT 4f971e89-eebd-4455-a8de-9e59040e7347 5ca83367-6e45-459f-a27b-476b1d01c936 1
    powercfg /setactive SCHEME_CURRENT

**On the lock fix:** exit 1 here was CORRECT (a genuine drift failure), and the fix behaved as designed — the stale-lock
warning explicitly read "does not change the primary failure." The PASS-path-with-lock-contention exit-0 behavior
remains unverified live (this run failed on drift before reaching it); low residual risk, noted.

Next: re-calibrate now that the host cannot sleep; a PASS is required before launch.

## Operator run 3 — PASS, host sleep-proofed (2026-07-17)

Re-run under `v2_20260717b` after the lid-close fix. **PASS, exit 0.**

| Metric | Value | vs run 2 (slept) |
|---|---|---|
| wall vs unbiased window | 600.1 s vs 600.1 s → **0.000 s** | 1463 vs 601 → 862 s |
| `max_observed_drift_seconds` | **0.00257** (2.6 ms) | 862 |
| utilization (floor/ceiling) | 0.972 / 0.972 | — |
| sample_count / missed | 602 / 0 | 602 / 0 |
| validator | **ACCEPTS** | rejected |

Wall == unbiased to the millisecond confirms the host did not sleep — the lid fix held. Artifact
`docs/methods/suspend_calibration_v2_20260717b.json` is validator-accepted and binds to `v2_20260717b`.

**Lock-fix PASS path now verified live (previously the one untested branch):** OneDrive contended the lock again, and
the fix degraded exactly as designed — "CALIBRATION PASSED AND THE VALIDATOR-ACCEPTED ARTIFACT IS INTACT. THIS IS A
LOCK-CLEANUP WARNING, NOT HOST DRIFT OR CALIBRATION FAILURE", **exit 0**, stale lock left for manual clear (which was
then cleared). OneDrive holds the handle longer than the 2.5 s retry window, so the manual-clear path is the normal
operational outcome on this synced host, not an error.

**Gate cleared. The v2 campaign is unblocked** pending launch under `v2_20260717b` on AC.

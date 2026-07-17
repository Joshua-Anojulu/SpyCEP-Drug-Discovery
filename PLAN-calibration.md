# Plan: Pre-campaign suspend-calibration harness
_Locked via grill-with-docs — by Claude + Josh, 2026-07-17. Terms per `PROJECT_CONTEXT.md` / `docs/adr/ADR-0001`._
_Isolation checkpoint: HEAD = `300bbdc`. Working tree carries one prior modification: `run_campaign.sh`._
_**Revision 8 — APPROVED** by Codex round 7 (2026-07-17). Rounds 1–6 preceding. R3: "the design is beginning to fight the problem" → Josh chose the
simplified design. R4 found 2 blockers, both Claude's: a false stall-guarantee arithmetic, and calibrating a clock the
campaign does not use. Both fixed here; Josh withdrew the guarantee and set the floor to 0.90 on 2026-07-17.
See `PLAN-REVIEW-LOG-calibration.md`._

## Why this exists (the link to the science)

SpyCEP's headline claims — the Mann–Whitney population, top-ranked candidates, the SpeB positive control, the
67/53/31 catalytic-triad ranges — rest on which compounds got `valid_fit` versus `timeout`. On 2026-07-15 the host
slept mid-campaign and azithromycin/7EDD recorded `elapsed_seconds: 29287`, serialized as a scientific `no_fit`/
`timeout`: **a compound classified as non-binding because the machine was asleep, not because of chemistry.** The
schema-v2 fix makes the ceiling sleep-excluding. This calibration proves the clock that fix depends on is trustworthy
on *this host* before ~10–15 h of publishable compute. Its purpose is to keep "azithromycin does not inhibit SpyCEP" a
statement about a molecule rather than about a power setting.

## Frozen measurement-validity constants (approved by Josh 2026-07-17, **before any calibration data existed**)

| Constant | Value | Basis |
|---|---|---|
| `CPU_UTILIZATION_FLOOR` | `0.90` core-s/s (mean) | Judgment — **mean-load evidence only.** See the withdrawn guarantee below. |
| `CPU_UTILIZATION_CEILING` | `1.10` core-s/s (mean) | Judgment — `--cpu 1` must not exceed one core. **Narrowed claim:** catches *sustained* over-utilization only (Codex R3 #7); a brief two-core excursion can average under. |
| `SAMPLE_CADENCE_SECONDS` | `1.0` | Judgment — absolute deadlines |
| `MAX_INTERSAMPLE_GAP_SECONDS` | `5.0`, **on the unbiased (awake) basis** | Judgment — sampler health. Unbiased basis because QPC includes sleep, so wall gaps are expected after a suspend (Codex R3 #10) |
| `MIN_SAMPLE_COUNT` | `590` | Judgment (~98% of ~600 at 1 Hz) |
| `NEGATIVE_EXCURSION_TOLERANCE_SECONDS` | `0.5` | Symmetric with the approved drift gate. Fail-closed: monotonic **negative** divergence can *shrink* a real suspend gap and cause a false negative during the campaign (Codex R4) |

**The lag allowance is measured, not frozen** — §6 derives it from the host at run time and records it. That is
deliberate: the one constant Claude assumed and mislabelled is the one that broke.

> ### ⚠️ Withdrawn: the contiguous-stall guarantee
> Rev-4 claimed `mean ≥ 0.95 ⟹ no contiguous stall > 30 s`. **This is false** (Codex R4 #1). The inference requires an
> **instantaneous** one-core cap; only the *mean* is bounded, so a burst above one core pays for a stall:
> 60 s idle + 540 s at 1.056 cores = 570 core-s / 600 s = **0.95, passes**. The bound is also duration-dependent (a
> 620 s window permits 31 s idle at 0.95). Claude used this false arithmetic to argue for the simplified design; the
> correction was put to Josh, who withdrew the guarantee and set the floor to **0.90** — since the floor now only
> evidences that the load was real, and 0.90 does that while remaining achievable on a working host.
>
> **The honest claim, to appear in ADR-0002 verbatim:** *the calibration ran under a mean load of ≥ 0.90 cores over the
> window. This is evidence the load was real. It does **not** prove the load was continuous; a localized stall
> compensated by a multi-core burst could pass.*

**Retired rather than re-approved** (each dissolved by a design change, not a new number):
- `TICK_UNCERTAINTY_SECONDS = 0.015625` — **withdrawn.** Claude labelled it "Documented — Microsoft"; Codex R3 #2
  correctly showed Microsoft documents 0.5–15.625 ms as a **typical range**, not a contractual one-sided bound. It was
  a judgment call wearing a citation's clothing. §6 now **measures** the host's lag with
  `QueryUnbiasedInterruptTimePrecise` instead of assuming a bound.
- `INSTRUMENT_SKEW_LIMIT_SECONDS = 0.250` — **withdrawn.** Codex R3 #6: against a 0.5 s gate, two *in-limit* brackets
  could fail a zero-drift run. Replaced by the three-way classification in §7, which can never blame the host for the
  instrument's uncertainty.
- `MAX_LOW_UTIL_INTERVAL_SECONDS = 30.0` and the embedded `0.50` threshold — **withdrawn.** They were replaced by an
  arithmetic claim that Codex R4 #1 then proved **false** (see the withdrawn-guarantee box below), so the guarantee is
  gone outright rather than relocated. The entire CPU-series subsystem — and a second thread inside the scientific
  supervisor — existed only to serve them.

**Authorship, recorded honestly:** every *Judgment* value is Claude's, carrying Josh's approval, frozen prospectively
with no calibration data in existence. R4 #4 is satisfied by that freezing — a threshold is never *raised* after a bad
measurement. If a reviewer asks why the floor is 0.90, the honest answer is "chosen prospectively on reasoning, not
measurement." **No value here may be tuned after seeing a result.** A failing calibration is investigated; it is never
answered by moving a number.

## Approach

1. **Files:** new `scripts/calibrate_suspend.py`, new `tests/test_calibrate_suspend.py`;
   **new `docs/adr/ADR-0002-suspend-calibration-protocol.md`** — the plan promises ADR-0002 twice (the withdrawn
   stall guarantee and the forgeability/freshness limits must be recorded there); rev-6 promised it without ever
   declaring it in scope _(Codex R6)_. It is now an in-scope deliverable, not a promise; **additive edit** to
   `_run_vina_supervised()` / `SupervisedResult` (§2); additive cases in `tests/test_docking_timeout.py`;
   campaign-binding in the three entry points (§10); early-diagnostic check in `run_campaign.sh` (§10).
   **`validate_suspend_calibration` and the v1 schema remain untouched** — Josh's Act-1 constraint holds throughout.

2. **Supervisor edit — aggregate only, no internal thread.** _(Codex R3 #3/#8; back to the scope Josh originally
   approved.)_ The main thread is blocked in the single armed `WaitForSingleObject`; sampling accounting "on a cadence"
   would require chunking that wait — which ADR-0001 expressly rejects — or a second thread inside the scientific
   supervisor. Neither is acceptable. Instead, **once**, while the Job handle is still live, query
   `QueryInformationJobObject` → `JOBOBJECT_BASIC_ACCOUNTING_INFORMATION` (`TotalUserTime + TotalKernelTime`, 100 ns)
   and return on `SupervisedResult`:
   - `job_cpu_seconds` — cumulative numerator; correctly includes the terminated process.
   - `load_window_unbiased_seconds` — the denominator: a **bracketed (enclosing) measure**, not an exact one. Rev-4
     said "exactly from successful `ResumeThread` to kernel wait return"; that interval is **not literally obtainable**
     without inserting clock calls inside it, so "exactly" overstated the instrument _(Codex R4)_.
   - **The denominator must conservatively enclose every possible numerator interval** _(Codex R5 #1 — rev-5 got this
     backwards)_. Job accounting is cumulative over the process's entire execution, so:
     - **Start timestamp: immediately BEFORE `ResumeThread`**, not after. Rev-5 timestamped *after*, which lets the
       child accrue Job CPU while the supervisor is descheduled before the read — inflating utilization past the floor
       with time the denominator never counted.
     - **End: after the deadline, terminate and reap, query Job accounting while the handle is still live, then take
       the end timestamp.** Numerator ⊆ denominator by construction, so utilization can only be under-stated — the
       fail-closed direction against a floor.
     - This supersedes rev-5's contradictory mentions of "after wait returns" / "post-termination endpoint" /
       "resume-to-deadline", which Codex correctly flagged as three different answers to one question.
   - Accounting is **opt-in and default-disabled**, so an ordinary campaign call's **runtime control flow** is
     unaffected. It is **not** "byte-for-byte unaffected" _(Codex R4)_: editing `docking.py` intentionally changes
     `supervisor_source_sha256()`, and therefore every provenance fingerprint downstream. That change is deliberate and
     is recorded, not hidden.

3. **Entry gates and load construction** _(restored — Codex R3 #11 caught that rev-3 dropped these when Claude rewrote
   rather than edited)._
   - `require_campaign_id()`; assert Windows; refuse if the target artifact exists.
   - Acquire **both** locks in the launcher's order: `.campaign.lock` (repo root) then
     `results/docking/.docking-campaign.lock` via `campaign_lock()` — they are genuinely different locks
     _(Codex R2 #13)_. Hold both for the whole calibration.
   - Assert `results/docking/campaign_<id>/` does not exist, **and re-check immediately before emission** — the
     launcher refuses to start if that root pre-exists.
   - Resolve the load from the **unique** validated attempt-manifest row (`workflow="wide"`, azithromycin, `state_01`,
     `spycep_5xya_aes_active_site`); **abort on zero or multiple matches**. Take `receptor_pdbqt_path`,
     `box_center_angstrom`, `box_size_angstrom`, `pocket_id`, `pdb_id` from that row — the seam `run_docking.py:157`
     actually uses. Ligand resolves to `azithromycin__state_01.pdbqt` from the row key. _(Codex R1 #7/#8.)_
   - Build argv **only** via `build_vina_command()` with frozen params (`seed=42`, `exhaustiveness=8`, `num_modes=9`,
     `cpu=1`); `out_path` inside `tempfile.mkdtemp()`, removed in `finally`. **Poses are load-generation, never a
     scientific record.**
   - Call exactly `_run_vina_supervised(cmd, timeout_seconds=600.0, cwd=PROJECT_ROOT, temp_dir=<tmp>)`.

4. **Seven inputs, hashed before and after, equality required.** _(Codex R1 #9, R2 #11.)_ Calibrator script,
   `docking.py` (public `supervisor_source_sha256()`), `vina.exe`, receptor pdbqt, ligand pdbqt, attempt manifest, and
   `docs/methods/species_audit.json` — `validate_attempt_manifest(manifest, species_catalog)`
   (`attempt_manifest.py:129`) requires the catalog, so it is a real input. The repo lives in a **OneDrive-synced
   tree**: the 10-minute mutation race is real. Persist both hash sets and the resolved box.

5. **One external sampler thread.** Started before `_run_vina_supervised`, it takes and **persists its baseline and
   signals ready before the main thread may enter the supervisor** _(Codex R3 #9)_. Absolute deadlines
   (`t₀ + i·SAMPLE_CADENCE_SECONDS`), never cumulative sleep. **Missed deadlines are skipped, never backfilled** —
   QPC includes sleep, so many deadlines fall due at once on resume and backfilling could falsely satisfy
   `MIN_SAMPLE_COUNT` _(Codex R3 #10)_. A **mandatory terminal sample** is taken after the supervisor returns. If the
   sampler raises or exits early, the run is invalid.

6. **Each sample — five reads, gating the clock the campaign actually uses.** _(Codex R4 #2 — this fixes a blocker
   Claude introduced while fixing an earlier one.)_
   Rev-4 gated the **precise** counter. That escaped the mislabelled tick constant but calibrated a clock the campaign
   **never touches**: `require_suspend_calibration`'s downstream suspend detection runs on the **non-precise**
   `QueryUnbiasedInterruptTime`. Recording their lag cannot stop a non-precise anomaly from passing calibration and
   corrupting campaign dispositions. So the **non-precise clock is the gated one**; precise is the cross-check.
   - **Read order per sample:** `n₁ᵢ = QUIT()`, `p₁ᵢ = QUIT_Precise()`, `wᵢ = perf_counter()`,
     `p₂ᵢ = QUIT_Precise()`, `n₂ᵢ = QUIT()`. Rev-4's `pᵢ − nᵢ` compared readings taken at **different instants**
     _(Codex R4 #2)_; the lag is now itself bracketed.
   - **Why bracketing alone is insufficient, and what replaces the assumed tick:** two non-precise reads inside one
     clock tick return an *identical* value, so `[n₁ᵢ, n₂ᵢ]` collapses to zero width while true time lies anywhere in
     that tick. The campaign clock therefore still needs a lag allowance — but it is **measured, not assumed**:
     `lagᵢ ∈ [p₁ᵢ − n₂ᵢ, p₂ᵢ − n₁ᵢ]`, and `MEASURED_LAG = maxᵢ (p₂ᵢ − n₁ᵢ)` over the run, recorded in the artifact.
   - **Well-formedness, checked not assumed** _(Codex R6)_: require `n₁ᵢ ≤ n₂ᵢ`, `p₁ᵢ ≤ p₂ᵢ` and `MEASURED_LAG ≥ 0`.
     Any violation means the clocks are not behaving as the whole design presumes → **INDETERMINATE**, never a pass.
     This is Codex R3 #2's own first option ("validate the actual host's non-precise lag against the precise API"),
     reached via its R4 #2. **No documented-worst-case claim is made anywhere.**

7. **Gate on the maximum observed excursion over every sub-interval — and classify three ways.**
   - **Why not against `t₀`:** once monotonicity is withdrawn, a drift *fall* before the load can mask a *rise* during
     it _(Codex R3 #1)_. Excursion over `[i,j]` is `(wⱼ − wᵢ) − (nⱼ − nᵢ)` — **the origin cancels algebraically**, so
     no `ResumeThread` handshake is needed and every sampled sub-interval is covered.
   - **Primary gate (campaign clock, non-precise):**
     `excursion_upper = maxᵢ<ⱼ (wⱼ − wᵢ) − (n₁ⱼ − n₂ᵢ) + MEASURED_LAG` — conservative: unbiased low at `j`, high at
     `i`, plus the measured lag bound. `excursion_estimate` uses bracket midpoints and no lag term.
   - **Cross-check (precise clock):** the same excursion computed on `p`, compared **per identical `(i,j)` interval**
     — not aggregate extremum against aggregate extremum _(Codex R5 #2)_ — and comparing **midpoint estimates**, not
     conservative bounds _(Codex R6: rev-6 left this unspecified)_. Bounds would be dominated by bracket width and
     would flag nothing; the estimates are what diverge when the clock misbehaves. If any interval's two estimates
     disagree by more than `MEASURED_LAG`, the non-precise clock is **anomalous** → INDETERMINATE. This is what
     actually catches R4 #2's "non-precise anomaly passes calibration".
   - **Negative excursion, fail-closed — with an explicit lower bound** _(Codex R5 #2; rev-5's "`min` of the same
     quantity" was ambiguous between the midpoint estimate and the positive upper bound, and **neither proves negative
     drift is within tolerance**)_:
     `excursion_lowerᵢⱼ = (wⱼ − wᵢ) − (n₂ⱼ − n₁ᵢ) − MEASURED_LAG`
     PASS requires `minᵢ<ⱼ excursion_lowerᵢⱼ ≥ −NEGATIVE_EXCURSION_TOLERANCE_SECONDS`; otherwise INDETERMINATE.
     Without this, a forward non-precise step landing between `n₁` and the wall read can hold the midpoint above −0.5
     while the clock value the campaign actually consumes has moved more than 0.5. Monotonic negative divergence
     *shrinks* a real suspend gap and produces a **false negative** in the campaign — the exact failure mode this
     project exists to prevent.
   - **This is a maximum-*observed* protocol** _(Codex R4)_, stated rather than hidden: a trough occurring **between**
     samples — notably between the ready baseline and `ResumeThread` — is not covered. Bounding that would require an
     opt-in supervisor sample at the resume boundary; it is declared a limitation, not engineered away.
   - O(n²) over ~600 samples is ~180 k operations; a running-minimum form is O(n). Not a cost.
   - **Classification** _(Codex R3 #6 — retires the skew-limit contradiction)_:
     - `excursion_upper ≤ 0.5` **and** cross-check agrees **and** negative excursion within tolerance → **PASS**;
       `max_observed_drift_seconds = max(0.0, excursion_upper)`.
     - `excursion_estimate > 0.5` → **FAIL (host drift)** — investigate; the threshold is **not** raised (R4 #4).
     - otherwise → **INDETERMINATE (measurement)** — never a pass. The instrument's uncertainty is never attributed to
       the host, and never excuses one either.

8. **Validity — evidence the load was real.** _(Codex R1 #3.)_ `disposition_basis == "deadline_timeout"` proves vina
   was **unsignaled**, not **working**; a hung, throttled or descheduled vina is indistinguishable, which is why an
   aggregate is required at all. Early finish (`wait_signaled`) stays **fail-closed**.
   - **Two utilization bounds, two denominators — never one band against one denominator** _(Codex R6: rev-6's own fix created
     this)_. The enclosing denominator is conservative for the **floor** but **fail-open for the ceiling**, because
     cleanup/reap time enlarges the denominator without necessarily adding CPU, diluting the ratio:
     663 core-s over the real 600 s active interval is `1.105` and must fail, yet with 5 s of post-termination
     enclosure `663/605 = 1.096` **passes**. Applying a two-sided band to a one-sided conservative denominator is the
     defect.
     - **Floor:** `job_cpu_seconds / load_window_unbiased_seconds ≥ 0.90` — the enclosing window is the larger
       denominator, so this can only under-state utilization. Fail-closed.
     - **Ceiling:** `job_cpu_seconds / 600.0 ≤ 1.10` — `deadline_timeout` guarantees the process was active for at
       least the nominal armed wait, so dividing by the nominal 600.0 can only over-state utilization. Fail-closed in
       the opposite direction.
   - Also require `load_window_unbiased_seconds ≥ 600.0`.
   **This is mean-load evidence and nothing more.** It does not prove continuity (the stall guarantee is withdrawn —
   see the frozen table), and the ceiling catches only *sustained* over-utilization. Both limits are stated in
   ADR-0002 rather than engineered away.

9. **Concurrency failure order — explicit, not implied.** _(Codex R3 #13.)_ If the sampler fails while the main thread
   waits, the supervisor **still terminates and reaps vina and takes final accounting before any failure propagates**;
   a wedged sampler is joined with a bounded timeout and must never orphan a process or delay cleanup indefinitely.
   Exception precedence: infrastructure failure > measurement invalidity > drift verdict. No path leaves a live vina.

10. **Campaign binding at the entry points.** _(Codex R2 #9; Claude's launcher-only arbitration withdrawn.)_
    `run_campaign.sh` invokes the scripts as `$PY scripts/run_docking.py`, so a launcher check covers one path only.
    Each of the three entry points compares the `campaign_id` in the record **returned by**
    `require_suspend_calibration()` against `require_campaign_id()` and aborts on mismatch — no validator or schema
    change, every executable path bound. The launcher check remains **only as an early diagnostic**. Filename-based
    "is it FAILED" is dropped: no integrity value.
    **Limitation, stated precisely** _(Codex R2 #10, R3)_: this prevents **cross-campaign-ID reuse**. It does **not**
    detect an old artifact with a *matching* ID produced before a host, OS, supervisor, vina or input change. Hashes
    are recorded but not enforced. This is **not freshness enforcement**, and the plan does not claim it is.

11. **Assemble the record.** `duration_seconds` = literal `600.0`, explicitly the **nominal requested wait**, never the
    observed interval (the validator rejects anything ≠ `CALIBRATION_DURATION_SECONDS`, so an honest `600.3` would fail
    the gate). Add `sampling_window_unbiased_seconds` / `sampling_window_wall_seconds` and
    `load_window_unbiased_seconds`. `calibration_schema_version` / `load` are **local literals** — `docking.py` exposes
    no public constants for them (inline strings at `:1780`/`:1784`) — asserted against the **real** validator in
    tests. `suspend_threshold_seconds` and numeric bounds read from the real module constants, which do exist.
    Provenance: `measured_at_utc`, `hostname`, `os_build`, `campaign_id`, both hash sets, resolved box, `load_command`,
    `disposition_basis`, `job_cpu_seconds`, **both utilization values recorded explicitly** (`utilization_floor_ratio` = C/O and `utilization_ceiling_ratio` = C/600, never a singular "utilization"), sample series, skew series, **precise-vs-non-precise lag
    series**, and every frozen constant used.

12. **Self-check through the real gate.** Call `validate_suspend_calibration(record)` on the assembled record — single
    source of truth; the instrument cannot drift from the gate it feeds.

13. **Emit — atomic, with staged failure records.** _(Codex R2 #10/#12, R3 #12.)_ Unique temp file + **atomic
    no-replace rename** (`O_EXCL`); check-then-replace is a TOCTOU race.
    - **PASS** → `docs/methods/suspend_calibration_<campaign_id>.json`, exit 0, print the launch line.
    - **Any other outcome** → a failure artifact carrying an explicit **`failure_stage`**, uniquely named, and
      **deliberately invalid under `docking-suspend-calibration-v1`** so the validator can never accept it even when
      drift is small. Evidence is **staged and honestly nullable**: a failure at input-hashing or lock contention
      cannot carry samples that do not exist yet, so required-evidence-by-stage is declared rather than promising
      artifacts the code cannot produce. Stages: input-resolution, pre-hash, lock, sampler-start, supervisor-infra,
      early-finish, utilization, measurement-indeterminate, drift-fail, hash-mutation, campaign-root-recheck,
      emission. Exit non-zero; print that the threshold is **not** to be raised (R4 #4).

14. **Tests** (new file; additive cases in `tests/test_docking_timeout.py` for §2). Deterministic:
    **negative pre-load drift followed by a load-window rise** (the sub-interval excursion — the case a `t₀` baseline
    misses); a **late-window peak**; the exact `excursion_upper` arithmetic; **three-way classification** including an
    upper-bound-only crossing landing on INDETERMINATE, never PASS or host-FAIL; sampler start race (ready-handshake);
    sampler death mid-wait leaving **no orphan vina**; missing terminal sample; **post-sleep deadline backfill is
    rejected**; excessive unbiased gap; short coverage; stalled-but-unsignaled vina; a **0.89 mean** failing the 0.90
    floor; **sustained** multi-core over-utilization; **a forward non-precise step inside the five-read bracket**
    (Codex R5 #2); denominator **encloses** the numerator — pre-`ResumeThread` start, post-reap end — and a test that
    CPU accrued before the start timestamp cannot inflate utilization;
    **accounting disabled for ordinary campaign calls**; attempt-row zero/multiple match; species-catalog mutation;
    input mutation; concurrent writers; **direct-entry campaign_id mismatch**; local literals vs the real validator;
    every failure artifact invalid under v1; non-Windows raises. Plus a **short** Windows integration test asserting
    real Job accounting, timeout, termination and cleanup — **without** the 600 s run.

15. **Preserve the ADR evidence.** `results/docking/library_stage2_CONTAMINATED_SLEEP_2026-07-15/` holds the **sole
    copy** of the `elapsed_seconds: 29287.070618800004` sidecar cited in ADR-0001 line 12 and `PLAN-timeout-fix.md:10`.
    Gitignored; exists nowhere else. **Must not be deleted.**

16. **`results/` scope.** _(Codex R2 #14.)_ Holding `campaign_lock()` necessarily creates and removes
    `results/docking/.docking-campaign.lock`. That **transient lock file is the sole permitted `results/` write**; no
    persistent artifact is created there, and no existing file — including every archive — is read, modified or removed.

## Key decisions & tradeoffs

- **Simplified on Codex's own recommendation** ("the design is beginning to fight the problem"). Deleted: the internal
  supervisor sampler thread, the CPU series, three cadence/threshold constants, and an assumed tick bound.
- **The stall guarantee is gone, not relocated.** Claude first justified the simplification with arithmetic that was
  **wrong** (see the frozen table). The honest outcome is a simpler instrument that proves *less* and says so, rather
  than a complex one that proves more. Josh took that trade knowingly.
- **Calibrate the clock the campaign consumes, not the nicer one.** Rev-4 gated the precise counter because it was
  mathematically convenient; the campaign runs on the non-precise counter. Convenience is not a reason to measure the
  wrong thing.
- **Real vina, not a synthetic loop** — "docking-equivalent" demonstrated, and now *enforced* by the utilization band.
- **azithromycin/5XYA runtime is provisional evidence, not a guarantee** _(Codex R1 #6)_ — one observation under a
  different execution path. Mitigated by fail-closed early-finish abort plus the utilization band.
- **The gate remains forgeable.** §10 binds every executable path to the campaign id, killing cross-ID reuse. It does
  **not** stop a hand-written artifact, nor a stale same-ID one after a host change. Stated, not claimed away.
- **Measure, don't assume.** The tick bound is the clearest lesson of this review: an assumed constant labelled
  "documented" became a load-bearing premise. It is now measured on the host and recorded as evidence.

## Risks / open questions

- **A 0.90 floor may still prove unachievable on a busy host.** If so the correct response is to quiet the host and
  re-run, or seek a signed amendment — **never** to lower the floor. A failing calibration may mean "close the
  browser", not "bad clock", and the failure artifact carries the utilization needed to tell those apart.
- **The maximum-observed protocol cannot see between samples** — notably between the sampler's ready baseline and
  `ResumeThread`. Declared, not closed.
- **Sampler perturbation:** a 1 Hz thread is negligible against a saturated core, but it is a moving part in the
  instrument that gates everything. Bracketed reads bound the skew rather than assume it away.
- **Sub-threshold suspends remain undetected but bounded** — inherited from ADR-0001, not introduced here.
- **A pass attests the host was drift-free during *that* 10 minutes**, not across the following ~10–15 h. Inherent to
  any pre-flight; the per-attempt `suspend_gap_seconds` quarantine covers the campaign itself.
- **`_run_vina_supervised` is private.** Deliberate reuse plus an additive, default-disabled edit.

## Out of scope

- Changing frozen params (1800 s, seed 42, exh 8, num_modes 9, cpu 1), receptors, or boxes.
- Editing `PLAN.md` / `PLAN-REVIEW-LOG.md` / `PLAN-timeout-fix.md` (frozen), or the v1 schema and its validator.
- Making the calibration gate unforgeable, or enforcing freshness — both out of reach under the approved provenance
  decision; recorded as limitations.
- Running the campaign or recomputing headlines (§H18). This plan ends when a passing artifact exists.
- Any `results/` write beyond the transient lock in §16.

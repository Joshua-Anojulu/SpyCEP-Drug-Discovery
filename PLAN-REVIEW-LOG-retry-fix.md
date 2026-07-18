# Plan Review Log: Tolerate transient vina process-spawn failures

Act 1 (grill-with-docs) complete — plan locked at `PLAN-calibration.md`'s sibling `PLAN-retry-fix.md`.
MAX_ROUNDS=5. Non-default files (the frozen PLAN.md / PLAN-timeout-fix.md / PLAN-calibration.md and their logs are
untouched). Domain doc: PROJECT_CONTEXT.md.
Isolation checkpoint: HEAD `552a481`, tree clean.

## Act 1 — decisions locked (Claude ↔ Josh, 2026-07-18)

| # | Question | Decision |
|---|----------|----------|
| 1 | Retries exhausted → skip or abort? | **Retry, then fail-closed abort. Never silently skip a compound.** Completeness + integrity. |
| 2 | What counts as a transient (retryable) failure? | **Triple signal:** OS-level NTSTATUS (exit ≥ 0xC0000000) AND empty stdout+stderr AND near-instant (unbiased < 1 s). Conservative; only "never started" retries. |
| 3 | Per-campaign guard? | **Yes** — per-attempt (3 retries, backoff 2/5/10 s) + per-campaign budget (~10 distinct attempts) via a ledger; abort if exceeded (degrading-host signal). |
| 4 | Provenance | **Resolved from code:** record `spawn_failures`/`spawn_retry_count` in run.json; NOT in the fingerprint (scientific-inputs-only), so a retried success == a clean success by fingerprint. |
| 5 | Determinism | **Resolved from code:** retry re-invokes with same seed/box/ligand/cpu → bit-identical scientific intent. |
| 6 | Root-cause vs tolerate | **Tolerate now (retry); root-cause (desktop-heap/reboot) only if it recurs.** Limitation stated in ADR-0003. |

### Resolved by reading code (not asked)
- **All 3 entry points (WIDE/TIGHT via run_docking.py, SPEB, BORON) call `dock_ligand`** — the retry there auto-covers
  every stage.
- **A retry loop ALREADY EXISTS** in `dock_ligand` (docking.py:1096, `MAX_SUSPENDED_RETRIES`) for *suspend* retries,
  with `status="retrying"`/`halted_quarantine_limit` and selection handling. The fix EXTENDS it rather than adding a
  parallel mechanism.
- **The sildenafil case is a returned result, not a supervisor exception.** CreateProcessW succeeded; vina died at
  loader init; the supervisor returned `wait_signaled` + exit `0xC0000142`. So it fell through to `vina_exit_nonzero`
  (docking.py:1194), NOT the infrastructure_failure exception path (1112). The fix intercepts before 1194.
- **The riskiest change is the `for`→`while` restructure** (two independent retry budgets) touching frozen
  timeout-fix code — flagged as the primary target for Act 2.

---

## Round 1 — Codex (`gpt-5.6-sol`, read-only, thread `019f7551-50eb-7f41-b10d-9cbeef5722c4`)

The plan is not safe to implement as written. It contains two concrete correctness bugs and does not meet its “never retry a genuine Vina failure” claim.

1. **CRITICAL — The NTSTATUS range is not a process-startup classifier.** The test in [PLAN-retry-fix.md:37](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PLAN-retry-fix.md:37) accepts every error-severity NTSTATUS. `GetExitCodeProcess` can return an application exit value, a termination value, or an unhandled-exception value—not its provenance. Thus an immediate Vina access violation (`0xC0000005`), Ctrl-C (`0xC000013A`), stack corruption, or other application crash can have empty buffered output and finish within one second, satisfying all three signals. Microsoft explicitly identifies `0xC0000005` as access violation, `0xC000013A` as Ctrl-C, and `0xC0000142` as DLL initialization failure. [GetExitCodeProcess](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-getexitcodeprocess), [NTSTATUS definitions](https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-erref/596a1078-e883-4972-9bbc-49e60bebca55)

Fix — Replace the severity range with a documented pre-entrypoint loader-status allowlist—initially only the observed `0xC0000142`—and withdraw the claim of proof unless a launch-phase handshake/debug event can distinguish pre-main failure.

2. **HIGH — The three signals are not necessary for a real transient.** DLL initialization can exceed one second under severe resource pressure or emit a diagnostic, while `CreateProcessW` can fail before producing a `SupervisedResult`; all would abort. That is fail-closed, but the claimed general transient resilience is overstated.

Fix — Scope the feature explicitly to the exact observed silent `STATUS_DLL_INIT_FAILED` signature and keep slow/noisy/ambiguous startup failures fatal.

3. **CRITICAL — The retry pseudocode crashes on exhaustion.** [PLAN-retry-fix.md:56](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PLAN-retry-fix.md:56) indexes `backoff[spawn_retries]` before checking exhaustion. After three retries, the fourth failed execution evaluates `backoff[3]` against a three-element tuple and raises `IndexError`, never producing the promised infrastructure record or selection manifest.

Fix — On each transient failure, first abort if `spawn_retries >= MAX_TRANSIENT_SPAWN_RETRIES`; otherwise sleep at that index, increment once, and retry.

4. **CRITICAL — Exact suspend semantics are not specified or proved.** The current boundary is precise: the third quarantined execution halts because `retry_index == MAX_SUSPENDED_RETRIES` in [docking.py:1241](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/src/spycep_drug_discovery/docking.py:1241). The plan never defines when `suspended_retries` increments or whether the comparison is `==`, `>=`, or `>`. Worse, a result can simultaneously have an empty fast NTSTATUS and a raw-wall suspend gap; taking the spawn branch first bypasses ADR-0001’s requirement that every suspension-touched execution be quarantined. Incrementing both counters would instead double-charge one execution. A missed increment creates an infinite loop. ADR-0001 also requires a unique immutable attempt directory for every execution. [ADR-0001:20](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/docs/adr/ADR-0001-timeout-unbiased-wall-basis.md:20)

Fix — Give quarantine precedence, define every `continue` as incrementing exactly one bounded counter, preserve `mkdir(exist_ok=False)` after a fresh UUID on every execution, and assert a hard maximum of `1 + 2 + 3 = 6` supervisor calls in interleaving tests.

5. **HIGH — Transient predecessor persistence is incomplete.** The branch promises a sidecar but does not define a marker/status/cause; `_final_record` hashes its `output_path` in [docking.py:1747](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/src/spycep_drug_discovery/docking.py:1747), so absent a created marker it fails. It also writes no retrying selection manifest. A crash after the first transient therefore leaves no claim-level manifest, and a fresh invocation can reuse the claim despite the plan’s immutable/no-resume rule. Finally, only “authoritative success” receives `spawn_failures`; a retry ending in timeout, operational non-fit, genuine failure, or later supervisor exception loses that predecessor chain.

Fix — Define a canonical non-authoritative transient marker/record, atomically publish a `retrying_spawn` selection state after every intercepted execution, and attach the complete predecessor list to every terminal record and selection manifest.

6. **CRITICAL — The exhaustion record contradicts the current validator.** The plan specifies `cause="transient_spawn_failure_exhausted"` in [PLAN-retry-fix.md:58](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PLAN-retry-fix.md:58), but [validate_run_record](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/src/spycep_drug_discovery/docking.py:1579) requires every infrastructure disposition to have `cause=="infrastructure_failure"`. Normal validation would fail before persistence; using `validate=False` would persist an invalid record.

Fix — Keep `cause="infrastructure_failure"`, encode the subtype as `failure_stage` or a validated `infrastructure_cause`, validate with `allow_infrastructure=True`, persist it and the blocking selection manifest, then raise `InfrastructureError`.

7. **HIGH — The fingerprint claim and proposed equality test are false.** `attempt_instance_id` enters `out_path` in [docking.py:971](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/src/spycep_drug_discovery/docking.py:971); the full command containing that path enters `fingerprint_payload` in [docking.py:990](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/src/spycep_drug_discovery/docking.py:990). Each retry therefore has a different fingerprint. Also, `supervisor_source_sha256()` hashes the entire `docking.py`, so this implementation changes all new fingerprints. The narrower statement is true: `spawn_failures` and `spawn_retry_count` themselves are absent from the payload. Extra sidecar fields will not currently break `compute_statistics` or campaign consistency because those gates validate each fingerprint internally and compare campaign/method fields, not fingerprints across attempts.

Fix — Withdraw the same-fingerprint assertion/test or introduce a separate scientific-intent fingerprint that canonicalizes the volatile `--out` argument while retaining the existing attempt-specific fingerprint for exact resume provenance.

8. **HIGH — The ledger design is not sufficiently defined to be fail-closed or idempotent.** The production entry points’ global `campaign_lock` serializes cooperating stage processes, so they should not race if the entire read-check-write occurs under it. But the plan provides no ledger schema/version/campaign validation, no corrupt-ledger test, and no rule for partial or missing files. Its key is an attempt-instance UUID even though every supervisor execution receives a new UUID; the stable distinct unit should be `claim_key`. The existing `_atomic_json` uses a shared fixed `.tmp` name and is unsafe if any caller bypasses the outer lock. Rewriting mutable operational state inside the no-reuse scientific result tree is also a discipline conflict, regardless of calling it “non-scientific.”

Fix — Use strictly validated, append-only per-`claim_key` event files under an explicitly operational state directory, perform creation/checking under the campaign lock, fail on every I/O/schema/duplicate inconsistency, and place a content hash of the finalized ledger in campaign manifests.

9. **HIGH — Retry provenance is not covered by any downstream consistency gate.** [build_timeout_qc_report](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/src/spycep_drug_discovery/docking.py:1385) incorporates `quarantined_predecessors` but not `spawn_failures`; `validate_run_record` tolerates arbitrary extra fields without checking that count, IDs, exit codes, and sidecars agree. The metadata can therefore be inconsistent or edited without invalidating fingerprint, timeout QC, or campaign consistency.

Fix — Add structural and cross-field validation for retry metadata and include spawn-predecessor rows in a dedicated content-addressed operational QC artifact consumed by analysis gates.

10. **MEDIUM — The proposed broad `for`→`while` rewrite is unnecessary.** A raw retry wrapper that reuses one attempt directory would violate ADR-0001, but the outer suspend loop can remain unchanged while a narrow inner helper allocates a fresh context/directory for each spawn execution and returns the first non-transient, non-quarantined result.

Fix — Retain the existing suspend `for` loop and add a bounded inner spawn-retry helper that owns fresh UUID/context/directory creation, leaving the quarantine boundary and authoritative-selection block structurally unchanged.

The entry-point abort routing itself is sound once a valid infrastructure record exists: `InfrastructureError` inherits `DockingError`, all three loops re-raise non-continuable dispositions, and [is_continuable_scientific_disposition](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/src/spycep_drug_discovery/docking.py:1818) rejects infrastructure records. Genuine nonzero Vina failures also remain fatal unless misclassified by the overly broad classifier. The supervisor’s own deadline `TerminateJobObject(..., 1)` path is not a classifier false positive because it returns `deadline_timeout`, while interruption/cleanup failures raise; external termination remains indistinguishable because Windows permits a caller-supplied termination exit code. [TerminateJobObject](https://learn.microsoft.com/en-us/windows/win32/api/jobapi2/nf-jobapi2-terminatejobobject)

VERDICT: REVISE
### Claude's response — Round 1: accepted almost in full; architecture changed

**Verified independently (all confirmed):**
- **#6** — `validate_run_record` (docking.py:1580) requires `cause=="infrastructure_failure"` for an infra
  disposition. My `transient_spawn_failure_exhausted` cause would raise. Real bug.
- **#7** — `attempt_context` builds `out_path` from the per-attempt UUID; `command` embeds it;
  `fingerprint_payload["command"] = normalize_command(command)`; and `normalize_command` only strips absolute
  PREFIXES (keeps the UUID). So every retry has a DIFFERENT fingerprint — my same-fingerprint claim is FALSE.
  (This is already true of existing suspend-retries; each attempt is uniquely fingerprinted by design.)
- **#3** — my pseudocode does `sleep(backoff[spawn_retries])` before the exhaustion check; `backoff[3]` on a
  3-tuple is an IndexError. My retry loop crashes on exhaustion. Real bug.

**Accepted:** #1, #2, #3, #4, #5, #6, #7, #8, #9, #10 — essentially the whole review.
- **#1 (CRITICAL, integrity)** — the `>= 0xC0000000` range is NOT a 'never started' proof. An instant access
  violation (0xC0000005) with empty buffered output <1s would pass all three signals and be wrongly retried.
  FIX ADOPTED: replace the range with an explicit ALLOWLIST of pre-entrypoint loader codes, initially ONLY the
  observed `0xC0000142`; withdraw the 'proof' language. This is the single most important correction.
- **#4 (CRITICAL)** — quarantine must take PRECEDENCE (a suspend-touched result must be quarantined per ADR-0001
  even if it also looks fast/empty); each retry path increments exactly one bounded counter; `mkdir(exist_ok=False)`
  + fresh UUID per execution preserved.
- **#10 (architecture)** — ADOPTED and it resolves the risk I flagged myself: keep the frozen suspend `for`-loop
  STRUCTURALLY UNCHANGED; add a narrow inner spawn-retry helper that owns fresh context/dir per spawn execution and
  returns the first non-transient, non-quarantined result. The whole `for`→`while` restructure is withdrawn.

**Nothing rejected.** Rewriting as revision 2 around the inner-helper architecture, the allowlist classifier, the
corrected retry ordering, infra-cause-with-failure_stage exhaustion, per-terminal predecessor chains + retrying_spawn
manifests, a Codex-compliant operational ledger (per-claim_key, append-only, operational dir, fail-closed), a QC gate
over spawn_failures, and the withdrawn fingerprint-equality claim.

---

## Round 2 — Codex (same thread, read-only) — 6 CRITICAL + 3 HIGH (all new integration issues)

Revision 2 is substantially safer, but it introduces several new helper/ledger integration blockers. The classifier narrowing itself is acceptable.

## Blocking findings

1. **CRITICAL — The helper cannot propagate the active context when the supervisor raises.** Today the outer loop binds `context`, `out_path`, `marker_path`, `sidecar_path`, and `common` before entering the `try` in [docking.py:1097](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/src/spycep_drug_discovery/docking.py:1097). If the helper allocates that context internally and `_run_vina_supervised` raises, tuple assignment never completes; the outer exception block then sees unbound variables on the first iteration or stale variables from a prior quarantine iteration. The claim that the supervisor exception path remains unchanged is therefore false.

Fix — Either finalize supervisor exceptions inside the helper or raise a context-bearing exception and make the outer handler explicitly extract that active context before touching any paths.

2. **CRITICAL — “Only swap the call” is structurally impossible.** The helper must take over UUID allocation, `attempt_context()`, field extraction, and `mkdir`, which currently occur before the direct supervisor call; the outer block also needs a new `attempt_instance_id` derived from the returned context for authoritative selection at [docking.py:1272](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/src/spycep_drug_discovery/docking.py:1272). Leaving those lines creates an unused orphan attempt directory; removing them necessarily changes more than the call.

Fix — Replace the entire iteration prologue through the supervisor call with explicit helper-result destructuring, then assert that the unchanged region begins at the duration calculation on current line 1169.

3. **CRITICAL — Spawn state resets across suspend retries.** The helper-local `spawn_retries` and returned `spawn_failures` disappear when the outer quarantine branch executes `continue`. This falsifies §6’s promise that every terminal record contains the complete predecessor chain. The stated 12-call bound confirms the reset: one claim can receive nine spawn retries—three during each suspend iteration—despite `MAX_TRANSIENT_SPAWN_RETRIES=3`.

Fix — Keep the cumulative retry counter and `spawn_failures` list outside the suspend `for` loop, pass them through every helper call, preserve a per-claim three-retry ceiling, and restore the additive six-call maximum.

4. **CRITICAL — Exhaustion overwrites the last predecessor sidecar.** Section 3 writes and appends the transient sidecar before checking exhaustion, then §5 tells the caller to finalize an infrastructure record using that same returned context. That overwrites the last transient sidecar and marker; §9 will subsequently read the predecessor path and find an infrastructure record rather than the required allowlisted transient signature.

Fix — On the terminal fourth failure, write only the infrastructure terminal record for that context; keep the three earlier transient executions as immutable predecessors and do not append the terminal context to `spawn_failures`.

5. **CRITICAL — Infrastructure records still cannot “validate normally.”** Even with the corrected cause, [validate_run_record](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/src/spycep_drug_discovery/docking.py:1579) deliberately raises `InfrastructureError` whenever `allow_infrastructure=False`. Therefore `_final_record(validate=True)` or plain `validate_run_record(record)` prevents the caller from reaching the planned sidecar and selection-manifest writes.

Fix — Build with `validate=False`, call `validate_run_record(record, allow_infrastructure=True)`, persist both artifacts, and only then raise the intended `InfrastructureError`.

6. **CRITICAL — Claim-level selection history can be erased during a retry.** There is no filesystem race—the writes are sequential atomic replacements—but there is a semantic collision. `_selection_manifest` currently has no spawn-predecessor field, and the helper signature receives no accumulated `quarantined` list. If a transient occurs after an earlier suspend quarantine, `retrying_spawn` overwrites the existing `retrying` manifest without that quarantine history; a crash at that point leaves an incomplete authority trail. Later outer writes likewise overwrite any helper-only spawn fields.

Fix — Version the selection schema and require every helper and outer write to carry both cumulative `quarantined_attempts` and cumulative `spawn_failure_attempts`.

7. **HIGH — Raw `claim_key` is not a valid Windows filename.** Current claim keys contain colons—`workflow:entity:state:pocket` in [docking.py:1028](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/src/spycep_drug_discovery/docking.py:1028)—so `<claim_key>.json` cannot be created on Windows. Generic sanitization would also permit collisions.

Fix — Name ledger files with `sha256(claim_key).json` and store and strictly verify the full unsanitized `claim_key` inside each record.

8. **HIGH — A cumulative ledger hash becomes stale across stage processes.** WIDE’s manifest records the ledger-set hash at WIDE completion; TIGHT, SpeB, and BORON then add files. Recomputing against the live ledger makes earlier manifests fail, while merely comparing copied manifest/QC values does not prove correspondence to the ledger. The plan does not define snapshot or hash-chain semantics.

Fix — Hash an immutable per-stage ledger snapshot embedded or content-addressed with that stage’s manifest, then have aggregate validation verify snapshot integrity and monotonic set inclusion—or create one final sealed campaign ledger consumed by analysis.

9. **HIGH — The proposed QC cannot currently resolve predecessor sidecars safely.** `build_timeout_qc_report(run_records)` and `validate_manifest_timeout_qc(manifest)` receive no project root, yet sidecar paths are project-relative. A file-existence/signature gate would otherwise depend on the process working directory. The predecessor summary also omits a sidecar content hash.

Fix — Record each predecessor sidecar’s SHA-256 and pass an explicit trusted `project_root` to the generation-time filesystem gate; downstream manifest validation should recompute embedded metadata without relying on cwd.

## Verified fixes and refinements

- **Classifier:** The `< SUSPEND_THRESHOLD` guard is exactly complementary to the outer `>= SUSPEND_THRESHOLD` comparison for finite values. A real suspension shorter than five seconds remains undetected, but that is an existing ADR threshold limitation, not a new regression. The prose should say “not threshold-detected” rather than “not suspend-touched.”
- **Timing ambiguity refinement:** The classifier does not explicitly test `unbiased_seconds < timeout_seconds`. This is harmless for the frozen 1,800-second campaign timeout because the classifier already requires `<1` second, but adding the explicit guard would make the stated precedence invariant true for non-campaign/test timeouts.
- **Transient record validation:** `status="failed"` and `cause="transient_spawn_failure"` pass the current validator when the marker exists, authority is false, and the wait/timing fields match. The validator does not enumerate allowed causes for ordinary `wait_signaled` failures.
- **Selection-path replacement:** Sequential `retrying_spawn → retrying/authoritative/blocked` replacement is safe once every replacement carries the complete cumulative history.
- **Campaign lock:** The three production entry points hold `campaign_lock` around the entire `_run_campaign`, so the lock is not released between attempts; it is released between stage processes. That safely serializes cooperating WIDE/TIGHT/SpeB/BORON ledger updates.
- **Scope, allowlist, fingerprint:** Round-1 findings #1, #2, and #7 are adequately addressed.
- **Terminology refinement:** `_operational` is logically excluded from analysis but remains physically underneath `results/docking/campaign_<id>`; call it an excluded operational subtree, not “outside” the result tree.

VERDICT: REVISE
### Claude's response — Round 2: accepted in full; cumulative state hoisted to claim level

Round-1 fixes CONFIRMED by Codex: classifier allowlist (#1), narrowed scope (#2), fingerprint claim (#7),
transient-record validation passes, campaign_lock serializes stage processes correctly, quarantine-precedence
guard is exactly complementary to the outer suspend comparison. The core architecture holds.

**Verified (both confirmed):**
- **#5** — `validate_run_record` has `allow_infrastructure=False` default and RAISES at :1587 without it; the
  existing infra path already uses `validate=False` (:1151). My 'validate normally' was wrong. Fix: build
  `validate=False`, then `validate_run_record(record, allow_infrastructure=True)`, persist, then raise.
- **#7** — `claim_key = f"{workflow}:{entity_id}:{state_id}:{pocket}"` (:1028) contains COLONS → invalid Windows
  filename. My `<claim_key>.json` fails. Fix: `sha256(claim_key).json`, full claim_key stored inside.

**All 9 accepted.** The 6 criticals reduce to one root cause: I scoped cumulative spawn state INSIDE the helper,
so it resets when the outer suspend loop `continue`s. Unifying fix in rev 3:
- Cumulative `spawn_retries` counter + `spawn_failures` list live at the CLAIM level (dock_ligand scope, outside
  the suspend loop), threaded through every helper call → per-claim ceiling is 3 TOTAL (not 3-per-suspend-iter);
  additive 6-call max (#3).
- The helper handles the supervisor-RAISES path internally (finalizes infra there), so the outer exception
  handler never sees unbound context (#1). Honest scope: helper replaces the iteration prologue THROUGH the
  supervisor call + its exception handling; outer unchanged from the duration calc (:1169) onward (#2).
- Exhaustion terminal writes ONLY the infra record for the 4th context; the 3 prior transient executions stay
  immutable predecessors; terminal NOT appended to spawn_failures (#4).
- Selection manifest: versioned, carries cumulative quarantined_attempts + spawn_failure_attempts on EVERY write
  (helper and outer), so history is never erased (#6).
- Ledger: `sha256(claim_key).json` filenames (#7); SEALED once at analysis time with a single content hash
  (avoids the stale-per-stage-hash problem #8); predecessor sidecar SHA-256 stored + explicit project_root passed
  to the QC gate, cwd-independent (#9).
- Terminology: 'not threshold-detected' (not 'suspend-touched'); '_operational' is an EXCLUDED operational
  subtree under the campaign dir, not 'outside' it; add explicit `unbiased < timeout_seconds` guard for non-campaign timeouts.

---

## Round 3 — Codex (same thread) — 3 CRITICAL + 2 HIGH + schema refinement; CONVERGING

Revision 3 is converging, but two control-flow blockers and the analysis-time sealing design still need correction.

## Blockers

1. **CRITICAL — The claim-level integer counter is not actually threaded through the helper.** Section 4 says `_run_one_spawn` receives `spawn_retries` but returns only `(supervised, context)`. Python integers are immutable: `spawn_retries += 1` inside the helper does not update the caller. After a suspend return, the next helper call receives the old count, recreating the reset bug and invalidating the six-call proof. The lists do not have this problem because they are mutable.

Fix — Pass one mutable `SpawnRetryState` object containing `retry_count` and `failures`, or return the updated counter alongside `(supervised, context)` and assign it before any outer `continue`.

2. **HIGH — The relocated exception handler is narrower than the existing behavior.** Revision 3 describes handling `_SupervisorInfrastructureError`, but the current block catches `BaseException` and converts every other exception to `failure_stage="supervisor_exception"` in [docking.py:1112](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/src/spycep_drug_discovery/docking.py:1112). Catching only `_SupervisorInfrastructureError` changes first-call behavior for interruption or unexpected supervisor exceptions and leaves no structured terminal record.

Fix — Relocate the complete `except BaseException` branch verbatim, including the existing type split, marker text, `WAIT_FAILED`, termination action, cleanup fields, chained raise, and generic `supervisor_exception` fallback.

3. **CRITICAL — The exhaustion ordering remains textually contradictory.** [PLAN-retry-fix.md:64](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PLAN-retry-fix.md:64) first instructs the helper to write the execution’s transient predecessor, then line 67 says the exhaustion check happens first and the fourth execution writes only an infrastructure record. Those cannot both occur. The intended behavior and tests are correct, but the algorithm still permits an implementation that recreates the sidecar overwrite.

Fix — State the branch literally as `if exhausted: write infrastructure terminal and raise; else: write/append transient predecessor, publish retrying manifest, back off, increment`.

4. **CRITICAL — “Seal once in compute_statistics” is not yet a valid campaign-wide seal.** Current [compute_statistics.py:109](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/scripts/compute_statistics.py:109) loads WIDE, TIGHT, and SpeB only; it neither requires BORON nor acquires `campaign_lock`. It could therefore seal while BORON is still absent or running. After releasing the analysis process, BORON can add ledger entries because no seal tombstone prevents later docking. Earlier final-analysis hashes would then be stale.

Fix — Require and validate all four manifests, acquire `campaign_lock`, verify exact ledger-to-manifest equality, create an immutable campaign seal with exclusive creation, and make every docking entry point refuse a sealed campaign.

5. **HIGH — “Monotonic inclusion” has no verifiable definition with one final snapshot.** Without per-stage snapshots, final analysis cannot prove historical monotonicity; it can only verify the final ledger set. Runtime exclusive creation can enforce append-only behavior prospectively, but the final check must compare concrete sets.

Fix — Define the invariant as exact equality between final ledger claim keys and the union of all four manifests’ claims with `spawn_retry_count > 0`, while ledger files are created with exclusive no-overwrite semantics.

## Required schema refinement

Adding cumulative history does ripple through the current APIs:

- `_final_record` currently validates before returning.
- `_selection_manifest` currently accepts only `quarantined` in [docking.py:1773](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/src/spycep_drug_discovery/docking.py:1773).
- `RUN_RECORD_REQUIRED_FIELDS` does not contain either spawn field.
- Existing analysis validators cannot distinguish “zero retries” from accidentally omitted metadata.

This does not alter the disposition logic from line 1169 onward, but it is a real schema change, not merely an extra write.

Fix — Have `_final_record` always emit `spawn_retry_count` and `spawn_failures` before validation, version the run-record schema or add a required retry-metadata schema marker, and extend every `_selection_manifest` call with both cumulative histories.

## Verified behavior

- **Concrete interleave, assuming the counter-threading fix:** transient call 1 increments spawn retries to 1; call 2 is suspend-quarantined and consumes suspend retry 1; transient call 3 increments spawn retries to 2; call 4 succeeds. Final history contains two spawn predecessors and one quarantine. Neither event consumes the other budget.
- **Worst case:** three spawn retries plus two suspend retries plus one terminal execution equals six calls. A sixth transient exhausts the spawn budget; a sixth suspend at outer `retry_index == 2` hits the unchanged quarantine limit.
- **First-call supervisor exception:** relocating the full existing handler preserves marker, record, blocked selection, and raised exception behavior; cumulative histories are simply empty.
- **Transient predecessor validation:** `status="failed"` and `cause="transient_spawn_failure"` remain accepted because the current validator does not enumerate ordinary `wait_signaled` failure causes.
- **Quarantine guard:** `< SUSPEND_THRESHOLD` is complementary to the existing outer `>=` boundary. The explicit unbiased-versus-timeout guard closes the test-time timing-ambiguity case.
- **Selection writes:** there is no concurrent file collision under the stage-wide lock; sequential replacement is correct once every replacement includes both complete histories.
- **Ledger access:** `compute_statistics` has `PROJECT_ROOT`, and the validated manifests provide `campaign_id`, so it can derive the campaign directory and record the seal hash in `docking_statistics.json`. The missing pieces are four-stage completeness, locking, and post-seal enforcement.
- **QC path handling:** explicit generation-time `project_root` plus stored sidecar hashes resolves the cwd dependency.

Round 3 has eliminated the classifier, fingerprint, directory-name, and suspend-loop architecture problems. The remaining changes are localized and should be closable in one revision.

VERDICT: REVISE
### Claude's response — Round 3: accepted; Codex confirms convergence

Codex verified: the concrete interleave works, the <=6-call bound holds with both budgets independent, first-call
supervisor-exception behavior is preserved by verbatim relocation, transient-record validation passes, the
quarantine guard is correct, and compute_statistics has PROJECT_ROOT + campaign_id. Its closing line: "Round 3 has
eliminated the classifier, fingerprint, directory-name, and suspend-loop architecture problems. The remaining
changes are localized and should be closable in one revision."

**Verified (both confirmed):**
- **#4** — compute_statistics.py:110 loads only WIDE/TIGHT/SPEB (`validate_campaign_manifest_set((wide,tight,speb))`),
  NO boron, no campaign_lock, no seal. Sealing there could seal while BORON still writes. Real gap.
- **schema** — `_selection_manifest` takes only `quarantined` (:1773); `RUN_RECORD_REQUIRED_FIELDS` (:46) has
  neither spawn field. Adding cumulative history is a real schema change.

**All accepted (localized fixes for rev 4):**
- **#1 (CRITICAL, Python)** — an `int` counter passed to the helper and `+= 1`'d inside does NOT update the
  caller (ints immutable), recreating the reset bug. FIX: a single mutable `SpawnRetryState` object
  {retry_count, failures} threaded through; lists were already fine.
- **#2** — the current handler catches `BaseException` with a type-split (infra vs generic `supervisor_exception`);
  relocate it VERBATIM, not narrowed to `_SupervisorInfrastructureError`.
- **#3** — state the branch literally: `if exhausted: infra terminal + raise; else: predecessor + retrying manifest
  + backoff + increment` — no predecessor write before the exhaustion check.
- **#4/#5** — sealing becomes a proper campaign-completion barrier: a dedicated seal step after stage 4 that
  requires all FOUR stage manifests, acquires campaign_lock, verifies exact set-equality (final ledger claim_keys
  == union of the 4 manifests' claims with spawn_retry_count>0), writes an immutable seal via EXCLUSIVE create,
  records the hash; every docking entry point refuses a sealed campaign. Ledger files also exclusive-create.
- **schema** — `_final_record` always emits `spawn_retry_count`+`spawn_failures` (default 0/[]) before validation
  (distinguishes zero-retries from omitted); bump RUN_SCHEMA_VERSION; extend every `_selection_manifest` call and
  the selection schema with cumulative `spawn_failure_attempts`.

---

## Round 4 — Codex (same thread) — 2 seal blockers + refinements; "very close"

Revision 4 is very close. Mutable retry state and helper ownership now compose correctly. Two localized seal-barrier issues still prevent approval.

## Blockers

1. **CRITICAL — The sealed check must occur after acquiring `campaign_lock`.** The plan says every entry point refuses a sealed campaign but does not freeze the ordering. Checking `SEALED.json` before entering the lock leaves a TOCTOU: a stage can observe “unsealed,” wait while the sealer creates `SEALED.json`, then acquire the lock and start writing into the sealed campaign. The seal operation has the reciprocal risk if it reads manifests or ledger state before acquiring the lock.

Fix — Every stage must execute `with campaign_lock(...): require_unsealed(); _run_campaign(...)`, while the sealer must acquire the same lock before reading any manifest/ledger state and hold it through exclusive seal creation.

2. **HIGH — A legitimate zero-retry campaign may have no ledger directory.** If `_operational/spawn_retry/` is created only on the first transient, a perfect campaign leaves it absent. The seal’s directory read then conflicts with “any I/O error fails closed,” even though the correct equality is `empty ledger == empty manifest union`.

Fix — Create the empty operational ledger directory once during campaign initialization under the lock; thereafter absence is corruption, while an empty directory has a canonical empty-set hash.

## Verified behavior

- **Mutable state:** `SpawnRetryState` is shared by reference, so helper mutations are visible after an outer suspend `continue`. `retry_count` and `failures` remain equal on every completed retry transition.
- **Concrete interleave:** transient 1 produces predecessor 1 and count 1; suspend consumes outer quarantine retry 1; transient 2 produces predecessor 2 and count 2; success becomes authoritative. Final history contains both spawn predecessors and the quarantine.
- **Independent limits:** transients never advance `retry_index`; suspends never change `state.retry_count`. Three spawn retries plus two suspend retries plus one terminal execution gives the correct six-call ceiling.
- **Exhaustion:** with `state.retry_count == 3`, the fourth transient execution becomes the infrastructure terminal and is not written or appended as a predecessor.
- **Exception relocation:** if context fields are destructured immediately after allocation and before the unchanged supervisor `try`, the complete `except BaseException` block has all its existing paths in local scope. A first-call exception behaves identically except for the intentional new schema fields and selection version.
- **Zero-retry equality:** after establishing the canonical empty directory, zero-retry claims are absent from both sets and equality succeeds.
- **Ledger equality:** final ledger keys should equal exactly the union of claim keys whose terminal records across WIDE/TIGHT/SpeB/BORON have `spawn_retry_count > 0`.

## Required implementation refinements

- The schema bump requires modifying existing tests despite §14 calling tests “additive.” [test_docking_timeout.py:119](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/tests/test_docking_timeout.py:119) asserts the exact old v2 literal, and the manual fixture in [test_environment_and_workflow_schema.py:24](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/tests/test_environment_and_workflow_schema.py:24) must gain both required spawn fields.
- The dead partial `campaign_v2_20260717b` and `campaign_v2_20260718` artifacts do not matter: they are non-resumable, remain v2, and their existing campaign roots prevent reuse. They should not be migrated or treated as v3 evidence.
- Invoke the seal through `run_stage` or an equivalent checked command so seal failure prevents the shell script from printing campaign completion.
- Define the ledger content hash as canonical JSON over entries sorted by full `claim_key`, excluding `SEALED.json` and filesystem metadata.
- All downstream entry points—not only `compute_statistics`—must require and validate the seal before consuming the new campaign.
- Update stale wording at plan line 162 (“sealed at analysis”) and `run_campaign.sh`’s schema-v2 comment.

This needs one final, narrowly scoped pass specifying lock/check ordering and canonical empty-ledger initialization. No retry-loop or classifier redesign remains.

VERDICT: REVISE
### Claude's response — Round 4: accepted; rev 5 is the final localized pass

Codex verified the ENTIRE core sound: SpawnRetryState is shared by reference (mutations visible after a suspend
continue); the concrete interleave yields 2 spawn predecessors + 1 quarantine with independent budgets; the
6-call ceiling holds; exhaustion makes the 4th execution the infra terminal (not a predecessor); the verbatim
exception relocation has all paths in local scope if context is destructured immediately after allocation.
Its verdict: "one final, narrowly scoped pass specifying lock/check ordering and canonical empty-ledger
initialization. No retry-loop or classifier redesign remains."

**Both blockers accepted (rev 5):**
- **#1 (CRITICAL, TOCTOU)** — sealed-check must be INSIDE the lock. Frozen: every entry point
  `with campaign_lock(): require_unsealed(); _run_campaign()`; the sealer takes the same lock before reading any
  manifest/ledger state and holds it through exclusive seal creation.
- **#2 (empty ledger)** — the `_operational/spawn_retry/` dir is created at campaign init under the lock, so a
  zero-retry campaign has an empty dir (canonical empty-set hash) and absence thereafter is corruption → abort.

**Refinements applied:** seal invoked via `run_stage` so its failure blocks 'campaign completion'; ledger hash =
canonical JSON sorted by full claim_key excluding SEALED.json + fs metadata; ALL downstream entry points
require+validate the seal; stale 'sealed at analysis' wording removed.

**Correction to MY plan (Codex R4):** rev-1's "tests additive, no existing test modified" was FALSE — verified:
`test_docking_timeout.py:119` hard-asserts `docking-run-record-v2` and the `_run_record` fixture in
`test_environment_and_workflow_schema.py:24` lacks the new required fields. The RUN_SCHEMA_VERSION bump forces both
edits; §14 now states this. Codex also confirmed the dead partial campaigns (v2_20260717b/v2_20260718) are inert
(non-resumable, remain v2, roots prevent reuse) — no migration.

---

## Round 5 — Codex (FINAL, same thread) — **VERDICT: APPROVED**

Revision 5 is approved. The two remaining blockers close cleanly:

- The sealed check and stage execution share one lock scope; the sealer uses that same lock through exclusive seal creation. This removes the check/seal TOCTOU.
- Campaign initialization creates the ledger directory under lock. Zero retries therefore canonicalize to an empty set/hash, while later absence fails closed.
- Set equality correctly excludes zero-retry claims from both sides and includes exhausted retry claims through their terminal `spawn_retry_count`.
- Running the seal through `run_stage` prevents false campaign-completion reporting.
- The schema-v3 test and fixture migrations are now explicitly accounted for. Dead v2 partial campaigns are historical artifacts, not resumable inputs.
- No new masking, silent-drop, counter, or scientific-integrity path was introduced. The remaining desktop-heap limitation is honestly bounded scope, not a plan defect.

Implementation tests should still exercise the zero-retry seal and a stage/sealer lock race, but those are verification requirements, not design blockers.

VERDICT: APPROVED
## Act 2 complete — 5 rounds, converged (APPROVED)

| Round | Findings | Outcome |
|---|---|---|
| 1 | 10 (2 integrity-critical) | REVISE — classifier would retry genuine crashes; retry loop crashed on exhaustion |
| 2 | 9 | REVISE — inner-helper rewrite integration; cumulative state reset root cause |
| 3 | 5 | REVISE — int-immutability counter bug; 'converging, closable in one revision' |
| 4 | 2 + refinements | REVISE — seal-barrier TOCTOU + empty-ledger; 'very close' |
| 5 | 0 | **APPROVED** — both seal fixes close cleanly; no new integrity path |

**Defects Act 2 caught that would have shipped:** a classifier that would silently retry a genuine mid-dock crash
as 'never started' (integrity hole); a retry loop that IndexError-crashed on its own exhaustion path; cumulative
spawn state that reset across suspend retries (lost predecessors, 9-retry budget instead of 3); an exhaustion
record that failed the validator; an exhaustion terminal that overwrote predecessor sidecars; a Python int passed
by value and mutated in a helper (no-op); a narrowed exception handler; ledger filenames with colons (invalid on
Windows); a stale-across-stages ledger hash; a check-then-lock seal TOCTOU; a false 'tests are additive' claim.

**What the plan deliberately does NOT do:** fix cumulative desktop-heap exhaustion (retry saves momentary
transients only — stated in ADR-0003); retry any genuine/ambiguous/non-allowlisted failure; skip a compound;
resume across runs. Proves less than a naive 'just retry on nonzero' would claim, and says exactly where it stops.

Awaiting Josh's sign-off. No code written during either act. Act 3 (build) begins only after sign-off.
Codex noted two implementation-time test requirements (zero-retry seal; stage/sealer lock race) — verification
items for the build, not design blockers.

---

# Act 3 — Build (Codex types, Claude verifies)

## Round 1 — Codex build (`gpt-5.6-sol`, `--yolo`, user-authorized)
_Isolation checkpoint `50bacb0`, clean tree. SPEC=PLAN-retry-fix.md rev 6. Pre-build baseline: 232 passed._

**Codex report:** implemented rev 6; **deviations: none**. Changed docking.py (classifier, SpawnRetryState, helper,
predecessors, schema v3, QC, ledger, seal APIs), the 3 entry points (locked require_unsealed), new
scripts/seal_docking_campaign.py, compute_statistics/make_figures/write_docking_methods (downstream seal gates),
run_campaign.sh (seal step), ADR-0003, PROJECT_CONTEXT.md (domain language), and tests
(test_docking_timeout v2→v3 literal, test_environment fixture spawn fields, new test_docking_spawn_retry.py +
test_campaign_seal.py).

### Claude's verdict — VERIFIED, no fix round needed
Verified independently (not trusting Codex's claims):
- **Scope:** only expected files. The three extra (make_figures, write_docking_methods, PROJECT_CONTEXT) are
  plan-faithful — §10a "all downstream entry points require+validate the seal" and the §Domain-language addition.
- **Hard constraints all hold.** `validate_suspend_calibration` / `docking-suspend-calibration-v1`: **0 diff lines**
  (Josh's Act-1 constraint held). **Nothing under `results/`**; the three dead/archive roots present and the ADR-0001
  `29287` sidecar byte-intact. Frozen params (seed/exh/timeout/num_modes/cpu) untouched. `HEAD` still Claude's commit —
  **no git ops by Codex**.
- **The five danger points, verified in source:** (1) `TRANSIENT_SPAWN_STATUS_ALLOWLIST = frozenset({0xC0000142})` —
  allowlist, not a range (the integrity-hole fix); (2) `@dataclass class SpawnRetryState` — mutable, not a bare int;
  (3) exhaustion checked **before** any predecessor write (`if is_transient…: if state.retry_count >= MAX: <infra
  terminal>`); (4) `validate_run_record(record, allow_infrastructure=True)` + `failure_stage=
  "transient_spawn_failure_exhausted"`, cause `"infrastructure_failure"`; (5) ledger `sha256(claim_key)+".json"`, and
  `with campaign_lock(...): require_unsealed(...); _run_campaign(...)` — seal-check **inside** the lock (TOCTOU closed).
- **Suspend-retry byte-equivalence:** `quarantine_reason` / `authoritative_selected = quarantine_reason is None` /
  `halted_quarantine_limit` boundary / `quarantined_predecessors` all intact; the only diff in that region is the new
  infra-terminal `authoritative_selected=False` writes and the cumulative-history threading. The 7-round timeout-fix
  behavior is preserved.
- **Proof (run by Claude):** `pytest tests -q` → **261 passed, 0 failed, 0 skipped** (baseline 232 → +29). The 29 new
  tests map 1:1 to the review's load-bearing findings: cumulative-budget-across-suspend-iterations (the int-immutability
  fix), non-allowlisted-instant-crash-is-fatal (the integrity floor), exhaustion-never-overwrites-predecessors, the
  ≤6-supervisor-call ceiling, both-histories-through-interleave, sha256 colon-claim_key filename, corrupt-ledger
  fail-closed, zero-retry empty-ledger seal, and stage/sealer lock race.

**Deferred, correctly not built:** running the campaign, the live calibration, and the desktop-heap root-cause
(evidence-gated). Rounds used: 0 of 2.

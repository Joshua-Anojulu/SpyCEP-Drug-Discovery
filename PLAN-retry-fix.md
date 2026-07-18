# Plan: Tolerate transient vina process-spawn failures within a campaign
_Locked via grill-with-docs — by Claude + Josh, 2026-07-18. Terms per `PROJECT_CONTEXT.md` / ADR-0001 / ADR-0002._
_Isolation checkpoint: HEAD = `552a481`, branch `remediation-2026-07-13`, tree clean._
_**Revision 6 — APPROVED** by Codex round 5 (2026-07-18). Rounds 1–4 preceding (Codex R4: "very close… one final narrowly scoped pass; no retry-loop or
classifier redesign remains"). Seal/lock ordering frozen; empty-ledger canonicalized; test impact stated honestly.
See `PLAN-REVIEW-LOG-retry-fix.md`._

## Goal

Survive the exact observed transient: `vina.exe` created successfully but dying at loader init before running its own
code (WIDE 141/154, `sildenafil`, exit `0xC0000142` STATUS_DLL_INIT_FAILED, empty stdout/stderr, 6.8 ms unbiased; the
compound docks fine in isolation, −6.296 kcal/mol). Retry that narrow signature; keep every genuine vina failure fatal;
never drop a compound.

## Scope discipline (Codex R1 #1/#2)

Tolerate the **specific silent DLL-init signature only**. Exit code does not prove provenance, so we use an explicit
**allowlist**, not a severity range; no "never started proof" is claimed. Slow (>1 s), noisy (any output), or
non-allowlisted startup failures stay **fatal/fail-closed** — acceptable under the integrity floor ("never retry a
genuine failure").

## Domain language (added to PROJECT_CONTEXT.md)

- **Transient spawn failure** — a *returned* supervised result matching the allowlisted signature: exit in
  `TRANSIENT_SPAWN_STATUS_ALLOWLIST`, empty stdout+stderr, unbiased `< TRANSIENT_SPAWN_MAX_ELAPSED_SECONDS`, and
  **not threshold-detected as a suspend** (Codex R2 terminology). Retryable.
- **Genuine vina failure** — vina ran and failed, or any non-allowlisted/slow/noisy exit. Fatal, never retried.
- **Quarantine precedence** — a suspend-/timing-ambiguous execution is quarantined per ADR-0001 before any spawn-retry.

## Approach

1. **Constants in `docking.py`** (frozen, prospectively set; never tuned — R4 #4):
   - `TRANSIENT_SPAWN_STATUS_ALLOWLIST = frozenset({0xC0000142})` — only the observed loader code; widening is a logged
     decision, not a range.
   - `TRANSIENT_SPAWN_MAX_ELAPSED_SECONDS = 1.0`; `MAX_TRANSIENT_SPAWN_RETRIES = 3` (⇒ ≤4 spawn executions per claim);
     `TRANSIENT_SPAWN_BACKOFF_SECONDS = (2.0, 5.0, 10.0)`; `CAMPAIGN_TRANSIENT_SPAWN_BUDGET = 10` distinct claim_keys.

2. **Classifier `is_transient_spawn_failure(supervised, timeout_seconds)`** (Codex R1 #1/#4, R2 refinement):
   ```
   disposition_basis == "wait_signaled"
   and exit_code is not None and (int(exit_code) & 0xFFFFFFFF) in TRANSIENT_SPAWN_STATUS_ALLOWLIST
   and stdout.strip() == "" and stderr.strip() == ""
   and float(unbiased_seconds) < TRANSIENT_SPAWN_MAX_ELAPSED_SECONDS
   and float(unbiased_seconds) < float(timeout_seconds)            # explicit; harmless for 1800s, correct for test timeouts
   and (float(wall_seconds) - float(unbiased_seconds)) < SUSPEND_THRESHOLD   # quarantine precedence (threshold-detected suspend wins)
   ```

3. **Cumulative spawn state in ONE MUTABLE OBJECT at the CLAIM level (Codex R2 #3/#6, R3 #1).** A Python `int` passed
   into the helper and `+= 1`'d inside does **not** update the caller (ints are immutable) — so the counter must be a
   mutable object, not a bare int. In `dock_ligand`, **before** the suspend `for` loop, create
   `state = SpawnRetryState(retry_count=0, failures=[])` (a small mutable dataclass) plus the existing `quarantined`
   list. Both are passed to every helper call and every selection-manifest write, so a claim's spawn budget is **3
   total across all suspend iterations** and the predecessor/authority history is never lost on `continue`. Additive
   worst case: `MAX_SUSPENDED_RETRIES` suspend retries + `MAX_TRANSIENT_SPAWN_RETRIES` spawn retries + 1 terminal =
   **≤6 supervisor calls per claim**, asserted in tests.

4. **Inner helper `_run_one_spawn(state, quarantined, ...)` (Codex R1 #10, R2 #1/#2/#4, R3 #1/#2/#3).** Returns
   `(supervised, context)` for the first non-transient-spawn execution, or finalizes a terminal itself and raises. Per
   call:
   - Allocate a **fresh** context (new UUID), `attempt_dir.mkdir(exist_ok=False)` (ADR-0001), run
     `_run_vina_supervised`.
   - **Supervisor RAISES**: relocate the **complete existing `except BaseException` branch VERBATIM** from the current
     docking.py:1112–1167 (Codex R3 #2) — including the `_SupervisorInfrastructureError`-vs-generic type split, the
     generic `failure_stage="supervisor_exception"` fallback, marker text, `WAIT_FAILED`, termination action, cleanup
     fields, sidecar, `blocked_infrastructure_failure` manifest (now also carrying cumulative `quarantined` +
     `state.failures`), and the chained `raise InfrastructureError`. It executes with *this* execution's context bound,
     so the outer loop never sees unbound context (Codex R2 #1). First-call behaviour is byte-equivalent; cumulative
     histories are simply empty then.
   - **`is_transient_spawn_failure(supervised, timeout_seconds)`** — branch stated **literally** (Codex R3 #3), with the
     exhaustion check strictly **before** any write for the terminal execution:
     - **`if state.retry_count >= MAX_TRANSIENT_SPAWN_RETRIES`** (exhausted): write **only** the infrastructure terminal
       record for *this* context (`status/cause="infrastructure_failure"`,
       `failure_stage="transient_spawn_failure_exhausted"`, `exit_code=0xC0000142`; §6 persistence), write the
       `blocked_infrastructure_failure` manifest, `raise InfrastructureError`. This 4th execution is **not** appended to
       `state.failures`; the 3 earlier transient executions remain the immutable predecessors (Codex R2 #4).
     - **`else`**: write this execution's immutable **transient predecessor** record (`status="failed"`,
       `cause="transient_spawn_failure"`, marker output_path; validated — the validator does not enumerate causes for
       `wait_signaled` failures, confirmed R2) with its sidecar SHA-256; append it to `state.failures`; publish a
       `retrying_spawn` selection manifest (cumulative history); `sleep(BACKOFF[state.retry_count])`;
       `state.retry_count += 1`; loop.
   - **Otherwise** (suspend-touched, timeout, genuine failure, success): return `(supervised, context)` immediately.

5. **Outer suspend loop — honest scope (Codex R2 #2).** The iteration **prologue through the supervisor call and its
   exception handler** (current 1097–1167) is replaced by `supervised, context = _run_one_spawn(...)` plus
   destructuring `attempt_instance_id`/`out_path`/`marker_path`/`sidecar_path`/`common` from the returned context. From
   the **duration calculation (current line 1169) onward the block is unchanged** — suspend_gap, quarantine_reason, the
   `retry_index == MAX_SUSPENDED_RETRIES` boundary, `quarantined_predecessors`, authoritative selection. The diff must
   show 1169→end is byte-equivalent except that every `_selection_manifest(...)` and the terminal record now also
   carry cumulative `spawn_failures` (Codex R2 #6).

6. **Infrastructure record persistence (Codex R2 #5).** All infra terminals: build `_final_record(..., validate=False)`,
   then `validate_run_record(record, allow_infrastructure=True)`, then persist sidecar + selection manifest, then raise
   `InfrastructureError`. Mirrors the existing infra path (docking.py:1151 already uses `validate=False`).

7. **Selection manifest, versioned (Codex R2 #6).** Bump the selection schema version; add cumulative
   `spawn_failure_attempts` alongside the existing quarantine fields. Every write — `retrying_spawn`, `retrying`,
   `authoritative_selected`, `blocked_infrastructure_failure` — carries **both** cumulative `quarantined` and
   `spawn_failures`, so no history is erased regardless of interleaving.

8. **Predecessor chain on EVERY terminal record (Codex R1 #5, R2 #3).** `spawn_failures` (each entry
   `{attempt_instance_id, exit_code, unbiased_seconds, sidecar_path, sidecar_sha256}` — Codex R2 #9) is attached to
   whatever the attempt terminates as, from the cumulative claim-level list.

9. **Fingerprint (Codex R1 #7).** `spawn_failures`/`spawn_retry_count` are operational, not in `fingerprint_payload`.
   Each execution already has a distinct fingerprint (UUID in `--out`), as suspend-retries already do; this change also
   alters `supervisor_source_sha256`, so all new fingerprints differ from old. **No cross-attempt fingerprint-equality
   claim or test.**

10. **Per-campaign ledger (Codex R2 #7/#8, R3 #4/#5, R4 #2).** Excluded operational **subtree** under the campaign dir:
    `results/docking/campaign_<id>/_operational/spawn_retry/`, ignored by analysis. **The directory is created once at
    campaign initialization, under `campaign_lock`** — so a legitimate **zero-retry** campaign has an *empty* directory
    (canonical empty-set hash), and thereafter directory **absence is corruption → fail closed** (Codex R4 #2). One file
    per retried claim, named **`sha256(claim_key).json`**, created with **exclusive no-overwrite** semantics, full
    `claim_key` stored and strictly verified inside. Schema-versioned; read-count-write under the already-held
    `campaign_lock`. Any I/O/schema/parse/duplicate inconsistency → **fail closed (abort)**. Over
    `CAMPAIGN_TRANSIENT_SPAWN_BUDGET` distinct claim_keys → abort. The **ledger content hash** is canonical JSON over
    entries sorted by full `claim_key`, excluding `SEALED.json` and filesystem metadata (Codex R4).

10a. **Campaign-completion seal — a real barrier, lock-ordered (Codex R3 #4/#5, R4 #1).** A dedicated seal operation
    runs **after stage 4**, invoked through `run_stage` so a seal failure aborts the script before it prints campaign
    completion (Codex R4). **Lock/check ordering is frozen to close the TOCTOU (Codex R4 #1):**
    - Every docking entry point runs `with campaign_lock(...): require_unsealed(); _run_campaign(...)` — the
      sealed-check happens **inside** the lock, never before it.
    - The sealer acquires **the same `campaign_lock` before reading any manifest or ledger state** and holds it through
      exclusive seal creation.
    Under the lock it: requires and validates **all four** stage manifests (WIDE/TIGHT/SpeB/BORON); verifies **exact
    set-equality** — final ledger claim_keys **==** the union across the four manifests of claims whose terminal record
    has `spawn_retry_count > 0` (zero-retry claims are in neither set); writes `campaign_<id>/_operational/SEALED.json`
    via **exclusive create** with the ledger content hash. **Every downstream entry point — not only
    `compute_statistics` — must require and validate the seal (existence + hash match) before consuming the campaign.**

11. **Consistency gate (Codex R1 #9, R2 #9).** Extend the QC path to incorporate `spawn_failures` like
    `quarantined_predecessors`: assert `spawn_retry_count == len(spawn_failures)`; verify each predecessor by its
    stored **SHA-256** (not cwd-relative existence) and that its sidecar is the allowlisted transient signature; pass an
    explicit **`project_root`** to the generation-time gate; downstream manifest validation recomputes from embedded
    hashes without relying on cwd.

11a. **Run-record schema bump (Codex R3 schema refinement).** `_final_record` **always** emits `spawn_retry_count`
    (default 0) and `spawn_failures` (default `[]`) **before** validation, so "zero retries" is distinguishable from
    omitted metadata on **every** record and disposition. Bump `RUN_SCHEMA_VERSION` and add both to
    `RUN_RECORD_REQUIRED_FIELDS`. Add `spawn_failure_attempts` to the versioned selection-manifest schema, populated on
    every `_selection_manifest` call. `_selection_manifest`'s signature gains the cumulative spawn history alongside
    `quarantined`.

12. **`is_continuable_scientific_disposition` unchanged; scientific taxonomy untouched; no compound skipped.**

13. **ADR-0003** — incident + evidence; allowlist rationale (exit codes ≠ provenance); retry-then-fail-closed; quarantine
    precedence; frozen constants; honest limitation (retry saves momentary, not cumulative desktop-heap exhaustion);
    root-cause deferred. No predicted outcome.

14. **Tests** (mostly additive; the schema bump forces TWO existing edits — Codex R4, correcting rev-1's "additive"
    claim): update `test_docking_timeout.py:119` `RUN_SCHEMA_VERSION == "docking-run-record-v2"` → the new v3 literal,
    and add the two required spawn fields to the manual `_run_record` fixture in
    `test_environment_and_workflow_schema.py:24`. New tests: classifier accepts the sildenafil signature, rejects each
    variant (0xC0000005, 0xC000013A,
    output-present, ≥1 s, threshold-detected suspend, success, genuine small code); **cumulative** budget — 2 spawn
    fails in suspend-iter 1 + 2 in iter 2 ⇒ exhaustion at the claim's 4th (not the iter's), proving state persists
    across `continue`; ≤6 supervisor calls asserted; exhaustion infra record PASSES `validate_run_record(allow_infrastructure=True)`
    and ABORTS; predecessor sidecars retain the transient signature after exhaustion (not overwritten); every selection
    manifest carries cumulative quarantine+spawn history through a suspend-then-transient interleave; supervisor-raises
    inside the helper finalizes infra with a bound context; ledger filename is `sha256(claim_key)`; corrupt/over-budget
    ledger → abort; backoff via injected clock; no real sleeps, no 300 real spawns.

## Key decisions & tradeoffs

- **Cumulative state at claim level** (Codex R2) — the unifying correction; spawn budget and history are per-claim, not
  per-suspend-iteration.
- **Helper owns the whole spawn lifecycle incl. supervisor-raises** (Codex R2 #1/#2) — the honest scope; the outer
  block is unchanged only from line 1169 onward, and the diff must prove it.
- **Exhaustion terminal ≠ predecessor** (Codex R2 #4) — the 4th execution becomes the infra terminal; the 3 prior stay
  immutable allowlisted predecessors for the QC gate.
- **Allowlist, not range** (Codex R1) — integrity fix; ambiguous cases fatal.
- **Ledger sealed by a lock-ordered campaign-completion barrier after stage 4** (Codex R3/R4) — all four manifests,
  exact set-equality, exclusive-create SEALED.json, sealed-check inside the lock; one hash, no cross-stage staleness;
  Windows-safe `sha256(claim_key)` names.

## Risks / open questions

- **The 1097–1169 boundary is the danger zone** — everything before 1169 is relocated into the helper; everything from
  1169 must stay byte-equivalent bar the cumulative-history threading. A regression corrupts suspend/timeout handling.
- **Allowlist may under-cover** — a different transient loader code next time is evidence to add it, logged.
- **Retry ≠ fix for cumulative desktop-heap exhaustion** — retries exhaust, campaign aborts gracefully. ADR-0003.
- **Ledger fail-closed** — corrupt ledger aborts, never resets the budget; tested.

## Out of scope

- Supervisor-raises semantics beyond relocation; frozen timeout/suspend logic, params, calibration schema; making any
  genuine/ambiguous failure retryable; skipping a compound; cross-run resume; desktop-heap root-cause (deferred).

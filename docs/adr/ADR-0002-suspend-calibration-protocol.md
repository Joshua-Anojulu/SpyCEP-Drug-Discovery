# ADR-0002: Pre-campaign suspend-calibration protocol

- Status: Accepted prospective measurement protocol
- Date: 2026-07-17
- Decision owner: Joshua Anojulu
- Artifact schema consumed: `docking-suspend-calibration-v1`

## Context

ADR-0001 changed the schema-v2 docking timeout to a sleep-excluding unbiased-wall basis after a sleep-touched attempt serialized host suspension as a scientific timeout. The existing campaign entry points require a ten-minute awake calibration artifact, but no approved instrument produced it. This ADR records the operator-run producer and the deliberately narrow evidence it supplies.

The measurement-validity constants were approved before calibration data existed. They are not adjusted after observing a run. A failed or indeterminate run is investigated and rerun under the same constants, or changed only by a separately signed amendment.

## Decision

Before a campaign, run the Windows-pinned calibration producer while holding the launcher lock and docking campaign lock. It selects the unique validated wide-workflow azithromycin/state_01/5XYA attempt, constructs the command only through the campaign's Vina command builder with seed 42, exhaustiveness 8, nine modes, and one CPU, and subjects the real Vina process to the existing single armed supervisor wait for a nominal 600 unbiased seconds. Poses are temporary load-generation output and are not scientific records.

The supervisor's opt-in Job accounting returns cumulative user-plus-kernel CPU time after termination and reap while the Job handle remains live. Its enclosing unbiased denominator begins immediately before `ResumeThread` and ends after termination, reap, and accounting. The load floor is `job_cpu_seconds / load_window_unbiased_seconds >= 0.90`; the sustained over-utilization ceiling is separately `job_cpu_seconds / 600.0 <= 1.10`. The enclosing load window must be at least 600 seconds. A deadline timeout establishes only that Vina was unsignaled; the CPU bounds provide the separate evidence that the load was real.

An external sampler persists a ready baseline before the supervisor starts, samples on one-second absolute deadlines without backfilling missed deadlines, and takes a mandatory terminal sample after the supervisor returns. Every sample reads exactly non-precise unbiased, precise unbiased, wall, precise unbiased, non-precise unbiased. The non-precise clock used by the campaign is the gated clock. The precise readings measure lag and cross-check midpoint excursion estimates for each identical sample interval.

The producer gates the maximum observed pairwise positive excursion, an explicit conservative negative-excursion lower bound, clock well-formedness, the precise/non-precise midpoint cross-check, sample count, unbiased intersample gaps, coverage, load validity, and pre/post equality of all seven input hashes. A conservative-bound-only positive crossing is measurement-indeterminate, not a host-drift failure or pass. Only a passing record is self-checked by the existing validator and atomically published at the campaign-specific methods path. Every other emitted record has an explicit failure stage and a schema identity the campaign validator rejects.

Each campaign entry point compares the campaign ID in the record returned by `require_suspend_calibration()` with `require_campaign_id()`. The launcher performs the same check only as an early diagnostic.

## Withdrawn continuity claim

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

No continuity or contiguous-stall guarantee is made. The ceiling catches sustained mean over-utilization only; a brief multi-core excursion can average below it.

## Limitations

**Limitation, stated precisely** _(Codex R2 #10, R3)_: this prevents **cross-campaign-ID reuse**. It does **not**
detect an old artifact with a *matching* ID produced before a host, OS, supervisor, vina or input change. Hashes
are recorded but not enforced. This is **not freshness enforcement**, and the plan does not claim it is.

- **The gate remains forgeable.** §10 binds every executable path to the campaign id, killing cross-ID reuse. It does
  **not** stop a hand-written artifact, nor a stale same-ID one after a host change. Stated, not claimed away.
- **The maximum-observed protocol cannot see between samples** — notably between the sampler's ready baseline and
  `ResumeThread`. Declared, not closed.
- **A pass attests the host was drift-free during *that* 10 minutes**, not across the following ~10–15 h. Inherent to
  any pre-flight; the per-attempt `suspend_gap_seconds` quarantine covers the campaign itself.

## Alternatives considered

- A precise-clock primary gate was rejected because the campaign consumes the non-precise clock.
- A fixed interrupt-tick uncertainty was rejected because the cited Windows range was typical rather than a contractual bound; lag is measured on the host instead.
- An internal accounting sampler and chunked supervisor waits were rejected because they would alter the single-wait scientific supervisor and add a second internal thread solely to support a continuity claim that is not made.
- A synthetic load was rejected in favor of the canonical real Vina invocation with independent aggregate CPU evidence.
- Validator/schema changes for freshness or unforgeability were rejected under the approved provenance scope; the limitations remain explicit.

## Consequences

Campaign launch remains fail-closed until an operator produces a validator-accepted artifact whose campaign ID matches the requested campaign. The calibration producer changes the supervisor source fingerprint deliberately even when Job accounting is disabled; ordinary campaign calls retain the same runtime control flow and do not query Job accounting.

Signed: Joshua Anojulu, 2026-07-17

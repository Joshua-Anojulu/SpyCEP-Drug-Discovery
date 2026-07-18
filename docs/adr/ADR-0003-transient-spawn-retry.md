# ADR-0003: Narrow retry for silent Vina DLL-initialization failure

- Status: Accepted prospective operational amendment
- Date: 2026-07-18
- Decision owner: Joshua Anojulu
- Schema introduced: `docking-run-record-v3`

## Context

During the schema-v2 campaign, WIDE attempt 141/154 for sildenafil created `vina.exe` successfully but returned in approximately 7 ms with `0xC0000142` (`STATUS_DLL_INIT_FAILED`) and empty standard output and error. The same compound subsequently docked in isolation, with a best affinity of -6.296 kcal/mol. This evidence establishes one observed loader-initialization incident; it does not establish a general process-startup classifier or predict the outcome of a new campaign.

Windows process exit codes do not prove provenance. In particular, treating every value at or above `0xC0000000` as a startup failure would also include genuine application crashes such as `0xC0000005` (access violation). Retrying that range could conceal a real Vina failure and compromise campaign integrity.

## Decision

Retry only a returned supervised result satisfying every part of the observed signature: `disposition_basis == "wait_signaled"`; the unsigned exit code is in the frozen allowlist `frozenset({0xC0000142})`; standard output and error are empty; unbiased duration is strictly below 1.0 second and below the attempt timeout; and wall-minus-unbiased duration is strictly below the existing 5.0-second suspend threshold. Suspend or timing quarantine retains precedence. A slow, noisy, ambiguous, successful, or non-allowlisted result is never retried by this mechanism.

The retry budget is three per claim, cumulative across all existing suspend-retry iterations, with fixed backoffs of 2, 5, and 10 seconds. Every execution receives a fresh UUID and immutable attempt directory. Each intercepted execution is persisted as a content-addressed predecessor; the fourth matching execution becomes a validated infrastructure terminal and aborts the campaign without overwriting the first three predecessors. Genuine Vina failures remain fatal under the existing taxonomy, and no compound is skipped.

A campaign-wide operational ledger records the first retried execution for each distinct claim. It uses exclusive files named by `sha256(claim_key)`, stores the full claim key, and aborts on corruption, duplication, or more than ten distinct retried claims. The empty ledger directory is created at campaign initialization so zero retries have a canonical empty-set hash.

After WIDE, TIGHT, SpeB, and BORON complete, a dedicated sealer acquires the same campaign lock before reading any manifest or ledger state. It requires exact equality between ledger claims and terminal manifest claims with `spawn_retry_count > 0`, then exclusively creates `SEALED.json` with the canonical ledger hash. Docking stages check for the seal inside the campaign lock; downstream consumers require the seal and verify its live ledger hash.

## Alternatives considered

- Retrying every severe NTSTATUS was rejected because exit-code severity does not distinguish loader initialization from a genuine crash.
- Retrying noisy or slower failures was rejected because those cases do not match the observed evidence.
- Skipping a compound after retry exhaustion was rejected because it would silently change the analysis population.
- Resetting the retry budget after a suspend quarantine was rejected because it would permit up to nine spawn retries and lose predecessor history.
- A mutable campaign ledger file was rejected in favor of exclusive per-claim entries and a final content hash.

## Consequences and limitations

Schema v3 always records `spawn_retry_count` and `spawn_failures`, including zero values, and the generation-time QC gate verifies every predecessor sidecar by SHA-256 and by the narrow signature. Selection manifests carry both suspend-quarantine and spawn-failure histories on every state transition. Infrastructure terminals are validated with the explicit infrastructure allowance before persistence and still abort normal campaign validation.

This amendment can bridge a momentary recurrence of the exact observed loader failure. It does **not** fix cumulative desktop-heap exhaustion or establish its root cause. A genuinely degrading host will consume the per-claim or per-campaign budget and abort loudly. No campaign outcome is predicted.

Signed: Joshua Anojulu, 2026-07-18

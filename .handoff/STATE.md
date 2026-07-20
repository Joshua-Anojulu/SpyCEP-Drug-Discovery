# Handoff state — SpyCEP Drug Discovery

_Last updated 2026-07-20 by Claude, after completing PLAN-species-exclusion end to end._
_Supersedes `RESUME-campaign3.md`, which is stale (it predates campaign 3 completing)._

## One-paragraph situation

Campaign `v2_20260719` ran to completion and is **sealed and immutable**. The set-level statistics
computed from it were pseudo-replicated; `PLAN-species-exclusion.md` (Codex-APPROVED, round 6) is the
correction, and it is now **complete — all six sections implemented, verified and pushed**. The build
landed as `27a0167` and the §4 manuscript rewrite as `978b456`, both on `remediation-2026-07-13`.
Nothing from that plan is outstanding. **The next move is a fresh read of the manuscript by Josh**,
since the triad framing changed and several headline numbers moved.

## Where things stand

| Item | State |
|---|---|
| Branch | **merged to `master`** 2026-07-20; `master` and `remediation-2026-07-13` both at `1e825fa`, pushed |
| HEAD | `1e825fa` Correct README headline numbers and retire the stale status banner |
| Pre-merge `master` | `0cbc255` — recovery point if the merge ever needs undoing (`git reset --hard 0cbc255`) |
| Campaign | `v2_20260719` sealed 2026-07-19 12:26; `spawn_retry_claim_count` 0 |
| Test suite | 270 passing |
| `compute_statistics.py` | byte-identical on rerun (idempotent) |
| Figures | all four regenerate in one run |
| Manuscript | **updated and cross-checked against `docking_statistics.json`** |

## PLAN-species-exclusion.md progress — COMPLETE

- §1 shared population module (`src/spycep_drug_discovery/analysis_population.py`) — **done**
- §2 `compute_statistics.py` consumes it — **done**
- §3 `make_figures.py` + `write_docking_methods.py` consume it — **done**
- §4 manuscript rewrite — **done** (`978b456`)
- §5 tests (golden + corruption) — **done**
- §6 verify (suite green, idempotent, one-run figures) — **done**

## Corrected numbers (authoritative: `docs/methods/docking_statistics.json`)

Populations: `attempted` 73, `valid_fit` 72, `analysis_eligible` 69 (triad), `numeric_analysis` 68.

- Wide-box triad over 69: **62 / 51 / 31** (≥1, ≥2, all three)
- Tight-box triad over 69: **68 / 56 / 31**
- SpeB primary (ambiguous excluded): 14 decoys, Q9D **rank 2/15** affinity, **4/15** efficiency,
  margin −0.093, fails both metrics
- SpeB sensitivity (dual-state collapsed, lowest-affinity state): 17 decoys, Q9D **4/18** and **7/18**,
  margin −0.231

The positive control still fails. The correction sharpens the null; it does not rescue the pipeline.

## RESOLVED DECISION — triad framing (Josh, 2026-07-20)

The plan flagged this as needing Josh's sight before sign-off, and it was put to him directly.

**Decision: correct the numbers, keep the argument.** §3 now reports 62/51/31 wide and 68/56/31 tight
over the 69-entity denominator, retires the false universal-contact claim, and softens the compact-site
conclusion from "carries no signal" to "carries little signal". The argument survives.

**Also decided: note the amidine chemistry.** Four of the six zero-contact compounds
(4-aminobenzamidine, benzamidine, DCI, caffeine) are 9–14 heavy-atom fragments; the amidines occupy the
S1 specificity pocket rather than the triad, so absent triad contact reflects binding mode and not a
failed pose. This is now stated in §3.

**Deliberately NOT reported — available if wanted.** The arm-level split was computed and is real:
in the wide box 83% of custom versus 94% of FDA contact ≥1 residue (56% vs 82% for ≥2); the tight box
is 100% for both. It would strengthen the null — the rational chemotypes do not engage the triad
preferentially — but it is a **new comparison outside the approved plan**, post-hoc and unpreregistered.
Josh chose to leave it out. Adding it later should go through its own review round.

**Sourcing rule that was followed (from the plan):** no number was hand-edited from an old value.
Analysis numbers came from `docking_statistics.json`, design/method numbers from validated manifests,
the test count from a verified run.

## Constraints that always apply

- Sealed campaign artifacts are **read-only**. Nothing is re-docked.
- Commit as Josh only; **never** add a Co-Authored-By Claude trailer.
- No fabricated compound data. Approval-gated repo.
- Non-trivial changes run the grill → codex-review → codex-build chain. §4 is already covered by the
  approved plan, so it does not need a fresh chain.

## Merge to master (2026-07-20)

`master` was 19 commits behind and still held the pre-remediation study, whose README and abstract
claimed the SpeB control **passed** by 4.4 SD and that this "confirms the SpyCEP result reflects the
target rather than a failure of the method" — the claim the remediation invalidated. That result came
from a box built from Q9D's own coordinates and seven decoys averaging half its heavy-atom count.
Josh chose to fast-forward rather than leave it as the repo default. Recovery point is `0cbc255`.

## Next moves

1. **Josh reads the manuscript fresh.** The triad paragraph, the SpeB results and the abstract all
   changed substantively. This is now the canonical version on `master`, so a disagreement means a
   follow-up commit rather than a blocked merge.
2. Consider whether the arm-level triad split (above) is worth a review round to include.
3. Revert the two AC-only power settings (below) — still owed.
4. Deferred and still open: Codex finding 15 — a bootstrap CI over a fixed curated library is not
   population inference and a non-significant Mann-Whitney is not equivalence. The manuscript now
   states this as a limitation rather than restructuring its inferential framing. Doing it properly
   (equivalence testing, say) would be new statistics on the same sealed data — no re-docking — and
   is a separate decision.

## Stale things to ignore

- `RESUME-campaign3.md` — says "nothing is running" and gives a launch recipe. Campaign 3 already ran.
- `stash@{0}` — pre-timeout-fix WIP `docking_result.json`. Superseded, safe to drop.

## Post-campaign cleanup still owed

Revert the two AC-only power settings changed 2026-07-18 (commands in `RESUME-campaign3.md`).

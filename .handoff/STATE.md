# Handoff state — SpyCEP Drug Discovery

_Last updated 2026-07-20 by Claude, after committing + pushing the species-exclusion build._
_Supersedes `RESUME-campaign3.md`, which is stale (it predates campaign 3 completing)._

## One-paragraph situation

Campaign `v2_20260719` ran to completion and is **sealed and immutable**. The set-level statistics
computed from it were pseudo-replicated; `PLAN-species-exclusion.md` (Codex-APPROVED, round 6) is the
correction, and it is now **implemented, verified and pushed** as commit `27a0167` on
`remediation-2026-07-13`. The only outstanding work from that plan is **§4, the manuscript rewrite**,
which has not been started. One decision is open and is Josh's to make (triad framing, below).

## Where things stand

| Item | State |
|---|---|
| Branch | `remediation-2026-07-13`, pushed, in sync with origin |
| HEAD | `27a0167` Implement entity-level population construction |
| Campaign | `v2_20260719` sealed 2026-07-19 12:26; `spawn_retry_claim_count` 0 |
| Test suite | 270 passing |
| `compute_statistics.py` | byte-identical on rerun (idempotent) |
| Figures | all four regenerate in one run |
| Manuscript | **NOT updated — known-false, see below** |

## PLAN-species-exclusion.md progress

- §1 shared population module (`src/spycep_drug_discovery/analysis_population.py`) — **done**
- §2 `compute_statistics.py` consumes it — **done**
- §3 `make_figures.py` + `write_docking_methods.py` consume it — **done**
- §4 **manuscript rewrite — NOT STARTED**
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

## OPEN DECISION — Josh's call, blocks §4

The plan flags this explicitly: *"Josh should see this before sign-off."*

Manuscript line 59 currently claims **"Every docked compound contacts at least one triad residue
(73 of 73 wide, 72 of 72 tight), and 42 of 73 contact all three."** Under correct affinity-best-receptor
counting this is **false**: wide is 62 of 69 (90%), tight 68 of 69 (99%), and all-three is 31 of 69
(45%) in both boxes — not 42/47.

The "triad contact does not discriminate" argument partly rested on contact being *universal*. It no
longer is in the wide box, and the all-three rate is now under half. The conclusion probably survives
on the compact-site reasoning, but the sentence and possibly the argument need rewriting, and that is
a scientific framing choice, not a mechanical number swap.

## §4 known-false manuscript claims (from the plan)

- **Abstract** — "6th of 20 / 7th of 20"; p = 0.32/0.26; the claim that every ligand is docked as its
  dominant microspecies (four are not). "55 comparators" and "17 decoys" stay, but qualified.
- **§2.3** — must name the four excluded entities (cephalexin, ampicillin, amoxicillin, lisinopril),
  the pKₐ rationale and the exclusion rule.
- **§2.4** — vancomycin exhausts the 1800 s ceiling against **both** boxes; the earlier wide-box pose
  was accepted past the ceiling under a suspend-extensible timeout and is superseded.
- **§2.6** — still implies 17 decoys are the primary analysis (primary is now 14).
- **§2.7** — claims best-receptor triad counting the code did not implement.
- **§3** — docked counts, means, CIs, p-values, triad counts, "67th of 73" (benzamidine re-ranks to
  63/68), and the unsupported historical "55–56 was a 146-row pose count" claim.
- **Discussion** — "Q9D trails two β-lactams" holds only in the sensitivity analysis.
- **Limitations** — vancomycin absent from **both** comparisons; "77 compounds and one pose each" false.
  Line 86's "does not fit the 16 Å triad box" is wrong — it exhausts the ceiling in both boxes.

**Sourcing rule (from the plan):** no number may be hand-edited from old values. Analysis numbers come
from `docking_statistics.json`, design/method numbers from validated manifests, test count from a
verified run.

## Constraints that always apply

- Sealed campaign artifacts are **read-only**. Nothing is re-docked.
- Commit as Josh only; **never** add a Co-Authored-By Claude trailer.
- No fabricated compound data. Approval-gated repo.
- Non-trivial changes run the grill → codex-review → codex-build chain. §4 is already covered by the
  approved plan, so it does not need a fresh chain.

## Stale things to ignore

- `RESUME-campaign3.md` — says "nothing is running" and gives a launch recipe. Campaign 3 already ran.
- `stash@{0}` — pre-timeout-fix WIP `docking_result.json`. Superseded, safe to drop.

## Post-campaign cleanup still owed

Revert the two AC-only power settings changed 2026-07-18 (commands in `RESUME-campaign3.md`).

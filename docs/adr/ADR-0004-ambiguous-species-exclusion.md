# ADR-0004: Exclude ambiguous-protonation entities from set-level statistics

- Status: Accepted
- Date: 2026-07-20 (amended same day after cross-model review)
- Decision owner: Joshua Anojulu
- Applies to: `src/spycep_drug_discovery/analysis_population.py` (shared population module),
  `scripts/compute_statistics.py`, `scripts/make_figures.py`, `scripts/write_docking_methods.py`,
  `docs/methods/docking_statistics.json`, `docs/methods/docking_analysis.md`,
  `docs/manuscript/spycep_insilico_screen.md`
- Terms: per `CONTEXT.md`

## Context

Run-record schema v3 introduced dual-state docking for ambiguous protonation. Four entities carry
a contested ionisable site whose pKₐ lies within roughly 0.3 units of 7.4, and the species catalog
marks them `tier: AMBIGUOUS` with `hard_state_cap_per_entity: 2`:

| Entity | States | Set |
|---|---|---|
| cephalexin | `alpha_amine_neutral`, `alpha_ammonium` | fda_comparator |
| ampicillin | `alpha_amine_neutral`, `alpha_ammonium` | fda_comparator |
| amoxicillin | `alpha_amine_neutral`, `alpha_ammonium` | fda_comparator |
| lisinopril | `secondary_amine_neutral`, `secondary_amine_protonated` | fda_comparator |

The catalog's `method_status` is `authoritative_preregistered_species_hypotheses_no_abundance_fractions`,
and each entity's hand-reviewed adjudication states that neither site-resolved form is established
as dominant, so both are docked and no abundance claim is made. Lisinopril's own citation reports
speciation fractions (65.04% / 34.93%); the project deliberately declines to weight by them.

`compute_statistics.py` counted **ranking rows**, not entities. Every ambiguous entity therefore
contributed two observations: ranking 76 rows over 72 entities, `fda_n` 58 over 54, SpeB decoys
20 rows over 17 compounds. The Mann-Whitney U and bootstrap CI were computed on pseudo-replicated
data, violating the independence both tests assume.

The same defect appeared a second time in `_triad_engagement`, whose `any()` was written to mean
"best receptor" and silently became "best receptor **or** best state". The two states genuinely
disagree: amoxicillin and ampicillin each classify as contacting all three triad residues under
one state but not the other in the wide box, as do all three β-lactams in the tight box.

All four ambiguous entities are FDA comparators. None are custom. Any per-entity selection rule
therefore perturbs exactly one arm of the study's central comparison.

## Decision

**Exclude ambiguous entities from all set-level statistics.** An entity contributing more than one
site-resolved state is removed from the custom-versus-FDA comparison, from triad-engagement counts,
and from the SpeB decoy population.

Ambiguity is assigned from pKₐ before docking and is therefore independent of the *outcome*. It is
**not**, however, unbiased in general: the criterion is chemistry-dependent, removes four FDA
entities and no custom ones, and changes the estimand. The primary result is therefore named
explicitly as a **valid-fit, single-state custom-versus-FDA estimand** — conditional both on being
single-state and on obtaining a valid fit. A **16-assignment sensitivity** (2⁴ one-state-per-entity
choices, effect size and p-range for both metrics under both boxes) covers the full valid-fit
comparator population of 54 and is what licenses the robustness claim.

The exclusion is **derived from state multiplicity in `attempt_manifest.json`**, not from a name list
and not from result manifests, whose ambiguous membership varies by stage (wide/tight 4, SpeB 3,
boron 0) and whose successful rows are outcome-dependent. The derived set is cross-checked against
the **global** dock-eligible `tier == "AMBIGUOUS"` catalog set once, then intersected with each
workflow roster. Catalog and attempt-manifest SHA-256 are verified by hashing raw bytes before
parsing. Disagreement is fatal. Any future ambiguous compound is covered automatically.

After exclusion every remaining entity is single-state, which removes the *state* dimension of the
`_triad_engagement` defect. It does **not** by itself fix the *receptor* dimension: `any()` means
"contacts in either receptor", whereas the documented method is the affinity-best receptor. Both
dimensions are corrected — best-receptor selection with an explicit tie rule, never `any()`.

The fail-closed assertion operates at **claim** granularity, not entity: an ordinary entity has two
terminal receptor claims and an ambiguous one has four, so a one-row-per-entity rule is false on
valid manifests. It requires one terminal run record per expected claim, one ranking row per species
with any valid receptor result, and one row per entity only in the final single-state numeric
population.

**The SpeB control additionally reports a sensitivity check** collapsing dual-state decoys to
best-affinity per compound (17 decoys), alongside the primary 14-decoy exclusion.

## Alternatives considered

- **Mean of the two states** was rejected because averaging implies 50:50 occupancy, which is an
  abundance claim the preregistration forbids.
- **Dominant-species selection** was rejected because it requires naming one form dominant, which
  contradicts the recorded adjudication verbatim.
- **Best-affinity state per entity** was rejected for the custom-versus-FDA comparison because
  max-of-two is upward-biased by construction and would apply only to the FDA arm — manufacturing a
  small amount of exactly the separation the study reports not finding.
- **Excluding the ambiguous decoys with no sensitivity check** was rejected because it drops
  amoxicillin at -7.037, the single strongest decoy and the clearest evidence of the pipeline
  failing, softening the study's central cautionary claim for a reason unrelated to what makes a
  good decoy. Q9D ranks **2nd of 15 under the primary exclusion versus 4th of 18 under the
  entity-collapsed sensitivity**.

  _Correction: an earlier draft of this ADR argued the point as "4th of 21 to 2nd of 15". That
  compared a pseudo-replicated denominator (20 decoy **rows** plus Q9D) against a clean one — the
  exact defect this ADR exists to document. The entity-level sensitivity denominator is 18._
- **A per-role rule** — exclusion for the comparison, best-of-two for the control, on the grounds
  that best-of-two only ever makes the control harder — was rejected as primary because two
  different rules invite a tuning objection that a single uniform rule forecloses. It survives as
  the reported sensitivity check.

## Consequences and limitations

The FDA arm falls from 54 to 50 entities and the custom arm is unchanged at 18. Populations are
reported at four distinct sizes and never conflated: attempted 73, valid-fit 72, analysis-eligible
69, numeric-analysis 68. **Triad statistics use the 69-entity analysis-eligible population**, which
includes vancomycin as a zero-contact non-fit per the `CONTEXT.md` rule that a non-fit is an outcome
rather than missing data; means and tests use the 68-entity numeric population.

Triad counting is additionally corrected to select each entity's **affinity-best receptor**, the
method the manuscript already claimed, rather than `any()` across receptors. This changes a reported
result: wide-box contact with at least one triad residue is **62 of 69**, not universal.

The four excluded entities are named in methods with the pKₐ rationale, and their
per-state results are retained in the deposited manifests. The sealed campaign data is not modified
— exclusion happens at analysis time only.

Excluding four real comparators costs a small amount of power in a comparison already stated to be
underpowered. The study's conclusions are unchanged in both directions: the custom set does not
separate from the FDA set, and the pipeline does not recover Q9D under either the 14-decoy primary
or the 17-decoy sensitivity treatment.

This ADR governs statistical population construction only. It makes no claim about which protonation
state is physiologically dominant, and it does not license inferring ambiguity from docking results.

Signed: Joshua Anojulu, 2026-07-20

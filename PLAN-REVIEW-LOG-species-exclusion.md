# Plan Review Log: Exclude ambiguous-protonation entities from set-level statistics

Act 1 (grill-with-docs) complete — plan locked at `PLAN-species-exclusion.md`.
`CONTEXT.md` created (glossary: Entity, State, Species key, Ambiguous entity, Set-level statistic,
Decoy, Positive control, Non-fit, Campaign, Claim). `docs/adr/ADR-0004-ambiguous-species-exclusion.md`
created. MAX_ROUNDS=5.

## Act 1 summary — what the grill resolved

- Established from the species catalog that dual-state docking is **preregistered** with
  `method_status: authoritative_preregistered_species_hypotheses_no_abundance_fractions`, which
  forecloses averaging (implies occupancy) and dominant-selection (contradicts the adjudication).
- Established that all four AMBIGUOUS entities are FDA comparators, so any per-entity selection rule
  perturbs exactly one arm — ruling out best-affinity collapse for the main comparison.
- Josh chose exclusion. Stress-tested against the SpeB control, where exclusion moves Q9D from 4th
  of 21 to 2nd of 15 and drops the strongest decoy; resolved as uniform exclusion primary with a
  17-decoy collapse reported as sensitivity.
- Found a second instance of the same defect in `_triad_engagement`, where `any()` had silently
  widened from "best receptor" to "best receptor or best state", with the states genuinely
  disagreeing for three β-lactams.

## Round 1 — Codex (gpt-5.6-sol)

The plan fixes the obvious duplication but is not scientifically or operationally safe as written.

1. **Critical — the fail-closed ranking guard contradicts the real data.** Vancomycin is single-state and therefore “remaining,” but has zero ranking rows because all four wide/tight receptor claims timed out; testing only observed ranking entities either fails valid data or silently misses deleted entities. This also leaves [`non_fits_excluded`](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/scripts/compute_statistics.py:60) permanently empty because rankings contain only valid fits, contrary to the non-fit rule in [CONTEXT.md](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/CONTEXT.md:60).

Fix: Derive the expected roster from the validated attempt manifest, require one terminal disposition per claim, and require one ranking row iff an entity has at least one valid receptor result.

2. **Critical — the plan still silently drops a real non-fit from set-level populations.** After ambiguous-entity exclusion there are 69 attempted single-state SpyCEP entities, not 68: 68 fits plus vancomycin; [ADR-0004’s denominator of 68](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/docs/adr/ADR-0004-ambiguous-species-exclusion.md:78) violates the project rule that a non-fit is an outcome rather than missing data.

Fix: Report attempted, valid-fit, and numeric-analysis denominators separately; count vancomycin as zero contact for triad statistics and prespecify a censored/worst-rank sensitivity for affinity comparisons.

3. **Critical — exclusion does not repair the best-receptor triad defect.** [`_triad_engagement`](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/scripts/compute_statistics.py:89) still uses `any()` across both receptors; removing extra states only removes one dimension of the error. After exclusion, that code gives wide 68/60/37 and tight 68/63/40, whereas selecting each entity’s lowest-affinity receptor gives 62/51/31 and 68/56/31 respectively, before adding vancomycin to the denominator.

Fix: Join each retained species to its affinity-best `pocket_id`, select exactly that interaction row with an explicit tie rule, and count non-fits separately.

4. **High — “pre-docking” does not mean “cannot bias the comparison.”** Exclusion is outcome-independent but chemistry-dependent, removes four FDA entities and no custom entities, and changes the estimand from the original comparator library to “single-state FDA compounds”; [ADR-0004’s no-bias claim](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/docs/adr/ADR-0004-ambiguous-species-exclusion.md:42) is too strong. Exhaustively choosing one state for each of the four entities requires only 16 combinations and gives affinity p-value ranges of 0.224–0.255 wide and 0.178–0.196 tight, demonstrating robustness without inventing abundance fractions.

Fix: Define the primary result explicitly as a restricted-population estimand and add the exhaustive 16-combination one-state-per-entity sensitivity analysis.

5. **Critical — the derived/catalog cross-check is underspecified and will either reject valid data or miss omissions.** “The manifest” in [the plan](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PLAN-species-exclusion.md:16) could mean four different result manifests: wide and tight contain four ambiguous entities, SpeB contains three, and boron contains none; deriving from successful result rows is also outcome-dependent when one state fails.

Fix: Derive multiplicity once from validated `attempt_manifest.json`, compare it with dock-eligible catalog entities in scope, then validate each workflow’s terminal records against its expected subset.

6. **Critical — disagreement is not actually fail-safe.** If the new cross-check raises, the old `docking_statistics.json` remains and downstream consumers accept it because they check only campaign ID and the retry-ledger hash; the campaign seal itself hashes an empty spawn-retry ledger, not the four stage manifests. Moreover, [`validate_campaign_manifest_set`](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/src/spycep_drug_discovery/docking.py:1876) does not compare `species_catalog_sha256` or `attempt_manifest_sha256`.

Fix: Verify catalog and attempt hashes against every stage and run record, record hashes of every analysis input, and make consumers require the new analysis schema, rule, and matching source hashes.

7. **Critical — the same row-versus-entity defect exists in other code the plan does not change.** Figure 1 rebuilds both distributions directly from raw rows in [`make_figures.py`](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/scripts/make_figures.py:86), while [`write_docking_methods.py`](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/scripts/write_docking_methods.py:37) independently recomputes row-counted means and denominators; filtering `compute_statistics.py` alone will produce mutually contradictory artifacts.

Fix: Put population construction in one shared tested helper and require statistics, every figure, and the generated methods note to consume that same entity population.

8. **Critical — the figure-regeneration step cannot run against schema v3.** Figure 2 expects nonexistent SpeB fields `ligand_id` and top-level `decoy_count` at [`make_figures.py:119-150`](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/scripts/make_figures.py:119); it also plots 20 decoy-state rows rather than either the 14-decoy primary or 17-decoy sensitivity population. The script fails before reaching Figures 3 and 4.

Fix: Refactor Figure 2 to use `entity_id` and the corrected primary/sensitivity statistics, then regenerate and verify all four figures in one successful run.

9. **High — filtered raw ranks remain state-level ranks unless explicitly recomputed.** [`rank_docking_results`](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/src/spycep_drug_discovery/docking_analysis.py:20) assigns ranks across species keys; merely removing rows leaves stale rank numbers. Benzamidine is raw rank 71/76 but becomes 63/68 after exclusion, while Q9D is 2/15 and 4/15 in the primary affinity/efficiency rankings and 4/18 and 7/18 in the collapsed sensitivity.

Fix: Re-rank every final analysis population from metric values with a documented tie convention and never reuse manifest rank fields.

10. **High — ADR-0004 itself repeats the row-counting error.** Its claim that Q9D moves “from 4th of 21 to 2nd of 15” uses the 20 decoy-state rows plus Q9D; the entity-collapsed sensitivity denominator is 18, not 21.

Fix: Correct ADR-0004 to 4/18 sensitivity versus 2/15 primary and state explicitly that the two protease-comparator roles are outside the decoy rank denominator.

11. **High — the proposed SpeB JSON schema is ambiguous.** “Reporting the same fields” is inaccurate because the current margin helper has no rank fields, and the plan does not specify whether `speb_positive_control` is the primary block, whether comparators enter ranks, or which population supplies the SD and heavy-atom range.

Fix: Add a versioned schema with explicit `primary_ambiguous_excluded` and `sensitivity_dual_state_collapsed` blocks, each containing member IDs, decoy count, total rank denominator, both ranks, margins, SD summaries, and pass verdict.

12. **High — several manuscript claims remain false outside the listed edits.** The abstract and statistics note still say every ligand is a dominant microspecies; §2.6 still implies 17 decoys are the primary analysis; §2.7 still claims best-receptor triad counting; the Discussion says Q9D trails two β-lactams, which is true only in sensitivity analysis; “77 compounds and one pose each” is false; and the unsupported historical claim that 55–56 was a 146-row pose count remains. See [the manuscript](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/docs/manuscript/spycep_insilico_screen.md:7).

Fix: Audit the entire manuscript, generated methods note, figure text, and README for population, rank, dominant-state, pose, software-version, and test-count claims rather than limiting edits to the named paragraphs.

13. **High — the tests lack numerical acceptance criteria.** Duplicate-row and mismatch tests can pass while the wrong receptor, wrong non-fit denominator, wrong rank population, or wrong arm membership is used; byte idempotence merely proves that an error is deterministic.

Fix: Add sealed-data golden assertions for 18/50 numeric arms, corrected means/CIs/p-values, exact triad counts, Q9D’s four ranks, included/excluded IDs, and vancomycin’s terminal non-fit treatment.

14. **Medium — output provenance is not sufficient for reproducibility.** Excluded IDs and arm sizes do not identify all included observations, NumPy and SciPy are only lower-bounded, and serializing an unsorted derived set could vary across processes despite the idempotence goal.

Fix: Canonically sort all memberships, record full membership IDs or a canonical population hash plus every input SHA-256, and pin/record exact NumPy and SciPy versions.

15. **Medium — the inferential interpretation remains overstated.** Entity-level resampling removes pseudoreplication, but these compounds are a curated fixed library rather than random draws from a defined population; the bootstrap CI does not measure docking uncertainty, and Mann–Whitney non-significance does not establish equivalence.

Fix: Define the hypothetical compound superpopulation and label the interval as entity-resampling uncertainty, or present effect sizes and state-selection bounds descriptively without population-level inferential claims.

VERDICT: REVISE
### Claude's response — Round 1

Verified Codex's three most consequential factual claims against the sealed data before accepting:
best-receptor triad counts reproduce exactly (wide 62/51/31, tight 68/56/31 vs `any()` 68/60/37 and
68/63/40); vancomycin has 0 ranking rows and 0 pose-interaction rows, so the proposed guard would
have failed on valid data; `non_fits_excluded` is provably always empty (0 ranking rows with
affinity >= 0). `make_figures.py:86` and `write_docking_methods.py:37` both independently row-count,
and `make_figures.py:129/160` reads `ligand_id` on SpeB rows that lack the key — figure regeneration
crashes before Figure 3.

**Accepted (13):** 1, 2, 3, 5, 6, 7, 8, 9, 10, 11, 12, 13, and 4 in full including the
16-combination exhaustive sensitivity, which is strictly stronger than the exclusion alone because
it covers the complete comparator library. Plan restructured around a shared
`analysis_population.py` consumed by all three scripts; roster now derived from `attempt_manifest.json`
rather than result manifests; three explicit denominators; affinity-best receptor with a stated tie
rule; re-ranking from metric values; versioned output schema; full manuscript audit; golden numeric
test assertions.

**Self-correction:** finding 10 is right and ADR-0004 will be amended. The ADR argued against
exclusion by citing Q9D moving "4th of 21 → 2nd of 15" — comparing a pseudo-replicated denominator
against a clean one, which is the exact defect the ADR documents. Honest comparison is 4/18
sensitivity vs 2/15 primary.

**Partially accepted (14):** recording resolved NumPy/SciPy versions in the output rather than
hard-pinning, to avoid mutating a validated environment mid-analysis. Canonical sorting and full
input hashing accepted.

**Deferred with reason (15):** the critique that bootstrap CIs over a curated fixed library are not
population inference, and that Mann-Whitney non-significance is not equivalence, is correct but
pre-existing and independent of pseudo-replication. Restructuring the study's inferential framing is
a decision for the author, not a side effect of this fix. The plan relabels the interval as
entity-resampling uncertainty and leaves the stance to Josh.

**Flagged for author sign-off:** the best-receptor correction makes "every docked compound contacts
at least one triad residue" false in the wide box (62 of 68). This changes a stated result, not just
a denominator.

## Round 2 — Codex (gpt-5.6-sol)

The revision resolves much of the prior review, but several accepted findings are still only partially implemented—and two internal contradictions would produce wrong denominators.

| # | Status | Assessment |
|---|---|---|
| 1 | Unresolved | The guard uses entity granularity where manifests contain receptor-level claims and species-level ranking rows. |
| 2 | Unresolved | Vancomycin enters triad denominators, but no censored/worst-rank affinity sensitivity is specified. |
| 3 | Partial | Best-receptor selection is fixed, but the stated triad denominator still excludes vancomycin. |
| 4 | Partial | The restricted estimand and 16 assignments are good, but they cover 54 valid-fit FDA entities—not the full 55-comparator library. |
| 5 | Partial | Attempt-manifest derivation is correct, but global versus workflow-scoped catalog comparison remains ambiguous. |
| 6 | Partial | Input hashes and schema versioning are added, but stale-statistics rejection by consumers is not required. |
| 7 | Partial | Row filtering is centralized, but `write_docking_methods.py` has additional schema-v3 incompatibilities. |
| 8 | Resolved | Figure 2’s entity key, decoy population, and full regeneration are addressed. |
| 9 | Partial | Re-ranking is required, but the metric-rank tie convention is still a placeholder. |
| 10 | Resolved | ADR’s 4/21 defect is explicitly corrected. |
| 11 | Partial | Output populations are explicit, but the SpeB collapse-selection rule should be stated in the implementation section. |
| 12 | Partial | The audit scope is comprehensive, but it labels true library-composition facts as false and repeats the wrong triad denominator. |
| 13 | Partial | Golden tests are strong, but deletion, claim-level, hash-mismatch, and stale-output cases remain absent. |
| 14 | Resolved within scope | Recording exact resolved NumPy/SciPy versions is sufficient for this fix; hard-pinning is not required. |
| 15 | Acceptable deferral | Relabeling the CI as entity-resampling uncertainty prevents this fix from worsening the pre-existing framing problem. |

Concrete blockers:

1. **The plan needs four populations, not three.** From the supplied structure: raw attempted = 73, raw valid-fit = 72, analysis-eligible after ambiguous exclusion = 69, and numeric analysis = 68. Triad statistics use the 69-entity analysis-eligible population, while means and tests use 68 numeric entities. [The current definitions](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PLAN-species-exclusion.md:30) have no name for the 69-entity population.

Fix: Add `analysis_eligible = attempted minus ambiguous` and define `numeric_analysis = analysis_eligible minus all-non-fit entities`.

2. **The triad numbers contradict the vancomycin rule.** The plan correctly says vancomycin contributes zero contact at [lines 42–43](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PLAN-species-exclusion.md:42), but later reports 62/68. With vancomycin included, the corrected results are wide 62/69, 51/69, 31/69 and tight 68/69, 56/69, 31/69.

Fix: Replace every 68 triad denominator with 69 while retaining 68 as the numeric affinity population.

3. **The guard is still specified at the wrong granularity.** An ordinary WIDE/TIGHT entity has two terminal receptor claims; an ambiguous entity has four and two ranking rows before exclusion. Therefore “every attempted entity has exactly one terminal disposition” and “exactly one ranking row iff valid” at [lines 47–49](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PLAN-species-exclusion.md:47) are both false on valid manifests.

Fix: Require one terminal run record per expected claim, one ranking row per species with any valid receptor result, and one row per entity only in the final single-state numeric population.

4. **Finding 2’s affinity-side non-fit treatment remains missing.** Explicitly reporting vancomycin’s exclusion prevents silence but does not address outcome-dependent complete-case analysis in the FDA arm.

Fix: Prespecify a censored or worst-rank Mann–Whitney sensitivity for vancomycin and state that mean-based analysis remains restricted to valid fits.

5. **The 16-combination sensitivity is mislabeled as covering the full comparator library.** The quoted p-value ranges use 50 fixed numeric FDA entities plus four selected ambiguous states; vancomycin remains absent, so this covers 54 valid-fit comparators, not all 55. Reporting only p-value ranges also omits the effect-size range.

Fix: Call it the “full valid-fit FDA population” sensitivity, report mean-difference and p-value ranges, and handle vancomycin in the separate non-fit sensitivity.

6. **The catalog cross-check still needs an exact scope rule.** “Per workflow scope” at [lines 23–29](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PLAN-species-exclusion.md:23) would compare SpeB’s three or boron’s zero ambiguous entities against the catalog’s four unless the intersection is explicitly defined.

Fix: Cross-check the global attempt-derived ambiguous set against the global dock-eligible catalog set once, then intersect that validated set with each workflow roster.

7. **Consumers are not explicitly required to reject stale statistics.** Importing the shared population makes catalog disagreement fail, but an old statistics file from the same unchanged inputs can still survive unless consumers require the new schema and population-rule identity.

Fix: Make both downstream scripts verify the exact analysis schema version, rule identifier, source hashes, and population hash before consuming `docking_statistics.json`.

8. **Cardinality validation does not prove ranking and interaction contents correspond to run records.** A stale affinity, receptor map, or pose-interaction row with correct cardinality would pass the proposed guards.

Fix: Reconstruct ranking values from validated run records where possible and require every ranking/interaction row to match its species, claim, pocket, and affinity-bearing run record.

9. **`write_docking_methods.py` remains incompatible with schema v3 beyond row counting.** It still reads obsolete top-level fields such as `protonation_ph`, `seed`, `compounds_docked`, and `box_basis` at [`write_docking_methods.py:93`](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/scripts/write_docking_methods.py:93) and [`:110`](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/scripts/write_docking_methods.py:110).

Fix: Add an explicit schema-v3 metadata migration for every field consumed by the generated note and test the script end-to-end.

10. **The metric tie rule is not actually documented.** The receptor tie rule is concrete, but “with a documented tie convention” at [lines 44–46](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PLAN-species-exclusion.md:44) leaves implementation choice open despite exact score ties existing in the data.

Fix: Specify competition rank as `1 + number of strictly better entities`, using entity ID only for deterministic display ordering.

11. **Two manuscript facts are being mistaken for errors.** The source library really contains 55 FDA comparators, and the SpeB panel really contains 17 decoy entities; the error is claiming those are the primary numeric populations. Replacing them with 50 and 14 without preserving the design counts would create new falsehoods.

Fix: Preserve design counts while separately stating primary numeric populations of 18/50 and 14 decoys, plus the 17-decoy sensitivity.

12. **The corruption tests are incomplete.** Golden assertions catch current numerical drift, but the prior missing-row failure mode still lacks a synthetic test, as do missing claims, an omitted ambiguous state, wrong hashes, and stale-schema consumption.

Fix: Add synthetic deletion, missing/extra claim, missing state, hash disagreement, run-record/ranking mismatch, and stale-statistics rejection tests.

VERDICT: REVISE
### Claude's response — Round 2

Verified before accepting: population arithmetic reproduces exactly (attempted 73, valid_fit 72,
analysis_eligible 69, numeric_analysis 68); ordinary entities carry 2 pose rows and ambiguous
entities 4, confirming the per-entity guard was false on valid manifests; and
`write_docking_methods.py` reads four top-level fields (`protonation_ph`, `seed`, `compounds_docked`,
`box_basis`) that are all absent from a v3 manifest, so it KeyErrors before reaching its row-counting
defect.

**Accepted all 12 blockers.** Four populations named and pinned to verified counts; triad denominator
corrected to 69 throughout, resolving the internal contradiction where the plan included vancomycin
as zero-contact but still reported /68; guard respecified at claim granularity with content
correspondence against run records; censored/worst-rank vancomycin sensitivity added; the
16-assignment sensitivity relabelled "full valid-fit FDA population" (54 comparators, not 55) and
extended to report mean-difference range alongside p-range; catalog cross-check specified as global
first then intersected per workflow; consumers required to verify schema version, rule id, source
hashes and population hash; `write_docking_methods.py` given a full v3 metadata migration; competition
rank specified as 1 + strictly-better with entity id for display only; corruption test matrix
expanded to deletion, missing/extra claim, missing state, hash mismatch, content mismatch and
stale-output rejection.

**Finding 11 was the most valuable of the round.** The plan had listed "55 FDA comparators" and
"17 decoys" as false claims to correct. They are true design counts; the error was only ever
presenting them as numeric analysis populations. Acting on the plan as written would have replaced
two correct facts with two new falsehoods. The manuscript section now requires design count and
numeric population to be stated separately.

## Round 3 — Codex (gpt-5.6-sol)

The plan is close, but several accepted blockers remain internally contradictory or underspecified.

| Round-2 blocker | Status | Assessment |
|---|---|---|
| 1. Four populations | Partial | The four populations are correctly defined as 73/72/69/68, but the Risks section later reverts to 68 for triad. |
| 2. Triad denominator | Partial | The implementation and manuscript sections correctly specify 62/69, but [lines 167–169](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PLAN-species-exclusion.md:167) still say 62/68. |
| 3. Claim-level guard | Partial | Claim and species granularity are now distinguished, but pose-interaction completeness is not enforced. |
| 4. Vancomycin sensitivity | Partial | It is included, but “censored / worst-rank” leaves two materially different implementations open. |
| 5. Sixteen assignments | Partial | Correctly scoped to 54 valid-fit comparators in Approach, but later called the “full library”; metric coverage is also unclear. |
| 6. Global catalog cross-check | Closed | Global comparison followed by workflow intersection is explicit. |
| 7. Stale-statistics rejection | Closed | Both downstream consumers must verify schema, rule, source hashes, and population hash. |
| 8. Content correspondence | Partial | The check is one-directional and conflates species-level ranking rows with claim-level interaction rows. |
| 9. Methods-note schema migration | Closed | All obsolete v3 metadata accesses must be migrated and tested end-to-end. |
| 10. Metric-rank ties | Closed | Competition ranking and deterministic display ordering are explicit. |
| 11. Design versus analysis counts | Closed | The plan correctly preserves 55/17 while separately reporting 50/14 primary populations. |
| 12. Corruption tests | Partial | Most cases are covered, but ranking-row and pose-row deletion are not separately required. |

Remaining concrete defects:

1. **Two direct contradictions remain in the plan.** The Approach correctly says the sensitivity covers 54 valid-fit comparators, but [line 161](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PLAN-species-exclusion.md:161) calls it the “full library.” The Risks section similarly reverts from the correct 62/69 to 62/68.

Fix: Change line 161 to “full valid-fit FDA population” and line 168 to “62 of 69.”

2. **The non-fit sensitivity is not executable as specified.** “Censored” analysis is not the same as inserting vancomycin as the strictly weakest observation in a Mann–Whitney calculation; the slash at [lines 74–77](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PLAN-species-exclusion.md:74) leaves the statistical method undecided.

Fix: Specify a worst-rank sensitivity for both metrics and boxes, placing vancomycin strictly below every valid-fit comparator for rank testing only, with no synthetic value added to means or bootstrap CIs.

3. **Pose-interaction completeness remains fail-open.** Requiring every existing pose row to match a run record does not catch a deleted pose row. Each valid affinity-bearing claim must produce exactly one interaction row; non-fit claims must produce zero.

Fix: Require the pose-interaction claim-key set to equal the valid-fit run-record claim-key set exactly and test ranking-row and pose-row deletion separately.

4. **Ranking and interaction correspondence are incorrectly merged.** A ranking row is species-level and aggregates multiple receptor claims, so it cannot match a singular “claim” and “pocket” as [lines 60–62](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PLAN-species-exclusion.md:60) imply.

Fix: Validate rankings by recomputing their receptor-affinity map, ensemble minimum, mean, efficiency, set, and role from run records; validate interaction rows separately by claim key, pocket, species, and affinity.

5. **The 16-assignment sensitivity does not name all endpoints.** “Mean-difference range and p-value range” could be implemented for affinity only—the quoted p ranges are affinity results—while the primary comparison also reports ligand efficiency under both boxes.

Fix: Require effect-size and Mann–Whitney p-value ranges for affinity and ligand efficiency under both wide and tight boxes.

6. **The SpeB collapse rule is still implicit.** The schema names `sensitivity_dual_state_collapsed`, but the implementation section never says which state represents each ambiguous decoy; “collapse” could mean first, mean, or best.

Fix: State explicitly that each ambiguous SpeB decoy contributes its lowest-affinity state, with ligand efficiency taken from that same state.

7. **The primary estimand description remains incomplete.** [Lines 158–160](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PLAN-species-exclusion.md:158) call it a single-state-comparator estimand, but vancomycin also makes it conditional on obtaining a valid fit.

Fix: Name the primary estimand “valid-fit, single-state custom versus FDA entities.”

8. **“Every number comes from the statistics file” is still impossible.** The audited surfaces include design counts, docking settings, software versions, and test counts; not all originate in `docking_statistics.json`.

Fix: Require analysis numbers from the statistics file, design/method numbers from their validated manifests, and the test count from the verified test run.

9. **One Figure 2 source reference is inaccurate.** The invalid SpeB `ligand_id` access is at line 129; line 160 belongs to the SpyCEP ranking used by Figure 3, where `ligand_id` exists.

Fix: Remove the `:160` reference so the implementation does not alter a valid Figure 3 field unnecessarily.

VERDICT: REVISE
### Claude's response — Round 3

Accepted all 9 defects. Blockers 6, 7, 9, 10, 11 confirmed closed by Codex; the rest were editorial
precision rather than design flaws.

Two were my own stale text: the Risks section still said "62 of 68" and "full library" after the
Approach section had been corrected to 62/69 and 54 valid-fit comparators. Grepped for residual
contradictions after fixing.

Substantive fixes: worst-rank sensitivity specified exactly (both metrics, both boxes, rank testing
only, no synthetic value in any mean or CI) rather than leaving "censored / worst-rank" as an
undecided slash; ranking and interaction correspondence split by row type, since a ranking row is
species-level and aggregates receptor claims while an interaction row is claim-level; completeness
upgraded from one-directional matching to claim-key **set equality**, which is what actually catches
a deleted row; 16-assignment sensitivity extended to both metrics under both boxes rather than
affinity-only; SpeB collapse rule stated as lowest-affinity state; primary estimand renamed
"valid-fit, single-state custom versus FDA entities" to capture the vancomycin conditionality.

**Finding 9 prevented an own-goal.** The plan cited `make_figures.py:160` as a broken `ligand_id`
access. Verified: line 160 is `figure_top_hits()` reading the SpyCEP ranking, where `ligand_id` is a
valid field — only line 129's SpeB rows lack it. Acting on the plan as written would have broken
working code.

## Round 4 — Codex (gpt-5.6-sol)

Eight of the nine round-3 defects are fully closed; the ninth citation correction is also correct. The plan now specifies the correct 73/72/69/68 populations, 69-entity triad denominator, exact worst-rank treatment, four metric/box sensitivity combinations, explicit SpeB collapse, source-specific manuscript numbers, and bidirectional ranking/pose validation.

One implementation blocker remains:

**SpeB `results` are an unvalidated third row type.** The correspondence and completeness rules at [lines 60–68](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PLAN-species-exclusion.md:60) cover SpyCEP `ranking` and `pose_interactions`, but the positive-control statistics consume `speb_positive_control_result.json["results"]`. Nothing requires those result rows to be complete, unique, or consistent with SpeB run records and the attempt-manifest roles. A deleted, duplicated, or stale decoy result could therefore alter the primary and sensitivity populations while the stated guards pass.

Fix: Require SpeB result claim keys to equal valid-fit SpeB run-record claim keys exactly, enforce unique claim/species keys, verify entity/state/affinity against run records, role against the attempt manifest, recompute ligand efficiency, and add SpeB deletion/duplicate/content-mismatch corruption tests.

Non-blocking polish:

- “Every set-level statistic counts rows” overstates the triad defect, which also involved wrong receptor selection and missing non-fits.
- “Verify hashes … before reading” would be clearer as “hash raw bytes before parsing.”
- A concrete example of the versioned statistics schema would help implementation but is not necessary given the listed required fields.

VERDICT: REVISE
### Claude's response — Round 4

Accepted the single remaining blocker and all three polish notes.

The SpeB gap was real and I had missed it across three rounds: I specified correspondence and
completeness for SpyCEP `ranking` and `pose_interactions`, but the positive-control statistics
consume a third row type, `speb_positive_control_result.json["results"]`, which no guard covered. A
deleted or duplicated decoy row would have altered both the primary and sensitivity populations
while every stated check passed. SpeB results now get claim-key set equality against valid-fit SpeB
run records, uniqueness on claim and species keys, entity/state/affinity verification against run
records, `role` verified against the attempt manifest, and recomputed ligand efficiency — plus
deletion, duplicate and content-mismatch corruption tests.

Polish applied: the Goal no longer describes the defect as purely row-counting, since the triad
statistic also selected the wrong receptor and omitted non-fits; hash verification specified as
raw bytes before parsing; and a concrete `docking-statistics-v2` SpeB schema example added so the
required fields are unambiguous at implementation time.

## Round 5 — Codex (gpt-5.6-sol) — MAX_ROUNDS reached

The round-4 blocker is closed: SpeB result completeness, uniqueness, provenance, recomputation, and corruption tests are now specified. The previous polish items are also resolved.

One new correctness blocker was introduced by the concrete schema example:

**The SpeB schema contradicts both its surrounding requirements and the existing margin semantics.**

- The plan says each primary/sensitivity block carries member IDs, margins, and SD summaries for both metrics, but the sensitivity example omits member IDs and all SD fields, while both blocks omit ligand-efficiency decoy means, best-decoy values, and margins.
- `beats_all_decoys` is not metric-qualified, making `passes_on_both_metrics` unauditable.
- The example reports positive margins of `0.093` and `0.231` even though the existing [`positive_control_margin`](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/src/spycep_drug_discovery/statistics_analysis.py:49) convention computes `best_decoy - positive`, yielding `−0.093` and `−0.231` when Q9D loses. An implementer could reasonably follow either convention and produce incompatible results.
- “Recompute ligand efficiency” does not identify the trusted heavy-atom source; recomputing from the untrusted SpeB result row would not detect a corrupted heavy-atom count.

Fix: Give each population nested `by_best_affinity` and `by_ligand_efficiency` blocks with positive value, decoy mean/SD, best decoy, explicitly formulated signed margin, and metric-specific `beats_all_decoys`; include memberships in both populations, and source heavy-atom counts from the validated species-keyed ligand-preparation records before recomputing efficiency.

Non-blocking note: placing `analysis_schema_version` at the document root as well as in the SpeB block would simplify whole-file consumer validation.

VERDICT: REVISE
### Claude's response — Round 5 (final)

Accepted in full. The blocker was self-inflicted: the concrete schema example I added in round 4 as
*polish* was underspecified and, worse, sign-flipped. Verified against
`statistics_analysis.py:49` — the convention is `margin = best_decoy - positive`, and the published
`docking_statistics.json` holds **-0.231**, not the `+0.231` my example showed. An implementer
following it would have produced margins contradicting both the helper and the existing file.

Rewritten: each population now carries nested `by_best_affinity` and `by_ligand_efficiency` blocks
with positive value, best decoy, signed margin, decoy mean/SD and metric-specific
`beats_all_decoys`, so `passes_on_both_metrics` is auditable; memberships present in both
populations; the margin convention stated inline; heavy-atom counts sourced from validated
ligand-preparation records rather than the SpeB result row; `analysis_schema_version` lifted to the
document root per the non-blocking note.

## Resolution — DEADLOCK at cap, not convergence

MAX_ROUNDS=5 reached without `VERDICT: APPROVED`. Recording this honestly rather than claiming
convergence.

**Claude's position on the state of the plan:** the substantive design converged by round 4. Rounds
1-3 found real, serious defects (three scripts sharing the row-vs-entity bug, wrong receptor
selection, a guard that would fail on valid data, an ADR that repeated the error it documented, and
two design counts I had wrongly marked as false). Round 4 found one real gap I had missed three
times (SpeB results as an unvalidated third row type). Round 5's blocker existed only because of an
example I introduced in round 4 and is now fixed.

No round-5 finding remains open. The plan has not, however, been seen by Codex in its current state,
so it carries no approval — a sixth round would be needed to confirm the fix lands. That is the
author's call.

## Round 6 — Codex (gpt-5.6-sol) — cap lifted by operator

The plan is now implementable and scientifically coherent. The amended ADR agrees with it on the primary estimand, four populations, 54-comparator sensitivity, 69-entity triad population, receptor selection, claim-level guards, and corrected SpeB denominators. The SpeB schema and validation path are sufficiently explicit to prevent duplicated, missing, stale, or corrupted rows from silently affecting results.

Non-blocking notes:

- [ADR-0004 line 54](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/docs/adr/ADR-0004-ambiguous-species-exclusion.md:54) could name `attempt_manifest.json` and the global-then-intersect rule explicitly, matching the plan.
- The ADR’s “Applies to” list omits the shared module, downstream scripts, and documentation surfaces now affected.
- The schema example is JSONC rather than strict JSON because it contains a comment and placeholder strings; labeling it illustrative would prevent copy-paste confusion.
- Clarifying whether `member_entity_ids` includes Q9D or only decoys would make provenance easier to interpret.
- The plan header still says “cap reached,” although the cap was lifted.

None of these changes the calculations, validation behavior, or safety of the implementation.

VERDICT: APPROVED
### Claude's response — Round 6 (final)

All five non-blocking notes applied: ADR-0004's derivation paragraph now names `attempt_manifest.json`
and the global-then-intersect rule explicitly and specifies raw-byte hashing before parsing; its
"Applies to" list extended to the shared module, both downstream scripts and the three documentation
surfaces; the schema example relabelled illustrative JSONC; `member_entity_ids` annotated as decoys
only, with Q9D the positive rather than a member; plan header corrected from "cap reached" to record
the operator lift.

## Resolution — CONVERGED

`VERDICT: APPROVED` at round 6. Act 1 (grill-with-docs) and Act 2 (Codex adversarial review) both
complete. No code written during either act. Awaiting author sign-off before implementation.

# Plan: Entity-level population construction for all set-level statistics
_Locked via grill-with-docs — by Claude + Josh, 2026-07-20. Revised across Codex rounds 1–6; APPROVED round 6 (operator lifted the 5-round cap). Terms per `CONTEXT.md`. Decision recorded in `docs/adr/ADR-0004-ambiguous-species-exclusion.md`._

## Goal

Set-level statistics in this project are wrong in three distinct ways, not one. The headline defect
is counting docking **rows** where entities must be counted, but the triad statistic additionally
selects the wrong receptor and omits non-fits entirely. Under run-record schema v3: the four AMBIGUOUS entities each contribute two
states (`fda_n` 58 over 54, SpeB decoys 20 over 17); `_triad_engagement` collapses receptors with
`any()` where the documented method is affinity-best receptor; and vancomycin, a genuine non-fit, is
silently absent from every denominator. The defect is replicated independently in three scripts.

Build one shared, tested entity-population helper; make `compute_statistics.py`, `make_figures.py`
and `write_docking_methods.py` all consume it; recompute; and correct every manuscript claim the
sealed campaign-3 data has falsified. The sealed campaign is read-only throughout; nothing is
re-docked.

## Approach

### 1. Shared population module (`src/spycep_drug_discovery/analysis_population.py`)

Single source of truth. All three consumer scripts import from here; none may filter rows itself.

- **Roster from `attempt_manifest.json`, not result manifests.** The four stage manifests disagree on
  which ambiguous entities they contain (wide/tight 4, SpeB 3, boron 0), and deriving multiplicity
  from successful result rows is outcome-dependent when one state fails. Derive state multiplicity
  once from the validated attempt manifest, per workflow scope.
- **Cross-check globally, then intersect.** Compare the attempt-derived ambiguous set against the
  *global* dock-eligible `tier == "AMBIGUOUS"` catalog set **once**, then intersect that validated
  set with each workflow roster — SpeB contains three ambiguous entities and boron zero, so a
  per-workflow comparison against the catalog's four would spuriously fail. Verify
  `species_catalog_sha256` and `attempt_manifest_sha256` against every stage manifest **and** every
  run record by **hashing raw bytes before parsing**. Any disagreement raises.
- **Four explicit populations**, never conflated (verified against sealed wide-box data):
  - `attempted` = **73** — entities with a terminal disposition in scope (includes vancomycin)
  - `valid_fit` = **72** — entities with at least one negative-affinity receptor result
  - `analysis_eligible` = **69** — `attempted` minus ambiguous; the **triad** population
  - `numeric_analysis` = **68** — `analysis_eligible` minus all-non-fit entities; the population
    means and tests run on
- **Affinity-best receptor selection** with an explicit tie rule: pick the row with lowest
  `best_affinity_kcal_mol`; on exact ties pick the lexicographically smaller `pocket_id`, recorded as
  the convention. Never `any()` across receptors.
- **Canonical ordering** on every emitted membership list, so output is process-independent.

### 2. `compute_statistics.py`

- Consume the shared population. Custom-vs-FDA over `numeric_analysis`.
- **Triad counts over affinity-best receptor** on the `analysis_eligible` population of **69**, with
  vancomycin present as a zero-contact non-fit per the `CONTEXT.md` rule that a non-fit is an
  outcome, not missing data. Corrected values: wide **62/69, 51/69, 31/69**; tight **68/69, 56/69,
  31/69**.
- **Re-rank from metric values** with an explicit convention: **competition rank = 1 + the number of
  strictly better entities**, with entity id used only for deterministic display ordering. Exact
  score ties exist in the data, so this must not be left to implementation choice. Never reuse
  manifest rank fields.
- **Fail-closed guard at claim granularity.** An ordinary entity has *two* terminal receptor claims
  and an ambiguous one has four, so a per-entity guard is false on valid manifests. Require: one
  terminal run record per expected claim; one ranking row per *species* with any valid receptor
  result; one row per *entity* only in the final single-state numeric population. Vancomycin passes
  with zero ranking rows.
- **Content correspondence, validated separately per row type.** A ranking row is *species-level* and
  aggregates multiple receptor claims, so it cannot match a singular claim or pocket; an interaction
  row is *claim-level*. Validate rankings by recomputing their receptor-affinity map, ensemble
  minimum, mean, efficiency, set and role from run records. Validate interaction rows independently
  by claim key, pocket, species and affinity.
- **Completeness by set equality, not one-directional matching.** Requiring existing rows to match a
  run record is fail-open — it cannot detect a *deleted* row. Require the pose-interaction claim-key
  set to **equal** the valid-fit run-record claim-key set exactly: every valid affinity-bearing claim
  produces exactly one interaction row, and every non-fit claim produces zero.
- **SpeB `results` is a third row type and gets the same treatment.** The positive-control statistics
  consume `speb_positive_control_result.json["results"]`, which the rules above do not cover — a
  deleted, duplicated or stale decoy row could silently alter both the primary and sensitivity
  populations while every other guard passes. Require: SpeB result claim keys **equal** the valid-fit
  SpeB run-record claim keys exactly; claim and species keys unique; entity, state and affinity
  verified against run records; `role` verified against the attempt manifest; and ligand efficiency
  recomputed rather than trusted.
- Fix `non_fits_excluded`, currently permanently empty — rankings contain only valid fits, so a
  non-negative-affinity filter over them can never match. Source it from the attempted roster.
- **Versioned output schema** with explicit blocks: `primary_ambiguous_excluded` and
  `sensitivity_dual_state_collapsed`, each carrying member ids, decoy count, total rank denominator,
  both ranks, margins, SD summary and pass verdict. State that the two protease comparators sit
  outside the decoy rank denominator. **The collapse rule is explicit:** each ambiguous SpeB decoy
  contributes its **lowest-affinity state**, with ligand efficiency taken from that same state — not
  first-listed, not averaged. Shape:

  Illustrative JSONC — contains a comment and `"..."` placeholders; not literal output.

  ```jsonc
  "analysis_schema_version": "docking-statistics-v2",   // also at document root
  "speb_positive_control": {
    "population_rule_id": "ambiguous-excluded-entity-level",
    "margin_convention": "margin = best_decoy - positive; negative means the positive LOSES",
    "heavy_atom_source": "validated species-keyed ligand-preparation records",
    "comparators_outside_rank_denominator": ["..."],
    "primary_ambiguous_excluded": {
      "decoy_count": 14, "rank_denominator": 15,
      "member_entity_ids": ["..."],   // decoys only; Q9D is the positive, not a member
      "excluded_entity_ids": ["amoxicillin", "ampicillin", "cephalexin"],
      "by_best_affinity": {
        "positive": -6.806, "best_decoy": -6.899,
        "margin_to_best_decoy": -0.093,
        "decoy_mean": -6.152, "decoy_sd": 0.584,
        "rank": 2, "beats_all_decoys": false
      },
      "by_ligand_efficiency": {
        "positive": -0.272, "best_decoy": "...",
        "margin_to_best_decoy": "...",
        "decoy_mean": "...", "decoy_sd": "...",
        "rank": 4, "beats_all_decoys": false
      },
      "passes_on_both_metrics": false
    },
    "sensitivity_dual_state_collapsed": {
      "decoy_count": 17, "rank_denominator": 18,
      "collapse_rule": "lowest_affinity_state_per_entity",
      "member_entity_ids": ["..."],
      "by_best_affinity": {
        "positive": -6.806, "best_decoy": -7.037,
        "margin_to_best_decoy": -0.231,
        "decoy_mean": -6.268, "decoy_sd": 0.593,
        "rank": 4, "beats_all_decoys": false
      },
      "by_ligand_efficiency": {
        "positive": -0.272, "best_decoy": "...",
        "margin_to_best_decoy": "...",
        "decoy_mean": "...", "decoy_sd": "...",
        "rank": 7, "beats_all_decoys": false
      },
      "passes_on_both_metrics": false
    }
  }
  ```

  Every population carries memberships and both metric blocks. `beats_all_decoys` is metric-specific
  so `passes_on_both_metrics` is auditable. The signed-margin convention matches the existing
  `positive_control_margin` helper (`statistics_analysis.py:49`) — **verified: the published file
  holds -0.231, not +0.231**. Heavy-atom counts come from the validated ligand-preparation records,
  not the SpeB result row, so a corrupted count is detectable rather than reproduced.
- **Full valid-fit FDA population sensitivity (16 assignments).** Choosing one state per ambiguous
  entity is 2⁴ = 16 assignments over the 54 valid-fit comparators — *not* the full 55-compound
  library, since vancomycin is a non-fit and remains absent. Report **effect-size (mean-difference)
  and Mann-Whitney p ranges for both affinity and ligand efficiency, under both wide and tight
  boxes** — the quoted p ranges (0.224–0.255 wide, 0.178–0.196 tight) are affinity-only, and the
  primary comparison reports both metrics. Demonstrates robustness without inventing abundance
  fractions.
- **Vancomycin worst-rank sensitivity.** Not "censored or worst-rank" — those are different methods.
  Specify exactly: a **worst-rank Mann-Whitney for both metrics under both boxes**, placing
  vancomycin strictly below every valid-fit comparator **for rank testing only**. No synthetic value
  enters any mean, effect size or bootstrap CI; mean-based analysis stays restricted to valid fits.
- **Provenance:** SHA-256 of every analysis input, full membership ids or a canonical population
  hash, and the exact resolved NumPy/SciPy versions.

### 3. `make_figures.py` and `write_docking_methods.py`

- Both import the shared population; remove their independent row-counting
  (`make_figures.py:86-88`, `write_docking_methods.py:37-40`).
- **Both must verify before consuming `docking_statistics.json`**: exact analysis schema version,
  population-rule identifier, source hashes and population hash. Centralizing row filtering alone
  does not stop a stale statistics file from the same unchanged inputs being consumed silently.
- **`write_docking_methods.py` needs a full schema-v3 metadata migration, not just a counting fix.**
  It reads top-level `protonation_ph`, `seed`, `compounds_docked` and `box_basis` (`:94-96`, `:110`,
  `:123`, `:149`) — **none of which exist in a v3 manifest**, so it KeyErrors before it can
  row-count. Migrate every field the generated note consumes and test the script end-to-end.
- **Figure 2 currently cannot run against v3** — it reads `r["ligand_id"]` on SpeB result rows that
  have no such key (`:129`) and a top-level `speb["decoy_count"]` (`:149`). Refactor to `entity_id`
  and the corrected primary/sensitivity populations. **Leave `:160` alone** — that is
  `figure_top_hits()` reading the SpyCEP ranking, where `ligand_id` is a valid field.
- Regenerate and visually verify **all four** figures in one successful run, not just Figure 1.

### 4. Manuscript — full audit, not spot edits

Codex found stale claims well beyond the three originally listed. Audit the whole manuscript, the
generated `docking_analysis.md`, all figure captions and the README for population, rank,
dominant-state, pose, software-version and test-count claims.

**Design counts are facts and must be preserved, not overwritten.** The library really does contain
55 FDA comparators and the SpeB panel really does contain 17 decoy entities. The error was never
those numbers — it was presenting them as the *numeric analysis populations*. Every affected
sentence states the design count **and** the numeric population separately: 55 comparators of which
50 enter the primary numeric analysis; 17 decoys of which 14 enter the primary and all 17 the
collapsed sensitivity. Replacing 55 with 50 or 17 with 14 would create new falsehoods.

Known-false at minimum:

- Abstract — "6th of 20 / 7th of 20", p = 0.32/0.26, and the claim that every ligand is docked as its
  dominant microspecies (four are not). The "55 comparators" and "17 decoys" figures stay, qualified.
- §2.3 — name the four excluded entities, the pKₐ rationale, the exclusion rule.
- §2.4 — vancomycin exhausts the 1800 s ceiling against **both** boxes; the earlier wide-box pose was
  accepted past the ceiling by a timeout extensible by host suspension and is superseded.
- §2.6 — still implies 17 decoys are the primary analysis.
- §2.7 — claims best-receptor triad counting the code did not implement.
- §3 — docked counts, means, CIs, p-values, triad counts ("every docked compound contacts at least
  one triad residue" is **false** under best-receptor: wide is **62 of 69**), "67th of 73"
  (benzamidine re-ranks to 63/68), and the unsupported historical "55–56 was a 146-row pose count"
  claim.
- Discussion — "Q9D trails two β-lactams" holds only in the sensitivity analysis.
- Limitations — vancomycin absent from **both** comparisons; "77 compounds and one pose each" false.

No number may be edited by hand from the old values, but "everything comes from the statistics file"
is impossible — the audited surfaces include design counts, docking settings, software versions and
test counts. Source each class explicitly: **analysis numbers** from `docking_statistics.json`,
**design and method numbers** from their validated manifests, and the **test count** from the
verified test run.

### 5. Tests — numerical acceptance criteria, not just shape

Golden assertions against sealed data: the 18/50 numeric arms, all **four** populations
(73/72/69/68), corrected means/CIs/p-values, exact triad counts under best-receptor on the 69
denominator, Q9D's four ranks across primary and sensitivity, explicit included/excluded id lists,
vancomycin's terminal non-fit treatment, and the 16-assignment mean-difference and p ranges.

Corruption tests — golden numbers catch drift but not structural failure. Add synthetic:
**ranking-row, pose-row and SpeB-result deletion as separate cases**; SpeB duplicate row; SpeB
content mismatch; missing claim; extra claim; omitted ambiguous state; hash disagreement;
run-record-versus-ranking content mismatch; and stale-statistics rejection by both consumers. Plus:
guard fires on a duplicate row, and does *not* fire on vancomycin's zero rows.

### 6. Verify

Full suite green; all four figures regenerate in one run; `compute_statistics.py` idempotent on a
second run. Byte-idempotence alone proves only that an error is deterministic, so it is a
supplementary check, not the proof.

## Key decisions & tradeoffs

Recorded in [ADR-0004](docs/adr/ADR-0004-ambiguous-species-exclusion.md), which this revision also
corrects — the ADR repeated the very row-counting error it documents, citing Q9D "4th of 21" from 20
decoy **rows** plus Q9D. The entity-collapsed sensitivity denominator is 18; the honest comparison is
**4/18 sensitivity versus 2/15 primary**.

- **Exclusion, not collapse**, because all four ambiguous entities are FDA comparators, so any
  per-entity selection rule perturbs one arm. Best-of-two is upward-biased by construction.
- **Averaging and dominant-selection are foreclosed by preregistration** — `method_status` is
  `..._no_abundance_fractions` and each adjudication states no form is established as dominant.
- **The primary result is a restricted-population estimand**, stated as such. Codex is right that
  "outcome-independent" does not mean "unbiased": the exclusion is chemistry-dependent, drops four
  FDA entities and no custom ones, and changes the estimand to single-state comparators. The
  16-assignment sensitivity covers the full **valid-fit FDA population** (54 comparators) and is what
  licenses the robustness claim. The primary estimand is named explicitly: **valid-fit, single-state
  custom versus FDA entities** — vancomycin makes it conditional on obtaining a valid fit, not only
  on being single-state.
- **One uniform rule as primary**, with the 17-decoy collapse reported as sensitivity rather than a
  deleted result.

## Risks / open questions

- **The triad correction changes a headline.** Under correct affinity-best-receptor counting the wide
  box gives **62 of 69** contacting at least one residue, not 100%. The "triad contact does not
  discriminate" argument partly rested on universal contact that was an artifact of counting either
  receptor. The conclusion likely survives — near-universal contact in a compact site — but the
  sentence must be rewritten, and **Josh should see this before sign-off.**
- Excluding four comparators costs power in a comparison already stated to be underpowered.
- `producing_rule` for lisinopril reads `explicit_hand_reviewed_beta_lactam_alpha_amino_hypothesis`,
  but lisinopril is not a β-lactam. Cosmetic mislabel in a sealed artifact; flagged, not fixed.
- **Deferred, logged as rejected-for-now:** Codex's finding 15 — that bootstrap CIs over a curated
  fixed library are not population inference and Mann-Whitney non-significance is not equivalence —
  is correct but pre-existing, and restructuring the paper's inferential framing is a separate
  decision for Josh, not part of a pseudo-replication fix. This plan relabels the interval as
  entity-resampling uncertainty; it does not rewrite the study's inferential stance.
- **Partially accepted:** Codex's finding 14 asks to pin exact NumPy/SciPy. This plan *records*
  resolved versions in the output rather than hard-pinning, to avoid mutating a validated environment
  mid-analysis.

## Out of scope

- Re-docking or modifying any sealed campaign artifact. Campaign `v2_20260719` is immutable.
- Revisiting which protonation states are plausible, or the AMBIGUOUS tier assignments.
- Vancomycin's timeout behaviour, correct per ADR-0001 — only the claims it falsified.
- Restructuring the study's inferential framing (see deferred, above).
- Committing campaign-3 results, which happens after this lands and is verified.

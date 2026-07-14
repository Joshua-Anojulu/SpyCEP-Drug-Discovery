# Plan: Remediate the Codex code-review findings

_Round 9 — APPROVED by Codex after eight rounds of adversarial plan review (85 findings). MAX_ROUNDS raised 5 → 8 by user._
_**AUTHORITY CHAIN — ONE OPERATIVE METHOD:** `PROJECT_CONTEXT.md` **§28 is the sole operative method statement**._
_It consolidates and supersedes §§9–27 IN FULL; every earlier section is historical record only and must not be
executed. PLAN.md and §28 must agree; divergence is a bug to fix, never a precedence to exercise._

## Goal

An adversarial code review (`docs/CODEX-CODE-REVIEW-2026-07-13.md`) found 12 confirmed defects in the uncommitted
pH-7.4 protonation work. **Nine** rounds of adversarial plan review found **87 more** problems with the remediation
itself — including three separate recurrences of result-conditioned reasoning in my own drafts.

### The real protonation defect (corrected — an earlier draft overstated this)

`_AMINE_SMARTS` protonates aliphatic amines assuming pKa 9–11. The β-lactam α-amino groups sit near **6.8–7.3**,
so the rule fires **outside its own stated domain of validity**. The consequence is not that every β-lactam is
flatly wrong — it is that **near-tied species are assigned a single state and reported as unambiguous**:

| Compound | SpeB rank | Net-0 abundance at pH 7.4 | Status |
|---|---|---|---|
| Ampicillin | 3 | ~56/44 | marginal — not clear-cut |
| Amoxicillin | 5 | **50.2%** | **near-tie; current state is marginally most abundant, NOT proven wrong** |
| Cephalexin | 11 | ~75/25 | clearly should be net −1 — but ranks BELOW Q9D, cannot flip the control |

**The SpeB result is not proven wrong — it is not yet proven right**, because two decoys above the positive control
are docked in a state that is effectively a coin flip presented as fact. Resolving that is the point of this work.

## Preregistered method (frozen BEFORE the redock)

### Decision rules are NEUTRAL and STATE-ROBUST — they preregister the criterion, never the answer
Three earlier drafts got this wrong: "the redock must not rescue the null"; then `assert beats_all_decoys == false`;
then — after deleting fabricated fractions — branching on a **"primary p"** and a single `beats_all_decoys` boolean
that **no longer exist**, because deleting the fractions also deleted the *primary state*. An ambiguous entity has
no single selected state, so different allowed state combinations can land on opposite sides of any threshold.
The outcome must therefore be **three-way**, not binary:

- **Screen (evaluated over all allowed state combinations):**
  - **`ROBUST_DETECTED`** — every combination gives p < 0.05.
  - **`ROBUST_NO_DETECTION`** — every combination gives p ≥ 0.05.
  - **`STATE_DEPENDENT`** — combinations straddle the threshold. **This is a legitimate, reportable result**, and
    reporting it honestly is the whole point: it says the conclusion is not robust to a protonation choice the
    evidence cannot settle.
  - Never "the null holds" — failure to reject is not proof of no effect.
- **SpeB, each metric separately (affinity; ligand efficiency) — EXPLICIT QUANTIFIERS:**
  - **`ROBUST_PASS`** — `beats_all_decoys` true for **every** combination.
  - **`ROBUST_FAIL`** — `beats_all_decoys` false for **every** combination.
  - **`STATE_DEPENDENT`** — true for **some** combinations and false for **others**.
  - `ROBUST_FAIL` must **not** be read as "robust pass was not established" — that would silently absorb
    state-dependent cases into the conclusion the old paper happened to want.
  - (`passes_on_both_metrics` remains insufficient on its own — also false when Q9D wins one metric and loses the other.)
- **`INDETERMINATE_NONEXHAUSTIVE` — applies to BOTH workflows.** `ROBUST_*` asserts a property of *every* allowed
  combination, so it can only be claimed under **exhaustive** evaluation. If enumeration is incomplete, or any required
  state has no `valid_fit`: straddling evidence ⇒ `STATE_DEPENDENT` (finding both sides *proves* it); otherwise ⇒
  **`INDETERMINATE_NONEXHAUSTIVE`**, never a robust outcome. **Failure to find a straddle is not proof of robustness.**
  The results schema **distinguishes** `INDETERMINATE_CHEMISTRY` (a >2-state chemical space forced an abort) from
  `INDETERMINATE_NONEXHAUSTIVE` (missing fits / incomplete combination evaluation) — different causes, different remedies.
- **Tests assert prose/result CONSISTENCY only.** No test asserts a predetermined outcome.

### Envelope algorithm (exact, not sampled)
Ranks **interact**, so the extrema of Mann-Whitney p and rank-biserial do **not** follow from independent per-ligand
extrema — an envelope built from per-entity worst cases would be wrong. Note the key asymmetry: **each state is
docked exactly once (cost is LINEAR in states), and a "combination" is only a re-selection of already-computed
affinities — so the combinatorial cost is in the ANALYSIS, which is cheap, not in the docking.**
- Let *k* = number of ambiguous entities in the analysed set and *C* = ∏ (states per entity).
- **If C ≤ 65 536 (k ≤ 16 ambiguous entities at ≤2 states each): exhaustive enumeration**, computing **verified exact extrema** of p and rank-biserial.
- **If C > 65 536: ABORT for renewed user approval** before any result is seen — do not silently degrade to a
  non-exhaustive fallback, which cannot establish a `ROBUST_*` outcome at all (see `INDETERMINATE_NONEXHAUSTIVE`).
  No sampling is ever used to claim a bounded envelope.
- The chosen branch and *C* are recorded in the results manifest.

### Statistics (fully specified, estimands matched)
- **Primary test:** custom-vs-FDA, **wide box**, **best affinity**, two-sided **Mann-Whitney**, **α = 0.05**.
- **Primary effect measure:** **rank-biserial correlation** with a **BCa** bootstrap CI — matched to the rank test.
  **There is no singular primary CI**, because with no primary state there is no single rank-biserial value to bound.
  Report instead: the CI for **each of the two extremal configurations** (the combinations attaining the min and max
  rank-biserial), each clearly labelled as **per-configuration and selection-affected** — a CI for the extremum-attaining
  configuration ignores selection and must not be presented as an unconditional interval. Bootstrapping is run for
  those extremal configurations only, not for all C combinations (10 000 × C would not be cheap).
  **Frozen:** orientation = **custom minus FDA** (negative ⇒ custom binds more strongly); **tie handling = mid-rank**;
  Mann-Whitney **asymptotic with continuity correction** (exact is infeasible at n=18/55 and must not be chosen
  post-hoc). Effect sign and p-value are therefore reproducible.
  (A Mann-Whitney p-value and a *mean-difference* CI are different estimands and can legitimately disagree; the
  mean-difference CI is retained only as a **secondary descriptive** statistic, labelled as such.)
  Resampling unit = **ligand**; **stratified by set**; **10,000 replicates**; **seed 42**; **CI level 95%**.
  **Extremal tie rule (frozen, pre-result):** ties are resolved over **distinct configurations** (not unique score
  vectors); report **every tied extremal configuration**, recording their **configuration IDs** in the CI artifact.
  The **secondary mean-difference CI is computed for those same extremal configurations only**, and labelled as such.
- Tight box and ligand efficiency are **secondary/sensitivity** — no multiplicity correction on the primary.

### Species / ambiguity — THREE TIERS, NO FRACTIONS ANYWHERE
Codex round 5 established a fact about **chemistry**, not about this plan: **Henderson–Hasselbalch on macroscopic
pKas cannot identify which *site* carries the proton, nor divide abundance among tautomeric/site microstates.**
Earlier drafts nonetheless demanded atom-mapped microstates with numeric fractions (≥66% dominance, ≥5% inclusion,
±0.5 "95% interval"). **Those numbers could not have been honestly produced** — it would have replaced a false
"unambiguous" label with a false "50.2% ± 0.5" one, the *same defect class* this remediation exists to eliminate.
Dead. Replaced with:

- **`UNAMBIGUOUS`** — compound-specific experimental evidence (macroscopic pKa **plus site assignment**) establishes
  one dominant state at pH 7.4. **Exactly one docked state.**
- **`AMBIGUOUS`** — evidence cannot establish a single site-resolved dominant state. **Enumerate** the site
  microstates (protocol below). **Dock all of them. Report a state-robust outcome. Claim no fractional precision.**
- **`NO_IONISABLE_SITE`** — **exactly one docked state**; no state decision required.

**BOUNDED, EXPLICIT alternative states — general enumeration is dead.**
A general `enumerate_species()` was over-engineered and unsafe on two counts: state count grows as
`2^undecided_sites × tautomers`, so a compound with several unresolved sites generates **hundreds of 1800-second
dockings** (docking is linear *in states*, but the number of states is not bounded); and **InChI normalises
mobile-hydrogen tautomers**, so deduplicating by InChI would have **silently deleted the very tautomer alternatives
the enumerator existed to preserve**. Replaced with a bounded, auditable form:

1. An `AMBIGUOUS` entity carries **exactly 2 explicitly-listed states** — the two contested protonation forms —
   each given as an **atom-mapped SMILES written out in the catalog**, with its literature citation and the reason
   the evidence cannot choose between them. No generator, no tautomer enumerator, no InChI dedup: the states are
   **enumerated by hand and reviewed**, so nothing can be silently normalised away.
2. **Hard cap: 2 states per entity.** If the evidence implies a compound genuinely needs >2 plausible states, **abort
   before docking** and report it as **chemically intractable ⇒ `INDETERMINATE`**, or seek **renewed user approval —
   before any result is seen.** Never silently truncate.
3. **Bounded workload.** With ≤2 states per entity, docking attempts grow by at most one extra state per ambiguous
   entity, and `C = 2^k` for *k* ambiguous entities. **k ≤ 16 ⇒ C ≤ 65 536 ⇒ exhaustive enumeration is always
   feasible.** If k > 16, abort for renewed approval rather than degrade to a non-exhaustive fallback.
4. This is **hand-entry of a hypothesis, not of a result**: we are not asserting which state is right — we dock both
   and report whether the conclusion depends on the choice. That distinction is what makes it honest, and the README's
   "nothing hand-entered" line is reworded to say exactly this.

**Resolving an apparent conflict:** the *rule* never assigns a charge to an undecided site (the generic rule emits
the neutral form there) — while the *catalog* carries **both** the charged and the neutral state for docking. Both
hold: the rule refuses to guess; the catalog refuses to hide the guess.

No abundance fractions, no sum-to-1 constraint, no ≥66%/≥5% thresholds, no fabricated uncertainty interval. **No pKa
calculator is used** — an unvalidated predictor would relocate the judgement, not remove it.

- **Envelope reporting — NEUTRAL, both sides.** Do **not** designate a "worst case": that is result-conditioned for a
  two-sided screen, and it was previously defined only relative to the SpeB control while being applied to custom/FDA
  entities. Report, across **all** allowed state combinations, the **min and max of the effect estimate and of the
  p-value** — a neutral range. Applies to **every** ambiguous entity, **including Q9D itself**.
- **State-level missingness.** If a required state has no `valid_fit`, report the entity as **INDETERMINATE** rather
  than inventing a bound ("maximally unfavourable" is numerically unbounded and itself result-conditioned). Report
  role-specific attrition.
- The SpeB panel always retains **17 unique decoy identities** — a compound is never duplicated into the panel, so
  frozen n cannot move.

### Analysis population
- Primary = **complete-case** (`valid_fit` against *both* receptors); one-receptor ligands → **available-case
  sensitivity**; **zero-fit entities reported as attrition by role**, never silently dropped.
- **`valid_fit` (frozen):** Vina exit 0 **and** parseable pose with ≥1 mode **and** sidecar/output hash agreement
  **and** best affinity **< 0**. A non-negative score is reported as an **"operational non-fit"**, NOT a "clash" — that word requires geometric evidence.
- **Receptor tie-break (frozen):** 5XYA before 7EDD.

### Frozen parameters
Seed 42, exhaustiveness 8, num_modes 9, **`--cpu 1`** (multi-CPU Vina is non-deterministic even under a fixed seed —
required for the reproducibility claim, and it removes a machine-dependent influence on hitting the wall-clock
ceiling), **`--scoring vina`**, all other effective Vina defaults recorded, **MMFF94s hard cap 2000 iterations**,
**uniform 1800s timeout across all four workflows**. No tuning after seeing a result. MMFF failure at the cap
requires **renewed user approval**, never a silent escalation.

**Reporting rule.** Freeze, run, report whatever comes out. If corrected chemistry legitimately rescues the SpeB
control, that is a **finding**, not a failure to suppress. No parameter rollback.

## Approach

**Order — dependencies freeze FIRST** (regenerating a gated artifact under a later dependency change would
invalidate it):
**freeze code + schema + dependency pins → receptor conversion → QC gate → species catalog → attempt manifest →
preparation audit → redocks → statistics → methods note → figures → prose → claim check.**

### 0. Freeze the environment first
Pin RDKit and Meeko to the **exact versions used** — `pyproject.toml` currently demands `rdkit>=2026.3.3` while the
results were produced on **2025.09.6**, so a clean install cannot reproduce them. Record versions plus the **Vina
binary hash** in every manifest. Normalise absolute user paths out. Only then convert receptors.

### 1. Species: fix the rules, then freeze a STATE catalog
- **Per-site amine pKa-domain guard** — never charge a site whose pKa falls in the ambiguity band around 7.4. Must
  **preserve azithromycin's genuine +2** (two separated, truly basic amines), so the guard is per-site, never
  "protonate only the most basic amine".
- Tautomer-insensitive **tetrazole** (losartan → −1); **acidic tricarbonyl/enol** (doxycycline); **sildenafil**
  (basic pKa ~6.5 → neutral base); **lisinopril → net −1** — its lower-basicity secondary amine is predominantly
  neutral at 7.4, and it was in the original upstream finding but went missing from an intermediate draft. Each of
  these five gets a **dedicated regression test**; an exhaustive table does not prove the generic rule was fixed.
- **Thread `(entity_id, state_id)` — not just `ligand_id` — through preparation, docking, FILENAMES, manifests,
  dispositions, fingerprints and claim keys.** Multiple states of one entity would otherwise collide and overwrite
  each other's poses, markers and sidecars.
- **Freeze `docs/methods/species_audit.json`** — a **species AUDIT catalog**, one `(entity_id, state_id)` row for
  every entity considered, each carrying an explicit **`dock_eligible`** flag and exclusion reason. It covers all 77
  library parents + **Q9D** + the **4 gem-diol surrogates**. The **4 boronic-acid parents are audited with
  `dock_eligible: false`** (they fail MMFF and are never directly docked), with a **source-to-surrogate mapping** to
  their gem-diol replacements. The set of *attempted* entities is **derived** from `dock_eligible`, so the catalog and
  the attempt relation cannot contradict each other. (An earlier draft defined this as "one row per DOCKED state
  covering all 77 parents" while the attempt relation correctly excluded four parents from every docking workflow —
  both could not be true.) The boron manifest currently records the *pre-protonation* surrogate SMILES.
- **Integrity checks:** unique `(entity_id, state_id)`; **entity-projection** covers the library exactly (a row-level
  bijection is impossible once entities carry multiple states); ****exactly one** state for every `UNAMBIGUOUS` and every `NO_IONISABLE_SITE` entity,
  and **exactly two** (never merely >=2 — the workload proof depends on it) for every `AMBIGUOUS` one**; provenance is **CID *or* citation *or* parent-transformation** (generated
  surrogates have no CID). **No sum-to-1 constraint** — there are no fractions to sum.
- Per row: atom-mapped canonical SMILES, per-atom + net formal charge, producing rule, **classification tier
  (`UNAMBIGUOUS` / `AMBIGUOUS` / `NO_IONISABLE_SITE`)**, and its evidence. Catalog **authoritative**, with a **tier-dependent validation rule** — a
  single "fails on regeneration mismatch" check is IMPOSSIBLE here and would destroy the design: the generic rule
  deliberately emits only the *neutral* form at an undecided site, while the catalog holds a neutral **and** a charged
  hand-entered alternative. A literal regeneration check would either reject every charged alternative or re-run
  protonation and **erase it**. Therefore:
  - **`UNAMBIGUOUS` / `NO_IONISABLE_SITE`** — validated by **rule-output matching**: the frozen state must equal what
    the generic rule regenerates. Mismatch ⇒ fail.
  - **`AMBIGUOUS`** — the frozen atom-mapped SMILES is **consumed VERBATIM** (never regenerated). Validated instead by:
    parses; atom maps intact; per-atom and net charges match the recorded values; provenance/citation present;
    canonical **round-trip identity**; and SHA-256 agreement. The rule is not consulted.
  The catalog SHA-256 is recorded in every downstream manifest.

### 2. Attempt manifest — a WORKFLOW-ELIGIBILITY RELATION, not a Cartesian product
A literal `state × workflow × receptor × box` product would route Q9D and the gem-diol surrogates into workflows
they do not belong to. Freeze `docs/methods/attempt_manifest.json` with **one row per LEGAL invocation**:

| Entities | Workflow | Receptors / box |
|---|---|---|
| **73 directly preparable library parents** (all states) | wide | {5XYA, 7EDD} |
| **73 directly preparable library parents** (all states) | tight | {5XYA, 7EDD} |
| SpeB panel — Q9D + 17 decoys + 2 protease comparators (all states) | speb | {6UKD}, one box |
| **4 gem-diol surrogates** of the 4 boronic-acid parents (all states) | boron | boron box |

**The 4 boronic-acid parents are NOT routed into wide/tight.** They fail MMFF parameterisation and cannot be docked
directly — which is exactly why the library docks **73/77** and why the gem-diol surrogates exist at all. An earlier
draft of this table sent all 77 parents into the screen, which would have created manifest rows that **can never pass
preparation** and would have silently changed the screen population. The surrogates are **not** substituted into the
primary screen (that would change the estimand); they remain a separate, clearly-labelled workflow.

**Derive the attempt count from this relation**; audit exactly these state records through MMFF. The
**attempt-manifest SHA-256 is recorded in every downstream run and analysis manifest** — otherwise workflow
eligibility could change without invalidating the run population. (The old fixed
"320" could never account for the alternative states the ambiguity policy docks.) `PLAN.md` and
operative **§28C** carry **identical dimensions**.

### 3. Validation (`tests/test_protonation.py`)
≥24 reference compounds with literature pKa citations covering **every** declared rule (tetrazole, phosphonate,
sulfonic acid, thiol, sulfonamide, phenol, imidazole, aniline, boronic acid) and every audited exception.
**Assert exact atom-mapped species and per-atom charges — never net charge alone.** Net-charge-only testing is what
let the β-lactam and losartan bugs through: right total, wrong atom or wrong tautomer.

### 4. Provenance and gating
- **Resume fingerprint:** normalised effective command, ligand + receptor PDBQT hashes, **Vina binary hash**, box,
  seed, exhaustiveness, num_modes, `--cpu`, `--scoring`, **timeout**, species-catalog hash, `(entity_id, state_id)`,
  run-schema version. Applies to **`.no_fit` markers** too. Never write `<resumed from existing pose file>`.
- **Per-attempt sidecar** beside every pose/marker (fingerprint, command, timing, status, cause, output hash),
  written atomically. Fresh runs **delete pose + marker + sidecar + temp files together**, and require
  sidecar/output hash agreement before accepting either.
- **One shared run-record schema across all four manifests.** `run_speb_positive_control.py` and
  `dock_boron_surrogates.py` call `dock_ligand()` but copy only scores/interactions — a clean rerun does not
  magically add commands, hashes, timings or versions.
- **QC gate:** content-addressed `pass|block` artifact with source, pocket and reviewed-PDBQT hashes; runtime
  requires exact agreement. Today `run_docking.py` never reads it and its success value is the ambiguous
  `reviewed_caution_not_docking_approval`.
- **SpeB receptor must stop bypassing the gate** — it converts 6UKD *inside* the docking run with `--allow_bad_res`.
  Split conversion out; produce a QC record verifying **Cys192/His340** and the 6UKD hashes before the control run.
- **Stale receptor-conversion outputs:** delete all expected outputs before conversion, verify hashes after
  (`pdbqt_conversion.py:93-100` has the same stale-existence bug).

### 5. Preparation audit
**MMFF94s, cap 2000**, over **every state in the attempt manifest** (not "82 entities"). **Abort before docking** if
any expected non-boron state fails. Today 47/73 silently fail while the manuscript claims "MMFF-optimized", and
`LigandPreparationError` is **caught and converted into a skipped compound** — so the entry point cannot fail loudly
even in principle.
**Stereo:** keep `source_undefined_centers` and `embedded_unassigned_centers` **separate** (assigning tags from 3D
would zero the source field and destroy the evidence for the 13-compound limitation). Require only the *embedded*
set empty. One arbitrary isomer per compound stays a stated limitation.

### 6. Clean redock — no `--resume`
Per the attempt manifest, under the frozen catalog and parameters. **Frozen pre-run SpeB panel manifest** (exact IDs,
roles, source + species hashes, selection rule, the 17-decoy pass/fail population) — the panel is currently
reconstructed dynamically from the library + heavy-atom tolerance + a hard-coded role set and could silently drift.
**Per-state disposition table**: preparation failure / zero-, one-, two-receptor success / timeout / operational_non_fit /
eligibility. Use **`operational_non_fit`** — never "clash" — unless a separate geometric-clash check succeeds.

### 7. Statistics
**Best-receptor is the sole headline** triad statistic (currently 67/53/31) — it answers the actual question: does
the pose the ligand was *ranked by* contact the triad. Report **5XYA and 7EDD separately**. The any-receptor OR is
ensemble-size-dependent, inflated, a different estimand — not co-headlined. Fix the false
`"counted_over": "ligands (best receptor)"` label and the wrong `non_fits_excluded: []`.

**STATE-AMBIGUITY MUST PROPAGATE HERE TOO — it does not stop at the statistical test.** With no primary state there is
**no singular best-receptor triad count** and **no singular Q9D rank**. Selecting one state after the redock to produce
a single number would **recreate exactly the result-conditioned selection this plan forbids** — the same error, one
layer further downstream. Therefore, **preregistered**:
- Triad counts (best-receptor, and per-receptor 5XYA/7EDD) are reported as **ranges over all allowed state
  combinations** — min and max — using the same exhaustive enumeration as the screen. Triad counts carry their OWN
  vocabulary: **`STATE_INVARIANT`** (identical across every combination) / **`STATE_DEPENDENT`** /
  **`INDETERMINATE_*`**. They must NOT reuse `ROBUST_PASS`/`ROBUST_DETECTED`, whose meanings are tied to a
  significance threshold that does not apply to an unthresholded contact count.
- Q9D's rank and score are likewise reported as a **range**, never a point value, whenever any panel member is
  `AMBIGUOUS`.

### 8. Methods note, figures, prose
- **Regenerate `docs/methods/docking_analysis.md`** (Finding 1 invalidated it).
- **Figure 2:** locate Q9D explicitly — `make_figures.py:137` reads `results[0]`, which is affinity-sorted, so it
  prints **dexamethasone's 28 heavy atoms as Q9D's** (Q9D is 25). Plot all **20** panel members with three role styles.
  **It must show BOTH states' scores and the rank RANGE for every ambiguous identity, and report the four-way per-metric
  outcome** (`ROBUST_PASS` / `ROBUST_FAIL` / `STATE_DEPENDENT` / `INDETERMINATE_*`) — a binary pass/fail caption is no
  longer a valid rendering of the result. Identities are never duplicated into the panel (n stays 17 decoys).
- **Figure 4:** show the **state-robust triad RANGE**, not a single corrected statistic, without duplicating identities.
- **Prose:** every number derived from regenerated artifacts, none prescribed. Do **not** pre-write "65th → 67th".
  Fix the README provenance and "nothing hand-entered" claims, the "24 reference compounds" claim, the RDKit
  version, and the vancomycin "five hours" claim.

### 9. Proof
- **Claim registry keyed by stable claim ID**, producing a claim-values artifact with formatter/derivation metadata.
  Raw JSON Pointers are unsafe: rankings and SpeB results are **sorted arrays**, so `/results/5/…` silently resolves
  to a different compound after the redock. Validate README, manuscript, **generated methods note, and figure
  annotations**.
- **Baseline archive + frozen ablation matrix** (D1 species, D2 MMFF, D3 timeout, D4 `--cpu`, D5 dependency/receptor).
  Each contrast is frozen with its exact variant, held-constant input hashes and command — no "where feasible" that
  leaves a post-result choice. Baselines are the **actual archived settings** (the code default is 600s — the 1800/600 split was
  a proposal that never ran). These are **controlled ablations, not unique causal attribution**: one-factor ablations
  around the new configuration cannot decompose interactions. Triggered **only if a headline classification flips**.
  **Diagnostics never replace the primary result.**
- `pytest` green. Preregistered criteria evaluated and reported, whatever they say.

## Risks / open questions
- **Scope.** This is no longer "fix 12 findings" — it is a re-architecture (state-keyed catalog, attempt manifest,
  content-addressed gates, claim registry, preregistration). That is a real cost and should be a conscious choice.
- The SpeB control may legitimately change once the β-lactam states are resolved. That is the purpose; reported
  either way, with ablations.
- Any number surviving the redock unchanged is suspicious and must be re-derived, not assumed.
- Multi-hour redock; wall-clock timeouts are hardware-dependent even at `--cpu 1` — recorded, named as a limitation.
- Cross-machine bitwise determinism is not proven; pinning + `--cpu 1` + path normalisation are in scope, a
  clean-room reproduction is not.

## Out of scope
- Changing seed, exhaustiveness, num_modes, receptors, or box definitions.
- Stereoisomer enumeration.
- Pushing to the remote (PROJECT_CONTEXT.md: "Do not push without explicit user approval").

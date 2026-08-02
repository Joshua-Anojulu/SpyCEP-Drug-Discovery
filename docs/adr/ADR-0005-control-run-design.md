# ADR-0005: Control-run design, box specification, and the `controls_v1` schema

- Status: **Accepted**
- Accepted: 2026-08-02 by Joshua Anojulu. Closes freeze gate 5.
- Carried forward, explicitly NOT resolved by this acceptance: **audit finding C** (the SpeB control
  docked the spent adduct rather than the inhibitor). It invalidates nothing and requires no
  re-docking, but the plan and manuscript still say "inhibitor" where they mean "adduct". Tracked
  below as a follow-up.
- Date: 2026-08-02
- Decision owner: Joshua Anojulu
- Governing plan: `PLAN-control-battery.md` **rev 14** (12 Codex rounds; log in
  `PLAN-REVIEW-LOG-control-battery.md`). Rev 12's `approved-final` was superseded by this ADR's own
  audit finding A; rev 14 actions it and the Round 12 review of it.
- Applies to: `src/spycep_drug_discovery/docking.py` (`require_campaign_seal`),
  `src/spycep_drug_discovery/analysis_population.py`, `scripts/compute_statistics.py`,
  `scripts/make_figures.py`, `scripts/write_docking_methods.py`, and the golden/corruption tests
- Terms: per `CONTEXT.md` — in particular `Control run`, `Ensemble`, `Recovered`, and `Claim`

## Context

The sealed campaign `v2_20260719` produced a null probe-set result **and** a failed SpeB positive
control. A failed control means the null cannot be attributed to the target, so the study is a
cautionary benchmark rather than evidence about SpyCEP's druggability. `PLAN-control-battery.md`
adds a battery of controls to characterise what the pipeline can and cannot resolve.

Three constraints shaped this ADR:

1. **`v2_20260719` is immutable.** It is not re-docked, appended to, or overwritten.
2. **`require_campaign_seal()` asserts `stage_workflows == ["boron", "speb", "tight", "wide"]`**
   (`docking.py:2641`), and `analysis_population.py` hard-codes four manifests at fixed method paths
   (lines 61–64) with pinned source hashes (81–83). Control work does not fit that shape.
3. **The box constants could not be sourced.** Freeze gate 1 originally required a published,
   receptor-independent, ligand-free source for them. No such source exists to be found: the docking
   field sets boxes from ligands (`GATE1-FINDINGS-box-constants.md`). The plan removed the
   quantities rather than inventing a citation.

## Decision

### 1. `controls_v1` is a control run, not a campaign

`CONTEXT.md` now carries `Control run` as a distinct term. `Campaign` keeps its existing meaning
exactly, so **no existing seal changes what it asserts**. This ADR carries only the engineering
consequences.

- **Stage roster:** `CALIBRATION`, `FURIN`, `SPYCEP_NATIVE`, `SPEB_NATIVE`.
- **Own schema version, own sealer path, own validators.** The `controls_v1` seal binds the science
  from the start: content hashes for every stage manifest, receptor, box definition, ligand catalog,
  analysis artifact and tool fingerprint.
- **v2's seal is not retrofitted.** It binds ids, schema versions, the ledger hash and the workflow
  set, and *nothing scientific*. v2's evidentiary support is stated as what it is — separate analysis
  source hashes in `docs/methods/docking_statistics.json` — in both papers. No re-seal, no mutation.
- **Never pooled** with v2, and never selected between on the basis of which is more favourable.

### 2. Consumer migration

Every consumer below hard-codes the four-manifest roster or its fixed paths and needs explicit
version dispatch. **A consumer meeting an unknown schema version fails closed** — it never falls back
to the v2 roster.

| consumer | what must change |
|---|---|
| `analysis_population.py` | manifest roster and fixed method paths (61–64); pinned source hashes (81–83) |
| `docking.py` | `require_campaign_seal()` stage-workflow assertion (2641) |
| `compute_statistics.py`, `make_figures.py`, `write_docking_methods.py` | fixed method output paths |
| golden + corruption tests | all of the above |

v2 analysis must remain readable byte-for-byte after the migration; that is a test, not an intention.

### 3. Box specification — the pinned values

Declared and hashed **before any docking**, and before any coverage quantity is computed.

| element | value |
|---|---|
| R (selection radius from catalytic centroid) | grid: **8, 10, 12 Å** |
| M (bounding-box margin) | grid: **2, 4 Å** |
| cells per receptor | **6**, all run, whole surface reported |
| connectivity contact distance | set **{4.0, 4.5, 5.0 Å}**, unanimity, no primary value |
| bracketing sequence window k | set **{1, 2, 3}**, unanimity, no primary value |
| presence-gate evaluation | all **3 × 3 = 9** combinations of contact distance × k |
| minimum selected atoms | geometric predicate: selection must contain every heavy atom of the catalytic triad/dyad residues |
| catalytic-atom completeness | all triad/dyad atoms present and resolved, else fail closed |
| maximum box edge | none — bounded by construction at ≈ 2(R + M) |

**No free numeric constant remains.** Any unanimity disagreement, from either set in either role, maps
to the single `geometry-sensitive` verdict, which counts as not recovered.

**"Unresolved" is operationalised here** (carried from the Round 6 review). A residue is unresolved if
it is listed in `REMARK 465`, or if any of its backbone atoms (N, CA, C, O) is absent from the
coordinates, or if all its side-chain heavy atoms carry zero occupancy. Alternate conformers are not
unresolved; they are reduced to the highest-occupancy conformer, ties broken by conformer ID, as in
the v2 preparation.

### 4. Endpoints

Primary: rank of the active among its decoy pool by best affinity, per receptor **per grid cell**.
Conservative rank `r = 1 + (better) + (tied)` over `N = 1 + n_decoys`; reported `p = r / N`.
Recovered requires strictly first — no decoy better, none tying — in every draw in **all six cells**.
Secondary, always reported, never substituted: ligand-efficiency rank and symmetry-corrected
heavy-atom pose RMSD. Non-fits take worst rank. Outcome precedence is the §5 tree: void →
geometry-sensitive → coverage-limited → {recovered | box-sensitive | not recovered}.

All four controls are **single-receptor, multi-box**, so none has an `Ensemble` in the `CONTEXT.md`
sense and `ensemble_best_affinity_kcal_mol` does not apply to them.

### 5. Decoy generation

Frozen and archived before generation, hashed with the generator specification: ZINC22 2D tranche
list, download date, per-file SHA-256; RDKit version; exact per-property matching tolerances (MW,
logP, HBD, HBA, rotatable bonds, net formal charge **after final protonation**); fingerprint and
topological-dissimilarity cutoff; dedup rule; the complete primary and spare seed queues, enumerated;
exact pool size per active; number of primary draws; replacement-abort fraction; maximum aborted
draws per system; pool-size sensitivity windows. **Abort if the snapshot cannot be pinned.**

Exclusions are **exact SMARTS**, per active, with class label and literature rationale, plus the
post-hoc count of candidates each removed. **Freeze gate 4 is closed below**: Q9D's warhead is a
diazomethylketone, the frozen class is the alpha-leaving-group ketone family plus the alpha-amido
nitrile chemotype (W1-W5), all five patterns RDKit-verified against positive and negative controls.

## The source audit

Gate 6 requires a structure-by-structure audit before this ADR is accepted. Performed 2026-08-02
against the RCSB data API. **Every value below was read from the API, not recalled.**

| PDB | title (abbreviated) | primary citation | PMID | resolution | ligand | formula | mass |
|---|---|---|---|---|---|---|---|
| 3PTB | Geometry of the reactive site … trypsin | Marquart, Walter, Deisenhofer, Bode, Huber. *Acta Crystallogr B* 39:480 (1983) | none | **1.7 Å** | BEN | — | — |
| 9QWF | Furin (PCSK3) with biphenyl compound 13 (mi3102) | Lange, Boller, Loresch, Bloch, Böttcher-Friebertshäuser, Brandstetter, Dahms, Steinmetzer. *J Med Chem* 68:25157–25170 (2025) | 41319212 | **1.65 Å** | A1JA5 | C32 H41 Cl2 F3 N4 O | **625.595** |
| 5XYA | Crystal structure of a serine protease from *Streptococcus* sp. | Jobichen, Tan, Prabhakar, Nayak, Biswas, Pannu, Hanski, Sivaraman. *Biochem J* 475:2847–2860 (2018) | 30049896 | **3.0 Å** | AES | C8 H10 F N O2 S | 203.234 |
| 7EDD | Crystal structure of a serine protease from *S. pyogenes* | Jobichen, Ying Chong, Hui Ling, Sivaraman. *Biochemistry* 60:1564–1568 (2021) | 33929828 | **2.9 Å** | — | — | — |
| 6UKD | Streptopain + 2S (RCSB title says "nitrile-based"; **it is a diazomethylketone** — finding B) | Woehl, Kitamura, Dillon, Han, Edgar, Nizet, Wolan. *ACS Chem Biol* 15:2060–2069 (2020) | 32662975 | 1.589 Å | Q9D | C18 H18 N2 O5 | 342.346 |
| 2AYW | Trypsin + designed inhibitor in the presence of benzamidine | Sherawat, Kaur, Perbandt, Betzel, Slusarchyk, Bisacchi, Chang, Jacobson, Einspahr, Singh. *Acta Crystallogr D* 63:500–507 (2007) | 17372355 | **0.97 Å** | — | — | — |

**Confirmed as the plan states:**

- **6UKD's primary citation is Woehl et al. 2020, PMID 32662975.** The manuscript's current
  reference [2] (Wang et al. 2015, PMID 26132413) is wrong, exactly as the plan claims.
- **A1JA5 is 625.595 Da** from formula C32 H41 Cl2 F3 N4 O — the plan's 625.6 Da is right, and the
  earlier figure it replaced was wrong.
- **5XYA is the ScpC–AEBSF complex**, PMID 30049896, ligand `AES` =
  4-(2-aminoethyl)benzenesulfonyl fluoride. This closes a long-standing `verify` item.
- **9QWF exists and is a genuine furin complex.** Note it is very new: deposited 2025-04-14,
  released **2025-12-24**, roughly seven months before this audit.

### Audit finding A — resolution co-varies with target, and the plan does not name it

| system | resolution | role |
|---|---|---|
| 2AYW | 0.97 Å | enrichment benchmark (deferred) |
| 9QWF | 1.65 Å | **held-out validation** |
| 3PTB | 1.7 Å | **calibration** |
| 6UKD | 1.589 Å | cross-target |
| 7EDD | 2.9 Å | probe-set application |
| **5XYA** | **3.0 Å** | **target-native** |

**The two SpyCEP structures are ~1.3 Å worse than every other system in the battery.** Resolution is
therefore a fourth factor co-varying with target identity, alongside the three the plan already names
(protease family, ligand charge, covalency). It is also the most mundane competing explanation
available: at 3.0 Å, side-chain positions are poorly determined, and side-chain positions are exactly
what the box rule depends on — the catalytic triad centroid *is* the box centre, and the pocket-lining
set is defined by side-chain heavy atoms. Pose RMSD comparisons are similarly weaker.

A referee will ask whether SpyCEP fails because of the pipeline or because its structures are 3 Å.
That question should be preregistered as a named confound, not answered defensively after review.

**ACTIONED in plan rev 13–14.** The scope paragraph now names resolution as a co-varying factor, the
roster table carries a resolution column, every results table must report it, and a binding rule
forbids any matrix row from attributing a 5XYA or 7EDD outcome to the pipeline, target, scoring
function or preparation without naming low resolution as an alternative of equal standing. The word
"target" is not available for SpyCEP conclusions; they are phrased as being about *this 3.0 Å SpyCEP
structural model under this protocol*.

Round 12 further established that the confound is **disclosed and indirectly probed, but not
bounded**: the R/M grid varies box geometry around the *same deposited coordinates* and so cannot
perturb coordinate uncertainty, and the 3PTB-vs-2AYW contrast is trypsin and may not be used to
constrain any SpyCEP-specific resolution explanation. The reviewer also confirmed 5XYA **can** still
serve as the target-native control in the limited sense that it tests the actual available SpyCEP
co-complex under this protocol — it simply cannot support a clean target-native failure
interpretation without the caveat attached.

### Audit finding B — RESOLVED against the full text. Q9D is a spent diazomethylketone.

Closed 2026-08-02 using the free PMC deposit of the primary paper (**PMC7755099**), plus RDKit
verification of every structure claimed below.

**The RCSB title for 6UKD is wrong, and so was this ADR's first attempt at correcting it.** The title
calls Q9D a "nitrile-based" covalent inhibitor. An earlier revision of this section concluded from the
formula alone that the warhead was a plain **methyl ketone**. Both are wrong, and the truth explains
both errors at once.

**What the paper actually says.** The series began with a reversible nitrile hit (**2477**, IC50
~14 uM) elaborated to **1S** (IC50 1.8 uM); its enantiomer **1R** was inactive (> 40 uM). Then:

> "The nitrile moiety, located within hydrogen-bonding distance to the catalytic cysteine (C192), was
> replaced with covalent-modifying groups chloromethyl ketone (**2S-CMK**) or diazomethylketone
> (**2S**)"

So **compound 2S — the ligand in 6UKD — is a diazomethylketone**, and the nitrile is the chemistry it
*replaced*. The RCSB title describes the series' ancestor, not this deposit. The structure shows a
genuine covalent bond:

> "The naive fo-fc electron density map exhibited unambiguous density for **2S** located within
> the SpeB active site and covalently linked to C192"

Irreversibility is established by jump-dilution ("no change in SpeB activity was measurable in the
presence of **2S**"), with k_inact = 4.1 x 10^-3 s^-1 and k_inact/K_i = 719 s^-1 M^-1.

**Why the deposited formula looked like a methyl ketone.** A diazomethylketone alkylates the cysteine
by expelling N2 and forming -C(=O)-CH2-S-Cys. The PDB component holds only the ligand-side atoms; the
bond to Cys192 is a LINK to the protein. So the component is written as if that methylene carried a
hydrogen — presenting as a methyl ketone, with the diazo nitrogens gone. **`Q9D` is the post-reaction
adduct, not the inhibitor.** Verified with RDKit (2025.09.6):

| species | formula | heavy atoms | MW |
|---|---|---|---|
| **`Q9D` as deposited (adduct)** | **C18H18N2O5** | **25** | **342.351** |
| RCSB deposited values | C18 H18 N2 O5 | 25 | 342.346 |
| **2S parent (diazomethylketone)** | C18H16N4O5 | **27** | 368.349 |
| 2S-CMK (chloromethyl ketone) | C18H17ClN2O5 | 26 | 376.796 |

The deposit matches the adduct exactly and the parent inhibitor not at all — two heavy atoms and
26 Da apart.

### Freeze gate 4 — the warhead SMARTS, verified and hereby frozen

The section 7 exclusion removes known target actives **and reactive analogues of the active's warhead
or ligand class** from the decoy pool. Because the true chemistry is a diazomethylketone rather than a
methyl ketone, the class is the **alpha-leaving-group ketone** family — the classic irreversible
cysteine-protease alkylators — plus the nitrile chemotype, which is a *documented active class against
this very target* and so cannot be allowed to sit in the decoy pool.

| id | class | SMARTS |
|---|---|---|
| W1 | diazomethyl ketone | `[CX3](=[OX1])[CX3H1]=[NX2+]=[NX1-]` |
| W2 | halomethyl ketone | `[CX3](=[OX1])[CX4H2][F,Cl,Br,I]` |
| W3 | acyloxymethyl ketone | `[CX3](=[OX1])[CX4H2][OX2][CX3]=[OX1]` |
| W4 | alpha-amido nitrile | `[NX3][CX4][CX2]#[NX1]` |
| W5 | alpha-amido methyl ketone (the docked adduct form) | `[NX3][CX4][CX3](=[OX1])[CX4H3]` |

**All five compile and were tested, not asserted.** Each matches exactly its intended chemotype and
nothing else, and — the check that matters — **none fires on the negative controls**, including
acetophenone. W5 is therefore specific to alpha-amido methyl ketones and does **not** strip ordinary
ketones from the pool:

|  | W1 | W2 | W3 | W4 | W5 |
|---|---|---|---|---|---|
| Q9D (deposited adduct) | . | . | . | . | **YES** |
| 2S parent (diazomethylketone) | **YES** | . | . | . | . |
| 2S-CMK (chloromethyl ketone) | . | **YES** | . | . | . |
| nitrile congener (1S-like) | . | . | . | **YES** | . |
| acetophenone | . | . | . | . | . |
| ibuprofen | . | . | . | . | . |
| caffeine | . | . | . | . | . |

W2 and W3 are included although no such compound is in this study: they are reactive analogues of the
same warhead class, W2 is literally 2S-CMK from the same paper, and the exclusion rule is about class
membership rather than about which analogues happened to be synthesised.

**Known actives excluded by name in addition to the SMARTS:** 2477, 1S, 1R, 2S, 2S-CMK, 2S-alkyne.

**What a wrong SMARTS would have cost.** Freezing the nitrile pattern implied by the RCSB title would
have stripped the wrong chemotype and left genuine alpha-leaving-group ketones in the pool. Freezing
this ADR's own earlier "alpha-amino methyl ketone" reading would have caught W5 only, leaving
diazomethyl, halomethyl and acyloxymethyl analogues — the actually reactive ones — available as
decoys. Either error moves the rank in the SpeB control, whose failure is the paper's headline result.

### Audit finding C — the SpeB control docks the spent adduct, not the inhibitor

Following directly from B, and **new**: the entity `Q9D_speb_inhibitor` carries **25 heavy atoms**
(`docs/CODEX-CODE-REVIEW-2026-07-13.md`), matching the deposited adduct and not the 27-heavy-atom
parent. So the sealed SpeB positive control docked **the covalent remnant with its warhead already
spent**, under the name "inhibitor".

This changes no number and requires no re-docking. Re-docking the deposited ligand is the ordinary
cognate convention and is exactly what the plan says it does. What it changes is **language and
interpretation**:

- The manuscript calls Q9D "the co-crystallised inhibitor". It is the co-crystallised **adduct**; the
  inhibitor is 2S, a diazomethylketone that is not what was docked.
- `CONTEXT.md` defines an `Active` as having experimental evidence of binding. The adduct has that
  evidence only as a *covalent* species; its non-covalent affinity — the only thing Vina scores — is
  not what the crystal establishes.
- The decoy pool was property-matched at 25 heavy atoms, i.e. to the adduct.
- It sharpens the confound the plan already names. This is not merely "a covalent active scored by a
  non-covalent function"; it is **the spent remnant of a covalent active, scored as though it were a
  reversible binder, with the N2 that did the work absent from the docked structure.** The control
  failing is even less surprising than previously argued, and correspondingly even weaker as evidence
  about the pipeline.

**Recommendation:** amend the plan's section 2 roster and section 5 covalency discussion, and the
manuscript's SpeB section, to say *adduct* where they currently say *inhibitor*, and to state that the
docked species is the post-reaction form. That is a manuscript-claim change and therefore runs the
chain. **Josh's call** — it is precision, not a defect, and nothing computed is invalidated.

## Alternatives considered

- **Widening `Campaign` to cover control work** was rejected. It would change what every existing
  seal asserts, for no benefit beyond avoiding a new term.
- **Versioning v3 in place of a separate control run** was rejected: v3 was not a `Campaign` under
  the four-stage definition, and it would have overwritten v2's tracked method manifests, which are
  written to fixed paths.
- **Sourcing the box constants from pocket detection** (fpocket, CASTp) was rejected in Act 1, which
  chose a triad-centred rule specifically to avoid a pocket-detection dependency that would be hard
  to state for SpyCEP's shallow groove.
- **Picking a single R and M and defending them** was rejected once the search established no
  qualifying source exists. A cited constant would still have permitted post-hoc selection of what to
  report; the grid does not.
- **Retroactively re-sealing v2** to bind its science was rejected as mutation of an immutable
  artifact. If notarisation is wanted it is a new, non-mutating artifact and a separate decision.

## Consequences and limitations

The control run costs six grid cells × four systems × the frozen draw count, tens of core-hours at
the measured 23–27 s per Vina call. Compute is not the constraint.

`recovered` is deliberately hard to reach: all six cells must survive and the active must be strictly
first in every draw in every one of them. The reviewer confirmed this still permits the benchmark's
thesis to be refuted, which is the property that matters.

The grid removes the "which R?" tuning channel but does not make the plan choice-free. The grid's
**membership** is still a declared choice — weaker because it is fixed pre-docking, published in
full, and resolved by transparent strictest-member unanimity, but not nothing. Both papers say so
rather than claiming the box rule is assumption-free.

**AEBSF/5XYA is a new `controls_v1` Claim.** A `Claim` is species key + receptor + **box**, so the
sealed v2 AEBSF result is a different Claim and cannot be reported as the control-battery result. The
Act 1 conclusion that the target-native control "needed no new docking" is retired.

This ADR governs control-run design, the box specification and the schema migration. It makes no
claim about SpyCEP's druggability, licenses no statement about Vina-class docking beyond these six
named systems, and does not modify `v2_20260719`.

## Status of the freeze gates, and the one follow-up

1. ~~Audit finding A~~ — **CLOSED.** Actioned in plan rev 13–14 and reviewed in Round 12.
2. ~~Audit finding B~~ — **CLOSED** against PMC7755099. Warhead is a **diazomethylketone**; `Q9D` is
   the post-reaction adduct. **Freeze gate 4 is closed** with the RDKit-verified W1-W5 SMARTS set.
3. ~~Freeze gate 5~~ — **CLOSED** by this ADR's acceptance.
4. **Audit finding C — OPEN, and carried past acceptance deliberately.** The SpeB control docked the
   spent adduct (25 heavy atoms), not the 27-heavy-atom inhibitor. This ADR is accepted *with that
   recorded*, because it is a precision defect in language rather than a defect in anything computed:
   no number changes and nothing is re-docked. What it still requires is an amendment to the plan
   (section 2 roster, section 5 covalency discussion) and to the manuscript's SpeB section, saying
   *adduct* where they say *inhibitor* and stating that the docked species is the post-reaction form.
   That is a manuscript-claim change and runs the grill -> codex chain.
5. Freeze gates 2 (box spec hashed at run time) and 3 (generator + snapshot archived) remain open.
   Gate 8 is already satisfied: plan rev 14 is `approved-final` over body
   `d3e99bd8d21b038f13dd10dea55147b6913af35ebb97b1652f38f31b89650d21`.

**A note on what the audit was worth.** It was specified as a formality — confirm citations and
masses before accepting an ADR. It confirmed all six entries and the two corrections the plan already
claimed, and it also caught a wrong warhead class that would have corrupted the SpeB decoy pool, and
a resolution confound that no review round had surfaced because no reviewer had the deposition
metadata in front of it. Gate 6 earned its place.

Signed: Joshua Anojulu, 2026-08-02

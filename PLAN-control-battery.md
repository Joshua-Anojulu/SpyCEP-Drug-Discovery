---
review_provenance:
  status: approved-final
  rounds:
    - round: 1
      reviewer: codex
      cli_version: codex-cli/0.145.0
      session_id: 019fbd48-3eb2-7ac3-94c3-36a72b51471f
      verdict: REVISE
      findings: 27
      accepted: 24
      body_sha256: unrecoverable
      body_sha256_note: >-
        The rev-1 body was overwritten in place before its hash was computed and the file was
        untracked, so no copy survives. Recorded as unrecoverable rather than back-filled with
        the hash of a body Round 1 never saw. Round 1 is therefore historical context, not a
        hash-bound verdict.
    - round: 2
      reviewer: codex
      cli_version: codex-cli/0.145.0
      session_id: 019fbd48-3eb2-7ac3-94c3-36a72b51471f
      verdict: REVISE
      findings: 20
      accepted: 19
      body_sha256: 9fc8771cc0b59aacb3d8db6ab6d1d0aca331d4dc0229eaf5ba961c62dc9c6dcb
    - round: 3
      reviewer: codex
      cli_version: codex-cli/0.145.0
      session_id: 019fbd48-3eb2-7ac3-94c3-36a72b51471f
      verdict: REVISE
      findings: 13
      accepted: 13
      body_sha256: ed1effd9fc4499cbb3f5bc5c4d1d5fa13dac70bee28ab8af044eb23841dde6a0
    - round: 4
      reviewer: codex
      cli_version: codex-cli/0.145.0
      session_id: 019fbd48-3eb2-7ac3-94c3-36a72b51471f
      verdict: REVISE
      findings: 5
      accepted: 5
      body_sha256: d1a459f124e62edf4c5aff622f3f626713cbb0963edd4a9be2c9e2380492f503
    - round: 5
      reviewer: codex
      cli_version: codex-cli/0.145.0
      session_id: 019fbd48-3eb2-7ac3-94c3-36a72b51471f
      verdict: REVISE
      findings: 1
      accepted: 1
      non_blocking_notes: 3
      body_sha256: d9d12a62040f71b5e32125da8ae4ae8697eedf934b89a3a005ea6eb09a073d03
      note: >-
        Original MAX_ROUNDS=5 cap reached at this round. The single blocking finding and all
        three non-blocking notes were actioned. The author then raised MAX_ROUNDS to 6 to seek
        an APPROVED verdict bound to the final body hash.
    - round: 6
      reviewer: codex
      cli_version: codex-cli/0.145.0
      session_id: 019fbd48-3eb2-7ac3-94c3-36a72b51471f
      verdict: APPROVED
      findings: 0
      non_blocking_notes: 3
      body_sha256: 8c63e1e7096f0b2161005e5dec1ae0584a4ac79e4a1ab27ed9fc4839278fc9d1
      note: >-
        Author raised MAX_ROUNDS from 5 to 6 so a verdict could bind to the final body. The
        three non-blocking notes were deliberately NOT applied to the body: doing so would
        change body_sha256 and downgrade this approval to approved-stale. They are recorded in
        the review log and carried into ADR-0005.
    - round: 7
      reviewer: codex
      cli_version: codex-cli/0.145.0
      session_id: 019fbd48-3eb2-7ac3-94c3-36a72b51471f
      verdict: REVISE
      findings: 5
      accepted: 5
      body_sha256: 2a14e0b7a3f7832f0fc19974d554d87a8d93fd5372d97bf2cc70aba5d7f17abb
      note: >-
        Review of the rev-8 grid rewrite, after the rev-7 APPROVED was deliberately superseded.
        Found that the disclosure sets still had primary values deciding outcomes, that the
        minimum-surviving-cell rule was a favourable-remnant path, that the 20-32 A span was an
        upper bound not a span, and that "widening is always conservative" was false.
    - round: 8
      reviewer: codex
      cli_version: codex-cli/0.145.0
      session_id: 019fbd48-3eb2-7ac3-94c3-36a72b51471f
      verdict: REVISE
      findings: 3
      accepted: 3
      non_blocking_notes: 2
      body_sha256: 55e9ec1d9a41fcb6e96facb3f98258bbef6b07ac3ff920ed90c8d763dbad4fc7
      note: >-
        All three were internal contradictions introduced by rev 9's own rewrite, not new science.
        The two non-blocking notes affirmatively cleared the unanimity construction as sound and
        confirmed all-six-cell survival still permits the thesis to be refuted.
    - round: 9
      reviewer: codex
      cli_version: codex-cli/0.145.0
      session_id: 019fbd48-3eb2-7ac3-94c3-36a72b51471f
      verdict: REVISE
      findings: 1
      accepted: 1
      non_blocking_notes: 3
      body_sha256: 3d500bbaab56c91832d62a0fdbccaddba8256f30e13be92a47a33733cb5e77ee
      note: >-
        One ungated spatial threshold: the bracketing rule still referred to "the hashed contact
        distance" after that single value had been replaced by a unanimity set, so it named
        nothing. Both stale-wording notes were also actioned rather than deferred. The precedence
        tree was affirmatively cleared as exhaustive and mutually exclusive.
    - round: 10
      reviewer: codex
      cli_version: codex-cli/0.145.0
      session_id: 019fbd48-3eb2-7ac3-94c3-36a72b51471f
      verdict: REVISE
      findings: 1
      accepted: 1
      non_blocking_notes: 2
      body_sha256: b8b33be9a7fce6d02271d3013d59dbfabdd823d1aa740c23d2a68c609e6e1460
      note: >-
        Rev 11 introduced an "integrity-sensitive" outcome in section 3 while section 5 recognised
        only a k-based "geometry-sensitive" verdict, so a disagreement arising from the bracketing
        contact distance mapped to no verdict at all. Collapsed to one verdict covering every
        unanimity disagreement; freeze gate 2 now binds the endpoint consequence, not just the
        input. Both non-blocking stale-wording notes actioned rather than deferred.
    - round: 11
      reviewer: codex
      cli_version: codex-cli/0.145.0
      session_id: 019fbd48-3eb2-7ac3-94c3-36a72b51471f
      verdict: APPROVED
      findings: 0
      non_blocking_notes: 1
      body_sha256: b7564d40b1cfbb8a9718988dd65d6d627364f09b15c75904d886f5dfcea7b1c0
      note: >-
        Approved over the final body. The single non-blocking note (one superseded sentence in
        Risks) was deliberately NOT applied: it is stale prose, not a reproducibility defect by
        the reviewer's own assessment, and editing the body would change body_sha256 and
        downgrade this to approved-stale. Carried to the first post-freeze editorial pass.
    - round: 12
      reviewer: codex
      cli_version: codex-cli/0.145.0
      session_id: 019fbd48-3eb2-7ac3-94c3-36a72b51471f
      verdict: REVISE
      findings: 2
      accepted: 2
      non_blocking_notes: 1
      body_sha256: 5d9b820c8e8208965b47c924cd67efc5505aefb527667a2e45f08fe0483764bf
      note: >-
        Rev 13 stated the resolution constraint in the scope paragraph but let outcome-matrix rows
        outrun it ("the SpyCEP null becomes evidence about the target"), and overclaimed the
        confound as "bounded". The R/M grid varies box geometry around the SAME deposited
        coordinates and so cannot bound coordinate uncertainty; the 3PTB-vs-2AYW contrast is
        trypsin and cannot constrain a SpyCEP-specific explanation. Also confirmed 5XYA remains
        usable as target-native in the limited sense, with the caveat attached.
    - round: 13
      reviewer: codex
      cli_version: codex-cli/0.145.0
      session_id: 019fbd48-3eb2-7ac3-94c3-36a72b51471f
      verdict: APPROVED
      findings: 0
      non_blocking_notes: 1
      body_sha256: d3e99bd8d21b038f13dd10dea55147b6913af35ebb97b1652f38f31b89650d21
      note: >-
        Approved over the final body. The binding rule after the outcome matrix was judged strong
        enough to close the resolution caveat across every row, the abstract and the conclusions;
        the mitigation language was judged honest; no ungated endpoint-affecting quantity found.
        The single non-blocking note (one stale Risks sentence, flagged in Rounds 11 and 13 alike)
        was deliberately NOT applied: editing the body would change body_sha256 and downgrade this
        to approved-stale. Carried to the post-freeze editorial pass.
  historical_cross_model_review: true
  final_body_cross_model_approved: true
  final_body_sha256: d3e99bd8d21b038f13dd10dea55147b6913af35ebb97b1652f38f31b89650d21
  superseded_approvals:
    - round: 6
      body_sha256: 8c63e1e7096f0b2161005e5dec1ae0584a4ac79e4a1ab27ed9fc4839278fc9d1
      superseded_by: rev 8
      note: >-
        Rev 7 held a genuine APPROVED bound to this hash. Deliberately superseded: freeze gate 1
        proved unsatisfiable (no receptor-only, ligand-free source for the box constants exists to
        be found), a defect the approval could not have caught because it was explicitly
        conditional on gate 1 being closable.
    - round: 11
      body_sha256: b7564d40b1cfbb8a9718988dd65d6d627364f09b15c75904d886f5dfcea7b1c0
      superseded_by: rev 13
      note: >-
        Rev 12 held a genuine APPROVED bound to this hash. Deliberately superseded after the §9
        source audit (ADR-0005) established from RCSB deposition metadata that crystallographic
        resolution co-varies with target — 5XYA 3.0 A and 7EDD 2.9 A against 1.59-1.7 A for every
        other battery system. No review round could have caught it: no reviewer had the deposition
        metadata. Rev 13 names it in the scope paragraph, the roster and the risks.
  degraded_rounds: []
---

# Plan: control battery + two-paper split (rev 14)

_Act 1 locked via grill-with-docs — Claude + Joshua Anojulu. Rounds 1–5 returned REVISE; Round 6
returned APPROVED over rev 7. That approval was then deliberately superseded when freeze gate 1
proved unsatisfiable — no receptor-only, ligand-free source for the box constants exists to be found
— so rev 8 replaced the single-value box with a declared R/M grid and removed every constant that
needed a source. Rounds 7 and 8 returned REVISE on that rewrite with five and three findings, all
accepted, as were the single findings of Rounds 9 and 10; Round 11 APPROVED rev 12. The §9 source
audit (ADR-0005) then surfaced a confound no review round had seen — crystallographic resolution
co-varies with target — so rev 13 named it and that approval was superseded in turn. Round 12 then
found the caveat had not been propagated into the outcome matrix and that the mitigations were
overclaimed; both accepted. This is rev 14. NOT yet frozen — see §Freeze conditions. Terms per CONTEXT.md._

## Goal

Characterise what this docking pipeline can and cannot resolve on a small, named set of protease
systems, and interpret the existing SpyCEP probe-set result against that characterisation.

**Scope of the claim, stated narrowly and deliberately.** Conclusions are limited to *this frozen
AutoDock Vina 1.2.7 pipeline on these named receptor–ligand systems*. This is a **diagnostic case
series**, not a factorial design: there is no target-native/non-covalent control available, and
target identity, protease family, ligand charge, covalency **and crystallographic resolution** all
co-vary across the systems. Nothing here establishes what "Vina-class docking" supports across
protease anti-virulence campaigns in general, and no sentence in either paper may claim that.

**Resolution is named explicitly because it is the most mundane competing explanation available.**
The two SpyCEP structures are **3.0 Å (5XYA)** and **2.9 Å (7EDD)**, against 1.7 Å (3PTB), 1.65 Å
(9QWF), 1.59 Å (6UKD) and 0.97 Å (2AYW) — roughly 1.3 Å worse than every other system in the battery,
and perfectly confounded with target identity. This matters mechanically, not just rhetorically: the
box rule is built on side-chain heavy atoms, the catalytic triad centroid *is* the box centre, and
side-chain positions are poorly determined at 3.0 Å. Pose RMSD comparisons are correspondingly
weaker. **No failure on 5XYA or 7EDD may be attributed to the pipeline, the target or the scoring
function without stating that a lower-resolution receptor is an untested alternative explanation**,
and resolution is reported in every results table alongside the outcome. Surfaced by the §9 source
audit (ADR-0005), not by any review round.

## Approach

### 1. ADR-0005, before any code

Records the control-run design, the frozen endpoints and the outcome matrix, versions the campaign
schema, and pins the box specification of §3 (the R/M grid, the two unanimity sets, the two geometric
predicates) and the generator parameters of §7. Per §6 it carries the
*engineering* consequences of the campaign/control-run split; the terminological distinction itself
is already settled in `CONTEXT.md` and is not reopened here.

### 2. The receptor roster (complete and frozen)

| system | PDB | protein | family | active | covalent | **resolution** | cofactors to retain | role |
|---|---|---|---|---|---|---|---|---|
| trypsin | 3PTB | β-trypsin | S1 | benzamidine (`BEN`) | no | 1.7 Å | Ca²⁺ ×1 | calibration (§4) |
| furin | 9QWF | furin/PCSK3 | S8 | `A1JA5` (mi3102, **625.6 Da** per deposited formula C₃₂H₄₁Cl₂F₃N₄O) | no | **1.65 Å** | Ca²⁺ ×3 | held-out validation (§4) |
| SpyCEP | 5XYA | SpyCEP/ScpC | S8 | AEBSF (`AES`) | yes | **3.0 Å** | Ca²⁺ (per entry) | target-native |
| SpyCEP | 7EDD | SpyCEP/ScpC | S8 | — | — | **2.9 Å** | per entry | probe-set application only |
| SpeB | 6UKD | streptopain | C47 papain | Q9D | yes | 1.59 Å | — (nitrate removed) | cross-target |
| trypsin | 2AYW | β-trypsin | S1 | DUD-E TRY1 actives | no | 0.97 Å | per entry | enrichment benchmark (§7, deferred) |

Six receptor structures, not four. **Every singular active–receptor pair above is cognate
re-docking** — 3PTB contains BEN, 9QWF contains A1JA5, 5XYA contains AES, 6UKD contains Q9D. Cognate
status is therefore *not* a distinguishing feature of the SpyCEP result and must not be presented as
one; it is a property of the whole battery, and it means every one of these measures **pose/rank
recovery under the most favourable available conditions**, never cross-docked discrimination.

**Cofactor retention rule** (target-independent, frozen before preparation): retain any heterogen
annotated as structurally or catalytically necessary — metal ions coordinated by the protein,
including all Ca²⁺ above. Remove crystallisation additives (sulfate, nitrate, DMSO, glycerol) and the
co-crystallised active. The §2.1 blanket "remove non-polymer heterogens" rule is **replaced**: applied
uncritically it strips trypsin's structural calcium and furin's three Ca²⁺, which would invalidate
both non-covalent controls.

### 3. Box rule — a deterministic, active-blind algorithm

The previous "chosen to contain the primary specificity pocket" was not an executable rule and was
circular for SpyCEP. Replaced by an algorithm whose inputs are fixed in advance:

**Allowed inputs:** protein ATOM records, and the coordinates of **retained cofactors** (§2). Round 2
was right that a strict ATOM-only rule contradicts the cofactor-retention rule — a calcium the plan
calls pocket-critical cannot simultaneously be invisible to the geometry that defines the pocket.
Cofactors are admitted because the circularity being guarded against is *ligand*-derived, and a
retained metal ion is part of the receptor, not the answer being sought.

**Prohibited inputs:** the coordinates of the co-crystallised active, any other ligand HETATM, and
any feature derived from either. This prohibition is the whole point of the rule.

1. Compute the centroid of the catalytic triad/dyad side-chain heavy atoms.
2. Select all allowed heavy atoms within a radius R of that centroid.
3. Box = axis-aligned bounding box of that selection, expanded by a margin M.
4. **R and M are not chosen. They are grid axes**, and the same grid is applied to all six receptors.
5. The algorithm's exact inputs and outputs are hashed per receptor **per grid cell**.

**The R/M grid replaces the single-value box, and this is the rev-8 change** (see §Gate 1 below for
why). Rather than select one R and one M and defend them, every control is run at **every cell of a
declared grid** and the whole surface is reported:

| axis | declared values | rationale |
|---|---|---|
| R | 8, 10, 12 Å | with M, caps box edges at ≈ 20–32 Å (an upper bound, not a span — see below) |
| M | 2, 4 Å | — |

**Six cells per receptor.** 2(R + M) is an **upper bound** on each box edge, not the edge itself
(Round 7 #4 — rev 8 asserted the grid "spans ≈ 20–32 Å", which was an overclaim). The selection is
the atoms within R of the centroid, and its axis-aligned bounding box is only ≈ 2R when those atoms
surround the centroid. **At a shallow surface groove the selection is one-sided and the box comes out
markedly smaller and off-centre** — which is exactly SpyCEP's situation and the reason the box rule
was hard to write in the first place. What can honestly be claimed is the cap: **no cell's box edge
exceeds ≈ 20–32 Å**, which holds the search space inside the range the docking literature reports as
ordinary practice for a focused box. The literature supplies a bracket, not a point (§Gate 1), and a
cap is what a bracket licenses.

**Actual per-cell box dimensions are a reported output for every receptor and every cell**, never
assumed from R and M. Anisotropy — a box much smaller than its bound in one or more axes — is
disclosed alongside them, because it is a direct measure of how open the site is and is a result in
its own right for the shallow-groove target.

**Why a range is defensible where a point was not.** A single R silently determines the answer, so it
needs external grounding. A grid does not determine the answer; it **exposes the answer's dependence
on the choice**. The requirements on the grid are that it be fixed before any docking and wide enough
to contain any value a competent practitioner would have picked.

**Widening the grid is *not* neutral, and rev 8 was wrong to call it "always conservative"**
(Round 7 #5). Adding cells makes a clean `recovered` call harder — but because disagreement across
cells is scored as **box-sensitive** and box-sensitive counts as not recovered, widening also makes
the pipeline look more fragile, **which is the direction that favours this paper's thesis**. The
honest statement is the narrow one: *widening is conservative against a clean recovery call, and
biased towards the benchmark's own conclusion.* It is therefore permitted **only before freeze and
only before any endpoint, coverage or integrity result exists** for any system. Narrowing the grid
after freeze is prohibited outright.

**Tuning becomes structurally impossible rather than merely forbidden.** Every cell is reported, so
there is no favourable cell to select. This is a stronger guarantee than a cited constant would have
given, since a citation constrains only the value and not what is done with the result.

**Compute is bounded and cheap.** Six cells × four control systems × (1 active + frozen decoy pool) ×
the declared number of draws, at a measured median 23–27 s per Vina call at `--cpu 1`, is tens of
core-hours. Compute was never the obstacle in this project and is not one here.

**Active-site-relevant cofactors must lie inside the final box.** Round 3 was right that the rev-3
wording ("every retained cofactor within R") was a tautology: an allowed step-2 input is inside the
bounding box of the step-2 selection by construction, so the check could never fail. The real
requirement is about cofactors the *chemistry* needs, wherever they sit:

- A retained cofactor is **active-site-relevant** if it is coordinated by any pocket-lining residue
  (defined below) or by the catalytic triad/dyad, per the deposited structure's annotation.
- Every active-site-relevant cofactor must lie inside the final box, **evaluated per grid cell**. A
  cell whose box excludes one is a **box-rule failure for that cell**, reported as such and dropped
  from that system's surface — never worked around by enlarging the box for one system alone.
  Because R is gridded, a cofactor may sit inside the box at R = 12 Å and outside it at R = 8 Å; that
  is a legitimate and informative cell-level difference, not a defect to smooth over.
- Retained cofactors that are structurally necessary but not active-site-relevant (distal stabilising
  metals) are kept in the receptor and are *not* required to be inside the box.

**"No defensible cleft" is a mechanical predicate, not a judgement call.** It is evaluated
**per grid cell**, and the algorithm returns this outcome — a reportable result, never an error to
work around — if any of the following holds:

- the step-2 selection does not contain every heavy atom of the catalytic triad/dyad residues;
- any catalytic triad/dyad atom is absent or unresolved in the deposited coordinates;
- the selected atom set is **not a single connected component at every one of 4.0, 4.5 and 5.0 Å**.

**Connectivity is decided by unanimity, not by a primary value** (Round 7 #1). Rev 8 declared 5.0 Å
primary and merely *reported* the other two, which left 5.0 Å determining whether a cell survives —
a single unsourced threshold wearing a disclosure set as a disguise. There is now no primary value:
a cell survives only if the selection is connected under **every** conventional contact distance, and
**any disagreement across the three is itself reported as a geometry-sensitive finding**. This has no
docking cost — it is pure geometry — and it eliminates the parameter rather than defending it.

The former maximum-box-edge clause is gone: the edge cannot exceed 2(R + M) and both are capped by
the grid, so it could never fire independently.

**Ordering, which Round 2 identified as the live loophole.** The grid, and every threshold below, are
declared and hashed **before any coverage quantity is computed for any system**. The
structure-by-structure source audit (§9) is explicitly split so that its ligand-geometry component
runs *after* that hash.

Once hashed, nothing here may change except via a §4 Class II protocol version, and **never in
response to any result from the held-out or control systems** (9QWF, 5XYA, 6UKD). The narrower
wording is deliberate: see §4, where 3PTB is a disclosed training system and its calibration result
*can* force a versioned change. Rev 3 claimed the constants never change in response to a ranking
result while §4 permitted exactly that on calibration failure — a contradiction Round 3 caught.

### Gate 1 — why there are no longer any constants to source

Revisions 4 through 7 required the box constants to come from a published, receptor-independent,
ligand-free source, and made that a hard freeze gate rather than naming a citation, on the grounds
that inventing one would be the fabrication `CLAUDE.md` rule 4 forbids. **A literature search on
2026-08-02 established that no such source exists to be found** (`GATE1-FINDINGS-box-constants.md`),
and the way it failed is itself a result:

- **DUD-E** (Mysinger et al. 2012) sets its box from the **ligand** — min/max of ligand coordinates,
  padded 12.5 Å, 30 Å floor. The field's reference benchmark uses precisely the circularity this
  section bans.
- **Feinstein & Brylinski 2015** sets the box edge at **2.9 × the radius of gyration of the docking
  compound** — ligand-derived, and compound-specific, so it cannot yield one value held constant
  across six receptors.
- Centroid-of-catalytic-residues **centring** is established apo practice and is citable. But every
  source then sizes the box "according to expected ligand size, typically 20–30 Å" — reaching for the
  ligand at exactly the step that must not.

So the constants were unsourceable because **the docking field sets boxes from ligands**, and an
active-blind rule has nothing to borrow. Rather than weaken the requirement, rev 8 removes the thing
that needed sourcing. **After this revision no free numeric constant remains:**

| former constant | disposition in rev 8 |
|---|---|
| **R**, **M** | Not chosen — **grid axes**, whole surface reported (above). |
| **maximum box edge** | **Deleted.** Bounded by construction: the edge cannot exceed 2(R + M), and R and M are capped by the grid. It was never an independent quantity. |
| **minimum selected-atom count** | **Replaced by a geometric predicate with no free parameter:** the step-2 selection must contain *every heavy atom of the catalytic triad/dyad residues themselves*. A selection that does not even contain the catalytic residues is degenerate by definition, not by threshold. |
| **catalytic-atom completeness** | Never numeric. All triad/dyad atoms present and resolved, or the system fails closed. |
| **contact distance** (connectivity) | **No primary value.** Declared set {4.0, 4.5, 5.0 Å}; a cell passes the connectivity predicate only if the selection is a single connected component at **every** value in the set, and **disagreement across the set is a geometry-sensitive outcome** (§5), not a footnote. Convention is genuinely unsettled across those three values, which is why none of them is allowed to decide alone. Costs nothing — geometry, not docking. |
| **sequence window k** | **No primary value.** Declared set {1, 2, 3}; a system passes the presence gate only if it passes at **every** k in the set, and **disagreement across the set is a geometry-sensitive outcome** (§5). k is two-sided — a larger k gates more residues and so excludes more systems — so it is resolved by unanimity rather than argued for. Also pure bookkeeping, no docking. |

**The principle behind the last two rows**, stated so it can be applied to anything added later: a
threshold that cannot be sourced is not defended, it is **disclosed across the plausible range**, and
disagreement across that range is published rather than resolved. A quantity that changes the verdict
depending on which conventional value is chosen is a fact about the pipeline's fragility, and this is
a paper about pipeline fragility.

**What gate 1 now requires** is therefore not a citation but a declaration: the grid, the two
unanimity sets, and the two geometric predicates, fixed and hashed before any docking. The
admissibility criteria that rev 7 applied to a source no longer have anything to apply to.

**Coverage check, per grid cell.** After each cell's box is fixed, report whether *every
crystallographic heavy atom* of the cognate active lies inside it with margin ≥ M/2 **for that cell's
M**. This is disclosed diagnostics; with R and M gridded it cannot be an input to choosing them,
because nothing is chosen. **A failed coverage check is preregistered as a box-rule failure for that
cell, not as scoring evidence** — an active that fails in a box that does not contain it tells us
nothing about scoring.

**A cell that fails coverage, or returns "no defensible cleft", is excluded and the exclusion is
reported with its reason. A system with any excluded cell can never be called `recovered`**
(Round 7 #3). Rev 8's "minimum surviving cells" rule was a favourable-remnant path: a system could
shed the small or awkward cells to coverage failures and still be called recovered on the large ones
that survived, which is selection by attrition rather than by choice. The minimum-cell threshold is
therefore **deleted** — it was itself an unsourced constant — and replaced by:

- **All six cells must survive** for a clean `recovered` call. Anything less is reported as
  **coverage-limited** and counts as **not recovered** (§5).
- A system where **no** cell survives is **voided**. Per §5's coverage table, a voided system does not
  void the control run.
- Cell-level survival counts and reasons are published for every system, so a surface computed over
  four cells is never presented as though it came from six.

This is deliberately strict: a partial surface cannot support a clean recovery claim, and saying so
costs nothing here because the full surface is published either way.

**Pocket-lining residue, defined mechanically.** A pocket-lining residue is any residue contributing
at least one heavy atom to the step-2 selection.

**The integrity gate cannot key off that set alone, and rev 3's did** (Round 3 #6). A residue absent
from the coordinates contributes no atoms, so it is never selected, so a selection-based gate can
never report it missing — the check was structurally incapable of catching the thing it existed to
catch. The gate is therefore split in two:

1. **Presence gate, from the deposited record rather than the coordinates.** For each receptor, take
   the reference sequence and compare: any catalytic triad/dyad residue, any pocket-lining residue,
   and any **bracketing residue** (defined immediately below) that is **absent from the coordinates**
   (`REMARK 465`), **unresolved**, or **engineered away** (`SEQADV`) fails the system closed.

   **Bracketing residue, defined mechanically** (Round 4 #2 — rev 4's "structurally bracketing the
   selected region" was a phrase, not an algorithm). A residue is bracketing if **either**:
   - it lies within **k** positions in the chain sequence of any pocket-lining residue, evaluated at
     **k = 1, 2 and 3 with no primary value** — the system passes the presence gate only if it passes
     at **all three**, and any disagreement across them is a geometry-sensitive outcome (§5)
     (Round 7 #2: declaring k = 2 primary and merely reporting the others left k = 2 deciding the
     gate, so a system failing only at k = 3 would still have been scored); **or**
   - it contributes a heavy atom within a **contact distance** of any step-2 selected atom, using the
     **same declared set {4.0, 4.5, 5.0 Å} under the same unanimity rule** — the system passes only
     if it passes with the bracketing set computed at *every* distance in the set (Round 9: rev 10
     said "the hashed contact distance", which no longer named anything, leaving an ungated spatial
     threshold able to change the bracketing set and so whether a system is scored or voided).

   The two clauses are therefore evaluated over all **3 × 3 = 9** combinations of contact distance and
   k, and the presence gate passes only if it passes in all nine; any disagreement is an
   **geometry-sensitive** outcome (§5) — the single verdict that covers *every* unanimity
   disagreement, whatever its source. This is pure bookkeeping — no docking — so exhaustive
   evaluation costs nothing. Both clauses are computed from the deposited chain and the step-2 selection only. The bracketing
   set is itself part of the hashed box/integrity payload (§8), so two runs that disagree about which
   residues were gated cannot compare as identical.
2. **Identity gate, against the reference sequence and not the deposited one** (Round 3 #7). Rev 3
   said "mutated relative to the deposited sequence", which is the wrong baseline: an engineered
   mutation already present in the deposited sequence matches itself and passes. This project has
   already been bitten by exactly that case and handled it correctly — **5XXZ was excluded because
   UniProt Q3HV58 annotates active-site positions 151/279/617 while PDB SEQADV mutates H279 and S617
   to alanine**, a comparison against the reference annotation, not the deposit. The gate follows that
   precedent: catalytic and pocket-lining residues are compared to the target's reference sequence
   (UniProt) and to explicit expected residue identities.

A system failing either gate is excluded from scoring claims, and the exclusion is reported.

### 4. Calibration vs validation — replacing the circular sensitivity control

Round 1 was right that "fails → misassembled → fix until it passes" is a tuning loop, and that one
target passing cannot validate another target's preparation, box or protonation. Round 2 was right
that rev 2 left the loop unbounded.

- **3PTB/benzamidine is the disclosed calibration system — and it is a training system, named as
  such** (Round 3 #4). Its ranking result can and does feed back into the protocol, so it is not
  held out and nothing about it is blind. Every claim in either paper that touches 3PTB says so.
  Calibration results are reported, never used as evidence that other systems are sound.
- **9QWF/furin is held out.** It is docked exactly once, under the final frozen protocol, and is
  never used to diagnose or tune anything.
- Passing calibration licenses exactly one statement: the pipeline is not grossly misassembled *on
  3PTB*. It does not convert any other system's failure into a scoring failure.

**Two classes of calibration failure, distinguished before the fact:**

- **Class I — infrastructure defect.** A crash, a malformed manifest, a mis-parsed file, a unit
  error, a wrong receptor loaded. Fixing one does not change what the protocol *measures*. Fixes are
  permitted, are logged, and force a re-run of all systems.
- **Class II — scientific parameter change.** Any change to the R/M grid, either unanimity set,
  either geometric predicate, the
  protonation rules, the cofactor rule, the decoy criteria, or the endpoints. Each creates a **new
  protocol version** and forces a full re-run of every system under it.

**Class II changes are capped at two.** If calibration still fails under the third protocol version,
the battery stops and the failure is reported as the result. **The complete history of every failed
calibration, both classes, is published** — a protocol that took three attempts to calibrate is a
finding about the pipeline, not an embarrassment to bury.

**Held-out bug-discovery rule (blinded, fail-closed).** If 9QWF exposes a defect, the plan must not
force a choice between hiding a bug and misreporting one as a scientific failure. So: manifest,
schema, receptor-preparation and box-rule integrity are checked on 9QWF **before its endpoint is
read**, and any Class I defect found at that stage aborts the protocol version, is fixed, and forces
a re-run — with the furin endpoint still unread. **Once the endpoint is read, nothing about the
protocol may change on furin's account.** Endpoint failure never licenses tuning.

**If a Class I defect is discovered *after* the furin endpoint has been read** (Round 3 #8 — rev 3
left this gap, and the gap creates pressure either to publish a result known to be buggy or to
quietly re-run a control that is no longer blind):

1. The protocol version is **invalidated**. No result from it is reported as held-out evidence.
2. **The fact that 9QWF was consumed is published.** Once its endpoint has been seen, furin can never
   again be held out for this pipeline — that is a permanent, disclosable loss.
3. The battery then either recruits a **new held-out target**, frozen and blinded before use, or
   proceeds with furin **explicitly relabelled as a non-held-out control**, with every claim resting
   on it downgraded accordingly. Silently re-running furin and calling it held out is prohibited.

### 5. Frozen endpoints and the outcome matrix

**Primary endpoint, per system:** rank of the active among its decoy pool by best affinity at that
system's receptor and box.

**Receptor and box multiplicity, stated per control** (Round 2: "best ensemble affinity" was
undefined here). All four control systems are **single-receptor, multi-box**: 3PTB, 9QWF, 5XYA and
6UKD each contribute one receptor, evaluated at each of the six §3 grid cells. They therefore still
have **no ensemble** in the CONTEXT.md sense — an ensemble is multiple receptor *conformations*, and
six boxes on one conformation is not that — so the v2 aggregate
`ensemble_best_affinity_kcal_mol` across 5XYA and 7EDD does not apply to them. The control endpoint
is the best affinity over poses **at one receptor in one grid cell**, and is named that way in every
table. Grid cells are never pooled into a single affinity. Only the §9 probe-set application, which
spans 5XYA and 7EDD, is an ensemble result.

**Recovery and ties, conservatively.** Per CONTEXT.md, the active is **recovered** only if **no decoy
scores better and no decoy ties it**. Round 2 was right that midrank plus "exact r/n" was internally
inconsistent and that a first-place tie is not a recovery.

**The rev-3 formula was wrong and is corrected** (Round 3 #2). Rev 3 wrote `p = (better + tied) / n`,
which returns `p = 0` when the active is strictly first — not a probability, and it would have
reported an impossible value for the single most important outcome in the battery. The conservative
rank of the active is

    r = 1 + (decoys scoring better) + (decoys tying)

over `N = 1 + n_decoys`, the whole ranked pool including the active itself, and the reported exact
random-rank probability is `p = r / N`. A strictly-first active therefore gets `r = 1` and
`p = 1/N`, which is the correct floor. Ties are still disclosed, never silently broken.

**Aggregation across decoy draws, preregistered** (Round 3 #3). §7 requires multiple independent
draws, but recovery is a binary outcome per system and a rank *distribution* does not by itself
decide it — rev 3 added the draws without saying how they resolve. The rule, fixed in advance:

- A system is **recovered** only if the active is strictly first in **every** frozen draw.
- Recovery in some draws but not others is a distinct reported outcome, **"unstable"**, and counts as
  **not recovered** for the outcome matrix.
- The per-draw ranks and the full distribution are reported in all cases, including when every draw
  agrees. Selecting, averaging or best-of-ing across draws is prohibited.

**Aggregation across grid cells, preregistered.** The primary endpoint is evaluated independently in
each surviving grid cell, over every draw in that cell. The system-level outcome is then:

The five outcomes are **not naturally disjoint** — a connectivity disagreement also causes a cleft
failure, which also excludes a cell — so rev 10 fixes an **explicit precedence tree** (Round 8 #2).
It is evaluated top to bottom, and **the first matching rule wins and no other outcome is reported
as the system's verdict**:

1. **Void** — no cell survived, or the system failed the presence/identity gate outright. The system
   has *no outcome*; it goes to the coverage table below, not to the outcome matrix.
2. **Geometry-sensitive** — **any** unanimity evaluation disagreed for this system. That means any
   of: the connectivity predicate across {4.0, 4.5, 5.0 Å}; or the presence gate across its full
   **3 × 3 grid** of contact distance {4.0, 4.5, 5.0 Å} × k {1, 2, 3} (§3). This is deliberately
   **one verdict covering every unanimity disagreement whatever its source** — rev 11 called some of
   these "integrity-sensitive" in §3 while §5 recognised only a k-based "geometry-sensitive", so a
   disagreement arising from the bracketing contact distance mapped to no verdict at all
   (Round 10). There is now exactly one label and no unmapped case. Takes precedence over coverage-limited because the
   disagreement is the *cause* of the cell exclusions, and reporting the symptom above the cause
   would hide why the surface is incomplete. **Counts as not recovered.**
3. **Coverage-limited** — one or more cells failed coverage or the cleft predicate for any reason
   *other* than a unanimity disagreement, so fewer than six cells survived. **Counts as not
   recovered**, reported with the failing cells and their reasons.
4. Among systems with a **full, valid six-cell surface**, exactly one of:
   - **Recovered** — the active is strictly first in every draw in all six cells. Nothing less
     qualifies.
   - **Box-sensitive** — recovered in at least one cell and not in at least one other. **Counts as
     not recovered.**
   - **Not recovered** — not strictly first in any cell.

Rules 1–3 are mutually exclusive by construction of the tree, and rule 4's three branches partition
the remaining case, so the five outcomes are **exhaustive and mutually exclusive**. The diagnostics
that did not determine the verdict are still published in full — a system reported
`geometry-sensitive` also reports its per-cell survival and its per-cell ranks. Precedence governs
only which single label the outcome matrix receives.

The full six-cell surface is reported for every system in every case, including when all cells agree.
**Selecting a cell, averaging across cells, or reporting a best cell is prohibited.** Order of
precedence is fixed: a system is box-sensitive if the cells disagree, regardless of how many fall
each way — a 5-of-6 majority does not become "recovered".

**Box-sensitivity is a headline result, not a caveat.** A benchmark asking what this pipeline can
resolve should report that a control's recovery flips on a 4 Å change in search radius, and that
finding is worth more than any single cell's verdict would have been. It is reported in the abstract
where it occurs, not buried in supplementary material.

**Secondary, reported always, never substituted:** ligand-efficiency rank, and pose RMSD to the
crystallographic pose (heavy-atom, symmetry-corrected). **Non-fits:** assigned worst rank, never
dropped, per `CONTEXT.md`. **Discordance rule:** if affinity rank and ligand-efficiency rank disagree,
the primary endpoint governs and the disagreement is reported as a result.

A single active against a decoy pool yields **one finite tail observation**. It is a **rank
diagnostic**. The words "enrichment", "ROC-AUC" and "EF1%" are reserved for §7 and may not be applied
to single-active panels.

**Outcome matrix — AEBSF and Q9D separated, per Round 2, since they are different targets and only
one of them is target-native. All eight post-calibration combinations are enumerated** (Round 3 #1:
rev 3 listed six, omitted two, and then asserted that no cell was left open — the assertion was the
worse half of the error):

| calibration (3PTB) | furin (9QWF) | AEBSF (5XYA) | Q9D (6UKD) | reading |
|---|---|---|---|---|
| recovered | recovered | recovered | recovered | Pipeline resolves all systems. **The central thesis is refuted**, and the benchmark paper has no result. The SpyCEP null then becomes evidence about **this 3.0 Å SpyCEP structural model under this protocol** — not about the target — because a control that recovers at 3.0 Å has not excluded resolution as the reason the probe set did not. |
| recovered | recovered | recovered | not recovered | AEBSF/Q9D split. Covalency alone does not explain Q9D; suspect the C47/papain family difference or the 6UKD preparation. Report both, claim neither as the pipeline's limit. |
| recovered | recovered | not recovered | recovered | The reverse split, and the most damaging to the target-native story: the pipeline recovers a cross-target covalent active but not our own. Report prominently. **Two candidate explanations are confounded and neither may be asserted over the other**: the SpyCEP-specific preparation, and the 1.4 Å resolution gap between 5XYA (3.0 Å) and 6UKD (1.59 Å). |
| recovered | recovered | not recovered | not recovered | Reduced scope only: covalent actives are unrankable by a non-covalent function. Known behaviour — **not publishable as a benchmark finding**. Note the two covalent actives differ in resolution (5XYA 3.0 Å, 6UKD 1.59 Å), so covalency is not the only property they fail to share. |
| recovered | **not recovered** | recovered | recovered | Both covalent actives recover while the non-covalent held-out fails. Covalency is *anti*-predictive here, so the confound the whole battery was built around is not operating as assumed. **The benchmark's framing does not survive this cell**; report as a furin-specific negative and reopen the design before making any pipeline-level claim. |
| recovered | not recovered | recovered | not recovered | Anomalous: the target-native covalent active is recovered while the non-covalent held-out is not. Covalency is not the discriminator; report as a furin-specific negative and claim nothing general. |
| recovered | not recovered | not recovered | recovered | Mixed and uninterpretable as a family claim: the held-out and the target-native both fail while the cross-target covalent recovers. Report all three; the 5XYA and 9QWF preparations are joint suspects, and for 5XYA its resolution is an equally live one. No pipeline-level conclusion. |
| recovered | **not recovered** | not recovered | not recovered | The strongest branch available: a non-covalent active fails under cognate conditions on a held-out S8 target. Reported as **"held-out 9QWF failure under this protocol"**, not as a general S8 or Vina-class claim — furin's polybasic ligand and electronegative pocket are an independent confound (§Risks), so one held-out failure cannot carry a family-level conclusion. |
| not recovered | any | any | any | Calibration failed. Diagnose, version the protocol (§4), re-run everything. **No claim of any kind is reported from a protocol whose calibration failed.** |

The eight rows above the calibration-failure row are exhaustive over the three binary outcomes, so no
post-calibration combination is unlisted. "Not recovered" includes the **unstable**,
**box-sensitive**, **coverage-limited** and **geometry-sensitive** cases defined above.

**Cell-level failure and system-level void are different things, and rev 9 conflated them**
(Round 8 #3). A system that loses *some* cells still has an outcome — `coverage-limited` or
`geometry-sensitive`, both of which are "not recovered" and belong in **this** matrix. Only a system
with **no surviving cell**, or one failing the integrity gate outright, has **no outcome at all**;
those are voided and handled by the table below, never by this one.

**The resolution constraint binds every row above, and overrides any row's wording where they
conflict** (Round 12 #1 — rev 13 stated the constraint in the scope paragraph and then let matrix
rows outrun it, which is this document's recurring failure mode). Concretely:

- **No branch involving a 5XYA or 7EDD outcome may attribute that outcome to the pipeline, the
  target, the scoring function or the preparation without naming the low-resolution receptor as an
  untested alternative explanation of equal standing.**
- **The word "target" is not available for SpyCEP conclusions.** Every such claim is phrased as being
  about *this 3.0 Å SpyCEP structural model under this protocol*, never about SpyCEP the protein.
- This applies to the abstract and the conclusions, not only the results section.

**Coverage failure is per-system, with per-system consequences** (Round 2 #19):

| system whose coverage fails | consequence |
|---|---|
| 3PTB (calibration) | The protocol has no calibration. **Paper 1 reports no scoring claims at all** until the box rule is versioned and everything re-run. |
| 9QWF (held out) | The held-out validation is void. The strongest matrix branch becomes unavailable; Paper 1 may still report calibration and the covalent controls, explicitly without held-out support. |
| 5XYA (AEBSF) | The target-native control is void. Paper 2 loses its shared-evidence reference and must state that the target-native control could not be evaluated. |
| 6UKD (Q9D) | The cross-target control is void. Reported as such; the rest of the battery stands. |

In every case the affected system is excluded from **scoring** claims but its box-rule failure is
itself reported — a box rule that cannot contain a known crystallographic ligand is a finding.

### 6. Run structure — `controls_v1` is a control run, and v2 is untouched

v3 as originally written was not a `Campaign` under `CONTEXT.md` (which requires WIDE, TIGHT, SpeB,
BORON) and the sealer enforces exactly those four stage manifests — `require_campaign_seal()` asserts
`stage_workflows == ["boron", "speb", "tight", "wide"]` at `src/spycep_drug_discovery/docking.py:2641`.

**Terminology — the split is already a glossary decision, and this plan no longer pretends otherwise**
(Round 3 #9). Rev 3 said ADR-0005 would decide "whether project terminology changes at all" while the
same revision had already added `Control run` to `CONTEXT.md` asserting that a control run is not a
campaign. The glossary had made the decision the plan called pending. Resolved in favour of the
glossary, because the distinction is genuinely about language and is the conservative option: it
leaves `Campaign` meaning exactly what it has always meant, so no existing seal changes meaning.

- **Settled, in `CONTEXT.md`:** a control run is a distinct concept from a campaign, and
  `controls_v1` is called a control run throughout.
- **Left to ADR-0005:** the engineering consequences only — the stage roster (CALIBRATION, FURIN,
  SPYCEP_NATIVE, SPEB_NATIVE), the schema version, the sealer path, the validators, and the consumer
  migration below. Those are implementation decisions and are deliberately kept out of the glossary.

- **`controls_v1`** — its own schema version and stage roster (CALIBRATION, FURIN, SPYCEP_NATIVE,
  SPEB_NATIVE), its own sealer path, its own validators.
- **The sealed `v2_20260719` campaign is not modified, re-docked, appended to, or overwritten.**
- Results from the two are **never pooled** and never selected between on the basis of which is more
  favourable. The mixed-campaign validator must be extended to permit *declared, non-pooled*
  cross-run reporting; that is a real code change to sealed-data machinery and needs its own review.

**Consumer migration list (Round 2 #13) — every one of these hard-codes the four-manifest roster or
its fixed paths, and each needs an explicit version-dispatch rule so v2 analysis stays readable
byte-for-byte while `controls_v1` uses its own schema:**

- `src/spycep_drug_discovery/analysis_population.py` — loads `docking_result.json`,
  `docking_result_tight.json`, `speb_positive_control_result.json`, `boron_surrogate_result.json` at
  fixed method paths (lines 61–64) and pins their source hashes (lines 81–83).
- `src/spycep_drug_discovery/docking.py` — `require_campaign_seal()`, the stage-workflow assertion.
- `compute_statistics.py`, `make_figures.py`, `write_docking_methods.py` — all consume the shared
  population module and write to fixed method paths.
- The golden and corruption tests covering the above.

Dispatch is on an explicit schema version recorded in each run's artifacts. A consumer that
encounters an unknown version **fails closed**; it never falls back to the v2 roster.

**Seal scope, stated honestly rather than promised retroactively (Round 2 #14).** The existing
`SEALED.json` binds `campaign_id`, schema versions, the spawn-retry ledger hash and the stage
workflow set — and **nothing scientific**. So "every number traced to a sealed manifest" is not true
of v2 today and cannot be made true without mutating an immutable artifact, which is forbidden.
Therefore:

- **v2's evidentiary support is stated as what it actually is:** separate analysis source hashes
  recorded in `docs/methods/docking_statistics.json`, not a science-binding seal. Both papers say so.
- **`controls_v1`'s seal binds the science from the start:** content hashes for every stage manifest,
  receptor, box definition (the R/M grid, both unanimity sets, both geometric predicates), ligand
  catalog, analysis
  artifact and tool fingerprint.
- No retroactive re-seal of v2. If a notarisation of v2 is wanted, it is a **new, non-mutating**
  artifact alongside it, and is a separate decision.

### 7. Decoys

- **Generated, for all four control systems**, by the published DUD-E property-matching recipe:
  matched on MW, logP, HBD, HBA, rotatable bonds and **net formal charge after final protonation**,
  topologically dissimilar above a declared cutoff.
- **The generator is an executable, pinned specification, not a citation** (Round 2 #15). ADR-0005
  records, before any docking: the candidate database and exact snapshot (ZINC22 2D tranches, tranche
  list, download date, per-file SHA-256), the property-computation implementation and version (RDKit,
  pinned), the exact matching tolerances per property, the topological-dissimilarity fingerprint and
  cutoff, the deduplication rule, the random seed, and the archived candidate input files. **If the
  snapshot cannot be pinned and archived, the control battery aborts** rather than proceeding on an
  unreproducible pool.
- **Exclusions, frozen as substructure queries rather than prose** (Round 4 #3 — "the corresponding
  Q9D class" was tunable and rank-affecting, since a looser class label removes more near-actives from
  the decoy pool and flatters the active's rank). Excluded are known actives of the target, and
  reactive analogues of the active's warhead or ligand class. Before any decoy generation, ADR-0005
  records, per active: the **exact SMARTS** defining the excluded warhead/class, a human-readable
  class label, the literature rationale for that class boundary, and — after generation — the **count
  of candidates each SMARTS removed**. Sulfonyl fluorides for AEBSF; the Q9D warhead class is named
  explicitly by SMARTS rather than by reference to Q9D. The SMARTS set is hashed with the generator
  parameters and may not change once decoys exist. (Rev 2 said "reactive analogues of the target",
  which was domain-wrong: the target is the protein.)
- **Pool size is an exact frozen number, not "~50"**, with an abort rule if the minimum yield cannot
  be met.
- **Multiple independent draws, not one** (Round 2 #17). A single pool of ~50 can make a rank
  diagnostic look stable or unstable by chance. A declared number of independent decoy draws (seeds
  fixed and recorded) is generated per active, the primary endpoint is computed against each, and the
  **distribution of ranks across draws is reported** — not a single draw, and not the best one. The
  pool-size sensitivity analysis used for the v2 SpeB result carries forward to the new controls.
- **Property matching is re-verified after preparation**, not before: re-protonation can destroy the
  net-charge match on which selection depended.
- **Preparation failures follow a deterministic, pre-endpoint replacement rule** (Round 2 #18): the
  frozen candidate pool is ordered by seed at generation time, and a decoy that fails preparation is
  replaced by the next candidate in that fixed order — never by a re-search, and never after any
  endpoint has been computed. If replacements exceed a declared fraction of the pool, that draw
  aborts. Silent decoy attrition selectively improves an active's rank and is a live bias.
- **What an aborted draw does, preregistered** (Round 4 #4 — rev 4 defined the abort but not its
  consequence, leaving the most convenient reading available at analysis time):
  1. An aborted draw is **replaced from a frozen seed queue**, declared at generation time with a
     fixed number of spare seeds. Replacement happens **pre-endpoint only**; a draw can never be
     abandoned after its endpoint is known.
  2. If the spare seed queue is exhausted, or if **more than a declared number of draws abort for one
     system**, that **system is voided** — reported as a preparation failure and excluded from
     scoring claims, exactly as a coverage failure is (§5), and entered in the per-system coverage
     table's terms.
  3. A voided system does **not** void the control run. The other systems stand, and the voiding is
     reported.
  4. Aborted draws, their seeds and their abort reasons are all reported. They are never silently
     replaced.
- **Entity/state catalog** built for every active and decoy. ADR-0004's rule does not "carry over
  unchanged" — its implementation derives ambiguous membership from the attempt manifest and
  cross-checks the species catalog, and new molecules have no adjudication. Class-specific exclusions
  and full denominator flow are reported.

**DUD-E TRY1 is deferred to a second stage.** Corrected counts: TRY1 is **449 actives and roughly
26,000 decoys** (the earlier "924 actives / 449 decoys" was a misreading of raw-substance versus
clustered-active columns), which is ~100× the original compute estimate. Stage 1 runs 3PTB/BEN
cognate rank recovery only. Stage 2, separately frozen, runs the full **2AYW** TRY1 enrichment
benchmark with real ROC-AUC and EF1%. These are different receptors, different questions and
different denominators, and are never merged.

The provenance comparison (generated vs DUD-E decoys) belongs to stage 2 and must hold receptor,
active population and pool size constant. It cannot estimate provenance effects on furin, SpyCEP or
SpeB, and will not be claimed to.

### 8. Determinism

Byte-identical repetition is impossible: attempts carry UUIDs, elapsed times, paths and a distinct
run id. Replaced by: two separately sealed runs compared on **normalised scientific payload**, with
declared operational metadata excluded from the comparison.

**The payload is defined as every endpoint-relevant input and every terminal scientific disposition**
(Round 3 #12 — rev 3 listed only poses, scores, ranks and derived statistics, which would let a run
differ in whether a box passed coverage, or in which decoys it actually used, and still compare as
identical):

- pose coordinates, scores, ranks and derived statistics;
- **box definitions and box status** per system **and per grid cell** — the grid specification, the
  **actual box dimensions and anisotropy** in each cell, the per-value outcomes of both unanimity
  sets, the surviving-cell count and per-cell exclusion reasons, the coverage
  outcome, and any "no defensible cleft" determination;
- **integrity-gate outcomes** — presence and identity gate results per receptor;
- **decoy pool identity** — pool ids and content hashes for every draw, plus the seed and the
  replacement log;
- **non-fit dispositions** — which claims yielded no valid pose, and under which rule they were
  assigned worst rank;
- **terminal claim records**, expressed **without** attempt UUIDs or filesystem paths (Round 4 #5 —
  rev 4's "identity of the attempt finally accepted" reintroduced exactly the operational identifiers
  this section excludes, making the payload self-contradictory). What is compared is: the normalised
  terminal claim **content**, its scientific-output hash, the **retry count**, and the **disposition
  classes** of the superseded attempts (timeout, transient spawn failure, non-fit) in order. That
  distinguishes a run which reached the same number by a different retry path, without smuggling a
  UUID or a path into the scientific payload.
- the **bracketing residue set** and the integrity-gate outcomes per receptor (§3).

Anything not on this list is operational metadata and is excluded by declaration, not by omission.
In particular attempt UUIDs, elapsed times, filesystem paths and the run id are excluded everywhere,
including inside the terminal claim records above.

### 9. The two papers

Kept as two, with both duplication defects fixed.

- **Paper 1 (benchmark):** owns the control run and every control result, including AEBSF.
- **Paper 2 (SpyCEP application):** owns the probe-set result. It **references** the AEBSF result as
  **shared evidence**, explicitly labelled as such, and never as independent replication.

**AEBSF is a new `controls_v1` Claim, and rev 2 was wrong about this** (Round 2 #1 — the most
consequential finding of the round). CONTEXT.md defines a `Claim` as species key **+ receptor + box**.
The sealed v2 AEBSF result was produced under the v2 wide and tight boxes; the control run uses the
new §3 uniform cleft box. Those are **different claims**, so the v2 number cannot be reported as the
control-battery result and the two are never compared as though one replicated the other.

This retires an Act-1 conclusion. Act 1 recorded that "the target-native control needed no new
docking — it was latent in the sealed campaign," and that is **no longer true** once the uniform box
rule is adopted: AEBSF/5XYA must be docked fresh under `controls_v1`. The v2 cognate observation
(AEBSF 6th of 8 under the v2 boxes) survives only as a v2-box result, reported with its box named.

The **single-execution rule still holds within the control run**: AEBSF/5XYA under the §3 box is
executed exactly once and referenced by both papers, so it is not double-counted.

**Each paper carries a standalone conclusion** (Round 2 #20, actionable half). Paper 1's conclusion
must hold as a statement about the pipeline without requiring Paper 2's probe-set result; Paper 2's
must hold as a statement about the SpyCEP probe set without requiring Paper 1's benchmark. Shared
evidence may be cited across them, but neither paper's conclusion may *depend* on the other's.
Co-posting is not a substitute for this and does not remove mutual dependence.

Population language corrected throughout: **77 curated entities, 73 directly attempted, 4 boron
surrogates, 72 valid-fit, 69 analysis-eligible, 68 numeric.** "77-compound null" is wrong and is
replaced by "probe-set result" with explicit populations.

**Source audit, split by the §3 ordering constraint.** A structure-by-structure audit covers ligand
identity, formula, mass, mutations, cofactors and primary citation for all six entries before
ADR-0005 is accepted. Its **ligand-geometry component runs only after the box specification is
hashed** (freeze gate 2), so that
coverage information cannot inform the constants. Manuscript citation corrected: **6UKD/Q9D is Woehl
et al. 2020, *ACS Chem Biol* 15:2060–2069, PMID 32662975** — verified against RCSB. The current
reference [2] (Wang et al. 2015, PMID 26132413) is wrong.

## Freeze conditions

This plan is **not frozen**. It becomes a preregistration only when every one of the following holds.
Each is a gate, not an aspiration:

1. ~~The external structural heuristic is pinned.~~ **CLOSED 2026-08-02 by removal, not by
   satisfaction.** No qualifying source exists to be found — the docking field sets boxes from
   ligands (§3 Gate 1, `GATE1-FINDINGS-box-constants.md`). Rev 8 removes the quantities that needed
   sourcing rather than weakening the requirement or inventing a citation.
2. **The box specification is declared and hashed before any docking** — the R/M grid
   ({8, 10, 12} × {2, 4} Å); the two **unanimity sets** (connectivity at 4.0/4.5/5.0 Å, presence gate
   at k = 1/2/3), which have **no primary value** and require agreement across the set; and the two
   geometric predicates (selection contains the catalytic residues' heavy atoms; all catalytic atoms
   present and resolved). **The {4.0, 4.5, 5.0 Å} set governs both the connectivity predicate and the
   spatial clause of the bracketing rule**, under unanimity in both places; there is no separate,
   ungated contact distance anywhere in the plan. **The gate binds the endpoint consequence, not just
   the input:** any unanimity disagreement, from either set in either role, maps to the single
   **geometry-sensitive** verdict of §5, which counts as not recovered. No disagreement may be
   interpreted separately or reported as anything else. The minimum-surviving-cell threshold is **deleted** — it was an unsourced
   constant and a favourable-remnant path (Round 7 #3); all six cells must survive for a clean
   `recovered` call. **No free numeric constant remains**, so there is nothing left to attribute to a
   source.
3. **The decoy generator AND every endpoint-affecting decoy threshold are pinned and archived,
   before generation, hashed together with the generator specification.** Round 5 was right that
   rev 5's gate covered generator *inputs* while §7 left a second group of quantities merely
   "declared" — and those are the ones that move the recovery endpoint, since draw count, pool size
   and abort thresholds jointly determine whether a system reads as recovered, unstable,
   box-sensitive or void.
   Choosing them late is a tuning channel that survived every earlier round. The gate requires:
   - **Generator:** ZINC22 snapshot with tranche list, download date and per-file SHA-256; RDKit
     version; exact matching tolerances per property; fingerprint and topological cutoff; dedup rule;
     and the archived candidate input files (§7).
   - **Thresholds:** the **exact pool size per active**; the **number of primary draws**; the
     **complete primary and spare seed queues**, enumerated rather than described; the
     **replacement-abort fraction**; the **maximum aborted draws per system**; and the
     **pool-size sensitivity parameters** (the heavy-atom windows).

   None of these may be chosen, widened or extended after any decoy exists.
4. **The warhead-exclusion SMARTS are frozen** per active, with class labels and rationale (§7).
5. **ADR-0005 is accepted**, carrying the stage roster, schema version, sealer, validators and the
   consumer migration (§6).
6. **The structure-by-structure source audit is complete**, with its ligand-geometry component run
   only after gate 2 (§9).
7. ~~The two-paper question is decided by the author.~~ **CLOSED 2026-08-02** — two papers,
   held by the author after three raisings; the standalone-conclusion requirement is the binding
   mitigation (§Resolved: the two-paper split).
8. **Review provenance shows an APPROVED verdict over the final body hash.**

Only then is it timestamped as frozen. The front matter is the authority on that status, not this
prose.

## Resolved: the two-paper split (author decision, 2026-08-02)

The reviewer recommended collapsing to a single integrated preprint in Rounds 1, 2 and 3, on the
grounds that Paper 1's motivation is the SpyCEP application while Paper 2 depends on Paper 1's AEBSF
control, so co-posting does not remove the mutual dependence. Each time the recommendation was
**escalated to the author rather than actioned by Claude or overridden silently**.

**Decision: two papers, held.** Josh reaffirmed the split on 2026-08-02, after the argument had been
put three times and sharpened each time. Freeze gate 7 is closed.

**The mitigation is therefore load-bearing and is not optional.** Each paper must carry a standalone
conclusion that holds without the other: Paper 1's as a statement about the pipeline that does not
require the probe-set result, Paper 2's as a statement about the SpyCEP probe set that does not
require the benchmark. Shared evidence — the AEBSF control above all — is citable across them but may
never be load-bearing for both conclusions, and is always labelled as shared rather than replicated.
If either paper's conclusion cannot be written to stand alone, that is evidence the reviewer was
right and the split should be revisited before submission, not after.

## Risks / open questions

- **Resolution is confounded with target and cannot be controlled for within this battery.** No
  higher-resolution SpyCEP structure exists to substitute, so the confound is **disclosed and
  indirectly probed, but not bounded** (Round 12 #2 — rev 13 said "bounded", which overclaimed).
  Neither available probe is a fix, and both are weaker than they first appear:
  - The six-cell R/M grid varies box geometry **around the same deposited coordinates**. It does not
    perturb coordinate uncertainty, which is what low resolution actually delivers, so it cannot
    bound the effect of resolution — only show whether the result is fragile to the box.
  - The 3PTB-versus-2AYW contrast (1.7 Å versus 0.97 Å) is **trypsin**, and differs from the
    confounded pair in protein, ligand set and benchmark task. **It may not be used to constrain any
    SpyCEP-specific resolution explanation**, and no sentence may imply it does.

  Both are reported for what they are. Neither licenses any claim that resolution has been excluded,
  bounded, or shown not to matter.
- Furin's electronegative pocket and polybasic ligand are a known Vina weak spot; a furin failure is
  differently confounded from covalency, not unconfounded. This is why the strongest matrix branch is
  worded as a held-out-system failure rather than a family-level claim.
- Extending the mixed-campaign validator is a real code change to sealed-data machinery and needs its
  own review.
- The grid removes the "which R?" tuning channel but does not make the plan choice-free: the grid's
  *membership* ({8, 10, 12} × {2, 4} Å, and the two unanimity sets) is still a declared choice. It is
  a much weaker one — it is fixed pre-docking, the whole surface is published, and unanimity
  transparently selects the strictest member of each set — but it is not nothing, and the paper says
  so rather than claiming the box rule is assumption-free.
- Whether R and M could have been chosen without tuning against a known answer was the sharpest threat
  to the box rule's ligand-freedom; the hash-before-coverage ordering in §3 is the mitigation, and it
  depends on the external heuristic being genuinely external.
- Cognate re-docking across the whole battery means every result is a best-case measurement; nothing
  here speaks to prospective cross-docking performance.
- The Class II cap of two protocol versions is a judgement call. Too low and a genuinely fixable
  pipeline is abandoned; too high and it is a tuning loop with extra steps.

## Out of scope

- Scaling the compound library. Settled and closed.
- Any modification, re-docking or extension of sealed campaign `v2_20260719`.
- Covalent docking. Covalency is a measured confound, not something to fix.
- Wet-lab validation, therapeutic claims, or any assertion of inhibition.
- Any general claim about Vina-class docking beyond these six named systems.

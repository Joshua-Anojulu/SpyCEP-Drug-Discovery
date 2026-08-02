# Gate 1 findings — sourcing the seven box constants

_Literature search 2026-08-02, Claude, read-only. Against freeze gate 1 of `PLAN-control-battery.md`
(rev 7, `approved-final`). **No plan text was changed** — gate 1 cannot be closed without an author
decision, and any body edit would break the `approved-final` hash binding._

## What gate 1 asks for

A published, citable source for the seven box constants (R, M, minimum selected-atom count, maximum
box edge, contact distance, catalytic-atom completeness, sequence window k) that is:

- published and citable, with version/edition and content hash;
- **independent of all six battery receptors** (3PTB, 9QWF, 5XYA, 7EDD, 6UKD, 2AYW);
- **ligand-free** — deriving nothing from co-crystallised ligand geometry;
- covering all seven constants, or combined with a second source with per-constant attribution.

## Result: not found, and there is a structural reason

**No source was found that supplies receptor-only values for any of the seven constants.** This is a
negative result from eight searches across the obvious angles, not a proof of non-existence — a
deeper search or a crystallographer may know of one. But the searches failed in a consistent and
informative way, and that pattern is the actual finding.

**The docking-box literature is ligand-anchored almost without exception.** The two canonical sources
both set the box from the ligand:

| source | how the box is set | why it fails gate 1 |
|---|---|---|
| **DUD-E** (Mysinger, Carchia, Irwin & Shoichet 2012, *J Med Chem* 55:6582–6594) | min/max of the **ligand** coordinates per dimension, padded 12.5 Å each side, floor of 30 Å per edge | Ligand-derived. This is precisely the circularity §3 bans — and it is the benchmark this project's §7 stage 2 otherwise relies on. |
| **Feinstein & Brylinski 2015**, *J Cheminform* 7:18 (PMID 26082804) | box edge = **2.9 × radius of gyration of the docking compound** | Ligand-derived, and compound-specific: it cannot yield a single global R/M held constant across six receptors. |

So the field's default is exactly what this plan forbids. That is worth stating in the paper on its
own merits — it is a real observation about docking practice, and it explains why an active-blind box
rule has no off-the-shelf constants to borrow.

**The centring rule is citable; the sizing constants are not.** Centring a box on the centroid of
named catalytic residues is established practice for apo work (the SARS-CoV-2 Mpro His41/Cys145 box
is the commonly cited worked example). But every source located then sizes that box "according to the
expected ligand size, typically 20–30 Å" — reaching for the ligand again at the one step where gate 1
needs it not to. **R and M specifically have no receptor-only published value.**

**The four cleft thresholds and k have no source in this literature at all.** Minimum selected-atom
count, maximum box edge, contact distance and sequence window k are constructs of this plan's own
predicate (§3). Contact-distance conventions exist but are study-specific and inconsistent — 4.0 Å,
4.5 Å and 5.0 Å are all in current use for "residue in contact", with no canonical choice.

## Candidate routes, and what each costs

**(a) Pocket detection as the external source** — fpocket (Le Guilloux, Schmidtke & Tuffery 2009,
*BMC Bioinformatics* 10:168) and CASTp are genuinely receptor-only and detect apo pockets at ~87–95%
success. **Blocked by Act 1 decision 5**, which chose a triad-centred rule with a fixed size
specifically to avoid a pocket-detection dependency, on the grounds that it must remain statable for
SpyCEP's shallow groove. Reopening that is an Act 1 decision, not a gate-1 fix.

**(b) Measure the constants on a receptor-only calibration set** — take S1/S8/C47 protease structures
excluding all six battery receptors, measure active-site pocket dimensions from receptor geometry
alone, and fix R and M from that distribution. Defensible and genuinely ligand-free. Costs: it is new
work, it needs its own preregistration, and it imports whatever bias the calibration set carries.

**(c) Report across a preregistered grid of R and M instead of picking one — recommended.** Declare a
grid (say R ∈ {8, 10, 12} Å × M ∈ {2, 4} Å), run every control at every combination, and report the
full surface. This dissolves the sourcing problem rather than solving it:

- Nothing needs justifying, because nothing is chosen. There is no R to defend.
- **Tuning becomes structurally impossible** — the whole grid is reported, so no favourable cell can
  be selected after the fact. That is a stronger guarantee than "we picked R from a citation."
- It converts the weakness into a result: whether the conclusions are box-sensitive is *exactly* what
  a benchmark paper about pipeline resolution should be measuring. A control that recovers at R=8 and
  fails at R=12 is a finding, not a nuisance.
- Cost is compute, which this project has already established is cheap (~23–27 s per Vina call at
  `--cpu 1`), and a §5 aggregation rule for reading recovery across the grid — the same problem §7's
  multiple decoy draws already solved, so the machinery exists.

**(d) Weaken gate 1** to accept a declared-and-hashed choice without an external source. Honest only
if the plan then stops claiming the constants are externally grounded. Weakest option; not
recommended.

## Consequence for the plan

**The plan cannot be frozen as written**, because gate 1 has no satisfiable route that does not change
the plan body. Whichever of (b), (c) or (d) is chosen, §3 and the freeze gates need amending — which
means the `approved-final` binding to hash `8c63e1e7…` will not survive, and one further review round
is required.

That is a normal outcome, not a failure of the review: the gates exist to surface exactly this before
freeze rather than after docking. Rev 7's approval remains valid for what it covers — it says the plan
is sound as a preregistration *given* that gate 1 can be closed. This note is the evidence that it
cannot be, in the form gate 1 currently specifies.

## Sources

- Mysinger MM, Carchia M, Irwin JJ, Shoichet BK. Directory of Useful Decoys, Enhanced (DUD-E).
  *J Med Chem* 2012;55(14):6582–6594. PMID 22716043. https://pubs.acs.org/doi/10.1021/jm300687e
- Feinstein WP, Brylinski M. Calculating an optimal box size for ligand docking and virtual screening.
  *J Cheminform* 2015;7:18. PMID 26082804. https://link.springer.com/article/10.1186/s13321-015-0067-5
- Le Guilloux V, Schmidtke P, Tuffery P. Fpocket: an open source platform for ligand pocket detection.
  *BMC Bioinformatics* 2009;10:168. https://bmcbioinformatics.biomedcentral.com/articles/10.1186/1471-2105-10-168
- Liang J, Edelsbrunner H, Woodward C. Anatomy of protein pockets and cavities. *Protein Sci*
  1998;7(9):1884–1897. PMID 9761470. https://onlinelibrary.wiley.com/doi/10.1002/pro.5560070905
- Ribeiro AJM et al. Mechanism and Catalytic Site Atlas (M-CSA). *Nucleic Acids Res* 2018;46(D1):D618–D623.
  https://academic.oup.com/nar/article/46/D1/D618/4584620

**Every citation above was returned by search and its identifiers read off the result; none is
recalled from memory.** Before any is written into ADR-0005 it must still be opened and verified
directly, per `CLAUDE.md` rule 6 — a search result is not a read paper.

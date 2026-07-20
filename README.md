# SpyCEP Drug Discovery

A reproducible in-silico screen for small-molecule inhibitors of SpyCEP/ScpC, the IL-8–degrading serine protease of necrotizing-fasciitis–causing *Streptococcus pyogenes*.

**Headline result: a cautionary benchmark. The screen found nothing, and the positive control failed.**

Ensemble docking of a 77-compound library (22 rational protease and anti-virulence chemotypes, 55 FDA comparators, all PubChem-sourced) against two SpyCEP structures (PDB 5XYA, 7EDD) surfaced **no compelling candidate**. Affinities span −4.4 to −8.3 kcal/mol, and the custom chemotypes do not separate from generic drugs under either search box (bootstrap 95% CI on the mean difference spans zero; Mann-Whitney p = 0.31 and p = 0.26). Correcting the ligand ionisation states to pH 7.4 did not change this: benzamidine carries its +1 amidinium charge and still ranks 63rd of 68 by affinity.

We cannot attribute that null to the target, because **the pipeline fails its own positive control**. Applied to SpeB, a related protease with a co-crystallised inhibitor (PDB 6UKD, ligand Q9D), with the search box built from the catalytic dyad alone and decoys size-matched to the inhibitor, the known binder ranks **2nd of 15 by affinity and 4th of 15 by ligand efficiency** against the 14 single-state decoys, losing to dexamethasone on both; returning the three dual-state β-lactams puts it 4th of 18 and 7th of 18. A method that cannot separate a known inhibitor from a corticosteroid has not earned the right to call SpyCEP undruggable.

An earlier version of this study reported that the control passed by 4.4 SD. That came from a search box computed from Q9D's own crystallographic coordinates and from decoys half its size. Removing both flaws removes the effect. See [`docs/manuscript/spycep_insilico_screen.md`](docs/manuscript/spycep_insilico_screen.md) and the figures in `docs/manuscript/figures/`.

## What's here

> **STATUS — remediation complete. Numbers come from the sealed campaign `v2_20260719`.**
> An adversarial code review ([`docs/CODEX-CODE-REVIEW-2026-07-13.md`](docs/CODEX-CODE-REVIEW-2026-07-13.md)) found defects in the
> supporting layer of this study — an inflated triad statistic, mis-speciated ligands, and a broken provenance chain. The remediation
> plan ([`PLAN.md`](PLAN.md)) was hardened over nine rounds of cross-model review, the pipeline was rebuilt, and the campaign was
> re-run and sealed on 2026-07-19. A subsequent correction ([`PLAN-species-exclusion.md`](PLAN-species-exclusion.md), Codex-approved
> over six rounds) replaced row-level counting with entity-level populations in every set-level statistic.
>
> The prediction made before the re-run — that the headline null and the failed positive control would survive — **held**. No
> disposition changed. The numbers moved: catalytic-triad contact is no longer universal (62 of 69 in the wide box, not 73 of 73),
> and Q9D's rank sharpened from 6th of 20 to 2nd of 15. The conclusions did not.

- **Reproducible pipeline** (fixed seed; `--cpu 1`, because multi-CPU Vina is non-deterministic even under a fixed seed; content-addressed QC and MMFF gates; per-attempt provenance sidecars recording the exact Vina command, timing and output hash; RDKit and Meeko pinned exactly): target feasibility → pocket definition → receptor prep → PDBQT conversion and QC → compound curation and ADMET → species audit → ligand prep (desalt → assign species at pH 7.4 → embed) → AutoDock Vina docking → ligand-efficiency ranking → catalytic-triad interaction analysis → state-robust statistics → figures.
- **Structures and compounds are sourced, not hand-entered** (PubChem, RCSB). The one deliberate exception is the pair of alternative protonation states for each `AMBIGUOUS` compound: those are hand-written, literature-cited, and reviewed — but they are a **hypothesis, not a result**. We do not assert which state is correct; we dock both and report whether the conclusion depends on the choice.
- **270 passing tests**; deterministic manifest regeneration; statistics byte-identical on recomputation.
- **Primary target** SpyCEP/ScpC (S8 subtilisin-like, catalytic triad D151/H279/S617); **positive-control target** SpeB (Cys192/His340).

Ligands are docked at **pH 7.4** as species assigned by an explicit, auditable pKa rule set — not as the neutral PubChem depiction. The custom set is dominated by amidines and guanidines, which are cations at physiological pH, and the S1 salt bridge is their entire binding rationale.

**Where the evidence cannot pick a state, we do not pick one.** Each compound is classified `UNAMBIGUOUS`, `AMBIGUOUS`, or `NO_IONISABLE_SITE` in [`docs/methods/species_audit.json`](docs/methods/species_audit.json). Four compounds — **ampicillin, amoxicillin, cephalexin and lisinopril** — carry an ionisable site whose pKa sits too close to 7.4 for the dominant species to be established, so **both plausible states are docked**. No abundance fraction is claimed for any of them: macroscopic pKa values cannot identify *which site* carries the proton, and inventing a fraction would manufacture precision the evidence does not support.

Because each of those four contributes two docking results, counting them in a set-level statistic would count them twice and inflate n. They are therefore **excluded from the primary set-level statistics**, which run one observation per entity, and a sensitivity analysis enumerating all 16 one-state-per-entity assignments over the full 54-comparator population is reported alongside. No assignment produces a significant separation (affinity p ranges 0.224–0.255 wide, 0.178–0.196 tight), which is what licenses the robustness claim.

The rule set is checked against **24 reference compounds** in [`docs/methods/protonation_reference_cases.json`](docs/methods/protonation_reference_cases.json), each recording the pKa value, the ionisable site, the measurement conditions, a source URL, and a verbatim quote from that source. Evidence is **tiered honestly**: 16 compound-specific experimental, 3 curated experimental compilations, 3 secondary-review (chain of custody stops at a review or textbook), and **2 `NO_SOURCE_FOUND`**. A PubChem link proves *structure*, not solution ionisation, and is never counted as a pKa source.

Those two `NO_SOURCE_FOUND` compounds are worth naming, because they illustrate the failure mode this project exists to avoid. **Fosfomycin** and **pentamidine** have no experimental pKa we could verify in any fetchable source; the values that circulate for both are software *predictions* (Chemicalize, DrugBank) that have been laundered into the literature as though measured — pentamidine's "pKa 12.1" appears in a peer-reviewed paper stated as fact with no citation. We record them as unverifiable rather than repeat the prediction.

The SpeB control is reported on **both** raw affinity and ligand efficiency, against **size-matched** decoys, with the box built from the catalytic dyad and never from the co-crystallised ligand. It fails on both metrics.

See the design spec in `docs/superpowers/specs/` and the generated methods note `docs/methods/docking_analysis.md`.

## Local Setup

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest
```

Use the virtual environment Python for all project commands on Windows.

For receptor-to-PDBQT conversion, install the optional local receptor-preparation toolchain:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev,receptor-prep]"
```

## Milestone 1: Target Feasibility

The first executable milestone determines whether SpyCEP/ScpC has structures suitable for defensible docking. See `environment/setup_windows.md` for local setup and commands.

## Milestone 2: Pocket Definition And Receptor Preparation

The second milestone records approved candidate SpyCEP/ScpC receptor pockets, cleaned receptor-preparation manifests, Meeko receptor PDBQT conversion manifests, and PDBQT QC review before docking. The current candidate set uses 5XYA as the AES-anchored active-site receptor and 7EDD as the native coverage comparator.

## Milestone 3: Ligand Preparation And Docking

The third milestone is the full compound-docking study: RDKit + Meeko ligand preparation (with desalting), an AutoDock Vina docking wrapper (fixed seed), ligand-efficiency ranking that corrects Vina's molecular-size bias, catalytic-triad interaction analysis, bootstrap/Mann–Whitney statistics, and publication figures. The full 77-compound library was docked against the 5XYA + 7EDD ensemble under two box definitions, a SpeB positive control was run, and the honest-null manuscript was written. See `environment/setup_windows.md` for the AutoDock Vina download and commands, and `docs/methods/docking_analysis.md` for the generated methods note.

Regenerate statistics and figures:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev,receptor-prep,figures]"
.\.venv\Scripts\python.exe scripts\compute_statistics.py
.\.venv\Scripts\python.exe scripts\make_figures.py
```

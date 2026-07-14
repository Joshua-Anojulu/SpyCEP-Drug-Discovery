# SpyCEP Drug Discovery

A reproducible in-silico screen for small-molecule inhibitors of SpyCEP/ScpC, the IL-8–degrading serine protease of necrotizing-fasciitis–causing *Streptococcus pyogenes*.

**Headline result: a cautionary benchmark. The screen found nothing, and the positive control failed.**

Ensemble docking of a 77-compound library (22 rational protease and anti-virulence chemotypes, 55 FDA comparators, all PubChem-sourced) against two SpyCEP structures (PDB 5XYA, 7EDD) surfaced **no compelling candidate**. Affinities span −4.4 to −8.0 kcal/mol, and the custom chemotypes do not separate from generic drugs under either search box (bootstrap 95% CI on the mean difference spans zero; Mann-Whitney p = 0.32 and p = 0.26). Correcting the ligand ionisation states to pH 7.4 did not change this: benzamidine carries its +1 amidinium charge and still ranks 67th of 73 by affinity.

We cannot attribute that null to the target, because **the pipeline fails its own positive control**. Applied to SpeB, a related protease with a co-crystallised inhibitor (PDB 6UKD, ligand Q9D), with the search box built from the catalytic dyad alone and 17 decoys size-matched to the inhibitor, the known binder ranks **6th of 20 by affinity and 7th of 20 by ligand efficiency**, behind dexamethasone, ampicillin and celecoxib. A method that cannot separate a known inhibitor from a corticosteroid has not earned the right to call SpyCEP undruggable.

An earlier version of this study reported that the control passed by 4.4 SD. That came from a search box computed from Q9D's own crystallographic coordinates and from decoys half its size. Removing both flaws removes the effect. See [`docs/manuscript/spycep_insilico_screen.md`](docs/manuscript/spycep_insilico_screen.md) and the figures in `docs/manuscript/figures/`.

## What's here

- **Reproducible pipeline** (fixed seeds; tracked JSON manifests recording per-docking commands, boxes and output hashes; PubChem and RCSB sources, nothing hand-entered): target feasibility → pocket definition → receptor prep → PDBQT conversion and QC → compound curation and ADMET → ligand prep (desalt → protonate at pH 7.4 → embed) → AutoDock Vina docking → ligand-efficiency ranking → catalytic-triad interaction analysis → bootstrap statistics → figures.
- **109 passing tests**; deterministic manifest regeneration.
- **Primary target** SpyCEP/ScpC (S8 subtilisin-like, catalytic triad D151/H279/S617); **positive-control target** SpeB (Cys192/His340).

Ligands are docked as their dominant microspecies at **pH 7.4**, assigned from an explicit pKa rule set validated against literature charges for 24 reference compounds, and not as the neutral PubChem depiction. The custom set is dominated by amidines and guanidines, which are cations at physiological pH, and the S1 salt bridge is their entire binding rationale.

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

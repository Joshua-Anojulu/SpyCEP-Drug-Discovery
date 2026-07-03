# SpyCEP Drug Discovery

A reproducible in-silico screen for small-molecule inhibitors of SpyCEP/ScpC, the IL-8–degrading serine protease of necrotizing-fasciitis–causing *Streptococcus pyogenes*.

**Headline result — an honest benchmarking / negative study.** Ensemble docking of a 77-compound library (22 rational protease/anti-virulence chemotypes + 55 FDA comparators, all PubChem-sourced) against two SpyCEP structures (PDB 5XYA, 7EDD) found **no compelling small-molecule candidate**: predicted affinities span only −4.5 to −8.1 kcal/mol and the custom chemotypes do **not** significantly separate from generic drugs (bootstrap 95% CI on the mean difference includes zero under both a wide and a tight search box). A **SpeB positive control** — the same pipeline applied to a related protease with a known inhibitor (PDB 6UKD) — correctly ranks that inhibitor 4.4 SD above all decoys, showing the SpyCEP null reflects a hard target, not a broken method. See the manuscript in [`docs/manuscript/spycep_insilico_screen.md`](docs/manuscript/spycep_insilico_screen.md) and figures in `docs/manuscript/figures/`.

## What's here

- **Reproducible pipeline** (fixed seeds, tracked JSON manifests with hashes, PubChem/RCSB-sourced structures — nothing hand-entered): target feasibility → pocket definition → receptor prep → PDBQT conversion + QC → compound curation + ADMET → ligand prep → AutoDock Vina docking → ligand-efficiency ranking → catalytic-triad interaction analysis → bootstrap statistics → figures.
- **77 passing tests**; deterministic manifest regeneration.
- **Primary target** SpyCEP/ScpC (S8 subtilisin-like, catalytic triad D151/H279/S617); **positive-control target** SpeB (Cys192/His340).

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

# SpyCEP Drug Discovery

Computational anti-virulence drug discovery project targeting SpyCEP/ScpC in necrotizing fasciitis-causing *Streptococcus pyogenes*.

The project is currently in design and feasibility planning. The approved primary direction is a novelty-first, reproducible docking workflow against SpyCEP/ScpC, with SpeB as the fallback target if SpyCEP/ScpC is not structurally suitable for defensible docking.

## Current Status

- Disease focus: necrotizing fasciitis associated with group A *Streptococcus pyogenes*.
- Primary target: SpyCEP/ScpC chemokine protease.
- Fallback target: SpeB streptococcal cysteine protease.
- Library strategy: custom anti-virulence/protease-focused compound library, with FDA-approved compounds as a comparator set.
- Reproducibility goal: preprint-grade scripts, notebooks, metadata, methods notes, and generated figures/tables.

See the design spec in `docs/superpowers/specs/` before implementation work.

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

The third milestone adds a reproducible compound-docking pipeline: RDKit + Meeko ligand preparation, an AutoDock Vina docking wrapper (fixed seed), ligand-efficiency ranking that corrects Vina's molecular-size bias, and catalytic-triad interaction analysis. A throwaway validation pilot (`scripts/run_validation_pilot.py`) confirms the pipeline runs end-to-end and is reproducible before any real compound library is curated. See `environment/setup_windows.md` for the AutoDock Vina download and commands, and `docs/methods/docking_analysis.md` for the generated methods note.

Real compound-library curation and docking remain gated on explicit user approval of the library scope.

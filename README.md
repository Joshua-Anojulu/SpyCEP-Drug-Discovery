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

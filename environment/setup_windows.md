# Windows Setup

Use PowerShell from the project root:

```powershell
cd C:\Users\josha\OneDrive\Documents\SpyCEP-Drug-Discovery
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest
```

Install the optional receptor-preparation/PDBQT conversion tools when working past pocket definition:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev,receptor-prep]"
```

Fetch SpyCEP/ScpC structure metadata and PDB files:

```powershell
.\.venv\Scripts\python.exe scripts\fetch_structures.py
```

Generate the target-feasibility report:

```powershell
.\.venv\Scripts\python.exe scripts\analyze_target_feasibility.py
```

Define the approved candidate SpyCEP/ScpC active-site pockets:

```powershell
.\.venv\Scripts\python.exe scripts\define_spycep_pockets.py
.\.venv\Scripts\python.exe scripts\analyze_target_feasibility.py
```

Prepare cleaned receptor PDB files for the approved pockets:

```powershell
.\.venv\Scripts\python.exe scripts\prepare_receptors.py
```

Convert the cleaned receptors to PDBQT with Meeko:

```powershell
.\.venv\Scripts\python.exe scripts\convert_receptors_to_pdbqt.py
```

Review Meeko residue omissions before any docking run:

```powershell
.\.venv\Scripts\python.exe scripts\review_pdbqt_conversion.py
```

The default report is generated from tracked normalized RCSB metadata in `docs/methods/rcsb_metadata.json` and manual structure-review fields in `docs/methods/structure_review.json`.

The raw structure files, cleaned receptor PDBs, generated PDBQT/Meeko files, and generated CSV outputs are ignored by Git. The methods notes in `docs/methods/target_feasibility.md`, `docs/methods/pocket_definition.json`, `docs/methods/receptor_preparation.json`, `docs/methods/pdbqt_conversion.json`, and `docs/methods/pdbqt_quality_review.json` are tracked because they record the decision gate.

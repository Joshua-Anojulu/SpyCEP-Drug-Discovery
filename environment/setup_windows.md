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

## Milestone 3: Ligand Preparation And Docking

The `vina` Python binding does not build on Windows/Python 3.14 (it needs Boost), so the
pipeline calls the official AutoDock Vina Windows executable via subprocess. Download it
once into the git-ignored `tools\` directory:

```powershell
New-Item -ItemType Directory -Force tools | Out-Null
Invoke-WebRequest -Uri "https://github.com/ccsb-scripps/AutoDock-Vina/releases/download/v1.2.7/vina_1.2.7_win.exe" -OutFile tools\vina.exe
.\tools\vina.exe --version
```

Ligand preparation and interaction analysis reuse the receptor-prep extra (RDKit, Meeko,
SciPy). Install it if you have not already:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev,receptor-prep]"
```

Run the pipeline-validation pilot (throwaway set; validates that ligand prep -> Vina
docking -> ranking runs and is reproducible before real compound curation):

```powershell
.\.venv\Scripts\python.exe scripts\run_validation_pilot.py
```

Regenerate the tracked docking methods note from the pilot result:

```powershell
.\.venv\Scripts\python.exe scripts\write_docking_methods.py
```

The downloaded `tools\vina.exe`, generated ligand PDBQT files, and docking poses/logs are
Git-ignored. The tracked docking manifests are `docs/methods/validation_pilot_compounds.json`,
`docs/methods/validation_pilot_result.json`, and the generated note `docs/methods/docking_analysis.md`.

The default report is generated from tracked normalized RCSB metadata in `docs/methods/rcsb_metadata.json` and manual structure-review fields in `docs/methods/structure_review.json`.

The raw structure files, cleaned receptor PDBs, generated PDBQT/Meeko files, and generated CSV outputs are ignored by Git. The methods notes in `docs/methods/target_feasibility.md`, `docs/methods/pocket_definition.json`, `docs/methods/receptor_preparation.json`, `docs/methods/pdbqt_conversion.json`, and `docs/methods/pdbqt_quality_review.json` are tracked because they record the decision gate.

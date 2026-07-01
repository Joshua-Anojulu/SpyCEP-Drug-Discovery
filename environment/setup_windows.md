# Windows Setup

Use PowerShell from the project root:

```powershell
cd C:\Users\josha\OneDrive\Documents\SpyCEP-Drug-Discovery
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest
```

Fetch SpyCEP/ScpC structure metadata and PDB files:

```powershell
.\.venv\Scripts\python.exe scripts\fetch_structures.py
```

Generate the target-feasibility report:

```powershell
.\.venv\Scripts\python.exe scripts\analyze_target_feasibility.py
```

The raw structure files and generated CSV outputs are ignored by Git. The methods note in `docs/methods/target_feasibility.md` is tracked because it records the decision gate.

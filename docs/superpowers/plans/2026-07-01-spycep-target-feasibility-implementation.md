# SpyCEP Target Feasibility Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the reproducible Python foundation and target-feasibility workflow needed to decide whether SpyCEP/ScpC is structurally defensible for docking.

**Architecture:** The first milestone separates project configuration, curated target metadata, external database clients, feasibility scoring, command-line scripts, and generated reports. The workflow records evidence for SpyCEP/ScpC first and only prepares the SpeB fallback if SpyCEP/ScpC fails the feasibility gate.

**Tech Stack:** Python 3.11+, pytest, requests, standard-library dataclasses/json/csv/pathlib, Markdown methods notes, Git.

---

## Scope

This plan implements Milestone 1 from the approved design:

- Python project foundation.
- Tracked target registry for SpyCEP/ScpC and SpeB.
- RCSB metadata fetching with network-free tests.
- Structure file download command.
- Target-feasibility scoring and report generation.
- Windows setup documentation.
- Private context update.

Compound curation, ligand preparation, docking, interaction analysis, figures, and manuscript drafting are intentionally excluded from this milestone. Those depend on the target-feasibility decision and should each receive their own plan after the SpyCEP/ScpC gate is resolved.

## File Structure

Create these files:

- `pyproject.toml`: package metadata, runtime dependencies, pytest configuration.
- `src/spycep_drug_discovery/__init__.py`: package version.
- `src/spycep_drug_discovery/paths.py`: project-root and directory helpers.
- `src/spycep_drug_discovery/targets.py`: target registry dataclasses and validation.
- `src/spycep_drug_discovery/rcsb.py`: RCSB entry normalization and fetching.
- `src/spycep_drug_discovery/feasibility.py`: feasibility scoring and CSV/Markdown report rows.
- `scripts/fetch_structures.py`: CLI that downloads RCSB metadata and PDB files.
- `scripts/analyze_target_feasibility.py`: CLI that writes feasibility outputs.
- `docs/methods/target_registry.json`: tracked target and structure registry.
- `environment/setup_windows.md`: reproducible local setup commands.
- `tests/test_paths.py`: path helper tests.
- `tests/test_targets.py`: target registry tests.
- `tests/test_rcsb.py`: RCSB normalization tests.
- `tests/test_feasibility.py`: scoring/report-row tests.

Modify these files:

- `.gitignore`: allow tracked `.gitkeep` files and keep generated data/results ignored.
- `README.md`: add setup and first milestone commands.
- `PROJECT_CONTEXT.md`: private transfer notes for the approved plan and current execution gate.

Generated files during execution:

- `data/raw/rcsb/*.json`
- `data/structures/*.pdb`
- `results/tables/target_feasibility.csv`
- `docs/methods/target_feasibility.md`

The generated data and results stay ignored unless the user approves tracking selected small artifacts.

---

### Task 1: Python Project Foundation

**Files:**
- Create: `pyproject.toml`
- Create: `src/spycep_drug_discovery/__init__.py`
- Create: `src/spycep_drug_discovery/paths.py`
- Create: `tests/test_paths.py`
- Modify: `README.md`

- [ ] **Step 1: Write the failing path tests**

Create `tests/test_paths.py`:

```python
from pathlib import Path

from spycep_drug_discovery.paths import ensure_dir, project_root


def test_project_root_contains_readme():
    root = project_root()

    assert root.name == "SpyCEP-Drug-Discovery"
    assert (root / "README.md").is_file()


def test_ensure_dir_creates_nested_directory(tmp_path):
    target = tmp_path / "nested" / "folder"

    result = ensure_dir(target)

    assert result == target
    assert target.is_dir()
```

- [ ] **Step 2: Run the failing path tests**

Run:

```powershell
python -m pytest tests/test_paths.py -q
```

Expected: FAIL because `spycep_drug_discovery.paths` does not exist.

- [ ] **Step 3: Create package configuration**

Create `pyproject.toml`:

```toml
[project]
name = "spycep-drug-discovery"
version = "0.1.0"
description = "Reproducible computational anti-virulence target-feasibility workflow for SpyCEP/ScpC."
requires-python = ">=3.11"
dependencies = [
  "requests>=2.32.0"
]

[project.optional-dependencies]
dev = [
  "pytest>=8.0.0"
]

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
addopts = "-q"
```

Create `src/spycep_drug_discovery/__init__.py`:

```python
"""Utilities for the SpyCEP computational drug discovery project."""

__version__ = "0.1.0"
```

- [ ] **Step 4: Implement path helpers**

Create `src/spycep_drug_discovery/paths.py`:

```python
from pathlib import Path


def project_root() -> Path:
    """Return the repository root for the SpyCEP drug discovery project."""
    return Path(__file__).resolve().parents[2]


def ensure_dir(path: Path) -> Path:
    """Create a directory if needed and return the same path."""
    path.mkdir(parents=True, exist_ok=True)
    return path
```

- [ ] **Step 5: Run the path tests**

Run:

```powershell
python -m pytest tests/test_paths.py -q
```

Expected: PASS with `2 passed`.

- [ ] **Step 6: Update README with local setup commands**

Add this section to `README.md`:

````markdown
## Local Setup

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest
```

Use the virtual environment Python for all project commands on Windows.
````

- [ ] **Step 7: Commit project foundation**

Run:

```powershell
git add pyproject.toml src/spycep_drug_discovery/__init__.py src/spycep_drug_discovery/paths.py tests/test_paths.py README.md
git commit -m "Add Python project foundation"
```

Expected: commit authored as `Joshua Anojulu <joshanojulu@gmail.com>`.

---

### Task 2: Target Registry

**Files:**
- Create: `docs/methods/target_registry.json`
- Create: `src/spycep_drug_discovery/targets.py`
- Create: `tests/test_targets.py`

- [ ] **Step 1: Write target registry tests**

Create `tests/test_targets.py`:

```python
from pathlib import Path

import pytest

from spycep_drug_discovery.targets import TargetRegistryError, load_target_registry


REGISTRY_PATH = Path("docs/methods/target_registry.json")


def test_registry_contains_approved_primary_and_fallback_targets():
    registry = load_target_registry(REGISTRY_PATH)

    assert registry.primary.uniprot_accession == "Q3HV58"
    assert registry.primary.gene_name == "scpC"
    assert registry.primary.decision_role == "primary"
    assert registry.fallback.uniprot_accession == "P0C0J0"
    assert registry.fallback.gene_name == "speB"
    assert registry.fallback.decision_role == "fallback"


def test_registry_tracks_spycep_candidate_structures():
    registry = load_target_registry(REGISTRY_PATH)
    pdb_ids = {structure.pdb_id for structure in registry.primary.structures}

    assert {"5XXZ", "5XYA", "5XYR", "7EDD"}.issubset(pdb_ids)


def test_registry_rejects_missing_primary_target(tmp_path):
    broken = tmp_path / "broken_registry.json"
    broken.write_text('{"targets": []}', encoding="utf-8")

    with pytest.raises(TargetRegistryError, match="exactly one primary"):
        load_target_registry(broken)
```

- [ ] **Step 2: Run the failing registry tests**

Run:

```powershell
python -m pytest tests/test_targets.py -q
```

Expected: FAIL because `spycep_drug_discovery.targets` does not exist.

- [ ] **Step 3: Create the approved target registry**

Create `docs/methods/target_registry.json`:

```json
{
  "project": "SpyCEP-Drug-Discovery",
  "registry_version": "2026-07-01",
  "targets": [
    {
      "target_id": "spycep_scpC",
      "decision_role": "primary",
      "protein_name": "Chemokine protease C / SpyCEP / ScpC",
      "gene_name": "scpC",
      "organism": "Streptococcus pyogenes",
      "uniprot_accession": "Q3HV58",
      "rationale": "Primary novelty-first anti-virulence target linked to CXC chemokine degradation and resistance to neutrophil killing.",
      "key_references": [
        {
          "pmid": "18692776",
          "note": "SpyCEP/ScpC promotes resistance to neutrophil killing."
        }
      ],
      "structures": [
        {
          "pdb_id": "5XXZ",
          "source": "RCSB",
          "selection_note": "Candidate SpyCEP/ScpC structure from UniProt cross-reference."
        },
        {
          "pdb_id": "5XYA",
          "source": "RCSB",
          "selection_note": "Candidate SpyCEP/ScpC structure from UniProt cross-reference."
        },
        {
          "pdb_id": "5XYR",
          "source": "RCSB",
          "selection_note": "Candidate SpyCEP/ScpC structure from UniProt cross-reference."
        },
        {
          "pdb_id": "7EDD",
          "source": "RCSB",
          "selection_note": "Candidate SpyCEP/ScpC structure from UniProt cross-reference."
        }
      ]
    },
    {
      "target_id": "speb",
      "decision_role": "fallback",
      "protein_name": "Streptopain / SpeB",
      "gene_name": "speB",
      "organism": "Streptococcus pyogenes",
      "uniprot_accession": "P0C0J0",
      "rationale": "Fallback virulence target with multiple high-resolution structures and inhibitor-complex evidence.",
      "key_references": [
        {
          "pmid": "26132413",
          "note": "SpeB small-molecule inhibitor co-complex."
        },
        {
          "pmid": "10681429",
          "note": "SpeB zymogen crystal structure."
        }
      ],
      "structures": [
        {
          "pdb_id": "1DKI",
          "source": "RCSB",
          "selection_note": "High-resolution zymogen form active-site mutant."
        },
        {
          "pdb_id": "1PVJ",
          "source": "RCSB",
          "selection_note": "SpeB inhibitor-complex structure."
        },
        {
          "pdb_id": "4D8B",
          "source": "RCSB",
          "selection_note": "High-resolution monomeric SpeB structure."
        },
        {
          "pdb_id": "6UKD",
          "source": "RCSB",
          "selection_note": "SpeB co-complex with nitrile-based inhibitor."
        }
      ]
    }
  ]
}
```

- [ ] **Step 4: Implement target registry loading**

Create `src/spycep_drug_discovery/targets.py`:

```python
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class TargetRegistryError(ValueError):
    """Raised when the target registry is missing required scientific decisions."""


@dataclass(frozen=True)
class Reference:
    pmid: str
    note: str


@dataclass(frozen=True)
class StructureCandidate:
    pdb_id: str
    source: str
    selection_note: str


@dataclass(frozen=True)
class Target:
    target_id: str
    decision_role: str
    protein_name: str
    gene_name: str
    organism: str
    uniprot_accession: str
    rationale: str
    key_references: tuple[Reference, ...]
    structures: tuple[StructureCandidate, ...]


@dataclass(frozen=True)
class TargetRegistry:
    project: str
    registry_version: str
    targets: tuple[Target, ...]

    @property
    def primary(self) -> Target:
        return _single_target_by_role(self.targets, "primary")

    @property
    def fallback(self) -> Target:
        return _single_target_by_role(self.targets, "fallback")


def load_target_registry(path: Path) -> TargetRegistry:
    raw = json.loads(path.read_text(encoding="utf-8"))
    targets = tuple(_target_from_dict(item) for item in raw.get("targets", []))
    registry = TargetRegistry(
        project=str(raw.get("project", "")),
        registry_version=str(raw.get("registry_version", "")),
        targets=targets,
    )
    _validate_registry(registry)
    return registry


def _target_from_dict(raw: dict[str, Any]) -> Target:
    references = tuple(Reference(**item) for item in raw.get("key_references", []))
    structures = tuple(StructureCandidate(**item) for item in raw.get("structures", []))
    return Target(
        target_id=str(raw.get("target_id", "")),
        decision_role=str(raw.get("decision_role", "")),
        protein_name=str(raw.get("protein_name", "")),
        gene_name=str(raw.get("gene_name", "")),
        organism=str(raw.get("organism", "")),
        uniprot_accession=str(raw.get("uniprot_accession", "")),
        rationale=str(raw.get("rationale", "")),
        key_references=references,
        structures=structures,
    )


def _single_target_by_role(targets: tuple[Target, ...], role: str) -> Target:
    matches = [target for target in targets if target.decision_role == role]
    if len(matches) != 1:
        raise TargetRegistryError(f"Registry must contain exactly one {role} target.")
    return matches[0]


def _validate_registry(registry: TargetRegistry) -> None:
    _single_target_by_role(registry.targets, "primary")
    _single_target_by_role(registry.targets, "fallback")
    for target in registry.targets:
        if not target.structures:
            raise TargetRegistryError(f"Target {target.target_id} has no candidate structures.")
        if not target.uniprot_accession:
            raise TargetRegistryError(f"Target {target.target_id} has no UniProt accession.")
```

- [ ] **Step 5: Run target registry tests**

Run:

```powershell
python -m pytest tests/test_targets.py -q
```

Expected: PASS with `3 passed`.

- [ ] **Step 6: Commit target registry**

Run:

```powershell
git add docs/methods/target_registry.json src/spycep_drug_discovery/targets.py tests/test_targets.py
git commit -m "Add target registry"
```

Expected: commit authored as `Joshua Anojulu <joshanojulu@gmail.com>`.

---

### Task 3: RCSB Metadata Client

**Files:**
- Create: `src/spycep_drug_discovery/rcsb.py`
- Create: `tests/test_rcsb.py`

- [ ] **Step 1: Write RCSB normalization tests**

Create `tests/test_rcsb.py`:

```python
from spycep_drug_discovery.rcsb import RcsbEntryMetadata, normalize_entry_metadata


def test_normalize_entry_metadata_extracts_resolution_and_method():
    raw = {
        "rcsb_id": "7EDD",
        "struct": {"title": "Crystal structure of a serine protease from Streptococcus pyogenes"},
        "exptl": [{"method": "X-RAY DIFFRACTION"}],
        "rcsb_entry_info": {"resolution_combined": [2.897]},
    }

    metadata = normalize_entry_metadata(raw)

    assert metadata == RcsbEntryMetadata(
        pdb_id="7EDD",
        title="Crystal structure of a serine protease from Streptococcus pyogenes",
        method="X-RAY DIFFRACTION",
        resolution_angstrom=2.897,
    )


def test_normalize_entry_metadata_handles_missing_resolution():
    raw = {
        "rcsb_id": "XXXX",
        "struct": {"title": "Predicted or unresolved entry"},
        "exptl": [{"method": "ELECTRON MICROSCOPY"}],
        "rcsb_entry_info": {},
    }

    metadata = normalize_entry_metadata(raw)

    assert metadata.pdb_id == "XXXX"
    assert metadata.resolution_angstrom is None
```

- [ ] **Step 2: Run the failing RCSB tests**

Run:

```powershell
python -m pytest tests/test_rcsb.py -q
```

Expected: FAIL because `spycep_drug_discovery.rcsb` does not exist.

- [ ] **Step 3: Implement RCSB metadata client**

Create `src/spycep_drug_discovery/rcsb.py`:

```python
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import requests


RCSB_ENTRY_URL = "https://data.rcsb.org/rest/v1/core/entry/{pdb_id}"
RCSB_PDB_DOWNLOAD_URL = "https://files.rcsb.org/download/{pdb_id}.pdb"


@dataclass(frozen=True)
class RcsbEntryMetadata:
    pdb_id: str
    title: str
    method: str
    resolution_angstrom: float | None

    def to_json_dict(self) -> dict[str, str | float | None]:
        return asdict(self)


def normalize_entry_metadata(raw: dict[str, Any]) -> RcsbEntryMetadata:
    resolutions = raw.get("rcsb_entry_info", {}).get("resolution_combined") or []
    resolution = float(resolutions[0]) if resolutions else None
    experiments = raw.get("exptl") or [{}]
    return RcsbEntryMetadata(
        pdb_id=str(raw.get("rcsb_id", "")).upper(),
        title=str(raw.get("struct", {}).get("title", "")),
        method=str(experiments[0].get("method", "")),
        resolution_angstrom=resolution,
    )


def fetch_entry_metadata(pdb_id: str, timeout_seconds: int = 30) -> RcsbEntryMetadata:
    response = requests.get(RCSB_ENTRY_URL.format(pdb_id=pdb_id.upper()), timeout=timeout_seconds)
    response.raise_for_status()
    return normalize_entry_metadata(response.json())


def fetch_pdb_text(pdb_id: str, timeout_seconds: int = 30) -> str:
    response = requests.get(RCSB_PDB_DOWNLOAD_URL.format(pdb_id=pdb_id.upper()), timeout=timeout_seconds)
    response.raise_for_status()
    return response.text
```

- [ ] **Step 4: Run RCSB tests**

Run:

```powershell
python -m pytest tests/test_rcsb.py -q
```

Expected: PASS with `2 passed`.

- [ ] **Step 5: Commit RCSB client**

Run:

```powershell
git add src/spycep_drug_discovery/rcsb.py tests/test_rcsb.py
git commit -m "Add RCSB metadata client"
```

Expected: commit authored as `Joshua Anojulu <joshanojulu@gmail.com>`.

---

### Task 4: Structure Fetch Command

**Files:**
- Create: `scripts/fetch_structures.py`
- Create: `data/raw/.gitkeep`
- Create: `data/structures/.gitkeep`
- Modify: `.gitignore`

- [ ] **Step 1: Adjust ignored data directories to keep skeleton folders**

Modify `.gitignore` so these lines remain ignored while `.gitkeep` files are tracked:

```gitignore
data/raw/*
data/external/*
data/processed/*
data/compounds/*
data/structures/*
results/docking/*
results/rankings/*
results/figures/*
results/tables/*

!.gitkeep
!data/raw/.gitkeep
!data/external/.gitkeep
!data/processed/.gitkeep
!data/compounds/.gitkeep
!data/structures/.gitkeep
!results/docking/.gitkeep
!results/rankings/.gitkeep
!results/figures/.gitkeep
!results/tables/.gitkeep
```

- [ ] **Step 2: Create tracked skeleton files**

Create empty files:

```text
data/raw/.gitkeep
data/structures/.gitkeep
results/tables/.gitkeep
```

- [ ] **Step 3: Create structure fetch command**

Create `scripts/fetch_structures.py`:

```python
from __future__ import annotations

import argparse
import json
from pathlib import Path

from spycep_drug_discovery.paths import ensure_dir, project_root
from spycep_drug_discovery.rcsb import fetch_entry_metadata, fetch_pdb_text
from spycep_drug_discovery.targets import load_target_registry


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch RCSB metadata and PDB files for registered target structures.")
    parser.add_argument(
        "--registry",
        type=Path,
        default=Path("docs/methods/target_registry.json"),
        help="Path to target registry JSON.",
    )
    parser.add_argument(
        "--include-fallback",
        action="store_true",
        help="Also fetch fallback target structures.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = project_root()
    registry = load_target_registry(root / args.registry)
    targets = [registry.primary]
    if args.include_fallback:
        targets.append(registry.fallback)

    metadata_dir = ensure_dir(root / "data" / "raw" / "rcsb")
    structure_dir = ensure_dir(root / "data" / "structures")

    for target in targets:
        for structure in target.structures:
            pdb_id = structure.pdb_id.upper()
            metadata = fetch_entry_metadata(pdb_id)
            metadata_path = metadata_dir / f"{pdb_id}.json"
            metadata_path.write_text(
                json.dumps(metadata.to_json_dict(), indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )

            pdb_text = fetch_pdb_text(pdb_id)
            pdb_path = structure_dir / f"{pdb_id}.pdb"
            pdb_path.write_text(pdb_text, encoding="utf-8")
            print(f"Fetched {pdb_id}: {metadata_path} {pdb_path}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run all tests before network fetch**

Run:

```powershell
python -m pytest
```

Expected: PASS with all tests passing.

- [ ] **Step 5: Fetch SpyCEP/ScpC structures**

Run:

```powershell
python scripts/fetch_structures.py
```

Expected: files created under `data/raw/rcsb/` and `data/structures/` for `5XXZ`, `5XYA`, `5XYR`, and `7EDD`.

- [ ] **Step 6: Commit structure fetch command**

Run:

```powershell
git add .gitignore data/raw/.gitkeep data/structures/.gitkeep results/tables/.gitkeep scripts/fetch_structures.py
git commit -m "Add structure fetch command"
```

Expected: generated `.json` and `.pdb` files remain ignored unless separately approved by the user.

---

### Task 5: Feasibility Scoring

**Files:**
- Create: `src/spycep_drug_discovery/feasibility.py`
- Create: `tests/test_feasibility.py`

- [ ] **Step 1: Write feasibility scoring tests**

Create `tests/test_feasibility.py`:

```python
from spycep_drug_discovery.feasibility import score_structure
from spycep_drug_discovery.rcsb import RcsbEntryMetadata


def test_score_structure_rates_high_resolution_xray_as_strong_starting_point():
    metadata = RcsbEntryMetadata(
        pdb_id="7EDD",
        title="Crystal structure of a serine protease from Streptococcus pyogenes",
        method="X-RAY DIFFRACTION",
        resolution_angstrom=2.897,
    )

    score = score_structure(metadata)

    assert score.pdb_id == "7EDD"
    assert score.resolution_flag == "usable"
    assert score.method_flag == "experimental"
    assert score.overall_flag == "candidate"
    assert "manual pocket review required" in score.notes


def test_score_structure_flags_missing_resolution_as_review_required():
    metadata = RcsbEntryMetadata(
        pdb_id="XXXX",
        title="Structure with missing resolution",
        method="X-RAY DIFFRACTION",
        resolution_angstrom=None,
    )

    score = score_structure(metadata)

    assert score.resolution_flag == "missing"
    assert score.overall_flag == "review_required"
```

- [ ] **Step 2: Run the failing feasibility tests**

Run:

```powershell
python -m pytest tests/test_feasibility.py -q
```

Expected: FAIL because `spycep_drug_discovery.feasibility` does not exist.

- [ ] **Step 3: Implement feasibility scoring**

Create `src/spycep_drug_discovery/feasibility.py`:

```python
from __future__ import annotations

from dataclasses import asdict, dataclass

from spycep_drug_discovery.rcsb import RcsbEntryMetadata


@dataclass(frozen=True)
class StructureFeasibility:
    pdb_id: str
    method: str
    resolution_angstrom: float | None
    resolution_flag: str
    method_flag: str
    overall_flag: str
    notes: str

    def to_row(self) -> dict[str, str | float | None]:
        return asdict(self)


def score_structure(metadata: RcsbEntryMetadata) -> StructureFeasibility:
    resolution_flag = _resolution_flag(metadata.resolution_angstrom)
    method_flag = "experimental" if metadata.method else "missing"
    overall_flag = "candidate" if resolution_flag in {"strong", "usable"} and method_flag == "experimental" else "review_required"
    notes = _notes_for_flags(resolution_flag, method_flag)
    return StructureFeasibility(
        pdb_id=metadata.pdb_id,
        method=metadata.method,
        resolution_angstrom=metadata.resolution_angstrom,
        resolution_flag=resolution_flag,
        method_flag=method_flag,
        overall_flag=overall_flag,
        notes=notes,
    )


def _resolution_flag(resolution: float | None) -> str:
    if resolution is None:
        return "missing"
    if resolution <= 2.0:
        return "strong"
    if resolution <= 3.2:
        return "usable"
    return "weak"


def _notes_for_flags(resolution_flag: str, method_flag: str) -> str:
    notes: list[str] = []
    if resolution_flag == "strong":
        notes.append("high-resolution structure")
    if resolution_flag == "usable":
        notes.append("resolution supports initial docking feasibility")
    if resolution_flag in {"missing", "weak"}:
        notes.append("resolution requires manual review before docking")
    if method_flag != "experimental":
        notes.append("experimental method metadata missing")
    notes.append("manual pocket review required")
    return "; ".join(notes)
```

- [ ] **Step 4: Run feasibility tests**

Run:

```powershell
python -m pytest tests/test_feasibility.py -q
```

Expected: PASS with `2 passed`.

- [ ] **Step 5: Commit feasibility scoring**

Run:

```powershell
git add src/spycep_drug_discovery/feasibility.py tests/test_feasibility.py
git commit -m "Add target feasibility scoring"
```

Expected: commit authored as `Joshua Anojulu <joshanojulu@gmail.com>`.

---

### Task 6: Feasibility Report Command

**Files:**
- Create: `scripts/analyze_target_feasibility.py`
- Create: `docs/methods/target_feasibility.md` after command execution
- Generated: `results/tables/target_feasibility.csv`

- [ ] **Step 1: Create feasibility report command**

Create `scripts/analyze_target_feasibility.py`:

```python
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from spycep_drug_discovery.feasibility import score_structure
from spycep_drug_discovery.paths import ensure_dir, project_root
from spycep_drug_discovery.rcsb import normalize_entry_metadata
from spycep_drug_discovery.targets import Target, load_target_registry


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze target-structure feasibility from cached RCSB metadata.")
    parser.add_argument(
        "--registry",
        type=Path,
        default=Path("docs/methods/target_registry.json"),
        help="Path to target registry JSON.",
    )
    parser.add_argument(
        "--include-fallback",
        action="store_true",
        help="Also analyze fallback target structures.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = project_root()
    registry = load_target_registry(root / args.registry)
    targets = [registry.primary]
    if args.include_fallback:
        targets.append(registry.fallback)

    rows = []
    for target in targets:
        rows.extend(_rows_for_target(root, target))

    table_path = ensure_dir(root / "results" / "tables") / "target_feasibility.csv"
    _write_csv(table_path, rows)

    methods_path = root / "docs" / "methods" / "target_feasibility.md"
    methods_path.write_text(_markdown_report(rows), encoding="utf-8")
    print(f"Wrote {table_path}")
    print(f"Wrote {methods_path}")


def _rows_for_target(root: Path, target: Target) -> list[dict[str, str | float | None]]:
    rows: list[dict[str, str | float | None]] = []
    for structure in target.structures:
        metadata_path = root / "data" / "raw" / "rcsb" / f"{structure.pdb_id.upper()}.json"
        raw = json.loads(metadata_path.read_text(encoding="utf-8"))
        score = score_structure(normalize_entry_metadata(raw))
        row = score.to_row()
        row["target_id"] = target.target_id
        row["decision_role"] = target.decision_role
        row["selection_note"] = structure.selection_note
        rows.append(row)
    return rows


def _write_csv(path: Path, rows: list[dict[str, str | float | None]]) -> None:
    fieldnames = [
        "target_id",
        "decision_role",
        "pdb_id",
        "method",
        "resolution_angstrom",
        "resolution_flag",
        "method_flag",
        "overall_flag",
        "selection_note",
        "notes",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _markdown_report(rows: list[dict[str, str | float | None]]) -> str:
    lines = [
        "# Target Feasibility Notes",
        "",
        "This file is generated from cached RCSB metadata and the tracked target registry.",
        "It supports the decision gate for whether SpyCEP/ScpC should proceed to docking.",
        "",
        "| Target | Role | PDB | Resolution | Overall | Notes |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            "| {target_id} | {decision_role} | {pdb_id} | {resolution_angstrom} | {overall_flag} | {notes} |".format(
                **row
            )
        )
    lines.extend(
        [
            "",
            "Decision rule: SpyCEP/ScpC can proceed only if at least one candidate structure has usable metadata and passes manual pocket review.",
            "",
        ]
    )
    return "\n".join(lines)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run all tests before generating report**

Run:

```powershell
python -m pytest
```

Expected: PASS with all tests passing.

- [ ] **Step 3: Generate SpyCEP/ScpC feasibility report**

Run:

```powershell
python scripts/analyze_target_feasibility.py
```

Expected:

```text
Wrote C:\Users\josha\OneDrive\Documents\SpyCEP-Drug-Discovery\results\tables\target_feasibility.csv
Wrote C:\Users\josha\OneDrive\Documents\SpyCEP-Drug-Discovery\docs\methods\target_feasibility.md
```

- [ ] **Step 4: Review generated methods note**

Run:

```powershell
Get-Content docs\methods\target_feasibility.md
```

Expected: Markdown table lists the SpyCEP/ScpC candidate structures and marks each as `candidate` or `review_required`.

- [ ] **Step 5: Commit report command and tracked methods note**

Run:

```powershell
git add scripts/analyze_target_feasibility.py docs/methods/target_feasibility.md
git commit -m "Add target feasibility report"
```

Expected: generated CSV remains ignored unless the user approves tracking it.

---

### Task 7: Windows Setup Documentation

**Files:**
- Create: `environment/setup_windows.md`
- Modify: `README.md`

- [ ] **Step 1: Create Windows setup documentation**

Create `environment/setup_windows.md`:

````markdown
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
````

- [ ] **Step 2: Add setup document link to README**

Append this to `README.md`:

```markdown
## Milestone 1: Target Feasibility

The first executable milestone determines whether SpyCEP/ScpC has structures suitable for defensible docking. See `environment/setup_windows.md` for local setup and commands.
```

- [ ] **Step 3: Commit setup documentation**

Run:

```powershell
git add environment/setup_windows.md README.md
git commit -m "Document Windows setup"
```

Expected: commit authored as `Joshua Anojulu <joshanojulu@gmail.com>`.

---

### Task 8: Final Verification And Private Context Update

**Files:**
- Modify: `PROJECT_CONTEXT.md`

- [ ] **Step 1: Run full test suite**

Run:

```powershell
python -m pytest
```

Expected: PASS with all tests passing.

- [ ] **Step 2: Verify generated artifacts are ignored**

Run:

```powershell
git status --short --ignored
```

Expected: tracked files are clean, `PROJECT_CONTEXT.md` is shown as ignored, and generated files under `data/` and `results/` are ignored.

- [ ] **Step 3: Update private context**

Append this section to `PROJECT_CONTEXT.md`:

```markdown
## Milestone 1 Implementation Result

Implementation plan: `docs/superpowers/plans/2026-07-01-spycep-target-feasibility-implementation.md`.

Milestone 1 builds:

- Python package foundation.
- Target registry for SpyCEP/ScpC and SpeB.
- RCSB metadata/PDB fetch command.
- Target-feasibility scoring.
- Generated target-feasibility methods note.

Current gate after Milestone 1: user must approve whether SpyCEP/ScpC proceeds to compound curation and docking, or whether the project pivots to SpeB.
```

- [ ] **Step 4: Confirm private context remains ignored**

Run:

```powershell
git check-ignore PROJECT_CONTEXT.md
```

Expected:

```text
PROJECT_CONTEXT.md
```

- [ ] **Step 5: Confirm commit author**

Run:

```powershell
git log -1 --pretty=fuller --stat
```

Expected: latest commit author and committer are `Joshua Anojulu <joshanojulu@gmail.com>`.

---

## Self-Review Notes

Spec coverage:

- Target feasibility is covered by Tasks 2, 3, 4, 5, and 6.
- Fallback trigger is supported by the target registry and final context gate in Task 8.
- Compound library curation, docking, analysis, and manuscript outputs are deferred until after the user approves the SpyCEP/ScpC target-feasibility decision.
- Git authorship is checked in Task 8 and must remain under the user's configured identity.
- Private transfer context is preserved and verified in Task 8.

Execution stop point:

- Stop after Task 8 and ask the user to review the target-feasibility evidence.
- Do not begin compound curation or docking until the user approves the target decision.


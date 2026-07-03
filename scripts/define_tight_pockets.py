"""Define tight docking boxes centered on the catalytic triad.

The Milestone-3 first pass used the 22 A receptor-preparation boxes, in which
nearly every ligand trivially contacts the triad. This script computes a smaller
box centered on the D151/H279/S617 side-chain centroid of each receptor so the
docking search is focused on the active site. Boxes are written to
docs/methods/tight_pocket_definition.json.

Run:
    .\\.venv\\Scripts\\python.exe scripts\\define_tight_pockets.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from spycep_drug_discovery.interaction_analysis import active_site_residue_keys, parse_pdbqt_atoms

RECEPTORS = PROJECT_ROOT / "docs" / "methods" / "pdbqt_conversion.json"
POCKETS = PROJECT_ROOT / "docs" / "methods" / "pocket_definition.json"
OUTPUT = PROJECT_ROOT / "docs" / "methods" / "tight_pocket_definition.json"

PADDING_ANGSTROM = 8.0
MIN_SIZE_ANGSTROM = 16.0
MAX_SIZE_ANGSTROM = 20.0


def _clamp(value: float) -> float:
    return round(min(max(value, MIN_SIZE_ANGSTROM), MAX_SIZE_ANGSTROM), 3)


def main() -> None:
    active_site = json.loads(POCKETS.read_text(encoding="utf-8"))["active_site_residues"]
    triad_keys = set(active_site_residue_keys(active_site))
    receptors = json.loads(RECEPTORS.read_text(encoding="utf-8"))["receptors"]

    pockets = []
    for receptor in receptors:
        pdbqt = PROJECT_ROOT / receptor["output_paths"]["pdbqt"]
        triad_atoms = [a for a in parse_pdbqt_atoms(pdbqt.read_text(encoding="utf-8")) if a.residue_key in triad_keys]
        if not triad_atoms:
            raise SystemExit(f"No triad atoms found in {pdbqt}")
        xs = [a.x for a in triad_atoms]
        ys = [a.y for a in triad_atoms]
        zs = [a.z for a in triad_atoms]
        center = {"x": round(sum(xs) / len(xs), 3), "y": round(sum(ys) / len(ys), 3), "z": round(sum(zs) / len(zs), 3)}
        size = {
            "x": _clamp((max(xs) - min(xs)) + PADDING_ANGSTROM),
            "y": _clamp((max(ys) - min(ys)) + PADDING_ANGSTROM),
            "z": _clamp((max(zs) - min(zs)) + PADDING_ANGSTROM),
        }
        pockets.append(
            {
                "pocket_id": receptor["pocket_id"],
                "pdb_id": receptor["pdb_id"],
                "receptor_pdbqt_path": receptor["output_paths"]["pdbqt"],
                "box_center_angstrom": center,
                "box_size_angstrom": size,
                "triad_atom_count": len(triad_atoms),
            }
        )
        print(f"  {receptor['pocket_id']}: center {center}  size {size}  ({len(triad_atoms)} triad atoms)")

    OUTPUT.write_text(
        json.dumps(
            {
                "definition_version": "2026-07-03",
                "basis": "centroid and extent of D151/H279/S617 side-chain atoms + 8 A padding, clamped to [16,20] A",
                "padding_angstrom": PADDING_ANGSTROM,
                "pockets": pockets,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {OUTPUT.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()

"""Define tight docking boxes centered on the catalytic-triad side chains.

The Milestone-3 first pass used the 22 A receptor-preparation boxes, in which nearly
every ligand trivially contacts the triad. This script computes a smaller box centered
on the D151/H279/S617 *side-chain* centroid of each receptor so the docking search is
focused on the catalytic machinery.

Coordinates come from the cleaned receptor PDB (which carries atom names) via
`pocket_definition.active_site_side_chain_coordinates`. An earlier version read the
PDBQT instead, which has no atom names, and so silently averaged backbone atoms and
polar hydrogens into a box it still described as a "side-chain centroid".

Run:
    .\\.venv\\Scripts\\python.exe scripts\\define_tight_pockets.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from spycep_drug_discovery.pocket_definition import active_site_side_chain_coordinates

RECEPTORS = PROJECT_ROOT / "docs" / "methods" / "pdbqt_conversion.json"
OUTPUT = PROJECT_ROOT / "docs" / "methods" / "tight_pocket_definition.json"

PADDING_ANGSTROM = 8.0
MIN_SIZE_ANGSTROM = 16.0
MAX_SIZE_ANGSTROM = 20.0


def _clamp(value: float) -> float:
    return round(min(max(value, MIN_SIZE_ANGSTROM), MAX_SIZE_ANGSTROM), 3)


def main() -> None:
    receptors = json.loads(RECEPTORS.read_text(encoding="utf-8"))["receptors"]

    pockets = []
    for receptor in receptors:
        prepared_pdb = PROJECT_ROOT / receptor["source_prepared_pdb_path"]
        atoms = active_site_side_chain_coordinates(prepared_pdb)
        xs = [a.x for a in atoms]
        ys = [a.y for a in atoms]
        zs = [a.z for a in atoms]
        center = {
            "x": round(sum(xs) / len(xs), 3),
            "y": round(sum(ys) / len(ys), 3),
            "z": round(sum(zs) / len(zs), 3),
        }
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
                "source_prepared_pdb_path": receptor["source_prepared_pdb_path"],
                "box_center_angstrom": center,
                "box_size_angstrom": size,
                "side_chain_atom_count": len(atoms),
            }
        )
        print(f"  {receptor['pocket_id']}: center {center}  size {size}  ({len(atoms)} side-chain atoms)")

    OUTPUT.write_text(
        json.dumps(
            {
                "definition_version": "2026-07-12",
                "basis": (
                    "centroid and extent of the D151/H279/S617 side-chain atoms "
                    "(ASP CG/OD1/OD2, HIS CG/ND1/CD2/CE1/NE2, SER CB/OG) read from the cleaned "
                    "receptor PDB, + 8 A padding, clamped to [16,20] A"
                ),
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

"""Compute docking statistics (bootstrap CIs, Mann-Whitney, positive-control margin).

Reads the tracked docking result manifests and writes docs/methods/docking_statistics.json:
- custom vs FDA comparison (best affinity and ligand efficiency) for the wide and tight
  boxes, each with a 95% bootstrap CI on the mean difference and a Mann-Whitney U test;
- the SpeB positive-control margin (Q9D vs decoys).

Run:
    .\\.venv\\Scripts\\python.exe scripts\\compute_statistics.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from spycep_drug_discovery.statistics_analysis import (
    bootstrap_mean_difference,
    mann_whitney,
    positive_control_margin,
)

METHODS = PROJECT_ROOT / "docs" / "methods"
LIBRARY = METHODS / "compound_library_source.json"
OUTPUT = METHODS / "docking_statistics.json"


def _split_by_set(result_path: Path, setof: dict, key: str) -> tuple[list, list]:
    ranking = json.loads(result_path.read_text(encoding="utf-8"))["ranking"]
    # A non-negative Vina affinity means no valid pose (ligand does not fit the box);
    # exclude these non-fits from the quantitative comparison.
    ranking = [r for r in ranking if r["ensemble_best_affinity_kcal_mol"] < 0]
    custom = [r[key] for r in ranking if setof.get(r["ligand_id"]) == "custom_anti_virulence"]
    fda = [r[key] for r in ranking if setof.get(r["ligand_id"]) == "fda_comparator"]
    return custom, fda


def _comparison(result_path: Path, setof: dict) -> dict:
    out = {}
    for key, label in (("ensemble_best_affinity_kcal_mol", "best_affinity"),
                       ("ligand_efficiency_kcal_mol_per_heavy_atom", "ligand_efficiency")):
        custom, fda = _split_by_set(result_path, setof, key)
        out[label] = {
            "custom_n": len(custom),
            "fda_n": len(fda),
            "bootstrap_mean_difference_custom_minus_fda": bootstrap_mean_difference(custom, fda),
            "mann_whitney": mann_whitney(custom, fda),
        }
    return out


def main() -> None:
    setof = {c["ligand_id"]: c["set"] for c in json.loads(LIBRARY.read_text(encoding="utf-8"))["compounds"]}
    speb = json.loads((METHODS / "speb_positive_control_result.json").read_text(encoding="utf-8"))
    decoys = [r["best_affinity_kcal_mol"] for r in speb["results"] if r["ligand_id"] != "Q9D_speb_inhibitor"]

    stats = {
        "note": "More negative affinity/efficiency = stronger. Bootstrap = 95% CI, 10000 resamples, seed 42.",
        "custom_vs_fda_wide_box": _comparison(METHODS / "docking_result.json", setof),
        "custom_vs_fda_tight_box": _comparison(METHODS / "docking_result_tight.json", setof),
        "speb_positive_control": positive_control_margin(speb["positive_best_affinity_kcal_mol"], decoys),
    }
    OUTPUT.write_text(json.dumps(stats, indent=2) + "\n", encoding="utf-8")

    b = stats["custom_vs_fda_tight_box"]["best_affinity"]["bootstrap_mean_difference_custom_minus_fda"]
    pc = stats["speb_positive_control"]
    print(f"Tight-box custom-vs-FDA best-affinity mean diff {b['observed_difference']:.3f} "
          f"[{b['ci95_low']:.3f}, {b['ci95_high']:.3f}] (excludes 0: {b['excludes_zero']})")
    print(f"SpeB Q9D beats all decoys: {pc['beats_all_decoys']}, margin {pc['margin_to_best_decoy']:.2f} kcal/mol, "
          f"{pc['sd_stronger_than_decoy_mean']:.1f} SD below decoy mean")
    print(f"Wrote {OUTPUT.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()

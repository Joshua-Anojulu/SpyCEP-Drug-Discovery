"""Compute docking statistics (bootstrap CIs, Mann-Whitney, positive-control margin).

Reads the tracked docking result manifests and writes docs/methods/docking_statistics.json:
- custom vs FDA comparison (best affinity and ligand efficiency) for the wide and tight
  boxes, each with a 95% bootstrap CI on the mean difference and a Mann-Whitney U test;
- the SpeB positive-control margin, reported on BOTH raw affinity and ligand efficiency.

The positive control is reported on both metrics deliberately. This project ranks by
ligand efficiency because Vina's raw score scales with molecular size; validating the
pipeline on raw affinity alone would mean judging the control by the very metric the
study disowns everywhere else.

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
OUTPUT = METHODS / "docking_statistics.json"

AFFINITY = "ensemble_best_affinity_kcal_mol"
EFFICIENCY = "ligand_efficiency_kcal_mol_per_heavy_atom"


def _fits(ranking: list[dict]) -> list[dict]:
    # A non-negative Vina affinity means no valid pose (the ligand does not fit the box).
    return [row for row in ranking if row[AFFINITY] < 0]


def _comparison(result_path: Path) -> dict:
    ranking = _fits(json.loads(result_path.read_text(encoding="utf-8"))["ranking"])
    custom = [r for r in ranking if r["set"] == "custom_anti_virulence"]
    fda = [r for r in ranking if r["set"] == "fda_comparator"]

    out: dict = {
        "non_fits_excluded": [
            r["ligand_id"]
            for r in json.loads(result_path.read_text(encoding="utf-8"))["ranking"]
            if r[AFFINITY] >= 0
        ]
    }
    for key, label in ((AFFINITY, "best_affinity"), (EFFICIENCY, "ligand_efficiency")):
        a = [r[key] for r in custom]
        b = [r[key] for r in fda]
        out[label] = {
            "custom_n": len(a),
            "fda_n": len(b),
            "custom_mean": sum(a) / len(a),
            "fda_mean": sum(b) / len(b),
            "bootstrap_mean_difference_custom_minus_fda": bootstrap_mean_difference(a, b),
            "mann_whitney": mann_whitney(a, b),
        }
    return out


def _triad_engagement(result_path: Path) -> dict:
    """Per-ligand triad contact, counted over ligands and not over pose rows.

    The earlier write-up reported "55-56 of 73" contacting all three residues. That
    figure is a pose-row count (ligand x receptor, out of 146) presented as a per-ligand
    count out of 73; no per-ligand reading of the manifests reproduces it.
    """
    manifest = json.loads(result_path.read_text(encoding="utf-8"))
    by_ligand: dict[str, list[dict]] = {}
    for row in manifest["pose_interactions"]:
        by_ligand.setdefault(row["ligand_id"], []).append(row)

    def _contacting(minimum: int) -> int:
        return sum(
            1
            for rows in by_ligand.values()
            if any(len(r["contacted_active_site_residues"]) >= minimum for r in rows)
        )

    total = len(by_ligand)
    return {
        "ligands": total,
        "contacting_at_least_one_triad_residue": _contacting(1),
        "contacting_at_least_two_triad_residues": _contacting(2),
        "contacting_all_three_triad_residues": _contacting(3),
        "counted_over": "ligands (best receptor), not ligand x receptor pose rows",
    }


def main() -> None:
    speb = json.loads((METHODS / "speb_positive_control_result.json").read_text(encoding="utf-8"))
    decoys = [r for r in speb["results"] if r["role"] == "decoy"]
    positive = next(r for r in speb["results"] if r["role"] == "positive_known_inhibitor")

    stats = {
        "note": (
            "More negative affinity/efficiency = stronger. Bootstrap = 95% CI, 10000 resamples, seed 42. "
            "Ligands are docked as their dominant microspecies at pH 7.4."
        ),
        "custom_vs_fda_wide_box": _comparison(METHODS / "docking_result.json"),
        "custom_vs_fda_tight_box": _comparison(METHODS / "docking_result_tight.json"),
        "triad_engagement_wide_box": _triad_engagement(METHODS / "docking_result.json"),
        "triad_engagement_tight_box": _triad_engagement(METHODS / "docking_result_tight.json"),
        "speb_positive_control": {
            "decoy_count": len(decoys),
            "decoys_are_size_matched": True,
            "positive_heavy_atom_count": positive["heavy_atom_count"],
            "decoy_heavy_atom_range": [
                min(r["heavy_atom_count"] for r in decoys),
                max(r["heavy_atom_count"] for r in decoys),
            ],
            "by_best_affinity": positive_control_margin(
                positive["best_affinity_kcal_mol"],
                [r["best_affinity_kcal_mol"] for r in decoys],
            ),
            "by_ligand_efficiency": positive_control_margin(
                positive["ligand_efficiency_kcal_mol_per_heavy_atom"],
                [r["ligand_efficiency_kcal_mol_per_heavy_atom"] for r in decoys],
            ),
        },
    }
    stats["speb_positive_control"]["passes_on_both_metrics"] = (
        stats["speb_positive_control"]["by_best_affinity"]["beats_all_decoys"]
        and stats["speb_positive_control"]["by_ligand_efficiency"]["beats_all_decoys"]
    )
    OUTPUT.write_text(json.dumps(stats, indent=2) + "\n", encoding="utf-8")

    for box in ("wide", "tight"):
        b = stats[f"custom_vs_fda_{box}_box"]["best_affinity"]
        d = b["bootstrap_mean_difference_custom_minus_fda"]
        print(f"{box:>5} box  custom {b['custom_mean']:.2f} vs FDA {b['fda_mean']:.2f}  "
              f"diff {d['observed_difference']:+.3f} [{d['ci95_low']:.3f}, {d['ci95_high']:.3f}]  "
              f"significant: {d['excludes_zero']}")
    pc = stats["speb_positive_control"]
    print(f"\nSpeB control ({pc['decoy_count']} size-matched decoys, "
          f"Q9D {pc['positive_heavy_atom_count']} heavy atoms vs decoys {pc['decoy_heavy_atom_range']}):")
    print(f"  by affinity          : beats all decoys = {pc['by_best_affinity']['beats_all_decoys']}, "
          f"{pc['by_best_affinity']['sd_stronger_than_decoy_mean']:.1f} SD" if pc["by_best_affinity"]["sd_stronger_than_decoy_mean"] else "")
    print(f"  by ligand efficiency : beats all decoys = {pc['by_ligand_efficiency']['beats_all_decoys']}, "
          f"{pc['by_ligand_efficiency']['sd_stronger_than_decoy_mean']:.1f} SD")
    print(f"  passes on BOTH metrics: {pc['passes_on_both_metrics']}")
    print(f"\nWrote {OUTPUT.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()

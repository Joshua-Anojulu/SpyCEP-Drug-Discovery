"""Full-library docking run against the SpyCEP 5XYA + 7EDD receptor ensemble.

Prepares every approved compound (with desalting) to PDBQT, docks each into both
receptors with AutoDock Vina (fixed seed), ranks by ligand efficiency, and runs
catalytic-triad interaction analysis. Fault-tolerant: a ligand-prep or docking
failure is recorded and skipped, not fatal.

Run (needs tools/vina.exe and the receptor-prep extra):
    .\\.venv\\Scripts\\python.exe scripts\\run_docking.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from spycep_drug_discovery.docking import DEFAULT_EXHAUSTIVENESS, DEFAULT_NUM_MODES, DEFAULT_SEED, DockingError, dock_ligand
from spycep_drug_discovery.docking_analysis import rank_docking_results, write_ranking_csv
from spycep_drug_discovery.interaction_analysis import analyze_pose_interactions
from spycep_drug_discovery.ligand_preparation import LigandPreparationError, prepare_ligand

TIGHT = "--tight" in sys.argv[1:]

VINA = PROJECT_ROOT / "tools" / "vina.exe"
MEEKO = PROJECT_ROOT / ".venv" / "Scripts" / "mk_prepare_ligand.exe"
LIBRARY = PROJECT_ROOT / "docs" / "methods" / "compound_library_source.json"
RECEPTORS = PROJECT_ROOT / "docs" / "methods" / "pdbqt_conversion.json"
TIGHT_POCKETS = PROJECT_ROOT / "docs" / "methods" / "tight_pocket_definition.json"
POCKETS = PROJECT_ROOT / "docs" / "methods" / "pocket_definition.json"
RESULT = PROJECT_ROOT / "docs" / "methods" / ("docking_result_tight.json" if TIGHT else "docking_result.json")
RANKING = PROJECT_ROOT / "results" / "tables" / ("docking_ranking_tight.csv" if TIGHT else "docking_ranking.csv")
POSE_DIR = PROJECT_ROOT / "results" / "docking" / ("library_tight" if TIGHT else "library")


def _receptors() -> list[dict]:
    if TIGHT:
        pockets = json.loads(TIGHT_POCKETS.read_text(encoding="utf-8"))["pockets"]
        return [
            {
                "pocket_id": p["pocket_id"],
                "pdb_id": p["pdb_id"],
                "receptor_pdbqt_path": p["receptor_pdbqt_path"],
                "box_center_angstrom": p["box_center_angstrom"],
                "box_size_angstrom": p["box_size_angstrom"],
            }
            for p in pockets
        ]
    manifest = json.loads(RECEPTORS.read_text(encoding="utf-8"))
    return [
        {
            "pocket_id": r["pocket_id"],
            "pdb_id": r["pdb_id"],
            "receptor_pdbqt_path": r["output_paths"]["pdbqt"],
            "box_center_angstrom": r["box_center_angstrom"],
            "box_size_angstrom": r["box_size_angstrom"],
        }
        for r in manifest["receptors"]
    ]


def main() -> None:
    compounds = json.loads(LIBRARY.read_text(encoding="utf-8"))["compounds"]
    receptors = _receptors()
    active_site = json.loads(POCKETS.read_text(encoding="utf-8"))["active_site_residues"]

    prepared: list[dict] = []
    prep_failures: list[dict] = []
    for compound in compounds:
        try:
            ligand = prepare_ligand(
                compound,
                project_root=PROJECT_ROOT,
                work_dir=PROJECT_ROOT / "data" / "compounds" / "sdf",
                output_dir=PROJECT_ROOT / "data" / "compounds" / "pdbqt",
                meeko_command=[MEEKO],
            )
            ligand["set"] = compound["set"]
            prepared.append(ligand)
            print(f"  prep ok   {compound['ligand_id']}")
        except (LigandPreparationError, Exception) as exc:  # noqa: BLE001 - record and continue
            prep_failures.append({"ligand_id": compound["ligand_id"], "error": str(exc)[:200]})
            print(f"  prep FAIL {compound['ligand_id']}: {str(exc)[:120]}")

    results: list[dict] = []
    dock_failures: list[dict] = []
    for ligand in prepared:
        for receptor in receptors:
            try:
                row = dock_ligand(
                    vina_executable=VINA,
                    receptor=receptor,
                    ligand_id=ligand["ligand_id"],
                    ligand_pdbqt=PROJECT_ROOT / ligand["pdbqt_path"],
                    project_root=PROJECT_ROOT,
                    output_dir=POSE_DIR,
                )
            except DockingError as exc:
                dock_failures.append(
                    {"ligand_id": ligand["ligand_id"], "pocket_id": receptor["pocket_id"], "error": str(exc)[:200]}
                )
                print(f"  dock FAIL {ligand['ligand_id']} vs {receptor['pocket_id']}: {str(exc)[:100]}")
                continue
            row["set"] = ligand["set"]
            row["heavy_atom_count"] = ligand["heavy_atom_count"]
            row["interactions"] = analyze_pose_interactions(
                PROJECT_ROOT / receptor["receptor_pdbqt_path"],
                PROJECT_ROOT / row["out_path"],
                active_site,
            )
            results.append(row)
            print(f"  dock ok   {ligand['ligand_id']:<28} {receptor['pocket_id']:<32} best={row['best_affinity_kcal_mol']:.2f}")

    ranked = rank_docking_results(results)
    write_ranking_csv(ranked, RANKING)

    manifest = {
        "run_version": "2026-07-03" if TIGHT else "2026-07-02",
        "status": "full_library_docking_computational_prioritization_only",
        "box_mode": "tight_triad_centered" if TIGHT else "receptor_prep_box",
        "seed": DEFAULT_SEED,
        "exhaustiveness": DEFAULT_EXHAUSTIVENESS,
        "num_modes": DEFAULT_NUM_MODES,
        "vina_version": "AutoDock Vina v1.2.7",
        "receptor_ensemble": [r["pocket_id"] for r in receptors],
        "compounds_input": len(compounds),
        "compounds_docked": len({row["ligand_id"] for row in results}),
        "prep_failures": prep_failures,
        "dock_failures": dock_failures,
        "ranking": ranked,
        "pose_interactions": [
            {
                "ligand_id": row["ligand_id"],
                "set": row["set"],
                "pocket_id": row["pocket_id"],
                "best_affinity_kcal_mol": row["best_affinity_kcal_mol"],
                "contacted_active_site_residues": row["interactions"]["contacted_active_site_residues"],
                "contacts_catalytic_triad": row["interactions"]["contacts_catalytic_triad"],
            }
            for row in results
        ],
    }
    RESULT.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"\nDocked {manifest['compounds_docked']}/{len(compounds)} compounds; "
          f"prep failures {len(prep_failures)}, dock failures {len(dock_failures)}.")
    print(f"Wrote {RANKING.relative_to(PROJECT_ROOT)} and {RESULT.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()

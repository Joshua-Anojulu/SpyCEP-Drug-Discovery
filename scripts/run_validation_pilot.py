"""Milestone 3 pipeline-validation pilot.

Runs the ligand-preparation -> AutoDock Vina docking pipeline end-to-end on a small
throwaway validation set (docs/methods/validation_pilot_compounds.json) against the
approved 5XYA + 7EDD receptor ensemble, then writes a ranking table and a result
manifest. This validates that the pipeline runs and is reproducible; it is NOT the
curated research library and makes no hit claims.

Run:
    .\\.venv\\Scripts\\python.exe scripts\\run_validation_pilot.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from spycep_drug_discovery.docking import DEFAULT_EXHAUSTIVENESS, DEFAULT_NUM_MODES, DEFAULT_SEED, dock_ligand
from spycep_drug_discovery.docking_analysis import rank_docking_results, write_ranking_csv
from spycep_drug_discovery.interaction_analysis import analyze_pose_interactions
from spycep_drug_discovery.ligand_preparation import prepare_ligands

VINA_EXECUTABLE = PROJECT_ROOT / "tools" / "vina.exe"
MEEKO_LIGAND = PROJECT_ROOT / ".venv" / "Scripts" / "mk_prepare_ligand.exe"
COMPOUND_FILE = PROJECT_ROOT / "docs" / "methods" / "validation_pilot_compounds.json"
RECEPTOR_FILE = PROJECT_ROOT / "docs" / "methods" / "pdbqt_conversion.json"
POCKET_FILE = PROJECT_ROOT / "docs" / "methods" / "pocket_definition.json"
RESULT_MANIFEST = PROJECT_ROOT / "docs" / "methods" / "validation_pilot_result.json"
RANKING_CSV = PROJECT_ROOT / "results" / "tables" / "validation_pilot_ranking.csv"


def _load_receptors() -> list[dict]:
    manifest = json.loads(RECEPTOR_FILE.read_text(encoding="utf-8"))
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
    compounds = json.loads(COMPOUND_FILE.read_text(encoding="utf-8"))["compounds"]
    receptors = _load_receptors()
    active_site = json.loads(POCKET_FILE.read_text(encoding="utf-8"))["active_site_residues"]

    ligand_manifest = prepare_ligands(
        compounds,
        project_root=PROJECT_ROOT,
        work_dir=PROJECT_ROOT / "data" / "compounds" / "sdf",
        output_dir=PROJECT_ROOT / "data" / "compounds" / "pdbqt",
        meeko_command=[MEEKO_LIGAND],
    )
    ligand_by_id = {lig["ligand_id"]: lig for lig in ligand_manifest["ligands"]}
    role_by_id = {c["ligand_id"]: c.get("role") for c in compounds}

    results: list[dict] = []
    for compound in compounds:
        ligand = ligand_by_id[compound["ligand_id"]]
        for receptor in receptors:
            row = dock_ligand(
                vina_executable=VINA_EXECUTABLE,
                receptor=receptor,
                ligand_id=ligand["ligand_id"],
                ligand_pdbqt=PROJECT_ROOT / ligand["pdbqt_path"],
                project_root=PROJECT_ROOT,
                output_dir=PROJECT_ROOT / "results" / "docking" / "validation_pilot",
            )
            row["role"] = role_by_id.get(ligand["ligand_id"])
            row["heavy_atom_count"] = ligand["heavy_atom_count"]
            row["interactions"] = analyze_pose_interactions(
                PROJECT_ROOT / receptor["receptor_pdbqt_path"],
                PROJECT_ROOT / row["out_path"],
                active_site,
            )
            results.append(row)
            contacts = ",".join(row["interactions"]["contacted_active_site_residues"]) or "none"
            print(
                f"  {row['ligand_id']:>18} vs {row['pocket_id']:<32} "
                f"best={row['best_affinity_kcal_mol']:.3f}  active-site contacts: {contacts}"
            )

    ranked = rank_docking_results(results)
    write_ranking_csv(ranked, RANKING_CSV)

    # Reproducibility check: re-dock the first ligand/receptor and compare best affinity.
    repeat = dock_ligand(
        vina_executable=VINA_EXECUTABLE,
        receptor=receptors[0],
        ligand_id=ligand_by_id[compounds[0]["ligand_id"]]["ligand_id"],
        ligand_pdbqt=PROJECT_ROOT / ligand_by_id[compounds[0]["ligand_id"]]["pdbqt_path"],
        project_root=PROJECT_ROOT,
        output_dir=PROJECT_ROOT / "results" / "docking" / "validation_pilot_repeat",
    )
    reproducible = repeat["best_affinity_kcal_mol"] == results[0]["best_affinity_kcal_mol"]

    manifest = {
        "pilot_version": "2026-07-02",
        "status": "pipeline_validation_only_not_hit_discovery",
        "seed": DEFAULT_SEED,
        "exhaustiveness": DEFAULT_EXHAUSTIVENESS,
        "num_modes": DEFAULT_NUM_MODES,
        "vina_version": "AutoDock Vina v1.2.7",
        "receptor_ensemble": [r["pocket_id"] for r in receptors],
        "reproducibility_check": {
            "ligand_id": repeat["ligand_id"],
            "pocket_id": repeat["pocket_id"],
            "first_run_best": results[0]["best_affinity_kcal_mol"],
            "repeat_run_best": repeat["best_affinity_kcal_mol"],
            "deterministic": reproducible,
        },
        "ligands": ligand_manifest["ligands"],
        "ranking": ranked,
        "pose_interactions": [
            {
                "ligand_id": row["ligand_id"],
                "pocket_id": row["pocket_id"],
                "best_affinity_kcal_mol": row["best_affinity_kcal_mol"],
                "contacted_active_site_residues": row["interactions"]["contacted_active_site_residues"],
                "contacts_catalytic_triad": row["interactions"]["contacts_catalytic_triad"],
            }
            for row in results
        ],
    }
    RESULT_MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"\nReproducibility deterministic: {reproducible}")
    print(f"Wrote {RANKING_CSV.relative_to(PROJECT_ROOT)}")
    print(f"Wrote {RESULT_MANIFEST.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()

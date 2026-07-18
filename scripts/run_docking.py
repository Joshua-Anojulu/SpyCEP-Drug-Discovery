"""Run one primary-screen docking workflow from the frozen attempt relation.

This entry point performs every preparation before invoking Vina and fails loudly if
the content-addressed QC or MMFF gates are stale or blocked.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from spycep_drug_discovery.attempt_manifest import validate_attempt_manifest
from spycep_drug_discovery.docking import (
    DEFAULT_CPU,
    DEFAULT_EXHAUSTIVENESS,
    DEFAULT_NUM_MODES,
    DEFAULT_SCORING,
    DEFAULT_SEED,
    DEFAULT_TIMEOUT_SECONDS,
    DockingError,
    InfrastructureError,
    build_run_manifest,
    campaign_lock,
    campaign_output_dir,
    dock_ligand,
    initialize_spawn_retry_ledger,
    is_continuable_scientific_disposition,
    require_campaign_id,
    require_suspend_calibration,
    require_unsealed,
    write_timeout_qc_report,
)
from spycep_drug_discovery.docking_analysis import (
    rank_docking_results,
    write_ranking_csv,
)
from spycep_drug_discovery.environment import runtime_versions
from spycep_drug_discovery.interaction_analysis import analyze_pose_interactions
from spycep_drug_discovery.ligand_preparation import prepare_ligand
from spycep_drug_discovery.pdbqt_quality import validate_pdbqt_quality_gate
from spycep_drug_discovery.preparation_audit import validate_preparation_audit
from spycep_drug_discovery.species import (
    catalog_state,
    load_species_catalog,
    sha256_file,
)


TIGHT = "--tight" in sys.argv[1:]
RESUME = "--resume" in sys.argv[1:]
WORKFLOW = "tight" if TIGHT else "wide"

VINA = PROJECT_ROOT / "tools" / "vina.exe"
MEEKO = PROJECT_ROOT / ".venv" / "Scripts" / "mk_prepare_ligand.exe"
SPECIES = PROJECT_ROOT / "docs" / "methods" / "species_audit.json"
ATTEMPTS = PROJECT_ROOT / "docs" / "methods" / "attempt_manifest.json"
PREPARATION_AUDIT = PROJECT_ROOT / "docs" / "methods" / "mmff_preparation_audit.json"
CONVERSION = PROJECT_ROOT / "docs" / "methods" / "pdbqt_conversion.json"
QC = PROJECT_ROOT / "docs" / "methods" / "pdbqt_quality_review.json"
POCKETS = PROJECT_ROOT / "docs" / "methods" / "pocket_definition.json"
RESULT = PROJECT_ROOT / "docs" / "methods" / (
    "docking_result_tight.json" if TIGHT else "docking_result.json"
)
RANKING = PROJECT_ROOT / "results" / "tables" / (
    "docking_ranking_tight.csv" if TIGHT else "docking_ranking.csv"
)
def _atomic_json(path: Path, value: dict) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _load_and_require_gates():
    catalog = load_species_catalog(SPECIES)
    attempts = json.loads(ATTEMPTS.read_text(encoding="utf-8"))
    validate_attempt_manifest(attempts, catalog)
    species_hash = sha256_file(SPECIES)
    attempt_hash = sha256_file(ATTEMPTS)

    conversion = json.loads(CONVERSION.read_text(encoding="utf-8"))
    qc = json.loads(QC.read_text(encoding="utf-8"))
    pockets = json.loads(POCKETS.read_text(encoding="utf-8"))
    validate_pdbqt_quality_gate(
        qc,
        conversion,
        pockets,
        project_root=PROJECT_ROOT,
        conversion_manifest_sha256=sha256_file(CONVERSION),
        pocket_definition_sha256=sha256_file(POCKETS),
        required_pocket_ids={
            row["pocket_id"] for row in conversion["receptors"]
        },
    )

    audit = json.loads(PREPARATION_AUDIT.read_text(encoding="utf-8"))
    expected_keys = {
        (row["entity_id"], row["state_id"])
        for row in attempts["attempts"]
    }
    validate_preparation_audit(
        audit,
        species_catalog_sha256=species_hash,
        attempt_manifest_sha256=attempt_hash,
        expected_state_keys=expected_keys,
    )
    return catalog, attempts, pockets, species_hash, attempt_hash


def _run_campaign(campaign_id: str, pose_dir: Path) -> None:
    initialize_spawn_retry_ledger(PROJECT_ROOT, campaign_id)
    (
        catalog,
        attempt_manifest,
        pockets,
        species_hash,
        attempt_hash,
    ) = _load_and_require_gates()
    versions = runtime_versions(VINA)
    attempts = [
        row
        for row in attempt_manifest["attempts"]
        if row["workflow"] == WORKFLOW
    ]
    if not attempts:
        raise SystemExit(f"No legal {WORKFLOW} attempts in attempt manifest.")

    # Complete all preparation first. No LigandPreparationError is converted into a
    # skipped compound, so Vina cannot start after a partial preparation population.
    prepared_by_key = {}
    for entity_id, state_id in sorted(
        {(row["entity_id"], row["state_id"]) for row in attempts}
    ):
        state = catalog_state(catalog, entity_id, state_id)
        ligand = prepare_ligand(
            {
                "entity_id": entity_id,
                "state_id": state_id,
                "smiles": state["source_smiles"],
                "set": state.get("set"),
            },
            project_root=PROJECT_ROOT,
            work_dir=PROJECT_ROOT / "data" / "compounds" / "sdf_stage2",
            output_dir=PROJECT_ROOT / "data" / "compounds" / "pdbqt_stage2",
            meeko_command=[MEEKO],
            species_catalog=catalog,
        )
        prepared_by_key[(entity_id, state_id)] = ligand
        print(
            f"  prep ok   {entity_id}/{state_id} "
            f"charge={ligand['formal_charge']:+d} MMFF={ligand['mmff_variant']}"
        )

    active_site = pockets["active_site_residues"]
    run_records = []
    valid_results = []
    interactions = []
    for attempt in attempts:
        key = (attempt["entity_id"], attempt["state_id"])
        ligand = prepared_by_key[key]
        receptor = {
            field: attempt[field]
            for field in (
                "pocket_id",
                "pdb_id",
                "receptor_pdbqt_path",
                "box_center_angstrom",
                "box_size_angstrom",
            )
        }
        try:
            record = dock_ligand(
                vina_executable=VINA,
                receptor=receptor,
                entity_id=attempt["entity_id"],
                state_id=attempt["state_id"],
                ligand_pdbqt=PROJECT_ROOT / ligand["pdbqt_path"],
                project_root=PROJECT_ROOT,
                output_dir=pose_dir,
                workflow=WORKFLOW,
                species_catalog_sha256=species_hash,
                attempt_manifest_sha256=attempt_hash,
                software_versions=versions,
                seed=DEFAULT_SEED,
                exhaustiveness=DEFAULT_EXHAUSTIVENESS,
                num_modes=DEFAULT_NUM_MODES,
                cpu=DEFAULT_CPU,
                scoring=DEFAULT_SCORING,
                resume=RESUME,
                timeout_seconds=DEFAULT_TIMEOUT_SECONDS,
                campaign_id=campaign_id,
            )
        except DockingError as exc:
            if not is_continuable_scientific_disposition(exc.run_record):
                raise
            record = exc.run_record
            run_records.append(record)
            print(
                f"  dock {record['status']:<19} "
                f"{attempt['entity_id']}/{attempt['state_id']} vs {attempt['pocket_id']}: "
                f"{record['cause']}"
            )
            continue

        record["set"] = ligand.get("set")
        record["role"] = ligand.get("set")
        record["heavy_atom_count"] = ligand["heavy_atom_count"]
        record["docked_smiles"] = ligand["docked_smiles"]
        record["formal_charge"] = ligand["formal_charge"]
        run_records.append(record)
        valid_results.append(record)
        pose_interaction = analyze_pose_interactions(
            PROJECT_ROOT / receptor["receptor_pdbqt_path"],
            PROJECT_ROOT / record["out_path"],
            active_site,
        )
        interactions.append(
            {
                "claim_key": record["claim_key"],
                "entity_id": record["entity_id"],
                "state_id": record["state_id"],
                "species_key": record["species_key"],
                "pocket_id": record["pocket_id"],
                "best_affinity_kcal_mol": record["best_affinity_kcal_mol"],
                **pose_interaction,
            }
        )
        print(
            f"  dock ok   {attempt['entity_id']}/{attempt['state_id']} "
            f"vs {attempt['pocket_id']} "
            f"best={record['best_affinity_kcal_mol']:.2f}"
        )

    ranked = rank_docking_results(valid_results)
    write_ranking_csv(ranked, RANKING)
    timeout_qc_path, _ = write_timeout_qc_report(
        pose_dir, run_records, project_root=PROJECT_ROOT
    )
    manifest = build_run_manifest(
        workflow=WORKFLOW,
        run_records=run_records,
        species_catalog_sha256=species_hash,
        attempt_manifest_sha256=attempt_hash,
        software_versions=versions,
        project_root=PROJECT_ROOT,
        preparation_records=list(prepared_by_key.values()),
        metadata={
            "resume_requested": RESUME,
            "qc_manifest": "docs/methods/pdbqt_quality_review.json",
            "qc_manifest_sha256": sha256_file(QC),
            "mmff_preparation_audit": "docs/methods/mmff_preparation_audit.json",
            "mmff_preparation_audit_sha256": sha256_file(PREPARATION_AUDIT),
            "seed": DEFAULT_SEED,
            "exhaustiveness": DEFAULT_EXHAUSTIVENESS,
            "num_modes": DEFAULT_NUM_MODES,
            "cpu": DEFAULT_CPU,
            "scoring": DEFAULT_SCORING,
            "timeout_seconds": DEFAULT_TIMEOUT_SECONDS,
        },
    )
    manifest["ranking"] = ranked
    manifest["pose_interactions"] = interactions
    manifest["timeout_qc_artifact_path"] = timeout_qc_path.relative_to(
        PROJECT_ROOT
    ).as_posix()
    _atomic_json(RESULT, manifest)
    print(f"Wrote {RESULT.relative_to(PROJECT_ROOT)}")


def main() -> None:
    campaign_id = require_campaign_id()
    calibration = require_suspend_calibration(PROJECT_ROOT)
    if calibration.get("campaign_id") != campaign_id:
        raise InfrastructureError(
            "Suspend calibration campaign_id does not match SPYCEP_CAMPAIGN_ID."
        )
    pose_dir = campaign_output_dir(PROJECT_ROOT, campaign_id, WORKFLOW)
    with campaign_lock(PROJECT_ROOT, campaign_id):
        require_unsealed(PROJECT_ROOT, campaign_id)
        _run_campaign(campaign_id, pose_dir)


if __name__ == "__main__":
    main()

"""Dock only the separately routed gem-diol surrogate states."""
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
    build_run_manifest,
    dock_ligand,
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


VINA = PROJECT_ROOT / "tools" / "vina.exe"
MEEKO = PROJECT_ROOT / ".venv" / "Scripts" / "mk_prepare_ligand.exe"
SPECIES = PROJECT_ROOT / "docs" / "methods" / "species_audit.json"
ATTEMPTS = PROJECT_ROOT / "docs" / "methods" / "attempt_manifest.json"
PREPARATION_AUDIT = PROJECT_ROOT / "docs" / "methods" / "mmff_preparation_audit.json"
CONVERSION = PROJECT_ROOT / "docs" / "methods" / "pdbqt_conversion.json"
QC = PROJECT_ROOT / "docs" / "methods" / "pdbqt_quality_review.json"
POCKETS = PROJECT_ROOT / "docs" / "methods" / "pocket_definition.json"
RESULT = PROJECT_ROOT / "docs" / "methods" / "boron_surrogate_result.json"
POSE_DIR = PROJECT_ROOT / "results" / "docking" / "boron_surrogate_stage2"


def _atomic_json(path: Path, value: dict) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def main() -> None:
    catalog = load_species_catalog(SPECIES)
    attempt_manifest = json.loads(ATTEMPTS.read_text(encoding="utf-8"))
    validate_attempt_manifest(attempt_manifest, catalog)
    species_hash = sha256_file(SPECIES)
    attempt_hash = sha256_file(ATTEMPTS)
    attempts = [
        row for row in attempt_manifest["attempts"] if row["workflow"] == "boron"
    ]

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
        required_pocket_ids={row["pocket_id"] for row in conversion["receptors"]},
    )
    audit = json.loads(PREPARATION_AUDIT.read_text(encoding="utf-8"))
    validate_preparation_audit(
        audit,
        species_catalog_sha256=species_hash,
        attempt_manifest_sha256=attempt_hash,
        expected_state_keys={
            (row["entity_id"], row["state_id"])
            for row in attempt_manifest["attempts"]
        },
    )
    versions = runtime_versions(VINA)

    prepared = {}
    for entity_id, state_id in sorted(
        {(row["entity_id"], row["state_id"]) for row in attempts}
    ):
        state = catalog_state(catalog, entity_id, state_id)
        prepared[(entity_id, state_id)] = prepare_ligand(
            {
                "entity_id": entity_id,
                "state_id": state_id,
                "smiles": state["source_smiles"],
                "role": "gem_diol_surrogate",
                "set": "boron_surrogate",
            },
            project_root=PROJECT_ROOT,
            work_dir=PROJECT_ROOT / "data" / "compounds" / "sdf_stage2",
            output_dir=PROJECT_ROOT / "data" / "compounds" / "pdbqt_stage2",
            meeko_command=[MEEKO],
            species_catalog=catalog,
        )

    active_site = pockets["active_site_residues"]
    records = []
    results = []
    for attempt in attempts:
        ligand = prepared[(attempt["entity_id"], attempt["state_id"])]
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
                output_dir=POSE_DIR,
                workflow="boron",
                species_catalog_sha256=species_hash,
                attempt_manifest_sha256=attempt_hash,
                software_versions=versions,
                seed=DEFAULT_SEED,
                exhaustiveness=DEFAULT_EXHAUSTIVENESS,
                num_modes=DEFAULT_NUM_MODES,
                cpu=DEFAULT_CPU,
                scoring=DEFAULT_SCORING,
                timeout_seconds=DEFAULT_TIMEOUT_SECONDS,
            )
        except DockingError as exc:
            if exc.run_record is None:
                raise
            records.append(exc.run_record)
            continue
        records.append(record)
        interaction = analyze_pose_interactions(
            PROJECT_ROOT / receptor["receptor_pdbqt_path"],
            PROJECT_ROOT / record["out_path"],
            active_site,
        )
        state = catalog_state(catalog, attempt["entity_id"], attempt["state_id"])
        results.append(
            {
                "claim_key": record["claim_key"],
                "entity_id": record["entity_id"],
                "state_id": record["state_id"],
                "species_key": record["species_key"],
                "source_parent_entity_id": state["source_parent_entity_id"],
                "docked_surrogate_smiles": ligand["docked_smiles"],
                "pocket_id": record["pocket_id"],
                "best_affinity_kcal_mol": record["best_affinity_kcal_mol"],
                "ligand_efficiency_kcal_mol_per_heavy_atom": (
                    record["best_affinity_kcal_mol"] / ligand["heavy_atom_count"]
                ),
                "contacted_active_site_residues": interaction[
                    "contacted_active_site_residues"
                ],
            }
        )

    manifest = build_run_manifest(
        workflow="boron",
        run_records=records,
        species_catalog_sha256=species_hash,
        attempt_manifest_sha256=attempt_hash,
        software_versions=versions,
        preparation_records=list(prepared.values()),
        metadata={
            "method": "R-B(OH)2 -> R-CH(OH)2 gem-diol surrogate",
            "surrogates_are_not_substituted_into_primary_screen": True,
            "qc_manifest_sha256": sha256_file(QC),
            "mmff_preparation_audit_sha256": sha256_file(PREPARATION_AUDIT),
            "cpu": DEFAULT_CPU,
            "scoring": DEFAULT_SCORING,
            "timeout_seconds": DEFAULT_TIMEOUT_SECONDS,
        },
    )
    manifest["results"] = results
    _atomic_json(RESULT, manifest)
    print(f"Wrote {RESULT.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()

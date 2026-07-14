"""Run the mandatory preparation-only MMFF94s audit; performs no docking."""
from __future__ import annotations

import importlib.metadata
import json
import os
import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from rdkit import Chem, rdBase

from spycep_drug_discovery.attempt_manifest import validate_attempt_manifest
from spycep_drug_discovery.ligand_preparation import (
    LigandPreparationError,
    MMFF_MAX_ITERATIONS,
    MMFF_VARIANT,
    smiles_to_sdf,
)
from spycep_drug_discovery.preparation_audit import (
    PREPARATION_AUDIT_SCHEMA_VERSION,
    validate_preparation_audit,
)
from spycep_drug_discovery.species import (
    catalog_state,
    load_species_catalog,
    sha256_file,
)


SPECIES_PATH = PROJECT_ROOT / "docs" / "methods" / "species_audit.json"
ATTEMPT_PATH = PROJECT_ROOT / "docs" / "methods" / "attempt_manifest.json"
OUTPUT_PATH = PROJECT_ROOT / "docs" / "methods" / "mmff_preparation_audit.json"
WORK_DIR = PROJECT_ROOT / "data" / "processed" / "mmff_preparation_audit_tmp"


def _distribution_version(name: str) -> str:
    return importlib.metadata.version(name)


def main() -> None:
    catalog = load_species_catalog(SPECIES_PATH)
    attempts = json.loads(ATTEMPT_PATH.read_text(encoding="utf-8"))
    validate_attempt_manifest(attempts, catalog)
    species_hash = sha256_file(SPECIES_PATH)
    attempt_hash = sha256_file(ATTEMPT_PATH)
    keys = sorted(
        {
            (row["entity_id"], row["state_id"])
            for row in attempts["attempts"]
        }
    )

    resolved_work = WORK_DIR.resolve()
    if PROJECT_ROOT.resolve() not in resolved_work.parents:
        raise SystemExit(f"Unsafe preparation-audit work path: {resolved_work}")
    if WORK_DIR.exists():
        shutil.rmtree(WORK_DIR)
    WORK_DIR.mkdir(parents=True)

    rows = []
    failures = []
    try:
        for entity_id, state_id in keys:
            state = catalog_state(catalog, entity_id, state_id)
            state_mol = Chem.MolFromSmiles(state["atom_mapped_canonical_smiles"])
            contains_boron = any(atom.GetAtomicNum() == 5 for atom in state_mol.GetAtoms())
            if contains_boron:
                failures.append(
                    {
                        "entity_id": entity_id,
                        "state_id": state_id,
                        "cause": (
                            "Attempt manifest illegally includes a boron-containing "
                            "state; MMFF94s is expected to be unavailable."
                        ),
                    }
                )
                continue
            try:
                record = smiles_to_sdf(
                    state["source_smiles"],
                    WORK_DIR / f"{entity_id}__{state_id}.sdf",
                    entity_id=entity_id,
                    state_id=state_id,
                    species_catalog=catalog,
                )
            except LigandPreparationError as exc:
                failures.append(
                    {
                        "entity_id": entity_id,
                        "state_id": state_id,
                        "cause": str(exc),
                    }
                )
                continue
            rows.append(
                {
                    "entity_id": entity_id,
                    "state_id": state_id,
                    "state_smiles_sha256": state["state_smiles_sha256"],
                    "mmff_variant": record["mmff_variant"],
                    "mmff_max_iterations": record["mmff_max_iterations"],
                    "mmff_status": record["mmff_status"],
                    "mmff_converged": record["mmff_converged"],
                    "source_undefined_centers": record["source_undefined_centers"],
                    "embedded_unassigned_centers": record["embedded_unassigned_centers"],
                    "embedded_isomeric_smiles": record["embedded_isomeric_smiles"],
                    "embed_seed": record["embed_seed"],
                }
            )
    finally:
        if WORK_DIR.exists():
            shutil.rmtree(WORK_DIR)

    audit = {
        "schema_version": PREPARATION_AUDIT_SCHEMA_VERSION,
        "decision_status": "pass" if not failures and len(rows) == len(keys) else "block",
        "source_species_catalog": "docs/methods/species_audit.json",
        "species_catalog_sha256": species_hash,
        "source_attempt_manifest": "docs/methods/attempt_manifest.json",
        "attempt_manifest_sha256": attempt_hash,
        "audited_unique_state_count": len(keys),
        "mmff_variant": MMFF_VARIANT,
        "mmff_max_iterations": MMFF_MAX_ITERATIONS,
        "embed_seed": 42,
        "versions": {
            "rdkit": rdBase.rdkitVersion,
            "meeko": _distribution_version("meeko"),
        },
        "failure_count": len(failures),
        "failures": failures,
        "states": rows,
    }
    temporary = OUTPUT_PATH.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, OUTPUT_PATH)

    if audit["decision_status"] != "pass":
        raise SystemExit(
            f"MMFF preparation audit BLOCKED: {len(failures)} failure(s); "
            f"see {OUTPUT_PATH.relative_to(PROJECT_ROOT)}"
        )
    validate_preparation_audit(
        audit,
        species_catalog_sha256=species_hash,
        attempt_manifest_sha256=attempt_hash,
        expected_state_keys=set(keys),
    )
    print(
        f"MMFF preparation audit PASS: {len(rows)} unique states, "
        f"{MMFF_VARIANT}, cap {MMFF_MAX_ITERATIONS}"
    )
    print(f"Wrote {OUTPUT_PATH.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()

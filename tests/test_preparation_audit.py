import copy
import json
from pathlib import Path

import pytest

from spycep_drug_discovery.preparation_audit import (
    PreparationAuditError,
    validate_preparation_audit,
)
from spycep_drug_discovery.species import sha256_file


def _inputs():
    audit = json.loads(
        open("docs/methods/mmff_preparation_audit.json", encoding="utf-8").read()
    )
    attempts = json.loads(
        open("docs/methods/attempt_manifest.json", encoding="utf-8").read()
    )
    keys = {
        (row["entity_id"], row["state_id"])
        for row in attempts["attempts"]
    }
    return audit, keys


def test_tracked_mmff_preparation_audit_passes_for_every_attempted_state():
    audit, keys = _inputs()

    validate_preparation_audit(
        audit,
        species_catalog_sha256=sha256_file(Path("docs/methods/species_audit.json")),
        attempt_manifest_sha256=sha256_file(Path("docs/methods/attempt_manifest.json")),
        expected_state_keys=keys,
    )

    assert audit["decision_status"] == "pass"
    assert audit["audited_unique_state_count"] == len(keys) == 82
    assert audit["failure_count"] == 0
    assert audit["failures"] == []
    assert all(row["mmff_converged"] is True for row in audit["states"])
    assert all(row["mmff_status"] == 0 for row in audit["states"])
    assert all(row["embedded_unassigned_centers"] == [] for row in audit["states"])


def test_mmff_audit_blocks_on_stale_attempt_hash():
    audit, keys = _inputs()

    with pytest.raises(PreparationAuditError, match="attempt-manifest hash is stale"):
        validate_preparation_audit(
            audit,
            species_catalog_sha256=audit["species_catalog_sha256"],
            attempt_manifest_sha256="0" * 64,
            expected_state_keys=keys,
        )


def test_mmff_audit_blocks_on_nonconvergence():
    audit, keys = _inputs()
    broken = copy.deepcopy(audit)
    broken["states"][0]["mmff_converged"] = False
    broken["states"][0]["mmff_status"] = 1

    with pytest.raises(PreparationAuditError, match="non-converged"):
        validate_preparation_audit(
            broken,
            species_catalog_sha256=broken["species_catalog_sha256"],
            attempt_manifest_sha256=broken["attempt_manifest_sha256"],
            expected_state_keys=keys,
        )

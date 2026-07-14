"""Content-addressed MMFF94s preparation audit."""
from __future__ import annotations

from typing import Any, Mapping

from spycep_drug_discovery.ligand_preparation import (
    MMFF_MAX_ITERATIONS,
    MMFF_VARIANT,
)


PREPARATION_AUDIT_SCHEMA_VERSION = "mmff-preparation-audit-v1"


class PreparationAuditError(RuntimeError):
    """Raised when the preparation gate is absent, stale, or blocked."""


def validate_preparation_audit(
    audit: Mapping[str, Any],
    *,
    species_catalog_sha256: str,
    attempt_manifest_sha256: str,
    expected_state_keys: set[tuple[str, str]],
) -> None:
    if audit.get("schema_version") != PREPARATION_AUDIT_SCHEMA_VERSION:
        raise PreparationAuditError("Unsupported MMFF preparation-audit schema.")
    if audit.get("decision_status") != "pass":
        raise PreparationAuditError(
            f"MMFF preparation gate is {audit.get('decision_status')!r}; docking is blocked."
        )
    if audit.get("species_catalog_sha256") != species_catalog_sha256:
        raise PreparationAuditError("MMFF audit species-catalog hash is stale.")
    if audit.get("attempt_manifest_sha256") != attempt_manifest_sha256:
        raise PreparationAuditError("MMFF audit attempt-manifest hash is stale.")
    if audit.get("mmff_variant") != MMFF_VARIANT:
        raise PreparationAuditError("MMFF audit did not use frozen MMFF94s.")
    if audit.get("mmff_max_iterations") != MMFF_MAX_ITERATIONS:
        raise PreparationAuditError("MMFF audit did not use the frozen 2000-iteration cap.")

    rows = list(audit.get("states", ()))
    keys = {(str(row.get("entity_id")), str(row.get("state_id"))) for row in rows}
    if len(keys) != len(rows):
        raise PreparationAuditError("MMFF audit contains duplicate species keys.")
    if keys != expected_state_keys:
        raise PreparationAuditError(
            "MMFF audit state projection does not match the attempt manifest."
        )
    for row in rows:
        if row.get("mmff_converged") is not True or row.get("mmff_status") != 0:
            raise PreparationAuditError(
                f"MMFF audit contains a non-converged state: "
                f"({row.get('entity_id')}, {row.get('state_id')})."
            )
        if row.get("embedded_unassigned_centers") != []:
            raise PreparationAuditError(
                f"Embedded stereochemistry remains unassigned for "
                f"({row.get('entity_id')}, {row.get('state_id')})."
            )

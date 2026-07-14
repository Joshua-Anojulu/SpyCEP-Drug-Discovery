"""Workflow-eligibility relation for Stage 1 docking attempts."""
from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any, Mapping, Sequence


ATTEMPT_MANIFEST_SCHEMA_VERSION = "attempt-manifest-v1"

# Frozen from the preregistered 20-member SpeB panel: Q9D, 17 true decoys and two
# explicitly labelled protease comparators.
SPEB_PANEL_ROLES = {
    "Q9D_speb_inhibitor": "positive_known_inhibitor",
    "amlodipine": "decoy",
    "amoxicillin": "decoy",
    "ampicillin": "decoy",
    "cephalexin": "decoy",
    "celecoxib": "decoy",
    "ciprofloxacin": "decoy",
    "clindamycin": "decoy",
    "dexamethasone": "decoy",
    "fluconazole": "decoy",
    "fluoxetine": "decoy",
    "levofloxacin": "decoy",
    "linezolid": "decoy",
    "loratadine": "decoy",
    "omeprazole": "decoy",
    "penicillin_g": "decoy",
    "prednisone": "decoy",
    "warfarin": "decoy",
    "gabexate": "protease_inhibitor_comparator",
    "nafamostat": "protease_inhibitor_comparator",
}


class AttemptManifestError(RuntimeError):
    """Raised when workflow eligibility is incomplete or contradictory."""


def build_attempt_manifest(
    species_catalog: Mapping[str, Any],
    *,
    species_catalog_sha256: str,
    wide_receptors: Sequence[Mapping[str, Any]],
    tight_receptors: Sequence[Mapping[str, Any]],
    speb_receptor: Mapping[str, Any],
) -> dict[str, Any]:
    states = list(species_catalog["states"])
    attempts: list[dict[str, Any]] = []

    for state in states:
        if not state["dock_eligible"]:
            continue
        kind = state["entity_kind"]
        if kind == "library_parent":
            for workflow, receptors in (("wide", wide_receptors), ("tight", tight_receptors)):
                for receptor in receptors:
                    attempts.append(
                        _attempt_row(
                            state,
                            workflow=workflow,
                            receptor=receptor,
                            role=state.get("set"),
                        )
                    )
            if state["entity_id"] in SPEB_PANEL_ROLES:
                attempts.append(
                    _attempt_row(
                        state,
                        workflow="speb",
                        receptor=speb_receptor,
                        role=SPEB_PANEL_ROLES[state["entity_id"]],
                    )
                )
        elif kind == "speb_positive_control":
            if state["entity_id"] not in SPEB_PANEL_ROLES:
                raise AttemptManifestError(
                    f"SpeB entity {state['entity_id']!r} is absent from the frozen panel."
                )
            attempts.append(
                _attempt_row(
                    state,
                    workflow="speb",
                    receptor=speb_receptor,
                    role=SPEB_PANEL_ROLES[state["entity_id"]],
                )
            )
        elif kind == "gem_diol_surrogate":
            for receptor in tight_receptors:
                attempts.append(
                    _attempt_row(
                        state,
                        workflow="boron",
                        receptor=receptor,
                        role="gem_diol_surrogate",
                    )
                )
        else:
            raise AttemptManifestError(
                f"Eligible entity {state['entity_id']!r} has no legal workflow route."
            )

    attempts.sort(
        key=lambda row: (
            row["workflow"],
            row["entity_id"],
            row["state_id"],
            row["pocket_id"],
        )
    )
    manifest = {
        "schema_version": ATTEMPT_MANIFEST_SCHEMA_VERSION,
        "relation": "one row per legal workflow invocation; never a Cartesian product",
        "species_catalog": "docs/methods/species_audit.json",
        "species_catalog_sha256": species_catalog_sha256,
        "attempt_count": len(attempts),
        "counts_by_workflow": dict(sorted(Counter(row["workflow"] for row in attempts).items())),
        "speb_panel": {
            "entity_count": len(SPEB_PANEL_ROLES),
            "role_counts": dict(sorted(Counter(SPEB_PANEL_ROLES.values()).items())),
            "roles": dict(sorted(SPEB_PANEL_ROLES.items())),
        },
        "attempts": attempts,
    }
    validate_attempt_manifest(manifest, species_catalog)
    return manifest


def validate_attempt_manifest(
    manifest: Mapping[str, Any],
    species_catalog: Mapping[str, Any],
) -> None:
    if manifest.get("schema_version") != ATTEMPT_MANIFEST_SCHEMA_VERSION:
        raise AttemptManifestError(
            f"Unsupported attempt-manifest schema: {manifest.get('schema_version')!r}"
        )
    catalog_states = {
        (str(row["entity_id"]), str(row["state_id"])): row
        for row in species_catalog["states"]
    }
    attempts = list(manifest.get("attempts", ()))
    if int(manifest.get("attempt_count", -1)) != len(attempts):
        raise AttemptManifestError("attempt_count is not derived from the relation.")

    ids = [str(row.get("attempt_id")) for row in attempts]
    if len(ids) != len(set(ids)):
        raise AttemptManifestError("Attempt IDs are not unique.")

    observed: set[tuple[str, str, str, str]] = set()
    for row in attempts:
        key = (str(row["entity_id"]), str(row["state_id"]))
        if key not in catalog_states:
            raise AttemptManifestError(f"Attempt references unknown species state {key}.")
        state = catalog_states[key]
        if not state["dock_eligible"]:
            raise AttemptManifestError(f"Attempt routes excluded species state {key}.")
        if row.get("state_smiles_sha256") != state["state_smiles_sha256"]:
            raise AttemptManifestError(f"Attempt species hash mismatch for {key}.")
        relation_key = (*key, str(row["workflow"]), str(row["pocket_id"]))
        if relation_key in observed:
            raise AttemptManifestError(f"Duplicate legal invocation {relation_key}.")
        observed.add(relation_key)

    eligible_entities = {
        str(row["entity_id"]) for row in species_catalog["states"] if row["dock_eligible"]
    }
    attempted_entities = {str(row["entity_id"]) for row in attempts}
    if attempted_entities != eligible_entities:
        raise AttemptManifestError(
            "Attempted entity projection must derive exactly from dock_eligible: "
            f"missing={sorted(eligible_entities - attempted_entities)}, "
            f"extra={sorted(attempted_entities - eligible_entities)}"
        )

    by_state: dict[tuple[str, str], list[Mapping[str, Any]]] = defaultdict(list)
    for row in attempts:
        by_state[(str(row["entity_id"]), str(row["state_id"]))].append(row)
    for key, state in catalog_states.items():
        rows = by_state.get(key, [])
        if not state["dock_eligible"]:
            if rows:
                raise AttemptManifestError(f"Excluded state {key} was routed.")
            continue
        workflows = Counter(str(row["workflow"]) for row in rows)
        kind = state["entity_kind"]
        if kind == "library_parent":
            expected = {"wide": 2, "tight": 2}
            if state["entity_id"] in SPEB_PANEL_ROLES:
                expected["speb"] = 1
        elif kind == "speb_positive_control":
            expected = {"speb": 1}
        elif kind == "gem_diol_surrogate":
            expected = {"boron": 2}
        else:
            raise AttemptManifestError(f"Eligible state {key} has unsupported kind {kind!r}.")
        if dict(workflows) != expected:
            raise AttemptManifestError(
                f"Workflow relation mismatch for {key}: expected {expected}, "
                f"observed {dict(workflows)}."
            )

    workflow_counts = dict(sorted(Counter(row["workflow"] for row in attempts).items()))
    if dict(manifest.get("counts_by_workflow", {})) != workflow_counts:
        raise AttemptManifestError("counts_by_workflow is not derived from the relation.")

    speb = [row for row in attempts if row["workflow"] == "speb"]
    speb_entities = {row["entity_id"] for row in speb}
    if speb_entities != set(SPEB_PANEL_ROLES):
        raise AttemptManifestError("SpeB attempts do not cover the frozen 20-entity panel.")
    for row in speb:
        if row["role"] != SPEB_PANEL_ROLES[row["entity_id"]]:
            raise AttemptManifestError(f"SpeB role mismatch for {row['entity_id']}.")


def _attempt_row(
    state: Mapping[str, Any],
    *,
    workflow: str,
    receptor: Mapping[str, Any],
    role: str | None,
) -> dict[str, Any]:
    entity_id = str(state["entity_id"])
    state_id = str(state["state_id"])
    pocket_id = str(receptor["pocket_id"])
    return {
        "attempt_id": f"{workflow}__{entity_id}__{state_id}__{pocket_id}",
        "workflow": workflow,
        "entity_id": entity_id,
        "state_id": state_id,
        "role": role,
        "pdb_id": receptor["pdb_id"],
        "pocket_id": pocket_id,
        "receptor_pdbqt_path": receptor["receptor_pdbqt_path"],
        "box_center_angstrom": receptor["box_center_angstrom"],
        "box_size_angstrom": receptor["box_size_angstrom"],
        "state_smiles_sha256": state["state_smiles_sha256"],
        "net_formal_charge": state["net_formal_charge"],
    }

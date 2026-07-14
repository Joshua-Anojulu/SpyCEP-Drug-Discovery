import copy
import json
from collections import Counter

import pytest
from pathlib import Path

from spycep_drug_discovery.species import sha256_file

from spycep_drug_discovery.attempt_manifest import (
    AttemptManifestError,
    SPEB_PANEL_ROLES,
    validate_attempt_manifest,
)


def _artifacts():
    catalog = json.loads(open("docs/methods/species_audit.json", encoding="utf-8").read())
    attempts = json.loads(open("docs/methods/attempt_manifest.json", encoding="utf-8").read())
    return catalog, attempts


def test_tracked_attempt_manifest_is_the_derived_eligibility_relation():
    catalog, manifest = _artifacts()
    validate_attempt_manifest(manifest, catalog)

    # 339, not 335: lisinopril became AMBIGUOUS, adding one state x (wide+tight) x 2 receptors.
    assert manifest["attempt_count"] == len(manifest["attempts"]) == 339
    assert manifest["counts_by_workflow"] == {
        "boron": 8,
        "speb": 23,
        "tight": 154,
        "wide": 154,
    }
    assert Counter(row["workflow"] for row in manifest["attempts"]) == manifest["counts_by_workflow"]
    assert manifest["species_catalog_sha256"] == sha256_file(Path("docs/methods/species_audit.json"))


def test_attempts_route_all_states_only_to_legal_workflows():
    catalog, manifest = _artifacts()
    rows = manifest["attempts"]
    surrogate_entities = {
        row["entity_id"]
        for row in catalog["states"]
        if row["entity_kind"] == "gem_diol_surrogate"
    }
    boron_parents = set(catalog["source_to_surrogate"])

    assert not any(
        row["entity_id"] in surrogate_entities and row["workflow"] in {"wide", "tight", "speb"}
        for row in rows
    )
    assert not any(row["entity_id"] in boron_parents for row in rows)
    assert {
        row["entity_id"] for row in rows if row["workflow"] == "boron"
    } == surrogate_entities
    assert {
        row["entity_id"] for row in rows if row["workflow"] == "speb"
    } == set(SPEB_PANEL_ROLES)


def test_all_ambiguous_states_are_routed_without_filename_key_collisions():
    catalog, manifest = _artifacts()
    ambiguous_keys = {
        (row["entity_id"], row["state_id"])
        for row in catalog["states"]
        if row["tier"] == "AMBIGUOUS"
    }

    for key in ambiguous_keys:
        entity_id, state_id = key
        attempts = [
            row
            for row in manifest["attempts"]
            if (row["entity_id"], row["state_id"]) == key
        ]
        expected = 5 if entity_id in SPEB_PANEL_ROLES else 4
        assert len(attempts) == expected
        assert all(entity_id in row["attempt_id"] and state_id in row["attempt_id"] for row in attempts)


def test_attempt_manifest_rejects_catalog_contradiction():
    catalog, manifest = _artifacts()
    broken = copy.deepcopy(manifest)
    broken["attempts"][0]["entity_id"] = "phenylboronic_acid"

    with pytest.raises(AttemptManifestError):
        validate_attempt_manifest(broken, catalog)


def test_speb_panel_roles_are_frozen_at_17_decoys_and_two_comparators():
    _, manifest = _artifacts()

    assert manifest["speb_panel"]["entity_count"] == 20
    assert manifest["speb_panel"]["role_counts"] == {
        "decoy": 17,
        "positive_known_inhibitor": 1,
        "protease_inhibitor_comparator": 2,
    }

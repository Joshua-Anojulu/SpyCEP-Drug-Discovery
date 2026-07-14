import copy
import json
from collections import Counter

import pytest

from spycep_drug_discovery.species import (
    SpeciesCatalogError,
    load_species_catalog,
    validate_species_catalog,
)


CATALOG_PATH = "docs/methods/species_audit.json"
LIBRARY_PATH = "docs/methods/compound_library_source.json"


def _catalog():
    library = json.loads(open(LIBRARY_PATH, encoding="utf-8").read())["compounds"]
    return load_species_catalog(
        __import__("pathlib").Path(CATALOG_PATH),
        library_entity_ids=(row["ligand_id"] for row in library),
    )


def test_tracked_species_catalog_covers_every_considered_entity():
    catalog = _catalog()
    rows = catalog["states"]
    entities = {row["entity_id"] for row in rows}
    library_entities = {
        row["ligand_id"]
        for row in json.loads(open(LIBRARY_PATH, encoding="utf-8").read())["compounds"]
    }

    assert catalog["entity_count"] == 82
    assert catalog["state_count"] == 86
    assert {row["entity_id"] for row in rows if row["entity_kind"] == "library_parent"} == library_entities
    assert "Q9D_speb_inhibitor" in entities
    assert len({row["entity_id"] for row in rows if row["entity_kind"] == "gem_diol_surrogate"}) == 4


def test_species_tier_cardinalities_and_ambiguous_audit_trail_are_exact():
    catalog = _catalog()
    by_entity = {}
    for row in catalog["states"]:
        by_entity.setdefault(row["entity_id"], []).append(row)

    ambiguous = {entity for entity, rows in by_entity.items() if rows[0]["tier"] == "AMBIGUOUS"}
    # lisinopril joins the beta-lactams: its secondary amine (logK2 = 7.13) leaves a 35%
    # neutral double-zwitterion at pH 7.4 — too large a minor species to assert away.
    assert ambiguous == {"ampicillin", "amoxicillin", "cephalexin", "lisinopril"}
    assert all(len(rows) == (2 if rows[0]["tier"] == "AMBIGUOUS" else 1) for rows in by_entity.values())
    for entity_id in ambiguous:
        for row in by_entity[entity_id]:
            review = row["review"]
            assert review["reviewer"]
            assert review["citations"]
            assert review["classification_rationale"]
            assert review["review_date"] == "2026-07-13"
            assert review["more_than_two_plausible_states_considered"]["answer"] is False
            assert review["more_than_two_plausible_states_considered"]["rationale"]


def test_boronic_acid_parents_are_excluded_and_mapped_to_separate_surrogates():
    catalog = _catalog()
    by_entity = {}
    for row in catalog["states"]:
        by_entity.setdefault(row["entity_id"], []).append(row)
    expected_parents = {
        "phenylboronic_acid",
        "4_carboxyphenylboronic_acid",
        "bortezomib",
        "ixazomib",
    }

    assert set(catalog["source_to_surrogate"]) == expected_parents
    for parent, surrogate in catalog["source_to_surrogate"].items():
        assert by_entity[parent][0]["dock_eligible"] is False
        assert "MMFF94s" in by_entity[parent][0]["exclusion_reason"]
        assert by_entity[parent][0]["surrogate_entity_id"] == surrogate
        assert by_entity[surrogate][0]["dock_eligible"] is True
        assert by_entity[surrogate][0]["source_parent_entity_id"] == parent


def test_catalog_contains_no_abundance_or_threshold_fields():
    forbidden = {
        "fraction",
        "abundance",
        "probability",
        "population",
        "sum_to_one",
        "dominance_threshold",
        "inclusion_threshold",
    }

    def keys(value):
        if isinstance(value, dict):
            yield from value
            for key, child in value.items():
                yield key.lower()
                yield from keys(child)
        elif isinstance(value, list):
            for child in value:
                yield from keys(child)

    assert forbidden.isdisjoint(set(keys(_catalog())))


def test_single_state_tiers_fail_on_rule_output_mismatch():
    catalog = copy.deepcopy(_catalog())
    row = next(row for row in catalog["states"] if row["entity_id"] == "benzamidine")
    # Keep the mapped state internally valid, but swap the source used by regeneration.
    row["source_smiles"] = "CC"

    with pytest.raises(SpeciesCatalogError, match="rule-output mismatch"):
        validate_species_catalog(catalog)


def test_ambiguous_states_are_validated_without_consulting_generic_rule(monkeypatch):
    catalog = copy.deepcopy(_catalog())
    catalog["states"] = [
        row for row in catalog["states"] if row["entity_id"] == "amoxicillin"
    ]
    catalog["entity_count"] = 1
    catalog["state_count"] = 2
    catalog["tier_counts_by_entity"] = {"AMBIGUOUS": 1}
    catalog["source_to_surrogate"] = {}

    def forbidden_rule_call(_source):
        raise AssertionError("generic rule must not be called for AMBIGUOUS states")

    monkeypatch.setattr("spycep_drug_discovery.species._rule_output", forbidden_rule_call)
    validate_species_catalog(catalog)


def test_more_than_two_states_abort_as_indeterminate_chemistry():
    catalog = copy.deepcopy(_catalog())
    amoxicillin = [
        row for row in catalog["states"] if row["entity_id"] == "amoxicillin"
    ]
    third = copy.deepcopy(amoxicillin[0])
    third["state_id"] = "forbidden_third_state"
    catalog["states"].append(third)

    with pytest.raises(SpeciesCatalogError, match="INDETERMINATE_CHEMISTRY"):
        validate_species_catalog(catalog)

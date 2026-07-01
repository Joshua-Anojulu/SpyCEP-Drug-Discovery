from pathlib import Path

import pytest

from spycep_drug_discovery.targets import TargetRegistryError, load_target_registry


REGISTRY_PATH = Path("docs/methods/target_registry.json")


def test_registry_contains_approved_primary_and_fallback_targets():
    registry = load_target_registry(REGISTRY_PATH)

    assert registry.primary.uniprot_accession == "Q3HV58"
    assert registry.primary.gene_name == "scpC"
    assert registry.primary.decision_role == "primary"
    assert registry.fallback.uniprot_accession == "P0C0J0"
    assert registry.fallback.gene_name == "speB"
    assert registry.fallback.decision_role == "fallback"


def test_registry_tracks_spycep_candidate_structures():
    registry = load_target_registry(REGISTRY_PATH)
    pdb_ids = {structure.pdb_id for structure in registry.primary.structures}

    assert {"5XXZ", "5XYA", "5XYR", "7EDD"}.issubset(pdb_ids)


def test_registry_rejects_missing_primary_target(tmp_path):
    broken = tmp_path / "broken_registry.json"
    broken.write_text('{"targets": []}', encoding="utf-8")

    with pytest.raises(TargetRegistryError, match="exactly one primary"):
        load_target_registry(broken)

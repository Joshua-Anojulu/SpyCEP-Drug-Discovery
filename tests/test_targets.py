import json
from pathlib import Path

import pytest

from spycep_drug_discovery.targets import TargetRegistryError, load_target_registry


REGISTRY_PATH = Path("docs/methods/target_registry.json")


def _registry_text(*targets: dict) -> str:
    return json.dumps({"targets": list(targets)})


def _target(
    target_id: str,
    decision_role: str,
    *,
    pdb_id: str = "7EDD",
    source: str = "RCSB",
    pmid: str = "18692776",
    note: str = "reference",
) -> dict:
    return {
        "target_id": target_id,
        "decision_role": decision_role,
        "protein_name": "Protein",
        "gene_name": "gene",
        "organism": "Streptococcus pyogenes",
        "uniprot_accession": "Q3HV58",
        "rationale": "Target rationale",
        "key_references": [{"pmid": pmid, "note": note}],
        "structures": [{"pdb_id": pdb_id, "source": source, "selection_note": "candidate"}],
    }


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


def test_registry_rejects_duplicate_pdb_ids(tmp_path):
    broken = tmp_path / "broken_registry.json"
    primary = _target("primary", "primary")
    primary["structures"].append({"pdb_id": "7EDD", "source": "RCSB", "selection_note": "duplicate"})
    broken.write_text(_registry_text(primary, _target("fallback", "fallback", pdb_id="6UKD")), encoding="utf-8")

    with pytest.raises(TargetRegistryError, match="Duplicate PDB ID"):
        load_target_registry(broken)


def test_registry_rejects_unknown_roles(tmp_path):
    broken = tmp_path / "broken_registry.json"
    broken.write_text(
        _registry_text(
            _target("primary", "primary"),
            _target("fallback", "fallback", pdb_id="6UKD"),
            _target("benchmark", "benchmark", pdb_id="1ABC"),
        ),
        encoding="utf-8",
    )

    with pytest.raises(TargetRegistryError, match="Unknown decision role"):
        load_target_registry(broken)


def test_registry_rejects_empty_target_ids(tmp_path):
    broken = tmp_path / "broken_registry.json"
    broken.write_text(
        _registry_text(_target("", "primary"), _target("fallback", "fallback", pdb_id="6UKD")),
        encoding="utf-8",
    )

    with pytest.raises(TargetRegistryError, match="target_id"):
        load_target_registry(broken)


def test_registry_rejects_bad_references(tmp_path):
    broken = tmp_path / "broken_registry.json"
    broken.write_text(
        _registry_text(
            _target("primary", "primary", pmid="PMID:abc", note=""),
            _target("fallback", "fallback", pdb_id="6UKD"),
        ),
        encoding="utf-8",
    )

    with pytest.raises(TargetRegistryError, match="reference"):
        load_target_registry(broken)


def test_registry_rejects_missing_structure_sources(tmp_path):
    broken = tmp_path / "broken_registry.json"
    broken.write_text(
        _registry_text(
            _target("primary", "primary", pdb_id="", source=""),
            _target("fallback", "fallback", pdb_id="6UKD"),
        ),
        encoding="utf-8",
    )

    with pytest.raises(TargetRegistryError, match="structure"):
        load_target_registry(broken)

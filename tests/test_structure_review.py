import json
from pathlib import Path

import pytest

from spycep_drug_discovery.structure_review import (
    StructureReviewError,
    load_structure_review_registry,
)
from spycep_drug_discovery.targets import load_target_registry


def _review_row(pdb_id: str = "7EDD", docking_readiness: str = "pending") -> dict[str, str]:
    return {
        "target_id": "spycep_scpC",
        "pdb_id": pdb_id,
        "chain_coverage": "pending manual review",
        "missing_regions": "pending manual review",
        "catalytic_region_status": "pending",
        "pocket_definition_status": "pending",
        "docking_readiness": docking_readiness,
        "review_notes": "Manual pocket/catalytic-site review has not been completed.",
    }


def _write_review(path: Path, *rows: dict[str, str]) -> None:
    path.write_text(json.dumps({"review_version": "2026-07-01", "structures": list(rows)}), encoding="utf-8")


def test_load_structure_review_registry_reads_pending_review(tmp_path):
    review_path = tmp_path / "structure_review.json"
    _write_review(review_path, _review_row())

    registry = load_structure_review_registry(review_path)
    review = registry.for_pdb_id("7edd")

    assert review.pdb_id == "7EDD"
    assert review.docking_readiness == "pending"
    assert review.pocket_definition_status == "pending"


def test_structure_review_registry_rejects_duplicate_pdb_ids(tmp_path):
    review_path = tmp_path / "structure_review.json"
    _write_review(review_path, _review_row("7EDD"), _review_row("7edd"))

    with pytest.raises(StructureReviewError, match="Duplicate PDB ID"):
        load_structure_review_registry(review_path)


def test_structure_review_registry_rejects_invalid_readiness(tmp_path):
    review_path = tmp_path / "structure_review.json"
    _write_review(review_path, _review_row(docking_readiness="maybe"))

    with pytest.raises(StructureReviewError, match="docking_readiness"):
        load_structure_review_registry(review_path)


def test_structure_review_registry_requires_registered_pdb_id(tmp_path):
    review_path = tmp_path / "structure_review.json"
    _write_review(review_path, _review_row("7EDD"))
    registry = load_structure_review_registry(review_path)

    with pytest.raises(StructureReviewError, match="5XXZ"):
        registry.for_pdb_id("5XXZ")


def test_tracked_structure_reviews_cover_registered_structures():
    targets = load_target_registry(Path("docs/methods/target_registry.json"))
    reviews = load_structure_review_registry(Path("docs/methods/structure_review.json"))

    for target in targets.targets:
        for structure in target.structures:
            review = reviews.for_pdb_id(structure.pdb_id)
            assert review.target_id == target.target_id


def test_tracked_primary_structure_reviews_record_receptor_decision():
    targets = load_target_registry(Path("docs/methods/target_registry.json"))
    reviews = load_structure_review_registry(Path("docs/methods/structure_review.json"))

    for structure in targets.primary.structures:
        review = reviews.for_pdb_id(structure.pdb_id)

        assert review.catalytic_region_status != "pending"
        assert "pending manual review" not in review.chain_coverage
        assert "pending manual review" not in review.missing_regions

    assert reviews.for_pdb_id("5XXZ").pocket_definition_status == "rejected"
    assert reviews.for_pdb_id("5XXZ").docking_readiness == "rejected"
    assert reviews.for_pdb_id("5XYA").pocket_definition_status == "approved"
    assert reviews.for_pdb_id("5XYA").docking_readiness == "approved"
    assert reviews.for_pdb_id("5XYR").pocket_definition_status == "unclear"
    assert reviews.for_pdb_id("5XYR").docking_readiness == "pending"
    assert reviews.for_pdb_id("7EDD").pocket_definition_status == "approved"
    assert reviews.for_pdb_id("7EDD").docking_readiness == "approved"

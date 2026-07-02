from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DOCKING_READINESS_VALUES = frozenset({"pending", "approved", "rejected"})
POCKET_STATUS_VALUES = frozenset({"pending", "approved", "rejected", "unclear"})
CATALYTIC_STATUS_VALUES = frozenset({"pending", "present", "absent", "unclear"})


class StructureReviewError(ValueError):
    """Raised when manual structure-review evidence is incomplete or invalid."""


@dataclass(frozen=True)
class StructureReview:
    target_id: str
    pdb_id: str
    chain_coverage: str
    missing_regions: str
    catalytic_region_status: str
    pocket_definition_status: str
    docking_readiness: str
    review_notes: str


@dataclass(frozen=True)
class StructureReviewRegistry:
    review_version: str
    structures: tuple[StructureReview, ...]

    def for_pdb_id(self, pdb_id: str) -> StructureReview:
        normalized = pdb_id.upper()
        matches = [review for review in self.structures if review.pdb_id == normalized]
        if len(matches) != 1:
            raise StructureReviewError(f"Structure review must contain exactly one row for PDB ID {normalized}.")
        return matches[0]


def load_structure_review_registry(path: Path) -> StructureReviewRegistry:
    raw = json.loads(path.read_text(encoding="utf-8"))
    registry = StructureReviewRegistry(
        review_version=_required_text(raw, "review_version", "Structure review registry"),
        structures=tuple(_review_from_dict(item) for item in raw.get("structures", [])),
    )
    _validate_registry(registry)
    return registry


def _review_from_dict(raw: dict[str, Any]) -> StructureReview:
    pdb_id = _required_text(raw, "pdb_id", "structure review row").upper()
    return StructureReview(
        target_id=_required_text(raw, "target_id", f"structure review row {pdb_id}"),
        pdb_id=pdb_id,
        chain_coverage=_required_text(raw, "chain_coverage", f"structure review row {pdb_id}"),
        missing_regions=_required_text(raw, "missing_regions", f"structure review row {pdb_id}"),
        catalytic_region_status=_required_text(raw, "catalytic_region_status", f"structure review row {pdb_id}"),
        pocket_definition_status=_required_text(raw, "pocket_definition_status", f"structure review row {pdb_id}"),
        docking_readiness=_required_text(raw, "docking_readiness", f"structure review row {pdb_id}"),
        review_notes=_required_text(raw, "review_notes", f"structure review row {pdb_id}"),
    )


def _required_text(raw: dict[str, Any], field_name: str, context: str) -> str:
    value = raw.get(field_name, "")
    if not isinstance(value, str) or not value.strip():
        raise StructureReviewError(f"{context} must define non-empty {field_name}.")
    return value.strip()


def _validate_registry(registry: StructureReviewRegistry) -> None:
    seen_pdb_ids: set[str] = set()
    for review in registry.structures:
        if review.pdb_id in seen_pdb_ids:
            raise StructureReviewError(f"Duplicate PDB ID in structure review registry: {review.pdb_id}")
        seen_pdb_ids.add(review.pdb_id)
        if review.docking_readiness not in DOCKING_READINESS_VALUES:
            raise StructureReviewError(f"Invalid docking_readiness for {review.pdb_id}: {review.docking_readiness}")
        if review.pocket_definition_status not in POCKET_STATUS_VALUES:
            raise StructureReviewError(
                f"Invalid pocket_definition_status for {review.pdb_id}: {review.pocket_definition_status}"
            )
        if review.catalytic_region_status not in CATALYTIC_STATUS_VALUES:
            raise StructureReviewError(
                f"Invalid catalytic_region_status for {review.pdb_id}: {review.catalytic_region_status}"
            )

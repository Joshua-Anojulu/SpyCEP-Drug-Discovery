from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ALLOWED_DECISION_ROLES = frozenset({"primary", "fallback"})


class TargetRegistryError(ValueError):
    """Raised when the target registry is missing required scientific decisions."""


@dataclass(frozen=True)
class Reference:
    pmid: str
    note: str


@dataclass(frozen=True)
class StructureCandidate:
    pdb_id: str
    source: str
    selection_note: str


@dataclass(frozen=True)
class Target:
    target_id: str
    decision_role: str
    protein_name: str
    gene_name: str
    organism: str
    uniprot_accession: str
    rationale: str
    key_references: tuple[Reference, ...]
    structures: tuple[StructureCandidate, ...]


@dataclass(frozen=True)
class TargetRegistry:
    project: str
    registry_version: str
    targets: tuple[Target, ...]

    @property
    def primary(self) -> Target:
        return _single_target_by_role(self.targets, "primary")

    @property
    def fallback(self) -> Target:
        return _single_target_by_role(self.targets, "fallback")


def load_target_registry(path: Path) -> TargetRegistry:
    raw = json.loads(path.read_text(encoding="utf-8"))
    targets = tuple(_target_from_dict(item) for item in raw.get("targets", []))
    registry = TargetRegistry(
        project=str(raw.get("project", "")),
        registry_version=str(raw.get("registry_version", "")),
        targets=targets,
    )
    _validate_registry(registry)
    return registry


def _target_from_dict(raw: dict[str, Any]) -> Target:
    target_id = _required_text(raw, "target_id", "Target")
    references = tuple(_reference_from_dict(item, target_id) for item in raw.get("key_references", []))
    structures = tuple(_structure_from_dict(item, target_id) for item in raw.get("structures", []))
    return Target(
        target_id=target_id,
        decision_role=_required_text(raw, "decision_role", f"Target {target_id}"),
        protein_name=_required_text(raw, "protein_name", f"Target {target_id}"),
        gene_name=_required_text(raw, "gene_name", f"Target {target_id}"),
        organism=_required_text(raw, "organism", f"Target {target_id}"),
        uniprot_accession=_required_text(raw, "uniprot_accession", f"Target {target_id}"),
        rationale=_required_text(raw, "rationale", f"Target {target_id}"),
        key_references=references,
        structures=structures,
    )


def _reference_from_dict(raw: dict[str, Any], target_id: str) -> Reference:
    return Reference(
        pmid=_required_text(raw, "pmid", f"reference for target {target_id}"),
        note=_required_text(raw, "note", f"reference for target {target_id}"),
    )


def _structure_from_dict(raw: dict[str, Any], target_id: str) -> StructureCandidate:
    return StructureCandidate(
        pdb_id=_required_text(raw, "pdb_id", f"structure for target {target_id}").upper(),
        source=_required_text(raw, "source", f"structure for target {target_id}"),
        selection_note=_required_text(raw, "selection_note", f"structure for target {target_id}"),
    )


def _required_text(raw: dict[str, Any], field_name: str, context: str) -> str:
    value = raw.get(field_name, "")
    if not isinstance(value, str) or not value.strip():
        raise TargetRegistryError(f"{context} must define non-empty {field_name}.")
    return value.strip()


def _single_target_by_role(targets: tuple[Target, ...], role: str) -> Target:
    matches = [target for target in targets if target.decision_role == role]
    if len(matches) != 1:
        raise TargetRegistryError(f"Registry must contain exactly one {role} target.")
    return matches[0]


def _validate_registry(registry: TargetRegistry) -> None:
    seen_target_ids: set[str] = set()
    seen_pdb_ids: set[str] = set()

    for target in registry.targets:
        if target.decision_role not in ALLOWED_DECISION_ROLES:
            raise TargetRegistryError(f"Unknown decision role for target {target.target_id}: {target.decision_role}")
        if target.target_id in seen_target_ids:
            raise TargetRegistryError(f"Duplicate target ID in registry: {target.target_id}")
        seen_target_ids.add(target.target_id)
        _validate_references(target)
        _validate_structures(target, seen_pdb_ids)

    _single_target_by_role(registry.targets, "primary")
    _single_target_by_role(registry.targets, "fallback")


def _validate_references(target: Target) -> None:
    if not target.key_references:
        raise TargetRegistryError(f"Target {target.target_id} has no key references.")
    for reference in target.key_references:
        if not reference.pmid.isdecimal():
            raise TargetRegistryError(f"Target {target.target_id} has a malformed reference PMID: {reference.pmid}")


def _validate_structures(target: Target, seen_pdb_ids: set[str]) -> None:
    if not target.structures:
        raise TargetRegistryError(f"Target {target.target_id} has no candidate structures.")
    for structure in target.structures:
        if len(structure.pdb_id) != 4 or not structure.pdb_id.isalnum():
            raise TargetRegistryError(f"Target {target.target_id} has a malformed structure PDB ID: {structure.pdb_id}")
        if structure.pdb_id in seen_pdb_ids:
            raise TargetRegistryError(f"Duplicate PDB ID in registry: {structure.pdb_id}")
        seen_pdb_ids.add(structure.pdb_id)

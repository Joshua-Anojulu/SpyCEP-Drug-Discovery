from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


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
    references = tuple(Reference(**item) for item in raw.get("key_references", []))
    structures = tuple(StructureCandidate(**item) for item in raw.get("structures", []))
    return Target(
        target_id=str(raw.get("target_id", "")),
        decision_role=str(raw.get("decision_role", "")),
        protein_name=str(raw.get("protein_name", "")),
        gene_name=str(raw.get("gene_name", "")),
        organism=str(raw.get("organism", "")),
        uniprot_accession=str(raw.get("uniprot_accession", "")),
        rationale=str(raw.get("rationale", "")),
        key_references=references,
        structures=structures,
    )


def _single_target_by_role(targets: tuple[Target, ...], role: str) -> Target:
    matches = [target for target in targets if target.decision_role == role]
    if len(matches) != 1:
        raise TargetRegistryError(f"Registry must contain exactly one {role} target.")
    return matches[0]


def _validate_registry(registry: TargetRegistry) -> None:
    _single_target_by_role(registry.targets, "primary")
    _single_target_by_role(registry.targets, "fallback")
    for target in registry.targets:
        if not target.structures:
            raise TargetRegistryError(f"Target {target.target_id} has no candidate structures.")
        if not target.uniprot_accession:
            raise TargetRegistryError(f"Target {target.target_id} has no UniProt accession.")

from __future__ import annotations

from dataclasses import asdict, dataclass

from spycep_drug_discovery.rcsb import RcsbEntryMetadata


@dataclass(frozen=True)
class StructureFeasibility:
    pdb_id: str
    method: str
    resolution_angstrom: float | None
    resolution_flag: str
    method_flag: str
    overall_flag: str
    notes: str

    def to_row(self) -> dict[str, str | float | None]:
        return asdict(self)


def score_structure(metadata: RcsbEntryMetadata) -> StructureFeasibility:
    resolution_flag = _resolution_flag(metadata.resolution_angstrom)
    method_flag = "experimental" if metadata.method else "missing"
    overall_flag = "candidate" if resolution_flag in {"strong", "usable"} and method_flag == "experimental" else "review_required"
    notes = _notes_for_flags(resolution_flag, method_flag)
    return StructureFeasibility(
        pdb_id=metadata.pdb_id,
        method=metadata.method,
        resolution_angstrom=metadata.resolution_angstrom,
        resolution_flag=resolution_flag,
        method_flag=method_flag,
        overall_flag=overall_flag,
        notes=notes,
    )


def _resolution_flag(resolution: float | None) -> str:
    if resolution is None:
        return "missing"
    if resolution <= 2.0:
        return "strong"
    if resolution <= 3.2:
        return "usable"
    return "weak"


def _notes_for_flags(resolution_flag: str, method_flag: str) -> str:
    notes: list[str] = []
    if resolution_flag == "strong":
        notes.append("high-resolution structure")
    if resolution_flag == "usable":
        notes.append("resolution supports initial docking feasibility")
    if resolution_flag in {"missing", "weak"}:
        notes.append("resolution requires manual review before docking")
    if method_flag != "experimental":
        notes.append("experimental method metadata missing")
    notes.append("manual pocket review required")
    return "; ".join(notes)

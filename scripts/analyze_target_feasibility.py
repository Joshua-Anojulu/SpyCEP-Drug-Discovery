from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from spycep_drug_discovery.feasibility import score_structure
from spycep_drug_discovery.paths import ensure_dir, project_root
from spycep_drug_discovery.rcsb import RcsbEntryMetadata, normalize_entry_metadata
from spycep_drug_discovery.structure_review import StructureReviewRegistry, load_structure_review_registry
from spycep_drug_discovery.targets import Target, load_target_registry


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze target-structure feasibility from tracked RCSB metadata.")
    parser.add_argument(
        "--registry",
        type=Path,
        default=Path("docs/methods/target_registry.json"),
        help="Path to target registry JSON.",
    )
    parser.add_argument(
        "--include-fallback",
        action="store_true",
        help="Also analyze fallback target structures.",
    )
    parser.add_argument(
        "--structure-review",
        type=Path,
        default=Path("docs/methods/structure_review.json"),
        help="Path to manual structure-review JSON.",
    )
    parser.add_argument(
        "--metadata-snapshot",
        type=Path,
        default=Path("docs/methods/rcsb_metadata.json"),
        help="Path to tracked RCSB metadata snapshot JSON.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = project_root()
    registry = load_target_registry(root / args.registry)
    reviews = load_structure_review_registry(root / args.structure_review)
    metadata = _load_metadata_snapshot(root / args.metadata_snapshot)
    targets = [registry.primary]
    if args.include_fallback:
        targets.append(registry.fallback)

    rows = []
    for target in targets:
        rows.extend(_rows_for_target(target, reviews, metadata))

    table_path = ensure_dir(root / "results" / "tables") / "target_feasibility.csv"
    _write_csv(table_path, rows)

    methods_path = root / "docs" / "methods" / "target_feasibility.md"
    methods_path.write_text(_markdown_report(rows), encoding="utf-8")
    print(f"Wrote {table_path}")
    print(f"Wrote {methods_path}")


def _rows_for_target(
    target: Target, reviews: StructureReviewRegistry, metadata_by_pdb_id: dict[str, RcsbEntryMetadata]
) -> list[dict[str, str | float | None]]:
    rows: list[dict[str, str | float | None]] = []
    for structure in target.structures:
        pdb_id = structure.pdb_id.upper()
        try:
            metadata = metadata_by_pdb_id[pdb_id]
        except KeyError as exc:
            raise ValueError(f"Missing tracked RCSB metadata for PDB ID {pdb_id}.") from exc
        score = score_structure(metadata)
        review = reviews.for_pdb_id(structure.pdb_id)
        row = score.to_row()
        row["target_id"] = target.target_id
        row["decision_role"] = target.decision_role
        row["selection_note"] = structure.selection_note
        row["chain_coverage"] = review.chain_coverage
        row["missing_regions"] = review.missing_regions
        row["catalytic_region_status"] = review.catalytic_region_status
        row["pocket_definition_status"] = review.pocket_definition_status
        row["docking_readiness"] = review.docking_readiness
        row["review_notes"] = review.review_notes
        row["overall_flag"] = _overall_flag_with_review(str(row["overall_flag"]), review.docking_readiness)
        rows.append(row)
    return rows


def _load_metadata_snapshot(path: Path) -> dict[str, RcsbEntryMetadata]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    metadata_by_pdb_id: dict[str, RcsbEntryMetadata] = {}
    for item in raw.get("entries", []):
        metadata = _metadata_from_snapshot_entry(item)
        if metadata.pdb_id in metadata_by_pdb_id:
            raise ValueError(f"Duplicate RCSB metadata entry for PDB ID {metadata.pdb_id}.")
        metadata_by_pdb_id[metadata.pdb_id] = metadata
    return metadata_by_pdb_id


def _overall_flag_with_review(metadata_flag: str, docking_readiness: str) -> str:
    if docking_readiness == "approved" and metadata_flag == "manual_review_required":
        return "candidate"
    if docking_readiness == "rejected":
        return "not_suitable"
    return metadata_flag


def _metadata_from_snapshot_entry(raw: dict[str, Any]) -> RcsbEntryMetadata:
    if "pdb_id" in raw:
        resolution = raw.get("resolution_angstrom")
        return RcsbEntryMetadata(
            pdb_id=str(raw.get("pdb_id", "")).upper(),
            title=str(raw.get("title", "")),
            method=str(raw.get("method", "")),
            resolution_angstrom=float(resolution) if resolution is not None else None,
        )
    return normalize_entry_metadata(raw)


def _write_csv(path: Path, rows: list[dict[str, str | float | None]]) -> None:
    fieldnames = [
        "target_id",
        "decision_role",
        "pdb_id",
        "method",
        "resolution_angstrom",
        "resolution_flag",
        "method_flag",
        "overall_flag",
        "chain_coverage",
        "missing_regions",
        "catalytic_region_status",
        "pocket_definition_status",
        "docking_readiness",
        "selection_note",
        "review_notes",
        "notes",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _markdown_report(rows: list[dict[str, str | float | None]]) -> str:
    lines = [
        "# Target Feasibility Notes",
        "",
        "This file is generated from tracked RCSB metadata and the tracked target registry.",
        "Manual structure-review fields come from `docs/methods/structure_review.json`.",
        "It supports the decision gate for whether SpyCEP/ScpC should proceed to docking.",
        "",
        "| Target | Role | PDB | Resolution | Overall | Catalytic | Pocket | Readiness | Review |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            "| {target_id} | {decision_role} | {pdb_id} | {resolution_angstrom} | {overall_flag} | {catalytic_region_status} | {pocket_definition_status} | {docking_readiness} | {review_notes} |".format(
                **{key: _markdown_cell(value) for key, value in row.items()}
            )
        )
    lines.extend(
        [
            "",
            "Decision rule: SpyCEP/ScpC can proceed only if at least one structure has usable metadata and passes manual pocket review. Metadata alone is not docking approval.",
            "",
            "Pocket boxes are tracked in `docs/methods/pocket_definition.json`.",
            "Cleaned receptor-preparation outputs are tracked in `docs/methods/receptor_preparation.json`; generated receptor PDB files remain ignored.",
            "PDBQT conversion outputs are tracked in `docs/methods/pdbqt_conversion.json`.",
            "PDBQT QC review is tracked in `docs/methods/pdbqt_quality_review.json`.",
            "Generated PDBQT, Meeko JSON, and Vina box files remain ignored.",
            "",
        ]
    )
    return "\n".join(lines)


def _markdown_cell(value: str | float | None) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


if __name__ == "__main__":
    main()

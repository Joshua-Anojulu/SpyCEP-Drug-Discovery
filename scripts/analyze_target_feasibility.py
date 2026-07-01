from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from spycep_drug_discovery.feasibility import score_structure
from spycep_drug_discovery.paths import ensure_dir, project_root
from spycep_drug_discovery.rcsb import RcsbEntryMetadata, normalize_entry_metadata
from spycep_drug_discovery.targets import Target, load_target_registry


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze target-structure feasibility from cached RCSB metadata.")
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
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = project_root()
    registry = load_target_registry(root / args.registry)
    targets = [registry.primary]
    if args.include_fallback:
        targets.append(registry.fallback)

    rows = []
    for target in targets:
        rows.extend(_rows_for_target(root, target))

    table_path = ensure_dir(root / "results" / "tables") / "target_feasibility.csv"
    _write_csv(table_path, rows)

    methods_path = root / "docs" / "methods" / "target_feasibility.md"
    methods_path.write_text(_markdown_report(rows), encoding="utf-8")
    print(f"Wrote {table_path}")
    print(f"Wrote {methods_path}")


def _rows_for_target(root: Path, target: Target) -> list[dict[str, str | float | None]]:
    rows: list[dict[str, str | float | None]] = []
    for structure in target.structures:
        metadata_path = root / "data" / "raw" / "rcsb" / f"{structure.pdb_id.upper()}.json"
        raw = json.loads(metadata_path.read_text(encoding="utf-8"))
        score = score_structure(_metadata_from_cache(raw))
        row = score.to_row()
        row["target_id"] = target.target_id
        row["decision_role"] = target.decision_role
        row["selection_note"] = structure.selection_note
        rows.append(row)
    return rows


def _metadata_from_cache(raw: dict[str, Any]) -> RcsbEntryMetadata:
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
        "selection_note",
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
        "This file is generated from cached RCSB metadata and the tracked target registry.",
        "It supports the decision gate for whether SpyCEP/ScpC should proceed to docking.",
        "",
        "| Target | Role | PDB | Resolution | Overall | Notes |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            "| {target_id} | {decision_role} | {pdb_id} | {resolution_angstrom} | {overall_flag} | {notes} |".format(
                **row
            )
        )
    lines.extend(
        [
            "",
            "Decision rule: SpyCEP/ScpC can proceed only if at least one candidate structure has usable metadata and passes manual pocket review.",
            "",
        ]
    )
    return "\n".join(lines)


if __name__ == "__main__":
    main()

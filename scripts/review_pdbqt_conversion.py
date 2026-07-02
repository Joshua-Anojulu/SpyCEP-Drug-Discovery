from __future__ import annotations

import argparse
import json
from pathlib import Path

from spycep_drug_discovery.paths import project_root as find_project_root
from spycep_drug_discovery.pdbqt_quality import build_pdbqt_quality_review


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Review Meeko PDBQT conversion warnings before docking.")
    parser.add_argument(
        "--conversion-manifest",
        type=Path,
        default=Path("docs/methods/pdbqt_conversion.json"),
        help="Tracked PDBQT conversion manifest JSON path.",
    )
    parser.add_argument(
        "--pocket-definition",
        type=Path,
        default=Path("docs/methods/pocket_definition.json"),
        help="Tracked pocket-definition JSON path.",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("docs/methods/pdbqt_quality_review.json"),
        help="Tracked PDBQT QC review manifest JSON path.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = find_project_root()
    review = write_pdbqt_quality_review(
        conversion_manifest_path=root / args.conversion_manifest,
        pocket_definition_path=root / args.pocket_definition,
        project_root=root,
        manifest_path=root / args.manifest,
    )
    print(f"Wrote {root / args.manifest}")
    print(f"Decision status: {review['decision_status']}")


def write_pdbqt_quality_review(
    conversion_manifest_path: Path,
    pocket_definition_path: Path,
    project_root: Path,
    manifest_path: Path,
) -> dict:
    conversion_manifest = json.loads(conversion_manifest_path.read_text(encoding="utf-8"))
    pocket_definition = json.loads(pocket_definition_path.read_text(encoding="utf-8"))
    review = build_pdbqt_quality_review(
        conversion_manifest=conversion_manifest,
        pocket_definition=pocket_definition,
        project_root=project_root,
    )
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(review, indent=2) + "\n", encoding="utf-8")
    return review


if __name__ == "__main__":
    main()

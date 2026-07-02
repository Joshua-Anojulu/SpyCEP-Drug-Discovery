from __future__ import annotations

import argparse
import json
from pathlib import Path

from spycep_drug_discovery.paths import project_root
from spycep_drug_discovery.pocket_definition import build_spycep_pocket_definition


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Define approved candidate SpyCEP active-site pockets.")
    parser.add_argument(
        "--structure-dir",
        type=Path,
        default=Path("data/structures"),
        help="Directory containing downloaded PDB files.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("docs/methods/pocket_definition.json"),
        help="Tracked JSON output path for pocket definitions.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = project_root()
    output_path = root / args.output
    write_pocket_definition(root / args.structure_dir, output_path)
    print(f"Wrote {output_path}")


def write_pocket_definition(structure_dir: Path, output_path: Path) -> dict:
    definition = build_spycep_pocket_definition(structure_dir)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(definition, indent=2) + "\n", encoding="utf-8")
    return definition


if __name__ == "__main__":
    main()

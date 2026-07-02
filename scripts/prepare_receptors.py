from __future__ import annotations

import argparse
import json
from pathlib import Path

from spycep_drug_discovery.paths import project_root
from spycep_drug_discovery.receptor_preparation import prepare_receptors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare cleaned receptor PDB files for approved SpyCEP pockets.")
    parser.add_argument(
        "--pocket-definition",
        type=Path,
        default=Path("docs/methods/pocket_definition.json"),
        help="Tracked pocket-definition JSON path.",
    )
    parser.add_argument(
        "--structure-dir",
        type=Path,
        default=Path("data/structures"),
        help="Directory containing downloaded PDB files.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/processed/receptors"),
        help="Generated cleaned receptor PDB output directory.",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("docs/methods/receptor_preparation.json"),
        help="Tracked receptor-preparation manifest JSON path.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = project_root()
    manifest = write_receptor_preparation(
        pocket_definition_path=root / args.pocket_definition,
        structure_dir=root / args.structure_dir,
        output_dir=root / args.output_dir,
        manifest_path=root / args.manifest,
    )
    print(f"Wrote {root / args.manifest}")
    for receptor in manifest["receptors"]:
        print(f"Wrote {root / receptor['prepared_pdb_path']}")


def write_receptor_preparation(
    pocket_definition_path: Path,
    structure_dir: Path,
    output_dir: Path,
    manifest_path: Path,
) -> dict:
    pocket_definition = json.loads(pocket_definition_path.read_text(encoding="utf-8"))
    manifest = prepare_receptors(pocket_definition, structure_dir, output_dir)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


if __name__ == "__main__":
    main()

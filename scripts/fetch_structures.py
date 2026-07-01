from __future__ import annotations

import argparse
import json
from pathlib import Path

from spycep_drug_discovery.paths import ensure_dir, project_root
from spycep_drug_discovery.rcsb import fetch_entry_metadata, fetch_pdb_text
from spycep_drug_discovery.targets import load_target_registry


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch RCSB metadata and PDB files for registered target structures.")
    parser.add_argument(
        "--registry",
        type=Path,
        default=Path("docs/methods/target_registry.json"),
        help="Path to target registry JSON.",
    )
    parser.add_argument(
        "--include-fallback",
        action="store_true",
        help="Also fetch fallback target structures.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = project_root()
    registry = load_target_registry(root / args.registry)
    targets = [registry.primary]
    if args.include_fallback:
        targets.append(registry.fallback)

    metadata_dir = ensure_dir(root / "data" / "raw" / "rcsb")
    structure_dir = ensure_dir(root / "data" / "structures")

    for target in targets:
        for structure in target.structures:
            pdb_id = structure.pdb_id.upper()
            metadata = fetch_entry_metadata(pdb_id)
            metadata_path = metadata_dir / f"{pdb_id}.json"
            metadata_path.write_text(
                json.dumps(metadata.to_json_dict(), indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )

            pdb_text = fetch_pdb_text(pdb_id)
            pdb_path = structure_dir / f"{pdb_id}.pdb"
            pdb_path.write_text(pdb_text, encoding="utf-8")
            print(f"Fetched {pdb_id}: {metadata_path} {pdb_path}")


if __name__ == "__main__":
    main()

"""Prepare, convert, and content-address QC the SpeB 6UKD receptor.

This is deliberately separate from the positive-control docking entry point.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any, Mapping

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from scripts.convert_receptors_to_pdbqt import (
    default_converter_command,
    meeko_tool_info,
)
from spycep_drug_discovery.pdbqt_conversion import convert_receptors_to_pdbqt
from spycep_drug_discovery.pdbqt_quality import (
    build_pdbqt_quality_review,
    validate_pdbqt_quality_gate,
)
from spycep_drug_discovery.receptor_preparation import clean_receptor_pdb_text
from spycep_drug_discovery.species import sha256_file


SOURCE = PROJECT_ROOT / "data" / "structures" / "6UKD.pdb"
PREPARED = PROJECT_ROOT / "data" / "processed" / "receptors" / "speb_6ukd_active_site.pdb"
OUTPUT_DIR = PROJECT_ROOT / "data" / "processed" / "pdbqt"
PREPARATION_MANIFEST = PROJECT_ROOT / "docs" / "methods" / "speb_receptor_preparation.json"
POCKET_MANIFEST = PROJECT_ROOT / "docs" / "methods" / "speb_pocket_definition.json"
CONVERSION_MANIFEST = PROJECT_ROOT / "docs" / "methods" / "speb_pdbqt_conversion.json"
QC_MANIFEST = PROJECT_ROOT / "docs" / "methods" / "speb_pdbqt_quality_review.json"

ACTIVE_SITE = [
    {"chain_id": "A", "residue_name": "CYS", "residue_number": 192},
    {"chain_id": "A", "residue_name": "HIS", "residue_number": 340},
]
DYAD_SIDE_CHAIN_ATOMS = {
    "CYS": {"CB", "SG"},
    "HIS": {"CG", "ND1", "CD2", "CE1", "NE2"},
}
PADDING_ANGSTROM = 8.0
MIN_SIZE_ANGSTROM = 18.0
MAX_SIZE_ANGSTROM = 24.0


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _dyad_box(source_text: str) -> tuple[dict[str, float], dict[str, float], int]:
    coordinates = []
    seen_residues = set()
    for line in source_text.splitlines():
        if not line.startswith("ATOM") or line[21] != "A":
            continue
        if line[16] not in (" ", "A"):
            continue
        residue_name = line[17:20].strip()
        residue_number = int(line[22:26])
        atom_name = line[12:16].strip()
        for site in ACTIVE_SITE:
            if (
                residue_name == site["residue_name"]
                and residue_number == site["residue_number"]
            ):
                seen_residues.add((residue_name, residue_number))
                if atom_name in DYAD_SIDE_CHAIN_ATOMS[residue_name]:
                    coordinates.append(
                        (
                            float(line[30:38]),
                            float(line[38:46]),
                            float(line[46:54]),
                        )
                    )
    expected = {(row["residue_name"], row["residue_number"]) for row in ACTIVE_SITE}
    if seen_residues != expected:
        raise SystemExit(
            f"6UKD source does not contain the complete Cys192/His340 dyad: {seen_residues}"
        )
    if len(coordinates) != 7:
        raise SystemExit(
            f"Expected seven Cys192/His340 side-chain atoms, found {len(coordinates)}."
        )
    xs, ys, zs = zip(*coordinates)
    center = {
        "x": round(sum(xs) / len(xs), 3),
        "y": round(sum(ys) / len(ys), 3),
        "z": round(sum(zs) / len(zs), 3),
    }

    def clamp(value: float) -> float:
        return round(min(max(value, MIN_SIZE_ANGSTROM), MAX_SIZE_ANGSTROM), 3)

    size = {
        "x": clamp((max(xs) - min(xs)) + PADDING_ANGSTROM),
        "y": clamp((max(ys) - min(ys)) + PADDING_ANGSTROM),
        "z": clamp((max(zs) - min(zs)) + PADDING_ANGSTROM),
    }
    return center, size, len(coordinates)


def _atomic_json(path: Path, value: Mapping[str, Any]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def main() -> None:
    source_text = SOURCE.read_text(encoding="utf-8")
    center, size, dyad_atom_count = _dyad_box(source_text)
    cleaned = clean_receptor_pdb_text(source_text, chain_id="A")
    PREPARED.parent.mkdir(parents=True, exist_ok=True)
    PREPARED.write_bytes(cleaned.pdb_text.encode("utf-8"))
    prepared_hash = _sha256(PREPARED)

    pocket = {
        "definition_version": "2026-07-13-speb-dyad",
        "target_id": "speb_positive_control",
        "decision_status": "approved_for_qc",
        "active_site_residues": ACTIVE_SITE,
        "pockets": [
            {
                "pocket_id": "speb_6ukd_active_site",
                "pdb_id": "6UKD",
                "chain_id": "A",
                "receptor_pdbqt_path": "data/processed/pdbqt/speb_6ukd_active_site.pdbqt",
                "box_center_angstrom": center,
                "box_size_angstrom": size,
                "box_basis": "Cys192/His340 side-chain atoms only",
                "dyad_side_chain_atom_count": dyad_atom_count,
            }
        ],
        "source_structure_path": "data/structures/6UKD.pdb",
        "source_structure_sha256": _sha256(SOURCE),
    }
    _atomic_json(POCKET_MANIFEST, pocket)

    preparation = {
        "preparation_version": "2026-07-13-speb",
        "source_pocket_definition": "docs/methods/speb_pocket_definition.json",
        "source_structure_path": "data/structures/6UKD.pdb",
        "source_structure_sha256": _sha256(SOURCE),
        "receptors": [
            {
                "pocket_id": "speb_6ukd_active_site",
                "pdb_id": "6UKD",
                "chain_id": "A",
                "prepared_pdb_path": "data/processed/receptors/speb_6ukd_active_site.pdb",
                "sha256": prepared_hash,
                "box_center_angstrom": center,
                "box_size_angstrom": size,
                "retained_atom_records": cleaned.retained_atom_records,
                "converted_mse_records": cleaned.converted_mse_records,
                "removed_heterogen_records": cleaned.removed_heterogen_records,
                "dropped_altloc_records": cleaned.dropped_altloc_records,
            }
        ],
    }
    _atomic_json(PREPARATION_MANIFEST, preparation)

    converter = default_converter_command(PROJECT_ROOT)
    conversion = convert_receptors_to_pdbqt(
        preparation,
        project_root=PROJECT_ROOT,
        output_dir=OUTPUT_DIR,
        converter_command=converter,
        tool_info=meeko_tool_info(converter, PROJECT_ROOT),
        allow_bad_res=True,
    )
    conversion["source_receptor_preparation"] = (
        "docs/methods/speb_receptor_preparation.json"
    )
    _atomic_json(CONVERSION_MANIFEST, conversion)

    conversion_hash = sha256_file(CONVERSION_MANIFEST)
    pocket_hash = sha256_file(POCKET_MANIFEST)
    review = build_pdbqt_quality_review(
        conversion,
        pocket,
        project_root=PROJECT_ROOT,
        conversion_manifest_sha256=conversion_hash,
        pocket_definition_sha256=pocket_hash,
        conversion_source_path="docs/methods/speb_pdbqt_conversion.json",
        pocket_source_path="docs/methods/speb_pocket_definition.json",
    )
    _atomic_json(QC_MANIFEST, review)
    validate_pdbqt_quality_gate(
        review,
        conversion,
        pocket,
        project_root=PROJECT_ROOT,
        conversion_manifest_sha256=conversion_hash,
        pocket_definition_sha256=pocket_hash,
        required_pocket_ids={"speb_6ukd_active_site"},
    )
    print(
        "SpeB receptor QC PASS: 6UKD Cys192/His340 present; "
        f"{dyad_atom_count} dyad side-chain atoms define the box."
    )
    print(f"Wrote {QC_MANIFEST.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()

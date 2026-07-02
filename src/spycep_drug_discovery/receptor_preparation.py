from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any


PREPARED_RECEPTOR_DIR = "data/processed/receptors"
PREPARATION_RULES = (
    "Keep only the selected receptor chain from ATOM records.",
    "Convert polymer MSE HETATM records to MET ATOM records, including SE-to-SD atom naming.",
    "Remove non-polymer HETATM records, including crystallographic ligands, salts, ions, and waters.",
    "Write cleaned PDB receptors only; PDBQT conversion remains a later, separately verified step.",
)


@dataclass(frozen=True)
class CleanedReceptorPdb:
    pdb_text: str
    retained_atom_records: int
    converted_mse_records: int
    removed_heterogen_records: int


def clean_receptor_pdb_text(pdb_text: str, chain_id: str) -> CleanedReceptorPdb:
    output_lines: list[str] = []
    converted_mse_records = 0
    removed_heterogen_records = 0

    for line in pdb_text.splitlines():
        if line.startswith("ATOM  "):
            if _chain_id(line) == chain_id:
                output_lines.append(line)
            continue
        if line.startswith("HETATM"):
            if _chain_id(line) == chain_id and _residue_name(line) == "MSE":
                output_lines.append(_mse_to_met_atom_line(line))
                converted_mse_records += 1
            else:
                removed_heterogen_records += 1

    output_lines.append("END")
    return CleanedReceptorPdb(
        pdb_text="\n".join(output_lines) + "\n",
        retained_atom_records=len(output_lines) - 1,
        converted_mse_records=converted_mse_records,
        removed_heterogen_records=removed_heterogen_records,
    )


def prepare_receptors(
    pocket_definition: dict[str, Any],
    structure_dir: Path,
    output_dir: Path,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    receptors = []
    for pocket in pocket_definition["pockets"]:
        pocket_id = str(pocket["pocket_id"])
        pdb_id = str(pocket["pdb_id"]).upper()
        chain_id = str(pocket["chain_id"])
        source_path = structure_dir / f"{pdb_id}.pdb"
        cleaned = clean_receptor_pdb_text(source_path.read_text(encoding="utf-8"), chain_id=chain_id)
        output_path = output_dir / f"{pocket_id}.pdb"
        output_path.write_text(cleaned.pdb_text, encoding="utf-8")
        receptors.append(_manifest_row(pocket, cleaned, output_path))

    return {
        "preparation_version": "2026-07-02",
        "source_pocket_definition": "docs/methods/pocket_definition.json",
        "rules": list(PREPARATION_RULES),
        "receptors": receptors,
    }


def _manifest_row(
    pocket: dict[str, Any],
    cleaned: CleanedReceptorPdb,
    output_path: Path,
) -> dict[str, Any]:
    return {
        "pocket_id": pocket["pocket_id"],
        "pdb_id": pocket["pdb_id"],
        "chain_id": pocket["chain_id"],
        "prepared_pdb_path": f"{PREPARED_RECEPTOR_DIR}/{output_path.name}",
        "sha256": hashlib.sha256(cleaned.pdb_text.encode("utf-8")).hexdigest(),
        "box_center_angstrom": pocket["box_center_angstrom"],
        "box_size_angstrom": pocket["box_size_angstrom"],
        "retained_atom_records": cleaned.retained_atom_records,
        "converted_mse_records": cleaned.converted_mse_records,
        "removed_heterogen_records": cleaned.removed_heterogen_records,
    }


def _mse_to_met_atom_line(line: str) -> str:
    converted = "ATOM  " + line[6:]
    converted = converted[:17] + "MET" + converted[20:]
    if _atom_name(converted) == "SE":
        converted = converted[:12] + " SD " + converted[16:]
        converted = _replace_element(converted, "S")
    return converted


def _replace_element(line: str, element: str) -> str:
    padded = line.ljust(78)
    return padded[:76] + f"{element:>2}" + padded[78:]


def _atom_name(line: str) -> str:
    return line[12:16].strip()


def _residue_name(line: str) -> str:
    return line[17:20].strip()


def _chain_id(line: str) -> str:
    return line[21].strip()

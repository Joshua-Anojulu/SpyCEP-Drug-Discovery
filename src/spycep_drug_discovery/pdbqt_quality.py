from __future__ import annotations

import ast
import re
from collections import Counter
from pathlib import Path
from typing import Any, Mapping


REVIEW_VERSION = "2026-07-02"
REVIEW_RULES = (
    "Parse Meeko --allow_bad_res residue omissions from the conversion manifest stderr tail.",
    "Block docking if any omitted residue overlaps the tracked SpyCEP catalytic active-site residues.",
    "Block docking if any tracked catalytic active-site residue is absent from the generated receptor PDBQT.",
    "Treat passing QC as a review checkpoint, not final docking approval.",
)


def parse_ignored_residue_keys(stderr_tail: str) -> tuple[str, ...]:
    match = re.search(r"Template matching failed for:\s*(\[.*?\])\s*Ignored due to allow_bad_res", stderr_tail, re.S)
    if not match:
        return ()
    try:
        values = ast.literal_eval(match.group(1))
    except (SyntaxError, ValueError):
        return ()
    return tuple(str(value) for value in values)


def build_pdbqt_quality_review(
    conversion_manifest: Mapping[str, Any],
    pocket_definition: Mapping[str, Any],
    *,
    project_root: Path,
) -> dict[str, Any]:
    active_site_residues = tuple(_active_site_residue_key(residue) for residue in pocket_definition["active_site_residues"])
    pockets_by_id = {pocket["pocket_id"]: pocket for pocket in pocket_definition["pockets"]}
    receptors = [
        _review_receptor(
            receptor,
            pocket=pockets_by_id[str(receptor["pocket_id"])],
            active_site_residues=active_site_residues,
            project_root=project_root,
        )
        for receptor in conversion_manifest["receptors"]
    ]
    return {
        "review_version": REVIEW_VERSION,
        "source_pdbqt_conversion": "docs/methods/pdbqt_conversion.json",
        "source_pocket_definition": "docs/methods/pocket_definition.json",
        "decision_status": _decision_status(receptors),
        "rules": list(REVIEW_RULES),
        "receptors": receptors,
    }


def _review_receptor(
    receptor: Mapping[str, Any],
    *,
    pocket: Mapping[str, Any],
    active_site_residues: tuple[str, ...],
    project_root: Path,
) -> dict[str, Any]:
    ignored_residue_keys = parse_ignored_residue_keys(str(receptor.get("stderr_tail", "")))
    ignored_chain_numbers = {_chain_number_key(residue_key) for residue_key in ignored_residue_keys}
    active_chain_numbers = {_chain_number_key(residue_key) for residue_key in active_site_residues}
    ignored_active_site = sorted(ignored_chain_numbers & active_chain_numbers, key=_residue_sort_key)

    pdbqt_path = project_root / receptor["output_paths"]["pdbqt"]
    residue_counts = _pdbqt_residue_counts(pdbqt_path)
    present_active = [residue_key for residue_key in active_site_residues if residue_counts[residue_key] > 0]
    missing_active = [residue_key for residue_key in active_site_residues if residue_counts[residue_key] == 0]
    box_matches = _axis_dict_matches(receptor["box_center_angstrom"], pocket["box_center_angstrom"]) and _axis_dict_matches(
        receptor["box_size_angstrom"], pocket["box_size_angstrom"]
    )
    blocked = bool(ignored_active_site or missing_active or not box_matches)

    return {
        "pocket_id": receptor["pocket_id"],
        "pdb_id": receptor["pdb_id"],
        "chain_id": receptor["chain_id"],
        "quality_status": "blocked" if blocked else "reviewed_caution",
        "ignored_residue_count": len(ignored_residue_keys),
        "ignored_residue_keys": list(ignored_residue_keys),
        "ignored_active_site_residue_keys": ignored_active_site,
        "pdbqt_active_site_residue_keys": present_active,
        "missing_active_site_residue_keys": missing_active,
        "pdbqt_active_site_atom_counts": {residue_key: residue_counts[residue_key] for residue_key in active_site_residues},
        "box_matches_conversion_manifest": box_matches,
        "review_notes": _review_notes(blocked),
    }


def _pdbqt_residue_counts(path: Path) -> Counter[str]:
    counts: Counter[str] = Counter()
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.startswith(("ATOM  ", "HETATM")):
            continue
        residue_key = _pdbqt_residue_key(line)
        if residue_key:
            counts[residue_key] += 1
    return counts


def _pdbqt_residue_key(line: str) -> str | None:
    residue_number = line[22:26].strip()
    if not residue_number:
        return None
    return f"{line[21].strip()}:{int(residue_number)}:{line[17:20].strip()}"


def _active_site_residue_key(residue: Mapping[str, Any]) -> str:
    return f"{residue['chain_id']}:{int(residue['residue_number'])}:{residue['residue_name']}"


def _chain_number_key(residue_key: str) -> str:
    parts = residue_key.split(":")
    return f"{parts[0]}:{int(parts[1])}"


def _residue_sort_key(residue_key: str) -> tuple[str, int]:
    chain_id, residue_number = residue_key.split(":")
    return chain_id, int(residue_number)


def _axis_dict_matches(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
    return all(round(float(left[axis]), 3) == round(float(right[axis]), 3) for axis in ("x", "y", "z"))


def _decision_status(receptors: list[dict[str, Any]]) -> str:
    if any(receptor["quality_status"] == "blocked" for receptor in receptors):
        return "blocked_before_docking"
    return "reviewed_caution_not_docking_approval"


def _review_notes(blocked: bool) -> str:
    if blocked:
        return "PDBQT QC found active-site or box mismatches; do not dock until reviewed."
    return "No active-site residue omission detected; this is a QC checkpoint, not docking approval."

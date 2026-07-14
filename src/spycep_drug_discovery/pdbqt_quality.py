from __future__ import annotations

import ast
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Mapping


REVIEW_VERSION = "2026-07-13-content-addressed"
REVIEW_RULES = (
    "Parse Meeko --allow_bad_res residue omissions from the full conversion stderr.",
    "Block if an omitted residue overlaps the tracked catalytic active-site residues.",
    "Block if a tracked catalytic residue is absent from the reviewed receptor PDBQT.",
    "Block if source-PDB, pocket-definition, or reviewed-PDBQT hashes disagree.",
)

IGNORED_RESIDUE_PATTERN = re.compile(
    r"Template matching failed for:\s*(\[.*?\])\s*Ignored due to allow_bad_res",
    re.S,
)


class QualityReviewError(RuntimeError):
    """Raised when receptor QC cannot establish a content-addressed pass."""


def parse_ignored_residue_keys(
    stderr: str,
    *,
    allow_bad_res: bool = True,
) -> tuple[str, ...]:
    if not allow_bad_res:
        return ()
    match = IGNORED_RESIDUE_PATTERN.search(stderr)
    if not match:
        if "Template matching failed" in stderr:
            raise QualityReviewError(
                "Meeko reported template-matching failures but the omitted-residue "
                "list could not be parsed. Refusing to record zero omissions."
            )
        return ()
    try:
        values = ast.literal_eval(match.group(1))
    except (SyntaxError, ValueError) as exc:
        raise QualityReviewError(
            f"Could not parse Meeko's omitted-residue list: {exc}"
        ) from exc
    return tuple(str(value) for value in values)


def build_pdbqt_quality_review(
    conversion_manifest: Mapping[str, Any],
    pocket_definition: Mapping[str, Any],
    *,
    project_root: Path,
    conversion_manifest_sha256: str | None = None,
    pocket_definition_sha256: str | None = None,
    conversion_source_path: str = "docs/methods/pdbqt_conversion.json",
    pocket_source_path: str = "docs/methods/pocket_definition.json",
) -> dict[str, Any]:
    active_site_residues = tuple(
        _active_site_residue_key(residue)
        for residue in pocket_definition["active_site_residues"]
    )
    pockets_by_id = {
        str(pocket["pocket_id"]): pocket
        for pocket in pocket_definition["pockets"]
    }
    conversion_hash = conversion_manifest_sha256 or _json_sha256(conversion_manifest)
    upstream_source = _upstream_source_record(pocket_definition, project_root)
    pocket_hash = pocket_definition_sha256 or _json_sha256(pocket_definition)
    receptors = [
        _review_receptor(
            receptor,
            pocket=pockets_by_id[str(receptor["pocket_id"])],
            active_site_residues=active_site_residues,
            project_root=project_root,
            pocket_definition_sha256=pocket_hash,
        )
        for receptor in conversion_manifest["receptors"]
    ]
    decision = (
        "block"
        if any(row["quality_status"] == "block" for row in receptors)
        or (upstream_source is not None and not upstream_source["hash_matches"])
        else "pass"
    )
    return {
        "review_version": REVIEW_VERSION,
        "source_pdbqt_conversion": conversion_source_path,
        "source_pdbqt_conversion_sha256": conversion_hash,
        "source_pocket_definition": pocket_source_path,
        "source_pocket_definition_sha256": pocket_hash,
        "decision_status": decision,
        "rules": list(REVIEW_RULES),
        "upstream_source": upstream_source,
        "receptors": receptors,
    }


def validate_pdbqt_quality_gate(
    review: Mapping[str, Any],
    conversion_manifest: Mapping[str, Any],
    pocket_definition: Mapping[str, Any],
    *,
    project_root: Path,
    conversion_manifest_sha256: str,
    pocket_definition_sha256: str,
    required_pocket_ids: set[str] | None = None,
) -> None:
    if review.get("decision_status") != "pass":
        raise QualityReviewError(
            f"Receptor QC decision is {review.get('decision_status')!r}; docking is blocked."
        )
    if review.get("source_pdbqt_conversion_sha256") != conversion_manifest_sha256:
        raise QualityReviewError("Receptor QC conversion-manifest hash is stale.")
    if review.get("source_pocket_definition_sha256") != pocket_definition_sha256:
        raise QualityReviewError("Receptor QC pocket-definition hash is stale.")

    upstream_source = review.get("upstream_source")
    if upstream_source is not None:
        source_path = _resolve_path(project_root, upstream_source["path"])
        actual_source_hash = _sha256(source_path)
        declared_source_hash = pocket_definition.get("source_structure_sha256")
        if not (
            actual_source_hash
            == declared_source_hash
            == upstream_source.get("sha256")
        ):
            raise QualityReviewError("Upstream source-structure hash agreement failed.")

    reviewed = {str(row["pocket_id"]): row for row in review.get("receptors", ())}
    converted = {
        str(row["pocket_id"]): row
        for row in conversion_manifest.get("receptors", ())
    }
    pockets = {
        str(row["pocket_id"]): row
        for row in pocket_definition.get("pockets", ())
    }
    required = required_pocket_ids or set(converted)
    if not required.issubset(reviewed) or not required.issubset(converted):
        raise QualityReviewError("Receptor QC does not cover every required pocket.")

    for pocket_id in required:
        row = reviewed[pocket_id]
        conversion = converted[pocket_id]
        pocket = pockets.get(pocket_id)
        if row.get("quality_status") != "pass":
            raise QualityReviewError(f"{pocket_id}: QC is not pass.")
        pdbqt_path = _resolve_path(project_root, conversion["output_paths"]["pdbqt"])
        source_path = _resolve_path(project_root, conversion["source_prepared_pdb_path"])
        actual_pdbqt_hash = _sha256(pdbqt_path)
        actual_source_hash = _sha256(source_path)
        conversion_pdbqt_hash = conversion["output_sha256"]["pdbqt"]
        if not (
            actual_pdbqt_hash
            == conversion_pdbqt_hash
            == row.get("reviewed_pdbqt_sha256")
        ):
            raise QualityReviewError(f"{pocket_id}: reviewed PDBQT hash agreement failed.")
        if not (
            actual_source_hash
            == conversion.get("source_prepared_pdb_sha256")
            == row.get("source_prepared_pdb_sha256")
        ):
            raise QualityReviewError(f"{pocket_id}: source prepared-PDB hash agreement failed.")
        if pocket is None or row.get("pocket_record_sha256") != _json_sha256(pocket):
            raise QualityReviewError(f"{pocket_id}: pocket-record hash agreement failed.")
        if row.get("pocket_definition_sha256") != pocket_definition_sha256:
            raise QualityReviewError(f"{pocket_id}: pocket-definition hash agreement failed.")


def _review_receptor(
    receptor: Mapping[str, Any],
    *,
    pocket: Mapping[str, Any],
    active_site_residues: tuple[str, ...],
    project_root: Path,
    pocket_definition_sha256: str,
) -> dict[str, Any]:
    stderr = str(receptor.get("stderr") or receptor.get("stderr_tail") or "")
    ignored_residue_keys = parse_ignored_residue_keys(
        stderr,
        allow_bad_res=bool(receptor.get("allow_bad_res", True)),
    )
    ignored_chain_numbers = {
        _chain_number_key(residue_key) for residue_key in ignored_residue_keys
    }
    active_chain_numbers = {
        _chain_number_key(residue_key) for residue_key in active_site_residues
    }
    ignored_active_site = sorted(
        ignored_chain_numbers & active_chain_numbers,
        key=_residue_sort_key,
    )

    pdbqt_path = _resolve_path(project_root, receptor["output_paths"]["pdbqt"])
    source_path = _resolve_path(project_root, receptor["source_prepared_pdb_path"])
    if not pdbqt_path.is_file() or not source_path.is_file():
        raise QualityReviewError(
            f"{receptor['pocket_id']}: source prepared PDB or reviewed PDBQT is missing."
        )
    actual_pdbqt_hash = _sha256(pdbqt_path)
    actual_source_hash = _sha256(source_path)
    conversion_pdbqt_hash = receptor.get("output_sha256", {}).get("pdbqt")
    conversion_source_hash = receptor.get("source_prepared_pdb_sha256")
    pdbqt_hash_matches = actual_pdbqt_hash == conversion_pdbqt_hash
    source_hash_matches = actual_source_hash == conversion_source_hash

    residue_counts = _pdbqt_residue_counts(pdbqt_path)
    present_active = [
        residue_key
        for residue_key in active_site_residues
        if residue_counts[residue_key] > 0
    ]
    missing_active = [
        residue_key
        for residue_key in active_site_residues
        if residue_counts[residue_key] == 0
    ]
    box_matches = _axis_dict_matches(
        receptor["box_center_angstrom"],
        pocket["box_center_angstrom"],
    ) and _axis_dict_matches(
        receptor["box_size_angstrom"],
        pocket["box_size_angstrom"],
    )
    blocked = bool(
        ignored_active_site
        or missing_active
        or not box_matches
        or not pdbqt_hash_matches
        or not source_hash_matches
    )

    return {
        "pocket_id": receptor["pocket_id"],
        "pdb_id": receptor["pdb_id"],
        "chain_id": receptor["chain_id"],
        "quality_status": "block" if blocked else "pass",
        "source_prepared_pdb_path": receptor["source_prepared_pdb_path"],
        "source_prepared_pdb_sha256": actual_source_hash,
        "source_hash_matches_conversion": source_hash_matches,
        "pocket_definition_sha256": pocket_definition_sha256,
        "pocket_record_sha256": _json_sha256(pocket),
        "reviewed_pdbqt_path": receptor["output_paths"]["pdbqt"],
        "reviewed_pdbqt_sha256": actual_pdbqt_hash,
        "pdbqt_hash_matches_conversion": pdbqt_hash_matches,
        "ignored_residue_count": len(ignored_residue_keys),
        "ignored_residue_keys": list(ignored_residue_keys),
        "ignored_active_site_residue_keys": ignored_active_site,
        "pdbqt_active_site_residue_keys": present_active,
        "missing_active_site_residue_keys": missing_active,
        "pdbqt_active_site_atom_counts": {
            residue_key: residue_counts[residue_key]
            for residue_key in active_site_residues
        },
        "box_matches_conversion_manifest": box_matches,
        "review_notes": (
            "Content-addressed receptor QC passed."
            if not blocked
            else "Content-addressed receptor QC failed; docking is blocked."
        ),
    }


def _upstream_source_record(
    pocket_definition: Mapping[str, Any],
    project_root: Path,
) -> dict[str, Any] | None:
    source_path_value = pocket_definition.get("source_structure_path")
    declared_hash = pocket_definition.get("source_structure_sha256")
    if source_path_value is None and declared_hash is None:
        return None
    if not source_path_value or not declared_hash:
        raise QualityReviewError(
            "Pocket definition carries incomplete upstream source provenance."
        )
    source_path = _resolve_path(project_root, source_path_value)
    actual_hash = _sha256(source_path)
    return {
        "path": source_path_value,
        "sha256": actual_hash,
        "hash_matches": actual_hash == declared_hash,
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
    return (
        f"{residue['chain_id']}:{int(residue['residue_number'])}:"
        f"{residue['residue_name']}"
    )


def _chain_number_key(residue_key: str) -> str:
    parts = residue_key.split(":")
    return f"{parts[0]}:{int(parts[1])}"


def _residue_sort_key(residue_key: str) -> tuple[str, int]:
    chain_id, residue_number = residue_key.split(":")
    return chain_id, int(residue_number)


def _axis_dict_matches(
    left: Mapping[str, Any],
    right: Mapping[str, Any],
) -> bool:
    return all(
        round(float(left[axis]), 3) == round(float(right[axis]), 3)
        for axis in ("x", "y", "z")
    )


def _json_sha256(value: Mapping[str, Any]) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _sha256(path: Path) -> str:
    if not path.is_file():
        raise QualityReviewError(f"Required QC input is missing: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _resolve_path(project_root: Path, value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else project_root / path

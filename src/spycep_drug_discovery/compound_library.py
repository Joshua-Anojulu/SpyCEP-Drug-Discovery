from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence


LIBRARY_VERSION = "2026-07-02"
VALID_SETS = ("custom_anti_virulence", "fda_comparator")
REQUIRED_FIELDS = (
    "ligand_id",
    "name",
    "smiles",
    "compound_class",
    "inclusion_rationale",
    "source",
    "set",
)


class CompoundLibraryError(ValueError):
    """Raised when a compound entry is missing provenance or the library is inconsistent."""


def validate_smiles(smiles: str) -> bool:
    from rdkit import Chem

    return Chem.MolFromSmiles(smiles) is not None


def validate_compound(compound: Mapping[str, Any], *, check_smiles: bool = True) -> None:
    ligand_id = compound.get("ligand_id", "<unknown>")
    missing = [field for field in REQUIRED_FIELDS if not str(compound.get(field, "")).strip()]
    if missing:
        raise CompoundLibraryError(f"Compound {ligand_id!r} is missing required fields: {', '.join(missing)}")
    if compound["set"] not in VALID_SETS:
        raise CompoundLibraryError(
            f"Compound {ligand_id!r} has invalid set {compound['set']!r}; expected one of {VALID_SETS}."
        )
    source = str(compound["source"]).strip()
    if not (source.upper().startswith("PMID:") or source.startswith("http://") or source.startswith("https://")):
        raise CompoundLibraryError(
            f"Compound {ligand_id!r} source must be a PMID:<id> or an http(s) URL, got {source!r}."
        )
    if check_smiles and not validate_smiles(str(compound["smiles"])):
        raise CompoundLibraryError(f"Compound {ligand_id!r} has an unparseable SMILES: {compound['smiles']!r}.")


def validate_library(compounds: Sequence[Mapping[str, Any]], *, check_smiles: bool = True) -> None:
    seen_ids: set[str] = set()
    seen_names: set[str] = set()
    for compound in compounds:
        validate_compound(compound, check_smiles=check_smiles)
        ligand_id = str(compound["ligand_id"])
        name = str(compound["name"]).strip().lower()
        if ligand_id in seen_ids:
            raise CompoundLibraryError(f"Duplicate ligand_id: {ligand_id!r}.")
        if name in seen_names:
            raise CompoundLibraryError(f"Duplicate compound name: {compound['name']!r}.")
        seen_ids.add(ligand_id)
        seen_names.add(name)


def load_compound_library(path: Path, *, check_smiles: bool = True) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    compounds = data.get("compounds", [])
    validate_library(compounds, check_smiles=check_smiles)
    return data


def summarize_library(compounds: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    counts: dict[str, int] = {set_name: 0 for set_name in VALID_SETS}
    for compound in compounds:
        counts[str(compound["set"])] += 1
    return {
        "library_version": LIBRARY_VERSION,
        "compound_count": len(compounds),
        "counts_by_set": counts,
    }

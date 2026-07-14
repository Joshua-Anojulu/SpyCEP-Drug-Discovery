"""Authoritative, tier-validated ligand-species catalog.

Single-state tiers are reproducible rule outputs.  AMBIGUOUS states are deliberately
not regenerated: they are hand-reviewed hypotheses consumed verbatim and checked for
chemical/cryptographic integrity only.
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping


CATALOG_SCHEMA_VERSION = "species-audit-v1"
SPECIES_TIERS = frozenset({"UNAMBIGUOUS", "AMBIGUOUS", "NO_IONISABLE_SITE"})
AMBIGUITY_LIMIT = 2


class SpeciesCatalogError(RuntimeError):
    """Raised when the authoritative species catalog fails closed."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atom_mapped_canonical_smiles(smiles: str) -> str:
    """Return canonical isomeric SMILES with one stable map number per atom."""
    from rdkit import Chem

    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise SpeciesCatalogError(f"RDKit could not parse species SMILES: {smiles!r}")
    for index, atom in enumerate(mol.GetAtoms(), start=1):
        atom.SetAtomMapNum(index)
    return Chem.MolToSmiles(mol, canonical=True, isomericSmiles=True)


def atom_charge_inventory(mapped_smiles: str) -> list[dict[str, Any]]:
    from rdkit import Chem

    mol = Chem.MolFromSmiles(mapped_smiles)
    if mol is None:
        raise SpeciesCatalogError(f"RDKit could not parse mapped species: {mapped_smiles!r}")
    return sorted(
        (
            {
                "atom_map": atom.GetAtomMapNum(),
                "element": atom.GetSymbol(),
                "formal_charge": atom.GetFormalCharge(),
            }
            for atom in mol.GetAtoms()
        ),
        key=lambda row: row["atom_map"],
    )


def state_smiles_sha256(mapped_smiles: str) -> str:
    return hashlib.sha256(mapped_smiles.encode("utf-8")).hexdigest()


def unmapped_canonical_smiles(mapped_or_unmapped_smiles: str) -> str:
    from rdkit import Chem

    mol = Chem.MolFromSmiles(mapped_or_unmapped_smiles)
    if mol is None:
        raise SpeciesCatalogError(
            f"RDKit could not parse species SMILES: {mapped_or_unmapped_smiles!r}"
        )
    for atom in mol.GetAtoms():
        atom.SetAtomMapNum(0)
    return Chem.MolToSmiles(mol, canonical=True, isomericSmiles=True)


def make_state_row(
    *,
    entity_id: str,
    state_id: str,
    source_smiles: str,
    state_smiles: str,
    tier: str,
    dock_eligible: bool,
    exclusion_reason: str | None,
    producing_rule: str,
    provenance: Mapping[str, Any],
    classification_evidence: Mapping[str, Any],
    entity_kind: str,
    set_name: str | None = None,
    review: Mapping[str, Any] | None = None,
    source_parent_entity_id: str | None = None,
    surrogate_entity_id: str | None = None,
) -> dict[str, Any]:
    from rdkit import Chem

    mapped = atom_mapped_canonical_smiles(state_smiles)
    mol = Chem.MolFromSmiles(mapped)
    row: dict[str, Any] = {
        "entity_id": entity_id,
        "state_id": state_id,
        "entity_kind": entity_kind,
        "set": set_name,
        "source_smiles": source_smiles,
        "atom_mapped_canonical_smiles": mapped,
        "atom_formal_charges": atom_charge_inventory(mapped),
        "net_formal_charge": Chem.GetFormalCharge(mol),
        "state_smiles_sha256": state_smiles_sha256(mapped),
        "producing_rule": producing_rule,
        "tier": tier,
        "dock_eligible": dock_eligible,
        "exclusion_reason": exclusion_reason,
        "provenance": dict(provenance),
        "classification_evidence": dict(classification_evidence),
    }
    if review is not None:
        row["review"] = dict(review)
    if source_parent_entity_id is not None:
        row["source_parent_entity_id"] = source_parent_entity_id
    if surrogate_entity_id is not None:
        row["surrogate_entity_id"] = surrogate_entity_id
    return row


def catalog_state(
    catalog: Mapping[str, Any],
    entity_id: str,
    state_id: str,
) -> Mapping[str, Any]:
    matches = [
        row
        for row in catalog.get("states", ())
        if row.get("entity_id") == entity_id and row.get("state_id") == state_id
    ]
    if len(matches) != 1:
        raise SpeciesCatalogError(
            f"Expected exactly one catalog state for ({entity_id!r}, {state_id!r}), "
            f"found {len(matches)}."
        )
    return matches[0]


def load_species_catalog(
    path: Path,
    *,
    library_entity_ids: Iterable[str] | None = None,
) -> dict[str, Any]:
    catalog = json.loads(path.read_text(encoding="utf-8"))
    validate_species_catalog(catalog, library_entity_ids=library_entity_ids)
    return catalog


def validate_species_catalog(
    catalog: Mapping[str, Any],
    *,
    library_entity_ids: Iterable[str] | None = None,
) -> None:
    """Validate the frozen catalog according to its classification tier."""
    from rdkit import Chem

    if catalog.get("schema_version") != CATALOG_SCHEMA_VERSION:
        raise SpeciesCatalogError(
            f"Unsupported species catalog schema: {catalog.get('schema_version')!r}"
        )
    rows = list(catalog.get("states", ()))
    if not rows:
        raise SpeciesCatalogError("Species catalog contains no states.")

    keys = [(str(row.get("entity_id")), str(row.get("state_id"))) for row in rows]
    if len(keys) != len(set(keys)):
        duplicates = sorted(key for key, count in Counter(keys).items() if count > 1)
        raise SpeciesCatalogError(f"Duplicate (entity_id, state_id) keys: {duplicates}")

    by_entity: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        entity_id = _required_text(row, "entity_id")
        _required_text(row, "state_id")
        tier = _required_text(row, "tier")
        if tier not in SPECIES_TIERS:
            raise SpeciesCatalogError(f"{entity_id}: unknown species tier {tier!r}")
        by_entity[entity_id].append(row)
        _validate_common_state(row)

        if tier == "AMBIGUOUS":
            _validate_ambiguous_state(row)
        else:
            _validate_rule_matched_state(row)
            if tier == "NO_IONISABLE_SITE" and int(row["net_formal_charge"]) != 0:
                raise SpeciesCatalogError(
                    f"{entity_id}: NO_IONISABLE_SITE state has nonzero formal charge."
                )

    for entity_id, entity_rows in by_entity.items():
        tiers = {str(row["tier"]) for row in entity_rows}
        if len(tiers) != 1:
            raise SpeciesCatalogError(f"{entity_id}: states span multiple tiers: {sorted(tiers)}")
        tier = next(iter(tiers))
        state_count = len(entity_rows)
        if state_count > AMBIGUITY_LIMIT:
            raise SpeciesCatalogError(
                f"INDETERMINATE_CHEMISTRY: {entity_id} has {state_count} states; "
                f"the hard cap is {AMBIGUITY_LIMIT}."
            )
        expected = 2 if tier == "AMBIGUOUS" else 1
        if state_count != expected:
            raise SpeciesCatalogError(
                f"{entity_id}: tier {tier} requires exactly {expected} state(s), "
                f"found {state_count}."
            )
        eligibilities = {bool(row["dock_eligible"]) for row in entity_rows}
        exclusions = {row.get("exclusion_reason") for row in entity_rows}
        if len(eligibilities) != 1 or len(exclusions) != 1:
            raise SpeciesCatalogError(
                f"{entity_id}: dock eligibility/exclusion must be entity-consistent."
            )
        eligible = next(iter(eligibilities))
        exclusion = next(iter(exclusions))
        if eligible and exclusion is not None:
            raise SpeciesCatalogError(f"{entity_id}: eligible state carries an exclusion reason.")
        if not eligible and not exclusion:
            raise SpeciesCatalogError(f"{entity_id}: excluded state lacks an exclusion reason.")

    if library_entity_ids is not None:
        expected_library = {str(value) for value in library_entity_ids}
        observed_library = {
            entity_id
            for entity_id, entity_rows in by_entity.items()
            if entity_rows[0].get("entity_kind") == "library_parent"
        }
        if observed_library != expected_library:
            raise SpeciesCatalogError(
                "Library entity projection mismatch: "
                f"missing={sorted(expected_library - observed_library)}, "
                f"extra={sorted(observed_library - expected_library)}"
            )

    mappings = dict(catalog.get("source_to_surrogate", {}))
    boron_parents = {
        entity_id
        for entity_id, entity_rows in by_entity.items()
        if entity_rows[0].get("entity_kind") == "library_parent"
        and not bool(entity_rows[0]["dock_eligible"])
    }
    if set(mappings) != boron_parents:
        raise SpeciesCatalogError(
            "source_to_surrogate keys must exactly equal excluded boronic-acid parents."
        )
    for parent, surrogate in mappings.items():
        if surrogate not in by_entity:
            raise SpeciesCatalogError(f"{parent}: missing mapped surrogate {surrogate!r}.")
        parent_row = by_entity[parent][0]
        surrogate_row = by_entity[surrogate][0]
        if parent_row.get("surrogate_entity_id") != surrogate:
            raise SpeciesCatalogError(f"{parent}: parent row does not record its surrogate.")
        if surrogate_row.get("source_parent_entity_id") != parent:
            raise SpeciesCatalogError(f"{surrogate}: surrogate row does not record its parent.")
        if surrogate_row.get("entity_kind") != "gem_diol_surrogate":
            raise SpeciesCatalogError(f"{surrogate}: mapped entity is not a gem-diol surrogate.")


def _validate_common_state(row: Mapping[str, Any]) -> None:
    from rdkit import Chem

    entity_id = _required_text(row, "entity_id")
    mapped = _required_text(row, "atom_mapped_canonical_smiles")
    mol = Chem.MolFromSmiles(mapped)
    if mol is None:
        raise SpeciesCatalogError(f"{entity_id}: mapped SMILES does not parse.")

    maps = [atom.GetAtomMapNum() for atom in mol.GetAtoms()]
    if any(value <= 0 for value in maps) or len(maps) != len(set(maps)):
        raise SpeciesCatalogError(f"{entity_id}: atom maps must be present and unique.")
    if set(maps) != set(range(1, len(maps) + 1)):
        raise SpeciesCatalogError(f"{entity_id}: atom maps must form the complete 1..N set.")

    round_trip = Chem.MolToSmiles(mol, canonical=True, isomericSmiles=True)
    if round_trip != mapped:
        raise SpeciesCatalogError(f"{entity_id}: canonical mapped-SMILES round trip changed identity.")

    expected_inventory = atom_charge_inventory(mapped)
    if list(row.get("atom_formal_charges", ())) != expected_inventory:
        raise SpeciesCatalogError(f"{entity_id}: per-atom formal-charge inventory mismatch.")
    if int(row.get("net_formal_charge", 10**9)) != Chem.GetFormalCharge(mol):
        raise SpeciesCatalogError(f"{entity_id}: net formal charge mismatch.")
    if row.get("state_smiles_sha256") != state_smiles_sha256(mapped):
        raise SpeciesCatalogError(f"{entity_id}: state SMILES SHA-256 mismatch.")

    _required_text(row, "producing_rule")
    _required_text(row, "entity_kind")
    if not isinstance(row.get("dock_eligible"), bool):
        raise SpeciesCatalogError(f"{entity_id}: dock_eligible must be boolean.")
    _validate_provenance(entity_id, row.get("provenance"))


def _validate_provenance(entity_id: str, provenance: Any) -> None:
    if not isinstance(provenance, Mapping):
        raise SpeciesCatalogError(f"{entity_id}: provenance must be an object.")
    kind = provenance.get("kind")
    if kind == "pubchem_cid":
        if not isinstance(provenance.get("pubchem_cid"), int) or not provenance.get("source_url"):
            raise SpeciesCatalogError(f"{entity_id}: PubChem provenance is incomplete.")
    elif kind == "citation":
        if not provenance.get("citations"):
            raise SpeciesCatalogError(f"{entity_id}: citation provenance is empty.")
    elif kind == "parent_transformation":
        if not provenance.get("parent_entity_id") or not provenance.get("transformation"):
            raise SpeciesCatalogError(f"{entity_id}: parent-transformation provenance is incomplete.")
    else:
        raise SpeciesCatalogError(f"{entity_id}: unsupported provenance kind {kind!r}.")


def _validate_rule_matched_state(row: Mapping[str, Any]) -> None:
    entity_id = str(row["entity_id"])
    regenerated = _rule_output(str(row["source_smiles"]))
    frozen = unmapped_canonical_smiles(str(row["atom_mapped_canonical_smiles"]))
    if regenerated != frozen:
        raise SpeciesCatalogError(
            f"{entity_id}: single-state rule-output mismatch; frozen={frozen!r}, "
            f"regenerated={regenerated!r}."
        )


def _validate_ambiguous_state(row: Mapping[str, Any]) -> None:
    """Validate verbatim state integrity; never call the protonation rule here."""
    entity_id = str(row["entity_id"])
    review = row.get("review")
    if not isinstance(review, Mapping):
        raise SpeciesCatalogError(f"{entity_id}: AMBIGUOUS state lacks review metadata.")
    for field in ("reviewer", "classification_rationale", "review_date"):
        _required_text(review, field, prefix=f"{entity_id}.review")
    citations = review.get("citations")
    if not isinstance(citations, list) or not citations or not all(
        isinstance(value, str) and value for value in citations
    ):
        raise SpeciesCatalogError(f"{entity_id}: AMBIGUOUS review citations are incomplete.")
    decision = review.get("more_than_two_plausible_states_considered")
    if not isinstance(decision, Mapping) or not isinstance(decision.get("answer"), bool):
        raise SpeciesCatalogError(
            f"{entity_id}: AMBIGUOUS review lacks the >2-state decision answer."
        )
    if not decision.get("rationale"):
        raise SpeciesCatalogError(
            f"{entity_id}: AMBIGUOUS review lacks the >2-state decision rationale."
        )


def _rule_output(source_smiles: str) -> str:
    """Desalt and apply the frozen generic rule for single-state tiers only."""
    from rdkit import Chem

    from spycep_drug_discovery.protonation import protonate

    mol = Chem.MolFromSmiles(source_smiles)
    if mol is None:
        raise SpeciesCatalogError(f"RDKit could not parse source SMILES: {source_smiles!r}")
    fragments = Chem.GetMolFrags(mol, asMols=True, sanitizeFrags=True)
    largest = max(fragments, key=lambda fragment: fragment.GetNumHeavyAtoms())
    return unmapped_canonical_smiles(protonate(Chem.MolToSmiles(largest)))


def _required_text(
    row: Mapping[str, Any],
    field: str,
    *,
    prefix: str | None = None,
) -> str:
    value = row.get(field)
    if not isinstance(value, str) or not value:
        label = f"{prefix}.{field}" if prefix else field
        raise SpeciesCatalogError(f"Required non-empty text field is missing: {label}.")
    return value

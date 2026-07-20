from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from spycep_drug_discovery.attempt_manifest import validate_attempt_manifest
from spycep_drug_discovery.docking import (
    DockingError,
    RUN_SCHEMA_VERSION,
    validate_campaign_manifest_set,
    validate_manifest_timeout_qc,
)


ANALYSIS_SCHEMA_VERSION = "docking-statistics-v2"
POPULATION_RULE_ID = "ambiguous-excluded-entity-level"
BEST_RECEPTOR_TIE_RULE = "lowest best_affinity_kcal_mol; ties by lexicographically smaller pocket_id"
AFFINITY = "ensemble_best_affinity_kcal_mol"
EFFICIENCY = "ligand_efficiency_kcal_mol_per_heavy_atom"
RAW_AFFINITY = "best_affinity_kcal_mol"


@dataclass(frozen=True)
class WorkflowPopulation:
    workflow: str
    attempted: tuple[str, ...]
    valid_fit: tuple[str, ...]
    analysis_eligible: tuple[str, ...]
    numeric_analysis: tuple[str, ...]
    ambiguous_excluded: tuple[str, ...]
    non_fits_excluded: tuple[str, ...]


@dataclass(frozen=True)
class AnalysisPopulation:
    project_root: Path
    methods_dir: Path
    species_catalog: Mapping[str, Any]
    attempt_manifest: Mapping[str, Any]
    manifests: Mapping[str, Mapping[str, Any]]
    source_hashes: Mapping[str, str]
    ambiguous_entity_ids: tuple[str, ...]
    populations: Mapping[str, WorkflowPopulation]
    population_hash: str


def load_analysis_population(project_root: Path) -> AnalysisPopulation:
    methods_dir = project_root / "docs" / "methods"
    species_catalog, species_hash = _load_hashed_json(methods_dir / "species_audit.json")
    attempt_manifest, attempt_hash = _load_hashed_json(methods_dir / "attempt_manifest.json")
    try:
        validate_attempt_manifest(attempt_manifest, species_catalog)
    except Exception as exc:  # pragma: no cover - preserves local exception wording as cause.
        raise DockingError("Attempt manifest is not valid for the species catalog.") from exc

    manifests = {
        "wide": _load_manifest(methods_dir / "docking_result.json"),
        "tight": _load_manifest(methods_dir / "docking_result_tight.json"),
        "speb": _load_manifest(methods_dir / "speb_positive_control_result.json"),
        "boron": _load_manifest(methods_dir / "boron_surrogate_result.json"),
    }
    validate_campaign_manifest_set(tuple(manifests.values()))
    for workflow, manifest in manifests.items():
        if manifest.get("workflow") != workflow:
            raise DockingError(f"Manifest workflow mismatch for {workflow}.")
        _verify_manifest_source_hashes(
            manifest,
            species_catalog_sha256=species_hash,
            attempt_manifest_sha256=attempt_hash,
        )

    ambiguous = _derive_ambiguous_entities(species_catalog, attempt_manifest)
    source_hashes = {
        "species_audit.json": species_hash,
        "attempt_manifest.json": attempt_hash,
        "docking_result.json": _sha256(methods_dir / "docking_result.json"),
        "docking_result_tight.json": _sha256(methods_dir / "docking_result_tight.json"),
        "speb_positive_control_result.json": _sha256(methods_dir / "speb_positive_control_result.json"),
        "boron_surrogate_result.json": _sha256(methods_dir / "boron_surrogate_result.json"),
    }

    _validate_spycep_manifest_rows(manifests["wide"], attempt_manifest)
    _validate_spycep_manifest_rows(manifests["tight"], attempt_manifest)
    _validate_speb_result_rows(manifests["speb"], attempt_manifest)

    populations = {
        workflow: _workflow_population(manifest, attempt_manifest, ambiguous)
        for workflow, manifest in manifests.items()
    }
    population_payload = {
        workflow: _population_json(population)
        for workflow, population in sorted(populations.items())
    }
    population_hash = _canonical_json_sha256(population_payload)
    return AnalysisPopulation(
        project_root=project_root,
        methods_dir=methods_dir,
        species_catalog=species_catalog,
        attempt_manifest=attempt_manifest,
        manifests=manifests,
        source_hashes=source_hashes,
        ambiguous_entity_ids=ambiguous,
        populations=populations,
        population_hash=population_hash,
    )


def population_block(population: WorkflowPopulation) -> dict[str, Any]:
    return _population_json(population)


def numeric_ranking_rows(manifest: Mapping[str, Any], population: WorkflowPopulation) -> list[dict[str, Any]]:
    allowed = set(population.numeric_analysis)
    rows = [dict(row) for row in manifest["ranking"] if row["entity_id"] in allowed]
    if len(rows) != len(allowed):
        raise DockingError(f"{manifest['workflow']} numeric population is not one ranking row per entity.")
    if {row["entity_id"] for row in rows} != allowed:
        raise DockingError(f"{manifest['workflow']} numeric ranking membership mismatch.")
    return sorted(rows, key=lambda row: row["entity_id"])


def triad_engagement(manifest: Mapping[str, Any], population: WorkflowPopulation) -> dict[str, Any]:
    records_by_entity: dict[str, list[Mapping[str, Any]]] = {}
    for record in manifest["run_records"]:
        entity_id = str(record["entity_id"])
        if entity_id in population.analysis_eligible and bool(record["valid_fit"]):
            records_by_entity.setdefault(entity_id, []).append(record)

    interactions = {row["claim_key"]: row for row in manifest["pose_interactions"]}
    counts = {1: 0, 2: 0, 3: 0}
    best_claims: dict[str, str | None] = {}
    for entity_id in population.analysis_eligible:
        records = records_by_entity.get(entity_id, [])
        if not records:
            contacted = 0
            best_claims[entity_id] = None
        else:
            best = min(
                records,
                key=lambda row: (float(row[RAW_AFFINITY]), str(row["pocket_id"])),
            )
            best_claims[entity_id] = str(best["claim_key"])
            contacted = len(interactions[str(best["claim_key"])]["contacted_active_site_residues"])
        for threshold in counts:
            if contacted >= threshold:
                counts[threshold] += 1
    return {
        "population_rule_id": POPULATION_RULE_ID,
        "population": "analysis_eligible",
        "best_receptor_tie_rule": BEST_RECEPTOR_TIE_RULE,
        "ligands": len(population.analysis_eligible),
        "member_entity_ids": list(population.analysis_eligible),
        "non_fit_zero_contact_entity_ids": list(population.non_fits_excluded),
        "best_claim_by_entity": best_claims,
        "contacting_at_least_one_triad_residue": counts[1],
        "contacting_at_least_two_triad_residues": counts[2],
        "contacting_all_three_triad_residues": counts[3],
        "counted_over": "entities; affinity-best receptor; non-fits counted as zero contact",
    }


def speb_rows(manifest: Mapping[str, Any]) -> list[dict[str, Any]]:
    prep = _prep_by_species(manifest)
    rows = []
    for row in manifest["results"]:
        item = dict(row)
        item["heavy_atom_count"] = int(prep[_species_tuple(row)]["heavy_atom_count"])
        item["ligand_efficiency_kcal_mol_per_heavy_atom"] = (
            float(item[RAW_AFFINITY]) / item["heavy_atom_count"]
        )
        rows.append(item)
    return rows


def competition_rank(positive: float, values: Sequence[float]) -> int:
    return 1 + sum(float(value) < float(positive) for value in values)


def verify_statistics_document(stats: Mapping[str, Any], population: AnalysisPopulation) -> None:
    if stats.get("analysis_schema_version") != ANALYSIS_SCHEMA_VERSION:
        raise DockingError("Docking statistics schema version mismatch.")
    if stats.get("population_rule_id") != POPULATION_RULE_ID:
        raise DockingError("Docking statistics population-rule mismatch.")
    if stats.get("source_hashes") != dict(population.source_hashes):
        raise DockingError("Docking statistics source hashes do not match analysis inputs.")
    if stats.get("population_hash") != population.population_hash:
        raise DockingError("Docking statistics population hash mismatch.")
    expected = {
        workflow: population_block(pop)
        for workflow, pop in sorted(population.populations.items())
    }
    if stats.get("populations") != expected:
        raise DockingError("Docking statistics populations do not match analysis inputs.")


def _workflow_population(
    manifest: Mapping[str, Any],
    attempt_manifest: Mapping[str, Any],
    ambiguous_entity_ids: Sequence[str],
) -> WorkflowPopulation:
    workflow = str(manifest["workflow"])
    attempted = _workflow_attempted_entities(attempt_manifest, workflow)
    valid_fit = tuple(sorted({str(row["entity_id"]) for row in manifest["run_records"] if row["valid_fit"]}))
    ambiguous_in_scope = tuple(sorted(set(attempted) & set(ambiguous_entity_ids)))
    analysis_eligible = tuple(entity for entity in attempted if entity not in ambiguous_in_scope)
    numeric = tuple(entity for entity in analysis_eligible if entity in valid_fit)
    non_fits = tuple(entity for entity in analysis_eligible if entity not in valid_fit)
    return WorkflowPopulation(
        workflow=workflow,
        attempted=attempted,
        valid_fit=valid_fit,
        analysis_eligible=analysis_eligible,
        numeric_analysis=numeric,
        ambiguous_excluded=ambiguous_in_scope,
        non_fits_excluded=non_fits,
    )


def _workflow_attempted_entities(
    attempt_manifest: Mapping[str, Any],
    workflow: str,
) -> tuple[str, ...]:
    return tuple(sorted({row["entity_id"] for row in attempt_manifest["attempts"] if row["workflow"] == workflow}))


def _population_json(population: WorkflowPopulation) -> dict[str, Any]:
    return {
        "attempted": {"n": len(population.attempted), "entity_ids": list(population.attempted)},
        "valid_fit": {"n": len(population.valid_fit), "entity_ids": list(population.valid_fit)},
        "analysis_eligible": {
            "n": len(population.analysis_eligible),
            "entity_ids": list(population.analysis_eligible),
        },
        "numeric_analysis": {
            "n": len(population.numeric_analysis),
            "entity_ids": list(population.numeric_analysis),
        },
        "ambiguous_excluded_entity_ids": list(population.ambiguous_excluded),
        "non_fits_excluded_entity_ids": list(population.non_fits_excluded),
    }


def _load_manifest(path: Path) -> dict[str, Any]:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    validate_manifest_timeout_qc(manifest)
    return manifest


def _load_hashed_json(path: Path) -> tuple[dict[str, Any], str]:
    raw = path.read_bytes()
    return json.loads(raw.decode("utf-8")), hashlib.sha256(raw).hexdigest()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_json_sha256(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _verify_manifest_source_hashes(
    manifest: Mapping[str, Any],
    *,
    species_catalog_sha256: str,
    attempt_manifest_sha256: str,
) -> None:
    if manifest.get("species_catalog_sha256") != species_catalog_sha256:
        raise DockingError(f"{manifest.get('workflow')} species-catalog hash mismatch.")
    if manifest.get("attempt_manifest_sha256") != attempt_manifest_sha256:
        raise DockingError(f"{manifest.get('workflow')} attempt-manifest hash mismatch.")
    for record in manifest["run_records"]:
        if record.get("run_schema_version") != RUN_SCHEMA_VERSION:
            raise DockingError("Run record schema mismatch.")
        if record.get("species_catalog_sha256") != species_catalog_sha256:
            raise DockingError(f"Run-record species-catalog hash mismatch: {record.get('claim_key')}.")
        if record.get("attempt_manifest_sha256") != attempt_manifest_sha256:
            raise DockingError(f"Run-record attempt-manifest hash mismatch: {record.get('claim_key')}.")


def _derive_ambiguous_entities(
    species_catalog: Mapping[str, Any],
    attempt_manifest: Mapping[str, Any],
) -> tuple[str, ...]:
    states_by_entity: dict[str, set[str]] = {}
    for row in attempt_manifest["attempts"]:
        states_by_entity.setdefault(str(row["entity_id"]), set()).add(str(row["state_id"]))
    attempt_ambiguous = {entity for entity, states in states_by_entity.items() if len(states) > 1}
    catalog_ambiguous = {
        str(row["entity_id"])
        for row in species_catalog["states"]
        if row.get("dock_eligible") is True and row.get("tier") == "AMBIGUOUS"
    }
    if attempt_ambiguous != catalog_ambiguous:
        raise DockingError(
            "Attempt-derived ambiguous entities differ from the dock-eligible species catalog: "
            f"attempt={sorted(attempt_ambiguous)}, catalog={sorted(catalog_ambiguous)}."
        )
    return tuple(sorted(attempt_ambiguous))


def _validate_spycep_manifest_rows(
    manifest: Mapping[str, Any],
    attempt_manifest: Mapping[str, Any],
) -> None:
    workflow = str(manifest["workflow"])
    attempt_claims = {
        _attempt_claim_key(row): row
        for row in attempt_manifest["attempts"]
        if row["workflow"] == workflow
    }
    run_records = {row["claim_key"]: row for row in manifest["run_records"]}
    if len(run_records) != len(manifest["run_records"]):
        raise DockingError(f"{workflow} contains duplicate run-record claim keys.")
    if set(run_records) != set(attempt_claims):
        raise DockingError(f"{workflow} run-record claims do not equal attempt-manifest claims.")

    valid_records = [row for row in manifest["run_records"] if row["valid_fit"]]
    valid_claims = {row["claim_key"] for row in valid_records}
    pose_claims = {row["claim_key"] for row in manifest["pose_interactions"]}
    if len(pose_claims) != len(manifest["pose_interactions"]):
        raise DockingError(f"{workflow} contains duplicate pose-interaction claim keys.")
    if pose_claims != valid_claims:
        raise DockingError(f"{workflow} pose-interaction claims do not equal valid-fit run records.")
    interactions = {row["claim_key"]: row for row in manifest["pose_interactions"]}
    for record in valid_records:
        interaction = interactions[record["claim_key"]]
        _require_same_species(interaction, record, f"{workflow} pose interaction")
        if interaction["pocket_id"] != record["pocket_id"]:
            raise DockingError(f"{workflow} pose interaction pocket mismatch for {record['claim_key']}.")
        if not math.isclose(
            float(interaction[RAW_AFFINITY]),
            float(record[RAW_AFFINITY]),
            rel_tol=0.0,
            abs_tol=1e-9,
        ):
            raise DockingError(f"{workflow} pose interaction affinity mismatch for {record['claim_key']}.")

    valid_by_species: dict[tuple[str, str], list[Mapping[str, Any]]] = {}
    for record in valid_records:
        valid_by_species.setdefault(_species_tuple(record), []).append(record)
    ranking = {_species_tuple(row): row for row in manifest["ranking"]}
    if len(ranking) != len(manifest["ranking"]):
        raise DockingError(f"{workflow} contains duplicate ranking species keys.")
    if set(ranking) != set(valid_by_species):
        raise DockingError(f"{workflow} ranking species do not equal valid-fit run-record species.")
    for species, records in valid_by_species.items():
        ranking_row = ranking[species]
        per_receptor = {
            str(record["pocket_id"]): float(record[RAW_AFFINITY])
            for record in records
        }
        best = min(per_receptor.values())
        mean_affinity = sum(per_receptor.values()) / len(per_receptor)
        first = records[0]
        _require_same_species(ranking_row, first, f"{workflow} ranking")
        if ranking_row["per_receptor_best_affinity"] != per_receptor:
            raise DockingError(f"{workflow} ranking receptor-affinity map mismatch for {species}.")
        _require_close(ranking_row[AFFINITY], best, f"{workflow} ranking ensemble best mismatch for {species}.")
        _require_close(
            ranking_row["ensemble_mean_affinity_kcal_mol"],
            mean_affinity,
            f"{workflow} ranking ensemble mean mismatch for {species}.",
        )
        heavy_atoms = int(first["heavy_atom_count"])
        _require_close(
            ranking_row[EFFICIENCY],
            best / heavy_atoms,
            f"{workflow} ranking ligand-efficiency mismatch for {species}.",
        )
        if ranking_row.get("set") != first.get("set") or ranking_row.get("role") != first.get("role"):
            raise DockingError(f"{workflow} ranking set/role mismatch for {species}.")


def _validate_speb_result_rows(
    manifest: Mapping[str, Any],
    attempt_manifest: Mapping[str, Any],
) -> None:
    attempt_claims = {
        _attempt_claim_key(row): row
        for row in attempt_manifest["attempts"]
        if row["workflow"] == "speb"
    }
    valid_records = [row for row in manifest["run_records"] if row["valid_fit"]]
    run_records = {row["claim_key"]: row for row in valid_records}
    result_claims = {row["claim_key"] for row in manifest["results"]}
    if len(result_claims) != len(manifest["results"]):
        raise DockingError("SpeB results contain duplicate claim keys.")
    if result_claims != set(run_records):
        raise DockingError("SpeB result claims do not equal valid-fit run records.")
    species_keys = [_species_tuple(row) for row in manifest["results"]]
    if len(species_keys) != len(set(species_keys)):
        raise DockingError("SpeB results contain duplicate species keys.")
    prep = _prep_by_species(manifest)
    for row in manifest["results"]:
        record = run_records[row["claim_key"]]
        attempt = attempt_claims[row["claim_key"]]
        _require_same_species(row, record, "SpeB result")
        if row.get("role") != attempt.get("role"):
            raise DockingError(f"SpeB role mismatch for {row['claim_key']}.")
        _require_close(row[RAW_AFFINITY], record[RAW_AFFINITY], f"SpeB affinity mismatch for {row['claim_key']}.")
        heavy_atoms = int(prep[_species_tuple(row)]["heavy_atom_count"])
        if int(row["heavy_atom_count"]) != heavy_atoms:
            raise DockingError(f"SpeB heavy-atom mismatch for {row['claim_key']}.")
        _require_close(
            row[EFFICIENCY],
            float(record[RAW_AFFINITY]) / heavy_atoms,
            f"SpeB ligand-efficiency mismatch for {row['claim_key']}.",
        )


def _attempt_claim_key(row: Mapping[str, Any]) -> str:
    return f"{row['workflow']}:{row['entity_id']}:{row['state_id']}:{row['pocket_id']}"


def _species_tuple(row: Mapping[str, Any]) -> tuple[str, str]:
    key = row.get("species_key")
    if isinstance(key, list) and len(key) == 2:
        return str(key[0]), str(key[1])
    return str(row["entity_id"]), str(row["state_id"])


def _prep_by_species(manifest: Mapping[str, Any]) -> dict[tuple[str, str], Mapping[str, Any]]:
    out = {_species_tuple(row): row for row in manifest["ligand_preparation"]}
    if len(out) != len(manifest["ligand_preparation"]):
        raise DockingError(f"{manifest.get('workflow')} ligand preparation contains duplicate species.")
    return out


def _require_same_species(row: Mapping[str, Any], record: Mapping[str, Any], label: str) -> None:
    if str(row["entity_id"]) != str(record["entity_id"]) or str(row["state_id"]) != str(record["state_id"]):
        raise DockingError(f"{label} species mismatch for {record.get('claim_key')}.")
    if list(row["species_key"]) != [str(record["entity_id"]), str(record["state_id"])]:
        raise DockingError(f"{label} species_key mismatch for {record.get('claim_key')}.")


def _require_close(actual: Any, expected: float, message: str) -> None:
    if not math.isclose(float(actual), float(expected), rel_tol=0.0, abs_tol=1e-9):
        raise DockingError(message)

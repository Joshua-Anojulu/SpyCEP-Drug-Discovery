"""Compute entity-level docking statistics for the sealed campaign.

Run:
    .\\.venv\\Scripts\\python.exe scripts\\compute_statistics.py
"""
from __future__ import annotations

import itertools
import json
import sys
from pathlib import Path
from statistics import mean, stdev

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from spycep_drug_discovery.analysis_population import (
    AFFINITY,
    ANALYSIS_SCHEMA_VERSION,
    EFFICIENCY,
    POPULATION_RULE_ID,
    competition_rank,
    load_analysis_population,
    numeric_ranking_rows,
    population_block,
    speb_rows,
    triad_engagement,
)
from spycep_drug_discovery.docking import require_campaign_seal
from spycep_drug_discovery.statistics_analysis import (
    bootstrap_mean_difference,
    mann_whitney,
    positive_control_margin,
)

METHODS = PROJECT_ROOT / "docs" / "methods"
OUTPUT = METHODS / "docking_statistics.json"


def _comparison(manifest: dict, population) -> dict:
    rows = numeric_ranking_rows(manifest, population)
    custom = [row for row in rows if row["set"] == "custom_anti_virulence"]
    fda = [row for row in rows if row["set"] == "fda_comparator"]
    out: dict = {
        "population_rule_id": POPULATION_RULE_ID,
        "population": "numeric_analysis",
        "non_fits_excluded": list(population.non_fits_excluded),
        "ambiguous_excluded": list(population.ambiguous_excluded),
        "custom_entity_ids": sorted(row["entity_id"] for row in custom),
        "fda_entity_ids": sorted(row["entity_id"] for row in fda),
    }
    for key, label in ((AFFINITY, "best_affinity"), (EFFICIENCY, "ligand_efficiency")):
        a = [float(row[key]) for row in custom]
        b = [float(row[key]) for row in fda]
        out[label] = {
            "custom_n": len(a),
            "fda_n": len(b),
            "custom_mean": mean(a),
            "fda_mean": mean(b),
            "bootstrap_mean_difference_custom_minus_fda": bootstrap_mean_difference(a, b),
            "mann_whitney": mann_whitney(a, b),
        }
    return out


def _metric_margin(positive: float, decoys: list[float]) -> dict:
    base = positive_control_margin(positive, decoys)
    return {
        "positive": base["positive_affinity"],
        "best_decoy": base["best_decoy_affinity"],
        "margin_to_best_decoy": base["margin_to_best_decoy"],
        "decoy_mean": base["decoy_mean"],
        "decoy_sd": base["decoy_sd"],
        "sd_stronger_than_decoy_mean": base["sd_stronger_than_decoy_mean"],
        "rank": competition_rank(positive, decoys),
        "beats_all_decoys": base["beats_all_decoys"],
    }


def _speb_positive_control(manifest: dict, population, ambiguous: tuple[str, ...]) -> dict:
    rows = speb_rows(manifest)
    positive = next(row for row in rows if row["role"] == "positive_known_inhibitor")
    protease = sorted(row["entity_id"] for row in rows if row["role"] == "protease_inhibitor_comparator")
    primary_decoys = sorted(
        [row for row in rows if row["role"] == "decoy" and row["entity_id"] not in ambiguous],
        key=lambda row: row["entity_id"],
    )
    all_decoy_entities = sorted({row["entity_id"] for row in rows if row["role"] == "decoy"})
    collapsed_decoys = []
    for entity_id in all_decoy_entities:
        candidates = [row for row in rows if row["role"] == "decoy" and row["entity_id"] == entity_id]
        collapsed_decoys.append(
            min(candidates, key=lambda row: (float(row["best_affinity_kcal_mol"]), str(row["state_id"])))
        )
    collapsed_decoys.sort(key=lambda row: row["entity_id"])

    def block(decoys: list[dict], *, extra: dict | None = None) -> dict:
        affinity = _metric_margin(
            float(positive["best_affinity_kcal_mol"]),
            [float(row["best_affinity_kcal_mol"]) for row in decoys],
        )
        efficiency = _metric_margin(
            float(positive["ligand_efficiency_kcal_mol_per_heavy_atom"]),
            [float(row["ligand_efficiency_kcal_mol_per_heavy_atom"]) for row in decoys],
        )
        return {
            **(extra or {}),
            "decoy_count": len(decoys),
            "rank_denominator": len(decoys) + 1,
            "member_entity_ids": sorted(row["entity_id"] for row in decoys),
            "by_best_affinity": affinity,
            "by_ligand_efficiency": efficiency,
            "passes_on_both_metrics": affinity["beats_all_decoys"] and efficiency["beats_all_decoys"],
        }

    primary = block(
        primary_decoys,
        extra={
            "excluded_entity_ids": sorted(set(all_decoy_entities) & set(ambiguous)),
        },
    )
    sensitivity = block(
        collapsed_decoys,
        extra={
            "collapse_rule": "lowest_affinity_state_per_entity",
            "selected_species_keys": {
                row["entity_id"]: list(row["species_key"]) for row in collapsed_decoys
            },
        },
    )
    return {
        "population_rule_id": POPULATION_RULE_ID,
        "margin_convention": "margin = best_decoy - positive; negative means the positive LOSES",
        "heavy_atom_source": "validated species-keyed ligand-preparation records",
        "comparators_outside_rank_denominator": protease,
        "decoys_are_size_matched": True,
        "positive_entity_id": positive["entity_id"],
        "positive_heavy_atom_count": int(positive["heavy_atom_count"]),
        "decoy_heavy_atom_range": [
            min(int(row["heavy_atom_count"]) for row in rows if row["role"] == "decoy"),
            max(int(row["heavy_atom_count"]) for row in rows if row["role"] == "decoy"),
        ],
        "primary_ambiguous_excluded": primary,
        "sensitivity_dual_state_collapsed": sensitivity,
    }


def _assignment_sensitivity(manifest: dict, population, ambiguous: tuple[str, ...]) -> dict:
    rows = [row for row in manifest["ranking"] if row["entity_id"] in population.valid_fit]
    by_entity: dict[str, list[dict]] = {}
    for row in rows:
        by_entity.setdefault(row["entity_id"], []).append(row)
    variable_entities = sorted(entity for entity in ambiguous if entity in by_entity)
    fixed_fda = [
        rows[0]
        for entity, rows in sorted(by_entity.items())
        if rows[0]["set"] == "fda_comparator" and entity not in variable_entities and entity != "vancomycin"
    ]
    custom = [
        rows[0]
        for entity, rows in sorted(by_entity.items())
        if rows[0]["set"] == "custom_anti_virulence"
    ]
    summaries = {
        "assignment_count": 2 ** len(variable_entities),
        "ambiguous_entity_ids": variable_entities,
        "fda_valid_fit_n": len(fixed_fda) + len(variable_entities),
        "custom_n": len(custom),
    }
    for key, label in ((AFFINITY, "best_affinity"), (EFFICIENCY, "ligand_efficiency")):
        diffs = []
        p_values = []
        for choices in itertools.product(*[sorted(by_entity[entity], key=lambda row: row["state_id"]) for entity in variable_entities]):
            fda = fixed_fda + list(choices)
            a = [float(row[key]) for row in custom]
            b = [float(row[key]) for row in fda]
            diffs.append(mean(a) - mean(b))
            p_values.append(mann_whitney(a, b)["p_value"])
        summaries[label] = {
            "mean_difference_custom_minus_fda_range": [min(diffs), max(diffs)],
            "mann_whitney_p_value_range": [min(p_values), max(p_values)],
        }
    return summaries


def _worst_rank_sensitivity(manifest: dict, population) -> dict:
    rows = numeric_ranking_rows(manifest, population)
    fda_entities = set(row["entity_id"] for row in rows if row["set"] == "fda_comparator")
    out = {
        "rule": "vancomycin placed strictly below every valid-fit comparator for rank testing only",
        "vancomycin_synthetic_value_enters_means": False,
    }
    for key, label in ((AFFINITY, "best_affinity"), (EFFICIENCY, "ligand_efficiency")):
        ordered = sorted(rows, key=lambda row: (float(row[key]), row["entity_id"]))
        rank_scores = {row["entity_id"]: index + 1 for index, row in enumerate(ordered)}
        rank_scores["vancomycin"] = len(ordered) + 1
        custom_scores = [
            score for entity, score in rank_scores.items()
            if entity not in fda_entities and entity != "vancomycin"
        ]
        fda_scores = [score for entity, score in rank_scores.items() if entity in fda_entities or entity == "vancomycin"]
        out[label] = {
            "custom_n": len(custom_scores),
            "fda_n_including_vancomycin": len(fda_scores),
            "mann_whitney": mann_whitney(custom_scores, fda_scores),
        }
    return out


def _software_versions() -> dict[str, str]:
    import numpy
    import scipy

    return {
        "numpy": numpy.__version__,
        "scipy": scipy.__version__,
    }


def main() -> None:
    population = load_analysis_population(PROJECT_ROOT)
    wide = population.manifests["wide"]
    tight = population.manifests["tight"]
    seal = require_campaign_seal(PROJECT_ROOT, str(wide["campaign_id"]))
    populations = {
        workflow: population_block(pop)
        for workflow, pop in sorted(population.populations.items())
    }
    stats = {
        "analysis_schema_version": ANALYSIS_SCHEMA_VERSION,
        "population_rule_id": POPULATION_RULE_ID,
        "campaign_id": wide["campaign_id"],
        "campaign_seal_schema_version": seal["seal_schema_version"],
        "campaign_ledger_content_sha256": seal["ledger_content_sha256"],
        "note": (
            "More negative affinity/efficiency = stronger. Bootstrap = 95% CI, "
            "10000 entity resamples, seed 42. Primary set-level statistics exclude "
            "AMBIGUOUS entities at analysis time."
        ),
        "source_hashes": dict(population.source_hashes),
        "population_hash": population.population_hash,
        "populations": populations,
        "software_versions": _software_versions(),
        "custom_vs_fda_wide_box": _comparison(wide, population.populations["wide"]),
        "custom_vs_fda_tight_box": _comparison(tight, population.populations["tight"]),
        "triad_engagement_wide_box": triad_engagement(wide, population.populations["wide"]),
        "triad_engagement_tight_box": triad_engagement(tight, population.populations["tight"]),
        "speb_positive_control": _speb_positive_control(
            population.manifests["speb"],
            population.populations["speb"],
            population.ambiguous_entity_ids,
        ),
        "full_valid_fit_fda_population_sensitivity": {
            "wide_box": _assignment_sensitivity(wide, population.populations["wide"], population.ambiguous_entity_ids),
            "tight_box": _assignment_sensitivity(tight, population.populations["tight"], population.ambiguous_entity_ids),
        },
        "vancomycin_worst_rank_sensitivity": {
            "wide_box": _worst_rank_sensitivity(wide, population.populations["wide"]),
            "tight_box": _worst_rank_sensitivity(tight, population.populations["tight"]),
        },
    }
    OUTPUT.write_text(json.dumps(stats, indent=2) + "\n", encoding="utf-8")

    for box in ("wide", "tight"):
        b = stats[f"custom_vs_fda_{box}_box"]["best_affinity"]
        d = b["bootstrap_mean_difference_custom_minus_fda"]
        print(
            f"{box:>5} box  custom n={b['custom_n']} mean {b['custom_mean']:.2f} vs "
            f"FDA n={b['fda_n']} mean {b['fda_mean']:.2f}  diff {d['observed_difference']:+.3f} "
            f"[{d['ci95_low']:.3f}, {d['ci95_high']:.3f}]  p={b['mann_whitney']['p_value']:.3f}"
        )
    pc = stats["speb_positive_control"]
    primary = pc["primary_ambiguous_excluded"]
    sensitivity = pc["sensitivity_dual_state_collapsed"]
    print(
        "\nSpeB control primary: "
        f"Q9D affinity rank {primary['by_best_affinity']['rank']}/{primary['rank_denominator']}, "
        f"LE rank {primary['by_ligand_efficiency']['rank']}/{primary['rank_denominator']}"
    )
    print(
        "SpeB control sensitivity: "
        f"Q9D affinity rank {sensitivity['by_best_affinity']['rank']}/{sensitivity['rank_denominator']}, "
        f"LE rank {sensitivity['by_ligand_efficiency']['rank']}/{sensitivity['rank_denominator']}"
    )
    print(f"\nWrote {OUTPUT.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()

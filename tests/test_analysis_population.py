from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from spycep_drug_discovery.analysis_population import (
    _derive_ambiguous_entities,
    _validate_speb_result_rows,
    _validate_spycep_manifest_rows,
    _verify_manifest_source_hashes,
    load_analysis_population,
    triad_engagement,
    verify_statistics_document,
)
from spycep_drug_discovery.docking import DockingError


PROJECT_ROOT = Path(__file__).resolve().parents[1]
METHODS = PROJECT_ROOT / "docs" / "methods"


def _stats() -> dict:
    return json.loads((METHODS / "docking_statistics.json").read_text(encoding="utf-8"))


def test_entity_populations_match_sealed_campaign_golden_counts():
    population = load_analysis_population(PROJECT_ROOT)

    assert population.ambiguous_entity_ids == (
        "amoxicillin",
        "ampicillin",
        "cephalexin",
        "lisinopril",
    )
    for workflow in ("wide", "tight"):
        block = population.populations[workflow]
        assert len(block.attempted) == 73
        assert len(block.valid_fit) == 72
        assert len(block.analysis_eligible) == 69
        assert len(block.numeric_analysis) == 68
        assert block.ambiguous_excluded == population.ambiguous_entity_ids
        assert block.non_fits_excluded == ("vancomycin",)
        assert "vancomycin" in block.analysis_eligible
        assert "vancomycin" not in block.numeric_analysis


def test_triad_counts_use_analysis_eligible_best_receptor_population():
    population = load_analysis_population(PROJECT_ROOT)

    wide = triad_engagement(population.manifests["wide"], population.populations["wide"])
    tight = triad_engagement(population.manifests["tight"], population.populations["tight"])

    assert (wide["ligands"], wide["contacting_at_least_one_triad_residue"]) == (69, 62)
    assert wide["contacting_at_least_two_triad_residues"] == 51
    assert wide["contacting_all_three_triad_residues"] == 31
    assert (tight["ligands"], tight["contacting_at_least_one_triad_residue"]) == (69, 68)
    assert tight["contacting_at_least_two_triad_residues"] == 56
    assert tight["contacting_all_three_triad_residues"] == 31
    assert wide["best_claim_by_entity"]["vancomycin"] is None


def test_statistics_file_has_entity_level_golden_numbers():
    population = load_analysis_population(PROJECT_ROOT)
    stats = _stats()

    verify_statistics_document(stats, population)
    wide = stats["custom_vs_fda_wide_box"]
    tight = stats["custom_vs_fda_tight_box"]
    assert wide["best_affinity"]["custom_n"] == 18
    assert wide["best_affinity"]["fda_n"] == 50
    assert wide["best_affinity"]["custom_mean"] == pytest.approx(-5.828833333333333)
    assert wide["best_affinity"]["fda_mean"] == pytest.approx(-6.09942)
    assert wide["best_affinity"]["mann_whitney"]["p_value"] == pytest.approx(0.30691314464412844)
    assert tight["best_affinity"]["custom_n"] == 18
    assert tight["best_affinity"]["fda_n"] == 50
    assert tight["best_affinity"]["custom_mean"] == pytest.approx(-5.5945)
    assert tight["best_affinity"]["fda_mean"] == pytest.approx(-5.8746)
    assert tight["best_affinity"]["mann_whitney"]["p_value"] == pytest.approx(0.2631284689551995)


def test_speb_primary_and_collapsed_sensitivity_golden_numbers():
    stats = _stats()["speb_positive_control"]
    primary = stats["primary_ambiguous_excluded"]
    sensitivity = stats["sensitivity_dual_state_collapsed"]

    assert primary["decoy_count"] == 14
    assert primary["rank_denominator"] == 15
    assert primary["excluded_entity_ids"] == ["amoxicillin", "ampicillin", "cephalexin"]
    assert primary["by_best_affinity"]["rank"] == 2
    assert primary["by_ligand_efficiency"]["rank"] == 4
    assert primary["by_best_affinity"]["margin_to_best_decoy"] == pytest.approx(-0.093)
    assert sensitivity["decoy_count"] == 17
    assert sensitivity["rank_denominator"] == 18
    assert sensitivity["by_best_affinity"]["rank"] == 4
    assert sensitivity["by_ligand_efficiency"]["rank"] == 7
    assert sensitivity["by_best_affinity"]["margin_to_best_decoy"] == pytest.approx(-0.231)


def test_assignment_sensitivity_reports_all_16_assignments_for_both_metrics():
    sensitivity = _stats()["full_valid_fit_fda_population_sensitivity"]

    assert sensitivity["wide_box"]["assignment_count"] == 16
    assert sensitivity["wide_box"]["fda_valid_fit_n"] == 54
    assert sensitivity["wide_box"]["best_affinity"]["mann_whitney_p_value_range"] == pytest.approx(
        [0.22401255125227804, 0.255162223665532]
    )
    assert sensitivity["tight_box"]["best_affinity"]["mann_whitney_p_value_range"] == pytest.approx(
        [0.17831116209859765, 0.19568099770243874]
    )
    assert "ligand_efficiency" in sensitivity["wide_box"]
    assert "ligand_efficiency" in sensitivity["tight_box"]


def test_vancomycin_worst_rank_sensitivity_keeps_means_clean():
    worst = _stats()["vancomycin_worst_rank_sensitivity"]

    for box in ("wide_box", "tight_box"):
        assert worst[box]["vancomycin_synthetic_value_enters_means"] is False
        assert worst[box]["best_affinity"]["fda_n_including_vancomycin"] == 51
        assert worst[box]["ligand_efficiency"]["fda_n_including_vancomycin"] == 51


def test_ranking_pose_and_speb_deletions_fail_closed():
    population = load_analysis_population(PROJECT_ROOT)
    attempt = population.attempt_manifest

    wide_missing_ranking = copy.deepcopy(population.manifests["wide"])
    wide_missing_ranking["ranking"] = wide_missing_ranking["ranking"][1:]
    with pytest.raises(DockingError, match="ranking species"):
        _validate_spycep_manifest_rows(wide_missing_ranking, attempt)

    wide_missing_pose = copy.deepcopy(population.manifests["wide"])
    wide_missing_pose["pose_interactions"] = wide_missing_pose["pose_interactions"][1:]
    with pytest.raises(DockingError, match="pose-interaction claims"):
        _validate_spycep_manifest_rows(wide_missing_pose, attempt)

    speb_missing_result = copy.deepcopy(population.manifests["speb"])
    speb_missing_result["results"] = speb_missing_result["results"][1:]
    with pytest.raises(DockingError, match="SpeB result claims"):
        _validate_speb_result_rows(speb_missing_result, attempt)


def test_duplicate_and_content_mismatch_corruptions_fail_closed():
    population = load_analysis_population(PROJECT_ROOT)
    attempt = population.attempt_manifest

    duplicate_pose = copy.deepcopy(population.manifests["wide"])
    duplicate_pose["pose_interactions"].append(copy.deepcopy(duplicate_pose["pose_interactions"][0]))
    with pytest.raises(DockingError, match="duplicate pose-interaction"):
        _validate_spycep_manifest_rows(duplicate_pose, attempt)

    mismatched_ranking = copy.deepcopy(population.manifests["wide"])
    mismatched_ranking["ranking"][0]["ensemble_best_affinity_kcal_mol"] = -999.0
    with pytest.raises(DockingError, match="ensemble best mismatch"):
        _validate_spycep_manifest_rows(mismatched_ranking, attempt)

    duplicate_speb = copy.deepcopy(population.manifests["speb"])
    duplicate_speb["results"].append(copy.deepcopy(duplicate_speb["results"][0]))
    with pytest.raises(DockingError, match="duplicate claim"):
        _validate_speb_result_rows(duplicate_speb, attempt)

    speb_mismatch = copy.deepcopy(population.manifests["speb"])
    speb_mismatch["results"][0]["heavy_atom_count"] += 1
    with pytest.raises(DockingError, match="heavy-atom mismatch"):
        _validate_speb_result_rows(speb_mismatch, attempt)


def test_hash_ambiguous_state_and_stale_statistics_corruptions_fail_closed():
    population = load_analysis_population(PROJECT_ROOT)
    manifest = population.manifests["wide"]

    with pytest.raises(DockingError, match="species-catalog hash mismatch"):
        _verify_manifest_source_hashes(
            manifest,
            species_catalog_sha256="0" * 64,
            attempt_manifest_sha256=population.source_hashes["attempt_manifest.json"],
        )

    omitted_state_attempt = copy.deepcopy(population.attempt_manifest)
    omitted_state_attempt["attempts"] = [
        row
        for row in omitted_state_attempt["attempts"]
        if not (row["entity_id"] == "amoxicillin" and row["state_id"] == "alpha_ammonium")
    ]
    with pytest.raises(DockingError, match="Attempt-derived ambiguous"):
        _derive_ambiguous_entities(population.species_catalog, omitted_state_attempt)

    stale_stats = copy.deepcopy(_stats())
    stale_stats["population_hash"] = "0" * 64
    with pytest.raises(DockingError, match="population hash mismatch"):
        verify_statistics_document(stale_stats, population)

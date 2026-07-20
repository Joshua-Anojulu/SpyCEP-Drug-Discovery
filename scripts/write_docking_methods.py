"""Generate the tracked docking methods/results note from validated manifests.

Run:
    .\\.venv\\Scripts\\python.exe scripts\\write_docking_methods.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from spycep_drug_discovery.analysis_population import (
    AFFINITY,
    EFFICIENCY,
    load_analysis_population,
    numeric_ranking_rows,
    verify_statistics_document,
)
from spycep_drug_discovery.docking import (
    DockingError,
    require_campaign_seal,
    validate_campaign_manifest_set,
)

METHODS = PROJECT_ROOT / "docs" / "methods"
STATS = METHODS / "docking_statistics.json"
OUTPUT = METHODS / "docking_analysis.md"


def _load_json(name: str) -> dict:
    return json.loads((METHODS / name).read_text(encoding="utf-8"))


def _stats(population) -> dict:
    stats = json.loads(STATS.read_text(encoding="utf-8"))
    verify_statistics_document(stats, population)
    return stats


def _top_rows(manifest: dict, population, n: int = 10) -> list[str]:
    lines = [
        "| Rank | Ligand | Set | Charge | Ligand efficiency | Best (kcal/mol) |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    charges = {
        tuple(row["species_key"]): int(row["formal_charge"])
        for row in manifest.get("ligand_preparation", [])
    }
    ranked = sorted(numeric_ranking_rows(manifest, population), key=lambda row: (row[EFFICIENCY], row["entity_id"]))
    for rank, row in enumerate(ranked[:n], start=1):
        label = "custom" if row["set"] == "custom_anti_virulence" else "FDA"
        charge = charges[tuple(row["species_key"])]
        lines.append(
            f"| {rank} | {row['ligand_id']} | {label} | {charge:+d} | "
            f"{row[EFFICIENCY]:.3f} | {row[AFFINITY]:.2f} |"
        )
    return lines


def _box_basis() -> dict:
    wide = _load_json("pocket_definition.json")
    tight = _load_json("tight_pocket_definition.json")
    speb = _load_json("speb_pocket_definition.json")
    return {
        "wide": f"{wide['minimum_box_size_angstrom']:.0f} A receptor-preparation boxes",
        "tight": tight["basis"],
        "speb": speb["pockets"][0]["box_basis"],
    }


def _fmt_ci(block: dict) -> str:
    ci = block["bootstrap_mean_difference_custom_minus_fda"]
    return f"[{ci['ci95_low']:.2f}, {ci['ci95_high']:.2f}]"


def main() -> None:
    population = load_analysis_population(PROJECT_ROOT)
    wide = population.manifests["wide"]
    tight = population.manifests["tight"]
    speb = population.manifests["speb"]
    boron = population.manifests["boron"]
    validate_campaign_manifest_set((wide, tight, speb, boron))
    seal = require_campaign_seal(PROJECT_ROOT, str(wide["campaign_id"]))
    stats = _stats(population)
    if (
        stats.get("campaign_id") != seal["campaign_id"]
        or stats.get("campaign_ledger_content_sha256") != seal["ledger_content_sha256"]
    ):
        raise DockingError("Docking statistics do not match the sealed campaign.")

    library = _load_json("compound_library.json")
    boxes = _box_basis()
    wide_meta = wide["metadata"]
    sw = wide["software_versions"]
    wide_pop = population.populations["wide"]
    tight_pop = population.populations["tight"]
    charged_entities = sorted(
        {
            row["entity_id"]
            for row in wide["ligand_preparation"]
            if int(row["formal_charge"]) != 0
        }
    )
    stereo = sorted(
        {
            row["entity_id"]
            for row in wide["ligand_preparation"]
            if int(row["undefined_stereocenter_count"]) > 0
        }
    )

    ws = stats["custom_vs_fda_wide_box"]
    ts = stats["custom_vs_fda_tight_box"]
    pc = stats["speb_positive_control"]
    primary = pc["primary_ambiguous_excluded"]
    sensitivity = pc["sensitivity_dual_state_collapsed"]
    assignment = stats["full_valid_fit_fda_population_sensitivity"]
    worst = stats["vancomycin_worst_rank_sensitivity"]

    lines = [
        "# Docking Methods And Results Note",
        "",
        "Generated from tracked manifests by `scripts/write_docking_methods.py`.",
        "Computational prioritization only; not evidence of binding or efficacy.",
        "",
        "## Pipeline",
        "",
        "SMILES (PubChem) -> desalt -> assign pH 7.4 species from the preregistered pKa "
        "rule set -> RDKit ETKDGv3 3D -> MMFF94 -> Meeko `mk_prepare_ligand` -> "
        f"{sw['vina']} (exhaustiveness {wide_meta['exhaustiveness']}, {wide_meta['num_modes']} modes, "
        f"seed {wide_meta['seed']}, timeout {wide_meta['timeout_seconds']:.0f} s) over the 5XYA + 7EDD "
        "ensemble -> ligand-efficiency ranking -> per-residue catalytic-triad interaction analysis.",
        "",
        f"The design library contains {library['compound_count']} compounds: "
        f"{library['counts_by_set']['custom_anti_virulence']} custom chemotypes and "
        f"{library['counts_by_set']['fda_comparator']} FDA comparators. Four FDA comparators "
        "(amoxicillin, ampicillin, cephalexin and lisinopril) have no established dominant "
        "state at pH 7.4, so both plausible states were docked and those entities are excluded "
        "from primary set-level statistics.",
        "",
        f"{len(charged_entities)} of {len(wide['ligand_preparation'])} prepared species carry a formal "
        "charge. The custom set is dominated by amidines and guanidines, which are cations at "
        "physiological pH; the S1 salt bridge is their binding rationale.",
        "",
        f"Two SpyCEP search boxes were used: {boxes['wide']}, and a tight box based on {boxes['tight']}.",
        "",
        "## Full-library result (wide box)",
        "",
        f"- Attempted population: {len(wide_pop.attempted)} entities; valid-fit population: "
        f"{len(wide_pop.valid_fit)} entities; numeric analysis population: "
        f"{len(wide_pop.numeric_analysis)} entities ({ws['best_affinity']['custom_n']} custom, "
        f"{ws['best_affinity']['fda_n']} FDA).",
        f"- Non-fits excluded from numeric means/tests: {', '.join(wide_pop.non_fits_excluded)}.",
        f"- Custom vs FDA mean best affinity: {ws['best_affinity']['custom_mean']:.2f} vs "
        f"{ws['best_affinity']['fda_mean']:.2f} kcal/mol; CI "
        f"{_fmt_ci(ws['best_affinity'])}; Mann-Whitney p = {ws['best_affinity']['mann_whitney']['p_value']:.3f}.",
        f"- Custom vs FDA mean ligand efficiency: {ws['ligand_efficiency']['custom_mean']:.3f} vs "
        f"{ws['ligand_efficiency']['fda_mean']:.3f}; CI {_fmt_ci(ws['ligand_efficiency'])}; "
        f"Mann-Whitney p = {ws['ligand_efficiency']['mann_whitney']['p_value']:.3f}.",
        "",
        "Top 10 by ligand efficiency in the primary numeric population:",
        "",
        *_top_rows(wide, wide_pop),
        "",
        "## Tight triad-centred box (robustness check)",
        "",
        f"- Attempted population: {len(tight_pop.attempted)} entities; valid-fit population: "
        f"{len(tight_pop.valid_fit)} entities; numeric analysis population: "
        f"{len(tight_pop.numeric_analysis)} entities ({ts['best_affinity']['custom_n']} custom, "
        f"{ts['best_affinity']['fda_n']} FDA).",
        f"- Custom vs FDA mean best affinity: {ts['best_affinity']['custom_mean']:.2f} vs "
        f"{ts['best_affinity']['fda_mean']:.2f} kcal/mol; CI "
        f"{_fmt_ci(ts['best_affinity'])}; Mann-Whitney p = {ts['best_affinity']['mann_whitney']['p_value']:.3f}.",
        f"- Custom vs FDA mean ligand efficiency: {ts['ligand_efficiency']['custom_mean']:.3f} vs "
        f"{ts['ligand_efficiency']['fda_mean']:.3f}; CI {_fmt_ci(ts['ligand_efficiency'])}; "
        f"Mann-Whitney p = {ts['ligand_efficiency']['mann_whitney']['p_value']:.3f}.",
        "",
        "## Catalytic-triad engagement",
        "",
        "Counted per entity over the affinity-best receptor. Vancomycin is retained as a "
        "zero-contact non-fit in the 69-entity analysis-eligible denominator.",
        "",
        "| Box | >=1 triad residue | >=2 residues | all 3 residues |",
        "| --- | --- | --- | --- |",
    ]
    for key, label in (("triad_engagement_wide_box", "Wide"), ("triad_engagement_tight_box", "Tight")):
        triad = stats[key]
        lines.append(
            f"| {label} | {triad['contacting_at_least_one_triad_residue']}/{triad['ligands']} | "
            f"{triad['contacting_at_least_two_triad_residues']}/{triad['ligands']} | "
            f"{triad['contacting_all_three_triad_residues']}/{triad['ligands']} |"
        )

    lines += [
        "",
        "## SpeB positive control",
        "",
        f"- Box: {boxes['speb']}.",
        f"- Design panel: 17 decoy entities size-matched to Q9D plus two protease comparators "
        f"outside the rank denominator ({', '.join(pc['comparators_outside_rank_denominator'])}).",
        f"- Primary population: {primary['decoy_count']} single-state decoys; excluded ambiguous "
        f"decoys: {', '.join(primary['excluded_entity_ids'])}.",
        f"- By best affinity: Q9D {primary['by_best_affinity']['positive']:.3f} kcal/mol, "
        f"best decoy {primary['by_best_affinity']['best_decoy']:.3f}; rank "
        f"{primary['by_best_affinity']['rank']}/{primary['rank_denominator']}; "
        f"margin {primary['by_best_affinity']['margin_to_best_decoy']:.3f}.",
        f"- By ligand efficiency: Q9D {primary['by_ligand_efficiency']['positive']:.3f}, "
        f"best decoy {primary['by_ligand_efficiency']['best_decoy']:.3f}; rank "
        f"{primary['by_ligand_efficiency']['rank']}/{primary['rank_denominator']}; "
        f"margin {primary['by_ligand_efficiency']['margin_to_best_decoy']:.3f}.",
        f"- Collapsed sensitivity: {sensitivity['decoy_count']} decoys, Q9D rank "
        f"{sensitivity['by_best_affinity']['rank']}/{sensitivity['rank_denominator']} by affinity "
        f"and {sensitivity['by_ligand_efficiency']['rank']}/{sensitivity['rank_denominator']} by "
        f"ligand efficiency; affinity margin "
        f"{sensitivity['by_best_affinity']['margin_to_best_decoy']:.3f}.",
        f"- Passes on both primary metrics: {primary['passes_on_both_metrics']}.",
        "",
        "## Ambiguous-state and non-fit sensitivities",
        "",
        f"- The full valid-fit FDA sensitivity enumerates {assignment['wide_box']['assignment_count']} "
        "one-state-per-ambiguous-entity assignments over 54 FDA comparators. Affinity p-value "
        f"ranges are {assignment['wide_box']['best_affinity']['mann_whitney_p_value_range'][0]:.3f}-"
        f"{assignment['wide_box']['best_affinity']['mann_whitney_p_value_range'][1]:.3f} wide and "
        f"{assignment['tight_box']['best_affinity']['mann_whitney_p_value_range'][0]:.3f}-"
        f"{assignment['tight_box']['best_affinity']['mann_whitney_p_value_range'][1]:.3f} tight.",
        f"- Ligand-efficiency p-value ranges are "
        f"{assignment['wide_box']['ligand_efficiency']['mann_whitney_p_value_range'][0]:.3f}-"
        f"{assignment['wide_box']['ligand_efficiency']['mann_whitney_p_value_range'][1]:.3f} wide and "
        f"{assignment['tight_box']['ligand_efficiency']['mann_whitney_p_value_range'][0]:.3f}-"
        f"{assignment['tight_box']['ligand_efficiency']['mann_whitney_p_value_range'][1]:.3f} tight.",
        f"- Worst-rank vancomycin sensitivity keeps synthetic values out of means/CIs. "
        f"Affinity p-values are {worst['wide_box']['best_affinity']['mann_whitney']['p_value']:.3f} "
        f"wide and {worst['tight_box']['best_affinity']['mann_whitney']['p_value']:.3f} tight; "
        f"ligand-efficiency p-values are "
        f"{worst['wide_box']['ligand_efficiency']['mann_whitney']['p_value']:.3f} wide and "
        f"{worst['tight_box']['ligand_efficiency']['mann_whitney']['p_value']:.3f} tight.",
        "",
    ]

    best = min(boron["results"], key=lambda row: row["best_affinity_kcal_mol"])
    lines += [
        "## Boron gem-diol surrogates",
        "",
        f"- {boron['metadata']['method']}",
        f"- Best surrogate: {best['source_parent_entity_id']} at {best['best_affinity_kcal_mol']:.2f} kcal/mol "
        f"({best['pocket_id']}). Approximation only; see `boron_surrogate_result.json`.",
        "",
        "## Limitations",
        "",
        "- Predictions are not evidence of inhibition or efficacy; no therapeutic claim is made.",
        "- Vina affinity is size-biased; ligand efficiency mitigates but does not remove this.",
        "- Boron compounds have no MMFF94 or Vina parameters and are handled only as gem-diol surrogates.",
        "- Rigid-receptor, single-conformer docking ignores protein flexibility.",
        "- Custom positives are general protease motifs, not validated SpyCEP binders.",
        "- Vancomycin is a real non-fit outcome in both SpyCEP boxes and is absent from mean-based comparisons.",
        f"- {len(stereo)} entities carry an unspecified stereocentre that ETKDG assigned arbitrarily "
        f"({', '.join(stereo)}); the docked isomer is recorded as `embedded_isomeric_smiles`.",
        "",
    ]
    OUTPUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()

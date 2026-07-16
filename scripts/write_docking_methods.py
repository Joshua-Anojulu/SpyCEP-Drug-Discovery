"""Generate the tracked docking methods/results note from tracked manifests.

Writes docs/methods/docking_analysis.md. Numbers are read from the tracked result
manifests so the note cannot drift from the data.

Run:
    .\\.venv\\Scripts\\python.exe scripts\\write_docking_methods.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from statistics import mean

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from spycep_drug_discovery.docking import validate_campaign_manifest_set

METHODS = PROJECT_ROOT / "docs" / "methods"
WIDE = METHODS / "docking_result.json"
TIGHT = METHODS / "docking_result_tight.json"
BORON = METHODS / "boron_surrogate_result.json"
SPEB = METHODS / "speb_positive_control_result.json"
STATS = METHODS / "docking_statistics.json"
OUTPUT = METHODS / "docking_analysis.md"

AFFINITY = "ensemble_best_affinity_kcal_mol"
EFFICIENCY = "ligand_efficiency_kcal_mol_per_heavy_atom"


def _set_stats(result: dict) -> dict:
    ranking = [r for r in result["ranking"] if r[AFFINITY] < 0]
    cu = [r for r in ranking if r["set"] == "custom_anti_virulence"]
    fd = [r for r in ranking if r["set"] == "fda_comparator"]
    return {
        "custom_n": len(cu),
        "fda_n": len(fd),
        "custom_best": mean(r[AFFINITY] for r in cu),
        "fda_best": mean(r[AFFINITY] for r in fd),
        "custom_le": mean(r[EFFICIENCY] for r in cu),
        "fda_le": mean(r[EFFICIENCY] for r in fd),
        "range": (min(r[AFFINITY] for r in ranking), max(r[AFFINITY] for r in ranking)),
    }


def _top_rows(result: dict, n: int = 10) -> list[str]:
    lines = ["| Rank | Ligand | Set | Charge | Ligand efficiency | Best (kcal/mol) |",
             "| --- | --- | --- | --- | --- | --- |"]
    charges = {r["ligand_id"]: r["formal_charge"] for r in result.get("ligand_preparation", [])}
    for r in [row for row in result["ranking"] if row[AFFINITY] < 0][:n]:
        s = "custom" if r["set"] == "custom_anti_virulence" else "FDA"
        q = charges.get(r["ligand_id"])
        lines.append(
            f"| {r['rank']} | {r['ligand_id']} | {s} | {q:+d} | "
            f"{r[EFFICIENCY]:.3f} | {r[AFFINITY]:.2f} |"
        )
    return lines


def main() -> None:
    wide = json.loads(WIDE.read_text(encoding="utf-8"))
    tight = json.loads(TIGHT.read_text(encoding="utf-8"))
    stats = json.loads(STATS.read_text(encoding="utf-8"))
    speb = json.loads(SPEB.read_text(encoding="utf-8"))
    boron = json.loads(BORON.read_text(encoding="utf-8")) if BORON.exists() else None
    validate_campaign_manifest_set(
        (wide, tight, speb, *((boron,) if boron else ()))
    )

    ws, ts = _set_stats(wide), _set_stats(tight)
    charged = sum(1 for r in wide["ligand_preparation"] if r["formal_charge"] != 0)
    stereo = [r["ligand_id"] for r in wide["ligand_preparation"] if r["undefined_stereocenter_count"]]

    lines = [
        "# Docking Methods And Results Note",
        "",
        "Generated from tracked manifests by `scripts/write_docking_methods.py`.",
        "Computational prioritization only; not evidence of binding or efficacy.",
        "",
        "## Pipeline",
        "",
        "SMILES (PubChem) -> desalt -> protonate to the dominant microspecies at pH "
        f"{wide['protonation_ph']} ({wide['protonation_tool']}) -> RDKit ETKDGv3 (seed "
        f"{wide['seed']}) 3D -> MMFF94 -> Meeko `mk_prepare_ligand` -> {wide['vina_version']} "
        f"(exhaustiveness {wide['exhaustiveness']}, {wide['num_modes']} modes, seed {wide['seed']}) "
        "over the 5XYA + 7EDD ensemble -> ligand-efficiency ranking -> per-residue "
        "catalytic-triad interaction analysis.",
        "",
        f"Ligands are docked as their charge state at pH 7.4, not as the neutral PubChem "
        f"depiction: {charged} of {len(wide['ligand_preparation'])} prepared compounds carry a formal "
        "charge. The custom set is dominated by amidines and guanidines, which are cations at "
        "physiological pH; the S1 salt bridge is their entire binding rationale.",
        "",
        "Two search boxes were used: the wide receptor-preparation box, and a tight box centred on "
        "the D151/H279/S617 **side-chain** centroid (`tight_pocket_definition.json`).",
        "",
        "## Full-library result (wide box)",
        "",
        f"- Compounds docked: {wide['compounds_docked']}/{wide['compounds_input']}. "
        f"Preparation failures: {len(wide['prep_failures'])}; docking failures: {len(wide['dock_failures'])}.",
        f"- Affinity range: {ws['range'][0]:.2f} to {ws['range'][1]:.2f} kcal/mol.",
        f"- Custom (n={ws['custom_n']}) vs FDA (n={ws['fda_n']}) mean best affinity: "
        f"{ws['custom_best']:.2f} vs {ws['fda_best']:.2f} kcal/mol.",
        f"- Custom vs FDA mean ligand efficiency: {ws['custom_le']:.3f} vs {ws['fda_le']:.3f}.",
        "",
        "Top 10 by ligand efficiency:",
        "",
        *_top_rows(wide),
        "",
        "## Tight triad-centred box (robustness check)",
        "",
        f"- Compounds docked: {tight['compounds_docked']}/{tight['compounds_input']}.",
        f"- Custom (n={ts['custom_n']}) vs FDA (n={ts['fda_n']}) mean best affinity: "
        f"{ts['custom_best']:.2f} vs {ts['fda_best']:.2f} kcal/mol "
        "(non-fits with non-negative affinity are excluded).",
        f"- Custom vs FDA mean ligand efficiency: {ts['custom_le']:.3f} vs {ts['fda_le']:.3f}.",
        "",
        "## Catalytic-triad engagement",
        "",
        "Counted per ligand (best receptor), not per ligand-by-receptor pose row:",
        "",
        "| Box | ≥1 triad residue | ≥2 residues | all 3 residues |",
        "| --- | --- | --- | --- |",
    ]
    for key, label in (("triad_engagement_wide_box", "Wide"), ("triad_engagement_tight_box", "Tight")):
        t = stats[key]
        lines.append(
            f"| {label} | {t['contacting_at_least_one_triad_residue']}/{t['ligands']} | "
            f"{t['contacting_at_least_two_triad_residues']}/{t['ligands']} | "
            f"{t['contacting_all_three_triad_residues']}/{t['ligands']} |"
        )

    pc = stats["speb_positive_control"]
    lines += [
        "",
        "## SpeB positive control",
        "",
        f"- Box: {speb['box_basis']}.",
        f"- Decoys: {pc['decoy_count']}, size-matched to Q9D "
        f"({pc['positive_heavy_atom_count']} heavy atoms; decoys {pc['decoy_heavy_atom_range'][0]}-"
        f"{pc['decoy_heavy_atom_range'][1]}).",
        f"- By best affinity: Q9D {pc['by_best_affinity']['positive_affinity']:.2f} kcal/mol, "
        f"best decoy {pc['by_best_affinity']['best_decoy_affinity']:.2f}; "
        f"beats all decoys: {pc['by_best_affinity']['beats_all_decoys']}.",
        f"- By ligand efficiency: Q9D {pc['by_ligand_efficiency']['positive_affinity']:.3f}, "
        f"best decoy {pc['by_ligand_efficiency']['best_decoy_affinity']:.3f}; "
        f"beats all decoys: {pc['by_ligand_efficiency']['beats_all_decoys']}.",
        f"- **Passes on both metrics: {pc['passes_on_both_metrics']}.**",
        "",
    ]

    if boron:
        best = min(boron["results"], key=lambda r: r["best_affinity_kcal_mol"])
        lines += [
            "## Boron gem-diol surrogates",
            "",
            f"- {boron['method']}",
            f"- Best surrogate: {best['parent_ligand_id']} at {best['best_affinity_kcal_mol']:.2f} kcal/mol "
            f"({best['pocket_id']}). Approximation only; see `boron_surrogate_result.json`.",
            "",
        ]

    lines += [
        "## Limitations",
        "",
        "- Predictions are not evidence of inhibition or efficacy; no therapeutic claim is made.",
        "- Vina affinity is size-biased; ligand efficiency mitigates but does not remove this.",
        "- Boron compounds have no MMFF94 or Vina parameters and are handled only as gem-diol surrogates.",
        "- Rigid-receptor, single-conformer docking ignores protein flexibility.",
        "- Custom positives are general protease motifs, not validated SpyCEP binders.",
        f"- {len(stereo)} compounds carry an unspecified stereocentre that ETKDG assigned arbitrarily "
        f"({', '.join(stereo)}); the docked isomer is recorded as `embedded_isomeric_smiles`.",
        "",
    ]
    OUTPUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {OUTPUT.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()

"""Generate the tracked docking methods/results note from tracked manifests.

Writes docs/methods/docking_analysis.md summarizing the full-library docking runs
(wide receptor-prep box and tight triad-centered box), ligand-efficiency ranking,
per-residue triad engagement, the boron gem-diol surrogate, and limitations.
Numbers are read from the tracked result manifests so the note stays in sync.

Run:
    .\\.venv\\Scripts\\python.exe scripts\\write_docking_methods.py
"""
from __future__ import annotations

import json
from pathlib import Path
from statistics import mean

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WIDE = PROJECT_ROOT / "docs" / "methods" / "docking_result.json"
TIGHT = PROJECT_ROOT / "docs" / "methods" / "docking_result_tight.json"
BORON = PROJECT_ROOT / "docs" / "methods" / "boron_surrogate_result.json"
LIBRARY = PROJECT_ROOT / "docs" / "methods" / "compound_library_source.json"
OUTPUT = PROJECT_ROOT / "docs" / "methods" / "docking_analysis.md"


def _set_stats(result: dict, setof: dict) -> dict:
    # Exclude non-fits (non-negative affinity = ligand does not fit the box, e.g. vancomycin in the tight box).
    ranking = [r for r in result["ranking"] if r["ensemble_best_affinity_kcal_mol"] < 0]
    cu = [r for r in ranking if setof.get(r["ligand_id"]) == "custom_anti_virulence"]
    fd = [r for r in ranking if setof.get(r["ligand_id"]) == "fda_comparator"]

    def m(group, key):
        return mean([r[key] for r in group]) if group else float("nan")

    return {
        "custom_best": m(cu, "ensemble_best_affinity_kcal_mol"),
        "fda_best": m(fd, "ensemble_best_affinity_kcal_mol"),
        "custom_le": m(cu, "ligand_efficiency_kcal_mol_per_heavy_atom"),
        "fda_le": m(fd, "ligand_efficiency_kcal_mol_per_heavy_atom"),
    }


def _top_rows(result: dict, setof: dict, n: int = 10) -> list[str]:
    lines = ["| Rank | Ligand | Set | Ligand efficiency | Best (kcal/mol) |", "| --- | --- | --- | --- | --- |"]
    for r in result["ranking"][:n]:
        s = "custom" if setof.get(r["ligand_id"]) == "custom_anti_virulence" else "FDA"
        lines.append(
            f"| {r['rank']} | {r['ligand_id']} | {s} | "
            f"{r['ligand_efficiency_kcal_mol_per_heavy_atom']:.3f} | {r['ensemble_best_affinity_kcal_mol']:.2f} |"
        )
    return lines


def main() -> None:
    setof = {c["ligand_id"]: c["set"] for c in json.loads(LIBRARY.read_text(encoding="utf-8"))["compounds"]}
    wide = json.loads(WIDE.read_text(encoding="utf-8"))
    tight = json.loads(TIGHT.read_text(encoding="utf-8")) if TIGHT.exists() else None
    boron = json.loads(BORON.read_text(encoding="utf-8")) if BORON.exists() else None

    ws = _set_stats(wide, setof)
    lines = [
        "# Docking Methods And Results Note",
        "",
        "Generated from tracked manifests by `scripts/write_docking_methods.py`.",
        "Computational prioritization only; not evidence of binding or efficacy.",
        "",
        "## Pipeline",
        "",
        "SMILES (PubChem) -> desalt -> RDKit ETKDGv3 (seed 42) 3D -> Meeko `mk_prepare_ligand` "
        "-> AutoDock Vina (exhaustiveness 8, 9 modes, seed 42) over the 5XYA + 7EDD ensemble "
        "-> ligand-efficiency ranking -> per-residue catalytic-triad interaction analysis.",
        "",
        f"Engine: {wide['vina_version']}. Two search boxes were used: the wide receptor-preparation "
        "box and a tight box centered on the D151/H279/S617 centroid (`tight_pocket_definition.json`).",
        "",
        "## Full-library result (wide box)",
        "",
        f"- Compounds docked: {wide['compounds_docked']}/{wide['compounds_input']}. "
        f"Failures: {len(wide['dock_failures'])} (the four boronic acids; AutoDock Vina has no boron parameters).",
        f"- Custom vs FDA mean best affinity: {ws['custom_best']:.2f} vs {ws['fda_best']:.2f} kcal/mol.",
        f"- Custom vs FDA mean ligand efficiency: {ws['custom_le']:.3f} vs {ws['fda_le']:.3f} kcal/mol per heavy atom.",
        "",
        "Top 10 by ligand efficiency:",
        "",
        *_top_rows(wide, setof),
        "",
    ]
    if tight:
        ts = _set_stats(tight, setof)
        lines += [
            "## Tight triad-centered box (robustness check)",
            "",
            f"- Compounds docked: {tight['compounds_docked']}/{tight['compounds_input']}.",
            f"- Custom vs FDA mean best affinity: {ts['custom_best']:.2f} vs {ts['fda_best']:.2f} kcal/mol "
            "(non-fits with non-negative affinity, e.g. oversized vancomycin, are excluded).",
            f"- Custom vs FDA mean ligand efficiency: {ts['custom_le']:.3f} vs {ts['fda_le']:.3f}.",
            "- FDA is marginally stronger on the mean in both boxes but the difference is not significant "
            "(bootstrap CI includes 0; see docking_statistics.json); the null is robust to box choice.",
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
        "## Interpretation",
        "",
        "Docking did not nominate a compelling small-molecule SpyCEP candidate. Scores are modest and "
        "rankings are metric-dependent; rational protease chemotypes are only weakly enriched by ligand "
        "efficiency. This reads as an honest benchmarking/negative result, consistent with the absence of "
        "any reported small-molecule SpyCEP inhibitor. See the manuscript draft in `docs/manuscript/`.",
        "",
        "## Limitations",
        "",
        "- Predictions are not evidence of inhibition or efficacy; no therapeutic claim is made.",
        "- Vina affinity is size-biased; ligand efficiency mitigates but does not remove this.",
        "- Boron compounds were approximated by gem-diol surrogates omitting boron chemistry.",
        "- Rigid-receptor, single-ligand-conformer docking ignores protein flexibility.",
        "- Custom positives are general protease motifs, not validated SpyCEP binders.",
        "",
    ]
    OUTPUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {OUTPUT.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()

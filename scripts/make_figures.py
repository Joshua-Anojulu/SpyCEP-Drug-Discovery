"""Generate manuscript figures from tracked manifests.

Writes four publication figures to docs/manuscript/figures/:
  1. custom vs FDA best-affinity distribution (the null: overlapping, n.s.)
  2. SpeB positive control, on BOTH raw affinity and ligand efficiency
  3. top compounds by ligand efficiency, colored by set
  4. per-ligand catalytic-triad engagement

Figure 2 shows both metrics side by side on purpose. Reporting the positive control on
raw affinity alone would judge it by the metric this project explicitly disowns as
size-biased, and the two metrics do not have to agree.

Colors use the dataviz categorical slots (custom=blue #2a78d6, FDA=aqua #1baf7a),
validated colorblind-safe; identity is reinforced by direct labels and a legend.

Run:
    .\\.venv\\Scripts\\python.exe scripts\\make_figures.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))
from spycep_drug_discovery.docking import (
    validate_campaign_manifest_set,
    validate_manifest_timeout_qc,
)

METHODS = PROJECT_ROOT / "docs" / "methods"
FIGDIR = PROJECT_ROOT / "docs" / "manuscript" / "figures"

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK2 = "#52514e"
CUSTOM = "#2a78d6"
FDA = "#1baf7a"
HILITE = "#2a78d6"
NEUTRAL = "#b7b6ae"

AFFINITY = "ensemble_best_affinity_kcal_mol"
EFFICIENCY = "ligand_efficiency_kcal_mol_per_heavy_atom"


def _style(ax):
    ax.set_facecolor(SURFACE)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color("#d9d8d2")
    ax.tick_params(colors=INK2, labelsize=9, length=0)
    ax.title.set_color(INK)
    ax.xaxis.label.set_color(INK2)
    ax.yaxis.label.set_color(INK2)


def _manifest(name: str) -> dict:
    manifest = json.loads((METHODS / name).read_text(encoding="utf-8"))
    validate_manifest_timeout_qc(manifest)
    return manifest


def _ranking(name: str) -> list[dict]:
    rows = _manifest(name)["ranking"]
    return [r for r in rows if r[AFFINITY] < 0]  # drop non-fits (positive = clash)


def figure_custom_vs_fda():
    stats = json.loads((METHODS / "docking_statistics.json").read_text(encoding="utf-8"))
    fig, axes = plt.subplots(1, 2, figsize=(8.0, 4.2), facecolor=SURFACE)
    panels = [
        ("docking_result.json", "Wide box (22 Å)", "custom_vs_fda_wide_box"),
        ("docking_result_tight.json", "Tight box (16–20 Å)", "custom_vs_fda_tight_box"),
    ]
    for ax, (result, box_label, statkey) in zip(axes, panels):
        ranking = _ranking(result)
        custom = [r[AFFINITY] for r in ranking if r["set"] == "custom_anti_virulence"]
        fda = [r[AFFINITY] for r in ranking if r["set"] == "fda_comparator"]
        rng = np.random.default_rng(42)
        for i, (vals, color) in enumerate(zip([custom, fda], [CUSTOM, FDA])):
            ax.boxplot(vals, positions=[i], widths=0.5, patch_artist=True, showfliers=False,
                       medianprops=dict(color=INK, linewidth=1.5),
                       whiskerprops=dict(color=INK2), capprops=dict(color=INK2),
                       boxprops=dict(facecolor=color, edgecolor=SURFACE, linewidth=1.5, alpha=0.35))
            ax.scatter(np.full(len(vals), i) + rng.uniform(-0.14, 0.14, len(vals)), vals,
                       s=22, color=color, edgecolor=SURFACE, linewidth=0.6, zorder=3)
        bd = stats[statkey]["best_affinity"]["bootstrap_mean_difference_custom_minus_fda"]
        sig = "significant" if bd["excludes_zero"] else "n.s."
        ax.set_title(box_label, fontsize=10)
        ax.set_xticks([0, 1])
        ax.set_xticklabels([f"Custom (n={len(custom)})", f"FDA (n={len(fda)})"], fontsize=9)
        ax.set_ylabel("Best ensemble affinity (kcal/mol)")
        ax.grid(axis="y", color="#ecebe6", linewidth=0.8, zorder=0)
        ax.set_axisbelow(True)
        ax.annotate(
            f"Δmean = {bd['observed_difference']:.2f}\n95% CI [{bd['ci95_low']:.2f}, {bd['ci95_high']:.2f}] ({sig})",
            xy=(0.5, 0.02), xycoords="axes fraction", ha="center", va="bottom", fontsize=8, color=INK2,
        )
        _style(ax)
    fig.suptitle("Custom chemotypes vs FDA drugs against SpyCEP — no significant separation",
                 color=INK, fontsize=11, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(FIGDIR / "fig1_custom_vs_fda.png", dpi=300, facecolor=SURFACE)
    plt.close(fig)


def figure_speb_positive_control():
    speb = _manifest("speb_positive_control_result.json")
    rows = [r for r in speb["results"] if r["role"] in ("positive_known_inhibitor", "decoy")]

    fig, axes = plt.subplots(1, 2, figsize=(10.5, 5.4), facecolor=SURFACE)
    for ax, (key, label) in zip(
        axes,
        [("best_affinity_kcal_mol", "Best affinity (kcal/mol)"),
         ("ligand_efficiency_kcal_mol_per_heavy_atom", "Ligand efficiency (kcal/mol per heavy atom)")],
    ):
        ordered = sorted(rows, key=lambda r: r[key])
        names = [
            "Q9D (known inhibitor)" if r["role"] == "positive_known_inhibitor" else r["ligand_id"]
            for r in ordered
        ]
        vals = [r[key] for r in ordered]
        colors = [HILITE if r["role"] == "positive_known_inhibitor" else NEUTRAL for r in ordered]
        y = np.arange(len(ordered))[::-1]
        ax.barh(y, vals, color=colors, edgecolor=SURFACE, linewidth=1.2, height=0.7, zorder=3)
        ax.set_yticks(y)
        ax.set_yticklabels(names, fontsize=8)
        ax.set_xlabel(f"{label}  — more negative = stronger", fontsize=9)
        rank = [r["role"] for r in ordered].index("positive_known_inhibitor") + 1
        verdict = "recovers the inhibitor" if rank == 1 else f"inhibitor ranks {rank} of {len(ordered)}"
        ax.set_title(f"By {label.split(' (')[0].lower()}: {verdict}", fontsize=10, color=INK)
        ax.grid(axis="x", color="#ecebe6", linewidth=0.8, zorder=0)
        ax.set_axisbelow(True)
        _style(ax)

    handles = [plt.Rectangle((0, 0), 1, 1, color=HILITE), plt.Rectangle((0, 0), 1, 1, color=NEUTRAL)]
    axes[0].legend(handles, ["Known inhibitor", "Size-matched decoys"], frameon=False, fontsize=8, loc="lower left")
    fig.suptitle(
        f"SpeB positive control — {speb['decoy_count']} decoys size-matched to Q9D "
        f"({speb['results'][0].get('heavy_atom_count', '')} heavy atoms), box from the catalytic dyad alone",
        color=INK, fontsize=11, fontweight="bold",
    )
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(FIGDIR / "fig2_speb_positive_control.png", dpi=300, facecolor=SURFACE)
    plt.close(fig)


def figure_top_hits():
    ranking = _ranking("docking_result.json")[:15]
    names = [r["ligand_id"] for r in ranking]
    le = [r[EFFICIENCY] for r in ranking]
    colors = [CUSTOM if r["set"] == "custom_anti_virulence" else FDA for r in ranking]
    fig, ax = plt.subplots(figsize=(7.6, 5.2), facecolor=SURFACE)
    y = np.arange(len(ranking))[::-1]
    ax.barh(y, le, color=colors, edgecolor=SURFACE, linewidth=1.5, height=0.7, zorder=3)
    for yi, v in zip(y, le):
        ax.annotate(f"{v:.2f}", xy=(v, yi), xytext=(5, 0), textcoords="offset points",
                    ha="left", va="center", color="white", fontsize=8, fontweight="bold")
    ax.set_yticks(y)
    ax.set_yticklabels(names, fontsize=9)
    ax.set_xlabel("Ligand efficiency (kcal/mol per heavy atom)  — more negative = stronger")
    ax.set_title("Top 15 SpyCEP compounds by ligand efficiency (wide box)", fontsize=10, color=INK)
    ax.grid(axis="x", color="#ecebe6", linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)
    handles = [plt.Rectangle((0, 0), 1, 1, color=CUSTOM), plt.Rectangle((0, 0), 1, 1, color=FDA)]
    ax.legend(handles, ["Custom chemotype", "FDA comparator"], frameon=False, fontsize=8, loc="lower right")
    _style(ax)
    fig.tight_layout()
    fig.savefig(FIGDIR / "fig3_top_hits_ligand_efficiency.png", dpi=300, facecolor=SURFACE)
    plt.close(fig)


def figure_triad_engagement():
    stats = json.loads((METHODS / "docking_statistics.json").read_text(encoding="utf-8"))
    fig, ax = plt.subplots(figsize=(7.2, 4.0), facecolor=SURFACE)
    labels = ["≥1 residue", "≥2 residues", "all 3 residues"]
    keys = [
        "contacting_at_least_one_triad_residue",
        "contacting_at_least_two_triad_residues",
        "contacting_all_three_triad_residues",
    ]
    x = np.arange(len(labels))
    for offset, (statkey, label, color) in enumerate(
        [("triad_engagement_wide_box", "Wide box", CUSTOM), ("triad_engagement_tight_box", "Tight box", FDA)]
    ):
        block = stats[statkey]
        total = block["ligands"]
        vals = [100.0 * block[k] / total for k in keys]
        bars = ax.bar(x + (offset - 0.5) * 0.38, vals, width=0.36, color=color, label=label,
                      edgecolor=SURFACE, linewidth=1.2, zorder=3)
        for rect, k in zip(bars, keys):
            ax.annotate(f"{block[k]}/{total}", xy=(rect.get_x() + rect.get_width() / 2, rect.get_height()),
                        xytext=(0, 3), textcoords="offset points", ha="center", fontsize=8, color=INK2)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=9)
    ax.set_ylabel("Compounds contacting the catalytic triad (%)")
    ax.set_ylim(0, 112)
    ax.set_title("Triad contact does not discriminate: nearly every ligand touches the site",
                 fontsize=10, color=INK)
    ax.grid(axis="y", color="#ecebe6", linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)
    ax.legend(frameon=False, fontsize=8)
    _style(ax)
    fig.tight_layout()
    fig.savefig(FIGDIR / "fig4_triad_engagement.png", dpi=300, facecolor=SURFACE)
    plt.close(fig)


def main() -> None:
    validate_campaign_manifest_set(
        (
            _manifest("docking_result.json"),
            _manifest("docking_result_tight.json"),
            _manifest("speb_positive_control_result.json"),
        )
    )
    FIGDIR.mkdir(parents=True, exist_ok=True)
    figure_custom_vs_fda()
    figure_speb_positive_control()
    figure_top_hits()
    figure_triad_engagement()
    print(f"Wrote 4 figures to {FIGDIR.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()

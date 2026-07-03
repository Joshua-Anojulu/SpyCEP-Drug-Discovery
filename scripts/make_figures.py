"""Generate manuscript figures from tracked manifests.

Writes three publication figures to docs/manuscript/figures/:
  1. custom vs FDA best-affinity distribution (the null: overlapping, n.s.)
  2. SpeB positive control (Q9D vs decoys; the pipeline recovers a real binder)
  3. top compounds by ligand efficiency, colored by set

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
METHODS = PROJECT_ROOT / "docs" / "methods"
FIGDIR = PROJECT_ROOT / "docs" / "manuscript" / "figures"

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK2 = "#52514e"
CUSTOM = "#2a78d6"   # categorical slot 1
FDA = "#1baf7a"      # categorical slot 2
HILITE = "#2a78d6"
NEUTRAL = "#b7b6ae"


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


def _setof():
    return {c["ligand_id"]: c["set"] for c in json.loads((METHODS / "compound_library_source.json").read_text())["compounds"]}


def figure_custom_vs_fda():
    setof = _setof()
    stats = json.loads((METHODS / "docking_statistics.json").read_text())
    fig, axes = plt.subplots(1, 2, figsize=(8.0, 4.2), facecolor=SURFACE)
    for ax, (result, box_label, statkey) in zip(
        axes,
        [("docking_result.json", "Wide box (22 Å)", "custom_vs_fda_wide_box"),
         ("docking_result_tight.json", "Tight box (16–20 Å)", "custom_vs_fda_tight_box")],
    ):
        ranking = [r for r in json.loads((METHODS / result).read_text())["ranking"]
                   if r["ensemble_best_affinity_kcal_mol"] < 0]  # drop non-fits (positive = clash)
        custom = [r["ensemble_best_affinity_kcal_mol"] for r in ranking if setof.get(r["ligand_id"]) == "custom_anti_virulence"]
        fda = [r["ensemble_best_affinity_kcal_mol"] for r in ranking if setof.get(r["ligand_id"]) == "fda_comparator"]
        groups = [custom, fda]
        colors = [CUSTOM, FDA]
        labels = [f"Custom (n={len(custom)})", f"FDA (n={len(fda)})"]
        rng = np.random.default_rng(42)
        for i, (vals, color) in enumerate(zip(groups, colors)):
            bp = ax.boxplot(vals, positions=[i], widths=0.5, patch_artist=True, showfliers=False,
                            medianprops=dict(color=INK, linewidth=1.5),
                            whiskerprops=dict(color=INK2), capprops=dict(color=INK2),
                            boxprops=dict(facecolor=color, edgecolor=SURFACE, linewidth=1.5, alpha=0.35))
            ax.scatter(np.full(len(vals), i) + rng.uniform(-0.14, 0.14, len(vals)), vals,
                       s=22, color=color, edgecolor=SURFACE, linewidth=0.6, zorder=3)
        bd = stats[statkey]["best_affinity"]["bootstrap_mean_difference_custom_minus_fda"]
        sig = "significant" if bd["excludes_zero"] else "n.s."
        ax.set_title(box_label, fontsize=10)
        ax.set_xticks([0, 1])
        ax.set_xticklabels(labels, fontsize=9)
        ax.set_ylabel("Best ensemble affinity (kcal/mol)")
        ax.grid(axis="y", color="#ecebe6", linewidth=0.8, zorder=0)
        ax.set_axisbelow(True)
        ax.annotate(f"Δmean = {bd['observed_difference']:.2f}\n95% CI [{bd['ci95_low']:.2f}, {bd['ci95_high']:.2f}] ({sig})",
                    xy=(0.5, 0.02), xycoords="axes fraction", ha="center", va="bottom",
                    fontsize=8, color=INK2)
        _style(ax)
    fig.suptitle("Custom chemotypes vs FDA drugs against SpyCEP — no significant separation",
                 color=INK, fontsize=11, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(FIGDIR / "fig1_custom_vs_fda.png", dpi=300, facecolor=SURFACE)
    plt.close(fig)


def figure_speb_positive_control():
    speb = json.loads((METHODS / "speb_positive_control_result.json").read_text())
    stats = json.loads((METHODS / "docking_statistics.json").read_text())["speb_positive_control"]
    rows = sorted(speb["results"], key=lambda r: r["best_affinity_kcal_mol"])
    names = [("Q9D (known inhibitor)" if r["ligand_id"] == "Q9D_speb_inhibitor" else r["ligand_id"]) for r in rows]
    vals = [r["best_affinity_kcal_mol"] for r in rows]
    colors = [HILITE if r["ligand_id"] == "Q9D_speb_inhibitor" else NEUTRAL for r in rows]
    fig, ax = plt.subplots(figsize=(7.2, 4.2), facecolor=SURFACE)
    y = np.arange(len(rows))[::-1]
    ax.barh(y, vals, color=colors, edgecolor=SURFACE, linewidth=1.5, height=0.68, zorder=3)
    for yi, v in zip(y, vals):
        ax.annotate(f"{v:.2f}", xy=(v, yi), xytext=(5, 0), textcoords="offset points",
                    ha="left", va="center", color="white", fontsize=8.5, fontweight="bold")
    ax.set_yticks(y)
    ax.set_yticklabels(names, fontsize=9)
    ax.set_xlabel("Best affinity vs SpeB (kcal/mol)  — more negative = stronger")
    ax.set_title(f"SpeB positive control: known inhibitor Q9D wins by {stats['margin_to_best_decoy']:.2f} kcal/mol "
                 f"({stats['sd_stronger_than_decoy_mean']:.1f} SD)", fontsize=10, color=INK)
    ax.grid(axis="x", color="#ecebe6", linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)
    handles = [plt.Rectangle((0, 0), 1, 1, color=HILITE), plt.Rectangle((0, 0), 1, 1, color=NEUTRAL)]
    ax.legend(handles, ["Known inhibitor", "Drug-like decoys"], frameon=False, fontsize=8, loc="lower left")
    _style(ax)
    fig.tight_layout()
    fig.savefig(FIGDIR / "fig2_speb_positive_control.png", dpi=300, facecolor=SURFACE)
    plt.close(fig)


def figure_top_hits():
    setof = _setof()
    ranking = json.loads((METHODS / "docking_result.json").read_text())["ranking"][:15]
    names = [r["ligand_id"] for r in ranking]
    le = [r["ligand_efficiency_kcal_mol_per_heavy_atom"] for r in ranking]
    colors = [CUSTOM if setof.get(r["ligand_id"]) == "custom_anti_virulence" else FDA for r in ranking]
    fig, ax = plt.subplots(figsize=(7.6, 5.2), facecolor=SURFACE)
    y = np.arange(len(ranking))[::-1]
    ax.barh(y, le, color=colors, edgecolor=SURFACE, linewidth=1.5, height=0.7, zorder=3)
    for yi, v in zip(y, le):
        ax.annotate(f"{v:.2f}", xy=(v, yi), xytext=(5, 0), textcoords="offset points",
                    ha="left", va="center", color="white", fontsize=8, fontweight="bold")
    ax.set_yticks(y)
    ax.set_yticklabels(names, fontsize=9)
    ax.set_xlabel("Ligand efficiency (kcal/mol per heavy atom)  — more negative = stronger")
    ax.set_title("Top 15 SpyCEP hits by ligand efficiency (wide box)", fontsize=10, color=INK)
    ax.grid(axis="x", color="#ecebe6", linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)
    handles = [plt.Rectangle((0, 0), 1, 1, color=CUSTOM), plt.Rectangle((0, 0), 1, 1, color=FDA)]
    ax.legend(handles, ["Custom chemotype", "FDA comparator"], frameon=False, fontsize=8, loc="lower right")
    _style(ax)
    fig.tight_layout()
    fig.savefig(FIGDIR / "fig3_top_hits_ligand_efficiency.png", dpi=300, facecolor=SURFACE)
    plt.close(fig)


def main() -> None:
    FIGDIR.mkdir(parents=True, exist_ok=True)
    figure_custom_vs_fda()
    figure_speb_positive_control()
    figure_top_hits()
    print(f"Wrote 3 figures to {FIGDIR.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()

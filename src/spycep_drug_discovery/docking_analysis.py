from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path
from statistics import mean
from typing import Any, Mapping, Sequence


ANALYSIS_VERSION = "2026-07-02"


def rank_docking_results(results: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Aggregate per-ligand best affinity across the receptor ensemble and rank ascending.

    A more negative ensemble_best_affinity is stronger. Ranking uses the best (min) affinity
    a ligand achieves against any receptor; ensemble_mean_affinity averages the per-receptor
    bests as a simple cross-receptor consistency signal.
    """
    per_ligand: dict[tuple[str, str], dict[str, Any]] = {}
    per_receptor: dict[tuple[str, str], dict[str, float]] = defaultdict(dict)
    for row in results:
        entity_id = str(row.get("entity_id") or row["ligand_id"])
        state_id = str(row.get("state_id") or "state_01")
        species_key = (entity_id, state_id)
        pocket_id = str(row["pocket_id"])
        affinity = float(row["best_affinity_kcal_mol"])
        per_receptor[species_key][pocket_id] = affinity
        per_ligand.setdefault(
            species_key,
            {
                "ligand_id": entity_id,
                "entity_id": entity_id,
                "state_id": state_id,
                "species_key": [entity_id, state_id],
                # `set` is the custom-vs-FDA label the whole comparison turns on. It was
                # previously dropped here, so every downstream consumer had to re-join
                # against the library manifest and the emitted `role` column was always
                # empty.
                "set": row.get("set"),
                "role": row.get("role"),
                "heavy_atom_count": row.get("heavy_atom_count"),
            },
        )

    ranked: list[dict[str, Any]] = []
    for species_key, base in per_ligand.items():
        receptor_bests = per_receptor[species_key]
        affinities = list(receptor_bests.values())
        best = min(affinities)
        heavy = base.get("heavy_atom_count")
        ranked.append(
            {
                **base,
                "per_receptor_best_affinity": dict(receptor_bests),
                "ensemble_best_affinity_kcal_mol": best,
                "ensemble_mean_affinity_kcal_mol": mean(affinities),
                "ligand_efficiency_kcal_mol_per_heavy_atom": (best / heavy) if heavy else None,
                "receptor_count": len(affinities),
            }
        )

    ranked.sort(key=lambda item: item["ensemble_best_affinity_kcal_mol"])
    for position, item in enumerate(ranked, start=1):
        item["rank_by_affinity"] = position

    # Ligand efficiency corrects the AutoDock Vina size bias (raw score scales with
    # molecular size). When heavy-atom counts are available it is the primary ranking.
    if all(item["ligand_efficiency_kcal_mol_per_heavy_atom"] is not None for item in ranked):
        ranked.sort(key=lambda item: item["ligand_efficiency_kcal_mol_per_heavy_atom"])
    for position, item in enumerate(ranked, start=1):
        item["rank"] = position
    return ranked


def write_ranking_csv(ranked: Sequence[Mapping[str, Any]], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "rank",
                "ligand_id",
                "state_id",
                "set",
                "role",
                "heavy_atom_count",
                "ensemble_best_affinity_kcal_mol",
                "ligand_efficiency_kcal_mol_per_heavy_atom",
                "rank_by_affinity",
            ]
        )
        for item in ranked:
            le = item.get("ligand_efficiency_kcal_mol_per_heavy_atom")
            writer.writerow(
                [
                    item["rank"],
                    item["ligand_id"],
                    item["state_id"],
                    item.get("set") or "",
                    item.get("role") or "",
                    item.get("heavy_atom_count", ""),
                    f"{item['ensemble_best_affinity_kcal_mol']:.3f}",
                    f"{le:.4f}" if le is not None else "",
                    item.get("rank_by_affinity", ""),
                ]
            )

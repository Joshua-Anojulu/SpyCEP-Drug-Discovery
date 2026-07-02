"""Generate the tracked docking methods note from tracked manifests.

Writes docs/methods/docking_analysis.md describing the ligand-preparation ->
AutoDock Vina docking -> ligand-efficiency ranking -> interaction-analysis
pipeline and the validation-pilot outcome. Numbers are read from the tracked
docs/methods/validation_pilot_result.json so the note stays in sync.

Run:
    .\\.venv\\Scripts\\python.exe scripts\\write_docking_methods.py
"""
from __future__ import annotations

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PILOT_RESULT = PROJECT_ROOT / "docs" / "methods" / "validation_pilot_result.json"
OUTPUT = PROJECT_ROOT / "docs" / "methods" / "docking_analysis.md"


def _ranking_table(ranking: list[dict]) -> list[str]:
    lines = [
        "| Rank (efficiency) | Ligand | Role | Heavy atoms | Ensemble best (kcal/mol) | Ligand efficiency | Rank (raw affinity) |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for item in ranking:
        lines.append(
            "| {rank} | {ligand_id} | {role} | {heavy} | {best:.3f} | {le:.4f} | {raw} |".format(
                rank=item["rank"],
                ligand_id=item["ligand_id"],
                role=item.get("role", ""),
                heavy=item.get("heavy_atom_count", ""),
                best=item["ensemble_best_affinity_kcal_mol"],
                le=item["ligand_efficiency_kcal_mol_per_heavy_atom"],
                raw=item.get("rank_by_affinity", ""),
            )
        )
    return lines


def _interaction_rows(pose_interactions: list[dict]) -> list[str]:
    lines = [
        "| Ligand | Receptor | Best (kcal/mol) | Active-site contacts | Full triad |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in pose_interactions:
        contacts = ", ".join(row["contacted_active_site_residues"]) or "none"
        lines.append(
            f"| {row['ligand_id']} | {row['pocket_id']} | {row['best_affinity_kcal_mol']:.3f} "
            f"| {contacts} | {'yes' if row['contacts_catalytic_triad'] else 'no'} |"
        )
    return lines


def main() -> None:
    pilot = json.loads(PILOT_RESULT.read_text(encoding="utf-8"))
    repro = pilot["reproducibility_check"]
    lines = [
        "# Docking Methods Note",
        "",
        "This file is generated from tracked manifests by `scripts/write_docking_methods.py`.",
        "It documents the Milestone 3 compound-docking pipeline and the pipeline-validation pilot.",
        "",
        "## Pipeline",
        "",
        "1. **Ligand preparation** — SMILES are embedded to a single 3D conformer with RDKit "
        f"ETKDGv3 (fixed seed {pilot['ligands'][0]['embed_seed']}) and MMFF-optimized, then converted "
        "to PDBQT with Meeko `mk_prepare_ligand`.",
        "2. **Docking** — AutoDock Vina (executable, subprocess) docks each ligand into the tracked "
        "active-site box of each receptor in the ensemble.",
        "3. **Ranking** — ligand efficiency (ensemble best affinity / heavy-atom count) is the primary "
        "ranking metric; raw affinity rank is retained for comparison.",
        "4. **Interaction analysis** — the best pose is checked for atomic contacts (<= "
        f"{pilot.get('contact_cutoff_angstrom', 4.0)} A) with the catalytic triad D151/H279/S617.",
        "",
        "## Configuration",
        "",
        f"- Docking engine: {pilot['vina_version']}",
        f"- Search: exhaustiveness {pilot['exhaustiveness']}, num_modes {pilot['num_modes']}, "
        f"fixed seed {pilot['seed']}.",
        f"- Receptor ensemble: {', '.join(pilot['receptor_ensemble'])}.",
        "- Boxes come from `docs/methods/pdbqt_conversion.json` / `receptor_preparation.json`.",
        "",
        "## Validation Pilot",
        "",
        "The pilot set (`docs/methods/validation_pilot_compounds.json`) is a throwaway pipeline check, "
        "**not** the research library and **not** a hit-discovery result.",
        "",
        f"- Reproducibility: {repro['ligand_id']} vs {repro['pocket_id']} scored "
        f"{repro['first_run_best']:.3f} kcal/mol on both the first and repeat run "
        f"(deterministic = {repro['deterministic']}).",
        "",
        "Ranking:",
        "",
        *_ranking_table(pilot["ranking"]),
        "",
        "Active-site contacts (best pose):",
        "",
        *_interaction_rows(pilot["pose_interactions"]),
        "",
        "## Limitations",
        "",
        "- Docking scores are computational predictions, not evidence of efficacy or binding in vitro.",
        "- Raw AutoDock Vina affinity is biased by molecular size; in the pilot the larger drug decoys "
        "outranked the smaller amidine positives by raw score, and ligand efficiency was required to "
        "recover the expected ordering. Report ligand efficiency (and/or property-matched decoys).",
        "- Receptor PDBQT files were generated with Meeko `--allow_bad_res`; some incomplete residues "
        "were omitted (none catalytic). See `docs/methods/pdbqt_quality_review.json`.",
        "- The pilot positive controls are generic serine-protease-binding motifs, not SpyCEP-specific "
        "inhibitors, so the pilot validates the pipeline, not SpyCEP selectivity.",
        "- Pilot poses in the 5XYA (AES-anchored) box did not contact the catalytic triad, unlike the "
        "7EDD box; box placement and the removed AES anchor should be reviewed before real docking.",
        "",
    ]
    OUTPUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {OUTPUT.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()

"""SpeB positive-control docking screen (plan C).

SpeB/streptopain has a known small-molecule inhibitor and an inhibitor co-complex
structure (PDB 6UKD, ligand Q9D, catalytic dyad Cys192/His340). Docking the known
inhibitor plus drug-like decoys into the SpeB active site tests whether the same
pipeline recovers a strong, specific signal for a real binder -- i.e. whether the
SpyCEP null result reflects the target rather than a broken pipeline.

Run (needs tools/vina.exe, receptor-prep extra, data/structures/6UKD.pdb):
    .\\.venv\\Scripts\\python.exe scripts\\run_speb_positive_control.py
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from spycep_drug_discovery.docking import dock_ligand
from spycep_drug_discovery.docking_analysis import rank_docking_results
from spycep_drug_discovery.interaction_analysis import analyze_pose_interactions
from spycep_drug_discovery.ligand_preparation import prepare_ligand
from spycep_drug_discovery.receptor_preparation import clean_receptor_pdb_text

VINA = PROJECT_ROOT / "tools" / "vina.exe"
MEEKO_LIG = PROJECT_ROOT / ".venv" / "Scripts" / "mk_prepare_ligand.exe"
MEEKO_REC = PROJECT_ROOT / ".venv" / "Scripts" / "mk_prepare_receptor.exe"
STRUCT = PROJECT_ROOT / "data" / "structures" / "6UKD.pdb"
REC_PDB = PROJECT_ROOT / "data" / "processed" / "receptors" / "speb_6ukd_active_site.pdb"
REC_STEM = PROJECT_ROOT / "data" / "processed" / "pdbqt" / "speb_6ukd_active_site"
RESULT = PROJECT_ROOT / "docs" / "methods" / "speb_positive_control_result.json"

# SpeB catalytic dyad in 6UKD; residue keys match interaction_analysis parsing.
ACTIVE_SITE = [
    {"chain_id": "A", "residue_name": "CYS", "residue_number": 192},
    {"chain_id": "A", "residue_name": "HIS", "residue_number": 340},
]
# Positive control: the co-crystallized specific covalent inhibitor (RCSB chemcomp Q9D).
POSITIVE = {
    "ligand_id": "Q9D_speb_inhibitor",
    "smiles": "CC(=O)[C@H](Cc1cccc(c1)[N+]([O-])=O)NC(=O)OCc2ccccc2",
    "role": "positive_known_inhibitor",
}
DECOYS = [
    {"ligand_id": "caffeine", "smiles": "Cn1cnc2n(C)c(=O)n(C)c(=O)c12", "role": "decoy"},
    {"ligand_id": "metformin", "smiles": "CN(C)C(=N)N=C(N)N", "role": "decoy"},
    {"ligand_id": "ibuprofen", "smiles": "CC(C)Cc1ccc(cc1)C(C)C(=O)O", "role": "decoy"},
    {"ligand_id": "acetaminophen", "smiles": "CC(=O)Nc1ccc(O)cc1", "role": "decoy"},
    {"ligand_id": "gabapentin", "smiles": "OC(=O)CC1(CN)CCCCC1", "role": "decoy"},
    {"ligand_id": "aspirin", "smiles": "CC(=O)Oc1ccccc1C(=O)O", "role": "decoy"},
    {"ligand_id": "benzamidine", "smiles": "NC(=N)c1ccccc1", "role": "decoy_generic_protease_motif"},
]


def _pocket_box() -> tuple[dict, dict]:
    """Box from the Q9D ligand atoms plus the catalytic dyad, +8 A padding, clamped [18,24]."""
    coords = []
    for line in STRUCT.read_text(encoding="utf-8").splitlines():
        het = line.startswith("HETATM") and line[17:20].strip() == "Q9D"
        dyad = line.startswith("ATOM") and line[21] == "A" and line[17:20].strip() in ("CYS", "HIS") and line[22:26].strip() in ("192", "340")
        if het or dyad:
            coords.append((float(line[30:38]), float(line[38:46]), float(line[46:54])))
    xs, ys, zs = zip(*coords)
    center = {"x": round(sum(xs) / len(xs), 3), "y": round(sum(ys) / len(ys), 3), "z": round(sum(zs) / len(zs), 3)}
    size = {ax: round(min(max((mx - mn) + 8.0, 18.0), 24.0), 3) for ax, mn, mx in
            (("x", min(xs), max(xs)), ("y", min(ys), max(ys)), ("z", min(zs), max(zs)))}
    return center, size


def _prepare_receptor(center: dict, size: dict) -> str:
    REC_PDB.parent.mkdir(parents=True, exist_ok=True)
    REC_STEM.parent.mkdir(parents=True, exist_ok=True)
    cleaned = clean_receptor_pdb_text(STRUCT.read_text(encoding="utf-8"), chain_id="A")
    REC_PDB.write_text(cleaned.pdb_text, encoding="utf-8")
    cmd = [
        str(MEEKO_REC), "--read_pdb", str(REC_PDB), "-o", str(REC_STEM), "--write_pdbqt",
        "--box_center", f"{center['x']:.3f}", f"{center['y']:.3f}", f"{center['z']:.3f}",
        "--box_size", f"{size['x']:.3f}", f"{size['y']:.3f}", f"{size['z']:.3f}", "--allow_bad_res",
    ]
    done = subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True, text=True)
    pdbqt = REC_STEM.with_suffix(".pdbqt")
    if not pdbqt.is_file():
        raise SystemExit(f"receptor PDBQT not produced: {done.stderr[-400:]}")
    return str(pdbqt.relative_to(PROJECT_ROOT).as_posix())


def main() -> None:
    center, size = _pocket_box()
    receptor_pdbqt = _prepare_receptor(center, size)
    receptor = {
        "pocket_id": "speb_6ukd_active_site", "pdb_id": "6UKD",
        "receptor_pdbqt_path": receptor_pdbqt, "box_center_angstrom": center, "box_size_angstrom": size,
    }
    print(f"SpeB pocket center {center} size {size}")

    results = []
    for compound in [POSITIVE] + DECOYS:
        ligand = prepare_ligand(
            compound, project_root=PROJECT_ROOT,
            work_dir=PROJECT_ROOT / "data" / "compounds" / "sdf",
            output_dir=PROJECT_ROOT / "data" / "compounds" / "pdbqt",
            meeko_command=[MEEKO_LIG],
        )
        row = dock_ligand(
            vina_executable=VINA, receptor=receptor, ligand_id=compound["ligand_id"],
            ligand_pdbqt=PROJECT_ROOT / ligand["pdbqt_path"], project_root=PROJECT_ROOT,
            output_dir=PROJECT_ROOT / "results" / "docking" / "speb_positive_control",
        )
        row["role"] = compound["role"]
        row["heavy_atom_count"] = ligand["heavy_atom_count"]
        inter = analyze_pose_interactions(PROJECT_ROOT / receptor_pdbqt, PROJECT_ROOT / row["out_path"], ACTIVE_SITE)
        row["contacted_dyad"] = inter["contacted_active_site_residues"]
        results.append(row)
        print(f"  {compound['ligand_id']:<22} best={row['best_affinity_kcal_mol']:.2f}  dyad={inter['contacted_active_site_residues'] or '-'}")

    ranked = rank_docking_results(results)
    pos = next(r for r in ranked if r["ligand_id"] == POSITIVE["ligand_id"])
    decoy_best = min(r["ensemble_best_affinity_kcal_mol"] for r in ranked if r["ligand_id"] != POSITIVE["ligand_id"])
    positive_wins = pos["ensemble_best_affinity_kcal_mol"] < decoy_best

    manifest = {
        "status": "speb_positive_control_pipeline_validation",
        "receptor": "6UKD chain A (streptopain/SpeB, catalytic dyad Cys192/His340)",
        "positive_control_ligand": "Q9D (RCSB chemcomp; co-crystallized covalent inhibitor)",
        "box_center_angstrom": center, "box_size_angstrom": size,
        "positive_best_affinity_kcal_mol": pos["ensemble_best_affinity_kcal_mol"],
        "positive_rank_by_affinity": pos["rank_by_affinity"],
        "best_decoy_affinity_kcal_mol": decoy_best,
        "positive_outscores_all_decoys": positive_wins,
        "results": [
            {"ligand_id": r["ligand_id"], "best_affinity_kcal_mol": r["ensemble_best_affinity_kcal_mol"],
             "rank_by_affinity": r["rank_by_affinity"]}
            for r in sorted(ranked, key=lambda r: r["ensemble_best_affinity_kcal_mol"])
        ],
    }
    RESULT.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"\nPositive control Q9D best={pos['ensemble_best_affinity_kcal_mol']:.2f} kcal/mol; "
          f"best decoy={decoy_best:.2f}; positive outscores all decoys: {positive_wins}")
    print(f"Wrote {RESULT.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()

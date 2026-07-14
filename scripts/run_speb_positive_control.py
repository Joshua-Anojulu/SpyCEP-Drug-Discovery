"""SpeB positive-control docking screen.

SpeB/streptopain has a known small-molecule inhibitor and an inhibitor co-complex
structure (PDB 6UKD, ligand Q9D, catalytic dyad Cys192/His340). Docking that inhibitor
against decoys tests whether the pipeline recovers a real binder -- i.e. whether the
SpyCEP null reflects the target rather than a broken pipeline.

Two design faults in the first version are corrected here, because both flattered the
control:

1. The box was centred on the centroid of the co-crystallised Q9D atoms *plus* the
   dyad, so the search box was built partly from the answer -- information no
   prospective screen has. The box is now defined by the Cys192/His340 side chains
   alone.

2. The decoys were not size-matched. Q9D has 25 heavy atoms; the old decoys averaged
   11.9. AutoDock Vina's raw score scales with molecular size, so Q9D "winning" on raw
   affinity was largely a size artefact -- and under ligand efficiency, the metric this
   project adopts precisely to correct that bias, Q9D ranked *last* of eight. Decoys are
   now drawn from the project's own FDA comparator set, restricted to compounds within
   +/-3 heavy atoms of Q9D, and both metrics are reported.

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
from spycep_drug_discovery.interaction_analysis import analyze_pose_interactions
from spycep_drug_discovery.ligand_preparation import prepare_ligand
from spycep_drug_discovery.receptor_preparation import clean_receptor_pdb_text

VINA = PROJECT_ROOT / "tools" / "vina.exe"
MEEKO_LIG = PROJECT_ROOT / ".venv" / "Scripts" / "mk_prepare_ligand.exe"
MEEKO_REC = PROJECT_ROOT / ".venv" / "Scripts" / "mk_prepare_receptor.exe"
STRUCT = PROJECT_ROOT / "data" / "structures" / "6UKD.pdb"
REC_PDB = PROJECT_ROOT / "data" / "processed" / "receptors" / "speb_6ukd_active_site.pdb"
REC_STEM = PROJECT_ROOT / "data" / "processed" / "pdbqt" / "speb_6ukd_active_site"
LIBRARY = PROJECT_ROOT / "docs" / "methods" / "compound_library_source.json"
RESULT = PROJECT_ROOT / "docs" / "methods" / "speb_positive_control_result.json"

ACTIVE_SITE = [
    {"chain_id": "A", "residue_name": "CYS", "residue_number": 192},
    {"chain_id": "A", "residue_name": "HIS", "residue_number": 340},
]
# Catalytic side chains only -- never the bound ligand.
DYAD_SIDE_CHAIN_ATOMS = {
    "CYS": {"CB", "SG"},
    "HIS": {"CG", "ND1", "CD2", "CE1", "NE2"},
}
POSITIVE = {
    "ligand_id": "Q9D_speb_inhibitor",
    "smiles": "CC(=O)[C@H](Cc1cccc(c1)[N+]([O-])=O)NC(=O)OCc2ccccc2",
    "role": "positive_known_inhibitor",
}
# Drugs whose mechanism is protease inhibition are not decoys; they are labelled so a
# good score from them is not miscounted as a false positive.
PROTEASE_INHIBITOR_DRUGS = {"nafamostat", "gabexate", "camostat", "argatroban", "ritonavir"}
HEAVY_ATOM_TOLERANCE = 3

PADDING_ANGSTROM = 8.0
MIN_SIZE_ANGSTROM = 18.0
MAX_SIZE_ANGSTROM = 24.0


def _dyad_box() -> tuple[dict, dict, int]:
    """Box from the Cys192/His340 side-chain atoms alone."""
    coords = []
    for line in STRUCT.read_text(encoding="utf-8").splitlines():
        if not line.startswith("ATOM") or line[21] != "A":
            continue
        if line[16] not in (" ", "A"):  # first altLoc only
            continue
        residue_name = line[17:20].strip()
        residue_number = line[22:26].strip()
        atom_name = line[12:16].strip()
        for site in ACTIVE_SITE:
            if residue_name == site["residue_name"] and residue_number == str(site["residue_number"]):
                if atom_name in DYAD_SIDE_CHAIN_ATOMS[residue_name]:
                    coords.append((float(line[30:38]), float(line[38:46]), float(line[46:54])))
    if not coords:
        raise SystemExit("No Cys192/His340 side-chain atoms found in 6UKD chain A.")

    xs, ys, zs = zip(*coords)
    center = {
        "x": round(sum(xs) / len(xs), 3),
        "y": round(sum(ys) / len(ys), 3),
        "z": round(sum(zs) / len(zs), 3),
    }

    def _clamp(value: float) -> float:
        return round(min(max(value, MIN_SIZE_ANGSTROM), MAX_SIZE_ANGSTROM), 3)

    size = {
        "x": _clamp((max(xs) - min(xs)) + PADDING_ANGSTROM),
        "y": _clamp((max(ys) - min(ys)) + PADDING_ANGSTROM),
        "z": _clamp((max(zs) - min(zs)) + PADDING_ANGSTROM),
    }
    return center, size, len(coords)


def _size_matched_decoys() -> list[dict]:
    """FDA comparators within +/-3 heavy atoms of Q9D, from the tracked library."""
    from rdkit import Chem

    positive_heavy = Chem.MolFromSmiles(POSITIVE["smiles"]).GetNumHeavyAtoms()
    compounds = json.loads(LIBRARY.read_text(encoding="utf-8"))["compounds"]
    decoys = []
    for compound in compounds:
        if compound["set"] != "fda_comparator":
            continue
        heavy = Chem.MolFromSmiles(compound["smiles"]).GetNumHeavyAtoms()
        if abs(heavy - positive_heavy) > HEAVY_ATOM_TOLERANCE:
            continue
        decoys.append(
            {
                "ligand_id": compound["ligand_id"],
                "smiles": compound["smiles"],
                "role": (
                    "protease_inhibitor_comparator"
                    if compound["ligand_id"] in PROTEASE_INHIBITOR_DRUGS
                    else "decoy"
                ),
            }
        )
    return sorted(decoys, key=lambda d: d["ligand_id"])


def _prepare_receptor(center: dict, size: dict) -> str:
    REC_PDB.parent.mkdir(parents=True, exist_ok=True)
    REC_STEM.parent.mkdir(parents=True, exist_ok=True)
    cleaned = clean_receptor_pdb_text(STRUCT.read_text(encoding="utf-8"), chain_id="A")
    REC_PDB.write_text(cleaned.pdb_text, encoding="utf-8")

    pdbqt = REC_STEM.with_suffix(".pdbqt")
    # Delete first: otherwise a failed Meeko run leaves a stale receptor that the
    # is_file() check below would happily accept.
    pdbqt.unlink(missing_ok=True)

    cmd = [
        str(MEEKO_REC), "--read_pdb", str(REC_PDB), "-o", str(REC_STEM), "--write_pdbqt",
        "--box_center", f"{center['x']:.3f}", f"{center['y']:.3f}", f"{center['z']:.3f}",
        "--box_size", f"{size['x']:.3f}", f"{size['y']:.3f}", f"{size['z']:.3f}", "--allow_bad_res",
    ]
    done = subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True, text=True, check=False)
    if done.returncode != 0:
        raise SystemExit(f"mk_prepare_receptor failed (exit {done.returncode}): {done.stderr[-600:]}")
    if not pdbqt.is_file():
        raise SystemExit(f"receptor PDBQT not produced: {done.stderr[-600:]}")
    return str(pdbqt.relative_to(PROJECT_ROOT).as_posix())


def main() -> None:
    center, size, dyad_atoms = _dyad_box()
    receptor_pdbqt = _prepare_receptor(center, size)
    receptor = {
        "pocket_id": "speb_6ukd_active_site",
        "pdb_id": "6UKD",
        "receptor_pdbqt_path": receptor_pdbqt,
        "box_center_angstrom": center,
        "box_size_angstrom": size,
    }
    decoys = _size_matched_decoys()
    print(f"SpeB dyad box center {center} size {size} ({dyad_atoms} side-chain atoms)")
    print(f"Size-matched decoy panel: {len(decoys)} compounds")

    results = []
    for compound in [POSITIVE] + decoys:
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
        interactions = analyze_pose_interactions(
            PROJECT_ROOT / receptor_pdbqt, PROJECT_ROOT / row["out_path"], ACTIVE_SITE
        )
        affinity = row["best_affinity_kcal_mol"]
        heavy = ligand["heavy_atom_count"]
        results.append(
            {
                "ligand_id": compound["ligand_id"],
                "role": compound["role"],
                "docked_smiles": ligand["docked_smiles"],
                "formal_charge": ligand["formal_charge"],
                "heavy_atom_count": heavy,
                "best_affinity_kcal_mol": affinity,
                "ligand_efficiency_kcal_mol_per_heavy_atom": affinity / heavy,
                "contacted_dyad": interactions["contacted_active_site_residues"],
            }
        )
        print(f"  {compound['ligand_id']:<24} heavy={heavy:<3} best={affinity:6.2f}  "
              f"LE={affinity / heavy:6.3f}  dyad={interactions['contacted_active_site_residues'] or '-'}")

    positive = next(r for r in results if r["ligand_id"] == POSITIVE["ligand_id"])
    decoy_rows = [r for r in results if r["role"] == "decoy"]

    def _verdict(key: str) -> dict:
        values = [r[key] for r in decoy_rows]
        best = min(values)
        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / (len(values) - 1)
        sd = variance ** 0.5
        return {
            "positive": positive[key],
            "best_decoy": best,
            "decoy_mean": mean,
            "decoy_sd": sd,
            "margin_to_best_decoy": best - positive[key],
            "sd_beyond_decoy_mean": (mean - positive[key]) / sd if sd else None,
            "positive_outscores_all_decoys": positive[key] < best,
            "positive_rank": sorted(r[key] for r in results).index(positive[key]) + 1,
        }

    by_affinity = _verdict("best_affinity_kcal_mol")
    by_efficiency = _verdict("ligand_efficiency_kcal_mol_per_heavy_atom")

    manifest = {
        "status": "speb_positive_control_pipeline_validation",
        "receptor": "6UKD chain A (streptopain/SpeB, catalytic dyad Cys192/His340)",
        "positive_control_ligand": "Q9D (RCSB chemcomp; co-crystallized covalent inhibitor)",
        "box_basis": "Cys192/His340 side-chain atoms only; the co-crystallised ligand is not used",
        "box_center_angstrom": center,
        "box_size_angstrom": size,
        "dyad_side_chain_atom_count": dyad_atoms,
        "decoy_selection": (
            f"FDA comparators from the tracked library within +/-{HEAVY_ATOM_TOLERANCE} heavy atoms "
            f"of Q9D ({positive['heavy_atom_count']}); drugs whose mechanism is protease inhibition "
            "are labelled protease_inhibitor_comparator and excluded from the decoy statistics"
        ),
        "decoy_count": len(decoy_rows),
        "by_best_affinity": by_affinity,
        "by_ligand_efficiency": by_efficiency,
        "passes_on_both_metrics": (
            by_affinity["positive_outscores_all_decoys"] and by_efficiency["positive_outscores_all_decoys"]
        ),
        "results": sorted(results, key=lambda r: r["best_affinity_kcal_mol"]),
    }
    RESULT.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    print()
    print(f"By best affinity     : Q9D {by_affinity['positive']:.2f}, best decoy {by_affinity['best_decoy']:.2f}, "
          f"rank {by_affinity['positive_rank']}/{len(results)}, beats all decoys: {by_affinity['positive_outscores_all_decoys']}")
    print(f"By ligand efficiency : Q9D {by_efficiency['positive']:.3f}, best decoy {by_efficiency['best_decoy']:.3f}, "
          f"rank {by_efficiency['positive_rank']}/{len(results)}, beats all decoys: {by_efficiency['positive_outscores_all_decoys']}")
    print(f"Positive control passes on BOTH metrics: {manifest['passes_on_both_metrics']}")
    print(f"Wrote {RESULT.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()

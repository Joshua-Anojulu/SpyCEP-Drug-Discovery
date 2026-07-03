"""Dock the boron-containing compounds via a gem-diol surrogate.

AutoDock Vina has no boron forcefield parameters, so the four boronic acids in
the library cannot be docked directly. As a documented surrogate, each boron is
converted to carbon, turning R-B(OH)2 into the R-CH(OH)2 gem-diol -- a tetrahedral
transition-state mimic of what the boronate targets. These are approximate stand-ins
(they drop boron's covalent/electronic character) and are reported separately from
the main docking result, never merged into it.

Run (after scripts/define_tight_pockets.py; needs tools/vina.exe):
    .\\.venv\\Scripts\\python.exe scripts\\dock_boron_surrogates.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from rdkit import Chem

from spycep_drug_discovery.docking import dock_ligand
from spycep_drug_discovery.interaction_analysis import analyze_pose_interactions
from spycep_drug_discovery.ligand_preparation import prepare_ligand

VINA = PROJECT_ROOT / "tools" / "vina.exe"
MEEKO = PROJECT_ROOT / ".venv" / "Scripts" / "mk_prepare_ligand.exe"
LIBRARY = PROJECT_ROOT / "docs" / "methods" / "compound_library_source.json"
TIGHT_POCKETS = PROJECT_ROOT / "docs" / "methods" / "tight_pocket_definition.json"
POCKETS = PROJECT_ROOT / "docs" / "methods" / "pocket_definition.json"
RESULT = PROJECT_ROOT / "docs" / "methods" / "boron_surrogate_result.json"

BORON_LIGANDS = {"phenylboronic_acid", "4_carboxyphenylboronic_acid", "bortezomib", "ixazomib"}


def _boron_to_carbon(smiles: str) -> str:
    rw = Chem.RWMol(Chem.MolFromSmiles(smiles))
    for atom in rw.GetAtoms():
        if atom.GetAtomicNum() == 5:
            atom.SetAtomicNum(6)
    mol = rw.GetMol()
    Chem.SanitizeMol(mol)
    return Chem.MolToSmiles(mol)


def main() -> None:
    compounds = {c["ligand_id"]: c for c in json.loads(LIBRARY.read_text(encoding="utf-8"))["compounds"]}
    receptors = json.loads(TIGHT_POCKETS.read_text(encoding="utf-8"))["pockets"]
    active_site = json.loads(POCKETS.read_text(encoding="utf-8"))["active_site_residues"]

    results = []
    for ligand_id in sorted(BORON_LIGANDS):
        original = compounds[ligand_id]
        surrogate_smiles = _boron_to_carbon(original["smiles"])
        ligand = prepare_ligand(
            {"ligand_id": f"{ligand_id}_gemdiol", "smiles": surrogate_smiles},
            project_root=PROJECT_ROOT,
            work_dir=PROJECT_ROOT / "data" / "compounds" / "sdf",
            output_dir=PROJECT_ROOT / "data" / "compounds" / "pdbqt",
            meeko_command=[MEEKO],
        )
        for receptor in receptors:
            row = dock_ligand(
                vina_executable=VINA,
                receptor={
                    "pocket_id": receptor["pocket_id"],
                    "pdb_id": receptor["pdb_id"],
                    "receptor_pdbqt_path": receptor["receptor_pdbqt_path"],
                    "box_center_angstrom": receptor["box_center_angstrom"],
                    "box_size_angstrom": receptor["box_size_angstrom"],
                },
                ligand_id=f"{ligand_id}_gemdiol",
                ligand_pdbqt=PROJECT_ROOT / ligand["pdbqt_path"],
                project_root=PROJECT_ROOT,
                output_dir=PROJECT_ROOT / "results" / "docking" / "boron_surrogate",
            )
            interactions = analyze_pose_interactions(
                PROJECT_ROOT / receptor["receptor_pdbqt_path"],
                PROJECT_ROOT / row["out_path"],
                active_site,
            )
            results.append(
                {
                    "parent_ligand_id": ligand_id,
                    "surrogate_smiles": surrogate_smiles,
                    "pocket_id": receptor["pocket_id"],
                    "best_affinity_kcal_mol": row["best_affinity_kcal_mol"],
                    "ligand_efficiency_kcal_mol_per_heavy_atom": row["best_affinity_kcal_mol"] / ligand["heavy_atom_count"],
                    "contacted_active_site_residues": interactions["contacted_active_site_residues"],
                }
            )
            print(f"  {ligand_id}_gemdiol vs {receptor['pocket_id']}: best={row['best_affinity_kcal_mol']:.2f}")

    RESULT.write_text(
        json.dumps(
            {
                "status": "boron_gemdiol_surrogate_approximation_not_merged_into_main_result",
                "method": "each boron replaced by carbon (R-B(OH)2 -> R-CH(OH)2 gem-diol TS mimic); Vina lacks boron parameters",
                "caveat": "Surrogates approximate sterics/H-bonding only; they drop boron covalent/electronic character. Interpret as indicative, not quantitative.",
                "box_mode": "tight_triad_centered",
                "results": results,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {RESULT.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()

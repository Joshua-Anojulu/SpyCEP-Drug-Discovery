import csv

from spycep_drug_discovery.docking_analysis import rank_docking_results, write_ranking_csv


RESULTS = [
    {"ligand_id": "lig_a", "pocket_id": "spycep_5xya_aes_active_site", "role": "positive", "heavy_atom_count": 9, "best_affinity_kcal_mol": -7.2},
    {"ligand_id": "lig_a", "pocket_id": "spycep_7edd_native_active_site", "role": "positive", "heavy_atom_count": 9, "best_affinity_kcal_mol": -6.8},
    {"ligand_id": "lig_b", "pocket_id": "spycep_5xya_aes_active_site", "role": "decoy", "heavy_atom_count": 20, "best_affinity_kcal_mol": -8.1},
    {"ligand_id": "lig_b", "pocket_id": "spycep_7edd_native_active_site", "role": "decoy", "heavy_atom_count": 20, "best_affinity_kcal_mol": -7.9},
]


def test_rank_by_affinity_favors_larger_ligand():
    ranked = rank_docking_results(RESULTS)

    by_affinity = sorted(ranked, key=lambda item: item["rank_by_affinity"])
    # lig_b has the stronger raw affinity purely because it is larger.
    assert by_affinity[0]["ligand_id"] == "lig_b"
    assert by_affinity[0]["ensemble_best_affinity_kcal_mol"] == -8.1


def test_primary_rank_uses_ligand_efficiency_to_correct_size_bias():
    ranked = rank_docking_results(RESULTS)

    # By ligand efficiency the smaller, tighter-per-atom binder wins.
    assert ranked[0]["ligand_id"] == "lig_a"
    assert ranked[0]["rank"] == 1
    assert ranked[0]["ligand_efficiency_kcal_mol_per_heavy_atom"] == -7.2 / 9


def test_write_ranking_csv_roundtrips(tmp_path):
    ranked = rank_docking_results(RESULTS)
    out = tmp_path / "ranking.csv"

    write_ranking_csv(ranked, out)

    rows = list(csv.DictReader(out.open(encoding="utf-8")))
    assert rows[0]["ligand_id"] == "lig_a"
    assert rows[0]["rank"] == "1"
    assert rows[0]["heavy_atom_count"] == "9"

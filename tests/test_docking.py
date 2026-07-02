from pathlib import Path

import pytest

from spycep_drug_discovery.docking import (
    DEFAULT_EXHAUSTIVENESS,
    DEFAULT_NUM_MODES,
    DEFAULT_SEED,
    DockingError,
    build_vina_command,
    parse_vina_modes,
    summarize_docking,
)


VINA_STDOUT = """Computing Vina grid ... done.
Performing docking (random seed: 42) ...
mode |   affinity | dist from best mode
     | (kcal/mol) | rmsd l.b.| rmsd u.b.
-----+------------+----------+----------
   1       -4.897          0          0
   2       -4.845    0.08604      1.614
   3       -4.622      9.624      10.57
"""


def test_parse_vina_modes_reads_affinity_table():
    modes = parse_vina_modes(VINA_STDOUT)

    assert len(modes) == 3
    assert modes[0] == {"mode": 1, "affinity_kcal_mol": -4.897, "rmsd_lb": 0.0, "rmsd_ub": 0.0}
    assert modes[1]["affinity_kcal_mol"] == -4.845
    assert modes[2]["rmsd_ub"] == 10.57


def test_parse_vina_modes_returns_empty_without_table():
    assert parse_vina_modes("no docking table here") == ()


def test_summarize_docking_reports_best_and_mean():
    modes = parse_vina_modes(VINA_STDOUT)

    summary = summarize_docking(modes)

    assert summary["best_affinity_kcal_mol"] == -4.897
    assert summary["mode_count"] == 3
    assert summary["mean_affinity_kcal_mol"] == pytest.approx((-4.897 - 4.845 - 4.622) / 3)


def test_build_vina_command_includes_box_seed_and_settings():
    command = build_vina_command(
        vina_executable="tools/vina.exe",
        receptor_pdbqt="data/processed/pdbqt/spycep_5xya_aes_active_site.pdbqt",
        ligand_pdbqt="results/docking/lig.pdbqt",
        box_center={"x": -43.74, "y": 28.233, "z": 26.561},
        box_size={"x": 22.0, "y": 22.0, "z": 27.5},
        out_path=Path("results/docking/lig_5xya_out.pdbqt"),
        seed=DEFAULT_SEED,
        exhaustiveness=DEFAULT_EXHAUSTIVENESS,
        num_modes=DEFAULT_NUM_MODES,
    )

    assert command[0] == "tools/vina.exe"
    assert "--receptor" in command
    assert "--seed" in command and str(DEFAULT_SEED) in command
    assert "--center_x" in command and "-43.740" in command
    assert "--size_z" in command and "27.500" in command
    assert "--exhaustiveness" in command and "8" in command
    assert "--num_modes" in command and "9" in command


def test_summarize_docking_raises_on_empty():
    with pytest.raises(DockingError):
        summarize_docking(())

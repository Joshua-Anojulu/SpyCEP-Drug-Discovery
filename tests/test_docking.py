import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from spycep_drug_discovery.docking import (
    DEFAULT_CPU,
    DEFAULT_EXHAUSTIVENESS,
    DEFAULT_NUM_MODES,
    DEFAULT_SCORING,
    DEFAULT_SEED,
    DockingError,
    build_vina_command,
    dock_ligand,
    parse_pose_pdbqt_modes,
    parse_vina_modes,
    summarize_docking,
)


POSE_PDBQT = """MODEL 1
REMARK VINA RESULT:      -5.367      0.000      0.000
ATOM      1  C   LIG A 900      10.0  1.0  0.0  1.00  0.00     0.000 C
ENDMDL
MODEL 2
REMARK VINA RESULT:      -5.100      1.234      2.345
ENDMDL
"""


def test_parse_pose_pdbqt_modes_recovers_affinities():
    modes = parse_pose_pdbqt_modes(POSE_PDBQT)

    assert len(modes) == 2
    assert modes[0]["affinity_kcal_mol"] == -5.367
    assert modes[1]["rmsd_ub"] == 2.345


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



def _docking_inputs(tmp_path):
    ligand = tmp_path / "ligand.pdbqt"
    receptor = tmp_path / "receptor.pdbqt"
    ligand.write_text("ATOM ligand\n", encoding="utf-8")
    receptor.write_text("ATOM receptor\n", encoding="utf-8")
    return ligand, {
        "pocket_id": "fake_pocket",
        "pdb_id": "FAKE",
        "receptor_pdbqt_path": receptor,
        "box_center_angstrom": {"x": 1, "y": 2, "z": 3},
        "box_size_angstrom": {"x": 18, "y": 18, "z": 18},
    }


def _successful_vina(command, **_kwargs):
    out_path = Path(command[command.index("--out") + 1])
    out_path.write_text(POSE_PDBQT, encoding="utf-8")
    return SimpleNamespace(returncode=0, stdout=VINA_STDOUT, stderr="")


def _dock(tmp_path, monkeypatch, **overrides):
    ligand, receptor = _docking_inputs(tmp_path)
    monkeypatch.setattr("spycep_drug_discovery.docking.subprocess.run", _successful_vina)
    kwargs = {
        "vina_executable": sys.executable,
        "receptor": receptor,
        "entity_id": "entity",
        "state_id": "state_a",
        "ligand_pdbqt": ligand,
        "project_root": tmp_path,
        "output_dir": tmp_path / "poses",
        "workflow": "wide",
        "species_catalog_sha256": "a" * 64,
        "attempt_manifest_sha256": "b" * 64,
        "software_versions": {"rdkit": "test", "meeko": "test", "vina": "test"},
    }
    kwargs.update(overrides)
    return dock_ligand(**kwargs), ligand, receptor, kwargs


def test_dock_ligand_writes_state_keyed_pose_and_atomic_provenance_sidecar(tmp_path, monkeypatch):
    record, _, _, _ = _dock(tmp_path, monkeypatch)

    assert record["status"] == "valid_fit"
    assert record["valid_fit"] is True
    assert record["entity_id"] == "entity"
    assert record["state_id"] == "state_a"
    assert record["cpu"] == DEFAULT_CPU == 1
    assert record["scoring"] == DEFAULT_SCORING == "vina"
    assert "--cpu" in record["command"] and "1" in record["command"]
    assert "--scoring" in record["command"] and "vina" in record["command"]
    assert "<resumed from existing pose file>" not in record["command"]
    assert "entity__state_a__fake_pocket.pdbqt" in record["out_path"]
    assert Path(tmp_path / record["out_path"]).is_file()
    sidecar = json.loads((tmp_path / record["sidecar_path"]).read_text(encoding="utf-8"))
    assert sidecar["fingerprint"] == record["fingerprint"]
    assert sidecar["out_sha256"] == record["out_sha256"]
    assert not any(str(tmp_path).replace("\\", "/") in token for token in record["command"])


def test_resume_requires_exact_fingerprint_and_preserves_full_command(tmp_path, monkeypatch):
    fresh, _, _, kwargs = _dock(tmp_path, monkeypatch)

    def must_not_run(*_args, **_kwargs):
        raise AssertionError("exact resume must not invoke Vina")

    monkeypatch.setattr("spycep_drug_discovery.docking.subprocess.run", must_not_run)
    resumed = dock_ligand(**kwargs, resume=True)

    assert resumed["resumed"] is True
    assert resumed["command"] == fresh["command"]
    assert resumed["fingerprint"] == fresh["fingerprint"]

    with pytest.raises(DockingError, match="fingerprint"):
        dock_ligand(**kwargs, resume=True, timeout_seconds=1799)


def test_resume_rejects_output_hash_tampering(tmp_path, monkeypatch):
    record, _, _, kwargs = _dock(tmp_path, monkeypatch)
    (tmp_path / record["out_path"]).write_text(POSE_PDBQT + "REMARK tampered\n", encoding="utf-8")

    with pytest.raises(DockingError, match="hash agreement"):
        dock_ligand(**kwargs, resume=True)


def test_no_fit_marker_has_same_fingerprint_budget_and_sidecar_guards(tmp_path, monkeypatch):
    ligand, receptor = _docking_inputs(tmp_path)

    def timeout(command, **_kwargs):
        raise subprocess.TimeoutExpired(command, timeout=7)

    monkeypatch.setattr("spycep_drug_discovery.docking.subprocess.run", timeout)
    kwargs = {
        "vina_executable": sys.executable,
        "receptor": receptor,
        "entity_id": "entity",
        "state_id": "state_timeout",
        "ligand_pdbqt": ligand,
        "project_root": tmp_path,
        "output_dir": tmp_path / "poses",
        "workflow": "speb",
        "species_catalog_sha256": "a" * 64,
        "attempt_manifest_sha256": "b" * 64,
        "timeout_seconds": 7,
    }
    with pytest.raises(DockingError) as caught:
        dock_ligand(**kwargs)
    record = caught.value.run_record

    assert record["status"] == "no_fit"
    assert record["cause"] == "timeout"
    assert record["timeout_seconds"] == 7
    assert Path(tmp_path / record["out_path"]).suffix == ".no_fit"
    assert Path(tmp_path / record["sidecar_path"]).is_file()

    with pytest.raises(DockingError, match="fingerprint"):
        dock_ligand(**{**kwargs, "resume": True, "timeout_seconds": 8})

    with pytest.raises(DockingError) as exact:
        dock_ligand(**{**kwargs, "resume": True})
    assert exact.value.run_record["fingerprint"] == record["fingerprint"]


def test_fresh_run_removes_pose_marker_sidecar_and_temp_as_one_attempt(tmp_path, monkeypatch):
    ligand, receptor = _docking_inputs(tmp_path)
    output = tmp_path / "poses"
    output.mkdir()
    base = "entity__state_a__fake_pocket"
    suffixes = (".pdbqt", ".no_fit", ".run.json", ".pdbqt.tmp", ".no_fit.tmp", ".run.json.tmp")
    for suffix in suffixes:
        (output / f"{base}{suffix}").write_text("stale", encoding="utf-8")

    monkeypatch.setattr("spycep_drug_discovery.docking.subprocess.run", _successful_vina)
    record = dock_ligand(
        vina_executable=sys.executable,
        receptor=receptor,
        entity_id="entity",
        state_id="state_a",
        ligand_pdbqt=ligand,
        project_root=tmp_path,
        output_dir=output,
        workflow="wide",
        species_catalog_sha256="a" * 64,
        attempt_manifest_sha256="b" * 64,
    )

    assert record["status"] == "valid_fit"
    assert not (output / f"{base}.no_fit").exists()
    assert not any(
        (output / f"{base}{suffix}").exists()
        for suffix in (".pdbqt.tmp", ".no_fit.tmp", ".run.json.tmp")
    )

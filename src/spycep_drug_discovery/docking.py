from __future__ import annotations

import hashlib
import re
import subprocess
from pathlib import Path
from statistics import mean
from typing import Any, Mapping, Sequence


DOCKING_VERSION = "2026-07-02"
DOCKING_OUTPUT_DIR = "results/docking"
DEFAULT_SEED = 42
DEFAULT_EXHAUSTIVENESS = 8
DEFAULT_NUM_MODES = 9

_MODE_ROW = re.compile(
    r"^\s*(\d+)\s+(-?\d+\.\d+)\s+(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)\s*$"
)


class DockingError(RuntimeError):
    """Raised when a docking run fails or produces no scored poses."""


def build_vina_command(
    *,
    vina_executable: str | Path,
    receptor_pdbqt: str | Path,
    ligand_pdbqt: str | Path,
    box_center: Mapping[str, Any],
    box_size: Mapping[str, Any],
    out_path: Path,
    seed: int = DEFAULT_SEED,
    exhaustiveness: int = DEFAULT_EXHAUSTIVENESS,
    num_modes: int = DEFAULT_NUM_MODES,
) -> list[str]:
    return [
        str(vina_executable),
        "--receptor", str(receptor_pdbqt),
        "--ligand", str(ligand_pdbqt),
        "--center_x", _fmt(box_center["x"]),
        "--center_y", _fmt(box_center["y"]),
        "--center_z", _fmt(box_center["z"]),
        "--size_x", _fmt(box_size["x"]),
        "--size_y", _fmt(box_size["y"]),
        "--size_z", _fmt(box_size["z"]),
        "--seed", str(seed),
        "--exhaustiveness", str(exhaustiveness),
        "--num_modes", str(num_modes),
        "--out", str(out_path),
    ]


def parse_vina_modes(stdout: str) -> tuple[dict[str, Any], ...]:
    modes: list[dict[str, Any]] = []
    in_table = False
    for line in stdout.splitlines():
        if line.strip().startswith("-----+"):
            in_table = True
            continue
        if not in_table:
            continue
        match = _MODE_ROW.match(line)
        if not match:
            if modes:
                break
            continue
        modes.append(
            {
                "mode": int(match.group(1)),
                "affinity_kcal_mol": float(match.group(2)),
                "rmsd_lb": float(match.group(3)),
                "rmsd_ub": float(match.group(4)),
            }
        )
    return tuple(modes)


def summarize_docking(modes: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    if not modes:
        raise DockingError("Docking produced no scored poses.")
    affinities = [float(mode["affinity_kcal_mol"]) for mode in modes]
    return {
        "best_affinity_kcal_mol": min(affinities),
        "mean_affinity_kcal_mol": mean(affinities),
        "mode_count": len(affinities),
    }


def dock_ligand(
    *,
    vina_executable: str | Path,
    receptor: Mapping[str, Any],
    ligand_id: str,
    ligand_pdbqt: str | Path,
    project_root: Path,
    output_dir: Path,
    seed: int = DEFAULT_SEED,
    exhaustiveness: int = DEFAULT_EXHAUSTIVENESS,
    num_modes: int = DEFAULT_NUM_MODES,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / f"{ligand_id}__{receptor['pocket_id']}.pdbqt"
    command = build_vina_command(
        vina_executable=vina_executable,
        receptor_pdbqt=receptor["receptor_pdbqt_path"],
        ligand_pdbqt=ligand_pdbqt,
        box_center=receptor["box_center_angstrom"],
        box_size=receptor["box_size_angstrom"],
        out_path=out_path,
        seed=seed,
        exhaustiveness=exhaustiveness,
        num_modes=num_modes,
    )
    completed = subprocess.run(command, cwd=project_root, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        raise DockingError(
            f"{ligand_id} vs {receptor['pocket_id']} docking failed "
            f"(exit {completed.returncode}): {_tail(completed.stderr) or _tail(completed.stdout)}"
        )
    modes = parse_vina_modes(completed.stdout)
    summary = summarize_docking(modes)
    return {
        "ligand_id": ligand_id,
        "pocket_id": receptor["pocket_id"],
        "pdb_id": receptor.get("pdb_id"),
        "command": command,
        "seed": seed,
        "exhaustiveness": exhaustiveness,
        "num_modes": num_modes,
        "out_path": _relative_path(out_path, project_root),
        "out_sha256": _sha256(out_path),
        "modes": list(modes),
        **summary,
    }


def _fmt(value: Any) -> str:
    return f"{float(value):.3f}"


def _tail(text: str, line_count: int = 15) -> str:
    return "\n".join(text.splitlines()[-line_count:])


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _relative_path(path: Path, project_root: Path) -> str:
    try:
        return path.resolve().relative_to(project_root.resolve()).as_posix()
    except ValueError:
        return str(path)

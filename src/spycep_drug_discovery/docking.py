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
# A ligand that fits its search box poses in minutes. Anything still searching after
# half an hour is not going to fit: vancomycin (101 heavy atoms) ran for five hours
# against the 16 A triad box without returning a pose. Compounds that exhaust this
# budget are recorded as non-fits for that box, the same treatment given to the
# non-negative clash scores Vina returns for oversized ligands.
DEFAULT_TIMEOUT_SECONDS = 600.0

_MODE_ROW = re.compile(
    r"^\s*(\d+)\s+(-?\d+\.\d+)\s+(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)\s*$"
)
_POSE_RESULT = re.compile(r"^REMARK VINA RESULT:\s+(-?\d+\.\d+)\s+(-?\d+\.\d+)\s+(-?\d+\.\d+)")


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


def parse_pose_pdbqt_modes(text: str) -> tuple[dict[str, Any], ...]:
    """Recover docked modes from a Vina output pose file's REMARK VINA RESULT lines."""
    modes: list[dict[str, Any]] = []
    for line in text.splitlines():
        match = _POSE_RESULT.match(line.strip())
        if match:
            modes.append(
                {
                    "mode": len(modes) + 1,
                    "affinity_kcal_mol": float(match.group(1)),
                    "rmsd_lb": float(match.group(2)),
                    "rmsd_ub": float(match.group(3)),
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
    resume: bool = False,
    timeout_seconds: float | None = DEFAULT_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    """Dock one ligand into one receptor box.

    `resume` defaults to False. A pose file on disk carries no record of the ligand
    chemistry or box that produced it, so resuming silently reuses poses after a change
    to protonation, stereochemistry or box definition. Opt in only when re-running an
    identical configuration.

    `timeout_seconds` bounds a single Vina call. A ligand far too large for the search
    box does not fail; it thrashes. Vancomycin (101 heavy atoms) ran for five hours
    against the 16 A triad box without producing a pose. A timeout turns that into a
    recorded non-fit instead of a hung pipeline.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / f"{ligand_id}__{receptor['pocket_id']}.pdbqt"
    # A ligand that exhausted the budget once will exhaust it again. Record the verdict
    # so a resumed run skips it instead of re-spending the timeout on every restart.
    timeout_marker = output_dir / f"{ligand_id}__{receptor['pocket_id']}.no_fit"

    if resume and timeout_marker.is_file():
        raise DockingError(
            f"{ligand_id} vs {receptor['pocket_id']}: no pose within the compute budget on a "
            f"previous run (see {timeout_marker.name}). The ligand is too large for this search box."
        )

    if resume and out_path.is_file():
        existing_modes = parse_pose_pdbqt_modes(out_path.read_text(encoding="utf-8"))
        if existing_modes:
            summary = summarize_docking(existing_modes)
            return {
                "ligand_id": ligand_id,
                "pocket_id": receptor["pocket_id"],
                "pdb_id": receptor.get("pdb_id"),
                "command": ["<resumed from existing pose file>"],
                "seed": seed,
                "exhaustiveness": exhaustiveness,
                "num_modes": num_modes,
                "out_path": _relative_path(out_path, project_root),
                "out_sha256": _sha256(out_path),
                "modes": list(existing_modes),
                "resumed": True,
                **summary,
            }

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
    try:
        completed = subprocess.run(
            command,
            cwd=project_root,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        out_path.unlink(missing_ok=True)  # a partial pose file is not a result
        timeout_marker.write_text(
            f"No pose within {timeout_seconds:.0f}s against box "
            f"{receptor['box_size_angstrom']}. Ligand too large for this search box.\n",
            encoding="utf-8",
        )
        raise DockingError(
            f"{ligand_id} vs {receptor['pocket_id']} produced no pose within "
            f"{timeout_seconds:.0f}s. The ligand is too large for this search box."
        ) from exc
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

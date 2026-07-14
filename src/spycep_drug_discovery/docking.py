from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import time
from pathlib import Path
from statistics import mean
from typing import Any, Mapping, Sequence


DOCKING_VERSION = "2026-07-13-stage1"
RUN_SCHEMA_VERSION = "docking-run-record-v1"
DOCKING_OUTPUT_DIR = "results/docking"
DEFAULT_SEED = 42
DEFAULT_EXHAUSTIVENESS = 8
DEFAULT_NUM_MODES = 9
DEFAULT_CPU = 1
DEFAULT_SCORING = "vina"
DEFAULT_TIMEOUT_SECONDS = 1800.0

RUN_RECORD_REQUIRED_FIELDS = frozenset(
    {
        "run_schema_version",
        "fingerprint",
        "fingerprint_payload",
        "workflow",
        "claim_key",
        "entity_id",
        "state_id",
        "species_key",
        "pocket_id",
        "pdb_id",
        "command",
        "ligand_pdbqt_path",
        "ligand_pdbqt_sha256",
        "receptor_pdbqt_path",
        "receptor_pdbqt_sha256",
        "vina_binary_sha256",
        "box_center_angstrom",
        "box_size_angstrom",
        "seed",
        "exhaustiveness",
        "num_modes",
        "cpu",
        "scoring",
        "timeout_seconds",
        "species_catalog_sha256",
        "attempt_manifest_sha256",
        "software_versions",
        "elapsed_seconds",
        "status",
        "cause",
        "exit_code",
        "out_path",
        "out_sha256",
        "sidecar_path",
        "resumed",
        "valid_fit",
    }
)

_MODE_ROW = re.compile(
    r"^\s*(\d+)\s+(-?\d+\.\d+)\s+(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)\s*$"
)
_POSE_RESULT = re.compile(
    r"^REMARK VINA RESULT:\s+(-?\d+\.\d+)\s+(-?\d+\.\d+)\s+(-?\d+\.\d+)"
)


class DockingError(RuntimeError):
    """Raised when a docking attempt is invalid or does not yield a valid fit."""

    def __init__(self, message: str, *, run_record: Mapping[str, Any] | None = None):
        super().__init__(message)
        self.run_record = dict(run_record) if run_record is not None else None


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
    cpu: int = DEFAULT_CPU,
    scoring: str = DEFAULT_SCORING,
) -> list[str]:
    return [
        str(vina_executable),
        "--receptor",
        str(receptor_pdbqt),
        "--ligand",
        str(ligand_pdbqt),
        "--center_x",
        _fmt(box_center["x"]),
        "--center_y",
        _fmt(box_center["y"]),
        "--center_z",
        _fmt(box_center["z"]),
        "--size_x",
        _fmt(box_size["x"]),
        "--size_y",
        _fmt(box_size["y"]),
        "--size_z",
        _fmt(box_size["z"]),
        "--seed",
        str(seed),
        "--exhaustiveness",
        str(exhaustiveness),
        "--num_modes",
        str(num_modes),
        "--cpu",
        str(cpu),
        "--scoring",
        scoring,
        "--out",
        str(out_path),
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
    """Recover docked modes from a Vina output pose file."""
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
    entity_id: str | None = None,
    state_id: str = "state_01",
    ligand_id: str | None = None,
    ligand_pdbqt: str | Path,
    project_root: Path,
    output_dir: Path,
    workflow: str = "unspecified",
    species_catalog_sha256: str = "",
    attempt_manifest_sha256: str = "",
    software_versions: Mapping[str, Any] | None = None,
    seed: int = DEFAULT_SEED,
    exhaustiveness: int = DEFAULT_EXHAUSTIVENESS,
    num_modes: int = DEFAULT_NUM_MODES,
    cpu: int = DEFAULT_CPU,
    scoring: str = DEFAULT_SCORING,
    resume: bool = False,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    """Dock one catalog state with content-addressed resume and an atomic sidecar."""
    entity_id = str(entity_id or ligand_id or "")
    state_id = str(state_id)
    if not entity_id:
        raise DockingError("dock_ligand requires entity_id.")
    if not state_id:
        raise DockingError("dock_ligand requires state_id.")
    if timeout_seconds <= 0:
        raise DockingError("timeout_seconds must be positive.")

    project_root = project_root.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    base = (
        f"{_filename_component(entity_id)}__{_filename_component(state_id)}"
        f"__{_filename_component(str(receptor['pocket_id']))}"
    )
    out_path = output_dir / f"{base}.pdbqt"
    marker_path = output_dir / f"{base}.no_fit"
    sidecar_path = output_dir / f"{base}.run.json"
    temporary_paths = (
        output_dir / f"{base}.pdbqt.tmp",
        output_dir / f"{base}.no_fit.tmp",
        output_dir / f"{base}.run.json.tmp",
    )

    ligand_path = _resolve_project_path(ligand_pdbqt, project_root)
    receptor_path = _resolve_project_path(receptor["receptor_pdbqt_path"], project_root)
    vina_path = _resolve_project_path(vina_executable, project_root)
    for label, path in (
        ("ligand PDBQT", ligand_path),
        ("receptor PDBQT", receptor_path),
        ("Vina binary", vina_path),
    ):
        if not path.is_file():
            raise DockingError(f"{label} does not exist: {path}")

    command = build_vina_command(
        vina_executable=vina_path,
        receptor_pdbqt=receptor_path,
        ligand_pdbqt=ligand_path,
        box_center=receptor["box_center_angstrom"],
        box_size=receptor["box_size_angstrom"],
        out_path=out_path,
        seed=seed,
        exhaustiveness=exhaustiveness,
        num_modes=num_modes,
        cpu=cpu,
        scoring=scoring,
    )
    normalized_command = normalize_command(command, project_root)
    fingerprint_payload = {
        "run_schema_version": RUN_SCHEMA_VERSION,
        "command": normalized_command,
        "entity_id": entity_id,
        "state_id": state_id,
        "ligand_pdbqt_sha256": _sha256(ligand_path),
        "receptor_pdbqt_sha256": _sha256(receptor_path),
        "vina_binary_sha256": _sha256(vina_path),
        "box_center_angstrom": _axis_dict(receptor["box_center_angstrom"]),
        "box_size_angstrom": _axis_dict(receptor["box_size_angstrom"]),
        "seed": int(seed),
        "exhaustiveness": int(exhaustiveness),
        "num_modes": int(num_modes),
        "cpu": int(cpu),
        "scoring": str(scoring),
        "timeout_seconds": float(timeout_seconds),
        "species_catalog_sha256": species_catalog_sha256,
        "attempt_manifest_sha256": attempt_manifest_sha256,
    }
    fingerprint = _json_sha256(fingerprint_payload)
    common = {
        "run_schema_version": RUN_SCHEMA_VERSION,
        "fingerprint": fingerprint,
        "fingerprint_payload": fingerprint_payload,
        "workflow": workflow,
        "claim_key": f"{workflow}:{entity_id}:{state_id}:{receptor['pocket_id']}",
        "entity_id": entity_id,
        "state_id": state_id,
        "species_key": [entity_id, state_id],
        "ligand_id": entity_id,
        "pocket_id": receptor["pocket_id"],
        "pdb_id": receptor.get("pdb_id"),
        "command": normalized_command,
        "ligand_pdbqt_path": _relative_path(ligand_path, project_root),
        "ligand_pdbqt_sha256": fingerprint_payload["ligand_pdbqt_sha256"],
        "receptor_pdbqt_path": _relative_path(receptor_path, project_root),
        "receptor_pdbqt_sha256": fingerprint_payload["receptor_pdbqt_sha256"],
        "vina_binary_sha256": fingerprint_payload["vina_binary_sha256"],
        "box_center_angstrom": fingerprint_payload["box_center_angstrom"],
        "box_size_angstrom": fingerprint_payload["box_size_angstrom"],
        "seed": seed,
        "exhaustiveness": exhaustiveness,
        "num_modes": num_modes,
        "cpu": cpu,
        "scoring": scoring,
        "timeout_seconds": float(timeout_seconds),
        "species_catalog_sha256": species_catalog_sha256,
        "attempt_manifest_sha256": attempt_manifest_sha256,
        "software_versions": dict(software_versions or {}),
        "sidecar_path": _relative_path(sidecar_path, project_root),
    }

    if resume:
        return _resume_exact(
            common=common,
            fingerprint=fingerprint,
            out_path=out_path,
            marker_path=marker_path,
            sidecar_path=sidecar_path,
            project_root=project_root,
        )

    _delete_attempt_artifacts(
        out_path,
        marker_path,
        sidecar_path,
        *temporary_paths,
    )
    started = time.perf_counter()
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
        elapsed = time.perf_counter() - started
        out_path.unlink(missing_ok=True)
        _atomic_text(
            marker_path,
            f"status=timeout\ntimeout_seconds={float(timeout_seconds):.3f}\n",
        )
        record = _final_record(
            common,
            elapsed=elapsed,
            status="no_fit",
            cause="timeout",
            exit_code=None,
            output_path=marker_path,
            project_root=project_root,
            resumed=False,
            modes=(),
        )
        _atomic_json(sidecar_path, record)
        raise DockingError(
            f"{entity_id}/{state_id} vs {receptor['pocket_id']} timed out after "
            f"{timeout_seconds:.3f}s.",
            run_record=record,
        ) from exc

    elapsed = time.perf_counter() - started
    if completed.returncode != 0:
        out_path.unlink(missing_ok=True)
        _atomic_text(
            marker_path,
            f"status=vina_exit_nonzero\nexit_code={completed.returncode}\n",
        )
        record = _final_record(
            common,
            elapsed=elapsed,
            status="failed",
            cause="vina_exit_nonzero",
            exit_code=completed.returncode,
            output_path=marker_path,
            project_root=project_root,
            resumed=False,
            modes=(),
            stdout_tail=_tail(completed.stdout),
            stderr_tail=_tail(completed.stderr),
        )
        _atomic_json(sidecar_path, record)
        raise DockingError(
            f"{entity_id}/{state_id} vs {receptor['pocket_id']} docking failed "
            f"(exit {completed.returncode}): "
            f"{_tail(completed.stderr) or _tail(completed.stdout)}",
            run_record=record,
        )

    if not out_path.is_file():
        _atomic_text(marker_path, "status=missing_pose\n")
        record = _final_record(
            common,
            elapsed=elapsed,
            status="failed",
            cause="missing_pose",
            exit_code=completed.returncode,
            output_path=marker_path,
            project_root=project_root,
            resumed=False,
            modes=(),
            stdout_tail=_tail(completed.stdout),
            stderr_tail=_tail(completed.stderr),
        )
        _atomic_json(sidecar_path, record)
        raise DockingError(
            f"{entity_id}/{state_id} vs {receptor['pocket_id']} exited zero without a pose.",
            run_record=record,
        )

    modes = parse_pose_pdbqt_modes(out_path.read_text(encoding="utf-8"))
    if not modes:
        out_path.unlink(missing_ok=True)
        _atomic_text(marker_path, "status=unparseable_pose\n")
        record = _final_record(
            common,
            elapsed=elapsed,
            status="failed",
            cause="unparseable_pose",
            exit_code=completed.returncode,
            output_path=marker_path,
            project_root=project_root,
            resumed=False,
            modes=(),
            stdout_tail=_tail(completed.stdout),
            stderr_tail=_tail(completed.stderr),
        )
        _atomic_json(sidecar_path, record)
        raise DockingError(
            f"{entity_id}/{state_id} vs {receptor['pocket_id']} produced no parseable modes.",
            run_record=record,
        )

    summary = summarize_docking(modes)
    if summary["best_affinity_kcal_mol"] >= 0:
        marker_path.unlink(missing_ok=True)
        record = _final_record(
            common,
            elapsed=elapsed,
            status="operational_non_fit",
            cause="non_negative_best_affinity",
            exit_code=completed.returncode,
            output_path=out_path,
            project_root=project_root,
            resumed=False,
            modes=modes,
            stdout_tail=_tail(completed.stdout),
            stderr_tail=_tail(completed.stderr),
        )
        _atomic_json(sidecar_path, record)
        raise DockingError(
            f"{entity_id}/{state_id} vs {receptor['pocket_id']} is an operational "
            "non-fit (best affinity is non-negative).",
            run_record=record,
        )

    marker_path.unlink(missing_ok=True)
    record = _final_record(
        common,
        elapsed=elapsed,
        status="valid_fit",
        cause=None,
        exit_code=completed.returncode,
        output_path=out_path,
        project_root=project_root,
        resumed=False,
        modes=modes,
        stdout_tail=_tail(completed.stdout),
        stderr_tail=_tail(completed.stderr),
    )
    _atomic_json(sidecar_path, record)
    validate_run_record(record)
    return record


def build_run_manifest(
    *,
    workflow: str,
    run_records: Sequence[Mapping[str, Any]],
    species_catalog_sha256: str,
    attempt_manifest_sha256: str,
    software_versions: Mapping[str, Any],
    preparation_records: Sequence[Mapping[str, Any]] = (),
    metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Serialize the same validated run-record schema for every workflow."""
    records = [dict(record) for record in run_records]
    for record in records:
        validate_run_record(record)
        if record["workflow"] != workflow:
            raise DockingError(
                f"Run record workflow {record['workflow']!r} does not match {workflow!r}."
            )
        if record["species_catalog_sha256"] != species_catalog_sha256:
            raise DockingError("Run record species-catalog hash mismatch.")
        if record["attempt_manifest_sha256"] != attempt_manifest_sha256:
            raise DockingError("Run record attempt-manifest hash mismatch.")
    vina_hashes = {record["vina_binary_sha256"] for record in records}
    if len(vina_hashes) > 1:
        raise DockingError("A workflow manifest cannot mix Vina binaries.")
    from spycep_drug_discovery.ligand_preparation import (
        MMFF_MAX_ITERATIONS,
        MMFF_VARIANT,
    )

    return {
        "run_schema_version": RUN_SCHEMA_VERSION,
        "workflow": workflow,
        "status": "complete" if all(record["valid_fit"] for record in records) else "complete_with_dispositions",
        "species_catalog_sha256": species_catalog_sha256,
        "attempt_manifest_sha256": attempt_manifest_sha256,
        "software_versions": dict(software_versions),
        "vina_binary_sha256": next(iter(vina_hashes), None),
        "mmff_variant": MMFF_VARIANT,
        "mmff_max_iterations": MMFF_MAX_ITERATIONS,
        "attempt_count": len(records),
        "disposition_counts": dict(
            sorted(
                {
                    status: sum(record["status"] == status for record in records)
                    for status in {record["status"] for record in records}
                }.items()
            )
        ),
        "ligand_preparation": [dict(record) for record in preparation_records],
        "run_records": records,
        "metadata": dict(metadata or {}),
    }


def normalize_command(command: Sequence[str | Path], project_root: Path) -> list[str]:
    """Remove machine-specific absolute path prefixes from recorded commands."""
    normalized: list[str] = []
    root = project_root.resolve()
    for part in command:
        text = str(part)
        path = Path(text)
        if path.is_absolute():
            try:
                normalized.append(path.resolve().relative_to(root).as_posix())
            except ValueError:
                normalized.append(f"<ABSOLUTE>/{path.name}")
        else:
            normalized.append(text.replace("\\", "/"))
    return normalized


def validate_run_record(record: Mapping[str, Any]) -> None:
    missing = RUN_RECORD_REQUIRED_FIELDS - set(record)
    if missing:
        raise DockingError(f"Run record lacks required provenance fields: {sorted(missing)}")
    if record["run_schema_version"] != RUN_SCHEMA_VERSION:
        raise DockingError("Run-record schema version mismatch.")
    if record["command"] == ["<resumed from existing pose file>"]:
        raise DockingError("Placeholder resume commands are forbidden.")
    if record["fingerprint"] != _json_sha256(record["fingerprint_payload"]):
        raise DockingError("Run-record fingerprint does not match its payload.")
    if int(record["cpu"]) != DEFAULT_CPU:
        raise DockingError("Run record did not freeze --cpu 1.")
    if record["scoring"] != DEFAULT_SCORING:
        raise DockingError("Run record did not freeze --scoring vina.")
    if record["status"] == "valid_fit" and not record["valid_fit"]:
        raise DockingError("valid_fit status is internally inconsistent.")
    if record["status"] != "valid_fit" and record["valid_fit"]:
        raise DockingError("Non-fit status is internally inconsistent.")


def _resume_exact(
    *,
    common: Mapping[str, Any],
    fingerprint: str,
    out_path: Path,
    marker_path: Path,
    sidecar_path: Path,
    project_root: Path,
) -> dict[str, Any]:
    if not sidecar_path.is_file():
        raise DockingError(
            f"Resume refused: missing sidecar {sidecar_path.name}; file existence is not provenance."
        )
    try:
        stored = json.loads(sidecar_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DockingError(f"Resume refused: unreadable sidecar {sidecar_path.name}.") from exc
    validate_run_record(stored)
    if stored.get("fingerprint") != fingerprint or stored.get("fingerprint_payload") != common.get(
        "fingerprint_payload"
    ):
        raise DockingError("Resume refused: run fingerprint does not exactly match.")
    if stored.get("command") != common.get("command"):
        raise DockingError("Resume refused: normalized effective command mismatch.")

    output_path_text = stored.get("out_path")
    if not output_path_text or not stored.get("out_sha256"):
        raise DockingError("Resume refused: sidecar lacks output path/hash.")
    output_path = _resolve_project_path(output_path_text, project_root)
    if not output_path.is_file() or _sha256(output_path) != stored["out_sha256"]:
        raise DockingError("Resume refused: sidecar/output hash agreement failed.")
    if out_path.is_file() and marker_path.is_file():
        raise DockingError("Resume refused: both pose and no-fit marker exist.")

    record = dict(stored)
    record["resumed"] = True
    if stored["status"] == "valid_fit":
        if output_path != out_path:
            raise DockingError("Resume refused: valid-fit sidecar does not address the pose path.")
        modes = parse_pose_pdbqt_modes(output_path.read_text(encoding="utf-8"))
        if not modes:
            raise DockingError("Resume refused: pose no longer contains parseable modes.")
        record["modes"] = list(modes)
        record.update(summarize_docking(modes))
        validate_run_record(record)
        return record

    if stored["status"] in {"no_fit", "failed"} and output_path != marker_path:
        raise DockingError("Resume refused: failure sidecar does not address its marker.")
    raise DockingError(
        f"Exact resumed attempt remains {stored['status']}: {stored.get('cause')}.",
        run_record=record,
    )


def _final_record(
    common: Mapping[str, Any],
    *,
    elapsed: float,
    status: str,
    cause: str | None,
    exit_code: int | None,
    output_path: Path,
    project_root: Path,
    resumed: bool,
    modes: Sequence[Mapping[str, Any]],
    stdout_tail: str = "",
    stderr_tail: str = "",
) -> dict[str, Any]:
    record = {
        **common,
        "elapsed_seconds": elapsed,
        "status": status,
        "cause": cause,
        "exit_code": exit_code,
        "out_path": _relative_path(output_path, project_root),
        "out_sha256": _sha256(output_path),
        "resumed": resumed,
        "valid_fit": status == "valid_fit",
        "stdout_tail": stdout_tail,
        "stderr_tail": stderr_tail,
        "modes": [dict(mode) for mode in modes],
    }
    if modes:
        record.update(summarize_docking(modes))
    else:
        record.update(
            {
                "best_affinity_kcal_mol": None,
                "mean_affinity_kcal_mol": None,
                "mode_count": 0,
            }
        )
    validate_run_record(record)
    return record


def _axis_dict(values: Mapping[str, Any]) -> dict[str, float]:
    return {axis: float(_fmt(values[axis])) for axis in ("x", "y", "z")}


def _resolve_project_path(path: str | Path, project_root: Path) -> Path:
    value = Path(path)
    return value.resolve() if value.is_absolute() else (project_root / value).resolve()


def _delete_attempt_artifacts(*paths: Path) -> None:
    for path in paths:
        path.unlink(missing_ok=True)


def _atomic_text(path: Path, text: str) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    os.replace(temporary, path)


def _atomic_json(path: Path, value: Mapping[str, Any]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _filename_component(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("._")
    if not cleaned:
        raise DockingError(f"Unsafe empty filename component from {value!r}.")
    return cleaned


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


def _json_sha256(value: Mapping[str, Any]) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _relative_path(path: Path, project_root: Path) -> str:
    try:
        return path.resolve().relative_to(project_root.resolve()).as_posix()
    except ValueError:
        return f"<ABSOLUTE>/{path.name}"

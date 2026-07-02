from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path
from typing import Any, Mapping, Sequence


CONVERSION_VERSION = "2026-07-02"
PDBQT_OUTPUT_DIR = "data/processed/pdbqt"
ALLOW_BAD_RES_REASON = (
    "SpyCEP crystal structures contain incomplete residues; direct Meeko template matching fails without "
    "--allow_bad_res. Generated receptor PDBQT files require review before docking."
)
CONVERSION_RULES = (
    "Convert only receptors approved in docs/methods/receptor_preparation.json.",
    "Use Meeko mk_prepare_receptor with the tracked active-site box center and size.",
    "Use --allow_bad_res because the selected SpyCEP structures contain incomplete residues.",
    "Record output hashes and command arguments before any docking run.",
)


class PdbqtConversionError(RuntimeError):
    """Raised when the receptor-to-PDBQT converter fails or omits expected files."""


def convert_receptors_to_pdbqt(
    receptor_manifest: Mapping[str, Any],
    *,
    project_root: Path,
    output_dir: Path,
    converter_command: Sequence[str | Path],
    tool_info: Mapping[str, Any],
    allow_bad_res: bool = True,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    receptors = [
        _convert_receptor(
            receptor,
            project_root=project_root,
            output_dir=output_dir,
            converter_command=converter_command,
            allow_bad_res=allow_bad_res,
        )
        for receptor in receptor_manifest["receptors"]
    ]
    return {
        "conversion_version": CONVERSION_VERSION,
        "source_receptor_preparation": "docs/methods/receptor_preparation.json",
        "source_preparation_version": receptor_manifest.get("preparation_version"),
        "tool": dict(tool_info),
        "allow_bad_res": allow_bad_res,
        "allow_bad_res_reason": ALLOW_BAD_RES_REASON if allow_bad_res else None,
        "rules": list(CONVERSION_RULES),
        "receptors": receptors,
    }


def _convert_receptor(
    receptor: Mapping[str, Any],
    *,
    project_root: Path,
    output_dir: Path,
    converter_command: Sequence[str | Path],
    allow_bad_res: bool,
) -> dict[str, Any]:
    pocket_id = str(receptor["pocket_id"])
    prepared_pdb_path = _normalized_path(str(receptor["prepared_pdb_path"]))
    output_stem = _relative_path(output_dir / pocket_id, project_root)
    command = [str(part) for part in converter_command]
    command.extend(
        [
            "--read_pdb",
            prepared_pdb_path,
            "-o",
            output_stem,
            "--write_pdbqt",
            "--write_json",
            "--write_vina_box",
            "--box_center",
            _format_angstrom(receptor["box_center_angstrom"]["x"]),
            _format_angstrom(receptor["box_center_angstrom"]["y"]),
            _format_angstrom(receptor["box_center_angstrom"]["z"]),
            "--box_size",
            _format_angstrom(receptor["box_size_angstrom"]["x"]),
            _format_angstrom(receptor["box_size_angstrom"]["y"]),
            _format_angstrom(receptor["box_size_angstrom"]["z"]),
        ]
    )
    if allow_bad_res:
        command.append("--allow_bad_res")

    completed = subprocess.run(command, cwd=project_root, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        raise PdbqtConversionError(_failure_message(receptor, completed))

    output_paths = _expected_output_paths(output_dir, pocket_id)
    missing_outputs = [str(path) for path in output_paths.values() if not path.is_file()]
    if missing_outputs:
        raise PdbqtConversionError(f"{pocket_id} conversion omitted expected files: {', '.join(missing_outputs)}")

    return {
        "pocket_id": receptor["pocket_id"],
        "pdb_id": receptor["pdb_id"],
        "chain_id": receptor["chain_id"],
        "source_prepared_pdb_path": prepared_pdb_path,
        "source_prepared_pdb_sha256": receptor.get("sha256"),
        "box_center_angstrom": receptor["box_center_angstrom"],
        "box_size_angstrom": receptor["box_size_angstrom"],
        "command": command,
        "exit_code": completed.returncode,
        "stdout_line_count": len(completed.stdout.splitlines()),
        "stderr_line_count": len(completed.stderr.splitlines()),
        "stderr_tail": _tail(completed.stderr),
        "output_paths": {name: _relative_path(path, project_root) for name, path in output_paths.items()},
        "output_sha256": {name: _sha256(path) for name, path in output_paths.items()},
        "pdbqt_atom_records": _count_pdbqt_atom_records(output_paths["pdbqt"]),
    }


def _expected_output_paths(output_dir: Path, pocket_id: str) -> dict[str, Path]:
    return {
        "pdbqt": output_dir / f"{pocket_id}.pdbqt",
        "json": output_dir / f"{pocket_id}.json",
        "box_txt": output_dir / f"{pocket_id}.box.txt",
        "box_pdb": output_dir / f"{pocket_id}.box.pdb",
    }


def _failure_message(receptor: Mapping[str, Any], completed: subprocess.CompletedProcess[str]) -> str:
    detail = _tail(completed.stderr) or _tail(completed.stdout) or "no converter output captured"
    return f"{receptor['pocket_id']} PDBQT conversion failed with exit code {completed.returncode}: {detail}"


def _tail(text: str, line_count: int = 20) -> str:
    lines = text.splitlines()
    return "\n".join(lines[-line_count:])


def _count_pdbqt_atom_records(path: Path) -> int:
    with path.open(encoding="utf-8") as handle:
        return sum(1 for line in handle if line.startswith(("ATOM  ", "HETATM")))


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


def _normalized_path(path: str) -> str:
    return path.replace("\\", "/")


def _format_angstrom(value: Any) -> str:
    return f"{float(value):.3f}"

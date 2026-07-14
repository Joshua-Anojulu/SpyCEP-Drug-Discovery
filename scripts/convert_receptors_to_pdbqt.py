from __future__ import annotations

import argparse
import importlib.metadata
import json
from pathlib import Path
from typing import Any, Sequence

from spycep_drug_discovery.paths import project_root as find_project_root
from spycep_drug_discovery.pdbqt_conversion import convert_receptors_to_pdbqt


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Convert prepared SpyCEP receptors to PDBQT with Meeko.")
    parser.add_argument(
        "--receptor-manifest",
        type=Path,
        default=Path("docs/methods/receptor_preparation.json"),
        help="Tracked receptor-preparation manifest JSON path.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/processed/pdbqt"),
        help="Generated PDBQT output directory.",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("docs/methods/pdbqt_conversion.json"),
        help="Tracked PDBQT conversion manifest JSON path.",
    )
    parser.add_argument(
        "--converter-command",
        nargs="+",
        help="Converter command prefix. Defaults to the local .venv mk_prepare_receptor executable when present.",
    )
    parser.add_argument(
        "--strict-residues",
        action="store_true",
        help="Do not pass --allow_bad_res to Meeko. SpyCEP receptors are expected to need the default relaxed mode.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = find_project_root()
    converter_command = tuple(args.converter_command) if args.converter_command else default_converter_command(root)
    manifest = write_pdbqt_conversion(
        receptor_manifest_path=root / args.receptor_manifest,
        project_root=root,
        output_dir=root / args.output_dir,
        manifest_path=root / args.manifest,
        converter_command=converter_command,
        tool_info=meeko_tool_info(converter_command, root),
        allow_bad_res=not args.strict_residues,
    )
    print(f"Wrote {root / args.manifest}")
    for receptor in manifest["receptors"]:
        print(f"Wrote {root / receptor['output_paths']['pdbqt']}")


def write_pdbqt_conversion(
    receptor_manifest_path: Path,
    project_root: Path,
    output_dir: Path,
    manifest_path: Path,
    converter_command: Sequence[str | Path],
    tool_info: dict[str, Any] | None = None,
    allow_bad_res: bool = True,
) -> dict[str, Any]:
    receptor_manifest = json.loads(receptor_manifest_path.read_text(encoding="utf-8"))
    manifest = convert_receptors_to_pdbqt(
        receptor_manifest,
        project_root=project_root,
        output_dir=output_dir,
        converter_command=converter_command,
        tool_info=tool_info or meeko_tool_info(converter_command, project_root),
        allow_bad_res=allow_bad_res,
    )
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def default_converter_command(project_root: Path) -> tuple[str, ...]:
    candidates = (
        project_root / ".venv" / "Scripts" / "mk_prepare_receptor.exe",
        project_root / ".venv" / "bin" / "mk_prepare_receptor",
    )
    for candidate in candidates:
        if candidate.is_file():
            # Absolute, not project-relative: Windows resolves a subprocess executable
            # against the parent's working directory and PATH, never against the child's
            # `cwd`, so a relative path here raises WinError 2 even though the file exists.
            return (str(candidate.resolve()),)
    return ("mk_prepare_receptor",)


def meeko_tool_info(
    converter_command: Sequence[str | Path],
    project_root: Path | None = None,
) -> dict[str, Any]:
    return {
        "name": "Meeko mk_prepare_receptor",
        "command_path": (
            _normalised_tool_path(converter_command[0], project_root)
            if converter_command
            else None
        ),
        "meeko_version": _distribution_version("meeko"),
        "rdkit_version": _rdkit_version(),
        "gemmi_version": _distribution_version("gemmi"),
        "scipy_version": _distribution_version("scipy"),
    }


def _normalised_tool_path(value: str | Path, project_root: Path | None) -> str:
    path = Path(value)
    if project_root is not None and path.is_absolute():
        try:
            return path.resolve().relative_to(project_root.resolve()).as_posix()
        except ValueError:
            return f"<ABSOLUTE>/{path.name}"
    return str(value).replace("\\", "/")


def _distribution_version(distribution_name: str) -> str | None:
    try:
        return importlib.metadata.version(distribution_name)
    except importlib.metadata.PackageNotFoundError:
        return None


def _rdkit_version() -> str | None:
    try:
        from rdkit import rdBase
    except ImportError:
        return None
    return rdBase.rdkitVersion


if __name__ == "__main__":
    main()

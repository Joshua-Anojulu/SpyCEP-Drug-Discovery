"""Pinned chemistry-tool environment provenance."""
from __future__ import annotations

import importlib.metadata
import subprocess
from pathlib import Path
from typing import Any


PINNED_RDKIT_VERSION = "2025.09.6"
PINNED_MEEKO_VERSION = "0.7.1"


class EnvironmentPinError(RuntimeError):
    """Raised when runtime chemistry versions differ from the frozen environment."""


def chemistry_versions() -> dict[str, str]:
    from rdkit import rdBase

    return {
        "rdkit": rdBase.rdkitVersion,
        "meeko": importlib.metadata.version("meeko"),
    }


def require_pinned_chemistry_environment() -> dict[str, str]:
    versions = chemistry_versions()
    expected = {
        "rdkit": PINNED_RDKIT_VERSION,
        "meeko": PINNED_MEEKO_VERSION,
    }
    if versions != expected:
        raise EnvironmentPinError(
            f"Pinned chemistry environment mismatch: expected {expected}, observed {versions}."
        )
    return versions


def runtime_versions(vina_executable: Path) -> dict[str, Any]:
    versions: dict[str, Any] = require_pinned_chemistry_environment()
    completed = subprocess.run(
        [str(vina_executable), "--version"],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise EnvironmentPinError(
            f"Could not establish Vina version (exit {completed.returncode})."
        )
    version = (completed.stdout or completed.stderr).strip()
    if not version:
        raise EnvironmentPinError("Vina returned an empty version string.")
    versions["vina"] = version
    return versions

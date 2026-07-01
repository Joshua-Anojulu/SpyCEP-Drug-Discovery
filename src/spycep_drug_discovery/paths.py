from pathlib import Path


def project_root() -> Path:
    """Return the repository root for the SpyCEP drug discovery project."""
    return Path(__file__).resolve().parents[2]


def ensure_dir(path: Path) -> Path:
    """Create a directory if needed and return the same path."""
    path.mkdir(parents=True, exist_ok=True)
    return path

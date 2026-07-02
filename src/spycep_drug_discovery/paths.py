from pathlib import Path


class ProjectRootError(RuntimeError):
    """Raised when the project root cannot be found from the current path."""


def project_root(start: Path | None = None) -> Path:
    """Return the repository root by searching upward for stable project markers."""
    current = (start or Path(__file__)).resolve()
    if current.is_file():
        current = current.parent

    for candidate in (current, *current.parents):
        if (candidate / "pyproject.toml").is_file() and (candidate / "README.md").is_file():
            return candidate

    raise ProjectRootError(f"Could not find project root from {current}")


def ensure_dir(path: Path) -> Path:
    """Create a directory if needed and return the same path."""
    path.mkdir(parents=True, exist_ok=True)
    return path

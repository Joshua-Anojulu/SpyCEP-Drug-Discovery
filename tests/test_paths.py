from pathlib import Path

from spycep_drug_discovery.paths import ensure_dir, project_root


def test_project_root_contains_repo_markers():
    root = project_root()

    assert (root / "README.md").is_file()
    assert (root / "pyproject.toml").is_file()


def test_ensure_dir_creates_nested_directory(tmp_path):
    target = tmp_path / "nested" / "folder"

    result = ensure_dir(target)

    assert result == target
    assert target.is_dir()


def test_project_root_from_nested_path_uses_repo_markers(tmp_path):
    checkout = tmp_path / "renamed-checkout"
    nested = checkout / "src" / "spycep_drug_discovery"
    nested.mkdir(parents=True)
    (checkout / "pyproject.toml").write_text("[project]\nname = 'demo'\n", encoding="utf-8")
    (checkout / "README.md").write_text("demo", encoding="utf-8")

    assert project_root(nested / "paths.py") == checkout

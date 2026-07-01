from pathlib import Path

from spycep_drug_discovery.paths import ensure_dir, project_root


def test_project_root_contains_readme():
    root = project_root()

    assert root.name == "SpyCEP-Drug-Discovery"
    assert (root / "README.md").is_file()


def test_ensure_dir_creates_nested_directory(tmp_path):
    target = tmp_path / "nested" / "folder"

    result = ensure_dir(target)

    assert result == target
    assert target.is_dir()

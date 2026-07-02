import pytest

from spycep_drug_discovery.ligand_preparation import (
    LigandPreparationError,
    prepare_ligand,
    smiles_to_sdf,
)


def test_smiles_to_sdf_is_deterministic(tmp_path):
    first = tmp_path / "a.sdf"
    second = tmp_path / "b.sdf"

    count_a = smiles_to_sdf("NC(=N)c1ccccc1", first, seed=42)
    count_b = smiles_to_sdf("NC(=N)c1ccccc1", second, seed=42)

    assert count_a == count_b == 17
    assert first.read_text() == second.read_text()


def test_smiles_to_sdf_rejects_bad_smiles(tmp_path):
    with pytest.raises(LigandPreparationError):
        smiles_to_sdf("not-a-smiles(((", tmp_path / "x.sdf")


def test_prepare_ligand_raises_when_meeko_fails(tmp_path):
    compound = {"ligand_id": "benzamidine", "smiles": "NC(=N)c1ccccc1", "role": "positive"}

    with pytest.raises(LigandPreparationError):
        prepare_ligand(
            compound,
            project_root=tmp_path,
            work_dir=tmp_path / "work",
            output_dir=tmp_path / "out",
            # a command that runs but never writes the -o PDBQT file
            meeko_command=["python", "-c", "pass"],
        )

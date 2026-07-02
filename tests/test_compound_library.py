import pytest

from spycep_drug_discovery.compound_library import (
    CompoundLibraryError,
    summarize_library,
    validate_compound,
    validate_library,
)


def _compound(**overrides):
    base = {
        "ligand_id": "benzamidine",
        "name": "Benzamidine",
        "smiles": "NC(=N)c1ccccc1",
        "compound_class": "aryl amidine",
        "inclusion_rationale": "serine-protease S1 pocket binder",
        "source": "PMID:12345678",
        "set": "custom_anti_virulence",
    }
    base.update(overrides)
    return base


def test_validate_compound_accepts_complete_entry():
    validate_compound(_compound())  # should not raise


def test_validate_compound_rejects_missing_provenance():
    with pytest.raises(CompoundLibraryError, match="inclusion_rationale"):
        validate_compound(_compound(inclusion_rationale=""), check_smiles=False)


def test_validate_compound_rejects_bad_source():
    with pytest.raises(CompoundLibraryError, match="source"):
        validate_compound(_compound(source="some paper"), check_smiles=False)


def test_validate_compound_rejects_invalid_set():
    with pytest.raises(CompoundLibraryError, match="set"):
        validate_compound(_compound(set="random"), check_smiles=False)


def test_validate_compound_rejects_unparseable_smiles():
    with pytest.raises(CompoundLibraryError, match="SMILES"):
        validate_compound(_compound(smiles="not-a-smiles((("))


def test_validate_library_rejects_duplicate_ids():
    with pytest.raises(CompoundLibraryError, match="Duplicate ligand_id"):
        validate_library([_compound(), _compound(name="Other")], check_smiles=False)


def test_summarize_library_counts_by_set():
    compounds = [
        _compound(ligand_id="a", name="A", set="custom_anti_virulence"),
        _compound(ligand_id="b", name="B", set="fda_comparator"),
    ]

    summary = summarize_library(compounds)

    assert summary["compound_count"] == 2
    assert summary["counts_by_set"] == {"custom_anti_virulence": 1, "fda_comparator": 1}

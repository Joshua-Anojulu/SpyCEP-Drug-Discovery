import pytest

from spycep_drug_discovery.admet import (
    AdmetError,
    admet_profile,
    compute_descriptors,
    lipinski_report,
    veber_report,
)


def test_compute_descriptors_benzamidine():
    desc = compute_descriptors("NC(=N)c1ccccc1")

    assert desc["heavy_atoms"] == 9
    assert 118 < desc["molecular_weight"] < 122  # ~120.15
    assert desc["h_bond_donors"] >= 1


def test_compute_descriptors_rejects_bad_smiles():
    with pytest.raises(AdmetError):
        compute_descriptors("not-a-smiles(((")


def test_lipinski_report_flags_large_molecule():
    small = lipinski_report(
        {"molecular_weight": 300, "logp": 2.0, "h_bond_donors": 2, "h_bond_acceptors": 4}
    )
    heavy = lipinski_report(
        {"molecular_weight": 900, "logp": 8.0, "h_bond_donors": 8, "h_bond_acceptors": 15}
    )

    assert small["passes"] is True
    assert small["violations"] == []
    assert heavy["passes"] is False
    assert set(heavy["violations"]) == {"MW>500", "logP>5", "HBD>5", "HBA>10"}


def test_veber_report():
    assert veber_report({"rotatable_bonds": 5, "tpsa": 90})["passes"] is True
    assert veber_report({"rotatable_bonds": 12, "tpsa": 90})["passes"] is False


def test_admet_profile_benzamidine_is_drug_like():
    profile = admet_profile("NC(=N)c1ccccc1")

    assert profile["lipinski"]["passes"] is True
    assert profile["veber"]["passes"] is True
    assert isinstance(profile["pains_alerts"], list)
    assert "drug_like" in profile

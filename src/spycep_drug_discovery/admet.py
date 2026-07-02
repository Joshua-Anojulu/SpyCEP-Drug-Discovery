from __future__ import annotations

from typing import Any


ADMET_VERSION = "2026-07-02"


class AdmetError(ValueError):
    """Raised when a SMILES cannot be parsed for descriptor calculation."""


def compute_descriptors(smiles: str) -> dict[str, Any]:
    from rdkit import Chem
    from rdkit.Chem import Crippen, Descriptors, Lipinski, rdMolDescriptors

    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise AdmetError(f"RDKit could not parse SMILES: {smiles!r}")
    return {
        "molecular_weight": round(Descriptors.MolWt(mol), 2),
        "logp": round(Crippen.MolLogP(mol), 2),
        "h_bond_donors": Lipinski.NumHDonors(mol),
        "h_bond_acceptors": Lipinski.NumHAcceptors(mol),
        "tpsa": round(rdMolDescriptors.CalcTPSA(mol), 2),
        "rotatable_bonds": Lipinski.NumRotatableBonds(mol),
        "heavy_atoms": mol.GetNumHeavyAtoms(),
    }


def lipinski_report(descriptors: dict[str, Any]) -> dict[str, Any]:
    violations = []
    if descriptors["molecular_weight"] > 500:
        violations.append("MW>500")
    if descriptors["logp"] > 5:
        violations.append("logP>5")
    if descriptors["h_bond_donors"] > 5:
        violations.append("HBD>5")
    if descriptors["h_bond_acceptors"] > 10:
        violations.append("HBA>10")
    return {"violations": violations, "passes": len(violations) <= 1}


def veber_report(descriptors: dict[str, Any]) -> dict[str, Any]:
    passes = descriptors["rotatable_bonds"] <= 10 and descriptors["tpsa"] <= 140
    return {"passes": passes}


def pains_alerts(smiles: str) -> list[str]:
    from rdkit import Chem
    from rdkit.Chem.FilterCatalog import FilterCatalog, FilterCatalogParams

    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise AdmetError(f"RDKit could not parse SMILES: {smiles!r}")
    params = FilterCatalogParams()
    params.AddCatalog(FilterCatalogParams.FilterCatalogs.PAINS)
    catalog = FilterCatalog(params)
    return [entry.GetDescription() for entry in catalog.GetMatches(mol)]


def admet_profile(smiles: str) -> dict[str, Any]:
    descriptors = compute_descriptors(smiles)
    lipinski = lipinski_report(descriptors)
    veber = veber_report(descriptors)
    alerts = pains_alerts(smiles)
    return {
        "admet_version": ADMET_VERSION,
        "descriptors": descriptors,
        "lipinski": lipinski,
        "veber": veber,
        "pains_alerts": alerts,
        "drug_like": lipinski["passes"] and veber["passes"] and not alerts,
    }

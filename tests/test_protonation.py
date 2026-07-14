"""Protonation states at pH 7.4, checked against literature pKa values.

These are the reference cases the rule set exists to get right. Dimorphite-DL, asked for
a single state at pH 7.4, returned metformin as a +3 trication, allopurinol as a -2
dianion, and acetaminophen deprotonated at a phenol whose pKa is 9.5. Every one of those
is a case below.
"""
import pytest
from rdkit import Chem

from spycep_drug_discovery.protonation import PROTONATION_PH, protonate


def _charge(smiles: str) -> int:
    return Chem.GetFormalCharge(Chem.MolFromSmiles(protonate(smiles)))


def test_protonation_ph_is_physiological():
    assert PROTONATION_PH == 7.4


@pytest.mark.parametrize(
    "name,smiles,expected",
    [
        # Strong bases: cations at pH 7.4. The S1 salt bridge is the binding rationale
        # for the whole custom set, so these carry the study.
        ("benzamidine", "NC(=N)c1ccccc1", +1),
        ("4-aminobenzamidine", "NC(=N)c1ccc(N)cc1", +1),
        ("pentamidine", "NC(=N)c1ccc(OCCCCCOc2ccc(C(N)=N)cc2)cc1", +2),
        ("propranolol", "CC(C)NCC(O)COc1cccc2ccccc12", +1),
        # A biguanide takes one charge, not one per amidine match: the second
        # protonation has pKa 2.8.
        ("metformin", "CN(C)C(=N)N=C(N)N", +1),
        # Strong acids: anions at pH 7.4.
        ("aspirin", "CC(=O)Oc1ccccc1C(=O)O", -1),
        ("ibuprofen", "CC(C)Cc1ccc(cc1)C(C)C(=O)O", -1),
        # Warfarin's acid is a 4-hydroxycoumarin enol (pKa 5.1), which RDKit
        # aromatises, so an aliphatic enol pattern never sees it.
        ("warfarin", "CC(=O)CC(c1ccccc1)C1=C(O)c2ccccc2OC1=O", -1),
        # Left neutral: pKa too far from 7.4 in the other direction.
        ("acetaminophen", "CC(=O)Nc1ccc(O)cc1", 0),  # phenol, pKa 9.5
        ("allopurinol", "C1=NNC2=C1C(=O)N=CN2", 0),  # pKa 9.4
        ("caffeine", "Cn1cnc2n(C)c(=O)n(C)c(=O)c12", 0),
        # Zwitterions net out.
        ("gabapentin", "OC(=O)CC1(CN)CCCCC1", 0),
        ("4-guanidinobenzoic acid", "NC(=N)Nc1ccc(cc1)C(=O)O", 0),
    ],
)
def test_dominant_microspecies_matches_literature(name, smiles, expected):
    assert _charge(smiles) == expected, name


def test_enamine_nitrogen_is_not_treated_as_a_basic_amine():
    # Amlodipine's dihydropyridine N-H is conjugated into the ring and carries no
    # basicity. Charging it as well as the primary amine gives a spurious dication.
    amlodipine = "CCOC(=O)C1=C(COCCN)NC(C)=C(C(=O)OC)C1c1ccccc1Cl"

    assert _charge(amlodipine) == +1


def test_protonation_is_idempotent():
    once = protonate("NC(=N)c1ccccc1")

    assert protonate(once) == once

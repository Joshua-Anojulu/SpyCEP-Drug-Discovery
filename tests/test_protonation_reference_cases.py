import json
from pathlib import Path

from spycep_drug_discovery.protonation import protonate
from spycep_drug_discovery.species import (
    atom_charge_inventory,
    atom_mapped_canonical_smiles,
)


REFERENCE_PATH = Path("docs/methods/protonation_reference_cases.json")

VALID_TIERS = {
    "COMPOUND_SPECIFIC_EXPERIMENTAL",
    "CURATED_EXPERIMENTAL_COMPILATION",
    "SECONDARY_REVIEW",
    "NO_SOURCE_FOUND",
}


def _cases():
    return json.loads(REFERENCE_PATH.read_text(encoding="utf-8"))["cases"]


def test_at_least_24_reference_compounds_have_exact_mapped_species():
    cases = _cases()
    assert len(cases) >= 24
    for case in cases:
        observed = atom_mapped_canonical_smiles(protonate(case["smiles"]))
        assert observed == case["expected"], case["name"]
        # Compare the complete atom inventory, not only a net charge: a molecule can carry
        # the right TOTAL charge with the charge on the wrong atom.
        assert atom_charge_inventory(observed) == atom_charge_inventory(case["expected"])


def test_pka_evidence_is_real_and_pubchem_is_never_counted_as_a_pka_source():
    """A PubChem link proves STRUCTURE, not solution ionisation.

    The earlier version of this suite asserted only that a `citation` field started with
    "https://" — which a PubChem compound URL satisfies. That is how 24 structure links
    came to stand in for pKa evidence while the README claimed the rules were "validated
    against literature charges". This test exists so that cannot recur.
    """
    for case in _cases():
        tier = case["evidence_tier"]
        assert tier in VALID_TIERS, case["name"]

        url = case.get("pka_source_url")
        if tier == "NO_SOURCE_FOUND":
            # An honest absence: no value may be asserted, and the reason must be recorded.
            assert case["pka_value"] is None, case["name"]
            assert url is None, case["name"]
            assert case.get("caveat"), case["name"]
            continue

        assert url and url.startswith("http"), case["name"]
        assert "pubchem" not in url.lower(), (
            f"{case['name']}: PubChem is a STRUCTURE source, not a pKa source"
        )
        assert case["pka_value"], case["name"]
        assert case["pka_source_citation"], case["name"]
        # A quote proves the number was read off the cited page rather than recalled.
        assert case["verified_quote"], case["name"]


def test_the_two_unverifiable_compounds_are_declared_not_guessed():
    """Fosfomycin and pentamidine have no verifiable experimental pKa.

    The values that circulate for both are software predictions (Chemicalize; DrugBank)
    that have been laundered into prose as though measured. Recording them as
    NO_SOURCE_FOUND is the honest outcome; substituting the predicted number is not.
    """
    by_name = {c["name"]: c for c in _cases()}
    for name in ("fosfomycin", "pentamidine"):
        assert by_name[name]["evidence_tier"] == "NO_SOURCE_FOUND", name
        assert by_name[name]["pka_value"] is None, name


def test_reference_set_covers_every_declared_rule_family_and_audited_exception():
    names = {case["name"] for case in _cases()}
    assert {
        "benzoic_acid",
        "methanesulfonic_acid",
        "fosfomycin",
        "tetrazole",
        "warfarin",
        "doxycycline",
        "benzamidine",
        "guanidine",
        "metformin",
        "pentamidine",
        "propranolol",
        "azithromycin",
        "acetaminophen",
        "imidazole",
        "cysteamine",
        "aniline",
        "benzenesulfonamide",
        "phenylboronic_acid",
        "sildenafil",
        "lisinopril",
        "losartan",
    }.issubset(names)

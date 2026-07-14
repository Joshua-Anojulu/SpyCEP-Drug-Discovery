"""Build the frozen Stage 1 species and workflow-eligibility artifacts.

This script prepares no 3-D ligands and runs no docking.
"""
from __future__ import annotations

import json
import os
import sys
from collections import Counter
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from rdkit import Chem

from spycep_drug_discovery.attempt_manifest import build_attempt_manifest
from spycep_drug_discovery.protonation import protonate
from spycep_drug_discovery.species import (
    CATALOG_SCHEMA_VERSION,
    make_state_row,
    sha256_file,
    validate_species_catalog,
)


LIBRARY = PROJECT_ROOT / "docs" / "methods" / "compound_library_source.json"
SPECIES_PATH = PROJECT_ROOT / "docs" / "methods" / "species_audit.json"
ATTEMPT_PATH = PROJECT_ROOT / "docs" / "methods" / "attempt_manifest.json"
CONVERSION = PROJECT_ROOT / "docs" / "methods" / "pdbqt_conversion.json"
TIGHT_POCKETS = PROJECT_ROOT / "docs" / "methods" / "tight_pocket_definition.json"
SPEB_RESULT = PROJECT_ROOT / "docs" / "methods" / "speb_positive_control_result.json"

BORON_PARENTS = {
    "phenylboronic_acid",
    "4_carboxyphenylboronic_acid",
    "bortezomib",
    "ixazomib",
}
NO_IONISABLE_LIBRARY = {
    "pmsf",
    "dci",
    "linezolid",
    "simvastatin",
    "prednisone",
    "dexamethasone",
    "caffeine",
    "colchicine",
}
Q9D = {
    "entity_id": "Q9D_speb_inhibitor",
    "source_smiles": "CC(=O)[C@H](Cc1cccc(c1)[N+]([O-])=O)NC(=O)OCc2ccccc2",
    "citation": "https://www.rcsb.org/ligand/Q9D",
}

# These are explicit hypotheses, not generated alternatives.  The neutral-alpha-amine
# states equal the generic rule output; the ammonium states are consumed verbatim.
AMBIGUOUS_STATES = {
    # Lisinopril's secondary amine sits at logK2 = 7.13 — within 0.3 units of 7.4.
    # The source's own speciation table AT PLASMA pH gives HLis- 65.04% and the neutral
    # double-zwitterion H2Lis 34.93%. A 35% minor species is far too large to discard by
    # asserting a single state, so both are docked. (The neutral-secondary-amine state is
    # exactly what the generic rule emits; the protonated one is the verbatim hypothesis.)
    "lisinopril": {
        "states": {
            "secondary_amine_neutral": (
                "[NH3+]CCCC[C@H](N[C@@H](CCc1ccccc1)C(=O)[O-])"
                "C(=O)N1CCC[C@H]1C(=O)[O-]"
            ),
            "secondary_amine_protonated": (
                "[NH3+]CCCC[C@H]([NH2+][C@@H](CCc1ccccc1)C(=O)[O-])"
                "C(=O)N1CCC[C@H]1C(=O)[O-]"
            ),
        },
        "citations": [
            "https://real.mtak.hu/29146/1/2013_Takacs_Novak__Deak_Beni_Physico_chemical_profiling_ADMET_and_DMPK_u.pdf",
        ],
        "rationale": (
            "Potentiometry + 1H NMR-pH titration (25.0 C, I = 0.15 M) assigns logK2 = 7.13 to "
            "the secondary amine, within 0.3 units of 7.4. The source's own speciation table at "
            "plasma pH reports HLis- at 65.04% and the neutral double-zwitterion H2Lis at 34.93%. "
            "Neither site-resolved form is safely dominant, so both are docked and no abundance "
            "claim is made."
        ),
    },
    "ampicillin": {
        "states": {
            "alpha_amine_neutral": (
                "CC1(C)S[C@@H]2[C@H](NC(=O)[C@H](N)c3ccccc3)"
                "C(=O)N2[C@H]1C(=O)[O-]"
            ),
            "alpha_ammonium": (
                "CC1(C)S[C@@H]2[C@H](NC(=O)[C@H]([NH3+])c3ccccc3)"
                "C(=O)N2[C@H]1C(=O)[O-]"
            ),
        },
        "citations": [
            "https://pmc.ncbi.nlm.nih.gov/articles/PMC12347571/",
        ],
        "rationale": (
            "Experimental acid-base profiling assigns the near-physiological pKa to "
            "the phenylglycyl alpha-amino site. At pH 7.4 the evidence does not justify "
            "choosing its neutral or ammonium form as a single site-resolved state."
        ),
    },
    "amoxicillin": {
        "states": {
            "alpha_amine_neutral": (
                "CC1(C)S[C@@H]2[C@H](NC(=O)[C@H](N)c3ccc(O)cc3)"
                "C(=O)N2[C@H]1C(=O)[O-]"
            ),
            "alpha_ammonium": (
                "CC1(C)S[C@@H]2[C@H](NC(=O)[C@H]([NH3+])c3ccc(O)cc3)"
                "C(=O)N2[C@H]1C(=O)[O-]"
            ),
        },
        "citations": [
            "https://sioc-journal.cn/Jwk_hxxb/EN/Y1989/V47/I5/484",
        ],
        "rationale": (
            "Published microscopic ionisation analysis assigns a near-physiological "
            "equilibrium to the alpha-amino site and does not establish one of the two "
            "site-resolved forms as safely dominant at pH 7.4."
        ),
    },
    "cephalexin": {
        "states": {
            "alpha_amine_neutral": (
                "CC1=C(C(=O)[O-])N2C(=O)[C@@H](NC(=O)[C@H](N)c3ccccc3)[C@H]2SC1"
            ),
            "alpha_ammonium": (
                "CC1=C(C(=O)[O-])N2C(=O)[C@@H](NC(=O)[C@H]([NH3+])c3ccccc3)"
                "[C@H]2SC1"
            ),
        },
        "citations": [
            "https://pubs.rsc.org/en/content/articlehtml/2017/ra/c7ra09461b",
        ],
        "rationale": (
            "The reported amino-site pKa is close enough to physiological pH that the "
            "generic 9-11 amine rule is outside its domain; both neutral and ammonium "
            "alpha-amino hypotheses are retained without abundance claims."
        ),
    },
}


def _desalted_rule_output(smiles: str) -> str:
    mol = Chem.MolFromSmiles(smiles)
    fragments = Chem.GetMolFrags(mol, asMols=True, sanitizeFrags=True)
    largest = max(fragments, key=lambda value: value.GetNumHeavyAtoms())
    return protonate(Chem.MolToSmiles(largest))


def _boron_to_carbon(smiles: str) -> str:
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise RuntimeError(f"Could not parse boronic-acid parent: {smiles!r}")
    rw = Chem.RWMol(mol)
    replacements = 0
    for atom in rw.GetAtoms():
        if atom.GetAtomicNum() == 5:
            atom.SetAtomicNum(6)
            replacements += 1
    if replacements != 1:
        raise RuntimeError(f"Expected exactly one boron atom, found {replacements}: {smiles!r}")
    surrogate = rw.GetMol()
    Chem.SanitizeMol(surrogate)
    return Chem.MolToSmiles(surrogate, canonical=True, isomericSmiles=True)


def _pubchem_provenance(compound: dict[str, Any]) -> dict[str, Any]:
    return {
        "kind": "pubchem_cid",
        "pubchem_cid": int(compound["pubchem_cid"]),
        "source_url": compound["source"],
    }


def _single_evidence(entity_id: str, tier: str) -> dict[str, Any]:
    if tier == "NO_IONISABLE_SITE":
        return {
            "basis": (
                "Manual functional-group review found no site ionised by the frozen "
                "pH 7.4 rule set; the single frozen state is rule-output matched."
            )
        }
    return {
        "basis": (
            "Tracked source structure with site-specific formal charges regenerated "
            "and matched under the frozen, literature-domain pH 7.4 rules."
        ),
        "rule_exception": entity_id in {"losartan", "doxycycline", "sildenafil", "lisinopril"},
    }


def build_species_catalog() -> dict[str, Any]:
    library = json.loads(LIBRARY.read_text(encoding="utf-8"))["compounds"]
    states: list[dict[str, Any]] = []
    source_to_surrogate: dict[str, str] = {}

    for compound in library:
        entity_id = compound["ligand_id"]
        provenance = _pubchem_provenance(compound)
        if entity_id in AMBIGUOUS_STATES:
            decision = AMBIGUOUS_STATES[entity_id]
            review = {
                "reviewer": "Codex implementation review; adjudication preregistered in approved PLAN.md",
                "citations": decision["citations"],
                "classification_rationale": decision["rationale"],
                "review_date": "2026-07-13",
                "more_than_two_plausible_states_considered": {
                    "answer": False,
                    "rationale": (
                        "The contested alpha-amino proton yields exactly the two listed "
                        "states; the carboxylate assignment is common to both and review "
                        "identified no third site-resolved state requiring inclusion."
                    ),
                },
            }
            for state_id, state_smiles in decision["states"].items():
                states.append(
                    make_state_row(
                        entity_id=entity_id,
                        state_id=state_id,
                        source_smiles=compound["smiles"],
                        state_smiles=state_smiles,
                        tier="AMBIGUOUS",
                        dock_eligible=True,
                        exclusion_reason=None,
                        producing_rule="explicit_hand_reviewed_beta_lactam_alpha_amino_hypothesis",
                        provenance=provenance,
                        classification_evidence={
                            "basis": decision["rationale"],
                            "citations": decision["citations"],
                        },
                        entity_kind="library_parent",
                        set_name=compound["set"],
                        review=review,
                    )
                )
            continue

        tier = (
            "NO_IONISABLE_SITE"
            if entity_id in NO_IONISABLE_LIBRARY
            else "UNAMBIGUOUS"
        )
        eligible = entity_id not in BORON_PARENTS
        surrogate_id = f"{entity_id}_gemdiol" if not eligible else None
        if surrogate_id:
            source_to_surrogate[entity_id] = surrogate_id
        states.append(
            make_state_row(
                entity_id=entity_id,
                state_id="state_01",
                source_smiles=compound["smiles"],
                state_smiles=_desalted_rule_output(compound["smiles"]),
                tier=tier,
                dock_eligible=eligible,
                exclusion_reason=(
                    None
                    if eligible
                    else (
                        "Boronic-acid parent lacks MMFF94s parameters and is never "
                        "directly docked; see the separately routed gem-diol surrogate."
                    )
                ),
                producing_rule="frozen_generic_protonation_rule_at_ph_7_4",
                provenance=provenance,
                classification_evidence=_single_evidence(entity_id, tier),
                entity_kind="library_parent",
                set_name=compound["set"],
                surrogate_entity_id=surrogate_id,
            )
        )

    states.append(
        make_state_row(
            entity_id=Q9D["entity_id"],
            state_id="state_01",
            source_smiles=Q9D["source_smiles"],
            state_smiles=_desalted_rule_output(Q9D["source_smiles"]),
            tier="NO_IONISABLE_SITE",
            dock_eligible=True,
            exclusion_reason=None,
            producing_rule="frozen_generic_protonation_rule_at_ph_7_4",
            provenance={"kind": "citation", "citations": [Q9D["citation"]]},
            classification_evidence={
                "basis": (
                    "RCSB ligand structure contains no site ionised by the frozen "
                    "pH 7.4 rule set; the state is rule-output matched."
                )
            },
            entity_kind="speb_positive_control",
            set_name="positive_control",
        )
    )

    library_by_id = {row["ligand_id"]: row for row in library}
    for parent_id, surrogate_id in sorted(source_to_surrogate.items()):
        parent = library_by_id[parent_id]
        surrogate_smiles = _boron_to_carbon(parent["smiles"])
        tier = (
            "UNAMBIGUOUS"
            if parent_id == "4_carboxyphenylboronic_acid"
            else "NO_IONISABLE_SITE"
        )
        states.append(
            make_state_row(
                entity_id=surrogate_id,
                state_id="state_01",
                source_smiles=surrogate_smiles,
                state_smiles=_desalted_rule_output(surrogate_smiles),
                tier=tier,
                dock_eligible=True,
                exclusion_reason=None,
                producing_rule=(
                    "parent_boron_to_carbon_then_frozen_generic_protonation_rule_at_ph_7_4"
                ),
                provenance={
                    "kind": "parent_transformation",
                    "parent_entity_id": parent_id,
                    "parent_pubchem_cid": int(parent["pubchem_cid"]),
                    "transformation": "R-B(OH)2 -> R-CH(OH)2 (boron atom replaced by carbon)",
                },
                classification_evidence=_single_evidence(surrogate_id, tier),
                entity_kind="gem_diol_surrogate",
                set_name="boron_surrogate",
                source_parent_entity_id=parent_id,
            )
        )

    states.sort(key=lambda row: (row["entity_id"], row["state_id"]))
    catalog = {
        "schema_version": CATALOG_SCHEMA_VERSION,
        "method_status": "authoritative_preregistered_species_hypotheses_no_abundance_fractions",
        "ph": 7.4,
        "hard_state_cap_per_entity": 2,
        "entity_count": len({row["entity_id"] for row in states}),
        "state_count": len(states),
        "tier_counts_by_entity": dict(
            sorted(
                Counter(
                    next(row["tier"] for row in states if row["entity_id"] == entity_id)
                    for entity_id in {row["entity_id"] for row in states}
                ).items()
            )
        ),
        "source_library": "docs/methods/compound_library_source.json",
        "source_to_surrogate": dict(sorted(source_to_surrogate.items())),
        "states": states,
    }
    validate_species_catalog(
        catalog,
        library_entity_ids=(row["ligand_id"] for row in library),
    )
    return catalog


def _wide_receptors() -> list[dict[str, Any]]:
    conversion = json.loads(CONVERSION.read_text(encoding="utf-8"))
    return [
        {
            "pocket_id": row["pocket_id"],
            "pdb_id": row["pdb_id"],
            "receptor_pdbqt_path": row["output_paths"]["pdbqt"],
            "box_center_angstrom": row["box_center_angstrom"],
            "box_size_angstrom": row["box_size_angstrom"],
        }
        for row in conversion["receptors"]
    ]


def _tight_receptors() -> list[dict[str, Any]]:
    pockets = json.loads(TIGHT_POCKETS.read_text(encoding="utf-8"))["pockets"]
    return [
        {
            "pocket_id": row["pocket_id"],
            "pdb_id": row["pdb_id"],
            "receptor_pdbqt_path": row["receptor_pdbqt_path"],
            "box_center_angstrom": row["box_center_angstrom"],
            "box_size_angstrom": row["box_size_angstrom"],
        }
        for row in pockets
    ]


def _speb_receptor() -> dict[str, Any]:
    result = json.loads(SPEB_RESULT.read_text(encoding="utf-8"))
    return {
        "pocket_id": "speb_6ukd_active_site",
        "pdb_id": "6UKD",
        "receptor_pdbqt_path": "data/processed/pdbqt/speb_6ukd_active_site.pdbqt",
        "box_center_angstrom": result["box_center_angstrom"],
        "box_size_angstrom": result["box_size_angstrom"],
    }


def _atomic_json(path: Path, value: MappingLike) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


MappingLike = dict[str, Any]


def main() -> None:
    catalog = build_species_catalog()
    _atomic_json(SPECIES_PATH, catalog)
    species_hash = sha256_file(SPECIES_PATH)
    attempts = build_attempt_manifest(
        catalog,
        species_catalog_sha256=species_hash,
        wide_receptors=_wide_receptors(),
        tight_receptors=_tight_receptors(),
        speb_receptor=_speb_receptor(),
    )
    _atomic_json(ATTEMPT_PATH, attempts)
    print(
        f"Wrote {SPECIES_PATH.relative_to(PROJECT_ROOT)}: "
        f"{catalog['entity_count']} entities, {catalog['state_count']} states"
    )
    print(
        f"Wrote {ATTEMPT_PATH.relative_to(PROJECT_ROOT)}: "
        f"{attempts['attempt_count']} legal invocations"
    )


if __name__ == "__main__":
    main()

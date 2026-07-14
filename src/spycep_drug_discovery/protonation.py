"""Assign ligand protonation states at physiological pH.

Why this is hand-rolled rather than delegated to Dimorphite-DL: Dimorphite enumerates
*plausible* microspecies, it does not pick the dominant one. Asking it for a single
state at pH 7.4 returns the most ionised form, which is wrong for a lot of this library
(metformin came back as a +3 trication, allopurinol as a -2 dianion, acetaminophen
deprotonated at a phenol whose pKa is 9.5). Docking those would be worse than docking
everything neutral.

So the rules are explicit, few, and auditable. A group is charged only when its pKa sits
far enough from 7.4 that the dominant species is unambiguous:

  deprotonated (pKa well below 7.4)
    carboxylic acid              3-5
    sulfonic acid                <1
    phosphonic / phosphate O-H   ~2
    tetrazole                    ~4.9
    vinylogous acid (4-hydroxycoumarin, e.g. warfarin)  ~5.1

  protonated (pKa well above 7.4)
    amidine / guanidine / biguanide   11-13.6, one charge per conjugated system
    aliphatic amine                   9-11

Everything else stays neutral. That includes phenols (9.5-10), imidazole (~7, so only a
quarter protonated and left neutral), thiols (~8.3), anilines (weak bases, ~4.6),
amides, sulfonamides, and each explicitly guarded amine site whose measured pKa is too
close to (or below) 7.4 for the generic 9-11 amine rule to apply. The guard is
per-site: it does not collapse a molecule to one protonated amine, which would turn
azithromycin's two independently basic amines into a spurious monocation.

Each choice is recorded in `PROTONATION_RULES` so a reader can check the call rather
than trust it. The rules deliberately emit the neutral form at an undecided site;
hand-reviewed alternative states belong in the authoritative species catalog, never
in this generic rule.
"""
from __future__ import annotations

from typing import Any


PROTONATION_PH = 7.4

PROTONATION_RULES = {
    "ph": PROTONATION_PH,
    "deprotonated": [
        {"group": "carboxylic acid", "pka": "3-5"},
        {"group": "sulfonic acid", "pka": "<1"},
        {"group": "phosphonic/phosphate O-H", "pka": "~2"},
        {"group": "tetrazole", "pka": "~4.9"},
        {"group": "tetracycline acidic tricarbonyl/enol", "pka": "~3.0"},
        {"group": "vinylogous acid (4-hydroxycoumarin)", "pka": "~5.1"},
    ],
    "protonated": [
        {"group": "amidine/guanidine/biguanide", "pka": "11-13.6",
         "note": "one charge per conjugated system; the second protonation has pKa < 3"},
        {"group": "aliphatic amine", "pka": "9-11"},
    ],
    "left_neutral": [
        {"group": "phenol", "pka": "9.5-10"},
        {"group": "imidazole", "pka": "~7.0", "note": "~25% protonated at pH 7.4; rounded to neutral"},
        {"group": "thiol", "pka": "~8.3"},
        {"group": "aniline", "pka": "~4.6", "note": "weak base; free base dominates"},
        {"group": "amide, sulfonamide, alcohol", "pka": "not ionised near 7.4"},
        {
            "group": "beta-lactam alpha-amino site",
            "pka": "~6.8-7.3",
            "note": "site is undecided near pH 7.4; generic rule emits neutral",
        },
        {
            "group": "sildenafil distal piperazine nitrogen",
            "pka": "~6.5",
            "note": "neutral base is dominant at pH 7.4",
        },
        {
            "group": "lisinopril lower-basicity secondary amine",
            "pka": "below physiological pH",
            "note": "site remains neutral while the terminal primary amine is protonated",
        },
    ],
}

# Acids: the acidic hydrogen sits on the atom matched last in each pattern.
_ACID_SMARTS = (
    "[CX3](=O)[OX2H1]",            # carboxylic acid
    "[SX4](=O)(=O)[OX2H1]",        # sulfonic acid
    "[PX4](=O)[OX2H1]",            # phosphonic / phosphate
    # Doxycycline's A-ring tricarbonyl/enol. This identifies the hydroxy atom in
    # O=C-C(C(=O)N)=C(O), rather than deprotonating one of its phenols/alcohols.
    "[CX3](=[OX1])[CX3]([CX3](=[OX1])[NX3])=[CX3]([OX2H1])",
    # 4-hydroxycoumarin (warfarin). RDKit aromatises this ring, so an aliphatic
    # enol pattern never sees it.
    "[OX2H1]c1c2ccccc2oc(=O)c1",
)

# Amidine / guanidine: the basic imine nitrogen is the sp2 =N.
_AMIDINE_SMARTS = "[NX3;!$([NX3][CX3]=[OX1])][CX3]=[NX2;!$([NX2][#7,#8])]"

# Aliphatic amine: sp3 nitrogen that is not an amide, sulfonamide, aniline, enamine,
# nitro, nitrile, or part of an amidine/guanidine. The enamine exclusion matters for
# amlodipine, whose dihydropyridine N-H is conjugated into the ring and carries no
# basicity; without it the molecule comes out as a dication.
_AMINE_SMARTS = (
    "[NX3;H2,H1,H0;!$([NX3][CX3]=[OX1]);!$([NX3][SX4](=O)=O);!$([NX3]a);"
    "!$([NX3][CX3]=[#7]);!$([NX3][CX3]=[CX3]);!$([NX3]=*);!$([NX3][#7]);"
    "!$([N+]);!$([NX3]C#N)]"
)

# Per-site exclusions from the generic aliphatic-amine pKa 9-11 domain. Match atom
# zero is the site that must remain neutral. These are structural site guards, not a
# "most basic amine" molecule-level heuristic.
_UNDECIDED_AMINE_SITE_SMARTS = (
    # Ampicillin, amoxicillin and cephalexin: the phenylglycyl alpha-amino site.
    "[NX3;H2][C;H1]([c])[CX3](=O)[NX3]",
    # Sildenafil: the piperazine nitrogen opposite the sulfonamide nitrogen.
    "[NX3;H0]1CC[NX3;H0]([SX4](=O)=O)CC1",
    # Lisinopril: lower-basicity secondary amine between its two amino-acid units.
    (
        "[NX3;H1]([C;H1](CCc1ccccc1)C(=O)[OX2H1])"
        "[C;H1](CCCC[NX3;H2])C(=O)[NX3]1CCC[C;H1]1C(=O)[OX2H1]"
    ),
)


def _tetrazole_acidic_atoms(mol) -> set[int]:
    """Return the mobile-H nitrogen of every neutral tetrazole tautomer.

    A literal SMARTS such as ``c1nnn[nH]1`` encodes one traversal/tautomer and misses
    losartan's ``c1nn[nH]n1`` depiction. Ring topology (five members, four nitrogens)
    is invariant to that mobile-H placement, so the actual N-H atom can be charged
    without normalising or enumerating tautomers.
    """
    hits: set[int] = set()
    for ring in mol.GetRingInfo().AtomRings():
        if len(ring) != 5:
            continue
        nitrogens = [index for index in ring if mol.GetAtomWithIdx(index).GetAtomicNum() == 7]
        if len(nitrogens) != 4:
            continue
        hits.update(index for index in nitrogens if mol.GetAtomWithIdx(index).GetTotalNumHs() > 0)
    return hits


def _acidic_hydrogen_atoms(mol) -> set[int]:
    from rdkit import Chem

    hits: set[int] = set()
    for smarts in _ACID_SMARTS:
        pattern = Chem.MolFromSmarts(smarts)
        for match in mol.GetSubstructMatches(pattern):
            for index in match:
                atom = mol.GetAtomWithIdx(index)
                if atom.GetSymbol() == "O" and atom.GetTotalNumHs() > 0:
                    hits.add(index)
    hits.update(_tetrazole_acidic_atoms(mol))
    return hits


def _basic_amidine_systems(mol) -> list[int]:
    """One basic nitrogen per conjugated amidine/guanidine/biguanide system.

    Biguanides (metformin) match the amidine pattern twice over shared atoms. They take
    a single charge at pH 7.4, so overlapping matches are merged and charged once.
    """
    from rdkit import Chem

    pattern = Chem.MolFromSmarts(_AMIDINE_SMARTS)
    matches = list(mol.GetSubstructMatches(pattern))
    if not matches:
        return []

    def _linked(a: set[int], b: set[int]) -> bool:
        # Merge on a shared atom OR a direct bond. A biguanide's two amidine matches are
        # disjoint but bonded (metformin), and the system takes one charge, not two.
        if a & b:
            return True
        return any(
            mol.GetBondBetweenAtoms(i, j) is not None
            for i in a
            for j in b
        )

    systems: list[set[int]] = []
    for match in matches:
        atoms = set(match)
        merged = [s for s in systems if _linked(s, atoms)]
        for s in merged:
            systems.remove(s)
            atoms |= s
        systems.append(atoms)

    basic: list[int] = []
    for system in systems:
        # Charge the sp2 imine nitrogen of the system.
        candidates = [
            i for i in sorted(system)
            if mol.GetAtomWithIdx(i).GetSymbol() == "N"
            and mol.GetAtomWithIdx(i).GetTotalNumHs() < 3
            and any(b.GetBondTypeAsDouble() == 2.0 for b in mol.GetAtomWithIdx(i).GetBonds())
        ]
        if candidates:
            basic.append(candidates[0])
    return basic


def _basic_amine_atoms(mol) -> list[int]:
    from rdkit import Chem

    pattern = Chem.MolFromSmarts(_AMINE_SMARTS)
    return [match[0] for match in mol.GetSubstructMatches(pattern)]


def _guarded_amine_atoms(mol) -> set[int]:
    """Amine sites outside the generic aliphatic-amine pKa domain."""
    from rdkit import Chem

    guarded: set[int] = set()
    for smarts in _UNDECIDED_AMINE_SITE_SMARTS:
        pattern = Chem.MolFromSmarts(smarts)
        guarded.update(match[0] for match in mol.GetSubstructMatches(pattern))
    return guarded


def protonate(smiles: str) -> str:
    """Return the dominant microspecies at pH 7.4 as canonical SMILES."""
    from rdkit import Chem

    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise ValueError(f"RDKit could not parse SMILES: {smiles!r}")

    rw = Chem.RWMol(mol)
    # Never touch an atom that already carries a charge: the input may already be an
    # ionised depiction, and re-applying the rules would stack a second charge onto it.
    already_charged = {a.GetIdx() for a in mol.GetAtoms() if a.GetFormalCharge() != 0}

    acidic = _acidic_hydrogen_atoms(mol) - already_charged
    amidines = set(_basic_amidine_systems(mol)) - already_charged
    amines = (
        set(_basic_amine_atoms(mol))
        - amidines
        - already_charged
        - _guarded_amine_atoms(mol)
    )

    for index in acidic:
        atom = rw.GetAtomWithIdx(index)
        atom.SetFormalCharge(-1)
        atom.SetNumExplicitHs(max(0, atom.GetTotalNumHs() - 1))
        atom.SetNoImplicit(True)

    for index in amidines | amines:
        atom = rw.GetAtomWithIdx(index)
        atom.SetFormalCharge(1)
        atom.SetNumExplicitHs(atom.GetTotalNumHs() + 1)
        atom.SetNoImplicit(True)

    out = rw.GetMol()
    Chem.SanitizeMol(out)
    return Chem.MolToSmiles(out)


def protonation_report(smiles: str) -> dict[str, Any]:
    from rdkit import Chem

    species = protonate(smiles)
    mol = Chem.MolFromSmiles(species)
    return {
        "input_smiles": smiles,
        "protonated_smiles": species,
        "formal_charge": Chem.GetFormalCharge(mol),
        "ph": PROTONATION_PH,
    }

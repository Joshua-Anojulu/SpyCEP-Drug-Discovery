# Docking Methods And Results Note

Generated from tracked manifests by `scripts/write_docking_methods.py`.
Computational prioritization only; not evidence of binding or efficacy.

## Pipeline

SMILES (PubChem) -> desalt -> assign pH 7.4 species from the preregistered pKa rule set -> RDKit ETKDGv3 3D -> MMFF94 -> Meeko `mk_prepare_ligand` -> AutoDock Vina v1.2.7 (exhaustiveness 8, 9 modes, seed 42, timeout 1800 s) over the 5XYA + 7EDD ensemble -> ligand-efficiency ranking -> per-residue catalytic-triad interaction analysis.

The design library contains 77 compounds: 22 custom chemotypes and 55 FDA comparators. Four FDA comparators (amoxicillin, ampicillin, cephalexin and lisinopril) have no established dominant state at pH 7.4, so both plausible states were docked and those entities are excluded from primary set-level statistics.

43 of 77 prepared species carry a formal charge. The custom set is dominated by amidines and guanidines, which are cations at physiological pH; the S1 salt bridge is their binding rationale.

Two SpyCEP search boxes were used: 22 A receptor-preparation boxes, and a tight box based on centroid and extent of the D151/H279/S617 side-chain atoms (ASP CG/OD1/OD2, HIS CG/ND1/CD2/CE1/NE2, SER CB/OG) read from the cleaned receptor PDB, + 8 A padding, clamped to [16,20] A.

## Full-library result (wide box)

- Attempted population: 73 entities; valid-fit population: 72 entities; numeric analysis population: 68 entities (18 custom, 50 FDA).
- Non-fits excluded from numeric means/tests: vancomycin.
- Custom vs FDA mean best affinity: -5.83 vs -6.10 kcal/mol; CI [-0.23, 0.77]; Mann-Whitney p = 0.307.
- Custom vs FDA mean ligand efficiency: -0.300 vs -0.269; CI [-0.09, 0.02]; Mann-Whitney p = 0.661.

Top 10 by ligand efficiency in the primary numeric population:

| Rank | Ligand | Set | Charge | Ligand efficiency | Best (kcal/mol) |
| --- | --- | --- | --- | --- | --- |
| 1 | benzamidine | custom | +1 | -0.539 | -4.85 |
| 2 | metformin | FDA | +1 | -0.492 | -4.43 |
| 3 | allopurinol | FDA | +0 | -0.482 | -4.82 |
| 4 | acetaminophen | FDA | +0 | -0.475 | -5.22 |
| 5 | 4_aminobenzamidine | custom | +1 | -0.471 | -4.71 |
| 6 | pmsf | custom | +0 | -0.417 | -4.58 |
| 7 | 4_guanidinobenzoic_acid | custom | +0 | -0.410 | -5.33 |
| 8 | dci | custom | +0 | -0.396 | -5.14 |
| 9 | gabapentin | FDA | +0 | -0.378 | -4.54 |
| 10 | aebsf | custom | +1 | -0.377 | -4.91 |

## Tight triad-centred box (robustness check)

- Attempted population: 73 entities; valid-fit population: 72 entities; numeric analysis population: 68 entities (18 custom, 50 FDA).
- Custom vs FDA mean best affinity: -5.59 vs -5.87 kcal/mol; CI [-0.15, 0.72]; Mann-Whitney p = 0.263.
- Custom vs FDA mean ligand efficiency: -0.289 vs -0.262; CI [-0.08, 0.03]; Mann-Whitney p = 0.555.

## Catalytic-triad engagement

Counted per entity over the affinity-best receptor. Vancomycin is retained as a zero-contact non-fit in the 69-entity analysis-eligible denominator.

| Box | >=1 triad residue | >=2 residues | all 3 residues |
| --- | --- | --- | --- |
| Wide | 62/69 | 51/69 | 31/69 |
| Tight | 68/69 | 56/69 | 31/69 |

## SpeB positive control

- Box: Cys192/His340 side-chain atoms only.
- Design panel: 17 decoy entities size-matched to Q9D plus two protease comparators outside the rank denominator (gabexate, nafamostat).
- Primary population: 14 single-state decoys; excluded ambiguous decoys: amoxicillin, ampicillin, cephalexin.
- By best affinity: Q9D -6.806 kcal/mol, best decoy -6.899; rank 2/15; margin -0.093.
- By ligand efficiency: Q9D -0.272, best decoy -0.285; rank 4/15; margin -0.013.
- Collapsed sensitivity: 17 decoys, Q9D rank 4/18 by affinity and 7/18 by ligand efficiency; affinity margin -0.231.
- Passes on both primary metrics: False.

## Ambiguous-state and non-fit sensitivities

- The full valid-fit FDA sensitivity enumerates 16 one-state-per-ambiguous-entity assignments over 54 FDA comparators. Affinity p-value ranges are 0.224-0.255 wide and 0.178-0.196 tight.
- Ligand-efficiency p-value ranges are 0.654-0.682 wide and 0.554-0.554 tight.
- Worst-rank vancomycin sensitivity keeps synthetic values out of means/CIs. Affinity p-values are 0.378 wide and 0.329 tight; ligand-efficiency p-values are 0.580 wide and 0.482 tight.

## Boron gem-diol surrogates

- R-B(OH)2 -> R-CH(OH)2 gem-diol surrogate
- Best surrogate: bortezomib at -6.37 kcal/mol (spycep_7edd_native_active_site). Approximation only; see `boron_surrogate_result.json`.

## Limitations

- Predictions are not evidence of inhibition or efficacy; no therapeutic claim is made.
- Vina affinity is size-biased; ligand efficiency mitigates but does not remove this.
- Boron compounds have no MMFF94 or Vina parameters and are handled only as gem-diol surrogates.
- Rigid-receptor, single-conformer docking ignores protein flexibility.
- Custom positives are general protease motifs, not validated SpyCEP binders.
- Vancomycin is a real non-fit outcome in both SpyCEP boxes and is absent from mean-based comparisons.
- 10 entities carry an unspecified stereocentre that ETKDG assigned arbitrarily (amlodipine, argatroban, atropine, chymostatin, fluoxetine, ibuprofen, metoprolol, omeprazole, propranolol, warfarin); the docked isomer is recorded as `embedded_isomeric_smiles`.


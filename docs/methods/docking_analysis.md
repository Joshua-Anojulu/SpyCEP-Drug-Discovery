# Docking Methods And Results Note

Generated from tracked manifests by `scripts/write_docking_methods.py`.
Computational prioritization only; not evidence of binding or efficacy.

## Pipeline

SMILES (PubChem) -> desalt -> protonate to the dominant microspecies at pH 7.4 (explicit pKa rule set (spycep_drug_discovery.protonation)) -> RDKit ETKDGv3 (seed 42) 3D -> MMFF94 -> Meeko `mk_prepare_ligand` -> AutoDock Vina v1.2.7 (exhaustiveness 8, 9 modes, seed 42) over the 5XYA + 7EDD ensemble -> ligand-efficiency ranking -> per-residue catalytic-triad interaction analysis.

Ligands are docked as their charge state at pH 7.4, not as the neutral PubChem depiction: 40 of 73 prepared compounds carry a formal charge. The custom set is dominated by amidines and guanidines, which are cations at physiological pH; the S1 salt bridge is their entire binding rationale.

Two search boxes were used: the wide receptor-preparation box, and a tight box centred on the D151/H279/S617 **side-chain** centroid (`tight_pocket_definition.json`).

## Full-library result (wide box)

- Compounds docked: 73/77. Preparation failures: 4; docking failures: 0.
- Affinity range: -7.96 to -4.39 kcal/mol.
- Custom (n=18) vs FDA (n=55) mean best affinity: -5.89 vs -6.10 kcal/mol.
- Custom vs FDA mean ligand efficiency: -0.301 vs -0.264.

Top 10 by ligand efficiency:

| Rank | Ligand | Set | Charge | Ligand efficiency | Best (kcal/mol) |
| --- | --- | --- | --- | --- | --- |
| 1 | benzamidine | custom | +1 | -0.539 | -4.85 |
| 2 | metformin | FDA | +1 | -0.488 | -4.39 |
| 3 | allopurinol | FDA | +0 | -0.482 | -4.82 |
| 4 | acetaminophen | FDA | +0 | -0.472 | -5.19 |
| 5 | 4_aminobenzamidine | custom | +1 | -0.472 | -4.72 |
| 6 | pmsf | custom | +0 | -0.417 | -4.58 |
| 7 | 4_guanidinobenzoic_acid | custom | +0 | -0.410 | -5.33 |
| 8 | dci | custom | +0 | -0.396 | -5.14 |
| 9 | aebsf | custom | +1 | -0.380 | -4.93 |
| 10 | gabapentin | FDA | +0 | -0.378 | -4.54 |

## Tight triad-centred box (robustness check)

- Compounds docked: 72/77.
- Custom (n=18) vs FDA (n=54) mean best affinity: -5.64 vs -5.93 kcal/mol (non-fits with non-negative affinity are excluded).
- Custom vs FDA mean ligand efficiency: -0.290 vs -0.262.

## Catalytic-triad engagement

Counted per ligand (best receptor), not per ligand-by-receptor pose row:

| Box | ≥1 triad residue | ≥2 residues | all 3 residues |
| --- | --- | --- | --- |
| Wide | 73/73 | 64/73 | 42/73 |
| Tight | 72/72 | 66/72 | 47/72 |

## SpeB positive control

- Box: Cys192/His340 side-chain atoms only; the co-crystallised ligand is not used.
- Decoys: 17, size-matched to Q9D (25 heavy atoms; decoys 22-28).
- By best affinity: Q9D -6.70 kcal/mol, best decoy -6.92; beats all decoys: False.
- By ligand efficiency: Q9D -0.268, best decoy -0.283; beats all decoys: False.
- **Passes on both metrics: False.**

## Boron gem-diol surrogates

- each boron replaced by carbon (R-B(OH)2 -> R-CH(OH)2 gem-diol TS mimic); Vina lacks boron parameters
- Best surrogate: bortezomib at -6.33 kcal/mol (spycep_5xya_aes_active_site). Approximation only; see `boron_surrogate_result.json`.

## Limitations

- Predictions are not evidence of inhibition or efficacy; no therapeutic claim is made.
- Vina affinity is size-biased; ligand efficiency mitigates but does not remove this.
- Boron compounds have no MMFF94 or Vina parameters and are handled only as gem-diol surrogates.
- Rigid-receptor, single-conformer docking ignores protein flexibility.
- Custom positives are general protease motifs, not validated SpyCEP binders.
- 13 compounds carry an unspecified stereocentre that ETKDG assigned arbitrarily (chymostatin, clindamycin, azithromycin, argatroban, ibuprofen, omeprazole, warfarin, metoprolol, amlodipine, fluoxetine, atropine, morphine, propranolol); the docked isomer is recorded as `embedded_isomeric_smiles`.

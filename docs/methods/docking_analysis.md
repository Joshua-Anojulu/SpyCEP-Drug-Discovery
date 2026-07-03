# Docking Methods And Results Note

Generated from tracked manifests by `scripts/write_docking_methods.py`.
Computational prioritization only; not evidence of binding or efficacy.

## Pipeline

SMILES (PubChem) -> desalt -> RDKit ETKDGv3 (seed 42) 3D -> Meeko `mk_prepare_ligand` -> AutoDock Vina (exhaustiveness 8, 9 modes, seed 42) over the 5XYA + 7EDD ensemble -> ligand-efficiency ranking -> per-residue catalytic-triad interaction analysis.

Engine: AutoDock Vina v1.2.7. Two search boxes were used: the wide receptor-preparation box and a tight box centered on the D151/H279/S617 centroid (`tight_pocket_definition.json`).

## Full-library result (wide box)

- Compounds docked: 73/77. Failures: 8 (the four boronic acids; AutoDock Vina has no boron parameters).
- Custom vs FDA mean best affinity: -5.93 vs -6.21 kcal/mol.
- Custom vs FDA mean ligand efficiency: -0.304 vs -0.269 kcal/mol per heavy atom.

Top 10 by ligand efficiency:

| Rank | Ligand | Set | Ligand efficiency | Best (kcal/mol) |
| --- | --- | --- | --- | --- |
| 1 | benzamidine | custom | -0.544 | -4.90 |
| 2 | metformin | FDA | -0.497 | -4.47 |
| 3 | allopurinol | FDA | -0.482 | -4.82 |
| 4 | 4_aminobenzamidine | custom | -0.476 | -4.76 |
| 5 | acetaminophen | FDA | -0.474 | -5.22 |
| 6 | 4_guanidinobenzoic_acid | custom | -0.422 | -5.49 |
| 7 | pmsf | custom | -0.413 | -4.54 |
| 8 | gabapentin | FDA | -0.407 | -4.88 |
| 9 | apmsf | custom | -0.390 | -5.46 |
| 10 | dci | custom | -0.379 | -4.93 |

## Tight triad-centered box (robustness check)

- Compounds docked: 73/77.
- Custom vs FDA mean best affinity: -5.68 vs -5.96 kcal/mol (non-fits with non-negative affinity, e.g. oversized vancomycin, are excluded).
- Custom vs FDA mean ligand efficiency: -0.294 vs -0.263.
- FDA is marginally stronger on the mean in both boxes but the difference is not significant (bootstrap CI includes 0; see docking_statistics.json); the null is robust to box choice.

## Boron gem-diol surrogates

- each boron replaced by carbon (R-B(OH)2 -> R-CH(OH)2 gem-diol TS mimic); Vina lacks boron parameters
- Best surrogate: bortezomib at -6.70 kcal/mol (spycep_7edd_native_active_site). Approximation only; see `boron_surrogate_result.json`.

## Interpretation

Docking did not nominate a compelling small-molecule SpyCEP candidate. Scores are modest and rankings are metric-dependent; rational protease chemotypes are only weakly enriched by ligand efficiency. This reads as an honest benchmarking/negative result, consistent with the absence of any reported small-molecule SpyCEP inhibitor. See the manuscript draft in `docs/manuscript/`.

## Limitations

- Predictions are not evidence of inhibition or efficacy; no therapeutic claim is made.
- Vina affinity is size-biased; ligand efficiency mitigates but does not remove this.
- Boron compounds were approximated by gem-diol surrogates omitting boron chemistry.
- Rigid-receptor, single-ligand-conformer docking ignores protein flexibility.
- Custom positives are general protease motifs, not validated SpyCEP binders.

# Docking Methods Note

This file is generated from tracked manifests by `scripts/write_docking_methods.py`.
It documents the Milestone 3 compound-docking pipeline and the pipeline-validation pilot.

## Pipeline

1. **Ligand preparation** — SMILES are embedded to a single 3D conformer with RDKit ETKDGv3 (fixed seed 42) and MMFF-optimized, then converted to PDBQT with Meeko `mk_prepare_ligand`.
2. **Docking** — AutoDock Vina (executable, subprocess) docks each ligand into the tracked active-site box of each receptor in the ensemble.
3. **Ranking** — ligand efficiency (ensemble best affinity / heavy-atom count) is the primary ranking metric; raw affinity rank is retained for comparison.
4. **Interaction analysis** — the best pose is checked for atomic contacts (<= 4.0 A) with the catalytic triad D151/H279/S617.

## Configuration

- Docking engine: AutoDock Vina v1.2.7
- Search: exhaustiveness 8, num_modes 9, fixed seed 42.
- Receptor ensemble: spycep_5xya_aes_active_site, spycep_7edd_native_active_site.
- Boxes come from `docs/methods/pdbqt_conversion.json` / `receptor_preparation.json`.

## Validation Pilot

The pilot set (`docs/methods/validation_pilot_compounds.json`) is a throwaway pipeline check, **not** the research library and **not** a hit-discovery result.

- Reproducibility: benzamidine vs spycep_5xya_aes_active_site scored -4.897 kcal/mol on both the first and repeat run (deterministic = True).

Ranking:

| Rank (efficiency) | Ligand | Role | Heavy atoms | Ensemble best (kcal/mol) | Ligand efficiency | Rank (raw affinity) |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | benzamidine | positive | 9 | -4.897 | -0.5441 | 3 |
| 2 | 4_aminobenzamidine | positive | 10 | -4.748 | -0.4748 | 4 |
| 3 | ibuprofen | decoy | 15 | -5.367 | -0.3578 | 1 |
| 4 | caffeine | decoy | 14 | -4.975 | -0.3554 | 2 |

Active-site contacts (best pose):

| Ligand | Receptor | Best (kcal/mol) | Active-site contacts | Full triad |
| --- | --- | --- | --- | --- |
| benzamidine | spycep_5xya_aes_active_site | -4.897 | none | no |
| benzamidine | spycep_7edd_native_active_site | -4.603 | A:151:ASP | no |
| 4_aminobenzamidine | spycep_5xya_aes_active_site | -4.748 | none | no |
| 4_aminobenzamidine | spycep_7edd_native_active_site | -4.624 | A:151:ASP | no |
| caffeine | spycep_5xya_aes_active_site | -4.975 | none | no |
| caffeine | spycep_7edd_native_active_site | -4.503 | A:279:HIS, A:617:SER | no |
| ibuprofen | spycep_5xya_aes_active_site | -5.227 | A:617:SER | no |
| ibuprofen | spycep_7edd_native_active_site | -5.367 | A:151:ASP | no |

## Limitations

- Docking scores are computational predictions, not evidence of efficacy or binding in vitro.
- Raw AutoDock Vina affinity is biased by molecular size; in the pilot the larger drug decoys outranked the smaller amidine positives by raw score, and ligand efficiency was required to recover the expected ordering. Report ligand efficiency (and/or property-matched decoys).
- Receptor PDBQT files were generated with Meeko `--allow_bad_res`; some incomplete residues were omitted (none catalytic). See `docs/methods/pdbqt_quality_review.json`.
- The pilot positive controls are generic serine-protease-binding motifs, not SpyCEP-specific inhibitors, so the pilot validates the pipeline, not SpyCEP selectivity.
- Pilot poses in the 5XYA (AES-anchored) box did not contact the catalytic triad, unlike the 7EDD box; box placement and the removed AES anchor should be reviewed before real docking.

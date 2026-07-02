# Target Feasibility Notes

This file is generated from tracked RCSB metadata and the tracked target registry.
Manual structure-review fields come from `docs/methods/structure_review.json`.
It supports the decision gate for whether SpyCEP/ScpC should proceed to docking.

| Target | Role | PDB | Resolution | Overall | Catalytic | Pocket | Readiness | Review |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| spycep_scpC | primary | 5XXZ | 3.085 | not_suitable | unclear | rejected | rejected | UniProt Q3HV58 annotates active-site positions 151, 279, and 617. Coordinates contain D151, but PDB SEQADV mutates H279 and S617 to alanine in both chains. Excluded from native active-site docking; see docs/methods/pocket_definition.json. |
| spycep_scpC | primary | 5XYA | 3.0 | candidate | present | approved | approved | Coordinates contain native D151, H279, and S617. HET/SITE records place AES near H279 and S617; approved as the primary ligand-anchored receptor-preparation candidate in docs/methods/pocket_definition.json. |
| spycep_scpC | primary | 5XYR | 2.8 | manual_review_required | present | unclear | pending | Coordinates contain native D151, H279, and S617. Heterogens are chloride, calcium, sulfate, and malonate rather than a substrate-like inhibitor; retained as supporting evidence but not selected for the first receptor-preparation set. |
| spycep_scpC | primary | 7EDD | 2.897 | candidate | present | approved | approved | Coordinates contain native D151, H279, and S617 and this entry has the lowest missing-residue burden among the current SpyCEP set. Approved as the native coverage-comparator receptor-preparation candidate in docs/methods/pocket_definition.json. |

Decision rule: SpyCEP/ScpC can proceed only if at least one structure has usable metadata and passes manual pocket review. Metadata alone is not docking approval.

Pocket boxes are tracked in `docs/methods/pocket_definition.json`.
Cleaned receptor-preparation outputs are tracked in `docs/methods/receptor_preparation.json`; generated receptor PDB files remain ignored.
PDBQT conversion outputs are tracked in `docs/methods/pdbqt_conversion.json`.
PDBQT QC review is tracked in `docs/methods/pdbqt_quality_review.json`.
Generated PDBQT, Meeko JSON, and Vina box files remain ignored.

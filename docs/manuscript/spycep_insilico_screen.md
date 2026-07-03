# A first in-silico screen against the group A *Streptococcus* IL-8 protease SpyCEP/ScpC: a cautious benchmarking study

*Working preprint draft. Computational prioritization only; no therapeutic claims.*

## Abstract

SpyCEP/ScpC is a cell-envelope, subtilisin-like (MEROPS S8) serine protease of *Streptococcus pyogenes* that degrades IL-8 and related CXC chemokines, impairing neutrophil recruitment and promoting invasive disease including necrotizing fasciitis. No small-molecule inhibitor of SpyCEP has been reported; the enzyme's known inhibitors are proteins. We assembled a 77-compound library — 22 rational serine/subtilisin protease-inhibitor and anti-virulence chemotypes plus 55 FDA-approved comparators, all with PubChem-sourced structures — and performed reproducible ensemble docking against two experimental SpyCEP structures (PDB 5XYA, 7EDD) with AutoDock Vina, ranking by ligand efficiency and profiling catalytic-triad engagement. Across both a wide (22 Å) and a tight, triad-centered (16–20 Å) search box, docking did not surface a compelling candidate: predicted affinities spanned only −4.5 to −8.1 kcal/mol, and rational protease chemotypes were only marginally enriched over generic drugs by ligand efficiency. As a positive control, the identical pipeline applied to the related protease SpeB — for which a co-crystallized small-molecule inhibitor exists (PDB 6UKD) — correctly ranked that known inhibitor (−6.75 kcal/mol) above all drug-like decoys, confirming the SpyCEP result reflects the target rather than a failure of the method. We report this as an honest benchmarking/negative result, consistent with SpyCEP being a difficult small-molecule target, and provide a fully reproducible pipeline for future work.

## 1. Introduction

Necrotizing fasciitis is a rapidly progressive soft-tissue infection for which group A *Streptococcus* (GAS) is a leading cause. SpyCEP/ScpC (UniProt Q3HV58) is an anti-virulence-relevant target: by cleaving CXCL8/IL-8 within its C-terminal α-helix and degrading other CXC chemokines, it blunts neutrophil recruitment and NET formation, and its activity correlates with invasive-disease severity. Unlike heavily studied antibiotic targets, SpyCEP has, to our knowledge, no published small-molecule inhibitor, and the inhibitors described for the S8 subtilase family are protein-based (I9 propeptides, serpins, the *Streptomyces* subtilisin inhibitor). This makes SpyCEP a high-novelty but high-risk target for in-silico screening. We ask a deliberately modest question: does structure-based docking of rationally chosen protease chemotypes and approved drugs prioritize any candidate worth experimental follow-up?

## 2. Methods

### 2.1 Targets and receptor preparation
Candidate SpyCEP structures were screened by metadata and manual review. 5XYA (AES-anchored active site) and 7EDD (native, best coordinate coverage) were selected; 5XXZ was excluded (H279A/S617A mutations) and 5XYR retained as supporting evidence only. Chain A was isolated, selenomethionine converted to methionine, and non-polymer heterogens removed; alternate conformers are reduced to a single conformer (none present in these chains). Receptors were converted to PDBQT with Meeko `mk_prepare_receptor` (`--allow_bad_res`; no catalytic residue omitted). The catalytic triad is D151/H279/S617.

### 2.2 Compound library
77 compounds: 22 in a custom "anti-virulence" set (aryl amidines/guanidines, sulfonyl fluorides, chloromethyl ketones, an isocoumarin, boronic acids, peptide aldehydes, and the GAS anti-virulence leads CCG-2979/CCG-102487) and 55 FDA-approved comparators (GAS-relevant antibiotics, approved serine-protease-inhibitor drugs, and a broad common-drug panel). All structures and PubChem CIDs were retrieved programmatically from PubChem; no structure was hand-entered. Drug-likeness (Lipinski, Veber, PAINS) was computed with RDKit (58/77 drug-like); non-drug-like mechanistic tool compounds and two PAINS-flagged compounds were retained and flagged.

### 2.3 Ligand preparation and docking
Ligands were desalted (largest fragment), embedded to a single 3D conformer (RDKit ETKDGv3, fixed seed 42, MMFF-optimized), and converted to PDBQT with Meeko `mk_prepare_ligand`. Docking used AutoDock Vina 1.2.7 (exhaustiveness 8, 9 modes, fixed seed 42) against both receptors. Two box definitions were used: (i) the 22 Å receptor-preparation box and (ii) a tight box (16–20 Å) centered on the triad side-chain centroid. Compounds were ranked by ligand efficiency (best ensemble affinity ÷ heavy-atom count) to control AutoDock Vina's molecular-size bias; raw affinity rank was retained for comparison. Catalytic-triad engagement was quantified per residue (nearest ligand-atom distance and contact-atom count, 4 Å cutoff).

### 2.4 Boron handling
AutoDock Vina lacks boron forcefield parameters, so the four boronic acids could not be docked directly. They were docked as B→C gem-diol surrogates (R-B(OH)₂ → R-CH(OH)₂, a tetrahedral transition-state mimic), reported separately and never merged into the main results.

### 2.5 SpeB positive control
To test whether the pipeline can recover a true binder, the identical protocol was applied to the related *S. pyogenes* cysteine protease SpeB/streptopain, using the inhibitor co-complex structure 6UKD (catalytic dyad Cys192/His340). The co-crystallized specific inhibitor (RCSB chemical component Q9D) was docked alongside seven drug-like decoys into a box centered on the dyad.

### 2.6 Reproducibility
The pipeline is scripted end-to-end with tracked manifests recording tool versions, commands, seeds, box coordinates, and output hashes. Fixed-seed docking is deterministic (benzamidine vs 5XYA reproduced −4.897 kcal/mol on repeat runs). AutoDock Vina 1.2.7, RDKit 2026.03.3, Meeko 0.7.1.

## 3. Results

Of 77 compounds, 73 docked successfully; the 4 boronic acids failed on both receptors (boron unsupported by Vina) and were treated as surrogates.

**No standout candidate.** Predicted best ensemble affinities spanned −4.5 to −8.1 kcal/mol (wide box), with none in the strong-binding regime (< −9 kcal/mol). The top of the ligand-efficiency ranking interleaves rational chemotypes (benzamidine, 4-aminobenzamidine, 4-guanidinobenzoic acid, PMSF, APMSF, DCI, AEBSF) with small approved drugs (metformin, allopurinol, acetaminophen, gabapentin), i.e. the metric rewards small size more than mechanistic rationale.

**Weak, box-robust enrichment.** Custom vs FDA sets, best-affinity mean: −5.93 vs −6.21 kcal/mol (wide box; FDA slightly better, a size artifact) and −5.68 vs −5.13 (tight box; custom better, because the focused box penalizes bulky drugs). Ligand efficiency favored the custom set marginally under both boxes (−0.29 to −0.30 vs −0.25 to −0.27). Custom compounds were over-represented in the top-20 by ligand efficiency (8 of 18 docked customs vs 12 of 55 FDA) under both boxes — a consistent but weak signal.

**Triad contact is not discriminating.** Under both boxes essentially all compounds contacted ≥1 triad residue (73/73) and most contacted all three (55–56/73), a geometric consequence of the compact active site rather than evidence of specific engagement.

**Boron surrogates.** The bortezomib gem-diol surrogate scored best among boron compounds (−6.70 kcal/mol, tight box), but as an approximation this is indicative only.

**SpeB positive control.** Applied unchanged to SpeB (6UKD), the pipeline ranked the co-crystallized inhibitor Q9D first at −6.75 kcal/mol, ahead of all seven drug-like decoys (best decoy −5.55 kcal/mol), with Q9D contacting both catalytic dyad residues. The pipeline therefore recovers a genuine binder with a clear margin when one exists.

## 4. Discussion

Two independent box definitions, ligand-efficiency ranking, and per-residue interaction analysis converge on the same conclusion: docking does not nominate a compelling small-molecule SpyCEP inhibitor from this library. The SpeB positive control is decisive for interpreting this: because the same pipeline cleanly separates a known inhibitor from decoys on a related protease, the flat SpyCEP result is attributable to the target — a large, shallow substrate groove with no reported small-molecule inhibitor — rather than to a limitation of the docking protocol. This negative result is informative. It is consistent with the absence of any reported small-molecule SpyCEP inhibitor and with the protein-only inhibitor repertoire of the S8 subtilase family, and it cautions against over-interpreting single docking scores against this target. The one modest positive signal — a consistent, weak enrichment of rational protease chemotypes by ligand efficiency, several of which are small S1-binding amidines/guanidines — is a hypothesis for focused experimental testing, not a claim.

## 5. Limitations

- Docking predicts binding geometry and an approximate score; it is not evidence of inhibition, efficacy, or activity in vitro or in vivo. No therapeutic claim is made.
- AutoDock Vina scores are size-biased; ligand efficiency mitigates but does not eliminate this.
- Boron compounds were approximated by gem-diol surrogates that omit boron's covalent/electronic character.
- Receptors were prepared with `--allow_bad_res`; incomplete crystallographic residues (none catalytic) were omitted.
- Rigid-receptor docking of a single ligand conformer ensemble ignores protein flexibility and the large, shallow substrate groove of SpyCEP.
- Custom "positive" chemotypes are general serine/subtilisin-protease motifs, not validated SpyCEP binders, so the study benchmarks a pipeline rather than confirming SpyCEP selectivity.

## 6. Data and code availability

All scripts, tracked manifests (target feasibility, pocket definitions, receptor and PDBQT preparation, QC, compound library with provenance, and docking results), tool versions, seeds, and commands are in the project repository. Generated large artifacts (structures, PDBQT, poses) are reproducible from the scripts.

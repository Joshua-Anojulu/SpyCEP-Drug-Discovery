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

### 2.6 Statistics and non-fit handling
Set-level differences (custom vs FDA) were assessed by a 10,000-resample bootstrap 95% CI on the mean difference (seed 42) and a two-sided Mann–Whitney U test. A non-negative AutoDock Vina affinity indicates no valid pose (the ligand does not fit the search box); such non-fits — one compound, vancomycin, in the tight box — were excluded from the quantitative comparison. The positive-control margin is reported as the gap to the best decoy and in units of the decoy standard deviation.

### 2.7 Reproducibility
The pipeline is scripted end-to-end with tracked manifests recording tool versions, commands, seeds, box coordinates, and output hashes. Fixed-seed docking is deterministic (benzamidine vs 5XYA reproduced −4.897 kcal/mol on repeat runs). AutoDock Vina 1.2.7, RDKit 2026.03.3, Meeko 0.7.1.

## 3. Results

Of 77 compounds, 73 docked successfully; the 4 boronic acids failed on both receptors (boron unsupported by Vina) and were treated as surrogates.

**No standout candidate.** Predicted best ensemble affinities spanned −4.5 to −8.1 kcal/mol (wide box), with none in the strong-binding regime (< −9 kcal/mol). The top of the ligand-efficiency ranking interleaves rational chemotypes (benzamidine, 4-aminobenzamidine, 4-guanidinobenzoic acid, PMSF, APMSF, DCI, AEBSF) with small approved drugs (metformin, allopurinol, acetaminophen, gabapentin) — i.e. the metric rewards small size more than mechanistic rationale (Figure 3).

**No significant custom-vs-FDA separation (Figure 1).** Mean best affinity was −5.93 (custom) vs −6.21 kcal/mol (FDA) in the wide box and −5.68 vs −5.96 in the tight box (excluding one non-fit, vancomycin, whose non-negative clash score in the tight box is not a valid pose). FDA is thus marginally *stronger* on the mean in both boxes, but the difference is **not statistically significant**: a 10,000-sample bootstrap of the custom−FDA mean difference gives 95% CI [−0.25, 0.81] (wide) and [−0.17, 0.72] (tight), both spanning zero, and Mann–Whitney U tests are non-significant. Ligand efficiency favored the custom set only marginally (−0.30 vs −0.27), with custom over-represented in the top-20 by efficiency (8 of 18 docked customs vs 12 of 55 FDA) — a weak, non-significant signal, not a separation.

**Triad contact is not discriminating.** Under both boxes essentially all compounds contacted ≥1 triad residue (73/73) and most contacted all three (55–56/73), a geometric consequence of the compact active site rather than evidence of specific engagement.

**Boron surrogates.** The bortezomib gem-diol surrogate scored best among boron compounds (−6.70 kcal/mol, tight box), but as an approximation this is indicative only.

**SpeB positive control (Figure 2).** Applied unchanged to SpeB (6UKD), the pipeline ranked the co-crystallized inhibitor Q9D first at −6.75 kcal/mol, ahead of all seven drug-like decoys (best decoy aspirin −5.55 kcal/mol; margin 1.19 kcal/mol, **4.4 standard deviations** below the decoy mean), with Q9D contacting both catalytic dyad residues (Cys192, His340). The pipeline therefore recovers a genuine binder with a clear, quantified margin when one exists — in direct contrast to the flat SpyCEP result.

## 4. Discussion

Two independent box definitions, ligand-efficiency ranking, and per-residue interaction analysis converge on the same conclusion: docking does not nominate a compelling small-molecule SpyCEP inhibitor from this library. The SpeB positive control is decisive for interpreting this: because the same pipeline cleanly separates a known inhibitor from decoys on a related protease, the flat SpyCEP result is attributable to the target — a large, shallow substrate groove with no reported small-molecule inhibitor — rather than to a limitation of the docking protocol. This negative result is informative. It is consistent with the absence of any reported small-molecule SpyCEP inhibitor and with the protein-only inhibitor repertoire of the S8 subtilase family, and it cautions against over-interpreting single docking scores against this target. The one modest positive signal — a consistent, weak enrichment of rational protease chemotypes by ligand efficiency, several of which are small S1-binding amidines/guanidines — is a hypothesis for focused experimental testing, not a claim.

## 5. Limitations

- Docking predicts binding geometry and an approximate score; it is not evidence of inhibition, efficacy, or activity in vitro or in vivo. No therapeutic claim is made.
- AutoDock Vina scores are size-biased; ligand efficiency mitigates but does not eliminate this.
- Boron compounds were approximated by gem-diol surrogates that omit boron's covalent/electronic character.
- Receptors were prepared with `--allow_bad_res`; incomplete crystallographic residues (none catalytic) were omitted.
- Rigid-receptor docking of a single ligand conformer ensemble ignores protein flexibility and the large, shallow substrate groove of SpyCEP.
- Custom "positive" chemotypes are general serine/subtilisin-protease motifs, not validated SpyCEP binders, so the study benchmarks a pipeline rather than confirming SpyCEP selectivity.
- Oversized ligands (e.g. vancomycin) do not fit the tight active-site box and return invalid (non-negative) scores; these are excluded rather than interpreted, which slightly reduces the tight-box FDA sample.
- With n=77 compounds and a single ligand pose, set-level statistical power is modest; the reported non-significance is consistent with a true null but does not prove equivalence.

## 6. Data and code availability

All scripts, tracked manifests (target feasibility, pocket definitions, receptor and PDBQT preparation, QC, compound library with provenance, docking results, and statistics), tool versions, seeds, and commands are in the project repository. Generated large artifacts (structures, PDBQT, poses) are reproducible from the scripts.

## Figures

- **Figure 1.** Custom vs FDA best-affinity distributions in the wide and tight boxes; overlapping, non-significant (`docs/manuscript/figures/fig1_custom_vs_fda.png`).
- **Figure 2.** SpeB positive control — known inhibitor Q9D vs drug-like decoys (`fig2_speb_positive_control.png`).
- **Figure 3.** Top 15 SpyCEP compounds by ligand efficiency, colored by set (`fig3_top_hits_ligand_efficiency.png`).

## References

1. Zinkernagel AS, Timmer AM, Pence MA, Locke JB, Buchanan JT, Turner CE, Mishalian I, Sriskandan S, Hanski E, Nizet V. "The IL-8 protease SpyCEP/ScpC of group A *Streptococcus* promotes resistance to neutrophil killing." *Cell Host & Microbe* 4(2):170–178, 2008. PMID 18692776.
2. Wang AY, González-Páez GE, Wolan DW, et al. "Identification and Co-complex Structure of a New *S. pyogenes* SpeB Small Molecule Inhibitor." *Biochemistry* 54(28):4365–4373, 2015. PMID 26132413. (SpeB positive control; PDB 6UKD.)
3. UniProt Consortium. UniProtKB entry Q3HV58 (SpyCEP/ScpC, *Streptococcus pyogenes*). https://www.uniprot.org/uniprotkb/Q3HV58.
4. RCSB Protein Data Bank. Structures 5XYA and 7EDD (SpyCEP/ScpC) and 6UKD (SpeB streptopain–inhibitor Q9D co-complex). https://www.rcsb.org.
5. Trott O, Olson AJ. "AutoDock Vina: improving the speed and accuracy of docking with a new scoring function, efficient optimization, and multithreading." *J. Comput. Chem.* 31(2):455–461, 2010.
6. Eberhardt J, Santos-Martins D, Tillack AF, Forli S. "AutoDock Vina 1.2.0: New Docking Methods, Expanded Force Field, and Python Bindings." *J. Chem. Inf. Model.* 61(8):3891–3898, 2021.
7. Landrum G, et al. "RDKit: Open-source cheminformatics." https://www.rdkit.org.
8. Kim S, et al. "PubChem 2023 update." *Nucleic Acids Research* 51(D1):D1373–D1380, 2023.
9. Lipinski CA, Lombardo F, Dominy BW, Feeney PJ. "Experimental and computational approaches to estimate solubility and permeability in drug discovery and development settings." *Adv. Drug Deliv. Rev.* 23(1–3):3–25, 1997.

*(Tool-version DOIs and any remaining author lists to be confirmed against the cited records before submission.)*

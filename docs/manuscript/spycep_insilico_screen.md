# A docking screen against the group A *Streptococcus* IL-8 protease SpyCEP/ScpC, and the positive control that fails it

*Working preprint draft. Computational prioritization only; no therapeutic claims.*

## Abstract

SpyCEP/ScpC is a cell-envelope subtilisin-like (MEROPS S8) serine protease of *Streptococcus pyogenes* that cleaves IL-8 and related CXC chemokines, blunts neutrophil recruitment, and promotes invasive disease including necrotizing fasciitis. No small-molecule inhibitor of SpyCEP has been reported, and the inhibitors known for its family are proteins. We assembled a 77-compound library of 22 rational serine-protease and anti-virulence chemotypes plus 55 FDA-approved comparators, all sourced from PubChem, and docked it against two experimental SpyCEP structures (PDB 5XYA, 7EDD) with AutoDock Vina. Ligands were docked as their dominant microspecies at pH 7.4, so that the amidines and guanidines that motivate the custom set carry the cationic charge that forms the S1 salt bridge. Across a wide 22 Å box and a tight box centred on the catalytic-triad side chains, no compound reached the strong-binding regime: predicted affinities span −4.4 to −8.0 kcal/mol, and the rational chemotypes do not separate from generic drugs under either box (bootstrap 95% CI on the mean difference spans zero; Mann-Whitney p = 0.32 and p = 0.26). We then applied the identical pipeline to SpeB, a related *S. pyogenes* protease with a co-crystallised small-molecule inhibitor (PDB 6UKD, ligand Q9D), using a search box built from the catalytic dyad alone and 17 decoys size-matched to the inhibitor. **The pipeline failed to recover the known binder.** Q9D ranked 6th of 20 by affinity and 7th of 20 by ligand efficiency, behind dexamethasone, ampicillin and celecoxib. We therefore cannot attribute the SpyCEP null to the target. The screen shows what this class of docking can and cannot resolve, and we report it as a cautionary benchmark rather than as evidence that SpyCEP resists small molecules.

## 1. Introduction

Group A *Streptococcus* is a leading cause of necrotizing fasciitis. SpyCEP/ScpC (UniProt Q3HV58) cleaves CXCL8/IL-8 within its C-terminal α-helix and degrades other CXC chemokines, which suppresses neutrophil recruitment and NET formation, and its activity tracks with invasive-disease severity. That makes it an appealing anti-virulence target: disarm the bacterium instead of killing it. It is also a hard one. No published small-molecule inhibitor exists, and the S8 subtilase family is inhibited by proteins (I9 propeptides, serpins, the *Streptomyces* subtilisin inhibitor) rather than by drug-like compounds.

We asked a modest question. Does structure-based docking of rational protease chemotypes and approved drugs prioritise any SpyCEP candidate worth testing at the bench? A second question turned out to matter more. Can the docking pipeline recover a known inhibitor of a comparable protease when the test is not rigged in its favour?

## 2. Methods

### 2.1 Targets and receptor preparation
We screened candidate SpyCEP structures by metadata and manual review, and selected 5XYA (active site anchored by the bound AES fragment) and 7EDD (native, best coordinate coverage). We excluded 5XXZ, which carries H279A and S617A active-site mutations, and retained 5XYR as supporting evidence. We isolated chain A, converted selenomethionine to methionine, removed non-polymer heterogens, and reduced alternate conformers to one. Meeko `mk_prepare_receptor` produced the PDBQT with `--allow_bad_res`. No catalytic residue was omitted; the omitted-residue inventory (81 residues for 5XYA, 24 for 7EDD) is parsed from the converter's full stderr and gated against the active site before docking. The catalytic triad is D151/H279/S617.

### 2.2 Compound library
The library holds 77 compounds. Twenty-two form a custom anti-virulence set: aryl amidines and guanidines, sulfonyl fluorides, chloromethyl ketones, an isocoumarin, boronic acids, peptide aldehydes, and the GAS anti-virulence leads CCG-2979 and CCG-102487. Fifty-five are FDA-approved comparators spanning GAS-relevant antibiotics, approved serine-protease-inhibitor drugs, and a common-drug panel. A script retrieved every structure and PubChem CID from PubChem. Nothing was hand-drawn. RDKit computed drug-likeness (58 of 77 pass Lipinski and Veber without PAINS flags); we retained and flagged the non-drug-like mechanistic tool compounds.

### 2.3 Protonation
We docked each ligand as its dominant microspecies at pH 7.4 rather than as the neutral PubChem depiction. This matters for the question at hand: 11 of the 22 custom compounds carry an amidine or guanidine (pKa 11.6 to 13.6), which is a cation at physiological pH, and the amidinium salt bridge into S1 is the entire binding rationale for the chemotype. Docking them neutral would remove the interaction the study exists to test.

We assign states from an explicit pKa rule set rather than from a microspecies enumerator. Carboxylic acids, sulfonic acids, phosphonates, tetrazoles and the 4-hydroxycoumarin enol of warfarin lose a proton. Amidines, guanidines and aliphatic amines gain one, with a single charge per conjugated amidine system so that a biguanide such as metformin takes one charge and not two. Phenols, imidazoles, thiols and anilines stay neutral, since their pKa values sit too close to 7.4 for the dominant species to be unambiguous. The rules validate against literature charges for 24 reference compounds. Forty of the 73 docked compounds carry a formal charge; none did before.

### 2.4 Ligand preparation and docking
We desalted each compound to its largest fragment, protonated it, embedded a single conformer with RDKit ETKDGv3 (seed 42), and optimised with MMFF94. Preparation raises an error when MMFF94 cannot parameterise a molecule, which rejects the four boronic acids rather than emitting an unoptimised geometry as if it were prepared. Meeko `mk_prepare_ligand` wrote the PDBQT.

Docking used AutoDock Vina 1.2.7 (exhaustiveness 8, 9 modes, seed 42) against both receptors under two box definitions: the 22 Å receptor-preparation box, and a tight box of 16 Å centred on the centroid of the D151/H279/S617 **side-chain** atoms. We rank by ligand efficiency (best ensemble affinity divided by heavy-atom count) to correct Vina's bias toward large molecules, and retain the raw affinity rank alongside it. Catalytic-triad engagement is measured per residue as nearest ligand-atom distance and contact-atom count within 4 Å.

A single Vina call is bounded by a compute budget. Vancomycin (101 heavy atoms) returned no pose against the 16 Å box after five hours and is recorded as a non-fit for that box, alongside the non-negative clash scores Vina returns for oversized ligands. It docked without incident in the wide box.

### 2.5 Boron handling
Vina has no boron parameters and MMFF94 has none either, so the four boronic acids cannot be docked directly. We docked them as B→C gem-diol surrogates (R-B(OH)₂ → R-CH(OH)₂), a tetrahedral transition-state mimic, and report them apart from the main result. They are never merged into it.

### 2.6 SpeB positive control
To test whether the pipeline recovers a true binder, we applied the identical protocol to SpeB/streptopain using the inhibitor co-complex 6UKD (catalytic dyad Cys192/His340) and its co-crystallised inhibitor Q9D.

Two design choices decide whether such a control means anything, and an earlier version of this study got both wrong. First, the search box must not be built from the ligand's own coordinates. Ours is defined by the Cys192 and His340 side-chain atoms alone, which is information a prospective screen would have. Second, the decoys must be size-matched, because Vina's raw score scales with molecular size. We drew 19 comparators from our own FDA set restricted to within ±3 heavy atoms of Q9D (25 heavy atoms), and labelled the two whose mechanism is protease inhibition (nafamostat, gabexate) so that a strong score from them is not counted as a false positive. That leaves 17 decoys. We report the control on raw affinity and on ligand efficiency, since judging it on the size-biased metric alone would contradict the metric used everywhere else in the study.

### 2.7 Statistics
Set-level differences were assessed with a 10,000-resample bootstrap 95% CI on the mean difference (seed 42) and a two-sided Mann-Whitney U test. Triad engagement is counted per ligand over its best receptor, not per ligand-by-receptor pose row.

### 2.8 Reproducibility
The pipeline is scripted end to end. Tracked manifests record tool versions, seeds, box coordinates, the SMILES of the species that was docked, the isomer ETKDG assigned where the input left a stereocentre unspecified, and a SHA-256 for every Vina invocation and its command line. Fixed-seed docking is deterministic. AutoDock Vina 1.2.7, RDKit 2026.03.3, Meeko 0.7.1. The suite runs 109 tests.

## 3. Results

Of 77 compounds, 73 docked in the wide box and 72 in the tight box. The four boronic acids failed preparation and were handled as surrogates; vancomycin does not fit the 16 Å box.

**No candidate emerged.** Best ensemble affinities span −4.39 to −7.96 kcal/mol in the wide box and −4.11 to −7.84 in the tight box. Nothing approaches the strong-binding regime below −9 kcal/mol. The top of the ligand-efficiency ranking interleaves rational chemotypes (benzamidine, 4-aminobenzamidine, PMSF, DCI, AEBSF, 4-guanidinobenzoic acid) with small approved drugs (metformin, allopurinol, acetaminophen, gabapentin). Benzamidine leads the ranking and metformin sits second, which shows the metric rewarding small size ahead of mechanistic rationale (Figure 3).

**Correct protonation does not rescue the custom set (Figure 1).** Mean best affinity was −5.89 kcal/mol for the custom compounds against −6.10 for the FDA drugs in the wide box, and −5.64 against −5.93 in the tight box. The approved drugs score 0.2 to 0.3 kcal/mol stronger on the mean in both boxes. The difference does not reach significance: the bootstrap 95% CI on the custom-minus-FDA mean difference is [−0.33, 0.72] wide and [−0.16, 0.74] tight, both spanning zero, with Mann-Whitney p = 0.32 and p = 0.26. Ligand efficiency favours the custom set by a small margin (−0.301 against −0.264 wide), and the custom compounds hold 7 of the top 20 by efficiency out of 18 docked, against 13 of 20 from 55 FDA compounds. This is a weak enrichment and not a separation.

Benzamidine is the case that settles the protonation question. It carries the +1 amidinium charge that forms the canonical S1 salt bridge, and it still ranks 67th of 73 by affinity. Giving the archetypal warhead its correct charge changed nothing about where it lands.

**Triad contact does not discriminate (Figure 4).** Every docked compound contacts at least one triad residue (73 of 73 wide, 72 of 72 tight), and 42 of 73 contact all three in the wide box, 47 of 72 in the tight box. A compact active site produces this geometry for anything dropped into it, so triad contact carries no signal about specific engagement. An earlier version of this study reported "55 to 56 of 73" contacting all three. That figure is a pose-row count out of 146 presented as a per-ligand count, and no reading of the manifests reproduces it.

**Boron surrogates.** The bortezomib gem-diol surrogate scored best among the four at −6.33 kcal/mol. As an approximation that discards boron's covalent and electronic character, this is indicative and nothing more.

**The positive control fails (Figure 2).** Against SpeB, with a box built from the catalytic dyad and 17 size-matched decoys, the pipeline did not recover the known inhibitor. Q9D scored −6.70 kcal/mol and ranked **6th of 20** by affinity, behind dexamethasone (−6.92), ampicillin (−6.76), celecoxib (−6.76), prednisone (−6.75) and amoxicillin (−6.71). By ligand efficiency it ranked **7th of 20**. It sits 0.8 standard deviations from the decoy mean by affinity and 0.5 by efficiency. Q9D does contact both catalytic dyad residues, so the pose is plausible; the score does not separate it from ordinary drugs of the same size.

An earlier version of this study reported that Q9D beat all decoys by 4.4 standard deviations. That result came from a search box whose centre was computed from Q9D's own crystallographic coordinates, and from decoys averaging 11.9 heavy atoms against the inhibitor's 25. Removing the ligand from the box definition and matching the decoys on size removes the effect.

## 4. Discussion

Two box definitions, corrected ionisation states, ligand-efficiency ranking and per-residue interaction analysis converge on the same reading of SpyCEP: this library contains no compelling small-molecule candidate, and the rational chemotypes do not beat a panel of unrelated approved drugs. Taken alone, that reads as a hard target.

We cannot draw that conclusion, because the pipeline fails its own positive control. On SpeB, where a genuine small-molecule inhibitor exists and sits in a solved co-complex, the same protocol ranks that inhibitor behind a corticosteroid and two β-lactams. A method that cannot distinguish a known binder from dexamethasone has not earned the right to tell us that SpyCEP is undruggable. The SpyCEP null is consistent with a hard target. It is as consistent with a scoring function that lacks the resolution to answer the question, and this study cannot separate those two readings.

Part of the explanation lies in the control itself. Q9D is a covalent inhibitor: it forms a bond with Cys192. AutoDock Vina scores non-covalent interactions, so a covalent warhead's docked score reflects only the pre-covalent encounter complex and carries no credit for the bond that produces the inhibition. A covalent inhibitor is a poor instrument for validating a non-covalent docking pipeline, and the earlier 4.4-standard-deviation "pass" concealed that mismatch behind a box built from the answer. The wider point stands regardless of Q9D's chemistry: Vina's scoring function is known to rank actives against property-matched decoys with modest enrichment, and our result is an instance of a known weakness.

The one signal we can report is a weak enrichment of small S1-binding amidines and guanidines by ligand efficiency. It is not significant, the metric that produces it also elevates metformin and acetaminophen, and we offer it as a hypothesis for bench testing rather than as a finding.

## 5. Limitations

- Docking predicts a geometry and an approximate score. It is not evidence of inhibition, efficacy, or activity in cells or animals. We make no therapeutic claim.
- The pipeline does not pass a fair positive control, so its power to recover true binders is unmeasured. Every negative statement about SpyCEP in this paper inherits that limitation.
- Q9D is covalent and Vina is not, which makes SpeB an imperfect benchmark. A non-covalent inhibitor with a solved co-complex against an S8 or papain-family protease would be a better control, and we did not find one.
- Vina affinity scales with molecular size. Ligand efficiency mitigates this and does not remove it, as the metformin and allopurinol results show.
- Boron compounds have no MMFF94 or Vina parameters and appear only as gem-diol surrogates that discard boron's covalent character.
- Receptors are rigid and each ligand contributes one conformer, which ignores protein flexibility. SpyCEP presents a large shallow substrate groove, the case where rigid-receptor docking is least reliable.
- Thirteen compounds carry a stereocentre the source SMILES leaves unspecified, including chymostatin and argatroban. ETKDG assigned each one at random, so those affinities belong to a single arbitrary diastereomer. The manifests record the isomer that was docked.
- Vancomycin does not fit the 16 Å triad box and is absent from the tight-box comparison.
- The custom compounds are general serine-protease motifs and not validated SpyCEP binders, so the study benchmarks a pipeline against a target rather than testing a designed series.
- With 77 compounds and one pose each, the power to detect a set-level difference is low. Non-significance here is consistent with a true null and does not establish equivalence.

## 6. Data and code availability

Scripts, tracked manifests (target feasibility, pocket definitions, receptor and PDBQT preparation, converter QC, the compound library with provenance, per-docking commands and output hashes, and statistics), tool versions, seeds and commands are in the project repository. Large artifacts (structures, PDBQT files, poses) regenerate from the scripts.

## Figures

- **Figure 1.** Custom versus FDA best-affinity distributions in the wide and tight boxes. The distributions overlap and the difference is not significant (`fig1_custom_vs_fda.png`).
- **Figure 2.** SpeB positive control, shown on raw affinity and on ligand efficiency, against decoys size-matched to Q9D. The known inhibitor does not lead either ranking (`fig2_speb_positive_control.png`).
- **Figure 3.** Top 15 SpyCEP compounds by ligand efficiency, coloured by set (`fig3_top_hits_ligand_efficiency.png`).
- **Figure 4.** Per-ligand catalytic-triad engagement in both boxes (`fig4_triad_engagement.png`).

## References

1. Zinkernagel AS, Timmer AM, Pence MA, Locke JB, Buchanan JT, Turner CE, Mishalian I, Sriskandan S, Hanski E, Nizet V. "The IL-8 protease SpyCEP/ScpC of group A *Streptococcus* promotes resistance to neutrophil killing." *Cell Host & Microbe* 4(2):170–178, 2008. PMID 18692776.
2. Wang AY, González-Páez GE, Wolan DW. "Identification and co-complex structure of a new *S. pyogenes* SpeB small molecule inhibitor." *Biochemistry* 54(28):4365–4373, 2015. PMID 26132413. (SpeB positive control; PDB 6UKD.)
3. UniProt Consortium. UniProtKB entry Q3HV58 (SpyCEP/ScpC, *Streptococcus pyogenes*). https://www.uniprot.org/uniprotkb/Q3HV58
4. RCSB Protein Data Bank. Structures 5XYA and 7EDD (SpyCEP/ScpC) and 6UKD (SpeB–Q9D co-complex). https://www.rcsb.org
5. Trott O, Olson AJ. "AutoDock Vina: improving the speed and accuracy of docking with a new scoring function, efficient optimization, and multithreading." *J. Comput. Chem.* 31(2):455–461, 2010.
6. Eberhardt J, Santos-Martins D, Tillack AF, Forli S. "AutoDock Vina 1.2.0: new docking methods, expanded force field, and Python bindings." *J. Chem. Inf. Model.* 61(8):3891–3898, 2021.
7. Landrum G, et al. "RDKit: open-source cheminformatics." https://www.rdkit.org
8. Kim S, et al. "PubChem 2023 update." *Nucleic Acids Research* 51(D1):D1373–D1380, 2023.
9. Lipinski CA, Lombardo F, Dominy BW, Feeney PJ. "Experimental and computational approaches to estimate solubility and permeability in drug discovery and development settings." *Adv. Drug Deliv. Rev.* 23(1–3):3–25, 1997.

*(Tool-version DOIs and remaining author lists to be confirmed against the cited records before submission.)*

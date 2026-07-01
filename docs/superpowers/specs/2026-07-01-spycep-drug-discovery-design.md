# SpyCEP Drug Discovery Design

Date: 2026-07-01

## Purpose

Build a preprint-grade, reproducible computational drug discovery project that prioritizes anti-virulence inhibitor candidates against *Streptococcus pyogenes* SpyCEP/ScpC, a chemokine-degrading protease relevant to immune evasion in severe group A streptococcal infection.

The project must remain scientifically cautious. It will not claim to cure or treat necrotizing fasciitis. The intended contribution is an in-silico prioritization workflow and candidate ranking that could motivate later experimental testing.

## Approved Scientific Scope

Disease focus: necrotizing fasciitis associated with group A *Streptococcus pyogenes*.

Primary target: SpyCEP/ScpC, the IL-8/CXC chemokine-degrading protease.

Fallback target: SpeB, the streptococcal cysteine protease, if SpyCEP/ScpC is not structurally suitable for defensible docking.

Main research direction: novelty-first ensemble docking and analysis against SpyCEP/ScpC, using a curated anti-virulence/protease-focused compound library and FDA-approved compounds as a comparator set.

## Rationale

Necrotizing fasciitis is a severe, rapidly progressive infection that requires urgent clinical treatment. Group A *Streptococcus* is a key cause. A computational project in this area should avoid therapeutic claims and focus on early-stage hit prioritization.

SpyCEP/ScpC is attractive because it has an anti-virulence mechanism: degradation of CXC chemokines and promotion of resistance to neutrophil killing. This is more novel than screening a heavily studied generic antibiotic target. It is also riskier because SpyCEP/ScpC is large and available structures may be harder to use for small-molecule docking.

SpeB is the fallback because it has strong virulence relevance and multiple experimental structures, including inhibitor-complex structures.

## Evidence Checked

- CDC necrotizing fasciitis overview: https://www.cdc.gov/group-a-strep/about/necrotizing-fasciitis.html
- UniProt SpyCEP/ScpC candidate: Q3HV58, chemokine protease C, *Streptococcus pyogenes*.
- RCSB SpyCEP/ScpC candidate structures identified from UniProt: 5XXZ, 5XYA, 5XYR, 7EDD.
- PubMed SpyCEP/ScpC rationale: PMID 18692776, "The IL-8 protease SpyCEP/ScpC of group A Streptococcus promotes resistance to neutrophil killing."
- SpeB fallback UniProt: P0C0J0.
- SpeB fallback structures identified from UniProt/RCSB: 1DKI, 1PVJ, 2UZJ, 4D8B, 4D8E, 4D8I, 6UKD, 6UQD.
- SpeB structure and inhibitor literature includes PMID 26132413 and PMID 10681429.
- Sortase A and C5a peptidase were considered as possible fallback or benchmarking targets, but are not the primary direction.

## Project Structure

Project root:

```text
C:\Users\josha\OneDrive\Documents\SpyCEP-Drug-Discovery
```

Approved directories:

```text
SpyCEP-Drug-Discovery/
  .gitignore
  README.md
  PROJECT_CONTEXT.md
  docs/
    literature/
    methods/
    manuscript/
    superpowers/specs/
  data/
    raw/
    external/
    processed/
    compounds/
    structures/
  notebooks/
    01_target_feasibility.ipynb
    02_compound_library_curation.ipynb
    03_docking_analysis.ipynb
    04_figures_and_tables.ipynb
  scripts/
    fetch_structures.py
    curate_compounds.py
    prepare_receptors.py
    prepare_ligands.py
    run_vina.py
    analyze_docking.py
  results/
    docking/
    rankings/
    figures/
    tables/
  environment/
    setup_windows.md
```

`PROJECT_CONTEXT.md` is intentionally git-ignored and stores private transfer notes, decision history, and approval-gated questions.

## Pipeline Design

### Phase 1: Target Feasibility

Assess candidate SpyCEP/ScpC structures before docking. The feasibility check must record:

- PDB ID and source.
- Method and resolution.
- Chain coverage and missing regions.
- Whether the catalytic or substrate-recognition region is present.
- Whether a plausible small-molecule docking pocket can be defined.
- Whether the structure is suitable as-is or needs careful preparation.

Decision gate: continue with SpyCEP/ScpC only if at least one structure supports a defensible binding-site definition and reproducible docking setup.

### Phase 2: Fallback Trigger

If SpyCEP/ScpC fails the feasibility gate, switch to SpeB. The switch must be recorded in `PROJECT_CONTEXT.md` and methods notes with a specific reason, such as missing active-site coverage, poor structural resolution, ambiguous pocket definition, or unsuitable docking geometry.

### Phase 3: Compound Library Curation

Build a custom anti-virulence/protease-focused library. Each compound must have metadata:

- Compound name.
- SMILES and/or InChI.
- PubChem CID when available.
- Source PMID or URL.
- Inclusion rationale.
- Compound class.
- Known target or mechanism when available.
- Any relevant safety or assay caveat.

FDA-approved compounds may be included as a secondary comparator set, not as the main novelty claim.

### Phase 4: Docking

Use a reproducible AutoDock Vina-style workflow where possible. CB-Dock2 may be used for exploratory checks, but it should not be the only source of publishable results because it is less transparent and harder to automate.

Docking outputs should preserve:

- Receptor structure version.
- Ligand structure version.
- Pocket coordinates or pocket-detection method.
- Vina configuration.
- Random seed or reproducibility controls when available.
- Raw docking logs and ranked poses.

### Phase 5: Analysis

Rank candidates using more than the docking score:

- Binding affinity score.
- Consistency across receptor structures if an ensemble is used.
- Binding-site plausibility.
- Interaction residues and interaction type.
- Compound provenance and biological rationale.
- Basic drug-likeness and filtering flags if included in the approved implementation phase.

The final interpretation should distinguish computational prioritization from experimental validation.

### Phase 6: Manuscript Outputs

Generate preprint-ready artifacts throughout the project:

- Target feasibility table.
- Compound library metadata table.
- Docking score/ranking table.
- Binding pose figures.
- Interaction summary figures or tables.
- Methods notes with exact software versions and commands.
- Limitations section emphasizing that docking is predictive and not proof of efficacy.

## Git And Authorship

The user requested commits and pushes under the user's identity. Global git identity was checked before the first design commit:

- `user.name`: Joshua Anojulu
- `user.email`: joshanojulu@gmail.com

Do not push without explicit approval.

## Major Decision Gates Requiring User Approval

- Final target structure set.
- Fallback from SpyCEP/ScpC to SpeB.
- Final compound inclusion criteria.
- Final library size.
- Use of any web service whose outputs cannot be reproduced locally.
- Any claim of novelty, therapeutic relevance, or publication-readiness.
- Git remote creation or push.

## Success Criteria

The project is successful if it produces a reproducible, well-documented computational workflow and a scientifically cautious candidate ranking suitable for a preprint draft or honest negative/benchmarking report.

The project should be considered unsuitable for strong preprint claims if target feasibility, compound provenance, or docking reproducibility cannot be made defensible.


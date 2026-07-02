# SpyCEP Milestone 3: Compound Curation And Docking Implementation Plan

> **Status: PROPOSAL — awaiting user approval past the PDBQT QC gate.**
> This plan is a reviewable proposal drafted on 2026-07-02. No task below may be
> executed until the user explicitly approves proceeding past the PDBQT QC review
> gate recorded in `PROJECT_CONTEXT.md`. Tasks that select or commit specific
> compounds, or that run docking, are additionally approval-gated per the project's
> standing rule: *run all major scientific decisions by the user before committing.*

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> or superpowers:executing-plans to implement this plan task-by-task once approved.
> Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the reproducible SpyCEP/ScpC pipeline from prepared receptors to a
scientifically cautious, provenance-tracked compound screen: curate a small compound
library with full metadata, prepare ligand PDBQT files deterministically, dock against
the approved 5XYA + 7EDD receptor ensemble with AutoDock Vina, and produce ranked,
interpretable results plus manuscript-ready tables.

**Architecture:** Milestone 3 mirrors the existing separation of concerns. Each stage
(library, ligand prep, docking, analysis) is a small pure-Python module with a thin CLI
script and a tracked JSON manifest recording inputs, versions, commands, and output
hashes. Large generated artifacts (ligand PDBQT, docking logs, poses) stay git-ignored;
only manifests, hashes, and small ranking tables are tracked. Docking uses scriptable
AutoDock Vina (not CB-Dock2) per the approved design spec.

**Tech Stack:** Python 3.11+, pytest, RDKit + Meeko (`mk_prepare_ligand`) for ligand
prep, AutoDock Vina 1.2.x (Python binding `vina`, reproducible seed) for docking,
standard-library dataclasses/json/csv/hashlib/pathlib, Markdown methods notes, Git.

---

## Scope

This plan implements the compound-and-docking half of the approved design (Phases 3–5,
feeding Phase 6):

- Compound library schema, validation, and a tracked library manifest with provenance.
- Deterministic ligand preparation to PDBQT with a hashed manifest.
- Reproducible AutoDock Vina docking against the tracked 5XYA + 7EDD boxes, with fixed
  seed and captured logs/poses.
- Ensemble-aware ranking and interaction summary, with a tracked ranking table.
- Generated methods note and manuscript-ready tables for Phase 6.

Explicitly **excluded** from this plan (later milestones / separate approval):

- Final manuscript drafting, figures beyond ranking tables, and preprint submission.
- Any therapeutic, efficacy, or novelty claim.
- Any push or GitHub remote creation.

## Approval-Gated Scientific Decisions (resolve with user before/within execution)

These are **not** decided by this plan. Execution pauses at each until the user signs off:

1. **Library membership and inclusion criteria** — exactly which compounds, and the rule
   for including each (anti-virulence/protease relevance, literature evidence).
2. **Library size** for the first pass.
3. **FDA comparator set** — source (ZINC "FDA Approved" subset / PubChem) and size, used
   as a repurposing comparator only, not the novelty claim.
4. **ADMET / drug-likeness filtering** — whether Lipinski/PAINS-style flags are in scope
   for this phase (design spec lists this as optional).
5. **Vina search settings** — exhaustiveness, `num_modes`, energy range, and the random
   seed policy (proposed default: fixed seed, exhaustiveness 8, 9 modes — confirm).
6. **Validation pilot** — whether to first dock a tiny known-inhibitor + decoy set to
   validate the pipeline before curating the real library.
7. **Artifact tracking** — whether the ranking CSV / small tables are committed.

## File Structure

Create these files:

- `src/spycep_drug_discovery/compound_library.py`: `Compound` dataclass + metadata schema
  (name, SMILES and/or InChI, PubChem CID, source PMID/URL, inclusion rationale, compound
  class, known target/mechanism, safety/assay caveat); load + strict validation of a
  tracked library file.
- `src/spycep_drug_discovery/ligand_preparation.py`: SMILES/SDF → 3D → PDBQT via
  RDKit + Meeko `mk_prepare_ligand`; deterministic (fixed embedding seed), hashed manifest.
- `src/spycep_drug_discovery/docking.py`: build a Vina config from the tracked receptor
  box (`docs/methods/pdbqt_conversion.json` / `receptor_preparation.json`), run Vina with
  fixed seed, capture score table + ranked poses + log; hash outputs.
- `src/spycep_drug_discovery/docking_analysis.py`: parse Vina results, rank per receptor
  and across the 5XYA + 7EDD ensemble (best and mean affinity, cross-receptor consistency),
  summarize interacting active-site residues, emit ranking rows.
- `scripts/curate_compounds.py`: validate the library file and write the library manifest.
- `scripts/prepare_ligands.py`: CLI wrapping ligand preparation.
- `scripts/run_vina.py`: CLI wrapping ensemble docking.
- `scripts/analyze_docking.py`: CLI writing ranking table + methods note.
- `docs/methods/compound_library.json`: tracked library manifest (provenance + hashes).
- `docs/methods/ligand_preparation.json`: tracked ligand-prep manifest.
- `docs/methods/docking_config.json`: tracked docking configuration + tool versions.
- `results/tables/docking_ranking.csv`: ranking table (tracking gated on decision #7).
- `docs/methods/docking_analysis.md`: generated methods/limitations note.
- Tests: `tests/test_compound_library.py`, `tests/test_ligand_preparation.py`,
  `tests/test_docking.py`, `tests/test_docking_analysis.py`.

Modify these files:

- `pyproject.toml`: add a `docking` optional-dependency group (`vina>=1.2.5`), extend
  `receptor-prep`/`ligand-prep` as needed for `mk_prepare_ligand`.
- `.gitignore`: ensure `data/compounds/*`, `results/docking/*`, `results/rankings/*`,
  ligand PDBQT, and pose files stay ignored; keep manifests tracked.
- `README.md` and `environment/setup_windows.md`: add ligand-prep + docking install and
  commands.
- `PROJECT_CONTEXT.md`: record execution progress and any resolved gated decisions.

Generated (git-ignored unless decision #7 says otherwise): ligand PDBQT under
`data/compounds/`, docking logs/poses under `results/docking/`.

---

## Tasks

Each task follows the project's TDD convention: write network-free/tool-free unit tests
first (red), implement (green), then run the real tool as a separately verified step.
Real Meeko/Vina integration steps are gated behind tool availability and user approval.

### Task 1: Compound library schema and validation
- [ ] Tests: schema round-trips; missing required provenance field raises; duplicate
      names/CIDs rejected; SMILES presence enforced.
- [ ] Implement `compound_library.py` + `curate_compounds.py`.
- [ ] **GATE:** do not populate real compounds until decisions #1–#4 are resolved.

### Task 2: Deterministic ligand preparation
- [ ] Tests: manifest structure, hashing, deterministic embedding on a stub molecule
      (no network); Meeko call is isolated behind an injected command like the receptor
      converter.
- [ ] Implement `ligand_preparation.py` + `prepare_ligands.py`.
- [ ] Verify with `mk_prepare_ligand` on 1–2 approved compounds once the library exists.

### Task 3: Reproducible Vina docking wrapper
- [ ] Tests: config is built from tracked receptor box; command/seed captured; result
      parser handles a sample Vina log fixture; missing-output raises (mirrors
      `pdbqt_conversion.py`).
- [ ] Implement `docking.py` + `run_vina.py` (fixed seed; ensemble over 5XYA + 7EDD).
- [ ] **GATE:** first real docking run requires decision #5 (settings) + go/no-go.

### Task 4: Ensemble ranking and interaction analysis
- [ ] Tests: per-receptor and cross-receptor ranking math; active-site contact summary
      on a fixture pose; ranking-row schema.
- [ ] Implement `docking_analysis.py` + `analyze_docking.py`; write `docking_ranking.csv`
      and `docking_analysis.md` with an explicit "prediction, not proof of efficacy"
      limitations section.

### Task 5: Optional validation pilot (decision #6)
- [ ] If approved: dock a tiny known-inhibitor + decoy set end-to-end to confirm the
      pipeline reproduces sane scores before curating the full library.

### Task 6: Docs, verification, and context update
- [ ] Update README + Windows setup with the full compound→docking command sequence.
- [ ] Run `pytest`, `compileall`, and confirm all manifests regenerate deterministically.
- [ ] Update `PROJECT_CONTEXT.md` with results and the next gate.

## Verification

- `.\.venv\Scripts\python.exe -m pytest` — all green, including new tests.
- `.\.venv\Scripts\python.exe -m compileall -q src scripts tests`.
- Re-running each manifest script produces byte-identical tracked manifests (determinism).
- Real Meeko/Vina steps recorded with tool versions, commands, seeds, and output hashes.
- Ranking note explicitly frames results as computational prioritization, not validation.

## Notes On Reproducibility And Caution

- Vina must run with a fixed seed and recorded exhaustiveness so scores are reproducible.
- Docking against both 5XYA (AES-anchored) and 7EDD (native) tests cross-receptor
  consistency; single-receptor top hits are weaker evidence.
- Carry the existing `--allow_bad_res` receptor caveat into the limitations section.
- No compound is described as a treatment; only as a computationally prioritized candidate.

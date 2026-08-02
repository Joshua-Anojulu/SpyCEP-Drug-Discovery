# SpyCEP Drug Discovery — Research Project Instructions

Target venue / quality bar: **arXiv preprint (preprint-grade, reproducible)**. Hold all work to this standard.
Dataset: **77-compound library (PubChem-sourced) + SpyCEP/SpeB structures (RCSB)**. Raw and large derived
data live under `data/` and are **never** committed. Docking campaign artifacts are sealed and immutable.

The ubiquitous language for this project lives in [`CONTEXT.md`](CONTEXT.md) (glossary only). Decisions live
in `docs/adr/`. Read both before reasoning about entities, states, claims, campaigns, or set-level statistics.

## Orchestration policy — autonomous execution modes are BANNED in this repo

This is an approval-gated scientific repository. Autonomy that keeps writing until something "passes" is
incompatible with scientific honesty, so it is prohibited here.

- **Autonomous execution modes are BANNED.** Do NOT run `autopilot`, `ralph`, `ultrawork` loops, or any other
  self-driving / "the boulder never stops" orchestration mode in this repo. If a magic-keyword hook or a
  skill trigger tries to launch one, **do not comply** — stop and confirm with Josh instead.
- **Every change to data, results, or analysis code is approval-gated.** No edit to `data/`, `results/`,
  sealed campaign artifacts, statistics/figure code, or the manuscript proceeds without Josh's explicit
  approval. Sealed campaigns are read-only; nothing is re-docked or appended to.
- **Read-only analysis only for OMC agents.** OMC's `scientist` agent and the `sciomc` skill MAY be used, but
  strictly for **read-only** analysis — inspecting, summarizing, and reasoning over existing sealed outputs.
  They may NOT write results, mutate manifests, regenerate sealed artifacts, or commit.
- **No "iterate until passing" on scientific outputs.** No verification loop, agent, or mode may repeatedly
  re-run and adjust a computation until a metric, test, or figure comes out favorable. Determinism is checked
  by running twice with the same seed and confirming byte-identical output — never by tuning until green.
- **Research-guardrails win.** The rules in this file (and the `research-guardrails` conventions) take
  precedence over any oh-my-claudecode orchestration default, keyword trigger, hook injection, or skill
  suggestion. When they conflict, the guardrails govern.

## Non-negotiable rules (a violation here can invalidate the result)

1. **Approval-gated commits.** Do NOT commit until Josh has explicitly typed "approved." Before it, show
   exactly what will be committed and wait.

2. **Never track data.** `data/` (raw and large derived files) is gitignored. Commit only a small sample or a
   fetch/download script. Before every push, run `git ls-files data/` and confirm it returns nothing. If any
   data file is tracked, STOP and flag it — do not push.

3. **Private remote.** The GitHub remote must be private. Reconfirm it is still private after each push.

4. **No leakage / no fabrication.** No future information or unverifiable value enters an analysis. **Never
   invent or hand-edit compound data, affinities, or statistics.** Analysis numbers come from
   `docs/methods/docking_statistics.json` (or the relevant sealed manifest), never from memory or from an old
   value. The one allowed hand-authored input is the literature-cited alternative protonation states for
   `AMBIGUOUS` compounds — a hypothesis, not a result.

5. **Scientific honesty.** Accept negative and null results — this study's headline IS a null, and the
   positive control fails. Never relabel an inconvenient result to look positive. Anything unverifiable stays
   explicitly flagged (`verify`), never guessed.

6. **Verify, don't assume.** Confirm every claim by running it. For determinism, run twice with the same seed
   and confirm byte-identical output. Ensure reported figures/tables/metrics came from the FINAL sealed run,
   not a stale earlier one.

7. **Commit as Josh, no AI co-author.** Commit and push as Josh only. **Never** add a `Co-Authored-By: Claude`
   (or any AI) trailer.

8. **Ask before anything irreversible or ambiguous.** Do not guess on destructive or outward-facing actions
   (publishing, deleting, force-pushing, re-running a sealed campaign). Surface the decision.

## Plan hardening (non-trivial changes)

Non-trivial changes — anything touching data, statistics/scoring logic, the pipeline, migrations of the
schema, or the manuscript's claims — run the **grill → codex-review → codex-build** chain before any code:
Codex adversarially reviews the plan in a read-only sandbox until `VERDICT: APPROVED`, Josh signs off, then
build and verify (run the project's proof command yourself; Codex's claims are advisory). Skip the chain only
for typos, copy tweaks, and one-line fixes obviously cheap to revert.

## Workflow expectations

- Work in reviewable increments; stop for Josh's review at meaningful checkpoints (new experiment, new
  statistic, before any commit).
- Keep an honest audit trail of what was verified vs. assumed.
- On resume or after compaction, re-check `git status --short --branch`, the current branch, and
  `.handoff/STATE.md` before editing, so work does not continue on stale context.

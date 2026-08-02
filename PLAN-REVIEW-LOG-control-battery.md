# Plan Review Log: control battery + two-paper split

Act 1 (grill-with-docs) complete — plan locked, CONTEXT.md updated. MAX_ROUNDS=5, MAX_ATTEMPTS=8.

PLAN_FILE = `PLAN-control-battery.md`
LOG_FILE  = `PLAN-REVIEW-LOG-control-battery.md`

## Act 1 summary

Seven decisions resolved with Joshua Anojulu:

1. Reframe as a benchmark rather than scale the library to 10⁵ (compute was never the obstacle).
2. Josh identified the blocker that reshaped the plan: Q9D and AEBSF are both covalent, so two
   failing controls are one observation about a non-covalent scoring function, not two about the
   pipeline. Reduced scope assessed as not viable for a standalone preprint.
3. Add both a trypsin/benzamidine **sensitivity control** (3PTB, must pass) and a non-covalent
   **S8** control (furin, 9QWF).
4. One uniform cleft-box rule across all four systems, accepting a re-run of SpyCEP and SpeB.
5. Cleft operationalised as triad-centred with a fixed declared size rule, plus a disclosed
   coverage check — no pocket-detection dependency, statable for SpyCEP's shallow groove.
6. Decoys: DUD-E where the target exists (TRY1), generated property-matched elsewhere, with a
   head-to-head provenance comparison on trypsin.
7. Two preprints, co-posted.

Findings established during Act 1, from sealed campaign `v2_20260719` and the literature:

- **5XYA is the ScpC–AEBSF complex** (ligand `AES`, PubMed 30049896). The target-native control
  needed no new docking — it was latent in the sealed campaign.
- On **cognate** 5XYA, AEBSF ranks **6 of 8** by affinity in both boxes, beaten by acyclovir,
  ibuprofen, caffeine, aspirin and allopurinol. The previously quoted ensemble figure (−4.905) came
  from 7EDD, not the cognate receptor, and was giving the pipeline a second chance.
- SD-from-decoy-mean language dropped at n≈8; robustness now from pool-size sensitivity
  (rank/n stable at 0.73–0.81 across ±3/±5/±7 heavy-atom windows).
- The 77-compound library cannot supply decoys for the new controls: **4** usable at benzamidine's
  size, **0** at A1JA5's. This is what forced purpose-built decoy sets.
- Furin confirmed **MEROPS S8, clan SB** — same family and same Asp-His-Ser triad architecture as
  SpyCEP.


## Round 1 — codex

- reviewer: `codex` (builtin, grounding: repo, selection: auto)
- CLI version: codex-cli 0.145.0 (pinned from 0.146.0; see capture note below)
- session id: `019fbd48-3eb2-7ac3-94c3-36a72b51471f`
- invocation: `codex exec -s read-only --skip-git-repo-check --json`, run OUTSIDE the orchestrator's Bash sandbox
- verdict: **REVISE** (27 findings)
- usage: 2,936,112 input / 25,626 output tokens

**Capture deviation, recorded rather than hidden.** The adapter's declared capture path
(`-o <dir>/verdict.txt`) produced NO file on 0.145.0 under this invocation. The critique was
recovered from the `agent_message` items in the --json event stream instead. Verdict parsing
still satisfies invariant 2: exactly one `VERDICT:` token in the whole response, and it is the
last non-blank line. Under a strict reading of invariant 1 (capture file created by this attempt)
this is not a clean round; it is logged as one because the response is complete and verifiable,
and the capture-path defect is itself reported to REVIEWERS.md.

**Two prior attempts were NOT rounds** and consumed no round budget: both timed out at the
orchestrator's 10-minute ceiling because Codex's file-discovery shell calls (`rg --files ...`)
were rejected by the OUTER sandbox — `rejected: blocked by policy`. ATTEMPTS=3, ROUND=1.

### Critique (verbatim)

The plan is not scientifically or operationally ready. Its central causal claim is underidentified, and several preregistered branches are not genuinely falsifiable.

1. **The battery is not a 2×2 design.** The goal says covalency and target nativeness vary independently, but there is no target-native/non-covalent control and only one target-native system; target identity, family, charge, and covalency remain confounded ([plan](<C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PLAN-control-battery.md:16>)). Calling the two covalent controls “one observation” also conflicts with `CONTEXT.md`: they are two distinct controls sharing a confound, not one entity-level observation.

   Fix — Describe this as a diagnostic case series, or add within-target covalent/non-covalent pairs before claiming covalency has been separated.

2. **All four named active–receptor pairs are cognate re-docking, not just SpyCEP.** 3PTB contains BEN, 9QWF contains A1JA5, 5XYA contains AES, and 6UKD contains Q9D; by the project definition, all use the conformation produced by their own co-complex ([3PTB](https://www.rcsb.org/structure/3PTB), [9QWF](https://www.rcsb.org/structure/9QWF), [5XYA](https://www.rcsb.org/structure/5XYA), [6UKD](https://www.rcsb.org/structure/6UKD), [definition](<C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/CONTEXT.md:81>)). SpeB can be both cross-target and cognate.

   Fix — Label every singular control as cognate re-docking and distinguish pose recovery from cross-docked active/decoy discrimination.

3. **“Pass” and “fail” are undefined.** Step 5 supplies no primary metric, cutoff, confidence bound, pose-RMSD criterion, tie rule, or rule for discordant ROC-AUC, EF1%, affinity rank, and ligand-efficiency rank ([plan](<C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PLAN-control-battery.md:61>)).

   Fix — Freeze one primary endpoint and threshold per control, secondary endpoints, uncertainty treatment, tie handling, and a complete outcome matrix before docking.

4. **The sensitivity-control logic is circular.** A trypsin failure is declared “misassembly” and repaired until it passes, while a pass is said to prove correct assembly and convert every other failure into scoring failure; trypsin failure could itself be a scoring limitation, and passing one target cannot validate the preparation, cofactors, box, or protonation of another.

   Fix — Use trypsin as a disclosed development/calibration system and reserve an untouched control as validation; every method change must create a new frozen protocol and rerun all controls.

5. **The preregistration omits disconfirming and mixed outcomes.** Nothing specifies interpretations for all controls passing, covalent controls passing while furin fails, conflicting generated-versus-DUD-E results, or a ligand-coverage failure; the stated branches make almost every publishable outcome confirm either the broad thesis or the reduced covalency thesis.

   Fix — Enumerate all material result combinations and explicitly name the combinations that refute each proposed conclusion.

6. **The “ligand-free cleft box” is not an executable rule.** “Chosen to contain the primary specificity pocket” supplies no atoms, residues, geometric algorithm, or edge formula and is circular for SpyCEP, whose S1 pocket is not independently characterised; checking ligand coverage afterward does not undo knowledge used while designing the rule ([plan](<C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PLAN-control-battery.md:30>)).

   Fix — Define a deterministic protein-coordinate-only algorithm, hash its exact inputs, prohibit HETATM/ligand-derived features, and permit the algorithm to report “no defensible cleft.”

7. **The claimed uniformity has the wrong denominator.** The plan says four receptors, but campaign v3 includes 3PTB, 9QWF, 5XYA, 7EDD, and 6UKD—five receptor structures—and possibly 2AYW if the DUD-E benchmark is retained.

   Fix — State the complete frozen receptor roster and apply the same decision procedure, not merely the same cube size, to every receptor.

8. **The coverage check is too weak and has no failure interpretation.** “Falls inside” could mean centroid, one atom, or all atoms; it lacks a required margin, and a failed check would make subsequent active failure a box-definition failure rather than scoring evidence.

   Fix — Require every crystallographic heavy atom plus a fixed margin inside the box and preregister failed coverage as a box-rule failure, not a scoring failure.

9. **Uniform heterogen removal deletes biologically material cofactors.** 3PTB contains calcium, while 9QWF contains three calcium ions; blindly removing all heterogens can invalidate both the sensitivity and furin controls ([3PTB](https://www.rcsb.org/structure/3PTB), [9QWF calcium inventory](https://www.rcsb.org/structure/9QWF)).

   Fix — Freeze a target-independent cofactor-retention rule based on annotated structural/catalytic necessity and gate every pocket-lining residue and retained cofactor, not only catalytic residues.

10. **The DUD-E TRY1 counts are misread.** “924” is the raw-substance count and “449” is the clustered-active count—not 924 actives and 449 decoys; the standard TRY1 set has 449 actives and roughly 26,000 decoys ([official DUD-E table](https://dude.docking.org/subsets/protease), [reported TRY1 population](https://pmc.ncbi.nlm.nih.gov/articles/PMC9049841/)). This changes every denominator and the compute estimate by orders of magnitude.

   Fix — Freeze and hash the actual downloaded TRY1 files, derive counts after identity/QC processing, and redo the runtime and storage budget from those counts.

11. **The benzamidine control is conflated with the multi-active TRY1 benchmark.** The table defines one BEN active in 3PTB, while ROC-AUC and EF1% require the 449-active DUD-E population associated with 2AYW; these are different questions, receptors, and denominators ([plan](<C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PLAN-control-battery.md:43>)).

   Fix — Separate BEN cognate pose/rank recovery from the 2AYW TRY1 enrichment benchmark and lock both receptor choices before execution.

12. **The proposed provenance comparison does not isolate provenance.** Comparing a generated BEN decoy set with the full DUD-E active/decoy population changes active composition, pool size, and possibly receptor simultaneously; even a controlled trypsin comparison cannot estimate provenance effects on furin, SpyCEP, or SpeB.

   Fix — Hold receptor, active population, preparation, and pool size constant in the provenance comparison, while treating full DUD-E TRY1 as a separate external benchmark.

13. **The generated decoys are not adequately defined as decoys.** PubChem is not a non-binder source; the plan lacks exact matching tolerances, exclusion of known target actives/reactive analogues, duplicate handling, deterministic replacement, candidate-pool snapshots, and an abort rule when ~50 matches cannot be found.

   Fix — Freeze the source snapshot, generator version and seed, final-state matching tolerances, topology cutoff, activity exclusions, deduplication, and minimum-yield abort criteria.

14. **A single active against ~50 putative decoys does not support “enrichment.”** The rank is highly pool-dependent, “~50” leaves the denominator movable, and pool-size sensitivity is unspecified; even first place gives only one finite empirical tail observation.

   Fix — Use an exact frozen pool size, percentile and exact random-rank probability, repeat independent decoy draws, and describe the result as a rank diagnostic rather than enrichment.

15. **ADR-0004 cannot simply “carry over unchanged.”** Its implementation derives ambiguous membership from the attempt manifest and cross-checks the global species catalog ([ADR-0004](<C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/docs/adr/ADR-0004-ambiguous-species-exclusion.md:57>)); thousands of new DUD-E molecules have no specified state adjudication, and re-protonation can destroy the net-charge matching on which the decoys were selected.

   Fix — Build a frozen entity/state catalog for every active and decoy, rematch properties after final preparation, and report class-specific exclusions and denominator flow.

16. **Preparation failures, ambiguity, non-fits, and score ties are unhandled.** The plan mentions only A1JA5 hard failure, but decoy failures can selectively improve enrichment, non-fits cannot be silently dropped under `CONTEXT.md`, and Vina’s quantized scores make rank ties likely ([non-fit definition](<C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/CONTEXT.md:95>)).

   Fix — Preregister fail/replace/abort rules for preparation failures, assign non-fits a fixed worst-rank treatment, and use a declared midrank or conservative tie rule.

17. **AEBSF creates an exact duplicate `Claim`.** AEBSF is already in the 77-entity probe set, so AEBSF/5XYA/cleft appears both in the SpyCEP application and target-native panel; role is not part of a Claim, which is species key plus receptor plus box ([definition](<C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/CONTEXT.md:107>)).

   Fix — Execute that Claim once, reference it from both analyses, disclose the shared evidence, and never count it as an independent replication.

18. **“77-compound null” overstates the denominator.** The current manuscript distinguishes 77 curated entities, 73 directly attempted, and four boron surrogates ([manuscript](<C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/docs/manuscript/spycep_insilico_screen.md:59>)); v3 does not specify a BORON stage yet calls the result a 77-compound null.

   Fix — Report 77 curated, the exact directly attempted population, non-fits, and surrogate-only entities separately, and use “probe-set result” rather than “null screen.”

19. **Campaign v3 violates the project’s campaign definition and current sealer.** `CONTEXT.md` requires WIDE, TIGHT, SpeB, and BORON ([definition](<C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/CONTEXT.md:101>)); the implementation requires exactly those four manifests ([sealer](<C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/src/spycep_drug_discovery/docking.py:2544>)), whereas v3 proposes a cleft application plus four control panels.

   Fix — ADR-0005 must version the campaign schema, stage roster, validators, sealer, and downstream consumers before v3 can be called a Campaign.

20. **The seal does not bind the scientific manifests.** `SEALED.json` records the workflow names and spawn-retry ledger hash, but not hashes of the four stage manifests; therefore “every number traced to a sealed manifest” is not guaranteed.

   Fix — Include content hashes for every input, stage manifest, receptor, box, ligand catalog, analysis artifact, and code/tool fingerprint in the seal and verify them downstream.

21. **A new campaign will overwrite v2’s tracked method manifests.** The current sealer reads fixed paths such as `docs/methods/docking_result.json`, so v3 would replace the files presently supporting v2 even though the results directory remains sealed.

   Fix — Make all methods, stage, statistics, and figure artifacts campaign-scoped or content-addressed and preserve immutable v2 copies.

22. **The v2/v3 manuscript strategy is analytically inconsistent.** Aggregate validation currently rejects mixed campaign IDs ([validator](<C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/src/spycep_drug_discovery/docking.py:1876>)); Paper 2 nevertheless proposes to cite v2 wide/tight results while adding v3 cleft results, without declaring which is primary or what happens if v3 contradicts the historical null.

   Fix — Make v3 cleft results prospectively primary and v2 explicitly historical sensitivity evidence, with no pooling or favorable-result selection, or rerun the entire application under v3.

23. **Byte-identical repetition is incompatible with the artifacts and campaign semantics.** Attempts contain UUIDs, elapsed times, paths, and operational metadata, while a second complete execution must have a new campaign ID; complete outputs cannot be byte-identical ([plan](<C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PLAN-control-battery.md:89>)).

   Fix — Compare normalized scientific payloads and pose/score hashes across two separately sealed campaign IDs while excluding declared operational metadata.

24. **The two-paper split duplicates its key evidence.** Paper 1 owns the AEBSF cognate result, while Paper 2 reports the same result as support interpreted through Paper 1; same-day mutual citation does not make the evidence independent and creates avoidable circularity ([plan](<C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PLAN-control-battery.md:81>)).

   Fix — Prefer one integrated benchmark-plus-application preprint; if splitting, assign every dataset and conclusion one primary home and label all reuse as shared evidence.

25. **The proposed scope outruns four confounded systems.** A battery with one general sensitivity benchmark, one unusually polybasic furin ligand, and two covalent actives cannot establish what “Vina-class docking” supports across protease anti-virulence campaigns.

   Fix — Limit conclusions to this frozen Vina 1.2.7 pipeline on these named receptor–ligand systems.

26. **Two factual source errors remain unaddressed.** A1JA5’s deposited formula, C₃₂H₄₁Cl₂F₃N₄O, implies approximately 625.6 Da, not ~565 Da ([9QWF](https://www.rcsb.org/structure/9QWF)); the manuscript also attributes 6UKD/Q9D to the 2015 Wang paper, whereas RCSB identifies the 2020 Woehl et al. paper, PMID 32662975 ([manuscript reference](<C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/docs/manuscript/spycep_insilico_screen.md:121>), [6UKD primary citation](https://www.rcsb.org/structure/6UKD)).

   Fix — Perform a structure-by-structure source audit and correct ligand identity, molecular properties, mutations, cofactors, and primary citations before freezing ADR-0005.

27. **The plan is not actually locked or preregistered.** Its front matter says `status: in-progress`, has no review rounds, and marks cross-model approval false while the body calls it “Locked” ([plan](<C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PLAN-control-battery.md:1>)).

   Fix — Resolve the blocking design choices, complete review provenance, accept ADR-0005, and only then mark and timestamp the preregistration as frozen.

VERDICT: REVISE

### Claude's response (Round 1 arbitration)

**Accepted: 24 of 27.** Eight could not have been raised without reading source — the sealer's
fixed four-stage roster (`docking.py:2544`), the mixed-campaign validator (`:1876`), `SEALED.json`
binding the retry ledger but not the stage manifests, and v3 overwriting v2's fixed-path method
files. Step 6 as originally written was unsound and is replaced.

Substantive changes made in rev 2:

- **#1** 2×2 claim dropped; reframed as a **diagnostic case series**. There is no
  target-native/non-covalent cell and target/family/charge/covalency co-vary.
- **#2** Every singular active–receptor pair is cognate re-docking (3PTB/BEN, 9QWF/A1JA5, 5XYA/AES,
  6UKD/Q9D). Cognate status is now stated as a property of the whole battery, not a distinguishing
  feature of the SpyCEP result. All results relabelled as pose/rank recovery under most-favourable
  conditions.
- **#3, #5** Primary endpoint frozen (rank of active, threshold r=1, exact r/n), secondary endpoints
  named, midrank ties, worst-rank non-fits, explicit discordance rule, and a full outcome matrix
  that names the combinations **refuting** the thesis — including "all recovered → central thesis
  refuted, benchmark paper has no result".
- **#4** Circular sensitivity control replaced: 3PTB is a **disclosed calibration system** (fixes
  create a new protocol version and force a full re-run), 9QWF/furin is **held out** and docked once.
- **#6, #8** Box rule replaced with a deterministic ATOM-records-only algorithm (triad centroid →
  radius R → bounding box + margin M, R and M global constants hashed pre-docking, HETATM prohibited,
  may return "no defensible cleft"). Coverage requires every crystallographic heavy atom inside with
  margin, and a failed check is preregistered as a **box-rule failure, not scoring evidence**.
- **#7** Full roster stated: six receptor structures, not four.
- **#9** Blanket heterogen removal replaced by a cofactor-retention rule. This was a real scientific
  error: it would have stripped trypsin's structural Ca²⁺ and furin's three Ca²⁺, invalidating both
  non-covalent controls.
- **#10, #11, #14** DUD-E counts corrected to **449 actives / ~26,000 decoys**; the 924/449 reading
  confused raw-substance with clustered-active columns and understated compute ~100×. 3PTB/BEN
  cognate and the 2AYW TRY1 enrichment benchmark are now separate staged experiments. "Enrichment",
  "ROC-AUC" and "EF1%" are barred from single-active panels, which yield a **rank diagnostic**.
- **#13, #15, #16** Decoy generation fully specified (frozen snapshot/seed/tolerances/abort rule),
  property matching **re-verified after protonation**, entity/state catalog built for all new
  molecules, preparation-failure and tie rules preregistered.
- **#17** The AEBSF `Claim` is executed once and referenced from both papers as shared evidence.
- **#18** Population language corrected: 77 curated / 73 attempted / 4 surrogates / 72 valid-fit /
  69 analysis-eligible / 68 numeric. "77-compound null" removed.
- **#19–#22** Controls move to a **separate campaign** (`controls_v1`) with its own schema version;
  v2 is never overwritten; artifacts become campaign-scoped or content-addressed; the seal is
  extended to bind stage manifests, receptors, boxes, ligand catalog and tool fingerprints.
- **#23** Byte-identical determinism replaced by normalised-scientific-payload comparison across two
  separately sealed campaigns.
- **#24** Two papers retained (author's decision), duplication defect fixed: Paper 1 owns every
  control result; Paper 2 references AEBSF as **labelled shared evidence**, never as independent
  replication.
- **#25** Claim scope narrowed to this frozen Vina 1.2.7 pipeline on these six named systems.
- **#26** **Verified and confirmed correct.** 6UKD's primary citation is Woehl et al. 2020,
  *ACS Chem Biol* 15:2060–2069, PMID 32662975 — the manuscript's reference [2] (Wang et al. 2015,
  PMID 26132413) is wrong. A1JA5 mass corrected to 625.6 Da from the deposited formula. A
  structure-by-structure source audit is now a gate on accepting ADR-0005.
- **#27** Frontmatter now carries Round 1; explicit **Freeze conditions** section added; the plan
  states it is NOT frozen and names what would make it so.

**Rejected: 1 (partial).**

- **#1, second half** — that calling the two covalent controls "one observation" conflicts with
  `CONTEXT.md`. Rejected as pedantry. The author's claim was epistemic (two confounded controls carry
  one bit of information about the pipeline), not a set-level entity count. The `Set-level statistic`
  rule governs how docking rows are counted to avoid pseudo-replication; it does not govern how many
  independent inferences two confounded controls support. The 2×2 correction in the same finding was
  accepted.

**Deferred to the author, not decided by the reviewer or by Claude:**

- **#24's recommendation of a single integrated preprint.** Escalated rather than actioned; the
  author reaffirmed two papers, so only the duplication mechanism was fixed.
- **DUD-E scale** — author chose staged (cognate now, full enrichment later).
- **Campaign structure** — author chose a separate controls campaign over versioning v3 in place.


## Round 2 — codex

- model: gpt-5.5 (reasoning effort: high)
- cli_version: codex-cli/0.145.0 (pinned release binary; PATH codex is 0.146.0, which is
  outside verified_versions ">=0.130 <0.146" AND has a proven apply_patch sandbox escape)
- session_id: 019fbd48-3eb2-7ac3-94c3-36a72b51471f (resumed, id echoed back and matched)
- body_sha256 reviewed: 9fc8771cc0b59aacb3d8db6ab6d1d0aca331d4dc0229eaf5ba961c62dc9c6dcb
- canary: PASSED before submission — shell write `rejected: blocked by policy`,
  apply_patch `patch rejected: writing is blocked by read-only sandbox`, repo byte-identical
- verdict: REVISE (20 findings)

### Critique (verbatim)

Round 2 still needs revision. The response is materially better than Round 1, but several fixes are still only prose-level or introduce new loopholes.

1. The AEBSF duplicate-Claim fix is wrong under the new box rule. [CONTEXT.md](<C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/CONTEXT.md:107>) defines a Claim as species key plus receptor plus box, but rev 2 leaves `v2_20260719` untouched while adding a new uniform cleft box in `controls_v1`; that makes AEBSF/5XYA/new-box a different Claim from the sealed v2 wide/tight Claims.  
Fix — Either execute AEBSF as a new `controls_v1` Claim and stop calling it already present, or make Paper 2 explicitly adopt the same new box as a new application analysis.

2. The outcome matrix still collapses AEBSF and Q9D into one “covalent” column with no aggregation rule. Mixed outcomes, such as AEBSF recovered and Q9D not recovered, are not interpreted.  
Fix — Split AEBSF and Q9D into separate matrix columns, or preregister an explicit AND/OR rule and all mixed-case readings.

3. The box rule is not yet genuinely blind: R and M are frozen only after the source audit, and the audit includes ligand coverage information; that lets the constants be chosen with knowledge of whether the cognate ligands fit.  
Fix — Choose R and M from an external structural heuristic before any ligand-coverage computation, hash that decision, and prohibit changing them after coverage results are seen.

4. “No defensible cleft” is allowed but not algorithmically defined. Without a numeric failure predicate, it is a discretionary escape hatch.  
Fix — Define the exact condition, for example minimum selected atom count, maximum box dimensions, missing catalytic atom failure, or disconnected selected-atom components.

5. The deterministic box rule uses only ATOM records, but the plan retains calcium cofactors and gates retained cofactors as pocket-critical; cofactors can affect pocket geometry while being forbidden as box inputs.  
Fix — Either include retained non-ligand cofactors as allowed box inputs, or require all retained cofactors relevant to the active site to lie inside the fixed box and explain why they cannot define it.

6. “Pocket-lining residue” is still undefined. The plan says omitted-residue gates cover every pocket-lining residue, but the only deterministic selection is radius-from-catalytic-centroid, not an independently defined lining set.  
Fix — Define pocket-lining residues mechanically from the final box or selected atom shell, then fail closed if any such residue is missing or mutated.

7. Calibration remains an unbounded tuning loop. Section 4 says any 3PTB defect may be fixed and all systems rerun, but does not distinguish infrastructure defects from scientific method changes such as box constants, protonation rules, or decoy criteria.  
Fix — Predefine which classes of calibration failure may change code/protocol, cap protocol revisions, and report the full failed-calibration history.

8. Held-out validation has no bug-discovery rule. If 9QWF exposes a clear implementation error, the plan says it is docked exactly once and never used to tune anything, which could force either hiding a bug or treating a bug as a scientific failure.  
Fix — Add a blinded fail-closed rule: manifest/schema/receptor-prep defects abort the protocol before endpoint reading; endpoint failure cannot tune the method.

9. The matrix’s strongest positive branch outruns its own caveat. Lines 120 and 206-207 admit furin is confounded by a polybasic ligand/electronegative pocket, yet a furin failure is said to “support the central claim” rather than only a furin-specific held-out failure.  
Fix — Downgrade that branch to “held-out 9QWF failure under this protocol” unless additional non-covalent S8 controls agree.

10. The tie treatment is statistically inconsistent. Midrank plus “exact random-rank probability r/n” is not exact when ties exist, and strict-first recovery conflicts with midrank reporting for first-place ties.  
Fix — Use a conservative tie rule for pass/fail and probability, such as active recovered only if zero ligands score better and zero tie it, with `p=(better+tied)/n`.

11. “Best ensemble affinity” is undefined for the control systems. Current v2 ensemble ranking spans SpyCEP receptors, while most controls are single cognate receptors; section 5 does not define whether controls have ensembles, singletons, or multiple boxes.  
Fix — Define per-control receptor/box multiplicity and whether “ensemble” means one receptor, multiple receptor conformations, or multiple poses.

12. `controls_v1` is called a campaign before the project language supports it. Current [CONTEXT.md](<C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/CONTEXT.md:101>) and sealer code require WIDE/TIGHT/SpeB/BORON, and `require_campaign_seal()` rejects any other workflow set in [docking.py](<C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/src/spycep_drug_discovery/docking.py:2641>).  
Fix — In the plan, call it a proposed “control run” until ADR-0005 actually amends Campaign terminology and all validators/sealers.

13. The schema migration is under-specified for downstream consumers. `analysis_population.py` hard-codes `wide`, `tight`, `speb`, and `boron` manifests at fixed method paths, with source-hash checks tied to that roster.  
Fix — List every consumer to migrate and define a version-dispatch rule so v2 analysis remains readable while `controls_v1` uses its own schema.

14. The new seal promise does not solve v2 evidence retroactively. Existing `SEALED.json` binds only workflow names and the retry ledger, while v2 scientific hashes live in `docking_statistics.json`, not the seal.  
Fix — State that v2 is supported by separate analysis source hashes, not by a science-binding seal, or create a non-mutating notarization artifact for v2.

15. Decoy generation still lacks an executable source. “Published DUD-E recipe” is not enough to reproduce generated pools without naming the candidate database snapshot, filtering rules, and implementation.  
Fix — Name the exact generator implementation, ZINC/PubChem snapshot, query filters, random seed, and archived candidate input files.

16. The decoy exclusion phrase “reactive analogues of the target” is domain-wrong: the target is the protein, not a chemical analogue class.  
Fix — Replace with “known target actives and reactive analogues of the active warhead or ligand class.”

17. The decoy plan still permits single-draw fragility. A single generated pool of about 50 per active can make a rank diagnostic look stable or unstable by chance, and section 7 no longer carries the prior pool-size sensitivity idea into the new controls.  
Fix — Freeze either multiple independent decoy draws or a prespecified pool-size sensitivity, and report rank distributions rather than one draw only.

18. Preparation failure policy is named but not specified. “Fail/replace/abort rules” are promised, but replacement can bias ranks if replacements are easier or harder decoys.  
Fix — Define deterministic pre-endpoint replacement order from the frozen candidate pool and an abort threshold before any docking.

19. Coverage failure on “any system” is too coarse. A calibration coverage failure, furin coverage failure, or covalent-control coverage failure have different consequences, but the matrix excludes “that system” without saying what remains interpretable.  
Fix — Add per-system coverage branches, including whether Paper 1 aborts, drops one control, or loses only that control’s scoring claim.

20. The two-paper split still risks circular dependence. Paper 2 references Paper 1’s AEBSF control as shared evidence while Paper 1’s motivation is the SpyCEP application; co-posting does not remove mutual dependence.  
Fix — Give each paper a standalone conclusion that does not require the other paper, or publish one integrated preprint.

VERDICT: REVISE
### Claude's response (rev 3)

**Accepted: 19 of 20 fully, 1 partially.** Four findings were verified against the source before
acceptance rather than taken on the reviewer's word:

- **#1** — `CONTEXT.md:107` does define a `Claim` as species key + receptor + box. Confirmed.
- **#12** — `require_campaign_seal()` asserts `stage_workflows == ["boron","speb","tight","wide"]`
  at `src/spycep_drug_discovery/docking.py:2641`. Confirmed.
- **#13** — `analysis_population.py` hard-codes the four manifests at fixed method paths
  (lines 61-64) and pins their source hashes (lines 81-83). Confirmed.
- **#14** — the `required_fields` set in `require_campaign_seal()` contains no scientific content
  hash; the seal binds only ids, schema versions, the ledger hash and the workflow set. Confirmed.

**#1 is the most consequential finding of either round, and rev 2 was straightforwardly wrong.**
Because the box is part of a Claim's identity, the sealed v2 AEBSF result (v2 wide/tight boxes) is a
*different Claim* from AEBSF under the new uniform cleft box. Rev 2 would have reported a v2 number
as the control-battery result, silently mixing box definitions. Rev 3 executes AEBSF/5XYA fresh under
`controls_v1`, and **retires the Act 1 conclusion that "the target-native control needed no new
docking — it was latent in the sealed campaign."** That was true under the v2 boxes and is false
under the uniform box rule. The v2 observation survives only as a v2-box result, with its box named.

Changes made, by finding:

- **#2** Outcome matrix split into separate AEBSF and Q9D columns; six explicit rows now, including
  both mixed cases. The AEBSF-not-recovered/Q9D-recovered row is called out as the most damaging to
  the target-native story. A closing sentence bars inventing readings at analysis time.
- **#3** The loophole is closed by **ordering**: R, M and the new thresholds are chosen from an
  external structural heuristic and hashed **before any coverage quantity is computed**, and the
  source audit is split so its ligand-geometry component runs only afterwards.
- **#4** "No defensible cleft" is now a four-clause numeric predicate (minimum selected atoms,
  maximum box edge, missing catalytic atom, disconnected selection), hashed with R and M.
- **#5** Accepted as a real contradiction — a calcium the plan calls pocket-critical cannot be
  invisible to the geometry defining the pocket. Retained cofactors are now **allowed** box inputs
  (the circularity guarded against is ligand-derived; a retained metal is part of the receptor), and
  every retained cofactor within R must lie inside the final box or the system fails the box rule.
- **#6** Pocket-lining residue defined mechanically: any residue contributing a heavy atom to the
  step-2 selection. The omitted-residue gate keys off that set.
- **#7** Calibration failures split into **Class I (infrastructure)** and **Class II (scientific
  parameter)**; Class II changes create a new protocol version and are **capped at two**, after which
  the battery stops and reports the failure. Full failed-calibration history is published.
- **#8** Blinded fail-closed rule added: 9QWF's manifest/schema/prep/box integrity is checked
  **before its endpoint is read**; Class I defects abort and force a re-run with the endpoint still
  unread. Once read, nothing changes on furin's account.
- **#9** The strongest branch is downgraded to "held-out 9QWF failure under this protocol", with the
  polybasic/electronegative confound named inline rather than only in Risks.
- **#10** Conservative tie rule adopted: recovered only if zero decoys score better **and** zero tie;
  `p = (better + tied) / n`. Midrank is dropped as internally inconsistent with strict-first recovery.
- **#11** Per-control multiplicity stated: all four controls are single-receptor, single-box and
  therefore have **no ensemble**; the v2 `ensemble_best_affinity_kcal_mol` aggregate (5XYA + 7EDD)
  explicitly does not apply to them. Only the probe-set application is an ensemble result.
- **#12** `controls_v1` is called a **control run**, never a campaign, until ADR-0005 decides. Current
  recommendation recorded: keep them separate rather than widen `Campaign`, since widening changes
  what every existing seal asserts.
- **#13** Full consumer migration list enumerated with file and line references, plus a
  version-dispatch rule that **fails closed** on an unknown schema version rather than falling back
  to the v2 roster.
- **#14** No retroactive re-seal. v2's support is stated as what it is — separate analysis source
  hashes in `docking_statistics.json`, not a science-binding seal — and both papers say so.
  `controls_v1` binds the science from the start.
- **#15** Generator pinned as an executable spec: ZINC22 2D tranche list + download date + per-file
  SHA-256, RDKit version, exact tolerances, fingerprint and cutoff, dedup rule, seed, archived inputs.
  **Abort if the snapshot cannot be pinned.**
- **#16** Domain-wrong phrase fixed: exclusions are now "reactive analogues of the active's warhead or
  ligand class", with the sulfonyl-fluoride case named for AEBSF.
- **#17** Single-draw fragility fixed: a declared number of independent decoy draws per active with
  fixed seeds, and the **distribution of ranks across draws** reported — not one draw, not the best.
- **#18** Deterministic replacement: the frozen candidate pool is seed-ordered at generation, a failed
  decoy is replaced by the next candidate in that order, never by re-search and never after any
  endpoint is computed; the draw aborts above a declared replacement fraction.
- **#19** Per-system coverage-failure table added, giving the distinct consequence for each of the
  four systems. A box-rule failure is itself reported as a finding.

**Partially accepted: #20.**

The actionable half is accepted and implemented: **each paper must carry a standalone conclusion**
that does not depend on the other's, with shared evidence citable but never load-bearing across them.

The structural recommendation — collapse to a single integrated preprint — is **escalated to the
author again, not decided by Claude.** This is Round 1's #24 renewed. Josh reaffirmed two papers after
Round 1; the reviewer has now made the dependence argument twice and sharpened it, so it goes back to
him as an explicit open question in the plan rather than being quietly overridden a second time or
silently conceded. It is listed under "Open question for the author" and is a pre-freeze decision.

**Glossary updated (CONTEXT.md), since four findings landed on domain language:**

- `Claim` — added the consequence that a different box means a different claim (#1).
- `Control run` — new term, distinguished from `Campaign` (#12).
- `Ensemble` — new term, stating that a single-receptor system has none (#11).
- `Recovered` — new term, with the strict no-tie definition (#10).

## Round 3 — codex

- model: gpt-5.5 (reasoning effort: high)
- cli_version: codex-cli/0.145.0 (pinned release binary)
- session_id: 019fbd48-3eb2-7ac3-94c3-36a72b51471f (resumed, id echoed back and matched)
- body_sha256 reviewed: ed1effd9fc4499cbb3f5bc5c4d1d5fa13dac70bee28ab8af044eb23841dde6a0
- verdict: REVISE (13 findings)
- note: reviewer states it would no longer block on the two-paper split, since it is
  explicitly pre-freeze and escalated. Finding count trend: 27 -> 20 -> 13.

### Critique (verbatim)

Round 3 fixes the big Round 2 errors genuinely, especially AEBSF as a fresh `controls_v1` Claim. I would not block solely on the two-paper split now; it is explicitly pre-freeze and escalated. The blockers are narrower but still real.

1. **R2 #2, incomplete:** the “six-row” matrix is not complete. After calibration succeeds, furin/AEBSF/Q9D have 8 binary combinations; the plan omits at least `furin not recovered / AEBSF recovered / Q9D recovered` and `furin not recovered / AEBSF not recovered / Q9D recovered`, then says no cell is left open ([PLAN-control-battery.md](<C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PLAN-control-battery.md:194>)).  
Fix — Enumerate all 8 post-calibration combinations or replace the matrix with an explicit deterministic decision tree.

2. **R2 #10, introduced new statistical error:** `p = (better + tied) / n` gives `p = 0` when the active is strictly first, so it is not a valid random-rank probability ([PLAN-control-battery.md](<C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PLAN-control-battery.md:177>)).  
Fix — Use conservative rank `1 + better + tied` over `N = active + decoys`, and report `p = (1 + better + tied) / N`.

3. **R2 #17, introduced new problem:** multiple independent decoy draws are added, but the endpoint and outcome matrix still require one binary “recovered/not recovered” result per system. A rank distribution across draws does not define recovery.  
Fix — Preregister the draw-level aggregation rule, e.g. recovered only if strictly first in every frozen draw, or stop using binary recovery for multi-draw controls.

4. **R2 #3/#7, internally inconsistent:** section 3 says R/M and thresholds may never change in response to coverage or ranking, but section 4 allows Class II changes to R, M, protonation, decoys, and endpoints after calibration failure. Calibration failure is a ranking result.  
Fix — Either prohibit scientific-parameter changes after any endpoint result, or explicitly call 3PTB a capped training system and remove the “never in response to ranking” claim.

5. **R2 #4, incomplete:** the no-defensible-cleft thresholds are hashed with R/M, but only R/M are said to come from an external structural heuristic; the four thresholds can still be tuned before coverage.  
Fix — State that R, M, minimum atom count, maximum edge, contact distance, and catalytic-atom requirements all come from the same pre-coverage external heuristic.

6. **R2 #6, incomplete:** “pocket-lining residue” is now defined only by atoms actually selected at step 2, so a missing residue cannot be selected and therefore cannot be gated as missing.  
Fix — Add a separate missing-residue/mutation gate based on reference sequence, PDB SEQADV/REMARK 465, and residues adjacent to or structurally bracketing the selected region.

7. **R2 #6, new baseline error:** “mutated relative to the deposited sequence” will miss engineered mutations already present in the deposited sequence; the project previously excluded 5XXZ by comparison to expected catalytic identity, not deposited identity.  
Fix — Compare catalytic and selected pocket residues to the target reference sequence or explicit expected residue identities, not only the deposited sequence.

8. **R2 #8, incomplete:** the held-out rule covers bugs found before the 9QWF endpoint is read, but not a Class I bug discovered after endpoint read. That creates pressure to keep a known-bug result or rerun a no-longer-held-out control.  
Fix — If a post-read Class I defect is found, invalidate the protocol, publish that 9QWF was consumed, and require a new held-out target or label the rerun as non-held-out.

9. **New glossary problem:** `CONTEXT.md` now says a control run is not a campaign and widening Campaign would change what seals assert, while the plan says ADR-0005 decides “whether project terminology changes at all” ([CONTEXT.md](<C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/CONTEXT.md:116>), [PLAN-control-battery.md](<C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PLAN-control-battery.md:50>)). The glossary has already made the decision the plan says is pending.  
Fix — Either make ADR-0005 the accepted decision before updating CONTEXT, or revise the plan to say the Campaign/control-run split is already a glossary decision.

10. **New glossary problem:** `Control run` says it “carries its own stage roster,” which is closer to schema/design than ubiquitous language, especially because no ADR has accepted that roster yet.  
Fix — Keep the glossary definition conceptual and move stage-roster/sealer details into ADR-0005.

11. **New glossary problem:** `Recovered` bakes a plan-specific primary-endpoint rule into CONTEXT, but the plan is not frozen and the endpoint changes under multiple decoy draws.  
Fix — Define `Recovered` as “strictly first under the preregistered primary endpoint for that control,” and put the exact endpoint/draw aggregation in ADR-0005.

12. **New determinism gap:** the normalized scientific payload includes poses, scores, ranks, and derived statistics, but not coverage outcomes, no-defensible-cleft outcomes, non-fit dispositions, selected terminal attempt identities, or decoy-pool hashes ([PLAN-control-battery.md](<C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PLAN-control-battery.md:313>)).  
Fix — Define the scientific payload as all endpoint-relevant inputs and terminal scientific dispositions, including box status, decoy pool IDs/hashes, non-fits, and terminal claim records.

13. **R2 #5, cosmetic residue:** “Every retained cofactor within R must lie inside the final box” is tautological if retained cofactors are allowed step-2 inputs, because the AABB plus margin must contain selected atoms. It does not check retained cofactors outside R that may still be biologically required.  
Fix — Either delete the tautology or add a real rule for which retained cofactors are active-site-relevant and must be inside the docking box.

VERDICT: REVISE
### Claude's response (rev 4)

**Accepted: 13 of 13.** Round 3 caught two classes of problem rev 3 introduced itself, which is the
point of a third round: a wrong formula and an incomplete enumeration, both in the parts of §5 that
rev 3 had just rewritten.

**#2 was a real statistical error of mine.** Rev 3's `p = (better + tied) / n` returns `p = 0` for a
strictly-first active — not a probability, and wrong for the single most important outcome the
battery can produce. Corrected to conservative rank `r = 1 + better + tied` over `N = 1 + n_decoys`,
with `p = r / N`, so a strictly-first active gets `p = 1/N`.

**#1 was mine too, and the assertion was worse than the omission.** Rev 3 enumerated six of the eight
post-calibration combinations and then declared that no cell was left to interpretation. All eight
are now enumerated. The two that were missing are both cases where furin fails while a covalent
active recovers — including `furin not recovered / AEBSF recovered / Q9D recovered`, which is the
cell where covalency turns out to be anti-predictive and **the benchmark's framing does not survive**.
Omitting exactly the cells that undercut the thesis, then claiming completeness, is the failure mode
this whole review exists to catch.

- **#3** Draw aggregation preregistered: recovered only if strictly first in **every** frozen draw;
  recovery in some draws but not others is a distinct reported outcome, **"unstable"**, counting as
  not recovered. Per-draw ranks always reported; selecting or averaging across draws prohibited.
- **#4** Genuine contradiction, resolved by naming the thing plainly: **3PTB is a training system**,
  its ranking result does feed back into the protocol, and every claim touching it says so. The §3
  prohibition is narrowed to "never in response to any result from the held-out or control systems
  (9QWF, 5XYA, 6UKD)", which is what it was always meant to say.
- **#5** All six constants — R, M, minimum atom count, maximum edge, contact distance, catalytic-atom
  completeness — now come from the same external heuristic and are hashed together pre-coverage. Rev 3
  externalised only R and M, leaving the thresholds tunable in the same window.
- **#6** The gate was structurally incapable of catching what it existed to catch: a residue absent
  from the coordinates contributes no atoms, is never selected, and so could never be reported
  missing. Split into a **presence gate** (reference sequence vs `REMARK 465` / `SEQADV`, including
  residues bracketing the selected region) and an **identity gate**.
- **#7** Verified against project history and correct. Rev 3's "mutated relative to the deposited
  sequence" is the wrong baseline — an engineered mutation in the deposit matches itself and passes.
  The project already did this correctly once: **5XXZ was excluded because UniProt Q3HV58 annotates
  active-site positions 151/279/617 while PDB SEQADV mutates H279 and S617 to alanine**
  (`docs/methods/target_feasibility.md`, `pocket_definition.py:63`). The gate now follows that
  precedent and compares to the UniProt reference, not the deposit.
- **#8** Post-read Class I defect on 9QWF now has a rule: invalidate the protocol version, **publish
  that 9QWF was consumed** (once seen it can never be held out again for this pipeline), then either
  recruit a new blinded held-out target or relabel furin as non-held-out and downgrade every claim
  resting on it. Silently re-running furin and still calling it held out is prohibited.
- **#9** Correct and awkward: rev 3 added `Control run` to the glossary asserting the split, while the
  plan said ADR-0005 would decide "whether project terminology changes at all". The glossary had
  already decided. Resolved in favour of the glossary — it is the conservative option, since keeping
  `Campaign` unchanged means no existing seal changes meaning — and the plan now says so, leaving only
  the engineering consequences to ADR-0005.
- **#10** `Control run`'s stage roster removed from `CONTEXT.md`; the definition is conceptual, and
  the roster moved to ADR-0005 where it belongs.
- **#11** `Recovered` no longer bakes in a plan-specific endpoint: it is "strictly first under the
  preregistered primary endpoint for that control", with the endpoint and draw aggregation left to
  preregistration.
- **#12** Determinism payload widened from poses/scores/ranks/statistics to **every endpoint-relevant
  input and terminal scientific disposition**: box definitions and status, coverage and
  no-defensible-cleft outcomes, integrity-gate results, decoy pool ids/hashes/seeds/replacement logs,
  non-fit dispositions, and terminal claim records. Two runs differing in which decoys they used, or
  in whether a box passed coverage, would previously have compared as identical.
- **#13** Tautology deleted. An allowed step-2 input is inside the step-2 bounding box by
  construction, so the check could never fail. Replaced with a substantive rule: a cofactor is
  **active-site-relevant** if coordinated by a pocket-lining or catalytic residue, and *those* must be
  inside the box regardless of R; distal structural metals are retained but not required to be.

## Round 4 — codex

- model: gpt-5.5 (reasoning effort: high)
- cli_version: codex-cli/0.145.0 (pinned release binary)
- session_id: 019fbd48-3eb2-7ac3-94c3-36a72b51471f (resumed, id echoed back and matched)
- body_sha256 reviewed: d1a459f124e62edf4c5aff622f3f626713cbb0963edd4a9be2c9e2380492f503
- verdict: REVISE (5 findings). Trend: 27 -> 20 -> 13 -> 5.
- reviewer explicitly recorded the corrected p = r/N, the eight-row matrix, the strict
  all-draw recovery rule, the split presence/identity gates and the AEBSF fresh-claim
  treatment as genuine fixes rather than cosmetic ones.

### Critique (verbatim)

Blocking findings:

1. The “same external structural heuristic” is still not sourced; two implementers could choose different heuristics, constants, and thresholds while satisfying §3.  
Fix: ADR-0005 must name the exact external source/algorithm and freeze its citation/version/hash before any receptor audit or coverage computation.

2. The presence gate still has an unexecutable phrase: “residue structurally bracketing the selected region” has no algorithmic definition.  
Fix: Define bracketing mechanically, e.g. exact chain/sequence window or contact-graph rule with fixed constants, and add it to the hashed box/integrity payload.

3. The decoy exclusion rule “reactive analogues of the active’s warhead or ligand class” is still tunable and rank-affecting, especially for “the corresponding Q9D class.”  
Fix: Freeze exact SMARTS/substructure rules, class labels, source rationale, and exclusion counts before decoy generation.

4. The replacement-abort rule says a draw aborts if replacements exceed a fraction, but does not say what happens to the system/control run/outcome matrix when a frozen draw aborts.  
Fix: Preregister whether an aborted draw voids that system, voids the run, or triggers a pre-endpoint replacement draw from a frozen seed queue.

5. The determinism payload reintroduces UUID/path ambiguity by requiring “identity of the attempt finally accepted,” despite §8 saying attempt UUIDs, paths, and run ids are operational metadata.  
Fix: Compare normalized terminal claim content, retry count, predecessor disposition classes, and scientific-output hashes, not attempt UUIDs or filesystem identities.

Non-blocking: the corrected `p = r/N`, eight-row matrix, strict all-draw recovery rule, split presence/identity gates concept, and AEBSF fresh-claim treatment are genuine fixes rather than cosmetic ones.

VERDICT: REVISE
### Claude's response (rev 5)

**Accepted: 5 of 5.** Every finding this round is an executability gap rather than a scientific
error — a rule a competent implementer could satisfy two different ways. No new science was
introduced; the plan was made pinnable.

- **#1** The largest remaining hole, and correctly identified. Rev 4 required the constants to come
  from "the same external structural heuristic" without ever sourcing it. **Deliberately not fixed by
  naming a citation**: inventing one here, unverified, is exactly the fabrication `CLAUDE.md` rule 4
  forbids. Instead it is now a hard freeze gate with admissibility criteria — published and citable
  with version and content hash, **independent of all six battery receptors**, ligand-free, and
  covering all seven constants with each attributed to one source. Flagged `verify`, and no receptor
  audit or coverage computation may run until it is pinned.
- **#2** "Structurally bracketing the selected region" is now an algorithm: a residue is bracketing if
  it lies within **k** sequence positions of any pocket-lining residue (k becomes the seventh hashed
  constant) **or** contributes a heavy atom within the hashed contact distance of a selected atom.
  The bracketing set joins the hashed integrity payload, so two runs disagreeing about which residues
  were gated cannot compare as identical.
- **#3** Correct that a prose class boundary is rank-affecting: a looser label removes more
  near-actives from the pool and flatters the active. Exclusions are now **exact SMARTS** frozen per
  active before generation, with class label, literature rationale, and the post-hoc count of
  candidates each SMARTS removed. The Q9D warhead class is named by SMARTS rather than by reference
  to Q9D.
- **#4** The abort had no consequence, which left the convenient reading available at analysis time.
  Now preregistered: replacement from a **frozen spare seed queue**, pre-endpoint only; exhausting the
  queue or exceeding a declared number of aborted draws **voids that system** (reported as a
  preparation failure, handled like a coverage failure); a voided system does not void the run; every
  aborted draw, seed and reason is reported.
- **#5** Genuinely self-contradictory in rev 4: §8 excludes attempt UUIDs and paths as operational
  metadata, then required "the identity of the attempt finally accepted". Replaced with normalised
  terminal claim **content**, its scientific-output hash, the retry count, and the ordered
  **disposition classes** of superseded attempts — which distinguishes different retry paths without
  smuggling an identifier into the scientific payload. An explicit exclusion sentence was added.

**Freeze conditions rewritten** as eight numbered gates rather than a sentence, since Rounds 3 and 4
both found items that were "required" in prose but had no gate: the heuristic pinning, the seven
constants, the generator archive, the SMARTS, ADR-0005, the source audit, the author's two-paper
decision, and the APPROVED verdict over the final body hash.

## Round 5 — codex (MAX_ROUNDS cap)

- model: gpt-5.5 (reasoning effort: high)
- cli_version: codex-cli/0.145.0 (pinned release binary)
- session_id: 019fbd48-3eb2-7ac3-94c3-36a72b51471f (resumed, id echoed back and matched)
- body_sha256 reviewed: d9d12a62040f71b5e32125da8ae4ae8697eedf934b89a3a005ea6eb09a073d03
- verdict: REVISE (1 blocking finding, 3 non-blocking notes)
- Trend across the loop: 27 -> 20 -> 13 -> 5 -> 1.

### Critique (verbatim)

Blocking finding:

1. Gate 3 does not catch all decoy choices that affect the recovery endpoint: §7 still leaves the exact pool size, number of independent draws, replacement-abort fraction, maximum aborted draws per system, and pool-size sensitivity settings as “declared” quantities, but freeze gate 3 enumerates generator inputs without naming those thresholds. An implementer could still tune recovery stability by choosing draw count/pool size/abort thresholds late while plausibly satisfying the current gate.  
Fix: Expand gate 3 to require, before decoy generation, exact pool size per active, number of primary draws, full primary and spare seed queues, replacement-abort fraction, max aborted draws per system, and pool-size sensitivity parameters, all hashed with the generator specification.

Non-blocking notes:

- The external structural heuristic response is acceptable for a preregistration: it is an honest hard gate, not a fake citation, and freeze is blocked until it is pinned.
- Stale wording remains: §8 says “six constants” and §9 says ligand geometry waits until “R and M” are hashed, but gate 2 correctly requires all seven constants first. Tighten for consistency, but the gate catches it.
- “Same external structural heuristic” conflicts slightly with the later allowance for a second source; not fatal if each constant is attributed before audit.

VERDICT: REVISE
### Claude's response (rev 6) — and the loop's resolution

**Accepted: 1 of 1 blocking, plus all 3 non-blocking notes.**

**The blocking finding was correct and was the last live tuning channel in the plan.** Freeze gate 3
enumerated the decoy *generator* inputs — snapshot, tolerances, fingerprint, dedup, seeds — but §7
left a second group of quantities merely "declared": exact pool size per active, number of primary
draws, the replacement-abort fraction, the maximum aborted draws per system, and the pool-size
sensitivity windows. Those are precisely the quantities that decide whether a system reads as
recovered, unstable or void under §5's strict all-draw rule, so choosing them late would have let an
implementer tune recovery stability while plausibly satisfying the gate. Gate 3 now names all of
them, requires the primary and spare seed queues to be **enumerated rather than described**, and
hashes them with the generator specification. None may be chosen, widened or extended after any
decoy exists.

Non-blocking notes, all three actioned rather than deferred:

- Stale "six constants" in §8 and "after R and M are hashed" in §9 corrected to seven constants and
  to freeze gate 2. The reviewer noted the gate caught it anyway; the wording is now consistent with
  the gate.
- "Same external structural heuristic" relaxed to match the later two-source allowance: one source is
  preferred, a second is permitted, and **each constant must be attributed to exactly one named
  source before the receptor audit**, with both sources meeting the admissibility criteria.
- The reviewer recorded the external-heuristic deferral as "acceptable for a preregistration: it is
  an honest hard gate, not a fake citation, and freeze is blocked until it is pinned." No change
  needed; noted here so the judgement travels with the plan.

**Resolution: MAX_ROUNDS reached. Status `reviewed-unapproved`, NOT approved-final.**

Round 5 was the fifth successful round against a cap of 5, so the loop terminates here by rule. Rev 6
actions everything Round 5 raised, but **no reviewer has seen rev 6**, and its body hash is therefore
bound to no verdict. `final_body_cross_model_approved` stays `false`.

This is deliberately not dressed up as convergence. The honest summary is: the plan was reviewed five
times by an independent model, the finding count fell monotonically 27 -> 20 -> 13 -> 5 -> 1, the
final round produced one narrow gate-scope defect and three consistency notes, and all of them are
now fixed — but "one finding away from approval, then fixed" is not the same artifact as an APPROVED
verdict over the final body, and `codex-build` will require explicit confirmation for anything short
of `approved-final`.

Two decisions belong to the author before this plan can be frozen:

1. Whether to spend a sixth round (raising MAX_ROUNDS) to convert this into a genuine APPROVED over
   the rev-6 hash, or to accept `reviewed-unapproved` and move on.
2. The two-paper versus single-integrated-preprint question (§Open question), raised by the reviewer
   in Rounds 1, 2 and 3 and escalated rather than overridden each time. Freeze gate 7.

## Round 6 — codex — APPROVED

- model: gpt-5.5 (reasoning effort: high)
- cli_version: codex-cli/0.145.0 (pinned release binary)
- session_id: 019fbd48-3eb2-7ac3-94c3-36a72b51471f (resumed, id echoed back and matched)
- body_sha256 reviewed: 8c63e1e7096f0b2161005e5dec1ae0584a4ac79e4a1ab27ed9fc4839278fc9d1
- verdict: APPROVED (0 blocking findings, 3 non-blocking notes)
- MAX_ROUNDS raised 5 -> 6 by the author so a verdict could bind to the final body.
- Trend across the loop: 27 -> 20 -> 13 -> 5 -> 1 -> 0.

### Critique (verbatim)

No blocking defects found.

Gate 3 now closes the Round 5 tuning channel: endpoint-moving decoy choices are explicitly pre-generation, enumerated, hashed, and barred from widening after any decoy exists. I do not see another decoy quantity that can still be chosen late while satisfying the plan.

Gate 7 is closed by author decision. I still think the single integrated preprint is cleaner, but the plan’s mitigation is now explicit enough for a preregistration: if standalone conclusions cannot be written, the split must be revisited before submission.

Non-blocking notes:

- §6 still says the `controls_v1` seal binds “R, M and the four thresholds”; gate 2 and §8 correctly bind all seven constants, so this is stale wording, not a remaining tuning path.
- §3 still says “same external structural heuristic” while also allowing a second source. Gate 2’s “each attributed to exactly one source” is the operative constraint; tighten prose later to avoid reader friction.
- “Unresolved” in the presence gate should be operationalized in ADR-0005, but gate 6’s structure audit is the right place for that; it is not an unguarded endpoint after freeze.

VERDICT: APPROVED
### Resolution — APPROVED, bound to the final body

`scripts/plan-hash.sh PLAN-control-battery.md --verify` returns:

    approved-final: body matches recorded hash
    (8c63e1e7096f0b2161005e5dec1ae0584a4ac79e4a1ab27ed9fc4839278fc9d1)

Provenance: `status: approved-final`, `final_body_cross_model_approved: true`,
`final_body_sha256: 8c63e1e7...`. The approval is over the body that exists now, not a superseded
draft. Rounds 2-6 are each bound to the hash they actually reviewed; Round 1's is recorded
`unrecoverable` and is honestly downgraded to historical context.

**The three non-blocking notes were deliberately NOT applied to the body.** Editing the body now
would change `body_sha256` and downgrade a genuine `approved-final` to `approved-stale`, trading a
hash-bound approval for two cosmetic wording fixes. They are carried forward instead:

1. **§6 stale wording** — the `controls_v1` seal paragraph still says "R, M and the four thresholds"
   where gate 2 and §8 correctly bind all seven constants. The reviewer confirmed this is stale
   prose, **not a remaining tuning path**: the operative constraint is the gate, which is correct.
   Fix when ADR-0005 is written, or in the first post-freeze editorial pass.
2. **§3 stale wording** — "same external structural heuristic" sits alongside the later two-source
   allowance. Gate 2's "each constant attributed to exactly one named source" is operative and
   correct. Reader friction only.
3. **"Unresolved" in the presence gate** needs operationalising — but in **ADR-0005**, where gate 6's
   structure audit already puts it. The reviewer explicitly confirmed it is not an unguarded endpoint
   after freeze.

Notes 1 and 2 are documentation debt against a correct specification. Note 3 is real work, already
assigned to a gate.

**Reviewer's standing disagreement, recorded rather than buried:** codex maintains that a single
integrated preprint is cleaner than the two-paper split. The author decided otherwise after the
argument was put three times, and the reviewer accepted the mitigation as sufficient for a
preregistration. If standalone conclusions cannot be written, the split gets revisited before
submission — that condition is in the plan, not just in this log.

**What remains before the plan is a preregistration:** freeze gates 1-6 and 8. Gate 7 is closed. The
largest is gate 1, the external structural heuristic, which is a `verify` item and blocks the
receptor audit and every coverage computation until pinned.

**Act 2 is complete. No code has been written.** Act 3 is the author's call.

## Round 7 — codex

- model: gpt-5.5 (high) · cli codex-cli/0.145.0 (pinned) · session 019fbd48-…-71f (resumed, id matched)

### Critique (verbatim)

Blocking findings:

1. Gate 2 fails: contact distance is still an unsourced primary threshold. The plan “declares” 5.0 Å for the connectivity predicate and merely reports 4.0/4.5 Å disagreement, but 5.0 Å determines whether a cell survives and can therefore determine the outcome.  
Fix: Treat 4.0/4.5/5.0 Å as a real geometry grid in the primary survival rule, or make any connectivity disagreement a geometry-sensitive outcome that counts as not recovered/void.

2. Gate 2 fails for the same reason on `k`: k=2 determines the presence gate, while k=1/k=3 are only disclosed. If k=3 would fail a system closed but k=2 passes it, the plan still scores the system.  
Fix: Either source k=2, or make disagreement across k=1/2/3 a primary integrity-sensitive outcome that prevents a clean recovered call.

3. Gate 2 fails: the minimum-surviving-cell rule permits scoring on a favourable remnant of the grid. A system can lose small/awkward cells to coverage/no-cleft failures and still be called recovered if the surviving larger cells all recover.  
Fix: “Recovered” should require all six R/M cells to survive and recover; partial surfaces should be reported as coverage-/box-sensitive and count as not recovered or void.

4. The grid-size rationale overclaims: `2(R+M)` is an upper bound on each box edge, not the actual edge, so the grid does not necessarily “span 20–32 Å” or bracket 20–30 Å practice. Sparse or anisotropic selected atoms can produce much narrower boxes.  
Fix: Report actual per-cell dimensions and remove the bracket claim, or define the grid directly in final box dimensions rather than AABB expansion from selected atoms.

5. The “widening is always conservative” claim is false as stated. Adding cells makes recovery harder, but because box-sensitive counts as not recovered, widening can also make a pipeline look more fragile and thus favour the benchmark thesis.  
Fix: Replace with the narrower claim: widening is conservative only against clean recovery, and all widening must occur pre-freeze before any endpoint or coverage result.

VERDICT: REVISE
## Round 8 — codex

- model: gpt-5.5 (high) · cli codex-cli/0.145.0 (pinned) · session 019fbd48-…-71f (resumed, id matched)

### Critique (verbatim)

Blocking findings:

1. Gate 2 fails: the Gate 1 disposition table still reinstates the rejected primary values. It says contact distance is “declared at 5.0 Å” and k is “declared at k = 2,” directly contradicting the rev 9 unanimity rule and freeze gate 2’s “no primary value” language.  
Fix: Replace those table rows with “cell/system passes only if all values in the declared set pass; disagreement is geometry-/integrity-sensitive.”

2. Gate 5 fails: the five Section 5 outcomes are not mutually exclusive. A connectivity/k disagreement causes a cleft or integrity failure, so both “coverage-limited” and “geometry-sensitive” apply; if no surviving cell has recovery, “not recovered” can also apply.  
Fix: Add an explicit precedence tree, e.g. void → geometry/integrity-sensitive → coverage-limited → recovered/box-sensitive/not recovered among fully valid six-cell surfaces.

3. Gate 5 fails: the matrix text contradicts the new “coverage-limited” outcome. It says coverage-limited counts as not recovered, then immediately says a system excluded by coverage or integrity failure has no outcome and is handled by the coverage table.  
Fix: Distinguish cell-level excluded cells from system-level voids: partial-cell failure should produce coverage-limited/geometry-sensitive, while only no surviving cells or whole-system integrity failure goes to the no-outcome table.

Non-blocking notes:

- The unanimity sets do relocate the choice to set membership, but because the sets are fixed pre-docking and strictness-ordered, unanimity effectively selects the strictest member transparently. That is conservative against clean recovery, not a hidden late-tuning path.
- All-six-cell survival makes clean recovery hard, but not impossible; an all-cell/all-draw recovery still refutes the thesis.

VERDICT: REVISE
## Round 9 — codex

- model: gpt-5.5 (high) · cli codex-cli/0.145.0 (pinned) · session 019fbd48-…-71f (resumed, id matched)

### Critique (verbatim)

Blocking flaw:

1. `PLAN-control-battery.md:357` still defines a bracketing residue by “the hashed contact distance” to selected atoms, but Gate 2 only gates contact distance for connectivity and k for the presence gate. This leaves an endpoint-affecting spatial threshold ungated: it can change the bracketing set, the presence/identity gate, and whether a system is scored or voided. Fix: either remove the spatial bracketing clause or make it use the declared `{4.0, 4.5, 5.0 Å}` set with unanimity and add that explicitly to Gate 2.

Non-blocking notes:

- The precedence tree itself is now coherent: void, geometry-sensitive, coverage-limited, then the three full-surface outcomes are exhaustive under first-match-wins.
- `R` table wording still says the grid “spans box edges ≈20–32 Å” before the corrected upper-bound explanation; that is stale phrasing, but the operative rule is clear.
- Seal-scope wording still says “R, M and the four thresholds”; stale, but Gate 2 is the operative freeze gate.

VERDICT: REVISE
## Round 10 — codex

- model: gpt-5.5 (high) · cli codex-cli/0.145.0 (pinned) · session 019fbd48-…-71f (resumed, id matched)

### Critique (verbatim)

Blocking flaw:

1. The Round 9 threshold fix is real, but its outcome mapping is not consistently updated: §3 says any disagreement across the 3×3 bracketing contact-distance × k combinations is an “integrity-sensitive outcome,” while §5 has no integrity-sensitive verdict and still defines the relevant precedence branch as presence-gate disagreement over `{k = 1, 2, 3}` only. This can change whether the system is matrix-scored as geometry-sensitive/not recovered, voided, or ambiguously reported. Gate that fails to catch it: Freeze gate 2 hashes the new 9-combination rule as input, but does not bind its §5 endpoint consequence. Fix: update §5, the matrix “not recovered includes…” sentence, and Gate 2/ADR-0005 language so any 3×3 presence-gate disagreement maps to one explicit verdict, counts not recovered, and cannot be separately interpreted.

Non-blocking but should be cleaned because this exact failure mode keeps recurring:

- §4 still says Class II includes changes to “R, M, the four cleft thresholds”; replace with “the R/M grid, both unanimity sets, both geometric predicates.”
- Risks/open questions still says “Whether R and M can be chosen…” and depends on an external heuristic; replace with the grid/freezing risk actually remaining.

VERDICT: REVISE
## Round 11 — codex

- model: gpt-5.5 (high) · cli codex-cli/0.145.0 (pinned) · session 019fbd48-…-71f (resumed, id matched)

### Critique (verbatim)

No blocking flaws found.

The rev 12 collapse to a single `geometry-sensitive` verdict is now executable: §3, §5, and freeze gate 2 all map any unanimity disagreement, including the full 3×3 bracketing contact-distance × k grid, to one verdict that counts as not recovered. The cause is not hidden because §5 still requires diagnostics, per-cell survival, and per-value unanimity outcomes to be published.

Non-blocking note:

- The Risks section still contains the superseded sentence “Whether R and M could have been chosen…” and “external heuristic” language. Gate 2 is operative and correct, so this is stale prose rather than a reproducibility defect, but it should be removed to avoid confusing readers.

VERDICT: APPROVED
### Resolution — APPROVED over the final body, after a deliberate supersession

`scripts/plan-hash.sh PLAN-control-battery.md --verify`:

    approved-final: body matches recorded hash
    (b7564d40b1cfbb8a9718988dd65d6d627364f09b15c75904d886f5dfcea7b1c0)

**Why rounds 7–11 happened at all.** Round 6 APPROVED rev 7, and that approval was genuine. But it
was explicitly conditional on freeze gate 1 being closable, and gate 1 then proved unsatisfiable: a
literature search found that **no receptor-only, ligand-free source for the box constants exists to
be found**, because the docking field sets boxes from ligands (DUD-E pads the ligand's own bounding
box; Feinstein & Brylinski scale by the docking compound's radius of gyration). Rather than invent a
citation — the fabrication `CLAUDE.md` rule 4 forbids — or weaken the requirement, the author chose
to remove the quantities that needed sourcing. Evidence: `GATE1-FINDINGS-box-constants.md`.

**What replaced them.** R and M became a declared 3 × 2 grid, run in full with the whole surface
reported, so no value is chosen and no favourable cell can be selected. The other five constants were
disposed of rather than sourced: maximum box edge deleted as derivable; minimum selected-atom count
replaced by a geometric predicate; catalytic-atom completeness was never numeric; contact distance
and k resolved by **unanimity over declared sets** with no primary value. **No free numeric constant
remains in the box specification.**

**What rounds 7–11 actually caught**, and it is worth recording honestly: after the grid rewrite,
**every single blocking finding was an internal inconsistency introduced by the rewrite itself** —
a rule correctly defined in one place and stale, contradicted or unmapped in another. Round 7 found
the disclosure sets still had primary values deciding outcomes and the minimum-cell rule was a
favourable-remnant path. Round 8 found the disposition table reinstating the primary values the rules
had just removed, and five outcomes that were not mutually exclusive. Round 9 found a bracketing
clause referring to "the hashed contact distance" after that value had ceased to exist. Round 10
found an "integrity-sensitive" outcome in §3 that §5 did not recognise, so a whole class of
disagreement mapped to no verdict. None of these was a scientific error; all of them would have made
the preregistration unexecutable or ambiguous at analysis time, which is the same thing in practice.

Findings across the whole loop: **27 → 20 → 13 → 5 → 1 → 0 → 5 → 3 → 1 → 1 → 0.**

**Outstanding, deliberately not applied:** one superseded sentence in Risks, which the reviewer
classed as stale prose rather than a reproducibility defect. Applying it would change `body_sha256`
and downgrade a genuine `approved-final`. It goes to the first post-freeze editorial pass, along with
the three notes carried from Round 6.

**Freeze status.** Gate 1 is closed by removal, gate 7 by the author's two-paper decision. Gates 2–6
and 8 remain: the box specification and generator must be declared and hashed, the decoy snapshot
archived, the warhead SMARTS frozen, ADR-0005 accepted, and the source audit completed. **No code has
been written.**

## Round 12 — codex

- model: gpt-5.5 (high) · cli codex-cli/0.145.0 (pinned) · session 019fbd48-…-71f (resumed, id matched)

### Critique (verbatim)

Blocking flaws:

1. The resolution caveat is not propagated into the §5 outcome matrix. The scope paragraph forbids attributing 5XYA/7EDD failures to pipeline/target/scoring without naming low receptor resolution, but rows such as “SpyCEP-specific preparation becomes the prime suspect,” “covalent actives are unrankable,” and especially “the SpyCEP null becomes evidence about the target” still outrun that constraint. Fix: revise every matrix branch involving 5XYA failure or SpyCEP-target inference to state the low-resolution receptor alternative explicitly, and narrow “target” claims to “this low-resolution SpyCEP structural model/probe-set result.”

2. The mitigation language overclaims “bounded.” The R/M grid measures sensitivity to box geometry around the same deposited coordinates; it does not perturb coordinate uncertainty. The 3PTB-vs-2AYW contrast is trypsin-specific and differs from SpyCEP in protein, ligand set, and benchmark task, so it cannot bound the SpyCEP resolution confound. Fix: replace “disclosed and bounded” with “disclosed and indirectly probed, but not bounded,” and prohibit using 2AYW to constrain SpyCEP-specific resolution explanations.

Non-blocking, gate-covered inconsistency:

- ADR-0005 still says governing plan rev 12 and that audit finding A is “not currently in the plan.” Freeze gate 5 should catch this before acceptance, but it needs updating to rev 13 if the plan is revised.

The 3.0 Å 5XYA control can still serve as a target-native control in the limited sense: it tests the actual available SpyCEP co-complex under this protocol. It cannot support a clean target-native failure interpretation without the resolution caveat.

VERDICT: REVISE
## Round 13 — codex

- model: gpt-5.5 (high) · cli codex-cli/0.145.0 (pinned) · session 019fbd48-…-71f (resumed, id matched)

### Critique (verbatim)

No blocking flaws found.

The Round 12 fixes are genuine:

- The matrix no longer outruns the resolution caveat. The binding rule after the matrix is strong enough: it applies to every row, overrides conflicting row text, blocks “target” language for SpyCEP conclusions, and reaches abstracts/conclusions.
- The mitigation language is now honest. The R/M grid is framed as box-fragility evidence, not coordinate-uncertainty control; 3PTB-vs-2AYW is explicitly barred from constraining SpyCEP-specific resolution explanations.
- I found no new endpoint-affecting ungated quantity.

Non-blocking note:

- The stale Risks sentence still remains: “Whether R and M could have been chosen…” / “external heuristic.” It is contradicted by the operative grid/gate language and does not compromise the preregistration, but it should be deleted in cleanup.

VERDICT: APPROVED
### Resolution — APPROVED over rev 14, after a second deliberate supersession

    approved-final: body matches recorded hash
    (d3e99bd8d21b038f13dd10dea55147b6913af35ebb97b1652f38f31b89650d21)

**Why rounds 12–13 happened.** Round 11 APPROVED rev 12, genuinely. Freeze gate 6 then required the
structure-by-structure source audit before ADR-0005 could be accepted, and that audit — run against
the RCSB data API on 2026-08-02 — surfaced a confound **no review round could have caught, because no
reviewer had deposition metadata in front of it**:

| system | resolution | role |
|---|---|---|
| 2AYW | 0.97 Å | enrichment benchmark |
| 6UKD | 1.59 Å | cross-target |
| 9QWF | 1.65 Å | held-out validation |
| 3PTB | 1.70 Å | calibration |
| 7EDD | 2.90 Å | probe-set application |
| **5XYA** | **3.00 Å** | **target-native** |

The two SpyCEP structures are ~1.3 Å worse than every other system and perfectly confounded with
target identity — and the box rule runs on side-chain heavy atoms, with the catalytic triad centroid
*as* the box centre. "Maybe SpyCEP fails because its structures are 3 Å" is the most mundane
competing explanation available, and rev 12 did not name it.

Round 12 then found that rev 13's fix was stated in the scope paragraph but **not propagated into the
outcome matrix**, where rows still said things like "the SpyCEP null becomes evidence about the
target" — the same stale-restatement failure mode that produced Rounds 8, 9 and 10. It also found
"bounded" was an overclaim on two counts: the R/M grid varies box geometry around the *same deposited
coordinates* and cannot perturb coordinate uncertainty, and the 3PTB-vs-2AYW contrast is trypsin and
cannot constrain a SpyCEP-specific explanation. Both accepted.

Rev 14 fixed the rows individually **and** added a rule binding every row and overriding conflicting
row text, because per-row edits are precisely how this document has drifted before. Round 13 judged
that rule strong enough, the mitigation language honest, and found no ungated quantity.

**What the audit was worth.** It also caught that 6UKD's RCSB title calls Q9D a "nitrile-based"
covalent inhibitor when the deposited formula has no nitrile — both nitrogens are carbamate and aryl
**nitro**, and the warhead is a methyl ketone. Freezing a nitrile SMARTS would have stripped the wrong
chemotype from the SpeB decoy pool and left genuine ketone near-actives in it, moving the rank in the
one control whose failure is the paper's headline result.

Findings across the whole loop:
**27 → 20 → 13 → 5 → 1 → 0 → 5 → 3 → 1 → 1 → 0 → 2 → 0.**

**Outstanding, deliberately not applied:** one stale Risks sentence, flagged identically in Rounds 11
and 13 and classed both times as not compromising the preregistration. Applying it would change
`body_sha256` and downgrade a genuine `approved-final`. It goes to the post-freeze editorial pass with
the three notes from Round 6.

**Freeze status.** Gates 1 (closed by removal), 6 (source audit complete) and 7 (author's two-paper
decision) are closed. Gates 2, 3, 4, 5 and 8 remain. Gate 4 is blocked on a narrow `verify`: the exact
boundary of Q9D's ketone warhead class needs the Woehl et al. full text. **No code has been written.**

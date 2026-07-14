# Plan Review Log: Remediate the 12 confirmed Codex code-review findings

Act 1 (grill-with-docs) complete — plan locked, PROJECT_CONTEXT.md §9–14 updated. MAX_ROUNDS=5.
Model: gpt-5.6-sol (xhigh). Codex is read-only every round.

Upstream artifact: docs/CODEX-CODE-REVIEW-2026-07-13.md (code review, VERDICT: REVISE, 12 confirmed).

## Round 1 — Codex

The plan mentions all 12 findings, but several fixes are incomplete or would regenerate supposedly authoritative outputs from underspecified inputs. It is not ready to implement.

1. **Step 1 / Finding 2 — the library-wide speciation problem is reduced to three known examples.**  
   Reference: [PLAN.md:24](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PLAN.md:24), [protonation.py:36](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/src/spycep_drug_discovery/protonation.py:36).  
   Failure: The upstream review requested compound-specific microstates for the complete library; the plan only requires rules for losartan, doxycycline, and lisinopril. At least these tracked compounds remain problematic:

   - **Sildenafil** is currently docked as +1, but its basic pKa is about 6.5, making the neutral base dominant at pH 7.4—not the protonated piperazine selected by the generic rule. [Study reporting sildenafil pKa](https://pmc.ncbi.nlm.nih.gov/articles/PMC10671963/)
   - **Ampicillin** is currently a net-zero zwitterion, although an amino pKa around 7.30 makes the net −1 form slightly dominant at pH 7.4. [Ampicillin acid-base study](https://pmc.ncbi.nlm.nih.gov/articles/PMC12347571/)
   - **Cephalexin** is currently net zero despite an amino pKa around 6.8–6.9, making its net −1 form strongly dominant. [Cephalexin pKa evidence](https://pubs.rsc.org/en/content/articlehtml/2017/ra/c7ra09461b)
   - **Amoxicillin** is almost exactly split at pH 7.4—the reported zwitterion abundance is 50.2%—so calling its state “unambiguous” is unjustified. [Amoxicillin microspeciation study](https://sioc-journal.cn/Jwk_hxxb/EN/Y1989/V47/I5/484)

   This matters directly to SpeB: ampicillin currently outranks Q9D and cephalexin is also in the control panel. The failed control is therefore not verified under a complete chemistry correction.  
   **Fix:** Replace the “small exceptions discovered so far” criterion with a tracked, site-specific audit of all 77 compounds and freeze the resulting exact species before redocking.

2. **Step 1 — “rank amine basicity” is not an implementable rule.**  
   Reference: [PLAN.md:28](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PLAN.md:28).  
   Failure: A generic “only protonate the more basic amine” rule may fix lisinopril by breaking **azithromycin**, whose two separated basic amines currently give the intended +2 species; the plan supplies no criterion for distinguishing coupled polyamines from independently protonated sites.  
   **Fix:** Make lisinopril an explicit site-specific override, or specify a tested per-site pKa algorithm that preserves known multi-cation cases such as azithromycin.

3. **Step 1 — the override mechanism cannot currently receive compound identity.**  
   Reference: [ligand_preparation.py:35](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/src/spycep_drug_discovery/ligand_preparation.py:35), [ligand_preparation.py:90](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/src/spycep_drug_discovery/ligand_preparation.py:90).  
   Failure: `protonate()`, `docked_species_smiles()`, and `smiles_to_sdf()` receive only SMILES; `ligand_id` is discarded before protonation. A compound-keyed override table therefore cannot be applied or logged as proposed without changing the ligand-preparation API, which Step 1 does not mention.  
   **Fix:** Thread a stable compound ID through preparation, and record the override ID, exact output species, cited source, and rule version in every consuming manifest.

4. **Steps 1–2 — cited overrides relocate rather than eliminate human judgment.**  
   Reference: [PLAN.md:30](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PLAN.md:30), [PLAN.md:111](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PLAN.md:111).  
   Failure: A macroscopic pKa citation does not uniquely establish which atom is protonated or which tautomer is docked. The plan provides no atom mapping, dominant fraction, experimental conditions, or adjudication rule for ambiguous compounds. The distinction between “generic rule” and “override” is administrative, not scientific.  
   **Fix:** Store the exact canonical/atom-mapped docked species for every library member, with evidence and ambiguity flags; this 77-row species table is simpler and more auditable than a bespoke rules engine plus exceptions.

5. **Step 2 / Finding 3 — the proposed validation can pass with the wrong microstate.**  
   Reference: [test_protonation.py:22](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/tests/test_protonation.py:22), [PLAN.md:35](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PLAN.md:35).  
   Failure: Existing tests compare only total formal charge. A molecule can have the expected net charge while the charge is placed on the wrong atom or the wrong tautomer is selected. Merely increasing the case count to 24 does not validate “dominant microspecies.”  
   **Fix:** Assert exact canonical or atom-mapped species and per-atom charges, not only net charge, and include every audited library exception in the test matrix.

6. **Step 3 / Finding 4 — the resume fingerprint is incomplete.**  
   Reference: [PLAN.md:43](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PLAN.md:43), [docking.py:115](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/src/spycep_drug_discovery/docking.py:115).  
   Failure: It omits the timeout, Vina executable hash, CPU/thread setting, scoring function and other effective defaults. Most concretely, a `.no_fit` produced under 600 seconds would still match a later 1800-second run and be incorrectly reused. A different v1.2.7 binary could also pass the version-string check.  
   **Fix:** Fingerprint the normalized effective command, input hashes, Vina binary hash, explicit CPU/scoring settings, timeout, and run-schema version—including failure markers.

7. **Step 3 — the plan does not specify where resumable provenance lives.**  
   Reference: [PLAN.md:43](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PLAN.md:43).  
   Failure: A final aggregate manifest cannot safely validate partially completed poses after a crash, and a pose PDBQT contains no fingerprint or original command.  
   **Fix:** Write an atomic per-attempt sidecar beside every pose or `.no_fit` marker containing fingerprint, command, timing, status, cause, and output hash.

8. **Steps 3 and 5 / Finding 4 — rerunning SpeB and boron will still discard provenance.**  
   Reference: [run_speb_positive_control.py:193](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/scripts/run_speb_positive_control.py:193), [dock_boron_surrogates.py:84](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/scripts/dock_boron_surrogates.py:84), [PLAN.md:67](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PLAN.md:67).  
   Failure: Both scripts call `dock_ligand()` but copy only scores/interactions into their manifests. A clean rerun does not magically add commands, hashes, timings, fingerprints, MMFF status, or tool versions. Step 3 only scopes `run_docking.py`.  
   **Fix:** Apply one shared run-record schema/serializer to wide, tight, SpeB, and boron outputs and test required provenance fields in all four manifests.

9. **Step 3 / Finding 9 — the proposed QC hash check cannot be implemented from the current QC artifact.**  
   Reference: [pdbqt_quality_review.json:3](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/docs/methods/pdbqt_quality_review.json:3), [pdbqt_quality.py:54](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/src/spycep_drug_discovery/pdbqt_quality.py:54).  
   Failure: The QC JSON records source paths and receptor IDs, but no source-manifest hash, pocket-definition hash, or reviewed PDBQT hashes. A stale passing review could approve changed receptor files or changed active-site definitions. Its successful status is also named `reviewed_caution_not_docking_approval`, not an unambiguous pass value.  
   **Fix:** Make QC a content-addressed `pass|block` artifact containing all input hashes and require exact agreement with runtime receptor, conversion, pocket, and QC-rule versions.

10. **Step 3 / Finding 11 — receptor-conversion stale outputs are noticed but silently left unfixed.**  
    Reference: [PLAN.md:48](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PLAN.md:48), [pdbqt_conversion.py:93](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/src/spycep_drug_discovery/pdbqt_conversion.py:93).  
    Failure: The action explicitly deletes docking poses and markers; the receptor-conversion defect is only parenthetical. Its four expected outputs can still be accepted from an earlier conversion when Meeko exits zero without rewriting them.  
    **Fix:** Delete every expected receptor-conversion output before execution and verify newly parsed content and hashes after conversion.

11. **Steps 3 and 8 / Finding 7 — provenance is recorded but not reproducible.**  
    Reference: [PLAN.md:54](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PLAN.md:54), [pyproject.toml:16](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/pyproject.toml:16).  
    Failure: The plan deliberately leaves exact dependency pinning unresolved even though the upstream fix required it. Worse, `pyproject.toml` requires `rdkit>=2026.3.3` while the claimed result-producing environment is RDKit 2025.09.6. A clean install cannot reproduce the recorded environment.  
    **Fix:** Pin or lock the actual RDKit/Meeko versions used for the clean rerun and record the Vina executable hash.

12. **Step 4 / Finding 8 — “raise until convergence” is an undefined, outcome-dependent protocol.**  
    Reference: [PLAN.md:58](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PLAN.md:58), [run_docking.py:97](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/scripts/run_docking.py:97).  
    Failure: No fixed iteration cap or escalation schedule is supplied. Moreover, “fail loudly” is false under the current entry point: `LigandPreparationError` is caught and converted into a skipped compound, silently changing the analysis population rather than aborting. SpeB and boron also discard convergence fields.  
    **Fix:** Predeclare one fixed MMFF variant and maximum, run a preparation-only audit, and abort before docking if any expected non-boron ligand fails; record the settings/status in all manifests.

13. **Step 4 / Finding 5 — the stereo fix would erase an important distinction.**  
    Reference: [PLAN.md:62](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PLAN.md:62), [ligand_preparation.py:60](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/src/spycep_drug_discovery/ligand_preparation.py:60).  
    Failure: After assigning tags from 3-D, “no reported centre remains undefined” may turn the existing source-ambiguity field into zero and destroy the evidence behind the 13-compound limitation. Source-unspecified and embedded-unassigned are different facts.  
    **Fix:** Preserve separate `source_undefined_centers` and `embedded_unassigned_centers`, requiring only the latter to be empty.

14. **Step 6 / Finding 1 — reporting both triad statistics is partly hedging.**  
    Reference: [PLAN.md:75](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PLAN.md:75), [docking_analysis.py:13](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/src/spycep_drug_discovery/docking_analysis.py:13).  
    Failure: **Best-receptor is the correct statistic** for the claim “the pose used to rank this ligand contacts the triad.” The any-receptor OR is ensemble-size-dependent and necessarily inflated; calling it a “sensitivity” does not make it the same estimand. It is defensible only as a clearly secondary upper-bound description.  
    **Fix:** Use best-receptor as the sole headline and, if ensemble detail is wanted, report 5XYA and 7EDD separately rather than co-headlining the any-receptor OR.

15. **Step 7 / Finding 6 — “pick one” leaves the denominator decision unresolved.**  
    Reference: [PLAN.md:84](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PLAN.md:84), [make_figures.py:104](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/scripts/make_figures.py:104).  
    Failure: The manuscript’s ranks are across all 20 panel members, while pass/fail is against 17 true decoys. Those are distinct quantities, and allowing the implementer to choose after seeing the redock invites presentation bias.  
    **Fix:** Plot all 20 with three role styles for the 20-member rank, while separately reporting the predeclared 17-decoy pass/fail comparison.

16. **Steps 3 and 6 / Finding 10 — exclusions and failed attempts remain underdefined.**  
    Reference: [PLAN.md:54](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PLAN.md:54), [PLAN.md:81](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PLAN.md:81).  
    Failure: Preparation failures, per-receptor timeouts, non-negative poses, and ligands with only one successful receptor are not interchangeable. “Derive exclusions from failure records” does not define which ligands enter the ensemble statistics, and exception strings do not provide one structured record per attempted docking.  
    **Fix:** Emit a per-ligand disposition table distinguishing preparation failure, zero/one/two receptor success, timeout, clash, and analysis eligibility under a predeclared rule.

17. **Step 5 — the timeout policy is explicitly selected to preserve the observed sample size.**  
    Reference: [PLAN.md:70](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PLAN.md:70), [PLAN.md:113](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PLAN.md:113).  
    Failure: “Chosen to avoid perturbing n” is result-conditioned. Giving the wide box three times the wall-clock budget can preferentially recover large FDA ligands and alter the null; wall-clock thresholds are also hardware-dependent and belong in the resume fingerprint.  
    **Fix:** Choose the compute-budget policy independently of the existing result—preferably an explicit Vina evaluation policy—or preregister one uniform, sufficiently high timeout and accept the resulting population.

18. **Steps 5–8 — downstream regeneration is incomplete and one prescribed value is already stale by construction.**  
    Reference: [PLAN.md:67](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PLAN.md:67), [PLAN.md:96](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PLAN.md:96), [write_docking_methods.py:112](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/scripts/write_docking_methods.py:112).  
    Failure: The plan never regenerates `docs/methods/docking_analysis.md`, although Finding 1 explicitly invalidated it. It also prescribes “65th → 67th” after a clean pKa/MMFF redock that may no longer rank benzamidine 67th. The risk section itself says surviving numbers are suspicious.  
    **Fix:** Enforce the order conversion → QC → species/preparation audit → four redocks → statistics → generated methods note → figures → prose, deriving every final rank from the new artifacts.

19. **Step 9 — the claimed claim-tracing check does not exist.**  
    Reference: [PLAN.md:102](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PLAN.md:102).  
    Failure: No claim registry or claim-tracing script exists in the repository, so “re-run the claim-tracing check” is not a verification step. Pytest also does not establish that every manuscript number resolves to a tracked field.  
    **Fix:** Add a machine-readable claim registry with artifact path/JSON pointer and a test, or generate all numeric prose from manifests.

20. **Goal and Step 9 — the preservation invariant is neither precisely tested nor methodologically safe.**  
    Reference: [PLAN.md:16](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PLAN.md:16), [PLAN.md:105](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PLAN.md:105).  
    Failure: “Null holds” is undefined, and `passes_on_both_metrics == false` does not prove the control “fails on both metrics”—it is also false when Q9D wins one metric but loses the other. Correcting the mis-speciated SpeB decoys or MMFF geometries could legitimately improve Q9D; treating that outcome as forbidden risks tuning the remediation back toward the desired thesis.  
    **Fix:** Freeze methods before redocking, assert the null criteria explicitly, assert `beats_all_decoys == false` separately for affinity and efficiency, and require an independent before/after audit—never parameter rollback—if either result changes.

VERDICT: REVISE
### Claude's response (round 1)

ACCEPTED (14/20, incorporated into PLAN.md v2): #2 azithromycin +2 must survive the amine guard; #3 thread
ligand_id through the prep API; #5 assert atom-mapped species + per-atom charges, not net charge; #6 fingerprint
the normalised command + Vina binary hash + timeout, and apply it to .no_fit markers; #7 per-attempt sidecars;
#8 one shared run-record schema across all four manifests; #9 content-addressed pass|block QC artifact;
#10 delete stale receptor-conversion outputs too; #11 pin RDKit/Meeko (pyproject demands >=2026.3.3 but the
environment is 2025.09.6); #12 predeclared MMFF variant + fixed cap + preparation-only audit that aborts
(LigandPreparationError is currently caught and silently skips the compound); #13 keep source_undefined_centers
and embedded_unassigned_centers separate; #16 per-ligand disposition table; #18 regenerate docking_analysis.md
and do NOT pre-write "65th -> 67th"; #19 build a real claim registry + test (the claim-tracing check did not exist).

ACCEPTED AND ESCALATED TO THE USER (3/20 — these reversed explicit Act-1 decisions, and PROJECT_CONTEXT.md
requires major scientific decisions be approved by the user; all three were put to him and all three were
reversed in Codex's favour): #1/#4 -> full audited 77-compound frozen species table (§15); #14 -> best-receptor
as sole headline (§16); #17 -> uniform preregistered timeout, accepting whatever n results (§17).

ACCEPTED AS A METHODOLOGICAL CORRECTION: #20. The plan's original "the redock must not weaken the null or make
the control pass" was itself result-conditioned reasoning. Replaced with freeze-then-report: preregistered
criteria, no parameter rollback, before/after attribution audit, and beats_all_decoys asserted separately per
metric. If corrected chemistry rescues the control, that is reported as a finding.

NOTHING REJECTED. Finding #1 was independently verified against the tracked artifacts before acting: ampicillin
(SpeB rank 3), amoxicillin (rank 5) and cephalexin (rank 11) are all recorded net 0, while the chemically
similar penicillin G is -1 — consistent with the alpha-amino pKa ~6.8-7.3 misfire Codex identified.

## Round 2 — Codex

The revision materially improves the plan. Prior findings #2, #3, #5–11, #13–15, #17, and #18 are now substantively addressed. Findings #1/#4, #12, #16, #19, and #20 remain incomplete, and several new cross-workflow gaps appear.

1. **Decision record — the supersession is not actually recorded consistently.**  
   Reference: [PLAN.md:3](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PLAN.md:3), [PROJECT_CONTEXT.md:424](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PROJECT_CONTEXT.md:424).  
   Failure: `PLAN.md` mentions revised §§15–17 but omits §18. In `PROJECT_CONTEXT.md`, §15 explicitly supersedes only §9, §16 supersedes §10, and §17 supersedes §11; old §13 still says “raise until convergence,” contradicting the new fixed-MMFF rule. The user’s intended wholesale supersession exists in this conversation but not unambiguously in the durable record.  
   **Fix:** Add an explicit banner that §§15–18 supersede §§9–14 in full, and record the revised MMFF/stereo decisions there.

2. **Step 1 — amoxicillin is simultaneously called wrong, net −1, and ambiguous.**  
   Reference: [PLAN.md:11](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PLAN.md:11), [PLAN.md:58](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PLAN.md:58), [PROJECT_CONTEXT.md:419](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PROJECT_CONTEXT.md:419).  
   Failure: The goal and context say amoxicillin “should” be net −1 and count it among two mis-speciated decoys above Q9D. Step 1 correctly notes that it is approximately 50/50; the cited microspeciation study reports the zwitterion at 50.2%, making the current net-zero species marginally the most abundant—not demonstrably wrong. [Amoxicillin microspeciation study](https://sioc-journal.cn/Jwk_hxxb/EN/Y1989/V47/I5/484)  
   **Fix:** Remove the claim that amoxicillin is proven mis-speciated and preregister how near-tied species are selected and sensitivity-tested.

3. **Step 1 — “near pH 7.4” remains an undefined rule boundary.**  
   Reference: [PLAN.md:45](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PLAN.md:45).  
   Failure: The per-site guard does not define “near,” “dominant,” or “ambiguous.” Ampicillin at roughly 56/44, amoxicillin near 50/50, and cephalexin around 75/25 could receive different classifications depending on an unstated confidence threshold. Freezing the resulting table would merely freeze an arbitrary cutoff.  
   **Fix:** Predeclare a quantitative abundance/confidence threshold and a policy for compounds below it—primary highest-abundance state plus separate sensitivity, or exclusion from single-state claims.

4. **Step 1 — a 77-compound table does not cover every species actually docked.**  
   Reference: [PLAN.md:56](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PLAN.md:56), [dock_boron_surrogates.py:55](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/scripts/dock_boron_surrogates.py:55), [run_speb_positive_control.py:59](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/scripts/run_speb_positive_control.py:59).  
   Failure: Q9D is not in the 77-compound library, and the four B→C gem-diol derivatives are new molecules distinct from their boron parents. Thus SpeB and boron cannot actually run “under the frozen species table.” The current boron manifest even records the pre-protonation surrogate SMILES rather than `ligand["docked_smiles"]`.  
   **Fix:** Freeze species records for all 77 parents, Q9D, and all four exact surrogate molecules, and require every prepared entity to resolve to one record.

5. **Step 1 — the frozen table is not bound to its source or made authoritative.**  
   Reference: [PLAN.md:53](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PLAN.md:53).  
   Failure: Threading `ligand_id` permits lookup, but the plan does not require a bijection with the library, bind each row to source CID/SMILES hashes, state whether preparation reads the frozen state or regenerates it, or record the table hash in run manifests. A source SMILES could change under the same ID while a stale species row still passes.  
   **Fix:** Validate exact ID coverage and source hashes, make the frozen species authoritative or fail on regeneration mismatch, and record its SHA-256 in every preparation/docking manifest.

6. **Step 1 — “literature citation for all 77” overstates likely evidence quality.**  
   Reference: [PLAN.md:56](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PLAN.md:56).  
   Failure: Compound-specific experimental pKas may not exist for obscure members such as CCG-2979 and CCG-102487. Reusing a functional-group citation is not a compound-specific audit, while citing PubChem proves structure rather than solution microspeciation.  
   **Fix:** Record an evidence tier—compound-specific experiment, calculated pKa, close analog/class rule, or no relevant ionizable site—plus conditions and estimated species fraction.

7. **Step 4 / prior finding #12 — the MMFF method is still not preregistered.**  
   Reference: [PLAN.md:94](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PLAN.md:94).  
   Failure: The plan says to predeclare a variant and fixed maximum but provides neither. It also does not explicitly include Q9D and the four gem-diol surrogates in the preparation audit. Choosing or increasing the cap after seeing which molecules fail would recreate the undefined escalation it rejects.  
   **Fix:** Put the exact MMFF variant and iteration cap in the plan now, audit every actually docked entity, and require renewed approval rather than cap escalation if any expected entity fails.

8. **Steps 3–5 — the SpeB receptor still bypasses the declared conversion→QC order.**  
   Reference: [PLAN.md:41](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PLAN.md:41), [run_speb_positive_control.py:137](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/scripts/run_speb_positive_control.py:137).  
   Failure: `run_speb_positive_control.py` converts the 6UKD receptor inside the docking run with `--allow_bad_res`; the proposed `pdbqt_quality_review.json` covers only the SpyCEP receptors. SpeB therefore cannot pass the content-addressed QC gate before the four redocks and could omit a dyad residue without the new gate detecting it.  
   **Fix:** Split SpeB receptor preparation/conversion from docking and create a content-addressed QC record verifying Cys192/His340 and the 6UKD/receptor hashes before the control run.

9. **Step 5 — timeout scope and workload remain inconsistent.**  
   Reference: [PLAN.md:105](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PLAN.md:105), [PLAN.md:158](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PLAN.md:158).  
   Failure: “1800s for both boxes” does not explicitly set SpeB or boron timeouts. The stated 310 dockings omits all eight boron-surrogate invocations and counts successful tight rows rather than attempts. With 73 prepared main ligands, the clean ceiling is 146 wide + 146 tight + 20 SpeB + 8 boron = 320 attempts.  
   **Fix:** State the timeout for every workflow explicitly and correct the attempt count to a 320-call ceiling.

10. **Step 5 / prior finding #16 — the eligibility rule is still only promised.**  
    Reference: [PLAN.md:114](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PLAN.md:114).  
    Failure: The plan creates disposition categories but never decides whether an ensemble ligand with only one valid receptor is eligible, whether a non-negative result makes that receptor missing, or which denominator best-receptor and set-level statistics use. This is a substantive analysis-population decision, not an implementation detail.  
    **Fix:** Define the primary ensemble as an explicit complete-case or available-case population now, with separate per-receptor denominators and deterministic tie handling.

11. **Methodological invariant / prior finding #20 — the preregistered criteria are still absent.**  
    Reference: [PLAN.md:27](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PLAN.md:27), [PLAN.md:144](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PLAN.md:144).  
    Failure: “Write down now what the null holds means” is followed by no such definition. The plan does not name the primary box/metric, strong-binding threshold, alpha, relationship between bootstrap and Mann–Whitney results, or multiplicity policy across two boxes and two metrics. That omission becomes critical if one corrected comparison becomes significant. Also, failure to reject is not proof that “the null holds.”  
    **Fix:** Preregister a primary endpoint and analysis population, exact thresholds/tests/alpha/multiplicity treatment, and use “no detected separation” rather than claiming that a statistical null is established.

12. **Methodological invariant — the SpeB decoy set is not concretely frozen.**  
    Reference: [PLAN.md:27](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PLAN.md:27), [run_speb_positive_control.py:110](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/scripts/run_speb_positive_control.py:110).  
    Failure: Current code dynamically reconstructs the panel from the library, heavy-atom tolerance, and a hard-coded role set. The plan says the decoy set will be fixed but specifies no tracked input artifact or exact IDs, so dependency/library changes can alter the benchmark before redocking.  
    **Fix:** Commit a pre-run SpeB panel manifest containing exact IDs, roles, source/species hashes, selection rule, and the 17-decoy pass/fail population.

13. **Methodological invariant — the promised causal attribution cannot come from one before/after comparison.**  
    Reference: [PLAN.md:33](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PLAN.md:33), [PLAN.md:154](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PLAN.md:154).  
    Failure: Species, MMFF geometry, timeout, receptor provenance, and potentially dependency versions all change in the same clean run. A before/after difference cannot be attributed to a “specific corrected defect” without controlled diagnostic counterfactuals.  
    **Fix:** Archive baseline hashes and preregister one-factor diagnostic reruns for any changed headline classification, explicitly separated from the frozen primary run.

14. **Step 9 / prior finding #19 — raw JSON Pointers are unstable and insufficient.**  
    Reference: [PLAN.md:145](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PLAN.md:145).  
    Failure: Rankings and SpeB results are sorted arrays, so a pointer such as `/results/5/...` can silently resolve to another compound after redocking. Raw pointers also cannot express rounding, filtering, rank derivation, or compound conclusions. The registry excludes numeric annotations in generated methods and figures—the exact places prior defects occurred.  
    **Fix:** Generate a stable claim-values artifact keyed by claim ID, including formatter/derivation metadata, and validate README, manuscript, generated methods, and figure annotations against it.

15. **Step 3 — clean execution omits stale sidecars from deletion.**  
    Reference: [PLAN.md:76](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PLAN.md:76), [PLAN.md:86](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PLAN.md:86).  
    Failure: Fresh-run cleanup deletes poses and `.no_fit` markers but not their provenance sidecars or temporary atomic-write files. A same-fingerprint deterministic rerun could leave a stale sidecar with old timing/status after a crash.  
    **Fix:** Delete sidecars and temporary files together with their pose/marker and require sidecar/output hash agreement before either is accepted.

VERDICT: REVISE
### Claude's response (round 2)

Codex closed prior findings #2, #3, #5-11, #13-15, #17, #18. All 15 remaining findings ACCEPTED; none rejected.

MOST IMPORTANT — Codex caught me OVERSTATING the SpeB contamination, and it was right. I had told the user "two of
the five decoys that outrank Q9D are mis-speciated". In fact amoxicillin's zwitterion is 50.2% (its current net-0
state is marginally the MOST abundant — not proven wrong), ampicillin is ~56/44 (marginal), and the compound with
the clearest case (cephalexin, ~75/25) ranks 11th, BELOW Q9D, so it cannot flip the control. Corrected in PLAN.md,
in PROJECT_CONTEXT.md, and to the user directly. The real defect is narrower but still real: near-tied species are
assigned a single state and reported as UNAMBIGUOUS, contrary to the module's own rule. The SpeB result is not
proven wrong — it is not yet proven right.

ESCALATED TO THE USER (3 scientific decisions; all three adopted as recommended): ambiguity threshold >=66% with
sub-threshold compounds docked in BOTH states as a preregistered sensitivity (§19); primary endpoint = wide box +
best affinity, Mann-Whitney alpha=0.05, tight/LE secondary, "no detected separation" language (§20); complete-case
primary population with available-case sensitivity (§21).

FOLDED IN DIRECTLY: supersession banner (§§15-21 supersede §§9-14 in full — §13's "raise until convergence" was
still contradicting the new fixed-MMFF rule); species table extended from 77 to all 82 DOCKED entities (Q9D is not
in the library, and the 4 gem-diol surrogates are new molecules whose manifest currently records the
pre-protonation SMILES); evidence TIERS rather than a blanket "literature citation for all 77" (CCG-2979 and
CCG-102487 have no compound-specific experimental pKa); species table made authoritative + bound to source hashes,
failing on regeneration mismatch; MMFF variant and cap named NOW (MMFF94s, 2000) rather than "predeclare later";
SpeB receptor conversion split out of the docking run and put behind the content-addressed QC gate (it currently
converts 6UKD inline with --allow_bad_res and bypasses QC entirely); attempt ceiling corrected 310 -> 320; frozen
pre-run SpeB panel manifest (the panel is currently reconstructed dynamically and could drift); sidecars and temp
files deleted with their pose/marker; claim registry keyed by stable claim ID rather than raw JSON Pointers (which
resolve into SORTED arrays and would silently point at a different compound after the redock), extended to cover
the generated methods note and figure annotations; one-factor diagnostic counterfactuals preregistered but run only
if a headline classification changes, kept separate from the frozen primary run.

## Round 3 — Codex

The revision closes most prior findings, including the supersession conflict, authoritative species catalog, MMFF choice, QC scope, endpoint/population decisions, provenance, and claim architecture. Seven material gaps remain.

1. **Preregistered outcomes are still result-conditioned.**  
   Reference: [PLAN.md:38](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PLAN.md:38), [PLAN.md:43](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PLAN.md:43), [PLAN.md:56](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PLAN.md:56).  
   Failure: The plan says to report whatever occurs, but also mandates “no detected separation” and asserts `beats_all_decoys == false`. If the primary p-value is below 0.05 or Q9D beats all decoys, those assertions either fail the pipeline or force the old conclusion. The criterion should define what constitutes pass/fail, not require a particular result.  
   **Fix:** Branch neutrally: report “detected separation” iff primary p < 0.05, and report each SpeB metric as pass iff `beats_all_decoys` is true and fail iff false; tests should assert prose/result consistency, not a predetermined Boolean value.

2. **The 82-record catalog omits the alternative species that will actually be docked.**  
   Reference: [PLAN.md:33](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PLAN.md:33), [PLAN.md:73](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PLAN.md:73), [PLAN.md:117](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PLAN.md:117).  
   Failure: Each catalog row contains one SMILES, but every sub-66% compound creates at least one additional docked state. Those alternatives are absent from the authoritative table, its hash, and the stated 82-entity preparation audit. “320 plus sensitivity” therefore leaves part of the method unfrozen.  
   **Fix:** Represent every primary and alternative as a source-bound `entity_id + state_id` record, audit every state through MMFF, and derive the final attempt count from that frozen state list.

3. **“Report SpeB under both states” is undefined for multiple ambiguous decoys.**  
   Reference: [PLAN.md:33](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PLAN.md:33), [PLAN.md:127](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PLAN.md:127).  
   Failure: Ampicillin and amoxicillin already yield four joint state combinations, and the audit may identify more ambiguous decoys. Putting both states into one panel duplicates a decoy and changes the frozen n=17; running only “all primary” versus “all alternative” misses mixed combinations. The same ambiguity affects the custom-vs-FDA sensitivity analysis.  
   **Fix:** Predeclare the scenario rule—e.g. primary-state analysis, one-compound-at-a-time substitutions, and a worst-case envelope over all allowed states while retaining 17 unique decoy identities.

4. **The 66% abundance decision lacks a reproducible evidence-to-fraction procedure.**  
   Reference: [PLAN.md:33](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PLAN.md:33), [PLAN.md:76](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PLAN.md:76).  
   Failure: Evidence tiers are recorded, but the table schema does not require the actual pKa source, experimental conditions, prediction tool/version, uncertainty, or method converting macroscopic/site pKas into whole-molecule microstate abundance. A “close-analog class rule” may not support a numerical 66% determination.  
   **Fix:** Freeze a source hierarchy and calculation protocol, record evidence references/conditions or calculator version, and classify a state as ambiguous whenever its uncertainty interval crosses 66%.

5. **CPU and scoring settings are fingerprinted but not frozen.**  
   Reference: [PLAN.md:51](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PLAN.md:51), [PLAN.md:93](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PLAN.md:93).  
   Failure: The fingerprint includes CPU/scoring settings, but the frozen-parameter block supplies no values. Current Vina commands omit them, so CPU count remains machine-dependent and can affect whether a run reaches the wall-clock timeout.  
   **Fix:** Predeclare explicit `--cpu` and `--scoring` values—and record all other effective Vina defaults—before generating the frozen run fingerprint.

6. **Complete-case eligibility still does not define a valid docking result.**  
   Reference: [PLAN.md:47](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PLAN.md:47), [PLAN.md:134](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PLAN.md:134).  
   Failure: “Docked successfully” could mean Vina exited zero and wrote a pose, while the existing analysis treats non-negative affinity as a clash/non-fit. The plan also says tie handling is deterministic without stating the receptor tie-break. These choices determine the primary population and triad statistic.  
   **Fix:** Define `valid_fit` exactly—exit status, parseable pose/modes, hash agreement, and affinity rule—and specify a fixed receptor ordering for equal best scores.

7. **The one-factor attribution audit remains a promise rather than a design.**  
   Reference: [PLAN.md:164](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PLAN.md:164).  
   Failure: “Preregister one-factor diagnostic reruns” does not state the actual contrasts or which old/new settings remain fixed. Without a matrix, a changed headline can still be attributed selectively after inspection.  
   **Fix:** Freeze the diagnostic matrix before the primary run, naming each baseline/new contrast, held-constant settings, triggering classification changes, and the rule that diagnostics cannot replace primary results.

VERDICT: REVISE
### Claude's response (round 3)

Codex closed the supersession conflict, the authoritative species catalog, the MMFF choice, QC scope, the
endpoint/population decisions, provenance, and the claim architecture. All 7 remaining findings ACCEPTED; none
rejected.

MOST IMPORTANT — #1, and I committed this error TWICE. My "preregistered criteria" asserted
`beats_all_decoys == false` and mandated the phrase "no detected separation". That preregisters the ANSWER, not the
CRITERION. Had the corrected chemistry made Q9D beat the decoys, my own test suite would have failed the pipeline
and forced the old conclusion — the exact result-conditioned reasoning I flagged in Codex's round-1 #20 and then
reproduced myself. Replaced with NEUTRAL BRANCHING: report "detected separation" iff p < 0.05; report each SpeB
metric pass iff beats_all_decoys is true, fail iff false; tests assert PROSE/RESULT CONSISTENCY, never a
predetermined boolean.

FOLDED IN: species catalog restructured from one-row-per-compound to a (entity_id, state_id) catalog — every
sub-66% compound contributes primary AND alternative states that are actually docked, so a one-SMILES-per-compound
table would have left part of the frozen method outside the table, its hash, and the MMFF audit; the attempt count
is now DERIVED from the frozen state list rather than asserted. Scenario rule for multiple ambiguous decoys frozen
(all-primary headline; one-compound-at-a-time substitutions; worst-case envelope; panel always retains 17 UNIQUE
decoy identities so a compound is never duplicated and frozen n cannot move). Evidence-to-fraction protocol frozen
with a source hierarchy, recorded uncertainty, and the rule that a state is ambiguous whenever its uncertainty
interval CROSSES 66% (a class rule cannot by itself support a numeric dominance call). `--cpu 1` and
`--scoring vina` frozen explicitly — multi-CPU Vina is non-deterministic even under a fixed seed, so --cpu 1 is
REQUIRED for the reproducibility claim and also removes a machine-dependent influence on hitting the wall-clock
ceiling. `valid_fit` defined exactly (exit 0 + parseable modes + sidecar/output hash agreement + affinity < 0) with
a frozen 5XYA-before-7EDD receptor tie-break. One-factor diagnostic MATRIX frozen as a table (D1 species, D2 MMFF,
D3 timeout, D4 cpu), triggered only if a headline classification flips, and explicitly barred from replacing the
primary result.

## Round 4 — Codex

Not yet. The `--cpu/--scoring` fingerprint and exact `valid_fit`/tie-break fixes are genuinely closed. Several others remain only partially implemented.

1. **The authoritative decision record restores the forbidden result-conditioned rules.**  
   Reference: [PLAN.md:4](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PLAN.md:4), [PROJECT_CONTEXT.md:466](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PROJECT_CONTEXT.md:466).  
   Failure: PLAN says §§15–21 supersede everything, but §20 still mandates “no detected separation” and `beats_all_decoys == false`; under PLAN’s own precedence rule, lines 40–46 lose. §21 also retains the fixed 320-plus-sensitivity count.  
   Fix: Update the superseding decision record to the neutral branches and derived-count policy, or remove its precedence over PLAN.

2. **`state_id` stops at the catalog, causing alternate states to collide.**  
   Reference: [PLAN.md:93](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PLAN.md:93), [PLAN.md:96](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PLAN.md:96), [PLAN.md:124](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PLAN.md:124).  
   Failure: The API change threads only `ligand_id`; multiple states of one entity will share preparation and docking filenames, so poses, markers and sidecars can overwrite one another.  
   Fix: Thread `(entity_id, state_id)` through preparation, docking, filenames, manifests, dispositions, fingerprints and claim keys.

3. **The docking count still cannot be derived from the species catalog.**  
   Reference: [PLAN.md:96](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PLAN.md:96), [PLAN.md:144](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PLAN.md:144), [PLAN.md:154](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PLAN.md:154).  
   Failure: A state list alone does not say whether a state enters wide, tight, SpeB, boron-surrogate, or multiple workflows. The plan also reasserts “320 … plus sensitivity” and audits “82 entities” rather than every state.  
   Fix: Freeze an attempt manifest as the explicit state × workflow × receptor × box cross-product, derive the count from it, and audit exactly those state records.

4. **“Every alternative” is not a defined finite species set.**  
   Reference: [PLAN.md:52](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PLAN.md:52).  
   Failure: Polyprotic compounds can have many low-population microstates; without an abundance or cumulative-coverage cutoff, different implementers can include different alternatives and obtain different worst-case envelopes.  
   Fix: Preregister a finite inclusion rule, such as every state above a fixed abundance plus enough states to cover a fixed cumulative population.

5. **The evidence-to-fraction protocol still contains placeholders.**  
   Reference: [PLAN.md:54](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PLAN.md:54).  
   Failure: “Named tool + version” does not name one, and allowing each row to record its own macro-pKa-to-microstate method relocates rather than eliminates human judgment; the uncertainty confidence level and propagation procedure are also undefined.  
   Fix: Name the actual calculator/version, conversion algorithm, physical conditions, uncertainty definition and propagation method before constructing the table.

6. **The scenario rule is complete only for part of SpeB.**  
   Reference: [PLAN.md:59](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PLAN.md:59).  
   Failure: It discusses ambiguous decoys but not an ambiguous Q9D or reference ligand, does not define “worst” separately for affinity and efficiency, and supplies no sensitivity aggregation for ambiguous custom/FDA compounds.  
   Fix: Define role- and metric-specific scenario functions for both screen and SpeB, including Q9D states, ties and the exact reported envelope.

7. **Missing alternative-state fits can bias both sensitivities toward success.**  
   Reference: [PLAN.md:65](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PLAN.md:65), [PLAN.md:161](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PLAN.md:161).  
   Failure: If a favorable decoy state or difficult FDA state times out, it can disappear from the envelope or complete-case population. Available-case analysis does not address zero-fit entities.  
   Fix: Predeclare state-level missingness handling and report group/role-specific attrition, including conservative bounds when a required sensitivity state lacks a valid fit.

8. **Lisinopril remains silently absent from the remediation rules.**  
   Reference: [upstream Finding 2](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/docs/CODEX-CODE-REVIEW-2026-07-13.md:9), [PLAN.md:87](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PLAN.md:87), [PLAN.md:111](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PLAN.md:111).  
   Failure: The upstream defect explicitly includes lisinopril’s incorrectly protonated secondary amine, but the fix list names losartan, doxycycline and sildenafil without requiring a lisinopril regression. An exhaustive table does not guarantee the generic rule is corrected.  
   Fix: Add lisinopril’s expected dominant atom-mapped net−1 state and a dedicated regression test.

9. **The stated execution order can regenerate outputs under stale dependencies.**  
   Reference: [PLAN.md:84](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PLAN.md:84), [PLAN.md:139](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PLAN.md:139).  
   Failure: Receptor conversion is ordered before the environment pin; changing Meeko or related code afterward invalidates the supposedly gated receptor output. Species generation has the same dependency-order problem.  
   Fix: Put code, schema and dependency freezing before any receptor conversion, species generation or QC approval.

10. **D1–D4 still do not support the promised attribution.**  
    Reference: [PLAN.md:191](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PLAN.md:191), [docking.py:21](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/src/spycep_drug_discovery/docking.py:21).  
    Failure: D3 calls an unexecuted 1800/600 proposal the baseline, while the current code default is 600 seconds. The table also names receptor provenance and dependency versions as simultaneous changes but provides no contrasts for either. One-factor ablations around the new configuration cannot uniquely decompose interactions.  
    Fix: Compare actual archived baseline settings, add receptor/dependency contrasts where feasible, and describe D1–Dn as controlled ablations rather than unique causal attribution.

11. **Catalog integrity and source binding are internally impossible as written.**  
    Reference: [PLAN.md:96](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PLAN.md:96), [PLAN.md:107](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PLAN.md:107).  
    Failure: Multiple rows per entity plus Q9D and surrogates cannot be a row-level “bijection with the library”; generated B→C surrogates also may have no source CID. No checks require fractions to sum to one or exactly one primary state.  
    Fix: Validate unique `(entity_id,state_id)`, entity-projection coverage, normalized fractions and one primary, using CID-or-citation-or-parent-transformation provenance.

12. **The bootstrap CI remains statistically unspecified.**  
    Reference: [PLAN.md:48](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PLAN.md:48).  
    Failure: It does not identify the CI estimand, resampling unit, method, replicate count or seed, so materially different “bootstrap 95% CIs” satisfy the plan.  
    Fix: Freeze an effect estimand and complete bootstrap specification, including stratification, method, replicates and seed.

The neutral reporting language itself is now correct, but the supersession conflict, state-key collision, undefined state universe and incomplete scenario analysis make implementation unsafe. The header also still says “Round 3” and “35 findings,” which should be corrected for audit-trail integrity.

VERDICT: REVISE
### Claude's response (round 4)

All 12 findings ACCEPTED; none rejected.

MOST IMPORTANT — #1 was an own-goal with teeth. PLAN.md declared that PROJECT_CONTEXT.md §§15-21 SUPERSEDE
everything, but §20 still contained the OLD result-conditioned rules ("no detected separation",
beats_all_decoys == false). Under my own precedence rule the durable record's bad version WON over the plan's
neutral fix. I had fixed the plan and left the authority pointing at the wrong text. §20/§21 rewritten to carry the
neutral branches and the derived attempt count.

#8 — lisinopril had silently VANISHED from the fix list between drafts despite being one of the three originally
mis-speciated compounds. Restored, with a dedicated regression test (as for losartan, doxycycline, sildenafil and
the beta-lactams) — an exhaustive table does not prove the generic rule was fixed.

FOLDED IN: (entity_id, state_id) threaded through preparation, docking, FILENAMES, manifests, dispositions,
fingerprints and claim keys — multiple states of one entity would otherwise overwrite each other's poses, markers
and sidecars. Attempt manifest frozen as an explicit state x workflow x receptor x box cross-product, with the
attempt count DERIVED from it (the fixed "320" could never account for the alternative states the ambiguity policy
docks). Finite state universe frozen: every state >=5% abundance, adding states until >=95% cumulative coverage —
"every alternative" is unbounded for polyprotic compounds. Evidence-to-fraction protocol de-placeholdered: NO pKa
calculator is used at all (introducing an unvalidated predictor relocates the judgement rather than removing it);
tiers are compound-specific experimental > close-analog class rule > no ionisable site, with conditions,
+/-0.5 default uncertainty, Henderson-Hasselbalch propagation, and "ambiguous whenever the 95% interval crosses
66%" — so class-rule compounds default to AMBIGUOUS unless the interval clears. Scenario rule extended to ALL
ambiguous entities including Q9D itself and ambiguous custom/FDA compounds, with "worst" defined PER METRIC.
State-level missingness handled with role-specific attrition + conservative bounds, so a timed-out favourable decoy
state cannot silently bias the envelope toward success. Catalog integrity made internally possible: unique
(entity_id, state_id), ENTITY-PROJECTION coverage rather than a row-level bijection, fractions sum to 1, exactly one
primary, provenance = CID or citation or parent-transformation (generated surrogates have no CID). Bootstrap fully
specified (BCa, estimand = difference in mean best affinity custom-minus-FDA, resampling unit = ligand, stratified
by set, 10,000 replicates, seed 42). Dependency/schema freeze moved BEFORE receptor conversion and species
generation. D-matrix baselines corrected to the ACTUAL archived settings (code default 600s; the 1800/600 split was
a proposal that never ran), D5 added, and the matrix relabelled CONTROLLED ABLATIONS rather than unique causal
attribution. Header corrected.

## Round 5 — Codex (FINAL, MAX_ROUNDS reached)

No. The plan is substantially improved, but five issues still block an unambiguous implementation. The neutral branching, state-key propagation, lisinopril regression, dependency ordering, fingerprint, and derived-count principle are otherwise closed.

## Blocking implementation

1. **The decision record is still internally stale and contradictory.**  
   Reference: [PROJECT_CONTEXT.md:424](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PROJECT_CONTEXT.md:424), [PROJECT_CONTEXT.md:439](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PROJECT_CONTEXT.md:439), [PROJECT_CONTEXT.md:461](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PROJECT_CONTEXT.md:461), [PLAN.md:4](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PLAN.md:4).  
   Failure: §18 still says `Assert beats_all_decoys == false`; §15 still specifies 77 compounds and only `ligand_id`; §19 still says one alternative, SpeB “both states,” and an 82-entity—not state—MMFF audit. These directly conflict with PLAN even though PLAN requires agreement.  
   Fix: Rewrite §§15, 18 and 19 to the round-5 rules, especially deleting §18’s predetermined assertion.

2. **The finite-state catalog cannot satisfy its own integrity checks.**  
   Reference: [PLAN.md:45](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PLAN.md:45), [PLAN.md:106](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PLAN.md:106).  
   Failure: Docked rows cover at least 95% of population, yet their fractions must sum to 1. Renormalizing the included states would alter the 5% and 66% decisions. It is also unclear whether a nominally single 80/20 compound docks only the 80% state or both states under the ≥5% rule.  
   Fix: Separate the complete population ledger from the docked-state subset; only the full ledger sums to 1, excluded residual is recorded without renormalization, and the docking rule for ≥66% compounds is explicit.

3. **Henderson–Hasselbalch does not determine exact atom-mapped microstates from macroscopic pKas.**  
   Reference: [PLAN.md:50](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PLAN.md:50), [PLAN.md:112](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PLAN.md:112).  
   Failure: Sequential macroscopic pKas can provide charge-state populations, but generally cannot identify which site carries the proton or divide abundance among tautomeric/site microstates—precisely what lisinopril, doxycycline and the exact atom-mapped catalog require. The default ±0.5 is also not a “95% interval” unless its statistical meaning is defined and justified.  
   Fix: Require microscopic/site-assignment evidence where available; otherwise enumerate plausible site microstates as ambiguous without fabricated fractional precision, and call ±0.5 a sensitivity range unless it has calibrated 95% coverage.

4. **The screen’s worst-case sensitivity and missing-state bound remain undefined.**  
   Reference: [PLAN.md:56](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PLAN.md:56), [PLAN.md:62](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PLAN.md:62).  
   Failure: “Worst” is defined only relative to the SpeB positive control, despite applying to ambiguous custom/FDA entities. “Maximally unfavourable to the conclusion being tested” is both numerically unbounded and potentially result-conditioned for a two-sided screen.  
   Fix: For the screen, preregister neutral minimum/maximum effect and p-value envelopes across allowed states; treat unbounded missing-state cases as indeterminate or use explicitly justified finite bounds.

5. **The attempt manifest is described as the wrong mathematical object.**  
   Reference: [PLAN.md:116](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PLAN.md:116), [PROJECT_CONTEXT.md:486](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PROJECT_CONTEXT.md:486).  
   Failure: A literal state × workflow × receptor × box Cartesian product would send Q9D, surrogates and screen ligands into inapplicable workflows. PROJECT_CONTEXT also omits the box dimension.  
   Fix: Define a workflow-eligibility relation and materialize one manifest row per legal invocation, with identical dimensions in PLAN and PROJECT_CONTEXT.

## Refinements during the build

- **Test and CI estimands differ.** [PLAN.md:39](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PLAN.md:39) combines a Mann–Whitney distributional test with a mean-difference CI, which can legitimately disagree. Prefer a probability-of-superiority/rank-biserial CI, or explicitly state that the p-value and CI describe different estimands.

- **The ablation matrix is not yet actually frozen.** [PLAN.md:183](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PLAN.md:183) gives labels rather than exact variants, held-constant hashes and commands, while “D5 … where feasible” leaves a post-result choice. Fill out and freeze the table before the primary run.

- **Do not equate every non-negative Vina score with a clash.** [PLAN.md:69](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PLAN.md:69) may retain `<0` as the preregistered operational inclusion rule, but “clash” requires geometric evidence and should be reported as “operational non-fit” otherwise.

VERDICT: REVISE
### Resolution — DEADLOCK, not convergence

MAX_ROUNDS=5 reached without APPROVED. Not presented as convergence.

CLOSED over the five rounds (Codex explicitly confirms): neutral branching criteria; (entity_id, state_id) key
propagation; lisinopril regression; dependency-freeze ordering; resume fingerprint; derived-count principle.
These cover the ORIGINAL 12 code-review defects — none of the original findings is in dispute.

STILL BLOCKING (5) — and note ALL FIVE concern the microstate/ambiguity machinery that was ADDED during the
review, not the original defects:
  1. PROJECT_CONTEXT §§15/18/19 still stale (§18 still carries "assert beats_all_decoys == false").
  2. The state catalog cannot satisfy its own integrity checks: rows covering >=95% of population cannot also sum
     to 1 without renormalisation, and renormalising would move the 5%/66% decisions.
  3. **The deep one.** Henderson-Hasselbalch on MACROSCOPIC pKas cannot identify WHICH SITE carries the proton, nor
     divide abundance among tautomeric/site microstates. But exact atom-mapped microstates with numeric fractions is
     precisely what the plan demands for lisinopril, doxycycline and the catalog. The goal is partly UNATTAINABLE
     from the available evidence. The +/-0.5 default is also not a "95% interval" in any calibrated sense.
  4. "Worst-case" is defined only relative to the SpeB control, yet applied to ambiguous custom/FDA entities; and
     "maximally unfavourable to the conclusion" is unbounded and itself result-conditioned for a two-sided screen.
  5. The attempt manifest is the wrong mathematical object: a literal state x workflow x receptor x box Cartesian
     product would route Q9D and the surrogates into inapplicable workflows.

CLAUDE'S POSITION: Codex is right on all five, and #3 is the decisive one — it is a statement about chemistry, not
about the plan. Demanding numeric microstate fractions manufactures precision the evidence cannot support, which is
the SAME defect class this whole remediation exists to eliminate. More review rounds cannot fix that; it needs a
design change. Proposed synthesis (Codex's own #3 fix, generalised): DROP numeric fractions entirely. Classify each
state as UNAMBIGUOUS (compound-specific experimental/microscopic evidence for a single dominant state) / AMBIGUOUS
(dock all plausible site microstates, report a bounded envelope, claim no fractional precision) / NO IONISABLE SITE.
This closes #2 (no sum-to-1 constraint to violate), #3 (no fabricated fractions), and most of #4, and it is better
science than the version Codex was reviewing.

Handed to the user at gate #2 to decide scope. No code written during either act.

## Round 9 — Codex: VERDICT APPROVED

Yes. The plan is now sound enough to implement. The two round-8 blockers are genuinely closed rather than displaced.

## Blocking implementation

None.

The tier-dependent validation now has an executable split: rule matching for single-state tiers and verbatim, charge-preserving validation for ambiguous states. State ambiguity also propagates consistently through screen statistics, SpeB, triad counts, ranks, figures, prose and claim validation. No downstream step may recover a convenient point estimate by selecting a state.

The bounded two-state design, exhaustive `k≤16` rule, explicit abort conditions, four-way outcomes, legal-invocation manifest and neutral reporting rules collectively prevent silent truncation or result-conditioned rescue of either headline.

## Safe build-time refinements

- Update the stale sentence in [PROJECT_CONTEXT.md:579](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PROJECT_CONTEXT.md:579) from generic “regeneration mismatch” to the J tier-dependent validation rule. J makes the intended behavior unambiguous, but the obsolete sentence should not remain.

- Give triad ranges their own labels—such as `STATE_INVARIANT`, `STATE_DEPENDENT`, and `INDETERMINATE_*`—because `ROBUST_PASS` and `ROBUST_DETECTED` have threshold-specific meanings that do not naturally apply to an unthresholded contact count.

- Clarify whether “all distinct tied extrema” means configurations or unique score vectors, and record configuration IDs in the CI artifact. Also state which configurations, if any, receive the secondary mean-difference CI.

- Record the reviewer, citation, classification rationale, review date and explicit “more than two plausible states considered?” decision for every hand-adjudicated entity. This preserves the intended auditability without inventing abundance precision.

- Correct the Round 8 metadata and the minor Markdown typo at [PLAN.md:191](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/PLAN.md:191).

These refinements do not require another scientific decision, alter the preregistered endpoints, or prevent implementation from starting.

VERDICT: APPROVED
### Resolution — CONVERGED

APPROVED at round 9, zero blocking issues. MAX_ROUNDS was raised 5 -> 8 -> 9 by the user rather than shipping on a deadlock.

Finding count by round: 20, 15, 7, 12, 5, 5, 7, 2, 0.

The five non-blocking refinements from round 9 were applied immediately (28 J/M/N/O): stale 'regeneration mismatch' sentence corrected to the tier-dependent rule; triad ranges given their own STATE_INVARIANT/STATE_DEPENDENT vocabulary rather than reusing threshold-specific ROBUST_* labels; extremal ties resolved over distinct configurations with IDs recorded; secondary mean-difference CI scoped to the extremal configurations; and a full audit trail (reviewer, citations, rationale, date, explicit >2-states-considered decision) for every hand-adjudicated entity.

NO CODE WAS WRITTEN DURING EITHER ACT. Awaiting user sign-off at gate #2.

## Act 3 — Build (Codex, workspace-write)

### Round 1 — Codex build

Sandbox repair required first: codex workspace-write failed with 'helper=codex-windows-sandbox-setup.exe error=program not found'.
Root cause was NOT a missing file — the helper ships in codex-resources/ and was present on disk. Codex spawns it by BARE NAME,
so it relies on a PATH lookup, and codex-resources/ was not on PATH. Fixed per-invocation with a PATH prefix
(a persistent user-PATH edit was correctly refused as out of scope for 'repair the sandbox').

Codex delivered: 22 files modified, 19 new (2219 insertions). 82 entities / 85 states catalogued, 335 legal attempts derived,
81-state MMFF94s audit, primary + SpeB receptor QC gates, claimed 155 tests passing.

### Claude's verdict — VERIFIED INDEPENDENTLY (Codex's claims are advisory)

PROOF DISCREPANCY (found, fixed): Codex reported "155 passed". That was true IN ITS SANDBOX ONLY. It had added
`--basetemp=.pytest_tmp` to pyproject.toml, redirecting pytest's temp dir INTO the repo — which lives in OneDrive,
whose sync process locks the directory. In the real environment this produced PermissionError [WinError 5] across
test_targets.py. I reverted the workaround (keeping its correct version pins: rdkit==2025.9.6, meeko==0.7.1).
Suite now genuinely passes 155/155 in the user's environment. This is exactly why the proof is re-run, never trusted.

CHEMISTRY VERIFIED EMPIRICALLY (9/9), not merely via Codex's own tests:
  ampicillin -1, amoxicillin -1, cephalexin -1 (beta-lactam alpha-amino no longer wrongly protonated)
  losartan -1 (was NEUTRAL — the tetrazole tautomer bug), lisinopril -1 (was net 0), sildenafil neutral (was +1)
  azithromycin +2 PRESERVED (the case a naive "most basic amine only" rule would have destroyed)
  metformin +1 (not +3), benzamidine +1
STATE-ROBUSTNESS IS ACTUALLY USED WHERE IT MATTERS: amoxicillin, ampicillin and cephalexin are classified AMBIGUOUS,
each carrying BOTH states (net -1 and net 0) for docking. These are precisely the compounds contaminating the SpeB
control. Their classification_evidence explicitly REFUSES to claim an abundance, and cites the real papers surfaced
during the review rounds (amoxicillin microspeciation; ampicillin PMC; cephalexin RSC). NOT fabricated.

DEFECT FOUND — the one that matters most: the 24 protonation reference cases cite PUBCHEM URLS AND NOTHING ELSE.
No pKa value, no literature source, no evidence tier — the record is just {name, smiles, citation:pubchem, expected}.
This fails the spec on the exact point CODEX ITSELF raised in round 1: "citing PubChem proves structure rather than
solution microspeciation." The README claim "validated against literature charges for 24 reference compounds" would
therefore STILL BE FALSE — cited-looking, but backed by the wrong kind of evidence. Codex cannot fix this (no web
access; asking it for literature citations would invite fabrication, which is strictly worse). Claude takes over:
fetching real, verifiable pKa sources with anti-fabrication rules, recording pka value + site + conditions + source +
evidence tier per compound, marking NO_SOURCE_FOUND honestly where none exists, and rewording the README to exactly
what the evidence supports.

### Round 2 — Claude takeover (citation evidence)

Codex could not fix the citation defect (no web access; asking it for literature citations would invite fabricated DOIs
— strictly worse than the honest-but-inadequate PubChem links it produced). Claude took over per the skill's takeover rule.

Three parallel researchers fetched REAL pKa evidence under hard anti-fabrication rules (must load the page; never
reconstruct a DOI/author/year from memory; NO_SOURCE_FOUND is an acceptable answer). Results, all recorded in
docs/methods/protonation_reference_cases.json with pka value + site + conditions + source URL + verbatim quote + tier:
  COMPOUND_SPECIFIC_EXPERIMENTAL 16 | CURATED_EXPERIMENTAL_COMPILATION 3 | SECONDARY_REVIEW 3 | NO_SOURCE_FOUND 2

TWO GENUINE NO_SOURCE_FOUND — and both are the exact defect class this project exists to eliminate, found in the
PUBLISHED LITERATURE:
  - pentamidine: no experimental pKa exists in any fetchable source. The circulating "pKa 12.1" — stated as fact with NO
    reference in a PLoS Pathogens paper — is almost certainly DrugBank's PREDICTED 12.13 laundered into prose. A 2022
    paper explicitly labels it "predicted". Its +2 state is justified as a close-analog inference from benzamidine
    (experimental 11.6) and labelled as such, never as a pentamidine measurement.
  - fosfomycin: the only value printed in a peer-reviewed paper we could open is EXPLICITLY a Chemicalize PREDICTION
    (1.25/7.82). The 1.8/6.5 pair in search results traces to a paywalled paper that could not be opened.
Also refused: warfarin's canonical 5.05 (unverifiable), azithromycin's popular 8.74/9.45 pair (unverifiable — used the
verified 8.1/8.8, which still gives +2), metformin's FDA-label 12.4 (every accessdata.fda.gov URL 404'd).

RECLASSIFICATION DRIVEN BY THE EVIDENCE: lisinopril moved UNAMBIGUOUS -> AMBIGUOUS. The best source (potentiometry +
1H NMR-pH, 25 C, I=0.15 M, with explicit site assignment) publishes a speciation table AT PLASMA pH: HLis- 65.04%,
neutral double-zwitterion H2Lis 34.93%. A 35% minor species is far too large to assert away. It now joins the three
beta-lactams and is docked in BOTH states. Catalog: 82 entities / 86 states / 4 AMBIGUOUS; 339 derived legal attempts;
MMFF94s cap-2000 audit passes for all 82 unique states.

THE TEST THAT LET THE DEFECT THROUGH IS FIXED. The old assertion was `case["citation"].startswith("https://")` — which a
PubChem URL satisfies perfectly. That is precisely how 24 structure links came to stand in for pKa evidence while the
README claimed "validated against literature charges". The new test asserts the tier is valid, that the pKa source is
NOT PubChem, that a value + citation + verbatim quote exist, and that NO_SOURCE_FOUND compounds assert no value at all.

README corrected: the "24 reference compounds" claim now states the real tier breakdown; "nothing hand-entered" now names
the one deliberate exception (the ambiguous states are a HYPOTHESIS, not a result — we dock both rather than assert one);
the false "per-docking commands" claim is replaced with what the pipeline now actually does; and a STATUS BANNER warns
that all results below are STALE pending the redock.

PROOF: 157 passed (Claude's own run, in the user's real environment).


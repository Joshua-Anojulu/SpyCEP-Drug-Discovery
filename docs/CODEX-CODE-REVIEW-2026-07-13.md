## CONFIRMED

1. **CRITICAL — [scripts/compute_statistics.py](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/scripts/compute_statistics.py:81): triad engagement is computed over any receptor, despite being reported as the ligand’s best receptor.**

   Failure: Recomputing from `pose_interactions` using the lowest-affinity receptor gives wide-box counts of 67/73, 53/73, and 31/73—not 73/73, 64/73, and 42/73—and tight-box counts of 72/72, 60/72, and 35/72—not 72/72, 66/72, and 47/72. This invalidates manuscript line 59, `docking_statistics.json:77-89`, the generated methods note, and Figure 4. The historical assertion that 55–56 was a pose-row count is also unsupported: commit `22d4a6a` contains 53 and 59 such rows.

   Fix: Select `min(rows, key=best_affinity_kcal_mol)` for each ligand before counting contacts, then regenerate statistics, prose, and Figure 4.

2. **CRITICAL — [protonation.py](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/src/spycep_drug_discovery/protonation.py:59): the claimed dominant-microspecies rules assign materially wrong states to at least losartan, doxycycline, and lisinopril.**

   Failure: `docking_result.json:574-580` docks losartan neutral because the tetrazole SMARTS recognizes only one tautomer; `:365-371` docks doxycycline as +1 while omitting its acidic tricarbonyl/enol deprotonation; `:563-569` protonates both lisinopril amines and reports net 0 although its lower-basicity secondary amine is predominantly neutral at pH 7.4, giving a dominant net −1 species. These established speciation facts are supported by the [losartan tetrazole study](https://www.sciencedirect.com/science/article/pii/S0021925819479921), [doxycycline pKa/speciation study](https://pmc.ncbi.nlm.nih.gov/articles/PMC2850495/), and [lisinopril acid-base profiling](https://hrcak.srce.hr/en/112502).

   Fix: Use tautomer-insensitive matching plus curated compound-specific microstates for the complete 77-compound library, then reprepare and redock every affected ligand.

3. **HIGH — [README.md](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/README.md:19): “validated against literature charges for 24 reference compounds” is unsupported.**

   Failure: `test_protonation.py` contains only 14 unique reference compounds—13 parametrized compounds plus amlodipine—and supplies no literature citations; it omits tetrazole, phosphonate, sulfonic acid, boronic acid, thiol, sulfonamide, doxycycline, and lisinopril cases.

   Fix: Either reduce the claim to the actual cited validation set or add 24 genuinely independent, cited reference compounds covering every declared rule and relevant library exception.

4. **HIGH — [docking.py](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/src/spycep_drug_discovery/docking.py:153): resume accepts any existing pose without validating ligand, receptor, box, or command fingerprints.**

   Failure: A protonation or box change followed by `--resume` silently associates stale poses with newly generated ligand metadata. The current wide manifest contains 146/146 placeholder commands, the tight manifest contains 50 placeholders, and both say `resumed_existing_poses: true`; SpeB and boron manifests contain no per-run hashes or commands at all. Thus README/manuscript claims that every Vina invocation has its command and SHA-256 are false.

   Fix: Store and verify a content-addressed run fingerprint covering ligand/receptor hashes, box, Vina version, and parameters; retain a normalized full command on resume and regenerate these manifests from a clean, non-resumed run.

5. **HIGH — [ligand_preparation.py](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/src/spycep_drug_discovery/ligand_preparation.py:115): `embedded_isomeric_smiles` does not record the arbitrary stereoisomer selected in 3-D.**

   Failure: RDKit still reports every one of the 13 advertised compounds as containing `?` stereocentres after parsing the recorded SMILES; for example, ibuprofen is recorded at `docking_result.json:464-472` without an `@` tag. A third party cannot identify the claimed docked isomer from the tracked manifest.

   Fix: Assign chiral tags from the embedded conformer before producing the SMILES—or explicitly enumerate and choose a stereoisomer—and test that no reported assigned centre remains undefined.

6. **HIGH — [scripts/make_figures.py](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/scripts/make_figures.py:105): Figure 2 contains false and inconsistent numeric labels.**

   Failure: Line 137 reads the first affinity-sorted result, dexamethasone, and labels Q9D as having 28 heavy atoms rather than 25; lines 106–127 exclude the two protease comparators, so the rendered figure says 6/18 and 7/18 while the manuscript headline says 6/20 and 7/20.

   Fix: Locate Q9D explicitly for its heavy-atom count and either plot all 20 compounds with distinct comparator styling or consistently report the decoy-only denominator.

7. **HIGH — [spycep_insilico_screen.md](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/docs/manuscript/spycep_insilico_screen.md:47): the claimed RDKit 2026.03.3 provenance is contradicted by the repository evidence.**

   Failure: `pdbqt_conversion.json:9` records RDKit 2025.09.6, and the current result-producing environment also reports 2025.09.6; ligand manifests record no RDKit version. Exact conformer and PDBQT reproduction cannot be tied to the claimed version.

   Fix: Record actual RDKit/Meeko versions in every ligand/docking manifest, pin them with a lockfile or exact versions, regenerate, and correct the manuscript.

8. **HIGH — [ligand_preparation.py](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/src/spycep_drug_discovery/ligand_preparation.py:101): MMFF non-convergence is accepted and then hidden from the tracked manifests.**

   Failure: Re-running the exact seed/species in memory returned MMFF status 1 for 47 of 73 prepared ligands; only 26 converged. `smiles_to_sdf` records `mmff_converged=False`, but `run_docking.py:167-179` drops that field, while the manuscript says ligands were MMFF-optimized.

   Fix: Increase the iteration budget and fail or explicitly retain non-convergence; record status and iteration settings in the manifest and regenerate affected dockings.

9. **MEDIUM — [scripts/run_docking.py](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/scripts/run_docking.py:78): the advertised PDBQT QC gate is not enforced by docking.**

   Failure: The script reads `pdbqt_conversion.json` directly and never reads `pdbqt_quality_review.json`; a future QC result of `blocked_before_docking` would not prevent docking, contrary to manuscript line 18.

   Fix: Require a passing QC manifest, matching receptor hashes, and no blocked receptor before entering the ligand loop.

10. **MEDIUM — [spycep_insilico_screen.md](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/docs/manuscript/spycep_insilico_screen.md:33): the “five hours” vancomycin claim is not traceable to a tracked artifact.**

   Failure: The tight manifest records a 600-second default, the wide manifest records 1800 seconds despite current code using 600, and the tracked JSON only says a previous run failed; no tracked timing supports five hours. `docking_statistics.json:41` also incorrectly reports `non_fits_excluded: []`.

   Fix: Record actual elapsed time, applied timeout, and non-fit cause in the result JSON, then derive exclusion metadata from preparation/docking failures.

11. **MEDIUM — [docking.py](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/src/spycep_drug_discovery/docking.py:183): fresh executions do not remove stale outputs or stale timeout markers before invoking Vina.**

   Failure: If Vina exits zero without writing, an old pose can be hashed and analyzed as the new result; conversely, a successful rerun leaves an old `.no_fit` marker that later takes precedence during resume. Receptor conversion has the same stale-output existence check at `pdbqt_conversion.py:93-100`.

   Fix: Delete old output/marker files before fresh execution, require newly created outputs, and clear failure markers after success.

12. **MEDIUM — [spycep_insilico_screen.md](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/docs/manuscript/spycep_insilico_screen.md:57): “changed nothing about where [benzamidine] lands” is literally false.**

   Failure: HEAD ranks neutral benzamidine 65th by wide-box affinity; the protonated run ranks it 67th and changes both receptor scores.

   Fix: Say it “remained near the bottom, moving from 65th to 67th” rather than claiming no change.

## SUSPECTED / NOT FULLY VERIFIED

1. **[README.md](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/README.md:16): “109 passing tests” was not fully executable in this read-only environment.**

   Failure: Exactly 109 tests collect and the 26 pure protonation/statistics/docking tests pass, but the full suite requires writable temporary directories unavailable here.

   Fix: Attach a clean CI run or tracked test report before retaining “passing.”

2. **[spycep_insilico_screen.md](/C:/Users/josha/OneDrive/Documents/SpyCEP-Drug-Discovery/docs/manuscript/spycep_insilico_screen.md:47): cross-machine bitwise determinism remains unproven.**

   Failure: Manifests contain absolute user paths, dependency constraints are not an exact lock, and there is no tracked paired rerun demonstrating identical Vina hashes on a clean checkout.

   Fix: Normalize paths, pin the complete environment, and add a clean-room reproducibility check comparing generated manifests and hashes.

## Claims checked and found SOUND

- Library composition is 77 compounds: 22 custom and 55 FDA, with PubChem CIDs/URLs for all 77; `drug_like_count` is 58.
- Wide/tight docking counts are 73/77 and 72/77; four boron compounds fail MMFF parameterization and vancomycin is absent from the tight ranking.
- Affinity ranges, custom/FDA means, top-20 composition of 7 custom plus 13 FDA, and the −6.33 kcal/mol bortezomib-surrogate result match their JSONs.
- The bootstrap CIs and two-sided Mann–Whitney values were independently reproduced exactly: wide p = 0.32125, CI [−0.3335, 0.7189]; tight p = 0.26339, CI [−0.1561, 0.7412]. No multiple-testing correction is applied, but no positive significance claim is made.
- Benzamidine is recorded as +1 and ranks 67/73 by current wide-box affinity.
- Charge propagation itself works: all 73 ligand-PDBQT hashes match the manifests, and all 146 wide-box pose files retain partial-charge sums consistent with their recorded formal charge; benzamidine sums to +1.001 and pentamidine to +2.001.
- SpeB’s box is computed exclusively from seven Cys192/His340 side-chain atoms, not Q9D coordinates.
- The SpeB panel contains Q9D plus 19 comparators within 22–28 heavy atoms versus Q9D’s 25; two are labelled protease comparators, leaving 17 decoys.
- Q9D’s JSON values are correct: −6.695 kcal/mol, affinity rank 6/20, efficiency rank 7/20, and approximately 0.8/0.5 decoy SD. All 20 local pose scores match the JSON.
- The historical 4.4-SD result, Q9D-centred box, and 11.9-heavy-atom mean of the seven old comparators are recoverable from HEAD.
- Receptor QC currently records 81 and 24 omitted residues with no catalytic residue missing; the side-chain-only tight boxes are 16 Å for both receptors.
- Forty of 73 current prepared compounds have nonzero net formal charge, versus zero charged PubChem source depictions; 11 of 22 custom compounds contain amidine/guanidine systems.
- Thirteen compounds with unspecified stereocentres is the correct count, although the claimed recorded isomer is not.
- AutoDock Vina is actually v1.2.7 and Meeko is 0.7.1.

VERDICT: REVISE
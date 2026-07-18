# Resume: launch campaign 3 (when back at a stable, plugged-in machine)

**Status 2026-07-18:** the transient-spawn-retry fix is built, verified (261 tests pass), committed (`1bc3a24`) and
pushed. Campaigns 1 and 2 both died in stage 1 (WIDE) — attempt 1 to a sleep (fixed), attempt 2 to the transient vina
crash (this fix). **Nothing is running.** Launch campaign 3 only when the laptop can stay **awake + on AC + not moved
for 10–15 h**.

## Preconditions (all must hold)
- On **AC power** (battery still sleeps — only AC sleep vectors were disabled).
- Plugged in and stationary the whole run; lid may be closed (AC lid-close is set to "do nothing").
- Consider pausing Windows Update so a forced reboot can't kill the run.

## Launch (fresh calibration + campaign, NEW id each time)
Pick a fresh id (calibrations/campaigns are immutable; reuse is refused). Example `v2_20260722`:

```bash
cd ~/OneDrive/Documents/SpyCEP-Drug-Discovery

# 1. Fresh 10-min calibration (must PASS; proves the host isn't sleeping/drifting)
SPYCEP_CAMPAIGN_ID=v2_20260722 ./.venv/Scripts/python.exe scripts/calibrate_suspend.py
#   -> writes docs/methods/suspend_calibration_v2_20260722.json on PASS

# 2. Launch the 4-stage campaign (~10-15 h) under the SAME id
SPYCEP_CAMPAIGN_ID=v2_20260722 \
SPYCEP_SUSPEND_CALIBRATION_PATH=docs/methods/suspend_calibration_v2_20260722.json \
./run_campaign.sh
#   -> WIDE -> TIGHT -> SPEB -> BORON, then the seal step
```

If a stale `.campaign.lock` blocks step 2 (OneDrive can hold it): `rmdir .campaign.lock` then retry.

## If campaign 3 ALSO aborts on `transient_spawn_failure_exhausted`
That confirms the failure is **cumulative desktop-heap exhaustion**, not a momentary blip (the ADR-0003 caveat). The
evidence-backed next step is then a desktop-heap headroom increase (registry `SharedSection` + reboot) — a new fix,
not a retry.

## After a SUCCESSFUL campaign — recompute headlines + revert power settings
- §H18: recompute the frozen headlines (Mann–Whitney population, top candidates, SpeB control, 67/53/31 triad ranges)
  on clean v2 data and check whether any disposition changed vs the pre-fix numbers.
- Revert the two power-setting changes made 2026-07-18 (both AC-only, reversible):
  ```
  powercfg /setacvalueindex SCHEME_CURRENT 4f971e89-eebd-4455-a8de-9e59040e7347 5ca83367-6e45-459f-a27b-476b1d01c936 1
  powercfg /setacvalueindex SCHEME_CURRENT 238c9fa8-0aad-41ed-83f4-97be242c8f20 7bc4a2f9-d8fc-4469-b07b-33eb785aaca0 120
  powercfg /setactive SCHEME_CURRENT
  ```

## What got built this session (all committed + pushed on `remediation-2026-07-13`)
- Pre-campaign suspend-calibration harness (7-round Codex review) + host calibrated.
- All four AC sleep vectors closed (lid / idle / hibernate / unattended-timeout).
- Transient-spawn-retry fix (5-round Codex review): allowlist classifier, bounded retry, fail-closed exhaustion,
  per-campaign ledger + seal barrier, run-record schema v3. See `PLAN-retry-fix.md` + `PLAN-REVIEW-LOG-retry-fix.md`.

#!/bin/bash
# Stage 2 clean redock — NO --resume. Frozen: seed 42, exh 8, num_modes 9, --cpu 1, 1800s.
set -u

PY=./.venv/Scripts/python.exe
LOCKDIR=.campaign.lock

# The schema-v2 entry points refuse to start without BOTH of these. Require them from
# the environment rather than hardcoding: an ID baked into this script gets silently
# reused on the next run, and PLAN-timeout-fix.md §H17 forbids cross-campaign reuse.
#   SPYCEP_CAMPAIGN_ID=v2_20260716 \
#   SPYCEP_SUSPEND_CALIBRATION_PATH=docs/methods/suspend_calibration.json \
#   ./run_campaign.sh
: "${SPYCEP_CAMPAIGN_ID:?Set a fresh campaign id per campaign (PLAN-timeout-fix.md §H17)}"
: "${SPYCEP_SUSPEND_CALIBRATION_PATH:?Set the pre-campaign calibration artifact path (§H9)}"
export SPYCEP_CAMPAIGN_ID SPYCEP_SUSPEND_CALIBRATION_PATH

# Early diagnostic only.  Every Python entry point repeats this comparison against
# the record returned by the real validator, so direct invocation remains bound too.
if ! "$PY" -c 'import sys; from pathlib import Path; sys.path.insert(0, "src"); from spycep_drug_discovery.docking import require_campaign_id, require_suspend_calibration; campaign_id = require_campaign_id(); record = require_suspend_calibration(Path.cwd()); record.get("campaign_id") == campaign_id or sys.exit("Suspend calibration campaign_id does not match SPYCEP_CAMPAIGN_ID.")'; then
    echo "REFUSING TO START: suspend calibration validation or campaign binding failed."
    exit 1
fi

CAMPAIGN_ROOT="results/docking/campaign_${SPYCEP_CAMPAIGN_ID}"

# Campaigns are immutable and never resumed. Python enforces this per-attempt
# (attempt_dir.mkdir(exist_ok=False)), which aborts mid-stage after real work; fail
# up front instead so a reused ID costs seconds rather than hours.
if [ -e "$CAMPAIGN_ROOT" ]; then
    echo "REFUSING TO START: $CAMPAIGN_ROOT already exists — pick a new SPYCEP_CAMPAIGN_ID."
    echo "Campaigns are immutable and are never resumed (PLAN-timeout-fix.md §H17)."
    exit 1
fi

# Single-instance guard. A concurrent second campaign races the first on identical
# output paths and inflates every elapsed_seconds, which fabricates `cause: timeout`
# dispositions (this happened on 2026-07-14: clindamycin@5XYA).
if ! mkdir "$LOCKDIR" 2>/dev/null; then
    echo "REFUSING TO START: $LOCKDIR exists — a campaign is already running."
    echo "If you are certain none is, remove it: rmdir $LOCKDIR"
    exit 1
fi
trap 'rmdir "$LOCKDIR" 2>/dev/null' EXIT

# Run one stage. $? after a pipeline is the LAST command's status (tail), never the
# script's — so read PIPESTATUS[0] and abort loudly instead of logging a false exit=0.
run_stage () {
    local label="$1"; shift
    echo "--- $label ---"
    "$@" 2>&1 | tail -5
    local rc=${PIPESTATUS[0]}
    echo "$label exit=$rc"
    if [ "$rc" -ne 0 ]; then
        echo "=== CAMPAIGN ABORTED: $label failed (exit $rc) at $(date) ==="
        exit "$rc"
    fi
}

echo "=== STAGE 2 CAMPAIGN START: $(date) ==="
echo "campaign_id   : $SPYCEP_CAMPAIGN_ID"
echo "campaign_root : $CAMPAIGN_ROOT"
echo "calibration   : $SPYCEP_SUSPEND_CALIBRATION_PATH"
echo "code          : $(git rev-parse --short HEAD 2>/dev/null || echo unknown)$(git diff --quiet 2>/dev/null || echo ' -DIRTY')"
run_stage "[1/4] WIDE (154 attempts)"  $PY scripts/run_docking.py
run_stage "[2/4] TIGHT (154 attempts)" $PY scripts/run_docking.py --tight
run_stage "[3/4] SPEB (23 attempts)"   $PY scripts/run_speb_positive_control.py
run_stage "[4/4] BORON (8 attempts)"   $PY scripts/dock_boron_surrogates.py
echo "=== STAGE 2 CAMPAIGN DONE: $(date) ==="

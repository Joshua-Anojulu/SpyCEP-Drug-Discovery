#!/bin/bash
# Stage 2 clean redock — NO --resume. Frozen: seed 42, exh 8, num_modes 9, --cpu 1, 1800s.
set -u

PY=./.venv/Scripts/python.exe
LOCKDIR=.campaign.lock

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
run_stage "[1/4] WIDE (154 attempts)"  $PY scripts/run_docking.py
run_stage "[2/4] TIGHT (154 attempts)" $PY scripts/run_docking.py --tight
run_stage "[3/4] SPEB (23 attempts)"   $PY scripts/run_speb_positive_control.py
run_stage "[4/4] BORON (8 attempts)"   $PY scripts/dock_boron_surrogates.py
echo "=== STAGE 2 CAMPAIGN DONE: $(date) ==="

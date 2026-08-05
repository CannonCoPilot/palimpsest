#!/bin/bash
# Step 5 of the round, chained to fire when the R3 pass finishes: re-measure ALL 50 and rebuild the report.
#
# Waits on the LEDGER LINE, not on a PID. A pid wait says "the process I started ended", which is also true
# when it dies; the ledger's own COMPLETE line is written by the runner only after its last chapter returns,
# so it distinguishes finished from died. If the runner dies the line never appears and this waits — visible
# in the log as a stall, which is the correct failure mode for a chained job (a chained job that proceeds on
# a dead predecessor measures a half-finished board and reports it as the round's result).
HERE="$(cd "$(dirname "$0")" && pwd)"
cd "$HERE" || exit 1
LEDGER="$HERE/.campaign/r3-ledger.txt"
LOG="$HERE/.campaign/after-r3.log"
PY="$HERE/../ocr-venv/bin/python"

echo "$(date +%H:%M) waiting for R3 PASS v3 COMPLETE" > "$LOG"
for _ in $(seq 1 720); do                       # 720 x 10s = 2h ceiling, then give up loudly
  grep -q "R3 PASS v3 COMPLETE" "$LEDGER" && break
  sleep 10
done
if ! grep -q "R3 PASS v3 COMPLETE" "$LEDGER"; then
  echo "$(date +%H:%M) GAVE UP — the pass never wrote COMPLETE. NOT re-measuring." >> "$LOG"
  exit 3
fi

echo "$(date +%H:%M) R3 done — re-measuring all 50" >> "$LOG"
PYTORCH_ENABLE_MPS_FALLBACK=1 "$PY" chapter_campaign.py --chapters 1-50 --phase measure >> "$LOG" 2>&1
echo "$(date +%H:%M) rebuilding report" >> "$LOG"
PYTORCH_ENABLE_MPS_FALLBACK=1 "$PY" build_reocr_report.py --stage pilot \
  --campaign-note "left-bound fix on 162 leaves + margin-mark filter + R3 pass on 17 stale chapters" >> "$LOG" 2>&1
echo "$(date +%H:%M) DONE" >> "$LOG"

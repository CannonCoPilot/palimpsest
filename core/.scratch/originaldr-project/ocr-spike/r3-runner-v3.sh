#!/bin/bash
# r3-runner-v3.sh — sequential R3 residual pass over a chapter list.
#
# Replaces r3-runner-v2.sh, which the docs reference and which is not on disk. v2 was a
# POLLING runner: the recovered ledger shows 297 consecutive "no chapter ready — waiting
# for the breadth measurement" lines over 1h35m. This one takes an explicit chapter list
# and does the work, so an idle ledger means a real stall rather than a design choice.
#
# HARD CONSTRAINT: one 17GB olmOCR at a time. The loop is sequential and holds an
# mkdir lock carrying an owner token, so a stale lock can be attributed (see the
# trap-TERM/lock-ownership gotcha: a trap that strips a lock it does not own is worse
# than no lock).
#
# Usage: ./r3-runner-v3.sh 31 13 20 7 ...

HERE="$(cd "$(dirname "$0")" && pwd)"
cd "$HERE" || exit 1
LOCK="$HERE/.campaign/r3-runner.lock"
LEDGER="$HERE/.campaign/r3-ledger.txt"
PY="$HERE/../ocr-venv/bin/python"
TOKEN="$$@$(hostname -s)"

if ! mkdir "$LOCK" 2>/dev/null; then
  echo "LOCKED by $(cat "$LOCK/owner" 2>/dev/null || echo unknown) — refusing to run a second olmOCR"
  exit 3
fi
echo "$TOKEN" > "$LOCK/owner"

release() {
  # Only remove the lock if it is still OURS.
  if [ "$(cat "$LOCK/owner" 2>/dev/null)" = "$TOKEN" ]; then
    rm -rf "$LOCK"
  fi
}
trap 'release; exit 130' INT TERM
trap 'release' EXIT

log() { echo "$(date +%H:%M) $*" | tee -a "$LEDGER"; }

log "R3 PASS v3 START — chapters: $*  (owner $TOKEN)"
for ch in "$@"; do
  log "START ch $ch"
  PYTORCH_ENABLE_MPS_FALLBACK=1 "$PY" chapter_campaign.py --chapters "$ch" --phase r3 \
    >> "$HERE/.campaign/r3-run-ch${ch}.log" 2>&1
  rc=$?
  log "done ch $ch rc=$rc"
done
log "R3 PASS v3 COMPLETE"

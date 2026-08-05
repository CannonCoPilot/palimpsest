#!/bin/bash
# Alert only if the 6-worker OCR load induces SUSTAINED active swapping. Exits when OCR pid dies.
PID=85037
prev=$(vm_stat | awk '/Swapouts/{gsub(/\./,"",$2); print $2}')
while kill -0 "$PID" 2>/dev/null; do
  sleep 120
  cur=$(vm_stat | awk '/Swapouts/{gsub(/\./,"",$2); print $2}')
  free=$(sysctl -n vm.swapusage | sed -E 's/.*free = ([0-9.]+)M.*/\1/')
  delta=$(( cur - prev ))
  # ~20000 pages * 16KB = ~320MB swapped out in 120s = real thrash worth flagging
  if [ "$delta" -gt 20000 ]; then
    echo "MEM-TRIPWIRE: active swapping delta=${delta}pages/120s swap_free=${free}M pid=$PID $(date '+%H:%M:%S')"
  fi
  prev=$cur
done
echo "MEM-TRIPWIRE: OCR pid $PID ended, tripwire exiting $(date '+%H:%M:%S')"

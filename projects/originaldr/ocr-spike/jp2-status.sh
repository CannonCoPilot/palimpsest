#!/bin/bash
# jp2 re-OCR status dashboard — read-only. Run:  bash jp2-status.sh
# Live loop:  while true; do clear; bash jp2-status.sh; sleep 30; done
# Adapted from ocr-status.sh for the hi-res jp2 re-OCR run (jp2:S06 + jp2:S08).
cd "$(dirname "$0")/../../../.." 2>/dev/null   # -> palimpsest root
ROOT=projects/originaldr/sources/our-ocr-diplomatic
LOG=projects/originaldr/ocr-spike/jp2-reocr.log
PIDFILE=projects/originaldr/ocr-spike/.jp2-reocr-pid
TARGET=3672                 # S06 2872 + S08 800
PREFIX=jp2-                 # only count/monitor the jp2-* line dirs
export OCR_BATCH=8          # matches the run's BATCH (for inflight->pages estimate)
PID=$(cat "$PIDFILE" 2>/dev/null)

echo "======== jp2 RE-OCR STATUS  $(date '+%Y-%m-%d %H:%M:%S') ========"

# --- run state ---
if [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null; then
  echo "run:      ALIVE  PID=$PID  age=$(ps -o etime= -p "$PID" | tr -d ' ')"
else
  echo "run:      NOT RUNNING (pid=$PID) — finished or stopped"
fi

# --- pages / progress (jp2-* dirs only) ---
TOT=0
for d in "$ROOT"/${PREFIX}*/; do
  [ -d "$d" ] || continue
  n=$(find "$d" -name '*.json' 2>/dev/null | grep -v _manifest | wc -l | tr -d ' ')
  TOT=$((TOT + n))
done
printf "pages:    %s / %s  (%.1f%%)\n" "$TOT" "$TARGET" "$(awk "BEGIN{print $TOT/$TARGET*100}")"
for d in "$ROOT"/${PREFIX}*/; do
  [ -d "$d" ] || continue
  n=$(find "$d" -name '*.json' 2>/dev/null | grep -v _manifest | wc -l | tr -d ' ')
  printf "            %-22s %s\n" "$(basename "$d")" "$n"
done

# --- throughput + ETA (from newest log progress line) ---
RATE=$(grep -E "pg/s" "$LOG" 2>/dev/null | tail -1 | grep -oE "[0-9.]+ pg/s" | grep -oE "[0-9.]+")
LASTLINE=$(grep -E "done=|COMPLETE" "$LOG" 2>/dev/null | tail -1)
echo "log:      ${LASTLINE:-<no progress line yet>}"
if [ -n "$RATE" ] && awk "BEGIN{exit !($RATE>0)}"; then
  REM=$((TARGET - TOT))
  printf "eta:      ~%.1f h  (%s pages left @ %s pg/s)\n" "$(awk "BEGIN{print $REM/$RATE/3600}")" "$REM" "$RATE"
fi

# --- recent completed pages + in-flight frontier + output validity (python: stdlib only) ---
LINE_PREFIX="$PREFIX" python3 - "$ROOT" "$LOG" 2>/dev/null <<'PY' || echo "detail:   <python check unavailable>"
import json, os, sys, re, heapq
root, log = sys.argv[1], sys.argv[2]
S = "ſ"  # long-s (ſ): the glyph this whole diplomatic pipeline exists to preserve
pref = os.environ.get("LINE_PREFIX", "jp2-")
try:
    batch = int(os.environ.get("OCR_BATCH", "8"))
except ValueError:
    batch = 8

ents = []
for dn in os.listdir(root):
    if not dn.startswith(pref):
        continue
    d = os.path.join(root, dn)
    if not os.path.isdir(d):
        continue
    for f in os.listdir(d):
        if f.endswith(".json") and not f.startswith("_manifest"):
            p = os.path.join(d, f)
            try:
                ents.append((os.stat(p).st_mtime, dn, f, p))
            except OSError:
                pass
if not ents:
    print("recent:   <no output yet>")
    sys.exit(0)
newest = heapq.nlargest(40, ents, key=lambda t: t[0])

def pageno(name):
    m = re.search(r"_(\d+)\.json$", name)
    return m.group(1) if m else name[-10:-5]

def load(p):
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)

print(f"recent:   newest completed (line | page | lines | {S}-count | text)")
for _, dn, f, p in newest[:6]:
    try:
        d = load(p); L = d.get("lines", [])
        s = sum(ln.get("text", "").count(S) for ln in L)
        snip = next((ln.get("text", "") for ln in L if ln.get("text", "").strip()), "")
        snip = re.sub(r"\s+", " ", snip)[:42]
        print(f"          {dn:<16} {pageno(f):>5} {len(L):>3}ln {S}{s:<3} \"{snip}\"")
    except Exception as e:
        print(f"          {dn:<16} {pageno(f):>5} <unreadable: {e}>")

# current activity: the log's LAST line-event is the sequential truth (output is bursty:
# a batch writes its N files only on completion, so newest-written file lags by up to a batch).
lastev = ""
try:
    with open(log, encoding="utf-8", errors="ignore") as fh:
        for ln in fh:
            t = ln.strip()
            if t.startswith("[" + pref):
                lastev = t
except OSError:
    pass
m = re.match(r"\[(" + re.escape(pref) + r"[\w-]+)\]\s+(.*)", lastev)
if not m:
    print("analyzing: <no activity line yet>")
elif m.group(2).startswith("COMPLETE"):
    print(f"analyzing:[{m.group(1)}] COMPLETE -- next line warming up "
          f"(first batch ~1min; output is bursty per {batch}-page batch)")
else:
    lk, rest = m.group(1), m.group(2)
    infm = re.search(r"inflight=(\d+)", rest)
    infl = infm.group(1) if infm else "?"
    maxn = -1
    for f in os.listdir(os.path.join(root, lk)):
        mm = re.search(r"_(\d+)\.json$", f)
        if mm:
            maxn = max(maxn, int(mm.group(1)))
    est = f" (~{int(infl) * batch} pages)" if infl.isdigit() else ""
    front = f"_{maxn:04d}" if maxn >= 0 else "?"
    print(f"analyzing:[{lk}] inflight={infl} batches{est} | frontier~{front} (next uncached)")

sample = newest[:30]
ok = blank = bad = swith = stot = 0
bad_ex = []
for _, dn, f, p in sample:
    try:
        d = load(p)
        L = d.get("lines")
        if not (isinstance(d, dict) and isinstance(d.get("page"), str) and isinstance(L, list)):
            bad += 1; bad_ex.append(pageno(f)); continue
        good = True; sh = 0
        for ln in L:
            if not (isinstance(ln, dict) and isinstance(ln.get("bbox"), list)
                    and len(ln["bbox"]) == 4 and all(isinstance(v, int) for v in ln["bbox"])
                    and isinstance(ln.get("text"), str)):
                good = False; break
            sh += ln["text"].count(S)
        if not good:
            bad += 1; bad_ex.append(pageno(f)); continue
        if L:
            ok += 1
        else:
            blank += 1
        if sh > 0:
            swith += 1
        stot += sh
    except Exception:
        bad += 1; bad_ex.append(pageno(f))
n = len(sample)
flags = ""
if ok > 0 and swith == 0:
    flags += f"  ** {S}=0 across sample -- CHECK glyph collapse **"
if bad > 0:
    flags += f"  ** {bad} MALFORMED: {','.join(bad_ex[:5])} **"
print(f"valid:    sampled {n} newest | ok={ok} blank={blank} bad={bad} | "
      f"{S} on {swith}/{n} pages, {stot} total{flags}")
PY

# --- workers + OCR memory ---
if [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null; then
  NW=$(pgrep -f 'bin/kraken' 2>/dev/null | wc -l | tr -d ' ')
  OCRKB=$(ps -axo pid,ppid,rss | awk -v p="$PID" '
    NR==1{next}
    {rss[$1]=$3; par[$1]=$2}
    END{
      t=0
      for(pid in par){ q=pid; d=0
        while(q!="" && q!=1 && d<6){ if(par[q]==p||q==p){t+=rss[pid]; break} q=par[q]; d++ } }
      print t
    }')
  printf "workers:  %s kraken  |  OCR footprint ~%.1f GB\n" "$NW" "$(awk "BEGIN{print $OCRKB/1048576}")"
fi

# --- box memory / swap / active swapping ---
MEM=$(top -l 1 -n 0 2>/dev/null | grep PhysMem)
SWAP=$(sysctl -n vm.swapusage 2>/dev/null | sed -E 's/total = //; s/  used/ used/')
S1=$(vm_stat | awk '/Swapouts/{gsub(/\./,"",$2);print $2}'); sleep 2
S2=$(vm_stat | awk '/Swapouts/{gsub(/\./,"",$2);print $2}')
echo "box:      $MEM"
echo "swap:     $SWAP"
D=$((S2-S1)); [ "$D" -gt 0 ] && echo "          ** ACTIVE SWAPPING: +${D} pages/2s **" || echo "          (no active swapping)"
echo "=================================================="

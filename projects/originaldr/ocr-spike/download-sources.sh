#!/bin/bash
# Sequential download of the 8 missing DR scan sources into the organized sources/ tree.
SRC=/Users/nathanielcannon/Claude/Projects/palimpsest/imports/Scripture/Bibles/DouayRheims_DR/sources
LOG="$SRC/../download.log"
: > "$LOG"
dl() {  # id  dir  url
  local id="$1" dir="$2" url="$3"
  mkdir -p "$SRC/$dir"
  local out="$SRC/$dir/$id.pdf"
  echo "[$(date '+%H:%M:%S')] START $id -> $dir" | tee -a "$LOG"
  curl -sL -C - --retry 3 --retry-delay 5 -o "$out" "$url" 2>>"$LOG"
  local sz=$(stat -f '%z' "$out" 2>/dev/null || echo 0)
  echo "[$(date '+%H:%M:%S')] DONE  $id  $((sz/1024/1024)) MB" | tee -a "$LOG"
}
dl S02 S02_1609-douay-ot-hires        "https://archive.org/download/1609douayoldtestament1/1635%20Douay%20Old%20Testament%201.pdf"
dl S03a S03_holie-bible-engl-ot-vol1  "https://archive.org/download/holiebiblefaithf01engl/holiebiblefaithf01engl.pdf"
dl S03b S03_holie-bible-engl-ot-vol2  "https://archive.org/download/holiebiblefaithf02engl/holiebiblefaithf02engl.pdf"
dl S04 S04_1633-rheims-nt             "https://archive.org/download/1582douayrheimsnt/1582%20Douay%20Rheims%20NT.pdf"
dl S06 S06_1610-facsimile-whole       "https://archive.org/download/1610A.d.DouayOldTestament1582A.d.RheimsNewTestament_176/Douay-Rheims-1610-Bible.pdf"
dl S07 S07_1635-facsimile-whole       "https://archive.org/download/coverdale-bible-1535/1610%20A.D.%20Douay%20Old%20Testament%2C%201582%20A.D.%20Rheims%20New%20Testament%20%28Printed%201635%20A.D.%29.pdf"
dl S08 S08_1582-rhemes-nt-hires       "https://archive.org/download/1582RhemesNewTestament/1582_Rhemes_New_Testament.pdf"
dl S09nt S09_nevvtestament-mart-nt    "https://archive.org/download/nevvtestamentofi00mart/nevvtestamentofi00mart.pdf"
echo "[$(date '+%H:%M:%S')] ALL DOWNLOADS COMPLETE" | tee -a "$LOG"

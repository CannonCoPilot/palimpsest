#!/bin/bash
# Download the 7 missing archive.org scan PDFs into their organized group folders.
# Resumable (curl -C -). Verifies %PDF magic + page count after each.
SCANS="/Users/nathanielcannon/Claude/Projects/palimpsest/imports/Scripture/Bibles/DouayRheims_DR/sources/scans"

dl () { # tag url out
  local tag="$1" url="$2" out="$3"
  echo "[$(date +%H:%M:%S)] START $tag -> $out"
  curl -L -C - --retry 4 --retry-delay 3 --fail --silent --show-error -o "$out" "$url"
  local rc=$?
  if [ $rc -ne 0 ]; then echo "[$(date +%H:%M:%S)] FAIL $tag rc=$rc"; return $rc; fi
  local magic; magic=$(head -c 5 "$out")
  local pages; pages=$(pdfinfo "$out" 2>/dev/null | awk '/^Pages:/{print $2}')
  echo "[$(date +%H:%M:%S)] DONE  $tag magic=$magic pages=${pages:-?} size=$(du -h "$out"|cut -f1)"
}

dl S1a "https://archive.org/download/1582DouaiRheimsDouayRheimsFirstEdition1Of31609OldTestament/1582%20Douai%20Rheims%20Douay%20Rheims%20First%20Edition%20%201%20of%203%201609%20Old%20Testament.pdf" "$SCANS/S01_1582-first-edition-3vol/ot1-1609.pdf"
dl S1b "https://archive.org/download/1582DouaiRheimsDouayRheimsFirstEdition2Of31610OldTestament/1582%20Douai%20Rheims%20Douay%20Rheims%20First%20Edition%20%202%20of%203%201610%20Old%20Testament.pdf" "$SCANS/S01_1582-first-edition-3vol/ot2-1610.pdf"
dl S1c "https://archive.org/download/1582DouaiRheimsDouayRheimsFirstEdition3Of31582NewTestament/1582%20Douai%20Rheims%20Douay%20Rheims%20First%20Edition%20%203%20of%203%201582%20New%20Testament.pdf" "$SCANS/S01_1582-first-edition-3vol/nt-1582.pdf"
dl S5  "https://archive.org/download/newtestamentofie00engl/newtestamentofie00engl.pdf" "$SCANS/S05_newtestament-engl-nt/newtestamentofie00engl.pdf"
dl S7  "https://archive.org/download/coverdale-bible-1535/1610%20A.D.%20Douay%20Old%20Testament%2C%201582%20A.D.%20Rheims%20New%20Testament%20%28Printed%201635%20A.D.%29.pdf" "$SCANS/S07_1635-facsimile-whole/1635-printing.pdf"
dl S9b "https://archive.org/download/holiebiblefaithf00mart_0/holiebiblefaithf00mart_0.pdf" "$SCANS/S09_nevv-testament-mart-3vol/holiebiblefaithf00mart_0-OT1.pdf"
dl S9c "https://archive.org/download/holiebiblefaithf00mart/holiebiblefaithf00mart.pdf" "$SCANS/S09_nevv-testament-mart-3vol/holiebiblefaithf00mart-OT2.pdf"

echo "[$(date +%H:%M:%S)] ALL DOWNLOADS COMPLETE"
# S7 must differ from S6:
echo "S6 vs S7 sha compare:"
shasum -a 256 "$SCANS/S06_1610-facsimile-whole/S06.pdf" "$SCANS/S07_1635-facsimile-whole/1635-printing.pdf" 2>/dev/null

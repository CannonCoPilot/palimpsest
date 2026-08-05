#!/usr/bin/env python3
"""gt_match_report.py — Sir's report rules E2/E4/E5a: per-SOURCE OCR-vs-Gold-Transcript scoring.

Distinct from qc_audit (which scores each source vs the reference READS): here every curated source's
OCR is scored against the GOLD TRANSCRIPT itself, on the canonical (s_dismas) coordinate system that both
the GT (verses_aligned) and the source OCR (realign_vmap) share. Reuses qc_audit's per-source extraction
machinery verbatim so the detection/alignment is identical to production.

Flags (Sir 2026-07-19):
  E4  a source is flagged for reOCR of a book if ANY chapter fails — chapter passes iff
      (verses matching GT >= 0.90) / scoreable-verses  >= 0.90.
  E5a a source is flagged if the book as a whole (all verses combined) matches < 0.90 of verses.
Emits the source x book PASS/FAIL matrix (report rule E2: a row per source that does/should contain the book).

Run: ocr-venv/bin/python ocr-spike/gt_match_report.py [book ...]   (default: all GT-covered books)
"""
from __future__ import annotations
import json, re, sys, glob, os
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import qc_audit as Q                         # reuse its loaders/detection/alignment
from char_identity import fold_archaic, edit_ratio

PASS = 0.90
GT_DIR = HERE / "ground-truth"
# curated sources per testament (Sir's curation; S6-NT dropped)
OT_SRC = ["S1", "S3", "S6", "S9"]
NT_SRC = ["S1", "S4", "S8", "S9"]


def load_gt():
    """{book: {(ch,v): gt_text}} from every scripture GT's verses_aligned (canonical, non-empty)."""
    gt = defaultdict(dict)
    skipped = []
    for f in glob.glob(str(GT_DIR / "scripture-*.json")):
        d = json.loads(Path(f).read_text())
        locus = d.get("locus", "")
        m = re.match(r"scripture/([a-z0-9-]+)/", str(locus))
        if not m:
            continue
        book = m.group(1)
        va = d.get("verses_aligned") or {}
        n = 0
        for k, txt in va.items():
            if not isinstance(txt, str) or not txt.strip():
                continue
            cm = re.match(r"^(\d+):(\d+)$", k)
            if not cm:
                continue
            gt[book][(int(cm.group(1)), int(cm.group(2)))] = txt
            n += 1
        if n == 0:
            skipped.append(os.path.basename(f))
    return gt, skipped


def source_vmap(book, wid, anchor_ch, by_source):
    """canonical {(ch,v): ocr_text} for one source's OCR of `book` — qc_audit's L300-318 logic."""
    w = by_source.get(wid)
    if not w or w.get("kind") != "scan":
        return None, None
    best = None
    for ocr_dir in Q.scan_ocr_dirs(w):
        stm = Q.stream_for(ocr_dir)
        if stm is None:
            continue
        reads, _, meta = Q.D.detect_book(book, anchor_ch, wid, {ocr_dir: stm})
        if not meta.get("covered"):
            continue
        if best is None or (meta.get("probe_recall") or 0) > (best["meta"].get("probe_recall") or 0):
            best = {"meta": meta, "vmap": Q.verse_texts_from_reads(reads, book), "ocr_dir": ocr_dir}
    if best is None:
        return None, None
    vmap = Q.realign_vmap(best["vmap"], book) if Q.ALIGN_COORDS else best["vmap"]
    return vmap, best["ocr_dir"]


def main(argv):
    gt, skipped = load_gt()
    ordinals = Q.load_book_ordinals()
    anchor_bb = Q.D.anchor_by_book(Q.D.load_anchor())
    msl = json.loads(Q.MSL.read_text())
    by_source = {w["source"]: w for w in msl["witnesses"]}

    books = argv or sorted(gt)
    if skipped:
        print(f"note: {len(skipped)} GT file(s) skipped (no verses_aligned): {skipped}")

    matrix = {}     # book -> {source -> verdict}
    for book in books:
        if book not in gt:
            print(f"  ! {book}: no GT verses_aligned — skip"); continue
        binfo = ordinals.get(book)
        testament = binfo["testament"] if binfo else "?"
        anchor_ch = anchor_bb.get(book, {})
        gtv = gt[book]
        srcs = OT_SRC if testament == "OT" else NT_SRC
        matrix[book] = {}
        for wid in srcs:
            vmap, ocr_dir = source_vmap(book, wid, anchor_ch, by_source)
            if vmap is None:
                matrix[book][wid] = {"status": "no-ocr", "ocr_dir": None}
                continue
            # score every GT verse this source's OCR also carries
            by_ch = defaultdict(lambda: [0, 0])   # ch -> [pass, total]
            allp = allt = 0
            for (ch, v), gtext in gtv.items():
                if (ch, v) not in vmap:
                    continue
                g = fold_archaic(gtext)
                if not g:
                    continue
                s = edit_ratio(fold_archaic(vmap[(ch, v)]), g)
                by_ch[ch][1] += 1; allt += 1
                if s >= PASS:
                    by_ch[ch][0] += 1; allp += 1
            if allt == 0:
                matrix[book][wid] = {"status": "no-overlap", "ocr_dir": ocr_dir}
                continue
            ch_fracs = {ch: (p / t) for ch, (p, t) in by_ch.items()}
            failed_ch = sorted(ch for ch, fr in ch_fracs.items() if fr < PASS)   # E4
            book_frac = allp / allt
            e4 = len(failed_ch) > 0
            e5a = book_frac < PASS
            matrix[book][wid] = {
                "status": "scored", "ocr_dir": ocr_dir,
                "verses_scored": allt, "verses_pass": allp, "book_frac": round(book_frac, 4),
                "chapters": {ch: round(fr, 3) for ch, fr in ch_fracs.items()},
                "reocr_flag": bool(e4 or e5a), "E4_chapter_fail": failed_ch, "E5a_book_fail": e5a,
            }

    # ---- render matrix ----
    print("\n" + "=" * 78)
    print("SOURCE x BOOK — OCR vs GOLD TRANSCRIPT  (PASS = no reOCR flag; ✗ = flagged)")
    print("=" * 78)
    all_src = ["S1", "S3", "S4", "S6", "S8", "S9"]
    print(f"{'book':16} " + " ".join(f"{s:>7}" for s in all_src))
    for book in books:
        if book not in matrix:
            continue
        cells = []
        for s in all_src:
            r = matrix[book].get(s)
            if r is None:
                cells.append(f"{'—':>7}")
            elif r["status"] != "scored":
                cells.append(f"{r['status'][:7]:>7}")
            else:
                tag = "✗" if r["reocr_flag"] else "PASS"
                cells.append(f"{tag+' '+str(int(r['book_frac']*100)):>7}")
        print(f"{book:16} " + " ".join(cells))
    print("\n  legend: 'PASS NN' = NN% verses match GT ≥.90, no flag · '✗ NN' = reOCR-flagged (E4/E5a)")
    print("          '—' source doesn't cover this testament · 'no-ocr'/'no-over(lap)' = detect miss")

    out = HERE / "gt-match-report.json"
    out.write_text(json.dumps({"pass_threshold": PASS, "matrix": matrix,
                               "skipped_gt_no_align": skipped}, indent=1, ensure_ascii=False))
    print(f"\nwrote {out.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

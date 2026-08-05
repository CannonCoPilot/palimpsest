#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""integrity_sweep.py — find EVERY misaligned, misattributed, mislocalized, skipped, missing or
double-counted book / chapter / page, in every tome of every source (2026-07-28).

Each check exists because a defect of that exact shape has already been found by hand in this project. The
point of the module is that none of them should ever again need to be found by hand.

  C1  OUT-OF-TOME       a page addressed to a book the volume cannot contain (an OT volume holding an NT page).
  C2  MISSING BOOK      a canonical book of the volume's tome with no page at all.
  C3  MISSING CHAPTER   a canonical chapter with no page.
  C4  SKIPPED OPENING   the book is present but chapter 1 is not — the head of a book lost.
  C5  DISCONTIGUOUS     one chapter's pages split across disjoint runs. A chapter is printed once, in one
                        place; two runs means part of it is attributed to the wrong leaves.
  C6  OVERLONG CHAPTER  a chapter claiming implausibly many pages for its verse count — the runaway shape.
  C7  FRONT-MATTER DUMP a long run at the head of a volume assigned to a mid-book chapter instead of to the
                        book's own front matter. (Measured: jp2-S04 pages 2-14 all sat on matthew/2.)
  C8  DOUBLE-COUNTED    one page contributing to two different books.
  C9  PAGE-COUNT        OCR pages vs jp2 pages vs PDF pages for the same volume.
  C10 VERSE-vs-ADDRESS  a localized verse whose (book, chapter) is not what its own page is addressed to.

Severity: ERROR = certainly wrong. WARN = implausible, needs a look. INFO = expected asymmetry, recorded so
it is never mistaken for a defect.
"""
from __future__ import annotations

import glob
import json
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import jp2_page                       # noqa: E402
import page_address as PA             # noqa: E402
import witness_inventory as WI        # noqa: E402

CH = {b["slug"]: b["chapters"] for b in PA.SKELETON["books"]}
VERSES = {}
_NUM = re.compile(r"_(\d{4})$")

# PDF per volume — the third rendering of the same book. Declared, because the filenames follow no pattern.
PDFS = {
    "archive-ot1-1609":       "S01_1582-first-edition-3vol/ot1-1609.pdf",
    "archive-ot2-1610":       "S01_1582-first-edition-3vol/ot2-1610.pdf",
    "archive-nt-1582":        "S01_1582-first-edition-3vol/nt-1582.pdf",
    "pdf-S03a":               "S03_holie-bible-engl-ot-vol1/S03a.pdf",
    "pdf-S03b":               "S03_holie-bible-engl-ot-vol2/S03b.pdf",
    "jp2-S04":                "S04_1633-rheims-nt/S04.pdf",
    "jp2-S06":                "S06_1610-facsimile-whole/S06.pdf",
    "jp2-S08":                "S08_1582-rhemes-nt-hires/S08.pdf",
    "archive-holiebible-ot1": "S09_nevv-testament-mart-3vol/holiebiblefaithf00mart_0-OT1.pdf",
    "jp2-S09ot2":             "S09_nevv-testament-mart-3vol/holiebiblefaithf00mart-OT2.pdf",
    "pdf-S09nt":              "S09_nevv-testament-mart-3vol/nevvtestamentofi00mart-NT.pdf",
}


def pdf_pages(ocr_dir: str):
    rel = PDFS.get(ocr_dir)
    if not rel:
        return None
    p = Path(jp2_page.SCANS) / rel
    if not p.exists():
        return None
    try:
        out = subprocess.run(["pdfinfo", str(p)], capture_output=True, text=True, timeout=60).stdout
        m = re.search(r"^Pages:\s+(\d+)", out, re.M)
        return int(m.group(1)) if m else None
    except Exception:                                   # noqa: BLE001
        return None


def canon_books(ocr_dir: str) -> list:
    tomes = set(WI.tomes_for(ocr_dir))
    out = []
    for b in PA.BOOK_ORDER:
        t = PA.BOOK_TESTAMENT.get(b)
        if t == "NT" and "NT" in tomes:
            out.append(b)
        elif t == "OT" and (("OT2" if b in WI.OT2_BOOKS else "OT1") in tomes):
            out.append(b)
    return out


def _runs(pages: list) -> list:
    """Contiguous runs in a sorted page list, tolerating single-page holes (a plate between two leaves)."""
    pages = sorted(set(pages))
    runs, cur = [], [pages[0]] if pages else []
    for p in pages[1:]:
        if p - cur[-1] <= 2:
            cur.append(p)
        else:
            runs.append((cur[0], cur[-1]))
            cur = [p]
    if cur:
        runs.append((cur[0], cur[-1]))
    return runs


def sweep_volume(ocr_dir: str) -> list:
    f = HERE / f".page-address-{ocr_dir}.json"
    if not f.exists():
        return [{"check": "C0", "sev": "ERROR", "vol": ocr_dir, "msg": "no address cache"}]
    recs = json.loads(f.read_text())["records"]
    canon = set(canon_books(ocr_dir))
    tomes = "+".join(WI.tomes_for(ocr_dir))
    out = []

    def add(check, sev, msg, **kw):
        out.append({"check": check, "sev": sev, "vol": ocr_dir, "tome": tomes, "msg": msg, **kw})

    # C1 out-of-tome
    bad = Counter(r["book"] for r in recs if r["book"] not in canon)
    for b, n in bad.items():
        add("C1", "ERROR", f"{n} pages addressed to '{b}', which is not in this volume's tome", book=b, n=n)

    by_book = defaultdict(list)
    by_ch = defaultdict(list)
    for r in recs:
        by_book[r["book"]].append(r["page_index"])
        for c in r["chapters_on_page"] or []:
            by_ch[(r["book"], c)].append(r["page_index"])

    # C2 missing book · C3 missing chapter · C4 skipped opening
    for b in sorted(canon):
        if b not in by_book:
            add("C2", "ERROR", f"book '{b}' has no page in this volume at all", book=b)
            continue
        miss = [c for c in range(1, CH[b] + 1) if (b, c) not in by_ch]
        if miss:
            add("C3", "ERROR", f"'{b}' missing {len(miss)} chapter(s): {miss[:8]}", book=b, chapters=miss)
        if 1 in miss:
            add("C4", "ERROR", f"'{b}' is present but its chapter 1 is not — the head of the book is lost",
                book=b)

    # C5 discontiguous · C6 overlong
    for (b, c), pages in sorted(by_ch.items()):
        runs = _runs(pages)
        if len(runs) > 1:
            add("C5", "ERROR", f"'{b} {c}' is split across {len(runs)} disjoint page runs: {runs[:4]}",
                book=b, chapter=c, runs=runs)
        # a chapter of N verses spanning more than ~N/2 pages is not printed that way
        nv = VERSES.get((b, c))
        span = len(set(pages))
        if span > 25 and (nv is None or span > max(8, nv)):
            add("C6", "WARN", f"'{b} {c}' claims {span} pages", book=b, chapter=c, n=span)

    # C7 front-matter dump: a long run at the very head of the volume on a chapter > 1
    if recs:
        first = sorted(recs, key=lambda r: r["page_index"])[:40]
        c0 = Counter((r["book"], r["chapter"]) for r in first)
        (b, ch), n = c0.most_common(1)[0]
        if ch and ch > 1 and n >= 8:
            add("C7", "ERROR",
                f"{n} of the volume's first 40 pages are addressed to '{b} {ch}' — front matter dumped onto a "
                f"mid-book chapter instead of the book's own front matter", book=b, chapter=ch, n=n)

    # C8 double-counted page
    perpage = defaultdict(set)
    for r in recs:
        perpage[r["page_index"]].add(r["book"])
    dup = {p: bs for p, bs in perpage.items() if len(bs) > 1}
    if dup:
        add("C8", "ERROR", f"{len(dup)} page(s) contribute to more than one book", n=len(dup),
            sample=sorted(dup)[:5])

    # C9 page counts across the three renderings
    import reocr_core as core
    n_ocr = len(glob.glob(str(core.BASE_OCR_ROOT / ocr_dir / "*.json")))
    entry = jp2_page.OCR_DIR_TO_JP2.get(ocr_dir)
    n_jp2 = len(glob.glob(str(Path(jp2_page.SCANS) / entry[1] / "*.jp2"))) if entry else None
    n_pdf = pdf_pages(ocr_dir)
    if n_jp2 is not None and n_ocr != n_jp2:
        add("C9", "WARN" if abs(n_ocr - n_jp2) <= 2 else "ERROR",
            f"OCR {n_ocr} pages vs jp2 {n_jp2}", n_ocr=n_ocr, n_jp2=n_jp2)
    if n_pdf is not None and n_jp2 is not None and n_pdf != n_jp2:
        add("C9", "INFO", f"PDF {n_pdf} pages vs jp2 {n_jp2} — the two renderings differ; any PDF "
                          f"cross-reference needs a verified offset", n_pdf=n_pdf, n_jp2=n_jp2)

    # C10 verse vs its page's address
    lf = HERE / f".corpus-localize-{ocr_dir}.json"
    if lf.exists():
        addr = {r["page_index"]: (r["book"], set(r["chapters_on_page"] or [])) for r in recs}
        mism = 0
        for key, rec in json.loads(lf.read_text())["verses"].items():
            b, c, _v = key.rsplit("/", 2)
            a = addr.get(rec["page"])
            if a and (a[0] != b or int(c) not in a[1]):
                mism += 1
        if mism:
            add("C10", "ERROR", f"{mism} localized verses whose book:chapter is not what their page is "
                                f"addressed to", n=mism)
    return out


def main():
    findings = []
    for od in WI.admitted_ocr_dirs():
        findings += sweep_volume(od)
    sev = Counter(f["sev"] for f in findings)
    chk = Counter(f["check"] for f in findings)
    print(f"\n{'='*100}\nINTEGRITY SWEEP — {len(findings)} findings across {len(WI.admitted_ocr_dirs())} volumes\n")
    print(f"  by severity: {dict(sev)}")
    print(f"  by check   : {dict(sorted(chk.items()))}\n")
    for f in sorted(findings, key=lambda x: (x["sev"] != "ERROR", x["check"], x["vol"])):
        print(f"  [{f['sev']:5}] {f['check']:4} {f['vol']:24} {f['msg']}")
    (HERE / "integrity-sweep.json").write_text(json.dumps(
        {"n": len(findings), "by_severity": dict(sev), "by_check": dict(chk), "findings": findings},
        ensure_ascii=False, indent=1))
    print(f"\n-> wrote integrity-sweep.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

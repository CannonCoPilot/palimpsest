#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""page_address_eval.py — does `page_address` address EVERY page, and address it RIGHT? (2026-07-27)

Two measurements, because the 16 GT pages alone cannot answer the question Sir actually asked:

  GT CHECK        — over the scripture GT pages, does the assigned (book, chapter) equal the declared locus?
                    Exact, but only 16 labels.
  HELD-OUT CHECK  — run with printed chapter headings WITHHELD from the evidence, then measure how often the
                    DP independently recovers the chapter the page actually prints. Thousands of labels, no
                    gold, and it is the only evidence that scales to "ALL pages are addressed correctly".

COVERAGE is reported separately from ACCURACY and is the first thing printed: a run that addresses 90% of
pages very accurately has not done the job.

Usage: ocr-venv/bin/python ocr-spike/page_address_eval.py [--ocr-dir X] [--from N] [--to N] [--use-headings]
"""
from __future__ import annotations

import argparse
import glob
import json
import re
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import gt_registry as REG                 # noqa: E402
import witness_inventory as WI            # noqa: E402
sys.path.insert(0, str(HERE / "witness"))
import witnesses as W                     # noqa: E402  # the artefact must NAME the witness it addressed
import page_address as PA                 # noqa: E402
import reocr_core as core                 # noqa: E402
from corpus_wire_probe import stored_page  # noqa: E402

# `tome-map.json` (v1) was loaded here as `TOME` to feed `tome_prior`. Both the load and the prior are gone:
# see `tome_prior` below for the measurement that retired it. The load is deleted rather than left dormant
# because a module-level read makes this module depend, at import time, on a superseded artifact.
# ocr_dir -> testaments, from master-source-list (the witness registry) — the authority on what a volume IS.
REGISTRY_TESTAMENTS = {}
for _w in json.loads((HERE / "master-source-list.json").read_text())["witnesses"]:
    for _v in (_w.get("volumes") or []):
        if _v.get("ocr_dir"):
            REGISTRY_TESTAMENTS[_v["ocr_dir"]] = _w.get("testaments") or []
_PIDX = re.compile(r"_(\d{4})(?:\.\w+)?$")


def volume_books(ocr_dir: str) -> list[str]:
    """The DP's state space: the books this volume MAY legally contain, from `witness_inventory` — declared.

    NOT inferred. Three artifacts were previously consulted as if each were authoritative about what a volume
    holds, and they disagree: `master-source-list` records testaments per WITNESS (so S1's three-volume set
    hands "OT+NT" to its New Testament), `tome-map` declares the 1633 Rheims NEW TESTAMENT as ['NT','OT'], and
    a missing entry fell back to "both". A 27-book volume therefore got a 73-book state space, and the DP used
    the room: **archive-ot2-1610 put 140 pages on NT books, jp2-S09ot2 put 136, jp2-S06 put 772.** An OT volume
    cannot contain a New Testament page; the state space must make that impossible rather than merely
    improbable."""
    tt = set(WI.testaments_for(ocr_dir))
    if not tt:
        raise KeyError(f"{ocr_dir} is not in the authoritative witness inventory (witness_inventory.WITNESSES)")
    tomes = set(WI.tomes_for(ocr_dir))
    books = []
    for b in PA.BOOK_ORDER:
        t = PA.BOOK_TESTAMENT.get(b)
        if t == "NT":
            if "NT" in tomes:
                books.append(b)
        elif t == "OT":
            # The printed OT is split into two tomes; a volume carrying only OT2 cannot hold Genesis.
            tome = "OT2" if b in WI.OT2_BOOKS else "OT1"
            if tome in tomes:
                books.append(b)
    return books


def tome_prior(ocr_dir: str) -> dict:
    """DISABLED — returns {}. Retained so the call sites and the reasoning stay visible.

    tome-map **v1** was the prior, and the audit measured it at 25.5% accuracy on `archive-nt-1582` and 0.0%
    on `jp2-S04` and `pdf-S03b` (flat at every candidate offset, so genuinely wrong rather than shifted). A
    prior that wrong is not weak evidence, it is misinformation with a +0.4 emission bonus attached.

    tome-map **v2** cannot replace it: v2 is DERIVED FROM this addressing, so feeding it back would make the
    DP confirm its own previous answer — a self-fulfilling prior that would look like agreement and prove
    nothing.

    So the prior is removed rather than replaced, and the removal was MEASURED before it was made: with the
    prior and without it, held-out chapter accuracy is identical on every volume tested, including the ones
    where v1 was accurate (pdf-S03a 309/309, jp2-S08 150/150, archive-ot2-1610 152/152) and the one where it
    was worst (archive-nt-1582 14/14). The content evidence and the monotone constraint already carry it."""
    return {}


def load_pages(ocr_dir: str, lo: int, hi: int) -> list[dict]:
    pages = []
    for f in sorted(glob.glob(str(core.BASE_OCR_ROOT / ocr_dir / "*.json"))):
        m = _PIDX.search(Path(f).stem)
        if not m:
            continue
        pi = int(m.group(1))
        if not (lo <= pi <= hi):
            continue
        p = stored_page(ocr_dir, pi)
        if p:
            p["page_index"] = pi
            pages.append(p)
    return pages


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--ocr-dir", default="archive-ot2-1610")
    ap.add_argument("--from", dest="lo", type=int, default=0)
    ap.add_argument("--to", dest="hi", type=int, default=10**9)
    ap.add_argument("--use-headings", action="store_true",
                    help="production mode; WITHOUT it, headings are held out and become the accuracy check")
    a = ap.parse_args(argv)

    books = volume_books(a.ocr_dir)
    pages = load_pages(a.ocr_dir, a.lo, a.hi)
    print(f"\nvolume {a.ocr_dir}: {len(books)} books, {len(pages)} pages loaded "
          f"[{a.lo}..{min(a.hi, max((p['page_index'] for p in pages), default=0))}]  "
          f"headings={'USED' if a.use_headings else 'WITHHELD (held-out check)'}")
    if not pages:
        print("no pages"); return 1
    recs = PA.address_volume(pages, books, prior=tome_prior(a.ocr_dir), use_headings=a.use_headings)
    recs = PA.pin_carry_chain(recs, pages)      # exact line-range pinning from the printed headings + carry-in

    # chapter 0 IS an address (the book's own front matter), so test for presence, not truthiness — a falsy-0
    # check reported 33 correctly-addressed front-matter pages as unaddressed.
    addressed = sum(1 for r in recs if r["book"] and r["chapter"] is not None)
    front = sum(1 for r in recs if r["chapter"] == 0)
    print(f"\nCOVERAGE  {addressed}/{len(recs)} pages addressed = {100*addressed/len(recs):.1f}%"
          f"   (the aim is 100% — an unaddressed page cannot be re-OCR'd)"
          f"\n          of which {front} are book front-matter (chapter 0) and "
          f"{sum(1 for r in recs if r['kind']=='no-scripture')} carry no scripture — both are ADDRESSES, not gaps")

    ho = PA.heldout_heading_accuracy(recs)
    label = "HELD-OUT" if not a.use_headings else "CIRCULAR (headings were used as evidence)"
    print(f"{label} chapter accuracy vs pages that PRINT their chapter: "
          f"{ho['agreed']}/{ho['pages_with_printed_chapter']} = "
          f"{'n/a' if ho['accuracy'] is None else f'{100*ho['accuracy']:.1f}%'}")

    # PINNING CHECK — where does each chapter START on the page? The printed heading line is an independent
    # label for this (the pinner never sees headings), so it measures the thing the interval number cannot.
    from statistics import mean as _mean
    widths = [len(r["chapters_on_page"]) or 1 for r in recs]
    dis = sum(1 for r in recs if r.get("carry_disagrees_with_dp"))
    print(f"PINNING  mean chapters/page {_mean(widths):.2f} (max {max(widths)}); "
          f"boundaries are the PRINTED heading lines, exact by construction.")
    ex = sum(1 for r in recs if r.get("exact_pins"))
    print(f"EXACT LINE PINS from a surviving printed heading: {ex}/{len(recs)} pages = {100*ex/len(recs):.1f}%"
          f"   (elsewhere the boundary is not printed-and-readable; the interval is what the verse localizer resolves within)")
    print(f"HEADING vs DP disagreement (heading chapter not in {{dp, dp+1}}): {dis}/{len(recs)} = {100*dis/len(recs):.2f}%")

    by_pi = {r["page_index"]: r for r in recs}
    gt = [g for g in REG.records("scripture") if g.ocr_dir == a.ocr_dir and a.lo <= (g.page_index or -1) <= a.hi]
    if gt:
        hit = 0
        print(f"\nGT CHECK ({len(gt)} declared pages in range):")
        for g in gt:
            r = by_pi.get(g.page_index)
            got = f"{r['book']}/{r['chapter']}" if r else "MISSING"
            want_ch = set(g.chapters) or ({g.chapter} if g.chapter else set())
            want = f"{g.book}/{'+'.join(str(c) for c in sorted(want_ch)) or '?'}"
            # A multi-chapter GT page ("115+116") is correct if the address lands on ANY chapter it declares.
            ok = bool(r and r["book"] == g.book and (want_ch & set(r["chapters_on_page"])))
            hit += ok
            print(f"   {'OK ' if ok else 'BAD'} p{g.page_index:<5} want {want:<16} got {got:<16} "
                  f"src={r['source'] if r else '-':<18} fit={r['fit'] if r else '-'} kind={r['kind'] if r else '-'}")
        print(f"   -> {hit}/{len(gt)} correct")
    # The artefact names the witness it addressed, not only the directory it read. `jp2-S06` was a
    # directory naming two settings 53 years apart (R7.5a); an artefact that records only a path
    # cannot be checked against the registry, and the R7.5a re-key left one file declaring an
    # `ocr_dir` its own filename contradicted. `witness_of` RAISES on an ambiguous id, so a volume
    # that cannot be named is a loud failure here rather than an unnamed record downstream.
    (HERE / f".page-address-{a.ocr_dir}.json").write_text(json.dumps(
        {"ocr_dir": a.ocr_dir, "witness": W.wid(*W.witness_of(a.ocr_dir)),
         "use_headings": a.use_headings, "coverage": [addressed, len(recs)],
         "heldout": ho, "records": recs}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

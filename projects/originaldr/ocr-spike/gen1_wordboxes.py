# -*- coding: utf-8 -*-
"""WORD BOXES FOR GENESIS 1 — re-recognize the twelve pages and keep the per-character geometry.

WHY THIS EXISTS. Every attempt this project has made to separate the Douay-Rheims's marginal apparatus from
its scripture has been an ESTIMATE over line-level geometry, because line-level geometry is all the stored
corpus keeps (`bbox` + `text`, nothing more). Three such estimators were built and all three failed corpus
validation: a widest-gap right edge cut 36.5% of psalms lines; a proportional character offset over-cut
Genesis; a run-length filter over an un-anchored token set deleted the hyphen-split "a fir. ment" out of
*firmament*. The reason is structural — the apparatus and the scripture share a line's y-band, so a single
box cannot say where one ends and the other begins.

`kraken`'s recognizer already knows. `rpred` returns an `ocr_record` whose `.cuts` is a per-CHARACTER polygon
in page coordinates, one per character of the prediction. Word boxes follow directly, and with them the column
boundary stops being estimated and becomes measured.

WHY ONLY TWELVE PAGES. Genesis 1's verses are supplied by exactly twelve leaves across the four witnesses
(S1 21-24, S3 14/25/26, S9 31-33, S6 19-20). Re-recognizing the whole corpus for this would be hours; re-
recognizing Genesis 1 is minutes, and Sir's instruction is to hold everything to Genesis 1 until it is right.

WHAT IS NOT CLAIMED. This re-runs recognition, so its text is not identical to the stored stream — the point
is the GEOMETRY, and any comparison of pass rates against the stored-stream baseline must say which stream it
is measuring. The cache records the model used so a later reader cannot mistake one for the other.

Usage:  ocr-venv/bin/python gen1_wordboxes.py [--force]
Output: .gen1-wordboxes.json  {ocr_dir: {page_index: {page_px, lines:[{bbox,text,words:[{t,x0,x1,y0,y1}]}]}}}
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import reocr_core as core                    # noqa: E402

OUT = HERE / ".gen1-wordboxes.json"          # legacy default: Genesis 1


def cache_path(book: str, chapter: int) -> Path:
    """One cache per chapter. Genesis 1 keeps its historical filename so nothing already measured is orphaned."""
    return OUT if (book, chapter) == ("genesis", 1) else HERE / f".wordboxes-{book}-{chapter}.json"


def discover_pages(book: str, chapter: int, pad: int = 1) -> dict[str, list[int]]:
    """The leaves that actually supply this chapter's verses, per witness, read off the localizer's own output.

    Genesis 1's page list was assembled by hand. That does not scale and it is not necessary: every witness has
    a `.corpus-localize-<ocr_dir>.json` recording which leaf each verse was found on, so the leaf set is a
    query, not a judgement. `pad` widens it by a leaf either side, because a chapter's first or last verse can
    continue onto a neighbour the localizer credited to the adjacent chapter."""
    import collections
    out: dict[str, list[int]] = {}
    for od in PAGES:
        f = HERE / f".corpus-localize-{od}.json"
        if not f.exists():
            continue
        d = json.loads(f.read_text()).get("verses", {})
        pgs = {v["page"] for k, v in d.items()
               if k.startswith(f"{book}/{chapter}/") and isinstance(v, dict) and v.get("page") is not None}
        if pgs:
            out[od] = sorted({p + o for p in pgs for o in range(-pad, pad + 1) if p + o >= 0})
    return out

# The leaves that actually supply Genesis 1 verses, per witness — taken from the localizer's own output
# rather than from the address interval, so no page is recognized that cannot contribute.
PAGES = {
    "archive-ot1-1609": [21, 22, 23, 24],
    "pdf-S03a": [14, 25, 26, 27],
    "archive-holiebible-ot1": [30, 31, 32, 33],
    "jp2-S06": [17, 18, 19, 20, 21],
}


def _poly_bounds(poly):
    xs = [p[0] for p in poly]
    ys = [p[1] for p in poly]
    return min(xs), max(xs), min(ys), max(ys)


def words_from_record(text: str, cuts) -> list[dict]:
    """Group the per-character cuts into words, splitting on whitespace in the prediction.

    `cuts[i]` corresponds to `text[i]`, so a word's box is the union of the cuts of its own characters. A
    character with no cut (kraken can return a shorter tuple on a degenerate line) is skipped rather than
    guessed at, and a word left with no boxes at all is dropped — a word without geometry is of no use to a
    column test and inventing a position for it would defeat the purpose of this module."""
    words: list[dict] = []
    cur: list[int] = []
    n = min(len(text), len(cuts))
    for i in range(n + 1):
        ch = text[i] if i < n else " "
        if ch.isspace():
            if cur:
                bs = [_poly_bounds(cuts[j]) for j in cur if cuts[j]]
                if bs:
                    words.append({"t": "".join(text[j] for j in cur),
                                  "x0": min(b[0] for b in bs), "x1": max(b[1] for b in bs),
                                  "y0": min(b[2] for b in bs), "y1": max(b[3] for b in bs)})
                cur = []
        else:
            cur.append(i)
    return words


def recognize_page(ocr_dir: str, page_index: int) -> dict:
    from kraken import rpred
    pim = core.preprocess(core.load_scan(ocr_dir, page_index))
    seg = core.segment(pim)
    lines = []
    for rec in rpred.rpred(core._model(core.R2_MODEL), pim, seg):
        text = str(rec)
        cuts = list(getattr(rec, "cuts", ()) or ())
        w = words_from_record(text, cuts)
        if not w:
            continue
        lines.append({"text": text,
                      "bbox": [min(x["x0"] for x in w), min(x["y0"] for x in w),
                               max(x["x1"] for x in w), max(x["y1"] for x in w)],
                      "words": w})
    return {"page_px": list(pim.size), "model": core.R2_MODEL.name, "lines": lines}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--book", default="genesis")
    ap.add_argument("--chapter", type=int, default=1)
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args(argv)
    out = cache_path(a.book, a.chapter)
    pages_by_od = PAGES if (a.book, a.chapter) == ("genesis", 1) else discover_pages(a.book, a.chapter)
    if not pages_by_od:
        print(f"no leaves found for {a.book} {a.chapter} in the localizer output", file=sys.stderr)
        return 1
    print(f"{a.book} {a.chapter}: " + "  ".join(f"{od}={p}" for od, p in pages_by_od.items()))
    cache = json.loads(out.read_text()) if (out.exists() and not a.force) else {}
    t0 = time.time()
    for od, pages in pages_by_od.items():
        cache.setdefault(od, {})
        for pi in pages:
            if str(pi) in cache[od]:
                print(f"  {od} p{pi}: cached", flush=True)
                continue
            try:
                cache[od][str(pi)] = recognize_page(od, pi)
                n = len(cache[od][str(pi)]["lines"])
                nw = sum(len(l["words"]) for l in cache[od][str(pi)]["lines"])
                print(f"  {od} p{pi}: {n} lines, {nw} words, {time.time()-t0:.0f}s", flush=True)
            except Exception as e:                              # noqa: BLE001
                print(f"  {od} p{pi}: FAILED {type(e).__name__}: {e}", flush=True)
            out.write_text(json.dumps(cache, ensure_ascii=False))
    tot = sum(len(v) for v in cache.values())
    print(f"wrote {out.name}: {tot} pages, {time.time()-t0:.0f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

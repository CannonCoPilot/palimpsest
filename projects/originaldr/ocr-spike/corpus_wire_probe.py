#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""corpus_wire_probe.py — DOES THE GOLD-PAGE LIFT SURVIVE ON THE STORED CORPUS STREAM? (2026-07-27)

THE QUESTION THIS EXISTS TO ANSWER. Every headline number in the report comes from `qc_audit`, which reads
`sources/our-ocr-diplomatic`. `reocr_core.base_ocr` — the "base" column that V9 shows R2 beating by +0.204 —
reads THE SAME DIRECTORY. So the report has been showing the BEFORE state on 6438 verses and the AFTER state
on 15 pages, and never joining them: `qc_audit` imports NONE of `verse_locate`, `xsrc_gate`, `r3_route`,
`s_arbiter`, and nothing writes R3/arbiter output back into the corpus stream. The improved pipeline has
touched 191 of 6438 verses (3.0%).

WHY THE FIX MIGHT BE CHEAP. The stored corpus stream was ALREADY recognized with `reichenau_lat` (the R2
model — see `sources/our-ocr-diplomatic/_manifest.json`) and every stored line carries a `bbox`. So the
gold-page lift is mostly DOWNSTREAM of recognition — body-isolation (dropping interleaved marginalia) plus
localization — and should be re-derivable from what is already on disk, with no kraken re-run.

"Should be" is a hypothesis, so this measures it instead of assuming it:

  ARM 1  base      the stored page text as `base_ocr` returns it — ALL lines, stored order. The report's stream.
  ARM 2  isolated  the same stored lines, body-isolated by `layout.type_lines` on the stored bboxes.
  ARM 3  live-R2   the number `reocr_lift.py` measured by actually re-running kraken (from reocr-lift.json).

Scored per verse against the SAME janvier-cut gold, archaic-preeminent — the truth standard, not a proxy.
ARM2 vs ARM1 is the lift a corpus wire-through would actually buy. ARM2 vs ARM3 is the honest cost of NOT
re-recognizing: if ARM2 lands near ARM3, the corpus is a wiring job away; if it lands near ARM1, the lift came
from re-recognition after all and the wire-through is a 12-hour kraken pass, not an afternoon.

Usage: ocr-venv/bin/python ocr-spike/corpus_wire_probe.py [--localize] [slug ...]
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys
import warnings
from pathlib import Path
from statistics import mean

warnings.filterwarnings("ignore")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import layout                              # noqa: E402
import reocr_core as core                  # noqa: E402
import verse_seg as VS                     # noqa: E402
from char_identity import evaluate_locus   # noqa: E402
from reocr_lift import LOCI, gold_by_chapter  # noqa: E402

GT = HERE / "ground-truth"
STORE = core.BASE_OCR_ROOT


class _Shim:
    """Presents a stored {bbox:[x0,y0,x1,y1]} line the way `layout` expects a kraken segmentation line.

    layout reads geometry off `.baseline` / `.boundary` point lists, so the stored rectangle is handed over as
    its four corners. This is the whole adapter: no re-segmentation, no recognition, no image touched."""
    __slots__ = ("boundary", "baseline")

    def __init__(self, bbox):
        x0, y0, x1, y1 = bbox
        self.boundary = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
        self.baseline = [(x0, y1), (x1, y1)]


def stored_page(ocr_dir: str, page_index: int) -> dict | None:
    """Rebuild a `reocr_page`-shaped result from the STORED stream — same keys, no kraken.

    Page dims come from the stored line extent rather than the image: `type_lines` uses page_w only for its
    wide-line and margin fractions, and the recorded lines already span the printed block. Reading the jp2 for
    exact dims would defeat the purpose of the probe (it is the per-page image work we are trying to avoid)."""
    hits = sorted(glob.glob(str(STORE / ocr_dir / f"*_{page_index:04d}.json")))
    if not hits:
        return None
    d = json.load(open(hits[0], errors="ignore"))
    raw = [l for l in (d.get("lines") or []) if isinstance(l, dict) and l.get("bbox") and l.get("text")]
    if not raw:
        return None
    W = max(l["bbox"][2] for l in raw)
    H = max(l["bbox"][3] for l in raw)
    roles = layout.type_lines([_Shim(l["bbox"]) for l in raw], W, H)
    lines = [{"text": l["text"], "conf": 1.0, "role": r, "bbox": tuple(l["bbox"])}
             for l, r in zip(raw, roles)]
    # The DR sets its annotations in a column beside the text, and the line builder merges a marginal
    # fragment with the body text sharing its y-band into ONE line — so apparatus arrives INSIDE a
    # `role="body"` line, past every role filter downstream. `layout.strip_margin_prefix` removes it by
    # POSITION (the line box), which is the only signal that separates it: the token-vocabulary filter was
    # tested and rejected because the un-anchored runs are dominated by correct archaic spellings.
    # Applied to the line texts themselves so `r2_body` below and `verse_geom.build_body_tokmap` — which
    # rebuilds from these same lines — cannot disagree about the token stream (best_spans raises if they do).
    # DEFAULT ON, measured before adopted (2026-07-28). Corpus-wide with the strip: pass_rate_archaic
    # 0.5919 -> 0.6300, verse_cover_rate 0.8187 -> 0.8535, source_fail_mean 0.4041 -> 0.3636, archaic passes
    # +972, covered loci +223 — every scripture metric improved and none regressed. On Genesis the gain has
    # the shape the mechanism predicts, which is the real evidence: S1 +6.1, S3 +6.3, S9 +7.0 points, and
    # S6 — set widest, with only 3.4% merged lines against their ~13% — moves +0.4. Set ODR_STRIP_MARGIN=0
    # to measure without it.
    # APPARATUS REMOVAL, IN THIS ORDER — the order is load-bearing, not stylistic.
    #
    # The side-column DEMOTION must run FIRST. Both strips locate the text block by the median body-line x0,
    # and while the right-hand apparatus lines are still typed `body` their x0 (≈5150 of a 6048-wide page)
    # drags that median from ≈1075 to ≈2400. Every legitimate line then looks like it begins in the margin,
    # and the prefix strip cuts real scripture out of it: on `archive-holiebible-ot1` p31 it removed
    # "5 diuided the light" from L38, "light, Day, and the" from L39 and "mament made amidſt the" from L44 —
    # deleting the text it exists to protect. Demote first and the median lands on the text block.
    side = layout.drop_side_column_lines(lines, W) if os.environ.get("ODR_DROP_SIDECOL", "1") != "0" else set()
    # The apparatus column's left edge, taken from the lines that lie wholly inside it, BEFORE they are
    # demoted out of `body` and the evidence disappears. A page with fewer than three such lines has no
    # column, and the suffix strip must then leave it alone — a ragged right margin is not a column, and
    # treating one as such cut 36.5% of `jp2-S06`'s psalms lines and took the corpus from 0.6384 to 0.5602.
    col_left = min((lines[i]["bbox"][0] for i in side), default=None) if len(side) >= 3 else None
    for i in side:
        lines[i]["role"] = "marginalia"
    # Then the apparatus MERGED INTO a body line, which no role filter can reach — left edge, then right.
    if os.environ.get("ODR_STRIP_MARGIN", "1") != "0":
        for l, t in zip(lines, layout.strip_margin_prefix(lines, W, keep_slack=0)):
            l["text"] = t
    # DEFAULT OFF — implemented, measured, and NOT adopted. It removes the apparatus that shares a body
    # line's y-band on the right, and on Genesis 1 it is clearly right: zero-support verses 13 -> 3. But it
    # does not survive corpus validation in any form yet.
    #   v1 (widest-gap edge): cut 36.5% of `jp2-S06` psalms lines, truncating plain prose, and took the
    #      corpus from pass_rate_archaic 0.6384 to 0.5602.
    #   v2 (edge evidenced by real side-column lines): psalms safe, but still over-cuts Genesis pages that DO
    #      have a column — localization MISSES jumped S1 9->30, S3 5->24, and Genesis fell 76.2->64.9.
    # The mechanism is real and the estimate is not yet accurate enough to spend scripture on. Set
    # ODR_STRIP_SUFFIX=1 to measure it; it must beat the corpus baseline before it goes back on.
    if os.environ.get("ODR_STRIP_SUFFIX", "0") != "0":
        for l, t in zip(lines, layout.strip_margin_suffix(lines, W, edge=col_left)):
            l["text"] = t
    body = [l for l in lines if l["role"] == "body"]
    return {"ocr_dir": ocr_dir, "page_index": page_index, "page_px": (W, H), "lines": lines,
            "r2_body": layout.strip_verse_numbers(core._norm(" ".join(l["text"] for l in body))),
            "n_body": len(body), "n_lines": len(lines)}


def _score(body: str, janv: dict, gold_j: dict, *, spans=None) -> dict:
    seg = spans if spans is not None else (VS.segment(body, janv, drop_apparatus=True) if body else {})
    return {v: (evaluate_locus((seg.get(v) or {}).get("text", ""), janv.get(v), gold_j[v]["text"])["archaic_id"]
                if v in seg else None) for v in gold_j}


def probe(slug: str, *, localize: bool = False) -> dict | None:
    gt = json.loads((GT / f"{slug}.json").read_text())
    book, od, pi = LOCI.get(slug), gt.get("ocr_dir"), gt.get("page_index")
    if not book or od is None or pi is None:
        return None
    page = stored_page(od, pi)
    if page is None:
        return None
    base_body = core.base_ocr(od, pi)
    rows = []
    for ch, gold_text in sorted(gold_by_chapter(gt).items()):
        janv = VS.chapter_verses(book, ch, VS.JANVIER)
        if not janv:
            continue
        gold_j = VS.segment(gold_text, janv)
        b = _score(base_body, janv, gold_j)
        spans = None
        if localize:
            import verse_locate
            spans = verse_locate.best_spans(page, book, ch)
        i = _score(page["r2_body"], janv, gold_j, spans=spans)
        for v in sorted(gold_j):
            rows.append({"ch": ch, "v": v, "base": b.get(v), "iso": i.get(v)})
    return {"slug": slug, "book": book, "n_lines": page["n_lines"], "n_body": page["n_body"], "rows": rows}


def _stat(rows, key):
    xs = [r[key] for r in rows if r[key] is not None]
    return (round(mean(xs), 4) if xs else None, sum(1 for r in rows if (r[key] or 0) >= 0.90), len(rows))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--localize", action="store_true", help="also apply the hybrid localizer to the stored stream")
    ap.add_argument("slugs", nargs="*")
    a = ap.parse_args(argv)

    live = {p["slug"]: p for p in json.loads((HERE / "reocr-lift.json").read_text())["pages"]} \
        if (HERE / "reocr-lift.json").exists() else {}
    slugs = a.slugs or sorted(p.stem for p in GT.glob("scripture-*.json"))
    arm2 = "stored+isolated" + ("+localized" if a.localize else "")
    print(f"\n{'='*100}\nCORPUS WIRE PROBE — can the stored stream reproduce the live-R2 lift without re-recognising?\n")
    print(f"{'slug':26} {'lines/body':>11} {'ARM1 base':>10} {arm2:>26} {'ARM3 live-R2':>13}")
    print("-" * 100)
    out = []
    for slug in slugs:
        r = probe(slug, localize=a.localize)
        if not r:
            print(f"{slug:26} (no stored page / no book)")
            continue
        out.append(r)
        bm, bp, n = _stat(r["rows"], "base")
        im, ip, _ = _stat(r["rows"], "iso")
        lv = live.get(slug) or {}
        print(f"{r['slug'].replace('scripture-',''):26} {f'{r['n_lines']}/{r['n_body']}':>11} "
              f"{f'{bm} {bp}/{n}':>10} {f'{im} {ip}/{n}':>26} {str(lv.get('r2_mean')):>13}")
    allr = [x for r in out for x in r["rows"]]
    bm, bp, n = _stat(allr, "base")
    im, ip, _ = _stat(allr, "iso")
    print("-" * 100)
    print(f"{'AGGREGATE':26} {'':>11} {f'{bm} {bp}/{n}':>10} {f'{im} {ip}/{n}':>26}")
    print(f"\nARM1 base      mean {bm}   pass {bp}/{n} = {100*bp/n:.0f}%   <- the stream every report headline scores")
    print(f"ARM2 {arm2:<22} mean {im}   pass {ip}/{n} = {100*ip/n:.0f}%")
    if live:
        agg = json.loads((HERE / "reocr-lift.json").read_text())["aggregate"]
        print(f"ARM3 live-R2   mean {agg['r2_mean']}   pass {agg['r2_pass']}/{agg['verses']} "
              f"= {100*agg['r2_pass']/agg['verses']:.0f}%   <- what re-running kraken buys")
        recovered = ((im - bm) / (agg["r2_mean"] - bm)) if (agg["r2_mean"] - bm) else None
        print(f"\nFRACTION OF THE LIVE-R2 LIFT RECOVERED FROM DISK ALONE: "
              f"{f'{100*recovered:.0f}%' if recovered is not None else 'n/a'}")
    (HERE / "corpus-wire-probe.json").write_text(json.dumps(
        {"arm2": arm2, "aggregate": {"base_mean": bm, "base_pass": bp, "iso_mean": im, "iso_pass": ip, "n": n},
         "pages": out}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

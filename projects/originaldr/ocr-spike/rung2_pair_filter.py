#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""rung2_pair_filter.py — drop training pairs whose GT does not describe the same ink as the crop (§13 Q39).

THE DEFECT, found by hand-checking 40 harvested pairs against the human transcription (2026-07-29): **11 of 40
were mislabelled**, in two forms, both concentrated in TABLES and LISTS:

    GT entry SPANS MORE than the crop   crop `Thurſday,`  GT `Thurſday, goſp. 186.`   (a two-column row)
    WRONG GT line paired to the crop    crop `V. 39. For charitie they ſay loue : &`
                                        GT   `V. 15. For Church they ſay Congregation.`

Both come from one broken assumption in `rung2_prepare`: **one GT entry = one visual line.** A table row is one
logical entry set across two columns or wrapped over two lines, so a crop can only ever be a fragment of it; and
because table rows are formulaic, the similarity matcher pairs the wrong row at high confidence. Measured content
accuracy against the human read: scripture 0.9654, matter PROSE 0.9731, matter TABLES/LISTS **0.8225**.

WHY NOT FILTER ON THE MATCH SIMILARITY `sim`. Because `sim` is low for two OPPOSITE reasons — the label is wrong,
or the RECOGNIZER is wrong — and the second kind is the most valuable training data there is. Dropping low-`sim`
pairs would throw away exactly the lines that teach. (`scripture-abdias-01` has mean sim 0.575 on a page that is
simply hard to read.)

WHAT SEPARATES THEM IS GEOMETRY, NOT SIMILARITY. A mislabelled pair has a GT string too long for the pixels it is
paired with; a hard-but-correct pair has a GT string of the right length that the model reads badly. So the test
is CHARACTERS PER PIXEL OF CROP WIDTH, compared against the median for that GT file (robust to one bad row, and
per-file because founts and scan scales differ). A pair whose density is far above the file's median is claiming
more text than fits; far below means the crop holds ink the GT does not account for.

VALIDATED AGAINST HAND LABELS, not asserted: the 40 calibration lines in `rung2-calib40.json` were read blind and
scored against the human GT, so they are a labelled test set for this filter. Run with `--validate`.

Usage:
  ../ocr-venv/bin/python rung2_pair_filter.py --data .rung2-data-v2 [--hi 1.35] [--lo 0.70] [--validate]
"""
from __future__ import annotations

import argparse
import collections
import json
import statistics as st
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from PIL import Image                                     # noqa: E402

Image.MAX_IMAGE_PIXELS = None


def density(data: Path, man: list[dict]) -> list[dict]:
    out = []
    for m in man:
        png = data / f"line_{m['id']:04d}.png"
        gt = data / f"line_{m['id']:04d}.gt.txt"
        if not (png.exists() and gt.exists()):
            continue
        with Image.open(png) as im:
            w, h = im.size
        text = gt.read_text().strip()
        if not text or w < 8 or h < 4:
            continue
        # normalise by crop HEIGHT too: a crop's characters scale with type size, so chars per (width/height)
        # is roughly "characters per em" and comparable across scans of different resolution.
        ems = w / h
        out.append({**m, "w": w, "h": h, "chars": len(text), "per_em": len(text) / ems})
    return out


def classify(rows: list[dict], hi: float, lo: float) -> list[dict]:
    med = {}
    by = collections.defaultdict(list)
    for r in rows:
        by[r["slug"]].append(r["per_em"])
    for s, v in by.items():
        med[s] = st.median(v)
    for r in rows:
        m = med[r["slug"]] or 1e-9
        r["rel"] = r["per_em"] / m
        r["keep"] = lo <= r["rel"] <= hi
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=".rung2-data-v2")
    ap.add_argument("--hi", type=float, default=1.35)
    ap.add_argument("--lo", type=float, default=0.70)
    ap.add_argument("--validate", action="store_true")
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    data = HERE / a.data
    man = json.loads((data / "_manifest.json").read_text())
    rows = classify(density(data, man), a.hi, a.lo)
    kept = [r for r in rows if r["keep"]]
    print(f"pairs {len(rows)} -> kept {len(kept)} ({len(kept)/len(rows):.1%}), dropped {len(rows)-len(kept)}")
    by = collections.Counter()
    for r in rows:
        if not r["keep"]:
            by[r["slug"]] += 1
    print("  most-dropped GT files:")
    for s, n in by.most_common(8):
        tot = sum(1 for r in rows if r["slug"] == s)
        print(f"    {s:<44} {n}/{tot}")

    if a.validate:
        calib = {c["id"]: c for c in json.loads((HERE / "rung2-calib40.json").read_text())}
        # HAND LABEL: content-fold >= 0.90 against my blind read means the crop and the GT are the same ink.
        tp = fp = tn = fn = 0
        for r in rows:
            key = f"{r['id']:04d}"
            if key not in calib:
                continue
            good_label = calib[key]["content"] >= 0.90
            if r["keep"] and good_label:
                tp += 1
            elif r["keep"] and not good_label:
                fp += 1
            elif not r["keep"] and not good_label:
                tn += 1
            else:
                fn += 1
        n = tp + fp + tn + fn
        print(f"\n  VALIDATION against {n} hand-read lines (label = 'crop and GT are the same ink'):")
        print(f"    kept & good  {tp:>3}   kept & MISLABELLED {fp:>3}  <- these survive the filter")
        print(f"    dropped & mislabelled {tn:>3}   dropped & good {fn:>3}  <- these are lost needlessly")
        if tn + fp:
            print(f"    mislabelled caught: {tn}/{tn+fp} = {tn/(tn+fp):.0%}")
        if tp + fn:
            print(f"    good retained:      {tp}/{tp+fn} = {tp/(tp+fn):.0%}")

    if a.out:
        (HERE / a.out).write_text(json.dumps([{k: v for k, v in r.items() if k != "keep"} | {"keep": r["keep"]}
                                              for r in rows], ensure_ascii=False))
        print(f"\n[wrote] {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

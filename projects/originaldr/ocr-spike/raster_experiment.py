#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""raster_experiment.py — does the 2200px cap and the autocontrast cost us recognition accuracy?

THE CLAIM UNDER TEST. `reocr_core.preprocess()` forces every page to MAXW=2200 with a LANCZOS resample and
applies `ImageOps.autocontrast` unconditionally. Against S09's 3231px native that discards 32% of the linear
resolution, and LANCZOS on a near-binary scan manufactures grey fringes on every stroke. Both are plausible
damage. Plausible is not measured, so this measures it.

THE DESIGN, AND WHY IT ISOLATES OUR OWN DAMAGE. Variants A-D all read THE SAME SOURCE IMAGE and differ only in
what we do to it afterwards. That removes every confound about which file is better and asks the one question
we control: *is our preprocessing costing us accuracy?* (The separate question — whether the PDF's embedded
mask beats the jp2 — needs a page-mapping step and is run separately.)

    A  current      autocontrast + resize to 2200      (the production path)
    B  no-contrast  resize to 2200, no autocontrast
    C  no-resize    autocontrast, native resolution
    D  native       neither — the raw page as scanned

THE METRIC, AND WHY NOT CER. A page is not a verse, so there is no aligned reference string to diff against
without first solving the alignment problem this experiment is meant to inform. Instead: concatenate the
chapter's archaic reference into one character stream, and ask what fraction of the page's recognized
characters appear in an aligned matching block of it (difflib matching blocks / length of transcript).

    attested-char rate = matched characters / recognized characters

A misread lowers it; a dropped word does not raise it. It is a PRECISION measure, deliberately — the failure
mode we are testing for (grey fringes, lost stroke detail) produces wrong characters, not missing ones. It is
reported beside the raw character count so that a variant cannot win by recognizing less.
"""
from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import reocr_core as RC                        # noqa: E402
import layout                                  # noqa: E402
import ref_renumber as RR                      # noqa: E402

LEAVES = [                                     # (ocr_dir, page_index, book, chapter) — all in walked chapters
    ("archive-holiebible-ot1", 71, "genesis", 10),
    ("pdf-S03a", 65, "genesis", 10),
    ("jp2-S06", 56, "genesis", 10),
    ("archive-ot1-1609", 61, "genesis", 10),
]


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip()


def ref_stream(book: str, chapter: int) -> str:
    """The chapter's archaic reference as one character stream — s_dismas, else odr_com."""
    sd = RR.load_corrected("s_dismas")
    od = RR.load_corrected("odr_com")
    out = []
    for v in range(1, 200):
        k = f"scripture/{book}/{chapter}/{v}"
        t = sd.get(k) or od.get(k)
        if t:
            out.append(t)
    return norm(" ".join(out))


def attested_rate(got: str, ref: str) -> tuple[float, int]:
    """Fraction of recognized characters that fall in a matching block against the reference stream."""
    if not got:
        return 0.0, 0
    sm = difflib.SequenceMatcher(a=got, b=ref, autojunk=False)
    matched = sum(b.size for b in sm.get_matching_blocks())
    return matched / len(got), len(got)


def variant_image(ocr_dir: str, page_index: int, mode: str):
    from PIL import ImageOps, Image
    im = RC.load_scan(ocr_dir, page_index)          # native, mode "L"
    native = im.size
    if mode in ("A", "C"):
        im = ImageOps.autocontrast(im)
    if mode in ("A", "B") and im.width > RC.MAXW:
        im = im.resize((RC.MAXW, int(im.height * RC.MAXW / im.width)), Image.LANCZOS)
    return im, native


def run_leaf(ocr_dir: str, page_index: int, book: str, chapter: int, modes: list[str]) -> list[dict]:
    ref = ref_stream(book, chapter)
    rows = []
    for mode in modes:
        t0 = time.time()
        pim, native = variant_image(ocr_dir, page_index, mode)
        seg = RC.segment(pim, cache_key=f"{ocr_dir}:{page_index}:{mode}:{pim.width}")
        recs = RC.recognize_lines(RC.R2_MODEL, pim, seg)
        roles = layout.type_lines(list(seg.lines), pim.width, pim.height)
        body = [r for r, role in zip(recs, roles) if role == "body"]
        got = layout.strip_verse_numbers(norm(" ".join(r["text"] for r in body)))
        rate, n = attested_rate(got, ref)
        conf = RC.page_confidence(body) if body else 0.0
        rows.append({"ocr_dir": ocr_dir, "page": page_index, "mode": mode,
                     "native": f"{native[0]}x{native[1]}", "used": f"{pim.width}x{pim.height}",
                     "lines": len(recs), "body_lines": len(body), "chars": n,
                     "attested": round(rate, 4), "conf": round(conf, 4), "secs": round(time.time() - t0, 1)})
        print(f"   {mode}  {rows[-1]['used']:>10}  lines {len(recs):>3}  chars {n:>5}  "
              f"attested {rate:.4f}  conf {conf:.4f}  {rows[-1]['secs']}s", flush=True)
    return rows


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--modes", default="A,B,C,D")
    ap.add_argument("--leaves", default="", help="index into LEAVES, comma list; default all")
    a = ap.parse_args(argv)
    modes = [m.strip() for m in a.modes.split(",") if m.strip()]
    picks = ([LEAVES[int(i)] for i in a.leaves.split(",")] if a.leaves else LEAVES)
    print("A current(autocontrast+2200) · B no-contrast · C no-resize · D native(neither)\n")
    all_rows = []
    for od, p, bk, ch in picks:
        print(f"{od} p{p}  ({bk} {ch})")
        all_rows += run_leaf(od, p, bk, ch, modes)
        print()
    out = HERE / ".campaign/raster-experiment.json"
    out.write_text(json.dumps(all_rows, indent=1))

    print("=" * 92)
    print(f"{'source':26} {'leaf':>5} {'mode':>5} {'used':>11} {'chars':>6} {'attested':>9} {'Δ vs A':>8}")
    base = {}
    for r in all_rows:
        if r["mode"] == "A":
            base[(r["ocr_dir"], r["page"])] = r["attested"]
    for r in all_rows:
        b = base.get((r["ocr_dir"], r["page"]))
        d = f"{r['attested'] - b:+.4f}" if b is not None and r["mode"] != "A" else ""
        print(f"{r['ocr_dir']:26} {r['page']:>5} {r['mode']:>5} {r['used']:>11} "
              f"{r['chars']:>6} {r['attested']:>9.4f} {d:>8}")
    print(f"\nwritten to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

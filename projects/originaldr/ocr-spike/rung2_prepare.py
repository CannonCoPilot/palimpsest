#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""rung2_prepare.py — build kraken line training data (line-image ↔ DIPLOMATIC gold-text pairs) for
per-source recognizer fine-tuning (Rung 2). For each scripture gold page: render the source raster,
kraken-segment it, recognize with the BASE recognizer, then ALIGN each segmented line to its gold body
line by folded edit-similarity (greedy 1:1, best-first). Matched pairs → <out>/line_NNNN.png + .gt.txt.
The gold text (diplomatic, ſ-preserving) is the training TARGET, so the fine-tune learns the archaic surface.

Run: ocr-venv/bin/python ocr-spike/rung2_prepare.py [--out .rung2-data] [--min-sim 0.45] [--limit N]
"""
from __future__ import annotations
import sys, json, glob, argparse, warnings
from pathlib import Path
warnings.filterwarnings("ignore")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
from char_identity import fold_archaic, edit_ratio
import jp2_page
from kraken import blla, rpred
from kraken.lib import models

BASE = HERE / "models" / "reichenau_lat.mlmodel"
GT = HERE / "ground-truth"
MAXW = 2000  # downscale wide rasters for segmentation speed/stability


def page_lines(gt_slug: str, model, min_sim: float):
    """Line pairs for one GT file, across EVERY page it covers.

    MULTI-PAGE GT FILES WERE BEING DISCARDED WHOLE (fixed 2026-07-29, §13 Q38). `page_index` is a LIST for 11 of
    the 50 GT files — `matter-ot2-historical-table` spans 24 pages — and the old guard returned [] for all of
    them. Measured on the first 10 gold pages, **584 of 617 unharvested lines (95%) were lost to this single
    line of code**. The gold lines do not record which page they sit on, so every page in the list is segmented
    and its candidates pooled; the greedy 1:1 assignment then runs ONCE over the union, which is what keeps a
    repeated table entry from being consumed twice."""
    d = json.loads((GT / f"{gt_slug}.json").read_text())
    ocr_dir, pi = d.get("ocr_dir"), d.get("page_index")
    if not ocr_dir or pi is None:
        return []                                    # unlocated: nothing to render
    gold = [b.get("text", "").strip() for b in d.get("body", [])
            if b.get("text", "").strip() and b.get("role") not in ("catchword", "signature")]
    if not gold:
        return []
    if isinstance(pi, list):
        return _multi_page_lines(gt_slug, ocr_dir, pi, gold, model, min_sim)
    return _one_page_lines(ocr_dir, pi, gold, model, min_sim)


def _multi_page_lines(gt_slug, ocr_dir, pages, gold, model, min_sim):
    """Pool candidates from every page of a multi-page GT file, then assign 1:1 across the union."""
    pool = []            # (sim, page_key, seg_idx, gold_idx, crop)
    for pg in pages:
        try:
            for sim, si, gi, crop in _page_candidates(ocr_dir, pg, gold, model, min_sim):
                pool.append((sim, f"{pg}:{si}", gi, crop))
        except Exception as e:                                   # noqa: BLE001
            print(f"  {gt_slug} p{pg}: {type(e).__name__}: {e}")
    pool.sort(key=lambda x: -x[0])
    used_s, used_g, pairs = set(), set(), []
    for sim, key, gi, crop in pool:
        if key in used_s or gi in used_g:
            continue
        used_s.add(key); used_g.add(gi)
        pairs.append((crop, gold[gi], round(sim, 3)))
    return pairs


def _one_page_lines(ocr_dir, pi, gold, model, min_sim):
    cands = list(_page_candidates(ocr_dir, pi, gold, model, min_sim))
    cands.sort(key=lambda x: -x[0])
    used_s, used_g, pairs = set(), set(), []
    for sim, si, gi, crop in cands:
        if si in used_s or gi in used_g:
            continue
        used_s.add(si); used_g.add(gi)
        pairs.append((crop, gold[gi], round(sim, 3)))
    return pairs


def _page_candidates(ocr_dir, pi, gold, model, min_sim):
    """Every (similarity, seg index, gold index, crop) above `min_sim` for ONE page. Assignment is the caller's
    job, so a multi-page file can assign across its pages at once."""
    try:
        im = jp2_page.load(ocr_dir, pi).convert("L")
    except Exception as e:                                       # noqa: BLE001
        print(f"  {ocr_dir} p{pi}: render fail {e}")
        return []
    if im.width > MAXW:
        im = im.resize((MAXW, int(im.height * MAXW / im.width)), Image.LANCZOS)
    seg = blla.segment(im)
    lines = list(getattr(seg, "lines", []) or [])
    recs = list(rpred.rpred(model, im, seg))
    out = []
    for si, rec in enumerate(recs):
        rtxt = fold_archaic(str(rec))
        if len(rtxt) < 4:
            continue
        # crop once per segmented line, not once per candidate pair
        try:
            bnd = lines[si].boundary
            xs = [q[0] for q in bnd]; ys = [q[1] for q in bnd]
            box = (max(0, int(min(xs)) - 4), max(0, int(min(ys)) - 4),
                   min(im.width, int(max(xs)) + 4), min(im.height, int(max(ys)) + 4))
            if box[2] - box[0] < 12 or box[3] - box[1] < 8:
                continue
            crop = im.crop(box)
        except Exception:                                        # noqa: BLE001
            continue
        for gi, g in enumerate(gold):
            sim = edit_ratio(rtxt, fold_archaic(g))
            if sim >= min_sim:
                out.append((sim, si, gi, crop))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=".rung2-data")
    ap.add_argument("--min-sim", type=float, default=0.45)
    ap.add_argument("--limit", type=int, default=0)
    # §13 Q38: `scripture-*` is 423 of the 2,611 hand-made GT body lines. The other 2,188 are `matter-*` —
    # prefaces, arguments, recapitulations, tables, title pages — and were never even globbed. They are the same
    # press and founts and the right GRAIN, but NOT scripture's content distribution, so they are harvested under
    # their own tag and must be ablated against the unchanged scripture val split before anyone believes they
    # help. `--kinds scripture` reproduces the historical 311-line harvest exactly.
    ap.add_argument("--kinds", default="scripture,matter",
                    help="which GT families to harvest: scripture, matter, or both (default both)")
    a = ap.parse_args()
    out = HERE / a.out
    out.mkdir(exist_ok=True)
    model = models.load_any(str(BASE))
    kinds = [k.strip() for k in a.kinds.split(",") if k.strip()]
    slugs = []
    for k in kinds:
        slugs += sorted(s.split("/")[-1][:-5] for s in glob.glob(str(GT / f"{k}-*.json")))
    if a.limit:
        slugs = slugs[:a.limit]
    print(f"[harvest] kinds={kinds} -> {len(slugs)} GT files")
    n = 0
    manifest = []
    for slug in slugs:
        pairs = page_lines(slug, model, a.min_sim)
        for crop, gold, sim in pairs:
            crop.save(out / f"line_{n:04d}.png")
            (out / f"line_{n:04d}.gt.txt").write_text(gold, encoding="utf-8")
            manifest.append({"id": n, "slug": slug, "sim": sim, "text": gold,
                             "kind": "scripture" if slug.startswith("scripture-") else "matter"})
            n += 1
        print(f"  {slug:34} {len(pairs):3} pairs  (running total {n})", flush=True)
    (out / "_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nWROTE {n} training line-pairs to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

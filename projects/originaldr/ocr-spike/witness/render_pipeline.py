"""Draw every stage of the head-band pipeline ONTO THE ACTUAL SCAN.

⚠️ WHY THIS IS TRACKED CODE AND NOT A THROWAWAY. Every claim R2.1g-R2.1j makes is a number computed
over pixels nobody has looked at. A region accuracy of 0.8760 and a word-count exact of 0.8125 are
both compatible with the instrument being wrong in ways an aggregate cannot show -- R2.1g's leaf 412
was called a running-head failure for a week when the token was a MARGINAL NOTE, and the aggregate
said nothing either way. This module puts the geometry back on the page so a claim can be REFUSED by
looking at it.

The stages, in the order the pipeline runs them, each rendered on the same crop:

  1 RAW            the head band as the reader receives it (0.06h..0.30h, frozen -- see HEAD_BAND)
  2 ELEMENTS       connected components surviving the type-size filters -- `glyph_boxes`
  3 ROWS           components clustered onto shared baselines -- `_rows_and_lines`
  4 SEGMENTS       rows cut at gaps wider than the line pitch -- `region_segments` (R2.1h)
  5 WORDS          the word split under a named splitter -- gap threshold or recogniser
  6 MEASURE        the justified block edges L/R -- `block_measure` (R1)
  7 REGIONS        the R1-R6 labels, with the gold overlaid and disagreements marked

Usage:
    python witness/render_pipeline.py --leaf 414 --stages all --out .scratch/r2/plates
    python witness/render_pipeline.py --leaf 414 --splitter recogniser --stages words,regions

⚠️ It renders what the pipeline ACTUALLY returns. It never re-derives a stage its own way -- every
stage below calls the same function the reader calls, for the reason `head_tokens` exists: two
descriptions of one row drift apart, and a diagnostic that drifts is worse than none.
"""

import argparse
import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(_HERE.parent))

import numpy as np
from PIL import Image, ImageDraw
import witnesses as W
import collation_read as CR
import region_head as RG

GOLD = _HERE / "gold/head_regions_OT1-1609-B_400-419.json"
MODEL = _HERE.parent / "models/reichenau_dr.mlmodel"

# Palette shared with the architecture artifact so a plate and its prose read as one document.
INK = (21, 28, 34)
TEAL = (10, 143, 132)         # MainText
OCHRE = (174, 117, 5)         # MarginNote
MADDER = (196, 58, 46)        # RunningHead / errors
INDIGO = (92, 111, 216)       # ChapterHead / structure
MUTED = (126, 140, 148)
LABEL_COLOUR = {RG.MAIN_TEXT: TEAL, RG.MARGIN_NOTE: OCHRE,
                RG.RUNNING_HEAD: MADDER, RG.CHAPTER_HEAD: INDIGO}


SCORER_FRAC = 0.35          # score_head_regions.TOP_FRAC / score_head_tokens.TOP_FRAC


def band_of(leaf_path, which="reader"):
    """The band under test.

    ⚠️ THERE ARE TWO, AND THAT IS THE POINT OF HAVING THIS OPTION (R2.2c, found 2026-08-17 by
    rendering leaf 414 and seeing no running head in it). The production reader uses
    `CR.head_band` = 0.06h..0.30h. Both SCORERS -- `score_head_regions.py` and
    `score_head_tokens.py` -- crop 0..0.35h instead, and the 121-token region gold is labelled
    against THAT. So the region numbers describe a band the reader never receives. Rendering both
    is how the discrepancy stops being an arithmetic argument.
    """
    if which == "reader":
        return CR.head_band(leaf_path)
    if which == "scorer":
        im = Image.open(str(leaf_path))
        im.draft("RGB", (2800, 3920))
        im = im.convert("RGB")
        w, h = im.size
        crop = im.crop((0, 0, w, int(h * SCORER_FRAC)))
        return crop.resize((1400, max(1, int(crop.height * 1400 / w))), Image.LANCZOS)
    raise SystemExit(f"unknown band {which!r}")


def stage_bands(leaf_path):
    """The SCORER's band with the READER's band drawn on it. The R2.2c plate.

    Returns the 0..0.35h crop with the frozen 0.06h..0.30h bound overlaid, so what the reader is
    handed -- and what it is therefore structurally unable to see -- is visible at a glance.
    """
    im = band_of(leaf_path, "scorer")
    d = ImageDraw.Draw(im)
    lo, hi = CR.HEAD_BAND
    y0 = int(im.height * lo / SCORER_FRAC)
    y1 = int(im.height * hi / SCORER_FRAC)
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rectangle((0, 0, im.width, y0), fill=(196, 58, 46, 60))
    im = Image.alpha_composite(im.convert("RGBA"), sh).convert("RGB")
    d = ImageDraw.Draw(im)
    d.line((0, y0, im.width, y0), fill=MADDER, width=4)
    if y1 < im.height:
        d.line((0, y1, im.width, y1), fill=TEAL, width=3)
    d.text((12, max(2, y0 - 20)), "HEAD_BAND top = 0.06h  — everything above is CUT OFF from the reader",
           fill=MADDER)
    return im


def _rect(d, box, colour, w=2):
    d.rectangle(box, outline=colour, width=w)


def _canvas(band):
    return band.convert("RGB").copy()


def stage_raw(band, ctx):
    return _canvas(band)


def stage_elements(band, ctx):
    """Connected components that survived the type-size filters. THE INPUT TO EVERYTHING ELSE."""
    im = _canvas(band)
    d = ImageDraw.Draw(im)
    for (t, b, l, r) in ctx["boxes"]:
        _rect(d, (l, t, r, b), INDIGO, 1)
    return im


def stage_rows(band, ctx):
    """Components clustered onto shared baselines. A ROW is the unit every later stage addresses."""
    im = _canvas(band)
    d = ImageDraw.Draw(im)
    for j, row in enumerate(ctx["rows"]):
        l = min(g[2] for g in row); r = max(g[3] for g in row)
        t = min(g[0] for g in row); b = max(g[1] for g in row)
        _rect(d, (l - 3, t - 3, r + 3, b + 3), TEAL if j % 2 == 0 else INDIGO, 2)
        base = float(np.median([g[1] for g in row]))
        d.line((l, base, r, base), fill=MUTED, width=1)
    return im


def stage_segments(band, ctx):
    """R2.1h: rows cut where a gap exceeds the LINE PITCH -- a run out to another region.

    This is the stage that stopped the recogniser being handed a crop spanning a running head, a
    field of white and a side-note. Leaf 414 row 0 is the case it was built for.
    """
    im = _canvas(band)
    d = ImageDraw.Draw(im)
    for row in ctx["rows"]:
        segs = CR.region_segments(row, ctx["pitch"])
        for k, seg in enumerate(segs):
            l = min(g[2] for g in seg); r = max(g[3] for g in seg)
            t = min(g[0] for g in seg); b = max(g[1] for g in seg)
            _rect(d, (l - 2, t - 2, r + 2, b + 2), MADDER if len(segs) > 1 else MUTED, 2)
    return im


def stage_words(band, ctx):
    """The word split under the splitter named on the command line. THE R2.1h DELIVERABLE."""
    im = _canvas(band)
    d = ImageDraw.Draw(im)
    for row in ctx["rows"]:
        t = min(g[0] for g in row); b = max(g[1] for g in row)
        for (l, r) in [(s[0], s[1]) for s in ctx["split_fn"](row, ctx["pitch"])]:
            _rect(d, (l - 1, t - 2, r + 1, b + 2), TEAL, 2)
    return im


def stage_measure(band, ctx):
    """R1: the justified block edges, voted on by the FIRST AND LAST token of each row only."""
    im = _canvas(band)
    d = ImageDraw.Draw(im)
    toks = ctx["tokens"]
    LR, why = RG.block_measure(toks, ctx["pitch"])
    if LR is None:
        d.text((10, 10), f"ABSTAIN: {why}", fill=MADDER)
        return im
    L, R = LR
    for x, c in ((L, TEAL), (R, TEAL)):
        d.line((x, 0, x, im.height), fill=c, width=3)
    for t in toks:
        if t["n_glyphs"] >= RG.MIN_GLYPHS:
            _rect(d, (t["l"], t["base"] - 4, t["r"], t["base"] + 2), MUTED, 1)
    return im


def stage_regions(band, ctx):
    """R1-R6 labels, with the GOLD overlaid. A disagreement is drawn, not summarised.

    Gold spans are drawn as a bar UNDER the row; the token boxes above carry the instrument's label.
    Where the two differ the token is drawn in madder and cross-hatched, so a region error is a thing
    on the page rather than a row in a table.
    """
    im = _canvas(band)
    d = ImageDraw.Draw(im)
    labelled, why = RG.classify(band, ctx["pitch"], nrows=ctx["nrows"], split_fn=ctx["split_fn"])
    if labelled is None:
        d.text((10, 10), f"ABSTAIN: {why}", fill=MADDER)
        return im
    gold = [e for e in ctx["gold"] if e["leaf"] == ctx["leaf"]]
    for t in labelled:
        col = LABEL_COLOUR.get(t["label"], MUTED)
        top, bot = t["base"] - 26, t["base"] + 6
        # the instrument's label
        _rect(d, (t["l"] - 1, top, t["r"] + 1, bot), col, 2)
        # the gold entry covering this token's centre, by the R2.1j ink/containment reading
        c = (t["l"] + t["r"]) / 2.0
        g = next((e for e in gold if e["row"] == t["row"] and e["l"] <= c <= e["r"]), None)
        if g is not None:
            gc = LABEL_COLOUR.get(g["label"], MUTED)
            d.line((g["l"], bot + 5, g["r"], bot + 5), fill=gc, width=4)
            if g["label"] != t["label"]:
                d.line((t["l"], top, t["r"], bot), fill=MADDER, width=2)
                d.line((t["l"], bot, t["r"], top), fill=MADDER, width=2)
    return im


def stage_bands_wrap(band, ctx):
    return stage_bands(ctx["leaf_path"])


STAGES = {"bands": stage_bands_wrap, "raw": stage_raw, "elements": stage_elements, "rows": stage_rows,
          "segments": stage_segments, "words": stage_words, "measure": stage_measure,
          "regions": stage_regions}


def build_ctx(leaf_index, leaf_path, splitter, nrows, which="reader"):
    band = band_of(leaf_path, which)
    p, src = CR.scale(band)
    if p is None:
        raise SystemExit(f"leaf {leaf_index}: no type scale ({src}) -- the reader abstains here too")
    boxes = CR.glyph_boxes(band, 0, p)
    rows = CR._rows_and_lines(boxes, p)
    if splitter == "recogniser":
        from kraken.lib import models
        split_fn = CR.make_recogniser_split(models.load_any(str(MODEL)), band)
    elif splitter == "quantile":
        bg, _w = CR.band_word_gap(rows, p)
        split_fn = CR.gap_split(lambda r, q: CR.row_word_gap(r, q, bg or 12))
    elif splitter == "baseline":
        split_fn = CR.gap_split(None)
    else:
        raise SystemExit(f"unknown splitter {splitter!r}")
    toks, _why = RG.tokens(band, p, split_fn=split_fn)
    gold = json.loads(GOLD.read_text())["labels"] if GOLD.exists() else []
    return band, {"leaf": leaf_index, "leaf_path": leaf_path, "pitch": p, "boxes": boxes, "rows": rows,
                  "split_fn": split_fn, "tokens": toks, "gold": gold, "nrows": nrows}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--leaf", type=int, nargs="+", required=True)
    ap.add_argument("--stages", default="all")
    ap.add_argument("--splitter", default="recogniser",
                    choices=["recogniser", "quantile", "baseline"])
    ap.add_argument("--nrows", type=int, default=3)
    ap.add_argument("--band", default="reader", choices=["reader", "scorer"],
                    help="reader = CR.head_band 0.06h..0.30h (production); "
                         "scorer = 0..0.35h, what the gold and both scorers use (R2.2c)")
    ap.add_argument("--out", default=".scratch/r2/plates")
    ap.add_argument("--crop-rows", type=int, default=0,
                    help="crop to the first N rows so a plate is legible at page width; 0 = whole band")
    ap.add_argument("--width", type=int, default=1400)
    args = ap.parse_args()

    want = list(STAGES) if args.stages == "all" else args.stages.split(",")
    bad = [s for s in want if s not in STAGES]
    if bad:
        raise SystemExit(f"unknown stage(s) {bad}; choose from {list(STAGES)}")

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    vol, sig = [k for k in W.WITNESSES if W.wid(*k) == "OT1-1609-B"][0]
    leaves = W.leaves(vol, sig)

    for i in args.leaf:
        band, ctx = build_ctx(i, leaves[i], args.splitter, args.nrows, args.band)
        for s in want:
            im = STAGES[s](band, ctx)
            if args.crop_rows:
                rs = ctx["rows"][:args.crop_rows]
                if rs:
                    b = max(max(g[1] for g in r) for r in rs)
                    im = im.crop((0, 0, im.width, min(im.height, b + 40)))
            if im.width != args.width:
                im = im.resize((args.width, max(1, int(im.height * args.width / im.width))),
                               Image.LANCZOS)
            path = out / f"leaf{i}-{s}-{args.splitter}-{args.band}.png"
            im.save(path)
            print(f"  {path}  {im.width}x{im.height}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

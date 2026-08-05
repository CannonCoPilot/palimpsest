#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""rung2_chapter_pairs.py — turn the FULLY WORKED CHAPTERS into R2 line-training pairs (item 2, 2026-07-29).

WHY THIS IS THE CHEAPEST LEVER ON R2. `reichenau_dr` was fine-tuned on **311 aligned lines** (264 train / 47
val) harvested by `rung2_prepare.py` from the 83 hand-made gold-page GT files, and reached 93.96% line
char-accuracy against a 93.0% base. Since then two chapters have been brought to 100% of cells >=0.90 against
FOUR references with the ſ-surface closed — which means there now exists, for 37 leaves x 4 witnesses, a verse
transcript that is *validated*, *diplomatic* and *ſ-faithful*, and that nobody has ever shown the recognizer.
This module converts it into line-image / line-text pairs, in the same format `rung2_prepare.py` emits, so the
two harvests merge into one training set.

WHAT THE TARGET TEXT IS, EXACTLY. `gen1_matrix.build()`'s `cells[(source, verse)]["text"]` — the page model's
own reading where it cleared the bar, and the R3 re-read where one was ADOPTED (adoption already required
beating the incumbent on the governing archaic arm AND clearing 0.90, with `s_arbiter` closing the ſ surface).
So for the R3-adopted cells this is a DISTILLATION of the vision model plus the arbiter back into the cheap
ſ-faithful recognizer, which is precisely what "improve R2 with data that already exists" means.

THREE HONESTY CONSTRAINTS, because a training set is the easiest place in a project to launder a result:

1. **The split is by LEAF, never by line.** Two lines of one leaf share typeface, inking, skew and scan
   geometry; splitting lines at random puts near-duplicates on both sides and inflates val accuracy. Leaves are
   assigned to train/val whole, and the assignment is recorded in the manifest.
2. **A row is only emitted if the validated text actually accounts for it.** Alignment is a monotone token
   match between the leaf's R2 stream and the chapter's validated stream; a row must have `--min-cover` of its
   tokens matched, and the emitted target is the ALIGNED SPAN, not a guess at what the row ought to say. Rows
   that fail are counted and reported, never silently dropped.
3. **ſ is checked, not assumed.** Every emitted target is counted for ſ, and a pair whose target has FEWER ſ
   than the row's own R2 reading is rejected outright — that would teach the recognizer to unlearn the surface
   it already has right. (The R3 arm modernizes ſ->s; `s_arbiter` restores it, and this is the check that the
   restoration actually reached the text being used as a target.)

Usage:
  ../ocr-venv/bin/python rung2_chapter_pairs.py [--chapters 1,16] [--out .rung2-chapters]
                                                [--min-cover 0.7] [--val-frac 0.2] [--dry-run]
"""
from __future__ import annotations

import argparse
import difflib
import json
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from PIL import Image                                    # noqa: E402

Image.MAX_IMAGE_PIXELS = None

import gen1_matrix as MX                                 # noqa: E402
import gen1_pagemodel as PM                              # noqa: E402
import gen1_pagemodel_eval as EV                         # noqa: E402
import jp2_page                                          # noqa: E402

PAD = 0.004          # crop padding as a fraction of page width/height around the row's own bounding box
MIN_ROW_TOKENS = 3   # a one- or two-token row carries almost no signal and inflates the pair count


def _fold(t: str) -> str:
    """Match fold for alignment ONLY — never emitted. ſ/s folded so an R2 reading and a restored target agree."""
    return t.strip(" \t.,;:·†‡*()[]").lower().replace("ſ", "s")


def _count_s(text: str) -> int:
    return text.count("ſ")


def leaf_pairs(ocr_dir: str, page: int, pd: dict, target: list[str], lex, *, min_cover: float):
    """Line pairs for one leaf: (row_bbox, r2_text, target_text) plus the rows that could not be accounted for.

    `target` is the witness's validated token stream for the whole chapter. The leaf's rows are matched into it
    monotonically, which is what lets a row that straddles a verse boundary still receive the right text — the
    verse grid is irrelevant here, only the token order is."""
    rows = PM.row_tokens(ocr_dir, page, pd, lex)
    if not rows:
        return [], {}
    flat, row_of = [], []
    for i, (ts, _r) in enumerate(rows):
        for t in ts:
            flat.append(t)
            row_of.append(i)
    sm = difflib.SequenceMatcher(a=[_fold(t) for t in flat], b=[_fold(t) for t in target], autojunk=False)
    # per R2 token, the index it matched in the validated stream (None if unmatched)
    mapped: list[int | None] = [None] * len(flat)
    for bl in sm.get_matching_blocks():
        for k in range(bl.size):
            mapped[bl.a + k] = bl.b + k
    out, rejected = [], {"too_short": 0, "no_match": 0, "low_cover": 0, "would_unlearn_s": 0,
                         "ink_absent_from_target": 0, "hyphen_broken_at_measure": 0}
    for i, (ts, r) in enumerate(rows):
        idx = [j for j, ri in enumerate(row_of) if ri == i]
        hits = [mapped[j] for j in idx if mapped[j] is not None]
        if len(ts) < MIN_ROW_TOKENS:
            rejected["too_short"] += 1
            continue
        if not hits:
            rejected["no_match"] += 1
            continue
        if len(hits) / len(ts) < min_cover:
            rejected["low_cover"] += 1
            continue
        # THE TARGET IS THE ALIGNED SPAN, inclusive of validated tokens the row's own reading missed entirely —
        # a DROPOUT is exactly what this data is meant to teach, so the span is taken from the first to the last
        # matched position rather than only the tokens that matched.
        tgt = " ".join(target[min(hits):max(hits) + 1])
        r2 = " ".join(ts)
        # NOT EVERY UNMATCHED R2 TOKEN IS AN R2 ERROR, and the two cases need opposite treatment. Re-align the
        # row against its own target span and read the opcodes:
        #
        #   replace — R2 misread a word that IS in the target (`broughr` -> `brought`).  KEEP: the best signal.
        #   insert  — the target has a word R2 dropped entirely.                          KEEP: teaches dropouts.
        #   delete  — R2 read a token the target does NOT contain (`of and to diuide` ->
        #             `and to diuide`, `pdf-S03a` ch1 p22 row12).                          REJECT.
        #
        # A `delete` is the dangerous one: the token may be real ink that the validated verse text legitimately
        # excludes (an apparatus mark, a margin intruder, a neighbouring verse's word), and training a target
        # that omits ink the crop contains teaches the recognizer to DELETE TEXT. That is the one failure this
        # whole project cannot afford in its recognizer, so the row is dropped rather than risked.
        # THE TEST MUST RUN ON THE **RAW** ROW, NOT THE ASSEMBLED ONE — found by LOOKING AT A WRITTEN CROP
        # (`line_00101.png`, S3 ch1 p26), which is the only way any of this was ever going to be caught:
        #
        #   image: `good. † And he " bleſſed them ſaying : Increaſe and multi-`
        #   target: `good. † And he bleſſed them ſaying : Increaſe and multiplie,`
        #
        # Two independent corruptions, both introduced by the page model's own (correct) assembly:
        #   * `clean_tokens` DROPS apparatus marks — here an inline footnote reference `"` that is REAL INK in
        #     the crop. Compared on assembled tokens there is no `delete` opcode to catch, because the token was
        #     already gone before the comparison.
        #   * `rejoin_break` JOINS a word broken at the measure, so the row's target ends `multiplie,` while the
        #     crop ends `multi-`. Training on that teaches the recognizer to HALLUCINATE the rest of a word.
        #
        # Both are right for reading a chapter and fatal for training a line recognizer, so the raw recognized
        # words are what must be accounted for: every one of them has to correspond to something in the target
        # (a match or a substitution), and a row broken at the measure is rejected outright.
        raw = [w["t"] for w in r]
        if raw and raw[-1].rstrip(".,;:").endswith("-"):
            rejected["hyphen_broken_at_measure"] += 1
            continue
        a_f = [_fold(t) for t in raw]
        b_f = [_fold(t) for t in target[min(hits):max(hits) + 1]]
        ops = difflib.SequenceMatcher(a=a_f, b=b_f, autojunk=False).get_opcodes()
        if any(tag == "delete" for tag, *_ in ops):
            rejected["ink_absent_from_target"] += 1
            continue
        if _count_s(tgt) < _count_s(r2):
            rejected["would_unlearn_s"] += 1   # would teach the model to UNLEARN a ſ it already reads right
            continue
        # CROP y FROM THE ROW'S MEDIAN BAND, CLAMPED TO THE NEIGHBOURS' MIDPOINTS. The union of the row's word
        # boxes is the wrong band: one tall initial or a long descender stretches it, and `line_00101.png` came
        # out carrying a full row of glyphs from the line ABOVE plus the tops of the line below — three lines of
        # image against one line of target. The median top/bottom is robust to a single tall glyph, and clamping
        # to halfway between this row and its neighbours guarantees no neighbouring x-height enters the crop.
        x0 = min(w["x0"] for w in r); x1 = max(w["x1"] for w in r)
        y0s = sorted(w["y0"] for w in r); y1s = sorted(w["y1"] for w in r)
        y0, y1 = y0s[len(y0s) // 2], y1s[len(y1s) // 2]
        prev_b = max((w["y1"] for w in rows[i - 1][1]), default=None) if i > 0 else None
        next_t = min((w["y0"] for w in rows[i + 1][1]), default=None) if i + 1 < len(rows) else None
        h = max(1, y1 - y0)
        top = y0 - 0.25 * h
        bot = y1 + 0.25 * h
        # The clamp is the midpoint RELAXED BY 0.15 of the row's height, because at the strict midpoint the
        # ascenders were shaved — `fifth` came back looking like `hfth` on `line_00030.png`. A recognizer needs
        # the full ascender; a sliver of the neighbour's descenders is normal in a line image (kraken's own line
        # polygons include them) and costs nothing.
        if prev_b is not None:
            top = max(top, (prev_b + y0) / 2 - 0.15 * h)
        if next_t is not None:
            bot = min(bot, (y1 + next_t) / 2 + 0.15 * h)
        out.append({"bbox": (x0, top, x1, bot), "r2": r2, "gt": tgt,
                    "ocr_dir": ocr_dir, "page": page, "row": i})
    return out, rejected


def harvest(chapters: list[int], out_dir: Path, *, min_cover: float, val_frac: float, dry: bool) -> dict:
    out_dir.mkdir(exist_ok=True)
    manifest = []
    stats = {"rows_emitted": 0, "leaves": 0, "cells_used": 0,
             "rejected": {"too_short": 0, "no_match": 0, "low_cover": 0, "would_unlearn_s": 0,
                          "ink_absent_from_target": 0, "hyphen_broken_at_measure": 0}}
    n = 0
    for ch in chapters:
        EV.set_locus("genesis", ch)
        board = MX.build(use_r3=True)
        lex = EV.book_lexicon()
        wb = PM.load("genesis", ch)
        for src, ocr_dir in MX.WITS.items():
            # the witness's validated token stream for the chapter, in verse order
            target: list[str] = []
            for v in board["verses"]:
                t = (board["cells"].get((src, v)) or {}).get("text") or ""
                if t:
                    target += t.split()
                    stats["cells_used"] += 1
            if not target:
                continue
            for pi in sorted((wb.get(ocr_dir) or {}), key=int):
                pd = wb[ocr_dir][str(pi)] if str(pi) in wb[ocr_dir] else wb[ocr_dir][pi]
                pairs, rej = leaf_pairs(ocr_dir, int(pi), pd, target, lex, min_cover=min_cover)
                for k, n_ in (rej or {}).items():
                    stats["rejected"][k] += n_
                stats["leaves"] += 1
                if not pairs:
                    continue
                im = None
                if not dry:
                    try:
                        im = jp2_page.load(ocr_dir, int(pi)).convert("L")
                    except Exception as e:                       # noqa: BLE001
                        print(f"  ! {ocr_dir} p{pi}: raster unavailable ({e}) — {len(pairs)} pairs skipped")
                        continue
                W, H = pd["page_px"]
                for p in pairs:
                    n += 1
                    stem = f"line_{n:05d}"
                    if im is not None:
                        x0, y0, x1, y1 = p["bbox"]
                        sx, sy = im.size[0] / W, im.size[1] / H
                        # y is already the clamped band from `leaf_pairs`; only x gets padding here.
                        box = (max(0, int((x0 - PAD * W) * sx)), max(0, int(y0 * sy)),
                               min(im.size[0], int((x1 + PAD * W) * sx)),
                               min(im.size[1], int(y1 * sy)))
                        im.crop(box).save(out_dir / f"{stem}.png")
                        (out_dir / f"{stem}.gt.txt").write_text(p["gt"] + "\n")
                    manifest.append({**p, "stem": stem, "chapter": ch, "source": src,
                                     "n_s_gt": _count_s(p["gt"]), "n_s_r2": _count_s(p["r2"])})
                    stats["rows_emitted"] += 1

    # LEAF-LEVEL SPLIT. Deterministic (sorted, strided) rather than random, so the split is reproducible without
    # a seed and a later re-harvest lands the same leaves on the same side.
    leaves = sorted({(m["ocr_dir"], m["page"]) for m in manifest})
    step = max(1, int(round(1 / val_frac))) if val_frac > 0 else 0
    val_leaves = {l for i, l in enumerate(leaves) if step and i % step == 0}
    for m in manifest:
        m["split"] = "val" if (m["ocr_dir"], m["page"]) in val_leaves else "train"
    rep = {"stats": stats, "n_leaves": len(leaves), "n_val_leaves": len(val_leaves),
           "n_train": sum(1 for m in manifest if m["split"] == "train"),
           "n_val": sum(1 for m in manifest if m["split"] == "val"),
           "min_cover": min_cover, "chapters": chapters, "lines": manifest}
    (out_dir / "_manifest.json").write_text(json.dumps(rep, ensure_ascii=False, indent=1))
    return rep


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--chapters", default="1,16")
    ap.add_argument("--out", default=".rung2-chapters")
    ap.add_argument("--min-cover", type=float, default=0.7)
    ap.add_argument("--val-frac", type=float, default=0.2)
    ap.add_argument("--dry-run", action="store_true", help="align and count, write no images")
    a = ap.parse_args()
    chs = [int(c) for c in a.chapters.split(",") if c.strip()]
    rep = harvest(chs, HERE / a.out, min_cover=a.min_cover, val_frac=a.val_frac, dry=a.dry_run)
    s = rep["stats"]
    print(f"\n=== chapters {chs} -> {a.out}{' (DRY RUN)' if a.dry_run else ''} ===")
    print(f"  validated cells consumed : {s['cells_used']}")
    print(f"  leaves visited           : {s['leaves']}")
    print(f"  rows EMITTED as pairs    : {s['rows_emitted']}")
    r = s["rejected"]
    print(f"  rows rejected            : {sum(r.values())}")
    print(f"    under {MIN_ROW_TOKENS} tokens        : {r['too_short']}")
    print(f"    matched NOTHING        : {r['no_match']}   <- apparatus/commentary prose, or unreadable")
    print(f"    under {a.min_cover:.0%} token cover  : {r['low_cover']}")
    print(f"    would unlearn a ſ      : {r['would_unlearn_s']}")
    print(f"    ink not in target      : {r['ink_absent_from_target']}   <- would teach DELETING ink")
    print(f"    broken at the measure  : {r['hyphen_broken_at_measure']}   <- would teach HALLUCINATING a word end")
    print(f"  leaf-level split         : {rep['n_train']} train / {rep['n_val']} val "
          f"over {rep['n_leaves']} leaves ({rep['n_val_leaves']} held out)")
    tot_s = sum(m["n_s_gt"] for m in rep["lines"])
    print(f"  ſ in the targets         : {tot_s} across {s['rows_emitted']} lines")
    print(f"\n  for comparison, the CURRENT R2 was trained on 311 lines (264/47).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

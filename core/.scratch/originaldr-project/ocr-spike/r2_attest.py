#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""r2_attest.py — a ſ-FAITHFUL ATTESTING ARM for the arbiter, read off the leaf by the fine-tuned recognizer.

THE GAP THIS FILLS, MEASURED. Across every `r3-residual-genesis-*.json` the verdict `CONTENT OK, ſ-SURFACE
OPEN` appears **1,158 times against 1,133 ADOPT**, and 1,142 of those cells have an R3 reading that already
passes ALL FOUR references at >=0.90. The remaining gap on the board is ~1,080 cells. They are the same cells.
The recognizer is not the binding constraint — the ATTESTATION is.

`s_arbiter.transfer(r2_text, r3_text)` closes a token's surface only where the attesting arm OBSERVED the
glyph, and the arm it is handed is `t["old_text"]`: the incumbent page-model text, which comes from the stored
corpus OCR. Where that OCR dropped or mangled a word, R3's token has no attested surface and the cell stays
OPEN however good the reading is. Meanwhile this project TRAINED a ſ-faithful recognizer for exactly this
(`reichenau_dr.mlmodel`, val 0.9396; `dr_v3_armA/best_0.9739.mlmodel` better still) and no module in the
campaign path referenced either of them.

WHAT THIS IS NOT. It is not a rule, a lexicon or a positional guess. `long_s_rule.restore_long_s` was rejected
at ~90.4% — about one invented glyph in ten published as the printed surface — and `s_lexicon` deliberately
refuses about three quarters of what it is asked, which is why it validates at 1.0000 on held-out GT. This
module adds no inference of any kind: it RE-READS THE PIXELS of the leaf with a recognizer that renders ſ, and
reports what that recognizer saw.

THE UNIT OF ATTESTATION IS THE LEAF, and the refusal is what makes it safe. The guidelines record that the
same word is set BOTH WAYS on one page (`shal` round and long within a few lines), so a book-wide or even
chapter-wide answer for a word would be a guess wearing an observation's clothes. So:

  * a leaf attests a spelling for a folded word only if EVERY occurrence of that word on that leaf agrees;
  * where the leaf shows two forms, this module returns NOTHING and the token stays unresolved for an eye.

That refusal is not a limitation to be tuned away later. It is the same discipline that makes `s_lexicon`
trustworthy, applied at the grain where the compositor actually varies.

Cache: `.r2-attest/<ocr_dir>-<page>.json` holds the raw recognized lines, so the attestation map can be
re-derived, audited or ablated without re-running the recognizer (which is the expensive part).

Usage:
  ../ocr-venv/bin/python r2_attest.py --chapter 39            # recognize every leaf the chapter uses
  ../ocr-venv/bin/python r2_attest.py --chapter 39 --report   # what it attests, and what it refuses
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

CACHE = HERE / ".r2-attest"
# The ſ-FAITHFUL fine-tune. `catmus-print-large` must never be used here: it modernizes ſ->s, so it would
# attest the absence of every glyph this module exists to observe.
MODEL = Path(os.environ.get("ODR_R2_MODEL", str(HERE / "models" / "dr_v3_armA" / "best_0.9739.mlmodel")))
ENABLED = os.environ.get("ODR_R2_ATTEST", "1") != "0"

_MAP_CACHE: dict[tuple[str, int], dict[str, str]] = {}


def _fold(t: str) -> str:
    return t.replace("ſ", "s")


def recognize_leaf(ocr_dir: str, page: int, *, force: bool = False) -> list[str]:
    """The leaf's lines as the ſ-faithful recognizer reads them. Cached — recognition is the expensive part."""
    CACHE.mkdir(exist_ok=True)
    f = CACHE / f"{ocr_dir}-{page}.json"
    if f.exists() and not force:
        return json.loads(f.read_text()).get("lines", [])
    import jp2_page
    import reocr_core
    pim = jp2_page.load(ocr_dir, page)
    seg = reocr_core.segment(pim)
    lines = [r["text"] for r in reocr_core.recognize_lines(MODEL, pim, seg)]
    f.write_text(json.dumps({"ocr_dir": ocr_dir, "page": page, "model": MODEL.name, "lines": lines},
                            ensure_ascii=False))
    return lines


def leaf_map(ocr_dir: str, page: int) -> dict[str, str]:
    """folded word -> the spelling THIS LEAF attests, for words the leaf is consistent about.

    A word the leaf sets two ways is omitted entirely rather than resolved by majority: the compositor really
    does mix the forms, and a majority vote over four occurrences is an inference, not an observation."""
    key = (ocr_dir, page)
    if key in _MAP_CACHE:
        return _MAP_CACHE[key]
    f = CACHE / f"{ocr_dir}-{page}.json"
    if not f.exists():
        _MAP_CACHE[key] = {}
        return {}
    seen: dict[str, set[str]] = collections.defaultdict(set)
    for line in json.loads(f.read_text()).get("lines", []):
        for tok in line.split():
            bare = tok.strip(" .,;:·†‡*()[]?!\"'")
            if not bare:
                continue
            seen[_fold(bare).lower()].add(bare)
    out = {}
    for fold, forms in seen.items():
        # Case is not a surface question; the ſ is. Collapse forms that differ only in case, and refuse only
        # when the leaf genuinely disagrees about a GLYPH.
        variants = {f.lower() for f in forms}
        if len(variants) == 1:
            out[fold] = sorted(forms, key=lambda s: (s[:1].islower(), s))[0]
    _MAP_CACHE[key] = out
    return out


def attest(ocr_dir: str, pages: list[int], token: str) -> str | None:
    """The ſ-faithful spelling of `token` observed on these leaves, or None if unobserved or inconsistent."""
    if not ENABLED:
        return None
    bare = token.strip(" .,;:·†‡*()[]?!\"'")
    if not bare:
        return None
    key = _fold(bare).lower()
    found: set[str] = set()
    for p in pages:
        got = leaf_map(ocr_dir, p).get(key)
        if got:
            found.add(got)
    if len(found) != 1:
        return None                       # unobserved, or the leaves disagree — refuse
    obs = found.pop()
    if _fold(obs).lower() != key:         # paranoia: never return a different word
        return None
    # Restore the token's own punctuation and capitalisation shape around the observed letters.
    lead = token[:len(token) - len(token.lstrip(" .,;:·†‡*()[]?!\"'"))]
    trail = token[len(token.rstrip(" .,;:·†‡*()[]?!\"'")):]
    if bare[:1].isupper() and obs[:1].islower():
        obs = obs[:1].upper() + obs[1:]
    if bare[:1].islower() and obs[:1].isupper():
        obs = obs[:1].lower() + obs[1:]
    return lead + obs + trail


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--chapter", type=int, required=True)
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    import gen1_pagemodel as PM
    import gen1_pagemodel_eval as EV
    EV.BOOK, EV.CHAPTER, PM.CHAPTER = "genesis", a.chapter, a.chapter
    wb = PM.load("genesis", a.chapter)
    n_lines = 0
    for od in sorted(wb):
        for pg in sorted(wb[od], key=int):
            lines = recognize_leaf(od, int(pg), force=a.force)
            n_lines += len(lines)
            print(f"  {od} p{pg}: {len(lines)} lines", flush=True)
    print(f"recognized {n_lines} lines with {MODEL.name}")
    if a.report:
        for od in sorted(wb):
            pages = [int(p) for p in wb[od]]
            merged: dict[str, set[str]] = collections.defaultdict(set)
            for p in pages:
                for k, v in leaf_map(od, p).items():
                    merged[k].add(v)
            longs = {k: sorted(v)[0] for k, v in merged.items() if any("ſ" in x for x in v)}
            print(f"\n{od}: {len(merged)} words attested consistently on their leaf; "
                  f"{len(longs)} carry a long-ſ")
            for k, v in list(longs.items())[:12]:
                print(f"     {k!r} -> {v!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

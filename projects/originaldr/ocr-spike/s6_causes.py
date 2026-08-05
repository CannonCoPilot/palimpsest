#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""s6_causes.py — SIZE THE THREE S6 CAUSES SEPARATELY, over the whole book (§13, CAMPAIGN-STATUS step 1).

WHY THIS EXISTS. "S6 is the weakest source" is not one problem, it is at least three wearing one label, and
EIGHT apparatus-separation attempts are pinned OFF in this tree because each was aimed at their AVERAGE — each
convinced on the examples its author looked at and failed on the population. Nothing can sensibly be built
until the three are counted apart, and no count existed.

THE BUCKETS, and the signature each leaves in a failing cell:

  NO-TEXT     the verse was never localized on this source at all — no span, no text. A coverage failure
              upstream of every recognizer; no rule about columns or bands can touch it.
  INTERLEAVE  annotation prose sharing rows with scripture on a MIXED leaf: foreign material pushed BETWEEN
              the verse's own words (`God endeo &gouerning his worke ... reſted the ſeuenth al things, day`).
  TRUNCATED   we hold only part of the verse — a large deletion at the head or tail. Segmentation, not reading.
  MISREAD     the recognizer got the letters wrong (`Abtaham`, `truit ot the tree`, `ihould`). Substitution in
              place, and the substituted pair still looks like the word it should be.
  DIVERGE     read cleanly, but the words are not the reference's words — the 1635-vs-1609 collation question,
              which no recognizer closes.

TWO INSTRUMENTS, AND THE DISAGREEMENT BETWEEN THEM IS THE ERROR BAR.

1. **Shape.** Where does the mismatch sit? Foreign material appearing between the verse's own words, with
   nothing missing from the reference there, is an insertion — measured as our side being LONGER than the
   reference's inside one alignment opcode, with the excess tokens unlike anything the reference has nearby.
   Substitution in place is a misreading or a variant instead.
2. **Attribution.** Where did the inserted words COME FROM? The s_dismas PDF carries every chapter's
   annotations, so a word in a failing cell that appears in that chapter's apparatus and in NONE of its verses
   is attributable bleed rather than an inference about a ratio.

They agree in direction and not in detail, and the report prints both: INTERLEAVE cells are ~4.5x more likely
than MISREAD cells to carry an attributable apparatus word (46% vs 10%), which is real signal — but ~23% of
DIVERGE cells carry one too, so **the INTERLEAVE count is a LOWER BOUND on apparatus contamination, not a
count of it.** Read the two together: about a fifth of S6's failing cells are apparatus, and about half are
plain misreading.

THE FIRST VERSION OF THIS FILE ANSWERED THE OPPOSITE, AND CONVINCINGLY. Classifying on aggregate overlap
(recall high AND precision low) it reported 4 interleaved cells against 414 divergent ones — because two words
of marginal text pushed into a twelve-word verse move neither ratio. Only printing worked examples per bucket
exposed it. **Do not trust a bucket table from this file without reading its examples.**

Usage:
  ../ocr-venv/bin/python s6_causes.py                 # all 50 chapters, summary + per-chapter table
  ../ocr-venv/bin/python s6_causes.py --source S6     # any source
  ../ocr-venv/bin/python s6_causes.py --examples 3    # show N worked examples per bucket
"""
from __future__ import annotations

import argparse
import difflib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

CAMPAIGN = HERE / ".campaign"
BOOK = "genesis"

# THE FIRST VERSION OF THIS FILE GOT THE ANSWER WRONG, CLEANLY AND CONVINCINGLY, and the way it was wrong is
# worth keeping. It classified on aggregate overlap — recall high AND precision low meant INTERLEAVE — and
# reported 4 interleaved cells against 414 "divergent" ones. But `the heauens therfore the earth were fully
# finiſhed, and 17conſeruins al the furniture of them` scores recall 0.93 AND precision 0.93: two words of
# marginal text pushed into a twelve-word verse barely move either ratio. The bucket that mattered most was
# the one the metric could least see. Only printing worked examples per bucket exposed it.
#
# The real signature of a column that was never separated is not "how much overlaps" but WHERE the mismatch
# sits: foreign material appears BETWEEN the verse's own words, with nothing missing from the reference at
# that point. That is an INTERIOR PURE INSERTION in the alignment, and difflib names it exactly — an `insert`
# opcode (reference side empty) that is neither the head nor the tail. Divergence and misreading produce
# `replace` opcodes instead: something stands where something else should, one for one.
INSERT_MIN = 1              # tokens in an interior insertion before it counts as foreign material
TRUNC_SHARE = 0.30          # a head/tail `delete` this large means we hold only part of the verse
MISREAD_CHAR_SIM = 0.55     # a substituted pair this alike at character level is a misreading, not a variant


def _norm(t: str) -> list[str]:
    return [w.strip(" .,;:·†‡*()[]?!").lower().replace("ſ", "s").replace("v", "u").replace("j", "i")
            for w in (t or "").split() if w.strip(" .,;:")]


def classify(ours: str, ref: str) -> tuple[str, float, float]:
    """(bucket, recall, precision) for one failing cell against the archaic reference.

    Buckets are decided on the SHAPE of the alignment, in priority order: interior insertions first (they are
    the apparatus signature and can coexist with anything), then truncation, then the character-level
    character of the substitutions."""
    a, b = _norm(ours), _norm(ref)
    if not a:
        return "NO-TEXT", 0.0, 0.0
    if not b:
        return "NO-REF", 0.0, 0.0
    sm = difflib.SequenceMatcher(a=a, b=b, autojunk=False)
    ops = sm.get_opcodes()
    matched = sum(i2 - i1 for tag, i1, i2, _j1, _j2 in ops if tag == "equal")
    recall, precision = matched / len(b), matched / len(a)

    # LOOKING FOR BARE `insert` OPCODES FINDS ALMOST NOTHING, because difflib folds an insertion that sits
    # next to any mismatch into a single `replace`. In `...and [17conſeruins] al the furniture...` the
    # reference is missing an `&` a few tokens earlier, and the whole region comes back as one `replace`.
    # So the excess is measured directly — our side longer than the reference's inside one opcode — and the
    # excess tokens must be FOREIGN: unlike anything the reference has nearby. That is what separates a column
    # bleeding in (`17conſeruins`, `The third`, `12.de Gen.`) from a misreading of a word that belongs there
    # (`Abtaham` for `Abraham`), which is a near-match in place and no excess at all.
    foreign_in = 0
    for k, (tag, i1, i2, j1, j2) in enumerate(ops):
        if tag not in ("insert", "replace") or not (0 < k < len(ops) - 1):
            continue
        excess = (i2 - i1) - (j2 - j1)
        if excess <= 0:
            continue
        window = b[max(0, j1 - 2):j2 + 2]
        foreign = [x for x in a[i1:i2]
                   if max((difflib.SequenceMatcher(a=x, b=y, autojunk=False).ratio() for y in window),
                          default=0.0) < MISREAD_CHAR_SIM]
        foreign_in += min(excess, len(foreign))
    if foreign_in >= INSERT_MIN and matched:
        return "INTERLEAVE", recall, precision

    edge_del = sum(j2 - j1 for k, (tag, _i1, _i2, j1, j2) in enumerate(ops)
                   if tag == "delete" and (k == 0 or k == len(ops) - 1))
    if edge_del / len(b) >= TRUNC_SHARE:
        return "TRUNCATED", recall, precision

    sims, n_sub = [], 0
    for tag, i1, i2, j1, j2 in ops:
        if tag != "replace":
            continue
        for x, y in zip(a[i1:i2], b[j1:j2]):
            sims.append(difflib.SequenceMatcher(a=x, b=y, autojunk=False).ratio())
            n_sub += 1
    if not n_sub:
        return "DIVERGE", recall, precision
    return (("MISREAD" if sum(sims) / n_sub >= MISREAD_CHAR_SIM else "DIVERGE"), recall, precision)


def apparatus_lexicon() -> dict[int, set[str]]:
    """Per chapter, the words that occur in the APPARATUS and nowhere in the scripture.

    A SECOND INSTRUMENT, AND AN INDEPENDENT ONE. The shape test above asks what an insertion looks like; this
    asks where the inserted words CAME FROM, which is a question with a real answer on disk. The s_dismas PDF
    carries every chapter's annotations and marginal notes in full — the same material `ref_repair_s_dismas`
    strips out of the scripture — so a token in a failing S6 cell that appears in chapter N's apparatus and in
    none of chapter N's verses is attributable bleed, not a guess about a ratio.

    (`odr_com`'s scrape also carries a `notes` field, and it is NOT usable for this: only 12 of 50 Genesis
    chapters have one, and what they hold is the chapter ARGUMENT rather than the marginalia.)"""
    import ref_repair_s_dismas as RSD
    import ref_renumber as RR
    blocks = RSD.chapter_blocks(RSD.pdf_lines())
    scripture = RR.load_corrected("s_dismas")
    out: dict[int, set[str]] = {}
    for ch, block in blocks.items():
        appar: list[str] = []
        seen_hdr = False
        for i, ln in enumerate(block):
            if ln.strip().lower() in ("annotations", "annotation"):
                seen_hdr = True
            if seen_hdr:
                appar.append(ln)
        # the page-foot notes too: whatever `_strip_page_furniture` takes out of the body
        body = block[:len(block) - len(appar)] if appar else block
        appar += [ln for ln in body if ln not in set(RSD._strip_page_furniture(body, "Genesis"))]
        appar_w = set(_norm(" ".join(appar)))
        script_w = set(_norm(" ".join(v for k, v in scripture.items()
                                      if k.startswith(f"scripture/{BOOK}/{ch}/"))))
        out[ch] = appar_w - script_w
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default="S6")
    ap.add_argument("--examples", type=int, default=0)
    ap.add_argument("--json", help="write the per-cell classification here")
    a = ap.parse_args()

    import ref_renumber as RR
    refs = RR.load_corrected("odr_com")
    lex = apparatus_lexicon()

    rows, per_ch = [], defaultdict(Counter)
    examples = defaultdict(list)
    for ch in range(1, 51):
        f = CAMPAIGN / f"matrix-{BOOK}-{ch}.json"
        if not f.exists():
            continue
        m = json.loads(f.read_text())
        for cell in m.get("open", []):
            if cell.get("src") != a.source:
                continue
            v = cell["verse"]
            ref = refs.get(f"scripture/{BOOK}/{ch}/{v}") or ""
            bucket, rec, prec = classify(cell.get("text", ""), ref)
            # the independent attribution: our words that live in this chapter's apparatus and in none of
            # its verses
            ours_w, ref_w = set(_norm(cell.get("text", ""))), set(_norm(ref))
            bleed = sorted((ours_w - ref_w) & lex.get(ch, set()))
            per_ch[ch][bucket] += 1
            rows.append({"chapter": ch, "verse": v, "bucket": bucket, "worst": cell.get("worst"),
                         "page": cell.get("from"), "recall": round(rec, 3), "precision": round(prec, 3),
                         "apparatus_bleed": bleed})
            if len(examples[bucket]) < a.examples:
                examples[bucket].append((ch, v, cell.get("from"), rec, prec,
                                         (cell.get("text") or "")[:150], ref[:150]))

    total = Counter(r["bucket"] for r in rows)
    n = len(rows)
    print(f"{a.source}: {n} open cells across {len(per_ch)} chapters\n")
    print(f"{'bucket':<11} {'cells':>6} {'share':>7}   what it means for the build")
    meaning = {
        "INTERLEAVE": "within-leaf column separation — UNBUILT, and this is its true size",
        "TRUNCATED":  "verse segmentation / leaf coverage — we hold only part of the verse",
        "MISREAD":    "recognizer accuracy — R2/R3 territory",
        "DIVERGE":    "collation judgement — no recognizer closes it",
        "NO-TEXT":    "localizer coverage — upstream of every recognizer",
        "NO-REF":     "reference gap — should be zero after the 07-31 session",
    }
    for b, c in total.most_common():
        print(f"{b:<11} {c:>6} {c / max(1, n):>6.1%}   {meaning.get(b, '')}")

    print(f"\n{'ch':>3} " + " ".join(f"{b:>10}" for b in meaning) + "   total")
    for ch in sorted(per_ch):
        c = per_ch[ch]
        print(f"{ch:>3} " + " ".join(f"{c.get(b, 0):>10}" for b in meaning) + f"   {sum(c.values()):>5}")

    # AGREEMENT BETWEEN THE TWO INSTRUMENTS — reported, not assumed. A shape call that the attribution
    # contradicts is a call to distrust, and the size of that disagreement is the error bar on this table.
    print()
    for b in meaning:
        cells = [r for r in rows if r["bucket"] == b]
        if not cells:
            continue
        with_bleed = sum(1 for r in cells if r["apparatus_bleed"])
        print(f"{b:<11} {len(cells):>5} cells, {with_bleed:>4} ({with_bleed / len(cells):>5.1%}) carry a word "
              f"attributable to this chapter's apparatus")

    # THE CUT THAT DECIDES IT, and it needs no classifier at all. Edition divergence is a property of the
    # PAGE ALL FOUR SOURCES PHOTOGRAPHED, so it must fail in all four at the same verse. A cell that fails in
    # this source ALONE cannot be the edition diverging — whatever it is, the other three read it correctly.
    shared = alone = 0
    for ch in sorted(per_ch):
        m = json.loads((CAMPAIGN / f"matrix-{BOOK}-{ch}.json").read_text())
        by: dict[str, set] = {}
        for c in m.get("open", []):
            by.setdefault(c["src"], set()).add(c["verse"])
        mine = by.get(a.source, set())
        rest = [by.get(s, set()) for s in ("S1", "S3", "S9", "S6") if s != a.source]
        shared += len(mine.intersection(*rest)) if rest else 0
        alone += len(mine - set().union(*rest)) if rest else 0
    print(f"\nCROSS-SOURCE: of {a.source}'s open cells, {shared} also fail in ALL of the other three at the "
          f"same verse\n              (the ceiling on edition divergence — it is a property of the page, so "
          f"it cannot fail in one source alone),\n              and {alone} fail in {a.source} ALONE.")

    for b, exs in examples.items():
        print(f"\n=== {b} examples")
        for ch, v, page, rec, prec, ours, ref in exs:
            print(f"  {BOOK} {ch}:{v} on {page}  recall={rec:.2f} precision={prec:.2f}")
            print(f"     ours: {ours}")
            print(f"     ref : {ref}")

    if a.json:
        Path(a.json).write_text(json.dumps({"source": a.source, "thresholds": {
            "INSERT_MIN": INSERT_MIN, "TRUNC_SHARE": TRUNC_SHARE,
            "MISREAD_CHAR_SIM": MISREAD_CHAR_SIM}, "totals": dict(total), "cells": rows},
            ensure_ascii=False, indent=2))
        print(f"\n[wrote] {a.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

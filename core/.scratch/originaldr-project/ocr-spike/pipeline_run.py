#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""pipeline_run.py — run a chapter through the seven stages of OCR-MASTERPLAN-V2 and report what each did.

WHY THIS EXISTS. The masterplan describes seven stages; the code describes none of them. `chapter_campaign.py`
prints one line (a score), `triage.py` prints an attribution, and everything between acquisition and the board
happens inside `gen1_pagemodel` with no external account of it. So the pipeline could only be *read*, never
*watched* — and a stage that cannot be watched is a stage whose failures show up three layers downstream as a
number that is merely low.

This runner is READ-ONLY. It changes nothing, adopts nothing, and tunes nothing. It re-executes the stages
that exist against the artifacts on disk and reports, per stage: what went in, what came out, and — the part
the board cannot show — WHICH SCOPE decided each thing (§3 of the masterplan: source / book / chapter / page).

WHAT IS REAL TODAY AND WHAT IS NOT. The plan's stages 1 and 3 are unbuilt, and this runner says so out loud at
the point where they would execute rather than quietly routing around them:

    STAGE 1  GEOMETRY   the trained region model is NOT BUILT -> the 371-constant fallback runs, as the plan's
                        "the constants stay until beaten" clause specifies. Printed as FALLBACK, per leaf.
    STAGE 3  ALIGN      the forced-alignment GT engine is NOT BUILT -> no line-level ground truth is produced,
                        so stage 2 is running an un-fine-tuned recognizer. Printed as the size of the corpus
                        it WOULD consume, so the missing stage has a number attached to it and not a shrug.

A stage that is missing is reported as missing. That is the whole discipline: `NOT BUILT` is a loud state,
never a silent pass-through (No Silent Degradation).

Usage:
    ../ocr-venv/bin/python pipeline_run.py --chapters 21          # one chapter, all seven stages
    ../ocr-venv/bin/python pipeline_run.py --chapters 21,49,15    # several
    ../ocr-venv/bin/python pipeline_run.py --chapters 21 --leaves # add the per-leaf geometry scope table
"""
from __future__ import annotations

import argparse
import collections
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import gen1_pagemodel as PM                    # noqa: E402
import gen1_pagemodel_eval as EV               # noqa: E402
import gen1_matrix as MX                       # noqa: E402
import triage as TR                            # noqa: E402

BAR = 0.90
ARCHAIC = ("s_dismas", "odr_com")
MODERN = ("sabates_a", "madueke_b")

# THE APPARATUS VOCABULARY, DELIBERATELY TIGHT. The first version of this scan false-positived on
# `interpretation` and `interprete`, which are real scripture in ch40 — a validity audit that cries wolf gets
# switched off, and then the class it was built for goes unseen. Every pattern here is anchored on the
# punctuation or capitalisation that makes a marginal citation what it is, not on a word stem.
APPARATUS = re.compile(
    r"(?:\bChri[ſs]o[ſs]t\b|\bAmbro?[ſs]?\.|\bAug\.|\bHiero\.|\bTheodor\.|\bTradit\.|\bMoral\.|"
    r"\bho\.\s*\d|\bli\.\s*\d|\bq\.\s*\d|\bc\.\s*\d+\.|\bS\.\s*[A-Z]|\bGen\.\s*\d|\bHebr[.æ])")

# THE SECOND ARM, AND THE MISTAKE THAT PRODUCED IT. An all-caps token looks like a running head, so the first
# version of this scan flagged `\b[A-Z]{4,}\b` — and returned `THE SCEPTER SHAL NOT BE TAKEN AWAY FROM IVDAS`
# (gen 49:10) and `THY SALVATION` (49:18). The Douay-Rheims sets its messianic passages in full capitals: the
# pattern had found the book's own typography and called it contamination. Capitalisation cannot decide this
# on its own. What CAN: an all-caps token that does not appear in this verse's own reference — which leaves
# `MMND` (49:1 S6, a drop-cap `AND` destroyed), `ACOB` (32:1 S6), `TAEN` (49:10 S9, for `TAKEN`) and drops
# every genuine capitalised word. A verse can PASS at 0.90 with its first word annihilated; that is the class.
CAPS = re.compile(r"\b[A-Z]{3,}\b")


def scope_of(od: str, page: int) -> tuple[str, tuple[float, float]]:
    """Which tuning scope decided this leaf's body band — the §3 hierarchy, read off the live model.

    Most specific wins, and the winner is NAMED. This is the table that convicted the campaign twice: ten
    PAGE_OVERRIDE entries carrying a right bound tuned to four decimals beside an identical default left bound
    (Rule C), and seven even jp2-S06 leaves that the parity sweep skipped entirely (ch10 walk). Neither was
    visible until the scope, rather than the value, was printed.
    """
    src = PM.SOURCE_MODEL.get(od, {})
    chm = PM.chapter_model(od) or {}
    pg = PM.PAGE_OVERRIDE.get((od, page), {})
    merged = {**src, **chm, **pg}
    band = merged.get("body", (0.0, 1.0))
    if "body" in pg:
        return "PAGE", band
    if "body" in chm:
        return "CHAPTER", band
    return "SOURCE", band


def run_chapter(ch: int, show_leaves: bool = False) -> dict:
    EV.set_locus("genesis", ch)
    out: dict = {"chapter": ch}
    say = print

    say(f"\n{'=' * 100}\nGENESIS {ch} — seven stages\n{'=' * 100}")

    # ---------------------------------------------------------------- STAGE 0: ACQUIRE
    wb = PM.load("genesis", ch)
    leaves = {s: sorted(int(p) for p in wb.get(od, {})) for s, od in EV.WITS.items()}
    say("\nSTAGE 0  ACQUIRE                                                            [exists]")
    for s, od in EV.WITS.items():
        lv = leaves[s]
        px = ""
        if lv:
            rec = wb[od][str(lv[0])]
            px = f"  raster {rec['page_px'][0]}x{rec['page_px'][1]}"
        say(f"   {s} {od:26s} {len(lv):>2} leaves  {lv}{px}")
    out["leaves"] = {s: len(v) for s, v in leaves.items()}

    # ---------------------------------------------------------------- STAGE 1: GEOMETRY
    say("\nSTAGE 1  GEOMETRY   region model NOT BUILT -> constants                   [FALLBACK]")
    scopes = collections.Counter()
    rows = []
    for s, od in EV.WITS.items():
        for p in leaves[s]:
            sc, band = scope_of(od, p)
            scopes[(s, sc)] += 1
            rows.append((s, od, p, sc, band))
    for s in EV.WITS:
        tot = sum(n for (ss, _), n in scopes.items() if ss == s)
        parts = " ".join(f"{k[1]}={n}" for k, n in sorted(scopes.items()) if k[0] == s)
        say(f"   {s}  {tot:>2} leaves banded by:  {parts or '(none)'}")
    say(f"   {'':4}{'-' * 88}")
    say("   the region model would return POLYGONS here, in the baselines' own coordinate space;")
    say("   a fraction cannot describe a leaf whose note column and body are 0.002 of page width apart.")
    if show_leaves:
        say(f"\n   {'src':4}{'leaf':>5}  {'scope':8} band")
        for s, od, p, sc, band in rows:
            mark = "  <- source default, never varied for this leaf" if sc == "SOURCE" else ""
            say(f"   {s:4}{p:>5}  {sc:8} ({band[0]:.3f}, {band[1]:.3f}){mark}")
    out["scopes"] = {f"{k[0]}:{k[1]}": n for k, n in scopes.items()}

    # ---------------------------------------------------------------- STAGE 2: RECOGNISE
    say("\nSTAGE 2  RECOGNISE  kraken R2 checkpoint, no per-edition fine-tune          [exists]")
    tax = {}
    for s, od in EV.WITS.items():
        nl = nw = out_band = 0
        for p in leaves[s]:
            rec = wb[od][str(p)]
            W = rec["page_px"][0]
            _, band = scope_of(od, p)
            lo, hi = band[0] * W, band[1] * W
            for L in rec["lines"]:
                nl += 1
                for w in L["words"]:
                    nw += 1
                    if w["x0"] < lo or (w["x0"] + w["x1"]) / 2 > hi:
                        out_band += 1
        tax[s] = (nl, nw, out_band)
        pct = (100.0 * out_band / nw) if nw else 0.0
        say(f"   {s}  {nl:>4} lines  {nw:>6} words   {out_band:>5} outside the band ({pct:4.1f}%)"
            f"  <- apparatus, heads, catchwords AND anything stage 1 is clipping")
    out["recognise"] = tax

    # ---------------------------------------------------------------- STAGE 3: ALIGN
    total_lines = sum(v[0] for v in tax.values())
    say("\nSTAGE 3  ALIGN      forced-alignment GT engine NOT BUILT                  [NOT BUILT]")
    say(f"   {total_lines} recognised lines in this chapter alone would be alignment candidates;")
    say("   ~931 leaves book-wide. No line-level ground truth is produced, so stage 2 stays un-fine-tuned")
    say("   at ~6% CER against a published ~2% for book-specific models. THIS IS THE BINDING GAP.")
    out["align"] = {"built": False, "candidate_lines": total_lines}

    # ---------------------------------------------------------------- STAGE 4: ASSEMBLE
    lex = EV.book_lexicon()
    spans = {s: EV.witness_spans(od, wb.get(od, {}), lex) for s, od in EV.WITS.items()}
    say("\nSTAGE 4  ASSEMBLE   localize -> hyphen-join -> clean -> verses               [exists]")
    for s in EV.WITS:
        prov = collections.Counter((sp.get("from") or "?") for sp in spans[s].values())
        leafy = sum(n for k, n in prov.items() if str(k).startswith("p"))
        chapterwide = prov.get("chapter", 0)
        empty = sum(1 for sp in spans[s].values() if not (sp.get("text") or "").strip())
        say(f"   {s}  {len(spans[s]):>3} verses   {leafy:>3} located on a leaf, "
            f"{chapterwide:>3} only as a chapter-stream fallback, {empty:>2} empty")
    out["assemble"] = {s: len(spans[s]) for s in EV.WITS}

    # ---------------------------------------------------------------- STAGE 5: ESCALATE
    store = MX.r3_store()
    r3 = json.loads(store.read_text()) if store.exists() else {}
    say("\nSTAGE 5  ESCALATE   R2 (kraken ſ-faithful) / R3 (olmOCR re-read)            [exists]")
    if r3:
        bysrc = collections.Counter(k.split(":")[0] for k in r3)
        say(f"   {len(r3)} R3 re-reads adopted (beat the incumbent AND cleared the bar): "
            f"{dict(sorted(bysrc.items()))}")
        say(f"   store {store.name}")
    else:
        say(f"   no R3 adoptions for this chapter ({store.name} absent or empty)")
    out["escalate"] = len(r3)

    # ---------------------------------------------------------------- STAGE 6: SCORE + VALIDITY
    mpath = HERE / f".campaign/matrix-genesis-{ch}.json"
    if not mpath.exists():
        say("\nSTAGE 6  SCORE      NO MATRIX ON DISK — run chapter_campaign.py --phase measure first")
        return out
    m = json.loads(mpath.read_text())
    say("\nSTAGE 6  SCORE      verses x witnesses x references -> board                [exists]")
    say(f"   {m['n_pass']}/{m['n_cells']} = {m['rate']:.4f}   all-fail verses {m['n_all_fail']}   "
        f"ref means {m['ref_means']}")
    say(f"   per source: {m['src_rates']}")

    # -- validity audit A: the edition split (the board cannot see this by construction)
    split = exact = 0
    for v, row in m["cellgrid"].items():
        for s, c in row.items():
            sc = {r: x for r, x in (c.get("score") or {}).items() if x is not None}
            if not sc or min(sc.values()) >= BAR:
                continue
            passing = {r for r, x in sc.items() if x >= BAR}
            failing = set(sc) - passing
            if (passing == set(ARCHAIC) and failing == set(MODERN)) or \
               (passing == set(MODERN) and failing == set(ARCHAIC)):
                split += 1
                if max(sc.values()) >= 0.98:
                    exact += 1
    say(f"   VALIDITY A — reference-family split: {split} open cells fail ONLY the family they do not belong")
    say(f"                to; {exact} of those score >= 0.98 against their own family (transcribed EXACTLY,")
    say("                marked failing). These are edition facts, not OCR defects.")

    # -- validity audit B: apparatus inside PASSING cells
    leaks = []
    refs_by_verse = m.get("refs_by_verse") or {}
    for v, row in m["cellgrid"].items():
        refwords = {TR.norm(w) for rv in (refs_by_verse.get(v) or {}).values()
                    if isinstance(rv, str) for w in rv.split()}
        for s, c in row.items():
            sc = {r: x for r, x in (c.get("score") or {}).items() if x is not None}
            if not sc or min(sc.values()) < BAR:
                continue
            txt = c.get("text") or ""
            hit = APPARATUS.search(txt)
            if hit:
                leaks.append((int(v), s, "apparatus", hit.group(0), txt[:90]))
                continue
            # An all-caps token is only evidence if this verse's own references do not contain it.
            bad = [t for t in CAPS.findall(txt) if TR.norm(t) and TR.norm(t) not in refwords]
            if bad:
                leaks.append((int(v), s, "caps-anomaly", " ".join(bad[:3]), txt[:90]))
    say(f"   VALIDITY B — apparatus / caps-anomaly inside PASSING cells: {len(leaks)}")
    for v, s, kind, tok, txt in leaks[:6]:
        say(f"                v{v} {s} [{kind}] {tok!r}  {txt}")

    # -- attribution: which layer owns the residual
    boxes = TR.Boxes()
    counts, detail = TR.triage_chapter(ch, boxes)
    say(f"   ATTRIBUTION — GEOMETRY {counts['GEOMETRY']}  RECOGNITION {counts['RECOGNITION']}  "
        f"unattributed {counts['unattributed']}  complete-but-failing {counts['complete-but-failing']}")
    geo = collections.Counter(d[0].rsplit(" ", 1)[0] for d in detail if d[1].startswith("recoverable"))
    if geo:
        say("                geometry leaves: " + " ".join(f"{k}×{n}" for k, n in geo.most_common(6)))
    out["score"] = {"pass": m["n_pass"], "cells": m["n_cells"], "rate": m["rate"],
                    "split": split, "split_exact": exact, "apparatus_in_passing": len(leaks),
                    "GEOMETRY": counts["GEOMETRY"], "RECOGNITION": counts["RECOGNITION"],
                    "unattributed": counts["unattributed"]}
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--chapters", required=True, help="comma list")
    ap.add_argument("--leaves", action="store_true", help="print the per-leaf geometry scope table")
    a = ap.parse_args(argv)
    results = [run_chapter(int(c), a.leaves) for c in a.chapters.split(",") if c.strip()]

    say = print
    say(f"\n{'=' * 100}\nROLL-UP\n{'=' * 100}")
    say(f"{'ch':>4} {'board':>12} {'GEOM':>5} {'RECOG':>6} {'unatt':>6} {'split':>6} {'exact':>6} "
        f"{'appar':>6}   scope of the leaves")
    for r in results:
        s = r.get("score")
        if not s:
            say(f"{r['chapter']:>4}   (no matrix)")
            continue
        sc = r.get("scopes", {})
        scope_s = " ".join(f"{k}={v}" for k, v in sorted(sc.items()) if v)
        say(f"{r['chapter']:>4} {s['pass']:>5}/{s['cells']:<6} {s['GEOMETRY']:>5} {s['RECOGNITION']:>6} "
            f"{s['unattributed']:>6} {s['split']:>6} {s['split_exact']:>6} {s['apparatus_in_passing']:>6}   "
            f"{scope_s}")
    say("\nSTAGES NOT BUILT: 1 (trained region model — constants in fallback) · 3 (forced-alignment GT).")
    say("Everything above ran against artifacts on disk; nothing was adopted, tuned, or written.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

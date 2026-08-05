#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""divergence.py — DIV-1: the full between-witness divergence matrix, janvier-cut (2026-07-22).

§9 of the master plan. Establishes the between-witness NOISE FLOOR — the yardstick for "is an OCR diff real
or within witness noise" — and the routing signal for §7 alarm 2 (cross-source disagreement gates IN a locus
for reOCR; it NEVER accepts a reading). Corrects the span-artifact that produced the old gt_rescore 0.80
numbers: every witness's chapter text is re-cut to the SAME janvier grid (via verse_seg) before comparison, so
divergence reflects genuine textual difference, not versification mismatch.

Witnesses (reads/): sabates_a (=janvier, modern, 76 books) · madueke_b (modern, 73) · s_dismas (archaic, 52) ·
odr_com (archaic, 39). Plus Gold (per GT locus) vs each. Two identity axes per pair: CONTENT (fold_modern —
collapses archaic/modern spelling) and SURFACE (fold_archaic — keeps archaic spelling). Same-register pairs are
judged on surface; cross-register pairs report both (content is the meaningful axis there).

HONEST by construction: where a witness lacks a book the cell is `absent` (not 0); the known witness DEFECTS
(odr_com Ps-118 versification 175 vv in range 1..207; s_dismas \\hfil pdftotext artifacts) are SURFACED as
per-chapter anomalies, never averaged away. No consensus text is built (retired) — divergence is a spread, not
a fabricated truth.

Usage:
  ocr-venv/bin/python ocr-spike/divergence.py                # GT-locus chapters (default) + Gold legs
  ocr-venv/bin/python ocr-spike/divergence.py --sample 40    # + a stratified non-gold sample (noise floor)
  ocr-venv/bin/python ocr-spike/divergence.py --json divergence-report.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from itertools import combinations
from pathlib import Path
from statistics import mean

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from char_identity import edit_ratio, fold_archaic, fold_modern  # noqa: E402
import verse_seg as VS  # noqa: E402

GT = HERE / "ground-truth"
WITNESSES = ("sabates_a", "madueke_b", "s_dismas", "odr_com")
REGISTER = {"sabates_a": "modern", "madueke_b": "modern", "s_dismas": "archaic", "odr_com": "archaic"}
_VTAG = re.compile(r"^(\d+):(\d+)([a-c])?$")

# slug -> book (mirror verse_seg_eval.LOCI)
LOCI = {
    "scripture-genesis-24": "genesis", "scripture-genesis-16-p081": "genesis",
    "scripture-genesis-16-p082": "genesis", "scripture-psalms-001": "psalms",
    "scripture-psalms-074-p137": "psalms", "scripture-psalms-074-p138": "psalms",
    "scripture-psalms-115-116": "psalms", "scripture-psalms-118": "psalms",
    "scripture-psalms-150-p265": "psalms", "scripture-psalms-150-p266": "psalms",
    "scripture-matthew-28-p102": "matthew", "scripture-2john": "2-john",
    "scripture-proverbs-16": "proverbs", "scripture-colossians-3": "colossians",
    "scripture-2esdras-07": "2-esdras",
}


def witness_jcut(name: str, book: str, chapter: int, janv: dict[int, str]) -> dict[int, str]:
    """A witness's chapter, re-cut to the janvier grid -> {verse -> text}. {} if the witness lacks the book."""
    cv = VS.chapter_verses(book, chapter, name)
    if not cv:
        return {}
    body = " ".join(cv[v] for v in sorted(cv))
    seg = VS.segment(body, janv)                       # janvier-cut (drop_apparatus off: witness text is clean)
    return {v: d["text"] for v, d in seg.items()}


def gold_jcut(slugs: list[str], chapter: int, janv: dict[int, str]) -> dict[int, str]:
    """Merge the gold body for `chapter` from ALL GT pages covering it (a chapter can span pages, e.g.
    genesis-16 p081+p082), then janvier-cut. Merging before the cut is what makes a multi-page chapter's gold
    complete rather than page-partial."""
    body = []
    for slug in slugs:
        gt = json.loads((GT / f"{slug}.json").read_text())
        for L in gt.get("body", []):
            if L.get("role") in ("catchword", "excluded", "signature"):
                continue
            m = _VTAG.match((L.get("verse") or "").strip())
            if m and int(m.group(1)) == chapter and isinstance(L.get("text"), str) and L["text"].strip():
                body.append(L["text"].strip())
    if not body:
        return {}
    seg = VS.segment(re.sub(r"-\s+", "", " ".join(body)), janv)
    return {v: d["text"] for v, d in seg.items()}


def pair_scores(a: dict[int, str], b: dict[int, str]) -> dict:
    """Per-shared-verse content + surface identity between two janvier-cut witness dicts."""
    shared = sorted(set(a) & set(b))
    if not shared:
        return {"n": 0, "content": None, "surface": None, "worst": None, "worst_v": None}
    content = [edit_ratio(fold_modern(a[v]), fold_modern(b[v])) for v in shared]
    surface = [edit_ratio(fold_archaic(a[v]), fold_archaic(b[v])) for v in shared]
    wi = min(range(len(shared)), key=lambda i: content[i])
    return {"n": len(shared),
            "content": round(mean(content), 4), "surface": round(mean(surface), 4),
            "worst": round(content[wi], 4), "worst_v": shared[wi]}


def chapter_matrix(book: str, chapter: int, gold_slugs: list[str] | None = None) -> dict:
    janv = VS.chapter_verses(book, chapter, VS.JANVIER)
    if not janv:
        return {"book": book, "chapter": chapter, "error": "janvier lacks chapter"}
    cut = {w: witness_jcut(w, book, chapter, janv) for w in WITNESSES}
    present = [w for w in WITNESSES if cut[w]]
    absent = [w for w in WITNESSES if not cut[w]]
    pairs = {}
    for w1, w2 in combinations(present, 2):
        pairs[f"{w1}|{w2}"] = {**pair_scores(cut[w1], cut[w2]),
                               "register": f"{REGISTER[w1][:3]}-{REGISTER[w2][:3]}"}
    gold_legs = {}
    if gold_slugs:
        gcut = gold_jcut(gold_slugs, chapter, janv)
        if gcut:
            for w in present:
                gold_legs[f"gold|{w}"] = {**pair_scores(gcut, cut[w]), "register": f"gold-{REGISTER[w][:3]}"}
            gold_legs["_gold_verses"] = len(gcut)
    return {"book": book, "chapter": chapter, "janvier_verses": len(janv),
            "present": present, "absent": absent, "pairs": pairs, "gold": gold_legs}


def build(gt_slugs: list[str], sample_chapters: list[tuple[str, int]]) -> dict:
    chapters = []
    # map (book, chapter) -> [GT slugs covering it]; a chapter may span multiple GT pages -> process ONCE,
    # merge the gold across pages (dedup fixes double-counting + partial-gold that per-slug iteration caused).
    chapter_slugs: dict[tuple[str, int], list[str]] = {}
    for slug in gt_slugs:
        book = LOCI.get(slug)
        if not book:
            continue
        gt = json.loads((GT / f"{slug}.json").read_text())
        for ch in sorted({int(m.group(1)) for L in gt.get("body", [])
                          if (m := _VTAG.match((L.get("verse") or "").strip()))}):
            chapter_slugs.setdefault((book, ch), []).append(slug)
    for (book, ch), slugs in sorted(chapter_slugs.items()):
        chapters.append({"slugs": slugs, **chapter_matrix(book, ch, gold_slugs=slugs)})
    # non-gold sample chapters (witness noise floor only) — skip any already covered by a GT chapter
    for book, ch in sample_chapters:
        if (book, ch) not in chapter_slugs:
            chapters.append({"slugs": None, **chapter_matrix(book, ch)})

    # aggregate per witness-pair across all chapters (content + surface)
    pair_keys = sorted({k for c in chapters for k in c.get("pairs", {})})
    matrix = {}
    for k in pair_keys:
        cvals = [c["pairs"][k]["content"] for c in chapters if k in c.get("pairs", {}) and c["pairs"][k]["content"] is not None]
        svals = [c["pairs"][k]["surface"] for c in chapters if k in c.get("pairs", {}) and c["pairs"][k]["surface"] is not None]
        reg = next((c["pairs"][k]["register"] for c in chapters if k in c.get("pairs", {})), "?")
        matrix[k] = {"register": reg, "content_mean": round(mean(cvals), 4) if cvals else None,
                     "surface_mean": round(mean(svals), 4) if svals else None,
                     "n_chapters": len(cvals),
                     "content_min": round(min(cvals), 4) if cvals else None}
    # gold legs aggregate
    gold_keys = sorted({k for c in chapters for k in c.get("gold", {}) if k.startswith("gold|")})
    gold_matrix = {}
    for k in gold_keys:
        cvals = [c["gold"][k]["content"] for c in chapters if k in c.get("gold", {}) and c["gold"][k]["content"] is not None]
        svals = [c["gold"][k]["surface"] for c in chapters if k in c.get("gold", {}) and c["gold"][k]["surface"] is not None]
        gold_matrix[k] = {"content_mean": round(mean(cvals), 4) if cvals else None,
                          "surface_mean": round(mean(svals), 4) if svals else None, "n_chapters": len(cvals)}
    # anomaly surfacing (§7 alarm-2 routing signal): a sharp PER-VERSE divergence — the worst shared verse of a
    # pair drops far below the pair's own noise floor — flags that LOCUS as likely-bad (versification defect,
    # \hfil artifact, or a genuine bad reading). Chapter MEANS average these away, so we key on `worst`, not
    # the mean. This is flag-IN (route to reOCR/escalation); it NEVER accepts a reading.
    WORST_GATE = 0.60
    anomalies = []
    for c in chapters:
        for k, p in c.get("pairs", {}).items():
            if p.get("worst") is not None and p["worst"] < WORST_GATE:
                anomalies.append({"book": c["book"], "chapter": c["chapter"], "pair": k,
                                  "worst_v": p.get("worst_v"), "worst": p["worst"],
                                  "chapter_mean": p.get("content"), "register": p["register"]})
    anomalies.sort(key=lambda a: a["worst"])
    return {"matrix": matrix, "gold_matrix": gold_matrix, "anomalies": anomalies,
            "n_chapters": len(chapters), "chapters": chapters}


# a small stratified non-gold sample across OT/NT for the witness noise floor (DIV-2 re-run target)
DEFAULT_SAMPLE = [("genesis", 1), ("genesis", 50), ("exodus", 20), ("psalms", 23), ("psalms", 50),
                  ("proverbs", 8), ("isaie", 53), ("matthew", 5), ("john", 3), ("romans", 8),
                  ("apocalypse", 21), ("tobias", 6)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", type=int, default=0, help="include N stratified non-gold chapters (noise floor)")
    ap.add_argument("--json", default=None)
    a = ap.parse_args()
    gt_slugs = sorted(p.stem for p in GT.glob("scripture-*.json"))
    sample = DEFAULT_SAMPLE[:a.sample] if a.sample else []
    res = build(gt_slugs, sample)

    print(f"\n{'='*90}\n### DIV-1 witness divergence matrix (janvier-cut, {res['n_chapters']} chapters)\n")
    print(f"{'witness pair':30} {'reg':9} {'content':>8} {'surface':>8} {'c-min':>7} {'n':>4}")
    print("-" * 70)
    for k, m in res["matrix"].items():
        print(f"{k:30} {m['register']:9} {str(m['content_mean']):>8} {str(m['surface_mean']):>8} "
              f"{str(m['content_min']):>7} {m['n_chapters']:>4}")
    print(f"\n### Gold vs each witness (janvier-cut, GT chapters)")
    for k, m in res["gold_matrix"].items():
        print(f"{k:30} {'':9} {str(m['content_mean']):>8} {str(m['surface_mean']):>8} {'':>7} {m['n_chapters']:>4}")
    print(f"\n### anomalies — sharp per-verse divergence (worst shared verse < 0.60; §7 alarm-2 routing, "
          f"flag-IN not accept): {len(res['anomalies'])}")
    for an in res["anomalies"][:25]:
        print(f"  {an['book']:10} ch{an['chapter']:<4} {an['pair']:30} worst_v={an['worst_v']} "
              f"worst={an['worst']} (chapter_mean={an['chapter_mean']})")
    if a.json:
        Path(a.json).write_text(json.dumps(res, ensure_ascii=False, indent=2))
        print(f"\nwrote {a.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""matter_scoring_run.py — E-phase driver: score EVERY matter GT against the curated sources that
do/should contain that testament's matter, using the E5b pooled scorer (matter_match_report).
Caches each source's OCR page-texts once. Emits matter-scoring-summary.json for the audit Artifact.
Per Sir's report rules: a row for every source that does/should contain the book; below-0.90 => reOCR flag."""
from __future__ import annotations
import json, glob, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import matter_match_report as M

# curated source OCR dirs per testament (drop S6-NT per directive; S2/S5/S7/S10-15 dropped)
SOURCES = {
    "ot1": [("S1", "archive-ot1-1609"), ("S3", "pdf-S03a"), ("S9", "archive-holiebible-ot1")],
    "ot2": [("S1", "archive-ot2-1610"), ("S3", "pdf-S03b"), ("S6", "jp2-S06"), ("S9", "jp2-S09ot2")],
    "nt":  [("S1", "archive-nt-1582"), ("S4", "jp2-S04"), ("S8", "jp2-S08"), ("S9", "pdf-S09nt")],
}
GT_DIR = HERE / "ground-truth"
_CACHE: dict[str, tuple[list[str], list[set]]] = {}  # ocr_dir -> (page_texts, page_tokensets), built ONCE


def source_cache(ocr_dir: str):
    if ocr_dir not in _CACHE:
        files = sorted(glob.glob(str(M.OCR_ROOT / ocr_dir / "*.json")))
        texts = [M._page_text(f) for f in files]
        toks = [set(M._fold_tokens(t)) for t in texts]  # pre-tokenise once (the expensive step)
        _CACHE[ocr_dir] = (texts, toks)
        print(f"    [cache {ocr_dir}: {len(files)} pages]", flush=True)
    return _CACHE[ocr_dir]


def locate(anchor: str, ocr_dir: str, span: int = 3) -> str:
    texts, toks = source_cache(ocr_dir)
    atoks = set(M._fold_tokens(anchor))
    if not atoks or not texts:
        return ""
    best_i, best = -1, 0.0
    for i, pt in enumerate(toks):
        if pt:
            sc = len(atoks & pt) / len(atoks)
            if sc > best:
                best, best_i = sc, i
    if best_i < 0 or best < 0.3:
        return ""
    lo, hi = max(0, best_i - span), min(len(texts), best_i + span + 1)
    return " ".join(texts[lo:hi])


def testament_of(slug: str) -> str:
    for t in ("ot1", "ot2", "nt"):
        if slug.startswith(f"matter-{t}-"):
            return t
    return "nt"


def main() -> int:
    rows = []
    for f in sorted(GT_DIR.glob("matter-*.json")):
        slug = f.stem
        gt = json.loads(f.read_text())
        ivs = M.intervals_of(gt)
        scoreable = [iv for iv in ivs if iv.get("kind") in M.SCORE_KINDS and (iv.get("text") or "").strip()]
        anchor = " ".join(iv["text"] for iv in ivs[:4])
        t = testament_of(slug)
        book = {"slug": slug, "locus": gt.get("locus"), "testament": t,
                "n_intervals": len(scoreable), "own_source": gt.get("ocr_dir"), "sources": []}
        for sid, ocr_dir in SOURCES[t]:
            txt = locate(anchor, ocr_dir)
            if not txt:
                book["sources"].append({"scan": sid, "ocr_dir": ocr_dir, "located": False})
                continue
            _, p, n = M.score_intervals(txt, ivs)
            pools = M.score_pools(txt, ivs)
            pp, pt = pools["para"]; ap, at = pools["app"]
            book["sources"].append({
                "scan": sid, "ocr_dir": ocr_dir, "located": True,
                "overall_pct": round(100 * p / n) if n else None,
                "para_pct": round(100 * pp / pt) if pt else None, "para": [pp, pt],
                "app_pct": round(100 * ap / at) if at else None, "app": [ap, at],
                "reocr_flag": (p / n < M.PASS) if n else True,
            })
        rows.append(book)
        loc = sum(1 for s in book["sources"] if s.get("located"))
        print(f"{slug:44} {t}  intervals={len(scoreable):4}  located {loc}/{len(SOURCES[t])} sources")
    out = HERE / "matter-scoring-summary.json"
    out.write_text(json.dumps({"pass_threshold": M.PASS, "window_words": M.WINDOW_W, "books": rows},
                              ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nWROTE {out.name}  ({len(rows)} matter books)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

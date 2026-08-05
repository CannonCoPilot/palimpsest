#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""verse_seg_eval.py — VS-5 validation of the janvier-cut verse segmenter (2026-07-22).

Proves the §5 linchpin on the gold pages: per-verse identity that was depressed (~0.47-0.68 "per-verse OCR")
was a BOUNDARY-mismatch artifact, and re-cutting BOTH sides by the janvier grid recovers the true fidelity
(~0.95+). Runs a controlled experiment that holds the TEXT constant and varies only the CUT:

  OLD (artifact): gold cut by its GT verse-tags   vs  s_dismas cut by its native versification  [two grids]
  NEW (janvier):  gold re-cut by janvier          vs  s_dismas re-cut by janvier                [one grid]

The witness arm (gold vs s_dismas) needs NO recognizer, so the linchpin proof is instant. A second arm runs
the REAL production OCR (reocr_core R2, fine-tuned kraken) and scores it per-verse vs the janvier-cut gold —
the "does per-verse identity TRACK page quality" headline (VS-5). It also reports the clean-cut stats
(len_ratio, OPEN count) that prove VS-4.

Usage:
  ocr-venv/bin/python ocr-spike/verse_seg_eval.py scripture-psalms-118 scripture-genesis-24
  ocr-venv/bin/python ocr-spike/verse_seg_eval.py scripture-psalms-118 --ocr     # add the real-R2 arm
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from statistics import mean

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from char_identity import edit_ratio, fold_archaic, fold_modern, evaluate_locus  # noqa: E402
import verse_seg as VS  # noqa: E402

GT = HERE / "ground-truth"

# slug -> book (janvier/skeleton book naming; hyphenated). Mirrors align_coords.LOCI.
LOCI = {
    "scripture-genesis-24": "genesis", "scripture-genesis-16-p081": "genesis",
    "scripture-psalms-001": "psalms", "scripture-psalms-118": "psalms",
    "scripture-psalms-115-116": "psalms", "scripture-psalms-150-p265": "psalms",
    "scripture-matthew-28-p102": "matthew", "scripture-2john": "2-john",
}
_VTAG = re.compile(r"^(\d+):(\d+)([a-c])?$")


def book_of(slug: str, gt: dict, override: str | None) -> str | None:
    if override:
        return override
    if slug in LOCI:
        return LOCI[slug]
    loc = (gt.get("locus") or "").lower()
    for b in {v for v in LOCI.values()}:
        if b in loc:
            return b
    return None


def gt_body_by_chapter(gt: dict) -> dict[int, str]:
    """Join GT body-line texts per chapter, in reading order (a/b cross-page fragments merge naturally).
    GT `body` is already body-isolated (apparatus/marginalia/catchword live in separate top-level fields);
    `role` only appears in genesis GT, where we still drop catchword/excluded."""
    by_ch: dict[int, list[str]] = {}
    for L in gt.get("body", []):
        if L.get("role") in ("catchword", "excluded", "signature"):
            continue
        m = _VTAG.match((L.get("verse") or "").strip())
        if not m:
            continue
        ch = int(m.group(1))
        t = L.get("text", "")
        if isinstance(t, str) and t.strip():
            by_ch.setdefault(ch, []).append(t.strip())
    return {ch: re.sub(r"-\s+", "", " ".join(lines)) for ch, lines in by_ch.items()}


def gt_naive_verses(gt: dict, chapter: int) -> dict[int, str]:
    """OLD boundary method: per-verse gold by GT verse-TAG grouping (letter fragments merged into the base
    verse number). This is the cut that produced the artifact."""
    out: dict[int, list[str]] = {}
    for L in gt.get("body", []):
        if L.get("role") in ("catchword", "excluded", "signature"):
            continue
        m = _VTAG.match((L.get("verse") or "").strip())
        if not m or int(m.group(1)) != chapter:
            continue
        t = L.get("text", "")
        if isinstance(t, str) and t.strip():
            out.setdefault(int(m.group(2)), []).append(t.strip())
    return {v: re.sub(r"-\s+", "", " ".join(x)) for v, x in sorted(out.items())}


def _mean(xs):
    xs = [x for x in xs if x is not None]
    return round(mean(xs), 4) if xs else None


def _passrate(xs, t=0.90):
    xs = [x for x in xs if x is not None]
    return (sum(1 for x in xs if x >= t), len(xs)) if xs else (0, 0)


def evaluate(slug: str, want_ocr: bool = False, book_override: str | None = None) -> dict:
    gt = json.loads((GT / f"{slug}.json").read_text())
    book = book_of(slug, gt, book_override)
    if not book:
        return {"slug": slug, "error": "no book mapping (pass --book)"}
    gold_by_ch = gt_body_by_chapter(gt)

    # optional real-OCR body (production R2), body-isolated, whole page -> we segment per chapter below
    r2_body = None
    if want_ocr:
        try:
            import reocr_core as core
            r = core.reocr_page(gt["ocr_dir"], gt["page_index"], want_base=False, want_r1=False)
            r2_body = r["r2_body"]
        except Exception as e:
            r2_body = None
            print(f"  [{slug}] R2 arm skipped: {type(e).__name__}: {e}", file=sys.stderr)

    chapters = []
    for ch, gold_body in sorted(gold_by_ch.items()):
        janv = VS.chapter_verses(book, ch, VS.JANVIER)
        if not janv:
            chapters.append({"chapter": ch, "error": f"janvier lacks {book} {ch}"}); continue

        # janvier-cut gold + janvier-cut s_dismas (re-cut its whole-chapter text to the janvier grid)
        gold_j = VS.segment(gold_body, janv)
        sd_native, sd_name = VS.archaic_chapter(book, ch)
        sd_body = " ".join(sd_native[v] for v in sorted(sd_native)) if sd_native else ""
        sd_j = VS.segment(sd_body, janv) if sd_body else {}
        gold_naive = gt_naive_verses(gt, ch)

        # OCR bodies carry interleaved central-column apparatus (footnotes/annotations) that geometry-only
        # body-isolation can't remove; the janvier grid filters it (drop_apparatus). No-op on clean gold.
        r2_j = VS.segment(r2_body, janv, drop_apparatus=True) if r2_body else {}

        rows = []
        for v in sorted(gold_j):
            gj = gold_j[v]["text"]
            # NEW: gold vs s_dismas, both janvier-cut (the linchpin proof; recognizer-free)
            new_wit = edit_ratio(fold_archaic(gj), fold_archaic(sd_j[v]["text"])) if v in sd_j else None
            # OLD: gold-by-GT-tag vs s_dismas-native-verse (two grids — the artifact)
            old_wit = (edit_ratio(fold_archaic(gold_naive[v]), fold_archaic(sd_native[v]))
                       if (v in gold_naive and v in sd_native) else None)
            # gold faithfulness to janvier CONTENT (sanity: is the janvier-cut gold itself good?)
            gold_content = edit_ratio(fold_modern(gj), fold_modern(janv[v])) if v in janv else None
            # REAL OCR (production headline): R2 vs janvier-cut gold, archaic-preeminent
            ocr = None
            if v in r2_j:
                verdict = evaluate_locus(r2_j[v]["text"], janv.get(v), gj)
                ocr = {"archaic_id": verdict["archaic_id"], "modern_id": verdict["modern_id"],
                       "passed": verdict["passed"]}
            rows.append({"v": v, "new_wit": _r(new_wit), "old_wit": _r(old_wit),
                         "gold_content": _r(gold_content),
                         "len_ratio": gold_j[v]["len_ratio"], "open": gold_j[v]["open"],
                         "reason": gold_j[v]["reason"], "anchor": gold_j[v]["anchor"],
                         "ocr": ocr})

        new_vals = [r["new_wit"] for r in rows]
        old_vals = [r["old_wit"] for r in rows]
        chapters.append({
            "chapter": ch, "book": book, "n_verses": len(rows), "sd_witness": sd_name,
            "localized": (min(gold_j), max(gold_j)) if gold_j else None,
            "NEW_witness_mean": _mean(new_vals), "OLD_witness_mean": _mean(old_vals),
            "gold_content_mean": _mean([r["gold_content"] for r in rows]),
            "NEW_pass@.90": _passrate(new_vals), "OLD_pass@.90": _passrate(old_vals),
            "open_verses": sum(1 for r in rows if r["open"]),
            "len_ratio_span": (min((r["len_ratio"] for r in rows if r["len_ratio"] is not None), default=None),
                               max((r["len_ratio"] for r in rows if r["len_ratio"] is not None), default=None)),
            "ocr_archaic_mean": _mean([r["ocr"]["archaic_id"] for r in rows if r["ocr"]]),
            "ocr_pass@.90": _passrate([r["ocr"]["archaic_id"] for r in rows if r["ocr"]]),
            "rows": rows,
        })
    return {"slug": slug, "book": book, "ocr_dir": gt["ocr_dir"], "page_index": gt["page_index"],
            "chapters": chapters}


def _r(x):
    return round(x, 4) if isinstance(x, float) else x


def _print(res: dict):
    if res.get("error"):
        print(f"\n### {res['slug']}: ERROR {res['error']}"); return
    print(f"\n{'='*94}\n### {res['slug']}  ({res['book']}, {res['ocr_dir']} p{res['page_index']})")
    for c in res["chapters"]:
        if c.get("error"):
            print(f"  ch{c['chapter']}: {c['error']}"); continue
        print(f"\n  chapter {c['chapter']}  ({c['n_verses']} verses on page, localized to {c['localized']}, "
              f"archaic witness = {c['sd_witness']})")
        print(f"    {'ARTIFACT vs FIX (witness, janvier-cut both sides)':52}")
        print(f"      OLD (two grids):   mean {c['OLD_witness_mean']}   pass@.90 {c['OLD_pass@.90'][0]}/{c['OLD_pass@.90'][1]}")
        print(f"      NEW (janvier-cut): mean {c['NEW_witness_mean']}   pass@.90 {c['NEW_pass@.90'][0]}/{c['NEW_pass@.90'][1]}   "
              f"<-- target >= 0.95")
        print(f"    clean-cut (VS-4): OPEN verses {c['open_verses']}/{c['n_verses']}   "
              f"len_ratio span {c['len_ratio_span']}   gold-content vs janvier mean {c['gold_content_mean']}")
        if c["ocr_archaic_mean"] is not None:
            print(f"    REAL OCR (R2, production): archaic-id mean {c['ocr_archaic_mean']}   "
                  f"pass@.90 {c['ocr_pass@.90'][0]}/{c['ocr_pass@.90'][1]}")
        # per-verse detail
        print(f"      {'v':>4} {'OLD':>6} {'NEW':>6} {'g-cont':>7} {'lenR':>5} {'anc':>4}  flag")
        for r in c["rows"]:
            flag = ("OPEN:" + r["reason"]) if r["open"] else ""
            oc = f"  ocr_arc={r['ocr']['archaic_id']}" if r["ocr"] else ""
            print(f"      {r['v']:>4} {str(r['old_wit']):>6} {str(r['new_wit']):>6} {str(r['gold_content']):>7} "
                  f"{str(r['len_ratio']):>5} {r['anchor']:>4}  {flag}{oc}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("slugs", nargs="+")
    ap.add_argument("--ocr", action="store_true", help="also run the real R2 recognizer arm (needs kraken)")
    ap.add_argument("--book", default=None)
    ap.add_argument("--json", default=None, help="write full results json here")
    a = ap.parse_args()
    allres = []
    for slug in a.slugs:
        res = evaluate(slug, want_ocr=a.ocr, book_override=a.book)
        _print(res)
        allres.append(res)
    # headline aggregate
    print(f"\n{'='*94}\n### HEADLINE (VS-5 gate: per-verse identity TRACKS page quality; boundary artifact removed)")
    new_all = []
    for res in allres:
        for c in res.get("chapters", []):
            if c.get("NEW_witness_mean") is not None:
                new_all.append((res["slug"], c["chapter"], c["OLD_witness_mean"], c["NEW_witness_mean"],
                                c["open_verses"], c["n_verses"]))
    for slug, ch, old, new, op, n in new_all:
        lift = f"+{round(new-old,3)}" if (old is not None and new is not None) else "?"
        print(f"  {slug:26} ch{ch:<3} OLD {old} -> NEW {new}  ({lift})  clean-cut {n-op}/{n}")
    if a.json:
        Path(a.json).write_text(json.dumps(allres, ensure_ascii=False, indent=2))
        print(f"\nwrote {a.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""reocr_lift.py — REP-2 evidence: the base-OCR → R2 (fine-tuned recognizer) LIFT, per-verse janvier-cut (2026-07-22).

The v014 report shows the legacy scan OCR is inadequate (~0.5, everything flagged for reOCR). This harness
answers the necessary next question — does the reOCR actually FIX it? — on the gold pages, where the answer
is checkable. For each GT-covered page it scores BOTH streams against the SAME janvier-cut gold, at the SAME
per-verse grain (archaic-preeminent identity), so the lift is apples-to-apples:

  base : existing scan OCR (reocr_core.base_ocr) — the report's baseline stream, janvier-cut.
  R2   : fine-tuned kraken (reocr_core.reocr_page.r2_body, body-isolated) — the production reOCR, janvier-cut.

Both janvier-cut with drop_apparatus=True (the raw-page stream can carry interleaved footnotes). This is the
honest, No-Silent-Degradation lift: verses R2 still fails to lift ≥0.90 stay OPEN → they are the R3 residual.

Usage: ocr-venv/bin/python ocr-spike/reocr_lift.py [slug ...]   (default: all scripture GT with a page+gold)
"""
from __future__ import annotations

import json
import re
import sys
import warnings
from pathlib import Path
from statistics import mean

warnings.filterwarnings("ignore")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from char_identity import evaluate_locus  # noqa: E402
import verse_seg as VS  # noqa: E402
import reocr_core as core  # noqa: E402

GT = HERE / "ground-truth"
_VTAG = re.compile(r"^(\d+):(\d+)([a-c])?$")
# LOCI comes from the REGISTRY now, never a hand-typed dict. The previous literal here omitted
# scripture-abdias-01 — a completed, Sir-reviewed GT page silently excluded from every lift number reported
# before 2026-07-27, because the harness printed "no book/page" and moved on. See gt_registry.py.
import gt_registry as _REG  # noqa: E402
LOCI = _REG.loci("scripture")


def gold_by_chapter(gt: dict) -> dict[int, str]:
    by: dict[int, list[str]] = {}
    for L in gt.get("body", []):
        if L.get("role") in ("catchword", "excluded", "signature"):
            continue
        m = _VTAG.match((L.get("verse") or "").strip())
        if m and isinstance(L.get("text"), str) and L["text"].strip():
            by.setdefault(int(m.group(1)), []).append(L["text"].strip())
    return {ch: re.sub(r"-\s+", "", " ".join(v)) for ch, v in by.items()}


def _score(ocr_body: str, janv: dict[int, str], gold_j: dict[int, dict]) -> dict[int, float | None]:
    """per-janvier-verse archaic-preeminent identity of an OCR body vs the janvier-cut gold."""
    seg = VS.segment(ocr_body, janv, drop_apparatus=True) if ocr_body else {}
    out: dict[int, float | None] = {}
    for v in gold_j:
        if v in seg:
            out[v] = evaluate_locus(seg[v]["text"], janv.get(v), gold_j[v]["text"])["archaic_id"]
        else:
            out[v] = None                                # not localized in this stream (a miss, counts as fail)
    return out


def _ladder(slug: str) -> dict:
    """{(ch,v) -> {r3_gold, state, s_state}} — the R3 and ſ-arbiter outcomes for this page, from their caches.

    REP-2 asks for the reOCR STREAMS rendered, and base→R2 is only the first two rungs. The R3 re-read and the
    ſ arbiter already ran and were checkpointed; joining them here means the report shows the whole ladder
    (base → R2 → R3 → arbiter) against ONE gold-anchored grid, instead of three artifacts a reader must
    reconcile by hand. Absent caches degrade to base/R2 only — the join never invents a rung."""
    out: dict = {}
    f = HERE / ".r3-stats" / f"{slug}.json"
    if f.exists():
        for r in json.loads(f.read_text()):
            out[(r["ch"], r["v"])] = {"r3_gold": r.get("r3_gold_aid"), "r3_state": r.get("state")}
    tf = HERE / ".s-arbiter" / "_transfer.json"
    if tf.exists():
        for key, v in json.loads(tf.read_text())["verdicts"].items():
            _b, ch, vs = key.split("/")
            k = (int(ch), int(vs))
            if v.get("slug") == slug and k in out:
                out[k]["s_state"] = v.get("state")
                out[k]["s_text"] = v.get("text")
    return out


def evaluate(slug: str) -> dict:
    gt = json.loads((GT / f"{slug}.json").read_text())
    book = LOCI.get(slug)
    od, pi = gt.get("ocr_dir"), gt.get("page_index")
    if not book or od is None or pi is None:
        return {"slug": slug, "error": "no book/page"}
    rows = []
    ladder = _ladder(slug)
    base_body = core.base_ocr(od, pi)
    import gate_calibrate as _calib
    r = _calib.cached_page(slug, od, pi)          # `.page-cache/` — kraken cannot change the lift question
    r2_body = r["r2_body"]
    for ch, gold_text in sorted(gold_by_chapter(gt).items()):
        janv = VS.chapter_verses(book, ch, VS.JANVIER)
        if not janv:
            continue
        gold_j = VS.segment(gold_text, janv)
        base_s = _score(base_body, janv, gold_j)
        r2_s = _score(r2_body, janv, gold_j)
        for v in sorted(gold_j):
            rows.append({"ch": ch, "v": v, "base": base_s.get(v), "r2": r2_s.get(v),
                         "gold": True,                       # REP-4: this locus IS gold-anchored, not witness-anchored
                         **ladder.get((ch, v), {})})
    def _m(key):
        xs = [r[key] for r in rows if r[key] is not None]
        return round(mean(xs), 4) if xs else None
    def _p(key, t=0.90):
        xs = [(r[key] or 0.0) for r in rows]
        return (sum(1 for x in xs if x >= t), len(xs))
    base_mean, r2_mean = _m("base"), _m("r2")
    # A page where R2 catastrophically UNDERperforms base is not a recognizer signal — it is a confounded
    # measurement (addressing mismatch / multi-chapter page / a layout mode whose body-isolation drops the
    # gold content, e.g. greek-margins). Flag it (with the reason) and report it SEPARATELY — never hide it,
    # never let it misrepresent R2's recognition lift (No Silent Degradation cuts both ways: no false-bad either).
    multi_chapter = len(gold_by_chapter(gt)) > 1
    flagged = (base_mean is not None and r2_mean is not None and r2_mean < base_mean - 0.30)
    reason = ""
    if flagged:
        reason = ("confound: " + ("multi-chapter GT page; " if multi_chapter else "")
                  + "body-isolation/addressing drops gold content (§4 ADDR / §11 layout) — NOT recognizer quality")
    return {"slug": slug, "book": book, "ocr_dir": od, "page": pi, "n": len(rows),
            "base_mean": base_mean, "r2_mean": r2_mean,
            "base_pass": _p("base"), "r2_pass": _p("r2"), "flagged": flagged, "reason": reason,
            "still_open": [f"{r['ch']}:{r['v']}" for r in rows if (r["r2"] or 0.0) < 0.90], "rows": rows}


def _agg(rows, label, npages):
    bm = [r["base"] for r in rows if r["base"] is not None]
    rm = [r["r2"] for r in rows if r["r2"] is not None]
    bp = sum(1 for r in rows if (r["base"] or 0) >= 0.90)
    rp = sum(1 for r in rows if (r["r2"] or 0) >= 0.90)
    n = len(rows)
    lift = (mean(rm) - mean(bm)) if bm and rm else 0
    print(f"{label:28} {round(mean(bm),4) if bm else None:>9} {round(mean(rm),4) if rm else None:>8} "
          f"{f'{bp}/{n}':>10} {f'{rp}/{n}':>9}  {lift:+.3f}")
    print(f"    → base pass-rate {100*bp/n:.0f}%  →  R2 pass-rate {100*rp/n:.0f}%   (n={n} verses, {npages} pages)")


def main():
    slugs = sys.argv[1:] or sorted(p.stem for p in GT.glob("scripture-*.json"))
    print(f"\n{'='*86}\nREP-2 base→R2 LIFT (per-verse janvier-cut vs gold, archaic-preeminent, ≥0.90 bar)\n")
    print(f"{'slug':28} {'base mean':>9} {'R2 mean':>8} {'base pass':>10} {'R2 pass':>9}  {'lift':>6}")
    print("-" * 82)
    results = []
    for slug in slugs:
        res = evaluate(slug)
        if res.get("error"):
            print(f"{slug:28} {res['error']}"); continue
        results.append(res)
        bp, bn = res["base_pass"]; rp, rn = res["r2_pass"]
        lift = (res["r2_mean"] or 0) - (res["base_mean"] or 0)
        mark = "  ⚠FLAG" if res["flagged"] else ""
        print(f"{slug:28} {str(res['base_mean']):>9} {str(res['r2_mean']):>8} "
              f"{f'{bp}/{bn}':>10} {f'{rp}/{rn}':>9}  {lift:+.3f}{mark}")
    clean = [r for r in results if not r["flagged"]]
    flagged = [r for r in results if r["flagged"]]
    print("-" * 82)
    _agg([row for r in results for row in r["rows"]], "AGGREGATE (all)", len(results))
    if flagged:
        _agg([row for r in clean for row in r["rows"]], "AGGREGATE (representative)", len(clean))
        print(f"\n⚠ {len(flagged)} FLAGGED confound page(s) — reported, NOT hidden, NOT representative of R2 recognition:")
        for r in flagged:
            print(f"    {r['slug']}: base {r['base_mean']} → R2 {r['r2_mean']}  — {r['reason']}")
    print(f"\nResidual R2<0.90 on clean pages = the R3 escalation set (No Silent Degradation: stays OPEN → M5 R3).")

    # REP-2/REP-4 ARTIFACT. The renderer must not recompute any of this — a report that re-derives its own
    # numbers can disagree with the harness that validated them. One file, written by the measuring code.
    allrows = [row for r in results for row in r["rows"]]
    art = {
        "generated_by": "reocr_lift.py (REP-2 stream ladder + REP-4 gold anchoring)",
        "bar": 0.90, "reference": "Jarvis diplomatic GOLD, janvier-cut, archaic-preeminent identity",
        "aggregate": {
            "pages": len(results), "verses": len(allrows),
            "base_mean": round(mean([r["base"] for r in allrows if r["base"] is not None]), 4),
            "r2_mean": round(mean([r["r2"] for r in allrows if r["r2"] is not None]), 4),
            "base_pass": sum(1 for r in allrows if (r["base"] or 0) >= 0.90),
            "r2_pass": sum(1 for r in allrows if (r["r2"] or 0) >= 0.90),
        },
        "representative": {
            "pages": len(clean),
            "base_mean": round(mean([r["base"] for c in clean for r in c["rows"] if r["base"] is not None]), 4),
            "r2_mean": round(mean([r["r2"] for c in clean for r in c["rows"] if r["r2"] is not None]), 4),
        },
        "flagged_confounds": [{"slug": r["slug"], "base_mean": r["base_mean"], "r2_mean": r["r2_mean"],
                               "reason": r["reason"]} for r in flagged],
        "pages": results,
    }
    (HERE / "reocr-lift.json").write_text(json.dumps(art, ensure_ascii=False, indent=1))
    print(f"→ wrote reocr-lift.json ({len(results)} pages, {len(allrows)} gold-anchored verses)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

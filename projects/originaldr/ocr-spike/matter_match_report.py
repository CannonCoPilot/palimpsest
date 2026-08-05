#!/usr/bin/env python3
"""matter_match_report.py — Sir's report rule E5b for front/back-matter "books".

Matter has no verses, so we score on canonical INTERVALS (paragraphs / table-rows / headings) — the
matter analog of verses. Each source's OCR of a matter section is aligned to the GT's intervals[] with
the SAME engine used for verses (align_coords.realign), then scored per interval (fold_archaic+edit_ratio).
A source is reOCR-flagged for a matter book if < PASS of intervals match the gold at ≥ PASS (E4/E5a analog).

`intervals_of(gt)` returns the GT's own intervals[] (emitted by transcription agents) or derives them from
body[] (tables→rows, display→title blocks, prose→paragraph runs [coarse; flagged for raster refinement]).

Run: ocr-venv/bin/python ocr-spike/matter_match_report.py <matter-slug> [source ...]
     ocr-venv/bin/python ocr-spike/matter_match_report.py --selftest
"""
from __future__ import annotations
import json, re, sys, glob, os
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import align_coords as AC
from char_identity import fold_archaic, edit_ratio

PASS = 0.90
GT_DIR = HERE / "ground-truth"
OCR_ROOT = HERE.parent / "sources/our-ocr-diplomatic"
SCORE_KINDS = {"paragraph", "table_row", "list_item", "heading", "subtitle", "title_block", "colophon_line"}
SKIP_ROLES = {"catchword", "excluded", "signature"}
# E5b pools (Sir): running PROSE scored at ~20-word WINDOW grain (paragraph-grain too coarse for the 0.90 bar);
# short APPARATUS items (headings/subtitles/table & list rows) scored at interval grain (already <~1 window).
PARA_KINDS = {"paragraph", "title_block", "colophon_line"}
APP_KINDS = {"heading", "subtitle", "table_row", "list_item"}
WINDOW_W = 20


def intervals_of(gt: dict) -> list[dict]:
    """GT-provided intervals[], else derive from body[]. Prose runs become coarse paragraphs (flagged)."""
    if gt.get("intervals"):
        return gt["intervals"]
    body = sorted(gt.get("body", []), key=lambda L: int(L.get("line_index", 0) or 0))
    out: list[dict] = []
    buf: dict | None = None
    idx = 0

    def flush():
        nonlocal buf, idx
        if buf and buf["text"].strip():
            buf["idx"] = idx
            out.append(buf)
            idx += 1
        buf = None

    for L in body:
        role = (L.get("role") or "prose")
        txt = L.get("text", "") or ""
        li = L.get("line_index")
        if role in SKIP_ROLES:
            flush(); continue
        if role in ("table_row", "list_item"):
            flush(); out.append({"idx": idx, "kind": role, "text": txt, "lines": [li]}); idx += 1
        elif role in ("title_display", "subtitle", "heading"):
            kind = "title_block" if role == "title_display" else role
            if buf and buf["kind"] == kind:
                buf["text"] += " " + txt; buf["lines"].append(li)
            else:
                flush(); buf = {"kind": kind, "text": txt, "lines": [li]}
        else:  # prose / latin -> paragraph run (coarse; refine from raster)
            if buf and buf["kind"] == "paragraph":
                buf["text"] += " " + txt; buf["lines"].append(li)
            else:
                flush(); buf = {"kind": "paragraph", "text": txt, "lines": [li], "_coarse": True}
    flush()
    return out


def _page_text(path: str) -> str:
    try:
        d = json.load(open(path, encoding="utf-8", errors="ignore"))
    except Exception:
        return ""
    if isinstance(d, dict):
        if isinstance(d.get("text"), str):
            return d["text"]
        if isinstance(d.get("lines"), list):
            return " ".join(l.get("text", "") for l in d["lines"] if isinstance(l, dict))
    return ""


def _fold_tokens(s: str) -> list[str]:
    return [t for t in (re.sub(r"[^a-z0-9]", "", fold_archaic(w).lower()) for w in re.findall(r"\S+", s or "")) if t]


def find_section_page(ocr_dir: str, anchor: str, span: int = 2) -> str:
    """best-matching page text (+span neighbours) in ocr_dir for the section, by folded-token overlap."""
    files = sorted(glob.glob(str(OCR_ROOT / ocr_dir / "*.json")))
    if not files:
        return ""
    atoks = set(_fold_tokens(anchor))
    if not atoks:
        return ""
    best_i, best_score = -1, 0.0
    texts = [_page_text(f) for f in files]
    for i, t in enumerate(texts):
        pt = set(_fold_tokens(t))
        if not pt:
            continue
        sc = len(atoks & pt) / len(atoks)
        if sc > best_score:
            best_score, best_i = sc, i
    if best_i < 0 or best_score < 0.3:
        return ""
    lo, hi = max(0, best_i - span), min(len(texts), best_i + span + 1)
    return " ".join(texts[lo:hi])


def score_intervals(ocr_text: str, intervals: list[dict]) -> tuple[dict, int, int]:
    ref = {str(iv["idx"]): iv["text"] for iv in intervals if iv.get("kind") in SCORE_KINDS and (iv.get("text") or "").strip()}
    if not ref:
        return {}, 0, 0
    aligned = AC.realign(ocr_text, ref)
    res = {}
    for k, gtext in ref.items():
        res[k] = round(edit_ratio(fold_archaic(aligned.get(k, "")), fold_archaic(gtext)), 4)
    npass = sum(1 for r in res.values() if r >= PASS)
    return res, npass, len(res)


def word_windows(text: str, W: int = WINDOW_W) -> list[str]:
    """Non-overlapping ~W-word windows of GT text (the scoring unit for long prose)."""
    toks = re.findall(r"\S+", text or "")
    return [" ".join(toks[i:i + W]) for i in range(0, len(toks), W)] if toks else []


def _ocr_windows(text: str, W: int = WINDOW_W) -> list[str]:
    """Overlapping ~W-word windows of OCR text (stride W//2) so a GT window can align at any offset."""
    toks = re.findall(r"\S+", text or "")
    if not toks:
        return [""]
    step = max(1, W // 2)
    return [" ".join(toks[i:i + W]) for i in range(0, len(toks), step)] or [""]


def score_para_windows(aligned_ocr: str, gt_text: str, W: int = WINDOW_W) -> tuple[int, int]:
    """% of GT ~W-word windows whose BEST-matching OCR window scores >=PASS. Returns (npass, ntotal).
    Forgiving where whole-paragraph edit_ratio is not: a localized OCR error fails one window, not the
    entire paragraph (the E5b granularity fix — see SPRINT-STATUS 'E5b GRANULARITY FINDING')."""
    gt_wins = word_windows(gt_text, W)
    if not gt_wins:
        return 0, 0
    ocr_wins = [fold_archaic(ow) for ow in _ocr_windows(aligned_ocr, W)]
    npass = 0
    for gw in gt_wins:
        gf = fold_archaic(gw)
        best = max((edit_ratio(ow, gf) for ow in ocr_wins), default=0.0)
        if best >= PASS:
            npass += 1
    return npass, len(gt_wins)


def score_pools(ocr_text: str, intervals: list[dict]) -> dict:
    """E5b: score the section split into two pools.
      PARA (running prose) -> window grain: % of ~20-word windows matching >=PASS.
      APP  (headings/subtitles/table & list rows) -> interval grain: % of items matching >=PASS.
    Returns {'para': (pass, total), 'app': (pass, total), 'ratios': {...}}."""
    ref = {str(iv["idx"]): iv["text"] for iv in intervals
           if iv.get("kind") in SCORE_KINDS and (iv.get("text") or "").strip()}
    aligned = AC.realign(ocr_text, ref) if ref else {}
    p_pass = p_tot = a_pass = a_tot = 0
    ratios: dict[str, float] = {}
    for iv in intervals:
        k = str(iv["idx"]); kind = iv.get("kind"); txt = (iv.get("text") or "").strip()
        if not txt:
            continue
        if kind in PARA_KINDS:
            npw, ntw = score_para_windows(aligned.get(k, ""), txt)
            p_pass += npw; p_tot += ntw
            ratios[k] = round(npw / ntw, 4) if ntw else 0.0
        elif kind in APP_KINDS:
            r = round(edit_ratio(fold_archaic(aligned.get(k, "")), fold_archaic(txt)), 4)
            a_tot += 1; a_pass += (1 if r >= PASS else 0); ratios[k] = r
    return {"para": (p_pass, p_tot), "app": (a_pass, a_tot), "ratios": ratios}


def selftest():
    """validate the scoring mechanism: identical->1.0 all pass; noised->degrades; garbled->fails."""
    ivs = [{"idx": 0, "kind": "paragraph", "text": "Blessed is the man that hath not gone in the counſel of the impious."},
           {"idx": 1, "kind": "paragraph", "text": "But his wil is in the law of our Lord, and therein he wil meditate."},
           {"idx": 2, "kind": "table_row", "text": "S. Iohn Euangeliſt. Eccli. 15. v. 1. to v. 7."}]
    clean = " ".join(iv["text"] for iv in ivs)
    noised = clean.replace("Blessed", "Bleſſed").replace("counſel", "counsel").replace("Euangeliſt", "Euangelift")
    garbled = "xq zz totally different text with no overlap whatsoever lorem ipsum foo bar baz"
    for label, txt in (("identical", clean), ("light-noise", noised), ("garbled", garbled)):
        res, p, n = score_intervals(txt, ivs)
        print(f"  {label:12} {p}/{n} intervals pass@{PASS}  ratios={list(res.values())}")


def main(argv):
    if argv and argv[0] == "--selftest":
        print("matter-scorer self-test (validates interval alignment + scoring):")
        selftest()
        return 0
    if not argv:
        print(__doc__); return 1
    slug = argv[0]
    sources = argv[1:]
    gt = json.loads((GT_DIR / f"{slug}.json").read_text())
    ivs = intervals_of(gt)
    coarse = sum(1 for iv in ivs if iv.get("_coarse"))
    print(f"{slug}: {len(ivs)} intervals ({sum(1 for iv in ivs if iv['kind'] in SCORE_KINDS)} scoreable"
          f"{f'; {coarse} COARSE prose runs — refine from raster' if coarse else ''})")
    anchor = " ".join(iv["text"] for iv in ivs[:3])
    for src_ocr_dir in sources:
        ocr_text = find_section_page(src_ocr_dir, anchor)
        if not ocr_text:
            print(f"  {src_ocr_dir:20} section not located in source OCR"); continue
        res, p, n = score_intervals(ocr_text, ivs)
        frac = p / n if n else 0.0
        flag = "✗" if frac < PASS else "PASS"
        pools = score_pools(ocr_text, ivs)
        pp, pt = pools["para"]; ap, at = pools["app"]

        def _fmt(pas, tot, unit):
            if not tot:
                return f"   {unit:9} —"
            fr = pas / tot
            return f"   {unit:9} {'✗' if fr < PASS else 'PASS'} {int(fr*100):3d}%  ({pas}/{tot} ≥{PASS})"
        print(f"  {src_ocr_dir:20} {flag} {int(frac*100)}% overall  ({p}/{n} intervals)")
        print(_fmt(pp, pt, "PARA/win"))   # E5a-analog: prose at ~20-word window grain
        print(_fmt(ap, at, "APPARATUS"))  # E5b: headings/subtitles/rows combined, interval grain
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

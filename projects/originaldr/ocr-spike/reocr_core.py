#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""reocr_core.py — the GOLD-FREE production reOCR pipeline for the Douay-Rheims corpus.

Principle #1: every stage here works on ANY DR page addressed by (ocr_dir, page_index). There is no gold
transcript parameter, no `ground-truth/` access, no metric — this module could run on all 3,028 core pages
that have no gold. Quality is SELF-assessed via recognizer confidence (gold-free), which drives the R3 gate.
All gold scoring lives in `reocr_eval.py`.

Ladder per page: base (existing scan OCR) · R1 (base recognizer + preprocess) · R2 (fine-tuned recognizer)
· body-region typing (layout.py, drops header/marginalia/catchword) · confidence gate → escalate to R3.

ſ surface-safe throughout: NFC, no dictionary/LM. Recognizer = reichenau_lat base / reichenau_dr fine-tuned.
"""
from __future__ import annotations
import re, json, glob, statistics, warnings
from pathlib import Path
warnings.filterwarnings("ignore")

HERE = Path(__file__).resolve().parent
PROJ = HERE.parent
BASE_OCR_ROOT = PROJ / "sources" / "our-ocr-diplomatic"
BASE_MODEL = HERE / "models" / "reichenau_lat.mlmodel"     # ſ-faithful base recognizer
R2_MODEL = HERE / "models" / "reichenau_dr.mlmodel"        # fine-tuned DR recognizer
MAXW = 2200

import jp2_page  # gold-free scan addressing (ocr_dir, page_index) -> jp2 page
import layout


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


# ---------- base (existing scan OCR) — gold-free, page-indexed ----------
def base_ocr(ocr_dir: str, page_index: int) -> str:
    """The existing scan-OCR text for a page, addressed directly by page index (no gold anchor).
    Source jsons are named `..._{page_index:04d}.json`, matching the jp2 `_NNNN` labels."""
    hits = sorted(glob.glob(str(BASE_OCR_ROOT / ocr_dir / f"*_{page_index:04d}.json")))
    if not hits:
        return ""
    d = json.load(open(hits[0], errors="ignore"))
    t = d.get("text") if isinstance(d.get("text"), str) else \
        " ".join(l.get("text", "") for l in d.get("lines", []) if isinstance(l, dict))
    return _norm(t or "")


# ---------- scan + preprocess + segment ----------
def load_scan(ocr_dir: str, page_index: int):
    return jp2_page.load(ocr_dir, page_index).convert("L")


def preprocess(im):
    from PIL import ImageOps, Image
    im = ImageOps.autocontrast(im)
    if im.width < 1500:                    # low-res source (e.g. 800px S8): upscale for the recognizer
        im = im.resize((1600, int(im.height * 1600 / im.width)), Image.LANCZOS)
    elif im.width > MAXW:
        im = im.resize((MAXW, int(im.height * MAXW / im.width)), Image.LANCZOS)
    return im


_SEG_CACHE: dict = {}
_MODELS: dict = {}


def _model(path):
    from kraken.lib import models
    p = str(path)
    if p not in _MODELS:
        _MODELS[p] = models.load_any(p)
    return _MODELS[p]


def segment(pim, cache_key=None):
    from kraken import blla
    if cache_key is not None and cache_key in _SEG_CACHE:
        return _SEG_CACHE[cache_key]
    seg = blla.segment(pim)
    if cache_key is not None:
        _SEG_CACHE[cache_key] = seg
    return seg


def recognize_lines(model_path, pim, seg):
    """Recognize each segmentation line → list of dicts {text, conf} in reading order (gold-free).
    conf = mean per-char confidence from the recognizer (kraken ocr_record.confidences)."""
    from kraken import rpred
    out = []
    for rec in rpred.rpred(_model(model_path), pim, seg):
        confs = getattr(rec, "confidences", None) or []
        out.append({"text": str(rec), "conf": float(statistics.mean(confs)) if confs else 0.0,
                    "nchars": len(confs)})
    return out


# ---------- confidence gate (gold-free R3 escalation signal) ----------
def page_confidence(body_lines):
    """Length-weighted mean confidence over BODY lines — the page's self-assessed quality (no gold)."""
    num = sum(l["conf"] * max(1, l["nchars"]) for l in body_lines)
    den = sum(max(1, l["nchars"]) for l in body_lines)
    return round(num / den, 4) if den else 0.0


# ---------- the ladder for one page ----------
def reocr_page(ocr_dir: str, page_index: int, *, r2_model=R2_MODEL, base_model=BASE_MODEL,
               conf_gate=0.92, want_base=True, want_r1=True, locus=None, taux=None):
    """Run the gold-free ladder on one page. Returns a dict with the R2 body transcript, per-line records
    (text/conf/role), self-assessed page confidence, and an escalate flag — NO gold anywhere.

    want_base/want_r1: also compute the base and R1 rungs (used by the eval harness / for comparison).

    locus=(book, chapter): OPT-IN §7 ALARM 2 (cross-source divergence). Recognizer confidence is self-report-
    BLIND to systematic misreads (gate_calibrate.py: conf recall=1 costs 88% escalation, catches the confident-
    wrong tail 0/40). When the page's (book, chapter) is supplied, the ladder ALSO scores each verse against the
    reference-witness cascade (xsrc_gate, gold-free) and escalates on cross-source divergence below `taux`
    (calibrated 0.90: recall=1 at 34% escalation). Still NO gold — the witness is a reads/ reference, not gold.
    Absent `locus`, the gate stays conf-only (the pure legacy contract, for callers without addressing).
    taux: cross-source threshold override (default xsrc_gate.TAUX)."""
    pim = preprocess(load_scan(ocr_dir, page_index))
    W, H = pim.width, pim.height
    ck = f"{ocr_dir}:{page_index}:{W}x{H}"
    seg = segment(pim, cache_key=ck)
    lines = list(seg.lines)

    # R2 (fine-tuned) — the production recognizer
    r2_lines = recognize_lines(r2_model, pim, seg)
    roles = layout.type_lines(lines, W, H)
    for rec, role, ln in zip(r2_lines, roles, lines):
        rec["role"] = role
        rec["bbox"] = layout.line_bbox(ln)   # px (x0,y0,x1,y1) in preprocessed-page coords, for verse_geom (§8 R3-4)
    body_lines = [l for l in r2_lines if l["role"] == "body"]
    r2_body = layout.strip_verse_numbers(_norm(" ".join(l["text"] for l in body_lines)))

    conf = page_confidence(body_lines)
    dropped = {r: roles.count(r) for r in ("header", "marginalia", "catchword") if roles.count(r)}

    result = {
        "ocr_dir": ocr_dir, "page_index": page_index, "page_px": (W, H),
        "n_lines": len(lines), "dropped_apparatus": dropped,
        "r2_body": r2_body,
        "lines": [{"text": l["text"], "conf": round(l["conf"], 4), "role": l["role"], "bbox": l.get("bbox")}
                  for l in r2_lines],
        "page_conf": conf,
        "escalate_r3": conf < conf_gate,   # gold-free gate: low self-confidence → send to R3
        "conf_gate": conf_gate,
    }

    # §7 ALARM 2 — cross-source divergence (the calibrated gold-free router conf is blind to). Opt-in: needs the
    # page's (book, chapter) so the reference witness can be pulled. Escalation is flag-IN only — it routes a
    # verse to R3, never accepts one (agreement ≠ pass). When absent, the gate stays conf-only.
    if locus is not None:
        import xsrc_gate
        book, chapter = locus
        # Pass `taux` straight through (None ⇒ AXIS-AWARE per verse: 0.90 archaic / 0.92 modern-fallback). Do NOT
        # pre-resolve to a single page-wide value — that forces the archaic constant onto modern-fallback verses
        # and silently under-escalates the [0.90,0.92) band (code-review HIGH-1, 2026-07-25). A float overrides
        # both axes intentionally. This matches r3_route.rescue_page, which passed taux through correctly.
        import verse_locate
        # HYBRID LOCALIZATION (2026-07-27): segment the page with `best_spans` — per verse, whichever of the
        # global aligner and the anchor-walk fits janvier better (gold-free selector). Measured on the 177 gold
        # verses: mean identity 0.9215 -> 0.9548, passing 131 -> 147, Wilcoxon p=0.00007, and the runaway spans
        # (a "verse" of 53 lines) are structurally gone. This is a GATE input, not cosmetics: a span pointed at
        # the wrong place scores low against the witness and is escalated as an OCR failure, so sharper
        # localization moves verses out of the flagged set for the right reason instead of masking a bad read.
        # The SAME dict goes to verse_geom downstream (r3_route.rescue_page) so the crop is cut from the span
        # that was scored. `lines` here carry `bbox`, so the walk arm has the geometry it needs.
        spans = verse_locate.best_spans(result, book, chapter)
        xs_scores = xsrc_gate.cross_source_verse_scores(r2_body, book, chapter, taux=taux, spans=spans)
        flagged = [v for v, s in xs_scores.items() if s["escalate"]]
        no_locate = (len(xs_scores) == 0)                       # R2 localized to no verse → page-level OPEN
        xs_vals = [s["xsrc_id"] for s in xs_scores.values() if s["xsrc_id"] is not None]
        conf_fired = result["escalate_r3"]
        result["cross_source"] = {
            "book": book, "chapter": chapter, "taux": taux,     # None = axis-aware; per-verse τx is in verse_scores
            "n_verses": len(xs_scores), "n_flagged": len(flagged),
            "flagged_verses": sorted(flagged), "no_locate": no_locate,
            "worst_xsrc": round(min(xs_vals), 4) if xs_vals else None,
            "seg": {"engine": "hybrid-best_spans",
                    "walk": sum(1 for s in xs_scores.values() if s.get("seg_source") == "walk"),
                    "align": sum(1 for s in xs_scores.values() if s.get("seg_source") == "align")},
            "verse_scores": {v: {k: s.get(k) for k in ("xsrc_id", "xsrc_gate", "escalate", "xsrc_below_taux",
                                                       "seg_open", "arc_src", "taux", "seg_source", "seg_fit")}
                             for v, s in xs_scores.items()},
        }
        result["escalate_r3"] = bool(conf_fired or flagged or no_locate)
        result["escalate_reasons"] = ([f"conf<{conf_gate}"] if conf_fired else []) + \
            ([f"xsrc-alarm2({len(flagged)}v<τx)"] if flagged else []) + (["no-locate"] if no_locate else [])
    if want_r1:
        r1_lines = recognize_lines(base_model, pim, seg)
        for rec, role in zip(r1_lines, roles):
            rec["role"] = role
        r1_body_lines = [l for l in r1_lines if l["role"] == "body"]
        result["r1_body"] = layout.strip_verse_numbers(_norm(" ".join(l["text"] for l in r1_body_lines)))
        result["r1_body_raw"] = _norm(" ".join(l["text"] for l in r1_lines))  # pre-layout, for diagnosis
    if want_base:
        result["base"] = base_ocr(ocr_dir, page_index)
    return result


def low_conf_lines(result, line_gate=0.85):
    """Body lines whose recognition confidence is below the line gate — the regions R3 should re-read.
    Gold-free: uses only the recognizer's own per-char confidence."""
    return [i for i, l in enumerate(result["lines"])
            if l["role"] == "body" and l["conf"] < line_gate]


def reocr_batch(ocr_dir, page_indices, *, out_dir=None, r2_model=R2_MODEL, conf_gate=0.92,
                line_gate=0.85, want_r1=False, run_r3=False, progress=True, locus_map=None, taux=None):
    """Run the gold-free ladder over a range of pages of ONE volume (corpus-scale). Writes one JSON per page
    (full structured transcript: whole-page lines with roles + confidences + the body transcript) and returns
    a QA summary flagging pages/lines that need R3 escalation. This is the tool that lets us transcribe the
    ~3,028-page corpus WITHOUT page-by-page human transcription: R2 handles the confident majority, the gate
    routes the low-confidence residual to R3.

    run_r3=True: on gate-flagged pages, auto-run the Rung-3 vision-LLM pass (reocr_r3). Failure-safe — if the
    vision call errors (e.g. missing/invalid API creds), the page is recorded with `r3_error` and the batch
    continues; the escalation flag STAYS set (No Silent Degradation: the page is not silently 'accepted')."""
    out = Path(out_dir) if out_dir else (HERE / ".reocr-out" / ocr_dir)
    out.mkdir(parents=True, exist_ok=True)
    import open_ledger
    ledger = open_ledger.OpenLedger()     # terminal OPEN worklist (No Silent Degradation): the residual R3 can't clear
    summary = []
    for n, pi in enumerate(page_indices):
        try:
            r = reocr_page(ocr_dir, pi, r2_model=r2_model, conf_gate=conf_gate,
                           want_base=False, want_r1=want_r1,
                           locus=(locus_map.get(pi) if locus_map else None), taux=taux)
        except Exception as e:
            summary.append({"page": pi, "error": f"{type(e).__name__}: {e}"});  continue
        lc = low_conf_lines(r, line_gate)
        r["low_conf_body_lines"] = lc
        r3_note = ""
        if run_r3 and r["escalate_r3"]:
            loc = locus_map.get(pi) if locus_map else None
            if loc is None:
                # verse-targeted R3 needs (book, chapter) to localize crops; without it we cannot re-read a
                # specific verse. Surface it (never silently 'accept' the page) — the page stays escalated.
                r["r3_error"] = "run_r3 needs a locus (book,chapter) to target crops; none supplied for this page"
                r3_note = " R3✗(no-locus)"
            else:
                try:
                    import r3_route
                    rr = r3_route.rescue_page(r, ocr_dir, pi, loc[0], loc[1], ledger=ledger, taux=taux)
                    r["r3_route"] = rr
                    r3_note = (f" R3[{rr['n_rescued']}✓ {rr['n_content_rescued_s_open']}ſ-open "
                               f"{rr['n_open']}○]")
                except Exception as e:      # surfaced, not swallowed — page stays flagged for R3
                    r["r3_error"] = f"{type(e).__name__}: {e}"
                    r3_note = " R3✗"
        (out / f"page_{pi:04d}.json").write_text(json.dumps(r, ensure_ascii=False, indent=1))
        summary.append({"page": pi, "page_conf": r["page_conf"], "n_body": sum(1 for l in r["lines"] if l["role"] == "body"),
                        "n_low_conf": len(lc), "escalate_r3": r["escalate_r3"], "dropped": r["dropped_apparatus"],
                        **({"xsrc_flagged": r["cross_source"]["n_flagged"], "worst_xsrc": r["cross_source"]["worst_xsrc"],
                            "escalate_reasons": r.get("escalate_reasons")} if r.get("cross_source") else {}),
                        **({"r3": {k: r["r3_route"][k] for k in ("n_rescued", "n_content_rescued_s_open", "n_open")}}
                           if r.get("r3_route") else {}),
                        **({"r3_error": r["r3_error"]} if r.get("r3_error") else {})})
        if progress:
            flag = "⚠R3" if r["escalate_r3"] else "  "
            print(f"  [{n+1}/{len(page_indices)}] p{pi:04d} conf={r['page_conf']:.3f} "
                  f"low-conf-lines={len(lc)} {flag}{r3_note}", flush=True)
    esc = [s for s in summary if s.get("escalate_r3")]
    (out / "_qa_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1))
    if run_r3:
        ledger.write(out / "_open_ledger.json")           # the terminal human-review worklist (blocks the deliverable)
        try:
            import reocr_r3
            reocr_r3.shutdown_mlx()                        # release the load-once olmOCR process
        except Exception:
            pass
    print(f"\nbatch done: {len(summary)} pages → {out}/ ; {len(esc)} flagged for R3 "
          f"({100*len(esc)/max(1,len(summary)):.0f}%)")
    if run_r3:
        s = ledger.summary()
        print(f"OPEN ledger: {s['n_open']} verse(s) unresolved after R3 (blocks_deliverable={s['blocks_deliverable']})"
              f"{'; by reason ' + str(s['by_reason']) if s['n_open'] else ''}")
    return summary


if __name__ == "__main__":
    import sys
    if len(sys.argv) >= 4 and sys.argv[1] == "batch":
        od = sys.argv[2]; lo, hi = (int(x) for x in sys.argv[3].split("-"))
        reocr_batch(od, range(lo, hi + 1))
    else:
        od, pi = sys.argv[1], int(sys.argv[2])
        r = reocr_page(od, pi)
        print(f"=== {od} p{pi} ({r['page_px'][0]}x{r['page_px'][1]}, {r['n_lines']} lines, "
              f"dropped {r['dropped_apparatus']}, page_conf {r['page_conf']}, escalate={r['escalate_r3']}) ===")
        print("R2 body[:300]:", r["r2_body"][:300])

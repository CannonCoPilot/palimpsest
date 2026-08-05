"""reocr_ladder.py — the OriginalDR re-OCR remediation LADDER (Sir, v8.1).

This is a WORKLIST + a DIAGNOSTIC GATE, deliberately NOT an auto-remediation pipeline. Nothing in the
re-OCR programme is implemented here beyond rung 0; the higher rungs are specified so the design is
legible and so no method gets redesigned before a human has actually *looked* at the failing page.

    ┌────────────────────────────────────────────────────────────────────────────────────────────┐
    │ RUNG 0 — DIAGNOSTIC RASTERIZE  ·  MANDATORY GATE  ·  *implemented here*                       │
    │   For each worst-scoring locus (scripture chapter / apparatus element), content-anchor the    │
    │   failing scan back to its SOURCE PDF PAGE and rasterize that page to a PNG. Jarvis then       │
    │   VISUALLY INSPECTS the raster and records the observed failure mode (ſ/f confusion, drop-cap  │
    │   glyph-stream reordering, columnar gutter, marginalia bleed, blur/skew, missing region…).    │
    │   No higher rung may fire until this visual sign-off exists for the locus.                     │
    │   WHY a gate: the metric only says a page FAILED, never WHY. Redesigning an OCR method from the │
    │   score alone is guessing; the eye tells you which rung is even applicable. (No Silent          │
    │   Degradation — we confirm the real limit before re-approaching it, never accept the gap.)     │
    ├────────────────────────────────────────────────────────────────────────────────────────────┤
    │ RUNG 1 — LAYOUT-AWARE RE-OCR       (only after rung-0 sign-off marks "legible, mis-segmented")│
    │   Re-run OCR with layout/reading-order handling: column/gutter detection, drop-cap anchoring,  │
    │   running-header suppression, body-vs-margin typing. Targets segmentation failures.            │
    ├────────────────────────────────────────────────────────────────────────────────────────────┤
    │ RUNG 2 — REGION-TARGETED RE-OCR    (only after rung-0 sign-off marks "glyph-level errors")     │
    │   Crop to the failing region at higher DPI and re-OCR just that band with an archaic-aware     │
    │   model / lexicon (ſ-placement, ligatures, u/v, archaic orthography). Targets glyph fidelity.  │
    ├────────────────────────────────────────────────────────────────────────────────────────────┤
    │ RUNG 3 — VISION-LLM TRANSCRIPTION  (only after rung-0 sign-off marks "OCR-intractable")        │
    │   Last resort: a vision-LLM transcribes the rasterized region directly, cross-checked against  │
    │   the modern reference for content and hand-verified for archaic surface before it may credit  │
    │   a witness. Most expensive; reserved for pages the cheaper rungs cannot lift.                  │
    └────────────────────────────────────────────────────────────────────────────────────────────┘

Rung 0's page resolution is EMPIRICAL, never fabricated: a scripture chapter is located in a scan by
content-token recall of its modern reads against the scan's diplomatic OCR pages (the same localization
principle the audit uses); an apparatus element is located by recall of its s_dismas reference text over
the scan's front pages. The peak page's index is read from the diplomatic page label's trailing `_NNNN`
(0-based, matching PyMuPDF), so the raster is of the actual source leaf. If a target cannot be resolved
to a real page it is reported as an explicit gap — never silently rasterized to a wrong page.

CLI:
  reocr_ladder.py                 rank worst targets, rasterize rung-0 diagnostics, write index + sheet
  reocr_ladder.py --k 8           cap scripture targets (default 6); apparatus worklist is always full
  reocr_ladder.py --list          rank + resolve pages but do NOT rasterize (dry run)
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

import fitz  # PyMuPDF  # type: ignore[import-not-found]

HERE = Path(__file__).resolve().parent
PALIMPSEST = Path("/Users/nathanielcannon/Claude/Projects/palimpsest")
SOURCES = PALIMPSEST / "imports/Scripture/Bibles/DouayRheims_DR/sources"
RECON = PALIMPSEST / "core/tests/fixtures/gold/mask_engine/originaldr_reconstruction"
READS = HERE.parent / "reconstruction" / "reads"
VERSE_AUDIT = HERE / "coverage-audit-verse.json"
APPARATUS_AUDIT = HERE / "coverage-audit-apparatus.json"
MSL = HERE / "master-source-list.json"
OUTDIR = HERE / "diag-reocr"

sys.path.insert(0, str(HERE))
sys.path.insert(0, str(RECON))
import apparatus_audit as AA  # noqa: E402  # type: ignore[import-not-found]  # sibling spike module

DIPL_ROOT = AA.D.DIPL_ROOT
MODERN_ANCHOR_SOURCES = ("sabates_a", "madueke_b", "odr_com")  # whole-bible modern reads, in preference order
RASTER_DPI = 150
DEFAULT_K = 6  # scripture chapters to diagnose per run (worst-first); apparatus worklist is always full


# --------------------------------------------------------------------------------------------------
# Source mapping and page loading
# --------------------------------------------------------------------------------------------------
def ocrdir_to_pdf() -> dict[str, dict[str, Any]]:
    """Map every diplomatic ocr_dir -> its source PDF (via each witness volume's `file`)."""
    msl = json.loads(MSL.read_text())
    out: dict[str, dict[str, Any]] = {}
    for w in msl.get("witnesses", []):
        for v in w.get("volumes", []):
            od, f = v.get("ocr_dir"), v.get("file")
            if od and f:
                out[od] = {"source": w.get("source"), "pdf": SOURCES / f, "file": f, "role": v.get("role")}
    return out


_PAGE_CACHE: dict[str, list[tuple[int, str, set[str]]]] = {}


def load_pages(ocr_dir: str, limit: int | None = None) -> list[tuple[int, str, set[str]]]:
    """Return [(pdf_page_index, page_label, folded_token_set), ...] for a diplomatic OCR dir, in scan
    order. pdf_page_index is parsed from the trailing `_NNNN` of the page label (0-based, matching
    PyMuPDF), falling back to sorted-glob position. Cached per ocr_dir (a scan is anchored many times)."""
    ckey = f"{ocr_dir}|{limit}"
    if ckey in _PAGE_CACHE:
        return _PAGE_CACHE[ckey]
    d = DIPL_ROOT / ocr_dir
    pages: list[tuple[int, str, set[str]]] = []
    if d.is_dir():
        files = sorted(d.glob("*.json"))
        if limit:
            files = files[:limit]
        for pos, p in enumerate(files):
            try:
                rec = json.loads(p.read_text())
            except (json.JSONDecodeError, OSError):
                continue
            label = str(rec.get("page", p.stem))
            mt = re.search(r"_(\d+)\s*$", label)
            idx = int(mt.group(1)) if mt else pos
            text = " ".join(ln.get("text", "") for ln in rec.get("lines", []))
            pages.append((idx, label, set(AA._tokens(text))))
    _PAGE_CACHE[ckey] = pages
    return pages


def best_page(anchor: set[str], pages: list[tuple[int, str, set[str]]]) -> dict[str, Any] | None:
    """Locate the page most saturated by the anchor content. Score = |page ∩ anchor| / |page| (the
    localize_element measure — the page whose content is most *concentrated* on the target), with
    recall = |page ∩ anchor| / |anchor| reported alongside. None if nothing overlaps (honest gap)."""
    if not anchor or not pages:
        return None
    scored = []
    for idx, label, toks in pages:
        if not toks:
            continue
        inter = len(toks & anchor)
        if inter == 0:
            continue
        scored.append((round(inter / len(toks), 4), round(inter / len(anchor), 4), idx, label))
    if not scored:
        return None
    scored.sort(reverse=True)
    sat, recall, idx, label = scored[0]
    return {"page_index": idx, "page_label": label, "saturation": sat, "recall": recall}


def locate_region(anchor: set[str], pages: list[tuple[int, str, set[str]]]) -> dict[str, Any] | None:
    """Locate a MULTI-PAGE element the way the audit does (localize_element): peak page by content
    saturation, then the contiguous run of pages whose saturation stays >= half the peak. Rung 0
    rasterizes the region's OPENING leaf and reports the span; recall is measured over the whole run,
    so a genuine preface reads high and a spurious single-page vocabulary match reads low (a signal)."""
    n = len(pages)
    sats = [(len(p[2] & anchor) / len(p[2]) if p[2] else 0.0) for p in pages]
    if not any(sats):
        return None
    peak = max(range(n), key=lambda i: sats[i])
    thr = sats[peak] * 0.5
    lo = hi = peak
    while lo - 1 >= 0 and sats[lo - 1] >= thr:
        lo -= 1
    while hi + 1 < n and sats[hi + 1] >= thr:
        hi += 1
    union: set[str] = set()
    for i in range(lo, hi + 1):
        union |= pages[i][2]
    region_recall = round(len(union & anchor) / len(anchor), 4) if anchor else 0.0
    o_idx, o_label, _ = pages[lo]
    return {"page_index": o_idx, "page_label": o_label, "saturation": round(sats[peak], 4),
            "recall": region_recall, "region_pages": hi - lo + 1,
            "region_span": [pages[lo][0], pages[hi][0]]}


# --------------------------------------------------------------------------------------------------
# Anchors
# --------------------------------------------------------------------------------------------------
_READS_CACHE: dict[str, list[dict[str, Any]]] = {}


def _reads(source: str) -> list[dict[str, Any]]:
    if source not in _READS_CACHE:
        p = READS / f"{source}.json"
        _READS_CACHE[source] = (json.loads(p.read_text()).get("reads", []) if p.exists() else [])
    return _READS_CACHE[source]


def chapter_anchor(book: str, chapter: int) -> set[str]:
    """Folded token set for a scripture chapter, from the first modern reads source that carries it."""
    prefix = f"scripture/{book}/{chapter}/"
    for src in MODERN_ANCHOR_SOURCES:
        toks: set[str] = set()
        for r in _reads(src):
            if str(r.get("skeleton_id", "")).startswith(prefix):
                toks |= set(AA._tokens(str(r.get("surface", ""))))
        if toks:
            return toks
    return set()


def apparatus_anchors() -> dict[str, set[str]]:
    """Folded token set per apparatus element, from the s_dismas front-matter reference parse."""
    refs: dict[str, list[str]] = {}
    refs.update(AA.parse_ot_frontmatter())
    refs.update(AA.parse_nt_frontmatter())
    return {locus: set(AA._tokens("\n".join(pages))) for locus, pages in refs.items()}


# --------------------------------------------------------------------------------------------------
# Target ranking (from the audit worklists — measured, not narrative)
# --------------------------------------------------------------------------------------------------
def _verse_scan_ocrdirs(va: dict[str, Any]) -> dict[tuple[str, int, str], str]:
    """(book, chapter, scan_id) -> ocr_dir, harvested from the verse audit's per-verse localization."""
    out: dict[tuple[str, int, str], str] = {}
    for rec in va.get("verses", {}).values():
        book, ch = rec.get("book"), rec.get("chapter")
        for scan, sd in (rec.get("sources", {}) or {}).items():
            od = sd.get("ocr_dir")
            if book and ch is not None and od:
                out.setdefault((book, int(ch), scan), od)
    return out


def rank_scripture(va: dict[str, Any], k: int) -> tuple[list[dict[str, Any]], int]:
    """Worst chapters first: most verses short, then most missing witnesses. Returns (top_k, dropped)."""
    wl = sorted(va.get("reocr_worklist", []),
                key=lambda w: (-(w.get("verses_shortfall") or 0), -(w.get("missing") or 0)))
    return wl[:k], max(0, len(wl) - k)


def rank_apparatus(ap: dict[str, Any]) -> list[dict[str, Any]]:
    """The full apparatus re-OCR worklist (localizes but below the 0.90 archaic bar)."""
    return list(ap.get("reocr_worklist", []))


# --------------------------------------------------------------------------------------------------
# Rasterization
# --------------------------------------------------------------------------------------------------
def rasterize(pdf: Path, page_index: int, out_png: Path, dpi: int = RASTER_DPI) -> bool:
    if not pdf.exists():
        return False
    doc = fitz.open(pdf)
    try:
        if not (0 <= page_index < doc.page_count):
            return False
        zoom = dpi / 72.0
        pix = doc.load_page(page_index).get_pixmap(matrix=fitz.Matrix(zoom, zoom))
        out_png.parent.mkdir(parents=True, exist_ok=True)
        pix.save(str(out_png))
        return True
    finally:
        doc.close()


# --------------------------------------------------------------------------------------------------
# Rung 0 driver
# --------------------------------------------------------------------------------------------------
def rung0(k: int = DEFAULT_K, do_raster: bool = True) -> dict[str, Any]:
    va = json.loads(VERSE_AUDIT.read_text())
    ap = json.loads(APPARATUS_AUDIT.read_text())
    pdfmap = ocrdir_to_pdf()
    scan_dirs = _verse_scan_ocrdirs(va)
    records: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []

    # scripture: locate the worst chapters in their failing scans, rasterize one representative leaf each.
    scripture, dropped = rank_scripture(va, k)
    for t in scripture:
        book, ch = t["book"], int(t["chapter"])
        anchor = chapter_anchor(book, ch)
        failed = list(t.get("localized_but_failed", []))
        resolved = False
        for scan in failed:
            od = scan_dirs.get((book, ch, scan))
            if not od or od not in pdfmap:
                continue
            hit = best_page(anchor, load_pages(od))
            if not hit:
                continue
            pdf = pdfmap[od]["pdf"]
            tag = f"scripture-{book}-{ch}-{scan}-p{hit['page_index']}"
            png = OUTDIR / f"{tag}.png"
            ok = rasterize(pdf, hit["page_index"], png) if do_raster else pdf.exists()
            records.append({
                "rung": 0, "domain": "scripture", "locus": t["locus"], "book": book, "chapter": ch,
                "scan": scan, "ocr_dir": od, "source_pdf": pdfmap[od]["file"],
                "page_index": hit["page_index"], "page_label": hit["page_label"],
                "recall": hit["recall"], "saturation": hit["saturation"],
                "also_failed": [s for s in failed if s != scan],
                "verses_shortfall": t.get("verses_shortfall"), "missing_witnesses": t.get("missing"),
                "png": str(png.relative_to(HERE)) if ok else None, "rasterized": bool(ok),
                "inspection": None,  # filled by Jarvis after visual review — the mandatory gate
            })
            resolved = True
            break
        if not resolved:
            unresolved.append({"domain": "scripture", "locus": t["locus"],
                               "reason": "no localized_but_failed scan resolved to a real page",
                               "candidates": failed})

    # apparatus: locate each worklist element in its localized-but-failed scan front pages.
    anchors = apparatus_anchors()
    for t in rank_apparatus(ap):
        locus = t["locus"]
        anchor = anchors.get(locus, set())
        el = ap.get("elements", {}).get(locus, {})
        failed = list(t.get("localized_but_failed", []))
        resolved = False
        for scan in failed:
            od = (el.get("sources", {}).get(scan, {}) or {}).get("ocr_dir")
            if not anchor or not od or od not in pdfmap:
                continue
            # apparatus elements are multi-page: locate the contiguous region (as the audit does) and
            # rasterize its OPENING leaf; the region recall separates a real preface from a spurious match.
            hit = locate_region(anchor, load_pages(od, limit=AA.FRONT_SEARCH_PAGES))
            if not hit:
                continue
            pdf = pdfmap[od]["pdf"]
            tag = f"apparatus-{locus.replace('apparatus/', '').replace('/', '-')}-{scan}-p{hit['page_index']}"
            png = OUTDIR / f"{tag}.png"
            ok = rasterize(pdf, hit["page_index"], png) if do_raster else pdf.exists()
            records.append({
                "rung": 0, "domain": "apparatus", "locus": locus, "scan": scan, "ocr_dir": od,
                "source_pdf": pdfmap[od]["file"], "page_index": hit["page_index"],
                "page_label": hit["page_label"], "recall": hit["recall"], "saturation": hit["saturation"],
                "region_span": hit.get("region_span"), "region_pages": hit.get("region_pages"),
                "also_failed": [s for s in failed if s != scan],
                "best_archaic_id": t.get("best_archaic_id"), "score_grain": t.get("score_grain"),
                "png": str(png.relative_to(HERE)) if ok else None, "rasterized": bool(ok),
                "inspection": None,
            })
            resolved = True
            break
        if not resolved:
            unresolved.append({"domain": "apparatus", "locus": locus,
                               "reason": "no localized_but_failed scan resolved to a real page",
                               "candidates": failed})

    return {
        "rung": 0, "gate": "MANDATORY: Jarvis visual inspection required before any rung>=1",
        "scripture_targets_diagnosed": sum(1 for r in records if r["domain"] == "scripture"),
        "scripture_targets_dropped_over_k": dropped, "k": k,
        "apparatus_targets_diagnosed": sum(1 for r in records if r["domain"] == "apparatus"),
        "unresolved": unresolved, "records": records,
    }


# --------------------------------------------------------------------------------------------------
# Outputs
# --------------------------------------------------------------------------------------------------
def write_index(result: dict[str, Any]) -> Path:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    p = OUTDIR / "index.json"
    p.write_text(json.dumps(result, indent=1))
    return p


def write_contact_sheet(result: dict[str, Any]) -> Path:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    cards = []
    for r in result["records"]:
        img = (f'<img src="{Path(r["png"]).name}" loading="lazy">'
               if r.get("png") else '<div class="noimg">not rasterized</div>')
        also = f' · also failed: {", ".join(r["also_failed"])}' if r.get("also_failed") else ""
        cards.append(
            f'<figure><div class="thumb">{img}</div><figcaption>'
            f'<b>{r["locus"]}</b><br>scan <b>{r["scan"]}</b> · {r["source_pdf"]}<br>'
            f'page idx <b>{r["page_index"]}</b> (recall {r["recall"]}, saturation {r["saturation"]})'
            f'{also}<br><span class="todo">visual inspection: PENDING (rung-0 gate)</span>'
            f'</figcaption></figure>')
    unres = "".join(f"<li>{u['domain']} · <b>{u['locus']}</b> — {u['reason']} "
                    f"(candidates: {', '.join(u['candidates']) or '—'})</li>"
                    for u in result["unresolved"]) or "<li>none</li>"
    html = f"""<!doctype html><html><head><meta charset="utf-8">
<title>re-OCR rung-0 diagnostics</title><style>
body{{font:14px/1.5 -apple-system,sans-serif;margin:24px;color:#222}}
h1{{font-size:20px}} .meta{{color:#555;margin-bottom:16px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:18px}}
figure{{margin:0;border:1px solid #ddd;border-radius:8px;overflow:hidden;background:#fafafa}}
.thumb{{background:#000;text-align:center}} .thumb img{{max-width:100%;max-height:420px;display:block;margin:auto}}
.noimg{{padding:40px;color:#c00;text-align:center}} figcaption{{padding:10px;font-size:12.5px}}
.todo{{color:#b26a00;font-weight:600}} .mono,code{{font-family:ui-monospace,monospace}}
ul{{background:#fff6f6;border:1px solid #f0caca;border-radius:8px;padding:12px 12px 12px 30px}}
</style></head><body>
<h1>Re-OCR ladder — rung 0 (diagnostic rasters)</h1>
<div class="meta"><b>{result['gate']}</b><br>
scripture diagnosed: {result['scripture_targets_diagnosed']}
(dropped over k={result['k']}: {result['scripture_targets_dropped_over_k']}) ·
apparatus diagnosed: {result['apparatus_targets_diagnosed']}</div>
<h3>Unresolved targets (explicit gaps — never rasterized to a guessed page)</h3><ul>{unres}</ul>
<div class="grid">{''.join(cards)}</div>
</body></html>"""
    p = OUTDIR / "contact-sheet.html"
    p.write_text(html)
    return p


def _cli(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="OriginalDR re-OCR ladder — rung 0 diagnostic rasterizer")
    ap.add_argument("--k", type=int, default=DEFAULT_K, help="max scripture chapters to diagnose")
    ap.add_argument("--list", action="store_true", help="resolve pages but do not rasterize")
    a = ap.parse_args(argv)
    result = rung0(k=a.k, do_raster=not a.list)
    idx = write_index(result)
    sheet = write_contact_sheet(result)
    print(f"rung-0: {result['scripture_targets_diagnosed']} scripture + "
          f"{result['apparatus_targets_diagnosed']} apparatus diagnosed; "
          f"{len(result['unresolved'])} unresolved; dropped {result['scripture_targets_dropped_over_k']} "
          f"scripture over k={result['k']}.")
    for r in result["records"]:
        print(f"  [{r['domain']:9s}] {r['locus']:28s} scan {r['scan']:5s} "
              f"pg {r['page_index']:>4} recall {r['recall']:.3f} "
              f"{'->' + r['png'] if r.get('png') else '(not rasterized)'}")
    print(f"index: {idx.relative_to(HERE)} · sheet: {sheet.relative_to(HERE)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli(sys.argv[1:]))

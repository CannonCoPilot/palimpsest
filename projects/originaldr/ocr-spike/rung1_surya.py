"""rung1_surya.py — RUNG 1 done right: per-layout region typing (Surya) + ſ-faithful recognize (kraken).

Controlled A/B on ONE page image and ONE recognizer, isolating the LAYOUT lever:
  A. baseline  = kraken lines filtered by the current x-band (what detect_our_ocr does today)
  B. surya     = kraken lines kept only if their centroid lands in a Surya BODY text-region
                 (running headers -> PageHeader, marginal apparatus -> separate/ small Text box,
                  watermark -> Picture/PageFooter are all typed OUT of the body)

Both variants are scored through the audit's OWN machinery: written as a single-page diplomatic
stream, localized+read by detect_our_ocr.detect_book, then per-verse archaic identity =
edit_ratio(fold_archaic(read), fold_archaic(s_dismas_ref)) — the exact metric behind mean_archaic.

Usage: ocr-venv/bin/python ocr-spike/rung1_surya.py <page.png> <book> <chapter>
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
GOLD = Path("/Users/nathanielcannon/Claude/Projects/palimpsest/core/tests/fixtures/"
            "gold/mask_engine/originaldr_reconstruction")
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(GOLD))

import detect_our_ocr as D  # noqa: E402
from char_identity import edit_ratio, fold_archaic  # noqa: E402

MODEL = str(HERE / "models" / "reichenau_lat.mlmodel")
S_DISMAS = HERE.parent / "reconstruction" / "reads" / "s_dismas.json"
ALIAS = "reocr-tmp"  # NOT in _GEOM_WIDTH -> load_stream normalizes by per-page max x1


def kraken_lines(im: Image.Image) -> list[dict]:
    from kraken import blla, rpred
    from kraken.lib import models
    rec = models.load_any(MODEL, device="cpu")
    g = im.convert("L")
    seg = blla.segment(g, device="cpu")
    out = []
    for r in rpred.rpred(rec, g, seg):
        b = getattr(r, "line", None)
        boundary = (b.get("boundary") if isinstance(b, dict) else None) or getattr(r, "boundary", None)
        if not boundary:
            continue
        xs = [p[0] for p in boundary]
        ys = [p[1] for p in boundary]
        out.append({"text": str(getattr(r, "prediction", "") or ""),
                    "bbox": [min(xs), min(ys), max(xs), max(ys)]})
    return out


def surya_regions(im: Image.Image) -> list[dict]:
    from surya.fast_layout import FastLayoutPredictor
    pred = FastLayoutPredictor()
    res = pred([im.convert("RGB")])[0]
    return [{"label": b.label, "bbox": [float(v) for v in b.bbox]} for b in res.bboxes]


def _area(box):
    x0, y0, x1, y1 = box
    return max(0.0, x1 - x0) * max(0.0, y1 - y0)


def pick_body_regions(regions: list[dict]) -> list[dict]:
    """Body = Text regions whose area is a large fraction of the biggest Text region.
    This keeps single- and 2-column bodies while dropping small marginal Text boxes;
    PageHeader/PageFooter/Footnote/Picture/SectionHeader are excluded outright."""
    texts = [r for r in regions if r["label"] == "Text"]
    if not texts:
        return []
    mx = max(_area(r["bbox"]) for r in texts)
    return [r for r in texts if _area(r["bbox"]) >= 0.40 * mx]


def _centroid_in(box, cx, cy):
    x0, y0, x1, y1 = box
    return x0 <= cx <= x1 and y0 <= cy <= y1


def surya_body_lines(klines: list[dict], body_regions: list[dict]) -> list[dict]:
    keep = []
    for l in klines:
        x0, y0, x1, y1 = l["bbox"]
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        if any(_centroid_in(r["bbox"], cx, cy) for r in body_regions):
            keep.append(l)
    return keep


def archaic_ref(book: str) -> dict[str, str]:
    reads = json.loads(S_DISMAS.read_text())["reads"]
    pref = f"scripture/{book}/"
    return {r["skeleton_id"]: r["surface"] for r in reads
            if r.get("skeleton_id", "").startswith(pref) and r.get("present") and r.get("surface")}


def score_variant(lines: list[dict], book: str, anchor_ch, wid: str, a_ref: dict[str, str]):
    tmp = Path(tempfile.mkdtemp(prefix="reocr-"))
    (tmp / "page.json").write_text(json.dumps({"page": "page", "lines": lines}, ensure_ascii=False))
    stm = D.load_stream(tmp, ALIAS, 2)
    reads, _app, meta = D.detect_book(book, anchor_ch, wid, {ALIAS: stm})
    per = {}
    for r in reads:
        sk = r.get("skeleton_id", "")
        surf = r.get("surface", "") or ""
        if sk in a_ref and surf.strip():
            per[sk] = edit_ratio(fold_archaic(surf), fold_archaic(a_ref[sk]))
    mean = sum(per.values()) / len(per) if per else 0.0
    s_out = sum(l["text"].count("ſ") for l in lines)
    s_ref = sum(a_ref[sk].count("ſ") for sk in per)
    return {"mean_archaic": round(mean, 4), "n_verses": len(per), "s_out": s_out,
            "s_ref": s_ref, "covered": bool(meta.get("covered")),
            "probe_recall": meta.get("probe_recall"),
            "verses": sorted(int(sk.split("/")[3]) for sk in per)}


def main() -> int:
    if len(sys.argv) < 4:
        print("usage: rung1_surya.py <page.png> <book> <chapter>", file=sys.stderr)
        return 2
    page, book, ch = sys.argv[1], sys.argv[2], int(sys.argv[3])
    wid = "S1"
    im = Image.open(page)
    W, H = im.size
    print(f"page {page} {W}x{H}  book={book} ch={ch}", flush=True)

    klines = kraken_lines(im)
    print(f"kraken lines: {len(klines)}", flush=True)
    regions = surya_regions(im)
    body_regions = pick_body_regions(regions)
    print(f"surya regions: {len(regions)}  body-text regions: {len(body_regions)}", flush=True)

    baseline_lines = klines  # load_stream applies the current x-band 0.11-0.88 itself
    surya_lines = surya_body_lines(klines, body_regions)
    print(f"surya body lines kept: {len(surya_lines)}/{len(klines)}", flush=True)

    a_ref = archaic_ref(book)
    anchor_ch = D.anchor_by_book(D.load_anchor()).get(book, {})

    base = score_variant(baseline_lines, book, anchor_ch, wid, a_ref)
    sury = score_variant(surya_lines, book, anchor_ch, wid, a_ref)

    print("\n=== RUNG-1 SURYA A/B (same image, same recognizer) ===")
    print(f"{'variant':<10}{'mean_arch':>10}{'n_v':>5}{'ſ out/ref':>12}{'covered':>9}{'probe':>7}")
    for name, r in (("baseline", base), ("surya", sury)):
        pr = f"{r['probe_recall']:.2f}" if isinstance(r['probe_recall'], (int, float)) else "?"
        print(f"{name:<10}{r['mean_archaic']:>10.4f}{r['n_verses']:>5}"
              f"{str(r['s_out'])+'/'+str(r['s_ref']):>12}{str(r['covered']):>9}{pr:>7}")
    d = sury["mean_archaic"] - base["mean_archaic"]
    print(f"\nΔ mean_archaic (surya - baseline): {d:+.4f}")
    print(f"baseline verses: {base['verses']}")
    print(f"surya    verses: {sury['verses']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

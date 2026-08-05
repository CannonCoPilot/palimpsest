"""rung1_batch.py — run the rung-1 re-OCR loop across all diagnosed scripture loci.

Loads the ſ-faithful recognizer ONCE, then for each locus: segment+recognize the diag page,
detect the verse-window from the OCR's own verse numbers, score the BASELINE body selection
(x-band 0.11–0.88, what detect_our_ocr does today) against the RUNG-1 geometric suppression,
on BOTH tracks (edit_ratio via fold_archaic + a separate ſ-count). Prints a movement table.

Usage: ocr-venv/bin/python ocr-spike/rung1_batch.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from char_identity import fold_archaic, edit_ratio  # noqa: E402

REF = json.loads((HERE.parent / "reconstruction" / "reads" / "s_dismas.json").read_text())["reads"]
MODEL = str(HERE / "models" / "reichenau_lat.mlmodel")
DIAG = HERE / "diag-reocr"

LOCI = [
    ("psalms", 118, "scripture-psalms-118-S1-p227.png"),
    ("matthew", 26, "scripture-matthew-26-S10-p105.png"),
    ("john", 6, "scripture-john-6-S1-p236.png"),
    ("psalms", 77, "scripture-psalms-77-S1-p144.png"),
    ("genesis", 24, "scripture-genesis-24-S1-p99.png"),
    ("matthew", 27, "scripture-matthew-27-S1-p99.png"),
]


def ref_verses(book: str, ch: int) -> dict[int, str]:
    out = {}
    for r in REF:
        m = re.match(rf"scripture/{book}/{ch}/(\d+)$", r.get("skeleton_id", "") or "")
        if m and r.get("present") and r.get("surface"):
            out[int(m.group(1))] = r["surface"]
    return out


def strip_vnum(t: str) -> str:
    return re.sub(r"^\s*\d{1,3}\s*", "", t).strip()


def main() -> int:
    from kraken import blla, rpred  # type: ignore[import-not-found]
    from kraken.lib import models  # type: ignore[import-not-found]

    rec = models.load_any(MODEL, device="cpu")
    print("recognizer loaded (reichenau_lat)\n")

    results = []
    for book, ch, png in LOCI:
        im = Image.open(str(DIAG / png)).convert("L")
        W, H = im.size
        seg = blla.segment(im, device="cpu")
        recs = list(rpred.rpred(rec, im, seg))
        lines = []
        for r in recs:
            b = getattr(r, "line", None)
            boundary = (b.get("boundary") if isinstance(b, dict) else None) or getattr(r, "boundary", None)
            if not boundary:
                continue
            xs = [p[0] for p in boundary]; ys = [p[1] for p in boundary]
            lines.append({"text": str(getattr(r, "prediction", "") or ""),
                          "xc": (min(xs) + max(xs)) / 2 / W, "yc": (min(ys) + max(ys)) / 2 / H})

        rv = ref_verses(book, ch)

        # CONTENT-ANCHORED window (not OCR verse numbers): a ref verse is "on this page" if its
        # folded tokens have high recall in the folded main-column OCR body. Robust to number misreads.
        main_body = " ".join(l["text"] for l in lines if 0.11 <= l["xc"] <= 0.80)
        body_tok = set(fold_archaic(main_body).split())

        def recall(vt: str) -> float:
            toks = [t for t in fold_archaic(vt).split() if len(t) >= 3]
            if not toks:
                return 0.0
            return sum(1 for t in toks if t in body_tok) / len(toks)

        # a page is a CONTIGUOUS verse span. High-recall verses (>=0.6, content words really present)
        # anchor the span ends; fill between them. Common-word false positives rarely clear 0.6 alone.
        hot = [v for v in sorted(rv) if recall(rv[v]) >= 0.6]
        if hot:
            lo, hi = min(hot), max(hot)
            window = [v for v in sorted(rv) if lo <= v <= hi]
        else:
            window = sorted(rv)
        ref_text = " ".join(rv[v] for v in window)

        # find ANNOTATIONS block: everything at/below the first annotation-ish line is dropped (rung-1)
        anno_y = 1.01
        for l in sorted(lines, key=lambda z: z["yc"]):
            if re.search(r"ANNOTATION|Annotation|annotation", l["text"]):
                anno_y = l["yc"]; break

        def assemble(sel):
            keep = sorted([l for l in lines if sel(l)], key=lambda z: (z["yc"], z["xc"]))
            return " ".join(strip_vnum(l["text"]) for l in keep if l["text"].strip())

        base = assemble(lambda l: 0.11 <= l["xc"] <= 0.88)  # current detect_our_ocr body filter
        r1 = assemble(lambda l: 0.065 <= l["yc"] <= 0.965 and 0.11 <= l["xc"] <= 0.80 and l["yc"] < anno_y)

        s_base = edit_ratio(fold_archaic(base), fold_archaic(ref_text))
        s_r1 = edit_ratio(fold_archaic(r1), fold_archaic(ref_text))
        s_ref = ref_text.count("ſ")
        s_out = r1.count("ſ")
        results.append({"locus": f"{book}/{ch}", "verses": f"{window[0]}–{window[-1]}" if window else "?",
                        "n_v": len(window), "base": round(s_base, 4), "rung1": round(s_r1, 4),
                        "delta": round(s_r1 - s_base, 4), "s_ref": s_ref, "s_out": s_out,
                        "s_faithful": (s_out >= 0.5 * s_ref) if s_ref else True})

    (DIAG / "rung1-batch-results.json").write_text(json.dumps(results, indent=1, ensure_ascii=False))
    print(f"{'locus':<14}{'verses':<10}{'baseline':>9}{'rung-1':>9}{'Δ':>8}   ſ(out/ref)  faithful  ≥0.90")
    print("-" * 78)
    for r in results:
        bar = "PASS" if r["rung1"] >= 0.90 else "open"
        print(f"{r['locus']:<14}{r['verses']:<10}{r['base']:>9.4f}{r['rung1']:>9.4f}{r['delta']:>+8.4f}"
              f"   {r['s_out']:>3}/{r['s_ref']:<4}    {'Y' if r['s_faithful'] else 'N✗':<8}  {bar}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

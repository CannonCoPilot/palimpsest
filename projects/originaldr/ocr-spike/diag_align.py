"""diag_align.py — separate RECOGNITION quality from ALIGNMENT artifact.

1. concat OCR body vs concat of the true on-page reference verses -> alignment-FREE recognition score.
2. per OCR read: best-match ratio over ALL book refs (oracle) vs the slot detect_book assigned ->
   if oracle >> assigned, the loss is ALIGNMENT, not recognition.

Usage: ocr-venv/bin/python ocr-spike/diag_align.py <page.png> <book> <chapter> <vlo> <vhi>
"""
from __future__ import annotations

import json
import re
import sys
import tempfile
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import rung1_surya as R  # noqa: E402
import detect_our_ocr as D  # noqa: E402
from char_identity import edit_ratio, fold_archaic  # noqa: E402


def strip_vnum(t: str) -> str:
    return re.sub(r"^\s*\d{1,3}\s*", "", t).strip()


def main() -> int:
    page, book, ch = sys.argv[1], sys.argv[2], int(sys.argv[3])
    vlo, vhi = int(sys.argv[4]), int(sys.argv[5])
    im = Image.open(page)
    klines = R.kraken_lines(im)
    body = R.pick_body_regions(R.surya_regions(im))
    slines = R.surya_body_lines(klines, body)
    a_ref = R.archaic_ref(book)

    # (1) alignment-free: concat OCR body vs concat of true on-page verses
    ocr_concat = " ".join(strip_vnum(l["text"]) for l in slines if l["text"].strip())
    onpage = [f"scripture/{book}/{ch}/{v}" for v in range(vlo, vhi + 1) if f"scripture/{book}/{ch}/{v}" in a_ref]
    ref_concat = " ".join(a_ref[k] for k in onpage)
    concat_ratio = edit_ratio(fold_archaic(ocr_concat), fold_archaic(ref_concat))
    print(f"ALIGNMENT-FREE concat ratio (OCR body vs {book} {ch}:{vlo}-{vhi}): {concat_ratio:.4f}")
    print(f"  OCR chars={len(ocr_concat)}  REF chars={len(ref_concat)}  ſ OCR={ocr_concat.count('ſ')} REF={ref_concat.count('ſ')}")

    # (2) oracle vs assigned via detect_book
    anchor_ch = D.anchor_by_book(D.load_anchor()).get(book, {})
    tmp = Path(tempfile.mkdtemp(prefix="align-"))
    (tmp / "page.json").write_text(json.dumps({"page": "page", "lines": slines}, ensure_ascii=False))
    stm = D.load_stream(tmp, R.ALIAS, 2)
    reads, _a, _m = D.detect_book(book, anchor_ch, "S1", {R.ALIAS: stm})
    ref_items = list(a_ref.items())
    assigned_sum = oracle_sum = 0.0
    n = 0
    print("\nper-read: assigned-slot ratio  vs  oracle best-match  (chapter drift shown)")
    for r in reads:
        sk = r.get("skeleton_id", "")
        surf = (r.get("surface", "") or "").strip()
        if not surf or sk not in a_ref:
            continue
        fo = fold_archaic(surf)
        assigned = edit_ratio(fo, fold_archaic(a_ref[sk]))
        best_k, best_r = max(((k, edit_ratio(fo, fold_archaic(v))) for k, v in ref_items), key=lambda x: x[1])
        assigned_sum += assigned
        oracle_sum += best_r
        n += 1
        drift = "" if best_k == sk else f"  <-- best matches {best_k.split('/',2)[2]}"
        if assigned < 0.6 or drift:
            print(f"  slot {sk.split('/',2)[2]:<8} assigned={assigned:.3f}  oracle={best_r:.3f}{drift}")
    if n:
        print(f"\nMEAN assigned={assigned_sum/n:.4f}   MEAN oracle={oracle_sum/n:.4f}   (n={n})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

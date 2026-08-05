"""diag_recognition.py — LOOK at where re-OCR identity is lost, per verse.

Reuses rung1_surya's kraken+surya extraction, scores through detect_book, then dumps
per-verse: reference surface vs OCR surface vs edit_ratio (worst first), so we can tell
SYSTEMATIC pipeline failure (misalignment, fused/missing lines, verse-number contamination,
wrong reading order) from scattered RECOGNITION noise.

Usage: ocr-venv/bin/python ocr-spike/diag_recognition.py <page.png> <book> <chapter>
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import rung1_surya as R  # noqa: E402
import detect_our_ocr as D  # noqa: E402
from char_identity import edit_ratio, fold_archaic  # noqa: E402


def main() -> int:
    page, book, ch = sys.argv[1], sys.argv[2], int(sys.argv[3])
    im = Image.open(page)
    klines = R.kraken_lines(im)
    regions = R.surya_regions(im)
    body = R.pick_body_regions(regions)
    slines = R.surya_body_lines(klines, body)
    a_ref = R.archaic_ref(book)
    anchor_ch = D.anchor_by_book(D.load_anchor()).get(book, {})

    tmp = Path(tempfile.mkdtemp(prefix="diag-"))
    (tmp / "page.json").write_text(json.dumps({"page": "page", "lines": slines}, ensure_ascii=False))
    stm = D.load_stream(tmp, R.ALIAS, 2)
    reads, _app, meta = D.detect_book(book, anchor_ch, str("S1"), {R.ALIAS: stm})

    rows = []
    for r in reads:
        sk = r.get("skeleton_id", "")
        surf = (r.get("surface", "") or "").strip()
        if sk in a_ref:
            ratio = edit_ratio(fold_archaic(surf), fold_archaic(a_ref[sk])) if surf else 0.0
            rows.append((ratio, sk, a_ref[sk], surf))
    rows.sort()
    print(f"page={page}  covered={meta.get('covered')} probe={meta.get('probe_recall')}  "
          f"n_scored={len(rows)}  mean={sum(r[0] for r in rows)/len(rows):.4f}")
    print("=" * 100)
    for ratio, sk, ref, ocr in rows:
        v = sk.split("/")[3]
        print(f"\n[v{v}] ratio={ratio:.3f}")
        print(f"  REF: {ref[:160]}")
        print(f"  OCR: {ocr[:160]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

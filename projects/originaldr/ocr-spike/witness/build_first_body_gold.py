"""R2.2b/A1 -- read the head rows of each leaf so the FIRST BODY LINE can be hand-adjudicated.

⚠️ WHY A SEPARATE ARTEFACT AND NOT MORE ENTRIES IN THE REGION GOLD. The region gold answers "what
REGION is this token", over the top 3 rows of a fixed crop. A1 asks a different question about a
different object: "where on the page is this leaf's first line of scripture". On a CHAPTER-OPENING
leaf the answer lies BELOW the region gold's 3-row window -- which is exactly why A1 came out
unevaluable on leaves 403 and 411. Widening the region gold's window to reach it would change the
denominator of every number recorded against that file (0.8760 and the R2.1j figures). A separate,
separately-scoped file leaves those untouched.

⚠️ ANTI-CIRCULARITY, TWICE OVER, AND IT IS THE POINT OF THIS MODULE.
  1. **The label may not come from the band under test.** If the first body line were identified by
     asking where the anchored band puts it, A1 would be the band grading its own homework -- "a
     boxer evaluated on the boxes it proposed always looks excellent". So the rows here are read by
     the RECOGNISER, as whole-row crops, and adjudicated on WHAT THEY SAY.
  2. **Nor from `region_head`.** It is the instrument A1 exists to test. Its MainText/RunningHead
     decision is never consulted; a row is head matter here because it READS as the book's name or
     `CHAP.`, not because a rule labelled it so.
This follows the region gold's own stated basis -- LABELS COME FROM WHAT THE TOKEN SAYS, NEVER FROM
WHERE IT SITS -- and the word-count gold's practice of adjudicating against a DIFFERENT instrument
from the one under test.

⚠️ THE ROWS ARE FOUND WITH NO PAGE FRACTION, by `page_type_rows` over the whole page, for the same
reason the band is: a window here would put a fraction back into the evidence A1 rests on.

This module only READS. It writes candidates to `.scratch/` for adjudication and never writes the
gold file itself -- a gold written by the same pass that read it is a gold nobody adjudicated.

    python witness/build_first_body_gold.py --rows 8
"""

import argparse
import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(_HERE.parent))

import witnesses as W
import collation_read as CR

MODEL = _HERE.parent / "models/reichenau_dr.mlmodel"
OUT = _HERE.parent / ".scratch/r2/first-body-candidates.json"
LEAVES = range(400, 420)


def main(nrows) -> int:
    from kraken.lib import models
    m = models.load_any(str(MODEL))
    vol, sig = [k for k in W.WITNESSES if W.wid(*k) == "OT1-1609-B"][0]
    leaves = W.leaves(vol, sig)

    out = {}
    for i in LEAVES:
        rows, frame, p, why = CR.page_type_rows(leaves[i])
        if rows is None or p is None:
            print(f"  ⚠️ ABSTAIN leaf {i}: {why}")
            out[str(i)] = {"abstain": why}
            continue
        p = float(p)
        page, _f = CR.band_frame(leaves[i], 0.0, 1.0)
        recs = []
        for j, r in enumerate(rows[:nrows]):
            t = min(g[0] for g in r); b = max(g[1] for g in r)
            l = min(g[2] for g in r); rr = max(g[3] for g in r)
            pad = max(4, int(round(0.35 * p)))
            crop = page.crop((max(0, l - pad), max(0, t - pad),
                              min(page.width, rr + pad), min(page.height, b + pad)))
            txt, conf = CR.read(m, crop) if crop.width >= 8 and crop.height >= 8 else ("", 0.0)
            recs.append({"row": j,
                         "y0f": round(CR.page_y_frac(frame, t), 6),
                         "y1f": round(CR.page_y_frac(frame, b), 6),
                         "xlf": round(CR.page_x_frac(frame, l), 6),
                         "xrf": round(CR.page_x_frac(frame, rr), 6),
                         "read": txt, "conf": round(conf, 3), "n_glyphs": len(r)})
        out[str(i)] = {"pitch": round(p, 3), "rows": recs}
        print(f"\nleaf {i}  (pitch {p:.1f})")
        for r in recs:
            print(f"  row {r['row']}  y {r['y0f']:.4f}..{r['y1f']:.4f}  x {r['xlf']:.3f}..{r['xrf']:.3f}"
                  f"  n={r['n_glyphs']:3d}  conf {r['conf']:.2f}  {r['read'][:78]!r}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
    print(f"\ncandidates written: {OUT}")
    print("⚠️ NOT a gold file. Adjudicate these readings, then write "
          "witness/gold/first_body_line_OT1-1609-B_400-419.json by hand.")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--rows", type=int, default=8)
    raise SystemExit(main(ap.parse_args().rows))

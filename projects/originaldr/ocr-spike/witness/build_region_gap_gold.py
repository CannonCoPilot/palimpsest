"""R2.2e -- record the rows SWALLOWED WHOLE into one out-of-block token, as E3's reference set.

⚠️ WHAT IS ADJUDICATED HERE AND WHAT IS NOT.
  * WHICH ROWS are affected is a MEASUREMENT of the shipping pipeline, taken with both candidate
    flags OFF: a row carrying one out-of-block token of >= 20 glyphs that spans >= 75% of the row's
    ink. That is the defect's own definition and it is reproducible, not a judgement.
  * WHAT THE ROW IS is the adjudication, and it comes from WHAT THE ROW SAYS -- its whole-row
    recogniser reading -- plus, for the sample rendered to `.scratch/r2/plates/`, from looking at the
    leaf. `† And Moyses referred their people` and `the familie of the Noemanites. † The` are
    scripture in anybody's reading. ⚠️ NOT from `region_head`, which is the instrument under test.
  * WHICH ROWS ARE ARGUMENT rows is taken from GOLD-ARGUMENT by page-fraction overlap, so the two
    reference sets cannot disagree about the same row. Those are excluded from E3, whose bar is
    about the 44 rows that are BODY.

⚠️ THE ROW INDEX IS NOT AN ADDRESS. Entries carry `y0f/y1f` page fractions (the R2.2c address) and
are matched by BEST OVERLAP -- an ordinal is the defect R2.1i, R2.1j and R2.2c each removed once, and
a float EQUALITY is the one `score_argument_region` then hit on its first run at scale.

    python witness/build_region_gap_gold.py            # rewrite the gold
    python witness/build_region_gap_gold.py --check    # verify against the page; write nothing
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
import region_head as RG
import score_argument_region as SA

GOLD = _HERE / "gold/region_gap_rows_OT1-1609-B_400-419.json"
ARG_GOLD = _HERE / "gold/argument_rows_OT1-1609-B_400-419.json"
CANDS = _HERE.parent / ".scratch/r2/first-body-candidates.json"
MIN_GLYPHS_SWALLOWED = 20
MIN_SPAN_FRAC = 0.75


def build():
    vol, sig = [k for k in W.WITNESSES if W.wid(*k) == "OT1-1609-B"][0]
    leaves = W.leaves(vol, sig)
    cand = json.loads(CANDS.read_text()) if CANDS.exists() else {}
    ag = json.loads(ARG_GOLD.read_text())
    arg = {}
    for e in ag["rows"]:
        arg.setdefault(e["leaf"], []).append((e["y0f"], e["y1f"]))

    was = (RG.REGION_GAP_TOKENS, RG.ARGUMENT_RULE)
    RG.REGION_GAP_TOKENS = False          # ⚠️ the defect is defined on the SHIPPING pipeline
    RG.ARGUMENT_RULE = False
    out = []
    for i in range(400, 420):
        band, frame = CR.band_frame(leaves[i], 0.0, 1.0)
        p, src = CR.scale(band)
        if p is None:
            print(f"  ⚠️ ABSTAIN leaf {i}: no type scale ({src})")
            continue
        toks, why = RG.classify(band, p)
        if toks is None:
            print(f"  ⚠️ ABSTAIN leaf {i}: {why}")
            continue
        rows = CR._rows_and_lines(CR.glyph_boxes(band, 0, p), p)
        reads = {r["row"]: r["read"] for r in cand.get(str(i), {}).get("rows", [])}
        per = {}
        for t in toks:
            per.setdefault(t["row"], []).append(t)
        for j, v in sorted(per.items()):
            big = [t for t in v
                   if not t["in_block"] and t["n_glyphs"] >= MIN_GLYPHS_SWALLOWED]
            if not big:
                continue
            wide = max(big, key=lambda t: t["n_glyphs"])
            span = (wide["r"] - wide["l"]) / max(1.0, wide["row_r"] - wide["row_l"])
            if span < MIN_SPAN_FRAC:
                continue
            y0 = CR.page_y_frac(frame, min(x[0] for x in rows[j]))
            y1 = CR.page_y_frac(frame, max(x[1] for x in rows[j]))
            ys = {0: (y0, y1)}
            is_arg = any(SA.best_overlap(s, ys) is not None for s in arg.get(i, []))
            out.append({
                "leaf": i, "row_at_labelling": j,
                "y0f": round(y0, 6), "y1f": round(y1, 6),
                "xlf": round(CR.page_x_frac(frame, wide["l"]), 6),
                "xrf": round(CR.page_x_frac(frame, wide["r"]), 6),
                "n_glyphs": wide["n_glyphs"], "span_frac": round(span, 3),
                "is_argument_row": bool(is_arg),
                "read": reads.get(j, ""),
            })
    RG.REGION_GAP_TOKENS, RG.ARGUMENT_RULE = was
    return out


def doc(rows):
    body = [r for r in rows if not r["is_argument_row"]]
    return {
        "what": "R2.2e -- the rows whose ink is swallowed into ONE out-of-block token and therefore "
                "labelled MarginNote by the shipping pipeline. E3's reference set.",
        "defect": "`region_head` R2 sets `in_block = not (l < L - tol or r > R + tol)`. A token that "
                  "spans the measure NECESSARILY fails that test, so a row the splitter failed to "
                  "cut is typed MARGINALIA -- an entire line of scripture. 🔴 `region_segments` "
                  "splits those same rows correctly, so TWO SPLITTERS DISAGREE ABOUT ONE ROW AND "
                  "THE COARSER ONE DECIDES THE LABEL.",
        "selection": f"MEASURED, not judged, with REGION_GAP_TOKENS and ARGUMENT_RULE both OFF: a "
                     f"row carrying an out-of-block token of >= {MIN_GLYPHS_SWALLOWED} glyphs "
                     f"spanning >= {MIN_SPAN_FRAC:.0%} of the row's ink.",
        "basis": "WHAT each row IS comes from what it SAYS (its whole-row recogniser reading) and, "
                 "for the rendered sample, from looking at the leaf -- never from `region_head`, "
                 "the instrument under test. Argument rows are taken from GOLD-ARGUMENT by "
                 "page-fraction overlap so the two reference sets cannot disagree about a row.",
        "address": "y0f/y1f are PAGE fractions (the R2.2c address), matched by BEST OVERLAP. ⚠️ "
                   "`row_at_labelling` is traceability ONLY -- an ordinal is the defect R2.1i, "
                   "R2.1j and R2.2c each removed once, and a float EQUALITY is the one "
                   "`score_argument_region` hit on its first run at scale.",
        "counts": f"{len(rows)} rows over the 20 leaves; {len(body)} are BODY (E3's bar) and "
                  f"{len(rows) - len(body)} are argument rows already covered by GOLD-ARGUMENT.",
        "provenance": "Built by `witness/build_region_gap_gold.py`; found by "
                      "`.scratch/r2/probe_unsplit_rows.py`; scored by "
                      "`witness/score_region_gap_tokens.py`.",
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="verify against the page; write nothing")
    a = ap.parse_args()
    rows = build()
    payload = {"_doc": doc(rows), "rows": rows}
    body = sum(1 for r in rows if not r["is_argument_row"])

    if a.check:
        have = json.loads(GOLD.read_text())
        bad = 0
        if len(have["rows"]) != len(rows):
            print(f"🔴 file has {len(have['rows'])} rows, page gives {len(rows)}")
            bad += 1
        else:
            for x, y in zip(have["rows"], rows):
                for f in ("leaf", "row_at_labelling", "y0f", "y1f", "is_argument_row"):
                    if (round(float(x[f]), 4) if isinstance(x[f], float) else x[f]) != (
                            round(float(y[f]), 4) if isinstance(y[f], float) else y[f]):
                        print(f"🔴 leaf {x['leaf']} r{x['row_at_labelling']}: {f} {x[f]} != {y[f]}")
                        bad += 1
        print(f"{'🔴 ' if bad else ''}{len(rows)} swallowed rows, {body} of them BODY -- "
              f"{'MISMATCH' if bad else 'reproduces from the page'}")
        return 1 if bad else 0

    GOLD.write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n")
    print(f"wrote {GOLD}")
    print(f"  {len(rows)} swallowed rows; {body} BODY (E3's bar), {len(rows) - body} argument")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

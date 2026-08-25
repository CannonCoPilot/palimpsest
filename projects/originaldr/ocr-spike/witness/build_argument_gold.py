"""R2.2d step (1) -- assemble GOLD-ARGUMENT over EVERY chapter opening in OT1-1609-B leaves 400-419.

⚠️ WHAT IS ADJUDICATION HERE AND WHAT IS NOT. The tables below (`BLOCKS`, `NEGATIVES`) ARE the
adjudication: each range and each negative was decided by LOOKING at the rendered leaf, where the
italic fount is unmistakable against the roman scripture. This module derives nothing but the
ADDRESS -- the page fractions and the recogniser's reading, both read off the page. No label here
comes from `region_head`, the instrument under test, and none comes from the positional rule
"between a ChapterHead and the first verse", which presumes the boundary it is meant to find.

⚠️ WHY THE GOLD HAD TO GROW. R2.2d measured D1/D2 on FOUR leaves while the whole-page censuses put
argument blocks on TEN. The gold was the binding constraint, so D2 was a subset result and 46 rows
the rule labelled ARGUMENT were reported UNADJUDICATED -- truth unknown, counted neither way.

⚠️ THE THREE ENUMERATORS, AND WHY IT TOOK ALL THREE.
  1. `probe_chap_census_wholepage.py` -- CHAP heads over the WHOLE page. The earlier census read
     only a leaf's first 8 rows, which is how leaf 406's mid-page `CHAP. XXV.` was missed.
  2. `probe_slant_census.py` -- row slant over the whole page, net wider than the rule's.
  3. `probe_seg_census_all.py` -- THE RULE ITSELF at a widened net. Needed because 1 and 2 are
     ROW-level: a row whose average slant is upright can still hold an italic SEGMENT, so neither
     can prove ABSENCE, and "this leaf carries no argument" is exactly a claim of absence.
  Where 1 and 2 disagreed is where the eye was required, and each disagreement was real:
     leaf 406  slant-only -- a true chapter opening whose head row READS as its side-note.
     leaf 410  head-only  -- 'CHAP' at the FOOT is the CATCHWORD for leaf 411. No chapter opens.
     leaf 417  two heads  -- `CHAP. XXX.` at r33 heads the ANNOTATIONS, not a chapter.

⚠️ FOUNT IS REGION-DEPENDENT, WHICH THE RULE DOES NOT YET KNOW. In the body, italic marks the
argument and roman the scripture. Inside ANNOTATIONS (leaf 417 r41-r43) it INVERTS: the roman is
commentary and the italic is QUOTED SCRIPTURE. So an italic-fount test alone can never separate an
argument from an annotation's quotation -- recorded here as adjudicated negatives so that the limit
is measured rather than described.

    python witness/build_argument_gold.py            # rewrite the gold
    python witness/build_argument_gold.py --check    # verify the file matches the page; write nothing
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

GOLD = _HERE / "gold/argument_rows_OT1-1609-B_400-419.json"
CANDS = _HERE.parent / ".scratch/r2/first-body-candidates.json"

# ── THE ADJUDICATION ──────────────────────────────────────────────────────────────────────────────
# leaf -> (first argument row, last argument row, chapter-head row, first verse row, note)
# Row indices are into `CR.page_type_rows`; they are the handle used to BUILD the entry and are
# recorded as `row_at_labelling` for traceability only. ⚠️ NEVER an address -- an ordinal into a list
# the row clusterer controls is the defect R2.1i, R2.1j and R2.2c each had to remove once.
BLOCKS = {
    400: (25, 37, 24, 38, "CHAP. XXII. at r24. Eight italic lines, r25-r37 detected ('Balac King of "
                          "Moab fearing the Israelites, sendeth for Balaam a soothsayer to curse "
                          "them. 8. ... 35. and is charged to speake nothing but that the Angel "
                          "shal suggest.'). The even rows r26/r29/r31/r35/r37 are FRAGMENTS of the "
                          "line above -- curvature drifts a baseline past the clusterer's tolerance "
                          "and cuts one printed line into two detected rows. First verse r38, "
                          "roman, slant 0."),
    403: (4, 9, 3, 10, "CHAP. XXIII. at r3. Argument r4-r9 ('Balaam endeuoureth to curse Israel, but "
                       "God forceth him to blesse them. 11. ... 26. Yet Balac insisteth willing him "
                       "to curse, or not to blesse them.'). First verse r10, drop-cap."),
    404: (38, 47, 37, 48, "CHAP. XXIIII. at r37. Argument r38-r47 ('Balaam forced by the euidence of "
                          "truth (though not conuerted in wil to serue God, whom he confesseth to "
                          "be omnipotent) prophecieth stil more good of Israel: 10. ... 20. Also of "
                          "Amalacheites, Cineites, and Italians.'). r47 is the SHORT LAST LINE "
                          "('Italians.', 8 components) -- the case R3's span test cannot reach. "
                          "First verse r48, drop-cap A."),
    406: (18, 21, 17, 22, "🔴 CHAP. XXV. MID-PAGE at r17 -- AND THE WHOLE-PAGE CHAP CENSUS MISSED IT. "
                          "The head row's recogniser reading is 'ap: 4. v. CHAXXV.': the left "
                          "marginal note wins the row read, so a text census looking for 'CHAP' at "
                          "the head of a row finds nothing. Only the slant census saw the leaf. "
                          "Argument r18-r21 ('By carnal fornication manie are drawen to spiritual. "
                          "... 10. Phinees his zele in stabbing to death two fornicators, is "
                          "commended by God, and rewarded.'). First verse r22."),
    407: (35, 45, 33, 46, "CHAP. XXVI. at r33, whose row read also carries the ROMAN marginal column "
                          "('tie, against the'). Argument r35-r45 ('Al the men of twelue tribes "
                          "being againe numbered ... 64. al being dead in the desert, which were "
                          "numbered before, except Caleb and Iosue.'), ending in the short last line "
                          "r45. ⚠️ r36/r38/r40/r42/r44 are fragments that run out INTO the roman "
                          "marginal column: mixed rows, argument ink and margin ink on one baseline. "
                          "r34 is PURE margin inside the argument's y-band and is an adjudicated "
                          "NEGATIVE -- the trap a y-band alone would fall into. First verse r46."),
    411: (3, 13, 2, 14, "CHAP. XXVII. at r2. Argument r3-r13, eleven detected rows ('Salphaads "
                        "daughters succede to their fathers inheritance. 8. ... and the people.'). "
                        "First verse r14."),
    412: (31, 35, 30, 36, "CHAP. XXVIII. MID-PAGE at r30, whose row read carries the LEFT marginal "
                          "column ('Duke, but Elea.'). Argument r31-r35 ('Special sacrifices are "
                          "appointed for euerie day in the morning and euening. 9. ... for Pasch, "
                          "26. and for Pentecost.'). Every row is mixed: roman side-note at the left "
                          "edge, italic argument to the measure. First verse r36."),
    414: (7, 10, 6, 11, "CHAP. XXIX. MID-PAGE at r6. Argument r7-r10 ('In the seuenth moneth are "
                        "celebrated with particular sacrifices the feastes of Trumpets, 7. ... and "
                        "Collection.'). r9 is a FRAGMENT of r8. r10 carries the argument's short "
                        "last line AND the marginal verse number '6.'. First verse r11, drop-cap T "
                        "with a ':: Feast of' side-note."),
    416: (13, 15, 12, 16, "CHAP. XXX. MID-PAGE at r12. Argument r13-r15 ('Voluntarie vowes or oathes "
                          "of men; 14. of maides in their fathers houses, ... or are made "
                          "frustrate.'). First verse r16."),
    417: (49, 62, 48, 63, "🔴 TWO 'CHAP.' ROWS, ONE CHAPTER. r33 'CHAP. XXX.' heads the ANNOTATIONS "
                          "section (r32 reads 'ANNOTATIONS.') and opens NO chapter; the real head is "
                          "r48 'CHAP. XXXI.'. Argument r49-r62 ('The Madianites are slaine in "
                          "battle, for that they had drawen the people of Israel to sinne. 11. ... "
                          "48. The princes of the hoste geue free offerings to our Lord.'). r62 is a "
                          "fragment of r61. First verse r63."),
}

# leaf -> [(row, why)] -- rows adjudicated NOT-ARGUMENT. Every one of these is a row the ARGUMENT
# rule DOES label ARGUMENT at its shipping net (slant >= 8, >= 8 components), except where noted:
# they are the measured content of D2, not a list of things that happen to be elsewhere.
NEGATIVES = {
    401: [(31, "right-margin italic patristic citation 'Theodoret. q.' -- inside `in_block`'s edge "
               "tolerance, so the rule reaches it"),
          (33, "right-margin italic citation '40. Procopius. in Num.'")],
    403: [(28, "right-margin italic citation '( saith S. Hierom. de mans.'"),
          (62, "right-margin italic citation 'do. S. Greg. li. 33. c. 17. Moral.'")],
    405: [(11, "right-margin italic SIDE-NOTE 'Manie do prophecie, and cast out diuels', sharing a "
               "baseline with the roman verse '† How beautiful are thy tabernacles ô Iacob'. THE "
               "case that refuted the row-level fount test"),
          (13, "the same side-note, continued"),
          (62, "right-margin italic citation 'Psal. 2. Act. 13. v. 8.'")],
    406: [(39, "left-margin italic citation 'See Apoc. 2. v. 14.'")],
    407: [(34, "⚠️ ROMAN marginal row lying INSIDE the argument's y-band ('killers wil. Ca-'). The "
               "rule does NOT fire on it -- it is recorded because a y-band or row-range definition "
               "of the argument WOULD sweep it in")],
    410: [(46, "⚠️ 'CHAP' at the page FOOT is the CATCHWORD for leaf 411's `CHAP. XXVII.`, not a "
               "head. Leaf 410 opens no chapter and carries no argument. The one leaf where the "
               "CHAP census fired and the slant census did not")],
    412: [(37, "left-margin italic side-note 'his going out,'"),
          (38, "left-margin italic side-note 'and going in.'")],
    417: [(41, "🔴 ANNOTATIONS, where the fount INVERTS: roman is commentary and the italic is "
               "QUOTED SCRIPTURE -- '( Leuit. 23. v. 29. ) Euerie soule that is not af-'"),
          (42, "the same quotation, continued: 'flicted (that is, which fasteth not) this day,'"),
          (43, "the same quotation, ending: 'shal perish out of his people.'")],
}

WINDOW = range(400, 420)


def _addr(frame, row):
    return {
        "y0f": round(CR.page_y_frac(frame, min(g[0] for g in row)), 6),
        "y1f": round(CR.page_y_frac(frame, max(g[1] for g in row)), 6),
        "xlf": round(CR.page_x_frac(frame, min(g[2] for g in row)), 6),
        "xrf": round(CR.page_x_frac(frame, max(g[3] for g in row)), 6),
    }


def build():
    vol, sig = [k for k in W.WITNESSES if W.wid(*k) == "OT1-1609-B"][0]
    leaves = W.leaves(vol, sig)
    cand = json.loads(CANDS.read_text()) if CANDS.exists() else {}
    rows_out, negs_out = [], []
    for i in WINDOW:
        if i not in BLOCKS and i not in NEGATIVES:
            continue
        rows, frame, p, why = CR.page_type_rows(leaves[i])
        if rows is None:
            raise SystemExit(f"leaf {i}: no rows ({why})")
        reads = {r["row"]: r["read"] for r in cand.get(str(i), {}).get("rows", [])}
        if i in BLOCKS:
            lo, hi, _head, _first, _note = BLOCKS[i]
            for j in range(lo, hi + 1):
                rows_out.append({"leaf": i, "row_at_labelling": j, **_addr(frame, rows[j]),
                                 "read": reads.get(j, "")})
        for j, whyn in NEGATIVES.get(i, []):
            negs_out.append({"leaf": i, "row_at_labelling": j, **_addr(frame, rows[j]),
                             "read": reads.get(j, ""), "why": whyn})
    return rows_out, negs_out


def doc(rows_out, negs_out):
    return {
        "what": "GOLD-ARGUMENT -- the rows of the italic CHAPTER ARGUMENT on OT1-1609-B leaves "
                "400-419. The reference set for R2.2d's criteria D1 (recall) and D2 (precision).",
        "why_it_had_to_exist":
            "🔴 The 121-token region gold CANNOT score this at any bar. Every chapter head in the "
            "window sits at a row the region gold's 3-row window never reaches, so EVERY argument "
            "row lies outside it. Its sparseness on 403 and 411 -- 2 and 4 entries, no MainText at "
            "all -- is the FOSSIL of this missing category: the labeller had no admissible label.",
        "scope": f"ALL {len(BLOCKS)} chapter openings in the window are labelled row by row "
                 f"({sorted(BLOCKS)}). ⚠️ The previous version covered FOUR (403, 411, 414, 416), so "
                 f"D2 was a subset result and the rest were reported UNADJUDICATED. That caveat is "
                 f"now discharged: {len(rows_out)} argument rows and {len(negs_out)} adjudicated "
                 f"negatives, and the negatives are the rows the rule actually fires on.",
        "address": "y0f/y1f/xlf/xrf are PAGE fractions (the R2.2c address). ⚠️ `row_at_labelling` is "
                   "recorded for traceability ONLY and is NOT an address: a row index is an ordinal "
                   "into a list the row-clusterer controls, which is the defect R2.1i, R2.1j and "
                   "R2.2c each had to remove once. Score by page-fraction overlap, never by it.",
        "basis": "LABELS COME FROM WHAT THE ROW IS SET IN, NOT FROM WHERE IT SITS. Each row was "
                 "adjudicated from the RENDERED leaf (the italic fount is unmistakable against the "
                 "roman scripture) together with its whole-row recogniser reading. ⚠️ NOT from "
                 "`region_head`, which is the instrument under test, and NOT from the positional "
                 "rule 'between a ChapterHead and the first verse' -- that rule presumes the "
                 "boundary it is meant to find.",
        "negatives": "`negatives` are rows adjudicated NOT-ARGUMENT. All but one are rows the rule "
                     "DOES label ARGUMENT at its shipping net, so they are D2's measured content. "
                     "Two kinds: (a) marginal italic side-notes and patristic citations that fall "
                     "just inside `in_block`'s edge tolerance; (b) 🔴 leaf 417's ANNOTATIONS, where "
                     "the fount INVERTS -- roman is commentary, italic is QUOTED SCRIPTURE. An "
                     "italic-fount test alone cannot separate (b) from an argument.",
        "coverage": f"{20 - len(BLOCKS)} of the 20 leaves carry NO argument and are the precision "
                    f"test: a rule that paints scripture as argument destroys the reading it was "
                    f"built to protect.",
        "provenance": "Built by `witness/build_argument_gold.py`, whose BLOCKS/NEGATIVES tables ARE "
                      "the adjudication; this file holds only the addresses it read off the page. "
                      "Enumerated by `.scratch/r2/probe_{chap_census_wholepage,slant_census,"
                      "seg_census_all}.py`, rendered for the eye by "
                      "`.scratch/r2/probe_render_{adjudicate,fpcands}.py`. Row readings from "
                      "`witness/build_first_body_gold.py --rows 16`. Scored by "
                      "`witness/score_argument_region.py`.",
        "per_leaf": {str(i): BLOCKS[i][4] for i in sorted(BLOCKS)},
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="verify the gold on disk matches the page; write nothing")
    a = ap.parse_args()
    rows_out, negs_out = build()
    payload = {"_doc": doc(rows_out, negs_out), "rows": rows_out, "negatives": negs_out}

    if a.check:
        have = json.loads(GOLD.read_text())
        bad = 0
        for k in ("rows", "negatives"):
            h, w = have.get(k, []), payload[k]
            if len(h) != len(w):
                print(f"🔴 {k}: file has {len(h)}, page gives {len(w)}"); bad += 1; continue
            for x, y in zip(h, w):
                for f in ("leaf", "row_at_labelling", "y0f", "y1f", "xlf", "xrf"):
                    if round(float(x[f]), 4) != round(float(y[f]), 4):
                        print(f"🔴 {k} leaf {x['leaf']} r{x['row_at_labelling']}: {f} "
                              f"{x[f]} != {y[f]}"); bad += 1
        print(f"{'🔴 ' if bad else ''}{len(payload['rows'])} argument rows over {len(BLOCKS)} "
              f"leaves, {len(payload['negatives'])} negatives -- "
              f"{'MISMATCH' if bad else 'addresses reproduce from the page'}")
        return 1 if bad else 0

    GOLD.write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n")
    print(f"wrote {GOLD}")
    print(f"  {len(rows_out)} argument rows over {len(BLOCKS)} chapter openings {sorted(BLOCKS)}")
    print(f"  {len(negs_out)} adjudicated negatives over {len(NEGATIVES)} leaves "
          f"{sorted(NEGATIVES)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

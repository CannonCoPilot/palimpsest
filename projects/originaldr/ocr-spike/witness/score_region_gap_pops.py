"""R2.2o.1 -- are a WORD SPACE and a REGION GAP separable by width at all?

`CR.region_segments` cuts a row wherever an intra-row gap exceeds ONE LINE PITCH, on the rule "a gap
wider than the line pitch is a run to another region, not a word space". R2.2n refuted four span
rules built on top of that primitive, each buying ~1 MarginNote for 11-12 MainText, and R2.2o
measured why: of 301 body-like rows, 102 (34%) have no continuous segment reaching 0.75 of the
measure, because JUSTIFIED setting stretches the word space to fill the measure.

That established the primitive mis-cuts. It did NOT establish that a better THRESHOLD exists. This
does: it labels every intra-row gap from the GOLD and publishes the two width distributions, so the
question "is there any single threshold that separates them" is answered with a number instead of
being tuned around.

⚠️ WHERE THE LABELS COME FROM, and why not from geometry. The rule under test is geometric. Labelling
a gap a region gap BECAUSE IT IS WIDE would score the instrument against its own signal and guarantee
whatever answer the instrument already gives -- the circularity `gold/head_regions_*.json`'s own
`labelling_basis` forbids ("LABELS COME FROM WHAT THE TOKEN SAYS, NEVER FROM WHERE IT SITS"). So:

  * the LABEL of a gap is adjudicated by the GOLD's hand-assigned region labels (RH/MN/MT/CH), read
    off the text in R2.1g and unchanged since;
  * GEOMETRY is used only to ADDRESS which gold entry a glyph belongs to -- vertical INK overlap
    (`ink2d`, the address adopted at R2.2j after the row ordinal was refuted), plus x-containment of
    the glyph's centre in the entry's span. Addressing is not adjudication (R2.1i).

A gap between two glyphs is:
  * WORD SPACE   -- both glyphs address the SAME gold entry. An entry is a contiguous stretch of one
                    region ('deuoured Ar of the Moabites, and the inhabitantes of the' is one entry,
                    line-length), so every gap inside it is by construction a space between words of
                    one region. This is the population the cut rule must NOT cut.
  * REGION GAP   -- the glyphs address entries of DIFFERENT LABELS (e.g. MT | MN). This is the
                    population the cut rule MUST cut.
  * SAME-LABEL SEAM -- different entries, same label. NOT folded into either population: whether the
                    gold split one region into two entries is a gold-authoring artefact, and quietly
                    calling these word spaces would inflate the word-space tail with real margin
                    runs (two MN entries flanking a body block sit either side of the text block).
                    Counted and printed; never silently dropped (R1.4).
  * UNLABELLED   -- either glyph addresses no entry (the gold labels only the top 3 rows, and
                    excludes tokens under 3 glyph components). Counted and printed.
  * AMBIGUOUS    -- either glyph falls in an entry the gold lists as genuinely ambiguous. Excluded,
                    counted, printed.

⚠️ THE DENOMINATOR IS THE LABELLED GAPS, and the unlabelled count is printed beside it. The S6 bar
exists because a scorer printed a number for months whose verdict read neither line.

    ../ocr-venv/bin/python witness/score_region_gap_pops.py

Verdict: exit 1 if the two labelled populations OVERLAP in width -- i.e. if the best achievable
single threshold still misclassifies gaps. An overlap is not a failure of this script; it is the
finding R2.2o.1 was written to obtain, and it refutes "retune the threshold" as the repair.
"""

import sys
import warnings

warnings.filterwarnings("ignore")

from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(_HERE.parent))

import json

import numpy as np

import collation_read as CR
import witnesses as W
from score_head_regions import GOLD, INK_Y_FRAC, _entry_band, _overlap, top_band

WITNESS = "OT1-1609-B"
LEAF_LO, LEAF_HI = 400, 420          # the R2.2n / R2.2o window, and R2.1d'(A)'s
INCUMBENT_CUT = 1.0                  # `CR.region_segments`: cut where gap > 1 pitch


def _addr(entries, ambig, band_h):
    """-> callable(glyph) -> (entry_index, label) | (None, None) | ('AMBIG', None).

    R2.2j `ink2d`: a glyph is on an entry's line iff their ink overlaps VERTICALLY by at least
    INK_Y_FRAC of the shorter of the two. Then it belongs to the entry whose x-span contains the
    glyph's CENTRE -- the containment binding of R2.1j, which exists because a gold ENTRY is coarser
    than a token and far coarser than a glyph.
    """
    spans = [(_entry_band(e, band_h), e) for e in entries]
    aspans = [(_entry_band(e, band_h), e) for e in ambig if "y0f" in e]

    def of(g):
        y0, y1, x0, x1 = g[0], g[1], g[2], g[3]
        xc = 0.5 * (x0 + x1)
        for (ey0, ey1), e in aspans:
            if _overlap((ey0, ey1), (y0, y1)) >= INK_Y_FRAC * max(1.0, min(ey1 - ey0, y1 - y0)):
                if e["l"] <= xc <= e["r"]:
                    return ("AMBIG", None)
        for i, ((ey0, ey1), e) in enumerate(spans):
            if _overlap((ey0, ey1), (y0, y1)) >= INK_Y_FRAC * max(1.0, min(ey1 - ey0, y1 - y0)):
                if e["l"] <= xc <= e["r"]:
                    return (i, e["label"])
        return (None, None)

    return of


def _best_threshold(word, region):
    """-> (cut, errors, n) minimising misclassification over every candidate cut.

    Candidates are the observed widths themselves; a threshold strictly between two observations
    cannot beat the one at the lower observation. `cut` means: gap > cut => region gap.
    """
    cands = np.unique(np.concatenate([word, region])) if region.size else np.unique(word)
    best = (None, 10**9)
    for c in cands:
        err = int((word > c).sum() + (region <= c).sum())
        if err < best[1]:
            best = (float(c), err)
    return best[0], best[1], word.size + region.size


def main():
    g = json.loads(GOLD.read_text())
    entries, ambig = g["labels"], g["ambiguous"]
    by_leaf = {}
    for e in entries:
        by_leaf.setdefault(e["leaf"], []).append(e)
    amb_by_leaf = {}
    for e in ambig:
        amb_by_leaf.setdefault(e.get("leaf"), []).append(e)

    vol, sig = [k for k in W.WITNESSES if W.wid(*k) == WITNESS][0]
    leaves = W.leaves(vol, sig)

    word, region, seam = [], [], []
    n_unlab = n_amb = n_gaps = 0
    pairs = {}                                   # (labelA, labelB) -> [widths]
    mnmt = []                                    # the boundary the MN gap is actually about

    for i in range(LEAF_LO, LEAF_HI):
        ents = by_leaf.get(i, [])
        if not ents:
            continue
        band = top_band(leaves[i])
        p, _ = CR.scale(band)
        if p is None:
            continue
        band_h = band.size[1]
        rows = CR._rows_and_lines(CR.glyph_boxes(band, 0, p), p)
        addr = _addr(ents, amb_by_leaf.get(i, []), band_h)
        for row in rows:
            xs = sorted(row, key=lambda gg: gg[2])
            tags = [addr(gg) for gg in xs]
            for (u, tu), (v, tv) in zip(zip(xs, tags), zip(xs[1:], tags[1:])):
                gap = v[2] - u[3]
                if gap <= 0:
                    continue
                n_gaps += 1
                w = gap / p
                (ai, la), (bi, lb) = tu, tv
                if ai == "AMBIG" or bi == "AMBIG":
                    n_amb += 1
                elif ai is None or bi is None:
                    n_unlab += 1
                elif ai == bi:
                    word.append(w)
                elif la == lb:
                    seam.append(w)
                else:
                    region.append(w)
                    pairs.setdefault(tuple(sorted([str(la), str(lb)])), []).append(w)
                    if {la, lb} == {"MN", "MT"}:
                        mnmt.append((i, w, ents[ai]["text"][:28], ents[bi]["text"][:28]))

    wo, re_, se = np.array(word), np.array(region), np.array(seam)
    lab = wo.size + re_.size

    def dist(name, a):
        if not a.size:
            print(f"  {name:16} n=0")
            return
        print(f"  {name:16} n={a.size:5d}  median {np.median(a):6.3f}  p90 {np.percentile(a,90):6.3f}"
              f"  p99 {np.percentile(a,99):6.3f}  max {a.max():7.3f}  min {a.min():6.3f}")

    print(f"R2.2o.1 -- intra-row gap populations, {WITNESS} leaves {LEAF_LO}-{LEAF_HI-1}")
    print("labels from GOLD-HEADBAND region labels; geometry used only to address. Widths in PITCHES.\n")
    print(f"gaps examined            {n_gaps}")
    print(f"  labelled (denominator) {lab}   -- both glyphs address a gold entry")
    print(f"  unlabelled             {n_unlab}   -- gold labels the top 3 rows only; counted, not scored")
    print(f"  ambiguous (excluded)   {n_amb}   -- listed in the gold's `ambiguous`")
    print(f"  same-label seam        {se.size}   -- different entries, SAME label; not in either population\n")
    dist("WORD SPACE", wo)
    dist("REGION GAP", re_)
    dist("same-label seam", se)

    if not re_.size or not wo.size:
        print("\n🔴 one population is EMPTY -- no separability question can be answered. NOT a pass.")
        return 1

    lo, hi = re_.min(), wo.max()
    print(f"\nOVERLAP  region-gap min {lo:.3f}  vs  word-space max {hi:.3f}")
    if lo > hi:
        print("  ✅ SEPARATED -- no word space is as wide as the narrowest region gap.")
    else:
        w_in = int(((wo >= lo) & (wo <= hi)).sum())
        r_in = int(((re_ >= lo) & (re_ <= hi)).sum())
        print(f"  🔴 OVERLAPPING on [{lo:.3f}, {hi:.3f}] pitches")
        print(f"     word spaces in the overlap  {w_in} of {wo.size} ({100*w_in/wo.size:.1f}%)")
        print(f"     region gaps in the overlap  {r_in} of {re_.size} ({100*r_in/re_.size:.1f}%)")

    inc_err = int((wo > INCUMBENT_CUT).sum() + (re_ <= INCUMBENT_CUT).sum())
    cut, err, n = _best_threshold(wo, re_)
    print(f"\nTHRESHOLD, on the labelled gaps ({n}):")
    print(f"  incumbent  gap > {INCUMBENT_CUT:.3f} pitch : {inc_err} misclassified "
          f"({100*inc_err/n:.2f}%)  [{int((wo>INCUMBENT_CUT).sum())} word spaces cut, "
          f"{int((re_<=INCUMBENT_CUT).sum())} region gaps missed]")
    print(f"  BEST possible gap > {cut:.3f} pitch : {err} misclassified ({100*err/n:.2f}%)  "
          f"[{int((wo>cut).sum())} word spaces cut, {int((re_<=cut).sum())} region gaps missed]")

    print("\nregion gaps by label pair:")
    for k in sorted(pairs, key=lambda k: -len(pairs[k])):
        a = np.array(pairs[k])
        print(f"  {k[0]}|{k[1]:4}  n={a.size:4d}  median {np.median(a):6.3f}  min {a.min():6.3f}")

    # ⚠️ MN|MT is the boundary the MN gap is about, and MN|RH (n=14, median 7.3 pitches) is not --
    # the running head and the side-note are separated by the whole head of the page, which no rule
    # has ever got wrong. Printing the MN|MT instances individually because the aggregate is carried
    # by the easy pair.
    if mnmt:
        print("\nMN|MT boundaries -- the ones the MN gap is about:")
        for lf, w, ta, tb in sorted(mnmt, key=lambda r: r[1]):
            mark = "🔴 BELOW the incumbent cut -- NOT cut" if w <= INCUMBENT_CUT else "cut"
            print(f"  leaf {lf}  gap {w:6.3f} pitches  {mark}")
            print(f"      {ta!r} | {tb!r}")

    # ── The accounting `region_segments` ACTUALLY faces ───────────────────────────────────────────
    # The primitive does not decide "are these two gold ENTRIES different"; it decides "should this
    # row be CUT here". A seam between two entries of the SAME label is a gap the row must NOT be cut
    # at -- one region either side. Folding the seams into the must-not-cut population is only
    # legitimate if no seam actually spans the text block (two MN entries either side of the body
    # would be same-label yet genuinely separate). That is CHECKED, not assumed: a cross-block seam
    # would be pitches wide, like the MN|RH gaps above.
    if se.size:
        cross = int((se >= re_.min()).sum())
        print(f"\nSEAM CHECK -- seams as wide as the narrowest region gap ({re_.min():.3f}): {cross}")
        if cross:
            print("  ⚠️ at least one seam may span the text block; NOT folded in. Reporting the")
            print("     entry-level accounting only.")
        else:
            nocut = np.concatenate([wo, se])
            n2 = nocut.size + re_.size
            inc2 = int((nocut > INCUMBENT_CUT).sum() + (re_ <= INCUMBENT_CUT).sum())
            cut2, err2, _ = _best_threshold(nocut, re_)
            print("  ✅ no seam reaches region-gap width => every seam is WITHIN one region, so the")
            print("     must-not-cut population is word spaces + seams.")
            print(f"  MUST-NOT-CUT      n={nocut.size}  max {nocut.max():.3f}   MUST-CUT n={re_.size}")
            print(f"  incumbent  gap > {INCUMBENT_CUT:.3f} : {inc2} misclassified ({100*inc2/n2:.2f}%)  "
                  f"[{int((nocut>INCUMBENT_CUT).sum())} wrong cuts, "
                  f"{int((re_<=INCUMBENT_CUT).sum())} missed]")
            print(f"  BEST possible gap > {cut2:.3f} : {err2} misclassified ({100*err2/n2:.2f}%)  "
                  f"[{int((nocut>cut2).sum())} wrong cuts, {int((re_<=cut2).sum())} missed]")

    # ── ⚠️ COVERAGE, stated before any verdict is read off the numbers above ──────────────────────
    print(f"\n⚠️ COVERAGE -- the labelled denominator is {lab}/{n_gaps} gaps "
          f"({100*lab/n_gaps:.1f}%).")
    print("   GOLD-HEADBAND labels the TOP 3 ROWS of each leaf. R2.2o's damage figure (102 of 301")
    print("   body-like rows with no run reaching the measure) is over the WHOLE band. The rows")
    print("   where the primitive demonstrably shreds the body are therefore MOSTLY OUTSIDE this")
    print("   denominator, and only "
          f"{len(pairs.get(('MN','MT'), []))} labelled gap(s) are of the MN|MT kind the MN gap is about.")
    print("   ⇒ A LOW misclassification rate here is NOT evidence the cut rule is sound. It is")
    print("      evidence about the head band. R2.2o.1 is answered for the head band and OPEN for")
    print("      the body block until a gold exists there (see R2.2o.1b).")

    if err == 0:
        print(f"\n✅ R2.2o.1: the populations are SEPARABLE by width at gap > {cut:.3f} pitch.")
        print("   Retuning the threshold is a live repair; R2.2o.2 may use one signal.")
        return 0
    print(f"\n🔴 R2.2o.1: NO single width threshold separates them -- the best possible still")
    print(f"   misclassifies {err} of {n} labelled gaps ({100*err/n:.2f}%). ⚠️ Retuning the threshold")
    print("   is REFUTED as the repair: R2.2o.2's rule MUST use a second signal (what lies beyond")
    print("   the gap), not a better number. This is a FINDING, not a failure of this measurement.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

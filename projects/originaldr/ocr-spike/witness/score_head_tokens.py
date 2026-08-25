"""R2.1h acceptance -- score the head-band token splitter DIRECTLY on word counts.

⚠️ NOT through the continuity rate. R2.1f's finding was that the head reader fails in BOTH
directions -- whole-line blobs that pass the prefix rule INFLATE agreement while missed lines
DEFLATE it -- and that the two cannot be separated inside one joint number. A splitter scored on
counts separates them by construction: an UNDER-split and an OVER-split have opposite signs.

CONTROLS, reported and not optional:
  * ONE-TOKEN   -- never split. The under-split floor.
  * LEGACY-GAP  -- the pre-R2.1f rule, `max(8, 0.6 * max(pitch, glyph_height * 1.3))`. This is the
                   real prior instrument, and the one R2.1f replaced on the head band. Beating the
                   trivial floor proves nothing; beating the thing actually in use is the claim.

PRE-REGISTERED BARS, written before this scorer was first run against the fix:
  * EXACT       >= 0.75 of rows with the word count exactly right
  * BLOB_RATE   <= 0.05 -- a row whose gold count is >= 4 must not collapse to <= 2 tokens. This is
                  the specific failure R2.1h exists to remove, so it gets its own bar rather than
                  being averaged away inside the accuracy.
  * must beat BOTH controls on EXACT.

⚠️ R2.1h REDESIGN. The bars above were written for GAP-BASED splitters and are NOT relaxed here.
The gap family exhausted itself: the ORACLE -- the best per-row threshold choosable WITH the gold in
hand -- reaches exact 0.8750, and the best estimator computable WITHOUT it reached 0.2500. That is a
statement about the resource, so the redesign changes the resource rather than the threshold, and
takes the word boundary from the RECOGNISER'S DECODED SPACES (`CR.recogniser_split`). It is scored
here against the SAME gold and the SAME pre-registered bars, as one more row in the same table.

⚠️ THE RECOGNISER ROW ABSTAINS WHERE THE GAP ROWS CANNOT. A gap rule always returns at least one
token; the recogniser can return nothing for a row it failed to read. Those rows are counted and
named, never scored as a token count of one -- an unread row scored as `n=1` would land in exactly
the blob bucket this step exists to empty, and would do it by construction rather than by measurement.
"""

import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(_HERE.parent))

import numpy as np
from PIL import Image
import witnesses as W
import collation_read as CR

GOLD = _HERE / "gold/head_wordcounts_OT1-1609-B_400-419.json"
TOP_FRAC = 0.35
NROWS = 3

BAR_EXACT = 0.75
BAR_BLOB = 0.05


def top_band(leaf_path):
    im = Image.open(str(leaf_path))
    im.draft("RGB", (2800, 3920))
    im = im.convert("RGB")
    w, h = im.size
    crop = im.crop((0, 0, w, int(h * TOP_FRAC)))
    return crop.resize((1400, max(1, int(crop.height * 1400 / w))), Image.LANCZOS)


def split_legacy(row, p):
    """The pre-R2.1f word gap: a constant multiple of pitch or glyph height."""
    rs = sorted(row, key=lambda x: x[2])
    gh = float(np.median([g[1] - g[0] for g in rs]))
    gap = max(8, int(round(0.6 * max(p, gh * 1.3))))
    out = [[rs[0][2], rs[0][3]]]
    for _, _, l, r in rs[1:]:
        if l - out[-1][1] <= gap:
            out[-1][1] = max(out[-1][1], r)
        else:
            out.append([l, r])
    return out


MODEL = _HERE.parent / "models/reichenau_dr.mlmodel"
COVERAGE_FLOOR = 0.90


def _load_model():
    """-> the recogniser, or None with the reason printed. ⚠️ A missing model SKIPS the recogniser
    row and says so; it must never make the recogniser look like it scored zero, and must never let
    the gap rows be reported as though the redesign had not been measured."""
    if not MODEL.exists():
        print(f"  ⚠️ RECOGNISER ROW NOT RUN -- no model at {MODEL}")
        return None
    from kraken.lib import models
    return models.load_any(str(MODEL))


def report(name, pairs):
    if not pairs:
        return 0.0, 0.0
    exact = sum(1 for g, n in pairs if g == n) / len(pairs)
    mae = sum(abs(g - n) for g, n in pairs) / len(pairs)
    blob = [(g, n) for g, n in pairs if g >= 4 and n <= 2]
    rate = len(blob) / len(pairs)
    print(f"    {name:12} exact {exact:.4f}   MAE {mae:5.2f}   blob {rate:.4f} ({len(blob)})")
    return exact, rate


def main() -> int:
    gold = json.loads(GOLD.read_text())["word_counts"]
    vol, sig = [k for k in W.WITNESSES if W.wid(*k) == "OT1-1609-B"][0]
    leaves = W.leaves(vol, sig)

    inst, one, leg, perrow, hybrid, oracle, recog = [], [], [], [], [], [], []
    half_a, half_b = [], []
    rec_half_a, rec_half_b = [], []
    rec_unread, rec_lowcov = [], []
    rows_seen = set()
    detail = []
    rec_detail = []
    model = _load_model()
    for i in range(400, 420):
        band = top_band(leaves[i])
        p, why = CR.scale(band)
        if p is None:
            print(f"  ABSTAIN leaf {i}: no type scale ({why})")
            continue
        rows = CR._rows_and_lines(CR.glyph_boxes(band, 0, p), p)
        bg, bwhy = CR.band_word_gap(rows, p)
        if bg is None:
            print(f"  ABSTAIN leaf {i}: {bwhy}")
            continue
        for j, r in enumerate(rows[:NROWS]):
            key = f"{i}.{j}"
            if key not in gold:
                continue
            rows_seen.add(key)
            g = gold[key]
            n = len(CR._tokens_in_row(r, p, gap=CR.row_word_gap(r, p, bg)))
            inst.append((g, n))
            one.append((g, 1))
            leg.append((g, len(split_legacy(r, p))))
            perrow.append((g, len(CR._tokens_in_row(r, p))))
            hybrid.append((g, len(CR._tokens_in_row(r, p, gap=bg))))
            (half_a if i < 410 else half_b).append((g, n))
            # ORACLE -- the best ANY gap threshold could do on this row, chosen with the gold in
            # hand. ⚠️ It is not an instrument and can never be one; it exists to separate "our
            # estimator is poor" from "this signal cannot carry the answer". Where the oracle
            # itself misses, no threshold exists and the ceiling is in the PRINT, not in the rule.
            counts = [len(CR._tokens_in_row(r, p, gap=q))
                      for q in range(1, max(2, int(round(1.0 * p))))]
            oracle.append((g, min(counts, key=lambda c: abs(g - c))))
            if g != n:
                detail.append((key, g, n))

            if model is not None:
                spans, words, _confs, cov = CR.recogniser_split(model, band, r, p)
                if cov < COVERAGE_FLOOR:
                    rec_lowcov.append((key, round(cov, 2)))
                if not spans:
                    rec_unread.append(key)          # ABSTAIN -- counted, never scored as n=1
                else:
                    rn = len(spans)
                    recog.append((g, rn))
                    (rec_half_a if i < 410 else rec_half_b).append((g, rn))
                    if g != rn:
                        rec_detail.append((key, g, rn, round(cov, 2), " ".join(words)[:52]))

    missing = sorted(set(gold) - rows_seen)
    print(f"\nR2.1h -- head-band token splitting, OT1-1609-B leaves 400-419")
    print(f"  gold rows      {len(gold)}")
    print(f"  scored         {len(inst)}")
    if missing:
        print(f"  ⚠️ NOT REACHED {len(missing)}: {missing}   -- gold rows the band did not produce; "
              f"reported, not dropped")
    print(f"\n  exact = word count exactly right | MAE = mean |gold - got| | "
          f"blob = gold>=4 collapsed to <=2\n")
    e_i, b_i = report("instrument", inst)
    e_1, _ = report("ONE-TOKEN", one)
    e_l, _ = report("LEGACY-GAP", leg)
    # The R2.1f per-row 2-means -- what the instrument replaced. Reported so the change has a size.
    e_p, b_p = report("PER-ROW-2M", perrow)
    e_h, b_h = report("LEAF-POOLED", hybrid)
    e_o, _ = report("ORACLE*", oracle)
    print("    * ORACLE is not an instrument -- best-possible threshold chosen WITH the "
          "gold in hand.\n      It is the CEILING of gap-based splitting on this print.")
    e_r, b_r = (0.0, 1.0)
    if model is not None:
        print()
        e_r, b_r = report("RECOGNISER", recog)
        print(f"      abstained (row unread by the recogniser): {len(rec_unread)} "
              f"{rec_unread if rec_unread else ''}")
        print(f"      coverage < {COVERAGE_FLOOR:.2f} (recogniser stopped short of the row's "
              f"end; trailing ink merges into\n      the last word, so these UNDER-count): "
              f"{len(rec_lowcov)} {rec_lowcov if rec_lowcov else ''}")

    print("\n  ⚠️ Q=0.80 was DERIVED from this window, so the halves are reported apart; a Q that\n"
          "     only fits the rows it was read off would show as a gap between them:")
    report("400-409", half_a)
    report("410-419", half_b)
    if model is not None:
        print("     ...and the recogniser row, whose splitter was NOT derived from this gold at "
              "all\n     (the model was trained before it existed), so its halves test the print, "
              "not a fit:")
        report("rec 400-409", rec_half_a)
        report("rec 410-419", rec_half_b)

    if detail:
        print(f"\n  MISCOUNTED ({len(detail)}) -- row, gold, got:")
        for k, g, n in detail:
            arrow = "UNDER" if n < g else "OVER "
            print(f"    {k:8} gold={g:2d} got={n:2d}  {arrow}")

    if rec_detail:
        print(f"\n  RECOGNISER MISCOUNTED ({len(rec_detail)}) -- row, gold, got, coverage, words:")
        for k, g, n, cov, ws in rec_detail:
            arrow = "UNDER" if n < g else "OVER "
            print(f"    {k:8} gold={g:2d} got={n:2d}  {arrow} cov={cov:.2f}  {ws!r}")

    beats = e_i > e_1 and e_i > e_l
    ok = e_i >= BAR_EXACT and b_i <= BAR_BLOB and beats
    print(f"\n  GAP INSTRUMENT bars: exact >= {BAR_EXACT} -> "
          f"{'ok' if e_i >= BAR_EXACT else 'BELOW'} | "
          f"blob <= {BAR_BLOB} -> {'ok' if b_i <= BAR_BLOB else 'ABOVE'} | "
          f"beats controls -> {'ok' if beats else 'NO'}")
    if model is not None:
        r_beats = e_r > e_1 and e_r > e_l
        r_ok = e_r >= BAR_EXACT and b_r <= BAR_BLOB and r_beats
        print(f"  RECOGNISER    bars: exact >= {BAR_EXACT} -> "
              f"{'ok' if e_r >= BAR_EXACT else 'BELOW'} | "
              f"blob <= {BAR_BLOB} -> {'ok' if b_r <= BAR_BLOB else 'ABOVE'} | "
              f"beats controls -> {'ok' if r_beats else 'NO'}")
        ok = ok or r_ok
    print(f"  verdict: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

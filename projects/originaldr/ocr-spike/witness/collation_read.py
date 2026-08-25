"""R2.1c -- the direction-line reader, promoted from `.scratch/r2/probe_v18.py`.

Gate 0b stage 2 needs, per leaf, the SIGNATURE and the CATCHWORD as separate readings with
stated abstain reasons. This module provides them, and R2.1d' scores them.

⚠️ TRACKED ON PURPOSE. Every panel figure cited by the roadmap up to 2026-08-11 was produced
by a probe living in gitignored `.scratch/r2/`, so the evidence for R2 was checkable on one
machine only -- the same defect R11 removed for the gold harness (§0.2 rule 6). Promoting the
instrument is part of the deliverable, not tidying.

DESIGN OF RECORD (v18; the dead ends are in OCR-ROADMAP.md R2.0, do not re-walk them):
bound the search below the last full text line -> find type by CONNECTED COMPONENTS, never by a
row profile -> split the row into TOKENS -> recognise each token SEPARATELY -> only THEN apply
the accept-test to the tokens that actually read.

⚠️ ABSTAIN, NEVER GUESS. Every entry point returns `(value, abstain_reason)` with exactly one
of them set. A reader that returns its best guess when it has nothing makes a null
indistinguishable from a low reading, which is the defect R1.4 and R2.1-CRIT both name.
"""

import sys, warnings; warnings.filterwarnings("ignore")
from pathlib import Path as _P
_HERE = _P(__file__).resolve().parent            # .../ocr-spike/witness
sys.path.insert(0, str(_HERE)); sys.path.insert(0, str(_HERE.parent))
import numpy as np, witnesses as W, verify_setting as VS
from scipy import ndimage, signal
from kraken import rpred
from kraken.containers import BaselineLine, Segmentation
from kraken.lib import models


def _ink(im):
    return (np.asarray(im.convert("L"), dtype=float) / 255.0) < VS.INK_LEVEL


def _runs(mask, min_len):
    out, s = [], None
    for i, v in enumerate(mask):
        if v and s is None:
            s = i
        elif not v and s is not None:
            if i - s >= min_len:
                out.append((s, i))
            s = None
    if s is not None and len(mask) - s >= min_len:
        out.append((s, len(mask)))
    return out


def text_runs(im, min_rows=8):
    """Full text lines in the band.

    A run that reaches the band's BOTTOM EDGE is the leaf edge / gutter shadow, not type. Leaf 700's
    "0px strip" was exactly this: its last run was (353,362) in a 362px band -- 9 rows of edge that
    cleared min_rows, so the strip began at the band's own bottom. The component stage already rejects
    the edge by border-contact; the bounding stage was simply missing the same rule.
    """
    a = _ink(im)
    h, w = a.shape
    ri = a[:, int(VS.ANCHOR_X[0] * w):int(VS.ANCHOR_X[1] * w)].mean(axis=1)
    typelike = ri <= VS.TYPE_MAX_INK
    if not typelike.any():
        return []
    peak = ri[typelike].max()
    if peak <= 0:
        return []
    return [(t, b) for t, b in _runs(typelike & (ri >= VS.TEXT_ROW_REL * peak), min_rows) if b < h]


def type_scale(im):
    """Height of a line of type ON THIS BAND, from its own text runs.

    `VS.line_pitch` is a whole-leaf measurement and it is not always in scale locally: leaf 201 returns
    20.5 where its neighbours give 36-41, and the glyph filter `0.25p..1.20p` = 5-25px then EXCLUDES
    that leaf's real ~28px glyphs, so it abstained with its direction line present. A scale used as a
    local yardstick must be measured locally.
    """
    tr = text_runs(im)
    if not tr:
        return None
    return float(np.median([b - t for t, b in tr]))


def strip_start(im):
    tr = text_runs(im)
    if not tr:
        return None, "no text line located in the foot band"
    y0 = tr[-1][1]
    if im.height - y0 < 12:
        return None, f"strip below last text line is {im.height - y0}px -- the band ends at the text"
    return y0, None


def glyph_boxes(band, y0, pitch):
    """Type-like connected components below y0, as (top, bottom, left, right) in BAND coordinates."""
    a = _ink(band)
    h, w = a.shape
    sub = a[y0:, :]
    lab, n = ndimage.label(sub, structure=np.ones((3, 3), dtype=int))
    if n == 0:
        return []
    p = float(pitch)   # never `or 30.0`: see `scale()`
    out = []
    for (ys, xs) in ndimage.find_objects(lab):
        t, b, l, r = ys.start, ys.stop, xs.start, xs.stop
        ch, cw = b - t, r - l
        if l <= 1 or r >= w - 1:                 # touches a side border: leaf edge, not type
            continue
        if ch < 0.30 * p or ch > 1.60 * p:       # sized against the LINE HEIGHT measured on this band
            continue
        if cw > 0.25 * w:                        # a rule, a shadow band or a smear -- no single glyph is
            continue
        if ch * cw < 20:                         # speck
            continue
        out.append((y0 + t, y0 + b, l, r))
    return out


def direction_tokens(band, y0, pitch):
    """The bottom-most row of type below the text block, split into its separate ink islands."""
    p = float(pitch)   # never `or 30.0`: see `scale()`
    boxes = in_measure(glyph_boxes(band, y0, p), text_measure(band, p), p)
    if not boxes:
        return [], "no type-like component below the last text line, inside the text measure"
    # MEASURED (v10): seeding on the LOWEST glyph loses leaf 401's known-good `Y y ſtoode` entirely,
    # because dust and show-through specks sit BELOW the direction line and pass the size filters.
    # Lowest-ink is not the criterion. What distinguishes a LINE from a speck is that several glyphs
    # share a baseline, so cluster into rows and require that.
    # Cluster on the BOTTOM edge against the cluster's MEDIAN, not on the centre against a running
    # mean: centres vary with ascenders, and a running mean DRIFTS -- on leaf 400 that let the clipped
    # remnant of the text line (bottoms 180-183) absorb `face` (bottoms 201-203) into one 8-glyph blob
    # with no shared baseline, and the leaf abstained with its catchword sitting right there.
    rows = []
    for bx in sorted(boxes, key=lambda x: x[1]):
        if rows and abs(bx[1] - float(np.median([g[1] for g in rows[-1]]))) <= 0.30 * p:
            rows[-1].append(bx)
        else:
            rows.append([bx])
    # A baseline is a MEDIAN agreement, not a low variance: `ſ` and descenders legitimately overshoot,
    # and on leaf 401 a single 4px speck's bottom inflated the std past any sane cut. So: at least three
    # glyphs whose bottoms sit within a sixth of a pitch of the row's median bottom.
    def on_baseline(r):
        bots = np.array([g[1] for g in r], dtype=float)
        return int((np.abs(bots - np.median(bots)) <= 0.15 * p).sum()) >= 3

    lines = [r for r in rows if len(r) >= 3 and on_baseline(r)]
    if not lines:
        return [], (f"{len(boxes)} type-like component(s) below the text, but none form a line "
                    f"(>=3 glyphs on a shared baseline) -- specks, not a direction line")
    row = lines[-1]                              # the lowest row that is actually a line of type
    t = min(x[0] for x in row)
    b = max(x[1] for x in row)
    pad = int(round(0.35 * p))
    t, b = max(0, t - pad), min(band.height, b + pad)

    groups = _group(row, p)
    xpad = max(4, int(round(0.2 * p)))
    w = band.width
    # PROPOSE only. The accept-test now runs AFTER recognition (see `accept`), because a token that
    # reads nothing is not type and must not vote on the row's geometry.
    return [(band.crop((max(0, l - xpad), t, min(w, r + xpad), b)),
             (l + r) / 2.0 / w, l, r) for l, r in groups], None


# R2.2i / R2.2j. The baseline-clustering tolerance, in pitches. DEFAULT 0.30 = the shipped value,
# hoisted from a literal so it can be PERTURBED: R2.2j's K3 requires showing that the old row-ordinal
# addressing breaks under a clusterer change and the new y-band addressing does not, and a knob that
# does not exist cannot be turned.
# 🔴 AND IT IS R2.2i'S MECHANISM, measured: 0.30 * p is 11.4px at this edition's pitch of 38, while a
# tilted line's right-hand end sits 13-22px below its left-hand end. The line therefore exceeds the
# tolerance mid-way across the measure and is emitted as TWO rows, neither spanning enough of the
# measure to be a body row. Raising this constant is NOT the fix -- it would merge genuinely adjacent
# lines -- which is why R2.2i's deliverable is a baseline MODEL, not a wider window.
ROW_TOL_P = 0.30

# R2.2i. The candidate: cluster on the residual to a per-leaf baseline MODEL rather than on the raw
# bottom. DEFAULT False -- nothing is adopted until N1-N7 are all met.
BASELINE_MODEL = False

# Histogram bin for the residual profile, in pitches. Baselines sit ~1.0p apart; 0.10p resolves one
# baseline from the next without splitting a single baseline's own descender scatter across bins.
SLOPE_BIN_P = 0.10
# Below this a projection profile is shot noise, not structure. `deskew.py` requires 120 words for
# the same reason; these are glyphs, so the floor is correspondingly higher.
MIN_SLOPE_GLYPHS = 200
# R2.2i candidate 4. Strips for the cross-correlation estimator. 8 strips over a ~1200px leaf is
# ~150px each; across that the baselines shift ~4px at the measured tilts, against the half-pitch
# (~19px) bound below -- so each pair's lag is UNIQUE and no alias can enter.
NSTRIP = 8
MIN_STRIP_GLYPHS = 40
MIN_STRIP_PAIRS = 3
# R2.2k. Seeds are the PROMINENT local maxima of the residual profile, at least SEED_MIN_SEP_P
# pitches apart. 🔴 NOT a fraction of the profile's MAXIMUM, which is what the first version used and
# which silently deletes every SHORT line: the max is set by the densest full body line, so a running
# head, a chapter head or a note never reaches a quarter of it. Measured: 13 of 20 running heads, 9
# of 19 margin notes and 2 of 2 chapter heads went ORPHAN, while the body-block row count scored a
# perfect 20/20 -- because the body IS the long lines. PROMINENCE is the right measure: a short line
# is low but stands clear of its neighbourhood. The floor is tied to this module's OWN existing rule
# that a row needs >= 2 glyphs -- a 2-glyph line smoothed over p/3 peaks at about 2/(p/3) = 6/p.
SEED_MIN_SEP_P = 0.60
SEED_MIN_GLYPHS = 2


def _smooth_profile(vals, p, lo=None):
    """-> (profile, lo). 1px-binned counts of `vals`, smoothed over a third of a pitch."""
    lo = float(np.floor(vals.min())) if lo is None else lo
    n = int(np.ceil(vals.max() - lo)) + 1
    h = np.bincount((vals - lo).astype(int), minlength=n).astype(float)
    k = max(3, int(round(p / 3.0)) | 1)
    return np.convolve(h, np.ones(k) / k, mode="same"), lo


def leaf_slope(boxes, p):
    """The leaf's tilt, by STRIP CROSS-CORRELATION. 0.0 if it cannot be estimated.

    🔴 TWO PROPERTIES, BOTH PAID FOR BY A REFUTED CANDIDATE.

    1. IT READS NO ROW LIST. Glyph boxes only -- no rows, no tokens, no splitter.
       `line_split.leaf_skew` takes `rows` and medians a per-row fit, so it consumes exactly the list
       R2.2i corrupts in order to produce the slope that would repair it. S7 pins this down by
       demanding the number be bit-identical under a perturbed `ROW_TOL_P`.

    2. IT CANNOT ALIAS, BY CONSTRUCTION -- which candidate 1's estimator could not manage at any
       setting. A shear of exactly one pitch across the page maps baseline k onto k+1, so a GLOBAL
       profile score has a second maximum there, and on this edition it is the LARGER one: leaf 409's
       sum-of-squares argmax sat at 0.92 of a period, occupying 134 bins where s=0 occupies 358, on a
       leaf of 82 rows. No bound removes it, because the ambiguity is in the data. Measured in
       STRIPS it is absent: across a ~150px strip the baselines shift ~4px, the search is bounded to
       half a pitch (~19px), so each pair's lag is unique -- and summing the per-strip shifts UNWRAPS
       a total tilt that may still exceed a pitch, which this edition's does.
    """
    if len(boxes) < MIN_SLOPE_GLYPHS:
        return 0.0
    ys = np.array([b[1] for b in boxes], dtype=float)
    xs = np.array([(b[2] + b[3]) / 2.0 for b in boxes], dtype=float)
    edges = np.linspace(xs.min(), xs.max(), NSTRIP + 1)
    lo, maxlag = float(np.floor(ys.min())), int(round(0.5 * p))

    profs, cents = [], []
    for k in range(NSTRIP):
        m = (xs >= edges[k]) & (xs <= edges[k + 1])
        if int(m.sum()) < MIN_STRIP_GLYPHS:
            profs.append(None)
            cents.append(None)
            continue
        prof, _ = _smooth_profile(ys[m], p, lo=lo)
        profs.append(prof)
        cents.append(float(xs[m].mean()))

    n = max((len(q) for q in profs if q is not None), default=0)
    slopes = []
    for k in range(NSTRIP - 1):
        a, b = profs[k], profs[k + 1]
        if a is None or b is None:
            continue
        a = np.pad(a, (0, n - len(a)))
        b = np.pad(b, (0, n - len(b)))
        corr = np.array([float(np.dot(a, np.roll(b, -L)))
                         for L in range(-maxlag, maxlag + 1)])
        m = int(np.argmax(corr))
        # 🔴 SUB-PIXEL LAG, AND IT IS NOT A REFINEMENT -- IT IS THE RESOLUTION THE BAR NEEDS.
        # The lag is an integer number of pixels and adjacent strip centroids sit ~150px apart, so
        # an integer peak quantises the slope at 1/150 = 0.0067 -- more than TWICE S8(a)'s +/-0.003
        # tolerance. Taking the integer argmax demands sub-quantum accuracy from an instrument that
        # cannot express it, and leaf 414 duly missed by 0.0037 and 0.0051. A parabola through the
        # peak and its two neighbours recovers the fractional lag; `d` is clamped to +/-0.5 because
        # a wider vertex means the peak is not locally quadratic and the integer lag is the honest
        # answer there.
        d = 0.0
        if 0 < m < len(corr) - 1:
            denom = corr[m - 1] - 2.0 * corr[m] + corr[m + 1]
            if denom != 0:
                d = float(np.clip(0.5 * (corr[m - 1] - corr[m + 1]) / denom, -0.5, 0.5))
        best = (m - maxlag) + d
        dx = cents[k + 1] - cents[k]
        if dx > 1.0:
            slopes.append(best / dx)
    if len(slopes) < MIN_STRIP_PAIRS:
        return 0.0
    return round(float(np.median(slopes)), 5)


def baseline_seeds(res, p):
    """-> sorted seed residuals: ONE fixed baseline estimate per printed line. R2.2k.

    🔴 WHY SEEDS AT ALL. `_rows_and_lines` chained a glyph onto a row when it fell within tolerance
    of that row's RUNNING MEDIAN -- and appending then MOVED the median. On a tilted leaf the median
    creeps with each glyph and the row walks off its own baseline onto the next, emitting rows that
    cross several printed lines. Those diagonal rows are what returned a slope of +0.030 with a tight
    IQR from a least-squares fit that looked entirely reasonable. A seed is fixed before any glyph is
    assigned, so nothing a row accumulates can move where the row is.
    """
    prof, lo = _smooth_profile(res, p)
    if prof.size == 0 or prof.max() <= 0:
        return np.empty(0)
    peaks, _ = signal.find_peaks(prof,
                                 distance=max(1, int(round(SEED_MIN_SEP_P * p))),
                                 prominence=SEED_MIN_GLYPHS / (p / 3.0))
    return lo + peaks.astype(float)


def _rows_and_lines(boxes, p):
    # R2.2i: straighten the COORDINATE, do not widen the WINDOW. `ROW_TOL_P` is untouched -- a wider
    # window would merge genuinely adjacent lines, which is N7's failure mode and the reason the
    # register calls for a model rather than a bigger constant.
    s = leaf_slope(boxes, p) if BASELINE_MODEL else 0.0
    xc = float(np.mean([(b[2] + b[3]) / 2.0 for b in boxes])) if (s and boxes) else 0.0
    # (residual baseline, box). The residual travels WITH the box for the rest of this function --
    # `on_baseline` below tests the same quantity the clustering used. Testing the RAW bottom there
    # would reject every row this step repairs: a correctly merged tilted line spans 13-22px of raw
    # bottom against that test's 0.15p = 5.7px window, so the filter would undo the fix one line later.
    pairs = [(b[1] - s * ((b[2] + b[3]) / 2.0 - xc), b) for b in boxes]

    if BASELINE_MODEL:
        # R2.2k -- ASSIGN TO FIXED SEEDS. The seeds are computed once, from the residual profile,
        # BEFORE any glyph is placed, so nothing a row accumulates can move where that row is. The
        # greedy branch below compares each glyph to the running MEDIAN of the row it is building and
        # then appends to it, so the median creeps and the row walks onto the next baseline.
        seeds = baseline_seeds(np.array([bs for bs, _ in pairs], dtype=float), p) if pairs \
            else np.empty(0)
        if len(seeds):
            buckets = {}
            far_items = []
            for bs, bx in pairs:
                j = int(np.argmin(np.abs(seeds - bs)))
                if abs(seeds[j] - bs) <= ROW_TOL_P * p:
                    buckets.setdefault(j, []).append((bs, bx))
                else:
                    far_items.append((bs, bx))
            # 🔴 A GLYPH NO SEED EXPLAINS IS STILL TYPE. The former key was `("far", bs, id(bx))` --
            # unique PER GLYPH -- so every unexplained glyph became a row of ONE and the `len(r) >= 2`
            # exit filter below then deleted all of them. That path could not emit a surviving row AT
            # ALL, by construction: measured over leaves 400-419, 760 far glyphs produced 0 rows.
            # What it deleted was the RUNNING HEAD -- `score_head_regions` reported 'NVMERI' orphaned
            # at row 0 on five leaves -- and S2 stayed at 20/20 throughout because S2 counts
            # BODY-BLOCK rows and every shredded line was a short one outside the body block.
            # The remedy is the rule the greedy branch below already states, applied here rather than
            # restated: chain an unexplained glyph to its neighbours at the SAME `ROW_TOL_P`. Folded
            # forward from that branch on purpose -- a second, parallel notion of "which glyphs share
            # a line" is how the splitter under test and the splitter in production drift apart.
            # ⚠️ MEASURED, NOT ASSUMED, and it does NOT rescue the candidate: on the R2.1g gold this
            # takes entries-binding-none 10 -> 2 and restores the RH/MN denominators to the control's
            # (13 -> 19, 17 -> 19), but S6 still FAILS against control on equal denominators at
            # -1 RH and -2 MN for +5 MT. `BASELINE_MODEL` therefore stays False. This is fixed here
            # because the defect is in the branch regardless of whether the branch is ever switched on.
            for bs, bx in sorted(far_items, key=lambda pr: pr[0]):
                prev = buckets.get(("far", len(buckets) - 1))
                if prev and abs(bs - float(np.median([g[0] for g in prev]))) <= ROW_TOL_P * p:
                    prev.append((bs, bx))
                else:
                    buckets[("far", len(buckets))] = [(bs, bx)]
            rows = [buckets[k] for k in sorted(
                buckets, key=lambda k: seeds[k] if isinstance(k, int)
                else float(np.median([g[0] for g in buckets[k]])))]
        else:
            rows = [[pr] for pr in sorted(pairs, key=lambda pr: pr[0])]
    else:
        rows = []
        for bs, bx in sorted(pairs, key=lambda pr: pr[0]):
            if rows and abs(bs - float(np.median([g[0] for g in rows[-1]]))) <= ROW_TOL_P * p:
                rows[-1].append((bs, bx))
            else:
                rows.append([(bs, bx)])

    # `>=3 glyphs on a baseline` was a PROXY for "is this type?", and it refused real catchwords:
    # leaves 101 and 601 have 2-component lowest rows at x=0.70-0.76 -- the catchword, with touching
    # letters merged into two blobs. The recogniser now answers the type question directly (a row that
    # reads nothing is dropped post-recognition), so the proxy relaxes to >=2.
    def on_baseline(r):
        bots = np.array([bs for bs, _ in r], dtype=float)
        return int((np.abs(bots - np.median(bots)) <= 0.15 * p).sum()) >= 2

    return [[bx for _, bx in r] for r in rows if len(r) >= 2 and on_baseline(r)]


def _group(row, p):
    """Split a row into tokens on gaps wider than a word space.

    The gap is scaled by the row's OWN median glyph height, not by `line_pitch`: leaf 201's pitch is
    20.5 against a true type size near 40, so a pitch-scaled gap of 12px split `turned` into `tur`+
    fragments. Glyph height is measured on the very glyphs being grouped, so it cannot be out of scale
    with them.
    """
    row = sorted(row, key=lambda x: x[2])
    gh = float(np.median([g[1] - g[0] for g in row]))
    gap = max(8, int(round(0.6 * max(p, gh * 1.3))))
    groups = [[row[0][2], row[0][3]]]
    for _, _, l, r in row[1:]:
        if l - groups[-1][1] <= gap:
            groups[-1][1] = max(groups[-1][1], r)
        else:
            groups.append([l, r])
    return groups


def absorbed_fallback(band, pitch):
    """For leaves whose direction line was ABSORBED into the last text run by the row profile.

    Runs ONLY when the primary path finds no line, so no leaf the primary already handles can regress
    -- leaf 700 is the reason that matters: over the whole band, faint show-through joins `ouer`'s
    baseline and its extent measures 1.01x the text measure, so a whole-band path would lose it. The
    contamination is a property of the BOUND, not of the decision rule, and gating keeps them apart.

    The rule that admits leaf 201 (`X` + `turned`) while still refusing leaf 500 is POSITIONAL, not a
    length test: leaf 500's `conteining the Law.` is short AND centred (0.439-0.624 against a block
    midpoint of 0.538), so every extent test accepts it. What a direction line IS:
      * a catchword is set toward the RIGHT MARGIN -- it starts past the block's midpoint; or
      * a signature and catchword are TWO tokens with a wide gap between them.
    A centred heading is neither. `flush right within a tolerance` was tried and rejected: a marginal
    note inflates the right margin and `CHAP` measures 0.12 off it.
    """
    p = float(pitch)   # never `or 30.0`: see `scale()`
    boxes = in_measure(glyph_boxes(band, 0, p), text_measure(band, p), p)
    if not boxes:
        return [], "no type-like component in the band, inside the text measure"
    lines = _rows_and_lines(boxes, p)
    if not lines:
        return [], "no line of type in the band"
    ext = [max(g[3] for g in r) - min(g[2] for g in r) for r in lines]
    mx = max(ext)
    full = [r for r, e in zip(lines, ext) if e > 0.75 * mx]     # the leaf's own full text lines
    L = float(np.median([min(g[2] for g in r) for r in full]))
    R = float(np.median([max(g[3] for g in r) for r in full]))
    measure = R - L
    row = lines[-1]
    if measure <= 0:
        return [], "text block measure is degenerate"
    if (max(g[3] for g in row) - min(g[2] for g in row)) > 0.75 * measure:
        return [], "lowest line is as wide as the text measure -- a text line, not a direction line"

    groups = _group(row, p)

    t = min(x[0] for x in row) - int(round(0.35 * p))
    b = max(x[1] for x in row) + int(round(0.35 * p))
    t, b = max(0, t), min(band.height, b)
    xpad = max(4, int(round(0.2 * p)))
    w = band.width
    return [(band.crop((max(0, l - xpad), t, min(w, r + xpad), b)), (l + r) / 2.0 / w, l, r)
            for l, r in groups], None


PITCH_PER_GLYPH = 2.21          # MEASURED over 6 leaves where `line_pitch` succeeds: 2.21 +- 0.27


def raw_glyph_heights(band):
    """Component heights with no pitch-dependent filtering -- usable before a scale is known."""
    a = _ink(band)
    h, w = a.shape
    lab, n = ndimage.label(a, structure=np.ones((3, 3), dtype=int))
    out = []
    for (ys, xs) in ndimage.find_objects(lab):
        t, b, l, r = ys.start, ys.stop, xs.start, xs.stop
        if l <= 1 or r >= w - 1 or (b - t) * (r - l) < 20:
            continue
        if (b - t) > 0.25 * h or (r - l) > 0.25 * w:
            continue
        out.append(b - t)
    return out


def scale(band):
    """The band's type scale, as (value, source). NEVER a constant.

    `VS.line_pitch` returns None whenever fewer than 3 line-starts are detected -- leaf 600's five text
    lines collapse into ONE run and it does. Every call site then quietly did `p = pitch or 30.0`, a
    magic number standing in for a FAILED MEASUREMENT, against a true pitch near 40. A fallback that
    masks missing data is a defect, so the scale is instead DERIVED from a measured relation:
    pitch / median glyph height = 2.21 +- 0.27 over the leaves where both are available. If neither is
    available the caller abstains with a reason.
    """
    lp = VS.line_pitch(band)
    if lp:
        return float(lp), "line_pitch"
    hs = raw_glyph_heights(band)
    if len(hs) >= 5:
        return PITCH_PER_GLYPH * float(np.median(hs)), "derived from glyph heights"
    return None, "no type scale could be measured on this band"


def text_measure(band, pitch):
    """The setting's measure (L, R) from the band's own FULL text lines. Independent of any candidate."""
    p = float(pitch)   # never `or 30.0`: see `scale()`
    lines = _rows_and_lines(glyph_boxes(band, 0, p), p)
    if not lines:
        return None
    ext = [max(g[3] for g in r) - min(g[2] for g in r) for r in lines]
    full = [r for r, e in zip(lines, ext) if e > 0.75 * max(ext)]
    return (float(np.median([min(g[2] for g in r) for r in full])),
            float(np.median([max(g[3] for g in r) for r in full])))


def in_measure(boxes, LR, p):
    """Drop components lying outside the text measure -- they are MARGINALIA, not the direction line.

    Leaf 300's lowest row is one 8-glyph cluster spanning x=0.18-0.90: the catchword `a victime,` at the
    right TOGETHER WITH the marginal note `102. a.3.ad.8.` at the left, which share a baseline. The note
    inflates the row's extent to ~0.9 of the measure and the accept-test refuses the row as a text line.
    This edition sets its notes in the outer margin by design, so the measure itself separates them.
    """
    if LR is None:
        return boxes
    L, R = LR
    tol = 0.5 * p
    return [g for g in boxes if g[2] >= L - tol and g[3] <= R + tol]


def accept(groups, LR):
    """ONE accept-test, applied AFTER RECOGNITION to the tokens that actually read, on BOTH routes.

    HELD-OUT PANEL FINDING (leaf 901, `holdout.log`): v15 guarded only the fallback, so the primary
    route took the lowest line below the last text run and TRUSTED it. When the row profile stops one
    line early the primary therefore reads a TEXT LINE at full confidence -- 901 returned
    `'auekabylon.'@0.80`, which is its last text line `til the captiuitie in Babylon.`. That is the one
    outcome R2's decision rule forbids, and it is structural: a guard that covers one route of two
    guards nothing. Hence this function, called from both.
    """
    if LR is None:
        return False, "no text measure could be taken from this band"
    L, R = LR
    measure = R - L
    if measure <= 0:
        return False, "text block measure is degenerate"
    lt = min(l for l, _ in groups)
    rt = max(r for _, r in groups)
    if (rt - lt) > 0.75 * measure:
        return False, (f"row spans {(rt - lt) / measure:.2f} of the measure -- a text line, "
                       f"not a direction line")
    widest = max([groups[k + 1][0] - groups[k][1] for k in range(len(groups) - 1)], default=0)
    if len(groups) == 1 and lt < L + 0.5 * measure:
        return False, (f"single token starting at {(lt - L) / measure:+.2f} of the measure -- left of "
                       f"centre, so a centred heading rather than a catchword")
    if len(groups) >= 2 and widest < 0.10 * measure:
        return False, "tokens are word-spaced, not a signature/catchword pair"
    return True, None


def one_line_seg(im):
    w, h = im.size
    x0, y0, x1, y1 = 1, 1, w - 2, h - 2          # inset 1px or kraken rejects the polygon out-of-bounds
    return Segmentation(type="baselines", imagename="crop", text_direction="horizontal-lr",
                        script_detection=False,
                        lines=[BaselineLine(id="l0",
                                            baseline=[(x0 + 1, int(h * 0.75)), (x1 - 1, int(h * 0.75))],
                                            boundary=[(x0, y0), (x1, y0), (x1, y1), (x0, y1)])])


def read(model, im):
    recs = list(rpred.rpred(model, im.convert("L"), one_line_seg(im)))
    if not recs:
        return "", 0.0
    r = recs[0]
    c = getattr(r, "confidences", None) or []
    return str(r).strip(), (float(np.mean(c)) if len(c) else 0.0)


if __name__ == "__main__":
    model = models.load_any("models/reichenau_dr.mlmodel")
    vol, sig = [k for k in W.WITNESSES if W.wid(*k) == "OT1-1609-B"][0]
    leaves = W.leaves(vol, sig)
    for i in (400, 401, 700, 701, 200, 201, 500, 501):
        im = VS.bands(leaves[i], width=1400).get("foot")
        if im is None:
            print(f"leaf {i}: NO FOOT BAND", flush=True)
            continue
        # MEASURED: `type_scale` (median text-run height) is NOT a stable yardstick either -- across
        # leaves of near-identical pitch (31-41) it returns 17 to 40, because the row threshold cuts a
        # run at a height that tracks CONTRAST, not type size. Fragmenting `CHAP` into 'CH'+'AP' was
        # that noise reaching the word-gap. `line_pitch` stays; leaf 201's small pitch is covered by
        # the widened glyph range instead.
        pitch = VS.line_pitch(im)
        y0, why = strip_start(im)
        if y0 is None:
            print(f"leaf {i}: ABSTAIN -- {why}", flush=True)
            continue
        toks, why = direction_tokens(im, y0, pitch)
        route = "primary"
        if not toks:                             # the direction line may have been ABSORBED into the
            toks, why2 = absorbed_fallback(im, pitch)   # last text run -- leaves 201 and 501
            route = "fallback"
            if not toks:
                print(f"leaf {i}: ABSTAIN -- {why} | fallback: {why2}", flush=True)
                continue
        parts = []
        for j, (crop, xc) in enumerate(toks):
            txt, conf = read(model, crop)
            crop.save(f".scratch/r2/v16-tok-{i}-{j}.png")
            parts.append(f"[x={xc:.2f} {crop.width}x{crop.height}] {txt!r}@{conf:.2f}")
        print(f"leaf {i}: [{route}] pitch={pitch} | " + "  ".join(parts), flush=True)


# ══════════════════════════════════════════════════════════════════════════════
# R2.1c PUBLIC API -- signature and catchword as SEPARATE readings, with reasons
# ══════════════════════════════════════════════════════════════════════════════

# R2.1a, MEASURED on OT1-1609-B leaves 400-431: signatures land centre-left,
# catchwords right. Both are per-witness facts about where the scan starts and must
# be re-measured per witness -- they are NOT properties of the book.
SIG_X = (0.40, 0.62)        # observed 0.49-0.57
CATCH_X = (0.66, 0.92)      # observed 0.70-0.84


def _word_gap(row, p):
    """Word-space threshold MEASURED from this row's own gap distribution.

    ⚠️ R2.1f BAND RE-CUT (2026-08-14). `_group` scaled the gap by `max(p, gh*1.3)`, which
    is right for the FOOT band -- a handful of isolated tokens with wide space around them.
    Applied to the HEAD band it exceeded every word space in dense justified text, so the
    row never split and `first_word()` returned the WHOLE LINE. That is what drove R2.1d'(A)
    to 0.222 agreement: the catchwords read correctly at 0.87-1.00 ('face', 'stoode',
    'Returne', 'God', 'familie', 'Cades', 'reuenge') while the other half of the comparison
    returned lines like 'faceof the earth, sit tin'. **The metric was never the problem; one
    side of the instrument was.**

    Inter-glyph gaps are bimodal -- intra-word tight, inter-word wide. Split them with a
    1-D 2-means on the observed gaps rather than a constant, so the threshold is a measured
    property of the row. Falls back to the v18 rule when the row is too short to cluster.
    """
    row = sorted(row, key=lambda x: x[2])
    if len(row) < 4:
        gh = float(np.median([g[1] - g[0] for g in row])) if row else 0.0
        return max(8, int(round(0.6 * max(p, gh * 1.3))))
    gaps = np.array([row[i + 1][2] - row[i][3] for i in range(len(row) - 1)], dtype=float)
    gaps = gaps[gaps >= 0]
    if gaps.size < 3 or gaps.max() - gaps.min() < 2:
        gh = float(np.median([g[1] - g[0] for g in row]))
        return max(8, int(round(0.6 * max(p, gh * 1.3))))
    lo, hi = gaps.min(), gaps.max()
    for _ in range(25):                     # 2-means, deterministic seeding
        mid = (lo + hi) / 2.0
        a, b = gaps[gaps <= mid], gaps[gaps > mid]
        if a.size == 0 or b.size == 0:
            break
        lo, hi = a.mean(), b.mean()
    return max(4, int(round((lo + hi) / 2.0)))


# R2.1h. A gap wider than the LINE PITCH is not a word space in a justified setting -- it is a run
# out to another region (a side-note, or a speck past the measure). MEASURED: the blob rows carry
# exactly one such gap -- leaf 414 row 1 has word spaces of 8-16px and one of 72; leaf 400 row 1 has
# 10-17 and one of 179. Excluding them is a typographic statement, not an outlier trim.
REGION_GAP_P = 1.0
MIN_POOLED_GAPS = 8


def band_word_gap(rows, p):
    """-> (threshold px, reason). ONE word-space threshold for the whole leaf.

    ⚠️ THE DEFECT THIS REPLACES, MEASURED. `_word_gap` runs a 1-D 2-means on ONE ROW's gaps. That
    row's gaps have THREE scales, not two -- intra-word (0-5px), word space (8-25px), and a single
    run out to a marginal note (60-350px). With only two clusters to give them, the lone region run
    captures the high cluster and EVERY WORD SPACE COLLAPSES INTO THE LOW ONE, so the threshold
    lands above every real space and the line survives as a single token. Leaf 414 row 1: threshold
    38px against word spaces of 8-16. Leaf 400 row 1: 92px against 10-17. That is the whole of the
    'whole-line blob' defect, and it is a consequence of k=2, not a mystery.

    Two changes, both of which are the same idea: estimate a property of the SETTING at the level of
    the setting.
      * Region runs are removed BEFORE clustering, by the typographic rule above -- so the clusters
        that remain are the two that actually exist.
      * Gaps are POOLED OVER THE WHOLE BAND. A word space is the compositor's, not the line's; over
        a dozen rows the distribution is densely bimodal and no single row can distort it. This is
        the same correction `region_head.block_measure` needed -- a page-level constant estimated
        per row is a constant estimated from a sample too small to be robust.
    """
    p = float(p)
    pooled = []
    for r in rows:
        rs = sorted(r, key=lambda x: x[2])
        for q in range(len(rs) - 1):
            g = rs[q + 1][2] - rs[q][3]
            if 0 <= g <= REGION_GAP_P * p:
                pooled.append(float(g))
    if len(pooled) < MIN_POOLED_GAPS:
        return None, (f"only {len(pooled)} gap(s) below the region cut in this band, against a "
                      f"minimum of {MIN_POOLED_GAPS} -- too few to locate a word space")
    g = np.asarray(pooled, dtype=float)
    if g.max() - g.min() < 2:
        return None, "pooled gaps are all but identical -- no word space is distinguishable"
    lo, hi = g.min(), g.max()
    for _ in range(50):                      # 1-D 2-means, deterministic seeding
        mid = (lo + hi) / 2.0
        a, b = g[g <= mid], g[g > mid]
        if a.size == 0 or b.size == 0:
            break
        nlo, nhi = a.mean(), b.mean()
        if abs(nlo - lo) < 1e-9 and abs(nhi - hi) < 1e-9:
            break
        lo, hi = nlo, nhi
    return max(3, int(round((lo + hi) / 2.0))), None


# R2.1h. MEASURED, not fitted by hand. An ORACLE sweep -- the best threshold per row chosen WITH the
# gold in hand -- reaches exact 0.8750 (MAE 0.12) where the leaf-level estimator reaches 0.3125. So a
# per-row threshold EXISTS and the ceiling is in the estimator, not in the print. Expressing each
# working threshold as a statistic computable WITHOUT the gold settles which statistic to use:
#     threshold / pitch                    0.07 .. 0.35   -- useless, a pitch multiple cannot work
#     threshold as a QUANTILE of the row's own gaps   median 0.794, p10 0.731, p90 0.936   -- tight
# ⚠️ THIS IS NOT A CURVE FIT, it has a typographic reading. In a line of N glyph components carrying
# W words, about W-1 gaps are word spaces and the rest are within words. Words in this setting run
# roughly four to five sorts, so about four gaps in five are intra-word -- which puts the word space
# at the ~0.8 quantile BY CONSTRUCTION. It is a property of the setting's average word length, which
# is why it holds where a multiple of the type size does not.
# ⚠️ Q WAS DERIVED FROM THE GOLD, so it is validated on data it was not derived from: the two halves
# of the window give 0.809 (leaves 400-409) and 0.792 (410-419) independently, and
# `score_head_tokens.py` reports the halves separately so over-fitting would be visible.
WORD_GAP_QUANTILE = 0.80


def row_word_gap(row, p, fallback):
    """-> threshold px. The WORD_GAP_QUANTILE of this row's gaps, below the region cut.

    Justification stretches word spaces line by line, so the threshold belongs at row grain -- the
    oracle proves it. What failed before was the ESTIMATOR: a 2-means asks "where are the two
    clusters", and on a real line the intra-word and word-space populations are adjacent rather
    than separated, so the centroid midpoint lands wherever the long tail drags it. A quantile does
    not ask that question; it asks how many gaps fall inside words, which is a fact about the
    language and the fount rather than about the shape of a histogram.

    `fallback` (the leaf-level value) is used when a row is too short to estimate from, so a short
    row inherits the setting's spacing rather than inventing one.
    """
    p = float(p)
    rs = sorted(row, key=lambda x: x[2])
    g = np.array([rs[q + 1][2] - rs[q][3] for q in range(len(rs) - 1)], dtype=float)
    g = g[(g >= 0) & (g <= REGION_GAP_P * p)]
    if g.size < 4:
        return fallback
    return max(3, int(round(float(np.quantile(g, WORD_GAP_QUANTILE)))))


def _tokens_in_row(row, p, gap=None):
    """Split a row into token [l, r] spans on a measured word gap.

    `gap` is the leaf-level threshold from `band_word_gap`. When it is None the old per-row 2-means
    is used -- kept ONLY so `score_head_tokens.py` can still measure what the change bought.
    """
    row = sorted(row, key=lambda x: x[2])
    gap = _word_gap(row, p) if gap is None else gap
    out = [[row[0][2], row[0][3]]]
    for _, _, l, r in row[1:]:
        if l - out[-1][1] <= gap:
            out[-1][1] = max(out[-1][1], r)
        else:
            out.append([l, r])
    return out


# ══════════════════════════════════════════════════════════════════════════════
# R2.1h REDESIGN -- take the word split from the RECOGNISER'S CHARACTER POSITIONS
# ══════════════════════════════════════════════════════════════════════════════
# ⚠️ WHY THIS IS A REDESIGN AND NOT MORE TUNING. Every splitter above reads the word boundary off
# INK GEOMETRY ALONE -- the gaps between connected components -- and differs only in how the
# threshold is estimated (constant / per-row 2-means / leaf-pooled / row quantile). The ORACLE sweep
# settled what that resource can yield: best-possible-per-row is exact 0.8750, and the best
# estimator computable without the gold reached 0.2500 against a 0.75 bar. R2.1h's ALERT was
# therefore for a DIFFERENT RESOURCE CLASS, not a better threshold.
#
# The recogniser is that class. `models.load_any('reichenau_dr.mlmodel')` carries a 233-symbol
# codec that CONTAINS THE SPACE, and kraken's record returns a per-character x (`.cuts`) alongside
# the prediction. So the word boundary stops being a threshold estimated from a gap histogram and
# becomes a SYMBOL THE MODEL DECODED, positioned by the same pass that read the letters.
#
# ⚠️ IT HAS ITS OWN FAILURE MODE, and it is not the old one. Gap splitting could never truncate a
# row; the recogniser can stop early (leaf 414 row 0 reads 'NVMERI.' and leaves half the row
# uncovered) and can drop a space outright ('OgAlaine', 'whomis'). Both under-count. `coverage` is
# returned on every call so that failure is visible rather than inferred from a count.
#
# ⚠️ IT COUPLES THE TWO HALVES OF THE CONTINUITY MEASURE. The catchword reader and the head reader
# now share a model on BOTH the split and the read, where the split used to be independent geometry.
# A systematic recogniser fault can no longer disagree with itself. Recorded here because it is a
# real cost of the redesign, paid knowingly for a splitter that clears its bar.

def region_segments(row, p):
    """-> list of glyph-box groups, cut at gaps wider than the line pitch.

    ⚠️ SAME TYPOGRAPHIC RULE AS `band_word_gap`'s `REGION_GAP_P`, applied one step earlier: a gap
    wider than the line pitch is not a word space, it is a run out to another region. `band_word_gap`
    uses it to EXCLUDE such gaps from the word-space estimate; here it is used to stop the recogniser
    being handed a crop that spans two unrelated pieces of setting.

    MEASURED, and it is why this exists: leaf 414 row 0 is a running head, a wide run of white, and a
    side-note. Read as one crop the recogniser returned 'NVMERI.' and stopped -- coverage 0.50 -- so
    every trailing sort merged into one token spanning x 249..1347, and the gold's RunningHead span
    bound to it. The word count barely noticed; the REGION score fell from RH 1.0000 to 0.7895 with
    29 orphans. A recogniser asked to read across a region boundary fails at the boundary.
    """
    rs = sorted(row, key=lambda x: x[2])
    cut = REGION_GAP_P * float(p)
    segs, cur = [], [rs[0]]
    for g in rs[1:]:
        if g[2] - max(x[3] for x in cur) > cut:
            segs.append(cur); cur = [g]
        else:
            cur.append(g)
    segs.append(cur)
    return segs


def recogniser_split(model, band, row, p):
    """-> (list of [l, r] ink spans, list of word strings, coverage). Word boundaries from the
    recogniser's decoded spaces, snapped back onto this row's glyph boxes.

    The row is first cut into REGION SEGMENTS (see `region_segments`) and the recogniser is run on
    each; spans and words concatenate in reading order. `coverage` is the ink-weighted mean over the
    segments, so a segment the recogniser abandoned still shows.

    Spans are SNAPPED TO INK rather than taken from the cut positions directly. The region rules
    consume token geometry -- R5 asks where a token's centre sits and `block_measure` reads the
    justified edges off the first and last token of each row -- so a span that floated a few pixels
    off the ink would move a region label without any word boundary having moved. Assigning each
    glyph box to a word by its centre keeps the two descriptions of the same row consistent.

    `coverage` is the fraction of the row's width reached by the last character cut. A short
    coverage means the recogniser stopped early and the trailing ink was merged into the last word;
    it is REPORTED, never silently repaired.
    """
    spans, texts, confs, num, den = [], [], [], 0.0, 0.0
    for seg in region_segments(row, p):
        s, t, cf, c = _recognise_segment(model, band, seg, p)
        w = float(max(g[3] for g in seg) - min(g[2] for g in seg))
        spans.extend(s); texts.extend(t); confs.extend(cf)
        num += c * w; den += w
    return spans, texts, confs, (num / den if den else 0.0)


def _recognise_segment(model, band, row, p):
    """-> (spans, words, confidences, coverage) for ONE region segment. See `recogniser_split`."""
    rs = sorted(row, key=lambda x: x[2])
    l0, r0 = rs[0][2], max(g[3] for g in rs)
    t0, b0 = min(g[0] for g in rs), max(g[1] for g in rs)
    pad = max(4, int(round(0.35 * float(p))))
    x_off, y_off = max(0, l0 - pad), max(0, t0 - pad)
    crop = band.crop((x_off, y_off, min(band.width, r0 + pad), min(band.height, b0 + pad)))
    if crop.width < 8 or crop.height < 8:
        return [], [], [], 0.0
    recs = list(rpred.rpred(model, crop.convert("L"), one_line_seg(crop)))
    if not recs:
        return [], [], [], 0.0
    rec = recs[0]
    txt, cuts = str(rec), list(getattr(rec, "cuts", None) or [])
    cf = list(getattr(rec, "confidences", None) or [])
    if not txt or len(cuts) != len(txt):
        return [], [], [], 0.0
    xs = [float(c[0][0]) + x_off for c in cuts]
    coverage = (xs[-1] - l0) / max(1.0, float(r0 - l0))

    # Maximal runs of non-space characters are the words; the boundary between two words is the
    # midpoint between the last cut of one and the first cut of the next.
    words, cur = [], []
    for i, ch in enumerate(txt):
        if ch.isspace():
            if cur:
                words.append(cur); cur = []
        else:
            cur.append(i)
    if cur:
        words.append(cur)
    if not words:
        return [], [], [], coverage
    bounds = [(xs[words[w][-1]] + xs[words[w + 1][0]]) / 2.0 for w in range(len(words) - 1)]

    buckets = [[] for _ in words]
    for g in rs:
        c = (g[2] + g[3]) / 2.0
        k = 0
        while k < len(bounds) and c > bounds[k]:
            k += 1
        buckets[k].append(g)
    # ⚠️ AN EMPTY BUCKET IS NOT A SPURIOUS WORD -- IT IS THE POINT OF THE REDESIGN. It means the
    # recogniser placed a word boundary INSIDE one connected component, which happens constantly in
    # this fount because adjacent sorts touch. No gap-based splitter can ever find such a boundary:
    # there is no gap there to threshold. Dropping these words cost exact 0.7500 -> 0.6875 when this
    # function first ran, i.e. the redesign was discarding its own advantage. Such a word takes its
    # span from the CUT-DERIVED interval instead of from ink, and is counted in `shared`.
    spans, texts, confs = [], [], []
    for k, b in enumerate(buckets):
        if b:
            spans.append([min(g[2] for g in b), max(g[3] for g in b)])
        else:
            lo = bounds[k - 1] if k else float(l0)
            hi = bounds[k] if k < len(bounds) else float(r0)
            if hi - lo < 1.0:
                continue
            spans.append([lo, hi])
        texts.append("".join(txt[i] for i in words[k]))
        cw = [cf[i] for i in words[k] if i < len(cf)]
        confs.append(float(np.mean(cw)) if cw else 0.0)
    return spans, texts, confs, coverage


def make_recogniser_split(model, band):
    """-> split_fn(row, p) -> list of [l, r]. The recogniser splitter in `split_fn` shape.

    ⚠️ NO FALLBACK TO A GAP THRESHOLD when the recogniser returns nothing. A row the recogniser
    could not read is returned EMPTY, so the consumer sees a row it has no tokens for and abstains
    on it. Quietly substituting the gap splitter there would mean the reported instrument was two
    instruments, with the mix decided by the failures -- which is the shape of defect this step
    exists to remove, not one to reintroduce.

    ⚠️ THE DECODED TEXT AND CONFIDENCE TRAVEL WITH THE SPAN. `read_first_words_typed` used to re-read
    a padded crop of the token it had been handed, and the pad (0.2 x pitch) pulled in neighbouring
    ink: on leaves 405 and 415 the split said ONE word and the re-read returned TWO ('venemently
    vpon', 'fowre tempered'), so a k=1 comparison silently became a k=2 one. Two descriptions of the
    same row drifting apart is the recurring defect in this module; the recogniser already decoded
    this exact span in the pass that produced the boundary, so the text comes from there.
    """
    def split_fn(row, p):
        spans, texts, confs, _cov = recogniser_split(model, band, row, p)
        return [(s[0], s[1], t, c) for s, t, c in zip(spans, texts, confs)]
    return split_fn


def gap_split(gap_fn=None):
    """-> split_fn(row, p). A gap THRESHOLD expressed as a splitter, so the threshold rules and the
    recogniser rule share one injection point instead of the consumer branching on which it holds.
    """
    def split_fn(row, p):
        return _tokens_in_row(row, p, gap=None if gap_fn is None else gap_fn(row, p))
    return split_fn


def _crop_span(band, row, span, p):
    l, r = span
    t = min(x[0] for x in row) - int(round(0.35 * p))
    b = max(x[1] for x in row) + int(round(0.35 * p))
    xpad = max(4, int(round(0.2 * p)))
    return band.crop((max(0, l - xpad), max(0, t),
                      min(band.width, r + xpad), min(band.height, b)))


def read_direction_line(model, leaf_path, conf_floor=0.0):
    """-> dict(signature, catchword, x_positions, confidence, abstain_reason).

    `signature` and `catchword` are SEPARATE fields (R2.1e): scoring ">=1 token read" as a
    success hides leaf 851's exact failure mode -- catchword read, signature missed.
    """
    out = {"signature": None, "catchword": None, "x_positions": {},
           "confidence": {}, "abstain_reason": None}
    im = VS.bands(str(leaf_path), width=1400).get("foot")
    if im is None:
        out["abstain_reason"] = "no foot band"; return out
    p, src = scale(im)
    if p is None:
        out["abstain_reason"] = f"no type scale ({src})"; return out
    y0, why = strip_start(im)
    prop = []
    if y0 is not None:
        prop, why = direction_tokens(im, y0, p)
    if not prop:
        prop, why2 = absorbed_fallback(im, p)
        why = why2 or why
    if not prop:
        out["abstain_reason"] = why or "no token proposed"; return out
    kept = []
    for crop, xc, l, r in prop:
        txt, conf = read(model, crop)
        if txt and conf >= conf_floor:
            kept.append((xc, txt, conf))
    if not kept:
        out["abstain_reason"] = f"proposed {len(prop)} token(s); none read above floor {conf_floor}"
        return out
    for xc, txt, conf in kept:
        slot = "signature" if SIG_X[0] <= xc <= SIG_X[1] else (
               "catchword" if CATCH_X[0] <= xc <= CATCH_X[1] else None)
        if slot and out[slot] is None:
            out[slot] = txt
            out["x_positions"][slot] = round(xc, 3)
            out["confidence"][slot] = round(conf, 3)
    if out["signature"] is None and out["catchword"] is None:
        out["abstain_reason"] = ("read %d token(s) but none in a direction-line position: x=%s"
                                 % (len(kept), [round(k[0], 2) for k in kept]))
    return out


# R2.1f pre-registered EXACTLY ONE band re-cut and it is spent on the word-gap fix. This bound is
# therefore FROZEN at 0.06h..0.30h and is not a tunable. ⚠️ It is also, on measurement, WRONG -- a
# fixed fraction of page height is not anchored to the type block, so on leaf 400 it opens BELOW the
# running head while on leaf 403 it opens above it. That defect is raised as R2.2b and is not fixed
# here, because fixing it here would be the second re-cut under another name.
HEAD_BAND = (0.06, 0.30)


BAND_WIDTH = 1400       # every band is resized to this width; the x-scale follows from it


def band_frame(leaf_path, lo, hi):
    """-> (band image, frame dict). ONE definition of *what a band's pixels mean*.

    ⚠️ R2.2c. Every band this project cuts is FULL PAGE WIDTH resized to `BAND_WIDTH`, so two bands
    of one leaf share an x-scale EXACTLY and differ only by a constant y offset -- measured on
    OT1-1609-B: page 3092x4367, scale 0.452781 for both, offset 118.6px. That fact is what makes a
    band-independent address cheap, and it was invisible while each caller cropped for itself.
    Before this existed, `head_band` (0.06h..0.30h) and `score_head_regions.top_band` (0..0.35h)
    were two hand-rolled crops with no shared vocabulary, so nothing could STATE that the 121-token
    gold addresses a band the production reader never receives. It does not, on 20 of 20 leaves.

    `frame` carries what a consumer needs to convert in both directions and nothing else:
      page_w, page_h  -- the drafted page size, in px
      scale           -- band px per page px
      lo, hi          -- the band's bounds, in fractions of page height
    Use `to_page_frac` / `from_page_frac`; do not re-derive the arithmetic at a call site, which is
    the drift `head_tokens` exists to prevent.
    """
    from PIL import Image
    im = Image.open(str(leaf_path))
    im.draft("RGB", (2800, 3920))
    im = im.convert("RGB")
    w, h = im.size
    crop = im.crop((0, int(h * lo), w, int(h * hi)))
    band = crop.resize((BAND_WIDTH, max(1, int(crop.height * BAND_WIDTH / w))), Image.LANCZOS)
    return band, {"page_w": w, "page_h": h, "scale": BAND_WIDTH / w, "lo": float(lo),
                  "hi": float(hi)}


def page_x_frac(frame, x):
    """Band pixel x -> fraction of PAGE WIDTH. Always a float."""
    return float((x / frame["scale"]) / frame["page_w"])


def page_y_frac(frame, y):
    """Band pixel y -> fraction of PAGE HEIGHT. Always a float.

    ⚠️ Prefer this and `page_x_frac` over `to_page_frac` at any call site that knows which axis it
    wants. `to_page_frac` returns a pair with an optional half, so every consumer had to re-assert
    that the half it asked for is present -- noise that obscures the one place it would actually
    matter. Same arithmetic, one definition; `to_page_frac` now delegates here.
    """
    return float((int(frame["page_h"] * frame["lo"]) + y / frame["scale"]) / frame["page_h"])


def to_page_frac(frame, x=None, y=None):
    """Band pixels -> fractions of PAGE width / height. Either coordinate may be omitted."""
    return (None if x is None else page_x_frac(frame, x),
            None if y is None else page_y_frac(frame, y))


def from_page_frac(frame, xf=None, yf=None):
    """Fractions of PAGE width / height -> band pixels. The inverse of `to_page_frac`.

    ⚠️ A returned y may be NEGATIVE or beyond the band's height, and that is the point: it is how a
    consumer discovers that a labelled feature lies OUTSIDE the band it is holding, instead of
    clamping it to an edge and scoring it as if it were present.
    """
    x = None if xf is None else xf * frame["page_w"] * frame["scale"]
    y = None if yf is None else (yf * frame["page_h"] - int(frame["page_h"] * frame["lo"])) * frame["scale"]
    return x, y


# ══════════════════════════════════════════════════════════════════════════════════════════════
# R2.2d -- SLANT, the measurement that tells the ITALIC ARGUMENT from the ROMAN scripture.
# ══════════════════════════════════════════════════════════════════════════════════════════════
# ⚠️ A PROPERTY OF THE SETTING, WHICH IS THE WHOLE POINT. The alternative discriminator -- "the block
# between the ChapterHead and the first verse" -- is definitionally correct and diagnostically
# worthless: it presumes the boundary it is meant to find, and cannot fire where the chapter head was
# missed. The book's own distinction is a FOUNT. Its arguments are set in italic, its scripture in
# roman, at the same measure. So the thing to measure is slant.
SLANT_ANGLES = tuple(range(-8, 36))     # degrees; this edition's italic leans right


def row_slant(ink, row):
    """-> the shear angle in degrees that best DESLANTS this row's ink, or None if too little of it.

    Shear the row by x' = x - (y - h/2)*tan(a) and take the `a` maximising the column-projection
    profile's SUM OF SQUARES. Deslanting a slanted fount packs each stem into a single column, which
    is exactly what that statistic rewards; upright roman already peaks at 0. Standard deslant
    estimation, applied per row rather than per page because a page holds both founts at once.

    MEASURED over leaves 400-419, 520 rows: ARGUMENT rows 12-18 deg (median 14), everything else
    median 0. The populations do not overlap once rows too small to estimate are excluded.
    """
    t = min(g[0] for g in row); b = max(g[1] for g in row)
    l = min(g[2] for g in row); r = max(g[3] for g in row)
    sub = ink[t:b, l:r]
    if sub.shape[0] < 6 or sub.shape[1] < 20:
        return None
    h, w = sub.shape
    ys = np.arange(h)
    on = sub > 0
    best, bestv = None, -1.0
    for a in SLANT_ANGLES:
        xs = (np.arange(w)[None, :] + (ys[:, None] - h / 2.0) * np.tan(np.deg2rad(a))).astype(int)
        ok = on & (xs >= 0) & (xs < w)
        prof = np.zeros(w)
        np.add.at(prof, xs[ok], 1.0)
        v = float((prof ** 2).sum())
        if v > bestv:
            best, bestv = float(a), v
    return best


def page_slant_mode(leaf_path):
    """-> (the leaf's modal row slant in degrees, reason). The ROMAN slant, i.e. the page's skew.

    ⚠️ TAKEN OVER THE WHOLE PAGE, NEVER OVER A BAND, and the reason is measurable: leaf 411's head
    band is ELEVEN argument rows out of seventeen, so a band-local mode or median is ITALIC and a
    mode-relative rule would invert -- calling the scripture the odd fount. Over the page, scripture
    outnumbers argument several times over on every leaf in the window. This is the same defect as
    R2.1h's `k=2` word gap, where a statistic taken over too small a population was captured by the
    minority it was supposed to exclude.
    """
    rows, frame, p, why = page_type_rows(leaf_path)
    if rows is None or p is None:
        return None, why
    page, _f = band_frame(leaf_path, 0.0, 1.0)
    ink = _ink(page)
    vals = [s for s in (row_slant(ink, r) for r in rows) if s is not None]
    if len(vals) < 5:
        return None, f"only {len(vals)} row(s) support a slant estimate"
    return float(np.median(vals)), None


# ══════════════════════════════════════════════════════════════════════════════════════════════
# R2.2b -- THE ANCHORED HEAD BAND. Built 2026-08-18 to the pre-registration in OCR-ROADMAP.md.
# ══════════════════════════════════════════════════════════════════════════════════════════════
# ⚠️ NOT YET ADOPTED. `HEAD_BAND` remains the production bound and `head_band` still returns it.
# This band is adopted only if it clears A1-A4 pre-registered in the roadmap, and `score_band_anchor.py`
# is what decides that. Wiring it into the reader before it passes would be the second band re-cut
# under a new name -- the exact move R2.2b exists to make legitimate rather than to smuggle.
#
# THE DEFECT IT ANSWERS: 0.06h..0.30h is a fraction of PAGE HEIGHT, so where the type falls inside it
# depends on how the leaf was photographed. Measured: it opens BELOW leaf 400's running head and ABOVE
# leaf 403's. A bound that moves relative to the type cannot be reasoned about per leaf.
#
# N IS STATED IN THE VOCABULARY OF THE BOOK, NOT OF THE ERROR (Sir's anti-circularity ruling). The head
# of a page in this edition carries at most a running head, a chapter head (`CHAP.` / `XXVII.`) and
# their flanking side-notes before the first line of scripture -- three non-body rows by the edition's
# design. N = 6 doubles that. It was fixed BEFORE any leaf was measured; picking it from where the
# first body line happened to fall would be fitting the band to the window it is scored on.
ANCHOR_ROWS = 6
ANCHOR_PAD_P = 0.5      # padding above the first row and below the last, in measured line pitches


def page_type_rows(leaf_path):
    """-> (rows, frame, pitch, reason). Every row of type on the WHOLE PAGE, top-down.

    ⚠️ THE WHOLE PAGE, WITH NO SEARCH WINDOW. A window would be a page fraction, which is the thing
    R2.2b removes -- and a window whose bound is never tested is how a fraction survives a step that
    was supposed to delete it. The page's own type-size filters do the work instead: `glyph_boxes`
    already drops side-border components (leaf edges), anything taller than 1.6 pitches or wider than
    a quarter of the page (rules, shadow bands, smears) and specks, and `_rows_and_lines` requires two
    components on a shared baseline. A scan artefact at the head of the page is one large component
    and is refused by the width filter, not by a guess about where the type starts.
    """
    page, frame = band_frame(leaf_path, 0.0, 1.0)
    p, src = scale(page)
    if p is None:
        return None, frame, None, f"no type scale on the page ({src})"
    rows = _rows_and_lines(glyph_boxes(page, 0, p), p)
    if not rows:
        return None, frame, p, "no row of type found on the page"
    return rows, frame, p, None


def anchored_head_band(leaf_path, n_rows=ANCHOR_ROWS, pad_p=ANCHOR_PAD_P):
    """-> (band image, frame, reason). The first `n_rows` rows of type, padded by `pad_p` pitches.

    The bound MOVES WITH THE TYPE, which is the whole content of "anchored": both edges are read off
    detected rows, so a leaf photographed with more headroom gets a band further down the sheet and
    the same type inside it. Abstains with a reason rather than guessing (house rule R7).

    ⚠️ The crop is taken from the ORIGINAL image via `band_frame`, not from the downscaled page the
    rows were found on, so the band a consumer receives is at full working resolution. The rows only
    supply the BOUND; they never supply the pixels.
    """
    rows, frame, p, why = page_type_rows(leaf_path)
    if rows is None or p is None:
        return None, frame, why
    p = float(p)
    if len(rows) < n_rows:
        return None, frame, (f"page holds {len(rows)} row(s) of type but the band is defined as the "
                             f"first {n_rows}; refusing to return a short band")
    take = rows[:n_rows]
    top = min(g[0] for g in take[0]) - pad_p * p
    bot = max(g[1] for g in take[-1]) + pad_p * p
    lo = max(0.0, page_y_frac(frame, top))
    hi = min(1.0, page_y_frac(frame, bot))
    if hi <= lo:
        return None, frame, f"degenerate anchored bound ({lo:.4f}h .. {hi:.4f}h)"
    band, bframe = band_frame(leaf_path, lo, hi)
    return band, bframe, None


def head_band(leaf_path, frac=None):
    """The head band, as one definition both readers share. FROZEN -- see HEAD_BAND.

    ⚠️ `frac` exists for ONE purpose: running the R2.2b DIAGNOSTIC, which measures what the frozen
    bound is costing. It is not a tuning knob and no production path may pass it. Any number
    produced with `frac` set is NOT comparable to 0.312 and must be reported as a diagnostic.
    """
    lo, hi = HEAD_BAND if frac is None else frac
    return band_frame(leaf_path, lo, hi)[0]


def head_tokens(model, leaf_path, k=1, band=None):
    """-> (the first K MainText token dicts of the head band's first body row, reason).

    ⚠️ ONE PATH. `read_first_words_typed` is a thin map over this, and `audit_prefix_rule` reads the
    SAME tokens rather than re-deriving them. The audit needs each token's SPAN (a whole-line token
    is a blob whether or not the recogniser decoded a space inside it), and a second derivation of
    "the token the reader chose" is exactly how two descriptions of one row drift apart -- the defect
    R2.1g hit on the head band and R2.1i hit on the gold's addressing.
    """
    import region_head as RG
    band = head_band(leaf_path, frac=band)
    p, src = scale(band)
    if p is None:
        return None, f"no type scale ({src})"
    toks, why = RG.classify(band, p, split_fn=make_recogniser_split(model, band))
    if toks is None:
        return None, f"region typing abstained: {why}"
    body = [t for t in toks if t["label"] == RG.MAIN_TEXT]
    if not body:
        labs = sorted({t["label"] for t in toks})
        return None, f"no MainText token in the head band (regions found: {labs or 'none'})"
    row = min(t["row"] for t in body)
    line = sorted([t for t in body if t["row"] == row], key=lambda t: t["l"])
    if len(line) < k:
        return None, (f"first MainText row holds {len(line)} token(s) but {k} were asked for "
                      f"(multi-word catchword); refusing to compare a partial head")
    return line[:k], None


def read_first_words_typed(model, leaf_path, k=1, conf_floor=0.0, band=None):
    """R2.1g -- the head reader rebuilt on the REGION PRIMITIVE. Same signature as its predecessor.

    The difference from `read_first_words` is the whole of R2.1g: that one asks "which row is wide
    enough to be a text line", which a running head can satisfy, and it has no concept of a marginal
    note at all -- so on leaf 412 it returned the side-note `Temporal` in place of the true opening
    `Cades`. This one asks `region_head` which tokens are MainText and reads the first of them, so a
    failure lands on a region label that is separately scored (`score_head_regions.py`) rather than
    on an opaque crop.

    ⚠️ Same band, same k, same abstention discipline. k still comes from the FOOT side.

    ⚠️ R2.1h REDESIGN IS WIRED IN HERE. The split comes from the recogniser's decoded spaces
    (`make_recogniser_split`), which is what makes this reader return WORDS. That is the second half
    of R2.1h and it does not stand alone: `audit_prefix_rule` records that `agrees()` scores the SAME
    whole-line blob as AGREE or DISAGREE according to the CATCHWORD's letter count, so a reader that
    hands the scorer a blob makes the continuity rate a measure of the book's vocabulary. Fixing
    either half alone moves the rate uninterpretably, because the two biases stop cancelling.
    MEASURED at adoption: word count exact 0.2500 -> 0.8125 (MAE 1.44 -> 0.25, blob 0.0000 held),
    with the region score unchanged at 0.8760 and RunningHead recall held at 1.0000.
    """
    toks, why = head_tokens(model, leaf_path, k, band=band)
    if toks is None:
        return None, why
    got = []
    for j, t in enumerate(toks):
        # The splitter DECODED this exact span, so the reading comes from the pass that produced the
        # boundary. This used to re-read a padded crop instead, and the pad pulled in neighbouring
        # ink: on leaves 405 and 415 the split said one word and the re-read returned two. No
        # fallback branch -- `head_tokens` always splits with the recogniser, so a token without a
        # reading is a bug to surface, not a case to quietly re-read.
        txt, conf = t["read"], t["conf"]
        if not txt:
            return None, f"head token {j + 1} of {k} did not read"
        if conf < conf_floor:
            return None, f"head token {j + 1} read {txt!r} at {conf:.2f}, below floor {conf_floor}"
        got.append((txt, conf))
    return got, None


def read_first_words(model, leaf_path, k=1, conf_floor=0.0):
    """-> ([(word, conf), ...], abstain_reason). The first K TOKENS of the first full-measure line.

    Read with the SAME machinery as the direction line, applied to the head band, so a
    failure is attributable to the instrument rather than to two different pipelines.

    ⚠️ WHY K IS A PARAMETER (R2.1f defect 2). A catchword is not always one word: leaf 414 sets
    'of flowre'. Reading exactly one head token and comparing it to a two-word catchword scores a
    TRUE agreement as DISAGREE. The caller knows how many words the catchword holds, so the head
    reader must be able to return that many. K is never inferred here -- inferring it from the head
    side would let the head reader choose the comparison that flatters it.

    Fewer than K tokens on the row is an ABSTENTION, not a short read: returning 1 of 2 tokens
    would silently compare 'of' against 'of flowre' and manufacture a disagreement of the opposite
    sign. Abstentions are reported and counted (R1.4), never dropped.
    """
    band = head_band(leaf_path)
    p, src = scale(band)
    if p is None:
        return None, f"no type scale ({src})"
    boxes = glyph_boxes(band, 0, p)
    LR = text_measure(band, p)
    if LR is None:
        return None, "no text measure in the head band"
    boxes = in_measure(boxes, LR, p)
    lines = _rows_and_lines(boxes, p)
    if not lines:
        return None, "no line of type in the head band"
    L, R = LR
    measure = R - L
    full = [r for r in lines
            if (max(g[3] for g in r) - min(g[2] for g in r)) > 0.75 * measure]
    if not full:
        return None, "no full-measure line in the head band (running head only?)"
    row = full[0]
    spans = _tokens_in_row(row, p)
    if len(spans) < 2:
        return None, (f"head row did not split into tokens ({len(spans)} span) -- "
                      f"word gap {_word_gap(row, p)}px vs row width "
                      f"{spans[0][1] - spans[0][0]}px; refusing to return a whole line as a word")
    if len(spans) < k:
        return None, (f"head row split into {len(spans)} token(s) but {k} were asked for "
                      f"(multi-word catchword); refusing to compare a partial head")
    got = []
    for j in range(k):
        txt, conf = read(model, _crop_span(band, row, spans[j], p))
        if not txt:
            return None, f"head token {j + 1} of {k} did not read"
        if conf < conf_floor:
            return None, f"head token {j + 1} read {txt!r} at {conf:.2f}, below floor {conf_floor}"
        got.append((txt, conf))
    return got, None


def read_first_word(model, leaf_path, conf_floor=0.0):
    """-> ((word, conf), abstain_reason). Single-token wrapper over read_first_words."""
    got, why = read_first_words(model, leaf_path, k=1, conf_floor=conf_floor)
    return (got[0] if got else None), why

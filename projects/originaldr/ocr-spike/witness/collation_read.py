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
from scipy import ndimage
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


def _rows_and_lines(boxes, p):
    rows = []
    for bx in sorted(boxes, key=lambda x: x[1]):
        if rows and abs(bx[1] - float(np.median([g[1] for g in rows[-1]]))) <= 0.30 * p:
            rows[-1].append(bx)
        else:
            rows.append([bx])

    # `>=3 glyphs on a baseline` was a PROXY for "is this type?", and it refused real catchwords:
    # leaves 101 and 601 have 2-component lowest rows at x=0.70-0.76 -- the catchword, with touching
    # letters merged into two blobs. The recogniser now answers the type question directly (a row that
    # reads nothing is dropped post-recognition), so the proxy relaxes to >=2.
    def on_baseline(r):
        bots = np.array([g[1] for g in r], dtype=float)
        return int((np.abs(bots - np.median(bots)) <= 0.15 * p).sum()) >= 2

    return [r for r in rows if len(r) >= 2 and on_baseline(r)]


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


def _tokens_in_row(row, p):
    """Split a row into token [l, r] spans on a measured word gap."""
    row = sorted(row, key=lambda x: x[2])
    gap = _word_gap(row, p)
    out = [[row[0][2], row[0][3]]]
    for _, _, l, r in row[1:]:
        if l - out[-1][1] <= gap:
            out[-1][1] = max(out[-1][1], r)
        else:
            out.append([l, r])
    return out


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


def read_first_word(model, leaf_path, conf_floor=0.0):
    """-> (word, abstain_reason). The FIRST TOKEN of the first full-measure line.

    Read with the SAME machinery as the direction line, applied to the head band, so a
    failure is attributable to the instrument rather than to two different pipelines.
    """
    from PIL import Image
    im = Image.open(str(leaf_path))
    im.draft("RGB", (2800, 3920))
    im = im.convert("RGB")
    w, h = im.size
    crop = im.crop((0, int(h * 0.06), w, int(h * 0.30)))
    band = crop.resize((1400, max(1, int(crop.height * 1400 / w))), Image.LANCZOS)

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
    txt, conf = read(model, _crop_span(band, row, spans[0], p))
    if not txt:
        return None, "first token did not read"
    if conf < conf_floor:
        return None, f"first token read {txt!r} at {conf:.2f}, below floor {conf_floor}"
    return (txt, conf), None

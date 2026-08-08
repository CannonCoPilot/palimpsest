"""R8.4 — verify every witness's SETTING, not just the suspected one.

The `F` error stood for four months because the concordance verified *title
pages*, and a title page is exactly what `F` turns out to have borrowed.  The
test that catches it reads the **printed page number and the running head**
at several separated points and compares them across witnesses that claim the
same setting.  Two copies of one setting put the same printed page number on
the same text with the same running head; two different editions do not, and
they diverge by tens of pages (`B` 743 against `F` 692).

This module does the mechanical half: it crops the head of a leaf -- where the
running head and the page number sit -- for probe leaves spread through each
witness, and assembles one contact sheet per witness for reading.  The
readings themselves are recorded in `setting-readings.json` and checked by
`test_setting_verified.py`.

Structural work only, so `leaves()` is the correct accessor: a render
preserves page content and page order, which is all a page number needs.
`pixel_source()` would refuse five of the twelve and none of the refusals
would be relevant here -- a page number survives interpolation intact.
"""
import os
import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import witnesses as W

OUT = Path(__file__).resolve().parent.parent / ".scratch" / "setting-verify"

# Fraction of page height to keep.  The running head and page number sit in the
# top margin; 0.16 holds them plus the first lines of text, which is what makes
# a same-setting claim checkable -- identical line breaks are the corroboration
# the page number alone does not give.
HEAD_FRAC = 0.16

# ...and the foot, which the head band structurally cannot see.
#
# The constitution (masterplan 0.3) defines setting identity as "same signature,
# same catchword, same line-end words".  The first R8.4 pass read printed page
# number + running head + sidehead + line breaks -- STRONGER than 0.3 on page
# numbers, which 0.3 omits, and silently WEAKER on two of its three named
# criteria, because **the signature and the catchword are both at the FOOT of the
# leaf** and a 16% head crop cannot contain either.  Eleven witnesses were
# verified by a test that never looked at them.
#
# The result was not wrong -- page-number agreement at the same text is hard to
# fake across editions -- but "the method deviates from the constitution and
# nobody said so" is the same defect shape as the one that cost four months.  So
# the instrument is extended to the constitution rather than the constitution
# relaxed to the instrument.
#
# The foot band is located BY INK, not by a fraction of the leaf, and this is not
# fastidiousness -- a fixed fraction was tried first and it FAILED.  The bottom
# 14% of `NT-1582-B` leaf 181 is blank paper: the scans carry generous and
# UNEQUAL bottom margins, so the fraction that reaches the catchword is 0.10 on
# `OT1-1609-P`, over 0.18 on `NT-1582-B` and over 0.22 on `NT-1633-R`.  A single
# constant would have shown blank paper for some witnesses -- and blank paper
# reads as "no catchword on this leaf", which is a false NEGATIVE that looks like
# a finding.  Same shape as the absolute ink thresholds that made `F` report zero
# blank leaves (R1.4): a constant chosen against one witness, applied to all.
FOOT_LINES_FRAC = 0.085   # height above the last ink to keep: last few text lines
FOOT_PAD_FRAC = 0.018     # and below it, so the catchword line is never flush
                          # against the crop edge -- a glyph touching the border
                          # is unreadable in exactly the way that invites a guess
INK_LEVEL = 0.55          # grey below this counts as ink

# A row belongs to the text block if it reaches this fraction of the page's own
# peak row-ink -- witness-relative by construction, never an absolute cut.  This
# deliberately sees only FULL lines: short runs (the catchword, the signature, a
# watermark, a leaf edge) fall below it, and the band is extended downward to
# cover them rather than anchored on them.  See last_ink_row.
TEXT_ROW_REL = 0.20

# ...and a row darker than this across the sampled width is NOT type.  A full
# line of these founts measures 0.10-0.60; 0.80+ is a scan artefact -- the black
# border the digitisation leaves at a leaf edge.  This is an absolute bound, and
# deliberately so: it encodes a property of TYPE, not of any one witness, and
# without it `OT2-1610-F` anchors on its own 183-row black bottom band and every
# F foot band comes out of the wrong place.  `NT-1582-B` carries the same band at
# the top.  Detected on two witnesses, so not a special case for one file.
TYPE_MAX_INK = 0.80

# How far below the last full text line the band extends, in units of the leaf's
# OWN measured line pitch.  Measured requirement: the catchword sits 3.7 pitches
# down on `NT-1633-F` and nearer 2 on the high-resolution captures, so 5 clears
# every case observed with room to spare.  Pitch units and not pixels, because a
# pixel constant would be inherited from whichever witness it was tuned on and
# these leaves range from 1124 to 8672 px tall.
FOOT_BELOW_PITCHES = 5.0

# A run standing more than this many pitches clear of the previous one is not part
# of the regularly-spaced text block.  2.0 admits a normal line and a paragraph
# break, and excludes both `F`'s watermark and `OT1-1609-B`'s leaf-edge shadow.
REGULAR_BREAK_PITCHES = 2.0

# Horizontal window, as fractions of leaf width, in which the row-ink profile is
# measured to FIND the band.  The band itself is always cropped full width -- this
# window only decides where the text block ends.
#
# Right of centre, and that is a deliberate choice about this corpus rather than a
# tuning: `F`'s rehost watermark and papal-keys device sit at the lower LEFT of
# every leaf, and catchwords sit right of centre.  Sampling 0.20-0.80 put the
# watermark inside the window, and on `OT2-1610-F` leaf 243 its several ink runs
# were regular enough to survive the break test, so the anchor landed on the
# watermark and the catchword `† Let` fell outside the band.  Sampling 0.45-0.95
# excludes the device while still covering the text block, the catchword and the
# marginal notes.  Checked against all eleven readable witnesses: every other
# anchor moved by at most 8 px.
ANCHOR_X = (0.45, 0.95)
SHEET_W = 1500

# Probe positions as fractions of the leaf list.  Four, not three, because a
# probe can land on a plate, a blank or a leaf whose number failed to ink, and
# the acceptance criterion needs three *readable* points.  Spread wide: two
# adjacent probes cannot distinguish a constant offset from a coincidence.
PROBE_FRACS = (0.22, 0.42, 0.62, 0.82)


def probe_indices(n, fracs=PROBE_FRACS):
    return [min(n - 1, max(0, int(round(f * n)))) for f in fracs]


def _resize(b, width):
    scale = width / b.width
    return b.resize((width, max(1, int(b.height * scale))), Image.LANCZOS)


def last_ink_row(im):
    """Row index of the last inked line on the leaf, or None if none is found.

    Measured over ANCHOR_X of the width, not the whole leaf: the outer margins
    carry the binding gutter, the page edge and the neighbouring leaf, all of
    which are dark and none of which is type.  Returning None rather than a guess matters
    -- a leaf with no locatable text block must present as UNRESOLVED, not as a
    band cropped from the wrong place (R1.4: absence reported as absence).
    """
    import numpy as np
    a = np.asarray(im.convert("L"), dtype=float) / 255.0
    _, w = a.shape
    core = a[:, int(ANCHOR_X[0] * w):int(ANCHOR_X[1] * w)]
    row_ink = (core < INK_LEVEL).mean(axis=1)
    typelike = row_ink <= TYPE_MAX_INK          # drop scan-border bands
    if not typelike.any():
        return None
    peak = row_ink[typelike].max()               # peak among TYPE rows only
    if peak <= 0.0:
        return None
    # Anchor on the last FULL LINE OF TEXT, and do not try to locate the
    # catchword itself.
    #
    # Locating it was tried and abandoned, which is worth recording because the
    # failure is not obvious.  The catchword is a short run of ink a few line
    # pitches below the text block, and so are the artefacts: `F` carries the
    # `www.fatimamovement.com` watermark in that margin on every leaf (1.1a), and
    # `OT1-1609-B` has its own leaf edge and a dog-eared corner there.  Measured,
    # the separations overlap -- `F`'s catchword sits 3.7 line pitches below the
    # text, `OT1-1609-B`'s edge artefact 4.3 -- so no threshold in pitch units
    # separates catchword from artefact across the corpus.  Every value tried
    # either read the watermark as the catchword or pruned the catchword as an
    # artefact, and both of those are silent: one shows the wrong glyphs, the
    # other shows blank paper, which reads as "this leaf has no catchword".
    #
    # So the band is instead made WIDE ENOUGH TO CONTAIN the catchword wherever it
    # falls, and a person reads it.  Slightly more paper on the sheet is the whole
    # cost; the benefit is that no automatic decision stands between the leaf and
    # the reading.  The instrument's job here is to put the right pixels in front
    # of a reader, not to adjudicate them.
    full = typelike & (row_ink >= TEXT_ROW_REL * peak)
    if not full.any():
        return None

    # The last inked row is not necessarily the last line of TYPE.  `OT1-1609-B`
    # leaf 255 has a dog-eared corner and the shadow of the leaf edge at its foot,
    # broad enough to pass the text threshold and not dark enough to be caught as
    # a border, so the raw answer is row 4350 of 4391 -- past the end of the page.
    #
    # What separates type from that is REGULARITY: lines of type recur at a
    # constant pitch, artefacts do not.  So walk in from the bottom and drop any
    # run standing more than two pitches clear of the one before it.  The
    # catchword is often dropped too -- it also stands clear -- and that is
    # harmless here precisely because the band is extended downward past this
    # anchor rather than ending at it.
    runs = []
    start = None
    for i, v in enumerate(full):
        if v and start is None:
            start = i
        elif not v and start is not None:
            runs.append((start, i))
            start = None
    if start is not None:
        runs.append((start, len(full)))
    if not runs:
        return None
    if len(runs) >= 3:
        pitch = float(np.median(np.diff([r[0] for r in runs])))
        if pitch > 0:
            while len(runs) >= 2 and (runs[-1][0] - runs[-2][1]) > REGULAR_BREAK_PITCHES * pitch:
                runs.pop()
    return int(runs[-1][1] - 1)


def line_pitch(im):
    """Median line pitch of the leaf in pixels, or None if not measurable.

    Start-of-line to start-of-line, not the white gap between lines: the two
    differ by the height of a line of type, and confusing them understates the
    pitch by roughly a factor of three.
    """
    import numpy as np
    a = np.asarray(im.convert("L"), dtype=float) / 255.0
    _, w = a.shape
    core = a[:, int(ANCHOR_X[0] * w):int(ANCHOR_X[1] * w)]
    row_ink = (core < INK_LEVEL).mean(axis=1)
    typelike = row_ink <= TYPE_MAX_INK
    if not typelike.any():
        return None
    peak = row_ink[typelike].max()
    if peak <= 0.0:
        return None
    inked = typelike & (row_ink >= TEXT_ROW_REL * peak)
    starts, prev = [], False
    for i, v in enumerate(inked):
        if v and not prev:
            starts.append(i)
        prev = v
    if len(starts) < 3:
        return None
    return float(np.median(np.diff(starts)))


def _foot_band(im, width):
    """The band holding the last text lines, the catchword and the signature.

    Anchored on the last ink rather than on the leaf edge -- see FOOT_LINES_FRAC.
    """
    w, h = im.size
    last = last_ink_row(im)
    if last is None:
        return None
    pitch = line_pitch(im)
    below = (FOOT_BELOW_PITCHES * pitch) if pitch else (FOOT_PAD_FRAC * h)
    top = max(0, int(last - FOOT_LINES_FRAC * h))
    bot = min(h, int(last + below))
    return _resize(im.crop((0, top, w, bot)), width)


def head_crop(path, width=SHEET_W):
    """The head band alone. Retained so existing callers keep working."""
    return bands(path, width)["head"]


def bands(path, width=SHEET_W):
    """Head and foot bands of one leaf.

    Both are decoded from a single open+draft, because opening a 6000px JP2
    twice to crop two ends of it is the kind of waste that makes a verification
    pass feel expensive enough to skip.
    """
    im = Image.open(path)
    im.draft("RGB", (width * 2, int(width * 2 * 1.4)))  # cheap partial decode
    im = im.convert("RGB")
    w, h = im.size
    return {"head": _resize(im.crop((0, 0, w, int(h * HEAD_FRAC))), width),
            "foot": _foot_band(im, width)}


def leaf_paths(vol, sig, idxs, tmp):
    """Leaf images for the probe indices, from whichever artefact can supply them.

    `M`'s JP2 package is the known-broken one (`..._jp2_broken`), so `leaves()`
    yields paths that will not decode.  M is PDF-primary anyway, and the PDF is
    where its real CCITT stencils live, so falling back to the extractor is not
    a workaround -- it is reading the primary artefact.  The extractor also owns
    the `leaf_range` offset (M's leaf 0 is package page 2072); recomputing that
    here is exactly how a frontmatter leaf gets attributed to the wrong tome.

    The fallback is NEVER silent: an unreadable JP2 on a witness that is *not*
    PDF-primary is a real defect and must raise, not quietly reroute.
    """
    try:
        fs = W.leaves(vol, sig)
        Image.open(fs[idxs[0]]).convert("RGB")  # probe one before trusting all
        return [fs[i] for i in idxs], "jp2"
    except Exception as e:
        if W.PRIMARY[(vol, sig)] != "pdf":
            raise RuntimeError(
                f"{W.wid(vol, sig)}: JP2 leaves unreadable ({type(e).__name__}: {e}) "
                f"and this witness is JP2-primary, so there is no admissible "
                f"fallback. This is a defect, not a routing question.") from e
        import extract_pdf_leaves as X
        tmp.mkdir(parents=True, exist_ok=True)
        written = X.extract(vol, sig, list(idxs), tmp)
        return list(written), "pdf"


def sheet(vol, sig, out_dir=OUT, idxs=None, tag="", want=("head", "foot")):
    """One contact sheet for a witness, labelled by leaf index and band.

    `idxs` overrides the spread probes.  Targeted leaves are what turn a
    near-miss into a match: probing at fixed FRACTIONS lands two witnesses on
    neighbouring printed pages, which corroborates but does not demonstrate.
    The acceptance criterion wants the SAME printed page in both.

    `want` selects bands.  Both by default: the head carries the page number,
    running head and sidehead, the foot carries the signature and catchword, and
    0.3's criterion needs both.  Each band is labelled with WHAT IS TO BE READ
    IN IT, so a later reader cannot mistake a sheet that shows only heads for
    one that discharged the whole criterion -- which is the confusion the first
    R8.4 pass was able to have with itself.
    """
    n = W.WITNESSES[(vol, sig)]["leaves"]
    if idxs is None:
        idxs = probe_indices(n)
    paths, via = leaf_paths(vol, sig, idxs, out_dir / f"_{W.wid(vol, sig)}_src")
    reads = {"head": "page no. / running head / sidehead / first lines",
             "foot": "SIGNATURE / CATCHWORD / last lines"}
    rows = []
    unresolved = []
    for i, p in zip(idxs, paths):
        bs = bands(p)
        for which in want:
            if bs[which] is None:
                # No text block located. Recorded on the sheet as a labelled gap,
                # never omitted: a missing row would read as a leaf that has no
                # catchword, which is a finding, not a measurement failure.
                unresolved.append((i, which))
                continue
            rows.append((i, which, bs[which]))
    band = 34
    total_h = sum(c.height + band for _, _, c in rows)
    sheet_im = Image.new("RGB", (SHEET_W, total_h), "white")
    d = ImageDraw.Draw(sheet_im)
    y = 0
    for i, which, c in rows:
        fill = (20, 20, 20) if which == "head" else (70, 30, 90)
        d.rectangle([0, y, SHEET_W, y + band], fill=fill)
        d.text((8, y + 10),
               f"{W.wid(vol, sig)}   leaf {i}  of {n}   [via {via}]   "
               f"{which.upper()}: {reads[which]}",
               fill=(255, 255, 255))
        y += band
        sheet_im.paste(c, (0, y))
        y += c.height
    out_dir.mkdir(parents=True, exist_ok=True)
    p = out_dir / f"{W.wid(vol, sig)}{tag}.png"
    sheet_im.save(p)
    if unresolved:
        print(f"  !! {W.wid(vol, sig)}: no text block located for "
              + ", ".join(f"leaf {i} {b}" for i, b in unresolved)
              + " -- band UNRESOLVED, not empty")
    return p, idxs


def main():
    want = sys.argv[1:] or None
    for (vol, sig) in sorted(W.WITNESSES):
        wid = W.wid(vol, sig)
        if want and wid not in want and vol not in want:
            continue
        try:
            p, idxs = sheet(vol, sig)
            print(f"{wid:14s} leaves {idxs}  -> {p}")
        except Exception as e:  # reported, never skipped silently
            print(f"{wid:14s} FAILED: {type(e).__name__}: {e}")


if __name__ == "__main__":
    main()

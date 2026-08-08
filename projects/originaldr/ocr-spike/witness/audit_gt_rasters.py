#!/usr/bin/env python3
"""audit_gt_rasters.py — which raster was each ground-truth file actually read from?

Roadmap R7.  `pixel_source()` already refuses to hand a pipeline a rendered raster,
but it guards *code*.  A transcription is made by a person looking at a PNG, and that
path never touches the guard.  This script closes the loop from the other end: it reads
the raster each ground-truth file *declares* and reports it against the witness's
declared PRIMARY artefact.

Three findings of the same shape motivated it -- the global vv->w flip ratified on `F`,
and `d. Roüen` / `Marchans` in the 1634 privilege read on a 1.73x render of `M`.  In all
three the rule was right and the observer was careful; only the image was derived.
Upscaling manufactures the very feature these calls depend on: it closes the gap between
two `v` sorts, rounds a 3x2 speck into a plausible point, and smears a failed `d` bowl
into a point-plus-stroke.

Exit status is 1 if any file declares an inadmissible raster, so this can gate.
"""
from __future__ import annotations

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from witness import witnesses as W  # noqa: E402

GT = pathlib.Path(__file__).resolve().parents[1] / "ground-truth"

# The `ocr_dir` values the ground-truth files use predate the sigla.  They name an
# ACQUISITION, not a book, which is exactly why they went stale.
#
# R7.5b (2026-08-08): this was a SECOND, hand-written copy of the registry's ocr_dir
# map, and it had already drifted -- it resolved `jp2-S06` to `("OT", "M")` while the
# registry deliberately REFUSES that identifier, because `S06` spans two settings 53
# years apart.  Two maps, one of which guesses where the other refuses, is the
# four-month error's exact shape.  The shared entries are now DERIVED.
GT_LEGACY = {
    # Three identifiers appear in ground truth that the registry cannot address, and
    # each is resolved from the RECORD, not from the id.
    #
    # `jp2-S06`: all three files are `matter-ot2-*` at leaves 2049-2070, and M's OT
    # half is leaves 0-2070 (the NT half begins at 2071).  So the volume is read off
    # the leaf index, which is evidence; the identifier itself remains ambiguous and
    # the registry is right to refuse it.  R7.5a re-keys these to `jp2-S06ot`, after
    # which this entry goes away rather than being maintained.
    "jp2-S06":              ("OT", "M"),
    # These two are not acquisitions at all -- they name the extraction directories
    # the prelims were read from, and they already carry the witness id in the path.
    "witness/prelims-M":    ("NT", "M"),
    "witness/prelims-OT-M": ("OT", "M"),
}
OCR_DIR_TO_WITNESS = {**W.OCR_DIR_TO_WITNESS, **GT_LEGACY}

# Why a witness cannot carry a glyph-level call.  Resolution and derivation are separate
# defects and a witness can have both: `F` is barred on resolution *and* renders.
# MOVED to `witnesses.py` as `GLYPH_BARRED` (R7.5, 2026-08-07) and imported here.  It
# is a property of the witness, and the audit and the raster router each holding
# their own copy of "which witnesses are barred" is how the two routes drift apart --
# which is the R7.5 defect itself, one level up.
BARRED = W.GLYPH_BARRED

SUFFIXES = (".pre-review", ".pre-vvfix", ".pre-primary-raster")


def declared_raster_is_render(ocr_dir: str | None, raster: str) -> bool:
    """True when the declared raster comes from a JP2 package rather than the primary."""
    if ocr_dir in OCR_DIR_TO_WITNESS and ocr_dir.startswith(("archive-", "jp2-")):
        return True
    return "jp2" in raster.lower()


def audit() -> int:
    rows, unmapped = [], []
    for f in sorted(GT.glob("*.json")):
        if f.name.endswith(SUFFIXES):
            continue
        d = json.loads(f.read_text())
        ocr_dir = d.get("ocr_dir")
        raster = str(d.get("raster") or "")
        key = OCR_DIR_TO_WITNESS.get(ocr_dir)
        if key is None:
            unmapped.append((f.name, ocr_dir))
            continue
        vol, sig = key
        primary = W.PRIMARY.get((vol, sig))
        render = declared_raster_is_render(ocr_dir, raster)
        # Inadmissible if the witness is barred outright, or if its primary is a PDF and
        # the file was read from the JP2 render of it.
        reasons = []
        # Wrong edition outranks every other defect and is listed first.  A resolution
        # complaint about a file read from the wrong book is a true statement that
        # buries the one that matters -- re-reading it at 545 ppi fixes nothing.
        if W.attests_transcribed_setting(vol, sig) is False:
            reasons.append(
                f"WRONG SETTING -- {W.wid(vol, sig)} attests {W.setting(vol, sig)[1]}, "
                f"but {vol} is a transcript of {W.TRANSCRIBED[vol]}")
        if sig in BARRED:
            reasons.append(BARRED[sig])
        if primary == "pdf" and render:
            reasons.append("primary is the PDF; this is its JP2 render")
        rows.append((f.name, f"{vol}-{sig}", primary, render, reasons))

    bad = [r for r in rows if r[4]]
    print(f"{len(rows)} ground-truth files audited\n")
    by_witness: dict[str, int] = {}
    for _, wit, _, _, _ in rows:
        by_witness[wit] = by_witness.get(wit, 0) + 1
    print("by witness:")
    for wit, n in sorted(by_witness.items()):
        sig = wit.split("-")[1]
        note = f"  <- {BARRED[sig]}" if sig in BARRED else ""
        print(f"  {wit:8} {n:3d}{note}")
    admissible = sum(n for w, n in by_witness.items() if w.split("-")[1] in ("B", "P"))
    print(f"\nread from B (~545 ppi) or P (~411 ppi), the jp2-primary witnesses: {admissible}")

    if unmapped:
        print(f"\n⚠ {len(unmapped)} file(s) with an unmapped ocr_dir -- reported, not skipped:")
        for n, o in unmapped:
            print(f"    {n}  ocr_dir={o!r}")

    print(f"\nINADMISSIBLE: {len(bad)} of {len(rows)}")
    for name, wit, _, _, reasons in bad:
        print(f"  {name:52} {wit:8} {'; '.join(reasons)}")
    if not bad:
        print("  none")
    return 1 if (bad or unmapped) else 0


if __name__ == "__main__":
    sys.exit(audit())

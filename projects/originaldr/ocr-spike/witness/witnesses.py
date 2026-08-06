"""Canonical witness registry for the OriginalDR corpus.

Sigla follow textual-criticism practice: one letter for the physical copy,
volume given separately.  See OCR-MASTERPLAN.md 1.1.
"""
from pathlib import Path

SCANS = Path("/Users/nathanielcannon/Claude/Projects/Palimpsest/imports/"
             "Scripture/Bibles/DouayRheims_DR/sources/scans")

# siglum -> repository / character of the copy
COPIES = {
    "B": "Boston Public Library (G.404.12 / BS180 1609 / BS2080 1582)",
    "P": "Princeton Theological Seminary, Lenox donation (12904, Shelf 1844)",
    "R": "Princeton Theological Seminary, 1633 Rouen (Shelf 1852)",
    "F": "fatimamovement.com rehost; physical copy unidentified",
    "X": "derivative, not a witness",
}

# (volume, siglum) -> record
WITNESSES = {
    ("NT",  "B"): dict(legacy="NT/S09",  year=1582, leaves=812,
                       jp2=SCANS/"S09_nevv-testament-mart-3vol/nevvtestamentofi00mart_jp2",
                       role="base"),
    ("NT",  "F"): dict(legacy="NT/S01",  year=1582, leaves=765,
                       jp2=SCANS/"S01_1582-first-edition-3vol/1582 Douai Rheims Douay Rheims First Edition  3 of 3 1582 New Testament_jp2",
                       role="structure"),
    # Acquired 2026-08-05 (roadmap R4.4).  The file previously held here was a
    # user re-upload of IA's MRC PDF, whose text layer is a 1-bit JBIG2 mask;
    # this is the original Princeton digitisation behind it, continuous tone at
    # the capture's own raster.  Same copy: NCC 0.990 at offset -1.
    ("NT",  "R"): dict(legacy="NT/S04",  year=1633, leaves=778,
                       jp2=SCANS/"S04_1633-rheims-nt/newtestamentofie00engl_jp2",
                       role="support",
                       superseded=SCANS/"S04_1633-rheims-nt/1582 Douay Rheims NT_jp2"),
    ("NT",  "X"): dict(legacy="NT/S08",  year=1582, leaves=800,
                       jp2=SCANS/"S08_1582-rhemes-nt-hires/1582_Rhemes_New_Testament_jp2",
                       role="excluded"),
    ("OT1", "B"): dict(legacy="OT1/S09", year=1609, leaves=1160,
                       jp2=SCANS/"S09_nevv-testament-mart-3vol/holiebiblefaithf00mart_0_jp2",
                       role="base"),
    ("OT1", "P"): dict(legacy="OT1/S03a", year=1609, leaves=1146,
                       jp2=SCANS/"S03_holie-bible-engl-ot-vol1/holiebiblefaithf01engl_jp2",
                       role="surrogate"),
    ("OT1", "F"): dict(legacy="OT1/S01", year=1609, leaves=1135,
                       jp2=SCANS/"S01_1582-first-edition-3vol/1582 Douai Rheims Douay Rheims First Edition  1 of 3 1609 Old Testament_jp2",
                       role="structure"),
    ("OT2", "B"): dict(legacy="OT2/S09", year=1610, leaves=1150,
                       jp2=SCANS/"S09_nevv-testament-mart-3vol/holiebiblefaithf00mart_jp2",
                       role="base"),
    ("OT2", "P"): dict(legacy="OT2/S03b", year=1610, leaves=1146,
                       jp2=SCANS/"S03_holie-bible-engl-ot-vol2/holiebiblefaithf02engl_jp2",
                       role="surrogate"),
    ("OT2", "F"): dict(legacy="OT2/S01", year=1610, leaves=1128,
                       jp2=SCANS/"S01_1582-first-edition-3vol/1582 Douai Rheims Douay Rheims First Edition  2 of 3 1610 Old Testament_jp2",
                       role="structure"),
}

# Which artefact is PRIMARY for each witness.  Not a guess and not a rule about
# formats: taken from the `source`/`original` fields of
# https://archive.org/metadata/<identifier>.  For the institutional captures the
# JP2 package derives from `<id>_orig_jp2.tar` — the camera originals — and the
# PDF is IA's derivative.  For the five user re-uploads the direction reverses:
# someone uploaded a PDF and IA *rendered* the JP2 package from it, at a DPI of
# its own choosing.  Those renders are interpolation (S08 2.00x, OT/S01 4.17x)
# and carry no information about the scan.  See OCR-MASTERPLAN.md 1.2.
PRIMARY = {
    ("NT",  "B"): "jp2",   # nevvtestamentofi00mart      <- _orig_jp2.tar
    ("OT1", "B"): "jp2",   # holiebiblefaithf00mart_0    <- _orig_jp2.tar
    ("OT1", "P"): "jp2",   # holiebiblefaithf01engl      <- _orig_jp2.tar
    ("OT2", "B"): "jp2",   # holiebiblefaithf00mart      <- _orig_jp2.tar
    ("OT2", "P"): "jp2",   # holiebiblefaithf02engl      <- _orig_jp2.tar
    ("NT",  "F"): "pdf",   # 1582DouaiRheims...3Of3      <- uploaded PDF
    ("OT1", "F"): "pdf",   # 1582DouaiRheims...1Of3      <- uploaded PDF
    ("OT2", "F"): "pdf",   # 1582DouaiRheims...2Of3      <- uploaded PDF
    ("NT",  "X"): "pdf",   # 1582RhemesNewTestament      <- uploaded PDF
    ("NT",  "R"): "jp2",   # newtestamentofie00engl      <- _orig_jp2.tar (acquired R4.4)
}

# Path to the primary artefact where that is a PDF.
PDF = {
    ("NT",  "F"): SCANS/"S01_1582-first-edition-3vol/nt-1582.pdf",
    ("OT1", "F"): SCANS/"S01_1582-first-edition-3vol/ot1-1609.pdf",
    ("OT2", "F"): SCANS/"S01_1582-first-edition-3vol/ot2-1610.pdf",
    ("NT",  "X"): SCANS/"S08_1582-rhemes-nt-hires/S08.pdf",
}

# Witnesses whose primary artefact has a BINARISED text layer, so no reading may
# be taken from them.  Empty since 2026-08-05: NT/R was the only entry, and it
# cleared when the original Princeton digitisation was acquired (roadmap R4.4).
# The mechanism stays in place — it is what a re-upload of an MRC PDF looks like
# from the inside, and nothing guarantees this corpus is the last to contain one.
NO_READING = {}


def wid(vol, sig):
    """Canonical witness id, e.g. OT1-1609-B."""
    return f"{vol}-{WITNESSES[(vol, sig)]['year']}-{sig}"

def leaves(vol, sig):
    """Leaf paths for STRUCTURAL work — page order, counts, collation.

    Safe for every witness: a render preserves page content and page order, so
    the leaf inventory and the collation hold regardless of primacy.  For
    pixel-level work use `pixel_source` instead, which refuses the renders.
    """
    return sorted(WITNESSES[(vol, sig)]["jp2"].glob("*.jp2"))

def pixel_source(vol, sig):
    """The artefact a pixel-level consumer must read: crops, training, CER.

    Raises for the five witnesses whose JP2 package is an IA render of an
    uploaded PDF, and for any witness whose primary text layer is binarised.
    Both are SILENT defects otherwise — a rendered or composited leaf still
    looks like a page, which is how 3334x4684 was once read as a scan.
    """
    key = (vol, sig)
    if key in NO_READING:
        raise ValueError(f"{wid(vol, sig)}: no reading may be taken — {NO_READING[key]}")
    if PRIMARY[key] != "jp2":
        raise ValueError(
            f"{wid(vol, sig)}: primary artefact is a PDF ({PDF[key].name}); its JP2 "
            f"package is an IA render of that PDF and is interpolation, not scan "
            f"detail. Extract pages from the PDF, or use leaves() for structure only.")
    return WITNESSES[key]["jp2"]

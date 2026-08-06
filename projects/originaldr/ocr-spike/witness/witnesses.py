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
    # F names a copy OWNED AND DIGITISED BY THE FATIMA MOVEMENT.  It has no
    # library shelfmark because it is not a library's copy -- privately held is
    # a determinate answer, not a missing one.  An earlier revision read "rehost;
    # physical copy unidentified", which subordinated the COPY on evidence that
    # only ever concerned the SCAN.  See OCR-MASTERPLAN.md 1.1a.
    "F": "privately held; owned and digitised by the Fatima Movement (fatimamovement.com)",
    # M names the copies behind the 2007 Maximus Scriptorius reprint: a 1635
    # Rouen OT and a 1582 Rheims NT.  Excluded from the verse text, admitted for
    # prelims and endmatter -- it carries the ONLY genuine 1582 Censure and
    # Preface p.1 in the corpus (1.4).
    "M": "unknown copies republished 2007 by Maximus Scriptorius (1635 Rouen OT, 1582 Rheims NT)",
    "X": "not a distinct copy -- B re-wrapped and re-rendered",
}

# Each role names a PERMISSION and a LIMIT, and every one is a statement about
# what a FILE may be used for -- never a ranking of the COPIES.  Definitions are
# OCR-MASTERPLAN.md 1.1a; this table exists so a consumer of MANIFEST.json need
# not go and read the plan to find out what it is allowed to do.
ROLES = {
    "base":        "the copy the transcript is taken FROM -- it IS the text. "
                   "Every reading; training crops; CER evaluation.",
    "surrogate":   "a second scan of the SAME setting at usable resolution. "
                   "Resolves what the base cannot show -- damage, show-through, "
                   "an inked-over sort.  Never supplies a reading where the base "
                   "is legible and merely disagreed with.",
    "lowres":      "a genuinely independent copy whose DIGITISATION resolves too "
                   "little for glyph-level work.  Collation, page order, "
                   "completeness, and any reading no better-resolved witness "
                   "carries.  NOT training data, NOT CER evaluation, and it may "
                   "not adjudicate long-s against f -- the distinguishing nub is "
                   "under 1.6 px at 168 ppi.",
    "support":     "a copy of a DIFFERENT edition, admitted for named leaves "
                   "only: a reading where the base has NO leaf at all, flagged "
                   "as supplied with its source named.",
    "frontmatter": "admitted for prelims and endmatter, excluded from the verse "
                   "text.  No verse of scripture, at any resolution.",
    "excluded":    "not a distinct copy, or not a witness to the setting. "
                   "Audit and provenance only; nothing evidential.",
}

# NOTE: "lowres" was called "structure" until 2026-08-05.  The old label stated
# the limit as a property of the COPIES when it is a property of ONE
# DIGITISATION of them -- F is not less complete than the library copies (for
# OT1 it holds the same 1132-leaf book block, and for the NT it is MORE complete
# than the base exemplar, which lacks its Censure and Preface p.1 outright).
# "Structure only" barred it from readings it is entitled to carry.  1.1a.

# (volume, siglum) -> record
WITNESSES = {
    ("NT",  "B"): dict(legacy="NT/S09",  year=1582, leaves=812,
                       jp2=SCANS/"S09_nevv-testament-mart-3vol/nevvtestamentofi00mart_jp2",
                       role="base"),
    ("NT",  "F"): dict(legacy="NT/S01",  year=1582, leaves=765,
                       jp2=SCANS/"S01_1582-first-edition-3vol/1582 Douai Rheims Douay Rheims First Edition  3 of 3 1582 New Testament_jp2",
                       role="lowres"),
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
                       role="lowres"),
    ("OT2", "B"): dict(legacy="OT2/S09", year=1610, leaves=1150,
                       jp2=SCANS/"S09_nevv-testament-mart-3vol/holiebiblefaithf00mart_jp2",
                       role="base"),
    ("OT2", "P"): dict(legacy="OT2/S03b", year=1610, leaves=1146,
                       jp2=SCANS/"S03_holie-bible-engl-ot-vol2/holiebiblefaithf02engl_jp2",
                       role="surrogate"),
    ("OT2", "F"): dict(legacy="OT2/S01", year=1610, leaves=1128,
                       jp2=SCANS/"S01_1582-first-edition-3vol/1582 Douai Rheims Douay Rheims First Edition  2 of 3 1610 Old Testament_jp2",
                       role="lowres"),
    # The 2007 reprint holds BOTH testaments in one 2872-leaf package, so this
    # witness is a SLICE of it: the NT begins at the blank leaf 2071 and its
    # title page stands at 2072.  Addressing the whole package as one witness
    # would pool a 1635 Rouen OT with a 1582 Rheims NT -- the same mistake the
    # retired S01/S09 identifiers made (1.1a).
    ("NT",  "M"): dict(legacy="NT/S06", year=1582, leaves=800,
                       jp2=SCANS/"S06_1610-facsimile-whole/Douay-Rheims-1610-Bible_jp2_broken",
                       leaf_range=(2072, 2872),
                       role="frontmatter"),
    # The OTHER half of the same package, and a DIFFERENT EDITION: a 1635 Rouen
    # (Cousturier) printing of the Old Testament, not the 1609/1610 Douai
    # (Kellam) one the edition transcribes.  It is therefore NOT a witness to
    # either OT tome's setting and may never supply an OT verse reading.  It is
    # registered because R6.4 collates its PRELIMS against 1609/1610, and a
    # difference cannot be cited to a leaf in a witness that has no addresses.
    #
    # The OT/NT boundary is the blank leaf 2071, asserted from an ink-profile
    # scan of the package, not assumed: 2070 is the backmatter (Faults escaped
    # + the 1634 privilege), 2071 blank, 2072 the NT title page.
    ("OT",  "M"): dict(legacy="OT/S06", year=1635, leaves=2071,
                       jp2=SCANS/"S06_1610-facsimile-whole/Douay-Rheims-1610-Bible_jp2_broken",
                       leaf_range=(0, 2071),
                       role="frontmatter"),
}

# A declared vocabulary that nothing checks is decoration.  An unknown role must
# fail at import, not silently reach MANIFEST.json where a downstream consumer
# would treat it as a permission it does not have.
_bad = {(v, s): r["role"] for (v, s), r in WITNESSES.items() if r["role"] not in ROLES}
if _bad:
    raise ValueError(
        f"witness roles not in the declared vocabulary: {_bad}. "
        f"Known roles: {sorted(ROLES)}.  A role is a permission and a limit "
        f"(OCR-MASTERPLAN.md 1.1a) -- add it to ROLES with its definition, or "
        f"fix the typo; do not let an undefined one through."
    )
del _bad

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
    # S06's JP2s are a 600-dpi render of a LETTER-SIZE page (5100x6601), and the
    # JPGs a 300-dpi one (2550x3301), while the PDF carries the actual scan as a
    # 2955x4206 CCITT stencil.  Both renders are therefore worse than the source
    # -- the 600-dpi one is a plain 2x upscale of the 300-dpi one.
    ("NT",  "M"): "pdf",   # S06.pdf (Maximus Scriptorius 2007) <- the CCITT stencils
    ("OT",  "M"): "pdf",   # same package, same PDF -- the 1635 Rouen OT half
}

# Path to the primary artefact where that is a PDF.
PDF = {
    ("NT",  "F"): SCANS/"S01_1582-first-edition-3vol/nt-1582.pdf",
    ("OT1", "F"): SCANS/"S01_1582-first-edition-3vol/ot1-1609.pdf",
    ("OT2", "F"): SCANS/"S01_1582-first-edition-3vol/ot2-1610.pdf",
    ("NT",  "X"): SCANS/"S08_1582-rhemes-nt-hires/S08.pdf",
    ("NT",  "M"): SCANS/"S06_1610-facsimile-whole/S06.pdf",
    ("OT",  "M"): SCANS/"S06_1610-facsimile-whole/S06.pdf",
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
    rec = WITNESSES[(vol, sig)]
    fs = sorted(rec["jp2"].glob("*.jp2"))
    lo, hi = rec.get("leaf_range", (0, len(fs)))
    fs = fs[lo:hi]
    if len(fs) != rec["leaves"]:
        raise ValueError(f"{wid(vol, sig)}: {len(fs)} leaves on disk, registry says "
                         f"{rec['leaves']} -- the registry is the source of truth, so "
                         f"one of them is wrong and neither may be silently preferred")
    return fs

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

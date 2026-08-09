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
    # YEAR CORRECTED 1582 -> 1633 (2026-08-06, roadmap R8).  This witness's NEW
    # TESTAMENT IS NOT THE 1582 RHEMES SETTING.  Its body agrees with NT-1633-R
    # page for page and line for line -- printed 332 "THE ACTES", 530 "THE FIRST
    # EPISTLE OF S. PAVL", 682, 686, 690 all identical including the shared
    # misprint "Iralie" for "Italie" -- at a constant leaf offset of +4, while
    # the genuine 1582 (NT-1582-B) puts Apocalypse ch. XXII on printed 743
    # against F's 692 and carries running-head apparatus ("CHA. N.", "HOLY
    # weeke") that neither F nor R has.
    #
    # It is an INDEPENDENT COPY of that 1633 edition, not a re-render of R: on a
    # verified-blank bottom margin F/R matched pairs correlate 0.099/0.021/-0.022
    # against controls 0.077/-0.084/-0.030, i.e. no shared paper.  Compare the
    # proven same-leaf case (F's Censure vs R's) at +0.769.
    #
    # The folder name says "1582 New Testament" because the uploader named it so.
    # A vendor's folder name is not a bibliographical fact; the leaves are.
    #
    # F's OT1 and OT2 are UNAFFECTED and remain genuine 1609/1610 -- checked the
    # same way (LEVITICVS 280, SECOND BOOKE 680/980; PROVERBES, OF EZECHIEL).
    ("NT",  "F"): dict(legacy="NT/S01",  year=1633, leaves=765,
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
    #
    # R9.0 (2026-08-08): role `frontmatter` -> `lowres`.  This half is the SAME
    # SETTING as the base exemplar -- 1582 Rheims Fogny -- so the bibliographic
    # ground that limits the OT half does not touch it.  What limits it is the
    # raster: 1-bit CCITT at ~380 ppi against B-NT's ~545 ppi continuous tone.
    # That is a limit on GLYPH work, which is exactly `lowres`, the role F's two
    # OT volumes carry.  Filing it as `frontmatter` stated a limit of one
    # DIGITISATION as a property of the COPY -- the identical error the plan
    # retired for F under the term `structure only` (1.1a) -- and withheld from
    # the New Testament the second copy of its own setting that it has.
    # It attests; it never adjudicates.  GLYPH_BARRED is unchanged by this.
    ("NT",  "M"): dict(legacy="NT/S06", year=1582, leaves=800,
                       jp2=SCANS/"S06_1610-facsimile-whole/Douay-Rheims-1610-Bible_jp2_broken",
                       leaf_range=(2072, 2872),
                       role="lowres"),
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

# ---------------------------------------------------------------------------
# R9.1 -- EVIDENTIAL SCOPE AT VERSE GRAIN (Gate 0f, OCR-MASTERPLAN.md 2)
#
# What a witness may be used for at verse grain.  DERIVED from the role, never
# assigned per witness, because a per-witness field is a second place for the
# same fact and would drift from 1.1a exactly as three copies of the raster map
# drifted from each other (R7.5b/c).  The role IS the permission; this table
# only says what the permission means for a verse.
#
#   full       the verse text may be read, adjudicated and evaluated here
#   collation  the verse may be ATTESTED, localized and counted -- and no glyph
#              call, no training crop, no CER figure.  ATTESTATION IS NOT
#              ADJUDICATION, and the whole point of a third value is that the
#              corpus can now say so.
#   none       the verse text is not evidence here AT ANY GRAIN -- not a
#              reading, not an attestation, not a presence count
#
# Why this exists.  1.1a has stated these limits from the beginning and NO CODE
# HAS EVER READ ONE.  `OT-1635-M` is excluded from the verse text in four
# documents and was attesting psalms 2,515 and genesis 1,530 in
# coverage-audit-verse.json for as long as that audit has run.  The nearest
# thing to enforcement was `witness_inventory.drop_tomes`, which named the right
# file for the wrong reason, had exactly one consumer, and that consumer read it
# as a CONTAINMENT claim -- the R7.5a-3 addressing defect.  The prose was right
# throughout; it simply had nothing downstream of it.
VERSE_SCOPES = frozenset({"full", "collation", "none"})

ROLE_VERSE_SCOPE = {
    "base":        "full",        # it IS the text
    "surrogate":   "full",        # same setting, usable resolution
    "lowres":      "collation",   # a real copy of the setting, a raster that cannot answer a glyph
    "support":     "collation",   # a real copy of ANOTHER setting; supplies only where the base has no leaf
    "frontmatter": "none",        # different edition -- no capture of it could make it a witness here
    "excluded":    "none",        # not a distinct copy, or not a witness to the setting
}

_unscoped = sorted(set(ROLES) - set(ROLE_VERSE_SCOPE))
if _unscoped:
    raise ValueError(
        f"roles with no declared verse scope: {_unscoped}. A role added without a scope would "
        f"default into admission, which is the failure Gate 0f exists to prevent -- give it a "
        f"scope in ROLE_VERSE_SCOPE, or do not declare the role."
    )
del _unscoped


def verse_scope(vol, sig):
    """What this witness may be used for at VERSE grain: 'full' | 'collation' | 'none'."""
    return ROLE_VERSE_SCOPE[WITNESSES[(vol, sig)]["role"]]


def verse_scope_of(ocr_dir):
    """`verse_scope` for a legacy `ocr_dir`. Raises the registry's own error on an unknown id."""
    return verse_scope(*witness_of(ocr_dir))


def verse_admitted(ocr_dir):
    """May this volume's verse text count as evidence at all? (Gate 0f)"""
    return verse_scope_of(ocr_dir) != "none"


class VerseScopeError(PermissionError):
    """Raised when verse text is read from a witness the corpus does not admit for verse text."""


def assert_verse_admitted(ocr_dir):
    """Refuse a verse-grain read of a `none`-scope witness, naming the role and the gate."""
    if not verse_admitted(ocr_dir):
        vol, sig = witness_of(ocr_dir)
        raise VerseScopeError(
            f"{ocr_dir} is {wid(vol, sig)}, role {WITNESSES[(vol, sig)]['role']!r}, "
            f"verse_scope 'none': its verse text is not evidence at any grain -- not a reading, "
            f"not an attestation, not a presence count (OCR-MASTERPLAN.md 2, Gate 0f). "
            f"It is admitted for prelims and endmatter, and for structural bookkeeping, which is "
            f"why its leaves still appear in every leaf count. If you are auditing the localization "
            f"ARTEFACT rather than scoring the text, pass scope_check=False and say so."
        )


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


# Why a witness cannot carry a GLYPH-level call.  Resolution and derivation are
# separate defects and a witness can have both: `F` is barred on resolution *and*
# is a render.
#
# This lived in `audit_gt_rasters.py` until 2026-08-07 (R7.5).  It belongs beside
# the registry, because it is a property of the witness, and because two routes to
# the pixels each holding their own copy of "which witnesses are barred" is how the
# routes drift apart.  The audit now imports it from here.
GLYPH_BARRED = {
    "F": "~168 ppi in all three volumes; the long-ſ nub spans under 1.6 px (§1.2)",
    "X": "excluded -- a 2.00x upscale of B-NT with zero real detail beyond it",
}


# Legacy `ocr_dir` -> the witness it actually addresses.
#
# This lived in `jp2_page.py` until 2026-08-07 (R7.5b).  It is registry data --
# "which witness does this legacy identifier name?" -- and it moved here for the
# same reason `GLYPH_BARRED` did: `jp2_page` is the raster ACCESSOR, and a module
# that reads the map should not have to import a module that opens images to get
# it.  `curated_sources.py` in particular is a pure allowlist imported at every
# ingest boundary, and making it depend on PIL to answer "which source is this
# folder?" would be a reason not to call the guard.
#
# Every entry except the two noted was confirmed by PATH IDENTITY against the old
# table.  The two exceptions are the two defects R7.5 retired.
OCR_DIR_TO_WITNESS = {
    # --- S01 / `F`: PDF-primary renders. Barred from pixel work, fine for structure.
    "archive-ot1-1609":       ("OT1", "F"),
    "archive-ot2-1610":       ("OT2", "F"),
    # NB the id says 1582 and the witness is 1633 (1.1c). The id is legacy and is
    # NOT renamed here -- it is what the existing ground-truth records contain, and
    # silently remapping it would hide R8.6 rather than discharge it.
    "archive-nt-1582":        ("NT", "F"),
    # --- S03 / `P`: genuine Princeton captures, JP2-primary.
    "pdf-S03a":               ("OT1", "P"),
    "pdf-S03b":               ("OT2", "P"),
    # --- S04 / `R`: DEFECT. The old table named the retired MRC composite; the
    #     registry resolves the acquired Princeton original (R4.4).
    "jp2-S04":                ("NT", "R"),
    # --- S08 / `X`: excluded witness, PDF-primary. Barred.
    "jp2-S08":                ("NT", "X"),
    # --- S09 / `B`: the base exemplars, JP2-primary.
    "pdf-S09nt":              ("NT", "B"),
    "archive-holiebible-ot1": ("OT1", "B"),
    "jp2-S09ot2":             ("OT2", "B"),
    "archive-holiebible-ot2": ("OT2", "B"),   # alias of the same volume
}

# `jp2-S06` is NOT in the map above, and that is deliberate.
#
# `S06` is a whole Bible in one file: 2,872 leaves carrying the **1635 Rouen OT**
# and the **1582 Rheims NT**, held here as two witness records over one file
# (`OT-1635-M`, `NT-1582-M`).  A bare `jp2-S06` therefore names neither a witness
# nor a setting -- the two halves are 53 years and two towns apart.  Resolving it
# to either would be a guess, and guessing which setting a leaf belongs to is the
# error that cost four months.
#
# So it raises, and names the two ids that are well formed.  113,514 existing
# records carry the ambiguous value; they are re-keyed by R7.5a, not papered over.
S06_AMBIGUOUS = "jp2-S06"
S06_SPLIT = {
    "jp2-S06nt": ("NT", "M"),
    "jp2-S06ot": ("OT", "M"),
}
OCR_DIR_TO_WITNESS.update(S06_SPLIT)

# WHERE the two settings meet, VERIFIED BY READING THE LEAVES (R7.5a, 2026-08-08).
#
# Not inferred from the leaf counts, which is what makes this trustworthy: the counts
# alone leave one leaf of 2,872 unaccounted for, and an arithmetic argument cannot say
# which testament that leaf belongs to.  All three were rendered from `S06.pdf` (M's
# primary artefact) and read:
#
#   package 2070  `FAVLTS ESCAPED IN THE PRINTING` + `EXTRAICT DV PRIVILEGE DV ROY`,
#                 the latter granted to Iean le Cousturier at Rouen and dated 1634 --
#                 Old Testament errata and the OT's own privilege.  LAST OT LEAF.
#   package 2071  BLANK.  0.00% ink at 40 dpi against 4-9% on its neighbours.  A
#                 divider between the testaments; it belongs to NEITHER witness, and
#                 assigning it to either would be inventing a leaf for a setting.
#   package 2072  the New Testament title page: `THE NEVV TESTAMENT OF IESVS CHRIST`
#                 ... `PRINTED AT RHEMES, by Iohn Fogny. 1582.`, in its woodcut
#                 border.  FIRST NT LEAF, and 53 years from the leaf two before it.
#
# 2071 OT + 1 blank + 800 NT = 2872, which is the whole package with nothing left over.
S06_LAST_OT_LEAF = 2070          # package index, inclusive
S06_BLANK_DIVIDER = 2071         # package index; in neither witness
S06_FIRST_NT_LEAF = 2072         # package index, inclusive


def s06_volume(package_leaf):
    """"OT" or "NT" for a leaf of the S06 package, or a loud error for the divider.

    Takes a PACKAGE index (0-based, 0..2871).  The blank divider raises rather than
    being folded into whichever side is convenient: a leaf that is in neither setting
    is a third answer, and collapsing it to a binary is how a boundary quietly moves.
    """
    if not 0 <= package_leaf < 2872:
        raise IndexError(f"S06 package leaf {package_leaf} outside 0..2871")
    if package_leaf <= S06_LAST_OT_LEAF:
        return "OT"
    if package_leaf >= S06_FIRST_NT_LEAF:
        return "NT"
    raise ValueError(
        f"S06 package leaf {package_leaf} is the BLANK DIVIDER between the 1635 Rouen "
        f"Old Testament and the 1582 Rheims New Testament. It is in neither witness "
        f"(verified: 0.00% ink). It has no setting, and giving it one would invent a "
        f"leaf for whichever setting it was assigned to.")


def witness_of(ocr_dir):
    """(vol, sig) for a legacy `ocr_dir`, or a loud error naming the alternative."""
    if ocr_dir == S06_AMBIGUOUS:
        raise KeyError(
            f"{ocr_dir!r} names a FILE, not a witness: S06 is one 2,872-leaf volume "
            f"carrying the 1635 Rouen Old Testament and the 1582 Rheims New "
            f"Testament, which are two settings 53 years apart. Use "
            f"{' or '.join(sorted(S06_SPLIT))} and say which. (R7.5a re-keys the "
            f"existing records; do not guess a volume here.)")
    if ocr_dir not in OCR_DIR_TO_WITNESS:
        raise KeyError(f"{ocr_dir!r} is not a known ocr_dir; known: "
                       f"{', '.join(sorted(OCR_DIR_TO_WITNESS))}")
    return OCR_DIR_TO_WITNESS[ocr_dir]


def source_id(vol, sig):
    """The ACQUISITION this witness came from, as a curated-allowlist id ('S9').

    Derived from the registry's own `legacy` field rather than restated, so the
    allowlist in `curated_sources.py` cannot drift from the registry.  `legacy`
    carries the acquisition with its zero padding and, for the two-volume S03 set,
    a volume suffix -- `OT1/S03a` is source `S3`.  Both are normalised away here;
    the allowlist is per acquisition, not per volume.
    """
    acq = WITNESSES[(vol, sig)]["legacy"].split("/", 1)[1]     # 'S03a'
    return "S" + acq[1:].lstrip("0").rstrip("ab")              # -> 'S3'


def glyph_source(vol, sig):
    """The artefact a GLYPH-level consumer must read, as (kind, path).

    `kind` is "jp2" for a directory of capture leaves, or "pdf" for a PDF whose
    pages must be extracted.  Raises for any witness that cannot support a glyph
    call at all.

    This is deliberately distinct from `pixel_source()`, which answers a narrower
    question -- "is this witness's JP2 package the capture, or an IA render?" -- and
    therefore raises for `M`, whose JP2 package is corrupt but whose PDF holds the
    real CCITT stencils.  `pixel_source()`'s own message says to extract from the
    PDF in that case; this function is where that instruction is executed rather
    than left to each caller to remember.

    The bars, in the order they are applied and for separate reasons:
      * NO_READING  -- the primary's text layer is binarised (an MRC re-upload).
      * GLYPH_BARRED -- the witness is excluded, or its resolution cannot resolve
        the features a glyph call depends on.  A render is not the issue here; an
        upscale of a genuine capture is still barred, because interpolation
        manufactures the feature the call depends on rather than recording it.
      * primary == "pdf" -- not a bar. It selects the extraction route.
    """
    key = (vol, sig)
    if key in NO_READING:
        raise ValueError(f"{wid(vol, sig)}: no reading may be taken — {NO_READING[key]}")
    if sig in GLYPH_BARRED:
        raise ValueError(
            f"{wid(vol, sig)}: barred from glyph-level work — {GLYPH_BARRED[sig]}. "
            f"Re-read the locus on an admissible witness ({', '.join(admissible(vol))}) "
            f"or report that neither holds it. No fallback is permitted (R7).")
    if PRIMARY[key] == "pdf":
        return ("pdf", PDF[key])
    return ("jp2", WITNESSES[key]["jp2"])


def admissible(vol):
    """Sigla in `vol` that can carry a glyph-level call, for use in error messages.

    The bars are tested directly rather than by calling `glyph_source()`, which
    would recurse: `glyph_source` builds its refusal message from this function.
    """
    out = [wid(v, s) for (v, s) in WITNESSES
           if v == vol and s not in GLYPH_BARRED and (v, s) not in NO_READING]
    return sorted(out) or ["none in this volume"]


def setting(vol, sig):
    """The SETTING a witness attests: (volume, year).

    Two witnesses may be collated against each other only if this matches.  The
    NT holds two settings -- 1582 Rhemes and 1633 Rouen -- and for four months
    the plan treated NT-F as a witness to the first when its body is the second.
    Nothing in the code said otherwise, because the year lived in a dict field
    that only `wid()` ever read.
    """
    return (vol, WITNESSES[(vol, sig)]["year"])


def witnesses_to(vol, year):
    """Every siglum attesting one setting.  Use this to pick collation partners."""
    return sorted(s for (v, s) in WITNESSES if v == vol and WITNESSES[(v, s)]["year"] == year)


def assert_same_setting(vol, *sigs):
    """Raise if sigla span more than one setting.

    A collation across settings is not a collation, it is a conflation, and it
    fails SILENTLY: two editions of one translation agree for pages at a time,
    so the error surfaces only where they happen to differ -- which is exactly
    where the reading matters.
    """
    seen = {}
    for s in sigs:
        seen.setdefault(setting(vol, s), []).append(s)
    if len(seen) > 1:
        parts = "; ".join(f"{y}: {','.join(ss)}" for (v, y), ss in sorted(seen.items()))
        raise ValueError(
            f"{vol}: sigla span {len(seen)} settings ({parts}). These attest DIFFERENT "
            f"editions and may not be collated as witnesses to one setting. Use "
            f"witnesses_to({vol!r}, <year>) to choose partners.")
    return True


# The edition each volume is a transcript OF.  A witness attesting anything else is
# support, never the text.  `OT` is deliberately absent: it is the whole-Bible pseudo-
# volume behind M's 1635 Rouen prelims, admitted precisely BECAUSE it is another
# edition, so "wrong setting" is not a defect there and must not be reported as one.
TRANSCRIBED = {"NT": 1582, "OT1": 1609, "OT2": 1610}


def attests_transcribed_setting(vol, sig):
    """True if this witness attests the edition being transcribed.

    None when the volume has no transcribed target (see TRANSCRIBED), so callers
    can distinguish "not the text" from "not applicable" rather than collapsing
    both to False -- collapsing them is how NT-F stayed admissible.
    """
    target = TRANSCRIBED.get(vol)
    if target is None:
        return None
    return WITNESSES[(vol, sig)]["year"] == target


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

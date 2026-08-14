#!/usr/bin/env python
"""R9.6 -- the OriginalDR project root, derived ONCE and imported, never restated.

THE DEFECT THIS REPLACES. Commit `2633cbb` moved the OCR project out of gitignored
scratch into ``projects/originaldr/``. Six modules restated the old root as a literal
and were not moved with it, so every path below them resolved into a directory that
**does not exist** -- verified 2026-08-14: ``core/.scratch/originaldr-project`` is
absent in its entirety, while ``projects/originaldr/reconstruction/reads`` holds 10
entries and ``.../consensus`` holds 76.

It resolved SILENTLY. Readers guarded on ``.exists()`` and skipped, so
``detect_our_ocr`` reported the well-formed ``{"verses_scored": 0, "error": "no
anchor text"}`` for **every book** -- a clean-looking empty result standing in for a
source that was never opened. That is R1.4 and ``_empty_because`` (§1.4): a null needs
its cause established.

⚠️ **FOUR modules `mkdir(parents=True)` on these paths and WRITE** -- `detect_sources`,
`detect_s_dismas`, `detect_ocr_consensus`, `build_consensus`. Running any of them
against the old literal would RECREATE the dead tree and write the anchor reads into
it, where nothing reads them, leaving a directory that looks populated and current.
The roadmap recorded two; it is four (found 2026-08-14 while dispositioning R11.2a).

THE RULE. One derived root, imported. A module that restates it is a second copy of a
fact that has already changed once -- the shape R7.5b found in three copies of a
routing map (one already drifted) and R11.1 found in two copies of a work-order pin.

Enforced by ``witness/test_project_root.py``.
"""
from __future__ import annotations

import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
# HERE.parents = [0]mask_engine [1]gold [2]fixtures [3]tests [4]core [5]<repo>
REPO = HERE.parents[5]

#: The live project root. Overridable so a checkout elsewhere is not forced to move.
ORIGINALDR = Path(os.environ.get("ORIGINALDR_ROOT", REPO / "projects" / "originaldr"))

#: The pre-`2633cbb` location. Named ONLY so the guard and `require()` can refuse it.
LEGACY_ROOT = REPO / "core" / ".scratch" / "originaldr-project"

READS_DIR = ORIGINALDR / "reconstruction" / "reads"
CONSENSUS_DIR = ORIGINALDR / "reconstruction" / "consensus"
BASIS_DB = ORIGINALDR / "reconstruction" / "basis-db.sqlite"
SOURCES = ORIGINALDR / "sources"
DIPL_ROOT = SOURCES / "our-ocr-diplomatic"
OCR_ROOT = SOURCES / "our-ocr"
S_DISMAS = SOURCES / "s-dismas"
ARCHIVE_ORG = SOURCES / "archive-org"
ODR_COM = SOURCES / "odr-com"
ODR_SCRAPE = ODR_COM / "scrape"
OCR_VENV_BIN = ORIGINALDR / "ocr-venv" / "bin"
OCR_SPIKE = ORIGINALDR / "ocr-spike"

# ── The two Madueke witnesses: they did NOT migrate with the project (R9.6a) ──
# They live under imports/, not under the project root, and were repointed only after
# verification against the reads built from them -- R9.6a's requirement, because a
# same-named file is not the same file.
_MADUEKE = (REPO / "imports/Scripture/Bibles/DouayRheims_DR/sources/transcriptions/madueke")

#: VERIFIED 2026-08-14. All 1334 chapter <title>s match the loci in madueke_a.json, and
#: **all 35,809 recorded verses appear verbatim** (100.0000%, whole corpus, after
#: stripping <sup> verse markers and the `^` annotation anchors the reads also strip).
MADUEKE_A = _MADUEKE / "raw-a-webscrape" / "books"

#: 🔴 REFUTED 2026-08-14 as the source of madueke_b.json: only **2.05%** of the 35,809
#: recorded verses appear in it. `madueke_b.json` records `locus: madueke-b/pdf` and
#: `method: pdf-bbox-two-column` -- it was built from the PDF below by de-interleaving
#: the two columns, exactly as `projects/originaldr/ingest_madueke_b.py` documents.
#: `merged.txt` is the RAW `pdftotext` dump taken BEFORE de-interleaving, so its verse
#: text is spliced across columns ("In the beginning God created heaven and *fruit after
#: his kind*..."). Repointing a verse-comparing consumer at it on the strength of the
#: matching filename would silently corrupt every comparison. See R9.6b.
MADUEKE_B_PDF = _MADUEKE / "madueke-b__Original-Douay-Rheims-Bible-Merged.pdf"
MADUEKE_B_RAW_INTERLEAVED = _MADUEKE / "raw-b-extract" / "merged.txt"


def require(path: Path, what: str) -> Path:
    """Return `path`, or raise naming it and the reason it is not simply created.

    Used for READ roots. A writer may create its own output directory; a reader that
    creates a missing input directory manufactures the evidence of its own success.
    """
    if path.exists():
        return path
    hint = ""
    legacy = LEGACY_ROOT / path.relative_to(ORIGINALDR) if _under_root(path) else None
    if legacy is not None and legacy.exists():
        hint = (f"\nNOTE: it DOES exist under the pre-2633cbb root {legacy} -- the "
                f"migration is incomplete, do not repoint at the legacy tree.")
    raise FileNotFoundError(
        f"{what}: {path} does not exist.{hint}\n"
        f"Project root is {ORIGINALDR} (override with $ORIGINALDR_ROOT). This is a "
        f"READ root and is deliberately not created on demand: a reader that mkdirs "
        f"its own input reports success over an empty directory (R9.6)."
    )


def _under_root(path: Path) -> bool:
    try:
        path.relative_to(ORIGINALDR)
        return True
    except ValueError:
        return False


def assert_not_legacy() -> None:
    """Fail loudly if the dead tree has been recreated -- by an old checkout, a stale
    script, or one of the four writers run before this module existed."""
    if LEGACY_ROOT.exists():
        raise RuntimeError(
            f"the pre-2633cbb root has REAPPEARED: {LEGACY_ROOT}\n"
            f"Nothing reads it. It is created only by a module still restating the old "
            f"literal and calling mkdir(parents=True) -- find that module before trusting "
            f"any artefact written since. Live root: {ORIGINALDR}"
        )

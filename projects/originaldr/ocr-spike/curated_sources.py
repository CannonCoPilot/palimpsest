#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""curated_sources.py — the SINGLE source of truth for the OriginalDR source allowlist (Sir, 2026-07-22).

Only S1, S3, S4, S6, S8, S9 may touch ANY stage of the OriginalDR project (train / test / reOCR / report /
divergence / production). S2, S5, S7, S10-S15 (and every derivative) are BANNED — no silent reinclusion.

Any builder that sweeps sources (`build_tome_map`, `qc_audit`, `consensus_v2`, report, divergence) MUST filter
through `is_curated()` / `assert_curated()` so a banned folder can never re-enter by a directory glob. This
mirrors the hard gate already in `jp2_page.OCR_DIR_TO_JP2` (which KeyErrors on non-curated ocr_dirs).
"""
from __future__ import annotations

# Canonical scan sources permitted for ALL work.
CURATED: frozenset[str] = frozenset({"S1", "S3", "S4", "S6", "S8", "S9"})
BANNED: frozenset[str] = frozenset({"S2", "S5", "S7", "S10", "S11", "S12", "S13", "S14", "S15"})

# ocr_dir folder → source id (the curated map; must stay in sync with jp2_page.OCR_DIR_TO_JP2).
# ocr_dirs NOT listed here are treated as banned/unknown and rejected.
OCR_DIR_SOURCE: dict[str, str] = {
    "archive-ot1-1609": "S1", "archive-ot2-1610": "S1", "archive-nt-1582": "S1",
    "pdf-S03a": "S3", "pdf-S03b": "S3",
    "jp2-S04": "S4",
    "jp2-S06": "S6",
    "jp2-S08": "S8",
    "pdf-S09nt": "S9", "archive-holiebible-ot1": "S9", "archive-holiebible-ot2": "S9",
}

# Banned ocr_dir folders (physically present as OCR derivatives until purged) — reject on sight.
BANNED_OCR_DIRS: frozenset[str] = frozenset({
    "eebo-nt", "eebo-vol1", "eebo-vol2", "eebo-vol3", "eebo-vol4", "eebo-vol5",  # S10-S15
    "pdf-S02",                                                                    # S2
    "archive-newtestament",                                                       # S5
})


def source_of(ocr_dir: str) -> str | None:
    """Curated source id for an ocr_dir, or None if unknown/banned."""
    return OCR_DIR_SOURCE.get(ocr_dir)


def is_curated(ident: str) -> bool:
    """True iff `ident` (a source id like 'S3' OR an ocr_dir like 'jp2-S04') is in the curated allowlist."""
    if ident in CURATED:
        return True
    return OCR_DIR_SOURCE.get(ident) in CURATED


def assert_curated(ident: str) -> str:
    """Return the curated source id for `ident`, or raise. Use at every source-ingest boundary so a banned
    source loudly fails instead of silently polluting (No Silent Degradation)."""
    if ident in CURATED:
        return ident
    src = OCR_DIR_SOURCE.get(ident)
    if src in CURATED:
        return src
    raise ValueError(
        f"BANNED/unknown source '{ident}': only S1,S3,S4,S6,S8,S9 (and their curated ocr_dirs) are permitted. "
        f"See curated_sources.py / SIR-DIRECTIVE-2026-07-19.md."
    )


def filter_curated(idents):
    """Filter an iterable of source ids / ocr_dirs down to the curated ones (drops banned silently — for use
    when you explicitly want the curated subset, e.g. iterating a directory listing)."""
    return [i for i in idents if is_curated(i)]


if __name__ == "__main__":
    # self-check
    assert is_curated("S1") and is_curated("jp2-S04") and is_curated("archive-holiebible-ot1")
    assert not is_curated("S10") and not is_curated("eebo-vol4") and not is_curated("pdf-S02")
    assert source_of("archive-holiebible-ot1") == "S9"      # NOT S3 (common mislabel)
    for bad in ("eebo-nt", "pdf-S02", "S5"):
        try:
            assert_curated(bad); raise SystemExit(f"FAIL: {bad} not rejected")
        except ValueError:
            pass
    print("curated_sources self-check PASS:", sorted(CURATED))

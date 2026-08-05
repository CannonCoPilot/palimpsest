#!/usr/bin/env python3
"""Pilot check: does the contiguity fix (inline-annotation separation) make eebo-vol4 Psalms localize?

Loads the eebo-vol4 stream, runs detect_book('psalms'), reports inline-annotation lines rerouted, the
mid-chapter probe recall (vs the old BOOK_ALIAS_FLOOR=0.35 that dropped the book), and attested verses.
Also lets us A/B the fix by monkeypatching _is_inline_annotation off.
"""
from __future__ import annotations
import sys
from pathlib import Path

RECON = Path("/Users/nathanielcannon/Claude/Projects/palimpsest/core/tests/fixtures/gold/"
             "mask_engine/originaldr_reconstruction")
sys.path.insert(0, str(RECON))
import detect_our_ocr as D  # type: ignore[import-not-found]

DIP = D.DIPL_ROOT / "eebo-vol4"
anchor = D.anchor_by_book(D.load_anchor())
psalms = anchor.get("psalms")
assert psalms, "no psalms anchor"
n_expected = sum(len(vs) for vs in psalms.values())
n_chapters = len(psalms)


def run(label: str, annotation_fix: bool) -> None:
    orig = D._is_inline_annotation
    if not annotation_fix:
        D._is_inline_annotation = lambda *_: False  # type: ignore[assignment]
    try:
        st = D.load_stream(DIP, "vol4", 2)
        streams = {"vol4": st}
        alias, probe_recall = D.resolve_alias("psalms", psalms, streams)
        reads, _, meta = D.detect_book("psalms", psalms, "annas", streams)
        located_ch = len({r["skeleton_id"].split("/")[2] for r in reads
                          if r["skeleton_id"].startswith("scripture/psalms/")})
        print(f"\n=== {label} (annotation_fix={annotation_fix}) ===")
        print(f"  body_tok={len(st.fold):,}  inline_annot_lines={st.n_inline_annot_lines}  "
              f"margin_lines={st.n_margin_lines}  ſ={st.long_s:,}")
        print(f"  resolve_alias -> alias={alias!r} probe_recall={probe_recall}  (old drop floor was 0.35)")
        print(f"  attested_verses={meta['attested_verses']}/{n_expected}  "
              f"attestation_rate={meta['attestation_rate']}  covered={meta['covered']}")
        print(f"  psalms chapters with >=1 attested verse: {located_ch}/{n_chapters}")
        print(f"  apparatus_words captured={meta['apparatus_words']}")
    finally:
        D._is_inline_annotation = orig  # type: ignore[assignment]


run("BEFORE fix (geometry-only)", annotation_fix=False)
run("AFTER fix (content signal)", annotation_fix=True)

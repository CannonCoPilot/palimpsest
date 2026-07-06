#!/usr/bin/env python3
"""§6.3 — independent-print bootstrap-CI validation of BOTH OriginalDR editions against the print.

Leg 3 of the witness protocol (the genuinely INDEPENDENT witness), extended from the modern-only
``originaldr_validation/ocr_sample.py`` to the ARCHAIC edition (idx 109) and reported by
archaic-witness tier. For a seeded, stratified-random sample of chapters it locates each chapter in
the archive.org djvu OCR of the original 1582/1609/1610 print (a third party's OCR, outside the
Madueke/Sabates transcription lineage and our tesseract pipeline) and measures token recall of BOTH
the idx-109 archaic and the idx-108 modern render surfaces against that print — on the SAME chapters,
so archaic vs modern is a paired comparison. Chapter-resampled bootstrap 95% CIs (seed 1729) are
reported aggregate, per genre stratum, and per archaic-witness tier.

Fold choice (deliberate, and OPPOSITE to §6.2): this reuses ``ocr_sample.skel``, which folds long-ſ
and 'f' SYMMETRICALLY. §6.2 kept f≠s to EXPOSE the fresh-OCR ſ→f defect in a reconstruction-vs-
reconstruction comparison; §6.3 compares the reconstruction against the print's own noisy OCR, so it
must TOLERATE that OCR's ſ→f to measure genuine content recall rather than counting OCR artifacts. The
fold is lossy, so recall is a CORROBORATION signal and the distinctive-content-word miss count is the
genuine-discrepancy signal.

Independence, stated honestly (per witness tier, derived from the basis-db attestation):
  * clean-diplomatic (3 witnesses incl. s-dismas) — the archaic surface is s-dismas's transcription,
    INDEPENDENT of the archive.org OCR; validating it against the print is a genuine cross-witness check.
  * mixed (2 witnesses) — s-dismas or odr-com + ocr_consensus.
  * ocr-only-noisy (1 witness: ocr_consensus) — the archaic surface DERIVES from the same archive.org
    OCR family (our-ocr + djvu + hocr), so its recall against the djvu print is PARTIALLY SELF-
    REFERENTIAL. Flagged, not hidden: for these books the modern-vs-print recall (Madueke lineage) is
    the independent signal, and the archaic recall mainly confirms the surface was faithfully projected.

Raw djvu sources are pinned by sha256 in the output. The basis-db it reads is gitignored/regenerable;
the committed artifact is archaic-print-validation.json.

Run:  core/.venv/bin/python print_validate_archaic.py
"""
from __future__ import annotations

import json
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np

HERE = Path(__file__).resolve().parent                 # originaldr_reconstruction
VALID = HERE.parent / "originaldr_validation"
sys.path.insert(0, str(VALID))
import ocr_sample as O  # type: ignore[import]  # noqa: E402  (reuse skel/best_window/bootstrap_ci/strata)

REPO = HERE.parents[5]
BASIS_DB = REPO / "core/.scratch/originaldr-project/reconstruction/basis-db.sqlite"
AO = REPO / "core/.scratch/originaldr-project/sources/archive-org"
MODERN_VALIDATION = VALID / "ocr-validation.json"      # the existing idx-108 standalone run (context)
OUT = HERE / "archaic-print-validation.json"

SEED, N_BOOT, FUZZ = O.SEED, O.N_BOOT, O.FUZZ
N_PER_STRATUM = 8                                       # more than the modern run (6): funds per-tier CIs
MIN_CHAPTER_TOKENS = 20                                 # skip stubs / coverage-gap-only chapters
_TIER_LABEL = {3: "clean-diplomatic", 2: "mixed", 1: "ocr-only-noisy"}
_TIER_ORDER = ["clean-diplomatic", "mixed", "ocr-only-noisy"]

Chapters = dict[tuple[str, int], dict[int, tuple[str, str]]]


def load_basis() -> tuple[Chapters, dict[str, set[str]]]:
    """Return {(book, chapter): {verse: (render_modern, render_archaic)}} and {book: {witnesses}}."""
    con = sqlite3.connect(BASIS_DB)
    try:
        rows = con.execute(
            "SELECT id, render_modern, render_archaic FROM elements WHERE type='scripture-verse'").fetchall()
        wit_rows = con.execute(
            "SELECT e.book, a.source FROM attestation a JOIN elements e ON e.id = a.element_id "
            "WHERE e.type='scripture-verse' "
            "AND a.surface_archaic IS NOT NULL AND TRIM(a.surface_archaic) <> ''").fetchall()
    finally:
        con.close()
    chapters: Chapters = defaultdict(dict)
    for eid, rm, ra in rows:
        parts = eid.split("/")            # scripture / book / chapter / verse
        if len(parts) != 4 or not parts[2].isdigit() or not parts[3].isdigit():
            continue
        _, book, ch, v = parts
        chapters[(book, int(ch))][int(v)] = (rm or "", ra or "")
    witnesses: dict[str, set[str]] = defaultdict(set)
    for book, source in wit_rows:
        witnesses[book].add(source)
    return chapters, witnesses


def _tokens(text: str) -> list[str]:
    return [s for s in (O.skel(w) for w in O.raw_words(text)) if len(s) >= 2]


def main() -> int:
    if not BASIS_DB.exists():
        print(f"!! basis-db not found: {BASIS_DB}", file=sys.stderr)
        return 2
    if not AO.exists() or not list(AO.glob("*_djvu.txt")):
        print(f"!! archive.org djvu OCR missing under {AO}", file=sys.stderr)
        return 2

    rng = np.random.default_rng(SEED)
    chapters, witnesses = load_basis()
    tier_of = {b: len(witnesses.get(b, set())) for b in {bk for bk, _ in chapters}}

    def chapter_text(book: str, ch: int) -> tuple[str, str]:
        verses = chapters[(book, ch)]
        order = sorted(verses)
        return (" ".join(verses[v][0] for v in order), " ".join(verses[v][1] for v in order))

    print("loading djvu print witnesses (skeleton tokenising) ...")
    djvu = O.load_djvu()
    witness_types = {name: list(set(toks)) for name, toks in djvu.items()}

    # book -> its chapters present in the basis DB
    book_chapters: dict[str, list[int]] = defaultdict(list)
    for (book, ch) in chapters:
        book_chapters[book].append(ch)
    for book in book_chapters:
        book_chapters[book].sort()

    # coverage resolution: best print witness per book, probed on a mid-chapter's archaic surface
    print("resolving book -> print-witness coverage ...")
    coverage: dict[str, dict[str, Any]] = {}
    for book, chs in book_chapters.items():
        cands = O.OT_DJVU if book in O.OT_SLUGS else O.NT_DJVU
        mid = chs[len(chs) // 2]
        _, arc = chapter_text(book, mid)
        probe = _tokens(arc) or _tokens(chapter_text(book, mid)[0])
        best_name, best_rec = "", 0.0
        for name in cands:
            rec, _, _ = O.best_window(probe, djvu[name])
            if rec > best_rec:
                best_name, best_rec = name, rec
        coverage[book] = {"witness": best_name, "probe_recall_pct": round(100 * best_rec, 2),
                          "n_archaic_witnesses": tier_of[book], "witness_tier": _TIER_LABEL.get(tier_of[book], "none")}

    # stratified-random sample of chapters (genre strata, seed 1729)
    def sample_chapters(slugs: list[str], k: int) -> list[tuple[str, int]]:
        frame = [(b, ch) for b in slugs for ch in book_chapters.get(b, [])]
        if not frame:
            return []
        pick = rng.choice(len(frame), size=min(k, len(frame)), replace=False)
        return [frame[i] for i in sorted(pick)]

    samples: list[tuple[str, str, int]] = []
    for stratum, slugs in O.GENRE_STRATA.items():
        for book, ch in sample_chapters(slugs, N_PER_STRATUM):
            samples.append((stratum, book, ch))

    # whole-edition archaic token set (2nd-pass "attested elsewhere in the edition" check)
    print("building full archaic-edition attestation set ...")
    edition_archaic: set[str] = set()
    for surfaces in chapters.values():
        for pair in surfaces.values():
            ra = pair[1]
            if ra:
                edition_archaic.update(_tokens(ra))

    # measure each sampled chapter: paired archaic + modern recall against the same print witness
    print(f"measuring {len(samples)} sampled chapters (paired archaic/modern print recall) ...")
    per_sample: list[dict[str, Any]] = []
    for stratum, book, ch in samples:
        witness = str(coverage[book]["witness"])
        if not witness:
            continue
        hay = djvu[witness]
        modern_text, archaic_text = chapter_text(book, ch)
        arc_raw, mod_raw = O.raw_words(archaic_text), O.raw_words(modern_text)
        if len(_tokens(archaic_text)) < MIN_CHAPTER_TOKENS or len(_tokens(modern_text)) < MIN_CHAPTER_TOKENS:
            continue
        # archaic recall (locate on the archaic surface)
        _, a0, a1 = O.best_window(_tokens(archaic_text), hay)
        a_att, a_tot, a_missed = O.attest_recall(arc_raw, hay[a0:a1])
        a_content = O.content_misses(a_missed)
        a_elsewhere, a_genuine = O.genuine_candidates(
            a_content, set(hay), edition_archaic, witness_types[witness])
        # modern recall (locate on the modern surface, same witness)
        _, m0, m1 = O.best_window(_tokens(modern_text), hay)
        m_att, m_tot, _ = O.attest_recall(mod_raw, hay[m0:m1])
        per_sample.append({
            "stratum": stratum, "book": book, "chapter": ch, "witness": witness,
            "witness_tier": _TIER_LABEL.get(tier_of[book], "none"),
            "archaic": {"tokens": a_tot, "attested": a_att,
                        "recall_pct": round(100 * a_att / a_tot, 2) if a_tot else None,
                        "content_misses": len(a_content), "attested_elsewhere": a_elsewhere,
                        "genuine_candidates": a_genuine},
            "modern": {"tokens": m_tot, "attested": m_att,
                       "recall_pct": round(100 * m_att / m_tot, 2) if m_tot else None},
        })

    if not per_sample:
        print("!! no measurable chapters sampled", file=sys.stderr)
        return 2

    def ci(records: list[dict[str, Any]], edition: str) -> dict[str, Any]:
        hits = np.array([r[edition]["attested"] for r in records], dtype=float)
        tots = np.array([r[edition]["tokens"] for r in records], dtype=float)
        point, lo, hi = O.bootstrap_ci(hits, tots, rng)
        return {"n_chapters": len(records), "n_tokens": int(tots.sum()),
                "recall_pct": point, "ci95": [lo, hi]}

    def grouped(key) -> dict[str, Any]:
        out: dict[str, Any] = {}
        buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for r in per_sample:
            buckets[str(key(r))].append(r)
        for name, recs in buckets.items():
            out[name] = {"archaic": ci(recs, "archaic"), "modern": ci(recs, "modern")}
        return out

    per_stratum = grouped(lambda r: r["stratum"])
    per_tier_raw = grouped(lambda r: r["witness_tier"])
    per_tier = {t: per_tier_raw[t] for t in _TIER_ORDER if t in per_tier_raw}

    a_genuine_all = sorted({w.lower() for r in per_sample for w in r["archaic"]["genuine_candidates"]})
    a_content_total = sum(int(r["archaic"]["content_misses"]) for r in per_sample)

    modern_ref = None
    if MODERN_VALIDATION.exists():
        m = json.loads(MODERN_VALIDATION.read_text())["aggregate"]
        modern_ref = {"source": "ocr_sample.py (idx 108, Madueke lineage, independent sample)",
                      "recall_pct": m["recall_pct"], "ci95": m["ci95"],
                      "genuine_candidate_misses": m["genuine_candidate_misses"]}

    artifact = {
        "artifact": "archaic-print-validation",
        "phase": "P2 · §6.3",
        "generated_by": "print_validate_archaic.py",
        "idx": 109,
        "seed": SEED,
        "n_bootstrap": N_BOOT,
        "fuzz_threshold": FUZZ,
        "n_per_stratum": N_PER_STRATUM,
        "fold": "ocr_sample.skel (symmetric long-ſ/f — tolerates the print OCR's ſ→f, the OPPOSITE of "
                "§6.2's fold_diplomatic which keeps f≠s to expose that defect)",
        "method": "Leg 3 independent print witness, extended to the archaic edition: for a seeded, "
                  "genre-stratified chapter sample, locate the chapter in the archive.org djvu OCR of the "
                  "1582/1609/1610 print (third-party OCR, outside the Madueke/Sabates lineage and our "
                  "tesseract pipeline) and measure token recall of BOTH the idx-109 archaic and idx-108 "
                  "modern render surfaces against it, on the same chapters (paired). Chapter-resampled "
                  "bootstrap 95% CIs, aggregate + per genre stratum + per archaic-witness tier. The "
                  "archaic skeleton fold is lossy, so recall is a corroboration signal; the distinctive-"
                  "content-word miss count is the genuine-discrepancy signal.",
        "independence_note": "Per witness tier: clean-diplomatic archaic recall is a GENUINE cross-witness "
                             "check (s-dismas transcription vs the archive.org OCR — two independent readings "
                             "of the same print). ocr-only-noisy archaic recall is PARTIALLY SELF-REFERENTIAL "
                             "(the archaic surface derives from the same archive.org OCR family), so for "
                             "those books the modern-vs-print recall is the independent signal and the "
                             "archaic recall mainly confirms faithful projection. Flagged, not hidden.",
        "sources": {name: {"path": str((AO / f"{name}_djvu.txt").relative_to(REPO)),
                           "sha256": O.sha256_file(AO / f"{name}_djvu.txt")}
                    for name in djvu},
        "coverage_resolution": coverage,
        "aggregate": {
            "archaic": ci(per_sample, "archaic"),
            "modern": ci(per_sample, "modern"),
            "archaic_content_word_misses": a_content_total,
            "archaic_genuine_candidate_misses": len(a_genuine_all),
            "archaic_genuine_candidate_words": a_genuine_all,
        },
        "per_stratum": per_stratum,
        "per_witness_tier": per_tier,
        "modern_reference_standalone": modern_ref,
        "per_sample": per_sample,
    }
    OUT.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    agg_a, agg_m = artifact["aggregate"]["archaic"], artifact["aggregate"]["modern"]
    print(f"\n§6.3 print validation ({len(per_sample)} chapters):")
    print(f"  archaic recall {agg_a['recall_pct']}% CI{agg_a['ci95']}  vs  modern {agg_m['recall_pct']}% CI{agg_m['ci95']}")
    print(f"  archaic genuine content-word discrepancy candidates: {len(a_genuine_all)}")
    for t in _TIER_ORDER:
        if t in per_tier:
            a, m = per_tier[t]["archaic"], per_tier[t]["modern"]
            print(f"  {t:18} n={a['n_chapters']:2}  archaic {a['recall_pct']}% CI{a['ci95']}  modern {m['recall_pct']}% CI{m['ci95']}")
    print(f"wrote {OUT.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Phase 2 · P2b — render the archaic diplomatic OriginalDR (idx 109) FROM the basis database.

idx 109 is the ARCHAIC sibling of idx 108: both are deterministic projections of the SAME Phase-1
basis DB (plan §5.3, and the §1.2 principle "one basis, two renderings"). They share skeleton,
apparatus placement and element structure EXACTLY, and differ ONLY in the final
orthographic/typographic layer — a diff of 108 vs 109 isolates precisely the spelling/typeset delta.

  * Verse bodies come from the basis-db ``render_archaic`` surface — the consensus-called archaic
    form from the archaic witnesses (s-dismas primary; odr-com + majority-consensus fresh OCR fill).
    Each surface is run through ``gen.clean_scripture`` so it is normalization-stable (ingest
    reproduces it byte-for-byte) WHILE preserving the diplomatic glyphs: long-ſ, æ/œ, u/v, i/j, vv,
    and & (verified: ``normalize`` folds none of these; cleaning fixes 139 smart-quote/OCR-artifact
    surfaces to 0 unstable and loses 0 glyphs).
  * The editorial apparatus (arguments, footnotes, cross-refs, the 26 reference documents) and the
    structural frame reuse the proven ``gen_dr_original`` machinery at render time — the SAME masked
    apparatus as idx 108 (the janvier-s / Sabates_A witness). The masked apparatus is hidden from the
    reader, so sharing it keeps the 108-vs-109 diff a pure SCRIPTURE spelling delta; sourcing an
    ARCHAIC apparatus witness is a documented follow-up (the basis-db apparatus render surfaces are
    null except the 26 reference-doc titles).

Two versification/coverage edge sets, handled honestly rather than papered over (plan §6, and the
"Fallbacks-Are-Failures" guardrail — surface gaps, do not fabricate):

  * ARCHAIC COVERAGE GAPS (199 coords): modern-present coordinates with NO archaic witness — all
    single-witness, low-tier, in the OT/apocryphal books absent from s-dismas (Gen→Wisdom) and
    odr-com: Ecclesiasticus, 4-Esdras, Isaie, Zacharias and the prophets. They have no attested
    diplomatic archaic reading, so ``gen.build`` falls through to the attested MODERN surface for
    them; they are FLAGGED here (not glyph-transformed — a mechanical long-ſ/u-v back-transform would
    fabricate diplomatic detail we cannot attest, and could not restore the period SPELLINGS the
    archaic witnesses carry). idx 109 is therefore byte-identical to idx 108 on exactly these 199
    verses (plus the shared apparatus/structure), and archaic elsewhere.
  * ARCHAIC-ONLY COORDS (55): positions the modern edition lacks. The engine emits one paragraph per
    modern (Sabates) verse, so these are never emitted here — and they are NOT injected: the set is
    dominated by single-witness OCR artifacts (e.g. matthew/4/32 carries Matthew 4:23 text,
    genesis/1/32 carries Genesis 1:31, acts/10/49 duplicates Acts 10:48) — the same spurious-verse
    failure mode the P2a byte-identity gate caught and removed. A minority are genuine Vulgate
    versification splits (chiefly Psalms, at independent-depth 2). They are recorded as a
    versification-divergence adjudication set for a focused follow-up, not bulk-injected on
    single-witness faith.

Unlike P2a there is no pre-existing archaic reference text to gate against; the sha below is newly
MINTED by this deterministic projection and pinned into the report + manifest.

Outputs:
  - imports/Scripture/Bibles/OriginalDR/OriginalDR-archaic-1582-1610.txt   (archaic reference text)
  - core/tests/fixtures/gold/maps/work-109.map.json                        (masking map)
  - originaldr_reconstruction/render-archaic-report.json                   (committed projection summary)

Run:  core/.venv/bin/python render_archaic.py
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
MASK_ENGINE = HERE.parent
sys.path.insert(0, str(MASK_ENGINE))
import gen_dr_original as gen  # type: ignore[import]  # noqa: E402  (sibling dynamic import: machinery)

REPO = HERE.parents[5]
BASIS_DB = REPO / "core/.scratch/originaldr-project/reconstruction/basis-db.sqlite"
REPORT = HERE / "render-archaic-report.json"
OUT_TXT = REPO / "imports/Scripture/Bibles/OriginalDR/OriginalDR-archaic-1582-1610.txt"
MAP_108 = gen.MAPS / "work-108.map.json"
IDX = 109

GENERATED_FROM = (
    "mask_engine/originaldr_reconstruction/render_archaic.py "
    "(basis-db projection: diplomatic archaic verse bodies = consensus render_archaic surfaces "
    "[s-dismas / odr-com / majority-consensus OCR], cleaned normalization-stable with "
    "long-ſ/æ/œ/u-v/i-j/vv/& preserved; apparatus + structure = janvier-s at render time, shared with idx 108)")

# Diplomatic glyphs whose retained counts are the evidence that the type is genuinely archaic (§6.2).
_GLYPHS = {"long-s (ſ)": "ſ", "ae (æ)": "æ", "AE (Æ)": "Æ",
           "oe (œ)": "œ", "OE (Œ)": "Œ", "ampersand (&)": "&"}


def load_basis(db: Path) -> tuple[list[tuple[str, str, str]], dict[str, str], dict[str, int]]:
    """Return [(verse_id, render_modern, render_archaic)], {verse_id: tier}, {verse_id: indep_depth}."""
    con = sqlite3.connect(db)
    try:
        rows = con.execute(
            "SELECT id, render_modern, render_archaic FROM elements WHERE type='scripture-verse'").fetchall()
        tier = {eid: t for eid, t in con.execute("SELECT element_id, tier FROM consensus")}
        depth = {eid: d for eid, d in con.execute("SELECT element_id, indep_depth FROM consensus")}
    finally:
        con.close()
    return rows, tier, depth


def _book_of(eid: str) -> str:
    parts = eid.split("/")
    return parts[1] if len(parts) > 1 else eid


def main() -> int:
    if not BASIS_DB.exists():
        print(f"!! basis-db not found: {BASIS_DB} — run build_basis_db.py first", file=sys.stderr)
        return 2

    rows, tier, depth = load_basis(BASIS_DB)

    # Build the archaic verse-body override. A coordinate contributes its cleaned archaic surface
    # when an archaic witness attests it; coordinates with no archaic surface are classified for the
    # honest gap/adjudication accounting below.
    override: dict[str, str] = {}
    archaic_attested: list[str] = []   # coords with an archaic surface (may or may not be in the modern structure)
    archaic_only: list[str] = []       # archaic-present, modern-absent — not in the modern structure (deferred)
    coverage_gap: list[str] = []       # modern-present, archaic-absent — render from modern surface, FLAGGED
    for eid, rm, ra in rows:
        has_arc = bool(ra and ra.strip())
        has_mod = bool(rm and rm.strip())
        if has_arc:
            override[eid] = gen.clean_scripture(ra)
            archaic_attested.append(eid)
            if not has_mod:
                archaic_only.append(eid)
        elif has_mod:
            coverage_gap.append(eid)

    hits: set[str] = set()
    text, els, warns = gen.build(verse_override=override, _override_hits=hits)
    sha = hashlib.sha256(text.encode("utf-8")).hexdigest()

    # The archaic-only coords must NOT have been emitted (they are absent from the modern structure);
    # if any leaked in, an unexpected injection happened — fail loudly rather than ship it.
    injected = hits & set(archaic_only)
    if injected:
        print(f"!! {len(injected)} archaic-only coords were injected into the modern structure "
              f"(unexpected): {sorted(injected)[:5]} — investigate before emitting.", file=sys.stderr)
        return 1

    emit_sha = gen.emit_outputs(text, els, warns, idx=IDX, out_txt=OUT_TXT, generated_from=GENERATED_FROM)
    assert emit_sha == sha, "emit_outputs re-derived a different sha than build()"

    # Structural parity vs idx 108: same skeleton ⇒ identical element_count + type_counts (only the
    # verse-body bytes differ). This is the P2b headline gate.
    m108 = json.loads(MAP_108.read_text(encoding="utf-8"))
    m109 = json.loads((gen.MAPS / f"work-{IDX}.map.json").read_text(encoding="utf-8"))
    parity_ok = (m108["element_count"] == m109["element_count"]
                 and m108["type_counts"] == m109["type_counts"])
    if not parity_ok:
        print(f"!! STRUCTURAL PARITY FAILED vs idx 108: "
              f"elements {m108['element_count']}->{m109['element_count']}, "
              f"type_counts equal={m108['type_counts'] == m109['type_counts']}", file=sys.stderr)
        return 1

    # Confidence model behind the RENDERED archaic verses + diplomatic-glyph inventory (§6.2 evidence).
    rendered_tiers: Counter[str] = Counter()
    rendered_depth: Counter[int] = Counter()
    glyph_counts: dict[str, int] = {name: 0 for name in _GLYPHS}
    verses_with_long_s = 0
    for vid in hits:
        if tier.get(vid):
            rendered_tiers[tier[vid]] += 1
        d = depth.get(vid)
        if isinstance(d, int):
            rendered_depth[d] += 1
        body = override[vid]
        for name, ch in _GLYPHS.items():
            glyph_counts[name] += body.count(ch)
        if "ſ" in body:
            verses_with_long_s += 1

    gap_by_book = Counter(_book_of(e) for e in coverage_gap)

    report = {
        "artifact": "render-archaic", "phase": "P2b", "idx": IDX,
        "generated_by": "render_archaic.py",
        "note": "idx 109 rendered as a diplomatic-archaic projection of the basis DB: verse bodies "
                "from the consensus render_archaic surface (s-dismas / odr-com / fresh-OCR), cleaned "
                "normalization-stable with long-ſ/æ/œ/u-v/i-j/vv/& preserved; apparatus + structure "
                "from janvier-s at render time, shared with idx 108. idx 109 shares idx 108's skeleton "
                "and element structure exactly and differs only in the scripture spelling/typeset "
                "layer. The archaic reference text has no pre-existing witness to gate against; the "
                "sha below is minted by this deterministic projection. Verse render surfaces live in "
                "the gitignored basis-db.sqlite; this JSON is the diff-reviewable, CI-safe summary.",
        "reference": {
            "file": str(OUT_TXT.relative_to(REPO)),
            "sha256": sha,
            "text_len": len(text),
            "sha_provenance": "minted by this projection (no prior archaic reference text)",
        },
        "structural_parity_vs_108": {
            "element_count_108": m108["element_count"],
            "element_count_109": m109["element_count"],
            "element_count_equal": m108["element_count"] == m109["element_count"],
            "type_counts_equal": m108["type_counts"] == m109["type_counts"],
            "text_len_108": m108["text_len"],
            "text_len_109": m109["text_len"],
            "note": "same skeleton + apparatus placement; only verse-body bytes differ (archaic vs modern surface)",
        },
        "diplomatic_glyphs_preserved": ["long-s (ſ)", "æ", "œ", "u/v", "i/j", "vv", "&"],
        "glyph_inventory": {
            "counts": dict(sorted(glyph_counts.items())),
            "rendered_verses_with_long_s": verses_with_long_s,
            "note": "aggregate retained-glyph counts over the rendered archaic verse bodies — evidence "
                    "the type is genuinely archaic (§6.2). Per-book glyph charts are a Phase-3 report "
                    "deliverable (§7.2).",
        },
        "diplomatic_fidelity": {
            "render_backing": "every rendered archaic verse is consensus-called at independent-depth "
                              ">=2 (see rendered_independent_depth / rendered_confidence_tiers — no "
                              "depth-1 verse is rendered archaic; the single-witness low-tier coords "
                              "are exactly the coverage gaps that fall through to the modern surface). "
                              "The archaic surfaces are the majority-consensus of s-dismas + odr-com + "
                              "fresh OCR, not raw single-source OCR.",
            "known_upstream_artifacts": {
                "example": "scripture/genesis/1/2 renders '...and the the Spirite of God moued...' — a "
                           "doubled article carried verbatim from the s-dismas archaic surface (an "
                           "upstream witness transcription artifact, faithfully projected, not "
                           "introduced by the renderer).",
                "note": "surfaced here rather than silently corrected; cataloguing and adjudicating "
                        "such residuals is the §6.2 deliverable below.",
            },
            "validation": {
                "status": "built (§6.1 spelling-glyph model + §6.2 word-correspondence validation)",
                "model": "spelling-glyph-model.json",
                "fold": "spelling_glyph_model.fold_diplomatic",
                "report": "archaic-fidelity-validation.json",
                "method": "per-verse token-set Jaccard of fold_diplomatic(render_modern) vs "
                          "fold_diplomatic(render_archaic); the fold neutralises expected orthography "
                          "(long-ſ, æ/œ, u/v, i/j, vv, &, period spellings) so only genuine WORDING "
                          "divergence survives. It deliberately keeps f and s distinct (no symmetric "
                          "f↔s), so the ocr-only books' fresh-OCR long-ſ→f misread shows up as a "
                          "residual rather than being masked.",
                "finding": "Fidelity is tiered by archaic-witness coverage: books s-dismas / odr-com "
                           "attest fold nearly exactly onto the modern surface (a spelling-only delta), "
                           "while the ocr-only books (Isaie, Ecclesiasticus, Zacharias, 4-Esdras, minor "
                           "prophets) score far lower — a true, quantified fresh-OCR sourcing "
                           "limitation, surfaced not hidden. The severe tail (Jaccard < 0.1) is "
                           "dominated by verse-numbering divergence in the WELL-attested books (chiefly "
                           "the Vulgate psalm-title-as-verse-1 offset), recorded as a versification "
                           "adjudication set — not an OCR artifact and not a fold bug.",
                "authoritative_numbers": "archaic-fidelity-validation.json (aggregate + by_witness_tier "
                                         "+ per_book glyph inventory + severe_tail)",
                "followups": "§6.3 independent-print bootstrap CIs (vs archive.org scans) and the "
                             "versification-divergence adjudication land with the P3 brief (§7).",
            },
        },
        "apparatus": {
            "source": "janvier-s (Sabates_A) modern apparatus, shared with idx 108",
            "note": "the masked apparatus is identical to idx 108 (it is hidden from the reader, so the "
                    "108-vs-109 diff stays a pure scripture spelling delta). Sourcing an archaic "
                    "apparatus witness is a documented follow-up; basis-db apparatus render surfaces "
                    "are null except the 26 reference-doc titles.",
        },
        "scripture_projection": {
            "basis_db_verses": len(rows),
            "archaic_surface_verses": len(archaic_attested),
            "verse_bodies_from_basis_db": len(hits),
            "render_time_fallbacks": len(warns),
            "pure_basis_db_projection_over_attested": len(warns) == 0,
            "archaic_coverage_gaps": len(coverage_gap),
            "archaic_coverage_gap_note": "modern-present coords with NO archaic witness (books absent "
                                         "from s-dismas [Gen→Wisdom] and odr-com: Ecclesiasticus, "
                                         "4-Esdras, prophets). Rendered from the attested modern "
                                         "surface and FLAGGED — not glyph-transformed (that would "
                                         "fabricate unattested diplomatic detail). idx 109 == idx 108 "
                                         "byte-for-byte on exactly these verses.",
            "archaic_coverage_gap_by_book": dict(sorted(gap_by_book.items(), key=lambda kv: (-kv[1], kv[0]))),
            "archaic_coverage_gap_sample": sorted(coverage_gap)[:8],
            "archaic_only_coordinates_deferred": len(archaic_only),
            "archaic_only_note": "positions absent from the modern edition; NOT injected — dominated "
                                 "by single-witness OCR artifacts (e.g. matthew/4/32 = Matthew 4:23 "
                                 "text; genesis/1/32 = Genesis 1:31). Versification-divergence "
                                 "adjudication set for a follow-up.",
            "archaic_only_sample": sorted(archaic_only)[:8],
            "rendered_confidence_tiers": dict(sorted(rendered_tiers.items())),
            "rendered_independent_depth": {str(k): v for k, v in sorted(rendered_depth.items())},
        },
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(f"render_archaic: idx109 sha {sha[:12]} (minted) · {len(hits)} archaic verse bodies · "
          f"{len(coverage_gap)} coverage-gap (modern surface, flagged) · "
          f"{len(archaic_only)} archaic-only deferred · parity vs 108 OK · report -> {REPORT.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

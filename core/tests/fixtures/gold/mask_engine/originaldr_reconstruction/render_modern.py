#!/usr/bin/env python3
"""Phase 2 · P2a — render the modern OriginalDR (idx 108) FROM the basis database.

The modern gold work is a deterministic PROJECTION of the Phase-1 basis DB (plan §5.2, and the
§1.2 principle "one basis, two renderings"), not a direct re-read of a single witness:

  * verse bodies come from the basis-db ``render_modern`` surface — the consensus-called modern
    form resolved under ``modern-standard.json`` (Madueke_A authoritative; ligatures expanded,
    divine-speech majuscule preserved);
  * the editorial apparatus (book/chapter arguments, footnotes, cross-refs, annotations, the 26
    reference documents) and the structural frame reuse the proven ``gen_dr_original`` machinery,
    sourced from the janvier-s (Sabates_A) witness AT RENDER TIME — the basis DB stores apparatus
    placement + coverage, not prose (see build_basis_db.py's snapshot note).

Byte-identity gate (why this is faithful, not a silent rewrite): ``render_modern`` equals
``clean_scripture(Madueke)`` where Madueke attests a verse and ``clean(Sabates)`` where it does not
(the same functions gen_dr_original's fallback + appendix paths use). So this projection reproduces
the idx 108 reference text BYTE-FOR-BYTE — asserted here against the pinned sha. The projection
therefore proves the basis DB is a faithful single source of truth, and sets up P2b
(render_archaic.py) as the archaic sibling off the SAME basis, differing only in the final
orthographic/typographic layer.

Provenance of the pinned sha: the first run of this gate DID diverge, on exactly one paragraph — it
surfaced a source artifact where 3-Esdras 2:1 appears twice in the janvier-s raw (the second "verse
1" is a leaked cross-reference list). The direct-witness generator emitted both as verses; the
consensus (skeleton-keyed) collapsed them, keeping the wrong one. Fixed at the root by a keep-first
verse-number dedup in the generator, the detector, and the consensus loader — the exact "detect →
generate → re-detect as confirmation" payoff the paradigm promises (plan §1). The pinned sha below
is the corrected idx 108 (one spurious paragraph dropped vs the pre-fix da451dc27ccf).

Outputs:
  - imports/Scripture/Bibles/OriginalDR/OriginalDR-modern-1582-1610.txt   (reference text)
  - core/tests/fixtures/gold/maps/work-108.map.json                        (masking map)
  - originaldr_reconstruction/render-modern-report.json                    (committed projection summary)

Run:  core/.venv/bin/python render_modern.py
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

sys.path.insert(0, str(Path(__file__).resolve().parent))  # R9.6: sibling import
import project_root as pr  # noqa: E402  R9.6: one derived root
import gen_dr_original as gen  # type: ignore[import]  # noqa: E402  (sibling dynamic import: machinery)

REPO = HERE.parents[5]
BASIS_DB = pr.BASIS_DB
REPORT = HERE / "render-modern-report.json"

# The pinned reference sha of the committed idx 108 (the direct-witness build). The basis-db
# projection MUST reproduce it — that equality is the P2a correctness gate.
EXPECTED_SHA = "4f8f52ee8c30d297915ab7c9d3344e365f1e0272e56df17de13d5dfa9b5ae3f6"
GENERATED_FROM = (
    "mask_engine/originaldr_reconstruction/render_modern.py "
    "(basis-db projection: verse bodies = consensus render_modern surfaces under "
    "modern-standard.json; apparatus + structure = janvier-s at render time)")


def load_basis(db: Path) -> tuple[dict[str, str], dict[str, str], dict[str, int]]:
    """Return {verse_id: render_modern}, {verse_id: tier}, {verse_id: independent_depth}."""
    con = sqlite3.connect(db)
    try:
        surfaces = {eid: rm for eid, rm in con.execute(
            "SELECT id, render_modern FROM elements WHERE type='scripture-verse'")}
        tier = {eid: t for eid, t in con.execute("SELECT element_id, tier FROM consensus")}
        depth = {eid: d for eid, d in con.execute("SELECT element_id, indep_depth FROM consensus")}
    finally:
        con.close()
    return surfaces, tier, depth


def main() -> int:
    if not BASIS_DB.exists():
        print(f"!! basis-db not found: {BASIS_DB} — run build_basis_db.py first", file=sys.stderr)
        return 2

    surfaces, tier, depth = load_basis(BASIS_DB)
    # Verses with no modern surface are ARCHAIC-ONLY coordinates: positions present in the 1582
    # archaic witnesses (s-dismas / odr-com) but absent from the modern edition, a genuine
    # versification divergence (e.g. 1-Corinthians 7:41 — modern 1 Cor 7 ends at v40). They have no
    # modern counterpart, so idx 108 correctly never renders them; idx 109 (archaic) will.
    archaic_only = sorted(vid for vid, s in surfaces.items() if not s)

    hits: set[str] = set()
    text, els, warns = gen.build(verse_override=surfaces, _override_hits=hits)
    sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
    if sha != EXPECTED_SHA:
        print(f"!! BYTE-IDENTITY GATE FAILED: basis-db projection sha {sha[:12]} != committed idx108 "
              f"{EXPECTED_SHA[:12]}.\n   The render_modern surfaces diverge from the direct-witness "
              f"text — investigate before emitting.", file=sys.stderr)
        return 1

    emit_sha = gen.emit_outputs(text, els, warns, idx=108, out_txt=gen.OUT_TXT,
                                generated_from=GENERATED_FROM)
    assert emit_sha == EXPECTED_SHA, "emit_outputs re-derived a different sha than build()"

    # Projection accounting: verse bodies driven by the basis DB, and the confidence model behind
    # the rendered text (consensus tier / independent-depth over the rendered verses).
    rendered_tiers: Counter[str] = Counter()
    rendered_depth: Counter[int] = Counter()
    for vid in hits:
        if tier.get(vid):
            rendered_tiers[tier[vid]] += 1
        d = depth.get(vid)
        if isinstance(d, int):
            rendered_depth[d] += 1

    report = {
        "artifact": "render-modern", "phase": "P2a", "idx": 108,
        "generated_by": "render_modern.py",
        "note": "idx 108 rendered as a projection of the basis DB: verse bodies from the "
                "consensus render_modern surface (modern-standard.json), apparatus + structure "
                "from janvier-s at render time. The reference text is byte-identical to the "
                "committed direct-witness idx 108 (sha pinned below) — the basis DB is a faithful "
                "single source of truth. Verse render surfaces live in the gitignored basis-db.sqlite; "
                "this JSON is the diff-reviewable, CI-safe projection summary.",
        "reference": {
            "file": str(gen.OUT_TXT.relative_to(REPO)),
            "sha256": sha,
            "text_len": len(text),
            "matches_pinned_reference_sha": True,
            "expected_sha256": EXPECTED_SHA,
        },
        "modern_standard": "originaldr_reconstruction/modern-standard.json",
        "scripture_projection": {
            "basis_db_verses": len(surfaces),
            "modern_surface_verses": len(surfaces) - len(archaic_only),
            "archaic_only_coordinates": len(archaic_only),
            "archaic_only_note": "positions in the 1582 archaic witnesses with no modern counterpart "
                                 "(versification divergence); rendered by idx 109, not idx 108",
            "archaic_only_sample": archaic_only[:8],
            "verse_bodies_from_basis_db": len(hits),
            "render_time_fallbacks": len(warns),
            "pure_basis_db_projection": len(warns) == 0,
            "rendered_confidence_tiers": dict(sorted(rendered_tiers.items())),
            "rendered_independent_depth": {str(k): v for k, v in sorted(rendered_depth.items())},
        },
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(f"render_modern: idx108 sha {sha[:12]} (byte-identical) · "
          f"{len(hits)} verse bodies from basis DB · {len(warns)} render-time fallbacks · "
          f"report -> {REPORT.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

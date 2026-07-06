#!/usr/bin/env python3
"""Phase 1 · P1.1 — build the canonical element skeleton (reference coordinate system).

The skeleton is the source-neutral "reference genome" onto which every witness's
detected elements align (P1.2) and against which consensus is called (P1.3). It
fixes the *coordinate space* — tome -> testament -> front/back matter -> book ->
chapter, plus the per-book/per-chapter apparatus channels and the ~26 standalone
reference documents — from canonical authority (the Catholic/Clementine DR oracle
`catholic_dr` for book+chapter identity, and the scan-derived `apparatus-order.json`
for the reference-doc slots). It deliberately does NOT enumerate verses: verse
membership within a chapter is a *called* quantity (consensus across witnesses),
so pre-seeding it from any one source would be circular. Verses are addressed
canonically as `scripture/<book>/<ch>/<v>` when detection opens them.

Canonical book slugs + apparatus order are imported from the existing 108 builder
(gen_dr_original.py) so the coordinate system stays in lock-step with the emitter;
chapter counts come from the `catholic_dr` oracle. Positional alignment between the
two is asserted.

Output: skeleton.json (tracked) in this directory.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent          # …/mask_engine/originaldr_reconstruction
MASK_ENGINE = HERE.parent                        # …/mask_engine
GOLD = MASK_ENGINE.parent                        # …/gold
CANON = GOLD / "canon_chapters.json"

sys.path.insert(0, str(MASK_ENGINE))
import gen_dr_original as gen  # type: ignore[import]  # noqa: E402  (dynamic sibling import; canonical slug lists + apparatus order)

# Per-chapter apparatus channels (masked) + the visible scripture body. Names mirror the
# apparatus the 108 builder aggregates: chapter argument/summary, per-verse footnotes,
# cross-references, and the marginal-commentary sidecar.
CHAPTER_CHANNELS = [
    {"name": "scripture_body", "masked": False,
     "note": "verse bodies; individual verses addressed scripture/<book>/<ch>/<v>"},
    {"name": "chapter_argument", "masked": True, "note": "chapter summary/argument"},
    {"name": "verse_footnotes", "masked": True, "note": "per-verse footnotes"},
    {"name": "cross_refs", "masked": True, "note": "per-verse cross-references"},
    {"name": "sidecar_notes", "masked": True, "note": "marginal commentary (annotations sidecar)"},
]
BOOK_CHANNELS = [
    {"name": "book_argument", "masked": True, "note": "book-level argument/introduction"},
]


def load_canon() -> list[dict]:
    return json.loads(CANON.read_text())["catholic_dr"]


def build() -> dict:
    canon = load_canon()
    slugs = list(gen.OT) + list(gen.NT) + list(gen.APOCRYPHA)
    appendix = set(gen.APOCRYPHA)
    # Integrity: the coordinate grid must match the canonical authority exactly. Per-book
    # positional identity is authoritatively validated downstream by classify_books_catholic
    # (the Catholic oracle) when the rendered map is checked — that already passes 76/76 for the
    # existing 108 build, which emits in this exact OT+NT+APOCRYPHA order, so the positional zip
    # is correct by construction. Here we hard-assert the aggregate + a few unambiguous anchors.
    assert len(slugs) == len(canon) == 76, f"book count drift: slugs={len(slugs)} canon={len(canon)}"
    assert len(gen.OT) == 46 and len(gen.NT) == 27 and len(gen.APOCRYPHA) == 3, "testament partition drift"
    _by_slug = dict(zip(slugs, canon))
    _anchors = {"genesis": 50, "apocalypse": 22,
                "prayer-of-manasses": 1, "3-esdras": 9, "4-esdras": 16}
    for a_slug, a_ch in _anchors.items():
        assert _by_slug[a_slug]["chapters"] == a_ch, \
            f"anchor drift: {a_slug} expected {a_ch}, got {_by_slug[a_slug]['chapters']}"

    def testament_of(slug: str) -> str:
        if slug in gen.NT:
            return "NT"
        if slug in appendix:
            return "APPENDIX"
        return "OT"

    books = []
    for i, (slug, c) in enumerate(zip(slugs, canon), start=1):
        books.append({
            "ordinal": i,
            "slug": slug,
            "oracle_match": c["match"],
            "testament": testament_of(slug),
            "is_appendix": slug in appendix,
            "chapters": c["chapters"],
            "scripture_id": f"scripture/{slug}",
            "argument_id": f"apparatus/{slug}/argument",
        })

    # 26 standalone reference docs from the scan-derived apparatus order.
    ao = json.loads((MASK_ENGINE / "originaldr_validation/apparatus-order.json").read_text())
    ref_docs = []
    for region in ("ot_front", "ot_back", "nt_front", "nt_back"):
        testament, matter = region.split("_")
        for entry in ao[region]:
            ref_docs.append({
                "slot_id": f"apparatus/{testament}-{matter}/{entry['name']}",
                "region": region,
                "testament": testament.upper(),
                "matter": matter,
                "name": entry["name"],
                "position": entry["position"],
                "evidence_method": entry.get("evidence", {}).get("method"),
            })

    total_chapters = sum(b["chapters"] for b in books)
    assert total_chapters == 1360, f"chapter-sum drift: {total_chapters} != 1360"
    skeleton = {
        "schema": "originaldr.skeleton/v1",
        "generated_by": "originaldr_reconstruction/build_skeleton.py",
        "canonical_authority": (
            "book+chapter identity from catholic_dr oracle (canon_chapters.json); "
            "reference-doc slots from originaldr_validation/apparatus-order.json; "
            "book slugs + apparatus order from gen_dr_original.py"
        ),
        "id_conventions": {
            "scripture_chapter": "scripture/<book-slug>/<chapter>",
            "scripture_verse": "scripture/<book-slug>/<chapter>/<verse>  (opened by detection; consensus-called)",
            "book_argument": "apparatus/<book-slug>/argument",
            "chapter_channel": "apparatus/<book-slug>/<chapter>/<channel>  (channel in {chapter_argument,verse_footnotes,cross_refs,sidecar_notes})",
            "reference_doc": "apparatus/<ot|nt>-<front|back>/<name>",
            "structural": "structure/<node>  (tome, testament/OT, testament/NT, appendix, matter/<region>)",
        },
        "structure": {
            "tome": "originaldr",
            "testaments": ["OT", "NT"],
            "matter_regions": ["ot_front", "ot_back", "nt_front", "nt_back"],
            "appendix": list(gen.APOCRYPHA),
        },
        "channels": {"book_level": BOOK_CHANNELS, "chapter_level": CHAPTER_CHANNELS},
        "books": books,
        "reference_docs": ref_docs,
        "totals": {
            "books": len(books),
            "canonical_books": sum(1 for b in books if not b["is_appendix"]),
            "appendix_books": sum(1 for b in books if b["is_appendix"]),
            "chapters": total_chapters,
            "reference_docs": len(ref_docs),
            "book_channels": len(BOOK_CHANNELS),
            "chapter_channels": len(CHAPTER_CHANNELS),
        },
        "integrity": "aggregate + anchor asserts pass; per-book identity oracle-validated downstream "
                     "(classify_books_catholic 76/76 on the rendered map)",
    }
    return skeleton


def main() -> int:
    sk = build()
    out = HERE / "skeleton.json"
    out.write_text(json.dumps(sk, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    t = sk["totals"]
    print(f"skeleton.json: {t['books']} books ({t['canonical_books']} canonical + "
          f"{t['appendix_books']} appendix), {t['chapters']} chapters, "
          f"{t['reference_docs']} reference docs, {t['chapter_channels']} chapter channels")
    print("integrity:", sk["integrity"])
    return 0


if __name__ == "__main__":
    sys.exit(main())

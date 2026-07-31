# -*- coding: utf-8 -*-
"""The two Genesis-8 defects, pinned so neither can return (§13 Q48).

Chapter 8 was blocked twice over, by faults of different KINDS that the count-based verify could not tell
apart, and the second only became visible once the first was fixed:

  1. A PAGE-FOOT NOTE BLOCK spliced into the middle of printed verse 20 — two marginal notes, the page number
     and the facing page's running head `Genesis`, all sitting between `...cogitation of` and `mans hart are
     prone to euil`. It is not a suffix, so no end-of-verse trimmer reaches it, and it wounds Genesis 46:25 in
     exactly the same way. This is a PARSE fault: the text is ours to get right.
  2. The EDITION'S OWN NUMBERING — the s_dismas page prints DR verses 15 and 16 merged under `15` and numbers
     the rest one lower, ending at a printed `21` that is DR 22. This is NOT a parse fault: the parse is
     faithful to the page, and the correction belongs in `ref_renumber.CORRECTIONS` where it is reversible and
     carries its corroboration.

Keeping the two apart is the whole point. Fixing (2) in the parser would make the transcription unfaithful to
its source; fixing (1) in `ref_renumber` would hide a real parse bug behind a numbering entry.

These tests run on synthetic line-blocks in the shape `pdftotext` emits, so they need neither the PDF nor the
built reads.
"""
from __future__ import annotations

import ref_renumber as RR
import ref_repair_s_dismas as R


def _key(v: int, ch: int = 8) -> str:
    return f"scripture/genesis/{ch}/{v}"


# ---------------------------------------------------------------- 1. the page-foot note block

def test_page_foot_note_block_is_removed_from_mid_verse():
    """The chapter-8 wound, reduced to its structure: body, notes, page number, running head, body."""
    block = [
        "curſe the earth for men: for the ſenſe and cogitation of",
        "a The crowe returned not into the arke, but (as appeareth by the",
        "",
        "Hebrew text) going and returning reſted vpon the arke.",
        "",
        "b They entred into the arke the 17. day, the ſecõd moneth of the",
        "",
        "other yeare: ſo they remained there 12. monethes and tenne dayes.",
        "",
        "51",
        "",
        "Genesis",
        "mans hart are prone to euil from their youth: I wil no",
    ]
    out = " ".join(ln for ln in R._strip_page_furniture(block, "Genesis") if ln.strip())
    assert "cogitation of mans hart are prone to euil" in out
    for gone in ("The crowe returned", "Hebrew text", "They entred into the arke the 17", "Genesis", "51"):
        assert gone not in out, f"page furniture survived: {gone!r}"


def test_marginal_citations_go_with_their_note():
    """Genesis 46:25's shape — an anchored note followed by bare marginal citations, then the page foot."""
    block = [
        "and Ieſer and Sallem. 25 Theſe be the ſonnes of Bala,",
        "a That is, she bare their fathers in Meſopotamia.",
        "",
        "in Gen.",
        "",
        "S. Aug. q. 151.",
        "",
        "177",
        "",
        "Genesis",
        "whom Laban gaue to Rachel his daughter: and theſe ſhe",
    ]
    out = " ".join(ln for ln in R._strip_page_furniture(block, "Genesis") if ln.strip())
    assert "ſonnes of Bala, whom Laban gaue to Rachel his daughter" in out
    for gone in ("That is, she bare", "in Gen.", "S. Aug.", "Genesis"):
        assert gone not in out


def test_the_drop_capital_survives_the_page_foot_scan():
    """The engraved capital sits on its own line NEXT TO a page number, exactly where a note would. Consuming
    it would silently behead verse 1 — `nd God remembred Noe` — so the backward scan stops dead at it."""
    block = [
        "appeared. 6 And after that fourtie dayes were paſſed,",
        "",
        "A",
        "",
        "50",
        "",
        "Noe opening the windowe of the arke, which he had",
    ]
    out = R._strip_page_furniture(block, "Genesis")
    assert "A" in [ln.strip() for ln in out]
    assert "50" not in [ln.strip() for ln in out]


def test_body_prose_across_a_page_break_is_untouched():
    """A page break with no apparatus at all must lose the number and nothing else."""
    block = ["and the waters decreaſed. 2 And the fountaines of the", "", "12", "", "depth, and the floud gates"]
    out = [ln for ln in R._strip_page_furniture(block, "Genesis") if ln.strip()]
    assert out == ["and the waters decreaſed. 2 And the fountaines of the", "depth, and the floud gates"]


# ---------------------------------------------------------------- 2. the edition's numbering

def test_genesis_8_split_is_registered_with_its_evidence():
    entry = RR.CORRECTIONS[("s_dismas", "genesis", 8)]
    assert entry["split"] == (15,)
    assert entry.get("evidence"), "a correction without its corroboration is not adoptable"


def test_split_restores_the_dr_numbering_without_inventing_text():
    """v15 carries DR 15+16; the others say where to cut, and everything after moves UP by one."""
    parsed = {
        14: "In the ſecond moneth, the earth was dried.",
        15: "And God ſpake to Noe, ſaying: Goe forth of the arke, thou & thy wife.",
        16: "Al cattle, that are with thee of al flesh.",
        17: "Noe therfore went forth, and his ſonnes.",
    }
    others = [{_key(15): "And God spake to Noe, saying:",
               _key(16): "Goe forth of the arke, thou & thy wife.",
               _key(17): "Al cattle, that are with thee of al flesh."} for _ in range(3)]
    out = R._renumbered(RR, 8, parsed, others)

    assert out[14] == parsed[14], "verses before the split are untouched"
    assert out[15] == "And God ſpake to Noe, ſaying:"
    assert out[16] == "Goe forth of the arke, thou & thy wife."
    assert out[17] == parsed[16], "printed 16 is DR 17"
    assert out[18] == parsed[17], "the shift persists to the chapter end"
    # nothing invented, nothing lost: the tokens are the same tokens
    assert sorted(" ".join(parsed.values()).split()) == sorted(" ".join(out.values()).split())


def test_a_chapter_without_a_correction_passes_through_unchanged():
    parsed = {1: "And God remembred Noe.", 2: "And the fountaines of the depth."}
    assert R._renumbered(RR, 7, parsed, [{}, {}, {}]) == parsed

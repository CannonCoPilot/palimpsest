# -*- coding: utf-8 -*-
"""The five marginal notes spliced INSIDE an s_dismas verse — pinned so they cannot silently evaporate.

HOW THEY WERE FOUND, which is the part worth keeping. A verse failing in ALL FOUR sources was being triaged as
"edition divergence, a ceiling, never chase". It has TWO causes, and the split test separates them:

    For each reference, does EVERY source fail against it? If exactly ONE reference binds while all four
    sources PASS the other three, the fault is in the REFERENCE, not in the reading.

Over Genesis's 34 all-fail verses that returned five loci, every one `s_dismas`, worth 20 cells. The other 7
(where all four references bind) are the true divergence ceiling — the number to quote is 7, not 34.

WHY `trim_apparatus` CANNOT REACH THEM. Not a tuning gap; a class its model cannot express.
  · It is SUFFIX-only — it keeps a PREFIX. These are INFIXED (`of the [Fruitful or] ſecond`).
  · Its 1.4x length ratio cannot see a short gloss: 29:15 is 1.10x, 41:52 1.14x, 33:10 1.22x.

So they are ENUMERATED, not detected — deliberately. `trim_apparatus`'s first version was general and
under-guarded and fired 149 times destroying real scripture; five corroborated loci do not justify a second
general excision rule. The DETECTOR is safe and belongs in the audit; the EXCISION stays enumerated.

WHAT THESE TESTS ENFORCE. `excise_apparatus` records a phrase it cannot find as MISSING rather than raising,
because a data change upstream should not take the whole pipeline down. That makes the test the enforcement:
if a read changes and a correction stops applying, this fails LOUDLY instead of the correction evaporating and
the cells quietly re-opening. Same reasoning as `test_every_correction_carries_its_corroboration`.
"""
from __future__ import annotations

import pytest

import ref_renumber as RR

LOCI = [(26, 2), (29, 15), (33, 10), (41, 52), (47, 4)]


@pytest.fixture(scope="module")
def reads():
    return {n: RR.load_corrected(n) for n in ("s_dismas", "odr_com", "sabates_a", "madueke_b")}


def test_every_excision_applies_and_none_is_missing():
    """A MISSING entry means the upstream read changed and the correction is no longer landing."""
    RR.load_corrected("s_dismas")
    found = RR.LAST_EXCISIONS.get("s_dismas") or []
    assert len(found) == len(RR.APPARATUS_EXCISIONS), "not every enumerated locus was visited"
    missing = [f for f in found if "MISSING" in f]
    assert not missing, f"excision phrases no longer present in the source read: {missing}"


@pytest.mark.parametrize("ch,vn", LOCI)
def test_the_corrected_verse_matches_the_corroborating_witnesses_in_length(ch, vn, reads):
    """THE ARITHMETIC CORROBORATION. Removing exactly the listed phrases must yield exactly the token count the
    other three witnesses carry — that is what makes this an excision of apparatus and not an edit of text."""
    k = f"scripture/genesis/{ch}/{vn}"
    mine = len(reads["s_dismas"][k].split())
    others = [len(reads[n][k].split()) for n in ("odr_com", "sabates_a", "madueke_b")]
    assert mine == others[0], f"genesis {ch}:{vn}: s_dismas {mine} != odr_com {others[0]}"
    assert abs(mine - min(others)) <= 1, f"genesis {ch}:{vn}: {mine} vs {others}"


@pytest.mark.parametrize("ch,vn", LOCI)
def test_no_apparatus_phrase_survives_in_the_corrected_verse(ch, vn, reads):
    for (n, b, c, v), phrases in RR.APPARATUS_EXCISIONS.items():
        if (c, v) != (ch, vn):
            continue
        txt = reads[n][f"scripture/{b}/{c}/{v}"]
        for p in phrases:
            assert p not in txt, f"{b} {c}:{v} still carries {p[:60]!r}"


def test_the_note_that_wraps_lands_at_two_anchors():
    """29:15 and 41:52 carry ONE marginal note at TWO anchor points, because the note wraps across two printed
    lines and each line is spliced where it sits. The fragments reassemble into a coherent note — which is
    corroboration in itself, since neither an OCR failure nor a genuine variant reading would do that."""
    assert RR.APPARATUS_EXCISIONS[("s_dismas", "genesis", 29, 15)] == ["VVithout", "vvages?"]
    assert RR.APPARATUS_EXCISIONS[("s_dismas", "genesis", 41, 52)] == ["Fruitful or", "Grovving."]


def test_excision_removes_no_scripture(reads):
    """The residue must still read as the verse. Checked at both ends against a witness that never carried the
    note — a trim that ate scripture would fail at the tail, which is how 41:52 was recognised in the first
    place (s_dismas had lost `in the land of my pouertie` behind the gloss `Grovving.`)."""
    for ch, vn in LOCI:
        k = f"scripture/genesis/{ch}/{vn}"
        mine = RR._norm(reads["s_dismas"][k])
        ref = RR._norm(reads["odr_com"][k])
        assert len(mine) == len(ref) and len(mine) >= 2
        # BOTH ENDS must survive. Compared on a 4-char prefix because the witnesses differ in ORTHOGRAPHY
        # (`ſaid`/`said`, `ſoiourne`/`sojourn`) but not in wording — an unfolded equality would fail on
        # spelling alone, which is the same trap `ref_alignment_audit` and `trim_span_edges` both record.
        assert mine[0][:4].lower() == ref[0][:4].lower(), f"genesis {ch}:{vn} head lost: {mine[:3]} vs {ref[:3]}"
        assert mine[-1][:4].lower() == ref[-1][:4].lower(), f"genesis {ch}:{vn} tail lost: {mine[-3:]} vs {ref[-3:]}"


def test_a_verse_with_no_entry_is_untouched(reads):
    """The excision table must not reach anything it does not name."""
    k = "scripture/genesis/26/3"
    assert len(reads["s_dismas"][k].split()) == len(RR.load_corrected("s_dismas")[k].split())
    assert not any(v == 3 for (_n, _b, c, v) in RR.APPARATUS_EXCISIONS if c == 26)

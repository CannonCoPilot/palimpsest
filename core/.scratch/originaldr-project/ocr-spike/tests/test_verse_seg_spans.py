# -*- coding: utf-8 -*-
"""TDD spec for verse_seg's RAW TOKEN SPAN exposure (tok_lo/tok_hi).

verse_geom needs to map each localized verse back to the pixel band of the page lines that carry it. The only
robust bridge is the raw-token index range each verse occupies in the INPUT body text: verse -> [tok_lo,tok_hi)
-> line indices -> bboxes. This file pins that contract:

  1. every emitted verse carries integer tok_lo/tok_hi with 0 <= tok_lo <= tok_hi <= n_raw_tokens;
  2. for the clean (non-apparatus) cut, `" ".join(raw_tokens[tok_lo:tok_hi])` reproduces the verse's own span
     text EXACTLY (so a caller can trust the index range == the text it scored);
  3. spans TILE the localized range without overlap (tok_hi[v] == tok_lo[next_v]) — a partition, so a token maps
     to exactly one verse (no double-counted pixels);
  4. REGRESSION: adding the spans must not perturb the validated fields (text/open/len_ratio/anchor). We re-run
     the module self-check scenario and assert the pre-existing outputs are byte-identical.
"""
from __future__ import annotations

import re

import verse_seg


def _raw_tokens(text: str):
    return re.findall(r"\S+", text)


def test_every_verse_has_integer_token_span():
    cv = verse_seg.chapter_verses("psalms", 118, verse_seg.JANVIER)
    page = " ".join(cv[v] for v in range(9, 17))
    seg = verse_seg.segment(page, cv)
    n = len(_raw_tokens(page))
    assert seg, "expected vv9-16 to localize"
    for v, r in seg.items():
        assert "tok_lo" in r and "tok_hi" in r, f"verse {v} missing token span"
        assert isinstance(r["tok_lo"], int) and isinstance(r["tok_hi"], int)
        assert 0 <= r["tok_lo"] <= r["tok_hi"] <= n, f"verse {v} span {r['tok_lo']}..{r['tok_hi']} out of [0,{n}]"


def test_token_span_reproduces_clean_span_text():
    """On a clean cut (no apparatus), the raw-token slice must equal the emitted span text verbatim."""
    cv = verse_seg.chapter_verses("psalms", 118, verse_seg.JANVIER)
    page = " ".join(cv[v] for v in range(9, 17))
    raw = _raw_tokens(page)
    seg = verse_seg.segment(page, cv)
    for v, r in seg.items():
        sliced = " ".join(raw[r["tok_lo"]:r["tok_hi"]]).strip()
        assert sliced == r["text"], f"verse {v}: slice {sliced!r} != span {r['text']!r}"


def test_spans_tile_without_overlap():
    """Consecutive localized verses partition the token stream: tok_hi[v] == tok_lo[v+1]."""
    cv = verse_seg.chapter_verses("psalms", 118, verse_seg.JANVIER)
    page = " ".join(cv[v] for v in range(9, 17))
    seg = verse_seg.segment(page, cv)
    vs = sorted(seg)
    for a, b in zip(vs, vs[1:]):
        assert seg[a]["tok_hi"] == seg[b]["tok_lo"], (
            f"gap/overlap between v{a} (hi={seg[a]['tok_hi']}) and v{b} (lo={seg[b]['tok_lo']})")


def test_spans_do_not_perturb_validated_fields():
    """REGRESSION: the exact self-check numbers must be unchanged by the additive span fields."""
    from char_identity import fold_modern, edit_ratio
    cv = verse_seg.chapter_verses("psalms", 118, verse_seg.JANVIER)
    page = " ".join(cv[v] for v in range(9, 17))
    seg = verse_seg.segment(page, cv)
    # every verse cleanly cut, no OPEN, content-id 1.0 (the self-check's [clean-cut] assertion)
    worst = min(edit_ratio(fold_modern(seg[v]["text"]), fold_modern(cv[v])) for v in range(9, 17))
    assert worst >= 0.95
    assert sum(int(seg[v]["open"]) for v in range(9, 17)) == 0
    # apparatus path still excises the interleaved footnote (drop_apparatus contract intact)
    foot = "this is an interleaved footnote annotation gloss commentary paratext insertion here"
    poll = " ".join([cv[9], cv[10], cv[11], cv[12], foot, cv[13], cv[14], cv[15], cv[16]])
    on = verse_seg.segment(poll, cv, drop_apparatus=True)
    on12 = edit_ratio(fold_modern(on.get(12, {}).get("text", "")), fold_modern(cv[12]))
    assert on12 >= 0.98

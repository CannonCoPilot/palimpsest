# -*- coding: utf-8 -*-
"""TDD spec for s_arbiter — the ſ-faithful arbiter that closes the RESCUED_CONTENT_S_OPEN debts (§12.5 Tier C2).

THE SHAPE OF THE DEBT. 21 verses have CONTENT accepted at R3 (olmOCR lifted them past τx) but a MODERNIZED ſ
surface (olmOCR flattens ſ→s). The ſ-faithful surface must be OBSERVED, never rule-inserted: `long_s_rule.
restore_long_s` is ~90.4% accurate on this project's own gold, so publishing it would pass off ~1-in-10
invented glyphs as the printed surface — exactly the laundering No Silent Degradation forbids.

THE METHOD. R2 (kraken/reichenau_lat) IS an ſ-faithful visual recognizer; it is only its CONTENT that the gate
rejected. So wherever R2 and R3 read the same token modulo the ſ-fold, R2's spelling is an OBSERVATION of the
ſ surface for a token whose content R3 has confirmed — adopt it. Only where R3 *corrected* R2 is the ſ genuinely
unobserved, and that residue (small, and itemised) is what the in-session vision arbiter must read off the crop.

The fold here is ſ-ONLY, deliberately narrower than `verse_seg._afold`. Folding u/v, i/j or case would let a
token R3 *corrected* count as "agreeing" with R2 and hand the deliverable R2's rejected reading back.
"""
from __future__ import annotations

import pytest

import s_arbiter


# ---------------------------------------------------------------- transfer: adopt the observed surface

def test_agreeing_token_takes_R2s_observed_long_s():
    """R3 modernized 'bleſſed'->'blessed'; R2 read the same word WITH ſ -> the ſ is observed, adopt R2's form."""
    out = s_arbiter.transfer("and he was bleſſed", "and he was blessed")
    assert out["text"] == "and he was bleſſed"
    assert out["unresolved"] == []
    assert out["n_observed"] == 1        # one token carried an s-decision, resolved from R2


def test_content_correction_leaves_the_long_s_UNOBSERVED_not_guessed():
    """R2 misread 'ſeruant' as garbage; R3 fixed the content to 'servant'. No R2 token attests this word's
    surface, so its medial s is UNDECIDED -> it must be reported, never positionally restored."""
    out = s_arbiter.transfer("and he was zzzqq", "and he was servant")
    assert out["unresolved"] == [{"i": 3, "token": "servant", "positions": [0]}]
    assert "ſ" not in out["text"]                      # nothing invented
    assert out["tokens"][3]["source"] == "R3-content"


def test_word_final_s_is_no_decision_at_all():
    """Word-final s is round in every 1582-1610 setting, so a token whose only s is final needs no arbitration."""
    out = s_arbiter.transfer("zzz", "his")
    assert out["unresolved"] == []
    assert out["n_undecided"] == 0


def test_a_token_with_no_s_glyph_is_never_flagged():
    out = s_arbiter.transfer("qqq", "unto")
    assert out["unresolved"] == []


def test_archaic_spelling_keeps_R2s_OBSERVED_form_not_R3s_modernization():
    """REVERSAL OF AN EARLIER DECISION, on evidence (2026-07-29). This test previously asserted that R2 `vpon`
    vs R3 `upon` is a CONTENT disagreement in which R3 wins, and that was wrong on three counts:

      1. `ground-truth/GUIDELINES.md` requires u/v to be preserved AS PRINTED (`vpon`, `vnderſtand`, `geue`,
         `haue`). The deliverable is a diplomatic transcription; publishing `upon` corrupts it.
      2. Under the project's OWN diplomatic fold the two are the SAME WORD, so there is no content
         disagreement to resolve — only a surface one, and this module exists to publish R3's content with
         R2's OBSERVED surface.
      3. MEASURED COST: olmOCR modernizes spelling as well as ſ (`ſeuenth`/`seventh`, `therfore`/`therefore`,
         `reſted`/`rested`), and because the fold here is ſ-only those pairs landed in a `replace` block. On
         genesis 2 that left 19 of 25 verses OPEN with reasons like `1 ſ kept, 2 unresolved: "rested",
         seventh` while R3's content scored 0.99 against the governing reference. The surface gate was
         refusing text that was right, for a difference the project does not consider a difference.

    The equivalence test is `char_identity.fold_modern` per word — the same class every content score uses — NOT
    the loose ſ/s/f skeleton. R2's known failure modes stay with R3: an n/u misread (`hane` for `haue`) or a
    dropout does not fold equal, so R3 still wins those."""
    out = s_arbiter.transfer("vpon the houſe", "upon the house")
    assert out["tokens"][0]["text"] == "vpon", "R2's OBSERVED archaic spelling must be kept"
    assert out["text"].split()[2] == "houſe"           # the agreeing token still takes R2's ſ
    assert out["unresolved"] == [], "an archaic-equivalent pair leaves no surface debt"
    # a pair that DOES carry an ſ decision is recorded as an observation, which is what closes the surface
    out2 = s_arbiter.transfer("reſted the ſeuenth day", "rested the seventh day")
    assert out2["text"] == "reſted the ſeuenth day"
    assert [t["source"] for t in out2["tokens"]][:1] == ["R2-observed"]
    assert out2["unresolved"] == []


def test_a_genuine_R2_misread_still_loses_to_R3():
    """The bound on the rule above. R2's documented weaknesses are dropouts and n/u, g/s confusions; those do
    NOT fold equal to the correct word, so R3's reading still wins and the surface debt is opened honestly."""
    out = s_arbiter.transfer("hane the houſe", "have the house")
    assert out["tokens"][0]["text"] == "have", "an n/u misread must not be preserved as an observation"


def test_punctuation_travels_with_the_token():
    out = s_arbiter.transfer("Bleſſed, Lord.", "Blessed, Lord.")
    assert out["text"] == "Bleſſed, Lord."


def test_an_f_where_the_print_has_long_s_is_a_DECISION_not_a_settled_token():
    """MEASURED ON THE REAL DEBT SET: olmOCR renders ſ as f as well as flattening it to s ('haiſt'->'haift',
    'anſwere'->'anfwere'). Such a token carries no s-glyph, so an s-only detector would call it settled and ship
    a wrong surface silently — the confident-wrong class one level below the gate."""
    out = s_arbiter.transfer("in al haiſt zzz", "in al haift went")
    assert [u["token"] for u in out["unresolved"]] == ["haift", "went"] or \
           "haift" in [u["token"] for u in out["unresolved"]]
    assert s_arbiter.decision_positions("haift") == [3]
    assert s_arbiter.decision_positions("of") == []          # word-final f is settled


def test_arbitration_may_move_f_to_long_s_but_not_change_other_letters():
    out = s_arbiter.transfer("zzz", "haift")
    s_arbiter.arbitrate(out, {0: "haiſt"})                    # surface observation -> allowed
    with pytest.raises(ValueError, match="content"):
        s_arbiter.arbitrate(out, {0: "haiſte"})               # letters changed -> refused


def test_long_s_in_material_R3_DROPPED_is_not_charged_to_the_verse_surface():
    """R2's line band interleaves apparatus ('on Eaſter eue.') that R3 correctly excludes from the verse. The
    baseline must be the RETAINED material, or closure is unreachable for a reason unrelated to the surface —
    and the dropped count is reported, never silently discounted."""
    out = s_arbiter.transfer("his garment as ſnow. on Eaſter eue.", "his garment as snow.")
    v = s_arbiter.verdict(out, "his garment as ſnow. on Eaſter eue.")
    assert v["r2_s_count"] == 1 and v["r2_s_dropped"] == 1
    assert v["state"] == "CLOSED"


def test_marginalia_INSIDE_a_replace_block_is_dropped_not_charged():
    """Matthew 28:16 — R2 read the running note 'The Ghoſper' between two words R3 corrected, so the aligner put
    note and correction in ONE replace block. Charging that note's ſ to the verse surface makes closure
    unreachable; pairing by skeleton similarity keeps the correction and drops the note."""
    out = s_arbiter.transfer("where The Ghoſper Iesvs had", "where I E S V S had")
    assert "Ghoſper" in out["dropped_tokens"]
    assert out["r2_s_dropped"] == 1 and out["r2_s_retained"] == 0


# ---------------------------------------------------------------- arbitrate: the in-session visual read

def test_arbitration_fills_the_undecided_token_and_closes_it():
    out = s_arbiter.transfer("and he was zzzqq", "and he was servant")
    done = s_arbiter.arbitrate(out, {3: "ſervant"})
    assert done["text"] == "and he was ſervant"
    assert done["unresolved"] == []
    assert done["tokens"][3]["source"] == "vision-observed"


def test_arbitration_MAY_NOT_change_content():
    """The arbiter reads the ſ SURFACE only. A reading that alters the letters is a content edit smuggled in on
    the surface axis -> refuse it loudly rather than publish it."""
    out = s_arbiter.transfer("and he was zzzqq", "and he was servant")
    with pytest.raises(ValueError, match="content"):
        s_arbiter.arbitrate(out, {3: "ſeruant"})


def test_arbitration_rejects_a_word_final_long_s():
    """No 1582-1610 printer sets ſ word-finally; such a 'reading' is a misread, not an observation."""
    out = s_arbiter.transfer("zzz qqq", "his house")
    out2 = s_arbiter.transfer("zzz qqq", "his houses")
    with pytest.raises(ValueError, match="word-final"):
        s_arbiter.arbitrate(out2, {1: "houſeſ"})


def test_arbitration_of_an_unknown_index_is_refused():
    out = s_arbiter.transfer("and he was zzzqq", "and he was servant")
    with pytest.raises(KeyError):
        s_arbiter.arbitrate(out, {9: "ſomething"})


def test_a_content_error_found_while_reading_the_crop_REOPENS_the_verse():
    """Reading the crop to settle ſ also reveals when R3 got the LETTERS wrong — measured: 'ſayſt'->'layst'
    (abdias 1:3), 'ſate'->'satte' (matthew 28:2), 'fooles'->'foolcs' (proverbs 16:22), 'afflict'->'affliet'
    (genesis 16:6). The verse-level gate absorbed each because the rest of the verse scored well. Publishing a
    tidy ſ on top of a wrong word is the worst available outcome, so the verse re-opens on the CONTENT axis."""
    out = s_arbiter.transfer("which ſayſt in", "which layst in")
    done = s_arbiter.arbitrate(out, {1: {"printed": "ſayſt", "note": "olmOCR read ſ as l"}})
    v = s_arbiter.verdict(done, "which ſayſt in")
    assert v["state"] == "CONTENT_OPEN"
    assert v["content_errors"] == [{"i": 1, "r3": "layst", "printed": "ſayſt", "note": "olmOCR read ſ as l"}]
    assert done["tokens"][1]["text"] == "layst"        # nothing rewritten behind the gate's back


def test_confirming_a_token_unchanged_is_a_valid_OBSERVATION():
    """Most residue is a genuine f ('fountaine') or a round s the printer really set ('shal' before h — the
    ſh/sh inconsistency that makes positional restoration ~90%). Confirming it is evidence, not a no-op."""
    out = s_arbiter.transfer("zzz qqq", "shal fountaine")
    done = s_arbiter.arbitrate(out, {0: "shal", 1: "fountaine"})
    assert [t["source"] for t in done["tokens"]] == ["vision-observed", "vision-observed"]
    assert done["unresolved"] == []


# ---------------------------------------------------------------- verdict: closure uses the OPENING instrument

def test_verdict_closes_only_when_nothing_is_left_undecided():
    out = s_arbiter.transfer("and he was zzzqq", "and he was servant")
    assert s_arbiter.verdict(out, "and he was zzzqq")["state"] == "OPEN"
    done = s_arbiter.arbitrate(out, {3: "ſervant"})
    assert s_arbiter.verdict(done, "and he was zzzqq")["state"] == "CLOSED"


def test_verdict_is_measured_by_the_same_s_ratio_that_opened_the_debt():
    """r3_route opens the debt when r3_ſ < s_ratio * r2_ſ. Closure must be judged by that same test, or the
    debt could be 'closed' at a surface poorer than the one the gate rejected."""
    r2 = "bleſſed ſhal zzz"
    out = s_arbiter.transfer(r2, "blessed shal come")   # 'come' carries no ſ-decision -> nothing to arbitrate
    v = s_arbiter.verdict(out, r2)
    assert v["state"] == "CLOSED"                       # both agreeing tokens took their observed ſ
    assert v["s_count"] >= v["r2_s_count"] == 3

    lossy = s_arbiter.transfer(r2, "blessed shal come")
    lossy["tokens"][1]["text"] = "shal"                 # simulate a surface that lost an attested ſ
    lossy["text"] = " ".join(t["text"] for t in lossy["tokens"])
    assert s_arbiter.verdict(lossy, r2)["state"] == "ALERT"


def test_the_module_never_uses_the_positional_restoration_rule():
    """A durable guard: rule-restored ſ is ~90% accurate and must never reach the deliverable through here."""
    src = open(s_arbiter.__file__.replace(".pyc", ".py"), encoding="utf-8").read()
    body = src.split('"""', 2)[-1]                      # ignore the docstring, which discusses it
    assert "restore_long_s" not in body


def test_every_emitted_glyph_is_provenanced():
    """No token may reach the text without saying where its surface came from — the audit property the whole
    ladder rests on."""
    out = s_arbiter.transfer("and he was bleſſed zzzqq", "and he was blessed servant")
    done = s_arbiter.arbitrate(out, {4: "ſervant"})
    assert {t["source"] for t in done["tokens"]} <= {"R2-observed", "vision-observed", "R3-content", "no-decision"}
    for t in done["tokens"]:
        if "ſ" in t["text"]:
            assert t["source"] in ("R2-observed", "vision-observed")

#!/usr/bin/env python3
"""Deterministic long-ſ placement rule + validator (R12) — reference-free archaic fidelity (Phase 1).

QC contract §1.4 step 4: archaic identity ſ-FOLDS both sides (so ſ/s does not penalise the letter metric),
and ſ *placement* is checked separately here. For the 24 later-OT books that have NO archaic reference
(s_dismas reaches only Genesis→Wisdom; odr_com is partial), this rule-based conformance is the archaic
gate's substitute (plan R12): a diplomatic OCR that correctly places ſ scores high; one that silently
normalised ſ→s (or misread ſ) scores low — a reference-free quality signal.

THE RULE (1582–1610 English/Latin printing, the near-universal core):
  * lowercase s-glyphs: round `s` word-FINALLY (and before an apostrophe); long `ſ` everywhere else
    (initial + medial). This single positional rule yields the correct compounds automatically:
      medial double-s -> ſſ  (Bleſſed),  word-final double-s -> ſs  (wickedneſs),  initial/medial -> ſ.
  * Capital `S` is ALWAYS round (no capital long-ſ existed) → excluded from the check.
  * Deliberately OMITS the printer-inconsistent before-f and before-b/k conventions (they only stabilised
    in later 18th-c. English; applying them to 1582–1610 DR would manufacture false violations).

Emits per text: conformance (0..1), the hard word-final-ſ violation count, the soft medial-round-s count
(the ſ-normalisation tell), has_long_s, and a rule_pass verdict for the no-archaic-reference case.
"""
from __future__ import annotations
import re

# words including long-ſ and an internal apostrophe (round-s-before-apostrophe rule).
_WORD_RE = re.compile(r"[A-Za-zſ]+(?:'[A-Za-zſ]+)*")
THRESHOLD = 0.90


def _is_final_s_position(word: str, i: int) -> bool:
    """True if the s-glyph at index i sits in a word-final position (last char, or immediately before an
    apostrophe) → the rule wants round s there; long ſ everywhere else."""
    if i == len(word) - 1:
        return True
    return word[i + 1] == "'"


def evaluate(text: str) -> dict:
    """Long-ſ placement conformance for a diplomatic text (reference-free)."""
    total = correct = 0
    final_long_s_violations = 0   # ſ where the rule wants round s (hard error / OCR misread)
    medial_round_s = 0            # round s where the rule wants ſ (soft: the ſ-normalisation tell)
    has_long_s = "ſ" in text
    for w in _WORD_RE.findall(text):
        for i, ch in enumerate(w):
            if ch not in ("s", "ſ"):   # lowercase only; capital S is always round, apostrophes skipped
                continue
            total += 1
            want_long = not _is_final_s_position(w, i)
            is_long = ch == "ſ"
            if is_long == want_long:
                correct += 1
            elif is_long and not want_long:
                final_long_s_violations += 1
            else:  # round s where long was expected
                medial_round_s += 1
    conformance = correct / total if total else 1.0
    return {
        "conformance": round(conformance, 4),
        "n_s_glyphs": total,
        "final_long_s_violations": final_long_s_violations,
        "medial_round_s": medial_round_s,
        "has_long_s": has_long_s,
    }


def restore_long_s(text: str) -> str:
    """Positional ſ-restoration for a MODERNIZED (all-round-s) transcription — the inverse of `evaluate`'s rule:
    a lowercase 's' becomes long ſ unless it is word-final or immediately before an apostrophe; capital S and
    word-final s stay round.

    USE WITH CARE — this is a LABELED surface-completion utility, NOT ground truth. Measured accuracy on this
    project's gold surface is ~90.4% (527/583 ſ-positions): DR's ſ is glyph-driven, not purely positional (the
    ſh/sh distinction especially is inconsistent — 45 of the 56 errors are 's before h'). So a restored ſ is an
    APPROXIMATION of the printed surface, ~1-in-10 wrong. Apply it only when explicitly chosen (e.g. to give a
    content-faithful olmOCR transcript an approximate diplomatic surface) and RECORD that ſ is rule-restored,
    never observed — the ſ-faithful surface comes from a visual recognizer (reichenau/R2, or the Claude arbiter),
    never from this rule silently (No Silent Degradation / AI_OCR: don't pass off inserted glyphs as observed)."""
    def _fix(m):
        w = list(m.group(0))
        for i, ch in enumerate(w):
            if ch == "s" and not _is_final_s_position("".join(w), i):
                w[i] = "ſ"
        return "".join(w)
    return _WORD_RE.sub(_fix, text)


def rule_pass(text: str, threshold: float = THRESHOLD) -> bool:
    """Archaic gate for the no-archaic-reference case (R12): the text must actually USE long-ſ, place it
    conformantly, and carry no word-final ſ violations."""
    r = evaluate(text)
    return bool(r["has_long_s"] and r["conformance"] >= threshold and r["final_long_s_violations"] == 0)


if __name__ == "__main__":
    ok = True

    # (1) correctly-placed diplomatic text → high conformance, no violations, uses ſ.
    good = "Bleſſed is the man that walketh not, and ſpeaketh of wickedneſs and juſtice"
    rg = evaluate(good)
    print(f"[conformant diplomatic] {rg}")
    ok = ok and rg["conformance"] >= 0.99 and rg["final_long_s_violations"] == 0 and rg["has_long_s"]
    ok = ok and rule_pass(good)

    # (2) ſ-normalised OCR (all round s, no ſ) → low conformance on medial positions, fails rule_pass.
    normalized = "Blessed is the man that walketh not, and speaketh of wickednes and justice"
    rn = evaluate(normalized)
    print(f"[ſ-normalised OCR]      {rn}")
    ok = ok and (not rn["has_long_s"]) and rn["medial_round_s"] > 0 and not rule_pass(normalized)

    # (3) word-final ſ misread (should be round s) → hard violation flagged, rule_pass fails.
    misread = "Bleſſed is the manſ ſonſ"  # ſ word-final on 'manſ'/'ſonſ'
    rm = evaluate(misread)
    print(f"[word-final ſ misread]  {rm}")
    ok = ok and rm["final_long_s_violations"] >= 2 and not rule_pass(misread)

    # (4) double-s compounds: medial ſſ + final ſs are both conformant.
    dbl = "poſſeſſion of wickedneſs"   # ſſ medial, ſs final
    rd = evaluate(dbl)
    print(f"[double-s compounds]    {rd}")
    ok = ok and rd["conformance"] >= 0.99 and rd["final_long_s_violations"] == 0

    # (5) capital S is always round → not a violation, not counted.
    cap = "Sion and Salem, the ſeat of ſalvation"  # initial capital S round (correct), medial ſ
    rc = evaluate(cap)
    print(f"[capital S round]       {rc}")
    ok = ok and rc["final_long_s_violations"] == 0 and rc["conformance"] >= 0.99

    print("\nSELF-CHECK:", "PASS" if ok else "FAIL")
    raise SystemExit(0 if ok else 1)

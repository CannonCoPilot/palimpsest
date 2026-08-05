#!/usr/bin/env python3
"""Character-level identity metric — the QC measurement backbone (Phase 1, 2026-07-08).

QC contract §1.4: the OCR identity bar is CHARACTER-level (today's consensus_v2.sim() is token-level).
For each OCR locus text the 5-step bootstrap yields two scores against two references at once:

  MODERN identity  = char-ratio(fold_modern(ocr), fold_modern(janvier))   — did OCR capture the CONTENT?
  ARCHAIC identity = char-ratio(fold_archaic(ocr), fold_archaic(s_dismas)) — did it capture the diplomatic SURFACE?
  PASS iff modern >= T AND (archaic >= T OR no archaic reference exists for the locus).   [T = 0.90]

The two folds ask opposite questions and MUST differ:
  * fold_modern reuses spelling_glyph_model.fold_diplomatic — the modern-neutral *skeleton* (NFKD drop
    combining ſ->s/accents, æ->ae, vv->w, v->u, j->i, y->i, strip trailing silent -e, collapse doubles).
    Archaic and modern spellings of the SAME word collapse identically, so archaic OCR can be scored
    against modern Janvier. Measures content, ignores all spelling/typography.
  * fold_archaic is a LIGHT fold: lowercase, ſ->s (ſ *placement* is checked separately by long_s_rule.py,
    so ſ/s must not penalise the letter metric), vv->w, v->u, j->i, æ->ae, œ->oe — but KEEPS archaic
    spelling (trailing -e, doubled letters, y). "Prophete" stays "prophete" and must match s_dismas, not
    modern "prophet". Measures surface fidelity.

Gate metric = normalized Levenshtein (`edit_ratio`, QC §1.4 DECIDED 2026-07-08): `1 - editdist(a,b)/max(len)`
over the folded character stream. difflib.SequenceMatcher.ratio (`char_ratio`) is retained only as a fast
C-backed SKIP-PREFILTER: it over-scores vs true edit distance, so when it already reads < 0.80 the pair
cannot clear the 0.90 gate and we short-circuit to 0.0, skipping the O(nm) edit-distance DP. Reference-free
ſ-rule conformance is the separate concern of long_s_rule.py (R12); this module deliberately ſ-folds so the
two don't double-count.
"""
from __future__ import annotations
import difflib
import re
import sys
from pathlib import Path

RECON = Path("/Users/nathanielcannon/Claude/Projects/palimpsest/core/tests/fixtures/gold/"
             "mask_engine/originaldr_reconstruction")
sys.path.insert(0, str(RECON))
import spelling_glyph_model as G  # noqa: E402  # type: ignore[import-not-found]

THRESHOLD = 0.90
_WORD_RE = re.compile(r"[^\W\d_]+", re.UNICODE)  # unicode letter runs incl. ſ + accents
_WS_RE = re.compile(r"\s+")
_S_WORD_RE = re.compile(r"[A-Za-zſ]+(?:'[A-Za-zſ]+)*")  # words incl. long-ſ + apostrophe (f/ſ scan)


# --------------------------------------------------------------------------- #
# folds → character streams
# --------------------------------------------------------------------------- #
def fold_modern(text: str) -> str:
    """Modern-neutral skeleton char stream (content metric). Reuses spelling_glyph_model.fold_diplomatic
    per word so archaic and modern of the same word collapse identically; joins with single spaces."""
    return " ".join(f for f in (G.fold_diplomatic(w) for w in _WORD_RE.findall(text)) if f)


def fold_archaic(text: str) -> str:
    """Light archaic-surface char stream (surface metric). ſ->s (placement checked elsewhere) + typography
    (vv->w, v->u, j->i) + æ/œ expand, but KEEPS archaic spelling (trailing -e, doubles, y)."""
    t = text.lower().replace("ſ", "s").replace("æ", "ae").replace("œ", "oe").replace("vv", "w")
    t = t.replace("v", "u").replace("j", "i")
    t = re.sub(r"[^a-z\s]", "", t)
    return _WS_RE.sub(" ", t).strip()


# --------------------------------------------------------------------------- #
# character-level ratios
# --------------------------------------------------------------------------- #
def char_ratio(a: str, b: str) -> float:
    """difflib character-similarity ratio (0..1), autojunk off. Empty/empty = 1.0; one-empty = 0.0."""
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return difflib.SequenceMatcher(a=a, b=b, autojunk=False).ratio()


def edit_ratio(a: str, b: str) -> float:
    """1 - levenshtein(a,b)/max(len) — a normalized-edit secondary (more standard 'char identity')."""
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    la, lb = len(a), len(b)
    prev = list(range(lb + 1))
    for i in range(1, la + 1):
        cur = [i] + [0] * lb
        ca = a[i - 1]
        for j in range(1, lb + 1):
            cost = 0 if ca == b[j - 1] else 1
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost)
        prev = cur
    return 1.0 - prev[lb] / max(la, lb)


def identity_ratio(a: str, b: str) -> float:
    """The GATE metric (QC §1.4 DECIDED): normalized Levenshtein with a difflib skip-prefilter.

    char_ratio (difflib) over-scores relative to edit distance, so if it already reads < 0.80 the pair
    cannot clear the 0.90 identity gate — return 0.0 and skip the O(nm) edit-distance DP. Otherwise return
    the exact edit_ratio. The prefilter only zeroes far-failures (which are deep-red on the report either
    way); every score in the gate-relevant band [0.80, 1.0] is the exact normalized Levenshtein."""
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    if char_ratio(a, b) < 0.80:
        return 0.0
    return edit_ratio(a, b)


def modern_identity(ocr_text: str, janvier_text: str) -> float:
    return identity_ratio(fold_modern(ocr_text), fold_modern(janvier_text))


def archaic_identity(ocr_text: str, s_dismas_text: str) -> float:
    return identity_ratio(fold_archaic(ocr_text), fold_archaic(s_dismas_text))


# --------------------------------------------------------------------------- #
# §1.4 scoped-re-OCR-routing primitives (QC contract, rev 2026-07-10)
# --------------------------------------------------------------------------- #
def floor_modern(archaic_ref: str | None, modern_ref: str | None) -> float | None:
    """Modern-yardstick validity (§1.4 sub-rule 3). Aligns the TRANSCRIBED ARCHAIC reference against the
    modern (Janvier) reference under the modern content fold — REFERENCES only, no OCR. High => the printed
    1582/1610 text and the modern edition agree in content, so modern_id is a valid OCR yardstick here.
    Low (< 0.90) => the modern edition genuinely diverges from the printed text at this locus, so modern_id
    is a partially-invalid yardstick: gating must redirect to the archaic / in-family instrument (never burn
    re-OCR chasing the modern number, never accept the locus on it). Returns None if either ref is absent
    (divergence is unassessable — do not spuriously invalidate)."""
    if not (archaic_ref and archaic_ref.strip()) or not (modern_ref and modern_ref.strip()):
        return None
    return round(identity_ratio(fold_modern(archaic_ref), fold_modern(modern_ref)), 4)


def _medial_f_count(text: str) -> int:
    """'f' glyphs in a NON-word-final (ſ-expected) position — the positions a long-ſ would occupy."""
    n = 0
    for w in _S_WORD_RE.findall(text):
        for i, ch in enumerate(w):
            if ch == "f" and not (i == len(w) - 1 or (i + 1 < len(w) and w[i + 1] == "'")):
                n += 1
    return n


def suspected_long_s_as_f(ocr_text: str, archaic_ref: str | None = None) -> dict:
    """f→ſ misread pre-check (§1.4 step 4). A diplomatic OCR that emits NO long-ſ yet carries 'f' in medial/
    initial (ſ-expected) positions is a suspected ſ→f RECOGNITION error (the model read long-ſ as f), NOT a
    benign ſ→s normalisation — route to re-OCR for ſ-fidelity, never accept as a surface variant. Reference-
    aware: excess_f = the OCR's medial-f over the archaic reference's medial-f estimates the number of ſ→f
    misreads (genuine f's cancel). Fires only when the OCR lost long-ſ entirely and the reference uses it.
    A heuristic ſ-fidelity SIGNAL, not a gate."""
    ocr_has_long_s = "ſ" in ocr_text
    ref_has_long_s = bool(archaic_ref) and "ſ" in archaic_ref
    ocr_mf = _medial_f_count(ocr_text)
    ref_mf = _medial_f_count(archaic_ref) if archaic_ref else 0
    excess_f = max(0, ocr_mf - ref_mf)
    if archaic_ref is None:
        suspected = (not ocr_has_long_s) and ocr_mf > 0          # reference-free: weaker signal
    else:
        suspected = (not ocr_has_long_s) and ref_has_long_s and excess_f > 0
    return {
        "suspected_long_s_as_f": bool(suspected), "excess_f": excess_f,
        "ocr_medial_f": ocr_mf, "ref_medial_f": ref_mf,
        "ocr_has_long_s": ocr_has_long_s, "ref_has_long_s": ref_has_long_s,
    }


# --------------------------------------------------------------------------- #
# the 5-step bootstrap verdict (QC §1.4)
# --------------------------------------------------------------------------- #
def evaluate_locus(ocr_text: str, modern_ref: str | None, archaic_ref: str | None,
                   threshold: float = THRESHOLD) -> dict:
    """Archaic-preeminent OCR-identity verdict for one locus (QC §1.4, REVISED 2026-07-10, Sir).

    modern_ref = Janvier/sabates_a (madueke_b backfill upstream); archaic_ref = s_dismas (odr_com backfill
    upstream), or None if no archaic reference exists at the locus. BOTH scores are always computed and
    reported. The GOVERNING gate is archaic-preeminent:

      * archaic_ref exists  -> PASS iff archaic_id >= T. The archaic gate is the quality bar; modern_id is a
        recorded signal but does NOT gate (a faithful 1582 OCR must not fail for diverging from a modern
        edition).
      * else, modern_ref exists -> PASS iff modern_id >= T. The only place the modern gate governs.
      * neither reference       -> governing_gate = 'needs-reference', passed = False (loud OPEN state; never
        a silent pass, per No Silent Degradation).
    """
    modern_ref_exists = modern_ref is not None and modern_ref.strip() != ""
    archaic_ref_exists = archaic_ref is not None and archaic_ref.strip() != ""
    modern_id = modern_identity(ocr_text, modern_ref) if (modern_ref is not None and modern_ref.strip() != "") else None
    archaic_id = archaic_identity(ocr_text, archaic_ref) if (archaic_ref is not None and archaic_ref.strip() != "") else None
    modern_pass = modern_id is not None and modern_id >= threshold
    archaic_pass = archaic_id is not None and archaic_id >= threshold
    if archaic_ref_exists:
        governing_gate, passed = "archaic", archaic_pass
    elif modern_ref_exists:
        governing_gate, passed = "modern", modern_pass
    else:
        governing_gate, passed = "needs-reference", False
    return {
        "modern_id": round(modern_id, 4) if modern_id is not None else None,
        "archaic_id": round(archaic_id, 4) if archaic_id is not None else None,
        "modern_ref_exists": modern_ref_exists,
        "archaic_ref_exists": archaic_ref_exists,
        "modern_pass": modern_pass,
        "archaic_pass": archaic_pass,
        "governing_gate": governing_gate,
        "passed": bool(passed),
        "threshold": threshold,
    }


if __name__ == "__main__":
    # Self-check: the two folds ask opposite questions. Uses genuine archaic spellings that SURVIVE the
    # light fold (trailing silent -e: olde/old, worde/word; doubled: Sonne/Son, bee/be; -ie/-y: manie/many)
    # — as opposed to pure typography (vv/w, u/v, ſ/s) which both folds correctly treat as identical.
    ok = True
    ocr = "The olde Sonne ſpeaketh manie true vvordes and bee glorified"  # archaic OCR surface
    janvier = "The old Son speaketh many true words and be glorified"       # modern content ref
    sdismas = "The olde Sonne ſpeaketh manie true wordes and bee glorified"  # archaic diplomatic ref

    # (1) content captured despite archaic spelling → modern_id high (skeleton fold collapses olde->old etc.)
    m = modern_identity(ocr, janvier)
    print(f"[modern content match]     archaic-vs-modern  modern_id={m:.3f}  (expect >= 0.90)")
    ok = ok and m >= 0.90

    # (2) archaic surface matches the archaic diplomatic reference → archaic_id high.
    a_ref = archaic_identity(ocr, sdismas)
    print(f"[archaic surface match]    archaic-vs-sdismas archaic_id={a_ref:.3f}  (expect >= 0.90)")
    ok = ok and a_ref >= 0.90

    # (3) the archaic metric DISCRIMINATES: the archaic surface must prefer the archaic ref over the modern
    #     one (olde/Sonne/manie/wordes survive the fold and differ from old/Son/many/words). The gap is
    #     per-differing-word, so it compounds at chapter scale; a short sentence shows a modest but real gap.
    a_mod = archaic_identity(ocr, janvier)
    print(f"[archaic discriminates]    archaic-vs-modern  archaic_id={a_mod:.3f}  (expect < archaic-vs-sdismas by a real margin)")
    ok = ok and (a_ref - a_mod) >= 0.05

    # (4) pure-typography differences (vv/w, u/v, ſ/s) must NOT lower either metric — they are glyph noise.
    typo = "The olde Sonne speaketh manie true wordes and bee glorified"  # w for vv, no ſ
    a_typo = archaic_identity(ocr, typo)
    print(f"[typography invariant]     ſ/vv folded         archaic_id={a_typo:.3f}  (expect ~1.0)")
    ok = ok and a_typo >= 0.99

    # (5) garbage OCR fails the modern content gate.
    garbage = "xqz mmm lll ttt zzz qqq vbn plmk"
    mg = modern_identity(garbage, janvier)
    print(f"[garbage fails]            garbage            modern_id={mg:.3f}  (expect < 0.90)")
    ok = ok and mg < 0.90

    # (6) both refs present → archaic gate GOVERNS; clean archaic OCR passes.
    v = evaluate_locus(ocr, janvier, sdismas)
    print(f"[verdict clean] passed={v['passed']} gate={v['governing_gate']} modern={v['modern_id']} archaic={v['archaic_id']}")
    ok = ok and v["passed"] and v["governing_gate"] == "archaic"

    # (7) no archaic ref → modern gate governs.
    v2 = evaluate_locus(ocr, janvier, None)
    print(f"[verdict no-archaic-ref] passed={v2['passed']} gate={v2['governing_gate']} archaic_ref_exists={v2['archaic_ref_exists']}")
    ok = ok and v2["passed"] and v2["governing_gate"] == "modern" and not v2["archaic_ref_exists"]

    # (8) ARCHAIC-PREEMINENCE: modern FAILS (OCR diverges from the modern edition) but archaic PASSES →
    #     the faithful-1582 reading is kept, not discarded. This is the core behavioral change.
    v3 = evaluate_locus(ocr, "totally unrelated modern sentence about weather and traffic today", sdismas)
    print(f"[archaic-preeminent] passed={v3['passed']} gate={v3['governing_gate']} modern_pass={v3['modern_pass']} archaic_pass={v3['archaic_pass']}")
    ok = ok and v3["passed"] and not v3["modern_pass"] and v3["governing_gate"] == "archaic"

    # (9) neither reference → needs-reference OPEN state, never a silent pass.
    v4 = evaluate_locus(ocr, None, None)
    print(f"[needs-reference] passed={v4['passed']} gate={v4['governing_gate']}  (expect passed=False)")
    ok = ok and (not v4["passed"]) and v4["governing_gate"] == "needs-reference"

    # (10) floor_modern: archaic & modern refs that AGREE in content -> valid yardstick (>= 0.90); refs that
    #      genuinely diverge -> invalid yardstick (< 0.90); a missing ref -> None (unassessable).
    fm_ok = floor_modern(sdismas, janvier)
    fm_bad = floor_modern("The archaic reading here is wholly other in substance and wording", janvier)
    print(f"[floor_modern valid]  archaic~modern floor={fm_ok}  (expect >= 0.90)")
    print(f"[floor_modern invalid] divergent floor={fm_bad}  (expect < 0.90)")
    ok = ok and fm_ok is not None and fm_ok >= 0.90 and fm_bad is not None and fm_bad < 0.90
    ok = ok and floor_modern(None, janvier) is None

    # (11) f→ſ misread pre-check: OCR that lost long-ſ and shows medial f where the ref has ſ -> suspected;
    #      a faithful ſ-using OCR -> not suspected.
    fmis = suspected_long_s_as_f("Blefled is the man and the juftice of falvation", sdismas)  # ſ→f misreads
    fok = suspected_long_s_as_f(sdismas, sdismas)                                              # ſ preserved
    print(f"[f→ſ suspected] {fmis['suspected_long_s_as_f']} excess_f={fmis['excess_f']}  (expect True)")
    print(f"[f→ſ clean]     {fok['suspected_long_s_as_f']}  (expect False)")
    ok = ok and fmis["suspected_long_s_as_f"] and fmis["excess_f"] > 0 and not fok["suspected_long_s_as_f"]

    print("\nSELF-CHECK:", "PASS" if ok else "FAIL")
    raise SystemExit(0 if ok else 1)

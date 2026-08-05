#!/usr/bin/env python3
"""glyph_map.py — reversible archaic⇄modern-core glyph mapping for OriginalDR (Sir's 1B, 2026-07-18).

Design (Sir's call):
  * The CORE transcription uses MODERN BASE CHARACTERS but preserves the ARCHAIC SPELLING.
    e.g. "vnderſtand" -> core "vnderstand"  (ſ->s; the archaic spelling vnder-stand is kept, NOT "understand").
  * A compact, reversible VARIANT list rides alongside so a fully glyph-archaic string can be re-emitted.
  * Goal: search / embeddings / edit-distance operate on clean ASCII-ish core text; nothing is lost.

Core is what Palimpsest ingests. Archaic is emittable for other projects via decode(core, variants).

Two representations, one source of truth:
  encode(archaic) -> (core, variants)     # core = modern base; variants = [{i,n,t,a}]
  decode(core, variants) -> archaic       # exact inverse; round-trip guaranteed by tests

variant entry: {"i": core_offset, "n": core_len, "t": type, "a": archaic_slice}
  n == 0  => the archaic slice is a pure MARKER absent from core (e.g. stripped '†'); re-inserted on decode.

u/v and i/j are NOT mapped — they are archaic SPELLING (period-swap), kept in core verbatim.
"""
from __future__ import annotations

# ─── comprehensive archaic-glyph → (modern-core, variant-type) map ───────────────────────────
# Each maps one archaic char to its modern-base string + a variant tag for reversal.
GLYPH = {
    "ſ": ("s",  "LONG_S"),     # long-s  (U+017F) — 1423×, the big one
    "ﬅ": ("st", "ST_LIG"),     # ſt ligature (U+FB05)
    "ﬆ": ("st", "ST_LIG"),     # st ligature (U+FB06)
    "æ": ("ae", "AE_LIG"),     # U+00E6
    "Æ": ("Ae", "AE_LIG"),     # U+00C6
    "œ": ("oe", "OE_LIG"),
    "Œ": ("Oe", "OE_LIG"),
}
# macron / tilde vowels = scribal abbreviation of a following nasal (n, occasionally m).
# core EXPANDS to vowel+nasal so the word is searchable ("diſpēſeth" -> "dispenseth"); variant is reversible.
# default nasal = 'n'; the rare 'm' cases are listed in NASAL_M by (archaic-char, following-context) override.
MACRON = {
    "ā": "a", "ē": "e", "ī": "i", "ĩ": "i", "ō": "o", "õ": "o", "ũ": "u", "ū": "u",
    "ã": "a", "ñ": "n",  # ñ is n+tilde; here treat as the letter n (Spanish loan) — no expansion
    # NB: both u+macron (ū U+016B) and u+tilde (ũ U+0169) occur for the same nasal abbrev
    #     (Sūday=Sunday, Mūday=Munday, vvhitſū=vvhitsun in matter-nt-table-of-epistles).
}
# markers that Sir wants STRIPPED from produced output but recorded (verse dividers, footnote anchors).
# '†','‡' = verse dividers (Sir 2026-07-18: strip). '‖' = footnote anchor. '″' = ditto/prime apparatus mark.
MARKERS_STRIP = {"†": "DAGGER", "‡": "DDAGGER", "‖": "ANCHOR", "″": "PRIME",
                 "⁘": "QUAD_DOT", "⊣": "LEFT_TACK"}  # legend/reference marks (E5b): stripped from core, recorded
# accented Latin letters in citations/proper nouns → ASCII fold for core, variant preserves the accent.
ACCENT = {"ô": "o", "è": "e", "é": "e", "à": "a", "û": "u", "î": "i", "â": "a", "ç": "c"}


def encode(archaic: str) -> tuple[str, list[dict]]:
    """archaic glyph text -> (modern-core, reversible variant list)."""
    core_parts: list[str] = []
    variants: list[dict] = []
    pos = 0  # running offset into core
    i = 0
    while i < len(archaic):
        ch = archaic[i]
        if ch == "⟨":  # uncertainty notation ⟨X?⟩ (guess X) or ⟨?⟩ (unknown); keep guess, record for reversal
            j = archaic.find("⟩", i)
            if j != -1:
                whole = archaic[i:j + 1]          # e.g. "⟨2?⟩"
                guess = whole[1:-1].split("?")[0]  # chars before '?' -> "2"  (or "" for ⟨?⟩)
                core_parts.append(guess)
                variants.append({"i": pos, "n": len(guess), "t": "UNCERTAIN", "a": whole}); pos += len(guess)
                i = j + 1
                continue
        if ch in GLYPH:
            base, typ = GLYPH[ch]
            core_parts.append(base); variants.append({"i": pos, "n": len(base), "t": typ, "a": ch}); pos += len(base)
        elif ch in MACRON:
            base = MACRON[ch]
            if ch == "ñ":  # standalone n, no nasal expansion
                core_parts.append("n"); variants.append({"i": pos, "n": 1, "t": "TILDE_N", "a": ch}); pos += 1
            else:          # vowel + omitted nasal -> vowel+n in core
                exp = base + "n"
                core_parts.append(exp); variants.append({"i": pos, "n": len(exp), "t": "MACRON_NASAL", "a": ch}); pos += len(exp)
        elif ch in MARKERS_STRIP:
            variants.append({"i": pos, "n": 0, "t": MARKERS_STRIP[ch], "a": ch})  # stripped: absent from core
        elif ch in ACCENT:
            core_parts.append(ACCENT[ch]); variants.append({"i": pos, "n": 1, "t": "ACCENT", "a": ch}); pos += 1
        else:
            core_parts.append(ch); pos += 1
        i += 1
    return "".join(core_parts), variants


def decode(core: str, variants: list[dict]) -> str:
    """(modern-core, variants) -> exact archaic glyph text. Inverse of encode()."""
    # apply variants right-to-left so earlier offsets stay valid
    out = core
    for v in sorted(variants, key=lambda v: v["i"], reverse=True):
        i, n = v["i"], v["n"]
        out = out[:i] + v["a"] + out[i + n:]
    return out


def to_core(archaic: str) -> str:
    """Convenience: just the modern-base core (for search/embeddings/edit-distance)."""
    return encode(archaic)[0]


if __name__ == "__main__":
    # self-test: round-trip every GT text field + report any unmapped non-ASCII left in core
    import json, glob, sys, unicodedata
    from pathlib import Path
    GT = Path(__file__).resolve().parent / "ground-truth"
    def fields(d):
        for L in d.get("body", []):
            if isinstance(L.get("text"), str): yield L["text"]
        for a in d.get("apparatus", []):
            if isinstance(a.get("text"), str): yield a["text"]
        for m in d.get("marginalia", []):
            if isinstance(m.get("text"), str): yield m["text"]
        for k in ("book_title", "chapter_heading"):
            if isinstance(d.get(k), str): yield d[k]
        a = d.get("argument")
        if isinstance(a, dict) and isinstance(a.get("text"), str): yield a["text"]
    n_fields = n_fail = 0
    leftover = {}
    for f in sorted(glob.glob(str(GT / "*.json"))):
        d = json.loads(Path(f).read_text())
        for t in fields(d):
            n_fields += 1
            core, variants = encode(t)
            if decode(core, variants) != t:
                n_fail += 1
                print(f"  ROUND-TRIP FAIL in {Path(f).name}: {t[:60]!r}")
            for ch in core:
                if ord(ch) > 127:
                    leftover.setdefault(ch, 0); leftover[ch] += 1
    print(f"round-trip: {n_fields - n_fail}/{n_fields} fields exact")
    if leftover:
        print("UNMAPPED non-ASCII left in core (extend the map!):")
        for ch, c in sorted(leftover.items(), key=lambda x: -x[1]):
            try: nm = unicodedata.name(ch)
            except ValueError: nm = "?"
            print(f"    U+{ord(ch):04X} {ch!r} x{c}  {nm}")
    else:
        print("core is clean ASCII/spelling-only — no unmapped archaic glyphs remain.")
    sys.exit(1 if n_fail else 0)

#!/usr/bin/env python3
"""§6.1 bidirectional spelling-glyph model — the archaic<->modern fold for the OriginalDR gold works.

This is the operational half of ``spelling-glyph-model.json`` (the documented spec): a per-word
fold that reduces BOTH the modern (idx 108) and archaic (idx 109) surfaces to a spelling/glyph-
neutral skeleton, so the §6.2 word-for-word correspondence check (``validate_archaic_fidelity.py``)
isolates genuine wording differences from expected orthographic variation.

Design note — why this is NOT ``ocr_sample.skel``: that fold folds long-ſ SYMMETRICALLY with 'f'
(``f<->s``) to tolerate tesseract misreading long-ſ as 'f'. Folding that here would MASK the
fresh-OCR ``ſ->f`` defect as a match and hide a real diplomatic-fidelity problem in the OCR-only
books. This fold keeps f and s distinct so §6.2 SEES the defect; long-ſ (U+017F) still folds to 's'
via its NFKD decomposition (it is a genuine long-s, not an OCR 'f').

Round-trippable glyph rules (ſ<->s, æ<->ae, œ<->oe, vv<->w, &<->and) and the lossy period-spelling /
positional-u-v-i-j patterns are catalogued in the JSON; the archaic gold text restores every archaic
form from the WITNESS, never from a lossy inverse of the modern text (plan §5.3, §6.1).
"""
from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

HERE = Path(__file__).resolve().parent
MODEL_JSON = HERE / "spelling-glyph-model.json"

_LIG = (("æ", "ae"), ("œ", "oe"), ("Æ", "ae"), ("Œ", "oe"))
# Unicode letter runs — MUST include long-ſ (U+017F) and precomposed accents (õ, ô, ã) so archaic
# words like "Bleſſed" / "cõfeſſe" tokenise whole. A plain [A-Za-z…] class splits on ſ and shreds
# every clean archaic word, artificially deflating the fold-agreement metric.
_WORD_RE = re.compile(r"[^\W\d_]+", re.UNICODE)
_DEDUP_RE = re.compile(r"(.)\1+")
_NONALPHA_RE = re.compile(r"[^a-z]")


def fold_diplomatic(word: str) -> str:
    """Fold one word to the archaic<->modern-neutral skeleton (see spelling-glyph-model.json §fold).

    Steps: NFKD + drop combining (ſ->s, õ->o); æ->ae, œ->oe; vv->w; strip non-[a-z];
    v->u & j->i (positional classes); y->i; strip trailing silent -e; collapse doubled letters.
    """
    w = unicodedata.normalize("NFKD", word.lower())
    w = "".join(c for c in w if not unicodedata.combining(c))
    for a, b in _LIG:
        w = w.replace(a, b)
    w = w.replace("vv", "w")
    w = _NONALPHA_RE.sub("", w)
    w = w.replace("v", "u").replace("j", "i")
    w = w.replace("y", "i")
    w = re.sub(r"e$", "", w)
    w = _DEDUP_RE.sub(r"\1", w)
    return w


def fold_tokens(text: str, min_len: int = 2) -> list[str]:
    """Fold every word in ``text`` to its skeleton, dropping skeletons shorter than ``min_len``."""
    return [f for f in (fold_diplomatic(w) for w in _WORD_RE.findall(text)) if len(f) >= min_len]


def load_model() -> dict:
    return json.loads(MODEL_JSON.read_text(encoding="utf-8"))


if __name__ == "__main__":
    # Self-check: every worked example's modern and archaic surfaces must fold identically.
    model = load_model()
    ok = True
    for ex in model["worked_examples"]:
        fm, fa = fold_tokens(ex["modern"]), fold_tokens(ex["archaic"])
        same = fm == fa == ex["fold"]
        ok = ok and same
        print(f"{'ok ' if same else 'BAD'} modern={fm} archaic={fa} expected={ex['fold']}")
    print("round-trip glyph pairs:", model["reversible_round_trip"])
    raise SystemExit(0 if ok else 1)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""s_arbiter.py — the ſ-faithful arbiter (§12.5 Tier C2): closes RESCUED_CONTENT_S_OPEN without inventing glyphs.

THE DEBT. `r3_route` accepts a verse's CONTENT at R3 (olmOCR lifted it past τx) but olmOCR modernizes ſ, so the
diplomatic SURFACE — the whole point of this project — is lost. Those verses are held OPEN and block the
deliverable. 21 of them sit in `.r3-stats/_open_ledger.json`.

WHY NOT JUST RESTORE ſ POSITIONALLY. `long_s_rule.restore_long_s` is measured at ~90.4% on this project's own
gold surface (DR's ſ is glyph-driven, not purely positional; ſh/sh alone accounts for 45 of its 56 errors).
Publishing it would present ~1-in-10 INVENTED glyphs as the printed surface. That is the laundering No Silent
Degradation forbids, so this module never calls it — closure comes from OBSERVATION or the debt stays OPEN.

THE METHOD — SURFACE TRANSFER, THEN A BOUNDED VISUAL RESIDUE.
R2 (kraken + reichenau_lat) is itself an ſ-FAITHFUL visual recognizer; it is only its CONTENT the gate rejected.
So a token that R2 and R3 read identically MODULO THE ſ-FOLD is a token whose content R3 confirms and whose
surface R2 observed — adopt R2's spelling. Only where R3 CORRECTED R2 is the ſ genuinely unattested; those
tokens are itemised as `unresolved` for the in-session vision arbiter (I read the crop myself; NO paid API).

THE FOLD IS ſ-ONLY, deliberately narrower than `verse_seg._afold`. Folding u/v, i/j or case would let a token
R3 corrected register as "agreeing" with R2 and hand the deliverable R2's rejected reading back under the guise
of a surface adoption.

CLOSURE USES THE INSTRUMENT THAT OPENED THE DEBT. `verdict` re-applies r3_route's own test (ſ count vs R2 at
`s_ratio`). A debt may not be closed at a surface poorer than the one the gate rejected; if the arbitrated text
is still deficient the state is ALERT (the approach needs redesign), never a quiet accept.

Provenance is carried per token — every ſ that reaches the deliverable can name the eye that saw it.
"""
from __future__ import annotations

import difflib
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

LONG_S = "ſ"
S_RATIO = 1.0            # r3_route's default: any ſ lost vs R2 is a regression
_WORD_RE = re.compile(r"[A-Za-zſ]+(?:'[A-Za-zſ]+)*")


def sfold(text: str) -> str:
    """The ONLY fold this module performs: ſ -> s. Nothing else (see module docstring)."""
    return text.replace(LONG_S, "s")


def _diplomatic_equal(a: str, b: str) -> bool:
    """Are these the SAME WORD under the project's diplomatic fold — i.e. archaic and modern spellings of one
    word? Used only to recognise that R2's archaic token and R3's modernized token are the same word, so R2's
    OBSERVED spelling can be kept instead of R3's modernization."""
    from char_identity import fold_modern
    fa, fb = fold_modern(a), fold_modern(b)
    return bool(fa) and fa == fb


def _skeleton(text: str) -> str:
    """Content skeleton for the arbitration guard: the three glyphs the ſ SURFACE may legitimately move between
    (ſ / s / f) collapse to one; every other letter must be preserved exactly. So `haift` -> `haiſt` is a surface
    observation and passes, while `ſaid` -> `ſayd` is a content edit and is refused."""
    return text.replace(LONG_S, "s").replace("f", "s")


def decision_positions(token: str, *, include_f: bool = True) -> list[int]:
    """Indices in `token` whose ſ identity is an OPEN decision — the positions a visual read must settle.

    Excluded, because the 1582-1610 convention leaves them no freedom: capital S (no capital long-ſ existed) and
    word-final position (round s, and before an apostrophe) — the same carve-outs `long_s_rule` documents.

    `f` IS A DECISION POSITION (measured, Tier C2). olmOCR does not only flatten ſ→s; it also misreads ſ as f —
    `haiſt`->`haift`, `anſwere`->`anfwere`, `deſpiſed`->`despifed` on this very debt set. An f-token carries no
    s-glyph, so an s-only detector calls it 'no decision' and ships a wrong surface silently: the confident-wrong
    class, one level below the gate. Flagging medial f over-reports on genuinely-f words (`before`), which is the
    right direction of error — a false residue costs one look at the crop, a missed one corrupts the deliverable."""
    cands = ("s", LONG_S, "f") if include_f else ("s", LONG_S)
    out: list[int] = []
    for m in _WORD_RE.finditer(token):
        w, off = m.group(0), m.start()
        for i, ch in enumerate(w):
            if ch not in cands:
                continue
            final = i == len(w) - 1 or w[i + 1] == "'"
            if not final:
                out.append(off + i)
    return out


def _mk(text: str, source: str) -> dict:
    return {"text": text, "source": source if decision_positions(text) else "no-decision"}


def transfer(r2_text: str, r3_text: str) -> dict:
    """Build the R3 content with R2's OBSERVED ſ surface wherever the two agree modulo the ſ-fold.

    Returns {text, tokens:[{text, source}], unresolved:[{i, token, positions}], n_observed, n_undecided}.
    `source` is one of R2-observed / R3-content / no-decision (and vision-observed after `arbitrate`)."""
    r2_toks, r3_toks = r2_text.split(), r3_text.split()
    a, b = [sfold(t) for t in r2_toks], [sfold(t) for t in r3_toks]
    tokens: list[dict] = [None] * len(r3_toks)  # type: ignore[list-item]
    dropped: list[str] = []

    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(a=a, b=b, autojunk=False).get_opcodes():
        for k in range(j1, j2):
            if tag == "equal":
                tokens[k] = _mk(r2_toks[i1 + (k - j1)], "R2-observed")
            else:
                tokens[k] = _mk(r3_toks[k], "R3-content")
        if tag == "delete":                      # R2-only material R3 did not carry into the verse
            dropped += r2_toks[i1:i2]
        elif tag == "replace":
            # ARCHAIC-EQUIVALENT PAIRS KEEP R2's SPELLING (2026-07-29). olmOCR modernizes SPELLING as well as
            # ſ — `ſeuenth`/`seventh`, `therfore`/`therefore`, `reſted`/`rested` — and because this module's fold
            # is ſ-only those pairs land here as a `replace`, so R3's MODERN token was taken as content and the
            # surface was flagged unresolved. Both halves of that are wrong: the module exists to publish R3's
            # CONTENT WITH R2's OBSERVED SURFACE, and for these pairs R2's token IS the observed surface of the
            # same word. Measured on genesis 2, this single narrowness left 19 of 25 verses OPEN with reasons
            # like `1 ſ kept, 2 unresolved: "rested", seventh` while R3's content scored 0.99 against the
            # governing reference.
            #
            # The equivalence test is the project's own diplomatic fold (`char_identity.fold_modern` per word),
            # the same equivalence class every content score already uses — so a pair it accepts is a pair the
            # deliverable already treats as the same word. It is NOT the loose ſ/s/f skeleton, which would equate
            # genuinely different readings.
            for k in range(j1, j2):
                r3t = r3_toks[k]
                mate = next((t for t in r2_toks[i1:i2] if _diplomatic_equal(t, r3t)), None)
                if mate is not None:
                    tokens[k] = _mk(mate, "R2-observed")
            # A replace block mixes two different things: R2 tokens R3 CORRECTED (same word, better read) and R2
            # tokens R3 EXCLUDED (intruded marginalia that happened to fall between two corrections, e.g. the
            # `The Ghoſper` running note inside Matthew 28:16). Only the first kind is verse material whose ſ the
            # surface still owes; pairing by skeleton similarity separates them instead of charging both.
            for t in r2_toks[i1:i2]:
                if not any(difflib.SequenceMatcher(a=_skeleton(t), b=_skeleton(u)).ratio() >= 0.6
                           for u in r3_toks[j1:j2]):
                    dropped.append(t)

    unresolved = [{"i": i, "token": t["text"], "positions": decision_positions(t["text"])}
                  for i, t in enumerate(tokens) if t["source"] == "R3-content"]
    return {
        "text": " ".join(t["text"] for t in tokens),
        "tokens": tokens,
        "unresolved": unresolved,
        "n_observed": sum(1 for t in tokens if t["source"] == "R2-observed"),
        "n_undecided": len(unresolved),
        # ſ-BASELINE, SPLIT. The gate opened these debts on `r3_ſ < r2_ſ` over R2's WHOLE line-band, which
        # includes interleaved apparatus R2 read and R3 correctly excluded (`on Eaſter eue.`, `his Iuſt
        # balancedo`). Charging the verse surface for marginalia ſ makes closure unreachable for a reason that
        # has nothing to do with the surface. The baseline is therefore the RETAINED material; what was dropped
        # is reported beside it, never silently discounted.
        "r2_s_retained": sum(t.count(LONG_S) for t in r2_toks) - sum(t.count(LONG_S) for t in dropped),
        "r2_s_dropped": sum(t.count(LONG_S) for t in dropped),
        "dropped_tokens": dropped,
    }


def arbitrate(result: dict, readings: dict) -> dict:
    """Apply in-session VISUAL readings to the unresolved tokens (token index -> ſ-faithful spelling).

    Two guards, both refusals rather than repairs:
      * the reading must ſ-fold-equal the R3 token — the arbiter reads the SURFACE, and a reading that changes
        letters is a content edit smuggled in on the surface axis;
      * no word-final ſ — no 1582-1610 printer sets one, so such a 'reading' is a misread, not an observation."""
    open_idx = {u["i"] for u in result["unresolved"]}
    out = {**result, "tokens": [dict(t) for t in result["tokens"]]}
    content_errors = list(result.get("content_errors") or [])
    for i, reading in readings.items():
        if i not in open_idx:
            raise KeyError(f"token {i} is not unresolved (nothing to arbitrate)")
        if isinstance(reading, dict):
            # THE ARBITER LOOKED AND FOUND A CONTENT ERROR, NOT A SURFACE ONE. Reading the crop to settle ſ also
            # reveals when R3 got the LETTERS wrong ('ſayſt'->'layst', 'ſate'->'satte') — a token-level misread
            # the verse-level gate absorbed because the rest of the verse scored well. Recording it as a surface
            # reading would publish the error with a nice ſ on it; the verse re-opens on the CONTENT axis instead.
            content_errors.append({"i": i, "r3": out["tokens"][i]["text"], "printed": reading["printed"],
                                   "note": reading.get("note", "")})
            out["tokens"][i] = {**out["tokens"][i], "source": "content-open"}
            continue
        want = _skeleton(out["tokens"][i]["text"])
        if _skeleton(reading) != want:
            raise ValueError(f"arbitration changed content at token {i}: {want!r} -> {_skeleton(reading)!r}")
        for m in _WORD_RE.finditer(reading):
            w = m.group(0)
            for k, ch in enumerate(w):
                if ch == LONG_S and (k == len(w) - 1 or w[k + 1] == "'"):
                    raise ValueError(f"word-final ſ in arbitration of token {i}: {reading!r}")
        out["tokens"][i] = {"text": reading, "source": "vision-observed"}

    out["text"] = " ".join(t["text"] for t in out["tokens"])
    out["unresolved"] = [u for u in result["unresolved"] if u["i"] not in readings]
    out["n_undecided"] = len(out["unresolved"])
    out["content_errors"] = content_errors
    return out


def verdict(result: dict, r2_text: str, *, s_ratio: float = S_RATIO) -> dict:
    """CLOSED / OPEN / ALERT for one verse's ſ surface, judged by r3_route's own deficiency test.

    OPEN  — tokens remain whose ſ nobody has observed (the visual arbiter has work left).
    ALERT — every token is provenanced, yet the surface still carries fewer ſ than R2 attested. The transfer
            did not recover what the recognizer saw: the APPROACH needs redesign, not a lowered bar.
    CLOSED— nothing undecided and the surface is no poorer than the one the gate rejected."""
    import long_s_rule
    s_count = result["text"].count(LONG_S)
    r2_s = result.get("r2_s_retained", r2_text.count(LONG_S))
    ev = long_s_rule.evaluate(result["text"])
    if result.get("content_errors"):
        state = "CONTENT_OPEN"          # the surface work found a LETTER error -> re-escalate on the content axis
    elif result["n_undecided"]:
        state = "OPEN"
    elif r2_s > 0 and s_count < s_ratio * r2_s:
        state = "ALERT"
    else:
        state = "CLOSED"
    return {"state": state, "s_count": s_count, "r2_s_count": r2_s,
            "r2_s_dropped": result.get("r2_s_dropped", 0), "n_undecided": result["n_undecided"],
            "content_errors": result.get("content_errors") or [],
            "conformance": ev["conformance"], "final_long_s_violations": ev["final_long_s_violations"],
            "provenance": {s: sum(1 for t in result["tokens"] if t["source"] == s)
                           for s in ("R2-observed", "vision-observed", "R3-content", "no-decision")}}


if __name__ == "__main__":
    # smoke: one agreeing token transfers its observed ſ; one corrected token stays undecided until read.
    t = transfer("And ſhe ſaid: zzzqq to my lord.", "And she said: seruant to my lord.")
    ok = t["text"].startswith("And ſhe ſaid:") and [u["i"] for u in t["unresolved"]] == [3]
    ok &= verdict(t, "And ſhe ſaid: zzzqq to my lord.")["state"] == "OPEN"
    d = arbitrate(t, {3: "ſeruant"})
    v = verdict(d, "And ſhe ſaid: zzzqq to my lord.")
    ok &= v["state"] == "CLOSED" and v["provenance"]["vision-observed"] == 1
    print("SELF-CHECK:", "PASS" if ok else "FAIL", "|", d["text"], "|", v["state"])
    raise SystemExit(0 if ok else 1)

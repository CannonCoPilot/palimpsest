# -*- coding: utf-8 -*-
"""IS A REFERENCE MIS-NUMBERED? — detect verse-boundary drift between the reference witnesses.

WHY THIS EXISTS. Genesis 1 scores far worse against `s_dismas` (mean 0.756, 86/124) than against `odr_com`
(0.946, 109/124), and the gap is not OCR. Laid side by side, `s_dismas` agrees with `odr_com` verse for verse
through 1:25 and then goes off by one for the rest of the chapter:

    s_dismas 1:25  `And God made the beaſtes of the earth ... in his kind.`
    s_dismas 1:26  `And God ſaw that it was good,`                       <- the tail of the SAME printed verse
    s_dismas 1:27  == odr_com 1:26, exactly (ratio 1.00)
    ...            every later verse shifted by one; odr_com 1:31 has no s_dismas counterpart

So `s_dismas` split one printed verse into two and renumbered everything after it. **Verses 26-31 cannot
reach the bar against that reference by any amount of OCR work — the comparison is against the wrong text.**
That is worth knowing before another hour is spent tuning recognition against it.

WHAT THIS MODULE DOES. For every book/chapter present in two or more references, it asks of each verse: does
this reference's verse N match the OTHER reference's verse N better than it matches verse N±k? A run of verses
that all match at a constant nonzero offset is a numbering shift, and the verse where the run begins is the
split. Reported, never silently repaired — a numbering claim about a printed edition is a collation judgement,
and §13 Q21's rule holds here too: flag the locus, do not convert it to a pass.

Usage:  ../ocr-venv/bin/python ref_alignment_audit.py [--book genesis] [--refs a,b,...] [--json OUT]
"""
from __future__ import annotations

import argparse
import collections
import difflib
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import qc_audit as QC                          # noqa: E402

REFS = ("s_dismas", "odr_com", "sabates_a", "madueke_b")
MATCH = 0.80          # two verses "are the same verse" above this token-sequence ratio
MAX_SHIFT = 3         # how far to look for the counterpart
MIN_RUN = 3           # a shift must persist this many verses to be called a shift, not a coincidence


def _norm(t: str) -> list[str]:
    """Fold the archaic/modern spelling difference before comparing.

    WITHOUT THIS THE AUDIT MISSES ITS OWN HEADLINE CASE. The s_dismas Genesis 1 shift is unanimous — odr_com,
    sabates_a and madueke_b agree with each other at every verse — but a raw token ratio only detected it
    against `odr_com`, because `sabates_a`/`madueke_b` are MODERN-spelling and `heauen`/`heaven`,
    `likenes`/`likeness`, `ouer`/`over` score as different words. The corroboration filter then dismissed a
    3-witness agreement as a 1-witness disagreement. Folding u/v, i/j, the long s and doubled finals is the
    same normalization the identity metric applies, and it is what lets a shift be corroborated ACROSS the
    archaic/modern boundary rather than only within it."""
    out = []
    for w in (t or "").split():
        w = w.strip(" .,;:·†‡*()[]†‡").lower()
        w = w.replace("ſ", "s").replace("æ", "ae").replace("œ", "oe")
        w = w.replace("vv", "w").replace("u", "v").replace("j", "i").replace("y", "i")
        w = re.sub(r"(.)\1+$", r"\1", w)        # likenesse/likeness -> likenes
        w = re.sub(r"e$", "", w)                # kinde/kind, fruite/fruit
        if w:
            out.append(w)
    return out


def _ratio(a: str, b: str) -> float:
    na, nb = _norm(a), _norm(b)
    if not na or not nb:
        return 0.0
    return difflib.SequenceMatcher(a=na, b=nb, autojunk=False).ratio()


def chapters(reads: dict) -> dict[tuple[str, int], dict[int, str]]:
    out: dict[tuple[str, int], dict[int, str]] = collections.defaultdict(dict)
    for k, v in reads.items():
        m = re.fullmatch(r"scripture/([^/]+)/(\d+)/(\d+)", k)
        if m:
            out[(m.group(1), int(m.group(2)))][int(m.group(3))] = v
    return out


def drift(a: dict[int, str], b: dict[int, str]) -> list[dict]:
    """Per verse of `a`, the offset k at which it best matches `b`. Returns the runs where |k| > 0."""
    best: dict[int, tuple[float, int]] = {}
    for v, txt in a.items():
        cand = [(( _ratio(txt, b[v + k]) if (v + k) in b else 0.0), k)
                for k in range(-MAX_SHIFT, MAX_SHIFT + 1)]
        best[v] = max(cand)
    runs, cur = [], None
    for v in sorted(best):
        score, k = best[v]
        if score >= MATCH and k != 0:
            if cur and cur["offset"] == k and v == cur["last"] + 1:
                cur["last"] = v
                cur["scores"].append(round(score, 3))
            else:
                if cur and cur["last"] - cur["first"] + 1 >= MIN_RUN:
                    runs.append(cur)
                cur = {"first": v, "last": v, "offset": k, "scores": [round(score, 3)]}
        else:
            if cur and cur["last"] - cur["first"] + 1 >= MIN_RUN:
                runs.append(cur)
            cur = None
    if cur and cur["last"] - cur["first"] + 1 >= MIN_RUN:
        runs.append(cur)
    return runs


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--book", default=None, help="restrict to one book (default: every book present)")
    ap.add_argument("--refs", default=",".join(REFS))
    ap.add_argument("--json", default=str(HERE / "ref-alignment-audit.json"))
    a = ap.parse_args()

    names = [r.strip() for r in a.refs.split(",") if r.strip()]
    loaded = {n: chapters(QC.load_reads_verse(n)) for n in names}
    for n in names:
        print(f"{n:>10}: {len(loaded[n])} chapters, {sum(len(c) for c in loaded[n].values())} verses")

    findings = []
    for i, n in enumerate(names):
        for m in names:
            if m == n:
                continue
            for key, av in loaded[n].items():
                if a.book and key[0] != a.book:
                    continue
                bv = loaded[m].get(key)
                if not bv or len(av) < MIN_RUN + 2:
                    continue
                for r in drift(av, bv):
                    findings.append({"ref": n, "against": m, "book": key[0], "chapter": key[1], **r})

    # A shift is CORROBORATED when the same reference drifts the same way against every other reference —
    # that is what distinguishes "this reference is mis-numbered" from "those two disagree".
    by_locus = collections.defaultdict(list)
    for f in findings:
        by_locus[(f["ref"], f["book"], f["chapter"], f["first"], f["offset"])].append(f["against"])
    corroborated = {k: v for k, v in by_locus.items() if len(v) >= 2}

    Path(a.json).write_text(json.dumps(
        {"findings": findings, "corroborated": [{"ref": k[0], "book": k[1], "chapter": k[2],
                                                 "from_verse": k[3], "offset": k[4], "against": v}
                                                for k, v in corroborated.items()]},
        ensure_ascii=False, indent=1))

    # The detector reads RAW references on purpose — it must see the state on disk, not the corrected view, or
    # it could never find anything twice. But an operator needs to know which findings are already handled, so
    # each is marked against `ref_renumber.CORRECTIONS`. Only the UNENCODED ones are work.
    try:
        import ref_renumber as RR
        encoded = {(n, b, c) for (n, b, c) in RR.CORRECTIONS}
    except Exception:                                           # noqa: BLE001
        encoded = set()
    print(f"\n=== CORROBORATED NUMBERING SHIFTS (agreed by >=2 other references) — {len(corroborated)} ===")
    tally = collections.Counter(k[0] for k in corroborated)
    n_new = 0
    for k, v in sorted(corroborated.items()):
        done = (k[0], k[1], k[2]) in encoded
        n_new += not done
        tag = "[encoded in ref_renumber]" if done else "[** UNENCODED — WORK **]"
        print(f"  {k[0]:>10} {k[1]} {k[2]}: from verse {k[3]:>3}, offset {k[4]:+d}  (vs {', '.join(v)})  {tag}")
    print(f"\n  {n_new} finding(s) not yet encoded" if n_new else "\n  all corroborated findings are encoded")
    print(f"\nby reference: {dict(tally)}")
    print(f"uncorroborated (one witness only): {len(by_locus) - len(corroborated)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

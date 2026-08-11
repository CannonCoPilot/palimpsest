# -*- coding: utf-8 -*-
"""BOOK-GRAIN CROSS-WITNESS AUDIT — one book, every witness that should carry it, attributed to a stack layer.

WHY BOOK-GRAIN AND ALL-WITNESSES-AT-ONCE (Sir, 2026-07-28). Chasing one source's gaps wherever they fall mixes
defects that have nothing to do with each other. Holding the BOOK fixed and varying the WITNESS turns the
witnesses into controls for one another, which is what makes the diagnosis cheap:

    a defect present in EVERY witness of a book cannot be that witness's recognizer — it is vertical
    (reference, addressing, pinning, segmentation, gating)

    a defect present in ONE witness, where its siblings read the same verse correctly, is horizontal
    (that volume's scan quality, layout or recognizer head)

That single test — "do the others agree?" — is what this module operationalizes. It was arrived at the hard
way: the `Pſal. 30` furniture defect (#9) and the `_line_range` truncation (#8) both LOOKED like recognition
until a sibling witness was asked the same question.

TWO STACKS ARE VALIDATED AT ONCE.

  HORIZONTAL (parity across witnesses) — S1, S3, S4, S6, S8, S9 must reach the bar on the same verses. The
  parity spread (best minus worst pass-rate on the same book) is the headline: a wide spread is a per-volume
  problem, a uniformly low level is a stack problem.

  VERTICAL (the operational stack) — every defect is attributed to exactly one layer, defined in `STACK`
  below. The layer is what tells you which module to open.

A NOTE ON WHAT IS *NOT* MEASURED HERE. This module never proposes excising text to raise a score. The
janvier-anchoring signal in particular must not be used that way: the archaic spellings that dominate the
un-anchored tokens (`sone`, `therfore`, `daies`, `citie`, `geue`, `betwene`, `darkenes`, `uho`) are CORRECT
readings that a modern-spelling grid cannot match, and dropping them would delete scripture to flatter the
metric. See `apparatus_min` in `verse_seg.segment`, which is deliberately conservative for exactly this reason.

Usage:  python book_audit.py genesis [--out book-audit-genesis.json]
"""
from __future__ import annotations

import argparse
import collections
import difflib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import corpus_localize as CL               # noqa: E402  # Gate 0f route to the localization artefact
import page_address as PA                  # noqa: E402
import qc_audit as QC                      # noqa: E402
import verse_seg as VS                     # noqa: E402
import witness_inventory as WI             # noqa: E402
sys.path.insert(0, str(HERE / "witness"))
import witnesses as _W                     # noqa: E402  # the registry adjudicates verse scope (Gate 0f)


# --------------------------------------------------------------------------------------------------
# THE OPERATIONAL VERTICAL STACK
# --------------------------------------------------------------------------------------------------
# Each layer is a place a verse can be lost, named by the module that owns it, with the observable that says
# the layer is at fault. A defect belongs to the LOWEST layer that can explain it — attributing a truncated
# span to "recognition" is how #8 survived three rounds.
STACK = [
    ("V0", "SOURCE INVENTORY", "witness_inventory.py · master-source-list.json",
     "Which physical volumes exist and which tome each holds. FAULT: a book attested by a volume that cannot "
     "contain it (an NT-only witness claiming Genesis), or an admitted volume that is a duplicate rendering."),
    ("V1", "PAGE ADDRESSING", "page_address.py (monotone DP) · page_address_eval.py → .page-address-*.json",
     "page → (book, chapter). FAULT: a chapter with no page at all; a page addressed to the wrong chapter. "
     "The DP is MONOTONE, so a single false heading does not mis-label one page — it makes every chapter "
     "between the true and false position unreachable (defect #9)."),
    ("V2", "TOME MAP", "build_tome_map_v2.py → tome-map-v2.json",
     "The derived per-volume coverage claim. FAULT: divergence from V1. It is DERIVED from addressing, so it "
     "can never be fed back as a prior — that would be a self-fulfilling loop (see `tome_prior`)."),
    ("V3", "PINNING / BODY ISOLATION", "pin_carry_chain · corpus_localize._line_range · verse_geom.build_body_tokmap",
     "Which lines of a page are body, and which chapter owns them. FAULT: a chapter's line range truncated "
     "(defect #8) or over-offered; marginal-column apparatus concatenated INTO a body line by the line "
     "builder, so it cannot be separated downstream by role."),
    ("V4", "VERSE LOCALIZATION", "verse_locate.best_spans (walk ⊕ align hybrid) · verse_seg.segment",
     "chapter body → per-verse spans. FAULT: no span for a verse present on the page (a MISS); a span that "
     "stops short or swallows its neighbour."),
    ("V5", "RECOGNITION", "reocr_core (kraken base / R1 / R2 fine-tuned) · r3_route (olmOCR)",
     "Glyph accuracy on the span's pixels. FAULT: substituted tokens. This is the ONLY layer a better "
     "recognizer can fix, which is why everything above it must be excluded first."),
    ("V6", "REFERENCE", "s_dismas (archaic, preeminent) · odr_com (archaic backfill) · janvier/sabates_a (modern grid)",
     "What the verse is compared against, and the versification grid it is cut on. FAULT: a locus the "
     "reference does not carry; a versification offset (the Psalm superscription shift)."),
    ("V7", "GATING / SCORING", "qc_audit (archaic_id, modern_id, ARCHAIC_VALID_FLOOR) · xsrc_gate",
     "archaic-preeminent identity scoring and the ≥0.90 bar. FAULT: a metric that consults a set the label "
     "helped build (defect #7), or any rule that converts a below-bar unit into an accepted one."),
    ("V8", "REPORTING / VERSIONING", "build_reocr_report.py · version_compare.py",
     "What is published and how versions are compared. FAULT: a stale or circular figure persisted where a "
     "later reader will quote it."),
]

# failure taxonomy at V4/V5/V6, decided by the shape of the diff against the archaic reference
KINDS = {
    "A": ("EXTRA tokens", "V3", "interleaved apparatus / neighbouring-chapter bleed inside the span"),
    "B": ("MISSING tokens", "V4", "the span stops short of the verse — truncation or a bad cut"),
    "C": ("SUBSTITUTED tokens", "V5", "the words are there but misrecognised — recognizer territory"),
    "D": ("near-miss", "V5", "below the bar with no dominant error mode; usually accumulated glyph noise"),
    "E": ("no archaic reference", "V6", "nothing to compare against — the verse cannot pass at any quality"),
}


def witnesses_for_book(book: str, *, for_scoring: bool = True, announce=print) -> dict[str, str]:
    """{witness_id -> ocr_dir} for every witness whose declared tomes can contain `book`.

    From `witness_inventory`, which is the authority — NOT inferred from where pages happen to land, which
    would make the check circular (a mis-addressed page would define its own volume as legitimate).

    R9.2c — `for_scoring` EXISTS BECAUSE THIS FUNCTION ANSWERS THE WRONG QUESTION FOR ITS CALLERS. The
    `tomes` declaration is a CONTAINMENT fact: it says which books a volume's leaves carry. Both callers
    used it as a SCORING permission, and so both were scoring `jp2-S06ot` (OT-1635-M, a 1635 Rouen
    edition — `frontmatter`, verse_scope 'none') and `jp2-S08` (NT-1582-X, B upscaled 2.000× —
    `excluded`), because those volumes DO contain the books. Containment was never the question; it is
    admissibility, and only the registry's role answers that.

    This is R7.5a-3's category error with the arrow reversed. There a SCORING rule (`drop_tomes`) was
    read as a containment claim and force-fitted 800 NT leaves onto OT books. Here a containment fact is
    read as a scoring permission. The lesson is the same one, and it is why the two now have separate
    accessors instead of one that has to be interpreted: `for_scoring=False` for bookkeeping — how many
    leaves exist, which volumes hold this book — and the default for anything that produces a figure.

    The drop is PRINTED, not silent: an audit whose witness set narrowed without saying so describes a
    corpus it did not read (the `qc_audit.scan_ocr_dirs` pattern, R9.2)."""
    tome = "NT" if PA.BOOK_TESTAMENT.get(book) == "NT" else ("OT2" if book in WI.OT2_BOOKS else "OT1")
    out, dropped = {}, []
    for sid, w in WI.WITNESSES.items():
        t = (w.get("tomes") or {}).get(tome)
        if not (t and t.get("ocr_dir")):
            continue
        od = t["ocr_dir"]
        if for_scoring and not _W.verse_admitted(od):
            vol, sig = _W.witness_of(od)
            dropped.append((sid, od, _W.wid(vol, sig), _W.WITNESSES[(vol, sig)]["role"]))
            continue
        out[sid] = od
    if dropped and announce:
        announce(f"[Gate 0f] {book}: {len(dropped)} witness(es) dropped from SCORING — verse_scope 'none'. "
                 f"Their leaves still count structurally; their text is not evidence at any grain:")
        for sid, od, w, role in dropped:
            announce(f"          {sid:4} {od:14} {w:12} role {role!r}")
    return out


def _fold_toks(s: str) -> list[str]:
    return [f for f in (VS._afold(t) for t in VS._toks(s or "")) if f]


def classify(ref: str | None, got: str) -> str:
    """Which failure mode dominates this verse, by the shape of the diff against the archaic reference."""
    if ref is None:
        return "E"
    R, O = _fold_toks(ref), _fold_toks(got)
    ins = dele = rep = 0
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, R, O).get_opcodes():
        if tag == "insert":
            ins += j2 - j1
        elif tag == "delete":
            dele += i2 - i1
        elif tag == "replace":
            rep += max(i2 - i1, j2 - j1)
    n = max(1, len(R))
    if ins >= dele and ins > 0.25 * n:
        return "A"
    if dele > 0.25 * n and dele > ins:
        return "B"
    if rep > 0.25 * n:
        return "C"
    return "D"


def audit_book(book: str) -> dict:
    wits = witnesses_for_book(book)
    aud = json.loads((HERE / "coverage-audit-verse.json").read_text())["verses"]
    sd, oc = QC.load_reads_verse("s_dismas"), QC.load_reads_verse("odr_com")
    archaic = dict(oc)
    archaic.update(sd)                                  # s_dismas preeminent, odr_com backfills
    # R9.2c: through Gate 0f, not around it. `missing_ok` keeps the pre-existing tolerance for a volume
    # that has not been localized -- this audit is run mid-pipeline and a not-yet-built artefact is a
    # legitimate state here -- but a witness the corpus does not admit for verse text now RAISES.
    loc = {sid: CL.load_verses(od, missing_ok=True) for sid, od in wits.items()}

    addr = {}
    for sid, od in wits.items():
        p = HERE / f".page-address-{od}.json"
        addr[sid] = json.loads(p.read_text())["records"] if p.exists() else []

    n_ch = max((int(c) for k in archaic for b, c in [k.split("/")[1:3]] if b == book), default=0)
    n_ch = max(n_ch, max((int(k.split("/")[2]) for k in aud if k.startswith(f"scripture/{book}/")), default=0))

    chapters, per_wit = [], {s: collections.Counter() for s in wits}
    kinds = {s: collections.Counter() for s in wits}
    allfail, splits, allpass = [], 0, 0
    misses = {s: [] for s in wits}
    for ch in range(1, n_ch + 1):
        cv = VS.chapter_verses(book, ch, VS.JANVIER) or {}
        if not cv:
            continue
        row = {"chapter": ch, "expected": len(cv), "witnesses": {}}
        for sid in wits:
            att = pas = 0
            for v in cv:
                r = aud.get(f"scripture/{book}/{ch}/{v}")
                st = (r or {}).get("sources", {}).get(sid) or {}
                if not st.get("localized"):
                    if r:
                        misses[sid].append(f"{ch}:{v}")
                    continue
                att += 1
                per_wit[sid]["localized"] += 1
                if st.get("passed"):
                    pas += 1
                    per_wit[sid]["passed"] += 1
                else:
                    k = classify(archaic.get(f"scripture/{book}/{ch}/{v}"),
                                 (loc[sid].get(f"{book}/{ch}/{v}") or {}).get("text", ""))
                    kinds[sid][k] += 1
            row["witnesses"][sid] = {"attested": att, "passed": pas}
        # cross-witness verdict per verse
        for v in cv:
            r = aud.get(f"scripture/{book}/{ch}/{v}")
            if not r:
                continue
            got = [s for s in wits if ((r["sources"].get(s) or {}).get("localized"))]
            if not got:
                continue
            ok = [s for s in got if (r["sources"][s] or {}).get("passed")]
            if not ok:
                allfail.append(f"{ch}:{v}")
            elif len(ok) == len(got):
                allpass += 1
            else:
                splits += 1
        chapters.append(row)

    # V0: a witness attesting a book its tome cannot hold
    alien = {}
    for sid in set(WI.WITNESSES) - set(wits):
        n = sum(1 for k, r in aud.items()
                if k.startswith(f"scripture/{book}/") and ((r["sources"].get(sid) or {}).get("localized")))
        if n:
            alien[sid] = n

    # V1: a chapter NO page of this witness covers. The test is on `chapters_on_page` (the DP's interval),
    # not on each page's primary chapter — several short chapters legitimately share one leaf, so a
    # primary-chapter-only test reports a gap for every chapter that never happens to open a page. That false
    # positive fired on S9/genesis-39 before this was corrected.
    gaps = {}
    for sid, recs in addr.items():
        have = set()
        for r in recs:
            if r.get("book") != book:
                continue
            have |= {c for c in (r.get("chapters_on_page") or []) if c}
            if r.get("chapter"):
                have.add(r["chapter"])
        g = [c for c in range(1, n_ch + 1) if c not in have]
        if g:
            gaps[sid] = g

    n_verses = sum(c["expected"] for c in chapters)
    parity = {s: round(per_wit[s]["passed"] / max(1, per_wit[s]["localized"]), 4) for s in wits}
    _read = {s: p for s, p in parity.items() if per_wit[s]["localized"] > 0}
    _silent = sorted(set(parity) - set(_read))
    if len(_read) >= 2:
        _spread = {"value": round(max(_read.values()) - min(_read.values()), 4),
                   "basis": {"over": sorted(_read), "excluded_localized_nothing": _silent}}
    else:
        _spread = {"value": None, "basis": {
            "over": sorted(_read), "excluded_localized_nothing": _silent,
            "why": f"a spread needs two witnesses that read something; {len(_read)} did. This is NOT a "
                   f"spread of zero -- it is the absence of a comparison, and the two must not be "
                   f"reported as the same number (R1.4)."}}
    return {
        "book": book, "n_chapters": len(chapters), "n_verses": n_verses,
        "witnesses": wits, "stack": [dict(zip(("id", "name", "modules", "fault"), s)) for s in STACK],
        "kinds": {k: dict(zip(("label", "layer", "note"), v)) for k, v in KINDS.items()},
        "chapters": chapters,
        "per_witness": {s: {"localized": per_wit[s]["localized"], "passed": per_wit[s]["passed"],
                            "pass_rate": parity[s], "kinds": dict(kinds[s]),
                            "localization_misses": misses[s]} for s in wits},
        # PARITY SPREAD, over witnesses that actually READ something (R9.2c).
        #
        # 🔴 MEASURED DEFECT THIS REPLACES. `max - min` over every witness in the set reported, on all
        # five pilot books, a spread EXACTLY EQUAL TO THE BEST WITNESS'S OWN PASS RATE -- genesis 0.7601
        # vs S9 0.7601, psalms 0.633, matthew 0.7594, john 0.6507, apocalypse 0.5728 -- because the set
        # contained a witness that localized ZERO verses (`jp2-S06ot` on OT, `jp2-S08` on NT: 1,530 and
        # 1,070 localization misses out of 1,530 and 1,070). `min` was therefore always 0.0 and the
        # "spread" was the best pass rate under another name. A metric that measures nothing still
        # produces a ranking -- the R7.5a dead-metric lesson, here restating a real number so plausibly
        # that nothing looked wrong.
        #
        # Gate 0f now removes those two, but it does NOT remove the mechanism: an ADMITTED witness that
        # has not been localized yet (pipeline order) puts a 0.0 back into the floor. So the spread is
        # taken over witnesses with `localized > 0`, the excluded ones are NAMED, and with fewer than
        # two readers it is None-with-a-reason rather than 0.0 -- a spread of zero and "no spread could
        # be computed" are different claims, and reporting the second as the first is R1.4.
        "parity_spread": _spread["value"],
        "parity_spread_basis": _spread["basis"],
        "cross_witness": {"all_pass": allpass, "split": splits, "all_fail": len(allfail),
                          "all_fail_loci": allfail},
        "v0_alien_attestations": alien,
        "v1_chapter_gaps": gaps,
    }


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("book")
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    rep = audit_book(a.book)
    out = Path(a.out) if a.out else HERE / f"book-audit-{a.book}.json"
    out.write_text(json.dumps(rep, ensure_ascii=False, indent=1))

    print(f"=== BOOK AUDIT — {rep['book'].upper()} · {rep['n_chapters']} chapters · {rep['n_verses']} verses ===")
    print(f"witnesses that SHOULD carry it (from witness_inventory): {rep['witnesses']}")
    print("\nHORIZONTAL — parity across witnesses")
    for s, d in rep["per_witness"].items():
        k = d["kinds"]
        print(f"  {s:<3} localized {d['localized']:>5}/{rep['n_verses']:<5} pass {d['passed']:>5} "
              f"= {100*d['pass_rate']:5.1f}%   A={k.get('A',0):<4} B={k.get('B',0):<4} "
              f"C={k.get('C',0):<4} D={k.get('D',0):<4} E={k.get('E',0):<3} misses={len(d['localization_misses'])}")
    _b = rep["parity_spread_basis"]
    if rep["parity_spread"] is None:
        print(f"  PARITY SPREAD: NOT COMPUTED — {_b['why']}")
    else:
        print(f"  PARITY SPREAD (best-worst over {len(_b['over'])} witnesses that read something, "
              f"{'+'.join(_b['over'])}): {100*rep['parity_spread']:.1f} points")
    if _b["excluded_localized_nothing"]:
        # Named, never silent: a witness that localized nothing would drag the floor to 0.0 and turn
        # the spread back into the best witness's own pass rate (R9.2c).
        print(f"    excluded from the spread, localized NOTHING: {_b['excluded_localized_nothing']} "
              f"— they still appear per-witness above; this is a spread, not a coverage claim")
    cw = rep["cross_witness"]
    tot = cw["all_pass"] + cw["split"] + cw["all_fail"]
    print(f"\nCROSS-WITNESS verdict over {tot} verses")
    print(f"  all pass {cw['all_pass']:>5} ({100*cw['all_pass']/tot:.1f}%) · split {cw['split']:>5} "
          f"({100*cw['split']/tot:.1f}%) · ALL FAIL {cw['all_fail']:>5} ({100*cw['all_fail']/tot:.1f}%) "
          f"<- vertical, no witness can read it")
    print(f"\nV0 alien attestations: {rep['v0_alien_attestations'] or 'none'}")
    print(f"V1 chapter gaps      : {rep['v1_chapter_gaps'] or 'none'}")
    print(f"\nwrote {out.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

# -*- coding: utf-8 -*-
"""CORRECT A REFERENCE'S VERSE NUMBERING AT LOAD TIME — evidence-based, non-destructive, reversible.

THE PROBLEM THIS SOLVES. `s_dismas` is the governing archaic reference, and in Genesis 1 it is mis-numbered.
It splits the printed verse 25 in two:

    s_dismas 1:25  `And God made the beaſtes of the earth ... in his kind.`          (24 tokens)
    s_dismas 1:26  `And God ſaw that it was good,`                                   ( 7 tokens)
    odr_com  1:25  `And God made the beaſtes ... in his kind. And God ſaw that it was good.`  (31 tokens)

and therefore runs the chapter to 32 verses where every other reference runs it to 31, with 26-31 all shifted
by one. **No amount of OCR work can bring verses 26-31 to the bar against that reference**, because the
comparison is against the wrong text — which is the whole of why Genesis 1 scored 0.756 against `s_dismas` and
0.946 against `odr_com`. It was never a transcription gap.

WHY CORRECTING IT IS NOT LAUNDERING A SCORE. The house rule is that a below-threshold unit stays open and
blocks, and that safeguards must never convert a bad result into an accepted one. That rule is about our
OUTPUT. This is an error in our INPUT: the numbering claim is falsified by unanimous corroboration —
`odr_com`, `sabates_a` and `madueke_b` agree with each other verse for verse, at identical token counts, and
`s_dismas` 1:27 matches `odr_com` 1:26 at ratio 1.000. Correcting a demonstrably wrong reference raises the
score because the measurement becomes true, not because the bar moved. The distinction that keeps it honest:
**only corroborated shifts are corrected, the evidence is recorded with each entry, and the source file is
never touched** — `apply()` rewrites keys in the loaded dict, so removing an entry here restores the old
behaviour exactly.

WHAT IS NOT CORRECTED. `ref_alignment_audit.py` also reports shifts in `odr_com` genesis 39 and `s_dismas`
genesis 26. They are real and they are left alone: this sprint is scoped to Genesis 1, and a numbering
correction should be adopted one chapter at a time with its evidence read, not applied in bulk from a
detector. Re-run the audit before extending to Genesis 2-50.

DISTINCT FROM THE OUTLIER DETECTOR (§13 Q21). A mis-NUMBERING is a mechanical fault with an unambiguous
remedy. A divergent READING at a correctly numbered verse — gen 1:25, where all four witnesses read the page
correctly and s_dismas's wording simply differs — is a collation judgement, and that one must be FLAGGED and
never auto-passed. Do not extend this module to cover it.

Usage:  from ref_renumber import apply;  reads = apply("s_dismas", QC.load_reads_verse("s_dismas"))
"""
from __future__ import annotations

import re

# (reference, book, chapter) -> correction. THREE operations, because three distinct faults have been found:
#
#   "merge": (a, b)  verse b is the tail of printed verse a. Join them, renumber everything after b DOWN by 1.
#                    (Genesis 1/s_dismas: v25 split in two, chapter ran to 32 instead of 31.)
#   "split": (a,)    verse a carries verse a+1 as well. Cut it where the corroborating references' verse a
#                    ends, renumber everything after a UP by 1, and put the tail in a+1.
#                    (Genesis 26/s_dismas: v4 = 52 tokens where the others have 34 and their v5 has 18.)
#   "shift": (a, k)  verses from a onward are numbered k too high — usually because a slot ahead of them is
#                    EMPTY. Renumber them down by k.
#                    (Genesis 39/odr_com: v6 is empty and its text sits in v7; v7..v24 are all one too high.)
#
# Every entry must cite the corroboration that justifies it. Only corroborated faults are corrected, and the
# source file is never touched — `apply()` rewrites keys in the loaded dict.
CORRECTIONS: dict[tuple[str, str, int], dict] = {
    ("s_dismas", "genesis", 1): {
        "merge": (25, 26),
        "evidence": "odr_com/sabates_a/madueke_b agree verse-for-verse at identical token counts and run the "
                    "chapter to 31; s_dismas runs to 32. s_dismas 1:27 == odr_com 1:26 at ratio 1.000, and "
                    "the +1 shift persists to the chapter end (ref_alignment_audit.py, corroborated 3/3).",
    },
    ("odr_com", "genesis", 39): {
        "shift": (7, 1),
        "evidence": "odr_com v6 is EMPTY and its text sits in v7: odr_com v7 == s_dismas v6 at ratio 1.000, "
                    "and the -1 offset persists v7..v24 against s_dismas (18 verses, every score 1.000) and "
                    "against sabates_a/madueke_b. All four references carry 23 non-empty verses.",
    },
    ("s_dismas", "genesis", 26): {
        "split": (4, 21),
        "evidence": "s_dismas v4 is 52 tokens where odr_com/sabates_a/madueke_b carry 34, and their v5 carries "
                    "18 (34+18=52): s_dismas merged v4 and v5. The resulting +1 offset persists v5..v19 "
                    "against all three (scores 1.000 vs odr_com). s_dismas has 33 verses, the others 35.",
        "evidence2": "The SECOND merge is at v21 (post-first-split numbering): s_dismas 56 tokens where "
                     "sabates_a carries 19 at v21 and 35 at v22 (19+35=54). Splitting both clears the residual "
                     "drift entirely and brings s_dismas to 35 verses, matching the other three.",
    },
    ("s_dismas", "genesis", 8): {
        "split": (15,),
        "evidence": "The PRINT ITSELF merges DR 15 and 16 under `15`: the s_dismas page reads `15 And God ſpake "
                    "to Noe, ſaying: Goe forth of the arke, thou & thy wife...` (25 tokens) where odr_com has 6 "
                    "at v15 and 19 at v16 (6+19=25), and it numbers the rest of the chapter one lower, ending "
                    "at a printed `21` that is DR 22. The parse is FAITHFUL to that page — this entry corrects "
                    "the edition's numbering, not the transcription. Corroborated 3/3: after the split, "
                    "s_dismas v16..v22 score 1.000, 1.000, 1.000, 1.000, -, 0.991 against odr_com v16..v22 "
                    "(v21 is a separate parse defect, the page-foot note block, fixed in ref_repair_s_dismas), "
                    "and all four references then carry 22 verses.",
    },
    # ---------------------------------------------------------------------------------------------------
    # THE LAST SIX REFERENCE GAPS IN GENESIS, each a single verse, found together once the odr_com
    # truncation was repaired and the board could be read without 600 cells of noise in front of it. Five are
    # merges and are corrected here; the sixth (odr_com genesis 23:20) is NOT — the site's page simply lacks
    # the verse, and inventing it is not available to us. See CAMPAIGN-STATUS.
    ("s_dismas", "genesis", 20): {
        "split": (17,),
        "evidence": "s_dismas v17 is 33 tokens and reads `...and they bare children: for our Lord had cloſed "
                    "vp euerie matrice...`, which is DR 17 followed verbatim by DR 18; sabates_a and "
                    "madueke_b carry 16 at v17 and 17 at v18 (16+17=33) and run the chapter to 18. odr_com "
                    "MERGES IT THE SAME WAY (see below) — both are 1609/1610-typeset witnesses, so this is "
                    "the edition's versification, not an accident of either transcription.",
    },
    ("odr_com", "genesis", 20): {
        "split": (17,),
        "evidence": "The same merge as s_dismas above, in the same place, word for word: odr_com v17 is 33 "
                    "tokens ending `...for Sara Abrahams wife.` where sabates_a/madueke_b carry 16 at v17 and "
                    "17 at v18. Two independent lineages attest the merge; two attest the split.",
    },
    ("odr_com", "genesis", 34): {
        "split": (28,),
        "evidence": "The SITE'S OWN MARKERS repeat: the chapter's `<b>N. </b>` sequence runs "
                    "...26, 27, 28, 28, 30, 31 — verse 29 is printed with the number 28, so the scrape "
                    "faithfully concatenates the two blocks. The result is 28 tokens where s_dismas, "
                    "sabates_a and madueke_b carry 17 at v28 and 11 at v29 (17+11=28), and the text is their "
                    "v28 followed by their v29 verbatim.",
    },
    ("s_dismas", "genesis", 40): {
        "split": (1,),
        "evidence": "s_dismas v1 is 42 tokens, ending `...And Pharao being wrath againſt them (for the one "
                    "was chiefe of the cupbearers, the other chiefe baker)` — DR 1 plus DR 2 entire. The "
                    "other three carry 24 at v1 and 18 at v2 (24+18=42) and run the chapter to 23; s_dismas "
                    "runs to 22.",
    },
    ("s_dismas", "genesis", 41): {
        "split": (45,),
        "evidence": "s_dismas v45 is 64 tokens and swallows v46: `...went forth to the land of Ægypt (46 and "
                    "he was thirtie yeares old...`. The other three carry 40 at v45 and 23 at v46. NOTE the "
                    "printed `46` survives INSIDE the text — the marker sits after an opening parenthesis, "
                    "which the pdftotext verse-number split does not recognise, so the tail begins `(46 and`. "
                    "That is a parse residue, recorded here rather than edited away: this module re-keys "
                    "verses, it does not rewrite their words.",
    },
}

_KEY = re.compile(r"scripture/([^/]+)/(\d+)/(\d+)")

# Who corroborates whom. A trim needs at least two independent witnesses to the shorter reading.
_ALL = ("s_dismas", "odr_com", "sabates_a", "madueke_b")
OTHERS = {n: [m for m in _ALL if m != n] for n in _ALL}
# Populated by `load_corrected` so a caller can report what was trimmed rather than trust it blindly.
LAST_TRIMS: dict[str, list[dict]] = {}


def apply(name: str, reads: dict[str, str], *, others: list[dict[str, str]] | None = None,
          log=None) -> dict[str, str]:
    """Return `reads` with this reference's corroborated numbering faults corrected. Input is not mutated.

    `others` is needed only for a "split", whose cut point is taken from the corroborating references' own
    verse length rather than chosen here."""
    todo = {(b, c): v for (n, b, c), v in CORRECTIONS.items() if n == name}
    if not todo:
        return reads
    # Whole-chapter renumberings (shift, split) run before the per-key merge pass.
    for (book, ch), corr in todo.items():
        if "shift" in corr:
            a, k = corr["shift"]
            src = {int(_KEY.fullmatch(key).group(3)): txt for key, txt in list(reads.items())
                   if (m := _KEY.fullmatch(key)) and m.group(1) == book and int(m.group(2)) == ch}
            out2 = {key: txt for key, txt in reads.items()
                    if not ((m := _KEY.fullmatch(key)) and m.group(1) == book and int(m.group(2)) == ch)}
            for vn in sorted(src):
                out2[f"scripture/{book}/{ch}/{vn - k if vn >= a else vn}"] = src[vn]
            reads = out2
            if log:
                log(f"ref_renumber: {name} {book} {ch}: shifted v{a}+ down by {k}")
        if "split" in corr and others:
            # Splits are applied in ASCENDING order, each expressed in the numbering that results from the
            # previous one. A split renumbers everything after it upward, so a later split's verse number is
            # already post-shift — which is also how it was measured off the references.
            import statistics
            for a in corr["split"]:
                key = f"scripture/{book}/{ch}/{a}"
                txt = reads.get(key)
                lens = [len(_norm(o[key])) for o in others if o.get(key)]
                if not txt or len(lens) < 2:
                    continue
                cut = int(statistics.median(lens))
                toks = txt.split()
                if not (0 < cut < len(toks)):
                    continue
                # A MERGE LEAVES ONE OF TWO WOUNDS, and they need opposite repairs. Either the source went on
                # to number every LATER verse one lower — s_dismas genesis 8 prints DR 22 as `21` — and the
                # tail verses must all move up by one; or it kept the later numbering and simply left a HOLE
                # where the swallowed verse should be, as odr_com genesis 34 does (its markers run 27, 28, 28,
                # 30, 31 — verse 29 is printed `28`, and 30 and 31 are already right). Renumbering the second
                # kind pushes correct verses off the end: it gave odr_com 34 a verse 32 and s_dismas 40 a
                # verse 24 that no edition has.
                #
                # The reference itself says which it is, with no judgement required: if a+1 is ABSENT, the
                # merge left a hole and there is nothing after it to move.
                shift_tail = f"scripture/{book}/{ch}/{a + 1}" in reads
                src = {int(_KEY.fullmatch(k2).group(3)): t2 for k2, t2 in list(reads.items())
                       if (m := _KEY.fullmatch(k2)) and m.group(1) == book and int(m.group(2)) == ch}
                out2 = {k2: t2 for k2, t2 in reads.items()
                        if not ((m := _KEY.fullmatch(k2)) and m.group(1) == book and int(m.group(2)) == ch)}
                for vn in sorted(src, reverse=True):
                    out2[f"scripture/{book}/{ch}/{vn + 1 if (shift_tail and vn > a) else vn}"] = src[vn]
                out2[f"scripture/{book}/{ch}/{a}"] = " ".join(toks[:cut])
                out2[f"scripture/{book}/{ch}/{a + 1}"] = " ".join(toks[cut:])
                reads = out2
                if log:
                    log(f"ref_renumber: {name} {book} {ch}: split v{a} at token {cut}, "
                        + ("renumbered after" if shift_tail else "filled the hole at a+1"))
    todo = {k: v for k, v in todo.items() if "merge" in v}
    if not todo:
        return reads
    out: dict[str, str] = {}
    joined: dict[tuple[str, int], str] = {}
    for k, txt in reads.items():
        m = _KEY.fullmatch(k)
        if not m:
            out[k] = txt
            continue
        book, ch, v = m.group(1), int(m.group(2)), int(m.group(3))
        corr = todo.get((book, ch))
        if not corr or "merge" not in corr:
            out[k] = txt
            continue
        a, b = corr["merge"]
        if v == a:
            joined[(book, ch)] = txt                    # held back until its tail arrives
        elif v == b:
            head = joined.pop((book, ch), "")
            # The split fell mid-sentence, so the head keeps its trailing comma-or-nothing and the tail is
            # appended with a single space — the reference's own words, rejoined, nothing invented.
            out[f"scripture/{book}/{ch}/{a}"] = (head + " " + txt).strip() if head else txt
        elif v > b:
            out[f"scripture/{book}/{ch}/{v - 1}"] = txt
        else:
            out[k] = txt
    for (book, ch), txt in joined.items():              # a head whose tail was absent
        out.setdefault(f"scripture/{book}/{ch}/{CORRECTIONS[(name, book, ch)]['merge'][0]}", txt)
    if log:
        for (b, c), corr in todo.items():
            log(f"ref_renumber: {name} {b} {c}: merged {corr['merge'][0]}+{corr['merge'][1]}, renumbered after")
    return out


def _norm(t: str) -> list[str]:
    return [w.strip(" .,;:·†‡*()[]").lower().replace("\u017f", "s") for w in (t or "").split() if w.strip(" .,;:")]


def trim_apparatus(name: str, reads: dict[str, str], others: list[dict[str, str]], *,
                   ratio: float = 1.4, head_fit: float = 0.85, tail_max: float = 0.45,
                   scope: tuple[str, int] | None = None, log=None) -> tuple[dict[str, str], list[dict]]:
    """Trim a marginal ANNOTATION that the ingest glued onto the end of a verse. Corroborated and reported.

    THE DEFECT. `s_dismas` genesis 16:3 carries 53 tokens where the other three references carry 27 — the extra
    is the DR's controversial note on faith and works (`To beleue Gods word without ſtaggering is an act of
    iuſtice. Not workes before faith...`). It is apparatus, it is not scripture, and no transcription of the
    printed verse can ever match it. Genesis 1's `s_dismas` gap was a mis-NUMBERING (see CORRECTIONS above);
    this is a different fault with the same effect, and across 50 chapters it needs detecting, not tabulating.

    THE TEST, AND WHY IT IS SAFE. Three conditions must all hold: the verse is more than `ratio` times the
    MEDIAN length of the same verse in the other references; its opening aligns with them at >= `head_fit`; and
    the trim point falls at the end of that alignment. So the kept text is a PREFIX of what was there, matching
    what the other witnesses independently attest, and the discarded tail is material none of them has. A verse
    that is merely long, or that diverges throughout (a genuine reading difference — §13 Q21's territory, which
    must be FLAGGED not fixed), fails the head-fit test and is left alone.

    THE GUARD THAT MAKES IT SAFE, ADDED AFTER IT FAILED WITHOUT IT. A first version had only the length and
    head-fit tests, and it fired 149 times across the corpus DESTROYING REAL SCRIPTURE: `matthew/1/3` lost
    `And Aram begat Aminadab. And Aminadab begat Naaſſon...`, `matthew/1/24` lost `And he knew her not til ſhe
    brought forth her firſt borne Sonne`. Those references MERGE verses where the others split them — the exact
    inverse of the Genesis 1 fault — and a length outlier cannot tell a merge from a glued annotation.

    It can be told by asking what the tail IS. A merged verse's tail is the NEXT verse of the other references;
    an annotation's tail is in none of them. So the trim now also requires the discarded tail to align at under
    `tail_max` with the following verses. This is scoped and opt-in for the same reason — a corpus-wide silent
    rewrite of the governing reference is not something a helper should do on import.

    Returns (corrected reads, findings). Nothing is silent: every trim is reported with what was removed."""
    import difflib
    import statistics
    out = dict(reads)
    found = []
    for k, txt in reads.items():
        m = _KEY.fullmatch(k)
        if not m:
            continue
        if scope and (m.group(1), int(m.group(2))) != scope:
            continue
        mine = _norm(txt)
        lens = [len(_norm(o[k])) for o in others if o.get(k)]
        if len(lens) < 2 or not mine:
            continue
        med = statistics.median(lens)
        if not med or len(mine) <= ratio * med:
            continue
        # Align against the LONGEST corroborating version, so the kept prefix is the most that is attested.
        ref = max((_norm(o[k]) for o in others if o.get(k)), key=len, default=[])
        if not ref:
            continue
        sm = difflib.SequenceMatcher(a=mine, b=ref, autojunk=False)
        matched = sum(b.size for b in sm.get_matching_blocks())
        if matched / len(ref) < head_fit:
            continue                     # diverges throughout: a reading difference, not a glued annotation
        cut = max((b.a + b.size for b in sm.get_matching_blocks() if b.size), default=0)
        if cut <= 0 or cut >= len(mine):
            continue
        # Is the tail the NEXT verse (a merge) rather than an annotation (contamination)?
        tail = mine[cut:]
        if not tail:
            continue
        book, ch, vn = m.group(1), int(m.group(2)), int(m.group(3))
        nxt = []
        for step in (1, 2):
            for o in others:
                t2 = o.get(f"scripture/{book}/{ch}/{vn + step}")
                if t2:
                    nxt.append(_norm(t2))
        best_tail = 0.0
        for cand in nxt:
            sm2 = difflib.SequenceMatcher(a=tail, b=cand, autojunk=False)
            best_tail = max(best_tail, sum(b.size for b in sm2.get_matching_blocks()) / max(1, len(tail)))
        if best_tail > tail_max:
            found.append({"locus": k, "SKIPPED": "tail matches the following verse — this is a verse MERGE, "
                                                 "not an annotation; numbering question, do not trim",
                          "tail_fit": round(best_tail, 3)})
            continue
        toks = txt.split()
        out[k] = " ".join(toks[:cut])
        found.append({"locus": k, "kept": cut, "removed": " ".join(toks[cut:])[:160],
                      "len_before": len(mine), "median_others": med})
        if log:
            log(f"ref_renumber: {name} {k}: trimmed {len(mine) - cut} apparatus tokens")
    return out, found


def load_corrected(name: str, loader=None, *, trim: tuple[str, int] | None = None) -> dict[str, str]:
    """`qc_audit.load_reads_verse` with the corrections applied — the entry point evaluation should use."""
    if loader is None:
        import qc_audit as QC
        loader = QC.load_reads_verse
    raw_others = [loader(n) for n in (OTHERS.get(name) or [])]
    reads = apply(name, loader(name), others=raw_others)
    # OPT-IN AND SCOPED, deliberately. `trim` defaults to None (off): the first version defaulted ON and
    # silently rewrote 149 loci across the whole corpus, several of them real scripture. Pass an explicit
    # (book, chapter) to trim, and read the findings in LAST_TRIMS.
    if trim:
        others = [apply(n, o) for n, o in zip(OTHERS.get(name) or [], raw_others)]
        if len(others) >= 2:
            reads, found = trim_apparatus(name, reads, others, scope=trim)
            if found:
                LAST_TRIMS[name] = found
    return reads

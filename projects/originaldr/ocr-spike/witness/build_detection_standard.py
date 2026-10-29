#!/usr/bin/env python
"""R16.7 — the EYE-ATTESTED DETECTION STANDARD, graded by ink mass.

🔴 WHY A NEW STANDARD IS NEEDED AT ALL. Every score this project quotes is GOLD-ENTRY-DRIVEN: it
walks a list of adjudicated boxes and asks what the agent named each one. That loop can only visit
boxes THAT EXIST. A leaf whose entire scripture column got no region contributes nothing to it —
`OT2-1610-P_0749` is the worst-served leaf in the corpus and a label score reads it as silence, not
as failure. **A LABEL SCORE IS STRUCTURALLY BLIND TO A MISSING BOX**, and the eye review found 200+
of them. That blindness is what Piece 3 exists to remove.

⚠️ THIS IS NOT GOLD AND MAY NEVER BE RENAMED INTO ONE. It is the eye review's CLAIM about LECTOR's
claim, unadjudicated: no human verdict settles any of it (`plates/REVIEW-STATE.md`). It is admissible
as the standard against which a DETECTION INSTRUMENT is validated — an instrument found by an eye and
a measure agreeing is on firmer ground than one found by either alone — and it is inadmissible as a
figure to quote about the detector's accuracy.

🔑 GRADED BY INK MASS, AND THE GRADING IS THE POINT. An instrument that measures unclaimed INK cannot
possibly be equally sensitive to a missing body column and a missing catchword: one is a third of the
page, the other is two words. Pooling them into "detection defects: 116/208" would produce a single
recall figure that is a weighted average of a solved problem and an impossible one, and would hide
which is which. So every leaf carries a SEVERITY, and the acceptance criteria are stated per grade.

    SEVERE   the body block itself is unclaimed          — E26.  Ink mass: enormous
    STRUCT   a chapter head or running head has no box   — E25.  Ink mass: a line of display type
    SMALL    a note, signature or catchword has no box   — E9/E27/E3. Ink mass: a few words
    EMPTY    a box drawn over blank paper                — E23.  The INVERSE defect; ink mass zero

⚠️ ADDRESSED BY THE READERS' OWN WORDS, NOT BY THE CODES. E24–E28 were minted from the reader output
AFTER the readers worked, so NOT ONE finding string contains 'E26' and a regex over the codes returns
ZERO for all five. That is a false absence of exactly the shape this project has now recorded five
times — a bounded search returning not-found in the same shape an exhaustive one does. The readers
wrote `NEW:`, `SG-MISSING:` and `E9 (severe)`; those phrasings are the addressable evidence, which is
the concrete reason the merge keeps their strings VERBATIM.

    ../ocr-venv/bin/python witness/build_detection_standard.py           # report
    ../ocr-venv/bin/python witness/build_detection_standard.py --build   # write the standard
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
PLATES = _HERE / "plates"
FINDINGS = PLATES / "eye-findings.json"
BUNDLE = PLATES / "bundle.json"
OUT = PLATES / "detection-standard.json"

# ---------------------------------------------------------------- the phrasings, and their grade
# ⚠️ EACH PATTERN IS A CLAIM ABOUT WHAT THE READERS WROTE, and it is CHECKED: every leaf the pattern
# matches is written into the standard WITH the matching string, so the evidence travels with the
# label and a wrong pattern is visible rather than silently inflating a count.
#
# 🔴 "NO BOX AT ALL" IS THE LOAD-BEARING PHRASE and it is deliberately paired with WHAT was missed.
# The bare phrase appears on catchwords, signatures, notes and body columns alike; the severity is
# carried by the object, never by the phrasing. Matching the phrase alone would grade a missing
# catchword as a missing scripture column.
# ⚠️ `verses? \d` WAS IN HERE AND IT IS A LOCATOR, NOT AN OBJECT. *"the right-margin cite ⟨quoted⟩
# (beside verse 5) has no box"* is a MISSING MARGIN CITE — a SMALL defect — and it was graded as the
# body block going unclaimed because the reader said where on the page it sat. A pattern that
# matches how a defect is ADDRESSED rather than what the defect IS will always do this.
# ⚠️ `body(?! of the leaf)` — THE THIRD LOCATOR THIS PATTERN MISTOOK FOR AN OBJECT. *"the only
# unboxed head furniture in the body of the leaf"* is a MISSING CHAPTER HEAD, graded SEVERE because
# the reader said WHERE it sat. `verse 5` was the first, `PSALME.` as a catchword the second.
_BODY = r"(scripture|psalm(?!e\.)|body(?! of the leaf)|main ?text|whole leaf|text ?block|verse column)"
_MISS = r"(no box|not boxed|unboxed|unclaimed|gets no region|has no region)"
# 🔴 THE QUOTATIONS COME OUT FIRST, AND THIS IS THE WHOLE REPAIR. Two versions of the SEVERE test
# failed in OPPOSITE directions before the cause was found, which is the tell that neither was
# addressing it:
#
#   v1, an 80-120 character proximity window — TOO NARROW. The readers interpose the VERBATIM TEXT of
#      the missing block between the object and the phrase: *"the entire scripture body of Osee ch. 1
#      (verses 1 to 11, 'HE word of our Lord, that was made to Osee the sonne of Beeri…') has NO box
#      at all"* is 140 characters of quotation wide. Three of the five hand-cited E26 leaves fell out
#      of SEVERE, and a presence-only cross-check called them recovered.
#   v2, unbounded same-string co-occurrence — TOO WIDE, and worse, wrong in kind. It fired on `GOOD:`
#      strings, and on `OT2-1610-P_0025` because a CATCHWORD there reads *'PSALME.'* — the quoted
#      early-modern text is full of body vocabulary, so any measure that reads the quotation is
#      reading the BOOK's words as if they were the READER's.
#
# ⚠️ THE QUOTED SPAN IS EVIDENCE ABOUT THE PAGE, NOT DESCRIPTION OF THE DEFECT. Removing it leaves
# the reader's own sentence, and on that sentence a tight window is a rule rather than a guess. This
# is the same distinction the project draws everywhere else between an instrument and its input.
_QUOTED = re.compile(r"'[^']{4,}'|\"[^\"]{4,}\"|\([^)]{40,}\)")
_GOOD = re.compile(r"^\s*GOOD\b", re.I)


def _said(s: str) -> str:
    """The reader's own words, with the book's words taken out."""
    return _QUOTED.sub(" ⟨quoted⟩ ", s)


GRADES = [
    # SEVERE — the body block itself. The most severe detection failure in the corpus.
    # `(severe)` and `unclaimed` are the readers' OWN severity markers and are honoured directly.
    # ⚠️ `(severe)` NO LONGER ELEVATES ON ITS OWN, and the case that forced it is instructive:
    # `OT2-1610-P_0020` reads *"E16 (severe): every region below the drawn `foot` rule … is named SG,
    # but the ink there is the Psalm scripture text"*. That is a MISNAMING marked severe — the
    # reader's severity is about how bad it is, NOT about what kind of defect it is, and this
    # standard is graded by KIND. It must co-occur with a miss phrase to count here.
    # 🔴 SEVERE REQUIRES A TOTALITY MARKER, and that is the rule the four earlier versions were
    # groping for one patch at a time. Every false positive was a body noun used as a LOCATOR rather
    # than as the object — `verse 5`, `PSALME.` (a catchword), `body of the leaf`, `psalm verse` —
    # and each was excluded individually until the shape was obvious: a reader saying the whole block
    # is gone SAYS SO, with `entire`, `whole`, `ENTIRE`, or by naming the block itself (`body block`,
    # `scripture column`, `main text`). A body noun without one of those is telling you WHERE the
    # defect is, not WHAT it is. ⚠️ Patching a pattern per counter-example is how a rule becomes a
    # list of exceptions that fits this corpus and nothing else; the totality marker is a claim about
    # English, and it recovers all eight true positives while rejecting the fourth false one.
    ("SEVERE", re.compile(
        rf"(?=.*{_MISS})"                                    # something must be missing, AND
        rf".*((entire|whole|all of the)\s+\w*\s*{_BODY}"     # the WHOLE of a body object
        rf"|body block|scripture (column|block)|main ?text of the leaf)", re.I)),
    # STRUCT — the page's structural spine: a chapter head or a running head with no box.
    ("STRUCT", re.compile(rf"(chapter head|running ?head|CHAP\.|PSALME [IVX]+\.)[^.]{{0,90}}{_MISS}"
                          rf"|{_MISS}[^.]{{0,90}}(chapter head|running ?head)", re.I)),
    # SMALL — apparatus and foot furniture. The floor case for any ink-based measure.
    ("SMALL", re.compile(rf"(SG-MISSING|signature[^.]{{0,60}}{_MISS}|{_MISS}[^.]{{0,60}}signature"
                         rf"|catchword[^.]{{0,60}}{_MISS}|{_MISS}[^.]{{0,60}}catchword"
                         rf"|\bE3\b|\bE9\b|note[^.]{{0,60}}{_MISS}|{_MISS}[^.]{{0,60}}(note|cite)"
                         rf"|page number[^.]{{0,40}}{_MISS})", re.I)),
    # 🔴 SLACK — THE OTHER HALF OF THE PROBLEM, AND R16.7 SHIPPED WITHOUT IT (Sir, 2026-08-29).
    # Unclaimed ink finds ink no box covers. It is SILENT on the opposite defect: a box that covers
    # far more than its object. Both corrupt the same downstream thing — the crop handed to the
    # recogniser — and they corrupt it in opposite directions, so an instrument measuring only one
    # can be driven to zero by a detector that boxes the whole page. ⚠️ THAT DEGENERATE SOLUTION
    # SCORES PERFECTLY ON UNCLAIMED INK: one box round the leaf leaves nothing unclaimed.
    # The eye already found this in two families: E5 note column SWALLOWED into the MT box (26) and
    # E13 column structure LOST, multi-column matter taken as one block (15).
    ("SLACK", re.compile(r"\bE5\b|\bE13\b|swallow|as one (MT )?block|taken as one|wraps a"
                         r"|merg(ed|ing)|spans the (left|right|whole)|under-?segment", re.I)),
    # EMPTY — the INVERSE: a region over blank paper. An ink measure should find these too, and with
    # the OPPOSITE sign, which makes them a free negative control rather than an afterthought.
    ("EMPTY", re.compile(r"\bE23\b|blank (right )?margin|no ink of this leaf|over blank paper", re.I)),
]
# ⚠️ SLACK RANKS WITH STRUCT, NOT BELOW SMALL. A swallowed note column is a whole genre of
# apparatus lost into a containment class — the same magnitude of harm as a missing head, and
# larger than a missing catchword. The rank orders by CONSEQUENCE, not by pixel count.
RANK = {"SEVERE": 4, "SLACK": 3, "STRUCT": 2, "SMALL": 1, "EMPTY": 0}


def main(build: bool) -> int:
    d = json.loads(FINDINGS.read_text())
    ids = [p["id"] for p in json.loads(BUNDLE.read_text())["plates"]]
    leaves: dict[str, dict] = {}

    for pid in ids:
        hits: dict[str, list[str]] = {}
        for s in d["leaves"].get(pid, []):
            # ⚠️ A `GOOD:` STRING IS THE READER SAYING THE AGENT WAS RIGHT. Both earlier versions
            # scored two of them as the most severe defect in the corpus, because such a string
            # names the objects it approves of and the quoted text supplies the rest.
            if _GOOD.match(s):
                continue
            said = _said(s)
            for grade, rx in GRADES:
                if rx.search(said):
                    hits.setdefault(grade, []).append(s)   # the VERBATIM string is kept as evidence
        if hits:
            worst = max(hits, key=lambda g: RANK[g])
            leaves[pid] = {"severity": worst, "grades": sorted(hits, key=lambda g: -RANK[g]),
                           "evidence": {g: v for g, v in hits.items()}}

    by = {g: [k for k, v in leaves.items() if v["severity"] == g] for g in RANK}
    print("R16.7 — EYE-ATTESTED DETECTION STANDARD")
    print(f"leaves in the plate set : {len(ids)}")
    print(f"leaves with a detection finding : {len(leaves)}  "
          f"({len(leaves) / len(ids):.1%} — this is the BASE RATE any ranking must beat)\n")
    for g in sorted(RANK, key=lambda x: -RANK[x]):
        print(f"  {g:7s} {len(by[g]):3d} leaf/leaves (worst finding on the leaf)")
    print("\n  SEVERE leaves — the body block itself unclaimed:")
    for k in sorted(by["SEVERE"]):
        print(f"     {k}")

    # 🔴 THE CROSS-CHECK AGAINST MY OWN TAXONOMY, RUN RATHER THAN ASSUMED. `_classes` cites exemplar
    # leaves for E25/E26/E27 by hand. If the phrasing search is sound it must RECOVER them; a cited
    # leaf the search misses means the pattern is too narrow, and a citation the plate set does not
    # contain is a broken address. ⚠️ TWO WERE BROKEN when this first ran — `_1011` and `_0661` were
    # written under the OT2 prefix they inherited from their neighbours in the citation list, and
    # neither leaf exists. A bare ordinal is not an address.
    #
    # ⚠️ AND IT CHECKS THE GRADE, NOT MERELY THE PRESENCE. A presence-only check passed while three
    # of the five E26 exemplars sat in `SMALL` — recovered, and recovered as the wrong thing. The
    # citing class implies the grade, so that is what is asserted.
    #
    # ⚠️ ONLY THE DETECTION CLASSES ARE CROSS-CHECKED. E13's and E19's exemplars are UNDER-
    # segmentation and MISnaming — a box exists and is wrong — so requiring a missing-box search to
    # find them would be scoring an instrument against a defect it is not built to see. Excluding
    # them is a scope statement and is written here so it is a decision rather than an omission.
    IMPLIES = {"E26": "SEVERE", "E25": "STRUCT", "E27": "SMALL"}
    # ⚠️ AND THE CHECKER ITSELF HAD THE BARE-ORDINAL BUG IT EXISTS TO CATCH. Matching only FULL ids
    # skipped `_0821`, `_0024` and `_0035` — written bare in the citation list under an implied
    # prefix — so it checked 7 of 12 exemplars and reported a clean sweep. A bare ordinal is resolved
    # here against the last full id seen in the same string, and the count of bare ones is PRINTED,
    # because a citation whose address had to be inferred is weaker evidence than one that carried it.
    cited: dict[str, str] = {}
    bare = 0
    for e, want in IMPLIES.items():
        prefix = None
        for m in re.finditer(r"([A-Z]{2,3}\d?-\d{4}-[BP])_(\d{4})|_(\d{4})", d["_classes"][e]):
            if m.group(1):
                prefix, ordinal = m.group(1), m.group(2)
            elif prefix:
                ordinal, bare = m.group(3), bare + 1
            else:
                continue
            cited.setdefault(f"{prefix}_{ordinal}", want)
    missing_addr = sorted(c for c in cited if c not in set(ids))
    unrecovered = sorted(c for c in cited if c in set(ids) and c not in leaves)
    misgraded = sorted((c, w, leaves[c]["severity"]) for c, w in cited.items()
                       if c in leaves and RANK[leaves[c]["severity"]] < RANK[w])
    print(f"\n  cross-check: {len(cited)} leaves cited by hand in E25/E26/E27, WITH the grade each implies")
    print(f"     of those, {bare} were written as a BARE ORDINAL and resolved by the preceding prefix")
    print(f"     citations naming a leaf NOT IN THE PLATE SET : {len(missing_addr)} "
          f"{' '.join(missing_addr) or '—'}")
    print(f"     cited leaves the phrasing search did NOT find: {len(unrecovered)} "
          f"{' '.join(unrecovered) or '—'}")
    print(f"     cited leaves found but graded TOO LOW        : {len(misgraded)} "
          f"{' '.join(f'{c}({got}<{w})' for c, w, got in misgraded) or '—'}")
    if missing_addr:
        print("     🔴 A CITATION THAT NAMES NO LEAF IS A BROKEN ADDRESS, not a near miss. FIX IT.")
    if misgraded:
        print("     🔴 THE SEARCH IS TOO NARROW. A leaf recovered at the wrong grade is not recovered.")
    bad = bool(missing_addr or unrecovered or misgraded)

    if build:
        OUT.write_text(json.dumps({
            "_doc": "Eye-attested DETECTION defects per leaf, graded by ink mass. Built by "
                    "witness/build_detection_standard.py from plates/eye-findings.json.",
            "_warning": "NOT GOLD, NOT ADJUDICATED. This is Jarvis's claim about LECTOR's claim. "
                        "Admissible for VALIDATING a detection instrument; inadmissible as a figure "
                        "quoted about the detector's accuracy.",
            "_base_rate": len(leaves) / len(ids),
            "_grades": {g: len(by[g]) for g in RANK},
            "leaves": leaves}, indent=1, ensure_ascii=False))
        print(f"\nwritten -> {OUT.relative_to(_HERE.parent)}")
    else:
        print("\n(report only — pass --build to write)")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main("--build" in sys.argv))

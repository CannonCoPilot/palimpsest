#!/usr/bin/env python
"""Gold masking-map completion for work idx 80 — The Dead Sea Scrolls Translated
(García Martínez / Watson, Eerdmans 2011). Monkeypatch-only verification per
MAPPING_AGENT_SPEC.md. Does NOT edit shared engines.

Structure (close reading of reference_text()):
  front matter (singular, already in gold): title_page, contents, preface, foreword,
    introduction[36138,124274)
  body: 9 thematic "chapters" (the editor's word) = `part` (generic), tiled 124274..1093367.
    Each part opens with one translator's prose `introduction` (heading -> first ms siglum),
    then a run of per-manuscript `translation` units headed by a siglum line.
  back matter (singular, gold): bibliography (List of the Manuscripts from Qumran) -> EOF.
  apparatus: "Notes to the Introduction" (~88 numbered endnotes) closing the front-matter
    Introduction -> typed `endnotes` ON TOP of the introduction tile (no deferral).

Counts verified programmatically against reference_text():
  part            = 9   (exact, 9 mixed-case chapter headings)
  introduction    = 9   (per-chapter, exact anchors) + 1 singular front-matter scholarly intro
  translation     = 271 (manuscript siglum headers; gold's "270" is the author's editorial
                         round figure — see count correction note below)
"""
import sys
import instance_edges
import masking_map

IDX = 80

# ── Repeating instance rules ─────────────────────────────────────────────────────
# part (generic): the 9 thematic chapters. Body renders each heading in mixed case
# (the TOC ALL-CAPS forms do not recur in the body). tile=True -> partition the body.
PART_HEADS = "(?m)" + "|".join("(?:%s)" % h for h in [
    r"\n\nRules\n\nThis chapter contains",
    r"Halakhic Texts\n\nA large part",
    r"Literature with Eschatological Content\n\nAlthough",
    r"Exegetical Literature\n\nThe exegetical",
    r"Para-biblical Literature\n\nThis chapter also gathers",
    r"Poetic Texts\n\nDue to our ignorance",
    r"Liturgical Texts\n\nThis chapter contains a set",
    r"Astronomical Texts, Calendars and Horoscopes\n\nThis chapter assembles",
    r"The Copper Scroll\n\nPossibly the most mystifying",
])

# translation (specific, PRIMARY): per-manuscript siglum header lines. The recurring
# delimiter is a line that begins with a cave siglum (NQ / OCR i,l,I for 1; optional
# A/B copy-band letter; or the Cairo "Damascus Document (CD-A/B)" lines) and ends with a
# parenthesised siglum, e.g. "1QRule of the Community (iQs)", "4Q394 [4QMMTa]",
# "Damascus Document (CD-A)". Requiring the trailing "(...)" siglum excludes the two
# OCR false positives (a wrapped prose line "4QFlorilegium are various forms…" and the
# composition-number line "4Q550"). tile=True -> partition the manuscript bodies.
MS_HEADER = (
    r"(?m)"
    r"(?:"
    r"^"
    r"(?:[ABC] )?"                       # optional A/B/C copy-band prefix
    r"(?:[0-9]{1,2}|[ilI])Q"             # cave siglum (OCR i/l/I == 1)
    r"[^\n]{0,68}"
    r"\([^\n)]{0,45}\)"                   # ends with a parenthesised siglum
    r"\s*$"
    r"|"
    r"^Damascus Document\w? \(CD-[AB]\)\s*$"   # Cairo Genizah copies (no Q prefix)
    r")"
)

# Per-chapter translation spans: each chapter's manuscript run is tiled WITHIN its own
# [first-ms, next-chapter-heading) span so the last translation of a chapter ends exactly
# at the chapter boundary (no bleed into the next chapter's heading+intro). Counts per
# chapter verified against reference_text(): 25+18+22+30+91+41+33+10+1 = 271.
CHAP_TRANS_SPANS = [
    ("1QRule of the Community (iQs)",
     "Halakhic Texts\n\nA large part of the contents", 25),
    ("4QHalakhic Letter' (4Q394 [4QMMT°])",
     "Literature with Eschatological Content\n\nAlthough eschatology", 18),
    ("1QWar Scroll (1QM [+1Q33])\n\nCol. i i For the Ins[tructor: The Rule] of the War.",
     "Exegetical Literature\n\nThe exegetical activity", 22),
    ("4QTargum of Leviticus (4Q156 14QtgLev])",
     "Para-biblical Literature\n\nThis chapter also gathers together", 30),
    ("A 4QReworked Pentateuch' (4Q158 [4QRP'])",
     "Poetic Texts\n\nDue to our ignorance", 91),
    ("4QPsalmsi (4Q88 [4QPW])",
     "Liturgical Texts\n\nThis chapter contains a set of poetic texts", 41),
    ("4QDaily Prayers' (4Q5o3 [4QPrQuot])",
     "Astronomical Texts, Calendars and Horoscopes\n\nThis chapter assembles", 33),
    ("4QAstronomical Enochb (4Q2o9 [4QEnastrb at])",
     "The Copper Scroll\n\nPossibly the most mystifying", 10),
    ("3QCopper Scroll (3Q15)",
     "List of the Manuscripts from Qumran", 1),
]

instance_edges.RULES[IDX] = [
    {
        "type": "part",                 # GENERIC container — 9 thematic chapters
        "kind": "regex_in_span",
        "pattern": PART_HEADS,
        "at": "start", "tile": True,
        "expected_count": 9,
    },
] + [
    {
        "type": "translation",          # SPECIFIC primary — manuscript translations
        "kind": "regex_in_span",
        "pattern": MS_HEADER,
        "at": "start", "tile": True,
        "span_start": s,
        "span_end": e,
        "expected_count": n,
    }
    for s, e, n in CHAP_TRANS_SPANS
]

# ── Singular supplements (front/apparatus the gold omits) ────────────────────────
# 9 per-chapter editorial introductions: heading -> first manuscript siglum of the
# chapter (covers the chapter heading + the translator's prose intro + composition
# sub-headings). Anchors resolve exactly once.
INTRO_SUPP = [
    ("\n\nRules\n\nThis chapter contains those texts which can be called",
     "1QRule of the Community (iQs)"),
    ("Halakhic Texts\n\nA large part of the contents",
     "4QHalakhic Letter' (4Q394 [4QMMT°])"),
    ("Literature with Eschatological Content\n\nAlthough eschatology",
     "1QWar Scroll (1QM [+1Q33])\n\nCol. i i For the Ins[tructor: The Rule] of the War."),
    ("Exegetical Literature\n\nThe exegetical activity",
     "4QTargum of Leviticus (4Q156 14QtgLev])"),
    ("Para-biblical Literature\n\nThis chapter also gathers together",
     "A 4QReworked Pentateuch' (4Q158 [4QRP'])"),
    ("Poetic Texts\n\nDue to our ignorance",
     "4QPsalmsi (4Q88 [4QPW])"),
    ("Liturgical Texts\n\nThis chapter contains a set of poetic texts",
     "4QDaily Prayers' (4Q5o3 [4QPrQuot])"),
    ("Astronomical Texts, Calendars and Horoscopes\n\nThis chapter assembles",
     "4QAstronomical Enochb (4Q2o9 [4QEnastrb at])"),
    ("The Copper Scroll\n\nPossibly the most mystifying",
     "3QCopper Scroll (3Q15)"),
]

masking_map.SUPPLEMENT[IDX] = [
    {"type": "introduction", "start_anchor": s, "end_anchor": e}
    for s, e in INTRO_SUPP
] + [
    # endnotes apparatus closing the front-matter Introduction (overlay on intro tile)
    {"type": "endnotes",
     "start_anchor": "Notes to the Introduction\n\n1 F. M. Cross",
     "end_anchor": "Rules\n\nThis chapter contains those texts which can be called"},
]

# ── Audit ────────────────────────────────────────────────────────────────────────
# count gate for repeating rules
import instance_edges as ie
from masking_map import project_for
text = project_for(IDX).reference_text()
for rule in ie.RULES[IDX]:
    starts = ie.materialize(text, rule)
    exp = rule["expected_count"]
    print(f"GATE {rule['type']:12} materialized {len(starts)} (expected {exp}) "
          f"-> {'GREEN' if len(starts)==exp else 'RED'}")

a = masking_map.audit(IDX)
print("coverage:", a["coverage_pct"])
print("counts:", {k: v for k, v in a["type_counts"].items() if v})
print("unresolved:", a["unresolved"])
for r in a["sparse_regions"][:10]:
    print("  sparse", r["cls"], r["start"], r["end"], r["len"], repr(r.get("head", "")[:60]))

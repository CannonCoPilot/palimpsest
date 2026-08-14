#!/usr/bin/env python
"""Verify the gold masking-map for work 105 (Dead Sea Scrolls Reader Vol. 1).

Monkeypatches instance_edges.RULES[105] + masking_map.SUPPLEMENT[105] only — never
edits the shared engines.  Run: .venv/bin/python core/tests/fixtures/gold/harness/_verify_105.py

Model (parallel scholarly edition — Qumran texts):
  front matter  : title_page, copyright, contents, introduction×2, glossary (gold singulars)
                  + a 51c GENERAL-TABLE-OF-CONTENTS stub (supplement contents)
  GENERIC layer : body[0,EOF]  +  6 lettered genre `part` sections (title_list, tile)
                  +  6 named `book` compositions (supplement spans, grouping mss)
  SPECIFIC layer: 63 per-manuscript `translation` blocks (regex on the 'trans.' attribution
                  line, tile) + the lead-in 1QS I-III edition unit (supplement translation)
"""
import sys, re
import instance_edges, masking_map
from harness import project_for

IDX = 105
t = project_for(IDX).reference_text()
n = len(t)

# ── 6 lettered genre sections (part, GENERIC) — body-start anchors, each unique ──
SEC_A = "2\n\nA. COMMUNITY RULES\n\nSerekh ha-Yaúad"
SEC_B = "194\n\nB. ESCHATOLOGICAL RULES\n\nRULE OF THE CONGREGATION"
SEC_C = "292\n\nC. PURITY RULE\n\n4Q274 (4QTohorot A) ed. J. M. Baumgarten, DJD XXXV"
SEC_D = "298\n\nD. OTHER RULES\n\n4Q159 (4QOrdinancesa) ed. J. M. Allegro, DJD V"
SEC_E = "326\n\nE. EPISTOLARY TREATISE CONCERNED WITH RELIGIOUS LAW\n\nMiq§at Ma>a°e Ha-Torah = MMT"
SEC_F = "338\n\nF. UNCLASSIFIED TEXTS CONCERNED WITH RELIGIOUS LAW\n\n4Q276 (4QTohorot Ba) ed. J. M. Baumgarten, DJD XXXV"

# trans. attribution line — the 63-block primary anchor (programmatically verified == 63)
TRANS_RE = r"(?m)^.*\btrans\.\s"

instance_edges.RULES[IDX] = [
    {
        "type": "part",            # 6 lettered genre/classification sections (GENERIC)
        "kind": "title_list",
        "titles": [SEC_A, SEC_B, SEC_C, SEC_D, SEC_E, SEC_F],
        "expected_count": 6,
    },
    {
        "type": "translation",     # 63 per-manuscript English-translation blocks (SPECIFIC, primary)
        "kind": "regex_in_span",
        "pattern": TRANS_RE,
        "at": "start", "tile": True,
        "expected_count": 63,
    },
]

# ── SUPPLEMENT (front matter the gold omits + book grouping + lead-in unit) ──
masking_map.SUPPLEMENT[IDX] = [
    # GENERAL-TABLE-OF-CONTENTS stub between gold `contents` end and the introduction body.
    {"type": "contents",
     "start_anchor": "GENERAL TABLE OF CONTENTS\nI\n\nGENERAL INTRODUCTION",
     "end_anchor": "The Dead Sea Scrolls Reader (DSSR) presents for the first time"},

    # Lead-in 1QS I-III edition unit (transcription paired with translation[0]) — gives the
    # first parallel-edition unit its SPECIFIC translation layer; trans-line tiling starts at 44002.
    {"type": "translation",
     "start_anchor": SEC_A.split("\n\nSerekh")[0] + "\n\nSerekh ha-Yaúad\n\n1QS I 1–III 12 ed.",
     "end_anchor": "1QS I 1–III 12 trans. M. Wise, M. Abegg, and E. Cook with"},

    # 6 named compositions (book, GENERIC, role=secondary) grouping their manuscript copies.
    {"type": "book", "start_anchor": "Serekh ha-Yaúad\n\n1QS I 1–III 12 ed.",
     "end_anchor": "Serekh le<anshey ha-Yaúad\n\n1QS V 1–XI 22, ed."},
    {"type": "book", "start_anchor": "Serekh le<anshey ha-Yaúad\n\n1QS V 1–XI 22, ed.",
     "end_anchor": "Damascus Document (D)\n\n4Q266 (4QDa) ed."},
    {"type": "book", "start_anchor": "Damascus Document (D)\n\n4Q266 (4QDa) ed.",
     "end_anchor": "194\n\nB. ESCHATOLOGICAL RULES"},
    {"type": "book", "start_anchor": "RULE OF THE CONGREGATION\n\n1Q28a (1QSa) ed.",
     "end_anchor": "1Q33 (1QM[ilúamah] = 1QWar Scroll [Rule]) ed."},
    {"type": "book", "start_anchor": "1Q33 (1QM[ilúamah] = 1QWar Scroll [Rule]) ed.",
     "end_anchor": "292\n\nC. PURITY RULE"},
    {"type": "book",
     "start_anchor": "326\n\nE. EPISTOLARY TREATISE CONCERNED WITH RELIGIOUS LAW\n\nMiq§at Ma>a°e Ha-Torah = MMT",
     "end_anchor": "338\n\nF. UNCLASSIFIED"},

    # ── footnote apparatus (8 per-page note blocks: 7 in the General Introduction, 1 closing
    # the Introduction to Part 1). Each runs from its first numbered note (just after the page's
    # rule-line) to the page-number that ends the page. Typed `footnotes` ON TOP of the
    # introduction tile (spec: apparatus is not absorbed into its container type). ──
    {"type": "footnotes", "start_anchor": "1 Several persons helped us in this",
     "end_anchor": "viii\n\nThe Dead Sea Scrolls Reader"},
    {"type": "footnotes", "start_anchor": "3 Exceptions to this rule are the",
     "end_anchor": "ix\n\nGeneral Introduction"},
    {"type": "footnotes", "start_anchor": "6 Some of the very fragmentary texts which ha",
     "end_anchor": "x\n\nThe Dead Sea Scrolls Reader"},
    {"type": "footnotes", "start_anchor": "10 These transcriptions were prepared for the",
     "end_anchor": "xi\n\nGeneral Introduction"},
    {"type": "footnotes", "start_anchor": "16 The data and difficulties involved are des",
     "end_anchor": "xii\n\nThe Dead Sea Scrolls Reader"},
    {"type": "footnotes", "start_anchor": "18 It would not be amiss to note that vol. V",
     "end_anchor": "xiii\n\nGeneral Introduction"},
    {"type": "footnotes", "start_anchor": "20 Such typographic errors are corrected in t",
     "end_anchor": "xiv\n\nThe Dead Sea Scrolls Reader"},
    {"type": "footnotes", "start_anchor": "1 DSSR follows the classification of A. Lange",
     "end_anchor": "xxii\n\nIntroduction to Part 1"},
]


# ── reconcile counts then audit coverage ──
print("== count gates ==")
for rule in instance_edges.RULES[IDX]:
    starts = instance_edges.materialize(t, rule)
    exp = rule["expected_count"]
    print(f"  {rule['type']:<12} materialized {len(starts):>3} (expected {exp:>3}) "
          f"-> {'GREEN' if len(starts) == exp else 'RED'}")

a = masking_map.audit(IDX)
print("\n== audit ==")
print("coverage:", a["coverage_pct"])
print("counts:", {k: v for k, v in a["type_counts"].items() if v})
print("unresolved:", a["unresolved"])
print("n_sparse_runs:", a["n_sparse_runs"], " sparse_chars:", a["sparse_chars"])
for r in a["sparse_regions"][:12]:
    print("  sparse", r["cls"], r["start"], r["end"], r["len"], repr(r.get("head", "")[:70]))

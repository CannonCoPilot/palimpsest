import sys;import instance_edges, masking_map

IDX = 48

instance_edges.RULES[IDX] = [
    {   # PRIMARY tiling layer: 29 per-text editorial introductions, anchored at each
        # text's byline-block. tile=True ⇒ each instance spans to the next text start,
        # so the per-text introduction/translation/notes/bibliography body is covered.
        "type": "introduction",
        "kind": "regex_in_span",
        "pattern": r"(?m)^(?:A (?:new )?translation and introduction\n\nby |Introduction\n\nby |by Lorne R\. Zelyck\n\nIrenaeus)",
        "at": "start", "tile": True,
        "span_start": "I. Gospels and Related Traditions of New Testament Figures",
        "expected_count": 29,
    },
    {   # PRIMARY: 30 'Translation'/'Translations' section headers (27 + 3). Thin markers
        # (tile=False) — they mark the rendered-translation sub-block inside each text;
        # introduction already tiles the body, so translation need not re-tile.
        "type": "translation",
        "kind": "regex_in_span",
        "pattern": r"(?m)^Translations?\n\n",
        "at": "start", "tile": False,
        "span_start": "I. Gospels and Related Traditions of New Testament Figures",
        "expected_count": 30,
    },
    {   # PRIMARY: 29 per-text bibliographies, headed exactly 'Bibliography'. Thin markers.
        "type": "bibliography",
        "kind": "regex_in_span",
        "pattern": r"(?m)^Bibliography\n\n",
        "at": "start", "tile": False,
        "span_start": "I. Gospels and Related Traditions of New Testament Figures",
        "expected_count": 29,
    },
]

masking_map.SUPPLEMENT[IDX] = [
    {   # Leading part-division header + first text title strip [39116,39219): the only
        # main-matter char-run not absorbed by the introduction tile (subsequent
        # part-headers+titles ride inside the prior instance's tail). Typed `header`.
        "type": "header",
        "start_anchor": "I. Gospels and Related Traditions of New Testament Figures",
        "end_anchor": "A translation and introduction\n\nby Mark Glen Bilby",
    },
    {   # LCCN tail of the copyright/imprint block: the copyright singular mask's
        # end_anchor lands at the START of this sentence, leaving it [~350,425] bare.
        # Reabsorb it into the copyright band, ending at the dedication.
        "type": "copyright",
        "start_anchor": "A catalog record for this book is available from the Library of Congress.",
        "end_anchor": "Dedicated to current students (and future scholars) of Christian apocrypha",
    },
    {   # 'Note on Cyrillic Transliteration' [~28184,29836]: a transliteration-scheme /
        # orthography reference note between the volume Introduction and the Abbreviations
        # list. Sigla→Latin mapping table ⇒ typed `glossary` (same class the gold assigns
        # the Abbreviations block; gold's glossary note states this note 'precedes' it).
        "type": "glossary",
        "start_anchor": "Note on Cyrillic Transliteration by Slavomír Čéplö",
        "end_anchor": "Abbreviations\n\nUnless listed below, all abbreviations",
    },
]

a = masking_map.audit(IDX)
print("coverage:", a["coverage_pct"])
print("counts:", {k: v for k, v in a["type_counts"].items() if v})
print("unresolved:", a["unresolved"])
print("n_sparse_runs:", a["n_sparse_runs"], "sparse_chars:", a["sparse_chars"])
for r in a["sparse_regions"][:12]:
    print(" sparse", r["cls"], r["start"], r["end"], r["len"], repr(r.get("head", "")[:60]))

# Count-gate verification
import instance_edges as ie
from harness import project_for
t = project_for(IDX).reference_text()
for rule in ie.RULES[IDX]:
    got = len(ie.materialize(t, rule))
    print(f"GATE {rule['type']}: {got} == {rule['expected_count']} -> {'GREEN' if got==rule['expected_count'] else 'RED'}")

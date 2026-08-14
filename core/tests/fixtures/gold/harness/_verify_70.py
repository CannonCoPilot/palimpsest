import sys;import instance_edges, masking_map

instance_edges.RULES[70] = [
    {
        # 2 volumes (GENERIC). Printed division lines "Volume I"/"Volume II" precede
        # chapters I and XVIII. Tiles the whole body (4118 -> Endnotes).
        "type": "volume",
        "kind": "regex_in_span",
        "pattern": r"(?m)^Volume [IVXLC]+\n\n",
        "at": "start", "tile": True,
        "span_start": "Charlotte Temple\n\nA Tale of Truth\n\nVolume I",
        "span_end": "Endnotes\n\nThe above lines, in the original American edition",
        "expected_count": 2,
    },
    {
        # 35 chapters (SPECIFIC, primary). Each heading is a line-start Roman numeral
        # I..XXXV, OPTIONALLY followed by fused endnote digits (XXI11, XXXI18 — the two
        # the nav-built detector misses). Title line follows after \n\n. Tiles the body.
        "type": "chapter",
        "kind": "regex_in_span",
        "pattern": r"(?m)^[IVXLC]+\d*\n\n",
        "at": "start", "tile": True,
        "span_start": "Volume I\n\nI\n\nA Boarding School",
        "span_end": "Endnotes\n\nThe above lines, in the original American edition",
        "expected_count": 35,
    },
]

masking_map.SUPPLEMENT[70] = [
    {"type": "title_page", "start_anchor": "<<BOF>>",
     "end_anchor": "Imprint\n\nThis ebook is the product"},
    {"type": "copyright", "start_anchor": "Imprint\n\nThis ebook is the product",
     "end_anchor": "\"She was her parents' only joy"},
    {"type": "epigraph", "start_anchor": "\"She was her parents' only joy",
     "end_anchor": "The Author's Preface"},
    {"type": "preface", "start_anchor": "The Author's Preface",
     "end_anchor": "Charlotte Temple\n\nA Tale of Truth\n\nVolume I"},
    {"type": "title_page", "start_anchor": "Charlotte Temple\n\nA Tale of Truth\n\nVolume I",
     "end_anchor": "I\n\nA Boarding School", "resolve": "last"},
]

a = masking_map.audit(70)
print("coverage:", a["coverage_pct"])
print("counts:", {k: v for k, v in a["type_counts"].items() if v})
print("unresolved:", a["unresolved"])
for r in a["sparse_regions"][:10]:
    print(" sparse", r["cls"], r["start"], r["end"], r["len"], repr(r.get("head", "")[:60]))

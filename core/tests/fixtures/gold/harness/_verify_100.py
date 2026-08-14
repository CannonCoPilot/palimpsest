import sys;import instance_edges, masking_map

instance_edges.RULES[100] = [
    {
        "type": "book",  # 73 books (generic) — boundary at each book's Chapter 1
        "kind": "regex_in_span",
        "pattern": r"(?m)^.{0,40}?\bChapter 1\b",
        "at": "start", "tile": True,
        "expected_count": 73,
    },
    {
        "type": "chapter",  # 1334 chapters (specific) tile the verse bodies
        "kind": "regex_in_span",
        "pattern": r"(?m)^(?!\()(?:.{0,40}?)\bChapter \d+\b",
        "at": "start", "tile": True,
        "expected_count": 1334,
    },
    {
        "type": "chapter_heading",  # 1334 heading+summary markers (gold primary)
        "kind": "regex_in_span",
        "pattern": r"(?m)^(?!\()(?:.{0,40}?)\bChapter \d+\b",
        "at": "start", "tile": False,
        "expected_count": 1334,
    },
]

masking_map.SUPPLEMENT[100] = [
    {"type": "front_matter", "start_anchor": "<<BOF>>",
     "end_anchor": "Genesis Chapter 1\n\nGod createth Heaven and Earth"},  # title page + Contents + Genesis argument
]

# ---- count gates ----
from harness import project_for  # noqa: E402
t = project_for(100).reference_text()
for rule in instance_edges.RULES[100]:
    starts = instance_edges.materialize(t, rule)
    gate = "GREEN" if len(starts) == rule["expected_count"] else "RED"
    print(f"GATE {rule['type']:<16} materialized {len(starts)} exp {rule['expected_count']} -> {gate}")

a = masking_map.audit(100)
print("coverage:", a["coverage_pct"])
print("counts:", {k: v for k, v in a["type_counts"].items() if v})
print("unresolved:", a["unresolved"])
for r in a["sparse_regions"][:10]:
    print(" sparse", r["cls"], r["start"], r["end"], r["len"], repr(r.get("head", "")[:60]))

import sys;import instance_edges, masking_map

# ── Per-book chapter rules (SPECIFIC layer; tile the body) ───────────────────────
# Chapter numbering RESTARTS per book and each book uses a DIFFERENT heading format:
#   1 Enoch  — bracket form '[Chapter N}'  (108; OCR-corrupt '[Chapter 35J','[Chapter 361',
#              'IChapter 85/105/106]', '[Chapter 60] - Noah's Vision'); pattern anchors the
#              heading START so trailing OCR garble is irrelevant.
#   2 Enoch  — title-case 'Chapter N'  (68; '5' OCR'd 'S'; ch 4/24/27 glued to the END of the
#              prior paragraph line so NOT at ^ — caught by 'heading-then-blank-line').
#   3 Enoch  — uppercase '^CHAPTER N'  (54; '5' & '8' OCR'd 'S'; 15B, 22-B, 22-C, 48A-D parts).
# Each rule is span-scoped to its own book so its last chapter tiles only to the NEXT book's
# introduction (a SUPPLEMENT mask), NOT across book boundaries.
instance_edges.RULES[64] = [
    {"type": "chapter", "kind": "regex_in_span",
     "pattern": r"(?m)^[\[I]Chapt", "at": "start", "tile": True,
     "span_start": "[Chapter I}",
     "span_end": "Introduction to The Second Book\n\nof Enoch:\n\nSlavonic Enoch",
     "expected_count": 108},
    {"type": "chapter", "kind": "regex_in_span",
     "pattern": r"Chapter (?:\d+|S)\b[\"”’)]*\n\n", "at": "start", "tile": True,
     "span_start": "Chapter 1\n\n1 There was a wise man",
     "span_end": "Intro duction of 3 Enoch",
     "expected_count": 68},
    {"type": "chapter", "kind": "regex_in_span",
     "pattern": r"(?m)^CHAPTER\b", "at": "start", "tile": True,
     "span_start": "Intro duction of 3 Enoch",
     "expected_count": 54},
]

# ── SUPPLEMENT singular masks (front seams + 2 per-book introductions) ───────────
# The 2 per-book introductions also act as the tiling boundary that stops the prior
# book's last chapter at the book seam (precision). Each spans [intro-heading, next book's
# first chapter), absorbing the short book-title heading at its tail.
masking_map.SUPPLEMENT[64] = [
    # intro heading 'INTRODUCTION\n\n' that precedes the gold introduction's start anchor
    {"type": "introduction",
     "start_anchor": "INTRODUCTION\n\nThe study of scripture",
     "end_anchor": "The study of scripture is a lifelong venture"},
    # intro tail ('Let us now proceed…') + page furniture + 1 Enoch title heading,
    # up to 1 Enoch chapter 1
    {"type": "introduction",
     "start_anchor": "Let us now proceed to the Book of Enoch.",
     "end_anchor": "[Chapter I}"},
    # 2 Enoch (Slavonic) per-book introduction → tail = book-2 title heading → ch1
    {"type": "introduction",
     "start_anchor": "Introduction to The Second Book\n\nof Enoch:\n\nSlavonic Enoch",
     "end_anchor": "Chapter 1\n\n1 There was a wise man"},
    # 3 Enoch (Hebrew) per-book introduction → tail = book-3 title heading → CHAPTER I
    {"type": "introduction",
     "start_anchor": "Intro duction of 3 Enoch",
     "end_anchor": "CHAPTER I\n\n"},
]

a = masking_map.audit(64)
print("coverage:", a["coverage_pct"])
print("counts:", {k: v for k, v in a["type_counts"].items() if v})
print("unresolved:", a["unresolved"])
for r in a["sparse_regions"][:15]:
    print(" sparse", r["cls"], r["start"], r["end"], r["len"], repr(r.get("head", "")[:70]))

# Count gate per rule
text = __import__("harness").project_for(64).reference_text()
for rule in instance_edges.RULES[64]:
    starts = instance_edges.materialize(text, rule)
    gate = "GREEN" if len(starts) == rule["expected_count"] else "RED"
    print(f"  GATE {rule['type']} span={rule['span_start'][:18]!r}: {len(starts)}/{rule['expected_count']} {gate}")

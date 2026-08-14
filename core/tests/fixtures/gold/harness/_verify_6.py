import sys;import re
import instance_edges
import masking_map
from harness import project_for

IDX = 6
t = project_for(IDX).reference_text()

# ── Anchors (resolved once, verified) ───────────────────────────────────────────
# Scripture main matter: first chapter argument (Genesis 1) .. last verse before back matter.
FIRST_ARG = t.find('THE FIRST BOOK OF MOSES')          # 55281 — book head, front-matter ends here
BACK_MATTER = t.find('A FORM OF PRAYER TO BE USED')      # 6637818 — back matter begins

# Chapter argument/superscription block start: the \n\n-block immediately before each verse-1.
# verse-1 marker is '\n\n1\xa0' (non-breaking space); the block before it (no internal \n\n) is the
# argument (numbered editorial summary) or, for Psalms, the superscription. Anchor at that block.
CHAP_RE = r"\n\n(?:(?!\n\n)[\s\S])*?(?=\n\n1\xa0)"

# Obadiah is the lone single-chapter book whose verse 1 is fused into its argument ("1 1 The
# vision of Obadiah ...") so it has no '\n\n1\xa0' marker. Add it explicitly so its chapter is typed.
OBADIAH = t.find('\n\nOBADIAH\n\n1 1 The vision')


def patched_materialize(text, rule):
    """Augment the engine's regex_in_span chapter rules with the Obadiah extra anchor."""
    starts = _orig_materialize(text, rule)
    if rule.get("_obadiah"):
        starts = sorted(set(starts) | {OBADIAH})
    return starts


_orig_materialize = instance_edges.materialize
instance_edges.materialize = patched_materialize
masking_map.materialize = patched_materialize  # masking_map imported `materialize` by name

instance_edges.RULES[IDX] = [
    {
        "type": "chapter",          # SPECIFIC — tiles every verse body + argument + apparatus
        "kind": "regex_in_span",
        "pattern": CHAP_RE,
        "at": "start", "tile": True,
        "span_start": "THE FIRST BOOK OF MOSES",
        "span_end": "A FORM OF PRAYER TO BE USED",
        "expected_count": 1133,     # 1132 \n\n1\xa0 chapters + Obadiah
        "_obadiah": True,
    },
    {
        "type": "chapter_heading",  # SPECIFIC marker (gold primary) — the numbered argument
        "kind": "regex_in_span",
        "pattern": CHAP_RE,
        "at": "start", "tile": False,
        "span_start": "THE FIRST BOOK OF MOSES",
        "span_end": "A FORM OF PRAYER TO BE USED",
        "expected_count": 1133,
        "_obadiah": True,
    },
]

masking_map.SUPPLEMENT[IDX] = [
    # Front matter: title page, copyright, TOC, foreword, prefaces, instructions, book-lists —
    # everything up to (and incl.) the Genesis book heading, abutting Genesis 1's argument so the
    # first chapter tile starts exactly here (no GENERIC_ONLY seam at the book head).
    {"type": "front_matter", "start_anchor": "<<BOF>>",
     "end_anchor": "\n\n11 God created the heaven and the earth"},
    # Back matter 1: the appended "Form of Prayer" devotional (after Revelation, before the editor note).
    {"type": "appendix", "start_anchor": "A FORM OF PRAYER TO BE USED",
     "end_anchor": "The preceding prayers, from the 1599 Geneva Bible"},
    # Back matter 2: the editor's note on the updated prayers.
    {"type": "afterword", "start_anchor": "The preceding prayers, from the 1599 Geneva Bible",
     "end_anchor": "GLOSSARY\n\nWORD"},
    # NOTE: the A-Z glossary (GLOSSARY\n\nWORD .. EOF) is already a gold singular mask.
]

a = masking_map.audit(IDX)
print("coverage:", a["coverage_pct"])
print("counts:", {k: v for k, v in a["type_counts"].items() if v})
print("unresolved:", a["unresolved"])
print("sparse runs:", a["n_sparse_runs"], "sparse chars:", a["sparse_chars"])
for r in a["sparse_regions"][:12]:
    print(" sparse", r["cls"], r["start"], r["end"], r["len"], repr(r.get("head", "")[:70]))

# Count gate
for rule in instance_edges.RULES[IDX]:
    starts = patched_materialize(t, rule)
    print(f"GATE {rule['type']}: {len(starts)} vs {rule['expected_count']} -> "
          f"{'GREEN' if len(starts) == rule['expected_count'] else 'RED'}")

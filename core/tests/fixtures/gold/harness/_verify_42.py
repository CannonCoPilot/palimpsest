import sys;import re
import instance_edges
import masking_map
from harness import project_for

IDX = 42
t = project_for(IDX).reference_text()
N = len(t)

# ── The 39 per-text title offsets (each text tiles: title -> next title) ──────────
# Each text opens "<Title>\n\n(A new translation and introduction|Introduction and a
# new translation)\n\nby <editor>". The title is the paragraph immediately before the
# opener phrase. The whole per-text span (intro + translation + apparatus + biblio)
# is one TRANSLATED WORK unit -> typed `translation` (the masked rendered ancient text
# is the body of each unit; the editor intro/biblio/notes are typed ON TOP).
_OPENER = re.compile(r'(?i)\n\n(?:A new translation and introduction|'
                     r'Introduction and a new translation)')


def _text_title_starts(text):
    starts = []
    for m in _OPENER.finditer(text):
        pre = text.rfind('\n\n', 0, m.start())
        starts.append(pre + 2)
    return sorted(starts)


_TITLE_STARTS = _text_title_starts(t)
assert len(_TITLE_STARTS) == 39, len(_TITLE_STARTS)

# Part I body head ("I. Texts Ordered according to Biblical Chronology") sits 48 chars
# before the first title; start the translation tile there so the part head + first
# title strip are covered by the translation specific layer (no gap).
_PARTI_HEAD = t.find('I. Texts Ordered according to Biblical Chronology')
assert _PARTI_HEAD >= 0
_TILE_STARTS = [_PARTI_HEAD] + _TITLE_STARTS[1:]


# ── Custom materializer: explicit-offset tiling/region rules ──────────────────────
# instance_edges' built-in kinds key on anchors/regex; the per-text tile + footnote
# regions are computed programmatically (offsets), so register a kind="offset_tile"
# (contiguous partition over given starts) and kind="offset_regions" (bounded,
# non-tiling regions) and patch materialize to honor them.
_orig_materialize = instance_edges.materialize


def _materialize(text, rule):
    if rule.get("kind") == "offset_tile":
        return list(rule["starts"])
    if rule.get("kind") == "offset_regions":
        # bounded (start,end) regions handled in the patched build_elements; return
        # [] so the stock tiling loop in build_elements adds nothing for them.
        return []
    return _orig_materialize(text, rule)


instance_edges.materialize = _materialize
masking_map.materialize = _materialize


# ── Numbered intro-footnote regions: the consecutive ^\d+\. run after each text's
# Bibliography block. Bounded exactly (first "1. " to end of the last consecutive
# numbered paragraph). Lettered translation notes (a.,b.,c.) are interleaved with the
# translation tail and not separately contiguous; the numbered run is the cleanly
# boundable apparatus region. ─────────────────────────────────────────────────────
def _numbered_fn_regions(text, title_starts):
    bib = re.compile(r'\n\nBibliography\n\n')
    bibs = [m.start() for m in bib.finditer(text)]
    bounds = title_starts + [len(text)]
    regions = []
    for b in bibs:
        # window: from this bib to the next text title
        hi = next((x for x in bounds if x > b), len(text))
        m = re.search(r'(?m)^1\. ', text[b:hi])
        if not m:
            continue
        start = b + m.start()
        # walk consecutive numbered paragraphs ^N. ; region ends where numbering breaks
        pos = start
        last_end = start
        expect = 1
        while True:
            mm = re.match(r'(\d+)\. ', text[pos:pos + 12])
            if not mm:
                break
            # find end of this paragraph
            nxt = text.find('\n\n', pos)
            if nxt < 0 or nxt >= hi:
                last_end = hi
                break
            last_end = nxt
            pos = nxt + 2
        if last_end > start:
            regions.append((start, last_end))
    return regions


_FN_REGIONS = _numbered_fn_regions(t, _TILE_STARTS)


_BOUNDS = _TILE_STARTS + [N]


def _bib_region(m):
    """Bound one bibliography: header -> start of following numbered-note run (or
    next text boundary). Captures the whole alphabetized reference block."""
    s = m.start() + 2
    hi = next((x for x in _BOUNDS if x > s), N)
    mm = re.search(r'(?m)^\d+\. ', t[m.end():hi])
    end = m.end() + mm.start() if mm else hi
    # trim a trailing blank-line separator so the region ends on real text
    while end > s and t[end - 1] == '\n':
        end -= 1
    return (s, end)


# ── Build elements: monkeypatch build_elements to honor offset_regions bounds ─────
_orig_build = masking_map.build_elements


def _build(idx):
    text, els = _orig_build(idx)
    # offset_regions produce bounded (non-tiling) elements; inject directly
    for rule in instance_edges.RULES.get(idx, []):
        if rule.get("kind") == "offset_regions":
            for s, e in rule["regions"]:
                els.append({"type": rule["type"], "start": s, "end": e,
                            "source": "rule:offset_regions"})
    return text, els


masking_map.build_elements = _build


# ── RULES ─────────────────────────────────────────────────────────────────────────
instance_edges.RULES[IDX] = [
    {   # GENERIC: 2 parts (title-case body heads; uppercase forms live only in TOC)
        "type": "part", "kind": "offset_tile",
        "starts": [t.find("I. Texts Ordered according to Biblical Chronology"),
                   t.find("II. Thematic Texts")],
        "expected_count": 2,
    },
    {   # SPECIFIC TILE: 39 translated works tile the whole main body (part head -> EOF)
        "type": "translation", "kind": "offset_tile",
        "starts": _TILE_STARTS,
        "expected_count": 39,
    },
    {   # SPECIFIC: 39 per-text editor introductions (markers on top of the tile)
        "type": "introduction", "kind": "offset_regions",
        "regions": [(s, t.find('\n\nBibliography\n\n', s)
                     if 0 <= t.find('\n\nBibliography\n\n', s) < (
                         _TILE_STARTS[i + 1] if i + 1 < len(_TILE_STARTS) else N)
                     else min(s + 4000, N))
                    for i, s in enumerate(_TITLE_STARTS)],
        "expected_count": 39,
    },
    {   # SPECIFIC: 40 per-text bibliographies (1 per text + 1 split-list extra).
        # Each runs from its "Bibliography" header to the start of the following
        # numbered-footnote run (^N. ) or the next text boundary — the full
        # alphabetized reference block, not just the first entry.
        "type": "bibliography", "kind": "offset_regions",
        "regions": [_bib_region(m) for m in re.finditer(r'\n\nBibliography\n\n', t)],
        "expected_count": 40,
    },
    {   # SPECIFIC: numbered intro-footnote regions (consecutive ^N. run after biblio)
        "type": "footnotes", "kind": "offset_regions",
        "regions": _FN_REGIONS,
        "expected_count": len(_FN_REGIONS),
    },
]

masking_map.SUPPLEMENT[IDX] = [
    {   # volume-level editors' Introduction (1 of the 40 introductions). [22710,107931)
        "type": "introduction",
        "start_anchor": "Introduction\n\nby Richard Bauckham and James R. Davila",
        "end_anchor": "Abbreviations\n\nUnless listed below, all abbreviations"},
    {   # List of Abbreviations / sigla -> glossary (closest registered type, as idx48)
        "type": "glossary",
        "start_anchor": "Abbreviations\n\nUnless listed below, all abbreviations",
        "end_anchor": "I. Texts Ordered according to Biblical Chronology"},
]

a = masking_map.audit(IDX)
print("coverage:", a["coverage_pct"])
print("counts:", {k: v for k, v in a["type_counts"].items() if v})
print("unresolved:", a["unresolved"])
print("n_sparse_runs:", a["n_sparse_runs"], "sparse_chars:", a["sparse_chars"])
for r in a["sparse_regions"][:14]:
    print(" sparse", r["cls"], r["start"], r["end"], r["len"], repr(r.get("head", "")[:60]))

# Count gates
print("--- GATES ---")
print("part:", 2, "translation:", len(_TILE_STARTS), "intro(repeat):", len(_TITLE_STARTS),
      "bib:", t.count('\n\nBibliography\n\n'), "fn_regions:", len(_FN_REGIONS))

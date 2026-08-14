import sys;import re
import instance_edges, masking_map
from harness import project_for

IDX = 101
t = project_for(IDX).reference_text()
N = len(t)

# ── Chapter / chapter_heading regex: 385 explicit labels + 8 implicit single-chapter
#    book-title headers (Enos, Jarom, Omni, Words of Mormon, 4 Nephi, JS—Matthew,
#    JS—History, Articles of Faith) = 393 (canon/geometry count). ──────────────────
CHAP_PAT = (
    r"(?m)^(?:Chapter|Section) \d+\b"
    r"|^The Book of Enos\b"
    r"|^The Book of Jarom\b"
    r"|^The Book of Omni\b"
    r"|^The Words of Mormon\b"
    r"|^Fourth Nephi\b"
    r"|^Joseph Smith—Matthew\n\n"
    r"|^Joseph Smith—History\n\n"
    r"|^The Articles of Faith\b"
)

# ── Volume regex: 3 standard-works divisions (generic). ───────────────────────────
VOL_PAT = (
    r"(?m)^BOOK OF\n\nMORMON"
    r"|T\nhe Doctrine and Covenants is a co"
    r"|T\nhe Pearl of Great Price is a se"
)

# ── Book regex: 20 books (15 BoM + 5 PoGP), body-title headers, disambiguated. ────
BOOK_PAT = (
    r"(?m)^The First Book of Nephi\b"
    r"|^The Second Book of Nephi\b"
    r"|^The Book of Jacob\b"
    r"|^The Book of Enos\b"
    r"|^The Book of Jarom\b"
    r"|^The Book of Omni\b"
    r"|^The Words of Mormon\b"
    r"|^The Book of Mosiah\b"
    r"|^The Book of Alma\b"
    r"|^The Book of Helaman\b"
    r"|^Third Nephi\b"
    r"|^Fourth Nephi\b"
    r"|^The Book of Mormon\n\nChapter 1\n\nAmmaron"
    r"|^The Book of Ether\b"
    r"|^The Book of Moroni\b"
    r"|^Selections from the\b"
    r"|^The Book of Abraham\b"
    r"|^Joseph Smith—Matthew\n\n"
    r"|^Joseph Smith—History\n\n"
    r"|^The Articles of Faith\b"
)

# ── Footnotes: per-entry apparatus markers (^N x ). Distinct masked layer, ON TOP
#    of the chapter tiles. tile:False (markers); count unverifiable per gold (null). ─
FN_PAT = r"(?m)^\d+ [a-z] "

# Facsimile caption separator is U+2002 (en-space).
ENSP = chr(0x2002)  # U+2002 EN SPACE


def n_matches(pat):
    return len(set(m.start() for m in re.finditer(pat, t)))


print("=== programmatic count verification ===")
print("chapter (393):", n_matches(CHAP_PAT),
      " [^Chapter:", n_matches(r"(?m)^Chapter \d+\b"),
      "^Section:", n_matches(r"(?m)^Section \d+\b"), "+ 8 implicit]")
print("volume (3):   ", n_matches(VOL_PAT))
print("book (20):    ", n_matches(BOOK_PAT))
FN_N = n_matches(FN_PAT)
print("footnote entry markers:", FN_N)
print()

instance_edges.RULES[IDX] = [
    # generics
    {"type": "volume", "kind": "regex_in_span", "pattern": VOL_PAT,
     "at": "start", "tile": True, "expected_count": 3},
    {"type": "book", "kind": "regex_in_span", "pattern": BOOK_PAT,
     "at": "start", "tile": True, "expected_count": 20},
    # specific content tiler
    {"type": "chapter", "kind": "regex_in_span", "pattern": CHAP_PAT,
     "at": "start", "tile": True, "expected_count": 393},
    # specific markers (do NOT tile / swallow body)
    {"type": "chapter_heading", "kind": "regex_in_span", "pattern": CHAP_PAT,
     "at": "start", "tile": False, "expected_count": 393},
    # footnote apparatus layer (markers, on top of tiles)
    {"type": "footnotes", "kind": "regex_in_span", "pattern": FN_PAT,
     "at": "start", "tile": False, "expected_count": FN_N},
]

masking_map.SUPPLEMENT[IDX] = [
    # front matter (title page -> contents -> introduction -> [gold front_matter] -> introduction)
    {"type": "title_page", "start_anchor": "<<BOF>>",
     "end_anchor": "© 1981, 2013 by Intellectual Reserve, Inc."},
    {"type": "contents", "start_anchor": "English approval: 11/12",
     "end_anchor": "Contents\n\nT\nhe Book of Mormon is a volume of holy scripture"},
    {"type": "introduction",
     "start_anchor": "Contents\n\nT\nhe Book of Mormon is a volume of holy scripture",
     "end_anchor": "The Testimony of Three Witnesses\n\nB\ne it known unto all nations"},
    # [9699,12207] = gold front_matter singular (Witnesses; gold end_anchor resolves
    # at the START of the Eight-Witnesses signer roster, so this introduction picks up
    # the roster tail + Prophet-Joseph-Smith testimony excerpt + Brief Explanation).
    {"type": "introduction",
     "start_anchor": "Hiram Page\nJoseph Smith, Sen.\nHyrum Smith\nSamuel H. Smith",
     "end_anchor": "Chapter 1\n\nNephi begins the record of his people"},
    # the 3 Facsimile inserts (apparatus ON TOP of the Abraham chapter tiles).
    {"type": "insert",
     "start_anchor": "A Facsimile from the Book of Abraham\n\nFig. 1." + ENSP + "The Angel",
     "end_anchor": "called the Book of\nAbraham, written by his own hand, upon papyrus."},
    {"type": "insert",
     "start_anchor": "A Facsimile from the Book of Abraham\n\nNo. 2",
     "end_anchor": "and, at that\nday, many followed after him."},
    {"type": "insert",
     "start_anchor": "A Facsimile from the Book of Abraham\n\nFig. 1." + ENSP + "Abraham sitting",
     "end_anchor": "Abraham is reasoning upon the principles of Astronomy, in the king's court."},
]

a = masking_map.audit(IDX)
print("=== audit ===")
print("coverage:", a["coverage_pct"])
print("counts:", {k: v for k, v in a["type_counts"].items() if v})
print("unresolved:", a["unresolved"])
print("sparse runs:", a["n_sparse_runs"], "chars:", a["sparse_chars"])
for r in a["sparse_regions"][:15]:
    print("  sparse", r["cls"], r["start"], r["end"], r["len"], repr(r.get("head", "")[:60]))

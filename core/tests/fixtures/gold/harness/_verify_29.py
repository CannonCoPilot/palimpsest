"""Verify the complete gold masking map for work idx 29
(The Message of the Qur'An, Muhammad Asad).

Monkeypatch only — does NOT edit the shared engines.

Structure materialized:
  front matter (singular, from gold): title_page, contents, foreword, bibliography  [0 .. 39934]
  chapter  x114  — surahs, tile the main body  [39934 .. 1307081]
  introduction x114 — Asad per-surah note (after Period line -> first verse), ON TOP of chapter
  translation  x114 — verse blocks (first verse -> next surah heading), ON TOP of chapter
  appendix x4    — APPENDIX I..IV, tile  [1307081 .. 1344185]
  footnotes x1   — pooled commentary block  [1344185 .. EOF]
"""
import re
import sys

import instance_edges          # noqa: E402
import masking_map             # noqa: E402
from harness import project_for  # noqa: E402

IDX = 29

# ── Region constants (verified by _probe_29.py / probes) ─────────────────────
BODY_BANNER = 39934          # "THE MESSAGE OF THE QUR'ĀN" — start of main matter
APPENDIX_START = 1307081     # "APPENDIX I" — first appendix heading
FOOTNOTE_POOL = 1344185      # "1 It is to be borne in mind..." — pooled notes start

_SURAH = re.compile(r"(?m)^THE [A-Z\-]+(?: [A-Z\-]+)? SŪRAH$")
_APPX = re.compile(r"(?m)^APPENDIX [IVX]+$")
_PERIOD = re.compile(r"(?m)^(?:Mecca Period|Medina Period|Period Uncertain)$")
_VERSE1 = re.compile(r"(?m)^\(1\) ")


# ── Rules: chapter (tile) + appendix (tile). intro/translation injected via the
#    build_elements override below (interleaved sub-blocks the tiling kinds can't
#    express). Counts here are the COUNT GATE targets. ─────────────────────────
instance_edges.RULES[IDX] = [
    {
        "type": "chapter", "kind": "regex_in_span",
        "pattern": r"(?m)^THE [A-Z\-]+(?: [A-Z\-]+)? SŪRAH$",
        "at": "start", "tile": True,
        "span_start": "THE MESSAGE OF THE QUR'ĀN\n\nTHE FIRST SŪRAH",
        "span_end": "APPENDIX I\n\nSYMBOLISM AND ALLEGORY IN THE QUR'ĀN",
        "expected_count": 114,
    },
    {
        "type": "appendix", "kind": "regex_in_span",
        "pattern": r"(?m)^APPENDIX [IVX]+$",
        "at": "start", "tile": True,
        "span_start": "APPENDIX I\n\nSYMBOLISM AND ALLEGORY IN THE QUR'ĀN",
        "span_end": "1 It is to be borne in mind that, in its final compilation",
        "expected_count": 4,
    },
]

# Front matter (title_page/contents/foreword/bibliography) + pooled footnotes.
# The four front singulars already live in the gold contract; footnotes is added
# here as the bounded pooled-apparatus element (5326 notes, one block).
masking_map.SUPPLEMENT[IDX] = [
    {"type": "footnotes",
     "start_anchor": "1 It is to be borne in mind that, in its final compilation",
     "end_anchor": "<<EOF>>"},
]


# ── Sub-block materializers (interleaved per surah) ──────────────────────────
def _surah_subblocks(text):
    """Return (intro_spans, trans_spans), each a list of (start,end), 114 long."""
    starts = [m.start() for m in _SURAH.finditer(text)]
    bounds = starts + [APPENDIX_START]
    intro, trans = [], []
    for i, s in enumerate(starts):
        e = bounds[i + 1]
        pm = _PERIOD.search(text, s, e)
        vm = _VERSE1.search(text, s, e)
        istart = pm.end()                 # just after the '...Period' word
        # skip the blank line so the boundary lands on the dropcap (real edge)
        while istart < len(text) and text[istart] in "\r\n":
            istart += 1
        intro.append((istart, vm.start()))
        trans.append((vm.start(), e))
    return intro, trans


# ── build_elements override: base engine + banner-extended first chapter +
#    interleaved introduction/translation sub-blocks. ──────────────────────────
_orig_build = masking_map.build_elements


def _build(idx):
    text, els = _orig_build(idx)
    if idx != IDX:
        return text, els
    # Extend the first chapter tile back to the body banner so the 27-char
    # banner ("THE MESSAGE OF THE QUR'ĀN\n\n") is inside the chapter (no GENERIC_ONLY).
    chs = [e for e in els if e["type"] == "chapter"]
    if chs:
        first = min(chs, key=lambda e: e["start"])
        first["start"] = BODY_BANNER
    # Inject the 114 introduction + 114 translation sub-blocks (overlap chapter).
    intro, trans = _surah_subblocks(text)
    for s, e in intro:
        els.append({"type": "introduction", "start": s, "end": e, "source": "subblock:intro"})
    for s, e in trans:
        els.append({"type": "translation", "start": s, "end": e, "source": "subblock:trans"})
    return text, els


masking_map.build_elements = _build


# ── COUNT GATE: reconcile tiling rules + sub-block counts ────────────────────
text = project_for(IDX).reference_text()
print("=== COUNT GATE ===")
for rule in instance_edges.RULES[IDX]:
    starts = instance_edges.materialize(text, rule)
    exp = rule["expected_count"]
    print(f"  {rule['type']:<12} materialized {len(starts):>4} / expected {exp:>4} "
          f"-> {'GREEN' if len(starts) == exp else 'RED'}")
intro, trans = _surah_subblocks(text)
print(f"  {'introduction':<12} materialized {len(intro):>4} / expected  114 "
      f"-> {'GREEN' if len(intro) == 114 else 'RED'}")
print(f"  {'translation':<12} materialized {len(trans):>4} / expected  114 "
      f"-> {'GREEN' if len(trans) == 114 else 'RED'}")

# Footnote pool count: split on blank lines, read leading integer of each para.
pool = text[FOOTNOTE_POOL:]
paras = [p for p in re.split(r"\n\n+", pool) if p.strip()]
nums = []
for p in paras:
    m = re.match(r"\s*(\d+)\b", p)
    if m:
        nums.append(int(m.group(1)))
mono = all(nums[i] <= nums[i + 1] for i in range(len(nums) - 1)) if nums else False
print(f"  {'footnotes':<12} pool paras={len(paras)} numbered={len(nums)} "
      f"first={nums[0] if nums else '-'} last={nums[-1] if nums else '-'} "
      f"monotonic_nondec={mono} -> expected last=5326")

# ── AUDIT ────────────────────────────────────────────────────────────────────
a = masking_map.audit(IDX)
print("\n=== AUDIT ===")
print("coverage:", a["coverage_pct"])
print("counts:", {k: v for k, v in a["type_counts"].items() if v})
print("unresolved:", a["unresolved"])
print("n_sparse_runs:", a["n_sparse_runs"], "sparse_chars:", a["sparse_chars"])
for r in a["sparse_regions"][:10]:
    print("  sparse", r["cls"], r["start"], r["end"], r["len"], repr(r.get("head", "")[:60]))

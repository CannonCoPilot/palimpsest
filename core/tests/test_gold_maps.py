"""Hermetic verification of the committed Gold-Set masking maps.

Every ``fixtures/gold/maps/work-<idx>.map.json`` is a durable, version-controlled
masking contract (schema ``palimpsest.gold-map/v1``): a full char-span tiling of a
work, plus the ``reference_sha256`` of the exact text those offsets were cut against.
At runtime the maps are applied by ``server._apply_gold_map``, which re-checks the sha
against a freshly-ingested project — but that path needs the (usually copyrighted,
never-committed) source text and a live workspace, so it only runs on the machine that
holds the ingested cache. That is the same reason the anchor-based annotation golds
(``gold_verify.py`` / ``gold_ratify.py`` / ``a3_score.py``) are hand-run tools and not
part of this suite: they resolve against live text via the machine-local eval harness.

This module is the CI-runnable half. It re-derives the *generator's own gates*
(``mask_engine/gen_marker_gold.py``: zero unresolved elements, 100% two-layer
GENERIC+SPECIFIC coverage, raw-marker count parity) directly from the frozen JSON —
which stores everything needed (``text_len``, ``sections``, ``type_counts``), so no
source text is required — and round-trips each map through the *production* loader
(``LayoutConfig.from_dict``) and masker (``masked_intervals``). A schema or taxonomy
drift that would break real gold application therefore fails here first.

The one invariant it cannot check hermetically is ``reference_sha256`` vs. the live
text; that tie is verified on-machine at generation and application time. Everything
else — the structural correctness of the map as printed — is verified here, which makes
the marker-Bible Gold Set (idx 201-219) a first-class citizen of the automated suite
rather than a set of standalone, hand-verified artifacts.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from functools import lru_cache
from pathlib import Path

import pytest

from palimpsest.layout import LayoutConfig, _UNMASKED_TYPES, masked_intervals

MAPS_DIR = Path(__file__).parent / "fixtures" / "gold" / "maps"

# The GENERIC coverage layer, per the map generators (``gen_marker_gold.GENERIC`` /
# ``gen_gold_maps``): the structural nesting containers that tile the whole work at the
# coarse grain. Everything else is the SPECIFIC layer. Both layers must independently
# tile [0, text_len) with no gaps — the "100% two-layer coverage" gate. Pinned on
# purpose: a new container type absent from this set is exactly the drift a gold test
# should force a human to reconcile, not silently absorb.
_GENERIC_LAYER = frozenset({"body", "volume", "book", "part", "section"})

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_MARKER_GEN = "gen_marker_gold"  # substring of ``generated_from`` for marker-Bible maps
# Marker-Bible admission floors, mirrored from gen_marker_gold (MIN_BOOKS / MIN_CHAPTERS).
_MIN_BOOKS, _MIN_CHAPTERS = 4, 20

# The flagship marker-Bible Gold Set this infrastructure exists to protect. 204-207 are
# intentionally absent (never scraped); the guard is a subset check, so adding maps is
# fine and only a deletion trips it.
_EXPECTED_BIBLE_IDXS = frozenset({201, 202, 203, *range(208, 220)})


def _idx_of(path: Path) -> int:
    return int(path.stem.split("-")[1].split(".")[0])


_MAP_PATHS = sorted(MAPS_DIR.glob("work-*.map.json"), key=_idx_of)
_MAP_IDS = [f"work-{_idx_of(p):03d}" for p in _MAP_PATHS]


@lru_cache(maxsize=None)
def _load(path_str: str) -> dict:
    return json.loads(Path(path_str).read_text(encoding="utf-8"))


def _merge(spans: list[tuple[int, int]]) -> list[tuple[int, int]]:
    out: list[tuple[int, int]] = []
    for s, e in sorted(spans):
        if out and s <= out[-1][1]:
            out[-1] = (out[-1][0], max(out[-1][1], e))
        else:
            out.append((s, e))
    return out


def _gaps(merged: list[tuple[int, int]], n: int) -> list[tuple[int, int]]:
    gaps: list[tuple[int, int]] = []
    cur = 0
    for s, e in merged:
        if s > cur:
            gaps.append((cur, s))
        cur = max(cur, e)
    if cur < n:
        gaps.append((cur, n))
    return gaps


# ── inventory guards ─────────────────────────────────────────────────────────

def test_maps_discovered() -> None:
    """The glob is wired correctly and the committed set has not silently shrunk."""
    assert MAPS_DIR.is_dir(), f"missing maps dir: {MAPS_DIR}"
    assert len(_MAP_PATHS) >= 30, f"only {len(_MAP_PATHS)} maps found — deletions?"


def test_flagship_bible_golds_present() -> None:
    """The marker-Bible Gold Set (201-219) is complete — the deliverable this guards."""
    present = {_idx_of(p) for p in _MAP_PATHS}
    missing = sorted(_EXPECTED_BIBLE_IDXS - present)
    assert not missing, f"missing flagship Bible golds: {missing}"


# ── per-map hermetic gates ───────────────────────────────────────────────────

@pytest.mark.parametrize("path", _MAP_PATHS, ids=_MAP_IDS)
def test_schema_and_identity(path: Path) -> None:
    d = _load(str(path))
    assert d.get("schema") == "palimpsest.gold-map/v1"
    assert d.get("idx") == _idx_of(path), "idx field disagrees with filename"
    assert _SHA256_RE.match(d.get("reference_sha256", "") or ""), "reference_sha256 not 64-hex"
    for key in ("source_file", "text_len", "element_count", "type_counts",
                "mask_by_type", "sections"):
        assert key in d, f"missing required key: {key}"
    assert isinstance(d["text_len"], int) and d["text_len"] > 0


@pytest.mark.parametrize("path", _MAP_PATHS, ids=_MAP_IDS)
def test_deserializes_via_production_loader(path: Path) -> None:
    """The frozen map still loads into the current production LayoutConfig types."""
    d = _load(str(path))
    cfg = LayoutConfig.from_dict(d)
    assert cfg.sections, "no sections"
    assert len(cfg.sections) == d["element_count"] == len(d["sections"])


@pytest.mark.parametrize("path", _MAP_PATHS, ids=_MAP_IDS)
def test_spans_wellformed(path: Path) -> None:
    """Generator gate #1: zero unresolved elements — every span within [0, text_len)."""
    d = _load(str(path))
    n = d["text_len"]
    bad = [(s.get("id"), s["start"], s["end"]) for s in d["sections"]
           if not (0 <= s["start"] < s["end"] <= n)]
    assert not bad, f"{len(bad)} malformed spans (n={n}): {bad[:5]}"


@pytest.mark.parametrize("path", _MAP_PATHS, ids=_MAP_IDS)
def test_type_counts_reconcile(path: Path) -> None:
    """The summary ``type_counts`` matches the actual per-type section tally."""
    d = _load(str(path))
    actual = dict(Counter(s["type"] for s in d["sections"]))
    assert actual == d["type_counts"]


@pytest.mark.parametrize("path", _MAP_PATHS, ids=_MAP_IDS)
def test_two_layer_coverage(path: Path) -> None:
    """Generator gate #2: GENERIC and SPECIFIC layers each tile [0, text_len) fully."""
    d = _load(str(path))
    n = d["text_len"]
    for layer, in_layer in (("GENERIC", True), ("SPECIFIC", False)):
        merged = _merge([(s["start"], s["end"]) for s in d["sections"]
                         if (s["type"] in _GENERIC_LAYER) is in_layer])
        gaps = _gaps(merged, n)
        assert not gaps, f"{layer} coverage gaps ({len(gaps)}): {gaps[:5]}"


@pytest.mark.parametrize("path", _MAP_PATHS, ids=_MAP_IDS)
def test_mask_by_type_matches_taxonomy(path: Path) -> None:
    """``mask_by_type`` is re-derivable from the live taxonomy, not a frozen stale copy."""
    d = _load(str(path))
    types_present = sorted({s["type"] for s in d["sections"]})
    expected = {t: (t not in _UNMASKED_TYPES) for t in types_present}
    assert d["mask_by_type"] == expected


@pytest.mark.parametrize("path", _MAP_PATHS, ids=_MAP_IDS)
def test_masking_contract(path: Path) -> None:
    """The production masker runs clean, honors its postcondition, and masks something."""
    d = _load(str(path))
    n = d["text_len"]
    cfg = LayoutConfig.from_dict(d)
    mi = masked_intervals(cfg.sections, cfg.mask_by_type, n)
    assert all(0 <= a < b <= n for a, b in mi), "masked interval out of range"
    assert all(mi[i][1] <= mi[i + 1][0] for i in range(len(mi) - 1)), \
        "masked intervals not sorted/disjoint"
    assert sum(b - a for a, b in mi) > 0, "gold map masks zero characters"


@pytest.mark.parametrize("path", _MAP_PATHS, ids=_MAP_IDS)
def test_marker_bible_parity(path: Path) -> None:
    """Generator gate #3 (marker Bibles only): raw-marker count parity.

    ``chapter`` and ``chapter_heading`` are emitted 1:1 by gen_marker_gold, and a real
    canon clears the book/chapter admission floors. Non-marker (epub) maps carry no
    ``chapter_heading`` track, so the parity gate does not apply — skip them.
    """
    d = _load(str(path))
    if _MARKER_GEN not in (d.get("generated_from") or ""):
        pytest.skip("not a marker-Bible map")
    tc = d["type_counts"]
    assert tc.get("chapter") == tc.get("chapter_heading"), "chapter/chapter_heading parity broken"
    assert tc.get("book", 0) >= _MIN_BOOKS, "below marker-Bible book floor"
    assert tc.get("chapter", 0) >= _MIN_CHAPTERS, "below marker-Bible chapter floor"

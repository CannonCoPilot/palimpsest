"""Gold-Set registry + verification — the production core shared by the CLI, the API,
and the canon-oracle test, so all three read the registry and judge a map identically.

The gold artifacts live under ``core/tests/fixtures/gold/`` — the same location the
server resolves via ``server._gold_maps_dir`` — and this module is their single
programmatic entry point: the sources manifest (registry), the frozen masking maps, the
canonical versification oracle, and a from-JSON map verifier that needs no source text.
"""
from __future__ import annotations

import json
from collections import Counter
from functools import lru_cache
from pathlib import Path
from typing import Any

from palimpsest.canon import _normalize

GOLD_DIR = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "gold"
MAPS_DIR = GOLD_DIR / "maps"
MANIFEST_PATH = GOLD_DIR / "sources.manifest.json"
NONBIBLE_MANIFEST_PATH = GOLD_DIR / "sources.nonbible.manifest.json"
CANON_PATH = GOLD_DIR / "canon_chapters.json"

# Variant base names (Vulgate/Latin/Old-English/apocryphal spellings) → canon_chapters
# keys. Sourced from canon.py's _BASE_DIVISION variants; the resolver preserves ordinals,
# so e.g. "1 paralipomenon" → "1 chronicles".
_ALIAS: dict[str, str] = {
    "josue": "joshua", "paralipomenon": "chronicles", "nehemias": "nehemiah",
    "canticle of canticles": "song of solomon", "song of songs": "song of solomon",
    "osee": "hosea", "abdias": "obadiah", "jonas": "jonah", "micheas": "micah",
    "habacuc": "habakkuk", "sophonias": "zephaniah", "aggeus": "haggai",
    "zacharias": "zechariah", "malachias": "malachi", "malachie": "malachi",
    "isaias": "isaiah", "isaie": "isaiah", "jeremias": "jeremiah", "jeremy": "jeremiah",
    "ezechiel": "ezekiel", "apocalypse": "revelation",
    # deuterocanon variants
    "tobias": "tobit", "wisdom": "wisdom of solomon", "sirach": "ecclesiasticus",
    "epistle of jeremiah": "letter of jeremiah", "epistle of jeremy": "letter of jeremiah",
    "song of the three children": "prayer of azariah", "prayer of manasses": "prayer of manasseh",
    "machabees": "maccabees",
}


def load_manifest() -> dict[str, Any]:
    """The Bible Gold-Set registry (sources.manifest.json)."""
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def load_nonbible_manifest() -> dict[str, Any]:
    """The non-Bible Gold-Set registry (sources.nonbible.manifest.json)."""
    return json.loads(NONBIBLE_MANIFEST_PATH.read_text(encoding="utf-8"))


def registry_entries() -> list[dict[str, Any]]:
    """Every gold entry across the whole set — Bibles + non-Bible works — kind-agnostic.

    The two manifests are kept as separate files so each keeps an honest ``scope``, but the
    lookup/enumeration paths (``manifest_entry``, ``gold list``, ``gold verify``) treat the
    gold set as one registry. Bibles carry a ``translation`` label, works a ``title``.
    """
    return list(load_manifest()["bibles"]) + list(load_nonbible_manifest()["works"])


@lru_cache(maxsize=1)
def load_canon() -> dict[str, Any]:
    """The external versification oracle (canon_chapters.json)."""
    return json.loads(CANON_PATH.read_text(encoding="utf-8"))


def map_path(idx: int) -> Path:
    return MAPS_DIR / f"work-{idx:03d}.map.json"


@lru_cache(maxsize=None)
def load_map(idx: int) -> dict[str, Any]:
    return json.loads(map_path(idx).read_text(encoding="utf-8"))


def manifest_entry(idx: int) -> dict[str, Any] | None:
    return next((e for e in registry_entries() if e.get("id") == idx), None)


def canon_key(label: str) -> str:
    """Resolve a book label to its canon_chapters key (ordinal-aware, variant-normalized)."""
    ordinal, base = _normalize(label)
    base = _ALIAS.get(base, base)
    return f"{ordinal} {base}" if ordinal else base


def books_chapters(gmap: dict) -> list[tuple[str, int]]:
    """(book_label, chapter_count) per book via span-containment (metadata-agnostic)."""
    secs = gmap["sections"]
    chaps = [s for s in secs if s["type"] == "chapter"]
    out = []
    for b in (s for s in secs if s["type"] == "book"):
        bs, be = b["start"], b["end"]
        out.append((b.get("label", "?"), sum(1 for c in chaps if bs <= c["start"] < be)))
    return out


def classify_books(idx: int) -> tuple[list, list, list, list]:
    """Resolve every book of a map against the oracle.

    Returns (core_ok, core_bad, deutero, unresolved), each a list of (key, label, got,
    expected) tuples — core_bad/unresolved being the accuracy failures a strict Bible
    must have empty.
    """
    canon = load_canon()
    core, apoc = canon["protestant_66"], canon["kjv_apocrypha"]
    core_ok, core_bad, deutero, unresolved = [], [], [], []
    for label, got in books_chapters(load_map(idx)):
        key = canon_key(label)
        if key in core:
            (core_ok if got == core[key] else core_bad).append((key, label, got, core[key]))
        elif key in apoc:
            deutero.append((key, label, got, apoc[key]))
        else:
            unresolved.append((key, label, got, None))
    return core_ok, core_bad, deutero, unresolved


def classify_books_catholic(idx: int) -> tuple[list, list, list]:
    """Resolve a Catholic (Vulgate/Douay-Rheims) map against the ordered DR canon.

    The Protestant name-keyed oracle cannot judge a Vulgate edition: its canon genuinely
    differs (Esther 16 with the Greek additions, Daniel 14 with Susanna+Bel, Baruch 6 with
    the Epistle of Jeremiah, 1 Esdras = Ezra = 10), and the original-DR book labels are
    verbose incipits ("The Book of Iosue, in Hebrew Iehosua …") that defeat name lookup. So
    this checks the map's book *sequence* positionally against ``catholic_dr`` — the fixed
    Clementine Vulgate order being itself an externally-established fact — confirming each
    slot's identity by a label token and gating on the external chapter count.

    Returns (ok, count_bad, align_bad), each a list of (position, book, label, got,
    expected) tuples: ``count_bad`` are books in the right slot with the wrong chapter
    count; ``align_bad`` are slots whose label does not carry the expected book's token (or
    a book-count length mismatch) — a divergence from the canonical order itself.
    """
    canon = load_canon()["catholic_dr"]
    books = books_chapters(load_map(idx))
    ok: list = []
    count_bad: list = []
    align_bad: list = []
    if len(books) != len(canon):
        align_bad.append((0, "*length*", f"map has {len(books)} books", len(books), len(canon)))
    for pos, (exp, (label, got)) in enumerate(zip(canon, books), 1):
        row = (pos, exp["book"], label, got, exp["chapters"])
        if exp["match"] not in label.lower():
            align_bad.append(row)
        elif got == exp["chapters"]:
            ok.append(row)
        else:
            count_bad.append(row)
    return ok, count_bad, align_bad


def quran_sura_count(idx: int) -> int:
    """Count the suras of a flat-structured Qur'an map (idx 29, 107).

    Unlike the Bibles (book → chapter nesting), the Qur'an's 114 suras are top-level
    ``chapter`` sections with no enclosing ``book`` span, so ``books_chapters`` — which
    derives its tallies *inside* book spans — would find nothing and any book-based oracle
    would vacuously pass. The externally-established fact is instead the fixed 114-sura
    canon, so this is a pure section count. It counts ``chapter`` specifically because a
    Qur'an map may carry parallel per-sura ``introduction``/``translation`` sections (idx
    29) that must not inflate the tally.
    """
    return sum(1 for s in load_map(idx)["sections"] if s["type"] == "chapter")


def verify_map(idx: int) -> list[str]:
    """Verify a frozen gold map from the JSON alone — structural gates + canon oracle.

    Re-derives the marker generator's gates through the *production* loader/masker (a
    schema or taxonomy drift that would break real gold application fails here), then, for
    Bibles whose registered accuracy source is the canon oracle, checks per-book chapter
    counts against the external versification table. Needs no source text. Returns a list
    of human-readable problems; empty means the map passes.
    """
    from palimpsest.layout import LayoutConfig, masked_intervals

    problems: list[str] = []
    d = load_map(idx)
    n = d.get("text_len", 0)
    if not isinstance(n, int) or n <= 0:
        return [f"invalid text_len: {n!r}"]

    bad = [(s.get("id"), s["start"], s["end"]) for s in d["sections"]
           if not (0 <= s["start"] < s["end"] <= n)]
    if bad:
        problems.append(f"{len(bad)} malformed spans, e.g. {bad[:3]}")

    if dict(Counter(s["type"] for s in d["sections"])) != d.get("type_counts"):
        problems.append("type_counts do not reconcile with sections")

    try:
        cfg = LayoutConfig.from_dict(d)
        mi = masked_intervals(cfg.sections, cfg.mask_by_type, n)
        if not all(0 <= a < b <= n for a, b in mi):
            problems.append("masked interval out of range")
        if not all(mi[i][1] <= mi[i + 1][0] for i in range(len(mi) - 1)):
            problems.append("masked intervals not sorted/disjoint")
        if sum(b - a for a, b in mi) <= 0:
            problems.append("map masks zero characters")
    except Exception as e:  # noqa: BLE001
        problems.append(f"production loader/masker rejected map: {e}")

    if "gen_marker_gold" in (d.get("generated_from") or ""):
        tc = d.get("type_counts", {})
        if tc.get("chapter") != tc.get("chapter_heading"):
            problems.append("chapter/chapter_heading parity broken")

    entry = manifest_entry(idx)
    if entry and entry.get("accuracy_source") == "canon-oracle":
        core_ok, core_bad, _deutero, unresolved = classify_books(idx)
        if core_bad:
            problems.append(f"canon chapter mismatches: {core_bad}")
        if core_ok and unresolved:
            problems.append(f"unresolved book labels (add alias?): {[u[1] for u in unresolved]}")

    if entry and entry.get("accuracy_source") == "catholic-oracle":
        ok, count_bad, align_bad = classify_books_catholic(idx)
        # Chapter mismatches known to originate in the source edition (recorded in the
        # manifest with provenance) are surfaced there, not gated — a specific, cited
        # exception, never a blanket pass. All others, and any order divergence, fail.
        allowed = {e.get("position") for e in (entry.get("canon_exceptions") or [])}
        undocumented = [r for r in count_bad if r[0] not in allowed]
        if align_bad:
            problems.append(f"catholic canon order/identity errors: {align_bad}")
        if undocumented:
            problems.append(f"catholic chapter mismatches: {undocumented}")
        if not ok:
            problems.append("no catholic-canon books resolved — is idx 108 map present?")

    if entry and entry.get("accuracy_source") == "quran-oracle":
        # The Qur'an is structurally flat (114 top-level sura sections, no book nesting),
        # so its external accuracy lens is a pure count against the fixed 114-sura canon
        # rather than the Bibles' positional book alignment (see quran_sura_count).
        got = quran_sura_count(idx)
        expected = load_canon()["quran_suras"]
        if got != expected:
            problems.append(f"Qur'an sura count {got} != canonical {expected}")

    return problems

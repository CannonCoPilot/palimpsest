"""Hermetic verification of ``sources.manifest.json`` — the Bible Gold-Set registry.

The manifest (``fixtures/gold/sources.manifest.json``, schema
``palimpsest.gold-sources/v1``) is three things at once: the **audit trail** (a
``source_sha256`` fingerprint of every source binary, so "preserve, don't push" is
provable without redistributing copyrighted epub/pdf/txt), the **corpus registry**
(the enumeration source for the CLI/API gold paths), and the Gold-Set **scorecard**
(the per-Bible ``validated:{cli,api,ui}`` block). It is produced by
``mask_engine/gen_sources_manifest.py`` from three inputs: the frozen maps, the
generator's curated ``PROVENANCE`` table, and the local (gitignored) source corpus.

This module is the CI-runnable guard. Two of the manifest's fields —
``source_present`` and ``source_sha256`` — depend on the local corpus, which CI does
not hold, so full byte-for-byte freshness (``gen_sources_manifest.py --check``) is a
*machine-local* concern verified at generation time (and by ``verify_sources.py``).
Everything else is derivable from committed files alone, and that is what we check:

- **registry completeness** — the manifest enumerates exactly the Bible program the
  generator knows about, and every artifact it points at exists;
- **structural reconcile** — each entry's ``structure``/``reference_sha256`` ties back
  to its map (catches a manifest that drifts from the masking contract it registers);
- **hermetic freshness** — re-running the *real* generator with an empty corpus
  reproduces the committed manifest in every field except the two corpus-only ones,
  proving the curated provenance and derived counts are not stale hand-edits.
"""
from __future__ import annotations

import copy
import importlib.util
import json
import re
from pathlib import Path

import pytest

_GOLD_DIR = Path(__file__).parent / "fixtures" / "gold"
_MANIFEST_PATH = _GOLD_DIR / "sources.manifest.json"
_GEN_PATH = _GOLD_DIR / "mask_engine" / "gen_sources_manifest.py"

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
# Fields whose value depends on the local (uncommitted) source corpus. Excluded from
# the hermetic freshness comparison because CI cannot reproduce them.
_CORPUS_ONLY_FIELDS = ("source_present", "source_sha256")
# The full Bible Gold Set this registry must enumerate (mirrors test_gold_maps'
# flagship guard + the two Catholic epubs + the bespoke DR-original).
_EXPECTED_BIBLE_IDXS = frozenset({5, 6, 100, 108, 201, 202, 203, *range(208, 220)})


def _load_generator():
    """Import gen_sources_manifest as a module without running its ``main``."""
    spec = importlib.util.spec_from_file_location("gen_sources_manifest", _GEN_PATH)
    assert spec and spec.loader, f"cannot load generator at {_GEN_PATH}"
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_MANIFEST = json.loads(_MANIFEST_PATH.read_text(encoding="utf-8"))
_ENTRIES = _MANIFEST["bibles"]
_ENTRY_IDS = [f"bible-{e['id']}" for e in _ENTRIES]


# ── manifest-level guards ─────────────────────────────────────────────────────

def test_manifest_schema_and_scope() -> None:
    assert _MANIFEST["schema"] == "palimpsest.gold-sources/v1"
    assert _MANIFEST["scope"] == "bibles"
    assert _MANIFEST["count"] == len(_ENTRIES)


def test_registry_completeness() -> None:
    """The manifest enumerates exactly the generator's Bible program — no more, no less."""
    gen = _load_generator()
    manifest_ids = {e["id"] for e in _ENTRIES}
    assert manifest_ids == set(gen.BIBLE_IDXS), (
        f"manifest/generator drift: only-manifest={manifest_ids - set(gen.BIBLE_IDXS)}, "
        f"only-generator={set(gen.BIBLE_IDXS) - manifest_ids}"
    )
    missing_flagship = sorted(_EXPECTED_BIBLE_IDXS - manifest_ids)
    assert not missing_flagship, f"registry missing flagship Bibles: {missing_flagship}"


@pytest.mark.parametrize("entry", _ENTRIES, ids=_ENTRY_IDS)
def test_gold_artifacts_exist(entry: dict) -> None:
    """Every artifact the registry points at is actually committed."""
    gold_map = _GOLD_DIR / entry["gold_map"]
    assert gold_map.is_file(), f"missing gold map: {entry['gold_map']}"
    if entry["annotation_gold"] is not None:
        ann = _GOLD_DIR / entry["annotation_gold"]
        assert ann.is_file(), f"missing annotation gold: {entry['annotation_gold']}"


# ── structural reconcile: manifest ↔ its map ──────────────────────────────────

@pytest.mark.parametrize("entry", _ENTRIES, ids=_ENTRY_IDS)
def test_entry_reconciles_with_map(entry: dict) -> None:
    """The registered structure/fingerprint match the masking contract it registers."""
    m = json.loads((_GOLD_DIR / entry["gold_map"]).read_text(encoding="utf-8"))
    tc = m.get("type_counts", {})
    assert entry["source_file"] == m.get("source_file"), "source_file disagrees with map"
    assert _SHA256_RE.match(entry["reference_sha256"] or ""), "reference_sha256 not 64-hex"
    assert entry["reference_sha256"] == m.get("reference_sha256"), "reference_sha256 drift"
    assert entry["structure"]["books"] == tc.get("book"), "book count drift"
    assert entry["structure"]["chapters"] == tc.get("chapter"), "chapter count drift"
    assert entry["structure"]["verses"] == m.get("verse_count"), "verse count drift"


# ── hermetic freshness (curated provenance + derived counts) ──────────────────

def _strip_corpus_fields(manifest: dict) -> dict:
    out = copy.deepcopy(manifest)
    for entry in out["bibles"]:
        for field in _CORPUS_ONLY_FIELDS:
            entry.pop(field, None)
    return out


def test_manifest_is_fresh_sans_corpus(tmp_path, monkeypatch) -> None:
    """Re-running the real generator (empty corpus) reproduces the committed manifest.

    Excludes only the two corpus-dependent fields, so a stale curated ``PROVENANCE``
    edit, a changed map count, or a hand-tweaked manifest all fail here — while the
    absence of the source binaries in CI does not. Full ``source_sha256`` freshness is
    a machine-local check (``gen_sources_manifest.py --check`` / ``verify_sources.py``).
    """
    gen = _load_generator()
    monkeypatch.setattr(gen, "IMPORTS", tmp_path / "no-corpus")
    regenerated = gen.build()
    assert _strip_corpus_fields(regenerated) == _strip_corpus_fields(_MANIFEST), (
        "sources.manifest.json is stale vs the generator — run gen_sources_manifest.py"
    )

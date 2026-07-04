"""Hermetic verification of ``sources.nonbible.manifest.json`` — the non-Bible Gold-Set
registry (the sibling of ``test_gold_sources.py``).

The Step-4b audit found that the 17 non-Bible gold maps clear every machine-checkable
structural gate yet were registered nowhere, so they were unreachable through the gold
paths (§6 operational-readiness FAIL). This registry + these guards close the data + CLI
half of that gap. Like the Bible manifest, the file is three things — audit trail
(``source_sha256`` fingerprint), registry (enumeration source for ``registry_entries`` and
the CLI ``gold list``/``gold verify``), and scorecard (``validated``) — and it is produced
by ``mask_engine/gen_nonbible_manifest.py``.

Two fields (``source_present``/``source_sha256``) depend on the gitignored ``imports/``
corpus, so full freshness is a machine-local concern; everything else is derivable from
committed files alone and is what these guards check — plus that every registered map
actually passes ``verify_map``, and that the Qur'an count-oracle wired into ``verify_map``
genuinely gates (it is not a vacuous pass).
"""
from __future__ import annotations

import copy
import importlib.util
import json
import re
from pathlib import Path

import pytest

from palimpsest.gold import load_nonbible_manifest, verify_map

_GOLD_DIR = Path(__file__).parent / "fixtures" / "gold"
_MANIFEST_PATH = _GOLD_DIR / "sources.nonbible.manifest.json"
_GEN_PATH = _GOLD_DIR / "mask_engine" / "gen_nonbible_manifest.py"

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
# Fields whose value depends on the local (uncommitted) source corpus — excluded from the
# hermetic freshness comparison because CI cannot reproduce them.
_CORPUS_ONLY_FIELDS = ("source_present", "source_sha256")
# The full non-Bible program (report-4b / NON-BIBLE-WORKLIST tables): 17 works.
_EXPECTED_NONBIBLE_IDXS = frozenset({18, 19, 29, 42, 48, 56, 64, 70, 71, 80,
                                     101, 102, 103, 104, 105, 106, 107})
# Works with an external accuracy oracle vs. structural-only gates (the §2/§3 gap).
_QURAN_IDXS = frozenset({29, 107})
_LONE_OF_KIND_IDXS = frozenset({18, 101})  # §3 min-of-two flag → candidate, not standard


def _load_generator():
    spec = importlib.util.spec_from_file_location("gen_nonbible_manifest", _GEN_PATH)
    assert spec and spec.loader, f"cannot load generator at {_GEN_PATH}"
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_MANIFEST = json.loads(_MANIFEST_PATH.read_text(encoding="utf-8"))
_ENTRIES = _MANIFEST["works"]
_ENTRY_IDS = [f"work-{e['id']}" for e in _ENTRIES]


# ── manifest-level guards ─────────────────────────────────────────────────────

def test_manifest_schema_and_scope() -> None:
    assert _MANIFEST["schema"] == "palimpsest.gold-sources/v1"
    assert _MANIFEST["scope"] == "non-bibles"
    assert _MANIFEST["count"] == len(_ENTRIES)


def test_registry_completeness() -> None:
    """The manifest enumerates exactly the generator's non-Bible program — no more, no less."""
    gen = _load_generator()
    manifest_ids = {e["id"] for e in _ENTRIES}
    assert manifest_ids == set(gen.NON_BIBLE_IDXS), (
        f"manifest/generator drift: only-manifest={manifest_ids - set(gen.NON_BIBLE_IDXS)}, "
        f"only-generator={set(gen.NON_BIBLE_IDXS) - manifest_ids}"
    )
    assert manifest_ids == _EXPECTED_NONBIBLE_IDXS, "registry drifted from the 17-work audit program"


def test_loader_matches_file() -> None:
    """The gold.load_nonbible_manifest accessor returns the committed registry."""
    assert load_nonbible_manifest() == _MANIFEST


# ── scorecard honesty (standard §3: soundness ≠ correctness) ──────────────────

@pytest.mark.parametrize("entry", _ENTRIES, ids=_ENTRY_IDS)
def test_scorecard_is_honest(entry: dict) -> None:
    """Only the CLI path is claimed validated here; api/ui/apply are deferred, not faked."""
    v = entry["validated"]
    assert v == {"cli": True, "api": False, "ui": False}, (
        "non-Bible readiness is CLI-only in this environment; api/ui must not be claimed"
    )
    # Qur'an works carry the external count-oracle; every other kind is honestly structural.
    expect = "quran-oracle" if entry["id"] in _QURAN_IDXS else "map-gates"
    assert entry["accuracy_source"] == expect
    # §3 min-of-two: the two lone-of-kind works are candidates, never "standard".
    expect_cohort = "candidate" if entry["id"] in _LONE_OF_KIND_IDXS else "standard"
    assert entry["cohort_status"] == expect_cohort


# ── artifacts + structural reconcile: manifest ↔ its map ──────────────────────

@pytest.mark.parametrize("entry", _ENTRIES, ids=_ENTRY_IDS)
def test_gold_artifacts_exist(entry: dict) -> None:
    gold_map = _GOLD_DIR / entry["gold_map"]
    assert gold_map.is_file(), f"missing gold map: {entry['gold_map']}"
    if entry["annotation_gold"] is not None:
        ann = _GOLD_DIR / entry["annotation_gold"]
        assert ann.is_file(), f"missing annotation gold: {entry['annotation_gold']}"


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
    assert entry["structure"]["elements"] == m.get("element_count"), "element count drift"


# ── operational: every registered map verifies (the §6 CLI-path evidence) ─────

@pytest.mark.parametrize("entry", _ENTRIES, ids=_ENTRY_IDS)
def test_registered_map_verifies(entry: dict) -> None:
    """Every non-Bible in the registry passes verify_map — the CLI ``gold verify`` gate."""
    problems = verify_map(entry["id"])
    assert problems == [], f"work-{entry['id']:03d} failed verification: {problems}"


# ── the Qur'an count-oracle wired into verify_map is a REAL gate, not vacuous ──

@pytest.mark.parametrize("idx", sorted(_QURAN_IDXS))
def test_quran_oracle_gates(idx: int, monkeypatch) -> None:
    """A wrong sura count makes verify_map fail — proving the oracle branch actually gates."""
    # Clean today.
    assert verify_map(idx) == []
    # Force a wrong count; verify_map must now surface a Qur'an-count problem.
    monkeypatch.setattr("palimpsest.gold.quran_sura_count", lambda _idx: 113)
    problems = verify_map(idx)
    assert any("Qur'an sura count" in p for p in problems), (
        f"quran-oracle did not gate work-{idx:03d}: {problems}"
    )


# ── hermetic freshness (curated provenance + derived counts) ──────────────────

def _strip_corpus_fields(manifest: dict) -> dict:
    out = copy.deepcopy(manifest)
    for entry in out["works"]:
        for field in _CORPUS_ONLY_FIELDS:
            entry.pop(field, None)
    return out


def test_manifest_is_fresh_sans_corpus(tmp_path, monkeypatch) -> None:
    """Re-running the real generator (empty corpus) reproduces the committed manifest.

    Excludes only the two corpus-dependent fields, so a stale curated
    ``NON_BIBLE_PROVENANCE`` edit, a changed map count, or a hand-tweaked manifest all fail
    here — while the absence of the source binaries in CI does not.
    """
    gen = _load_generator()
    monkeypatch.setattr(gen, "IMPORTS", tmp_path / "no-corpus")
    regenerated = gen.build()
    assert _strip_corpus_fields(regenerated) == _strip_corpus_fields(_MANIFEST), (
        "sources.nonbible.manifest.json is stale vs the generator — run gen_nonbible_manifest.py"
    )

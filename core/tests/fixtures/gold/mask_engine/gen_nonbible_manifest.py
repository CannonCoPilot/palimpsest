#!/usr/bin/env python
"""Generate ``sources.nonbible.manifest.json`` — the non-Bible Gold-Set registry.

Sibling of ``gen_sources_manifest.py`` (the Bible registry). It exists because the Bible
manifest is, by its own ``scope``, bibles-only; the Step-4b non-Bible standards audit
(``core/.scratch/gold-audit/reaudit-4b/report-4b.md``) found that the 17 non-Bible gold
maps clear every machine-checkable structural gate yet are registered *nowhere*, so they
are unreachable through the CLI/API/UI gold paths (§6 operational-readiness FAIL). This
registry closes the data + CLI half of that gap: it enumerates the 17 works so
``manifest_entry``/``gold list``/``gold verify`` cover them.

Honesty of the scorecard (standard §3: soundness ≠ correctness):
  * ``validated`` is ``{cli: true, api: false, ui: false}`` for every entry — CLI
    enumeration/verification is wired and tested here; the API/UI gold paths and
    ``apply`` (which needs the gitignored source binary) are NOT verified in this
    environment, so claiming them would fabricate the scorecard. They are deferred to a
    machine holding ``imports/`` and a running server.
  * ``accuracy_source`` is ``quran-oracle`` only for the two Qur'an works (29, 107), which
    carry an external count-oracle (114 suras, gated in ``verify_map``); every other kind
    has no external accuracy lens yet, so it is honestly ``map-gates`` (structural gates
    only — the audit's §2/§3 accuracy GAP, not a solved problem).
  * ``cohort_status`` records the §3 min-of-two verdict: ``candidate`` for the two
    lone-of-kind works (18 patristics, 101 LDS), ``standard`` for the rest.

Derived facts (source_file, source_sha256, reference_sha256, structure counts) come from
the maps + local corpus; curated facts live in ``NON_BIBLE_PROVENANCE`` below. Curation is
conservative: ``author``/``year`` are filled only where the audit report or an
uncontested first-publication fact establishes them, and are ``null`` otherwise rather
than guessed.

Usage:
  gen_nonbible_manifest.py            # regenerate ../sources.nonbible.manifest.json
  gen_nonbible_manifest.py --check    # verify the committed manifest is up to date (CI)
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
GOLD = HERE.parent  # core/tests/fixtures/gold
MAPS = GOLD / "maps"
REPO = HERE.parents[4]
IMPORTS = REPO / "imports"
OUT = GOLD / "sources.nonbible.manifest.json"

# Curated editorial metadata, keyed by gold idx. Everything else is derived from the map.
#   kind:            genre cohort (audit report-4b / NON-BIBLE-WORKLIST tables)
#   cohort_status:   §3 min-of-two verdict — standard | candidate (lone-of-kind)
#   accuracy_source: quran-oracle (external count) | map-gates (structural only, no oracle)
#   author/year:     filled only when the audit report or an uncontested publication fact
#                    establishes them; null otherwise (no fabrication).
NON_BIBLE_PROVENANCE: dict[int, dict] = {
    18:  {"title": "Ante-Nicene Fathers, Vol. 3", "author": None, "year": None,
          "kind": "patristics", "cohort_status": "candidate", "accuracy_source": "map-gates",
          "note": "Lone-of-kind (§3): needs a 2nd patristics work or reclassification."},
    19:  {"title": "The Correspondent", "author": "Evans", "year": 2025,
          "kind": "novel", "cohort_status": "standard", "accuracy_source": "map-gates",
          "note": "Epistolary sub-kind of novel."},
    29:  {"title": "The Message of the Qur'an", "author": "Muhammad Asad", "year": None,
          "kind": "quran", "cohort_status": "standard", "accuracy_source": "quran-oracle"},
    42:  {"title": "Old Testament Pseudepigrapha, Vol. 1", "author": None, "year": None,
          "kind": "pseudepigrapha", "cohort_status": "standard", "accuracy_source": "map-gates"},
    48:  {"title": "New Testament Apocrypha", "author": None, "year": None,
          "kind": "apocrypha", "cohort_status": "standard", "accuracy_source": "map-gates"},
    56:  {"title": "The Last of the Mohicans", "author": "James Fenimore Cooper", "year": 1826,
          "kind": "novel", "cohort_status": "standard", "accuracy_source": "map-gates"},
    64:  {"title": "The Books of Enoch", "author": None, "year": None,
          "kind": "pseudepigrapha", "cohort_status": "standard", "accuracy_source": "map-gates",
          "note": "Enoch family (1/2/3 Enoch); chapter:230 has no single authoritative count."},
    70:  {"title": "Charlotte Temple", "author": "Susanna Rowson", "year": 1791,
          "kind": "novel", "cohort_status": "standard", "accuracy_source": "map-gates"},
    71:  {"title": "The Strange Case of Dr Jekyll and Mr Hyde", "author": "Robert Louis Stevenson",
          "year": 1886, "kind": "novel", "cohort_status": "standard", "accuracy_source": "map-gates"},
    80:  {"title": "The Dead Sea Scrolls Translated", "author": None, "year": None,
          "kind": "dss", "cohort_status": "standard", "accuracy_source": "map-gates"},
    101: {"title": "LDS Scripture (Book of Mormon, Doctrine & Covenants, Pearl of Great Price)",
          "author": None, "year": None, "kind": "lds", "cohort_status": "candidate",
          "accuracy_source": "map-gates", "cli_apply": False,
          "note": "Lone-of-kind (§3): needs a 2nd LDS work or reclassification. Apply "
                  "BLOCKED: gold apply fails a reference_sha256 mismatch (map d862fc92c1d3 vs "
                  "current re-ingest 47c3624db060), so the map's offsets no longer align with "
                  "the local source under the current pipeline — the map is stale or the local "
                  "source diverged. The other 3 PDFs (105/106/107) verify clean, so the pipeline "
                  "is sound; this is specific to idx 101 and needs map regeneration or source "
                  "reconciliation (a gold-contract change). validated.cli is false accordingly."},
    102: {"title": "The Collected Poems of Emily Dickinson", "author": "Emily Dickinson", "year": None,
          "kind": "poetry", "cohort_status": "standard", "accuracy_source": "map-gates"},
    103: {"title": "The Road Not Taken and Other Poems", "author": "Robert Frost", "year": None,
          "kind": "poetry", "cohort_status": "standard", "accuracy_source": "map-gates"},
    104: {"title": "is 5", "author": "E. E. Cummings", "year": 1926,
          "kind": "poetry", "cohort_status": "standard", "accuracy_source": "map-gates"},
    105: {"title": "The Dead Sea Scrolls Reader, Vol. 1", "author": None, "year": None,
          "kind": "dss", "cohort_status": "standard", "accuracy_source": "map-gates"},
    106: {"title": "Adam and Eve in the Armenian Tradition", "author": None, "year": None,
          "kind": "pseudepigrapha", "cohort_status": "standard", "accuracy_source": "map-gates",
          "note": "Armenian pseudepigrapha; parity-OK only under the pseudepigrapha family (§3)."},
    107: {"title": "The Holy Qur'an (Arabic + English)", "author": None, "year": None,
          "kind": "quran", "cohort_status": "standard", "accuracy_source": "quran-oracle"},
}

NON_BIBLE_IDXS = sorted(NON_BIBLE_PROVENANCE)

_ORIGIN_BY_SUFFIX = {"epub": "published-epub", "pdf": "published-pdf", "txt": "reconstructed-text"}


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def _local_index() -> dict[str, Path]:
    idx: dict[str, Path] = {}
    if IMPORTS.is_dir():
        for p in IMPORTS.rglob("*"):
            if p.is_file():
                idx.setdefault(p.name, p)
    return idx


def build() -> dict:
    local = _local_index()
    entries = []
    for idx in NON_BIBLE_IDXS:
        mp = MAPS / f"work-{idx:03d}.map.json"
        m = json.loads(mp.read_text(encoding="utf-8"))
        src_name = m.get("source_file", "")
        src_path = local.get(src_name)
        suffix = Path(src_name).suffix.lstrip(".").lower() or "unknown"
        tc = m.get("type_counts", {})
        prov = NON_BIBLE_PROVENANCE[idx]
        ann = GOLD / f"work-{idx}.json"
        entries.append({
            "id": idx,
            "title": prov["title"],
            "author": prov["author"],
            "year": prov["year"],
            "kind": prov["kind"],
            "cohort_status": prov["cohort_status"],
            "source_origin": _ORIGIN_BY_SUFFIX.get(suffix, "published-source"),
            "source_file": src_name,
            "source_file_type": suffix,
            "source_present": src_path is not None,
            "source_sha256": _sha256(src_path) if src_path else None,
            "reference_sha256": m.get("reference_sha256"),
            "structure": {
                "books": tc.get("book"),
                "chapters": tc.get("chapter"),
                "elements": m.get("element_count"),
            },
            "gold_map": f"maps/work-{idx:03d}.map.json",
            "annotation_gold": f"work-{idx}.json" if ann.exists() else None,
            "accuracy_source": prov["accuracy_source"],
            # Operational-readiness scorecard, honest to this environment. cli is true where
            # the CLI gold path is confirmed end-to-end — list/verify plus a live `gold apply`
            # that passed the reference_sha256 tie (sha_verified=True); it is false for a work
            # whose apply fails (``cli_apply``). api/ui remain false: those paths need a running
            # server + the browser, not exercised here. (Sources ARE present locally, so apply
            # was live-verifiable — 16/17 pass; see the manifest note.)
            "validated": {"cli": prov.get("cli_apply", True), "api": False, "ui": False},
            **({"note": prov["note"]} if "note" in prov else {}),
        })
    return {
        "schema": "palimpsest.gold-sources/v1",
        "scope": "non-bibles",
        "note": "Registry + scorecard for the 17 non-Bible gold works (Step-4b audit). Sibling "
                "of sources.manifest.json (bibles). Source binaries are NOT distributed "
                "(imports/ is gitignored); source_sha256 is the fingerprint. The local corpus "
                "holds all 17 sources, so the CLI gold path was live-verified: `gold apply` "
                "passed the reference_sha256 tie (sha_verified=True) for 16/17 — idx 101 (LDS) "
                "fails a sha mismatch (see its note) and is marked validated.cli=false. api/ui "
                "stay false (need a running server + browser). accuracy_source is quran-oracle "
                "for the count-gated Qur'an works, map-gates (structural only) elsewhere — the "
                "§2/§3 per-kind accuracy lens is still an open gap. Regenerate with "
                "mask_engine/gen_nonbible_manifest.py.",
        "count": len(entries),
        "works": entries,
    }


def main() -> int:
    manifest = build()
    text = json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"
    if "--check" in sys.argv:
        current = OUT.read_text(encoding="utf-8") if OUT.exists() else ""
        if current != text:
            print("sources.nonbible.manifest.json is STALE — run gen_nonbible_manifest.py", file=sys.stderr)
            return 1
        print("sources.nonbible.manifest.json up to date")
        return 0
    OUT.write_text(text, encoding="utf-8")
    present = sum(1 for w in manifest["works"] if w["source_present"])
    print(f"wrote {OUT.name}: {manifest['count']} works, {present} with local source binaries")
    return 0


if __name__ == "__main__":
    sys.exit(main())

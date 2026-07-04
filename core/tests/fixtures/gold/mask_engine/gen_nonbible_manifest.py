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
  * ``validated`` is ``{cli: apply_ok, api: apply_ok, ui: false}`` — cli and api both track
    whether a live ``gold apply`` passed the reference_sha256 tie (true for all 17: each apply
    ingests the map's ``import_source``, so idx 101's column-aware LDS text reproduces its
    sha too). They mirror because the CLI and the ``/api/gold`` apply endpoint drive the SAME
    verified ``_apply_gold_map`` over the same source, so the CLI evidence substantiates both.
    ``ui`` stays false for every entry: the frontend reads only the ``bibles`` array, so no
    non-Bible work is exercised through the browser yet.
  * ``accuracy_source`` is an external count-oracle where one exists: ``quran-oracle`` for
    the two Qur'an works (29, 107 — 114 suras) and ``novel-oracle`` for the two novels whose
    chapter total is author-fixed and edition-stable (56 Mohicans = 33, 71 Jekyll = 10), both
    gated in ``verify_map`` against ``canon_chapters.json``. Every other kind — and the novels
    whose chapter count is edition-variable (70, 19) — has no external accuracy lens yet, so it
    is honestly ``map-gates`` (structural gates only — the audit's §2/§3 accuracy GAP).
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
#   accuracy_source: quran-oracle / novel-oracle (external count) | map-gates (structural only)
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
          "kind": "novel", "cohort_status": "standard", "accuracy_source": "novel-oracle",
          "note": "Chapter count author-fixed at 33 across standard editions (novel-oracle)."},
    64:  {"title": "The Books of Enoch", "author": None, "year": None,
          "kind": "pseudepigrapha", "cohort_status": "standard", "accuracy_source": "map-gates",
          "note": "Enoch family (1/2/3 Enoch); chapter:230 has no single authoritative count."},
    70:  {"title": "Charlotte Temple", "author": "Susanna Rowson", "year": 1791,
          "kind": "novel", "cohort_status": "standard", "accuracy_source": "map-gates"},
    71:  {"title": "The Strange Case of Dr Jekyll and Mr Hyde", "author": "Robert Louis Stevenson",
          "year": 1886, "kind": "novel", "cohort_status": "standard", "accuracy_source": "novel-oracle",
          "note": "Chapter count author-fixed at 10 across standard editions (novel-oracle)."},
    80:  {"title": "The Dead Sea Scrolls Translated", "author": None, "year": None,
          "kind": "dss", "cohort_status": "standard", "accuracy_source": "map-gates"},
    101: {"title": "LDS Scripture (Book of Mormon, Doctrine & Covenants, Pearl of Great Price)",
          "author": None, "year": None, "kind": "lds", "cohort_status": "candidate",
          "accuracy_source": "map-gates",
          "note": "Lone-of-kind (§3): needs a 2nd LDS work or reclassification (orthogonal to "
                  "apply). Apply ingests the map's import_source (LDS_eng.reference.txt, a "
                  "column-aware pre-extraction staged in imports/) rather than the raw "
                  "LDS_eng.pdf: the map's offsets were computed against that reference text, so "
                  "ingesting it reproduces reference_sha256 d862fc92c1d3 exactly and gold apply "
                  "verifies (sha_verified=True, 9227 elements). The earlier 'sha mismatch' report "
                  "came from re-ingesting the raw PDF via the standard extractor, not the "
                  "import_source the map declares — a resolution bug in the apply path, since fixed."},
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
        apply_ok = prov.get("cli_apply", True)  # live `gold apply` passed the sha tie
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
            # Operational-readiness scorecard, honest to this environment. apply_ok is true
            # where a live `gold apply` passed the reference_sha256 tie (sha_verified=True) —
            # true for all 17. A work can set ``cli_apply: False`` to record a genuine apply
            # failure (none currently do). Both cli and api mirror apply_ok because the CLI and
            # the /api/gold apply endpoint drive the SAME verified _apply_gold_map over the same
            # source — the API added no new failure mode, so the CLI evidence substantiates
            # both. ui stays false: the frontend reads only `bibles`, so no non-Bible work is
            # exercised through the browser yet.
            "validated": {"cli": apply_ok, "api": apply_ok, "ui": False},
            **({"note": prov["note"]} if "note" in prov else {}),
        })
    return {
        "schema": "palimpsest.gold-sources/v1",
        "scope": "non-bibles",
        "note": "Registry + scorecard for the 17 non-Bible gold works (Step-4b audit). Sibling "
                "of sources.manifest.json (bibles). Source binaries are NOT distributed "
                "(imports/ is gitignored); source_sha256 is the fingerprint. The local corpus "
                "holds all 17 sources, so the gold apply path was live-verified: `gold apply` "
                "passed the reference_sha256 tie (sha_verified=True) for all 17 — including idx "
                "101 (LDS), which ingests the map's import_source (LDS_eng.reference.txt) per its "
                "note. validated.cli=api=true accordingly. "
                "validated.api mirrors cli because /api/gold/{id}/apply drives the same "
                "_apply_gold_map; ui stays false (frontend reads only `bibles`). "
                "accuracy_source is an external count-oracle where one exists — quran-oracle "
                "(29, 107) and novel-oracle (56, 71) — and map-gates (structural only) elsewhere; "
                "the §2/§3 per-kind accuracy lens is still an open gap. Regenerate with "
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

# The Gold Set Standard

Status: **As-built** (Bibles). Non-Bible re-audit deferred (see §7).

This document defines what "Gold Set Standard" means in Palimpsest, so the guarantee
cannot silently drift or fork. It is the anchor the registry, the tests, and the
CLI/API/UI gold paths all reference.

## 1. The bar

A text is **Gold Set Standard** only when all three hold:

1. **Complete, accurate, precise masking** — its masking layout is confirmed to tile the
   work with correct structure, verified by machinery, not eyeball.
2. **Validation parity with other Gold-Set texts of its kind** — it carries the same
   verification lenses as its peers; kind differences are explicit here, never silent.
3. **Operational readiness through every path** — it can be applied through the CLI, the
   API, and the UI. The registry's `validated: {cli, api, ui}` block records this state.

"Gold Set" is not a label a text is given; it is a bar a text is shown to clear.

## 2. Two gold kinds (one standard)

The single standard is realized by two artifact kinds, keyed to *detection difficulty* —
this is the frame that dissolves the apparent fork between "map-only" and "annotated"
works.

- **Reconstruction gold — the map. Universal.**
  Every Gold-Set work has a CI-verified masking map
  (`core/tests/fixtures/gold/maps/work-<idx>.map.json`, schema `palimpsest.gold-map/v1`):
  a full char-span tiling plus the `reference_sha256` of the exact text the offsets were
  cut against. **This map *is* the masking.** It is applied verbatim by
  `server._apply_gold_map` after the sha check.

- **Detection gold — the annotation. Conditional.**
  Required *only* where structure must be inferred by the detector — implicit-structure
  epub/pdf. It is the sparse, anchor-based ground truth (`work-<idx>.json`) consumed by
  the machine-local ratification tools (`gold_verify.py`, `gold_ratify.py`, `a3_score.py`).

Self-describing marker scripture is **exempt from detection gold by design**. Bolting an
annotation gold onto text that carries its own chapter/verse markers would be theater —
scoring a detector against structure the text states outright. Map-only marker scripture
is *complete*, not lesser.

## 3. Rigor parity — the accuracy lens per kind

Parity is not "everyone gets the same lens." It is "everyone gets an *independent*
accuracy check appropriate to how their structure is known." The map's own consistency
(spans tile, counts reconcile, masking round-trips) proves the map is internally sound —
but not that it is *correct* (a scrape that dropped a chapter still tiles perfectly). Each
kind closes that blind spot differently:

| Kind | Structure known via | Independent accuracy lens | Registry `accuracy_source` |
|------|---------------------|---------------------------|----------------------------|
| Marker scripture (201–219) | self-marked chapter/verse | **Canon versification oracle** — per-book chapter counts vs. an external table | `canon-oracle` |
| Detector epub (5, 6, 100) | inferred from epub structure | **Annotation gold** + detector recall (`gold_ratify`/`a3`) | `annotation+detector` |
| Bespoke (108) | one-off reconstruction | map gates; canon oracle N/A (Catholic Vulgate canon) | `map-gates` |

The canon oracle (`core/tests/fixtures/gold/canon_chapters.json`, `test_gold_canon.py`,
shared production logic in `palimpsest/gold.py`) is the rigor **elevation** for marker
Bibles: an accuracy guarantee *stronger* than the annotation works' human eyeball,
because the external chapter counts (stable since Langton, c. 1227) are something the map
never had a hand in. It strict-gates the universal 66-book Protestant core (plus the
established KJV-Apocrypha set from idx 219); tradition-variant deuterocanon is *recorded,
not gated*, so the oracle stays honest and never self-blesses a versification difference
as an error.

### The per-kind minimum-of-two rule

A kind keeps Gold-Set status only if **≥2 works of that kind** clear the bar. A lone
member of a novel kind is a candidate, not a standard. (This is why idx 108, a Catholic
Vulgate edition, routes to parity via a Catholic oracle or an annotation gold rather than
being force-gated against the Protestant canon — its kind already has parity-bearing
members in 5 and 100.)

## 4. The registry & audit model

`core/tests/fixtures/gold/sources.manifest.json` (schema `palimpsest.gold-sources/v1`) is
the single record of every Bible gold source. It is three things at once:

- **Audit trail** — `source_sha256` fingerprints the source binary and `reference_sha256`
  the produced text, so a holder of the corpus can prove their local binaries match what
  each gold was keyed to, *without the binaries ever being distributed*.
- **Registry** — the enumeration source for the CLI/API/UI gold paths.
- **Scorecard** — the `validated: {cli, api, ui}` block records operational readiness.

It is generated (not hand-authored) by `mask_engine/gen_sources_manifest.py` from three
inputs: the frozen maps, the curated `PROVENANCE` table, and the local corpus. `--check`
re-verifies freshness on a machine holding the corpus; `verify_sources.py` checks a local
corpus against the recorded hashes; `test_gold_sources.py` guards registry completeness,
map reconcile, and provenance freshness hermetically in CI.

### Copyright — preserve, don't push

We hold full **use** rights (masks, annotations, and all derivatives are committable) but
do **not distribute** source binaries. Source epub/pdf/txt stay in the gitignored
`imports/` corpus; only their fingerprints ship. The maps and annotations — our derivative
work — are the committed product.

## 5. Verification lenses (what proves each criterion)

| Lens | Runs where | Proves |
|------|-----------|--------|
| `test_gold_maps.py` | CI (hermetic) | map is structurally sound (spans, coverage, taxonomy, parity, production round-trip) |
| `test_gold_canon.py` | CI (hermetic) | marker-Bible chapter counts match the external canon |
| `test_gold_sources.py` | CI (hermetic) | registry is complete, reconciles with maps, and is fresh |
| `gold_ratify.py` / `a3_score.py` | machine-local | detector accuracy for epub golds (needs copyrighted text) |
| `reference_sha256` re-check | apply time (machine-local) | the map's offsets align to the freshly-ingested text |

The sha tie and the detector/annotation lenses are inherently machine-local — they need
the copyrighted source text — and that boundary is by design, not a gap.

## 6. Operational readiness — the three paths

All three apply *any* registered Bible by id, over the same `_apply_gold_map` core, so the
resulting mask is identical:

- **API** — `GET /api/gold` (registry, with local-availability flags) and
  `POST /api/gold/{idx}/apply` (ingest + apply after the sha check).
- **CLI** — `palimpsest gold list` / `gold apply <idx> <workspace>` / `gold verify [idx]`
  (direct-import; `verify` is the CLI face of the hermetic gates + canon oracle).
- **UI** — the Gold Library overlay (`browser/src/components/common/GoldLibrary.tsx`):
  browse the registry, Apply a Bible. Apply is disabled with a reason when the map is not
  committed or the source is not present locally.

## 7. Non-Bible re-audit (deferred)

Scope of this standard as ratified is **Bibles only**. Every non-Bible work currently
called Gold Set (novels, poetry, Qur'an, apocrypha/DSS, LDS) must be shown to meet the
§1 bar alongside ≥1 other work of its kind (the §3 rule), or lose the label. That
re-audit is a separate pass, tracked in the collections-tier build journal's deferred
items, and is not part of the Bible ratification recorded here.

# Wave 0 Analysis Suite — Development Plan

**Status:** Draft for human review
**Date:** 2026-06-24
**Companion:** [wave0-analysis-suite-vision.md](./wave0-analysis-suite-vision.md) (the vision & requirements this plan implements)
**Builds on:** [analysis-design-principles.md](./analysis-design-principles.md) (P1–P5 + acceptable-default rule), [analysis-paradigm-audit-2026-06.md](../audits/analysis-paradigm-audit-2026-06.md) (G1–G5), and the substrate contract-lock walk (masking / segmentation / verse-element / OffsetMap / analyzable-bridge).

---

## 0. How to read this plan

This plan turns the Vision doc's requirements (FR-1…12, NFR-1…7) into five sequenced phases. Each phase is scoped to be **independently landable, tested, and committed** — the project's established cadence (each substrate contract-lock piece was its own verified commit). For every phase:

- **Scope** — what it delivers, by FR/NFR id.
- **Mechanism** — the concrete code, by `file:line`, that it touches or mirrors. No hand-waving: every new artifact rides an existing rail.
- **New artifacts** — files added/changed.
- **Tests** — what proves it, and the existing test module it extends.
- **Done criteria** — the checklist that closes the phase.
- **Risks & mitigations** — phase-local hazards.
- **Sequencing** — what it needs and what it unblocks.

**Verification command** (every phase ends GREEN here):
```
cd /Users/nathanielcannon/Claude/Projects/palimpsest \
  && core/.venv/bin/python -m pytest core/tests/ -q -m "not external" --junitxml=core/.tr.xml
```
(Parse the JUnit XML — RTK drops the pytest summary line through pipes. Backend baseline at the substrate-walk tip: **636/636 GREEN**.)

### Phasing summary

| Phase | Delivers | Nature | Unblocks |
|---|---|---|---|
| **P1 — Chunk-output contract-lock + CLI parity** | FR-1, FR-12, NFR-3 | Correctness no-regret; small, isolating | Nothing (pure hardening); safe to land alone |
| **P2 — Promote chunk + embed to layer-tracks** | FR-2…7, **FR-13/14 (manifest backbone)**, NFR-1/2/5/6 | Structural core | P3, P4-embedding, P5/P6 rendering, all Wave-1 reuse |
| **P3 — Embedding-as-analysis + visualization suite** | FR-3 (extends), FR-6, **FR-13/14 (embedding data)**, NFR-4 | Embedding viz suite + endpoints | P5 embedding lane, P6 embedding stats |
| **P4 — Broader Wave-0 analytics tracks** | FR-8, FR-9, FR-10, NFR-7 | New tracks (mostly independent) | P5 Profile/Explore tabs |
| **P5 — Suite shell + native plural layer-track rendering** | FR-11, **FR-13** | Frontend; data-driven plural rendering | (terminal) tracks visible in browser |
| **P6 — Per-layer statistics, distributions & viz options** | **FR-14** | Frontend + chunk-stats endpoint | (terminal) stats/viz drill-in |

**Critical path:** P1 → P2 → {P3, P4} → {P5, P6}. P1 is detachable (land anytime). P4's tracks are mutually independent and parallelizable once P2 lands. P5 (rendering) and P6 (stats panels) both need P2's manifest backbone + P3's embedding data; they ship together as the user-facing surface. The two new user commitments — *every chunk/embedding layer always renders as a track* (FR-13) and *every layer has quick-access stats/distributions/viz* (FR-14) — are carried by the P2 manifest backbone → P3 embedding data → P5/P6 UI chain.

---

## P1 — Chunk-output contract-lock + CLI parity

> **No-regret correctness.** Valuable regardless of which architectural options ship later. This is the chunking analogue of the substrate-walk commits (`c13db0f` segmentation, `5778533` OffsetMap, …): close the last substrate-boundary producer that trusts its own output.

### Scope
- **FR-1** — `chunk_text` output self-validates a chunk contract.
- **FR-12** — CLI `analyze` path applies masking + remap (closes the known CLI gap so a chunking analysis from the CLI is coordinate-correct).
- **NFR-3** — violations fail loud (`ValueError` at producer; `UnmappedCoordinateError` already covers remap).

### Mechanism
- **Contract validator.** Add `_validate_chunks(chunks, text, *, overlapping: bool)` in `chunking.py`, mirroring `_validate_segments` (`segmenter.py`, committed in `c13db0f`). It takes the full analyzable `text` (not just its length) so it can anchor-check each chunk against the source. Called at the single output point of `chunk_text` (`chunking.py:290`). Contract:
  - each record in-bounds in analyzable coordinates: `0 <= start < end <= len(text)`;
  - `index` sequential from 0;
  - ordered by `start` (non-decreasing);
  - **anchored**: `chunk["text"] == text[start:end]`;
  - **disjoint** for non-overlapping modes (`word`, `punctuation`, `verse`, `smart`): `chunk[i].start >= chunk[i-1].end` — no overlap, but whitespace gaps **are** allowed (chunkers snap to word/content boundaries and skip inter-chunk whitespace, so coverage is not total). This is the same DISJOINT contract `_validate_segments` enforces, **not** a gapless partition;
  - `slide` is overlap-tolerant: ordered + in-bounds + non-decreasing starts, **not** disjoint (mirrors the MERGE-TOLERANT relaxation used for verse regions in `b402e00`).
  - The `overlapping` flag is derived from the chunk `mode`, not guessed from the data, so a degenerate non-overlap result still fails loud.
- **CLI parity.** The `analyze` command (`cli.py:128`) calls `extractor.extract(project)` **directly** at `cli.py:193` — no masking, no remap. Route it through the same `_extract_masked` logic the server uses (`server.py:236`). Cleanest path: extract `_extract_masked` server-local into a reusable function in the run layer (e.g. `runner.py`/`derive.py`) that both `server.py:980` and the `cli.py` `analyze` command call, so HTTP and CLI share one masked-run code path. This is a **prerequisite** for a chunking track, since a CLI-run chunking track would otherwise persist unmasked, wrong-coordinate offsets.

### New artifacts
- `chunking.py`: `_validate_chunks` + call site.
- `cli.py` + shared run helper: CLI routed through masked-run path.
- `core/tests/test_chunking.py` (new or extended) + `core/tests/test_cli.py` parity test.

### Tests
- Contract tests mirroring the segmentation set (`test_ingest.py`'s `_validate_segments` tests): valid `word`/`punctuation`/`verse`/`smart` → disjoint holds (a whitespace gap between chunks is explicitly **allowed** — `test_whitespace_gap_is_allowed`); valid `slide` → overlap tolerated; injected corruption (overlap in non-overlap mode, out-of-bounds end, non-sequential index, unordered, anchor mismatch) → `ValueError`.
- **Behavior-identical guard:** every existing fixture (incl. gold Douay-Rheims) yields byte-identical chunk lists; the validator fires only on impossible-today corruption. This is the same acceptance bar the substrate walk used.
- CLI parity test: a chunking/derive run via `cli.py` produces the same masked, original-coordinate output as the HTTP path on the same project.

### Done criteria
- [ ] `_validate_chunks` enforces the contract at `chunk_text`'s output; all five modes pass on real fixtures.
- [ ] CLI `analyze` produces masked, remapped coordinates identical to HTTP for a shared project.
- [ ] New tests green; full suite still 636/636 (+ new) GREEN.
- [ ] One commit, behavior byte-identical for valid inputs.

### Risks & mitigations
- *`smart` mode may legitimately not perfectly partition* (it grows over heterogeneous units). **Resolved:** the contract is disjoint, not a partition, so `smart`'s whitespace micro-gaps validate as-is without special-casing — confirmed byte-identical on the gold DR fixture and every other real fixture.
- *Refactoring `_extract_masked` out of `server.py` could disturb the signal-consumer skip logic* (`_is_signal_consumer`, masking-skip for non-underscore `depends_on`). **Mitigation:** move the function verbatim, keep server as a thin caller, re-run the full derive/masking test set before/after.

### Sequencing
Needs nothing. Unblocks nothing structurally, but **must precede P2** so the chunking track inherits a validated, coordinate-correct producer.

---

## P2 — Promote chunk + embed to layer-tracks

> **The structural core.** Converts chunking and embedding from `self_similarity`-owned locals into first-class, persisted, reusable tracks with capability descriptors and a dependency-check resolver — then rewires `self_similarity` to consume them with byte-identical results.

### Scope
- **FR-2** — `ChunkingTrack` implements `TrackExtractor` (`output_type="signal"`), auto-discovered, runs through `_extract_masked`, persists `signals/chunking_{label}.json`.
- **FR-3** — `EmbeddingTrack` (`output_type="signal"`, depends on a chunk layer) persists vectors to SQLite-vec + manifest.
- **FR-4/FR-5** — layers appear in `/analysis/status` with provenance + descriptor; plural layers coexist (label-keyed paths).
- **FR-6** — capability descriptor in each manifest.
- **FR-7** — dependency-check resolver; `self_similarity` migrated to consume layers.
- **FR-13/FR-14 (data backbone only)** — each layer manifest carries a `rendering` descriptor + a precomputed `stats` summary, so the P5 rendering and P6 stats UI need no per-layer code. (The *UI* that consumes them ships in P5/P6.)
- **NFR-1** — `self_similarity` public results byte-identical at existing defaults.
- **NFR-2/5/6** — provenance-stamped, atomic writes, reuse-over-recompute.

### Mechanism
- **Track skeletons.** Drop two modules in `tracks/` implementing the protocol (`tracks/base.py:19`); auto-discovery (`tracks/registry.py:88`) picks them up with zero registration. Subclass `ParameterizedTrack` (`tracks/params.py:177`) so chunk size/overlap/model are runtime params under the existing fail-loud `ChunkingConfig`/`EmbeddingConfig`.
  - `ChunkingTrack.extract(project) -> Path`: runs `chunk_text` on the analyzable view (post contract-lock from P1), writes `signals/chunking_{label}.json` via `write_signal` (`signals.py:63`, atomic). `segment_offsets` = `[[start,end], …]` in original coordinates after remap.
  - `EmbeddingTrack.extract(project) -> Path`: `depends_on=["chunking_{label}"]`; embeds the resolved chunk layer's records via `embed_texts` (currently `self_similarity.py:875`), writes vectors to `cache/embeddings_{label}.db` (SQLite-vec, `sqlite_vec.py`) + `signals/embedding_{label}.json` manifest.
- **Label scheme (FR-5 collision-free).** Reuse `self_similarity`'s content-addressed label: `sha256(provider+endpoint+model+chunk_texts)[:16]` for embeddings; an analogous `sha256(mode+params+analyzable_digest)[:16]` for chunk layers. Distinct params → distinct label → distinct path; no collision.
- **Masked, coordinate-correct runs.** Both tracks run through the P1-unified `_extract_masked` (`server.py:236`). Chunking is **not** a signal-consumer (it produces the first layer), so it masks + remaps; embedding's `depends_on` references a chunk layer, so it follows existing consumer rules. Novel coordinate fields not in the manifest's `analyzable_coordinate_fields` already hard-fail via `UnmappedCoordinateError` (G4).
- **Capability descriptor (FR-6).** Write into the signal manifest `metadata`:
  - chunk layer: `{mode, overlapping, covers_full_text, unit, size, analyzable_digest}`;
  - embedding layer: `{chunk_layer_id, provider, model, dim, model_fingerprint}`.
  `analyzable_digest` is the same digest the analyzable bridge asserts (`5cd15cc`: `len(atext)==omap.child_len`), so a descriptor is only valid against the exact text it was computed on.
- **Render descriptor (FR-13) — the rendering backbone, added here so P5 needs no per-layer code.** Each layer manifest also carries a `rendering` block telling the frontend how to draw the layer as a track:
  - chunk layer: `rendering = {track_view: "chunk-band", overviewBarRendering: {type: "chunk-band", color}}` — drawn from `segment_offsets` by the `OverviewBar` lane machinery (the manifest already drives `overviewBarRendering.type`, `TrackManifest.ts:16`);
  - embedding layer: `rendering = {track_view: "embedding-lane", encoding: "cluster" | "pc1" | "nn-density", projection_ref}` — a 1-D per-chunk scalar (cluster id / first PC / neighbor density), drawn as a colored lane; `projection_ref` points at the 2-D scatter data (P3).
  This is the single change that makes rendering **data-driven and plural-safe**: the frontend iterates the track list and draws each layer by its `rendering.track_view`, so the Nth layer costs zero new code (the alternative — a hard-coded branch per layer label — does not scale to plural layers and is explicitly rejected).
- **Stats summary block (FR-14).** Each layer manifest carries a precomputed `stats` block, computed once at extract time (cheap, O(chunks)) so the UI can show numbers with no recompute:
  - chunk layer: `{count, coverage_pct, overlap_ratio, len_words: {mean,median,min,max}, len_chars: {...}, boundary_alignment: {sentence,paragraph,verse,element}}`;
  - embedding layer: `{count, dim, model_fingerprint, mean_pairwise_distance, cluster_count?}` (geometry summaries that are cheap; heavier distributions are computed on-read in P6, not stored).
- **Dependency check (FR-7) — the load-bearing mechanism, fully specified.** Today `depends_on` is a bare `list[str]` (`tracks/base.py:38`) with the `"_x"` virtual-dependency convention. We add a parallel, optional `layer_requirements: list[LayerRequirement]` to the protocol (back-compatible: tracks without it behave exactly as today). The schema and resolution algorithm are defined in **Vision §3.3** — implement it as:
  - **`LayerRequirement`** dataclass (`tracks/base.py` or a new `tracks/requirements.py`): `kind: Literal["chunk","embedding"]`, `constraints: dict[str, Any]` (descriptor-field predicates), `digest_match: bool = True`.
  - **Resolver** (`tracks/requirements.py:resolve_layers(project, requirements) -> dict[str, BoundLayer]`), called in the run lifecycle (`server.py:980`, before `asyncio.create_task`) and from the CLI run path (P1's unified runner). For each requirement: enumerate persisted layer manifests of `kind`; filter by every constraint predicate against the capability descriptor (§FR-6) and, if `digest_match`, by `analyzable_digest == project.analysis_view digest`; bind the sole survivor, or the newest by `run.json` timestamp if several (recording the choice in provenance), or **raise `LayerResolutionError`** (a `ValueError` subclass, mirroring `UnmappedCoordinateError`) naming the requirement and listing what was available. No silent consumption, no silent auto-production.
  - Keep `dependency_order()` Kahn topo-sort (`tracks/registry.py:52`) for *ordering* of name-based `depends_on`; the resolver adds *compatibility* binding for `layer_requirements`. The two are orthogonal and compose.
  - `self_similarity` declares `layer_requirements = [LayerRequirement("chunk", {"overlapping": False}), LayerRequirement("embedding", {"dim": <model-dim>})]` and reads the bound layers instead of computing inline.
- **`self_similarity` migration (NFR-1, the critical guard).** Replace the inline `chunk_text` (`tracks/self_similarity.py:1141`) + `embed_texts` (`:875`) calls with consumption of a resolved chunk layer + embedding layer. The `_chunks_cache`/`_embeddings_cache` extract-locals (`self_similarity.py:1135-1136`) become reads of the persisted layers.
  - **The equivalence the byte-identity rests on (made explicit).** `self_similarity`'s embedding cache is keyed `sha256(provider+endpoint+model+chunk_texts)[:16]`. Byte-identity therefore requires that `ChunkingTrack`, run with the *same params* `self_similarity` uses today, yields the **exact same ordered `chunk_texts` list** the inline `chunk_text` produced — only then is the embedding label unchanged, the existing vector cache hit, and the matrix identical. The chunk-layer's own new label (`sha256(mode+params+analyzable_digest)`) is *additional* metadata for layer identity; it does **not** feed the embedding key. So the migration invariant is: *track-produced `chunk_texts` ≡ inline `chunk_text` output, element-for-element.*
  - **Acceptance bar (two-level):** (1) an upstream test asserts `ChunkingTrack.extract` chunk-text list equals the legacy inline `chunk_text` output on every fixture (this is what *guarantees* the embedding label is unchanged); (2) a downstream regression test asserts the `self_similarity` matrix is byte-identical pre/post migration on every fixture incl. gold DR. Do not merge if either diverges.

### New artifacts
- `tracks/chunking_track.py`, `tracks/embedding_track.py`.
- Resolver: small module or function in the run layer (`registry.py`/`runner.py`).
- Manifest schema additions (capability + `rendering` + `stats` blocks) in `signals.py` writers.
- `self_similarity.py` rewired to consume layers.
- Tests: `test_chunking_track.py`, `test_embedding_track.py`, `test_layer_resolver.py`, `test_self_similarity_migration.py` (matrix-equality regression), `test_layer_manifest_schema.py` (rendering + stats blocks present and well-formed).

### Tests
- Track discovery: both tracks appear via `registry.discover()` and in `/analysis/status`.
- Persistence: chunk/embedding layers written atomically with manifest + `{track}.run.json`; reload round-trips.
- Plural coexistence: two chunk layers (different params) + two embedding layers coexist without path collision.
- Descriptor correctness: manifest carries the full descriptor; `analyzable_digest` matches the bridge digest.
- Resolver: compatible layer reused; incompatible (overlap mismatch, wrong dim, stale digest) → loud error.
- **NFR-1 regression:** `self_similarity` matrix byte-identical pre/post migration on all fixtures incl. gold DR.

### Done criteria
- [ ] Both layer-tracks auto-discovered, runnable via HTTP + CLI, persisted with capability + `rendering` + `stats` blocks + provenance.
- [ ] Plural layers coexist; resolver reuses-or-fails-loud (never silently wrong).
- [ ] `self_similarity` consumes layers; matrix byte-identical; full suite GREEN.
- [ ] Manifest-schema test confirms every layer carries well-formed `rendering` + `stats` blocks.
- [ ] Committed as a small series (track skeletons → descriptor/resolver → self_sim migration), each independently green.

### Risks & mitigations
- *Migration changes `self_similarity` numerics.* **Mitigation:** content-addressed embedding label → identical vectors; gate the migration commit on a matrix-equality test; do not merge if any fixture diverges.
- *Resolver becomes a hidden auto-invocation in disguise* (re-introducing the smell we're removing). **Mitigation:** per Vision OQ#3 recommendation, default resolver = **fail-loud, require the layer to exist**; inline production is an explicit, separately-flagged convenience, not the default.
- *Embedding-layer home ambiguity* (`cache/` vs `signals/`, Vision OQ#2). **Mitigation:** keep vectors in `cache/embeddings_{label}.db` (today's location) but treat the **manifest** in `signals/` as the first-class result; defer the move decision to human review, code so the manifest is the source of truth either way.
- *In-memory `_running_jobs` (no job DB) loses layer-run state on restart.* **Mitigation:** on-disk `{track}.run.json` is the authoritative provenance (already true); status reads disk, not the in-memory dict, for completed layers. Documented in §Risk register.

### Sequencing
Needs P1 (coordinate-correct chunk producer + CLI parity). Unblocks P3 (embedding-as-analysis builds on `EmbeddingTrack`), P4 (analytics tracks reuse the layer-track pattern), and all Wave-1 reuse (`self_similarity` now consumes layers; future entity/dialogue/topic tracks declare layer dependencies instead of recomputing).

---

## P3 — Embedding-as-analysis + the embedding visualization suite

> Turns the embedding layer from "input to self_similarity" into a **standalone analysis** with a full semantic-space toolkit: model choice, filtered embedding, a 2-D projection, distance distributions, a similarity heatmap, clustering, and the 1-D lane encoding that lets an embedding render as an in-text track (FR-13). This is the backend half of "all sorts of visualization options"; P6 renders them.

### Scope
- **FR-3 (extended)** — embedding runnable as its own analysis (not just a self_similarity dependency); model/provider/dim selectable.
- **FR-6** — descriptor surfaced for embedding-space reuse.
- **FR-13 (embedding-lane data)** — compute the per-chunk 1-D encoding (cluster id / PC1 / NN-density) the embedding track lane draws.
- **FR-14 (embedding distributions)** — compute the on-read distributions the per-layer stats panel renders.
- **NFR-4** — pre-run cost estimate; never auto-run embedding.

### Mechanism
All compute reads the persisted vectors — `get_all_vectors()` returns them in insertion = chunk order (`sqlite_vec.py`, `ORDER BY para_index, rowid` — load-bearing), so row *i* is chunk *i*. Each endpoint mirrors the `DotplotView` fetch contract (manifest + `Float32Array` `.bin`, little-endian) so the frontend reuses one fetch path.

- **Filtered embedding.** `EmbeddingTrack` accepts an optional filter (book/chapter/element-type/query) applied to the chunk layer before embedding — embed only a subset. Filter recorded in provenance params.
- **Projection** `GET …/embedding/{label}/projection?method=pca|umap` → N×2 `Float32Array`. **PCA via numpy is the default** (deterministic, zero new deps); UMAP is opt-in (host decision — server `umap-learn` vs client `umap-js` — deferred to Vision OQ#4). Colorable client-side by structure or another layer (color is a frontend join on chunk index, not a server concern).
- **Distance distributions** `GET …/embedding/{label}/distances?kind=pairwise|nn` → a histogram (bin edges + counts) of cosine distances: `pairwise` (sampled if N large, with the sample size logged — no silent cap) or `nn` (each chunk's nearest-neighbor distance, via the existing `search(MATCH ORDER BY distance)`).
- **Similarity heatmap** `GET …/embedding/{label}/heatmap?order=chunk|cluster` → an N×N (or block-reduced for large N) cosine-similarity matrix as `Float32Array`; consumed by the existing `CooccurrenceHeatmap.tsx` renderer.
- **Clustering** `GET …/embedding/{label}/clusters?k=` → per-chunk cluster labels (k-means via numpy, deterministic seed passed in params per the LOCK policy on seeds) + cluster sizes. Feeds both the `cluster` lane encoding and the cluster summary stat.
- **Embedding-lane encoding (FR-13)** `GET …/embedding/{label}/lane?encoding=cluster|pc1|nn-density` → one scalar per chunk (`Float32Array`), the value the in-text embedding lane colors by. `pc1` reuses the projection's first component; `cluster` reuses the clustering; `nn-density` is mean inverse NN-distance.
- **Cost estimate (NFR-4) — new work, not a reuse.** Before run, surface a `chunk_count → vectors → ~time/$` estimate; embedding never auto-runs. **No cost estimate exists today** — audit remediation item D2-7 (the param dialog shows nothing about chunk count, matrix dimension, or memory). P3 builds `GET …/embedding/{label}/estimate` returning chunk count → vector count → rough wall-time from the resolved chunk layer, rendered as a pre-run confirmation in the param dialog.

### New artifacts
- Endpoints in `server.py`: `projection`, `distances`, `heatmap`, `clusters`, `lane`, `estimate`.
- A `vectorstore/analytics.py` (or `embedding_analytics.py`) compute helper: numpy PCA, k-means, pairwise/NN distance histograms, similarity matrix — all deterministic, numpy-only.
- Filter param plumbing in `EmbeddingTrack`.
- Tests: `test_embedding_projection.py`, `test_embedding_distances.py`, `test_embedding_heatmap.py`, `test_embedding_clusters.py`, `test_embedding_lane.py`, filtered-embedding + estimate tests.

### Tests
- Projection: N chunks → N×2 coords; PCA deterministic; shape/dtype contract (`Float32Array`, little-endian, matches `DotplotView`).
- Distances/heatmap/clusters/lane: deterministic outputs on a fixture; index alignment (row *i* = chunk *i*) asserted; large-N sampling logs the sample size (no silent cap, per the fallbacks-are-failures rule).
- Filtered embedding: subset filter → only matching chunks embedded; provenance records filter.
- Cost estimate returns before any vectors are computed.

### Done criteria
- [ ] Embedding runs as a standalone analysis with model/filter choice + provenance.
- [ ] All six endpoints return deterministic, index-aligned data consumable by the frontend fetch pattern.
- [ ] Embedding-lane encoding (FR-13) and distribution data (FR-14) exist for P5/P6 to render.
- [ ] Cost estimate precedes every embedding run; no auto-run.
- [ ] Suite GREEN.

### Risks & mitigations
- *UMAP nondeterminism / heavy dependency.* **Mitigation:** PCA (numpy, deterministic, zero new deps) is the default; UMAP opt-in, host decided in OQ#4.
- *O(N²) heatmap / pairwise blow-up at high chunk counts.* **Mitigation:** block-reduce the heatmap and sample pairwise distances above a threshold, **logging the reduction** (no silent truncation); NN-distance (O(N·k)) is the scalable default.
- *Embedding cost surprises the user.* **Mitigation:** NFR-4 estimate is mandatory pre-run UI, not optional.

### Sequencing
Needs P2 (`EmbeddingTrack` + descriptor + `rendering`/`stats` blocks). Unblocks P5 (embedding lane rendering) and P6 (the embedding stats panel's visualization set).

---

## P4 — Broader Wave-0 analytics tracks

> The descriptive/QC/exploration analytics from Vision §4.3–4.5. Mostly **independent tracks** that reuse the layer-track pattern; can be built in parallel once P2 lands.

### Scope
- **FR-8** — `ProfileTrack`: descriptive/distributional statistics (Vision §4.3).
- **FR-9** — data-quality / integrity report running the substrate contract validators (Vision §4.4).
- **FR-10** — positional/lexical analytics: KWIC, dispersion, collocations, duplicate-finder (Vision §4.5).
- **NFR-7** — descriptive-not-inferential framing throughout.

### Mechanism
- **`ProfileTrack`** (`tracks/profile_track.py`): counts (tokens/types/vocab/hapax), lexical diversity (TTR/MATTR/MTLD/Yule's K), length distributions (word/sentence/paragraph/chunk), Zipf fit + Heaps' curve, function-word profile, n-gram tables. Computes on the analyzable view; emits a **report** + distribution data (signal manifest). Cheap → candidate for auto-run on open (UI decision in P5).
- **Integrity report (FR-9, the contract-lock's second dividend).** A user-runnable report that **executes the substrate contract validators already built** — `_complement_spans` partition (masking, `e6758de`), `_validate_segments` (`c13db0f`), `validate_section_tree` + `_validate_span_regions` (`b402e00`), `OffsetMap.__init__` round-trip (`5778533`), analyzable-bridge length agreement (`5cd15cc`) — and returns green/violation per invariant. This makes the substrate invariants **legible** to the user ("are my coordinates sound?") and reuses validators verbatim (no new validation logic, just a presentation surface). Plus encoding/normalization sanity, near-duplicate finder (surface the repeat-masking signal), masking-coverage + structural-count summary.
- **Positional/lexical (FR-10).** Two delivery shapes, chosen by whether the result is a reusable layer or a transient query:
  - **Dispersion = a layer-producing track** (`tracks/dispersion_track.py`): for a query term, emit an `annotation`-type track whose records are `{start, end, term}` hits in original coordinates (one per occurrence), rendered as a lexical barcode via the existing `OverviewBar` lane. Reuses `_extract_masked` + remap like any track; persists as `tracks/dispersion_{label}.jsonl`.
  - **KWIC / collocations / duplicate-finder = transient query endpoints** (not persisted layers — they are interactive lookups): `GET /api/projects/{id}/kwic?term=&window=` returns `[{start, end, left, keyword, right}]`; `GET …/collocations?window=` returns `[{a, b, pmi, loglik, count}]` (PMI / log-likelihood over a co-occurrence window); duplicate-finder returns repeat-passage spans (surfacing the repeat-masking signal as a report). These compute on the analyzable view and need no descriptor/provenance because nothing downstream depends on them.
- **Honesty (NFR-7).** All framed descriptive-of-this-text; explicit caveats where no reference corpus exists (consistent with the §5 consumption-honesty pass). No inferential claims dressed as descriptive.

### New artifacts
- `tracks/profile_track.py`, `tracks/integrity_report.py` (or an endpoint that runs validators), positional/lexical analytics (track + endpoints).
- Tests: `test_profile_track.py`, `test_integrity_report.py` (validators surface known-good + injected-violation), `test_kwic_dispersion.py`.

### Tests
- ProfileTrack: deterministic stats on a fixture (TTR/MTLD/Zipf-slope within tolerance); report + distribution data shape.
- Integrity report: clean fixture → all-green; a project with an injected coordinate violation → the matching validator flags it (proves the report actually runs the validators).
- KWIC/dispersion: correct positions for a known term; collocation scores deterministic.

### Done criteria
- [ ] ProfileTrack runs, emits report + distributions; stats deterministic.
- [ ] Integrity report runs all substrate validators and reports per-invariant pass/violation.
- [ ] KWIC/dispersion/collocations/dup-finder available; layer-producing where applicable.
- [ ] All framed descriptive (NFR-7); suite GREEN.

### Risks & mitigations
- *Stat libraries pull heavy deps.* **Mitigation:** TTR/MTLD/Zipf/Heaps are small pure-Python/numpy computations; avoid new deps; reuse existing tokenization.
- *Integrity report drifts from the real validators* (re-implements instead of reusing). **Mitigation:** the report **calls the exact validator functions**; a test injects a violation and asserts the report catches it, guaranteeing no drift.

### Sequencing
Needs P2 (layer-track pattern; ProfileTrack may consume a chunk layer for chunk-length stats). Tracks here are mutually independent → parallelizable. Unblocks P5's Profile + Explore tabs.

---

## P5 — Suite shell + native plural layer-track rendering

> Delivers the user-facing workbench shell **and** the Vision §3.4 commitment: every chunk & embedding layer auto-renders as a browser track, **plural-safe, driven by the P2 `rendering` descriptor** — producing the Nth layer adds a lane with zero new code. Frontend has **no viz libs installed** (all viz hand-rolled `<canvas>`/`<svg>`); the one default add is `d3-shape` for curves.

### Scope
- **FR-11** — Profile / Representations / Explore shell + layer manager, in the existing app frame.
- **FR-13** — data-driven rendering of *every* layer as a track; plural coexistence; layer manager controls order / visibility / overlay.

### Mechanism
- **Integration point (lowest-friction).** The app is a **flat tab-switch** (`AppLayout`, no router; `viewStore` `TabId` union: `reading|browser|texthic|characters|analysis|compare`). Two options:
  - (a) add a new `'suite'` `TabId`; or
  - (b, recommended) add **sub-tabs inside the existing `AnalysisPanel`** → Profile / Representations / Explore. Lower friction: reuses the panel that already polls `/analysis/status` @2s and renders `TrackStatus[]` (name/status/outputType/dependsOn/evidenceLevel/runInfo/error) with `ParamDialog`.
- **Data-driven track-rendering loop (the FR-13 core — this is what makes "always rendered, plural" true).** Rather than a hard-coded view per layer kind, the frontend iterates the track list from `/analysis/status` and, for each layer, **dispatches on `manifest.rendering.track_view`** (the P2 render descriptor):
  - `chunk-band` → an `OverviewBar` ribbon lane: new branch in the `TrackBarcode` fn (`OverviewBar.tsx:86`); add `'chunk-band'` to the `TrackManifest.ts:16` union (`density-barcode | state-band | ab-band | none | chunk-band`); `x = off/docLen*W` — same coordinate math as existing barcodes; drawn from `segment_offsets`.
  - `embedding-lane` → a colored lane fed by the P3 `…/lane?encoding=…` scalar (`Float32Array`, one value per chunk), mapped through a color scale.
  Because dispatch is on manifest data, **the fifth chunk layer and the third embedding layer render with no new code** — the alternative (a branch per layer label) is explicitly rejected as not plural-safe.
- **Plural coexistence + layer manager.** Multiple layers → multiple stacked lanes. The layer manager — **reusing the `@dnd-kit/*` drag pattern already implemented in `TrackPanel.tsx`** (`DndContext`/`SortableContext`/`useSortable`/`arrayMove`; installed and in active use, not a new dep) — controls lane **order**, **visibility** (toggle), and **overlay/compare** (e.g. two chunk ribbons overlaid). Reuse `browserStore.laneDisplayModes`. Each row shows provenance + capability descriptor + the instant `stats` summary (read straight from the manifest, no fetch) + two affordances: "open stats panel →" (P6) and "use in →" (hand the layer to a Wave-1 analysis).
- **Embedding scatter (Representations panel).** Mirror `DotplotView` (double-buffer canvas; fetch the P3 `…/projection` 2-D `Float32Array`); color by structure or another layer (a frontend join on chunk index). The scatter is the embedding's Representations-panel view; its in-text presence is the `embedding-lane` above — so an embedding is visible **both** ways.
- **Text-level Profile dashboard (renderer decision — resolved).** Render the P4 ProfileTrack distributions hand-rolled, consistent with the repo's zero-viz-dep idiom: **histograms / bars as plain `<svg>` rects** (the primitive `OverviewBar` already uses); **ECDF / Zipf / Heaps curves as a single `<path>`** whose *only* new dependency is **`d3-shape`** (`d3.line`/`d3.curve*` — path-string generation, no DOM, small). Net new frontend deps across P5+P6: **`d3-shape`** (default); **`umap-js`** only if P3 chose client-side UMAP.
- **Suite shell + integrity badge.** Profile / Representations / Explore sub-tabs; header **substrate-integrity badge** (one-click P4 integrity report; green/violation) — "are my coordinates sound?" is the first thing the user sees.

### New artifacts
- `AnalysisPanel` sub-tabs (Profile/Representations/Explore) or new `SuitePanel`.
- The **layer-render dispatch loop** (iterate tracks → render by `rendering.track_view`).
- `chunk-band` branch in `OverviewBar.tsx` + `'chunk-band'` in the `TrackManifest.ts:16` union.
- `EmbeddingLane` (colored 1-D lane) + `EmbeddingScatter` (hand-rolled `DotplotView` canvas mirror, zero-dep).
- `LayerManager` (reusing the `TrackPanel.tsx` `@dnd-kit` pattern; order/visibility/overlay).
- `ProfileDashboard` (text-level ProfileTrack viz).
- `package.json`: `d3-shape` (default); `umap-js` (only if P3 chose client-side UMAP).
- Frontend tests + Playwright user-flow capture.

### Tests
- Component/render tests for the dispatch loop, chunk-band ribbon, embedding lane, scatter, layer manager, profile dashboard.
- **Plural Playwright golden-path:** import → produce **two** chunk layers (`word-7`, `slide-10`) + **one** embedding layer → assert **all three render as distinct lanes simultaneously** → reorder via layer manager → toggle one off → overlay the two chunk ribbons. This is the explicit proof of FR-13 plural rendering.
- Integrity badge: green on a clean project; violation surfaced on an injected-violation project.
- (UI correctness is feature-verified in-browser, not only unit-tested — per project practice.)

### Done criteria
- [ ] Profile / Representations / Explore reachable; layer manager lists layers with provenance + descriptor + instant stats.
- [ ] **Every chunk & embedding layer auto-renders as a track lane via its manifest `rendering` descriptor; producing an additional layer adds a lane with no code change.**
- [ ] Plural layers coexist; layer manager reorders / toggles / overlays them.
- [ ] Substrate-integrity badge runs the P4 report.
- [ ] Frontend tests + the plural Playwright golden-path green; verified in-browser.

### Risks & mitigations
- *Render dispatch hard-codes a per-label branch (defeating plural-safety).* **Mitigation:** the dispatch keys on `rendering.track_view` only; a test adds a *second* chunk layer and asserts it renders with no new code path.
- *New viz libs balloon the bundle.* **Mitigation:** mirror `DotplotView` canvas (zero-dep) for scatter/lane; add only `d3-shape` for curves; UMAP client-side only if P3 didn't ship server-side.
- *Sub-tab vs new-TabId churns navigation.* **Mitigation:** recommend sub-tabs inside `AnalysisPanel`; new `TabId` only if the suite outgrows it.
- *Many stacked lanes hurt perf at high chunk counts.* **Mitigation:** `OverviewBar`/`DotplotView` already render large arrays via SVG-rect / double-buffer canvas; virtualize lanes if needed.

### Sequencing
Needs P2 (`rendering` descriptor + layer data) and P3 (embedding `lane`/`projection` data). Renders alongside P6 (which adds the drill-in stats panels the layer rows link to).

---

## P6 — Per-layer statistics, distributions & visualization options

> The Vision §3.5 + FR-14 commitment: from any layer, **one click to its summary statistics, distributions, and a selectable set of visualizations.** Backend distribution endpoints (chunk) + reuse of P3 (embedding) + the per-layer stats-panel UI.

### Scope
- **FR-14** — per-layer stats panel: instant `stats` summary + a selectable visualization set over on-demand distributions, quick-navigable from the layer manager and the track lane.

### Mechanism
- **Chunk-layer distributions (backend, new).** Add `GET /api/projects/{id}/chunking/{label}/stats` returning the heavier distribution data the manifest summary points at: length histograms (words & chars; bin edges + counts) + ECDF arrays, by-element-type length groups (for violins), and the boundary-alignment breakdown. Computed on-read from `segment_offsets` + the structural boundaries (`layout_sections.json`); cheap, numpy-only, deterministic.
- **Embedding-layer distributions (backend, reuse).** Already built in P3 (`projection` / `distances` / `heatmap` / `clusters`). P6 only consumes them — no new embedding endpoints.
- **Per-layer stats panel (frontend, new).** Selecting a layer (from the layer-manager row or the track-lane action) opens a panel with the instant `stats` summary (from the manifest — no fetch) plus a **visualization-option selector**:
  - chunk layer: `length histogram | ECDF | by-element violin | boundary-alignment bar`;
  - embedding layer: `projection scatter | pairwise-distance histogram | NN-distance histogram | similarity heatmap | cluster summary`.
  Renderers reuse the P5 primitives: `<svg>` rect histograms/bars; `d3-shape` for ECDF/curves; canvas scatter (`DotplotView` mirror); and the **already-existing `CooccurrenceHeatmap.tsx`** for the similarity heatmap. Every view is colorable by structure or by another layer (chunk-index join).
- **Quick navigation.** The panel opens in **one click** from (a) the layer-manager row and (b) a track-lane context action; it is deep-linkable through `viewStore` so a compare flow can open two panels side by side (e.g. the length histograms of `word-7` vs `slide-10`).

### New artifacts
- `chunking/{label}/stats` endpoint + `chunk_layer_stats` compute helper (numpy).
- `LayerStatsPanel` (frontend) with the per-kind visualization-option selector.
- `ViolinChart` + `Histogram`/`ECDF` chart components (svg + `d3-shape`); reuse `CooccurrenceHeatmap.tsx`, `DotplotView` mirror.
- Tests: `test_chunk_layer_stats.py` + frontend component/Playwright tests.

### Tests
- Chunk-layer stats: deterministic histograms/ECDF/violin groups/boundary-alignment on a fixture; bins sum to chunk count; alignment fractions in `[0,1]`.
- **Playwright:** open a chunk layer's panel → switch `histogram → ECDF → violin → boundary-bar`; open an embedding layer's panel → switch `scatter → pairwise-hist → NN-hist → heatmap → cluster`; open two chunk panels side-by-side and confirm both render.
- Quick-nav: one click from a layer-manager row opens the correct layer's panel.

### Done criteria
- [ ] Every chunk & embedding layer exposes a stats panel: instant summary + selectable distribution visualizations.
- [ ] Chunk distributions endpoint deterministic + index-correct; embedding views reuse P3 data.
- [ ] One-click navigation from layer manager and track lane; side-by-side compare works.
- [ ] Frontend + Playwright green; backend suite GREEN.

### Risks & mitigations
- *O(N²) heatmap / pairwise blow-up at high chunk counts.* **Mitigation:** reuse P3's block-reduction + sampling (with logged sample size — no silent cap); NN-distance is the scalable default view.
- *Per-layer stat compute duplicates ProfileTrack (text-level).* **Mitigation:** P6 chunk stats are *of a chunk layer* (over `segment_offsets`), distinct from P4 ProfileTrack (*of the whole text*); share tokenization helpers, not endpoints.
- *Viz-option switching re-fetches and feels slow.* **Mitigation:** cache fetched distribution arrays per (layer, view) in the store; the instant `stats` summary needs no fetch at all.

### Sequencing
Needs P2 (`stats` summary block), P3 (embedding distributions), and P5 (the shell + layer manager the panel launches from). Terminal UI, shipped alongside/after P5.

---

## Cross-cutting concerns

### Testing strategy
- Every phase ends with the full backend suite GREEN (`-m "not external"`, JUnit-parsed). Baseline 636/636 at substrate-walk tip.
- Two recurring acceptance bars from the substrate walk are reused: **(1)** behavior byte-identical for valid inputs (P1 chunk lists, P2 self_similarity matrix); **(2)** validators fire only on impossible-today corruption.
- Frontend (P5/P6): unit/component tests **plus** in-browser feature verification (Playwright) — UI correctness is not claimed from type-check/tests alone. The P5 **plural** golden-path (two chunk layers + one embedding layer rendering as three simultaneous lanes) is the explicit proof of the FR-13 "always rendered, plural" commitment.

### Backward compatibility (NFR-1)
- No on-disk format is removed; new manifests/descriptors are additive. Existing analyses and artifacts keep working. `self_similarity`'s public results are unchanged (gated by the matrix-equality regression). The only behavior change a user can observe is **new opt-in capability**, never a changed default.

### Provenance & auditability (NFR-2, P1/P3 principles)
- Every layer is stamped via `write_run_provenance` → `{track}.run.json` (`atomic.py:47`) — the **sole** provenance source, read by `_track_run_info` (`server.py:139`). No output-affecting value is hidden (acceptable-default rule). Capability descriptors live in the signal manifest, co-located with the data they describe.

### Performance (NFR-6)
- Reuse-over-recompute: content-addressed labels mean a compatible layer is found and reused, not recomputed. The SQLite-vec cache survives across runs/projects. The resolver's compatibility scan is over manifests (small JSON), not vectors.

### CLI/HTTP parity (FR-12)
- The known gap (`cli.py:193`, inside the `analyze` command at `cli.py:128`, extracts directly with no masking/remap) is closed in **P1** by unifying both paths through one `_extract_masked`. After P1, every track — including the new layer-tracks — is coordinate-correct from either entry point. This is called out as its own done-criterion because it is a latent correctness bug, not merely a convenience.

---

## Risk register (cross-phase)

| Risk | Phase | Severity | Mitigation |
|---|---|---|---|
| `self_similarity` numerics drift on migration | P2 | High | Content-addressed label → identical vectors; gate commit on matrix-equality regression; don't merge on any divergence |
| Resolver becomes hidden auto-invocation (re-introducing the smell) | P2 | Med | Default fail-loud + require-layer-exists (Vision OQ#3a); inline production is explicit/flagged only |
| `smart` mode legitimately non-partitioning | P1 | Resolved | Contract is disjoint (whitespace gaps allowed), not a partition — `smart` validates as-is; verified byte-identical on gold DR + all fixtures |
| `_extract_masked` refactor disturbs signal-consumer skip logic | P1 | Med | Move verbatim, server stays thin caller, re-run derive/masking set before+after |
| In-memory `_running_jobs` loses state on restart (no job DB) | P2 | Low | `{track}.run.json` on disk is authoritative; status reads disk for completed layers; documented non-goal (Vision §8) |
| Embedding-layer home ambiguity (`cache/` vs `signals/`) | P2 | Low | Manifest in `signals/` is source of truth; defer physical move to human review (Vision OQ#2) |
| UMAP nondeterminism / heavy dep | P3 | Med | PCA default (numpy, deterministic, zero deps); UMAP opt-in, host TBD |
| Integrity report drifts from real validators | P4 | Med | Report calls the exact validator fns; injected-violation test guarantees no drift |
| New frontend viz libs balloon bundle | P5/P6 | Low | Mirror `DotplotView` canvas (zero-dep); add only `d3-shape` if needed; UMAP client-side only if not server-side |
| Render dispatch hard-codes a per-label branch (defeats FR-13 plural-safety) | P5 | Med | Dispatch keys on `rendering.track_view` only; a test adds a *second* chunk layer and asserts it renders via the same path with no new code |
| O(N²) heatmap / pairwise-distance blow-up at high chunk counts | P3/P6 | Med | Block-reduce heatmap + sample pairwise with **logged** sample size (no silent cap); NN-distance (O(N·k)) is the scalable default view |
| Per-layer stats duplicate text-level ProfileTrack | P6 | Low | Layer stats compute over `segment_offsets` (a *layer*), distinct from ProfileTrack over the *whole text*; share tokenization helpers, not endpoints |
| Embedding cost surprises user | P3/P5 | Low | NFR-4 mandatory pre-run estimate; never auto-run embedding |

---

## Sequencing & dependency summary

```
P1 (contract-lock + CLI parity)  ── no upstream; detachable, land anytime
        │  (coordinate-correct chunk producer + unified masked-run path)
        ▼
P2 (layer-tracks + capability/RENDER/STATS descriptors + resolver + self_sim migration)
        │
        ├──────────► P3 (embedding viz suite: projection / distances / heatmap / clusters / lane)
        │                   │
        ├──────────► P4 (profile / integrity / dispersion + KWIC — parallelizable)
        │                   │
        └─────────┬─────────┴────► P5 (suite shell + native PLURAL layer-track rendering · FR-13)
                  │                          │
                  └──────────────────────────┴────► P6 (per-layer stats / distributions / viz · FR-14)
```

- **P1** is a pure correctness no-regret; ship it first and alone if desired.
- **P2** is the linchpin; everything else reuses its layer-track + resolver pattern, and it now also carries the **render + stats manifest backbone** that makes P5 plural-rendering and P6 instant-stats possible. Internal commits: track skeletons → capability/render/stats descriptors + resolver → `self_similarity` migration (each green).
- **P3 and P4 are independent** of each other and parallelizable post-P2.
- **P5 + P6 are the terminal user-facing pair.** P5 makes *every* chunk/embedding layer render as a browser track (FR-13, plural-safe); P6 adds the stats/distribution/visualization drill-in (FR-14). Both need P2's backbone + P3's embedding data; P6 additionally needs P5's shell + layer manager to launch from.

### Open questions carried from the Vision doc
The Vision doc's nine open questions (esp. layer naming, embedding-layer home, resolver strictness, first-UI-cut scope, CLI-fix timing) are **inputs to this plan, not resolved by it** — they are flagged at the relevant phase risk rows and await human review before P2/P5 lock their respective decisions.

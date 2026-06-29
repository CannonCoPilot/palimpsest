# Wave 0 Analysis Suite — Development Plan

**Status:** Draft for human review
**Date:** 2026-06-24
**Companion:** [wave0-analysis-suite-vision.md](./wave0-analysis-suite-vision.md) (the vision & requirements this plan implements)
**Builds on:** [analysis-design-principles.md](./analysis-design-principles.md) (P1–P5 + acceptable-default rule), [analysis-paradigm-audit-2026-06.md](../audits/analysis-paradigm-audit-2026-06.md) (G1–G5), and the substrate contract-lock walk (masking / segmentation / verse-element / OffsetMap / analyzable-bridge).

---

## 0. How to read this plan

This plan turns the Vision doc's requirements (FR-1…22, NFR-1…7) into eight Wave-0 phases (P1–P8), a behavior-neutral pre-stage refactor (P9), and two deferred cross-text phases (P10–P11). Each phase is scoped to be **independently landable, tested, and committed** — the project's established cadence (each substrate contract-lock piece was its own verified commit). For every phase:

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
| **P2 — Layer infrastructure: chunk + embed tracks, resolver, producibility** | FR-2…7, **FR-13/14 (manifest backbone)**, FR-4 (producibility + status), NFR-2/5/6 | Structural core (additive) | P3, P4-embedding, P5/P6 rendering, P7 redesign, all Wave-1 reuse |
| **P3 — Embedding-as-analysis + visualization suite** | FR-3 (extends), FR-6, **FR-13/14 (embedding data)**, NFR-4 | Embedding viz suite + endpoints | P5 embedding lane, P6 embedding stats |
| **P4 — Broader Wave-0 analytics tracks** | FR-8, FR-9, FR-10, NFR-7 | New tracks (mostly independent) | P5 Profile/Explore tabs |
| **P5 — Suite shell + native plural layer-track rendering** | FR-11, **FR-13** | Frontend; data-driven plural rendering | (terminal) tracks visible in browser |
| **P6 — Per-layer statistics, distributions & viz options** | **FR-14** | Frontend + chunk-stats endpoint | (terminal) stats/viz drill-in |
| **P7 — self_similarity redesign (layer-consumer)** | embedding-agnostic, fail-loud similarity consumer; foundation for a *family* of similarity methods | Backend redesign (behavior-changing) | future similarity / NN / clustering analyses |
| **P8 — Repeat detection + masking analysis** | FR-15, FR-16, FR-17 | New tracks + chunking option (additive); opens masking constants | P7's flag-only repeat consumption |
| **P9 — Similarity-engine generalization (cross-text pre-stage)** | FR-18, FR-19, FR-20 | Behavior-neutral seam-lift | P10; **gates the "P1/P2/P7/P8 passed" call** |
| **P10 — Cross-text similarity & synteny view** *(deferred)* | FR-21 | New similarity mode (collection-scoped) | the cross-text / synteny UI |
| **P11 — Scale & corpus modes** *(deferred)* | FR-22 | Compute strategy (candidate-gen + sparse) | probe / corpus at scale |

> **Re-scope (2026-06-26).** P2 no longer migrates `self_similarity`. The original P2 folded a *byte-identical migration* of self_similarity into the structural work; review concluded that designed *to* the legacy monolith rather than *toward* the vision. P2 is now strictly the **layer infrastructure** (producer tracks + dependency resolver + producibility/status) — additive, no existing behavior changed. The self_similarity rework is promoted to its own phase **P7**, a *ground-up redesign* as an embedding-agnostic, fail-loud **layer consumer** (it does not run when no chunk/embedding layers exist, and does not dictate which embedding model is used), and the framing for a family of similarity methods (self-similarity matrix, NN graphs, clustering, …). Consequently **NFR-1 (byte-identical self_similarity) is retired** — a consumer redesign intentionally changes the workflow; the honest invariant is the weaker *same chunk layer + same embedding vectors → identical similarity math*.

**Critical path:** P1 → P2 → {P3, P4, P8, P7} → {P5, P6}. P1 is detachable (land anytime). P4's tracks are mutually independent and parallelizable once P2 lands. P7 (self_similarity redesign) needs P2's producible layers (FR-4) — you cannot make a consumer *fail-loud-requiring-layers* until users can produce those layers through the normal run flow and see them. P8 (repeat detection + masking) is parallelizable post-P2 like P3/P4, and its `repeat_mask` layer is what makes P7's flag-only repeat consumption concrete, so P8 lands before (or with) P7's repeat step. P5 (rendering) and P6 (stats panels) both need P2's manifest backbone + P3's embedding data; they ship together as the user-facing surface. The two user commitments — *every chunk/embedding layer always renders as a track* (FR-13) and *every layer has quick-access stats/distributions/viz* (FR-14) — are carried by the P2 manifest backbone → P3 embedding data → P5/P6 UI chain. **P9** sits off the critical path: it follows P7/P8, is behavior-neutral (self-similarity byte-identical), and is the gate that lets **P1/P2/P7/P8 be declared *passed***. **P10 and P11 are deferred** — P10 (cross-text / synteny) additionally needs the collection analytical tier; P11 (scale / corpus) is a compute-strategy phase. Neither is scheduled, and P9 is explicitly shaped so adding them is additive rather than a rewrite.

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

## P2 — Layer infrastructure: chunk + embed tracks, resolver, producibility

> **The structural core.** Converts chunking and embedding from `self_similarity`-owned locals into first-class, persisted, reusable tracks with capability descriptors and a dependency-check resolver. The resolver lands here as *additive* infrastructure; the first consumer that declares a requirement against it — the ground-up `self_similarity` redesign — is **P7**, not P2. No existing behavior changes in P2.

### Scope
- **FR-2** — `ChunkingTrack` implements `TrackExtractor` (`output_type="signal"`), auto-discovered, runs through `_extract_masked`, persists `signals/chunking_{label}.json`.
- **FR-3** — `EmbeddingTrack` (`output_type="signal"`, depends on a chunk layer) persists vectors to SQLite-vec + manifest. *(Repeat-masking is **not** a P2 sub-step of this track — see the note below.)*

> **Repeat-masking deferred to a dedicated analysis (decision 2026-06-26).** P2 extracts the exact-repeat helpers into `tracks/repeats.py` so `self_similarity` shares one definition and a future analysis can reuse them — but it does **not** bolt a `repeat_mask` flag onto `EmbeddingTrack`. Repeat-masking is a complex analysis in its own right. The agreed near-term *semantics* is **flag-only** (embed every chunk; record a per-chunk `masked` flag + the repeat phrases for a consumer to honor — mirroring today's `self_similarity`, which embeds all chunks and skips masked ones only in the matrix). The full treatment — what masking *means* for an embedding, how it renders, how a consumer declares it — is promoted to its own phase, **P8** (now scoped below: a text-level `repeats` detection track, a `ChunkingTrack.hide_repeats` pre-chunk option, and a persisted `repeat_mask` flag layer), not a one-line track option.
- **FR-4/FR-5 (producibility + status)** — layer tracks are runnable through the normal HTTP/CLI run flow with their params, and plural label-keyed layers appear in `/analysis/status` each with its label + capability + stats + per-label provenance. This is the prerequisite that lets a future consumer (P7) *require* layers and fail loud when they are absent.
- **FR-6** — capability descriptor in each manifest.
- **FR-7** — dependency-check resolver (`resolve_layers`): the compatibility binding a downstream consumer declares against (sole-survivor / newest / fail-loud). Additive; no track is migrated onto it in P2 (the first real consumer, the redesigned self_similarity, lands in **P7**).
- **FR-13/FR-14 (data backbone only)** — each layer manifest carries a `rendering` descriptor + a precomputed `stats` summary, so the P5 rendering and P6 stats UI need no per-layer code. (The *UI* that consumes them ships in P5/P6.)
- **NFR-2/5/6** — provenance-stamped, atomic writes, reuse-over-recompute.

> `self_similarity` is **not** migrated in P2 (re-scope 2026-06-26). The dependency resolver lands here as additive infrastructure; the redesigned self_similarity that consumes it is **P7**. NFR-1 (byte-identical self_similarity) is retired.

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
  - The first real consumer to *declare* `layer_requirements` and read the bound layers is the redesigned `self_similarity` in **P7** — P2 lands the resolver as additive infrastructure with its own tests, not wired into any track.
- **Producibility + status (FR-4).** Make the layer tracks runnable through the normal run flow and visible:
  - **Run flow.** The HTTP run handler (`server.py:925`) and CLI carry the established chunk/embed param vocabulary (`chunk_mode`/`chunk_size`/`smart_unit`/`delimiters`/`grow_factor`/`remainder_ratio`/`embed_*`); the layer tracks adopt those exact param names (plus a `chunk_label` the handler forwards to `EmbeddingTrack`) so they are produced through the same surface as every other track, not a side door.
  - **Status.** `/analysis/status` enumerates `signals/{chunking,embedding}_*.json` and reports each layer (label + capability + stats + per-label `runInfo`), in addition to the registry's single track row — so plural label-keyed layers are visible.
  - **Provenance.** A layer run writes `manifests/{name}_{label}.run.json` (label derived from the returned manifest path), so each plural layer has its own resolved-param record rather than a single name-keyed file that successive runs overwrite.

### New artifacts
- `tracks/chunking_track.py`, `tracks/embedding_track.py` (the producer tracks).
- `tracks/requirements.py` (the resolver).
- `tracks/repeats.py` — the exact-repeat helpers (`find_exact_repeats` / `mask_repeats` + `STOPWORDS`) extracted from `self_similarity`, which now imports them back (one definition, no drift). Reusable by the future repeat-masking analysis; **not** wired into `EmbeddingTrack` in P2.
- `server.py` / `cli.py` run-flow + status changes for label-keyed producibility, provenance, and enumeration (FR-4).
- Tests: `test_chunking_track.py`, `test_embedding_track.py`, `test_layer_resolver.py`, plus FR-4 producibility/status tests.

### Tests
- Track discovery: both tracks appear via `registry.discover()` and in `/analysis/status`.
- Persistence: chunk/embedding layers written atomically with manifest + per-label `run.json`; reload round-trips.
- Plural coexistence: two chunk layers (different params) + two embedding layers coexist without path collision.
- Descriptor correctness: manifest carries the full descriptor; `analyzable_digest` matches the analyzable bridge digest.
- Resolver: compatible layer bound; incompatible (overlap mismatch, wrong dim, stale digest) → loud error.
- Producibility/status (FR-4): a layer is produced via the run flow with params and then appears in `/analysis/status` with its label/capability/stats. The repeat-mask extraction is covered by `self_similarity`'s existing suite staying byte-identical against the relocated helpers.

### Done criteria
- [ ] Both layer-tracks auto-discovered, runnable via HTTP + CLI with their params, persisted with capability + `rendering` + `stats` blocks + per-label provenance.
- [ ] Plural layers coexist and are enumerated in `/analysis/status`; resolver binds-or-fails-loud (never silently wrong).
- [ ] Exact-repeat helpers extracted to `tracks/repeats.py` and shared by `self_similarity` (byte-identical); repeat-masking as a standalone analysis is deferred (flag-only baseline, own design).
- [ ] Manifest-schema test confirms every layer carries well-formed `rendering` + `stats` blocks.
- [ ] Committed as a small additive series (track skeletons → resolver → producibility/status), each independently green. **(self_similarity is untouched — its redesign is P7.)**

### Risks & mitigations
- *Resolver becomes a hidden auto-invocation in disguise* (re-introducing the smell we're removing). **Mitigation:** the resolver is **fail-loud, require the layer to exist**; it never auto-produces. (The auto-produce-vs-fail-loud decision for the consumer is settled in P7's favour of fail-loud.)
- *Layer-track params collide with self_similarity's in the shared HTTP handler.* **Mitigation:** the layer tracks adopt the *same* param names the handler already forwards (`chunk_mode`, `chunk_size`, `embed_*`); the handler routes by `track_name`, so there is one vocabulary, not two.
- *Embedding-layer home ambiguity* (`cache/` vs `signals/`, Vision OQ#2). **Mitigation:** keep vectors in `cache/embeddings_{label}.db` but treat the **manifest** in `signals/` as the first-class result; the manifest is the source of truth either way.
- *In-memory `_running_jobs` (no job DB) loses layer-run state on restart.* **Mitigation:** on-disk per-label `run.json` is the authoritative provenance; status reads disk, not the in-memory dict, for completed layers.

### Sequencing
Needs P1 (coordinate-correct chunk producer + CLI parity). Unblocks P3 (embedding-as-analysis builds on `EmbeddingTrack`), P4 (analytics tracks reuse the layer-track pattern), **P7 (the self_similarity redesign consumes these producible layers via the resolver)**, and all Wave-1 reuse (future entity/dialogue/topic tracks declare layer dependencies instead of recomputing).

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

## P7 — `self_similarity` redesign (layer-consumer)

> **A ground-up redesign, not a migration.** The original P2 folded a *byte-identical migration* of `self_similarity` into the structural work. Review (2026-06-26) concluded that designing *to* the legacy monolith — preserving its inline chunk/embed/repeat-mask pipeline bit-for-bit — pulls the whole effort back toward the very coupling Wave 0 exists to remove. So the rework is promoted to its own phase and reconceived: `self_similarity` becomes an embedding-**agnostic**, **fail-loud layer consumer**, and the foundation for a *family* of similarity methods (self-similarity matrix, nearest-neighbour graphs, clustering, …) rather than one hard-wired matrix.

### Scope
- **Consumer, not producer.** `self_similarity` no longer chunks or embeds inline. It declares `layer_requirements` (`[chunk{overlapping:False}, embedding{dim:<method-dim>, chunk_layer_id:<bound chunk>}]`) and consumes the layers P2 makes producible (FR-4) through the P2 resolver (FR-7).
- **Fail-loud, not auto-produce.** If no compatible chunk/embedding layer exists, the track raises a descriptive `LayerResolutionError` naming the requirement and what was available — it does **not** silently chunk/embed on the user's behalf. Producing a layer is an explicit, separate user action (the layer tracks from P2).
- **Embedding-agnostic.** The track does not dictate the embedding model. Whatever embedding layer the user produced and bound is what the similarity math runs on; the method records the bound layer's `model_fingerprint` in provenance rather than choosing one.
- **A family, not a singleton.** The redesign factors the similarity computation behind a method interface so self-similarity-matrix, NN-graph, and clustering variants are siblings sharing the same layer-consumption contract.

### Mechanism
- Add `layer_requirements` to the `self_similarity` track and call `resolve_layers` (`tracks/requirements.py`) in its `extract`, replacing the inline `_get_chunks`/`_embed_chunks` path (`self_similarity.py:1138`/`:875`). The exact-repeat masking it relies on is, as of P2, a shared helper (`tracks/repeats.py`, imported back into `self_similarity`); the redesigned consumer honors the `repeat_mask` layer **P8** produces (flag-only: skip the masked chunks) instead of running the inline masking pass — so P7's repeat handling consumes P8's layer rather than re-deriving it.
- The similarity matrix math itself is preserved as one method implementation; the change is *where its inputs come from* (bound layers vs. inline computation), plus the method-interface factoring.

### Input-discovery endpoint (`GET /api/projects/{id}/self_similarity/inputs`)

Because the consumer binds layers by **explicit label** (one `{chunk_label, repeat_mask_label, embedding_label?}` bundle per chunk size) and users cannot type sha256 labels, the picker needs a read endpoint that enumerates the bindable layers, **pre-grouped and server-validated for coherence**. This is the read-side of the dependency system (Vision §3.3) — the third leg of the safe-reuse triad alongside `resolve_layers` (implicit discovery) and `resolve_explicit_bundle` (run-time binding); this endpoint is **explicit display-time discovery** (enumerate options, never auto-select).

- **Route / scope (decision, 2026-06-28):** consumer-scoped `…/self_similarity/inputs` today; field names are **family-neutral** (nothing prefixed `self_similarity_*`) so promotion to a generic `…/layers/consumable?for=<track>` is a *rename, not a redesign* for any chunk-rooted consumer. No query params in v1.
- **Coherence lives server-side (decision, 2026-06-28):** a single source of truth, no Python/TS drift. The endpoint computes coherence with the **same predicate** run-time binding uses (`chunk_layer_id` + `chunk_analyzable_digest` match), factored as `bundles.coherence_reason(dep, chunk_label, chunk_digest) -> str | None`: `_assert_coherent` raises on its truthy return, the endpoint routes truthy → `incompatible[]`. One predicate, two callers — discovery and binding can never disagree.
- **Response (200):** chunk-rooted, coherent dependents nested.
  - `chunk_layers[]`: `{label, size, bundle_ready, capability, stats, rendering?, runInfo?, repeat_masks[], embeddings[]}` — `repeat_masks`/`embeddings` are **coherent only**; `bundle_ready = len(repeat_masks) >= 1` (a bundle's `repeat_mask` is mandatory; embedding is required only for embedding-based metrics).
  - `methods[]`: `{name, requires_embedding}` — single source is `self_similarity._METHODS` (cosine/jaccard `True`; word_overlap/edit_distance `False`).
  - `incompatible[]`: `{kind, label, reason}` — layers that exist but bind to no present chunk layer, **surfaced not dropped** (NFR-3 fail-loud).
- **Errors:** `404` project-not-found (existing resolution dependency); `200` with `chunk_layers: []` when nothing is produced yet (discovery finding nothing is not an error); the endpoint **never `400`s on incoherence** — that fails loud at *run* time in `resolve_explicit_bundle`, discovery only reports.
- **Reuse:** enumerates via the existing `_layer_status_entries(project_dir, name)` (`server.py:189`) for `chunking`/`repeat_mask`/`embedding`; no new persistence, no new coordinate logic.

### Tests
- **Equivalence (the honest invariant).** *Same chunk layer + same embedding vectors → identical similarity math.* This is a 2-level test (the matrix produced from a bound layer equals the matrix the legacy inline path produced for the same chunks/vectors), **not** the retired NFR-1 "byte-identical at existing defaults from a single run" claim — a consumer redesign deliberately changes the entry workflow (you must produce layers first).
- **Fail-loud:** with no compatible layer present, `extract` raises `LayerResolutionError` and produces no output.
- **Agnosticism:** binding a different (compatible-dim) embedding layer changes the result and is recorded in provenance; the track never embeds on its own.

### Done criteria
- [ ] `self_similarity` runs only as a consumer: no inline `chunk_text`/`embed_texts` calls remain in its `extract` path.
- [ ] Absent layers → loud, descriptive failure (no silent chunk/embed).
- [ ] Equivalence test green: identical matrix for identical bound chunks + vectors.
- [ ] Similarity computation factored behind a method interface (room for NN-graph / clustering siblings).
- [ ] `GET …/self_similarity/inputs` returns coherent, server-validated bundles (`incompatible[]` surfaced, not dropped); coherence shares one predicate with run-time binding.
- [ ] Picker dialog builds `inputs` from the endpoint (no hand-typed labels); DotplotView Recompute retired (slider = cached-size view only); Playwright golden-path green.

### Risks & mitigations
- *Equivalence drift from the legacy matrix.* **Mitigation:** the matrix math moves verbatim into the method; the equivalence test gates the commit on identical output for identical inputs; do not merge on any divergence.
- *Redesign scope creep into Wave-1 similarity features.* **Mitigation:** P7 ships only the consumer-refactor + method-interface seam; concrete NN-graph/clustering methods are explicitly future work, not P7 deliverables.

### Sequencing
Needs P2's producible layers (FR-4) and the resolver (FR-7) — you cannot make a consumer *require* layers until users can produce them through the normal run flow. Independent of the P3–P6 user-facing surface; can land in parallel with them once P2 is in.

---

## P8 — Repeat detection + masking analysis

> **Repeat structure as a first-class, semi-independent analysis.** Promotes the exact-repeat logic — today buried in `self_similarity` (`self_similarity.py:1046`) and merely *extracted* to `tracks/repeats.py` in P2 — into a real analysis. Per the 2026-06-28 scoping, detection is **decoupled from chunking** (text-level, order-independent) and masking is a **consumer policy** applied two ways: hide repeats *before* chunking, or flag repeat-dominated chunks *after*. Flag-only throughout — the analysis records the mask; it never silently mutates a downstream result.

### Scope
- **FR-15** — `repeats` detection track (text-level, `depends_on=[]`): persists `signals/repeats_{label}.json` (repeat intervals + phrases), with open detection params.
- **FR-16** — `ChunkingTrack.hide_repeats`: optional pre-chunk excision of a named repeat layer, reusing the masking-excision substrate.
- **FR-17** — `repeat_mask` layer-track: post-chunk per-chunk flag layer (depends on a chunk layer + a repeat layer via the resolver), renderable + stats'd.
- **Open the masking constants (G2).** `min_words` / `min_occurrences` / `coverage_threshold` move from LOCKED in `repeats.py` (`repeats.py:27-29`) to user-tunable `Param`s, defaulting to 3 / 3 / 0.5 so `self_similarity` stays byte-identical.

### Mechanism
- **Decouple detection from chunks.** `find_exact_repeats` currently takes `chunks` only to build the word list and derive an n-gram ceiling from `chunk_size` (`repeats.py:69-75`). Add a text-level entry point that tokenizes the analyzable text directly and takes an explicit `max_phrase_len` param in place of the chunk-size ceiling — preserving the existing `min(max_phrase_len, token_count // 2)` cap (`repeats.py:75`) so behavior is unchanged at the default. `self_similarity` keeps calling the existing chunk-based path unchanged (`self_similarity.py:1046`) — its inline masking is byte-identical; only the new track uses the text-level path.
- **`repeats` track** (`tracks/repeat_track.py`): `ParameterizedTrack`, `output_type="signal"`, `depends_on=[]`, `layer_keyed=True` — structurally a sibling of `ChunkingTrack` (`tracks/chunking_track.py`). `extract(project)` runs on the analyzable view (so `runner.extract_masked` masks + remaps), maps each detected phrase to its character intervals, and writes a `SignalManifest` whose `segment_offsets` are the repeat intervals (analyzable → original after remap, G4) and whose `metadata` carries the phrases/counts, a `capability` (`{kind:"repeat-set", min_words, min_occurrences, max_phrase_len, analyzable_digest}`), a `rendering` (`{track_view:"repeat-band"}`), and a `stats` block (`{phrase_count, interval_count, coverage_pct}`). Label = `sha256(detection-params + analyzable_digest)[:16]`, mirroring `ChunkingTrack._label` (`chunking_track.py:148`).
- **Pre-chunk hiding (FR-16).** Add a `hide_repeats` param to `ChunkingTrack`. When set to a repeat label, `extract` loads that repeat layer's (original-coordinate) intervals and unions them into the project's excised set for this run. The excise/remap substrate is reused as-is — `Project.masked_intervals(extra_masked=…)` (`project.py:274`; `layout.py:319-373`) unions arbitrary flat disjoint spans, and `_complement_spans` + `OffsetMap` excise + remap them (`project.py:314`/`:341`) — so there is **no new coordinate math**. It does need new *plumbing*, though: today the `extra_masked` channel is hardwired to the verse layer (`project.py:299`) with no path for caller-supplied intervals, so P8 adds one — either an interval field on the per-run mask override (`set_mask_override`, `project.py:198`/`server.py:1016`, whose `MaskOverrideRequest` is today per-type/per-section toggles only) plus a branch in `masked_intervals`, or a dedicated `ChunkingTrack` hook that unions the repeat intervals into `extra_masked`. Because the run then chunks a repeat-excised view, its `analyzable_digest` (already in the label, `chunking_track.py:171`/`:189`) differs automatically, so the repeats-hidden chunk layer is a *distinct* content-addressed layer coexisting with the un-hidden one — no special label-casing. Embedding inherits hiding for free (it embeds whatever chunk layer it is bound to). `hide_repeats` is recorded in provenance params.
- **Post-chunk mask layer (FR-17).** A `repeat_mask` track (`tracks/repeat_mask_track.py`) declaring `layer_requirements = [chunk{...}, repeat-set{...}]`, resolved by `resolve_layers` (`tracks/requirements.py`, P2/FR-7). `extract` reads the bound chunk layer's `chunk_texts` + the bound repeat layer's phrases, runs `mask_repeats` (`repeats.py:102`) at the resolved `coverage_threshold`, and persists `signals/repeat_mask_{chunk_label}_{repeat_label}.json`: per-chunk `masked` booleans index-aligned to the chunk layer, a `rendering` (`{track_view:"chunk-band", shade:"masked"}`), and a `stats` (`{masked_count, masked_ratio, phrase_count}`). It is a signal-consumer (non-underscore requirements), so it runs on the bound layers' already-original coordinates — no remap. Per-label provenance + status enumeration ride the FR-4 rails already built in P2 (`_layer_status_entries`, `runner.provenance_name`).

### New artifacts
- `tracks/repeat_track.py` (detection), `tracks/repeat_mask_track.py` (post-chunk flag).
- `tracks/repeats.py`: a text-level `find_exact_repeats` entry point + the three constants promoted to track `Param`s (defaults unchanged).
- `tracks/chunking_track.py`: `hide_repeats` param + the new interval-injection plumbing into `extra_masked` (no label change needed — the excised-view digest carries it).
- Tests: `test_repeat_track.py`, `test_repeat_mask_track.py`, `test_chunk_hide_repeats.py`, plus a `self_similarity` byte-identity guard.

### Tests
- Detection: deterministic repeat set on a fixture with planted refrains; intervals in-bounds + remapped to original coords; open params change the result and are recorded in provenance; default params reproduce the phrases `self_similarity` finds today.
- Pre-chunk hiding: a chunk layer produced with `hide_repeats=<label>` excludes the repeated passages (its `chunk_texts` contain none of the repeat phrases) and is coordinate-correct (chunk spans map to the un-repeated original text); its label differs from the un-hidden chunking; both coexist.
- Post-chunk mask: `repeat_mask` over a chunk + repeat layer flags the same chunks `self_similarity`'s inline pass flags at the default threshold; the layer is index-aligned to the chunk layer (`len(masked) == chunk count`); the resolver fails loud if the repeat layer is absent.
- **`self_similarity` byte-identical:** its existing suite stays green — the now-`Param` constants default to the prior LOCKED values and its inline chunk-based path is untouched.
- Producibility/status (FR-4): both new tracks appear in `/analysis/status` with label + capability + stats + per-label provenance; plural repeat / mask layers coexist.

### Done criteria
- [x] `repeats` detection track runs text-level (no chunk dependency), persists the interval layer; detection params open + reported.
- [x] `ChunkingTrack.hide_repeats` produces a distinct, coordinate-correct repeats-hidden chunk layer reusing the masking excise/remap path (no new coordinate math; new interval-injection plumbing into `extra_masked`).
- [x] `repeat_mask` layer-track binds chunk + repeat layers via the resolver (fail-loud when absent) and persists a renderable, index-aligned per-chunk flag layer.
- [x] Masking constants are user-tunable `Param`s defaulting to 3/3/0.5; `self_similarity` byte-identical.
- [x] Full suite GREEN; committed as a small additive series (detection → hide-option → mask layer).

### Risks & mitigations
- *Text-level detection diverges from the chunk-based path and silently changes `self_similarity`.* **Mitigation:** `self_similarity` keeps its existing chunk-based call; the text-level entry point is a *new* function used only by the track; a byte-identity guard gates the commit.
- *Pre-chunk hiding re-implements excision instead of reusing it (coordinate risk).* **Mitigation:** union the repeat intervals into `extra_masked` and reuse `_complement_spans`/`OffsetMap` — the exact excise/remap path content-masking uses (new plumbing only, no new coordinate math); a test asserts hidden chunk spans round-trip to original coords (the G4 invariant).
- *`repeat_mask` index drift against its chunk layer.* **Mitigation:** the mask is keyed to `chunk_label` and index-aligned; a test asserts `len(masked) == chunk count` and per-index correspondence.
- *Opening the masking constants subtly shifts `self_similarity` defaults.* **Mitigation:** the `Param` defaults are exactly the prior LOCKED values; the byte-identity guard fails on any drift.

### Sequencing
Needs **P2** (the resolver FR-7 for `repeat_mask`'s requirements, the FR-4 producibility/status rails, and the `tracks/repeats.py` extraction). Independent of P3–P6. **Unblocks P7's repeat handling:** the redesigned `self_similarity` consumes the `repeat_mask` layer (flag-only: skip the masked chunks) instead of masking inline — so P8's mask layer is what makes P7's repeat consumption concrete. Parallelizable with P3/P4 post-P2; should land before (or with) P7's repeat step.

---

## P9 — Similarity-engine generalization (cross-text pre-stage)

> **The seam-lift that "passes" Wave 0.** P7 left `self_similarity` a single-operand consumer. P9 lifts the three single-operand assumptions baked into it (Vision §10.2) into parameters, so the cross-text build (P10) is additive — **without changing self-similarity's behavior**. This is the refactor that lets P1/P2/P7/P8 be declared *passed*. It ships no cross-text feature; it removes the constraints that would otherwise force a rewrite to add one.

### Scope
- **FR-18** — Operand abstraction: `LayerBundle` becomes one **Operand**; a `ComparisonSpec(op_a, op_b, methods)` binds two; self-similarity is the `op_a is op_b` instance.
- **FR-19** — Two-operand kernel + method capability: `SimilarityMethod.build(op_a, op_b)`; diagonal/symmetry/mirror-dedup conditional on `op_a is op_b`; `{representation, symmetric, supports_cross}` on each method.
- **FR-20** — Multi-axis output manifest: `axes[]` + `mode` + `symmetric` + `storage` discriminators; the self path emits length-1 `axes` that current readers consume unchanged.

### Mechanism
- **Operand (FR-18).** Reframe `LayerBundle` (`tracks/bundles.py:27`) as the per-operand unit — it already holds exactly one text's `{chunk, repeat_mask, embedding?}` + repeat phrases. Add a thin `ComparisonSpec` (frozen dataclass: `operand_a`, `operand_b`, `methods`) with a self constructor (`ComparisonSpec.self(operand)` → `op_a is op_b`). `resolve_explicit_bundle` (`bundles.py:92`) is unchanged for within-project operand loading; a second-project `resolve_operand` is **not** built here (P10).
- **Kernel (FR-19).** Change `SimilarityMethod.build` from `build(chunks, *, embeddings)` (`self_similarity.py:229`) to `build(op_a, op_b)`; the four existing builders read chunks/embeddings off the operands (with `op_a is op_b` for self). In `extract` (`self_similarity.py:980`), make `np.fill_diagonal(matrix, 1.0)` (`:998`), the `_is_self` diagonal guard in `_extend_alignment` (`:497`), and LASTZ mirror-dedup (`:738`) **conditional on `op_a is op_b`**. Add `symmetric`/`supports_cross`/`representation` to the `SimilarityMethod` dataclass (`:222`) — for the four current methods, `symmetric=True, supports_cross=True`, `representation ∈ {vector, token-set}`.
- **Manifest (FR-20).** In the master manifest (`self_similarity.py:1061`), add an `axes: [{role:"row"|"col", project_id, ref_sha256, segment_offsets, label}]` list plus `mode:"auto"`, `symmetric:true`, `storage:"dense"`. **Back-compat:** keep emitting the legacy top-level `segment_offsets`/`reference_sha256`/`dimensions` (mirroring `axes[0]`) so `DotplotView` + `/analysis/status` need no change; `axes` is purely additive. (Migrating `DotplotView` to *read* `axes` is a P10 concern.)

### Tests
- **Behavior byte-identical:** every existing `self_similarity` test stays green; the self matrix, alignments, and on-disk files are byte-identical (the seams' single-operand path is the default). This is P9's whole acceptance bar.
- **Seam unit tests:** `ComparisonSpec.self(op)` yields `op_a is op_b`; a method's `build(op, op)` equals the legacy `build(chunks, embeddings=…)`; the manifest carries a length-1 `axes` whose `axes[0]` mirrors the legacy headline fields.

### Done criteria
- [ ] `LayerBundle`→Operand + `ComparisonSpec` landed; self-similarity routes through `ComparisonSpec.self`.
- [ ] Method `build(op_a, op_b)` + `{symmetric, supports_cross, representation}` capability; diagonal/symmetry/dedup conditional on self.
- [ ] Manifest carries `axes[]`/`mode`/`symmetric`/`storage`; legacy headline fields still emitted (readers unchanged).
- [ ] Full suite GREEN; **self-similarity byte-identical** (the bar that declares P1/P2/P7/P8 passed).

### Risks & mitigations
- *Seam-lift silently changes self output.* **Mitigation:** byte-identity guard on every existing fixture; the single-operand path is the literal default of each conditional.
- *`axes[]` breaks a reader that assumed top-level `segment_offsets`.* **Mitigation:** legacy fields still emitted (additive `axes`); a reader-contract test asserts `DotplotView`'s fetch shape is unchanged.

### Sequencing
Needs **P7** (the consumer engine it generalizes) and **P8** (the `repeat_mask` layer the operand carries). Unblocks **P10**. Behavior-neutral, so it can land any time after P7/P8. **This is the gate for declaring P1/P2/P7/P8 passed.**

---

## P10 — Cross-text similarity & the synteny view (deferred)

> **The first non-auto mode.** With P9's seams lifted, cross-text comparison is additive: bind two operands, run the same methods, render against a root backbone. Deferred — scoped here so P9 doesn't constrain it. Implements **FR-21**.

### Scope (FR-21)
- A `ComparisonSpec` over **two distinct operands** (one designated **root**), bound via a `resolve_operand` that loads the second operand's layers (within a collection).
- **Cross-text alignment:** the LASTZ pass with the `_is_self` guard dropped = **Smith-Waterman local alignment** across the two chunk sequences, persisted as a B→root `OffsetMap`-bearing alignment layer.
- **Render:** cross-text similarity signals remapped operand→root (analysis-design-principles §4.1) ride the §3.4 rendering loop as root-frame tracks; `DotplotView` reads `axes` for the two-axis **synteny dot-plot**; alignment ribbons from the alignment layer.

### Mechanism (sketch)
- **Operand-pair binding.** `resolve_operand(scope, operand_ref)` generalizes `resolve_explicit_bundle`; the *cross* coherence predicate checks **shared embedding space** (`model_fingerprint`) across operands, not `chunk_layer_id`.
- **Alignment layer.** A `cross_alignment` artifact: query/target chunk spans + identity, exported as genuine PAF (`specs/paf-v0.1.md`). It *is* the B→root `OffsetMap`.
- **Synteny rendering.** `DotplotView` reads `axes[0]`=root, `axes[1]`=compared; a synteny panel stacks root-frame similarity tracks above the dot-plot (the UCSC/JAX idiom). Collection-scoped UI.

### Sequencing & gating
Needs **P9** (operand/kernel/manifest seams) and the **collection analytical tier** (deferred — the prerequisite for cross-text UI; Vision §8/§10.3). Independent of P3–P6. **Not** scheduled until the collection tier and P9 land.

---

## P11 — Scale & corpus modes (deferred)

> Probe (`q × corpus`) and corpus (N-way) modes + the compute strategy the dense kernels cannot reach. Implements **FR-22**. Scoped, not scheduled.

- **Candidate-generation → exact-score.** Two-stage similarity: ANN over embeddings (`SqliteVecStore.search`) or MinHash/LSH over shingles produces candidate pairs; exact scoring runs only on candidates. Sparse **top-k** output (`storage:"sparse-topk"`, the P9 discriminator) for the O((kN)²) regime the dense lexical/edit kernels (`_word_overlap_matrix`/`_edit_distance_matrix`, today O(N²) Python loops) cannot reach.
- **Corpus weighting.** Corpus-level IDF/BM25 to down-weight ubiquitous terms (a statistic auto-similarity never needed).
- **Block parallelism.** Structure per-pair/per-tile computation as independent tasks so a future executor parallelizes without restructuring.

---

## Cross-cutting concerns

### Testing strategy
- Every phase ends with the full backend suite GREEN (`-m "not external"`, JUnit-parsed). Baseline 636/636 at substrate-walk tip.
- Two recurring acceptance bars from the substrate walk are reused: **(1)** behavior byte-identical for valid inputs — P1 chunk lists, and (the weaker consumer form) P7's *same bound chunks + vectors → identical similarity matrix*; **(2)** validators fire only on impossible-today corruption. P2 itself is purely additive, so its bar is "every existing fixture stays green," not an equivalence claim.
- Frontend (P5/P6): unit/component tests **plus** in-browser feature verification (Playwright) — UI correctness is not claimed from type-check/tests alone. The P5 **plural** golden-path (two chunk layers + one embedding layer rendering as three simultaneous lanes) is the explicit proof of the FR-13 "always rendered, plural" commitment.

### Backward compatibility (NFR-1 *retired as a byte-identical claim*)
- No on-disk format is removed; new manifests/descriptors are additive. Existing analyses and artifacts keep working through P1–P6, which are additive. **NFR-1's original "`self_similarity` results byte-identical at existing defaults" claim is retired** in P7: the redesign makes `self_similarity` a layer-consumer, so the entry workflow deliberately changes (you produce chunk/embedding layers first). The honest, weaker invariant P7 holds is **same bound chunk layer + same embedding vectors → identical similarity matrix** — gated by the equivalence test, not a single-run default. Through P6 the only observable change is **new opt-in capability**; P7 changes how `self_similarity` is invoked.

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
| `self_similarity` numerics drift on redesign | P7 | High | Matrix math moves verbatim into the method; equivalence test gates the commit (same bound chunks + vectors → identical matrix); don't merge on any divergence |
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
| Text-level repeat detection diverges from the chunk-based path, silently changing `self_similarity` | P8 | Med | `self_similarity` keeps its chunk-based call; text-level entry point is new + track-only; byte-identity guard gates the commit |
| Pre-chunk hiding re-implements excision (coordinate risk) | P8 | Med | Union repeat intervals into `extra_masked`; reuse `_complement_spans`/`OffsetMap` — the exact content-masking excise/remap path (new plumbing only, no new coordinate math); test asserts hidden chunk spans round-trip to original coords (G4) |
| Opening the masking constants shifts `self_similarity` defaults | P8 | Low | `Param` defaults are the prior LOCKED values (3/3/0.5); byte-identity guard fails on any drift |
| Seam-lift (operand/kernel/manifest) silently changes the self-similarity matrix | P9 | High | Every existing `self_similarity` test stays green + on-disk files byte-identical; the single-operand path (`op_a is op_b`) is the default; equivalence is the whole acceptance bar — don't merge on any divergence |
| `axes[]` manifest addition breaks `DotplotView` / `/analysis/status` readers | P9 | Med | `axes` is purely additive; legacy top-level `segment_offsets`/`reference_sha256`/`dimensions` keep mirroring `axes[0]`, so no existing reader changes; migrating readers to consume `axes` is a P10 concern |
| Cross-text coordinate drift — operand mapped to the wrong root frame | P10 | High *(deferred)* | Alignment is an explicit `OffsetMap` into the root backbone (reuse the proven excise/remap math); every cross-text annotation round-trips operand→root→operand in test before render; no implicit frame inference |

---

## Sequencing & dependency summary

```
P1 (contract-lock + CLI parity)  ── no upstream; detachable, land anytime
        │  (coordinate-correct chunk producer + unified masked-run path)
        ▼
P2 (layer-tracks + capability/RENDER/STATS descriptors + resolver — additive infrastructure)
        │
        ├──────────► P3 (embedding viz suite: projection / distances / heatmap / clusters / lane)
        │                   │
        ├──────────► P4 (profile / integrity / dispersion + KWIC — parallelizable)
        │                   │
        ├──────────► P8 (repeat detection + hide-option + repeat_mask layer) ──► feeds P7's repeat step
        │                   │
        ├──────────► P7 (self_similarity redesign: fail-loud, embedding-agnostic layer consumer)
        │                   │
        └─────────┬─────────┴────► P5 (suite shell + native PLURAL layer-track rendering · FR-13)
                  │                          │
                  └──────────────────────────┴────► P6 (per-layer stats / distributions / viz · FR-14)

P7 + P8 ──► P9 (similarity-engine seam-lift: operand / kernel / manifest — behavior-neutral)
                  └──► GATE: declares P1 / P2 / P7 / P8 *passed* (self-similarity byte-identical)
                              │
                              ▼
                  P10 (cross-text + synteny view · deferred — also needs the collection tier)
                  P11 (scale / corpus modes · deferred)
```

- **P1** is a pure correctness no-regret; ship it first and alone if desired.
- **P2** is the linchpin; everything else reuses its layer-track + resolver pattern, and it now also carries the **render + stats manifest backbone** that makes P5 plural-rendering and P6 instant-stats possible. It is purely additive. Internal commits: track skeletons → resolver → producibility/status (each green). `self_similarity` is **not** touched in P2 — its redesign is **P7**.
- **P3, P4, P8, and P7 are independent** of each other and parallelizable post-P2 — except that **P8's `repeat_mask` layer feeds P7's repeat handling**, so P8 lands before (or with) P7's repeat step. P8 is purely additive (new `repeats` + `repeat_mask` tracks + a `ChunkingTrack.hide_repeats` option); it opens the masking constants but defaults them to today's values, so `self_similarity` stays byte-identical.
- **P5 + P6 are the terminal user-facing pair.** P5 makes *every* chunk/embedding layer render as a browser track (FR-13, plural-safe); P6 adds the stats/distribution/visualization drill-in (FR-14). Both need P2's backbone + P3's embedding data; P6 additionally needs P5's shell + layer manager to launch from.
- **P9 is the gate, not a feature.** It is behavior-neutral and sits after P7/P8; it lifts the three single-operand seams (operand/kernel/manifest, FR-18/19/20) so cross-text is later additive. Landing P9 with self-similarity byte-identical is what lets **P1/P2/P7/P8 be declared *passed***. **P10** (cross-text + synteny, FR-21) and **P11** (scale/corpus, FR-22) are **deferred** — P10 also waits on the collection analytical tier, and neither is scheduled; they are scoped only so P9 doesn't constrain them.

### Open questions carried from the Vision doc
The Vision doc's nine open questions (esp. layer naming, embedding-layer home, resolver strictness, first-UI-cut scope, CLI-fix timing) are **inputs to this plan, not resolved by it** — they are flagged at the relevant phase risk rows and await human review before P2/P5 lock their respective decisions.

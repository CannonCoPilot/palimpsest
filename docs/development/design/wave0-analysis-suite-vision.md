# Wave 0 Analysis Suite — Vision & Requirements

**Status:** Draft for human review
**Date:** 2026-06-24
**Companion:** [wave0-analysis-suite-plan.md](./wave0-analysis-suite-plan.md) (the phased development plan)
**Builds on:** [analysis-design-principles.md](./analysis-design-principles.md) (P1–P5 + the acceptable-default rule), [analysis-paradigm-audit-2026-06.md](../audits/analysis-paradigm-audit-2026-06.md) (the D1 guard-rails G1–G5), and the substrate contract-lock walk (masking / segmentation / verse-element / OffsetMap / analyzable-bridge).

---

## 1. Purpose & scope

Wave 0 is the **pre-analysis layer**: everything that happens to a newly imported or subsetted text *before* a literary analysis (self-similarity, sentiment, topics, …) consumes it. Today that layer is invisible and implicit — chunking and embedding are computed inside `self_similarity` and thrown away; the text's descriptive profile is never surfaced; and the only proof a text's coordinates are sound is that the test suite happens to pass.

This document reframes Wave 0 as a **suite of first-class, user-driven pre-analysis analytics** — chunking and embedding chief among them — and specifies what they are, how the user interacts with them, and which existing Palimpsest mechanisms they rest on. It is a vision-and-requirements doc, not an implementation guide; the phased build is in the companion plan.

**In scope:** chunking-as-analysis, embedding-as-analysis, descriptive/distributional statistics, data-quality/integrity reporting, positional/lexical exploration (KWIC, dispersion, collocations, duplicate detection), and the Stage-1 Analysis Suite UI that presents them.

**Out of scope (Wave 1+):** the literary analyses themselves (self-similarity, entities, coreference, dialogue, lexical, topics, sentiment, boundary detection, compartments, lithmm, alphabet, syntax, rqa, narrative-arc). Wave 0 *feeds* these; it does not replace them.

---

## 2. The paradigm shift

### 2.1 From hidden pipeline to declared analyses

The current model treats chunking and embedding as a **fixed pre-processing pipeline step** — one-shot, hidden, owned by a single consumer:

- `chunk_text(...)` is called in exactly one place: `self_similarity.py:1141`.
- `embed_texts(...)` is called in exactly one place: `self_similarity.py:875`.
- `ChunkingConfig` / `EmbeddingConfig` are constructed only inside `self_similarity`.
- The chunk list and embedding vectors live in `extract()`-local dicts (`_chunks_cache`, `_embeddings_cache`) and are discarded when the call returns. Only the on-disk SQLite-vec cache (`cache/embeddings_{label}.db`) survives, and only `self_similarity` knows it exists.

The new model treats chunking and embedding as **two related-but-independent analyses** in their own right:

- The user runs them deliberately, under chosen methods and parameters.
- Each **reveals information about the text** (segmentability, semantic geography) worth seeing on its own.
- Each **persists a reusable layer** that other analyses may consume.
- A downstream analysis that needs chunks or embeddings **declares a dependency** on a specific layer (checked for compatibility) instead of silently triggering its own hidden invocation.

This dissolves the "where/when to invoke" tension that motivated this work: chunking/embedding are invoked the same way any analysis is (user-run, runtime params, persisted result), and consumers reuse layers rather than recompute them.

### 2.2 Why this is the right model (and why it is cheap)

This reframing is consistent with — and completes — the principles already adopted:

- **D1 posture (user-defined-at-runtime).** `chunking.py` already declares "every parameter is user-defined at runtime; no hidden defaults, no silent clamps." Making chunking a user-run analysis is the natural home for that posture, not a contradiction of it. We do **not** reverse D1 by fixing a canonical chunking at import; the user keeps full runtime control.
- **Design principle P4 (flexibility for novel approaches).** Plural, named, comparable chunk/embedding layers — rather than one blessed representation — is exactly the flexibility P4 asks for.
- **Design principles P1/P3/P5 (transparency, auditability, user-sees-everything).** A persisted layer with provenance (`{track}.run.json`) and a visible descriptor is transparent and auditable in a way an `extract()`-local dict can never be.

Critically, **the reframing is architecturally cheap**, because a chunk/embedding layer *is already* expressible as a Palimpsest **track**:

- A track is "a named, parameterized, provenance-stamped, offset-anchored layer with a manifest" — precisely a chunk layer (`{index, start, end, text, words}` records) or an embedding layer (vectors keyed to a chunk layer).
- The persistence machinery already exists: `write_track()` (`annotation/serializer.py:21`, atomic), `write_signal()` (`formats/signals.py:63`, atomic), `write_run_provenance()` (`atomic.py:47`), and the SQLite-vec store (`vectorstore/sqlite_vec.py`).
- Track discovery is automatic: `TrackRegistry.discover()` (`tracks/registry.py:88`) finds any module in `palimpsest.tracks/` that satisfies the `TrackExtractor` protocol (`tracks/base.py:19`) — zero registration boilerplate.
- The coordinate machinery already remaps a track's output back to original coordinates after a masked run (`_extract_masked` → `_remap_signal_dir` → `remap_signal_data`, hardened by G4).

So Wave 0 is mostly **promotion and exposure of machinery that already exists**, not a new subsystem.

### 2.3 The load-bearing idea: capability descriptors + dependency checks

If layers are reusable, reuse must be **safe, not silently wrong**. A `self_similarity` run that needs non-overlapping word chunks must not silently consume a `slide`-overlap chunk layer and produce a corrupted matrix. The mechanism that makes reuse safe is a **capability descriptor** on each layer plus a **dependency check** at the consumer:

- Every chunk layer records a typed descriptor: `mode`, `overlapping` (bool), `covers_full_text` (bool), `unit` (word/verse/paragraph/sentence/char), `size`, and the analyzable-text digest it was computed against.
- Every embedding layer records: the chunk-layer identity it embeds, `provider`, `model`, `dim`, and a model fingerprint.
- A consumer declares what it requires (e.g. "a non-overlapping chunk layer"; "an embedding layer at dim 2560"). On run, the system either finds a compatible layer and reuses it, or **fails loud with a clear reason** — never silently consuming an incompatible one.

This is the same fail-loud, anti-Goodhart posture the audit established for parameters (G2) and coordinates (G4), applied to **layer reuse**.

### 2.4 Contract-lock extension (the no-regret hardening)

Independent of the architecture, one gap closes immediately: chunk **output coordinates** are currently trusted, not validated. `chunk_text` (`chunking.py:290`) returns each chunker's records directly; `ChunkingConfig` validates *parameters*, never *output*. Chunking is the only substrate-boundary producer not yet under the contract-lock that masking, segmentation, verse/element detection, the OffsetMap, and the analyzable bridge now enjoy. Wave 0 brings it under the same declare→enforce→lock regime: chunk records must be in-bounds in analyzable coordinates, index-sequential, ordered, anchored to the source text, and (for non-overlapping modes) disjoint — whitespace gaps between chunks are allowed, so this is a disjoint ordering, not a gapless partition. This is valuable regardless of which architectural option is chosen, and is therefore the first deliverable.

---

## 3. Core concepts

### 3.1 Layer-tracks

A **layer-track** is a track whose purpose is to produce a reusable representation rather than a literary finding:

| Layer | Records | On-disk | output_type |
|---|---|---|---|
| Chunk layer | `{index, start, end, text, words}` per chunk, in original coordinates after remap | `signals/chunking_{label}.json` (manifest with `segment_offsets`) | `signal` |
| Embedding layer | one vector per chunk, keyed to a chunk layer | `cache/embeddings_{label}.db` (SQLite-vec) + `signals/embedding_{label}.json` (manifest) | `signal` |

Both implement the existing `TrackExtractor` protocol and are discovered automatically. Both are written atomically and stamped with `{track}.run.json` provenance. Both appear in `/analysis/status` like any other track.

### 3.2 Capability descriptor

A small typed record, written into the layer's signal manifest `metadata`, that declares what the layer *is* and therefore what it *can be reused for*. It is the contract that makes a layer a first-class, shareable asset rather than an opaque blob. (Schema in §6, FR-6.)

### 3.3 Dependency declaration & check

A consumer track declares a typed requirement (not just a track name) and the system resolves it against available layers, reusing a compatible one or failing loud. This generalizes the existing `depends_on` list (`tracks/base.py:38`, today a bare `list[str]` with the underscore-prefixed virtual-dependency convention, e.g. `"_embeddings"` = pre-satisfied).

**Typed requirement schema.** A consumer declares `layer_requirements: list[LayerRequirement]`, where each requirement is a predicate over the candidate layer's capability descriptor (§3.2):

- `kind`: `"chunk"` | `"embedding"`;
- `constraints`: a set of descriptor-field predicates, e.g. for a chunk requirement `{overlapping: False, covers_full_text: True, unit: "word"}`; for an embedding requirement `{dim: 2560, provider: "mlx"}`;
- `digest_match`: `True` to require the layer's `analyzable_digest` equal the consumer's current analyzable text (the default — prevents reusing a layer computed against different text).

**Resolution algorithm** (run before `extract`, in the run lifecycle): enumerate the project's persisted layer manifests of the requested `kind`; keep those whose descriptor satisfies every constraint and (if `digest_match`) whose digest matches; if exactly one survives, bind it; if several, bind the most recent (by `run.json` timestamp) and record the choice in provenance; if **none**, raise a descriptive error naming the requirement and what was available — never silently consume an incompatible layer, never silently auto-produce one (auto-production is a separate, explicit action — see §9 OQ#3). `self_similarity` expresses its need as `[chunk{overlapping:False}, embedding{dim:<model-dim>, chunk_layer_id:<bound chunk>}]`.

### 3.4 Every layer is a viewable browser track (the rendering commitment)

A layer that is computed but not *seen* is no better than today's discarded `extract()`-local. So a firm product commitment: **every chunk layer and every embedding layer the user produces is, by default, rendered as a browser track** — and because the user works with *plural* layers (multiple chunkings, multiple embeddings, side by side), rendering must be **automatic and N-safe**: producing the fifth chunk layer must cost zero new frontend code and must coexist visually with the other four.

The mechanism that makes this true without bespoke per-layer code is a **render descriptor** carried in every layer's manifest (alongside the capability descriptor of §3.2). It tells the frontend *how to draw this layer as a track* — declaratively, so the track-rendering loop draws any layer it finds:

- A **chunk layer** declares `rendering = {track_view: "chunk-band", ...}` → the existing `OverviewBar` lane machinery draws its `segment_offsets` as a chunk ribbon over the text.
- An **embedding layer** declares `rendering = {track_view: "embedding-lane", encoding: "cluster" | "pc1" | "nn-density", projection_ref}` → a 1-D per-chunk encoding (cluster id / first principal component / neighbor density) is drawn as a colored lane over the text, *and* the layer offers its 2-D scatter in the Representations panel. An embedding is therefore visible **both** as an in-text track lane **and** as a semantic-space scatter.
- Other layer kinds ride the same loop with no new dispatch code: a **repeat layer** (§4.6) declares `rendering = {track_view: "repeat-band"}` (its repeated stretches shaded over the text), and a **repeat-mask layer** declares `rendering = {track_view: "chunk-band", shade: "masked"}` (the repeat-dominated chunks shaded). The point of a data-driven loop is exactly that the kinds it draws are open-ended.

Because the descriptor lives in data, the frontend iterates the track list from `/analysis/status` and renders each layer by its `rendering.track_view`. Plural layers become plural lanes; the layer manager (§5) controls their order, visibility, and overlay. This is the contract that upgrades Wave-0 layers from "appears as a status-list row" to "appears as a drawn track."

### 3.5 Every layer carries summary statistics & distributions

Alongside the render descriptor, each layer manifest carries a precomputed **`stats` block** — a small summary computed once at extract time so the user can *navigate to the numbers instantly*, without re-running anything:

- a **chunk layer**'s stats: chunk count, coverage %, overlap ratio, chunk-length summary (mean/median/min/max, words & chars), and boundary-alignment fractions (what share of chunk edges land on sentence / paragraph / verse / element boundaries);
- an **embedding layer**'s stats: vector count, dim, model fingerprint, and cheap geometry summaries (mean pairwise distance, cluster count if clustered).

Heavier, interactive **distributions** (full length histograms/ECDFs, pairwise-distance distributions, similarity heatmaps, projections) are computed on demand from the persisted layer and rendered in the per-layer stats panel (§5), under a **selectable set of visualization options**. The summary is always-present and instant; the distributions are a click away.

---

## 4. The Wave 0 analytics catalog

### 4.1 Chunking as an analysis — "how is this text segmentable?"

**Methods** (today, in `chunking.py`): `word`, `slide` (overlap), `punctuation` (delimiters), `verse` (verse spans), `smart` (grow over verse/paragraph/sentence units). **Candidate additions:** paragraph-unit, sentence-unit, fixed-char, regex-delimited, and (later) cohesion-based boundaries (TextTiling-style).

**Parameters:** per the D1 posture — fully required, validated, no defaults — already enforced by `ChunkingConfig`.

**What it reveals (the analysis payload):**
- chunk-length distribution (words and chars), count, overlap ratio, coverage of the analyzable text;
- **boundary alignment** — what fraction of chunk edges coincide with sentence / paragraph / verse / element boundaries (a genuine signal about the text's natural granularity; `smart` mode already implicitly chases this);
- the chunk **ribbon** rendered over the text (the existing barcode idiom).

**How it surfaces (per §3.4–3.5):** every chunk layer is **rendered as a track ribbon over the text by default**, and carries a `stats` summary (count / coverage / overlap / length-summary / boundary-alignment) navigable instantly, with length **histogram / ECDF / by-element violin** distributions a click away in the per-layer stats panel (§5). Multiple chunk layers render as multiple coexisting ribbons for overlay/compare.

**Why it's an analysis, not a setting:** boundary-alignment and length-distribution are descriptive findings about the text. Two chunkings of the same text are *comparable artifacts*, not interchangeable defaults.

### 4.2 Embedding as an analysis — "what does the semantic space look like?"

**Inputs:** a chunk layer + an embedding model (MLX Qwen3-Embedding-4B @ dim 2560 today; alternative providers/models/dims selectable).

**What it reveals (the embedding visualization suite):**
- a 2-D **projection** (PCA default; UMAP optional — see plan) of selected/filtered chunks, colorable by structure (book/chapter/verse) or by another layer (sentiment/topic);
- **pairwise-distance** and **nearest-neighbor-distance** distributions (histograms);
- a **similarity heatmap**; nearest-neighbor exploration; **clustering** with cluster-size summary; outlier surfacing;
- **filtering before embedding** — embed only one book, only chapters, only chunks matching a query.

**How it surfaces (per §3.4–3.5):** an embedding layer renders **both** as an in-text **track lane** (a 1-D per-chunk encoding — cluster id / first principal component / neighbor density — drawn over the text like any track) **and** as the 2-D **scatter** in the Representations panel. Its `stats` summary (vector count / dim / model / mean pairwise distance / cluster count) is instant; the full visualization suite above is the per-layer stats panel's selectable view set. Plural embedding layers coexist as plural lanes + comparable scatters.

**Persistence:** the vector layer lives in the SQLite-vec store, content-addressed (so it survives across runs and projects); a manifest records provenance + descriptor (+ render descriptor + stats summary).

### 4.3 Descriptive & distributional statistics — "know your text"

Cheap, mostly auto-computed on open:
- counts: tokens, types, vocabulary size, hapax legomena; lexical diversity (TTR, MATTR, MTLD, Yule's K);
- length distributions: word / sentence / paragraph / chunk (histogram + ECDF + by-element-type violins);
- frequency structure: rank-frequency **Zipf** fit (log-log + slope), **Heaps'** vocabulary-growth curve, function-word profile (the stylometric base), n-gram tables, stopword ratio;
- readability indices as *descriptive* signals (never normative scores).

### 4.4 Data-quality / integrity QC — the contract-lock's second dividend

- a **substrate integrity report**: run the contract validators built in the substrate walk (masking partition, segment anchoring, section forest, OffsetMap round-trip, analyzable↔original length agreement) and present green/violations to the user. This makes the invariants *legible* — "is this text's coordinate substrate sound?";
- encoding / normalization sanity (non-ASCII, control characters, mojibake), language / mixed-language detection;
- segmentation sanity (degenerate or oversized paragraphs);
- **near-duplicate / repeat-passage finder** (surface the repeat-masking signal as a report — see §4.6);
- masking-coverage summary (% masked by type) and structural-count summary.

### 4.5 Positional / lexical exploration — interactive, layer-producing

- KWIC / concordance; **dispersion plots** (where a term lives across the document — a lexical barcode); collocations (PMI / log-likelihood); burstiness.

### 4.6 Repeat detection & masking as an analysis — "what does this text repeat?"

Formulaic, frequently-repeated passages — scripture refrains, legal boilerplate, liturgical formulae, epic epithets — are a genuine structural property of a text, and they distort any analysis that treats every passage as equally informative (a similarity matrix inflates; an embedding space clumps). Today this is handled invisibly inside `self_similarity` (`self_similarity.py:1046`), which detects exact repeats and skips the dominated chunks in its matrix. Wave 0 promotes it to a first-class analysis with its own layers — and, per the 2026-06-28 scoping, **decouples detection from chunking** so the two are semi-independent.

**Detection is text-level, not chunk-level.** A `repeats` track runs on the analyzable text alone (`depends_on=[]`, masked + remapped like chunking) and finds the contiguous word-sequences (n-grams from `min_words` up to `max_phrase_len`) that recur at least `min_occurrences` times across the whole document (`find_exact_repeats`, `tracks/repeats.py:53`). It persists the repeat **intervals** (character spans) as a layer — `signals/repeats_{label}.json` — with the phrases and their counts. Because it reads only text, it is **order-independent**: run it before or after any chunking.

**Masking is a consumer policy, applied two ways:**
- **Pre-chunk hiding (opt-in).** If a repeat layer exists, a chunking (or embedding) run may *hide* it: the repeat intervals are excised from the analyzable stream before chunking, so the chunker never sees the repeated passages. This rides the **same excise/remap path the codebase already uses for content masking** — `Project.masked_intervals(extra_masked=…)` → `_complement_spans` → `OffsetMap`, which already unions and remaps arbitrary disjoint spans — so there is no new coordinate *math*; it does need new *plumbing* to feed the repeat intervals into the excised set, since today's `extra_masked` channel is hardwired to the verse layer (`project.py:299`). A repeats-hidden chunk layer is a distinct, content-addressed layer (its excised analyzable text has a different digest) that coexists with the plain one.
- **Post-chunk flagging (persisted mask layer).** Given a chunk layer + a repeat layer, a `repeat_mask` layer records, per chunk, whether more than `coverage_threshold` of its content words are covered by repeats (`mask_repeats`, `tracks/repeats.py:102`). It renders as a shaded chunk-band and is a *declarable, optional* dependency a downstream analysis honors (skip masked chunks) or ignores — never a silent mutation.

**Parameters are open, defaulting to today's behavior.** The three masking constants currently locked in `repeats.py` (`min_words=3`, `min_occurrences=3`, `coverage_threshold=0.5`) become user-tunable, validated `Param`s — they change which text is excluded from analysis, so by the acceptable-default rule (G2) they are declared and reported, not hidden. Their defaults reproduce `self_similarity`'s current results exactly.

**Why it's an analysis, not a setting:** the repeat structure is itself a finding ("this text is 40 % formulaic refrain"), and two maskings of the same text — different thresholds, hidden vs. flagged — are comparable artifacts, not interchangeable defaults.

### 4.7 Honesty constraint on every Wave 0 analytic

All statistics are framed **descriptive-of-this-text**, with explicit caveats when there is no reference corpus to be inferential against — consistent with the §5 consumption-honesty pass. No faked progress, no inferential claims dressed as descriptive ones.

---

## 5. The Stage-1 Analysis Suite (UX vision)

A workbench presented immediately after import/mask, for a text *or* a subtext, organized around **layers as the currency of work**.

- **Header:** text identity + a **substrate-integrity badge** (one click runs the contract validators as a report). The first thing the user sees is "are my coordinates sound?"
- **Profile tab** (auto, cheap, on open): the descriptive-stats dashboard + distribution thumbnails + data-quality flags. "Know your text at a glance."
- **Representations tab** (the chunking + embedding workbench): produce / inspect / compare chunk and embedding layers. By §3.4 commitment, **every layer here auto-renders as a browser track** — chunk ribbons and embedding lanes over the text — with plural layers coexisting for overlay/compare. A **layer manager** lists every layer with its provenance, capability descriptor, and render/visibility/order controls. Selecting any layer opens its **per-layer stats panel** (§3.5): the instant `stats` summary plus a **visualization-option selector** over its distributions — for a chunk layer: length histogram / ECDF / by-element violin / boundary-alignment bar; for an embedding layer: 2-D projection scatter / pairwise- and NN-distance histograms / similarity heatmap / cluster summary — each colorable by structure or by another layer. This is the "quickly navigate to summary statistics, distributions, and visualization options" surface.
- **Explore tab** (interactive proto-analyses): **dispersion** (a layer-producing positional track) plus **KWIC, collocations, and the duplicate-finder** (lightweight *transient queries* rendered inline — not persisted layers; see plan P4). Each is a fast lexical lookup over the analyzable text.
- **Composition affordances** threaded throughout: "use this layer in →" (hand a layer to a Wave-1 analysis); "compare layers"; "filter → embed → project."
- **Reports:** each analysis emits a printable report (feeding the documentary tier) alongside the raw layer, so the suite is exploratory *and* on-the-record.

### 5.1 Example user journeys (combinations)

- *Granularity sweep:* run `word-7`, `slide-10`, and `smart-paragraph-50` chunk layers; overlay their ribbons; see which respects the text's structure → hand the winner to `self_similarity`.
- *Representation compare:* embed the same chunk layer with two models; project both; confirm the semantic geography is model-stable before trusting any downstream similarity result.
- *Filtered semantics:* filter to footnotes only → embed → project colored by which chapter they annotate → discover whether apparatus clusters by content or by position.

---

## 6. Requirements

### Functional requirements

- **FR-1 — Chunk-output contract.** `chunk_text` output must satisfy and self-validate a chunk contract: each record in-bounds in analyzable coordinates (`0 <= start < end <= len(text)`), index-sequential from 0, ordered by start, anchored (`chunk["text"] == text[start:end]`), and **disjoint** for non-overlapping modes (`word`, `punctuation`, `verse`, `smart`) — `chunk[i].start >= chunk[i-1].end`. Disjoint is **not** a partition: chunkers snap to word/content boundaries and skip inter-chunk whitespace, so consecutive chunks may have whitespace gaps and coverage is not total. `slide` is overlap-tolerant (non-decreasing starts only). A violation raises `ValueError` at the producer. (Mirrors `_validate_segments`.)
- **FR-2 — Chunking is a first-class track.** A `ChunkingTrack` implements `TrackExtractor` (`output_type="signal"`), is auto-discovered, runs through `_extract_masked` (so chunk offsets remap to original coordinates), and persists `signals/chunking_{label}.json`.
- **FR-3 — Embedding is a first-class track.** An `EmbeddingTrack` (`output_type="signal"`, depends on a chunk layer) persists vectors to the SQLite-vec store + a manifest, reusing the existing labeled-cache mechanism.
- **FR-4 — Layers are persisted, named, and listed.** Each layer appears in `/analysis/status` with its provenance (`{track}.run.json`) and descriptor; the user can list, inspect, compare, and delete layers.
- **FR-5 — Plural layers coexist.** Multiple chunk/embedding layers (different methods/params/models) for one project must coexist without collision (label-keyed paths).
- **FR-6 — Capability descriptor.** Each chunk-layer manifest records `{mode, overlapping, covers_full_text, unit, size, analyzable_digest}`; each embedding-layer manifest records `{chunk_layer_id, provider, model, dim, model_fingerprint}`.
- **FR-7 — Dependency check.** A consumer declares a typed requirement; the resolver reuses a compatible layer or fails loud with a descriptive reason. The resolver ships as additive infrastructure; the first consumer to *declare* a requirement against it is the redesigned `self_similarity`, reconceived as an embedding-agnostic, fail-loud **layer consumer** that requires a chunk layer + embedding layer instead of computing them inline (delivered as its own phase — see the Development Plan's **P7** — not an in-place migration).
- **FR-8 — Descriptive-statistics analytics.** A `ProfileTrack` (or equivalent) computes the §4.3 statistics and exposes them as a report + distribution data.
- **FR-9 — Data-quality / integrity report.** A user-runnable report executes the substrate contract validators and the §4.4 QC checks and returns pass/violation results.
- **FR-10 — Positional/lexical analytics.** KWIC, dispersion, collocations, and duplicate-finder are available as Wave-0 analyses (layer-producing where applicable).
- **FR-11 — Stage-1 Suite UI.** Profile / Representations / Explore surfaces + a layer manager, integrated into the existing app frame, hosting the FR-13 track rendering and FR-14 stats panels.
- **FR-12 — CLI/HTTP parity.** The CLI `analyze` path applies masking + remap (via `_extract_masked`) so a chunking analysis run from the CLI produces correct (masked, original-coordinate) output. (Closes a known existing gap.)
- **FR-13 — Native, plural layer-track rendering.** Every chunk and every embedding layer renders as a browser track by default, driven by a `rendering` descriptor in the layer manifest (no bespoke per-layer frontend code). Chunk layers render as ribbons; embedding layers render as a 1-D in-text lane (cluster / PC1 / NN-density encoding) **and** a 2-D scatter. Multiple layers of either kind coexist as multiple lanes; the layer manager controls order, visibility, and overlay. Adding the Nth layer costs zero new rendering code.
- **FR-14 — Per-layer statistics, distributions & visualization options.** Each layer manifest carries a precomputed `stats` summary (chunk: count / coverage / overlap / length-summary / boundary-alignment; embedding: count / dim / model / mean-pairwise-distance / cluster-count), navigable instantly. Selecting a layer opens a stats panel with a **selectable visualization set** over on-demand distributions — chunk: length histogram / ECDF / by-element violin / boundary-alignment bar; embedding: projection scatter / pairwise- & NN-distance histograms / similarity heatmap / cluster summary — colorable by structure or by another layer.
- **FR-15 — Repeat detection is a first-class, text-level track.** A `repeats` track (`output_type="signal"`, `depends_on=[]`) runs through `_extract_masked` on the analyzable text — independent of any chunk layer — detects exact-repeat phrases via `tracks/repeats.py`, and persists `signals/repeats_{label}.json` with the repeat intervals as `segment_offsets` (original coordinates after remap) plus the phrases and their counts. Detection params (`min_words`, `min_occurrences`, `max_phrase_len`) are user-tunable, validated, and default to today's behavior. The track is order-independent of chunking (may be run before or after).
- **FR-16 — Pre-chunk repeat hiding.** `ChunkingTrack` accepts an optional `hide_repeats=<repeat_label>`. When set, the named repeat layer's (original-coordinate) intervals are unioned into the project's masked set for that run, so the analysis view the chunker sees has the repeated passages excised — the chunker, and any embedding built on the resulting chunk layer, never sees them. This reuses the existing excise/remap path (`Project.masked_intervals(extra_masked=…)` → `_complement_spans` → `OffsetMap`, `project.py`/`layout.py`, which already unions and remaps arbitrary disjoint spans), so it adds **no new coordinate math** — but it does require new *plumbing* to inject the intervals, because today `extra_masked` is hardwired to the verse layer (`project.py:299`): P8 adds either an interval channel on the per-run mask override (`set_mask_override`, `project.py:198`/`server.py:1016`, today toggles-only) plus a branch in `masked_intervals`, or a dedicated `ChunkingTrack` hook that unions the repeat intervals into `extra_masked`. Because the run chunks a repeat-excised view, its `analyzable_digest` already differs, so the repeats-hidden chunk layer is a distinct content-addressed layer coexisting with the un-hidden one. Coordinate-safe by construction (the view's OffsetMap remaps chunk spans past the excised gaps); `hide_repeats` is recorded in provenance.
- **FR-17 — Post-chunk repeat-mask layer.** A `repeat_mask` layer-track declares `layer_requirements` for a chunk layer + a repeat layer (resolver-checked, FR-7) and persists `signals/repeat_mask_{chunk_label}_{repeat_label}.json`: a per-chunk `masked` boolean (true when more than `coverage_threshold` of the chunk's content words are covered by repeats), index-aligned to the chunk layer, plus a `rendering` descriptor (shaded chunk-band, FR-13) and a `stats` summary (`masked_count` / `masked_ratio` / `phrase_count`, FR-14). `coverage_threshold` is user-tunable (default 0.5). Flag-only: the layer records the mask; honoring it is a consumer's declared policy, never a silent mutation.

### Non-functional requirements

- **NFR-1 — Backward compatibility (additive layers; `self_similarity` equivalence reframed).** No on-disk format is removed and every new manifest/descriptor is additive, so existing analyses and artifacts keep working. The original "`self_similarity` byte-identical at existing defaults" guarantee is **retired**: because `self_similarity` is redesigned into a *layer consumer* (P7), its entry workflow deliberately changes — a user produces chunk/embedding layers first. The honest, weaker invariant is **same bound chunk layer + same embedding vectors → identical similarity math**, enforced by an equivalence test rather than a single-run default.
- **NFR-2 — Provenance & auditability (P1/P3).** Every layer is provenance-stamped via the existing `{track}.run.json` mechanism; no output-affecting value is hidden (acceptable-default rule).
- **NFR-3 — Fail-loud (G2/G4/G5).** Invalid params → 400; incompatible layer reuse → loud error; coordinate misplacement → `UnmappedCoordinateError`. No silent fallback.
- **NFR-4 — Cost transparency.** Embedding is expensive; the UI must surface a pre-run cost estimate (chunk count → vectors → ~time) and never auto-run embedding. **This estimate does not exist today** — it is audit remediation item D2-7 (the param dialog currently shows no chunk-count / matrix-dim / memory estimate), so it is *new work delivered in this plan*, not the reuse of an existing rail.
- **NFR-5 — Atomic, transactional writes (G3).** Layer artifacts use `atomic_write_*` and stage-then-commit; partial failures leave no half-written layer.
- **NFR-6 — Performance.** Reuse over recompute: a compatible cached layer is reused; the content-addressed cache survives across runs/projects.
- **NFR-7 — Honest visualization.** Descriptive-not-inferential framing; no faked progress; caveats surfaced (consistent with §5 consumption-honesty).

---

## 7. Integration with existing architecture & paradigms

| Wave 0 element | Rests on (existing mechanism) |
|---|---|
| Chunk/embedding layer-tracks | `TrackExtractor` protocol (`tracks/base.py:19`) + auto-discovery (`tracks/registry.py:88`) |
| Layer persistence | `write_signal` (`signals.py:63`), `write_track` (`serializer.py:21`), SQLite-vec (`sqlite_vec.py`) |
| Provenance | `write_run_provenance` → `{track}.run.json` (`atomic.py:47`); `_track_run_info` (`server.py:139`) |
| Param posture | `ParameterizedTrack` (`params.py:177`), `ChunkingConfig`/`EmbeddingConfig` (already fail-loud) |
| Masked, coordinate-correct runs | `_extract_masked` (`server.py:236`) + OffsetMap remap (`derive.py`, G4) |
| Dependency ordering | `depends_on` + `dependency_order()` Kahn sort (`registry.py:52`) |
| Status & UI feed | `/analysis/status` (`server.py:930`) → `TrackStatus[]` (AnalysisPanel) |
| Chunk ribbon | `OverviewBar` SVG-lane pattern (`TrackBarcode` is its internal render fn, `OverviewBar.tsx:86`) + new `overviewBarRendering.type` |
| Embedding projection | `DotplotView` canvas/fetch pattern, mirrored for a 2-D scatter |
| Native plural rendering (FR-13) | manifest `rendering` descriptor → frontend track loop dispatches on `overviewBarRendering.type`; plural lanes via existing multi-track `OverviewBar` |
| Per-layer stats & distributions (FR-14) | manifest `stats` block (instant) + on-read distribution endpoints; `CooccurrenceHeatmap.tsx` (already exists) + `DotplotView` mirrors + `d3-shape` for curves |
| Layer manager | the `@dnd-kit/*` drag-reorder pattern already used in `TrackPanel.tsx` (reuse, not a new dep) |
| Repeat detection & masking (§4.6) | `tracks/repeats.py` (exact-repeat helpers, extracted in P2) + the `Project.masked_intervals(extra_masked)` → `_complement_spans` → `OffsetMap` excise/remap path (`project.py`/`layout.py`) for pre-chunk hiding (reuses the coordinate math; adds new interval-injection plumbing) + the resolver (FR-7) for the mask layer's chunk+repeat requirements |

The Wave 0 model is an **extension of the analysis-paradigm remediation**, not a departure: it applies the same contract-lock, fail-loud, provenance, and acceptable-default disciplines to the pre-analysis layer that G1–G5 applied to the analysis layer.

---

## 8. Non-goals

- We do **not** make chunking a property of the text fixed at import time (no canonical one-size chunking); D1 runtime control is preserved.
- We do **not** rebuild the Wave-1 analyses here; we only give them a cleaner, declared way to consume Wave-0 layers.
- We do **not** introduce a persistent job database; the existing in-memory `_running_jobs` + on-disk artifact model is retained (its limits are noted in the plan's risk register).

---

## 9. Open questions for human review

1. **Layer identity & naming.** Is a content-addressed label (sha256 of descriptor + analyzable digest) sufficient as the user-visible layer identity, or do layers need human-assigned names too?
2. **Where embedding layers live.** Keep embeddings in `cache/` (today's location, semantically "derivable cache") or promote to `signals/` (semantically "a result")? This affects whether they are treated as disposable or as first-class outputs.
3. **Dependency-check strictness.** When no compatible layer exists, should a consumer (a) fail loud and require the user to produce the layer first, or (b) offer to produce it inline with the consumer's declared requirements? (Recommendation: (a) for transparency; (b) as an explicit convenience action.)
4. **Scope of the first UI cut.** Rendering every chunk/embedding layer as a track (FR-13) is committed, not optional; the open question is *staging order* — Profile-only first (cheap, high-value, only `d3-shape`), or Profile + Representations (plural rendering) together? And: server-side PCA (zero new frontend deps) vs client-side `umap-js` for projection?
5. **CLI parity fix timing.** Fix the CLI `_extract_masked` gap as part of Phase 1 (correctness) or call it out as a separate bug fix? (Recommendation: Phase 1 — a chunking track is the first thing the gap would corrupt.)

# Palimpsest — System Design

> **Status: current architecture reference (rewritten 2026-06-29).** This supersedes the
> original P0-prototype stub (which described a MongoDB / sentence-transformers / D3 stack that
> was never built). The system below is the one in `core/` and `browser/` today. For the analysis
> paradigm specifically, this doc defers to `analysis-design-principles.md`; for the Wave-0
> analytics direction it defers to `wave0-analysis-suite-{vision,plan}.md`.

## 1. What Palimpsest is

Palimpsest is a computational literary-analysis platform. A user ingests a text (PDF / EPUB / HTML /
plain text), and the platform produces **analysis layers** over that text — entities, dialogue,
lexical features, topics, sentiment, repeats, chunkings, embeddings, self-similarity, and more — each
addressed back to exact character offsets in the original document and rendered as a **track** in a
genome-browser-style viewer.

The guiding metaphor is the browser, not the report: every analysis is a coordinate-bearing layer you
can line up against the text and against other layers.

## 2. Architecture at a glance

| Concern | Technology | Where |
|---|---|---|
| Core library | Python 3.12, packaged as `palimpsest` | `core/palimpsest/` |
| HTTP API | FastAPI + uvicorn | `core/palimpsest/server.py` |
| CLI | click (`palimpsest` entry point) | `core/palimpsest/cli.py` |
| NLP | spaCy, vaderSentiment, scikit-learn, numpy/scipy; optional booknlp | `tracks/`, `characters.py`, … |
| Ingest | pymupdf, ebooklib, beautifulsoup4 | `ingest/` |
| Persistence | **Filesystem project directories** + **sqlite-vec** (the only DB) | per-project dirs, `cache/*.db` |
| Frontend | React 19 + zustand + Tailwind 4 + Vite | `browser/` |
| Visualization | Hand-rolled `<canvas>` / `<svg>` (no D3 / plotly) | `browser/src/components/` |

There is **no MongoDB and no Postgres** in Palimpsest. Project state lives on the filesystem; the only
database is a per-project sqlite-vec vector store under `cache/`.

## 3. Storage model — the project directory

A *project* is a directory on disk. Everything about one text's analysis lives there, which makes
projects portable, diff-able, and content-addressable. The canonical layout (subdirs from
`project.py:_SUBDIRS`):

```
<project>/
  reference.txt            # the normalized text being analyzed (+ reference.txt.sha256)
  metadata.json            # title/author/source/profile/provenance
  layout_sections.json     # detected structural tree (book/chapter/verse/element …)
  coordinates.json         # structural coordinate index
  tracks/      *.jsonl      # annotation layers — one W3C JSON-LD annotation per line
  signals/     *.bin/.json  # signal layers — float32 matrices + JSON manifests
  manifests/   *.run.json   # per-run provenance (run_id, params, version, clamped values)
  cache/       *.db         # sqlite-vec embedding stores (the only database)
  x-config/    schemas/, detectors/   # per-project schema + detector overrides
  exports/                 # generated export artifacts
```

Two output families:

- **Annotation tracks** (`tracks/{name}.jsonl`) — discrete, located findings. Each line is a W3C
  Web-Annotation (JSON-LD) with a `TextPositionSelector` (integer `start`/`end` into `reference.txt`),
  a `body` typed `palimpsest:*`, and an `evidenceLevel` (E1–E5). Written atomically, sorted by start.
- **Signal layers** (`signals/{name}.bin` + `.json` manifest) — dense numeric outputs (e.g. a
  similarity matrix). The manifest declares `type`, `dimensions`, `dtype`, and `segment_offsets`
  (`[[start,end], …]` into `reference.txt`) so every cell of the signal maps back to a span of text.
  Manifest-only signals (no `.bin`) are valid (e.g. `alphabet`).

Provenance is filesystem-native: `manifests/{name}.run.json` is the **sole** authoritative record that
a track ran and with what parameters. Status is computed by reading disk, not a job table.

## 4. The track model — producers over a protocol

Every analysis is a **track**. A track is any object implementing the `TrackExtractor` protocol
(`tracks/base.py`): it declares a `name`, an `output_type` (`"annotation"` | `"signal"`), its
`depends_on` list, evidence level, and an `extract(project)` method returning annotations or a signal
path, plus `manifest()` / `parameters()`.

Adding a track is **zero-boilerplate**: drop a module in `tracks/` implementing the protocol;
`registry.discover()` (`tracks/registry.py`) finds it by package iteration, and `dependency_order()`
Kahn-topo-sorts the DAG. Tunable tracks subclass `ParameterizedTrack` (`tracks/params.py`), declaring
a tuple of validated `Param`s.

The current track roster spans structural detection, linguistic analysis (entities, coreference,
dialogue, lexical, syntax, sentiment, topics, narrative arc), and the Wave-0 substrate layers
(chunking, embedding, repeats, repeat_mask, self_similarity).

## 5. The coordinate-frame contract

Most analyses should not see masked content (e.g. verse numbers, repeated boilerplate). So the platform
computes an **analyzable view** of the text — the original with masked spans excised — and runs
extraction against that view. The mapping between the two frames is an `OffsetMap`:

- `project.analysis_view(sep)` returns `(view, OffsetMap)`; extraction runs on `view`'s analyzable text.
- Results are remapped **analyzable → original** before persistence (`runner.extract_masked`), so
  every on-disk offset addresses `reference.txt` directly. Annotations straddling a masked gap are
  dropped; signal `segment_offsets` are remapped span-by-span.
- A guard (G4) fails loud (`UnmappedCoordinateError`) if a track emits a coordinate-bearing field the
  manifest didn't declare — coordinates can never silently land in the wrong frame.

`analysis-design-principles.md §4` is the authoritative statement of this contract. The key property
for what follows: **a coordinate frame is an explicit, remappable object, not an implicit assumption** —
which is exactly what makes a *second* frame (cross-text root backbone) a small extension rather than a
rewrite.

## 6. The Wave-0 layer-track model and the resolver

Chunking and embedding used to be hidden preprocessing inside `self_similarity`. They are now
**first-class layer-tracks**: a user runs them under chosen parameters, they persist as reusable
signal layers carrying a **capability descriptor** (mode, size, model, dim, digests…), and downstream
analyses **declare a dependency on a layer** rather than triggering hidden invocation.

Two resolution paths make reuse safe rather than silently-wrong:

- **`resolve_layers`** (`tracks/requirements.py`) — kind-keyed implicit resolution (newest / sole
  survivor), fail-loud when a required layer kind is absent.
- **`resolve_explicit_bundle`** (`tracks/bundles.py`) — explicit, path-direct binding of one operand's
  `{chunk, repeat_mask, embedding?}` layers, validating coherence (`chunk_layer_id`,
  `analyzable_digest`) before use.

A read-side endpoint (`GET /api/projects/{id}/self_similarity/inputs`) completes the "safe-reuse triad":
explicit *display-time* discovery of which compatible layers a consumer can bind, so a user can pick
bundles without typing sha256 labels.

## 7. self_similarity as a layer-consumer (the paradigm in miniature)

`self_similarity` is the reference consumer. It is **embedding-agnostic** (it does not dictate an
embedding model) and **fail-loud** (it does not run unless the chunk / embedding / repeat_mask layers
it binds already exist). It declares a family of similarity methods (`_METHODS`: cosine, jaccard,
word_overlap, edit_distance) each flagged `requires_embedding`, binds explicit operand bundles, builds
an N×N matrix per method, and persists it as a signal layer with `segment_offsets` remapped to original
coordinates. This is the shape every future analysis-of-analyses follows.

## 8. Run lifecycle

Both entry points converge on the same persistence:

- **HTTP**: `POST /api/projects/{id}/analyze/{track}` validates/echoes resolved params, registers an
  in-memory job (`_running_jobs`; provenance on disk is authoritative across restarts), runs under an
  asyncio semaphore via `runner.extract_masked`, and writes track/signal + manifest + `run.json`.
  Status is `GET /analysis/status` reading disk per track; long runs stream via SSE.
- **CLI**: `palimpsest run-track <project> <track> -p key=value …` runs one track with explicit params
  through the same `extract_masked` + `persist_track_outputs` path. Content-addressed artifacts mean
  CLI- and UI-produced layers accumulate side by side automatically.

## 9. Frontend (`browser/`)

A React 19 / zustand / Tailwind 4 / Vite single-page app — a flat tab switch (no router), reading the
filesystem API through a Vite dev proxy. There are **no charting libraries**: every visualization is a
hand-rolled `<canvas>` or `<svg>` (e.g. `DotplotView`'s double-buffered similarity matrix,
`OverviewBar`'s track lanes). Installed UI primitives are `@dnd-kit/*` (layer-manager drag-reorder),
radix slider/tooltip/context-menu, and `@tanstack/react-virtual`. Each layer manifest carries a
`rendering` descriptor so the track loop draws *any* layer by `rendering.track_view` — the Nth layer of
a kind renders with zero new code (the FR-13 plural-rendering commitment).

## 10. Forward direction — the resemblance operator and cross-text

Self-similarity is the `A = B` degenerate case of a general two-operand resemblance operator `R(A, B)`,
with four modes on one engine: **auto** (`A=A`, today), **cross** (`A×B`), **probe** (`q×corpus`), and
**corpus** (`N-way`). The pre-stage (P9, FR-18/19/20) lifts three single-operand seams —
operand (`LayerBundle` → `ComparisonSpec`), kernel (`build(op_a, op_b)` with the self-guards made
conditional), and manifest (an `axes[]` list of length 1 for self, 2 for cross) — **without changing
self-similarity's behavior**.

The cross-text view (deferred, P10/FR-21) is a genome/synteny browser: a **root** text is the
coordinate backbone, other texts are coordinate-mapped onto it (alignment is an `OffsetMap` into the
root frame — the same excise/remap math, a second target), and cross-text similarity layers ride as
browser tracks. This extends the JBrowse 2 patterns adopted in `ADR-005` (`LinearSyntenyView`) and
reuses the producer/consumer + resolver machinery above. It additionally requires the **collection
analytical tier**, which is why it is scoped but not scheduled.

## 11. Relationship to other docs

- **`analysis-design-principles.md`** — authoritative for the analysis paradigm and the coordinate-frame
  contract (§4 / §4.1). This doc defers to it.
- **`wave0-analysis-suite-vision.md` / `…-plan.md`** — the layer-track analytics direction (FR-1…22,
  P1–P11) and the forward cross-text design (Vision §10).
- **`ADR-005-jbrowse2-patterns.md`** — the track/viewer pattern the cross-text view extends.
- **`../audits/analysis-paradigm-audit-2026-06.md`** — the evidence and sequenced remediation behind the
  layer-track reframe.

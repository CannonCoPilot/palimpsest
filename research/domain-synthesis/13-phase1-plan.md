# Palimpsest Phase 1: Walking Skeleton — Detailed Implementation Plan

**Date**: 2026-06-06
**Duration**: 10 weeks
**Predecessor**: None (Phase 1 is the starting point)
**Exit gate**: A literary scholar imports a novel and produces a multi-track structural overview in <30 minutes

---

## 0. Phase 1 Constraints and Policies

### 0.1 What Phase 1 Is

Phase 1 delivers a **read-only analytical tool**: import a text, compute features, view results. There is no human annotation UI, no custom schemas, no alignment engine. Those come in Phase 2 and 3. Phase 1's job is to prove that the core pipeline works, the browser is responsive, and the analytical results are meaningful.

### 0.2 PAF Instability Policy

During Phase 1, the PAF format is unstable. It will evolve as new tracks reveal requirements the initial design didn't anticipate. This is acceptable because:
- All track files are recomputable from source text + pipeline version
- No user-created annotations exist yet (human annotation is Phase 2)
- Upgrading between Phase 1 milestones may require re-ingesting projects

PAF will be declared v1.0 (stable) at the end of Phase 1. After that, only backward-compatible changes are permitted.

### 0.3 English-Only

Phase 1 supports English-language texts only. The data model (PAF, project structure) is language-agnostic, but all feature extractors (NER, sentiment, topic modeling, BookNLP) are English-specific. Non-English texts can be ingested but will produce incomplete or incorrect tracks — this is documented, not hidden.

### 0.4 Local-Only

No cloud services. No user accounts. No collaboration. The entire platform runs on one machine. The browser connects to a local server. All data lives in the project directory on the local filesystem.

---

## 1. Source Code Layout

```
palimpsest/
├── core/                        # Python backend (pip-installable package)
│   ├── palimpsest/
│   │   ├── __init__.py
│   │   ├── cli.py               # CLI entry points (ingest, analyze, serve)
│   │   ├── ingest/
│   │   │   ├── __init__.py
│   │   │   ├── extractor.py     # PDF/EPUB/TXT → raw text
│   │   │   ├── normalizer.py    # Unicode NFC, whitespace, SHA-256
│   │   │   └── segmenter.py     # Sentence/paragraph/section splitting
│   │   ├── tracks/
│   │   │   ├── __init__.py
│   │   │   ├── base.py          # Abstract track extractor interface
│   │   │   ├── entities.py      # spaCy NER → PAF
│   │   │   ├── sentiment.py     # VADER → PAF
│   │   │   ├── lexical.py       # TTR, hapax, etc → PAF
│   │   │   ├── dialogue.py      # Quote detection → PAF
│   │   │   ├── topics.py        # LDA → PAF
│   │   │   ├── narrative_arc.py # Boyd 15-dim → signal
│   │   │   ├── self_similarity.py # Embedding cosine → signal
│   │   │   ├── rqa.py           # Recurrence quantification → signal
│   │   │   ├── alphabet.py      # K-means encoding → signal
│   │   │   ├── coreference.py   # BookNLP coref → PAF
│   │   │   └── booknlp_enrichment.py  # BookNLP wrapper
│   │   ├── formats/
│   │   │   ├── __init__.py
│   │   │   ├── paf.py           # PAF reader/writer/validator
│   │   │   ├── w3c.py           # W3C Web Annotation converter
│   │   │   └── signals.py       # Signal (matrix/vector) I/O
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── embedding.py     # Ollama embedding client
│   │   │   ├── llm.py           # Ollama LLM client
│   │   │   └── manager.py       # Service lifecycle (start/stop/health)
│   │   ├── project.py           # Project directory management
│   │   └── server.py            # FastAPI/static file server
│   ├── tests/
│   │   ├── fixtures/            # IJ Chapter 1 text, expected outputs
│   │   ├── test_ingest.py
│   │   ├── test_tracks.py
│   │   ├── test_paf.py
│   │   └── test_pipeline.py     # Integration tests
│   ├── pyproject.toml
│   └── README.md
├── browser/                     # React frontend
│   ├── src/
│   │   ├── App.tsx
│   │   ├── components/
│   │   │   ├── TextLinearView/
│   │   │   │   ├── TextLinearView.tsx
│   │   │   │   ├── AnnotationOverlay.tsx
│   │   │   │   ├── VirtualScroller.tsx
│   │   │   │   └── SemanticZoom.tsx
│   │   │   ├── OverviewBar/
│   │   │   │   ├── OverviewBar.tsx
│   │   │   │   └── DensityBarcode.tsx
│   │   │   ├── DotplotView/
│   │   │   │   ├── DotplotView.tsx
│   │   │   │   └── CanvasRenderer.tsx
│   │   │   ├── TrackPanel/
│   │   │   │   ├── TrackPanel.tsx
│   │   │   │   ├── TrackToggle.tsx
│   │   │   │   └── ConfidenceSlider.tsx
│   │   │   ├── DetailPanel/
│   │   │   │   ├── DetailPanel.tsx
│   │   │   │   └── LLMSummary.tsx
│   │   │   └── CrossTextDotplot/
│   │   │       └── CrossTextDotplot.tsx
│   │   ├── stores/
│   │   │   ├── ProjectStore.ts    # MobX-state-tree: loaded project data
│   │   │   ├── ViewStore.ts       # MobX-state-tree: current viewport, zoom, selection
│   │   │   └── TrackStore.ts      # MobX-state-tree: track visibility, colors, filters
│   │   ├── adapters/
│   │   │   ├── PAFAdapter.ts      # Reads PAF files → annotation objects
│   │   │   └── SignalAdapter.ts   # Reads signal files → typed arrays
│   │   └── utils/
│   │       ├── offsets.ts         # Character offset ↔ viewport position math
│   │       └── colors.ts         # Track color palette (ColorBrewer qualitative)
│   ├── index.html
│   ├── vite.config.ts
│   ├── tsconfig.json
│   └── package.json
├── fixtures/                    # Test data (checked into repo)
│   ├── ij-chapter1.txt          # IJ Chapter 1, pre-normalized
│   ├── ij-chapter1.pdf          # IJ Chapter 1 as PDF (for extraction testing)
│   ├── swinehart/               # Symlink or copy of Swinehart datasets
│   └── expected/                # Expected PAF outputs for regression testing
├── specs/                       # Format specifications (generated from code)
│   ├── PAF.md                   # PAF format description (updated per milestone)
│   ├── LFO.md                   # Literary Feature Ontology (updated per milestone)
│   └── signals.md               # Signal format description
└── docs/
    └── architecture/
        ├── ADR-001-annotation-format.md
        ├── ADR-002-paf-format.md
        └── ...
```

---

## 2. Data Formats

### 2.1 PAF-Span (Span Annotations)

Tab-separated, one feature per line. Comment lines start with `#`. Header line starts with `##`.

```
##palimpsest-paf-version 0.1
##reference-sha256 a1b2c3d4...
##reference-file reference.txt
#docname	source	type	start	end	score	strand	phase	attributes
moby_dick	spacy/3.7	entity.character	0	4	0.92	.	.	ID=e001;Name=Ishmael;entity_type=PER
moby_dick	spacy/3.7	entity.location	37	49	0.85	.	.	ID=e002;Name=New Bedford;entity_type=LOC
moby_dick	vader/0.1	signal.sentiment	0	847	0.62	.	.	ID=s001;valence=0.23;arousal=0.41
```

**Column definitions**:
| Column | Type | Description |
|---|---|---|
| docname | string | Document identifier (from metadata.json) |
| source | string | Tool/annotator that produced this annotation. Format: `tool/version` or `human:username` |
| type | string | LFO term (dot-separated hierarchy). E.g., `entity.character`, `structural.scene`, `signal.sentiment` |
| start | int | Start character offset, 0-based inclusive |
| end | int | End character offset, 0-based exclusive (half-open: `[start, end)`) |
| score | float or `.` | Confidence 0.0-1.0, or `.` if not applicable |
| strand | `.` | Reserved for future use (directionality of references) |
| phase | `.` | Reserved for future use |
| attributes | string | Semicolon-separated key=value pairs. `ID` must be unique per file. `Parent` references another ID. |

### 2.2 Signals (Non-Span Data)

Stored as JSON in `signals/` subdirectory:

```json
{
  "type": "matrix",
  "name": "self_similarity",
  "source": "embedding_cosine/0.1",
  "reference_sha256": "a1b2c3d4...",
  "dimensions": [200, 200],
  "segment_offsets": [[0, 423], [424, 891], ...],
  "data_file": "self_similarity.npz",
  "metadata": {
    "similarity_metric": "cosine",
    "embedding_model": "qwen3-embedding-4b"
  }
}
```

Matrix data stored as compressed NumPy (`.npz`). Signal metadata stored as JSON manifest. The browser reads the JSON manifest and fetches the `.npz` on demand.

Signal types:
- `matrix` — 2D array (self-similarity, cross-text similarity)
- `vector` — 1D array (narrative arc dimensions, sequential scores)
- `sequence` — categorical string (narrative alphabet: "AABCDDEFFGHA...")
- `distribution` — per-segment probability vectors (topic distributions)

### 2.3 Project Directory

```
projects/{text-id}/
├── reference.txt              # Normalized text (immutable after ingest)
├── reference.sha256           # SHA-256 of reference.txt
├── metadata.json              # Title, author, year, source format, ingest date, language
├── segments.paf               # Structural segmentation (sentences, paragraphs, sections)
├── tracks/                    # PAF-Span annotation files (one per track)
│   ├── entities.paf
│   ├── sentiment.paf
│   ├── lexical.paf
│   ├── dialogue.paf
│   ├── topics.paf
│   └── coreference.paf       # (if BookNLP available)
├── signals/                   # Non-span data
│   ├── self_similarity.json   # Matrix manifest
│   ├── self_similarity.npz    # Matrix data
│   ├── narrative_arc.json     # Vector manifest
│   ├── narrative_arc.npz      # Vector data
│   ├── rqa.json               # RQA scores manifest
│   ├── rqa.npz                # RQA data
│   ├── topics_dist.json       # Topic distribution manifest
│   ├── topics_dist.npz        # Distribution data
│   └── alphabet.json          # Narrative alphabet manifest + sequence string
├── cache/                     # Intermediate computation results (not in git)
│   ├── spacy_docs.pkl         # Cached spaCy parse (expensive to recompute)
│   ├── embeddings.db          # sqlite-vec database of segment embeddings
│   └── booknlp/               # BookNLP output files
├── x-config/                  # Extension configuration (scaffolded, empty in Phase 1)
│   ├── schemas/
│   └── detectors/
└── exports/                   # User-requested exports
```

---

## 3. Analysis Units

| Unit | Definition | Used by | Granularity |
|---|---|---|---|
| **Character** | Single Unicode code point in reference.txt | Offset indexing | Finest |
| **Token** | spaCy token (word or punctuation) | NER, POS analysis | Sub-sentence |
| **Sentence** | spaCy sentence boundary | Sentiment (per-sentence), base segmentation | Fine |
| **Paragraph** | Double-newline delimited block in reference.txt | Topics, lexical stats, default analysis unit | Medium |
| **Section** | Detected chapter/heading boundary | Overview aggregation, structural analysis | Coarse |
| **Span** | Arbitrary `[start, end)` range | Entity mentions, dialogue quotes, any annotation | Variable |

Default analysis granularity: **paragraph**. Tracks that need finer granularity (entity spans, sentiment per sentence) operate at their natural level. Tracks that produce continuous signals (narrative arc, RQA) use a **sliding window** of configurable width (default: 100 words, 50-word overlap).

---

## 4. Track Inventory (Final, Phase 1)

Exactly 10 track files are produced. The confusion in the v2 roadmap is resolved here.

### 4.1 PAF-Span Tracks (6 files in `tracks/`)

| # | File | Type hierarchy | Source | Granularity | Depends on |
|---|---|---|---|---|---|
| 1 | `entities.paf` | `entity.character`, `entity.location`, `entity.organization` | spaCy NER (basic) or BookNLP (enriched) | Span | spaCy parse |
| 2 | `sentiment.paf` | `signal.sentiment` | VADER | Sentence | spaCy parse |
| 3 | `lexical.paf` | `signal.lexical_density`, `signal.vocabulary_richness` | Custom | Paragraph | Tokenization |
| 4 | `dialogue.paf` | `structural.dialogue.quote`, `structural.dialogue.attribution` | Regex + BookNLP | Span | spaCy parse |
| 5 | `topics.paf` | `signal.topic_assignment` | LDA | Paragraph | Tokenization |
| 6 | `coreference.paf` | `entity.coreference_link` | BookNLP (optional) | Span | entities.paf |

### 4.2 Signal Files (4 signal sets in `signals/`)

| # | Manifest | Type | Source | Granularity | Depends on |
|---|---|---|---|---|---|
| 7 | `narrative_arc.json` | vector (15-dim × 5 segments) | Boyd function-word arc | 5 equal text segments | Tokenization |
| 8 | `self_similarity.json` | matrix (N×N paragraphs) | Embedding cosine | Paragraph | Embeddings |
| 9 | `rqa.json` | vector (RR, DET, LAM per window) | RQA computation | Sliding window | Tokenization |
| 10 | `alphabet.json` | sequence (string of N letters) | K-means on feature vectors | Paragraph | Tracks 2-5 |

### 4.3 Dependency DAG

```
reference.txt
  → spaCy parse (cached in cache/spacy_docs.pkl)
    → entities.paf [Track 1]
    → sentiment.paf [Track 2]
    → dialogue.paf [Track 4]
  → tokenization
    → lexical.paf [Track 3]
    → topics.paf [Track 5]
    → narrative_arc signal [Track 7]
    → rqa signal [Track 9]
  → embeddings (cached in cache/embeddings.db)
    → self_similarity signal [Track 8]
  → tracks 2-5 features
    → alphabet signal [Track 10]
  → BookNLP (optional, cached in cache/booknlp/)
    → entities.paf enrichment [Track 1 update]
    → dialogue.paf enrichment [Track 4 update]
    → coreference.paf [Track 6]
```

Partial recomputation: changing the embedding model only recomputes Track 8 and Track 10 (which depends on all features). Changing the spaCy model recomputes Tracks 1, 2, 4, and everything downstream.

---

## 5. Browser ↔ Backend Communication

### Phase 1 Architecture: Static File Serving

```
palimpsest serve <project-dir> [--port 8080]
```

1. FastAPI serves the React build output at `/`
2. FastAPI serves the project directory at `/data/`
3. Browser fetches `reference.txt`, `*.paf`, `signals/*.json` via HTTP GET
4. Browser parses PAF client-side using the `PAFAdapter`
5. No write endpoints — Phase 1 is read-only
6. LLM summaries: browser calls `/api/summarize` which proxies to Ollama

```
Browser (React)                     Server (FastAPI)
    │                                     │
    ├── GET /                     ────→   Static: browser/dist/index.html
    ├── GET /data/reference.txt   ────→   Static: projects/{id}/reference.txt
    ├── GET /data/tracks/entities.paf ──→ Static: projects/{id}/tracks/entities.paf
    ├── GET /data/signals/self_similarity.json ──→ Static
    ├── GET /data/signals/self_similarity.npz ──→ Static (binary)
    └── POST /api/summarize       ────→   Proxy to Ollama → response
```

### Why Not a Full REST API in Phase 1

A full REST API (CRUD for annotations, search, etc.) is unnecessary when the data is read-only and the user is a single person on one machine. Static file serving is:
- Trivial to implement (3 lines of FastAPI)
- Debuggable (you can inspect the PAF files in a text editor)
- Fast (no database queries, no serialization overhead)
- A correct foundation (the React app learns to parse PAF from files; when Phase 2 adds a REST API, the PAF parsing code is already written)

---

## 6. Milestone Detail

### Milestone 1.1: Ingest + Normalize + First Track + Minimal Browser (Week 1-2)

#### Week 1: Backend

**Day 1-2: Project scaffolding**
- Initialize monorepo: `core/` (Python, pyproject.toml with hatch), `browser/` (React, Vite, TypeScript)
- Set up pytest for core/
- Set up Vitest for browser/
- Create `fixtures/ij-chapter1.txt` — manually extract and normalize IJ Chapter 1 (pp. 3-17)
- First passing test: `test_normalizer.py` — normalize a known string, assert SHA-256

**Day 3: Ingestion pipeline**
- `extractor.py`: PDF (pymupdf) → raw text; EPUB (ebooklib) → raw text; TXT → passthrough
- `normalizer.py`: Unicode NFC, collapse whitespace, normalize quotes, compute SHA-256
- `segmenter.py`: spaCy `en_core_web_sm` sentence segmentation; paragraph detection (double newline); section detection (ALL-CAPS or numbered headings)
- `project.py`: create project directory, write reference.txt, segments.paf, metadata.json
- Tests: ingest IJ Chapter 1 from TXT; ingest from PDF; assert identical reference.txt from both

**Day 4: Entity track**
- `entities.py`: run spaCy NER over reference.txt; produce `entities.paf` with PER, LOC, ORG spans
- `paf.py`: PAF writer (generate valid TSV); PAF reader (parse TSV → list of annotation dicts); PAF validator (check required columns, valid offsets, unique IDs)
- Tests: entity track on IJ Chapter 1 detects "Hal" (PER), "Arizona" (LOC), "University of Arizona" (ORG); PAF round-trip (write → read → assert identical)
- LFO v0.1 written: document the 15 terms used by segments.paf + entities.paf

**Day 5: CLI**
- `cli.py` using Click: `palimpsest ingest <file>` (runs extractor → normalizer → segmenter → entity track)
- `palimpsest info <project-dir>` (prints metadata + track inventory)
- Smoke test: `palimpsest ingest ij-chapter1.pdf` → project directory created with all expected files

#### Week 2: Browser

**Day 6-7: React scaffolding**
- Vite + React + TypeScript + MobX-state-tree setup
- `PAFAdapter.ts`: fetch PAF file → parse → return typed annotation objects
- `ProjectStore.ts`: load reference.txt + segments.paf + entities.paf from `/data/`
- Minimal `TextLinearView.tsx`: render reference text as paragraphs in a scrollable div
  - No virtualization yet (Chapter 1 is only 15 pages — not needed yet)

**Day 8-9: Annotation overlay**
- `AnnotationOverlay.tsx`: render entity spans as colored `<mark>` elements over the text
- Click an entity → show name and type in a tooltip
- One-track toggle: checkbox to show/hide entities
- `server.py`: FastAPI static file serving for browser build + project directory

**Day 10: Integration + smoke test**
- `palimpsest serve <project-dir>` launches server, opens browser
- End-to-end smoke test: `palimpsest ingest ij-chapter1.txt && palimpsest serve projects/ij-chapter1/`
- Visual verification: entities highlighted in the browser

**Milestone 1.1 smoke test** (must pass before proceeding):
```
$ palimpsest ingest fixtures/ij-chapter1.txt
  → Project created: projects/ij-chapter1/
$ palimpsest serve projects/ij-chapter1/
  → Browser opens at http://localhost:8080
  → Text visible with "Hal" highlighted in blue, "Arizona" in green
  → Click "Hal" → tooltip: "entity.character, confidence: 0.92"
  → Total time from command to visible result: <30 seconds
```

---

### Milestone 1.2: Five Tracks + AI Summary (Week 3-5)

#### Week 3: Four New Tracks

**Day 11-12: Sentiment + Lexical tracks**
- `sentiment.py`: VADER per sentence → `sentiment.paf` with valence score
- `lexical.py`: per paragraph → `lexical.paf` with TTR, hapax count, mean word length, vocabulary richness
- Tests: sentiment track on IJ Chapter 1 detects negative sentiment in the mold-eating passage; lexical track computes correct TTR for known paragraphs

**Day 13-14: Dialogue + Topics tracks**
- `dialogue.py`: regex detection of quoted speech (curly/straight quotes + said-verb patterns) → `dialogue.paf`
- `topics.py`: sklearn LatentDirichletAllocation, 10 topics, per-paragraph → `topics.paf` (topic assignment) + `signals/topics_dist.json` (distribution vectors)
- Tests: dialogue track finds quoted speech in IJ Chapter 1 opening interview; topic model produces 10 distinct topics

**Day 15: Pipeline orchestration**
- `cli.py` updated: `palimpsest analyze <project-dir>` runs all track extractors
- Track dependency DAG: define dependencies in each track's metadata; orchestrator runs in dependency order
- Caching: spaCy parse cached to `cache/spacy_docs.pkl`; skip recomputation if cache valid
- `palimpsest analyze` on full IJ: all 5 tracks in <30 seconds (benchmark)

#### Week 4: LLM Integration + Browser Tracks

**Day 16-17: Ollama service manager**
- `manager.py`: `palimpsest services start` → check if Ollama is running; pull required model if not present; report status
- `llm.py`: client for Ollama chat completions with structured output
- `embedding.py`: client for Ollama embeddings (batch and single)
- Tests: health check, model availability check, embedding dimension verification

**Day 18-19: LLM passage summarizer**
- `/api/summarize` endpoint: accepts passage text, returns 2-sentence summary
- System prompt: "You are a literary analysis assistant. Summarize this passage in exactly 2 sentences, focusing on narrative significance."
- `LLMSummary.tsx`: component displayed in DetailPanel when user selects a passage
- Graceful degradation: if Ollama not running, show "Start AI services for summaries" message

**Day 20: Browser track panel**
- `TrackPanel.tsx`: list all available tracks with:
  - Toggle switch (show/hide)
  - Color swatch (from ColorBrewer qualitative-8 palette)
  - Count badge (number of annotations in this track)
  - Confidence slider (filter by minimum score)
- `OverviewBar.tsx`: horizontal barcode per track showing annotation density across document
  - One thin colored bar per active track
  - Click position → scroll TextLinearView to that offset
- Track rendering in TextLinearView: entity highlights + sentiment background tint + dialogue markers

#### Week 5: Polish + Testing

**Day 21-22: Multi-track rendering**
- Overlapping annotation rendering strategy:
  - Primary track: inline background highlight
  - Secondary tracks: colored underline or left-margin marker
  - Max 3 concurrent inline highlights (more → clutter)
  - Overflow tracks → margin markers only
- Track color assignment: stable per track type (entities always blue, sentiment always warm/cool gradient, dialogue always yellow)

**Day 23-24: Testing infrastructure**
- Unit tests for all 5 track extractors
- Integration test: full pipeline on IJ Chapter 1 → validate all PAF files against expected outputs
- Regression test framework: snapshot PAF outputs; compare on re-run
- Benchmark: time full pipeline on IJ Chapter 1; assert <5 seconds

**Day 25: Milestone 1.2 smoke test**
```
$ palimpsest ingest ij-full.txt
$ palimpsest analyze projects/ij-full/
  → 5 tracks computed in <30 seconds
$ palimpsest serve projects/ij-full/
  → Browser: 5 tracks visible in TrackPanel
  → Toggle sentiment on → text paragraphs tinted by valence
  → OverviewBar shows density barcodes for all 5 tracks
  → Select a paragraph → DetailPanel shows attributes
  → Click "Summarize" → LLM generates 2-sentence summary (or degradation message)
  → Total time: <2 minutes from ingest to summary
```

---

### Milestone 1.3a: Remaining Base Tracks + Embedding Service (Week 5-7)

#### Week 5 (continued) - Week 6

**Day 26-27: Embedding service**
- Ollama embedding model served via `embedding.py`
- Batch embed all paragraphs → store in `cache/embeddings.db` (sqlite-vec)
- Similarity search endpoint: `GET /api/search?query=...&k=10` → top-k similar paragraphs
- Performance: embed IJ (~3000 paragraphs) in <3 minutes on M1; <60 seconds on M4

**Day 28-29: Self-similarity matrix**
- `self_similarity.py`: compute pairwise cosine similarity between all paragraph embeddings
- Output: `signals/self_similarity.json` (manifest) + `signals/self_similarity.npz` (matrix)
- For memory: use float16 for storage; compute in float32
- Test: IJ self-similarity matrix shows block-diagonal structure at chapter boundaries

**Day 30-31: Narrative arc + RQA + Alphabet**
- `narrative_arc.py`: Boyd 15-dimensional function-word arc (5 equal text segments × 3 dimensions: staging, plot progression, cognitive tension)
- `rqa.py`: recurrence quantification analysis (RR, DET, LAM per sliding window)
- `alphabet.py`: K-means clustering on per-paragraph feature vectors → 16-letter alphabet string
- All produce signal files in `signals/`
- Tests: narrative arc on IJ shows declining staging, rising plot progression (matches Boyd theory)

#### Week 7: BookNLP + DotplotView

### Milestone 1.3b: BookNLP + DotplotView (Week 7-8)

**Day 32-33: BookNLP integration**
- `booknlp_enrichment.py`: wrapper around BookNLP Python package
  - Character name clustering → update `entities.paf` with canonical IDs and character type
  - Coreference resolution → produce `coreference.paf`
  - Quotation attribution → update `dialogue.paf` with speaker assignments
- Fallback path: if BookNLP import fails (Java not installed, memory error):
  - Log warning: "BookNLP unavailable — using basic entity/dialogue tracks"
  - Skip coreference track entirely
  - Mark entities.paf and dialogue.paf as "basic mode" in metadata
- Tests: BookNLP on IJ Chapter 1 clusters "Hal" variants; coreference resolves >60% of pronouns

**Day 34-36: DotplotView**
- `DotplotView.tsx`: Canvas-based 2D heatmap rendering
  - Load self-similarity matrix from `signals/self_similarity.npz`
  - Render as color-mapped pixels on a Canvas element
  - Color scale: white (low similarity) → dark blue (high similarity)
  - Interaction: zoom (scroll wheel), pan (drag), click (select cell)
  - Click cell (i,j) → highlight paragraphs i and j in TextLinearView
- Performance: render 500×500 matrix in <500ms; 1000×1000 in <1 second
- Overlay: chapter boundary lines drawn over the matrix

**Day 37: Linked views first pass**
- Shared MobX-state-tree selection state:
  - `ViewStore.selectedParagraphIndex: number | null`
  - TextLinearView: clicking a paragraph sets `selectedParagraphIndex`
  - DotplotView: highlighting row/column for `selectedParagraphIndex`
  - OverviewBar: position indicator at `selectedParagraphIndex`

**Milestone 1.3 smoke test**:
```
$ palimpsest ingest ij-full.txt
$ palimpsest analyze projects/ij-full/ --enrich  # includes BookNLP
  → 10 tracks/signals computed
$ palimpsest serve projects/ij-full/
  → Browser: 6 PAF tracks + 4 signal displays available
  → DotplotView: self-similarity matrix visible with chapter blocks
  → Click a cell → both paragraphs highlighted in TextLinearView
  → Select passage → LLM summary appears
  → Walking skeleton: end-to-end in <3 minutes from clean start
```

---

### Milestone 1.4: Full Text Browser + Cross-Text Dotplot (Week 8-10)

#### Week 8-9: Browser Polish

**Day 38-40: Virtualized scrolling**
- `VirtualScroller.tsx`: renders only the visible viewport + 2-screen buffer
  - Computes paragraph positions from offset + estimated line heights
  - Recycled DOM elements for smooth scroll performance
  - Intersection Observer for lazy loading of annotation overlays
- Performance target: smooth 60fps scrolling through full IJ (300+ pages, 5 active tracks)

**Day 41-42: Semantic zoom**
- `SemanticZoom.tsx`: zoom level determines what's rendered
  - Close zoom (paragraph visible): individual annotation spans with labels
  - Medium zoom (chapter visible): annotation density bars per paragraph
  - Far zoom (document visible): per-track density heatmap bars only
- Zoom control: scroll wheel with Ctrl/Cmd held, or slider in toolbar

**Day 43-44: Signal visualizations in browser**
- Narrative arc display: small sparkline chart in a dedicated panel showing staging/progression/tension curves
- RQA display: bar chart of RR, DET, LAM values per window
- Alphabet display: colored barcode (one block per paragraph, color = letter assignment)
- Topic display: stacked bar chart of topic distributions per section

**Day 45: OverviewBar enhancements**
- Brush selection: click-drag in OverviewBar → highlight region → TextLinearView scrolls to center of selection
- Multiple track barcodes stacked vertically
- Annotations per barcode: thin colored ticks at annotation positions

#### Week 9-10: Cross-Text + Export + Final Polish

**Day 46-47: Cross-text dotplot**
- `palimpsest ingest <second-file>` → second project
- `CrossTextDotplot.tsx`: given two projects with embeddings, compute and display inter-text similarity matrix
  - Text A paragraphs on X axis, Text B on Y axis
  - Color = cosine similarity
  - Near-diagonal patterns = aligned parallel passages
  - Off-diagonal blobs = structural rearrangement or thematic echo
- UI: dropdown to select second project; dotplot renders in the DotplotView panel

**Day 48: Export**
- `palimpsest export <project-dir> --format w3c` → W3C Web Annotation JSON-LD
- `palimpsest export <project-dir> --format csv` → flat CSV of all annotations
- `palimpsest export <project-dir> --format paf` → copy of all PAF files
- Round-trip test: export W3C → reimport → assert annotations preserved

**Day 49-50: Final polish + documentation**
- Error messages: every CLI error includes a suggested fix
- `palimpsest --help` / `palimpsest ingest --help` / `palimpsest analyze --help`
- README.md: installation, quick start, example commands
- PAF spec document (specs/PAF.md) updated to v1.0
- LFO document (specs/LFO.md) updated with all ~60 terms used across 10 tracks

**Phase 1 exit smoke test**:
```
$ pip install palimpsest
$ palimpsest ingest pride-and-prejudice.txt
$ palimpsest analyze projects/pride-and-prejudice/
  → 10 tracks/signals computed in <30 seconds
$ palimpsest serve projects/pride-and-prejudice/
  → Browser: text with multi-track annotations
  → DotplotView: self-similarity visible
  → TrackPanel: toggle tracks, adjust confidence
  → Select passage: LLM summary (if Ollama running)
  → Import second text → cross-text dotplot shows structural comparison
  → Export W3C JSON-LD → valid file produced

Time from install to first structural analysis: <5 minutes
A literary scholar produces a multi-track overview: <30 minutes
```

---

## 7. Test Plan

### 7.1 Unit Tests (pytest, every commit)

| Module | Tests | Key assertions |
|---|---|---|
| `normalizer.py` | 8 | NFC normalization, whitespace collapse, SHA-256 determinism, idempotency |
| `extractor.py` | 6 | PDF extraction, EPUB extraction, TXT passthrough, encoding handling |
| `segmenter.py` | 10 | Sentence boundaries, paragraph boundaries, section detection, offset accuracy |
| `paf.py` | 12 | Write/read round-trip, validation (bad offsets, missing columns, duplicate IDs), special characters in attributes |
| `entities.py` | 5 | PER/LOC/ORG detection on known text, confidence scores, offset accuracy |
| `sentiment.py` | 4 | Positive/negative valence detection, neutral handling, per-sentence granularity |
| `lexical.py` | 4 | TTR computation, hapax count, vocabulary richness for known paragraphs |
| `dialogue.py` | 6 | Direct quote detection, nested quotes, said-verb patterns, edge cases (em-dash dialogue) |
| `topics.py` | 3 | 10 topics produced, per-paragraph assignment, distribution sums to 1.0 |
| `narrative_arc.py` | 3 | 15-dimensional output, 5-segment division, function-word category counts |
| `self_similarity.py` | 3 | Matrix dimensions match paragraph count, diagonal is 1.0, symmetry |
| `rqa.py` | 3 | RR/DET/LAM values in [0,1], window size correctness |
| `alphabet.py` | 3 | Output length matches paragraph count, K letters used, deterministic with fixed seed |

### 7.2 Integration Tests (pytest, every PR)

| Test | What it validates |
|---|---|
| `test_full_pipeline` | Ingest → analyze → all 10 tracks produced → all valid PAF/signal |
| `test_partial_recompute` | Change one track config → only that track + dependents recomputed |
| `test_booknlp_fallback` | Mock BookNLP failure → graceful fallback → 8 tracks produced (no coreference) |
| `test_ollama_absent` | Ollama not running → all non-LLM features work → summarizer shows degradation message |

### 7.3 End-to-End Tests (Playwright, weekly)

| Test | Steps |
|---|---|
| `test_ingest_to_browser` | CLI ingest → serve → browser loads → text visible → entities highlighted |
| `test_track_toggle` | Load browser → toggle tracks on/off → verify rendering updates |
| `test_dotplot_interaction` | Load browser → open dotplot → click cell → verify text view scrolls |
| `test_cross_text` | Ingest two texts → serve → open cross-text dotplot → verify matrix renders |

### 7.4 Regression Tests (snapshot, every release)

- PAF output for IJ Chapter 1 snapshotted after each milestone
- New runs compared against snapshot: byte-identical (excluding timestamps in headers)
- Any delta requires explicit approval ("this change is intentional because...")

### 7.5 Benchmarks (custom, every release)

| Benchmark | Target | Measured |
|---|---|---|
| Ingest IJ Chapter 1 (TXT) | <2 seconds | Wall clock |
| Ingest IJ Chapter 1 (PDF) | <5 seconds | Wall clock |
| Analyze IJ Chapter 1 (5 tracks) | <5 seconds | Wall clock |
| Analyze full IJ (10 tracks, no BookNLP) | <30 seconds | Wall clock |
| Browser initial load (IJ Chapter 1) | <1 second | Lighthouse |
| Dotplot render (200×200 matrix) | <500ms | Canvas draw time |
| Dotplot render (1000×1000 matrix) | <2 seconds | Canvas draw time |
| Scroll performance (full IJ, 5 tracks) | 60fps | Chrome DevTools |

---

## 8. Dependencies and Prerequisites

### 8.1 Python Dependencies

```toml
[project]
requires-python = ">=3.12"
dependencies = [
    "click>=8.0",
    "fastapi>=0.100",
    "uvicorn>=0.20",
    "spacy>=3.7",
    "vaderSentiment>=3.3",
    "scikit-learn>=1.3",      # LDA, K-means
    "numpy>=1.26",
    "scipy>=1.12",            # Sparse matrices
    "pymupdf>=1.23",          # PDF extraction
    "ebooklib>=0.18",         # EPUB extraction
    "beautifulsoup4>=4.12",   # HTML cleaning
    "sqlite-vec>=0.1",        # Embedded vector store
    "httpx>=0.25",            # Ollama client
]

[project.optional-dependencies]
booknlp = ["booknlp>=2.0"]
dev = ["pytest>=8.0", "pytest-cov", "ruff", "mypy"]
```

### 8.2 Node Dependencies

```json
{
  "dependencies": {
    "react": "^18",
    "react-dom": "^18",
    "mobx": "^6",
    "mobx-state-tree": "^6",
    "mobx-react-lite": "^4",
    "d3": "^7"
  },
  "devDependencies": {
    "typescript": "^5",
    "vite": "^5",
    "@vitejs/plugin-react": "^4",
    "vitest": "^1",
    "@playwright/test": "^1"
  }
}
```

### 8.3 External Prerequisites

| Prerequisite | Required? | Install command |
|---|---|---|
| Python 3.12+ | Yes | System-dependent |
| Node.js 20+ | Yes | `brew install node` or nvm |
| spaCy English model | Yes (auto-downloaded) | `python -m spacy download en_core_web_sm` |
| Ollama | Optional (for LLM features) | `brew install ollama` |
| Ollama embedding model | Optional | `ollama pull qwen3-embedding` or `nomic-embed-text` |
| Ollama LLM model | Optional | `ollama pull qwen3:8b` or `mistral:7b` |
| Java 11+ | Optional (for BookNLP) | `brew install openjdk@11` |

---

## 9. Definition of Done (Phase 1)

Phase 1 is complete when ALL of the following are true:

- [ ] `palimpsest ingest` accepts PDF, EPUB, and TXT files and produces a valid project directory
- [ ] `palimpsest analyze` computes 10 tracks/signals in <30 seconds for a 300-page novel
- [ ] `palimpsest serve` launches a browser showing text with multi-track annotations
- [ ] TrackPanel: toggle visibility, color coding, confidence filtering for all tracks
- [ ] OverviewBar: density barcodes for all active tracks; click-to-navigate
- [ ] DotplotView: self-similarity matrix with zoom, pan, click-to-navigate
- [ ] Cross-text dotplot: two imported texts compared via embedding similarity matrix
- [ ] LLM passage summarizer: working when Ollama is running; graceful degradation when not
- [ ] Linked views: selection in any view propagates to all others
- [ ] Semantic zoom: close/medium/far zoom show different annotation detail levels
- [ ] Export: W3C Web Annotation JSON-LD, PAF, CSV
- [ ] All unit tests pass (>80% code coverage on core/)
- [ ] All integration tests pass
- [ ] All benchmarks meet targets
- [ ] PAF spec v1.0 documented in specs/PAF.md
- [ ] LFO v1.0 documented in specs/LFO.md with ~60 terms
- [ ] README.md: installation, quick start, example commands
- [ ] A literary scholar unfamiliar with the tool produces a structural analysis in <30 minutes (user test)

---

*This plan is the implementation guide for Phase 1 of the Palimpsest development roadmap (document 12, v2.0). The critical reviews (12a, 12b) are preserved as audit trails.*

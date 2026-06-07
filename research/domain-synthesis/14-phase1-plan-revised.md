# Palimpsest Phase 1: Walking Skeleton — Revised Implementation Plan (v4.0)

**Date**: 2026-06-07
**Supersedes**: v3.0 (2026-06-06), v2.0, v1.0 (doc 13)
**Incorporates**: All 20 findings from document 13a; format/architecture alignment with research corpus (docs 07-11); **v4.0 performance architecture redesign (doc 15)**

> **v4.0 CRITICAL CHANGE**: The entire rendering and data layer has been redesigned. Python+React+Browser is replaced by **Tauri 2.0 + Rust core engine + WebGPU frontend**. See `15-performance-architecture-v4.md` for full rationale. All 37 atomized tasks (T01-T37) have been rewritten with v4.0 Critical Review + v4.0 Rewrite sections. The original v3.0 content is preserved in each task file for reference.
>
> **Motivation**: M1.2 browser was completely unresponsive loading a full novel (130K words, 18,760 annotations). Root cause: O(paragraphs x annotations) = 48M comparisons per render, 50-75MB JS heap for annotation objects, 50K+ DOM elements. This is unfixable within the browser/React model at the target scale (5-10 simultaneous novels, 100K+ annotations, side-by-side alignment views).

## v4.0 Architecture Summary

| Layer | v3.0 (replaced) | v4.0 (current) |
|-------|-----------------|----------------|
| App shell | Chrome browser tab | Tauri 2.0 (native macOS WKWebView) |
| Data engine | Python FastAPI + JS fetch | Rust core (arena alloc, SIMD filter, interval tree) |
| Frontend | React 19 in browser | React 19 in Tauri webview (virtual scroll + canvas) |
| Visualizations | SVG elements (18K+ DOM nodes) | WebGPU compute shaders (single draw call) |
| IPC | HTTP + JSON serialize (12MB) | Tauri zero-copy commands (<1ms) |
| NLP pipeline | Python in-process | Python subprocess managed by Rust tokio |
| Search | JS String.indexOf loop | Rust suffix array (O(m log n)) |
| Multi-document | Impossible (OOM at 3 novels) | 1.5MB per novel in Rust arena |
| Annotation storage | JS objects (3.5KB each) | PackedAnnotation (16 bytes each, 217x reduction) |

## v4.0 Performance Targets (CI-enforced)

| Operation | Threshold | Technique |
|-----------|-----------|-----------|
| Project load (full novel) | <100ms | Rust arena parse from mmap'd JSONL |
| Track toggle | <2ms | SIMD bitmask filter + range query |
| Scroll (new viewport) | <5ms | Virtual scroll + canvas overlay |
| Text search | <10ms | Rust suffix array |
| OverviewBar render | <1ms | WebGPU density compute shader |
| Filter by confidence | <50μs | ARM NEON vectorized pass |
| Load 5 novels | <500ms total | 1.5MB packed per novel |
| Alignment dotplot | <100ms | GPU compute shader |

## v4.0 Hardware Target

M4 Max Mac Studio: 128GB unified RAM, 16 cores (12P+4E), 40 GPU cores, 273 GB/s memory bandwidth. Design assumes high hardware floor — no degradation for low-end devices. macOS-first; cross-platform via Tauri later.

---
**Duration**: 10 weeks (50 working days)
**Exit gate**: A literary scholar imports a novel and produces a multi-track structural overview in <30 minutes

## Revision History

| Version | Change | Source |
|---|---|---|
| v1.0 (doc 13) | Original Phase 1 plan | Roadmap doc 12 |
| v2.0 (doc 14) | Incorporated 20 findings from critical review (doc 13a) | Critical review doc 13a |
| v3.0 (this) | Corrected annotation format to W3C Web Annotation JSON-LD per research (docs 07-11); added JBrowse 2 architectural alignment; added evidence hierarchy; defined Palimpsest body types | Full research corpus review |

### v3.0 Key Corrections

1. **Annotation format**: W3C Web Annotation (JSON-LD) is the **primary** format, stored as JSONL (one annotation per line). PAF (GFF3-analogue TSV) is an **export** format for computational operations. This corrects a hierarchy inversion in v2.0 that contradicted research documents 07 §6.2, 08 §Recommendations, and 11 §5.2.
2. **Browser architecture**: Adopts JBrowse 2's adapter/track/display/renderer pattern as reference architecture, per research documents 09 §4.3, 10, and 11 §7.
3. **Evidence hierarchy**: Annotations carry evidence levels (E1-E5) per research document 07 §4.1, not just raw confidence scores.
4. **Custom body types**: Palimpsest-specific W3C body types defined for Phase 1 tracks, per doc 07 §7.1.
5. **ModeHMM**: K-means alphabet explicitly documented as Phase 1 placeholder for ModeHMM (Phase 2+), per doc 11.

---

## 0. Phase 1 Constraints and Policies

### 0.1 What Phase 1 Is

Phase 1 delivers a **read-only analytical tool**: import a text, compute features, view results. There is no human annotation UI, no custom schemas, no alignment engine. Those come in Phase 2 and 3. Phase 1's job is to prove that the core pipeline works, the browser is responsive, and the analytical results are meaningful.

### 0.2 Format Instability Policy

During Phase 1, the W3C body type schemas are unstable. They will evolve as new tracks reveal requirements the initial design didn't anticipate. This is acceptable because:
- All annotation files are recomputable from source text + pipeline version
- No user-created annotations exist yet (human annotation is Phase 2)
- Upgrading between Phase 1 milestones may require re-ingesting projects

Body type schemas will be declared v1.0 (stable) at the end of Phase 1. After that, only backward-compatible changes are permitted.

### 0.3 English-Only

Phase 1 supports English-language texts only. The data model is language-agnostic, but all feature extractors (NER, sentiment, topic modeling, BookNLP) are English-specific. Non-English texts can be ingested but will produce incomplete or incorrect tracks — this is documented, not hidden.

### 0.4 Local-Only

No cloud services. No user accounts. No collaboration. The entire platform runs on one machine. The browser connects to a local server. All data lives in the project directory on the local filesystem.

### 0.5 Scheduling Policy

Day-level estimates in this plan are **aspirational reference points**. Milestones and their smoke tests are the actual commitments. Within a milestone, the implementer has freedom to reorder tasks as discovery demands. A task taking longer than estimated is normal; a milestone deadline slipping is a signal to reassess scope.

### 0.6 Git Workflow

- **Branching**: trunk-based development (commit to `main`). Feature branches for multi-day experiments; merged via squash commit.
- **Commit messages**: Conventional Commits (`feat:`, `fix:`, `chore:`, `docs:`, `test:`, `refactor:`).
- **Tags**: milestone completion tagged as `v0.1.0` (Milestone 1.1), `v0.2.0` (1.2), `v0.3.0` (1.3a), `v0.4.0` (1.3b), `v0.5.0` (1.4), `v1.0.0` (Phase 1 complete).
- **Changelog**: auto-generated from commit messages using `git-cliff` or manual curation per milestone.

### 0.7 Code Quality Standards

Set up on **Day 1** before any application code is written:

**Python**:
- Linter + formatter: `ruff check` + `ruff format`
- Type checking: `mypy --strict` on `core/palimpsest/` interfaces and data classes
- Pre-commit: `pre-commit` hooks running ruff + mypy

**TypeScript**:
- Linter: `eslint` with `@typescript-eslint/recommended`
- Formatter: `prettier`
- Type checking: `tsc --strict`
- Pre-commit: eslint + prettier via `lint-staged`

---

## 1. Source Code Layout

```
palimpsest/
├── core/                        # Python backend (pip-installable package)
│   ├── palimpsest/
│   │   ├── __init__.py
│   │   ├── cli.py               # CLI entry points (ingest, analyze, serve, export)
│   │   ├── ingest/
│   │   │   ├── __init__.py
│   │   │   ├── extractor.py     # PDF/EPUB/TXT → raw text
│   │   │   ├── normalizer.py    # Unicode NFC, whitespace, SHA-256
│   │   │   └── segmenter.py     # Sentence/paragraph/section splitting
│   │   ├── tracks/
│   │   │   ├── __init__.py
│   │   │   ├── base.py          # TrackExtractor protocol + evidence levels
│   │   │   ├── registry.py      # Auto-discovery + registration (JBrowse 2 pattern)
│   │   │   ├── entities.py      # spaCy NER → W3C annotations
│   │   │   ├── sentiment.py     # VADER → W3C annotations
│   │   │   ├── lexical.py       # TTR, hapax → W3C annotations
│   │   │   ├── dialogue.py      # Quote detection → W3C annotations
│   │   │   ├── topics.py        # LDA → W3C annotations
│   │   │   ├── narrative_arc.py # Boyd 15-dim → signal
│   │   │   ├── self_similarity.py # Embedding cosine → signal
│   │   │   ├── rqa.py           # Recurrence quantification → signal
│   │   │   ├── alphabet.py      # K-means encoding → signal (ModeHMM placeholder)
│   │   │   ├── coreference.py   # BookNLP coref → W3C annotations
│   │   │   └── booknlp_enrichment.py
│   │   ├── annotation/          # W3C Web Annotation model
│   │   │   ├── __init__.py
│   │   │   ├── model.py         # Annotation dataclasses (W3C compliant)
│   │   │   ├── bodies.py        # Palimpsest body types (§2.3)
│   │   │   ├── serializer.py    # JSONL read/write/validate
│   │   │   └── paf_export.py    # W3C → PAF export converter
│   │   ├── formats/
│   │   │   ├── __init__.py
│   │   │   └── signals.py       # Signal (raw binary + JSON manifest) I/O
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── embedding.py     # Ollama embedding client
│   │   │   ├── llm.py           # Ollama LLM client
│   │   │   └── manager.py       # Service lifecycle (start/stop/health)
│   │   ├── vectorstore/
│   │   │   ├── __init__.py
│   │   │   ├── protocol.py      # VectorStore protocol (add, search, count)
│   │   │   └── sqlite_vec.py    # sqlite-vec implementation
│   │   ├── project.py           # Project directory management
│   │   └── server.py            # FastAPI server (static + API endpoints)
│   ├── tests/
│   │   ├── fixtures/            # Public domain test texts
│   │   │   ├── pride-prejudice-ch1.txt
│   │   │   ├── pride-prejudice-ch1.pdf
│   │   │   ├── moby-dick-ch1.txt
│   │   │   └── expected/        # Expected JSONL outputs for regression
│   │   ├── test_ingest.py
│   │   ├── test_annotation.py   # W3C model + serializer tests
│   │   ├── test_tracks.py
│   │   ├── test_registry.py
│   │   ├── test_vectorstore.py
│   │   ├── test_paf_export.py   # W3C → PAF export tests
│   │   └── test_pipeline.py
│   ├── pyproject.toml
│   └── README.md
├── browser/                     # React frontend (JBrowse 2 architectural pattern)
│   ├── src/
│   │   ├── App.tsx
│   │   ├── components/
│   │   │   ├── Layout/
│   │   │   │   ├── AppLayout.tsx
│   │   │   │   ├── ResizablePanel.tsx
│   │   │   │   └── Toolbar.tsx
│   │   │   ├── TextLinearView/      # (≈ JBrowse LinearGenomeView)
│   │   │   │   ├── TextLinearView.tsx
│   │   │   │   ├── AnnotationOverlay.tsx
│   │   │   │   ├── VirtualScroller.tsx
│   │   │   │   ├── SemanticZoom.tsx
│   │   │   │   └── TextSearch.tsx
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
│   │   │   ├── CrossTextDotplot/
│   │   │   │   └── CrossTextDotplot.tsx
│   │   │   └── common/
│   │   │       ├── LoadingOverlay.tsx
│   │   │       └── ProgressBar.tsx
│   │   ├── stores/
│   │   │   ├── projectStore.ts    # Zustand: loaded project data
│   │   │   ├── viewStore.ts       # Zustand: viewport, zoom, selection
│   │   │   ├── trackStore.ts      # Zustand: visibility, colors, filters
│   │   │   └── searchStore.ts     # Zustand: text search state
│   │   ├── adapters/              # (≈ JBrowse TrackAdapters)
│   │   │   ├── AnnotationAdapter.ts  # Reads JSONL → W3C annotation objects
│   │   │   ├── SignalAdapter.ts      # Reads raw binary → typed arrays
│   │   │   └── TrackManifest.ts      # Track rendering manifest loader
│   │   ├── registry/              # (≈ JBrowse PluginManager)
│   │   │   ├── TrackRendererRegistry.ts
│   │   │   └── defaultRenderers.ts
│   │   └── utils/
│   │       ├── offsets.ts
│   │       ├── colors.ts
│   │       └── keyboard.ts
│   ├── index.html
│   ├── vite.config.ts
│   ├── tsconfig.json
│   └── package.json
├── fixtures/                    # Test data (checked into repo)
│   ├── pride-prejudice-ch1.txt
│   ├── pride-prejudice-ch1.pdf
│   ├── moby-dick-ch1.txt
│   ├── pride-prejudice-full.txt
│   ├── swinehart/               # Swinehart datasets (gitignored)
│   ├── ij/                      # IJ files (gitignored)
│   └── expected/                # Expected JSONL outputs for regression
├── specs/
│   ├── annotation-model.md      # W3C body types + evidence hierarchy
│   ├── LFO.md                   # Literary Feature Ontology
│   ├── signals.md               # Signal format specification
│   └── PAF-export.md            # PAF export format (GFF3-analogue)
└── docs/
    └── architecture/
        ├── ADR-001-annotation-format.md   # W3C chosen over custom PAF
        ├── ADR-002-track-registry.md
        ├── ADR-003-signal-format.md
        ├── ADR-004-state-management.md
        ├── ADR-005-jbrowse2-patterns.md   # Architectural reference
        └── ...
```

---

## 2. Data Formats

### 2.1 Annotation Format: W3C Web Annotation (JSON-LD)

**This is the primary annotation format for Palimpsest.** Per research documents 07 §6.2 (*"The W3C Web Annotation Data Model replaces our ad-hoc PAF format"*), 08 §Recommendations (*"Build Palimpsest's data model around the W3C Web Annotation Data Model"*), and 11 §5.2 (*"All annotations use the W3C Web Annotation Data Model"*).

Each annotation is a standalone JSON-LD object:

```json
{
  "@context": [
    "http://www.w3.org/ns/anno.jsonld",
    {"palimpsest": "https://palimpsest.dev/ns/"}
  ],
  "type": "Annotation",
  "id": "urn:palimpsest:pride-and-prejudice:entities:e001",
  "body": {
    "type": "palimpsest:EntityAnnotation",
    "value": "Mr. Bennet",
    "purpose": "classifying",
    "palimpsest:entityType": "PER",
    "palimpsest:lfoType": "entity.character"
  },
  "target": {
    "source": "urn:palimpsest:pride-and-prejudice",
    "selector": {
      "type": "TextPositionSelector",
      "start": 14,
      "end": 23
    }
  },
  "creator": {
    "type": "Software",
    "name": "spacy/en_core_web_lg/3.7.4"
  },
  "palimpsest:confidence": 0.95,
  "palimpsest:evidenceLevel": "E4"
}
```

**Why W3C over a custom format:**
- **Overlapping annotations are natural** — each annotation is an independent object; no TSV row-overlap problems
- **Multiple selectors** — `TextPositionSelector` (fast offset lookup), `TextQuoteSelector` (robust to edits), combinable via `RefinedBy`
- **Multiple bodies** — a single annotation can carry a classification, a tag, and a link simultaneously
- **Interoperability** — Hypothes.is, INCEpTION, Annotation Studio all speak this format
- **Browser-native** — JSON is the natural wire format for `fetch()`; no TSV parsing needed
- **Extensibility** — custom body types are just JSON objects with Palimpsest-namespaced properties

### 2.2 Track Files: JSONL (One Annotation Per Line)

Track annotations are stored as **JSONL** (JSON Lines) — one W3C annotation per line. This gives:
- **Streamability**: process line-by-line without loading entire file into memory
- **grep-friendliness**: `grep "Mr. Bennet" tracks/entities.jsonl` works
- **Standards compliance**: each line is a valid W3C Web Annotation JSON-LD object
- **Browser loading**: `fetch()` → split by newlines → `JSON.parse()` each line

```
tracks/
├── entities.jsonl          # Entity annotations (PER, LOC, ORG)
├── sentiment.jsonl         # Per-sentence sentiment scores
├── lexical.jsonl           # Per-paragraph lexical statistics
├── dialogue.jsonl          # Quoted speech detection + attribution
├── topics.jsonl            # Per-paragraph topic assignments
└── coreference.jsonl       # Coreference chains (BookNLP, optional)
```

**File structure**: no header rows. Each line is a complete, self-contained W3C annotation. Lines are ordered by `target.selector.start` (character offset) for efficient sequential access.

**Python I/O** (`annotation/serializer.py`):
```python
def write_track(path: Path, annotations: list[Annotation]) -> None:
    sorted_anns = sorted(annotations, key=lambda a: a.target.selector.start)
    with open(path, 'w') as f:
        for ann in sorted_anns:
            f.write(json.dumps(ann.to_jsonld(), ensure_ascii=False) + '\n')

def read_track(path: Path) -> list[Annotation]:
    with open(path) as f:
        return [Annotation.from_jsonld(json.loads(line)) for line in f if line.strip()]
```

**Browser I/O** (`AnnotationAdapter.ts`):
```typescript
async function loadTrack(url: string): Promise<Annotation[]> {
  const text = await fetch(url).then(r => r.text());
  return text.trim().split('\n').map(line => JSON.parse(line));
}
```

### 2.3 Palimpsest Body Types

Custom W3C body types for Phase 1 tracks. Each extends the W3C `body` with Palimpsest-namespaced properties (per doc 07 §7.1):

| Body Type | Used By | Properties | W3C `purpose` |
|---|---|---|---|
| `palimpsest:EntityAnnotation` | entities.jsonl | `entityType` (PER/LOC/ORG/WORK), `canonicalName`, `mentionType` (name/pronoun/description) | `classifying` |
| `palimpsest:SentimentAnnotation` | sentiment.jsonl | `valence` (-1.0 to 1.0), `arousal` (0.0 to 1.0), `model` (vader) | `describing` |
| `palimpsest:LexicalAnnotation` | lexical.jsonl | `ttr`, `hapaxCount`, `meanWordLength`, `vocabularyRichness` | `describing` |
| `palimpsest:DialogueAnnotation` | dialogue.jsonl | `quoteType` (direct/indirect), `speaker` (if attributed), `verb` (said/asked/etc.) | `tagging` |
| `palimpsest:TopicAnnotation` | topics.jsonl | `topicId`, `topicWeight`, `topicTerms` (top 5 words) | `classifying` |
| `palimpsest:CoreferenceAnnotation` | coreference.jsonl | `chainId`, `referentId`, `mentionType` | `linking` |

**Example: Sentiment annotation**
```json
{
  "@context": ["http://www.w3.org/ns/anno.jsonld", {"palimpsest": "https://palimpsest.dev/ns/"}],
  "type": "Annotation",
  "id": "urn:palimpsest:pride-and-prejudice:sentiment:s001",
  "body": {
    "type": "palimpsest:SentimentAnnotation",
    "purpose": "describing",
    "palimpsest:valence": 0.74,
    "palimpsest:arousal": 0.31,
    "palimpsest:model": "vader",
    "palimpsest:lfoType": "signal.sentiment"
  },
  "target": {
    "source": "urn:palimpsest:pride-and-prejudice",
    "selector": {"type": "TextPositionSelector", "start": 0, "end": 178}
  },
  "creator": {"type": "Software", "name": "vaderSentiment/3.3"},
  "palimpsest:confidence": 0.82,
  "palimpsest:evidenceLevel": "E4"
}
```

**Example: Dialogue annotation**
```json
{
  "@context": ["http://www.w3.org/ns/anno.jsonld", {"palimpsest": "https://palimpsest.dev/ns/"}],
  "type": "Annotation",
  "id": "urn:palimpsest:pride-and-prejudice:dialogue:d001",
  "body": {
    "type": "palimpsest:DialogueAnnotation",
    "purpose": "tagging",
    "value": "My dear Mr. Bennet, have you heard that Netherfield Park is let at last?",
    "palimpsest:quoteType": "direct",
    "palimpsest:speaker": "Mrs. Bennet",
    "palimpsest:verb": "said",
    "palimpsest:lfoType": "structural.dialogue.quote"
  },
  "target": {
    "source": "urn:palimpsest:pride-and-prejudice",
    "selector": {"type": "TextPositionSelector", "start": 245, "end": 316}
  },
  "creator": {"type": "Software", "name": "palimpsest-dialogue/0.1"},
  "palimpsest:confidence": 0.90,
  "palimpsest:evidenceLevel": "E4"
}
```

### 2.4 Evidence Hierarchy

Per research document 07 §4.1, every annotation carries an evidence level indicating its provenance quality:

| Level | Source | Phase 1 Usage | Confidence Range |
|---|---|---|---|
| **E1** | Explicit in text (direct extraction) | Structural segmentation (paragraph/section boundaries) | 1.0 |
| **E2** | Human annotator | Not used in Phase 1 (Phase 2) | 0.7-1.0 |
| **E3** | Cross-text homology (alignment) | Not used in Phase 1 (Phase 3) | 0.5-0.9 |
| **E4** | ML prediction (trained model) | NER, coreference, dialogue attribution, topics | 0.3-0.95 |
| **E5** | Ab initio prediction (rule-based/statistical) | Sentiment (VADER), lexical stats, narrative arc | 0.5-0.9 |

Phase 1 tracks are all E1 (segmentation), E4 (spaCy NER, BookNLP, LDA), or E5 (VADER, lexical, narrative arc). The evidence level is stored on every annotation as `palimpsest:evidenceLevel` and is displayed in the browser's DetailPanel alongside the confidence score.

### 2.5 Signals (Non-Span Data)

Signals are **not annotations** — they are continuous numerical data (matrices, vectors, sequences) that don't fit the W3C annotation model. They remain stored as raw binary with JSON manifests, unchanged from v2.0.

**JSON manifest** (in `signals/`):
```json
{
  "type": "matrix",
  "name": "self_similarity",
  "source": "embedding_cosine/0.1",
  "reference_sha256": "a1b2c3d4...",
  "dimensions": [200, 200],
  "dtype": "float32",
  "byte_order": "little-endian",
  "data_file": "self_similarity.bin",
  "segment_offsets": [[0, 423], [424, 891]],
  "metadata": {
    "similarity_metric": "cosine",
    "embedding_model": "qwen3-embedding-4b"
  }
}
```

**Binary data**: raw little-endian Float32 bytes. Row-major order (C-contiguous).

**Signal types**:
- `matrix` — 2D array (self-similarity, cross-text similarity). Binary file, shape in manifest.
- `vector` — 1D array (narrative arc, sequential scores). Binary file, length in manifest.
- `sequence` — categorical string (narrative alphabet). Stored inline in manifest JSON, no binary file.
- `distribution` — per-segment probability vectors (topic distributions). Binary file, shape `[n_segments, n_topics]`.

### 2.6 Project Directory

```
projects/{text-id}/
├── reference.txt              # Normalized text (immutable after ingest)
├── reference.sha256           # SHA-256 of reference.txt
├── metadata.json              # Schema defined in §2.7
├── pipeline_run.json          # Provenance record (§2.8)
├── tracks/                    # W3C Web Annotation JSONL files
│   ├── segments.jsonl         # Structural segmentation (sentences, paragraphs, sections)
│   ├── entities.jsonl         # Named entities
│   ├── sentiment.jsonl        # Sentiment scores
│   ├── lexical.jsonl          # Lexical statistics
│   ├── dialogue.jsonl         # Quoted speech
│   ├── topics.jsonl           # Topic assignments
│   └── coreference.jsonl      # Coreference chains (BookNLP, optional)
├── signals/                   # Non-span numerical data (raw binary + JSON manifest)
│   ├── self_similarity.json
│   ├── self_similarity.bin
│   ├── narrative_arc.json
│   ├── narrative_arc.bin
│   ├── rqa.json
│   ├── rqa.bin
│   ├── topics_dist.json
│   ├── topics_dist.bin
│   └── alphabet.json          # Inline sequence string
├── manifests/                 # Track rendering manifests
│   ├── entities.manifest.json
│   ├── sentiment.manifest.json
│   └── ...
├── cache/
│   ├── spacy_docs.pkl
│   ├── embeddings.db          # sqlite-vec
│   └── booknlp/
├── x-config/                  # Extension configuration (scaffolded, empty in Phase 1)
│   ├── schemas/
│   └── detectors/
└── exports/                   # User-requested exports
    ├── w3c/                   # W3C AnnotationCollection JSON-LD
    ├── paf/                   # PAF GFF3-analogue TSV
    └── csv/                   # Flat CSV
```

### 2.7 Metadata Schema

Every project contains `metadata.json`:

```json
{
  "id": "pride-and-prejudice",
  "title": "Pride and Prejudice",
  "author": "Jane Austen",
  "year": 1813,
  "language": "en",
  "source_format": "txt",
  "source_file": "pride-and-prejudice.txt",
  "ingest_date": "2026-06-10",
  "palimpsest_version": "0.1.0",
  "reference_sha256": "a1b2c3d4...",
  "word_count": 122189,
  "paragraph_count": 1832,
  "section_count": 61,
  "sentence_count": 6437,
  "character_count": 684459
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `id` | string | yes | URL-safe slug (directory name) |
| `title` | string | yes | Human-readable title |
| `author` | string | no | Author name(s) |
| `year` | int | no | Year of publication/composition |
| `language` | string | yes | ISO 639-1 code |
| `source_format` | string | yes | Original file format (`txt`, `pdf`, `epub`) |
| `source_file` | string | yes | Original filename |
| `ingest_date` | string | yes | ISO 8601 date |
| `palimpsest_version` | string | yes | Version that performed ingestion |
| `reference_sha256` | string | yes | SHA-256 of reference.txt |
| `word_count` | int | yes | Whitespace-delimited token count |
| `paragraph_count` | int | yes | Paragraph count |
| `section_count` | int | yes | Detected section/chapter count |
| `sentence_count` | int | yes | Sentence count (spaCy) |
| `character_count` | int | yes | Unicode character count |

### 2.8 Pipeline Run Provenance

Every `palimpsest analyze` invocation writes `pipeline_run.json`:

```json
{
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2026-06-10T14:30:00Z",
  "palimpsest_version": "0.1.0",
  "python_version": "3.12.5",
  "spacy_model": "en_core_web_lg/3.7.4",
  "annotation_format": "W3C Web Annotation JSON-LD (JSONL)",
  "tracks_computed": ["entities", "sentiment", "lexical", "dialogue", "topics"],
  "signals_computed": ["narrative_arc", "self_similarity", "rqa", "topics_dist", "alphabet"],
  "parameters": {
    "topics.n_topics": 10,
    "topics.random_state": 42,
    "alphabet.n_clusters": 16,
    "alphabet.random_state": 42,
    "sentiment.model": "vader",
    "entities.spacy_model": "en_core_web_lg",
    "self_similarity.embedding_model": "qwen3-embedding-4b"
  },
  "elapsed_seconds": 24.7,
  "booknlp_available": false
}
```

### 2.9 PAF Export Format

PAF (Palimpsest Annotation Format) is a **GFF3-analogue TSV** for computational operations — filtering, intersection, coverage computation, and interop with genomics-style tooling (bedtools-equivalents). It is an **export** format, not the primary storage format.

```
##palimpsest-paf-version 0.1
##reference-sha256 a1b2c3d4...
##reference-file reference.txt
##exported-from W3C Web Annotation JSONL
#docname	source	type	start	end	score	strand	phase	attributes
pride_prejudice	spacy/3.7	entity.character	14	23	0.95	.	.	ID=e001;Name=Mr. Bennet;entity_type=PER;evidence=E4
```

**Reserved PAF attributes** (for forward compatibility):
- `Target` — cross-span reference: `Target=<docname> <start> <end>`
- `Relation` — typed relationship: `Relation=<type>:<target_ID>`

Export: `palimpsest export <project-dir> --format paf`

---

## 3. Track Extensibility Protocol

### 3.1 Architectural Reference: JBrowse 2

Per research documents 09 §4.3 and 11 §7, Palimpsest's text browser follows JBrowse 2's **adapter/track/display/renderer** hierarchy — not as a dependency, but as an architectural pattern:

| JBrowse 2 Concept | Palimpsest Equivalent | Description |
|---|---|---|
| `TrackAdapter` | `TrackExtractor` (Python) | Reads source data, produces structured annotations |
| `PluginManager.addTrackType()` | `TrackRegistry.register()` | Registers new track types without modifying core code |
| `Track` | Track JSONL file | Computed annotation data |
| `Display` | `TrackManifest` | Rendering configuration (colors, style, view strategy) |
| `Renderer` | `TrackRendererRegistry` (browser) | Maps manifest to React rendering components |

This pattern is architecturally load-bearing: **the entire Base/X thesis depends on new tracks being addable without modifying Base code.**

### 3.2 Python: TrackExtractor Protocol + Registry

Every track implements the `TrackExtractor` protocol:

```python
from typing import Protocol, Literal, runtime_checkable
from palimpsest.annotation.model import Annotation

@runtime_checkable
class TrackExtractor(Protocol):
    @property
    def name(self) -> str: ...

    @property
    def output_type(self) -> Literal["annotation", "signal"]: ...

    @property
    def depends_on(self) -> list[str]: ...

    @property
    def lfo_types(self) -> list[str]: ...

    @property
    def evidence_level(self) -> str:
        """E1-E5 per the evidence hierarchy."""
        ...

    def extract(self, project: Project) -> list[Annotation] | Path:
        """Returns W3C annotations (for annotation tracks) or a signal path."""
        ...

    def manifest(self) -> dict:
        """Track rendering manifest for the browser."""
        ...
```

The `TrackRegistry` discovers all `TrackExtractor` implementations:

```python
class TrackRegistry:
    _extractors: dict[str, type[TrackExtractor]]

    @classmethod
    def discover(cls) -> "TrackRegistry":
        """Auto-discover all TrackExtractor subclasses in the tracks package."""
        ...

    def get(self, name: str) -> type[TrackExtractor]: ...

    def all(self) -> list[type[TrackExtractor]]: ...

    def dependency_order(self) -> list[type[TrackExtractor]]:
        """Topological sort by depends_on."""
        ...
```

Discovery uses Python's `__subclasses__()` mechanism. Phase 2's X tracks register via the same mechanism from `x-config/detectors/`.

### 3.3 Browser: TrackRenderer Registry

Each track type registers a rendering manifest:

```typescript
interface TrackManifest {
  trackName: string;
  bodyType: string; // Palimpsest body type name
  colorScheme: { primary: string; secondary: string; scale?: string[] };
  textViewRendering: "highlight" | "underline" | "margin-marker";
  overviewBarRendering: { type: "density-barcode"; color: string };
  dedicatedView?: string;
}
```

Base tracks ship with built-in manifests. The browser reads `manifests/*.manifest.json` from the project directory for custom/X tracks. Unknown track types fall back to generic gray highlight + density barcode.

---

## 4. Analysis Units

| Unit | Definition | Used by | Granularity |
|---|---|---|---|
| **Character** | Single Unicode code point in reference.txt | Offset indexing, W3C TextPositionSelector | Finest |
| **Token** | spaCy token | NER, POS analysis | Sub-sentence |
| **Sentence** | spaCy sentence boundary | Sentiment, base segmentation | Fine |
| **Paragraph** | Double-newline delimited block | Topics, lexical stats, default unit | Medium |
| **Section** | Detected chapter/heading boundary | Overview aggregation | Coarse |
| **Span** | Arbitrary `[start, end)` range (W3C TextPositionSelector) | Entity mentions, dialogue quotes, any annotation | Variable |

---

## 5. Track Inventory (Final, Phase 1)

### 5.1 Annotation Tracks (6 JSONL files in `tracks/`)

All tracks produce W3C Web Annotation objects with Palimpsest body types (§2.3).

| # | File | Body Type | Source | Evidence | Depends on |
|---|---|---|---|---|---|
| 1 | `entities.jsonl` | `EntityAnnotation` | spaCy NER (`en_core_web_lg`) or BookNLP | E4 | spaCy parse |
| 2 | `sentiment.jsonl` | `SentimentAnnotation` | VADER | E5 | spaCy parse |
| 3 | `lexical.jsonl` | `LexicalAnnotation` | Custom computation | E5 | Tokenization |
| 4 | `dialogue.jsonl` | `DialogueAnnotation` | Regex + BookNLP | E4/E5 | spaCy parse |
| 5 | `topics.jsonl` | `TopicAnnotation` | LDA (`random_state=42`) | E4 | Tokenization |
| 6 | `coreference.jsonl` | `CoreferenceAnnotation` | BookNLP (optional) | E4 | entities track |

### 5.2 Signal Files (4 signal sets in `signals/`)

Signals are not W3C annotations — they are continuous numerical data.

| # | Manifest | Type | Source | Format | Depends on |
|---|---|---|---|---|---|
| 7 | `narrative_arc.json` | vector (15-dim × 5 segments) | Boyd function-word arc | Float32 binary | Tokenization |
| 8 | `self_similarity.json` | matrix (N×N paragraphs) | Embedding cosine | Float32 binary | Embeddings |
| 9 | `rqa.json` | vector (RR, DET, LAM per window) | RQA computation | Float32 binary | Tokenization |
| 10 | `alphabet.json` | sequence (string of N letters) | K-means (`random_state=42`) | Inline JSON | Tracks 2-5 |

**Note on Track 10 (Alphabet)**: The K-means narrative alphabet is a **Phase 1 placeholder** for the ModeHMM (ChromHMM-analogue) described in doc 11. ModeHMM jointly trains 15-25 passage-function states on a corpus of 60+ texts. Since Phase 1 operates on individual texts without a training corpus, K-means clustering provides a reasonable single-text approximation. Phase 2 will introduce ModeHMM trained on 60 Project Gutenberg novels across 6 genres.

### 5.3 Dependency DAG

```
reference.txt
  → spaCy parse (en_core_web_lg, cached in cache/spacy_docs.pkl)
    → entities.jsonl [Track 1]  (W3C EntityAnnotation, evidence E4)
    → sentiment.jsonl [Track 2]  (W3C SentimentAnnotation, evidence E5)
    → dialogue.jsonl [Track 4]  (W3C DialogueAnnotation, evidence E4)
  → tokenization
    → lexical.jsonl [Track 3]  (W3C LexicalAnnotation, evidence E5)
    → topics.jsonl [Track 5]  (W3C TopicAnnotation, evidence E4)
    → narrative_arc signal [Track 7]
    → rqa signal [Track 9]
  → embeddings (cached in cache/embeddings.db via VectorStore)
    → self_similarity signal [Track 8]
  → tracks 2-5 features
    → alphabet signal [Track 10]  (Phase 1 placeholder for ModeHMM)
  → BookNLP (optional, cached in cache/booknlp/)
    → entities.jsonl enrichment [Track 1 update]
    → dialogue.jsonl enrichment [Track 4 update]
    → coreference.jsonl [Track 6]  (W3C CoreferenceAnnotation, evidence E4)
```

### 5.4 Determinism Policy

All stochastic algorithms use fixed random seeds:
- `sklearn.decomposition.LatentDirichletAllocation(random_state=42)`
- `sklearn.cluster.KMeans(random_state=42, n_init=10)`
- Any future stochastic algorithm must default to `random_state=42`

Regression tests compare JSONL output line-by-line (parsing JSON, comparing annotation content while ignoring `id` UUIDs and timestamps). Signal binary files are compared byte-identical. Determinism is guaranteed only with the same Python version, sklearn version, and random seed — documented in `pipeline_run.json`.

---

## 6. Vector Store Abstraction

```python
from typing import Protocol

class VectorStore(Protocol):
    def add(self, ids: list[str], vectors: list[list[float]], metadata: list[dict] | None = None) -> None: ...
    def search(self, query: list[float], k: int = 10) -> list[tuple[str, float]]: ...
    def count(self) -> int: ...
    def delete(self, ids: list[str]) -> None: ...
```

`SqliteVecStore` is the Phase 1 implementation. If sqlite-vec has issues, a `FaissStore` can be swapped in via the same protocol.

---

## 7. Browser Layout

### 7.1 Default Layout

```
┌───────────────────────────────────────────────────────────────────┐
│ Toolbar: project name │ view selector │ zoom │ search (Ctrl+F)   │
├──────────┬──────────────────────────────┬─────────────────────────┤
│          │                              │                         │
│  Track   │     TextLinearView           │   Detail Panel          │
│  Panel   │     (main reading area)      │   (annotation details,  │
│  (left   │     with annotation          │    evidence level,      │
│  sidebar │     overlays)                │    LLM summary)         │
│  ~200px) │                              │                         │
│          │                              │   (~280px, collapsible) │
├──────────┴──────────────────────────────┴─────────────────────────┤
│ OverviewBar (full-document density barcodes, ~60px)               │
├───────────────────────────────────────────────────────────────────┤
│ Secondary View: DotplotView / CrossTextDotplot                    │
│ (collapsible bottom panel, ~30% height when open)                 │
└───────────────────────────────────────────────────────────────────┘
```

All panels resizable via drag handles. Detail Panel and Secondary View are collapsible. On narrow screens (<1024px): Detail Panel overlays as a right drawer.

### 7.2 Keyboard Navigation

| Key | Action |
|---|---|
| `j` / `↓` | Next paragraph |
| `k` / `↑` | Previous paragraph |
| `Ctrl+F` / `/` | Open text search |
| `Escape` | Close search / deselect / collapse detail panel |
| `1`-`9` | Toggle track N visibility |
| `0` | Show all tracks |
| `d` | Toggle dotplot panel |
| `[` / `]` | Previous / next search result |
| `?` | Show keyboard shortcut help overlay |

### 7.3 Text Search

Phase 1 provides **text search** (words/phrases in reference text). Annotation search and cross-track queries are Phase 2 and Phase 5.

- `Ctrl+F` or `/` opens search bar
- Type-ahead highlighting in TextLinearView
- `Enter` / `]` to next match; `Shift+Enter` / `[` for previous
- Match count: "3 of 47 matches"
- Case-insensitive default; toggle via button
- OverviewBar shows match positions as yellow ticks

---

## 8. Browser ↔ Backend Communication

### 8.1 Server Architecture

```
palimpsest serve <workspace-dir> [--port 8080]
```

**Static routes** (`/data/*`): read-only, cacheable
- `GET /data/{project-id}/reference.txt`
- `GET /data/{project-id}/tracks/*.jsonl`
- `GET /data/{project-id}/signals/*.json`
- `GET /data/{project-id}/signals/*.bin`
- `GET /data/{project-id}/manifests/*.manifest.json`
- `GET /data/{project-id}/metadata.json`
- `GET /data/{project-id}/pipeline_run.json`

**API routes** (`/api/*`): dynamic
- `GET /api/projects` — list all projects in workspace
- `GET /api/search?project={id}&query={text}&k=10` — similarity search
- `POST /api/summarize` — LLM passage summarizer (proxies to Ollama)

### 8.2 Multi-Project Serving

`palimpsest serve <workspace-dir>` serves all project directories. `/api/projects` returns:

```json
[
  {"id": "pride-and-prejudice", "title": "Pride and Prejudice", "author": "Jane Austen", "word_count": 122189},
  {"id": "moby-dick", "title": "Moby-Dick", "author": "Herman Melville", "word_count": 206052}
]
```

---

## 9. Progress Reporting

### 9.1 CLI Progress

```
$ palimpsest analyze projects/pride-and-prejudice/
  Analyzing Pride and Prejudice (122,189 words)
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100%  spaCy parse      [00:08]
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100%  entities         [00:02]
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100%  sentiment        [00:01]
  ...
  ✓ 10 tracks computed in 29.4s (6 annotation tracks, 4 signals)
  ✓ Pipeline run saved: pipeline_run.json
```

### 9.2 Browser Loading

`LoadingOverlay.tsx`: full-screen overlay with loading steps. "Loading metadata..." → "Loading reference text..." → "Loading tracks (3/6)..." → "Loading signals (2/4)..." → auto-dismiss.

---

## 10. Milestone Detail

### Milestone 1.1: Ingest + Normalize + First Track + Minimal Browser (Week 1-2)

#### Week 1: Backend + Tooling

**Day 1: Project scaffolding + code quality**
- Initialize monorepo: `core/` (Python, pyproject.toml with hatch), `browser/` (React, Vite, TypeScript)
- Set up ruff, mypy, pre-commit (Python); eslint, prettier, tsc --strict (TypeScript)
- Set up pytest; Vitest
- Write ADR-001 (W3C Web Annotation chosen over custom PAF — rationale from docs 07-08)
- Write ADR-005 (JBrowse 2 architectural patterns)
- Git init, conventional commit config, `.gitignore`

**Day 2: Test fixtures + W3C annotation model + TrackExtractor protocol**
- Download _Pride and Prejudice_ from Project Gutenberg → `fixtures/pride-prejudice-full.txt`
- Extract P&P Chapter 1 → `fixtures/pride-prejudice-ch1.txt`; PDF version → `fixtures/pride-prejudice-ch1.pdf`
- Download _Moby-Dick_ Chapter 1 → `fixtures/moby-dick-ch1.txt`
- Implement W3C annotation model (`annotation/model.py`): `Annotation`, `Body`, `Target`, `Selector` dataclasses
- Implement Palimpsest body types (`annotation/bodies.py`): `EntityAnnotation`, `SentimentAnnotation`, etc.
- Implement JSONL serializer (`annotation/serializer.py`): read/write/validate
- Implement `TrackExtractor` protocol in `tracks/base.py` (including `evidence_level` property)
- Implement `TrackRegistry` in `tracks/registry.py`
- Tests: annotation model round-trip (Python object → JSON-LD → Python object); JSONL serializer; registry discovers track classes; dependency ordering

**Day 3: Ingestion pipeline**
- `extractor.py`: PDF (pymupdf) → raw text; EPUB (ebooklib) → raw text; TXT → passthrough
- `normalizer.py`: Unicode NFC, collapse whitespace, normalize quotes, SHA-256
- `segmenter.py`: spaCy `en_core_web_lg` sentence segmentation; paragraph detection; section detection
- `project.py`: create project directory, write `reference.txt`, `segments.jsonl` (structural annotations as W3C), `metadata.json`
- Tests: ingest P&P Chapter 1 from TXT and PDF; assert identical `reference.txt`; validate `metadata.json` schema

**Day 4: Entity track**
- `entities.py`: implements `TrackExtractor`; spaCy NER → `EntityAnnotation` W3C objects → `entities.jsonl`
- Each entity is a full W3C annotation with `TextPositionSelector`, `palimpsest:entityType`, `palimpsest:evidenceLevel: "E4"`
- Tests: entity track on P&P Chapter 1 detects "Mr. Bennet" (PER), "Hertfordshire" (LOC); JSONL round-trip; annotation validates against W3C schema

**Day 5: CLI + provenance**
- `cli.py` using Click: `palimpsest ingest <file>`, `palimpsest info <project-dir>`
- Writes `pipeline_run.json` on every `palimpsest analyze`
- Smoke test: `palimpsest ingest pride-prejudice-ch1.txt` → project with `tracks/entities.jsonl` + valid `pipeline_run.json`

#### Week 2: Browser

**Day 6-7: React scaffolding with Zustand**
- Vite + React + TypeScript + Zustand setup
- `AnnotationAdapter.ts`: fetch JSONL file → parse each line as JSON → return typed W3C annotation objects
- `projectStore.ts`: load `reference.txt` + `segments.jsonl` + `entities.jsonl` from `/data/`
- `AppLayout.tsx`: layout from §7.1
- `ResizablePanel.tsx`: drag-to-resize
- Minimal `TextLinearView.tsx`: render reference text as paragraphs

**Day 8-9: Annotation overlay + keyboard**
- `AnnotationOverlay.tsx`: render entity annotations as colored `<mark>` elements (reads `palimpsest:entityType` for color)
- Click entity → DetailPanel shows W3C annotation body, evidence level, confidence
- `keyboard.ts`: j/k navigation, 1-9 track toggle, Escape, ?
- `server.py`: FastAPI with static serving + `/api/projects`

**Day 10: Integration + smoke test**
- `palimpsest serve <project-dir>` launches server, opens browser
- End-to-end: ingest → serve → entities visible → keyboard works
- Track rendering manifest for entities

**Milestone 1.1 smoke test**:
```
$ palimpsest ingest fixtures/pride-prejudice-ch1.txt
  → Project created with tracks/entities.jsonl (W3C JSONL)
  → metadata.json + pipeline_run.json written
$ palimpsest serve projects/pride-prejudice-ch1/
  → "Mr. Bennet" highlighted; click → Detail Panel shows:
    body type: EntityAnnotation, entity: PER, evidence: E4, confidence: 0.95
  → j/k navigates paragraphs; '1' toggles entities
```

**Tag**: `v0.1.0`

---

### Milestone 1.2: Five Tracks + AI Summary + Search (Week 3-5)

#### Week 3: Four New Tracks

**Day 11-12: Sentiment + Lexical**
- Both implement `TrackExtractor`; produce W3C annotations with Palimpsest body types
- `sentiment.py`: VADER per sentence → `SentimentAnnotation` objects → `sentiment.jsonl` (evidence E5)
- `lexical.py`: per paragraph → `LexicalAnnotation` objects → `lexical.jsonl` (evidence E5)

**Day 13-14: Dialogue + Topics**
- `dialogue.py`: regex quoted speech → `DialogueAnnotation` → `dialogue.jsonl` (evidence E5)
- `topics.py`: LDA, 10 topics, `random_state=42` → `TopicAnnotation` → `topics.jsonl` (evidence E4); also writes `signals/topics_dist.json` + `.bin`

**Day 15: Pipeline orchestration via registry**
- `palimpsest analyze` runs all registered extractors via `TrackRegistry.dependency_order()`
- CLI progress bars via `rich`
- `pipeline_run.json` with all parameters
- Benchmark: full P&P, 5 tracks <30 seconds

#### Week 4: LLM + Browser + Search

**Day 16-17: Ollama service manager**
- `manager.py`, `llm.py`, `embedding.py` — uses `VectorStore` protocol

**Day 18-19: LLM summarizer + text search**
- `/api/summarize` endpoint; `LLMSummary.tsx` in DetailPanel
- `TextSearch.tsx`: Ctrl+F, type-ahead, match count

**Day 20: Track panel + overview bar**
- `TrackPanel.tsx`: list from registry manifests; toggle, color, count, confidence slider
- `OverviewBar.tsx`: density barcodes; click-to-navigate; search ticks
- `LoadingOverlay.tsx`: track-by-track loading progress

#### Week 5: Polish + Testing

**Day 21-22: Multi-track rendering**
- Overlapping strategy: primary = inline highlight; secondary = underline/margin; max 3 concurrent
- Colors from manifest (stable per track type)

**Day 23-24: Testing**
- Unit tests for all 5 extractors (P&P fixtures, W3C output validation)
- Integration: full pipeline → all JSONL files valid W3C
- Regression snapshots (JSONL content comparison, ignoring UUIDs/timestamps)
- `test_annotation.py`: body type validation, evidence level, JSON-LD compliance

**Day 25: Milestone 1.2 smoke test**
```
$ palimpsest analyze projects/pride-and-prejudice/
  ✓ 5 tracks (JSONL) computed in 24.7s
$ palimpsest serve projects/pride-and-prejudice/
  → 5 tracks in TrackPanel, each with evidence level badge
  → Ctrl+F → "Bennet" → 37 matches
  → Select paragraph → DetailPanel shows body type, evidence, confidence
  → Click "Summarize" → LLM summary
```

**Tag**: `v0.2.0`

---

### Milestone 1.3a: Remaining Base Tracks + Embedding Service (Week 5-7)

**Day 26-27: Embedding service + VectorStore**
- `SqliteVecStore` implements `VectorStore` protocol
- Batch embed all paragraphs; similarity search endpoint

**Day 28-29: Self-similarity matrix**
- `self_similarity.py`: pairwise cosine → `signals/self_similarity.json` + `.bin` (Float32)

**Day 30-31: Narrative arc + RQA + Alphabet**
- `narrative_arc.py`: Boyd 15-dim → signal binary
- `rqa.py`: RR/DET/LAM per window → signal binary
- `alphabet.py`: K-means `random_state=42`, 16 letters → inline JSON sequence
  - **Phase 1 placeholder**: This single-text K-means encoding will be replaced by ModeHMM (a ChromHMM-analogue jointly trained on 60+ texts) in Phase 2. The alphabet track's registry interface remains identical; only the implementation changes.

### Milestone 1.3b: BookNLP + DotplotView (Week 7-8)

**Day 32-33: BookNLP integration**
- `booknlp_enrichment.py`: updates `entities.jsonl` with canonical IDs; produces `coreference.jsonl` (`CoreferenceAnnotation`, evidence E4); updates `dialogue.jsonl` with speaker attribution
- Fallback: if BookNLP unavailable, 8 tracks instead of 10

**Day 34-36: DotplotView**
- Load `self_similarity.bin` via `SignalAdapter.ts` → `Float32Array` → Canvas heatmap
- Zoom, pan, click-to-navigate; `d` key toggles

**Day 37: Linked views**
- Zustand shared selection state across TextLinearView, DotplotView, OverviewBar

**Milestone 1.3 smoke test**:
```
$ palimpsest analyze projects/pride-and-prejudice/ --enrich
  ✓ 6 annotation tracks (JSONL) + 4 signals computed
$ palimpsest serve projects/pride-and-prejudice/
  → DotplotView: self-similarity with chapter blocks
  → Click cell → paragraphs highlighted
  → tracks/coreference.jsonl: W3C CoreferenceAnnotation objects
```

**Tag**: `v0.3.0` (1.3a), `v0.4.0` (1.3b)

---

### Milestone 1.4: Full Text Browser + Cross-Text Dotplot + Export (Week 8-10)

#### Week 8-9

**Day 38-40: Virtualized scrolling**
- `VirtualScroller.tsx`: viewport + 2-screen buffer; recycled DOM; Intersection Observer

**Day 41-42: Semantic zoom**
- Close (paragraph): individual annotation spans; Medium (chapter): density bars; Far (document): heatmap bars

**Day 43-44: Signal visualizations**
- Narrative arc sparkline, RQA bar chart, alphabet colored barcode, topic stacked bars

**Day 45: OverviewBar enhancements**
- Brush selection; stacked barcodes; search ticks

#### Week 9-10

**Day 46-47: Cross-text dotplot**
- `palimpsest serve <workspace-dir>` with `/api/projects`
- `CrossTextDotplot.tsx`: inter-text similarity matrix; project selector dropdown

**Day 48: Export (three formats)**
- `palimpsest export <project-dir> --format w3c` → W3C AnnotationCollection JSON-LD (one file per track, full `@context`)
- `palimpsest export <project-dir> --format paf` → PAF GFF3-analogue TSV (§2.9)
- `palimpsest export <project-dir> --format csv` → flat CSV
- `paf_export.py`: converts W3C annotations → PAF rows, preserving IDs and evidence levels
- Tests: round-trip validation (W3C → PAF → verify fields); W3C export validates against JSON-LD schema

**Day 49-50: Final polish + documentation**
- README.md: installation, quick start, keyboard shortcuts
- `specs/annotation-model.md`: W3C body types + evidence hierarchy
- `specs/LFO.md`: all ~60 Literary Feature Ontology terms
- `specs/signals.md`: raw binary format
- `specs/PAF-export.md`: PAF export format
- Final determinism regression tests

**Phase 1 exit smoke test**:
```
$ pip install palimpsest
$ palimpsest ingest pride-and-prejudice.txt
$ palimpsest analyze projects/pride-and-prejudice/
  ✓ 6 annotation tracks (W3C JSONL) + 4 signals in <30 seconds
$ palimpsest serve projects/
  → Project selector → Pride and Prejudice
  → Multi-track annotations (each showing body type, evidence level)
  → DotplotView, TrackPanel, OverviewBar all functional
  → Ctrl+F search, j/k navigation, 1-9 toggles
  → LLM summary (if Ollama running)
  → Cross-text dotplot with second text
  → Export W3C → valid AnnotationCollection JSON-LD
  → Export PAF → valid GFF3-analogue TSV
  → All tracks deterministic (re-analyze = identical output)

Time from install to first analysis: <5 minutes
Literary scholar produces structural overview: <30 minutes
```

**Tag**: `v0.5.0` (Milestone 1.4), then `v1.0.0` (Phase 1 complete)

---

## 11. Test Plan

### 11.1 Unit Tests (pytest, every commit)

| Module | Tests | Key assertions |
|---|---|---|
| `annotation/model.py` | 10 | W3C JSON-LD round-trip, selector types, body type validation, `@context` correctness |
| `annotation/bodies.py` | 8 | Each Palimpsest body type serializes correctly, required fields enforced |
| `annotation/serializer.py` | 6 | JSONL write/read, multi-line, empty file, malformed line handling |
| `paf_export.py` | 5 | W3C → PAF conversion, reserved attributes preserved, evidence level mapping |
| `normalizer.py` | 8 | NFC, whitespace, SHA-256, idempotency |
| `extractor.py` | 6 | PDF, EPUB, TXT, encoding |
| `segmenter.py` | 10 | Sentence/paragraph/section boundaries, offset accuracy |
| `registry.py` | 6 | Auto-discovery, dependency ordering, unknown name, duplicate name |
| `vectorstore/protocol.py` | 4 | Add/search/count/delete |
| `entities.py` | 5 | PER/LOC/ORG on P&P, W3C body type correct, evidence E4 |
| `sentiment.py` | 4 | Valence detection, W3C body, evidence E5 |
| `lexical.py` | 4 | TTR, hapax, W3C body, evidence E5 |
| `dialogue.py` | 6 | Quote detection, W3C body, speaker attribution |
| `topics.py` | 4 | 10 topics, W3C body, deterministic with seed |
| `narrative_arc.py` | 3 | 15-dim output, signal format |
| `self_similarity.py` | 3 | Matrix dimensions, diagonal, symmetry |
| `rqa.py` | 3 | Values in [0,1], window correctness |
| `alphabet.py` | 4 | Length matches paragraphs, deterministic with seed |
| `signals.py` | 4 | Binary write/read round-trip, manifest schema |
| `metadata` | 3 | Schema validation, required fields, counts correct |

**Total**: ~103 unit tests

### 11.2 Integration Tests (pytest, every PR)

| Test | What it validates |
|---|---|
| `test_full_pipeline` | Ingest → analyze → all JSONL valid W3C → all signals valid → `pipeline_run.json` written |
| `test_partial_recompute` | Change config → only affected tracks recomputed |
| `test_booknlp_fallback` | BookNLP failure → graceful fallback → 8 tracks |
| `test_ollama_absent` | Non-LLM features work → summarizer degrades |
| `test_determinism` | Run pipeline twice → JSONL content identical (ignoring UUIDs) |
| `test_multi_project_serve` | Serve workspace → `/api/projects` returns both |
| `test_paf_export` | W3C JSONL → PAF export → fields preserved |

### 11.3 End-to-End Tests (Playwright, weekly)

| Test | Steps |
|---|---|
| `test_ingest_to_browser` | CLI ingest → serve → text visible → entities highlighted |
| `test_track_toggle` | Toggle tracks → rendering updates |
| `test_dotplot_interaction` | Click cell → text scrolls |
| `test_cross_text` | Two texts → cross-text dotplot renders |
| `test_text_search` | Ctrl+F → matches highlighted → navigate |
| `test_keyboard_nav` | j/k, 1-9, Escape, d |
| `test_loading_overlay` | Large project → track-by-track progress |
| `test_detail_panel` | Click annotation → body type, evidence, confidence shown |

### 11.4 Regression Tests

- JSONL output for P&P Chapter 1 snapshotted per milestone
- Comparison: parse JSON, compare annotation bodies (ignoring `id` UUIDs and `timestamp` fields)
- Signal binaries compared byte-identical

### 11.5 Benchmarks

| Benchmark | Target | Measured |
|---|---|---|
| Ingest P&P Chapter 1 (TXT) | <2 seconds | Wall clock |
| Ingest P&P Chapter 1 (PDF) | <5 seconds | Wall clock |
| Analyze P&P Chapter 1 (5 tracks) | <5 seconds | Wall clock |
| Analyze full P&P (10 tracks, no BookNLP) | <30 seconds | Wall clock |
| Browser initial load (P&P Chapter 1) | <1 second | Lighthouse |
| Dotplot render (200×200) | <500ms | Canvas draw |
| Dotplot render (1000×1000) | <2 seconds | Canvas draw |
| Scroll performance (full P&P, 5 tracks) | 60fps | DevTools |

---

## 12. Dependencies and Prerequisites

### 12.1 Python Dependencies

```toml
[project]
requires-python = ">=3.12"
dependencies = [
    "click>=8.0",
    "fastapi>=0.100",
    "uvicorn>=0.20",
    "spacy>=3.7",
    "vaderSentiment>=3.3",
    "scikit-learn>=1.3",
    "numpy>=1.26",
    "scipy>=1.12",
    "pymupdf>=1.23",
    "ebooklib>=0.18",
    "beautifulsoup4>=4.12",
    "sqlite-vec>=0.1",
    "httpx>=0.25",
    "rich>=13.0",
]

[project.optional-dependencies]
booknlp = ["booknlp>=2.0"]
dev = [
    "pytest>=8.0",
    "pytest-cov",
    "ruff>=0.4",
    "mypy>=1.10",
    "pre-commit>=3.7",
]
```

### 12.2 Node Dependencies

```json
{
  "dependencies": {
    "react": "^18",
    "react-dom": "^18",
    "zustand": "^4",
    "d3": "^7"
  },
  "devDependencies": {
    "typescript": "^5",
    "vite": "^5",
    "@vitejs/plugin-react": "^4",
    "vitest": "^1",
    "@playwright/test": "^1",
    "eslint": "^9",
    "@typescript-eslint/eslint-plugin": "^7",
    "prettier": "^3"
  }
}
```

**Zustand** over MobX-state-tree: MST's snapshot/undo capabilities are Phase 2 (annotation UI undo/redo). Zustand is simpler and adequate for Phase 1's read-only browser. Evaluate MST at Phase 2 start — noting that JBrowse 2 itself uses MST, which may make it the right choice when the browser architecture matures.

### 12.3 External Prerequisites

| Prerequisite | Required? | Install |
|---|---|---|
| Python 3.12+ | Yes | System-dependent |
| Node.js 20+ | Yes | `brew install node` or nvm |
| spaCy `en_core_web_lg` | Yes | `python -m spacy download en_core_web_lg` (560MB) |
| Ollama | Optional | `brew install ollama` |
| Ollama embedding model | Optional | `ollama pull qwen3-embedding` |
| Ollama LLM model | Optional | `ollama pull qwen3:8b` |
| Java 11+ | Optional (BookNLP) | `brew install openjdk@11` |

---

## 13. Definition of Done (Phase 1)

### Core Pipeline
- [ ] `palimpsest ingest` produces valid project directory with `metadata.json` and `pipeline_run.json`
- [ ] `palimpsest analyze` computes 10 tracks/signals in <30 seconds for P&P
- [ ] All annotation tracks produce W3C Web Annotation JSONL (not PAF)
- [ ] All annotations carry Palimpsest body types and evidence levels (E1-E5)
- [ ] All tracks register via `TrackRegistry` — no hardcoded lists
- [ ] Stochastic algorithms deterministic with fixed seeds
- [ ] Signal data as raw Float32 binary, loadable in Python and browser
- [ ] `VectorStore` protocol abstracts sqlite-vec

### Browser
- [ ] Layout matches §7.1; keyboard navigation per §7.2
- [ ] TrackPanel driven by rendering manifests (JBrowse 2 pattern)
- [ ] DetailPanel shows W3C body type, evidence level, confidence for selected annotations
- [ ] OverviewBar with density barcodes and search ticks
- [ ] DotplotView + cross-text dotplot with project selector
- [ ] Text search (Ctrl+F) with type-ahead
- [ ] LLM summarizer with graceful degradation
- [ ] Linked views; semantic zoom; virtualized scrolling
- [ ] Loading overlay with track-by-track progress

### Export
- [ ] W3C AnnotationCollection JSON-LD (standards-compliant)
- [ ] PAF GFF3-analogue TSV (computational export)
- [ ] CSV (flat tabular)

### Quality
- [ ] All unit tests pass (>80% coverage on core/)
- [ ] All integration tests pass (including determinism and W3C validation)
- [ ] All benchmarks meet targets
- [ ] Test fixtures are public domain only (P&P, Moby-Dick)
- [ ] Code quality enforced via pre-commit (ruff + mypy + eslint + prettier)
- [ ] Git: conventional commits, milestone tags

### Documentation
- [ ] `specs/annotation-model.md`: W3C body types + evidence hierarchy
- [ ] `specs/LFO.md` with ~60 terms
- [ ] `specs/signals.md`: binary format
- [ ] `specs/PAF-export.md`: export format
- [ ] README.md with keyboard shortcuts
- [ ] ADRs for key decisions

### User Validation
- [ ] A literary scholar produces a structural analysis in <30 minutes

---

## 14. Traceability

### v2.0 Findings (doc 13a) → Resolution

| # | Finding | Resolution | Section |
|---|---|---|---|
| 1 | No TrackRegistry | `TrackExtractor` protocol + `TrackRegistry` (JBrowse 2 pattern) | §3 |
| 2 | npz browser loading | Raw Float32 binary + JSON manifest | §2.5 |
| 3 | No PAF Relation/Target | Reserved attributes in PAF export spec | §2.9 |
| 4 | No pipeline_run.json | Written on every `analyze` | §2.8 |
| 5 | No metadata.json schema | 15-field schema | §2.7 |
| 6 | IJ copyright risk | P&P + Moby-Dick (public domain) | All milestones |
| 7 | LDA non-determinism | `random_state=42` everywhere | §5.4 |
| 8 | No layout wireframe | Layout with dimensions | §7.1 |
| 9 | No text search | Ctrl+F with type-ahead | §7.3 |
| 10 | No progress indicators | `rich` CLI + browser overlay | §9 |
| 11 | sqlite-vec abstraction | `VectorStore` protocol | §6 |
| 12 | MST learning curve | Zustand for Phase 1 | §12.2 |
| 13 | No linting/formatting | ruff + mypy + eslint + prettier Day 1 | §0.7 |
| 14 | Wrong spaCy model | `en_core_web_lg` | §12.3 |
| 15 | No git workflow | Trunk-based, conventional commits | §0.6 |
| 16 | Scheduling fragile | Policy documented | §0.5 |
| 17 | W3C export under-specified | Full body type mapping | §2.3 |
| 18 | No keyboard navigation | 10+ shortcuts | §7.2 |
| 19 | No multi-project serving | Workspace serving + /api/projects | §8 |
| 20 | No track rendering manifest | TrackManifest + registry | §3.3 |

### v3.0 Corrections (research alignment)

| # | Issue | Source | Resolution | Section |
|---|---|---|---|---|
| 21 | Format hierarchy inverted (PAF primary, W3C export) | Docs 07 §6.2, 08 §Rec, 11 §5.2 | W3C JSONL primary; PAF is export | §2.1, §2.9 |
| 22 | No JBrowse 2 architectural reference | Docs 09 §4.3, 10, 11 §7 | Adapter/track/display/renderer pattern adopted | §3.1 |
| 23 | No evidence hierarchy | Doc 07 §4.1 | E1-E5 on every annotation | §2.4 |
| 24 | No custom W3C body types | Doc 07 §7.1 | 6 body types defined | §2.3 |
| 25 | ModeHMM not mentioned | Doc 11 | Alphabet as Phase 1 placeholder, explicit | §5.2 note |

---

*This plan supersedes documents 13 and 14 v2.0. It aligns Phase 1 implementation with the full research corpus (documents 00-11) while incorporating all 20 findings from the critical review (document 13a) and 5 additional research-alignment corrections.*

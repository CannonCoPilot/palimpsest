# Phase 1 Cross-Cutting Conventions

These conventions apply to ALL task documents and resolve systemic inconsistencies found during the task review.

---

## 1. Canonical Names

### 1.1 TrackExtractor `.name` Values

Every `TrackExtractor` subclass must use exactly these `.name` values. Dependency references in `depends_on` lists must match exactly.

| Track | `.name` value | `output_type` | Evidence |
|---|---|---|---|
| Entity | `"entities"` | `"annotation"` | E4 |
| Sentiment | `"sentiment"` | `"annotation"` | E5 |
| Lexical | `"lexical"` | `"annotation"` | E5 |
| Dialogue | `"dialogue"` | `"annotation"` | E5 (E4 after BookNLP) |
| Topics | `"topics"` | `"annotation"` | E4 |
| Coreference | `"coreference"` | `"annotation"` | E4 |
| Self-Similarity | `"self_similarity"` | `"signal"` | — |
| Narrative Arc | `"narrative_arc"` | `"signal"` | — |
| RQA | `"rqa"` | `"signal"` | — |
| Alphabet | `"alphabet"` | `"signal"` | — |

### 1.2 Virtual Dependencies

Some dependencies are infrastructure steps, not registered tracks. These are handled specially by `TrackRegistry.dependency_order()`:

| Virtual name | Meaning | Satisfied by |
|---|---|---|
| `"_spacy_parse"` | spaCy parse cached in `cache/spacy_docs.pkl` | First track that calls `project.load_spacy_docs()` |
| `"_embeddings"` | Paragraph embeddings stored in `cache/embeddings.db` | `embed_paragraphs()` in `services/embedding.py` |
| `"_tokenization"` | Basic tokenization available | Project creation (always satisfied) |

**Convention**: Virtual dependencies use a leading underscore (`_`) prefix. The registry treats any dependency starting with `_` as pre-satisfied (not in topological sort). Tracks that need these infrastructure steps should document the real dependency in a code comment.

### 1.3 Browser Adapter Functions

Use these exact function names across all browser code:

| Function | Module | Signature |
|---|---|---|
| `loadTrack` | `AnnotationAdapter.ts` | `(url: string) => Promise<W3CAnnotation[]>` |
| `loadSignal` | `SignalAdapter.ts` | `(manifestUrl: string) => Promise<{manifest: SignalManifest, data: Float32Array}>` |
| `loadTrackManifest` | `TrackManifest.ts` | `(url: string) => Promise<TrackManifest>` |

### 1.4 TypeScript Type Names

| Type | Correct | WRONG |
|---|---|---|
| W3C Annotation | `W3CAnnotation` | ~~`WC3Annotation`~~ |
| Zustand store action | `viewStore.requestScrollToParagraph(index)` | ~~`viewStore.scrollToParagraph(n)`~~ |

### 1.5 Zustand Store Actions

Canonical action names across all stores:

| Store | Action | Signature |
|---|---|---|
| `viewStore` | `setSelectedParagraphIndex` | `(index: number \| null) => void` |
| `viewStore` | `requestScrollToParagraph` | `(index: number) => void` |
| `viewStore` | `clearScrollRequest` | `() => void` |
| `trackStore` | `toggleTrack` | `(name: string) => void` |
| `trackStore` | `toggleTrackByIndex` | `(index: number) => void` (1-based, toggles) |
| `searchStore` | `setQuery` | `(query: string) => void` |
| `searchStore` | `nextMatch` / `prevMatch` | `() => void` |

---

## 2. Dependency References

### 2.1 Cross-Task References

When referencing another task, always use the format `T{NN} ({short title})`. Do NOT reference plan section numbers for tasks that have their own document.

### 2.2 When Earlier Tasks Are From a Different Series

Some task documents reference earlier tasks by wrong numbers because they were written independently. The canonical task numbers are in `00-INDEX.md`. When in doubt, reference the plan section (e.g., "per plan §8.1") rather than a task number.

---

## 3. Format Rules

### 3.1 Annotation Files

- **Primary format**: W3C Web Annotation JSON-LD, stored as JSONL (one annotation per line)
- **File extension**: `.jsonl`
- **Evidence level**: Every annotation carries `palimpsest:evidenceLevel` at the **annotation root** (NOT inside the body)
- **Confidence**: `palimpsest:confidence` at the **annotation root**
- **LFO type**: `palimpsest:lfoType` inside the **body** object
- **ID format**: `urn:palimpsest:{project-id}:{track-name}:{unique-suffix}`

### 3.2 Signal Files

- **Format**: raw little-endian Float32 binary + JSON manifest
- **File extension**: `.bin` (data) + `.json` (manifest)
- **NO `.npz` files** — browsers cannot parse them
- **Narrative arc shape**: `[5, 3]` (5 segments × 3 Boyd dimensions), NOT `[5, 15]`

### 3.3 PAF

- PAF is an **export format only** (not primary storage)
- Produced by `annotation/paf_export.py`
- Converts W3C annotations to GFF3-analogue TSV

### 3.4 JSON Field Naming

- Python dataclasses use `snake_case`
- JSON-LD output uses `camelCase` for Palimpsest-namespaced fields
- Serializer (`annotation/serializer.py`) handles the conversion
- Example: Python `vocabulary_richness` → JSON `palimpsest:vocabularyRichness`

---

## 4. Testing Rules

### 4.1 Fixture Texts

- **P&P Chapter 1**: `fixtures/pride-prejudice-ch1.txt` (public domain, primary test text)
- **P&P Full**: `fixtures/pride-prejudice-full.txt` (benchmark text, NOT in `core/tests/fixtures/`)
- **Moby-Dick Chapter 1**: `fixtures/moby-dick-ch1.txt` (secondary test text)
- **IJ / copyrighted texts**: `fixtures/ij/` (gitignored, local-only, NEVER in CI)

### 4.2 PDF/TXT Extraction Identity

**KNOWN ISSUE**: PDF text extraction via pymupdf does not produce byte-identical output to the original TXT after normalization. Do NOT assert SHA-256 identity between TXT and PDF extractions. Instead, assert:
- Both produce non-empty normalized text
- Key substrings are present in both (e.g., "Mr. Bennet", "Hertfordshire")
- Both segment into the same number of paragraphs (±1)

### 4.3 Determinism

- All stochastic algorithms: `random_state=42`
- Regression tests compare JSONL content (ignoring `id` UUIDs and timestamps)
- Signal binaries compared byte-identical

### 4.4 Filesystem Policy

- **NEVER write to `/tmp`** — use project-local `.scratch/` directory or `tmp_path` pytest fixture
- Smoke test scripts: use `${WORKSPACE:-$(pwd)/.scratch/smoke-test}` not `/tmp`

---

## 5. Bash Script Rules

- **NEVER `set -euo pipefail`** — grep exit 1 kills the script (macOS Bash 3.2)
- Use explicit error checking: `command || { echo "FAIL: ..."; exit 1; }`
- No associative arrays, no `readarray`, no `;&` in case (Bash 3.2 macOS)

---

## 6. Project Interface (`project.py`)

The `Project` class exposes these methods. All tasks should reference this canonical interface:

```python
class Project:
    path: Path                    # Project directory root
    metadata: ProjectMetadata     # Loaded from metadata.json

    @classmethod
    def load(cls, path: Path) -> "Project": ...

    def paragraphs(self) -> list[tuple[int, int, str]]:
        """Returns (start_offset, end_offset, text) for each paragraph."""
        ...

    def sections(self) -> list[tuple[int, int, str]]:
        """Returns (start_offset, end_offset, heading_text) for each section."""
        ...

    def load_spacy_docs(self) -> "spacy.tokens.Doc":
        """Load or compute the spaCy parse, caching to cache/spacy_docs.pkl."""
        ...

    def reference_text(self) -> str:
        """Read and return reference.txt contents."""
        ...
```

---

## 7. TrackExtractor Parameters

Each `TrackExtractor` that has configurable parameters should expose them via a `parameters()` method:

```python
def parameters(self) -> dict[str, Any]:
    """Return parameter dict for pipeline_run.json provenance."""
    return {"topics.n_topics": self.N_TOPICS, "topics.random_state": self.RANDOM_STATE}
```

The pipeline orchestrator (T15) aggregates these into `pipeline_run.json`. Do NOT hardcode parameter collection in the CLI — each extractor owns its own parameters.

---

## 8. Body Type Registry

All 7 Palimpsest body types (6 analytical + 1 structural):

| Body Type | Track | JSON `type` value |
|---|---|---|
| `SegmentAnnotation` | segments.jsonl | `palimpsest:SegmentAnnotation` |
| `EntityAnnotation` | entities.jsonl | `palimpsest:EntityAnnotation` |
| `SentimentAnnotation` | sentiment.jsonl | `palimpsest:SentimentAnnotation` |
| `LexicalAnnotation` | lexical.jsonl | `palimpsest:LexicalAnnotation` |
| `DialogueAnnotation` | dialogue.jsonl | `palimpsest:DialogueAnnotation` |
| `TopicAnnotation` | topics.jsonl | `palimpsest:TopicAnnotation` |
| `CoreferenceAnnotation` | coreference.jsonl | `palimpsest:CoreferenceAnnotation` |

Note: `SegmentAnnotation` is not in the plan's §2.3 table (which covers only the 6 analytical types) but IS used by `segmenter.py` (T05) for structural annotations. It should be added to `annotation/bodies.py` with fields: `segmentType` (sentence/paragraph/section), `segmentIndex`.

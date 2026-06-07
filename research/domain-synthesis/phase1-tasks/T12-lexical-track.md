# T12: Lexical Track

**Milestone**: 1.2 — Five Tracks + AI Summary + Search
**Estimated effort**: 3 hours
**Dependencies**: T04 (spaCy parse cache established), T02 (W3C annotation model + serializer)
**Outputs**: `core/palimpsest/tracks/lexical.py` (created); `core/tests/test_tracks.py` (modified, lexical section added)

---

## v4.0 Critical Review

**Verdict: Extractor logic is correct. Output contract is completely wrong. The `extract()` API must be abolished.**

### What is broken

**1. `project.paragraphs()` is a Python method call — it cannot work when the extractor is a subprocess.**
The original design relies on `project.paragraphs() -> list[tuple[int, int, str]]`, which reads the reference text from disk and parses paragraph boundaries inside Python. In the v4.0 architecture, the extractor is spawned as a subprocess by Rust's `PipelineManager`. It has no `Project` object. It has no Python runtime shared with the orchestrator. The extractor must receive paragraph boundaries as input — either via stdin as a JSONL stream from Rust, or by reading the reference text file itself given a path argument. The latter is simpler and requires no protocol change: pass `--reference <path>` and `--spacy-cache <path>`.

**2. `numpy` is imported but only used for Yule's K numerics — this is a 60MB import for pure Python arithmetic.**
`_yule_k()` and `_compute()` use only Python's `Counter` and basic arithmetic. The `numpy>=1.26` prerequisite exists solely because the original task assumed numpy would be imported. It should not be imported in this extractor. Remove the prerequisite. The Rust side does not care what Python libraries are loaded, but startup time per subprocess scales with import cost. VADER already loads a 4MB lexicon; adding numpy adds 60ms of import time per subprocess invocation for zero benefit.

**3. Building a list of annotation objects and then serializing it is O(2n) memory.**
Same problem as T11: the `annotations: list[Annotation] = []` accumulator holds ~500-2,000 `LexicalAnnotation` Python objects before writing. In the subprocess model the correct pattern is emit-as-you-go: one JSONL line per paragraph, flushed immediately. For lexical (paragraph-level granularity, ~50-2,500 annotations per novel), this is not a catastrophic allocation, but the pattern must be consistent across all extractors for Rust's streaming ingestion to work.

**4. `confidence=0.99` is hardcoded and not `u16`-compatible as written.**
`0.99 * 10000 = 9900` — this is fine as a `u16`. However, the original code does `confidence=0.99` without the `confidence_fixed_point()` rounding wrapper. Any extractor that produces a float like `0.9900000000000001` (IEEE 754 representation of 0.99) will fail the strict round-trip test in T20. All confidence values must be passed through the fixed-point normalizer before serialization.

**5. The `seen` set and overlap detection logic in the original task are mentioned for T13 but the no-overlap acceptance criterion here relies on the original `Project.paragraphs()` guaranteeing non-overlapping ranges.**
In the new architecture, paragraph boundary detection must be explicit and testable. The paragraph splitter must be a standalone pure function tested independently, not a `Project` method called implicitly.

**6. `margin-marker` rendering referenced in `manifest()` implies DOM-rendered gutter elements.**
`"textViewRendering": "margin-marker"` — in the v4.0 Canvas overlay architecture, margin markers are painted on the canvas layer as colored rectangles in the left gutter, not as DOM `<div>` or `<span>` elements. The manifest value must signal this to the frontend.

---

## v4.0 Rewrite

### Architecture

```
Rust PipelineManager (tokio)
  ├── spawns: python -m palimpsest.tracks.lexical
  │           --project <id> --reference <path> --spacy-cache <path>
  └── stdout: JSONL stream, one annotation per paragraph
```

**Performance requirement**: Rust must ingest at **100K annotations/sec** (matches T11 standard). Lexical produces fewer annotations than sentiment (~50-2500 vs ~18K), so ingestion is not the bottleneck — the bottleneck is Python Yule's K computation on long novels. Target: full P&P (~2500 paragraphs) in **<3 seconds** of Python CPU time.

### Language and technology

- **Python** (stays): pure Python `Counter` + regex tokenization. No numpy. No spaCy needed (operates on raw text, not parsed docs).
- **Output**: streaming JSONL to stdout
- **Invocation**: `python -m palimpsest.tracks.lexical --project <id> --reference <path>`

### Data structures

**Rust `PackedAnnotation`** for lexical:
```rust
PackedAnnotation {
    start: u32,         // paragraph start char
    end: u32,           // paragraph end char
    confidence: 9900,   // u16 — 0.99 * 10000
    track_id: 2,        // u8 — lexical track = 2
    evidence_level: 5,  // u8 — E5
    body_offset: u32,   // offset into body arena for LexicalAnnotation fields
}
```

The `body_offset` points into the body arena where Rust stores the variable-length lexical data (ttr, hapax_count, mean_word_length, vocabulary_richness) as a compact struct — not as a JSON string. The Rust body arena struct:

```rust
#[repr(C)]
struct LexicalBody {
    ttr: f32,                  // type-token ratio
    hapax_count: u32,          // raw count
    mean_word_length: f32,     // characters
    vocabulary_richness: f32,  // Yule's K
}
```

This is **16 bytes per annotation** in the body arena vs. 200+ bytes as a JSON string.

### Implementation

**`core/palimpsest/tracks/lexical.py`** — streaming CLI, no numpy:

```python
#!/usr/bin/env python3
"""Lexical track extractor — streaming JSONL to stdout for Rust ingestion.

Invocation (by Rust PipelineManager):
    python -m palimpsest.tracks.lexical \
        --project <project_id> \
        --reference <path/to/reference.txt>

Output: one W3C annotation JSON object per stdout line (JSONL).
No numpy required. Pure Python arithmetic only.
"""
import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path


_TOKEN_RE = re.compile(r"[A-Za-z']+")
_PARA_RE = re.compile(r"\n{2,}")
MIN_TOKENS = 5


def deterministic_id(project_id: str, start: int, end: int) -> str:
    key = f"{project_id}:lexical:{start}:{end}"
    return hashlib.sha256(key.encode()).hexdigest()[:8]


def confidence_fixed_point(value: float) -> float:
    return round(round(value * 10000) / 10000, 4)


def split_paragraphs(text: str) -> list[tuple[int, int, str]]:
    """Split text into (start, end, content) tuples on blank lines.

    Returns non-overlapping, non-empty paragraph spans covering the full text.
    Empty paragraphs (whitespace only) are excluded.
    """
    paragraphs = []
    pos = 0
    for segment in _PARA_RE.split(text):
        content = segment.strip()
        start = text.find(segment, pos)
        if start == -1:
            start = pos
        end = start + len(segment)
        if content:
            paragraphs.append((start, end, content))
        pos = end
    return paragraphs


def yule_k(tokens: list[str], counts: Counter) -> float:
    """Yule's K: length-independent vocabulary richness measure."""
    n = len(tokens)
    if n == 0:
        return 0.0
    freq_of_freq = Counter(counts.values())
    numerator = sum(freq * (m ** 2) for m, freq in freq_of_freq.items()) - n
    return (10_000 * numerator) / (n ** 2)


def compute_lexical(text: str) -> dict | None:
    tokens = [w.lower() for w in _TOKEN_RE.findall(text)]
    if len(tokens) < MIN_TOKENS:
        return None
    counts = Counter(tokens)
    n_tokens = len(tokens)
    n_types = len(counts)
    hapax = sum(1 for v in counts.values() if v == 1)
    mean_len = sum(len(w) for w in tokens) / n_tokens
    yk = yule_k(tokens, counts)
    return {
        "ttr": round(n_types / n_tokens, 4),
        "hapax_count": hapax,
        "mean_word_length": round(mean_len, 4),
        "vocabulary_richness": round(yk, 4),
    }


def emit(annotation: dict) -> None:
    sys.stdout.write(json.dumps(annotation, separators=(",", ":")) + "\n")
    sys.stdout.flush()


def extract(project_id: str, reference_path: Path) -> None:
    text = reference_path.read_text(encoding="utf-8")
    source_urn = f"urn:palimpsest:{project_id}"
    confidence = confidence_fixed_point(0.99)

    for start, end, content in split_paragraphs(text):
        stats = compute_lexical(content)
        if stats is None:
            continue

        ann = {
            "type": "Annotation",
            "@context": [
                "http://www.w3.org/ns/anno.jsonld",
                "https://palimpsest.io/context.jsonld",
            ],
            "id": (
                f"urn:palimpsest:{project_id}:lexical:"
                + deterministic_id(project_id, start, end)
            ),
            "body": {
                "type": "palimpsest:LexicalAnnotation",
                "palimpsest:ttr": stats["ttr"],
                "palimpsest:hapaxCount": stats["hapax_count"],
                "palimpsest:meanWordLength": stats["mean_word_length"],
                "palimpsest:vocabularyRichness": stats["vocabulary_richness"],
                "palimpsest:lfoType": "signal.lexical",
            },
            "target": {
                "source": source_urn,
                "selector": {
                    "type": "TextPositionSelector",
                    "start": start,
                    "end": end,
                },
            },
            "palimpsest:confidence": confidence,
            "palimpsest:evidenceLevel": "E5",
            "creator": {"type": "Software", "name": "palimpsest-lexical/0.1"},
        }
        emit(ann)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True)
    parser.add_argument("--reference", required=True, type=Path)
    args = parser.parse_args()
    extract(args.project, args.reference)


if __name__ == "__main__":
    main()
```

### Paragraph splitter: standalone and testable

`split_paragraphs()` is a module-level pure function, not a `Project` method. It must be tested independently:

```python
def test_split_paragraphs_non_overlapping():
    text = "First paragraph.\n\nSecond paragraph.\n\nThird."
    paras = split_paragraphs(text)
    assert len(paras) == 3
    # Verify non-overlapping
    for i in range(len(paras) - 1):
        assert paras[i][1] <= paras[i+1][0]

def test_split_paragraphs_covers_full_text():
    text = "Para one.\n\nPara two.\n\nPara three."
    paras = split_paragraphs(text)
    covered = sum(end - start for start, end, _ in paras)
    # Should cover most of the text (some separator chars may be excluded)
    assert covered >= len(text) * 0.85
```

### Rust ingestion interface

```rust
pub async fn run_lexical(
    store: &mut AnnotationStore,
    project_id: &str,
    reference_path: &Path,
    python_bin: &Path,
) -> Result<usize, PipelineError> {
    let mut child = Command::new(python_bin)
        .args([
            "-m", "palimpsest.tracks.lexical",
            "--project", project_id,
            "--reference", reference_path.to_str().unwrap(),
        ])
        .stdout(std::process::Stdio::piped())
        .spawn()?;

    let stdout = child.stdout.take().unwrap();
    let mut lines = BufReader::new(stdout).lines();
    let mut count = 0usize;

    while let Some(line) = lines.next_line().await? {
        store.ingest_jsonl_line(&line, TrackId::Lexical)?;
        count += 1;
    }
    let status = child.wait().await?;
    if !status.success() {
        return Err(PipelineError::ExtractorFailed("lexical", status));
    }
    Ok(count)
}
```

### Test strategy

**Unit tests** (`core/tests/test_tracks.py`):

```python
def test_lexical_stdout_is_valid_jsonl(pp_ch1_reference_path, tmp_path):
    """Extractor writes valid JSONL to stdout; every line is a valid W3C annotation."""
    result = subprocess.run(
        [sys.executable, "-m", "palimpsest.tracks.lexical",
         "--project", "pp-ch1",
         "--reference", str(pp_ch1_reference_path)],
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stderr
    lines = [l for l in result.stdout.splitlines() if l.strip()]
    assert len(lines) > 0
    for line in lines:
        ann = json.loads(line)
        assert ann["type"] == "Annotation"
        assert ann["palimpsest:evidenceLevel"] == "E5"
        body = ann["body"]
        assert body["type"] == "palimpsest:LexicalAnnotation"
        assert 0.0 < body["palimpsest:ttr"] <= 1.0
        assert body["palimpsest:hapaxCount"] >= 0
        assert body["palimpsest:meanWordLength"] > 0.0
        assert body["palimpsest:vocabularyRichness"] >= 0.0

def test_lexical_no_overlapping_spans(pp_ch1_reference_path):
    """Paragraph spans are non-overlapping."""
    result = subprocess.run(
        [sys.executable, "-m", "palimpsest.tracks.lexical",
         "--project", "pp-ch1", "--reference", str(pp_ch1_reference_path)],
        capture_output=True, text=True,
    )
    anns = [json.loads(l) for l in result.stdout.splitlines() if l.strip()]
    spans = sorted(
        [(a["target"]["selector"]["start"], a["target"]["selector"]["end"]) for a in anns]
    )
    for i in range(len(spans) - 1):
        assert spans[i][1] <= spans[i+1][0], f"Overlapping spans at index {i}"

def test_lexical_ids_deterministic(pp_ch1_reference_path):
    """Annotation IDs are identical across two runs."""
    def run():
        r = subprocess.run(
            [sys.executable, "-m", "palimpsest.tracks.lexical",
             "--project", "pp-ch1", "--reference", str(pp_ch1_reference_path)],
            capture_output=True, text=True,
        )
        return [json.loads(l)["id"] for l in r.stdout.splitlines() if l.strip()]
    assert run() == run()

def test_lexical_no_numpy_import(pp_ch1_reference_path):
    """Extractor does not import numpy (startup cost regression test)."""
    result = subprocess.run(
        [sys.executable, "-c",
         "import sys; import palimpsest.tracks.lexical; print('numpy' in sys.modules)"],
        capture_output=True, text=True,
    )
    assert result.stdout.strip() == "False"
```

**Performance benchmarks** (`palimpsest-core/benches/ingest_lexical.rs`):

```rust
fn bench_lexical_ingest(c: &mut Criterion) {
    // ~2,500 lexical JSONL lines for full P&P
    let lines = include_str!("fixtures/pp-full-lexical.jsonl");
    let line_vec: Vec<&str> = lines.lines().collect();

    c.bench_function("lexical_ingest_full_pp", |b| {
        b.iter(|| {
            let mut store = AnnotationStore::new();
            for line in &line_vec {
                store.ingest_jsonl_line(line, TrackId::Lexical).unwrap();
            }
        })
    });
}
```

**Performance targets**:
| Operation | Target | Notes |
|-----------|--------|-------|
| Full P&P lexical extraction (Python) | <3s | Yule's K is O(V log V) per paragraph |
| Rust ingest of 2,500 lines | <0.03s | Easily within 100K ann/sec target |
| Python startup (no numpy) | <1s | Measured via `time python -m palimpsest.tracks.lexical --help` |

### Manifest (updated for v4.0)

```python
def manifest() -> dict:
    return {
        "trackName": "lexical",
        "trackId": 2,
        "bodyType": "palimpsest:LexicalAnnotation",
        "evidenceLevel": "E5",
        "colorScheme": {"primary": "#9b59b6", "secondary": "#d5b8e8"},
        "textViewRendering": "canvas-margin-marker",   # Canvas gutter rectangle
        "overviewBarRendering": {
            "type": "webgpu-density",                  # GPU compute shader
            "color": "#9b59b6",
        },
    }
```

---

## Original Content (preserved for reference)

### Context

The lexical track computes per-paragraph vocabulary statistics — type-token ratio (TTR), hapax count, mean word length, and vocabulary richness — and stores them as `LexicalAnnotation` W3C objects in `tracks/lexical.jsonl`. Lexical density is one of the earliest computational stylistics signals: it distinguishes ornate from plain prose, detects register shifts, and correlates with reading difficulty. It operates at paragraph granularity rather than sentence granularity because paragraph-level TTR is more stable than sentence-level TTR (sentences are often too short for meaningful type counts).

### Prerequisites

- `core/palimpsest/annotation/model.py` — `Annotation`, `Target`, `TextPositionSelector` dataclasses.
- `core/palimpsest/annotation/bodies.py` — `LexicalAnnotation` body type with fields `palimpsest:ttr`, `palimpsest:hapaxCount`, `palimpsest:meanWordLength`, `palimpsest:vocabularyRichness`, `palimpsest:lfoType`.
- `core/palimpsest/annotation/serializer.py` — `write_track`, `read_track`.
- `core/palimpsest/tracks/base.py` — `TrackExtractor` protocol, `EvidenceLevel`.
- `core/palimpsest/project.py` — `Project.load_spacy_docs()` and `Project.paragraphs() -> list[tuple[int, int, str]]` returning `(start_char, end_char, text)` tuples for each paragraph.
- `core/palimpsest/tracks/sentiment.py` already exists (T11), demonstrating the pattern to follow.
- `numpy>=1.26` is installed (needed for efficient token statistics, though pure Python is acceptable here).
- `fixtures/pride-prejudice-ch1.txt` and `fixtures/moby-dick-ch1.txt` exist.

### Deliverables

- `core/palimpsest/tracks/lexical.py` — `LexicalExtractor` class implementing `TrackExtractor`
- `core/tests/test_tracks.py` — lexical section with at least 4 test functions

### Implementation Steps

1. **Implement `LexicalExtractor`** in `core/palimpsest/tracks/lexical.py`:

   ```python
   from palimpsest.annotation.model import Annotation, Target, TextPositionSelector
   from palimpsest.annotation.bodies import LexicalAnnotation
   from palimpsest.tracks.base import TrackExtractor, EvidenceLevel
   from palimpsest.project import Project
   import uuid, re
   from collections import Counter

   class LexicalExtractor:
       name = "lexical"
       output_type = "annotation"
       depends_on = ["spacy_parse"]
       lfo_types = ["signal.lexical.ttr", "signal.lexical.hapax"]
       evidence_level = EvidenceLevel.E5

       def extract(self, project: Project) -> list[Annotation]:
           annotations: list[Annotation] = []
           for start, end, text in project.paragraphs():
               stats = self._compute(text)
               if stats is None:
                   continue
               ann = Annotation(
                   id=f"urn:palimpsest:{project.metadata['id']}:lexical:{uuid.uuid4().hex[:8]}",
                   body=LexicalAnnotation(
                       ttr=stats["ttr"],
                       hapax_count=stats["hapax_count"],
                       mean_word_length=stats["mean_word_length"],
                       vocabulary_richness=stats["vocabulary_richness"],
                       lfo_type="signal.lexical",
                   ),
                   target=Target(
                       source=f"urn:palimpsest:{project.metadata['id']}",
                       selector=TextPositionSelector(start=start, end=end),
                   ),
                   creator={"type": "Software", "name": "palimpsest-lexical/0.1"},
                   confidence=0.99,
                   evidence_level=EvidenceLevel.E5,
               )
               annotations.append(ann)
           return annotations
   ```

2. **Implement `_compute(text: str) -> dict | None`**:

   ```python
   def _compute(self, text: str) -> dict | None:
       # Tokenize: alphabetic lowercased tokens only (exclude punctuation, numbers)
       tokens = [w.lower() for w in re.findall(r"[A-Za-z']+", text)]
       if len(tokens) < 5:
           return None  # Skip very short paragraphs (headings, etc.)
       counts = Counter(tokens)
       n_tokens = len(tokens)
       n_types = len(counts)
       hapax = sum(1 for v in counts.values() if v == 1)
       mean_len = sum(len(w) for w in tokens) / n_tokens
       yule_k = self._yule_k(tokens, counts)
       return {
           "ttr": round(n_types / n_tokens, 4),
           "hapax_count": hapax,
           "mean_word_length": round(mean_len, 4),
           "vocabulary_richness": round(yule_k, 4),
       }

   def _yule_k(self, tokens: list[str], counts: Counter) -> float:
       n = len(tokens)
       if n == 0:
           return 0.0
       freq_of_freq: Counter = Counter(counts.values())
       numerator = sum(freq * (m ** 2) for m, freq in freq_of_freq.items()) - n
       return (10_000 * numerator) / (n ** 2) if n > 0 else 0.0
   ```

3. **Minimum token threshold**: paragraphs with fewer than 5 tokens (chapter headings, page numbers, isolated quotation marks) return `None` and are skipped.

4. **Write output**: call `write_track(project.path / "tracks" / "lexical.jsonl", annotations)` at the end of `extract()`.

5. **Write manifest**: call `project.write_manifest("lexical", self.manifest())`.

6. **Register**: auto-discovered by `TrackRegistry` via `__subclasses__()`. No explicit registration needed.

### Acceptance Criteria

- `palimpsest analyze <project-dir>` produces `tracks/lexical.jsonl`.
- Annotation count equals paragraph count (minus any skipped short paragraphs).
- Every annotation body has `"type": "palimpsest:LexicalAnnotation"`, `"palimpsest:evidenceLevel": "E5"`.
- `palimpsest:ttr` is in `(0.0, 1.0]` for every annotation.
- `palimpsest:hapaxCount` is a non-negative integer.
- `palimpsest:meanWordLength` is a positive float.
- `palimpsest:vocabularyRichness` (Yule's K) is non-negative.
- Target selectors cover non-overlapping character ranges.
- Running `palimpsest analyze` twice produces identical `lexical.jsonl`.
- `isinstance(LexicalExtractor(), TrackExtractor)` is `True`.

### Design Decisions

- **Paragraph granularity, not sentence**: Sentence-level TTR is noisy and strongly dependent on sentence length. Paragraph-level TTR is the standard unit in computational stylistics (Herdan 1960, Tweedie & Baayen 1998).
- **Yule's K as `vocabularyRichness`**: TTR is already stored separately. Yule's K (1944) is length-independent unlike TTR, making it suitable for comparing paragraphs of different lengths.
- **Alphabetic tokens only**: excluding punctuation and numbers from token counts matches the standard stylometric convention.
- **Confidence = 0.99**: lexical statistics are exact computations (no ML, no approximation).
- **`margin-marker` rendering**: paragraph-span highlights would obscure all text in each paragraph. Margin markers convey density without blocking readability.
- **Evidence level E5**: Yule's K and TTR are ab initio statistical computations with no trained model.

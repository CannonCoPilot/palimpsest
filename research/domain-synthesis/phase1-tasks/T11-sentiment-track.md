# T11: Sentiment Track

**Milestone**: 1.2 — Five Tracks + AI Summary + Search
**Estimated effort**: 4 hours
**Dependencies**: T04 (entity track, which establishes the spaCy parse cache), T02 (W3C annotation model + serializer)
**Outputs**: `core/palimpsest/tracks/sentiment.py` (created); `core/tests/test_tracks.py` (modified, sentiment section added)

---

## v4.0 Critical Review

**Verdict: The Python extractor logic is sound and stays. The output contract is fatally wrong for the new architecture.**

### What is broken

**1. `extract()` returns a list and writes a file — both are wrong.**
The method signature `extract(project: Project) -> list[Annotation]` builds an in-memory list of Python objects and calls `write_track()` inside the extractor. Under the v4.0 architecture, the Rust pipeline manager spawns this extractor as a subprocess and reads its stdout as a streaming JSONL pipe. There is no shared Python heap. The extractor must write JSONL lines to stdout as it produces them — not accumulate a list and bulk-write to a file. The `write_track()` side-effect is eliminated; the Rust `AnnotationStore` owns the file.

**2. A list of Python objects is 65MB of heap for a full novel.**
W3C annotation objects with full JSON-LD structure cost ~3,500 bytes each in Python's object model. A 122K-word novel produces ~18,000 annotations. Building this as a Python list before writing is a 65MB allocation that then gets serialized to disk and loaded again by Rust — three copies of the data in memory simultaneously during a pipeline run. The new architecture produces zero copies: extractor writes one JSONL line per sentence directly to stdout; Rust reads and packs to 16 bytes in the `AnnotationStore`.

**3. The `depends_on = ["spacy_parse"]` field implies orchestrator-level caching that no longer exists.**
The old CLI orchestrator satisfied `spacy_parse` by loading a pickled Doc from disk. In the new architecture, Rust spawns each Python subprocess independently. The spaCy pickle cache must be an explicit file path argument, not an orchestrator-managed virtual dependency. The dependency protocol must change.

**4. `manifest()` returns a dict that references SVG rendering concepts.**
`"overviewBarRendering": {"type": "density-barcode", "color": "#2ecc71"}` — the density barcode is now a WebGPU compute shader, not an SVG `<line>` element per annotation. The manifest field name and value must change to `"overviewBarRendering": {"type": "webgpu-density", "color": "#2ecc71"}` so the frontend's WebGPU pipeline knows to use the GPU path, not fall back to DOM elements.

**5. Confidence = `min(|valence| + 0.5, 1.0)` produces values that are not fixed-point `u16` compatible without rounding.**
`PackedAnnotation.confidence` is a `u16` storing values in `[0, 10000]` (divide by 10000 to get the float). The Python extractor must round confidence to 4 decimal places AND serialize it as a float that round-trips cleanly through `u16` fixed-point. The formula itself is fine; the serialization contract must be enforced.

**6. UUID in the annotation ID is non-deterministic.**
`uuid.uuid4().hex[:8]` generates a different ID on every run. This breaks Rust's deduplication logic in `AnnotationStore`, which uses the annotation `id` field as a key to detect duplicate ingestion from re-runs. IDs must be deterministic — derived from `(project_id, track_name, char_start, char_end)` hashed with SHA-256 truncated to 8 hex chars.

---

## v4.0 Rewrite

### Architecture

```
Rust PipelineManager (tokio)
  ├── spawns: python sentiment.py --project /path/to/project --spacy-cache /path/to/cache.pkl
  │   └── stdout: JSONL stream, one annotation per line, newline-delimited
  └── reads stdout line-by-line → AnnotationStore::ingest_jsonl_line()
        └── packs into PackedAnnotation (16 bytes) + body arena
```

**Performance requirement**: Rust must ingest extractor output at **100K annotations/sec**. For a full novel (~18K sentiment annotations), ingestion must complete in **<0.2 seconds** after the last Python line is written.

### Language and technology

- **Python** (stays): VADER is the NLP engine. No rewrite.
- **Output**: streaming JSONL to stdout (not file write, not list return)
- **Invocation**: CLI binary with explicit `--project` and `--spacy-cache` args, not a callable `extract()` method
- **Rust ingestion**: `tokio::process::Command` with `stdout: Stdio::piped()`, async line reader

### Data structures

**Python output format** (each line on stdout):
```json
{"type":"Annotation","@context":["http://www.w3.org/ns/anno.jsonld","https://palimpsest.io/context.jsonld"],"id":"urn:palimpsest:pp:sentiment:3a7f2c1b","body":{"type":"palimpsest:SentimentAnnotation","palimpsest:valence":-0.2732,"palimpsest:arousal":0.1841,"palimpsest:model":"vader","palimpsest:lfoType":"signal.sentiment"},"target":{"source":"urn:palimpsest:pp","selector":{"type":"TextPositionSelector","start":0,"end":243}},"palimpsest:confidence":0.6366,"palimpsest:evidenceLevel":"E5","creator":{"type":"Software","name":"vaderSentiment/3.3"}}
```

**Rust `PackedAnnotation`** (after ingestion):
```rust
PackedAnnotation {
    start: 0,           // u32 char offset
    end: 243,           // u32 char offset
    confidence: 6366,   // u16 fixed-point (0.6366 * 10000)
    track_id: 1,        // u8 — sentiment track = 1
    evidence_level: 5,  // u8 — E5
    body_offset: 0,     // u32 — offset into body arena for variable data
}
```

### Implementation

**`core/palimpsest/tracks/sentiment.py`** — rewrite as a streaming CLI:

```python
#!/usr/bin/env python3
"""Sentiment track extractor — streaming JSONL to stdout for Rust ingestion.

Invocation (by Rust PipelineManager):
    python -m palimpsest.tracks.sentiment \
        --project <project_id> \
        --spacy-cache <path/to/cache.pkl> \
        --reference <path/to/reference.txt>

Output: one W3C annotation JSON object per stdout line (JSONL).
Exit code 0 = success; non-zero = failure. Rust reads exit code.
"""
import argparse
import hashlib
import json
import pickle
import sys
from pathlib import Path


def deterministic_id(project_id: str, track: str, start: int, end: int) -> str:
    """Derive a stable annotation ID from content, not random UUID."""
    key = f"{project_id}:{track}:{start}:{end}"
    return hashlib.sha256(key.encode()).hexdigest()[:8]


def confidence_fixed_point(value: float) -> float:
    """Round to 4 decimal places so u16 fixed-point round-trips cleanly."""
    return round(round(value * 10000) / 10000, 4)


def emit(annotation: dict) -> None:
    """Write one annotation as a JSONL line to stdout. No buffering."""
    sys.stdout.write(json.dumps(annotation, separators=(",", ":")) + "\n")
    sys.stdout.flush()


def extract(project_id: str, spacy_cache_path: Path) -> None:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

    with open(spacy_cache_path, "rb") as f:
        docs = pickle.load(f)

    analyzer = SentimentIntensityAnalyzer()
    source_urn = f"urn:palimpsest:{project_id}"

    for doc in docs:
        for sent in doc.sents:
            scores = analyzer.polarity_scores(sent.text)
            valence = round(scores["compound"], 4)
            arousal = round((scores["pos"] + scores["neg"]) / 2.0, 4)
            confidence = confidence_fixed_point(min(abs(valence) + 0.5, 1.0))

            ann = {
                "type": "Annotation",
                "@context": [
                    "http://www.w3.org/ns/anno.jsonld",
                    "https://palimpsest.io/context.jsonld",
                ],
                "id": (
                    f"urn:palimpsest:{project_id}:sentiment:"
                    + deterministic_id(project_id, "sentiment", sent.start_char, sent.end_char)
                ),
                "body": {
                    "type": "palimpsest:SentimentAnnotation",
                    "palimpsest:valence": valence,
                    "palimpsest:arousal": arousal,
                    "palimpsest:model": "vader",
                    "palimpsest:lfoType": "signal.sentiment",
                },
                "target": {
                    "source": source_urn,
                    "selector": {
                        "type": "TextPositionSelector",
                        "start": sent.start_char,
                        "end": sent.end_char,
                    },
                },
                "palimpsest:confidence": confidence,
                "palimpsest:evidenceLevel": "E5",
                "creator": {"type": "Software", "name": "vaderSentiment/3.3"},
            }
            emit(ann)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True)
    parser.add_argument("--spacy-cache", required=True, type=Path)
    args = parser.parse_args()
    extract(args.project, args.spacy_cache)


if __name__ == "__main__":
    main()
```

### Rust ingestion interface

The `PipelineManager` in `src-tauri/src/pipeline.rs` spawns this extractor:

```rust
use tokio::process::Command;
use tokio::io::{AsyncBufReadExt, BufReader};

pub async fn run_sentiment(
    store: &mut AnnotationStore,
    project_id: &str,
    spacy_cache: &Path,
    python_bin: &Path,
) -> Result<usize, PipelineError> {
    let mut child = Command::new(python_bin)
        .args([
            "-m", "palimpsest.tracks.sentiment",
            "--project", project_id,
            "--spacy-cache", spacy_cache.to_str().unwrap(),
        ])
        .stdout(std::process::Stdio::piped())
        .spawn()?;

    let stdout = child.stdout.take().unwrap();
    let mut lines = BufReader::new(stdout).lines();
    let mut count = 0usize;

    while let Some(line) = lines.next_line().await? {
        store.ingest_jsonl_line(&line, TrackId::Sentiment)?;
        count += 1;
    }

    let status = child.wait().await?;
    if !status.success() {
        return Err(PipelineError::ExtractorFailed("sentiment", status));
    }
    Ok(count)
}
```

**Ingestion throughput requirement**: `AnnotationStore::ingest_jsonl_line` must parse the JSON, pack into `PackedAnnotation`, and append to the arena at **>=100K lines/sec**. On M4 Max this is achievable with `serde_json` + direct arena `push`. Benchmark this in `palimpsest-core/benches/ingest.rs`.

### Manifest (updated for v4.0)

```python
def manifest() -> dict:
    return {
        "trackName": "sentiment",
        "trackId": 1,          # u8 assigned at registration; Rust uses this as track_id
        "bodyType": "palimpsest:SentimentAnnotation",
        "evidenceLevel": "E5",
        "colorScheme": {
            "primary": "#2ecc71",
            "secondary": "#e74c3c",
            "scale": ["#e74c3c", "#95a5a6", "#2ecc71"],
        },
        "textViewRendering": "canvas-highlight",   # Canvas layer, not DOM spans
        "overviewBarRendering": {
            "type": "webgpu-density",              # GPU compute shader, not SVG lines
            "color": "#2ecc71",
        },
    }
```

### Test strategy

**Unit tests** (Python, `core/tests/test_tracks.py`):

```python
import subprocess
import json

def test_sentiment_stdout_is_valid_jsonl(pp_ch1_spacy_cache, tmp_path):
    """Extractor writes valid JSONL to stdout; every line parses as W3C annotation."""
    result = subprocess.run(
        [sys.executable, "-m", "palimpsest.tracks.sentiment",
         "--project", "pp-ch1",
         "--spacy-cache", str(pp_ch1_spacy_cache)],
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stderr
    lines = [l for l in result.stdout.splitlines() if l.strip()]
    assert len(lines) > 0
    for line in lines:
        ann = json.loads(line)  # must not raise
        assert ann["type"] == "Annotation"
        assert ann["palimpsest:evidenceLevel"] == "E5"
        assert ann["body"]["type"] == "palimpsest:SentimentAnnotation"
        assert -1.0 <= ann["body"]["palimpsest:valence"] <= 1.0
        assert 0.0 <= ann["body"]["palimpsest:arousal"] <= 1.0
        assert ann["target"]["selector"]["start"] < ann["target"]["selector"]["end"]

def test_sentiment_ids_are_deterministic(pp_ch1_spacy_cache):
    """Running twice produces identical annotation IDs (no random UUIDs)."""
    def run():
        r = subprocess.run(
            [sys.executable, "-m", "palimpsest.tracks.sentiment",
             "--project", "pp-ch1", "--spacy-cache", str(pp_ch1_spacy_cache)],
            capture_output=True, text=True,
        )
        return [json.loads(l)["id"] for l in r.stdout.splitlines() if l.strip()]
    ids1, ids2 = run(), run()
    assert ids1 == ids2

def test_sentiment_confidence_fixed_point_compatible(pp_ch1_spacy_cache):
    """All confidence values survive u16 fixed-point round-trip."""
    result = subprocess.run(
        [sys.executable, "-m", "palimpsest.tracks.sentiment",
         "--project", "pp-ch1", "--spacy-cache", str(pp_ch1_spacy_cache)],
        capture_output=True, text=True,
    )
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        conf = json.loads(line)["palimpsest:confidence"]
        u16_val = round(conf * 10000)
        assert 0 <= u16_val <= 10000
        recovered = u16_val / 10000
        assert abs(recovered - conf) < 0.0001
```

**Performance benchmark** (`palimpsest-core/benches/ingest_sentiment.rs`):

```rust
use criterion::{criterion_group, criterion_main, Criterion, Throughput};

fn bench_sentiment_ingest(c: &mut Criterion) {
    // 18,760 pre-generated sentiment JSONL lines (full P&P)
    let lines = include_str!("fixtures/pp-full-sentiment.jsonl");
    let line_vec: Vec<&str> = lines.lines().collect();
    let n = line_vec.len();

    let mut group = c.benchmark_group("sentiment-ingest");
    group.throughput(Throughput::Elements(n as u64));

    group.bench_function("ingest_jsonl_lines", |b| {
        b.iter(|| {
            let mut store = AnnotationStore::new();
            for line in &line_vec {
                store.ingest_jsonl_line(line, TrackId::Sentiment).unwrap();
            }
            store
        })
    });
    group.finish();
}

// REQUIRED: assert throughput >= 100K annotations/sec
// criterion will fail the benchmark if this target is not met
criterion_group!(benches, bench_sentiment_ingest);
criterion_main!(benches);
```

**Performance targets**:
| Operation | Target | Failure condition |
|-----------|--------|-------------------|
| Full P&P sentiment extraction (Python) | <5s | Test timeout at 10s |
| Rust ingest of 18,760 lines | <0.2s | Benchmark asserts >100K ann/sec |
| `u16` confidence round-trip error | <0.0001 | Test asserts exact equality |

---

## Original Content (preserved for reference)

### Context

The sentiment track runs VADER on every spaCy sentence in the reference text and emits one `SentimentAnnotation` W3C object per sentence into `tracks/sentiment.jsonl`. This is the second annotation track (after entities) and the first to exercise evidence level E5 (ab initio rule-based/statistical prediction). It reuses the spaCy parse already cached in `cache/spacy_docs.pkl` from the entity track run, so no additional parsing cost is incurred.

### Prerequisites

- `core/palimpsest/annotation/model.py` exists with `Annotation`, `Target`, `Selector`, and `Body` dataclasses.
- `core/palimpsest/annotation/bodies.py` defines `SentimentAnnotation` body type with fields `palimpsest:valence`, `palimpsest:arousal`, `palimpsest:model`, `palimpsest:lfoType`.
- `core/palimpsest/annotation/serializer.py` implements `write_track(path, annotations)` and `read_track(path)`.
- `core/palimpsest/tracks/base.py` defines the `TrackExtractor` protocol and `EvidenceLevel` constants.
- `core/palimpsest/tracks/registry.py` implements `TrackRegistry` with auto-discovery.
- `core/palimpsest/project.py` exposes `Project` with `.path`, `.metadata`, `.spacy_cache_path`, and helper `load_spacy_docs() -> list[spacy.tokens.Doc]`.
- `cache/spacy_docs.pkl` is populated by a prior `palimpsest analyze` run (entities track depends on spaCy parse).
- `vaderSentiment>=3.3` is installed in the project virtualenv.
- `fixtures/pride-prejudice-ch1.txt` and `fixtures/moby-dick-ch1.txt` exist in the repo root `fixtures/` directory.

### Deliverables

- `core/palimpsest/tracks/sentiment.py` — `SentimentExtractor` class implementing `TrackExtractor`
- `core/tests/test_tracks.py` — sentiment section with at least 4 test functions (see Tests to Write)

### Implementation Steps

1. **Install dependency**: ensure `vaderSentiment` is in `pyproject.toml` under `[project.dependencies]` and `pip install -e ".[dev]"` picks it up.

2. **Implement `SentimentExtractor`** in `core/palimpsest/tracks/sentiment.py`:

   ```python
   from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
   from palimpsest.annotation.model import Annotation, Body, Target, TextPositionSelector
   from palimpsest.annotation.bodies import SentimentAnnotation
   from palimpsest.tracks.base import TrackExtractor, EvidenceLevel
   from palimpsest.project import Project
   import uuid, datetime

   class SentimentExtractor:
       name = "sentiment"
       output_type = "annotation"
       depends_on = ["spacy_parse"]
       lfo_types = ["signal.sentiment"]
       evidence_level = EvidenceLevel.E5

       def extract(self, project: Project) -> list[Annotation]:
           analyzer = SentimentIntensityAnalyzer()
           docs = project.load_spacy_docs()
           annotations: list[Annotation] = []
           for doc in docs:
               for sent in doc.sents:
                   scores = analyzer.polarity_scores(sent.text)
                   valence = scores["compound"]          # -1.0 to 1.0
                   arousal = (scores["pos"] + scores["neg"]) / 2.0  # 0.0 to 1.0
                   ann = Annotation(
                       id=f"urn:palimpsest:{project.metadata['id']}:sentiment:{uuid.uuid4().hex[:8]}",
                       body=SentimentAnnotation(
                           valence=round(valence, 4),
                           arousal=round(arousal, 4),
                           model="vader",
                           lfo_type="signal.sentiment",
                       ),
                       target=Target(
                           source=f"urn:palimpsest:{project.metadata['id']}",
                           selector=TextPositionSelector(
                               start=sent.start_char,
                               end=sent.end_char,
                           ),
                       ),
                       creator={"type": "Software", "name": "vaderSentiment/3.3"},
                       confidence=round(min(abs(valence) + 0.5, 1.0), 4),
                       evidence_level=EvidenceLevel.E5,
                   )
                   annotations.append(ann)
           return annotations

       def manifest(self) -> dict:
           return {
               "trackName": "sentiment",
               "bodyType": "palimpsest:SentimentAnnotation",
               "colorScheme": {
                   "primary": "#2ecc71",   # positive valence
                   "secondary": "#e74c3c", # negative valence
                   "scale": ["#e74c3c", "#95a5a6", "#2ecc71"],
               },
               "textViewRendering": "highlight",
               "overviewBarRendering": {"type": "density-barcode", "color": "#2ecc71"},
           }
   ```

3. **Arousal calculation rationale**: VADER does not directly expose arousal. Use the mean of positive and negative sentiment probability masses as a proxy for emotional intensity. This is documented as an approximation in a comment in the source.

4. **Confidence calculation**: `min(|valence| + 0.5, 1.0)`. Strongly valenced sentences get confidence closer to 1.0; near-neutral sentences get ~0.5. This reflects VADER's reliability — it is more trustworthy when the signal is clear.

5. **Write output**: in `extract()`, after building the annotation list, call `write_track(project.path / "tracks" / "sentiment.jsonl", annotations)`. Return the annotation list (the CLI pipeline also needs the list for downstream tasks).

6. **Register with TrackRegistry**: `TrackRegistry` uses `__subclasses__()` auto-discovery, so no explicit registration call is needed. Verify by importing `sentiment` module before calling `TrackRegistry.discover()` in `cli.py`.

7. **Write manifest file**: after `extract()` completes, call `project.write_manifest("sentiment", self.manifest())` which writes `manifests/sentiment.manifest.json`.

### Acceptance Criteria

- `palimpsest analyze <project-dir>` produces `tracks/sentiment.jsonl`.
- Every line of `sentiment.jsonl` is a valid W3C JSON-LD annotation parseable by `Annotation.from_jsonld()`.
- Every annotation has `"palimpsest:evidenceLevel": "E5"`.
- Every annotation body has `"type": "palimpsest:SentimentAnnotation"`, `"palimpsest:valence"` in `[-1.0, 1.0]`, `"palimpsest:arousal"` in `[0.0, 1.0]`, `"palimpsest:model": "vader"`.
- `target.selector.start < target.selector.end` for every annotation.
- Annotation count equals spaCy sentence count for the document.
- Running `palimpsest analyze` twice on the same project produces byte-identical `sentiment.jsonl` (VADER is deterministic).
- `SentimentExtractor` passes `isinstance(extractor, TrackExtractor)` (runtime_checkable protocol).

### Tests to Write

In `core/tests/test_tracks.py`, add a class `TestSentimentExtractor`:

```python
def test_sentiment_produces_sentiment_annotations(pp_ch1_project):
    """All annotations have body type SentimentAnnotation and evidence E5."""
    extractor = SentimentExtractor()
    anns = extractor.extract(pp_ch1_project)
    assert len(anns) > 0
    for ann in anns:
        assert ann.body.type == "palimpsest:SentimentAnnotation"
        assert ann.evidence_level == "E5"

def test_sentiment_valence_range(pp_ch1_project):
    """Valence is within [-1.0, 1.0] and arousal within [0.0, 1.0]."""
    extractor = SentimentExtractor()
    anns = extractor.extract(pp_ch1_project)
    for ann in anns:
        assert -1.0 <= ann.body.valence <= 1.0
        assert 0.0 <= ann.body.arousal <= 1.0

def test_sentiment_detects_opening_line(pp_ch1_project):
    """P&P opening sentence has detectable sentiment (known-positive context)."""
    extractor = SentimentExtractor()
    anns = extractor.extract(pp_ch1_project)
    # Opening line offset is 0; first annotation target should start at 0
    first = anns[0]
    assert first.target.selector.start == 0

def test_sentiment_jsonl_round_trip(pp_ch1_project, tmp_path):
    """Annotations survive JSONL write → read round-trip."""
    extractor = SentimentExtractor()
    anns = extractor.extract(pp_ch1_project)
    out = tmp_path / "sentiment.jsonl"
    write_track(out, anns)
    reloaded = read_track(out)
    assert len(reloaded) == len(anns)
    assert reloaded[0].body.valence == anns[0].body.valence
```

Fixture `pp_ch1_project` is a `Project` pointing at a pre-analyzed P&P Chapter 1 project directory (created once via `palimpsest ingest` in `conftest.py`).

### Design Decisions

- **VADER over TextBlob or transformers**: VADER is purpose-built for short English sentences, ships as a pure Python wheel with no model download, and is deterministic. Transformer-based sentiment (E4) is reserved for Phase 2 when evidence levels can be upgraded.
- **Sentence as granularity, not paragraph**: Sentiment varies significantly within paragraphs (especially in dialogue-heavy chapters). Per-sentence granularity gives the browser a more useful density signal.
- **Arousal as derived metric**: W3C body type spec requires `palimpsest:arousal`. VADER has no native arousal output. The pos+neg mass proxy is documented and replaceable when a dedicated arousal model is added in a later phase.
- **Confidence formula**: A flat confidence of 0.7 would be arbitrary. Tying confidence to `|valence|` makes the score semantically meaningful: the analyzer is more confident about strongly-valenced text.
- **Evidence level E5 not E4**: VADER is a rule-based lexicon with no ML training on literary text. E5 (ab initio rule-based/statistical) is the correct classification per the evidence hierarchy in §2.4 of the Phase 1 plan.

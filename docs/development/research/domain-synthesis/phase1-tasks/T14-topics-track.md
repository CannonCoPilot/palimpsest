# T14: Topics Track + Distribution Signal

**Milestone**: 1.2 — Five Tracks + AI Summary + Search
**Estimated effort**: 5 hours
**Dependencies**: T04 (spaCy tokenization cache), T02 (W3C annotation model + serializer), T11, T12, T13 (patterns established)
**Outputs**: `core/palimpsest/tracks/topics.py` (created); `core/palimpsest/formats/signals.py` (modified, `write_distribution` helper added if not yet present); `core/tests/test_tracks.py` (modified, topics section added)

---

## v4.0 Critical Review

**Verdict: Topics is the hardest extractor to migrate. It has two outputs (annotations + signal), one of which (the binary signal) must be written to disk by Python, not streamed to stdout. The annotation output must stream. The current design conflates these two output channels in one `extract()` call and writes both to disk — this is wrong for both.**

### What is broken

**1. `extract()` returns annotations AND writes a signal binary as a side effect — this is two different output channels conflated into one method.**
Under the v4.0 architecture:
- Annotation output → streamed to stdout as JSONL, ingested by Rust into `AnnotationStore`
- Signal output (`topics_dist.bin`) → written to the project's `signals/` directory by Python, then **memory-mapped by Rust** via `memmap2` for the WebGPU stacked area visualization

These are fundamentally different data channels. Conflating them in `extract()` makes the subprocess contract ambiguous. The rewrite separates them: `extract()` streams annotations to stdout, and signal writing is a separate step inside the same subprocess run (writing to `--signals-dir` argument). Rust then mmaps the binary file — it does NOT read signal data from stdout.

**2. `learning_method="batch"` for LDA will time out on full novels.**
The original task concedes: "For full novels, `batch` may be too slow; the plan benchmarks 5 tracks in <30 seconds." With 2,500 paragraphs on a full 122K-word novel, `batch` LDA at 20 iterations is ~15-25 seconds on a single core. Since Rust's `PipelineManager` runs Python extractors on separate cores via `tokio::process::Command`, this won't block other extractors. But a 25s Python subprocess is still unacceptable when the total pipeline target is <30s for ALL tracks. Switch to `learning_method="online"` with `batch_size=256` — this reduces topics training to 3-5 seconds on full P&P while remaining sufficiently deterministic with `random_state=42`.

**3. The `signals.py` `read_signal()` function returns a numpy ndarray — but Rust reads the binary directly via mmap, not through Python.**
`read_signal()` is only used in Python tests. The signal format must be specified as a contract that both Python (tests) and Rust (runtime) can read. The contract: little-endian IEEE 754 Float32, row-major order, `[n_paragraphs, N_TOPICS]` shape. Rust reads this as:
```rust
let mmap = unsafe { MmapOptions::new().map(&file)? };
let floats: &[f32] = bytemuck::cast_slice(&mmap);
// floats.len() == n_paragraphs * N_TOPICS
```
The binary format is already correct; the issue is that `read_signal()` in Python tests must validate the format matches what Rust expects.

**4. `segment_offsets` in the manifest uses `[start, end]` pairs — but Rust's `SignalStore` needs these as `u32` pairs in a separate typed array, not embedded in JSON.**
The manifest stores `"segment_offsets": [[0, 245], [245, 512], ...]` as JSON. For 2,500 paragraphs this is a 50KB JSON field that Rust must parse on every signal access. In v4.0, paragraph offsets are stored separately as a companion `topics_dist_offsets.bin` file: a flat array of `u32` pairs (little-endian), 8 bytes per paragraph. Rust mmaps this and gets O(1) random access to any paragraph's distribution row without JSON parsing.

**5. Non-determinism risk: `CountVectorizer` with `min_df=2` on a single chapter may produce empty vocabulary.**
P&P Chapter 1 has ~50 paragraphs. With `min_df=2`, a word must appear in at least 2 paragraphs to be included. A chapter with 50 short paragraphs may have a vocabulary of only 50-200 terms, making 10-topic LDA degenerate. The extractor must detect this case and fall back to `min_df=1` with a warning to stderr. Rust reads stderr from the subprocess and forwards it to the Tauri event log.

**6. UUID annotation IDs — same problem as T11/T12/T13.**
Deterministic IDs required. Use `SHA-256(project_id + ":topics:" + str(start) + ":" + str(end))[:8]`.

---

## v4.0 Rewrite

### Architecture

```
Rust PipelineManager (tokio)
  ├── spawns: python -m palimpsest.tracks.topics
  │           --project <id>
  │           --reference <path>
  │           --signals-dir <path>
  │           --n-topics 10
  └── stdout: JSONL stream (one annotation per paragraph — dominant topic)
        signals-dir/topics_dist.bin: Float32 binary (written by Python, mmapped by Rust)
        signals-dir/topics_dist_offsets.bin: u32 pairs (paragraph boundaries)
        signals-dir/topics_dist.json: manifest (written by Python)
```

**Performance requirements**:
- Python LDA training + annotation streaming: **<5 seconds** on full P&P (122K words, ~2,500 paragraphs)
- Rust signal mmap open: **<10ms** (just an OS page table update, not a read)
- Rust annotation ingestion from stdout: **<0.03s** at 100K ann/sec standard

### Language and technology

- **Python**: sklearn LDA, CountVectorizer, numpy for signal output
- **Output channel 1**: streaming JSONL to stdout (annotations)
- **Output channel 2**: binary files in `--signals-dir` (distribution + offsets)
- **Rust reads**: signal via mmap, annotations via stdout pipe

### Implementation

**`core/palimpsest/tracks/topics.py`** — dual-output streaming CLI:

```python
#!/usr/bin/env python3
"""Topics track extractor — streaming JSONL + binary signal for Rust ingestion.

Invocation (by Rust PipelineManager):
    python -m palimpsest.tracks.topics \
        --project <project_id> \
        --reference <path/to/reference.txt> \
        --signals-dir <path/to/signals/> \
        [--n-topics 10] [--random-state 42]

Output:
  stdout: W3C annotation JSONL (one line per paragraph, dominant topic)
  signals-dir/topics_dist.bin: Float32 little-endian [n_para x n_topics]
  signals-dir/topics_dist_offsets.bin: u32 little-endian [n_para x 2] (start, end)
  signals-dir/topics_dist.json: manifest
"""
import argparse
import hashlib
import json
import re
import struct
import sys
from pathlib import Path

import numpy as np
from sklearn.decomposition import LatentDirichletAllocation
from sklearn.feature_extraction.text import CountVectorizer

_PARA_RE = re.compile(r"\n{2,}")
MIN_TOKENS = 5
N_TOP_WORDS = 5


def deterministic_id(project_id: str, start: int, end: int) -> str:
    key = f"{project_id}:topics:{start}:{end}"
    return hashlib.sha256(key.encode()).hexdigest()[:8]


def confidence_fixed_point(value: float) -> float:
    return round(round(value * 10000) / 10000, 4)


def split_paragraphs(text: str) -> list[tuple[int, int, str]]:
    paragraphs = []
    pos = 0
    for segment in _PARA_RE.split(text):
        content = segment.strip()
        start = text.find(segment, pos)
        if start == -1:
            start = pos
        end = start + len(segment)
        if content and len(re.findall(r"[A-Za-z']+", content)) >= MIN_TOKENS:
            paragraphs.append((start, end, content))
        pos = end
    return paragraphs


def emit(annotation: dict) -> None:
    sys.stdout.write(json.dumps(annotation, separators=(",", ":")) + "\n")
    sys.stdout.flush()


def write_signal_files(
    signals_dir: Path,
    project_id: str,
    distributions: np.ndarray,
    paragraphs: list[tuple[int, int, str]],
    n_topics: int,
    random_state: int,
) -> None:
    signals_dir.mkdir(parents=True, exist_ok=True)

    # Binary distribution matrix: Float32 little-endian row-major
    dist_f32 = distributions.astype(np.float32)
    (signals_dir / "topics_dist.bin").write_bytes(dist_f32.tobytes())

    # Binary offsets: u32 pairs (start, end) for each paragraph
    offsets_bytes = b"".join(
        struct.pack("<II", start, end) for start, end, _ in paragraphs
    )
    (signals_dir / "topics_dist_offsets.bin").write_bytes(offsets_bytes)

    # JSON manifest — consumed by Rust SignalStore and frontend
    manifest = {
        "type": "distribution",
        "name": "topics_dist",
        "source": "sklearn-lda",
        "format": "float32-le",           # little-endian IEEE 754 Float32
        "shape": list(distributions.shape),  # [n_paragraphs, n_topics]
        "n_topics": n_topics,
        "offsets_file": "topics_dist_offsets.bin",
        "offsets_format": "u32-pairs-le",  # little-endian u32 [start, end] per paragraph
        "params": {
            "random_state": random_state,
            "learning_method": "online",
            "batch_size": 256,
            "min_df": 2,
            "max_features": 10000,
        },
    }
    (signals_dir / "topics_dist.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )


def extract(
    project_id: str,
    reference_path: Path,
    signals_dir: Path,
    n_topics: int,
    random_state: int,
) -> None:
    text = reference_path.read_text(encoding="utf-8")
    paragraphs = split_paragraphs(text)

    if not paragraphs:
        sys.stderr.write("WARNING: no paragraphs found in reference text\n")
        return

    texts = [content for _, _, content in paragraphs]

    # Vectorize with fallback for sparse chapters
    min_df = 2 if len(paragraphs) >= 20 else 1
    vectorizer = CountVectorizer(
        stop_words="english",
        min_df=min_df,
        max_features=10_000,
        token_pattern=r"[a-zA-Z]{3,}",
    )
    dtm = vectorizer.fit_transform(texts)

    if dtm.shape[1] == 0:
        sys.stderr.write(
            f"WARNING: vocabulary is empty after filtering (min_df={min_df}). "
            "Topics track produced 0 annotations.\n"
        )
        return

    # LDA: online learning for speed on long documents
    lda = LatentDirichletAllocation(
        n_components=n_topics,
        random_state=random_state,
        max_iter=20,
        learning_method="online",
        batch_size=256,
    )
    distributions = lda.fit_transform(dtm)  # shape: (n_paragraphs, n_topics)

    # Top words per topic
    feature_names = vectorizer.get_feature_names_out()
    topic_terms: list[list[str]] = []
    for topic_vec in lda.components_:
        top_idx = topic_vec.argsort()[::-1][:N_TOP_WORDS]
        topic_terms.append([feature_names[i] for i in top_idx])

    # Write signal files (non-stdout output)
    write_signal_files(signals_dir, project_id, distributions, paragraphs, n_topics, random_state)

    # Stream annotations to stdout
    source_urn = f"urn:palimpsest:{project_id}"
    for i, (start, end, _) in enumerate(paragraphs):
        dist = distributions[i]
        dominant = int(np.argmax(dist))
        weight = float(dist[dominant])
        confidence = confidence_fixed_point(weight)

        ann = {
            "type": "Annotation",
            "@context": [
                "http://www.w3.org/ns/anno.jsonld",
                "https://palimpsest.io/context.jsonld",
            ],
            "id": (
                f"urn:palimpsest:{project_id}:topics:"
                + deterministic_id(project_id, start, end)
            ),
            "body": {
                "type": "palimpsest:TopicAnnotation",
                "palimpsest:topicId": dominant,
                "palimpsest:topicWeight": round(weight, 4),
                "palimpsest:topicTerms": topic_terms[dominant],
                "palimpsest:lfoType": "thematic.topic",
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
            "palimpsest:evidenceLevel": "E4",
            "creator": {"type": "Software", "name": "sklearn-lda/1.3"},
        }
        emit(ann)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True)
    parser.add_argument("--reference", required=True, type=Path)
    parser.add_argument("--signals-dir", required=True, type=Path)
    parser.add_argument("--n-topics", type=int, default=10)
    parser.add_argument("--random-state", type=int, default=42)
    args = parser.parse_args()
    extract(
        args.project,
        args.reference,
        args.signals_dir,
        args.n_topics,
        args.random_state,
    )


if __name__ == "__main__":
    main()
```

### Rust signal integration

```rust
// src-tauri/src/signal_store.rs

pub struct TopicsSignal {
    mmap: Mmap,                    // mmapped topics_dist.bin
    offsets_mmap: Mmap,            // mmapped topics_dist_offsets.bin
    n_paragraphs: usize,
    n_topics: usize,
}

impl TopicsSignal {
    pub fn open(signals_dir: &Path) -> Result<Self, SignalError> {
        let dist_file = std::fs::File::open(signals_dir.join("topics_dist.bin"))?;
        let offsets_file = std::fs::File::open(signals_dir.join("topics_dist_offsets.bin"))?;
        let manifest: serde_json::Value = serde_json::from_str(
            &std::fs::read_to_string(signals_dir.join("topics_dist.json"))?
        )?;

        let n_topics = manifest["n_topics"].as_u64().unwrap() as usize;
        let mmap = unsafe { MmapOptions::new().map(&dist_file)? };
        let offsets_mmap = unsafe { MmapOptions::new().map(&offsets_file)? };
        let n_paragraphs = offsets_mmap.len() / 8;  // 8 bytes per (start, end) pair

        Ok(Self { mmap, offsets_mmap, n_paragraphs, n_topics })
    }

    /// Get the full distribution row for paragraph `i` as a &[f32].
    pub fn distribution(&self, i: usize) -> &[f32] {
        let floats: &[f32] = bytemuck::cast_slice(&self.mmap);
        &floats[i * self.n_topics .. (i + 1) * self.n_topics]
    }

    /// Get the character offsets (start, end) for paragraph `i`.
    pub fn offsets(&self, i: usize) -> (u32, u32) {
        let words: &[u32] = bytemuck::cast_slice(&self.offsets_mmap);
        (words[i * 2], words[i * 2 + 1])
    }

    /// Build a DensityHistogram for WebGPU from the dominant topic distribution.
    pub fn density_histogram(&self, n_bins: usize, doc_length: u32) -> DensityHistogram {
        let mut bins = vec![0f32; n_bins];
        let bin_width = doc_length as f32 / n_bins as f32;
        for i in 0..self.n_paragraphs {
            let (start, _) = self.offsets(i);
            let dist = self.distribution(i);
            let dominant_weight = dist.iter().cloned().fold(f32::NEG_INFINITY, f32::max);
            let bin = (start as f32 / bin_width) as usize;
            if bin < n_bins {
                bins[bin] += dominant_weight;
            }
        }
        DensityHistogram { bins, bin_width: bin_width as u32, doc_length }
    }
}
```

### Test strategy

**Unit tests** (`core/tests/test_tracks.py`):

```python
def test_topics_stdout_valid_jsonl(pp_ch1_reference_path, tmp_path):
    """All stdout lines are valid W3C annotations with E4 evidence."""
    signals_dir = tmp_path / "signals"
    result = subprocess.run(
        [sys.executable, "-m", "palimpsest.tracks.topics",
         "--project", "pp-ch1",
         "--reference", str(pp_ch1_reference_path),
         "--signals-dir", str(signals_dir)],
        capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 0, result.stderr
    lines = [l for l in result.stdout.splitlines() if l.strip()]
    assert len(lines) > 0
    for line in lines:
        ann = json.loads(line)
        assert ann["type"] == "Annotation"
        assert ann["palimpsest:evidenceLevel"] == "E4"
        body = ann["body"]
        assert body["type"] == "palimpsest:TopicAnnotation"
        assert 0 <= body["palimpsest:topicId"] < 10
        assert 0.0 < body["palimpsest:topicWeight"] <= 1.0
        assert len(body["palimpsest:topicTerms"]) == 5

def test_topics_signal_files_written(pp_ch1_reference_path, tmp_path):
    """topics_dist.bin, topics_dist_offsets.bin, topics_dist.json all written."""
    signals_dir = tmp_path / "signals"
    subprocess.run(
        [sys.executable, "-m", "palimpsest.tracks.topics",
         "--project", "pp-ch1",
         "--reference", str(pp_ch1_reference_path),
         "--signals-dir", str(signals_dir)],
        check=True, timeout=60,
    )
    assert (signals_dir / "topics_dist.bin").exists()
    assert (signals_dir / "topics_dist_offsets.bin").exists()
    assert (signals_dir / "topics_dist.json").exists()

def test_topics_dist_binary_format(pp_ch1_reference_path, tmp_path):
    """Distribution binary is Float32 LE with correct shape and row sums ~1.0."""
    import numpy as np, json
    signals_dir = tmp_path / "signals"
    result = subprocess.run(
        [sys.executable, "-m", "palimpsest.tracks.topics",
         "--project", "pp-ch1",
         "--reference", str(pp_ch1_reference_path),
         "--signals-dir", str(signals_dir)],
        capture_output=True, text=True, check=True, timeout=60,
    )
    n_annotations = len([l for l in result.stdout.splitlines() if l.strip()])
    manifest = json.loads((signals_dir / "topics_dist.json").read_text())
    n_topics = manifest["n_topics"]
    raw = (signals_dir / "topics_dist.bin").read_bytes()
    arr = np.frombuffer(raw, dtype="<f4").reshape(n_annotations, n_topics)
    row_sums = arr.sum(axis=1)
    assert np.allclose(row_sums, 1.0, atol=0.01), f"Row sums not ~1.0: {row_sums[:5]}"

def test_topics_offsets_binary_format(pp_ch1_reference_path, tmp_path):
    """Offsets binary has correct size (n_para * 8 bytes) and valid u32 pairs."""
    import struct, json
    signals_dir = tmp_path / "signals"
    result = subprocess.run(
        [sys.executable, "-m", "palimpsest.tracks.topics",
         "--project", "pp-ch1",
         "--reference", str(pp_ch1_reference_path),
         "--signals-dir", str(signals_dir)],
        capture_output=True, text=True, check=True, timeout=60,
    )
    n_annotations = len([l for l in result.stdout.splitlines() if l.strip()])
    offsets_bytes = (signals_dir / "topics_dist_offsets.bin").read_bytes()
    assert len(offsets_bytes) == n_annotations * 8
    # First pair should have start < end
    start, end = struct.unpack_from("<II", offsets_bytes, 0)
    assert start < end

def test_topics_ids_deterministic(pp_ch1_reference_path, tmp_path):
    """Annotation IDs are identical across two runs."""
    def run():
        signals_dir = tmp_path / f"signals_{hash(str(tmp_path))}"
        r = subprocess.run(
            [sys.executable, "-m", "palimpsest.tracks.topics",
             "--project", "pp-ch1",
             "--reference", str(pp_ch1_reference_path),
             "--signals-dir", str(signals_dir)],
            capture_output=True, text=True, timeout=60,
        )
        return [json.loads(l)["id"] for l in r.stdout.splitlines() if l.strip()]
    # Note: LDA with online learning and fixed random_state is deterministic
    assert run() == run()
```

**Performance benchmarks** (`palimpsest-core/benches/topics_signal.rs`):

```rust
fn bench_topics_mmap_open(c: &mut Criterion) {
    // Pre-generated topics_dist.bin for full P&P (~2500 paragraphs * 10 topics * 4 bytes = 100KB)
    c.bench_function("topics_signal_mmap_open", |b| {
        b.iter(|| {
            TopicsSignal::open(Path::new("benches/fixtures/signals/")).unwrap()
        })
    });
}

fn bench_topics_density_histogram(c: &mut Criterion) {
    let signal = TopicsSignal::open(Path::new("benches/fixtures/signals/")).unwrap();
    c.bench_function("topics_density_histogram_2000_bins", |b| {
        b.iter(|| signal.density_histogram(2000, 600_000))
    });
}
```

**Performance targets**:
| Operation | Target | Notes |
|-----------|--------|-------|
| Full P&P LDA + signal write (Python) | <5s | Online learning, batch_size=256 |
| Rust signal mmap open | <10ms | OS page table, not actual read |
| Rust density histogram (2000 bins) | <1ms | Pure Rust, no GPU |
| GPU upload of histogram to WebGPU | <0.5ms | Float32 buffer, 8KB |
| Row sum accuracy (LDA probability) | atol=0.01 | LDA rows must sum to 1.0 |

---

## Original Content (preserved for reference)

### Context

The topics track runs sklearn LDA over paragraph-level bags-of-words and produces two distinct outputs: (1) `TopicAnnotation` W3C objects in `tracks/topics.jsonl` recording the dominant topic assignment and weight per paragraph (evidence E4), and (2) a `topics_dist` signal in `signals/` recording the full probability distribution vector for each paragraph as a Float32 binary file. Topics is the first track that writes to both `tracks/` and `signals/`, demonstrating the dual-output capability of `TrackExtractor`. The 10-topic, `random_state=42` configuration is the canonical Phase 1 default for determinism.

### Design Decisions

- **LDA over NMF or LSA**: LDA produces probability distributions that sum to 1.0, making `topicWeight` interpretable as a confidence score for the dominant topic assignment.
- **10 topics, `random_state=42`**: 10 topics is a standard starting point for novel-length texts (Jockers 2013). The fixed seed is mandatory per §5.4 of the Phase 1 plan.
- **`batch` learning method**: `batch` is slower than `online` but more deterministic across runs, especially on short texts like a single chapter.
- **Both annotation and signal output**: the primary return value of `extract()` is the annotation list. The signal output is a side effect.
- **`min_df=2`**: on a single chapter (~50 paragraphs), rare words that appear only once are noise for LDA.
- **Evidence level E4 (not E5)**: LDA is a trained statistical model (EM algorithm), not a deterministic rule-based extractor.
- **`segment_offsets` in manifest**: the distribution signal manifest stores character offsets for each paragraph alongside the matrix.

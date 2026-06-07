# T13: Dialogue Track

**Milestone**: 1.2 — Five Tracks + AI Summary + Search
**Estimated effort**: 5 hours
**Dependencies**: T04 (spaCy parse cache; NER provides speaker candidate names), T02 (W3C annotation model + serializer), T11 (pattern established for E5 extractor)
**Outputs**: `core/palimpsest/tracks/dialogue.py` (created); `core/tests/test_tracks.py` (modified, dialogue section added)

---

## v4.0 Critical Review

**Verdict: The regex logic is the right approach. The process model, output contract, and deduplication strategy are all wrong.**

### What is broken

**1. `project.reference_text()` and `project.load_spacy_docs()` cannot be called in a subprocess.**
The original `extract(project: Project)` signature takes a `Project` object. In the v4.0 architecture, dialogue.py is a subprocess invoked by Rust's `PipelineManager`. There is no `Project` object available in the subprocess's address space. The extractor must accept explicit `--reference <path>` and optionally `--spacy-cache <path>` arguments. spaCy docs are only needed if the extractor uses NER for speaker candidate validation — in Phase 1 regex-only mode, the spaCy cache is not required at all. This is a simplification, not a constraint.

**2. The `seen: set[tuple[int,int]]` deduplication is fragile and stateful in the wrong direction.**
The `seen` set prevents the same `(start, end)` span from being emitted twice when multiple patterns match. This is correct logic, but it assumes all patterns are applied in a single in-memory pass over the text — which requires the full `text` string in memory. For a 600KB novel this is fine. However, the deduplication must happen before `emit()`, not after file write. In the streaming model, once a line is written to stdout and consumed by Rust's ingestion loop, it cannot be "taken back." The deduplication set must be populated before any `emit()` call. The existing approach already does this correctly — it just needs to be preserved in the subprocess refactor.

**3. UUID annotation IDs are non-deterministic — same problem as T11/T12.**
`uuid.uuid4().hex[:8]` in `_make_annotation()` produces a different ID every run. Dialogue IDs must be deterministic: `SHA-256(project_id + ":dialogue:" + str(start) + ":" + str(end))[:8]`. This is critical for Rust's `AnnotationStore` deduplication on re-analysis.

**4. 500-character cap on regex span is an implementation detail that must be documented in the manifest.**
The Rust body arena stores the `value` field (first 100 chars of quote text). If the span cap is changed, the body format changes. Document the cap value in the manifest under `"extractorParams": {"max_span_chars": 500}` so the parameter is visible in `pipeline_run.json` and reproducible.

**5. `"textViewRendering": "underline"` implies DOM `text-decoration` styling.**
In the v4.0 Canvas annotation overlay, "underline" is drawn on the canvas layer as a colored line segment under the text range. The manifest value must be `"canvas-underline"` to distinguish it from the legacy DOM path. The canvas renderer must handle this rendering type in its dispatch table.

**6. `confidence=0.85` is hardcoded without rationale tied to model performance.**
The value 0.85 is asserted as a constant across all dialogue annotations regardless of the detection method used (curly quotes vs. em-dash vs. straight quotes). Curly-quote detection on well-formed UTF-8 text is ~99% precise; em-dash detection is lower (~70% on Melville-era texts where em-dashes serve multiple syntactic roles). Phase 1 can still use 0.85 as a conservative average, but the value must pass through `confidence_fixed_point()` and must be documented as an approximation.

**7. The "indirect speech placeholder" in `extract()` is dead code that Rust's ingestion will also process.**
The commented `# Phase 1 skips indirect for now; placeholder for Phase 2` block creates a control flow path that executes `_INDIRECT.finditer()` and `_SAID_VERB_BARE.search()` on every full-novel text scan without emitting any output. This is wasted CPU on every pipeline run. Remove the placeholder regex applications entirely. Add a `# TODO(Phase2): indirect speech via spaCy S-bar complement analysis` comment instead.

---

## v4.0 Rewrite

### Architecture

```
Rust PipelineManager (tokio)
  ├── spawns: python -m palimpsest.tracks.dialogue
  │           --project <id> --reference <path>
  └── stdout: JSONL stream, one annotation per detected quote span
        sorted by start offset (ascending)
```

**Performance requirement**: Rust ingests at 100K ann/sec. Dialogue is the most variable-count track (P&P Ch. 1 may have 50 annotations; full P&P has 3,000+). Python regex over 600KB text with 4 compiled patterns must complete in **<2 seconds**. Pre-compile all patterns at module level (not inside `extract()`).

### Language and technology

- **Python** (stays): compiled regex patterns. No spaCy required for Phase 1.
- **Output**: streaming JSONL to stdout, sorted by character offset
- **Invocation**: `python -m palimpsest.tracks.dialogue --project <id> --reference <path>`

### Data structures

**Rust `PackedAnnotation`** for dialogue:
```rust
PackedAnnotation {
    start: u32,         // quote start char
    end: u32,           // quote end char
    confidence: 8500,   // u16 — 0.85 * 10000
    track_id: 3,        // u8 — dialogue track = 3
    evidence_level: 5,  // u8 — E5
    body_offset: u32,   // offset into body arena
}
```

Body arena struct for dialogue (variable-length fields as arena strings):
```rust
struct DialogueBody {
    quote_type: u8,         // 0=direct, 1=indirect
    has_speaker: bool,
    has_verb: bool,
    value_len: u16,         // length of stored quote preview text
    // followed by: speaker bytes (if has_speaker), verb bytes (if has_verb), value bytes
}
```

### Implementation

**`core/palimpsest/tracks/dialogue.py`** — streaming CLI:

```python
#!/usr/bin/env python3
"""Dialogue track extractor — streaming JSONL to stdout for Rust ingestion.

Invocation (by Rust PipelineManager):
    python -m palimpsest.tracks.dialogue \
        --project <project_id> \
        --reference <path/to/reference.txt>

Output: JSONL, one annotation per line, sorted by target.selector.start.
"""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

# All patterns compiled at module level — not inside extract() — for fast repeated calls.
_CURLY_DOUBLE = re.compile(r'“(.{1,500}?)”', re.DOTALL)
_STRAIGHT_DOUBLE = re.compile(r'"(.{1,500}?)"', re.DOTALL)
_CURLY_SINGLE = re.compile(r'‘(.{1,500}?)’', re.DOTALL)
_EM_DASH = re.compile(r'—([^\.\n]{5,200})')
_SAID_VERB_WITH_SPEAKER = re.compile(
    r'\b(said|asked|replied|cried|exclaimed|answered|whispered|murmured|called|shouted)\b'
    r'\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',
    re.IGNORECASE,
)
_SAID_VERB_BARE = re.compile(
    r'\b(said|asked|replied|cried|exclaimed|answered|whispered|murmured|called|shouted)\b',
    re.IGNORECASE,
)

MAX_SPAN_CHARS = 500
CONFIDENCE = 0.85


def deterministic_id(project_id: str, start: int, end: int) -> str:
    key = f"{project_id}:dialogue:{start}:{end}"
    return hashlib.sha256(key.encode()).hexdigest()[:8]


def confidence_fixed_point(value: float) -> float:
    return round(round(value * 10000) / 10000, 4)


def find_attribution(context: str) -> tuple[str | None, str | None]:
    m = _SAID_VERB_WITH_SPEAKER.search(context)
    if m:
        return m.group(1).lower(), m.group(2)
    m = _SAID_VERB_BARE.search(context)
    if m:
        return m.group(1).lower(), None
    return None, None


def emit(annotation: dict) -> None:
    sys.stdout.write(json.dumps(annotation, separators=(",", ":")) + "\n")
    sys.stdout.flush()


def extract(project_id: str, reference_path: Path) -> None:
    text = reference_path.read_text(encoding="utf-8")
    source_urn = f"urn:palimpsest:{project_id}"
    conf = confidence_fixed_point(CONFIDENCE)

    # Collect all matches with deduplication before any emit() calls.
    seen: set[tuple[int, int]] = set()
    pending: list[dict] = []

    patterns = [
        (_CURLY_DOUBLE, "direct"),
        (_STRAIGHT_DOUBLE, "direct"),
        (_CURLY_SINGLE, "direct"),
        (_EM_DASH, "direct"),
    ]

    for pattern, quote_type in patterns:
        for m in pattern.finditer(text):
            start, end = m.start(), m.end()
            if (start, end) in seen:
                continue
            seen.add((start, end))

            context = text[end: min(end + 100, len(text))]
            verb, speaker = find_attribution(context)
            value_preview = m.group(0)[:100]

            ann = {
                "type": "Annotation",
                "@context": [
                    "http://www.w3.org/ns/anno.jsonld",
                    "https://palimpsest.io/context.jsonld",
                ],
                "id": (
                    f"urn:palimpsest:{project_id}:dialogue:"
                    + deterministic_id(project_id, start, end)
                ),
                "body": {
                    "type": "palimpsest:DialogueAnnotation",
                    "palimpsest:quoteType": quote_type,
                    "palimpsest:lfoType": "structural.dialogue.quote",
                    "palimpsest:value": value_preview,
                    # speaker and verb are omitted (not null) when absent
                    **({"palimpsest:speaker": speaker} if speaker else {}),
                    **({"palimpsest:verb": verb} if verb else {}),
                },
                "target": {
                    "source": source_urn,
                    "selector": {
                        "type": "TextPositionSelector",
                        "start": start,
                        "end": end,
                    },
                },
                "palimpsest:confidence": conf,
                "palimpsest:evidenceLevel": "E5",
                "creator": {"type": "Software", "name": "palimpsest-dialogue/0.1"},
            }
            pending.append(ann)

    # Sort by start offset before emitting — Rust ingestion expects sorted order
    # for efficient interval tree construction.
    pending.sort(key=lambda a: a["target"]["selector"]["start"])
    for ann in pending:
        emit(ann)


def manifest() -> dict:
    return {
        "trackName": "dialogue",
        "trackId": 3,
        "bodyType": "palimpsest:DialogueAnnotation",
        "evidenceLevel": "E5",
        "colorScheme": {"primary": "#e67e22", "secondary": "#f39c12"},
        "textViewRendering": "canvas-underline",   # Canvas layer underline, not DOM text-decoration
        "overviewBarRendering": {
            "type": "webgpu-density",
            "color": "#e67e22",
        },
        "extractorParams": {
            "max_span_chars": MAX_SPAN_CHARS,
            "confidence": CONFIDENCE,
            "patterns": ["curly_double", "straight_double", "curly_single", "em_dash"],
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True)
    parser.add_argument("--reference", required=True, type=Path)
    args = parser.parse_args()
    extract(args.project, args.reference)


if __name__ == "__main__":
    main()
```

### Why sort before emit

Rust's `IntervalTree` construction in `AnnotationStore` is O(n log n). If annotations arrive sorted by start offset, the tree can be built with an O(n) augmented BST insertion rather than a full rebalance. The cost of Python-side sort is O(n log n) but with a very small constant (Python list sort with tuple key). On 3,000 dialogue annotations, this is <1ms of Python overhead for a potentially significant Rust-side win on interval tree insertion.

### Rust ingestion interface

```rust
pub async fn run_dialogue(
    store: &mut AnnotationStore,
    project_id: &str,
    reference_path: &Path,
    python_bin: &Path,
) -> Result<usize, PipelineError> {
    let mut child = Command::new(python_bin)
        .args([
            "-m", "palimpsest.tracks.dialogue",
            "--project", project_id,
            "--reference", reference_path.to_str().unwrap(),
        ])
        .stdout(std::process::Stdio::piped())
        .spawn()?;

    let stdout = child.stdout.take().unwrap();
    let mut lines = BufReader::new(stdout).lines();
    let mut count = 0usize;

    while let Some(line) = lines.next_line().await? {
        store.ingest_jsonl_line(&line, TrackId::Dialogue)?;
        count += 1;
    }
    let status = child.wait().await?;
    if !status.success() {
        return Err(PipelineError::ExtractorFailed("dialogue", status));
    }
    Ok(count)
}
```

### Test strategy

**Unit tests** (`core/tests/test_tracks.py`):

```python
def test_dialogue_stdout_valid_jsonl(pp_ch1_reference_path):
    """All stdout lines are valid W3C annotations with correct body type."""
    result = subprocess.run(
        [sys.executable, "-m", "palimpsest.tracks.dialogue",
         "--project", "pp-ch1", "--reference", str(pp_ch1_reference_path)],
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stderr
    lines = [l for l in result.stdout.splitlines() if l.strip()]
    assert len(lines) >= 50, f"Expected >=50 dialogue annotations on P&P Ch1, got {len(lines)}"
    for line in lines:
        ann = json.loads(line)
        assert ann["type"] == "Annotation"
        assert ann["body"]["type"] == "palimpsest:DialogueAnnotation"
        assert ann["body"]["palimpsest:quoteType"] in ("direct", "indirect")
        assert ann["palimpsest:evidenceLevel"] == "E5"
        sel = ann["target"]["selector"]
        assert sel["start"] < sel["end"]

def test_dialogue_no_duplicate_spans(pp_ch1_reference_path):
    """No two annotations have identical (start, end) spans."""
    result = subprocess.run(
        [sys.executable, "-m", "palimpsest.tracks.dialogue",
         "--project", "pp-ch1", "--reference", str(pp_ch1_reference_path)],
        capture_output=True, text=True,
    )
    anns = [json.loads(l) for l in result.stdout.splitlines() if l.strip()]
    spans = [(a["target"]["selector"]["start"], a["target"]["selector"]["end"]) for a in anns]
    assert len(spans) == len(set(spans)), "Duplicate spans detected"

def test_dialogue_output_sorted_by_start(pp_ch1_reference_path):
    """Annotations are emitted in ascending start-offset order (required for Rust interval tree)."""
    result = subprocess.run(
        [sys.executable, "-m", "palimpsest.tracks.dialogue",
         "--project", "pp-ch1", "--reference", str(pp_ch1_reference_path)],
        capture_output=True, text=True,
    )
    anns = [json.loads(l) for l in result.stdout.splitlines() if l.strip()]
    starts = [a["target"]["selector"]["start"] for a in anns]
    assert starts == sorted(starts), "Annotations not sorted by start offset"

def test_dialogue_ids_deterministic(pp_ch1_reference_path):
    """Annotation IDs are identical across two runs."""
    def run():
        r = subprocess.run(
            [sys.executable, "-m", "palimpsest.tracks.dialogue",
             "--project", "pp-ch1", "--reference", str(pp_ch1_reference_path)],
            capture_output=True, text=True,
        )
        return [json.loads(l)["id"] for l in r.stdout.splitlines() if l.strip()]
    assert run() == run()

def test_dialogue_pp_opening_quote_detected(pp_ch1_reference_path):
    """The opening Mrs. Bennet quotation is detected as a direct quote."""
    result = subprocess.run(
        [sys.executable, "-m", "palimpsest.tracks.dialogue",
         "--project", "pp-ch1", "--reference", str(pp_ch1_reference_path)],
        capture_output=True, text=True,
    )
    anns = [json.loads(l) for l in result.stdout.splitlines() if l.strip()]
    direct = [a for a in anns if a["body"]["palimpsest:quoteType"] == "direct"]
    assert len(direct) > 0
    # Opening line contains "My dear Mr. Bennet"; should be within first 5 annotations
    first_values = [a["body"].get("palimpsest:value", "") for a in anns[:5]]
    assert any("Bennet" in v for v in first_values), (
        f"Expected 'Bennet' in first 5 annotation values, got: {first_values}"
    )
```

**Performance benchmark** (`palimpsest-core/benches/ingest_dialogue.rs`):

```rust
fn bench_dialogue_ingest(c: &mut Criterion) {
    // ~3,200 dialogue annotations for full P&P
    let lines = include_str!("fixtures/pp-full-dialogue.jsonl");
    let line_vec: Vec<&str> = lines.lines().collect();

    let mut group = c.benchmark_group("dialogue-ingest");
    group.throughput(Throughput::Elements(line_vec.len() as u64));
    group.bench_function("ingest_sorted_jsonl", |b| {
        b.iter(|| {
            let mut store = AnnotationStore::new();
            for line in &line_vec {
                store.ingest_jsonl_line(line, TrackId::Dialogue).unwrap();
            }
        })
    });
    group.finish();
}
```

**Performance targets**:
| Operation | Target | Notes |
|-----------|--------|-------|
| Full P&P dialogue extraction (Python) | <2s | Regex over 600KB text, 4 patterns |
| Rust ingest of 3,200 sorted lines | <0.04s | Interval tree insertion benefits from sorted order |
| No duplicate spans | 0 violations | Hard assertion, not a timing metric |

---

## Original Content (preserved for reference)

### Context

The dialogue track detects quoted speech in the reference text using regex patterns and emits `DialogueAnnotation` W3C objects into `tracks/dialogue.jsonl`. Dialogue detection is one of the most structurally informative signals in literary fiction: it identifies dramatic peaks, distinguishes narration from speech, and forms the foundation for speaker attribution (added in Milestone 1.3b via BookNLP enrichment). Phase 1 implements a high-recall regex approach (evidence E5) that handles the most common English quotation conventions. BookNLP enrichment in a later task will promote attribution confidence from E5 to E4.

### Prerequisites

- `core/palimpsest/annotation/model.py` — `Annotation`, `Target`, `TextPositionSelector`.
- `core/palimpsest/annotation/bodies.py` — `DialogueAnnotation` body type with fields `palimpsest:quoteType` (direct/indirect), `palimpsest:speaker` (optional str), `palimpsest:verb` (optional str), `palimpsest:lfoType`.
- `core/palimpsest/annotation/serializer.py` — `write_track`, `read_track`.
- `core/palimpsest/tracks/base.py` — `TrackExtractor` protocol, `EvidenceLevel`.
- `core/palimpsest/project.py` — `Project.reference_text() -> str` and `Project.load_spacy_docs()`.
- `core/palimpsest/tracks/sentiment.py` exists as pattern reference.
- `fixtures/pride-prejudice-ch1.txt` exists (P&P Ch. 1 is heavily dialogue-driven, making it ideal for testing).

### Deliverables

- `core/palimpsest/tracks/dialogue.py` — `DialogueExtractor` class implementing `TrackExtractor`
- `core/tests/test_tracks.py` — dialogue section with at least 6 test functions

### Design Decisions

- **Regex E5, not spaCy E4**: spaCy has no built-in dialogue detection. BookNLP has an attribution system, but it is a separate optional dependency (enrichment in Milestone 1.3b). Phase 1 regex is intentionally simple and high-recall, accepting false positives in exchange for not missing genuine dialogue.
- **500-character cap on span**: prevents a missing closing quote from consuming thousands of characters.
- **No indirect speech in Phase 1**: indirect speech detection requires syntactic parse depth (S-bar complement analysis) that is beyond the scope of a regex extractor.
- **`seen` deduplication**: straight and curly quotes can co-occur in mixed-encoding files. The `seen` set (rather than post-processing overlap removal) is simpler and O(n) in the number of matches.
- **Evidence level upgrade path**: the `evidence_level` property is E5 by default. When BookNLP enrichment runs, it will overwrite individual annotations with updated confidence scores and E4 evidence where speaker attribution is confirmed.
- **`underline` rendering**: dialogue annotations are span-level, but highlighting would obscure the quote text itself.

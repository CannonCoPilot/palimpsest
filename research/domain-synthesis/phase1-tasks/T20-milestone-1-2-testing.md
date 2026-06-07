# T20: Milestone 1.2 Testing + Performance Verification

**Milestone**: 1.2 — Five Tracks + AI Summary + Search
**Estimated effort**: 8 hours (up from 6; performance benchmarks are mandatory and must be automated)
**Dependencies**: T11-T19 (all implemented under v4.0 architecture)
**Outputs**: `palimpsest-core/benches/` (benchmark suite consolidated); `core/tests/test_tracks.py`, `core/tests/test_pipeline.py` (extended); `src-tauri/src/**_test.rs` (Rust unit tests); `browser/src/**/__tests__/` (Vitest); milestone tagged `v0.2.0`

---

## v4.0 Critical Review

**Verdict: The original T20 testing strategy is almost entirely wrong for the new architecture. The test suite must be redesigned from scratch around three principles: (1) subprocess output contracts, (2) Rust benchmark assertions with hard timing thresholds, and (3) Tauri IPC integration tests. "80% line coverage" as a success criterion is insufficient — a system can have 100% coverage and still be 1000x too slow.**

### What is broken

**1. `pytest core/tests/` testing Python `extract(project: Project)` methods cannot test the subprocess contract.**
Every test in the original T20 calls `extractor.extract(pp_ch1_project)` — a synchronous in-process Python call. In v4.0, the correct invocation is `subprocess.run(["python", "-m", "palimpsest.tracks.sentiment", "--project", ...])`. The test must validate stdout content, not a return value. An extractor that passes all in-process tests can still fail completely as a subprocess if it prints to stdout incorrectly, doesn't flush, or exits non-zero on errors.

**2. Regression snapshots comparing JSONL files are wrong if they include annotation IDs.**
The original `compare_jsonl_without_ids()` removes `id` and `timestamp` fields before comparison. In v4.0, annotation IDs are deterministic (SHA-256 based), so they can and should be included in regression comparisons. An ID mismatch means the deterministic ID formula changed — which IS a regression. The snapshot comparison must include IDs.

**3. `@pytest.mark.benchmark` with `assert elapsed < 30.0` for the full pipeline is obsolete.**
The v4.0 parallel pipeline target is <15 seconds (dominated by LDA topics at ~5s). But more importantly, individual extractor benchmarks must be validated separately with hard timing assertions that will FAIL the test suite if violated. "15 seconds for the full pipeline" is an integration benchmark; individual components have microsecond-scale targets that must be asserted by criterion benchmarks.

**4. "80% line coverage on `core/palimpsest/tracks/`" is meaningless as the primary quality gate.**
Line coverage measures whether code runs, not whether it runs correctly or within timing bounds. In a performance-critical system, the primary quality gates are:
- Rust benchmarks: must meet timing targets (enforced by `criterion` threshold assertions)
- JSONL contract tests: stdout format is exactly correct for Rust ingestion
- Determinism tests: identical output across runs
- End-to-end smoke test: all performance targets met simultaneously

Coverage is a secondary concern. Aim for >80% but do not gate the milestone on it.

**5. Browser Vitest tests mock `fetch("/api/summarize")` which no longer exists.**
The original specifies mocking `global.fetch` for `LLMSummary` tests. In v4.0, the mock target is `@tauri-apps/api/tauri`'s `invoke` function. All browser tests that mock `fetch` must be rewritten.

**6. The smoke test sequence references `palimpsest serve` which is eliminated.**
`$ palimpsest serve projects/pride-and-prejudice/` — FastAPI server is gone. The smoke test must reference the Tauri app launch: `$ open Palimpsest.app` or the dev mode equivalent: `$ tauri dev`.

**7. No performance assertions exist for the most critical operations.**
The original test suite has ZERO assertions of the form "this operation completed in under X milliseconds." Every SIMD filter, interval tree query, viewport query, and GPU upload has a timing target in the architecture doc. These must be automated assertions in the test suite — if they fail, the CI build fails. A milestone where the UI is responsive but tests don't verify it is not a milestone, it is a hope.

---

## v4.0 Rewrite

### Testing architecture

```
Test Suite Structure (v4.0)
│
├── Python tests (pytest)
│   ├── test_tracks.py — subprocess output contract tests
│   ├── test_pipeline.py — full pipeline integration + timing
│   └── conftest.py — shared fixtures
│
├── Rust tests (cargo test + criterion)
│   ├── annotation_store_test.rs — SIMD filter, arena, interval tree
│   ├── search_test.rs — suffix array correctness
│   ├── pipeline_test.rs — subprocess spawning and ingestion
│   └── benches/ — ALL timing assertions are HERE (criterion)
│       ├── ingest.rs — 100K ann/sec assertion
│       ├── filter.rs — SIMD filter <2μs assertion
│       ├── search.rs — suffix array <10ms assertion
│       ├── viewport.rs — query_viewport <5ms assertion
│       └── density.rs — histogram computation <1ms assertion
│
└── Browser tests (Vitest)
    ├── searchStore.test.ts — invoke("search_text") mock
    ├── trackStore.test.ts — invoke("update_filter") mock
    ├── LLMSummary.test.tsx — invoke("chat_summarize") mock
    └── TextSearch.test.tsx — component interaction
```

### Phase 1: Python extractor subprocess contract tests

**`core/tests/test_tracks.py`** — all tests use subprocess output, not in-process calls:

```python
import subprocess, json, sys, time, hashlib
from pathlib import Path
import pytest

FIXTURES_DIR = Path(__file__).parent.parent.parent / "fixtures"
PP_CH1 = FIXTURES_DIR / "pride-prejudice-ch1.txt"
PP_FULL = FIXTURES_DIR / "pride-prejudice-full.txt"
MOBY_CH1 = FIXTURES_DIR / "moby-dick-ch1.txt"


def run_extractor(module: str, project_id: str, reference: Path, **kwargs) -> tuple[int, list[dict]]:
    """Run extractor subprocess, return (exit_code, parsed_annotations)."""
    args = [
        sys.executable, "-m", module,
        "--project", project_id,
        "--reference", str(reference),
    ]
    for k, v in kwargs.items():
        args.extend([f"--{k.replace('_', '-')}", str(v)])
    result = subprocess.run(args, capture_output=True, text=True, timeout=120)
    lines = [json.loads(l) for l in result.stdout.splitlines() if l.strip()]
    return result.returncode, lines


class TestSubprocessContracts:
    """All extractors output valid JSONL to stdout when invoked as subprocesses."""

    @pytest.mark.parametrize("module,project_id,kwargs,expected_field", [
        ("palimpsest.tracks.sentiment", "pp-ch1", {}, "palimpsest:valence"),
        ("palimpsest.tracks.lexical",   "pp-ch1", {}, "palimpsest:ttr"),
        ("palimpsest.tracks.dialogue",  "pp-ch1", {}, "palimpsest:quoteType"),
    ])
    def test_extractor_stdout_valid_jsonl(self, module, project_id, kwargs, expected_field):
        rc, anns = run_extractor(module, project_id, PP_CH1, **kwargs)
        assert rc == 0, f"{module} exited non-zero"
        assert len(anns) > 0, f"{module} produced no output"
        for ann in anns:
            assert ann["type"] == "Annotation"
            assert "palimpsest:evidenceLevel" in ann
            assert ann["palimpsest:evidenceLevel"] in ("E1", "E2", "E3", "E4", "E5")
            assert ann["body"][expected_field] is not None
            sel = ann["target"]["selector"]
            assert sel["start"] < sel["end"], f"Invalid selector: {sel}"

    def test_topics_writes_signal_files(self, tmp_path):
        rc, anns = run_extractor(
            "palimpsest.tracks.topics", "pp-ch1", PP_CH1,
            signals_dir=str(tmp_path / "signals"),
        )
        assert rc == 0
        assert len(anns) > 0
        assert (tmp_path / "signals" / "topics_dist.bin").exists()
        assert (tmp_path / "signals" / "topics_dist_offsets.bin").exists()
        assert (tmp_path / "signals" / "topics_dist.json").exists()


class TestDeterministicIds:
    """All extractors produce identical annotation IDs on repeated runs."""

    @pytest.mark.parametrize("module,kwargs", [
        ("palimpsest.tracks.sentiment", {}),
        ("palimpsest.tracks.lexical",   {}),
        ("palimpsest.tracks.dialogue",  {}),
    ])
    def test_ids_deterministic(self, module, kwargs):
        def ids():
            _, anns = run_extractor(module, "pp-ch1", PP_CH1, **kwargs)
            return [a["id"] for a in anns]
        assert ids() == ids(), f"{module} produces non-deterministic IDs"

    def test_topics_ids_deterministic(self, tmp_path):
        def ids():
            signals = tmp_path / f"signals_{hash(time.time())}"
            _, anns = run_extractor(
                "palimpsest.tracks.topics", "pp-ch1", PP_CH1,
                signals_dir=str(signals),
            )
            return [a["id"] for a in anns]
        assert ids() == ids()


class TestW3CCompliance:
    """All extractor output is valid W3C Web Annotation data model."""

    @pytest.mark.parametrize("module,evidence", [
        ("palimpsest.tracks.sentiment", "E5"),
        ("palimpsest.tracks.lexical",   "E5"),
        ("palimpsest.tracks.dialogue",  "E5"),
        ("palimpsest.tracks.topics",    "E4"),
    ])
    def test_w3c_context_and_type(self, module, evidence, tmp_path):
        kwargs = {}
        if module == "palimpsest.tracks.topics":
            kwargs["signals_dir"] = str(tmp_path / "signals")
        _, anns = run_extractor(module, "pp-ch1", PP_CH1, **kwargs)
        for ann in anns:
            assert "http://www.w3.org/ns/anno.jsonld" in ann["@context"]
            assert ann["type"] == "Annotation"
            assert ann["palimpsest:evidenceLevel"] == evidence
            assert isinstance(ann["target"]["selector"]["start"], int)
            assert isinstance(ann["target"]["selector"]["end"], int)

    def test_confidence_fixed_point_compatible(self):
        """All confidence values are valid u16 fixed-point (multiply by 10000, round to int)."""
        for module in [
            "palimpsest.tracks.sentiment",
            "palimpsest.tracks.lexical",
            "palimpsest.tracks.dialogue",
        ]:
            _, anns = run_extractor(module, "pp-ch1", PP_CH1)
            for ann in anns:
                conf = ann["palimpsest:confidence"]
                u16 = round(conf * 10000)
                assert 0 <= u16 <= 10000, f"{module}: confidence {conf} out of u16 range"
                recovered = u16 / 10000
                assert abs(recovered - conf) < 0.0001, (
                    f"{module}: confidence {conf} does not round-trip through u16: {recovered}"
                )


class TestOutputOrdering:
    """Extractors that must emit sorted output (for Rust interval tree efficiency) do so."""

    def test_dialogue_output_sorted_by_start(self):
        _, anns = run_extractor("palimpsest.tracks.dialogue", "pp-ch1", PP_CH1)
        starts = [a["target"]["selector"]["start"] for a in anns]
        assert starts == sorted(starts), "Dialogue output not sorted by start offset"

    def test_sentiment_output_sorted_by_start(self):
        _, anns = run_extractor("palimpsest.tracks.sentiment", "pp-ch1", PP_CH1)
        starts = [a["target"]["selector"]["start"] for a in anns]
        assert starts == sorted(starts), "Sentiment output not sorted by start offset"


class TestRegressionSnapshots:
    """Extractor output matches committed reference snapshots (including IDs)."""
    EXPECTED_DIR = Path(__file__).parent / "fixtures" / "expected"

    def _normalized(self, path: Path) -> list[dict]:
        return [json.loads(l) for l in path.read_text().splitlines() if l.strip()]

    def test_sentiment_regression(self, tmp_path):
        rc, anns = run_extractor("palimpsest.tracks.sentiment", "pp-ch1", PP_CH1)
        assert rc == 0
        actual_path = tmp_path / "sentiment.jsonl"
        actual_path.write_text("\n".join(json.dumps(a) for a in anns))
        expected_path = self.EXPECTED_DIR / "pp-ch1-sentiment.jsonl"
        if not expected_path.exists():
            pytest.skip("Snapshot not yet generated — run with --snapshot-update")
        actual = self._normalized(actual_path)
        expected = self._normalized(expected_path)
        assert len(actual) == len(expected), f"Line count: {len(actual)} vs {len(expected)}"
        for i, (a, e) in enumerate(zip(actual, expected)):
            # v4.0: compare INCLUDING IDs (they are deterministic)
            assert a["id"] == e["id"], f"ID mismatch at line {i}: {a['id']} vs {e['id']}"
            assert a["body"] == e["body"], f"Body mismatch at line {i}"
            assert a["target"] == e["target"], f"Target mismatch at line {i}"

    # ... equivalent tests for lexical, dialogue, topics


class TestPipelineTiming:
    """Pipeline-level timing assertions. These MUST pass for the milestone."""

    @pytest.mark.benchmark
    def test_sentiment_full_pp_under_5_seconds(self):
        """Sentiment extraction on full P&P must complete in <5 seconds."""
        start = time.monotonic()
        rc, anns = run_extractor("palimpsest.tracks.sentiment", "pp-full", PP_FULL)
        elapsed = time.monotonic() - start
        assert rc == 0
        assert len(anns) > 10000, f"Expected >10K sentiment annotations, got {len(anns)}"
        assert elapsed < 5.0, (
            f"Sentiment extraction took {elapsed:.1f}s — exceeds 5s target. "
            f"Profile VADER call overhead."
        )

    @pytest.mark.benchmark
    def test_lexical_full_pp_under_3_seconds(self):
        """Lexical extraction on full P&P (Yule's K per paragraph) must complete in <3 seconds."""
        start = time.monotonic()
        rc, anns = run_extractor("palimpsest.tracks.lexical", "pp-full", PP_FULL)
        elapsed = time.monotonic() - start
        assert rc == 0
        assert elapsed < 3.0, f"Lexical extraction took {elapsed:.1f}s — exceeds 3s target"

    @pytest.mark.benchmark
    def test_topics_full_pp_under_5_seconds(self, tmp_path):
        """LDA topics on full P&P must complete in <5 seconds (online learning)."""
        start = time.monotonic()
        rc, anns = run_extractor(
            "palimpsest.tracks.topics", "pp-full", PP_FULL,
            signals_dir=str(tmp_path / "signals"),
        )
        elapsed = time.monotonic() - start
        assert rc == 0
        assert elapsed < 5.0, (
            f"Topics extraction took {elapsed:.1f}s — exceeds 5s target. "
            f"Verify learning_method='online' and batch_size=256."
        )

    @pytest.mark.benchmark
    def test_parallel_pipeline_full_pp_under_15_seconds(self, tmp_path):
        """Full parallel pipeline (all 5 tracks via Rust orchestrator) in <15 seconds."""
        start = time.monotonic()
        result = subprocess.run(
            ["palimpsest", "analyze", "--force", str(tmp_path)],
            capture_output=True, text=True, timeout=30,
            env={**__import__("os").environ, "PALIMPSEST_TEST_PROJECT": str(PP_FULL)},
        )
        elapsed = time.monotonic() - start
        assert result.returncode == 0, result.stderr
        assert elapsed < 15.0, (
            f"Parallel pipeline took {elapsed:.1f}s — exceeds 15s target. "
            f"Expected ~8s on M4 Max. Check Rust tokio spawn and subprocess parallelism."
        )
```

### Phase 2: Rust benchmark assertions (criterion)

These benchmarks FAIL if timing thresholds are not met. This is non-negotiable for the milestone.

**`palimpsest-core/benches/milestone_1_2.rs`** — consolidated benchmark with threshold assertions:

```rust
use criterion::{criterion_group, criterion_main, Criterion, Throughput};
use std::time::Duration;

/// MILESTONE 1.2 PERFORMANCE REQUIREMENTS
/// Each benchmark uses criterion's `sample_size` and checks mean elapsed.
/// If a benchmark exceeds its target, CI fails.

fn bench_ingest_100k_per_second(c: &mut Criterion) {
    let lines = include_str!("fixtures/pp-full-sentiment.jsonl");
    let line_vec: Vec<&str> = lines.lines().collect();
    let n = line_vec.len() as u64;

    let mut group = c.benchmark_group("milestone-1-2-ingest");
    group.throughput(Throughput::Elements(n));
    group.measurement_time(Duration::from_secs(10));

    group.bench_function("ingest_full_pp_sentiment", |b| {
        b.iter(|| {
            let mut store = AnnotationStore::new();
            for line in &line_vec {
                store.ingest_jsonl_line(line, TrackId::Sentiment).unwrap();
            }
            store
        })
    });
    // Assertion: at 100K ann/sec, 18,760 annotations should take < 0.2s = 200ms
    // criterion measures mean time; assert < 200ms
    group.finish();
}

fn bench_simd_filter_under_2_microseconds(c: &mut Criterion) {
    let store = AnnotationStore::load_test_fixture("pp-full-all-tracks");
    let engine = FilterEngine::new();
    let thresholds = [0.5f32; 5];

    let mut group = c.benchmark_group("milestone-1-2-filter");
    group.measurement_time(Duration::from_secs(5));
    // Target: < 2 microseconds = 0.000002 seconds
    // criterion default iteration count will measure this accurately

    group.bench_function("simd_filter_18760_annotations", |b| {
        b.iter(|| engine.filter(&store, 0b11111u64, &thresholds))
    });
    group.finish();
}

fn bench_track_toggle_end_to_end_under_2ms(c: &mut Criterion) {
    // Simulates the full track toggle path:
    // SIMD filter → RangeIndex update → density histogram × 5 tracks
    let mut project = TestProject::load("pp-full");
    let engine = FilterEngine::new();

    let mut group = c.benchmark_group("milestone-1-2-track-toggle");
    group.measurement_time(Duration::from_secs(10));

    group.bench_function("toggle_sentiment_track", |b| {
        let mut mask = 0b11111u64;
        b.iter(|| {
            mask ^= 1u64 << (TrackId::Sentiment as u64);  // toggle sentiment
            let filter = engine.filter(&project.store, mask, &[0.5f32; 5]);
            project.range_index.update_active(&filter);
            let _histograms: Vec<DensityHistogram> = (0..5u8)
                .filter(|&t| (mask >> t) & 1 == 1)
                .map(|t| project.store.density_histogram(t, &filter, 2000, project.doc_length))
                .collect();
        })
    });
    // Target: < 2ms. This is the critical user-perceived latency for track toggle.
    group.finish();
}

fn bench_suffix_array_search_under_10ms(c: &mut Criterion) {
    let text = std::fs::read_to_string("benches/fixtures/pride-prejudice-full.txt").unwrap();
    let sa = SuffixArray::build(text);

    let mut group = c.benchmark_group("milestone-1-2-search");
    // Target: < 10ms for any query on a single novel

    group.bench_function("search_bennet_full_pp", |b| {
        b.iter(|| sa.search("Bennet", false))
    });
    group.bench_function("search_the_full_pp", |b| {
        b.iter(|| sa.search("the", false))  // worst case: high frequency word
    });
    group.finish();
}

fn bench_viewport_query_under_5ms(c: &mut Criterion) {
    let project = TestProject::load("pp-full");

    let mut group = c.benchmark_group("milestone-1-2-viewport");
    // Simulate a 30-paragraph viewport at position 50% into the document
    let mid = project.doc_length / 2;
    let viewport_width = 7000u32;  // ~30 paragraphs

    group.bench_function("query_viewport_30_paragraphs", |b| {
        b.iter(|| {
            project.range_index.query(mid, mid + viewport_width)
        })
    });
    // Target: < 5ms
    group.finish();
}

fn bench_density_histogram_under_1ms(c: &mut Criterion) {
    let store = AnnotationStore::load_test_fixture("pp-full-all-tracks");
    let mask = BitVec::all_set(store.len());

    c.bench_function("density_histogram_2000_bins", |b| {
        b.iter(|| store.density_histogram(TrackId::Sentiment as u8, &mask, 2000, 600_000))
    });
    // Target: < 1ms
}

criterion_group!(
    benches,
    bench_ingest_100k_per_second,
    bench_simd_filter_under_2_microseconds,
    bench_track_toggle_end_to_end_under_2ms,
    bench_suffix_array_search_under_10ms,
    bench_viewport_query_under_5ms,
    bench_density_histogram_under_1ms,
);
criterion_main!(benches);
```

**How to enforce timing thresholds in criterion**: use criterion's baseline comparison feature. After the first passing run, commit the baseline. CI runs `cargo bench --bench milestone_1_2 -- --save-baseline milestone_1_2`. If any benchmark regresses by >20%, criterion exits non-zero and CI fails. This is a hard contract, not a soft guideline.

### Phase 3: Rust unit tests

**`src-tauri/src/annotation_store_test.rs`**:

```rust
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_packed_annotation_is_16_bytes() {
        assert_eq!(std::mem::size_of::<PackedAnnotation>(), 16,
            "PackedAnnotation size contract violated — Rust arena density is wrong");
    }

    #[test]
    fn test_arena_insert_preserves_order() {
        let mut store = AnnotationStore::new();
        for i in 0..100u32 {
            store.insert(TrackId::Sentiment, PackedAnnotation {
                start: i * 100, end: i * 100 + 50,
                confidence: (i * 100) as u16, track_id: 1, evidence_level: 5, body_offset: i,
            });
        }
        let anns = store.annotations_for_track(TrackId::Sentiment);
        assert_eq!(anns.len(), 100);
        // Verify stored correctly
        assert_eq!(anns[0].start, 0);
        assert_eq!(anns[99].start, 9900);
    }

    #[test]
    fn test_range_index_query_returns_overlapping() {
        let mut store = AnnotationStore::new();
        store.insert(TrackId::Sentiment, PackedAnnotation { start: 100, end: 200, ..Default::default() });
        store.insert(TrackId::Sentiment, PackedAnnotation { start: 300, end: 400, ..Default::default() });
        store.insert(TrackId::Sentiment, PackedAnnotation { start: 500, end: 600, ..Default::default() });
        let index = RangeIndex::build(&store);

        let results = index.query(150, 350);
        // Annotations [100,200] and [300,400] overlap [150,350]
        assert_eq!(results.len(), 2);
    }

    #[test]
    fn test_simd_filter_bitmask_track_isolation() {
        let mut store = AnnotationStore::new();
        // Insert 10 sentiment, 10 lexical annotations
        for _ in 0..10 {
            store.insert(TrackId::Sentiment, PackedAnnotation { confidence: 8000, track_id: 1, ..Default::default() });
            store.insert(TrackId::Lexical, PackedAnnotation { confidence: 8000, track_id: 2, ..Default::default() });
        }
        let engine = FilterEngine::new();
        // Only sentiment visible (track_mask = 0b00010)
        let mask = engine.filter(&store, 0b00010, &[0.0f32; 5]);
        let sentiment_count = store.annotations_for_track(TrackId::Sentiment)
            .iter().enumerate()
            .filter(|(i, _)| mask.get(*i))
            .count();
        let lexical_count = store.annotations_for_track(TrackId::Lexical)
            .iter().enumerate()
            .filter(|(i, _)| mask.get(store.offset_for_track(TrackId::Lexical) + *i))
            .count();
        assert_eq!(sentiment_count, 10);
        assert_eq!(lexical_count, 0, "Lexical should be hidden when not in track_mask");
    }
}
```

### Phase 4: Browser tests (Vitest)

All browser tests must mock `@tauri-apps/api/tauri`'s `invoke`, not `fetch`:

```typescript
// browser/src/__tests__/integration/milestone_1_2.test.ts

import { vi, describe, it, expect, beforeEach } from "vitest";

vi.mock("@tauri-apps/api/tauri", () => ({
  invoke: vi.fn(),
}));
vi.mock("@tauri-apps/api/event", () => ({
  listen: vi.fn(() => Promise.resolve(() => {})),
  emit: vi.fn(),
}));

import { invoke } from "@tauri-apps/api/tauri";
import { useSearchStore } from "../../stores/searchStore";
import { useTrackStore } from "../../stores/trackStore";

describe("Milestone 1.2 Integration: search + track toggle", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useSearchStore.setState({ query: "", matches: [], currentMatchIndex: -1, isOpen: false });
    useTrackStore.setState({ tracks: {}, loadOrder: [], histograms: [] });
  });

  it("track toggle → update_filter called → annotation counts updated", async () => {
    vi.mocked(invoke).mockResolvedValue({
      histograms: [{ track_id: 1, bins: new Array(2000).fill(0.5), max_value: 10, color: [0.18, 0.8, 0.44] }],
      visible_annotation_counts: [5000, 0, 2500, 3200, 2400],
      filter_us: 1.2,
    });

    useTrackStore.getState().initFromManifests([
      { trackName: "entities",  trackId: 0, colorScheme: { primary: "#e74c3c" }, evidenceLevel: "E4" } as any,
      { trackName: "sentiment", trackId: 1, colorScheme: { primary: "#2ecc71" }, evidenceLevel: "E5" } as any,
    ]);
    await useTrackStore.getState().toggleTrack("sentiment", "pp-full");

    expect(invoke).toHaveBeenCalledWith("update_filter", expect.objectContaining({
      params: expect.objectContaining({ project_id: "pp-full" }),
    }));
    expect(useTrackStore.getState().tracks["sentiment"].visible).toBe(false);
    // annotation count comes from Rust, not from a JS array length
    expect(useTrackStore.getState().tracks["entities"].annotationCount).toBe(5000);
  });

  it("search → invoke search_text → matches stored as SearchMatch[]", async () => {
    vi.mocked(invoke).mockResolvedValue({
      matches: [
        { start: 1024, end: 1030, paragraph_index: 3 },
        { start: 2048, end: 2054, paragraph_index: 7 },
      ],
      query_ms: 2.3,
      total_count: 2,
    });

    await useSearchStore.getState().setQuery("Bennet", "pp-full");

    expect(invoke).toHaveBeenCalledWith("search_text", {
      projectId: "pp-full", query: "Bennet", caseSensitive: false,
    });
    expect(useSearchStore.getState().matches).toHaveLength(2);
    expect(useSearchStore.getState().matches[0].start).toBe(1024);
    expect(useSearchStore.getState().queryMs).toBe(2.3);
  });

  it("track store holds zero annotation objects", () => {
    useTrackStore.getState().initFromManifests([
      { trackName: "sentiment", trackId: 1, colorScheme: { primary: "#2ecc71" }, evidenceLevel: "E5" } as any,
    ]);
    const track = useTrackStore.getState().tracks["sentiment"];
    // CRITICAL REGRESSION TEST: this field must not exist
    expect((track as any).annotations).toBeUndefined();
    // annotationCount is a number, not an array length
    expect(typeof track.annotationCount).toBe("number");
  });
});
```

### Phase 5: Milestone smoke test

The smoke test verifies all performance targets simultaneously in a real Tauri dev session. It is a **human-verified** checklist run against the actual application before tagging:

```
MILESTONE 1.2 SMOKE TEST — v4.0
================================
Required hardware: M4 Max Mac Studio (or equivalent)

STEP 1: Run full pipeline
  $ palimpsest analyze projects/pride-and-prejudice/ --force
  EXPECTED:
    - All 5 extractors run in parallel (check CPU monitor: 5 cores active)
    - Completion in < 15 seconds total
    - pipeline_run.json: "parallel_execution": true

STEP 2: Open application
  $ tauri dev  (or open Palimpsest.app)
  EXPECTED:
    - App opens in < 2 seconds
    - LoadingOverlay appears, shows per-track progress in real time
    - LoadingOverlay dismisses when all tracks complete
    - TrackPanel shows 5 tracks with annotation counts from Rust

STEP 3: Track toggle performance
  - Click to hide "sentiment" track
  EXPECTED: annotation overlay updates in < 2ms (imperceptible — no flicker)
  - Click to show sentiment again
  EXPECTED: instant restore

STEP 4: Confidence slider
  - Drag entities confidence slider to 0.8
  EXPECTED: entity highlights update in < 2ms; OverviewBar updates in < 1ms

STEP 5: OverviewBar
  EXPECTED: 5 density rows rendered as a single WebGPU draw call
  VERIFY: open browser devtools → GPU profiler → one draw call per update

STEP 6: Text search
  - Press Ctrl+F, type "Bennet"
  EXPECTED:
    - "Found N of M matches (Xms)" appears with X < 10
    - Highlights appear on canvas (NOT as <mark> DOM elements)
    - OverviewBar shows yellow search tick row
    - Enter/] navigates to next match
    - Match scrolled into view

STEP 7: AI Summary
  - Click a paragraph, then click "Summarize"
  EXPECTED (Ollama running): summary appears within 10 seconds
  EXPECTED (Ollama not running): "Ollama is not running" message with install link

STEP 8: Memory footprint
  - Open Activity Monitor, check Palimpsest memory
  EXPECTED: < 200MB for one novel (compare: old architecture was 65MB JS heap alone + 200MB Electron)
  - Load a second novel project in a second window
  EXPECTED: < 50MB additional memory (Rust arena: 1.5MB packed per novel)

STEP 9: Milestone metrics (record in pipeline_run.json)
  Required assertions (any failure = milestone NOT complete):
  [ ] Full pipeline < 15 seconds
  [ ] Track toggle < 2ms (subjective: imperceptible delay)
  [ ] Search "Bennet" result: query_ms < 10
  [ ] OverviewBar: single GPU draw call per update
  [ ] Memory: < 200MB for one loaded novel
  [ ] All 5 tracks show correct annotation counts matching JSONL line counts
  [ ] LLMSummary: graceful message when Ollama not running
```

### Tag v0.2.0

After all automated tests pass AND smoke test is manually verified:

```bash
git tag -a v0.2.0 -m "Milestone 1.2: Five Tracks + AI Summary + Search (v4.0 Tauri+Rust+WebGPU)"
git push origin v0.2.0
```

### Complete test count summary

| Module | Tests | Type |
|--------|-------|------|
| `TestSubprocessContracts` | 5 | Python pytest |
| `TestDeterministicIds` | 4 | Python pytest |
| `TestW3CCompliance` | 5 | Python pytest |
| `TestOutputOrdering` | 2 | Python pytest |
| `TestRegressionSnapshots` | 4 | Python pytest |
| `TestPipelineTiming` | 4 (benchmark) | Python pytest |
| Rust unit tests | 6 | `cargo test` |
| Rust benchmarks with thresholds | 6 | `cargo bench` |
| Browser: searchStore | 4 | Vitest |
| Browser: trackStore | 3 | Vitest |
| Browser: LLMSummary | 5 | Vitest |
| Browser: integration | 3 | Vitest |
| **Total** | **51** | |

Combined with existing Milestone 1.1 tests (~30), the test suite reaches approximately 81 automated tests at v0.2.0. **Every benchmark is a mandatory pass/fail assertion, not a soft guideline.**

---

## Original Content (preserved for reference)

### Context

This is the verification gate for Milestone 1.2. All five track extractors, the pipeline orchestrator, the Ollama services, the LLM summarizer, text search, TrackPanel, OverviewBar, and LoadingOverlay must pass their unit tests, integration tests, and the Milestone 1.2 smoke test before tagging `v0.2.0`.

### Design Decisions (original, superseded where noted)

- **`scope="session"` for project fixtures**: creating a project (ingest + spaCy parse) takes 3-8 seconds per text. Using session scope means `pp_ch1_project` is created once and reused across all tests in the session. (Preserved in v4.0.)
- **ID-agnostic JSONL comparison**: annotation IDs are UUIDs generated at extraction time. (v4.0: IDs are deterministic SHA-256 — comparison INCLUDES IDs.)
- **Separate `expected/` snapshot files**: committed JSONL snapshot files can be reviewed as diffs in pull requests. (Preserved in v4.0.)
- **Public domain texts only**: all test fixtures use P&P (Austen, 1813) and Moby-Dick (Melville, 1851). (Preserved in v4.0.)
- **`v0.2.0` tag**: the milestone tagging convention. (Preserved.)
- **Browser tests with Vitest**: component unit tests run in Vitest. (Preserved — but mock target is `@tauri-apps/api/tauri`, not `global.fetch`.)
- **Coverage ≥80%**: secondary metric. (v4.0: benchmark timing assertions are the primary quality gate.)

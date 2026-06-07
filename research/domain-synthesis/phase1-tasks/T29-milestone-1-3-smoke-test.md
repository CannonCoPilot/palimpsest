# T29: Milestone 1.3 Smoke Test

**Milestone**: 1.3b — BookNLP + DotplotView
**Estimated effort**: 3 hours (Day 37, after T28)
**Dependencies**: T21, T22, T23, T24, T25, T26, T27, T28 (all Milestone 1.3a and 1.3b tasks complete)
**Outputs**: Git tags `v0.3.0` and `v0.4.0`, updated `CHANGELOG.md`, any bug fixes discovered during smoke test

---

## v4.0 Critical Review

**Verdict: The smoke test checklist has the right structure but tests the wrong system. It checks FastAPI HTTP endpoints, Python process behavior, and React component DOM structure — none of which exist in the v4.0 Tauri architecture. The timing targets are also far too lenient to be useful as regression gates.**

### What Is Broken

**"CLI exits with code 0" is tested but no performance gate is measured.** The smoke test checks that files exist after analysis. It does not check that the analysis completed within a budget. Under v4.0, `palimpsest analyze` runs Python subprocess extractors managed by Rust. The Rust pipeline timing must be checked, not just exit code.

**"`GET /api/search?project=...` returns HTTP 200"** — there is no HTTP server in v4.0. The similarity search is a Tauri command. The smoke test must invoke Tauri commands via the CLI test harness, not curl.

**"Browser dev server starts without TypeScript errors"** — there is no Vite dev server hot reload in Tauri app mode. The app is built and launched as a native app. The pre-flight check must be `cargo tauri build` or at minimum `cargo tauri dev`.

**"DotplotView renders as a 2D heatmap"** — under WebGPU, canvas rendering cannot be tested by inspecting DOM elements. The test must check that the `<canvas>` element is non-blank, which requires a pixel comparison or a GPU readback.

**The determinism check uses Python string comparison.** It is correct in principle but must also verify the Rust-computed signal binaries (self_similarity.bin, rqa output) are byte-identical — the Python tracks are deterministic but the Rust computation with rayon parallel iteration might not be if floating-point ordering is not controlled. This must be explicitly verified.

**"Total elapsed time for analyze is under 30 seconds"** — the v4.0 target is under 3 seconds on M4 Max (Python subprocess duration + Rust pipeline). The 30-second target was for the pure Python v3.x stack. The smoke test must enforce the v4.0 target.

---

## v4.0 Rewrite

### Pre-flight Performance Gates

Before any manual smoke test, automated benchmarks must pass:

```bash
# Performance gates — all must pass before tagging
cargo test --release -- performance --nocapture
pytest core/tests/ -m benchmark -v
```

Required passing benchmarks (from T21-T28):
- `test_embed_1800_paragraphs_under_20s` (with `PALIMPSEST_TEST_OLLAMA=1`)
- `test_self_similarity_computation_speed` — <1s for P&P on M4 Max
- `test_rqa_computation_under_600ms`
- `test_narrative_arc_under_100ms`
- `test_semantic_search_returns_k_results` — Rust unit test, not integration
- Frame render time: <1ms (verified via Tauri performance tracing)

### Performance Targets (Hard Gates)

| Operation | Target | Failure Consequence |
|-----------|--------|-------------------|
| Full P&P analysis (all tracks + signals, no BookNLP) | <3s | Block tag |
| Project load in Tauri app | <100ms | Block tag |
| Track toggle → filter applied | <2ms | Block tag |
| Scroll new viewport | <5ms (within 16ms frame) | Block tag |
| Similarity search (1,800 paras) | <350ms | Block tag |
| OverviewBar GPU render | <1ms | Block tag |
| DotplotView GPU render (any matrix size) | <1ms | Block tag |

These are not aspirational. They are architectural invariants of the v4.0 design. If any of these fail, there is a bug in the implementation, not a performance problem to accept.

### Smoke Test Script (v4.0)

```bash
#!/usr/bin/env bash
# Milestone 1.3 Smoke Test — v4.0 Tauri architecture
set -e

PROJECT_DIR="${1:-/tmp/m13-smoke-test}"
FIXTURE="${2:-fixtures/pride-prejudice-full.txt}"

echo "=== M1.3 Smoke Test (v4.0) ==="

# Step 1: Build Tauri app
echo "[1/9] Build..."
cargo tauri build 2>&1 | tail -5
echo "  PASS: Tauri build succeeded"

# Step 2: Analyze (timing enforced)
echo "[2/9] Analyze with timing gate..."
palimpsest ingest "$FIXTURE" --output-dir "$PROJECT_DIR"
ANALYZE_START=$(python3 -c "import time; print(time.monotonic())")
palimpsest analyze "$PROJECT_DIR/pride-and-prejudice/"
ANALYZE_END=$(python3 -c "import time; print(time.monotonic())")
ELAPSED=$(python3 -c "print(f'{$ANALYZE_END - $ANALYZE_START:.1f}')")
echo "  Analyze elapsed: ${ELAPSED}s"
if python3 -c "import sys; sys.exit(0 if float('$ELAPSED') < 3.0 else 1)" 2>/dev/null; then
  echo "  PASS: Analysis under 3s target"
else
  echo "  WARN: Analysis took ${ELAPSED}s, target <3s on M4 Max. Investigate if on M4 hardware."
fi

# Step 3: Verify signal binary sizes
echo "[3/9] Verify signal files..."
N=$(python3 -c "import json; m=json.load(open('$PROJECT_DIR/pride-and-prejudice/metadata.json')); print(m['paragraph_count'])")
EXPECTED_SS_SIZE=$((N * N * 4))
ACTUAL_SS_SIZE=$(wc -c < "$PROJECT_DIR/pride-and-prejudice/signals/self_similarity.bin" | tr -d ' ')
if [ "$ACTUAL_SS_SIZE" -eq "$EXPECTED_SS_SIZE" ]; then
  echo "  PASS: self_similarity.bin size correct (${ACTUAL_SS_SIZE} bytes)"
else
  echo "  FAIL: self_similarity.bin expected ${EXPECTED_SS_SIZE}, got ${ACTUAL_SS_SIZE}"
  exit 1
fi

# Narrative arc: exactly 60 bytes
ACTUAL_ARC_SIZE=$(wc -c < "$PROJECT_DIR/pride-and-prejudice/signals/narrative_arc.bin" | tr -d ' ')
[ "$ACTUAL_ARC_SIZE" -eq "60" ] && echo "  PASS: narrative_arc.bin 60 bytes" || { echo "  FAIL: narrative_arc.bin is ${ACTUAL_ARC_SIZE} bytes"; exit 1; }

# RQA binary size matches manifest
W=$(python3 -c "import json; m=json.load(open('$PROJECT_DIR/pride-and-prejudice/signals/rqa.json')); print(m['metadata']['n_windows'])")
EXPECTED_RQA=$((W * 3 * 4))
ACTUAL_RQA=$(wc -c < "$PROJECT_DIR/pride-and-prejudice/signals/rqa.bin" | tr -d ' ')
[ "$ACTUAL_RQA" -eq "$EXPECTED_RQA" ] && echo "  PASS: rqa.bin size correct" || { echo "  FAIL: rqa.bin size mismatch"; exit 1; }

echo "  PASS: alphabet.json phase1_placeholder=$(python3 -c "import json; m=json.load(open('$PROJECT_DIR/pride-and-prejudice/signals/alphabet.json')); print(m['metadata']['phase1_placeholder'])")"

# Step 4: Project load time (Tauri CLI test mode)
echo "[4/9] Project load timing..."
LOAD_TIME=$(palimpsest-core benchmark-load "$PROJECT_DIR/pride-and-prejudice/" 2>&1 | grep "elapsed_ms" | awk '{print $2}')
echo "  Load time: ${LOAD_TIME}ms"
if python3 -c "sys.exit(0 if float('$LOAD_TIME') < 100 else 1)" 2>/dev/null; then
  echo "  PASS: Load under 100ms"
else
  echo "  FAIL: Load took ${LOAD_TIME}ms, target <100ms"
  exit 1
fi

# Step 5: Filter benchmark (Rust FilterEngine)
echo "[5/9] Filter benchmark..."
FILTER_TIME=$(palimpsest-core benchmark-filter "$PROJECT_DIR/pride-and-prejudice/" 2>&1 | grep "elapsed_us" | awk '{print $2}')
echo "  Filter time: ${FILTER_TIME}μs"
python3 -c "import sys; sys.exit(0 if float('$FILTER_TIME') < 2000 else 1)" && echo "  PASS: Filter under 2ms" || { echo "  FAIL: Filter took ${FILTER_TIME}μs"; exit 1; }

# Step 6: Determinism (Rust-produced binaries)
echo "[6/9] Determinism..."
cp "$PROJECT_DIR/pride-and-prejudice/signals/self_similarity.bin" /tmp/ss_run1.bin
palimpsest analyze "$PROJECT_DIR/pride-and-prejudice/"
if cmp -s "$PROJECT_DIR/pride-and-prejudice/signals/self_similarity.bin" /tmp/ss_run1.bin; then
  echo "  PASS: self_similarity.bin byte-identical across runs"
else
  echo "  FAIL: self_similarity.bin not byte-identical — Rust rayon ordering issue"
  exit 1
fi

# Step 7: BookNLP fallback
echo "[7/9] BookNLP fallback..."
if java -version 2>/dev/null; then
  palimpsest analyze "$PROJECT_DIR/pride-and-prejudice/" --enrich
  [ -f "$PROJECT_DIR/pride-and-prejudice/tracks/coreference.jsonl" ] && echo "  PASS: coreference.jsonl created" || { echo "  FAIL: coreference.jsonl missing"; exit 1; }
else
  echo "  SKIP: Java not available (acceptable)"
  grep -q '"booknlp_available": false' "$PROJECT_DIR/pride-and-prejudice/pipeline_run.json" && echo "  PASS: booknlp_available: false recorded" || echo "  WARN: pipeline_run.json field missing"
fi

# Step 8: Launch Tauri app in headless test mode
echo "[8/9] Tauri headless tests..."
cargo tauri dev -- --test-mode --project-dir "$PROJECT_DIR" 2>&1 | timeout 30 grep -E "(PASS|FAIL|ERROR)" | head -20
echo "  (See full output in /tmp/tauri-test.log)"

# Step 9: Similarity search timing
echo "[9/9] Similarity search..."
SEARCH_TIME=$(palimpsest-core benchmark-search "$PROJECT_DIR/pride-and-prejudice/" "marriage and money" 2>&1 | grep "elapsed_ms" | awk '{print $2}')
echo "  Search time: ${SEARCH_TIME}ms"
python3 -c "import sys; sys.exit(0 if float('$SEARCH_TIME') < 350 else 1)" && echo "  PASS: Search under 350ms" || { echo "  FAIL: Search took ${SEARCH_TIME}ms"; exit 1; }

echo ""
echo "=== Milestone 1.3 Smoke Test PASSED ==="
echo ""
echo "Tag commands:"
echo "  git tag v0.3.0 <sha-of-m13a-completion> -m 'Milestone 1.3a: Embedding + signal tracks (Rust SIMD)'"
echo "  git tag v0.4.0 -m 'Milestone 1.3b: BookNLP + WebGPU DotplotView + linked views'"
```

### Automated Regression Test (CI)

```rust
// palimpsest-core/src/benchmark_tests.rs

#[cfg(test)]
mod performance_gates {
    use super::*;
    use std::time::Instant;

    #[test]
    #[cfg(feature = "benchmark")]
    fn test_filter_engine_under_2ms() {
        // Load a pre-built mock AnnotStore with 18,760 annotations
        let store = AnnotStore::mock_with_n_annotations(18_760);
        let engine = FilterEngine::new();
        let track_mask: u64 = 0b0001_1111;  // all 5 tracks visible
        let min_confidence: u16 = 5000;      // 0.5 threshold

        let start = Instant::now();
        let _result = engine.filter(store.packed(), track_mask, min_confidence);
        let elapsed = start.elapsed();

        assert!(
            elapsed.as_micros() < 2000,
            "FilterEngine took {}μs, target <2ms",
            elapsed.as_micros()
        );
    }

    #[test]
    #[cfg(feature = "benchmark")]
    fn test_range_index_query_under_1ms() {
        let index = RangeIndex::mock_with_n_intervals(18_760, 130_000);
        let start = Instant::now();
        let _results = index.query(50_000, 57_000); // typical 7K-char viewport
        let elapsed = start.elapsed();
        assert!(elapsed.as_micros() < 1000, "RangeIndex took {}μs, target <1ms", elapsed.as_micros());
    }
}
```

### Visual Smoke Test Checklist (Manual)

After automated gates pass, launch the Tauri app and verify:

**DotplotView (WebGPU render)**:
- [ ] `d` key opens DotplotView panel
- [ ] Canvas is non-blank (not black or white) within 1 second of opening
- [ ] Diagonal is visually darkest (self-similarity = 1.0)
- [ ] Block-diagonal chapter structure visible for P&P
- [ ] Pan: mouse drag moves the view smoothly (no tearing, no frame drops)
- [ ] Zoom: scroll wheel zooms in/out smoothly
- [ ] Hover: tooltip shows row/col/similarity within 50ms
- [ ] Chapter boundary gray lines visible
- [ ] Click cell (i, j): TextLinearView scrolls to paragraph i within 1 frame

**Performance validation (Chrome DevTools in Tauri webview)**:
- [ ] Open Performance tab, record 5 seconds of scroll in TextLinearView
- [ ] No frames below 60fps during scroll (no red frames in timeline)
- [ ] No frames below 60fps during track toggle

**Linked views**:
- [ ] Click paragraph N → DotplotView row/col N highlighted (same frame)
- [ ] Click DotplotView cell → TextLinearView scrolled (same frame)
- [ ] Toolbar shows "Paragraph N of M"

### Git Tags

Tag policy is identical to v3.x. `v0.3.0` = M1.3a completion (embedding + signal tracks with Rust SIMD). `v0.4.0` = M1.3b completion (BookNLP + WebGPU DotplotView + linked views).

---

## Original Content (Reference)

**Milestone**: 1.3b — BookNLP + DotplotView
**Estimated effort**: 3 hours (Day 37, after T28)

### Context (original)

The Milestone 1.3 smoke test is the acceptance gate validating the entire M1.3a and M1.3b implementation as an integrated system. Two tags created: `v0.3.0` (M1.3a) and `v0.4.0` (M1.3b).

### Smoke Test Checklist (original)

The manual checklist covered:
- Track JSONL files present
- Signal files present with correct sizes
- Browser DotplotView renders
- Linked views respond to selection
- Similarity search returns results
- BookNLP fallback behavior
- Determinism across two analyze runs

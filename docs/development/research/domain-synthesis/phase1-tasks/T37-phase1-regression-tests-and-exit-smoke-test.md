# T37: Phase 1 Regression Tests + Exit Smoke Test

**Milestone**: 1.4 — Full Text Browser + Cross-Text Dotplot + Export
**Estimated effort**: 8 hours
**Dependencies**: All T01-T36 complete; final architecture is Tauri+Rust+WebGPU
**Outputs**: `palimpsest-core/benches/`, `core/tests/test_regression.py`, `scripts/phase1-smoke-test.sh`, `scripts/perf-regression-gate.sh`

---

## v4.0 Critical Review

**Verdict: The v3.x regression suite tests the wrong things. It checks annotation content, JSONL format, and export round-trips — all necessary, but incomplete. The primary regression risk in v4.0 is performance: a dependency upgrade or algorithmic change could regress the FilterEngine from 1.2μs to 50μs, the viewport query from 5ms to 50ms, or the GPU render from 1ms to 16ms. None of these are caught by the v3.x test suite. The v4.0 regression suite must be half correctness tests and half performance benchmarks.**

### What Is Broken

**"pytest --snapshot-update overwrites snapshots"** — this is the standard snapshot testing model but it is dangerous for a deterministic pipeline. If a dependency upgrade changes sklearn's KMeans output (which happens across minor versions), `pytest --snapshot-update` would silently accept the new output. The snapshot test must include a hash of the Python/Rust dependency versions in the snapshot metadata, so unintentional dependency upgrades are flagged.

**"`pytest -m 'not slow'` separates benchmark tests from CI"** — this means performance regressions are only caught in pre-release runs. For a v4.0 architecture where performance is the primary value proposition, every PR must run at least the FilterEngine, RangeIndex, and DensityHistogram benchmarks. They take <1 second each.

**"Smoke test script tags the release"** — the smoke test should validate but not tag. Tagging should be a separate step after the smoke test output is reviewed. The script correctly prints the tag commands rather than running them — this is the right design, but it must be made explicit.

**No Rust benchmark suite.** The v3.x spec has no `cargo bench` benchmarks. All Rust performance targets are stated in task specs but never enforced by a CI gate. `cargo criterion` benchmarks must be added and their results committed so regressions are detected.

**No WebGPU render timing validation.** The spec claims "GPU render <1ms" but there is no test that measures this. GPU timing in WebGPU is available via `GPUQuerySet` with timestamp queries. This must be measured in the Tauri headless test mode.

---

## v4.0 Rewrite

### Performance Regression Suite

Every PR must pass these benchmarks. They run in <30 seconds total on M4 Max.

#### Rust Benchmarks (`cargo criterion`)

```rust
// palimpsest-core/benches/filter_bench.rs

use criterion::{black_box, criterion_group, criterion_main, Criterion};
use palimpsest_core::filter::FilterEngine;
use palimpsest_core::annotation::mock_packed_annotations;

fn bench_filter_engine(c: &mut Criterion) {
    let annotations = mock_packed_annotations(18_760);
    let engine = FilterEngine::new();

    c.bench_function("filter_18760_annotations", |b| {
        b.iter(|| {
            let result = engine.filter(
                black_box(&annotations),
                black_box(0b0001_1111u64),  // 5 tracks visible
                black_box(5000u16),          // 0.5 min confidence
            );
            black_box(result)
        })
    });
}

fn bench_range_index_query(c: &mut Criterion) {
    // Build interval tree with 18,760 annotations over a 130K-char document
    let index = mock_range_index(18_760, 130_000);

    c.bench_function("range_index_query_7k_chars", |b| {
        b.iter(|| {
            // Typical viewport: 7,000 characters
            black_box(index.query(black_box(50_000), black_box(57_000)))
        })
    });
}

fn bench_density_histogram(c: &mut Criterion) {
    let annotations = mock_packed_annotations(18_760);
    let boundaries: Vec<u32> = (0..1832).map(|i| i * 71).collect(); // ~71 chars per para

    c.bench_function("density_histogram_1832_paragraphs", |b| {
        b.iter(|| {
            black_box(DensityHistogram::compute(
                black_box(&annotations.iter().collect::<Vec<_>>()),
                black_box(1832),
                black_box(5),
                black_box(&boundaries),
            ))
        })
    });
}

fn bench_cross_similarity(c: &mut Criterion) {
    // Smaller dim (64) for CI speed — actual is 2560
    let n_a = 100; let n_b = 120; let dim = 64;
    let a: Vec<f32> = (0..n_a * dim).map(|i| i as f32 / 1000.0).collect();
    let b: Vec<f32> = (0..n_b * dim).map(|i| i as f32 / 1000.0).collect();

    c.bench_function("cross_similarity_100x120_dim64", |b| {
        b.iter(|| {
            black_box(CrossSimilarityEngine::compute(
                black_box(&a), black_box(n_a),
                black_box(&b), black_box(n_b),
                black_box(dim),
            ))
        })
    });
}

fn bench_self_similarity(c: &mut Criterion) {
    let n = 200; let dim = 64;
    let embeddings: Vec<f32> = (0..n * dim).map(|i| i as f32 / 1000.0).collect();

    c.bench_function("self_similarity_200x64", |b| {
        b.iter(|| {
            black_box(SelfSimilarityEngine::compute(black_box(&embeddings), black_box(n), black_box(dim)))
        })
    });
}

criterion_group!(
    benches,
    bench_filter_engine,
    bench_range_index_query,
    bench_density_histogram,
    bench_cross_similarity,
    bench_self_similarity,
);
criterion_main!(benches);
```

#### CI Performance Gates (Rust)

```toml
# palimpsest-core/Cargo.toml
[profile.bench]
opt-level = 3
lto = true  # Link-time optimization for accurate benchmark results
```

Performance gates are enforced by comparing benchmark output to stored baselines:

```bash
# scripts/perf-regression-gate.sh

#!/usr/bin/env bash
# Run criterion benchmarks and fail if any result regresses by >20%
set -e

BASELINE_DIR="benches/baselines"

cargo criterion --message-format json 2>/dev/null | python3 - <<'EOF'
import json, sys

THRESHOLDS = {
    "filter_18760_annotations": 2_000_000,   # <2ms in ns
    "range_index_query_7k_chars": 1_000_000,  # <1ms in ns
    "density_histogram_1832_paragraphs": 5_000_000,  # <5ms in ns
}

results = {}
for line in sys.stdin:
    try:
        obj = json.loads(line)
        if obj.get("reason") == "benchmark-complete":
            name = obj["id"]
            mean_ns = obj["mean"]["estimate"]
            results[name] = mean_ns
    except:
        pass

failures = []
for bench, threshold_ns in THRESHOLDS.items():
    actual = results.get(bench, 0)
    if actual > threshold_ns:
        failures.append(f"FAIL: {bench}: {actual/1e6:.2f}ms (threshold {threshold_ns/1e6:.2f}ms)")
    else:
        print(f"PASS: {bench}: {actual/1e6:.3f}ms")

if failures:
    for f in failures:
        print(f, file=sys.stderr)
    sys.exit(1)
EOF
```

This script runs in <15 seconds (criterion is fast for small benchmarks). It fails the PR if any benchmark exceeds its threshold.

### Correctness Regression Tests

The snapshot testing approach from v3.x is preserved with two additions:

1. **Dependency hash in snapshot metadata**: Each snapshot includes `"python_version"`, `"spacy_version"`, `"sklearn_version"` so unintentional upgrades are detected.

2. **Rust output checksums**: Rust-computed signal binaries (self_similarity.bin, rqa.bin) have their SHA-256 stored in snapshot metadata. If the checksum changes without a deliberate `pytest --snapshot-update`, the test fails.

```python
# core/tests/test_regression.py (extensions)

import hashlib
import subprocess

def get_dependency_versions() -> dict[str, str]:
    """Returns a dict of critical dependency versions for snapshot metadata."""
    import sklearn, spacy
    return {
        "python": sys.version.split()[0],
        "spacy": spacy.__version__,
        "sklearn": sklearn.__version__,
    }

def sha256_of_file(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()

@pytest.fixture(scope="module")
def dependency_versions():
    return get_dependency_versions()

def test_signal_binary_checksum(pp_ch1_analyzed, snapshot_dir):
    """Signal binary checksums match stored snapshots."""
    for signal in ["self_similarity", "rqa", "narrative_arc"]:
        bin_path = pp_ch1_analyzed / "signals" / f"{signal}.bin"
        if not bin_path.exists():
            continue
        live_checksum = sha256_of_file(bin_path)
        snap_checksum_file = snapshot_dir / "signals" / f"{signal}.sha256"
        if not snap_checksum_file.exists():
            pytest.skip(f"No snapshot checksum for {signal}.bin")
        expected = snap_checksum_file.read_text().strip()
        assert live_checksum == expected, (
            f"{signal}.bin checksum mismatch.\n"
            f"  Expected: {expected}\n"
            f"  Actual:   {live_checksum}\n"
            f"  Run: pytest --snapshot-update to accept new output"
        )

def test_snapshot_dependency_versions_match(dependency_versions, snapshot_dir):
    """Snapshot was generated with the same Python and library versions."""
    snap_meta_file = snapshot_dir / "snapshot_metadata.json"
    if not snap_meta_file.exists():
        pytest.skip("No snapshot metadata")
    snap_meta = json.loads(snap_meta_file.read_text())
    for key, value in dependency_versions.items():
        if snap_meta.get(key) and snap_meta[key] != value:
            pytest.xfail(
                f"Snapshot was generated with {key}={snap_meta[key]}, "
                f"running with {key}={value}. "
                "Run pytest --snapshot-update if the dependency upgrade was intentional."
            )
```

### Full Exit Smoke Test Script (v4.0)

```bash
#!/usr/bin/env bash
# Phase 1 Exit Smoke Test — v4.0 Tauri + Rust + WebGPU
# Usage: bash scripts/phase1-smoke-test.sh [workspace-dir] [fixture-txt]
set -e

WORKSPACE="${1:-/tmp/palimpsest-p1-smoke}"
FIXTURE="${2:-fixtures/pride-prejudice-full.txt}"
FAIL_COUNT=0

pass() { echo "  PASS: $1"; }
fail() { echo "  FAIL: $1" >&2; FAIL_COUNT=$((FAIL_COUNT + 1)); }
gate() {
  local val="$1" threshold="$2" label="$3"
  if python3 -c "import sys; sys.exit(0 if float('$val') < float('$threshold') else 1)" 2>/dev/null; then
    pass "$label: ${val} < ${threshold}"
  else
    fail "$label: ${val} >= ${threshold} (PERFORMANCE GATE FAILURE)"
  fi
}

echo "=== Phase 1 Exit Smoke Test (v4.0) ==="
echo "Workspace: $WORKSPACE"
echo ""

# ---- STEP 1: Rust benchmark gates ----
echo "[1/10] Rust performance benchmarks..."
bash scripts/perf-regression-gate.sh && pass "All Rust benchmarks within thresholds" || fail "Rust benchmark regression detected"

# ---- STEP 2: Build ----
echo "[2/10] Tauri build..."
cargo tauri build --release 2>&1 | tail -3
pass "Tauri build succeeded"

# ---- STEP 3: Ingest + Analyze ----
echo "[3/10] Ingest + Analyze..."
mkdir -p "$WORKSPACE"
palimpsest ingest "$FIXTURE" --output-dir "$WORKSPACE"
N=$(python3 -c "import json; m=json.load(open('$WORKSPACE/pride-and-prejudice/metadata.json')); print(m['paragraph_count'])")
echo "  Paragraph count: $N"

ANALYZE_ELAPSED=$(python3 -c "
import time, subprocess
start = time.monotonic()
subprocess.run(['palimpsest', 'analyze', '$WORKSPACE/pride-and-prejudice/'], check=True)
print(f'{(time.monotonic() - start):.2f}')
")
gate "$ANALYZE_ELAPSED" 3.0 "Analysis time (target <3s on M4 Max)"

# ---- STEP 4: Signal file verification ----
echo "[4/10] Signal file sizes..."

SS_EXPECTED=$((N * N * 4))
SS_ACTUAL=$(wc -c < "$WORKSPACE/pride-and-prejudice/signals/self_similarity.bin" | tr -d ' ')
[ "$SS_ACTUAL" -eq "$SS_EXPECTED" ] && pass "self_similarity.bin size" || fail "self_similarity.bin: expected $SS_EXPECTED bytes, got $SS_ACTUAL"

ARC_ACTUAL=$(wc -c < "$WORKSPACE/pride-and-prejudice/signals/narrative_arc.bin" | tr -d ' ')
[ "$ARC_ACTUAL" -eq "60" ] && pass "narrative_arc.bin 60 bytes" || fail "narrative_arc.bin wrong size ($ARC_ACTUAL)"

W=$(python3 -c "import json; m=json.load(open('$WORKSPACE/pride-and-prejudice/signals/rqa.json')); print(m['metadata']['n_windows'])")
RQA_EXPECTED=$((W * 3 * 4))
RQA_ACTUAL=$(wc -c < "$WORKSPACE/pride-and-prejudice/signals/rqa.bin" | tr -d ' ')
[ "$RQA_ACTUAL" -eq "$RQA_EXPECTED" ] && pass "rqa.bin size matches manifest" || fail "rqa.bin size mismatch"

ALPHA_LEN=$(python3 -c "import json; m=json.load(open('$WORKSPACE/pride-and-prejudice/signals/alphabet.json')); print(len(m['sequence']))")
[ "$ALPHA_LEN" -eq "$N" ] && pass "alphabet sequence length == paragraph_count" || fail "alphabet length mismatch ($ALPHA_LEN vs $N)"
PLACEHOLDER=$(python3 -c "import json; m=json.load(open('$WORKSPACE/pride-and-prejudice/signals/alphabet.json')); print(m['metadata']['phase1_placeholder'])")
[ "$PLACEHOLDER" = "True" ] && pass "alphabet.json phase1_placeholder=true" || fail "phase1_placeholder missing"

# ---- STEP 5: Rust benchmark-load (project load time) ----
echo "[5/10] Project load time..."
LOAD_MS=$(palimpsest-core benchmark-load "$WORKSPACE/pride-and-prejudice/" 2>/dev/null | grep "elapsed_ms" | awk '{print $2}')
gate "$LOAD_MS" 100 "Project load (target <100ms)"

# ---- STEP 6: Rust filter benchmark ----
echo "[6/10] FilterEngine benchmark..."
FILTER_US=$(palimpsest-core benchmark-filter "$WORKSPACE/pride-and-prejudice/" 2>/dev/null | grep "elapsed_us" | awk '{print $2}')
gate "$FILTER_US" 2000 "FilterEngine (target <2ms)"

# ---- STEP 7: Determinism ----
echo "[7/10] Determinism..."
cp "$WORKSPACE/pride-and-prejudice/signals/self_similarity.bin" /tmp/ss_run1.bin
cp "$WORKSPACE/pride-and-prejudice/signals/narrative_arc.bin" /tmp/arc_run1.bin
palimpsest analyze "$WORKSPACE/pride-and-prejudice/" >/dev/null 2>&1
cmp -s "$WORKSPACE/pride-and-prejudice/signals/self_similarity.bin" /tmp/ss_run1.bin && pass "self_similarity.bin byte-identical across runs" || fail "self_similarity.bin not deterministic"
cmp -s "$WORKSPACE/pride-and-prejudice/signals/narrative_arc.bin" /tmp/arc_run1.bin && pass "narrative_arc.bin byte-identical across runs" || fail "narrative_arc.bin not deterministic"

# ---- STEP 8: Export ----
echo "[8/10] Export..."
EXPORT_ELAPSED=$(python3 -c "
import time, subprocess
start = time.monotonic()
for fmt in ['w3c', 'paf', 'csv']:
    subprocess.run(['palimpsest', 'export', '$WORKSPACE/pride-and-prejudice/', '--format', fmt], check=True)
print(f'{(time.monotonic() - start):.2f}')
")
gate "$EXPORT_ELAPSED" 1.5 "All-format export time (target <1.5s)"

python3 -c "
import json
from pathlib import Path
for f in Path('$WORKSPACE/pride-and-prejudice/exports/w3c').glob('*.collection.json'):
    c = json.load(open(f))
    assert c['type'] == 'AnnotationCollection', f'{f.name}: wrong type'
    assert len(c['items']) == c['total'], f'{f.name}: total mismatch'
print('  PASS: W3C export validates')
"

# ---- STEP 9: Regression tests ----
echo "[9/10] Regression tests..."
cd core && pytest tests/test_regression.py -q --tb=short 2>&1 | tail -10
pass "Regression test suite"

# ---- STEP 10: Semantic search benchmark ----
echo "[10/10] Semantic search timing..."
if [ -n "$PALIMPSEST_TEST_OLLAMA" ]; then
    SEARCH_MS=$(palimpsest-core benchmark-search "$WORKSPACE/pride-and-prejudice/" "marriage money" 2>/dev/null | grep "elapsed_ms" | awk '{print $2}')
    gate "$SEARCH_MS" 350 "Semantic search (target <350ms)"
else
    echo "  SKIP: PALIMPSEST_TEST_OLLAMA not set (requires Ollama)"
fi

# ---- Summary ----
echo ""
echo "==========================="
if [ "$FAIL_COUNT" -eq 0 ]; then
    echo "=== Phase 1 Smoke Test PASSED ==="
    echo ""
    echo "Ready to tag. Run:"
    echo "  git tag v0.5.0 -m 'Milestone 1.4: Full browser + export + cross-text dotplot'"
    echo "  git tag v1.0.0 -m 'Phase 1 complete: Tauri+Rust+WebGPU walking skeleton'"
else
    echo "=== Phase 1 Smoke Test FAILED ($FAIL_COUNT failures) ==="
    echo "Fix all failures before tagging."
    exit 1
fi
```

### CI Configuration

The perf regression gate runs on every PR:

```yaml
# .github/workflows/ci.yml (additions)

performance_gates:
  runs-on: self-hosted-m4  # Must run on M4 Mac for NEON benchmarks
  steps:
    - uses: actions/checkout@v4
    - name: Run Rust benchmarks
      run: bash scripts/perf-regression-gate.sh
    - name: Run Python correctness tests
      run: cd core && pytest tests/test_regression.py -q -m "not slow"
    - name: TypeScript type check
      run: cd browser && npx tsc --strict --noEmit
```

The `self-hosted-m4` runner is required for NEON SIMD benchmarks — they would produce incorrect numbers on x86 GitHub-hosted runners (no ARM NEON) and on ARM Rosetta emulation.

### Performance Gates Summary

| Test | Threshold | Failure consequence |
|------|-----------|-------------------|
| FilterEngine 18,760 annotations | <2ms | Block PR |
| RangeIndex query 7K chars | <1ms | Block PR |
| DensityHistogram 1,832 paragraphs | <5ms | Block PR |
| Self-similarity 200×64 (proxy) | <100ms | Block PR |
| Cross-similarity 100×120×64 (proxy) | <10ms | Block PR |
| Project load (<100ms) | smoke test only | Block release |
| Analysis time (<3s) | smoke test only | Block release |
| Export time (<1.5s) | smoke test only | Block release |
| Semantic search (<350ms) | smoke test (Ollama required) | Block release |

Lower-dim proxies (dim=64 instead of dim=2560) are used in CI to keep benchmark run time under 30 seconds. The smoke test on actual hardware validates the full-dimension performance.

### Acceptance Criteria (v4.0)

- `bash scripts/perf-regression-gate.sh` exits 0 on M4 Mac hardware
- `pytest tests/test_regression.py -q` passes 0 failures (not counting skipped)
- `pytest tests/test_pipeline.py::test_determinism_signal_binaries` passes (Rust binaries byte-identical)
- `bash scripts/phase1-smoke-test.sh` exits 0 in a clean environment
- `v0.5.0` and `v1.0.0` tags applied only after smoke test passes
- `cargo criterion` benchmark history committed (`.criterion/` directory) for regression tracking
- `scripts/perf-regression-gate.sh` integrated in CI (runs on M4 self-hosted runner)

---

## Original Content (Reference)

**Milestone**: 1.4 — Full Text Browser + Cross-Text Dotplot + Export
**Estimated effort**: 8 hours

### Context (original)

Regression test suite locks in current correct output so future changes (Phase 2 track additions, dependency upgrades, refactoring) cannot silently break existing behavior. Snapshot approach: store expected JSONL, compare on every test run. Exit smoke test is the sequential command sequence from §10, runnable end-to-end in clean virtualenv.

### Design Decisions (original)

- **Snapshots stored in `fixtures/expected/`, not auto-generated**: Deliberate regeneration prevents silent acceptance of wrong output.
- **Compare annotation bodies, not raw JSON strings**: Robust to field reordering.
- **Signal binaries compared byte-identical**: Ensures random seed policy is working.
- **`pytest -m "not slow"` separates benchmark tests**: Full P&P benchmark ~30s, skip locally.
- **Smoke test script prints tag commands, not runs them**: Human operator decides when Phase 1 is done.

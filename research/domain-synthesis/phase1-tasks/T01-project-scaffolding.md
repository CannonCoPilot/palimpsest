# T01: Project Scaffolding + Code Quality Tooling

**Milestone**: 1.1 — Ingest + Normalize + First Track + Minimal Browser
**Estimated effort**: 4 hours (original) → 6 hours (v4.0: Tauri workspace adds complexity)
**Dependencies**: None
**Outputs**: Full monorepo skeleton, all tooling configured, ADR-001 and ADR-005 written, no application code

---

## v4.0 Critical Review

**From a Senior Lead System Architect perspective, the original T01 scaffold is dead on arrival for the performance requirements we now have.**

The original structure scaffolds a Python monolith with a Vite SPA bolted on the side. This makes several assumptions that v4.0 shatters:

1. **The `browser/` directory is a standalone Vite project.** This is wrong. In v4.0, the browser is a Tauri webview — it cannot be served independently with `vite dev` against a FastAPI backend, because the data access layer is Tauri IPC commands, not HTTP. The Vite proxy configuration (`'/api': 'http://localhost:8080'`) is meaningless: there is no HTTP server to proxy to.

2. **`core/` is a Python-only package.** This is wrong. The core engine is now a Rust crate (`palimpsest-core`). Python remains for NLP extractors only. The `core/pyproject.toml` cannot be the root of the project — the root is a Cargo workspace.

3. **The dependency list targets FastAPI + uvicorn as primary serving infrastructure.** Both are now eliminated from the local use case. FastAPI is retained only for an optional remote mode. `uvicorn` is not in the critical path.

4. **ADR-005 (JBrowse 2 patterns) maps to TypeScript adapters and a TrackRegistry.** This is preserved, but the data flow described in that ADR (browser fetches JSONL over HTTP → JSON.parse → JS heap) is exactly what v4.0 eliminates. ADR-005 needs a new section documenting the Tauri command layer as the data access boundary.

5. **Pre-commit hooks check only Python and TypeScript.** Rust code has its own toolchain (clippy, rustfmt) that must be integrated. A pre-commit hook that only checks `core/palimpsest/` misses half the codebase.

6. **No performance test infrastructure is scaffolded.** For a platform with a 2ms track-toggle target and a <100ms project load target, performance benchmarks are not optional. They must be scaffolded from day one alongside unit tests, not bolted on later.

**What must change:**
- Root becomes a Cargo workspace, not just a Python package
- `browser/` becomes `src-tauri/` (Tauri convention) + a `ui/` directory for the React frontend
- Rust toolchain configuration (clippy, rustfmt, cargo-nextest) added to pre-commit
- Performance benchmark infrastructure (criterion.rs for Rust, bench markers in pytest for Python extractors) scaffolded from the start
- ADR-001 updated to note that JSONL is the storage format but annotations never enter the JS heap — Rust parses them
- ADR-005 updated to include Tauri command layer as the data access pattern

---

## v4.0 Rewrite

### Architecture

```
palimpsest/                        ← Cargo workspace root
├── Cargo.toml                     ← workspace manifest (members: ["core", "src-tauri"])
├── core/                          ← palimpsest-core Rust crate (the data engine)
│   ├── Cargo.toml
│   ├── src/
│   │   ├── lib.rs
│   │   ├── annotation/
│   │   │   ├── mod.rs
│   │   │   ├── packed.rs          ← PackedAnnotation struct (16 bytes)
│   │   │   ├── arena.rs           ← arena allocator + body store
│   │   │   └── jsonl.rs           ← JSONL parser: W3C → PackedAnnotation
│   │   ├── index/
│   │   │   ├── mod.rs
│   │   │   └── range_index.rs     ← interval tree (RangeIndex)
│   │   ├── filter/
│   │   │   ├── mod.rs
│   │   │   └── engine.rs          ← FilterEngine (SIMD/NEON)
│   │   ├── project/
│   │   │   ├── mod.rs
│   │   │   └── manager.rs         ← ProjectManager (multi-doc)
│   │   └── density/
│   │       └── histogram.rs       ← DensityHistogram
│   ├── benches/
│   │   ├── filter_bench.rs        ← criterion benchmark: filter 18K annotations
│   │   ├── load_bench.rs          ← criterion benchmark: JSONL → arena load time
│   │   └── range_query_bench.rs   ← criterion benchmark: interval tree query
│   └── tests/
│       └── integration/
│           └── annotation_round_trip.rs
├── src-tauri/                     ← Tauri application shell
│   ├── Cargo.toml
│   ├── tauri.conf.json
│   ├── src/
│   │   ├── main.rs
│   │   └── commands/
│   │       ├── mod.rs
│   │       ├── project.rs         ← load_project, list_projects Tauri commands
│   │       ├── viewport.rs        ← query_viewport Tauri command
│   │       ├── filter.rs          ← update_filter Tauri command
│   │       └── histogram.rs       ← get_histogram Tauri command
├── ui/                            ← React frontend (Tauri webview)
│   ├── src/
│   │   ├── App.tsx
│   │   ├── components/
│   │   ├── stores/
│   │   ├── adapters/
│   │   │   └── tauri.ts           ← Tauri invoke wrappers (replaces HTTP fetch)
│   │   ├── registry/
│   │   └── utils/
│   ├── index.html
│   ├── vite.config.ts
│   ├── tsconfig.json
│   └── package.json
├── python/                        ← NLP extractors (managed subprocess, not HTTP server)
│   ├── palimpsest/
│   │   ├── __init__.py
│   │   ├── extractors/            ← TrackExtractor implementations (unchanged protocol)
│   │   └── cli_extract.py         ← thin CLI called by Rust pipeline manager
│   ├── tests/
│   │   ├── fixtures/
│   │   │   └── expected/
│   │   └── conftest.py
│   └── pyproject.toml
├── fixtures/
│   └── expected/
├── specs/
│   ├── annotation-model.md
│   ├── LFO.md
│   ├── signals.md
│   └── PAF-export.md
├── docs/
│   └── architecture/
│       ├── ADR-001-annotation-format.md
│       └── ADR-005-jbrowse2-patterns.md
├── .pre-commit-config.yaml
├── .gitignore
└── .gitmodules (empty)
```

### Rust Workspace Configuration

**`Cargo.toml` (workspace root)**:
```toml
[workspace]
members = ["core", "src-tauri"]
resolver = "2"

[workspace.dependencies]
tokio = { version = "1", features = ["full"] }
serde = { version = "1", features = ["derive"] }
serde_json = "1"
memmap2 = "0.9"
intervaltree = "0.2"
bitvec = "1"
rayon = "1"
thiserror = "1"
anyhow = "1"

[profile.release]
opt-level = 3
lto = true
codegen-units = 1
```

**`core/Cargo.toml`**:
```toml
[package]
name = "palimpsest-core"
version = "0.1.0"
edition = "2021"

[dependencies]
serde = { workspace = true }
serde_json = { workspace = true }
memmap2 = { workspace = true }
intervaltree = { workspace = true }
bitvec = { workspace = true }
rayon = { workspace = true }
thiserror = { workspace = true }
anyhow = { workspace = true }

[dev-dependencies]
criterion = { version = "0.5", features = ["html_reports"] }
tempfile = "3"

[[bench]]
name = "filter_bench"
harness = false

[[bench]]
name = "load_bench"
harness = false

[[bench]]
name = "range_query_bench"
harness = false
```

**`core/src/lib.rs`** (stub):
```rust
//! palimpsest-core: High-performance data engine for literary annotation analysis.
//!
//! Architecture:
//! - PackedAnnotation: 16-byte struct (start u32, end u32, confidence u16, track_id u8,
//!   evidence_level u8, body_offset u32)
//! - AnnotationArena: bump allocator for packed annotations + body strings
//! - RangeIndex: augmented interval tree for O(log n + k) viewport queries
//! - FilterEngine: SIMD-accelerated track mask + confidence threshold filtering
//! - DensityHistogram: pre-computed bin counts for GPU upload
//! - ProjectManager: loads multiple projects, manages mmap'd signal files

pub mod annotation;
pub mod density;
pub mod filter;
pub mod index;
pub mod project;
```

### Performance Benchmarks (scaffold)

**`core/benches/filter_bench.rs`**:
```rust
use criterion::{criterion_group, criterion_main, BenchmarkId, Criterion, Throughput};
use palimpsest_core::annotation::{AnnotationArena, PackedAnnotation};
use palimpsest_core::filter::FilterEngine;

fn bench_filter(c: &mut Criterion) {
    let mut group = c.benchmark_group("filter");

    for count in [1_000u32, 5_000, 18_760, 50_000, 100_000] {
        group.throughput(Throughput::Elements(count as u64));

        let arena = AnnotationArena::mock(count);
        let engine = FilterEngine::new();
        let track_mask: u64 = 0b1111_1111; // all tracks visible
        let min_confidence: u16 = 3000;    // 0.3 fixed-point

        group.bench_with_input(
            BenchmarkId::from_parameter(count),
            &count,
            |b, _| {
                b.iter(|| {
                    engine.filter(arena.slice(), track_mask, min_confidence)
                });
            },
        );
    }

    group.finish();
}

criterion_group!(benches, bench_filter);
criterion_main!(benches);
```

**Performance targets that benchmarks must validate:**
- `filter(18_760 annotations, all tracks, 0.3 threshold)` → **< 5μs** on M4 Max
- `load_project(P&P full novel JSONL)` → **< 100ms** wall clock
- `range_query(7000-char viewport)` on 18,760 annotations → **< 1ms**

CI fails if benchmarks regress beyond 2× these targets.

### Tauri Configuration

**`src-tauri/tauri.conf.json`** (key sections):
```json
{
  "build": {
    "beforeBuildCommand": "npm run build",
    "beforeDevCommand": "npm run dev",
    "devUrl": "http://localhost:5173",
    "frontendDist": "../ui/dist"
  },
  "app": {
    "windows": [{
      "title": "Palimpsest",
      "width": 1400,
      "height": 900,
      "minWidth": 1024,
      "minHeight": 600
    }]
  },
  "identifier": "dev.palimpsest.app"
}
```

**`src-tauri/src/main.rs`** (stub):
```rust
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod commands;

fn main() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![
            commands::project::load_project,
            commands::project::list_projects,
            commands::viewport::query_viewport,
            commands::filter::update_filter,
            commands::histogram::get_histogram,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
```

### Python Package (NLP extractors only)

**`python/pyproject.toml`**:
```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "palimpsest-extractors"
version = "0.1.0"
requires-python = ">=3.12"

[project.dependencies]
spacy = ">=3.7"
vaderSentiment = ">=3.3"
scikit-learn = ">=1.4"
numpy = ">=1.26"
scipy = ">=1.12"
pymupdf = ">=1.24"
ebooklib = ">=0.18"
beautifulsoup4 = ">=4.12"
click = ">=8.1"
rich = ">=13"

[project.optional-dependencies]
booknlp = ["booknlp>=2.0"]
dev = ["pytest>=8", "pytest-cov", "pytest-benchmark", "ruff", "mypy", "pre-commit"]

[project.scripts]
# Not a user-facing CLI — called by Rust pipeline manager as subprocess
palimpsest-extract = "palimpsest.cli_extract:main"

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "N", "ANN"]
ignore = ["ANN101", "ANN102"]

[tool.mypy]
strict = true
python_version = "3.12"

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
addopts = "--strict-markers -q"
```

Note: `fastapi` and `uvicorn` are **removed** from the default dependency list. They may be added as an optional `[remote]` extra for future network-accessible deployment mode only.

### Pre-commit Configuration

**`.pre-commit-config.yaml`** (monorepo root):
```yaml
repos:
  # Rust: format
  - repo: local
    hooks:
      - id: rustfmt
        name: rustfmt
        language: system
        entry: cargo fmt --all --
        pass_filenames: false
        files: \.rs$

  # Rust: lint
      - id: clippy
        name: clippy
        language: system
        entry: cargo clippy --all-targets --all-features -- -D warnings
        pass_filenames: false
        files: \.rs$

  # Python: ruff format + lint
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.4.0
    hooks:
      - id: ruff
        args: [--fix]
        files: ^python/
      - id: ruff-format
        files: ^python/

  # Python: mypy
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.10.0
    hooks:
      - id: mypy
        files: ^python/palimpsest/
        additional_dependencies: [types-all]

  # TypeScript: ESLint + Prettier
  - repo: local
    hooks:
      - id: eslint
        name: eslint
        language: system
        entry: bash -c 'cd ui && npx eslint src --ext .ts,.tsx'
        files: ^ui/src/

      - id: prettier
        name: prettier
        language: system
        entry: bash -c 'cd ui && npx prettier --check src'
        files: ^ui/src/
```

### Frontend (ui/) Setup

Scaffold with Tauri's recommended React+TypeScript template:
```bash
npm create tauri-app@latest palimpsest -- --template react-ts
```

Install runtime dependencies:
```bash
cd ui
npm install zustand@^4 @tauri-apps/api@^2
npm install -D vitest @vitest/ui @playwright/test eslint@^9 \
  @typescript-eslint/eslint-plugin@^7 @typescript-eslint/parser@^7 \
  prettier@^3 lint-staged
```

**`ui/vite.config.ts`**:
```typescript
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  test: { globals: true, environment: 'jsdom' },
  // No HTTP proxy — all data access goes through Tauri invoke commands.
  // In dev mode, Tauri runs the Rust backend in-process; no separate server needed.
  clearScreen: false,
  server: {
    port: 5173,
    strictPort: true,
  },
});
```

**`ui/tsconfig.json`**:
```json
{
  "compilerOptions": {
    "strict": true,
    "target": "ES2022",
    "module": "ESNext",
    "moduleResolution": "bundler",
    "jsx": "react-jsx",
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "baseUrl": ".",
    "paths": {
      "@/*": ["./src/*"]
    }
  },
  "include": ["src"]
}
```

**`ui/src/App.tsx`** (stub):
```typescript
export default function App(): JSX.Element {
  return <div id="app-root">Palimpsest — loading...</div>;
}
```

### ADR Updates

**ADR-001** must add: "W3C JSONL is the persistent storage format. At runtime, JSONL is parsed by the Rust core engine into `PackedAnnotation` arena. Annotation data **never enters the JavaScript heap**. The browser accesses annotation data exclusively through typed Tauri commands that return pre-filtered, serialized viewport slices."

**ADR-005** must add: "The Tauri command layer is the data access boundary. `query_viewport(start, end)` replaces the JBrowse 2 concept of a `fetch()` call to an HTTP track endpoint. The Rust `RangeIndex` plays the role of the JBrowse 2 track adapter's data store. Browser components invoke commands; they do not own annotation arrays."

### Verification Targets

After T01, these must all pass:

```bash
# Rust workspace builds
cargo build --all

# Rust tests (using nextest for parallel execution)
cargo nextest run --all

# Criterion benchmarks run (no regression yet, just ensure they compile + run)
cargo bench --no-run

# Python package installs
cd python && pip install -e ".[dev]"
cd python && pytest  # 0 tests, exit 0

# TypeScript compiles
cd ui && npx tsc --noEmit

# ESLint passes
cd ui && npx eslint src --ext .ts,.tsx

# Pre-commit passes on all files
pre-commit run --all-files
```

## Acceptance Criteria

- `cargo build --all` exits 0 from workspace root
- `cargo clippy --all-targets -- -D warnings` exits 0
- `cargo nextest run --all` collects 0 tests and exits 0
- `cargo bench --no-run` exits 0 (benchmarks compile)
- `cd python && pip install -e ".[dev]"` succeeds
- `cd python && pytest` collects 0 tests and exits 0
- `mypy --strict python/palimpsest/` exits 0 on stub `__init__.py`
- `cd ui && npx tsc --noEmit` exits 0
- `cd ui && npx eslint src --ext .ts,.tsx` exits 0
- `pre-commit run --all-files` exits 0
- `docs/architecture/ADR-001-annotation-format.md` references Rust arena loading and absence of JS heap annotation storage
- `docs/architecture/ADR-005-jbrowse2-patterns.md` maps Tauri command layer to JBrowse 2 adapter pattern
- No application code in any source file — only module stubs
- `fastapi` and `uvicorn` are NOT in the default `python/pyproject.toml` dependencies

## Tests to Write

None in T01 — infrastructure only. First tests are in T03 (Rust annotation structs) and T05 (Python extractors).

---

## Original Content (v3.0, preserved for reference)

### Context

This task initializes the entire Palimpsest monorepo structure before any application code is written. Getting tooling right on Day 1 prevents accumulated technical debt: ruff + mypy enforce type safety and style from the first commit, and pre-commit hooks ensure no commit ever bypasses them. The monorepo layout (§1) must be established here because every subsequent task assumes its existence.

### Prerequisites

None. This is the first task in the project.

### Deliverables (v3.0)

```
palimpsest/
├── core/
│   ├── palimpsest/
│   │   └── __init__.py
│   ├── tests/
│   │   ├── fixtures/
│   │   │   └── expected/
│   │   └── .gitkeep
│   ├── pyproject.toml
│   └── README.md
├── browser/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── components/
│   │   ├── stores/
│   │   ├── adapters/
│   │   ├── registry/
│   │   └── utils/
│   ├── index.html
│   ├── vite.config.ts
│   ├── tsconfig.json
│   └── package.json
...
```

[... full original content omitted for brevity but preserved in git history ...]

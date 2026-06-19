# Critical Review: Phase 1 Plan — Design Gaps, Architecture Risks, and Protocol Gaps

**Date**: 2026-06-06
**Scope**: Evaluates document 13 for implementation feasibility, architectural soundness, forward compatibility with Phases 2-8, and whether it establishes durable development protocols.

---

## 1. Architecture and Design Gaps

### 1.1 No Track Extension Protocol — The Base/X Boundary Is Declared But Not Enforced

The roadmap's central architectural principle is "X emerges from Base; never build X into Base." But the Phase 1 plan hardcodes all 10 tracks into the source tree (`core/palimpsest/tracks/*.py`). There is no plugin system, no track registry, no dynamic discovery mechanism. When Phase 2 arrives and X needs to add a custom track, the developer will have to:
- Add a new `.py` file in `tracks/`
- Update the CLI to know about it
- Update the DAG orchestrator to include it
- Update the browser's track list

That's 4 touch points across 2 codebases. This is not "X emerges from Base" — this is "X requires editing Base code in 4 places."

**What's missing**: A `TrackRegistry` — a manifest or discovery system that allows new tracks to be registered without modifying existing code. In genomics, JBrowse 2 uses a plugin system where a new track type is registered by calling `pluginManager.addTrackType()`. Palimpsest needs the equivalent.

**Fix for Phase 1**: Even if the full plugin system isn't built in Phase 1, establish the pattern now:
- Each track extractor implements a `TrackExtractor` interface with methods: `name()`, `depends_on()`, `extract(project) → PAF | Signal`, `lfo_types() → List[str]`
- A `registry.py` auto-discovers all classes implementing `TrackExtractor` in the `tracks/` package (Python's `__subclasses__()` or entry points)
- The CLI and DAG orchestrator iterate over the registry, not a hardcoded list
- Phase 2's X tracks register via the same mechanism but from `x-config/detectors/` instead of `tracks/`

This is ~50 lines of code but establishes the extension protocol that the entire project depends on.

### 1.2 No Browser Extension Protocol Either

The same problem exists in the browser. TrackPanel, OverviewBar, and TextLinearView all need to know what tracks exist and how to render them. If these are hardcoded React components, Phase 2's custom tracks will require editing browser code.

**What's missing**: A `TrackRenderer` registry on the browser side. Each track type registers:
- A color scheme
- A rendering strategy for TextLinearView (highlight, underline, margin marker)
- A rendering strategy for OverviewBar (density barcode config)
- An optional dedicated view component (DotplotView for self-similarity)

**Fix**: Define a `TrackManifest` JSON schema (shipped alongside the PAF file) that tells the browser how to render a track. Base tracks ship with built-in manifests. X tracks include custom manifests in their PAF headers or in a companion `.manifest.json` file. The browser reads the manifest and selects rendering strategy dynamically.

### 1.3 The Similarity Search Endpoint Is Architecturally Misplaced

The plan puts a similarity search endpoint (`GET /api/search?query=...&k=10`) in the Phase 1 server. But:
- Phase 1 is "read-only" with static file serving
- The similarity search requires loading the sqlite-vec database and running a query
- This is a dynamic API endpoint, not a static file

This creates a hybrid server: mostly static, but with `/api/search` and `/api/summarize` as dynamic endpoints. That's fine technically, but the plan should acknowledge this is no longer "3 lines of FastAPI" — it's a real API server with at least 3 endpoints.

**Fix**: Acknowledge the API endpoints explicitly. Define a clear boundary: `/data/*` = static files (read-only, cacheable); `/api/*` = dynamic endpoints (compute on request). This boundary carries forward cleanly to Phase 2 where `/api/*` expands to include annotation CRUD.

### 1.4 npz Files Cannot Be Loaded in a Browser

The plan stores matrix data as NumPy `.npz` files and states "the browser reads the JSON manifest and fetches the `.npz` on demand." But browsers cannot parse `.npz` files natively. NumPy's compressed archive format requires Python to decompress.

**Options**:
- **Option A**: Server-side conversion. Add a `/api/signal/{name}` endpoint that reads the `.npz` and returns the matrix as a JSON array or binary Float32Array. Adds latency and server load.
- **Option B**: Store matrices as raw binary Float32 (`.bin`) with dimensions in the JSON manifest. The browser loads the binary with `fetch()` + `Float32Array(buffer)`. Zero server computation. Fast.
- **Option C**: Store matrices as Apache Arrow IPC format (`.arrow`). Readable in both Python (pyarrow) and browser (apache-arrow JS). Cross-platform, typed, compressed.

**Recommendation**: Option B for Phase 1 (simplest). The manifest already has `dimensions` — add a `dtype` field (e.g., `float32`) and store the raw binary. Revisit for Phase 5 (corpus scale) where Arrow may be worth the dependency.

### 1.5 No Concept of "Project Workspace" in the Browser

The browser receives data from one project at a time via `palimpsest serve <project-dir>`. But Milestone 1.4 introduces cross-text dotplots, which require loading data from TWO projects simultaneously. The plan says "dropdown to select second project" but doesn't explain how the browser discovers available projects, or how the server serves data from multiple project directories.

**Fix**: Either:
- `palimpsest serve <dir1> <dir2>` — serve multiple projects, exposed at `/data/project-1/` and `/data/project-2/`
- `palimpsest serve <workspace-dir>` — serve all projects under a parent directory, with a project listing at `/api/projects`

The second option is more forward-looking (Phase 5's corpus manager needs this anyway).

---

## 2. Implementation Feasibility Issues

### 2.1 Day-Level Scheduling Is Fragile

The plan assigns specific deliverables to specific days (e.g., "Day 3: Ingestion pipeline"). This precision is useful for communication but dangerous for execution. A single unexpected problem (spaCy version conflict, PDF extraction edge case, React build configuration issue) can cascade and invalidate the entire day-level schedule.

**Fix**: Keep the day-level plan as a *reference*, not a commitment. The milestones and their smoke tests are the actual commitments. Within a milestone, the developer should have freedom to reorder tasks as discovery demands. Document this as a protocol: "Day-level estimates are aspirational; milestone deadlines are binding."

### 2.2 IJ Full Text as Test Fixture Is a Copyright Problem

The plan uses "ij-full.txt" (the complete Infinite Jest) as a test fixture and benchmark target. IJ is copyrighted — it cannot be checked into a public repo, and distributing it in a test suite is a legal risk.

**Fix**: Use two test tiers:
- **Tier 1 (checked into repo)**: Public domain texts — e.g., _Pride and Prejudice_ (Project Gutenberg), a chapter of _Moby-Dick_. Used for unit tests, integration tests, regression snapshots, and benchmarks.
- **Tier 2 (local only, gitignored)**: IJ and other copyrighted texts. Used for manual validation and the Swinehart ground truth comparison. The test suite must pass using only Tier 1 texts.

This also forces the pipeline to be tested on multiple texts, not just IJ — revealing text-specific bugs earlier.

### 2.3 spaCy Model Size Matters

The plan uses `en_core_web_sm` (small model, ~12MB). But small model NER is significantly worse than `en_core_web_lg` (large, ~560MB) or `en_core_web_trf` (transformer, ~400MB). The acceptance criterion "Entity track detects 'Hal' (PER)" will likely pass with `sm` because "Hal" is a common name. But "Wardine" or "Clenette" (IJ characters) will not be detected with `sm`.

**Decision needed**: Is the Phase 1 entity track meant to be high-quality (use `lg` or `trf`) or fast (use `sm`)? The plan should state this explicitly and document the quality tradeoff.

**Recommendation**: Default to `en_core_web_lg`. The 560MB download is a one-time cost. The quality difference is substantial for literary text where character names are often unusual. Allow override via config: `palimpsest analyze --spacy-model en_core_web_sm` for users with limited disk/memory.

### 2.4 LDA Topic Model Is Non-Deterministic

sklearn's `LatentDirichletAllocation` is non-deterministic by default. The plan requires "regression test: deterministic output (same input → same PAF)." These are contradictory.

**Fix**: Set `random_state=42` (or any fixed seed) in the LDA model. Document that topic assignments are reproducible only with the same random seed and same sklearn version. Also applies to K-means in the alphabet track.

---

## 3. Forward Compatibility with Future Phases

### 3.1 PAF-Span Has No Relation Support

Phase 2 needs annotation of *relationships* — "Character A knows Character B", "Passage X foreshadows Passage Y", "This passage references Book Z." PAF-Span's column layout has no mechanism for encoding relationships between two annotations.

GFF3 handles this via the `Parent` attribute (hierarchical containment) but not via arbitrary edges. The W3C Web Annotation model handles it via multiple `hasTarget` bodies. PAF currently has neither.

**Fix**: Add to the PAF spec now (even if no Phase 1 track uses it):
- `Target` attribute (borrowed from GFF3): `Target=<docname> <start> <end>` for cross-span references
- `Relation` attribute: `Relation=<relation_type>:<target_ID>` for typed relationships between annotations

This doesn't require implementation in Phase 1 — just reserving the attribute names in the spec so that Phase 2 can use them without a breaking format change.

### 3.2 No Versioning or Provenance Protocol

The plan says "every annotation has `source` = tool name + version." But there's no protocol for:
- What version string format to use (semver? tool/version? arbitrary string?)
- How to record pipeline configuration (what parameters were used for each track run?)
- How to reproduce a specific analysis (given project + pipeline version → identical output?)

**Fix**: Define a `pipeline_run.json` file written alongside tracks on each `palimpsest analyze` invocation:
```json
{
  "run_id": "uuid",
  "timestamp": "2026-06-10T14:30:00Z",
  "palimpsest_version": "0.1.0",
  "python_version": "3.12.5",
  "spacy_model": "en_core_web_lg/3.7.4",
  "tracks_computed": ["entities", "sentiment", "lexical", "dialogue", "topics"],
  "parameters": {
    "topics.n_topics": 10,
    "topics.random_state": 42,
    "alphabet.n_clusters": 16,
    "sentiment.model": "vader"
  }
}
```

This enables reproducibility and becomes the provenance record that Phase 2's annotation transfer (TextLiftoff) needs.

### 3.3 No Metadata Schema for Texts

`metadata.json` is mentioned but never specified. What fields does it have? Is the schema validated? Can Phase 5's corpus manager query across metadata from different texts?

**Fix**: Define a minimal metadata schema:
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
  "reference_sha256": "a1b2c3d4...",
  "word_count": 122189,
  "paragraph_count": 1832,
  "section_count": 61
}
```

Phase 5's corpus manager will index these fields. Defining them now costs nothing and prevents schema migration pain later.

### 3.4 W3C Web Annotation Export Is Under-Specified

The plan includes "Export: W3C Web Annotation JSON-LD" but the converter (`w3c.py`) is not detailed:
- How does a PAF entity annotation map to a W3C annotation body?
- What `@context` is used?
- How are confidence scores represented? (W3C doesn't have a score field)
- How are multi-track exports structured? (One annotation container per track? One flat list?)

**Fix**: Sketch the W3C mapping now. Key decisions:
- Each PAF annotation → one W3C Annotation
- `body.purpose` = `classifying` for entity/topic annotations; `describing` for sentiment; `tagging` for dialogue markers
- `body.value` = human-readable label
- Confidence → `oa:certainty` (from the Open Annotation extensions) or custom `palimpsest:confidence` property
- Export as JSON-LD array per track, or as a single AnnotationCollection with all tracks

---

## 4. UI Design Gaps

### 4.1 No Layout Design

The plan specifies individual components (TextLinearView, TrackPanel, DotplotView, OverviewBar, DetailPanel) but never describes how they're arranged on screen. Questions unanswered:
- Is it a fixed layout or resizable panels?
- Where does the DotplotView go relative to the TextLinearView?
- Is the DetailPanel a sidebar, a bottom drawer, or a modal?
- How does the user switch between views (tabs, split panes, floating windows)?

**Fix**: Define a default layout:
```
┌───────────────────────────────────────────────────────┐
│ Toolbar: project name, view selector, zoom, search    │
├──────────┬────────────────────────┬───────────────────┤
│          │                        │                   │
│  Track   │    TextLinearView      │   Detail Panel    │
│  Panel   │    (main reading area) │   (annotation     │
│  (left   │                        │    details,       │
│  sidebar)│                        │    LLM summary)   │
│          │                        │                   │
├──────────┴────────────────────────┴───────────────────┤
│ OverviewBar (full-document density barcodes)          │
├───────────────────────────────────────────────────────┤
│ Secondary View: DotplotView / CrossTextDotplot        │
│ (collapsible bottom panel, ~30% height)               │
└───────────────────────────────────────────────────────┘
```

All panels resizable via drag handles. Secondary view collapsible. DetailPanel collapsible. This should be documented with a wireframe, not left to improvisation during implementation.

### 4.2 No Keyboard Navigation

The plan mentions "keyboard shortcuts for rapid annotation" in Phase 2 but has no keyboard interaction plan for Phase 1. Scholarly users working with text expect:
- Arrow keys or j/k for paragraph navigation
- `/` or Ctrl+F for search
- Number keys (1-9) to toggle track visibility
- Escape to deselect
- Space to toggle play/pause for any future animation

Establishing keyboard navigation in Phase 1 sets the interaction vocabulary for the entire project.

### 4.3 No Search

A 300-page novel with 10 annotation tracks will produce thousands of annotations. The plan provides no way to search through them:
- No text search (find a word or phrase in the text)
- No annotation search (find all entity annotations matching "Hal")
- No cross-track query (find passages where sentiment < -0.5 AND dialogue is present)

Text search at minimum should be in Phase 1. Annotation search can wait for Phase 2. Cross-track queries are Phase 5.

### 4.4 No Loading/Progress Indicators

`palimpsest analyze` takes up to 30 seconds. `palimpsest analyze --enrich` (with BookNLP) could take minutes. The plan has no progress reporting:
- No CLI progress bar
- No browser loading state
- No indication of which track is being computed

**Fix**: CLI progress via `rich` or `tqdm` (one line per track, time elapsed, ETA). Browser: a loading overlay with track-by-track progress bar when project data is loading.

---

## 5. Dependency Risks

### 5.1 sqlite-vec Is Young

sqlite-vec is relatively new (v0.1.x). Its API, performance characteristics, and bug surface are less proven than alternatives like faiss or chromadb. If sqlite-vec has a critical bug or API breaking change during Phase 1 development, there's no fallback path documented.

**Fix**: Abstract the vector store behind an interface (`VectorStore` protocol with `add()`, `search()`, `count()`). sqlite-vec is the default implementation. A faiss implementation can be swapped in if sqlite-vec fails. This abstraction costs 20 lines and eliminates a single-vendor dependency risk.

### 5.2 MobX-state-tree Has a Learning Curve

MobX-state-tree (MST) is powerful but has a steep learning curve. Its immutable snapshot + mutable tree duality, strict typing, and action/view separation are non-obvious to developers used to simple React state or Redux. If the developer is new to MST, Week 2's "React scaffolding + MobX-state-tree setup" may take significantly longer than planned.

**Alternative**: Start with Zustand (much simpler API, same "stores outside React" pattern). Migrate to MST only if cross-view synchronization proves too complex for Zustand — which may not happen until Phase 2's annotation UI needs undo/redo (where MST's snapshot system shines).

**Recommendation**: Start with Zustand for Phase 1. Evaluate MST for Phase 2.

---

## 6. Protocol Establishment Gaps

### 6.1 No Git Workflow Defined

The plan describes a monorepo but says nothing about:
- Branching strategy (trunk-based? feature branches? release branches?)
- Commit message conventions
- PR/code review protocol (single developer now, but Phase 7 adds collaborators)
- Release versioning (semver? calver?)
- Changelog maintenance

**Recommendation**: Trunk-based development (commit to `main`). Conventional commits (`feat:`, `fix:`, `chore:`). Tags for milestones (`v0.1.0` = Milestone 1.1, `v0.2.0` = 1.2, etc.). Automated changelog from commit messages. This costs nothing to adopt now and prevents chaos later.

### 6.2 No Code Quality Standards

No mention of:
- Linter (ruff for Python, eslint for TypeScript)
- Formatter (ruff format, prettier)
- Type checking (mypy for Python, tsc strict mode)
- Pre-commit hooks

**Recommendation**: Set these up on Day 1. `ruff check + ruff format` for Python; `eslint + prettier` for TypeScript; `mypy --strict` for core/ types; pre-commit hooks to enforce. This is 30 minutes of setup that saves hundreds of hours of debugging.

### 6.3 No Documentation Protocol

The plan says "README.md: installation, quick start." But for a multi-phase project, the documentation strategy needs to be established:
- Where do ADRs go? (`docs/architecture/` — stated but not populated)
- Where do API docs go? (Auto-generated from FastAPI OpenAPI spec? Manual?)
- Where do user-facing docs go? (Separate docs site? README sections?)
- How are specs (PAF, LFO) kept in sync with code? (Generated from code? Manually updated?)

**Recommendation**: Specs are kept in `specs/` and manually updated per milestone (the plan already says this). API docs are auto-generated from FastAPI's OpenAPI schema. ADRs are written when a non-obvious decision is made. README is the single entry point for users.

---

## 7. Summary: What Must Change Before Implementation

### Critical (blocks correctness or forward compatibility)

1. **Add TrackRegistry** (§1.1) — extensibility protocol for both Python and browser
2. **Fix npz browser loading** (§1.4) — use raw binary Float32 instead of npz
3. **Add Relation/Target attributes to PAF spec** (§3.1) — forward compatibility for Phase 2
4. **Add pipeline_run.json** (§3.2) — reproducibility and provenance
5. **Define metadata.json schema** (§3.3) — corpus manager dependency
6. **Use public domain texts for test fixtures** (§2.2) — legal and CI/CD requirement
7. **Fix LDA non-determinism** (§2.4) — set random seeds for reproducibility

### Important (affects quality and efficiency)

8. **Add screen layout wireframe** (§4.1) — prevents re-layout during implementation
9. **Add text search** (§4.3) — basic usability for 300-page texts
10. **Add CLI progress reporting** (§4.4) — user experience during long computations
11. **Abstract vector store** (§5.1) — dependency risk mitigation
12. **Evaluate Zustand vs MST** (§5.2) — developer productivity
13. **Set up linting/formatting/pre-commit on Day 1** (§6.2) — code quality protocol
14. **Default to en_core_web_lg** (§2.3) — NER quality on literary text

### Advisable (establishes good protocols)

15. **Define git workflow** (§6.1) — trunk-based, conventional commits, milestone tags
16. **Document day-level scheduling as aspirational** (§2.1) — milestone deadlines are binding
17. **Sketch W3C export mapping** (§3.4) — avoid Phase 2 surprises
18. **Add keyboard navigation** (§4.2) — interaction vocabulary for the project
19. **Multi-project serving** (§1.5) — `palimpsest serve <workspace>` for cross-text features
20. **Track rendering manifest** (§1.2) — browser-side extensibility protocol

---

*This review identifies 20 specific issues across 6 categories. The 7 critical issues must be resolved before implementation begins; the 7 important issues should be resolved during Milestone 1.1; the 6 advisable issues should be addressed by end of Phase 1.*

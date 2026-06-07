# Phase 1 Task Errata

Issues discovered during cross-referencing all 37 task documents against the Phase 1 plan (v3.0).
**Apply these fixes before or during implementation of each task.**

---

## Critical (4 issues — must fix before coding)

### E-C1: T04 — `TrackRegistry.discover()` walks entire Python class hierarchy
**Problem**: `discover()` calls `collect_subclasses(object)` which traverses `object.__subclasses__()` — visiting hundreds of internal Python classes and trying to instantiate each one.
**Fix**: Change discovery to import all modules in the `tracks/` package, then collect `TrackExtractor.__subclasses__()` (subclasses of a concrete base, not the Protocol). Or use explicit registration: each track module calls `TrackRegistry.register(MyExtractor)` at module level, and `discover()` triggers the imports.

### E-C2: T02/T05 — PDF/TXT SHA-256 identity test will fail
**Problem**: pymupdf text extraction re-flows text at page width. After normalization, PDF and TXT extractions will NOT produce identical SHA-256 hashes.
**Fix**: Replace `assert compute_sha256(txt_norm) == compute_sha256(pdf_norm)` with substring assertions: both produce non-empty text, both contain "Mr. Bennet" and "Hertfordshire", paragraph count matches ±1. See `00-CONVENTIONS.md §4.2`.

### E-C3: T05 — `_split_paragraphs` offset tracking bug
**Problem**: `re.split(r"\n\n+", text)` discards the separators. `current_pos += len(block) + 2` assumes exactly 2 newlines between paragraphs. If the text has 3+ newlines, offsets drift.
**Fix**: Use `re.finditer(r"(?:^|\n\n+)(.+?)(?=\n\n|\Z)", text, re.DOTALL)` to capture both content and positions. Or track offsets by searching for each block with `text.index(block, current_pos)` and advancing by the actual match position.

### E-C4: T32 — Narrative arc shape is `[5, 3]`, not `[5, 15]`
**Problem**: T32 uses `reshapeRows(data, 5, 15)` and indexes columns `[3, 7, 8, 11, 12]` — all out of bounds. The Boyd arc is 5 segments × 3 dimensions (staging, plot_progression, cognitive_tension) = 15 total values, flattened. Reshape is `[5, 3]`.
**Fix**: Change all `[5, 15]` to `[5, 3]`. The chart renders 3 lines (one per Boyd dimension column). Remove references to "15 Boyd dimensions per row" — each row has 3 values. Change `reshapeRows(data, 5, 15)` → `reshapeRows(data, 5, 3)`.

---

## Important — Cross-Cutting (10 issues affecting multiple tasks)

### E-I1: Cross-task dependency numbering collisions
**Tasks**: T22, T28, T30, T33, T34
**Problem**: Several tasks reference earlier tasks by wrong numbers (e.g., T30 says "T22 (multi-track rendering)" but T22 is the Similarity Search task).
**Fix**: Replace all cross-series task number references with plan section references or descriptive names. See `00-CONVENTIONS.md §2.2`. Example: "T22 (multi-track rendering)" → "the multi-track rendering overlay (plan §10, Week 5)".

### E-I2: `SignalAdapter.ts` function name inconsistency
**Tasks**: T27, T32, T34
**Problem**: T27 defines `loadMatrixSignal()`, T32 calls `loadSignalMatrix()`, T34 calls `loadSignalMatrix()`.
**Fix**: Standardize on `loadSignal()` per `00-CONVENTIONS.md §1.3`. Signature: `(manifestUrl: string) => Promise<{manifest: SignalManifest, data: Float32Array}>`.

### E-I3: `WC3Annotation` typo in T09
**Tasks**: T09, T10 (propagates to all browser code)
**Problem**: TypeScript interface named `WC3Annotation` (W-C-3) instead of `W3CAnnotation` (W-3-C).
**Fix**: Rename to `W3CAnnotation` everywhere.

### E-I4: Evidence level placement (annotation root vs body)
**Tasks**: T11, T13
**Problem**: Some acceptance criteria say "annotation body has `palimpsest:evidenceLevel`" but the plan places it at the annotation root.
**Fix**: `palimpsest:evidenceLevel` and `palimpsest:confidence` are always at the **annotation root** (alongside `body`, `target`, `creator`), never inside `body`. See `00-CONVENTIONS.md §3.1`.

### E-I5: `depends_on` uses non-standard names
**Tasks**: T11, T12, T23, T24
**Problem**: Tracks declare `depends_on = ["spacy_parse"]` or `depends_on = ["embeddings"]` but no registered track has these names.
**Fix**: Use underscore-prefixed virtual dependency names per `00-CONVENTIONS.md §1.2`: `"_spacy_parse"`, `"_embeddings"`, `"_tokenization"`. The registry treats `_` prefix as pre-satisfied.

### E-I6: `/tmp` filesystem violations
**Tasks**: T10, T37
**Problem**: Smoke tests and scripts write to `/tmp`, violating project filesystem policy.
**Fix**: Use `${WORKSPACE:-$(pwd)/.scratch/smoke-test}` or pytest's `tmp_path` fixture. See `00-CONVENTIONS.md §4.4`.

### E-I7: `set -e` in bash scripts
**Tasks**: T37
**Problem**: `scripts/phase1-smoke-test.sh` uses `set -e`, which the project forbids (grep exit 1 kills script on macOS Bash 3.2).
**Fix**: Remove `set -e`. Use explicit error checking: `command || { echo "FAIL: step N"; exit 1; }`.

### E-I8: `OverviewBar` hardcoded 800px width
**Tasks**: T19
**Problem**: Density barcode uses `barcodeWidth = 800` pixels. Tick positions are wrong on larger/smaller screens.
**Fix**: Use `ResizeObserver` or `useRef` + `getBoundingClientRect()` to measure actual container width.

### E-I9: Missing `SegmentAnnotation` body type
**Tasks**: T05, T03
**Problem**: `segmenter.py` produces segment annotations but `SegmentAnnotation` is not defined in `bodies.py` or the plan's §2.3 table.
**Fix**: Add `SegmentAnnotation` to `bodies.py` with fields: `segmentType` (sentence/paragraph/section), `segmentIndex`. Add to `00-CONVENTIONS.md §8`.

### E-I10: `TrackExtractor.parameters()` method missing from protocol
**Tasks**: T04, T15
**Problem**: T15 uses `hasattr(e, "N_TOPICS")` to scrape parameters. Fragile and type-unsafe.
**Fix**: Add `parameters(self) -> dict[str, Any]` to the `TrackExtractor` Protocol. Default return `{}`. Each extractor returns its own params. T15 aggregates via `{k: v for e in extractors for k, v in e.parameters().items()}`. See `00-CONVENTIONS.md §7`.

---

## Important — Per-Task (28 issues)

### T01
- **E-T01a**: `mypy` config is inside the ruff TOML section. Show `[tool.mypy]` as a separate top-level block.
- **E-T01b**: `mypy_path = "core"` is wrong (pyproject.toml is already in `core/`). Remove or set to `"."`.
- **E-T01c**: `jsdom` missing from npm devDependencies. Add it for Vitest JSDOM environment.

### T04
- **E-T04a**: `test_registry_get_unknown_raises` uses `match="unknown"` (lowercase) but error message has "Unknown" (capital U). Change to `match="Unknown"`.
- **E-T04b**: Add `test_discover_empty_package_succeeds` — registry with no concrete extractors should return empty, not crash.

### T05
- **E-T05a**: Empty import block `from palimpsest.annotation.bodies import (  # type: ignore)` causes syntax error. Remove entirely.
- **E-T05b**: `segmenter.py` uses `disable=["ner", "textcat"]` but `textcat` may not exist in `en_core_web_lg`. Use `exclude=["ner"]` instead.

### T06
- **E-T06a**: `count_characters` imported from `normalizer.py` but not defined there. Add `def count_characters(text: str) -> int: return len(text)` to `normalizer.py`.

### T07
- **E-T07a**: `test_entity_extractor_detects_hertfordshire` should assert specifically that "Hertfordshire" is in detected LOC entities, not just "a location."

### T08
- **E-T08a**: `pipeline_run.json` uses `project.metadata.palimpsest_version` (ingest-time version). Should use runtime version for analysis provenance.
- **E-T08b**: `palimpsest serve` in T08 acceptance criteria cannot pass until T10 is done. Remove from T08's criteria or note it's tested in T10.

### T09
- **E-T09a**: `projectStore.ts` `loadProject` hardcodes segments + entities. Add comment: "M1.1 only; generalize for additional tracks in M1.2."
- **E-T09b**: `keyboard.ts` stub exports `createKeyboardHandler` but T10 replaces with `setupKeyboardHandlers`. Use same name in both.

### T10
- **E-T10a**: `test_server_serves_entities_jsonl` has spurious `runner` parameter. Remove it.
- **E-T10b**: `server.py` browser dist path (`__file__/../../..`) only works in dev (editable install). Document this limitation.

### T13
- **E-T13a**: Quote normalizer may convert curly quotes to straight, making `_CURLY_SINGLE` pattern dead code. Check what `normalizer.py` does; adapt or remove curly patterns.
- **E-T13b**: `test_dialogue_detects_pp_opening_quote` uses `anns[0]` (fragile). Replace with `any(ann for ann in anns if "Bennet" in (ann.body.value or ""))`.
- **E-T13c**: `test_dialogue_moby_em_dash` asserts `len(anns) >= 0` — always true. Change to `isinstance(anns, list)` minimum.

### T14
- **E-T14a**: `output_type = "annotation"` but also writes a signal as side effect. `pipeline_run.json` will miss `topics_dist` in `signals_computed`. Fix: have `extract()` return both annotation list and signal path, or add `secondary_outputs` to the protocol.
- **E-T14b**: LDA on chapter-length text (~15 paragraphs, 10 topics) may produce degenerate output. Add fallback: `n_topics = min(N_TOPICS, max(2, n_paragraphs // 2))`.

### T15
- **E-T15a**: Skip logic only checks `.jsonl` file existence. Signal tracks (which produce `.json` + `.bin`) are never skipped. Also check `signals/{name}.json`.
- **E-T15b**: spaCy model version hardcoded as `"en_core_web_lg/3.7.4"`. Read dynamically: `spacy.info("en_core_web_lg")["version"]`.

### T16
- **E-T16a**: `think: false` is documented as a comment but NOT in the actual `llm.py` payload dict. Add it to the payload: `"think": False`.
- **E-T16b**: `@pytest.mark.skipif(not _ollama_running(), ...)` evaluates at import time. `_ollama_running()` must be defined BEFORE the first decorated test.

### T17
- **E-T17a**: `test_client` fixture not defined — `test_summarize_endpoint_validation` uses it as free variable. Define as pytest fixture or parameter.
- **E-T17b**: `LLMSummary.tsx` sets state during render (anti-pattern). Use `useEffect` for passageId change detection.

### T18
- **E-T18a**: Single-character queries trigger `findMatches` on 122K-word text — blocks main thread. Add `if (query.length < 2) return []` or debounce 150ms.
- **E-T18b**: `[` and `]` keys in search input call `preventDefault()`, blocking the user from typing square brackets in search. Only intercept these from the global keyboard handler, not inside the input.

### T19
- **E-T19a**: `TrackManifest` interface missing `evidenceLevel?: string` field. Add it.
- **E-T19b**: `toggleTrackByIndex(index, visible)` takes a boolean — should be a toggle (no second param).

### T20
- **E-T20a**: `--snapshot-update` flag references syrupy but code uses hand-written comparator. Either adopt syrupy or remove the flag reference.
- **E-T20b**: `pp_ch1_project` fixture doesn't pre-populate `cache/spacy_docs.pkl`. All extractor tests that depend on spaCy cache will fail. Add a warm-up step.

### T25
- **E-T25a**: Feature dimension hardcoded as 19. Should be `2 + 4 + n_topics + 3` (dynamic).

### T26
- **E-T26a**: "8 tracks without BookNLP" is ambiguous. Clarify: 5 annotation JSONL tracks + 4 signals = 9 total outputs. "8" refers to annotation tracks only if you exclude segments.jsonl.

### T27
- **E-T27a**: Chapter boundary detection claims `segment_offsets` in signal manifest is sufficient, but it only has paragraph offsets, not chapter boundaries. Add `chapter_boundaries: number[]` to the manifest (computed by T23 from `project.sections()`).

### T28
- **E-T28a**: Tick color collision with T33. Resolution: orange `#e67e22` for selection indicator, yellow `#f1c40f` for search ticks.

### T31
- **E-T31a**: `zoomManualOverride` state flag missing from `viewStore`. Add `zoomManualOverride: boolean` (default false), set true on slider use, reset on scroll.

### T34
- **E-T34a**: Web Worker hardcodes embedding dimension as 2560. Read from `X-Shape` response header instead.
- **E-T34b**: `CanvasRenderer.tsx` assumes square matrix (`n × n`). Add `nCols?: number` prop (default `n`) for rectangular cross-text matrices.

### T35
- **E-T35a**: `annotation_to_paf_row()` missing `LexicalAnnotation` handling. Add case for `palimpsest:LexicalAnnotation` with ttr, hapaxCount, meanWordLength attributes.

### T36
- **E-T36a**: Boyd citation wrong ("Boyd 2010"). Correct to "Boyd et al. 2020, Science Advances."
- **E-T36b**: `KeyboardHelp.tsx` (? overlay) created in T36 but keyboard handler registered in T10. Move creation to T10 or earlier milestone.
- **E-T36c**: ADR-001 and ADR-005 are T01 deliverables. T36 acceptance criteria should say "verify they exist" not create them.

### T37
- **E-T37a**: `test_booknlp_fallback_produces_8_tracks` — count assertion is ambiguous with segments.jsonl. Assert `coreference not in track_names AND len(annotation_tracks) == 5`.
- **E-T37b**: Smoke test script should check Ollama availability before embedding-dependent steps.

---

## Milestone-Level Gaps (7 items)

### G1: No task creates ADRs 002, 003, 004
**Fix**: Assign ADR-002 → T04, ADR-003 → T07, ADR-004 → T09.

### G2: `topics_dist` signal produced as side-effect (T14) not tracked in `pipeline_run.json`
**Fix**: See E-T14a. Resolved by `parameters()` method or `secondary_outputs`.

### G3: `EmbeddingsPlaceholderTrack` not created for registry ordering
**Fix**: See E-I5. Virtual dependencies with `_` prefix resolve this.

### G4: Vite proxy for `/api/*` not configured
**Fix**: Add to T09: in `vite.config.ts`, add `server.proxy: { '/api': 'http://localhost:8080', '/data': 'http://localhost:8080' }`.

### G5: `TrackManifest.ts` loader referenced by T19 but never fully implemented
**Fix**: Add implementation steps to T09 or T19. The loader fetches `manifests/{trackName}.manifest.json` and returns a `TrackManifest` object with fallback defaults.

### G6: Browser `AnnotationAdapter.ts` not extended for M1.2 body types
**Fix**: The adapter returns generic `W3CAnnotation` objects (JSON parsed from JSONL). Body-type-specific TypeScript interfaces are optional type narrowing — the adapter itself is body-type-agnostic. Add a note to T09 that the adapter handles all body types generically.

### G7: Cross-text precomputed matrix path in T34 always 404s
**Fix**: Remove the precomputed-matrix fallback code from `loadCrossTextMatrix()`. Phase 1 always computes client-side.

---

*Apply these fixes during implementation. Critical issues (E-C1 through E-C4) must be resolved before coding begins. Important issues should be fixed when implementing the affected task. Gaps (G1-G7) should be addressed in the assigned tasks.*

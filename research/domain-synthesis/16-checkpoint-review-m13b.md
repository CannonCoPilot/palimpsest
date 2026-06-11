# Phase 1 Checkpoint Review — Post-M1.3b Adversarial Audit

**Date**: 2026-06-07
**Status**: RESOLVED — All 7 critical bugs fixed (2026-06-08). M1.4 implemented (2026-06-08-09). Additional 15 bugs fixed (2026-06-09 audit). See development-history.md for full fix log.
**Reviewer**: Multi-agent adversarial panel (4 independent reviewers)
**Scope**: Full codebase review against `14-phase1-plan-revised.md` (v4.0)
**Trigger**: Stakeholder walkthrough + manual QA identified browser defects; prompted comprehensive audit

---

## Executive Summary

The implementation is **M1.3b-complete in functionality** — core pipeline (10 tracks/signals), W3C annotation model, CLI, FastAPI server, React browser with annotation overlays, dotplot, and linked views are all working. 194 Python tests pass, 24 Rust tests pass, TypeScript compiles clean.

**M1.4 is entirely unstarted.** VirtualScroller, SemanticZoom, signal visualizations, cross-text dotplot, PAF export, all 4 spec documents, and Playwright tests are absent. Additionally, several findings across M1.1–M1.3b represent policy violations (silent error swallowing, non-deterministic IDs, silent model fallbacks) that should be remediated before proceeding to M1.4.

---

## Findings by Severity

### CRITICAL (must fix before M1.4)

| # | Area | File:Line | Finding | Plan Ref |
|---|---|---|---|---|
| C1 | Backend | `server.py:156` | `/api/search` catches all exceptions and returns empty results. A crash is indistinguishable from "no matches." Violates stated fallback policy. | §8.1 |
| C2 | Backend | `cli.py:158-159` | Embedding errors caught as bare `Exception`, printed as warning, execution continues. Programming bugs look identical to "Ollama not running." | §9.1 |
| C3 | Backend | `segmenter.py:83-101`, `entities.py:37-39` | Silent fallback from `en_core_web_lg` to `en_core_web_sm` with no logging. `parameters()` still reports `en_core_web_lg`. Pipeline silently degrades to lower-quality model. | §12.3 |
| C4 | Backend | `annotation/model.py:179-184` | Annotation IDs use `uuid.uuid4().hex[:8]` — non-deterministic. Re-running pipeline produces different IDs. Breaks idempotency and stable references. Determinism test (`test_tracks.py:287-295`) explicitly skips checking IDs. | §5.4 |
| C5 | Rust/Tauri | `tauri.conf.json` | `frontendDist` points at `../../../ui/dist` (legacy directory), `devUrl` port 5174 matches `ui/` not `browser/`. Tauri build wires to wrong frontend. | §1 |
| C6 | Specs | `specs/*.md` (all 4 files) | Every spec file is a 3-line stub (header + HTML comment deferring to "T36"). No actual specification content exists. The annotation format, LFO, signal format, and PAF export format are documented only implicitly in code. | §13 DoD |
| C7 | Browser | `browser/src/` (entire) | Zero test files exist. Vitest and Playwright are installed in `package.json` but have no configs and no tests. | §11.3, §11.1 |

### ERROR (should fix)

| # | Area | File:Line | Finding | Plan Ref |
|---|---|---|---|---|
| E1 | Backend | `cli.py:291` | PAF export is a user-facing CLI option (`click.Choice(["w3c", "paf", "csv"])`) but prints "not yet implemented." `test_export_paf_deferred` asserts the stub is a stub. | §2.9, M1.4 |
| E2 | Backend | `alphabet.py:139` | `SignalManifest` metadata contains `"note": "Phase 1 placeholder for LitHMM (Phase 2)"` — placeholder comment shipping in persistent output data. | §5.2 |
| E3 | Backend | `server.py:106-108` | `/api/search` GET endpoint has no query length validation. POST model `SearchRequest` has `max_length=2000` but the GET endpoint bypasses it. | §8.1 |
| E4 | Backend | `test_pipeline.py:27-28` | Pipeline fixture catches `(FileNotFoundError, ValueError, RuntimeError)` — `RuntimeError` is too broad, masks programming errors in extractors, causing downstream tests to pass vacuously. | §11.2 |
| E5 | Backend | `serializer.py:96-103` | `validate_annotation` checks `start >= 0` and `start <= end` but not `end <= text_length`. Out-of-bounds offsets pass validation. | §2.1 |
| E6 | Backend | `manager.py:47` | `except (httpx.ConnectError, httpx.TimeoutException, Exception)` — trailing `Exception` makes specific catches dead code. | — |
| E7 | Backend | `extractor.py:22-24` | Silent latin-1 fallback on UTF-8 `UnicodeDecodeError`. No log, no warning. Produces mojibake silently. | §0 policy |
| E8 | Backend | `rqa.py`, `alphabet.py` | `_compute_det` and `_compute_lam` use O(n²) Python loops. Performance sinkholes on long texts; no tests exercise large inputs. | §11.5 |
| E9 | Browser | (entire) | No virtualized scrolling — all paragraphs rendered to DOM unconditionally. Full novel = 1800+ paragraph nodes, violating the v4.0 plan's stated motivation. | M1.4, §7 |
| E10 | Browser | `OverviewBar.tsx:43-47` | SVG renders one `<line>` per annotation. At 1000+ annotations × 6 tracks = 6000+ DOM nodes. No canvas fallback, no throttle. | M1.4 |
| E11 | Browser | `projectStore.ts:116-120` | Tracks loaded sequentially (`for...of` with `await`). 7 serial HTTP round-trips instead of parallel. | §8.1 |
| E12 | Browser | `searchStore.ts:29-55` | `findMatches` scans full reference text synchronously on every keystroke. No debounce at call site (`TextSearch.tsx:24-29`). Blocks main thread on 500K-character novels. | §7.3 |
| E13 | Legacy | `src/` directory | 527-line legacy Python prototype still tracked in git. Not referenced by anything current. | §1 |
| E14 | Legacy | `ui/` directory | Old Tauri frontend with its own `package.json`, `node_modules`, and `dist/`. Superseded by `browser/` but still present. Tauri config references it (see C5). | §1 |

### WARNING (quality gaps)

| # | Area | File:Line | Finding | Plan Ref |
|---|---|---|---|---|
| W1 | Browser | `TextLinearView.tsx:74` | `collectVisibleAnnotations` runs unmemoized on every render — O(N) rebuild of flattened annotation array on every paragraph selection. | — |
| W2 | Browser | `TextLinearView.tsx:101-109` | Every `ParagraphView` receives full `allAnnotations` array. `AnnotationOverlay` re-runs `buildSpans` (O(N log N)) on every render. No per-paragraph pre-slicing. | — |
| W3 | Browser | `AnnotationOverlay.tsx:106-107` | Multi-annotation overlap shows only first annotation's color (`topAnn`). Overlapping entity + dialogue annotations show only entity color. | §7, M1.2 |
| W4 | Browser | `TrackPanel.tsx:27-77` | `TrackRow` is a `div` with `onClick`. No `role="button"`, no `tabIndex`, no `onKeyDown`. Keyboard-only users cannot toggle tracks. | §7.2 |
| W5 | Browser | `ProjectPicker.tsx:69-94` | Clickable project cards are `div` elements with no keyboard access. | §7.2 |
| W6 | Browser | `TextLinearView.tsx:39-62` | `ParagraphView` `div` with `onClick`, no `tabIndex`, no keyboard handler. | §7.2 |
| W7 | Browser | `AnnotationOverlay.tsx:102-122` | Annotation spans use color as primary information channel with no non-color fallback. Screen readers get nothing. `title` for tooltips (hover only). | — |
| W8 | Browser | `HelpOverlay.tsx` | Modal has no `role="dialog"`, no `aria-modal`, no focus trap. Tab escapes the modal. | — |
| W9 | Browser | `DetailPanel.tsx:161-173` | Close button renders `×` as raw text. Screen reader announces "times" or "multiply." No `aria-label`. | — |
| W10 | Browser | `viewStore.ts:13-14` | `zoomLevel` and `zoomManualOverride` declared and exported but never consumed by any component. Dead state from unimplemented SemanticZoom. | M1.4 |
| W11 | Browser | `src/assets/` | `react.svg`, `vite.svg`, `hero.png` — Vite scaffold artifacts not imported anywhere. | — |
| W12 | Browser | `TrackManifest.ts:15` | `textViewRendering` declares 3 modes (`highlight`, `underline`, `margin-marker`). Only `highlight` implemented. `underline` and `margin-marker` are dead variants. | §3.3 |
| W13 | Browser | `TrackPanel.tsx` / `trackStore.ts` | `confidenceThreshold` state exists and is applied in filtering logic, but no UI control (slider/input) exists to set it. Permanently 0. | M1.2, §7.1 |
| W14 | Browser | `OverviewBar.tsx` | Fixed `barWidth = 600` pixels. Width doesn't scale to viewport. | M1.4 |
| W15 | Browser | `TrackManifest.ts:19` | `dedicatedView?: string` declared in interface, loaded from JSON, never read by any component. Dead field. | — |
| W16 | Browser | `TrackManifest.ts:37` | `as TrackManifest` cast without runtime validation of fetched JSON shape. No Zod or schema check. | — |
| W17 | Browser | No `React.memo` | `ParagraphView` and `AnnotationOverlay` not memoized. Inline arrow `onSelect` prop busts referential equality. | — |
| W18 | Rust | `palimpsest-tauri` | Zero tests — all test coverage is in `palimpsest-core`. | §11.1 |
| W19 | Rust | `crates/palimpsest-core` | `RangeIndex` uses raw pointer (`*const [PackedAnnotation]`) with manual `unsafe impl Send/Sync`. Sound given arena lifetime but fragile if arena is ever moved post-construction. | — |
| W20 | Rust | Tauri commands | `get_signal_data` returns flat `Vec<f32>` with no shape metadata. Caller must make a second round-trip for dimensions. | — |
| W21 | Backend | `narrative_arc.py` | Boyd 15-dim narrative arc uses custom function-word lists, not Boyd's published categories. Shape (3-dim × 5 segments = 15 values) matches but feature semantics are a simplification. | §5.1 |
| W22 | Backend | Pre-commit | `.pre-commit-config.yaml` passes `--ignore-missing-imports` to mypy instead of `--strict`. `pyproject.toml` declares `strict = true` under `[tool.mypy]` but pre-commit hook overrides. | §0.7 |
| W23 | Git | (repo) | Zero milestone tags exist (`v0.1.0` through `v0.5.0`). Plan §0.6 requires tagging each milestone. | §0.6 |
| W24 | Backend | `TrackPanel.tsx` | `EVIDENCE_LEVEL_FALLBACK` hardcoded for display rather than reading from track manifest. Coupling smell. | §3.3 |
| W25 | Docs | `docs/architecture/` | Only ADR-001 and ADR-005 exist. ADR-002 (track-registry), ADR-003 (signal-format), ADR-004 (state-management) are absent. | §1 |
| W26 | Project | `fixtures/expected/` | Expected JSONL output directory for regression tests does not exist. | §11.4 |

---

## M1.4 Deliverables Status

| Deliverable | Plan Reference | Status | Notes |
|---|---|---|---|
| `VirtualScroller.tsx` | M1.4 Day 38-40 | **NOT STARTED** | All paragraphs rendered to DOM |
| `SemanticZoom.tsx` | M1.4 Day 41-42 | **NOT STARTED** | Dead state in viewStore, no rendering |
| Signal visualizations (arc sparkline, RQA chart, alphabet barcode) | M1.4 Day 43-44 | **NOT STARTED** | Signals computed but never displayed |
| OverviewBar enhancements (brush, stacked bars, responsive width) | M1.4 Day 45 | **PARTIAL** | Density barcodes + search ticks only |
| `CrossTextDotplot.tsx` | M1.4 Day 46-47 | **NOT STARTED** | Empty directory exists |
| PAF export (`paf_export.py`) | M1.4 Day 48 | **NOT STARTED** | CLI option exists but prints stub message |
| `specs/annotation-model.md` | M1.4 Day 49-50 | **STUB** | 3-line placeholder |
| `specs/LFO.md` | M1.4 Day 49-50 | **STUB** | 3-line placeholder |
| `specs/signals.md` | M1.4 Day 49-50 | **STUB** | 3-line placeholder |
| `specs/PAF-export.md` | M1.4 Day 49-50 | **STUB** | 3-line placeholder |
| Regression tests (JSONL snapshots) | M1.4 Day 49-50 | **NOT STARTED** | No `fixtures/expected/` directory |
| Playwright E2E tests | §11.3 | **NOT STARTED** | Frameworks installed, no tests |
| Git milestone tags | §0.6 | **NOT STARTED** | Zero tags |
| `ResizablePanel.tsx` | §7.1, M1.1 | **NOT STARTED** | Fixed-width divs |
| DotplotView zoom/pan | M1.3b Day 34-36 | **PARTIAL** | Click-to-navigate only |
| ADR-002 through ADR-004 | §1 | **NOT STARTED** | Only ADR-001 and ADR-005 exist |
| Confidence slider UI | M1.2 | **NOT STARTED** | State wired, no control |

---

## Scores

| Dimension | Backend | Browser | Rust | Overall |
|---|---|---|---|---|
| Functionality | 8/10 | 6/10 | 8/10 | **7/10** |
| Code quality | 6/10 | 6/10 | 8/10 | **6/10** |
| Test coverage | 7/10 | 0/10 | 7/10 | **5/10** |
| Documentation | 1/10 | — | — | **1/10** |
| Performance readiness | 6/10 | 3/10 | 9/10 | **5/10** |

---

## Recommendations

1. **Remediate C1–C4 immediately** — these are policy violations, not missing features. Silent error swallowing, non-deterministic IDs, and silent model fallbacks undermine trust in pipeline output.
2. **Delete legacy directories** (E13, E14) and fix Tauri config (C5) — dead code that misleads and wastes space.
3. **Decide M1.4 scope** — the v4.0 plan's stated motivation was rendering performance (VirtualScroller). If M1.4 is pursued, virtualization is the single most important deliverable. If M1.3b is accepted as the Phase 1 exit, document the descope explicitly.
4. **Browser tests before more features** (C7) — zero browser test coverage is the single largest risk.
5. **Parallel track loading** (E11) — trivial fix with large UX impact.

---

*Generated by 4-agent adversarial review panel. Each agent independently reviewed one dimension (exit criteria, backend quality, browser quality, Rust/specs). Findings were deduplicated and severity-assessed by the synthesizing agent.*

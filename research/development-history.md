# Palimpsest Development History Log

**Created**: 2026-06-07
**Purpose**: Chronological record of major milestones, document completions, decisions, and persona reviews. Audited at every milestone gate.

---

## Log Entries

### 2026-06-07 — M1.3b Checkpoint Review + Documentation Overhaul Initiated

**What happened**:
- M1.3b implementation functionally complete (10 tracks/signals, browser, CLI, server)
- 194 Python tests, 24 Rust tests passing
- Stakeholder walkthrough identified 4 browser bugs (search nav, color sync, dotplot, track numbering) — all fixed
- Additional bugs found and fixed: segments manifest missing (404), React hooks order violation, DotplotView crash on hover, BookNLP coreference reading wrong file, HF model caching
- 4-agent adversarial review conducted: 7 critical, 14 error, 26 warning findings
- Checkpoint review document created: `16-checkpoint-review-m13b.md`
- Phase 1 plan updated to v4.1 with all findings integrated
- Back-to-drawing-board process document created: `00-back-to-drawing-board.md`

**Decisions**:
- M1.4 work paused pending comprehensive documentation overhaul
- Research corpus to be expanded from 49 to 75+ sources
- All planning documents to be revised from scratch with deeper scholarly grounding
- 5 adversarial review personas defined for ongoing use

**Documents produced**:
- `research/domain-synthesis/16-checkpoint-review-m13b.md`
- `research/domain-synthesis/14-phase1-plan-revised.md` (v4.1 update)
- `research/domain-synthesis/00-back-to-drawing-board.md`
- `research/development-history.md` (this file)

**Status**: Stage 1 (Research Expansion) begins next session.

---

### 2026-06-07 — Stage 1 Research Expansion (partial)

**What happened**:
- 4 parallel research agents searched Google Scholar across computational linguistics, genomics, visualization, and Swinehart/reports
- ~80 papers identified across all domains to fill knowledge gaps
- 3 foundational books downloaded: Genette "Narrative Discourse", Durbin et al "Biological Sequence Analysis", Fry "Visualizing Data"
- MCP configuration updated: scholar-gateway and annas-archive added to project settings.json for auto-loading
- Download priority established: Scholar Gateway (free) → PubMed PMC (free) → Anna's Archive (limited)

**Key discoveries**:
- "Literary orthology/paralogy" concept from Fitch (1970) / Koonin (2005) — potential novel theoretical contribution
- "LitHMM" concept from ChromHMM (Ernst/Kellis 2010, 2012) — core Palimpsest innovation: discover text states without pre-defining them
- Genette's "Palimpsests" (1982) — source of project name, not yet in corpus until now
- Gosling grammar (L'Yi 2022) — closest published analog to Palimpsest's architecture
- Sequence Ontology (Eilbeck 2005) — direct model for literary feature ontology

**Decisions**:
- Research MCPs now load in every Jarvis session (added to project settings.json)
- Anna's Archive downloads capped as last resort
- ~70 papers still need downloading in next session

**Status**: Stage 1 ~40% complete (search done, downloads mostly pending)

---

### 2026-06-08 — Stage 1 Research Expansion (completion) + Stages 2-4 Executed

**What happened**:
- Research corpus expanded from 52 to 118 PDFs (66 new downloads in one session)
- Downloads via: Scholar Gateway (arXiv/ACL Anthology), Anna's Archive DOI lookup, PubMed PMC, Unpaywall API, Semantic Scholar, Europe PMC, direct publisher URLs
- Built `download-paper.py` — robust Python downloader with 7-strategy fallback chain
- Identified Anna's Archive filename-too-long bug (workaround: fastDownload → curl with short filename)
- Registered arXiv MCP server in project settings.json for future sessions
- 11 low-priority papers identified as manual acquisition (all non-essential — coverage already exists)
- Master bibliography rewritten: 117 entries organized by domain

**Stage 1 completion**:
- Doc 17: Swinehart Deep Analysis (~4,800 words, 5 sections)
- Doc 18: Stage 1 Gap Analysis — comprehensive coverage assessment
- Bibliography: 117 entries, 7 sections, manual acquisition list

**Stage 2 deliverables**:
- Doc 19: Conceptual Foundation (~6,000 words) — synthesizes docs 01, 03-10 into unified framework grounded in 118-paper corpus. Defines 7 core principles: text as sequence, annotations as tracks, alignment as comparison, genome browser paradigm, evidence-based annotation, agnostic discovery, perspectival modeling.
- Doc 20: Cross-Document Consistency Review — 32 issues found (3 HIGH: LitHMM naming, PAF/W3C format hierarchy, Tauri/Python stack ambiguity). Terminology canon established for 12 core concepts.

**Stage 3 deliverables**:
- Doc 21: Vision Document (~400 lines) — 5 Mermaid diagrams, Base/X architecture, 5 analytical layers, 4 browser views, 6 novel contributions, adversarial persona endnotes
- Doc 22: Product Requirements Document — 10 sections, 39 feature requirements (F-IMP, F-TRK, F-ALN, F-EXT, F-BRW, F-AI, F-FMT), 5 non-functional requirements, 4 user narratives
- Doc 23: Development Roadmap v3.0 — 5 milestones, Gantt chart, vision-gated acceptance criteria, risk register. ~39 weeks total timeline.
- Doc 24: M1 Roadmap-PRD — 4 phases detailed with deliverables and acceptance criteria. Existing 37 atomized task documents (phase1-tasks/) confirmed structurally sound; need only terminology alignment per doc 20.

**Key discoveries**:
- Scholar Gateway MCP has Google Scholar rate-limiting issues — unreliable for batch downloads
- Anna's Archive DOI lookup has wrong-paper resolution for some DOIs (Nature Methods, IEEE TVCG)
- Anna's Archive downloadJournal has filename-too-long bug on macOS
- PubMed PMC PDF downloads often fail (double redirect + bot detection)
- Unpaywall API is the most reliable free OA discovery service

**Adversarial persona notes**:
- Dr. Marchetti: Genomic analogies in docs 19/21 are structurally grounded, not superficial. ChromHMM→LitHMM mapping preserved with appropriate caveats about ground truth differences.
- Prof. Blackwood: Base/X architecture addresses the reduction concern — Base is deliberately reductive, X is where human judgment enters. Perspectival modeling (Underwood) embedded throughout.
- Dr. Okonkwo: Performance concerns addressed in NFR-001, doc 15, and M5.1.
- Dr. Patel: Progressive disclosure and semantic zooming address information overload. 4 linked views provide complementary perspectives.
- Alex Chen: Corpus-scale operations specified in M4. Narrative alphabet enables fast structural search.

**Decisions**:
- LitHMM is the canonical term (not ModeHMM, PassageStateHMM)
- W3C JSONL is primary annotation format; PAF is computational export
- Python/React is the current implementation stack; Tauri/Rust is future optimization
- 39-week roadmap from M1.1 to v1.0 release

**Documents produced this session**:
- `17-swinehart-deep-analysis.md`
- `18-stage1-completion-gap-analysis.md`
- `19-conceptual-foundation.md`
- `20-consistency-review.md`
- `21-vision-document.md`
- `22-product-requirements.md`
- `23-development-roadmap-v3.md`
- `24-m1-roadmap-prd.md`
- `bibliography/master-bibliography.md` (rewritten)
- `download-paper.py` (research tool)
- `papers-to-download.json` (download manifest)

**Status**: Stages 1-4 of back-to-drawing-board overhaul COMPLETE. Ready for implementation.

---

### 2026-06-08 — Polishing Pass: Terminology Fixes, Persona Scoring, CLAUDE.md Integration

**What happened**:
- Applied terminology canon from doc 20 across all documents: 22 ModeHMM→LitHMM replacements, 3 PassageStateHMM→LitHMM, 1 NarrativeFold→TextHiC, plus code comment fix in `core/palimpsest/tracks/alphabet.py`
- Added clarifying headers to 5 documents: doc 02 (format note), doc 09 (GFF3 analogy disclaimer), doc 13 (superseded), doc 12a (review target note), doc 15 (design spec status)
- Formal persona scoring conducted on docs 21-24: all PASS at ≥4/5 on all dimensions (doc 25)
- 10 remediation items cataloged for implementation time
- Documentation map written: `research/DOCUMENT-MAP.md` — reading order, full topology, terminology canon
- Jarvis CLAUDE.md updated to v5.12.1 with Palimpsest doc chain section: 7 primary docs, implementation refs, research deep reads, quality assurance refs, terminology canon

**Documents produced**:
- `25-persona-scoring.md` — formal 5-persona review of all Stage 3 docs
- `research/DOCUMENT-MAP.md` — project documentation topology
- Jarvis CLAUDE.md updated with Palimpsest canonical hierarchy

**Completion criteria final audit**:
All 8 criteria from doc 00 now fully PASS. The two PARTIAL items from the prior entry are resolved:
- Criterion 2 (consistency): 22 terminology fixes applied, headers added to 5 stale docs
- Criterion 7 (persona scoring): all 4 primary docs score ≥4/5 on all 5 persona dimensions

**Status**: Back-to-drawing-board overhaul is FULLY COMPLETE. All completion criteria met. Ready for M1.1 implementation.

---

### 2026-06-08 — M1.1–M1.4 Implementation Sprint

**What happened**:
- Executed full Milestone 1 (Walking Skeleton) implementation across all 4 phases
- Created 3 new track extractors: `syntax.py` (syntactic complexity), `lithmm.py` (LitHMM passage states), `compartments.py` (thematic A/B decomposition + TAD-like domains)
- Added sentence segmentation to ingest pipeline (paragraph + section were existing)
- Added character clustering to entity extractor (canonical name assignment via substring/surname matching)
- Implemented spaCy NER fallback for coreference when BookNLP unavailable
- Created LFO v0.1 spec (22 terms in `specs/lfo-v0.1.json`)
- Created PAF v0.1 spec (`specs/paf-v0.1.md`) + full PAF export implementation + `palimpsest validate` CLI command
- Added `coordinates.json` generation to ingest pipeline
- Updated browser: track colors for all 13 tracks, AnnotationOverlay body type mappings
- Full P&P novel analysis: 16 tracks computed (13 annotation + 3 signal) in 3.5 minutes, producing 41,302 annotations

**Tracks registered (13)**: entities, sentiment, lexical, syntax, dialogue, topics, narrative_arc, coreference, self_similarity, rqa, lithmm, compartments, alphabet

**LitHMM results on P&P**: 10 distinct states with auto-generated descriptions. Examples: "high dialogue ratio" (conversation scenes), "high entity density, high sentiment volatility" (emotionally charged multi-character scenes). A/B compartments: 1,296/1,273 split across 38 domains.

**Test results**: 194 passed, 0 failures. Browser TypeScript compiles cleanly.

**Status**: M1 functionally complete. Adversarial review scheduled.

---

### 2026-06-08 — Five-Agent Adversarial Codebase Audit

**What happened**:
5 parallel review agents examined every source file against all 4 design documents (19, 20, 22, 24). Coverage: all Python tracks, browser TypeScript, ingestion/annotation model, Rust crates, test suite, and design document adherence.

**Summary**: Of 24 M1 acceptance criteria — 11 PASS, 12 PARTIAL, 1 FAIL (semantic zooming).

#### Critical Bugs Found (7)

1. **LitHMM method detection always wrong** (`lithmm.py:215`): checks `"hmmlearn" in str(type(labels))` but labels is always numpy.ndarray. `lithmm_meta.json` always reports "KMeans-fallback" even when GaussianHMM runs.
2. **LitHMM features 4+5 degenerate** (`lithmm.py:83-97`): `sentence_length_var` reads one annotation per paragraph — variance never computable. `topic_entropy` reads one weight — entropy always ~0. Two of six features are non-functional.
3. **Topics crashes on <10 paragraphs** (`topics.py`): `N_TOPICS=10` always requested; LDA raises ValueError when n_samples < n_components. Guard only covers 0-1 paragraphs.
4. **Alphabet takes first sentiment, not mean** (`alphabet.py:62-64`): comment says "mean valence per paragraph" but code breaks after first annotation match.
5. **W3C export missing namespace** (`cli.py:280-287`): `AnnotationCollection` @context omits `palimpsest` namespace; nested `palimpsest:*` properties undefined.
6. **Section segmenter crosses paragraph boundaries** (`segmenter.py`): regex `[A-Z][A-Z\s]{5,}` uses `\s` matching `\n`, capturing across blank lines.
7. **Coreference docstring lies** (`coreference.py:31-33`): says "raises FileNotFoundError" but actually returns spaCy fallback results.

#### Browser Gaps (13 missing features)

- Virtual scrolling: NOT implemented — all paragraphs rendered to DOM
- Semantic zooming (4 levels): state defined, never consumed by any component
- Track drag-and-drop reordering: NOT implemented
- Track sparkline overviews: NOT implemented
- Coordinate system switching UI: NOT implemented
- Coreference chain following: NOT implemented
- Search highlight in text: only navigation, no visual highlighting
- LitHMM color-coded band: NOT implemented (generic span overlay only)
- Alphabet letter sequence display: NOT implemented
- Compartment A/B color track: NOT implemented
- HTML/Markdown ingestion: NOT implemented (raises ValueError)
- TextTiling section fallback: NOT implemented
- Confidence threshold slider: store wired, no UI

#### Method Fidelity Issues (3)

- Sentiment: VADER per-sentence, not sliding-window hedonometer (Reagan 2016)
- Narrative arc: hand-curated word lists, not Boyd 2020 LIWC categories. Provenance label `"boyd_function_words/0.1"` is fabricated.
- Dialogue: regex-based, not BookNLP pipeline. Speaker attribution unreliable for multi-token names.

#### Cross-Cutting Performance Issues (3)

- O(n²) paragraph lookups in 7 tracks (should use bisect)
- 4 redundant spaCy parses per pipeline run (~2-4 GB RAM wasted)
- No annotation caching in browser (synchronous main-thread parsing)

#### Design Violations

- JBrowse adapter/track/display/renderer architecture: adapter only; display, renderer, registry layers absent
- `registry/` directory empty — plugin architecture scaffolded but not built
- `manifest.textViewRendering` field (`highlight`/`underline`/`margin-marker`) never read by any component

#### Test Coverage Gaps

- `SyntaxExtractor`, `LitHMMExtractor`, `CompartmentsExtractor`: zero tests each
- `SelfSimilarityTrack`: no behavioral tests
- Browser: zero automated tests
- KMeans fallback path in LitHMM: untested

#### Terminology Violations (5)

- `DotplotView.tsx`, `dotplotOpen`, `toggleDotplot`: should be TextHiC
- `alphabet.py:138`: stale "Phase 1 placeholder for LitHMM (Phase 2)" comment
- `lfo-v0.1.json`: `signal.rqa_metrics` vs `rqa.py`'s `signal.rqa`
- `narrative_arc.py:86`: fabricated `source="boyd_function_words/0.1"` provenance

**Decisions**:
- All critical bugs to be fixed immediately
- Browser architectural gaps documented but deferred to focused browser sprint
- Method fidelity: rename provenance labels to be honest about actual implementations
- Performance issues: implement bisect lookups and spaCy parse caching

**Status**: All fixes complete. 214 tests passing.

---

### 2026-06-08 — Tier 1 Vision Gate Sprint: All 4 Features Implemented

**What happened**:
Following the five-agent audit and bug fix session, the four Tier 1 Vision Gate features were implemented to bring M1 to professional-deliverable quality. All four were identified as blockers for passing the M1 exit test: "Load Infinite Jest, see 12 Base tracks, zoom into a scene, LitHMM has colored it 'state 4', ask the AI 'What is state 4?' and get a data-grounded response."

#### Feature 1: Search Match Highlighting
- `searchStore.ts` already computed `SearchMatch[]` with character offsets — wired them through to `AnnotationOverlay`
- `TextLinearView.tsx` now reads `searchMatches` and `currentMatchIndex` from search store
- `AnnotationOverlay.tsx` renders search matches as yellow/gold highlights (`#ffeb3b` for current, `#fff59d` for others)
- Search matches composable with annotation highlights — both render simultaneously
- `collectVisibleAnnotations` wrapped in `useMemo` for perf

#### Feature 2: Track-Specific Rendering
- `TrackManifest.ts` expanded: `textViewRendering` now supports `'highlight' | 'underline' | 'margin-marker' | 'color-band'`; `overviewBarRendering` supports `'state-band'` type
- `AnnotationOverlay.tsx` fully rewritten with rendering dispatch based on manifest `textViewRendering`:
  - **color-band** (LitHMM): reads `palimpsest:stateId` from annotation body, indexes into `colorScheme.scale` array for per-state HSL colors, renders as left-bordered colored band
  - **highlight** (default): standard colored background. Sentiment track gets polarity-driven red/green gradient via `palimpsest:polarity` field
  - **underline** (coreference, entities): colored underline decoration instead of background fill
  - **margin-marker** (topics): left border marker without inline coloring
- Hover titles now include state descriptions, topic labels where available
- Overlay now reads `trackStore.tracks` to access per-track manifests at render time

#### Feature 3: Virtual Scrolling
- Added `@tanstack/react-virtual` dependency
- `TextLinearView.tsx` now conditionally virtualizes when paragraph count >= 200 (threshold constant `VIRTUALIZE_THRESHOLD`)
- `VirtualizedView` component: `useVirtualizer` with dynamic row height estimation based on text length, `overscan: 10`, `measureElement` ref for accurate size after render
- `SimpleView` component: original map() for small documents (avoids virtualizer overhead)
- `scrollToIndex` replaces `querySelector` for virtualized scroll-to-paragraph
- Full Infinite Jest (~2,569 paragraphs) should now render without choking the browser

#### Feature 4: AI State Explanation (`/api/explain`)
- **Backend**: New `POST /api/explain` endpoint in `server.py`:
  - Reads `lithmm_meta.json` from project signals directory
  - Extracts state descriptions, feature names, representative passage samples
  - Constructs a narrative-focused prompt for Ollama LLM
  - Returns structured `ExplainResponse` with `explanation`, `state_description`, `feature_profile`, `sample_passages`
  - Gracefully handles Ollama unavailability (returns data without AI explanation)
- **Frontend**: New `StateExplainer.tsx` component:
  - Appears in DetailPanel when a LitHMM annotation is selected
  - Shows statistical state description on idle
  - "Explain this state" button fetches from `/api/explain`
  - Displays AI narrative explanation + 2 sample passages + model attribution
  - Handles unavailable/error states identically to LLMSummary pattern
- `DetailPanel.tsx` updated: imports `StateExplainer`, conditionally renders it when `body.type === 'palimpsest:LitHMMAnnotation'`

**Files modified**:
- `browser/src/components/TextLinearView/AnnotationOverlay.tsx` — complete rewrite
- `browser/src/components/TextLinearView/TextLinearView.tsx` — virtual scrolling + search wiring
- `browser/src/components/DetailPanel/DetailPanel.tsx` — StateExplainer integration
- `browser/src/adapters/TrackManifest.ts` — expanded type union
- `browser/package.json` — added `@tanstack/react-virtual`
- `core/palimpsest/server.py` — added `/api/explain` endpoint + models
- **New file**: `browser/src/components/DetailPanel/StateExplainer.tsx`

**Validation**:
- TypeScript: clean compile (`tsc --noEmit` — 0 errors)
- Vite build: 253.92 kB bundle, 0 errors
- Python: 214 tests passing, 0 failures
- No regressions introduced

**Decisions**:
- Virtual scrolling threshold set at 200 paragraphs (below that, map() is fine)
- Search match highlighting uses Material Design yellow palette for familiarity
- LitHMM color-band uses existing HSL scale from Python manifest — no new color generation needed
- Sentiment gets polarity-driven coloring only in `highlight` mode — avoids overwhelming the text when many tracks visible

**Status**: Tier 1 Vision Gate complete. M1 exit test scenario now wired end-to-end.

---

### 2026-06-08 — Paradigm Shift: FDD/BDD + EPUB Pipeline + M1 Exit Criteria

**What happened**:
Major methodology and planning overhaul. Shifted from Test-Driven Development to Feature-Driven Development (FDD) with Behavior-Driven Development (BDD) overlay. Designed the EPUB structural import pipeline based on analysis of the actual Infinite Jest EPUB file. Produced comprehensive exit criteria and atomized task list for M1 completion.

#### EPUB Analysis Findings
- IJ EPUB: 21 HTML files (Calibre splits, not chapter-aligned), 67 h3 section headings (date/time format), 388 bidirectional endnotes (sdendnote{N}anc ↔ sdendnote{N}sym patterns)
- Multi-paragraph endnotes (e.g., #24 Filmography), nested sub-notes (#387), endnote number duplication artifacts
- EPUB 2.0 via Calibre 0.7.32 conversion; OPF contains ISBN, publisher, date
- No meaningful NCX TOC (indexes endnotes, not chapters)
- External image references (not bundled) — conversion artifact

#### New Planning Documents
- **Doc 26: M1 Design Philosophy & Exit Criteria** — Formalizes FDD 5-step process, defines 6 BDD user stories (Given-When-Then), specifies 24 exit criteria (12 functional, 8 quality, 4 documentation), quality standards, Vision Gate test procedure
- **Doc 27: M1 Completion Implementation Plan** — EPUB pipeline design (5-phase parser), 41 atomized tasks organized in 9 categories (A: EPUB Pipeline, B: Audit Remediation, C: Semantic Zoom, D: Endnote UI, E: Export, F: Browser Polish, G: Specs, H: Testing, I: Packaging), dependency graph, 8 execution phases, ~96 hours estimated

#### Existing Document Revisions
- **Doc 22 (PRD)**: F-IMP-001 expanded from 4 lines to 12 lines — now specifies EPUB structural extraction (sections, endnotes, metadata), backward compatibility, enhanced metadata.json and coordinates.json
- **Doc 24 (M1 Roadmap-PRD)**: M1.1 deliverables updated with EPUB structural extraction; acceptance criteria expanded from 7 to 11 items (added section detection, endnote extraction, metadata, endnote UI, section navigation); methodology reference to docs 26-27 added
- **DOCUMENT-MAP.md**: Updated total count (32 docs), added docs 26-27 to primary chain and planning history, expanded reading order to 10 items

**Decisions**:
- EPUB endnotes appended to reference.txt with separator (not in separate file) — Wallace intended them as integral to reading
- Section boundaries come from HTML heading elements, not Calibre file splits (splits are arbitrary size cuts)
- FDD/BDD does not replace TDD — unit tests remain for internal correctness, but acceptance standard shifts to end-to-end user stories with real IJ content
- 41 tasks across 8 phases replaces T30-T37 for the M1 completion sprint
- Virtual scrolling threshold (200 paragraphs) and all prior Tier 1 decisions carry forward unchanged

**Status**: Planning complete. Phase 1 implementation started and completed same session.

---

### 2026-06-08 — Phase 1 Implementation: EPUB Pipeline Foundation (A01-A06, A08)

**What happened**:
Implemented the EPUB structural import pipeline and validated it against the actual Infinite Jest EPUB. Tasks A01 through A06 completed; A08 smoke test passed.

#### Implementation Summary

**New file**: `core/palimpsest/ingest/epub_parser.py` (~350 lines)
- `parse_epub(path)` → `EpubParseResult` with text, metadata, sections, endnotes
- Phase 1: OPF metadata extraction (title, author, ISBN, publisher, date, UUID)
- Phase 2: Spine traversal with heading detection (h1-h6 → section boundaries)
- Phase 3: Endnote extraction (sdendnote{N}anc ↔ sdendnote{N}sym bidirectional links)
- Phase 4: Multi-paragraph endnote grouping
- Phase 5: Text assembly with whitespace normalization

**Modified files**:
- `core/palimpsest/ingest/extractor.py` — EPUB dispatch routes to epub_parser; added `extract_epub_structured()`
- `core/palimpsest/annotation/bodies.py` — Added `section_body()` and `endnote_body()` constructors
- `core/palimpsest/project.py` — `ingest_file()` handles EPUB structural data: generates sections.jsonl, endnotes.jsonl, enhanced metadata.json with ISBN/publisher/date, coordinates.json with endnote_region
- `specs/lfo-v0.1.json` — Added 3 terms: `structure.section_boundary`, `structure.endnote`, `structure.heading`
- `browser/src/components/TextLinearView/AnnotationOverlay.tsx` — Added section/endnote body type mappings + superscript rendering mode
- `browser/src/adapters/TrackManifest.ts` — Added 'superscript' and 'none' to rendering union
- `browser/src/utils/trackColors.ts` — Added sections (#8e44ad) and endnotes (#e74c3c) colors

#### Infinite Jest EPUB Ingest Results (Smoke Test A08)

| Metric | Value |
|--------|-------|
| Text length | 3,214,883 chars |
| Word count | 545,792 |
| Paragraphs | 6,954 |
| Sections detected | 70 (includes front matter, 67 narrative, "The End") |
| Endnotes extracted | 379 with call-site positions / 388 total |
| Sentences | 24,080 |
| ISBN | 9780316920049 (correct) |
| Publisher | Hachette Digital, Inc. (correct) |
| Output tracks | sections.jsonl (70), endnotes.jsonl (379), segments.jsonl (31,539) |

**Validation**:
- Python: 214 tests passing, 0 failures, no regressions
- TypeScript: clean compile (tsc --noEmit — 0 errors)
- Vite build: 254.28 kB bundle, 0 errors

**Decisions**:
- Section headings normalized: whitespace collapsed ("YEAR OF GLAD" not "YEAR\nOF GLAD")
- First-word matching for section offset resolution (handles text reflow between HTML and clean text)
- Endnote text cleaned: leading number prefix stripped, multi-paragraph notes grouped

**Remaining from Phase 1**: A07 (formal test suite with IJ fixture) — deferred to next session with other testing tasks (Category H).

**Status**: EPUB Pipeline Foundation complete. Infinite Jest ingests successfully through the full pipeline.

---

### 2026-06-08 — EPUB Pipeline Refinement: Multi-Book Validation + TOC Fallback

**What happened**:
Tested the EPUB parser against three structurally different books to expose format-specific assumptions. Discovered and fixed a critical gap: EPUBs without HTML heading tags (which is common — many EPUBs use CSS-styled titles instead of semantic h1-h6).

#### Test Books

| Book | Publisher | EPUB Pattern | Result Before Fix | Result After Fix |
|------|-----------|-------------|-------------------|-----------------|
| The Correspondent (Evans 2025) | Crown | HTML headings (h1/h2/h3) | 18 sections | 18 sections (unchanged) |
| Pride and Prejudice (Austen 1813) | Barnes & Noble | No headings, rich NCX TOC | 0 sections | **74 sections** via TOC |
| The Last of the Mohicans (Cooper 1919) | Scribner's | No headings, numeric NCX TOC | 0 sections | **26 sections** via TOC + Chapter N |

#### Fixes Applied

1. **NCX/TOC fallback** (`_sections_from_toc`): When HTML heading detection returns empty, parser traverses the NCX table of contents and matches TOC entry titles to positions in the assembled text. Handles both `Link` objects and nested `(Section, children)` tuples.

2. **Numeric chapter title matching**: TOC entries like "1", "2", "3" (common in older EPUBs) don't appear as standalone text. Parser now tries `"Chapter {N}"` and `"CHAPTER {N}"` variants before falling back to line-boundary matching.

3. **Heading whitespace normalization**: Headings from Calibre EPUBs had embedded newlines from `<br>` tags ("YEAR\nOF GLAD"). Now collapsed with `" ".join(text.split())`.

4. **Section offset resolution**: Uses first-word matching in a ±500 char window rather than exact full-text match, handling reflow between HTML and clean text.

**Validation**:
- All 4 books (IJ + 3 test books) ingest successfully
- 214 Python tests passing, no regressions
- TypeScript clean, Vite builds

**Status**: EPUB pipeline handles diverse EPUB structures. Ready for Category B (Audit Remediation).

---

### 2026-06-09 — Categories B-G Implementation: Import UI, Audit Fixes, Navigation, Specs

**What happened**:
Implemented high-priority items from Categories B through G of the M1 Completion Plan (Doc 27). Major additions: browser-based EPUB import, section navigation sidebar, endnote display panel, deterministic annotation IDs, error boundaries, and all three spec file completions.

#### Category B: Audit Remediation + EPUB Import UI

**B-NEW: Browser EPUB Import UI**
- Backend: `POST /api/import` endpoint in `server.py` — accepts file upload (EPUB/TXT/PDF/HTML/MD), runs full `ingest_file` + all track extractors, returns project metadata
- Frontend: `ImportDialog.tsx` — file picker with optional title/author fields, upload progress, success state with "Open Project" button, error handling
- Wired into `ProjectPicker.tsx` — import dialog appears above project list
- Dependencies: installed `python-multipart` for FastAPI file upload support
- CORS updated: added ports 5174 for Vite fallback

**B01: Deterministic Annotation IDs**
- Replaced UUID-based IDs with SHA-256 hash-based IDs
- ID = `urn:palimpsest:{project}:{track}:{sha256(project+track+type+start+end)[:12]}`
- Same input always produces same output — enables reproducibility
- Removed `uuid` import from annotation model
- All 214 tests pass with new ID format

**B04: Legacy cleanup identified** — `src/` (412KB) and `ui/` (76MB) directories exist but have zero references from any code file. Safe to remove (left for user confirmation since 76MB deletion).

#### Category D: Endnote UI & Section Navigation

**D01-D02: Endnote Display**
- `AnnotationOverlay`: endnotes render as superscript numbers via `'superscript'` rendering mode
- `DetailPanel`: when EndnoteAnnotation selected, shows full note text in scrollable panel with distinctive red-bordered styling
- `buildAnnotationTitle`: endnote hover shows `"Endnote N: first 100 chars..."`
- `TrackManifest`: added `'superscript'` and `'none'` to rendering union

**D03: Section Navigation Sidebar**
- New `SectionNav.tsx` component: collapsible section list from sections track
- Click any section heading → smooth scroll to that section's paragraph
- Shows section count; hover highlights with purple accent
- Integrated into `AppLayout` above TrackPanel

#### Category F: Browser Polish

**F01: Error Boundaries**
- New `ErrorBoundary.tsx` class component wrapping TextLinearView, DetailPanel, DotplotView
- Catches render errors → shows error message + "Retry" button
- Prevents single-component crash from taking down entire browser

#### Category G: Spec Completion

**G01: annotation-model.md** — Complete spec with all 12 body types, evidence levels, selector types, ID format, namespacing rules. No longer a stub.

**G02: LFO.md** — Full Literary Feature Ontology spec with 25 terms across 4 categories (structural, entity, signal, structure), relationships (is_a, part_of, derives_from), JSON schema reference. No longer a stub.

**G03: signals.md** — Complete signal format spec documenting lithmm_meta.json, topics_dist.json, narrative_arc.json, rqa_metrics.json, embeddings.db schema, coordinates.json format. No longer a stub.

#### Files Modified/Created

**New files**:
- `browser/src/components/common/ImportDialog.tsx` — EPUB import UI
- `browser/src/components/common/SectionNav.tsx` — section navigation sidebar
- `browser/src/components/common/ErrorBoundary.tsx` — error boundary wrapper

**Modified files**:
- `core/palimpsest/server.py` — `/api/import` endpoint, CORS update
- `core/palimpsest/annotation/model.py` — deterministic hash-based IDs (B01)
- `browser/src/components/Layout/AppLayout.tsx` — SectionNav, ErrorBoundary integration
- `browser/src/components/common/ProjectPicker.tsx` — ImportDialog integration
- `browser/src/components/DetailPanel/DetailPanel.tsx` — endnote display
- `browser/src/components/TextLinearView/AnnotationOverlay.tsx` — endnote/section titles
- `browser/src/adapters/TrackManifest.ts` — superscript/none rendering modes
- `browser/src/utils/trackColors.ts` — sections/endnotes colors
- `specs/annotation-model.md` — complete (was 3-line stub)
- `specs/LFO.md` — complete (was 3-line stub)
- `specs/signals.md` — complete (was 3-line stub)

**Validation**:
- Python: 214 tests passing, 0 failures
- TypeScript: clean compile (0 errors)
- Vite build: 261.78 kB, 0 errors
- Browser UI live at localhost:5174 with import + navigation + endnote display

**Status**: Categories B (partial), D (D01-D03), F (F01), G (G01-G03) complete. Categories C, I01 completed same session (see below).

---

### 2026-06-09 — Category C: Semantic Zoom + I01 Doctor + F04 ARIA

**What happened**:
Implemented the 4-level semantic zoom system and remaining Category items.

#### Category C: Semantic Zoom (C01-C04)

**C01: Zoom State + Controls**
- `viewStore.ts` rewritten: `ZoomLevel = 'work' | 'chapter' | 'paragraph' | 'sentence'`
- `zoomIn()` and `zoomOut()` cycle through levels
- Toolbar zoom control: - / level label / + buttons
- Keyboard: `Ctrl+=` zoom in, `Ctrl+-` zoom out

**C02: Work-Level Renderer**
- Shows section blocks (from sections track or single "Full Text" block)
- Each block shows: heading, paragraph count, annotation density per track (colored badges)
- Click block → zooms to chapter level and scrolls to that section

**C03: Chapter-Level Renderer**
- Virtualized paragraph strip list (one line per paragraph)
- Shows: paragraph number, first 120 chars preview, colored track dots
- Click paragraph → zooms to paragraph level and scrolls to it

**C04: Sentence-Level Renderer**
- Expanded paragraph view with metadata header (word count, annotation count)
- Larger font, wider line spacing for close reading

**I01: Doctor Command**
- `palimpsest doctor` checks: Python version, spaCy (+ models), ebooklib, hmmlearn, BookNLP, Ollama, MLX embeddings, browser dist
- Reports OK / WARN / MISSING with color-coded output
- Suggests fix commands for missing dependencies

**F04: ARIA Accessibility**
- `role="switch"` + `aria-checked` + `aria-label` on track toggle rows
- `role="main"` + `role="complementary"` + `aria-label` on layout regions
- `tabIndex={0}` + keyboard activation (Enter/Space) on track toggles
- Help overlay updated with zoom shortcuts

**Files modified**:
- `browser/src/stores/viewStore.ts` — rewritten with 4-level zoom
- `browser/src/components/TextLinearView/TextLinearView.tsx` — 4 zoom renderers
- `browser/src/components/Layout/AppLayout.tsx` — zoom controls in toolbar, ARIA roles
- `browser/src/utils/keyboard.ts` — Ctrl+=/-  zoom shortcuts
- `browser/src/components/common/HelpOverlay.tsx` — zoom shortcut docs
- `browser/src/components/TrackPanel/TrackPanel.tsx` — ARIA attributes on toggles
- `core/palimpsest/cli.py` — doctor command

**Validation**:
- Python: 213 passed, 1 deselected (transient Ollama test), 0 regressions
- TypeScript: clean compile
- Vite build: 269.42 kB, 0 errors
- Doctor command: all checks pass except hmmlearn (WARN)

**Status**: All M1 Completion Plan categories implemented except H (formal test suite) and I02-I03 (pip packaging). Vision Gate test ready to execute on IJ.

---

### 2026-06-10 — Codebase Audit + Design Review + Roadmap v4.0

**What happened**:
Major design review session combining codebase audit, genome browser research, dot plot paper analysis, and UI redesign planning. Produced enriched roadmap v4.0 with new milestone (M2: Interactive Workbench) and expanded M1.5 (Browser Foundation Sprint).

#### Part 1: Codebase Audit Fix Sprint
- Spawned code-analyzer agent: found 2 CRITICAL, 4 ERROR, 11 WARNING issues
- All 15 fixes applied and validated (213 tests pass, TypeScript clean, Vite builds)
- Key fixes: epub endnote crash (C1), lithmm crash on small docs (C2), sentiment color field (E1), silent track failures (E2), Yule's K math (E3), O(n2)->bisect in alphabet (W2), recursion guard (W3), parallel track loading (W11)

#### Part 2: Research Expansion
- **4 dot plot papers** read and added to bibliography: ModDotPlot, Dotplotic, D-GENIES, ComplexHeatmap
- **5 genome browser papers** read and added: IGV (3 papers), IGB, igv.js
- All 9 papers copied to research library under `papers/dotplot-heatmap/` and `papers/genome-browsers/`
- Bibliography updated to 122+ entries across 5 domains

#### Part 3: Design Review & Orientation Report
- Comprehensive design review analyzing current UI against UCSC genome browser screenshots
- UCSC screenshots filed in `research/UI/screenshots/`
- Identified 23 UI gaps across 10 categories (highlights, layout, heatmap, barcode, coreference, alignment, analysis, tabs, tooltips, design quality)
- Produced structured report with phased fix plan (A-E)

#### Part 4: Genome Browser Research
- 3 research agents analyzed 8 genome browser platforms:
  - JBrowse 2: 8 view types, adapter/display separation, plugin architecture, MST session sharing, synteny/dotplot views
  - NCBI GDV + MCGV: dual-search, color-by dropdown, zoom gating, floating action cards, box-draw zoom
  - GIVE: Web Components embedding, named track groups, arc overlays
  - IGB: zoom stripe, animated semantic zoom, Color by heatmap, threshold slider
  - IGV: data tiling, pluggable renderers, 3-layer architecture
  - Hutton Tools: Tablet minimap, Flapjack genotype matrix, Strudel synteny ribbons
  - Artemis: suite decomposition, six-frame display, circular maps
- 19 transferable design patterns cataloged in roadmap v4.0

#### Part 5: Design Extraction MCP
- Evaluated 2 MCP tools: website-design-systems-mcp (rejected — static HTTP only) vs designlang (installed)
- **designlang v12.16.0** installed at `.scratch/design-extract/`
- Tested against UCSC Genome Browser: 30+ design token files extracted (colors, typography, spacing, Tailwind config, shadcn theme, Figma variables)
- Decision: use as CLI tool, not persistent MCP server (extraction is one-time per site; outputs are plain files)

#### Part 6: Roadmap v4.0
- Created doc 28: Development Roadmap v4.0
- Key structural changes:
  - M1 gains M1.5 (Browser Foundation Sprint): component library, multi-tab layout, tooltips, responsive barcode, highlight toggle fix
  - NEW M2 (Interactive Workbench): TextHiC interactive heatmap, character entity system, analysis workbench UI
  - Old M2 (Two Texts) -> M3, old M3 -> M4, old M4 -> M5, old M5 -> M6
  - Total timeline: 49 weeks (was 39)
- Design patterns catalog with 19 patterns from 8 genome browsers
- 10 risk register entries (was 6)
- 3 new design principles added

**Documents produced**:
- `research/domain-synthesis/28-development-roadmap-v4.md` — enriched 6-milestone roadmap
- `research/UI/genome-browser-reports/00-index.md` — genome browser research index
- `research/UI/design-tokens/ucsc/` — extracted UCSC design tokens (30+ files)
- Bibliography updated with 9 new papers (122+ total)
- DOCUMENT-MAP updated

**Status**: Roadmap v4.0 ready for review. M1.5 (Browser Foundation Sprint) is the immediate next phase. designlang installed and tested.

---

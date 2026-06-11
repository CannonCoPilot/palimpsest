# Document 27: M1 Completion Implementation Plan

**Version**: 1.1 (updated 2026-06-10)
**Date**: 2026-06-08 (v1.0); 2026-06-10 (v1.1 — completion status updated, M1.5 reference added)
**Status**: Categories A-G, I01 COMPLETE. H (testing) and I02-I03 (packaging) deferred to M1.5. See Roadmap v4.0 (doc 28) for M1.5 Browser Foundation Sprint.
**Supersedes**: Portions of Doc 14 (Phase 1 Plan) for remaining M1 work
**References**: Doc 26 (Exit Criteria), Doc 22 (PRD v1.1), Doc 24 (M1 Roadmap-PRD v1.2), Doc 28 (Roadmap v4.0), Doc 16 (Checkpoint Review)

---

## 1. Scope

This document covers ALL remaining work to bring Milestone 1 from its current state (M1.3b functionally complete + Tier 1 Vision Gate features implemented) to the M1 exit criteria defined in Doc 26. It supersedes the remaining task estimates in Doc 14 and the T30-T37 tasks in the phase1-tasks index for this final sprint.

### 1.1 What's Already Done

| Capability | Status | Evidence |
|-----------|--------|---------|
| 13 track extractors (entities, sentiment, lexical, syntax, dialogue, topics, narrative_arc, rqa, coreference, self_similarity, lithmm, alphabet, compartments) | Complete | 214 tests passing |
| CLI: ingest, info, analyze, serve | Complete | Functional |
| FastAPI server: /api/projects, /api/tracks, /api/summarize, /api/search, /api/explain | Complete | Functional |
| Browser: TextLinearView, AnnotationOverlay, DetailPanel, TrackPanel, OverviewBar, TextSearch, DotplotView, LLMSummary, StateExplainer | Complete | TypeScript compiles, Vite builds |
| Track-specific rendering (color-band, highlight, underline, margin-marker) | Complete | Implemented 2026-06-08 |
| Search match highlighting | Complete | Implemented 2026-06-08 |
| Virtual scrolling (@tanstack/react-virtual) | Complete | Implemented 2026-06-08 |
| AI state explanation (/api/explain + StateExplainer) | Complete | Implemented 2026-06-08 |
| W3C annotation JSONL format | Complete | All tracks produce valid JSONL |
| LFO v0.1 (22 terms) | Complete | specs/lfo-v0.1.json |
| PAF v0.1 spec | Complete | specs/paf-v0.1.md |
| VectorStore + sqlite-vec embeddings | Complete | Functional |

### 1.2 What Remains

| Category | Item Count | Estimated Effort |
|----------|-----------|-----------------|
| A. EPUB Structural Import Pipeline | 8 tasks | ~20 hours |
| B. Audit Remediation (Phase A — blocking) | 5 tasks | ~8 hours |
| C. Semantic Zoom | 4 tasks | ~12 hours |
| D. Endnote UI & Section Navigation | 4 tasks | ~10 hours |
| E. Export Implementation | 3 tasks | ~8 hours |
| F. Browser Polish & Accessibility | 5 tasks | ~10 hours |
| G. Spec Completion & Documentation | 4 tasks | ~8 hours |
| H. Testing & Verification | 5 tasks | ~14 hours |
| I. Packaging & Distribution | 3 tasks | ~6 hours |
| **Total** | **41 tasks** | **~96 hours** |

At 6 productive hours per session, this is approximately 16 sessions of focused work.

---

## 2. EPUB Pipeline Design

### 2.1 Architecture

The EPUB import pipeline extends the existing ingestion system. The current flow:

```
file.epub → extractor.py (ebooklib → raw text) → normalizer.py → reference.txt
```

The new flow adds structural extraction:

```
file.epub → epub_parser.py:
  ├── OPF metadata → metadata.json (enhanced)
  ├── Spine traversal → clean text assembly with offset map
  │   ├── reference.txt (clean narrative text, endnotes appended with separator)
  │   ├── Section boundaries (h1-h6 headings) → tracks/sections.jsonl
  │   └── Endnote pairs (anc ↔ sym) → tracks/endnotes.jsonl
  ├── coordinates.json (section_index mapping added)
  └── normalizer.py → SHA-256, Unicode NFC
```

### 2.2 EPUB Parser Design (Based on Infinite Jest EPUB Analysis)

**Input characteristics** (from actual IJ EPUB examination):
- EPUB 2.0, Calibre-converted, 21 HTML split files (not chapter-aligned)
- 67 section headings as `<h3 class="calibre7">` (date/time format)
- 388 endnotes with bidirectional `sdendnote{N}anc` ↔ `sdendnote{N}sym` links
- Multi-paragraph endnotes (e.g., endnote 24: Filmography)
- Endnote number duplication artifact (bare sup before linked sup)
- CSS classes are Calibre-generic (calibre5-calibre27), not semantic

**Parser strategy**:

1. **Phase 1: Metadata Extraction**
   - Read content.opf (or package.opf) via ebooklib
   - Extract: title, author, publisher, date, ISBN, language, UUID
   - Store in metadata.json alongside computed fields (word_count, etc.)

2. **Phase 2: Spine Traversal & Text Assembly**
   - Iterate spine items in reading order (not manifest order)
   - For each HTML document:
     - Parse with html.parser or BeautifulSoup (lxml)
     - Walk DOM tree in document order
     - For each text node: append to reference text, recording (html_file, element_id, char_offset) mapping
     - For `<h1>`-`<h6>` elements: record section boundary at current offset
     - For endnote anchor elements (class=sdendnoteanc, id pattern sdendnote{N}anc):
       record call-site position
     - For endnote definition elements (id pattern sdendnote{N}sym):
       record endnote start, collect text until next sym anchor
   - Strip all HTML tags; preserve paragraph breaks (double-newline between block elements)
   - Handle whitespace normalization (collapse runs, trim)

3. **Phase 3: Endnote Extraction**
   - Separate endnote text from narrative text:
     - Option A: Endnotes appended after a `\n\n---ENDNOTES---\n\n` separator
     - Option B: Endnotes in a separate `endnotes.txt` file
     - **Decision: Option A** — endnotes are part of the text (Wallace intended them as integral to reading), but the separator allows tracks to distinguish them
   - For each endnote (1-388):
     - Extract full note text (multi-paragraph: all p elements between sym N and sym N+1)
     - Record call-site character offset (from Phase 2 anc position)
     - Record note-text character offset (from Phase 2 sym position)
     - Create W3C annotation with body type `palimpsest:EndnoteAnnotation`
   - Handle endnote number duplication: if bare `<sup>N</sup>` immediately precedes linked `<a...><sup>N</sup></a>`, discard the bare one

4. **Phase 4: Section Boundary Extraction**
   - For each heading recorded in Phase 2:
     - Create W3C annotation with body type `palimpsest:SectionAnnotation`
     - Body includes: heading text, heading level (h1=1, h3=3), section index
     - Target: TextPositionSelector at the heading's character offset
   - Generate section entries in coordinates.json: `{section_index: N, start_offset: X, end_offset: Y, heading: "..."}`

5. **Phase 5: Coordinate System Assembly**
   - Update coordinates.json with:
     - `character_offset` (identity, always present)
     - `paragraph_index` (from segmenter)
     - `section_index` (from Phase 4)
     - `endnote_region` (boolean: is this offset in the endnotes section?)

### 2.3 Fallback Behavior

| Input Format | Section Detection | Endnote Detection | Metadata Source |
|-------------|-------------------|-------------------|-----------------|
| EPUB | HTML heading elements | Endnote anchor patterns | OPF metadata |
| HTML | h1-h6 elements | Footnote/endnote link patterns | meta tags |
| PDF | Heuristic (caps, font size via pymupdf) | None (not reliably extractable) | PDF metadata |
| TXT | TextTiling segmentation | None | Filename + word count |
| Markdown | # heading markers | None | YAML frontmatter if present |

---

## 3. Atomized Task List

Tasks are organized by category, then by dependency order within each category. Each task specifies:
- **ID**: Category letter + sequential number (e.g., A01)
- **Title**: What is built
- **Dependencies**: Which tasks must complete first
- **Acceptance Criteria**: Observable outcomes (BDD-aligned)
- **Effort**: Estimated hours

### Category A: EPUB Structural Import Pipeline

```
A01  EPUB Metadata Extractor
     Deps: None
     Effort: 2h
     ─────────────────────────────────────────────
     Create core/palimpsest/ingest/epub_parser.py.
     Implement parse_epub_metadata(epub_path) → dict with:
       title, author, publisher, date, isbn, language, uuid.
     Uses ebooklib to read OPF.
     Returns dict compatible with metadata.json schema.

     Acceptance:
     - [ ] Extracts correct metadata from IJ EPUB
     - [ ] Returns empty strings (not errors) for missing fields
     - [ ] Test: test_epub_metadata_extraction

A02  EPUB Text Assembly with Offset Mapping
     Deps: A01
     Effort: 4h
     ─────────────────────────────────────────────
     Implement epub_to_text(epub_path) → (clean_text, offset_map, headings, endnote_anchors).
     Traverses spine items in reading order.
     Strips HTML tags while building character offset map.
     Records heading positions (h1-h6) and endnote anchor positions.
     Handles Calibre split files (cross-file reference resolution).
     Deduplicates bare-sup endnote number artifacts.
     Normalizes whitespace: collapse runs, double-newline between block elements.

     Acceptance:
     - [ ] Produces clean text from IJ EPUB matching expected word count (~484,000)
     - [ ] Heading offsets point to correct positions in clean text
     - [ ] Endnote anchor offsets point to correct call-site positions
     - [ ] No HTML tags in output text
     - [ ] Test: test_epub_text_assembly, test_epub_offset_mapping

A03  Endnote Extraction and Annotation
     Deps: A02
     Effort: 3h
     ─────────────────────────────────────────────
     Implement extract_endnotes(epub_path, offset_map) → list[Annotation].
     For each endnote (identified by sdendnote{N}sym pattern):
       - Extract full note text (multi-paragraph grouping)
       - Resolve call-site offset from anc ↔ sym bidirectional link
       - Create W3C annotation: body type palimpsest:EndnoteAnnotation
         with palimpsest:noteNumber, palimpsest:noteText,
         palimpsest:callSiteStart, palimpsest:callSiteEnd
     Handle edge cases: multi-paragraph endnotes (e.g., #24 Filmography),
     sub-notes (e.g., #387 with lettered sub-note).

     Acceptance:
     - [ ] Extracts exactly 388 endnotes from IJ EPUB
     - [ ] Endnote 1 text contains "Methamphetamine hydrochloride"
     - [ ] Endnote 24 text contains "JAMES O. INCANDENZA: A FILMOGRAPHY"
     - [ ] Call-site offsets are valid positions in reference.txt
     - [ ] Test: test_endnote_extraction, test_endnote_count

A04  Section Boundary Extraction and Annotation
     Deps: A02
     Effort: 2h
     ─────────────────────────────────────────────
     Implement extract_sections(headings, offset_map) → list[Annotation].
     For each heading from A02:
       - Create W3C annotation: body type palimpsest:SectionAnnotation
         with palimpsest:headingText, palimpsest:headingLevel, palimpsest:sectionIndex
       - Target: TextPositionSelector at heading position
     Assign sequential section indices.

     Acceptance:
     - [ ] Extracts 67 section boundaries from IJ EPUB (+ 1 for book title = 68 total)
     - [ ] First section heading is "YEAR OF GLAD"
     - [ ] Section indices are sequential 0-67
     - [ ] Test: test_section_extraction, test_section_count

A05  Integrate EPUB Parser into Ingestion Pipeline
     Deps: A01, A02, A03, A04
     Effort: 3h
     ─────────────────────────────────────────────
     Update core/palimpsest/ingest/extractor.py:
       - Route .epub files to epub_parser instead of ebooklib raw extraction
       - After text extraction, run normalizer as before
       - Write tracks/sections.jsonl and tracks/endnotes.jsonl
       - Write enhanced metadata.json with EPUB-sourced fields
     Update coordinates.json generation to include section_index mapping.
     Ensure backward compatibility: TXT/PDF/HTML/Markdown paths unchanged.

     Acceptance:
     - [ ] `palimpsest ingest ij.epub` produces complete project directory
     - [ ] metadata.json contains isbn, publisher, date from EPUB
     - [ ] tracks/sections.jsonl exists with 67+ annotations
     - [ ] tracks/endnotes.jsonl exists with 388 annotations
     - [ ] coordinates.json contains section_index mapping
     - [ ] `palimpsest ingest novel.txt` still works identically
     - [ ] Test: test_epub_ingest_integration, test_txt_ingest_unchanged

A06  Endnote Annotation Body Type and LFO Terms
     Deps: A03
     Effort: 1h
     ─────────────────────────────────────────────
     Add palimpsest:EndnoteAnnotation and palimpsest:SectionAnnotation
     to annotation body types in core/palimpsest/annotation/bodies.py.
     Add LFO terms: structure.endnote, structure.section_boundary,
     structure.heading to specs/lfo-v0.1.json.
     Update BODY_TYPE_TO_TRACK mapping in browser AnnotationOverlay.tsx.

     Acceptance:
     - [ ] Body types serialize/deserialize correctly in JSONL
     - [ ] LFO JSON validates (no duplicate terms, correct hierarchy)
     - [ ] Browser recognizes new body types for track coloring
     - [ ] Test: test_endnote_body_type, test_section_body_type

A07  EPUB Ingestion Tests with IJ Content
     Deps: A05
     Effort: 3h
     ─────────────────────────────────────────────
     Create test fixtures from IJ EPUB:
       - Extract first 3 sections (~20KB) as test EPUB subset
       - Include endnotes 1-10 for endnote testing
     Write comprehensive test suite: test_epub_pipeline.py
       - Metadata extraction
       - Text assembly correctness
       - Section boundary positions
       - Endnote extraction (count, content, offsets)
       - Round-trip: ingest → load project → verify structure
       - Edge cases: empty headings, nested endnotes, missing images

     Acceptance:
     - [ ] All EPUB pipeline tests pass
     - [ ] Tests use real IJ content (not synthetic)
     - [ ] Edge cases covered: multi-paragraph endnotes, sub-notes
     - [ ] Test: full test_epub_pipeline.py suite

A08  Full IJ Ingest Smoke Test
     Deps: A07
     Effort: 2h
     ─────────────────────────────────────────────
     Run full Infinite Jest EPUB through complete pipeline:
       palimpsest ingest <ij.epub>
     Verify:
       - All 12+ tracks compute (sections, endnotes, + 12 Base)
       - Total time under 15 minutes
       - No errors or warnings
       - Browser loads and renders correctly
     Document any IJ-specific edge cases encountered.

     Acceptance:
     - [ ] Full IJ EPUB ingests successfully
     - [ ] 14+ tracks in project directory (12 Base + sections + endnotes)
     - [ ] Browser renders IJ text with all tracks
     - [ ] Documented in development-history.md
```

### Category B: Audit Remediation (Phase A — Blocking)

```
B01  Deterministic Annotation IDs
     Deps: None
     Effort: 2h
     ─────────────────────────────────────────────
     Replace UUID-based annotation IDs with deterministic hash-based IDs.
     ID = SHA-256(project_id + track_name + target.start + target.end + body.type)[:16]
     Prefix with track name: "entities-a3f2b1c8d9e0f1a2"
     Update annotation.py, all track extractors, and tests.
     Audit finding C4.

     Acceptance:
     - [ ] Same input produces same annotation IDs across runs
     - [ ] No ID collisions in any existing test fixture
     - [ ] All 214+ tests still pass
     - [ ] Test: test_deterministic_ids

B02  Exception Handling Audit
     Deps: None
     Effort: 2h
     ─────────────────────────────────────────────
     Audit all bare `except:` and `except Exception:` blocks.
     Audit finding C1 (silent error swallowing).
     Replace with:
       - Specific exception types where possible
       - Logging with context (logger.warning with track name, file, offset)
       - Re-raise for truly unexpected errors
     Never silently swallow errors that indicate data corruption.

     Acceptance:
     - [ ] Zero bare `except:` blocks in core/ directory
     - [ ] All `except Exception:` blocks log with context
     - [ ] Critical errors (file not found, parse failure) are raised, not swallowed
     - [ ] Test: existing tests still pass (no behavior change for valid inputs)

B03  spaCy Fallback Path Testing
     Deps: None
     Effort: 1h
     ─────────────────────────────────────────────
     Audit finding C3: ensure all tracks that use spaCy degrade gracefully
     when spaCy model is not installed.
     Test by temporarily removing spaCy from path.
     Verify: tracks that need spaCy skip with clear warning message;
     tracks that don't need spaCy still compute.

     Acceptance:
     - [ ] Without spaCy: entities, syntax, coreference tracks skip with warning
     - [ ] Without spaCy: sentiment, lexical, topics, lithmm tracks still compute
     - [ ] Warning messages suggest `python -m spacy download en_core_web_sm`
     - [ ] Test: test_spacy_fallback

B04  Legacy Directory Cleanup
     Deps: None
     Effort: 1h
     ─────────────────────────────────────────────
     Audit finding E3, E4: remove legacy directories and files.
     Delete: src/ (old pre-core code), ui/ (old pre-browser code),
     tauri.conf.json (v4.0 abandoned Tauri architecture).
     Update .gitignore if needed.

     Acceptance:
     - [ ] src/ directory removed
     - [ ] ui/ directory removed
     - [ ] tauri.conf.json removed
     - [ ] No broken imports referencing removed paths
     - [ ] All tests pass

B05  Dead State and Code Removal
     Deps: B04
     Effort: 2h
     ─────────────────────────────────────────────
     Remove unused code identified in audit:
     - Unused Zustand state fields (audit finding W1)
     - Unused imports
     - Dead CSS classes
     - Commented-out code blocks
     Run TypeScript strict check; fix any newly-surfaced issues.

     Acceptance:
     - [ ] No unused exports in browser/src/**
     - [ ] tsc --noEmit passes with zero warnings
     - [ ] No commented-out code blocks in core/ or browser/src/
```

### Category C: Semantic Zoom

```
C01  Zoom Level State and Controls
     Deps: None
     Effort: 2h
     ─────────────────────────────────────────────
     ViewStore already has zoomLevel: 'close' | 'medium' | 'far'.
     Expand to 4 levels: 'work' | 'chapter' | 'paragraph' | 'sentence'.
     Add zoom controls to browser toolbar:
       - Zoom in/out buttons
       - Zoom level indicator (text label)
       - Keyboard shortcuts (Ctrl+= zoom in, Ctrl+- zoom out)

     Acceptance:
     - [ ] 4 zoom levels cycle correctly
     - [ ] Zoom control buttons visible in toolbar
     - [ ] Keyboard shortcuts work
     - [ ] Current zoom level displayed

C02  Work-Level Zoom Renderer
     Deps: C01
     Effort: 3h
     ─────────────────────────────────────────────
     At work level: render chapter/section blocks (not individual paragraphs).
     Each section shows: heading text, paragraph count, track density sparklines.
     Click a section → zoom to chapter level centered on that section.
     Uses section annotations from sections.jsonl (or segments track fallback).

     Acceptance:
     - [ ] Work level shows section blocks with headings
     - [ ] Track sparklines visible per section
     - [ ] Click section → transitions to chapter level
     - [ ] Documents without sections show paragraph-range blocks

C03  Chapter-Level Zoom Renderer
     Deps: C01
     Effort: 3h
     ─────────────────────────────────────────────
     At chapter level: render paragraph strips with track barcodes.
     Each paragraph shows: first line of text (truncated), colored track indicators.
     Annotations shown as compressed barcode marks (not full inline rendering).
     Click a paragraph → zoom to paragraph level.

     Acceptance:
     - [ ] Chapter level shows paragraph strips
     - [ ] Track colors visible as barcode marks
     - [ ] Click paragraph → transitions to paragraph level
     - [ ] Scrolling is smooth at chapter level

C04  Zoom Transition Animation
     Deps: C02, C03
     Effort: 4h
     ─────────────────────────────────────────────
     Smooth transitions between zoom levels:
       - Animate scale change (CSS transform or canvas)
       - Maintain scroll position context (the passage you're looking at
         stays in view across zoom transitions)
       - Track renderers switch based on zoom level

     Acceptance:
     - [ ] Zoom in/out transitions are smooth (not abrupt page replacement)
     - [ ] Scroll position preserved across transitions
     - [ ] Track rendering mode changes at each level
```

### Category D: Endnote UI & Section Navigation

```
D01  Endnote Rendering in AnnotationOverlay
     Deps: A06
     Effort: 3h
     ─────────────────────────────────────────────
     In AnnotationOverlay: detect endnote call-site annotations.
     Render as superscript number (not colored span).
     textViewRendering mode: 'superscript' (add to TrackManifest union).
     Endnote numbers match the palimpsest:noteNumber field.

     Acceptance:
     - [ ] Endnote markers render as superscript numbers in text
     - [ ] Numbers match the original endnote numbering
     - [ ] Clicking a number triggers endnote display (D02)
     - [ ] Visual style: subtle but visible (not overwhelming)

D02  Endnote Display Panel
     Deps: D01
     Effort: 3h
     ─────────────────────────────────────────────
     When user clicks an endnote marker:
       - Show endnote text in DetailPanel (or a dedicated EndnotePanel)
       - Include note number, full text, and "Back to text" link
       - Preserve user's scroll position in main text
     For long endnotes (e.g., #24 Filmography): scrollable within panel.

     Acceptance:
     - [ ] Click endnote 1 → shows "Methamphetamine hydrochloride..."
     - [ ] Click endnote 24 → shows full Filmography (scrollable)
     - [ ] "Back to text" returns to call-site position
     - [ ] Main text scroll position unchanged after viewing endnote

D03  Section Navigation Sidebar
     Deps: A04
     Effort: 2h
     ─────────────────────────────────────────────
     Add a collapsible section list to the browser:
       - Lists all section headings from sections.jsonl
       - Click heading → scroll to that section
       - Current section highlighted as user scrolls
     Accessible via button in toolbar or keyboard shortcut.

     Acceptance:
     - [ ] Section list shows all 67 IJ section headings
     - [ ] Click heading → smooth scroll to section start
     - [ ] Current section highlighted during scroll
     - [ ] Section list is collapsible (doesn't consume space when hidden)

D04  Section Markers in OverviewBar
     Deps: A04
     Effort: 2h
     ─────────────────────────────────────────────
     Render section boundaries as vertical tick marks in the OverviewBar.
     Endnote density shown as a secondary indicator.
     Click a section tick → scroll to that section.

     Acceptance:
     - [ ] Section boundaries visible as ticks in OverviewBar
     - [ ] Ticks are clickable → scroll to section
     - [ ] Endnote region visually distinct from narrative region
```

### Category E: Export Implementation

```
E01  W3C Web Annotation JSON-LD Export
     Deps: None
     Effort: 3h
     ─────────────────────────────────────────────
     Implement `palimpsest export --format w3c <project>`.
     Output: valid JSON-LD with:
       - @context including W3C Web Annotation and palimpsest namespaces
       - AnnotationCollection wrapping all annotations
       - Every annotation with proper id, body, target, creator, generated
     Validate against W3C WADM spec.

     Acceptance:
     - [ ] Export produces valid JSON-LD
     - [ ] @context includes w3.org/ns/anno and palimpsest namespace
     - [ ] All tracks represented in collection
     - [ ] Round-trip: export → re-import produces identical annotations
     - [ ] Test: test_w3c_export, test_w3c_roundtrip

E02  PAF TSV Export
     Deps: None
     Effort: 3h
     ─────────────────────────────────────────────
     Implement `palimpsest export --format paf <project>`.
     Output: TSV file per paf-v0.1.md spec.
     Currently prints "not implemented" (audit finding E1).
     Columns: chrom, source, type, start, end, score, strand, phase, attributes.

     Acceptance:
     - [ ] Export produces valid PAF TSV
     - [ ] Validates against paf-v0.1.md spec
     - [ ] All tracks represented
     - [ ] Test: test_paf_export, test_paf_validation

E03  CSV Export (Simple Tabular)
     Deps: None
     Effort: 2h
     ─────────────────────────────────────────────
     Implement `palimpsest export --format csv <project>`.
     Output: one CSV per track, with columns appropriate to track type.
     For scholars who want to work in Excel/R/pandas.

     Acceptance:
     - [ ] One CSV per track in export directory
     - [ ] Headers match track-specific fields
     - [ ] Opens correctly in Excel/Numbers
     - [ ] Test: test_csv_export
```

### Category F: Browser Polish & Accessibility

```
F01  Error Boundaries
     Deps: None
     Effort: 2h
     ─────────────────────────────────────────────
     Add React error boundaries around:
       - TextLinearView (catch annotation rendering errors)
       - DotplotView (catch Canvas rendering errors)
       - DetailPanel (catch malformed annotation display)
     Each boundary shows: error message, "reload" button, error details (collapsed).

     Acceptance:
     - [ ] Malformed annotation doesn't crash entire browser
     - [ ] Error boundary shows helpful message
     - [ ] "Reload" button recovers gracefully

F02  Loading States and Spinners
     Deps: None
     Effort: 2h
     ─────────────────────────────────────────────
     Show loading indicators for:
       - Project loading (track computation progress)
       - AI summary generation
       - AI state explanation
       - Search execution
     Use projectStore.loadingStep for progress text.

     Acceptance:
     - [ ] Loading spinner visible during project load
     - [ ] Progress text shows current step ("Loading tracks...", "Computing LitHMM...")
     - [ ] No blank/empty states during async operations

F03  Keyboard Navigation
     Deps: None
     Effort: 2h
     ─────────────────────────────────────────────
     Keyboard shortcuts for:
       - 1-9: toggle tracks by index
       - Ctrl+F: open search (already done)
       - Escape: close panels/search (already done)
       - Arrow keys: navigate between paragraphs
       - Enter: select current paragraph
       - ?: show help overlay
     Audit findings W4-W5.

     Acceptance:
     - [ ] Number keys toggle tracks
     - [ ] Arrow keys navigate paragraphs
     - [ ] Help overlay lists all shortcuts
     - [ ] No keyboard traps

F04  ARIA Labels and Screen Reader Support
     Deps: F03
     Effort: 2h
     ─────────────────────────────────────────────
     Add ARIA attributes:
       - role="main" on reading area
       - aria-label on track toggle buttons
       - aria-live on search results count
       - aria-selected on selected paragraph
       - role="complementary" on DetailPanel
     Audit findings W6-W9.

     Acceptance:
     - [ ] VoiceOver reads track names when toggling
     - [ ] Search match count announced on change
     - [ ] Panel roles identified correctly

F05  Responsive Layout
     Deps: None
     Effort: 2h
     ─────────────────────────────────────────────
     Browser layout adjusts for different viewport sizes:
       - < 768px: single column (reading area fills width, panels as overlays)
       - 768-1200px: reading area + track panel (no detail panel until selection)
       - > 1200px: full three-column layout
     DetailPanel and TrackPanel collapse to slide-out drawers on small viewports.

     Acceptance:
     - [ ] Readable on 768px viewport
     - [ ] No horizontal scrolling at any viewport width
     - [ ] Panels collapse gracefully on small screens
```

### Category G: Spec Completion & Documentation

```
G01  Annotation Model Spec (Full)
     Deps: A06
     Effort: 2h
     ─────────────────────────────────────────────
     Complete specs/annotation-model.md (currently a 3-line stub).
     Document all palimpsest body types:
       EntityAnnotation, SentimentAnnotation, LexicalAnnotation, etc.
     Document evidence levels E1-E5.
     Document the W3C compliance model.
     Include examples for each body type.

     Acceptance:
     - [ ] Every body type documented with fields and examples
     - [ ] Evidence levels defined with criteria
     - [ ] W3C compliance notes included
     - [ ] Not a stub

G02  LFO Spec (Full)
     Deps: A06
     Effort: 2h
     ─────────────────────────────────────────────
     Complete specs/LFO.md (currently a 3-line stub).
     Document the Literary Feature Ontology:
       - Term hierarchy (is_a, part_of, derives_from relationships)
       - All 22+ terms from lfo-v0.1.json
       - New terms for sections and endnotes
       - Relationship to Sequence Ontology
     Include JSON Schema definition.

     Acceptance:
     - [ ] All LFO terms documented with definitions
     - [ ] Hierarchy diagram or table
     - [ ] JSON Schema provided
     - [ ] Not a stub

G03  Signals Spec (Full)
     Deps: None
     Effort: 2h
     ─────────────────────────────────────────────
     Complete specs/signals.md (currently a 3-line stub).
     Document signal file formats:
       - lithmm_meta.json schema
       - self-similarity matrix format
       - embeddings.db schema (sqlite-vec)
       - coordinates.json schema
     Include examples.

     Acceptance:
     - [ ] All signal formats documented
     - [ ] JSON Schema for each signal type
     - [ ] Examples from actual computed data
     - [ ] Not a stub

G04  WALKTHROUGH + README Update
     Deps: A05, E01
     Effort: 2h
     ─────────────────────────────────────────────
     Update WALKTHROUGH.md:
       - Add EPUB import instructions
       - Update CLI commands (export, doctor)
       - Add browser feature descriptions (zoom, endnotes, search)
     Update README.md:
       - Installation instructions (pip install, spaCy model, Ollama)
       - Quick start guide
       - Feature overview with screenshots

     Acceptance:
     - [ ] WALKTHROUGH covers complete user journey from EPUB to browser
     - [ ] README installation instructions work from clean environment
     - [ ] No references to removed/renamed features
```

### Category H: Testing & Verification

```
H01  Browser Unit Tests (Vitest)
     Deps: None
     Effort: 4h
     ─────────────────────────────────────────────
     Set up Vitest for browser/src/.
     Write unit tests for:
       - All Zustand stores (projectStore, trackStore, viewStore, searchStore)
       - AnnotationAdapter (JSONL parsing)
       - TrackManifest (loading, defaults)
       - AnnotationOverlay (span building with different rendering modes)
     Mock fetch for API calls.

     Acceptance:
     - [ ] Vitest configured and running
     - [ ] Store tests cover: initial state, mutations, edge cases
     - [ ] Adapter tests cover: valid JSONL, malformed lines, empty input
     - [ ] All browser tests pass

H02  Playwright E2E Tests
     Deps: H01
     Effort: 4h
     ─────────────────────────────────────────────
     Set up Playwright for browser E2E testing.
     Write scenarios matching BDD user stories:
       - Load project → verify track panel shows tracks
       - Click annotation → verify DetailPanel shows properties
       - Search → verify highlights appear
       - Click endnote → verify note text displays
       - Zoom controls → verify rendering changes
     Use test fixture project (P&P Chapter 1 or IJ sample).

     Acceptance:
     - [ ] Playwright configured with test fixture server
     - [ ] At least 5 E2E scenarios automated
     - [ ] Tests run in CI-compatible headless mode
     - [ ] All Playwright tests pass

H03  Python Test Coverage Expansion
     Deps: A07, B01, E01, E02
     Effort: 3h
     ─────────────────────────────────────────────
     Expand Python test suite to cover new features:
       - EPUB pipeline tests (A07)
       - Deterministic ID tests (B01)
       - Export tests (W3C, PAF, CSV)
       - Server endpoint tests (/api/explain)
     Target: >80% coverage on core/palimpsest/.

     Acceptance:
     - [ ] Coverage report generated (pytest-cov)
     - [ ] Core modules > 80% coverage
     - [ ] All new features have tests
     - [ ] Total test count > 250

H04  IJ Integration Smoke Test
     Deps: A08, H02
     Effort: 2h
     ─────────────────────────────────────────────
     Full end-to-end test with Infinite Jest:
       1. Ingest IJ EPUB
       2. Verify all tracks computed
       3. Start server
       4. Load in browser
       5. Execute Vision Gate test sequence (Doc 26 §5.4)
     Document results and any issues.

     Acceptance:
     - [ ] Vision Gate test sequence passes (10/10 steps)
     - [ ] Results documented in development-history.md
     - [ ] Any issues logged and tracked

H05  Regression Test Suite
     Deps: H03
     Effort: 1h
     ─────────────────────────────────────────────
     Create a single `make test` or `pytest` invocation that runs:
       - All Python unit tests
       - All browser Vitest tests
       - Playwright E2E tests (headless)
     Document in WALKTHROUGH.md.

     Acceptance:
     - [ ] Single command runs full test suite
     - [ ] Exit code 0 = all pass, nonzero = failure
     - [ ] Documented in WALKTHROUGH.md
```

### Category I: Packaging & Distribution

```
I01  palimpsest doctor Command
     Deps: None
     Effort: 2h
     ─────────────────────────────────────────────
     Implement `palimpsest doctor` CLI command.
     Checks:
       - Python version (>= 3.11)
       - spaCy installed and en_core_web_sm model available
       - ebooklib installed (for EPUB support)
       - Ollama running (optional, with status message)
       - hmmlearn installed (for LitHMM)
       - Browser dist available
     Reports: green checkmarks for available, yellow warnings for optional missing,
     red errors for required missing. Suggests install commands.

     Acceptance:
     - [ ] Reports all dependency statuses
     - [ ] Suggests fix commands for missing deps
     - [ ] Works with and without optional dependencies
     - [ ] Test: test_doctor_command

I02  Bundle Browser Dist in Package
     Deps: None
     Effort: 2h
     ─────────────────────────────────────────────
     Pre-build browser dist and include in pip package.
     Update server.py to find dist from installed package location,
     not just relative to source checkout.
     Use importlib.resources or pkg_resources for path resolution.

     Acceptance:
     - [ ] `pip install .` includes browser dist
     - [ ] `palimpsest serve` works from installed package (not just dev checkout)
     - [ ] Browser loads correctly from installed dist

I03  pyproject.toml Optional Dependency Groups
     Deps: I01
     Effort: 2h
     ─────────────────────────────────────────────
     Define optional dependency groups in pyproject.toml:
       [project.optional-dependencies]
       epub = ["ebooklib>=0.18"]
       ai = ["ollama"]
       booknlp = ["booknlp>=1.0"]
       full = ["ebooklib>=0.18", "ollama", "booknlp>=1.0"]
     Core install: minimal deps (spaCy, scikit-learn, fastapi, uvicorn).
     `pip install palimpsest[full]` gets everything.

     Acceptance:
     - [ ] `pip install palimpsest` works (core only)
     - [ ] `pip install palimpsest[epub]` adds ebooklib
     - [ ] `pip install palimpsest[full]` adds all optional deps
     - [ ] `palimpsest doctor` reports which groups are installed
```

---

## 4. Dependency Graph

```
                    ┌─────────────┐
                    │ A01 Metadata │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │ A02 Assembly │
                    └──┬───┬───┬──┘
                       │   │   │
              ┌────────┘   │   └────────┐
              │            │            │
       ┌──────▼──────┐ ┌──▼───────┐ ┌──▼──────────┐
       │ A03 Endnote │ │ A04 Sect │ │ A06 Body/LFO │
       └──────┬──────┘ └──┬───────┘ └──────────────┘
              │            │
              └─────┬──────┘
                    │
             ┌──────▼──────┐
             │ A05 Integrate│
             └──────┬──────┘
                    │
             ┌──────▼──────┐
             │ A07 Tests    │──────────┐
             └──────┬──────┘          │
                    │                  │
             ┌──────▼──────┐   ┌──────▼──────┐
             │ A08 IJ Smoke│   │ H03 Coverage│
             └─────────────┘   └─────────────┘

  ┌──────┐ ┌──────┐ ┌──────┐     (independent of A-chain)
  │ B01  │ │ B02  │ │ B03  │
  │ IDs  │ │ Exns │ │spaCy │
  └──────┘ └──────┘ └──────┘
  ┌──────┐
  │ B04  │──→ B05
  │Legacy│
  └──────┘

  C01 → C02, C03 → C04

  A06 → D01 → D02
  A04 → D03, D04

  E01, E02, E03 (independent)

  F01-F05 (independent)

  G01-G04 (independent, G01 needs A06)

  H01 → H02
  A07+B01+E01+E02 → H03
  A08+H02 → H04
  H03 → H05

  I01-I03 (independent)
```

---

## 5. Implementation Phases

Tasks grouped into phases for execution order. Within each phase, tasks can be parallelized.

### Phase 1: EPUB Pipeline Foundation (A01-A05, A06)
**Goal**: EPUB files produce structured project directories with section and endnote tracks.
**Effort**: ~15 hours
**Exit**: `palimpsest ingest ij.epub` produces complete project with sections.jsonl and endnotes.jsonl.

### Phase 2: Audit Remediation + Cleanup (B01-B05)
**Goal**: All blocking audit findings resolved, legacy code removed.
**Effort**: ~8 hours
**Exit**: Deterministic IDs, clean exception handling, no legacy directories.

### Phase 3: Endnote UI + Section Navigation (D01-D04)
**Goal**: Endnotes are clickable and readable; sections are navigable.
**Effort**: ~10 hours
**Exit**: Click endnote in IJ → see note text. Click section → scroll to it.

### Phase 4: Semantic Zoom (C01-C04)
**Goal**: Four zoom levels with smooth transitions.
**Effort**: ~12 hours
**Exit**: Zoom from work-level overview to sentence-level detail.

### Phase 5: Export + Specs (E01-E03, G01-G04)
**Goal**: All export formats working, all spec files complete.
**Effort**: ~16 hours
**Exit**: `palimpsest export --format w3c|paf|csv` works. All specs are non-stubs.

### Phase 6: Browser Polish (F01-F05)
**Goal**: Error boundaries, loading states, keyboard nav, a11y, responsive.
**Effort**: ~10 hours
**Exit**: Browser is professional quality on all screen sizes.

### Phase 7: Testing + EPUB Tests (A07, A08, H01-H05)
**Goal**: Comprehensive test coverage, E2E tests, Vision Gate smoke test.
**Effort**: ~14 hours
**Exit**: >250 tests, Playwright E2E, Vision Gate passes on IJ.

### Phase 8: Packaging (I01-I03)
**Goal**: pip install works, doctor command works, browser bundled.
**Effort**: ~6 hours
**Exit**: Fresh `pip install palimpsest[full]` → `palimpsest doctor` → green.

### Final: Vision Gate Test
**Goal**: Execute the full Vision Gate test sequence (Doc 26 §5.4) with Infinite Jest.
**Exit**: M1 declared complete.

---

## 6. Risk Register

| Risk | Impact | Mitigation |
|------|--------|-----------|
| IJ EPUB has unexpected structural patterns | A-chain delays | EPUB parser designed with fallbacks; test early with real file |
| ebooklib can't handle Calibre quirks | A-chain blocked | Fallback: raw zip extraction + BeautifulSoup parsing |
| Full IJ analysis takes too long (>15 min) | EXIT-F01 fails | Profile bottleneck tracks; add progress reporting; parallelize independent tracks |
| LitHMM discovers degenerate states on IJ | EXIT-F06 fails | Tune n_states, features; validate with P&P first then IJ |
| Playwright setup complex on macOS | H-chain delays | Use Vitest for component tests; Playwright for critical E2E only |
| Browser dist bundling breaks pip install | I-chain fails | Test in clean venv; use setuptools package_data |

---

*End of Document 27*

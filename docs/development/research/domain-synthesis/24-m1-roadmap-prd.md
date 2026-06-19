# Milestone 1: Walking Skeleton — Detailed Roadmap-PRD

**Date**: 2026-06-08 (v1.1); updated 2026-06-10 (v1.2 — M1.5 added, M1.1-M1.4 marked COMPLETE)
**Version**: 1.2
**Status**: Active — M1.1-M1.4 COMPLETE, M1.5 pending
**Source**: Roadmap v4.0 (doc 28), PRD (doc 22), Phase 1 plan (doc 14), Design Philosophy (doc 26), Implementation Plan (doc 27)

---

## Overview

Milestone 1 builds the complete product loop at minimum fidelity: import a text → compute 12 Base tracks → view them in an interactive browser → ask the AI assistant about what the analysis reveals. When M1 is complete, a scholar can import any novel and immediately begin exploring its computational anatomy.

**Duration**: 13 weeks (5 phases: M1.1-M1.4 COMPLETE as of 2026-06-09; M1.5 Browser Foundation Sprint pending)
**Exit criteria**: Load *Infinite Jest*, see all 12 Base tracks rendered in a genome-browser-quality UI with semantic zooming, multi-tab layout, styled tooltips, and interactive heatmap. Ask the AI "What does the green LitHMM state mean?" and get a data-grounded response.

---

## Phase M1.1: Ingest + Normalize + First Track (2 weeks) — COMPLETE

**Status**: COMPLETE (2026-06-08). 13 tracks compute, EPUB pipeline handles 55/55 books, 213 Python tests pass.

### Purpose
Build the thinnest possible vertical slice: one text in, one annotation track out, visible in a browser. This phase defines PAF, LFO, and the project directory structure by building them.

### Requirements Covered
F-IMP-001 (with structural extraction), F-IMP-002, F-IMP-003, F-TRK-001

### Deliverables

#### D1.1.1: CLI Ingestion Pipeline (with EPUB Structural Extraction)
- `palimpsest ingest <file> --title "X" --author "Y" --workspace projects/`
- Accepts: PDF (pymupdf), EPUB (ebooklib + BeautifulSoup), TXT, HTML, Markdown
- Normalizes: Unicode NFC, whitespace standardization, paragraph detection
- Computes: SHA-256 checksum of reference text
- Outputs: `reference.txt`, `reference.sha256`, `metadata.json`
- **EPUB structural extraction** (new):
  - OPF metadata → enhanced `metadata.json` (isbn, publisher, date, source_format)
  - Heading elements (h1-h6) → `tracks/sections.jsonl` (section boundary annotations)
  - Endnote/footnote pairs (bidirectional anc ↔ sym links) → `tracks/endnotes.jsonl`
  - Multi-paragraph endnotes grouped correctly
  - Endnote text preserved: appended after narrative text with separator
  - `coordinates.json` updated with section_index mapping
- Error handling: if PDF extraction fails, show extracted text + prompt for manual paste
- Backward compatible: TXT/PDF paths produce identical output to current pipeline

#### D1.1.2: Segmentation Engine
- Sentence boundaries: spaCy `en_core_web_sm` sentencizer
- Paragraph boundaries: double-newline heuristic
- Section boundaries: heading detection from EPUB/HTML structure; regex + TextTiling fallback (Hearst 1997) for PDF/TXT
- Output: `tracks/segments.jsonl` in W3C JSONL format

#### D1.1.3: Entity Track
- BookNLP pipeline (if installed) or spaCy NER fallback
- Entity types: PER (person), LOC (location), ORG (organization), WORK (literary work)
- Character clustering: merge "Hal", "Hal Incandenza", "Incandenza" into one entity
- Output: `tracks/entities.jsonl`

#### D1.1.4: PAF Format v0.1
- Defined by implementation, not by a priori specification
- TSV columns matching what the segmentation and entity tools actually produce
- Validator script: `palimpsest validate <file.paf>`

#### D1.1.5: LFO v0.1
- 22+ terms covering: segment types (sentence, paragraph, section), entity types (PER, LOC, ORG, WORK), structural primitives (boundary, span, point), structural elements (endnote, section_boundary, heading)
- JSON file in `specs/lfo-v0.1.json`

#### D1.1.6: Minimal Browser
- React + TypeScript app
- Renders reference text with entity highlight spans
- Click entity → tooltip with entity type + full name
- Track toggle (entities on/off)
- No multi-track, no zoom — just text + one track

#### D1.1.7: Project Directory Structure
```
projects/{text-id}/
├── reference.txt
├── reference.sha256
├── metadata.json
├── coordinates.json
├── tracks/
│   ├── segments.jsonl
│   ├── entities.jsonl
│   ├── sections.jsonl    (from EPUB/HTML heading elements)
│   └── endnotes.jsonl    (from EPUB/HTML endnote links)
├── signals/
│   └── (computed signals: lithmm_meta.json, etc.)
├── cache/
│   └── (embeddings.db, spacy docs, etc.)
├── manifests/
│   └── (per-track rendering manifests)
└── x-config/              (empty, scaffolded)
```

### Acceptance Criteria
- [ ] Ingest IJ Chapter 1 (PDF) in <5 seconds
- [ ] Ingest P&P full novel (TXT) in <10 seconds
- [ ] **Ingest IJ EPUB: 67 section boundaries detected and annotated**
- [ ] **Ingest IJ EPUB: 388 endnotes extracted with bidirectional links**
- [ ] **Ingest IJ EPUB: metadata.json contains isbn, publisher, date from OPF**
- [ ] Entity track detects "Hal", "Arizona", "University of Arizona" in IJ Ch1
- [ ] Browser displays text with colored entity spans
- [ ] Click entity → detail tooltip shows entity type and canonical name
- [ ] **Click endnote marker → note text displays in panel**
- [ ] **Section navigation: click section heading → scroll to section**
- [ ] PAF validates against the now-defined spec
- [ ] Degradation: if spaCy model missing, print install instructions and skip entity track

---

## Phase M1.2: Five Base Tracks + AI Summary (3 weeks) — COMPLETE

### Purpose
Expand from 1 track to 5 tracks. Introduce the LLM for the first time. Validate that the multi-track architecture scales.

### Requirements Covered
F-TRK-002, F-TRK-003, F-TRK-004, F-TRK-005, F-TRK-011, F-AI-001

### Deliverables

#### D1.2.1: Sentiment Trajectory Track
- Sliding-window hedonometer (Reagan et al. 2016 methodology)
- Configurable window (default: 1000 words, step: 100)
- Output: `tracks/sentiment.jsonl` (float per step)
- Visualization: area chart below text

#### D1.2.2: Lexical Features Track
- Per-segment: TTR, hapax count, vocabulary richness (Yule's K), mean word length, lexical density
- Output: `tracks/lexical.jsonl`
- Visualization: sparklines per metric

#### D1.2.3: Syntactic Complexity Track
- Per-sentence: dependency tree depth, subordination ratio, sentence length
- Aggregated per segment
- Output: `tracks/syntax.jsonl`
- Visualization: line chart + stacked POS bar chart

#### D1.2.4: Dialogue Attribution Track
- BookNLP quote detection + speaker attribution
- Output: `tracks/dialogue.jsonl` (quote span + speaker entity)
- Visualization: colored spans (speaker color) in text view, dialogue proportion sparkline

#### D1.2.5: Topic Distribution Track
- LDA with configurable topics (default: 20)
- Per-segment topic distribution vector
- Top-3 topics labeled per segment
- Output: `tracks/topics.jsonl`
- Visualization: stacked area chart

#### D1.2.6: LLM Integration
- Local LLM via Ollama (Qwen3:8B or equivalent)
- Per-chapter summarization
- Per-segment explanation (on demand)
- Graceful degradation: if Ollama not running, disable AI features with clear message

#### D1.2.7: Track Management UI
- Track toggle panel
- Track reordering (drag-and-drop)
- Overview sparklines for each track
- 5 tracks rendering simultaneously without jank

### Acceptance Criteria
- [ ] 5 tracks compute on IJ Ch1 in <30 seconds
- [ ] 5 tracks render simultaneously at 60fps scroll
- [ ] AI generates coherent per-chapter summary
- [ ] Topic labels are interpretable (not just "Topic 7")
- [ ] Track toggle is instantaneous
- [ ] If Ollama is not running, all non-AI features work normally

---

## Phase M1.3: Full Base Suite + Browser (3 weeks) — COMPLETE

### Purpose
Complete the remaining Base tracks and build the full browser with semantic zooming. This is the first time the product feels "real."

### Requirements Covered
F-TRK-006, F-TRK-010, F-IMP-004, F-BRW-001, F-BRW-006

### Deliverables

#### D1.3.1: Narrative Arc Track
- Boyd et al. (2020) 15-dimensional function-word arc
- 3-dimensional reduction: staging, progression, tension
- Output: `tracks/narrative-arc.jsonl`
- Visualization: multi-line chart (3 lines, one per dimension)

#### D1.3.2: Coreference Track
- BookNLP coreference chains
- Pronoun → character entity resolution
- Output: `tracks/coreference.jsonl` (chain IDs linking mentions)
- Visualization: click any mention → highlight full chain; hover → show canonical name

#### D1.3.3: Multiple Coordinate Systems
- `coordinates.json` defining: character_offset, paragraph_index, section_index, page_number
- For IJ: add narrative_order vs. chronological_order (from Swinehart data)
- Navigation bar shows current position in selected coordinate system
- UI control to switch coordinate system

#### D1.3.4: Full Linear Browser
- JBrowse 2-inspired architecture: adapter → track → display → renderer
- 9 tracks rendering simultaneously
- Smooth scroll at 60fps
- Virtual scrolling for full novels
- Semantic zooming: 4 levels (work → chapter → paragraph → sentence)
- Track configuration panel
- Search: find text + find entity

### Acceptance Criteria
- [ ] 9 Base tracks render on full P&P novel at 60fps
- [ ] Zoom from full-novel overview to sentence-level detail
- [ ] Coordinate system switching works for IJ (narrative ↔ chronological)
- [ ] Coreference chains visible: click "he" → highlight all instances of Hal
- [ ] Search finds "Mr. Darcy" across the full text

---

## Phase M1.4: LitHMM + Self-Similarity (2 weeks) — COMPLETE

### Purpose
The crown jewel: agnostic passage state discovery and self-similarity visualization. This phase delivers the core Palimpsest innovation.

### Requirements Covered
F-TRK-007, F-TRK-008, F-TRK-009, F-TRK-012

### Deliverables

#### D1.4.1: Self-Similarity Matrix (TextHiC)
- Passage-pair similarity matrix (SBERT cosine on paragraph embeddings)
- Stored as sparse matrix (HDF5 or similar)
- RQA metrics: RR, DET, LAM computed from matrix
- Output: `tracks/self-similarity.h5` + `tracks/rqa.jsonl`
- Basic dotplot visualization (Canvas-based, tiled for performance)

#### D1.4.2: LitHMM Passage States
- Multivariate HMM on feature vectors from existing tracks:
  - Lexical density (from F-TRK-003)
  - Dialogue ratio (from F-TRK-005)
  - NE density (from F-TRK-001)
  - Sentiment volatility (from F-TRK-002)
  - Sentence length variance (from F-TRK-004)
  - Topic entropy (from F-TRK-011)
- User-configurable states (default: 10)
- Auto-generated state descriptions from feature distributions
- Output: `tracks/lithmm.jsonl` (state label + posterior per segment)
- Visualization: color-coded band below text

#### D1.4.3: Narrative Alphabet
- K-means on the same feature vectors → discrete state labels
- Alphabet size configurable (default: 32)
- Sequence stored as string in `tracks/narrative-alphabet.txt`
- Visualization: letter sequence display with state colors

#### D1.4.4: Thematic Compartments
- A/B decomposition via first eigenvector of similarity matrix
- TAD-like domains via directionality index + HMM segmentation (Dixon 2012 method)
- Output: `tracks/compartments.jsonl`
- Visualization: A/B color-coded track + domain boundary markers

### Acceptance Criteria
- [ ] LitHMM discovers 8-12 distinct states on P&P
- [ ] State descriptions are interpretable (e.g., "This state is characterized by high dialogue ratio, low NE density, and high sentiment — likely intimate conversation scenes")
- [ ] AI can explain states when asked: "What does the green state mean?"
- [ ] Dotplot renders full P&P in <3 seconds
- [ ] A/B compartments reveal meaningful thematic structure
- [ ] All 12 Base tracks now available and rendering

---

## Phase M1.5: Browser Foundation Sprint (3 weeks) — PENDING

> Added by Roadmap v4.0 (doc 28, 2026-06-10). Addresses 23 UI gaps identified in the design review, informed by genome browser research (UCSC, IGV, IGB, JBrowse 2, D-GENIES).

### M1.5a: Component Library + Design System (1 week)

**Deliverables**:
- Install Radix UI primitives + Tailwind CSS (or shadcn/ui)
- Install Floating UI tooltip library; replace ALL native `title` attributes with styled, immediate tooltips
- Every interactive element gets a tooltip: track toggles, zoom buttons, toolbar controls, barcode bars, search buttons, detail panel fields
- Consistent design tokens (colors, typography, spacing) derived from genome browser analysis
- designlang MCP tool available for extracting reference palettes from target sites

**Acceptance**: Zero native `title` tooltips remaining. All interactive elements show styled tooltips within 100ms of hover.

### M1.5b: Layout Redesign (1 week)

**Deliverables**:
- **Multi-tab layout**: Reading | TextHiC | Characters | Analysis tabs
- **UCSC-inspired toolbar**: Position input (paragraph N / character offset), zoom level display, navigation arrows
- **Coordinate ruler**: Horizontal bar showing full text extent with viewport indicator band (MCGV box-draw zoom pattern)
- **Responsive OverviewBar**: CSS `width: 100%` with ResizeObserver; honor `state-band`, `ab-band` manifest types; viewport position indicator
- **Track display modes**: Dense (barcode), Pack (block annotations), Inline (colored spans) — user-selectable per track
- **Track reordering**: Drag-and-drop in TrackPanel
- **Highlight toggle fix**: Click same paragraph to deselect; click background to clear annotation selection

**Acceptance**: Multi-tab layout working. OverviewBar fills viewport width. Track display modes selectable. No highlight-sticking bug.

### M1.5c: Interaction Polish (1 week)

**Deliverables**:
- **Confidence threshold slider** per track in TrackPanel (currently wired in state but no UI control)
- **Rich annotation hover**: Floating UI popover showing body type, value, confidence, evidence level, text excerpt
- **OverviewBar hover**: Track name + annotation preview at mouse position
- **OverviewBar click-drag**: Select a text range by dragging
- **Context menu on annotations**: Right-click → "Show all mentions", "Copy text", "Navigate to..."
- **Keyboard**: Tab navigation with visible focus rings, Escape to close any panel/popover
- **Loading states**: Skeleton loaders for track loading, per-track progress during import

**Acceptance**: Every element has hover feedback. Confidence slider filters annotations in real time. Context menus provide discoverable actions.

---

## M1 Vision Gate

**The test**: Dr. Amara (UN-001 from PRD) imports Infinite Jest. In 3 minutes, 12 Base tracks compute. She opens the browser. She zooms into the Eschaton scene. LitHMM has colored it "state 4" (high dialogue, high NE density, high sentiment volatility, low lexical density). She asks the AI: "What is state 4?" The AI responds: "State 4 is characterized by rapid dialogue between many characters with high emotional intensity — in genome terms, this is a highly-transcribed, enhancer-active region." She realizes this is a "dramatic peak" state. She names it "dramatic peak" and begins exploring where else it occurs. She finds 23 other passages in state 4 — a map of IJ's dramatic high points that she hadn't noticed as a unified pattern.

This is the moment Palimpsest proves its thesis: computational analysis reveals literary structure invisible to the unaided reader.

---

## Methodology & Completion Reference

M1 completion follows **Feature-Driven Development (FDD) with BDD overlay** as formalized in Doc 26 (Design Philosophy & Exit Criteria). The shift from TDD to FDD means:
- Features are implemented as vertical slices (backend + frontend + tests), not horizontal layers
- Acceptance is validated against BDD user stories exercised with real Infinite Jest content, not synthetic fixtures
- The Vision Gate test (above) is the definitive exit gate — demonstrated capability, not code compilation

**Detailed exit criteria**: Doc 26 §5 (24 criteria across functional, quality, documentation gates)
**Atomized task list**: Doc 27 (41 tasks across 8 phases, ~96 hours estimated)
**EPUB pipeline design**: Doc 27 §2 (based on actual IJ EPUB structure analysis)

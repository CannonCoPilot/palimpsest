# Document 26: M1 Design Philosophy, User Stories & Exit Criteria

**Version**: 1.1 (updated 2026-06-10)
**Date**: 2026-06-08 (v1.0); 2026-06-10 (v1.1 — M1.5 reference, roadmap v4.0 alignment)
**Status**: Active — M1.1-M1.4 exit criteria PASSED. M1.5 exit criteria pending (see doc 24 v1.2 and doc 28).
**Supersedes**: None (new document)
**References**: Doc 21 (Vision), Doc 22 (PRD v1.1), Doc 28 (Roadmap v4.0), Doc 24 (M1 Roadmap-PRD v1.2)

> **NOTE**: Roadmap v4.0 (doc 28) adds M1.5 (Browser Foundation Sprint) with its own exit criteria. The original 6 BDD user stories and 24 exit criteria in this document cover M1.1-M1.4, which are COMPLETE. M1.5 user stories and exit criteria are defined in doc 24 v1.2.

---

## 1. Purpose

This document formalizes the methodological shift from Test-Driven Development (TDD) to Feature-Driven Development (FDD) with Behavior-Driven Development (BDD) overlay for the completion of Milestone 1. It defines:

- The design philosophy governing all remaining M1 work
- User stories and scenarios in BDD format (Given-When-Then)
- Concrete, measurable exit criteria for concluding M1
- Quality standards that every feature must meet before M1 is declared complete

The goal: M1 exits as a **polished, professional-quality product** — not a prototype, not a scaffold, but a viable platform that a literary scholar can use end-to-end with real content. All subsequent milestones build upon this foundation.

---

## 2. Methodology: FDD + BDD

### 2.1 Feature-Driven Development (5-Step Process)

FDD structures work around deliverable features visible to the user, not implementation tasks visible to the engineer. The five steps, applied to Palimpsest M1:

**Step 1 — Develop an Overall Model**
The overall model is the genome browser isomorphism established in Doc 21 (Vision Document). Every feature must trace back to this model. If a feature cannot be explained in terms of the text-as-genome metaphor, it does not belong in Base; it belongs in X or in a future milestone.

The model's core axioms:
- Text is a linear sequence with coordinate systems (character offset, paragraph, section, page)
- Analysis produces annotations (W3C Web Annotation) layered onto the sequence
- The browser renders multiple annotation tracks simultaneously along the sequence axis
- The AI assistant explains computational findings in human-interpretable terms
- Every classification is perspectival, not objective (Underwood 2019)

**Step 2 — Build a Feature List**
The feature list derives from Doc 22 (PRD) but is re-scoped to M1 deliverables. Features are expressed as user-visible capabilities, not internal implementation details:

| Feature | PRD Ref | User-Visible Capability |
|---------|---------|------------------------|
| EPUB Import | F-IMP-001 | Load an EPUB novel; structural metadata preserved as tracks |
| Section Navigation | F-IMP-003, F-IMP-004 | Navigate by chapter/section headings; coordinate system switching |
| Endnote System | F-IMP-001 (expanded) | Click endnote markers; read endnote content in context |
| 12 Base Tracks | F-TRK-001 through F-TRK-012 | All 12 analysis tracks compute and render |
| Track-Specific Rendering | F-BRW-001 | Each track type has visually distinct rendering (color-bands, gradients, underlines) |
| Virtual Scrolling | NFR-001 | Full novels render smoothly at 60fps |
| Search & Navigate | F-BRW-001 | Text search with highlighted matches; navigate between results |
| AI Summarization | F-AI-001 | Select any passage; get AI-generated summary |
| AI State Explanation | F-AI-001 | Click any LitHMM state; ask "what does this state mean?" |
| TextHiC Dotplot | F-TRK-007 | Interactive self-similarity matrix with brush selection |
| Data Export | F-FMT-001, F-FMT-003 | Export annotations in W3C JSON-LD and PAF formats |
| Project Management | F-IMP-002 | Create, list, load, and serve analysis projects |

**Step 3 — Plan by Feature**
Each feature gets a design brief (Section 4 of this document) specifying:
- User story (BDD scenario)
- Acceptance criteria
- Dependencies on other features
- Backend, frontend, and data components required

**Step 4 — Design by Feature**
Before implementation, each feature's design is reviewed against:
- The overall model (Step 1) — does it honor the genome browser isomorphism?
- The user story (Step 3) — does the design enable the described scenario?
- The quality standards (Section 6) — does it meet the bar?

**Step 5 — Build by Feature**
Implementation proceeds feature-by-feature (not layer-by-layer). Each feature is implemented vertically: backend + frontend + tests + documentation in a single pass. A feature is not "done" until a user can exercise the complete scenario.

### 2.2 Behavior-Driven Development Overlay

BDD ensures that every feature is specified in terms of observable user behavior, not internal state. The format:

```
Feature: [Feature Name]
  As a [role]
  I want [capability]
  So that [value proposition]

  Scenario: [Specific scenario name]
    Given [precondition]
    When [action]
    Then [observable outcome]
    And [additional outcome]
```

Every acceptance criterion in Section 5 maps to at least one BDD scenario. Every scenario is testable — either via automated Playwright test or via documented manual verification procedure.

### 2.3 The Shift from TDD

TDD validated isolated components: "does the sentiment extractor produce correct JSONL?" FDD/BDD validates integrated features: "can Dr. Amara see sentiment coloring change from green to red as she scrolls through a tense scene?"

TDD remains the discipline for internal correctness (unit tests still run, pytest still gates commits). But the *acceptance standard* shifts from "tests pass" to "user stories are exercised end-to-end with real content."

**Real content means Infinite Jest.** Not synthetic test fixtures. Not Pride and Prejudice Chapter 1. The validation corpus for M1 is a meaningful sample of IJ — enough to exercise endnotes, non-chronological structure, 200+ characters, and 1000+ page scale.

---

## 3. User Stories (BDD Scenarios)

### US-01: Import and Analyze an EPUB Novel

```
Feature: EPUB Import Pipeline
  As a literary scholar
  I want to import an EPUB file of a novel
  So that I can analyze it with all 12 Base tracks while preserving
  its structural metadata (chapters, endnotes, front matter)

  Scenario: Import Infinite Jest EPUB
    Given I have the Infinite Jest EPUB file
    When I run `palimpsest ingest infinite-jest.epub`
    Then a project directory is created with reference.txt (clean text, endnotes separated)
    And metadata.json contains title, author, publisher, ISBN, date, word count, section count
    And coordinates.json maps character offsets to section indices and paragraph indices
    And tracks/sections.jsonl contains 67 section boundary annotations with heading text
    And tracks/endnotes.jsonl contains 388 endnote annotations with call-site positions and note text
    And all 12 Base tracks compute without error
    And total ingest + compute time is under 10 minutes for the full novel

  Scenario: Import a simple TXT file (backward compatibility)
    Given I have a plain text file with no structural markup
    When I run `palimpsest ingest novel.txt`
    Then the system creates a project with reference.txt and computes all tracks
    And no sections or endnotes tracks are generated (graceful absence, not error)

  Scenario: Import HTML with chapter structure
    Given I have an HTML file with h1/h2/h3 headings
    When I run `palimpsest ingest novel.html`
    Then section boundaries are detected from heading elements
    And the sections track contains annotations at each heading position
```

### US-02: Explore LitHMM Passage States (Vision Gate)

```
Feature: LitHMM State Exploration
  As a literary scholar
  I want to see LitHMM states as color-coded bands and ask the AI
  what each state means
  So that I can discover functional passage types I hadn't noticed

  Scenario: The Vision Gate — Dr. Amara's Discovery
    Given I have loaded Infinite Jest with all 12 tracks computed
    And the browser is open showing the text with LitHMM track enabled
    When I scroll to the Eschaton scene
    Then the passage is rendered with a distinct color band indicating its LitHMM state
    And the color is different from surrounding passages in different states
    When I click on the colored passage
    Then the DetailPanel shows "LitHMMAnnotation — State 4"
    And the state description reads something like "high dialogue, high NE density"
    When I click "Explain this state"
    Then the AI generates a narrative explanation grounded in feature data and sample passages
    And the explanation describes narrative qualities (e.g., "dramatic peaks with rapid dialogue")
    And sample passages from the same state are shown for comparison

  Scenario: Find all passages in a state
    Given I have identified an interesting LitHMM state
    When I search for passages in that state (via track filtering or semantic search)
    Then I see a list of all passages assigned to that state
    And I can navigate between them
```

### US-03: Navigate a Large Novel Smoothly

```
Feature: Large Document Navigation
  As a literary scholar working with a 1000+ page novel
  I want smooth scrolling and responsive interaction
  So that the tool doesn't become a burden on my research workflow

  Scenario: Scroll through Infinite Jest (2500+ paragraphs)
    Given I have loaded Infinite Jest (full novel) in the browser
    When I scroll through the text
    Then rendering is smooth (no visible lag or blank frames)
    And annotations render correctly on visible paragraphs
    And paragraphs outside the viewport are not in the DOM

  Scenario: Jump to a specific section
    Given I have loaded Infinite Jest with sections track
    When I select a section from a navigation control
    Then the browser scrolls to that section's starting paragraph
    And the transition is smooth (not an abrupt jump)

  Scenario: Search in a large document
    Given I have loaded Infinite Jest
    When I press Ctrl+F and type "Eschaton"
    Then matching text is highlighted in yellow in the reading pane
    And the current match is highlighted in bright yellow, others in pale yellow
    And I can navigate between matches with Enter/Shift+Enter
    And the browser scrolls to each match automatically
```

### US-04: Navigate Endnotes in Context

```
Feature: Endnote Navigation
  As a literary scholar reading Infinite Jest
  I want to access endnotes without losing my reading position
  So that I can follow Wallace's endnote system as part of the reading experience

  Scenario: Click an endnote marker
    Given I am reading a passage that contains endnote marker 24
    When I click the endnote marker (superscript number)
    Then a panel or tooltip shows the text of endnote 24
    And my reading position in the main text is preserved
    And I can dismiss the endnote and continue reading

  Scenario: Endnote as annotation
    Given the endnotes track is enabled
    When I look at the OverviewBar
    Then endnote positions are visible as markers along the text axis
    And denser endnote regions are visually apparent
```

### US-05: Export Analysis for Publication

```
Feature: Data Export
  As a literary scholar preparing a publication
  I want to export my analysis in standard formats
  So that I can share findings, include in papers, and enable reproducibility

  Scenario: Export W3C Web Annotation JSON-LD
    Given I have a completed analysis project
    When I run `palimpsest export --format w3c project-id`
    Then a valid W3C Web Annotation JSON-LD file is produced
    And every annotation includes proper @context, body, target, creator
    And the export round-trips (re-import produces identical annotations)

  Scenario: Export PAF (computational format)
    Given I have a completed analysis project
    When I run `palimpsest export --format paf project-id`
    Then a valid PAF TSV file is produced
    And it passes validation against the PAF v0.1 spec
    And all tracks are represented
```

### US-06: First-Time Setup and Health Check

```
Feature: Setup and Diagnostics
  As a first-time user
  I want the tool to tell me if dependencies are missing
  So that I can get started without debugging configuration

  Scenario: Run doctor command
    Given I have installed palimpsest via pip
    When I run `palimpsest doctor`
    Then it checks for spaCy models, Ollama availability, and required dependencies
    And it reports what's available and what's missing
    And it suggests install commands for missing components

  Scenario: Graceful degradation without Ollama
    Given Ollama is not running
    When I load a project in the browser
    Then all non-AI features work normally
    And AI buttons show "Start AI services for this feature"
    And no errors or crashes occur
```

---

## 4. Feature Design Briefs

Each feature is specified with its vertical slice: what changes in the backend, frontend, data layer, and tests.

### F-EPUB: EPUB Structural Import Pipeline

**Overall Model Alignment**: Text ingestion is the analogue of genome sequencing — raw data (EPUB) is assembled into a reference sequence (reference.txt) with structural annotations (sections = genes, endnotes = regulatory elements).

**Backend Components**:
- `core/palimpsest/ingest/epub_parser.py`: EPUB-aware parser using `ebooklib`
  - Reads OPF metadata (title, author, ISBN, publisher, date)
  - Traverses spine items in reading order
  - Strips HTML tags while recording character offset mappings
  - Detects heading elements (h1-h6) as section boundaries
  - Extracts endnote pairs (anc ↔ sym) as bidirectional annotations
  - Handles multi-paragraph endnotes (group consecutive p tags after sym anchor)
  - Deduplicates endnote number artifacts (bare sup before linked sup)
- `core/palimpsest/ingest/extractor.py`: Updated dispatch to route .epub to epub_parser
- Section annotations: W3C body type `palimpsest:SectionAnnotation` with heading text
- Endnote annotations: W3C body type `palimpsest:EndnoteAnnotation` with:
  - `palimpsest:noteNumber` (integer)
  - `palimpsest:noteText` (string, full endnote content)
  - `palimpsest:callSiteStart` / `palimpsest:callSiteEnd` (character offsets in reference.txt)

**Frontend Components**:
- Endnote markers in text: AnnotationOverlay renders endnote call-sites as superscript clickable numbers
- Endnote tooltip/panel: Click endnote marker → show note text in DetailPanel or floating tooltip
- Section navigation: Section headings visible in OverviewBar; click → scroll to section

**Data Artifacts**:
- `metadata.json`: Enhanced with `isbn`, `publisher`, `pub_date`, `source_format: "epub"`, `endnote_count`, `section_count`
- `coordinates.json`: Adds `section_index` mapping (character offset → section number)
- `tracks/sections.jsonl`: Section boundary annotations
- `tracks/endnotes.jsonl`: Endnote annotations (both call-site and note content)

### F-ZOOM: Semantic Zoom (4 Levels)

**Overall Model Alignment**: Genome browsers change visual representation qualitatively at different zoom levels (nucleotides → codons → genes → chromosomes). The text browser should do the same.

**Zoom Levels**:
| Level | Name | Rendering | Tracks Show |
|-------|------|-----------|-------------|
| 1 | Work | Chapter blocks with density sparklines | Track overview bars only |
| 2 | Chapter | Paragraph strips with track barcodes | Compressed inline annotations |
| 3 | Paragraph | Full text with inline annotations | Full annotation spans |
| 4 | Sentence | Full detail with tooltips and metadata | Everything + confidence scores |

**Frontend Components**:
- Zoom control (buttons or scroll-wheel with modifier key)
- ZoomRenderer dispatch: based on `viewStore.zoomLevel`, render paragraphs at appropriate detail
- Track renderers provide zoom-level-specific visualization via manifest `zoomLevels` field

### F-EXPORT: Complete Data Export

**Backend Components**:
- `palimpsest export --format w3c|paf|csv <project>` CLI command
- W3C exporter: proper JSON-LD with @context, collection wrapping
- PAF exporter: TSV format per paf-v0.1.md spec
- CSV exporter: flat tabular format for spreadsheet import

### F-PKG: Installation and Packaging

**Components**:
- `palimpsest doctor` command: checks spaCy models, Ollama, ebooklib, browser dist
- Browser dist bundled in pip package (pre-built in `palimpsest/browser_dist/`)
- Static file serving from installed package location (not just dev checkout)
- pyproject.toml with optional dependency groups: `[epub]`, `[ai]`, `[booknlp]`

---

## 5. M1 Exit Criteria

M1 is **not complete** until ALL of the following criteria are met. These are hard gates, not aspirational targets.

### 5.1 Functional Exit Criteria

| ID | Criterion | Verification Method |
|----|-----------|-------------------|
| EXIT-F01 | EPUB import of Infinite Jest produces clean reference.txt with correct word count | Automated test |
| EXIT-F02 | 67 section boundaries detected and annotated from IJ EPUB headings | Automated test |
| EXIT-F03 | 388 endnotes extracted with bidirectional call-site ↔ note-text links | Automated test |
| EXIT-F04 | All 12 Base tracks compute on IJ without error | Automated test |
| EXIT-F05 | Browser renders IJ at 60fps scroll (no visible lag on M4 Mac) | Manual verification |
| EXIT-F06 | LitHMM states render as distinct color-coded bands (not identical highlights) | Visual verification |
| EXIT-F07 | Click LitHMM annotation → "Explain this state" → AI returns data-grounded explanation | Manual verification |
| EXIT-F08 | Text search highlights matches in reading pane with navigation | Automated test |
| EXIT-F09 | Endnote markers are clickable; note text displays without losing reading position | Manual verification |
| EXIT-F10 | `palimpsest export --format w3c` produces valid W3C JSON-LD | Automated test |
| EXIT-F11 | `palimpsest export --format paf` produces valid PAF TSV | Automated test |
| EXIT-F12 | `palimpsest doctor` correctly reports dependency status | Manual verification |

### 5.2 Quality Exit Criteria

| ID | Criterion | Verification Method |
|----|-----------|-------------------|
| EXIT-Q01 | Python test suite: 0 failures, coverage > 80% on core modules | CI |
| EXIT-Q02 | TypeScript: 0 compilation errors (tsc --noEmit) | CI |
| EXIT-Q03 | Vite build: produces working dist bundle | CI |
| EXIT-Q04 | Browser tests: Vitest unit tests for all stores and adapters | CI |
| EXIT-Q05 | No critical (C-level) findings from adversarial audit remain open | Review |
| EXIT-Q06 | All annotation IDs are deterministic (hash-based, not UUID) | Automated test |
| EXIT-Q07 | All spec files (LFO, PAF, annotation-model, signals) are complete (not stubs) | Review |
| EXIT-Q08 | Graceful degradation: all features work without Ollama (AI features show friendly message) | Manual verification |

### 5.3 Documentation Exit Criteria

| ID | Criterion | Verification Method |
|----|-----------|-------------------|
| EXIT-D01 | WALKTHROUGH.md reflects current CLI commands and browser features | Review |
| EXIT-D02 | README.md has installation instructions that work from clean environment | Manual verification |
| EXIT-D03 | development-history.md is current through M1 completion | Review |
| EXIT-D04 | All planning documents updated to reflect actual implementation | Review |

### 5.4 The Vision Gate Test

The definitive M1 exit test, derived from Doc 21 User Narrative UN-001:

> **Setup**: Import the Infinite Jest EPUB via `palimpsest ingest`. Wait for all 12 Base tracks to compute. Open the browser.
>
> **Test sequence**:
> 1. The browser loads without error. Text is readable. Track panel shows 12+ tracks.
> 2. Scroll through the novel. Rendering is smooth. Paragraphs outside the viewport are not in the DOM.
> 3. Enable the LitHMM track. Passages are color-coded by state — at least 3 visually distinct colors visible.
> 4. Navigate to a known scene (use search or section navigation). The Eschaton scene is findable.
> 5. Click a LitHMM-colored passage. DetailPanel shows state ID, description, confidence.
> 6. Click "Explain this state." AI generates a coherent, data-grounded explanation within 30 seconds.
> 7. Press Ctrl+F, type "Eschaton." Matches highlight in yellow. Navigate between matches.
> 8. Click an endnote marker (if visible in current view). Endnote text appears.
> 9. Open the TextHiC dotplot. Matrix renders. Brush-select a region → linear view highlights.
> 10. Run `palimpsest export --format w3c`. File is valid JSON-LD.
>
> **Pass condition**: All 10 steps complete without error, crash, or unacceptable delay (>30s for any single operation). AI explanation is coherent (human-judged). Visual rendering is professional quality (no overlapping elements, no broken layouts, no invisible tracks).

---

## 6. Quality Standards

Every feature delivered for M1 must meet these standards:

### 6.1 Code Quality
- Python: type-annotated, passes mypy (strict mode on new code)
- TypeScript: strict mode, no `any` types in new code
- No dead code, no commented-out code, no TODO placeholders in shipped features
- Functions under 50 lines; files under 400 lines (with justified exceptions)

### 6.2 Error Handling
- No silent exception swallowing (audit finding C1)
- User-facing errors are descriptive and suggest remediation
- Internal errors are logged with context
- Graceful degradation for optional dependencies (Ollama, BookNLP, spaCy models)

### 6.3 Performance
- Full IJ novel loads in browser within 5 seconds (initial render)
- Scroll at 60fps (virtual scrolling for documents > 200 paragraphs)
- Track toggle responds within 100ms
- Search results appear within 500ms of query completion
- AI responses within 30 seconds (network/model dependent)

### 6.4 Accessibility
- All interactive elements keyboard-navigable
- ARIA labels on track controls, buttons, panels
- Color is not the sole information channel (shapes, borders, labels supplement color)
- Minimum contrast ratio 4.5:1 for text

### 6.5 Testing
- Every new Python module has corresponding test file
- Every BDD scenario has either:
  - An automated Playwright test, OR
  - A documented manual verification procedure in the test plan
- Test fixtures use real IJ content (extracted sample, not synthetic data)

---

## 7. Relationship to Future Milestones

M1's exit state becomes M2's entry state. The following properties must hold:

- **Extensibility**: Adding a 13th track requires only: (1) write a TrackExtractor subclass, (2) register it. No browser changes needed for basic rendering.
- **Multi-text readiness**: Project directory structure supports multiple projects. Server can serve multiple projects. No hardcoded single-project assumptions.
- **Alignment readiness**: W3C annotation format supports cross-text references (target.source identifies the text). PAF format supports multi-source annotations. These are not implemented in M1 but the data model accommodates them.
- **X readiness**: The TrackExtractor protocol is generic enough that user-defined tracks follow the same pattern. No special-casing for Base tracks that would block X tracks.

M1 is the foundation. It must be solid enough that M2-M5 never need to revisit M1 decisions.

---

*End of Document 26*

# Palimpsest Development Roadmap v2.0

**Date**: 2026-06-06
**Status**: Post-review rewrite — incorporates all 15 critical review findings
**Source**: Vision document (11), research corpus (00-10), critical review (12a)

---

## Principles

1. **Vertical slices, not horizontal layers.** Every milestone delivers a demonstrable capability. No milestone is "infrastructure only."
2. **Spec by building, not spec then build.** Formal specifications (LFO, PAF) are defined by implementing them — the code IS the spec. Lightweight documents explain decisions; they don't precede them.
3. **The AI assistant is the product.** LLM integration is not a bolt-on added in Phase 2. It's present from the first milestone. Every interaction should feel like working with an intelligent collaborator, not a dumb pipeline.
4. **One text first, two texts second, many texts last.**
5. **Test against ground truth from Day 1.** Swinehart IJ datasets are the validation benchmark for every pipeline component.
6. **X emerges from Base; never build X into Base.** If an X feature requires a Base code change, the Base abstraction is wrong.
7. **Degrade gracefully.** Every component has a fallback path. If BookNLP fails, fall back to spaCy. If the LLM isn't running, show Base tracks without AI assistance. If a PDF is garbled, show the user what was extracted and let them paste clean text.

---

## Technology Decisions (Resolved)

| Decision | Choice | Rationale |
|---|---|---|
| **Frontend framework** | React + TypeScript | JBrowse 2 is React/TypeScript; adopting the same stack enables adapter/renderer reuse |
| **State management** | MobX-state-tree | JBrowse 2's pattern; enables reactive linked views with minimal boilerplate |
| **Visualization** | D3.js + Canvas (via OffscreenCanvas in web workers) | D3 for custom views (chord, arc); Canvas for performance-critical views (dotplot, contact map) |
| **Backend** | Python 3.12+ / FastAPI | Ecosystem: spaCy, BookNLP, hmmlearn, sentence-transformers all Python |
| **Vector store** | sqlite-vec (embedded) | Local-first; no Docker dependency; lives in the project SQLite database |
| **Metadata store** | SQLite | Lightweight, portable, zero-config |
| **Embedding model** | Qwen3-Embedding via Ollama or MLX | Local, 2560-dim, fast on Apple Silicon |
| **Annotation LLM** | Qwen3:8B or Mistral 7B via Ollama | Local, structured output capable, fast enough for interactive use |
| **Annotation format** | W3C Web Annotation (JSON-LD) for interchange; PAF (GFF3-analogue TSV) for computation | Standards-based interchange + fast columnar computation |
| **Project structure** | Monorepo: `core/` (Python), `browser/` (React), `models/` (trained), `specs/` (LFO, PAF) | Clear separation; single git history |

---

## Phase 1: Walking Skeleton (8-10 weeks)

**Goal**: Import a text, compute Base tracks, view them in a browser with AI-assisted annotation — the complete product loop at minimum fidelity. Every subsequent phase deepens and polishes this skeleton.

### Milestone 1.1: Ingest + Normalize + First Track (Week 1-2)

Build the thinnest possible vertical slice: one text in, one annotation track out, visible in a browser.

**Deliverables**:
- `palimpsest ingest <file>` CLI (PDF/EPUB/TXT → normalized text + segments)
- Normalization: Unicode NFC, whitespace standardization, SHA-256 reference ID
- Segmenter: sentences (spaCy), paragraphs (whitespace), sections (heading heuristic)
- One Base track computed: **entities** (spaCy NER → PER, LOC, ORG)
- PAF format defined by this implementation (the code is the spec v0.1)
- LFO v0.1 defined by what this track produces (~15 terms: the structural + entity hierarchies)
- Minimal browser: React app rendering text with entity highlights
  - Not the full PTB — just text + colored spans + a track toggle
- Output stored in project directory:
  ```
  projects/{text-id}/
    ├── reference.txt
    ├── reference.sha256
    ├── segments.paf
    ├── tracks/entities.paf
    ├── metadata.json
    └── x-config/           (empty, scaffolded for Phase 2)
  ```

**Acceptance criteria**:
- Ingest IJ Chapter 1 (PDF) in <5 seconds
- Entity track detects "Hal", "Arizona", "University of Arizona"
- Browser displays text with entity highlights; click entity → detail tooltip
- PAF file validates against the (now-defined) PAF spec
- **Degradation**: If spaCy model not installed, print error with install instructions and skip entity track

**What this milestone defines by building it**:
- PAF column layout (empirically validated, not speculated)
- LFO initial terms (driven by actual tool output, not theoretical categorization)
- Project directory structure (proven to work, not designed in a vacuum)

### Milestone 1.2: Five Base Tracks + AI Summary (Week 3-5)

Expand from 1 track to 5 tracks. Introduce the LLM for the first time — as a passage summarizer.

**Deliverables**:
- Four additional Base tracks:
  - `sentiment.paf` — VADER sentiment per sentence (fast, no model download needed)
  - `lexical.paf` — per-paragraph: TTR, hapax count, mean word length, vocabulary richness
  - `dialogue.paf` — quotation spans detected by regex (quote marks + said-verbs)
  - `topics.paf` — LDA topic model (10 topics, per-paragraph distributions)
- LLM integration (first touch):
  - Ollama service manager: `palimpsest services start` / `stop`
  - Passage summarizer: select a passage → LLM generates a 2-sentence summary
  - Displayed in the detail panel when clicking an annotation
- Browser enhancements:
  - Track panel: list of 5 tracks with toggle, color swatch, count badge
  - Overview bar: document-level annotation density barcode (one bar per track)
  - Confidence slider (for tracks that have confidence scores)
- LFO expanded to ~40 terms (adding sentiment, lexical, dialogue, topic types)
- PAF spec updated if needed based on what the new tracks require

**Acceptance criteria**:
- All 5 tracks computed for full IJ in <30 seconds
- Toggling tracks on/off updates display in <100ms
- LLM summarizer produces coherent summaries for IJ passages (spot-check 10)
- **Degradation**: If Ollama not running, summarizer button shows "Start AI services to enable summaries" — all other features work

**Testing introduced here**:
- Unit tests for each feature extractor (input: known text → expected PAF output)
- Integration test: full pipeline on IJ Chapter 1 → validate all 5 PAF files
- Regression test: deterministic output (same input → same PAF, except LLM summaries)

### Milestone 1.3: BookNLP + Coreference + Self-Similarity (Week 5-7)

Complete the Base track set. Add the self-similarity dotplot view — the first "palimpsest-like" experience where hidden structure becomes visible.

**Deliverables**:
- BookNLP integration:
  - Character name clustering → merged into `entities.paf` with canonical character IDs
  - Coreference resolution → `coreference.paf` (pronoun → character links)
  - Quotation attribution → `dialogue.paf` updated with speaker assignments
  - **Fallback**: If BookNLP fails (Java dependency issues, memory), fall back to spaCy NER + regex dialogue. Log what was lost.
- Additional Base tracks:
  - `narrative_arc.paf` — Boyd 15-dimensional function-word arc
  - `self_similarity.paf` — pairwise segment cosine similarity matrix (embedding-based)
  - `rqa.paf` — recurrence quantification (RR, DET, LAM per window)
  - `alphabet.paf` — narrative alphabet (16-letter K-means on feature vectors)
- Embedding service:
  - Ollama-served embedding model
  - Batch embed all segments on ingest → stored in sqlite-vec
  - Similarity search: `GET /search?query=...&k=10`
- **DotplotView**: self-similarity matrix rendered as interactive heatmap
  - Canvas-based for performance (matrices 200-1000 rows)
  - Click cell → highlight both segments in text view
  - Zoom/pan
  - Color scale: similarity (white=low, dark=high)
- LFO expanded to ~60 terms. PAF spec finalized as v1.0.

**Acceptance criteria**:
- IJ dotplot shows visible diagonal blocks at chapter boundaries
- BookNLP clusters "Hal" / "Hal Incandenza" / "Hallie" correctly
- Coreference: >60% of pronouns in Chapter 1 resolved to named characters
- Self-similarity matrix for IJ Chapter 1 renders in <1 second
- **Walking skeleton test**: Import IJ → compute all 12 tracks → open browser → see text with 5 active annotation tracks → view dotplot → select a passage → see LLM summary. End-to-end in <3 minutes from clean start.

### Milestone 1.4: Full Text Browser (PTB v1.0) (Week 7-10)

Polish the browser into a professional, fluid tool. Add linked views and semantic zoom.

**Deliverables**:
- **TextLinearView** (polished):
  - Smooth scrolling for 300-page texts with 5+ active tracks
  - Semantic zoom: sentence-level annotations visible at close zoom; density bars at chapter zoom
  - Track rendering: configurable inline highlights, underlines, or margin markers per track
  - Annotation detail panel: full attributes, linked metadata, LLM summary
- **OverviewBar** (enhanced):
  - Per-track density barcodes
  - Click-to-navigate
  - Brush to select region → linked to text view
- **DotplotView** (enhanced):
  - Toggle similarity metric (cosine, lexical, topic)
  - Overlay structural boundaries (chapter markers)
- **Linked views**:
  - Shared MobX-state-tree selection state
  - Selecting text in TextLinearView highlights in OverviewBar and DotplotView
  - Clicking in DotplotView scrolls TextLinearView
- **Basic cross-text comparison** (first taste of alignment):
  - Import two texts → compute embeddings → paragraph-level cosine similarity matrix
  - Display as dotplot (text A on X axis, text B on Y axis)
  - Diagonal = aligned passages; off-diagonal = structural rearrangements
  - No Smith-Waterman yet — just raw similarity matrix. But the *experience* of seeing two texts compared is present.
- **Export**: annotations as W3C Web Annotation JSON-LD, PAF, or CSV

**Acceptance criteria**:
- Browser is responsive (smooth scroll, <100ms interaction latency) for full IJ (300+ pages, 12 tracks)
- Linked views work: selection propagates correctly in all directions
- Cross-text dotplot: two translations of the same work show a near-diagonal pattern
- Export → import round-trip preserves all annotations
- **Phase 1 exit gate**: A literary scholar imports a novel and produces a structural overview in <30 minutes

---

## Phase 2: Annotation + X Scaffold (6-8 weeks)

**Goal**: Enable human annotation, build the X extension mechanism, validate it with one IJ-specific custom track.

### Milestone 2.1: Human Annotation UI (Week 11-13)

**Deliverables**:
- Annotation mode in TextLinearView:
  - Select span → create annotation (type from LFO dropdown, attributes, note)
  - Edit/delete annotations
  - Keyboard shortcuts for rapid annotation
  - Annotations stored as W3C Web Annotations
  - Annotator identity tracked
- Annotation list view: sortable table of all annotations
- Import/export W3C JSON-LD and PAF
- Undo/redo for annotation operations

**Acceptance criteria**:
- Create 50 annotations on IJ Chapter 1 in <30 minutes
- Export → import round-trip preserves all data
- Undo correctly reverses any annotation operation

### Milestone 2.2: X Schema Builder + Detection Pipeline (Week 13-16)

**Deliverables**:
- Schema builder UI:
  - Define custom annotation type: name, attributes (typed), description
  - LLM assist: describe feature in natural language → LLM proposes schema
  - Save to `x-config/schemas/`
  - Schema versioning
- Detection strategy builder:
  - Per schema, define detection method:
    - Regex patterns
    - NER entity type matching
    - Embedding similarity threshold against a reference set
    - LLM structured extraction (prompt template + JSON schema)
  - Multi-stage pipeline builder (chain stages)
  - Test button: run on a sample passage
- Bootstrap workflow:
  - Run detection on full text → produce candidate annotations
  - Review UI: accept/reject/correct per candidate
- Active learning mechanism (specified precisely):
  - Corrections stored as labeled examples
  - LLM detection: corrections update the few-shot example bank in the prompt (up to 20 examples)
  - Threshold-based detection: corrections adjust the decision boundary via logistic regression on embeddings
  - Precision/recall metrics displayed after each correction round
  - Regression guard: if retrained model is worse on held-out validation set, roll back
- **Immediate X validation**: define the IJ "character presence per section" annotation type, run detection, correct results, verify active learning improvement

**Acceptance criteria**:
- "BookReference" schema for The Correspondent defined in <5 minutes with LLM assist
- Auto-detection pipeline finds >70% of explicit book references in a test passage
- After 50 corrections, false positive rate drops >30%
- IJ "character presence" track works correctly as a custom X track
- **No Base code changes required** to support the X track

### Milestone 2.3: Lightweight Alignment (Week 16-18)

**Deliverables**:
- Basic paragraph-level alignment using embedding similarity + greedy matching
- **AlignmentView**: side-by-side parallel text with connecting ribbons
  - Scroll synchronization
  - Ribbon color = similarity score
  - Gap regions highlighted
- Statistical output: coverage, mean similarity, number of aligned regions
- Not the full SW engine — a simplified alignment that delivers the cross-text experience

**Acceptance criteria**:
- Two Gospel accounts: visible parallel passages connected with ribbons
- Two unrelated texts: sparse connections, mostly gaps
- Smooth synchronized scrolling

---

## Phase 3: Full Alignment Engine (6-8 weeks)

**Goal**: Production-quality Smith-Waterman alignment with statistical significance, scoring matrix configuration, and annotation transfer.

### Milestone 3.1: Smith-Waterman Engine (Week 19-22)

**Deliverables**:
- Alignment engine (Python; performance-critical DP matrix in Rust via PyO3 or C extension):
  - Smith-Waterman (local) and Needleman-Wunsch (global)
  - Configurable similarity function: SBERT cosine, Jaccard, TF-IDF cosine, topic cosine
  - Affine gap penalty model
  - Multiple local alignment extraction via traceback
  - Gumbel distribution fitting for statistical significance (GNAT approach)
- CLI: `palimpsest align <projectA> <projectB> --mode local --similarity sbert`
- Output: alignment PAF file with paired spans, scores, p-values

**Acceptance criteria**:
- Two translations of same novel: >80% paragraph correspondence, p < 0.001
- Two unrelated novels: no significant alignments (p > 0.05)
- Runtime: <60 seconds for two 300-page novels at paragraph granularity
- Gumbel parameters: μ and β within 50% of GNAT paper's published values

### Milestone 3.2: Enhanced Alignment View + TextLiftoff (Week 22-26)

**Deliverables**:
- AlignmentView upgrades:
  - Multiple local alignments displayed simultaneously
  - P-value filter: show only statistically significant alignments
  - Alignment statistics panel: scores, coverage, significance histogram
- TextLiftoff annotation transfer:
  - `palimpsest transfer <source> <target>` CLI
  - Project source annotations onto target coordinates via alignment
  - Transfer confidence = alignment quality × original confidence
  - Report: unmapped annotations, novel target passages
- Variant comparison mode:
  - Two editions of same text: diff-style insertions/deletions/substitutions
  - Change statistics per chapter

**Acceptance criteria**:
- Transfer IJ Chapter 1 annotations to differently formatted edition: >90% successfully remapped
- Variant comparison: 1818 vs 1831 Frankenstein correctly identifies substantive changes

---

## Phase 4: First Full X Instance — Infinite Jest (4-6 weeks)

**Goal**: Prove the Base/X architecture by building a comprehensive IJ analysis.

### Milestone 4.1: IJ Custom Tracks (Week 27-30)

- Endnote cross-reference network (endnotes.csv → directed graph)
- Dual coordinate system (narrative order / chronological order from Swinehart data)
- Plotline classification (AA&R, E.T.A., A.F.R. — using LLM + active learning)
- Theme tags (from Swinehart themes vocabulary)
- Character initialism resolver (C.T. → Charles Tavis registry)
- Subsidized year translator

### Milestone 4.2: IJ Visualization Suite (Week 30-33)

- Endnote arc diagram (dual-arc, Swinehart "All Those Footnotes" style, D3)
- Character co-occurrence network (force-directed, D3 force simulation)
- Chronological timeline (sortable by narrative order or chronological order)
- All linked to TextLinearView via shared state

### Milestone 4.3: Validation + Report (Week 33-34)

- Quantitative comparison: Palimpsest annotations vs Swinehart/CPudney ground truth
- Inter-annotator agreement metrics (Cohen's Kappa per track)
- Systematic failure analysis: where does the platform get it wrong and why?
- Published validation report (part of the research output)

**Phase 4 exit gate**: All X features implemented via the extension mechanism with zero Base code changes. Agreement with ground truth >0.7 for entities, >0.5 for scene boundaries.

---

## Phase 5: Corpus-Scale + ModeHMM (6-8 weeks)

### Milestone 5.1: Corpus Manager + Batch Pipeline (Week 35-37)

- Corpus CRUD: create, add texts, batch-process
- Parallel pipeline execution (multiprocessing)
- Corpus-level SQLite index
- Corpus search by metadata and annotation type

### Milestone 5.2: ModeHMM Joint Training (Week 37-41)

- Training corpus: 60 Project Gutenberg novels (English, 1800-1950, diverse genres)
  - Selection criteria: genre diversity (10 each: romance, adventure, mystery, literary, horror, comedy)
  - Balanced by length (50K-200K words)
- Feature selection: 8 binarized signals per 100-word window:
  1. Elevated first-person pronoun rate (> median)
  2. Elevated dialogue marker density (> median)
  3. Elevated syntactic complexity (mean dependency depth > median)
  4. Elevated figurative language density (adjective/adverb ratio > median)
  5. Elevated named entity density (> median)
  6. Elevated punctuation density (> median)
  7. Present tense dominance (present tense verbs > past tense)
  8. Short sentence dominance (mean sentence length < median)
- Training: hmmlearn GaussianHMM, states K = {10, 15, 20, 25}, BIC model selection
- Validation:
  - Expert-labeled passages (20 passages × 3 genres, manually annotated with rhetorical mode)
  - Enrichment analysis: each learned state vs known literary features
  - Cross-validation: train on 50, validate on 10
- Apply to all corpus texts → consistent mode annotations
- Export trained model for reuse on new texts

### Milestone 5.3: Corpus Visualization + Motif Search (Week 41-43)

- Corpus barcode comparison (narrative alphabets side by side)
- Structural similarity matrix (pairwise text distance)
- Genre clustering (hierarchical)
- Motif search: regex over narrative alphabet sequences

---

## Phase 6: Second X Instance — The Correspondent (4-6 weeks)

**Goal**: Validate X generalization. Completely different text type, same extension mechanism.

### Milestone 6.1: Letter Segmenter + Book Reference Pipeline (Week 44-47)

- Letter boundary detection (salutation/closing patterns)
- Four-stage intertextual reference pipeline:
  1. Regex + NER for explicit titles/authors
  2. Embedding similarity against OpenLibrary/Wikidata title index
  3. LLM verification with structured output
  4. Human review in annotation UI
- Metadata enrichment from bibliographic APIs

### Milestone 6.2: Chord Diagram + Linked Views (Week 47-50)

- D3 chord diagram: letters arc × referenced books arc
- Color by genre/theme/author (user-selectable)
- Hover → show reference passage in context
- Linked to TextLinearView

**Phase 6 exit gate**: No Base code changes required. Book reference pipeline works end-to-end. Chord diagram functional.

---

## Stretch Goals (Phases 7-8)

These phases are valuable but not essential to the core product. Prioritize only after Phase 6 exit gate is met.

### Phase 7: Collaboration (4-6 weeks)
- Multi-user annotation server (FastAPI + PostgreSQL)
- WebSocket real-time sync (Apollo-style)
- Contested annotation UI (multiple views preserved with discussion)
- X configuration sharing (export/import portable packages)

### Phase 8: Advanced Visualization (4-6 weeks)
- Storyline visualization (character lines over time, crossing minimization via Liu et al. heuristic)
- Scroll-driven narrative (Swinehart-style scrollytelling, exportable as standalone HTML)
- Narrative contact map (StructureFold output, interactive TAD boundaries)

---

## Cross-Cutting Concerns

### Testing Strategy

| Level | What | When | Tool |
|---|---|---|---|
| **Unit** | Individual feature extractors, PAF parser, format converters | Every commit | pytest |
| **Integration** | Full pipeline: ingest → tracks → export | Every PR | pytest + fixtures |
| **End-to-end** | Import IJ → compute tracks → open browser → verify display | Weekly | Playwright |
| **Regression** | Deterministic output: same input → same PAF (excluding LLM outputs) | Every release | snapshot testing |
| **Benchmark** | Pipeline speed: 300-page novel track computation time | Every release | custom benchmark suite |
| **Validation** | Annotation quality vs Swinehart ground truth | Phase 4 | Cohen's Kappa |

### Pipeline Architecture

```
Ingest → Normalize → Segment → [Feature Extractors] → [Track Writers] → [Index]
                                      ↑ parallel ↑
                                 each track independent
```

- DAG orchestration: each track declares its dependencies (e.g., `coreference` depends on `entities`)
- Partial recomputation: adding a new track runs only that track + its dependencies
- Caching: intermediate results (embeddings, parsed docs) cached in project directory
- Invalidation: if reference text changes (different SHA-256), all tracks recompute

### Error Handling

| Component | Failure mode | Degradation path |
|---|---|---|
| PDF extraction | Garbled text (scanned PDF) | Show extracted text; prompt user to paste clean text or provide TXT |
| BookNLP | Java dependency failure | Fall back to spaCy NER + regex dialogue; mark tracks as "basic mode" |
| Embedding model | Model not downloaded | Auto-download on first use; fall back to TF-IDF similarity |
| LLM service | Ollama not running | All non-LLM features work; LLM features show "Start AI services" prompt |
| Alignment engine | Out of memory (very long texts) | Chunk texts into sections; align section-by-section |
| Custom detection | Regex error in user-defined pattern | Validate regex on save; show error with line highlight |

### Internationalization

Phase 1 is English-only, but the data model is language-agnostic:
- PAF carries no language assumption (character offsets work for any Unicode text)
- LFO terms are English labels but semantically universal (a "sentence" is a sentence in any language)
- Feature extractors are the language-dependent components; each declares its language support
- spaCy supports 60+ languages; sentiment dictionaries are English-only (documented limitation)
- Decision: non-English texts can be ingested and analyzed with available tracks; English-only tracks show a "not available for this language" indicator rather than failing silently

---

## Timeline Summary

| Phase | Duration | Cumulative | Core or Stretch |
|---|---|---|---|
| Phase 1: Walking Skeleton | 8-10 weeks | Week 10 | Core |
| Phase 2: Annotation + X Scaffold | 6-8 weeks | Week 18 | Core |
| Phase 3: Full Alignment Engine | 6-8 weeks | Week 26 | Core |
| Phase 4: First X Instance (IJ) | 4-6 weeks | Week 32 | Core |
| Phase 5: Corpus + ModeHMM | 6-8 weeks | Week 40 | Core |
| Phase 6: Second X Instance (Correspondent) | 4-6 weeks | Week 46 | Core |
| Phase 7: Collaboration | 4-6 weeks | Week 52 | Stretch |
| Phase 8: Advanced Visualization | 4-6 weeks | Week 58 | Stretch |

**Core product (Phases 1-6)**: 10-12 months for a single experienced developer; 6-8 months for a 2-person team.
**Full product (Phases 1-8)**: 14-16 months solo; 8-10 months for a 2-person team.

---

## Risk Registry

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| BookNLP unmaintained / incompatible | Medium | High | Fallback to spaCy NER + LLM-based character extraction; evaluate Gemini Flash for structured extraction |
| JBrowse 2 patterns too complex to adapt | Medium | High | Study architecture; build lighter custom equivalent inspired by it, not forking it |
| Local LLM quality insufficient | Low | High | Cloud API fallback for reasoning service; prompt engineering iteration |
| ModeHMM states not meaningful | Medium | Medium | Start with known-labeled passages; iterate on features; accept that some states may be "noise" |
| Single-developer motivation decay | High | Critical | Phase 1 alone delivers a usable tool; each phase has standalone value; recruit collaborators after Phase 2 demo |
| React ecosystem churn | Low | Medium | Pin major dependency versions; minimize number of UI libraries |

---

*This roadmap is the implementation plan for the Palimpsest vision (document 11). The critical review (document 12a) is preserved as an audit trail of the issues identified and resolved in this rewrite.*

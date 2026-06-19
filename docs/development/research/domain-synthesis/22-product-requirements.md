# Palimpsest: Product Requirements Document

**Date**: 2026-06-08 (v1.0); updated 2026-06-10 (v1.1 — F-BRW-007 through F-BRW-012, F-TRK-013 added for M2 Interactive Workbench)
**Version**: 1.1
**Status**: Active — enriched with Roadmap v4.0 (doc 28) features
**Source**: Vision Document (21), Conceptual Foundation (19), Roadmap v4.0 (28), genome browser research (IGV, IGB, JBrowse 2, D-GENIES)

---

## 1. Product Overview

### 1.1 Purpose
Palimpsest is a computational literary analysis platform that implements the genome browser paradigm for text. It automatically computes multi-track analytical annotations on any text, provides an interactive browser for exploring those annotations, enables human-AI collaborative creation of custom analytical tracks, and supports pairwise and corpus-scale text comparison through alignment.

### 1.2 Target Users
- **Primary**: Literary scholars, digital humanities researchers, computational linguists
- **Secondary**: Students in CL/DH programs, creative writing MFA programs
- **Tertiary**: Publishers, editors, translators doing structural analysis

### 1.3 Platform Constraints
- **Local-first**: All computation runs on the user's machine. No cloud dependencies for core functionality.
- **Apple Silicon optimized**: Primary target hardware is macOS with M-series chips (MLX for local LLM inference).
- **Standards-based**: W3C Web Annotation for interchange, GFF3-analogue (PAF) for computation, Literary Feature Ontology for vocabulary.
- **Open source**: All core components MIT or Apache 2.0 licensed.

---

## 2. Feature Requirements: Import & Normalization

### F-IMP-001: Text Ingestion (with Structural Extraction)
**Description**: Import text from PDF, EPUB, TXT, HTML, and Markdown formats. For structured formats (EPUB, HTML), extract and preserve structural metadata as annotation tracks: section/chapter boundaries, endnotes/footnotes, front matter markers, and publication metadata.
**Justification**: Scholars work with texts in diverse formats. PDF is the most common for scanned/published works; EPUB for digital editions; TXT for plain transcriptions. Structural metadata (chapters, endnotes) is not merely incidental — it is architecturally significant. Infinite Jest's 388 endnotes constitute a parallel narrative; discarding them into plain text destroys the text's structure. The genome analogy demands that structural features be preserved as annotation tracks, just as gene boundaries and regulatory elements are preserved in genome annotation.
**Acceptance**:
- Import a 300-page PDF novel in <30 seconds. Unicode NFC normalization. SHA-256 reference checksum. Paragraph and sentence boundaries detected.
- EPUB import: extract OPF metadata (title, author, ISBN, publisher, date); detect section boundaries from heading elements (h1-h6); extract endnote/footnote pairs with bidirectional call-site ↔ note-text links.
- EPUB import produces `tracks/sections.jsonl` (section boundary annotations with heading text) and `tracks/endnotes.jsonl` (endnote annotations with note number, full note text, call-site offsets).
- Enhanced `metadata.json` includes source_format, isbn, publisher, pub_date, endnote_count, section_count.
- Enhanced `coordinates.json` includes section_index mapping.
- Backward compatible: TXT/PDF imports produce identical output to current pipeline (no sections/endnotes tracks generated; no error).
**Stack**: Python (pymupdf for PDF, ebooklib + BeautifulSoup for EPUB, markdown-it for MD).

### F-IMP-002: Multi-Format Reference Text
**Description**: Store the canonical reference text as a normalized plain-text file with character-offset indexing. All annotations reference this file by offset.
**Justification**: Standoff annotation requires an immutable reference (Pustejovsky & Stubbs 2012; W3C Web Annotation Data Model). Character offsets are the "base-pair positions" of the literary genome.
**Acceptance**: `reference.txt` + `reference.sha256` in project directory. All tracks reference offsets into this file.

### F-IMP-003: Segmentation
**Description**: Automatically detect sentence boundaries (spaCy), paragraph boundaries (whitespace heuristic), and section boundaries (heading heuristic + TextTiling — Hearst 1997).
**Justification**: Segmentation is the text equivalent of gene prediction — the first structural decomposition. All higher-level analyses operate on segments.
**Acceptance**: Sentence, paragraph, and section boundaries stored in `segments.paf`. Section boundaries validated against chapter headings where present.

### F-IMP-004: Multiple Coordinate Systems
**Description**: Support multiple coordinate systems on the same text with explicit mapping functions. Minimum: character offset, paragraph index, page number, narrative order, chronological order (if applicable).
**Justification**: Genette (1972/1983) formalized that narrative order ≠ chronological order. Swinehart's Infinite Digest uses `pos` (narrative) vs. `seq` (chronological). Every annotation must specify its coordinate system.
**Acceptance**: `coordinates.json` defines available systems with bidirectional mapping functions. UI allows switching between systems.

---

## 3. Feature Requirements: Base Tracks

### F-TRK-001: Named Entity Recognition
**Description**: Detect and classify named entities (PER, LOC, ORG, WORK, EVENT) using BookNLP (Bamman et al. 2014) with spaCy fallback.
**Justification**: Character and place identification is the foundation for network analysis, co-occurrence tracking, and alignment-based character matching.
**Acceptance**: F1 ≥ 0.85 on LitBank evaluation set. Entity spans stored in PAF format with LFO type tags.

### F-TRK-002: Sentiment Trajectory
**Description**: Compute emotional valence trajectory using sliding-window hedonometer (Reagan et al. 2016) with configurable window size.
**Justification**: Emotional arc is one of the most effective structural fingerprints — 6 archetypal shapes discriminate story types at 0.99 AUC.
**Acceptance**: Float values per segment. Window size configurable (default: 1000 words, step: 100 words). Visualization as area chart in linear view.

### F-TRK-003: Lexical Features
**Description**: Compute per-segment: word frequency distribution, type-token ratio (TTR), hapax legomena count, vocabulary richness (Yule's K), mean word length, lexical density.
**Justification**: Standard corpus linguistics measures that reveal style, register shifts, and vocabulary patterns (Piper 2018 Ch. 1).
**Acceptance**: Feature vector per segment. Sparkline visualization per metric in linear view. Aggregate statistics in overview panel.

### F-TRK-004: Syntactic Complexity
**Description**: Compute per-sentence: dependency tree depth, subordination ratio, sentence length, POS distribution. Aggregate per segment.
**Justification**: Syntactic complexity correlates with register, difficulty, and author style (Nivre 2006; Tesnière 1959/2015). Dependency parsing also powers downstream tasks (character verb vectors for BookNLP).
**Acceptance**: Dependency parsing via spaCy. Per-segment complexity vector. Visualization as stacked bar chart (POS distribution) and line chart (complexity over narrative position).

### F-TRK-005: Dialogue Attribution
**Description**: Detect direct speech, identify speaker via BookNLP quote attribution pipeline.
**Justification**: Dialogue vs. narration is a fundamental structural distinction. Speaker attribution enables per-character speech analysis — what each character talks about, how they talk (Piper 2018 Ch. 5; StoryRibbons Yeh et al. 2025 pipeline).
**Acceptance**: Quote spans with attributed speaker entity. Visualization: colored spans in text view, dialogue proportion sparkline in overview.

### F-TRK-006: Narrative Arc
**Description**: Compute Boyd et al. (2020) 15-dimensional function-word arc: staging, plot progression, cognitive tension dimensions.
**Justification**: Three universal arc components validated across ~60,000 texts. Complementary to Reagan's sentiment arc — LIWC-based vs. sentiment-based.
**Acceptance**: 15-D vector per segment, reduced to 3-D (staging/progression/tension) for visualization. Multi-line chart in linear view.

### F-TRK-007: Self-Similarity Matrix
**Description**: Compute passage-pair similarity matrix (TextHiC) and derived metrics: recurrence rate (RR), determinism (DET), laminarity (LAM) via RQA (Amancio et al. 2022).
**Justification**: Self-similarity reveals recurring patterns, thematic echoes, and structural repetition (Church & Helfman 1993; Lieberman-Aiden et al. 2009 analog).
**Acceptance**: Passage-pair similarity matrix stored as sparse HDF5. Dotplot visualization in dedicated view. RQA metrics as summary statistics.

### F-TRK-008: LitHMM Passage States
**Description**: Train a multivariate HMM on combinatorial textual feature patterns (lexical density, dialogue ratio, NE density, sentiment volatility, sentence length variance) to assign each segment to a latent functional state.
**Justification**: ChromHMM (Ernst & Kellis 2012) discovers chromatin states from combinatorial histone marks. LitHMM discovers passage functional states from combinatorial text features. This is the core Palimpsest innovation — agnostic state discovery.
**Acceptance**: User-configurable number of states (default: 8-15). Each segment assigned a state label with posterior probability. State descriptions auto-generated from feature distributions. Color-coded track in linear view.

### F-TRK-009: Narrative Alphabet
**Description**: Encode each segment's multi-dimensional feature vector as a discrete state label via K-means clustering. The resulting 1D sequence of state labels IS the narrative alphabet.
**Justification**: Foldseek (van Kempen et al. 2023) encodes 3D structure as 1D sequence for fast comparison. Narrative alphabet enables fast structural comparison at corpus scale.
**Acceptance**: Alphabet size configurable (default: 32 states). Sequence stored as string. Alphabet consistent within a project for cross-text comparison.

### F-TRK-010: Coreference Chains
**Description**: Resolve pronominal references to character entities via BookNLP coreference.
**Justification**: 74% of character references in novels are pronouns (Bamman et al. 2014). Without coreference, character analysis misses three-quarters of mentions.
**Acceptance**: Coreference chains linked to entity track. Visualization: click any pronoun to highlight the full chain.

### F-TRK-011: Topic Distributions
**Description**: Compute topic distributions per segment using LDA (Blei et al. 2003) or embedding-based clustering.
**Justification**: Topic modeling at corpus scale discovers thematic patterns invisible to individual readers (Piper 2018 Ch. 3; Schöch 2017). Per-segment distributions enable topic evolution tracking.
**Acceptance**: Configurable number of topics (default: 20). Per-segment topic distribution vector. Top-3 topics labeled per segment. Stacked area chart in linear view.

### F-TRK-012: Thematic Compartments
**Description**: From the self-similarity matrix (F-TRK-007), compute A/B thematic compartments via first eigenvector decomposition, and TAD-like domains via directionality index + HMM segmentation.
**Justification**: Lieberman-Aiden et al. (2009) showed genome compartmentalization via eigenvector decomposition. Dixon et al. (2012) showed TAD segmentation via directionality index. Both apply directly to text.
**Acceptance**: Each segment labeled A or B (thematic compartment). TAD-like domain boundaries identified with HMM. Visualization as color-coded track + heatmap view.

---

## 4. Feature Requirements: Alignment & Comparison

### F-ALN-001: Pairwise Text Alignment
**Description**: Align two texts using Smith-Waterman local alignment with SBERT semantic scoring and Gumbel-calibrated significance (GNAT — Pial & Skiena 2023).
**Justification**: This is the "BLAST" of Palimpsest — the core comparison operation. Detects semantic parallelism even when surface language differs entirely.
**Acceptance**: Alignment output as PAF records with positions in both texts, alignment score, and p-value. Interactive visualization showing aligned segments with ribbons.

### F-ALN-002: Narrative Alphabet Alignment
**Description**: Align two texts by their narrative alphabet sequences using fast sequence alignment (Smith-Waterman on discrete state sequences).
**Justification**: Foldseek analog — orders of magnitude faster than semantic alignment, enabling corpus-scale structural search.
**Acceptance**: Structural alignment score. Aligned state sequences visualizable as parallel tracks.

### F-ALN-003: Multi-Text Comparison
**Description**: Align three or more texts simultaneously, displaying shared structural patterns.
**Justification**: Comparative literature requires simultaneous comparison (e.g., four Gospels, multiple translations, genre families).
**Acceptance**: Multiple sequence alignment visualization showing conserved and divergent regions across texts.

### F-ALN-004: Edition Comparison
**Description**: Character-level diff between two editions of the same text, with alignment preserving paragraph structure.
**Justification**: Textual scholarship (Eve 2019) requires precise identification of editorial changes. CollateX (Dekker & Van Hulle 2015) provides the collation methodology.
**Acceptance**: Diff visualization showing insertions, deletions, and substitutions at word level. Statistics on change density per chapter.

---

## 5. Feature Requirements: X-Schema System

### F-EXT-001: Custom Annotation Schema Creation
**Description**: Users define custom annotation types with typed attributes via a schema editor. AI proposes schemas based on user descriptions.
**Justification**: Every text has unique features that Base tracks don't capture. The X architecture (doc 11 §1.2) makes custom extensions a first-class operation, not an afterthought.
**Acceptance**: Schema editor UI. AI schema proposal from natural language description. Schemas stored as JSON Schema in project `x-config/` directory.

### F-EXT-002: AI-Bootstrapped Annotation
**Description**: Given a custom schema, the AI proposes initial annotations across the full text using a detection pipeline it designs.
**Justification**: Manual annotation of a 300-page novel is prohibitively slow. AI bootstrap + human correction (the BRAKER model — doc 09 §1.2) makes custom tracks practical.
**Acceptance**: AI generates candidate annotations with confidence scores. Human review UI for accept/reject/correct. Retraining after corrections.

### F-EXT-003: Annotation Liftover
**Description**: Transfer annotations from one text to another using alignment. E.g., transfer IJ character annotations to a different edition, or genre annotations across novels.
**Justification**: Genomic liftover (Liftoff tool) transfers annotations from reference assemblies to new assemblies. Same principle for text editions, translations, and adaptations.
**Acceptance**: Alignment-based coordinate projection. Confidence scoring for transferred annotations. Human review for ambiguous cases.

### F-EXT-004: Custom Visualization Components
**Description**: Users can register custom D3 visualization components per project.
**Justification**: Swinehart's work (doc 17) demonstrates that the most compelling visualizations are custom-designed for each text's unique structural properties.
**Acceptance**: Plugin architecture: register a React component + data adapter. Component appears in the view menu for the project.

---

## 6. Feature Requirements: Browser & Interaction

### F-BRW-001: Linear Browser View
**Description**: Multi-track annotation display along the character-offset axis, following JBrowse 2's adapter/track/display/renderer architecture (Diesh et al. 2023).
**Justification**: The genome browser paradigm is the most successful example of multi-layer annotation visualization in any domain. Doc 10 §Finding 1 provides the architectural blueprint.
**Acceptance**: Render 12 tracks simultaneously on a full novel. Smooth scroll at 60fps. Zoom from work-level to sentence-level. Track reordering and toggling.

### F-BRW-002: Circular View
**Description**: Circos-style visualization of long-range relationships (Krzywinski et al. 2009). Ribbons connect passages with relationship annotations.
**Justification**: Circular layout minimizes edge crossings in long-range relationship visualization. Swinehart's "All Those Footnotes" IS a Circos diagram.
**Acceptance**: Render up to 500 ribbons. Color encodes relationship type. Width encodes strength. Click ribbon → navigate to passage pair in linear view.

### F-BRW-003: Dotplot View
**Description**: Interactive self-similarity matrix with zoom and brushing (Church & Helfman 1993).
**Justification**: Dotplots reveal structural patterns invisible in other views: repetition (diagonal runs), thematic echoes (off-diagonal clusters), chiastic structure (anti-diagonal patterns).
**Acceptance**: Render up to 1000×1000 matrix at interactive speed. Canvas rendering for performance. Brush selection → highlight in linear view.

### F-BRW-004: Network View
**Description**: Character/entity interaction graph with Louvain community detection, betweenness centrality, and temporal evolution.
**Justification**: Character networks reveal structural properties of novels (Moretti 2011; Lubars et al. 2018; Elson et al. 2010).
**Acceptance**: Force-directed layout. Node size = betweenness centrality. Node color = community. Edge weight = co-occurrence with threshold slider. Click node → highlight character in linear view.

### F-BRW-005: Coordinated Multiple Views
**Description**: Linked highlighting, brushing, and synchronized navigation across all four views (Roberts 2007; Buja et al. 1996).
**Justification**: Analytical insights emerge from cross-view comparison. Selecting a passage in one view should propagate to all others.
**Acceptance**: Selection in any view highlights corresponding elements in all linked views within 100ms.

### F-BRW-006: Semantic Zooming
**Description**: Visual representation changes qualitatively with zoom level (Furnas 1986). At work level: density sparklines. At chapter level: track barcodes. At paragraph level: inline annotations. At sentence level: full detail.
**Justification**: Genome browsers implement this successfully. Users need overview + detail simultaneously. Progressive disclosure prevents overwhelm (Munzner 2014).
**Acceptance**: 4+ distinct zoom levels with qualitatively different renderings per track.

### F-BRW-007: Interactive Heatmap/TextHiC *(NEW — v4.0 M2.1)*
**Description**: Canvas-rendered self-similarity heatmap with zoom, pan, brush-to-zoom, axis annotation tracks, color scale legend, and similarity threshold slider. Informed by ModDotPlot (Sweeten 2024), D-GENIES (Cabanettes 2018), InteractiveComplexHeatmap (Gu 2016).
**Justification**: The current TextHiC is a static canvas with no zoom, no pan, no controls. Genome browser dot plots (JBrowse 2, D-GENIES) provide interactive exploration that reveals structural patterns at multiple scales.
**Acceptance**: Scroll-wheel zoom + drag pan on heatmap. Brush-select a region to zoom in. Axis annotation tracks show active track density. Click cell → side-by-side passage comparison. Export PNG/SVG.

### F-BRW-008: Character Entity System *(NEW — v4.0 M2.2)*
**Description**: Entity index built from coreference and entity annotations. Character panel with mention counts, co-occurrence matrix, chain following, and filter-by-character.
**Justification**: Coreference is currently rendered as a generic annotation track with no entity-level aggregation. Characters are the primary analytical subjects in narrative analysis.
**Acceptance**: Characters tab shows all characters with mention count and frequency sparkline. Click character → highlight all mentions. Co-occurrence matrix shows shared-paragraph counts between character pairs.

### F-BRW-009: Analysis Workbench UI *(NEW — v4.0 M2.3)*
**Description**: UI for triggering, configuring, and monitoring track analysis independently of import. Per-track run/re-run buttons, parameter dialogs, progress indicators.
**Justification**: All analysis currently runs at import time with no user control. Users need to configure parameters, run individual analyses, and re-run with different settings.
**Acceptance**: Import only does text extraction + segmentation. User selects which tracks to compute from Analysis tab. Can re-run LitHMM with different state counts. Progress bar per track.

### F-BRW-010: Multi-Tab Layout *(NEW — v4.0 M1.5)*
**Description**: Tabbed workspace with dedicated spaces for Reading, TextHiC, Characters, and Analysis. Each tab is a full view with its own controls and state.
**Justification**: Single-panel layout cannot accommodate growing feature surface. JBrowse 2's multi-view workspace and IGB's tabbed interface demonstrate this pattern.
**Acceptance**: 4 tabs functioning independently. Tab state preserved when switching. Coordinated selection propagation between tabs.

### F-BRW-011: Styled Tooltips *(NEW — v4.0 M1.5)*
**Description**: Every interactive element has a styled, immediate tooltip using Floating UI or Radix Tooltip. No native `title` attributes. Rich annotation hover showing body type, value, confidence, and text excerpt.
**Justification**: Native `title` tooltips appear after 500-1000ms OS delay and cannot be styled. Genome browsers (IGV, IGB) use immediate, informative tooltips for all interactive elements.
**Acceptance**: Zero native `title` attributes remaining. All tooltips render within 100ms with consistent styling.

### F-BRW-012: Responsive Overview Bar *(NEW — v4.0 M1.5)*
**Description**: Full-width barcode overview with viewport position indicator, track-specific rendering (density-barcode, state-band, ab-band per manifest), hover preview, and click-drag range selection.
**Justification**: Current OverviewBar is hardcoded 600px wide with no hover, no viewport indicator, and ignores manifest rendering types.
**Acceptance**: OverviewBar fills viewport width. Shows current viewport position as highlighted band. Hover shows track name + annotation preview. Supports state-band rendering for LitHMM.

### F-TRK-013: Alignment Method Selection *(NEW — v4.0 M2.1)*
**Description**: User-selectable similarity metric for self-alignment: cosine embedding similarity (current), word n-gram Jaccard, TF-IDF cosine, character-level edit distance. Configurable window size and overlap.
**Justification**: Different similarity metrics reveal different structural patterns. Word overlap finds verbatim repetition; semantic embedding finds thematic echoes; edit distance finds near-copies.
**Acceptance**: Dropdown in TextHiC tab to select method. Re-computation triggered by method change. Parameters (window size, overlap) configurable via sliders.

---

## 7. Feature Requirements: AI Integration

### F-AI-001: Local LLM Stack
**Description**: All AI inference runs locally via Ollama or MLX. No cloud dependencies.
**Justification**: Cost ($10-50/text at cloud rates), privacy (unpublished manuscripts), latency (sub-second for interactive use), reproducibility (pinned model versions).
**Acceptance**: Full pipeline runs on M1 Mac mini with 16GB RAM. Embedding model: Qwen3-Embedding (2560-dim). Annotation LLM: Qwen3:8B or equivalent.

### F-AI-002: Schema Proposal Agent
**Description**: Given a natural language description of a feature, propose an annotation schema (type name, attributes, data types) and a detection pipeline.
**Justification**: Schema creation is the hardest step for non-technical users. AI assistance makes X accessible.
**Acceptance**: User describes feature in 1-2 sentences → agent proposes schema within 5 seconds → user can edit before accepting.

### F-AI-003: Active Learning Loop
**Description**: After human corrections on AI-bootstrapped annotations, retrain the detection model to improve precision.
**Justification**: The MAKER/BRAKER iterative refinement model. Each correction makes future predictions better.
**Acceptance**: Precision improves measurably (≥5% F1) after 50 human corrections.

### F-AI-004: Perspectival Modeling
**Description**: Every classification and analysis reflects a specific interpretive perspective (Underwood 2019). Users can select, compare, and define perspectives.
**Justification**: Literary analysis has no objective ground truth. A classification is only meaningful relative to the criteria that generated it.
**Acceptance**: Every ML-generated annotation carries a `perspective` attribute identifying the model/training data that produced it. UI allows comparison between perspectives.

---

## 8. Feature Requirements: Data Formats & Standards

### F-FMT-001: Palimpsest Annotation Format (PAF)
**Description**: GFF3-analogue TSV format for computational annotation storage. Columns: chrom (document ID), source (tool), type (LFO term), start, end, score, strand (reading direction), phase, attributes.
**Justification**: GFF3 is the universal genome annotation interchange format (Eilbeck et al. 2005). PAF adapts it for text with literary-specific extensions.
**Acceptance**: PAF spec document. Parser/writer in Python and TypeScript. Validation tool.

### F-FMT-002: Literary Feature Ontology (LFO)
**Description**: Controlled vocabulary for literary features, modeled on the Sequence Ontology. Hierarchical, with defined relationships (is_a, part_of, derives_from).
**Justification**: Without a controlled vocabulary, annotation terms proliferate inconsistently across projects. The SO enables interoperability in genomics; the LFO enables it in literary analysis.
**Acceptance**: LFO v0.1 with ≥100 terms covering Base track outputs. OWL/RDF serialization. Term lookup API.

### F-FMT-003: W3C Web Annotation Interchange
**Description**: Export/import annotations in W3C Web Annotation Data Model (JSON-LD) format.
**Justification**: The W3C standard is the most interoperable modern annotation format. INCEpTION (Klie et al. 2018) and other DH tools speak it natively.
**Acceptance**: Round-trip conversion PAF ↔ W3C Web Annotation without data loss.

---

## 9. Non-Functional Requirements

### NFR-001: Performance
**Description**: Full novel (300 pages / ~100K words) ingested and Base tracks computed in <5 minutes. Browser renders 12 tracks at 60fps. Dotplot view handles 1000×1000 matrix interactively.
**Justification**: Alex Chen loads War and Peace with all tracks. It must work.
**Stack**: Rust for text processing, web workers for rendering, virtual scrolling, tiled rendering for large matrices.

### NFR-002: Scalability
**Description**: Support corpus-level operations on 100+ texts. Narrative alphabet alignment across full corpus in <1 hour.
**Justification**: Distant reading (Moretti 2013) operates at corpus scale. Palimpsest must eventually work there.
**Stack**: Batch processing pipeline. SQLite FTS5 for text search. sqlite-vec for embedding similarity.

### NFR-003: Portability
**Description**: Single-command setup on macOS and Linux. No Docker requirement for core functionality.
**Justification**: Scholars are not DevOps engineers. `pip install palimpsest` should work.
**Stack**: Python package with Rust extensions (PyO3/maturin). Browser served via built-in FastAPI.

### NFR-004: Extensibility
**Description**: Plugin architecture for custom tracks, views, adapters, and renderers.
**Justification**: JBrowse 2's success comes from its plugin ecosystem. Palimpsest needs the same.
**Stack**: React component registry for views. Python plugin registry for tracks and adapters.

### NFR-005: Reproducibility
**Description**: Every analysis run is fully reproducible. Pinned model versions, deterministic processing, version-controlled configurations.
**Justification**: Scholarly work must be reproducible. "I ran the analysis last year and got different results" is unacceptable.
**Stack**: Project-level config files specifying model versions, parameters, and random seeds. Lock files for dependencies.

---

## 10. User Narratives

### UN-001: First-Time Scholar
*Dr. Amara imports Infinite Jest. In 3 minutes, 12 Base tracks are computed. She opens the browser and sees entity highlights, sentiment trajectory, and LitHMM state colors. She zooms into a section she knows well and notices the LitHMM has colored it "bivalent" — contradictory feature signals. She realizes this passage is deeply ironic. She creates a custom "irony" annotation type, labels 20 examples, and the AI learns to detect more. Within an hour she has 47 irony annotations across the full novel, visualized as a track showing ironic density peaks.*

### UN-002: Comparative Literature Student
*Marcus loads four translations of the Bible. Palimpsest automatically aligns them at verse level. He opens the dotplot view and sees that one translation has significantly restructured the Psalms. He exports the alignment to his term paper with a Circos diagram showing cross-translation verse correspondence.*

### UN-003: Textual Scholar
*Prof. Whitfield loads two editions of Cloud Atlas (P and E, as in Eve 2019). Edition comparison shows 847 word-level differences. She filters by chapter and discovers that the changes cluster in the middle nested narrative. She exports the diff statistics and argues that the editorial process was more intensive in the structurally crucial nesting point.*

### UN-004: Power User (Alex Chen)
*Alex loads a corpus of 50 Victorian novels. He computes narrative alphabets for all 50 and runs corpus-level alignment. The structural clustering reveals three distinct "shapes" — not genre-based but structurally defined. He discovers that Charlotte Brontë's structural shape is closer to Dickens than to any other Brontë sister. He publishes this in a DH journal with the full Palimpsest project attached as supplementary material.*

---

*This PRD is the source of truth for all development planning. Every feature in the roadmap and milestone plans must trace back to a requirement here. No requirement should be implemented without being documented here first.*

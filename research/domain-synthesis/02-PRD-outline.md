# Palimpsest — Product Requirements Document (Draft Outline)

**Status**: DRAFT — awaiting integration of deep-reading results
**Date**: 2026-06-06
**Version**: 0.1

---

## 1. Vision Statement

Palimpsest is a computational literary analysis platform that treats texts as objects with multi-layered structure — analogous to how a genome encodes information across primary sequence, regulatory elements, 3D organization, and epigenetic marks. The platform enables researchers, students, and curious readers to parse, align, annotate, visualize, and explore the structural layers of written texts at scales from single passages to entire corpora.

### 1.1 Core Metaphor

A palimpsest is a manuscript in which earlier writing has been scraped off and overwritten, but traces of the earlier text remain visible. Every literary text is a palimpsest: it carries traces of its sources, its genre conventions, its cultural context, its revision history, and its structural architecture — layers that computational analysis can reveal.

### 1.2 Target Users

| User | Need | Platform Value |
|---|---|---|
| **Literary scholar** | Close reading augmented with quantitative evidence | Multi-track text browser with annotation layers |
| **Digital humanities researcher** | Corpus-scale pattern detection | Batch pipeline + narrative alphabet comparison |
| **Student** | Understand complex text structure | Interactive visualization of narrative architecture |
| **Creative writer** | Study structural craft in published works | Alignment comparison between own work and models |
| **Publisher/editor** | Track editorial changes across revisions | Variant-edition alignment (textual scholarship) |

---

## 2. Product Architecture (Layers)

### Layer 1: Data Handling & Ingestion

**What it does**: Accepts texts in multiple formats, extracts clean content, segments into analyzable units.

| Component | Function | Status |
|---|---|---|
| **Text Extractor** | PDF/EPUB/TXT/HTML → structured JSON | Built (pipeline stage 1) |
| **Text Cleaner** | Normalize encoding, strip boilerplate | Built (pipeline stage 2) |
| **Text Segmenter** | Chapter/paragraph/sentence splitting with offsets | Built (pipeline stage 3) |
| **Corpus Manager** | Import, organize, tag, search across multiple texts | Not built |
| **Format Export** | Output to docx, LaTeX, Markdown with annotations | Not built |

**Key design decisions**:
- All intermediate representations are JSON with character offsets
- Every annotation carries provenance (which module generated it, with what parameters)
- Storage: local filesystem + SQLite metadata index (lightweight, portable)

### Layer 2: Analysis & Feature Extraction

**What it does**: Computes linguistic, structural, and semantic features at multiple granularities.

| Component | Function | Status |
|---|---|---|
| **Signal Extractor** | Entropy, lexical diversity, dialog ratio, NER density, POS distribution | Built (pipeline stage 4) |
| **Narrative Encoder** | Feature vectors → 16-letter structural alphabet via KMeans | Built (pipeline stage 5) |
| **Semantic Embedder** | Sentence/paragraph embeddings for similarity search | Partial (SemanticAnalyzer exists) |
| **Entity Recognizer** | Named entities, characters, places | External (spaCy, BookNLP integration) |
| **Dialog Attributor** | Quotation detection + speaker identification | Not built (BookNLP integration planned) |
| **Sentiment Tracker** | Emotional arc computation via sliding window | Not built (Reagan/Syuzhet approach) |
| **Topic Modeler** | LDA/NMF topic distributions over segments | Not built |
| **Discourse Parser** | RST tree or simplified rhetorical structure | Not built (research-grade only) |
| **Self-Similarity Matrix** | Pairwise segment similarity → recurrence plot | Not built (Church & Helfman approach) |

### Layer 3: Alignment & Comparison

**What it does**: Establishes correspondences between texts (or text regions) at multiple structural levels.

| Component | Function | Status |
|---|---|---|
| **Sequence Alignment** | Smith-Waterman / Needleman-Wunsch on narrative alphabet | Not built (GNAT-inspired) |
| **Semantic Alignment** | Passage-to-passage mapping via embedding similarity | Not built |
| **Topic Flow Alignment** | SimDoc-style LDA sequence alignment | Not built |
| **Variant Alignment** | Edition-to-edition diff with structural awareness | Not built |
| **Cross-Reference Mapping** | Endnote/citation/allusion network extraction | Not built |
| **Temporal Alignment** | Map narrative order to chronological order (fabula↔syuzhet) | Not built (Swinehart data as validation) |

**Key technical decisions**:
- Scoring matrices should be configurable (different matrices for different comparison types)
- Statistical significance testing via Gumbel distribution (GNAT approach)
- Support both global (Needleman-Wunsch) and local (Smith-Waterman) alignment modes
- Multi-level alignment: word → sentence → paragraph → chapter → document

### Layer 4: Visualization & Browsing

**What it does**: Renders analyses as interactive, explorable visual representations.

| Component | Function | Status |
|---|---|---|
| **Text Browser** | JBrowse-inspired multi-track view along character-position axis | Not built |
| **Narrative Alphabet Barcode** | Colored segment-level structural fingerprint | Concept proven (pipeline output) |
| **Self-Similarity Dotplot** | Matrix visualization of intra-text repetition/structure | Not built |
| **Alignment View** | Side-by-side text with connecting lines showing correspondence | Not built |
| **Emotional Arc Plot** | Sentiment trajectory with annotation markers | Not built |
| **Character Network Graph** | Force-directed or storyline character interaction | Not built |
| **Circos/Arc Diagram** | Circular or arc visualization of cross-references | Not built |
| **Semantic Zoom** | Whole-text → chapter → paragraph → sentence detail levels | Not built |

**Key design principles** (from research):
- Always pair visualizations with computable metrics (Moretti's lesson)
- Support both exploratory and presentational modes
- Linked views: clicking in one view highlights corresponding regions in others
- Export publication-quality static images alongside interactive explorations

### Layer 5: Annotation & Knowledge Management

**What it does**: Supports human-in-the-loop annotation, glossary building, and iterative refinement.

| Component | Function | Status |
|---|---|---|
| **Manual Annotation** | Add/edit/delete annotations on any text span | Not built |
| **Glossary Builder** | Character registry, place registry, entity ontology | Not built |
| **Relationship Editor** | Define typed relationships between entities | Not built |
| **Annotation Import/Export** | TEI-XML, standoff, inline markup interoperability | Not built |
| **Collaborative Annotations** | Multiple annotators, inter-annotator agreement metrics | Not built |
| **Gold Standard Management** | Manage evaluation datasets for pipeline validation | Not built |

---

## 3. Core Workflows

### Workflow 1: Single-Text Deep Analysis
1. Import text → extract → clean → segment
2. Run feature extraction (all signals)
3. Compute narrative alphabet encoding
4. Generate self-similarity matrix
5. Compute emotional arc
6. Extract characters and dialog
7. View in text browser with all annotation tracks

### Workflow 2: Comparative Alignment
1. Import two (or more) texts
2. Choose alignment strategy (lexical, semantic, structural, topic-based)
3. Configure scoring matrix and gap penalties
4. Run alignment → get correspondence map
5. View in alignment view with connected parallel texts
6. Compute alignment statistics (score, significance, conservation regions)

### Workflow 3: Corpus-Scale Pattern Discovery
1. Import corpus (many texts)
2. Run pipeline on all → compute narrative alphabets
3. Build corpus-level indexes (alphabet FM-index, embedding ANN index)
4. Search for structural motifs across corpus
5. Cluster texts by structural similarity
6. Visualize corpus-level patterns (genre boundaries, stylistic change over time)

### Workflow 4: Iterative Annotation
1. Run automated analysis → produce initial annotations
2. Human reviews, corrects, extends
3. Corrections feed back to improve models
4. Export annotated edition (scholarly output)

---

## 4. Technical Architecture

### 4.1 Backend
- **Language**: Python 3.12+
- **Core pipeline**: standalone CLI scripts (composable, testable)
- **NLP**: spaCy, NLTK, sentence-transformers, optionally BookNLP
- **Embeddings**: local model (Qwen3-Embedding via MLX or sentence-transformers)
- **Storage**: SQLite for metadata, JSON for annotations, filesystem for texts
- **Search**: Qdrant for semantic search, suffix arrays for alphabet pattern search
- **API**: FastAPI REST server for frontend communication

### 4.2 Frontend
- **Framework**: SvelteKit or React (Swinehart uses SvelteKit for scroll-driven viz)
- **Visualization**: D3.js for custom visualizations, Canvas for large datasets
- **Text display**: Custom text renderer with annotation overlay (not a standard editor)
- **Layout**: Multi-panel with linked views (text + viz + annotations sidebar)

### 4.3 Data Model

```
Corpus
  └── Document
       ├── metadata (title, author, year, format, import date)
       ├── raw_text (original extracted text)
       ├── segments[] (with character offsets, hierarchy)
       │    └── features{} (per-segment computed features)
       ├── annotations[] (span-indexed, typed, attributed)
       ├── entities[] (characters, places, objects)
       ├── relationships[] (typed edges between entities)
       ├── narrative_alphabet (encoded string)
       └── alignments[] (to other documents, with correspondence maps)
```

---

## 5. MVP Scope (Phase 1)

Focus: single-text analysis with visualization.

**In scope**:
- Import PDF/EPUB/TXT
- Full pipeline (extract → clean → segment → features → encode)
- Text browser with 3 annotation tracks (NER, sentiment, narrative alphabet)
- Self-similarity dotplot
- Emotional arc visualization
- Narrative alphabet barcode
- CLI interface + basic web UI

**Out of scope for MVP**:
- Multi-text alignment
- Corpus-level operations
- Collaborative annotation
- BookNLP integration
- Character network visualization
- Circos/arc diagrams

---

## 6. Phase Roadmap

| Phase | Focus | Deliverable |
|---|---|---|
| **Phase 0** (done) | Research & pipeline | CLI pipeline, research library, conceptual framework |
| **Phase 1** | Single-text analysis + basic viz | Text browser, dotplot, arc plot, web UI |
| **Phase 2** | Pairwise alignment | Smith-Waterman narrative alignment, alignment view, variant comparison |
| **Phase 3** | Entity & character layer | BookNLP integration, character network, dialog attribution |
| **Phase 4** | Corpus-scale operations | Batch pipeline, corpus index, motif search, clustering |
| **Phase 5** | Annotation & collaboration | Manual annotation UI, glossary builder, export to TEI |
| **Phase 6** | Advanced visualization | Circos, storyline, Swinehart-style scrollytelling |

---

## 7. Success Criteria

### Technical
- Pipeline processes a 300-page novel in <30 seconds
- Narrative alphabet edit distance correlates with genre similarity (r > 0.5)
- Self-similarity matrix reveals known structural features (chapter boundaries, recurring motifs)
- Alignment between known parallel texts (e.g., two Gospel accounts) produces meaningful correspondence

### User
- A literary scholar can produce a structural analysis of a novel in 2 hours (vs. 2 weeks manual)
- A student can visually identify the narrative structure of a complex text within 5 minutes of importing it
- Computed annotations achieve >70% agreement with expert annotations on standard texts

---

## 8. Open Questions (for deep-reading results to inform)

1. What should the default scoring matrix look like for narrative alignment?
2. Is the 16-letter alphabet granular enough, or do we need 26 or 64 states?
3. What's the right embedding model for literary text (general vs. domain-fine-tuned)?
4. Should the text browser be modeled after JBrowse (genomics) or a code editor (VS Code)?
5. How should we handle texts with non-linear structure (hypertext, CYOA, endnote networks)?
6. What's the right balance between automated analysis and human annotation?
7. What file format should annotations be stored in (standoff JSON, TEI-XML, custom)?
8. Should Palimpsest be a desktop app, web app, or both?

---

*This is a living document. The deep-reading agents' results will refine sections 2-4 and resolve the open questions in section 8.*

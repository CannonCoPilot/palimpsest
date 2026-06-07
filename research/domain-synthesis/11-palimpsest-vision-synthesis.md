# Palimpsest: A Self-Rewriting Platform for Computational Literary Analysis

**Date**: 2026-06-06
**Status**: Capstone vision synthesis — integrates all prior research (documents 00-10, 366KB, 140+ citations)
**Version**: 1.0

---

## 0. The Name Is the Architecture

A palimpsest is a manuscript that has been scraped clean and rewritten — but the earlier layers remain, faintly visible beneath the new text. The name encodes three meanings simultaneously:

1. **The object of study**: Literary texts are palimpsests. Every work carries traces of its sources, genre conventions, cultural context, revision history, and structural architecture — layers that computational analysis can reveal.

2. **The analytical method**: Palimpsest *the platform* uncovers hidden structure by layering multiple computational analyses atop the same text — NER, sentiment, topic models, structural segmentation, intertextual reference maps — each layer revealing something the others cannot.

3. **The platform itself**: Palimpsest rewrites and evolves itself for each new text. The Infinite Jest version of the platform has different annotation schemas, different custom tracks, different trained models than the New Testament version or the Origin of Species version. Each text's analysis becomes a new layer of the platform's own accumulated intelligence.

---

## 1. The Base/X Architecture

### 1.1 Palimpsest Base: Universal Feature Tracks

Every text, regardless of genre, period, language, or form, can be analyzed through a set of **universal feature tracks** — analyses that are meaningful for any written work. These form the Base platform:

| Track Category | Universal Tracks | Source Algorithm |
|---|---|---|
| **Segmentation** | Sentence, paragraph, section boundaries | TextTiling + embedding discontinuity |
| **Entities** | Named entities (PER, LOC, ORG, WORK) | BookNLP / spaCy + LitBank fine-tuning |
| **Sentiment** | Emotional valence trajectory | Sliding-window hedonometer (Reagan) |
| **Lexical** | Word frequency, TTR, hapax legomena, vocabulary richness | Standard corpus linguistics |
| **Syntactic** | POS distribution, sentence length, syntactic complexity | spaCy dependency parsing |
| **Dialogue** | Quotation detection, speaker attribution | BookNLP quote attribution |
| **Narrative arc** | Staging / plot progression / cognitive tension | Boyd 15-dimensional function-word arc |
| **Self-similarity** | Recurrence plot, recurrence quantification (RR, DET, LAM) | Church-Helfman dotplot + RQA |
| **Structural mode** | Passage functional state (expository, dramatic, reflective...) | ModeHMM (ChromHMM-analogue, jointly trained) |
| **Narrative alphabet** | 16-64 letter structural encoding per segment | K-means on feature vectors |
| **Coreference** | Pronoun → character resolution | BookNLP coreference |
| **Topics** | Topic distributions per segment | LDA / embedding-based clustering |

These tracks are computed automatically on import. They require no configuration, no human annotation, and no text-specific knowledge. They are the **genome sequence** of any text — the raw data from which all higher-level analyses are derived.

### 1.2 Palimpsest-X: Per-Text Adaptive Extensions

The truly interesting analysis begins when a human reader engages with a specific text and discovers features unique to it. Palimpsest-X is the platform layer that adapts to each text:

| Extension type | Example | How it adapts |
|---|---|---|
| **Custom annotation schemas** | IJ: "subsidized year" translations; Correspondent: book references in letters; Bible: cross-verse citation links | User defines annotation type + attributes; LLM bootstraps detection |
| **Text-specific entity ontology** | IJ: character initialisms (C.T. = Charles Tavis); Ulysses: Dublin street map; Origin: species taxonomy | LLM reads text + reader's guide → proposes entity registry; human refines |
| **Custom coordinate systems** | IJ: narrative order vs chronological order; epistolary novels: letter sequence | User defines coordinate mapping; platform projects all annotations into both systems |
| **Domain-specific scoring matrices** | Biblical parallels need different alignment scoring than Victorian edition comparison | LLM analyzes text pair → proposes substitution weights; validated against known parallel passages |
| **Trained classifiers** | "Is this passage ironic?" trained on 200 human-labeled examples from this author | Active learning loop: LLM proposes → human corrects → model retrains → LLM improves |
| **Custom visualization components** | Endnote arc diagram for IJ; geographic map overlay for Ulysses; phylogenetic tree for folktale corpus | Plugin architecture: new D3 components registered per project |

### 1.3 How X Emerges from Base

The critical insight is that Palimpsest-X features are not hand-coded per text — they **emerge from the interaction between a human reader and an AI assistant** working with the Base platform:

```
Reader imports text
  → Base tracks computed automatically
  → Reader notices something the Base tracks don't capture
     (e.g., "these letters contain book references")
  → Reader describes the feature to an AI agent
  → Agent proposes:
     - An annotation schema (IntertextualReference with attributes)
     - A detection strategy (NER for titles + embedding similarity)
     - A visualization (chord diagram by genre)
  → Reader refines and approves
  → Agent implements the custom track
  → New track becomes part of this text's Palimpsest-X configuration
  → Detection model improves as reader corrects false positives
```

This is the MAKER evidence model applied to the platform itself: the AI provides ab initio predictions, the text provides structural evidence, and the human reader provides the expert curation that turns a generic analysis into a text-specific scholarly instrument.

---

## 2. The LLM Integration Architecture

### 2.1 Why Local LLMs

Palimpsest should run its AI services locally, not via cloud APIs. The reasons are practical, not ideological:

1. **Cost**: Literary analysis is token-heavy. A 300-page novel is ~100K tokens. Running 20 analytical passes over it (NER, sentiment, topic modeling, etc.) at cloud API rates would cost $10-50 per text. Locally, the marginal cost is electricity.

2. **Privacy**: Scholars working with unpublished manuscripts, copyrighted texts, or sensitive materials cannot send them to external servers.

3. **Latency**: Interactive annotation requires sub-second response times. Cloud round-trips add 200-500ms per query. Local inference on Apple Silicon is comparable.

4. **Customization**: Fine-tuned models for literary domains (LitBank-trained NER, author-specific classifiers) are easier to deploy locally than to host on cloud endpoints.

5. **Reproducibility**: Pinned local model versions ensure that an analysis run today produces the same results next year.

### 2.2 The Model Stack

| Role | Model type | Example | Use case |
|---|---|---|---|
| **Embedding** | Dense encoder, 2048-4096 dim | Qwen3-Embedding, nomic-embed-text | Semantic similarity, passage retrieval, self-similarity matrices |
| **NER / classification** | Small fine-tuned transformer | LitBank-trained spaCy/Flair models | Named entity recognition, genre classification, scene boundary detection |
| **Annotation assistant** | 7-14B instruction-tuned LLM | Qwen3:8B, Llama 3.1:8B, Mistral 7B | Schema proposal, bootstrap annotation, draft summaries |
| **Deep analysis** | 30-70B LLM | Qwen3:30B, Llama 3.1:70B, or cloud fallback | Complex reasoning: irony detection, thematic analysis, intertextual interpretation |
| **Structured extraction** | Any LLM with JSON mode | Ollama + structured output | Character relationship extraction, event chain identification, plot function classification |
| **HMM / statistical** | Custom trained models | hmmlearn, pomegranate | ModeHMM (rhetorical state), PassageStateHMM (functional annotation) |

### 2.3 The Agentic Workflow

Palimpsest-X features are created through **agentic workflows** — multi-step AI processes that a human reader initiates and supervises:

**Workflow: Build a Custom Annotation Track**

```
1. Reader describes the feature:
   "I want to find all book references within the letters"

2. Schema Agent proposes annotation type:
   {
     type: "BookReference",
     attributes: {
       referencedWork: "string (title)",
       referencedAuthor: "string",
       referenceType: "enum: [explicit, allusion, thematic_echo]",
       genre: "string[]",
       themes: "string[]"
     }
   }

3. Detection Agent proposes pipeline:
   Stage 1: Regex + NER for explicit titles/authors
   Stage 2: Embedding similarity against OpenLibrary title database
   Stage 3: LLM verification (is this actually a book reference?)

4. Bootstrap Agent runs the pipeline on the full text:
   → Produces ~200 candidate annotations with confidence scores

5. Human reviews candidates in annotation UI:
   → Accepts 150, rejects 30, corrects 20

6. Retrain Agent fine-tunes detection model on corrected data:
   → Precision improves from 75% to 92%

7. Visualization Agent proposes display:
   → Chord diagram (letters × referenced books, colored by genre)
   → Inline highlights in text view
   → Distribution barcode in overview

8. Reader iterates: "Can you also detect when characters
   discuss reading habits without naming a specific book?"
   → Agent extends the schema with a new referenceType: "indirect"
   → Cycle repeats
```

This workflow is the literary equivalent of the genome annotation pipeline: BRAKER (unsupervised bootstrap) → MAKER (evidence integration) → Apollo (human curation) → retrain → iterate.

### 2.4 The Self-Rewriting Mechanism

Each Palimpsest-X instance accumulates knowledge:

- **Trained models**: Scene boundary detectors trained on this text's corrections
- **Custom schemas**: Annotation types specific to this work
- **Entity registries**: Character names, aliases, relationships verified by the reader
- **Detection rules**: Regex patterns, embedding thresholds, classification boundaries
- **Visualization configurations**: Track layouts, color schemes, linked view setups

This accumulated knowledge is the platform's own **palimpsest layer** — a layer of intelligence written atop the Base platform by the interaction between reader and AI. When a reader begins analyzing a new text:

1. The Base tracks compute universally.
2. The platform offers: "This looks like an epistolary novel. Would you like to import the letter-detection and book-reference schemas from your Correspondent project?"
3. The reader accepts, modifies, or builds new schemas.
4. The cycle continues, accumulating new layers.

Over time, the platform builds a **library of analytical patterns** — not just data, but *trained analytical capabilities* that transfer across texts. The IJ analysis produces a non-linear-chronology handler; the Bible analysis produces a cross-reference network builder; the Origin of Species analysis produces a taxonomic entity tracker. Each becomes a reusable component.

---

## 3. Challenges by Text Type

### 3.1 The Diversity Problem

The genome annotation world benefits from a universal grammar: all genomes are DNA, all genes encode proteins, all regulatory elements bind transcription factors. Literature has no such universal grammar. The challenges vary radically by text type:

| Text type | Unique challenges | What Base tracks miss | What X must provide |
|---|---|---|---|
| **Dense modernist novel** (IJ, Ulysses) | Non-linear chronology, unreliable narrator, endnote networks, stream of consciousness | Narrative order ≠ chronological order; Base sentiment misreads irony; dialogue attribution fails in SOC | Custom temporal coordinate system; irony-aware sentiment; SOC passage detector |
| **Epistolary novel** (The Correspondent) | Letter boundaries are functional units; intertextual references within dialogue; multiple narrator voices | Base segmentation misses letter structure; NER doesn't know "book reference" as an entity type | Letter segmenter; BookReference annotation type; per-character voice classifier |
| **Sacred text** (Bible, Quran) | Verse-level granularity; massive commentary tradition; cross-verse citation networks; translation comparison | Base segmentation too coarse for verses; no concept of "verse parallel" | Verse-aligned multi-translation viewer; citation network graph; commentary integration |
| **Scientific treatise** (Origin of Species) | Argument structure; evidence citation; taxonomic hierarchy; historical context | Base tracks are narrative-focused; no argument structure track; no taxonomic entity type | Argument-structure track (claim/evidence/warrant); species entity ontology; historical context timeline |
| **Poetry collection** | Line/stanza structure; meter and rhyme; sound patterning; compression of meaning | Base tracks are prose-focused; no meter track; sentence segmentation fails on enjambment | VerseFormScan; phonemic analysis track; enjambment-aware segmentation |
| **Drama** (Shakespeare) | Act/scene/speech structure; stage directions vs dialogue; soliloquy vs dialogue; verse vs prose shifts | Base dialogue attribution doesn't understand dramatic convention; no concept of stage direction | Drama-aware segmenter; speech-act classifier; verse/prose transition detector |
| **Oral epic** (Iliad, Beowulf) | Formulaic composition; oral-formulaic theory (Parry-Lord); ring composition; catalogue passages | Base repetition detection doesn't distinguish formula from quotation; no concept of ring structure | Formula database (AllusioDB for oral tradition); ring-composition detector; catalogue annotator |
| **Hypertext / digital literature** | Non-linear reading paths; conditional content; multiple endings; reader agency | Base assumes linear text; no concept of branching or conditional display | Graph-based text model; reading-path tracker; CYOA structural analysis (Swinehart-style) |

### 3.2 How LLMs Address These Challenges

The key insight is that **LLMs can serve as the "BRAKER" for any text type** — they can learn the text's own patterns without requiring pre-labeled training data:

**Challenge: Non-linear chronology**
- LLM reads the text + any available reader's guide
- LLM proposes a chronological event sequence
- Human verifies/corrects the sequence
- Platform builds the dual coordinate system automatically

**Challenge: Irony detection**
- Base sentiment gives a "positive" score
- LLM reads the passage in context and flags: "This is ironic — the surface sentiment is positive but the narrative context (the character just lost everything) indicates the intended affect is negative"
- Human confirms
- Irony classifier trained on confirmed examples

**Challenge: Domain-specific entities**
- LLM reads the text and proposes: "This text contains references to ~45 distinct species. Would you like me to build a species entity ontology?"
- LLM extracts species mentions with Linnaean names, common names, and page references
- Human corrects misidentifications
- Species NER model fine-tuned on corrections

**Challenge: Structural forms specific to a genre**
- LLM detects: "This text uses ring composition (ABCBA) at the chapter level"
- LLM proposes a ring-structure annotation schema
- Reader confirms or refines the structural analysis
- Ring-composition detector added to this text's X configuration

### 3.3 The Transfer Learning Pipeline

When a reader moves from one text to another, the platform should intelligently offer applicable X components:

```
Reader finishes IJ analysis (X-IJ components):
  - Non-linear chronology handler
  - Endnote network builder
  - Character initialism resolver
  - Subsidized-year translator

Reader begins Ulysses analysis:
  Platform offers: "Ulysses also has non-linear chronology and
  extensive intertextual reference networks. Import from X-IJ?"

  Reader accepts chronology handler (applicable)
  Reader declines endnote builder (Ulysses uses no endnotes)
  Platform suggests: "Ulysses has Homeric parallels as a unique
  structural layer. Would you like me to build a parallel-episode
  annotation schema?"
```

This transfer is mediated by LLM reasoning: the agent compares the structural profile of the new text (Base track signatures) against the profiles of previously analyzed texts, identifies which X components are likely transferable, and proposes adaptations.

---

## 4. The Universal Tool Taxonomy

From the genome annotation research (document 09), Palimpsest has 18 proposed analytical tools organized in a hierarchy that mirrors the genome annotation stack. These tools are the building blocks that both Base and X draw from:

### 4.1 Segmentation & Structure Discovery

| Tool | Function | Base or X? |
|---|---|---|
| **NarrativeMAKER** | Evidence-integrated scene/episode segmentation with AED confidence | Base (default segmentation) |
| **StyleBRAKER** | Unsupervised self-training from reader engagement signals | X (adapts per text) |
| **RhetoriKa** | Rapid batch rhetorical figure annotation via tiered pattern lookup | Base (universal patterns) |
| **StructureFold** | Narrative domain calling via contact maps + insulation scores | Base (universal) |

### 4.2 Feature Detection & Classification

| Tool | Function | Base or X? |
|---|---|---|
| **ModeHMM** | Jointly-trained rhetorical mode state classifier | Base (universal mode vocabulary) |
| **FormInfernal** | Structural pattern search via literary covariance models | X (requires genre-specific models) |
| **VerseFormScan** | Dedicated verse form detection with isotype classification | X (poetry only) |
| **AllusionMasker** | Borrowed language detection and masking via AllusioDB | X (requires reference corpus) |
| **StyleG4Hunter** | Local stylistic intensity scoring | Base (universal) |

### 4.3 Relational Analysis

| Tool | Function | Base or X? |
|---|---|---|
| **EchoFinder** | Foreshadowing-fulfillment link prediction | X (requires training pairs) |
| **NarrativeKEGG** | Structural completeness scoring against known narrative schemas | X (requires schema library) |
| **NarrativePseudofinder** | Narrative decay/dysfunction detection | X (requires reference text) |
| **TextLiftoff** | Annotation transfer across editions/translations | X (requires aligned editions) |

### 4.4 Infrastructure

| Tool | Function | Base or X? |
|---|---|---|
| **MarginDetector** | Structural periphery and digression detection | Base (universal) |
| **ScholiaApollo** | Collaborative scholarly annotation over evidence tracks | Base (UI component) |
| **Palimpsest Text Browser** | JBrowse 2-style multi-track text browser | Base (core UI) |

### 4.5 Emerging from Reader Interaction

The most important tools are the ones that don't exist yet — the ones that emerge when a reader encounters something no existing tool handles:

- A reader analyzing The Canterbury Tales discovers that the **frame narrative** structure (story-within-a-story) requires a tool for tracking narrative embedding depth
- A reader analyzing a graphic novel discovers that **image-text relationships** require a multimodal annotation layer
- A reader analyzing parliamentary debates discovers that **speaker turn-taking patterns** require a discourse-flow visualization

Each of these becomes a new tool — first implemented as an ad-hoc X extension, then potentially promoted to Base if it proves useful across multiple texts.

---

## 5. The Data Architecture

### 5.1 The Layered Store

```
Palimpsest Data Architecture
│
├── TEXT LAYER (immutable)
│   ├── Raw text (Unicode NFC normalized — the "reference genome")
│   ├── Character offset index
│   └── Structural markup (chapters, sections, paragraphs) — TEI-encoded
│
├── BASE ANNOTATION LAYER (computed, reproducible)
│   ├── W3C Web Annotations (JSON-LD)
│   ├── One annotation set per Base track
│   ├── All carry source provenance + confidence scores
│   └── Recomputable from text + model versions
│
├── X ANNOTATION LAYER (learned, per-text)
│   ├── W3C Web Annotations (JSON-LD) with custom body types
│   ├── Custom annotation schemas (versioned)
│   ├── Trained model checkpoints
│   ├── Entity registries (character ontology, place gazetteer)
│   └── Detection rules and thresholds
│
├── HUMAN ANNOTATION LAYER (curated, authoritative)
│   ├── W3C Web Annotations with annotator identity
│   ├── Inter-annotator agreement metrics
│   ├── Contested annotations (multiple views preserved)
│   └── Free-text reader notes and interpretations
│
└── META LAYER (platform knowledge)
    ├── Cross-text transfer registry (which X components apply where)
    ├── Model performance metrics per text
    ├── Annotation correction logs (for active learning)
    └── Visualization configurations
```

### 5.2 The Format Standard

All annotations use the **W3C Web Annotation Data Model** (JSON-LD), extended with Palimpsest-specific body types. The annotation format is NOT proprietary — it is the same format used by Hypothes.is, INCEpTION, Recogito, and the broader scholarly annotation ecosystem.

For genome-style track operations (filtering, intersection, coverage computation), annotations can be exported to a **PAF (Palimpsest Annotation Format)** — a GFF3 analogue with character offsets replacing base-pair coordinates and a Literary Feature Ontology replacing the Sequence Ontology.

### 5.3 The LLM Service Layer

```
Palimpsest LLM Service Architecture
│
├── EMBEDDING SERVICE (always-on)
│   ├── Local model (Qwen3-Embedding via MLX or llama.cpp)
│   ├── Batch mode: index entire text on import
│   ├── Query mode: real-time similarity search during annotation
│   └── Backed by Qdrant vector store
│
├── ANNOTATION SERVICE (on-demand)
│   ├── Local 7-14B model (Ollama)
│   ├── Structured output (JSON schemas per annotation type)
│   ├── Schema proposal, bootstrap detection, draft summaries
│   └── Active learning: retrains on human corrections
│
├── REASONING SERVICE (on-demand, may use cloud fallback)
│   ├── Local 30-70B model or cloud API
│   ├── Complex interpretive tasks: irony, intertextuality, argument structure
│   ├── Schema design assistance
│   └── Transfer learning recommendations
│
└── AGENT ORCHESTRATOR
    ├── Multi-step workflow execution
    ├── Tool selection and chaining
    ├── Human-in-the-loop checkpoints
    └── Progress tracking and logging
```

---

## 6. The Palimpsest Text Browser

### 6.1 Architecture: JBrowse 2 Adapted for Text

The Palimpsest Text Browser (PTB) follows JBrowse 2's four-layer pluggable element hierarchy:

```
View (TextLinearView, ChordView, ContactMapView, DotplotView)
  └── Track (what data, what adapter)
       └── Display (how to render for a specific view type)
            └── Renderer (runs in web worker, draws to canvas)
       └── Adapter (data source: W3C Annotation endpoint, PAF file, etc.)
```

### 6.2 Semantic Zoom Levels

| Zoom level | What appears | Primary question |
|---|---|---|
| **Corpus** | Text-level barcodes for all texts in corpus | Which texts are structurally similar? |
| **Document** | Annotation density heatmap + structural overview | Where are the interesting regions? |
| **Chapter** | Distribution graphs + barcode per track | Which chapters are densest in this feature? |
| **Paragraph** | Highlighted spans with labels | What exactly is this annotation? |
| **Sentence** | Full annotation detail + linked metadata | What can be said about this specific span? |

### 6.3 Linked Views

All views share state via MobX-state-tree (following JBrowse 2's pattern):
- Selecting an annotation in the text view highlights the corresponding element in the chord diagram, the character network, and the timeline
- Filtering in any view propagates to all linked views
- Zoom/pan in the text view updates the position indicator in overview views

---

## 7. Resolved Open Questions

The original PRD (document 02) listed 8 open questions. The research corpus now answers all of them:

| # | Question | Resolution |
|---|---|---|
| 1 | What should the default scoring matrix look like for narrative alignment? | Configurable per comparison type. SBERT cosine similarity as default S(x,y); Gumbel-calibrated significance testing (GNAT approach). Domain-specific matrices proposed by LLM, validated against known parallel passages. |
| 2 | Is the 16-letter alphabet granular enough? | ModeHMM with 15-25 jointly-trained states (ChromHMM-inspired) replaces fixed-K alphabet. State count learned from data, not pre-specified. |
| 3 | What's the right embedding model? | Local model: Qwen3-Embedding-4B via MLX (2560-dim). Fast enough for interactive use; high enough quality for literary semantic similarity. |
| 4 | JBrowse or VS Code as text browser model? | JBrowse 2 architecture, definitively. Its Adapter→Track→Display→Renderer hierarchy is purpose-built for multi-layer overlapping annotations. VS Code's editor model is wrong for this use case. |
| 5 | How to handle non-linear structure? | Multiple coordinate systems per text (narrative order, chronological order, custom). All annotations specify which coordinate system they reference. Dual coordinate view with mapping function visualization. |
| 6 | Balance between automation and human annotation? | MAKER evidence model: AI generates predictions (E4-E5), text provides evidence (E1), cross-text homology provides constraints (E3), human curator adjudicates (E2). Active learning loop improves automation with each correction. |
| 7 | What annotation format? | W3C Web Annotation Data Model (JSON-LD). Interoperable with Hypothes.is, INCEpTION, Recogito. Supplemented by PAF (GFF3 analogue) for track-level operations. |
| 8 | Desktop, web, or both? | Web-first (SvelteKit or React). Local LLM services via Ollama/MLX. The browser handles visualization; local services handle computation. Electron wrapper optional for offline use. |

---

## 8. Revised Phase Roadmap

| Phase | Focus | Key Deliverables | Base or X |
|---|---|---|---|
| **Phase 0** | Research & design | This document corpus; tool taxonomy; format specifications | — |
| **Phase 1** | Base platform + text browser | PTB with 5 universal tracks; CLI pipeline; import/export | Base |
| **Phase 2** | LLM integration + annotation UI | Local model stack; schema builder; annotation workflow; active learning | Base + X scaffold |
| **Phase 3** | Pairwise alignment + variant comparison | SW alignment; alignment view; TextLiftoff; edition comparison | Base |
| **Phase 4** | First X instance: Infinite Jest | Full IJ analysis with custom tracks, chronology handler, endnote network | X (proof of concept) |
| **Phase 5** | Corpus-scale operations | Batch pipeline; ModeHMM joint training; corpus index; motif search | Base |
| **Phase 6** | Second X instance: The Correspondent | Book reference pipeline; chord diagram; letter segmenter; voice classifier | X (generalization test) |
| **Phase 7** | Collaborative annotation + sharing | Apollo-style collaboration; Hypothes.is integration; shareable X configurations | Base |
| **Phase 8** | Advanced visualization + scrollytelling | Swinehart-style scroll-driven narratives; Circos; storyline | Base |

---

## 9. Success Criteria (Updated)

### Technical
- Base pipeline processes a 300-page novel in <30 seconds
- ModeHMM state assignments achieve >0.7 agreement with expert-labeled passages across 10 diverse texts
- Self-similarity matrix correctly identifies >90% of known chapter boundaries
- Alignment between known parallel texts (Gospel accounts, variant editions) produces meaningful correspondence (AUC > 0.85)
- Custom annotation track from schema proposal to first pass takes <10 minutes with LLM assistance

### User
- A literary scholar can produce a multi-track structural analysis of a novel in 2 hours (vs. 2 weeks manual)
- A reader can define and populate a custom annotation type (like "book references") in under 30 minutes
- Computed annotations achieve >70% agreement with expert annotations before human correction
- After one round of human correction (50-100 examples), agreement rises to >90% via active learning
- A student can visually identify the narrative structure of a complex text within 5 minutes of import

### Platform
- X configurations from one text demonstrably transfer to a second text of the same type with <50% additional effort
- The platform accumulates a library of >20 reusable X components within the first year of use
- No X component requires modifying Base platform code — all extension via plugin/schema/model mechanisms

---

*This document synthesizes research from 11 domain-synthesis documents (366KB), 49 papers/books (500MB PDFs), and 140+ academic citations. It is the capstone of the Palimpsest research phase and the foundation for implementation.*

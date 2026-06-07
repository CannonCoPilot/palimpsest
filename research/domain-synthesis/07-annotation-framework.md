# Annotation as the Foundation Layer: From Genome Annotation to Literary Text Annotation

**Date**: 2026-06-06
**Status**: Working document — incorporates Swinehart/CPudney data analysis, genome annotation methodology mapping, and computational linguistics research

---

## 0. Why Annotation Is Harder Than Alignment

Alignment is a two-input problem: given text A and text B, find correspondences. Annotation is an open-ended, multi-layer problem: given text A, discover and record *everything that is happening in it* at every level of organization. In genomics, alignment came first historically (Smith-Waterman, 1981) but annotation quickly became the larger enterprise — the Human Genome Project spent far more effort on annotation (ENCODE, Roadmap) than on the initial sequencing alignment.

For Palimpsest, the same priority inversion applies. Alignment is the headline feature, but annotation is the foundation that makes alignment meaningful. You cannot align two texts by their character networks if you haven't first annotated who the characters are. You cannot compare thematic arcs without first identifying themes. Annotation is the infrastructure that every other analysis layer depends on.

### The Annotation Paradox

The fundamental paradox of literary annotation is that **the most valuable annotations are the ones that require the most human judgment**, while **the most automatable annotations are the ones that require the least**. A machine can count word frequencies, detect named entities, and compute sentiment scores. A human reader naturally notices that a character is being ironic, that a scene echoes an earlier one, or that the narrator is unreliable. The gap between what NLP can detect and what a thoughtful reader notices is *the core design problem* for Palimpsest's annotation architecture.

The genome annotation world solved an analogous problem with the **evidence-based annotation** paradigm (MAKER): combine multiple sources of evidence — ab initio prediction, transcript evidence, protein homology, cross-species conservation — and let the human curator adjudicate where they disagree. Palimpsest needs the same architecture: combine ML-generated annotations with human reading evidence and cross-text structural parallels, presenting the human annotator with pre-computed suggestions that they can accept, reject, or refine.

---

## 1. The Genome Annotation Stack and Its Literary Analogues

### 1.1 Gene Prediction → Scene/Episode Segmentation

| Genome tool | What it does | Literary analogue | Palimpsest equivalent |
|---|---|---|---|
| **MAKER** | Integrates ab initio gene predictions (Augustus, SNAP) with transcript evidence (RNA-seq) and protein homology to produce consensus gene models | Integrates ML-based text segmentation with human-marked scene boundaries and structural parallels from related texts | **EvidenceSegmenter**: combines topic-shift detection (TextTiling), sentence embedding discontinuity (SBERT cosine drops), and human-marked boundaries into consensus scene segmentation |
| **BRAKER** | Automated training of ab initio gene predictors using RNA-seq evidence — no manual curation required | Self-supervised training of scene segmentation models from a corpus of texts with known chapter/section structure | **AutoSegmenter**: train scene boundary detectors on texts with explicit structural markup (chapters, sections), then apply to texts without markup |
| **Prokka** | Lightning-fast prokaryotic annotation using pre-built databases — sacrifices some accuracy for speed | Fast annotation using pre-trained models and lookup tables — good enough for first-pass exploration | **QuickAnnotate**: pre-trained NER + sentiment + topic models applied in a single pass, producing a "draft annotation" in seconds |
| **Liftoff** | Transfers annotations from a reference genome to a new assembly of the same or closely related species | Transfers annotations from an annotated edition to a different edition, translation, or adaptation of the same work | **AnnotationTransfer**: given a fully annotated edition A and an unannotated edition B, use text alignment to project A's annotations onto B's coordinate system |
| **Apollo** | Web-based collaborative manual curation environment — multiple annotators can edit the same genome simultaneously | Collaborative reading environment where multiple readers can annotate the same text in real time | **CollabReader**: web-based annotation UI with real-time multi-user editing, annotation versioning, and conflict resolution |

#### The MAKER Evidence Model in Detail

MAKER's three-source evidence integration is the most important architectural pattern for Palimpsest:

1. **Ab initio predictions** = ML model outputs (NER, sentiment, topic segmentation, event detection)
2. **Transcript evidence** = the actual text itself (what the words say, verbatim quotations, explicit structural markers like chapter headings)
3. **Protein homology** = cross-text structural parallels (does a similar passage in a related work have an existing annotation?)

MAKER assigns **Annotation Edit Distance (AED)** scores measuring how well a gene model matches the evidence. Low AED = high confidence. Palimpsest should assign confidence scores to every automated annotation indicating how much evidence supports it: an NER detection confirmed by a human annotator in a related text has higher confidence than one generated by a model alone.

### 1.2 Feature-Specific Annotation → Domain-Specific Literary Feature Detection

| Genome tool | Biological feature | Literary analogue | Palimpsest equivalent |
|---|---|---|---|
| **MAPLE / KAAS** | Metabolic pathway assignment — maps predicted proteins to KEGG pathways | **Plot pathway assignment** — maps narrative events to archetypal plot structures (hero's journey stages, Proppian functions, genre conventions) | **PlotMapper**: classify each scene into plot-functional categories (inciting incident, rising action, climax, denouement) using learned models of narrative structure |
| **Infernal** | Non-coding RNA detection via covariance models that capture both sequence AND secondary structure | **Subtext detection** — identifying passages that function through implication, irony, or structural parallelism rather than explicit statement | **SubtextDetector**: detect passages where surface meaning diverges from contextual meaning using sentiment-context mismatch, unreliable narrator signals, and irony markers |
| **tRNAscan-SE** | Transfer RNA detection using highly specific structural models | **Transition marker detection** — identifying structural elements that mediate between narrative sections (scene breaks, temporal jumps, POV shifts) | **TransitionDetector**: identify and classify narrative transitions using trained models of temporal markers, spatial shifts, and focalization changes |
| **RepeatMasker** | Transposable element and repeat detection via homology search against known repeat databases | **Intertextual reference detection** — finding quotations, allusions, paraphrases, and formulaic phrases borrowed from other texts | **IntertextDetector**: search each passage against a reference library of known texts, identifying direct quotations (exact match), paraphrases (semantic similarity above threshold), and allusions (shared entity/concept clusters) |
| **Pseudofinder** | Pseudogene detection — identifying genes that have accumulated disabling mutations (frameshifts, premature stops) | **Vestigial element detection** — finding narrative threads that were introduced but never resolved, abandoned plotlines, red herrings | **VestigialDetector**: identify characters, themes, or plot threads introduced early in a text that are never referenced again after a certain point — potential abandoned threads or deliberate red herrings |

### 1.3 Epigenomic/Structural Annotation → Multi-Layer Functional State Assignment

This is where annotation becomes genuinely multi-dimensional — not just "what is this passage?" but "what is this passage *doing* in this context?"

| Genome tool | Information layer | Literary analogue | Palimpsest equivalent |
|---|---|---|---|
| **ChromHMM / Segway** | Chromatin state assignment from combinatorial histone mark patterns (15 states: active promoter, enhancer, repressed, etc.) | **Passage functional state** — what role does this passage play? Is it expository, dramatic, reflective, transitional, comedic, descriptive? States emerge from combinatorial feature patterns, not single features. | **PassageStateHMM**: train a multivariate HMM on feature vectors (lexical density, dialogue ratio, named entity density, sentiment volatility, sentence length variance) to assign each passage to one of N functional states. States are learned, not predefined. |
| **Akita / HiCExplorer** | 3D chromatin organization — TADs, loops, compartments from Hi-C contact data | **Narrative domain organization** — self-contained thematic units, long-range narrative callbacks, A/B compartment (active/latent) decomposition | **NarrativeFold**: build passage-pair similarity matrix, identify TAD-like self-interacting domains, detect statistically anomalous long-range "loop" connections between distant passages |
| **TargetFinder / EPIVAN** | Enhancer-promoter linkage — which distal regulatory elements control which genes? | **Foreshadowing-payoff linkage** — which early passages set up payoffs that are delivered later? Which thematic statements are "activated" by later narrative events? | **PayoffLinker**: identify statistically significant semantic connections between distant passages where the later passage resolves, inverts, or elaborates on the earlier one |
| **G4Hunter** | G-quadruplex detection — identifying sequence motifs that form non-canonical secondary structures | **Rhetorical figure detection** — identifying recurring syntactic or prosodic patterns (anaphora, chiasmus, periodic sentences, catalogues) that create local structural effects | **FigureDetector**: detect syntactic patterns, repetitive structures, and prosodic regularities that deviate from the text's baseline style |
| **LADetector** | Lamina-associated domain boundaries — identifying heterochromatic regions at the nuclear periphery | **Voice/register boundaries** — identifying transitions between narrative voices, registers, or modes (e.g., where a text shifts from narration to stream-of-consciousness, or from formal to colloquial) | **RegisterDetector**: detect shifts in lexical register, sentence complexity, and stylistic markers that indicate voice or mode transitions |

---

## 2. The Five Types of Text Annotation (from Swinehart Data Analysis)

Examining the Swinehart Infinite Digest datasets reveals five fundamentally different information types that coexist on a single text. Each requires a different data model, different ML approaches, and different visualization strategies.

### Type 1: Coordinate Systems (Where Things Are)

**Genomic parallel**: Physical position (base pairs) vs. genetic map distance (centimorgans) vs. cytogenetic bands (chromosome arms and regions)

**Literary instance**: Swinehart's `pos` (narrative order, 1-202) vs `seq` (chronological order, 1-202) in chapters.csv. These are two independent coordinate frames for the same 202 sections. The mapping between them IS the fabula/syuzhet function.

**Data model**: A coordinate system is a totally ordered set of positions with a defined metric (page numbers, word offsets, paragraph indices, timestamps). Multiple coordinate systems can be defined on the same text, with explicit mapping functions between them.

**What Palimpsest needs**: A robust multi-coordinate system. Every annotation must specify which coordinate system it references. The minimum viable set:
- **Linear offset** (character/word/sentence position from start of text)
- **Structural position** (chapter.section.paragraph)
- **Narrative position** (if non-chronological: position in author's presentation order)
- **Chronological position** (if reconstructible: position in story-internal timeline)
- **User-defined coordinates** (e.g., "letter number" for epistolary novels)

### Type 2: Entity Markup (Who and What Is Present)

**Genomic parallel**: Gene annotations on GFF3 — each gene has coordinates, strand, name, type, and attributes

**Literary instance**: Swinehart's character-tagged plotlines (`<gately>Gately</> watches <orin>Orin</> on TV`). Each mention is a span of text attributed to a character entity, with the entity having a canonical identity, aliases, group membership, and biographical attributes.

**Data model**: Standoff annotation — entities are stored separately from the text, with start/end offsets pointing into the text. Each entity has:
- Canonical ID (slug: `gately`, `hal`, `avril`)
- Display names and aliases (`Don Gately`, `Gately`, `Don G.`, `Big D.`)
- Type (person, place, organization, object, concept)
- Attributes (biographical, relational, categorical)
- Mention spans (list of [start, end] offsets in the text)

**ML approach**: Named Entity Recognition (BookNLP, LitBank-trained models) + coreference resolution (linking pronouns and aliases to canonical entities) + human correction

### Type 3: Categorical Overlays (How Things Are Classified)

**Genomic parallel**: Gene Ontology (GO) terms, KEGG pathway assignments, chromatin state labels — classification systems applied per-feature

**Literary instance**: Swinehart's `plotlines` column (`"AA&R, Gately"`) and `themes` column (`"Recur, Cycles, Fear/Obsess, Inf/Reg, Memory, Loss"`). These are independent controlled vocabularies applied per-section. Critically, they are specific to *this* text — "AA&R" (Addiction & Recovery) and "E.T.A." (Enfield Tennis Academy) are Infinite Jest categories, not universal ones.

**Data model**: Tag sets — each tag set is a controlled vocabulary (possibly hierarchical) that can be applied to any span of text. Tag sets are per-text or per-corpus, not universal. Each tag application has:
- Tag set ID (e.g., "IJ-plotlines", "IJ-themes")
- Tag value (e.g., "AA&R", "Recur")
- Span (which text region this tag applies to)
- Confidence (if ML-assigned)
- Annotator (if human-assigned)

**The per-text uniqueness problem**: This is the core design challenge. Unlike genomics where GO terms are universal, literary annotation categories are often specific to a single work. "AA&R" makes no sense outside Infinite Jest. "Book references" would be a category specific to The Correspondent. Palimpsest needs a tag set creation workflow that lets users define custom vocabularies per text, with the option to inherit from standard vocabularies (e.g., Proppian functions, narrative arc stages).

### Type 4: Cross-References (How Things Connect)

**Genomic parallel**: Enhancer-promoter interactions, chromosome conformation capture (Hi-C) contacts, regulatory network edges

**Literary instance**: Swinehart's endnotes.csv maps ref_page → note_page ranges. Also: character co-appearance (implicit cross-reference between passages sharing characters), thematic echoes, and the user's specific use case of book references within The Correspondent's letters.

**Data model**: Directed edges between text spans:
- Source span (start, end in some coordinate system)
- Target span (start, end — possibly in the same or a different text)
- Edge type (endnote, allusion, character co-occurrence, thematic echo, book reference)
- Edge attributes (for book references: author, title, genre, theme of referenced book)
- Evidence (how was this cross-reference identified — explicit text, ML detection, human annotation)

**The Correspondent use case in detail**: Each letter in the novel contains references to books. Each reference is a span in the letter text. Each referenced book has metadata (author, genre, publication year, themes). The cross-reference annotation links the reference span to the book metadata. Visualization would use:
- Circos plot: letters arranged on one arc, referenced books on another, ribbons connecting them
- Color coding: ribbon color = genre of referenced book, or theme, or author
- Contextual analysis: for each reference, what is the narrative context? What themes are active in the letter at that point? Is there a correlation between the referenced book's themes and the letter's narrative themes?

### Type 5: Free-Text Summaries (What Humans Think Is Happening)

**Genomic parallel**: Gene descriptions, functional annotations in natural language, curator notes

**Literary instance**: Swinehart's `capsule` column contains human-written summaries of each section. CPudney's `Synopsis` column contains independent summaries of each scene. These are irreducibly human — no ML system can generate the insight "Hal's image of 'the hero of non-action, the catatonic hero' could describe both himself and Gately."

**Data model**: Free-text notes attached to spans:
- Span reference
- Note text (markdown)
- Note type (summary, interpretation, question, connection, personal response)
- Annotator identity
- Timestamp

**ML augmentation**: LLMs can generate *draft* summaries that human annotators then edit. The key is that the LLM summary is a starting point, not a final product. StoryRibbons (Yeh et al., 2025) validated this workflow: LLM extraction with human correction loops for hallucinated quotes and entity deduplication.

---

## 3. The GFF3 Lesson: How Genomics Represents Multi-Layer Annotations

GFF3 (Generic Feature Format version 3) is the standard for genome annotation interchange. Its design encodes several lessons for text annotation:

### 3.1 The GFF3 Data Model

Each line represents one feature:
```
seqid  source  type  start  end  score  strand  phase  attributes
```

- **seqid**: which sequence (chromosome) — for text: which document
- **source**: which tool/annotator produced this — critical for provenance
- **type**: what kind of feature (gene, mRNA, exon, CDS) — for text: what kind of annotation
- **start/end**: coordinates on the reference — for text: character/word offsets
- **score**: confidence — for text: ML model probability or annotator agreement
- **strand**: +/- orientation — for text: could encode directionality of references
- **phase**: reading frame for CDS — no direct text analogue
- **attributes**: key=value pairs (ID, Name, Parent, etc.) — extensible metadata

### 3.2 Hierarchical Features via Parent-Child Relationships

GFF3 represents hierarchical structure:
```
gene → mRNA → exon, CDS, UTR
```

For text, this maps to:
```
act → chapter → scene → paragraph → sentence
character_arc → arc_phase → key_moment
theme → theme_instance → supporting_passage
```

### 3.3 What GFF3 Gets Right for Text

1. **Source provenance**: every annotation records who/what produced it. This enables filtering by annotator ("show me only human annotations") or by method ("show me only BookNLP NER results").
2. **Score field**: every annotation has a confidence. This enables progressive disclosure — show high-confidence annotations by default, reveal uncertain ones on demand.
3. **Extensible attributes**: the key=value attribute system accommodates per-text custom fields without schema changes.
4. **Parent-child nesting**: hierarchical annotation without arbitrary depth limits.

### 3.4 What GFF3 Gets Wrong for Text

1. **Linear coordinate assumption**: GFF3 assumes features lie on a single linear sequence. Text annotation needs multiple overlapping coordinate systems.
2. **No overlapping features on same type**: GFF3 doesn't handle well the case where two annotations of the same type overlap (e.g., two themes active in the same passage). Text annotation must support arbitrary overlap.
3. **No cross-document references**: GFF3 links features within a single genome. Text annotation needs inter-document links (intertextual references, cross-edition mappings).

### 3.5 A Palimpsest Annotation Format (PAF)

Drawing on GFF3 but addressing its limitations:

```json
{
  "document_id": "the-correspondent-2024",
  "annotations": [
    {
      "id": "ref-042",
      "type": "book_reference",
      "source": "human:reader-1",
      "coordinates": {
        "linear": {"start": 45230, "end": 45267},
        "structural": {"letter": 14, "paragraph": 3, "sentence": 2}
      },
      "confidence": 1.0,
      "attributes": {
        "referenced_work": "Don Quixote",
        "referenced_author": "Cervantes",
        "referenced_genre": "novel",
        "reference_type": "explicit_mention",
        "narrative_context_themes": ["idealism", "delusion", "quest"]
      },
      "parent": null,
      "children": [],
      "cross_references": [
        {"target_doc": "don-quixote", "target_span": null, "relationship": "references"}
      ]
    }
  ]
}
```

---

## 4. Bridging Human and Machine Annotation

### 4.1 The Evidence Hierarchy

Not all annotations are equal. Borrowing from MAKER's evidence integration:

| Evidence level | Source | Confidence | Example |
|---|---|---|---|
| **E1: Explicit text** | The text itself contains the annotation | Highest | A chapter heading, an explicit "she said" attribution, a footnote reference |
| **E2: Human annotator** | A human reader identified this feature | Very high | "This scene is ironic," "This alludes to Hamlet," a scene boundary |
| **E3: Cross-text homology** | The same feature is annotated in a related text | High | A character type annotated in BookNLP training data; a plot structure matching a known archetype |
| **E4: ML prediction** | A trained model detected this feature | Variable | NER output, sentiment score, topic assignment |
| **E5: Ab initio prediction** | A model applied without domain-specific training | Lowest | Zero-shot LLM annotation, generic sentiment lexicon |

### 4.2 The Annotation Workflow

Inspired by MAKER's iterative evidence integration:

**Round 1 — Automated Draft**
Run QuickAnnotate (the Prokka equivalent): fast NER, sentence segmentation, basic sentiment, word frequency statistics. Produces a "draft genome" in seconds.

**Round 2 — Evidence Integration**
Run EvidenceSegmenter (the MAKER equivalent): combine Round 1 results with structural signals (paragraph breaks, dialogue markers, temporal expressions) and any available cross-text annotations (if this is a new edition of an already-annotated work, use AnnotationTransfer/Liftoff). Produce confidence-scored annotations.

**Round 3 — Human Curation**
Present the reader with pre-computed annotations in a CollabReader (the Apollo equivalent). The reader accepts, rejects, or refines ML suggestions, and adds annotations the ML missed entirely. Each human action updates the evidence for future ML predictions (active learning loop).

**Round 4 — Domain-Specific Analysis**
Run specialized detectors: IntertextDetector (for book references), PayoffLinker (for foreshadowing connections), SubtextDetector (for irony/unreliable narration). These are the Infernal/G4Hunter equivalents — highly specific tools that detect features the general pipeline misses.

### 4.3 What ML Can and Cannot Do

| Task | ML capability | Human requirement |
|---|---|---|
| Named entity recognition | Good (F1 ~0.85 on literary text with LitBank-trained models) | Resolve ambiguous cases, add aliases |
| Coreference resolution | Moderate (degrades with long documents, literary language) | Critical for pronoun resolution in complex narratives |
| Scene boundary detection | Good for explicit markers, poor for implicit transitions | Essential for texts without chapter/section markup |
| Sentiment/emotion scoring | Good at passage level, poor at detecting irony | Must flag ironic passages; readers naturally detect these |
| Theme identification | Good via topic modeling (LDA), but topics ≠ themes | Themes are interpretive; topics are distributional |
| Intertextual reference detection | Good for explicit quotations, poor for allusions | The core human contribution — recognizing that a passage echoes another work |
| Plot structure annotation | Poor — current models cannot reliably identify narrative function | Readers intuitively identify climax, turning points, setup/payoff |
| Character relationship inference | Moderate via co-occurrence; poor for implicit relationships | "They're rivals" vs "they appeared in the same scene" |

---

## 5. The Correspondent Use Case: Annotation as Discovery

The user's example — visualizing book references within The Correspondent's letters — illustrates how annotation becomes a discovery tool, not just a labeling exercise.

### 5.1 The Annotation Pipeline

1. **Detect book references**: Scan each letter for mentions of books, authors, literary works. Use a combination of:
   - Named entity recognition tuned for literary work titles
   - A reference database of known books (Open Library, Wikidata)
   - Pattern matching for citation conventions ("have you read...", "reminds me of...", "like [Author]'s...")
   - Human annotation for oblique or partial references

2. **Enrich with metadata**: For each detected book reference, look up:
   - Author, publication date, genre, language
   - Subject headings, themes (from library catalog data or LLM summarization)
   - Canonical importance (citation count, canon membership)

3. **Contextualize within the narrative**: For each reference, compute:
   - What themes are active in the surrounding letter text? (topic model of the local context)
   - Who is the letter writer and recipient? What is their relationship state at this point?
   - Is the reference prescriptive ("you should read"), descriptive ("I just finished"), or allusive ("this situation is very [Author]")?
   - Does the referenced work's theme correlate with or contrast with the local narrative theme?

### 5.2 The Visualization

**Circos view**: Letters arranged chronologically on one arc, referenced books clustered by genre on another arc. Ribbons connect each reference to its source letter. Ribbon width could encode reference depth (passing mention vs extended discussion). Ribbon color encodes:
- By genre: fiction (blue), philosophy (green), poetry (purple), history (gold)
- By theme: love (red), death (black), adventure (orange) — using referenced book's themes
- By author: each distinct author gets a color from a categorical palette

**Interactive features**:
- Hover on a ribbon: show the reference passage in context
- Click a book cluster: filter to show only references to that book/author across all letters
- Toggle color coding between genre/theme/author views
- Time slider: animate which references appear at each point in the correspondence

**Discovery potential**: Does the character who writes about philosophy books have a different narrative arc than the one who references novels? Do references to tragic works cluster before narrative crisis points? Does the density of book references increase or decrease as the correspondence deepens? These are questions that the *annotation* reveals — they're invisible in the raw text.

### 5.3 Generalization: Per-Text Annotation Types

Every text will have annotation types unique to it:
- For The Correspondent: book references within letters
- For Infinite Jest: endnote cross-references, subsidized year translations, character initialism mappings
- For Ulysses: Homeric parallels, Dublin geography, time-of-day tracking
- For a scientific paper collection: citation graphs, method references, dataset mentions
- For a poetry collection: meter/rhyme scheme, allusion to classical sources, phonetic patterns

Palimpsest needs a **custom annotation type builder** — a way for users to define:
1. What the annotation type is called
2. What attributes it carries
3. How to detect it (ML model, regex pattern, manual-only)
4. How to visualize it (color scheme, coordinate mapping, linked views)
5. How to export it (for sharing, for use in other tools)

This is analogous to how genomics labs define custom GFF3 feature types for organism-specific annotations (e.g., operon structures in bacteria, tissue-specific enhancers in mammals).

---

## 6. The CL Annotation Landscape: Standards and Tools

### 6.1 The Standoff Annotation Requirement

The foundational architectural decision is **standoff annotation** — annotations stored separately from the immutable source text, referencing it by offset or identifier. Inline markup (TEI XML, HTML) cannot represent overlapping annotations due to XML's well-formedness constraint. Since a single passage in Palimpsest may simultaneously carry a scene boundary annotation, a thematic tag, a character presence marker, and an intertextual reference from different sources, standoff is architecturally required.

### 6.2 W3C Web Annotation Data Model (Primary Standard)

The W3C Web Annotation Data Model (2017 Recommendation) replaces our ad-hoc PAF format from §3.5. It is JSON-LD serialized, RDF-compatible, and web-native:

```json
{
  "@context": "http://www.w3.org/ns/anno.jsonld",
  "type": "Annotation",
  "body": {
    "type": "TextualBody",
    "value": "Allusion to Middlemarch Chapter 3",
    "purpose": "commenting"
  },
  "target": {
    "source": "https://palimpsest.app/text/the-correspondent/letter-12",
    "selector": {
      "type": "TextQuoteSelector",
      "exact": "she had read too many novels about impossible expectations",
      "prefix": "After some reflection ",
      "suffix": " to be taken in"
    }
  }
}
```

Key advantages over a custom format:
- **Multiple selectors**: `TextQuoteSelector` (by surrounding context — robust to minor edits), `TextPositionSelector` (by character offset — fast), `XPathSelector`, `FragmentSelector`. Combinable via `RefinedBy`.
- **Multiple bodies**: a single annotation can carry a comment, a tag, and a link to an external resource simultaneously.
- **Motivation taxonomy**: `commenting`, `tagging`, `classifying`, `bookmarking`, `linking`, `identifying`, `describing` — matches our annotation use cases.
- **User-defined types**: extend the body vocabulary with custom properties (`charactersPresentIds`, `plotPhase`, `intertextualSource`).
- **Real implementations**: Hypothes.is, INCEpTION, Annotation Studio all speak this format.

### 6.3 Recommended Technology Stack

| Layer | Tool | Role |
|---|---|---|
| **Data model** | W3C Web Annotation (JSON-LD) | Primary annotation interchange format |
| **Automated extraction** | BookNLP | Character NER, coreference, quote attribution (~85% F1 on literary text) |
| **Discourse analysis** | RST parsers (RSTFinder) | Passage-level rhetorical function (elaboration, contrast, attribution) |
| **Intertextual detection** | Tesserae-style TF-IDF + dense embedding retrieval | Detect quotations, allusions, and references to other texts |
| **Human annotation UI** | INCEpTION | Active learning, knowledge base integration, multi-annotator curation |
| **Reader-facing annotation** | Hypothes.is (self-hosted) | Collaborative reading with social annotation features |
| **ML-assisted labeling** | Prodigy | High-throughput annotation sprints (300-400 examples/hour) |
| **Source text encoding** | TEI XML + TEI Standoff | Archival encoding with scholarly provenance |

### 6.4 The Intertextual Reference Detection Pipeline

No existing end-to-end system handles "book references embedded within a novel's dialogue" — this is a genuinely novel problem. Recommended four-stage pipeline:

**Stage 1 — Explicit Detection (High Precision)**
- Regex + rule-based matching for book titles, author mentions, attribution phrases ("have you read...", "reminds me of...")
- Cross-reference against literary title database (Wikidata Q47461344 = literary work, OpenLibrary)
- Expected precision: ~95%; expected recall: ~40% (misses oblique references)

**Stage 2 — Passage-Level Retrieval (Moderate Precision)**
- Embed letter segments with dense encoder (e.g., `text-embedding-3-large`)
- Embed passages from candidate source texts
- Retrieve top-k candidates by cosine similarity
- Threshold-filtered results feed into Stage 3

**Stage 3 — LLM Verification (High Recall, Human-in-the-Loop)**
- For each candidate pair, prompt LLM: "Does this passage allude to or reference [book title]? What is the nature of the reference?"
- LLM provides structured output: reference type (explicit quotation, paraphrase, thematic echo, structural parallel), confidence, relevant excerpt
- Human annotators confirm/reject in Prodigy or INCEpTION

**Stage 4 — Metadata Enrichment**
- Query bibliographic APIs (OpenLibrary, Wikidata) for author, genre, publication year, themes
- Store as W3C Web Annotation with custom `IntertextualReference` body type

### 6.5 Key Tools from Computational Linguistics

**Tesserae** (University of Buffalo): the foundational tool for computational intertextuality, built for classical Latin/Greek poetry. Algorithm: lemmatize both texts, find all shared n-gram pairs, score by word frequency (rarer = higher) and proximity (closer = higher). TF-IDF-modified scoring shown to work on English prose. Open source at tesserae.caset.buffalo.edu.

**CLÉA** (McGill): Collaborative Literature Exploration and Annotation Environment, designed explicitly for *interpretive plurality* — multiple contradictory readings can coexist in markup. Uses TEI-compliant non-deterministic standoff. The most philosophically aligned tool to Palimpsest's vision.

**INCEpTION** (TU Darmstadt): successor to WebAnno. Active learning retrains from human corrections automatically. Knowledge base integration (Wikidata, custom KB) for entity linking. Custom annotation layers definable per project. UIMA CAS XMI export for downstream NLP pipelines. EMNLP 2024 demo showed REST API integration for external ML pre-annotators.

**Prodigy** (Explosion AI): ML-assisted annotation achieving 3-4x throughput over blank-slate annotation. Binary mode ("is this a reference? yes/no") is ideal for confirming pipeline output. Commercial license (~$490/seat academic).

### 6.6 What BookNLP Covers vs. What Humans Must Provide

| Task | BookNLP capability | Human requirement |
|---|---|---|
| Named entity recognition | Good (F1 ~0.85 on LitBank-trained models) | Resolve ambiguous cases, add aliases |
| Coreference resolution | Moderate (degrades on long docs, literary language) | Critical for pronoun resolution in complex narratives |
| Quotation attribution | Good for explicit quotes; ~63% on implicit | Correct mis-attributions |
| Scene boundary detection | Not supported | Essential — no reliable automated model exists |
| Theme identification | Not supported | Themes are interpretive, not distributional |
| Intertextual reference detection | Not supported | Core human contribution |
| Plot structure annotation | Not supported | Readers intuitively identify climax, turning points |
| Character relationship types | Co-occurrence only | "Rivals" vs "appeared in same scene" |

BookNLP covers ~40% of "reader's guide" annotation types. The remaining 60% requires human input augmented by LLM suggestions.

---

## 7. Architectural Implications

### 7.1 The Annotation Store

All annotations stored as W3C Web Annotations (JSON-LD) with Palimpsest-specific body extensions:

| Body type | Attributes | Source |
|---|---|---|
| `CharacterPresence` | `characterId`, `mentionType` (name/pronoun/description), `confidence` | BookNLP + human |
| `SceneBoundary` | `boundaryType` (chapter/scene/transition), `transitionSignal` | Human + AutoSegmenter |
| `ThematicTag` | `tagSetId`, `tagValue`, `tagHierarchy` | Human + LDA |
| `PlotPoint` | `plotFunction` (inciting/rising/climax/resolution), `significance` | Human |
| `IntertextualReference` | `sourceWork`, `sourceAuthor`, `referenceType`, `genre`, `themes[]` | Pipeline + human |
| `ReaderNote` | `noteType` (summary/interpretation/question/connection), `markdown` | Human |
| `PassageState` | `stateLabel`, `featureVector`, `confidence` | PassageStateHMM |

### 7.2 The Annotation API

Built on the W3C Annotation Protocol (LDP-based):

```
POST /annotations/                    — create annotation (W3C JSON-LD body)
GET  /annotations/?target={doc_id}    — query by target document
GET  /annotations/?body.type={type}   — query by annotation type
GET  /annotations/?creator={user_id}  — query by annotator
PUT  /annotations/{anno_id}           — update
DELETE /annotations/{anno_id}         — soft-delete (audit trail preserved)
POST /annotations/batch/run           — execute automated pipeline on document
```

### 7.3 The Track Model

Borrowing from genome browsers: each annotation type is a "track" that can be independently:
- Shown or hidden
- Colored by any attribute
- Filtered by confidence threshold or source provenance
- Grouped with related tracks
- Exported independently

Default tracks for any text:
1. **Entities** (BookNLP: characters, places, organizations)
2. **Quotations** (BookNLP: attributed speech)
3. **Sentiment** (passage-level emotional valence)
4. **Structure** (scene boundaries, transitions)
5. **Discourse** (RST rhetorical relations — elaboration, contrast, etc.)
6. **Topics** (LDA or embedding-based topic assignments)
7. **Custom** (user-defined per-text annotation types)

### 7.4 The Annotation Workflow (MAKER-Inspired)

```
Round 1: QuickAnnotate (Prokka-equivalent)
  └─ BookNLP + sentiment + word frequency → draft annotations in seconds

Round 2: EvidenceIntegrate (MAKER-equivalent)
  └─ Combine Round 1 + structural signals + cross-text annotations
  └─ Assign confidence scores per annotation

Round 3: HumanCurate (Apollo-equivalent)
  └─ INCEpTION or custom CollabReader UI
  └─ Accept/reject/refine ML suggestions + add what ML missed
  └─ Active learning loop updates models from corrections

Round 4: SpecializedDetect (Infernal/G4Hunter-equivalent)
  └─ IntertextDetector, PayoffLinker, SubtextDetector
  └─ Domain-specific tools that detect what general pipeline misses
```

---

*This document integrates findings from deep-read reports (03-06), CL annotation frameworks research (08), and is pending integration of genome annotation methodology (09) and annotation visualization patterns (10).*

# Research Report: Computational Linguistics and NLP Annotation Frameworks for Literary Text — Palimpsest Platform

**Generated**: 2026-06-06
**Date**: 2026-06-06
**Scope**: Annotation standards, NLP pipelines, discourse analysis, literary NER, intertextual reference detection, human-in-the-loop annotation, and collaborative close reading — all evaluated for applicability to a multi-layer literary annotation platform.

---

## Executive Summary

Building a literary annotation platform at the "reader's guide" level of granularity is technically achievable using existing tools, but requires careful layering of three distinct capability classes: (1) structural annotation frameworks that define how annotations are stored and composed, (2) NLP pipelines specialized for long-form literary text, and (3) human-in-the-loop tooling that bridges automatic extraction with expert correction.

No single framework handles all the requirements. The dominant pattern in the field is to adopt a standoff annotation model — where annotations are stored separately from the immutable source text — because it is the only model that naturally handles overlapping markup (a critical requirement when a single passage is simultaneously a scene boundary, a thematic statement, and an intertextual allusion). The W3C Web Annotation Data Model is the most interoperable modern standard for this, and INCEpTION is the most capable open-source tool implementing it.

For automated extraction, BookNLP (character clustering, coreference, quote attribution) and LitBank (training corpus for literary NER) are the primary domain-specific tools. Intertextual reference detection — the hardest task, and central to "The Correspondent" use case — currently requires a hybrid approach: dense embedding retrieval to find candidate passages, followed by human confirmation, with no existing end-to-end solution for detecting book references embedded within a novel's dialogue.

---

## Key Findings

### 1. Annotation Standards and Formats

#### Standoff vs. Inline Markup

The foundational architectural decision for any literary annotation system is the choice between inline markup (annotations embedded in the text, as in standard XML/HTML) and standoff annotation (annotations stored in a separate layer, referencing the source by offset or identifier).

Inline XML, including TEI XML, cannot natively represent overlapping annotations. In a poem, for example, a quotation that crosses a line break cannot be expressed as a `<q>` element because it would violate XML's well-formedness constraint requiring elements to nest properly. The TEI community has debated this for over a decade; milestone tags are a workaround but require custom tooling to interpret. As of 2020, an active effort within TEI is developing a formal `<standoff>` container for annotations. The consensus view: "the current state of the art to represent linguistically annotated data is to use a graph-based representation serialized as standoff XML as a pivot format."

For a platform where a single passage may simultaneously carry a chapter-break annotation, a thematic tag, a character-presence tag, and an intertextual reference tag applied by different users or processes, **standoff annotation is architecturally required**.

#### UIMA CAS (Common Analysis Structure)

UIMA is Apache's framework for NLP pipelines and annotation management. Its data model is specifically designed for overlapping, nested, multi-layer annotations via a standoff architecture.

Core concepts:
- **Sofa (Subject of Analysis)**: the immutable source artifact (the text). A single CAS can have multiple Sofas (e.g., one for raw text, one for a clean plaintext version).
- **Feature Structure**: the fundamental annotation unit. Has a type and a set of attribute-value pairs. Types are organized in a single-inheritance hierarchy.
- **Annotation**: a Feature Structure that references a span (character offset pair) within a Sofa.
- **Type System**: user-defined. You declare annotation types (e.g., `CharacterMention`, `PlotPoint`, `IntertextualReference`) in an XML descriptor. Each type can have arbitrary typed attributes.
- **CAS Views**: multiple views over the same document allow different annotation layers to coexist without conflict.

For overlapping annotations, UIMA uses the MAX strategy by default in inter-annotator agreement modules: treat all annotations for each annotator as a set, compute the cartesian product, and choose the n-tuple with highest agreement.

UIMA's serialization format is **UIMA CAS XMI** (XML Metadata Interchange), the de facto interchange format for NLP pipelines. INCEpTION, DKPro, and many academic NLP tools speak this format natively.

**Verdict for Palimpsest**: UIMA CAS XMI is the right backend data format if you need to interface with academic NLP pipelines. The type system is powerful but requires Java tooling. Consider it for the pipeline layer, not the user-facing API.

#### GATE (General Architecture for Text Engineering)

GATE is the Sheffield-originated open source framework for NLP. It uses an annotation model based on the TIPSTER format: annotations associate document spans (byte offset pairs) with attribute-value typed metadata, stored separately from the source text.

Key characteristics:
- Annotations are stored in **Annotation Sets** — named collections within a document. You can have as many named annotation sets as you like (e.g., "BookNLP", "ManualLiterary", "IntertextualRefs").
- Annotation types are defined in XML descriptors but are practically ad hoc — you create whatever types you need.
- The **CREOLE** plugin system allows user-defined processing resources. You can add a custom annotator component that produces any annotation type.
- GATE Embedded (the API) and GATE Developer (the GUI) are both actively maintained.
- The annotation model handles overlapping annotations naturally since annotations are objects pointing into text, not embedded tags.

GATE's practical advantage is its mature GUI (GATE Developer) for visualizing and editing multi-layer annotations, and its tight integration with rule-based annotation via **JAPE** (Java Annotation Patterns Engine), which lets you write Perl-style regex patterns over annotation graphs.

**Verdict for Palimpsest**: GATE is excellent for building annotation pipelines with mixed rule-based and ML components. Less suited as the primary data model for a web application.

#### LAF/GrAF (Linguistic Annotation Framework / Graph Annotation Format)

LAF is ISO standard 24612:2012. Its XML serialization, GrAF, represents annotations as a directed graph: annotation nodes point into the primary data (the text), and edges between annotation nodes represent structural or semantic relationships.

GrAF's key properties:
- Any annotation type can be represented as nodes and edges in the graph.
- Multiple annotation layers can be merged because they all live in the same graph space.
- Graph traversal algorithms from graph theory apply directly — you can query for all annotations that overlap, or find the shortest annotation path between two nodes.
- It was used as the exchange format for MASC (Manually Annotated Sub-Corpus of ANC) and OANC.

The weakness: GrAF is an academic standard with limited active tooling. It is more of an exchange format than a platform.

#### TEI XML

TEI (Text Encoding Initiative) is the dominant standard in digital humanities for encoding literary texts. TEI XML is inline XML with a rich tagset covering structural features (chapters, paragraphs, lines, stanzas), character names (`<persName>`), places (`<placeName>`), direct speech (`<said>`), dates, and editorial annotations.

TEI's strengths for Palimpsest:
- The scholarly community universally understands it.
- Rich semantic tag vocabulary for literary features.
- Long-term archival format.
- Extensive tooling (Oxygen XML Editor, TEIPublisher, XSLT transforms).

TEI's weakness is the overlapping markup problem. The emerging solution is **TEI Standoff** with a `<standoff>` container: annotations live outside the body text as elements with `@corresp` or `@target` pointers to `@xml:id` anchors in the text. A TEI/RDF hybrid approach links RDF triples to TEI anchors, allowing a knowledge graph of annotations to coexist with the linearly encoded text.

**Verdict for Palimpsest**: TEI is the right archival format for the source text encoding. Use TEI Standoff or TEI/RDF for annotation layers that would otherwise conflict.

#### W3C Web Annotation Data Model

The W3C Web Annotation Data Model (published as a Recommendation in 2017) is the most practically important modern standard for building annotation applications. It is JSON-LD serialized, RDF-compatible, and designed for web-native use.

The data model has three core entities:
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
    "source": "https://palimpsest.app/text/the-correspondent/chapter-12",
    "selector": {
      "type": "TextQuoteSelector",
      "exact": "she had read too many novels about impossible expectations",
      "prefix": "After some reflection ",
      "suffix": " to be taken in"
    }
  }
}
```

Key features:
- **Body**: what the annotation says (text, an RDF resource, a tag from a controlled vocabulary, a rich JSON object).
- **Target**: what the annotation is about (a document, a text fragment via selector, a time range in video, etc.).
- **Selectors**: `TextQuoteSelector` (by surrounding context), `TextPositionSelector` (by character offset), `XPathSelector`, `CssSelector`, `FragmentSelector`. Multiple selectors can be combined via `RefinedBy` for precision.
- **Multiple bodies**: a single annotation can have multiple body resources (e.g., a comment, a tag, and a link to an external resource, all attached to the same target span).
- **Motivation**: the purpose of the annotation (commenting, tagging, classifying, bookmarking, linking, identifying, describing, etc.).

Overlapping annotations are handled trivially: each annotation is an independent JSON object. There is no XML tree constraint. Multiple annotations can target the same or overlapping spans without conflict.

**User-defined annotation types** are implemented by extending the body vocabulary. You can define a `PalimpsestAnnotation` type with custom properties (e.g., `charactersPresentIds`, `plotPhase`, `intertextualSource`) and include it as the body of a W3C annotation.

**Hypothes.is** is the most widely deployed open-source implementation of the W3C Web Annotation protocol. It provides a REST API at `hypothes.is/api/`, stores annotations as JSON-LD conforming to the data model, and supports groups, tags, and public/private visibility. The Frankenstein Variorum project converted Hypothes.is annotations to full W3C JSON-LD, confirming the compatibility.

**Verdict for Palimpsest**: The W3C Web Annotation Data Model should be the primary data model for Palimpsest. It is web-native, JSON-LD serialized, interoperable with Hypothes.is and other tools, and handles overlapping annotations naturally. Build the API around this model with custom body types.

---

### 2. NLP Annotation Pipelines for Literary Text

#### BookNLP

BookNLP is the primary purpose-built NLP pipeline for English literary texts. It is available as a Python package (`pip install booknlp`). It addresses the two key problems with applying general NLP tools to novels: (1) models trained on news degrade badly on literary language, and (2) quadratic-complexity coreference resolution fails on novel-length documents.

What BookNLP annotates automatically:
- **Part-of-speech tagging** and **dependency parsing** (sentence-level)
- **Named Entity Recognition**: PER, LOC, FAC, GPE, ORG, VEH — trained on 968K tokens including LitBank and ~500 contemporary books
- **Character name clustering**: resolves aliases (Tom / Tom Sawyer / Mr. Sawyer → TOM_SAWYER) using a BERT-based character name clustering model
- **Pronominal coreference resolution**: links pronouns to named character clusters at book-length scale
- **Quotation attribution**: identifies quoted speech and links it to the speaking character, using a BERT model fine-tuned on LitBank speaker annotations. Accuracy approaches perfect for explicit quotes; ~63% on the PDNC corpus overall
- **Supersense tagging**: coarse semantic categories for nouns and verbs (e.g., `noun.person`, `verb.communication`)
- **Referential gender inference**: infers character gender from pronoun usage

What requires human input:
- Thematic annotation
- Plot structure and scene boundaries
- Intertextual references
- Reader-level interpretation and significance judgments
- Relationship types between characters (knows / antagonist / family / romantic)

BookNLP outputs structured data: a `{book_id}.book` file containing character lists with their mention spans, a `{book_id}.tokens` file with token-level annotations, a `{book_id}.quotes` file with attributed quotations, and a `{book_id}.entities` file.

**Key limitation for Palimpsest**: BookNLP handles character-level tasks well but has no plot or theme extraction capability. Its character co-occurrence data can feed a scene-sharing graph, but scene segmentation itself requires either manual annotation or a separate model.

#### LitBank

LitBank is the annotated training corpus underlying BookNLP's literary models. 100 works of fiction from Project Gutenberg, each with ~2,000 annotated tokens.

Annotation layers in LitBank:
- **Entity annotation**: ACE-style types (PER, ORG, FAC, LOC, GPE, VEH) with nested entities
- **Coreference**: 29,103 mentions resolved to 7,235 unique entities; covers identity coreference, copula, and apposition
- **Event annotation**: events with asserted realis (actually occurring, with specific participants at a specific time)
- **Quotation attribution**: speaker and addressee for quoted speech

LitBank's coreference models achieve 79.3 F1 on literary text vs. 72.9 F1 for models trained on OntoNotes (news). This difference is significant and establishes that domain-specific training data is essential for literary annotation quality.

LitBank is Creative Commons ShareAlike licensed and available at github.com/dbamman/litbank.

#### spaCy

spaCy is the most practical general-purpose NLP library for building custom literary annotation pipelines.

Relevant architecture for Palimpsest:
- **Custom pipeline components**: `@Language.component` decorator registers a function that takes a `Doc` and returns a modified `Doc`. Add components for scene boundary detection, theme classification, or intertextual flagging.
- **Custom extensions**: `Doc.set_extension`, `Token.set_extension`, `Span.set_extension` add arbitrary attributes to spaCy's core objects. A `span._.intertextual_refs` list extension could hold detected references for each text span.
- **Transformer integration**: `spacy-transformers` gives access to BERT/RoBERTa embeddings via `doc._.trf_data`.
- **Project templates**: `spacy project` provides CLI-driven reproducible training workflows.

For literary domains, spaCy's pretrained models (trained on web/news text) produce degraded NER on fictional names and places. Fine-tuning on LitBank or a custom literary corpus is needed.

**LatinCy** demonstrates domain adaptation: a full Latin-language spaCy pipeline for classical literary texts, providing tokenization, lemmatization, POS tagging, dependency parsing, and NER trained on Latin treebanks.

#### Stanza

Stanford's Stanza (formerly StanfordNLP) is a fully neural pipeline supporting 60+ languages. Its dependency parser (Bi-LSTM deep biaffine) and NER are high-quality but trained on standard news/web corpora. It is more appropriate than spaCy for multilingual scenarios or when you need high-accuracy dependency parses.

For literary annotation, Stanza is best used for the low-level linguistic features (sentence segmentation, dependency parsing, lemmatization) that feed into higher-level literary-specific models. It does not have literary-domain models.

---

### 3. Discourse and Rhetorical Annotation

#### RST (Rhetorical Structure Theory)

RST decomposes a text into a hierarchical tree of **Elementary Discourse Units (EDUs)** — clause-like segments, each expressing a single proposition — connected by labeled rhetorical relations (Elaboration, Contrast, Attribution, Cause, Purpose, Antithesis, etc.).

The tree has two types of nodes:
- **Nucleus**: the central or most essential span
- **Satellite**: a supporting span that elaborates, constrains, or provides context for the nucleus
- **Multinuclear relations** (e.g., Joint, Contrast, List): all children are equally central

RST analysis provides a functional decomposition of text that is highly relevant for literary analysis: it identifies what each passage is doing rhetorically — providing background, elaborating a theme, contrasting with a prior statement, attributing a claim to a character.

Available RST tools:
- **RSTFinder** (Educational Testing Service, Python 3.7–3.10): a discourse segmenter + shift-reduce parser. Conda install only, Linux only.
- **Fast RST Discourse Parser** (Heilman et al.): shift-reduce parser with near-state-of-the-art accuracy on short documents. Processes a news article in under one second.
- **RST Parsing from Scratch** (arXiv 2105.10861): top-down seq2seq formulation that yields segmentation as part of the parsing process — no separate segmentation step needed.

RST parsers are typically trained on the RST-DT (RST Discourse Treebank, newswire text) or the GUM corpus (multiple genres). Neither is literary fiction. Transfer performance on novels will be limited; expect EDU segmentation to work reasonably well but relation labeling to be noisy.

**For Palimpsest**: RST is most useful as an analytical lens for understanding passage function, not as an automated annotation layer. Semi-automatic RST annotation with human correction is the practical approach. The RST tree structure could also serve as the backbone for a passage-level navigation UI (browse text by rhetorical function).

#### PDTB (Penn Discourse Treebank)

PDTB takes a flatter, lexically grounded approach to discourse structure. Rather than building a full tree, PDTB annotates discourse relations locally: wherever a **discourse connective** (because, however, although, as a result) or implicit relation is detected, PDTB labels the relation type and its two arguments (Arg1 and Arg2).

PDTB 3.0 (Webber et al., 2019) contains 40,600+ annotated relation tokens. The sense hierarchy has three levels: class (Temporal, Contingency, Comparison, Expansion), type (e.g., Cause, Condition), and subtype.

PDTB-style annotation is shallower than RST but more reliable to automate. End-to-end shallow discourse parsers achieve reasonable performance on explicit connectives; implicit relations remain harder.

**For Palimpsest**: PDTB-style discourse relation annotation at the paragraph level could support theme tracking (noting when a passage elaborates vs. contrasts with a prior theme statement) and cause/effect chain construction for plot analysis.

---

### 4. Named Entity and Relation Extraction for Literary Domains

#### Literary NER Challenges

Standard NER models (CoNLL-2003, OntoNotes) fail significantly on literary text for multiple reasons:
- **Fictional proper nouns**: "Frodo," "Winterfell," "Arrakis" are not in any pretraining distribution.
- **Naming variation**: characters are referred to by first name, surname, title, nickname, and pronoun. "Elizabeth," "Miss Bennet," "Lizzy," and "she" all refer to the same entity.
- **Entity overlap**: "the young knight" is both a common noun phrase and a character reference.
- **Metonymy and allegory**: abstract entities take on character-like properties.
- **Historical/archaic language**: Victorian fiction uses syntax patterns rare in modern web text.

Flair, Trankit, and spaCy NER outperform other general models on fantasy domain texts (D&D adventure books) without fine-tuning. With fine-tuning on LitBank, models improve substantially: LitBank-trained coreference resolvers achieve 79.3 F1 vs. 72.9 F1 for OntoNotes-trained models.

#### Character Co-occurrence and Social Network Extraction

The standard pipeline for extracting "characters sharing scenes":
1. Run BookNLP to get character clusters and their mention spans.
2. Segment the text into scenes (manually, or via a scene-boundary detector).
3. For each scene segment, collect the set of character clusters whose mentions fall within that segment.
4. Build a co-occurrence graph: characters are nodes, scenes are hyperedges, edge weight = number of shared scenes.

"A City of Millions: Mapping Literary Social Networks At Scale" (arXiv 2502.19590, Feb 2025) applied Gemini 1.5 Flash (1M token context window) to extract character relationship types from fiction, using a structured JSON schema output. This is the current state-of-the-art for automated relation extraction in literary texts.

#### Relation Extraction

LLM-based approaches significantly outperform traditional supervised models for literary relation extraction because they can reason over long-range context. GPT-4 performs best extracting relationships from a single character's perspective but degrades when asked to extract all relationships simultaneously (the "complex relationships in detective narratives" paper). This suggests a decomposed prompt strategy: run one extraction pass per major character.

For a Palimpsest use case, the recommended pipeline for character relations:
1. BookNLP for character identification and coreference.
2. GPT-4/Claude with structured output (JSON schema) for relation type extraction.
3. Human review via INCEpTION or Prodigy.

#### Grounding Characters and Places

The paper "Grounding Characters and Places in Narrative Texts" (arXiv 2305.17561) addresses entity disambiguation in fiction — linking extracted character mentions to a knowledge base (e.g., a Palimpsest-specific character registry). This is the digital equivalent of the reader's guide problem: "Colonel Brandon" must be recognized as the same entity across 300 pages, not just as a recurring string.

---

### 5. Intertextual Reference Detection

This is the hardest and most novel task for Palimpsest. No existing end-to-end system detects "book references embedded within a novel's dialogue or narration" — the specific need for "The Correspondent."

#### Taxonomy of Intertextual Relations

The literature distinguishes:
- **Explicit quotation**: verbatim text from another work, typically with attribution ("As Middlemarch says...")
- **Paraphrase**: meaning-preserving restatement without attribution
- **Allusion**: a reference that relies on reader recognition without stating it explicitly
- **Structural parallel**: similar plot/character structure without textual similarity
- **Thematic echo**: shared themes without shared language

Computational methods exist for the first three; the last two require human expert annotation.

#### The Tesserae Project

Tesserae (Coffee et al., 2012) is the foundational computational tool for intertextuality, built for classical Latin and Greek poetry. Its algorithm:
1. Lemmatize both source and target texts.
2. Find all pairs of phrases (2-lemma n-grams) that appear in both texts.
3. Score matches by: word frequency (rarer shared words score higher) and word proximity (words closer together in both texts score higher).
4. Output is a ranked list of parallel phrases with 1–10 scores.

Tesserae also supports semantic search (word2vec similarity) and phonetic search (sound similarity for Latin alliteration patterns).

Tesserae is available as an open-source web tool at tesserae.caset.buffalo.edu. The codebase is Python/Perl.

For English prose intertextuality (the Palimpsest use case), a TF-IDF modified version of the Tesserae scoring function has been shown to outperform the original on English poetry, and by extension English prose.

#### Embedding-Based Approaches

For detecting allusions and paraphrases at semantic level (not just lexical overlap):
- Barbu and Trausan-Matu (2017): pairwise Word2Vec comparisons of all words between two documents.
- Liebl and Burghardt (2020): aligned text sequences with FastText and wnet2vec embeddings to detect Shakespearean quotations in later texts.
- Recent work (arXiv 2501.10731, 2025): multilingual embedding spaces for cross-lingual intertextuality detection.

The "Latent Structures of Intertextuality in French Fiction" paper (arXiv 2410.17759) applied dense retrieval over large corpora to find intertextual connections, representing the current state-of-the-art for prose fiction.

#### Practical Pipeline for "The Correspondent" Use Case

The user wants to find all book references within letters in a novel and visualize them by location, genre, theme, and author. Here is the recommended multi-stage pipeline:

**Stage 1 — Explicit detection (high precision)**
- Extract letter segments from the novel (scene segmentation + document-type classification).
- Run regex and rule-based matching for explicit book/author mentions (`<title>` patterns, quotation marks + attribution phrases).
- Cross-reference against a curated literary reference database (e.g., Wikidata entities for book titles, author names).

**Stage 2 — Passage-level retrieval (moderate precision)**
- Embed all letter segments with a dense encoder (e.g., `text-embedding-3-large` or a literary-domain fine-tuned encoder).
- Embed passages from candidate source texts.
- Retrieve top-k candidates by cosine similarity for each letter segment.
- Threshold-filtered results feed into Stage 3.

**Stage 3 — LLM verification (high recall, human-in-the-loop)**
- For each candidate pair (letter segment, candidate source passage), prompt an LLM: "Does this passage from [novel] allude to or reference [book title]? What is the nature of the reference (explicit quotation, paraphrase, thematic echo, structural parallel)? Quote the relevant excerpt."
- Human annotators confirm or reject LLM-suggested references in a tool like Prodigy.

**Stage 4 — Metadata enrichment**
- For each confirmed reference, query a bibliographic API (OpenLibrary, Google Books API, Wikidata) for author nationality, publication date, genre, and subject tags.
- Store as W3C Web Annotation with a custom `IntertextualReference` body type containing `sourceBook`, `sourceAuthor`, `referenceType`, `genre`, `themes[]`, `geoContext`.

**Visualization layer**: a timeline of the novel's location (x-axis = page/chapter) vs. density of intertextual references, facetable by genre, theme, author nationality, and reference type. This is achievable with standard dataviz libraries once the annotation layer is populated.

---

### 6. Human-in-the-Loop Annotation

#### INCEpTION (recommended primary tool)

INCEpTION is the successor to WebAnno, developed at TU Darmstadt. It is the most capable open-source annotation platform as of 2024–2026.

Key features:
- **Active learning**: automatically retrains models from human corrections and surfaces the most uncertain examples for annotation — no manual trigger needed (unlike WebAnno).
- **Knowledge base integration**: connect an external knowledge base (Wikidata, custom KB) for entity linking directly in the annotation UI.
- **Custom annotation layers**: define arbitrary annotation types with arbitrary features in the project settings. For Palimpsest, you could define a `IntertextualReference` layer with fields `sourceTitle`, `referenceType`, `confidence`.
- **UIMA CAS XMI export**: standard format compatible with downstream NLP pipelines.
- **Multi-user**: annotators work on separate copies, then curation reconciles disagreements.
- **INCEpTION 2024 paper** (EMNLP 2024 Demo): demonstrated integration with external automation services — you can POST a document to a REST endpoint, receive pre-annotations, and display them for human correction. This is the hook for integrating BookNLP, LLM-based annotators, etc.

INCEpTION is the right tool for the scholarly annotation workflow: export texts → auto-annotate with BookNLP/LLM → load into INCEpTION → human experts correct and enrich.

#### Prodigy

Prodigy (Explosion AI, makers of spaCy) is a paid annotation tool optimized for ML-assisted human annotation.

Key features:
- **ner.correct recipe**: model pre-annotates, human accepts/rejects/corrects spans. 300–400 examples/hour vs. 80–120/hour for blank-slate annotation.
- **Active learning loop**: the model is retrained on each batch of corrections and immediately improves its suggestions.
- **Custom annotation interfaces**: define arbitrary JSON schemas for annotation tasks, rendered in a React-based UI.
- **Python-first API**: scriptable for automation; tight integration with spaCy training.
- **Binary annotation mode**: efficient for binary classification tasks (is this an intertextual reference? yes/no).

For Palimpsest, Prodigy is the right tool for high-throughput annotation sprints where a bootstrapping model is available (e.g., after Stage 1-2 of the intertextuality pipeline).

Cost: commercial license, ~$490/seat for academic use.

#### Label Studio

Label Studio (HumanSignal) is the most-deployed open-source annotation platform in 2026. Free tier available; enterprise tier adds ML backends and SSO.

Key features:
- **Visual annotation templates**: NER, relation extraction, classification, image labeling — all configurable via XML templates.
- **ML backend**: connect a prediction API; Label Studio calls it pre-annotation and displays predictions.
- **Custom interfaces**: arbitrary HTML/CSS/JS in annotation templates.
- **Multi-modal**: text, images, audio, video in one platform — relevant if Palimpsest eventually annotates illustrations or audiobooks.

Label Studio is slower per-annotation-hour than Prodigy (no active learning tightness) but more flexible and free.

#### Doccano

Doccano is a lightweight open-source annotation tool. Good starting point for text-only projects with simple label sets, but lacks active learning and becomes a liability for complex multi-layer annotation.

#### Active Learning Frameworks

For building custom active learning loops:
- **modAL**: a Python library integrating with scikit-learn/PyTorch for query strategy selection (uncertainty sampling, query-by-committee, expected model change). Used to select the most informative examples to annotate next.
- **Small-text**: active learning library for NLP fine-tuning, specifically supports transformer models (HuggingFace).

The practical active learning workflow for Palimpsest:
1. Annotate 100–200 examples manually (seed set).
2. Train a lightweight classifier on the seed set.
3. Run inference on unannotated examples.
4. Surface the 20–30 examples with highest uncertainty (entropy or margin sampling) for human annotation.
5. Retrain. Repeat.
6. LLM annotations (GPT-4/Claude) as a "silver standard" to bootstrap before any human labels exist.

---

### 7. Crowdsourced and Collaborative Annotation

#### Multi-Annotator Models

The dominant model in computational linguistics for multi-annotator corpora:
- Each annotator works on their own copy (the "separation" model).
- A **curation** or adjudication step reconciles disagreements: typically a senior annotator acts as "gold curator" who sees all annotators' outputs and makes final decisions.
- **Inter-annotator agreement (IAA)** is measured with Cohen's Kappa (two annotators), Fleiss' Kappa (multiple annotators), or Krippendorff's Alpha (handles ordinal and continuous scales).

INCEpTION natively supports this workflow: projects have per-annotator "annotation documents" and a separate "curation document."

#### Literary-Specific Collaborative Tools

**Annotation Studio (MIT HyperStudio)**: a collaborative annotation space designed specifically for close reading in educational settings. Students annotate the same text simultaneously, see each other's highlights, and reply to each other's comments. Built on the Annotator.js project (precursor to Hypothes.is).

**CLÉA (Collaborative Literature Éxploration and Annotation Environment)**: developed at McGill to support non-hierarchical, discontinuous literary reading. Uses TEI-compliant non-deterministic standoff markup, allowing users to express multiple contradictory readings in markup. This is the most philosophically aligned tool to the Palimpsest vision — it was explicitly designed to capture the interpretive plurality of literary annotation rather than converging on a single "correct" annotation.

**Hypothes.is groups**: Hypothes.is supports annotation groups (private or public). Multiple readers can annotate the same web-served text, with annotations visible to group members. This is the lowest-friction entry point for collaborative literary annotation — but lacks structured data models for machine-readable literary annotations.

#### The Apollo Analogy

The user mentioned Apollo in genomics as a model for collaborative annotation. Apollo (web-based genome annotation editor) is relevant because it uses an "evidence layer + curation layer" model: automated gene predictions from multiple sources are displayed as evidence, and curators annotate the canonical gene model by reviewing and adjudicating the evidence. This translates directly to Palimpsest:

- **Evidence layer**: BookNLP character detections, LLM intertextual suggestions, RST-parsed discourse units.
- **Curation layer**: human experts confirm, modify, and extend the evidence-layer annotations.
- **Provenance tracking**: each annotation records its source (automated model, human expert, crowdsourced reader) and confidence.

The key technical feature enabling this in Apollo is its **real-time WebSocket collaboration** (multiple curators see each other's cursors and edits). For Palimpsest, this corresponds to a real-time annotation server with WebSocket support — achievable with the Hypothes.is `h` server or a custom W3C Annotation Protocol server.

---

## Comparison: Annotation Tool/Format Selection

| Dimension | UIMA CAS | GATE | W3C WebAnno | TEI Standoff | INCEpTION | Hypothes.is |
|---|---|---|---|---|---|---|
| Primary use case | NLP pipeline data model | Pipeline + GUI | Web annotation | DH archival encoding | Human annotation GUI | Collaborative reading |
| Overlapping annotations | Native (standoff) | Native (standoff) | Native (JSON objects) | Workaround required | Via UIMA backend | Native (JSON-LD) |
| User-defined types | Full type system | CREOLE plugins | Custom body JSON | Custom TEI elements | Layer definitions | Tag vocabularies |
| Web-native | No | No | Yes (JSON-LD) | No | Partial | Yes |
| Active learning | No | No | No | No | Yes (built-in) | No |
| Multi-annotator | Yes (via XMI export) | Yes | No | No | Yes (native) | Groups only |
| Best for Palimpsest | Backend pipeline exchange | Rule-based pipeline | Primary data model | Source text archival | Human annotation UI | Reader discussion layer |

---

## Recommendations

### Primary Recommendation: W3C Web Annotation + INCEpTION + BookNLP

Build Palimpsest's data model around the W3C Web Annotation Data Model (JSON-LD), with custom body types for each literary annotation layer. This gives:
- Interoperability with any W3C-compliant tool (Hypothes.is, Annotation Studio).
- Natural handling of overlapping, multi-layer annotations.
- A web-native REST API with the W3C Annotation Protocol.
- Future-proof format with strong community support.

Use INCEpTION as the primary human annotation interface for scholarly work. Its active learning, knowledge base integration, and UIMA CAS XMI export make it the richest available tool. The November 2024 EMNLP demo of its external automation integration means you can wire BookNLP and LLM pre-annotators directly into the INCEpTION curation workflow.

Use BookNLP as the automated extraction layer for character mentions, coreference, and quote attribution. Accept that it covers approximately 60% of the "reader's guide" annotation types; the rest requires human input.

Rationale: this stack minimizes build effort while maximizing capability. The W3C data model is the right long-term format; INCEpTION handles the human workflow; BookNLP handles the automatic baseline.

Caveats: INCEpTION's UI is optimized for sequential annotation tasks (NER, relations), not for the "browser's guide" level of annotation (themes, plot arcs, intertextual networks). You will likely need a custom Palimpsest UI for reader-facing annotation that stores its data as W3C Annotations. INCEpTION serves the scholarly back-end workflow.

### Alternative: Hypothes.is + Custom Schema

If the primary use case is reader-facing collaborative annotation (not scholarly NLP pipeline work), deploy a self-hosted Hypothes.is instance with a custom tag vocabulary (structured JSON in the annotation body). This is lower infrastructure overhead and gives immediate social annotation features (threads, replies, groups).

When to use: for the Palimpsest "reading group" mode where readers collaboratively annotate texts. Pair with a custom visualization layer that reads the Hypothes.is API and renders annotation density, character co-occurrence, and intertextual reference maps.

### Recommendation for Intertextual Reference Detection

No existing tool handles the "book references within letters in a novel" task end-to-end. Implement the four-stage pipeline described in Section 5:
1. Regex + rule-based explicit detection.
2. Dense embedding retrieval (candidate generation).
3. LLM verification with structured output.
4. Human confirmation in Prodigy.

The critical dependency is a good knowledge base of literary titles and their metadata. Wikidata's literary works ontology (Q47461344 = literary work) is the best free source; OpenLibrary provides ISBN-level metadata; Project Gutenberg provides full texts of public domain works for embedding.

---

## Action Items

- [ ] Evaluate `booknlp` Python package output on a chapter of "The Correspondent" — establish baseline character extraction quality before any fine-tuning.
- [ ] Deploy self-hosted INCEpTION instance (Docker image: `ghcr.io/inception-project/inception`); define a project with custom annotation layers matching the Palimpsest annotation schema.
- [ ] Define the Palimpsest annotation type schema as W3C Web Annotation body extensions: `CharacterPresence`, `PlotPoint`, `ThematicTag`, `IntertextualReference`, `SceneBoundary`, `ReaderNote`.
- [ ] Build a Wikidata + OpenLibrary literary title index for Stage 1 of the intertextuality pipeline.
- [ ] Implement the Tesserae-style TF-IDF text reuse scoring function in Python and run it against the target novel + a corpus of candidate source texts.
- [ ] Evaluate Gemini 1.5 Flash vs. GPT-4o for structured character relation extraction — compare cost, accuracy, and JSON schema compliance.
- [ ] Survey existing digital humanities corpora in TEI XML for candidate import into Palimpsest (DTA, EEBO-TCP, Folger Digital Texts).

---

## Sources

1. [Apache UIMA Overview and SDK Setup](https://uima.apache.org/d/uimaj-current/oas.html)
2. [OASIS UIMA Specification v1.0](https://docs.oasis-open.org/uima/v1.0/os/uima-spec-os.html)
3. [GitHub: texttechnologylab/UIMA-Agreement](https://github.com/texttechnologylab/UIMA-Agreement)
4. [W3C Web Annotation Data Model (Recommendation)](https://www.w3.org/TR/annotation-model/)
5. [W3C Web Annotation Working Group](https://www.w3.org/annotation/)
6. [STAM: Stand-off Text Annotation Model](https://annotation.github.io/stam/)
7. [GitHub: annotation/stam](https://github.com/annotation/stam)
8. [TEI Wiki: Stand-off Markup](https://wiki.tei-c.org/index.php/Stand-off_markup)
9. [Balisage: Implementing TEI Standoff Annotation in the Browser (Cayless, 2019)](https://balisage.net/Proceedings/vol23/html/Cayless01/BalisageVol23-Cayless01.html)
10. [Balisage: Why TEI Stand-off Annotation Doesn't Quite Work (Banski, 2010)](https://www.balisage.net/Proceedings/vol5/html/Banski01/BalisageVol5-Banski01.html)
11. [Toward a TEI/RDF Encoding for Semantic Annotations (TEI MEC 2023)](https://teimec2023.uni-paderborn.de/contributions/165.html)
12. [GitHub: booknlp/booknlp](https://github.com/booknlp/booknlp)
13. [GitHub: dbamman/book-nlp (Java, archival)](https://github.com/dbamman/book-nlp)
14. [Improving Automatic Quotation Attribution in Literary Novels (arXiv 2307.03734)](https://arxiv.org/html/2307.03734)
15. [Improving Quotation Attribution with Fictional Character Embeddings (arXiv 2406.11368)](https://arxiv.org/html/2406.11368v1)
16. [GitHub: dbamman/litbank](https://github.com/dbamman/litbank)
17. [An Annotated Dataset of Literary Entities — Bamman et al. NAACL 2019 (PDF)](https://people.ischool.berkeley.edu/~dbamman/pubs/pdf/naacl2019_literary_entities.pdf)
18. [LitBank: Born-Literary NLP (Bamman, DH Debates)](https://people.ischool.berkeley.edu/~dbamman/pubs/pdf/Bamman_DH_Debates_CompHum.pdf)
19. [Integrating INCEpTION into Larger Annotation Processes (EMNLP 2024 Demo)](https://aclanthology.org/2024.emnlp-demo.12.pdf)
20. [Label Studio vs Doccano vs Prodigy: 2026 Comparison (AI Taggers)](https://aitaggers.com.au/blog/label-studio-vs-doccano-vs-prodigy-2026)
21. [Top Text Annotation Tools in 2025 (Encord)](https://encord.com/blog/top-text-annotation-tools-in-2024/)
22. [Active Learning and Human-in-the-Loop for NLP Annotation (DZone)](https://dzone.com/articles/active-learning-nlp-annotation)
23. [GrAF: A Graph-based Format for Linguistic Annotations (Ide, Vassar PDF)](https://www.cs.vassar.edu/~ide/papers/LAW.pdf)
24. [The Linguistic Annotation Framework: A Standard for Annotation Interchange (Springer)](https://link.springer.com/article/10.1007/s10579-014-9268-1)
25. [Penn Discourse Treebank Version 2.0 (LDC)](https://catalog.ldc.upenn.edu/LDC2008T05)
26. [Penn Discourse Treebank Version 3.0 (Princeton DSS)](https://dss.princeton.edu/catalog/resource5296)
27. [The Penn Discourse TreeBank 2.0 (Prasad et al., LREC 2008)](http://www.lrec-conf.org/proceedings/lrec2008/pdf/754_paper.pdf)
28. [Fast Rhetorical Structure Theory Discourse Parsing (arXiv 1505.02425)](https://arxiv.org/abs/1505.02425)
29. [RST Parsing from Scratch (arXiv 2105.10861)](https://arxiv.org/abs/2105.10861)
30. [GitHub: EducationalTestingService/rstfinder](https://github.com/EducationalTestingService/rstfinder)
31. [Computational Approaches to Intertextuality (Antwerp PDF)](https://repository.uantwerpen.be/docman/irua/6b6d46/178931.pdf)
32. [The Tesserae Project: Intertextual Analysis of Latin Poetry (Semantic Scholar)](https://www.semanticscholar.org/paper/The-Tesserae-Project:-intertextual-analysis-of-Coffee-Koenig/21e377ff25b2fac9b38d7fb7b7607bc3ebf28cb2)
33. [Characterizing the Effects of Translation on Intertextuality (arXiv 2501.10731)](https://arxiv.org/pdf/2501.10731)
34. [Latent Structures of Intertextuality in French Fiction (arXiv 2410.17759)](https://arxiv.org/pdf/2410.17759)
35. [Intertextuality Detection Using Word2Vec Models (ResearchGate)](https://www.researchgate.net/publication/321351908_Intertextuality_detection_in_literary_texts_using_Word2Vec_models)
36. [A City of Millions: Mapping Literary Social Networks at Scale (arXiv 2502.19590)](https://arxiv.org/pdf/2502.19590)
37. [Large Language Models Fall Short: Complex Relationships in Detective Narratives (arXiv 2402.11051)](https://arxiv.org/pdf/2402.11051)
38. [Grounding Characters and Places in Narrative Texts (arXiv 2305.17561)](https://arxiv.org/pdf/2305.17561)
39. [Evaluating NER Tools for Social Networks from Novels (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC7924459/)
40. [Towards an Event Based Plot Model (JCLS)](https://jcls.io/article/id/110/print/)
41. [A Survey on Event-Based News Narrative Extraction (ACM Computing Surveys)](https://dl.acm.org/doi/full/10.1145/3584741)
42. [Annotation Studio (MIT OpenCourseWare)](https://ocw.mit.edu/courses/cms-633-digital-humanities-spring-2015/pages/instructor-insights/on-annotation-studio/)
43. [CLÉA: Collaborative Literature Exploration and Annotation (DH 2012)](https://www-archiv.fdm.uni-hamburg.de/dh2012/conference/programme/abstracts/crowdsourcing-meaning-a-hands-on-introduction-to-clea-the-collaborative-literature-exploration-and-annotation-environment.html)
44. [Hypothes.is Wikipedia](https://en.wikipedia.org/wiki/Hypothes.is)
45. [GitHub: hypothesis/h](https://github.com/hypothesis/h)
46. [Towards Cross-Platform Interoperability for Machine-Assisted Text Annotation (PMC)](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6808624/)
47. [GATE User Guide](https://gate.ac.uk/releases/gate-7.0-build4195-ALL/doc/tao/)
48. [A General Architecture for Language Engineering (GATE arXiv)](https://arxiv.org/pdf/cmp-lg/9601009)
49. [Stanza: A Python NLP Toolkit (arXiv 2003.07082)](https://arxiv.org/pdf/2003.07082)
50. [spaCy Official: Linguistic Features](https://spacy.io/usage/linguistic-features)

---

## Uncertainties

- **Scene segmentation**: no published model reliably segments literary fiction into discrete scenes. This remains a manual task or requires training a custom classifier. The LitBank event layer partially addresses this (event realis annotation), but scene boundaries are distinct from event boundaries.
- **RST on literary fiction**: all RST parsers are trained on news or conversational text. Transfer performance on novel-length literary text is untested in the literature. Empirical evaluation would be required.
- **Intertextual paraphrase detection at novel scale**: the dense retrieval approach (Stage 2 of the recommended pipeline) has been validated on poetry and classical texts but not on modern English-language fiction. False positive rates for thematically similar but non-intertextual passages are unknown.
- **LLM reliability for literary annotation**: LLMs achieve high accuracy on structured extraction tasks but have documented hallucination risks for literary interpretation. The human-in-the-loop confirmation step is not optional — it is architecturally necessary.
- **Epistolary fiction structure**: the specific challenge of detecting embedded book references within letters-within-a-novel is not addressed by any existing NLP tool or dataset. This is a genuinely novel problem that the Palimpsest system would be among the first to solve at scale.

## Related Topics for Future Research

- **Character arc modeling**: tracking how character attributes (emotional state, knowledge, relationships) change across a novel's timeline — related to LitBank event annotation but requiring temporal reasoning.
- **Digital scholarly editions**: how projects like the Digital Thoreau, Frankenstein Variorum, and EEBO-TCP handle multi-layer annotation in production — practical case studies.
- **Semantic role labeling for narrative**: FrameNet-based annotation of who did what to whom, as a structured representation of plot events.
- **Cross-lingual literary annotation**: adapting this pipeline for non-English texts — Stanza covers 60+ languages but LitBank is English-only.
- **Visualization methods for annotation layers**: dot-plot, arc diagram, and network graph approaches for displaying annotation density and relationships across a text.
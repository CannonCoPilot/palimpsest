# Research Report: Visualization and Interactive Exploration Patterns for Multi-Layer Text Annotation in Literary Analysis

**Date**: 2026-06-06
**Scope**: Architecture patterns, visualization paradigms, and interaction design for a computational literary analysis platform (Palimpsest) focusing on intertextual reference visualization in an epistolary novel ("The Correspondent"), drawing on genome browser technology, digital humanities tools, and information visualization research.

---

## Executive Summary

The challenge of visualizing intertextual references in a literary platform like Palimpsest sits at the intersection of three mature but largely separate technical traditions: genome browser engineering (multi-track, multi-zoom data visualization), digital humanities annotation tools (per-text flexible schemas, hermeneutic exploration), and information visualization (chord diagrams, linked views, semantic zoom).

The most architecturally instructive model is JBrowse 2, which solved an almost identical problem in genomics — multiple overlapping annotation tracks on a 1D sequence at variable zoom — using a clean four-layer abstraction: Adapter (data), Track (what to show), Display (how to show it for a given view type), and Renderer (pixel-level drawing). This maps almost directly onto text: the "genome" becomes the text; "chromosomal position" becomes character offset; "tracks" become annotation layers (book references, narrative context, letter provenance, etc.).

For the chord/circular reference diagram, D3's chord module provides a proven data-format-to-visual pipeline, but the more interesting design problem is the data model: the DHQ formalization of intertextuality (Horstmann et al.) provides an OWL/WADM-compatible schema with `here` references (text passage + character offsets), `there` references (external work), and `specifiedBy` (relation type like "quotation," "allusion," "thematic echo"), which slots directly into a D3 chord matrix.

The critical insight for managing 5–10 concurrent annotation layers without overwhelming users comes from CATMA, ANNIS, and the VIANA research: layers should be task-specific and toggled rather than permanently visible; each layer should have a distinct visual channel (color, shape, stroke style); and every overview visualization should preserve a direct click-through path to the source text.

---

## Key Findings

### Finding 1: JBrowse 2 — The Genome Browser as Architectural Template

JBrowse 2 (current stable: v2.17.0, November 2024) is a complete rewrite of JBrowse 1 using React, TypeScript, and MobX-state-tree. Its architecture is directly applicable to a "text browser" for Palimpsest.

**The five-layer pluggable element hierarchy:**

```
View (LinearGenomeView, CircularView, DotplotView)
  └── Track (what data, what adapter)
       └── Display (how to render for a specific view type)
            └── Renderer (runs in web worker, draws to OffscreenCanvas)
       └── Adapter (data source parsing)
```

A single Track can have multiple Display types — for example, a `VariantTrack` has both a `LinearVariantDisplay` (for the standard scroll view) and a `ChordVariantDisplay` (for the circular structural variant view). This is the key pattern for Palimpsest: a "book references" annotation layer should have a `LinearTextDisplay` (inline highlights in the reading view) and a `ChordDisplay` (arcs in the circular reference diagram) controlled by the same underlying data and Track state.

**MobX-state-tree state management:** Every view, track, and display has a corresponding MST model. React components are `observer`-wrapped and re-render reactively when model state changes. This makes cross-view synchronization (linked views) trivial: changing the selected annotation in one view updates shared MST state that all observer components react to.

**Zoom-level rendering strategy:** At low zoom (overview), genome browsers show density histograms or heat maps. At high zoom, individual features with full detail. The same pattern for text: at "chapter level" zoom, show a barcode/sparkline of annotation density; at "paragraph level" zoom, show individual highlighted spans with labels. JBrowse 2 samples data according to current zoom level and caches derived views (e.g., pre-computed mismatch data for long reads).

**Composability:** Adapters can wrap other adapters. Views can contain sub-views. Tracks can contain sub-tracks (e.g., `AlignmentsTrack` is a composite of a pileup display and a coverage wiggle). This enables compound annotation views in Palimpsest without monolithic components.

**Source**: [JBrowse 2 Developer Guide](https://jbrowse.org/jb2/docs/developer_guide/), [JBrowse Pluggable Elements](https://jbrowse.org/jb2/docs/developer_guides/pluggable_elements/), [JBrowse GitHub](https://github.com/GMOD/jbrowse-components)

---

### Finding 2: IGV.js — Lightweight Embeddable Alternative

IGV.js is the lighter-weight alternative to JBrowse 2: a single JavaScript file, no external dependencies, embedded via `igv.createBrowser(div, config)`. It is organized around track type objects (annotation, quantitative, alignment, variant) initialized from JSON configuration objects.

**What it contributes beyond JBrowse:** IGV.js's session serialization API — `browser.toJSON()` returns a compressed URL-safe string encoding the complete browser state including all loaded tracks, current view, and settings. This is directly applicable to Palimpsest's sharing/bookmarking use case: a user's current annotation layer configuration, zoom level, and selected text passage can be serialized into a shareable URL.

IGV.js does not have JBrowse 2's full plugin architecture or multi-view support, but its simpler API surface makes it easier to embed as a component in a larger application without fighting the host framework.

**Source**: [IGV.js GitHub](https://github.com/igvteam/igv.js), [IGV.js paper (Bioinformatics 2023)](https://academic.oup.com/bioinformatics/article/39/1/btac830/6958554)

---

### Finding 3: Genome Browser Zoom Level Strategies

Genome browsers have developed a well-tested set of rendering strategies for different zoom levels, all applicable to text:

| Zoom Level | Genomics Rendering | Text Analog |
|---|---|---|
| Overview (whole genome) | Karyotype ideogram, density bands | Document-level barcode (AntConc-style) |
| Mid-range (chromosome region) | Feature density heat map, coverage wiggle | Chapter/section density bar charts |
| Feature level | Labeled rectangles per feature, color-coded | Highlighted spans with inline labels, visible tag names |
| Base level | Individual nucleotides, per-base coloring | Individual characters, glyph-per-character annotations |

The key principle is **semantic zoom**: the representation changes qualitatively, not just in size. At text overview level, the question is "where in the novel does this annotation type occur?" At feature level, the question is "what exactly is this annotation?" These are fundamentally different questions requiring different visual representations.

**Source**: [Genome Maps paper (NAR 2013)](https://academic.oup.com/nar/article/41/W1/W41/1113984), Genome Explorer (bioRxiv 2024)

---

### Finding 4: Digital Humanities Annotation Tools — Paradigms and Gaps

**CATMA (v7.2.0, 2025)** is the closest existing tool to what Palimpsest needs for the annotation side. Its key innovations:

- Per-project tagsets (annotation schemas): users create custom tag hierarchies, either taxonomy-based or developed on the fly during analysis. These tagsets are per-project, not global, matching the "per-text unique annotation types" requirement.
- Overlapping, non-hierarchical annotations: CATMA explicitly embraces "undogmatic" annotation — multiple, overlapping, contradictory annotations on the same span are permitted and stored.
- Distribution graphs: show where annotation types concentrate across text length (x-axis = position as % of text; y-axis = frequency per segment). Clicking a spike opens a KWIC table, which allows double-clicking to jump to source text. This is the distant-to-close reading pipeline in action.
- The `DoubleTree` visualization: a center-out branching diagram showing words that co-occur around a query term, where bubble size encodes frequency. Useful for understanding the narrative context of referenced books.

**CATMA's limitation for Palimpsest:** Its visualizations are corpus-statistical (frequency, co-occurrence, KWIC). It has no spatial/geographic or network/chord view. It cannot represent the "which books reference which other books" relationship as a chord diagram.

**Recogito / RecogitoJS** is the W3C-standard-compliant annotation layer: every annotation is a W3C WebAnnotation JSON-LD object with `hasTarget` (text position via `TextPositionSelector` or `TextQuoteSelector`) and `hasBody` (annotation content and type). This is the correct data format for storing Palimpsest's annotations, since it is interoperable, dereferenceable, and supports fragment selectors for character-offset-based text targeting. Recogito Studio (2024) adds real-time multi-user annotation with WebSocket synchronization.

**ANNIS** is the gold standard for multi-layer corpus search and visualization, but its architecture (Java/PostgreSQL backend, Vaadin web frontend) and query language (AQL) are oriented toward linguistic corpora (syntax trees, dependency graphs, morphology). Its key contribution for Palimpsest is the AQL pattern: a graph-based query language where you search for "annotation node A adjacent to annotation node B within a span of N characters," enabling queries like "find all instances where a book reference annotation overlaps with a named emotion annotation."

**Voyant Tools** contributes the concept of a fully linked tool suite: Cirrus (word cloud), Bubblelines (frequency-per-segment timeline), TermsBerry (co-occurrence), Trends (word frequency over document), and Contexts (KWIC) are all separate panels but wired together — clicking in any panel updates all others. This is exactly the linked-views architecture that Palimpsest needs.

**AntConc's Concordance Plot** is the simplest possible version of the "distribution across text" visualization: a barcode where each black tick is a keyword occurrence, the bar width represents text length, and tick density visually encodes distribution patterns. This is the baseline visualization for any single annotation type.

**Source**: [CATMA](https://catma.de/), [CATMA Analyze & Visualize Tutorial](https://catma.de/how-to/tutorials/analyze-and-visualize/), [Recogito JS GitHub Wiki](https://github.com/recogito/recogito-js/wiki/API-Reference), [ANNIS](https://corpus-tools.org/annis/), [Voyant Tools](https://voyant-tools.org/docs/tutorial-tools_.html), [AntConc Concordance Plot Manual](https://antconc-manual.readthedocs.io/en/latest/concordance_plot.html)

---

### Finding 5: The Intertextuality Data Model — A Formal Schema for "Book References"

The most directly applicable scholarly work for the Palimpsest data model is the DHQ formalization of intertextuality by Horstmann, Lück, and Normann (2023, DHQ 17:3), paired with the Intertextor project (DHd 2024, award-winning poster).

**The formal model defines:**

- `IntertextualRelation`: a directed, asymmetric link from a "here" text to a "there" text (anti-chronological: later text → earlier text)
- `here`: a `Reference` pointing to a specific location in the source text (e.g., a passage in "The Correspondent")
- `there`: a `Reference` pointing to the referenced external text (e.g., a specific chapter of *Don Quixote*, or the work as a whole, or a genre)
- `specifiedBy`: an `IntertextualSpecification` that characterizes the relation type (quotation, allusion, parody, transposition, thematic echo — extensible via ontology)
- `mediatedBy`: optional `Mediator` elements (motifs, titles, characters that signal the reference)

**Reference granularity levels (the "4 zoom levels" Intertextor discusses):**

1. `TextSegment` — specific passage (character offsets)
2. `SingleText` / `Work` — the complete book
3. `TextGenre` / `System` — genre, author corpus, literary movement

These map precisely onto the D3 chord diagram's arc structure: at the `Work` level, one arc per referenced book; at the `System` level, arcs represent genres or authors.

**Web Annotation Data Model (WADM) mapping:**

```json
{
  "@type": "Annotation",
  "hasTarget": {
    "source": "https://palimpsest.example/texts/correspondent/letter-23",
    "selector": {
      "@type": "TextPositionSelector",
      "start": 1204,
      "end": 1287
    }
  },
  "hasBody": {
    "@type": "IntertextualRelation",
    "there": {
      "work": "https://openlibrary.org/works/OL27448W",
      "title": "Don Quixote",
      "author": "Cervantes",
      "genre": ["novel", "satire"],
      "theme": ["chivalry", "madness", "imagination"]
    },
    "specifiedBy": {
      "relationType": "allusion",
      "modalType": "playful"
    }
  }
}
```

This structure supports filtering the chord diagram by `genre`, `author`, or `relationType` directly.

**Source**: [DHQ: Systems of Intertextuality](https://dhq.digitalhumanities.org/vol/17/3/000731/000731.html), [Intertextor DHd-2024 GitHub](https://github.com/intertextor/dhd-2024), [Intertextor organization](https://github.com/intertextor)

---

### Finding 6: Chord Diagrams for Intertextual Reference Visualization

D3's `d3-chord` module provides the computational pipeline for circular reference diagrams.

**Data format required:**

For a chord diagram where arcs represent referenced books and chords represent co-reference patterns (passages in "The Correspondent" that reference multiple books), the matrix is:

```js
// matrix[i][j] = number of passages that reference both book i and book j
// diagonal matrix[i][i] = passages referencing only book i
const matrix = [
  [12, 3, 0, 2],   // Don Quixote
  [ 3, 8, 1, 0],   // Orlando Furioso
  [ 0, 1, 5, 4],   // The Canterbury Tales
  [ 2, 0, 4, 7],   // The Decameron
];
```

Alternatively, for a diagram where one arc represents the source text and other arcs represent referenced books (radial spoke model):

```js
// arcs: [source_novel, book_A, book_B, book_C, ...]
// matrix[0][i] = number of references from the novel to book_i
// matrix[i][0] = 0 (books don't reference the novel)
```

**Interactive filtering by genre/theme/author:**

The filtering approach is opacity-based: on hover or filter selection, set chord ribbon opacity to 0 for non-matching chords and 1 for matching ones. With D3, this is done by maintaining the full chord set and toggling CSS classes or `opacity` attributes:

```js
svg.selectAll('.chord')
  .attr('opacity', d =>
    bookMetadata[d.source.index].genre.includes(selectedGenre) ? 1 : 0.05
  );
```

For color coding: assign a color scale to genres, authors, or relation types, and apply `fill` to both arc groups and ribbon paths using the same scale so the visual language is consistent across views.

**Position-on-arc encoding:** For the use case of linking text positions to the chord diagram, an arc can be subdivided using D3's `arcGroup` — the arc for "The Correspondent" is divided into character-position segments, so each chord originates from the correct linear position in the text (like a miniature AntConc barcode on the circumference of the circle). This requires pre-computing character offset → arc angle mappings.

**Existing literary implementations:** The Yale DHLab's Intertext project (now migrated to the Yale Digital Humanities Lab) combines ML-based text reuse detection with interactive visualization. The Quantitative Intertextuality survey (Oxford UP, 2025) reports that researchers are now processing 14 million intertextual pairs from 202,000 texts using vector retrieval, feeding results into network visualizations.

**Source**: [D3 chord module](https://d3js.org/d3-chord), [d3-graph-gallery chord diagram](https://d3-graph-gallery.com/chord.html), [Visual Cinnamon gradient chord](https://www.visualcinnamon.com/2016/06/orientation-gradient-d3-chord-diagram/), [D3 chord GitHub](https://github.com/d3/d3-chord)

---

### Finding 7: Multi-Layer Annotation Visualization — Managing 5–10 Concurrent Layers

The central problem: how do you show, say, (1) book references, (2) emotional register, (3) narrative time, (4) letter recipient, (5) intertextual density, and (6) authorial irony as concurrent annotation layers on the same text passage without the display becoming unreadable?

**Four proven patterns, from least to most complex:**

**Pattern A — Track-based (genome browser style):** Annotation layers appear as horizontal bands above the text, each occupying its own vertical lane. The text is the reference track; annotations appear as colored rectangles in assigned lanes. Pros: complete visual separation, arbitrary number of layers, no text obscuration. Cons: layers are spatially separated from the text they annotate; reading and interpreting simultaneously requires eye movement. Best for: overview and structural analysis.

**Pattern B — Color-coded inline spans:** Each layer is assigned a unique color; highlighted spans are rendered as colored background fills or underlines directly in the text. Multiple overlapping layers combine colors (additive or layered borders). Pros: annotations are in-situ, natural reading flow. Cons: more than 3–4 overlapping layers become unreadable; color channels are limited. Best for: 2–3 actively focused layers at close reading zoom.

**Pattern C — Margin annotations (Hypothesis model):** Annotation markers appear in a side rail (right or left margin); hovering or clicking reveals the annotation detail in a popup or side panel. Multiple annotations at the same line appear as stacked icons. Pros: text is never occluded; annotations at different granularities can coexist. Cons: spatial relationship between annotation and annotated span must be maintained with a connecting line; dense annotation regions create icon pileup. Best for: qualitative/interpretive annotations like notes, debates, commentaries.

**Pattern D — Task-specific layer panels (VIANA model):** Only the annotation layers relevant to the current analytical task are shown; others are toggled off. Smooth transitions (morphing animations) maintain orientation when switching between layer configurations. A layer panel UI (sidebar or toolbar) shows all available layers with toggle switches, count badges, and color swatches. Pros: avoids cognitive overload entirely; each task has a focused view. Cons: requires good layer organization and naming; users must know which layers are relevant to their task.

**The recommended approach for Palimpsest:** A hybrid of C and D. The persistent layer panel (D) controls which layers are visible. Active layers show inline color spans (B) for the 1–2 "primary" layers in focus, plus margin annotation markers (C) for secondary layers. A global annotation density track (A) appears above the text at all times as an overview.

**Visual encoding recommendations** for distinguishing layers:
- Reserve color hue for layer identity (each layer has a unique hue)
- Use luminance/saturation to encode within-layer properties (e.g., relation type certainty, sentiment valence)
- Use border style (solid, dashed, dotted) as a redundant cue when layers overlap
- Keep the color palette to maximum 8–10 perceptually distinct hues (use ColorBrewer qualitative scales)

**Source**: [VIANA paper arXiv](https://arxiv.org/pdf/1907.12413), [CATMA annotation tutorial](https://catma.de/how-to/tutorials/manual-annotation/), [Annotation design arXiv 2604.07691](https://arxiv.org/pdf/2604.07691), [USPTO annotation layer patent 11003843](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/11003843)

---

### Finding 8: Interactive Exploration — Semantic Zoom and Linked Views

**Shneiderman's mantra** ("overview first, zoom and filter, then details on demand") is the foundational principle, operationalized in modern visualization as semantic zoom + coordinated multiple views (CMV).

**Semantic zoom for text:**

| Zoom Level | What the User Sees | Primary Question |
|---|---|---|
| Corpus / document overview | Annotation density heatmap across entire novel; chord diagram of all book references | Where does this reference type occur? How connected are the referenced books? |
| Chapter / section level | Barcode visualization (AntConc-style) + distribution graph (CATMA-style) per chapter | Which chapters are richest in references? |
| Paragraph / passage level | Highlighted spans in text, annotation labels in margin | What exactly is this reference? What is its context? |
| Sentence / span level | Full annotation detail panel: referenced book metadata, relation type, scholar notes | What can be said about this specific reference? |

The CATMA approach of clicking a distribution spike → KWIC table → double-click to source text is the proven three-step drill-down pattern. Sensecape's three-level semantic zoom (keyword → summary sentence → full text) shows this can work for LLM-generated summaries too.

**Linked views architecture:**

Brushing-and-linking is the technical mechanism: selecting a region in one view propagates a filter to all linked views. Implementation choices:

1. **Shared state store (MobX/Redux/Zustand):** All views subscribe to a shared selection/filter state. Changing selection in any view updates the store; all subscribed views react. This is the JBrowse 2 pattern (MST models as shared state).

2. **Event bus:** Views publish `annotationSelected(annotationId)` events; other views subscribe and highlight/filter accordingly. Looser coupling, easier to add new views.

3. **URL-encoded state (IGV.js pattern):** Full view state in URL; deep links directly encode the selected annotation, active layers, and zoom level.

**Specific linked-view combinations for Palimpsest:**

- Chord diagram ↔ Linear text view: hovering a chord highlights the corresponding text spans; clicking a chord zooms the text view to the first occurrence
- Distribution graph ↔ KWIC table ↔ Text passage: clicking a spike in the distribution graph populates the KWIC table; double-clicking a KWIC row scrolls/highlights the text
- Author filter in chord legend ↔ All views: toggling "show only Cervantes references" grays out non-Cervantes chords, dims non-Cervantes inline highlights, and filters the KWIC table
- Text position slider ↔ Chord diagram: moving through the novel (by chapter or character offset) animates the chord diagram to show only references that occur in the current text window

**Performance guidance:** User performance improves 30–80% with coordinated overview and detail views in exploratory tasks (CMV research). But clutter from too many linked views is a real hazard — keep the default view to 2–3 panels; advanced views available on demand.

**Source**: [Semantic Zoom InfoVis Wiki](https://infovis-wiki.net/wiki/Semantic_Zoom), [Brushing and Linking Wikipedia](https://en.wikipedia.org/wiki/Brushing_and_linking), [CMV state of the art ResearchGate](https://www.researchgate.net/publication/4259731_State_of_the_Art_Coordinated_Multiple_Views_in_Exploratory_Visualization), [Observable linked brushing](https://observablehq.com/blog/linked-brushing)

---

### Finding 9: Apollo 3 — Collaborative Annotation Model

Apollo 3 (public beta, December 2024) is the genome annotation editor built directly on JBrowse 2. Its collaborative model is the "Google Docs of genome annotation."

**Architecture for collaboration:**

- Apollo runs as a client-server system: the Apollo Server maintains the authoritative annotation database; clients (JBrowse 2 instances with Apollo plugin loaded) connect via WebSocket
- All edits in one client are instantly pushed to all other connected clients — true real-time synchronization, not eventual consistency
- Users can choose to make their annotation work public or restricted to specific collaborators
- Demo mode (single-user, session-local) vs. server mode (multi-user, persistent) are both supported

**Conflict resolution in Apollo (classical Web Apollo):** The original Web Apollo took the approach of synchronization over locking — rather than preventing concurrent edits, it accepted them and relied on real-time sync to surface conflicts immediately. In practice, curators at the same genomic region simultaneously making edits would see each other's cursors/edits in near-real-time (similar to Google Docs cursor tracking), which serves as a social conflict prevention mechanism. Formal automated conflict detection (two users asserting contradictory attributes of the same feature) was handled by database constraints and surfaced to a curator for manual resolution.

**For Palimpsest's collaborative annotation:** The Apollo model suggests:

- Store annotations in a central annotation server (not just client-side)
- Use WebSocket for real-time sync of annotation creation/deletion/modification events
- Show collaborator presence indicators (named cursors or ghost highlights) on the text
- For competing annotations on the same span (e.g., two scholars disagree about whether a reference is "allusion" or "quotation"), store both annotations with annotator identity and expose them as a "contested" flag — do not force resolution, since humanities scholarship values the productive tension of disagreement

**Source**: [Apollo 3 Beta Release Blog](https://apollo.jbrowse.org/blog/), [Web Apollo paper (Genome Biology 2013)](https://genomebiology.biomedcentral.com/articles/10.1186/gb-2013-14-8-r93), [Apollo Democratizing paper (PLoS CB 2019)](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6380598/)

---

### Finding 10: Per-Text Flexible Annotation Schemas

The @Note system and CATMA both establish the correct design pattern for per-text unique annotation types:

**Schema isolation:** Each text (or "annotation activity" in @Note's terminology) has its own annotation schema — a hierarchy of annotation types and categories. Schema is not global. A book-reference schema for "The Correspondent" may have types `{quotation, allusion, thematic_echo, structural_parallel}` while a different novel uses `{biblical_ref, classical_ref, contemporary_ref}`.

**CATMA's implementation:** Users create "Tagsets" (collections of related tag types) and assign them to projects. Tagsets can be built from scratch or imported. Tags can have properties (key-value metadata). Annotations associate a text span with a tag (and optionally tag property values).

**Recommended data model for Palimpsest:**

```
TextCorpus
  └── Text (e.g., "The Correspondent")
       ├── AnnotationSchema (per-text, versioned)
       │    ├── AnnotationType ("BookReference")
       │    │    ├── property: referencedWork (URI/title)
       │    │    ├── property: referenceType (enum: quotation, allusion, echo)
       │    │    ├── property: referencedGenre (tag)
       │    │    └── property: referencedAuthor (URI)
       │    └── AnnotationType ("NarrativeContext")
       │         ├── property: narrator (character name)
       │         └── property: temporalDistance (years from narrative present)
       └── AnnotationLayer (per AnnotationType)
            └── Annotation (W3C WebAnnotation, selector → text span)
```

**Versioning concern:** As schemas evolve during a research project, existing annotations may become inconsistent with updated types. The @Note system addressed this by separating "metalevel" schemas (theory-driven type hierarchies) from "work-oriented" schemas (empirical observation-driven). CATMA handles it by allowing "free tagging" — annotations can carry tags that don't yet exist in the formal tagset, deferring formalization.

**Source**: [A flexible model for collaborative annotation of literary works (DH2012)](https://www-archiv.fdm.uni-hamburg.de/dh2012/conference/programme/abstracts/a-flexible-model-for-the-collaborative-annotation-of-digitized-literary-works.1.html), [CATMA](https://catma.de/)

---

## Comparison: Visualization Approaches for Intertextual Reference Data

| Visualization | What it shows | Best zoom level | Interaction | DH tool precedent |
|---|---|---|---|---|
| **Chord diagram** | Book-to-book co-reference co-occurrence; reference density per book | Corpus overview | Hover to highlight; filter by genre/author/type | D3; Circos; no direct DH precedent |
| **Arc diagram (linear)** | References ordered by text position; chords connect source passage to referenced work | Document level | Zoom to region; filter layers | Intertextor (design phase) |
| **AntConc-style barcode** | Annotation occurrence distribution across text length | Document/chapter | Click to jump to source | AntConc; CATMA distribution graph |
| **CATMA distribution graph** | Tag frequency per segment over document length | Chapter level | Click spike → KWIC; double-click → source text | CATMA |
| **KWIC / concordance table** | All occurrences with surrounding context | Passage level | Click row → source text; select rows → annotate | CATMA; AntConc |
| **Inline highlighted spans** | Exact text spans with color-coded annotation types | Sentence level | Hover → popup; click → detail panel | Recogito; Hypothesis; CATMA |
| **Network graph** | Intertextual relationships as nodes/edges across texts | Corpus network | Force-directed layout; cluster by genre; zoom to subgraph | Intertext (Yale); Gephi |
| **Margin annotation rail** | Qualitative annotations, comments, debate threads | Passage level | Click to expand; thread replies | Hypothesis; Recogito Studio |

---

## Recommendations

### 1. Primary Recommendation: JBrowse 2-Style Architecture with CATMA-Style Visualization Suite

Adopt JBrowse 2's four-layer pluggable element architecture (Adapter → Track → Display → Renderer) as the core architecture for Palimpsest's annotation visualization engine. The text is the "genome"; character offsets replace genomic coordinates; annotation layers replace genome tracks.

- **Rationale:** This architecture has been battle-tested on the hardest version of this problem (millions of features, petabyte-scale genomic data, many annotation types). It is React/TypeScript-native, well-documented, and open source.
- **Adaptation required:** Replace genomic coordinate math with character offset math. Replace BAM/CRAM adapters with W3C WebAnnotation JSON-LD adapters. Implement a `TextLinearView` as the primary view type (analogous to `LinearGenomeView`).
- **Caveats:** JBrowse 2 is a large dependency (the full package). Consider `@jbrowse/react-linear-genome-view` as an embeddable component, or study its architecture as a reference implementation and build a smaller custom version.

### 2. Data Model: W3C WebAnnotation + DHQ Intertextuality Ontology

Use W3C WebAnnotation (JSON-LD) as the storage format for all annotations, extended with the Horstmann/Lück/Normann intertextuality properties for book reference annotations specifically. Recogito Studio provides a ready-made annotation server implementing this standard.

- **Rationale:** Interoperability, dereferenceable URIs for referenced works (link to Open Library, Wikidata, etc.), standard query APIs, and tooling support (RecogitoJS for front-end annotation UI, Hypothesis for general-purpose annotation import/export).
- **Caveats:** The DHQ ontology (OWL/RDF) needs translation to a JSON-LD context file for practical use; this is non-trivial but a one-time cost.

### 3. Chord Diagram: D3 `d3-chord` with Position-Encoded Source Arc

Build the intertextual chord diagram using D3's chord module with these specific customizations:
- **Source arc subdivision:** Divide the "The Correspondent" arc into chapter/letter segments so chord origins reflect text position
- **Color by referenced work attribute:** Use genre as the primary color dimension, author as secondary (encoded in chord opacity)
- **Filtering controls:** Dropdown/checkbox filters for genre, author, relation type; use opacity transitions (0.05 for non-matching, 1.0 for matching) for smooth visual filtering
- **Bidirectional linkage:** Hovering a chord scrolls/highlights corresponding text spans in the linear view; clicking a text span pulses the corresponding chord

### 4. Multi-Layer Display: Hybrid Track + Margin + Toggle

Implement a three-tier annotation display:
- **Top tier (always visible):** Annotation density overview track above the text — one thin colored bar per active annotation type showing distribution across document
- **Middle tier (in-text, up to 3 active layers):** Color-coded inline highlight spans for the 1–3 "primary focus" layers toggled on by the user
- **Bottom tier (always visible):** Margin annotation rail for qualitative annotations (notes, debates, scholar comments)

Layer management panel: floating sidebar with layer list, per-layer toggle, color swatch, count badge, and opacity slider.

### 5. Alternative: Label Studio as Annotation Collection Frontend

If building the annotation collection UI from scratch is out of scope, Label Studio (React + MobX-state-tree frontend, open source) supports custom annotation schemas, overlapping spans, and relation extraction. It can export in W3C WebAnnotation format. Use it as the annotation collection layer while building a custom visualization layer on top.

- **When to use:** When the priority is getting high-quality annotations quickly rather than building a fully integrated research platform

---

## Action Items

- [ ] Prototype a `TextPositionAdapter` implementing the JBrowse 2 adapter interface that reads W3C WebAnnotation JSON-LD from a REST endpoint, keyed by `TextPositionSelector.start/end`
- [ ] Implement a minimal `TextLinearView` component (React + MobX-state-tree) with character-offset scrolling, track lane rendering, and zoom level state — analogous to `@jbrowse/react-linear-genome-view`
- [ ] Design the per-text `AnnotationSchema` data model; implement schema CRUD API with versioning (store schema version on each annotation for forward compatibility)
- [ ] Build a D3 chord prototype for "The Correspondent" book references with: (a) source arc subdivided by letter number, (b) referenced-work arcs colored by genre, (c) hover-to-highlight linking to a static text view
- [ ] Adopt Horstmann et al.'s intertextuality ontology as the body content schema for book reference annotations; write a JSON-LD context file mapping it to W3C WebAnnotation `hasBody`
- [ ] Implement the distribution graph visualization (CATMA-style): x = character position as % of text, y = annotation count per segment, clickable data points that populate a KWIC panel
- [ ] Evaluate Apollo 3 for the collaborative annotation backend — particularly whether the JBrowse 2 plugin architecture can be extended with Palimpsest's custom text view while reusing Apollo's real-time sync infrastructure
- [ ] Design a "contested annotation" UI: when two annotators have conflicting annotations on the same span, display both with annotator attribution and a "discuss" thread (do not force resolution)

---

## Sources

1. [JBrowse 2 Developer Guide](https://jbrowse.org/jb2/docs/developer_guide/)
2. [JBrowse 2 Pluggable Elements](https://jbrowse.org/jb2/docs/developer_guides/pluggable_elements/)
3. [JBrowse 2 GitHub Repository](https://github.com/GMOD/jbrowse-components)
4. [JBrowse 2 v2.17.0 Release Notes](https://jbrowse.org/jb2/blog/2024/11/18/v2.17.0-release/)
5. [IGV.js GitHub](https://github.com/igvteam/igv.js)
6. [IGV.js paper (Bioinformatics 2023)](https://academic.oup.com/bioinformatics/article/39/1/btac830/6958554)
7. [CATMA — Computer Assisted Text Markup and Analysis](https://catma.de/)
8. [CATMA Analyze & Visualize Tutorial](https://catma.de/how-to/tutorials/analyze-and-visualize/)
9. [3DH: Three-Dimensional Dynamic Data Visualization](https://threedh.catma.de/)
10. [Recogito — Linked Data Annotation Without the Pointy Brackets (paper)](https://oro.open.ac.uk/49745/7/Simon_Barker_etal_2017_Recogito.pdf)
11. [RecogitoJS API Reference](https://github.com/recogito/recogito-js/wiki/API-Reference)
12. [Recogito Studio](https://recogitostudio.org/)
13. [W3C Web Annotation Working Group](https://www.w3.org/annotation/)
14. [W3C Web Annotation Protocol](https://www.w3.org/TR/annotation-protocol/)
15. [ANNIS — Multi-layer Corpus Browser](https://corpus-tools.org/annis/)
16. [ANNIS GitHub](https://github.com/korpling/ANNIS)
17. [ANNIS3: New Architecture paper (ResearchGate)](https://www.researchgate.net/publication/274083213_ANNIS3_A_New_Architecture_for_Generic_Corpus_Query_and_Visualization)
18. [AQL — ANNIS Query Language Reference](http://amir-zeldes.github.io/aql)
19. [Voyant Tools Documentation](https://voyant-tools.org/docs/tutorial-tools_.html)
20. [AntConc Concordance Plot Manual](https://antconc-manual.readthedocs.io/en/latest/concordance_plot.html)
21. [D3 chord module](https://d3js.org/d3-chord)
22. [D3 chord GitHub](https://github.com/d3/d3-chord)
23. [D3 Graph Gallery — Chord Diagram](https://d3-graph-gallery.com/chord.html)
24. [Visual Cinnamon — Gradient Chord Diagrams](https://www.visualcinnamon.com/2016/06/orientation-gradient-d3-chord-diagram/)
25. [DHQ: Systems of Intertextuality (Horstmann, Lück, Normann 2023)](https://dhq.digitalhumanities.org/vol/17/3/000731/000731.html)
26. [Intertextor GitHub Organization](https://github.com/intertextor)
27. [Intertextor DHd-2024 repository](https://github.com/intertextor/dhd-2024)
28. [Apollo 3 Beta Release](https://apollo.jbrowse.org/blog/)
29. [Web Apollo paper — Genome Biology 2013](https://genomebiology.biomedcentral.com/articles/10.1186/gb-2013-14-8-r93)
30. [Apollo: Democratizing genome annotation (PLoS CB 2019)](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6380598/)
31. [Semantic Zoom — InfoVis Wiki](https://infovis-wiki.net/wiki/Semantic_Zoom)
32. [Brushing and Linking — Wikipedia](https://en.wikipedia.org/wiki/Brushing_and_linking)
33. [Coordinated Multiple Views — State of the Art (ResearchGate)](https://www.researchgate.net/publication/4259731_State_of_the_Art_Coordinated_Multiple_Views_in_Exploratory_Visualization)
34. [Observable — Linked Brushing Tutorial](https://observablehq.com/blog/linked-brushing)
35. [Quantitative Intertextuality Survey (arXiv 2025)](https://arxiv.org/abs/2510.27045)
36. [A Flexible Model for Collaborative Annotation of Digitized Literary Works (DH2012)](https://www-archiv.fdm.uni-hamburg.de/dh2012/conference/programme/abstracts/a-flexible-model-for-the-collaborative-annotation-of-digitized-literary-works.1.html)
37. [VIANA: Visual Interactive Annotation of Argumentation (arXiv)](https://arxiv.org/pdf/1907.12413)
38. [Hypothesis — Social Annotation Platform](https://web.hypothes.is/)
39. [Chord Diagram — Wikipedia](https://en.wikipedia.org/wiki/Chord_diagram_(information_visualization))
40. [Genome Maps (NAR 2013)](https://academic.oup.com/nar/article/41/W1/W41/1113984)

---

## Uncertainties

- **Intertextor software availability:** The Intertextor project's annotation interface and visualization tools are not yet publicly released (GitHub organization shows "TODO" for software development). The four-zoom-level design and ontology are documented, but no running implementation can be studied or reused.
- **Apollo 3 stability:** Apollo 3 is in public beta as of December 2024. Its collaborative architecture is well-documented but the API surface for custom view types (e.g., integrating a non-genomic text view) has not been publicly evaluated.
- **Scale of "The Correspondent":** The chord diagram recommendations assume O(10–100) distinct referenced books. If the book references catalog extends to thousands of works, the chord diagram becomes unreadable and a network graph (force-directed, with clustering by genre/period) becomes the more appropriate primary overview visualization.
- **Character encoding of text positions:** W3C TextPositionSelector uses Unicode character offsets. If the primary text has multiple versions or transcriptions, position anchors can drift. TEI-XML fragment selectors (XPath-based) are more version-stable but require an XML source text, which may or may not be available for "The Correspondent."

---

## Related Topics for Future Research

- **TEI-XML as the canonical text encoding:** TEI provides hierarchical markup for letters, dates, persons, places, and bibliographic references natively — worth investigating whether "The Correspondent" can be encoded in TEI, which would provide a richer coordinate system than raw character offsets.
- **IIIF (International Image Interoperability Framework):** If the platform eventually incorporates manuscript images (facsimile pages alongside transcriptions), IIIF provides the same multi-layer annotation standard for images that W3C WebAnnotation provides for text.
- **spaCy / Stanza for automated annotation bootstrap:** NLP pipelines could automatically identify candidate book references (named entity recognition for title + author), pre-populating annotations for human review — reducing the manual annotation burden for the "book references" layer.
- **Gephi or Sigma.js for the large-scale network view:** For corpus-level intertextual networks (all books in a library, not just one novel), force-directed graph layouts with Louvain community detection for genre clustering offer a scalable alternative to chord diagrams.
- **Label Studio's annotation schema system:** Worth evaluating whether Label Studio's XML-based labeling configuration is expressive enough to define the per-text annotation schemas Palimpsest needs, potentially removing the need to build a custom schema editor.

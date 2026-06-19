# Swinehart Deep Analysis: Design Principles, Theoretical Underpinnings, and Implications for Palimpsest

**Date**: 2026-06-08
**Audience**: Adversarial review by Prof. Blackwood (literary rigor) and Dr. Patel (visualization principles)
**Corpus position**: This document presupposes familiarity with reports 03, 04, 06, and 11. It does not repeat bibliographic summaries but synthesizes them into argument.

---

## Preface: Why Swinehart Matters

Christian Swinehart (Samizdat Drafting Co.) is not a researcher in the conventional sense: he holds no literary studies appointment, publishes in no peer-reviewed venue, and accumulates no citation metrics. He is a computational neuroscientist turned graphic designer whose two major literary visualization projects — "One Book, Many Readings" (CYOA, 2009/2022) and "Infinite Digest" (Infinite Jest companion, 2021–ongoing) — are nonetheless the most consequential prior art for the Palimpsest project. The reason is not methodological novelty in the academic sense but something rarer: aesthetic wisdom. Swinehart has solved a problem that many papers in the adjacent research literature have not — how to make computational literary analysis feel like an encounter with literature rather than an escape from it.

This document unpacks that wisdom, situates it within the formal frameworks the research community has developed, and uses the result to sharpen Palimpsest's design priorities.

---

## 1. Swinehart's Design Principles

### 1.1 The Finite State Machine as Reading Model

The foundational methodological move in "One Book, Many Readings" is to treat a branching gamebook as a **finite automaton**: pages are states, reader choices are transition functions, and the book's structure is the graph induced by the transition relation. This is not merely a metaphor. Swinehart's implementation enumerates every unique path through each CYOA volume computationally — a graph traversal that reveals the complete topology of the decision space rather than any single reading's experience of it.

The formal result is striking. The CYOA graph is not a uniform branching tree; it is a directed acyclic multigraph with dramatically varying connectivity. Some nodes are unreachable from any starting state (the *Inside UFO 54-40* "ideal ending," reachable only by violating the book's instructions). Others are hyper-connected hubs where most paths converge before diverging again. The structural evolution Swinehart documents — creeping linearity across editions, the shift from dense branching to long linear runs with occasional choices — is empirically visible only because the full graph is available for comparison, not any single reader's path.

For Palimpsest, the principle here is: **the reading as experienced and the reading as structured are different objects, and both are analytically legitimate.** A single reader's path through *Infinite Jest* (or any non-linear novel) is phenomenologically real but structurally incomplete. The platform must represent both simultaneously.

### 1.2 Multi-View Architecture from a Single Dataset

Both Swinehart projects demonstrate an architectural commitment that is easily overlooked because the outputs look like discrete artifacts: **all views are derived reads of a single underlying dataset.** The CYOA project generates page grids, stacked bar charts, arc diagrams, and force-directed network layouts from the same page-type classification and adjacency list. The Infinite Digest project generates the endnote arc, the Plotlines chronological view, and (in planned 2026 additions) character arc trajectories and social networks from the same CSVs: `chapters.csv`, `plotlines.csv`, `endnotes.csv`, `bios.csv`.

This is not merely a code architecture preference. It reflects a theoretical commitment: the text has one structure, which multiple visual encodings reveal differently. No single view is complete; the views are coordinated facets of the same underlying formal object.

The data model underlying the Infinite Digest is worth specifying precisely. The `chapters.csv` schema includes both `pos` (narrative position, i.e., the page order in which Wallace presents scenes) and `seq` (chronological sequence, i.e., the diegetic year/month ordering). This `pos ↔ seq` mapping is the fabula/syuzhet distinction formalized as a coordinate transformation — the same data field viewed from two reference frames. The `plotlines.csv` uses XML-like inline character tags (`<name>text</>`) to annotate which characters appear in each chronological event capsule, enabling both character-filtered reading and corpus-level character network construction. The `endnotes.csv` encodes each of the 388 references with reference page, note page range, and note length — sufficient to reconstruct the "All Those Footnotes" visualization in its entirety from first principles.

### 1.3 Visual Encoding Choices: What Swinehart Selects and Why

Examining Swinehart's specific encoding choices reveals a consistent aesthetic logic:

**Arc diagrams for cross-reference:** The "All Those Footnotes" visualization places the novel's 979 pages on an upper semicircular arc and the 97 endnote pages on a lower arc. Each endnote is rendered as a "wiggly" curved line bridging the two arcs, with line width proportional to note length and curvature encoding proximity. This is a design choice that honors the **phenomenological experience of reading endnotes** — the physical gesture of flipping from page to endnote and back, which the dual-arc structure makes viscerally spatial. A standard heatmap or chord diagram would be analytically equivalent but experientially alien to a reader who has held the book.

**Color spectrum for ending quality:** The CYOA ending classification (red = catastrophic, blue = ideal) is not arbitrary. It maps onto a pre-existing cultural encoding of temperature and affect (cold = calm/good, hot = dangerous/bad in American color semiotics) that readers bring to the visualization without being told. This is an instance of what Bertin calls "retinal variables" being selected for their pre-attentive alignment with the data's semantic content.

**Force-directed layout for CYOA decision graphs:** The Barnes-Hut simulation used for the CYOA network layouts is not chosen for algorithmic elegance but because force-directed graphs preserve the reader's spatial intuition about density. Dense regions of a CYOA book (many pages, many connections) cluster visually; sparse "dead end" branches push to the periphery. The visual weight distribution corresponds to the reader's felt sense of the narrative's complexity.

**Scroll-driven interaction in Infinite Digest:** The SvelteKit + scroll-driven interaction architecture for the Plotlines view is significant because it synchronizes the **temporal axis of reading** (scrolling down) with the **temporal axis of the narrative** (chronological episode sequence). Reading and navigating merge. This is a phenomenological choice: the reader is not using a visualization to understand a text they remember; they are experiencing the text's temporal structure in a new medium simultaneously.

### 1.4 Phenomenological Fidelity as a Design Criterion

The unifying principle across all of Swinehart's design choices is what the deep-read report (06-deep-read-visualization.md) calls "phenomological fidelity": visual design that honors the reader's experience of the text rather than abstracting it into pure graph-theoretic structure. The endnote arc makes the *physical act* of consulting an endnote visible. The color spectrum on CYOA endings maps onto the *emotional valence* a reader feels upon reaching them. The scroll-driven chronology synchronizes with the *act of reading*.

This is not a merely aesthetic preference. It is a claim about the epistemological purpose of literary visualization. If a visualization of *Infinite Jest* can only be understood by someone who has never read it — because it has been abstracted so far from the text's surface that no residue of the reading experience remains — it has failed as a literary artifact. It may succeed as a graph-theoretic one. Swinehart's work consistently chooses the former over the latter when they conflict.

---

## 2. The Conceptual Underpinnings

### 2.1 Bertin's Semiology and Swinehart's Visual Grammar

Jacques Bertin's *Sémiologie Graphique* (1967) — the foundational text of information visualization — identifies seven **visual variables** or "retinal variables" that encode data: position, size, shape, value (lightness), color hue, orientation, and texture. Each variable has specific properties: some are selective (allow identification of elements sharing the same value), some are associative (allow grouping), some are ordered (allow ranking), and some are quantitative (allow ratio estimation).

Swinehart's visual grammar uses these variables with disciplined precision:

- **Position**: Page number on the arc (CYOA and IJ both) encodes narrative position — the most powerful quantitative variable, appropriate for the most important axis.
- **Size** (line width): Note length in "All Those Footnotes." Size is ordered and associative — it allows ranking (longer notes are more prominent) without encoding an arbitrary categorical distinction.
- **Color value** (lightness within a hue): Not directly used, but the red-to-blue ending spectrum in CYOA is a hue × lightness joint encoding of a unidimensional quality score. This overloads two retinal variables on one dimension, which is technically redundant but perceptually powerful because both channels reinforce the same ordering.
- **Shape**: Node shape distinctions in the CYOA graphs (branching vs. story vs. ending pages) carry the categorical page-type classification. Shape is associative but not ordered — it groups without implying rank, appropriate for a nominal typology.
- **Orientation**: Used implicitly in the directional arc curvature of the endnote visualization — lines arcing "inward" versus "outward" encode the relative position of the endnote relative to the reference.

What Swinehart does not do is also instructive: he avoids **texture** (which is weak at small scales and loses meaning under zoom) and never uses **color hue** for ordered quantitative data (a common error in scientific visualization). His restraint reflects internalized Bertin-level discipline even where the formalism is not cited.

### 2.2 Tufte's Data-Ink Ratio

Edward Tufte's foundational criterion — the data-ink ratio, the proportion of a graphic's ink devoted to irreducible data representation — maps cleanly onto Swinehart's aesthetic. The CYOA page grids have no chartjunk: no drop shadows, no decorative borders, no legends rendered larger than necessary. The arc diagrams use line width as a data channel rather than an aesthetic flourish. The force-directed layouts suppress redundant node labels except on hover.

Tufte's secondary principle — information density, measured in data per unit area — is where Swinehart makes the most interesting choices. The "All Those Footnotes" visualization is extremely information-dense: 388 data points (endnotes) × 3 channels (reference page, note extent, note length) in a single image. But it reads as simple rather than cluttered because the visual encoding uses continuous position (arc location) for what is in fact a nearly continuous variable (page number), and reserves categorical channels (none, in this design) for what would be noisiest.

Tufte's warning against "chartjunk" is relevant to a risk Palimpsest faces that Swinehart does not: the platform will generate visualizations programmatically, at which point no human designer is available to exercise aesthetic judgment. The constraint must be built into the visualization pipeline — sensible defaults for data-ink ratio, suppression of low-salience elements below a threshold, progressive disclosure of detail only when user-initiated.

### 2.3 Munzner's What-Why-How Framework

Tamara Munzner's visualization analysis framework (*Visualization Analysis and Design*, 2014) — decomposing any visualization task into **What** (data type), **Why** (task/action), and **How** (encoding and interaction idiom) — provides a useful taxonomy for dissecting Swinehart's designs:

**CYOA Network Views:**
- **What**: Network data (nodes = pages, edges = directed choices, node attributes = page type and ending quality).
- **Why**: Present overview of network topology; identify (locate) anomalies (unreachable nodes, high-degree hubs); compare structural properties across books.
- **How**: Force-directed layout (reveals clustering), node color-by-type (categorical shape variable), node size-by-degree (quantitative size variable), arc diagram as alternative encoding for linear sequence structure.

**Infinite Digest "All Those Footnotes":**
- **What**: Bipartite network (novel pages and endnote pages as two node sets, references as edges, note length as edge attribute).
- **Why**: Present the cross-reference structure; reveal distribution patterns (where long notes cluster); summarize aggregate properties (total endnote burden per section).
- **How**: Dual-arc spatial encoding (position = narrative location), edge width = quantitative note length, edge curvature = reference proximity.

**Infinite Digest "Plotlines":**
- **What**: Temporal data with categorical grouping (episodes × character groups × chronological ordering).
- **Why**: Identify temporal distribution; compare episode density across character groups; discover chronological reordering patterns.
- **How**: Scroll-driven timeline, color-by-character-group, arc connectors between sequential events.

Munzner's framework reveals that Swinehart's choices are tightly matched between task and encoding. He does not, for example, use a force-directed layout for the "Plotlines" view, where the ordering constraint (chronological sequence) would be violated by a physics simulation that treats all edges equivalently. This task-encoding alignment is the source of the designs' clarity.

### 2.4 Genette's Narratological Categories

Gérard Genette's *Narrative Discourse* (1972/1980) provides the narratological vocabulary that makes Swinehart's structural findings precise. Genette's categories — **order** (the relationship between story chronology and narrative sequence), **duration** (story time versus narrative time), **frequency** (how often events are narrated relative to how often they occur), **mood** (narrative distance and focalization), and **voice** (who narrates) — can each be operationalized as a visualization dimension in Swinehart's framework:

**Order**: The `pos ↔ seq` mapping in `chapters.csv` is a direct operationalization of Genette's *anachrony* — the displacement of story events from their narrative position. The "Plotlines" view makes this visible by showing episodes in chronological (fabula) order with connectors indicating their narrative (syuzhet) adjacency. Kim et al. (2018) formalize this in "Story Curves: Visualizing the Narrative Structure of Nonlinear Narratives" (IEEE TVCG), directly extending the Genettian framework into a visualization design problem.

**Duration**: Note length in "All Those Footnotes" encodes what Genette calls *scene* (real-time narration), *summary* (compressed time), and *ellipsis* (time omitted). A 10,000-word endnote (Note 110) is a full scene embedded in a summary-dense chapter — the line width encoding makes this durational hierarchy visible.

**Frequency**: Wallace's habit of narrating a single event once in a summary and again in full scene (what Genette calls *singulative* vs. *iterative* narration) would be detectable via the Lubars et al. (2018) dynamic network approach, which analyzes both the authored and chronological orderings of the same character co-occurrences. Swinehart's planned "social networks across plotlines" will partially operationalize this.

**Voice**: The four character-group color encoding in "Plotlines" (using the bio classifications in `bios.csv`) implicitly tracks focalization — scenes following Hal, scenes following Don Gately, scenes in Québec, scenes in the tennis academy represent distinct focalizing voices whose temporal distribution the visualization reveals.

Genette's framework is the literary theoretical vocabulary that disambiguates what Swinehart's visualizations are *about*. Without it, the `pos ↔ seq` mapping is just two columns in a CSV. With it, it is an operationalization of anachrony — one of the fundamental dimensions of narrative structure.

### 2.5 The Genome Browser Paradigm

The genome browser — exemplified by IGV, UCSC Genome Browser, and most recently JBrowse 2 (Diesh et al., 2024) — provides the structural architectural model that Swinehart's multi-view approach approximates. The paradigm: a **linear coordinate axis** (chromosome/text position) with **multiple annotation tracks** in horizontal bands, supporting **zoom from overview to base-pair resolution** and **cross-document linking** via synteny ribbons.

Swinehart's page arc corresponds to the chromosome ideogram: a linear coordinate axis rendered spatially. His multiple visualization types (page grid, arc diagram, force-directed network, timeline) correspond to the genome browser's multiple tracks. His scroll-driven navigation approximates the genome browser's zoom-and-pan interaction. What he does *not* have — and what Palimpsest must build — is the formalized multi-track view with synchronized zooming, the ability to add and remove tracks programmatically, and the cross-document linking (synteny ribbons in genomics, alignment arcs in text analysis).

The Swinehart approach thus represents the manually crafted artisan version of what the genome browser paradigm enables at scale and with automation. The connection between these traditions is not coincidental: both are visualization problems about correspondence — between genomic regions, between narrative positions, between textual editions — and both solve it by establishing a shared coordinate system and overlaying multiple annotation channels.

---

## 3. Cross-Reference with the Research Corpus

### 3.1 Arc Diagrams → Hi-C Contact Maps

Swinehart's "All Those Footnotes" arc diagram (novel page arc + endnote page arc, curved lines connecting them) has a precise structural analog in Hi-C contact maps — genome-wide interaction matrices revealing which genomic loci are physically proximate in 3D nuclear space (Lieberman-Aiden et al., 2009, *Science*). In both cases, the data is a set of pairwise correspondences between positions on a (partially) ordered linear axis. In both cases, the visualization must display many such correspondences without overlap-induced illegibility.

The key difference: Hi-C contact maps use a 2D matrix heatmap (position × position, with color intensity encoding contact frequency), while Swinehart uses a 1D arc with curved connectors. For dense correspondence data (a genome with millions of significant contacts), the matrix is more information-efficient. For sparse correspondence data (388 endnotes across 979 pages), the arc diagram is more interpretable — individual links are trackable. This suggests that Palimpsest's cross-reference visualization should switch idioms based on density: arc diagram for sparse reference networks, heatmap/matrix for dense self-similarity. The Church and Helfman (1993) dotplot formalism provides exactly the matrix idiom for the dense case.

### 3.2 Branching Graphs → Gene Regulatory Networks

The CYOA directed graph (pages as nodes, choices as edges, traversal paths as execution traces) is structurally isomorphic to a gene regulatory network (genes as nodes, activation/repression relationships as edges, expression states as execution traces). Both are directed graphs over a discrete state space where the dynamics — the set of possible path trajectories — are the object of analysis, not any single trajectory.

The Barabási scale-free network framework (analyzed in 04-deep-read-genomics.md) is relevant here: Lubars et al. (2018) explicitly tested whether the *Infinite Jest* character network is scale-free and found that it is *not* — unlike real-world social networks and most biological regulatory networks, Wallace's character co-occurrence network follows a different degree distribution. This is a substantive literary finding: Wallace's construction is more deliberate and less power-law distributed than organic social formation. Swinehart's planned "social networks across plotlines" extension of Infinite Digest will visually confirm or extend this result.

### 3.3 Character Tracking → Coreference Chains

Swinehart's "Plotlines" character color-coding in `plotlines.csv` (using the `<name>text</>` inline tagging) is a manually produced coreference chain: a mapping from textual events to character identities that makes each event's character participation explicit. Bamman et al.'s BookNLP pipeline and the LitBank literary coreference dataset (Bamman, Lewke & Mansoor, LREC 2020) automate the construction of exactly this kind of chain. Swinehart's manually annotated data thus serves as a gold standard — a human-curated coreference layer — against which BookNLP's automatic extraction can be evaluated for this particular text.

The CHAPLIN character/place network extractor (Marazzato & Caroli, arXiv:1402.4259, 2014) and the Elson, Dames & McKeown (ACL 2010) dialogue-network approach both address the same extraction task from different angles: CHAPLIN via NER and co-occurrence windows, Elson via dialogue attribution. Swinehart's `bios.csv` (122 characters, group affiliations, biographical summaries) is the ontological layer that both automated systems would need but cannot fully produce without human curation — precisely what Palimpsest-X's entity registry mechanism is designed to support.

### 3.4 Endnote Visualization → Circos Ribbons

The structural logic of "All Those Footnotes" is identical to Circos ribbon diagrams (Krzywinski et al., *Genome Research*, 2009). A Circos diagram places genomic segments on a circular axis and draws ribbons between segments that share a relationship (translocations, homologies, syntenic blocks). Replace genomic segments with novel pages and endnote pages, replace syntenic ribbons with endnote reference links, and you have Swinehart's visualization expressed in the Circos idiom.

The technical difference — Swinehart uses a straight semicircular arc where Circos uses a full circle — has a motivated rationale: the novel's pages have a canonical left-to-right reading order that a full circle would obscure by bending the sequence back on itself. A semicircle preserves the linear reading order in the upper arc while creating visual space for the endnote pages in the lower arc. The NG-Circos implementation (Cui et al., 2020) would allow this configuration in a web-deployable JavaScript component.

### 3.5 Storyline Layouts → Tanahashi 2012, StoryRibbons 2025

Swinehart's "Plotlines" is an informal storyline visualization: characters as colored arcs, time as horizontal axis, connectors as interaction indicators. The formal literature on storyline visualization — from Tanahashi & Ma (IEEE TVCG 2012) through the ILP crossing minimization work (Dobler et al., arXiv:2409.02858, 2024) to Story Ribbons (Yeh et al., arXiv:2508.06772, 2025) — addresses the algorithmic problem that Swinehart solves manually: how to minimize crossing lines and maximize readability when many characters are active simultaneously.

Story Ribbons' two-loop LLM extraction pipeline (hallucination detection via exact string match + entity deduplication via cluster call) addresses exactly the data quality problem that makes Swinehart's manual approach necessary: the raw text does not contain structured character-presence data. Palimpsest's pipeline must solve this extraction problem at scale. For Infinite Jest specifically, where Swinehart's manually curated `plotlines.csv` exists as ground truth, Story Ribbons' approach could be validated against the human annotation — a direct quality assessment for the automated extraction.

### 3.6 Scroll-Driven Interaction → Focus+Context (Furnas 1986)

Swinehart's scroll-driven interaction design in Infinite Digest instantiates what Furnas (1986) formalized as **focus+context** display: a technique that shows a region of interest in full detail while simultaneously maintaining a reduced-detail context view. In Swinehart's implementation, scrolling down through the "Plotlines" view moves the focus position along the chronological timeline while the arc connectors provide context by linking to temporally displaced events — episodes that are adjacent in the fabula but distant in the syuzhet.

The NetworkNarratives "data tours" approach (Li et al., CHI 2023) extends focus+context from spatial to semantic navigation: guided tours highlight specific network subsets in sequence, with surrounding context always visible in background. For Palimpsest, the implication is that scroll-driven interaction is appropriate for linear narrative structures (where reading and exploring are temporally synchronized), while tour-based guided exploration is appropriate for network structures (where there is no canonical traversal order and users need scaffolding to identify entry points).

---

## 4. Transferable Principles for Palimpsest

### 4.1 Multi-Layer Visual Vocabulary

The most directly transferable architectural principle is the multi-view commitment: **one underlying structured dataset, multiple coordinated visualization types.** Swinehart's four view types (page grid, arc diagram, force-directed network, timeline) are not separately maintained data products — they are derived reads of the same data. Palimpsest must implement this at the platform level: all extracted features (entity tracks, sentiment trajectories, topic distributions, coreference chains, structural segmentation) stored in a normalized schema from which any visualization is derived without re-processing the text.

The practical implication is that view types are **plugins** over a shared data layer, not standalone analytical products. Adding a new visualization type does not require re-running the NLP pipeline; it requires writing a new rendering component that consumes the existing data layer's API. This is the JBrowse 2 architecture applied to literary texts: modular, extensible, with a stable data model at the core.

### 4.2 Cross-Reference as First-Class Data

Swinehart's most distinctive contribution to literary data modeling is treating cross-references — endnotes, character co-appearances, episode connections — as **graph edges in a first-class data structure**, not as annotations on a linear text. The `endnotes.csv` is not a list of footnotes; it is an edge list for a bipartite graph. The `plotlines.csv` inline character tags are not just textual markup; they are the raw data for a character-episode bipartite network.

Palimpsest must formalize this: every cross-reference discovered by the platform (intertextual allusions, character co-occurrences, thematic echoes, structural parallels) should be stored as a typed, attributed edge in a graph database layer. The visualization system then queries this graph layer rather than scanning annotations. This enables queries that are impossible on linear text: "which chapters share the highest proportion of named characters?", "which endnotes are referenced from more than one location?", "which passages are thematically most similar to this passage across all texts in the corpus?"

### 4.3 Phenomenological Fidelity as a Design Constraint

The lesson of Swinehart's arc diagrams is that the best literary visualizations preserve the reader's **spatial memory of the text**. A reader who has held *Infinite Jest* knows approximately where the long endnotes fall (middle of the novel, between pages 550-800), knows that the last chapter is not the last in chronological order, knows the physical weight distribution of the endnote pages relative to the novel pages. Swinehart's "All Those Footnotes" design uses the semi-arc layout to encode these spatial intuitions — the proportional length of arcs corresponds to the proportional page counts.

For Palimpsest, this suggests a design rule: **every abstract visualization must have a "return to text" affordance.** A node in a character network, when clicked, should open the relevant passage. A bar in a sentiment histogram should be linked to the text segment it represents. A ribbon in a cross-reference diagram should be clickable to navigate to the reference and its target simultaneously. The abstract and the textual must remain connected — not as a UX nicety but as a principled design commitment to phenomenological fidelity.

### 4.4 Progressive Disclosure and Semantic Zooming

The CYOA page grid (overview) → arc diagram (structural topology) → force-directed network (full graph detail) progression is an informal instance of **semantic zooming**: different levels of abstraction reveal different structural features, and the reader moves between them based on analytical need. At the highest zoom level, individual page labels and choice texts are legible. At the overview level, only structural patterns (clusters, outliers, linear runs) are visible.

Krautter's "scalable reading" framework (Krautter 2023 — *The Scales of Computational Literary Studies*, referenced in report 04 though not yet downloaded) formalizes this movement between close and distant reading as the core operation of computational literary studies. Palimpsest's UI must implement semantic zoom as a first-class interaction primitive: scroll to zoom, with each zoom level revealing a different abstraction of the same underlying data. The text view is the maximum zoom level (individual words and punctuation visible); the corpus overview is the minimum zoom level (texts as single nodes in an intertextual similarity graph).

### 4.5 SvelteKit/D3 as Reference Implementation

Swinehart's current stack — SvelteKit for the application framework, custom SVG/Canvas for rendering, D3 for force simulations and layout algorithms — is the right choice for Palimpsest's web platform for reasons that go beyond consistency with prior art:

- **SvelteKit's compile-time reactivity** produces small bundles and avoids the virtual-DOM overhead that makes React-based literary visualization tools sluggish at large text scales (hundreds of thousands of words, thousands of characters).
- **D3's layout primitives** (`d3-chord`, `d3-force`, `d3-arc`, `d3-hierarchy`) cover the core visualization types Palimpsest needs without requiring separate charting libraries.
- **SVG at the literary visualization scale** (single text, hundreds of characters, thousands of words) is performant. Canvas becomes necessary only at corpus scale (millions of comparison pairs), where WebGL acceleration is preferable anyway.
- **Scrollytelling patterns** (scroll-driven state changes) are natively supported in SvelteKit via `IntersectionObserver` and Svelte's reactive assignment model.

The gap between Swinehart's hand-crafted, single-text implementations and Palimpsest's multi-text, programmatically generated visualizations will require solving the layout quality problem that Swinehart solves manually: crossing minimization, label placement, density-based filtering. The ILP crossing minimization framework (Dobler et al., 2024) and the Liu et al. constrained barycenter heuristic are the appropriate algorithmic foundations.

---

## 5. What Palimpsest Goes Beyond

### 5.1 Computational Track Generation

Swinehart's data is entirely hand-curated. The `chapters.csv` pos/seq mapping reflects the interpretive labor of Stephen Burn's *Reader's Guide*, Greg Carlisle's *Elegant Complexity*, and Drew Cordes' chronological reordering project — thousands of hours of scholarly annotation compressed into a CSV. The `plotlines.csv` character tags were entered manually. The `bios.csv` biographical summaries were written by hand.

This is not a limitation of Swinehart's project, which was designed as a visualization artifact, not a pipeline. But it means the methodology does not scale. There are a finite number of *Infinite Jest* scholars willing to produce this level of annotation, and most texts will never receive it.

Palimpsest's fundamental contribution is automating this annotation layer. The BookNLP pipeline (Bamman et al., ACL 2014/2021) produces character entity extraction, coreference resolution, dialogue attribution, and supersense tagging automatically for any English-language literary text. The Reagan et al. (2016) sentiment arc approach (sliding-window hedonometer) produces emotional arc extraction across any text. The Boyd et al. (2020) *Science Advances* framework produces staging/plot-progression/cognitive-tension decomposition. Story Ribbons' LLM extraction pipeline produces scene-character-location triples with 85% accuracy (97% for drama) — sufficient for exploratory analysis, with human correction available for precision-critical scholarship.

The GNAT narrative alignment tool (Pial & Skiena, EMNLP 2023) goes beyond anything in Swinehart's toolkit: applying Smith-Waterman local alignment directly to narrative text, with Gumbel distribution significance testing, enables discovery of structurally similar passages across distinct texts — the core alignment operation that defines Palimpsest's research identity and has no analog in Swinehart's single-text visualization approach.

### 5.2 Alignment as a First-Class Operation

Swinehart's visualizations are fundamentally **single-text analyses**: the CYOA books are treated independently (structural comparisons are made by juxtaposing separate visualizations, not by formally aligning the books), and Infinite Digest is entirely focused on *Infinite Jest* as an isolated object. Cross-reference within the novel is modeled; cross-reference between the novel and other texts is outside scope.

Palimpsest's core operation — **alignment** — is absent from Swinehart's toolkit. The formal apparatus assembled in the research corpus (Mäkinen et al. Ch. 6 for algorithmic foundations, GNAT for narrative alignment, SimDoc for topic sequence alignment, Church & Helfman for self-similarity dotplots, Foldseek as paradigmatic inspiration) enables precisely what Swinehart does not attempt: establishing formal correspondence between passages in different texts, versions of the same text, or temporal segments of the same text.

The alignment-first architecture means Palimpsest's coordinate system is inherently relational: a passage's position is defined not only by its location within its own text (the linear coordinate) but also by its position in alignment space (which passages in other texts it corresponds to, how strongly, and via what scoring function). This is the genomics paradigm made explicit: just as a genomic coordinate gains meaning from its syntenic relationship to homologous regions in other genomes, a textual coordinate gains meaning from its alignment relationships to corresponding passages elsewhere.

### 5.3 The Base/X Adaptive Architecture

Swinehart produces a custom visualization for each text: the CYOA analysis required writing graph traversal algorithms specific to the gamebook format; the Infinite Digest required parsing the Carlisle/Burn/Cordes annotations specific to *Infinite Jest*. There is no generalization mechanism — the CYOA code does not run on Infinite Jest and vice versa.

The Palimpsest Base/X architecture (formalized in 11-palimpsest-vision-synthesis.md) resolves this through two-tier design: **Base** provides universal tracks computed automatically on any text (segmentation, NER, sentiment, topic modeling, coreference, self-similarity, narrative arc, structural mode), while **Palimpsest-X** allows per-text adaptive extensions that emerge from the interaction between human reader and AI assistant. The Base tracks are the universal feature vectors; the X extensions are the text-specific domain knowledge.

Swinehart's *Infinite Jest* work, translated into the Base/X framework, would be: the `pos ↔ seq` coordinate transformation as an X custom coordinate system, the `bios.csv` character registry as an X entity ontology, the endnote arc as an X custom visualization component, and the plotline character tags as X coreference corrections atop the Base BookNLP extraction. The Swinehart curation becomes not a one-off artifact but a reusable X configuration that Palimpsest can apply to other non-linear novels and extend as the research evolves.

### 5.4 Scale: Corpus-Level, Not Single-Text

Both Swinehart projects are maximally deep on a minimal number of texts (twelve CYOA books; one novel). This is the appropriate scope for a visualization project whose goal is insight about specific texts. It is the wrong scope for a research platform whose goal is pattern discovery across literary traditions.

The research corpus assembled for Palimpsest — including Moretti's distant reading methodology (*Distant Reading*, 2013), Underwood's 300-year corpus analysis (*Distant Horizons*, 2019), Reagan et al.'s 1,327-text emotional arc corpus, and the alignment framework borrowed from genome-scale algorithm design (Mäkinen et al.) — is oriented toward corpus-scale analysis that no single-text visualization approach can support.

At corpus scale, the individual text recedes and the distributional patterns emerge: what is the distribution of narrative order displacement (the `pos ↔ seq` difference) across modernist novels as a genre? Do high-endnote texts share structural properties? How does the character network topology of CYOA books differ from linear novels across the genre's history? These are questions that Swinehart's approach cannot address because they require formal comparison across texts — exactly the alignment operation that defines Palimpsest.

The text recurrence network approach (Amancio et al., arXiv:2201.06665, 2022) — computing TF-IDF cosine similarity between all paragraph pairs within a text to construct a recurrence network — is directly scalable to cross-text comparison: replacing within-text paragraph pairs with cross-text passage pairs produces an intertextual similarity network. Palimpsest's self-similarity track (Base layer) becomes an inter-textual similarity track (corpus layer) by changing the comparison domain.

### 5.5 The Genomic Analogy as Organizing Principle

The deepest extension beyond Swinehart is conceptual. Swinehart's work is organized around the **narrative structure of a single text** as the primary unit of analysis. The genomic analogy — texts as genomes, passages as genes, narrative structures as regulatory circuits, intertextual relationships as syntenic homology — reconfigures the unit of analysis from the text to the **tradition**.

This is not purely metaphorical. The algorithmic apparatus of genome analysis (whole-genome alignment, syntenic block detection, phylogenetic reconstruction, structural alphabet encoding via Foldseek's paradigm) maps onto literary analysis with formal precision: edition comparison as sequence alignment, textual transmission as phylogenetic reconstruction, generic conventions as syntenic conserved elements, intertextual allusion as horizontal gene transfer. The Foldseek insight — encoding 3D protein structure as a 1D sequence of discrete structural states, enabling fast structural search — directly motivates Palimpsest's narrative alphabet concept: encoding paragraph-level narrative structure as a discrete symbolic sequence, enabling fast structural search across a corpus.

Swinehart's work establishes that structural visualization of literary texts is feasible, compelling, and analytically productive. The genomic analogy establishes that it is also principled — that the operations Palimpsest performs on texts are formally analogous to operations that the bioinformatics community has spent fifty years optimizing, validating, and scaling. Palimpsest is not borrowing a metaphor from genomics; it is importing an intellectual infrastructure.

---

## 6. Implications for Palimpsest's Research Identity

The foregoing analysis positions Swinehart as both foundation and limit. He demonstrates the aesthetic ceiling that literary visualization can achieve when a skilled designer applies principled choices to rich, manually curated data on a single text. He does not demonstrate (and does not attempt) what happens at scale, across texts, or with computational rather than human annotation.

Palimpsest's research identity is defined by the gap between what Swinehart achieves manually and what the platform can achieve computationally — at Swinehart's aesthetic quality, across an arbitrary text, automatically. That gap is wide. Closing it requires:

1. Automated extraction at BookNLP/Story Ribbons quality, with human correction loops for precision scholarship.
2. Alignment algorithms (GNAT, Smith-Waterman over narrative feature vectors) that Swinehart has no analogue for.
3. Layout algorithms (ILP crossing minimization, Louvain community detection, Circos chord diagrams) that replace the designer's manual choices with principled optimization.
4. A platform architecture (Base/X, multi-track, semantic zoom) that generalizes across texts rather than being hand-crafted per text.
5. The genomic organizing principle that elevates literary pattern discovery from an empirical observation to a theoretically grounded research program.

Swinehart's work is the benchmark. Palimpsest's goal is to surpass it at scale without sacrificing the phenomenological fidelity that makes the benchmark worth surpassing.

---

## Key References

*(Citation shorthand; full entries in master-bibliography.md)*

- Bamman et al. (ACL 2014/2021) — BookNLP pipeline
- Bamman, Lewke & Mansoor (LREC 2020) — Literary coreference dataset
- Bertin, J. (1967) — *Sémiologie Graphique*
- Boyd, Blackburn & Pennebaker (*Science Advances*, 2020) — Three-arc narrative model
- Burn, S. (2012) — *David Foster Wallace's Infinite Jest: A Reader's Guide*
- Carlisle, G. (2007) — *Elegant Complexity*
- Church & Helfman (1993) — Dotplot visualization of text
- Cordes, D. (v1.3) — IJ Chronological Reading Guide
- Dobler et al. (arXiv:2409.02858, 2024) — ILP crossing minimization for storylines
- Elson, Dames & McKeown (ACL 2010) — Social networks from literary fiction
- Furnas, G. (1986) — Generalized fisheye views (focus+context)
- Genette, G. (1972/1980) — *Narrative Discourse*
- Kim et al. (IEEE TVCG 2018) — Story Curves: nonlinear narratives
- Krautter (2023) — Scales of computational literary studies
- Krzywinski et al. (*Genome Research*, 2009) — Circos
- Li et al. (CHI 2023) — NetworkNarratives data tours
- Lieberman-Aiden et al. (*Science*, 2009) — Hi-C contact maps
- Lubars et al. (2018) — *Infinite Jest* dynamic character network
- Mäkinen et al. — *Genome-Scale Algorithm Design* Ch. 6
- Marazzato & Caroli (arXiv:1402.4259, 2014) — CHAPLIN
- Moretti, F. (2011) — "Network Theory, Plot Analysis"
- Munzner, T. (2014) — *Visualization Analysis and Design*
- Pial & Skiena (EMNLP 2023) — GNAT narrative alignment
- Reagan et al. (2016) — Emotional arcs of stories
- Swinehart, C. (samizdat.co/cyoa, 2009/2022) — One Book, Many Readings
- Swinehart, C. (samizdat.co/digest, 2021–) — Infinite Digest
- Tanahashi & Ma (IEEE TVCG 2012) — Storyline visualization design
- Tufte, E. (1983) — *The Visual Display of Quantitative Information*
- Yeh et al. (arXiv:2508.06772, 2025) — Story Ribbons

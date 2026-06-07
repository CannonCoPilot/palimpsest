# Deep Reading: Visualization Papers — Palimpsest Relevance Analysis

**Generated**: 2026-06-06

---

# Visualization Research Analysis for Palimpsest

**Date**: 2026-06-06
**Scope**: 4 academic papers, 1 EPUB, 1 practitioner book, 1 research report

---

## 1. StoryRibbons: Reimagining Storyline Visualizations with LLMs (arXiv:2508.06772)

**Authors**: Yeh, Menon, Arya, He, Weigel, Viégas, Wattenberg (Harvard / Google) — IEEE TVCG 2025

### Core concept
Story Ribbons extends the classic storyline paradigm (character lines over a time axis) by replacing hand-curated data pipelines with an LLM extraction chain, and extends the vertical axis from a simple grouping dimension to carry a second semantic variable — location by default, but configurable. Each character becomes a ribbon that moves through space (Y) and time (X) simultaneously.

### Palimpsest relevance
The paper directly confronts the central bottleneck that Palimpsest will face: transforming raw prose into structured narrative data. The system's four-step decomposition pipeline (chapter split → scene split with location anchoring → scene-level metadata extraction → aggregation) is a reusable architecture pattern applicable to any novel-length text. The user study finding that participants wanted to add their own visualization dimensions on demand ("what if I track dialogue vs. action?") is a direct argument for Palimpsest's UI needing a user-defined-dimension affordance, not a fixed set of views.

The paper's most important design decision: scenes are defined by changes in **location**, not by arbitrary LLM discretion. This anchors the segmentation to something both computable and meaningful for readers, and it maps cleanly onto the kind of structural markup Palimpsest would want to surface (where is each scene set?).

### Technical detail
The data pipeline produces a single JSON blob per work containing: chapters → scenes → characters with per-scene sentiment/emotion/quote → location per scene → pairwise interaction summaries. The pipeline runs LLM correction loops to address two specific failure modes: (1) hallucinated quotes are detected by exact string match against source text and replaced with paraphrase; (2) duplicate entity names (Jane / Jane Bennet / Miss Bennet) are resolved by a second LLM call doing group clustering. Quote extraction accuracy was 85% for novels, 97% for plays. This two-loop correction architecture is the directly reusable piece: exact-match hallucination detection + entity deduplication as a post-processing pass.

For the ribbon layout itself, the system assigns each character a unique color, plots X as chapter index, and uses a configurable Y-axis variable. Interaction events are rendered as vertical convergences of ribbons. Chapter titles are color-coded by sentiment (red = positive, blue = negative in their convention, though the sign direction is counterintuitive and worth inverting for Palimpsest).

### Key design insight
**Literary analysis has no ground truth — the visualization must support multiple valid interpretations rather than asserting a single reading.** The scholars consulted emphasized that asking whether the LLM "got it right" is the wrong question; the question is whether the visualization reveals patterns the scholar had not consciously noticed. This reframes Palimpsest's quality metric away from NLP accuracy and toward "does this prompt a new question?"

### Development implication
Implement a scene-segmentation pipeline using location changes as the primary signal, with LLM assistance for novels lacking explicit chapter structure. Build in a user-extensible "dimensions" panel so analysts can request ad-hoc ribbon overlays (e.g., "track scenes where character X is physically absent" or "highlight chapters above 0.7 conflict score"). Store extracted data as a normalized JSON schema per text — all views are derived reads of this single source.

---

## 2. Network Visualization Techniques for Story Charting (arXiv:2406.14734)

**Authors**: Aparicio, Karatsolis, Costa (MIT / ISEG Lisbon) — CISTI 2023

### Core concept
A short applied paper demonstrating a complete pipeline from raw text (a book-length Portuguese non-fiction account) to character co-occurrence network, using BERT-based NER, Louvain community detection, betweenness centrality, and PCA/correspondence analysis to reveal structural communities invisible in word-frequency analysis alone.

### Palimpsest relevance
This is the most practical implementation paper in the set — it documents what a minimal viable text-to-network pipeline looks like end-to-end, with no omissions. The key finding directly applicable to Palimpsest is that node frequency (raw mention count) and betweenness centrality measure different and complementary things: a character may be mentioned constantly but be structurally peripheral, while another may appear rarely but serve as the only bridge between two character communities. Palimpsest should display both metrics and make their divergence visible, since that divergence often encodes literary significance (Moretti's Horatio observation, confirmed here independently).

The three-community result from Louvain on a political memoir was reached without specifying the number of communities in advance — modularity optimization produced the number organically. This is the right default for literary character networks, where the analyst should not have to pre-specify how many factions exist.

### Technical detail
Pipeline: BERT-CRF NER (Portuguese) → proper noun extraction → phasic co-occurrence scoring (entities co-occurring within a sliding window) → NetworkX graph → Louvain community detection → betweenness centrality calculation → PCA with 3 factors explaining 84.2% of variance → 3-cluster correspondence analysis.

The word-evolution-over-time chart (plotting name frequency as a percentage of text across sequential segments) is a simple but powerful technique: it makes the sequential structure of a narrative legible without committing to any clustering, and reveals whether characters are introduced early, dominate the middle, or emerge late. This is essentially a character prominence timeline, implementable as a stacked area chart or horizon chart.

### Key design insight
**Network layout alone does not make character communities legible — you need to combine topology visualization with community coloring and centrality-as-node-size encoding simultaneously.** The paper shows that force-directed layout with no encoding beyond position is inadequate; the moment community color and betweenness-sized nodes are added, the three-faction structure becomes immediately readable to a naive viewer.

### Development implication
Implement a character network view with: node size = betweenness centrality, node color = community (Louvain), edge weight = co-occurrence count with a threshold slider to filter noise edges. Provide a parallel character prominence timeline (frequency over sequential text segments) as a linked companion view — clicking a node in the network highlights that character's frequency curve in the timeline, and vice versa.

---

## 3. NetworkNarratives: Data Tours for Visual Network Exploration (arXiv:2303.06456)

**Authors**: Li, Schöttler, Scott-Brown, Wang, Chen, Qu, Bach (HKUST / Edinburgh / MSR Asia / Fudan) — CHI 2023

### Core concept
NetworkNarratives introduces "data tours" as a design primitive for guided network exploration: a sequential slideshow of pre-computed network facts with textual annotations, where at each slide the analyst can either proceed linearly or pivot to a related goal-oriented sub-tour. Tours balance author-driven storytelling (the prescribed sequence) with reader-driven exploration (free interaction, detours on demand).

### Palimpsest relevance
This paper directly addresses the problem Palimpsest will face with non-expert users: a rich character network is overwhelming without a guided entry point. The data tour model translates to Palimpsest as a "reading guide" mode: instead of presenting the full network and expecting the reader to know what to look for, the system offers structured tours such as "who are the five most central characters?", "which characters only appear together?", "how does the network change across the three acts?" Each tour is a sequence of focused views with annotation, linked back to the text.

The CHI user study result is particularly relevant: with tours, novice analysts took significantly less time to find insights and reported lower cognitive load than free-form exploration, without sacrificing depth. For Palimpsest, this justifies investing in a curated "first run" tour experience rather than expecting users to construct their own queries from scratch.

### Technical detail
The system implements 10 tours covering: network overview, degree distribution, ego-network, temporal evolution, geographic layout, community exploration, subgraph comparison, path finding, link attribute analysis, and time-window filtering. Each tour slide consists of: (a) a fact statement in natural language, (b) a node-link diagram with the relevant elements highlighted, (c) a count badge showing how many remaining facts exist in this tour, and (d) detour entry points for pivoting to related tours.

The tour engine is a recommender that surfaces contextually relevant detours: if the current slide focuses on node X, the system offers an ego-network tour for X. This is a graph of slides where edges represent "natural next question" relationships — a lightweight implementation using a lookup table keyed on current fact type + current highlighted element type.

For Palimpsest, the critical rendering pattern is: **progressive disclosure with persistent context**. The network is always visible in the background; tours change which subset is highlighted and what annotation appears, rather than replacing the view entirely. The reader maintains spatial memory of the network while zooming in on specific facts.

### Key design insight
**The most effective guided exploration combines prescriptive sequencing with on-demand agency.** Tours that lock users into a linear path feel patronizing and miss serendipitous discoveries; tours that offer unlimited detours become indistinguishable from free-form exploration and lose the cognitive scaffolding benefit. The right balance is: a default linear path that the user can deviate from at any slide, with the system remembering where to return after a detour.

### Development implication
Build a "guided reading" mode for Palimpsest character networks with at minimum three tours: (1) Character Overview — who appears most, who is most structurally central; (2) Relationship Deep Dive — ego-network for a selected character with their direct connections highlighted and annotated; (3) Narrative Arc — network state at the beginning, middle, and end of the text, shown in three sequential panels. All tours should offer "read more in text" pivots that open the relevant passage in the raw text view.

---

## 4. Revisiting ILP Models for Exact Crossing Minimization in Storyline Drawings (arXiv:2409.02858)

**Authors**: Dobler, M. Jünger, P.J. Jünger, Meffert, Mutzel, Nöllenburg (TU Wien / Bonn) — arXiv 2024

### Core concept
A combinatorial algorithms paper establishing new exact and near-exact solvers for the NP-hard problem of minimizing line crossings in storyline drawings. Characters are modeled as x-monotone curves; interactions require character curves to be vertically consecutive at that time step; the task is to find the optimal permutation sequence over all time steps to minimize total crossings.

### Palimpsest relevance
This paper addresses the visual quality problem that determines whether storyline visualizations are legible or a tangled mess. The formal result is that the new ILP formulations solve previously intractable instances (Harry Potter film: from 374 crossings with a greedy heuristic to 236 with optimal — a 37% reduction) and run 2.6–3.2x faster than the prior state of the art. For Palimpsest, this matters because at typical novel scale (dozens of characters, hundreds of scenes), even greedy crossing minimization produces cluttered layouts, and the visual difference between a greedy solution and an optimal one is immediately apparent to a human reader.

The practical implication: Palimpsest should not implement storyline layout from scratch. The benchmark data and source code at osf.io/3bua2/ provide both reference implementations and test instances. The paper's recommended pipeline — use the new ILP for instances up to ~25 characters × ~80 interactions, fall back to the Liu et al. constrained barycenter heuristic for larger instances — is a directly adoptable strategy.

### Technical detail
The formal input is a 4-tuple (T, C, I, A) where T = time steps, C = characters, I = interactions (each interaction has a time step and a character subset that must appear consecutively), and A maps each character to its active time range. The output is a sequence of permutations of active characters at each time step, minimizing total inversions between consecutive permutations.

The key structural insight enabling speedup: **there always exists a crossing-minimum drawing where characters maintain their relative order within non-interacting groups between consecutive time steps** — this reduces the search space dramatically and enables symmetry-breaking constraints in the ILP. The practical heuristic for initialization: at each step, characters not participating in any interaction inherit their order from the previous step, and only interacting characters are re-sorted.

Three optimization objectives exist in the field: crossings (combinatorial, most important), wiggles (amount of vertical movement, affects readability), and white space (compactness). The pipeline proposed by Liu et al. 2013 — solve crossing minimization first, then minimize wiggles and white space while holding the permutation order fixed — is the standard architecture and the one Palimpsest should adopt.

For small scenes with few characters, the ILP from this paper is tractable within seconds. For Pride and Prejudice at full character count, a heuristic is needed; the referenced constrained barycenter algorithm from Liu et al. runs under one second and produces good (though not optimal) results.

### Key design insight
**Crossing minimization is the primary aesthetic quality metric for storyline visualizations, and the difference between optimal and heuristic solutions is visually significant.** A storyline with 37% more crossings is measurably harder to follow for human readers — this is not a marginal quality improvement but a readability threshold difference. Palimpsest should invest in an actual crossing-minimization step (even heuristic) rather than using naive left-to-right character ordering.

### Development implication
Use the Liu et al. 2013 constrained barycenter heuristic (implemented in multiple open-source tools; StoryFlow is the reference implementation) as the default storyline layout engine. For novels with fewer than 20 named characters, optionally attempt the ILP from osf.io/3bua2/. Expose a "character filter" control that lets users reduce the active character set (e.g., "show only characters appearing in more than 5 scenes") to bring complex novels within tractable layout ranges. Track wiggle count and crossing count as internal layout quality metrics, and surface them in a developer/debug panel.

---

## 5. Circos Data Visualization How-To — Tom Schenk Jr. (Packt, 2012)

### Core concept
A practitioner manual for Circos — Martin Krzywinski's Perl-based circular visualization tool originally designed for comparative genomics (chromosome ring diagrams with ribbon links encoding relationships between genomic regions). Schenk's contribution is demonstrating that the circular paradigm applies broadly to relational social-science data: political contribution flows, workforce transitions, any directed relationship between categories arranged on a circle.

### Palimpsest relevance
Circos introduces a visualization paradigm that would be genuinely novel for literary analysis: arranging narrative elements (chapters, locations, character groups) on a circular axis with ribbon links encoding relationships between them. For Palimpsest, the most immediate application is an **intertextual reference map**: books on the outer ring, cross-references or thematic links as ribbons. A second application is the Swinehart-style endnote visualization — all novel pages arranged as an arc, with curved lines connecting each in-text citation to its endnote page, line width encoding note length. This is exactly what Circos was built for.

The key design vocabulary: segments on the ring represent categories, ribbons represent directed or undirected relationships between segments, ribbon width encodes quantity, ribbon color encodes category origin. Data tracks (heatmaps, histograms) can be placed in concentric rings outside the main segments, adding further data channels without consuming additional canvas space.

### Technical detail
Circos configuration is declarative (`.conf` files specifying segment sizes, ribbon data files, track specifications) rather than programmatic. The core data model for ribbons is a TSV: `segment1 start1 end1 segment2 start2 end2 value` — where value optionally controls ribbon width. Rules allow conditional formatting: ribbons above a threshold can be colored differently, thin ribbons can be suppressed to reduce clutter, bundlelinks tool can merge parallel ribbons between the same pair of segments.

For web use, direct Circos is impractical (Perl dependency, command-line only). The equivalent in D3.js is a chord diagram using `d3.chord()` + `d3.arc()` + `d3.ribbon()` — the data structure is an n×n matrix where cell (i,j) encodes the flow from group i to group j. The `d3-chord` module supports all the same visual variables as Circos (sorted segments, color-by-source, opacity-by-value) and runs client-side.

For Palimpsest specifically, a useful adaptation: arrange **chapters** on the ring, with ribbons connecting chapters whose character sets overlap significantly, ribbon width proportional to the number of shared characters. This immediately reveals act structure, parallel plots, and isolated narrative branches.

### Key design insight
**Circular layout resolves the comparison problem that plagues linear timeline views: every segment is equidistant from every other segment, making cross-cutting relationships visible without the directional bias of left-to-right reading order.** For texts with non-linear narrative structure (Infinite Jest, Ulysses, any novel where chapter order diverges from story chronology), a circular arrangement avoids falsely implying that proximity in the visualization means proximity in time.

### Development implication
Implement a chord/circular view in Palimpsest using D3's chord diagram, with chapters as segments and shared-character-count as the relationship matrix. This is best used as a "structural overview" view for texts with complex narrative topology. For the Infinite Jest use case specifically: model the 97 endnote pages as a second arc facing the 979 novel pages, recreating Swinehart's "All Those Footnotes" layout — this is a direct Circos application and would be a compelling demonstration feature.

---

## 6. Visualize This, 2nd Edition — Nathan Yau (Wiley, 2024)

*(Introduction + Chapter 1: "Telling Stories with Data")*

### Core concept
Yau's book frames data visualization as an evolving medium for storytelling rather than a purely analytical tool, and Chapter 1 establishes a philosophy grounded in the iterative process: ask questions of the data, let visualization surface patterns, ask better questions, repeat. The "more than numbers" framing insists that the best visualizations work because they make patterns visible that could not otherwise be seen — not because they present facts efficiently.

### Palimpsest relevance
Yau's design philosophy is directly applicable to Palimpsest's product philosophy. His core tension — "visualization was mostly an analysis tool when I started my studies but it has developed into a medium to tell stories with data. You can show just the facts, but you can also evoke emotion, entertain, and compel change" — maps exactly onto the question Palimpsest has to answer for its users: are they doing analysis (finding facts about the text) or are they having an experience (encountering the text's structure in a new way)?

The second edition's emphasis on communicating to an audience (not just to the analyst) is relevant to Palimpsest's export and sharing features. A visualization that reveals something about a novel to its creator but cannot be shared or explained to a reader who hasn't used the tool has limited literary-critical value.

### Technical detail
Chapter 1 is philosophical rather than technical, but the book's structure (Chapter 4: Visualizing Time; Chapter 5: Visualizing Categories; Chapter 6: Visualizing Relationships; Chapter 7: Visualizing Space; Chapter 8: Analyzing Data Visually) maps cleanly onto Palimpsest's view types. Yau's taxonomy of time visualizations distinguishes trends (continuous), events (discrete), and cycles (periodic) — for narrative texts: scene duration as trends, character appearances as events, recurring motif patterns as cycles. The "Categories and Time" section (in Ch. 5) is specifically relevant to character group tracking over narrative time, which is the core data type for storyline views.

Yau advocates strongly for the iterative process: "I follow an iterative process of answering questions with data, visualizing the answers, and then asking more questions. Repeat until there are no more questions." For Palimpsest, this argues against any design that presents a single "correct" view — the interface should encourage re-questioning, re-filtering, re-annotating.

### Key design insight
**The chart type must serve the question, not the data.** Yau's core teaching is that you start with a question ("how does this character's prominence change over time?") and then select the encoding that makes the answer visible, rather than choosing the most visually interesting encoding available and hoping the question emerges. For Palimpsest, this means: the question-first interface (user asks what they want to see, system selects or suggests the appropriate visualization type) is more aligned with good visualization practice than a dashboard of fixed views.

### Development implication
Build a question/intent layer into Palimpsest's UI. At minimum: offer a "what are you looking for?" selector with pre-defined intents (character presence over time, relationship strength, location patterns, structural overview) that routes to the appropriate view type. In more ambitious form: an LLM-powered query interface where users type a natural language question and the system selects view type, filters the character set, and configures encoding automatically — similar to Story Ribbons' "custom views on demand" feature (T3 in that paper's design tasks).

---

## 7. Swinehart Narrative Visualization Research Report

*(Internal research report, 2026-06-06)*

### Core concept
A survey of Christian Swinehart's "One Book, Many Readings" (CYOA structural analysis, 2009/2022) and "Infinite Digest" (Infinite Jest companion, 2021–ongoing), plus the supporting ecosystem of tools and academic precedents (Moretti, Lubars, Tanahashi). Swinehart's work represents the current state of the art in literary visualization that achieves both analytical rigor and aesthetic quality accessible to non-specialist audiences.

### Palimpsest relevance
Swinehart's work establishes the benchmark Palimpsest should aim to meet or exceed. Three specific techniques are directly importable:

1. **Dual-arc endnote visualization** (Infinite Digest "All Those Footnotes"): Upper arc = novel pages, lower arc = endnote pages, wiggly curved lines connecting them, line width = note length. Directly implementable in SVG/D3. Source data available at samizdat.co/digest/.

2. **Page classification taxonomy** (CYOA project): Pages categorized as branching, story, or ending; ending spectrum from catastrophic (red) to ideal (blue). For Palimpsest's use: scenes classified by narrative function (branching = plot choice points, story = linear narration, ending = resolution beats). This classification scheme is applicable to any branching or episodic structure.

3. **Multi-view architecture** (both projects): page grid + arc diagram + force-directed network + timeline, all derived from the same underlying dataset. The principle that a single structured dataset should drive multiple coordinated view types is the architectural pattern Palimpsest should adopt as its core.

The Lubars 2018 finding about Infinite Jest is a strong empirical result worth building on: Wallace's non-chronological sequencing produces a character network with **higher degree, shorter paths, and fewer disconnected components** than the same text in chronological order. This means the order in which an author presents scenes is not narratively neutral — it shapes the social network that emerges. Palimpsest could make this structural choice visible by offering both authored-order and chronological-order network views for the same text.

### Technical detail
Swinehart's current stack: SvelteKit, custom SVG/Canvas, scroll-driven interaction. This is the right choice for Palimpsest's web stack — Svelte's compile-time approach produces small bundles and the scroll-driven interaction model (Scrollytelling) is the dominant pattern for literary visualization, where reading and exploring happen at the same time.

Barnes-Hut simulation (used in the CYOA force-directed layouts) is available in D3 as `d3-force` with the `forceSimulation` engine — it handles the branch/tree structure of CYOA-style directed graphs efficiently.

For the Infinite Digest "Plotlines" view: SvelteKit + custom SVG with arcs connecting sequential events, color-coded by character group. The key rendering detail: arcs connect the center of each episode glyph, with arc height proportional to the temporal gap between connected episodes. This is implementable with D3's `d3.line()` with a basis or natural spline interpolator.

### Key design insight
**The most enduring literary visualizations combine structural data (which pages connect to which, who appears with whom) with visual encodings that honor the reader's phenomenological experience of the text.** Swinehart's work is effective not because it abstracts the text into pure graph theory, but because it preserves the reader's spatial memory of the book (where things happen, how long they are) while surfacing structural relationships that reading cannot reveal. Palimpsest should always maintain a connection between abstract visualizations and the underlying textual passages — "reveal + return to text" as a core interaction pattern.

### Development implication
Prioritize downloading Swinehart's public datasets (samizdat.co/digest/) as initial test data for Palimpsest development — the Infinite Jest data (characters, chapters, endnotes in CSV format) is a well-documented, non-trivial real-world literary dataset. Implement the dual-arc endnote view for any text that has footnotes or endnotes, as this is a distinctive, high-signal visualization type that general tools (Gephi, Tableau) cannot produce. Build the multi-view architecture from the start: store all extracted narrative data in a normalized schema and derive all views from it, so that adding a new view type does not require re-processing the text.

---

## Cross-Cutting Synthesis for Palimpsest

### View type inventory (from all sources combined)

| View type | Source | Primary data | Interaction |
|---|---|---|---|
| Storyline / ribbon chart | StoryRibbons, ILP paper | Characters × scenes with location Y-axis | Filter by character group, change Y dimension |
| Character co-occurrence network | Story Charting, Swinehart | Co-mention edges, betweenness centrality | Guided tours, ego-network drill-down |
| Dual-arc arc diagram | Swinehart "All Those Footnotes" | Cross-references, endnotes | Hover to expand, click to text |
| Chord/circular diagram | Circos | Chapter-to-chapter shared character matrix | Filter by threshold, re-sort segments |
| Character prominence timeline | Story Charting | Frequency over sequential text segments | Linked selection with network view |
| Guided data tours | NetworkNarratives | Pre-computed network facts | Sequential slideshow with detours |
| Authored vs. chronological network | Swinehart/Lubars | Same characters, two orderings | Toggle between orderings |
| Page/chapter classification grid | Swinehart CYOA | Page type, ending valence | Click to open passage |

### Shared architectural principles

1. One normalized JSON schema per text drives all views — no view-specific data pipelines.
2. All views link back to source text passage — "reveal + return to text" is always available.
3. Crossing minimization is non-optional for storyline views; use Liu et al. 2013 heuristic as default.
4. LLM pipeline for extraction requires correction loops for hallucinated quotes (exact-match detection) and duplicate entity resolution (second-pass LLM grouping).
5. Guided entry points (tours, intent selectors) are necessary for non-expert users; free-form exploration is necessary for expert users — the design must support both without privileging either.
6. Network node encoding: size = betweenness centrality, color = community (Louvain). Display both frequency and centrality since they measure different literary properties.

### Most urgent implementation priority

Build the LLM extraction pipeline with the four-step architecture from StoryRibbons (scene split by location change, metadata extraction, entity deduplication, JSON output) before building any views. All visualization work depends on structured data; without the pipeline, every view is a prototype against hand-curated test data.

Second priority: implement the NetworkNarratives guided tour pattern as the default entry experience. A character network presented cold to a first-time user will be abandoned within thirty seconds; a "take a tour of this novel's structure" button converts the same data into an onboarding experience.

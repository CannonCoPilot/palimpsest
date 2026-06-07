# Palimpsest Conceptual Framework: Alignment, Structure, and the Layers of Text

**Date**: 2026-06-06
**Status**: Working document — evolving with research

---

## 0. Orientation

This document reframes the Palimpsest project in terms of its deep conceptual and technical questions. Where the [alignment convergence thesis](00-alignment-convergence-thesis.md) mapped the *topology* of cross-domain connections, this document digs into the *substance* — what the concepts actually mean, what problems they create, and how they interact.

The questions fall into five clusters:

1. **What is structure?** And what does it mean to align using it?
2. **Functional layers**: How deep does textual structure go? What's the analogy to a genome's functional hierarchy?
3. **Discovery and leverage**: How do you find structure? How does known structure inform alignment?
4. **Computational machinery**: Identification, representation, matching, scoring, speed.
5. **Visualization and interaction**: What are visuals *for* — exploration or presentation?

---

## 1. What Is Structure?

### 1.1 Structure as Constraint on Alignment

In the formal alignment literature (Mäkinen et al., *Genome-Scale Algorithm Design*, Ch. 6), an alignment between two sequences A and B is an injective partial mapping from positions in A to positions in B that **respects an ordering constraint** and **maximizes a scoring function**. The ordering constraint *is* the structural assumption: in global sequence alignment (Needleman-Wunsch), the constraint is that matched positions must be collinear — if position i maps to position j, then position i+1 can only map to j' ≥ j+1.

This immediately raises the question: **is ACTG "a kind of structure"?**

The answer is no — ACTG is alphabet, not structure. The *structure* of DNA has several levels:

- **Primary**: the linear sequence (ACTGATCG...)
- **Secondary**: local base-pairing patterns (stems, loops, hairpins)
- **Tertiary**: 3D spatial folding (chromosomal architecture, chromatin loops)
- **Quaternary**: multi-molecule complexes (nucleosomes, chromosome territories)

The sequence ACTG is a *representation* that admits structural analysis at these levels. The structure is the **set of constraints that govern which parts relate to which other parts and how**. In DNA, structure is what makes the TATA box a promoter rather than just four letters — its position relative to a coding region, its binding affinity for transcription factors, its epigenetic state.

### 1.2 Alignment Without Structure

**Can you align without structure?** Yes — edit distance (Levenshtein) makes no structural assumptions at all. It treats every character as equivalent and computes the minimum number of insertions, deletions, and substitutions to transform one string into another. This is "alignment" in the weakest possible sense: pure sequence-to-sequence correspondence.

But structureless alignment is nearly useless for interesting texts. Computing the edit distance between two novels tells you almost nothing — the number will be enormous and uninformative. You need structure to make alignment meaningful, and the kind of structure you impose determines what kind of meaning you find:

| Structural assumption | What alignment reveals |
|---|---|
| Word-level collinearity | Character substitutions, typos, editorial changes (Eve's *Cloud Atlas* P vs E editions) |
| Sentence-level correspondence | Translation alignment, paraphrase detection |
| Paragraph-level topic threading | Thematic parallelism across documents |
| Chapter/section ordering | Structural reorganization, narrative resequencing |
| None (bag-of-words) | Topical similarity only — no positional correspondence |

### 1.3 Structure as What Alignment Discovers

Here's the deep recursion: **structure is both the input to and the output of alignment.**

In genomics, you align two genomes using the assumption that gene order is roughly conserved (synteny). The alignment then reveals where that assumption breaks — inversions, translocations, duplications. The *violations* of structural constraint are the interesting discoveries.

In text analysis, the same recursion operates:
- You assume two editions of a novel share the same narrative structure → alignment reveals the editorial differences (Eve's textual scholarship on *Cloud Atlas*)
- You assume two novels in the same genre share thematic structure → alignment reveals where they diverge (Underwood's genre modeling via predictive features)
- You assume a novel has a linear emotional trajectory → decomposition reveals the archetypal shapes (Reagan et al.'s 6 emotional arcs via SVD)
- You assume *no* structure → clustering or dimensionality reduction discovers whatever structure exists (topic modeling, as in Piper's *Enumerations*)

**The key insight**: alignment and structure are co-dependent. You need a structural hypothesis to make alignment tractable, and alignment reveals structure you didn't hypothesize. This is exactly how science works: model → measure → revise model → measure again.

### 1.4 Informing Alignment by Leveraging Prior Knowledge of Structure

This is Foldseek's breakthrough in the protein world. The traditional approach (TM-align, DALI) was: take two 3D structures, try all possible superpositions, minimize RMSD. This is an NP-hard search over rotation/translation space. Foldseek's insight: encode the 3D structure as a 1D sequence (the 3Di alphabet), then use fast sequence-alignment algorithms (Smith-Waterman, MMseqs2) on the encoded representation.

The prior knowledge that Foldseek leverages is: **local geometry between adjacent residues captures most of the structural information needed for fold comparison**. This compresses 3D structure into 20 discrete states — a structural alphabet.

For text: what prior knowledge about literary structure could we encode into a structural alphabet?

- **Narrative function**: exposition, rising action, climax, falling action, denouement (Freytag's pyramid)
- **Speech act type**: dialog, narration, description, interior monologue, reported speech
- **Information density**: high-entropy passages (dense exposition) vs. low-entropy (formulaic exchange)
- **Temporal mode**: past narration, present action, flashback, flash-forward, timeless generalization
- **Register/style**: formal, colloquial, archaic, technical, lyrical

Our pipeline's `narrative_encoder.py` is a first approximation of this — encoding 6 features into a 16-letter alphabet. But it's crude compared to what's possible.

---

## 2. Functional Layers of a "Textual Genome"

### 2.1 The Genomic Hierarchy

A genome has at least six functional layers, each with its own "grammar" and detection methods:

1. **Coding sequences** (genes): triplet codons → amino acids → proteins. Detected by: ORF finding, codon bias, homology search.
2. **Regulatory sequences**: promoters, enhancers, silencers, insulators. Detected by: motif search (JASPAR), ChIP-seq, conservation across species.
3. **Chromatin structure**: nucleosome positioning, histone modifications. Detected by: MNase-seq, ATAC-seq, ChIP-seq for histone marks.
4. **3D spatial organization**: TADs (topologically associating domains), chromosome territories, A/B compartments. Detected by: Hi-C, FISH.
5. **Epigenetic patterning**: DNA methylation, histone acetylation, chromatin remodeling. Detected by: bisulfite sequencing, methylation arrays.
6. **Non-coding RNA**: miRNA, lncRNA, regulatory RNA. Detected by: RNA-seq, structure prediction, target prediction.

### 2.2 The Textual Hierarchy (by analogy)

| Genomic layer | Textual analogue | Detection method |
|---|---|---|
| **Coding sequences** (protein-coding genes) | **Propositional content** — the "meanings" a text encodes | Named entity recognition, semantic role labeling, information extraction |
| **Regulatory sequences** (promoters, enhancers) | **Discourse markers and rhetorical cues** — words/phrases that control how content is interpreted ("however," "moreover," "in conclusion," chapter titles, section breaks) | RST parsing, discourse connective detection, cue phrase classification |
| **Chromatin / folding** | **Paragraph and section structure** — how content is physically grouped and how grouping affects interpretation (a sentence means different things depending on which paragraph it's in) | Structural segmentation, topic modeling at multiple granularities, text tiling |
| **Spatial proximity** (Hi-C, TADs) | **Cross-reference networks** — endnotes, footnotes, citations, allusions, intertextual references (Swinehart's Infinite Jest endnote visualization maps exactly this layer) | Reference parsing, allusion detection, citation graph extraction |
| **Epigenetic patterning** | **Style, register, and voice** — the "how it's said" layer that modulates meaning without changing propositional content. Irony, unreliable narration, free indirect discourse | Stylometry, register classification, irony detection, narrative voice analysis |
| **Non-coding RNA** (regulatory but non-protein-coding) | **Phonetic and prosodic structure** — rhyme, meter, alliteration, assonance. Does not carry propositional content but affects reception, memorability, aesthetic impact | Phonemic analysis, scansion, sound pattern detection |

### 2.3 Narrowly Construed Analogies (Direct Structural Correspondences)

These are cases where the analogy is tight — the same algorithm or data structure genuinely applies:

- **Rhyming and phoneme similarity ↔ Sequence homology**: Two words rhyme because their terminal phoneme sequences are identical or highly similar. This is literally sequence alignment on phonemic transcriptions. Tools: CMU Pronouncing Dictionary + edit distance on phoneme strings.
- **Shared root words / root languages ↔ Homologous genes from common ancestor**: English "paternal" and Spanish "paterno" derive from Latin "pater" just as human hemoglobin and chimp hemoglobin derive from an ancestral globin gene. Etymology *is* molecular phylogenetics for words. Tools: etymological databases + phylogenetic tree construction.
- **Syntactic pattern matching ↔ Motif search**: Noun-noun, adjective-noun, subject-verb-object patterns are analogous to transcription factor binding motifs (e.g., TATA box). You can search a corpus for syntactic motifs the same way you search a genome for regulatory motifs. Tools: dependency parsing + pattern matching (spaCy, Tregex).
- **Sentence/clause structure ↔ Gene structure**: Exons (coding) and introns (non-coding) within a gene mirror main clauses (propositional content) and subordinate/parenthetical clauses (modifying content). Alternative splicing → ambiguous sentence parses.

### 2.4 Broadly Construed Analogies (Structural Isomorphisms)

These are cases where the analogy is looser but still illuminating:

- **Thesis/support/caveat/conclusion ↔ Operon structure**: A bacterial operon has a promoter, operator, structural genes, and terminator — a self-contained functional unit with regulatory bookends. A well-formed argument paragraph has a similar architecture. Both are "functional units" with internal structure and regulatory boundaries.
- **Narrative arc ↔ Gene expression trajectory**: A gene's expression level over developmental time traces a characteristic curve (rising, peaking, declining). Reagan et al. showed that stories' emotional trajectories similarly cluster into 6 archetypal shapes. Both are time-series whose shape encodes function.
- **Intertextuality ↔ Horizontal gene transfer**: When one text quotes, alludes to, or structurally echoes another, it's the literary equivalent of horizontal gene transfer — material crossing lineage boundaries. Detecting intertextuality requires the same alignment sensitivity as detecting HGT (high sensitivity to short, divergent matches).
- **Genre ↔ Species**: Genres are statistical clusters in feature space, not hard categories — exactly like biological species under the biological species concept. Underwood's *Distant Horizons* Ch. 2 ("The Life Spans of Genres") shows genre boundaries are probabilistic, contested, and historical — just like species boundaries.

---

## 3. Discovery: Finding Structure-Objects

### 3.1 What is a "Structure-Object" in Text?

A structure-object is any identifiable, bounded unit of text that carries a functional role at some level of the hierarchy:

- **Character mention** (NER): "Elizabeth Bennet" → a named entity with attributes, relationships, narrative function
- **Dialog turn** (quotation + speaker): a speech act attributed to a character
- **Scene** (temporal/spatial coherence): a continuous episode in one time/place
- **Chapter/section**: a structural division imposed by the author
- **Narrative function segment**: exposition, complication, resolution (Propp's functions, Barthes' codes)
- **Topic region**: a span dominated by a particular topic (LDA/NMF)
- **Emotional beat**: a local extremum in sentiment trajectory
- **Rhetorical move**: a discourse unit with a communicative function (RST nucleus/satellite)

### 3.2 Identification Algorithms

| Structure-object | Best current approach | Limitations |
|---|---|---|
| Named entities | Transformer-based NER (spaCy, Flair, BookNLP) | Literary entities often novel — not in training data |
| Dialog + speaker | BookNLP (Bamman): quote detection + coreference | Struggles with indirect speech, free indirect discourse |
| Scenes | Topic segmentation (TextTiling, TopicTiling) + temporal markers | No gold-standard evaluation datasets for literary scene boundaries |
| Chapters | Regex + structural cues (headings, page breaks) | PDF extraction destroys structural markup |
| Narrative functions | Not yet solved at scale | Propp's morphology hand-coded; ML approaches need labeled data |
| Topics | LDA, NMF, BERTopic | Number-of-topics is a hyperparameter; results sensitive to preprocessing |
| Emotional arcs | Sentiment lexicons (hedonometer, VADER) or transformer classifiers on sliding windows | Irony, understatement, unreliable narration systematically mislead sentiment tools |
| Rhetorical structure | RST parsers (Ji & Eisenstein 2014, Feng & Hirst 2014) | Discourse parsing accuracy ~60% F1 — far below NER/POS quality |

### 3.3 Representation: How to Store Structure in Memory

Once identified, structure-objects need a representation that supports alignment, search, and visualization:

- **Span-indexed annotations**: `(start_char, end_char, label, attributes)` — the genome browser model. Every annotation is an interval on the character-position axis. Efficient for interval intersection queries (interval trees, R-trees).
- **Graph/network**: nodes = entities or segments, edges = relationships (co-occurrence, reference, temporal succession). Supports network metrics (centrality, clustering, community detection). Moretti's character networks; Swinehart's CYOA decision graphs.
- **Sequence of symbols**: the "narrative alphabet" approach. Encode each segment's feature profile as a discrete letter. Supports fast string algorithms (suffix arrays, FM-index, k-mer search). Our pipeline's `narrative_encoder.py`.
- **Time-series**: project a scalar feature (sentiment, entropy, dialog density) along the text's position axis. Supports signal processing (FFT, wavelet transform, DTW). Reagan et al.'s emotional arcs.
- **Hierarchical tree**: sections → subsections → paragraphs → sentences → tokens. Supports tree alignment algorithms (Zhang-Shasha), tree edit distance. RST discourse trees.

### 3.4 Matching Algorithms That Mirror Linguistic Relations

The scoring function in alignment must reflect what counts as a "good match" between structure-objects. In genomics, substitution matrices (BLOSUM, PAM) encode evolutionary plausibility: A→G transitions (purines) score higher than A→C transversions because they're more likely. What's the equivalent for text?

- **Lexical**: edit distance, Jaccard similarity on word sets
- **Semantic**: cosine similarity of sentence embeddings (what our pipeline's `SemanticAnalyzer` does)
- **Syntactic**: tree kernel similarity on parse trees, POS-tag sequence alignment
- **Narrative-functional**: substitution matrix for narrative functions (exposition↔exposition = high score; exposition↔climax = low score, like PAM for story elements)
- **Stylistic**: Burrows' Delta, cosine distance on most-frequent-word profiles

**The key unsolved problem**: we don't have a "BLOSUM for narrative functions." We need labeled corpora and probabilistic models of narrative-function substitution to build one. This is the equivalent of estimating amino acid substitution frequencies from evolutionary data — except for text, the "evolutionary data" would be adaptation/retelling corpora (e.g., all film adaptations of novels, all retellings of the Cinderella archetype).

### 3.5 Speed: Finding and Matching at Scale

For a corpus of N texts each of length L:
- Pairwise global alignment: O(N² × L²) — quadratic in both dimensions. Infeasible for large corpora.
- **Seed-and-extend** (BLAST paradigm): hash short k-mers, find seed matches in O(N×L), extend promising seeds. This is how Foldseek achieves its 4-5 order-of-magnitude speedup.
- **Structural alphabet + FM-index**: encode texts as alphabet strings, build a compressed full-text index. Query time: O(m) for a pattern of length m, independent of corpus size. This is the approach our narrative alphabet enables.
- **Embedding-based approximate nearest neighbor**: encode segments as vectors, use ANN indexes (HNSW in Qdrant, Faiss). Sublinear query time. This is what our RAG infrastructure already supports.

### 3.6 False Positives and False Negatives

- **False positives** (spurious matches): two passages match on surface features but have no meaningful relationship. Mitigation: multi-level filtering (require match at lexical + semantic + structural levels simultaneously), statistical significance testing (is this match more similar than random text at this distance?).
- **False negatives** (missed relationships): two passages are deeply related but differ in surface form (e.g., a paraphrase, an allusion that inverts the original). Mitigation: use semantic embeddings rather than lexical matching, train on paraphrase/allusion corpora, use multiple alignment strategies and union their results.

### 3.7 "Evolutionary" Models and Scoring Assumptions

In bioinformatics, alignment scoring is grounded in an evolutionary model: the probability that sequence A evolved into sequence B given a specific mutation rate and time. The Jukes-Cantor, Kimura, and HKY models formalize different assumptions about mutation processes.

What's the equivalent for text? Several possibilities:

- **Transmission model**: How does a text change as it passes through copying, editing, translation, or adaptation? Textual criticism (stemmatology) builds phylogenetic trees of manuscript traditions — this is literally phylogenetics for texts.
- **Genre model**: How do texts within a genre vary? What's the "mutation rate" of detective fiction vs. literary fiction? Underwood's genre modeling implicitly estimates this.
- **Author model**: How does a single author's style evolve across their career? Stylometry tracks this via most-frequent-word profiles, sentence length distributions, etc.
- **Cultural model**: How do themes, tropes, and narrative structures spread and mutate through a literary tradition? This is cultural evolution / memetics formalized.

Each model implies a different scoring matrix. A transmission model weights insertions/deletions differently than a genre model because the "mutation processes" are different (editorial revision vs. independent creative variation).

---

## 4. Visualization: Exploration vs. Presentation

### 4.1 Two Purposes of Visualization

This is a real and consequential distinction:

**Exploratory visualization** supports investigation. It is interactive, multi-scale, hypothesis-generating. The user navigates, zooms, filters, and follows leads. The goal is to see something you didn't expect.
- Examples: genome browsers (JBrowse), network explorers (Gephi), Swinehart's scrollable Infinite Jest visualizations
- Design priority: flexibility, responsiveness, detail-on-demand
- Risk: visual clutter, cognitive overload, confirmation bias (you see patterns in noise)

**Presentational visualization** supports argumentation. It is static or lightly interactive, focused, conclusion-conveying. The author has already found the insight and encodes it for the reader.
- Examples: Moretti's network diagrams in "Plot Analysis," Reagan's 6-arc SVD decomposition figures, Circos plots in publications
- Design priority: clarity, narrative flow, aesthetic quality, minimal cognitive load
- Risk: oversimplification, cherry-picking, loss of context

### 4.2 The Genome Browser Paradigm for Text

The most powerful exploratory visualization paradigm from genomics is the **multi-track browser**: a linear coordinate axis (genome position / character position) with stacked annotation tracks. Each track shows a different analytical layer:

For text, the tracks could be:
- **Raw text** (with highlighting)
- **Named entities** (color-coded by type)
- **Sentiment trajectory** (line chart)
- **Dialog attribution** (character-colored spans)
- **Topic membership** (colored regions)
- **Narrative alphabet** (discrete letter annotations)
- **Cross-reference links** (arc connectors to other positions or other texts)
- **Structural boundaries** (chapter/scene/paragraph markers)

This is exactly the "text browser" concept from our alignment convergence thesis. JBrowse 2's architecture (modular, plugin-based, TypeScript/React) is the natural template.

### 4.3 Making Alignments Searchable

Efficient search over alignments requires indexing both the aligned texts and their correspondences:

- **Position-to-annotation**: given a character position, return all annotations at that position (interval tree / R-tree)
- **Annotation-to-position**: given a named entity or topic, return all positions where it occurs (inverted index)
- **Correspondence queries**: given a position in text A, return all aligned positions in text B (alignment index — stored as a sorted list of (posA, posB, score) tuples)
- **Pattern search on narrative alphabet**: given a motif like "AABCDDCA" (exposition → build → climax → resolution), find all occurrences across the corpus (FM-index or suffix array on concatenated alphabet strings)

### 4.4 Making Alignments Interactively Explorable

Beyond search, interactive exploration requires:

- **Linked views**: clicking a position in one text highlights the aligned position in another. Clicking a character name highlights all their appearances. This is the "brushing and linking" paradigm from information visualization.
- **Semantic zoom**: at the whole-text level, show the narrative alphabet as a colored barcode. At the chapter level, show topic distributions. At the paragraph level, show entity annotations. At the sentence level, show POS tags and dependency parses. This mirrors genome browser zoom levels (chromosome → region → gene → exon → codon).
- **Alignment overlay**: superimpose two texts' feature trajectories (e.g., sentiment arcs) with the alignment mapping shown as connecting lines. Where the arcs converge, the texts are structurally parallel; where they diverge, they differ.

---

## 5. Open Research Questions

These are the questions that research and development should address, roughly ordered by tractability:

### Near-term (answerable with existing tools and data)

1. **How stable is the narrative alphabet across segmentation granularity?** Does a text's structural fingerprint change qualitatively when you segment by sentence vs. paragraph vs. chapter?
2. **Can narrative alphabet edit distance predict genre similarity?** If two novels have similar alphabet sequences, are they more likely to be in the same genre?
3. **What's the relationship between Reagan's emotional arc shapes and the narrative alphabet?** Are the 6 archetypal arcs detectable as alphabet motifs?
4. **How does the text browser paradigm scale?** Can you display a full novel (~100K words, ~5K paragraphs) with multiple annotation tracks at interactive framerates?

### Medium-term (require new data or models)

5. **Building a BLOSUM for narrative functions**: What corpora of retellings/adaptations exist that could ground a substitution matrix?
6. **Discourse-aware alignment**: Can RST parse trees improve text alignment quality over flat sequence alignment?
7. **Cross-lingual structural alignment**: Do translated novels preserve their narrative alphabet sequence? (This tests whether the alphabet captures deep structure vs. surface features.)
8. **Epigenetic layer detection**: Can we reliably detect irony, unreliable narration, and free indirect discourse at scale?

### Long-term (require fundamental research)

9. **Is there a universal grammar of narrative?** Do all human stories share structural invariants analogous to the universal genetic code?
10. **What is the "information content" of literary structure?** Shannon entropy measures information in a sequence, but what's the information content of the *structure* of that sequence?
11. **Can alignment reveal influence?** If novel B was influenced by novel A, does structural alignment between them show systematic patterns distinct from genre similarity?
12. **Automated close reading**: Can we build a system that, given a text and a structural alignment, generates interpretive commentary comparable to a trained literary critic?

---

## 6. Annotated Bibliography Pointers

Cross-references to research catalog entries and downloaded materials, organized by conceptual question:

### Structure and Alignment Theory
- Mäkinen et al., *Genome-Scale Algorithm Design* Ch. 6 — formal definition of edit distance, LCS, global/local/semi-local alignment, scoring matrices, Needleman-Wunsch, Smith-Waterman
- Foldseek (van Kempen et al., 2023) — structural alphabet paradigm: 3D→1D encoding for fast search
- Johnson et al. (eLife 2024) — positional embeddings compressed to single bytes for speed-optimized search

### Functional Layers of Text
- Piper, *Enumerations* — each chapter operationalizes one layer: punctuation (phonetic/prosodic), plot (narrative arc), topoi (semantic), fictionality (pragmatic), characterization (entity)
- Eve, *Close Reading with Computers* — textual scholarship as alignment: comparing variant editions of *Cloud Atlas*
- Toolan, *Making Sense of Narrative Text* — cognitive models of how readers construct structure

### Discovery of Structure
- Reagan et al. (2016) — SVD decomposition discovers 6 archetypal emotional arcs from 1,327 stories
- Moretti, "Network Theory, Plot Analysis" — character network analysis; honest about limitations of visualization alone
- Underwood, *Distant Horizons* — predictive modeling discovers genre boundaries, stylistic change over centuries

### Visualization and Interaction
- Swinehart/Samizdat — CYOA as directed graphs; IJ endnote arcs; scroll-driven interactive design
- Krzywinski (Circos, 2009) — circular ideogram paradigm; ribbons encode 3-dimensional correspondences
- JBrowse 2 (Diesh et al., 2024) — modular genome browser architecture → "text browser" template
- Storyline visualization lineage (Tanahashi & Ma 2012 → StoryFlow 2013 → Story Ribbons 2025)

### Speed and Search
- BLAST/Smith-Waterman — seed-and-extend paradigm for subquadratic alignment
- FM-index / suffix arrays — full-text search in compressed space
- HNSW (approximate nearest neighbor) — sublinear embedding search

---

---

## 7. The Pre-Computational Problem: What Must Be Solved Before ML

Infinite Jest is the canonical stress test for Palimpsest — not as a development target, but as a reality check. The companion literature (Burn's *Reader's Guide*, Carlisle's *Elegant Complexity*, Feene's character guide, Cordes' chronological reading order) represents hundreds of hours of human analytical labor. These works expose problems that ML-based approaches tend to paper over:

### 7.1 What Is a "Character"?

In Infinite Jest, "Hal Incandenza" is one character. But "the kid in the red bandanna" who appears on page 5 might be the same person as "Ingersoll" on page 200 — or might not. A character is not a named entity; it's a **persistent identity** that may be referred to by name, pronoun, description, nickname, title, or epithet. BookNLP handles coreference for straightforward cases, but literary novels deliberately exploit ambiguity:

- **Unreliable references**: a character may be misidentified by the narrator
- **Split identities**: a character under an alias (the "Madame Psychosis" / Joelle van Dyne duality)
- **Collective characters**: "the Tunnel Club" or "the AFR" act as characters but have shifting membership
- **Characters who exist only in reference**: Infinite Jest's "James O. Incandenza" is dead throughout the novel but drives the entire plot

The question isn't "can NER find character names?" — it's "what ontology of personhood does the text assume?"

### 7.2 What Is a "Relationship"?

Character relationships in the Swinehart `plotlines.csv` are implicit in co-occurrence tags. But real relationships are typed, directional, and temporal:

- **Kinship**: Hal is the son of Avril and James (but James is dead; Avril may have an affair with Charles Tavis; the paternity question is never resolved)
- **Institutional**: Hal is a student at ETA; Don Gately is a resident at Ennet House — these are completely separate social worlds that barely interact until the novel's climax
- **Adversarial**: the AFR (Assassins des Fauteuils Rollents) are hunting the Entertainment — but the protagonists don't know this until late in the book
- **Emotional valence**: Hal and Orin's relationship is estranged; Hal and Mario's is protective; these require interpretive reading, not co-occurrence counting

Moretti's honest admission that his character network analysis produced results "difficult to interpret" stems from exactly this: **co-occurrence is not relationship**. The IJ character guide's manually annotated descriptions capture relationship quality that no current NLP pipeline can extract.

### 7.3 Building a Glossary: The Ontology Problem

Feene's character guide is essentially a **domain ontology** for Infinite Jest — a structured vocabulary of entities, their types, attributes, and relations. For any text, the question is: what are the domain-specific concepts that matter, and how do you represent them?

For IJ, the glossary includes:
- Characters (with aliases, family trees, institutional affiliations)
- Places (ETA, Ennet House, the Great Concavity — and the fact that characters call the same place "the Great Concavity" or "the Great Convexity" depending on which side of the border they're on)
- Temporal markers (Subsidized Time: "Year of the Depend Adult Undergarment" = a specific year that must be reconstructed from internal evidence)
- Substances and artifacts (the Entertainment, DMZ, various drugs)
- Organizations (ETA, AFR, ONAN, InterLace)

Building this glossary automatically requires:
1. **Entity discovery**: finding mentions of things that matter (NER+)
2. **Identity resolution**: recognizing that different mentions refer to the same thing (coreference+)
3. **Type assignment**: categorizing entities (person, place, substance, organization)
4. **Relation extraction**: connecting entities to each other with typed edges
5. **Temporal anchoring**: placing entities and events on a timeline

Steps 1-2 are partially automatable with current tools. Steps 3-5 require substantial domain knowledge or iterative human-AI collaboration — which is where Palimpsest should aim. Not fully automated extraction, but **assisted extraction with human-in-the-loop verification**.

### 7.4 Who Is Speaking? The Dialog Attribution Problem

Page 5 of Infinite Jest is narrated by Hal in first person. Page 37 shifts to third-person omniscient. Page 128 contains a lengthy monologue by a character in an AA meeting — inside a chapter narrated from Don Gately's perspective. Identifying "who is speaking" requires tracking:

- **Narrative voice**: first-person, third-person limited, third-person omniscient, second-person (yes, IJ has this too)
- **Direct speech**: "She said, 'I am here'" — quotation marks delimit, but IJ doesn't always use them
- **Indirect speech**: "She said she was there" — still her words, but embedded in narration
- **Free indirect discourse**: "She was here now, wasn't she" — whose thoughts are these? The narrator's or the character's? This is genuinely ambiguous by design
- **Embedded narratives**: a character telling a story within the story, which may itself contain dialog

BookNLP's quotation attribution handles cases 1-2. Cases 3-5 are open research problems.

### 7.5 The Lesson for Palimpsest

IJ teaches that the "interesting" structural problems in text are not the ones ML currently solves well. The pipeline we built (extract → clean → segment → signal → encode) handles the surface layers — the genomic equivalent of reading the raw sequence. But the deeper layers (chromatin folding, epigenetic marking, regulatory networks) require:

1. **Explicit structural hypotheses** that can be tested and refined
2. **Human annotation interfaces** that make expert knowledge capturable
3. **Iterative refinement** where computational results are evaluated by readers and corrected
4. **Tolerance for ambiguity** — some structural questions genuinely don't have single answers

This is why the pipeline should produce **searchable, inspectable intermediate representations** (the text browser paradigm) rather than black-box classifications. The goal isn't "automatically understand Infinite Jest" — it's "build tools that help a reader see what they couldn't see before, and test hypotheses about what they think they see."

---

*This document is a living framework. Update as research expands and development reveals which questions matter most.*

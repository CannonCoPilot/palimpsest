# Palimpsest: Conceptual Foundation

**Date**: 2026-06-08
**Status**: Stage 2a deliverable — comprehensive synthesis of all deep reads, frameworks, and the 118-paper research corpus
**Supersedes**: docs 01, 03-06, 07-10 (which remain as source material)

---

## 0. Thesis

A literary text is a genome. Not metaphorically — structurally. Both are linear sequences encoding hierarchical, multi-scale functional organization that no single analytical lens can fully resolve. The genome annotation revolution — from raw sequence through ab initio prediction, evidence integration, chromatin state discovery, and multi-track browser visualization — provides a complete, battle-tested architectural blueprint for computational literary analysis.

Palimpsest is the platform that implements this blueprint. It treats text as sequence, annotations as tracks, alignment as comparison, and the genome browser as the interaction paradigm. But it does not merely translate genomics tools into literary terms. It recognizes that literary texts have properties genomes do not — intentionality, ambiguity, interpretive multiplicity, and aesthetic purpose — and builds these properties into the architecture as first-class constraints.

This document synthesizes the conceptual foundations that make this possible, drawing on 118 sources across computational linguistics, genomics, visualization theory, and digital humanities.

---

## 1. What Is Structure?

### 1.1 The Alignment-Structure Recursion

Structure is both the input to and the output of alignment (doc 01 §1.3). In genomics, you align two genomes assuming collinearity (syntenic gene order preservation), and the alignment reveals where that assumption breaks — inversions, translocations, duplications (Mäkinen et al. 2023, Ch. 6). In text analysis, the same recursion operates:

- Assume two editions share narrative structure → alignment reveals editorial differences (Eve 2019 on *Cloud Atlas*)
- Assume genre texts share thematic structure → alignment reveals where they diverge (Underwood 2019 on genre evolution)
- Assume no structure → clustering discovers whatever structure exists (Blei et al. 2003; Piper 2018 Ch. 3)

The formal definition: an alignment between sequences A and B is an injective partial mapping from positions in A to positions in B that **respects an ordering constraint** and **maximizes a scoring function** (Needleman & Wunsch 1970; Smith & Waterman 1981). The ordering constraint *is* the structural assumption. In global alignment (Needleman-Wunsch), the constraint is strict collinearity. In local alignment (Smith-Waterman), the constraint is relaxed to allow unmatched regions. In the GNAT system (Pial & Skiena 2023), which is the closest prior art to Palimpsest's core alignment module, the constraint accommodates narrative reordering through SBERT-based semantic scoring with Gumbel-calibrated significance.

### 1.2 Levels of Structure

Structure is not monolithic. DNA has primary (linear sequence), secondary (base-pairing), tertiary (3D folding), and quaternary (multi-molecule complexes) structure. Text has an analogous hierarchy:

| Level | Genomic | Literary | Analytical Method |
|-------|---------|----------|-------------------|
| **Primary** | Nucleotide sequence | Character stream | Edit distance, tokenization |
| **Secondary** | Local base-pairing, stems/loops | Sentence syntax, local repetition patterns | Dependency parsing (Nivre 2006), RQA (Amancio 2022) |
| **Tertiary** | Chromatin loops, TADs, compartments | Narrative arcs, thematic domains, long-range callbacks | Hi-C analogy: TextHiC passage-pair matrices (Lieberman-Aiden 2009; Dixon 2012) |
| **Quaternary** | Multi-chromosome territories | Multi-text corpora, intertextual networks | Corpus-level alignment, citation graphs (Moretti 2013) |

The key insight from Bonev & Cavalli (2016): these levels operate simultaneously at different scales with different stability properties. Chromosome territories are cell-type invariant; TADs are moderately stable; individual loops are dynamic and context-specific. Literary structure follows the same stability gradient: genre conventions (very stable) > macro-plot shapes (stable) > chapter architecture (moderate) > paragraph-level thematic flow (dynamic) > sentence-level style (highly variable).

### 1.3 The Structural Alphabet

Foldseek (van Kempen et al. 2023) achieved a 4-5 order-of-magnitude speedup in protein structure comparison by encoding 3D geometry as a 1D sequence of 20 discrete states (the 3Di alphabet), then applying fast sequence-alignment algorithms to the encoded representation. The prior knowledge leveraged: local geometric interactions between adjacent residues capture most structural information needed for fold comparison.

For text, the analog is the **narrative alphabet**: encoding each text segment's multi-dimensional feature vector as a discrete state label, then using sequence alignment on the state sequence. The feature vector draws from:

- **Narrative function**: exposition, rising action, climax, falling action (Freytag; operationalized by Boyd et al. 2020's staging/progression/tension)
- **Speech act type**: dialogue, narration, description, interior monologue (BookNLP/Bamman et al. 2014)
- **Information density**: lexical entropy, vocabulary richness, hapax rate
- **Temporal mode**: past narration, present action, flashback (Genette 1972/1983 on narrative order)
- **Register/style**: sentence length, syntactic complexity, formality markers (Burrows 2002; Eder et al. 2016)

ChromHMM (Ernst & Kellis 2010, 2012) demonstrates that these multi-dimensional features can be learned jointly: a multivariate HMM trained on combinatorial patterns of binary features discovers latent states that correspond to meaningful functional categories — without pre-defining what those categories are. This is the **LitHMM** concept: the core Palimpsest innovation.

---

## 2. Annotation as the Foundation Layer

### 2.1 Why Annotation Is Harder Than Alignment

Alignment is a two-input problem. Annotation is open-ended and multi-layered: given text A, discover and record *everything happening in it* at every level of organization (doc 07 §0). In genomics, the Human Genome Project spent far more effort on annotation (ENCODE, Roadmap) than on the initial sequencing alignment. The ENCODE Phase II project (2012) mapped 1,640 functional datasets, assigning biochemical function to 80.4% of the genome. The corollary for text: most of a text's passages carry functional signal, even passages that seem "nonfunctional" at first glance — the challenge is characterizing *what kind* of function.

### 2.2 The Annotation Paradox

The most valuable annotations require the most human judgment; the most automatable require the least (doc 07 §0). A machine counts word frequencies and detects named entities. A human reader notices irony, unreliable narration, and structural echoes. The gap between NLP capability and reader perception is the core design problem.

The genome annotation world solved the analogous problem with the **MAKER evidence model** (doc 09 §1.1): combine three independent evidence streams — ab initio prediction, transcript evidence, protein homology — and let human curators adjudicate where they disagree. Each annotation carries an **Annotation Edit Distance (AED)** score measuring evidence agreement.

For Palimpsest, the three evidence streams are:
1. **Ab initio predictions** = ML model outputs (NER, sentiment, topic segmentation, event detection)
2. **Textual evidence** = the words themselves (explicit structural markers, verbatim quotations, formatting signals)
3. **Cross-text parallels** = does a similar passage in a related work already have an annotation? (Alignment-derived transfer, analogous to protein homology)

### 2.3 Five Types of Text Annotation

Examining Swinehart's Infinite Digest datasets reveals five fundamentally different annotation types (doc 07 §2), each requiring distinct data models:

1. **Coordinate systems** — Where things are. Narrative order vs. chronological order vs. character offset. Genette's (1972/1983) fabula/syuzhet distinction is a coordinate mapping function. Genomic analog: physical position vs. genetic map distance vs. cytogenetic bands.

2. **Categorical determinations** — What things are. Character classification, scene typing, rhetorical function labeling. Genomic analog: gene prediction (GENSCAN/Burge & Karlin 1997), GO term assignment (Gene Ontology Consortium 2000).

3. **Quantitative measurements** — How much of something. Sentiment scores, lexical density, dialogue ratio. Genomic analog: expression levels (RNA-seq), methylation percentages.

4. **Relational links** — What connects to what. Intertextual references, character co-occurrence, narrative callbacks. Genomic analog: chromatin loops (Rao et al. 2014), enhancer-promoter linkage.

5. **Structural states** — What role a passage plays in context. Functional passage states emerging from combinatorial feature patterns. Genomic analog: chromatin states from ChromHMM (Ernst & Kellis 2012) — 15 states from combinatorial histone marks.

### 2.4 The Literary Feature Ontology

The Sequence Ontology (Eilbeck et al. 2005) provides a controlled vocabulary of 2,500+ terms for genomic features, organized in a formal hierarchy with defined relationships (part_of, derives_from, adjacent_to). Every GFF3 annotation record references an SO term, enabling interoperability across tools and organisms.

Palimpsest needs an equivalent **Literary Feature Ontology (LFO)** — a formal vocabulary for literary features that enables:
- Consistent annotation across texts and users
- Hierarchical feature relationships (a "dialogue scene" is_a "scene" is_a "narrative_unit")
- Cross-text comparability (is this "recognition scene" in Novel A the same type as that one in Novel B?)
- Formal reasoning about annotation types (if X is_a "analepsis" and Y is_a "prolepsis", then X and Y are both is_a "anachrony" — Genette 1972/1983)

The LFO should be bootstrapped from existing literary taxonomies: Genette's narratological categories (order, duration, frequency, mood, voice), Propp's morphological functions, rhetorical figure taxonomies, and genre conventions — then extended through use as readers encounter features that don't fit existing categories.

---

## 3. Discovery: Finding Structure Without Knowing What You're Looking For

### 3.1 The Agnostic Approach

The most powerful genomic discovery methods work without pre-specifying what they're looking for:

- **ChromHMM** (Ernst & Kellis 2012): Discovers chromatin states from combinatorial histone mark patterns using a multivariate HMM. The number and character of states emerge from the data.
- **Segway** (Hoffman et al. 2012): Similar goal, different model — dynamic Bayesian network with continuous-valued inputs. Discovers finer-grained states than ChromHMM.
- **RepeatModeler2** (Flynn et al. 2020): Discovers transposable element families de novo from repetitive sequence patterns.
- **MEME** (Bailey & Elkan 1994): Discovers sequence motifs (short conserved patterns) from a set of unaligned sequences via expectation-maximization.

For literary text, the agnostic equivalents are:
- **LitHMM**: Multivariate HMM on textual feature vectors (lexical density, dialogue ratio, NE density, sentiment volatility, sentence length variance) to discover latent passage states. This is ChromHMM applied to text.
- **Topic modeling** (Blei et al. 2003): Discovers latent topics from word co-occurrence patterns. Piper (2018, Ch. 3) demonstrates this at corpus scale on 15,000 novels.
- **Emotional arc decomposition** (Reagan et al. 2016): SVD on sentiment trajectories discovers 6 archetypal shapes across 1,327 stories — structure that emerges without pre-specification.
- **Narrative event chains** (Chambers & Jurafsky 2008, 2009): Learns narrative schemas from raw text using coreference-based PMI between verb-dependency pairs.

### 3.2 The Close/Distant Reading Cycle

Piper (2018) reframes the close/distant binary as an iterative cycle: belief → close reading → measurement → distant reading → interpretation → model → remodel. The model is a representation encoding the critic's situated beliefs — not an objective transcript (Underwood 2019 calls this "perspectival modeling"). Palimpsest must embed this cycle in its architecture:

1. **Import** → Base tracks computed automatically (distant reading)
2. **Explore** → Reader notices something the Base tracks don't capture (close reading)
3. **Extend** → Reader describes the feature; AI proposes annotation schema + detection strategy (model)
4. **Refine** → Reader corrects false positives; model retrains (remodel)
5. **Compare** → Feature applied across corpus; patterns emerge (distant reading at larger scale)

This is the Base/X architecture from doc 11: universal tracks (Base) with per-text adaptive extensions (X) that emerge from reader-AI collaboration.

---

## 4. The Genome Browser as Interaction Paradigm

### 4.1 Multi-Track Linear Visualization

The genome browser (Kent et al. 2002; Robinson et al. 2011; Diesh et al. 2023) is the most successful example of multi-layer annotation visualization in any domain. Its core design: a linear coordinate axis (base-pair position) with stacked annotation tracks, each rendering a different data type at the current zoom level. The user scrolls horizontally through the sequence and vertically through tracks.

JBrowse 2's pluggable architecture (doc 10 §Finding 1) separates concerns cleanly:
- **Adapter** — data retrieval (how to read the file)
- **Track** — what data to show
- **Display** — how to render it for a specific view type
- **Renderer** — pixel-level drawing (runs in a web worker)

A single Track can have multiple Display types: a `VariantTrack` has both a `LinearVariantDisplay` and a `ChordVariantDisplay`. For Palimpsest: a "character presence" annotation layer should have a `LinearTextDisplay` (inline highlights in the reading view), a `HeatmapDisplay` (density overview), and a `ChordDisplay` (character co-occurrence arcs).

### 4.2 Circular and Relational Visualization

Circos (Krzywinski et al. 2009) encodes three dimensions in ribbons: source position, target position, and relationship strength. The circular layout minimizes edge crossings — a fundamental problem in linear displays. For text, Circos ribbons naturally represent:
- Endnote/cross-reference connections (Swinehart's "All Those Footnotes" IS a Circos diagram)
- Intertextual parallels between passages
- Character co-occurrence across chapters
- Thematic echo patterns (TextHiC long-range contacts)

HiGlass (Kerpedjiev et al. 2018) extends this to interactive, zoomable contact matrices — applicable to TextHiC passage-pair similarity visualization.

### 4.3 Visualization Theory Foundations

The visual encoding choices are grounded in established theory:

- **Bertin's visual variables** (1967): position, size, shape, value (lightness), color, orientation, texture — seven channels for encoding data dimensions. Position is the most effective channel for quantitative data (Cleveland & McGill 1984).
- **Munzner's what-why-how framework** (2014): What data → why the user needs it → how to encode it visually. Palimpsest's multiple view types (linear browser, circular Circos, dotplot, network graph) serve different "why" goals.
- **Wickham's layered grammar** (2010, extending Wilkinson 2005): Data → aesthetic mapping → geometric objects → statistical transforms → coordinate system → faceting. This declarative approach maps directly to Palimpsest's track configuration language.
- **Focus+context** (Furnas 1986): Show detail in the area of interest while maintaining global context. Genome browsers implement this via zoom + overview tracks; Palimpsest needs the same for text (detailed annotations in the reading view, density overview in the navigation bar).
- **Coordinated multiple views** (Roberts 2007): Linked highlighting, brushing (Buja et al. 1996), and synchronized navigation across views. Selecting a passage in the reading view highlights the corresponding point in the dotplot and the Circos diagram.

### 4.4 Narrative-Specific Visualization

Beyond the genomic paradigm, Palimpsest draws on narrative visualization research:

- **Storyline visualizations** (Tanahashi & Ma 2012): Character lines over a time axis, optimized for minimum crossings and wiggles. StoryRibbons (Yeh et al. 2025) extends this with LLM-extracted scene data and a configurable Y-axis.
- **Word Trees** (Wattenberg & Viégas 2008): Interactive concordances that reveal branching context patterns from any selected phrase.
- **Literature Fingerprinting** (Keim & Oelke 2007): Pixel-level visualization of entire texts, encoding features as color at character resolution.
- **Text-viz survey** (Jänicke et al. 2015): Comprehensive taxonomy of close-reading and distant-reading visualization techniques for literary text.

---

## 5. The Palimpsest Architecture: Synthesis

### 5.1 Core Principles

1. **Text as sequence**: Every text is a coordinate system. Character offsets are base-pair positions. Multiple coordinate systems (narrative order, chronological order, page numbers) coexist with explicit mapping functions.

2. **Annotations as tracks**: Every computational analysis produces a track. Tracks are typed (categorical, quantitative, relational, structural), stored in standoff format (W3C Web Annotation Data Model), and referenced to the Literary Feature Ontology.

3. **Alignment as comparison**: Pairwise and multiple text alignment using the full algorithmic toolkit — global (Needleman-Wunsch), local (Smith-Waterman/GNAT), structural alphabet (LitHMM state sequences), semantic (SBERT embeddings).

4. **The genome browser as interaction paradigm**: Multi-track linear visualization with zoom-dependent rendering, linked circular/relational views, and coordinated multiple views.

5. **Evidence-based annotation**: MAKER model — combine ML predictions, textual evidence, and cross-text parallels. Every annotation carries a confidence score.

6. **Agnostic discovery**: ChromHMM/LitHMM discovers structure without pre-specifying categories. The platform learns from each text it encounters.

7. **Perspectival modeling**: Every analysis reflects a specific lens (Underwood 2019). The platform never presents a single authoritative reading — it shows which perspective generated each result.

### 5.2 The Base/X Architecture

**Palimpsest Base** computes universal tracks automatically on import:

| Track | Method | Source |
|-------|--------|--------|
| Segmentation | TextTiling (Hearst 1997) + embedding discontinuity | Structural |
| Named entities | BookNLP (Bamman et al. 2014) / spaCy + LitBank | Categorical |
| Sentiment trajectory | Sliding-window hedonometer (Reagan et al. 2016) | Quantitative |
| Lexical features | TF-IDF, TTR, hapax legomena, vocabulary richness | Quantitative |
| Syntactic complexity | Dependency parsing (Nivre 2006) + sentence metrics | Quantitative |
| Dialogue attribution | BookNLP quote attribution | Categorical |
| Narrative arc | Boyd 15-dimensional function-word arc (2020) | Quantitative |
| Self-similarity | Church-Helfman dotplot (1993) + RQA metrics | Relational |
| Passage functional state | LitHMM — multivariate HMM on feature vectors | Structural |
| Narrative alphabet | K-means on feature vectors → discrete states | Structural |
| Coreference chains | BookNLP coreference | Relational |
| Topic distributions | LDA (Blei et al. 2003) per segment | Quantitative |

**Palimpsest-X** extends Base for each text through reader-AI collaboration. Custom annotation schemas, text-specific entity ontologies, custom coordinate systems, domain-specific scoring matrices, trained classifiers, and custom visualization components emerge from the iterative close/distant reading cycle.

### 5.3 The Five Adversarial Perspectives

Every design decision and document in the Palimpsest project is reviewed by five adversarial personas (doc 00 §Stage 4):

1. **Dr. Elena Marchetti** (Functional Genomics): Demands biological rigor. Checks that genomic analogies are accurate, not superficial. Questions whether alignment algorithms preserve claimed properties.

2. **Dr. James Okonkwo** (Platform Architecture): Demands scalability and performance. Questions every O(n²) loop, every synchronous operation. Won't accept "it works on chapter 1."

3. **Prof. Sarah Blackwood** (Computational Linguistics / Comparative Literature): Demands that computational methods respect literary complexity. Questions whether features like "sentiment" capture anything meaningful.

4. **Dr. Raj Patel** (Data Engineering / Visualization): Demands visual clarity and perceptual accuracy. Insists on proper visual grammar (Bertin, Munzner). Questions data-ink ratio.

5. **Alex Chen** (Power User / Stress Tester): Demands speed, scale, and analytical depth. Loads War and Peace with all tracks enabled. Compares 50 novels simultaneously. Finds every crash.

---

## 6. Novel Contributions

Palimpsest's conceptual framework yields several ideas not found in the existing literature:

### 6.1 Literary Orthology and Paralogy
From Fitch (1970) and Koonin (2005): texts can be **orthologous** (descended from a common ancestor through speciation — e.g., different translations of the Bible) or **paralogous** (duplicated within a tradition and diverging in function — e.g., genre variations on the same plot). This distinction, formalized through alignment-based phylogenetic methods, could ground comparative literary analysis in rigorous evolutionary logic.

### 6.2 TextHiC and Thematic Compartmentalization
From Lieberman-Aiden et al. (2009): building passage-pair similarity matrices reveals A/B compartments (thematically active vs. latent), TAD-like self-interacting narrative domains (analogous to Dixon et al. 2012's directionality index), and statistically anomalous long-range "loop" connections (analogous to Rao et al. 2014's HiCCUPS algorithm). This provides a principled, unsupervised decomposition of narrative structure at multiple scales.

### 6.3 The MAKER Evidence Model for Literary Annotation
From genome annotation: combining ML predictions, textual evidence, and cross-text parallels with confidence scoring. No existing literary annotation platform implements this three-source evidence architecture with quantitative confidence metrics.

### 6.4 LitHMM: Agnostic Passage State Discovery
From ChromHMM (Ernst & Kellis 2012): training a multivariate HMM on combinatorial textual feature patterns to discover functional passage states without pre-defining categories. The 15-state chromatin model (promoter-active, enhancer-active, transcribed, repressed, bivalent, heterochromatic, quiescent) provides a starting vocabulary that maps surprisingly well to literary passage types.

### 6.5 Narrative Alphabet Alignment
From Foldseek (van Kempen et al. 2023): encoding multi-dimensional passage features as a 1D sequence of discrete state labels, then using fast sequence-alignment algorithms for comparison at speeds orders of magnitude faster than pairwise semantic similarity computation.

---

## References

This document draws on all 118 sources in the master bibliography (master-bibliography.md), with particular reliance on:

**Alignment theory**: Needleman & Wunsch 1970, Smith & Waterman 1981, Altschul et al. 1990, Mäkinen et al. 2023, Pial & Skiena 2023 (GNAT)
**Chromatin state discovery**: Ernst & Kellis 2010/2012 (ChromHMM), Hoffman et al. 2012 (Segway)
**3D genome**: Lieberman-Aiden et al. 2009, Dixon et al. 2012, Rao et al. 2014, Bonev & Cavalli 2016
**Annotation infrastructure**: Eilbeck et al. 2005 (SO), Gene Ontology Consortium 2000, ENCODE 2012, Hovy & Lavid 2010, Pustejovsky & Stubbs 2012
**NLP/Narrative**: Bamman et al. 2014 (BookNLP), Chambers & Jurafsky 2008/2009, Lehnert 1981, Reagan et al. 2016, Boyd et al. 2020
**Digital humanities**: Moretti 2013, Jockers 2013, Underwood 2019, Piper 2018, Eve 2019
**Visualization**: Bertin 1967, Tufte 1983, Munzner 2014, Krzywinski et al. 2009, Kent et al. 2002, Diesh et al. 2023, Wickham 2010
**Narratology**: Genette 1972/1983, Genette 1982/1997, Kristeva 1966
**Distributional semantics**: Harris 1954, Deerwester et al. 1990, Mikolov et al. 2013, Vaswani et al. 2017

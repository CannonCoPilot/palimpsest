# Deep Reading: NLP & Narrative Papers — Palimpsest Relevance Analysis

**Generated**: 2026-06-06
**Papers analyzed**: 12 (10 present on disk, 2 absent, 3 bonus papers found)

---

## Summary Architecture

Reading these papers together, a coherent multi-layer architecture emerges:

- **Layer 1 — Surface Alignment (GNAT):** SW algorithm with SBERT embeddings on paragraph-sized chunks. Outputs local alignment regions with Gumbel-calibrated p-values.
- **Layer 2 — Structural Fingerprinting (Boyd, Reagan, RQA):** Fast, cheap pre-filters. Boyd's 15-dimensional arc vector, Reagan's 6-arc classification, and RQA's (RR, DET, LAM) triple form a ~20-dimensional structural signature per text.
- **Layer 3 — Character Networks (BookNLP, Elson):** Extract character entities with typed dependency vectors; build dialogue-based social networks for character-to-character matching.
- **Layer 4 — Event Structure (Chambers & Jurafsky 2008, 2009):** Narrative event chains and schemas as deep structural fingerprints invariant to surface language.
- **Layer 5 — Affect/Plot Structure (Lehnert):** Plot unit graphs from per-character affect sequences. Discrete, visualizable structural comparison via graph edit distance.
- **Visualization (Recurrence networks, RQA, dotplot):** Recurrence plot/dotplot as natural visual output for alignment results.

---

## Paper-by-Paper Analysis

### 1. GNAT — General Narrative Alignment Tool (Pial & Skiena, EMNLP 2023)

**Core Concept.** Adapts Smith-Waterman local alignment from bioinformatics to semantically related but textually dissimilar narrative documents (translations, abridgements, retellings).

**Palimpsest Relevance.** Most directly actionable paper — solves exactly the problem of detecting intertextual reuse without literal word repetition. The Gumbel-distribution significance model enables p-values on alignments rather than arbitrary similarity scores.

**Technical Detail.** SW recurrence: `H(i,j) = max(H(i-1,j-1) + S(xi,yj), H(i-1,j)+g, H(i,j-1)+g, 0)`. Similarity function S swappable: SBERT cosine (best general), Jaccard (fast, AUC 0.94 vs 0.99), TF-IDF, GloVe. Background distribution follows Gumbel (μ=1.29, β=0.30). O(mn) time. Multiple local alignments via traceback.

**Key Finding.** Plagiarism detection F1=0.85 on PAN-13 summary-obfuscation (vs top competition 0.35-0.61). Translated-book alignment AUC=0.99 with SBERT.

**Action.** Implement SW as primary alignment engine with SBERT scoring. Compute Gumbel calibration offline per corpus domain. Codebase: `github.com/tanzir5/alignment_tool2.0`.

---

### 2. BookNLP — Bayesian Mixed Effects Model of Literary Character (Bamman et al., ACL 2014)

**Core Concept.** NLP pipeline for book-length documents: clusters character name mentions, resolves pronominal coreference, infers latent character types from typed dependency relations.

**Palimpsest Relevance.** Provides machinery to extract character entities across both texts for character-aware alignment. The Bayesian mixed effects model controls for author-level style drift across centuries.

**Technical Detail.** Four-category typed-dependency vector: agent verbs, patient verbs, possessive nouns, predicative adjectives/nouns. 74% of character references in novels are pronouns — robust coreference is non-optional. Uses Stanford POS, MaltParser (linear-time), Stanford NER — avoids cubic-complexity full parsing for 1.8B token scalability.

**Action.** Integrate BookNLP as character extraction layer. Four-category dependency vector becomes canonical character representation for cross-text similarity scoring.

---

### 3. Narrative Event Chains (Chambers & Jurafsky, ACL 2008)

**Core Concept.** Learns "narrative chains" — partially ordered event sets sharing a protagonist — from raw text using coreference-based PMI between verb-dependency pairs.

**Palimpsest Relevance.** Event chains persist across retellings even when surface language changes entirely. Matching event chains detects structural borrowing invisible to surface alignment.

**Technical Detail.** Narrative event = tuple `(verb, typed-dependency-of-protagonist)`. PMI approximation for scoring. "Narrative cloze" evaluation. 36% improvement over baseline on event prediction.

**Action.** Implement event chain extraction as second-pass analysis on dependency parses. Cross-text event chain overlap becomes a structural similarity signal orthogonal to SBERT alignment.

---

### 4. Narrative Schemas and Participants (Chambers & Jurafsky, ACL 2009)

**Core Concept.** Extends chains into full "narrative schemas" with all argument slots and jointly learned semantic roles — e.g., `arrested(POLICE,SUSPECT), convicted(JUDGE,SUSPECT)`.

**Palimpsest Relevance.** Most powerful structural fingerprint: two texts implementing the same schema are structurally related even if all surface language, names, and specific events differ.

**Technical Detail.** CBC clustering for argument types. Chain merging considers all argument slots jointly. Resolves false-positive class errors from the 2008 model.

**Action.** Index texts by schema activations as fast retrieval key before expensive SW alignment. Domain-specific schema libraries (law, mythology, war) enable genre-aware search.

---

### 5. Plot Units (Lehnert, Cognitive Science 1981)

**Core Concept.** Formal structures from three affect states (+, -, M) and four causal link types, whose configurations encode plot as a graph. Graph degree reveals centrality.

**Palimpsest Relevance.** Character-affect representation invariant to surface language and event content. Provides discrete, graph-isomorphism-based comparison complementing continuous alignment scores.

**Technical Detail.** 15 primitive plot units from 36 possible configurations. Complex units assembled from primitives. High-degree nodes = central concepts, correlating with human summarization behavior.

**Action.** Implement lightweight affect tagger (+/-/M per sentence per character) and plot unit assembler. Output graph serves as both visualization artifact and structural fingerprint via graph edit distance.

---

### 6. The Narrative Arc (Boyd et al., Science Advances 2020)

**Core Concept.** Function word rates (not content words) across five text segments identify three universal narrative processes — staging, plot progression, cognitive tension — with consistent arc shapes across ~40,000 narratives.

**Palimpsest Relevance.** Low-dimensional, content-free structural signature computed cheaply. Fast pre-filter: similar arc profiles → likely structurally related. Can normalize texts to same narrative "phase" before comparing.

**Technical Detail.** 15-dimensional vector (3 dimensions × 5 segments), within-text z-scored. Staging: articles + prepositions (monotone decline). Plot progression: pronouns + auxiliaries + negations (monotone rise). Cognitive tension: LIWC cognitive process words (quadratic arc). Robust across 3-to-10 segment partitions.

**Key Finding.** No evidence that adherence to normative arc structures correlates with popularity — structure and quality are independent.

**Action.** Compute 15-dimensional arc vector per text using ~900-word function word dictionary. Fast first-pass structural similarity metric for corpus-scale retrieval.

---

### 7. Church-Helfman Dotplot (1993)

**NOT PRESENT** in directory at time of analysis. (Note: file `Church-Helfman-dotplot-text-1993.pdf` was later found on disk.) Binary matrix where cell (i,j) filled if tokens at positions i,j are identical/similar. Produces diagonals (repeated passages), off-diagonal squares (topic recurrence), isolated points (hapax structure). Mathematical precursor to GNAT's SW heatmap and RQA methods.

---

### 8. Emotional Arcs of Stories (Reagan et al., 2016)

**Core Concept.** SVD + hierarchical clustering + SOM on sentiment time series of 1,327 Gutenberg texts identifies six archetypal emotional arcs: rags-to-riches, tragedy, man-in-a-hole, Icarus, Cinderella, Oedipus.

**Palimpsest Relevance.** Discrete classification system for emotional shape. Arc-type as search/grouping dimension. Divergent arc types may indicate intentional genre inversion (e.g., parody).

**Technical Detail.** 10,000-word sliding window with labMT sentiment dictionary. SVD on matrix A = UΣV^T. First 12 modes explain 80-94% of variance. Six arcs = first three SVD modes and negations. Ward's method with L1 distance. 8×8 SOM validation. All three methods converge.

**Key Finding.** Fall-rise (man-in-a-hole) and rise-fall-rise (Cinderella) arcs disproportionately represented among high-download books.

**Action.** Implement sliding-window hedonometer as standard preprocessing. Project onto six SVD modes at query time for fast corpus-scale clustering.

---

### 9. Text Recurrence Networks (Souza et al., USP, 2022)

**Core Concept.** Texts → mesoscopic networks (nodes = paragraphs, edges = tf-idf cosine similarity above threshold). Network measures distinguish genres and structural properties at multiple scales.

**Palimpsest Relevance.** Comparing recurrence networks captures whether texts share "semantic architecture" — complementing surface alignment.

**Technical Detail.** Pipeline: SVO triple extraction → tf-idf vectors → directed recurrence network → accessibility, symmetry, recurrence signature (edge-length distribution). Fiction exhibits higher long-range recurrence than non-fiction.

**Action.** Build paragraph-level recurrence networks per text. Long-range recurrence edges identify Chekhov's Gun patterns and thematic echoes.

---

### 10. SimDoc — Topic Sequence Alignment

**NOT PRESENT** at time of NLP agent analysis. (File `SimDoc-topic-alignment-1611.04822.pdf` later confirmed on disk in alignment/ directory.) DTW on LDA topic distributions for document-level alignment — coarser than sentence-level SW but faster.

---

### 11. Social Networks from Literary Fiction (Elson et al., ACL 2010)

**Core Concept.** Social networks from 60 nineteenth-century novels via quote detection, speaker attribution, and conversational partner identification.

**Palimpsest Relevance.** Character social network topology provides high-level structural fingerprint. Graph edit distance between character networks is a tractable structural similarity measure.

**Technical Detail.** Quote detection via pattern-based approaches. Statistical attribution model. Network features: density, components, degree, cliques, betweenness centrality.

**Key Finding.** No significant correlation between setting (rural/urban) and network density — challenges Bakhtin's chronotope consensus on actual evidence rather than cherry-picked examples.

**Action.** Build dialogue-based character networks as standard extraction step. Graph-level statistics become fast structural fingerprints.

---

### 12. Dynamic NLP with RQA (Dale et al., 2018)

**Core Concept.** Recurrence Quantification Analysis adapted to text: word sequence as discrete time series → Recurrence Plot → quantitative measures.

**Palimpsest Relevance.** Bridges visual Church dotplot and quantitative alignment scores. RQA measures = cheap scalar features for corpus-scale comparison.

**Technical Detail.** RP = {(i,j) : wi = wj}. RR ↔ unigram TTR. DET ↔ n-gram repetition. LAM = vocabulary "stickiness." Formally equivalent to n-gram analysis plus additional dynamical measures.

**Action.** Compute RQA measures (RR, DET, LAM, mean diagonal length) as cheap scalar features per text. DET distinguishes genre/literary fiction — normalization variable for cross-genre comparison.

---

## Bonus Papers

### Portrayal (Hoque et al., DIS 2023)
Per-chapter character trait matrix (actions, emotions, speech, appearance) as UI paradigm for character-level alignment results. User study with 12 writers/scholars validated identification of unintentional biases.

### SYMON — Movie Synopses DTW (Sun et al., 2023)
DTW on sentence embeddings validated for story-level alignment. "Privileged event granularity" concept useful for deciding narrative event representation level.

### Moretti — Network Theory, Plot Analysis (2011)
Cautionary tale: visualization alone produced "difficult to interpret" results. Always pair with computable metrics.

---

## Critical Missing Papers (at time of analysis)
- Church-Helfman (1993) — dotplot formalism (found on disk post-analysis)
- SimDoc (2016) — topic-sequence DTW (found on disk post-analysis)

# Annotated Research Index — Palimpsest Project

**Purpose**: Fast topical lookup across all research materials. Organized by conceptual question, not by paper. Each entry links to the source file on disk and summarizes what's relevant to Palimpsest development.

**Last updated**: 2026-06-06

---

## How to Use This Index

Each section corresponds to a conceptual question or development task. Entries are tagged:
- `[ON DISK]` — file downloaded, path given
- `[DOWNLOADING]` — acquisition in progress
- `[METADATA]` — bibliographic info only, not yet downloaded
- `[WEB]` — online resource, not downloaded
- `[DATASET]` — structured data file

---

## 1. ALIGNMENT THEORY AND ALGORITHMS

### What alignment means formally; scoring, gap models, complexity

- **Mäkinen et al., *Genome-Scale Algorithm Design* Ch. 6** `[ON DISK]`
  `alignment/Genome-scale algorithm design...Anna's Archive.pdf` pp. 83-130
  - Edit distance (Levenshtein), LCS, Needleman-Wunsch global alignment, Smith-Waterman local alignment, semi-local alignment, overlap alignment
  - Affine gap penalties, scoring matrices (BLOSUM concept), Kullback-Leibler divergence for deriving substitution scores
  - Myers' bitparallel algorithm (O(mn/w) for edit distance)
  - **Palimpsest relevance**: formal foundation for all text alignment. Ch. 6 is the theoretical backbone — read it for scoring matrix derivation (§6.4) and the geometric interpretation of alignment paths

- **GNAT: General Narrative Alignment Tool — Pial & Skiena (EMNLP 2023)** `[ON DISK]`
  `nlp-narrative/GNAT-narrative-alignment-2311.03627.pdf`
  - **Directly applies Smith-Waterman to narrative text alignment** with modern text similarity scoring
  - Uses Gumbel distribution for statistical significance testing of alignment scores
  - Applications: translation alignment, summary-to-book mapping, plagiarism detection
  - **Palimpsest relevance**: THIS IS THE CLOSEST PRIOR ART to Palimpsest's core alignment module. Must-read for scoring function design and evaluation methodology

- **SimDoc: Topic Sequence Alignment — Maheshwari et al. (K-CAP 2017)** `[ON DISK]`
  `nlp-narrative/SimDoc-topic-alignment-1611.04822.pdf`
  - Applies Smith-Waterman to LDA topic sequences
  - Models "thematic flow" as a sequence alignment problem
  - **Palimpsest relevance**: validates the approach of treating topic evolution as an alignable sequence; directly applicable to our paragraph-level topic features

- **Foldseek — van Kempen et al. (Nature Biotech 2023)** `[METADATA]`
  DOI: 10.1038/s41587-023-01773-0
  - 3Di structural alphabet: encodes 3D protein structure as 1D sequence of 20 discrete states
  - 4-5 orders of magnitude speedup over TM-align by reducing structural comparison to sequence comparison
  - **Palimpsest relevance**: paradigm-defining inspiration for the narrative alphabet concept. The key insight: local geometric interactions capture enough structural information for fast comparison

- **Smith & Waterman (1981)** — Original local alignment algorithm `[METADATA]`
  DOI: 10.1016/0022-2836(81)90087-5
  - **Palimpsest relevance**: foundational algorithm; GNAT builds directly on this

---

## 2. STRUCTURE DISCOVERY IN TEXT

### How to find narrative structure computationally

- **Reagan et al., "Emotional Arcs of Stories" (2016)** `[ON DISK]`
  `nlp-narrative/Reagan-emotional-arcs-stories-1606.07772.pdf`
  - SVD decomposition of sentiment trajectories discovers 6 archetypal shapes across 1,327 Project Gutenberg stories
  - Sentiment computed via hedonometer (sliding window of 10K words)
  - Self-Organizing Maps (SOM) validate cluster structure
  - Controls: shuffled text produces no clusters — structure is real
  - **Key finding**: the fabula/syuzhet distinction means emotional arc ≠ plot. "Overcoming the Monster" and "Rags to Riches" may have similar arcs but different plots
  - **Palimpsest relevance**: demonstrates that unsupervised decomposition discovers meaningful literary structure. The SVD approach is directly applicable to our feature vectors

- **Boyd, Blackburn, Pennebaker — "The Narrative Arc" (Science Advances 2020)** `[ON DISK]`
  `nlp-narrative/Boyd-narrative-arc-2020.pdf`
  - Three universal arc components: staging, plot progression, cognitive tension
  - Validated across ~60,000 texts via LIWC linguistic categories
  - **Palimpsest relevance**: provides a complementary framework to Reagan — LIWC-based features vs. sentiment-based. Could add staging/progression/tension as additional signal features in our pipeline

- **Chambers & Jurafsky — "Unsupervised Learning of Narrative Event Chains" (ACL 2008)** `[ON DISK]`
  `nlp-narrative/Chambers-narrative-event-chains-P08-1090.pdf`
  - Learns chains of events linked by a common protagonist from unlabeled text
  - Introduces "narrative cloze" evaluation: given a partial chain, predict the next event
  - **Palimpsest relevance**: foundational for computational narratology; event chains are structure-objects at the plot level

- **Chambers & Jurafsky — "Narrative Schemas and Participants" (ACL 2009)** `[ON DISK]`
  `nlp-narrative/Chambers-narrative-schemas-P09-1068.pdf`
  - Extends to full schemas with typed participant roles
  - **Palimpsest relevance**: schemas are the narrative equivalent of gene regulatory circuits — multi-entity coordinated functional units

- **Lehnert — "Plot Units" (Cognitive Science 1981)** `[ON DISK]`
  `nlp-narrative/Lehnert-plot-units-1981.pdf`
  - Affect-state graph formalism: positive/negative/neutral mental states connected by causal links
  - Plot structure = topology of affect-state graph
  - **Palimpsest relevance**: earliest computational representation of narrative structure as a graph. Plot units could be structure-objects in our alignment framework

---

## 3. TEXT PROCESSING AND FEATURE EXTRACTION

### NLP pipelines for literary text; dialog, characters, entities

- **BookNLP — Bamman et al. (ACL 2014 + GitHub 2021)** `[ON DISK]`
  `nlp-narrative/BookNLP-bayesian-character-P14-1035.pdf`
  GitHub: https://github.com/booknlp/booknlp
  - End-to-end NLP pipeline for books: NER, coreference resolution, quotation attribution, supersense tagging
  - Bayesian mixed-effects model for character typing
  - 2021 Python rewrite trained on LitBank (annotated literary corpus)
  - **Palimpsest relevance**: the gold-standard pipeline for literary entity/dialog extraction. Should integrate with our text_segmenter output

- **Piper, *Enumerations* (2018)** `[ON DISK]`
  `nlp-narrative/Enumerations...Anna's Archive.pdf`
  - Ch. 1 "Punctuation": computational analysis of how punctuation creates meaning in poetry
  - Ch. 2 "Plot": operationalizing plot via topic modeling trajectories
  - Ch. 3 "Topoi": LDA topic modeling on 230K poems — topics as "generalized associational patterns"
  - Ch. 4 "Fictionality": what makes fictional language computationally distinguishable from non-fiction
  - Ch. 5 "Characterization": constraint-based model of character identity
  - **Palimpsest relevance**: each chapter demonstrates a different layer of the textual hierarchy being computationally operationalized. Ch. 3 (Topoi) is directly applicable to our topic-flow features; Ch. 5 (Characterization) complements BookNLP's character extraction

- **Jockers, *Macroanalysis* (2013)** `[ON DISK]`
  `nlp-narrative/Macroanalysis...Anna's Archive.pdf`
  - Topic modeling, stylometry, sentiment analysis at corpus scale
  - Created the Syuzhet R package for emotional arc extraction
  - "Macroanalysis" = literary equivalent of distant reading
  - **Palimpsest relevance**: methodological framework for corpus-scale literary analysis. Read for topic modeling methodology and the stylometry approach

- **Stoltz & Taylor, *Mapping Texts* (2023)** `[ON DISK]`
  `nlp-narrative/Mapping Texts...Anna's Archive.pdf`
  - Systematic coverage of modern computational text analysis for social sciences
  - Bridges NLP methods with interpretive frameworks
  - **Palimpsest relevance**: practical reference for text analysis implementation choices

- **Syuzhet R package — Jockers (2015)** `[WEB]`
  GitHub: https://github.com/mjockers/syuzhet
  - Sentiment-based plot arc extraction with DCT/Fourier smoothing for normalization
  - **Palimpsest relevance**: our signal_extractor sentiment features could implement this smoothing approach

---

## 4. SELF-SIMILARITY, RECURRENCE, AND INFORMATION THEORY

### Dotplots, recurrence plots, entropy measures for text

- **Church & Helfman — "Dotplot" (1993)** `[ON DISK]`
  `alignment/Church-Helfman-dotplot-text-1993.pdf`
  - **Foundational**: applies DNA homology dotplot visualization to text
  - Self-similarity matrix reveals repetition, refrain, structural boundaries
  - Applied to millions of lines of text and code
  - **Palimpsest relevance**: the dotplot is the simplest possible alignment visualization for text — our first prototype visualization should be a text self-similarity dotplot

- **Text Recurrence Networks — Amancio et al. (2022)** `[ON DISK]`
  `nlp-narrative/text-recurrence-networks-2201.06665.pdf`
  - TF-IDF cosine similarity between paragraphs → recurrence network
  - Classifies literary genres from network topology
  - **Palimpsest relevance**: validates self-similarity approach for literary analysis; the recurrence network metrics (determinism, entropy, laminarity) could be added to our signal_extractor

- **Dynamic NLP with RQA (2018)** `[ON DISK]`
  `nlp-narrative/dynamic-nlp-rqa-1803.07136.pdf`
  - Connects recurrence quantification analysis from dynamical systems to NLP
  - **Palimpsest relevance**: theoretical bridge between information theory and text structure detection

- **O'Neill, *The Comedy of Entropy* (1990)** `[ON DISK]`
  `nlp-narrative/O'Neill, Patrick/The comedy of entropy.../...Anna's Archive.pdf`
  - Information-theoretic approach to narrative: Shannon entropy in literary structure
  - **Palimpsest relevance**: theoretical grounding for our char_entropy and word_entropy features

- **Gray, *Entropy and Information Theory* (2011)** `[ON DISK]`
  `alignment/Robert M. Gray (auth.)/Entropy and information theory/...Anna's Archive.pdf`
  - Mathematical foundation: entropy, mutual information, rate-distortion theory
  - **Palimpsest relevance**: formal grounding for "information content of structure" question (see conceptual framework §5)

---

## 5. VISUALIZATION OF TEXT AND NARRATIVE

### Circos, storylines, network visualizations, genome browsers, interactive tools

- **Swinehart/Samizdat — Infinite Digest datasets** `[DATASET]`
  `datasets/swinehart/infinite-digest/` — 4 CSVs:
  - `chapters.csv` (202 rows): narrative position, chronological sequence, pages, endnote refs, year/month, plotline tags, themes
  - `plotlines.csv` (140 rows): chronological events with character-tagged capsules (`<name>text</>` format)
  - `endnotes.csv` (388 rows): reference page, note page range, note length
  - `bios.csv` (122 rows): character slugs, names, group affiliations, biographical summaries
  - **Palimpsest relevance**: gold-standard multi-layer annotation for a structurally complex novel. Use for prototyping and validating alignment/visualization tools. The pos↔seq mapping in chapters.csv IS the fabula/syuzhet reordering function

- **Swinehart report (Report 03)** `[ON DISK]`
  `reports/03-swinehart-narrative-visualization-research.md`
  - CYOA decision graphs, Infinite Jest endnote arcs, scrollable SvelteKit design
  - **Key takeaway**: best work combines structural data with encodings that honor reading experience

- **Circos — Krzywinski et al. (Genome Research 2009)** `[METADATA]`
  DOI: 10.1101/gr.092759.109
  - Circular ideogram with ribbons for 3-dimensional correspondence data
  - **Palimpsest relevance**: candidate visualization for multi-text alignment display (text positions on arc, alignment links as ribbons)

- **NG-Circos — Cui et al. (2020)** `[METADATA]`
  DOI: 10.1093/nargab/lqaa069
  - JavaScript-based interactive Circos with 21 functional modules
  - **Palimpsest relevance**: directly usable as web visualization component

- **Schenk, *Circos Data Visualization How-To* (2012)** `[ON DISK]`
  `visualization/Circos data visualization...Anna's Archive.epub`
  - Practical guide to Circos configuration
  - **Palimpsest relevance**: reference for implementing text-Circos visualizations

- **Story Charting with Networks (2024)** `[ON DISK]`
  `visualization/story-charting-networks-2406.14734.pdf`
  - Network visualization for narrative story structure
  - **Palimpsest relevance**: character network visualization techniques

- **NetworkNarratives — Data Tours (2023)** `[ON DISK]`
  `visualization/NetworkNarratives-data-tours-2303.06456.pdf`
  - Guided exploration of network data through narrative sequences
  - **Palimpsest relevance**: interaction design for narrative network exploration

- **Storyline Crossing Minimization (2024)** `[ON DISK]`
  `visualization/storyline-crossing-minimization-2409.02858.pdf`
  - ILP formulation for minimizing crossings in storyline visualizations
  - **Palimpsest relevance**: algorithmic foundation for storyline layout (complements Tanahashi & Ma)

- **Story Ribbons — Yeh et al. (2025)** `[ON DISK]`
  `visualization/StoryRibbons-LLM-storyline-2508.06772.pdf`
  - LLM-powered extraction of narrative structure for storyline visualization
  - **Palimpsest relevance**: state-of-the-art in automated narrative viz; uses LLMs where our pipeline uses classical NLP

- **Tanahashi & Ma — Storyline Visualization Design (IEEE TVCG 2012)** `[METADATA]`
  DOI: 10.1109/TVCG.2012.212
  - Foundational paper on automated storyline layout (xkcd → formalization)
  - **Palimpsest relevance**: defines the crossing minimization problem we'd need to solve for storyline views

- **Kim et al. — Story Curves: Nonlinear Narratives (IEEE TVCG 2018)** `[ON DISK]`
  `visualization/Kim-StoryCurves-nonlinear-narratives-2018.pdf`
  - Visualizing non-chronological narrative order
  - **Palimpsest relevance**: directly relevant to visualizing the pos↔seq mapping from the Swinehart data

- **JBrowse 2 — Diesh et al. (Current Protocols 2024)** `[METADATA]`
  DOI: 10.1002/cpz1.1120
  - Modular genome browser: multi-track, zoomable, plugin-based (TypeScript/React)
  - **Palimpsest relevance**: architectural template for a "text browser" with annotation tracks

- **Jänicke et al. — Close and Distant Reading Survey (EuroVis 2015)** `[ON DISK]`
  `visualization/Janicke-close-distant-reading-survey-EuroVis2015.pdf`
  - Broad survey of digital humanities visualization approaches (500 citations)
  - **Palimpsest relevance**: literature review for visualization design choices

- **Yau, *Visualize This* (2024)** `[ON DISK]`
  `visualization/Visualize This...Anna's Archive.pdf`
  - Comprehensive data visualization guide including text/narrative examples
  - **Palimpsest relevance**: general visualization reference

---

## 6. CLOSE AND DISTANT READING METHODOLOGY

### Frameworks for computational literary analysis

- **Moretti, *Distant Reading* (2013)** `[ON DISK]`
  `nlp-narrative/Distant Reading...Anna's Archive.pdf`
  - Manifesto for computational literary studies
  - "Distant reading" as counterpoint to close reading: patterns invisible at individual text level
  - **Palimpsest relevance**: philosophical framework for why we're building these tools

- **Moretti, "Network Theory, Plot Analysis" (2011)** `[ON DISK]`
  `nlp-narrative/Moretti-network-theory-plot-analysis.pdf`
  - Character network analysis on Shakespeare and Dickens
  - Honest conclusion: visualization alone produced results "difficult to interpret"
  - **Palimpsest relevance**: cautionary tale — always pair visualization with computable metrics. Moretti's honest failure is instructive

- **Underwood, *Distant Horizons* (2019)** `[ON DISK]`
  `nlp-narrative/Distant Horizons...Anna's Archive.pdf`
  - Predictive modeling of genre boundaries, narrative pace, literary prestige over 300 years
  - Bamman's gender-inference tools applied to character analysis
  - Ch. 2 "Life Spans of Genres": genre as probabilistic boundary, not hard category
  - Ch. 5 "Risks of Distant Reading": methodological self-critique
  - **Palimpsest relevance**: demonstrates rigorous quantitative literary analysis. The predictive modeling framework (distinguishing fiction from biography by features) is directly applicable to our classification tasks

- **Eve, *Close Reading with Computers* (2019)** `[ON DISK]`
  `nlp-narrative/Close Reading with Computers...Anna's Archive.pdf`
  - Computational methods on Cloud Atlas: textual scholarship comparing variant editions
  - Production flowchart for textual stemma (manuscript phylogeny)
  - POS-tag analysis reveals genre signals across the nested narratives
  - **Palimpsest relevance**: textual scholarship IS text alignment. Eve's variant-edition comparison is exactly the problem our alignment module solves. His methodology is our use case

- **Krautter, *The Scales of (Computational) Literary Studies* (2023)** `[METADATA — not downloaded]`
  Anna's Archive MD5: 021c19b4be2f8e0f103232600adf5849
  - "Scalable reading": moving fluidly between close and distant
  - **Palimpsest relevance**: theoretical framework for the text browser's semantic zoom

- **Toolan, *Making Sense of Narrative Text* (2016)** `[ON DISK]`
  `nlp-narrative/Making Sense of Narrative Text...Anna's Archive.pdf`
  - Cognitive approach to narrative comprehension: situation models, repetition, picturing
  - **Palimpsest relevance**: how readers construct mental models — relevant to designing visualizations that support (rather than replace) reading

---

## 7. CHARACTER ANALYSIS AND SOCIAL NETWORKS

### Character extraction, network construction, dialog attribution

- **CHAPLIN — Marazzato & Caroli (2014)** `[ON DISK]`
  `alignment/CHAPLIN-character-place-networks-1402.4259.pdf`
  - Automated extraction of character/place networks from literary text
  - **Palimpsest relevance**: character network extraction pipeline; tested with our text pipeline

- **Portrayal — Interactive Character Analysis (2023)** `[ON DISK]`
  `nlp-narrative/Portrayal-character-analysis-2308.04056.pdf`
  - Interactive visual tool for analyzing character portrayal in narrative
  - **Palimpsest relevance**: UI/UX patterns for character exploration interface

- **Elson, Dames, McKeown — Social Networks from Literary Fiction (ACL 2010)** `[ON DISK]`
  `nlp-narrative/Elson-social-networks-fiction-ACL2010.pdf`
  - Dialogue-based social network extraction from novels
  - Most-cited character network paper across our collection
  - **Palimpsest relevance**: standard methodology for character network construction

- **Bamman, Lewke, Mansoor — Literary Coreference Dataset (LREC 2020)** `[ON DISK]`
  `nlp-narrative/Bamman-literary-coreference-dataset-LREC2020.pdf`
  - Annotated coreference in English literature (29,103 mentions, 100 works 1719-1922)
  - **Palimpsest relevance**: training/evaluation data for literary NER + coreference

- **Lubars et al. — IJ Dynamic Character Network (2018)** `[WEB]`
  http://blubars.github.io/project/2018/12/20/complex-infinite-jest.html
  - Dynamic network analysis of Infinite Jest characters
  - Small-world effect confirmed; non-chronological sequencing is structurally optimal
  - **Palimpsest relevance**: provides network metrics we can compute and compare using the Swinehart datasets

- **Burn, *David Foster Wallace's Infinite Jest: A Reader's Guide* (2nd ed., 2012)** `[ON DISK]`
  `nlp-narrative/Burn, Stephen J/...Reader's Guide.../...Anna's Archive.pdf`
  - Chapter-by-chapter reading companion with character glossary, thematic analysis, timeline
  - **Palimpsest relevance**: gold-standard human annotation of IJ structure. Burn's character/event cross-references are the kind of structural data our tools should help generate

- **Carlisle, *Elegant Complexity* (2007)** `[ON DISK]`
  `nlp-narrative/Greg Carlisle/Elegant complexity.../...Anna's Archive.pdf` (29.6MB)
  - Most detailed structural analysis of IJ: scene-by-scene annotation, chronologies in appendices
  - Source data for Swinehart's Infinite Digest project
  - **Palimpsest relevance**: the definitive human-annotated structural decomposition of a complex novel. Appendix chronologies directly comparable to our computed timeline alignment

- **Cordes, "How to Read Infinite Jest Chronologically" v1.3** `[DATASET]`
  `datasets/swinehart/IJ-chronology-v1.3.pdf` (20pp)
  - Reshuffles all IJ scenes into chronological order with page references and reasoning
  - **Palimpsest relevance**: the pos↔seq mapping made explicit. Represents the fabula reconstruction that alignment algorithms should approximate

- **Feene, "And Like But So: A Character Guide to Infinite Jest"** `[DATASET]`
  `datasets/swinehart/IJ-character-guide-feene.md` (1500 lines, A-Z)
  - Comprehensive character guide with descriptions, page references, relationships, spoiler-tagged revelations
  - Archived from ISU (2004) via Wayback Machine
  - **Palimpsest relevance**: manually built domain ontology for IJ. Exactly the kind of glossary that Palimpsest's entity extraction should aspire to generate (with human verification)

- **CPudney — IJ Scene Annotations** `[DATASET]`
  `datasets/swinehart/cpudney-infinite-jest.csv` (190 scenes)
  - Independent annotation with Chapter, Scene, Page, Year, DayName, MonthDay, CharactersPresent, Synopsis
  - CC BY-SA 3.0, sourced from Keith O'Neill and the IJ Wiki
  - **Palimpsest relevance**: second independent annotator → enables inter-annotator agreement testing on scene boundaries and character presence

---

## 8. CULTURAL EVOLUTION AND TEXTUAL PHYLOGENETICS

### How texts change through transmission, adaptation, translation

- **da Silva & Tehrani — "Phylogenetic Analyses of Indo-European Folktales" (2016)** `[METADATA]`
  Royal Society Open Science 3(1)
  - Computational phylogenetics applied to folktale transmission
  - **Palimpsest relevance**: validates the text↔genome analogy for evolutionary analysis of literary traditions

- **Eve, *Close Reading with Computers* — Production Flowchart (p. 49)** `[ON DISK]`
  - Textual stemma for Cloud Atlas editions: P (UK Sceptre) → manuscript → E (US Random House)
  - Demonstrates how editorial "mutations" accumulate across transmission
  - **Palimpsest relevance**: textual criticism IS phylogenetics for books. Eve's production flowchart is literally a manuscript phylogeny

---

## 9. ACQUISITION STATUS (Updated 2026-06-06)

### Now on disk (resolved since initial index)

| Paper | Path |
|---|---|
| Elson, Dames, McKeown (ACL 2010) — Social Networks from Fiction | `nlp-narrative/Elson-social-networks-fiction-ACL2010.pdf` |
| Kim et al. (IEEE TVCG 2018) — Story Curves: Nonlinear Narratives | `visualization/Kim-StoryCurves-nonlinear-narratives-2018.pdf` |
| Bamman et al. (LREC 2020) — Literary Coreference Dataset | `nlp-narrative/Bamman-literary-coreference-dataset-LREC2020.pdf` |
| O'Neill (1990) — Comedy of Entropy | `nlp-narrative/O'Neill, Patrick/The comedy of entropy.../...Anna's Archive.pdf` |
| Gray (2011) — Entropy and Information Theory | `alignment/Robert M. Gray (auth.)/Entropy and information theory/...Anna's Archive.pdf` |
| Mann & Thompson (1987) — RST original | `nlp-narrative/Mann-Thompson-RST-1987.pdf` |
| Jänicke et al. (EuroVis 2015) — Close and Distant Reading Survey | `visualization/Janicke-close-distant-reading-survey-EuroVis2015.pdf` |

### Still missing

| Priority | Paper | Status |
|---|---|---|
| **MED** | Tanahashi & Ma (IEEE TVCG 2012) — Storyline Visualization Design | IEEE paywalled, no preprint found; key ideas covered by ILP crossing minimization paper on disk |
| **MED** | Krautter (2023) — Scales of Computational Literary Studies | Anna's Archive upstream unavailable (MD5: 021c19b4be2f8e0f103232600adf5849); "scalable reading" concept discussed in Underwood, Piper, Jockers |
| **LOW** | Carlson et al. (2003) — RST Discourse Treebank | Paywalled (Springer); Marcu's book on disk covers RST discourse parsing |

---

## 10. DEEP READING REPORTS

Structured Palimpsest-relevance analyses for all papers/books, organized by domain:

| Report | Path | Papers |
|---|---|---|
| NLP & Narrative | `domain-synthesis/03-deep-read-nlp-narrative.md` | 12 papers (GNAT, BookNLP, Chambers ×2, Lehnert, Boyd, Reagan, RQA, recurrence networks, Elson, Portrayal, SYMON) |
| Genomics | `domain-synthesis/04-deep-read-genomics.md` | 10 papers (Hi-C, TADs, Rao, Bonev & Cavalli, ENCODE, Roadmap, Barabási ×2, Senft & Macfarlan, Bartel) |
| Literary Studies | `domain-synthesis/05-deep-read-literary-studies.md` | 8 books (Piper, Underwood, Eve, Moretti, Jockers, Toolan, Carlisle, Burn) |
| Visualization | `domain-synthesis/06-deep-read-visualization.md` | 7 sources (StoryRibbons, story charting networks, NetworkNarratives, ILP crossing minimization, Circos, Yau, Swinehart report) |

---

*Index compiled from on-disk materials, PubMed metadata, ACL Anthology, arXiv, and Anna's Archive. Cross-reference with master-bibliography.md for full citation details. Last updated 2026-06-06.*

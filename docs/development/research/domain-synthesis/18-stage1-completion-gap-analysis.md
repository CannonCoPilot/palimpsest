# Stage 1 Completion: Research Expansion Gap Analysis

**Date**: 2026-06-08
**Status**: Stage 1 COMPLETE — ready for Stage 2

---

## Summary

Stage 1 of the Palimpsest back-to-drawing-board overhaul is complete. The research corpus has grown from 49 sources to **118 PDFs on disk** covering 117 bibliographic entries across four domains, plus 5 datasets, 5 web resources, and 11 low-priority items identified but not yet acquired. This exceeds the 75-source threshold set in the completion criteria (00-back-to-drawing-board.md §Completion Criteria #1).

---

## Coverage Assessment by Domain

### 1a. Computational Linguistics — COMPREHENSIVE

| Subdomain | Coverage | Key Sources |
|-----------|----------|-------------|
| **Distributional semantics** | Excellent | Harris 1954, Deerwester/LSA 1990, Mikolov/Word2Vec 2013, Pennington/GloVe 2014, Turney & Pantel 2010 survey |
| **Contextual embeddings** | Excellent | Vaswani/Transformers 2017, Devlin/BERT 2018 |
| **Topic modeling** | Good | Blei/LDA 2003, Schöch 2017 (genre-topic) |
| **Dependency parsing** | Good | Tesnière 1959 (foundational), Nivre 2006 (inductive), Palmer/PropBank 2005 |
| **Discourse analysis** | Good | Mann-Thompson/RST 1987, Prasad/PDTB 2008, Hearst/TextTiling 1997 |
| **Annotation theory** | Excellent | Hovy & Lavid 2010, Artstein & Poesio 2008, Pustejovsky & Stubbs 2012, INCEpTION 2018 |
| **Computational stylistics** | Good | Burrows/Delta 2002, Eder/stylo 2016 |
| **Text alignment & reuse** | Excellent | Gale-Church 1993, CollateX 2015, Büchler 2016, GNAT 2023, SimDoc 2017, Church/dotplot 1993 |
| **Intertextuality theory** | Good | Kristeva 1966, Genette/Palimpsests 1982 |
| **Narrative structure** | Excellent | Chambers & Jurafsky 2008/2009, Lehnert 1981, Boyd 2020, Reagan 2016, CHAPLIN 2014, BookNLP 2014 |
| **Digital humanities** | Excellent | Moretti 2011/2013, Jockers 2013, Underwood 2019, Piper 2018, Eve 2019, Stoltz & Taylor 2023, Elson 2010 |
| **Information theory in text** | Good | Gray 2011, O'Neill 1990, RQA (2018, 2022) |

**Remaining gap**: Firth 1957 (foundational distributional semantics, pre-Harris). Low priority — Harris 1954 covers the same intellectual territory with the computational specification.

### 1b. Genomic Analysis — COMPREHENSIVE

| Subdomain | Coverage | Key Sources |
|-----------|----------|-------------|
| **Sequence alignment algorithms** | Excellent | NW 1970, SW 1981, BLAST 1990, PSI-BLAST 1997, ClustalW 1994, T-Coffee 2000, MUSCLE 2004, MUMmer 2004 |
| **Alignment textbooks** | Excellent | Durbin et al. 1998, Mäkinen et al. 2023 |
| **Homology & evolution** | Good | Koonin 2005, Hardison 2003 |
| **Genome annotation** | Excellent | Sequence Ontology 2005, Gene Ontology 2000, GENCODE 2012 |
| **Gene finding & HMMs** | Good | GENSCAN 1997, Eddy/profile HMMs 1998 |
| **Chromatin state discovery** | Excellent | ChromHMM 2010 + 2012, Segway 2012 |
| **3D genome architecture** | Excellent | Hi-C 2009, TADs 2012, Rao 2014, Bonev & Cavalli 2016 |
| **ENCODE/Epigenomics** | Excellent | ENCODE Phase II 2012, Roadmap 2015 |
| **Transposable elements** | Good | RepeatModeler2 2020, Senft & Macfarlan 2021 |
| **Structural variation** | Good | Alkan et al. 2011 |
| **Network biology** | Good | Barabási & Oltvai 2004, Barabási 2016 |
| **Regulatory elements** | Good | Bartel/miRNAs 2009 |

**Remaining gaps**: Fitch 1970 (homology/analogy — covered conceptually by Koonin), MEME/Bailey 1994 (motif discovery — covered by Eddy HMMs), Pan-Genomics Consortium 2018 (covered by Alkan structural variation). All low priority.

### 1c. Visualization — COMPREHENSIVE

| Subdomain | Coverage | Key Sources |
|-----------|----------|-------------|
| **Foundational theory** | Excellent | Bertin 1967, Tufte 1983, Cleveland & McGill 1984, Wilkinson 2005, Wickham 2010, Munzner 2014 |
| **Genome browsers** | Excellent | UCSC 2002, IGV 2011, JBrowse 2 2023, HiGlass 2018, Circos 2009 |
| **Interaction techniques** | Good | Furnas/fisheye 1986, Buja/brushing 1996, Roberts/CMV 2007 |
| **Graph visualization** | Good | Holten/edge bundling 2006, Shneiderman/treemaps 1992 |
| **Narrative visualization** | Excellent | Wattenberg/Word Tree 2008, Tanahashi/storyline 2012, Keim/pixel displays 2000, Jänicke 2015 survey, Kim/StoryCurves 2018, StoryRibbons 2025, NetworkNarratives 2023 |
| **Practice & pedagogy** | Good | Fry 2008, Yau 2024 |

**Remaining gaps**: L'Yi/Gosling 2022 (grammar-based genomic viz — closest analog to Palimpsest, couldn't download due to Anna's Archive DOI mismatch). Keim & Oelke/Literature Fingerprinting 2007, Paley/TextArc 2002 (both covered by Jänicke 2015 survey). Medium priority for Gosling only.

### 1d. Swinehart & Conceptual Underpinnings — COMPLETE

Report 03 provides comprehensive analysis of Swinehart's CYOA and Infinite Digest projects. Deep analysis document (doc 17) connects Swinehart's work to the broader research corpus and identifies transferable principles for Palimpsest. Key insight preserved: Hi-C contact maps are the genomic analogue of endnote arc diagrams; the phenomenological approach (honoring the reader's experience rather than abstracting it away) is the design philosophy Palimpsest should adopt.

### 1e. Bibliography Maintenance — COMPLETE

Master bibliography updated to 117 entries organized by domain. 11 low-priority items listed as manual acquisition with coverage notes explaining why each is non-essential.

---

## Completion Criteria Check

| Criterion | Status |
|-----------|--------|
| Research corpus >75 sources with chapter-level book citations | **PASS**: 118 PDFs, 117 bibliography entries |
| Bibliography updated with full citations | **PASS**: master-bibliography.md rewritten 2026-06-08 |
| Gap analysis document | **PASS**: this document |
| Download priority established | **PASS**: download-paper.py script with 7-strategy fallback chain |

---

## Key Conceptual Discoveries from Stage 1

These emerged from the research expansion and will inform all subsequent stages:

1. **Literary orthology/paralogy** (from Fitch 1970 / Koonin 2005): Texts can be "orthologous" (descended from a common ancestor through divergence) or "paralogous" (duplicated within the same tradition and diverging in function). This maps directly to comparative literary analysis.

2. **LitHMM** (from ChromHMM / Ernst & Kellis 2010, 2012): Train a multivariate HMM on multiple textual features simultaneously to discover latent "passage states" — not predefined categories, but emergent functional roles. This is the core Palimpsest innovation.

3. **Sequence Ontology → Literary Feature Ontology** (from Eilbeck 2005): A controlled vocabulary for literary features analogous to SO terms for genomic features. Enables interoperability and formal reasoning about annotation types.

4. **TextHiC** (from Lieberman-Aiden 2009): Build passage-pair similarity matrices to reveal thematic compartmentalization, analogous to A/B genome compartments. Hi-C contact maps visualize long-range narrative connections.

5. **The MAKER evidence model** (from genome annotation): Combine ab initio ML predictions with textual evidence and cross-text parallels, with human curation adjudicating disagreements. This is the annotation architecture.

6. **Perspectival modeling** (from Underwood 2019): Every classification reflects a specific historical/critical perspective. Palimpsest should never present a single authoritative reading — always show which lens generated the analysis.

7. **Base/X architecture** (from vision synthesis doc 11): Universal tracks computed automatically (Base), with per-text adaptive extensions (X) that emerge from reader-AI collaboration. The genome's gene prediction → manual curation → community database pipeline is the model.

---

## Transition to Stage 2

Stage 1 is complete. The research corpus is comprehensive across all four domains. The conceptual discoveries listed above will serve as the intellectual backbone for Stage 2 (Domain Synthesis), where the 21 existing documents will be grounded in this expanded research base and synthesized into a unified conceptual foundation.

**Next steps**:
- Stage 2a: Write comprehensive conceptual foundation document (doc 19)
- Stage 2b: Research-ground all domain synthesis docs against 118-paper corpus
- Stage 2c: Cross-document consistency review

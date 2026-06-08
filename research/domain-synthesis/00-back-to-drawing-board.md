# Palimpsest: Back to the Drawing Board — Process Document

**Created**: 2026-06-07
**Purpose**: Master process reference for the comprehensive research, planning, and documentation overhaul. All work across multiple sessions refers back to this document for scope, sequence, and completion criteria.

---

## Overview

This document defines a four-stage overhaul of all Palimpsest research, planning, and implementation documentation. The overhaul was triggered by the M1.3b checkpoint review (doc 16), which revealed that while the codebase is functionally complete through M1.3b, the documentation foundation — research corpus, domain synthesis, vision, planning, and specifications — has significant gaps that will compound as the project scales.

The goal is not to start over, but to deepen and strengthen: fill knowledge gaps, ground the vision in rigorous scholarship, and produce planning documents so detailed that implementation becomes mechanical.

---

## Stage 1: Research Expansion

### 1a. Computational Linguistics

**Current state**: 17 papers covering narrative analysis (Moretti, Jockers, Underwood, Piper, Eve), narrative structure (Boyd, Chambers, Lehnert), NLP tools (BookNLP, CHAPLIN, Portrayal, GNAT), and text similarity (Church dotplot, SimDoc, RQA).

**Gaps to fill**:
- **Semantics**: Distributional semantics, word embeddings theory (Mikolov, Pennington GloVe), contextual embeddings (Devlin BERT, Vaswani Transformers), semantic role labeling
- **Syntax**: Dependency parsing theory (Tesnière, Mel'čuk), constituency parsing, syntactic complexity measures, RST beyond Mann-Thompson
- **Text alignment**: Sequence alignment algorithms applied to text (Smith-Waterman analogues), plagiarism detection alignment, translation alignment (Gale-Church), collation algorithms (CollateX)
- **Text annotation**: Annotation theory and praxis (Hovy & Lavid, Pustejovsky & Stubbs "Natural Language Annotation"), annotation schemes (UIMA, GATE, WebAnno/INCEpTION), inter-annotator agreement, annotation as interpretation
- **Comparative literature methods**: Intertextuality theory (Kristeva, Genette), distant reading methodology debates, canon formation studies, computational stylistics (Burrows, Eder)
- **Discourse analysis**: Rhetorical Structure Theory extensions, discourse parsing (PDTB, SDRT), coherence relations, topic segmentation (Hearst TextTiling)
- **Literary features**: Motif detection, allusion detection, style transfer analysis, readability metrics history, narrative voice classification

**Deliverables**:
- [ ] 15-25 new papers/books downloaded to `research/papers/`
- [ ] Bibliography updated with full citations
- [ ] Gap analysis document: what we found vs. what remains

### 1b. Genomic Analysis

**Current state**: 7 genomic papers (ENCODE, Hi-C, TADs, 3D genome, epigenomics, network biology, transposable elements), plus alignment algorithm textbook (Mäkinen).

**Gaps to fill**:
- **Sequence structure**: Genome architecture (chromatin domains, regulatory elements, non-coding RNA), structural variation, repeat elements, genome organization principles
- **Sequence alignment**: Foundational algorithms (Needleman-Wunsch, Smith-Waterman, BLAST, FASTA), multiple sequence alignment (ClustalW, MUSCLE, T-Coffee), whole-genome alignment (MUMmer, LASTZ), progressive alignment theory
- **Ontological meaning of alignment**: What does "alignment" mean biologically? Homology vs. analogy, orthology vs. paralogy, conserved synteny, convergent evolution. How alignment reveals function, history, and constraint.
- **Annotation concepts**: What IS a genome annotation? Feature types (genes, regulatory elements, repeats, variants). Structural vs. functional annotation. Evidence codes (IEA, ISS, TAS, IDA). GFF3/GTF/BED formats and their semantics. Ab initio prediction (gene finders, HMMs) vs. evidence-based annotation. The annotation lifecycle.
- **Predictive methodologies**: How agnostic computational methods find features: HMMs for gene finding (GENSCAN, Augustus), motif discovery (MEME), chromatin state learning (ChromHMM, Segway), de novo repeat finding (RepeatModeler). What these teach about finding literary features without a priori definitions.
- **Under-represented domains**: Population genomics, phylogenomics, metagenomics, epigenomics methodology, single-cell genomics, long-read sequencing and assembly, pangenomics

**Deliverables**:
- [ ] 15-25 new papers downloaded
- [ ] Bibliography updated
- [ ] Particular focus on ChromHMM, annotation ontologies (Sequence Ontology), and alignment algorithm foundations

### 1c. Visualization

**Current state**: 7 visualization papers. Circos represented only by metadata (Krzywinski 2009) — no full paper downloaded. Yau's FlowingData and Schenk's Circos How-To are books, not theory.

**Gaps to fill**:
- **Theory and concepts**: Information visualization principles (Tufte, Bertin, Munzner "Visualization Analysis and Design"), visual encoding theory, perceptual principles (Cleveland & McGill), grammar of graphics (Wilkinson, Wickham)
- **Genomic visualization**: IGV, UCSC Genome Browser architecture, Ensembl, WashU Epigenome Browser, HiGlass (Hi-C visualization), Galaxy visualization plugins, BioCircos
- **Literary text visualization**: Jänicke et al. survey (already have), VarifocalReader, Voyant Tools, distant reading visualizations, network visualization of literary texts
- **Circos deep dive**: Krzywinski original paper (download full text), Circos design principles, circular layout theory, application to non-genomic data, OmicCircos, shinyCircos
- **Advanced multi-layer data visualization**: Parallel coordinates, matrix views (Bertin), multi-scale visualization, linked views theory (Buja et al.), coordinated multiple views (Roberts 2007), focus+context techniques, semantic zooming
- **Large-scale complex data**: Graph visualization at scale, hierarchical edge bundling, treemaps, Sankey diagrams for flow data, force-directed layouts for networks

**Deliverables**:
- [ ] 15-25 new papers/books downloaded
- [ ] Circos full paper downloaded and analyzed
- [ ] Bibliography updated

### 1d. Swinehart and Conceptual Underpinnings

**Current state**: Swinehart's work referenced via web URLs (samizdat.co). Reports 01-05 catalog the research. No deep analysis of Swinehart's design principles, data structures, or visual grammar.

**Work required**:
- Read reports 01-05 thoroughly
- Unpack Swinehart's conceptual underpinnings: What makes CYOA and Infinite Digest work as visualizations? What data models, design decisions, and interaction patterns are at play?
- Connect to broader visualization theory (Tufte, Bertin, Munzner)
- Identify transferable principles for Palimpsest
- Review reports for relevance to 1a-1c research expansions

**Deliverables**:
- [ ] Swinehart design analysis integrated into domain synthesis
- [ ] Reports 01-05 cross-referenced with new research

### 1e. Bibliography Maintenance

**Rules**:
- Every new reference gets a full citation in `master-bibliography.md`
- Every downloadable PDF goes to `research/papers/{category}/`
- Papers that cannot be downloaded go into a "Manual Acquisition" list
- Books get chapter-level treatment: each chapter is a citable reference
- Bibliography organized by domain, then chronologically within domain

---

## Stage 2: Domain Synthesis Revision

### Current state
20 documents (docs 00-15, plus phase1-tasks/). Many were written incrementally as research was gathered. Cross-document consistency has drifted.

### Work required

**2a. Conceptual Foundation Document**
- Digest docs 01 (conceptual framework), 03 (NLP deep read), 04 (genomics deep read), 05 (literary studies deep read), 07 (annotation framework), 08 (CL frameworks), 09 (genome annotation methods), 10 (visualization)
- Synthesize into a single comprehensive conceptual foundation document
- Ground every claim in specific research references (not just "the literature suggests")
- Every chapter of every book in the corpus is a potential citation

**2b. Research Grounding**
- Review all domain synthesis documents against the expanded research corpus
- Update stale references, add new citations
- Ensure every architectural decision traces back to research justification
- Books get chapter-level citation treatment

**2c. Cross-Document Consistency**
- Review all 20+ documents jointly for consistency
- Update terminology, format references, architectural descriptions
- Include reports, WALKTHROUGH.md, and bibliography in the review
- Flag and resolve contradictions

**Deliverables**:
- [ ] New comprehensive conceptual foundation document
- [ ] All domain synthesis documents revised for consistency
- [ ] Citation density significantly increased across all documents

---

## Stage 3: Vision and Planning

### 3a. Vision Document
- Consolidate vision across docs 00 (alignment-convergence thesis), 01 (conceptual framework), 11 (vision synthesis), 12 (roadmap)
- Frame from the perspective of scholars and engineers whose aim is to bring all of computational linguistics under the functional umbrella of an exhaustively feature-rich genome browser and analytical platform
- Go beyond standard fare: include custom, unique complex analyses and visualizations not broadly considered standard in CL or comparative literature
- Richly embellish with: images from scholarly sources, Mermaid diagrams, SVG representations, graphs
- Dense end-notes from research sources

**Deliverable**: Vision document with visual richness and scholarly depth

### 3b. Product Requirements Document (PRD)
- Digest and atomize the Vision document
- Every feature justified in terms of purpose and function
- Every idea from largest to smallest mapped to product features
- Nothing lost in translation — ideas expanded and crystallized
- Atomic components, end-to-end user narratives
- Full stack detail: infrastructure, services, components, algorithms, interfaces
- Highly technical, highly detailed, lengthy

**Deliverable**: Comprehensive PRD

### 3c. Development Roadmap
- Translate PRD into full-scope development roadmap
- Milestones gated by demonstrated realization of vision, not just working code
- End-to-end coverage, no PRD detail missed
- Each section detailed enough to expand into individual milestone plans

**Deliverable**: Full-scope roadmap document

### 3d. Milestone 1 Deep Planning
- Milestone 1 Roadmap-PRD (detailed)
- Milestone 1.x phase Roadmap-PRDs (for each phase)
- Atomized task-level development instructions for Milestone 1.1
- Tasks written so a day-1 junior developer can follow with zero confusion
- Subsequent 1.x task documents created at the start of each phase

**Deliverables**:
- [ ] M1 Roadmap-PRD
- [ ] M1.x phase Roadmap-PRDs
- [ ] M1.1 atomized task documents

---

## Stage 4: Documenting Development

### Development History Log
- Created at the start of this overhaul
- Entries at: close of each milestone/phase, completion of major documents, significant decisions
- Audits of this log are part of completion gating

### Adversarial Review Personas

Five personas to be used throughout all stages of this process:

#### Dr. Elena Marchetti — Functional and Comparative Genomics
- **Background**: Principal investigator, 15 years in functional genomics. Published on chromatin architecture, gene regulation, and comparative genomics across vertebrates.
- **Perspective**: Demands biological rigor. Checks that genomic analogies are accurate, not superficial. Questions whether alignment algorithms are applied correctly. Insists on proper use of ontologies and evidence codes. Pushes back on claims that literary features "are like" genomic features unless the mapping is formally defined.
- **Key question**: "What is the biological basis for this analogy, and does the computational method actually preserve the properties you claim?"

#### Dr. James Okonkwo — Platform Architecture and Infrastructure
- **Background**: Staff engineer, 10 years building data-intensive browser-based platforms. Contributed to JBrowse 2 and IGV.js. Deep knowledge of Tauri, WebGPU, and high-performance rendering.
- **Perspective**: Demands scalability and performance. Questions every O(n²) loop, every unnecessary DOM node, every synchronous operation. Insists on virtualization, efficient data structures, and tested performance benchmarks. Won't accept "it works on chapter 1" as evidence of scalability.
- **Key question**: "Show me the benchmark on a full novel. What's the render time at 10x the current data volume?"

#### Prof. Sarah Blackwood — Computational Linguistics and Comparative Literature
- **Background**: Associate professor, dual appointment in CS and English. Published on computational stylistics, narrative structure, and digital humanities methodology. Skeptical of computational approaches that reduce literary complexity.
- **Perspective**: Demands that computational methods respect the richness and ambiguity of literary texts. Questions whether features like "sentiment" or "topic" capture anything meaningful about literature. Insists that the tool serves scholarship, not that scholarship serve the tool. Pushes for interpretive flexibility over deterministic classification.
- **Key question**: "What does this feature tell a scholar that close reading doesn't? What literary nuance does this representation lose?"

#### Dr. Raj Patel — Data Engineering, Data Science, and Complex Visualization
- **Background**: Lead data scientist, 12 years in scientific visualization and data engineering. Expert in D3, WebGL, and information visualization theory. Published on multi-scale visualization and perceptual design.
- **Perspective**: Demands visual clarity and perceptual accuracy. Questions color choices, encoding strategies, and information density. Insists on proper visual grammar (Bertin, Munzner). Won't accept visualizations that look good but misrepresent data or overwhelm the user. Pushes for progressive disclosure and semantic zooming.
- **Key question**: "Can a user extract the intended insight from this visualization in under 5 seconds? What's the data-ink ratio?"

#### Alex Chen — Critical End-User (Power User / Stress Tester)
- **Background**: PhD candidate in comparative literature, computationally fluent. Works with 20+ novels simultaneously, runs batch analyses overnight, demands the ability to compare across texts at scale.
- **Perspective**: Demands speed, scale, and analytical depth. Always asks for more: more texts, more tracks, more computational power, faster rendering. Tests edge cases: what happens with a 500K-word novel? With 50 novels loaded? With a custom track that produces 100K annotations? Finds every crash, every hang, every misleading default.
- **Key question**: "I loaded War and Peace with all tracks enabled. Why is it so slow? Can I compare it side-by-side with Anna Karenina?"

### Persona Usage Protocol
- At least 2 personas review every major document
- Dr. Marchetti and Prof. Blackwood review all research and domain synthesis (Stage 1-2)
- Dr. Okonkwo and Dr. Patel review all planning and architecture (Stage 3)
- Alex Chen reviews all milestone exit criteria and smoke tests (Stage 3-4)
- Persona feedback is recorded in the development history log
- A finding from any persona that rates below 4/5 on their dimension triggers remediation before proceeding

---

## Execution Sequence

### Session 1: Research Expansion (Stage 1a-1c)
1. Survey current bibliography against gaps identified above
2. Search for and download papers to fill gaps
3. Update master bibliography
4. Prioritize: foundational theory first, then applied methods, then tools

### Session 2: Research Expansion (Stage 1d-1e) + Domain Synthesis Start (Stage 2a)
1. Deep read of reports 01-05 and Swinehart analysis
2. Begin conceptual foundation document
3. Finalize bibliography

### Session 3: Domain Synthesis (Stage 2b-2c)
1. Cross-document consistency review
2. Research grounding of all domain synthesis docs
3. Citation densification

### Session 4: Vision Document (Stage 3a)
1. Consolidate vision
2. Create visual materials (Mermaid, SVG)
3. Persona review (Marchetti + Blackwood)

### Session 5: PRD (Stage 3b)
1. Atomize vision into product requirements
2. Full-stack technical detail
3. Persona review (all 5)

### Session 6: Roadmap (Stage 3c) + Milestone 1 Planning (Stage 3d)
1. Roadmap from PRD
2. M1 and M1.x detailed plans
3. M1.1 atomized tasks
4. Persona review (Okonkwo + Patel + Chen)

### Ongoing: Development History Log (Stage 4)
- Updated at every session boundary
- Audit at every milestone gate

---

## Completion Criteria

This overhaul is complete when:
1. Research corpus has >75 sources with full chapter-level book citations
2. All domain synthesis documents are internally consistent and densely cited
3. Vision document exists with visual richness and scholarly depth
4. PRD exists with atomic feature decomposition and full-stack detail
5. Roadmap exists with vision-gated milestones
6. M1.1 has step-by-step task documents a junior developer can follow
7. All 5 personas have reviewed their relevant documents at >=4/5
8. Development history log is current

---

*This document is the master reference for the Palimpsest documentation overhaul. All sessions refer back to it for scope, sequence, and completion criteria.*

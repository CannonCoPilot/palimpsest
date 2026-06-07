# Research Catalog: Alignment and Visualization

**Generated**: 2026-06-06
**Source**: PubMed, Anna's Archive
**Topics**: Whole genome alignment, protein structural alignment, Circos visualization, genome browsers

---

## Tier 1: Foundational Papers (Must-Read)

### Circos: An Information Aesthetic for Comparative Genomics
- **Authors**: Krzywinski M, Schein J, Birol I, et al.
- **Year**: 2009 | **Journal**: Genome Research
- **DOI**: [10.1101/gr.092759.109](https://doi.org/10.1101/gr.092759.109) | **PMID**: 19541911
- **Relevance**: The original Circos paper. Defines the circular ideogram paradigm for genome comparison. The visualization framework directly applicable to text comparison (positional data + relational ribbons). Supports scatter, line, histogram, heatmap, connectors, and text tracks.
- **Key insight**: Circos succeeds because it encodes *three* dimensions in ribbons (source position, target position, relationship strength) while maintaining visual clarity through the circular layout that minimizes edge crossings.

### Fast and Accurate Protein Structure Search with Foldseek
- **Authors**: van Kempen M, Kim SS, Tumescheit C, Mirdita M, et al. (Steinegger M)
- **Year**: 2023 | **Journal**: Nature Biotechnology
- **DOI**: [10.1038/s41587-023-01773-0](https://doi.org/10.1038/s41587-023-01773-0) | **PMID**: 37156916
- **Relevance**: Introduces the **structural alphabet** — encoding 3D protein structure as a 1D sequence (3Di alphabet), enabling sequence search algorithms on structural data. This is the key paradigm transfer: just as Foldseek encodes 3D structure as a searchable sequence, Palimpsest could encode narrative structure as a searchable representation.
- **Key insight**: 4-5 orders of magnitude speedup over TM-align/Dali by reducing structural comparison to sequence comparison. The 3Di alphabet captures local geometric interactions between residues.

### Rapid and Sensitive Protein Complex Alignment with Foldseek-Multimer
- **Authors**: Kim W, Mirdita M, Levy Karin E, et al. (Steinegger M)
- **Year**: 2025 | **Journal**: Nature Methods
- **DOI**: [10.1038/s41592-025-02593-7](https://doi.org/10.1038/s41592-025-02593-7) | **PMID**: 39910251
- **Relevance**: Extends structural alignment to multi-chain complexes. Analogous to comparing multi-document collections (e.g., all four Gospels simultaneously rather than pairwise).

### Sensitive Remote Homology Search by Local Alignment of Small Positional Embeddings
- **Authors**: Johnson SR, Peshwa M, Sun Z
- **Year**: 2024 | **Journal**: eLife
- **DOI**: [10.7554/eLife.91415](https://doi.org/10.7554/eLife.91415) | **PMID**: 38488154
- **Relevance**: Shows that protein language model embeddings (ESM2) can be compressed to single-byte positional representations and fed into speed-optimized search algorithms. Direct analogy to using text embeddings for fast passage alignment.

---

## Tier 2: Circos Ecosystem & Extensions

### CircosVCF: Circos Visualization of Whole-Genome Sequence Variations
- **Authors**: Drori E, Levy D, Smirin-Yosef P, et al.
- **Year**: 2017 | **Journal**: Bioinformatics
- **DOI**: [10.1093/bioinformatics/btw834](https://doi.org/10.1093/bioinformatics/btw834) | **PMID**: 28453675
- **Relevance**: Web-based Circos for VCF files. Interactive design of circles. Template for a "text-Circos" web application.

### NG-Circos: Next-Generation Circos for Data Visualization
- **Authors**: Cui Y, Cui Z, Xu J, et al.
- **Year**: 2020 | **Journal**: NAR Genomics and Bioinformatics
- **DOI**: [10.1093/nargab/lqaa069](https://doi.org/10.1093/nargab/lqaa069) | **PMID**: 33575618
- **Relevance**: JavaScript-based interactive Circos with 21 functional modules. Open source. Directly usable as a visualization layer for Palimpsest's output.

### A Painless Way to Customize Circos Plot: TBtools
- **Authors**: Chen C, Wu Y, Xia R
- **Year**: 2022 | **Journal**: iMeta
- **DOI**: [10.1002/imt2.35](https://doi.org/10.1002/imt2.35) | **PMID**: 38868708
- **Relevance**: GUI-based Circos construction. User-friendly interface pattern for non-technical users — relevant to Palimpsest's goal of democratizing literary analysis.

### Visualization of Oligonucleotide Probes Using RIdeogram, KaryoploteR, and Circlize
- **Authors**: Mann L, Maiwald S
- **Year**: 2023 | **Journal**: Methods in Molecular Biology
- **DOI**: [10.1007/978-1-0716-3226-0_26](https://doi.org/10.1007/978-1-0716-3226-0_26) | **PMID**: 37335492
- **Relevance**: R-based alternatives to Circos (circlize package). Comparative visualization of linear and circular plots.

---

## Tier 3: Books — Computational Literary Analysis & Visualization

### Visualize This: The FlowingData Guide to Design, Visualization, and Statistics (2nd Ed.)
- **Author**: Nathan Yau | **Year**: 2024 | **Publisher**: Wiley
- **Anna's Archive MD5**: ca20202082f7bdecd727de30317afc62 (PDF), 40fcbf949b092ce095c3faede2e5cd40 (EPUB)
- **Relevance**: Comprehensive data visualization guide. Includes text/narrative visualization examples.

### Distant Reading
- **Author**: Franco Moretti | **Year**: 2013 | **Publisher**: Verso Books
- **Anna's Archive MD5**: 2289aa1fcf8cfc2d69654cf2cf9099a3 (PDF), 0fec85d3fb4c6116e87e8a616bc54905 (EPUB)
- **Relevance**: Foundational text for computational literary studies. Moretti's Stanford Literary Lab pioneered quantitative approaches to literature at scale.

### Close Reading with Computers: David Mitchell's Cloud Atlas
- **Author**: Martin Paul Eve | **Year**: 2019 | **Publisher**: Stanford University Press
- **Anna's Archive MD5**: 0631e1fa85c6d0e794a5dd34a3d75a06 (PDF)
- **Relevance**: Directly demonstrates computational methods applied to a structurally complex novel. Cloud Atlas has nested narrative structure analogous to Infinite Jest.

### Mapping Texts: Computational Text Analysis for the Social Sciences
- **Authors**: Dustin S. Stoltz, Marshall A. Taylor | **Year**: 2023 | **Publisher**: Oxford University Press
- **Anna's Archive MD5**: a1d348a1e80894c02dd8760fef98bd75 (PDF)
- **Relevance**: Bridges computational text analysis methods with social science applications. Systematic coverage of modern NLP for document analysis.

### The Scales of (Computational) Literary Studies: Mueller's Scalable Reading
- **Author**: Benjamin Krautter | **Year**: 2023 | **Publisher**: de Gruyter
- **Anna's Archive MD5**: 021c19b4be2f8e0f103232600adf5849 (PDF)
- **Relevance**: Theory and practice of "scalable reading" — moving between close and distant reading. Directly relevant to Palimpsest's multi-dimensional approach.

### Structural Analysis of Narrative Texts: Conference Papers
- **Editors**: Andrej Kodjak et al. | **Year**: 1980 | **Publisher**: Slavica Publishers
- **Anna's Archive MD5**: 4e319fd9b20010fb6256c90993432e0c (PDF)
- **Relevance**: Early foundational work on structural narratology applied to text analysis. Historical grounding for modern computational approaches.

### Blueprints for Text Analytics Using Python
- **Authors**: Albrecht J, Ramachandran S, Winkler C | **Year**: 2021 | **Publisher**: O'Reilly
- **Anna's Archive MD5**: 2a74631bb6f3184c0f288fb668d3a3ca (PDF)
- **Relevance**: Practical NLP implementation guide. Covers text processing pipelines directly applicable to Palimpsest's analysis modules.

---

## Pending Research (Updated 2026-06-06)

- [x] BookNLP (Bamman et al.) — downloaded: `nlp-narrative/BookNLP-bayesian-character-P14-1035.pdf`
- [x] Emotional arcs of stories (Reagan et al., 2016) — on disk: `nlp-narrative/Reagan-emotional-arcs-stories-1606.07772.pdf`
- [x] Narrative schema learning (Chambers & Jurafsky) — downloaded: `Chambers-narrative-event-chains-P08-1090.pdf`, `Chambers-narrative-schemas-P09-1068.pdf`
- [x] Swinehart IJ/CYOA data — downloaded: `datasets/swinehart/` (4 IJ CSVs + 72 CYOA book sheets)
- [x] GNAT narrative alignment tool — downloaded: `nlp-narrative/GNAT-narrative-alignment-2311.03627.pdf`
- [x] Church & Helfman dotplot — downloaded: `alignment/Church-Helfman-dotplot-text-1993.pdf`
- [x] Plot Units (Lehnert 1981) — downloaded: `nlp-narrative/Lehnert-plot-units-1981.pdf`
- [x] Narrative Arc (Boyd et al. 2020) — downloaded: `nlp-narrative/Boyd-narrative-arc-2020.pdf`
- [ ] RST discourse parsing for literary texts (Mann & Thompson 1988 paywalled)
- [ ] Syuzhet R package docs (software, no paper — GitHub: mjockers/syuzhet)
- [ ] Genome browser architectures (JBrowse, IGV, UCSC) — metadata only
- [ ] HDS (Hierarchical Delta Synthesis) — internal skill at `.claude/skills/_disabled/hds/`
- [ ] Elson, Dames, McKeown (ACL 2010) — Social Networks from Fiction
- [ ] Kim et al. (IEEE TVCG 2018) — Story Curves: Nonlinear Narratives
- [ ] Tanahashi & Ma (IEEE TVCG 2012) — Storyline Visualization Design

---

*Catalog compiled from PubMed (attribution required per terms of use) and Anna's Archive.*

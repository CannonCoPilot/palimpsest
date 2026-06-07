# Alignment as Universal Structure: A Cross-Domain Synthesis

**Purpose**: Map the conceptual topology connecting genome alignment, protein structure alignment, text alignment, and their shared visualization paradigms. This synthesis informs search strategy for the Palimpsest research corpus.

---

## 1. The Alignment Paradigm

At its core, "alignment" is the problem of establishing correspondence between elements of two or more sequences (or structures) to maximize a scoring function while respecting ordering constraints. This problem recurs across biology, linguistics, and literary analysis with remarkable structural similarity.

### 1.1 Sequence Alignment (Genomics)

**Whole Genome Alignment (WGA)** compares complete genomes to identify:
- **Syntenic blocks**: conserved gene order across species
- **Rearrangements**: inversions, translocations, duplications
- **Divergence rates**: mutation accumulation since last common ancestor

Key algorithms: **MUMmer** (suffix trees for maximal unique matches), **LASTZ** (seeded alignment for mammalian genomes), **minimap2** (minimizer-based for long reads), **Cactus** (reference-free progressive alignment).

The scoring is typically substitution matrices (BLOSUM, PAM) + gap penalties (affine: open + extend). The constraint is collinearity — matches must respect chromosomal order within syntenic blocks.

### 1.2 Structural Alignment (Proteins)

**Protein structural alignment** maps 3D coordinates of amino acid residues to minimize RMSD (root-mean-square deviation). Unlike sequence alignment, the alphabet is spatial — two proteins can share a fold with <15% sequence identity.

Key tools: **TM-align** (TM-score normalization), **DALI** (distance matrix comparison), **CE** (combinatorial extension), **Foldseek** (structural alphabets for fast search), **AlphaFold2** (predicted structures enabling genome-scale structural comparison).

The paradigm shift: AlphaFold made structural alignment tractable at genomic scale. The AlphaFold Protein Structure Database (~200M structures) enables "structural genomics" — comparing fold space the way we compare sequence space.

### 1.3 Semantic Alignment (Texts)

**Text alignment** maps corresponding passages between document versions, translations, or thematically related works. The Palimpsest project addresses this directly.

Levels of text alignment:
- **Token/character**: edit distance, diff algorithms (Myers, patience diff)
- **Sentence**: sentence-level bilingual alignment (Gale-Church, Bleualign)
- **Paragraph/passage**: sliding window + embedding similarity
- **Structural**: chapter/section correspondence, narrative arc matching
- **Semantic**: thematic/conceptual correspondence independent of surface form

Key distinction from biological alignment: text alignment must handle **non-sequential correspondence** (chiastic structures, flashbacks, cross-references) and **many-to-many mappings** (one passage may parallel multiple others).

### 1.4 The Isomorphism

| Dimension | Genome | Protein | Text |
|-----------|--------|---------|------|
| **Unit** | nucleotide/gene | residue/domain | word/sentence/passage |
| **Scoring** | substitution matrix | RMSD/TM-score | cosine similarity/edit distance |
| **Constraint** | collinearity | spatial proximity | narrative order (relaxed) |
| **Gap model** | affine gap penalty | loop/insertion modeling | omission/addition tracking |
| **Rearrangement** | inversion/translocation | domain swapping | passage reordering |
| **Visualization** | dot plot/Circos/synteny | superposition/Ramachandran | alignment heatmap/arc diagram |

---

## 2. Visualization Convergence

The most striking convergence is in visualization. The same visual metaphors recur because the underlying data structure — pairwise or multi-way correspondence with scoring — is identical.

### 2.1 Circos Plots

Originally designed for genomic data (Krzywinski et al., 2009), **Circos** places sequences on a circular axis and draws ribbons/links between corresponding regions. This same representation works for:
- Genome rearrangements between species
- Character interaction networks in novels
- Cross-reference patterns in legal/religious texts
- Citation networks between papers

The circular layout solves the "crossing lines" problem of linear alignment displays.

### 2.2 Dot Plots

The simplest alignment visualization: sequences on X and Y axes, marks at positions of match. Diagonal runs = conserved blocks. Off-diagonal = rearrangements. Works identically for:
- DNA sequence comparison (Dotter, Gepard)
- Self-similarity in music (Foote novelty)
- Recurring motifs in narrative text

### 2.3 Genome Browsers → Text Browsers

Tools like **IGV**, **UCSC Genome Browser**, and **JBrowse** display multi-track annotations along a linear coordinate axis. The same paradigm applies to text:
- Coordinate axis = character/word position in document
- Tracks = different annotation layers (POS tags, named entities, sentiment, dialog attribution, structural markers)
- Cross-document linking = alignment ribbons connecting corresponding regions

**Swinehart's Infinite Jest visualization** extends this to non-linear narrative: the endnote network creates a hypertext graph overlaid on the linear page sequence.

### 2.4 Network/Graph Visualizations

Both genome interaction networks (Hi-C contact maps, gene regulatory networks) and narrative structure (character interaction graphs, plot dependency DAGs) use:
- Force-directed layouts (D3.js, Gephi)
- Adjacency matrices
- Hierarchical clustering dendrograms

---

## 3. The NLP/ML Frontier for Narrative Analysis

### 3.1 Dialog Attribution

Assigning quoted speech to characters in narrative text. State of the art:
- **BookNLP** (Bamman et al.): end-to-end pipeline for literary text — NER, coreference, quotation attribution, supersense tagging
- **Character-level language models**: GPT-based models fine-tuned on annotated literary corpora
- **Rule-based + ML hybrid**: punctuation parsing + coreference chains + speaker verb identification

### 3.2 Narrative Structure Extraction

- **Story arcs**: Kurt Vonnegut's shapes of stories, operationalized by Reagan et al. (2016) using sentiment trajectories
- **Plot units**: Lehnert's (1981) affect-state framework, computationalized by Goyal et al.
- **Narrative schema**: Chambers & Jurafsky (2008, 2009) — scripts learned from corpora
- **Discourse parsing**: RST (Rhetorical Structure Theory) trees for identifying argument structure

### 3.3 Information Signals in Creative Text

- **Narrative entropy**: Shannon entropy of word distributions tracks information density across a text
- **Surprisal**: language model perplexity per token measures "unexpectedness" — peaks at plot twists
- **Topic flow**: LDA/NMF topic weights over sliding windows track thematic evolution
- **Emotional arc**: sentiment analysis trajectories (Syuzhet package, VADER, transformer-based)

### 3.4 Poetry and Verse

- **Prosodic analysis**: meter detection, stress patterns, enjambment identification
- **Rhyme scheme**: phonemic comparison of line-terminal words
- **Formal structure**: sonnet/villanelle/haiku form detection
- **Sound symbolism**: phonestheme analysis, Bouba/Kiki effects in poetic language

---

## 4. Search Strategy Implications

This synthesis reveals that the research topics are not independent — they form a connected graph:

```
Genome Alignment ──── Visualization ──── Text Alignment
       │                    │                    │
  Structural            Circos/              NLP/ML
  Alignment           Dot Plots           Narrative
       │                    │                    │
   AlphaFold          Swinehart/IJ        BookNLP/
   Foldseek            CYOA viz          Dialog attr.
       │                    │                    │
       └────── Alignment as ────────────────────┘
              Universal Structure
```

**Search strategy**: Query terms should leverage this graph. Papers on "whole genome alignment visualization" will cite Circos. Papers on "narrative structure visualization" will cite network analysis from bioinformatics. Cross-domain citations are the highest-value finds.

---

## 5. Key Authors and Groups to Track

- **Martin Krzywinski** (BC Cancer) — Circos, data visualization
- **Sam Swinehart** (samizdat.co) — Infinite Jest and CYOA visualizations
- **Nathan Yau** (Flowing Data) — data visualization practice
- **David Bamman** (UC Berkeley) — BookNLP, computational literary analysis
- **Matthew Jockers** (Washington State) — Syuzhet, macroanalysis
- **Franco Moretti** (Stanford Literary Lab) — distant reading
- **Ted Underwood** (UIUC) — cultural analytics, distant reading
- **Andrew Reagan** (UVM/MassMutual) — emotional arcs of stories
- **Heng Li** (Dana-Farber) — minimap2, sequence alignment
- **Benedict Paten** (UCSC) — Cactus, progressive alignment
- **Martin Steinegger** (Seoul National) — Foldseek, MMseqs2
- **AlphaFold team** (DeepMind) — structural prediction at scale

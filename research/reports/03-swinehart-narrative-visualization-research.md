# Research Report: Swinehart's Narrative Visualization Work and the Computational Literary Analysis Landscape

**Date**: 2026-06-06
**Scope**: Christian Swinehart's CYOA and Infinite Jest visualization projects; the broader ecosystem of computational narrative visualization tools, methodologies, and academic foundations relevant to the Palimpsest platform.

---

## Executive Summary

Christian Swinehart (operating as Samizdat Drafting Co.) has produced two landmark works in the intersection of data visualization and literary structure. His 2009/2022 project "One Book, Many Readings" systematically mapped the branching architecture of twelve Choose Your Own Adventure books as directed network graphs, revealing structural evolution patterns across a decade of the genre. His ongoing 2021/2026 project "Infinite Digest" applies similar structural analysis to David Foster Wallace's *Infinite Jest* -- a deeply nonlinear novel whose 388 endnotes and non-chronological episodic structure make it an ideal subject for computational inquiry.

These projects exist within a rich and growing academic field. Franco Moretti's 2011 Stanford Literary Lab pamphlet "Network Theory, Plot Analysis" established theoretical foundations for character-network analysis. Subsequent work by Tanahashi and Ma formalized storyline visualizations. Brian Lubars and colleagues applied dynamic network metrics to *Infinite Jest* specifically. The tooling ecosystem has matured considerably: D3.js and Gephi anchor the visualization layer, while Python-based NLP pipelines (spaCy, NLTK) drive character extraction and co-occurrence modeling.

For Palimpsest, the key takeaway is that the most compelling work in this space combines structural data (which pages connect to which, who appears with whom) with visual encodings that honor the reader's phenomenological experience of the text -- not just abstracting it away into a graph.

---

## Key Findings

### Finding 1: "One Book, Many Readings" -- The CYOA Project (2009, Updated 2022)

**What it is**: A structural analysis of twelve Choose Your Own Adventure and gamebook titles from 1979 through the mid-1980s, treating each book as a finite state machine.

**Methodology**:
- Each page classified as: branching (2+ choices), story (single forced transition), or ending (red-to-blue spectrum: catastrophic to ideal)
- Books converted to directed graphs: pages as nodes, choices as weighted edges
- Graph traversal enumerates every unique reading path, enabling "decision frequency" calculation
- Four visualization types: page grids, stacked bar charts, arc diagrams, force-directed graph layouts (Barnes-Hut)

**Key structural discoveries**:
1. Creeping linearity over time: early books are dense with branching; later entries devote more pages to linear narrative
2. Three page-ordering strategies: linear threading, semi-random, breadth-first
3. Best endings cluster in back half; worst endings peak at two-thirds
4. The anomalous "unreachable" ending in *Inside UFO 54-40* -- a completely disconnected island node rewarding going outside the system

**Stack**: Python, PlotDevice, JavaScript, Traer physics / Barnes-Hut
**Source**: [samizdat.co/cyoa](https://samizdat.co/cyoa/)

### Finding 2: "Infinite Digest" -- The Infinite Jest Project (2021-2026, Ongoing)

An interactive illustrated companion to *Infinite Jest*. Two visualizations live, three more planned.

#### 2a. "All Those Footnotes" -- Endnote Visualization
- Dual semicircular arcs: upper = 979 novel pages, lower = 97 endnote pages
- Each endnote as a curved "wiggly" line bridging the arcs
- Line width encodes note length; curvature encodes relative proximity
- 388 total references; six of eight longest cluster between pp. 550-800
- Longest notes function as embedded narratives (Note 110: ~10,414 words)

#### 2b. "Plotlines" -- Chronological Character Tracking
Episode-by-episode summary reordered chronologically, color-coded by four character groups. Arcs connect sequential events.

#### 2c. Planned 2026 Additions
- Chronology vs. narrative order mapping
- Individual character arc trajectories
- Social networks across plotlines

**Data**: CSV datasets available at samizdat.co/digest/, drawn from Stephen Burn's *Reader's Guide*, Greg Carlisle's *Elegant Complexity*, Drew Cordes' chronological mapping.
**Stack**: SvelteKit, custom SVG/Canvas, scroll-driven interaction
**Source**: [samizdat.co/digest](https://samizdat.co/digest/)

### Finding 3: Swinehart Background
PhD Computational Neuroscience (Brandeis, 2005, under Laurence Abbott). MFA Graphic Design (RISD, 2008). Currently teaches Intro to Data Visualization at Columbia CS. Built Arbor.js (2,700+ stars), PlotDevice, Skia Canvas. Clients include NYT, Our World in Data, Bloomberg.

### Finding 4: Lubars et al. -- *Infinite Jest* as Dynamic Character Network (2018)
- Characters as nodes, co-mentions as weighted edges
- Both authored (non-chronological) and chronological orderings analyzed
- Small-world effect confirmed; NOT scale-free (unlike real social networks)
- Wallace's non-chronological sequencing is structurally optimal: higher degree, shorter paths, fewer disconnected components
- **Source**: [blubars.github.io](http://blubars.github.io/project/2018/12/20/complex-infinite-jest.html)

### Finding 5: Moretti and the Stanford Literary Lab
"Network Theory, Plot Analysis" (2011): character-network analysis applied to Shakespeare and Dickens.
- Removing Hamlet from the *Hamlet* network nearly splits the graph; Horatio is the sole bridge
- Honest conclusion: "many results were difficult to interpret" using visualization alone
- **Source**: [litlab.stanford.edu](https://litlab.stanford.edu/projects/network-theory-plot-analysis/)

### Finding 6: Storyline Visualization Lineage
From xkcd "Movie Narrative Charts" (2009) through Tanahashi & Ma (2012 IEEE TVCG) to StoryFlow (2013). Optimization: minimize line wiggles, crossings, white space. Recent: Story Ribbons (arXiv:2508.06772).

---

## Tool Comparison

| Tool | Type | Best For | License |
|---|---|---|---|
| D3.js | JS library | Custom interactive web viz | BSD |
| Gephi | Desktop | Exploratory network analysis | LGPL |
| SvelteKit | Web framework | Scroll-driven interactive viz | MIT |
| PlotDevice | Python | Static prototype graphics (macOS) | MIT |
| NetworkX + Gephi | Combined | Extraction + layout | Mixed |
| CHAPLIN | Research | Automated character/place networks | Research |
| webweb | Python/JS | Quick network viz from Python | MIT |

---

## Recommendations for Palimpsest

1. **Adopt multi-layer visual vocabulary**: page grid + arc diagram + force-directed network + timeline/storyline views
2. **Treat endnote/reference structure as first-class data**: model cross-references as graph edges
3. **Use D3.js for interactive; Gephi for exploratory**
4. **Ground in Moretti lineage but pair visualizations with computable metrics**
5. **Download Swinehart's datasets** from samizdat.co/digest/ for prototyping

---

## Key References

1. [samizdat.co/cyoa](https://samizdat.co/cyoa/) -- CYOA visualization
2. [samizdat.co/digest](https://samizdat.co/digest/) -- Infinite Digest
3. [samizdat.co/digest/notes/](https://samizdat.co/digest/notes/) -- endnote visualization
4. [samizdat.co/digest/sketchbook/](https://samizdat.co/digest/sketchbook/) -- design process
5. [litlab.stanford.edu](https://litlab.stanford.edu/projects/network-theory-plot-analysis/) -- Moretti network analysis
6. [arXiv:1402.4259](https://arxiv.org/pdf/1402.4259) -- CHAPLIN character/place extraction
7. [arXiv:2406.14734](https://arxiv.org/pdf/2406.14734) -- Story charting with network viz
8. [arXiv:2508.06772](https://arxiv.org/html/2508.06772v1) -- Story Ribbons (LLM-powered)
9. [arXiv:2303.06456](https://arxiv.org/pdf/2303.06456) -- NetworkNarratives data tours
10. [Science Advances: The Narrative Arc](https://www.science.org/doi/10.1126/sciadv.aba2196)
11. [blubars.github.io](http://blubars.github.io/project/2018/12/20/complex-infinite-jest.html) -- Lubars IJ networks
12. [Portrayal: arXiv:2308.04056](https://arxiv.org/abs/2308.04056) -- interactive character analysis

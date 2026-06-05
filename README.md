<p align="center">
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/Python-3.8+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python"></a>
  <a href="https://spacy.io/"><img src="https://img.shields.io/badge/spaCy-NLP-09A3D5?style=for-the-badge&logo=spacy&logoColor=white" alt="spaCy"></a>
  <a href="https://www.sbert.net/"><img src="https://img.shields.io/badge/Sentence_Transformers-Embeddings-FF6F00?style=for-the-badge" alt="Sentence Transformers"></a>
  <a href="https://flask.palletsprojects.com/"><img src="https://img.shields.io/badge/Flask-Web_UI-000000?style=for-the-badge&logo=flask&logoColor=white" alt="Flask"></a>
  <a href="https://networkx.org/"><img src="https://img.shields.io/badge/NetworkX-Graph_Analysis-4C8CBF?style=for-the-badge" alt="NetworkX"></a>
  <a href="https://www.nltk.org/"><img src="https://img.shields.io/badge/NLTK-Linguistics-154F5B?style=for-the-badge" alt="NLTK"></a>
</p>

# Palimpsest

A multi-dimensional text comparison system for computational literary analysis. Palimpsest compares large documents (1M+ words) across four independent analytical axes -- semantic similarity, syntactic structure, narrative architecture, and string-level matching -- to surface relationships that no single method would catch alone.

> [!NOTE]
> Named after the ancient practice of scraping and rewriting parchment, where traces of earlier texts remain visible beneath new ones. Palimpsest finds those traces computationally.

---

## The Problem

Existing tools for comparing literary texts operate on a single dimension: either raw string diff, or topic modeling, or syntactic parse trees. But the interesting questions in comparative literature -- Did the author of Mark draw from Matthew? Which Federalist Papers share an author? How did the Odyssey influence the Aeneid? -- require evidence from multiple analytical dimensions simultaneously. A shared phrase matters more when it occurs within a shared syntactic pattern within a shared narrative structure.

Palimpsest runs four independent analysis modules against the same document set and produces a combined similarity score, so researchers can distinguish surface-level borrowing from deep structural influence.

---

## Computational Discovery in Literary Texts

Palimpsest addresses a gap between single-method NLP tools and manual close reading. Each module targets a different layer of textual similarity:

| Module | Method | What It Finds |
|---|---|---|
| **Semantic** | Sentence-transformer embeddings (`all-MiniLM-L6-v2`) + cosine similarity | Thematic parallels, conceptual overlap even when phrasing differs |
| **Syntactic** | spaCy dependency parsing + Jaccard/cosine metrics on parse patterns | Shared grammatical fingerprints: passive voice frequency, clause depth, branching factor |
| **Structural** | NetworkX directed graph hierarchy + narrative flow segmentation | Document architecture similarity, transition patterns (temporal, causal, contrastive) |
| **String Matching** | Chunked indexing + Levenshtein fuzzy matching with masking/subsampling | Direct textual borrowing, repeated phrases, near-verbatim parallels |

The modules are independent. Run one or all four depending on the research question.

### Example Use Cases

- **Synoptic Gospel comparison** -- Load Matthew, Mark, and Luke from Project Gutenberg; run all four modules to quantify the Synoptic Problem with data
- **Federalist Papers authorship** -- Compare essays by Hamilton, Madison, and Jay; syntactic fingerprinting reveals stylistic signatures
- **Epic literature influence** -- Trace structural and thematic echoes from the Iliad through the Aeneid to Paradise Lost

---

## Architecture

```
palimpsest/
├── src/
│   ├── main.py                          # CLI + Flask web server entry point
│   └── core/
│       ├── semantic_analysis_module.py   # Sentence-transformer embeddings
│       ├── syntactic_analysis_module.py  # spaCy dependency parse comparison
│       ├── structural_analysis_module.py # NetworkX hierarchy + narrative flow
│       ├── string_matching_analysis.py   # Chunked fuzzy string matching
│       ├── string_matching_visualization.py  # Heatmaps via seaborn/matplotlib
│       └── gutenberg_client.py          # Project Gutenberg fetch + cache
├── ui/                                  # Flask-served web interface
├── tests/                               # Unit tests per module
├── research/                            # Jupyter notebooks (prototyping)
└── docs/                                # Mermaid class/sequence diagrams, PRD
```

> [!TIP]
> Mermaid architecture diagrams live in `docs/diagrams/`. The class diagram covers the full module interface hierarchy; the sequence diagram shows the analysis pipeline flow.

---

## Quick Start

<details>
<summary>Prerequisites</summary>

- Python 3.8+
- ~2 GB disk for sentence-transformer model weights
- spaCy English model (`en_core_web_sm`)

</details>

<details>
<summary>Installation</summary>

```bash
git clone https://github.com/CannonCoPilot/palimpsest.git
cd palimpsest

# Automated install (creates venv, installs deps)
./install.sh

# Or manually:
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -e .
python -m spacy download en_core_web_sm
```

</details>

### CLI Mode

```bash
# Compare two texts, output a report
python -m src.main source.txt target1.txt target2.txt --output report.txt
```

### Web UI Mode

```bash
# Launch the Flask-based analysis interface
python -m src.main --mode ui --port 8000
```

The web UI supports document upload, Project Gutenberg retrieval by book ID, module selection, and visualization of string matching results (heatmaps).

### Python API

```python
from src.core.semantic_analysis_module import SemanticAnalyzer

analyzer = SemanticAnalyzer(model_name='all-MiniLM-L6-v2')

# Pairwise similarity
score = analyzer.compute_similarity(
    "In the beginning God created the heaven and the earth.",
    "First Nephi, having been born of goodly parents."
)
print(f"Semantic similarity: {score:.4f}")

# Batch search against a corpus
matches = analyzer.find_similar_segments(
    target_text="Blessed are the meek",
    corpus=passage_list,
    threshold=0.7
)
```

---

## Analysis Output

The CLI generates a structured report:

```
PALIMPSEST ANALYSIS REPORT
========================

Combined relevance score: 0.7234

SEMANTIC CONNECTIONS
-------------------
Connection 1:
  Similarity: 0.9142
  Text: And it came to pass that...

Connection 2:
  Similarity: 0.8537
  Text: The Lord spoke unto Moses...
```

String matching results are saved as CSV files (`preliminary_match_scores.csv`, `fuzzy_match_scores.csv`) with heatmap visualizations generated via seaborn.

---

## Testing

```bash
# Run the full test suite
./run_tests.sh

# Or directly via unittest
python -m unittest discover -s tests
```

Test coverage spans semantic similarity validation (embedding dimensions, similarity ordering, threshold filtering), syntactic pattern extraction and comparison, structural hierarchy construction, and narrative flow segmentation.

---

## Key Dependencies

| Package | Role |
|---|---|
| `sentence-transformers` | Semantic embedding and similarity |
| `spacy` | Dependency parsing, syntactic analysis |
| `networkx` | Document hierarchy graph construction |
| `scikit-learn` | Cosine similarity, metrics |
| `matplotlib` / `seaborn` | String matching heatmaps |
| `flask` | Web UI server |
| `pandas` | Match score storage and manipulation |
| `gensim` | Topic modeling support |
| `nltk` | Tokenization, linguistic utilities |

---

## Status

This project is in active development (alpha). The semantic and string matching modules are functional end-to-end. Syntactic and structural modules have complete implementations with async analysis pipelines. The Project Gutenberg client handles automated text retrieval with local caching.

> [!IMPORTANT]
> Designed for research and exploration. The fuzzy matching backend (Levenshtein/Jaro-Winkler) is scaffolded but uses placeholder scoring -- integration with `python-Levenshtein` is the next priority.

---

## License

MIT License

---

<p align="center"><i>Scratching beneath the surface of texts to find what was written before.</i></p>

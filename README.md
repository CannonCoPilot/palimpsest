<p align="center">
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/Python-3.12+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python"></a>
  <a href="https://fastapi.tiangolo.com/"><img src="https://img.shields.io/badge/FastAPI-Server-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI"></a>
  <a href="https://react.dev/"><img src="https://img.shields.io/badge/React-19-61DAFB?style=for-the-badge&logo=react&logoColor=black" alt="React"></a>
  <a href="https://spacy.io/"><img src="https://img.shields.io/badge/spaCy-NLP-09A3D5?style=for-the-badge&logo=spacy&logoColor=white" alt="spaCy"></a>
  <a href="https://github.com/asg017/sqlite-vec"><img src="https://img.shields.io/badge/sqlite--vec-Embeddings-003B57?style=for-the-badge&logo=sqlite&logoColor=white" alt="sqlite-vec"></a>
</p>

# Palimpsest

A computational literary-analysis platform. Palimpsest ingests a text and produces **analysis layers**
over it — entities, dialogue, lexical and syntactic features, topics, sentiment, repeats, chunkings,
embeddings, self-similarity, and more — each addressed back to exact character offsets in the original
document and rendered as a **track** in a genome-browser-style viewer.

> [!NOTE]
> Named after the ancient practice of scraping and rewriting parchment, where traces of earlier texts
> remain visible beneath new ones. Palimpsest finds those traces computationally.

The guiding metaphor is the **browser, not the report**: every analysis is a coordinate-bearing layer
you can line up against the text and against other layers — the way a genome browser stacks annotation
tracks against a reference sequence.

---

## How it works

A *project* is a directory on disk. Everything about one text's analysis lives there, which makes
projects portable, diff-able, and content-addressable. There is **no database server** — project state
is filesystem-native, and the only DB is a per-project [`sqlite-vec`](https://github.com/asg017/sqlite-vec)
vector store for embeddings.

Every analysis is a **track** implementing a small `TrackExtractor` protocol; dropping a module into
`core/palimpsest/tracks/` registers it with zero boilerplate. Tracks come in two roles:

- **Producers** (chunking, embedding, repeats) emit reusable *layers* carrying a capability descriptor.
- **Consumers** (e.g. `self_similarity`) declare a dependency on existing layers and bind them
  explicitly — fail-loud, never silently recomputing. `self_similarity` is embedding-agnostic: its
  `word_overlap` / `edit_distance` metrics are text-only, while `cosine` / `jaccard` consume an
  embedding layer.

All outputs map back to the original text through an explicit, remappable coordinate frame
(`OffsetMap`) — the contract that lets masked-view analysis, layer reuse, and the forward cross-text
"root backbone" view all be small extensions rather than rewrites.

---

## Architecture

```
palimpsest/
├── core/                       # Python backend (the `palimpsest` package)
│   ├── palimpsest/
│   │   ├── server.py           # FastAPI server for the browser frontend
│   │   ├── cli.py              # `palimpsest` CLI (ingest / analyze / run-track / serve / export)
│   │   ├── tracks/            # Track extractors + the Wave-0 layer model (registry, resolver)
│   │   ├── ingest/            # PDF / EPUB / HTML / text ingestion
│   │   ├── vectorstore/      # sqlite-vec embedding store
│   │   └── project.py, runner.py, derive.py, …
│   └── tests/                 # pytest suite (markers: unit / nlp / api / cli / slow)
├── browser/                    # React 19 + zustand + Tailwind 4 (Vite) frontend
└── docs/development/           # Design, specs, ADRs, research corpus, audits
```

Tech stack: **FastAPI + uvicorn**, **spaCy**, scikit-learn, numpy/scipy, pymupdf/ebooklib (ingest),
**sqlite-vec**; frontend is **React 19 / zustand / Tailwind 4 / Vite** with hand-rolled `<canvas>`/`<svg>`
visualizations (no charting libraries). Embeddings are served by a local MLX or Ollama backend
(Qwen3-Embedding); none of it is required for the text-only analyses.

---

## Quick Start

### Backend (`core/`)

```bash
cd core
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
python -m spacy download en_core_web_lg

# Ingest a text, run the always-on tracks, then serve the browser
palimpsest ingest path/to/book.epub --workspace projects
palimpsest analyze projects/<text-id>
palimpsest serve projects --port 8080
```

Wave-0 *layer* tracks (`chunking`, `embedding`, `repeats`, `repeat_mask`, `self_similarity`) take
explicit parameters and are not part of batch `analyze`; produce them with `palimpsest run-track` or the
browser's Analysis panel. See [`docs/development/WALKTHROUGH.md`](docs/development/WALKTHROUGH.md).

### Frontend (`browser/`)

```bash
cd browser
npm install
npm run dev            # Vite dev server on :5173, proxies /api to the :8080 backend
```

---

## Documentation

Development documentation lives under [`docs/development/`](docs/development/) — start with its
[`README.md`](docs/development/README.md). The authoritative design docs are in
[`docs/development/design/`](docs/development/design/):

| Doc | Role |
|---|---|
| [`palimpsest_system_design.md`](docs/development/design/palimpsest_system_design.md) | Current system architecture |
| [`analysis-design-principles.md`](docs/development/design/analysis-design-principles.md) | Analysis paradigm + coordinate-frame contract |
| [`wave0-analysis-suite-vision.md`](docs/development/design/wave0-analysis-suite-vision.md) | Wave-0 analytics vision (FR-1…22) + forward cross-text design |
| [`wave0-analysis-suite-plan.md`](docs/development/design/wave0-analysis-suite-plan.md) | Phased development plan (P1–P11) |

Architecture Decision Records are in [`docs/development/architecture/`](docs/development/architecture/);
format specs (annotation model, signals, LFO, PAF) in [`docs/development/specs/`](docs/development/specs/).

---

## Testing

```bash
./run_tests.sh fast          # backend, excluding slow/external (pytest in core/)
./run_tests.sh all           # full backend suite
./run_tests.sh ui            # frontend (vitest in browser/)
```

---

## Status

Active development. The substrate (ingest, masking/coordinate contract, the always-on annotation tracks)
and the Wave-0 layer model (producible chunk/embedding/repeat layers + the `self_similarity` consumer)
are implemented end-to-end. The forward direction — a general two-operand resemblance operator and a
cross-text / synteny browser view — is designed and scoped (see the Wave-0 vision §10), not yet built.

---

## License

MIT License

---

<p align="center"><i>Scratching beneath the surface of texts to find what was written before.</i></p>

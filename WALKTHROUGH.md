# Palimpsest — Feature Walkthrough

A hands-on guide to launching Palimpsest and testing every major feature.

**Prerequisites**: macOS, Python 3.12+, Node.js 20+, uv (Python package installer), a terminal.
**Optional**: Ollama (for AI summaries and embedding-based features).
**Time**: ~15 minutes end-to-end.

---

## 1. Setup (one-time)

```bash
cd /Users/nathanielcannon/Claude/Projects/palimpsest

# Install Python package in editable mode (uses uv, already on this machine)
uv pip install -e core/ --python core/.venv/bin/python

# Install browser dependencies
cd browser
npm install
cd ..

# Verify spaCy model is available
core/.venv/bin/python -m spacy info en_core_web_lg
```

If the spaCy model is missing (~560 MB download):
```bash
core/.venv/bin/python -m spacy download en_core_web_lg
```

---

## 2. Ingest a Text

Create a workspace and ingest Pride and Prejudice Chapter 1:

```bash
mkdir -p projects

core/.venv/bin/palimpsest ingest \
  fixtures/pride-prejudice-ch1.txt \
  --title "Pride and Prejudice Ch1" \
  --author "Jane Austen" \
  --year 1813 \
  --workspace projects
```

**What to verify:**
- Output shows project created with word/paragraph/sentence counts
- Directory `projects/pride-and-prejudice-ch1/` exists
- Contains: `reference.txt`, `metadata.json`, `tracks/segments.jsonl`

You can also ingest the full novel:
```bash
core/.venv/bin/palimpsest ingest \
  fixtures/pride-prejudice-full.txt \
  --title "Pride and Prejudice" \
  --author "Jane Austen" \
  --year 1813 \
  --workspace projects
```

---

## 3. Analyze (Run All Track Extractors)

```bash
core/.venv/bin/palimpsest analyze projects/pride-and-prejudice-ch1
```

**What to verify:**
- Progress spinners show each track being computed
- Output: "Done: N tracks computed in X.Xs"
- `tracks/` now contains: `entities.jsonl`, `sentiment.jsonl`, `lexical.jsonl`, `dialogue.jsonl`, `topics.jsonl`
- `signals/` contains: `narrative_arc.json` + `.bin`, `rqa.json` + `.bin`, `alphabet.json`, `topics_dist.json` + `.bin`
- `manifests/` contains one `.manifest.json` per track
- `pipeline_run.json` records full provenance (version, parameters, timing)

**Expected skips** (not errors):
- `self_similarity`: skipped if Ollama not running (needs embeddings)
- `coreference`: skipped if BookNLP not installed (needs Java 11+)

To recompute everything from scratch:
```bash
core/.venv/bin/palimpsest analyze projects/pride-and-prejudice-ch1 --force
```

---

## 4. Inspect Project

```bash
core/.venv/bin/palimpsest info projects/pride-and-prejudice-ch1
```

**What to verify:**
- Shows title, author, word count, paragraphs, sentences, sections
- Lists all track files with annotation counts
- Lists all signal files

---

## 5. Export Data

### W3C Web Annotation (JSON-LD)
```bash
core/.venv/bin/palimpsest export projects/pride-and-prejudice-ch1 --format w3c
```
- Output goes to `projects/pride-and-prejudice-ch1/exports/w3c/`
- Each file is a valid W3C AnnotationCollection

### CSV (flat tabular)
```bash
core/.venv/bin/palimpsest export projects/pride-and-prejudice-ch1 --format csv
```
- Output goes to `exports/csv/`
- Each CSV has columns: id, track, type, start, end, confidence, evidence_level, creator, value, plus track-specific fields

---

## 6. Launch the Browser

Open **two terminal tabs**:

### Tab 1 — Backend server
```bash
core/.venv/bin/palimpsest serve projects --port 8080
```
Serves all projects in the `projects/` directory.

### Tab 2 — Frontend dev server
```bash
cd browser
npm run dev
```
Vite starts on `http://localhost:5173` (or the next available port — check the terminal output). It proxies `/api` and `/data` requests to the backend on port 8080.

### Open in browser
Navigate to the URL shown in Vite's terminal output (usually **http://localhost:5173**).

---

## 7. Browser Feature Tour

### 7.1 Project Picker
- On first load, you see the welcome screen with a project list
- Click a project to load it
- Or append `?project=pride-and-prejudice-ch1` to the URL

### 7.2 Text View + Annotations
- The main panel shows the reference text as paragraphs
- Entity annotations appear as colored highlights (PER=blue, LOC=green, ORG=orange)
- Sentiment, lexical, dialogue, and topic annotations overlay as additional colors
- Click any highlighted annotation to see its details in the right panel

### 7.3 Detail Panel (right sidebar)
- Shows the full W3C annotation body for the selected annotation
- Displays: body type, entity type, evidence level (E1-E5), confidence score
- **LLM Summary**: click "Summarize" to get an AI summary of the selected paragraph (requires Ollama running with qwen3:8b)

### 7.4 Track Panel (left sidebar)
- Lists all available tracks with annotation counts
- Click the eye icon or press `1`-`9` to toggle track visibility
- Each track shows its evidence level badge (E4, E5)
- Press `0` to toggle all tracks on/off

### 7.5 Text Search (Ctrl+F)
- Press `Ctrl+F` or `/` to open the search bar
- Type a search term — matches highlight in real-time
- "3 of 47 matches" counter updates as you type
- Press `Enter` or `]` to go to next match
- Press `Shift+Enter` or `[` for previous match
- Toggle case sensitivity with the `Aa` button
- Search match positions appear as yellow ticks in the OverviewBar
- Press `Escape` to close search

### 7.6 Overview Bar (bottom)
- Shows density barcodes for each visible track across the full document
- Each colored bar represents annotation density at that position
- Click anywhere on the bar to jump to that position in the text
- When search is active, yellow ticks show match positions

### 7.7 DotplotView (self-similarity heatmap)
- Press `d` to toggle the dotplot panel (bottom)
- If the self-similarity matrix exists (requires Ollama for embeddings), shows an N×N heatmap
- Blue intensity = cosine similarity between paragraph pairs
- Diagonal is always brightest (self-similarity = 1.0)
- Hover to see cell coordinates and similarity value
- Click a cell to navigate to that paragraph in the text view
- Shift+click navigates to the column paragraph instead

**Note**: The dotplot requires embeddings. If you see "Self-similarity matrix not available", run analysis with Ollama first (see Section 9).

### 7.8 Keyboard Navigation
| Key | Action |
|-----|--------|
| `j` / `↓` | Next paragraph |
| `k` / `↑` | Previous paragraph |
| `Ctrl+F` / `/` | Open text search |
| `Escape` | Close search / deselect |
| `1`-`9` | Toggle track N |
| `0` | Toggle all tracks |
| `d` | Toggle dotplot panel |
| `[` / `]` | Previous / next search match |
| `?` | Show keyboard help overlay |

### 7.9 Help Overlay
- Press `?` to show the keyboard shortcut reference
- Press `?` again or `Escape` to dismiss

---

## 8. API Endpoints

With the server running on port 8080, you can test the API directly:

```bash
# List all projects
curl http://localhost:8080/api/projects | python3 -m json.tool

# List tracks for a project
curl http://localhost:8080/api/projects/pride-and-prejudice-ch1/tracks

# Get raw annotation data
curl http://localhost:8080/data/pride-and-prejudice-ch1/tracks/entities.jsonl | head -3

# Get metadata
curl http://localhost:8080/data/pride-and-prejudice-ch1/metadata.json | python3 -m json.tool

# Similarity search (requires embeddings)
curl "http://localhost:8080/api/search?project=pride-and-prejudice-ch1&query=marriage&k=5" | python3 -m json.tool

# AI summary (requires Ollama)
curl -X POST http://localhost:8080/api/summarize \
  -H "Content-Type: application/json" \
  -d '{"passage": "It is a truth universally acknowledged, that a single man in possession of a good fortune, must be in want of a wife.", "model": "qwen3:8b"}'
```

---

## 9. Optional: Enable Embedding Features

Palimpsest auto-detects which embedding backend is available and picks the fastest one:

| Backend | Port | Speed (batch of 32) | Notes |
|---------|------|-------------------|-------|
| **MLX** (preferred) | 8000 | **24ms** (0.8ms/item) | Apple Silicon native, ~56x faster |
| **Ollama** (fallback) | 11434 | 1,356ms (42ms/item) | Also provides LLM summaries |

When you run `palimpsest analyze`, the output will show which backend was used:
```
Embedded 34 paragraphs via mlx     ← MLX was available
Embedded 34 paragraphs via ollama  ← fell back to Ollama
```

If you already have the MLX embedding server running (check with `curl -s http://localhost:8000/embed -X POST -d '{"text":"test"}' -H 'Content-Type: application/json'`), you only need Ollama for LLM summaries — not for embeddings.

### 9a. Ollama (LLM summaries + fallback embeddings)

Ollama provides LLM-powered passage summaries and serves as a fallback for embeddings if MLX is not available.

**Install Ollama** (if not already installed):
```bash
brew install ollama
```

**Start the Ollama server** (leave running in a terminal tab):
```bash
ollama serve
```

**Pull the required models:**
```bash
# Embedding model (2560-dim vectors, ~2.3 GB download)
ollama pull qwen3-embedding:4b

# LLM model for summaries (~4.7 GB download)
ollama pull qwen3:8b
```

**Verify models are loaded:**
```bash
ollama list | grep -E "qwen3-embedding|qwen3:4b"
```

**Re-analyze with embeddings enabled:**
```bash
core/.venv/bin/palimpsest analyze projects/pride-and-prejudice-ch1 --force
```

You should see:
```
  Embedding paragraphs (dim=2560)...
  Embedded 34 paragraphs
```

With embeddings, you get:
- **Self-similarity matrix** — enables the DotplotView heatmap (press `d`)
- **Embedding-based RQA** — more accurate recurrence analysis (vs. TF-IDF fallback)
- **Similarity search** — `/api/search` returns semantically similar paragraphs
- **LLM summaries** — "Summarize" button in the Detail Panel works

### 9b. BookNLP (coreference chains + speaker attribution)

BookNLP adds coreference resolution — identifying that "he", "Mr. Bennet", and "her husband" all refer to the same character. It requires Java 11+ and downloads ~1.5 GB of transformer models on first run.

**Step 1: Install Java 11+**

```bash
brew install openjdk@21
```

After installation, Homebrew will print a symlink command. Run it:
```bash
sudo ln -sfn /opt/homebrew/opt/openjdk@21/libexec/openjdk.jdk \
  /Library/Java/JavaVirtualMachines/openjdk-21.jdk
```

Verify Java is available:
```bash
java -version
# Should show: openjdk version "21.x.x" or similar
```

**Step 2: Install BookNLP + its spaCy model**

BookNLP pulls in PyTorch and TensorFlow as dependencies (~2-3 GB total). This may take several minutes:
```bash
uv pip install booknlp --python core/.venv/bin/python
```

BookNLP requires the `en_core_web_sm` spaCy model (separate from the `en_core_web_lg` used by Palimpsest's own pipeline):
```bash
uv pip install "https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.8.0/en_core_web_sm-3.8.0-py3-none-any.whl" --python core/.venv/bin/python
```

Verify both are installed:
```bash
core/.venv/bin/python -c "import booknlp; print('BookNLP available')"
core/.venv/bin/python -c "import spacy; spacy.load('en_core_web_sm'); print('en_core_web_sm OK')"
```

**Step 3: Re-analyze with BookNLP**

```bash
core/.venv/bin/palimpsest analyze projects/pride-and-prejudice-ch1 --force
```

On first run, BookNLP downloads its transformer models (~1.5 GB). Subsequent runs use the cached models. When BookNLP is available, you get:
- **Coreference track** (`tracks/coreference.jsonl`) — links character mentions across the text
- **Enhanced entity resolution** — canonical character names
- **Speaker attribution** — who said each line of dialogue

**Note**: BookNLP is slow on first run (~2-5 minutes per chapter). It is the only track that requires Java. If you skip this step, Palimpsest works fine with 9 tracks instead of 10 — the pipeline gracefully skips the coreference track and reports it as unavailable.

---

## 10. Verify Signal Outputs

```bash
# Check narrative arc (should be 60 bytes = 5 segments × 3 dims × 4 bytes)
ls -la projects/pride-and-prejudice-ch1/signals/narrative_arc.bin

# Inspect narrative arc values
core/.venv/bin/python -c "
import numpy as np
arc = np.fromfile('projects/pride-and-prejudice-ch1/signals/narrative_arc.bin', dtype=np.float32).reshape(5, 3)
print('Staging:    ', arc[:, 0])
print('Progression:', arc[:, 1])
print('Tension:    ', arc[:, 2])
"

# Inspect RQA metrics
core/.venv/bin/python -c "
import json, numpy as np
m = json.loads(open('projects/pride-and-prejudice-ch1/signals/rqa.json').read())
rqa = np.fromfile('projects/pride-and-prejudice-ch1/signals/rqa.bin', dtype=np.float32).reshape(-1, 3)
print(f'{m[\"metadata\"][\"n_windows\"]} windows, source: {m[\"metadata\"][\"state_vector_source\"]}')
print(f'RR:  [{rqa[:,0].min():.3f}, {rqa[:,0].max():.3f}]')
print(f'DET: [{rqa[:,1].min():.3f}, {rqa[:,1].max():.3f}]')
print(f'LAM: [{rqa[:,2].min():.3f}, {rqa[:,2].max():.3f}]')
"

# Inspect narrative alphabet
core/.venv/bin/python -c "
import json
m = json.loads(open('projects/pride-and-prejudice-ch1/signals/alphabet.json').read())
seq = m['metadata']['sequence']
print(f'Alphabet ({len(seq)} chars, {len(set(seq))} unique states): {seq}')
"

# Check pipeline provenance
core/.venv/bin/python -c "
import json
pr = json.loads(open('projects/pride-and-prejudice-ch1/pipeline_run.json').read())
print(f'Version: {pr[\"palimpsest_version\"]}')
print(f'Tracks:  {pr[\"tracks_computed\"]}')
print(f'Signals: {pr[\"signals_computed\"]}')
print(f'Time:    {pr[\"elapsed_seconds\"]}s')
"
```

---

## 11. Run Tests

```bash
# Python tests (193 tests)
core/.venv/bin/python -m pytest core/tests/ -q

# Rust tests (24 tests)
cargo test --workspace

# Python linter
core/.venv/bin/ruff check core/

# TypeScript type check
cd browser && npx tsc --noEmit && cd ..
```

---

## Quick Reference: Project Structure

```
projects/pride-and-prejudice-ch1/
├── reference.txt              # Normalized source text
├── reference.sha256           # SHA-256 hash
├── metadata.json              # 15-field project metadata
├── pipeline_run.json          # Full provenance record
├── tracks/                    # W3C Web Annotation JSONL
│   ├── segments.jsonl         # Paragraph/section boundaries (E1)
│   ├── entities.jsonl         # Named entities: PER, LOC, ORG (E4)
│   ├── sentiment.jsonl        # Per-sentence VADER sentiment (E5)
│   ├── lexical.jsonl          # Per-paragraph TTR, hapax, etc. (E5)
│   ├── dialogue.jsonl         # Quoted speech + attribution (E5)
│   └── topics.jsonl           # LDA topic assignments (E4)
├── signals/                   # Non-annotation numerical data
│   ├── narrative_arc.json/bin # Boyd 5-segment × 3-dim arc
│   ├── rqa.json/bin           # RR, DET, LAM per window
│   ├── topics_dist.json/bin   # Per-paragraph topic distributions
│   ├── alphabet.json          # K-means narrative state sequence
│   └── self_similarity.json/bin  # N×N cosine matrix (if embeddings)
├── manifests/                 # Browser rendering config per track
├── cache/                     # spaCy docs, embeddings DB
└── exports/                   # W3C, CSV export outputs
```

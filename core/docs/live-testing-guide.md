# Palimpsest M1.2 — Live Testing Guide

All features ready for interactive testing as of 2026-06-07.

---

## Setup (one-time)

You need **two terminal windows** for the full browser experience.

**Terminal 1** — Python CLI + API server:
```bash
cd /Users/nathanielcannon/Claude/Projects/palimpsest/core
```

**Terminal 2** — Vite dev server (browser frontend):
```bash
cd /Users/nathanielcannon/Claude/Projects/palimpsest/browser
```

---

## Phase 1: CLI Pipeline (Terminal 1)

### 1A. Ingest

```bash
# Create a workspace and ingest Pride & Prejudice (full novel, 130K words)
.venv/bin/palimpsest ingest ../fixtures/pride-prejudice-full.txt \
  --workspace ./data \
  --title "Pride and Prejudice" \
  --author "Jane Austen" \
  --year 1813
```

**Expect:** "Project created: pride-and-prejudice" with word count (~122K), paragraph count, sentence count.

```bash
# Second project for testing the picker
.venv/bin/palimpsest ingest ../fixtures/moby-dick-ch1.txt \
  --workspace ./data \
  --title "Moby-Dick Chapter 1" \
  --author "Herman Melville" \
  --year 1851
```

### 1B. Inspect

```bash
.venv/bin/palimpsest info ./data/pride-and-prejudice
```

**Expect:** Metadata table + "Tracks: segments" (only segments until we analyze).

### 1C. Analyze (runs all 5 extractors)

```bash
.venv/bin/palimpsest analyze ./data/pride-and-prejudice
```

**Expect:**
- Progress spinner for each track: entities, sentiment, lexical, dialogue, topics
- Full novel takes ~30-90 seconds (spaCy NER is the bottleneck)
- If any extractor fails, you see a yellow warning and the rest continue

```bash
# Verify all tracks produced
.venv/bin/palimpsest info ./data/pride-and-prejudice
```

**Expect:** 6 tracks listed (segments + entities + sentiment + lexical + dialogue + topics) with annotation counts.

### 1D. Export — W3C JSON-LD

```bash
.venv/bin/palimpsest export ./data/pride-and-prejudice --format w3c
```

**Expect:** Creates `./data/pride-and-prejudice/exports/w3c/` with one `.json` per track. Each file is a valid W3C AnnotationCollection with `@context`, `id` (URN), `type`, `total`, `items`.

**Quick verify:**
```bash
cat ./data/pride-and-prejudice/exports/w3c/entities.json | python3 -m json.tool | head -10
```

Should show the collection header with `"id": "urn:palimpsest:pride-and-prejudice:collection:entities"`.

### 1E. Export — CSV

```bash
.venv/bin/palimpsest export ./data/pride-and-prejudice --format csv
```

**Expect:** Creates `./data/pride-and-prejudice/exports/csv/` with one `.csv` per track.

**Quick verify:**
```bash
head -3 ./data/pride-and-prejudice/exports/csv/sentiment.csv
```

Should show columns like: `id,track,type,start,end,confidence,evidence_level,creator,value,arousal,model,valence`

### 1F. Also analyze Moby-Dick

```bash
.venv/bin/palimpsest analyze ./data/moby-dick-chapter-1
```

---

## Phase 2: Server + Browser (Both Terminals)

### 2A. Start the API server (Terminal 1)

```bash
.venv/bin/palimpsest serve ./data --port 8080
```

**Expect:** "Uvicorn running on http://127.0.0.1:8080" — leave running.

### 2B. Start the Vite dev server (Terminal 2)

```bash
npm run dev
```

**Expect:** "Local: http://localhost:5173/" — leave running.

### 2C. Open browser

Navigate to: **http://localhost:5173**

---

## Phase 3: Browser Feature Testing

### 3A. Project Picker (Welcome Screen)

**What you see:** "Palimpsest" heading + project picker showing your ingested projects.

**Test:**
- Both projects should appear with titles, authors, word counts
- Click "Pride and Prejudice" to load it
- URL should update to `?project=pride-and-prejudice`

---

### 3B. Main Interface Layout

After loading, you should see:

| Area | Location | Contents |
|------|----------|----------|
| Toolbar | Top | Title, author, word count, paragraph count, track count |
| TrackPanel | Left (200px) | 5 tracks with colored dots, evidence badges, counts, shortcut keys |
| TextLinearView | Center | Full text with annotation highlights |
| DetailPanel | Right (280px) | "Click an annotation highlight to view its properties" |
| OverviewBar | Bottom | 5 density barcodes (one per track) |

---

### 3C. Track Toggle (Critical M1.2 Feature)

| Action | Expected |
|--------|----------|
| Click "entities" row in TrackPanel | Entity highlights disappear from text; row becomes faded (opacity 0.4) |
| Click it again | Highlights reappear |
| Press `1` key | Toggles first track (alphabetical: dialogue) |
| Press `2` key | Toggles second track (entities) |
| Press `0` key | Hides all tracks — text becomes clean |
| Press `0` again | Shows all tracks |

**OverviewBar should reflect visibility** — hidden tracks appear faded.

---

### 3D. Text Search

| Action | Expected |
|--------|----------|
| Press `Ctrl+F` or `/` | Search bar appears at top |
| Type "Bennet" | Matches highlighted in text + yellow ticks on OverviewBar |
| Match count shows (e.g., "3/47") | |
| Press `Enter` | Jumps to next match, scrolls into view |
| Press `Shift+Enter` | Previous match |
| Press `[` or `]` | Also navigates matches |
| Press `Escape` | Closes search |

---

### 3E. Annotation Interaction

| Action | Expected |
|--------|----------|
| Click any colored highlight in text | DetailPanel populates with annotation properties |
| | Shows: body type, evidence badge (E4/E5), confidence %, excerpt, ID, creator, offsets |
| Click a dialogue annotation (orange underline) | Should show speaker and verb fields if attribution was found |
| Click a sentiment annotation (green highlight) | Shows valence, arousal, model="vader" |
| Click the X button in DetailPanel | Deselects annotation |

---

### 3F. OverviewBar Navigation

| Action | Expected |
|--------|----------|
| Click near the right end of any barcode row | Text scrolls to the end of the document |
| Click near the left end | Scrolls to the beginning |
| Click in the middle | Scrolls to approximately the middle |

---

### 3G. Keyboard Navigation

| Key | Action |
|-----|--------|
| `j` or Down arrow | Select + scroll to next paragraph |
| `k` or Up arrow | Select + scroll to previous paragraph |
| `d` | Toggle dotplot view (state toggles, no renderer yet) |
| `?` | Opens keyboard shortcut help overlay |
| `Escape` (while help open) | Closes help overlay |

---

### 3H. AI Summary (Requires Ollama)

If you have Ollama running (`ollama serve` in another terminal):

1. Click an annotation highlight
2. In the DetailPanel, scroll down to "AI Summary"
3. It should generate a contextual summary of the passage

If Ollama is not running: you'll see a message indicating the service is unavailable. No crash.

---

## Phase 4: Edge Cases

| Test | What to look for |
|------|-----------------|
| Search for a word that doesn't exist | "0/0" matches, no crash |
| Toggle all tracks off, then search | Search still works on raw text |
| Rapidly click different annotations | DetailPanel updates cleanly each time |
| Resize browser window very narrow | Layout should remain usable (panels have fixed widths) |
| Navigate to `?project=nonexistent` in URL | Should show error state, not crash |
| Check `./data/pride-and-prejudice/pipeline_run.json` | Should have python_version, spacy_model, booknlp_available, timing |

---

## Quick Smoke Test (CLI only, no browser)

```bash
cd /Users/nathanielcannon/Claude/Projects/palimpsest/core

.venv/bin/palimpsest ingest ../fixtures/pride-prejudice-ch1.txt \
  --workspace /tmp/palimpsest-test --title "PP Smoke Test" && \
.venv/bin/palimpsest analyze /tmp/palimpsest-test/pp-smoke-test && \
.venv/bin/palimpsest export /tmp/palimpsest-test/pp-smoke-test --format csv && \
.venv/bin/palimpsest info /tmp/palimpsest-test/pp-smoke-test
```

---

## CLI Command Reference

```
palimpsest ingest FILE --workspace PATH --title TEXT [--author TEXT] [--year INT]
palimpsest info PROJECT_DIR
palimpsest analyze PROJECT_DIR [--force]
palimpsest export PROJECT_DIR --format {w3c,csv,paf} [-o OUTPUT_DIR]
palimpsest serve WORKSPACE [--port INT]
palimpsest --version
```

---

## Known Limitations (by design, not bugs)

- **VADER sentiment is irony-blind** — the opening line of P&P will score weakly positive despite being ironic. Evidence level E5 signals this is rule-based.
- **Dialogue speaker is raw text** — "his lady" won't be resolved to "Mrs. Bennet" until coreference (M1.3b).
- **Single-quote pattern (confidence 0.60)** may produce false positives on contractions (don't, it's).
- **Panel widths are fixed** — no drag-to-resize yet (M1.3).
- **Topics stacked-bar view** — declared in manifests but no renderer yet (M1.3).
- **No per-entity-type filtering** — all entity types shown together (M1.3).

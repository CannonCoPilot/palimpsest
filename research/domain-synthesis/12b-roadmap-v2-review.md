# Critical Review: Palimpsest Development Roadmap v2.0

**Date**: 2026-06-06
**Purpose**: Second-pass review after v1→v2 rewrite. Focus on what the first review missed.

---

## 1. Structural Issues

### 1.1 Milestone 1.3 Is Overloaded

Milestone 1.3 packs four independent capabilities into one 2-week block: BookNLP integration, four new Base tracks, an embedding service, and the DotplotView. Any one of these could stall the entire milestone. BookNLP's Java dependency alone could burn a week of troubleshooting on a clean machine.

**Fix**: Split 1.3 into two sub-milestones:
- 1.3a (Week 5-6): Remaining Base tracks (narrative arc, self-similarity, RQA, alphabet) + embedding service. These are pure Python, no external dependencies.
- 1.3b (Week 6-7): BookNLP integration + DotplotView. BookNLP is optional (has a fallback path), so if it stalls, the dotplot can ship without it.

### 1.2 The Walking Skeleton Test Is at the Wrong Milestone

The "walking skeleton test" is defined in Milestone 1.3 — but the skeleton should be testable after EVERY milestone. The v2 roadmap correctly says "vertical slices" but then doesn't define end-to-end smoke tests for Milestones 1.1 and 1.2.

**Fix**: Define a smoke test per milestone:
- 1.1: Ingest TXT → entity track → see highlights in browser (30 seconds end-to-end)
- 1.2: Ingest PDF → 5 tracks → see tracks in browser with toggles + LLM summary (2 minutes)
- 1.3: Full IJ → 12 tracks → dotplot + linked views + summary (3 minutes)
- 1.4: Two texts → cross-text dotplot + export (5 minutes)

### 1.3 No Data Migration Strategy

The roadmap has PAF evolving from v0.1 (Milestone 1.1) through updates (1.2) to v1.0 (1.3). But it doesn't address: what happens to annotations created under v0.1 when the format changes in v1.0?

**Fix**: State the policy explicitly: during Phase 1, PAF is unstable. All track files are recomputable from source text + pipeline version. No user-created annotations exist yet (that's Phase 2). Therefore: PAF format changes during Phase 1 are free — just recompute. Document this as a known constraint: "Phase 1 projects may need to be re-ingested when upgrading Palimpsest."

### 1.4 Monorepo Structure Not Detailed

The tech decisions table says "Monorepo: `core/` (Python), `browser/` (React), `models/` (trained), `specs/` (LFO, PAF)" but the Phase 1 plan doesn't reference this structure. The project directory layout (`projects/{text-id}/`) is for user data, not for source code. These are two different trees and both need to be specified.

---

## 2. Missing Technical Details

### 2.1 FastAPI Server Not Specified

The browser (React) needs to talk to the backend (Python). The tech decisions say FastAPI, but no milestone specifies when the API server is built, what endpoints it exposes, or how the browser communicates with it. Is the browser served by FastAPI? Does it call FastAPI endpoints for data? Or does it read PAF files directly from disk?

**Fix**: Specify the communication architecture in Phase 1:
- Option A (simpler, Phase 1): Static file serving. `palimpsest serve` runs a static file server that serves the React app + the project directory. The browser reads PAF files via fetch from the file server. No API. Fast to build.
- Option B (Phase 2+): FastAPI REST API. Browser calls API endpoints for annotations, search, LLM services. Required when human annotations need a write path.
- Recommendation: Option A for Phase 1, transition to Option B in Phase 2 when annotations become writable.

### 2.2 Browser Build Tooling Not Specified

The React app needs a build system (Vite, Next.js, Create React App, etc.). This isn't glamorous but it's a real decision that affects development speed. MobX-state-tree + TypeScript + D3 + Canvas rendering is a specific stack that needs specific tooling.

**Fix**: Specify Vite as the build tool (fast HMR, TypeScript-first, no framework opinions).

### 2.3 PAF Column Semantics for Non-Span Features

PAF is defined as a span format (start/end character offsets). But several Base tracks produce non-span data:
- `self_similarity.paf` — a matrix, not spans
- `narrative_arc.paf` — a 15-dimensional vector per 5 text segments
- `topics.paf` — a topic distribution vector per segment
- `alphabet.paf` — a single encoded string

These don't fit the 9-column GFF3 model. The roadmap glosses over this.

**Fix**: Define two PAF variants:
- **PAF-Span**: the 9-column format for span annotations (entities, dialogue, sentiment per sentence)
- **PAF-Signal**: a parallel format for continuous/vector signals (matrices, arcs, distributions). Simplest: JSON or NumPy `.npz` files in a `signals/` subdirectory, with a manifest linking them to the text reference.

### 2.4 How Does the Browser Load a 300-Page Text?

The roadmap says "smooth scrolling for 300-page texts with 5+ active tracks." But rendering 300 pages of text in the browser DOM is a known performance problem. Solutions exist (virtualized scrolling, windowed rendering) but the roadmap doesn't acknowledge the challenge.

**Fix**: Specify virtualized scrolling from the start. The TextLinearView renders only the visible viewport + a buffer zone. Annotations for the visible region are fetched on demand (or from an in-memory index). This is the same approach JBrowse uses — never render more than the viewport.

---

## 3. Ambiguities

### 3.1 "Segments" Are Underspecified

The segmenter produces sentences, paragraphs, and sections — but which segments are the "units" for analysis? Are topics computed per-sentence? Per-paragraph? Are entities span-level (they can cross sentence boundaries)? Is the self-similarity matrix sentence×sentence or paragraph×paragraph?

**Fix**: Define the concept of "analysis units" explicitly:
- **Sentences**: the base segmentation unit. All character offsets are sentence-aligned.
- **Paragraphs**: the default analysis unit for most tracks (topics, sentiment, lexical stats). Features are computed per-paragraph.
- **Sections**: structural groupings (chapters, parts). Used for overview-level aggregation.
- **Spans**: arbitrary character ranges. Used for entities, dialogue quotes, and custom annotations. Spans can cross paragraph boundaries.

### 3.2 "12 Base Tracks" Count Is Inconsistent

Milestone 1.2 produces 5 tracks (entities + 4 new). Milestone 1.3 adds 4 more tracks (narrative_arc, self_similarity, rqa, alphabet) plus BookNLP upgrades to existing tracks. That's 9 track files. The "12 tracks" claim doesn't add up — unless coreference and the mode placeholder are counted separately, plus the segments file itself. The count should be precise.

### 3.3 Embedding Model Sizing

The tech decisions say "Qwen3-Embedding via Ollama or MLX" producing 2560-dim vectors. But sqlite-vec performance degrades above ~1000 dimensions for large collections. For a 300-page novel with ~3000 paragraphs, 2560-dim is fine. For a 60-novel corpus (Phase 5), that's 180K vectors at 2560-dim — sqlite-vec may struggle.

**Fix**: Use 2560-dim for Phase 1 (single-text, small collection). Revisit for Phase 5 with dimensionality reduction (PCA to 768 or 1024) or switch to faiss for corpus-scale operations.

---

## 4. Things the v2 Got Right (Preserve These)

- Principle 2 ("spec by building") eliminates the waterfall trap completely
- LLM in Milestone 1.2 establishes the AI-assistant identity early
- Cross-text dotplot in 1.4 gives the "palimpsest experience" in Phase 1
- Active learning specified as few-shot + embedding classifier (realistic)
- ModeHMM training corpus fully specified with selection criteria
- Degradation paths for every component
- Phases 7-8 explicitly labeled as stretch goals
- Risk registry includes "motivation decay" — honest and important

---

## 5. Summary of Changes Needed for Phase 1 Detail Plan

1. Split Milestone 1.3 into 1.3a (pure Python tracks) and 1.3b (BookNLP + DotplotView)
2. Define smoke tests per milestone, not just at 1.3
3. State PAF instability policy for Phase 1 (recompute on format change; no user data to migrate)
4. Specify monorepo source code layout
5. Specify browser↔backend communication: static file serving in Phase 1, FastAPI in Phase 2
6. Specify Vite as build tool
7. Define PAF-Span vs PAF-Signal variants (or signals/ directory for non-span data)
8. Specify virtualized scrolling for TextLinearView
9. Define analysis units (sentence, paragraph, section, span) explicitly
10. Clarify the exact track count and track file inventory

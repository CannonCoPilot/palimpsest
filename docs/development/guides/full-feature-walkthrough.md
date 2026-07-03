# Palimpsest — Full-Feature Walkthrough & Stress-Test Guide

**Audience:** a comparative genomicist stress-testing Palimpsest end-to-end through the browser UI.
**Corpus for this run:** KJV, Douay-Rheims (DR), and 1599 Geneva Bibles → extract **Matthew** and **Mark** from each → 6 subtext projects → 1 collection.
**Scope:** every capability from import to N-way corpus analysis, labeled by build status, with the genomics analogue and the exact click-path for each.

> This guide complements `docs/development/WALKTHROUGH.md` (which covers only the single-text Wave-0 flows and predates the Collections tier). Everything below is current as of the C1–C7 collections build + the full 2026-07-01 audit remediation (clusters #11–#14, all shipped) at `HEAD` `46b5283`. Status tags reflect that post-remediation state — a 🟡/🔧 tag is a genuine open item, not in-flight churn.

---

## How to read this document

Each feature is tagged with a **status** so you never confuse "not built yet" with "broken":

| Tag | Meaning |
|-----|---------|
| ✅ **SHIPPED** | Works in the browser now; exercised in-browser. |
| 🟡 **BUILT** | Implemented + unit-tested, but not yet browser/Playwright-verified against a live server, **or** has an in-flight fix landing this session. |
| 🔧 **KNOWN GAP** | Expected to work / should exist, but is currently a stub, dead-end, or audit-flagged bug. Note these — they are real findings, not your setup. |
| ⏳ **DEFERRED** | Intentionally scoped for a later phase; absence is by design. |

Each section also gives you **▷ Probe & note** prompts — the specific things worth stress-testing and recording, since your notes will be digested into development items afterward.

**A word on the framing.** Palimpsest is architected on comparative-genomics analogies down to the algorithm level (Smith-Waterman/LASTZ seed-and-extend, PAF export, union-find pangenome graphs, neighbor-joining trees over Jaccard distance, ANN/MinHash candidate generation with estimated recall). Your mental model transfers almost directly. Where the linguistic problem diverges from the genomic one, I call it out — those divergences are exactly where the interesting methodology questions live (see §7.3, the core/shell over-merge problem, which is the single most important open question for a synoptic corpus).

---

## Part 0 — Orientation: the object model & coordinate machinery

Before clicking anything, internalize four objects and two coordinate maps. Everything else is a consequence.

### 0.1 The four-object model  ✅

| Palimpsest object | What it is | Genomics analogue |
|---|---|---|
| **Work** | The abstract intellectual work ("the Gospel of Matthew"). Identity only — a user-asserted `work_id` tag, never auto-inferred. | A **taxon** ("mouse"). |
| **Imported Text** (Source/Edition) | One concrete ingested file (EPUB/PDF/HTML/TXT), content-hashed. KJV-Matthew and DR-Matthew are two Imported Texts of arguably one Work. | A specific **assembly** (GRCh38 vs hg19). |
| **Project** | A workspace over one Imported Text under one *analytical configuration* — masking policy, section detection, the analyzable frame + its `OffsetMap`. **This is the operand of every analysis.** | An **annotated assembly under a specific track/masking hub**. |
| **Collection** | A named grouping of Projects for co-analysis, plus collection-level policy + artifacts: the shared embedding-space contract, the alignment graph, cross-text/corpus results, collection masking. | The **comparative-genomics workspace / alignment set** — the genomes you chose to compare *and* the alignment between them. |

The membership graph is a **DAG, not a tree**: a Work has many Imported Texts; an Imported Text backs many Projects (different masking → different analyzable views); a Project belongs to many Collections; and a Project may **derive from a parent Project** (subtext extraction — this is how you'll get Matthew out of a whole Bible). Every edge is navigable in both directions (`GET /api/projects/{id}/lattice`).

### 0.2 Reference-free corpus model  ✅ (design decision OQ-1)

The corpus is a **co-equal alignment graph** (the pangenome idiom), *not* a reference-anchored MSA. No member is a privileged backbone. A "root" is a **per-view lens** — a member you temporarily designate as the coordinate axis for one synteny/pairwise/translation view — computed *on demand by projecting the graph*, never the ground truth. This is the pan-genome-graph-vs-single-reference decision, made deliberately in favor of the graph.

Consequence for you: when you designate KJV-Matthew as "root" in the Corpus tab, you are choosing a projection lens, exactly like picking a reference genome to display a multi-way alignment against. Switching roots re-projects; it does not re-analyze.

### 0.3 The three zoom tiers  ✅

1. **Corpus overview** (N-way): block map, all-pairs matrix, phyletic tree — the whole alignment set at once.
2. **Pairwise** (A vs B): heatmap + local-alignment dotplot + ribbons — one WGA.
3. **Single-text browser**: one assembly with its annotation tracks.

Click-through flows overview → pair → single-text (e.g. click a cell in the all-pairs matrix → jumps to that pair's dotplot).

### 0.4 Two coordinate maps — the assert-or-fail spine

- **OffsetMap** (single-text): maps between **original** document coordinates and the **analyzable** text (what remains after masking excises verse numbers, headers, endnotes). Masking is *deepest-section-wins*. Every extractor runs on the analyzable frame and its output is remapped back to original coordinates by an assert-or-fail discipline — an offset that can't be placed raises `UnmappedCoordinateError` rather than landing silently in the wrong place. This is the coordinate-liftover contract you'd want from any tool that excises regions before analysis.
- **AlignmentMap** (cross-text, C5): once an A↔B alignment exists, it *is* an OffsetMap that maps B's coordinates into A's frame. This drives **liftover** — projecting A's masks/annotations onto B (the genomic liftOver). As-built it is **block-granular**: an interval lifts to the whole aligned paragraph block, not a proportional sub-span, and intervals touching no aligned block are honestly reported as `dropped`. It refuses a char-precision the paragraph-level alignment never established.

### 0.5 Metric congruence — the compatibility contract  ✅ (FR-27)

A cross-text cell `(Mi, Nj)` is meaningful **only if Mi and Nj are the same kind of metric**. Every per-chunk metric carries a **congruence key** = analysis-type + model/params + dimensionality. Two members are "comparable on metric X" iff their X-keys match. Mismatch → a loud **409** + an explicit *reconcile* action (re-embed to a common key), never a silent comparison. This is the "you cannot compare coordinates across unaligned assemblies / different embedding models" guard, enforced at the API boundary.

> Design subtlety worth appreciating: the per-text *analyzable digest* is deliberately **excluded** from the cross-project congruence key. Two different texts always have different digests, so including it would make cross-text comparison impossible by construction. The digest stays an *intra*-project coherence check.

**▷ Probe & note (Part 0):** Does the UI ever *let* you compare incongruent metrics without warning? Does switching "root" ever mutate stored results (it shouldn't — it's a projection)? Is the Work/Edition/Project distinction visible anywhere in the UI, or only implicit?

---

## Part 1 — Import (the three Bibles)

**Genomics analogue:** sequencing + assembly + annotation lift-in. Import normalizes the raw file, then a layout parser calls structural features (books/chapters/verses) the way a gene-model annotator calls features on a new assembly.

### 1.1 Purpose-built Bible import profiles  ✅

Palimpsest auto-detects a **content profile** from the file and applies it during assembly. All three of your Bibles have dedicated profiles:

| Profile | Applied to | What it does |
|---|---|---|
| `PROFILE_KJV` | KJV | Strips `<span class="verses">` (verse-number spans). |
| `PROFILE_GENEVA` | 1599 Geneva | Strips footnote/middlenote anchors and digit-only `sup` verse numbers; skips a known front-matter spine file. |
| `PROFILE_DOUAY_RHEIMS` | DR | **Preserves** the verse-number prefixes ("1:1. ") in the text because they carry the canonical reference and delimit verses — then the *masking layer* marks each number token masked while the verse prose stays analyzable. Also promotes DR's heading `div` class to `<h2>`. |

This matters for your stress test: **DR verse numbers survive into the text as maskable tokens; KJV/Geneva verse numbers are stripped at import.** So the three Bibles reach the analyzable frame by different routes — a good thing to verify produces equivalent verse structure.

Detection samples HTML across the *whole* spine (endpoint-inclusive), because Geneva is front-matter-heavy and a shallow sample would misclassify it.

### 1.2 The Import Wizard — 5 steps  ✅

Reach it from the landing page: **Home → Import a Text**, or **Library → Import**. Files already sitting in the `imports/` drop-folder appear in Step 1; you can also **Upload from file** (`.epub/.txt/.pdf/.html/.md`).

| Step | UI | Under the hood | Endpoint |
|---|---|---|---|
| **1 Scan** | File list grouped by folder; "In library / Other version" badges; **Import & Scan**. | Extracts text (format dispatch), strips watermarks, normalizes (NFC, boilerplate strip, quote/whitespace normalize), computes `reference.sha256` (the coordinate anchor). | `POST /api/import/local/stream` (SSE progress) or `POST /api/import` (upload) |
| **2 Detect** | Full-text reader; **Detect Formatting**; masked regions highlight; right-click → mask ops. | Auto-classifies typed layout sections (front matter, book, chapter, verse, endnotes…). Scripture detection: ≥8 canonical book-name matches promotes headings to `book` divisions with chapters nested. Persists `applied=false`. | `POST /api/projects/{id}/sections/detect` |
| **3 Map** | `SectionMinimap` with Edit/Overview toggle; drag boundaries; right-click add. | User-edited section ranges/types; recomputes parent containment (the section forest). | `PUT /api/projects/{id}/sections` |
| **4 Mask** | Per-type keep/mask checkboxes with counts; **Add custom layer** (color + name); live masked-% readout. | Sets `mask_by_type`; verse numbers default to masked. | `PUT …/sections` |
| **5 Apply** | Masked-% summary; **Confirm & Apply**. | Persists the masking decision (`applied=true`), writes the unified `elements` track. **Does not run analysis** — masks apply lazily when extractors run. | `POST /api/projects/{id}/sections/apply` |

**Under the hood — masking is deepest-section-wins.** For each elementary text segment, the *smallest* covering section decides masked/unmasked (an O(N log N) heap). So a `mask=yes` header nested inside a `mask=no` chapter carves only the header window. The result is a sorted, disjoint, merged interval set — the "masking contract." Verse-number tokens and hidden repeats are unioned in as `extra_masked`.

**Gold-map path:** `POST /api/import/local` accepts a `layout_path` — a pre-generated masking map applied verbatim and **sha256-verified** against the ingested text (409 on mismatch). This is how the reproducible gold Bible fixtures are built. As of 2026-07-03 it is also **first-classed by id** through a browse-and-apply **Gold Library** UI, a `palimpsest gold` CLI group, and a `GET/POST /api/gold` API — see the dedicated **"The Gold Set"** section after Part 5.

### 1.3 What import captures  ✅

`metadata.json` records id/title/language/source-format/`reference_sha256`/word-paragraph-section-sentence-character counts/author/year; EPUB adds ISBN/publisher/endnote-count/cover. Subtext children additionally record `parent_project_id`, `parent_reference_sha256`, `ingest_method`, `derivation`, and a loose `work_id`.

**▷ Probe & note (Part 1):**
- Do all three Bibles auto-detect the right profile? (Watch the Geneva front-matter case especially.)
- After Apply, are Matthew and Mark each a single clean `book` section in all three, with chapters nested? (This gates subtext extraction.)
- Are DR's preserved verse numbers actually masked (greyed) in the reader, matching KJV/Geneva where they were stripped?
- **KNOWN GAP** 🔧: the ImportWizard's masked-region editing is powerful but fiddly; note any case where a chapter/verse boundary is mis-detected, since a bad `book` boundary will contaminate the extracted subtext.

---

## Part 2 — Subtext extraction (Matthew & Mark from each Bible)

**Genomics analogue:** excising a gene/region from an assembly into its own coordinate system, while retaining a liftover back to the parent. The child is a first-class "assembly" but remembers its `parent_project_id` and carries an `OffsetMap` so annotations lift both ways.

### 2.1 The Subtext Wizard  ✅ (FR-43)

**This is not in the Import Wizard.** Path:
1. Open the Bible project → **Mask** button in the top toolbar (opens the Masking drawer).
2. In the drawer → **Derive subtext…** (opens the Subtext Wizard).
3. Three stages:
   - **Stage 1 — Extract layers:** check the type-layer whose spans form the subtext (e.g. `chapter`, or `chapter`+`verse`). Below, an **optional container scope** (volume/part/book/appendix) lets you **restrict to specific books** — tick **Matthew** (and/or Mark) here. "Leave empty to use the whole document."
   - **Stage 2 — Refine elements:** elements grouped by container; deselect individual chapters or toggle a whole book off.
   - **Stage 3 — Generate:** name it ("KJV — Matthew"), choose/auto-create a target collection, preview the coverage bar, **Generate subtext**.

Endpoint: `POST /api/projects/{parentId}/derive/stream` (SSE). On completion you can **Open subtext** as its own project.

> **To produce your six projects:** for each of KJV/DR/Geneva, run the wizard twice — once with the **Matthew** container, once with **Mark** — `extraction_types=["chapter"]` (add `"verse"` if you want verse granularity). Each generate auto-links parent+child into a `{parent}+subtexts` collection.

### 2.2 Under the hood — the coordinate remap  ✅

`derive_subtext` (a) resolves the container spans, (b) computes kept spans = every section of the extraction type geometrically inside the container, (c) builds an `OffsetMap`, (d) **reuses the parent's spaCy segmentation** (the big speedup — no re-segmenting), (e) remaps the parent's layout, verse index, and non-structural tracks onto the child, (f) writes a normal project with `ingest_method="subtext_derivation"`.

The key method is `OffsetMap.inverse_span`, which **keeps ranges that bridge excised gaps** — mapping first→last char so greyed/masked content sits *inside* the lifted span (the "as if it weren't there" semantics an analysis window wants). This is the same liftover discipline you'd expect mapping features across a gapped alignment.

**▷ Probe & note (Part 2):**
- Does the container scope correctly isolate *only* Matthew / *only* Mark? Check the coverage preview and the child word-count against the known chapter count (Matthew 28 ch, Mark 16 ch).
- Do verse boundaries survive the derivation (child verses still masked correctly)?
- Does the auto-created collection contain the right members? Does the **lattice** (Members tab) correctly show parent = the full Bible, siblings = the other book from the same Bible?
- **Methodology note for you:** extraction is *geometric* (spans inside the container), independent of `parent_id`. If a chapter heading was mis-typed at import, it will silently leave/enter the subtext. Worth a spot-check.

---

## Part 3 — Single-text analysis (each of the 6 books)

Once a book is open, seven tabs are available (Alt+1…Alt+7): **Reading, Browser, TextHiC, Characters, Analysis, Compare, Corpus**. This part covers the five single-text tabs; Compare and Corpus get Parts 4–5.

### 3.1 Reading tab  ✅

Linear text with a **4-level semantic zoom** (work → chapter → paragraph → sentence), annotation overlays, and a live masking overlay. Side panels (Reading only): **SectionNav** (heading list), **TrackPanel** (per-track visibility, drag-reorder, dense/pack/inline display modes, confidence-threshold slider, element-type sub-toggles), **DetailPanel** (selected annotation's properties).

Two AI affordances in the DetailPanel (both degrade gracefully if Ollama is down):
- **StateExplainer** — "Explain this state" for a LitHMM annotation → `POST /api/explain` (LLM narrates an HMM state from its feature profile + sample passages).
- **LLMSummary** — "Summarize" any positioned passage → `POST /api/summarize`.

**▷ Probe & note:** Does the character-filter banner (set from the Characters tab) correctly narrow to paragraphs mentioning a figure? Does semantic zoom stay performant on a full gospel (virtualizes above 200 paragraphs)?

### 3.2 Browser tab  ✅

A **UCSC-genome-browser-style** linear track view — this is the ADR-005 JBrowse2-pattern surface. TickerTape text strip when zoomed in, Book:Chapter locator when zoomed out, masked ranges greyed. Toolbar: Tracks drawer, zoom, fit, pan, coordinate readout, **Jump to…** (`5000` or `¶42`). Each track lane has 5 display modes (Ribbon/Detail/Expanded/Condensed/Hide) and a "highlight in text" toggle. The `elements` track splits into Structure/Content/Headings/Notes group lanes; a **VersesLane** lazy-loads the verse index when zoomed below ~30k chars.

**Genomics analogue:** this is your genome browser — tracks = annotation tracks, the OverviewBar = the chromosome ideogram with a draggable viewport.

**▷ Probe & note:** Do verse lanes line up with chapter lanes? Is the coordinate readout in original or analyzable space, and is that labeled? (Coordinate honesty matters here.)

### 3.3 Analysis tab — the computation suite  ✅

Four sub-tabs. Header shows an **IntegrityBadge** and **Compute All (N)**.

#### 3.3.1 Tracks sub-tab  ✅
A table of every registered track with status (computed/pending/running/failed), output type, evidence level, and dependency chips. Per-row: **Compute** (`POST /api/projects/{id}/analyze/{track}`), **Re-run…** (param dialog), **Details** (method + explanation), **Retry** on failure. A dependency graph renders below.

The track roster (auto-discovered, run in topological order) — what each computes and whether it needs an embedding space:

| Track | Computes | Needs embedding? | Genomics analogue |
|---|---|---|---|
| **chunking** ✅ (layer-keyed, plural) | Segments the analyzable text. Modes: `word` (N-word windows), `slide` (overlapping), `punctuation`, `verse`, `smart` (target-N grown per verse/paragraph). Contract-checked (in-bounds, sequential, disjoint). | No | Windowing / tiling the sequence. |
| **embedding** ✅ (layer-keyed, plural) | Embeds a chosen chunk layer via MLX/Ollama (Qwen3-Embedding-4B, dim 2560) → SQLite-vec store. Records a `model_fingerprint` = the cross-text congruence key. | **Is** the embedding space | k-mer/vector representation of each window. |
| **narrative_arc** ✅ | Boyd function-word arc: per-segment staging/progression/tension word ratios → (segments×3) vector. | No | A positional composition signal along the sequence. |
| **rqa** ✅ | Recurrence Quantification Analysis over sliding paragraph windows: RR, DET (determinism), LAM (laminarity). Uses embeddings if present, else TF-IDF. | Optional (upgrades) | Recurrence-plot quantification — directly familiar from nonlinear time-series/genomics. |
| **repeats** ✅ | Exact n-gram repeats (length min..max words recurring ≥k times) → merged char intervals. Order-independent of chunking. | No | Tandem/interspersed repeat detection. |
| **self_similarity** 🟡 (Configure-only) | N×N chunk similarity matrices + LASTZ local alignments (see §3.4). | Only for cosine/jaccard | **Self-alignment dotplot.** |
| **characters** ✅ | Entity index from coreference+NER: canonical names, aliases, mention counts, density; co-occurrence matrix. | No | Feature catalog + interaction matrix. |
| **sections / verses** ✅ (structural) | The layout forest and verse index; served from disk, not recomputed. | No | The reference gene model. |
| **lithmm / topics / sentiment / entities / coreference / boundary_detection** ✅* | HMM state model (LitHMM), topic model, sentiment (**VADER only** — Hedonometer withheld 🔧), NER, coreference, boundary detection. | Varies | HMM segmentation / mixture models over the sequence. |

*Enumerated live by `GET /api/projects/{id}/analysis/status`; availability depends on optional deps (`palimpsest doctor` reports hmmlearn/BookNLP/spaCy/Ollama/MLX health).

Honesty features baked in: failed runs show the real error; **clamped params** and **HMM→KMeans fallback** are surfaced inline (`runInfo` reports what *actually* ran, not what was requested — the disk is the source of truth). Embedding-dependent tracks pop an **EmbeddingDialog** (a cost gate) before running `POST /api/projects/{id}/embeddings/compute` — embedding is **never** auto-run (NFR-4).

#### 3.3.2 Profile sub-tab  ✅
`ProfileDashboard` renders the descriptive/distributional statistics from the profile track: **TTR, MATTR, MTLD, Yule's K, Zipf slope, Heaps' β**, plus length histograms + ECDF. All *descriptive, not inferential* (honest-viz principle). Empty state: "Run the profile track."

> These are the stylometric/lexical-diversity leaves — length-robust diversity (MATTR/MTLD) vs length-sensitive (TTR), richness (Yule's K), and the Zipf/Heaps power-law fits. For a genomicist: think GC-content/k-mer-spectrum/rarefaction-curve descriptors of a sequence.

🔧 **KNOWN GAP:** the text-level profile has **no dedicated HTTP endpoint** — it's produced as a track and read from `signals/profile.json`. The only live per-*layer* analytics endpoint is chunk-layer stats (below). If the Profile tab is blank, the profile track hasn't been computed.

#### 3.3.3 Representations sub-tab  ✅
An `EmbeddingScatter` per embedding layer — a 2-D **PCA** projection (`GET …/embedding/{label}/projection`). Empty state: "No embedding layers yet."
⏳ **DEFERRED:** UMAP. `?method=umap` deliberately returns **400** ("UMAP deferred, OQ#4") — a loud reject, not a silent PCA substitution.

#### 3.3.4 Explore sub-tab  ✅ (FR-13/14)
`LayerWorkbench`: a **LayerManager** (drag-reorder, hide/show, overlay toggles) + a lane stack + up to **two side-by-side LayerStatsPanels**. Each panel offers a *selectable visualization set*:
- **Chunk layer:** length histogram / ECDF / **by-element violin** / **boundary-alignment** bar (`GET /api/projects/{id}/chunking/{label}/stats`). Boundary-alignment = the fraction of chunk starts within tolerance of a structural (sentence/paragraph/verse) boundary — a chunking-quality diagnostic.
- **Embedding layer:** scatter / pairwise-distance histogram / NN-distance histogram / cosine heatmap (block-reduced above a size cap) / k-means clusters (`…/embedding/{label}/{distances|heatmap|clusters}`).

**Genomics analogue:** the layer manager is a track-hub; the per-layer stats are QC plots on a chosen representation (insert-size histogram ≈ chunk-length histogram; a similarity heatmap ≈ an all-windows dotplot).

#### 3.3.5 Integrity badge  ✅ (FR-9)
`GET /api/projects/{id}/integrity` runs the substrate-contract validators as a presentation layer over the *producer's own* validators (so it can't drift): masked-partition, span bounds, segment contract, **section-tree containment**, **OffsetMap round-trip** (`inverse(translate(x))==x` sampled), analyzable↔original length agreement, encoding sanity. Each returns pass/violation/na.

> This is your assembly-QC / validation report. The round-trip check is the one to watch — it's the guarantee that annotations lift back to original coordinates losslessly.

#### 3.3.6 The positional/lexical leaf analyses  ✅ (FR-10)
Exposed as endpoints (surfaced in various panels; some are API-first): **KWIC** concordance (`/kwic`), **collocations** (PMI + Dunning G², `/collocations`), **dispersion** barcode (`/dispersion`), **near-duplicate finder** (`/duplicates` — same signal as the repeats masking layer). All return **original document coordinates**. All word/token-only (no embedding).

**▷ Probe & note (Part 3):**
- Compute a `word/100` chunk layer, then an embedding layer on it, on (say) KJV-Matthew. Watch the cost gate fire. Does the Representations scatter look sane (chapters clustering)?
- Chunk-layer **boundary-alignment**: does verse-mode chunking hit ~100% boundary alignment (it should — chunks *are* verses)?
- Run **collocations** — do PMI vs Dunning G² rank differently (they should; G² is the χ²-like contingency test, PMI the pointwise MI)? Recent audit fixes corrected the G² zero-cell handling and PMI normalization; verify the numbers look right.
- Run **Integrity** on a *derived* subtext — does the OffsetMap round-trip pass on the child (it validates the derivation coordinate math)?
- 🔧 Note: **self_similarity has no bare "Compute"** — it is **Configure-only** (§3.4). If you expect a one-click run and don't find it, that's by design (a bare run would 400).
- 🔧 Note: **sentiment offers only VADER**; Hedonometer is intentionally absent until a backend exists.

### 3.4 TextHiC tab — self-similarity dotplot  🟡

The **self-alignment dotplot**: an N×N chunk-similarity heatmap with LASTZ-style local alignments overlaid. Double-buffered canvas (matrix + overlay). Toolbar: palette (Blues/Viridis/Plasma/Diverging), zoom/fit, PNG/SVG export, **Filters** (threshold, diagonal on/off, **metric** dropdown = cosine/jaccard/word_overlap/edit_distance, alignments on/off, chapters grid, **chunk-size** slider 5–25 words with a "cached / not cached" indicator). An **alignments list** shows each LASTZ hit with identity % and an honest "exact/approximate boundaries" label; per-row **View** opens the paired passages.

**Under the hood** (`self_similarity` track): metrics `cosine`/`jaccard` (embedding-based) and `word_overlap`/`edit_distance` (text-only) → N×N matrices; LASTZ **seed-and-extend** finds top-K off-diagonal optima and extends **parallel (1,1)** for repeats *and* **antiparallel (1,−1) for chiasmus** (inversions!), with a threshold **empirically calibrated** on 1000 shuffled pairs (seed 42, p95). Masked chunks are skipped in the matrix but kept for LASTZ.

**Genomics read-off (identical to a self-dotplot):** the main diagonal is trivial self-identity; **off-diagonal streaks = internal repeats/refrains**; **anti-diagonal streaks = chiasmus** (the linguistic inversion). Scripture is full of both — refrains ("and it came to pass") and chiastic structures — so the gospels are a rich substrate here.

Reach it via the **TextHiC tab** (Alt+3) or press `d`. Because it consumes `self_similarity`, you must **Configure** that track first (Analysis → self_similarity → Configure…) binding a chunk layer (+ optional repeat-mask + embedding). Empty state: "Self-similarity matrix not available. Run analysis first."

🟡 **BUILT/verify:** the matrix + alignments render live. The former empty-state dead-end was **fixed (audit #12f, `050cd68`)**: the "matrix not available" state now shows a **"Compute in the Analysis tab →" CTA**, and the palette/zoom/export toolbar stays hidden until a matrix loads. (You still navigate to Analysis to run `self_similarity`; the CTA now points the way instead of leaving you stranded.)

**▷ Probe & note:** With `word_overlap` on a gospel, do refrains show as off-diagonal streaks? Does the anti-diagonal (chiasmus) detection surface anything in, say, Matthew's genealogy or the Sermon? Is the identity % honest vs the visual streak length?

### 3.5 Characters tab  ✅

Entity index + interaction matrix. Sortable table (Name/Mentions/Type/Distribution) with mention sparklines; per-row **Find** filters the Reading view to that figure. A **co-occurrence** toggle swaps in an N×N shared-paragraph heatmap (`/characters/cooccurrence?top_n=`). `GET /api/projects/{id}/characters`.

**Genomics analogue:** a feature catalog + a co-occurrence/interaction matrix (think ChIP co-binding or gene-gene co-occurrence).

**▷ Probe & note:** On the gospels, do Jesus/disciples/Pharisees resolve as canonical entities with sensible aliases? Co-occurrence structure across Matthew vs Mark is a genuinely interesting comparative signal.

---

## Part 4 — Pairwise comparison (Compare tab) — R(A, B)

**Genomics analogue:** whole-genome alignment. This is a single WGA between two "assemblies" (two books). Everything here is `R(A,B)`.

### 4.1 Setup  ✅
Open one book, then in Compare pick a second via the **CompareProjectPicker** (a collection-scope dropdown narrows candidates to co-members — e.g. scope to your gospel collection, then pick DR-Matthew as the partner for KJV-Matthew). Choose a **method** — **Semantic (embeddings)** / **Alphabet** / **Word overlap** — and click **Align**.

- Semantic is **409-gated** on embedding congruence: both texts must share an embedding space (same model fingerprint), or it fails loud with a reconcile pointer. Word/alphabet are token-only, ungated.
- ✅ The method label reads **"Semantic (embeddings)"** — corrected from "Semantic (SBERT)" (audit #309, `5539427`): the backend uses Qwen3-Embedding-4B/cosine, not SBERT. When you load an existing alignment, the dropdown now **syncs to the method that actually produced the on-disk records** (#12i), so it can't claim "Semantic" while a word-overlap matrix is on screen.
- ✅ **Fixed (audit #12a, `3d779e4`):** Compare **auto-loads any alignment already on disk** when you pick a partner, so Alignment/Synteny/Circos/Diff reflect existing results instead of a false "Ready to align." (Previously it hid completed alignments behind an empty state and forced a redundant re-Align.)

### 4.2 The five sub-views

| Sub-view | Shows | Genomics analogue | Status |
|---|---|---|---|
| **Alignment** ✅ | Split query/target panes with SVG ribbons connecting aligned passages; click a ribbon → scroll both. | Aligned-block ribbon view. | SHIPPED |
| **Dotplot** ✅ | N×M cross-similarity **heatmap**; palette; **score-threshold slider**; **color legend + honest metric caption** (new, #12b-d); **PAF export** link; wheel-zoom. | The M×N chunk-distance heatmap. | SHIPPED (see §4.5) |
| **Synteny** ✅ | Two stacked linear tracks + trapezoid ribbons between aligned blocks; **gated on records** so it no longer draws bare output on zero alignments. | Synteny/collinearity plot. | SHIPPED |
| **Circos** ✅ | Circular arcs; comparative mode = concentric rings + ribbons; click → Alignment; **gated on records** (no more bare rings reading as a false null). | Circos chord diagram. | SHIPPED |
| **Diff** ✅ | Auto-run paragraph diff (**fixed LCS + character-diff, method-independent** — now stated in a banner); added/removed/changed with a summary bar. | Variant/edit call between two near-identical assemblies. | SHIPPED |

### 4.3 The heatmap-vs-dotplot distinction (important, and a genomicist will care)  ✅ design / 🟡 build

Palimpsest's design draws a sharp line between two products that the current UI partly conflates:
1. **Chunk-distance heatmap** — the dense M×N matrix, *every* chunk-pair, over a congruent metric. (The current `ComparativeDotplot` component **is in fact a heatmap renderer** despite the "Dotplot" tab name.)
2. **Thresholded local-alignment dotplot** — only the *high-scoring local alignments* from an end-to-end **Smith-Waterman/LASTZ seed-extend** pass, each scored `f(length × [matchiness − gappiness])`, with an empirically-chosen cutoff on the score distribution (FR-40).

They inter-map through character coordinates (alignment streaks overlay the heatmap and vice-versa), and as chunk length shrinks the heatmap converges on the dotplot. **Dotplot geometry reads exactly as in WGA:** diagonals = collinear correspondence; **anti-diagonals = inversions (chiasmus across texts)**; off-diagonal blocks = transpositions; parallel offset diagonals = duplications; gaps = indels.

### 4.4 Significance & export  ✅
- **Gumbel p-values** are computed for the word & semantic methods (calibrated by shuffling); the `/scores` endpoint returns the score/identity distribution + a **suggested threshold (p75)**, with an honest note that raw score is length-proportional while identity is scale-free.
- **PAF export** (`/export.paf`) writes minimap2's real 12-column pairwise format with tags `AS:i` (score), `pv:f` (p-value), `id:f` (identity), `mt:Z` (method); mapping quality = Phred-scaled p-value. This is the genuine interop point — you can pull cross-text alignments into genomics tooling.

### 4.5 Compare — audit #12 fixes (now shipped) + residual honest caveats  ✅
The audit #12 cluster that was in-flight when this guide was first drafted has **shipped** (commits `50c1420`, `050cd68`, `3d779e4`). What changed:
- ✅ **Dotplot now has a color legend + honest metric caption** (#12b-d, `50c1420`). The caption is inferred from the records' method and states the domain: `cosine · negatives clamped to 0` / `word-overlap (Jaccard) · 0–1` / `alphabet similarity · 0–1`, plus a hidden-cell disclosure. The cosine clamp `[−1,1]→[0,1]` (negatives floor to the 0-end color, losing the sign) is now **declared in the caption** rather than silent.
- ✅ **Method-honesty** (#12i): the dropdown syncs to the method that actually produced the loaded records, so it can no longer show "Semantic (embeddings)" over a word-overlap matrix.
- ✅ **Empty-state CTAs** (#12e): the "Ready to align" state now carries a **`Run {method} alignment` button** that also covers the ran-but-empty case ("this method produced no aligned regions — pick another"). **Synteny/Circos are gated on records** so they no longer render bare/confusing output at zero alignments.
- ✅ **Diff method banner** (#12h): a banner states the edition diff is a fixed LCS + character-diff, **independent of the toolbar method** — so across translations (or where verse numbering differs) "most paragraphs read as changed" is labeled as *expected*, not a bug.

**Residual honest caveats worth your eye** (behavior is now labeled, but the methodology is still worth judging):
- 🔧 The dotplot's cosine **sign-loss** is disclosed but not *fixed* — a diverging palette centered at 0 would preserve it. Note whether the clamp costs you anything on the semantic matrix.
- 🔧 §4.3's **heatmap-vs-dotplot** distinction still holds: the "Dotplot" tab is a *heatmap renderer*; a true thresholded local-alignment dotplot (score-cutoff on seed-extend) is the intended second product.

**▷ Probe & note (Part 4):**
- Align **KJV-Matthew vs DR-Matthew** with `word` and with `semantic`. Does the metric-gap signal (embedding-high ∧ lexical-low ⇒ paraphrase/translation; both-high ⇒ verbatim) hold? This is the synonymous-vs-identical-substitution analogue and is the crux of translation analysis.
- Align **Matthew vs Mark** (same Bible). Synoptic parallels should show as strong local diagonals amid large indels (Matthew's non-Markan material). Do the anti-diagonals ever fire (cross-gospel chiasmus)?
- Export a PAF and sanity-check the columns/tags against minimap2's spec.
- The dotplot now has a legend + metric caption (#12b-d) — does the caption correctly name the metric/domain, and is the cosine sign-clamp disclosure (`negatives clamped to 0`) something you'd want handled with a diverging palette instead?

---

## Part 5 — Collection / corpus analysis (Corpus tab) — {R(Ai, Aj)}

**Genomics analogue:** comparative/pangenome genomics. This is the N-way alignment set over all six books (or a per-gospel sub-collection). Reach it via the **Corpus tab** (Alt+7). Pick a collection (only ≥2-member collections appear). The header shows a **CongruenceBadge** and **core/shell/singleton** class counts.

> ✅ Fixed (audit #11): member labels across the whole Corpus workbench now show **project titles** ("KJV — Matthew") instead of opaque slugs ("…chapter-in-book-0047"). If you still see slugs anywhere, note it.

### 5.1 The corpus graph — build it first  ✅ (C3)
Selecting a collection triggers a **build** of the reference-free corpus graph: `POST /api/collections/{id}/corpus-graph`. Under the hood: nodes are merged paragraph anchors per member; edges are the C2 pairwise alignment records; a **union-find** groups anchors into **homology components**, each classified **core** (all members) / **shell** (some) / **singleton** (one) — the core/accessory/cloud pangenome exactly. Proven invariant: aligned components are never singletons; singletons arise only from unaligned gaps.

✅ **Fixed (audit #12j, `4faedef`):** the workbench is now **GET-first** — it reads a persisted graph for free and only **POST-builds when none exists yet (404)**; re-root and revisit never rebuild. The costed C5 cross-member scans (**corpus-repeats**, **root-track**) were also moved off the auto-select path — they now **load lazily when their Corpus/Masking sub-tab opens**, so landing on Overview no longer triggers a ~30 s scan. (The one-time first build is still un-gated by a cost dialog; that's the remaining sliver of the "never auto-run costed ops" contract — note whether the first-selection build surprises you.)

### 5.2 The seven sub-tabs

| Sub-tab | Shows | Endpoint | Genomics analogue |
|---|---|---|---|
| **Overview** ✅ | **BlockMap** (Mauve-style per-member homology lanes, colored by component; click member → its Browser); **AllPairsMatrix** (shared-component grid; click cell → loads that pair + runs alignment + jumps to Compare→Dotplot); **PhyleticTreeView** (dendrogram with a **Root** dropdown → re-roots). | `/corpus-graph`, `/phyletic-tree?root=` | Mauve alignment blocks + all-pairs synteny + a cladogram. |
| **Members** ✅ | Table of member / Work / lineage / **root↔member role toggle**; per-member lattice. | `/lattice`, `PUT …/roles/{pid}` | Sample sheet + designating a reference. |
| **Corpus** ✅ | **RepeatLanes** — phrases recurring **across** members (cross-member motifs). | `/corpus-repeats` | Multi-genome conserved motifs. |
| **Masking** ✅ | **ConservationLane** — cross-text conservation projected on the root lens. | `/root-track?root=` | A conservation track (phyloP-like) on a reference. |
| **Analyses** ✅ | Boilerplate + discriminative terms (corpus IDF), near-duplicate member clusters, **undirected** diffusion/spread. | `/corpus-analyses` | Core-genome vs accessory content; an explicitly *non-directional* spread readout. |
| **Sweep** ✅ | Recall-dial candidate generation (see §5.4). | `/sweep`, `/sweeps` | Seeding sensitivity / ANN recall dial before exact scoring. |
| **Probe** ✅ | `R(q, Corpus)` retrieval (see §5.5). | `/probe` | Query-vs-database similarity search. |

### 5.3 Phyletic / stemma tree  ✅ (C4, FR-38)
Distance = **Jaccard dissimilarity** over shared homology components; tree = **neighbor-joining** (Saitou-Nei 1987) — additive, no molecular-clock assumption, with an auto-suggested root you can override. This is a stemma-from-shared-innovations, computed exactly like a distance phylogeny.

> Recent fix (2026-07-01): the phyletic distance was made **alignment-identity-aware**, after which Geneva-Matthew correctly sisters KJV-Matthew with DR/Vulgate as the outgroup — the ground-truth-correct topology. Verify this on your 6-member set.

### 5.4 Recall-dial sweep  ✅ (C6c, FR-35)
The candidate-generation dial for the O(N×M) chunk-pair space. Controls: metric, **mode (exhaustive ↔ high-recall ↔ fast)**, dense-threshold, **force-exhaustive** escape hatch. Small matrices default to exhaustive; large ones *recommend* (never force) candidate generation — **ANN over embeddings** (HNSW efSearch / IVF nprobe / multi-probe LSH / over-fetch-then-rerank) or **MinHash-LSH over shingles** for lexical similarity. Every run reports pruned counts + an **empirical estimated recall** (fraction of a sampled exact-NN oracle recovered) or an honest `null` when unsampled — **never a fabricated 1.0**. Runs are persisted as resumable journals (view/delete in a run manager).

> Live-proven: a word-shingle LSH sweep on the ~3.06M-pair Matthew-Mark matrix pruned 99.98% at measured recall 0.102; cosine over-fetch reached recall 1.0. This is the honest-recall discipline you'd demand of any ANN pipeline — it tells you what it *missed*.

### 5.5 Probe — R(q, Corpus)  ✅ (C6b)
"Find passages like this across the collection." Two query sources: an **existing passage** (service-free — reuses a stored corpus vector) or a **text query** (embedded first, gated behind a **CostDialog**). Congruence-gated at both the member and query boundaries (409 on mismatch). Live-proven finding a cross-translation match the word method missed (DR "his star in the East" ↔ Geneva phrasing, cosine 0.94).

### 5.6 Congruence badge & reconcile  ✅ (FR-39)
Per-metric, shows which members share a congruence key (are comparable) vs which need reconciling; **Reconcile…** routes through the cost dialog to re-embed. This is your "are these assemblies in a comparable coordinate/representation system" gate, made visible.

### 5.7 Liftover  ✅ (C5, FR-42)
Cross-text mask/annotation projection A→B across the alignment (`POST /api/collections/{id}/liftover`). Block-granular; lifted intervals land as an **additive, non-destructive run version**; intervals hitting no aligned block are reported `dropped`. The `mask-effect` endpoint proves a cross-text mask actually *changes* a downstream alignment (the done-criterion). This is genomic liftOver, honest about what it can't place.

**▷ Probe & note (Part 5) — this is the richest stress-test surface:**
- Build the graph on all 6 books. What are the **core/shell/singleton** counts? (See §7.3 — the core=1 over-merge is the key open question and your expertise is directly relevant.)
- Does the **phyletic tree** recover the expected topology (Matthew editions cluster, Mark editions cluster, translation family structure)? Try re-rooting.
- **AllPairsMatrix:** do same-book-different-translation pairs (KJV-Mt / DR-Mt / Geneva-Mt) show more shared components than cross-book pairs (Mt / Mk)? If cross-book synoptic sharing rivals within-book, that's the over-merge signal.
- **Sweep:** run high-recall vs exhaustive on the Matthew-Mark pair; does estimated-recall read honestly? Force-exhaustive and compare.
- **Probe:** seed with a Beatitude or a parable opening; does it retrieve the synoptic parallels across translations?
- **Liftover:** mask a passage in KJV-Matthew, lift to DR-Matthew; do the `dropped` counts make sense given translation divergence?

---

## The Gold Set — reproducible, standard-verified Bible masks  ✅ (2026-07-03)

**Genomics analogue:** a curated **benchmark truth set with a reproducibility harness** — Genome-in-a-Bottle for masking: a panel every tool is measured against, plus the recipe to regenerate it byte-for-byte and the QC that proves it still holds.

The Gold Set is the set of Bibles whose masking is a **committed, CI-verified contract**, not a one-off hand edit. Its bar and internal model are specified in [`../gold-set-standard.md`](../gold-set-standard.md) — read that for the authoritative definitions of *complete / accurate / precise* and the two gold kinds. This section is the operational face.

### The bar (summary)
A Bible is Gold Set only when its masking is **complete** (a generic layer `{body,volume,book,part,section}` and a specific layer each tile the whole text with no gaps), **accurate** (correct mask-types present; applied elements correctly typed), and **precise** (each masked element's char-level start/end capture its marker with no overrun into adjacent prose) — plus **validation parity** with peers of its kind and **operational readiness** through CLI + API + UI.

### Two gold kinds (one standard)
- **Reconstruction map — universal.** Every gold Bible has a committed `core/tests/fixtures/gold/maps/work-<idx>.map.json` (schema `palimpsest.gold-map/v1`): a full char-span tiling + the `reference_sha256` of the exact text it was cut against. The map **is** the masking; `server._apply_gold_map` applies it verbatim after the sha check.
- **Detection annotation — conditional.** Only where structure must be inferred (implicit-structure epub/pdf) does a sparse anchor-based gold (`work-<idx>.json`) drive the machine-local detector-recall tools (`gold_ratify.py` / `a3_score.py`). Self-marking marker scripture is exempt by design — scoring a detector against chapter/verse markers the text states outright would be theater.

### Rigor parity — the accuracy lens per kind
Map-internal consistency proves the map *sound*, not *correct* (a scrape that dropped a chapter still tiles perfectly). Each kind closes that blind spot with an independent lens:
- **Marker scripture (201–219):** a **canon versification oracle** (`canon_chapters.json`, `test_gold_canon.py`, prod logic in `palimpsest/gold.py`) checks per-book chapter counts against an external table — accuracy *stronger* than eyeball, since the external counts (stable since Langton, c. 1227) never touched the map. It strict-gates the universal 66-book Protestant core; tradition-variant deuterocanon is *recorded, not gated*, so the oracle never self-blesses a versification difference as an error. This is the pangenome analogue of validating a called gene model against an external, independently-curated annotation rather than against itself.
- **Detector epub (5, 100):** annotation gold + detector recall.
- **Bespoke (108):** map gates only (canon oracle N/A — Catholic Vulgate canon).

### The registry — one record, three roles
`core/tests/fixtures/gold/sources.manifest.json` (`palimpsest.gold-sources/v1`) is at once an **audit trail** (`source_sha256` of the source binary + `reference_sha256` of the produced text — provable without ever distributing the binary), a **registry** (the enumeration behind CLI/API/UI), and a **scorecard** (`validated:{cli,api,ui}`). Generated (not hand-authored) by `mask_engine/gen_sources_manifest.py`; guarded hermetically by `test_gold_sources.py`.

**Copyright — preserve, don't push.** Full *use* rights (masks/annotations/derivatives are committed) but **no distribution** of source binaries — epub/pdf/txt stay in gitignored `imports/`; only fingerprints ship.

### The three operational paths  ✅
All three apply *any* registered Bible by id over the same `_apply_gold_map` core, so the resulting mask is identical.

| Path | How | Entry |
|---|---|---|
| **API** | `GET /api/gold` (registry + `map_present`/`source_present` local-availability flags); `POST /api/gold/{idx}/apply` (ingest the registered source + apply the map after the sha check; 404 if the source isn't present locally) | `server.py` |
| **CLI** | `palimpsest gold list` / `gold apply <idx> <workspace>` / `gold verify [idx]` (direct-import; `verify` is the CLI face of the hermetic gates + canon oracle) | `cli.py` `gold` group |
| **UI** | ProjectPicker sidebar → **Gold Set** row → **Gold Library** overlay: browse the registry, **Apply** a Bible. Apply is disabled with a reason when the map isn't committed or the source isn't present locally. | `browser/src/components/common/GoldLibrary.tsx` |

### The set as it stands
**19 Bibles registered; 17 appliable on a machine holding the corpus.** (idx 6 Geneva-1599 and 108 DR-original keep their source outside `imports/`, so their UI Apply is disabled — preserve-don't-push, flagged honestly by `source_present:false`.) Marker Bibles: 201 Coverdale, 202 Bishops, 203 Wycliffe, 208 Great, 209 Matthew's, 210 Webster's, 211 Wessex (4 gospels), 212 Young's, 213 Julia Smith, 214 KJV-2016-NT, 215 EMTV-NT, 216 KJV-1769, 217 Tyndale, 218 Geneva-1560, 219 KJV-1611 (80 books). Epub (detector) golds: 5 DR-Haydock, 100 DR-Challoner. Bespoke: 108 DR-original.

### Verification lenses (what proves each criterion)
| Lens | Runs where | Proves |
|---|---|---|
| `test_gold_maps.py` | CI (hermetic) | map structurally sound (spans in-range, two-layer coverage, taxonomy, marker parity, production round-trip) |
| `test_gold_canon.py` | CI (hermetic) | marker-Bible chapter counts match the external canon |
| `test_gold_sources.py` | CI (hermetic) | registry complete, reconciles with maps, fresh |
| `gold_ratify.py` / `a3_score.py` | machine-local | detector accuracy for epub golds (needs copyrighted text) |
| `reference_sha256` re-check | apply-time (machine-local) | the map's offsets align to freshly-ingested text |

The sha tie and the detector lenses are machine-local **by design** — they need the copyrighted source text — so that boundary is a property, not a gap.

**▷ Probe & note (Gold Set):**
- Open the **Gold Library** (sidebar → **Gold Set**). Do the 19 Bibles list with correct availability flags (2 disabled for absent source)? Apply idx **211** (Wessex) — does it land as a project with masked chapter headings + verse-number tokens?
- On an applied marker Bible, zoom to readable text: does `## <Book> <n>` grey out while the following verse prose stays visible? Are the verse-number tokens (`2 `, `3 `) greyed but the verse *text* not?
- On **203** (Wycliffe) / **219** (KJV-1611): the large front-matter prologue/preface blocks are masked as whole units — is each greyed block bounded exactly at the first book heading, with no verse prose eaten?
- On the epub golds **5** (Haydock) / **100** (Challoner): `heading`/`chapter_heading` spans legitimately carry book/chapter *arguments/summaries* (bigger greyed blocks) — precise for those editions, not an overrun. Note if the UI render disagrees.
- Run `palimpsest gold verify` — do all 19 pass? Does `gold verify <idx>` on a marker Bible exercise the canon oracle?

---

## Part 6 — Cross-cutting guarantees (worth verifying hold everywhere)

| Guarantee | What it means | Where to test |
|---|---|---|
| **Fail-loud** (NFR-3) | Invalid params → 400; incongruent metric → 409; unplaceable coordinate → `UnmappedCoordinateError`. No silent fallback. | Try a semantic align on un-embedded texts (expect 409); a bad chunk config (expect 400). |
| **Cost transparency** (NFR-4) | Embedding/probe/reconcile never auto-run; a CostDialog/pre-run estimate gates them. | Every embedding-dependent action. (Narrowed exception 🔧: the **first** corpus-graph build still auto-fires without a cost dialog; reads/re-roots are now free and the costed C5 scans load lazily — §5.1.) |
| **Non-destructive versioning** (FR-41) | Re-runs are kept as tagged versions; only **structural/content masks** are ground-truth and supersede. | Re-run a track; check versions accumulate. |
| **Provenance** (NFR-2) | Every layer stamped with a `.run.json`; no hidden output-affecting value. | Layer manager provenance. |
| **Honest viz** (NFR-7) | Descriptive-not-inferential framing; no faked progress; caveats travel to the point of display (e.g. "approximate boundaries", "recall n/a"). | Sweep recall, LASTZ boundary labels, diffusion's non-directional note. |
| **Coordinate honesty** (NFR-C6) | Every cross-text offset remapped operand→root by assert-or-fail. | Integrity report on derived subtexts. |

---

## Part 7 — The honest boundary: gaps, stubs, deferred, and the one open methodology question

### 7.1 Stubs / dead-ends (note if they trip you)  🔧
- **ProjectPicker sidebar rows** Started / Finished / Novels / Translations / Papers / Scholars — **non-functional** (no onClick). Only "All", your Collections filter, and the **Gold Set** row (✅ opens the Gold Library overlay — see "The Gold Set") are wired.
- ✅ **Home now launches Corpus** — the "Analysis tools" grid gained the Corpus tile (audit #12g, `050cd68`); all 7 tabs launch from Home. (Was: Corpus reachable only via the tab bar.)
- **Sentiment = VADER only** (Hedonometer withheld).
- **self_similarity = Configure-only** (no bare Compute).
- **Empty-state guidance (partially fixed):** ✅ TextHiC now has a "Compute in the Analysis tab →" CTA (#12f). Still guide-text-only (no one-click compute button): **Profile** ("Run the profile track") and **Representations** ("No embedding layers yet. Run an embedding track…") — informative, but they don't run the track for you.
- **UMAP** → 400 (PCA only), by design.
- **Text-level profile** has no HTTP endpoint (track + file only).
- 🔧 **`edge_min_score` homology gate is API/CLI-only** — the #13 score gate (§7.3) is *not* surfaced as a browser control, so from the UI the corpus graph always builds at the default (`edge_min_score=0.0`, no score gate). Exposing it is an open enhancement.

### 7.2 Audit remediation status (all shipped as of `46b5283`)  ✅
The audit #11–#14 clusters that were in-flight when this guide was first drafted are **complete and pushed**:
- **#11 friendly member labels** — ✅ Corpus workbench shows titles, not slugs.
- **#12a Compare auto-load** — ✅ no false "Ready to align" when an alignment exists (`3d779e4`).
- **#12b–d dotplot legend + honest metric caption** — ✅ (`50c1420`).
- **#12e–i empty-state CTAs, Synteny/Circos record-gating, Diff method banner, method-honesty, Corpus-on-Home** — ✅ (`050cd68`).
- **#12j GET-first corpus-graph + lazy costed layers**, **#13 score homology gate** — ✅ (`4faedef`).
- **#14 batch A** honest spaCy fallback + scoped comparisons + self-describing `matrix.bin` — ✅ (`432bea3`); **batch B** "Semantic (embeddings)" label + shared E1–E5 evidence table + PCA scatter axes/legend — ✅ (`5539427`); **batch C** doc reconciliation — ✅ (`436d919`).
- **Follow-up** honest spaCy fallback extended to `segmenter`/`entities`/`syntax`/`coreference` — ✅ (`46b5283`).

So unless noted otherwise, what you see in the UI is the *post-remediation* state — the 🟡/🔧 tags remaining below are genuine open items, not in-flight churn.

### 7.3 The open methodology question — core/shell over-merge (your expertise wanted)  🔧⏳
On a synoptic corpus, **no `edge_min_identity` threshold separates Matthew from Mark into two cores** — the corpus graph collapses to `core=1`. The reason is genuinely interesting and squarely in your domain: **cross-book synoptic parallels share wording at identities that overlap same-book (translation) identities.** Word-overlap alignment cannot tell "same story retold" (Mt∥Mk) from "same text retranslated" (KJV-Mt / DR-Mt) on identity alone. Score (length/coverage-proportional) separates them cleanly, but the homology-edge gate deliberately uses identity, not score.

A KJV **Luke** subtext was added as a true outgroup to stress this; it landed mid-ladder rather than cleanly rooting, and the engine self-reported the cause ("only 1 shared multi-member component across 7 members — coarse/unstable"). The hypothesis is that **embedding (semantic) distance, not word-overlap, is needed for a stable synoptic tree.**

**Partial progress since (audit #13, `4faedef`):** a **score-based homology gate `edge_min_score`** was added to `build_corpus_graph`. Score is length/coverage-proportional — a long collinear translation correspondence accumulates score, while a short synoptic-parallel fragment scores far lower *even at the same per-block identity* — so a score gate separates shared-source from shared-content where identity provably cannot (a regression test asserts no `edge_min_identity` reproduces the `core=1` outcome that `edge_min_score` fixes). **But**: (i) it defaults to `0.0` (off, prior behavior), (ii) it is **API/CLI-only — not a browser control** (§7.1), and (iii) raw score isn't comparable across pairs of very different sizes, so the truly correct object is a **coverage-normalized, scale-free gate** — which is not yet built.

This is the pangenome analogue of the **high-identity paralog vs ortholog boundary** — separating recent duplicates that share sequence from truly orthologous regions. The open decision is now sharper: (a) make a **coverage-normalized score** the *default* homology gate (generalizing the raw `edge_min_score`), (b) require **semantic-space alignment** for corpus-graph edges, and/or (c) accept `core=1` as *legitimate* (synoptic gospels genuinely share a core) — plus the UX question of whether/how to expose the gate in the browser. **Please note your reasoning here in detail** — it's the highest-leverage methodology decision on the roadmap, and your ortholog/paralog and coverage-normalization intuitions map onto it directly.

### 7.4 Deferred by roadmap (absence is by design)  ⏳
- A **persistent job DB / scheduler** (only a lightweight resumable run-journal sidecar exists today; full queue is a later phase).
- **UMAP** projection.
- De-novo **N-way simultaneous MSA** — the graph is deliberately *assembled from pairwise edges*, never a single simultaneous aligner.
- Auto-detection that two Imported Texts are the same **Work** (Work identity is user-asserted, by design).

---

## Part 8 — Note-taking template (so your notes digest cleanly into dev items)

For each observation, capture:

```
[N] Where:      <tab / sub-view / exact control>   (e.g. Corpus → Overview → AllPairsMatrix)
    Action:     <what you clicked / the sequence>
    Expected:   <what the roadmap/genomics analogue implies should happen>
    Observed:   <what actually happened; screenshot id if any>
    Gap type:   BUG | UX | METHODOLOGY | ENHANCEMENT | DOC
    Severity:   BLOCKER | HIGH | MEDIUM | LOW
    Genomics note: <the analogue / where it diverges — optional but valuable>
```

Grouping by **Gap type** lets me route directly: BUG → fix + regression test; METHODOLOGY → design decision (like §7.3); UX → the audit-remediation stream; ENHANCEMENT → roadmap. When you hand me the compiled notes I'll cross-reference each against the code, the vision/plan docs, and the current audit backlog, and derive concrete, best-in-class solutions.

---

## Appendix A — Suggested exploration order (fastest path to full coverage)

1. **Import** KJV → DR → Geneva (watch profile auto-detection; verify Matthew/Mark are clean `book` sections).
2. **Extract** Matthew and Mark from each → 6 subtexts + auto-collection. Verify lattice.
3. **Single-text** on KJV-Matthew: Reading → Browser → Analysis (chunk `word/100` → embedding → Profile → Explore stats → Integrity) → TextHiC (configure self_similarity, `word_overlap`) → Characters.
4. **Pairwise**: KJV-Mt vs DR-Mt (translation: expect high semantic, lower lexical); then KJV-Mt vs KJV-Mk (synoptic: local diagonals + big indels). Export a PAF.
5. **Collection**: build the corpus graph on all 6 → Overview (block map / all-pairs / phyletic tree) → Members (roles) → Corpus repeats → Masking conservation → Analyses → Sweep (recall dial) → Probe. Focus notes on §7.3.

## Appendix B — Feature → endpoint → status quick map

| Feature | Endpoint(s) | Status |
|---|---|---|
| Import (local/upload/stream) | `POST /api/import[/local[/stream]]` | ✅ |
| Section detect/edit/apply | `…/sections/detect`, `PUT …/sections`, `…/sections/apply` | ✅ |
| Subtext derive | `POST …/derive/stream` | ✅ |
| Track compute / status | `POST …/analyze/{track}`, `…/analysis/status` | ✅ |
| Chunk-layer stats | `…/chunking/{label}/stats` | ✅ |
| Embedding analytics | `…/embedding/{label}/{projection,distances,heatmap,clusters,lane,estimate}` | ✅ (UMAP ⏳) |
| Profile (text-level) | *(track + `signals/profile.json`, no endpoint)* | ✅ / 🔧 no endpoint |
| Integrity | `…/integrity` | ✅ |
| KWIC / collocations / dispersion / duplicates | `…/{kwic,collocations,dispersion,duplicates}` | ✅ |
| Self-similarity (TextHiC) | `…/self_similarity/…` | 🟡 |
| Characters + co-occurrence | `…/characters[/cooccurrence]` | ✅ |
| Pairwise align + records + scores | `POST /api/alignment/run`, `…/{records,scores}` | ✅ |
| Cross-similarity matrix | `…/matrix[.bin]` | ✅ (legend + metric caption shipped; `matrix.bin` self-describing via `X-Matrix-*`) |
| PAF export | `…/export.paf` | ✅ |
| Edition diff | `POST /api/alignment/diff` | ✅ (fixed LCS+char-diff + honest method banner) |
| Collections CRUD + lattice + roles | `/api/collections…`, `…/lattice`, `…/roles/{pid}` | ✅ |
| Congruence | `…/congruence` | ✅ |
| Corpus graph + projection | `POST/GET …/corpus-graph[/projection]` | ✅ (GET-first #12j; `edge_min_score` gate API-only 🔧) |
| Phyletic tree | `…/phyletic-tree?root=` | ✅ |
| Corpus analyses | `…/corpus-analyses` | ✅ |
| Corpus repeats / low-correspondence / cross-text-mask / root-track / mask-effect | `…/{corpus-repeats,low-correspondence,cross-text-mask,root-track,mask-effect}` | ✅ |
| Liftover | `POST …/liftover` | ✅ |
| Sweep (recall dial) + run manager | `POST …/sweep`, `…/sweeps`, `DELETE …/sweep/{id}` | ✅ |
| Probe | `POST …/probe` | ✅ |
| Search / explain / summarize (LLM) | `/api/search`, `POST /api/{explain,summarize}` | ✅ (needs Ollama/embeddings) |

---

*Generated 2026-07-01 from a full backend (79-route)/frontend/vision/pipeline survey at commit `3d779e4`; **status tags refreshed 2026-07-01 to `46b5283`** after the audit #12–#14 remediation shipped (see §7.2 for the commit-by-commit map); **"The Gold Set" section added 2026-07-03** for the Gold-Set-Standard work (maps + canon oracle + sources manifest + CLI/API/UI, commits `1959f8c..4c80ff3`). Where this guide and older docs disagree on build status, trust `docs/development/collections-tier-build-journal.md` + this file.*

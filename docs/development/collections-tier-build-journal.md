# Collections Tier — Build Journal

Running log of the autonomous Collections-tier build + full-app regression validation
(authorized 2026-06-30). Companion specs: `design/collections-tier-vision.md`,
`design/collections-tier-plan.md`. Commit discipline: commit at green milestones **locally**;
**push held** pending explicit authorization.

## Baseline (2026-06-30, pre-build)

- Backend: **824 tests green** (0 fail/err/skip).
- Frontend: **60 tests green** (9 files).
- This is the regression floor; every phase must hold it.

---

## C1 — Object-model & operand foundation ✅ (FR-23–28, 37, 41, 43)

**Status:** complete; backend **839/839 green** (+15 new). Frontend untouched (60/60).

**Discovery that shaped the build:** `collections.py` was a flat, schema-less dict store with
**zero test coverage** and **zero CLI commands**; a `palimpsest.alignment` package (cross-similarity
matrices, Smith-Waterman, Gumbel significance, alignment records) already exists wired to
`POST /api/alignment/run` — a large C2 head start. So C1 added the *typed substrate* on uncovered
ground (low regression risk), not a rewrite.

**Shipped:**
- `core/palimpsest/collections_ops.py` (new) — the cross-text substrate:
  - Object model: `work_id` tag + `parent_project_id` subtext edge read as **loose metadata fields**
    (ProjectMetadata serialization untouched — protects the 824-test contract).
  - Membership lattice / inverse navigation: `edition_siblings` (shared Work), `subtext_children`
    (derived-from edge), `project_lattice`.
  - **Metric-congruence contract** (FR-27): `congruence_key` / `operands_congruent` /
    `congruence_report` — reuses the embedding layer's `model_fingerprint` and the
    `SimilarityMethod` registry's `requires_embedding`.
  - Cross-project operand resolution: `resolve_operand` / `resolve_comparison` (reuses the Wave-0
    explicit-bundle binder; gates embedding metrics on congruence, fail-loud).
  - Non-destructive run versioning + identity staleness: `operand_identity`, `comparison_identity`,
    `append/load/latest/delete_run_version`, `is_stale`.
- `core/palimpsest/collections.py` — collection-local roles (`member_role`, `set_member_role`, FR-25).
- `core/palimpsest/server.py` — endpoints: `GET /api/projects/{id}/lattice`,
  `PUT /api/collections/{id}/roles/{pid}`, `GET /api/collections/{id}/congruence`.
- `core/palimpsest/cli.py` — `collections` subgroup (list/show/create/add-member/remove-member/role/
  lattice/congruence) — first-ever collection CLI parity.
- `core/tests/test_collections.py` (new) — 15 tests: CRUD (previously untested), roles, lattice,
  congruence (token vs embedding, missing-layer, report), operand resolution (success + fail-loud),
  cross-text comparison + congruence gate, identity + non-destructive versioning, HTTP + CLI parity.

**Autonomous decisions (objective, flagged here):**
1. **Congruence key excludes the per-text analyzable digest.** The vision lists the digest in the key,
   but two distinct texts always have distinct digests, so including it makes cross-text comparison
   impossible by construction. The digest stays an *intra-project* coherence check
   (`bundles.coherence_reason`, FR-7); congruence is the orthogonal *cross-project* check
   (embedding-space identity via `model_fingerprint`). Documented in the module docstring.
2. **Loose metadata fields for `work_id`/`parent_project_id`** (mirroring how `parent_project_id` is
   already persisted) rather than extending the `ProjectMetadata` dataclass — avoids touching the
   serialization contract the baseline suite locks.
3. **`project_lattice` is fail-loud on an unknown project id** (404 at the API), while the low-level
   loose readers stay lenient (they iterate known projects).

**Done-criteria (plan §C1):** assemble collection ✓ · cross-project operand bind, fail-loud ✓ ·
per-metric incongruence detection ✓ · re-run keeps prior versions ✓ · CLI+HTTP parity ✓ · backend
green ✓ · no single-text regression (NFR-C1) ✓.

---

## C2 — Pairwise engine: heatmap + dotplot (FR-21, FR-33, FR-40, FR-36) — COMPLETE

**Discovery:** ~80% pre-existing. The `palimpsest.alignment` package (rectangular M×N cross-similarity
matrix, Smith-Waterman local alignment, Gumbel significance, JSONL records) and a full frontend Compare
tab (Alignment / Dotplot / Synteny / Circos / Diff sub-views, `ComparativeDotplot` heatmap with record
overlay, `comparisonStore`) already exist and are wired to live cross-text data. C2 = build the
**documented gaps only**, not a rewrite.

**Backend — committed `4435cda` (gap completions) + bug-fix commit (below):**
- `alignment/records.py` — `records_to_paf` / `write_paf` (minimap2 PAF, FR-36): 12 columns + tags
  `AS:i` (score), `pv:f` (p-value), `id:f` (identity), `mt:Z` (method); match count ≈ identity×block,
  mapping quality = Phred-scaled p-value.
- `server.py` — `GET …/records?min_score=&max_p_value=` (the dotplot's empirical cutoff, FR-40);
  `GET …/scores` (score distribution + suggested p75 threshold); `GET …/export.paf` (thresholdable PAF
  download); `GET /api/comparisons` (discovery — none existed).
- `cli.py` — `align-paf` command (CLI/HTTP parity).
- `tests/test_alignment_c2.py` — 9 tests (PAF format/roundtrip, record thresholding, score
  distribution, PAF export, comparison discovery, CLI, + 3 regression tests for the bugs below).

**Two real bugs surfaced by live HTTP validation (unit tests with on-disk fixtures missed both):**
1. **Every alignment POST 422'd.** `AlignmentRequest` was a Pydantic model defined *inside*
   `create_app`. Under `from __future__ import annotations` the endpoint's type hints are stringized,
   and FastAPI's `get_type_hints` resolves them against *module* globals only — a function-local class
   is invisible, so `request` silently degraded to a required query param and rejected every body.
   Fix: move `AlignmentRequest` to module scope (where all sibling request models already live).
2. **Long-id pairs hit `[Errno 63] File name too long`.** The comparison dir was named
   `{query}_vs_{target}`; two full edition slugs (≈150 chars each) blow past the 255-byte component
   limit — i.e. the headline use case (comparing Bible editions) was unrunnable. Fix: a shared
   `comparison_dir()` / `comparison_dirname()` helper keeps the readable name when it fits and falls
   back to a deterministic `cmp-<sha1[:16]>` hash otherwise; wired into all 8 construction sites.

**Frontend — verified + committed:** `ComparativeDotplot.tsx` gained a palette switcher
(blues/viridis — viridis was defined but unwired), a **score-threshold slider** (FR-40: hides
low-scoring alignments so only high-scoring local structure renders; range from the records' own score
min/max; shows shown/total count), and a **PAF download** link (`export.paf?min_score=…`). Covered by
`ComparativeDotplot.test.tsx` (3 vitest cases) — frontend 63/63 green, `tsc -b && vite build` clean.

**In-browser proof (C2 done-criterion):** `e2e/compare_dotplot_c2.spec.ts` drives the live stack on an
isolated server (`:8090`, leaving the shared `:8080` untouched). Loads a DR appendix sub-text, picks
its superset sibling, runs a word-overlap alignment (100 records, scores 21.5–34.0), opens the Dotplot,
and exercises all three controls: heatmap canvas renders, palette switches blues→viridis, raising the
threshold drops shown/total (100→27 at p75), and the PAF link carries `export.paf?min_score=`. Green.
Backend full suite 848/848. *Stretch (not done):* bidirectional B×A overlay toggle.

---

## C3 — Reference-free corpus graph (FR-31, pangenome) — COMPLETE

**Status:** complete; backend **857/857 green** (+9 new). Backend-only (no in-browser bar until C4
adds the viz). Done-criteria all met by unit + in-process HTTP/CLI tests.

**Shipped:**
- `core/palimpsest/corpus_graph.py` (new) — the reference-free corpus model. Nodes are *merged
  paragraph anchors per member*, edges are the C2 pairwise alignment records, a union-find groups
  anchors into homology **components**, and each component is classified **core** (all members) /
  **shell** (some) / **singleton** (one) by its distinct-member reach. `build_corpus_graph` reads each
  pair's stored comparison (`alignment.jsonl` + `metadata.json`, written by `POST /api/alignment/run`),
  merges per-member intervals into anchors, unions anchors linked by an edge, and adds each member's
  *unaligned gaps* as isolated singleton nodes. `project_to_root` derives the synteny lens on demand
  (each component's coordinate in a chosen root member's paragraph frame). Persistence under
  `workspace/collections/{id}/corpus_graph.json` (OQ-6 / FR-32), provenance-stamped by member
  `reference.sha256` and the contributing comparison dirs (NFR-C2).
- `core/palimpsest/server.py` — `POST /api/collections/{id}/corpus-graph` (build + persist → summary),
  `GET …/corpus-graph` (read full graph; 404 until built), `GET …/corpus-graph/projection?root=` (the
  root lens).
- `core/palimpsest/cli.py` — `collections corpus-graph-build / corpus-graph-show / corpus-graph-project`
  (CLI/HTTP parity, FR-37).
- `core/tests/test_corpus_graph.py` (new) — 9 tests: a 3-member fixture with real `reference.txt`
  paragraphs + hand-written comparison dirs proving 1 core / 1 shell / 3 singleton classification;
  the never-singleton-when-aligned invariant; root-projection coordinates verified against
  `Project.paragraphs()`; missing-pair reporting (graph still builds from existing edges);
  persistence roundtrip; build/projection guards; HTTP + CLI parity.

**Two formalized insights (the design's load-bearing properties, now proven):**
1. **Aligned components are never singletons.** Every alignment record links a *query* member to a
   *different* target member, so every edge crosses members; every edge-touched component therefore
   reaches ≥2 members and is core or shell. Singletons can arise *only* from unaligned gaps — passage
   regions no cross-member alignment covers. This makes the core/shell/singleton partition provably
   exhaustive over each member's paragraph space, and is asserted directly
   (`test_aligned_components_are_never_singletons`).
2. **Paragraph coordinates suffice for the root projection.** Records are paragraph-indexed, so
   projecting onto a chosen root is just reading each component's anchor in the root's paragraph frame
   — no character-space `OffsetMap` is needed at this tier (sub-paragraph precision is a C4/C5
   refinement). Character spans are still attached to nodes from `Project.paragraphs()` for C4
   rendering, but the graph *reasons* in paragraph space.

**Autonomous decisions (objective, flagged here):**
1. **Adjacent-anchor coarsening is intended, not a bug.** `_merge_intervals` fuses touching paragraph
   ranges, so a member's adjacent aligned passages collapse into one anchor node. This matches the
   design ("nodes = merged paragraph anchors per member"); finer splitting is a C4/C5 concern. The
   fixture deliberately separates a member's core and shell passages with an unaligned gap paragraph so
   they stay distinct nodes — which also surfaced a real edge case (see below).
2. **Gap detection depends on the member's paragraph total.** A member's *trailing* unaligned region is
   only detectable when the total paragraph count is known (from `Project.paragraphs()`); interior gaps
   (bounded by aligned ranges on both sides) are found regardless. The fixture's root member ends in a
   gap, so this path is exercised — an early fixture bug (incomplete `metadata.json` → `Project.load`
   silently failing → trailing gap lost) confirmed the dependency and is now covered.
3. **HTTP/CLI parity shipped with C3** (rather than deferred to C4) so the C4 viz is a pure frontend
   build against a stable contract — the Wave-0 "UI lands per-phase with its backend" pattern.

**Done-criteria (plan §C3):** graph over a ≥3-text collection ✓ · core/shell/singleton correct on a
fixture ✓ · project to a chosen root + verify coordinates ✓ · tests green (857/857) ✓.

---

## C4 — Collection overview visualization (FR-33, FR-38) — COMPLETE

### C4a — Phyletic/stemma tree backend ✅ (FR-38)

**Status:** backend complete; **865/865 green** (+8). The remaining C4 work is the frontend overview
(Circos / block-map / bubble / tree render) + in-browser proof — most of which is a pure data
transform over the already-shipped corpus-graph endpoint, the tree being the one piece JS shouldn't
own.

**Why a backend phyletic tree (and only that):** the Circos chord overview and the Mauve block-map are
*reading the same data the corpus-graph endpoint already returns* — members + components-with-
classification give all-pairs ribbon counts (shared components per pair) and per-member colored lanes
directly, in the frontend. The genuinely algorithmic piece is the phyletic/stemma tree (FR-38), which
needs an inter-text distance matrix and a real tree-building algorithm — so that is the C4 backend,
and nothing more is invented.

**Shipped:**
- `core/palimpsest/analysis/phylo.py` (new) — a pure numeric leaf (no I/O, no graph import, like
  `textstats` / `chunk_stats`): `component_distance_matrix` (pangenome **Jaccard dissimilarity** —
  members co-occurring in many homology components are close), `participation_counts` (root-
  completeness signal), `neighbor_joining` (Saitou-Nei 1987, deterministic lowest-index tie-break,
  negative branch lengths clamped), `root_tree` (BFS-orient the unrooted edge list from a chosen leaf).
- `core/palimpsest/corpus_graph.py` — `phyletic_tree(graph, root=None)` assembler: maps member ids to
  indices, builds comp-sets from the graph's components, calls the leaf, suggests the most component-
  complete member as the backbone root (user-overridable), and serializes a labelled rooted tree +
  the distance matrix + participation.
- `core/palimpsest/server.py` — `GET /api/collections/{id}/phyletic-tree?root=`.
- `core/palimpsest/cli.py` — `collections phyletic-tree` (CLI/HTTP parity, FR-37).
- `core/tests/test_phylo.py` (new, 6) + `test_corpus_graph.py` (+2 graph-phyletic, + endpoint/CLI
  coverage): Jaccard maths, deterministic NJ grouping (close pairs paired), base cases, tree
  orientation; graph-derived distances + suggested/overridden root + guard.

**Autonomous decisions (objective, flagged here):**
1. **Distance = pangenome Jaccard over shared components**, derived from the C3 graph rather than a
   second distance notion (e.g. raw alignment score), so the tree is a *reading of the graph's own
   structure* (plan §C4 "a reading of the reference-free graph's distance structure"). Avoids
   introducing an independent metric the user would have to reconcile.
2. **Auto-root = max component participation** (the most complete backbone), ties to lowest index —
   the "map everything onto the most-shared text" default the synteny lens wants. Manual override is a
   first-class `?root=` parameter (FR-38 manual-first).
3. **Neighbor-joining over UPGMA** — NJ is additive and doesn't assume a molecular clock, the genomics
   standard the plan names; ~40 deterministic lines, fully unit-tested (a known 4-taxon matrix groups
   the two close pairs).

### C4b — Collection overview frontend ✅ (FR-33) + in-browser proof

**Status:** frontend complete; committed `ea03c74`. **Frontend vitest 68/68 green**, `tsc -b && vite
build` clean. **In-browser Playwright 3/3 green** against a real three-text collection (run `b5lqhxh34`,
16.4s) — the Wave-0 done-criterion for a UI phase.

**Shipped (new Corpus tab):**
- `browser/src/components/CorpusView/corpusOverview.ts` (new) — pure data transforms over the
  `/corpus-graph` payload: per-member block-map lanes (component-classified colored segments), the
  all-pairs shared-component matrix (symmetric pair → shared-component count), and pangenome summary
  counts. No fetching, no React — unit-testable in isolation, mirroring the backend's leaf pattern.
- `browser/src/components/CorpusView/corpusOverview.test.ts` (new, 5) — matrix symmetry, lane
  derivation, core/shell/singleton tallies, empty-graph guard.
- `browser/src/components/CorpusView/CorpusView.tsx` (new) — the tab surface: collection picker →
  assemble/read graph → three linked overview surfaces (Mauve **block-map**, all-pairs **matrix**,
  phyletic **dendrogram** consuming `/phyletic-tree?root=` with a live root-override `<select>`), plus
  the two click-through zoom tiers.
- Wiring: `viewStore` (`TabId` gains `corpus`, `Alt+7` keyboard shortcut), `TabBar`, `AppLayout`.

**Three zoom tiers (FR-33 click-through), all proven in-browser:**
1. **Overview** — block-map + all-pairs matrix + phyletic tree render on first paint.
2. **Pair** — a matrix cell (an enabled, shared-component pair) → that pair's dotplot on the Compare
   tab.
3. **Single text** — a block-map member label → that text's Browser tab.

**In-browser proof rig (isolated, shared `:8080` untouched — the C2/C3 pattern):**
`core/.venv/bin/palimpsest serve .scratch/demo --port 8092` serves the built `dist` + API single-origin.
Fixture collection **`c4-overview-proof`** (via gitignored `scripts/c4_setup.py`): three nested
Douay-Rheims appendix sub-texts, mutually word-overlap aligned (100 records each); assembled corpus
graph = **core 1 / shell 0 / singleton 1, 300 edges**; phyletic suggested root = M1, distances
M2↔M3 = 0. `browser/e2e/corpus_overview_c4.spec.ts` (3 tests) drives it green.
Rerun: `cd browser && PALIMPSEST_BASE_URL=http://localhost:8092 PALIMPSEST_API_URL=http://localhost:8092 npx playwright test corpus_overview_c4 --reporter=list`.

**Test-side bug found + fixed during the proof (app was correct):** the first run had one failing test
because navigating Corpus → Browser → Corpus **re-mounts** `CorpusView` (it is conditionally rendered),
which resets the collection selection to the default `usable[0]`; the follow-up pair-click then landed
on a different, sparsely-aligned collection whose cell was *correctly* disabled (0 shared components).
Fix was test-side: split the single multi-click test into two independent tests (each does a fresh
`goto` + collection select) and target only enabled cells via `button[...]:not([disabled])`.

**Known minor UX (non-blocking, flagged):** that same re-mount means switching tabs away and back loses
the selected collection (resets to `usable[0]`). Acceptable for now; the fix is to lift `collectionId`
into a store — deferred as polish, not a done-criteria blocker.

**Done-criteria (plan §C4):** collection-overview surface (block-map + all-pairs matrix + phyletic
tree) ✓ · phyletic tree with root override re-projecting ✓ · three click-through zoom tiers ✓ ·
frontend + Playwright green **in-browser** on a real ≥3-text collection ✓.

## C5 — Cross-text masking, tracks & liftover (FR-29, FR-30, FR-42) — COMPLETE

**Status:** backend committed local (`c9be1cc` C5a, `0286737` C5b, `72134fb` C5c, `f8d28d0` C5d);
C5e frontend + in-browser proof this session. **Backend suite 891 green**, **frontend vitest 72 green**,
`tsc -b && vite build` clean. **In-browser Playwright 3/3 green** on an isolated three-text collection
(shared `:8080` untouched). Push HELD per standing discipline.

### C5a — Liftover leaf ✅ (`c9be1cc`, FR-42)
`core/palimpsest/alignment/liftover.py` (new) — `AlignmentMap`: paragraph-block character
correspondence between two members, built from their `AlignmentRecord`s. `project_span` / `lift_intervals`
project a source interval onto the target frame; intervals touching no aligned block are **dropped** and
reported. 10 tests.

> **FLAG (i) — purpose-built, NOT an `OffsetMap`.** The design doc said liftover "is itself an
> OffsetMap". It isn't: `OffsetMap` (derive.py) models *single-text excision* (analyzable↔original within
> one text); liftover models *cross-text correspondence* (member A char-frame ↔ member B char-frame). They
> are different coordinate problems, so C5a is a distinct type. Rationale in the file docstring.

> **FLAG (ii) — block-granular, honest.** Liftover maps at aligned-paragraph-**block** granularity — no
> within-block interpolation. A 50-char source interval inside a 136-char aligned block lifts to the
> whole 142-char target block, not a proportional 50-char sub-span. This refuses to smuggle a precision
> the paragraph-level alignment never established. Verified live: `alpha[0,50] → beta[0,142]`.

### C5b — Cross-text masking assembler ✅ (`0286737`, FR-29/30/42)
`core/palimpsest/collections_masking.py` (new):
- `corpus_repeats` — cross-member phrase tally (a phrase recurring once-per-member across ≥`min_members`
  is caught here though no single text repeats it). Reuses Wave-0 `tracks.repeats` `_normalise` /
  `_WORD_RE` / `STOPWORDS` / `_merge_spans` verbatim (no drift).
- `low_correspondence_intervals` — per-member spans that aligned to nothing (the corpus graph's
  singletons).
- `cross_text_mask` — union of the two, original-coordinate intervals ready for `extra_masked`.
- `masked_cross_similarity` — proves a mask *changes* a downstream alignment (the mask-effect signal).
- `lift_intervals_across` + `persist_lifted_track` (append run version, FR-41) + `lifted_track_is_stale`.
11 tests.

### C5c — Cross-text conservation track ✅ (`72134fb`, FR-30)
`cross_text_track` — corpus conservation on the **root lens** via `project_to_root`: root-frame
`segment_offsets` + a per-segment `[0,1]` conservation scalar (member_count / member_total) +
`rendering.track_view: "root-conservation-lane"`; `write_cross_text_track` →
`workspace/collections/{id}/tracks/`. 3 tests.

> **FLAG (iii) — collection-scoped, NOT injected into the root project's per-project registry.** The plan
> said render "via the FR-13 lane loop". Instead the track is written under the *collection* directory and
> the frontend renders the lane directly — injecting a cross-text artifact into a single project's track
> registry would widen blast radius (shared persist/remap, per-project readers) for no gain. Deliberate
> deviation.

### C5d — HTTP + CLI surface ✅ (`f8d28d0`, FR-37)
`server.py` +GET `corpus-repeats` / `low-correspondence` / `cross-text-mask/{member}` / `root-track` and
+POST `liftover` (with `persist` option); `LiftoverRequest` at **module scope** (the future-annotations
FastAPI body-parsing gotcha). `cli.py` `collections` subgroup gains `corpus-repeats` / `cross-text-mask` /
`root-track` / `liftover` for parity. 2 parity tests.

### C5e — Frontend + in-browser proof ✅
**Frontend (`browser/src/components/CorpusView/`):**
- `corpusOverview.ts` — new pure transforms `repeatLanes()` / `conservationLane()` / `conservationColor()`
  + `CorpusRepeats` / `RootTrack` types. Unit-testable, no React/fetch (leaf pattern).
- `CorpusView.tsx` — `loadOverview` also GETs `corpus-repeats` + `root-track?root=<phyletic suggested
  root>`; renders `<RepeatLanes>` (one red-band SVG per member, x-scaled by `lengths[m]`) and
  `<ConservationLane>` (root-frame heat lane). `corpusOverview.test.ts` +4 (vitest 72 total).

**Backend tweaks (mods to the already-committed C5 files):** `corpus_repeats` gains a `lengths` field and
`cross_text_track` a `root_length` (frontend lane x-scaling); new GET `mask-effect?a=&b=&metric=` (proves
done-crit 2 end-to-end: unmasked vs masked word-overlap matrix + `changed` bool). `_phrase_intervals`
optimized to a single-pass O(tokens × phrase-lengths) set-membership scan.

> **FLAG (iv) — corpus-repeat cost.** `_phrase_intervals` was O(phrases × tokens) — untenable on the
> real 5.5 MB C4 member. Rewritten single-pass to O(tokens × phrase-lengths), behavior-identical
> (16/16 masking unit tests unchanged). Still per-member linear; genuine corpus-scale
> many-large-members is C6 recall-dial territory.

**In-browser proof rig (isolated — Sir's shared `:8080` untouched):**
`core/.venv/bin/palimpsest serve .scratch/c5-demo --port 8092` against a **fresh** workspace (not the
shared `.scratch/demo`). Fixture **`c5-masking-proof`** via gitignored `.scratch/c5_setup.py`: three tiny
synthetic members. `browser/e2e/corpus_masking_c5.spec.ts` (3 tests) drives all four done-criteria green.
Rerun: `cd browser && PALIMPSEST_BASE_URL=http://localhost:8092 PALIMPSEST_API_URL=http://localhost:8092 npx playwright test corpus_masking_c5 --reporter=list`.

**Fixture engineering (the non-obvious part).** A natural-English fixture over-merged the whole corpus
into a single `core` component (uniform, meaningless conservation lane); a fully token-disjoint fixture
produced **zero** alignment records. Both are consequences of the committed alignment pipeline, not C5:
`word_overlap` is raw Jaccard on `.lower().split()` (no stopword stripping), and `smith_waterman` uses
`min_length=2` with `score = sim*2 − 1` (identical paragraph +1, disjoint −1). So a homology block needs
**≥2 consecutive identical paragraphs** to be reported, and **≥2 token-disjoint separator paragraphs** to
cancel a block's +2 buffer and reset the SW diagonal (else the positive score bridges a lone unique
paragraph and re-merges). The fixture is built to those constraints: SHARED (2 paras, all three) → core,
REFRAIN (2 paras, alpha+beta) → shell, coined-disjoint runs → singletons. Result graph on `root=c5-alpha`:
**core cons 1.0 / singleton cons 0.333 / shell cons 0.667** — real variation. (One caveat: SW's
repeated-traceback also emits trailing-mismatch records, e.g. `q[0:3]` score 1.0, which absorb one
adjacent unique paragraph into the core anchor — a committed-pipeline artifact; the lane still varies.)

**Live-verified values:** corpus-repeats `phrase_count=60`, `lengths {alpha 317, beta 322, gamma 196}`;
mask-effect `a=alpha,b=beta` → `changed=true`, matrix `[7,7]→[2,7]`; liftover core span `alpha[0,50] →
beta[0,142]` (lands), singleton span `alpha[138,186] →` dropped.

**Done-criteria (plan §C5):** (1) corpus-repeat layer renders on the overview ✓ · (2) cross-text mask
changes a downstream alignment ✓ · (3) cross-text conservation track draws on the root lens ✓ · (4) mask
lifted A→B lands at correct B-coords (block-granular) and drops unaligned spans ✓ · (5) suites green
(backend 891, frontend 72) ✓.

## C6 — Corpus analyses, probe & scale (FR-31, FR-22, FR-35)

### C6a — Corpus analyses leaf + anchor honesty ✅ (FR-31)

**The load-bearing finding (#9 validation review).** Running the word-method alignment on the standing
Matthew-Mark validation collection (DR-MM ↔ Geneva-MM, a 1747×1749 verse-level word-overlap matrix)
exposed two compounding defects in `smith_waterman`, both pre-existing (C2/C3, not a C6 regression):

1. **Silent cap.** The extraction loop ran `for _ in range(min(100, n*m))` — a hard 100-alignment
   ceiling with no report when hit.
2. **Insufficient traceback masking.** Each extraction marked only its *traceback-path* cells `used`
   and never checked used cells, so the next `argmax` re-discovered the *same* accumulated diagonal
   shifted by one column — a flood of near-duplicate records. On the validation matrix this exhausted
   the 100-cap re-finding the early-Matthew diagonal, leaving **all of Mark and the later text
   unaligned** (records all started at paragraph 15, ended 473–478).

**Before → after (empirical, `.scratch/verify_c6a.py`):**

| metric | before | after |
|---|---|---|
| DR Matthew verses covered | fragment of one region | **986 / 1070 (92%)** |
| DR Mark verses covered | **0%** | **390 / 677 (58%)** |
| corpus graph | 1 core / 4 singleton (coarse) | 67 core / 0 shell / 140 singleton (honest) |
| record score range | flat 32–35 (near-dupes) | 0.11–35.67 (real distribution) |

**The fix (`smith_waterman`).** Waterman-Eggert-style non-overlap: accepted alignments consume their
cells and traceback stops at any consumed cell, so alignments are cell-disjoint; a candidate whose
paragraph ranges overlap an accepted alignment on **both** axes (a shifted diagonal or trailing-mismatch
extension) is rejected — while a genuine repeat (one query range → several target ranges, overlapping on
one axis only) survives. The silent cap is replaced by `max_alignments: int | None = None` (default
exhaustive; a positive limit is logged at WARNING when hit — never silent). *Performance:* naive
exhaustive extraction re-scanned the 3M-cell matrix per iteration (~6 min on the validation matrix);
since `H` is fixed after the DP fill, candidate cells are now sorted **once** and walked, skipping
consumed cells — back to **~5.6 s**, byte-identical record set.

**Anchor honesty (plan §C6a).** `build_corpus_graph(…, anchor_trim=φ)` trims each record's block inward
past boundary cells whose cross-similarity is `< φ` (read from the stored `cross_similarity` signal)
before the homology union, so a shared block extended by a weakly-overlapping trailing/leading paragraph
no longer absorbs a disjoint passage into a `core`/`shell` component (the exact artifact flagged in the
C5 note above). Default `0.0` preserves prior behavior; the trimmed span is reported under
`summary.anchor_trim`. On the validation collection, `anchor_trim=0.3` resolves the coarse 458-verse
merged anchor into finer per-passage anchors (core 67→75, singletons 140→156).

**Corpus-analyses leaf** (`analysis/corpus_analysis.py`, pure/dependency-free, mirrors `phylo`/`textstats`):
corpus **IDF/BM25** (down-weight cross-member boilerplate), **single-linkage near-duplicate clustering**
over the pangenome Jaccard distance, and **diffusion/spread** (per-component breadth + per-member reach) —
explicitly undirected: spread across members, never a who-influenced-whom claim (the reference-free graph
carries no arrow of transmission). Assembler `corpus_graph.corpus_analyses` reads member texts + the graph
and calls the leaf. On the validation collection: 1888/3041 vocabulary terms are cross-member boilerplate
(two translations of one text), most-discriminative terms are translation-specific spellings (DR "abia" vs
Geneva "abijah"), member_reach symmetric at 0.745.

**Surface:** `GET /api/collections/{id}/corpus-analyses`; `POST …/corpus-graph?anchor_trim=`;
CLI `collections corpus-analyses` + `corpus-graph-build --anchor-trim`. **Tests:** +13
(`test_corpus_analysis.py` 6, `test_alignment.py` non-overlap/cap 4, `test_corpus_graph.py` trim/analyses 3);
full backend suite **904 green** (was 891).

**Honest limitation (carry to C6c).** Word-overlap at verse granularity detects translation-equivalence
strongly (100 same-book diagonal records) but synoptic Mt↔Mk parallels only weakly (3 cross-book records) —
shared pericopes share *content/structure*, not exact *wording*. That is a property of the word metric, not
the extractor; embedding-method alignment (and the C6c recall dial) is where synoptic recall improves. The
synoptic TP/TN oracle for scoring this lives at `core/tests/fixtures/validation-mm/synoptic-ground-truth.json`
(101 shared pericopes, 51 unique).

### C6b — Probe mode `R(q, Corpus)` ✅ (FR-31)

Retrieval over a collection's **shared embedding space**: rank every member's chunk embeddings against a
query vector and return the corpus-wide top-`k` with `(project_id, chunk_index, text, similarity)`
attribution. The value it adds over the pairwise C2 engine is *one-to-many* — "which passages anywhere in
the corpus are nearest this query" — rather than a fixed A↔B matrix.

**The honesty guarantee is the C1 metric-congruence contract (FR-27/39), applied at two boundaries, so a
probe is never a silent cross-space comparison:**

1. **Members.** `_gate_congruent_cohort` resolves each member's embedding layer (newest-wins) and computes
   its congruence key (`embedding:{metric}:{model_fingerprint}`). Any member missing the layer, or sitting
   on a divergent key, raises `MetricCongruenceError` naming the offenders and the reconcile action — the
   same picture the compatibility badge shows. No partial-corpus probe.
2. **Query.** The query vector must carry the corpus dimension; and when the query is embedded from text at
   the boundary, its re-derived `model_fingerprint` must equal the corpus key's fingerprint. A query
   embedded with a different provider/model is rejected *before* any search.

**Architecture (leaf-vs-glue, deliberate).** The core `probe_corpus(…, query_vector, …)` takes a *vector*
— so the gate + `SqliteVecStore.search` + merge/top-`k` are deterministic and unit-testable with no live
embedding service. Turning query *text* → vector is service I/O (MLX/Ollama), isolated at the boundary in
`embed_probe_query`; a fully service-free query path, `query_vector_from_ref`, reuses a passage already
embedded in the corpus ("find passages like this one"). Nothing is silently dropped: every member search is
reported (`members_searched`, `n_candidates`), and `k` caps only the returned rows, not the candidate count.

**Refactor (zero blast radius).** Extracted `collections_ops.member_embedding_layer` (returns the whole
`BoundLayer` — label + capability) as the single newest-wins resolver; `member_embedding_capability` now
delegates to it. This lets the probe locate the vector DB *and* congruence-gate from one resolution. All 904
prior tests stayed green, confirming behavior-identical delegation.

**Surface:** `POST /api/collections/{id}/probe` (body = `q` text + provider/endpoint/model, **or**
`ref_project`+`ref_chunk`; `409` on any congruence failure, `400`/`404` otherwise); CLI
`collections probe … --query …` or `--ref-project/--ref-chunk`. **Tests:** +13 (`test_collections_probe.py`
— ranking/attribution/snippets, ref-mode, and the full fail-loud gate: missing layer, incongruent members,
wrong-space query fingerprint, wrong dimension, token metric, unknown collection, CLI parity). Full backend
suite **917 green** (was 904).

**Note (standing collection).** The validation members were aligned with the embedding-free *word* method,
so they carry no embedding layer yet — the probe is proven here on deterministic synthetic vector stores.
Embedding the standing collection into a shared space (then an in-browser probe) is a C7/live-validation
step, not a C6b backend gate.

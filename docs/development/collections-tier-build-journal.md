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

## C4 — Collection overview visualization (FR-33, FR-38) — IN PROGRESS

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

**Remaining C4 (frontend, Task #6):** collection-overview surface (Circos chords + Mauve block-map +
bubble + the phyletic tree) consuming `/corpus-graph` and `/phyletic-tree`; click-through overview →
pair dotplot → single-text browser (the three zoom tiers); in-browser Playwright proof on a real
≥3-text collection (isolated server, leaving the shared `:8080` untouched — the C2/C3 pattern).

# Collections Tier — Development Plan

**Status:** Draft for human review
**Date:** 2026-06-30
**Companion (vision & requirements):** [collections-tier-vision.md](./collections-tier-vision.md) (FR-23…37, NFR-C1…7, OQ-1…7)
**Continues:** [wave0-analysis-suite-plan.md](./wave0-analysis-suite-plan.md) — P9 (seam-lift) landed; P10/P11 (cross-text) are **reframed here** as consumers of this tier rather than independent phases.

> This is the phased build plan for the cross-text analytical tier. It parallels the Wave-0 plan: a critical path, per-phase done-criteria, and a risk register. Phase numbers are `C1…C7` to avoid colliding with the Wave-0 `P1…P11` namespace; the Wave-0 plan's deferred **P10 ≈ C2+C4** (pairwise engine + synteny lens) and **P11 ≈ C3+C6** (corpus graph + scale).

---

## 0. Decisions

**Decided by Sir (2026-06-30):**
- **OQ-1 — Corpus model: REFERENCE-FREE.** The default corpus model is a **co-equal alignment graph** (pangenome idiom): no text is privileged as a backbone. Pairwise alignments are the graph's *edges*; the graph is the canonical corpus artifact. A **root-backbone projection** (the UCSC/JAX synteny browser) is an explicit **per-view lens** computed from the graph on demand — used for pairwise synteny, translation/recension alignment, and "map everything onto text X" views. It is not the default ontology.
- **OQ-7 — Build sequence:** plan doc → doc-review gate → **C1 object-model foundation** → **C2 visible pairwise result** → remaining implied components (C3…C7).

**Also decided (2026-06-30 review):**
- **OQ-2 — Work = lightweight user-asserted `work_id` tag** (multi-level allowed; not a heavy entity).
- **OQ-3 — Non-destructive run versioning + ground-truth-mask supersede**; staleness triggered by a ground-truth-masking re-run (not a re-import); removal tombstones.
- **OQ-4 — Metric-congruence contract** (generalizes embedding-compat to all metrics): fail-loud + explicit reconcile.
- **OQ-5 — Collection mask = union (additive)**: a collection mask unions with a member's project mask, never un-masks it; both layers surfaced distinctly (C5).
- **OQ-6 — Collection artifacts under `workspace/collections/{id}/`**: parallels the per-project layout (C3 persistence; FR-32, NFR-C2).

**All OQ-1…OQ-7 ratified (2026-06-30).** The tier is gated only by the C1 build go-ahead.

---

## 1. Critical path

```
C0  Planning & doc reconciliation  ──►  [DOC-REVIEW GATE]
                                              │
C1  Object-model & operand foundation  ◄──────┘   (FR-23–28, 37, 41, 43)
        │
        ├──►  C2  Pairwise engine: heatmap + dotplot (graph EDGE primitive)   (FR-21, FR-33, FR-40, FR-36)
        │           │
        │           └──►  C3  Reference-free corpus graph (DEFAULT)  (FR-31 corpus, pangenome)
        │                       │
        │                       └──►  C4  Collection overview viz (Circos / graph / block-map / phyletic tree)  (FR-33, FR-38)
        │
        ├──►  C5  Cross-text masking, tracks & liftover   (FR-29, FR-30, FR-42)
        │
        └──►  C6  Corpus analyses, probe & scale strategy   (FR-31, FR-22, FR-35)

C7  Collection workbench UI & operational tooling  (FR-34, FR-35, FR-37, FR-39, FR-41)  — lands incrementally with each phase's backend (the Wave-0 P5/P6 pattern)
```

`C1` is the gate the rest depends on; `C2` is the first visible result; `C3` is the default model proper; `C4`/`C5`/`C6` fan out from there; `C7` is woven through (each capability's UI ships with its backend, not at the end).

---

## 2. Phases

### C0 — Planning & doc reconciliation *(this step)*
- **Deliverables:** this plan; `collections-tier-vision.md` reconciled to reference-free-as-default (root demoted to a lens).
- **Done:** both docs coherent under OQ-1; Sir's review at the gate before any code.

### C1 — Object-model & operand foundation  *(Sir's #1; FR-23–28, 37, 41, 43)*
The "collection tier" P10 was always gated on. Pure substrate; minimal UI.
- Distinguish **Work / Imported Text / Project / Collection** (FR-23): Imported Text content digest + optional multi-level `work_id`; the Imported Text + masking/sectioning config a Project derives from; the **subtext-extraction edge** `Project.derived_from` (FR-43).
- **Membership lattice + inverse navigation** (FR-24): extend `core/palimpsest/collections.py` (`collections_for_project`, `link_derived`) with edition-sibling, shared-Work, and parent/child-subtext queries; both-direction navigation.
- **Collection-local role** (FR-25): per-member `role` (default co-equal `member`; optional `root` lens), collection-local, not a Project property.
- **Cross-project operand resolution** (FR-26): `resolve_operand(collection, project_ref, requirements)` binds a member's `{chunk, embedding?, repeat_mask}` into an `Operand` (vision FR-18), fail-loud, reusing the resolver (`tracks/requirements.py` + `tracks/bundles.py`, FR-7) across projects.
- **Metric-congruence contract** (FR-27): per-metric congruence key (analysis-type + model/params + dim + analyzable digest); fail-loud on mismatch with an explicit reconcile action; covers all metrics, not just embeddings.
- **Lifecycle** (FR-28): re-import = new instance; re-run edits in place; content-address results by operand identity; stale-flag on ground-truth-masking re-run, tombstone on removal.
- **Non-destructive run versioning** (FR-41): keep analysis-run versions with metadata; ground-truth (Structural/Content) masks supersede.
- **Done-criteria:** assemble a collection from existing projects; bind operands across projects (fail-loud when layers missing/incongruent); detect per-metric incongruence; re-run keeps prior versions; CLI + HTTP parity (FR-37); backend tests green. No regression in single-text projects (NFR-C1).

### C2 — Pairwise engine: heatmap + dotplot (the graph EDGE primitive)  *(Sir's #2; FR-21, FR-33, FR-40, FR-36)*
The first visible cross-text result and the graph's **edge** primitive. Two distinct products (vision §3.1):
- **Chunk-distance heatmap** — the dense M×N matrix over a congruent metric (FR-27). Generalize `DotplotView` (a heatmap renderer despite its name) from square `R(A,A)` → rectangular `R(A,B)`.
- **Local-alignment dotplot** (FR-40) — drop the `_is_self` diagonal guard so LASTZ seed-and-extend (`_extend_alignment`) becomes **Smith-Waterman local alignment** across two operands; score each alignment *f(length × [matchiness − gappiness])*; pick an empirical cutoff on the score distribution; render only high-scoring alignments. Seed sensitivity = the recall dial. (diagonal/symmetry/dedup mode-conditional, vision FR-19, seam-lifted in P9.)
- **Overlay**: heatmap and dotplot share the character-coordinate plane → alignment streaks over the heatmap and chunk scores under the dotplot, bidirectionally.
- Persist the pairwise alignment as an `OffsetMap`-bearing **edge** artifact (operand→operand; a root projection is `operand→root`, principles §4.1).
- Ribbon panel (ACT idiom); brushable side-by-side; direction toggle; PAF export (FR-36, `specs/paf-v0.1.md`).
- **Done-criteria:** a clickable two-text heatmap + thresholded dotplot + overlay + ribbon against live data (gospel-synopsis or DR/KJV pair); metric-gap layer (paraphrase vs verbatim) present; PAF export; in-browser Playwright proof (the Wave-0 verification bar); tests green.

### C3 — Reference-free corpus graph  *(the DEFAULT model; FR-31, pangenome)*
- Assemble the **alignment graph** from C2 pairwise edges (all-pairs, or candidate-pruned per C6): nodes = passage spans, edges = correspondences, no privileged axis.
- **Pangenome classification:** every passage tagged core (all members) / shell (some) / singleton (one).
- Persist the graph + classification under `collections/{id}/` (FR-32), provenance-stamped by operand identity (NFR-C2).
- **Root projection as a view:** given a chosen root, project the graph to that frame on demand (reusing `operand→root` `OffsetMap`) — the synteny lens, not stored ground truth.
- **Done-criteria:** build a graph over a ≥3-text collection; core/shell/singleton classification correct on a fixture; project to a chosen root and verify coordinates; tests green.

### C4 — Collection overview visualization  *(FR-33, FR-38)*
- **Circos chord overview** (all-pairs ribbons; the JAX Circos screenshot) and a **graph/bubble view** (shared backbone + text-specific bubbles) as the *primary* corpus surfaces.
- **Mauve-style block-map** (per-member colored lanes, shared blocks same-colored).
- **Phyletic / stemma tree** (FR-38) beside the overview: *manual-first* (user assigns the root taxon + groups text-taxa into clades as a working hypothesis), *distance-driven later* (recompute by neighbor-joining / nearest-neighbor once inter-text distances exist, auto-suggest the optimal root, user overrides only then). A reading of the reference-free graph's distance structure and the primary root-selection aid for 3+ texts.
- Root-projected **synteny browser lens** (UCSC/JAX block-view + dotplot) reachable from any node/pair.
- **Done-criteria:** overview renders a real multi-text collection; the phyletic tree builds manually and recomputes from distances with an auto-root suggestion the user can override; click-through from overview → pair dotplot → single-text browser (the three zoom tiers); in-browser proof.

### C5 — Cross-text masking, tracks & liftover  *(FR-29, FR-30, FR-42)* — COMPLETE
- **Corpus-repeat detection** (a phrase recurring across members) generalizing Wave-0 `repeats`.
- **Cross-text masking** (corpus-repeat ∪ low-correspondence) — interval sets assembled cross-corpus, then excised through the existing per-member `analysis_view` `extra_masked` mask path (riding the single-text `OffsetMap` machinery); declared, reported, never silent.
- **Cross-text conservation track** — projected to a chosen root lens via `project_to_root` and rendered as a root-frame conservation lane. *As built:* **collection-scoped** (`collections/{id}/tracks/`) + a dedicated Corpus-view lane, deliberately **not** injected into the root Project's per-project FR-13 registry (blast-radius). Collection-level annotation tracks (one declaration, per-member remap) remain planned.
- **Liftover** (FR-42) — given an A↔B alignment, project A's masks / annotations / score-tracks onto B's coordinates via a purpose-built **`AlignmentMap`** (the cross-text sibling of the single-text excision `OffsetMap`), producing new additive remapped versions on B. **Block-granular** (lifts to the whole aligned paragraph block, no interpolation; unaligned intervals reported `dropped`). Purely additive; nothing destroyed.
- **Done-criteria (all met, in-browser proof `cebbfe0`):** corpus-repeat layer renders on the overview ✓; cross-text mask demonstrably changes a downstream alignment ✓; a cross-text track draws on the root lens ✓; a mask/track lifted A→B lands at correct B-coordinates as a new additive version (and drops unaligned spans) ✓; tests green (backend 891 / frontend 72) ✓.
- **Carried into C6a (found during the C5 proof):** `smith_waterman`'s repeated-traceback emits *trailing-mismatch* records (a shared block extended by one disjoint paragraph) that let the C3 corpus graph absorb a unique passage into a `core`/`shell` homology component — polluting pangenome classification honesty. Fix = trim anchors to high-similarity cells (or post-filter trailing mismatches) before homology union. Pre-existing C2/C3 behavior, not a C5 regression.

### C6 — Corpus analyses, probe & scale  *(FR-31, FR-22, FR-35)*

Three separable workstreams; **C6a/C6b are decision-independent** (safe to build first), **C6c** carries the run-persistence decision (below). Each sub-phase: green backend + frontend where applicable + in-browser proof on the standing validation collection, commit-local, push on Sir's word.

**C6a — Corpus analyses leaf** *(decision-independent)*
- Pure numeric/graph leaves over the existing C3 graph + embedding store, mirroring the `analysis/` leaf pattern (`textstats` / `phylo` / `chunk_stats`): **corpus IDF/BM25 weighting** (down-weight cross-member boilerplate); **near-duplicate / stemma** clustering over the graph's Jaccard structure (reuse `phylo`); **formula/topos diffusion & influence** over the graph (honest about non-directionality given the reference-free model).
- **Anchor-honesty fix (carried from C5):** trim C3 corpus-graph anchors to high-similarity cells (or post-filter `smith_waterman` trailing-mismatch records) before homology union, so a shared block no longer absorbs a disjoint unique paragraph into a `core`/`shell` component. Re-verify pangenome classification on the standing collection.
- HTTP + CLI parity; unit tests.

**C6b — Probe mode** *(decision-independent)*
- `R(q, Corpus)` over the shared embedding space (`SqliteVecStore.search`), gated by the C1 **metric-congruence contract** (FR-27/39) — fail-loud on incongruent members, never a silent cross-key comparison. HTTP + CLI + tests.

**C6c — Scale: candidate generation as a recall dial** *(FR-35; run-persistence decision here)*
- Small matrices default **exhaustive/dense** (no missed signal); large matrices *recommend* (never force) candidate generation — ANN over embeddings (HNSW `efSearch` / IVF `nprobe` / multi-probe LSH / over-fetch-then-rerank) or MinHash-LSH over shingles; the alignment family's dial is seed sensitivity. The mode spans **exhaustive ↔ high-recall ↔ fast** with an **estimated-recall readout** and a **forced-exhaustive escape hatch**; exact scoring on candidates → sparse top-k; never a silent cap (report what was pruned).
- **Compute infrastructure:** parallel pair evaluation (worker pool), tiled/streamed matrices, MLX batch embedding; memory discipline (tiling, sparse top-k, memmap, dtype control); staged **%-progress** for long sweeps.
- **Run-persistence decision (Sir, 2026-06-30):** C6 adopts a **lightweight run journal** — sweep progress + candidate sets persisted to a JSON/SQLite sidecar under `collections/{id}/` for resumability, *without* a general job scheduler (matches the content-addressed, disk-reconstructs-the-run discipline; bounded scope). **A full persistent job DB (scheduler/queue) is a required LATER-PHASE feature** — deferred, not dropped — to be implemented when corpus-scale multi-stage sweeps outgrow the sidecar (revises the Wave-0 *"no persistent job DB"* non-goal in two steps: sidecar now, full job DB later).
- **Done-criteria:** corpus analyses produce results on the standing validation collection; the anchor-honesty fix verified; the recall dial prunes an O(N²) sweep with a reported estimated-recall and a working forced-exhaustive escape; a long sweep reports staged progress and **resumes from the run journal after interruption**; tests green.

### C7 — Workbench UI & operational tooling  *(FR-34, FR-35, FR-37, FR-39, FR-41; woven through C1–C6)*
- Tabs: Members / Overview / Compare / Corpus / Masking-&-Tracks; header **metric-congruence compatibility badge** (per metric, which member pairs share a congruence key; FR-39).
- **Metric-congruence surface** (FR-39): per metric, show which member chunk-sets are congruent and therefore comparable; incongruent pairs surface the reconcile action — the UI manifestation of FR-27.
- Operational tooling: **metric-congruence reconciliation** (costed re-embed / re-run a metric to a common key — embedding-space reconciliation is the common instance), **operand binding** UI, **pre-run cost dialogs** (P2 / NFR-C4), the **candidate-generation recall dial** (exhaustive ↔ high-recall ↔ fast, estimated-recall readout, forced-exhaustive escape), a **run/version manager** (list / keep / delete non-destructive run versions; ground-truth masks supersede; FR-41), root re-coordination.
- **Done-criteria:** each tab live with its backing capability; the congruence badge correctly flags an incongruent pair and routes to reconcile; the run/version manager lists and deletes versions with ground-truth supersede honored; every expensive op shows a pre-run estimate and never auto-runs; CLI + HTTP parity throughout.

---

## 3. Risk register

| Risk | Severity | Mitigation |
|---|---|---|
| Reference-free graph is new machinery (construction, storage, viz) with no existing component | High (highest-novelty) | Build the graph **from** the C2 pairwise edge primitive so it is assembled correspondences, not a new alignment algorithm; reuse `OffsetMap` for any root projection. Treat Circos/bubble viz as the one genuinely new frontend build. |
| O(N²) pair cost for corpus mode | High | Candidate generation as a **recall dial** (FR-35): ANN over embeddings / MinHash-LSH over shingles before exact scoring; exhaustive ↔ high-recall ↔ fast with estimated-recall readout + forced-exhaustive escape; sparse top-k; explicit cost estimate; report what was pruned (FR-22, NFR-C4). |
| Members carry a metric (embedding, sentiment, topic…) under different keys and can't be compared | Med | **Metric-congruence contract** (FR-27, FR-39): per-metric congruence key; fail-loud + explicit costed reconcile; never a silent cross-key comparison. Embedding-model mismatch is one instance, not the whole rule. |
| Candidate generation silently misses weak-but-real similarity | Med | The recall dial is *optional and dimension-driven* — small matrices stay exhaustive; large ones expose an estimated-recall readout + forced-exhaustive escape; pruning is always reported, never silent (FR-35, NFR-C7). |
| Corpus-scale compute (parallelism, memory, long-sweep progress) outgrows the Wave-0 in-memory model | Med | Worker-pool parallel pairs, tiled / streamed / memmapped matrices, MLX batch; staged %-progress. **Run-persistence (decided 2026-06-30):** a **lightweight run journal** sidecar under `collections/{id}/` for resumability in C6c; a **full persistent job DB is a required later-phase feature** (deferred, not dropped) for when multi-stage sweeps outgrow the sidecar. |
| Coordinate honesty across many frames | Med | Every cross-text offset remapped operand→(root lens) by the assert-or-fail discipline of principles §4 (NFR-C6); root projection is the only place a second frame enters. |
| Membership churn silently invalidating results | Med | Content-address by operand identity; stale-flag / tombstone / re-coordinate (FR-28); disk never lies. |
| Scope sprawl across 7 phases | Med | C7 UI lands per-phase (not at the end); each phase has its own done-criteria + in-browser proof; hold commits at green milestones, push only on Sir's word. |

---

## 4. Definition of done (the tier)

All FR-23…43 satisfied; the **reference-free corpus graph navigable as the default** (graph/Circos overview + pangenome core/shell/singleton + phyletic/stemma tree), with the root-backbone synteny browser available as a lens; pairwise **heatmap + thresholded dotplot + overlay + ribbon + PAF** working; cross-text masking + tracks + **liftover** + corpus analyses live; **non-destructive run versioning** (ground-truth masks supersede) in place; workbench tabs and operational tooling in place; CLI/HTTP parity; backend + frontend tests green; and an in-browser proof on a real multi-text collection (the Wave-0 verification standard).

---

## 5. Standing process notes

- **Commit discipline:** commit at green milestones **locally**; **push to shared `main` only on Sir's explicit word** (the Wave-0 P1–P9 pattern). The design docs (C0) stay uncommitted until the doc-review gate.
- **Verification bar:** backend pytest + frontend vitest + `tsc -b && vite build` + an in-browser Playwright proof against live data — the same bar every Wave-0 phase met. No phase is "done" on unit tests alone.
- **Principle conformance:** every new analytical knob is a declared `Param` (locked or open); no hidden defaults; fail-loud; disk reconstructs the run (analysis-design-principles P1–P5 + the acceptable-default rule).

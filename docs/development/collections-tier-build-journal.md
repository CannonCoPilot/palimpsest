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

# User-Story Workflow Audit & Remediation — 2026-06

**Scope:** the curation/authoring workflow — **Import → Mask (review & apply) → Subtext (derive) → Collection** — as distinct from the analysis pipeline covered in [`analysis-paradigm-audit-2026-06.md`](./analysis-paradigm-audit-2026-06.md).

**Method:** (1) three parallel read-only code investigations mapping each flow UI→API→storage; (2) a live end-to-end Playwright session driving a real Chromium against the running dev stack (frontend :5173, API :8080), role-playing a computational-literary-analysis expert; (3) targeted empirical verification of the data-layer finding via the live API.

**Test corpus:** the Douay-Rheims "Gold Set" project (`…1a24ae78…`).

## The user story under test

An expert wants to:
1. **Import** the Douay-Rheims bible.
2. **Review the maskings and apply** them.
3. Create a **subtext** that *includes* the Appendix books' content — their `introductions`, `footnotes`, and `chapter` text — but *excludes* the "Preface to the Reader" and the "Hard Words Explicated" sections.
4. Add that subtext into a **Collection** together with its parent Douay-Rheims.

## Verdict summary

| Step | Today | Blocking gap |
|---|---|---|
| Import a brand-new EPUB | ✅ works (file upload) | — |
| Import/re-import the Gold DR cleanly | ⚠️ partial | re-import clobbers; no "import as new copy" |
| Review masking (visual) | ✅ works | — |
| **Persist/apply masking** | ✅ **fixed (W5)** | "Apply masking…" in MaskingPanel bridges to the refine wizard |
| Derive a subtext (any flat type set) | ✅ works | — |
| **Derive an "Appendix-only" subtext** | ✅ **fixed (W1)** | geometric container scoping (`include_container_ids`); no `parent_id` dependency |
| Exclude Preface & Hard Words | ✅ free | both are their own types (`preface`, `glossary`) — just don't select them |
| Create a named collection | ✅ works | — |
| **Add parent + subtext to a named collection** | ✅ **fixed (W3)** | "Add to collection…" menu + Stage-3 collection picker |

**Bottom line (original audit):** the expert could perform the *easy* halves but **could not complete the core intent** — an appendix-scoped subtext, or a user-curated collection — through the UI.

> **Update 2026-06-23:** the three P0 story-blockers (W1 container scoping, W2 `parent_id` backfill, W3 collection-membership UI) and the P1 W5 apply-masking bridge are now **implemented** (backend 610 tests green, frontend tsc/vitest green). The core intent is expressible end-to-end pending a live browser click-through. See Part D for the shipped details.

---

## Part A — Findings by act

### Act 1 — Import  (PARTIAL)
- Entry: `ProjectPicker` "Import" → `ImportWizard` 5-step flow **Scan → Detect → Map → Mask → Apply** (`browser/src/components/.../ImportWizard.tsx`).
- Scan calls `GET /api/imports`, listing files under the server's `imports/` dir only. The `.scratch/demo/` DR source is **not** in `imports/`, so it cannot be selected there — but a `<input type="file">` upload control on the Scan step accepts an EPUB from any disk path.
- **Content profile is auto-detected, not selectable** (`content_filters.py` `detect_content_profile`; `PROFILE_DOUAY_RHEIMS` triggers on HTML class `wQnqgsgYTu`). No UI exposes or overrides it.
- The Gold DR EPUB *is* already in `imports/Scripture/Bibles/` with `status: "imported"`; completing the wizard against it warns "replaces the existing analysis" → re-import clobbers. No "import as a new copy" path exists.
- Re-entry for an existing project: project card ··· → **"Refine sections…"** re-opens the wizard at step 2 (Detect), skipping Scan (`resumeProjectId ? 2 : 1`).

### Act 2 — Review & apply masking  (PARTIAL)
- **Two distinct masking surfaces, not connected:**
  - **MaskingPanel** right-drawer (toolbar "Mask" button → `viewStore.toggleMaskPanel`): session-only overlay. Controls enumerated live: master On/Off; **Verse numbers** toggle; **15 per-type** toggles (Volume, Book, Section, Header, Front Matter, Title Page, Contents, Appendix, Glossary, Body, Preface, Introduction, Chapter, Heading, Footnotes — each Kept/Masked with counts); Reset; "Derive subtext…". **No Apply/Save button; makes no API call.**
  - **ImportWizard** Mask step → **"Confirm & Apply"** → `POST /api/projects/{id}/sections/apply` — the *only* permanent-persist path.
- The persist path is reachable **only** from Home → ··· → "Refine sections…", never from the reading view where the MaskingPanel lives. "Review and apply" is therefore not a coherent single flow today.

### Act 3 — Derive the appendix subtext  (PARTIAL — core gap CONFIRMED)
- Mechanism: `SubtextWizard` (3 stages) → `POST /api/projects/{id}/derive` (`server.py` `DeriveRequest` ~ln 101–109: `extraction_types`, `excluded_ids`, `title`, `author`, `collection_id`) → `derive.py` `derive_subtext()` / `compute_kept_spans()` (~ln 118). A subtext is a **materialized child project** on disk with a `derivation` stanza.
- DR parse (live) contains the needed semantic types: `appendix`×4, `preface`×1 ("THE PREFACE TO THE READER" = `preface-0001`), `glossary`×1 ("Hard Vvordes Explicated" = `glossary-0001`), `introduction`×7, `chapter`×3039, `footnotes`×1759.
- **Excluding Preface & Hard Words is free** — they are their own types; simply don't select `preface`/`glossary` in Stage 1. ✅
- **Appendix-only scoping is impossible.** Selecting `chapter`+`footnotes`+`introduction` pulls **all** canonical content too. Stage 2 (which groups by `parent_id`) showed all **4,805** candidate elements in one **"Ungrouped"** bucket — no "Appendix" branch — so isolating appendix content would require manually deselecting ~4,700 canonical chapters. Live-derived demonstration subtext = the whole text, not the appendices.

### Act 4 — Collection  (PARTIAL — gap CONFIRMED)
- Create empty named collection: sidebar "New Collection" → `window.prompt` → `POST /api/collections`. ✅
- **No UI to add an existing project to a collection.** `POST /api/collections/{id}/projects/{project_id}` works (verified 200 via direct call) but nothing in the UI invokes it; the BookCover ··· menu offers only Open/Refine/Re-import/Delete.
- SubtextWizard exposes no collection picker (`DeriveRequest.collection_id` is backend-only).
- The only way parent+child land together is the **auto-created `{parent}--subtexts` derived collection** (system-named, `kind:"derived"`), which cannot be merged with a user-named collection via UI.
- `GET /api/collections/{id}` (hydrated members) is never called by the frontend; collection view filters the list response client-side.

---

## Part B — New blockers found in the live run

- **B-1 (UX/robustness):** Subtext generation is **>30s, fire-and-forget**, button shows "Generating…" with no progress, ETA, or cancel.
- **B-2 (a11y/discoverability):** the toolbar "Mask" button exposes no `aria-pressed`/`aria-expanded` and no visible open-state.
- **B-3 (UX):** the only "apply masking" path is buried in Home → ··· → "Refine sections…"; invisible from the reading view (see W5).
- **B-4 (minor):** SubtextWizard modal overlay leaves the parent toolbar in the DOM behind it; pointer-event interception can mis-target controls.
- **B-5 (verify; likely non-issue):** Stage-1 checkboxes needed a full synthetic-event chain under Playwright (`change`+`input`+`click`); a real user's native click is unaffected. Flag for awareness only.

---

## Part C — Empirical investigation: `parent_id` population (KEY)

The "Ungrouped" Stage-2 collapse is caused by missing `parent_id` links. Verified via `GET /api/projects/{id}/sections`:

| Project | Import path | sections | with `parent_id` |
|---|---|---|---|
| Agnes Grey (novel) | live pipeline | 56 | **94%** |
| Geneva Bible | **live pipeline** | 2,271 | **0%** |
| Gold DR | fixture builder | 9,129 | **0%** |

**Conclusion:** this is **not** a gold-fixture-only artifact. The 0% holds for the *pipeline-imported* Geneva Bible as well, so `parent_id` is unpopulated across the entire scripture class — the platform's core use case — leaving Stage-2 subtext grouping with no container branches.

> **Root-cause correction (2026-06-23, from implementation introspection — the original hypothesis below was wrong).** The scripture geometry **does** nest correctly: querying `/api/projects/{id}/sections` on the gold DR shows each `volume`/`book`/`appendix` span *strictly contains* its chapter spans. So the spans were never "flat siblings that don't nest." The real cause is that **`_compute_parents()` was simply not applied/persisted** for these layouts: the gold builder (`bible_structure.py`) constructs `LayoutSection`s directly and never calls it, and the Geneva layout was saved without computed parents. It is an *application/persistence* gap, not a geometry gap. Two consequences followed for remediation: (1) **W1 needs no `parent_id` at all** — container scoping can be done geometrically by span-containment, which works on the existing gold DR today; (2) **W2 is a backfill** — recompute parents from the already-correct geometry on load, not a re-derivation of the nesting.
>
> *Original (superseded) hypothesis: "the scripture/verse overlay constructs flat sibling spans (book/chapter/verse) that don't nest under containing spans the way prose chapters do."*

---

## Part D — Remediation plan

Priorities: **P0** = blocks the stated user story; **P1** = correctness/coherence; **P2** = robustness/scale; **P3** = polish. These are also [design-principles](../design/analysis-design-principles.md) **P5** ("user controls and sees everything") violations — the user can neither express nor see container scoping, collection membership, or an apply action from where they review.

### P0 — story-blocking

**W1 — Container scoping for subtext derivation.** ✅ **Implemented 2026-06-23.**
Shipped as `include_container_ids: list[str]` on `DeriveRequest`, threaded through `derive_subtext()` → `compute_kept_spans(..., container_spans)`: an element is kept only when its span falls **fully within** any selected container's span (partial overlap excluded). Unknown/empty container ids **fail loud** (`ValueError` → HTTP 400) rather than silently producing an unscoped subtext. UI: a "Restrict to section(s)" container picker in `SubtextWizard` Stage 1. **Note:** this is *geometric* (span-containment) and does **not** depend on `parent_id`, so it works on the existing gold DR now — correcting the original "Depends on W2" assumption. It also resolves **W4** for the scoped case (front-matter `introduction`s fall outside the appendix span and are naturally excluded). Covered by `test_derive.py::test_derive_subtext_scoped_to_container` and `test_server.py::TestDeriveContainerScope`.

**W2 — Backfill `parent_id` for scripture-structured documents.** ✅ **Implemented 2026-06-23.**
Reframed from "production bug in nesting" to a **persistence/application gap** (see Part C correction): the geometry already nests; `_compute_parents()` just wasn't applied. Fix: `LayoutConfig` gains a `parents_computed: bool` flag; `load_layout()` lazily backfills (`if cfg.sections and not parents_computed: _compute_parents(...)`, then sets the flag and best-effort re-saves), so legacy gold/pipeline layouts get parents on first load without a migration. `detect_sections` and `put_sections` set/recompute the flag (user edits to containment recompute parents). Covered by `test_layout.py::test_load_layout_backfills_parent_id_for_legacy_layouts`. *Unblocks Stage-2 grouping for the entire Bible corpus.* (W1 no longer depends on this, but Stage-2's by-`parent_id` grouping does.)

**W3 — Collection membership UI.** ✅ **Implemented 2026-06-23.**
Wired the existing `POST /api/collections/{id}/projects/{project_id}` into the UI: an "Add to collection…" item (with a submenu of existing collections) on the project card ··· menu in `ProjectPicker.tsx`, threaded through `BookCover` → `HomeView` → library grid via `collections` + `onAddToCollection` props, plus a collection `<select>` in `SubtextWizard` Stage 3 (sends `DeriveRequest.collection_id`, so a derived subtext can join a collection at creation). *Enables a user-curated parent+subtext collection.*

### P1 — correctness / coherence

**W4 — Disambiguate the `introduction` type.** It conflates front-matter ("HISTORY") with per-appendix notes, so "include appendix introductions" drags in front matter. Split into a distinct type (e.g. `appendix_note`) or rely on W1 scoping.

**W5 — Make "apply masking" reachable from the reading view.** ✅ **Implemented 2026-06-23.**
Added an "Apply masking…" button to the MaskingPanel footer that bridges into the permanent apply path (the section-refinement wizard, which already persists masks to the saved layout). Because the wizard's `showImport`/`resumeProject` state is local to `ProjectPicker` (which only mounts when no project is active), the bridge is a one-way signal: the button stashes the active project id in `viewStore.refineRequestId` and calls `closeProject()`; `ProjectPicker`'s mount-effect honors the request (opens the wizard for that project) and clears the flag. Resolves B-3 and makes "review → apply" a single flow without duplicating the apply logic.

### P2 — robustness / scale

**W6 — Subtext generation progress + cancel.** Replace the >30s fire-and-forget with progress/ETA and a cancel; consider the async-job pattern used by analysis. (B-1)

**W7 — Stage-2 scalability.** A 4,805-item flat list is unusable for bulk include/exclude. Add per-group search/filter and "select all within container" (pairs with W1/W2).

**W8 — Import ergonomics.** Add a profile-override control (currently auto-only) and an "import as a new copy" path so an already-imported file needn't clobber. Lower priority — upload-from-disk already works.

### P3 — polish

**W9 — Mask button `aria-pressed` + visible open-state.** (B-2)
**W10 — SubtextWizard modal pointer-event layering.** (B-4)
**W11 — Verify Stage-1 checkbox event handling** is robust (likely a Playwright-only artifact; confirm no controlled-input edge case). (B-5)

---

## Appendix — provenance

- Live E2E run: 54 screenshots in `.scratch/e2e-douay/`, **zero JS console errors** across all sessions.
- `parent_id` figures: live `GET /api/projects/{id}/sections` on three projects (2026-06-23).
- Related: [`analysis-paradigm-audit-2026-06.md`](./analysis-paradigm-audit-2026-06.md) (analysis pipeline), [`analysis-design-principles.md`](../design/analysis-design-principles.md) (P1–P5 contracts).
- **Test artifacts created during this audit (pending cleanup):** subtext project `…-chapter-footnotes-introduction`; collections `e2e-test-dr-collection` (manual) and `…--subtexts` (auto-derived).
</content>
</invoke>

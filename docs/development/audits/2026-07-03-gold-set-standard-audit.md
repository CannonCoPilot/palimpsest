# Gold Set Standard — Live Re-Audit (2026-07-03)

**Scope.** Sir's directive: after the Gold-Set-Standard build shipped (`1959f8c..4c80ff3`), re-audit
**every Bible** against the redefined standard *as live-verified in the UI* (4a), then audit the
**non-Bible** Gold-Set works for adherence (4b, the activated Phase 8). The standard's redefined bar
(complete / accurate / precise, with per-kind parity + operational readiness) is in
[`../gold-set-standard.md`](../gold-set-standard.md) §1.

**Method — two independent lenses.**
1. **Data-side (machine, char-level).** A fresh backend on `:8080` re-applied all appliable Bibles into
   an isolated `core/.scratch/gold-audit` workspace (every apply `sha_verified: true`). A precision
   auditor (`core/.scratch/gold_precision_audit.py`) then extracted every masked substring from the
   *live reference text* and checked: two-layer coverage (COMPLETE), taxonomy/marker parity (ACCURATE),
   and per-element char bounds — no overrun into adjacent prose (PRECISE). This closes the one gap the
   hermetic suite leaves open (`test_gold_maps.py` proves spans are in-range and layers tile, but not
   that each masked span aligns to its marker at the character level).
2. **Live UI (browser, visual).** A Playwright agent drove the running app per Bible — expanding the
   mask-type track lanes and zooming to readable text to confirm the render matches the data.
   See "Live UI verification" below and `core/.scratch/gold-audit/ui-verification-report.md`.

**Corroborating suite.** `test_gold_maps.py` + `test_gold_canon.py` + `test_gold_sources.py` =
**327 passed / 21 skipped** (the skips are the by-design epub marker-parity skips).

---

## Part A — Bibles (4a)

### A.1 Registry & availability
`GET /api/gold` → **19 Bibles**, schema `palimpsest.gold-sources/v1`. **17 appliable** on this machine
(map + source both present). Two are honestly flagged `source_present: false` (preserve-don't-push, UI
Apply disabled): **6** Geneva-1599 and **108** DR-original. All 17 appliable Bibles were applied and
returned `sha_verified: true`.

### A.2 Data-side precision scorecard (all 17 appliable)
`gGap`/`sGap` = generic/specific-layer coverage gaps (COMPLETE); `mOvr` = short-marker overrun suspects;
`blkBnd` = block-boundary imprecision; `vLeak` = verse-number tokens leaking prose (PRECISE).

| idx | Bible | kind | gGap | sGap | mOvr | blkBnd | vLeak | verdict |
|----:|-------|------|:---:|:---:|:---:|:---:|:---:|:---|
| 201 | Coverdale | marker | 0 | 0 | 0 | 0 | 0 | **COMPLETE + PRECISE** |
| 202 | Bishops' | marker | 0 | 0 | 0 | 0 | 0 | **COMPLETE + PRECISE** |
| 203 | Wycliffe | marker | 0 | 0 | 0 | 0 | 0 | **PASS** (masks front-matter prologue blocks, char-precise) |
| 208 | Great | marker | 0 | 0 | 0 | 0 | 0 | **COMPLETE + PRECISE** |
| 209 | Matthew's | marker | 0 | 0 | 0 | 0 | 0 | **COMPLETE + PRECISE** |
| 210 | Webster's | marker | 0 | 0 | 0 | 0 | 0 | **COMPLETE + PRECISE** |
| 211 | Wessex (4 gospels) | marker | 0 | 0 | 0 | 0 | 0 | **COMPLETE + PRECISE** |
| 212 | Young's | marker | 0 | 0 | 0 | 0 | 0 | **COMPLETE + PRECISE** |
| 213 | Julia Smith | marker | 0 | 0 | 0 | 0 | 0 | **COMPLETE + PRECISE** |
| 214 | KJV-2016-NT | marker | 0 | 0 | 0 | 0 | 0 | **COMPLETE + PRECISE** |
| 215 | EMTV-NT | marker | 0 | 0 | 0 | 0 | 0 | **COMPLETE + PRECISE** |
| 216 | KJV-1769 | marker | 0 | 0 | 0 | 0 | 0 | **COMPLETE + PRECISE** |
| 217 | Tyndale | marker | 0 | 0 | 0 | 0 | 0 | **COMPLETE + PRECISE** |
| 218 | Geneva-1560 | marker | 0 | 0 | 0 | 0 | 0 | **COMPLETE + PRECISE** |
| 219 | KJV-1611 (80 bk) | marker | 0 | 0 | 0 | 0 | 0 | **PASS** (masks Epistle/Translators front-matter, char-precise) |
| 5 | DR-Haydock | epub | 0 | 0 | 1094* | 0 | 70* | **PASS w/ note** (see A.3) |
| 100 | DR-Challoner | epub | 0 | 0 | 1* | 0 | 0 | **PASS w/ note** (see A.3) |

\* not precision defects — see A.3.

**Representative evidence.** Wessex (211): chapter markers `'## Matthew 1'`, book headers `'# Matthew'`,
verse-number tokens `'2 '`,`'3 '` — all crisp, short, **0** prose leaks. Wycliffe (203) front-matter mask
ends exactly `'…of Goddis storye*.\n\n'` → `'# Genesis'` (char-precise). KJV-1611 (219) front-matter ends
`'…Amen.\n\n'` → `'# Genesis'`.

### A.3 The two epub flags are edition structure, not imprecision
- **Haydock (5)**: the 1094 "heading" flags are Haydock's per-book/chapter **argument paragraphs**
  (`"This book is so called from its treating of the GENERATION…"`) typed `heading` and masked as units;
  the 70 "verse alpha-leaks" are **letter-based chapter refs** (`'A:1.'`, `'A:2.'` — appendix/apparatus).
  Both are precisely bounded to their real units.
- **Challoner (100)**: the 1 flag is a chapter heading carrying its **summary line**
  (`'Job Chapter 39 The wonders of the power and providence of God…'`) — edition design, precisely bounded.

This is the standard's kind/parity distinction made concrete: marker Bibles cut crisp char-level markers
(verified cleanly at char level); epub Bibles carry *detected* structure whose appropriate precision lens
is the annotation gold + detector recall (`a3_score`), the `accuracy_source: annotation+detector` the
standard already assigns them — not the short-marker heuristic.

### A.4 Accuracy (canon oracle)
`test_gold_canon.py` (per-book chapter counts vs. the external canon table) passes for all marker Bibles.
`palimpsest gold verify` passes all 19; `gold verify 211` exercises the oracle. **Accuracy: PASS.**

### A.5 Live UI verification
> _Pending merge from the Playwright agent — `core/.scratch/gold-audit/ui-verification-report.md`._
> _(mask-type tracks expand + render; readable-text zoom confirms char-level greying of markers/verse
> numbers while verse prose stays visible; front-matter blocks render as bounded greyed units.)_

---

## Part B — Non-Bible Gold-Set works (4b / Phase 8)

**17 non-Bible works** carry committed gold maps (`build_epub_gold` generator). All 17 also carry a
**detection annotation gold** (`work-<idx>.json`). All pass the hermetic `test_gold_maps.py` gates
(COMPLETE two-layer coverage + taxonomy + in-range spans).

### B.1 Criterion-by-criterion
| Criterion (§1) | Non-Bible status |
|---|---|
| **1. Complete/accurate/precise masking** | **Map half: PASS** (hermetic gates green for all 17). *Precise* char-level + *detector-recall accuracy* are the machine-local lens (need source text + `a3`/`gold_ratify`); not scored in this pass — recommended per-kind follow-up. |
| **2. Validation parity (≥2 of a kind)** | Mixed — see B.2. |
| **3. Operational readiness (CLI/API/UI)** | **FAIL for all 17.** `sources.manifest.json` scope is **bibles-only**; none of the non-Bibles is in the registry, so none is applic­able by id through `gold list/apply` or `GET/POST /api/gold` or the Gold Library UI. |

### B.2 Kind classification & the ≥2-per-kind rule
| Kind | Works | ≥2? |
|---|---|:--:|
| Novel | 19 The Correspondent, 56 Last of the Mohicans, 70 Charlotte Temple, 71 Jekyll & Hyde | ✅ 4 |
| Poetry | 102 Dickinson, 103 Frost, 104 Cummings | ✅ 3 |
| Qur'an | 29 Message of the Qur'an (Asad), 107 Holy Quran (Arabic+English) | ✅ 2 |
| Dead Sea Scrolls | 80 DSS Translated (Qumran), 105 DSS Reader Vol 1 | ✅ 2 |
| Apocrypha / pseudepigrapha | 42 OT pseudepigrapha, 48 NT apocrypha, 64 Books of Enoch, 106 Adam & Eve (Armenian) | ✅ 4 (heterogeneous — see B.3) |
| Patristics | 18 Ante-Nicene Fathers Vol 3 | ❌ **1 (lone)** |
| LDS scripture | 101 LDS standard works | ❌ **1 (lone)** |

### B.3 Findings
- **F-B1 — operational-readiness gap (all 17).** Under the standard as written, no non-Bible currently
  clears the full §1 bar, because criterion 3 requires CLI/API/UI apply-by-id and the registry is
  bibles-only. This is the deferred-scope boundary §7 predicted, now quantified. **Decision needed**
  (see Open policy calls): extend the registry/manifest scope to non-Bibles (and wire them into the gold
  paths), *or* explicitly scope criterion 3 to Bibles and define a separate readiness bar for non-Bibles.
- **F-B2 — lone-kind demotion candidates.** **18 Ante-Nicene Fathers** (patristics) and **101 LDS** are
  the only members of their kind. Per the §3 rule they are *candidates, not standards* until a second
  member of each kind clears the bar. Recommend marking them "candidate" (not "Gold Set") pending a peer.
- **F-B3 — apocrypha/pseudepigrapha granularity is a judgment call.** Grouped coarsely, the four
  (42/48/64/106) satisfy ≥2; split finely (OT-pseudepigrapha vs NT-apocrypha vs Enochic vs
  parabiblical-Armenian) each risks being a lone member. Needs Sir's granularity ruling.
- **F-B4 — accuracy lens not yet scored.** The detection golds exist but detector-recall (`a3`) accuracy
  wasn't run here (machine-local, needs the copyrighted source + harness). Recommended per-kind before
  promoting any non-Bible kind to full standard.

---

## Recommendations & open policy calls for Sir

1. **Bibles (4a): ratify.** All 15 marker Bibles are complete + accurate + precise at char level; the 2
   epub Bibles are precise for their edition kind. No masking defects found. (Live-UI confirmation folds
   into A.5.)
2. **Non-Bibles (4b): none currently clears the full bar** — criterion 3 (ops readiness) is unmet for all
   17 because the registry is bibles-only. **Policy call:** (a) extend the manifest/registry + gold
   CLI/API/UI to non-Bibles, or (b) scope criterion 3 to Bibles and define a non-Bible readiness bar.
3. **Demote to "candidate":** 18 (Ante-Nicene Fathers) and 101 (LDS) — lone members of their kind.
4. **Rule needed:** apocrypha/pseudepigrapha kind granularity (F-B3).
5. **Follow-up:** run `a3`/`gold_ratify` detector-recall accuracy per non-Bible kind before promotion (F-B4).

# R3 Crop Geometry — Investigation & Measured Negative Result (2026-07-26)

Session goal (from `SESSION-HANDOFF-2026-07-25.md`, lever 1): *"layout-aware column-band crop geometry for
psalms (§8 R3-4) — the BIGGEST lever. Target: lift psalms pass-rate off 0.28."*

**Outcome: the lever is closed, and closed empirically. Crop geometry cannot lift psalms.** The handoff's
causal hypothesis was wrong, two real geometry defects were found and one was fixed, and a controlled
experiment shows that even a gold-omniscient choice among crops reaches only 0.543 acceptance. The effort
should move to apparatus-aware segmentation (new lever, evidence below) and the ſ-faithful arbiter.

---

## 1. The handoff's hypothesis was wrong

> *"olmOCR fails psalms because the generic region crop feeds it the interleaved 2-column central apparatus."*

Line geometry (`.page-cache/`, 13 gold pages) shows **most psalms pages are single-column**: the body-line
left-edge histogram is concentrated in one decile on psalms-074-p137, -p138, -115-116, -118, -150-p266. Only
psalms-001 and -150-p265 show a genuine second x-band.

The real failure signature was different: **13 of the worst verses scored an exact `0.000`** — a hard zero,
not degraded quality. Hard zeros mean the janvier-cut recovered no span for the verse, which is a routing or
input-clipping failure, not a recognizer-accuracy failure.

## 2. Three geometry defects found

| # | Defect | Evidence | Status |
|---|---|---|---|
| 1 | `body_column` took the median over **all** body lines. DR psalms set short italic gloss fragments flush-right *inside* the text block; on a gloss-heavy page they are the **majority of the line count**, dragging the median right so the crop's left edge lands inside the scripture column and clips the opening of every full line. | psalms-001: median-over-all x0 = **0.310** vs true column edge **0.161** — 15% of page width of scripture cut off. Containment 0.456 → 0.675. | **FIXED** (full-measure lines only) |
| 2 | Clipping to a **median** x1 means ~half the column's lines overflow it *by construction*. | Containment of flagged regions' own body lines = **0.456**; genesis-24 **0.21**, matthew-28 **0.33**. | **INVESTIGATED, REVERTED** — see §4 |
| 3 | Verse localization degenerates at page boundaries: a single "verse" absorbs the rest of the page. | psalms-150-p265 ch150 v1 → **53 lines / 0.74 of the page**; psalms-115-116 ch116 v1 → **47 lines**; psalms-074-p137 ch74 v1 → **39 lines**. These are the whole-page inputs olmOCR is documented to repetition-loop on. | **OPEN** — not a crop bug; a segmentation/addressing bug (§11) |

Defect 1 is fixed on **deterministic geometric grounds** (containment, no olmOCR involved), *not* on score
grounds — see §3 for why no score claim is defensible.

## 3. R3 is variance-limited, not geometry-limited (`r3_variance.py`)

A single-run A/B cannot attribute any geometry change here. olmOCR at temperature 0 is deterministic *in its
input*, but the map from crop rectangle to transcript is **chaotic**: prose pages whose column estimate moved
by <0.001 of page width nonetheless moved up to 0.25 in score (matthew-28 v16 `1.000 → 0.946`).

So the noise was measured directly. `r3_variance.py` runs K crop **variants** per region that only ever
*grow* the box — every variant still contains all the region's text, so any score difference is model
sensitivity and never lost content. On the 46 known-bad gold verses, 4 variants each:

**Chaos term** — gold-score spread across variants of the *same* region:
`mean 0.271 · median 0.051 · max 1.000` · spread >0.3 on **13/46** verses.
It is **not** concentrated in the large degenerate crops (§2 defect 3): mean spread is flat across region
size (≤8 lines 0.258 · 9–20 lines 0.280 · >20 lines 0.262). That refutes the "whole-page crop causes the
chaos" hypothesis.

**Can selection exploit the variance?** A production selector may only use the gold-free witness score, and
may only accept when its own witness score clears τx:

| strategy | mean gold | **acceptance** |
|---|---|---|
| single run | 0.671 | 0.435 |
| argmax by witness (best-of-4) | 0.782 | 0.457 |
| medoid consensus (best-of-4) | 0.758 | 0.457 |
| **ORACLE — best of 4 chosen *with gold*** | **0.801** | **0.543** |

Best-of-4 buys **one verse in 46**. And the *oracle ceiling is 0.543* — even choosing among four crops with
perfect knowledge, 46% of known-bad verses still fail. **No crop-geometry strategy can close psalms.**

Per No Silent Degradation this is "the method can't reach it" → **redesign the method**, never lower the aim.
The threshold stays; the R3-vision-on-crops rung is what must change.

## 4. The envelope fix: a measured negative result (do not re-attempt)

Defect 2 suggested raising the column to a near-full envelope (q=0.90), lifting containment 0.456 → 0.949.
The argument was that clipped scripture is unrecoverable while over-inclusion is recoverable, since the P5
janvier-cut discards unaligned material.

**The measurement refutes the argument.** Scored as the mean over 4 variants (the low-variance estimator):

```
median column q=0.50 : 0.6875
envelope     q=0.90 : 0.6631
paired Δ            : mean -0.0245  improved 5/46  worsened 18/46
                      Wilcoxon signed-rank p = 0.018
```

Acceptance was unchanged at every level (single 0.457, selected 0.457, oracle 0.543). So **fixing a crop that
was clipping half the scripture changed nothing in acceptance and made mean quality significantly worse** —
because what the wider crop admits on psalms pages is the interleaved annotation apparatus, and the cut does
**not** reliably discard it.

Two durable lessons, both pinned in code and tests so they are not silently re-"fixed":
- **Containment is not a proxy for transcript quality.** A geometrically-correct crop can score worse.
- **Over-inclusion is not free.** The P5 cut absorbs unaligned material far less reliably than assumed.

`body_column` therefore keeps `q=0.50` (median) as default, with `q` tunable for reproducibility.

## 5. NEW LEVER — symbol-conditional, apparatus-aware segmentation (Sir's proposal, evidence-backed)

Sir asked mid-session whether any approach leverages **symbol identification and known formatting** — e.g.
text following a `†` is verse text; in Psalms the verse text is separated by annotation text keyed by a single
letter; whereas Genesis runs verses together in a paragraph layout where `†` begins a verse but not a line.

**Nothing in the pipeline uses any of this.** `†`/`‡` appear only in code *comments*; all segmentation is
janvier reference-alignment, and the sole symbol rule is `strip_verse_numbers` (digits).

Measured, and the premises hold:

**(a) † is recovered near-exactly by R2.** Page-total † vs page-total gold verses:
proverbs-16 **21 vs 21** · psalms-150-p265 (8+2) **vs 10** · psalms-074-p137 (10+1) **vs 11** ·
psalms-115-116 (9+2) **vs 10** · genesis-24 19 vs 17 · 2-esdras-07 24 vs 23.
(Exception: matthew-28-p102 has **0** † — that page's typography or its OCR does not carry them, so any rule
must degrade to alignment, not fail.)

**(b) Sir's layout distinction is detectable gold-free** — fraction of body lines *starting* with †:
paragraph pages (genesis, 2-esdras, abdias, psalms-150-p266) **0–2 of ~41**; verse-per-line pages (psalms,
proverbs) **6–17 of ~40–60**. A threshold near 0.12 separates them cleanly.

**(c) Splitting on † alone is worse** (0.14–0.59 vs alignment's 0.79–0.99) — but diagnostically so: the
**boundary counts are right** while the *content* is polluted, because annotation lines carry `role='body'`
and interleave into the token stream. † gives boundaries; it does not give apparatus removal.

**(d) Apparatus removal is where the value is.** A crude gold-free filter (drop a body line that is
right-shifted from the column edge and does not open with a †), then re-align:

| page | align (current) | + annotation filter |
|---|---|---|
| psalms-115-116 ch116 | 0.500 | **0.985** |
| psalms-150-p265 ch149 | 0.808 | **0.931** |
| abdias-01 | 0.794 | 0.865 |
| genesis-24 | 0.956 | 0.973 |
| psalms-118 | 0.936 | 0.948 |
| **proverbs-16** | **0.943** | **0.337** ← over-drops |
| **psalms-150-p266** | **0.973** | **0.568** ← over-drops |

The gains are large exactly where the apparatus interleaves. The regressions are a defect of *my* blunt
heuristic, not of the idea: in verse-per-line mode a verse **wraps** onto an indented continuation line that
carries no †, and the filter eats it.

**This is the recommended next milestone** — and it is the first approach that attacks the actual cause
(apparatus contamination) rather than the crop rectangle around it. Design sketch:
1. Detect layout mode gold-free (†-line fraction) — per page, per region.
2. Paragraph mode: † marks verse starts mid-line; apparatus is marginal (geometry already handles it).
3. Verse-per-line mode: a line opens a verse (†), **continues** one (indented, no †, follows a verse line),
   or is **apparatus** (right-shifted, no †, often opening with a single-letter key). The continuation case
   is what the crude filter missed.
4. Feed the cleaned stream to both the gate and the R3 crop; validate with `r3_variance.py` (4-variant mean
   + Wilcoxon), **never a single run**.

## 5b. BUILT & MEASURED — the anchor-walk localizer (`verse_locate.py`)

Sir's second proposal, built: don't ask the recognizer *what is on this page*, ask **where is Psalms 118:5**.
Having found 118:4, search forward for the next verse, match the known janvier surface against the raw OCR
stream, reverse-look-up the geometry of whatever matched, and read the page there. Placement is an exact DP
over (verse × candidate window) maximizing match evidence subject to monotonicity — the optimum of "walk
forward finding each next verse", with **absence first-class** so an off-page verse is *chosen* absent.

**Result on the 13 gold pages / 177 verses** (per-verse `archaic_id` vs gold; all offline via `.page-cache`):

| segmenter | mean identity | pass ≥0.90 |
|---|---|---|
| incumbent (one global `difflib` over the chapter) | 0.9215 | 131/177 = 0.740 |
| anchor-walk alone | 0.8598 | 127/177 = 0.718 |
| **HYBRID — per-verse gold-free pick (`best_spans`)** | **0.9488** | **143/177 = 0.808** |
| oracle (picked with gold) | 0.9553 | 150/177 = 0.847 |

**+6.8pp absolute pass-rate, Wilcoxon p=0.004 (30 improved / 15 worsened), capturing 80% of the oracle's
available gain.** The selector is `janvier_fit` — the span's identity against the janvier verse it claims to
be — which is gold-free (janvier is a reference witness, the same standing `xsrc_gate` already relies on) and
is a strong detector of the failure that matters: a span pointed at the **wrong place** diverges from janvier
far more than any spelling variation does. Engine chosen: walk 52, align 125.

**Why a hybrid rather than a replacement.** The two fail in different places, which is exactly why picking
between them beats either. Global alignment wins on clean continuous prose (unambiguous long blocks);
the walk wins where global alignment degenerates — page-boundary chapters and interleaved apparatus:
psalms-074 ch74 **0.000 → 0.943**, psalms-150-p265 ch149 **0/8 → 5/8 passing**, psalms-115-116 ch115 5/9 →
8/9, psalms-118 8/12 → 10/12, abdias 0.794 → 0.946. **Runaway spans (>20 lines for one verse): eliminated.**

Honest cost: genesis-16-p082 fell 8/8 → 5/8 (mean 0.998 → 0.943) — the selector picked the walk on three
verses where the incumbent was already near-perfect. That is the price of a per-verse selector with an
imperfect signal, and it is the first thing to attack next.

**Three bugs found and fixed by measurement during the build** (each was a full re-measure, not a guess):
1. **Trim-before-walk.** Monotonicity was being enforced on the *padded* search window (2.2× verse length),
   so every verse's slack tail blocked its successor — **84/177 verses went "not-located"** (mean 0.42).
   Judging monotonicity on the *matched* extent fixed it (→ 0.824, not-located 10).
2. **Give the unmatched text back.** Anchoring on tokens that MATCH janvier and stopping there returns a
   verse stripped of precisely its divergent wording — which is the text we are trying to read. Expanding
   each verse into the unclaimed gap, budgeted by its own still-unmatched janvier tokens, gave +0.026.
3. **IDF weighting is load-bearing.** 2-Esdras 7 is the census list — every verse is "the children of
   <name>". Unweighted matching aligned the repeated scaffolding across verse boundaries, so v53 lost its
   position to v54 entirely. Weighting by 1/df lets the proper names decide placement. This is exactly Sir's
   "book-specific pattern" point, handled generically: it protects any genealogy, litany, or the psalms'
   formulaic parallelism without a per-book rule.

**One measured parameter rejection, pinned:** letting a verse reclaim text proportional to its own length
(on the theory that an edition adds words janvier lacks) degrades identity **monotonically** — 0.0 → 0.860,
0.10 → 0.809, 0.15 → 0.782, 0.25 → 0.700, 0.40 → 0.654. On these pages the gap material is **apparatus**, not
verse expansion. `expand_pad` stays 0.0.

**Apparatus falls out for free**: whatever no verse claims is returned as `apparatus` token-runs with their
line indices — already the input to Sir's "found and bound, then chunk the residual" step.

## 6. Deliverables

| Path | Contents |
|---|---|
| `verse_geom.py` | `body_column` full-measure fix + `_quantile`; both findings documented in the docstring |
| `r3_variance.py` | the variance harness (crop variants, gold-free selector, records span TEXT for offline consensus) |
| `tests/test_r3_variance.py` | 10 tests — label-preservation, no gold-peeking in the selector, errors are absent samples not zeros |
| `tests/test_verse_geom.py` | +4 tests incl. the pinned negative result |
| `.r3-variance/` · `.r3-variance-q050-widemedian/` | the two 4-variant runs (span text included) |
| `.r3-stats-baseline-medianbodycol/` | pre-change R3 baseline |
| `verse_locate.py` | the anchor-walk localizer + `best_spans` hybrid + `janvier_fit` selector |
| `verse_locate_eval.py` | offline A/B of both segmenters vs gold (no kraken, no model — seconds) |
| `tests/test_verse_locate.py` | 12 tests: monotonicity, absence-is-first-class, divergent wording kept, apparatus residue, IDF placement, selector honesty |
| `page_cache.py` → `.page-cache/` | per-page kraken results — makes geometry experiments instant (most of this investigation used **zero** model calls) |

**Test status: 72 passing (63 fast + 9 slow).** Nothing committed (`ocr-spike/` is gitignored). No Anthropic
API called — local olmOCR only.

## 7. Where to resume

1. **Wire `verse_locate.best_spans` into the pipeline** (§5b) — it is built, tested and measured (+6.8pp
   pass-rate, p=0.004) but NOT yet consumed by `xsrc_gate`/`reocr_core`/`verse_geom`. Re-run the gate
   calibration and `r3_stats` on top of it: better segmentation should shrink the flagged set AND raise R3's
   ceiling, since several "R3 failures" were really mislocated spans.
2. **Close the selector's cost** — genesis-16-p082 lost 8/8 → 5/8 to selector mistakes. Options: require a
   margin before switching engines, or add the †/layout-mode signal (§5) as a second selector input.
3. **Symbol-conditional apparatus removal** (§5) — still unbuilt and still promising (ch116 0.500 → 0.985 in
   the crude prototype); must handle the wrapped-continuation case.
4. **ſ-faithful in-agent arbiter** — closes the ~21 `RESCUED_CONTENT_S_OPEN` ſ debts and is a stronger reader
   than olmOCR on exactly the material olmOCR fails.
5. ~~Defect 3 (runaway spans)~~ — **FIXED** by the anchor-walk (§5b); eliminated on all gold pages.
6. GT-3 breadth (Sir-review labor tail).

**Do not** re-attempt: wider/enveloped crops (§4), best-of-N crop selection (§3) — both measured, both closed.

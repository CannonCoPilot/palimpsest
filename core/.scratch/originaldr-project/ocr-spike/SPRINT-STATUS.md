# OriginalDR reOCR — Full-Completion Sprint Tracker

> **RESUME (state as of 2026-07-27, post-M12 sprint).** Tiers **A, B, C1 CLOSED**; **C2 and D OPEN**.
> Start at **C2** (ſ-faithful in-agent arbiter, ~21 debts in `.r3-stats/_open_ledger.json`, IN-SESSION vision,
> NO paid API), then **D** (REP-2/4/5 · production audit · report artifact · COMPLETENESS REVIEW).
> Tier plan + gates: `REOCR-MASTER-PLAN-2026-07-22.md` §12.5 (rev 4) and its SPRINT RESULT block.
>
> **Read these three facts before touching any number:**
> 1. The reference is `gold_grid.py` (gold cut at the PRINTED verse markers). Every pre-2026-07-27 per-verse
>    figure was measured on an aligner-cut grid and is NOT comparable. `--aligner-grid` reproduces the legacy.
> 2. Current: segmentation hybrid **0.9629 / 143-of-165, worsened 0** · gate **recall 1.000 @ τx=0.90, 24%
>    escalation** · R3 content pass **0→63.3%**, 0 of 21 accepted verses worse than R2 · OPEN ledger **55,
>    blocks the deliverable**.
> 3. Tests: `../ocr-venv/bin/python -m pytest tests/ -q` → **98 pass**. Plus six module self-checks
>    (`xsrc_gate verse_geom verse_seg r3_route verse_locate gold_grid`) — run after any edit.
>
> **Do not re-attempt** (all measured, all pinned in code+tests): wider/enveloped crops · best-of-N crop
> selection · containment as a quality proxy · hybrid switching margin · trailing †/‡ trim · geometric
> apparatus removal · anchors rewriting spans. See the scratchpad's PINNED NEGATIVES.
>
> **HOLD commit/push for Sir OK.** Sir is doing GT-3 calls/corrections in parallel — re-read `ground-truth/`
> before scoring, his edits may have landed.

Sir authorized (2026-07-19) driving the ENTIRE remaining program to completion using my own
visual transcription/remediation; he reviews GT AFTER all work is done. S12–S15 CONFIRMED DROPPED.
Authoritative spec: `SIR-DIRECTIVE-2026-07-19.md`. Agent brief: `MATTER-AGENT-BRIEF.md`.

## ✅ M12 SPRINT — TIER A DONE, TIER B DONE, C1 DONE (2026-07-27)
**89 fast tests green** (+4), all self-checks pass.

### TIER A1 — verse numbers recovered corpus-wide, and the honest limit on using them
`build_verse_numbers.py` caches gutter reads to `.verse-numbers/` (olmOCR, 372s for 14 pages, cached
thereafter). **145 verse openings → 58 numbers read (40%) → 45 ACCEPTED (31%)** after monotonicity + chapter
vetting. Recovery is regime-dependent exactly as the grammar predicts: psalms/genesis pages give 60-88%,
while **abdias (0/11) and proverbs (0/21) give nothing because those pages print no numbers** — the module
reports absence instead of inventing. matthew gave 0 crops because `verse_opening_lines` keys on the dagger;
the NT numeral regime needs its own opening detector (its numbers already survive in the OCR, so this is a
completeness gap, not a loss).
- **⚠ ANCHORS MUST NOT REWRITE SPANS (measured, pinned).** Using accepted anchors to correct verse starts made
  things WORSE: known-bad **24 → 45**. A lone anchor moves ONE verse's start without moving its neighbour's,
  leaving the two spans mutually inconsistent. The anchor is right about its own verse and SILENT about the
  rest; using it for spans needs a joint re-solve (all verses re-placed subject to all anchors at once), which
  is not built. Anchors therefore drive the ALARM only and do not touch the output.

### TIER A2 — recall=1 RESTORED, and the alarm it was built for turned out not to be needed
Built alarm 5 (`xsrc_gate.anchor_disagreement`): a span that contradicts its own printed verse number — the
one signal about IDENTITY rather than quality, invisible to all four content alarms. Then measured the target
case and found **the gate was right and the REFERENCE was wrong**: psalms-118 118:109's span is verbatim
janvier 118:109; `gold_grid` had handed v109 the text of v103 on that under-marked page.
- **FIX AT THE INSTRUMENT:** `gold_grid` now WITHDRAWS any label scoring <0.35 against janvier. The gold is my
  own transcription, so a segment reading as a different verse is a labelling error, not a bad verse; the
  verse is reported unbuilt with a reason rather than published wrong. 4 labels withdrawn corpus-wide.
- **RESULT — the §7 gate gate is MET again:** four alarms, fair reference, **recall 1.000 at τx=0.90 → 24%
  escalation, 18 false alarms** (was 33%/13 on the biased reference, and 26% with one verse missed).
- **ALARM 5 IS KEPT BUT DEFAULTED OFF, on measurement:** with it, recall 1.000 @ **40% escalation, 44 false
  alarms** — 16 points of escalation for zero additional catches, because its precision is bounded by 31%
  anchor recovery and its firings are dominated by sparse anchors, not real disagreements. The failure class
  is real and this gold set contains no instance of it; turn it on when recovery improves.
- Fair-grid segmentation after the instrument fix: **hybrid 0.9629 mean, 143/165 pass, oracle == hybrid,
  worsened 0, p<0.00001**.

### TIER B — regime coverage across ALL SIX curated sources (33 pages, live kraken)

    ot-dagger 20 · nt-numeral 7 · no-scripture 3 · UNMATCHED 3 = 9.1%
    S1 {nt-numeral 3, ot-dagger 6} · S3 {ot-dagger 6} · S4 {nt-numeral 3}
    S6 {nt-numeral 1, no-scripture 1, unmatched 1} · S8 {ot-dagger 1, no-scripture 1, unmatched 1}
    S9 {ot-dagger 7, no-scripture 1, unmatched 1}

**THE NT QUESTION IS ANSWERED WITH A NUMBER: the numeral regime is NOT S1/Matthew-specific — it appears in
S1, S4 and S6, on 7 of 33 sampled pages.** So a regime detected on one book does extend across editions, which
is the property the grammar was designed for. **9.1% unmatched is the honest coverage gap** — the sweep
reports it rather than forcing those pages into the nearest regime, which is exactly the signal Sir asked for.
`no-scripture` fired on 3 pages, confirming that treatise/matter pages are recognised as carrying no verse
text instead of having verses forced onto them. Cached in `.regime-sweep/` (re-runs free).

### TIER C1 — multi-chapter pages (§13 Q5, colossians-3)
`block_grammar.chapter_ranges()` reads chapter headings (`CHAP. IIII`, roman or arabic) and returns per-chapter
line ranges; `verse_locate.best_spans(..., line_range=)` honours them. `verse_seg.segment`'s documented
contract ("split the body by chapter first and call once per chapter") had NO caller honouring it, so on a
straddling page every verse of both chapters competed for every position — the runaway the walk exists to
prevent, reintroduced at page level. Now available; the colossians-3 ADDR-2 page verification remains.

### NOT REACHED THIS SPRINT
**C2** ſ-faithful arbiter (~21 ſ-surface debts) · **D** REP-2/4/5 + production audit + report artifact +
completeness review. Both are unblocked and unchanged in scope.

## ▶ NEXT SPRINT — AUTONOMOUS TARGETS (queued 2026-07-27, awaiting Sir's go)
Full tiering + gates in `REOCR-MASTER-PLAN-2026-07-22.md` §12.5 (rev 4). Ordered by dependency, each tier
gated so a failure ALERTS for redesign rather than being absorbed.

| tier | work | gate | risk |
|---|---|---|---|
| **A1** | wire `verse_numbers.recover` → `block_grammar.dispatch` → segmenters (self-labelling anchors) | psalms detect as `psalm-numbered`; fair-grid mean + pass reported | low — parts built & tested |
| **A2** | **FIFTH ALARM**: span disagrees with its own PRINTED verse number | recall=1 restored on the fair reference, escalation cost reported | med — may need redesign; ALERTs if so |
| **B1-3** | regime breadth across 6 curated sources × layout modes (supersedes SEG-1/2) | every source×mode detects a regime or is `unmatched` WITH a reason; **NT uniformity answered with a number** | med — unknown unknowns are the point |
| **C1** | §13 Q5 colossians-3: ADDR-2 verify + chapter-split multi-chapter pages | colossians-3 unblocked or evidenced | low |
| **C2** | ſ-faithful in-agent arbiter (~21 ſ-surface debts, in-session vision, NO paid API) | debts closed or itemised in the ledger | med |
| **D** | REP-2/4/5, production audit re-run, report artifact, COMPLETENESS REVIEW | curated-clean per-verse + guard + matter, rendered & verified | med — the deliverable |

**OUT OF SCOPE, flagged not attempted:** M4 recognizer retrain (REVIEW milestone; depends on GT that Tier B
may still change — retraining now risks doing it twice) · Sir-only GT calls (NT roman-lowercase `w` RATIFY;
summe-of-nt p29 re-review) · the full GT-3 matter/layout sweep (a bounded slice is in scope: abdias vv13-21 +
one gold per missing source S3/S4/S9).

**CARRIED OPEN INTO THE SPRINT:** gate recall <1 on the fair reference (1 known-bad invisible to all four
alarms) · 55-entry OPEN ledger blocking the deliverable · psalms-118 fair grid builds only 6 of 12 verses.

## ✅ M11 COMPOSABLE BLOCK GRAMMAR + VERSE-NUMBER RECOVERY + PAGE ALARM (2026-07-27)
Four new modules, **94 tests green** (15 new), all six module self-checks pass.

**`verse_numbers.py` — the numbers ARE recoverable (measured, olmOCR).** kraken's line polygons start at the
dagger, so the printed number sits outside the recognized line: across the 14 cached gold pages an `N †`
opening survives in the OCR exactly ONCE. It is not being stripped — it is never being read.
- **MEASURED CROP GEOMETRY:** a bare digit sliver recovered **0 of 7** openings on psalms-118 (a vision model
  given two glyphs and no context returns nothing). The same crops widened to carry the opening words
  recovered **5 of 7 read, 3 ACCEPTED** — `105`, `110`, `111`, all correct against the page image. The number
  is isolated afterwards from the token before the dagger; the context is what makes it legible at all.
- **GLYPH-CONFUSION IS SAFE HERE:** `III †` (111) and `1c9 †` (109) are read as numbers because POSITION
  already guarantees the token is one. The same substitutions on free text would corrupt words.
- **REFUSAL, NOT REPAIR:** two misreads (v2, v1 after v111) were REFUSED by the monotone check. A wrong verse
  number relabels a correct span with confidence — strictly worse than no number.

**`block_grammar.py` — regimes, not books.** 12 shared block types; markers classified as SELF-LABELLING
(`N.` NT-1582, `N †` psalm-numbered) or positional (bare †); geometry separates continuation from annotation
because they move in OPPOSITE directions (a wrap is indented FURTHER, an annotation LESS and to the full
measure) — the distinction the symbol-only prototype could not make, which is why it destroyed proverbs.
`compose()` folds lines into runs (a verse absorbs its wraps). `dispatch()` returns regime + schema.
- **`no-scripture` IS A FIRST-CLASS DETECTION**: ot2-1610 p216 sits INSIDE the Psalm 118 range and carries no
  verse text at all (the General Annotations treatise). The schema returns `segmenter: None` — do not attempt
  verse localization — instead of forcing verses onto a treatise and then reporting failure.
- **`unmatched` IS REPORTED, NEVER FORCED.** An unseen book either matches a regime or is flagged. This is the
  anti-over-fitting property: book identity is a PRIOR, never a key.
- Detected on the 14 gold pages: nt-numeral ×1, ot-dagger ×13 (psalms-118 is ot-dagger and NOT psalm-numbered
  **because its numbers were never OCR'd** — recovery must run BEFORE dispatch to unlock the stronger regime).

**`coverage_alarm.py` — the page-level "is the grammar failing?" signal.** Distinct in grain from `xsrc_gate`:
a per-verse gate cannot raise it, because a misfired grammar makes EVERY verse look individually bad and the
gate escalates all of them to a rung that cannot help. Reports RECALL (did we FIND the verses the references
place here → suspect the REGIME) and FIDELITY (does what we found READ like the chapter → suspect the
RECOGNIZER) **separately**, because they demand opposite remedies.
- **MULTI-REFERENCE, AND IT MATTERED IMMEDIATELY.** Scoring against one witness reported a correctly-read page
  as catastrophic: `s_dismas` gives 2-Esdras 7 **70** verses where `sabates_a`/`madueke_b` give **73**, so our
  v27 was compared to a different verse — **fidelity 0.064**. Consulting every source that covers the locus
  and keeping the best gives **0.889**, and the spread is reported as a REFERENCE-numbering divergence rather
  than blamed on the page. That is the most expensive class of false alarm, now designed out.
- **LOW-EVIDENCE GUARD:** a chapter with <3 verses on the page cannot support a page-level verdict (every page
  boundary would cry wolf); those verses stay gated per-verse. Result on the gold pages: **3 alarms of 17
  chapters** — 2 reference-numbering divergences, 1 genuine low-fidelity page.

**NOT YET RUN — the NT breadth question.** The instrument for "does the Matthew regime extend evenly across
the NT?" is now built (regime detector + `unmatched` reporting + the page alarm), but it has only been run on
the 14 gold pages. Running it across an NT page sample is the next step and requires no new machinery.

## ✅ M10 PSALM 118 VISUAL INSPECTION + GEOMETRIC APPARATUS VARIANTS (2026-07-27)
Rendered and read ot2-1610 pp215-236 directly (`.ps118-render/`, pdftoppm @130dpi — the PDF is 178MB, over
the 100MB text-extraction limit, so it must be rasterised first).

**THE FINDING THAT EXPLAINS THE psalms FAILURES — WE DELETE THE STRONGEST MARKER BY ASSUMPTION.**
Psalm 118 prints its verse number INLINE, immediately before the dagger: `14 † I am delighted...`,
`15 † I wil be exercised...`. Psalm 119 (p234) prints the number in the RIGHT MARGIN instead. **Either way the
DR body DOES number its verses — and the number is SELF-LABELLING**, the strongest marker class we have (an
off-by-one becomes impossible). But `layout.strip_verse_numbers` deletes exactly these tokens, documented on
the assertion that "the DR body marks verses with † / ‡, **never digits**" — which the page disproves. On the
psalms-118 gold page the numbers survive NOWHERE: not in the OCR body, not in the GT transcription.
**So every alarm is downstream of a body text that had its best boundary signal removed before any alarm ran.
That is why nothing caught 118:109: the gate is not weak there, it is blind to a signal we discarded.**

**PAGE STRUCTURE (Ps 118, p219) — the composable block vocabulary:**
  verse opening `N †`, inset from the measure · verse CONTINUATION indented FURTHER (hanging indent) ·
  ANNOTATION starting LEFT of the verse block and running the FULL measure, keyed by an italic letter ·
  STANZA HEADING (centred, short: "Gimel. Fulnes.") every 8 verses (the acrostic) · marginal notes BOTH sides.
p216 inside the Ps-118 range carries **NO scripture at all** — it is the "General Annotations" treatise
(Hebrew-letter tables, two-sided margins). p234 composes six block types on ONE page: section heading,
treatise, psalm heading, italic argument, rubric, drop-cap verse, annotations.

**GEOMETRIC APPARATUS VARIANTS — MEASURED, NO VARIANT BEATS THE BASELINE (negative result, pinned).**
`apparatus_geom.py` (6 variants: left-edge, right-edge, AND, OR, marker-anchored, marker-anchored +
continuation protection) scored end-to-end vs the FAIR gold by `apparatus_eval.py`:

    baseline 0.9561 (146/170) | v3 -0.0014 | v6 -0.0162 | v1/v5 -0.0383 | v2 -0.1199 | v4 -0.1573

Only 2 pages gain anything (psalms-115-116 +0.012, psalms-074-p138 +0.009). **The earlier prototype's promise
(ps115-116 ch116 0.500 -> 0.985) was measured against a much weaker baseline: the hybrid localizer has since
SUBSUMED apparatus handling** — `drop_apparatus` plus the walk's unclaimed-run residue already exclude
annotation text. Apparatus removal is therefore NOT the remaining lever; the missing verse NUMBERS are.

## ✅ M9 FAIR PER-VERSE GOLD GRID — the reference was the bug (2026-07-27)
Built `gold_grid.py`: the gold is now cut into verses at the PRINTED VERSE MARKERS instead of by
`verse_seg.segment` (the incumbent aligner). **Every M7/M8 per-verse number was measured on a grid the
incumbent produced**, which charged every boundary-word disagreement to the challenger.
- **THE DR PRINTS THREE DIFFERENT CONVENTIONS** — the first hard evidence for book-specific schemas:
  OT 1609/1610 (genesis/proverbs/psalms/2-esdras) marks verses with **†** (positional only); NT 1582
  (matthew) uses **arabic numerals "2."** which are **SELF-LABELLING** (the marker carries its own verse
  number, so an off-by-one is impossible); abdias prints **no marker** (one verse per line); psalms-118 is
  **under-marked** (4 † for 12 verses).
- **`†` IS OVERLOADED** — it opens a verse AND serves as an intra-verse annotation reference. Counting
  daggers therefore does NOT cut a page: one intra-verse dagger in genesis-24 shifted every label by one
  (mean janvier identity **0.051** — the "gold" was reading v15's text as v14's). Fix: boundaries come from
  the print (a verse never runs through a marker unremarked), LABELS come from a monotone DP that may merge
  consecutive pieces, scored by janvier identity. Janvier never decides WHERE a verse ends — only WHICH
  printed segment is which verse, and a wrong labelling is detectable because identity collapses.
- Three further defects found and fixed by the same self-check: a **discardable leading fragment** (a page
  opens mid-verse; forcing that tail onto the first tagged verse corrupted it — genesis 16:10 gold 0.67 while
  the gate saw xsrc **1.00**, i.e. the REFERENCE was wrong, not the OCR), **repair for missing markers**
  (matthew 28:17 ran into v18), and **continue-past-unrepairable** (psalms-118 built 5 of 12 when the loop
  stopped at the first failure). All 17 chapters now build LOSSLESS; inferred boundaries are COUNTED.

**RE-MEASUREMENT ON THE FAIR GRID — the hybrid never loses a verse:**

    reference grid          align mean   hybrid mean   hybrid pass   worsened   Wilcoxon
    aligner-cut (legacy)        0.9215        0.9548     147/177=.83         11    p=0.00007
    FAIR (printed markers)      0.8979        0.9480     143/169=.85    ****0****  p<0.00001

The oracle EQUALS the hybrid (selector captures **100%** of available gain). **The entire "honest cost" of
M7/M8 was an artifact of the reference.** genesis-16-p082, the headline regression (reported 8/8 → 6/8), is
on the fair grid **4/7 → 6/7, an IMPROVEMENT**. NEXT item 2 ("close the selector cost") is therefore CLOSED:
there is no cost to close.

**⚠ OPEN ALERT (No Silent Degradation) — recall is NOT 1.0 on the fair reference.** Recalibrated:
hybrid 24 known-bad, **23 caught at τx=0.90, 1 MISSED** (psalms-118 118:109, gold 0.0 but xsrc 0.985, conf
0.973 — invisible to all four alarms); align **5 MISSED**, including the genesis/proverbs verses previously
attributed to the hybrid as its "cost" — they are ALIGN's failures that the gate cannot see. The previously
reported "recall=1 @ 33% escalation" was partly an artifact of a reference that mislabelled which verses were
bad. This stays OPEN and blocks: the approach needs a fifth alarm, not a lowered bar.

## ✅ M9b LAYOUT FINGERPRINT — regime detection is GOLD-FREE and PREDICTIVE (2026-07-27)
`layout_profile.py` computes a per-page fingerprint from the recognizer's own output only (line text +
bboxes): dagger/numeral/star fractions, short-line fraction, indent spread, right-edge raggedness,
lines-per-verse. Measured on the 14 gold pages:
- **`right_ragged` separates prose from verse-per-line/poetic setting with a clean gap and NO overlap**:
  2-esdras 0.039, abdias 0.052, genesis 0.117–0.145 | psalms 0.44–0.72, proverbs 0.46. matthew is separated
  first by `numeral_frac` 0.42 (the NT regime).
- **The fingerprint PREDICTS which segmenter wins** — poetic pages take the anchor-walk 39% of the time and
  gain +0.072 mean; prose pages take it 22% and gain +0.047. So dispatching a page to a fitted schema is
  buildable on signals available at runtime, which is the prerequisite for the book-specific program.

## ✅ M8 HYBRID LOCALIZATION WIRED INTO PRODUCTION — flagged set −21%, recall STILL 1.0 (2026-07-27)
M7's `best_spans` was built, measured and then left unconsumed. It is now the production segmentation: ONE
localization per page feeds BOTH the gate and the crop geometry. **70 fast tests green (79 with slow).**
Four defects were found while wiring, each by measurement, each fixed and pinned:
- **DEFECT A — the walk EMITTED the alignment fold.** `verse_seg._afold` is documented "for ALIGNMENT only
  (never emitted)": it lowercases, folds ſ→s, v→u, j→i, y→i and collapses doubled letters. `locate` returned
  `" ".join(folded)` as the verse text — i.e. handed the diplomatic pipeline a modernized, case-flattened
  reading, destroying the exact surface this project exists to preserve. Now matches on the fold, emits the
  raw page tokens. **Effect: walk arm 0.8598 → 0.8760, HYBRID 0.9488 → 0.9548, passing 143 → 147, selector
  capture of the oracle gain 80% → 87%.**
- **DEFECT B — two coordinate systems under one key.** `verse_seg` publishes `tok_lo/tok_hi` in RAW body-token
  space; the walk published FOLDED indices (punctuation dropped). `best_spans` mixed both, so any geometry
  consumer would have read the wrong pixels. Both now publish RAW; `page_tokens` returns the bridge.
- **DEFECT C — geometry from the LOSING engine.** `verse_seg` emits no `lines`, so `best_spans`' fallback
  ("use the walk's lines if the winner has none") fired on EVERY align-sourced verse: winner's text, loser's
  pixels. Now resolved from the selected span's own extent. Nothing consumed it yet; regression-pinned.
- **DEFECT D — the walk was NOT REPRODUCIBLE.** `_seed_positions` ranked seeds with `sorted(SET, key=df)`;
  set-of-strings iteration is randomized per process (PEP 456) and a df-only key leaves ties broken by that
  randomness. Two identical sweeps of the same cache gave psalms-118 walk 0.811 vs 0.747. A result that will
  not reproduce cannot be held to a threshold. Fixed with a TOTAL order (tie-break on the token), verified
  identical across 4 PYTHONHASHSEEDs. **Fixing the seed would have hidden it, not removed it.**

**GATE RECALIBRATION (13 gold pages / 177 verses, both engines on IDENTICAL cached inputs):**

    engine    known-bad   recall @ τx=0.90   escalation   false-alarms
    align            46            1.000            33%             13
    hybrid           30            1.000            27%             18

**21 verses left the known-bad set because they were LOCALIZATION failures, not misreads** (several at a hard
0.000 — never located at all): abdias 1:2,1:3 · proverbs 16:9,10,12,25 · psalms-001 1:4,1:6 · psalms-074 73:23,
74:1,74:4 · psalms-115-116 115:2,3,6 · psalms-118 118:108,114 · psalms-150-p265 149:2,3,5,6,7. Recall stays 1.0
— **No Silent Degradation held: the flagged set shrank because fewer verses are bad, not because the bar moved.**
**HONEST COST — 5 verses newly known-bad** (genesis-16-p082 16:15,16 · proverbs 16:21,22 · psalms-001 1:5).
All 5 still ESCALATE, so none is laundered; R3 then re-read 16:15 → **1.00** and 16:16 → **0.984**.
`gate_calibrate.py` is now cache-aware (`cached_page`) and engine-switchable (`--engine=align|hybrid`), so the
two operating points are comparable on identical inputs instead of across two differently-built runs.

**MEASURED REJECTION, PINNED — a switching margin does NOT fix the cost.** The obvious remedy (make align the
default, require the walk to beat it by δ) was swept: δ=0.005–0.01 changes nothing, 0.02–0.05 is flat-to-worse,
0.10 loses a verse, 0.20 costs 11. The bad switches have fit gaps of **0.07–0.13** — far above any usable
margin — so no threshold separates them. `switch_margin` is kept as a parameter (default 0.0) with the sweep
recorded. Trailing †/‡ trimming was also measured: **exactly zero** rows change (archaic_id already folds
non-alphanumerics), so the dagger is not the cost driver either.

**R3 RE-RUN ON THE NEW FLAGGED SET (real olmOCR, 14 pages, 366s — was 448s):** R3's ceiling ROSE, exactly as
the M7 handoff predicted it would once mislocated spans stopped being routed as OCR failures.

    metric                                    align-gate (2026-07-25)   hybrid-gate (2026-07-27)
    flagged verses                                        65                        56
    truly-known-bad among them                            46                        30
    content pass-rate (≥0.90 vs gold) after R3       0 → 50%                   0 → 63.3%
    positive-lift verses                              26/46                     22/30
    accepted verses WORSE vs gold than R2                  0                         0

**THE SAFETY RESULT SURVIVES THE CHANGE: of 21 accepted verses, 0 are worse vs gold than R2** — every olmOCR
failure stayed OPEN. Gate precision vs gold 0.625; ſ-deficiency 45/56 (80%), the residual owed to the arbiter.
OPEN ledger holds 55 (30 xsrc<τx-after-R3, 21 ſ-surface, 4 no-geometry) and BLOCKS the deliverable.
Artifacts: `.gate-calibration.json` (hybrid) · `.gate-calibration-align.json` (baseline) ·
`.gate-calibration.json.pre-hybrid-20260727` · `.r3-stats/` · `.r3-stats.pre-hybrid-20260727/` ·
`.r3-stats-hybrid-run.log`.

**⚠️ FINDING THAT LIMITS EVERY NUMBER ABOVE — THE GOLD REFERENCE IS CUT BY THE INCUMBENT.** Per-verse gold is
built as `verse_seg.segment(gold_text, janvier)` — the ALIGNER. So align-vs-hybrid is scored on an
align-shaped grid, and boundary disagreements are charged to the challenger. Demonstrated on the headline cost
case: the gold cut puts "Eightie" at the END of genesis 16:15, but janvier's v16 begins "Eighty" — **the word
belongs to v16, the walk places it there, and is scored WORSE for being right.** Therefore the measured hybrid
gain is a **LOWER BOUND** and part of the 5-verse "cost" is a measurement artifact. The fair reference is
buildable: GT lines carry verse tags and the printed text carries † at each verse start (10 of 14 gold pages;
abdias and matthew-28 have none and must degrade to alignment). **This is now the top NEXT item — it changes
every number in this sprint, so it comes before further selector tuning.**

## ✅ M7 ANCHOR-WALK VERSE LOCALIZATION — +6.8pp PASS-RATE, GOLD-FREE (2026-07-26)
Built Sir's "find the verse on the page, then read it there" proposal. `verse_locate.py`: use janvier (which
tells us WHAT each verse says) to find WHERE it sits, via seeded local matching + an exact monotone DP over
(verse × candidate window), then reverse-look-up the geometry. **72 tests green (63 fast + 9 slow).**
- **RESULT (13 gold pages, 177 verses, per-verse archaic_id vs gold, all offline via `.page-cache`):**
  incumbent global-align **0.9215 / 131 pass** · anchor-walk alone 0.8598 / 127 · **HYBRID `best_spans`
  (per-verse gold-free pick) 0.9488 / 143 pass = 0.808** · oracle (gold pick) 0.9553 / 150.
  **+6.8pp absolute pass-rate, Wilcoxon p=0.004 (30 improved / 15 worsened), 80% of the oracle's gain.**
- **Selector = `janvier_fit`** (span identity vs the janvier verse it claims to be) — gold-free, same standing
  as `xsrc_gate`'s witness. It cannot certify diplomatic fidelity but strongly detects a span pointed at the
  WRONG PLACE, which diverges from janvier far more than spelling variation does. Chosen: walk 52 / align 125.
- **HYBRID, not replacement — they fail in different places.** Global align wins on clean prose (long
  unambiguous blocks); the walk wins where align degenerates: psalms-074 ch74 **0.000→0.943**, psalms-150-p265
  ch149 **0/8→5/8 pass**, psalms-115-116 ch115 5/9→8/9, psalms-118 8/12→10/12, abdias 0.794→0.946.
  **RUNAWAY SPANS ELIMINATED** (M6 defect 3: the 53/47/39-line "verses" are gone).
- **HONEST COST:** genesis-16-p082 8/8→5/8 (0.998→0.943) — selector mistakes where the incumbent was already
  near-perfect. First thing to attack (require a switching margin, or add the †/layout-mode signal).
- **THREE BUGS FOUND BY MEASUREMENT during the build** (each a full re-measure, not a guess): (1) **trim
  BEFORE the walk** — monotonicity was enforced on the padded 2.2× search window so every verse blocked its
  successor, **84/177 not-located**, mean 0.42 → 0.824 once fixed; (2) **give the unmatched text back** —
  anchoring on MATCHED tokens and stopping there strips the verse of exactly its divergent wording (the text
  we want); expand into the unclaimed gap budgeted by still-unmatched janvier tokens (+0.026); (3) **IDF
  weighting is LOAD-BEARING** — 2-Esdras 7 is the census list ("the children of <name>"), unweighted matching
  aligned the scaffolding across verse boundaries and v53 lost its position to v54 entirely. This is Sir's
  "book-specific pattern" point solved GENERICALLY: it protects any genealogy/litany/psalmic parallelism with
  no per-book rule.
- **MEASURED PARAMETER REJECTION (pinned):** letting a verse reclaim text proportional to its own length
  (theory: editions ADD words janvier lacks) degrades identity MONOTONICALLY — 0.0→0.860, 0.10→0.809,
  0.15→0.782, 0.25→0.700, 0.40→0.654. The gap material is APPARATUS, not verse expansion. `expand_pad`=0.0.
- **APPARATUS FALLS OUT FREE:** unclaimed token runs are returned with their line indices — already the input
  to the "found and bound, then chunk the residual" step.
- **NOT YET WIRED:** `best_spans` is built/tested/measured but no consumer uses it. Next: wire into
  `xsrc_gate`/`reocr_core`/`verse_geom`, re-run gate calibration + `r3_stats` (better segmentation should
  shrink the flagged set AND raise R3's ceiling — several "R3 failures" were mislocated spans).

## ✅ M6 R3 CROP GEOMETRY — LEVER CLOSED BY MEASUREMENT (2026-07-26)
Drove handoff lever 1 ("layout-aware column-band crops for psalms — the BIGGEST lever") to a definitive
**negative result**, plus one real fix and a new evidence-backed lever. Full report:
`R3-GEOMETRY-VARIANCE-FINDINGS-2026-07-26.md`. **60 tests green (51 fast + 9 slow).**
- **The handoff's causal hypothesis was WRONG.** Psalms pages are mostly SINGLE-column (left-edge histograms);
  the real signature was 13 verses at an exact **0.000** — a hard zero (no span recovered), not degraded
  quality. Hypothesis refuted from line geometry before any code was written.
- **DEFECT 1 (FIXED, TDD):** `body_column` medianed over ALL body lines, but DR psalms set short italic gloss
  fragments flush-right INSIDE the text block, and they are the MAJORITY of the line count — dragging the
  left edge into the scripture column and clipping the opening of every full line (psalms-001 x0 **0.310 vs
  true 0.161**, 15% of page width of scripture cut off). Fixed to full-measure lines only. Containment
  0.456→0.675. Justified on DETERMINISTIC geometry, **not** on score (see below).
- **R3 IS VARIANCE-LIMITED, NOT GEOMETRY-LIMITED** (new harness `r3_variance.py`, 4 label-preserving crop
  variants that only GROW the box). Chaos term: gold-score spread across variants of the SAME region **mean
  0.271, max 1.0, >0.3 on 13/46**; FLAT across region size (refutes "whole-page crops cause the chaos").
  Selection: single-run accept 0.435 → best-of-4 argmax-by-witness 0.457 → medoid 0.457, **ORACLE (best of 4
  chosen WITH gold) 0.543**. Best-of-4 buys ONE verse in 46 and the oracle ceiling still fails 46%. **No crop
  strategy can close psalms** → No Silent Degradation: redesign the METHOD, threshold stays.
- **DEFECT 2 (INVESTIGATED → REVERTED, pinned negative result):** clipping to a MEDIAN x1 means half the
  lines overflow by construction (containment 0.456; genesis-24 0.21). Raising to a q=0.90 envelope lifts
  containment to **0.949** — and scored **WORSE**: 4-variant paired mean **0.6875→0.6631, 18 worsened vs 5
  improved, Wilcoxon p=0.018**, acceptance unchanged. The seductive argument ("over-inclusion is recoverable,
  the P5 cut discards unaligned material") is **empirically false** — the admitted material is the interleaved
  annotation apparatus and the cut does not discard it. Two durable lessons pinned in code + tests:
  **containment is NOT a proxy for quality**, and **over-inclusion is NOT free**.
- **DEFECT 3 (OPEN):** verse localization degenerates at page boundaries — psalms-150-p265 ch150 v1 absorbs
  **53 lines / 0.74 of the page**; ch116 v1 47 lines; ch74 v1 39 lines. A 53-line band is not a verse band.
- **NEW LEVER (Sir's proposal, measured & backed):** symbol-conditional, apparatus-aware segmentation.
  Nothing in the pipeline uses †/‡ (they appear only in COMMENTS); all segmentation is janvier alignment.
  (a) **† is recovered near-exactly** — proverbs 21 vs 21 †, psalms-150-p265 10 vs 10, psalms-074-p137 11 vs
  11 (matthew-28 has 0 † → any rule must degrade to alignment, not fail). (b) **Sir's layout distinction is
  gold-free detectable** — †-line fraction 0–2/41 (paragraph: genesis/2esdras/abdias) vs 6–17/40-60
  (verse-per-line: psalms/proverbs). (c) † alone is WORSE (boundaries right, content polluted — annotation
  lines are role='body' and interleave). (d) **Apparatus removal is where the value is**: a crude filter gave
  psalms-115-116 ch116 **0.500→0.985**, psalms-150-p265 ch149 0.808→0.931, genesis-24 0.956→0.973 — but
  over-drops on proverbs (0.943→0.337) because verses WRAP onto indented continuation lines carrying no †.
  That wrapped-continuation case is the design work to do.
- **DO NOT RE-ATTEMPT:** wider/enveloped crops; best-of-N crop selection. Both measured, both closed.
- **Methodology note for any future A/B here:** a single olmOCR run CANNOT resolve a geometry change (prose
  pages whose column moved <0.001 moved up to 0.25 in score). Use the 4-variant mean + Wilcoxon.

## ✅ M5 R3 PRODUCTIONIZATION — verse→crop geometry + load-once server + OPEN ledger + TDD (2026-07-25)
Drove the §8 R3 "STILL OWED" tail to a tested, end-to-end-validated finish (main-thread, autonomous). The gate
now ROUTES: flagged verse → pixel band → olmOCR re-read → re-score → terminal state → OPEN ledger. All new code
is TDD'd (pytest suite, **46 tests: 37 fast + 9 slow**, `ocr-venv` now carries pytest; `pytest.ini` isolates the
suite from the parent palimpsest xdist config).
- **CODE-REVIEW PASS (adversarial subagent, 2026-07-25) — 2 HIGH + 3 MED + 1 LOW found & FIXED, all regression-
  guarded.** Both HIGH were "report-success-while-degraded" gaps: **HIGH-1** `reocr_page` pre-resolved a single
  page-wide τx, forcing archaic 0.90 onto modern-fallback verses → silently under-escalated the [0.90,0.92)
  band; fixed to pass `taux=None` (axis-aware) through, matching `rescue_page`. (The `r3_stats` validation called
  the gate directly with axis-aware τx, so the reported numbers are unaffected.) **HIGH-2** one `transcribe()`
  failure in `rescue_flagged`'s region loop aborted the whole page — discarding already-scored regions AND
  dropping the failed region's verses with no ledger trace (MLXWorker timeout path is unconditional → live on
  any slow crop); fixed to contain per-region + ledger-OPEN + continue. **MED**: ledger provenance tracks the
  best attempt; `MLXWorker` RLock; `region_crops` single-column assumption documented. **LOW**: R3 temp PNGs →
  project-local `.r3-tmp`. Core logic (geometry mapping, P5 janvier-cut re-scoring, gold-free contract) SOUND.
- **`verse_geom.py` (NEW, §8 R3-4 crop geometry):** maps a flagged janvier verse → its body-line indices →
  union pixel bbox → fractional crop, reconstructed from a `reocr_page` result (no image re-seg). `verse_crops`
  (per-verse), `region_crops` (contiguous flagged verses → ONE body-column-clipped crop), `group_contiguous`,
  `body_column`. NO-SILENT-DEGRADATION guard: reconstructed body text must match stored `r2_body` or it RAISES;
  a verse that localizes but has no geometry is an explicit OPEN, never dropped. `verse_seg.segment` now emits
  `tok_lo/tok_hi` (raw-token extent per verse) — the bridge; additive, validated numbers unchanged.
- **`mlx_client.py` + `mlx_ocr_server.py` (NEW, §8 R3-1 load-once):** olmOCR loaded ONCE, served over stdin/
  stdout JSONL; reader-thread+queue gives timeout-safe reads; self-heals (respawn-on-death, one-shot retry);
  per-request ERROR raised (never a silent empty transcript). `mlx_ocr.py` split into `load_model`/`run`/
  `transcribe`. `reocr_r3._r3_mlx` uses the worker by default (`reload_per_call=True` = one-shot fallback).
- **`open_ledger.py` (NEW, §7 terminal / §8 R3-5):** the OPEN worklist — dedupes by locus, keeps the highest
  (still-sub-τx) score, unions rungs tried, BLOCKS the deliverable while non-empty. `reocr_batch` writes
  `_open_ledger.json` per run.
- **`r3_route.py` (NEW): the router** — gate scores + region crops → 1 olmOCR pass/region → **janvier-cut the R3
  blob** (P5 linchpin) → score verse span → terminal state. Two axes kept separate: CONTENT (xsrc, ſ-blind —
  what olmOCR lifts) vs ſ SURFACE (vs ſ-faithful R2 — olmOCR modernizes ſ). States: RESCUED /
  RESCUED_CONTENT_S_OPEN (ſ owed → arbiter) / OPEN.
- **Wiring:** `reocr_core.reocr_page` attaches per-line `bbox`; `reocr_batch(run_r3=True)` routes flagged verses
  via `r3_route.rescue_page` (verse-targeted, was whole-page), accumulates the OPEN ledger, shuts the worker.
- **CRITICAL FINDING (fixed):** first e2e scored 0/5 — a MEASUREMENT bug, not R3 failure. The crop spans a
  verse ± neighbours so olmOCR returns a multi-verse blob; comparing the blob to a single-verse ref craters to
  0.0. Fix = **janvier-cut the R3 output first** (the same P5 "cut both sides on one grid" the whole system
  rests on). Region crops (contiguous verses, body-column-clipped) beat per-verse (cleaner cuts, no margin bleed).
- **E2E VALIDATED (genesis-24, real olmOCR, region-based, 38s / one model load + 2 region crops):** the 5 gate-
  flagged verses `{12,27,28,29,30}` route correctly — **content RESCUED on 3/5 with real lift: v27 0.884→1.00,
  v28 0.777→0.967, v29 0.876→0.990**; all 3 are ſ-deficient (olmOCR drops ſ) → RESCUED_CONTENT_S_OPEN (ſ surface
  owed → Claude arbiter); v12/v30 stay OPEN (genuine cross-page fragments). OPEN ledger holds all 5, blocks the
  deliverable. **Nothing laundered** — content-recovery and ſ-surface debt reported separately.
- **STATISTICAL VALIDATION DONE (`r3_stats.py`, 13 gold pages, 65 flagged verses, real olmOCR, 448s):** measured
  the R3 content lift GOLD-ANCHORED (archaic_id vs gold — truth) AND gold-free (vs witness — production). On the
  46 truly-known-bad: **content pass-rate (≥0.90 vs gold) 0 → 50%**; olmOCR is HIGH-VARIANCE (bimodal): **prose
  R2 0.749→R3 0.862 (+0.113, 76% pass) vs psalms R2 0.734→R3 0.428 (−0.305, 28% pass)** — the 2-col apparatus
  wrecks generic olmOCR, dragging the raw mean to −0.114 (median +0.077, 26/46 gain). **THE SAFETY RESULT (No
  Silent Degradation, empirical): of 23 ACCEPTED verses, 0 are worse vs gold than R2** — every olmOCR failure
  stayed OPEN; the witness-based gate (psalms witnesses defective) laundered NOTHING. ſ-deficiency 52/65 (80%).
  Report: `R3-PRODUCTIONIZATION-REPORT-2026-07-25.md`. Gold-free witness Δ (−0.104) tracks gold Δ (−0.114) →
  proxy validated. Artifacts: `.r3-stats/`, `.gate-calibration.json` (177 verses, recall=1 @ τx0.90, 33% esc).
- **OPEN / next:** (1) **layout-aware crop geometry for psalms (R3-4, biggest lever)** — column-band crop per
  mode (the run pinpoints psalms as the failure; harness ready to prove any fix); (2) ſ arbiter rung
  (backend='claude') to close the 19 RESCUED_CONTENT_S_OPEN ſ-debts; (3) GT-3 breadth (labor tail, Sir-review).
  Files: `verse_geom.py`, `mlx_client.py`, `mlx_ocr_server.py`, `open_ledger.py`, `r3_route.py`, `r3_stats.py`, `tests/`.

## ✅ GT REVIEW TOOL FIXES + CORRECTIONS FOLDED (2026-07-23)
Sir reported two tool bugs + a design question while reviewing matter sections; all resolved:
- **Issue 3 (broken raster)** FIXED: `gt_review_server.py` `/raster` crashed with TypeError when `raster` was a
  LIST (multi-page sections store a list of paths) → broken-image icon. Now restricts the pre-rendered fast-path
  to actual `.png` strings and falls through to on-demand jp2→PNG render for all else. Verified: explication,
  argument-of-genesis, brief-recapitulation, summe-of-old-testament all render 200 PNG.
- **Issue 2 (multi-page sections)** DECIDED + BUILT — **Option A: show the whole section across ALL its pages,
  page-aligned.** `/raster?page=<pi>` renders any declared page (validated); `gt_review.html` stacks one labeled
  image per page and tags each body line with its `page`. Makes "not-on-page" obsolete. Verified: summe-of-nt
  serves p28 AND p29; undeclared page→404.
- **Corrections folded** (`gt_apply_corrections.py`, +No-Silent-Degradation guard): summe-of-nt applied the "to
  wit" edit but **DEFERRED L44–54** (all page 29, marked 'not-on-page' only because the old tool hid p29) as
  `needs_rereview` — NOT excluded (would have destroyed valid p29 content). signification + censure edits applied.
  books-of-nt was an empty submission (no-op). **Sir: re-review summe-of-nt p29 with the fixed tool (11 lines).**

## ✅ M5 GATE — CROSS-SOURCE ALARM WIRED + CALIBRATED (2026-07-23)
The §7 confidence gate was proven self-report-BLIND (conf recall=1 → 88% escalation; confident-wrong tail
40/40 uncaught by internal alarms). **FIXED:** built `xsrc_gate.py` (alarm 2 = R2 vs the reference-witness
cascade, janvier-cut, archaic-preeminent, GOLD-FREE), extended `gate_calibrate.py`, and wired it into
`reocr_core.reocr_page(locus=(book,chapter))` + `reocr_batch(locus_map=…)`.
- **Result:** mean xsrc known-bad **0.714** vs good **0.936** (separates; conf's gap was 0.008). FULL gate
  **recall=1 on all 43 known-bad at τx=0.90 → 34% escalation** (vs conf's 88%), 0 blind spots. Confident-wrong
  tail **40/40 caught**. E2E gold-free `reocr_page(genesis-24, locus=…)` recall **4/4** (vv27–30 + fragment v12).
- **Verified:** all self-checks PASS; calibrator reproduces identical numbers pre/post DRY refactor (calibrator
  + production share `xsrc_gate` — no drift). Independent re-derivation from `.gate-calibration.json` confirms.
- **R3-1 backend DONE (olmOCR-2 via MLX):** qwen3-vl:8b was thinking-locked/empty → replaced by **olmOCR-2-7B**
  (`mlx-community/olmOCR-2-7B-1025-bf16`) in an isolated `ocr-mlx-venv` (mlx-vlm 0.3.12 + transformers==5.1.0;
  5.2.0 has a Qwen2.5-VL video-processor bug). `mlx_ocr.py` ← subprocess ← `reocr_r3._r3_mlx` (default backend).
  **VALIDATED end-to-end: olmOCR-crop beats R2 on ALL 4 genesis-24 flagged verses** (archaic_id: R2 0.69–0.88 →
  R3 0.90–1.00). Loop on full pages → crop/bands fix it. **ſ finding:** olmOCR modernizes ſ on crops (content
  rung, not diplomatic-surface); ſ-faithful surface = Claude arbiter; `restore_long_s` = labeled ~90% utility.
- **GT-3 + axis-aware τx DONE (this connects Unit 2 → the gate):** modern-fallback τx **CALIBRATED** — the gate
  is now axis-aware (`xsrc_gate`: **archaic τx=0.90 / modern-fallback τx=0.92**). Confirmed on the first GT-3
  archaic-gap gold **`scripture-abdias-01`** (Abdias 1:1-12, archive-ot2-1610 p840; all 12 verses modern-axis, 3
  known-bad incl. 2 confident-wrong caught). Full calibration now 177 verses / 46 known-bad, recall=1 at 33%
  escalation. Abdias is live in the review tool for Sir.
- **OPEN / next:** (1) R3 productionization — verse→crop geometry (map flagged verse → pixel band via kraken
  bboxes) + `mlx_vlm.server` (load-once) + wire `run_r3=True`; (2) **GT-3 breadth (labor tail)** — abdias vv13-21
  (p841), S3/S4/S9 source-coverage gold (SIR-DIRECTIVE §2.1), matter/layout coverage. Draft via olmOCR content +
  Jarvis ſ-correction → push to the fixed review tool. Files: `xsrc_gate.py`, `gate_calibrate.py`, `reocr_core.py`,
  `reocr_r3.py`, `mlx_ocr.py`, `long_s_rule.py`, `ground-truth/scripture-abdias-01.json`.

## 🔄 MAIN-THREAD COMPLETION RUN 2026-07-21 (Sir: NO sub-agents; do ALL work here, in series, to FINAL)
Sir authorized a fresh 5h session to finish everything in the MAIN thread (no delegation, disregard spend).
Jarvis is doing all rendering + visual transcription directly (render jp2 → rband.py column bands → read → build GT).
**29/33 matter GT done.**
  1. ✅ table-of-epistles-nt → S8 pp773-776 DONE (matter-nt-table-of-epistles.json: 213 rows, 210 intervals, 356 ſ,
     core round-trips clean). Also hardened glyph_map (added ū→u macron; was only ũ). 2026-07-21.
  2. ✅ table-of-certaine-places DONE (matter-nt-table-of-certaine-places.json: 135 intervals = 22 book-headings
     + 110 corruption entries + title/subtitle/closing; 482 ſ; clean core). CORRECTION: it is NOT at S8 pp722-728
     (that's the Apocalypse argument) — it is the "A TABLE OF CERTAINE PLACES / HERETICAL CORRVPTIONS" appendix in
     **S1 archive-nt-1582 pp722-728** (S8 hi-res set lacks this appendix). p724 folded from existing matter-nt-table.
     S1 is a low-res 800px scan → italic w/vv below per-glyph threshold (flagged). 2026-07-21.
### ✅ COMPLETENESS GAPS DONE (2026-07-21): summe-and-partition +p17 tail (pages 15-17, RESOLVED);
  books-of-new-testament +p26-27 patristic catena (pts 3,4,5 + Augustine/Tertullian/Hierom/Vincentius/Baſil,
  pages 25-27, RESOLVED, 56 intervals). Both clean core round-trip.
### 📍 SECTION 5 LOCATED (continuance-of-church): it is "THE CONTINVANCE OF THE CHVRCH, AND RELIGION IN THE
  SIXTH AGE" — a LONG (~14pp) dense-italic apologetic treatise at **S1 archive-ot2-1610 pp988–~1001** (running
  header "CONTINVANCE OF THE / CHVRCH AND RELIGION" thru p1000; a genealogy/3rd-booke section follows by p1004;
  Historical Table = pp1077-1100). matter-ot2-backmatter.json already = its OPENING page (p988, header + treatise
  start, drop-cap S "SVCH is the prouidence…"). "Continuance of the Church" recurs at many S6 loci (6-age series)
  → that scatter caused the resume's 1961/1969-vs-941 confusion; the sixth-age back-matter one anchors at S1 p988.
  TODO: extend matter-ot2-backmatter with pp989-1001 (single wide column, roman/italic alternating). Not a quick win.
### ✅ DELIVERABLE SECURED (Sir chose "secure deliverable first", 2026-07-21):
  - **E5b**: matter_match_report.py enhanced — ~20-word WINDOW-grain PARA pool + interval-grain APPARATUS pool
    (score_para_windows / score_pools). Self-test GREEN. glyph_map hardened: ū→un, legend marks ⁘ ⊣ stripped.
  - **E**: matter_scoring_run.py scored all 30 matter GT × their testament's curated sources →
    matter-scoring-summary.json. Honest baseline: 102/105 located source-rows below 90% → reOCR-flagged
    (mirrors scripture: coverage-audit-verse.json = 6438 verses / 271 chapters all in shortfall).
  - **FINAL**: qc_audit.py all ran (scripture coverage). Matter completeness+scoring AUDIT ARTIFACT published:
    **https://claude.ai/code/artifact/47533001-7aa9-42cf-a944-f0f887004e67** (30 books, pools, OPEN items, log).
  - Build scripts durable in ocr-spike/.scratch/ (build_matter_audit_artifact.py, matter_scoring_run.py).
**REMAINING TRANSCRIPTION** (main-thread; per Sir's plan these come AFTER the secured deliverable; may end
  partial-but-honest — mark OPEN, never fake):
  3. particular-table → S6 pp2049-2068 (20pp alphabetical index; hi-res 5100px). **PARTIAL/OPEN**: pp2049-2051
     DONE (matter-ot2-particular-table.json: title + 2 intro notes + letter A Aaron→Aureola + letter B start
     Baal→Bleſſing, 55 entries, clean core). pp2052-2068 (rest of B→Z, tail LAVS DEO) REMAIN. NOTE recto/verso
     column shift: recto R col needs x~0.455 (else first chars clip). builder=.scratch/build_matter_ot2_particular_table.py
  4. ample-and-particular-table → S8 pp776-798 (HUGE alphabetical index; starts bottom of p776 after the rule)
  5. continuance-of-church → S6, RE-VERIFY location (grep 1961/1969 vs agent-at-941); long treatise, scope extent first.
Then: completeness-gaps (p17-tail, books-nt p26-27) → E5b (window-grain scoring) → E → F → FINAL audit + report V3.
(Original pre-/clear checkpoint preserved below.)

## ⏸ PRE-/CLEAR CHECKPOINT 2026-07-21 — resume via `.claude/context/.resume-prompt.md`
**28/31 matter GT done.** Agents BLOCKED: **monthly spend limit** hit (raise at claude.ai/settings/usage) + session limit.
Efficient agents (few-bands, write-to-file) work once unblocked — verified (censure/faults-escaped/etc. done lean ~27-33 tools).
**5 REMAINING** (all near-complete but died before writing — RETRY, exact pages, ⚡efficient, ONE agent each):
  1. table-of-epistles-nt → S8 pp773-776   2. table-of-certaine-places → S8 pp722-728 (="Table of Controversies")
  3. particular-table → S6 pp2050-2067 (was on final p2067)   4. ample-and-particular-table → S8 pp776-798 (HUGE; NO sub-split — /tmp collisions)
  5. continuance-of-church → S6, RE-VERIFY location (grep 1961/1969 vs agent-at-941); long treatise, scope extent first.
Then: completeness-gaps (p17-tail, books-nt p26-27) → E5b (window-grain scoring) → E → F → FINAL audit + report V3.

## Phases (efficient order)
- **D — matter-books** (~22 sections) + the NEW matter-INTERVAL coordinate system (paragraphs/rows) for
  mask-inventory + gold thresholds. Transcribe (agents, emit `intervals[]`), QC (localization/identity/
  placement/completeness), align/insert.
- **C — S9 Psalms remedial**: resolve localization/coord/accuracy causing broad S9-Psalms OCR failure.
- **F — stratified resample** per Inclusion Rules (all sources ≥1 page, all pages ≥2 sources, all books +
  matter represented); verify OCR (localization/coord/layout/accuracy); resolve blockers.
- **E — complete scoring**: extend gt_match_report to matter intervals (E5b) + all newly included/remediated
  pages; fold into build_reocr_report V3 html.
- **FINAL**: production audit (qc_audit all, curated+aligned+matter) → regen report Artifact → completeness review.

## Matter interval design (implemented in MATTER-AGENT-BRIEF.md)
`intervals[] = {idx, kind, text, lines[]}`; kind ∈ title_block/heading/subtitle/paragraph/table_row/
list_item/colophon_line. Coordinate `matter/<slug>/<idx>`. Scoring = align source OCR → GT intervals
(reuse align_coords.realign at interval grain), % intervals edit_ratio≥0.90 (E4/E5a analog). Agents emit
intervals from visible paragraph breaks (reliable). Existing 11 GT: derive/annotate intervals + scorer-validate.

## Matter section worklist (✅ have · ⏳ dispatched · ☐ todo · source)
### OT1 (S1 archive-ot1-1609, 1609 first ed.)
- ✅ Title Page · ✅ Approbatio · ✅ To the Right Wellbeloved (matter-ot1-preface)
- ☐ The Summe and Partition (front, ~p48) · ☐ The Summe of the Old Testament (front)
- ☐ Of Moyses (front, ~p18) · ☐ The Argument of Genesis (front, ~p19) · ☐ The Signification of the Markes (front, ~p20)
- ☐ A Brief Recapitulation (BACK, ~p1085-1135)
- (matter-ot1-colophon exists — verify which section it is)
### OT2 (S1 archive-ot2-1610, 1610; 1635-tagged → S6 jp2-S06)
- ✅ Title Page · ✅ Proemial Annotations (matter-ot2-preface-psalms) · ✅ Table of Epistles (matter-ot2-table-epistles)
- ☐ Approbatio (front) · ☐ Concerning Interpretation (front)
- ☐ Continuance of the Church (1635→S6, back) · ☐ An Historical Table (back) · ☐ A Particular Table / Chiefe Contents (1635→S6, back)
- ☐ Censura trium Theologorum (back) · ☐ Faults Escaped in the Printing (1635→S6, back) · ☐ Extraict du Privilege du Roi (1635→S6, back)
- (matter-ot2-backmatter exists — verify which section it is)
### NT (S8 jp2-S08 hires 1582 for 1582 sections)
- ✅ Title Page · ✅ Preface to the Reader (matter-nt-preface)
- ☐ The Censure and Approbation (front) · ☐ The Signification or Meaning (front) · ☐ The Summe of the New Testament (front) · ☐ The Books of the New Testament (front; verify vs matter-nt-table)
- ☐ The Explication of Certaine Words (back) · ☐ A Table of Certaine Places (back) · ☐ A Table of the Epistles (NT, back) · ☐ An Ample and Particular Table (back) · ☐ Faults Escaped in the Text (back)

## SESSION-LIMIT PACING (2026-07-20) — 2nd window exhausted, resets 5:50am Denver
Hit the session token limit AGAIN at cap 2 (~9 heavy agents/window ≈ 2M tok). Main-loop still works.
Windowed pace: ~8-9 matter agents per 5h window; ~16 sections left = ~2 more windows. Background waiter set
(~50min) to retry agents after reset. Recovery: concerning-interpretation WAS written (valid) before its stall;
brief-recapitulation NOT written → RETRY after reset (pages 1128-1131, distinct from p1132 colophon; header "OF IOB",
body "perſeuering conſtant in vertue…", ref "1.Tim.3"[content 2Tim3:12]).
**Matter GT done so far: 18/31.** Remaining: brief-recapitulation(retry) + OT2{historical-table p1077-1100,
censura, continuance/particular-table/faults-escaped/privilege-du-roi in S6 ~p2050-2140} + NT(9, locate first).
Non-agent TODO while blocked: E5b scorer pools (para vs apparatus split), p17-tail cleanup (render p17), F prep.
**E5b GRANULARITY FINDING (2026-07-20)**: matter-scorer FUNCTIONAL (flags reOCR: of-moyses/summe-of-OT vs S1 =
✗0%, honest baseline — raw matter OCR far from gold, like scripture). BUT paragraph-grain intervals are too COARSE
for the 0.90-per-interval bar (300-word paragraphs accumulate OCR error → always fail). For verse-comparable
%-threshold COHERENCE (Sir's ask), the E-phase must score at a finer grain: ~20-word WINDOW within each paragraph
(sentence-split is unreliable — abbreviation periods 'S.Aug. li.2.'). Keep paragraph intervals[] as the
inventory/localization unit; add window-grain scoring for the % metric. Apparatus pool (citation/gloss/marginalia)
scored COMBINED = E5b. matter_match_report.py: split SCORE_KINDS → PARA vs APP pools + window scoring (E phase).

## OT2 dispatch page-hints (located 2026-07-20)
- Approbatio → S1 archive-ot2-1610 front (~p2-14; DISPATCHED a9b9e4028d81d0799)
- Concerning Interpretation → S1 archive-ot2-1610 front (~p3-15; self-locate)
- An Historical Table → S1 archive-ot2-1610 BACK ~p1077-1100
- Censura trium Theologorum → S1 archive-ot2-1610 BACK ~p1030-1100 (near Historical Table)
- Particular Table / Chiefe Contents (1635) → S6 jp2-S06 ~p2050-2067
- Extraict du Privilege du Roi (1635) → S6 jp2-S06 ~p2071
- Faults Escaped in the Printing (1635) → S6 jp2-S06 ~p2090
- Continuance of the Church (1635) → S6 jp2-S06, self-locate in ~p2040-2140 region (or earlier; scattered)
- NT dispatch (S8 jp2-S08, 800pp; headers OCR poorly so hints are weak — self-locate in region):
  FRONT ~p2-40: Censure-and-Approbation (~p2), Signification-or-Meaning (~p8-30), Summe-of-NT (self-locate front),
  Books-of-NT (self-locate front). [Preface=matter-nt-preface, Title=matter-nt-title already have]
  BACK ~p760-800: Explication-of-Certaine-Words (~p765-799), Table-of-Certaine-Places (~back), Table-of-Epistles-NT
  (~back; distinct from OT2 table-epistles), Ample-and-Particular-Table (~p760-800, LARGE multi-page index/table),
  Faults-Escaped-in-the-Text (~back). NOTE verify Books-of-NT vs existing matter-nt-table (may be the same).

## ⏸ CHECKPOINT — PAUSED 2026-07-20 (session tokens 94%; Sir: interrupt/gather/checkpoint/wait)
**MATTER GT DONE: 22/31.** Both agents stopped cleanly. Resume = re-dispatch below at cap 2.
### 🔴 CRITICAL S6 DECODE FIX (discovered by privilege-du-roi agent)
`jp2_page.py`/PIL fails on EVERY S6 (jp2-S06) page ("broken data stream" — systematic PIL/decoder failure, NOT
page corruption). **Render S6 pages with `opj_decompress` (OpenJPEG)**, not jp2_page.py/PIL. Add this to future
S6-agent prompts (particular-table, continuance). (S6 page 2071 is genuinely truncated 1198B/blank — after privilege.)
### OT2 remaining (3) — corrected page map (from privilege agent's back-matter survey)
- particular-table → S6 ~p2050-2067 (agent reached p2063 before stop; RETRY, use opj_decompress). S1 has a 1610
  counterpart alphabetical index @archive-ot2-1610 p1101-1125 (edition nuance — flag for Sir).
- faults-escaped → S6 **p2070** (the "FAVLTS ESCAPED IN THE PRINTING" errata page; privilege box sits at its FOOT).
  (My earlier ~p2090 hint was WRONG — NT title begins S6 p2072, so OT2 ends ~2071.)
- continuance-of-church → S6, self-locate (longer apologetic section; ~p2040 or earlier; use opj_decompress).
- S6 OT2 back-matter order: …index tail "LAVS DEO" 2068 · Censura(Latin) 2069 · Faults-Escaped+Privilege 2070 ·
  blank/corrupt 2071 · NT title 2072.
### NT remaining (9) — S8 jp2-S08, hints recorded above (front ~p2-40, back ~p760-800).
### Post-matter: E5b window-grain scoring + apparatus pools; p17-tail cleanup (summe-and-partition); F resample; FINAL audit.

## NT FRONT structure recovered (from killed agents, 2026-07-20 eve) — S8 jp2-S08 indices
- Preface-to-Reader = idx23 (have=matter-nt-preface) · **Signification-or-Meaning = idx24** (heading "THE
  SIGNIFICATION OR MEANING OF THE NVMBERS AND MARKES vſed in this Nevv Teſtament"; single page, sig "d",
  catchword "THE") · **Books-of-NT = idx25** ("THE BOOKES OF THE NEVV Teſtament"). Censure-and-Approbation ~p2.
  summe-of-nt located in front (heading "NEW", display-VV). 
- **EFFICIENCY LESSON (Sir killed 3 NT agents for over-working)**: short single-page matter sections do NOT need
  the heavy iterative crop/zoom analysis used for dense scripture. Re-dispatch LEAN: render the page ONCE at full
  res, read it directly, minimal targeted crops only for genuinely ambiguous glyphs. Give EXACT page indices.

## COMPLETENESS-GAP CLEANUP LIST (batched, before FINAL — render spill pages + extend)
- summe-and-partition: final paragraph tail on TOP of OT1 p17 (before "SVMME OF THE OLD TESTAMENT").
- books-of-new-testament: patristic catena continues p26–27+ (points 3–4 Augustine/Tertullian/Hierom); p25 core done.
- (grep all matter GT for "continues"/"TRUNCATED"/"out of scope"/"would need" notes to find others.)

## Progress log
- 2026-07-19: Phase D START. Interval design + agent brief written. Batch 1 (OT1: 6 sections) DISPATCHED (opus agents):
  - a1eaeba9441bcd2c3 = summe-and-partition · aa727dcd57d3ed4ef = summe-of-old-testament
  - a3e7ffd752f7e1d0f = of-moyses · a67e3a5a794a7b341 = argument-of-genesis
  - a91ce34457a45dd40 = signification-of-the-markes · abff2e6158a75394d = brief-recapitulation
  Harvest each on completion (harvest_newmode-style: last GT object from .output), QC vs raster, add intervals check, insert.
  Batches 2 (OT2, 8) + 3 (NT, 9) staged — dispatch AFTER QC of batch 1 (validate interval format first).
- 2026-07-20 00:xx: **6-parallel dispatch HIT SESSION LIMIT — all 6 failed.** Sir: cap 2 agents at a time, deeper
  todo list, work within 5h window. Recovered PAGE-MAP from failures (no complete GT survived). Relaunched cap-2
  (seeded exact pages, skip locating): a9bc5b8acf30636ee=summe-and-partition(p15-16),
  a3a4a5496effb4fe9=summe-of-old-testament(p17-18). Queue: of-moyses(p18-19), argument-of-genesis(p19),
  signification-of-the-markes(p20), brief-recapitulation(p1127-29). Todo list = harness tasks #1-8.
- 2026-07-20: **matter_match_report.py BUILT + VALIDATED** (E5b core). Self-test correct (identical 3/3, noise
  3/3, garbled 0/3); lectionary vs S6 = ✗12% (located + scored, honest baseline). intervals_of() reliable for
  tables/display; PROSE needs agent-emitted intervals (new GT) or raster paragraph annotation (existing 11 = coarse).
- 2026-07-20: OT1 progress — ✅ summe-of-old-testament (a3a4a5496effb4fe9: 84 body, 34 intervals [2 para +
  title + citations/glosses], prose-conserv OK, self-validated). Running: summe-and-partition (a9bc5b8acf30636ee),
  of-moyses (aa86975a6508cf7f1). Queue: argument-of-genesis(p19), signification-of-markes(p20), brief-recap(p1127-29).
  Harvester `harvest_matter.py <agent_id>` (unescapes &amp;, writes GT, structural QC). 
  **E5b refinement TODO**: matter scoring = 2 pools — PARAGRAPH intervals (E4/E5a analog: per-interval + combined)
  vs APPARATUS intervals (citation/gloss/annotation/marginalia/footnote/heading → E5b "all apparatus combined").
  Update matter_match_report SCORE_KINDS split accordingly before the scoring run.
- 2026-07-20: OT1 cont'd — ✅ summe-and-partition (a9bc5b8: 78 body, 5 intervals, 3 para). **COMPLETENESS GAP**:
  its final paragraph (interval 4) TRUNCATES at p16 foot; ~5-line tail completes on TOP of p17 before "THE SVMME
  OF THE OLD TESTAMENT". Flagged in the GT's interval-4 "continues" note. Running: of-moyses, argument-of-genesis.
  Queue: signification-of-markes(p20), brief-recap(p1127-29).
  **Brief updated → WRITE-TO-FILE**: remaining matter agents Write GT to disk + return SHORT summary (was dumping
  ~15-20K-token GTs into orchestrator context). Old-style agents still running (of-moyses, argument-of-genesis).
  **COMPLETENESS-GAP CLEANUP (batched, before FINAL)**: grep all matter GT for "TRUNCATED"/"continues"/"out of scope"
  notes → render the spill page(s) → complete the tail(s). Known: summe-and-partition p17 tail.
- 2026-07-20: **C S9-Psalms RESOLVED** — jp2-S09ot2 gives 150/150 chapters (2402 vv, was empty). Residual per-verse
  noise (dropped drop-caps, 'THE BO' header-bleed) = general reOCR baseline shared by all sources (E-flagged), NOT
  S9-specific. No S9 coordinate/localization defect remains.
- 2026-07-22: **M2 VERSE-SEG ENGINE BUILT + VALIDATED** (`verse_seg.py` + `verse_seg_eval.py`; full record in
  REOCR-MASTER-PLAN §0.5). The §5 linchpin: janvier-cut both sides removes the boundary artifact — genesis-24
  witness 0.638→0.938 (+0.30). Real R2 per-verse identity now TRACKS page quality: genesis 0.956 (15/19 ≥.90, GATE
  MET), psalms 0.936 (8/12; residual = 3 genuine R2 recognition errors + 1 catchword leak → R3/M4, NOT seg —
  stays OPEN per No Silent Degradation). VS-4 length-sanity flags cross-page partials OPEN (genesis v30 `24:30a`).
  +2 new capabilities: (1) acrostic-paratext strip (janvier inlines "Nun. Everlasting." markers Ps 118 v=8k+1;
  fixed v105/v113 0.68→1.0); (2) **janvier-as-apparatus-filter** — drops interleaved central-column footnotes
  using the janvier grid alone, NO Surya/geometry (psalms 0.298→0.936); partial answer to §11 SEG. FINDING:
  witnesses NOT uniformly ~0.99 (s_dismas `\hfil` LaTeX artifacts; odr_com Ps-118 versification broken 175 vv in
  range 1..207) → §9 witness-witness claim qualified. STILL OWED for full M2: GT-3 gold-expansion, DIV-1 matrix.
  Code-review of both modules running. — **M2 REVIEW milestone reached.**
- 2026-07-22 (cont.): **code-review of verse_seg applied** — 3 real boundary-math bugs fixed+regression-guarded,
  validated numbers unchanged (local-anchor placement replaces global interpolation; block_min=3 localization
  kills unrelated-prose mislocalization 32→1; sorted(cverses)). **DIV-1 DONE** (`divergence.py`): witness noise
  floor janvier-cut, 28 ch — mod↔mod 0.9948, arc↔arc 0.9805 (NOT the asserted 0.994), Gold↔witness 0.96–0.978;
  per-verse crater routing (§7 alarm-2) surfaces 15 flag-IN loci (psalms-118 v107=0.0 pins odr_com defect).
  **GT-2 DONE** (`gt2_restandardize.py`): all 15 scripture GT re-standardized janvier-cut, non-destructive+backed
  up (.gt2-backup/); caught & verified Ps-1 janvier-6-vs-printed-7-verse difference. **M3 CORE**: qc_audit
  realign_vmap swapped align_coords→verse_seg (genesis base-OCR honest 0.65, artifact gone); REP-1 curated filter
  (S14 leak killed) + renderer guard; ocr_consensus already zero-ref. Pilot re-run (5 books) → coverage-audit-
  verse.json in flight; then render v010. OWED: REP-2 (R2 stream, compute-tail), REP-4 (gold col), REP-5 (matter
  rows). Docs: REOCR-MASTER-PLAN §0.5/§9/§12 current.
- 2026-07-22 (M3 rendered + REP-2): pilot re-run promoted → `coverage-audit-verse.json` (old `.pre-verse_seg`);
  **report RENDERED v014 `reocr-report-pilot.html`, 6438 verses, curated-clean** (DATA + version-compare delta
  both S1–S9 only; banned only in explanatory narrative). Base-OCR honest baseline (arc ~0.36–0.70, 1/271 chapters
  passing). **REP-2 base→R2 lift `reocr_lift.py`: all 15pp 0.721→0.926 (+0.204, pass 40%→68%); representative 14pp
  +0.210 (41%→73%)** — reOCR value proven; residual = R3 set (OPEN). colossians-3 FLAGGED confound (base 0.72→R2
  0.0, greek-margins + multi-chapter + suspected §4 mis-address; page 571 base-OCR lacks the gold Col-3:18) →
  §13 Q5, blocks its deliverable. NEXT: M5 four-alarm gate calibration; then M4 (needs GT-3), REP-4/5, M6.

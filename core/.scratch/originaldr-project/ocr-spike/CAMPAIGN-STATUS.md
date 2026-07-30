# GENESIS CAMPAIGN — STATE AT HANDOVER (2026-07-30, autonomous overnight session)

**Sir's order:** every chapter of Genesis to the standard chapters 1 and 16 reached — every verse of every
source (S1, S3, S6, S9) matching **each** of the four references at **>=0.90**, every ſ-surface CLOSED.

## THE HEADLINE, STATED PLAINLY

| | |
|---|---|
| cells >=0.90 against the ACHIEVABLE set | **4,104 / 5,284 = 0.7767** (from 0.7237 at first measurement, **+280 cells**) |
| cells >=0.90 against the raw total | 4,104 / 6,120 = 0.6706 |
| **chapters CLOSED** (references complete AND every cell >=0.90) | **2** — chapters 1 and 16 |
| chapters within 4 cells of closing | 0 |
| cells UNREACHABLE (a verse missing a reference) | **836, over 17 chapters** |

**The order as given cannot be met for 17 of the 50 chapters, and not for OCR reasons.** The standard is
">=0.90 against EACH of four references"; 836 cells sit on verses where a reference has no text at all, so no
recogniser can satisfy it. That is an acquisition defect in `reconstruction/reads`, upstream of every OCR stage
— `s_dismas.json` holds ONE entry for genesis 8 and its text is Gen 8:6 filed under key 8/1. **Repairing it is
the single highest-value action available, and I did not attempt it: a wrong edit to a reference corrupts every
score in the project.**

## WHAT MOVED, AND WHY

1. **The ſ-surface gate was the bottleneck, not recognition.** R3's content scored 0.97-1.00 against the
   governing reference while 19 of 25 verses stayed OPEN on surface debt. Two fixes: archaic-equivalent transfer
   (keep R2's observed `ſeuenth` rather than R3's modernized `seventh`) and an attested ſ lexicon built from the
   2,611 hand-transcribed GT lines — **502/502 and 657/657 = 1.0000 on held-out GT**, refusing 69% and 55%.
   Genesis 2 went 0.700 -> 0.840 and ADOPT 2 -> 15.
2. **R3 across the reachable set**, sequential (17GB model), fewest-open-first, self-driving, lock-protected.
   24+ chapters, **zero crashes** after the resilience fix.
3. **Agent-read GT calibrated and in use** — 40 blind reads against human transcription: content 0.9923 mean /
   1.0000 median on correctly-paired lines, **ſ counts exact on 29/29**.

## WHAT IS BLOCKING, WITH EVIDENCE

**S6 (the 1635 second edition) is the weakest source in 46 of 50 chapters, mean pass rate 0.570.** Its left
annotation column is merged into body rows by the recognizer (`and trie and out of thy kindred`,
`borne of therfore went out`). **Eight separate attempts to separate it have now failed and are pinned with
their numbers** — seven geometric (bands, thresholds, gap ratios, per-leaf edges, the S6 band sweep) and one on
content and sequence, which deleted scripture on the population while looking excellent on hand-picked rows.
The only thing that touches this residual is R3 re-reading the printed crop.

## CORRECTIONS TO MY OWN EARLIER CLAIMS THIS SESSION

* The derived `CHAPTER_MODEL` — which I called "the campaign's central lever" — is **net negative** measured
  across all 49 chapters (ON 3,827 vs OFF 3,834). Default OFF, pinned with figures.
* I committed that deriver as fixing "all 48 chapters" and **then never ran it on 45 of them**. True about the
  capability, false about the state; nothing in the pipeline could have said so.
* §13 Q30's `janvier_fit` defect is **prevalent but low-yield** — 33.7% of decisions, 0.01% of cells. My earlier
  "may be worth more than either model change" was wrong.
* The R2 challengers (more training data, matter prose) both **lost** to the incumbent. Item 2 closes negative.
* A report line counted genesis 49 as "100% of achievable" when its achievable set is 8 cells of 128. That is
  denominator laundering; CLOSED now requires complete references.

## STANDING STATE
* **17 commits**, nothing pushed. The hold on push stands.
* **172 tests green.** Chapters 1 and 16 held at 124/124 and 64/64 through ~25 changes — they are the sentinels
  on every measurement and they caught two regressions tonight.
* Ledger `.campaign/r3-ledger.txt`; per-chapter matrices `.campaign/matrix-genesis-N.json`;
  `chapter_campaign.py --report` reproduces every number above.

## BREADTH HAS REACHED ITS CEILING — MEASURED

R3 ran on 31 chapters with zero crashes and the achievable rate rose 0.7237 -> 0.7767. It is now done as a
breadth instrument: **the closest reachable chapters plateau 12-16 cells short of closing**, and none is within a
few cells.

    ch22 84/96 (short 12)   ch33 68/80 (12)   ch7 83/96 (13)   ch48 75/88 (13)
    ch25 122/136 (14)       ch45 98/112 (14)  ch17 93/108 (15) ch2 84/100 (16)

Those remaining cells are the classes R3 cannot reach: interleaved annotation words, unlocalized verses, and
edition divergence. Closing a chapter therefore needs the hand-work chapters 1 and 16 received — per-leaf
`PAGE_OVERRIDE`, drop-cap entries, visual readings, a reference audit — which historically is on the order of a
session per chapter. **That is the honest cost of "every chapter to the Genesis 1 standard": it is not a pipeline
run away, and no amount of R3 changes that.**

## WHAT "THE S6 RESIDUAL" ACTUALLY IS — measured on ch22, and it is not one problem

An attempt to hand-close genesis 22 (12 cells short, 11 of them S6 from ONE leaf, p88) was expected to need a
per-leaf `PAGE_OVERRIDE`. It does not, and the reason matters more than the chapter:

* p88's ROW STARTS cluster at 0.22-0.24, identical to its sibling leaves. **The band is not wrong.**
* Reading the rows word by word shows they are **entirely ANNOTATION PROSE spanning the full measure** —
  `the freewoman afflicted the handmaid, and the Apoſtle calleth it not Heretikes`, `Againe, he ſayth of Sara,
  Illuſionem vidit...` — plus a **right marginal column** (`Heretikes`, `other`, `ſword` at x>0.765) appended to
  every row.
* So p88 is an annotation-heavy leaf carrying commentary that competes for verse spans, and the intrusions
  inside words (`thy only begot-for ten-ſonne`, `into the Maſſe on Laud ot vilion` for `land of vision`) are that
  commentary interleaved by the recognizer, not a band error.

`_is_annotation_leaf` already excludes a WHOLE leaf that is nothing but notes (it caught `jp2-S06` p77 in
Genesis 16 on the printed `NNOTATION` heading). p88 is not that case: it carries both scripture and commentary,
so whole-leaf exclusion would delete real verses.

**Therefore "S6 is the weakest source" is at least THREE unrelated problems wearing one label:**

| cause | example | remedy class |
|---|---|---|
| annotation prose sharing rows with scripture on a mixed leaf | ch22 p88, ch12 | column/region separation within a leaf — UNBUILT |
| missing leaves and unlocalized verses | ch44 (8 verses with NO span; 4 leaves vs 5 elsewhere) | localizer coverage, upstream |
| edition divergence (1635 against 1609 references) | documented in CHAPTER-WORKFLOW | collation judgement; no recogniser closes it |

Every one of the eight pinned separation attempts was aimed at the AVERAGE of these three. That is why each
looked convincing on its chosen examples and failed on the population. **Sizing them separately is the
prerequisite for a ninth attempt, and it is fresh work rather than a patch.**

## THE NEXT THREE ACTIONS, IN THE ORDER THE EVIDENCE SUPPORTS
1. **Repair the reference data** (836 cells, 17 chapters). Nothing else unblocks them.
2. **A ninth approach to the S6 interleaved apparatus** — informed by eight documented failures. R3-on-crop is
   the only thing that currently touches it, so the question is whether an S6-specific crop (excluding the left
   column) beats the current full-width crop.
3. **Finish R3 across the remaining reachable chapters** and re-run those adopted under the superseded
   configuration.

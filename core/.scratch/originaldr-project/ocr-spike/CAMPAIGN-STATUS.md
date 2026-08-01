# GENESIS CAMPAIGN — RESUME HERE (state 2026-07-31, after the reference-gap session)

**Sir's standing order:** every chapter of Genesis to the standard chapters 1 and 16 reached — every verse of
every source (S1, S3, S6, S9) matching **each** of the four references at **>=0.90**, every ſ-surface CLOSED.
**Stance (Sir, 2026-07-30): DEPTH-FIRST**, and after each chapter is brought up, **re-measure the others** —
knock-on gains from generalizable fixes should reduce the work as the campaign iterates.

## THE ONE RULE THAT GOVERNS EVERYTHING HERE (§13 Q47)

> **A rule is measured by the TEXT IT CHANGES, not by the verdicts it flips.**

`split_glued` scored HELPS 8 / HURTS 1 / net +8 cells across 50 chapters with the sentinels unmoved, and was
minutes from adoption. It alters **1,356 tokens**, tearing real words into morphemes (`lawful` -> `law ful` 28x,
`faithful` -> `faith ful` 14x). The score could not see it: the corruptions were score-neutral or fell in cells
that already failed. **Before adopting ANY rule that edits text, run `faithfulness_audit.py` and read what it
changes.** Nine rules are pinned OFF in this tree with their numbers; the audit is why the tenth was caught.

**It caught an eleventh this session, and that one was mine.** Widening the s_dismas note-scan, the anchor
class was written `[A-ZſVI]` to admit a note opening on a long-s word — but `ſ` is LOWERCASE, so the pattern
matched the commonest phrase in the book, `a ſonne`. The scoreboard would have shown a gain (chapter 30 came
back from a real defect at the same time). The audit showed removals jumping 875 -> 2,462 tokens, and reading
them showed sixteen spans of plain scripture. **Run the audit on your own fixes, not only on other people's.**

## STATE

> **⚠ TWO BACKGROUND PASSES ARE RUNNING. DO NOT START A THIRD, AND DO NOT DUPLICATE THEM.**
> `ps aux | grep -E "r3-runner|r2-pass"` before doing anything. Both were started 2026-07-31 ~21:45.
>
> * **`r3-runner.sh`** — R3 over every chapter, fewest-open-cells-first, WITH the new R2 attesting arm.
>   Serialized behind the atomic `mkdir` lock `.campaign/r3-runner.lock` (one 17GB olmOCR at a time). Progress:
>   `.campaign/r3-ledger.txt`. **To run R3 yourself you must take that lock** (`mkdir .campaign/r3-runner.lock`,
>   `rmdir` after) — or stop the runner first.
> * **`r2-pass.sh`** — ſ-faithful kraken recognition of every leaf, chapter by chapter, feeding `.r2-attest/`.
>   ~14s per leaf, ~931 leaves total. Progress: `.campaign/r2-attest-ledger.txt` and `ls .r2-attest | wc -l`.
>
> **The board therefore CLIMBS WHILE YOU READ IT.** Every figure below is a snapshot. A total that fails to
> reproduce is not necessarily non-determinism — check both ledgers for activity newer than your measure run
> before concluding anything.

| | (snapshot 2026-07-31 22:00 UTC, and rising) |
|---|---|
| cells >=0.90 / ACHIEVABLE | **5,076 / 6,116 = 0.8300** |
| cells >=0.90 / raw total | 5,076 / 6,120 = 0.8294 |
| chapters by band | <0.70: **3** · 0.70-0.80: 14 · 0.80-0.90: 29 · 0.90-0.95: 1 · >=0.95: **3** |
| cells with NO TEXT anywhere | **0** (was 26) |
| **CHAPTERS CLOSED** | **2** — chapters 1 and 16 (sentinels; re-measure them on EVERY change) |
| cells blocked by an absent reference | **4**, in one chapter (was 704 over 16 chapters) |
| tests | **188 green** (`../ocr-venv/bin/python -m pytest tests/`) |
| commits | 29 unpushed — **the hold stands** |

**REF-GAP as a class is GONE.** The only remaining gap is `odr_com` genesis **23:20**, and it stays open: the
site prints 19 verses where the DR has 20, the verse is not merged into a neighbour (its v19 is the same length
as everyone else's), and it is simply absent from that witness. **That is an acquisition task, not a patch.**

### What moved, and the honest reading of it

| | achievable | >=0.90 | ratio | blocked |
|---|---|---|---|---|
| session start | 5,416 | 4,273 | 0.7890 | 704 |
| after genesis 8 | 5,500 | 4,354 | 0.7916 | 620 |
| after the odr_com repair | 6,096 | 4,806 | **0.7884** | 24 |
| after the five merges | 6,112 | 4,832 | 0.7906 | 8 |
| after genesis 30 | 6,116 | 4,853 | 0.7935 | 4 |
| + R3 running in the background | 6,116 | 4,884 | 0.7986 | 4 |
| R3 breadth exhausted (runner idle) | 6,116 | 4,960 | 0.8110 | 4 |
| + ch8 depth-first work | 6,116 | 4,963 | 0.8115 | 4 |
| + ch8 visual reads (87/88) | 6,116 | 4,967 | 0.8121 | 4 |
| + mixed-leaf fix, worst-first | 6,116 | 5,014 | 0.8198 | 4 |

The ratio **fell** at the third row while 596 cells were unblocked. That is the true direction: the old
denominator excluded the hardest 700 cells because we did not hold the references for them. **Do not read the
0.7890 -> 0.7935 move as +0.0045 of progress — the two numbers are rates over different populations, and the
new one is a rate over 99.9% of the book.**

## WHAT WAS FIXED THIS SESSION, AND WHAT IT TELLS YOU

Four defects, none of them an OCR problem. Every one was in the REFERENCES — the instruments the OCR is
measured against — and three had been recorded in an artifact that nothing read.

1. **`odr_com` lost 196 verses to one optional quote.** `id\s*=\s*['"]?Annotations['"]?[^>]*>` also matches the
   prefix of `id="Annotations2"`, and that id is not apparatus — on this site it is a STYLE whose meaning is
   positional: after the ANNOTATIONS. header it wraps annotation prose, before it, plain scripture. Every
   chapter using it was cut at its first occurrence. **The scrape manifest recorded `verse_count_match: 37/50`
   and a chapter-bag agreement 0.07 below the per-verse agreement — a gap its own documentation defines as
   isolating "text loss". Written in July, consumed by nothing.**
2. **s_dismas genesis 8** — a page-foot note block spliced into the MIDDLE of verse 20 (not a suffix, so no
   trimmer could reach it), plus the edition's own merge of DR 15+16 under a printed `15`.
3. **Five reference merges** (s_dismas 20:17, odr_com 20:17, odr_com 34:28, s_dismas 40:1, s_dismas 41:45),
   each corroborated arithmetically AND textually before encoding.
4. **s_dismas genesis 30** — six verses sitting behind the next chapter's running head, and a verse-6 tail lost
   at a page foot. **A hole in a nearly-full chapter is invisible to a count test:** ch30 held 42 of 43 and
   sailed past `h >= 0.9 * jn` while carrying `...geuing me againe Bala conceauing bare an other`.

**The lesson to carry:** when a chapter will not come up, ask what the REFERENCE says before asking what the
recognizer said. Four of this session's five wins were reference repairs, and the fifth was a parser bug.

## NEXT STEPS, IN ORDER — THIS IS THE RESUME PLAN

1. ~~SIZE THE THREE S6 CAUSES SEPARATELY~~ **DONE 2026-07-31 — `s6_causes.py`, and the answer redirects the
   work.** The three causes are NOT co-equal, and the one eight attempts were aimed at is not the big one.

   | | S6 | S1 | S3 | S9 |
   |---|---|---|---|---|
   | open cells | **568** | 242 | 211 | 174 |
   | INTERLEAVE (apparatus in the row) | 100 (17.6%) | 25 (10.3%) | 14 (6.6%) | 35 (20.1%) |
   | MISREAD (letters wrong) | **255 (44.9%)** | 96 | 73 | 41 |
   | DIVERGE | 198 | 119 | 114 | 90 |
   | NO-TEXT (never localized) | 14 | 2 | 10 | 8 |
   | **fail in this source ALONE** | **399** | 40 | — | 46 |
   | fail in ALL FOUR (the same cells) | 40 | 40 | 40 | 40 |

   **EDITION DIVERGENCE IS CAPPED AT 40 CELLS — 0.65% of the book — and needs no classifier to bound.** It is a
   property of the page all four sources photographed, so it CANNOT fail in one source alone; the cells failing
   in all four are its ceiling. It was carried as one of three co-equal causes and it is an order of magnitude
   smaller than that.

   **S6's excess is source-specific reading quality.** It fails alone on 399 cells against 40 and 46 for S1 and
   S9 — a nine-fold excess — and its excess over the other sources is concentrated in MISREAD, not INTERLEAVE
   (its interleave share, 17.6%, is *below* S9's 20.1%). **A ninth apparatus-separation attempt would be aimed
   at at most a fifth of S6's failures, and at a share S6 does not even lead on.** The lever is R2/R3 recognizer
   quality on S6's leaves.

   Two caveats to carry, both measured rather than asserted: the INTERLEAVE count is a **lower bound** (23% of
   DIVERGE-labelled cells also carry a word attributable to that chapter's apparatus, against 46% of INTERLEAVE
   ones and 10% of MISREAD ones), and the DIVERGE bucket cannot mean *edition* divergence for any cell that
   fails in one source alone — those are misreadings the character-similarity test judged too unlike to be one.
   **Read `s6_causes.py --examples 3` before quoting its table**; its first version reported the opposite
   answer, cleanly, and the examples are what exposed it.

2. **ch8 IS AT 87/88 AND THE LAST CELL IS A COLLATION QUESTION, NOT AN OCR DEFECT.** S1, S3 and S9 all reach
   1.000; S6 is 21/22. All 18 R3 adoptions have a CLOSED ſ-surface with zero unresolved tokens.
   **8:14/S6 stays OPEN and blocks.** The plate prints `In (b) the ſecond month , the ſeauen and twentieth day
   of the month the earth was dried` — our transcription is CORRECT, read at 2600px. The scores split exactly
   along the edition line: MODERN references agree (sabates_a/madueke_b 0.9877), 1609 ARCHAIC ones do not
   (s_dismas 0.8765, odr_com 0.8889), because S6 is the 1635 SECOND edition. R3 moves it 0.876 -> 0.864, AWAY
   from the bar. **No reading of those pixels satisfies both editions.** This is §13 Q21's first verified
   instance; the evidence is in `collation-flags.json` and the report surfaces it. **The cell is still counted
   as failing in every denominator — the register explains a failure, it never excuses one.**
   What would resolve it is a policy decision, Sir's not the pipeline's: either a 1635-edition witness gets a
   1635-edition governing reference, or the standard admits an edition-divergence verdict distinct from a
   transcription failure.

3. **DEPTH-FIRST, NEXT CHAPTERS.** Closest to closure now, cells short: **ch8 (7)**, ch12 (10), ch20 (11),
   ch22 (12), ch33 (12), ch18 (13), ch48 (13), ch25 (14), ch45 (14), ch2 (15). Follow CHAPTER-WORKFLOW phases
   0-7. After each chapter closes, **re-measure all 50** (`chapter_campaign.py --chapters 1-50 --phase measure`,
   ~5 min) to capture knock-on gains — Sir's explicit instruction.
4. **The s_dismas re-parser still fails 8 chapters it ought to reproduce** (2, 16, 19, 26, 31, 35, 36, 44 —
   chapter 44 now reaches 28 of 34, chapter 31 only 6 of 55). Each failure is a parse defect the SHIPPED reads
   may also carry, and chapter 30 proved those are invisible to the count test. Fixing them lets the re-parser
   supersede the original parser wherever it validates. **Use the `HOLE:` criterion already in `--verify`.**
5. **odr_com genesis 23:20 — ACQUISITION.** Report it; do not patch it. If a second odr-com surface exists
   (a print edition, a different page), that is the route.

## WORST-FIRST (Sir, 2026-07-31): work up the bands until every chapter is >= 0.95

**The order is worst-scoring first, re-measuring all 50 after each band for knock-on gains.** Three tools make
this tractable and they should be the first thing a resumed session reaches for:

| tool | the question it answers |
|---|---|
| `leaf_diag.py --chapter N --source SX` | why is THIS source collapsing in THIS chapter — leaves, the band in force, the tokens it drops on each side, the open cells |
| `chapter_open_probe.py --chapters N` | where the chapter OPENS on each witness: printed heading, italic argument, verse 1 located by janvier's wording — and whether it is a MIXED LEAF |
| `s6_causes.py --source SX --examples 3` | the cause mix of a source's open cells (INTERLEAVE / MISREAD / DIVERGE / TRUNCATED / NO-TEXT) |

**THE DIAGNOSTIC THAT FINDS THE BIG ONES.** A source scoring 0.90 across the book and 0.23 in one chapter has
a LEAF defect, not a recognition problem. Rank `(chapter, source)` pairs by how far the source sits below its
own median — every one of this session's large wins came off the top of that list.

**What the remaining work is made of** (measured, not guessed — `s6_causes.py`):
* **MISREAD ~45%** — recognizer quality. R3/R2 territory; `r3-runner.sh` works it autonomously.
* **DIVERGE ~35%** — but a cell failing in ONE source cannot be edition divergence, so most of these are
  misreads the character-similarity test judged too unlike. Edition divergence proper is capped at **40 cells
  book-wide** (§13 Q50) — it must fail in all four sources, being a property of the page.
* **INTERLEAVE ~18%** — annotation prose sharing rows with scripture. **This is the 8-times-failed problem**,
  and chapter 5's S9 leaves show why: the x-histogram is FLAT from x100 to x1900, so there is no gutter to cut
  on. Whole printed lines from different columns share a y-band and the row grouper merges them. Closing the
  worst chapters needs row-level column assignment, which is a BUILD, not a tuning.

## THE SUB-80% CHAPTERS, PARTITIONED BY WHAT IS ACTUALLY WRONG (Sir's two sets, tested 2026-07-31)

Sir proposed two sets — "S6 is the culprit" (3, 6, 15, 23, 47) and "other patterns" (5, 21, 24, 26, 28, 35,
37, 39, 41, 49) — and asked whether they are two problems worth reducing separately. **Measured, the split
does not fall where the sets do: S6 is the worst source in 12 of the 15**, including 7 of the 10 in the
"other" group (21, 24, 26, 28, 37, 39, 49). The partition that the data does support:

| group | chapters | worst source | dominant cause | what it needs |
|---|---|---|---|---|
| **S6 chronic — interleave** | 3, 6, 15 | S6 0.38-0.59 | INTERLEAVE 4-6 per chapter | per-leaf bounds; S6's swept band is right for its ordinary leaves and wrong for its annotated ones |
| **S6 chronic — misread** | 23, 47, 21, 24, 26, 28, 37, 39, 49 | S6 0.23-0.68 | MISREAD 3-16 | R2/R3. No geometry reaches it |
| **A GOOD SOURCE COLLAPSING** | 5 (S9 0.58), 35 (S1 0.52), 41 (S1 0.53) | not S6 | see below | diagnosed individually |

**The third group is the one that used to pay, and this time it does not.** A source at 0.88-0.93 across the
book dropping to 0.52 in one chapter was the signature that produced +15 on genesis 39 and +29 on genesis 44 —
a leaf the model was never told about. `leaf_diag` on genesis 41/S1 shows something different: the rows read
`tlare ſprang alto orher eates a many, the andwno` and `vith adulon, deuou ng al the beaue of the`. That is
DEGRADED RECOGNITION on those leaves, not layout, and no band, bound or chapter model reaches it. Genesis 5/S9
is the skew case `line_split` already addresses.

**So the whole sub-80% band reduces to two problems, and only one of them is geometry.** The interleave three
are worth per-leaf work on S6's annotated leaves; everything else is recognizer quality, which is what the R2
attestation pass and the R3 runner are for. Both are running.

## THE R2/R3 FINDING — where the remaining ~1,100 cells actually are (2026-07-31)

**1,142 cells are ones R3 HAS ALREADY READ CORRECTLY.** Counted across every `r3-residual-genesis-*.json`:
R3's reading passes **all four references at >=0.90**, and the adoption is refused for one reason only —
`CONTENT OK, ſ-SURFACE OPEN`. That verdict appears **1,158** times against 1,133 `ADOPT`. The remaining gap on
the board is ~1,080 cells. **These are the same cells.** The recognizer is not the binding constraint; the
ſ-surface attestation is.

**THE ATTESTING ARM IS THE BASE SCAN OCR, NOT THE FINE-TUNED RECOGNIZER.** `s_arbiter.transfer(r2_text,
r3_text)` closes a surface only where the attesting arm OBSERVED the glyph, and `gen1_r3` passes
`t["old_text"]` — the incumbent page-model text, which comes from the stored corpus OCR. Meanwhile
`reocr_core` defines `R2_MODEL = models/reichenau_dr.mlmodel`, the ſ-faithful DR fine-tune (val 0.9396), and
`models/dr_v3_armA/best_0.9739.mlmodel` scores better still — and **grep finds no reference to any of them in
`gen1_*.py`, `s_arbiter.py` or `chapter_campaign.py`.** The trained ſ-faithful recognizer is not in the path
that needs it.

**THIS IS THE NEXT BUILD, and it is the one that unlocks the campaign**: recognize each leaf with the
fine-tuned R2 model, align its output to the verse spans, and give `s_arbiter` a genuinely ſ-faithful arm to
attest from. Every closure it produces is an OBSERVATION, which is the only kind this project accepts.

**WHAT MAY NOT BE DONE INSTEAD.** `s_lexicon` refuses about three quarters of what it is asked, and that
strictness is exactly why it validates at 1.0000 on held-out GT. Loosening it to close these cells would be
inventing glyphs — `long_s_rule.restore_long_s` was rejected at ~90.4% for precisely that, about one invented
glyph in ten published as the printed surface.

**Composition of the 1,726 unresolved token-occurrences** (measured, and the measurement corrected twice —
see below):
* **324 are f-decisions the lexicon can settle**: folding the `f` to `s` yields a non-word (`slocks`, `slesh`,
  `sield`, `sormed`), so the `f` is a true `f`. **Caveat, stated because it is real:** the book lexicon is
  Genesis-only, so `found`->`sound` counts as decidable here while the wider book has `ſound`. Scope any such
  closure to the lexicon that justifies it.
* **84 must never be guessed**: folding gives a REAL word — `wife`/`wise`, `foule`/`soule`, `feed`/`seed`,
  `fold`/`sold`. These are the refusals that make the instrument trustworthy.
* **1,318 are s-decisions and the remainder** — an attesting recognizer or an eye, nothing else.

**TWO MEASUREMENTS OF MINE WERE WRONG BEFORE THEY WERE RIGHT, both worth remembering.** The first concluded
"0 of 1,726 unresolved tokens are in the ſ-lexicon" — the lookup was against the edition keys rather than the
words, and the lexicon in fact holds `ſonne` (31 obs), `alſo` (40). The second tested decidability by folding
`f`->`ſ` and asking whether the result was a book word: **the book lexicon contains zero long-ſ characters**,
so that test can never be true and called all 403 hits decidable, including `wife`/`wiſe` — the project's own
canonical example of a load-bearing refusal. Check what a lexicon actually contains before asking it a
question.

## THE LIVE BOARD, VISUALLY — `reocr-report-pilot.html`

```
../ocr-venv/bin/python build_reocr_report.py --campaign-note "what this step was"
```

The report's **first section** is the campaign board, and it is the ONLY section that moves when a chapter is
worked — everything below it renders `coverage-audit-verse.json`, the 5-book P3 pilot audit, a different
pipeline at a different grain. The board reads `.campaign/matrix-genesis-N.json` directly: four headline cards,
50 chapter tiles (click for the verse grid), every verse x every source as pass / fail-with-score / blocked,
and a click on any failing cell shows exactly what that source produced and which leaf it came from.

`--campaign-note` labels the point on the progression sparkline; a snapshot is appended to
`.campaign/progression.jsonl` **only when the totals actually change**, so rebuilding to look at it does not
manufacture history. Open it as a `file://` URL — it is fully self-contained.

## TOOLS (all in `ocr-spike/`, all chapter-parameterized)

| tool | what it answers |
|---|---|
| `chapter_campaign.py --report` | the whole board: per-chapter rate, triage, achievable vs blocked, closed set |
| `faithfulness_audit.py` | **what each rule CHANGES in the text** — run before adopting any text-editing rule |
| `ref_repair_s_dismas.py --verify` | re-parse of the s_dismas PDF; reports REPARSE / HOLE / still-short per chapter |
| `ref_renumber.CORRECTIONS` | every reference numbering fault, with its corroboration; reversible, source untouched |
| `scrape_odr_com.py` (in `core/tests/fixtures/.../acquisition/`) | the odr-com witness; manifest write MERGES |
| `s_lexicon.py --build --validate` | attested ſ and f-vs-ſ lexicons from human GT; 502/502 and 657/657 held out |
| `chapter_model_derive.py` | opening-leaf model per chapter (**measured NET NEGATIVE, default OFF**) |
| `.campaign/r3-ledger.txt`, `.campaign/matrix-genesis-N.json` | the R3 log and every chapter's matrix |

## PINNED NEGATIVES — DO NOT RE-PROPOSE WITHOUT READING THEIR NUMBERS

Nine, each wired-but-off with figures and a test: four geometric apparatus splits (word-x threshold, gap ratios,
widest-gap right edge, per-leaf median left edge), the S6 band sweep (0.228 costs chapter 1 four cells), the
margin-orphan gap test (fires nowhere), the row-interrupt content filter (deletes scripture: ch1 124->107), the
derived CHAPTER_MODEL (net -7 cells), and `split_glued` (1,356 corruptions for +8 cells).

## OPERATIONAL NOTES

* Interpreter `../ocr-venv/bin/python`; MLX needs `PYTORCH_ENABLE_MPS_FALLBACK=1`.
* R3 is ~17GB resident — run it SEQUENTIALLY. `r3-runner.sh` holds an atomic `mkdir` lock.
* R3 adoptions are APPEND-ONLY and go stale when the page model improves — `chapter_campaign.stale_adoptions(ch)`.
* Agent-read GT is APPROVED and calibrated: 40 blind reads, content 0.9923 mean, **ſ counts exact 29/29**.
* `ref_renumber.py` is now tracked (it governs every score and was untracked). Reads under
  `reconstruction/reads/` are gitignored build artifacts — regenerate with `detect_sources.py <source>`.
* A monitor must read the ARTIFACTS (matrices), never a prose document — a heartbeat once grepped this file and
  silently reported an empty closed-chapter list when it was reworded.

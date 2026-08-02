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

> **✅ BOTH PASSES FINISHED (2026-08-01). The board below is STABLE, not a moving snapshot.**
>
> * **`r2-pass.sh` COMPLETE** — `R2 PASS COMPLETE` in `.campaign/r2-attest-ledger.txt` at 23:15 on 07-31;
>   **594 leaves** in `.r2-attest/`. Note this is 594, not the ~931 leaves the pass was scoped against — the
>   difference is leaves no chapter credits, but if a later chapter needs one, re-run `r2_attest.py` for it.
> * **`r3-runner` COMPLETE for this round** — 47 chapters in `.campaign/r3-ledger.txt`, **every one `rc=0`**.
>   Since 02:44 it has logged only `no chapter ready` every 5 min: its selector skips chapters already in the
>   ledger, so the round is genuinely exhausted, not stalled.
>
> **⚠ ONE v1 RUNNER IS STILL ALIVE AND IDLE — pid 85490, started 07-29 23:13.** It is harmless (asleep in the
> 300s wait loop, holding `.campaign/r3-runner.lock` legitimately) and it will auto-resume R3 if a chapter
> becomes eligible again. But it is the **v1** script, so `kill` cannot stop it — **`kill -9` is required**, and
> then `rm -rf .campaign/r3-runner.lock`. Clear the ledger before starting a v2 round or it will find nothing
> to do.
>
> `ps aux | grep -E "r3-runner|r2-pass"` before doing anything. Both passes were started 2026-07-31 ~21:45.
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
>
> ### ⚠⚠ `r3-runner.sh` v1 IS UNKILLABLE AND RELEASES ITS OWN LOCK. USE `r3-runner-v2.sh`. (2026-07-31)
>
> A resumed session found **SIX** `r3-runner.sh` processes alive with **NO lock directory present**, serialized
> only by the in-loop `pgrep` — the exact check-then-act race the lock was added to eliminate. Six 17GB olmOCR
> models on a 128GB machine was one chapter-completion away.
>
> The cause is one line: `trap 'rmdir "$LOCK" 2>/dev/null' EXIT INT TERM`. **A TERM handler that does not exit
> makes the script SURVIVE SIGTERM** — the body runs, control returns to the loop, and the runner keeps going.
> So every attempt to stop a runner did exactly one thing: released the mutex and left the runner running. The
> failure compounds itself, because each "stop" frees the lock that would have refused the next runner.
>
> * **A `mkdir` lock is atomic on ACQUIRE and says nothing about RELEASE.** With no owner token inside it, any
>   party's `rmdir` frees another party's lock. `r3-runner-v2.sh` writes `owner.pid` into the lock, releases
>   only a lock it owns, reclaims a lock whose owner is dead, and exits on INT/TERM.
> * **`kill` will not stop a v1 runner — use `kill -9`**, which no trap can intercept. Check the count with
>   `ps -eo pid,command | grep r3-runner` and expect exactly ONE.
> * **Do not edit a running `.sh` in place.** zsh reads scripts incrementally, so an edit can resume the live
>   shell at a wrong byte offset. v2 was written as a NEW file for this reason.

| | (snapshot 2026-08-01 17:30 UTC — **BOTH PASSES ARE FINISHED**; this figure is stable) |
|---|---|
| cells >=0.90 / ACHIEVABLE | **5,245 / 6,116 = 0.8576** |
| cells >=0.90 / raw total | 5,245 / 6,120 = 0.8570 |
| chapters by band | <0.70: **0** · 0.70-0.80: 5 · 0.80-0.90: 32 · 0.90-0.95: 10 · >=0.95: **3** |
| cells with NO TEXT anywhere | **0** (was 26) |
| **CHAPTERS CLOSED** | **2** — chapters 1 and 16 (sentinels; re-measure them on EVERY change) |
| cells blocked by an absent reference | **4**, in one chapter (was 704 over 16 chapters) |
| tests | **202 green** (`../ocr-venv/bin/python -m pytest tests/`) |
| commits | 44 unpushed, plus this session's work UNCOMMITTED — **the hold stands** |

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
| + R2/R3 passes + ch15 leaf bound + 3 swept leaves | 6,116 | 5,085 | 0.8314 | 4 |
| **both passes FINISHED, full re-measure of all 50** | 6,116 | 5,224 | **0.8541** | 4 |
| + ch41 margin column, 8 leaves (3 witnesses) | 6,116 | 5,225 | 0.8543 | 4 |
| **+ 5 infixed-apparatus excisions in s_dismas** | 6,116 | **5,245** | **0.8576** | 4 |

**NO CHAPTER IS BELOW 0.70 ANY MORE**, and the worst chapter on the board is now ch23 at 0.700 — the one that
CANNOT MOVE (`ref_gaps: odr_com`). Read that as the grading in CHAPTER-WORKFLOW §6b B2 doing its job: the
board's floor is now set by an acquisition task, not by a reading failure.

**The two passes were worth +139 cells**, and hand-attributed geometry work in the same session was worth +3.
That ratio is the argument for letting a pass run to completion before opening a new seam by hand.

> **COUNT `n_pass`, NEVER `n_cells - n_open` (2026-08-01).** They differ, and the difference is silent. ch23
> carries 4 BLOCKED cells (the `odr_com` gap): blocked cells are in neither `n_pass` nor `open`, so subtracting
> `open` from `n_cells` credits them **as passing** and overstates the board. It cost this session a headline
> figure — 5,228 was reported before `build_reocr_report.py` disagreed with it at 5,225. The report was right.
> `n_pass` is the authoritative field, and `rate` is `n_pass / n_cells`.

The ratio **fell** at the third row while 596 cells were unblocked. That is the true direction: the old
denominator excluded the hardest 700 cells because we did not hold the references for them. **Do not read the
0.7890 -> 0.7935 move as +0.0045 of progress — the two numbers are rates over different populations, and the
new one is a rate over 99.9% of the book.**

## THE WORST-FIRST QUEUE AFTER THE PASSES (2026-08-01, re-measured)

The distribution has **compressed**: the worst chapter is now only 0.045 clear of the second worst, so there is
no dominant hole left to attack. Depth-first still applies, but expect single cells, not tens.

Re-ranked after the five excisions (2026-08-01). **ch26 and ch47 left this list entirely.**

| ch | rate (`n_pass`/`n_cells`) | note |
|---|---|---|
| 23 | 56/80 = 0.700 | **4 BLOCKED (`ref_gaps: odr_com`)** — CANNOT close by OCR. Skip; the R3 runner already does |
| **41** | 163/228 = 0.715 | S1 **0.5439** — recognizer damage, established by elimination (see PAGE_OVERRIDE) |
| 35 | 86/116 = 0.741 | |
| 39 | 72/92 = 0.783 | |
| 37 | 115/144 = 0.799 | |
| 10 | 103/128 = 0.805 | |
| 49 | 103/128 = 0.805 | |
| 28 | 71/88 = 0.807 | |

**Do not confuse "unreachable" with "hard".** ch23 is second-worst on the board and no amount of OCR work will
move it — its 4 blocked cells are the campaign's only remaining reference gap (genesis 23:20 absent from
`odr_com`). Skip it and go to ch35.

**The seam that is now closed:** geometry. ch3, ch6 and ch41 were all carried as column/interleave problems and
all three turned out not to be — ch3/ch6 lacked a chapter model, ch41 had a real but nearly score-free margin
merge. Every leaf-bound lever swept so far has been worked out. What is left in the worst chapters is
**recognition**, which means R3 (vision-LLM) or a better Rung-2 recognizer, not another bound.

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

3. **THE NEXT ROUND — USE `CHAPTER-WORKFLOW.md` § THE ROUND TEMPLATE (rewritten 2026-08-01).** It is the
   synthesis of how the ten chapters above 0.90 actually got there, and it changes where a round's hours go:
   autonomous passes bought **69%** of the +265 cells, systemic defect fixes **25%**, and per-chapter hand work
   **6%** for the largest share of the hours. Hand-work is still essential — every systemic fix was DISCOVERED
   by it — but its return is **the generalizable defect it exposes, not the cells it closes.** So hand-work ONE
   chapter per round as reconnaissance, scope whatever it finds to its defect class, then let the pass run.

   **Do NOT walk the 0.85-0.90 band chapter by chapter.** S6 is the worst source in **15 of those 16**
   chapters, and ch12 is the shape of the whole band: S1/S3/S9 at 1.000, S6 at 0.500. That is one problem
   wearing sixteen chapter numbers — route it through the router's signal 5 (recognition), not signal 4.

   After each round, **re-measure all 50** (`chapter_campaign.py --chapters 1-50 --phase measure`, ~9 min) to
   capture knock-on gains — Sir's explicit instruction.
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
| **S6 chronic — interleave** | ~~3, 6,~~ 15 | S6 0.38-0.59 | INTERLEAVE 4-6 per chapter | **DONE for ch15; ch3 and ch6 MOVED OUT — see below** |

### THE INTERLEAVE THREE ARE NOT THREE. Measured 2026-07-31 with `gutter_probe.py`, which is now the test.

**Only ch15 was ever reachable by geometry, and it is done.** `jp2-S06` p74's two columns are genuinely
disjoint — body line-ends at `x1<=1647`, margin column starting `x0>=1673`, a real 26px gutter — so a per-leaf
bound separates them. Swept (baseline 64/84): `0.825->64  0.780->65  0.765->66  0.755->66  0.746->66
0.740->66  0.735->65  0.730->65`. Adopted **0.746**, the MIDPOINT OF THE MEASURED GUTTER, so the bound is
right for the reason it is right rather than by tying on the scoreboard. **ch15 64 -> 66, S6 0.381 -> 0.476.**

The token diff is the reason to believe it: 65 tokens removed, every one traceable to the side-note glossing
15:13 (`Iſraelites`, `should be three`, `generations in`, `a ſtrange land`, `of Chanaan.`) or to the patristic
citations (`Theod.`, `S. Aug. Pſal 52`, `Greg. ho.`) — **and ONE TOKEN ADDED, `exceeding`.** The intruding
margin word had been sitting between `excee-` and `ding` and defeating `rejoin_break`. A bound that only
deleted could not have produced a word; the fix restored scripture as well as removing apparatus.

**ch3 AND ch6 ARE NOT A GEOMETRY PROBLEM AT ALL, and no bound can help them.** `gutter_probe` reports OVERLAP
on every one of their eight leaves, and the offending rows say why:

    ch3 p26   gaueſt me to be my fellow companion, gaue me of the tree, & I did eate. the diuel that
    ch6 p36   Noe: The eud of al fleſh is come before me, the earthis repleniſhed ratos God re-

These rows come from `pg["lines"]` — **kraken's OWN line segmentation, upstream of the page model's row
grouper.** On p74 kraken emitted the margin as 40 separate lines; on ch3/ch6 it merged margin text into the
body line itself. **No x-threshold can split words that arrived inside one line object.** This is the
"row-level column assignment is a BUILD, not a tuning" conclusion reached from the other end, and it moves
ch3 and ch6 into the R2/R3 bucket with the rest.

What ch3 and ch6 *did* lack was a chapter model at all (`chapter_model()` returned `{}` on every witness).
Those are now added and are **score-neutral**: ch3 76/96 unchanged, ch6 69/88 unchanged. Recorded as neutral,
not as a win.

### `gutter_probe.py` SWEPT ALL 914 CREDITED LEAVES — the separable set is small and now harvested

32 leaves report SEPARABLE. Most are useless: their recommended bound sits ABOVE the witness band's right edge
(S6 0.825), so wiring them would LOOSEN the band, not tighten it. **Check that before wiring any probe output.**
Four were genuine tightenings; `PAGE_OVERRIDE` is keyed by LEAF, so each serves every chapter that leaf carries:

| leaf | chapters | tokens removed | what they are | result |
|---|---|---|---|---|
| p128 | 37, 38 | 30 | the note on Iudas and Thamar's genealogy | **ch38 100 -> 101** |
| p156 | 49, 50 | 20 | `(4) Iacob ... hertofore mentioned`, `Aug. Gen.` | neutral, kept |
| p150 | 47, 48 | 19 | `The Septuagint ... contrarie ... Hebre[w] Latin text` | neutral, kept |
| p138 | 42 | **0 of 0** | the leaf contributes nothing to the body | **REJECTED** |

p138 is the one to learn from: a bound there changes no token, so it is an unevidenced entry and was removed
rather than carried. **The separable-leaf seam is now essentially worked out — do not expect more from it.**
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
| `gutter_probe.py --chapter N --source SX` | **does this LEAF have a separable margin column, and where** — SEPARABLE only when body and margin are actually disjoint, OVERLAP (with the offending rows) otherwise. A detector, not a separator: it refuses rather than guesses |
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

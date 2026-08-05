# OCR Masterplan v2 — Executive Summary & Walkthrough

Companion to `OCR-MASTERPLAN-V2.md`. Read this first; go there for evidence and detail.

---

# PART 1 — EXECUTIVE SUMMARY

## The situation in five sentences

The campaign is not a review process — it is layout analysis done by hand, and it works: the board moved from
0.8576 to 0.9374 in one session with zero regressions. Every large win was **geometry**, not recognition.
But the geometry is expressed as 364 hand-tuned numbers, and on the pages that matter most **no single number
can be correct**, because the leaves are rotated and the gap between a marginal note and scripture narrows to
four pixels. Meanwhile the failures that remain have flipped: **45% are now recognition, only 33% geometry**.
So the next phase changes both layers — polygons instead of numbers, and a real ground-truth engine instead
of hand-audited samples.

## The four decisions

**1. Replace the constants with a trained region model.**
Kraken can be trained to label regions (`MainText`, `Marginalia`, `RunningHead`, `VerseNumber`) in the same
coordinate space it already gives us. A polygon leans with a crooked page; a fraction cannot. Cost: 30–50
annotated pages — the largest human cost in the plan, and the one that retires the largest recurring cost.

**2. Build a ground-truth engine by forced alignment.**
The Douay-Rheims text is *known*. Aligning a diplomatic reference to the line images converts that into
line-level training data at scale — the path from ~6% CER to the ~2% that book-specific models reach on early
print. **Critical constraint:** `s_dismas` and `odr_com` are modern-spelling. They are excellent *scorers* and
dangerous *trainers* — training on them would teach the model to modernise ſ→s, which **improves CER by 1–2%
while destroying the entire point of the project.** Align against diplomatic witnesses only, and track a
glyph-fidelity metric so that a modernisation win can never masquerade as an accuracy win.

**3. Close the fork so campaign work compounds.**
Today campaign fixes land in `gen1_pagemodel.py` and reach the board, while the report and the rest of the
corpus are served by `qc_audit.py`, which carries **its own layout model**. That is why campaign learning does
not propagate. One geometry engine, one recognizer registry, one assembler — used by the board, the report,
and every book.

**4. Campaign mode becomes the pipeline's tuning loop.**
A chapter walk stops emitting *edits* and starts emitting *artifacts*: corrected region polygons (training
data), confirmed line ground truth (training data), and a rule or an ALERT. Each improves the engine for
every remaining book. Genesis is the calibration set; the rest of the Bible is the run.

## What we tried and it did not work

Reported because it closes doors that look open, and because the negative results cost real time:

- **Deskew retrofitted into the current stack: −5 to −25 cells.** The deskew is *correct* — it straightens
  every witness onto a common ~0.004 floor — but every constant in the stack was fitted in the skewed frame,
  so straightening the page moves it out from under its own tuning. It is built, validated, and deliberately
  **switched off**; it becomes adoptable the moment geometry is polygons.
- **Automatic bound derivation over 328 leaves: −25 cells** against the hand-tuned set. Heuristics do not beat
  364 measurements. This is the argument for a *trained* model rather than a cleverer rule.
- **A left-column detector swept over 73 leaves: −24 cells.** "The bound admits too much" has no orthogonal
  corroborator the way "the bound clips" does.

## The number that should govern priorities

| remaining failure | cells | share | addressed by |
|---|---|---|---|
| RECOGNITION — words not on the leaf at all | **172** | 45% | Stage 3 alignment + Stage 2 fine-tune |
| GEOMETRY — words on the leaf, outside the band | **125** | 33% | Stage 1 region model |
| unattributable | 86 | 22% | assembly/consensus |

## Build order

1. **Close the `qc_audit.py` fork** — unblocks everything.
2. **Annotate 30–50 pages → `ketos segtrain`** — worth ≤125 cells plus the validity class.
3. **Forced-alignment GT engine** — worth the 172 recognition cells *and* every remaining book.
4. **Re-base on CATMuS-Print, fine-tune per edition** — 6% → ~2% CER.
5. **Turn deskew back on**, once geometry is polygons.
6. **Re-target the escalation rungs** at recognition, gated on glyph fidelity.

Each step is gated and refusable on its own evidence. A below-gate component is never adopted "to unblock"
something — that is the No Silent Degradation rule applied to architecture.

---

# PART 2 — A WALK THROUGH IT, IN PLAIN TERMS

## What actually happens to a page, today

1. We pick a scan of the page and shrink it a bit. **No straightening, no cleanup.**
2. Kraken finds the text lines and reads them, preserving the archaic letters we care about (`ſ`, `u/v`).
3. We store each word as a rectangle — and **at this moment we throw away the fact that the line was
   tilted.**
4. We decide which words are scripture by asking: *is this word's left edge past 0.14 of the page width?*
   That number, and its partner on the right, is looked up from a table of 364 hand-written entries.
5. Surviving words are stitched into verses, hyphens rejoined, running heads removed.
6. Each verse is scored against four modern reference editions. Pass or fail. That is the board.

## Where that breaks, in one picture

Imagine a page of scripture with a narrow column of scholarly notes running down the left margin. Now tilt
the whole page by two degrees, as a book does when it is pressed on a scanner.

The notes column is no longer a vertical strip. At the top of the page it sits a little to the right; at the
bottom, a little to the left. **Our rule is a vertical line.** Wherever we put it, it is wrong at one end:
either it slices the first words off lines of scripture, or it lets the notes leak in.

That is not a hypothetical. On one leaf of Genesis 5, the gap between the notes and the scripture narrows to
**four pixels**, and the verse comes out reading `And Ma[God him]laleel liued` — the gloss words *God him*
wedged into the middle of the name *Malaleel*. (They land mid-verse rather than at the end because a verse is
built by stitching several lines together, so a stray word caught at each line's edge ends up in the middle of
the sentence.)

## Why we cannot just straighten the page

We tried; it is measured. Straightening works — it demonstrably makes every scan's margins tidier. But those
364 hand-written numbers were all chosen **while looking at crooked pages**. Straighten the pages and every
one of those numbers is now slightly wrong. We lose more than we gain.

It is like re-levelling a house after every door has been planed to fit the crooked frames. The levelling is
right; you just cannot do it without rehanging all the doors at once.

## What we are changing

**Instead of a number, an outline.** Train the software to draw a shape around each part of the page — *this
is scripture, this is a note, this is a running head, this is a verse number*. A shape can lean with the page.
A number cannot. Getting there costs about a day of a human tracing those shapes on 30–50 pages, and then the
software learns the pattern.

**Instead of guessing at the letters, using the answer key.** We know what the Douay-Rheims says. So we can
line the known text up against the pictures of the lines and produce thousands of labelled examples
automatically — the training data that takes the reader from about 94% accurate to about 98%.

There is a trap here, and it is worth understanding because it is counter-intuitive: **our best reference
texts would make our reader worse.** They are modern-spelling editions. If we trained on them, the reader
would learn to "correct" the old long-ſ into a modern s — and our accuracy score would *go up* while the
transcription became less faithful. So those references keep scoring, and never teach.

**Instead of two pipelines, one.** Right now the chapter-by-chapter work improves the scoreboard but not the
published report, because the report runs on a second, older copy of the layout logic. Everything gets merged
into one engine, so that improving Genesis improves every book.

## What changes about the campaign work itself

Almost nothing about *how* it feels, and everything about where it goes.

Today, walking a chapter means finding a defect and writing a new number into the table. Tomorrow it means
finding the defect and producing **the corrected outline** and **the confirmed line of text** — which become
training examples. The same investigation; the output feeds the engine instead of patching one page.

The discipline stays exactly as it is: seven steps, run the diagnostics the signal demands, audit anything
that changes text, re-measure everything, and never let "nothing to do here" end a pass. That protocol is why
this project can tell you what does *not* work — which is most of what is written above.

## The honest bottom line

We have taken the current design about as far as it goes, and we have the measurements to prove it rather
than the feeling. The next phase is less clever and more laborious: annotate some pages, build the ground
truth, and let the software learn what we have been encoding by hand. The clever part is knowing which
laborious thing to do, and the campaign work is what told us.

# FABLE COLD READ — 5 leaves, no detector, no cascade, no cache (2026-09-04)

**What this is.** Sir asked what *I* would do if handed a page of this book and told to draw and
classify every block of text, so that the answer can be captured and replicated by a locally
hosted agentic workflow. Five leaves, chosen across the three volumes and across page types,
including two that the current pipeline fails on. I looked at each plate image and nothing else.
No Surya boxes, no `bundle.json`, no gold, no cascade output were consulted before writing a leaf's
entry. Gold is compared **after**, in a separate section, and the comparison is scripted.

**What this is not.** Not gold. My coordinates are eyeballed to about ±0.01 of the page and my
labels are one reader's judgement. Sir corrects both in the Plate Tool; that verified set is the
reference. This file is the *method* record: it says how a reader reasons before any box exists,
because that is what LECTOR-as-director has to reproduce.

Regions are in `cold-read.json` as page fractions `[x0,y0,x1,y1]`, with class and a one-line
reason each. Class codes are the project's: `RH` running head · `PN` page number · `MT` main text
· `VN` verse number · `MN` marginal note · `CH` chapter head · `AR` argument · `DC` drop capital
· `SG` gathering signature · `CW` catchword · `??` abstain with cause.

---

## THE PROCEDURE I ACTUALLY FOLLOWED — the same six moves on every leaf, in this order

I did not draw a single box until move 4. That is the whole point.

**1. Orient the leaf.** Recto or verso? The page number sits in the OUTER top corner and the
signature, if any, only appears on a recto. That one decision fixes which side the fore-edge
margin is on, and therefore where marginal notes and verse numbers will be. On leaf 409 the page
number is top-right and there is a signature: recto. On 412 and 666 the number is top-left: verso.
On NT_0009 there is no page number at all, which is itself a strong signal (see move 2).

**2. Name the page kind before naming any block.** Three things told me the archetype in under a
second each: (a) does the text carry verse numbers in a gutter column — scripture; (b) is it set
in one prose measure with paragraph indents and no numbers — prelim/prose; (c) is there a centred
`CHAP.` line partway down — a chapter-break page, which will carry an argument and a drop capital
below it. NT_0009 is (b): "TO THE READER", no page number, prose paragraphs, italic citation in
the margin. 412 and 666 are (a)+(c). 409 and 749 are plain (a).

**3. Find the measure from the TYPE, not from a box.** The body column is the densest, most
regular block of roman type, and its left edge is a hard vertical line of aligned line-starts.
Its right edge is ragged by a few sorts but bounded. I located it on every leaf by the line-start
alignment alone. On 666 this took one look: the body starts at x≈0.17 with a hard edge and the
narrow left column is visibly a different, smaller fount. **The current pipeline framed this leaf
at width 0.147 — it took the note column as the body.** No reader would.

**4. Bound the body first, then everything relative to it.** Once the measure is fixed every
other class is defined by where it sits *relative to the measure*: verse numbers hug one edge of
it in a thin column; marginal notes are outside it in the fore-edge margin in a smaller fount;
running head and page number are above it; signature and catchword are below its last line. I
drew the body block first on all five leaves and then placed every other block by relation.

**5. Read a few words of every block before assigning its class.** This is where the cascade and
I part ways. I did not classify by position alone. I read. "CHAP. XXVIII." is a chapter head
because it *says* so. The italic lines under it are an argument because they *summarise* the
chapter ("Special sacrifices are appointed for euerie day…"). "Zz" and "Wwww 3" are signatures
because they are a letter-plus-numeral formula, not because they are centred at the foot. The
left-margin block on NT_0009, "Ind. lib. prohibit. regula 4", is a *citation*, a sub-kind of
marginal note, because it names a source. Position got me to a candidate class; reading confirmed
or overturned it.

**6. Check the page against itself, and abstain where the inventory has no word.** Verse numbers
must be monotone down the column; on 412 they run 15…23 then 1 2 3… after the chapter break,
which confirms the break. A catchword must match the first word of the next page; I cannot check
that here, so `CW` is a confident label with a stated unverified premise. And on 666 the far-right
column of italic Hebrew letter names ("Res. Sin. Thau. Aleph. Beth. Ghimel…") is an acrostic
apparatus for Lamentations. **The class inventory has no name for it.** I did not force it into
`MN` or `VN`. It is `??` with cause: *"acrostic letter markers; no declared class."* That is what
abstention is for, and a pipeline that silently filed these as notes would be wrong on every leaf
of Lamentations.

---

## PER LEAF — reading, then regions

### OT1-1609-B_0412 — Numbers 27–28, verso, page 380. Chapter-break page with apparatus.
Verso (page number top-left). Verse numbers in the RIGHT gutter (x≈0.82). Marginal notes in the
LEFT fore-edge margin, a long continuous commentary block from y≈0.07 to ≈0.72 in a smaller fount,
with visible paragraph breaks that I bound as separate notes where the gap is a full line. Chapter
27 ends at y≈0.42; centred `CHAP. XXVIII.` at 0.455; two italic argument lines; a two-line drop
capital `O` opening 28:1. Catchword "with" bottom right. No signature (verso).
Head line has THREE things: page number left, `NVMERI.` centre, and `Sacrifices for` right. The
right-hand one is a topical running title that continues onto the facing page; it is `RH` in this
inventory. I would not have known that without having seen the spread convention.

### OT1-1609-B_0409 — Numbers 26, recto, page 377. Plain scripture, no notes.
Recto (page number top-right, signature `Zz` at the foot). Verse numbers in the LEFT gutter.
`numbered.` top-left is the continuation of the facing page's topical running title; `RH`. One
body block, 26:29–48. Catchword "whom". This is the easy case and it should score perfectly.

### OT2-1610-P_0749 — Ezechiel 36, recto, page 741. Scripture with fore-edge notes.
Recto. Verse numbers LEFT. Two marginal notes in the RIGHT fore-edge margin at y≈0.37–0.65 and
0.67–0.92, both in a smaller fount, the second ending in an italic citation "Ephes. 5. v. 26. Tit.
3. v. 5." Signature `Wwww 3`, catchword "your". **This is the leaf the eye review flagged first
under E26, "the scripture column itself unclaimed."** The body is the most obvious object on the
page. If a detector misses it, the detector is the problem, not the page.

### NT-1582-B_0009 — "TO THE READER", prelim, recto (sig. `a iij`). Prose, no verses.
No page number. Running head `TO THE READER.` One prose measure x≈0.10–0.80 in four paragraphs;
I bound the body as ONE `MT` block because it is one text, and recorded the paragraph tops as
sub-structure — a reviewer may prefer four blocks and either is defensible, which is exactly the
kind of question the Plate Tool's ACCEPT should settle once, not per run. LEFT margin: italic
citation `Ind. lib. prohibit. regula 4.`; RIGHT margin: three summary notes. Signature, catchword.
R16.19's proxy called this leaf "no body block." It has the largest body block of the five.

### OT2-1610-P_0666 — Lamentations 3–4, verso, page 658. Chapter break + acrostic apparatus.
Verso. Verse numbers RIGHT (x≈0.85). Body verses set one per paragraph with a hanging indent,
which is why a paragraph-level detector returns many small `Text`/`ListGroup` boxes here instead of
one body — the *page* is one column; the *typography* is many paragraphs. LEFT margin: three note
blocks. `CHAP. IIII.` at y≈0.45, drop capital `H`. FAR RIGHT (x≈0.91–0.99): italic Hebrew letter
names, one per verse — the acrostic apparatus. **No class. Abstained with cause.** Catchword "It
was". The current pipeline framed this at width 0.147 (the note column).

---

## WHAT I THINK THIS SAYS ABOUT THE DESIGN

1. **Every classification I made used at least one of: reading the text, or a relation to the
   measure.** None used an absolute y-band. The cascade's constants (`HEADING_LO/HI`,
   `FOOT_CATCHWORD_REL`, `CENTRED_ABSTAIN`…) encode where things *usually* are; a reader uses
   where things are *relative to this page's body* and what they *say*. Those constants are good
   priors for a tool. They are not the decision.
2. **The measure came from type alignment, in one look, on all five leaves** — including the two
   the detector collapses. A "find the body" tool that looks for the hard left edge of aligned line
   starts would have saved R16.19 and R16.20 entirely.
3. **Recto/verso is decided first and it decides everything.** It is a two-way call from two cues
   (page-number corner, signature presence) and no current step makes it.
4. **Abstention was needed once in five leaves, for a real class the inventory lacks.** An
   inventory that cannot say "acrostic marker" will misfile every leaf of Lamentations, Psalm 119,
   and the alphabetic Proverbs. That is a `R16.5`-type finding: the class list is incomplete.
5. **The order of moves is fixed and it is not the detector's order.** Orient → kind → measure →
   body → relations → read → self-check. A detector proposes all boxes at once with no order.
   The director design is this order made executable, with detectors called at move 4.

## COMPARISON TO GOLD — see `compare_gold.py` output appended below

### Result, scripted (`compare_gold.py`, 2026-09-04)

**Against GOLD-HEADBAND on 409 + 412: 8 of 9 entries agree.** The one disagreement is a
definition, not a misread: gold labels `Sacrifices for` (the outer-margin topical running title
on 412) as `MN`; I read it as `RH`. Its facing-page twin `numbered.` on 409 has no gold row. The
class of the topical headline needs ONE ruling from Sir and then it is settled for every leaf.

**Against the live pipeline on the same five leaves**, addressing each of my regions to the
cascade box that covers it most:

| leaf | my regions | live agrees | live disagrees | live has no box |
|---|---|---|---|---|
| OT1-1609-B_0412 | 16 | 11 | 5 | 0 |
| OT1-1609-B_0409 | 7 | 2 | 5 | 0 |
| OT2-1610-P_0749 | 8 | 3 | 2 | 3 |
| NT-1582-B_0009 | 8 | 6 | 0 | 2 |
| OT2-1610-P_0666 | 14 | 5 | 4 | 5 |

The disagreements are not scattered. They are **four classes the cascade never separates from
the body**: verse numbers (`VN`, missed on all 4 scripture leaves), the drop capital (`DC`, 2/2),
the signature (`SG`, 3/3) and the catchword (`CW`, 4/5 called `MT` or missing). Every one of them
is decided by READING two or three sorts, which is the step the cascade does not have. The frame
on 749 and 666 is still wrong (measure to 0.978 / 0.975 — the note column is inside it), and
on 666 the head sits at 0.454, below the entire first half of the page. The `??` acrostic column
on 666 does not exist as a region anywhere in the live output.

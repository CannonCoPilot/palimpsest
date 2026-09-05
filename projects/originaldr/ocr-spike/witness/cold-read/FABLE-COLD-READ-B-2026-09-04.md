# FABLE COLD READ — THE B WITNESSES, 54 leaves, 18 per volume (2026-09-04)

**Why this round exists.** Rounds 1–3 read 35 leaves, and 33 of them were the `P` surrogate — a fixed
2262×3116 / 2196×2999 batch resize at ~390 ppi. The base setting `B` (S09, `holiebiblefaithf00mart*`)
is a real capture at a calibrated ~545 ppi with variable leaf sizes, and it is the set the project had
been deferring. Sir asked for the read to be redone on B, at equal counts per volume, with the 1630s
editions deferred. **Sample** `sample-B.json`: prior picks carried across by page number (OT1 B≈P+8,
OT2 B≈P+4, verified on a head-strip; drifts at both ends of each volume), NT unchanged (NT was already
B), random top-up from the B folders. Images `img-B/` at 1100 px. **Regions** `cold-read-B.json`,
written in batches of four so nothing was lost across three context clears.

Same six moves, same rule: image only, nothing else consulted before a leaf's entry was written.
Six NT and two OT1 leaves are carried verbatim from earlier rounds because they were the same B images.

---

## WHAT THE BASE SETTING CHANGED — very little at the region level

The class inventory from the P rounds held on every B leaf. Every structural finding recurred:
annotation bodies with lemmas, interleaved Psalter glosses with a lettered key column, acrostic
markers in Lamentations, ornaments as book boundaries, rules as annotation/scripture boundaries, blank
lower pages. **Resolution matters at the character level, which is SCRIBE's problem, not LECTOR's.**

## WHAT WAS NEW

| finding | leaves | what it means |
|---|---|---|
| **`LR` liturgical rubric** — "The Gospel vpõ Holy Roode day, Maij 3", "LOVV SVNDAY", "HOLY weeke" at the outer head | NT 0254, 0307 | Lectionary directions in the margin. Not commentary, not citation. A new note sub-kind, or a class |
| **Headline rule, now universal** | all 54 | Topical title (OT) and `CHA. n.` (NT) sit at the **gutter**; the page number at the **fore-edge**; the book name centred. Recto/verso decides which side is which |
| **Title page** | OT2 0011 | Four-sided type-ornament BORDER (an `OR` that is a frame, not a headpiece), six sizes of display type, motto, imprint, date, and an ink inscription across the top |
| **Approbatio** | OT2 0012 | Heading set INSIDE a woodcut cartouche; Latin italic prose; library stamps and shelfmarks OVER the type (`MS`); signatory block (`AT`) |
| **Entirely blank leaf** | OT2 1140 | No type, no rule, no marks. Side undecidable. The correct output is *blank leaf*, not an empty region list |
| **Empty table cells** | OT2 1088, 1089 | Whole columns with no ink inside a ruled table. Reportable state, like blank |
| **Signature not at the foot** | NT 0777, 0705 | Set directly under the last text line mid-page, or below a tailpiece |
| **Catchword carrying a numeral or cross** | NT 0404, OT1 1138 | "22. Concerning", "† Shadowes" — the catchword includes the next line's leading sort |
| **Numbered side-marks** | OT1 0033, 0339 | "1." "2." "3." in the margin keying a list in the text |
| **Chapter head + argument as the LAST thing on a leaf** | OT1 0982, NT 0564 | The chapter text begins overleaf; no drop cap, no body on this side |
| **Show-through of the facing page's signature/catchword** | NT 0706, OT1 0352, OT2 0279, 0674 | Mirror-image ghosts; on 0706 the recto's `Qqqq` and `THE` show through where a reader might expect this leaf's own |

## THE P→B OFFSET IS NOT A CONSTANT

Verified on page numbers: OT1 B = P+8 and OT2 B = P+4 hold **mid-volume** only. At the front, Genesis 1
is B_0031 not B_0033 (+6), and the dedication opening maps to a continuation page. At the back, the P
leaves for 4 Esdras and FINIS map to B leaves that are TABLE pages — the base copy paginates its
end-matter differently. **Correspondence between copies needs page numbers, not arithmetic.** For this
round the aim was coverage of B, so the sample stands as drawn.

## RESULT vs THE LIVE PIPELINE — only 10 of 54 leaves have a live plate

The 208-plate set holds the P surrogate for the OT, so **44 of the 54 B leaves have no live output
to compare against**. On the 10 that do (8 NT, 2 OT1):

| | n |
|---|---|
| regions | 120 |
| live label agrees | 47 |
| live label disagrees | 45 |
| live has no box | 28 |

Mislabelled, by my class: DC 6 · IX 6 · BT 5 · VN 5 · CR 4 · OR 3 · AN 3 · RH 3 · RL 2 · SG 2 · CW 2.
Same shape as every round. The index leaves score 0 of 10 and 1 of 12: the two-column layout is
invisible to a single-measure frame.

⚠️ **The live bundle cannot score the OT base setting at all.** Rebuilding it on B is stage-1 support
work under the director design and is not scheduled; the B gold will be scored against the director,
not against the cascade.

## FOR THE CLASS REGISTER

Add `LR`. Add the *frame* sub-kind of `OR` (the title-page border). Add *blank leaf* and *empty cell*
as first-class outputs beside *blank lower page*. Confirm `MS` covers stamps and shelfmarks as well as
pen marks. Everything else in the register stands, now with B exemplars available for every class.

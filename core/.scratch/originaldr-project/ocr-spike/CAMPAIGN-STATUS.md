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

| | |
|---|---|
| cells >=0.90 / ACHIEVABLE | **4,853 / 6,116 = 0.7935** |
| cells >=0.90 / raw total | 4,853 / 6,120 = 0.7930 |
| **CHAPTERS CLOSED** | **2** — chapters 1 and 16 (sentinels; re-measure them on EVERY change) |
| cells blocked by an absent reference | **4**, in one chapter (was 704 over 16 chapters) |
| tests | **188 green** (`../ocr-venv/bin/python -m pytest tests/`) |
| commits | 28, **nothing pushed** — the hold stands |

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

1. **SIZE THE THREE S6 CAUSES SEPARATELY** — still not done, and the prerequisite for any ninth apparatus
   attempt. S6 is now plainly the dominant weakness: 0.1471 (ch44), 0.2258 (ch47), 0.25 (ch23), 0.2727 (ch6),
   0.3333 (ch13), 0.381 (ch15) against S9 at 0.7-1.0 in the same chapters.
   | cause | example | remedy class |
   |---|---|---|
   | annotation prose sharing rows with scripture on a MIXED leaf | ch22 p88, ch12 | within-leaf column separation — UNBUILT |
   | missing leaves / unlocalized verses | ch44 (8 verses with NO span; 4 leaves vs 5 elsewhere) | localizer coverage, upstream |
   | edition divergence 1635 vs 1609 references | CHAPTER-WORKFLOW | collation judgement; no recognizer closes it |
   Every one of the EIGHT pinned separation attempts was aimed at the AVERAGE of these three, which is why each
   convinced on its examples and failed on the population.
2. **DEPTH-FIRST CHAPTER WORK.** Closest to closure now, cells short: **ch8 (7)**, ch12 (10), ch20 (11),
   ch22 (12), ch33 (12), ch18 (13), ch48 (13), ch25 (14), ch45 (14), ch2 (15). Follow CHAPTER-WORKFLOW phases
   0-7. After each chapter closes, **re-measure all 50** (`chapter_campaign.py --chapters 1-50 --phase measure`,
   ~5 min) to capture knock-on gains — Sir's explicit instruction.
3. **The s_dismas re-parser still fails 8 chapters it ought to reproduce** (2, 16, 19, 26, 31, 35, 36, 44 —
   chapter 44 now reaches 28 of 34, chapter 31 only 6 of 55). Each failure is a parse defect the SHIPPED reads
   may also carry, and chapter 30 proved those are invisible to the count test. Fixing them lets the re-parser
   supersede the original parser wherever it validates. **Use the `HOLE:` criterion already in `--verify`.**
4. **odr_com genesis 23:20 — ACQUISITION.** Report it; do not patch it. If a second odr-com surface exists
   (a print edition, a different page), that is the route.

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

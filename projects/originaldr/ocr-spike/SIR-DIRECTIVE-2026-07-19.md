# Sir's reOCR-infra Directive — AUTHORITATIVE SPEC
Recovered verbatim from prior session transcript (072e6880…) line 3223, ts 2026-07-20T01:57:13Z
(= evening of 2026-07-19 Denver). Re-persisted 2026-07-19 post-/clear because this spec was the
single hardest thing to recover. If context clears, THIS FILE is the source of truth for D/E/F.

## 1. Source curation (keep * / drop X) — jp2 always
Curated set = **S1, S3, S4, S6, S8, S9**. (drop S2,S5,S7,S10,S11,S12,S13,S14,S15)
- A: S1 — OT1/OT2/NT (1609/1610/1582)
- B: S3 — OT1/OT2 (1609/1610); S8 — NT (1582)
- C: S9 — OT1/OT2/NT (1609/1610/1582)
- D: S4 — NT (1633); S6 — OT1/OT2/NT (1635/1582). **DROP S6 NT pages** (repeat of 1582, dup).
- CONTRADICTION to flag for Sir: one earlier line says "S12–S15 present and should be included in
  OCR testing", but the explicit keep/drop table marks S12–S15 as **X (drop)**. Scratchpad resolved
  = DROPPED. Honoring DROPPED; surface in completeness review.
- Remedial-needed before inclusion: **S9 spotty all the way across Psalms** → (C) remedial preproc.
- Gaps Sir flagged: S5 has no diplomatic OCR; **S9 OT2 never OCR'd** → being fixed NOW by the
  running kraken job (cache sources/our-ocr-diplomatic/jp2-S09ot2/, ~1150 pp).

## 2. Source Inclusion Rules — Gold Transcription building
1. All Bible sources must be a source for ≥1 selected page.
2. All selected pages represented by ≥1 source.
3. Generated text from the source page scans (Rules 1&2 set) = draft GT.
4. Corrections by Jarvis' own visual analysis for EVERY selected page.
5. Corrections using every source page, or the higher-res/clearer source covering that page.
6. GT + page scans presented in the transcript editor tool for user review.
7. User's submitted corrections = final round to Gold standard.

## 3. Report rules (E) — "OriginalDR re-OCR statistical report" — VERBATIM
1. All Bible sources included as a source for EVERY book they contain.
2. V3 PASS/FAIL heatmap must show a **row for every source that does or should contain the book**.
3. The frontmatter and backmatter of each of the 3 volumes each constitute a **book** — included
   in full just as Genesis, Psalms, Matt, John, 2 John, Apocalypse.
4. Every source's OCR without ≥90% GT match **at every chapter (by % of verses matching >90%)** → flag reOCR.
5a. Every source's OCR without ≥90% GT match **across all verses combined** → flag reOCR.
5b. Every source's OCR without ≥90% GT match **across all apparatus combined**
    (chapter headings, arguments, summaries, annotations, footnotes, marginalia) → flag reOCR.

## 4. Front/Back matter as "books" (D) — full section lists
Each section below = one matter-"book" (GT + a report row). (✅ = have GT; ? = verify mapping; ∅ = MISSING)
### OT1 Frontmatter
- Title Page ✅ matter-ot1-title
- Approbatio ✅ matter-ot1-approbatio
- "To the Right Wellbeloved" ? (matter-ot1-preface — verify this IS the dedicatory epistle)
- "The Summe and Partition" ∅
- "The Summe of the Old Testament" ∅
- "Of Moyses" ∅
- "The Argument of Genesis"* ∅  (*not strictly frontmatter; placed before Signification of Markes)
- "The Signification of the Markes" ∅
### OT1 Backmatter
- "A Brief Recapitulation" ∅
### OT2 Frontmatter
- Title Page ✅ matter-ot2-title
- Approbatio ∅ (no matter-ot2-approbatio yet)
- "Proemial Annotations" ∅  (matter-ot2-preface-psalms may be related — verify)
- "Concerning Interpretation" ∅
### OT2 Backmatter
- "The Continuance of the Church (1635)" ∅
- "A Table of the Epistles" ✅ matter-ot2-table-epistles (added 2026-07-19)
- "An Historical Table" ∅
- "A Particular Table / A Table of the Chiefe Contents (1635)" ∅
- "Censura triûm Theologorum" ∅
- "Faults Escaped in the Printing (1635)" ∅
- "Extraict du Privilege du Roi (1635)" ∅
- (matter-ot2-backmatter ✅ exists — verify which of the above it is)
### NT Frontmatter
- Title Page ✅ matter-nt-title
- "The Censure and Approbation" ∅
- "The Preface to the Reader" ✅ matter-nt-preface
- "The Books of the New Testament" ? (matter-nt-table — verify)
- "The Signification or Meaning" ∅
- "The Summe of the New Testament" ∅
### NT Backmatter
- "The Explication of Certaine Words" ∅
- "A Table of Certaine Places" ∅
- "A Table of the Epistles" ∅ (NT one, distinct from OT2's)
- "An Ample and Particular Table" ∅
- "Faults Escaped in the Text" ∅

## 5. Reference-based coordinate aligning — DONE
s_dismas & odr_com for verse/sentence/paragraph/chapter/book coords; Janvier fallback where absent.
Rehabilitate every OCR text to canonical coords (trim+join) BEFORE any OCR-v-Any comparison.
= align_coords.py, FOLDED into qc_audit.realign_vmap (default-on). ✅

## 6. Additional layout-mode GT pages (from sampling)
Add GT for any sampled pages revealing new layout modes; own thorough visual analysis; add to editor
tool. DONE: 2esdras(genealogy), proverbs(running-poetry ✅), lectionary(table ✅);
colossians(greek-margins) 🟡 in flight.

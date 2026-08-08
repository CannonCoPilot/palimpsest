# OriginalDR — Development Roadmap

The executable counterpart to `OCR-MASTERPLAN.md`. The plan states *what must be true*; this file states
*what is built, in what order, and how each step is verified*. Every step names its deliverable, its
acceptance test, and the plan section it discharges.

**Current phase: pre-initialisation — Gate 0 (corpus).** No transcription work begins until Gate 0b and 0c
are satisfied for the leaves concerned (§2).

---

## Status index

**Sections appear below in the order they were written, which is not numeric order** — R6 and the dissolved
R3.5 sit between R4 and R5, because R5 was folded down from the former step 4 after R6 was drafted. The file
is the execution reference, so the index rather than the file order is authoritative for *what is open*.
Renumbering was considered and rejected: step ids are cited from the Masterplan, the companions, four
guards' comments and every devlog entry, so the ids are load-bearing and the ordering is not.

| section | subject | status |
|---|---|---|
| R0 | Witness identity and stable addressing | **COMPLETE** (R0.1–R0.5) |
| R1 | Physical leaf inventory — Gate 0b stage 1 | **COMPLETE** (R1.1–R1.6) |
| R2 | Structural inventory — Gate 0b stage 2 | **OPEN — NEXT.** Nothing built (R2.1–R2.4) |
| R3 | Cross-source leaf mapping — Gate 0c | **OPEN.** Nothing built (R3.1–R3.4) |
| R3.5 | NT's 36-leaf difference | **DISSOLVED** — the number was malformed. R3.5b, R3.5c live |
| R4 | Bibliographic completion — Gate 0a residue | **PART.** R4.1d/R4.2/R4.3/R4.4 done; R4.1e, R4.2a, R4.5, R4.6 open |
| R5 | Raster policy | **PART.** R5.1 not built; R5.2 has no proven negative |
| R6 | `S06` frontmatter/backmatter collation | **PART.** R6.1–R6.3a, R6.5 done; R6.3b/c, R6.4-remainder, R6.6a–d open |
| R7 | Ground truth read from inadmissible rasters | **OPEN — 48 of 51 files.** R7.5 defect is **LIVE** |
| R8 | `F`'s New Testament is the 1633 edition | **PART.** R8.1, R8.2, R8.4, R8.4a, R8.5, R8.8 done; R8.3, R8.4b, R8.6, R8.7 open |

### Open-items register

Maintained here so that "what is left" is answerable without reading 600 lines. **This register is
authoritative over prose elsewhere in the file**; where a paragraph and this table disagree, the table is
right and the paragraph is a bug to be fixed.

**OPEN** — R2.1 · R2.2 · R2.3 · R2.4 · R3.1 · R3.2 · R3.3 · R3.4 · R3.5b · R3.5c · R4.1e · R4.2a · R4.5 ·
R4.6 · R5.1 · R5.2 (negative test not proven) · R6.3b · R6.3c · R6.4-remainder (OT2/1610 prelims, endmatter
Tables, body rewording) · R6.6a · R6.6b · R6.6c · R6.6d · R7.1 · R7.2 (1 of 4 done) · R7.3 · R7.4 ·
**R7.5 (live defect)** · R8.3 · **R8.4b** · R8.6 · R8.7

**DONE** — R0.1–R0.5 · R1.1–R1.6 · R4.1d · R4.2 · R4.3 · R4.4 · R6.1 · R6.2 · R6.3 · R6.3a · R6.4 (tome 1) ·
R6.5 · R8.1 · R8.2 · R8.4 · **R8.4a** · R8.5 · **R8.8**

**DISSOLVED** — R3.5 (body retained, marked not to be executed)

⚠️ **Four "DONE" marks are narrower than they read**, and are spelled out where they occur rather than
here: R4.2 is done as an explicit *NOT ESTABLISHED* verdict, not as a repository found; R6.4 is done for
tome 1 only; R8.4 verified 11 of 12 witnesses and **named the twelfth unverifiable** rather than assuming it
sound; **R8.4a verified the foot criteria at ONE matched page per setting**, where the head pass used three or
more — R8.4b is the remainder and stays OPEN. A register that flattened these to "done" would be doing the
laundering it exists to prevent.

---

## R0 — Witness identity and stable addressing

**Discharges** §1.1. **Status: COMPLETE.**

| # | step | deliverable | acceptance |
|---|---|---|---|
| R0.1 | Canonical witness registry | `witness/witnesses.py` — sigla, volume, year, role, repository, source path | registry leaf counts equal on-disk counts for all **11 files** |
| R0.2 | Stable witness tree | `sources/witnesses/<VOL>/<WID>/leaves` symlink farm + `MANIFEST.json` | every witness path resolves; leaf counts match registry (**12/12**) |
| R0.3 | Naming convention documented | §1.1 "Addressing and sigla" | a reader can map any legacy id to a witness id and back |

**Design note — symlinks, not copies.** Copying the JP2 packages would duplicate ~11 GB and create a second
artefact that can drift from the first. A symlink gives the stable path without a second copy, and a broken
link fails loudly where a stale duplicate would fail silently.

**R0.4 — reopened by §1.2: the tree points at renders for `F` and `X`.** The farm links every witness to its
JP2 package, which is correct for the six institutional captures and **wrong for the four `S01`/`S08`
files**, whose JP2s are IA renders of an uploaded PDF. Structural work is unaffected — a render preserves
page content and page order, so the R1 leaf inventory and the R2/R3 collation stand — but **no pixel-level
measurement, training crop or CER evaluation may be taken through those links.**

| # | step | deliverable | acceptance |
|---|---|---|---|
| R0.4 | Primacy recorded per witness | `witnesses.py` gains `primary: "jp2" \| "pdf"` and, for `pdf`, the page-extraction path | every witness declares its primary artefact; the field is sourced from the IA `source`/`original` chain, not guessed |
| R0.5 | Render guard | load-time assertion at the pixel-consuming entry points | a `primary: "pdf"` witness accessed through the JP2 link **raises**, proven by a negative test |

**R0.5 needs the negative test for the same reason R5.2 does.** A guard that has never rejected anything is
not known to work — and this is precisely the class of error that produced the 3334 × 4684 misreading, so
the guard exists to make that error loud rather than plausible.

---

## R1 — Physical leaf inventory (Gate 0b, stage 1)

**Discharges** §2 Gate 0b, first half. **Status: COMPLETE.**

| # | step | deliverable | acceptance |
|---|---|---|---|
| R1.1 | Per-leaf physical classifier | `witness/inventory_leaves.py` → `TEXT / BLANK / SPARSE / PLATE / BINDING` per leaf | runs over all 10 witnesses; one JSON per witness |
| R1.2 | Witness-relative thresholds | saturation judged against the witness's own distribution | a uniformly sepia rehost is not misread as 42 colour plates |
| R1.3 | Leaf-count reconciliation | §1.1 table: every leaf-count difference attributed | each difference expressed as binding + blanks + duplicates + supplied + genuine textual difference |

**Design note — why thresholds must be relative.** Absolute saturation cannot separate a marbled endpaper
from a warm-toned scan: a sepia rehost saturates as strongly as a colour plate. What marks a plate is
standing out *against its own book*, so the cut is taken from each witness's own distribution.

**R1.4 — the same argument applies to ink, and applying it to saturation alone was a bug.** The first
reconciliation reported **zero** lead, trail and interior blanks for all three `F` witnesses, which reads
as the finding *"the rehost stripped its blanks"*. It is not a finding. A contrast-boosted rehost raises
its background everywhere, and the `F` ink floor is **0.196** against a BLANK cut of 0.010 — above the `B`
witnesses' **median** of 0.25. `BLANK` and `SPARSE` could never fire on those witnesses, so the zero was
the threshold's shape, not the book's.

| # | step | deliverable | acceptance |
|---|---|---|---|
| R1.4 | Resolvability check before classification | `label()` tests each witness's ink floor **against the cut it is about to apply** and emits `TEXT?` where blanks are indistinguishable | the four re-uploads report **UNRESOLVABLE**, the six genuine captures are unaffected |
| R1.5 | Summaries account for every leaf | per-kind counts printed for kinds *present*, with `sum == n` asserted | a new kind cannot drop out of the summary while `n` stays correct |
| R1.6 | Offline relabelling | `witness/relabel.py` re-applies `label()` to stored features | a threshold revision costs seconds, not a ~40-minute image pass over eleven witnesses |

**The criterion had to be corrected once, and how it failed is worth keeping.** The first version asked
whether the ink floor was a small fraction of the *median*, and that split the three `F` witnesses
inconsistently — `OT1` tripped at 0.196/0.350 while `NT` passed at 0.193/0.409 — although not one of them
has a single leaf below ink 0.06. The median is a property of the *text*, so a ratio against it measures
contrast rather than detectability. The question is only ever **"could a blank leaf be caught by the cut
about to be applied?"**, so the floor is compared to `BLANK_CUT`. That separates the corpus exactly:

| class | ink floor | witnesses |
|---|---|---|
| genuine capture | **0.0000** | `B` ×3, `P` ×2, `R` |
| re-upload | **14–20× the cut** (0.141–0.196) | `F` ×3, **`X`** |

**`NT-1582-X` was the fourth, and it was not predicted** — the check found it. And `NT-1633-R` sits in the
genuine class *because* its original was acquired (R4.4), so this is a fourth corroboration of the primacy
split of §1.2, arrived at from an unrelated measurement.

**Why this is R1.4 and not a footnote.** Zero is a measurement; *unmeasurable* is not, and the two must not
print the same. The failure mode is the one this project keeps meeting — a derived or degraded artefact
returning a well-formed number that reads as evidence. R1.5 exists because the summary enumerated a fixed
list of kinds, so `TEXT?` would have vanished from the totals while `n` stayed right: the unresolved leaves
would have looked accounted for.

**Consequence for `F`.** This is a **second and independent limit** on these witnesses, and it is narrower
than the resolution one: it bars them from **completeness** questions specifically. They carry **page
order**, but whether a leaf is wanting, blank or supplied is not recoverable from them, because their
processing raises the whole leaf and no blank can be distinguished from a lightly-printed one.
Completeness rests on the `B` and `P` witnesses. Note this is a limit on *these files*, not the
withdrawn "structure only" verdict on the copies (§1.1a).

---

## R2 — Structural inventory (Gate 0b, stage 2)

**Discharges** §2 Gate 0b, second half. **Status: NEXT.**

| # | step | deliverable | acceptance |
|---|---|---|---|
| R2.1 | Signature reader | OCR the signature line (`A ij`, `Aaa 4`) from the foot of each recto | ≥95% of rectos yield a parsed signature on the base exemplars; failures listed, never guessed |
| R2.2 | Printed-page-number reader | OCR the head of each leaf | ≥95% on the base exemplars; both readers abstain rather than emit a low-confidence value |
| R2.3 | Collation model | expected gathering structure per volume, derived from observed signatures | the derived collation reproduces the observed sequence with no unexplained gaps |
| R2.4 | Defect report per witness | wanting / duplicated / misbound / made-up leaves, each named | every leaf either fits the collation or appears in the defect report — **no leaf unaccounted** |

**Sequencing note.** R2.1/R2.2 are OCR tasks on a tiny, highly regular target (a short line in a fixed
position), not the edition's recognition problem. They must not wait on the recognizer, and their failures
must abstain: a mis-read signature would corrupt the collation that everything else is checked against.

---

## R3 — Cross-source leaf mapping (Gate 0c)

**Discharges** §2 Gate 0c.

| # | step | deliverable | acceptance |
|---|---|---|---|
| R3.1 | Leaf key | `(volume, printed page, signature, side)` as the addressing key — **never file index** | key is stable across witnesses by construction |
| R3.2 | Correspondence table | every admitted leaf → its leaf index in each witness of that volume | 100% of admitted leaves addressable in every witness that has them |
| R3.3 | Absence register | leaves present in one witness and absent in another, with cause | each absence classed: not in copy · not scanned · dropped in derivation |
| R3.4 | Verification by image | sampled correspondences confirmed by correlation | sampled pairs correlate far above the unrelated-page baseline |

**Why this cannot be skipped or deferred.** §1.4 established that leaf indices do **not** correspond between
files of the same volume — the NT witnesses differ by up to 47 leaves before any text is compared. Until
R3.2 exists, "the same page in another witness" is not a well-formed request, and no collation of readings
is possible.

---

## R4 — Bibliographic completion (Gate 0a residue)

Runs in parallel with R2/R3; it constrains citation, not imaging.

| # | step | deliverable | acceptance |
|---|---|---|---|
| R4.1 | STC/ESTC verification | STC and ESTC numbers for all copies, cross-checked against held OCLC numbers | each number resolves at an authority; **unverified leads are recorded as leads, never promoted** |
| R4.2 | Repository for `F` and `X` files | repository + shelfmark, or an explicit NOT ESTABLISHED | no field silently blank — **DONE**, see below |
| R4.2a | Physical copy behind the three `F` volumes | repository + shelfmark, by a route other than catalogue metadata | a named copy, or a published statement of what was tried and why it failed |
| R4.3 | Identify `NT-1582-X`'s supplied leaves | the fourth source of the Censure and Preface p.1 | source named, or its candidate set narrowed and published |
| R4.4 | **Acquire `newtestamentofie00engl`** — `NT-1633-R`'s original digitisation | the Princeton capture in continuous tone, replacing the binarised re-upload | **DONE** — 778 leaves, NCC 0.990 vs the superseded render, 190–228 grey levels |

**R4.4 blocked any *reading* from `NT-1633-R`, and is now discharged** (§1.2a). The witness previously held
was a user re-upload of IA's MRC PDF whose text layer is a **1-bit JBIG2 mask** — and `NT-1633-R` exists in
the corpus precisely to supply the Censure and Preface leaves, the two with no genuine 1582 reading
anywhere (§1.4). The original was on IA under a different identifier with full Princeton provenance, so
this was an acquisition rather than a research problem; `witnesses.py` now resolves `NT-1633-R` to it and
keeps the superseded package addressable as `superseded` for audit.

**R4.2 is discharged** (§1.3). All four items were traced to their IA records and read: every one is a
**user upload to `folkscanomy`** with no `scanningcenter`, `contributor`, `call_number` or
`external-identifier` — so no repository is recoverable from the catalogue, and the field is recorded
**NOT ESTABLISHED** with the evidence for that verdict rather than left blank. `NT-1582-X` is the exception
that proves it: its repository *is* known — **BPL G.404.12** — but by identity with `NT-1582-B`, since its
uploaded PDF carries that capture at that capture's own raster (§1.2). It is provenance inherited, not
provenance of its own.

**R4.2a is what remains, and it is deliberately not folded back into R4.2.** The digitisation provenance of
the `F` set is settled (`fatimamovement.com`, uploaded 2014-07-28); the *physical copies* are not, and the
catalogue route to them is exhausted. Recording that as done would convert a real gap into a false
closure. Because `F` is barred from glyph-level work by its resolution (§1.2), this blocks **citation**,
not imaging — but it stays **OPEN**.

**R4.3 is DISCHARGED, and not where it was expected.** The fourth source is the **1582 setting witnessed by
`NT/S06`** — the file the plan had excluded as "a modern facsimile" (§1.1, §1.4). Block-registered
correlation gives +0.424 / +0.398 on the matching pair against 0.000–0.036 on every cross-pairing, and the
visual agreement is line-for-line including the S. Augustine quotation absent from the 1633 setting.

**R4.1 — the ESTC authority is still down, but the route that worked was never the ESTC.** `estc.bl.uk`
redirects to CERL and the ESTC beta returns **`no such index [estc]`** for every query; USTC 404s, Virginia
is JS-only, Jisc 403s, LC's `search.catalog.loc.gov` 403s. Every *catalogue-interface* route is exhausted.
**The numbers came instead from the holding library's own MARC, which we already held locally** — see R4.1d.
**One institutional authority is in hand; the two-authority rule stands, so nothing is promoted into §1.3.**

| # | step | deliverable | acceptance |
|---|---|---|---|
| R4.1a | Automated ESTC retry | a scheduled probe of the CERL ESTC index that reports when it answers | the probe distinguishes "index down" from "record absent"; a passing probe re-opens R4.1 automatically |
| R4.1b | Fallback authorities, in order | Folger *Hamnet* (the STC authority of record) → USTC → Bodleian/Oxford SOLO → Harvard HOLLIS | a number is promoted only when **two independent authorities agree**, and the S102419/S102491 split is resolved explicitly, not silently picked |
| R4.1c | Record the disagreement, not just the answer | concordance carries the rejected variant and why | a later reader can see that a one-digit variant existed and was adjudicated |
| R4.1d | **Holding-library MARC via the IA item record** — DONE, and this is the route that worked | `curl -sL https://archive.org/metadata/<id>` → `metadata.references` carries the contributing library's own catalogue citations | numbers are read from a named institution's MARC, not from a dealer or auction listing |
| R4.1e | **Authority #2** — a second *institution's* record | Princeton's MARC for `holiebiblefaithf01engl` / `thenewtestamento00rhei` by the R4.1d route, or OpenLibrary JSON, or a Folger/Bodleian record | two institutions, independently, before any number enters §1.3 |

**R4.1d result — Boston Public Library's own MARC**, via `metadata.references` on the IA items:

| witness set | IA identifier | citations, verbatim from BPL's MARC |
|---|---|---|
| NT 1582 | `nevvtestamentofi00mart` (BPL, call no. `BS2080 1582`) | `ESTC S102491; STC (2nd ed.), 2884; Darlow & Moule (2001 reprint ed.), 134; Herbert, A.S. Engl. Bible, 177; Allison & Rogers. Engl. Counter-Reformation, II, 173` |
| OT 1609–10 | `holiebiblefaithf00mart_0` (BPL, call no. `BS180 1609`) | `STC (2nd ed.) 2207; ESTC S101944; Darlow & Moule 300` |

Both strings re-fetched and diffed against the live IA records on 2026-08-07 before being written here. The
first transcription of the NT row, made from working notes, had silently normalised the punctuation and
abbreviated *Herbert, A.S. Engl. Bible* and *Allison & Rogers. Engl. Counter-Reformation* — small, but a
row labelled **verbatim** that is not verbatim is the same defect class as a stale count. Fetch, don't recall.

⇒ **The one-digit split is adjudicated: it is `S102491`, not `S102419`.** R4.1c is satisfied on this point by
recording *why*: `S102491` comes from the holding library's catalogue record for the very copy we hold as
`NT-1582-B`, while `S102419` traces to dealer and auction listings — secondary descriptions of other copies.
The rejected variant is kept here deliberately so a later reader can see it existed and was decided.

**Method note, and the reason R4.1 sat "BLOCKED EXTERNALLY" longer than it needed to.** The block was real
but mis-scoped: it was a statement about *ESTC's search interface*, and it was allowed to stand for "the
bibliographic numbers are unobtainable." The numbers were sitting in an IA field we had already downloaded
for other purposes. **An external blocker names one route; it does not bound the space of routes** — the same
shape of error as R4.5's exclusion-by-description.

**Why two authorities and not one.** The failure mode here is not "no number found" but "a plausible number
found and propagated." A one-digit difference between two live-looking identifiers is precisely what a
single source cannot catch, and a misattributed ESTC number in a documentary edition is a defect that
survives every later correction.

| # | step | deliverable | acceptance |
|---|---|---|---|
| R4.5 | **Re-examine every excluded file before any "survives nowhere" claim** | each exclusion carries measured grounds — edition, date, printer, raster, and what its prelims contain — not a one-line description | no file is excluded on a description that has not been checked against its own leaves; `S06` is the worked example |
| R4.6 | Ask the Fatima Movement for a higher-resolution capture | a direct enquiry, and its answer recorded either way | if a higher-resolution capture of the `F` copy exists, `F`'s role changes from low-resolution to full witness (§1.1a); if not, the negative is recorded so it is not re-asked |

**R4.5 exists because an exclusion is a claim.** `S06` was set aside as "a modern facsimile, not a witness
to the setting." Its OT is a **1635 Rouen Cousturier** printing, its NT a **1582 Rheims Fogny**, and its
prelims hold the only genuine 1582 Censure and Preface p.1 in the corpus. The description was wrong about
the date, the printer and the nature of the artefact, and because it was never re-tested it produced a
false "no genuine 1582 reading survives anywhere" verdict at the single most consequential point in the NT.
**An exclusion inherits the evidential standard of any other claim**, and the cost of a wrong one is
silence rather than error — which is why it must be checked rather than trusted.

---

## R6 — `S06` and the frontmatter/backmatter collation

`S06` is **excluded from the verse text and admitted for prelims and endmatter** (§1.1). Its value is that
it holds two settings the rest of the corpus does not: a **1635 Rouen OT** and a **1582 Rheims NT** whose
frontmatter is complete.

| # | step | deliverable | acceptance |
|---|---|---|---|
| R6.1 | Address `S06`'s two halves separately | registry entries `NT-1582-M` (leaves 2072–2871) and, if wanted, `OT-1635-M` (leaves 0–2070) | the OT/NT boundary at the blank leaf 2071 is asserted, not assumed; each half declares its own edition |
| R6.2 | Extract the 1582 prelims | `NT-1582-M` leaves 2072–2076: title, Censure, Preface pp. 1–3 | each leaf named and its setting identified against `S04` (1633) and `S08` (supplied) — **DONE**, see below |
| R6.3 | **Transcribe the Censure and Preface p.1 from `M`** | the two leaves the base exemplar lacks, as 1582 readings | transcribed with `M` named as the supplying copy and its ~380 ppi bitonal raster recorded as the limiting factor — **DONE**, see below |
| R6.4 | Collate 1635 prelims against 1609/1610 | a difference report: what the second edition adds, drops and rewords in Approbatio, Preface, Tables, errata | every difference cited to a leaf in each edition; **no difference asserted from memory of the text** — **DONE**, report at `COLLATION-1635-vs-1609.md`; OT2/1610 prelims outstanding |
| R6.5 | Record the 1634 privilege | *Extraict du Privilege du Roy*, Paris, 3 Aug 1634, to Jean le Cousturier, ten years, to reprint *"de l'edition de Laurens Kellam Imprimeur de Douay"* | quoted verbatim from leaf 2070 with a transcription of the French — **DONE**, `ground-truth/matter-ot2-privilege-du-roi.json`, re-read on the primary raster; see below |

**R6.5 was already transcribed on 2026-07-20 — and the transcription was made on a derived image.** The
existing file read leaf 2070 from the `S06` **jp2** at 5100×6601. The per-item primacy finding later
established that `M` is **PDF-primary**: the PDF holds the real ~2955×4206 CCITT and the jp2 is a **1.73×
render of it**. The 2026-07-20 word zooms at 5× were therefore operating at roughly **8.6× the real
raster**. The transcription has been re-read from the embedded CCITT XObject directly.

**Three readings change, and two of them are the very spans the original file flagged as unresolvable.**

| line | was | now | how it was settled |
|---|---|---|---|
| 3 | `d. Roüen` | **`de Roüen`** | the `d`→`R` gap is **46 px**; word spaces on that line are 27/29/27 px and the line's own `e` is 22 px wide (22+27≈49). The gap holds an `e` *plus* a space. **Negative control**: a real period on this page is **10×12 px**; the mark in the gap is **3×2 px**, 1/25 the area, sitting at the baseline where an `e` bowl bottoms out. It is not a period — the `e` failed to ink |
| 5 | `Marchans` | **`Marchands`** | between `n` and `s`: a baseline blob 8×7 px **plus a 6×42 px full-ascender stroke**. An i-height stroke cannot reach ascender height; this is a `d`'s ascender and the foot of its bowl, bowl failed. Agrees with singular `Marchand` on line 2 |
| 9 | `Donnees` | **`Données`** | not previously flagged; the acute is solidly inked and well clear of the letter |

**This is the third instance of one defect class, and the mechanism is now explicit: upscaling manufactures
the feature the call depends on.** Interpolation rounds a 3×2 speck into a plausible point (`d.`) and smears
a failed `d` bowl into a point-plus-stroke (`Marchans`). In R6.6 it closed the gap between two `v` sorts and
produced a `w`. In each case **the rule was right, the observer was careful, and the image was derived**.
The prior observer here even enumerated the correct alternative — "or the word could be `de Roüen` with a
broken `e`" — and could not choose, because the evidence that chooses had been interpolated away.
⇒ **Before any glyph-level call, check `PRIMARY` for the witness.** `pixel_source()` already enforces this
for the five renders; the lesson is that a *transcription* must consult it too, not only a pipeline.

Backups retained as `*.pre-primary-raster`, on the R6.6c principle: the backup records what an observer
saw, the current file records what a measurement produced.

**R6.4 is DISCHARGED for the first tome; the report is `COLLATION-1635-vs-1609.md`.** Headline results:

- **Section for section, note for note, the 1635 adds nothing and drops nothing.** The adds/drops question
  was closed for the *whole* Preface by collating its **marginal note sequence** — ~24 notes corresponding
  one to one in the same order — rather than by a word-by-word read of 22 pages.
- **The Approbatio is reprinted verbatim, retaining `Duaci 8. Nouembris. 1609`.** The Rouen edition does
  not re-approve itself; the approbation dates the *text*, not the book.
- **What changed is orthography and typography** — dominated by `-ie`→`-y`, dropped terminal `-e`,
  increased capitalisation, and `VV`→`W` — plus one silent correction of a first-edition error
  (`to large`→`too large`).
- **It is not a modernisation programme**, and several changes run the other way (`AVTHOR`→`AVTHOVR`,
  `Goſpel`→`Ghoſpel`, `authors`→`authours`, `dearly`→`dearely`). The `ai`/`ay` digraph moves in **both**
  directions within the same edition.
- **The 1635 founts have a `W` sort and the Douai founts do not** (`VVELBELOVED` → `WELBELOVED`), and the
  1609 prose is itself mixed on a single page at ~545 ppi. This corroborates R6.6 on an admissible raster.

**Registered for this step**: `OT-1635-M` (package pages 0–2070). It is **not** a witness to either OT
tome's setting and may never supply an OT verse reading — it exists so a difference can be **cited to a
leaf** rather than described.

**Outstanding and named**: word-level rewording in the bodies beyond the collated samples · the endmatter
Tables · **the OT2/1610 prelims**, which sit further into `M`'s package and are not yet located. None of
these blocks the edition — `M` supplies no verse reading, so this is scholarly yield, not critical path.


**R6.4 is the deliverable that answers "what differs between the editions."** The privilege at R6.5 is what
makes it interesting rather than merely descriptive: the 1635 edition states on its own back matter that it
reprints the Kellam Douai edition, so **every difference in its prelims is a deliberate editorial act by
the Rouen house**, not an independent transmission. That makes the difference report evidence about how the
edition was understood in 1635, and it is the only such evidence the corpus contains.


**R6.2 and R6.3 are DISCHARGED, and doing so exposed a defect in existing ground truth.**

`witness/extract_pdf_leaves.py` extracts leaves from a PDF-primary witness by pulling the **embedded
XObject** rather than rasterising the page, with the slice offset read from the registry in one place. All
five prelim leaves are named: title page · **Censure and Approbation** · Preface p. 1 · two Preface
openings. The Censure carries the two-line heading, no headpiece and no *"of the first Edition"* subtitle
— the 1582 setting, exactly as the correlation evidence predicted.

| # | step | deliverable | acceptance |
|---|---|---|---|
| R6.3a | **Reclassify `matter-nt-preface.json`** | the file is the **1633** setting, not the 1582 Preface it was filed as | **DONE** — reclassified, kept as the only 1633 Preface p.1 we hold, and barred from citation as a 1582 reading |
| R6.3b | Sir to adjudicate `aliiíque` | a minim call that revises a correction Sir applied on the 138 ppi substitute | **OPEN** — flagged in the file, not silently changed |
| R6.3c | Sir to note the **mixed `w`/`vv` prelims face** | the NT prelims prose face sets BOTH a real `w` and `vv` | **OPEN** — a blanket `vv`→`w` pass over the NT prelims would be wrong in both directions |

**The ground-truth defect.** `matter-nt-preface.json` was filed as the NT Preface and transcribes the
**1633 setting**: it was read from `NT-1582-F` page 4, and F's Preface p. 1 is one of the two leaves F does
not natively own — proven by blank-margin foxing to be the 1633 Princeton copy's. The text settles it
independently of the foxing: **`ancient` for `auncient`, `manner` for `maner`**, a different display break
and a different headpiece. Letter-count differences cannot come from two impressions of one forme. This is
exactly the contamination §1.4 exists to catch, and it was sitting in ground truth **unflagged** — because
it was made when the plan believed no 1582 Preface p. 1 survived anywhere, so there was nothing to compare
it against. **A false "survives nowhere" verdict does not merely leave a gap; it removes the control that
would have caught a misfiling.** That is a second, sharper cost of the `S06` exclusion (R4.5).

**What `M` resolved that the substitute could not.** The Censure had been transcribed from `NT-1582-X`'s
138 ppi spliced substitute — the same setting, at the worst raster in the corpus for that leaf. `M` carries
it ~3.4× larger and settles three flagged uncertainties: **`vitǽque`** (acute clear), **`lib. 1. c. 3.`**,
and the minim count in **`aliiíque`** — three i-strokes, measured by connected-component count in the
diacritic band rather than judged by eye. The last revises a correction Sir applied, and is flagged for him
rather than changed silently.

**What `M` cannot resolve, and why it stays that way.** The `w`/`vv` discrimination on these leaves is at
the raster's limit and **cannot be improved by any acquisition**: the base exemplar lacks the leaves, `X`'s
copy is the spliced substitute, and `M` has no continuous-tone original. This is a genuine ceiling, recorded
as one — not a pending task.

### R6.6 — the `w`/`vv` flip was adjudicated on a raster that cannot resolve it

**Sir's ruling (2026-08-06): mixed `w`, `vv`, `VV` and `Vv` are likely on a variety of leaves. Do not
exclude the possibility, and be cautious about global flips lest original variants be overwritten.**

`GUIDELINES.md` §w-regime already states the right rule — **per-instance, decided by stroke connectivity,
never by the word** — and its priors are sound. The defect is not the rule. It is **where the rule was
applied**.

A global `vv`→`w` pass changed **33 lines** across three files (backups survive as `*.pre-vvfix`), and the
STATUS note records it as *"now VISUALLY VERIFIED (2026-07-18)"*. **Every one of those three files was read
from `NT-1582-F`.**

| file | witness | source raster | lines flipped |
|---|---|---|---|
| `matter-nt-title.json` | `F` | 800 × 1124 (**~168 ppi**), read at a 400-dpi *render* | 7 |
| `matter-nt-table.json` | `F` | same | 13 |
| `matter-nt-preface.json` | `F` | same — **and the 1633 setting** (R6.3) | 13 |

**The call is beneath the raster's limit.** `F` is barred from glyph-level work because the long-ſ nub —
3–6 px at the base exemplar's ~545 ppi — spans **under 1.6 px** at 168 (§1.2). **The gap that separates two
`v` sorts from one joined `w` is a finer feature than that nub.** So the 2026-07-18 verification could not
have resolved what it reports resolving: it was performed on an *upscaled render*, where interpolation
smooths precisely the gap the test depends on and makes separate sorts *look* joined. That is a mechanism
that biases the error **in the observed direction** — toward `w` — which is exactly the flip that was made.

**Independent evidence that the flip is not safe.** R6.3 read the same two frontmatter leaves in the 1582
setting from `M` at ~380 ppi, and found the prelims prose face setting **both** forms: `VVhich` as a
cap-height `V` plus an x-height `v` with a clear gap, and `word` as a single joined sort — **on the same
line as a two-sort `vve`**.

| # | step | deliverable | acceptance |
|---|---|---|---|
| R6.6a | Re-adjudicate the 33 lines on an **admissible raster** | each `w`/`vv` decided at 2–4× on `B` (~545 ppi) where `B` has the leaf, or on `M` (~380 ppi) where it does not | **no line decided on `F`** — it is inadmissible for this call by the plan's own resolution finding |
| R6.6b | No global pass in **either** direction | the flip is not simply reverted | wholesale reversion repeats the error with the opposite sign; the priors say roman body really is predominantly `w` |
| R6.6c | Retain every `*.pre-vvfix` backup until adjudicated | the observer's record is preserved | the backup is **what was seen**; the current file is **what a rule produced**. Where they disagree the observation is evidence and the rule is inference |
| R6.6d | Amend the §w-regime STATUS note | the ratification is scoped to the raster it was made on | a future observer must not read "visually verified" as covering a witness that cannot support the test |

**`matter-nt-title.json` first.** Its line 6 flips `Vvith`→`With` in **display matter**, where §w-regime
records that the large-capital fount **has no `W` sort at all**. If that holds, the pass manufactured a sort
the page cannot contain — and it did so on the one file whose fount the guidelines already single out as
always `VV`.

**Sequencing.** R6.2 and R6.3 are on the critical path — they close a gap in the NT that the plan wrongly
believed unclosable. R6.4 and R6.5 are not: they are scholarly yield, and they must not delay the base
transcription.

---

## R3.5 — Attribute the New Testament's 36-leaf difference — **DISSOLVED (R8)**

> **This step asked a malformed question and is closed without being completed.** It sought to attribute the
> 765 vs 801 leaf difference between `F` and `B` leaf by leaf. They are **different editions** (§1.1c), and
> a leaf-count difference between editions attributes nothing. The live successors are **R3.5b** (the OT2
> endmatter spread, 1128/1135/1137, a real same-setting question) and **R8.4** (verify every witness's
> setting). Retained here because a step that was open for weeks should not vanish silently.
>
> **R3.5c (NEW).** Grouping the reconcile deltas by setting did not merely delete the malformed −36; it
> produced a **well-formed** replacement. Within the 1633 setting, **`F`'s block is 5 leaves short of `R`'s**
> (765 against 770). *That* is the attributable question the old step was reaching for — two copies of **one**
> edition, so every leaf of the difference has a nameable cause. It inherits R3.5's acceptance criterion
> unchanged, against `R` instead of `B`.

*Everything below is the step as it stood, retained unaltered for provenance. **It is not to be executed.**
`NT-1582-F` is the siglum this step used; the witness is now `NT-1633-F`, which is the whole reason the step
dissolved.*

**Discharges** §1.1b, second half. Depends on the leaf map (R3.2).

| # | step | deliverable | acceptance |
|---|---|---|---|
| R3.5 | Account for `NT-1582-F` 765 vs `NT-1582-B` 801 | every one of the 36 leaves assigned to a named cause | each leaf classed **wanting in the copy** · **back matter absent from `F`** · **dropped in digitisation**, by printed page number and signature |

**Do not shortcut this to "the Fatima copy is defective."** `F` closes on an errata leaf where `B` closes
on *Hard Wordes Explicated*, which points at back matter rather than at missing text — but pointing is not
attributing, and the same 36 leaves are equally consistent with a digitisation that stopped early. The
distinguishing evidence is the **printed page numbers and signatures at the join**, which the leaf map
produces as a by-product. **Until R3.5 runs, no claim is made in either direction about NT completeness**,
and §1.1b says so explicitly rather than leaving a silence a reader would fill with the unflattering
reading.

---

## R5 — Raster policy (folded down from former step 4)

Formerly a full build step; the binarisation work it existed to support was withdrawn when the JP2 packages
were found to be continuous tone (§1.2, §3.1). What remains is small and belongs with Gate 0.

| # | step | deliverable | acceptance |
|---|---|---|---|
| R5.1 | Raster manifest per witness | path, native dimensions, bit depth, checksum of every leaf consumed | manifest complete for the three base exemplars |
| R5.2 | Derivative-contamination guard (Gate 0d) | load-time assertion: bit depth > 1, grey levels > 64, dimensions match manifest | a PDF-derived leaf entering the chain raises, and is proven to raise by a negative test |

**R5.2 needs a negative test, not just a passing one.** A guard that has never rejected anything is not
known to work; the test must feed it a PDF-derived leaf and require the exception.

---

## R7 — The existing ground truth was read from inadmissible rasters (NEW, 2026-08-06)

Fixing one file under R6.5 raised the obvious question — how many others? **Audited all 51 ground-truth
files by the witness and raster each declares.** The answer is not one file.

| what the file was read from | files | why it is inadmissible |
|---|---|---|
| `F` (legacy `S1`), via its JP2 package | **39** | `F` is **~168 ppi in all three volumes** and is barred from glyph-level work by §1.2 — the long-ſ nub spans under 1.6 px. Its OT JP2 is additionally a **4.17× render** of that 800×1124 source |
| `X` (legacy `S8`), via its JP2 package | **6** | `X` is the **excluded** witness: a 2.00× upscale of `B`-NT carrying **zero** real detail beyond it (measured: 0.0002 energy above `B`'s Nyquist, against 0.0093 in `B`'s own top band) |
| `M` (legacy `S6`), via its JP2 package | **3** | `M` is PDF-primary; the JP2 is a **1.73× render** of the ~2955×4206 CCITT |
| `M`, via the primary CCITT | 3 | admissible — R6.2/R6.3, plus the privilege re-read under R6.5 |
| **`B` (~545 ppi) or `P` (~411 ppi)** | **0** | — |

**48 of 51 inadmissible**, reproducible on demand: `python3 witness/audit_gt_rasters.py` (exit 1 while any
remain). The count was 49 before the R6.5 re-read; it is the audit's own regression test that it fell by one.

**Not one ground-truth file was read from the base exemplar or its surrogate.** `pixel_source()` raises for
every witness in the top three rows; it guards *pipelines*, and a human transcription walks straight past it.

### The claim, stated precisely

This does **not** say 48 files are wrong. It says **their glyph-level calls are unverified**, and that
re-reading on an admissible raster reliably moves the epistemic state. Two spot-checks, moving both ways:

- **`M`, the 1634 privilege (R6.5).** Three readings **changed** — `d. Roüen`→`de Roüen`,
  `Marchans`→`Marchands`, `Donnees`→`Données` — and two of them were spans the file had itself flagged as
  unresolvable at the raster it had.
- **`B`, `matter-ot1-approbatio` (read from `F`).** Both flagged uncertainties **resolved and confirmed**:
  the worn `r` of `Vniuerſitate` is plainly present at 545 ppi, and `Duacena` is genuine, not a worn
  `Duacenſi`. The transcription was right; it was merely **unverifiable**.

Confirmation and correction are both results. What is not a result is a call left resting on an image that
cannot carry it.

### The remedy is in-corpus — no acquisition is required

| files read from | re-read on | note |
|---|---|---|
| `F` (OT) | `B` ~545 ppi, or `P` ~411 ppi | both already held and jp2-primary |
| `X` (NT) | `B`-NT 2955×4343 | `X` **is** `B`-NT upscaled, so `B` is simply the same scan at its true raster |
| `M` | the embedded CCITT, via `witness/extract_pdf_leaves.py` | as done for R6.5 |

The only genuine ceiling is the two NT leaves `B` lacks — the Censure and Preface p. 1 — where `M`'s
~380 ppi CCITT is the best that exists. That limit is already recorded and is not new.

| # | step | deliverable | acceptance |
|---|---|---|---|
| R7.1 | Re-read the 6 `X`-based NT files on `B` | same loci, admissible raster | every changed reading carries its measurement; `*.pre-primary-raster` backups retained |
| R7.2 | Re-read the 4 `M`-based files on the CCITT | as R6.5 | one is DONE (`matter-ot2-privilege-du-roi`) |
| R7.3 | Re-read the 39 `F`-based files on `B`/`P` | the bulk of the corpus | prioritise files whose loci `B` or `P` actually hold; report any locus neither holds rather than substituting `F` silently |
| R7.4 | Move the guard to where the reading happens | a ground-truth field asserting the raster against `PRIMARY`, checked by a test | a file declaring a render-derived raster **fails the test**, proven by a negative case |
| R7.5 | Retire `jp2_page.py`'s routing table | every caller reaches rasters through `witnesses.pixel_source()` | `jp2_page.py` cannot return a render-derived path for any witness whose `PRIMARY` is a PDF |

**R7.5 is the mechanism, not a tidying job — and it was verified, not assumed.** `jp2_page.py`'s
`OCR_DIR_TO_JP2` keys **are** the `ocr_dir` values the ground-truth files carry, so this table is literally
what routed 48 transcriptions to the wrong image. It is not only the docstring that is stale:

| `ocr_dir` | routes to | should be |
|---|---|---|
| `archive-nt-1582`, `archive-ot1-1609`, `archive-ot2-1610` | `S01` JP2 | `F` is PDF-primary **and barred** — these loci belong on `B`/`P` |
| `jp2-S08` | `S08` JP2 | `X` is PDF-primary and **excluded**; the locus belongs on `B`-NT |
| `jp2-S06` | `S06` **JPEG** (2550×3301, a 300 dpi render) | the CCITT inside `S06.pdf` |
| `jp2-S04` | `S04_1633-rheims-nt/…_jp2` — the **retired MRC composite** | `newtestamentofie00engl_jp2`, the Princeton original, which is what `pixel_source()` returns |

So a caller using `witnesses.pixel_source()` and a caller using `jp2_page.py` get **different rasters for
the same witness**, and only one of them is guarded. Two routes to the pixels is the defect; the fix is one
route. This is the same shape as the `role="structure"` leak — a retracted decision still live in code —
except that here the code disagrees with the guard rather than merely with the plan.

**R7.4 is the one that stops this recurring.** Three instances now share a single shape — the vv→w flip,
`d. Roüen`, `Marchans` — and in all three the rule was right, the observer was careful, and only the image
was wrong. A guard that lives in `pixel_source()` cannot catch a human reading a PNG. It has to sit on the
ground-truth record itself.

⚠ **This re-opens ratified ground truth and is flagged, not actioned silently.** No transcription is being
withdrawn on suspicion — each stands until re-read.

---

## R8 — `F`'s New Testament is the 1633 edition (NEW, 2026-08-06)

**A load-bearing claim was wrong for four months.** `NT/S01` was registered as `NT-1582-F`, an independent
witness to the 1582 Rhemes New Testament. Its body is the **1633 Rouen** setting — page for page and line
for line with `NT-1633-R` at a constant leaf offset of **+4**, including the shared misprint `Iralie` for
`Italie`, while the genuine 1582 (`B`) puts Apocalypse ch. XXII on printed **743** against `F`'s **692**.
Full evidence at masterplan §1.1c.

**Consequences, in order of severity:**

1. **The New Testament has ONE witness to its own setting**, `B` — not two. `X` was already known to be `B`
   upscaled; `F` is a different edition; `M` is bitonal and prelims-only. Every redundancy assumption for
   the NT is void.
2. **`F`'s OT1 and OT2 are unaffected** — checked at three separated points each, same setting as `B` and
   `P`. The defect is confined to one file.
3. **§1.4's cross-edition "contamination" becomes a same-edition supply.** The foxing result stands; the
   inference drawn from it does not.
4. **R3.5 is DISSOLVED, not completed.** It asked for the 36-leaf `F`/`B` difference to be attributed leaf
   by leaf. The question was malformed: they are different editions, and a leaf-count difference between
   editions attributes nothing.

| # | step | deliverable | acceptance | status |
|---|---|---|---|---|
| R8.1 | Correct the registry | `year=1633`, `wid → NT-1633-F`, evidence in the record | tree rebuilds, 12/12 verified | **DONE** |
| R8.2 | Guard the class of error | `setting()`, `witnesses_to()`, `assert_same_setting()` | `test_setting_guard.py` — cross-setting collation **refused**, both directions exercised | **DONE** |
| R8.3 | Attribute `F`'s 1582 title page | it is the genuine 1582 Rhemes setting, **duplicated at leaves 0 and 2**, on a 1633 body | blank-paper correlation against `B`'s title page: a match ⇒ spliced from `B`'s scan; control-level ⇒ the copy is a made-up one. **State which, or state that neither is supported** | OPEN |
| R8.4 | Re-audit **every** witness for setting, not just the suspected one | printed page + running head at ≥3 separated points per witness, against a known-good partner in its claimed setting | a table covering all twelve records; **any witness whose setting was never checked is named as unchecked, not assumed sound** | **DONE** — 11/12 verified, `OT-1635-M` named unverifiable; §1.1b |
| R8.4a | **Verify the FOOT criteria §0.3 names and R8.4 never read** — signature and catchword | `verify_setting.py` gains a foot band anchored on the text block; readings in `setting-readings.json` under `foot_readings`/`foot_pairs`/`foot_negative_controls`; enforced by `test_setting_verified.py` | every setting agrees on **signature, catchword and last line** at a matched page, and a **negative control across two settings differs**; negatives proven by injection | **DONE** — 11/11 partnered witnesses agree; `B` @147 `T ij`/`30. Paſſing` vs `R` @147 `CHAP.` separates 1582 from 1633; §1.1b R8.4a |
| R8.4b | Extend the foot criteria from one matched page to **≥3 separated points**, matching the head pass | additional foot probes per setting, recorded as data | each setting agrees on signature and catchword at ≥3 separated printed pages, not one | OPEN — until then the foot criteria **corroborate the head result at one point**, they are not an independent three-point verification |
| R8.5 | Bind the plan's counts to the registry | `test_counts_vs_doc.py` | doc/registry disagreement **fails**, proven by a negative case | **DONE** |
| R8.8 | **Bind the roadmap's own verification standard to reality** | `test_verification_standard.py` — parses the command block, checks every command exists, every `-> N/M` claim matches what the command prints, every guard on disk is documented, guards exit 0 and open audits exit non-zero | a stale count, an undocumented guard, a named-but-missing command, or the section being renamed away each **fail**; all four proven by injection | **DONE** — this file's block claimed `10/10` while the tree verified `12/12`, and listed none of the guards |
| R8.6 | Re-examine every ground-truth file taken from `NT/S01` | 9 files (`matter-nt-*`, `nt-marke-*`, `scripture-2john`, `scripture-matthew-28`) | each re-filed as **1633** or re-read on `B`; **none silently left labelled 1582** | OPEN — overlaps R7.3 |

**R8.4 was the one that mattered most, and it is now run.** The error was not found by a test; it was found
by chasing an unrelated leaf-count discrepancy. **No witness's setting had ever been verified against a
same-setting partner** — the concordance verified *title pages*, and a title page is exactly what `F` turns
out to have borrowed. Eleven records were **unchecked**, not sound. `F` was simply the one that happened to
be looked at.

**Outcome (2026-08-06): eleven of twelve verified; no second mis-filing.** Every witness now agrees with a
partner in its claimed setting at three or more separated printed pages — page number, running head,
sidehead, text and line breaks together, marginal apparatus included. Full report and evidence at **§1.1b**
(the acceptance criterion said §1.1c; the report went to §1.1b because that section already owns
cross-witness comparison, and §1.1c stays the narrative of the `F` finding itself). The audit also supplies
its own **negative control**: at printed p.147 under the identical running head *ACCORDING TO S. LVKE*, `B`
prints Luke 4:31 and `F`/`R` print Luke 7:44 — the method visibly separates settings, so its positives are
worth something.

**The twelfth is `OT-1635-M`, and it is not verified — it is unverifiable by this method.** It is the sole
record of the 1635 Rouen setting, so no partner exists. Its date rests on internal evidence: its own
colophon *M.DC.XXXV* and the 1634 privilege it prints. That is stated, not glossed, and
`witness/test_setting_verified.py` holds it in an explicit `SOLE_WITNESS` list which **fails if a partner
ever appears** and is not then collated.

**What now stops recurrence.** `test_setting_verified.py` fails when a registered witness has **no readings
at all** — absence presents as absence rather than passing silently, which is the R1.4 rule applied to
provenance. Both branches are proven by injection: a dropped witness and a verification standing on one
matched page each fail the run, and exit code 1 is checked, not assumed.

| # | step | deliverable | acceptance | status |
|---|---|---|---|---|
| R8.7 | Settle whether `NT-1582-M` and `NT-1582-X` share a source | they have the **same leaf count (800) and the same leaf→printed-page map at every probe**, while `B` runs 5 leaves later; same-setting does not require that | a stated verdict — **same source · independent copies · not resolvable on available evidence** — with the discriminator named. ⚠ **`M` is bitonal CCITT: grayscale NCC against a continuous-tone scan is a DEAD METRIC (0.067 for two genuine 1582 title pages) and a null from it is not evidence.** Use physical accident that survives binarisation, or argue from structure | OPEN |

**R8.7 matters for a specific reason, not as tidiness.** §1.4 credits `M` with the corpus's only genuine
1582 Censure and Preface p.1, and identifies it as the source of `X`'s two supplied leaves. If `M` and `X`
shared a source that claim needs restating. **The existing evidence already argues against it and should be
weighed first**: `B` lacks both leaves, `M` carries them, and a file cannot supply what it was derived from.
That is an argument from the record, not a new measurement, and R8.7 should start by testing whether it
holds rather than by reaching for a correlation.

**R8.6 is the ground-truth blast radius.** Nine of the files audited under R7 declare `ocr_dir:
archive-nt-1582` — that is `F`. They were read from a 1633 book while being recorded as 1582 readings. This
compounds with R7: those files are on an inadmissible raster **and** the wrong edition. They must be
re-filed before any of them is cited.

**`audit_gt_rasters.py` now detects this rather than relying on this paragraph.** The audit previously
reported those nine under `F`'s *resolution* bar, because `BARRED` was keyed on the **siglum alone** — the
same assumption that produced the original error, that a copy has one character across all volumes. `F` is
low-resolution in the OT and **a different edition** in the NT, and only the second is fatal: re-reading a
1633 leaf at 545 ppi fixes nothing. The registry now carries `TRANSCRIBED` (the edition each volume is a
transcript *of*) and `attests_transcribed_setting()`, and the audit reports **`WRONG SETTING` first**, ahead
of the resolution and render reasons. It returns `None`, not `False`, for the whole-Bible `OT` pseudo-volume
behind `M`'s 1635 prelims — admitted *because* it is another edition — and the test asserts that
distinction, since collapsing "not the text" into "not applicable" is how `NT-F` stayed admissible.
Verified: **9 files flagged, no others.**

### Why this was missed — a method note, not an apology

The test that established `F` as an independent copy was run **against `B`** and correctly returned noise at
every offset. It was read as *"`F` is an independent copy of the 1582"* when it licensed only *"`F` is not
`B`."* The visual note recorded at the time — *"different text, different signature series"* — is this
finding, written down and misread as evidence of a different **copy** rather than a different **setting**.
`R` was never tested against `F`, because `R` had been filed as "the other edition" and so was not a
candidate partner.

⇒ **A test distinguishes exactly the hypotheses it contrasts, and filing a witness under a label removes it
from the candidate set.** Both are now structural: `witnesses_to(vol, year)` enumerates candidate partners
from the registry rather than from memory of how things were filed.

---

## Verification standard for this roadmap

A step is **DONE** when its acceptance test runs and passes on demand — not when the code exists.
Every step above that is marked COMPLETE has a command that reproduces its result.

Run everything with the project interpreter — `../ocr-venv/bin/python` from `ocr-spike/`. The block below
was itself found stale on 2026-08-07 (it claimed `10/10` and listed none of the guards) and is now bound to
reality by `witness/test_verification_standard.py`, which parses this block and fails if a command named
here does not exist or if a count asserted here disagrees with what the command prints.

**Registry and structure** — all exit 0:

```
../ocr-venv/bin/python witness/witnesses.py             # registry: 12 records over 11 files
../ocr-venv/bin/python witness/make_witness_tree.py     # build + verify tree  -> 12/12 witnesses verified
../ocr-venv/bin/python witness/inventory_leaves.py      # full-corpus leaf inventory
../ocr-venv/bin/python witness/reconcile_counts.py      # leaf-count reconciliation, grouped BY SETTING
```

**The guards** — each carries a proven negative case; all exit 0:

```
../ocr-venv/bin/python witness/test_primacy_guard.py       # R0.5  a render-primary witness raises on pixel access
../ocr-venv/bin/python witness/test_setting_guard.py       # R8.2  cross-setting collation is REFUSED
../ocr-venv/bin/python witness/test_counts_vs_doc.py       # R8.2  §1.1 table agrees with the registry (12/12)
../ocr-venv/bin/python witness/test_setting_verified.py    # R8.4  no witness may lack setting readings
../ocr-venv/bin/python witness/test_verification_standard.py  # this block agrees with reality
```

**The audits** — these are *expected to fail while their step is open*, and that is the point:

```
../ocr-venv/bin/python witness/audit_gt_rasters.py      # R7: exits 1 -> 48 of 51 GT files inadmissible, 9 WRONG SETTING
```

A guard exiting 0 and an audit exiting 1 are both healthy states. An audit that exits 0 before its remedy
is done would mean the audit stopped looking, not that the corpus got better.

# OriginalDR — Development Log

What was actually built, measured, and decided, in order, with the evidence. The plan states what must be
true and the roadmap states what will be built; **this file records what happened**, including the things
that turned out wrong.

A retraction here is not an embarrassment to be minimised — it is the most useful kind of entry, because
every one of them marks a place where a plausible reading survived until something measured it. They are
kept in full, with what produced them.

---

## 2026-08-05 — Session 1: witness identity, addressing, leaf inventory

**Discharges** §1.1, §1.1a · roadmap R0, R1.

| built | what it does |
|---|---|
| `witness/witnesses.py` | canonical registry — sigla, volume, year, role, repository, source path |
| `witness/make_witness_tree.py` | stable symlink farm at `sources/witnesses/<VOL>/<WID>/leaves` + `MANIFEST.json`, and **verifies** it |
| `witness/inventory_leaves.py` | per-leaf physical classifier → `TEXT / BLANK / SPARSE / PLATE / BINDING` |
| `witness/reconcile_counts.py` | splits each witness into leading matter / book block / trailing matter |

**Design note — symlinks, not copies.** Copying the JP2 packages would duplicate ~11 GB and create a second
artefact that can drift. A broken link fails loudly where a stale duplicate fails silently.

**Measured, and it changed the plan**: page counts cluster by volume; the tome map's 11 admitted volumes
minus S04 and S06 gives exactly the 9 files held.

---

## 2026-08-05 — Session 2: primacy is per item

**Discharges** §1.2, §1.2a · roadmap R0.4, R0.5, R4.2, R4.4. **Commit `28e136b`.**

### What was wrong

The plan carried a blanket rule: *"the JP2 packages are the primary source; the PDFs are derivatives."*
True of the institutional captures, **false of the user re-uploads**, where a PDF was uploaded and IA
*rendered* the JP2 package from it.

Read from IA's own `source`/`original` fields — one API call per item, not an inference:

| class | items | JP2 package derives from |
|---|---|---|
| institutional capture | `S09` ×3, `S03a`, `S03b` | `<id>_orig_jp2.tar` — the camera originals |
| user re-upload | `S01` ×3, `S08`, `S04` | **an uploaded PDF** |

Render ratios, from page box vs embedded image: **`S08` 2.00× (144 dpi) · `OT/S01` 4.17× (300 dpi) ·
`NT/S01` 1.00× (72 dpi)**. Every ratio above 1.00 is interpolation.

### Two retractions, in opposite directions

**`S01` is 800 × 1124 in all three volumes — the *original* reading was right.** An intermediate draft had
recorded `OT1/S01` and `OT2/S01` as 3334 × 4684 and concluded the PDFs were downsampled derivations. The
derivation chain shows the reverse: those PDFs are the md5-verified uploads and the large JP2s are 300-dpi
renders of them. Sampled at pages 50/300/700/1000 — every page 800 × 1124.

**`S04` broke the pattern, and it was the fifth item checked.** Its primary was an **IA-produced MRC PDF**
(*"Recoded by LuraDocument"*) whose text layer is a **1-bit JBIG2 mask** — while its 3659 × 5134 render
*composites* that mask and measures as 213 grey levels, 91% midtone. Had the rule been generalised from the
four `S01`/`S08` items, the exception that matters most to §1.4 would have been missed, and missed quietly.

**Remedy was acquisition, not reconstruction.** `newtestamentofie00engl` — Princeton Theological Seminary,
call no. 13733, OCLC 1049890088 — carries the continuous-tone originals. Acquired and verified: 778 leaves,
**NCC 0.990** against the superseded render, **190–228 grey levels** at 2439 × 3423.

### Built

`PRIMARY` / `PDF` / `NO_READING` and `pixel_source()` in the registry, which **refuses** every render and
any binarised primary while `leaves()` stays open for structural work. `test_primacy_guard.py` proves the
refusal in both directions.

---

## 2026-08-05 — Session 3: the classifier's zero was not a finding

**Discharges** roadmap R1.4, R1.5, R1.6. **Commit `e7e9fbc`.**

The full reconciliation reported **zero** lead, trail and interior blanks for all three `F` witnesses,
which reads as *"the rehost stripped its blanks."* It was the threshold's shape. `label()` had been made
witness-relative for *saturation* and left **absolute for ink**.

**The criterion took two attempts.** Comparing the ink floor to the **median** split the three `F`
witnesses inconsistently — OT1 tripped at 0.196/0.350 while NT passed at 0.193/0.409 — though not one has a
leaf below ink 0.06. The median describes the *text*, so that ratio measures contrast, not detectability.
Comparing the floor to **the cut about to be applied** separates the corpus exactly:

| class | ink floor | witnesses |
|---|---|---|
| genuine capture | **0.0000** | `B` ×3, `P` ×2, `R` |
| re-upload | **14–20× the cut** (0.141–0.196) | `F` ×3, **`X`** |

**The check found `X` at 14×, which had not been predicted**, and it places `R` in the genuine class
*because* its original was acquired — a fourth, independent corroboration of the primacy split, from a
measurement unconnected to derivation chains, page boxes or spectra.

Also fixed: the summary enumerated a fixed tuple of kinds, so `TEXT?` vanished from the totals while `n`
stayed right — 1135 unresolved leaves printing as all-zeros and looking accounted for.

`relabel.py` re-applies `label()` to stored features, so revising a threshold costs seconds rather than a
40-minute image pass. **A threshold nobody can afford to revise is one that never gets revised.**

---

## 2026-08-05 — Session 4: §1.1 / §1.1a review, and what `S06` actually is

**Discharges** §1.1, §1.1a, §1.1b, §1.3, §1.4 · roadmap R3.5, R4.1a/b/c, R4.3, R4.5, R4.6, R6.

### `S06` — an exclusion that was a claim, and was wrong

The plan excluded `S06` as *"a modern facsimile, not a witness to the setting."* Read from its own leaves:

- it is a **2007 Maximus Scriptorius print-on-demand** volume — letter-size, 1-bit CCITT ~380 ppi —
  but its images are **photographs of original copies**, not a redrawing;
- its **OT is 1635**, *"Printed by IOHN COVSTVRIER … M.DC.XXXV"* — Rouen, the second edition, not 1610;
- its **NT is a 1582 Rheims Fogny** (leaf 2072), the same setting as the base exemplar, from a copy that
  is not `NT/S09`.

**R4.3 discharged, and not where expected.** `NT/S08`'s two made-up leaves come from **the 1582 setting
witnessed by `S06`**:

| | `S06[2073]` Censure | `S06[2074]` Preface p.1 | 1633 setting |
|---|---|---|---|
| `S08[1]` supplied Censure | **+0.424** | +0.000 | −0.036 … +0.012 |
| `S08[2]` supplied Preface p.1 | +0.017 | **+0.398** | +0.055 … +0.212 |

Confirmed visually line-for-line, including the **S. Augustine quotation** that the 1633 setting lacks and
the absence of the *"of the first Edition of this Translated New Testament"* subtitle that dates the 1633.

**Withdrawn**: *"no genuine 1582 Censure or Preface-p.1 leaf exists anywhere in this corpus."* Both
survive, in `NT-1582-M`. The verdict had been true of the four files under consideration and false of the
corpus, because `S06` was excluded on a description that was never checked. **An exclusion inherits the
evidential standard of any other claim** — now roadmap R4.5.

Also recovered from `S06`'s back matter: the **`EXTRAICT DV PRIVILEGE DV ROY`**, Paris, **3 August 1634**,
ten years to Jean le Cousturier to reprint *"La Bible en language anglois, de l'edition de Laurens Kellam
Imprimeur de Douay"* — the 1635 OT states on its own leaves that it reprints the Kellam Douai edition.

### `F` — what was subordinated, and on what evidence

`F` had been called a *"rehost; physical copy not yet identified"* with role **"structure only."** Both
subordinated the **copy** on evidence that only concerned the **scan**.

- The copy is **owned and digitised by the Fatima Movement**; it has no shelfmark because it is not a
  library's copy. *Privately held* is a determinate answer.
- **OT1 `F` and `P` contain the same 1132-leaf book block**, opening at the same title page and closing at
  *"THE END OF THE FIRST TOME"*, printed p. 1114. The 11-leaf difference is 5 leaves of library apparatus,
  6 of binding and imaging targets, less a duplicate title page and one fewer terminal blank — **no text**.
- In the **NT, `F` is *more* complete than the base exemplar**, which lacks its Censure and Preface p.1
  outright.
- What holds is a measurement about the images: **800 × 1124, ~168 ppi**, where the long-ſ nub spans under
  1.6 px. That limits glyph-level work only.

Role restated as **independent witness, low-resolution scan**. Open and stated rather than buried:
`NT-1582-F`'s block is 765 against `B`'s 801, and those 36 leaves are **not yet attributed** — roadmap
R3.5, with no claim made in either direction until it runs.

**`ourladyisgod.com` tested and negative.** Sampled page images measure **800 × 1124** and correlate with
the corresponding `OT1/S01` leaves at **NCC 0.996–0.998** — the same files, not a better capture.

### ESTC — blocked externally, documented

`estc.bl.uk` redirects to CERL; the ESTC beta returns **`no such index [estc]`** for every query. Leads
held and **not promoted**: STC 2884 / ESTC **S102419 *or* S102491** (sources disagree by one digit), and
STC 2207 / ESTC S101944. `witness/estc_probe.py` distinguishes `INDEX_DOWN` from `ABSENT` so an outage can
never be recorded as evidence.

### Built

| built | what it does |
|---|---|
| registry `M` siglum + `leaf_range` | `NT-1582-M` is a **slice** (leaves 2072–2871) of the 2872-leaf `S06` package — addressing the whole package would pool a 1635 Rouen OT with a 1582 Rheims NT |
| `leaves()` count assertion | on-disk count must equal the registry, so a slice cannot silently drift |
| `make_witness_tree.py` link farm | a sliced witness gets per-leaf symlinks renumbered from zero, not a directory symlink |
| `witness/estc_probe.py` | three-state ESTC probe: `FOUND` / `ABSENT` / `INDEX_DOWN` |

**Verified**: 11/11 witnesses resolve, `M`'s slice is exactly 800 leaves, guard tests pass in both
directions.

---

## Session 5 — the companions caught up, and the role label came out of the code

The previous session established `M` and restated `F`, and wrote both into the plan. **The three companion
documents still carried the withdrawn descriptions**, which is the condition that makes a retraction
worthless: a reader arriving at the Overview would have been told, in the present tense, that `F` is *"a
rehost whose copy is unidentified"* with the role *"structure only"*, and that a *"1610 whole-Bible
facsimile is excluded outright"* — the exclusion this project had just proved wrong at the most
consequential point in the New Testament.

### The witness count was wrong in both directions

Every document opened with **"ten scan files … reduce them to seven witnesses."** Both numbers were stale,
and the derivation of "seven" was no longer recoverable from the table beneath it.

- The **file count omitted `S06`**, which had been excluded on a mistaken description and so was not
  counted as *held* at all.
- The **witness count subordinated the three `F` copies** as "structure only" — a limit belonging to their
  scan, not to the copies.

Restated as **eleven files, ten witnesses**, and — the part that matters — stated **so it can be checked
against the table** rather than trusted: eight witnessing their own volume's setting, one different-edition
support (`R`), one frontmatter witness (`M`), and one file that is no witness at all (`X`). A bare numeral
is what went stale three times; an arithmetic a reader can verify does not.

### Two blanket claims that `M` falsified

| claim, as it stood | why it failed | now |
|---|---|---|
| *"All ten are continuous tone at source"* | `M` is **1-bit CCITT at ~380 ppi**, and there is no continuous-tone original to acquire — the tone was discarded before the file existed | **ten of eleven**; `M` named as the one real exception, its raster recorded as the limiting factor on every reading taken from it |
| *"Read the JP2 leaves. Never the PDFs."* | right for the six institutional captures, **exactly backwards for the other five**, where a user uploaded the PDF and IA rendered the JP2s from it | **read each item's primary artefact**, per §1.2 — following the old rule would have put a render in place of a source in five cases out of eleven |

The second is the more instructive: a per-item empirical finding had been compressed into a universal rule,
which is the same defect as a stale numeral, wearing procedural clothing.

### The withdrawn label was still in the code

The plan retired *"structure only"* and the registry did not: `witnesses.py` still emitted
`role="structure"` into `MANIFEST.json`, so **every downstream consumer would have read the retracted
label** — and read it as a permission narrower than the evidence supports.

- Renamed to **`lowres`** across the three `F` witnesses, with the reason recorded at the definition rather
  than in a commit message.
- Added a **`ROLES` table to the code**, so a consumer of the manifest need not read the plan to learn what
  a role permits and forbids.
- Added an **import-time guard**: a role outside the vocabulary now raises. A declared vocabulary nothing
  checks is decoration, and an unknown role reaching the manifest would be read as a permission it does not
  have.

**Verified**: 11/11 witnesses rebuild, roles `base` 3 · `lowres` 3 · `surrogate` 2 · `support` 1 ·
`frontmatter` 1 · `excluded` 1, guard tests pass both directions.

### R6.2 — the 1582 prelims extracted and named

`witness/extract_pdf_leaves.py` extracts leaves from a PDF-primary witness, pulling the **embedded
XObject** rather than rasterising the page — rasterising would add one more render on top of the ones the
primacy rule exists to avoid. The slice offset (`M`'s leaf 0 = package page 2072) is read from the registry
and applied in **one place**, because hand-computing it per call site is exactly how a frontmatter leaf
gets attributed to the wrong edition.

| leaf | package page | identified as |
|---|---|---|
| 0 | 2072 | **title page** — *THE NEVV TESTAMENT OF IESVS CHRIST … IN THE ENGLISH COLLEGE OF RHEMES* |
| 1 | 2073 | **THE CENSVRE AND APPROBATION** — two-line heading, **no ornamental headpiece**, decorated `C` initial, **no *"of the first Edition"* subtitle** ⇒ **the 1582 setting** |
| 2 | 2074 | **Preface p. 1** — foliate headpiece, *THE PREFACE TO THE READER TREATING OF THESE THREE POINTS* |
| 3 | 2075 | Preface, running head *THE PREFACE*, marginalia both margins |
| 4 | 2076 | Preface, running head *TO THE READER* |

Leaf 1 is the leaf the plan once recorded as surviving nowhere, and its diagnostic features are present
exactly as §1.1 predicts from the correlation evidence.

**Two silent defects caught while doing it**, both of the kind that still *look* like a page:

- **A second embedded image on every page.** It is a **1×1 DeviceGray swatch, one shared xref reused
  across the whole document** — a Distiller background fill, not a soft mask. Dropped **by rule** (only
  when genuinely degenerate); anything larger is kept and reported, because a real second image would mean
  the leaf is composited and must be inspected before it is cited.
- **Polarity.** A PDF `/ImageMask` carries no polarity of its own — which value is ink is set by the page's
  fill and `/Decode` — so the stencils extracted **white-on-black**. Fed to a recognizer that is invisible:
  the page still looks like a page, and every stroke-width and ink-coverage statistic computed from it is
  inverted. Now decided **from the image** by the minority-class rule (ink measured at **5.8–8.7%** of the
  sheet across the five leaves), and where neither class is a clear minority the image is **left alone and
  the caller told loudly** rather than a coin being flipped — the same failure mode as the absolute ink
  threshold that made `F`'s blank leaves unresolvable.

---

## Session 6 — R6.3, and a contaminated leaf found sitting in ground truth

### The Censure, re-grounded

The Censure had already been transcribed and Sir-reviewed — from **`NT-1582-X`'s 138 ppi spliced
substitute**, which is the same setting at the worst raster in the corpus for that leaf. `M` carries it at
2617 × 4149 against roughly 771 × 1103: about **3.4× linear**. Not a new witness to a new text; the same
reading at a raster that can be read. Three flagged uncertainties settled:

| flagged | resolved on `M` |
|---|---|
| `vitæque` / `vitǽque` | **`vitǽque`** — the acute over the æ is unambiguous at 4× |
| `lib. 1.` numeral | **`lib. 1. c. 3.`** — the 3 is the old-style descending form |
| `aliíque` minim count | **`aliiíque`** — three i-strokes, the third carrying the acute |

The minim call was **measured, not judged**. In the band above x-height the word carries four marks: the
`l` ascender, two round dots (both rows 5–12, w = 8), and a larger slanted mark (rows 1–19, w = 13) — an
acute, standing one full letter-pitch beyond the second dot, so over a *third* minim. The x-height stroke
groups agree. Standard Latin is `aliíque`; the extra minim is the compositor's, and preserved.

**This revises a correction Sir applied on 2026-07-23, and is flagged rather than changed silently.** He
read `aliique` on the substitute, where two minims and an acute are not separable. It is not being
overruled on judgement — it is being re-taken on a materially better image. Corroboration: `aliiíque` and
`vitǽque` resolve in the *same* direction, both marking the enclitic `-que` with an acute. Two independent
instances of one convention on one leaf is a stronger warrant than either reading alone.

### The defect this exposed

`matter-nt-preface.json` was filed as the NT Preface. **It transcribes the 1633 setting.** It was read from
`NT-1582-F` page 4 — and F's Preface p. 1 is one of the two leaves F does not natively own, proven by
blank-margin foxing to be the 1633 Princeton copy's. The text settles it independently of the foxing:

| `M` (1582) | the filed GT |
|---|---|
| `auncient` | `ancient` |
| `maner` | `manner` |
| `text:& of the` | `text ; and of the` |
| `THE PREFACE TO / THE READER TREATING OF` | `THE / PREFACE TO / THE READER TREATING` |
| foliate **strapwork** headpiece | figured **grotesque** headpiece |

Letter-count differences cannot be produced by two impressions of one forme. Reclassified, and **kept** —
it is the only 1633 Preface p. 1 we hold, and the 1633 setting is an admitted witness — but barred from
citation as a 1582 reading.

**The instructive part is why it went unnoticed.** It was made when the plan believed no 1582 Preface p. 1
survived anywhere, so there was **nothing to compare it against**. A false "survives nowhere" verdict does
not merely leave a gap where evidence should be; it **removes the control that would have caught a
misfiling**. That is a second and sharper cost of the `S06` exclusion, beyond the one already recorded at
R4.5.

### `w`/`vv` — the prelims face mixes them

The standing per-face table gives *"NT 1582 roman body = real `w`."* On this leaf, in the smaller **prelims
prose face**, both forms occur:

- **`VVhich`** (4×) — a cap-height `V` then an x-height `v`: two sorts, clear gap, different heights.
- **`word`** (4×) — a single sort whose medial strokes join at a shared apex serif, no gap. **On the same
  line as `vve`, which is two sorts.**

So the `w`/`vv` call on this face must be **glyph-driven, exactly as long-ſ already is**, and no blanket
pass in either direction is safe. This does *not* trigger the global flip the guidelines contemplate: the
scripture body face is a different fount and no existing scripture transcription is affected.

Confidence is held at **medium and deliberately not raised** — at 380 ppi bitonal a `w` cut vv-style and a
true `vv` pair sit near the discrimination limit, and all zooms were held at or below 4× because past ~5×
the sort pixelates and proves nothing.

### The ceiling, recorded as a ceiling

`M`'s raster is 1-bit CCITT at ~380 ppi and **cannot be improved by any acquisition**: the base exemplar
lacks these leaves, `X`'s copies are the spliced substitutes, and `M` has no continuous-tone original — the
tone was discarded before the file existed. The `w`/`vv` uncertainty is therefore a **genuine ceiling, not
a pending task**, and is recorded as one in both transcriptions.

### Incidental corroboration

`M`'s Preface leaf carries **manuscript underlinings and marginal pen strokes** — a reader's marks in the
copy that was photographed. A facsimile in the strict sense, a redrawing, would not carry them. Independent
physical support for the claim on which `M`'s admission rests: these are photographs of an original. The
foot also gives signature **`a ij`** and catchword **`popular`**, and `M` leaf 3 opens `popular` — leaf
order confirmed by the book itself rather than assumed from file order.

---

## Session 7 — R6.4, and Sir's `w`/`vv` ruling turns out to have a mechanism

### Sir's calls

**`aliiíque` approved on the evidence.** **And on `w`/`vv`:** *mixed `w`, `vv`, `VV` and `Vv` are likely on
a variety of leaves; do not exclude the possibility, and be cautious about global flips lest original
variants be overwritten.*

Checking what that implicated turned up something sharper than the caution itself. A global `vv`→`w` pass
had already changed **33 lines** across three files, and `GUIDELINES.md` recorded it as *"now VISUALLY
VERIFIED."* **All three files were read from `NT-1582-F`** — an 800 × 1124 (~168 ppi) source, at a 400-dpi
*render*.

**The call is beneath that raster's limit.** `F` is barred from glyph work because the long-ſ nub spans
under 1.6 px there, and **the gap separating two `v` sorts from one joined `w` is a finer feature than that
nub**. Worse, upscaling interpolates exactly that gap, so a render makes separate sorts *look* joined —
biasing the error **toward `w`**, which is the direction the flip went. The rule was never wrong; only the
image it was applied to. Ratification withdrawn, backups retained, roadmap R6.6.

### R6.4 — the collation

`OT-1635-M` registered (package pages 0–2070) so differences could be **cited to a leaf** rather than
described. It is not a witness to either OT tome's setting and may never supply an OT verse reading.

**Adds and drops, resolved for the whole Preface without reading 22 pages word by word.** The Preface's
**marginal notes** are short, numerous and content-bearing, so a passage added or cut shows up as a note
without a counterpart, localised to the leaf. **All ~24 correspond one to one, in the same order.** The
1635 occupies ten leaves where Douai needed twelve because the measure is wider — not because anything was
lost.

**The Approbatio is reprinted verbatim, keeping `Duaci 8. Nouembris. 1609`.** Rouen does not re-approve
itself twenty-six years on; it reproduces the approbation of the edition it reprints. **The approbation
dates the text, not the book.**

**What Rouen actually changed** — dominated by `-ie`→`-y`, dropped terminal `-e`, more capitalisation,
`VV`→`W`, plus one silent correction of a first-edition error (`to large`→`too large`).

**And the part worth resisting the urge to tidy.** It is *not* a modernisation programme:

| 1609 | 1635 |
|---|---|
| `AVTHOR` | `AVTHOVR` |
| `authors` | `authours` |
| `Goſpel` | `Ghoſpel` |
| `dearly` | `dearely` |
| `S. Ierom` | `S. Hierom` |

The `ai`/`ay` digraph settles it: `affayres`→`affaires` but `Painimes`→`Paynimes` — **the same digraph
moves both ways inside one edition.** "The 1635 modernises the spelling" is a cleaner sentence than the
leaves support, so it is not the sentence in the report.

### The finding that bears back on Sir's ruling

**The 1635 founts have a `W` sort. The Douai founts do not.**

| | 1609 | 1635 |
|---|---|---|
| display | `VVELBELOVED` | **`WELBELOVED`** |
| marginal notes | `VVhy & how` · `VVhat part` | `Why and how` · `What part` |
| italic close | `tovvards` | `towards` |

And the 1609 prose is **itself mixed on a single page**, at ~545 ppi on the base exemplar (leaf 13):
`we`/`which`/`wil`/`know`/`whom` with a real `w`, **`vvorke` as two sorts**, `VVherin`/`VVherfore` with
capital `VV`.

So the availability of a `W` sort is **a property of the printing house**, and mixing occurs *within* a
page. A global flip would erase a real distinction between the two editions, silently. Sir's caution was
right, and it now has a documented mechanism and a measured counter-example on an admissible raster.

### Scope, stated rather than left to be discovered

Not collated: word-level rewording in the bodies beyond the sampled passages · the endmatter Tables · **the
OT2/1610 prelims**, which sit further into `M`'s package and are not yet located. None blocks the edition —
`M` supplies no verse reading, so this is scholarly yield, not critical path.

---

## Session 8 — R6.5, and the third instance of the same defect

R6.5 asked for the 1634 privilege transcribed verbatim from `M` leaf 2070. It turned out to be **already
transcribed** — `ground-truth/matter-ot2-privilege-du-roi.json`, dated 2026-07-20, careful work with its
own uncertainties honestly flagged. The finding is not that it was wrong. It is **what it was read from**.

That file records its raster as the `S06` **jp2** at 5100×6601. Everything since has established that `M`
is **PDF-primary**: the PDF holds the real ~2955×4206 CCITT and the jp2 is a **1.73× render** of it. So the
2026-07-20 observer's 5× word zooms were working at roughly **8.6× the true raster** — every fine call made
against pixels that interpolation invented.

Re-read from the embedded CCITT XObject (`witness/extract_pdf_leaves.py`, no rasterisation in the loop),
**three readings change — and two are precisely the spans the original file had flagged as unresolvable.**

**`d. Roüen` → `de Roüen`.** Settled by measurement, not by eye. The `d` ends at x526, the `R` begins at
x572: a **46 px** gap. Word spaces elsewhere on that line are 27, 29, 27 px, and the line's own `e` is
22 px wide — 22 + 27 ≈ 49. The gap holds an `e` *and* a space, not a space alone. The negative control is
what makes it airtight: **a real period sort on this page measures 10 × 12 px**; the mark in the gap
measures **3 × 2 px — one twenty-fifth the area** — and sits at the baseline, where an `e` bowl bottoms
out. It is not a period. It is the last surviving trace of an `e` that failed to ink.

**`Marchans` → `Marchands`.** Between the `n` and the `s` sit two fragments: a baseline blob 8 × 7 px, and
a narrow stroke **6 px wide and 42 px tall — full ascender height**. The original read them as a foxing
point plus an i-height stroke. An i-height stroke cannot reach ascender height. They are a `d`'s ascender
and the foot of its bowl, with the bowl failed. Agrees with the singular `Marchand` on line 2 and with the
standard formula *Marchands Libraires*.

**`Donnees` → `Données`.** Not previously flagged at all; the acute is solidly inked.

### The pattern, now with a mechanism

This is the **third** instance of one defect class, and the three together name it precisely:
**upscaling manufactures the very feature the call depends on.**

| where | what interpolation did | which way it biased |
|---|---|---|
| the `vv`→`w` flip (R6.6) | closed the gap between two `v` sorts | toward `w` — the direction the flip went |
| `d. Roüen` | rounded a 3 × 2 speck into a plausible point | toward an abbreviation that isn't there |
| `Marchans` | smeared a failed `d` bowl into point-plus-stroke | toward dropping a letter |

In every case **the rule was right and the observer was careful**. The defect was never judgement; it was
*which image the judgement was exercised on*. The 2026-07-20 observer even wrote down the correct answer as
an alternative — *"or the word could be `de Roüen` with a broken `e`"* — and could not choose between them,
because the evidence that chooses had already been interpolated away.

⇒ **The operational rule: before any glyph-level call, consult `PRIMARY` for that witness.**
`pixel_source()` enforces this for the five renders, but it guards *pipelines*. A human transcription can
walk straight past it, and did — twice. The guard needs to sit where the reading happens, not only where
the code does.

Backups retained as `*.pre-primary-raster`, on the R6.6c principle: the backup is what an observer saw, the
current file is what a measurement produced. Where they disagree, both are kept.

### Then the obvious question: how many others?

Fixing one file is not a result if the same fault sits in fifty. `witness/audit_gt_rasters.py` reads the
raster each ground-truth file **declares** and checks it against that witness's `PRIMARY`.

**48 of 51 files are inadmissible.** 39 were read from `F` — the witness barred from glyph work at
~168 ppi — 6 from `X`, the *excluded* witness, and 3 from `M`'s jp2 render. **Not one was read from `B`
(~545 ppi) or `P` (~411 ppi)**, the base exemplar and its surrogate.

That last number is the one that stings. The plan spent four sessions establishing which witnesses can
carry a glyph-level call, and the entire ground truth was read from the ones that cannot.

**Two spot-checks, and the epistemic state moved both ways** — which is the honest characterisation:

- **`M`, the privilege.** Three readings *changed*, two of them spans the file had flagged as unresolvable.
- **`B`, `matter-ot1-approbatio`** (originally read from `F`). Both flagged uncertainties *resolved and
  confirmed*: the worn `r` of `Vniuerſitate` is plainly present at 545 ppi, and `Duacena` is genuine rather
  than a worn `Duacenſi`. The transcription was right — it was **unverifiable**, which is a different fault
  from being wrong, and the only one being alleged here.

So the claim is not "48 files are wrong." It is that their glyph-level calls rest on images that cannot
carry them, and re-reading reliably resolves the question one way or the other. Confirmation is a result.

**The remedy needs no acquisition**: `F`-based files re-read on `B`/`P`; `X`-based files on `B`-NT (`X`
*is* `B`-NT upscaled, so `B` is the same scan at its true raster); `M`-based on the CCITT. The only real
ceiling is the two NT leaves `B` lacks, already recorded.

Tracked as **R7**, with R7.4 as the item that stops the recurrence: the guard must sit on the ground-truth
record, because `pixel_source()` guards *pipelines* and a person reading a PNG never touches it. Nothing is
withdrawn on suspicion — each transcription stands until re-read.

## Session 9 — `F`'s New Testament is the 1633 edition, and has been all along

A load-bearing claim was wrong for four months. `NT/S01` was registered `NT-1582-F` and described as *"an
independent witness to the 1582 Rhemes New Testament."* **Its body is the 1633 Rouen setting.**

It surfaced sideways. R3.5 asked why `F`'s NT block runs 765 leaves against `B`'s 801, and the intended
method was to walk the join and attribute the 36 leaves. Checking printed page numbers at the join instead
put `F` beside `R` — the 1633 copy — and they were the same book.

**The evidence, at four separated points:** `F` tracks `R` page-for-page and line-for-line at a **constant
leaf offset of +4**. F356/R360 both print **332** *THE ACTES*; F556/R560 print **530** *FIRST EPISTLE OF S.
PAVL*; F708/R712 print **682**; F716/R720 print **690**. They share the misprint **`Iralie`** for `Italie`.
`B` disagrees with both everywhere: Apocalypse ch. XXII stands at printed **743** in `B` against `F`'s
**692**, and `B` carries running-head apparatus (`CHA. XIII.`, `HOLY weeke`) that neither `F` nor `R` has.

**`F` is an *independent* 1633 copy, not a second render of `R`.** The blank-margin correlation that reads
**+0.769** for a proven shared physical leaf reads **0.099 / 0.021 / −0.022** here, against controls of
0.077 / −0.084 / −0.030. Two 1633 copies, not one file twice.

**`F`'s Old Testament volumes are unaffected** — genuinely 1609 and 1610, checked at three separated points
each and in step with `B` and `P`. The defect is the NT file alone, which is why sigla are per volume.

### Why it was missed

The independence test **was run**, and it passed. It was run **against `B`**, and returned noise. That
licensed exactly one conclusion — *`F` is not `B`* — and it was recorded as *`F` is an independent **1582**
copy*. `R` was never contrasted with `F`, because `R` had already been filed as "the other edition" and so
was not in the candidate set when the question was asked.

⇒ **A test distinguishes exactly the hypotheses it contrasts. Filing a witness under a label removes it
from the candidate set, and the removal is invisible afterwards.**

The corroborating detail is that the finding was already written down. A contemporaneous note recorded
*"different text, different signature series"* between `F` and `B` — which **is** this finding — and it was
read as *different copy* rather than *different setting*. The observation was correct and the category was
supplied by the label.

### Consequence

**The New Testament has one witness to its own setting.** `X` is `B` upscaled with zero real detail beyond
it, `F` and `R` are 1633, `M` is bitonal and prelims-only. Every NT redundancy assumption in the plan is
void. Nothing about `B`'s readings changes — but nothing corroborates them either, and no amount of
re-reading manufactures a second witness. **The remedy is acquisition.**

Still open (R8.3): `F`'s title page **is** a genuine 1582 Rhemes Fogny setting — woodcut border,
*PRINTED AT RHEMES, by Iohn Fogny. 1582.* — and it is **duplicated at leaves 0 and 2** on a 1633 body. A
made-up copy and a composite digitisation both explain that, and the blank-paper test against `B`'s title
page discriminates them.

### What was built, and what it caught

- **`setting()` / `witnesses_to()` / `assert_same_setting()`** in the registry. The year had always been in
  the witness dict; only `wid()` ever read it, so no code path could notice the contradiction. A collation
  across settings now raises rather than silently conflating — and it fails silently by nature, because two
  editions of one translation agree for pages at a time and diverge exactly where the reading matters.
- **`test_setting_guard.py`** — positive and negative, the negative being that a cross-setting collation is
  refused, plus a regression that no NT witness may claim 1582 unless its body is 1582.
- **`test_counts_vs_doc.py`** — parses the §1.1 table out of the plan and diffs `wid` / leaves / primary
  against the registry. 12/12 agree, and the negative case was *proven* by injecting a wrong leaf count and
  watching it fail. This one exists because the prose and the code had disagreed for four months with
  nothing able to notice.

**Then the audit caught a compounding defect.** R7 found 39 ground-truth files read from `F`; **nine of them
are NT files**, so they were read from a 1633 book while being recorded as 1582 readings. That is a worse
class than R7's: R7's files are *unverifiable* at their raster, these are *the wrong edition*, and
re-reading a 1633 leaf at 545 ppi fixes nothing.

`audit_gt_rasters.py` had been reporting those nine under `F`'s **resolution** bar — a true statement that
buried the one that mattered — because `BARRED` was keyed on the **siglum alone**. That is the original
error in miniature: the assumption that a copy has one character across every volume. `F` is
low-resolution in the OT and a different edition in the NT. The registry now carries `TRANSCRIBED` and
`attests_transcribed_setting()`, and the audit reports `WRONG SETTING` **first**. It returns `None` rather
than `False` for the whole-Bible `OT` pseudo-volume behind `M`'s 1635 prelims — admitted *because* it is
another edition — and the test asserts that distinction, since collapsing "not the text" into "not
applicable" is precisely how `NT-F` stayed admissible. **Nine files flagged, no others.**

### R4.1 — the STC/ESTC deadlock broke, using something held locally all along

ESTC still returns `no such index`; USTC 404, Virginia JavaScript-only, Jisc 403, LC 403. The catalogues
that were reachable were dealer and auction listings, which the rule bars from promoting anything.

The route around it was **the holding libraries' own MARC records, which the Internet Archive exposes** at
`archive.org/metadata/<id>` under `metadata.references` — already on disk, never queried. Boston Public
Library's record gives, for the 1582 NT: `ESTC S102491; STC (2nd ed.) 2884; Darlow & Moule 134; Herbert 177;
Allison & Rogers II, 173`, LCCN 16019327, signatures `a-c⁴ d² A-5D⁴ 5E²`. For the 1609/10 OT:
`STC (2nd ed.) 2207; ESTC S101944; Darlow & Moule 300`. It also gives BPL's own call numbers — NT
**G.404.11**, OT **G.404.12** — refining §1.3, and records that OT2 repeats pp. 1001–1004 with 1003–1004
misbound between 994 and 995.

**This settles the one-digit disagreement in favour of S102491**; the sources reading S102419 are the dealer
listings. **Nothing is promoted yet.** One institutional authority is not two, and the rule is being held
rather than relaxed — the point of a two-authority rule is precisely the single-digit error a lone source
cannot catch.

### An acquisition target, and the discipline it must be admitted under

IA `thenewtestamento00rhei` — **Princeton Theological Seminary, call no. 13737**, 1582, imagecount 732, with
a continuous-tone `_orig_jp2.tar`. Defective: *"Lacks pages before p. 9, 205-6, 337-8, 373-4, 423-4, 461-2,
after 742."* The *"after 742"* is consistent with the 1582's own pagination, where `B` has Apocalypse ch.
XXII at 743 — **promising, and not proof.**

**It must be setting-verified before admission**, by the method that caught this: printed page number and
running head at three or more separated points against a known-good same-setting partner. That test is
minutes of work, and it is the one nobody ran for four months.

### Method notes

- **Setting verification** = printed page number + running head at **≥3 separated points**, against a
  known-good same-setting partner. Cheap and decisive.
- **Blank-paper NCC discriminates same-*copy* from same-*setting*** — but the strip must be **verified
  blank**. The 0.62–0.95 band used for the Censure leaves is *text* on ordinary leaves; the first run was
  invalid for that reason before it was re-cropped.
- `M` is bitonal CCITT, so **grayscale NCC against continuous-tone scans is a dead metric** — it returns
  0.067 even for two genuine 1582 title pages. A null from it is not evidence.

## Session 10 — R8.4: every witness audited for setting, and the audit audited itself

Session 9 ended with an uncomfortable statement: eleven of the twelve witness records were **unchecked, not
sound**. `F`'s mis-filing had been found by accident, and the concordance that was supposed to catch such
things had verified **title pages** — which is exactly what `F` borrowed. This session ran the check.

### Method

`witness/verify_setting.py` crops the head of a leaf, where the running head and the printed page number
sit, at probes spread through each witness (22/42/62/82%, so no two are adjacent), and assembles one contact
sheet per witness. Where two witnesses claiming a setting did not land on the same printed page, a second
targeted pass put them there. **The criterion is agreement at the same *printed page*** — page number,
running head, sidehead, text and line breaks together.

Two things were deliberately not accepted as proof. **A constant leaf offset**, because that is a property
of the binding and the digitisation while the page number is a property of the printing — and because it is
not even reliably constant: `OT2-1610-B`'s drifts 10 → 12 across the volume, which is just its nine interior
plate and blank leaves. And **a title page**, for the obvious reason.

Leaf access goes through `leaves()`, which is admissible for all twelve: a render preserves page order and
page content, and a page number survives interpolation. `M`'s JP2 package is the broken one, so its probes
come from its PDF — its primary artefact anyway — via the existing extractor, which owns the `leaf_range`
offset that puts M's leaf 0 at package page 2072. The fallback refuses to fire for a JP2-primary witness:
an unreadable JP2 there is a defect, not a routing question.

### Result — eleven verified, one unverifiable, no second mis-filing

| setting | witnesses | matched printed pages |
|---|---|---|
| NT 1582 Rhemes | `B` · `M` · `X` | 149, 309, 469, 629 |
| NT 1633 Rouen | `F` · `R` | 147 (this session), 332, 530, 682, 690 |
| OT1 1609 Douai | `B` · `P` · `F` | 223, 457, 919 (`B`/`P` also 687; `P`/`F` also 222, 224, 918, 920) |
| OT2 1610 Douai | `B` · `P` · `F` | 243, 473, 931 (`P`/`F` also 242, 244, 930, 932) |
| OT 1635 Rouen | `M` alone | **none possible** |

Agreement at each matched page is line-for-line **including the marginal apparatus**, which is what makes it
setting identity rather than textual resemblance — OT1 p.223 carries the same sidehead `lawes.` and the same
marginal *":: VVhere great faults are cōmitted, punishment is inflicted ac-"* in all three copies; OT2 p.473
the same *"moueth a charitable hart to compassion. So the Prophet lamen-"*.

**The negative control is the part worth keeping.** At printed page **147**, under the *identical* running
head *ACCORDING TO S. LVKE*, `B` prints Luke 4:31 — *"And he vvent dovvne into Capharnaum a citie of
Galilee"* — and `F` and `R` print Luke 7:44, *"vnto Simon : Doest thou see this woman?"*. Same page number,
same running head, different text. §1.1c's whole finding, visible in one crop. A test that only ever passes
tells you nothing about the corpus; this one demonstrably separates settings, which is what makes the eleven
passes worth stating.

A smaller thing worth recording: `OT1-1609-B`[719]'s page number is genuinely ambiguous by eye — 657 or 687
— and was settled by the leaf offset, then confirmed when `P`[711] turned out to print **687** at the same
section opening with the same ornamental band. That is a call resolved by corroboration rather than by the
glyph, and it is flagged in §1.1b rather than passed over.

### `OT-1635-M` is not verified — it is unverifiable, and that is a different sentence

It is the sole record of the 1635 Rouen setting, so no partner exists to collate it against. Its date rests
on **internal evidence**: its own colophon *M.DC.XXXV* and the ten-year privilege of 3 August 1634 that it
prints, which must precede the printing it licenses. Respectable, and not this test.
`witness/test_setting_verified.py` holds it in an explicit `SOLE_WITNESS` entry that records what the
setting *does* rest on, and **fails if a same-setting partner ever arrives** and is not then collated —
so the exemption cannot quietly outlive its reason.

### What stops recurrence

The guard fails when a registered witness has **no readings at all**. Absence presents as absence rather
than passing by silence, which is the R1.4 rule — an unmeasurable quantity must not be emitted as a
measurement — applied to provenance instead of to ink. Both branches proven by injection: a dropped witness
and a verification standing on a single matched page each fail, and exit code 1 was checked rather than
assumed.

### The audit overstated its own result, and the guard caught it

The first draft of the §1.1b table credited `OT1-1609-B` with matching at pp. 222, 224, 918 and 920. Those
pages were read on the `P` and `F` crops; `B` was never probed at any of them. The `verified_pairs` list was
hand-authored, and nothing checked that a page a pair *claims* is actually present in **both** witnesses'
readings — so the guard would have passed a fabricated pair.

That is the four-month defect at small scale: **a claim asserted in one file and unsupported in the file
holding the evidence.** The check now exists, it failed on the real data, and the corrected figure is three
shared points for `B` rather than seven. The conclusion did not change and the number was wrong, and those
are different things.

### New question the audit raised and cannot settle — R8.7

`NT-1582-M` and `NT-1582-X` have the **same leaf count (800) and the same leaf-to-printed-page map at every
probe** (176 → 149, 336 → 309, 496 → 469, 656 → 629), while `B` runs five leaves later throughout.
Same-setting does not require that: page numbers must agree, leaf indices need not.

Two readings are open and neither is asserted. Either both were reduced to the same book block by the same
obvious convention — strip the library apparatus, begin at the title page — which for one edition yields one
answer; or they share a source. **The existing record already argues against the second**: `B` lacks the
Censure and Preface p.1 outright, `M` carries both, and §1.4 identifies `M` as the source of `X`'s two
supplied leaves — a file cannot supply what it was derived from. R8.7 should test whether that argument
holds before reaching for a new measurement, and ⚠ **`M` is bitonal CCITT, so grayscale NCC against a
continuous-tone scan is a dead metric here** (0.067 for two genuine 1582 title pages); a null from it is not
evidence.

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

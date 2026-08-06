# OriginalDR — Master Plan

**Objective**: a faithful documentary transcript of the first-edition Douay-Rheims Bible — the **1582
Rheims New Testament**, the **1609 Douai Old Testament volume 1**, and the **1610 Douai Old Testament
volume 2** — reproducing archaic typeset and archaic spelling as printed, from photographic surrogates.

Companion documents: `OCR-EXECUTIVE-SUMMARY.md` · `OCR-OVERVIEW.md` · `OCR-WALKTHROUGH.md`.
Campaign operating documents: `CAMPAIGN-STATUS.md` · `CHAPTER-WORKFLOW.md` · `WALKTHROUGH-PROTOCOL.md`.

---

## 0. CONSTITUTION

### 0.1 What is being built

**One documentary transcript of three printed books.** Not a critical edition, not a reconstruction of a
lost archetype, and not six independent publication-quality OCR transcripts.

This is a **documentary/diplomatic edition** in the sense of TEI P5 ch. 11, *Representation of Primary
Sources*. The distinction is load-bearing and determines most of what follows. A critical edition
*constructs* a text from witnesses of differing authority — its apparatus of sigla, historical collation,
rejected readings and authority chains exists to justify that construction. We are not constructing
anything. **We are reading three physical objects, and disagreement between two photographs of the same
setting of type is a scan-quality fact, not a textual one.**

### 0.2 Rules

1. **The base document is a named exemplar of a named edition-issue** — a specific physical copy, chosen on
   physical grounds and documented **with the losing candidates and the reason each lost**.
2. **The transcript reproduces what that document prints**: spelling, glyph forms, ligature presence,
   punctuation, capitalisation, and compositorial evidence (turned letters, wrong-fount sorts) as set.
3. **Nothing is synthesised.** No rule-generated spelling ever enters the transcript. Where a reading cannot
   be established, the transcript **records a gap** — it does not guess.
4. **Illegibility resolved from another photograph of the same setting of type is transcription, not
   emendation** (§0.3).
5. **Supply from a different setting is an intervention** — bracketed in every view, carrying the supplying
   document's identity and date.
6. **Every reading is addressable and checkable**: page and signature in the output, always.

### 0.3 Two disjoint channels

Resolving a blot from a second photograph of the same forme is *reading the document*. Taking a word from a
different printing is *altering* it. Merged into one apparatus, thousands of routine legibility resolutions
bury the handful of real interventions.

**The setting-identity test, applied before any cross-copy use**: same signature, same catchword, **same
line-end words**. Identical ⇒ same setting. Setting identity is **proved, never assumed**.

| channel | when | recorded as | where it appears |
|---|---|---|---|
| **Surrogate register** | base copy illegible; a **same-setting** copy resolves it | `resolved_from: <copy id> @facs zone` + certainty, and nothing else | machine-readable sidecar; **summarised statistically** in the editorial statement — never enumerated as apparatus |
| **Intervention apparatus** | supply from a **different setting**, or a demonstrable press error | `supplied-from-other-setting` + the source's identity **and date** | **bracketed in the reading text**, every view |

### 0.4 The three units

| level | unit | why this granularity |
|---|---|---|
| **bibliographic** | **edition-issue** (NT 1582 · OT1 1609 · OT2 1610) | three separate printings, two towns, two houses, 27 years apart, different founts and compositor conventions |
| **exemplar** | one named copy per bibliographic unit | **this is the document being transcribed** |
| **substitution** | **gathering / forme** | stop-press correction is a forme phenomenon: two copies of one edition differ gathering by gathering |

The deliverable is **three documentary transcripts concatenated**, each labelled, **with no accidental
harmonisation across the joins**. Where the base exemplar is defective and another copy supplies leaves,
that is declared **leaf by leaf in a made-up-copy table**.

### 0.5 Discipline on measurement

Two failure modes are forbidden by name, because both are easy to reach from good intentions:

- **Status-quo preservation dressed as empiricism** — treating an ambiguous measurement as licence to keep
  the incumbent. An ambiguous measurement licenses **a better experiment**, never a lowered requirement.
- **Unstartability** — a requirement so demanding that nothing can begin produces the *same observable
  outcome* as preserving the status quo. Every prerequisite carries a **stated hour ceiling and a
  pre-registered decision rule before it starts.**

Where a number must be reported before properly-sized evidence exists, it is reported **with its confidence
interval and the label PROVISIONAL / non-citable**, and **no gate closes on it.**

**No below-threshold result is ever given a terminal accepted state.** A unit that fails its threshold is
**OPEN and blocking**; a safeguard that fires raises an **ALERT that the approach needs redesign** and never
constitutes acceptance.

---

## 1. THE CORPUS

### 1.1 The files, and what they actually are

Ten scan files are held. **They are not ten witnesses.** Measurement (§1.2) and bibliographic verification
(§1.3) reduce them to **seven independent witnesses across three volumes**.

Each file's **primary artefact** — the JP2 package or the PDF — is established per item in §1.2, not assumed
from the file extension.

| volume | copy | primary artefact | leaves | status |
|---|---|---|---|---|
| **NT 1582** | `NT/S01` | PDF `S01_…/nt-1582.pdf` | 765 | independent witness |
| | `NT/S08` | PDF `S08_…/S08.pdf` | 800 | **NOT a witness — `NT/S09` re-wrapped** |
| | `NT/S09` | JP2 `S09_…/nevvtestamentofi00mart_jp2` | 812 | independent witness — **base exemplar** |
| | `NT/S04` | JP2 `S04_…/newtestamentofie00engl_jp2` | **778** | **1633 witness support** (§1.4) |
| | `NT/S06` | JP2 `S06_…/Douay-Rheims-1610-Bible_jp2` (leaves 2072–2871) | 800 | **NT frontmatter witness** — see below |
| **OT1 1609** | `OT1/S01` | PDF `S01_…/ot1-1609.pdf` | 1135 | independent witness |
| | `OT1/S03a` | JP2 `S03_…/holiebiblefaithf01engl_jp2` | 1146 | independent witness |
| | `OT1/S09` | JP2 `S09_…/holiebiblefaithf00mart_0_jp2` | 1160 | independent witness |
| **OT2 1610** | `OT2/S01` | PDF `S01_…/ot2-1610.pdf` | 1128 | independent witness |
| | `OT2/S03b` | JP2 `S03_…/holiebiblefaithf02engl_jp2` | 1146 | independent witness |
| | `OT2/S09` | JP2 `S09_…/holiebiblefaithf00mart_jp2` | 1150 | independent witness — **base exemplar** |

Root: `palimpsest/imports/Scripture/Bibles/DouayRheims_DR/sources/scans/`.

#### `S06` — what it actually is, and why the earlier exclusion was wrong on its facts

**The plan previously excluded `S06` as "a modern facsimile, not a witness to the setting." That
description was wrong twice, and the error cost the edition its only genuine 1582 Censure leaf.**

`S06` is a **2007 print-on-demand publication** (*Maximus Scriptorius Publications*, Acrobat Distiller,
ABBYY FineReader, letter-size 612 × 792 pt pages, 1-bit CCITT at ~380 ppi). But the *images inside it are
photographs of original early-modern copies*, and its own title page says which: **"1635 AD Douay Old
Testament, 1582 AD Rheims New Testament."** Being republished in 2007 does not make the leaves a facsimile
in the sense that matters — a facsimile is a *redrawing*, and these are photographs.

- **Its OT is 1635, not 1610** — *"Printed by IOHN COVSTVRIER. PERMISSV SVPERIORVM. **M.DC.XXXV**"*, i.e.
  Rouen, the same printer as `S04`. This is the **second edition of the Douay OT**, a distinct setting.
- **Its NT is a 1582 Rheims Fogny** — *"PRINTED AT RHEMES, by Iohn Fogny. **1582.** CVM PRIVILEGIO."*
  (leaf 2072), **the same setting as the base exemplar**, and from a copy that is *not* `NT/S09`.

**`S06` remains excluded as a witness to the biblical verse text**: it is bitonal, re-laid-out on
letter-size pages, and its OT is the wrong edition entirely. **It is admitted for frontmatter and
backmatter only**, where it is decisive (§1.4, §1.1b).

**What `S06` settles that nothing else could.** Its NT frontmatter carries **the Censure and the Preface
p.1 in the 1582 setting** — the two leaves for which the plan previously recorded *"no genuine 1582 reading
survives anywhere in the corpus."* Block-registered correlation identifies them as the source of `NT/S08`'s
two made-up leaves, and the match is diagonal while every cross-pairing collapses:

| | `S06[2073]` Censure | `S06[2074]` Preface p.1 | 1633 setting (`S04`, `S01nt`) |
|---|---|---|---|
| **`S08[1]`** (supplied Censure) | **+0.424** | +0.000 | −0.036 … +0.012 |
| **`S08[2]`** (supplied Preface p.1) | +0.017 | **+0.398** | +0.055 … +0.212 |

Confirmed visually: `S06[2073]` and `S08[1]` agree line for line — same two-line heading with **no
ornamental headpiece**, the same decorated initial, the same four signatories, and the same closing
**S. Augustine quotation** (*"S. August. lib. 1. c. 3. de serm. Do. in monte"*) with its English gloss and
catchword. The 1633 Censure (`S04`) differs plainly: it carries a foliate headpiece, adds the subtitle
***"of the first Edition of this Translated New Testament,"*** and has **no** Augustine quotation.

**The subtitle is what dates them.** A Censure headed *"of the first Edition"* is a later edition referring
back to an earlier one; the version without that subtitle is the one printed in the edition it approves.
**`S06`'s NT frontmatter is therefore the 1582 reading, and `S04`'s is the 1633 reprint's.** This resolves
the open question of `NT/S08`'s fourth source (§1.4).

**`S06`'s backmatter also carries the edition's legal record.** Leaf 2070 prints *Faults escaped in the
printing* for **both** tomes, followed by the **`EXTRAICT DV PRIVILEGE DV ROY`** — a ten-year privilege
granted at Paris on **3 August 1634** to Jean le Cousturier of Rouen to print *"La Bible en language
anglois, **de l'edition de Laurens Kellam Imprimeur de Douay**."* The 1635 OT is thus, by its own
statement, a reprint **of the Kellam Douai edition** — which is why its front and back matter are worth
collating against 1609/1610 even though its verse text is not.

**`S04` (1633 Rouen, Cousturier, "the fourth Edition") is admitted for the NT only**, as witness support and
not as copy-text. The NT needs it: `NT/S09` is frontmatter-defective and `NT/S01` is contaminated (§1.4), so
without S04 there is no independent reading for the leaves in question. The OT volumes remain
**first-edition only** — admitting a second setting there would require a witness typology and an apparatus
of readings across settings, cost that buys nothing for a documentary transcript of a single printing.

### 1.1a Addressing and sigla

Two generations of identifier have already failed here. `archive-*` / `jp2-*` / `pdf-*` named *how a file
was acquired*, not which book it was. `S01`…`S09` named an acquisition batch — and `S01` and `S09` each
contain **all three volumes**, so "per source" would have pooled the 1582 Rheims types with the 1609/1610
Douai types. Both are retired.

**The witness id is `VOLUME-YEAR-SIGLUM`**, and the siglum names the **physical copy**, following
textual-criticism practice:

| siglum | copy | digitised by |
|---|---|---|
| **B** | **B**oston Public Library — G.404.12 v.1/v.2, BS2080 1582 | Internet Archive, Boston |
| **P** | **P**rinceton Theological Seminary, Lenox donation — 12904, Shelf 1844 | Internet Archive, `nj` |
| **R** | Princeton Theological Seminary, 1633 **R**ouen — call no. 13733, Shelf 1852 | Internet Archive, `nj` |
| **F** | a copy **owned and digitised by the Fatima Movement** (`fatimamovement.com`) | the Fatima Movement, pub. 2014 |
| **M** | the copies behind the 2007 ***M**aximus Scriptorius* reprint — 1635 Rouen OT, 1582 Rheims NT | unknown; republished 2007 |
| **X** | not a distinct copy — `B` re-wrapped and re-rendered (§1.2) | — |

| witness id | legacy | role |
|---|---|---|
| `NT-1582-B` | `NT/S09` | **base exemplar** |
| `NT-1582-F` | `NT/S01` | **independent witness, low-resolution scan** |
| `NT-1633-R` | `NT/S04` | witness support |
| `NT-1582-M` | `NT/S06` | **frontmatter witness** (leaves 2072–2871) |
| `NT-1582-X` | `NT/S08` | excluded — not a distinct copy |
| `OT1-1609-B` | `OT1/S09` | **base exemplar** |
| `OT1-1609-P` | `OT1/S03a` | surrogate |
| `OT1-1609-F` | `OT1/S01` | **independent witness, low-resolution scan** |
| `OT2-1610-B` | `OT2/S09` | **base exemplar** |
| `OT2-1610-P` | `OT2/S03b` | surrogate |
| `OT2-1610-F` | `OT2/S01` | **independent witness, low-resolution scan** |

#### What the role terms mean

These are working terms, not standard bibliographical vocabulary, and they were used for several drafts
without being defined anywhere. Each names **a permission and a limit**, and every one is a statement about
what a *file* may be used for — never a ranking of the *copies*.

| term | means | may be used for | may **not** be used for |
|---|---|---|---|
| **base exemplar** | the copy the transcript is taken *from*. In a documentary edition there is exactly one per volume, and it **is** the text | every reading; training crops; CER evaluation | — |
| **surrogate** | a second scan of the **same setting**, at usable resolution | resolving a locus the base exemplar cannot answer — damage, show-through, an inked-over sort; training augmentation | supplying a reading where the base is legible and simply disagreed with |
| **witness support** | a copy of a **different edition**, admitted for named leaves only | a reading where the base exemplar has **no** leaf at all, flagged as supplied with its source named | anything the base exemplar can answer; anywhere its own setting would be silently imported |
| **frontmatter witness** | admitted for prelims and endmatter, excluded from the verse text | Censure, Approbation, Preface, Tables, errata, privileges | any verse of scripture |
| **independent witness, low-resolution scan** | a genuinely distinct physical copy whose *digitisation* resolves too little for glyph-level work | collation, page order, completeness, presence/absence of leaves, and **any reading no better-resolved witness carries** | training data; CER evaluation; adjudicating long-ſ against `f`, where the distinguishing nub is under 1.6 px |
| **excluded** | not a distinct copy or not a witness to the setting | audit and provenance only | anything evidential |

**Note the last two are deliberately different.** *Excluded* is a judgement about the artefact's identity;
*low-resolution scan* is a measured constraint on one digitisation of a real and independent copy.

#### On `F` — what was subordinated, what was not, and what has been corrected

An earlier draft called `F` a *"rehost; physical copy not yet identified"* and gave its role as
**"structure only."** Both were wrong in ways worth naming, because they subordinated the **copy** on
evidence that only ever concerned the **scan**.

- **The copy is identified.** It belongs to and was digitised by the **Fatima Movement**, whose three
  volumes were published to the Internet Archive on 2014-07-28 (§1.3). "Not yet identified" conflated *"we
  cannot name a library shelfmark"* with *"we do not know whose copy this is."* We do know.
- **`F` is not less complete than the library copies — for the Old Testament it is exactly as complete.**
  Measured leaf by leaf, `OT1-1609-F` and `OT1-1609-P` contain **the same 1132-leaf book block**, opening
  at the same title page and closing at *"THE END OF THE FIRST TOME"* on printed page 1114. The entire
  11-leaf difference is library binding, flyleaves, a bookplate and imaging targets (§1.1b).
- **For the New Testament `F` is *more* complete than the base exemplar at the point that matters.**
  `NT-1582-B` **lacks its Censure and Preface p.1 outright**; `NT-1582-F` has both. A witness that supplies
  what the base exemplar is missing is not a subordinate witness there — it governs.
- **What does hold is a measurement about the images, not the book.** `F`'s primary artefact carries one
  **800 × 1124** JPEG per page, about **168 ppi at the leaf** against ~545 ppi for `B` (§1.2). The nub that
  separates long-ſ from `f` spans 3–6 px at 545 ppi and **under 1.6 px** at 168. That is a limit on
  glyph-level work only, and it says nothing about the copy's authority, completeness or antiquity.

**So the role is now stated as what the evidence supports**: `F` is an **independent witness whose
digitisation is low-resolution**. It is not "structure only" — it carries readings wherever no
better-resolved witness has the leaf, and in the NT prelims that is precisely the case.

> **One qualification, stated rather than buried.** The OT accounting above is complete and `F` comes out
> equal. The NT accounting is **not yet complete**: `NT-1582-F`'s block runs 765 leaves against
> `NT-1582-B`'s 801, and those 36 leaves are not yet attributed leaf by leaf. Until they are, no claim is
> made in either direction about NT completeness. §1.1b gives the method and the roadmap gives the step
> (R3.5); this is an open measurement, not a verdict against the copy.

Why the year is in the id: the NT admits two editions (§1.1), so `NT-1582-B` and `NT-1633-R` must be
distinguishable at a glance, and a bare `NT-R` would hide the edition difference that governs how the
witness may be used.

**Stable paths.** Witnesses are addressed at
`sources/witnesses/<VOLUME>/<WITNESS-ID>/leaves/`, a **symlink farm** over the JP2 packages with a
`MANIFEST.json` alongside. Symlinks rather than copies: copying duplicates ~11 GB and creates a second
artefact that can drift from the first, whereas a broken link fails loudly where a stale duplicate fails
silently. The registry (`witness/witnesses.py`) is the single source of truth, and
`witness/make_witness_tree.py` rebuilds and **verifies** the tree — every path resolving, every leaf count
matching the registry.

**The leaf, not the file index, is the addressing unit.** Leaf indices do not correspond between witnesses
of the same volume (§1.4, §2 Gate 0c): the NT witnesses differ by up to 47 leaves before a word is compared.
Leaves are keyed by **`(volume, printed page number, signature, side)`**.

### 1.1b What accounts for the leaf-count differences

**Leaf counts differ because the files photograph different amounts of *object*, not different amounts of
*book*.** A library digitisation photographs the binding, the bookplate, the flyleaves and a colour target;
a privately made scan usually starts at the title page. Comparing raw totals therefore compares
photographic conventions, and the plan's early "the NT witnesses differ by up to 47 leaves" was a statement
about scanning practice, not about textual completeness.

The correct unit is the **book block**: the leaves of the printed book itself, from title page to final
printed leaf. Every difference below is attributed to a named cause, read off the leaves.

#### OT1 1609 — `F` and `P` are the same book, leaf for leaf

| | `OT1-1609-P` (Princeton) | `OT1-1609-F` (Fatima) |
|---|---|---|
| binding boards | leaves 0–1 (2) | — |
| **bookplate leaf** | leaf 2 — *"Donation of James Lenox Esq"*, arms, *"LIBRARY OF THE Theological Seminary, PRINCETON, N.J. Case SCC, Shelf 1844, Book v.1"*, ms. *"1st Edition Scarce"* | — |
| flyleaves, ms. notes | leaves 3–4 (2) | — |
| **title page** | leaf 5 | leaf 0 |
| **duplicate title page** | — | leaf 1 (re-processed second capture of the same leaf) |
| *Approbatio* (Duaci 8 Nov. 1609) | leaf 6 | leaf 2 |
| *To the Right Welbeloved English Reader* | leaves 7– | leaves 3– |
| **book block** (title page → *"THE END OF THE FIRST TOME"*, printed p. 1114) | leaves 5–1136 = **1132** | leaves 0–1132 less the duplicate = **1132** |
| terminal blanks | leaves 1137–1139 (3) | leaves 1133–1134 (2) |
| board, colour targets, greyscale charts, calibration | leaves 1140–1145 (6) | — |
| **total** | 5 + 1132 + 3 + 6 = **1146** | 1132 + 1 + 2 = **1135** |

**Both close on the same words at the same printed page.** The whole 11-leaf difference is
**5 leaves of library apparatus at the front, 6 of binding and imaging targets at the back, less 1
duplicate title page and 1 fewer terminal blank in `F`** — and **not one leaf of text**. On the evidence,
the Fatima copy of OT1 is neither more nor less complete than the Princeton copy; it is the same book,
photographed without the library's furniture.

`OT1-1609-B` (Boston) totals 1160 on the same block, its surplus lying in 12 leaves of leading apparatus,
2 trailing, and 10 interior binding/target leaves — the same kind of difference, at a scanning centre with
a fuller target protocol.

#### NT 1582 — the one real content difference, and it runs in `F`'s favour

| leaf | `NT-1582-B` (Boston) | `NT-1582-F` (Fatima) | `NT-1582-M` (`S06`) |
|---|---|---|---|
| title page (Rhemes, Fogny, 1582) | present | present (**and duplicated**) | present |
| **Censure and Approbation** | **ABSENT** | present — *but in the 1633 setting* (§1.4) | **present, 1582 setting** |
| **Preface p.1** | **ABSENT** | present — *but in the 1633 setting* | **present, 1582 setting** |
| binding / bookplate | 5 leading, 6 trailing | none | none |

So for the NT the base exemplar is the *defective* copy, `F` supplies the missing openings from a later
edition, and only `M` supplies them in the edition's own setting.

**Still to be attributed**: `NT-1582-F`'s block is **765** leaves against `NT-1582-B`'s **801**. Thirty-six
leaves are unaccounted, and they are not explained by binding, because `F` has none. The three candidate
causes are distinguishable and none may be assumed: leaves **wanting in the Fatima copy**; back matter
(Table of Controversies, *Hard Wordes Explicated*) **present in `B` and absent in `F`**; or leaves
**dropped in `F`'s digitisation**. `F` closes on an errata leaf while `B` closes on *Hard Wordes* — which
points at the second, but pointing is not attributing. **The leaf map (R3.2) resolves this by printed page
number and signature, and until it runs the difference stays open in both directions** (roadmap R3.5). — establish primacy per item, then measure the primary

**Which file is primary is a fact about each item, not a rule about formats.** Internet Archive records the
derivation chain for every file it holds, in the `source` and `original` fields of
`https://archive.org/metadata/<identifier>`. Reading it settles the question by evidence:

| item | JP2 package is… | derived from | ⇒ primary artefact |
|---|---|---|---|
| `nevvtestamentofi00mart` (`NT/S09`) | derivative | `…_orig_jp2.tar` — **the capture originals** | **the JP2s** |
| `holiebiblefaithf0*engl` / `…mart*` (`S03a/b`, `OT/S09`) | derivative | `…_orig_jp2.tar` | **the JP2s** |
| `1582RhemesNewTestament` (`NT/S08`) | derivative | **`1582_Rhemes_New_Testament.pdf`** (`source: original`) | **the PDF** |
| `1582DouaiRheims…1/2/3Of3` (`S01` ×3) | derivative | **the uploaded PDF** (`source: original`) | **the PDF** |
| ~~`1582douayrheimsnt`~~ → **`newtestamentofie00engl`** (`NT/S04`) | derivative | ~~an uploaded PDF~~ → **`…_orig_jp2.tar`** | **the JP2s**, once the original was acquired — §1.2a |

For the institutional captures the JP2s are the originals and the PDF is IA's derivative. **For the five
`S01`, `S08` and `S04` files as originally held, the direction was reversed**: a user uploaded a PDF, and
IA *rendered* the JP2 package from it. Measuring those JP2s does not measure a scan — it measures a
rendering decision. `S04` has since been replaced by its own original digitisation and has moved back to
the first group; the four `S01` and `S08` files have no original to move to.

> **Check every item; do not extrapolate from four.** `NT/S04` was the fifth, and it did not behave like
> the other four — it was the one case where the inherited artefact was genuinely binarised (§1.2a). Had
> the rule been generalised from the `S01`/`S08` result, the exception that matters most to §1.4 would have
> been the one missed, and it would have been missed *quietly*: the render measures as continuous tone.

> **This corrects the blanket rule this section previously carried** ("the JP2 packages are the primary
> source; the PDFs are derivatives"). It is true of the institutional items and **false of the user
> uploads**, and the difference is checkable in one API call rather than assumed from the file extension.

**The rendering is demonstrable, not inferred.** Both user-uploaded PDFs were produced by *Adobe Acrobat
Image Conversion Plug-in* and carry **one JPEG per page with the page box in points equal to the image in
pixels** — so 1 px = 1 pt = 1/72 in, and the nominal page is absurdly large. IA rendered each at a fixed
DPI of its own choosing:

| item | embedded JPEG | page box | IA render | ratio |
|---|---|---|---|---|
| `NT/S08` | 2955 × 4343 | 2955 × 4343 pt | 5910 × 8686 | **2.00× (144 dpi)** |
| `OT1/S01`, `OT2/S01` | 800 × 1124 | 800 × 1124 pt | 3334 × 4684 | **4.17× (300 dpi)** |
| `NT/S01` | 800 × 1124 | 800 × 1124 pt | 800 × 1124 | 1.00× (72 dpi) |

Every ratio above 1.00 is interpolation. **The JP2 pixel counts of `S01` and `S08` carry no information
about the scan**, and the local copies of all three `S01` PDFs plus `S08.pdf` are **byte-identical (md5) to
the IA originals**, so the embedded JPEG is the true ceiling.

| copy | primary raster | distinct leaf sizes | tone | line pitch (px) | ppi |
|---|---|---|---|---|---|
| `NT/S01` | **800 × 1124** *(PDF)* | 1 | continuous | 22 | ~168 — **too low, see below** |
| `NT/S04` | **2439 × 3423** *(JP2, acquired)* | — | continuous, 190–228 levels | — | 400 |
| `NT/S08` | **2955 × 4343** *(PDF)* | — | continuous | — | **= `NT/S09`; not a witness** |
| `NT/S09` | 2955 × 4343 | 8 | continuous | 106 | — (see below) |
| `OT1/S01` | **800 × 1124** *(PDF)* | 1 | continuous | — | ~168 — **too low** |
| `OT1/S03a` | 2262 × 3116 | 4 | continuous | 66 | ~411 |
| `OT1/S09` | 3092 × 4367 | 23 | continuous | 88 | **~545 (calibrated)** |
| `OT2/S01` | **800 × 1124** *(PDF)* | 1 | continuous | — | ~168 — **too low** |
| `OT2/S03b` | 2196 × 2999 | 16 | continuous | 66 | ~411 |
| `OT2/S09` | 3151 × 4352 | 28 | continuous | 88 | **~545 (calibrated)** |

> **`S01` is 800 × 1124 in all three volumes — the original reading was right.** An intermediate draft
> recorded `OT1/S01` and `OT2/S01` as 3334 × 4684 and concluded the PDFs were downsampled derivations. The
> derivation chain shows the reverse: those PDFs are the md5-verified uploads and the large JP2s are
> 300-dpi renders of them. Sampled at pages 50/300/700/1000, **every page of all three volumes is
> 800 × 1124**. The disqualification of `S01` on resolution therefore stands, and stands for all three
> volumes: at ~168 ppi the nub distinguishing long-ſ from `f` — 3–6 px at 545 ppi — spans under 1.6 px and
> is not present in the file.

**All ten are continuous tone at source — but only after §1.2a**, and re-tested against each item's
*primary* artefact rather than assumed from format. Nine were so already; the tenth, `NT/S04`, was not, and
was made so by acquiring its original rather than by reasoning about it. The
institutional PDFs (`NT/S09`, `S03a`) are MRC composites — a 167-ppi JPX background, a 500-ppi JPX
foreground and a **1-bit JBIG2 mask** — while their JP2 originals are continuous tone. The user-uploaded
PDFs (`S08`, `S01` ×3) carry a **plain 8-bit RGB JPEG per page, no mask and no JBIG2 anywhere in the
chain**. For those nine the MRC/JBIG2 structure exists only in IA's PDF derivation, so the binarisation
transfer gap of §3.1 is **an artefact we would introduce**, and it is avoided by taking each item's primary
artefact as established above.

### 1.2a `NT/S04` is the exception: for this witness the binarisation is inherited

**The tenth file breaks the rule, and it is the one §1.4 depends on.** `NT/S04`'s primary artefact is not a
user's photograph set but **an IA-produced MRC PDF** — Creator *"Digitized by the Internet Archive"*,
Producer *"Recoded by LuraDocument PDF"* — which a user then re-uploaded as a new item. Its structure at
pages 50/300/600 is identical throughout:

| layer | raster | encoding |
|---|---|---|
| background | 813 × 1141 @ 133 ppi | JPX, continuous |
| foreground | 2439 × 3423 @ 400 ppi | JPX, continuous |
| **text mask** | **2439 × 3423 @ 400 ppi** | **1-bit JBIG2** |

**So the text layer we hold for `S04` is binarised, and there is no continuous-tone original among our
files.** Its 3659 × 5134 JP2 package is IA's render *of that composite*: the renderer decodes the JBIG2
mask and composites it, producing a leaf that measures as continuous tone — 213 grey levels, 91% midtone —
while carrying a 1-bit text layer underneath. **That measurement was taken on the render and does not
establish continuous tone for `S04`.** This is exactly the trap the primacy rule exists to catch, and it is
caught only because primacy was checked per item rather than generalised.

**The remedy is acquisition, not reconstruction.** `S04`'s original digitisation is on IA as
**`newtestamentofie00engl`**, and it is the same copy: *Princeton Theological Seminary Library*, matching
the bookplate and shelf mark read off `S04`'s own leaves (§1.3). It carries
**`newtestamentofie00engl_orig_jp2.tar` (`source: original`, 580 MB)** — the continuous-tone capture
originals — plus full institutional metadata: **call number 13733**, OCLC **1049890088**, scanning centre
`nj`, sponsor MSN, imagecount **776** against our 772 pages.

**ACQUIRED — 2026-08-05.** `newtestamentofie00engl_jp2` is on disk beside the file it supersedes, and
`NT-1633-R` now resolves to it. Three acceptance checks, all met:

| check | result |
|---|---|
| same physical copy | **NCC 0.990** against the superseded render, at a constant offset of −1 |
| continuous tone | **190–228 grey levels**, 59–95% midtone, at leaves 5/50/300/600 |
| raster | **2439 × 3423** — the MRC foreground's native raster, i.e. the capture's own |

Two things follow. The held file's 3659 × 5134 was itself a 600-dpi render of a 452 × 638 pt page, so it
was **1.5× interpolation on top of a binarised text layer** — the failure compounded rather than merely
occurring. And the 1-bit mask is now out of the chain entirely: the restriction below is lifted, and
`NT-1633-R` may carry a reading.

> **This was a required acquisition, not an optimisation.** `S04` is admitted solely as witness support for
> the Censure and Preface leaves (§1.4), and those are the two leaves for which **no genuine 1582 reading
> survives anywhere in the corpus**. Taking a diplomatic reading of them from a 1-bit JBIG2 mask would have
> re-imported, at the single most consequential point in the edition, precisely the loss §3.1 withdrew its
> recovery machinery for.

**ppi is calibrated, not assumed.** `OT1/S09` leaf 0 is a calibration leaf carrying an imperial ruler, a
metric ruler and a colour target. FFT tick-pitch: metric 21.286 px/mm → **540.7 ppi**; imperial 34.706
px per 1/16 in → **555.3 ppi**. Two independent rulers agreeing to **2.7%** fix the S09 OT captures at
**~545 ppi**. Physical line pitch follows as **0.1606 in**, which propagates ppi to the other copies of the
same setting. Cross-check: 3092 × 4367 px at 545 ppi = **5.64 × 7.97 in**, a **quarto** — correct for the
1609 Douai OT. *No ppi is stated for the NT: neither NT scan carries a calibration leaf and the 1582 Rheims
is a different setting, so its physical line pitch cannot be borrowed from the OT.*

**Per-leaf size variance is a capture fingerprint.** S03a/S03b/S09 show **4–28 distinct leaf sizes** —
variable cropping, the signature of a real capture session, where each leaf is framed and cropped
individually. **All three S01 volumes have exactly one size on every page sampled**, which is what a batch
resize to a fixed target produces and what a capture session does not. The fingerprint agrees with the
derivation chain above: `S01` is a re-processed set, not a capture.

> An intermediate draft argued S01 was upsampled *because its computed ppi exceeded S09's while its detail
> did not*. That argument is now void — it rested on the 3334 × 4684 render, and S01's primary raster is
> 800 × 1124 (above). The conclusion is unchanged and better grounded: S01 is disqualified on **measured
> resolution**, directly, with no inference about upsampling required.

**The re-uploads cannot answer completeness questions either, and this narrows "structure-only".** Their
processing raises the whole leaf, so their ink floors sit **14–20× above the threshold that defines a blank
leaf** — 0.141 for `S08`, 0.188–0.196 for the three `S01` volumes, against 0.010 — while every genuine
capture floors at **exactly 0.0000**. A blank leaf is therefore not distinguishable from a lightly-printed
one anywhere in those four files. The leaf inventory reports `BLANK`/`SPARSE` as **UNRESOLVABLE** for them
rather than as zero, and their leading and trailing runs as **lower bounds**: a zero would have read as the
finding *"the rehost stripped its blanks"*, which the measurement cannot support (roadmap R1.4).
**They carry page order; whether a leaf is wanting, blank or supplied rests on the `B` and `P`
witnesses.**

> This is a fourth line of evidence for the split in §1.2, and an unplanned one — the ink floor has nothing
> to do with derivation chains, page boxes or spectra. It sorts the ten witnesses into the same two groups,
> and `NT/S04` moved from the second group to the first when its original was acquired.

**`NT/S08` is empty magnification — it is not a witness.** It is dimensionally an exact **2.000×** of
`NT/S09` (aspect ratio identical to five decimals) and correlates with it at **NCC = 1.000** at a constant
leaf offset. Downsampled to S09's grid it matches at **0.9847**. The decisive test is spectral:

| measurement | value |
|---|---|
| S08 energy above S09's Nyquist (leaves 200/400/500/600/700) | 0.00008 – 0.00033 |
| a plain **Lanczos 2× upscale of S09**, same band | 0.00012 – 0.00092 |
| **S09 measured in its own top band** (positive control) | **0.0074 – 0.0097** |

A genuine scan's top octave is **full**; S08's extra octave is **empty**, and emptier than a naive
interpolation. **S08 carries no information beyond S09.** It is retained only because two of its leaves
come from elsewhere (§1.4). The NT raster ceiling is **S09's 2955 × 4343**.

**The mechanism is now known, and it confirms the measurement.** S08's magnification was not the
uploader's doing: the uploaded PDF holds JPEGs at **2955 × 4343 — exactly `NT/S09`'s raster** — and IA
rendered its JP2 package from that PDF at 144 dpi, doubling it. So the chain is *BPL capture → re-wrapped
as a PDF → rendered 2× by IA*. This explains every observation independently: the exact 2.000× ratio, the
NCC of 1.000, and a top octave emptier than Lanczos (a renderer's interpolation, not a lens). **`NT/S08` is
the Boston Public Library scan at one remove, and adds nothing to it.**

**Base exemplars** — declared on the evidence above, losing candidates and reasons recorded per §0.2.1:

| volume | base exemplar | why | surrogate | rejected |
|---|---|---|---|---|
| NT 1582 | **`NT/S09`** | only true-resolution scan of the setting | `NT/S01` (structure only) | `NT/S08` — the same scan, rendered 2× |
| OT1 1609 | **`OT1/S09`** | ~545 ppi calibrated, highest real detail | `OT1/S03a` (~411 ppi) | `OT1/S01` — 800 × 1124, ~168 ppi |
| OT2 1610 | **`OT2/S09`** | ~545 ppi calibrated, highest real detail | `OT2/S03b` (~411 ppi) | `OT2/S01` — 800 × 1124, ~168 ppi |

The S01 volumes are **structure-only**: page order, book/chapter addressing, collation and gross
verification. They are independent witnesses and are **not** discarded, but they are not copy-text and not
recognition training data.

### 1.3 The source concordance

Verified from the leaves themselves and from Internet Archive metadata. **Dates are taken from the title
page, never from catalogue metadata** — see the 1610 correction below.

| copy | IA identifier | repository | shelfmark | date **from title page** | printer |
|---|---|---|---|---|---|
| `OT1/S03a` | `holiebiblefaithf01engl` | **Princeton Theological Seminary** | 12904; Case SCC, Shelf 1844, v.1 | **M.DC.IX = 1609** | Doway: Laurence Kellam |
| `OT2/S03b` | `holiebiblefaithf02engl` | **Princeton Theological Seminary** | 12904; v.2 | **M.DC.X = 1610** | Doway: Laurence Kellam |
| `OT1/S09` | `holiebiblefaithf00mart_0` | **Boston Public Library** | BS180 1609; **G.404.12 v.1** | **M.DC.IX = 1609** | Doway: Laurence Kellam |
| `OT2/S09` | `holiebiblefaithf00mart` | **Boston Public Library** | BS180 1609; **G.404.12 v.2** | **M.DC.X = 1610** | Doway: Laurence Kellam |
| `NT/S09` | `nevvtestamentofi00mart` | **Boston Public Library** | BS2080 1582 | **1582** | Rhemes: Iohn Fogny |
| `NT/S04` | `1582douayrheimsnt` — **re-upload; the original digitisation is `newtestamentofie00engl`** | **Princeton Theological Seminary Library** | **call no. 13733**; Case SCC, Shelf 1852; OCLC 1049890088 | **1633**, "the fourth Edition" | Roan: Iohn Cousturier |
| `NT/S01` | `1582DouaiRheimsDouayRheimsFirstEdition3Of31582NewTestament` | **NOT ESTABLISHED** | — | **1582** | Rhemes: Iohn Fogny |
| `OT1/S01` | `1582DouaiRheimsDouayRheimsFirstEdition1Of31609OldTestament` | **NOT ESTABLISHED** | — | 1609 | Doway: Laurence Kellam |
| `OT2/S01` | `1582DouaiRheimsDouayRheimsFirstEdition2Of31610OldTestament` | **NOT ESTABLISHED** | — | 1610 | Doway: Laurence Kellam |
| `NT/S08` | `1582RhemesNewTestament` | **NOT ESTABLISHED** — but see below | — | **1582** | Rhemes: Iohn Fogny |

**Two-volume sets, confirmed physically** (not merely by shared call number): `S03a`+`S03b` are one
Princeton set — the same *"Donation of James Lenox Esq"* bookplate and arms, marked v.1 and v.2.
`OT1/S09`+`OT2/S09` are one BPL set — the same armorial plate (*NEC TEMERE NEC TIMIDE*) and the paired
shelfmark G.404.12 v.1 / v.2.

> **The 1610 correction.** Internet Archive dates **both** OT-vol-2 records "1609". The title page of each
> reads **M.DC.X**. The catalogue error is inherited from the **approbation** printed on the following leaf
> (*"Duaci 8. Nouembris. 1609"*). **OT2 is 1610.** This is why the concordance rule is title-page-first.

**`NOT ESTABLISHED` is a finding here, not a gap left open.** The four remaining items were traced to their
Internet Archive records and those records were read. All four are **user uploads to the `folkscanomy`
collection**, not institutional digitisations, and the difference is visible in the metadata: they carry an
uploader address and *Internet Archive HTML5 Uploader* as the "scanner", and they have **no
`scanningcenter`, no `contributor`, no `call_number` and no `external-identifier`** — the four fields
through which a library digitisation names its holding institution.

| item | uploaded | by | states of itself |
|---|---|---|---|
| `S01` ×3 | 2014-07-28 | `mrnobody@fatimamovement.com` | creator *"Douay (Douai) Rheims College — scanned by www.fatimamovement.com"* |
| `NT/S08` | 2017-12-12 | `jemlee15@gmail.com` | no creator; description only |

The `S01` creator string names the **book's originating college**, dissolved in 1793, not a modern holding
repository — it cannot be promoted to the repository field. This corroborates the `fatimamovement.com`
watermark found on every `S01` leaf from a second, independent direction: the watermark says who processed
the images, and the upload record says the same thing and dates it.

**For `NT/S08` the physical copy is nonetheless known**, by a different route: its uploaded PDF holds the
Boston Public Library capture at that capture's own raster (§1.2). Its repository is **BPL, G.404.12 /
BS2080 1582 — by identity with `NT/S09`, not by its own provenance.** It contributes no independent
witness, and only its two made-up leaves are its own (§1.4).

**`F`'s repository question is answered, and it was the wrong question.** The three `S01` volumes have no
library shelfmark because **they are not a library's copy**: they belong to the Fatima Movement, which
digitised and published them (§1.1a). "Repository and shelfmark unresolved" is therefore closed as
**not applicable — privately held**, which is a determinate answer, not a gap. What remains genuinely open
is narrower: the copy's own history before the Fatima Movement acquired it, which no catalogue can supply
and which does not block any transcription work.

**The `ourladyisgod.com` scans are the same files, not better ones.** The site (a Fatima Movement property)
publishes the three volumes as 3,027 page images alongside the same three PDFs, so it was worth testing
whether it hosts a higher-quality capture than the Internet Archive copies. It does not: sampled images
measure **800 × 1124**, identical to `F`'s primary raster, and correlate with the corresponding `OT1/S01`
leaves at **NCC 0.996–0.998** — the same images, offset by one because the site numbers from leaf 1.
**There is no higher-resolution capture of the Fatima copy at that source.** If one exists it would
materially change `F`'s role (§1.1a), so the question is worth putting to the Fatima Movement directly
rather than inferring further from what is published (roadmap R4.6).

**STC / ESTC — leads held, verification externally blocked.** The candidate numbers are **STC 2884 /
ESTC S102419** (1582 Rheims NT) and **STC 2207 / ESTC S101944** (1609–10 Douai OT), with Herbert 177 and
Herbert 300 respectively. **These remain leads and are not written into the concordance**, for two
reasons. First, secondary sources disagree on the NT: **S102419** and **S102491** both circulate, and a
one-digit difference between two live-looking identifiers is exactly the error a documentary edition must
not propagate. Second, the authority cannot currently adjudicate it — `estc.bl.uk` now redirects to
CERL, and the ESTC beta's search returns **`no such index [estc]`** for every query, so no record
resolves. This is an outage, not a dead end; the retry and the fallback authorities are specified at
roadmap R4.1.

### 1.4 Leaf-level contamination in the New Testament

**Provenance is a property of the leaf, not of the file.** Three of the four NT files are made up, in
different ways, and the affected leaves are the same two in every case.

| file | Censure & Approbation | Preface p. 1 | source of the supplied leaves |
|---|---|---|---|
| `NT/S09` | **absent** | **absent** | — (goes title page → Preface p.2) |
| `NT/S08` | supplied | supplied | **the 1582 setting, as witnessed by `NT/S06`** — resolved, §1.1 |
| `NT/S01` | supplied | supplied | **the 1633 Princeton copy (`NT/S04`)** — proven |
| `NT/S04` | present | present | native (1633 setting) |
| `NT/S06` | **present** | **present** | **native — 1582 setting** |

**Proof that `NT/S01`'s two leaves are `NT/S04`'s: blank-margin foxing.** Correlating **only blank paper**
— a crop containing no type, so a shared forme cannot explain a match — gives **+0.769** (Censure) and
**+0.694** (Preface 1) against controls of **+0.045 / +0.044**: 17–24× the control baseline. Corroborated
visually by an identically broken heading (`THE CENSVRE AND A___BATION`), identical smudging of the
subtitle, and identical stray-speck positions. Printing repeats; foxing does not.

**Direction of borrowing.** The leaf's own subtitle reads *"of the **firſt** Edition of this Tranſlated New
Teſtament"* — wording a 1582 first edition would not use of itself. `NT/S01`'s title page is the genuine
1582 Fogny setting, so within that file the Censure leaf **contradicts its own title page**. The leaves are
natively S04's.

**`NT/S08`'s fourth source is identified, and it is the 1582 setting.** Its substitutes are from neither
S01 nor S04: its Censure has **no headpiece, no "first Edition" subtitle, and an extra S. Augustine
quotation**, correlating with every S01/S04 frontmatter leaf at 0.01–0.15 (noise). Those three features are
exactly the frontmatter of **`NT/S06`**, and block-registered correlation gives **+0.424** and **+0.398**
on the matching pair against **0.000–0.036** on every cross-pairing (§1.1). The distinguishing subtitle
dates them: a Censure headed *"of the first Edition of this Translated New Testament"* is a later edition
looking back, so the setting **without** that subtitle is the edition's own.

> **Consequence for the edition — revised, and the earlier statement withdrawn.** This section previously
> concluded that **"no genuine 1582 Censure or Preface-p.1 leaf exists anywhere in this corpus."** That was
> true of the four NT files then under consideration and **false of the corpus**, because `S06` had been
> excluded on a mistaken description (§1.1) and never examined. **Both leaves survive, in the 1582 setting,
> in `NT-1582-M`.** They may therefore be transcribed as 1582 witnesses — from `M`, with its bitonal
> ~380 ppi raster recorded as the limiting factor and `S08`'s copy of the same setting available as a
> second image of the same reading.
>
> The lesson is procedural and belongs in the plan, not in a footnote: **an exclusion is a claim, and it
> inherits the evidential standard of any other claim.** `S06` was excluded on a one-line description that
> was wrong about its date, its printer and its nature, and the cost was a false "nothing survives"
> verdict at the most consequential point in the NT. **Excluded files are now re-examined before any
> "survives nowhere" conclusion is drawn** (roadmap R4.5).

**Independence, verified.** `NT/S01` matches neither S09 nor S08 at any alignment: wide ±80-leaf searches
peak at **0.040 / 0.068 / 0.096** with *mutually inconsistent* best offsets (+67, +82, −70), whereas the
genuine S08/S09 duplicate returns **1.000 at one constant offset**. Different leaf counts, different
binding, different signature series at the same opening. It is an independent digitisation of a different
physical copy.

### 1.5 Reference texts are finding aids, not authorities

Four modern/modernised transcriptions exist. **None is an authority over the image.**

| reference | arm | verses | % of union | chapters absent |
|---|---|---|---|---|
| `s_dismas` | archaic-preserving | 25,892 | 69.7% | 369 |
| `odr_com` | archaic-preserving | 16,201 | 43.6% | 774 |
| `sabates_a` | modern | 37,130 | 99.9% | 0 |
| `madueke_b` | modern | 35,809 | 96.3% | 26 |

Union: **37,166 verses across 1,360 chapters.**

They supply verse addressing, word identity, alignment anchors and ground-truth candidate generation.
**They never supply glyph identity.** `s_dismas` in particular is an unprovenanced transcription of unknown
base edition which **splices editorial annotation into scripture** — `ruth/1/1` and `genesis/10/1` both
carry apparatus in place of the verse tail. **A provenance audit runs before either archaic reference is
used at all**: 200 verses sampled against the scans, reporting each transcription's `ſ`/`s` accuracy, its
ligature policy and its base edition, published.

**8,383 loci have no archaic reference.** This is a **QC-coverage figure, not a transcript gap** — the
scans contain those books. The risk it names is precise: **where the OCR is uncertain *and* no archaic
reference exists, a plausible hallucination is indistinguishable from a reading.** The remedies are the
abstention machinery of §4 and a **stratification quota** for those books.

**Reporting standard for any reference comparison** (mandatory): offset-0 similarity as **primary**;
best-match-within-window as a **labelled diagnostic**; a **permutation null** with the margin over null
reported; and the metric computed a **second time with glyphs unfolded** — that second number is the only
one relevant to archaic work.

**Blocking defect**: 8.0% of verses best-match at a non-zero verse offset. `ref_renumber` is incomplete,
concentrated in Psalms, Acts, Luke, Matthew and Mark, and **every verse-keyed comparison of the two archaic
references is invalid until it is finished.**

---

## 2. WHAT MUST BE ESTABLISHED BEFORE STEP 0

The concordance carries these fields per copy:

**edition-issue · STC/ESTC number · volume · repository and shelfmark · scan provenance · completeness and
imperfections · made-up leaves · raster properties.**

**Resolved** (§1.2–§1.4): raster properties and calibrated ppi · date-from-title-page for every copy ·
repository, shelfmark and set membership for the five Princeton and BPL copies · witness independence for
all ten files · made-up leaves and their sources for the New Testament · **base exemplars declared**, with
losing candidates and reasons recorded.

**Outstanding, and blocking:**

**Gate 0a — bibliographic completion.** (i) Repository and shelfmark for the four `S01` files and for
`NT/S08`. (ii) **STC / ESTC numbers for every copy**, verified against ESTC and cross-checked against the
held OCLC record numbers — the STC numbers in earlier notes are **unverified leads and are not to be
written into the concordance**. (iii) Identification of the fourth source supplying `NT/S08`'s two
frontmatter leaves.

**Gate 0b — completeness and collation.** Per copy: a leaf inventory against the expected signature
collation, listing **wanting leaves, duplicated leaves, misbound leaves, and made-up leaves with the
supplying copy named.** §1.4 establishes that this cannot be skipped: three of four NT files are made up,
and the defect was invisible until the leaves were read. **A copy is not admitted as a witness for a given
leaf until that leaf is known to be native to it.**

**Gate 0c — cross-source leaf mapping.** A per-leaf correspondence table across the copies of each volume,
keyed to printed page number and signature, so that any leaf can be addressed in every witness at once.
Without it, "the same page" cannot be stated across copies — and §1.4 shows that leaf indices do **not**
correspond between files even within one volume.

**No transcription of any leaf begins before 0b and 0c are satisfied for that leaf.** Gate 0a may complete
in parallel; it constrains citation, not imaging.

---

## 3. STAGES 0–1 — RASTERS AND GEOMETRY

### 3.1 Acquire

**Read the JP2 leaves. Never the PDFs.** The JP2 packages are the delivered scans; the PDFs are
derivatives, and every destructive transformation in this corpus lives in the PDF wrapper — MRC
composition, JBIG2 binarisation of the text layer, and (for `S01` and `NT/S08`) resampling. Measured at
source, **all ten scan files are continuous tone** (§1.2).

> **This supersedes an earlier reading of the corpus.** The plan previously treated most copies as MRC
> composites with 1-bit JBIG2 text layers, and built a binarisation-recovery path around that. The
> structure was real but it belonged to the derivative, not the scan. **The binarisation problem is not
> inherited; it is one we would create.** It is avoided by reading the JP2s — not mitigated afterwards.
> The pseudo-grayscale reconstruction step this once required is **deleted**, not softened: there is no
> 1-bit layer in the working chain to reconstruct from.

Rules:
1. **No lossy or resampling step anywhere in the working chain.** PNG or TIFF only. No page-level resize;
   scaling happens once, inside the recognizer, at the declared line height.
2. **No autocontrast, denoise, sharpen or binarisation of our own** in the default path. Any tonal
   operation is per copy, measured, and recorded.
3. **Never up-sample to match another copy.** `NT/S08` demonstrates the failure: 4× the pixels of
   `NT/S09` and, measurably, none of its information (§1.2). Resolution differences between copies are
   carried as they are and recorded in the manifest.
4. **A raster manifest per copy** — path, native dimensions, bit depth, provenance, checksum — so a silent
   substitution is impossible and every experiment can name what it consumed. **The manifest records the
   JP2 as the source and the checksum of the leaf actually consumed.**

**One test remains, and it is a guard rather than a remedy:**

- **Derivative-contamination guard** (Gate 0d). Any leaf entering the working chain is verified to have
  come from the JP2 package: bit depth > 1, distinct grey levels > 64, and dimensions matching the JP2
  manifest. A PDF-derived leaf entering by accident is a **silent** defect — it looks like a page — so it
  is caught by assertion at load, not by inspection.

*The former JBIG2-substitution and binarisation-transfer-gap tests are withdrawn: both measured a property
of the PDF derivatives, and neither describes any raster the edition will consume.*

### 3.2 Geometry — shapes from ink, labels from text

Region polygons are derived so that **line geometry is not a descendant of the incumbent layout bands**.
Deriving polygons as hulls of aligned line boxes is self-defeating: those boxes were produced *under* the
bands, so labels inherit the bands' blind spots and boundary error is bounded below by the hull's error.

1. **Shapes from ink**: connected-component and projection-profile grouping on the native raster, plus a
   generic baseline segmenter over the **untyped full page**.
2. **Labels from text**, assigned to ink groups — MainText from alignment to the archaic reference;
   Marginalia from the 1,334 transcribed apparatus blocks; RunningHead / Catchword / Signature from
   self-verifying positional-and-text tests; VerseNumber from numeral-matches-adjacent-verse.
3. **Unaligned residue is positive evidence.** For each leaf, the fraction of the chapter's reference span
   matched by *no* line localises a missed or clipped region. That residue is a **labelling target, not a
   discard** — the mechanism by which the model learns the failures currently fixed by hand.
   **A reference-independent residue signal runs alongside it — ink groups with no line assignment —
   because the reference-based signal is null exactly where there is no reference** (the 8,383 loci).
4. **Invariant**: no ink of a typed group may fall outside its polygon.
5. **The geometric prior is an initialisation and plausibility clamp, not a vote.** As a vote it means the
   incumbent always carries, and it overrides precisely on the leaves where it is wrong. Disagreements
   resolve **against pixel evidence in the disputed strip**, adjudicated on the crop, with a recorded rule
   and a gate.
6. **DropCap is not a region class.** One instance per chapter, nested inside MainText, and region polygons
   with reading order handle nesting badly. It is detected as an **alignment deficit at chapter open**
   (reference `AFTER`, line reads `FTER`) and restored as a character.
7. **Marginalia negatives are mined explicitly** — only leaves with confirmed apparatus coverage contribute
   Marginalia-negative pixels, or every unlabelled marginal block becomes an implicit negative and teaches
   the model to suppress the class.
8. **Books with no archaic reference generate no distantly-supervised labels**, so the training set would
   otherwise be a non-random book subset. **Layout ground truth carries an explicit quota for them.**

**Gate 9**, published *before* the baseline is measured and sha-pinned, with the recognizer frozen:
**marginalia recall ≥0.85 and precision ≥0.90 at block-level n · MainText boundary error ≤8 px median,
≤25 px p95 · per-class IoU · n ≥ 125 eval pages.**

---

## 4. STAGE 2 — RECOGNITION

### 4.1 The archaic typeset census — establishing the inventory empirically

**This step runs before the codec is fixed, because a class the model never sees cannot be output, and a
class asserted but not present invites the model to hallucinate it out of damaged type.**

The inventory is **not** taken from a medieval glyph list, nor from assumption. It is established by
**survey of the actual type in each volume**, then given a representation, then frozen.

**Procedure**

1. **Sample** — a stratified page set per volume (text pages, annotation pages, display/heading pages),
   independent of the reference texts.
2. **Enumerate** — for each candidate sort: is it present in this volume's fount? At what frequency? In
   which fount (roman text / italic annotation / display)?
3. **Represent** — assign each attested sort a Unicode representation, preferring standard codepoints and
   combining marks; **no Private Use Area codepoints in output**.
4. **Adjudicate the ambiguous pairs** — where two names may denote one sort, decide by inspection and
   record the decision.
5. **Freeze** the inventory as a versioned document with an image exemplar per class.
6. **Anything not attested is not in the codec** — and is recorded as *surveyed, not found*, so the question
   is closed rather than left open.

**The census table.** Every row is resolved to ATTESTED or NOT FOUND per volume before the codec is built.

| requested | sort identity | representation | notes to resolve at census |
|---|---|---|---|
| long-s | long s | `ſ` U+017F | the basic non-terminal s of the fount |
| tall-s | — | — | **resolve: is this a second sort, or another name for long s?** Early-modern founts normally carry **two** s-sorts, round `s` and long `ſ`. If the census finds only two, "tall-s" and "long-s" denote the same sort and the row merges |
| long-f | — | — | **resolve.** There is no "long f" sort as such. Two real candidates produce this impression: (a) **long ſ carrying a full crossbar** rather than a left nub — some founts cut it this way, and it is then near-indistinguishable from `f`; (b) an `f` in a ligature. **If (a) is attested it is a genuine allograph of ſ and needs its own class**, because it defeats nub-based discrimination |
| ct ligature | ct | `ct` + ligature flag | presence-vs-absence recorded as a fact |
| ae ligature | æ | `æ` U+00E6 / `Æ` U+00C6 | |
| fi ligature | ﬁ | `ﬁ` U+FB01 | |
| fl ligature | ﬂ | `ﬂ` U+FB02 | |
| double-f ligature | ﬀ | `ﬀ` U+FB00 | |
| tall-st ligature | ſt | `ſt` U+FB05 | **resolve against "long-st"** — if tall-s and long-s are one sort, these two rows merge |
| long-st ligature | ſt | `ſt` U+FB05 | listed twice in the request; **merges unless the census finds two distinct st sorts** |
| long-sl ligature | ſl | `ſl` (no precomposed codepoint) | represent as `ſ`+`l` with a ligature flag |
| tall-sl ligature | ſl | as above | **merges with long-sl unless two sorts are found** |
| tall-sh ligature | ſh | `ſ`+`h` with ligature flag | |
| double tall-s ligature | ſſ | `ſ`+`ſ` with ligature flag | |
| double long-s ligature | ſſ | as above | **merges with the above unless two sorts are found** |
| a-tilde | ã | `ã` U+00E3 | suppressed nasal, **unexpanded** |
| o-tilde | õ | `õ` U+00F5 | suppressed nasal, **unexpanded** |
| u-tilde | ũ | `ũ` U+0169 | suppressed nasal, **unexpanded** |

**Also surveyed, because they are present in Douay-Rheims and their omission would make the transcript
unusable or wrong:**

- **Note-reference marks** — `*`, `†`, `‡`, `¶`, superscript letters. **In this edition the apparatus is
  roughly half the book; a transcript that drops the marks keying annotation to text cannot be used.**
- `ﬃ` and `ﬄ`; **`ſi`** alongside `ſh`/`ſl`; `œ`/`Œ`.
- `&` and Tironian forms; **roman numerals including terminal `ij`**; **Greek and Hebrew sorts** in the
  annotations; braces and printers' rules.
- **`u`/`v` and `i`/`j` as printed** — not normalised.
- **Under survey, decided by the census, not asserted here**: `ꝛ` (r-rotunda); the Latin brevigraphs
  `ꝑ ꝓ ꝗ`; and **whether these founts set any blackletter at all**. These three questions are entangled —
  r-rotunda belongs to blackletter, so a negative finding on blackletter closes it too. The brevigraphs, if
  present, will be in the Latin of the annotations and running heads rather than in scripture.

**Ligature presence versus absence is itself recorded data**, not normalised away: whether the compositor
set `ct` or `c`+`t` at a given locus is a fact about the forme.

**Machinery, not glyphs**: `<unclear cert="">` and `<gap reason="">`. Without them there is no way to say
*I cannot read this*, and an unreadable glyph is forced into a confident reading.

**Gate 4.1**: the census is published per volume with an image exemplar and a frequency count per attested
class, every ambiguous row resolved to a single sort or explicitly split, and every *not found* recorded.
**The codec is built from the census and from nothing else.**

### 4.2 Style is a stand-off layer, never a codec class

Italic, small capitals, swash capitals, blackletter, and `VV` for `W` are **rendition states of characters,
not characters.** Admitting them as codec classes multiplies the alphabet and destroys the rare-class
budget §4.3 exists to protect. A turned `u` standing for `n` is **a defect in a sort**, not a glyph;
encoding it as a character forces a reading decision into the codec.

- The **text channel** is a plain grapheme string with a **stable character index**.
- A **parallel span table** holds `{start, end, rend}` over that index (TEI `<span>`/`@spanTo`).
- **Font is recognised by a separate word-level classifier over the line image, never by the CTC head.**
- **Alignment and collation run on the character channel, unchanged.**
- **Scoring is two channels**: CER on characters, **plus span-level precision/recall/F on rendition,
  reported separately and never folded into CER.**
- Serialisation materialises spans into `<hi rend="italic">`, `<seg rend="sc">`, `@rend="blackletter"`, and
  carries `<sic>` with `@rend="turned"` / `@rend="wrong-fount"`.

If the style classifier is not built in the first generation, **style is explicitly scoped out and recorded
as a known non-preservation in the statement of editorial principles** — not left as an unbudgeted promise.

### 4.3 Rare classes

Ligatures and abbreviation marks are rare enough that under CTC a class with under ~100 instances is
essentially never emitted: the loss is lower if the model prints blank plus the frequent neighbour. Left
alone, this **silently deletes exactly the inventory the project exists to preserve.**

- **All inventory classes are atomic codec entries, in NFC.** Decomposing the tilde vowels is
  counterproductive: **CTC alignment is monotonic, and the mark sits *above* the bowl rather than after it**
  — there is no horizontal slice where the mark is present and the base is not, so a two-symbol target
  forces the network to invent an ordering the image does not contain, and the mark is absorbed into the
  base's frame run and dropped. Decomposition also doubles target length on those lines and makes CER count
  one visual error as two edits.
  **Pin NFC** across codec construction, ground-truth files and edit-distance scoring; mixed forms silently
  produce duplicate codec entries and a CER that is simply wrong. **Compose/decompose only at output
  serialisation.**
- Recover parameter sharing by **initialising the tilde-vowel output rows from their base-letter rows plus a
  shared learned offset.**
- **Oversampling is capped at 3–8× line replication.** Replication is line-level, so it duplicates the
  line's other ~40 characters, its fount, its page texture and its binarisation artefacts — and rare-class
  lines cluster in a few gatherings. Beyond ~8× the model memorises a handful of pages and, in letterpress,
  learns **the specific damaged sort rather than the class**. **Precision breaks before recall does.**
  Above that, switch mechanism to **per-class CTC loss weighting (∝ 1/√freq, capped ~10)**.
- **Synthetic line rendering** from a digitised fount with degradation, and **decode-time logit prior
  scaling** (÷ prior^α), carry most of the load without distorting training.
- **Any oversampling breaks the softmax as a probability of the real distribution** — calibrate on an
  **unweighted** held-out set.
- **Monitors at every checkpoint, per rare class**: precision **and the frequent neighbour's false-positive
  rate**; reliability diagram / ECE. If `ﬁ` recall climbs while `f`+`i` precision falls, the reweighting is
  buying nothing.
- **Report per-class support with every per-class metric.** Recall on 12 instances is noise.

### 4.4 Ligatures and allographs

**The inventory is a closed set** (§4.1), and that is the fact the method exploits. The ligature sorts of a
given fount are few, known, and **cut as distinct shapes** — a ligature sort is not two adjacent letters
that happen to touch, it is a different piece of type with its own form. Working from the closed set gives
three advantages that per-instance open-set classification does not have:

1. **A small, enumerable hypothesis space.** The question at a locus is never "which of 400 classes" but
   "is this the `ﬁ` sort or an `f` followed by an `i`" — a binary decision with a known answer set.
2. **Strong false-positive control.** A ligature can only be proposed where its constituent letters are
   expected, so accidental proposals are rejected by construction rather than by threshold.
3. **Post-transcription correction is tractable.** Because the set is closed and each class has a known
   orthographic distribution, a whole-corpus sweep can revisit every decision for a class at once when the
   class's model improves — which an open-set per-instance approach cannot offer.

**How a decision is made, in order:**

1. **The codec decides the high-support classes end-to-end.** `ſ`, `f`, `æ`, `ﬀ`, `ﬁ`, `ﬂ` and the tilde
   vowels are trained normally and are **never removed from the codec**. Long-ſ in particular has tens of
   thousands of instances and a decisive, always-present shape cue; routing it to an external classifier
   would remove a high-support class from end-to-end training and reintroduce the segment-then-classify
   pipeline CTC exists to avoid. **The dominant cause of `ſ`/`f` error is resolution** — the nub is 3–6 px
   at ~545 ppi (§1.2) and 2–4 px after rescaling to a 120 px line height — **and the remedies are resolution
   (§4.5) and decode-time prior correction, not a separate subsystem.**
2. **Connected-component shape analysis over the closed set** proposes candidates. This is used as a
   **candidate detector within the known ligature set**, not as a general glyph segmenter. The distinction
   matters: it is true that a well-inked forme has adjacent sorts touching and that CC count alone is a
   function of ink load — but **the pairs that ligature are a specific small set, and their sorts differ in
   form from the same two letters set separately**, which is a discriminative signal available exactly
   where it is needed. Only loci whose letters belong to the closed set are ever examined.
3. **A small CNN per contested pair** decides, on **fixed windows centred on the base model's emission
   frame**, at native resolution. The discriminators are pair-specific and visual:
   **`ﬁ`/`ﬂ` — the tittle is absent in the ligature sort** (that is the ligature's reason to exist);
   **`ﬀ` — one crossbar spanning both stems versus two**; **`ct`/`ſt` — the connecting arc**;
   **`ſſ` — the relationship of the two nubs and the shared shoulder.**
4. **Three-way output — `A` / `B` / `indeterminate`** — abstaining into `<unclear cert="">`. Clean instances
   reach 0.97–0.99 F1 for `ſ`/`f` and 0.90–0.95 for the ligature pairs; on the difficult tail — touching
   type, over-inking, show-through, worn sorts — realistic accuracy is 0.7–0.85, and **that tail is 10–20%
   of instances.** Calibrate the abstention threshold so per-class precision meets target, and **report the
   abstention rate as a headline number.**

   > **An 8% abstention rate on `ſ`/`f` is an honest edition; a 0% one is a fabricated one.**

5. **Exploit the sort, not the instance.** Letterpress repeats **the same physical piece of type** thousands
   of times. Cluster all candidate crops for a class **per fount per volume, unsupervised; key ~50 cluster
   exemplars by hand; propagate.** This is the strongest available lever and it is unavailable to
   per-instance classification.
6. **Whole-class re-sweep.** Because the set is closed, every decision for a class is revisited in one pass
   when that class's classifier is retrained. Ligature decisions are therefore **revisable data, not
   irreversible transcription events.**

**Mining instances is bootstrapped from the text side, never the shape side** — mining by shape requires the
classifier being trained. The procedure terminates:

1. **Contexts are enumerable with no classifier.** `ﬃ` occurs only where the letters are `ffi`. Search the
   references for tokens containing `ffi|ffl|st|fi|fl|ff|ſſ` contexts — thousands in a 400-page volume.
2. **Align those tokens with the incumbent recognizer over the fold-equivalent letters** — `f`, `i` are in
   the codec, so character cuts localise the window to ±1 character **even when the ligature is misread as
   `f`+`i` or dropped entirely.**
3. **Crop that window.** Every crop is a positive-context candidate, found without the classifier.
4. **Key ~200 per class**, storing them as **whole ground-truth lines with the locus marked, not as bare
   crops** — crops cannot score a line recognizer.
5. **Tilde vowels** are mined where the recognised token is exactly one character shorter than the reference
   token with a nasal at the deletion point.
6. **Declare and bound the recall bias**: this finds ligatures only where the reference spells the letters,
   missing compositorial ligatures at unexpected loci. **Bound it by keying a random 100-line sample and
   counting misses.**
7. **`ſ`/`f` cannot be seeded this way** — the references' `ſ` policy is unaudited — so it is seeded from
   the §1.3 provenance audit.

### 4.5 Model scope

```
CATMuS-Print [Large]  →  VOLUME  →  FOUNT
```

**VOLUME is the primary scope, and it is a letterform boundary.** The NT was printed at Rheims in 1582 and
the two OT volumes at Douai in 1609 and 1610 — different houses, different type, different compositor
conventions. A model pooled across volumes is pooled across founts that genuinely differ.

**FOUNT is the sub-scope within a volume**: roman text, italic annotation, display/heading. This is the axis
on which letterforms differ *inside* a book, and it is the same axis §4.2 declares semantic.

**COPY is not a model level.** The three copies of a volume photograph **the same setting of the same
type**; they differ in resolution, capture conditions, colour and skew — image statistics, not letterforms.
Treating copy as a model scope would fit a separate model to each photograph of one book.

Instead, **copies are pooled within a volume as training augmentation**, which is a genuine advantage of
this corpus: *identical letterforms under different imaging conditions* is precisely the invariance a
recognizer should learn, and it is normally expensive to obtain. **Held-out splits are stratified by copy
and by gathering** — never by page, since adjacent leaves of one gathering share paper, bleed-through, skew
and the same forme, and a page-level split puts near-duplicates on both sides.

**BOOK is not a scope.** Distinguishing 0.60% from 0.50% CER requires on the order of 10⁵ held-out
characters per comparison — more ground truth than this project will hold — and the books that would most
need a book model are exactly those with no archaic reference and therefore the least alignment ground
truth.

**Adoption at each surviving level requires** a paired bootstrap over lines, a pre-registered minimum effect
size, and a second never-touched confirmation set.

**Input height** is a settable parameter (`ketos train -s '[1,H,0,1 …]'`), and the sweep is costed honestly:
**only H=120 warm-starts cleanly from the pretrained model.** Raising H multiplies the height reaching the
reshape, hence the recurrent stack's input width, **breaking weight transfer at the reshape and LSTM**. The
correct joint move is a **height-only pooling stage** to restore the reshape dimension; changing width
pooling would alter frames-per-character and confound the sweep.

- Grid: 3 heights × 2 pooling variants, minus the invalid cell = **5 configs × 3 seeds = 15 runs**, because
  single-run variance exceeds the effect on rare classes.
- **120–200 GPU-hours.** Rank on a fixed ~5k-line subset (~40 h), confirm the top two at full data.
- **Decision metric pre-registered as `ſ`/`f` and tilde-vowel per-class F1 with a paired bootstrap over
  lines** — aggregate CER is dominated by classes 120 px already handles and cannot resolve the question.
- **Normalise to measured x-height, not line-box height.** Line boxes include variable ascender/descender
  and marginalia at other type sizes, so a fixed line-box height presents different stroke widths across
  copies at ~411 and ~545 ppi (§1.2).

### 4.6 Accuracy targets

| metric | target | measured on |
|---|---|---|
| **CER-folded** (long-ſ, ligatures, `æ` folded) | ≤ 1.0% | GOLD-TEXT |
| **CER-diplomatic** (full census inventory, nothing folded) | **measured floor + δ**, δ pre-registered *before* the floor is read | GOLD-TEXT |
| **per-class precision AND recall**, with support | published per class, no aggregate hiding | GOLD-TEXT + glyph census |
| **macro error over the rare inventory** | class-balanced | glyph census, **scored on host lines** |
| **line-segmentation error** (missed / merged / clipped) | pre-registered | GOLD-LAYOUT |
| **WER** | pre-registered | GOLD-TEXT |
| **rendition span P/R/F** | pre-registered, **never folded into CER** | GOLD-TEXT |
| **abstention rate** per contested pair | reported as a headline, not minimised | glyph census |

**Method notes that decide whether these numbers mean anything:**

- **Cluster bootstrap over pages, not Wilson intervals.** Character errors cluster strongly by line, page
  and fount; an i.i.d. Bernoulli interval runs **2–4× too narrow**.
- **Per-class error stratified by volume × fount × neighbour-context, reporting the maximum over strata,
  not the mean**, plus a **run-length statistic**. Without these the suite is passed by its most dangerous
  failure — **systematic attested substitution**: a model reading `ſ` for `f` in one specific context
  produces a real word, scores well on aggregate CER, and is diluted below detection because the class is
  right 97% of the time overall. Nothing that fails to condition on context can catch it.
- **Attested-form rate is a diagnostic and never a gate.** It penalises precisely the turned letters,
  wrong-fount sorts and compositorial spellings §0.2 requires preserving. Where attestation is used, score
  against an **external corpus (EEBO-TCP 1580–1640)** with overlap reported, and **enumerate the unattested
  tokens** rather than reducing them to a number.
- **The ground truth's own error rate is reported alongside every target.** If GOLD-TEXT's own CER is 1%, a
  0.5% target is unmeasurable in principle. Saying so is not a lowered requirement; it is the requirement
  becoming enforceable.

---

## 5. STAGE 3 — GROUND TRUTH

Alignment is **intra-page**: concatenate a page's recognised lines into one character stream with
line-boundary offsets, concatenate the chapter's reference likewise, align at character level, project each
line's range onto the reference span it matched, then refine per-character cuts by forced alignment.
Character-level alignment keeps `hea-` and `uen` on their own lines, which line-to-verse mapping cannot
express.

**Acceptance, and its complement.** A line becomes ground truth under a strict distance threshold, **and the
unaligned residue is recorded** as a geometry signal (§3.2.3). But acceptance is itself a censoring
mechanism: words the recognizer never read never enter ground truth, so the next generation trains on the
same censored distribution. **The fraction of reference span never accepted is recorded and reported per
generation as a blocking OPEN quantity.**

**Substitution costs are typographically motivated or estimated on GOLD-TEXT — never derived from the
pipeline's own confusion matrix.** Deriving them from the model's confusions makes `ſ`↔`f` cheap *because
the model confuses them*, so confused lines are accepted as ground truth and the confusion is trained in.
Costs are **frozen at the first generation**.

**Never align against the modern references for character supervision.** They supply word identity, never
glyph identity.

**No synthesised spelling enters ground truth or the transcript.** A rule-generated archaic form has no
document source. Its only legitimate use is as an alignment prior; it never appears in the edition, and it
may not act as a scoring prior that decides which lines pass acceptance, since that injects synthesis
through selection.

---

## 6. STAGES 4–6 — TRANSCRIBE, LOCATE, CONSULT

### 6.1 The correction loop

```
leaf (ranked by residue)
   ↓
lines ── recognizer ──→ proposed diplomatic text
   ↓                              ↓
line crop ─────────→ VLM proposes corrections on the crop
   ↓                              ↓
   └──→ operator: accept / reject / retype, by keystroke ──┘
                     ↓
          sha-pinned signed-off page
                     ↓
  ┌──────────┬───────────┬────────────┬──────────────┐
transcript  eval text  training GT  layout GT  glyph instances
```

**One activity, five outputs.** Gold-keying and production transcription are the same keystrokes; there is
no separate annotation project, which is what makes the annotation affordable at all.

- **The VLM sees a line crop, never a page** — the only point at which a vision model touches the product.
- **The board is not the metric here**; the corrected page *is* the reference.
- **Rolling held-out set, free and ungameable**: fine-tune every N signed-off pages, and measure CER on
  **the last 20 signed pages before they entered training.** Each slice is used exactly once.

**Pilot book: Micheas (Micah), OT2 1610 — 7 chapters across ~7 leaves, present in all three OT2 copies.**

It is chosen deliberately: it has **no archaic reference witness**, so it exercises the part of the corpus
that is structurally invisible to every reference-based mechanism and would otherwise be discovered last.
It is genuinely multi-chapter, at roughly **one chapter-open per leaf** — an unusually dense test of the
drop-cap, chapter-heading and chapter-boundary machinery — while remaining small enough to transcribe
completely and early. Smaller and larger alternatives in the same condition, if the scale proves wrong:
**Joel** (3 chapters, ~5 leaves) and **Amos** (9 chapters, ~11 leaves).

### 6.2 Locate

The tome map gives, for every page of every copy, its book and chapter, so lookup is a query rather than a
search. **Iterate the union verse table (37,166), not the archaic arm** — iterating the archaic arm silently
drops the books with no archaic witness, which are exactly the books that must not be omitted. The tome
map's coverage-by-construction is a tautology, not an accuracy claim, and needs a **held-out audit with a
reported page-assignment error rate.**

**Three independent signals for one address** — tome map (leaves), VerseNumber regions (numerals), alignment
(content) — and **a disagreement is a flag, not an average.** The printed numeral does not decide: psalm
titles counted as verse 1, `xv`/`xu` misprints, merged and split verses, and chapter-opens mid-page all
produce numerals that lie. **Content alignment assigns the address.**

**Two address systems, both carried on every line:**
- **Page and signature — the primary physical address.** Verses span pages, and the three volumes paginate
  differently.
- **Verse — the secondary logical address**, following **the base document's own numerals** where they
  exist, with any content-derived disagreement recorded as a separate attribute.
- **Never silently normalise to modern versification.**

### 6.3 Consult

Collation **detects**; it does not generate. A verse-level diff of each consulted copy against the base
transcript finds the disagreement loci. Each routes to exactly one of three places:

| situation | disposition |
|---|---|
| base document legible and stands | **no record** — the overwhelming majority |
| base illegible, **same-setting** copy resolves it | **surrogate register** (§0.3) — *transcription, not emendation* |
| **different-setting** supply, or a demonstrable press error | **intervention apparatus** — bracketed, with the supplying document's identity and date |

**The base document's reading stands unless the locus is individually and visibly emended. There is no
witness-voting path for spellings or glyph forms at all** — a reading assembled from different copies across
a verse is a text no compositor set.

**One guard survives**: image adjudication fires on low-confidence loci **and on a random sample of loci
where everything agrees.** Concurrence between a model and a reference that helped train it is not evidence,
and the unanimous sample is the only available estimator of the correlated-error rate.

---

## 7. EVALUATION ARCHITECTURE

### 7.1 Three tiers and a published query ledger

Freezing an evaluation set prevents contamination. It does **not** prevent adaptive leakage from repeated
querying: across generations, sweeps and escalation rungs a plan of this shape makes on the order of **57
adoption queries** against one set, and the expected maximum of 57 noise draws at realistic set sizes is
**~0.18% apparent improvement from nothing at all** — larger than any threshold worth setting.

| tier | use | discipline |
|---|---|---|
| **DEV-GOLD** | sweeps, escalation rungs, all iteration | unlimited |
| **VAL-GOLD** | generation-adoption decisions | **noised reporting, tolerance 0.3%, hard budget 20 queries, counter published in every report**; exhausting it requires keying new pages |
| **HOLDOUT-GOLD** | **opened once, at publication** | the only publishable numbers |

**Escalation pages go to DEV/train only — never to VAL or HOLDOUT.** Growing the evaluation set in response
to failing it is not an escalation rung.

### 7.2 Sizing

Diplomatic keying care is required **for the base exemplar only** — the other copies are scored folded, for
word identity. The correction loop (§6.1) then grows the set continuously as a by-product.

| set | scope | size | hours |
|---|---|---|---|
| **GOLD-TEXT** | base exemplar, grown by the correction loop | 200 lines to start | **8–12 h**, then free |
| **GOLD-LAYOUT** | eval half **split by gathering** | ~80 eval + ~60 seed | ~15–20 h, then free via the UI |
| **glyph census** | §7.3 | exhaustive on a declared page set | first generation |
| **NOISE-FLOOR** | §7.4 | 150 lines × 3 keyings | ~15 h + one paid validation |

**Non-negotiable**: a frozen, image-derived, never-trained-on evaluation half for text and layout. Without
it every number is circular. **It is ~15–20 hours, not 200.**

**Stratification**: **not by book** — 6 copies × 2 parities × 73 books is 876 cells for ~125 pages, and the
books that matter most get single-digit page counts. Stratify **copy × parity × page-type** (~48 cells,
≥3 pages each), **plus purposive over-sampling**: ≥40 pages from books with no archaic reference, ≥60 chosen
*because* they carry marginalia, with sampling weights recorded and the estimator re-weighted. **Report
marginalia metrics at block-level n.**

### 7.3 The glyph census — a census, not a rate

Rare classes occur tens of times corpus-wide. A fixed "≥200 instances per class" quota is unsatisfiable for
exactly those classes, and mining instances with the detector under evaluation makes misses invisible, so
**recall becomes unmeasurable by construction.**

- **Exhaustive keying of a declared page set**: every instance on N fully-keyed pages, so the denominator is
  **page-defined, not detector-defined.**
- **Clopper–Pearson intervals** on the true n.
- **Disjoint train/eval halves split by page**, never-train rule applied verbatim.
- **Census below n=30 ⇒ UNMEASURABLE ⇒ OPEN and blocking.** Never silently passed.
- **A census is stronger than a recall figure on twelve instances, not weaker.** Every instance found and
  adjudicated once, published as a list.

### 7.4 NOISE-FLOOR

CER-diplomatic's target is the measured floor plus δ, so the floor must not be able to lower the
requirement.

1. **δ is pre-registered before the floor is read.**
2. **Time-separated blind self-re-keying** — same operator, ≥3 weeks apart. This is an
   **intra-transcriber** floor and therefore a **lower bound** on the true floor, which is the conservative
   direction. **Labelled as such everywhere it appears.**
3. **Three keyings on 150 lines** rather than two on 300, to expose **correlated error** — two keyers
   sharing one protocol both misread the same worn `?` as `;` and both miss the same tilde, and that
   component is what actually bounds achievable CER.
4. **Per-class floors on a purposive census** of `ſ`/`f` and the tilde vowels (≥300 instances each). A
   line-sampled 300 lines yields perhaps five `ſ`/`f` disagreements — a floor for the edition's central
   distinction estimated from five events. **A single aggregate floor is not usable for a per-class target.**
5. **Buy ~8 hours of a second keyer for the 150 lines to validate the self-re-key once.** If the two
   diverge, **ALERT: the floor estimator needs redesign.**
6. Resolve each disagreement against a magnified crop and record a **per-class irreducible-ambiguity rate**.

### 7.5 Circularity — every path closed

| path | closure |
|---|---|
| alignment substitution costs from the pipeline's own confusions | typographically motivated or GOLD-TEXT-estimated; **frozen at G1** (§5) |
| confidence calibration on pipeline-generated ground truth | calibrate on GOLD-TEXT, **unweighted** |
| attested-form rate scored against a lexicon derived from the object under repair | **external corpus**, overlap reported; diagnostic only (§4.6) |
| residue-as-signal computed against a reference absent at 8,383 loci | **reference-independent residue**: ink groups with no line assignment (§3.2.3) |
| ground-truth acceptance censoring what the recognizer never read | **never-accepted span fraction reported per generation, blocking** (§5) |
| later-generation regions relabelled from earlier-generation alignment | external check is GOLD-LAYOUT under §7.1's query ledger |
| glyph instances mined by the detector under evaluation | **text-side mining** (§4.4) + **page-defined census** (§7.3) |

### 7.6 Generations

```
G0  incumbent geometry + incumbent recognizer  → bootstrap only, never a gate
G1  ink-derived regions + seed labels → region model v1 → recognizer v1 → alignment v1
G2  regions v2 (relabelled from v1 alignment) → recognizer v2 → alignment v2
```

**Primary scalar**: CER-diplomatic on VAL-GOLD. **Non-inferiority constraints holding simultaneously**:
marginalia recall and precision, boundary error, rare-class macro error. A free choice among five metrics is
not a convergence criterion.

| terminal | condition | disposition |
|---|---|---|
| **CONVERGED-AT-TARGET** | metric ≥ threshold ∧ Δ < δ | closed |
| **STALLED-BELOW-TARGET** | metric < threshold ∧ Δ < δ | **OPEN, blocking, ALERT for approach redesign. The deliverable does not ship.** |

**Regression rule**: if a generation is worse than its predecessor by more than the paired confidence
interval, it is a **failed experiment** — revert, do not adopt, **do not re-baseline.** Keep-best
checkpointing throughout. **δ is pre-registered per metric, and δ ≥ 2× the evaluation set's standard error
or the gate is void.**

### 7.7 Escalation

- **Pre-register 3 rungs and an hour ceiling per rung** before the generation starts.
- **Every escalation names a different resource class than the one that failed**: paid annotation hours, a
  better scan, an outside palaeographer's ruling, or **a stated reduction in coverage — fewer books at full
  fidelity — never a reduction in fidelity.**
- **Escalation writes a dated, numbered ALERT** naming the approach to be redesigned; the component parks as
  **OPEN with that number attached.** It is never terminal acceptance.
- **Release-blocking versus campaign-open**: base-exemplar loci are release-blocking; everything else is
  campaign-open. Both stay open; only one gates a version.

### 7.8 Gates

**Document-level invariant: no step enters the build order until its row carries metric · threshold · named
set · n · pre-registered effect size.**

| # | step | metric | threshold | set | n |
|---|---|---|---|---|---|
| **0a** | source concordance | fields resolved per copy | **100%, no UNKNOWN** | — | 9 copies |
| **0b** | completeness & collation | leaves inventoried vs expected signature collation | **100% per admitted copy**; wanting / duplicated / misbound / made-up all named | all copies | 10 files |
| **0c** | cross-source leaf mapping | leaves keyed to printed page + signature across copies of a volume | **100% of admitted leaves addressable in every witness** | all copies | per volume |
| **0d** | derivative-contamination guard | leaves failing the JP2 assertion at load | **0** | working chain | every leaf |
| **1** | drop-cap fix + page axis | cells moving to OPEN | **18, against a frozen board, never netted** | board | 18 |
| **2** | residue detector | leaf-ranking precision@50 vs known defects | **≥0.6** | campaign history | 50 leaves |
| **3** | **archaic typeset census** | every requested class resolved ATTESTED / NOT FOUND, per volume | **100% resolved; exemplar image + frequency per attested class** | census page set | stratified, per volume |
| **4** | pilot gold | keying rate and variance measured | **rate published** | pilot | 60 lines, 20 pages |
| **5** | R1 renumber | offset-0 exact-key agreement | **≥99.8%** | both archaic references | all 13,292 shared |
| **6** | R2 de-contaminate | **splice detection recall on seeded splices** | **≥0.90** | seeded set | ≥100 seeded |
| **7** | provenance audit | `ſ`/`s` accuracy, ligature policy, base edition | **published** (a characterisation, not a threshold) | scans | 200 verses |
| **8** | tome map | page-assignment error rate | **≤1%** | held-out | 300 pages |
| **9** | GOLD frozen | sha-pinned, **gathering-level split** | **frozen; per-class n published** | — | §7.2 |
| **10** | G1 geometry | marginalia recall / precision · boundary error | **≥0.85 / ≥0.90 · ≤8 px median, ≤25 px p95** | GOLD-LAYOUT, recognizer frozen | ≥125 pages |
| **11** | G1 recognition | CER-folded · CER-diplomatic · per-class · abstention | **≤1.0% · floor+δ · published per class · reported** | GOLD-TEXT | §7.2, cluster bootstrap |
| **12** | alignment | accepted-line precision · never-accepted span fraction | **≥0.98 · reported, blocking if rising** | held-out | 500 lines |
| **13** | G2 | primary scalar + non-inferiority set | **§7.6** | VAL-GOLD | budget 20 |
| **14** | publish | apparatus schema validates; **HOLDOUT opened once** | **machine-checkable completeness assertion** | HOLDOUT | — |

---

## 8. THE BOARD, AND THE APPARATUS

### 8.1 Board

- **The archaic-preeminent gate is not adopted on provenance.** Approval is provenance, not evidence, and
  the party proposing a change benefits from it. Before adoption: **blind-adjudicate a random sample of
  n ≥ 100 newly-passing cells against the scans** — adjudicator sees image and candidate reading, **not
  which gate it passed or which way it moved** — with the vindicating pass rate **pre-registered**. **Gains
  and losses are reported separately against a frozen board, never netted.**
- **A cell passing the archaic gate while failing the modern check badly is OPEN and blocking.** A warning
  is an alert, not a disposition; a below-threshold unit is never given a terminal non-blocking state.
- **A page axis**: every open cell carries its leaf, so a per-leaf view sorts geometry defects to the top by
  construction. This is what the residue detector writes into.
- **The drop-cap class is open.**

### 8.2 Minimal viable apparatus

**One record type, at intervention granularity — the overwhelming majority of verses produce zero
entries:**

```
{ locus:  signature + leaf side + line + char-offset   (e.g. Aa3v.12.7)
  verse:  secondary logical address
  category: gap | unclear | resolved-from-surrogate* | supplied-from-other-setting
          | sic-preserved | editorial-correction
  base_reading | adopted_reading | evidence | agent | cert }
```
`*` lives in the surrogate register (§0.3), not the apparatus.

**Once per edition, not per locus**: STC/ESTC, repository and shelfmark, made-up-leaf table; scan provenance
and checksums; **a statement of editorial principles listing what is silently normalised** (line breaks,
word division at line-end, whitespace) **so those never generate records**; a TEI header; a versioned,
sha-pinned release.

**`<pb n="" facs=""/>` and `<milestone unit="signature"/>` in the text stream are the one non-negotiable
obligation** — without them no reading can be checked against the book, and **they must be captured during
transcription or never.**

**Not recorded**: rejected variants and historical collation (ship the raw collation output as a data file,
not as prose); cross-exemplar press-variant collation as a programme (it needs multiple exemplars per forme
we do not have — a stated caveat plus opportunistic recording); uncertainty markup at every adjudicated
locus (restrict it to loci **not** resolved by the base image, or the markup is noise).

### 8.3 The uncertainty gradient

| state | encoding | plain-text export |
|---|---|---|
| read, confident | plain text | the reading |
| read, uncertain | `<unclear reason="damage\|inking" cert="low\|medium" resp="">` | **the reading, flagged** |
| not read | `<gap reason="damage" quantity="" unit="chars"/>` | **the gap, never a guess** |
| supplied from a **document** | `<supplied source="#..." cert="">` | **bracketed in every view** |

**`<supplied>` requires `@source` pointing at a document. Rule-generated text has no document source and can
never appear inside it.**

### 8.4 What is in the transcript

| class | policy |
|---|---|
| original line breaks | **preserved**, `<lb/>` |
| line-end hyphenation | `<lb break="no"/>`, both fragments kept |
| catchwords | **excluded** from the reading text, recorded |
| signatures | **recorded as milestones** (§8.2) |
| running heads | **recorded**, separate layer |
| chapter arguments | **included**, marked |
| marginal annotations | **included**, separate layer, **keyed to text by the §4.1 reference marks** |
| preface, chapter-end annotations | **included** |
| verse numerals | **recorded as printed**; addressing per §6.2 |
| word division, whitespace | **silently normalised**, declared in the editorial statement |

---

## 9. BUILD ORDER

| # | step | ships | depends on |
|---|---|---|---|
| **0** | Concordance completion (0a) + **collation/inventory (0b)** + **cross-source leaf map (0c)** | the addressable, provenanced corpus | — |
| **1** | Drop-cap board fix + page axis | 18 cells | — |
| **2** | Residue detector → ranked leaf defect queue | a working defect queue | — |
| **3** | **Archaic typeset census** (§4.1) | the frozen inventory the codec is built from | 0 |
| **4** | Raster policy: JP2-only chain, derivative guard, manifest | raster policy settled | 0 |
| **5** | **Correction loop on Micheas (OT2)** | transcript pages **and** GOLD-TEXT **and** GT **and** layout GT **and** census instances | 0, 2, 3 |
| **6** | R1 renumber; R2 de-contaminate; provenance audit | references usable as finding aids | — |
| **7** | Pilot gold — measures keying rate and variance | sizing evidence | 5 |
| **8** | GOLD-TEXT / GOLD-LAYOUT frozen (**by gathering**); NOISE-FLOOR; **δ pre-registered** | the frozen sets | 7 |
| **9** | Tome map + held-out audit | addressing | 6 |
| **10** | **G1 geometry** | region model v1 | 8, 2 |
| **11** | **G1 recognition** — census inventory, atomic NFC codec, x-height, VOLUME scope | recognizer v1 | 8, 3, 4 |
| **12** | Alignment; `unclear`/`gap` and page anchors in the data model | line GT at scale | 11 |
| **13** | Glyph census; text-side mining; pair CNNs with abstention; H sweep | rare-class evidence | 11, 12 |
| **14** | FOUNT scope; style classifier **or** explicit scope-out | recognizer v2 | 13 |
| **15** | G2; **HOLDOUT opened once**; apparatus; versioned release | the edition | all |

**Steps 1, 2, 4, 6 need no ground truth and no new model. Step 5 begins as soon as a base exemplar is
declared and the census is frozen. Nothing in the first quarter waits on step 8** — only metric *claims* do,
never improvements.

---

## 10. OPEN

**Blocking**: **Gate 0b** — per-copy completeness and collation; no copy is a witness for a leaf until
that leaf is known native to it (§1.4) · **Gate 0c** — the cross-source leaf map; leaf indices do not
correspond between files · **Gate 0a residue** — repository/shelfmark for the four `S01` files and
`NT/S08`; **STC/ESTC for every copy** · **the fourth source of `NT/S08`'s two frontmatter leaves**, the
only NT frontmatter candidate not already known to be 1633 · one citation carried unverified from earlier
work and load-bearing for §3.2's gate — **resolve or delete** · the archaic typeset census (§4.1).

**Open, scheduled**: pair-CNN separability
on the difficult tail and the abstention rate it forces · whether unsupervised sort clustering propagates as
cleanly as letterpress suggests · input height jointly with pooling · whether the style classifier is built
in G1 or style is formally scoped out.

**Unratified**: the archaic-preeminent gate, pending the blind adjudication of §8.1.

---

## 11. CITATIONS

**Technical**: arXiv:2112.12703 · arXiv:2511.08903 · arXiv:1802.10038 (Reul et al.) · arXiv:1711.09670 ·
arXiv:2509.19768 (CHURRO) · kraken documentation (VGSL input height, `ketos segtrain` typology, forced
alignment, codec construction) · CATMuS-Print [Large] and guidelines · Bollmann & Søgaard 2016 ·
Pettersson et al. 2014 · cSMTiser · Al Azawi et al. · OmniDocBench / olmOCR-Bench.

**Editorial**: **TEI P5 ch. 11, *Representation of Primary Sources*** (the framework this edition adopts) ·
Tanselle, "Editing Historical Documents" · Greg, "The Rationale of Copy-Text" and Bowers, *Principles of
Bibliographical Description* (consulted for base-exemplar selection and forme-level description; **their
apparatus obligations are not adopted**) · STC/ESTC practice for imperfect and made-up copies.

**Unverified, not to be relied upon**: arXiv:2607.00596 · candidate STC numbers for the 1582 NT and 1609 OT.

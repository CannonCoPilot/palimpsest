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

### 1.1 Nine scans: three volumes × three copies

All nine are copies of **one first-edition printing per volume**. This is the corpus; nothing else is in
scope.

| volume | copy | file | pages |
|---|---|---|---|
| **NT 1582** | `NT/S01` | `S01_1582-first-edition-3vol/nt-1582.pdf` | 765 |
| | `NT/S08` | `S08_1582-rhemes-nt-hires/S08.pdf` | 800 |
| | `NT/S09` | `S09_nevv-testament-mart-3vol/nevvtestamentofi00mart-NT.pdf` | 810 |
| **OT1 1609** | `OT1/S01` | `S01_1582-first-edition-3vol/ot1-1609.pdf` | 1135 |
| | `OT1/S03a` | `S03_holie-bible-engl-ot-vol1/S03a.pdf` | 1140 |
| | `OT1/S09` | `S09_.../holiebiblefaithf00mart_0-OT1.pdf` | 1156 |
| **OT2 1610** | `OT2/S01` | `S01_1582-first-edition-3vol/ot2-1610.pdf` | 1128 |
| | `OT2/S03b` | `S03_holie-bible-engl-ot-vol2/S03b.pdf` | 1134 |
| | `OT2/S09` | `S09_.../holiebiblefaithf00mart-OT2.pdf` | 1146 |

Root: `palimpsest/imports/Scripture/Bibles/DouayRheims_DR/sources/scans/`.

**Excluded, deliberately**: `S04_1633-rheims-nt` (a second-edition printing) and `S06_1610-facsimile-whole`.
Admitting a second edition would require a witness typology, sigla, and an apparatus of readings supplied
across settings — cost that buys nothing for a first-edition documentary transcript. **The three volumes
are transcribed from first-edition copies alone.**

> **Naming.** Legacy internal identifiers (`archive-*`, `jp2-*`, `pdf-*`) name *how a file was acquired*,
> not which book it is — and `S01` and `S09` each contain **all three volumes**. Those identifiers are
> retired from the plan. **The addressing unit is `VOLUME/COPY`**, e.g. `OT2/S03b`.

### 1.2 Measured raster properties

Sampled at multiple leaves per file, `pdfimages -list`:

| copy | native raster | encoding | effective ppi at the leaf | grayscale path |
|---|---|---|---|---|
| `NT/S01`, `OT1/S01`, `OT2/S01` | **800 × 1124** | RGB JPEG | **~168** | yes (but see below) |
| `NT/S08` | ~3035 × 4336 | **RGB JPEG, continuous tone** | ~430 | **yes — no bitonal layer at all** |
| `NT/S09` | 3035 × 4336 | JPX + JBIG2 mask (MRC) | ~500 | via the JPX layer |
| `OT1/S03a` | 2262 × 3116 | JPX + JBIG2 mask (MRC) | ~500 | via the JPX layer |
| `OT1/S09` | 3092 × 4367 | JPX + JBIG2 mask (MRC) | ~650 | via the JPX layer |
| `OT2/S03b` | 2196 × 2999 | JPX + JBIG2 mask (MRC) | ~400 | via the JPX layer |
| `OT2/S09` | 3117 × 4335 | JPX + JBIG2 mask (MRC) | ~650 | via the JPX layer |

**Two findings that constrain the design:**

**The S01 set cannot serve diplomatic work.** It is uniformly 800 × 1124 across all three volumes —
roughly **168 ppi at the leaf, versus 650 ppi for S09**. The long-ſ is distinguished from `f` by a nub of
**3–6 px at 650 ppi**; at 168 ppi that feature spans **under 1.6 px** and is not represented. S01 is
therefore **structure-only**: useful for page order, book/chapter addressing and gross verification, and
**disqualified as a base exemplar or as recognition training data.** This is a measurement, not a
preference.

**`NT/S08` is the only continuous-tone scan in the corpus.** Every other copy is an MRC composite whose
text layer is a **1-bit JBIG2 mask**. That matters because binarisation destroys the grey levels the
recognizer's pretrained filters expect, and it destroys them *upstream* of anything we can do later
(§3.1). `NT/S08` has no such loss, which makes it the natural base exemplar for the New Testament.

**Consequence for base-exemplar selection**: each volume has **two** usable copies, not three.

| volume | usable copies | base candidate | second copy (surrogate) |
|---|---|---|---|
| NT 1582 | S08, S09 | **S08** — continuous tone | S09 |
| OT1 1609 | S09 (650 ppi), S03a (500 ppi) | **S09** | S03a |
| OT2 1610 | S09 (650 ppi), S03b (400 ppi) | **S09** | S03b |

**These are candidates, not the decision.** §2 states what must be established before a base exemplar is
declared.

### 1.3 Reference texts are finding aids, not authorities

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

The constitution cannot be exercised until each volume's base exemplar is identified bibliographically. A
concordance is built first, with these fields per copy:

**edition-issue · STC/ESTC number · volume · repository and shelfmark · scan provenance · completeness and
imperfections · made-up leaves · raster properties (§1.2).**

The raster column is measured and filled. **The bibliographic columns are currently unknown and are not
filled from memory or inference** — a misattributed shelfmark would poison the base-exemplar choice and
every downstream claim. Candidate STC numbers circulating in earlier notes are treated as **leads to verify
against ESTC**, not as facts.

**Gate 0a**: every field resolved for the nine copies, **no UNKNOWN remaining**.

Base exemplars are then declared per volume on completeness, impression quality and absence of
sophistication, **with the losing candidate and the reason recorded**.

---

## 3. STAGES 0–1 — RASTERS AND GEOMETRY

### 3.1 Acquire

**Extract, never render.** `pdfimages -png` writes the decoded native stream; rendering composites the
crisp text layer with a near-empty colour layer and returns an antialiased grey image — noise created by the
export. Composite only when a page genuinely needs it (plates, colour), at exactly native ppi.

**Grayscale is primary throughout.** For the MRC files this means the **JPX layer**, not the JBIG2 mask.

> **Why the mask is not the default, despite being crisper.** A 1-bit image upcast to 8-bit is two-valued
> — `{0, 255}` — not grayscale. The pretrained recognizer's first convolutional filters were fitted to
> antialiased stroke edges carrying 20–40 grey levels across a 2–3 px transition; binarised, that gradient
> is a step, and the mismatch concentrates in **exactly the 2–4 px features the edition depends on: the ſ
> nub and the macron.** Converting to uint8 before geometric operations fixes *resampling aliasing* only.
> It does not restore grey levels, which were destroyed upstream at binarisation.

Rules:
1. **No lossy or resampling step anywhere in the working chain.** PNG or TIFF only. No page-level resize;
   scaling happens once, inside the recognizer, at the declared line height.
2. **No autocontrast, denoise, sharpen or binarisation of our own** in the default path. Any tonal
   operation is per copy, measured, and recorded.
3. Where only a 1-bit layer exists, **reconstruct pseudo-grayscale with a ~0.8 px Gaussian at native
   resolution before any downsampling** — applied identically at train and inference, so it carries no risk
   of train/test skew.
4. **A raster manifest per copy** — path, native dimensions, bit depth, provenance, checksum — so a silent
   substitution is impossible and every experiment can name what it consumed.

**Two tests, measuring different things:**

- **JBIG2 substitution** (Gate 0b). Lossy symbol matching merges visually similar glyphs, and **`ſ`/`f` is
  the canonical case.** Extract the same 20 pages as mask and as composite; compare glyph-for-glyph on every
  `ſ`/`f` and `c`/`e`; report substitution rate **with per-class instance counts.** Threshold ≤0.1%, upper
  confidence bound.
- **Binarisation transfer gap** (Gate 0c). Zero-shot CER, grayscale versus 1-bit, per copy. **This gap
  exists even at a zero substitution rate**, which is why the two tests are separate.

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
   at 650 ppi and 2–4 px after rescaling to a 120 px line height — **and the remedies are resolution
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
type**; they differ in resolution, MRC structure, colour and skew — image statistics, not letterforms.
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
  copies at 400/500/650 ppi.

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
| **0b** | JBIG2 substitution | `ſ`/`f`, `c`/`e` substitution rate | **≤0.1%**, CI upper bound | mask-vs-composite pairs | 20 pages, per-class counts |
| **0c** | binarisation gap | zero-shot CER, grayscale vs 1-bit | **reported per copy**; 1-bit copies scoped separately | DEV-GOLD | 200 lines |
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
| **0** | Source concordance; **declare the three base exemplars** | the decision the constitution needs | — |
| **1** | Drop-cap board fix + page axis | 18 cells | — |
| **2** | Residue detector → ranked leaf defect queue | a working defect queue | — |
| **3** | **Archaic typeset census** (§4.1) | the frozen inventory the codec is built from | 0 |
| **4** | Raster policy: grayscale primary, JBIG2 test, binarisation-gap test | raster policy settled | 0 |
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

**Blocking**: the source concordance (§2) — bibliographic fields unresolved for all nine copies · one
citation carried unverified from earlier work and load-bearing for §3.2's gate — **resolve or delete** ·
the archaic typeset census (§4.1), which also closes the `ꝛ` / brevigraph / blackletter questions.

**Open, scheduled**: JBIG2 substitution and the separate binarisation transfer gap · pair-CNN separability
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

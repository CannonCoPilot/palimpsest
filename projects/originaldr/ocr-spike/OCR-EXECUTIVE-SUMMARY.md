# OriginalDR — Executive Summary

**The objective**: a faithful documentary transcript of the first-edition Douay-Rheims Bible — the **1582
Rheims New Testament**, the **1609 Douai Old Testament volume 1**, and the **1610 Douai Old Testament
volume 2** — in archaic typeset and archaic spelling, recovered from photographic surrogates.

Companion documents: `OCR-OVERVIEW.md` (architecture) · `OCR-WALKTHROUGH.md` (how it runs) ·
`OCR-MASTERPLAN.md` (the plan).

---

## 1. What this is, and what it is not

**It is a documentary edition** — we read three physical books and reproduce what they print. **It is not a
critical edition**: there is no authorial revision to reconcile, no lost archetype to reconstruct, no
construction of a text from witnesses of competing authority. That distinction removes machinery that would
otherwise be mandatory — sigla, historical collation, rejected-reading registers, authority chains — none of
which serves a transcript of a single printing.

The consequence that matters most: **disagreement between two photographs of the same setting of type is a
scan-quality fact, not a textual one.** It needs no apparatus and no voting.

## 2. The corpus: three volumes, three copies each — and two admitted for named leaves only

Eleven scan files are held. **They are not eleven witnesses** — measurement and bibliographic verification
resolve them into **twelve registered records**, because one file (`M`) holds two books of two different
editions. Of the twelve: **eight** witness their own volume's setting, **two** are admitted from a
different edition as support, **one** is admitted for frontmatter alone, and **one** is a re-wrapping of
another and no witness at all.

> **Two numbers in that sentence have been corrected, and both were undercounts.** It read *"resolve them
> into ten … seven witnessing their own volume's setting"*, which lost `M`'s Old Testament half (eleven
> files carry **twelve** records — §1.1 derives the counts from the registry for exactly this reason) and
> counted `NT-1582-M` as frontmatter-only when it witnesses the 1582 setting the transcript is taken from.

**One of the eleven was very nearly not counted.** A file set aside in an earlier draft as "a 1610
whole-Bible facsimile, excluded outright" is nothing of the kind: it is a 2007 reprint **of photographs of
original copies**, whose Old Testament is a **1635 Rouen** printing and whose New Testament is a **1582
Rheims Fogny** — and whose prelims carry the **only genuine 1582 Censure and Preface p.1 in the corpus**,
two leaves the plan had recorded as surviving nowhere. Its two halves are admitted on different terms:
**`OT-1635-M` for frontmatter and endmatter only**, because a 1635 reprint is not a witness to the 1609–10
printing at any resolution, and **`NT-1582-M` as a low-resolution witness to the setting the base exemplar
itself attests** — bitonal ~380 ppi, so it may attest and collate verses but may never decide a glyph.
Both halves were filed under the frontmatter role until 2026-08-08; **that single term was carrying two
unrelated limits**, one bibliographic and one photographic, and the New Testament was the loser — see the
count of witnesses to the 1582 setting in §2. **The lesson is procedural: an exclusion is a claim, and it
inherits the evidential standard of any other claim.** This one rested on a one-line description that was
wrong about the file's
date, its printer and its nature, and because it was never re-tested it produced a false "nothing survives"
verdict at the most consequential point in the New Testament.

**Three measured facts shaped the corpus:**

**Establish which file is primary, then measure that one.** Internet Archive records the derivation chain
for every file it holds, and reading it splits the corpus in two: for the six institutional captures the
JP2s are the originals, while for the five `F`, `X` and `M` files a user uploaded a **PDF** and IA rendered
the JP2s *from it*. Measured at each item's primary artefact, **ten of the eleven are continuous tone**
(`M` alone is bitonal at source, and no original exists to acquire) — the MRC
composition and 1-bit JBIG2 layers the plan once designed around live only in IA's PDF derivation of the
institutional captures, a problem we would have *created*, not inherited. The recovery machinery built for
it is withdrawn. **Format does not establish primacy; the derivation chain does**, and reading it also
corrected a second error in the opposite direction — the `F` files are 800 × 1124 in all three volumes, and
the larger rasters they appear to offer are 300-dpi renders of that.

**One file is empty magnification.** `NT-1582-X` is an exact 2× of the NT base copy, correlating at 1.000;
its energy above the base's Nyquist is *lower* than a plain Lanczos upscale, while the base's own top band
is 30–100× richer. It is excluded as a witness: four times the pixels, none of the information. The
mechanism is now known — its uploaded PDF holds the base copy's capture **at that capture's own raster**,
and IA's renderer doubled it. It is the Boston Public Library scan at one remove.

**Resolution is calibrated, not assumed.** The Boston OT scan photographs a ruler; imperial and metric
graduations agree to 2.7%, fixing those captures at **~545 ppi** — not the 650 previously assumed — and
implying a quarto leaf, which is correct for the edition. No ppi is claimed for the NT, which has no
calibration leaf.

**Provenance is a property of the leaf, not the file.** Most NT files are made up: the base copy **lacks**
its Censure and Preface leaves, one copy supplies them **from a 1633 edition** (proven by foxing in blank
margins, 0.77 against a 0.045 control), and the re-wrapped file supplies them from a fourth source. **That
fourth source is now identified — it is the 1582 setting, witnessed by `M`** (block-registered correlation
+0.424 / +0.398 on the matching pair against 0.000–0.036 on every cross-pairing, and line-for-line visual
agreement including an S. Augustine quotation the 1633 setting lacks).

> **An earlier statement is withdrawn.** This section previously concluded that **"no genuine 1582 Censure
> leaf exists anywhere in the corpus."** That was true of the four NT files then under consideration and
> false of the corpus, because the fifth had been excluded on a mistaken description and never examined.
> **Both leaves survive in the 1582 setting**, and may be transcribed as 1582 readings — from `M`, with its
> bitonal ~380 ppi raster recorded as the limiting factor.

The 1633 Rouen copy remains admitted for the NT as witness support, for the leaves where the base has no
reading at all.

**A second file proved to be that same 1633 edition, and it had been counted as a 1582 witness for four
months.** `F`'s New Testament carries a genuine 1582 Fogny title page over a **1633 Rouen body**: it tracks
the 1633 copy page-for-page and line-for-line at a constant +4 leaf offset, shares its misprint `Iralie` for
`Italie`, and departs from the 1582 base copy everywhere — Apocalypse ch. XXII at printed 692 against the
base's 743, and running-head apparatus the base has and it does not. It is an *independent* 1633 copy rather
than a re-render of the other, on blank-margin correlation of 0.099 / 0.021 / −0.022 where a proven shared
leaf reads +0.769. **`F`'s two Old Testament volumes are unaffected and genuinely 1609 and 1610**, checked
at three separated points each. It is re-sigla'd `NT-1633-F` and reclassified as support.

> **The consequence is the most significant open exposure in the corpus: the New Testament has exactly one
> witness that can carry a GLYPH-level call.** `X` is the base upscaled and `F` and `R` are 1633, so at that
> grain the base copy's readings are uncorroborated and no amount of re-reading manufactures a second
> opinion.
>
> ⚠️ **TWICE CORRECTED, 2026-08-17, AND BOTH CORRECTIONS MATTER.**
>
> **First, `M` is not "bitonal and prelims-only" — that is the pre-R9.0 role.** Only `M`'s 1635 Rouen OLD
> TESTAMENT half is frontmatter-only. Its NEW TESTAMENT half is **the same 1582 setting as the base
> exemplar** and carries the `lowres` role (R9.0; the Overview's witness table was corrected in R9.5a, and
> this sentence was missed). ⚠️ **It was missed in three separate places** — here, `OCR-OVERVIEW.md`'s
> consequence box, and `OCR-WALKTHROUGH.md`'s raster section — all corrected 2026-08-17. R9.5a fixed the
> *table* and left the *prose*, which is why the wrong role kept being quoted from documents whose own
> tables contradicted it.
>
> **Second, and the reason the first mattered: a resolution bar is a bar on ONE GRAIN of question, never on
> the witness.** `M` cannot adjudicate long-ſ against `f` — the nub is under 1.6 px at 168 ppi, and that bar
> stands. It can do everything that does not turn on resolving a glyph: **page layout and geometry**
> (region boundaries, archetype classification, reading order); **adjudicating damage, show-through and an
> inked-over sort in `B`**, because a second physical copy settles whether a mark is in the TYPE or in that
> COPY, and that is answered at blot grain; **confirming a training crop addresses the locus it claims**,
> which is addressing rather than recognition; and collation, page order and completeness.
>
> So the honest figure is a **pair, not a number**: the New Testament stands at **depth 1 at glyph grain and
> depth 2 at structural grain**. `witnesses.depth("NT", 1582)` returns `(1, 2)` and exists so the question
> cannot be asked without saying at which grain. What the NT lacks is specifically a *surrogate* — a second
> capture that can resolve a glyph — not a second witness.
>
> 🔴 **AND THE REMEDY IS NOT ACQUISITION.** This paragraph used to name one: a Princeton Theological Seminary
> 1582 copy, to be setting-verified before admission. **That lever is closed** (Sir, 2026-08-17) — there will
> be no better scans and no further copy. The reasoning is kept because it is sound and because a closed
> option that is deleted gets re-proposed; but it is closed. **The depth we have is the depth we design
> for**, and the consequence is a design constraint rather than a procurement item: NT work must be
> structured so that `M` carries every check that does not require a glyph, and so that a claim which *does*
> require one is recorded as resting on a single witness rather than silently presented as corroborated.
>
> The failure mode is worth stating because it is cheap to repeat. `F`'s independence was tested **against
> the base copy** and returned noise — which licensed only "`F` is not `B`", and was read as "`F` is an
> independent **1582** copy". The 1633 copy was never contrasted with `F`, because it had already been filed
> as "the other edition". **A test distinguishes exactly the hypotheses it contrasts, and filing a witness
> under a label removes it from the candidate set.** Two executable guards now enforce this: collation
> across settings is refused outright, and the corpus table in the plan is parsed and diffed against the
> registry, so a document claim and a code claim cannot drift apart silently. Both carry negative tests —
> a guard that has never rejected anything is not known to work.

**Every witness has now been audited for its edition, and no second mis-filing exists.** The `F` correction
raised the question the plan could not answer that day: how many of the others were wrong? The concordance
had verified title pages — and a title page is precisely what `F` borrowed — so eleven records stood
**unchecked rather than sound**. Each has since been collated against a partner in its claimed setting on
the printed page number, running head, sidehead, text and line breaks together. **Eleven of twelve agree at
three or more separated printed pages**, marginal notes breaking at the same words. The audit also
demonstrates that it *can* fail: at printed page 147 under the identical running head *ACCORDING TO S.
LVKE*, the 1582 copy prints Luke 4:31 while the two 1633 copies print Luke 7:44 — the 1582/1633 boundary
visible in a single crop, which is what makes the eleven passes worth stating.

> **The twelfth is named, not counted.** `OT-1635-M` is the only record of the 1635 Rouen setting in the
> corpus, so it has no partner and cannot be collated. Its date rests on internal evidence — its own
> colophon and the ten-year privilege of 1634 that it prints, which must precede the printing it licenses.
> That is respectable evidence and it is not this test, and the plan says so rather than rounding it up. The
> guard holds it on an explicit exemption that **fails if a same-setting partner ever arrives**, and fails
> for any registered witness with no readings at all — absence of evidence presents as absence, which is the
> same rule the corpus adopted after a classifier once reported an unmeasurable quantity as zero.

**Every volume has a base exemplar; the two OT tomes also have a same-setting surrogate** for resolving
illegibility. The NT has none — which is why it alone needs the witness-support and frontmatter roles.
It does, however, have a **second copy of its own setting at low resolution** (`NT-1582-M`, ~380 ppi
bitonal), which had been withheld from it by a role name until 2026-08-08. That improves collation,
completeness and attestation for the New Testament and changes nothing about illegibility: a surrogate is
defined by being able to answer a glyph, and `M` cannot.

## 3. How it works

**The correction loop is both the product and the ground truth.** A page goes through the recognizer, a
vision model proposes corrections on **line crops**, the operator accepts or retypes by keystroke, and the
signed-off page becomes — from the same keystrokes — the transcript, the evaluation text, the training
ground truth, the layout ground truth, and glyph instances. **There is no separate annotation project**,
which is the only reason the annotation is affordable.

**Residue is evidence.** The fraction of a chapter's reference text matched by *no* recognised line
localises a clipped or missed region. Ranked across leaves, that is a defect queue — needing no ground truth
and no new model, so it is the first real improvement to ship.

**Letterpress repeats the same physical sort.** Rather than classify `ſ` instance by instance, cluster the
candidate crops per fount per volume, key ~50 cluster exemplars, and propagate. This is the strongest lever
available, and it is unavailable to per-instance methods.

**And the recognizer may say it cannot tell.** Contested pairs emit `A` / `B` / *indeterminate*, abstaining
into `<unclear>`. On clean type the pair classifiers reach 0.97–0.99; on the difficult tail — touching,
over-inked, show-through, worn — 0.7–0.85, and that tail is 10–20% of instances.

> **An 8% abstention rate on `ſ`/`f` is an honest edition; a 0% one is a fabricated one.**

## 4. Training is organised by volume

The three volumes are **three different printings** — Rheims 1582 under one house, Douai 1609 and 1610 under
another, 27 years apart, different founts and compositor conventions. So:

```
CATMuS-Print [Large]  →  VOLUME  →  FOUNT
```

**VOLUME is the letterform boundary.** **FOUNT** — roman text, italic annotation, display — is the
letterform boundary *within* a volume, and the same axis the rendition layer already treats as semantic.

**COPY is not a model level.** Three copies of a volume photograph the same setting of the same type; they
differ in resolution, structure and skew — image statistics, not letterforms. Fitting a model per photograph
of one book would be a category error. *(That governs **scope** only. Skew is still measured: the geometry
stage emits the leaf's slant as a gated output, because a row holding two interleaved printed lines cannot
be split until the slope is removed, and the slope cannot be fitted from that row.)* Instead **copies are pooled within a volume as training
augmentation**, which is a genuine advantage of this corpus: *identical letterforms under different imaging
conditions* is exactly the invariance a recognizer should learn, and it is normally expensive to obtain.

Held-out splits are stratified **by copy and by gathering** — never by page, since adjacent leaves of one
gathering share paper, bleed-through, skew and the same forme.

> **Note on earlier naming.** Legacy identifiers (`archive-*`, `jp2-*`, `pdf-*`) describe *how a file was
> acquired*, not which book it is — and two of them each contain **all three volumes**. Training "per
> source" would therefore have pooled 1582 Rheims types with 1609/1610 Douai types into one model. The
> addressing unit is now `VOLUME/COPY`.

## 5. The archaic typeset census

**Before the codec is fixed, the inventory is established empirically** — surveyed from the actual type in
each volume, given a representation, then frozen. A class the model never sees cannot be output; a class
asserted but absent invites the model to hallucinate it out of damaged type.

Every requested sort is resolved **ATTESTED or NOT FOUND, per volume**, with an image exemplar and a
frequency count: the `ct`, `æ`, `ﬁ`, `ﬂ`, `ﬀ`, `ſt`, `ſl`, `ſh`, `ſſ` ligatures, long-ſ, and the `ã õ ũ`
suppressed-nasal vowels — plus the **note-reference marks** (`*`, `†`, `‡`, `¶`) without which the
annotation cannot be keyed to the text, and in this edition **the annotation is roughly half the book**.

Three items need the survey to settle them rather than an assumption:

- **"tall-s" versus "long-s"** — early-modern founts normally carry two s-sorts, round `s` and long `ſ`. If
  the census finds only two, these are one sort under two names and the rows merge. The same question
  governs the `ſt`, `ſl` and `ſſ` entries listed twice.
- **"long-f"** — there is no long-f sort as such, and two different things produce that impression. One is
  an `f` inside a ligature. The other is real and important: **some founts cut the long ſ with a full
  crossbar rather than a left-side nub**, making it near-indistinguishable from `f`. **If that allograph is
  attested it needs its own class**, because it defeats nub-based discrimination entirely — which would
  otherwise be a silent, systematic error across a whole volume.
- **`ꝛ` and the Latin brevigraphs `ꝑ ꝓ ꝗ`** — entangled with whether these founts set any blackletter at
  all. One inspection closes all three.

## 6. On connected components — a correction

An earlier draft asserted that connected-component analysis fails outright, because at 650 ppi a well-inked
line is largely one connected component. **That over-stated the case, and the plan now reflects the
correction.**

It remains true that ink load and paper absorbency drive whether adjacent sorts touch, so **CC count alone
decides nothing.** But **the pairs that ligature are a small closed set, and a ligature sort is a distinct
piece of type with its own form** — not two letters that happen to collide. That yields three real
advantages, and the method now uses them:

1. **A tiny hypothesis space** — never "which of 400 classes," only "is this the `ﬁ` sort, or `f` followed
   by `i`."
2. **False-positive control by construction** — a ligature can only be proposed where its constituent
   letters are expected.
3. **Revisability** — because the set is closed, every decision for a class can be re-swept corpus-wide when
   that class's classifier improves. Ligature decisions become **revisable data, not irreversible
   transcription events.**

Connected components are therefore used as a **candidate detector within the closed set**, with a per-pair
CNN deciding on the crop and abstaining when it cannot.

## 7. What ships, and in what order

**Ordered by dependency and complexity, not by calendar.** A schedule in weeks invites the two errors this
project is built to avoid — treating a spent budget as permission to stop, and reading a cheap step as the
better one. What governs order is what each step *needs* and how hard it is to get *right*.

| what | needs | complexity |
|---|---|---|
| source concordance + base-exemplar declaration; drop-cap board fix (**18 cells**); page axis | — | **low** — bounded, verifiable against the board |
| **residue detector** — ranked defect queue | — *(no ground truth, no new model)* | **low** — reuses the incumbent as a detector rather than a generator |
| **archaic typeset census** — the frozen inventory the codec is built from | the corpus admitted | **medium** — the difficulty is adjudicating ambiguous sorts, not enumerating them |
| **correction loop on Micheas**, producing transcript and ground truth together | concordance · census · residue queue | **medium** — mechanically simple, and the single largest call on skilled attention |
| frozen evaluation sets; **G1 geometry**; **G1 recognition**; glyph census; the edition | the above, in that order | **high** — the two models are the genuinely hard work, and each gates a published gate |

**The pilot book is Micheas (Micah) in OT2** — 7 chapters across about 7 leaves, present in all three OT2
copies. Chosen because it has **no archaic reference witness**, so it exercises the part of the corpus that
is structurally invisible to every reference-based mechanism and would otherwise be discovered last; because
at roughly one chapter-open per leaf it is an unusually dense test of the drop-cap and chapter-heading
machinery; and because it is small enough to finish early. **Joel** (3 chapters, ~5 leaves) and **Amos**
(9 chapters, ~11 leaves) are the smaller and larger alternatives in the same condition.

**The honest total cost, and it is a procurement figure rather than a schedule**: ~3,000–4,500 pages at
6–15 min/page corrected = **400–1,000 keyer-hours**. This is quoted in hours because it is **labour to be
bought** — the same unit escalation uses when it names *paid annotation* as a resource class — and not
because any step of this project is sized in time. That price holds under any architecture. The design does
not remove the keying; it makes the keying produce the deliverable directly rather than producing the
instrument that produces it.

## 8. How the plan keeps itself honest

- **Three evaluation tiers with a published query ledger** — freezing a set stops contamination but not
  repeated querying; at realistic set sizes ~57 adoption queries yield ~0.18% apparent improvement from
  noise alone.
- **Rare classes get a census, not a rate** — every instance on a declared page set, so the denominator is
  page-defined rather than detector-defined. **Below n=30 a class is UNMEASURABLE: open and blocking.**
- **Every gate carries metric, threshold, named set, n, and a pre-registered effect size**, as a
  document-level invariant.
- **Two terminals, never one** — *converged-at-target* closes; *stalled-below-target* is **open, blocking,
  and raises an alert that the approach needs redesign.** No below-threshold result is ever given a terminal
  accepted state.
- **Escalation must name a different resource class than the one that failed** — paid hours, a better scan,
  an outside ruling, or reduced **coverage** — **never reduced fidelity.**

## 8a. Where the two models actually stand (STATUS, added 2026-08-25)

⚠️ **This section exists because the status of both models was absent from this document, from the
Overview and from the Walkthrough**, while all three describe the recogniser's architecture at
length. A reader of the summaries could not have learned either of the two facts below, and both are
the kind that change what someone would work on next.

**The geometric boxing model — BLOCKED AT A PRIMITIVE.** Region typing over the head band is built
and scored against a 121-entry gold (RunningHead / MarginNote / MainText / ChapterHead), with an
address that survives a splitter change and an accounting bar that a candidate cannot game by
shedding entries. It is blocked below the model: `region_segments` cuts a row wherever a gap exceeds
the line pitch, and in **justified** setting the word space is stretched to fill the measure — so of
301 genuine body rows, **102 (34%) have no continuous run reaching the measure**. **Four** region-span
rules have been built and refuted against pre-registered bars, each buying ~1 MarginNote for 11–12
MainText. 🚨 **AND ON 2026-08-25 THE APPROACH-LEVEL ALERT FIRED, BY SIR'S RULING.** R2.2o.1 labelled
every intra-row gap from the gold and found the two populations **OVERLAP**: a true region gap of
**0.875 pitches** where the marginal column abuts the measure, against a true word space reaching
**1.525** on the same page. **No constant exists to be found**, so a fifth span rule was not built.
⇒ `region_head` / `region_segments` are **re-scoped from the region model to the initialisation and
plausibility clamp** of §3.2 item 5 — characterised and willing to abstain, never maximised — and the
four refuted rules plus the overlap measurement become **complete characterisation work** rather than a
stalled repair. The region-typing work moves to **R14, the adaptive visual agent**. ⚠️ The MN gap
stays **OPEN**: this is a redesign of the method, never an accepted gap.

⚠️ §3.2's own thesis —
that the recogniser's 49-point content/surface spread on `genesis-24` is a *layout-separation* failure,
not a reading failure — makes this the binding constraint on the **recognition** score as well.

**The character recognition model — BUILT, AND NOT IN THE PATH.** The ſ-faithful Rung-2 fine-tune
exists (Kraken, val 0.9396). **R13, verified on disk: nothing loads it.** `grep` over `gen1_*.py`,
`s_arbiter.py` and `chapter_campaign.py` returns nothing for `reichenau_dr` or `dr_v3_armA`; the
attesting arm is the base scan OCR. ⚠️ **That wiring it in would improve the board is a hypothesis,
not a finding** — the 1,142 `CONTENT OK, ſ-SURFACE OPEN` cells are *plausibly* reachable, and
plausibly is not measurably. R13.1 is the wiring, R13.2 is the measurement, and the cell count is not
claimable before R13.2 runs.

**Read together: the recognition problem looks like the hard one and is the better-served one.** The
model that exists is unwired; the model that is wired is bounded by a layout rule that mis-cuts a
third of the body.

### 8b. What the geometry stage is actually supposed to be (Masterplan §3.0, GOVERNING, 2026-08-25)

🔴 **STATED HERE BECAUSE ITS ABSENCE FROM THE SUMMARIES IS WHAT LET THE WORK DRIFT.** The aim was
present only in fragments — "archetype first" in one section, "reading order" inside a list in three
others, "shapes from ink" as a section title. **A project whose aim lives in fragments optimises the
nearest fragment.** This one did: four hand-built geometric span rules and five pre-registered bars
against a 19-entry gold on one witness, while four of the eight steps below had no code at all.

**The aim:** an **adaptive visual agent that reproduces what a literate human does when handed a page
of this book** — look at the leaf, recognise what *kind* of page it is, see by **visual cue** where each
class of text sits, bound those regions, understand how they **relate**, and read each region **as its
own kind of thing**, with its own rules, context and gates.

| | step | status |
|---|---|---|
| S1 | see the page | ✅ real |
| S2 | classify the archetype | 📋 designed (8 archetypes, REQUIRES/FORBIDS); **nothing built** |
| S3 | see the region classes by visual cue | ⚠️ geometric only, one witness, head band |
| S4 | bound them — box · label · slant · **confidence**, abstention permitted | ❌ **no layout score of any kind has ever been computed on this corpus** |
| S5 | **relate** them — reading order and note-to-verse attachment | ❌ named in three documents, owned by none |
| S6 | recognise each region **conditioned by its class** | ⚠️ recogniser validates at 0.9396, **not wired** (R13) |
| S7 | run that class's rules, checks and gates | ✅ exists, ⚠️ fed by a four-role geometric typer |
| S8 | **re-examine on failure** | ❌ residue is spent as training signal only |

⚠️ **"Adaptive" means per-page, from the page.** A constant fitted across a sample may initialise or
clamp; it may never decide. **The whole programme is R14**, and its cheapest step (R14.0) is to run and
score `surya_layout_probe.py` — a learned layout model **already in the repo** that appeared in none of
these five documents until today.

## 9. Open

**Blocking**: **collation and leaf inventory per copy**, and the **cross-source leaf map**. §1.4 is why
neither can be skipped — three of four NT files are made up, the defect was invisible until leaves were
read, and leaf indices do not correspond between copies of the same volume (the NT files differ by up to 47
leaves before a word is compared). Until the map exists, "the same page in another witness" is not a
well-formed request.

**Also blocking, and now the corpus's largest exposure: the New Testament has one witness that can carry a
GLYPH-level call** (§2) — depth `(1, 2)`, one at glyph grain and two at structural grain, `M` being the
second. 🔴 **The remedy is NOT acquisition (closed 2026-08-17).** This entry named a candidate 1582 copy with
continuous-tone originals; there will be no better scans and no further copy. **The depth we have is the
depth we design for.** What survives is the admission test itself, which remains a formal gate for anything
ever admitted: printed page number, running head, **signature and catchword** agreeing at three or more
separated points against a known-good same-setting partner (**Gate 0e**). That is the test that was never
run for four months and would have cost minutes — it is retained not as a procurement step but because it is
the standing method by which any setting claim is proved.

> ⚠️ **The held witnesses do not yet meet the standard this paragraph sets for a new one (2026-08-10).**
> The head criteria were verified at three or more separated points, but the **signature and catchword were
> verified at exactly one matched page per setting** (R8.4a); R8.4b, the remainder, is open. So the bar
> quoted above is the bar for admission and is *not* the bar the existing eleven have cleared. The Master
> Plan §2 status line said "the full §0.3 criterion" until this review and has been corrected. Reported
> because a gate whose own corpus does not meet it is a gate under pressure to be quietly relaxed.
>
> ⚠️ **A second gate is weaker than the documents implied: Gate 0d — derivative contamination — had never
> been implemented at all**, though three documents described it as a guard awaiting a negative test. It is
> now roadmap R5.1 + R5.2a–c. This matters here because 0d is the gate that would have caught the very
> `F`/`X` raster problem the paragraph below reports as 48 of 51 ground-truth files.

**Also open, and it is a defect in the ground truth rather than in the corpus: 48 of 51 ground-truth files
were read from a raster that cannot support the calls they carry** — 39 from `F` (~168 ppi, where the long-ſ
nub spans under 1.6 px), 6 from `X` (an excluded 2× upscale), 3 from `M`'s render. **Zero from `B` or `P`**,
the base exemplar and its surrogate. Stated precisely: those readings are **unverified, not wrong**, and
nothing is withdrawn on suspicion — two spot-checks moved the state in *both* directions. The remedy needs no
acquisition, since every locus but two NT leaves exists on an admissible witness.

The *mechanism* is now closed. A hand-written routing table in `jp2_page.py` sat beside the registry's guard
and never called it, so two routes to the pixels existed and only one refused an inadmissible image — the
table was verified as the cause in an earlier commit and was **still routing** until 2026-08-07. There is now
one route: an identifier resolves to a witness, and the witness resolves its own raster or refuses. **A
verified defect can stay live indefinitely; what retires it is a test, not a finding.**

Also blocking, but running in parallel: **STC/ESTC for every copy.** Direct verification remains
**externally blocked** — the ESTC index returns `no such index` for every query, `estc.bl.uk` redirects to
CERL, and the four fallback catalogues probed are 404, JavaScript-only, or 403. A scheduled probe
distinguishes an outage from an absent record. **The route around it was held locally all along**: Internet
Archive exposes each holding library's own MARC record, and the Boston Public Library's supplies
`ESTC S102491; STC (2nd ed.) 2884` for the New Testament and `STC (2nd ed.) 2207; ESTC S101944` for the Old
Testament, with LCCN and signature collation. **This settles the one-digit disagreement in favour of
S102491** — the sources reading S102419 are dealer and auction listings, which the rule bars from promoting
anything. That rule is unchanged and still binding: **one institutional authority is not two**, so no number
is written into §1.3 until a second, independent institution's record agrees.

**Two items on this list are now closed rather than pending.** The `F` repository question is answered and
was the wrong question: those volumes have no shelfmark because they are **not a library's copy** —
privately held is a determinate answer. And the source of the excluded file's two frontmatter leaves is
**identified** (§2). What remains genuinely open is narrower: the physical copies behind `F` and `M` before
their present owners, which no catalogue can supply and which blocks no transcription.

One citation carried from earlier work
is unverified and load-bearing for a geometry gate: resolve or delete — **and since that gate is §3.2's, this
item blocks the region model rather than sitting beside it, which is not how its placement here reads.** And
the typeset census, which also closes the `ꝛ` / brevigraph / blackletter questions.

**Unratified**: the archaic-preeminent board gate, pending blind adjudication of n ≥ 100 newly-passing cells
against the scans.

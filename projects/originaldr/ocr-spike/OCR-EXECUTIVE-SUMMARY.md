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
resolve them into **ten**, across three volumes: **seven** witnessing their own volume's setting, **two**
admitted from a different edition as support, one admitted for frontmatter alone, and one file that is a
re-wrapping of another and no witness at all.

**One of the eleven was very nearly not counted.** A file set aside in an earlier draft as "a 1610
whole-Bible facsimile, excluded outright" is nothing of the kind: it is a 2007 reprint **of photographs of
original copies**, whose Old Testament is a **1635 Rouen** printing and whose New Testament is a **1582
Rheims Fogny** — and whose prelims carry the **only genuine 1582 Censure and Preface p.1 in the corpus**,
two leaves the plan had recorded as surviving nowhere. It is admitted as `NT-1582-M`, for frontmatter and
endmatter only. **The lesson is procedural: an exclusion is a claim, and it inherits the evidential
standard of any other claim.** This one rested on a one-line description that was wrong about the file's
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
> witness to its own setting.** `X` is the base upscaled, `F` and `R` are 1633, `M` is bitonal and
> prelims-only. Nothing about the base copy's readings changes, but nothing corroborates them either, and no
> amount of re-reading manufactures a second witness. **The remedy is acquisition**, and a candidate is
> already identified: a Princeton Theological Seminary 1582 copy with continuous-tone originals, to be
> setting-verified *before* admission by the same printed-page-and-running-head method that caught this.
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
of one book would be a category error. Instead **copies are pooled within a volume as training
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

## 7. What ships, and when

| when | what |
|---|---|
| **week 1** | source concordance and base-exemplar declaration; drop-cap board fix (**18 cells**); page axis |
| **week 2** | **residue detector** — ranked defect queue, no ground truth, no new model |
| **week 2–3** | **archaic typeset census** — the frozen inventory the codec is built from |
| **week 3+** | **correction loop on Micheas**, producing transcript and ground truth together |
| later | frozen evaluation sets, G1 geometry and recognition, glyph census, the edition |

**The pilot book is Micheas (Micah) in OT2** — 7 chapters across about 7 leaves, present in all three OT2
copies. Chosen because it has **no archaic reference witness**, so it exercises the part of the corpus that
is structurally invisible to every reference-based mechanism and would otherwise be discovered last; because
at roughly one chapter-open per leaf it is an unusually dense test of the drop-cap and chapter-heading
machinery; and because it is small enough to finish early. **Joel** (3 chapters, ~5 leaves) and **Amos**
(9 chapters, ~11 leaves) are the smaller and larger alternatives in the same condition.

**The honest total cost**: ~3,000–4,500 pages at 6–15 min/page corrected = **400–1,000 hours**. That is the
price of this product under any architecture. The design does not remove those hours; it makes them produce
the deliverable directly rather than producing the instrument that produces it.

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

## 9. Open

**Blocking**: **collation and leaf inventory per copy**, and the **cross-source leaf map**. §1.4 is why
neither can be skipped — three of four NT files are made up, the defect was invisible until leaves were
read, and leaf indices do not correspond between copies of the same volume (the NT files differ by up to 47
leaves before a word is compared). Until the map exists, "the same page in another witness" is not a
well-formed request.

**Also blocking, and now the corpus's largest exposure: the New Testament has one witness to its own
setting** (§2). The remedy is acquisition, not further measurement of what is held. A candidate 1582 copy
with continuous-tone originals is identified and **must be setting-verified before admission** — printed page
number, running head, **signature and catchword** agreeing at three or more separated points against a
known-good same-setting partner. That is the test that was never run for four months and would have cost
minutes, and it is now a formal gate (**Gate 0e**) rather than a practice.

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
is unverified and load-bearing for a geometry gate: resolve or delete. And the typeset census, which also
closes the `ꝛ` / brevigraph / blackletter questions.

**Unratified**: the archaic-preeminent board gate, pending blind adjudication of n ≥ 100 newly-passing cells
against the scans.

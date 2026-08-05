# OCR Masterplan V3 — Round 2 Adversarial Critique (record)

> **NOTE ON METHOD — round 2 ran TWICE, blind.** A JICM context refresh mid-round caused me to re-launch
> the four specialists, believing the first panel's results lost. They were not lost; both panels returned.
> **Every remit therefore has two independent critiques that never saw each other.** This is an accident,
> and it is the most valuable evidence in the round: it separates *replicated* findings from *single-critic*
> findings, and it localises genuine uncertainty at the two points where same-remit specialists disagreed.
> **§ PANEL B and § REPLICATION below carry that analysis. Read them before the panel-A tables.**

Four specialists, run in parallel against **revision 2** (what it *newly* asserts in answer to round 1).
Round-1 record: `OCR-MASTERPLAN-V3-CRITIQUE-R1.md`. Panel:

| # | specialist | remit |
|---|---|---|
| **E** | evaluation-integrity red team | gold sizing, adaptive overfitting, residual circularity, gate falsifiability |
| **P** | program lead / executability | real hours, deliverable order, gold-plating, stall risk, simpler architecture |
| **H** | CTC/HTR engineer | §5 recognition — ligature machinery, codec, oversampling, raster, metric computability |
| **S** | DH scholarly editor | copy-text constitution, glyph inventory, apparatus, the 8,383 |

Round 1 attacked the plan's *epistemics* (it could not be falsified). Round 2 attacks its *scope and its
mechanisms* — and, unlike round 1, two reviewers who share no remit arrived at the same cut.

---

## THE CONVERGENT FINDING — the plan is paying for two different products

**P (§6) and S (§A/§D) reached this independently from opposite directions, and E's sizing arithmetic
confirms it.**

Revision 2 adopted Greg/Bowers copy-text discipline in §0.1. Under that discipline **five of the six
sources may never alter an accidental** — they contribute substantive readings and physical evidence only.
Revision 2 nonetheless retains "six transcripts each driven to publication quality" from V2, and sizes
GOLD-TEXT, the model hierarchy, the six-way collation, the variant graph, witness weighting and the drift
guard accordingly.

- **P**: six-way publication quality is the largest single cost driver and *does not serve the stated
  product*. It serves a six-witness collated critical edition — a legitimate but **different** project.
- **S**: nothing in Sir's ask requires a critical edition; §9.2 imports critical-edition overhead onto what
  is a diplomatic transcription.
- **E (D3)**: GOLD-TEXT at 300–500 lines/source is ~10× short of the power its own §5.4 argument demands.
- **P (§1)**: GOLD-TEXT × 6 at diplomatic keying care is 75–150 h of the 155–275 h Stage −1 total.

These are the same fact seen four ways. **Diplomatic keying care is required for the copy-text exemplar
only** (~150–200 lines, ~8–10 h). The other five are scored *folded*, for word identity, against far fewer
lines. This resolves E's "too small" and P's "too large" simultaneously — the sets were sized for the
wrong scope.

**Deleted by the cut**: six-way MSA/variant graph, calibrated ensembles, Henikoff weighting, effective-N,
the entire drift guard (no write-back loop remains to guard), five-sixths of GOLD-TEXT.

**This is the decision revision 3 must make explicitly, at the top, in Sir's words — not absorb silently.**

---

## E — evaluation integrity

| # | defect | fix |
|---|---|---|
| **E1** | **GOLD-GLYPH is training set and eval set for the same classes.** §5.3.2–3 trains the per-pair classifiers on GOLD-GLYPH crops; §5.5 scores rare-class macro error on GOLD-GLYPH. GOLD-TEXT carries a never-train rule; GOLD-GLYPH carries none. The gate the whole inventory claim rests on is scored on its own training data. | Split at mining time into disjoint halves **by page**; never-train rule verbatim; state per-class eval n. |
| **E2** | **The ≥200-instances-per-rare-class rule is unsatisfiable, and its escape clause launders it.** §5.2 says `ﬃ ﬄ` and the marks occur "tens of times corpus-wide"; §1's qualifier "where the class exists at all" converts an unmeetable requirement into automatic satisfaction at n=30. **That is a below-threshold unit given terminal accepted state — the exact thing the project forbids.** Worse, instances are mined *by the detector under evaluation*, so misses are invisible: **rare-class recall is unmeasurable by construction.** | Exhaustive keying of a declared **page census** (every instance on N fully-keyed pages) so the denominator is page-defined, not detector-defined. Corpus n < 200 → class reported **OPEN/unmeasurable**, never passed. |
| **E3** | **GOLD-TEXT ~10× too small for its own gates.** 300–500 lines ≈ 1.5×10⁴ chars. §5.4 kills BOOK because 0.60 vs 0.50% needs ~10⁵ held-out chars — then demands for SOURCE/TOME a paired bootstrap, a pre-registered effect size, **and a second never-touched confirmation set**, with no such set budgeted and no characters to build one. Per-class Wilson on a ~400-class alphabet at n=1.5×10⁴ is vacuous below the top ~40 classes. | Size from the effect size intended to be detected. ≥2×10⁵ chars/source for TOME adoption — **or drop TOME and state SOURCE-only.** Budget CONFIRM-TEXT separately, open once. |
| **E4** | **Adaptive overfitting to the frozen set is acknowledged nowhere.** G0→Gn with δ-stopping, a five-rung escalation ladder each re-evaluated on the same eval half, a joint H×pooling sweep, oversampling tuned 10–50× — hundreds of queries against ~2–3k lines. Freezing does not protect a set from repeated querying; the reported number drifts optimistic ≈ √(log k / n). | **Three tiers with a logged, published query counter**: DEV-GOLD (unlimited) / VAL-GOLD (budgeted looks) / FINAL-GOLD (opened once, at publication, freshly keyed). Exhausting the VAL budget requires re-keying new pages before continuing. |
| **E5** | **§8.4 is not airtight — four live output→evaluation paths survive.** (i) **§6 derives alignment substitution costs from the pooled OCR confusion matrix**: `ſ`↔`f` becomes cheap *because* the model confuses them, so confused lines are accepted as GT and the confusion is trained in. R1's C7 loop, re-entering through the cost matrix. (ii) **§8.3 calibrates isotonic confidences and indel priors on pipeline-generated alignment GT**, not GOLD. (iii) **§5.5's attested-form rate** scores against a lexicon derived from ARCHAIC; a model trained on ARCHAIC-derived GT passes by construction. (iv) **§4.2.3 residue-as-signal is computed against ARCHAIC** and is therefore structurally **null on the 8,383 archaic-less loci and ARCHAIC's 30.3% gaps** — dead exactly where geometry is unlabelled. | (i) typographically-motivated or GOLD-TEXT-estimated costs, never empirical-from-self. (ii) calibrate on GOLD-TEXT. (iii) external attested corpus. (iv) add a **reference-independent** residue signal: ink-groups with no line assignment. |
| **E6** | **§8.4.4's drift guard catches one quadrant of four.** "Agreement with gold falls while consensus rises" misses the realistic drift — aggregate gold agreement *rising* on frequent classes while rare classes collapse. No threshold, no n, no power, no defined action. | Per-class gold agreement with pre-registered **non-inferiority bounds**; fires on *any* class regressing beyond bound regardless of aggregate direction. |
| **E7** | **§3's generations are not EM and not convergent.** No shared likelihood — geometry, recognition and alignment optimise different objectives. "improvement < δ" is a stopping rule, not convergence; oscillation is unforbidden. **No rule for G1 < G0**: no rollback, no keep-best, no non-inferiority requirement. "Improvement on GOLD" is undefined across ≥5 metrics — free choice of which one moved. | One **primary scalar** (CER-diplomatic on VAL-GOLD) + non-inferiority constraints on marginalia recall, boundary error, rare-class macro error. Keep-best checkpointing. A regression escalates immediately. |
| **E8** | **§10's gate table is almost entirely unfalsifiable.** Only step 7's CER-folded ≤1% is complete. Step 0 zero-tolerance on undefined n; step 1 "frozen and sha-pinned" is a process check with no quality metric on the gold itself; step 2 restates the change (a definition cannot fail); steps 3/5/8/9 name a metric with **no threshold and no n**; step 4 "audit published" is a deliverable — seed known splices and report **detection recall** or you cannot claim clean; step 6 invokes a pre-registered effect size the document never registers; δ undefined throughout; step 11 is a checklist. | Every row: metric · threshold · held-out set name · n · pre-registered effect size — **before step 1 begins**. |
| **E9** | **NOISE-FLOOR self-lowers the target.** Target = floor + δ, δ unfixed, floor measured *first*: poor transcriber agreement **drops the requirement**. Two transcribers sharing one protocol and one trainer underestimate the floor, and they are plausibly the GOLD-TEXT keyers, so GOLD's error and the floor are correlated. | Pre-register δ **before** the floor is read. ≥3 transcribers disjoint from the GOLD-TEXT keyers; report **pairwise, unreconciled** agreement, per-class for `ſ/f` and macron. |
| **E10** | **§0.2 swapped failure modes — the plan cannot start.** Step 1 gates every metric claim and step 1 is 2–3k hand-keyed lines + 200–300 polygon pages + ≥200 crops × N classes + 300 double-keyed lines, with **no transcriber count, no rate estimate, no schedule, no cost, and no written diplomatic protocol** (a prerequisite of the prerequisite). §0.2's own rule — ambiguity always licenses a better experiment — has no budget cap and no terminating state: unfalsifiable ambition restated as a virtue. | **Pilot gold** (60 lines/source, 20 pages, 100 crops) validates the protocol and **measures keying rate and variance**; full sets sized from observed variance. G1 may proceed on pilot gold with every number labelled **PROVISIONAL, non-citable**. Add a look/cost budget to §0.2's rule. |
| **E11** | **GOLD-LAYOUT is split by page → guaranteed leakage.** Adjacent leaves of one gathering share paper, bleed-through, skew and the same forme; near-duplicates land on both sides and inflate the G1-vs-G0 geometry gate. | Split by **gathering/signature**, never by page. Report which gatherings are eval-only. |
| **E12** | **Words, not mechanisms.** §0.1 declares copy-text discipline but **declares no copy-text**, operationalises no selection criteria, and defers the bibliographic identification needed to choose one to step 11 — the constitution is unimplementable in the stated order. §0.1.6 "nothing is synthesised" coexists with pseudo-archaic as a **scoring** prior: a prior deciding which lines pass GT acceptance injects synthesised spelling *through selection*. §4.2.5 "resolve against pixel evidence in the disputed strip" names no adjudicator, no crop rule, no gate — and the strip is framed by the incumbent. §9.1's drop-cap fix reuses the ARCHAIC-derived lexicon of E5(iii). §5.3.2's classifiers have no accuracy gate, no n, no held-out set. | — |

---

## P — executability

**Stage −1 as specified: 155–275 focused hours = 5–9 weeks at 30 h/wk, realistically 3–4 months elapsed**,
sitting at step 1 of 12 and gating everything.

| set | as specified | hours |
|---|---|---|
| GOLD-TEXT | 1,800–3,000 lines @ 2–3 min | **75–150 h** + 10–15 h protocol/tooling |
| GOLD-LAYOUT | 250 pages × 6–10 min | **25–45 h** |
| GOLD-GLYPH | ~1,600 crops @ 10 s = 5 h; **the miner is the cost** | **20–40 h** |
| NOISE-FLOOR | 300 lines double-keyed + reconciliation | **25 h — and needs a second human who does not exist** |

**Reducible without losing the guarantee** — to **~20 h**, not 200:
- Diplomatic keying for the **copy-text exemplar only**: ~150–200 lines, 8–10 h (the convergent finding).
- GOLD-TEXT **200 lines** ≈ 9k chars ≈ 90 errors at 1% CER, ±10% relative — adequate for go/no-go. 500 only
  buys 0.6-vs-0.5% discrimination that §5.4 already concedes is undecidable.
- GOLD-LAYOUT eval **60–80 stratified pages** (+ optional 60 seed); arXiv:2511.08903's 5%-labels result
  argues the seed can be small.
- GOLD-GLYPH **deferred entirely**.

**Not reducible in kind**: a frozen, image-derived, never-trained-on eval half for text and layout. Round 1
was right that without it every number is circular. That part is non-negotiable — and it is ~15 h.

**Value before gold — yes, and the plan half-admits it.** Steps 0, 2, 3, 4, 5 need no gold set. "Step 1
gates every metric claim" is true of *metric claims*, not of *improvements*; conflating the two is what
makes this four months of unshipped infrastructure.

**Build first — the residue detector (§4.2.3).** Per leaf, the fraction of the chapter's reference span
matched by no recognised line; sort leaves by residue; feed the ranked queue to the existing chapter
workflow. Days of work, existing recogniser, existing geometry. It uses the incumbent pipeline as a
**detector rather than a generator** (so its bias does not propagate), targets exactly R1's censoring
defect (C2), and produces the stratification GOLD-LAYOUT needs — for free.
**Second: declare the copy-text per tome.** One decision, an afternoon, deletes five-sixths of Stage −1.

**Cut or defer**: §9.2 TEI apparatus (keep only page/signature anchors in the data model + the
`unclear`/`gap` mechanism — retrofitting *those* is expensive; the rest is packaging on a text that does
not exist) · §8.2 variant graph / POA (verse-level diff against copy-text finds the same loci at 1/100th
the machinery) · §8.3 isotonic calibration, LLR summation, Henikoff weighting, effective-N (all need
held-out GT a year away; all moot if adjudication is "look at the copy-text image") · **§7 R4
pseudo-archaic outright** (forbidden in the transcript by §0.1.6 and §6; its alignment-prior use is
subsumed by confusion-derived costs — a component with a gate, a metric, and **no consumer**) · §5.4 TOME
hierarchy and the H×pooling sweep (after SOURCE beats CATMuS, not during) · §5.4 ensemble diversity (a
late-stage 0.2% play) · §3 G2+ (one generation, honestly measured, before designing the loop's
termination condition).

**Stall risks, with escapes that are not degradation:**
- **NOISE-FLOOR needs a second transcriber who does not exist.** → same person, blind re-key of 100 lines
  ≥3 weeks apart, reported explicitly as an **intra**-transcriber floor and labelled a **lower bound** on
  the true floor. Weaker estimator, honestly named.
- **GOLD-GLYPH's ≥200 gate can never pass** (= E2). → **census, not rate**: every instance found and
  adjudicated once, published as a list. A census is *stronger* than a recall figure on n=12.
- **"OPEN and blocking" applied uniformly means nothing ever ships.** → distinguish **release-blocking**
  (copy-text loci) from **campaign-open** (everything else). Both stay open; only one gates a version.
- **"Escalate to Sir with the floor attached" is a no-op on a one-person team — Sir is the team.** →
  escalation writes a **dated, numbered ALERT record** naming the approach to be redesigned; the component
  parks as OPEN with that number attached.
- **arXiv:2607.00596 is unverified and load-bearing for §4.2's gate.** Resolve or delete **this week**.

**Simpler architecture (P's own words): one copy-text per tome, one recogniser fine-tuned on it, gold only
for that copy-text.** GT from alignment where an archaic reference exists, hand-correction where it does
not. Output carries page/signature anchors and explicit gaps. The other five sources are **never OCR'd to
publication quality** — consulted *as images* at flagged loci, which is all §0.1.3 permits them to do.

---

## H — CTC / HTR engineering

| # | defect | fix |
|---|---|---|
| **H1** | **§5.3 conflates two unrelated problems; `ſ`/`f` should never have left the codec.** ſ vs f differ by a left nub vs a full crossbar — a decisive, always-present cue on a class with tens of thousands of instances. Nothing like `ﬃ`/`ﬄ`. Routing it to a per-pair crop classifier removes a **high-support** class from end-to-end training and reintroduces the segment-then-classify pipeline CTC exists to avoid. The real cause of ſ/f error is that the nub is **2–4 px after rescale to H=120**, plus JBIG2 symbol merging. | `ſ f æ ﬀ ﬁ ﬂ` stay in the codec, trained normally. Fix by **resolution** (x-height-normalised input, H6) and **decode-time prior correction**. Report ſ/f as a per-class confusion, not a subsystem. |
| **H2** | **Connected components and advance width will not separate ligature from kerned pair on this material.** At 650 ppi with ink spread a printed line is largely **one** connected component — CC gives words, not glyphs — and broken type splits single sorts in two. Advance width is unmeasurable: CTC peaks are spiky and fire near a symbol's discriminative **interior**, not its left edge; cut error is routinely ±half a character. And to forced-align to `ﬁ` the codec must already contain `ﬁ` — **the lattice circularity, relocated.** Realistic width/CC discriminator accuracy ~60–75%: useless against a ~99% context prior. | The discriminators are pair-specific and **visual**: `ﬁ`/`ﬂ` — **the tittle is absent** in the ligature sort (that is the ligature's whole reason to exist); `ﬀ` — one crossbar spanning both stems vs two; `ct`/`ſt` — the connecting arc. One small CNN over **fixed-window crops centred on the base model's `f`/`ſ`/`t` emission frame**, at native resolution — not on cut widths. Report against a per-pair confusion floor. |
| **H3** | **"Targeted instance mining" IS bootstrappable — but not by shape.** You cannot mine by shape without the classifier you are training. You do not need to: **`ﬃ`/`ﬄ` occur in a closed orthographic set** (afflict-, suffic-, effic-, offic-, fulfill-…), so the archaic lexicon plus the base model's `ffi` trigram emission localises essentially every corpus instance for free. **Macrons**: mine loci where the recognised token is exactly one character shorter than the reference token with a nasal at the deletion point. Non-circular, text-only. **Also: GOLD-GLYPH as crops cannot score a line recognizer** — §5.5's "macro error measured on GOLD-GLYPH" has no computable evaluation path. | Adopt the orthographic-set miner. Store mined instances as **whole GOLD-TEXT lines with the locus marked**, not crops. |
| **H4** | **Blanket NFD is net-harmful; 10–50× oversampling is the most likely thing to break the run.** *NFD*: pooling onto one U+0304 does pool support — but it lengthens every diacritic label, lets the model drop the mark for a **one-label** penalty instead of a whole-symbol penalty (**macron recall can fall while support rises**), and makes CER count one visual error as **two edits**, so CER-folded ≤1% is no longer comparable to the literature §5.5 invokes. *Oversampling*: it is **line-level** — duplicating a line 50× duplicates its ~40 other characters, its fount, its page texture and its binarisation artefacts, and rare-class lines cluster in a few gatherings, so you 50× a handful of pages. **Precision breaks first**: the model emits `ﬃ`/macrons spuriously and overfits those pages' ink while the rare-class recall metric goes up. **A metric-gaming engine built into training.** | A private **decompose-marks-only** mapping (not blanket NFD) on codec and GT; **score on the composed form**; pin the form at both ends. Cap sample weight at **3–5×**; take the real gain from **synthetic line rendering** from a digitised fount with degradation (absent from the plan entirely, and the standard remedy) and **decode-time logit prior-scaling** (÷ prior^α — costs nothing, distorts no training). |
| **H5** | **§5.5 — wrong interval, and one metric is anti-correlated with the goal.** Character errors cluster by line, page and fount; **Wilson assumes i.i.d. Bernoulli and will be 2–4× too narrow** — while §5.4 already mandates a cluster bootstrap for model comparison, so the document contradicts itself. **Attested-form rate penalises precisely the turned letters, wrong-fount sorts and compositorial spellings §0.1 requires preserving**, and its lexicon derives from references §2.2 documents as contaminated. δ undefined throughout. **Missing entirely: line-segmentation error** (missed/merged/clipped lines) — which dominates real CER on this material and is what §4.2's whole redesign targets — **and WER**. | Cluster bootstrap over pages. Attested-form rate → diagnostic with unattested tokens enumerated, **never a gate**. Add line-segmentation error and WER. Fix δ. |
| **H6** | **§4.1's raster policy sabotages CATMuS transfer, and it will be misread as source difficulty.** 1-bit → uint8 yields a two-valued {0,255} image, **not grayscale**: edge gradients are effectively infinite and off-manifold for filters pretrained on antialiased grayscale. Separately, sources at 650 / 300 / ~230 effective ppi rescaled to a fixed **line-box** height present different stroke widths and blur scales — and line boxes include variable ascender/descender and marginalia at other type sizes. | Apply **σ≈0.5–0.8 Gaussian at native resolution before downsampling**. Normalise to **measured x-height**, not line-box height. Without this, cross-source ensembling and any pooled model are invalid. |
| **H7** | **§5.4's own argument kills TOME too.** SOURCE→TOME buys perhaps 0.05–0.2% absolute; detecting it needs the same ~10⁵ held-out characters that killed BOOK. Fount/type-class and scan condition, not tome, drive residual error. | Ship **SOURCE only**; pre-register TOME as a hypothesis **expected to be rejected**. |
| **H8** | Smaller: §5.1 keeps italic/roman "as a semantic" without saying whether it enters the codec — **if it does it doubles the alphabet and manufactures a new rare-class problem**. §5.4's Calamari voter needs `TF_USE_LEGACY_KERAS=1` on py3.12 and **defaults to binarised input, contradicting §4.1**; and cross-height ensembling requires **ROVER/alignment-level** voting, not frame-level — unstated. §6 derives substitution costs from OCR-vs-ARCHAIC confusions, **which contain real textual variance, not just OCR error**. | Italic → word-level style classifier emitted as markup (= S-C1). Estimate costs on GOLD-TEXT. |

---

## S — scholarly editing

**A1 (blocking). "No other witness may alter an accidental. Ever." conflates *edition* with *exemplar*.**
Copy-text is a **setting of type**, not a particular scan. Two scans of the same setting are the same
document; taking a reading from the cleaner one **is not emendation, it is transcription**. As written,
§0.1.2 forces the plan either to mark thousands of routine legibility resolutions as emendations
(drowning the apparatus) or to gap them (destroying the deliverable).
→ **Three-way witness typology**: *copy-text exemplar* / *supporting exemplar of the same setting* /
*other-edition witness*. Same-setting readings go to a lightweight `<witDetail>` register ("copy-text
illegible; read from S08, same setting, forme verified"). **Setting identity must be proved, not assumed**
— signature, catchword, headline, line-endings, and ≥1 accidental of the same forme. Only **cross-edition
supply** is an emendation.

**A2. Otherwise the constitution stands.** "Accidentals follow copy-text" *is* "archaic spelling and
archaic types preserved"; Greg's rule is the mechanism, not a substitute. 1630s-as-substantive-only is
exactly Sir's "supplemental voters." No over-constraint — **except** that nothing in Sir's ask requires a
*critical* edition, and §9.2 imports that overhead (→ the convergent finding).

**B1 (blocking). "Copy-text per tome" does not survive contact with the bibliography — the units are
three, not two**: **(i) NT, Rheims, John Fogny, 1582** (STC 2884); **(ii) OT vol. 1, Douai, Laurence
Kellam, 1609** (STC 2207, Genesis–Job); **(iii) OT vol. 2, Kellam, 1610** (Psalms–2 Machabees with the
appendix: Prayer of Manasses, 3–4 Esdras). Separate impressions, title-pages, compositor stints, founts
and rules. **Three copy-texts, three sets of accidentals, three sigla stacks.**
→ Define "tome" = **volume as issued**, name the three in §0.1, and state that the reference text is
**three copy-texts concatenated**, each labelled, **with no accidental harmonisation across the join**.
Still one transcript; still what Sir wants.

**B2 (blocking). The plan never states which scan is which edition.** §2.4 lists S9/S06/S03a/S08 by pixel
dimensions only. Nothing maps a source to an edition, volume or repository — yet copy-text selection is
the load-bearing decision (= E12).
→ **Source concordance table before step 0**: siglum → edition/volume → STC/ESTC → repository + shelfmark
→ scan provenance/IIIF → completeness and imperfections → JBIG2 status. Copy-text chosen on completeness,
impression quality and absence of sophistication, **documented with the losing candidates and why**.
Likely awkwardness to state now, not at step 11: **some of the six are 1633/1635 and are therefore
ineligible as copy-text for anything**; where only one scan exists for a 1609/1610 volume, A1's
supporting-exemplar route is unavailable and **gaps will be real**.

**C1. Italic must not be a glyph class** (independent convergence with H8). Doubling a ~400-class codec
into roman/italic pairs is fatal to §5.2's rare classes and to CER-diplomatic. Italic, small-cap and swash
are **style, not character identity**.
→ A **style channel**: a **per-word** (not per-character) font classifier over the line image, emitted as
`<hi rend="italic">` / `rend="smallcaps"` alongside a single-case codec. Swash capitals are
`rend="italic"` + a `@rendition` note, not a separate reading. **Turned letters and wrong-fount sorts
cannot be codec atoms** — encode as the character actually *set* with `<sic>` / `@rend="turned"`, detected
as anomalies, **never trained as classes**.

**C2. Still missing from the inventory, and actually present in DR**: the **note-reference marks**
(`*`, `†`, `‡`, superscript letters, `¶`) keying marginal annotations to the text — **in the
Douay-Rheims the apparatus is half the book, and a transcript that drops the keys is unusable**; roman
numerals including terminal `ij`; **Greek and Hebrew sorts** in the annotations; braces and printers'
rules; **`ſſ ſi ſl`** in addition to `ſt`/`ct`.
**Still possibly wrong**: "blackletter in headings" — Fogny and Kellam set roman/italic. **Verify against
the scans before enshrining it, or it is the same fantasy as `ꝛ`.**

**C3. No lineation, hyphenation or paratext policy anywhere.** Does the transcript preserve original
line-breaks? Are catchwords excluded (Sir's standing rule: yes), running heads, chapter arguments, the
marginal annotations, the 1582 preface, the chapter-end annotations? **These are the largest scoping
decisions in the project and the document is silent.**
→ A short **§0.3 "what is in the transcript"**: in / out / optional-layer per paratext class, plus
line-end policy (`<lb break="no"/>` for hyphenated) and page/signature milestones.

**D. Minimal viable apparatus.** *Necessary*: (1) the source concordance; (2) statement of editorial
principles with worked examples; (3) `<pb>`/signature milestones **in the output** — without them nothing
is checkable; (4) `unclear`/`gap` with `@cert`/`@reason`; (5) one machine-readable **emendation register**
(locus · copy-text reading or *illegible* · adopted reading · siglum · authority), one line each,
pipeline-generated; (6) A1's separate same-setting-supply register; (7) TEI header + versioned, sha-pinned
release.
*Overhead — demote to optional*: full **rejected-variant record** (that is a critical-edition negative
apparatus; ship the raw collation graph as a **data file**, not prose) · **press-variant collation as a
programme** (needs multiple exemplars per forme we do not have → a stated caveat plus opportunistic
recording) · uncertainty markup at *every* adjudicated locus (restrict to loci **not** resolved by the
copy-text image, else the markup is noise).

**E. The 22.6% is mis-stated and it will alarm Sir.** **8,383 loci lack an archaic *reference*, not
archaic *pages*.** The scans contain those books. The middle path is therefore not synthesis: (i)
pseudo-archaic stays an alignment/scoring prior only; (ii) those books run with a **weaker alignment
anchor** and therefore need proportionally **more** GOLD-TEXT/GOLD-LAYOUT stratification — make §4.2.8's
gesture a **quota**; (iii) **gaps arise only from illegibility and should be rare**. Rewrite every sentence
implying 22.6% of the Bible may end as gaps.

**F1. Two conflicting address systems.** Output is verse-keyed, but citability requires page/signature,
and they cross-cut (verses span pages; 1609 and 1582 paginate differently).
→ **Page/signature = primary physical address; verse = secondary logical address**, both on every line.
Verse numbering follows **the copy-text's own numerals** where they exist, with §8.1's content-derived
address recorded as a separate attribute when they differ. **Never silently normalise to modern
versification.**

**F2. §0.1.6 vs §8.2.5.** The path-validity constraint still permits a path assembled from *different*
witnesses across a verse. Under copy-text discipline the correct constraint is stronger: **the copy-text
path stands unless a locus is individually emended — there is no witness-voting path for accidentals at
all.** Rewrite §8.2.5, or the collation stage still generates text.

---

---

# PANEL B — the independent replicate

Same four remits, same two input documents, no knowledge of panel A. Only what panel B adds or contradicts
is recorded here; silent agreement with panel A is reported in § REPLICATION.

## E′ — evaluation integrity (adds to E)

- **E′1. The power shortfall, computed independently and in more detail.** 400 lines × ~45 chars ≈ **1.8×10⁴
  chars/source — 5.6× short of the plan's own stated ~10⁵ requirement.** At p=0.01, SE = 0.074%, 95% CI
  **±0.145%**; with burst-error clustering (design effect 2–3×) the true CI is **±0.21–0.25%**. So
  "CER-folded ≤1.0%" **cannot be distinguished from 1.29%**, and "floor + δ" cannot resolve any δ < 0.3%.
  Correctly sized to detect δ=0.1% at 80% power, paired: **~1.2×10⁵ chars ≈ 2,700 lines/source, ×2 for
  clustering ≈ 5,000 lines/source = 30,000 lines total.** → Either commit and state the hours, or **delete
  every gate whose δ is below the achievable CI** and say in the table what 400 lines actually buys.
- **E′2. The adaptive-leakage magnitude, quantified.** Per generation ≈ 3 layout + 5 recognition + ~6 sweep
  + 5 ladder ≈ **19 queries; three generations ≈ 57.** At SE=0.074%, **E[max of 57 noise draws] ≈ 2.4σ ≈
  0.18% apparent CER gain from pure noise** — larger than any δ the plan would plausibly set. **Freezing and
  sha-pinning prevents *contamination*, not *adaptive leakage*; revision 2 conflates two different
  failures.** And **escalation rung 1 is "annotate more pages" — growing the eval set in response to failing
  it.** → Thresholdout/reusable-holdout: DEV (unlimited) · VAL (Laplace-noised, tolerance T=0.3%, **hard
  budget B=20 queries, counter published**) · HOLDOUT (opened once at step 11, the only publishable
  numbers). **Rung-1 new pages go to DEV/train only.**
- **E′3 (NEW, and panel A missed it). GOLD-LAYOUT cannot support the stratification it declares.**
  6 sources × 2 parities × 73 books = **876 cells for ~125 eval pages = 0.14 pages/cell.** The five
  zero-witness books get ~8 eval pages *across all sources* — the stratum the plan calls structurally
  critical is the one it cannot measure. **Marginalia: 1,334 blocks over ~2,900 pages/source → ~15 blocks in
  125 pages; Wilson width ±25pp, so the marginalia recall/precision gate is unfalsifiable at any
  threshold.** Boundary error in pixels is the one adequately-powered metric here and draws no objection.
  → **Stop stratifying on book.** Stratify source × parity × page-type (3–4 types) ≈ 48 cells, ≥3 pages each
  ≈ 150 pages, **plus purposive over-sampling**: ≥40 pages from zero-witness books, ≥60 selected *because*
  they contain marginalia, sampling weights recorded and the estimator re-weighted. **Report marginalia
  metrics with block-level n, not page-level.**
- **E′4 (NEW). The two terminals — this is the No-Silent-Degradation-correct formulation.** "Improvement < δ
  → escalate with the floor attached" **fires identically whether the metric is above target (converged) or
  below it (stalled)**. Escalating a below-target unit and moving on **is the same laundering as the WARNING
  class §9.1 explicitly withdrew.** → Two distinct terminals, both explicit: **CONVERGED-AT-TARGET**
  (metric ≥ threshold ∧ Δ<δ → closed) and **STALLED-BELOW-TARGET** (metric < threshold ∧ Δ<δ → **OPEN,
  blocking, ALERT for approach redesign; the deliverable does not ship**). Plus a **regression rule**: if
  G(n+1) is worse than G(n) by more than the paired CI, G(n+1) is a **failed experiment** — revert artifacts
  to G(n), do not adopt, **do not re-baseline**.
- **E′5 (NEW). NOISE-FLOOR per-class arithmetic.** 300 lines ≈ 1.35×10⁴ chars; at 0.5% disagreement ≈ 68
  events, CI ±0.12% — **the floor is known no better than the quantity gated against it.** Per class it is
  far worse: **~500 `ſ` instances yielding perhaps 5 `ſ`/`f` disagreements — the floor for the single
  distinction the edition rests on, estimated from 5 events.** Two transcribers also estimate only
  *independent* disagreement; **shared-protocol correlated error (both read the worn `?` as `;`, both miss
  the same macron) is invisible, and that is what actually bounds achievable CER.** → **Three** transcribers
  on n=150 to expose 3-way vs 2-way agreement and estimate correlated error, **plus a per-class floor on a
  purposive `ſ`/`f` and macron set (≥300 instances each, drawn by census not line sampling). Publish the
  floor per class — a single aggregate floor is not usable for a per-class target.**
- **E′6. Two more circularity paths panel A did not name.** (v) **§6's strict distance threshold survives:**
  C2's class-conditional censoring was fixed for *geometry labels* (residue-as-signal) but **not for GT
  acceptance** — words the recognizer never read still never enter GT, so **G2 trains on the same censored
  distribution**. → record and report per generation the **fraction of reference span never accepted, as a
  blocking OPEN quantity**. (vi) **G2 regions are relabelled from G1 alignment, which ran on G1 geometry**;
  the only external check is GOLD-LAYOUT eval, now queried every generation (E′2). Also: score attestation
  against an **external lexicon (EEBO-TCP 1580–1640)** with overlap rate reported; **freeze substitution
  costs at G1** and re-derive only from GOLD-TEXT confusions.
- **E′7. Words-not-mechanism list, extended.** C6's remedy — "Henikoff weighting; effective N reported per
  locus" — **reporting N_eff is not a mechanism; nothing says what happens when N_eff = 2.1.** → blocking
  gate: **mean N_eff ≥ 3.5 over sampled loci, measured pairwise on GOLD-TEXT, else the ensemble is not used
  for adjudication at all.** C1's layout gate needs its numbers *published before G0 is measured and
  sha-pinned* (worked example: marginalia recall ≥0.85 ∧ precision ≥0.90; MainText boundary error ≤8 px
  median / ≤25 px p95; n≥125 eval pages). **C13 (the style inventory) is the largest words-only item — an
  entire new supervision modality asserted in one paragraph**: a CTC line recognizer over a character codec
  **structurally cannot emit a style channel**, and there is no encoding scheme, no GT protocol, no
  annotation cost and no gate. → either a **second style head with its own GT and gate**, or **explicitly
  scope style out of G1–G2 and record it as a known non-preservation in the statement of editorial
  principles.**
- **E′8. Panel B's "adequately answered" list** (no finding, do not re-open): C4 lattice withdrawal, C5
  POA/path-validity, C10 offset-0 + permutation null + glyphs-unfolded, C14 JBIG2 test with a stated
  decision rule, C15 board-netting, union iteration, DropCap-as-alignment-deficit, marginalia-negative
  mining.
- **E′9. §0.2 diagnosis, sharpened.** The over-correction is **not** "unfalsifiable ambition" as the plan
  feared — **it is unstartability, which is the original failure mode reached by a longer route.** A
  prerequisite that cannot be satisfied produces the *same observable outcome* as status-quo preservation:
  nothing moves. And **Sir's instruction was to avoid human-review bottlenecks**; §1 claims to honour it "at
  the production path" but then **makes the whole build order depend on the review path — the same
  bottleneck one level up.**

## P′ — executability (adds to P)

- **P′1. Independent costing: ≈ 210–280 hours** (panel A: 155–275). GOLD-TEXT 55–75 h at 35–45 lines/hr +
  25–35 h protocol/sampling/QC · GOLD-LAYOUT 45–75 h at 10–18 min/page (**because §4.2's gate is boundary
  error in pixels, boundaries must be ink-tight**) · GOLD-GLYPH 20–30 h labelling **+ 40 h developing the
  miner** · NOISE-FLOOR 25 h. **At 12 productive hrs/week that is 17–23 weeks before step 6 can start**, and
  steps 6–11 are the entire product.
- **P′2 (NEW, and it is the best idea in either panel). The correction UI makes gold-keying and production
  transcription the same keystrokes.** Panel A said "build the residue detector first"; panel B says build
  **a single-witness, copy-text-first correction loop over the best-impression tome**: page → lines →
  incumbent recognizer → operator correction UI → sha-pinned corrected page. **One activity, five outputs:**
  (a) shippable product, (b) GOLD-TEXT, (c) fine-tuning GT for the next generation, (d) GOLD-LAYOUT if the
  UI captures line/region boxes, (e) GOLD-GLYPH crops via click-to-tag. **That is the only way ~250 hours of
  annotation becomes affordable — it is not overhead, it is the deliverable.** Ships value in week 2 and
  every week after, and **the 0.9392 board is never the metric because the corrected page *is* the
  reference.** → **Order the first pages from a zero-archaic-witness book (Ecclesiasticus, Isaie)**, because
  those 8,383 loci are structurally invisible to every reference-based mechanism in the plan and will
  otherwise be discovered last.
- **P′3. A rolling held-out set that is free and cannot be gamed.** Fine-tune every N signed-off pages;
  **measure CER on the last 20 signed pages *before* they entered training.** Never stale, no annotation
  cost, and immune to E′2's adaptive leakage because each slice is used once.
- **P′4. NOISE-FLOOR escape, costed.** Time-separated self-re-keying (blind, ≥3 weeks) gives an
  **intra**-transcriber floor — a **lower** bound, the conservative direction. Resolve each disagreement
  against a magnified crop and record a **per-class irreducible-ambiguity rate** (the `ſ`-nub,
  macron-vs-speck) — *that* per-class rate is what §5.5 needs. **Then buy 8 hours of a second keyer for the
  300 lines only (~$200–400) to validate it once. If the two diverge, ALERT: the floor estimator needs
  redesign.** Panel A proposed the same self-re-key; panel B adds the paid validation, which converts a
  weaker estimator into a checked one.
- **P′5. The escalation ladder has no receiver, and no rung has a cost ceiling** — so "after N rungs with
  improvement < δ" has **no N and no δ**. → **Every escalation must name a *different resource class* than
  the one that failed**: paid annotation hours, a purchased or borrowed better scan, an outside
  palaeographer's ruling, or **a stated scope reduction in *coverage* (fewer books at full fidelity) — never
  in fidelity.** Pre-register **N=3 rungs and an hour ceiling per rung** before step 6.
- **P′6. Cuts panel B adds to panel A's list**: **§2.3's coverage interval** with the VerseNumber-derived
  upper bound (a measurement of the references, which the constitution demoted to finding aids), and
  **§4.2's ink-derived region model deferred behind the copy-text source only** — `PAGE_OVERRIDE`'s 371
  bands are adequate for *one* witness; a generalising region model is only needed for the other five.
- **P′7. Panel B's "already adequate" list**: BOOK-scope cut · variant-lattice withdrawal · pseudo-archaic
  barred from GT · DropCap out of the region model · JBIG2 blocking step 0 · 1-bit→uint8 before geometry ·
  WARNING class withdrawn · unanimous-sample image adjudication · ARCHAIC_v0 frozen · union-not-ARCHAIC
  iteration · the arXiv:2511.08903 correction.
- **P′8. The real cost of the product, under any architecture.** ~3,000–4,500 pages at 6–15 min/page
  corrected = **400–1,000 hours of human throughput.** Panel B's point is not that this is avoidable — it is
  that **in the simplified architecture those hours produce the deliverable directly, instead of producing
  the instrument that produces it.**

## H′ — CTC/HTR (adds to H)

- **H′1. The physics, quantified.** *Advance width* is the true physical discriminant — a ligature is cast on
  one body — **but you cannot measure body width, only ink extent**, and the two differ by spread varying
  several hundred µm within a page. The `fi` ligature/pair body difference in 16-pt roman is **0.15–0.25 em
  ≈ 15–25 px at 650 ppi, against spread noise of comparable magnitude plus ±2–4 frames of CTC cut jitter**
  (one frame at H=120 is several px). *CC count is a function of ink load and paper absorbency, not of the
  sort.* **The tittle is the only genuinely local feature** — in the `fi` ligature the f-terminal *replaces*
  the tittle by design. For `ſ`/`f`: same body, same CC, discriminated **solely by whether the nub crosses
  the stem — 3–6 px at 650 ppi, the first thing lost to bleed-through or any lossy raster.**
  **Realistic ceiling**: clean instances `ſ`/`f` 0.97–0.99 F1, `fi`-lig vs `f`+`i` 0.90–0.95; **on the tail
  that matters — touching, over-inked, show-through, worn — 0.7–0.85, and that tail is 10–20% of
  instances. There is no configuration reaching §5.5's per-class precision without an `unclear` escape.**
- **H′2 (NEW, and it is the right fix). Three-way output with calibrated abstention.** One CNN per contested
  pair, **directly on the crop, no hand features**, emitting **`A` / `B` / `indeterminate`** — abstaining
  into §5.1's `<unclear cert="">`. Calibrate the abstain threshold on GOLD-GLYPH so per-class precision hits
  target, and **report the abstention rate as a headline number. An 8% abstention rate on `ſ`/`f` is an
  honest edition; a 0% one is a fabricated one.**
- **H′3 (NEW, and it is the strongest single idea in the round). Exploit the sort, not the instance.**
  Letterpress **repeats the same physical sort**. Cluster all `ſ`-candidate crops **per tome per fount,
  unsupervised; key ~50 cluster exemplars; propagate.** Per-instance classification throws away the one real
  asymmetry the medium offers.
- **H′4. The mining seed, stated as a terminating procedure** (converges with panel A's orthographic-set
  miner and adds the alignment step and the bias bound): (1) contexts are enumerable with no classifier —
  `ﬃ` occurs only where the letters are `ffi`; search ARCHAIC and the modern references for
  `ffi|ffl|st|fi|fl|ff` tokens (`office`, `affliction`, `first`) — thousands in a 400-page Bible. (2) Align
  those tokens via §6 forced alignment **using the incumbent recognizer over the fold-equivalent letters** —
  `f`,`i` are in the codec, so cuts localise to ±1 character **even when the ligature is misread as `f`+`i`
  or dropped**. (3) Crop that window: every crop is a *positive-context* candidate and the only remaining
  question is the pair classifier's own. (4) Key ~200/class. **Declare the recall bias** — you find
  ligatures only where the reference spells the letters, missing compositorial ligatures at unexpected loci
  — **and bound it by keying a random 100-line sample and counting misses.** **`ſ`/`f` cannot be seeded this
  way** (the reference's `ſ` policy is unaudited per §7) — seed it from §7's 200-verse provenance audit,
  already scheduled.
- **H′5. Why NFD fails, mechanistically — panel B's reason is better than panel A's.** **CTC alignment is
  monotonic and one-symbol-per-frame-run. The macron sits *above* the bowl, not after it — there is no
  horizontal region where the mark is present and the base is not.** So a two-symbol target forces the
  network to manufacture an ordering **the image does not contain**; the mark's peak collapses into the
  base's frame run and is absorbed by repeat-collapse or blank. **`õ` decomposed is strictly *harder* than
  atomic `õ`.** Also, kraken's `PytorchCodec` builds from GT graphemes, so **a bare U+0304 becomes a
  standalone code point emittable after any base — the model can produce `t̄` and other non-sorts.**
  → **Keep `ã ẽ ĩ õ ũ` atomic NFC.** Get the sharing by **initialising the five output rows from the base
  rows plus a shared learned offset**, or just accept five atoms — 5 × ~200 mined = 1,000 instances, above
  CTC's viability floor. **Same for `ﬃ ﬄ`: splitting them while keeping `ﬁ` atomic creates a codec where
  `ﬃ` and `ﬁ`+`f` compete for identical pixels — the exact ambiguity §5.3 says has no likelihood
  asymmetry. Make them all atomic. Compose/decompose at output serialisation, never in the codec.** The
  "pin one normalisation form" rule is right, and **it is NFC.**
- **H′6. Oversampling — the calibration harm panel A did not name.** Any oversampling **breaks the softmax
  as a probability of the real distribution, directly damaging §8.3's isotonic calibration and LLR
  summation — you would be calibrating on a distribution that does not exist.** And in letterpress the
  duplicated line contains **the same physical damaged sort, so the model learns the copy, not the class.**
  → **3–8× line replication max; above that switch mechanism to per-class loss weighting inside CTC
  (weight ∝ 1/√freq, capped ~10), which affects only the rare symbol's contribution, not the whole line.**
  **Mandatory per-class monitors at every checkpoint**: rare-class precision **and the frequent neighbour's
  false-positive rate** (if `ﬁ` recall climbs while `f`+`i` precision falls, the reweighting buys nothing);
  reliability diagram / ECE for every class used downstream in §8.3; **calibrate isotonic on an *unweighted*
  held-out set, never the training distribution.**
- **H′7 (NEW). The failure mode that passes the entire §5.5 suite: systematic, attested substitution.** A
  model reading `ſ` for `f` in one ligature context, or dropping a macron on one vowel in one fount,
  produces **attested** output (`ſonne` is a real word), scores fine on CER-folded, and is **diluted below
  detection in per-class recall because the class is right 97% of the time overall. Nothing in the suite
  conditions on context.** → add **per-class error stratified by source × fount × neighbour-context, with
  the max-over-strata reported, not the mean**; add **CER on the GOLD-GLYPH crops' host lines
  specifically**; add a **run-length / consecutive-error statistic** — the suite as written **cannot
  distinguish 100 scattered errors from 100 errors on one gathering.**
- **H′8 (NEW — resolves the TOME question, see § REPLICATION). Replace TOME with FOUNT.** What actually
  varies inside a 1609 tome: the **fount** (roman text vs italic annotation vs blackletter heading —
  genuinely different letterforms, **and the axis §5.1 just declared semantic**), the **compositor**
  (spelling habits, not letterforms — irrelevant to a recognizer), and the **gathering** (paper, ink load,
  impression — a real image-statistics shift). **Tome matches none of these; it is a proxy for scan
  conditions, which is what SOURCE already is.** → third level = **FOUNT**, which has far more data per
  scope than 440 books did. **Handle gathering variation by stratifying the held-out split by gathering —
  the plan's own independence argument demands this and never states it — not by another model level.**
- **H′9 (NEW, and it changes the sweep's cost). Raising H breaks warm-start transfer.** In the CATMuS-family
  VGSL spec, H 120→192 multiplies the height reaching the `S1(1x0)1,3` reshape by 1.6, **multiplying the
  LSTM input width by 1.6 — so `ketos train -i catmus.mlmodel --resize new` will not transfer the reshape
  and LSTM layers. Only H=120 gets clean warm-start.** The correct joint move is **a fourth height-only
  `Mp2,1` stage** to restore the reshape dimension — `Mp2,2` pools height *and* width, and changing width
  pooling would alter frames/char (~8 at 120 px) and **confound the whole sweep.** Realistic grid: 3 heights
  × 2 pooling variants, minus the invalid cell = **5 configs × 3 seeds = 15 runs** (3 seeds because
  single-run variance exceeds the effect on rare classes — the chaotic-model A/B rule). At 6–12 GPU-h/run
  and H=192 cold-start on the recurrent stack: **120–200 GPU-hours, not an incidental line item.** → rank on
  a fixed ~5k-line subset (~40 h), confirm only the top-2 at full data; **pre-register the decision metric
  as `ſ`/`f` + macron per-class F1 with a paired bootstrap over lines, since aggregate CER cannot resolve
  it.**
- **H′10. The binarisation gap is upstream of the fix, and the JBIG2 test gates the wrong thing.** Expect a
  **2–5× CER multiplier on zero-shot CATMuS** against binarised input, and after fine-tuning a persistent
  penalty **concentrated in exactly the 2–4 px features — the `ſ` nub and the macron.** The uint8 conversion
  fixes only *resampling aliasing*; **it does not restore grey levels, destroyed upstream at binarisation,
  and revision 2 treats the correction as sufficient.** **The JBIG2 test measures substitution, which is
  necessary — but the binarisation gap exists even at a zero substitution rate.** → state the policy as
  **grayscale native primary throughout; 1-bit masks are a fallback for sources with no grayscale path
  only, and any such source is trained and evaluated as its own scope with its own reported CER.** Where
  only the mask exists (S06 stencil), **reconstruct pseudo-grayscale by ~0.8 px Gaussian blur — applied
  identically at train and inference, so zero risk.**

## S′ — scholarly editing (adds to S; and see § REPLICATION for the framing disagreement)

- **S′1 (the framing move — panel B goes further than panel A). Copy-text theory is the wrong instrument.**
  Greg's rationale exists to solve one problem: an editor must **construct** a text from witnesses of
  differing authority, chiefly where an author revised. **Its accidentals/substantives split is a rule about
  *authority*, not about *fidelity*.** This project has **no authorial revision, no lost archetype, no
  reconstructive ambition.** §0.1.1/.2/.5/.6 are right (and .5's preservation of compositorial evidence is
  exactly correct). **§0.1.3 and §0.1.4 are imports from critical editing and are actively harmful: they
  license a 1633 reading into a document dated 1582.** And once you say "copy-text," **an apparatus follows
  by convention** — historical collation, sigla, rejected readings, authority chains, cross-exemplar
  press-variant collation (Bowers, *Principles of Bibliographical Description*; Tanselle, "The Editorial
  Problem of Final Authorial Intention") — **and §9.2 duly demands all of it. None of it is answerable here,
  because the six scans are not witnesses to a text: they are photographic surrogates of documents.
  Disagreement among them is scan quality plus OCR error, not textual variation.**
  → **Reclassify as a documentary / diplomatic edition** (TEI P5 ch. 11 "Representation of Primary Sources";
  Tanselle, "Editing Historical Documents"). **Delete §0.1.3 and §0.1.4. The 1630s editions are not
  witnesses at all — they are reading aids for illegible passages, and any use of them is an intervention,
  never an "always-substantive witness."** Keep: transcription protocol, gap/unclear machinery, source
  identification, page/signature reference. **Drop: rejected-variant register, siglum-authority table,
  cross-exemplar press-variant collation, substantive apparatus.**
- **S′2. Three levels, not one — sharper than panel A's "three copy-texts."** **(a) bibliographic unit** =
  edition-issue, cited by STC/ESTC (NT 1582; OT 1609; OT 1610 as separate entries) — this is what §9.2 keys
  to; **(b) exemplar** = one named copy (repository + shelfmark) per bibliographic unit — **this is the
  document being transcribed**; **(c) substitution unit = gathering / forme, not page and not tome** —
  because **stop-press correction is a forme phenomenon, so two copies of one edition differ gathering by
  gathering.** Where the base exemplar is defective and a second copy supplies leaves, **declare it
  leaf-by-leaf in a made-up-copy table** (standard STC/ESTC practice). **"Tome" is a scan-volume word, and
  scan volumes do not respect bibliographic boundaries** — front matter, bound-together copies, made-up
  exemplars.
- **S′3. The setting-identity test, and two disjoint channels** (converges with panel A's A1, and specifies
  it): test = **same signature, same catchword, same turn-lines (line-end words). Identical ⇒ same
  setting.** Then: **Surrogate register (NOT apparatus)** — every page carries a *witness-of-record*
  surrogate; where it is illegible and a same-setting surrogate resolves it, record
  `resolved_from: <surrogate id> @facs zone` + certainty **and nothing else**; machine-readable sidecar,
  summarised **statistically** in the editorial statement, **never enumerated in the reading apparatus.**
  **Intervention apparatus** — only **different-setting** sources (1633/1635, or a different exemplar with
  stop-press variance) may enter, every entry marked `supplied-from-other-setting` **with the source's own
  STC number and date. A reader must be able to see that a word in the 1582 text came from 1635.**
- **S′4. Inventory — panel B contradicts panel A on two removals.** **Removing `ꝛ` while simultaneously
  admitting blackletter headings is self-contradictory — `ꝛ` is precisely the sort blackletter needs.**
  Removing `ꝑ ꝓ ꝗ` "generally" is **over-corrected: the Rheims annotations and running heads carry Latin,
  where per/pro brevigraphs do occur in roman-type Latin printing of the period.** PUA removal is right, but
  **state the rule as "no PUA in output; combining marks preferred," not "no MUFI" — much of MUFI is now
  standard Unicode.**
  On the additions panel B is harsher than panel A: **small caps, swash italic capitals, blackletter,
  italic/roman and `VV` are not characters — they are rendition states**, and admitting them multiplies the
  class count several-fold, **destroying the rare-class budget §5.2 just built.** `VV` is two sorts:
  **transcribe `VV`, record rendition.** **Turned letters and wrong-fount sorts are worse: a turned `u`
  standing for `n` is not a glyph, it is a *defect in a sort*; encoding it as a character forces a reading
  decision into the codec.** → `<sic>` at the letter the sort represents, with `@rend="turned"` /
  `@rend="wrong-fount"`.
- **S′5 (NEW, and it is the implementable form of the italic fix). A stand-off rendition layer.** Not
  character-level (doubles the alphabet, kills CTC); **not inline `<hi>` in the recognition stream — markup
  does not survive OCR, alignment or edit distance.** → **the text channel is a plain grapheme string with a
  stable character index; a parallel span table holds `{start, end, rend}` over that same index** (TEI P5
  `<span>`/`@spanTo`). Consequences the plan needs: **font is recognised by a separate classifier over the
  line image, never by the CTC head; alignment and collation run on the character channel unchanged;
  scoring is two channels — CER on characters, plus span-level precision/recall/F on rendition, reported
  separately and never folded into CER**; serialisation materialises spans into `<hi rend="italic">`,
  `<seg rend="sc">`, `@rend="blackletter"`. **The same layer carries turned/wrong-fount marking, so §0.1.5's
  preservation requirement is met without touching the codec.**
- **S′6. Minimal apparatus, as a schema.** One record type, **at intervention granularity — the overwhelming
  majority of verses produce zero entries**:
  `{ locus: signature + leaf side + line + char-offset (e.g. Aa3v.12.7) | verse key | category |
  base_reading | adopted_reading | evidence | agent | cert }`, `category` ∈
  `{gap, unclear, resolved-from-surrogate*, supplied-from-other-setting, sic-preserved,
  editorial-correction}` (*lives in the surrogate register). `evidence` = surrogate id + `@facs` zone, or
  source STC number + date. **Plus, once per edition, not per locus**: STC/ESTC + repository + shelfmark +
  made-up-leaf table; scan provenance and checksums; **a statement of editorial principles listing what is
  silently normalised (line breaks, word division at line-end, whitespace) so those never generate
  records**; TEI header with `<sourceDesc>`/`<encodingDesc>`/`<respStmt>`; **`<pb n="" facs=""/>` and
  `<milestone unit="signature"/>` in the text stream — the one apparatus obligation that is
  non-negotiable.**
- **S′7. The pseudo-archaic bright line, stated exactly.** The TEI gradient the transcript may use: read
  confident → plain text; read uncertain → `<unclear reason="damage|inking" cert="low|medium"
  resp="#ocr-v2">` (**retains the reading, flags it**); not read → `<gap reason="damage" quantity="4"
  unit="chars"/>` (**default plain-text export emits the gap, not a guess**); supplied from a **document** →
  `<supplied source="#stc2884" cert="">`, **bracketed in every view.**
  **The bright line: `<supplied>` requires `@source` pointing at a DOCUMENT. Rule-generated pseudo-archaic
  has no document source and therefore can never appear inside `<supplied>`, bracketed or not.** It may
  exist as a **separate, separately-named reconstruction layer** — distinct file, `type="reconstruction"`,
  **never merged into the documentary text, excluded from all citable exports, labelled non-documentary at
  the top of every view.** Used as §7-R4 specifies (alignment prior, scoring aid) **that layer is
  legitimate and no reader can mistake it for the text.**
- **S′8. On the 8,383, panel B agrees with panel A and adds the correct name for it.** Those loci are **not
  transcript gaps — they are a QC-coverage figure (no independent check on the OCR), not a fidelity
  crisis.** Revision 2 got this right and **should stop calling it a transcript problem.** The real risk is
  narrower and should be stated as such: **where the OCR is unsure *and* no archaic reference exists, there
  is no check, so a plausible hallucination is indistinguishable from a reading.**

---

# REPLICATION — what two blind panels did and did not confirm

## CONFIRMED (independently reached by both critics on a remit) — treat as settled

| finding | A | B |
|---|---|---|
| **Stage −1 is ~200 hours and the plan states zero** | 155–275 h | 210–280 h |
| **GOLD-TEXT is ~5–10× under-powered, by the plan's own §5.4 argument** | ~10× | 5.6×, CI ±0.145% → ±0.25% clustered |
| **"≥200 instances per rare class" is arithmetically impossible → census, not rate** | E2 | 2 |
| **Mining by shape is detector-conditioned → rare-class recall unmeasurable by construction** | E2 | 6.1 |
| **Adaptive overfitting: one frozen set, dozens of adoption decisions; freezing ≠ protection** | E4 | ~57 queries, E[max]≈0.18% |
| **9–10 of 12 gates lack threshold and/or n; δ is never defined anywhere** | E8 | 5 |
| **Circularity survives via confusion-derived costs, isotonic calibration, attested-form lexicon, and residue being null on the 8,383** | E5 | 6 |
| **No rule for G1 < G0; the loop is not EM and not convergent** | E7 | 7 |
| **NOISE-FLOOR needs a second human who does not exist → time-separated blind self-re-key, labelled a lower bound** | P | 3 |
| **Cut: §9.2 apparatus except page/signature anchors + `unclear`/`gap`; §8.2 variant graph; §8.3 calibration/LLR/Henikoff; §7 R4 pseudo-archaic; ensemble diversity; G2+** | P | 5 |
| **Nothing ships for ~4 months; the simpler architecture is single-witness copy-text-first** | P §2/§6 | 4/6/7 |
| **Escalation terminates in "escalate to Sir" and Sir is the team — a no-op** | P | 9 |
| **CC + advance width cannot separate ligature from kerned pair; the tittle is the real feature** | H2 | 1 |
| **Instance mining IS bootstrappable — through the TEXT side (closed orthographic contexts), never the shape side** | H3 | 2 |
| **NFD is net-harmful → keep atomic, pin one form, compose/decompose only at serialisation** | H4 | 3 |
| **10–50× oversampling is out of range → ~3–8×, plus synthetic rendering and decode-time prior scaling** | H4 | 4 |
| **Binarised input sabotages CATMuS transfer; ~0.8 px Gaussian at native res is the fix** | H6 | 7 |
| **Italic/small-caps/swash/turned/wrong-fount must NOT be codec classes → separate style channel → markup** | S-C1 + H8 | S′4/S′5 + 8 |
| **"Copy-text per tome" is not a bibliographic unit; three printings, and the plan never says which scan is which edition** | S-B1/B2 | S′2 |
| **"Same setting, better scan" is a READING, not an emendation, and needs its own channel + a mechanical setting test** | S-A1 | S′3 |
| **Minimal apparatus = intervention records only; page/signature milestones are the non-negotiable part** | S-D | S′6 |
| **Pseudo-archaic barred from the transcript is correct; the middle path is a separately-named layer** | S-E | S′7 |
| **The 8,383 lack an archaic *reference*, not archaic *pages* — the gap framing is wrong and alarming** | S-E | S′8 |

## OPEN — same-remit specialists disagreed; **these are Sir's calls, and I will not pretend the panel settled them**

1. **Model scope above SOURCE.** H says **cut TOME** (it inherits the same power problem that killed BOOK).
   H′ says **replace TOME with FOUNT** — because fount is the axis on which letterforms *actually* differ,
   it is the axis §5.1 just declared semantic, and it has far more data per scope than books did. **Both
   agree TOME-as-written is wrong.** H′'s reasoning is mechanistically stronger and I lean to FOUNT, with
   gathering handled by *stratifying the held-out split*, not by another model level.
2. **Editorial framing.** S says **keep copy-text discipline and repair it** with a three-way witness
   typology. S′ says **abandon copy-text framing for documentary/diplomatic editing** (TEI P5 ch. 11) and
   **delete §0.1.3/§0.1.4 outright**, because Greg's rule is about *authority* under authorial revision —
   which this project does not have — and adopting the word drags the whole critical-edition apparatus in
   behind it. **Both agree the apparatus obligations must go and that same-setting supply is not
   emendation.** S′'s diagnosis explains *why* revision 2 acquired §9.2's overhead, so I lean to the
   documentary framing — **but this decides what the product is called and what it promises scholars, and
   it is Sir's to decide.**
3. **First build.** P says **the residue detector** (days, uses the incumbent as a *detector* not a
   generator, produces GOLD-LAYOUT's stratification for free). P′ says **the correction UI** (one activity,
   five outputs; gold-keying and production transcription become the same keystrokes). **These are
   compatible and I intend to propose both — residue detector as the page-ordering signal *feeding* the
   correction UI** — but P′ is right that the UI is what makes ~250 annotation hours affordable, and that is
   the load-bearing claim.
4. **`ꝛ` and `ꝑ ꝓ ꝗ`.** S endorsed removing them as anachronistic. S′ says **removing `ꝛ` while admitting
   blackletter headings is self-contradictory**, and that per/pro brevigraphs **do** occur in the Latin of
   the Rheims annotations and running heads. **Resolvable empirically and cheaply — inspect the scans.**
   That inspection is now a task, not a judgement call. Note this is entangled with S-C2's separate
   instruction to **verify the blackletter headings themselves against the scans before enshrining them**:
   if there is no blackletter, both questions close together.

---

## What revision 3 must do — final, both panels folded in

**My four decisions on the OPEN items** (taken under the standing full-autonomy grant, flagged for Sir to
overturn — each is a one-paragraph change if he disagrees): **(1) FOUNT replaces TOME**, gathering handled
by held-out stratification. **(2) Documentary/diplomatic framing** (TEI P5 ch. 11), copy-text retained as a
*mechanism* for choosing the base exemplar but not as the edition's constitution; §0.1.3/§0.1.4 deleted.
**(3) Both first builds — the residue detector becomes the page-ordering signal feeding the correction
UI.** **(4) `ꝛ` and `ꝑ ꝓ ꝗ` become an inspection task, not a judgement**, resolved together with the
blackletter-headings question by looking at the scans.

**Structural**
1. **Decide the product explicitly** — one documentary transcript from a declared base exemplar, *not* six
   publication-quality transcripts. **Put the decision and its ~400–1,000 h true cost at the top, in Sir's
   terms.** This is the round's convergent finding and it is the largest change in the document.
2. **Source concordance table before step 0**: siglum → edition-issue (STC/ESTC) → **exemplar (repository +
   shelfmark)** → scan provenance → completeness/imperfections → JBIG2 status. **State now that some of the
   six are 1633/1635 and therefore ineligible as base for anything.**
3. **Three declared units**: bibliographic (1582 Fogny NT · 1609 Kellam OT1 · 1610 Kellam OT2) · exemplar ·
   **substitution unit = gathering/forme**. Made-up-copy table for defective leaves.
4. **Surrogate register vs intervention apparatus as two disjoint channels**, gated by the mechanical
   setting-identity test (signature + catchword + turn-lines).
5. **§0.3 paratext / lineation / hyphenation scope table** — the largest unstated scoping decisions.
6. **Re-sequence: correction UI + residue detector first.** Value in week 2. **Pilot gold measures the
   keying rate; the real gold is sized from observed variance.** Every pre-pilot number labelled
   **PROVISIONAL, non-citable.**

**Evaluation**
7. **DEV / VAL / HOLDOUT** with a **published query ledger** (VAL: Laplace-noised, T=0.3%, B=20; HOLDOUT
   opened once at step 11). **Escalation rung-1 pages go to DEV/train only, never to VAL or HOLDOUT.**
8. **Split GOLD-LAYOUT by gathering.** **Stop stratifying on book** — stratify source × parity × page-type
   (~48 cells), **purposively over-sample** ≥40 zero-witness pages and ≥60 marginalia-bearing pages,
   re-weight the estimator, **report marginalia at block-level n.**
9. **GOLD-GLYPH → exhaustive census**, disjoint train/eval **by page**; Clopper–Pearson intervals;
   **census < 30 ⇒ UNMEASURABLE, OPEN and blocking.**
10. Close all **six** circularity paths (E5 i–iv + E′6 v–vi), including the **never-accepted reference-span
    fraction reported per generation as a blocking OPEN quantity** and an **external attestation lexicon
    (EEBO-TCP 1580–1640)**.
11. **Rewrite every gate**: metric · threshold · named set · n · pre-registered effect size — **as a
    document-level invariant, no step enters the build order without all five.** **Define δ, and require
    δ ≥ 2× the set's SE or the gate is void.**
12. **Two terminals, explicit**: CONVERGED-AT-TARGET vs **STALLED-BELOW-TARGET (OPEN, blocking, ALERT for
    approach redesign — the deliverable does not ship)**. **Regression rule**: G(n+1) worse than G(n) by
    more than the paired CI ⇒ failed experiment, revert, **do not re-baseline.**
13. **Pre-register δ before NOISE-FLOOR is read.** Three transcribers on n=150 to expose correlated error;
    **per-class floor on a purposive `ſ`/`f` and macron census (≥300 each)** — a single aggregate floor is
    unusable for a per-class target. Intra-transcriber floor labelled a **lower bound**; buy 8 h of a second
    keyer to validate it once.
14. **Escalation must name a different resource class than the one that failed** — paid hours, a better
    scan, an outside palaeographer, or **scope reduction in coverage, never in fidelity.** Pre-register
    **N=3 rungs and an hour ceiling per rung.**
15. **Blocking gate on ensemble independence**: mean N_eff ≥ 3.5 on GOLD-TEXT, else the ensemble does not
    adjudicate at all.

**Recognition**
16. `ſ f æ ﬀ ﬁ ﬂ ﬃ ﬄ ã ẽ ĩ õ ũ` **all stay in the codec as atomic NFC entries.** Compose/decompose **only
    at output serialisation.** Pin **NFC** at both ends.
17. **Pair CNNs on the crop, no hand features, three-way output `A/B/indeterminate`** abstaining into
    `<unclear>`; **report the abstention rate as a headline number.** Drop CC and advance width as decision
    features.
18. **Cluster `ſ`-candidates per fount per exemplar, unsupervised; key ~50 exemplars; propagate** —
    letterpress repeats the same physical sort, and this is the one asymmetry the medium offers.
19. **Text-side mining**: closed orthographic contexts (`ffi|ffl|st|fi|fl|ff`) → forced alignment over
    fold-equivalent letters → crop window → key ~200/class. **Declare and bound the recall bias with a
    random 100-line sample.** Store mined instances as **lines**, not crops. Seed `ſ`/`f` from §7's
    200-verse provenance audit instead.
20. **Oversampling ≤3–8× line replication**; above that, **per-class CTC loss weighting (∝1/√freq, cap
    ~10)**. Add **synthetic line rendering from the fount** and **decode-time logit prior scaling**.
    **Monitors at every checkpoint**: rare-class precision *and the frequent neighbour's FP rate*; ECE;
    **calibrate isotonic on an unweighted held-out set.**
21. **Grayscale native primary throughout**; 1-bit masks are a fallback only, trained and scored as their
    own scope; **~0.8 px Gaussian at native resolution before downsampling**, applied identically at train
    and inference. **x-height normalisation, not line-box height.** Note the JBIG2 test measures
    substitution — **the binarisation gap exists even at zero substitution.**
22. **FOUNT replaces TOME** as the third scope level; **stratify held-out splits by gathering.** State the
    H sweep honestly: **only H=120 warm-starts from CATMuS**; the joint move is a height-only `Mp2,1`
    stage; **5 configs × 3 seeds = 15 runs ≈ 120–200 GPU-hours**, ranked on a 5k-line subset, decided on
    `ſ`/`f` + macron per-class F1 with a paired bootstrap.
23. **Cluster bootstrap over pages, not Wilson.** Add **line-segmentation error** and **WER**. Add
    **per-class error stratified by source × fount × neighbour-context, max-over-strata reported**, and a
    **run-length statistic** — otherwise systematic attested substitution passes the entire suite.
    **Attested-form rate demoted to a diagnostic, never a gate.**
24. **Style as a stand-off rendition layer**: plain grapheme channel with a stable character index + a
    parallel `{start, end, rend}` span table (TEI `<span>`/`@spanTo`); **separate font classifier over the
    line image; two-channel scoring, never folded into CER.** The same layer carries turned and wrong-fount
    marking via `<sic>`/`@rend`. Add note-reference marks (`* † ‡ ¶`, superscript letters), terminal `ij`,
    Greek/Hebrew sorts, braces and rules, `ſſ ſi ſl`.

**Cut**
25. Pseudo-archaic R4 as a pipeline component (survives only as a separately-named, non-citable
    reconstruction layer) · six-way variant graph / POA · isotonic calibration, LLR, Henikoff, effective-N ·
    drift guard · ensemble diversity · G2+ · §2.3's coverage interval · most of §9.2 (keep `<pb>`/signature
    milestones, `unclear`/`gap`, and the single intervention-record schema).
26. **Resolve or delete arXiv:2607.00596 this week** — a gate depends on it.
27. **Inspect the scans** for blackletter headings, `ꝛ`, and Latin per/pro brevigraphs. One task, closes
    three inventory questions.

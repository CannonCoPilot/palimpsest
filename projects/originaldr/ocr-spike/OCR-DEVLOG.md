# OriginalDR — Development Log

What was actually built, measured, and decided, in order, with the evidence. The plan states what must be
true and the roadmap states what will be built; **this file records what happened**, including the things
that turned out wrong.

A retraction here is not an embarrassment to be minimised — it is the most useful kind of entry, because
every one of them marks a place where a plausible reading survived until something measured it. They are
kept in full, with what produced them.

---

## 2026-08-28 — R14.14: the frame is rotated, and the reason I filed it was wrong

**`witness/build_skew_record.py` · `witness/score_skew_frame.py`.** The agent now has an angle.
**R14.14 stays OPEN**, and the most useful thing it produced is a refutation of its own premise.

### What was true

The tilt is real and it is per-leaf: **-0.901° to +1.636°** over leaves 400-419, median +0.131°,
with |angle| > 0.8° on nine of twenty. **A single corpus angle could not describe this window.** It
is fitted through the bottom edges of each row's glyph components, and it is deliberately NOT the
fount record's `slant_mode` — that quantity is *glyph* lean, quantised to whole degrees, and reads
**0.00 on every leaf here**. Read as skew it would report these pages as square.

The frame is now expressed in rotated coordinates through a single function, `ry()`, with the head
and foot lines taken as extremes of *rotated* y so they run parallel to the type. Nine vertical
tests were rewired through it. **GOLD-HEADBAND is exactly unchanged** — 115/121, MN 16/19, RH 20/20,
MT 77/80 — as are GOLD-FOREEDGE (40/42) and GOLD-PAGENUMBER (14/20). The rotation is **label-neutral**,
which is evidence it breaks nothing and is *not* evidence it helps.

### 🔴 What was false — and it was my own stated cause

I filed R14.14 because *"the horizontal head line cuts through 41 boxes"* and attributed the cutting
to the missing angle. **Tested by building it:**

| | |
|---|---|
| head-line straddles, unrotated | 41 |
| head-line straddles, **rotated** | **50** — the wrong way |
| corr(\|skew\|, straddles) over 20 leaves | **+0.051** |
| nearly-flat leaves (\|skew\|<0.3) | mean **2.50** straddles |
| tilted leaves (\|skew\|>0.8) | mean **2.44** straddles |

**Flat leaves are cut as often as tilted ones.** The head line is the extreme edge of the *body
block*, and page furniture sits at overlapping heights, so any scalar boundary between them is
straddled whatever its angle. **Those 41 boxes belong to R14.12, the lamination — they need
ownership of ink, not trigonometry.**

The acceptance clause `straddles 41 → 0` is **retired as unreachable by this step**, not quietly
reinterpreted into something the step happens to satisfy. A second clause — *"the estimated angle
correlates with the independently measured row tilt"* — was **circular**: the estimator *is* the row
tilt, so it could only ever return 1.0.

### What the tilt does cost, and why no number here shows it

Surya's boxes are axis-aligned, so a rectangle around a tilted line is taller than its type by
`width · tan θ`. Measured: **17% of a median box height on leaf 409**, 16% on 419, 0% on 406.

That is a **boundary** error under Gate 9.3, and **every gold this project holds scores labels**.
Which is exactly how S2 can be *exactly* unchanged while a real defect sits in the output — the same
shape as MainText-is-containment, one axis over.

⚠️ The full verification suite was **not** re-run after this landed. The standard's parse-and-enrol
checks pass and both commands are registered; the end-to-end run is outstanding.

---

## 2026-08-27h — Sir's review: the agent has 5 deciding constants and 99 overlapping boxes

Suite green at **56 commands, exit 0**. Three steps filed: **R14.11 · R14.12 · R14.13**.
Ceilings **19/93** (denominator +3, numerator +3 — both axes moved together).

### "Why exactly 20?" — because the test has no negative case

The page-number candidate test admitted 20 boxes over 20 leaves: **exactly one per leaf, on every
leaf.** That is not a pool being filtered — it is a test that selects *the* smallest extreme box in
each head band, and on this window that box always happens to be the page number.

🔴 **So the test never once had the opportunity to say "there is no page number here."** Every leaf
in the window prints one, so the window contains **no negative case at all**, and B2's zero false
positives is measuring an absence of opportunity rather than a discrimination. This sharpens the
2026-08-27g retraction: the read was not asked to reject a note, and neither was the geometry.

### The agent's central claim about itself is false, and it is now measured

`witness/audit_fixed_measures.py` sweeps every fixed number in the agent and reports the band over
which the **full label vector** — every box on every leaf — is unchanged.

| constant | shipped | invariant band | slack | verdict |
|---|---|---|---|---|
| `CENTRED_LO/HI` | 0.20 | 0.2000 … 0.2000 | **0.00×** | 🔴 **DECIDING** |
| `FOOT_CATCHWORD_REL` | 0.60 | 0.60 … 0.62 | 0.03× | 🔴 DECIDING |
| `OUTSIDE_FRAC` | 0.55 | 0.55 … 0.57 | 0.04× | 🔴 DECIDING |
| `THIN_MARGIN` | 0.08 | 0.080 … 0.085 | 0.06× | 🔴 DECIDING |
| `PN_MAX_AREA` | 0.0016 | 0.0014 … 0.0018 | 0.25× | 🔴 DECIDING |
| `AR_MEASURE_SPAN` | 0.60 | 0.05 … 0.89 | 1.40× | GUARD |
| `PN_EDGE` · `HEADING_LO/HI` · `COLUMN_OVERLAP` · `AR_ITALIC_MAJORITY` · `AR_MIN_SEGMENTS` · `SMALL_AREA` | | | 0.70–1.48× | GUARD |

**Five of twelve DECIDE.** Masterplan §3.0 permits a fitted constant to initialise or clamp and
forbids it to decide; `visual_agent.py`'s docstring asserts *"nothing here is a corpus-fitted
number"*. **The assertion was never tested until now and it does not hold.**

⚠️ **`CENTRED_LO/HI` at ZERO slack is the sharpest.** It is the band separating a RUNNING HEAD
(centred on the measure) from a head-band NOTE (pushed to a side) — the cue that recovered 14 of 19
marginal notes and is quoted throughout the roadmap. Move it one sweep step either way and the label
vector changes. **The most load-bearing cue in the head band sits exactly on a cliff edge**, and the
derivation was available all along: judge centredness against *this leaf's own* distribution of
head-band box centres, not a fixed fraction of the measure.

⚠️ **Four literals had to be NAMED before the audit was possible at all.** `COLUMN_OVERLAP`,
`CENTRED_LO/HI`, `HEADING_LO/HI` and `FOOT_CATCHWORD_REL` were spelled inline inside the cues that
used them. **An unnamed literal cannot be audited** — no instrument can sweep it and no reader can
find it. Naming them changed no score (115/121 held exactly).

### 99 overlapping box pairs — the layering problem, measured

Rendering all 20 gold leaves with every box produced a census: **158 boxes, 99 pairs physically
overlapping, every leaf affected**, worst at leaf 417 with 12 pairs on 15 boxes.

The codebase has paid for this three times and patched it locally each time — two rival binding
rules computed and both reported; fount evidence assigned to the smallest containing box; the
foot-band cue needing a second signal because the body block swallows the signature. **Three
symptoms of one missing concept**, now filed as **R14.12, the lamination**: regions carry a z-order,
a region owns the ink no higher region claims, and no region may contain ink lying inside another at
the same or higher level. ⚠️ The invariant is over **ink, never rectangles** — two boxes may overlap
in white space, because a page is not tiled by its type.

**Its acceptance includes the test that would prove the concept was the missing one: under a
lamination the two rival binding rules must COLLAPSE TO ONE and agree on every gold entry.**

### And the plates found a defect no number reports

Leaf 417's annotation block is boxed as `MT` (MainText). MainText is containment, so it **scores as
correct** against every gold this project holds. That is R14.10c's data loss, visible at a glance
and invisible to every instrument — found by looking, not by measuring.

### A parser trap, recorded

The three new rows were first written as `| **R14.11** |`. `audit_prereq_ceilings.own_rows` matches
a pipe then a **bare** step id, so all three read as INHERITED and the numerator held at 16 while
three properly classed rows sat in the document. **A declaration the instrument cannot parse is
indistinguishable from one nobody made.**

---

## 2026-08-27f — R14.10b: the page number, and twenty misfilings that cost nothing

**`witness/build_reading_record.py` · `witness/score_pagenumber_agent.py` · GOLD-PAGENUMBER.**
Suite green at **55 commands, exit 0**. `PN` is **adopted**; **R14.10b stays OPEN** on one box.

### The defect was 20 of 20, and every one of them was free

Every page number on leaves 400-419 was misfiled — **15 as `MN`, 4 as `MT`, 1 abstention**. What
makes it the sharpest instance of this project's signature defect is not the count but the
**silence**: scoring here is gold-entry-driven (`visual_agent._bind` walks the gold and binds each
entry to a box), and **no gold entry binds to any page-number box**. So `MN` **recall** — the
agent's headline bar — *cannot fall* when the agent invents marginal notes, and `MT` is containment,
so those four scored as **correct**. The agent was manufacturing roughly three-quarters of a note per
leaf at zero cost, and **no instrument in this project had ever measured `MN` precision.**

### 2026-08-27g — RETRACTION: I measured one statistic and called it "position"

**Sir asked whether the overlap was real or an artefact of poorly configured box mechanics. Neither,
and the question was the right one to ask.**

The overlap is **real** — the boxes are tight, correctly placed, and page numbers genuinely swap
sides with verso/recto alternation, so the box CENTRE of a page number lands where a side-note's
centre lands. Leaves 405 and 412 show it plainly: on 405 the page number is right and the note is
left, on 412 the reverse.

🔴 **But I generalised that single statistic into "position cannot separate them", and that is
false.** Measured over all **65** head-band boxes in the window:

| statistic | page numbers | everything else | verdict |
|---|---|---|---|
| **width** | 0.0442-0.0546 | 0.0757-0.3028 | ✅ **SEPARATES** — empty band **2.0×** the PN spread |
| **area** | 0.0008-0.0012 | 0.0018-0.0095 | ✅ SEPARATES — 1.5× |
| **aspect** | 2.01-2.73 | 3.17-10.25 | ✅ SEPARATES |
| centre (`rel_h`) | 0.000-0.995 | -0.055-1.072 | 🔴 OVERLAP — 36 inside |
| `out_frac` | 0.000-0.497 | 0.000-1.000 | 🔴 OVERLAP — 36 inside |
| `height` | 0.0179-0.0232 | 0.0213-0.0314 | 🔴 OVERLAP — 21 inside |

🔴 **And the counterfactual is worse than the correction.** The geometric test I used merely to
ROUTE candidates admits exactly 20 boxes and all 20 are page numbers — 0 notes. So **geometry alone
scores 20/20 with 0 false positives, where the confirming read scores 14/20 plus 5 abstentions and
1 `MN`. The read MEASURABLY DEGRADES the result here**, and B2's clean zero is not evidence that it
discriminates: it was never once asked to reject a note.

⚠️ **The reading of the page I walked past.** A page number is not distinguished from a side-note by
WHERE it sits but by being a **short, squat object** — two or three sorts against a phrase. That is
a fact about what the book *sets*, of exactly the kind R14.10a used for the ARGUMENT, and I missed it
because I had already decided the answer was a read. **Same failure mode as the one this step
otherwise documents well: a bounded search — here bounded to the statistic I had chosen.**

➡️ **Where the read still earns a place, pre-registered.** Width runs ~0.0165 of the page per digit,
so a **four-digit** page number measures ~0.059-0.073 against a note floor of 0.0757: the empty band
shrinks to almost nothing later in the volume. The defensible design is therefore the **inverse** of
the one shipped — **width is the cue, the read is the CHECK on a margin known to close**. Not
rewired here: the failing box is now known, so the redesign must be pre-registered with its own
out-of-sample test before it runs.

---

### Position cannot name this class, and that is why R13.1 exists

The roadmap filed `PN` as *"a head-band box at the extreme fore-edge, beyond where a note sits"*.
**Refuted.** Page numbers run **0.000-0.043** and **0.812-0.972** of the measure; head-band notes run
**0.010-0.110** and **0.857-1.072**. They **overlap on both sides** — R2.2o.1's shape applied to a
class instead of a gap. What separates them is that one says `380` and the other says
`Sacrifices for`, so `PN` is the first class in this agent **decided by a read**, and the concrete
argument for R13.1 that the row promised it would be.

### A false absence of my own, caught by a gold built for another step

The first run reported *"4 of 20 leaves carry no page-number box"* and filed it as a **detector**
gap. **There is no detector gap.** My candidate test was bounded by `mass_y <= head_y`, and on leaves
401, 402, 409 and 417 the number sits **~0.005 of a page below** a head line that the **body block**
defines. All four were silently `MT`. **GOLD-FOREEDGE** — not band-limited, built for R14.8 — carries
a `PN` entry on two of them, and that is what caught it.

⚠️ **A bounded search returns "not found" in exactly the shape an exhaustive one does.** This is the
**third** recorded instance here (`audit_label_sources.py` bounded by a directory, then by a field
name, now a **band**) — and filing the repair turned up a **fourth**, in the checker itself:
`test_verification_standard.py`'s guard inventory is the glob `test_*.py`, so it **cannot notice a
new scorer**. Both new scripts were added and it reported no gap. Filed as **R11.2f**, not fixed
inline — changing that parser changes the instrument every other number in the block is verified by.

### The result, and the one criterion that fails

| | criterion | result |
|---|---|---|
| B1 | `PN` named on ≥ 12 leaves | ✅ **14/20** |
| B2 | zero `PN` on a non-page-number | ✅ **0** |
| B3 | GOLD-HEADBAND exactly unchanged | ✅ 115/121 · MN 16/19 · RH 20/20 · MT 77/80 |
| B4 | withheld-record negative | ✅ **0/20** fire |
| B5 | spurious `MN` → 0 | 🔴 **1/20** — leaf 403 reads `37T` |

Out-of-sample, unbuilt for this step: **GOLD-FOREEDGE `PN` 2/2**, that gold **38/42 → 40/42**.

**B5 is not relaxed.** One misread sort turns a numeral into a "lettered reading" and the
pre-registered rule routes it to the note logic. Widening the predicate to *predominantly digits*
would be a rule edited after seeing which box it fails on, so the step stays open.

### The read is a measured limit, and three redesigns were refuted

`dr_v3_armB` returns the **exact** printed number on **4 of 16** crops and **empty on 5**. Tried and
refuted: more padding and 3× upscaling → **0/16**; a tighter crop, predicted from kraken's
line-height normalisation → **worse** (6/16 against 10/16 at the shipped padding); matching the
model's declared **`bbox`** segmentation type, which kraken warns about on *every read this project
makes* → **0/16**. That last one is worth keeping: it confirms the existing baseline path is correct
and leaves **R2.1b's numbers intact**.

⚠️ This **corroborates** R2.1b rather than contradicting it — all five candidates collapse on the
direction line (`SG` 0.47-0.75, `CW` 0.53-0.80), and a page number is an object of that scale.
**R14.10b is the first consumer to hit that collapse in production**, which turns a per-class caveat
into a blocking limit. That is an **ALERT on the approach**, never a licence to move the bar.

---


## Session 17 — 2026-08-17 — the sizing unit changes; three verified findings; a guard that checks the wrong field

> ⚠️ **THIS FILE HAS A HOLE AT 2026-08-12 → 2026-08-15 AND THIS ENTRY DOES NOT FILL IT.** R2.1f firing,
> R9.6/R9.6a, R11.1–R11.4 and R11.3a all landed in that window and **none of them has a session entry**, though
> the roadmap carries them. This entry records only what was verified on 2026-08-17, because writing up
> sessions one did not witness is how a log stops being evidence. **The gap is owed an entry from the
> transcripts.**

**SIZING IS NO LONGER DENOMINATED IN HOURS (Sir, standing instruction).** Work is described by **how complex
it is to solve correctly** — what must be designed, what is unknown, how many parts interact, what would
invalidate the approach — never by elapsed time, whether a person's or a script's. Nothing about escalation
changes: a ceiling still **ALERTS that the approach needs redesign**, still never closes a step, and a
below-bar result still stays OPEN and blocking (§0.5). Only the unit changes.

> 🔴 **AND IT HAS A CODE COUPLING NOBODY WOULD SEE UNTIL IT SILENTLY BROKE.**
> `witness/audit_prereq_ceilings.py` finds ceilings by matching the **literal string** `hour ceiling`
> (`CEILING_RE = re.compile(r"hour ceiling", re.I)`) against `OCR-ROADMAP.md`. Rewrite the roadmap's ceilings
> into complexity language without touching that regex and the audit finds **zero** ceilings, reports every
> OPEN step as uncovered, and the §0.5 coverage fraction collapses to `0/44` — **a total regression in the
> report, from a change that regressed nothing.** The parser must move with the vocabulary, in the same act.
> *A grep is a contract between a document and a program, and nothing declares it.*

**Three findings, each verified rather than read.**

1. **The ſ-faithful recognizer is still absent from the attesting path.** `grep` over `gen1_*.py`,
   `s_arbiter.py` and `chapter_campaign.py` returns nothing for `reichenau_dr` or `dr_v3_armA`. The claim was
   first made 2026-07-31; it is unchanged more than a fortnight later, while ~1,100 board cells sit at
   `CONTENT OK, ſ-SURFACE OPEN` waiting on precisely that arm. **Re-verifying an old claim is not redundant
   work** — it converted "recorded once" into "still true", which is what makes it actionable.

2. **`models/` holds five trained recognizers, and the campaign cites the third-best number.** `dr_v3_armA`
   0.9739 · `dr_v3_armB` 0.9694 · `reichenau_dr` 0.9396 (the cited one) · `dr_armA` 0.9349 ·
   `reichenau_dr_ho` 0.9230. ⚠️ **Comparability is UNKNOWN** — these are per-arm validation figures and
   nothing establishes a shared split, so the column is *not* a ranking and licenses no swap. **R2.1b exists
   to settle it** on one fixed hand-keyed token set. Recorded here because "a better model exists" and "a
   better model has been measured" are different claims and only the first is currently supported.

3. **R9.5a's acceptance is not met, and a second role disagreement is live.** The acceptance read *"extend
   `test_counts_vs_doc.py` to parse the companions' witness tables and compare **role-by-role** against the
   registry."* The guard compares **leaf counts and primary raster**, not roles, and reads the plan's §1.1
   table rather than the companions'. It prints twelve `ok` and exits 0 — while `witnesses.py` files
   **`NT-1633-F` as `role=lowres`** and `OCR-OVERVIEW.md` gives it **witness support**, in its table *and* its
   prose. **On the merits the document is right and the registry is wrong**: the registry's own criterion for
   `lowres`, stated in its `NT-M` comment, is *same setting as the base exemplar*, and `F`'s New Testament is
   1633 — a different setting, which is `support` by definition, the role `R` holds on identical grounds. As
   `lowres` it is entitled to *"any reading no better-resolved witness carries"* for the **1582** setting,
   which is the cross-setting supply §1.1c forbids; the exposure is masked only because the cross-setting
   guard refuses on the identifier. **The Overview was deliberately NOT edited to match the registry** — that
   would have propagated the error into the document that was right. Raised for a roadmap step: correct the
   registry, and extend the guard to roles.
   > **This is R9.5a one turn on.** There, prose was right and the table wrong. Here, prose *and* table are
   > right and the **registry** is wrong. The constant across both is that **no machine ever compared them**,
   > and R9.5a was closed on a guard that does not check the field that was wrong. *A fix verified by a guard
   > that cannot see the defect is verified by nothing.*

**A term disambiguated, because it means two different things in one directory.** `R2`/`R3` name the
**recognition rungs** in `CAMPAIGN-STATUS.md` and `WALKTHROUGH-PROTOCOL.md`, and the **roadmap steps**
(Gate 0b stage 2, Gate 0c) in this file and the Master Plan. Both usages were live and unmarked; both files
now say which they mean at the point of use.

**Recovered from Session 16, and it matters now.** That session's surviving candidate was
**signature-sequence monotonicity** — *"reads only signatures, no gold set needed"* — and it was set aside
when catchword continuity was adopted. Gate 0b's collation is being rebuilt on **several independent
signals** rather than one, so that candidate is live again rather than superseded. Session 16's standing
rule governs every one of them: **no R2 metric is adopted without a negative control.** The 0.95 bar is
unchanged; what was wrong was expecting a single instrument to carry the whole collation.

---

## Session 16 — 2026-08-11 — R2 STARTED; R2.1's acceptance criterion refuted; two metrics measured and rejected

**R2 is no longer "nothing built".** Instrument in `.scratch/r2/` (probes v1–v18). Design of record
`probe_v18.py`: bound below the last full text line -> connected components (never a row profile) ->
tokens -> recognise each token -> **then** one accept-test on the tokens that read.

**Doc defects found and fixed (Focus-Section review).**
* MP §0.5 and the roadmap register both named `witness/test_prereq_ceilings.py` — **a file that has never
  existed** — and called it a guard that "fails". The real instrument is `audit_prereq_ceilings.py`, which
  R10.1 argues must be an **audit, not a guard**. Both documents corrected.
* Roadmap R10's status line read "OPEN. Nothing built." while its own R10.1 row described a working audit
  and the verification block ran it. Corrected to **PART** (R10.1 built, R10.2 open).
* `audit_s06_keys` prints **261**; four places said 262. Corrected.
* Walkthrough described Gate 0d in the future tense ("is to be asserted") after R5.1/R5.2a–c landed —
  stale in the *understating* direction, which invites rebuilding a guard that exists.
* §0.5 ceiling coverage **rose 6/35 -> 12/41 (17% -> 29%)** because R2.1a–f were written as ceilinged
  sub-steps. Recorded: the fraction rises when work is **planned** under a ceiling, not when it is
  completed — and is therefore a coverage number that must never be read as progress.

**R2.1's acceptance criterion was unsatisfiable by construction.** It required ">=95% of rectos yield a
parsed signature". Measured over leaves 400–431 consecutive: signatures print on **7 of 16 rectos (44%)**,
all at odd leaf index; catchwords print on **every** leaf, both parities. A criterion that cannot separate
"the leaf prints no signature" from "the reader missed it" is not a test. Parity is now **measured**
(odd = recto for this witness) rather than assumed — R2.1a done.

**Two replacement metrics built and refuted the same day.**
1. Catchword continuity as TEXT: reading the next leaf's first word is **body text**, so it makes R2 wait
   on the recogniser — which R2's own sequencing note forbids. Measured 4/18 = 0.222, but the failures are
   recogniser errors (`'hoode'` for `ſtoode`), not discontinuities. **PROVISIONAL, not a collation fact.**
2. Catchword continuity by IMAGE correlation, with a mandatory negative control: matches **+0.264** vs
   controls **+0.247** (control max +0.631). **No separation.** §1.4's +0.424-vs-0.036 precedent did not
   transfer because it registered a whole page block; a catchword is 4–8 glyphs. *A method's separation is
   a property of the evidence it was demonstrated on, not of the method.* Without the control this run
   would have reported "continuity confirmed" and pushed a false collation into Gate 0b.

**Surviving candidate: signature-sequence monotonicity** (reads only signatures, no gold set needed).
~4h of R2's 12h ceiling spent, no metric cleared; the pre-registered rule is live and its named fallback
*method* — hand-reading a stratified sample — is now the likely route for the catchword half.

**Standing rule adopted:** no R2 metric is adopted without a negative control.

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

---

## Session 11 — the audit was measuring four of five criteria, and the routing table was still routing

Two defects, both of which had been *documented* and neither of which had been *closed*. That is the theme of
the session: a finding is not a fix, and the thing that turns one into the other is a test.

### The plan and the roadmap had drifted from the code, in six places

An audit of §0–§2 and R0–R8 before doing any work, and it was worth the time:

| what it said | what was true |
|---|---|
| R0.1 acceptance: "all **10 files**" | **11 files**, carrying 12 witness records |
| R0.2 acceptance: "leaf counts match registry (**10/10**)" | **12/12** |
| Roadmap "Verification standard": `make_witness_tree.py -> 10/10 verified`, and **none of the four guards listed** | 12/12; five guards and an audit exist |
| §2 "Resolved": "witness independence for all **eleven files**" | the claim §1.1c **overturned** for `NT-F` |
| §2 Gate 0a **(iii)**: listed as *outstanding and blocking* | **R4.3 discharged it** — the source is `M`, on +0.424/+0.398 |
| Roadmap R4.1: "BLOCKED EXTERNALLY … the digit unresolved" | resolved from BPL's own MARC in Session 9, written **only into the exec summary** |

The last one has a moral worth keeping: R4.1 sat blocked because the block was **mis-scoped**. It was a true
statement about *the ESTC search interface* and it was allowed to stand for *"the bibliographic numbers are
unobtainable"* — while the numbers sat in an Internet Archive metadata field already downloaded for other
purposes. **An external blocker names one route; it does not bound the space of routes.**

Re-fetching those citation strings to write them in caught a smaller thing that is the same shape: the row
was labelled **verbatim** and the working-notes transcription had normalised the punctuation and abbreviated
two of five citations. Nothing downstream depends on a comma, but *"verbatim"* is a claim that a later reader
need not re-fetch, and that claim was false. **Fetch, don't recall.**

Fixed, plus a **status index** and an **open-items register** at the head of the roadmap — the file's sections
run R0, R1, R2, R3, R4, R6, R3.5, R5, R7, R8, and renumbering was rejected because the ids are cited from
four guards, the masterplan, the companions and every devlog entry. The ids are load-bearing; the ordering is
not.

**And a guard so this class cannot recur: `test_verification_standard.py`** parses the roadmap's own command
block and fails if a command named there is missing, if an `N/M` claim disagrees with what the command
prints, if a guard on disk is undocumented, or if the section is renamed away. `test_counts_vs_doc.py` already
bound the masterplan's §1.1 table to the registry; nothing bound the roadmap to anything, which is exactly how
"10/10" survived the corpus growing.

### R8.4a — the setting audit was reading four of the constitution's five criteria

§0.3 defines setting identity as *"same signature, same catchword, same line-end words."* The R8.4 audit read
**printed page number, running head, sidehead and line breaks**. Line-end words it compared; **signature and
catchword it never looked at** — both sit at the **foot** of the leaf and `verify_setting.py` cropped the top
16%. So the audit was *stronger* than the constitution on an axis the constitution omitted, and **silently
weaker on two it named**, and neither document said so.

No verdict was wrong. But "the method deviates from the constitution and nobody noticed" is the shape of the
four-month error, not a lesser thing, so **the instrument was raised to the constitution** rather than the
criterion trimmed to the instrument. All four settings hold on the foot criteria too:

| setting | page | signature | catchword |
|---|---|---|---|
| NT 1582 | 149 | `T iij` — `B`, `M`, `X` | `bes` |
| NT 1633 | 147 | *verso, none* | `CHAP.` — `F`, `R` |
| OT1 1609 | 223 | *verso, none* | `wil` — `B`, `P`, `F` |
| OT2 1610 | 243 | `Gg2` — `B`, `P`, `F` | `† Let` |

The catchword completes the caught-up word every time — `Scri-`/`bes`, `virgins father`/`wil` — which is a
check on the reading as well as on the setting.

**The negative control is the result that matters.** At printed page **147** the two NT settings share the
page number *and* the running head *ACCORDING TO S. LVKE*, and separate completely at the foot: `B` has
signature `T ij` and catchword `30. Paſſing` (Luke 4:31), against `F`/`R`'s `CHAP.` (Luke 7:44). **The
criteria a head crop can see agree across the setting boundary; the two it cannot see separate it.** That is
the entire case for having closed the gap rather than explaining it away.

**The band cost four failed designs, and every one failed the same way — it showed blank paper or the wrong
glyphs, and both read as findings:**

1. A **fixed foot fraction** — bottom margins differ per witness, and the fraction that reaches the catchword
   is 0.10 on `P`, over 0.18 on `B`, over 0.22 on `R`. One constant shows blank paper for some witnesses, and
   blank paper reads as *"this leaf has no catchword."* Same shape as the absolute ink thresholds that made
   `F` report zero blank leaves (R1.4).
2. **Anchoring on the last ink** — `OT1-1609-B`'s dog-eared corner, `OT2-1610-F`'s 183-row black edge band and
   `F`'s `fatimamovement.com` watermark all present as the last inked thing on the leaf.
3. A **threshold tuned on full text lines** prunes the catchword, which is a *short* line: at 20% of peak the
   anchor found the last text line and the signature `T iij` was clipped at the crop edge.
4. **Pitch measured as the white gap** rather than start-to-start understates it threefold, so a
   five-pitch rule pruned the catchword along with the watermark.

The working design anchors on the last **regularly spaced** line of type (artefacts are not regular), samples
**right of centre** (the watermark is lower-left, catchwords are right of centre), then extends the band five
of the leaf's **own** line pitches below. The catchword is *guaranteed in view* rather than *located*, and a
person reads it. **The instrument's job is to put the right pixels in front of a reader, not to adjudicate
them** — R7.4's lesson arriving from a different direction.

Stated as a limit, because it is one: the foot criteria are verified at **one matched page per setting**, not
the three or more the head pass used. That is **R8.4b**, and until it is done they corroborate the head result
at one point rather than independently verifying it.

**NEW Gate 0e — setting identity, proved per witness.** §2 listed gates for bibliography, completeness, the
leaf map and derivative contamination, and **nothing for setting** — the exact failure that cost four months
had no gate in the section that exists to prevent such failures. Gates 0a–0d each guard a field *known* to be
uncertain. This one guards the field that was **not** known to be uncertain, which is the only kind that costs
months.

### R7.5 — the routing table that sent 48 transcriptions to the wrong image was still routing

`jp2_page.py` held `OCR_DIR_TO_JP2`, a hand-written identifier → raster-directory table. `witnesses.py` held
`pixel_source()` to refuse renders and composites. **The table never called the guard.** Both routes worked;
one of them refused nothing. Commit `c44ba20` had *verified* that this table was the mechanism behind 48 of 51
inadmissible ground-truth readings — and it was still the live routing when this session opened.
**Verifying a defect is not retiring it.**

The table is **deleted, not corrected**: a second mapping is the defect, because a mapping that is right today
is unguarded tomorrow. An identifier now resolves to a *witness*, and the witness resolves its own raster.

Four things a plain deletion would have got wrong:

- **`M` needed re-routing, not un-routing.** Its JP2 package is genuinely corrupt and its PDF holds the real
  CCITT stencils — the PDF *is* its primary artefact. Deleting the entry would have left `M` with no pixel
  route, which reads as *"this witness has no rasters"*, and `M` holds the only genuine 1582 Censure and
  Preface leaves in the corpus. New `witnesses.glyph_source()` returns `("pdf", …)` for it and extraction is
  **per leaf, on demand**: its PDF is 2,872 pages, and a guarded route slow enough to be skipped is a guarded
  route nobody uses.
- **`glyph_source()` is not `pixel_source()`.** The latter answers a narrower question — *is this witness's
  JP2 package the capture, or an IA render?* — and therefore refuses `M`, whose JP2 is neither. Both are kept
  because they answer two different questions.
- **The bar list had to move.** `BARRED` lived in `audit_gt_rasters.py`; it is now `witnesses.GLYPH_BARRED`
  beside the registry, and the audit imports it. Two copies of *which witnesses are barred* is R7.5 one level
  up, and the new test fails if a second definition appears anywhere in the tree.
- **`jp2-S06` names a file, not a witness**, and it is on **113,514 records**. `S06` is one volume carrying
  the 1635 Rouen OT *and* the 1582 Rheims NT — two settings 53 years apart — so resolving it to either is a
  guess of precisely the kind that cost four months. It now **raises** and names the two well-formed ids
  (R7.5a).

`jp2-S04` now resolves to `newtestamentofie00engl_jp2`, the acquired Princeton original, where the table
pointed at the **retired MRC composite**. Both paths existed on disk, so nothing had ever failed.

The verified `jp2-S09ot2 = −1` offset is carried across and **asserted by the test**: losing it in a refactor
silently returns the next leaf for every page of S9's entire Old Testament volume 2.

**The default is strict.** `jp2_path()` takes the guarded route unless the caller passes `structure=True`.
About twenty modules call this API and they split between legitimate structural use — page order and counts,
admissible for every witness because a render preserves page order — and pixel use. They are deliberately
**not** silently patched: the strict default makes each one fail loudly and declare which it is (R7.5b). The
previous behaviour was silent success on the wrong pixels, and the only honest replacement for silent success
is a loud failure.

### The most useful thing in the session was a hole in my own guard

The first `test_raster_routing.py` checked that whatever was barred refused pixels and whatever was not
resolved cleanly. Injecting a failure to prove it worked, I deleted `F` from the bar list — and the test
**passed**, because un-barring `F` merely moved it from one branch to the other and the test agreed with
whatever it found. **A self-consistent check constrains nothing.**

This is structurally the same error as the original: an independence test that contrasts `F` against `B` can
only ever license *"`F` is not `B`"*, and it was read as *"`F` is an independent 1582 copy."* A test only
constrains what it would reject. It now asserts the bar set is exactly `{F, X}`, so un-barring a witness is a
deliberate edit to a test rather than a silent widening.

**It was found by injection, not by reading the code**, which is the argument for proving negatives rather
than reasoning about them. Every guard touched this session has its negatives proven by injection: four for
R8.4a, four for R8.8, four for R7.5.

**Commits**: `e2df106` (R8.4a + R8.8 + the six doc corrections + Gate 0e), `a20c533` (R7.5).

---

## Session 12 — every caller of the routing table wanted page numbers, and three more copies of it turned up

R7.5 deleted the table. This session updated the six modules that were still reading it, and the answer to
"which route does each of you need?" came back unanimous and unexpected: **all six wanted STRUCTURE.**

`ocr_complete_volume` detects un-OCR'd pages. `integrity_sweep` compares page counts. `tome_map_audit` checks
index alignment. `build_tome_map_v2` addresses book and chapter to leaf. `source_inventory_audit` wanted only
the *set* of known identifiers. `curated_sources` never called it at all — it kept a copy.

Not one of them wanted pixels. The table's entire real use was **page bookkeeping**, and it was answering with
raster *directories*, which is how glyph work reached the wrong image through a door built for counting. The
six now share `jp2_page.structure_leaves()`, which returns the leaves rather than the directory: a caller
holding leaves can count them and cannot open the wrong ones.

### The duplicate count went from one to four, and one of them had already drifted

R7.5 moved `GLYPH_BARRED` because two copies of "which witnesses are barred" would drift. Discharging R7.5b
found three more copies of the same class:

| map | second copy | drifted? |
|---|---|---|
| which witnesses are barred | `audit_gt_rasters.py` | no — caught at R7.5 |
| `ocr_dir` → witness | `audit_gt_rasters.py` | **YES** |
| verified `jp2-S09ot2 = −1` offset | `tome_map_audit.py` | no |
| `ocr_dir` → curated source | `curated_sources.py` | no |

**The drift is the instructive one.** `witnesses.py` refuses `jp2-S06` outright, because S06 is one file
carrying the 1635 Rouen OT and the 1582 Rheims NT and choosing between them is precisely the guess that cost
four months. The GT audit's private copy mapped it to `("OT", "M")` anyway. Both behaviours were live; neither
could see the other, because only one is consulted per call. As it happens the audit's answer is *correct* —
all three files are `matter-ot2-*` at leaves 2049–2070, inside M's OT half — but it was correct **as a
standing guess rather than as a reading**, and the registry's refusal is what makes the difference visible.
It is now recorded as `GT_LEGACY` with the leaf-index evidence written down, and the guard fails if that
extension ever *shadows* an id the registry already resolves rather than merely extending past it.

The general lesson, which is sharper than "duplicates drift": **a duplicate is not dangerous when it drifts.
It is dangerous from the moment it exists, because from then on the agreement between the copies is a
coincidence that nothing is checking.** Three of these four had not drifted, and that fact was worth nothing.

`curated_sources.OCR_DIR_SOURCE` is the tidiest case: it carried the comment *"must stay in sync with
`jp2_page.OCR_DIR_TO_JP2`"*. A map that MUST STAY IN SYNC is R7.5 written down as a note-to-self. It is now
derived from the registry's own `legacy` field, so there is nothing left to keep in sync. One nuance kept
rather than flattened: `jp2-S06` remains **curated as a source** while staying **unaddressable as a volume**.
Dropping it would have made a folder of legitimate material read as BANNED, which is a false accusation, not
a stricter gate. Curation and addressing are two questions and collapsing them weakens one of them.

### R7.5d — the table was deleted and its output kept routing

`tome-map-v2.json`, 4.7 MB, tracked, built by the table on 2026-07-28, still held **all four wrong routes as
literal strings**: `jp2-S04` → the retired MRC composite, the three `archive-*` volumes → `F`'s renders,
`jp2-S06` → the JPEG render. A checked-in JSON full of raster paths is a routing table that no guard sits on,
one indirection further out, and it outlived the code that wrote it by eleven days without anyone noticing —
including me, three times through this file.

It was found by the *guard*, not by reading: the new check greps every tracked JSON for `jp2_dir` / `jp2_file`
and flagged two, the second being one vestigial field in `master-source-list.json` (correct-valued, read by
nothing, removed). **This is the second session running in which the injection/guard found something reading
did not.** The pattern is worth naming: reading a file tells you what the code does; a guard tells you what
the *tree* contains, and stale artefacts are invisible to the first.

The map is deleted rather than corrected, because it cannot be rebuilt until R7.5a re-keys `jp2-S06`, and
**a tome map short by 2,872 leaves looks exactly like a tome map.** `build_tome_map_v2` now builds the ten
volumes it can, then **refuses to write** and exits 1, naming the volume and the page count it could not
place. Skipping the volume would have been a one-line change producing a file that reports "100% of pages
addressed" — a below-threshold result wearing a finished one's clothes, which is the thing the project's
standing rule exists to forbid. `tome_map_audit` takes the same shape from the other side: an unaddressable
volume reports as a DEFECT row with its OCR count intact, so it stays visible and stays in the denominator,
rather than raising (which takes ten good volumes down) or being skipped (which makes "0 defects" mean
nothing).

**A guard is not finished when the code is fixed. It is finished when the artefacts the bad code produced are
gone too.**

Negatives proven by injection, exit 1 each: a revived second `ocr_dir` map; a curated map drifted from the
registry; the GT audit shadowing a registry entry; an artefact re-acquiring a `jp2_dir`; the dropped S09ot2
offset. Restored to exit 0 after each.

---

## Session 12b — R7.5a: the boundary between two settings, read rather than calculated

`jp2-S06` named a FILE: one 2,872-leaf package holding the **1635 Rouen Old Testament** and the **1582
Rheims New Testament**, 53 years and two towns apart. Every record keyed to it named a setting only by
accident of which half it happened to fall in. Splitting it is R7.5a.

### The counts cannot answer the question, and that is the whole difficulty

The registry gives the OT half 2,071 leaves and the NT half 800. The package holds 2,872. **One leaf is
unaccounted for.** Arithmetic tells you a leaf is missing; it cannot tell you which testament it belongs to,
and a plausible-looking answer was available in both directions.

So all three candidates were rendered from `S06.pdf` and read:

| package leaf | printed on it | verdict |
|---|---|---|
| 2070 | `FAVLTS ESCAPED IN THE PRINTING`, and beneath it `EXTRAICT DV PRIVILEGE DV ROY` — to Iean le Cousturier at Rouen, **1634** | last OT leaf |
| 2071 | nothing at all: **0.00% ink** against 4–9% either side | **blank divider, in neither** |
| 2072 | `THE NEVV TESTAMENT OF IESVS CHRIST` … `PRINTED AT RHEMES, by Iohn Fogny. 1582.`, woodcut border | first NT leaf |

2,071 + 1 + 800 = 2,872, exactly. The registry was right all along, and the orphan is a blank sheet between
the testaments. `witnesses.s06_volume()` **raises** for it. Assigning it to whichever side is convenient
would invent a leaf for a setting, and **a leaf in neither setting is a third answer — collapsing a third
answer into a binary is how a boundary moves without anyone deciding to move it.**

The 1634 Rouen privilege on leaf 2070 is a bonus: it independently corroborates that M's OT half is the
1635 Rouen edition, which the registry asserts from the colophon.

### I got it wrong first, and the check is what caught it

My first pass read the OCR file `S06_2071`, found `FAVLTS ESCAPED`, and concluded **the registry drops an OT
leaf**. It does not. The OCR corpus is **1-based** (`S06_0001`…`S06_2872`) and every raster rendering of it
is **0-based**, so OCR page N is package leaf N−1. Had I re-keyed on that reading I would have shifted the
OT/NT boundary by one leaf — mis-assigning the testament of precisely the leaves the split exists to
disambiguate. **The error was in the direction of the thing I was trying to prevent.**

### The off-by-one was real, unrecorded, and older than this session

`JP2_INDEX_OFFSET` had **no entry for `jp2-S06`**, which asserts alignment. It was not aligned. Text and
image disagreed by one leaf on all 2,872 pages, silently — the identical defect `jp2-S09ot2` carries a
verified −1 to prevent. Confirmed at two points ~1,000 leaves apart on content that cannot be mistaken: OCR
`S06_2071` = `FAVLTS ESCAPED` = package 2070; OCR `S06_1029` = `THE SECOND TOME OF THE HOLIE BIBLE` =
package 1028; and OCR `S06_1028` is empty where package 1027 is blank.

The fix does not add two offset entries. The files are **renumbered 0-based and witness-relative**, like
every other volume, so the offset ceases to exist rather than being written down. **An offset that does not
need to exist is one that cannot be dropped in a later refactor.** After the split,
`pixel_path("jp2-S06ot", 2070)` extracts package page 2070 and the OCR text for that index reads `FAVLTS
ESCAPED`; `pixel_path("jp2-S06nt", 0)` extracts package 2072, the NT title page. Text and image agree for
the first time.

### ⚠ A dead metric was tried first and pointed the wrong way

Before rendering anything I correlated per-leaf ink fraction against per-page OCR character count over 400
leaves, expecting the true offset to stand out. It returns **r ≤ 0.13 at every offset from −3 to +3**, and
its argmax is **+1** — the opposite of the truth. On bitonal CCITT with OCR this noisy the metric measures
nothing, and a metric that measures nothing still produces a ranking. It is recorded because the ranking was
there to be believed. *A null from a dead metric is not evidence, and neither is its maximum.*

### Scope, stated rather than blurred

Re-keyed: the OCR corpus (2,071 + 1 held aside + 800), the three ground-truth files, both addressing
artefacts. The divider is **moved aside, not deleted** — it is a real leaf of a real book, and "we dropped
one because it was blank" is a note nobody writes.

**347 derived artefacts (95,548 occurrences) still carry the old id.** They are **R7.5a-2, open and
blocking**, and they will be **regenerated, not edited** — patching a derived file is how a stale artefact
acquires the appearance of a current one, which is R7.5d exactly. `audit_s06_keys.py` exits **2** for a
regression in the authoritative sets and **1** while the backlog stands, so a defect and a backlog can never
be mistaken for each other.

One record was assigned on weaker evidence and says so in its own file: `matter-ot2-table-epistles.json`
carries `page_index: null`, so the leaf-range test that placed the other two could not be run. It is
assigned from its declared raster name and from a Table of Epistles being OT endmatter here — recorded as
weaker, not quietly levelled up.

Negatives proven by injection: the divider given a setting; a ground-truth file reverting to `jp2-S06`
(exit 2, not 1); a half losing a leaf (exit 2).

---

## Session 13 — three limits that were written down correctly and enforced nowhere

**Discharges** §1.1, §1.1a, §2 Gate 0d/0f · roadmap R7.5a-3, **R9**.

> 🔴 **CORRECTION, appended 2026-08-10 — "Gate 0d" in that line is false and is left standing rather
> than edited away.** This session was verse-scope work; it discharged **0f** and touched nothing of
> **0d**, whose guard *had never been written at all*. The devlog is a record of what was believed at
> a moment (Master Plan §0.6) and is not retroactively rewritten — but a false discharge claim is
> exactly how a gate acquires the appearance of coverage, so it is marked here. See Session 14.

Sir's instruction was to restate `M`'s role per half. Doing so required asking what a role *does*, and
the answer was: nothing. **No code has ever read a witness role.** The permissions and limits in §1.1a
have been correct since they were written and have never been on any execution path. Three separate
consequences had accumulated behind that, and each was invisible in a different way.

### 1. One role name carrying two unrelated limits

`M` is one file holding two books. Both halves were filed as *frontmatter witness*, and the two halves
are limited for reasons that have nothing to do with each other:

| | `OT-1635-M` | `NT-1582-M` |
|---|---|---|
| limit | **bibliographic** — 1635 Rouen, a different edition from the 1609/1610 Douai printing | **the raster** — 1-bit CCITT ~380 ppi against `B`-NT's ~545 ppi |
| could a better scan lift it? | **no**, and no scan ever will | **yes** |
| now | frontmatter witness (different edition), `verse_scope: none` | independent witness, low-resolution scan, `verse_scope: collation` |

**This is the `structure only` error repeating** — a limit on one *digitisation* stated as a property of
the *copy* — on a different witness, four rows below the table in §1.1a that records the first
retirement. It cost the New Testament the second copy of its own setting that it has: `NT-1582-M`
localizes **2,344** pilot verses and attests matthew 1,067 · john 877 · apocalypse 400.

### 2. The rule that was enforced by a defect

`witness_inventory` declared `S6: drop_tomes: ["NT"]` and called it a scoring rule. **No scorer read it.**
Its only consumer was `page_address_eval.volume_books()`, which read it as a *containment* claim and built
the addressing DP's state space from it — the R7.5a-3 defect that filed 800 leaves reading `ACCORDING TO
S. IOHN` under Machabees and Daniel at median fit 0.156. While that defect stood, S6's NT could not
localize a verse, so **the drop looked enforced**. Correcting the addressing removed the only thing
enforcing it. Retired at Sir's instruction; its premise had died with Session 9's 1633 finding, which
makes `NT-1582-M` the second witness to a setting the NT holds once rather than a fourth copy of one held
three times.

The re-run afterwards was **deep-equal to the run before it** — 6,434 verses, worklist 271, every figure
identical, differing in bytes only where two sources tie on every value and fall out of a dict in a
different order. That non-difference is the finding: **retiring a rule cannot move a number no scorer
read.**

### 3. `X` was attesting, and every NT agreement figure counted `B` twice

Building the scope table made this visible on its first run. `NT-1582-X` — `B` re-wrapped and upscaled
exactly 2.000×, NCC 0.9847 to `B`'s own grid, top-octave energy 0.0002 against `B`'s own 0.0074–0.0097 —
reaches the coverage audit as `S8` and was attesting **matthew 1,067 · john 876 · apocalypse 391**, beside
`B`'s own `S9` rows for the same books. §1.1a has said since it was written that admitting `X` *"would
double-count `B` under a second name"*. It was being admitted. **Every New Testament cross-source
agreement figure computed before today counted the base exemplar twice, at two scales.** R9.4b is the
remainder: no such figure may stand unlabelled.

### What was built

| built | what it does |
|---|---|
| `witnesses.ROLE_VERSE_SCOPE` + `verse_scope()` / `verse_admitted()` / `assert_verse_admitted()` | **derives** verse-grain permission from the role — `base`/`surrogate` → full · `lowres`/`support` → collation · `frontmatter`/`excluded` → none. A role with no scope **raises at import**, so a role added later cannot default into admission |
| `corpus_localize.load(scope_check=True)` | **raises** `VerseScopeError` for a `none` witness. Returning `{}` was rejected: `{}` is already what a never-localized volume returns, so a silent refusal would be indistinguishable from missing data |
| `qc_audit.scan_ocr_dirs` | drops `none` volumes and **prints what it dropped, above the figures**. A witness excluded on principle must be visible as an exclusion |
| `witness/test_verse_scope.py` | Gate 0f held four ways, including by **calling** the audit's choke point rather than reading it |
| `witness/test_verse_scope_bypass.py` | **exit 1** — nine modules read `.corpus-localize-*.json` directly, around the gate (R9.2c) |
| `witness/test_drop_rule_enforced.py` | a declared scoping rule with no consumer fails |
| §2 **Gate 0d restored** | it was cited twice — *"Gates 0a–0d each guard a field…"* — and defined nowhere, while roadmap R5.2 pointed back at it. A gate that exists only as a cross-reference is not a gate |

### 🔴 The guard passed all three injections, and was worthless

The first `test_verse_scope.py` checked that each witness's scope matched its role. Flipping `OT-1635-M`
from `frontmatter` to `lowres` **passed**: it moved to the other branch of a table that agreed with it
either way, and a 1635 reprint quietly became admissible for 1609 verse text. Flipping `NT-1582-M` back
passed too.

**This is `test_raster_routing.py` from Session 11, repeated with its lesson written down in the same
file I was editing** — that guard passed when `F` was deleted from the bar list, because un-barring merely
moved `F` to the other branch. The remedy was the same then and now: **assert the SET, not the branch.**
The three scope-critical assignments are pinned with their evidence and the verse-inadmissible set is
asserted to be exactly `{OT-1635-M, NT-1582-X}`. All three injections now fail; exit 0 restored.

⚠️ **Recording the near-miss because the guard would have shipped green.** A self-consistent check
produces the *same observable* as a working one, and I had already written the sentence describing that
failure mode twice in this repository before making it a third time.

### And one more copy of a fact, found the same way

`test_verification_standard.py` reported the new bypass audit as broken for exiting 1 — its healthy
state — because it classified audits from a hand-maintained set `{"audit_gt_rasters.py"}` inside the
checker. **The document already says which commands are audits**: they are the ones under *"The audits"*.
The classification now derives from the block, and `audit_s06_keys.py` moved to the block it belonged in.

### Result

`coverage-audit-verse.json` re-run with the gate live. Removed: `psalms/S6`, `genesis/S6`
(`OT-1635-M`); `matthew/S8`, `john/S8`, `apocalypse/S8` (`NT-1582-X`). **Added: none. Changed among
survivors: none — not one attested or passed count moved by one.** Guards **9 exit 0**; audits
`audit_gt_rasters`, `audit_s06_keys`, `test_verse_scope_bypass` exit 1, each with its remedy named.

---

## Session 14 — a gate that three documents described and nobody had written

**Discharges** §0.5, §0.6, §2 Gate 0d (built, not yet complete) · roadmap **R5.1/R5.2a–c**, **R9.4a**,
**R9.4b**, **R9.6** · opens **R9.5a**, **R10**.

Sir's instruction was a review of the Master Plan's Focus Sections (§0–§2) and the roadmap R0–R9,
reporting what remained open. The review found four things open that the documents said were closed,
and the pattern is one this project has now catalogued three times in three different forms.

### The finding: "no proven negative" and "does not exist" are different states

§2's Gate 0d note, roadmap R5, and the Walkthrough all described the derivative-contamination guard
as a guard that **ran and had merely never refused anything**. A search for any bit-depth,
grey-level, `.mode` or dimension assertion across every module returned **nothing**. The only
occurrence of the string `R5.2` in the entire codebase was a comment in `test_setting_verified.py`
asserting that R5.2 is *held to the same standard* — a cross-reference to a guard that did not exist.
Session 13's own header recorded it as **"Discharges … Gate 0d"**.

Three documents, one devlog entry, and a code comment all describing the same absent thing. Nothing
had gone wrong in the prose; the prose simply had nothing under it — **and this is the third instance
in one review**, after Gate 0f (a rule correctly written and read by no code) and §0.5's hour
ceilings (a rule with no step, no test and no consumer). The three failures are distinguishable and
worth keeping apart:

| | the rule | the code | how it read |
|---|---|---|---|
| Gate 0f | correct | absent | documentation looked right the whole time |
| §0.5 ceilings | correct | absent | R2/R3 never started, which is the failure §0.5 names |
| **Gate 0d** | correct | **absent, and described as present** | the *only* one where the documents asserted the code |

### Built

* **R5.1 `witness/build_raster_manifest.py`** → `witness/raster-manifest.json`. Per leaf: resolved
  path, dimensions, mode, bit depth, distinct grey levels from the histogram, sha256. Built through
  `witnesses.pixel_source()`, never a directory glob, so it cannot describe a raster the corpus
  would refuse to serve — a manifest assembled by a second route is a second opinion about which
  file is the witness, which is R7.5 exactly. A witness the registry refuses is **recorded as
  refused with its reason**, so "not measured" and "not admissible" are never the same entry.
* **R5.2a `witness/raster_gate.py`** — three clauses reported separately, because a caller that sees
  only "inadmissible" cannot tell a bitonal scan from a mis-sized one. It lives beside `witnesses.py`
  rather than inside it for R7.5c's reason: `curated_sources` imports the registry at every ingest
  boundary and **a pure allowlist must not drag in PIL**.
* 🔴 **`unknown` is returned separately from `failures` and is never folded in.** With no manifest,
  the dimension clause cannot be evaluated — and a clause that could not be evaluated is not a clause
  that passed. Folding them would have made the missing manifest into a silent yes, which is R1.4 and
  is the same defect as the `_empty_because` note that made a real absence look like a known one.
* **R5.2b/c `witness/test_raster_admissible.py`** — bitonal · 8 grey levels · dimensions off the
  manifest each refused **on its own clause**, and a real base-exemplar leaf **admitted**. The fourth
  case is what keeps the other three honest: without it a gate that refuses everything scores a
  perfect three.

### The review's own gap, caught in review

The first version of that test called `assert_admissible` directly. That proves the gate and proves
**nothing about whether anything reaches it** — and "a gate nothing calls guards nothing" is already
written twice in this repository (`assert_same_setting` had no caller; `drop_tomes` had no consumer).
Checking the wiring by *reading* `jp2_page.load` would have been the third. It now drives the real
entry point with a synthetic leaf behind it, and asserts three things at once: the **pixel** route
refuses a bitonal leaf, the **structure** route still serves it (scope governs evidence, never
denominators — R9.2b), and an admissible leaf still loads, without which the refusal proves nothing.

### Also this session

* **R9.4b closed.** `consensus_v2` discovered its sources by **globbing a directory** — the exact
  re-entry route `curated_sources` was written to close, whose docstring names `consensus_v2` as a
  builder that MUST filter and which **did not import it at all**. Old set: `jp2-S06` in all 76 books,
  `eebo-nt` and `jp2-S08` in 27 each. Its own supersession could not have caught `X`, and the reason
  generalises: supersession is keyed on the **filename**, and `X` (`jp2-S08`) and `B` (`pdf-S09nt`)
  are the same copy under two unrelated keys. **A filter cannot enforce a distinction it cannot
  state** — third instance. Delta measured against a **paired run on the same tree**, because
  comparing to the stored figures would have confounded the filter, the `2633cbb` migration and the
  R7.5a re-key: matthew modern 0.9268 → 0.9367, archaic 0.9317 → 0.9321, conservation 0.8370 → 0.8399.
  Corpus-wide the archaic gate flipped on four books **in both directions**. All 76 regenerated;
  **0 now fuse an inadmissible source**; R7.5a-2 drew down **339 → 262**.
* 🔴 **`eebo-*` are absent from the migrated tree, so the BANNED branch never fires on live data.**
  Its correctness would otherwise rest on the *absence of the input* rather than the presence of the
  filter, so `test_consensus_sources.py` proves it by **injection**.
* **R9.6** — commit `2633cbb` moved the project out of gitignored scratch and
  `detect_our_ocr.SCRATCH` was not moved with it. Both anchor reads resolved into a deleted tree,
  `load_anchor` skipped them with `continue`, and every book returned the well-formed
  `{"verses_scored": 0, "error": "no anchor text"}`. **The planned next step was to regenerate 77
  consensus files**, which would have written 77 empty files over untracked reference data. It was
  caught because the step before it printed *nothing* — the absent `[consensus] EXCLUDED` line, not
  the zero, was the tell. Five modules still restate that root and two of them `mkdir` and **write**
  the anchor reads into the dead tree.
* **R9.5 re-opened as R9.5a.** It was marked DONE on the strength of prose: the Overview's witness
  table left the low-resolution column **empty** for the NT and filed `NT-1582-M` under
  *other · frontmatter*, the pre-R9.0 role, while the same file's prose ninety lines later described
  it correctly and the registry said `lowres`. **A document can contradict itself in one file and
  read as finished, because nobody compares a table to its own commentary.** Its acceptance is now a
  machine check, not a reading.
* **§0.6 Precedence added at Sir's instruction**: code and guards → the roadmap register → the Master
  Plan → the companions → the devlog. The register already outranked roadmap prose; the review found
  the drift running *downward from the Master Plan* three times in one sitting, so the ordering was
  extended upward. **The thing that can refuse a claim outranks the thing that can only assert one.**
* **R10 opened** for §0.5's own machinery. `witness/audit_prereq_ceilings.py` reports **10 of 40**
  OPEN steps carrying an hour ceiling and a decision rule. It is filed as an **audit, not a guard**,
  deliberately: as a guard it would force either bulk-inventing ceilings nobody reasoned about or
  weakening the check until it passed. The fraction must **rise**; it is not a pass/fail.

### Recorded, not fixed

**The plan's own sequencing rule has already been broken.** §2: *"No transcription of any leaf begins
before 0b, 0c and 0e are satisfied for that leaf."* R2 (Gate 0b stage 2) and R3 (Gate 0c) are
**nothing built**, and `ground-truth/` holds **51 transcribed files**. This is a *separate* defect
from R7: R7 asks which photograph a reading came from, R2/R3 ask whether the leaf is the leaf it was
called — and §1.4 is the standing proof that the question is live, three of four NT files being made
up. The files are now **PROVISIONAL** in §0.5's sense: usable, **not citable**, no gate closing on
them, re-admitted leaf by leaf as the collation reaches them.

### Result

Guards **10 exit 0**; audits `audit_gt_rasters`, `audit_s06_keys`, `test_verse_scope_bypass`,
`audit_prereq_ceilings` exit 1, each with its remedy named. `test_verification_standard` names **18**
commands and agrees with reality. **Gate 0d is built and enforced on two of three clauses**; the
third stays UNKNOWN and says so per leaf until the manifest completes.

---

## Session 14b (2026-08-10) — R9.2c: Gate 0f gets one route, and two defects fall out of routing to it

### The conversion target was wrong, and taking the obvious one would have re-made the defect

Nine modules read `.corpus-localize-*.json` directly, so Gate 0f guarded `qc_audit` and nothing else.
The recorded plan was "route each through `load()`". **`load()` is not a drop-in**: it returns
`{(book, ch, verse): text}` and throws away `page` and `fit`, which is precisely what every direct
reader wanted — `gen1_r3` uses the localizer's `page` as *evidence about where a verse sits*, and says
so in its own docstring. Converting to `load()` would have meant re-deriving that from somewhere else,
i.e. **making the gate cost evidence**. A gate that costs evidence is a gate that gets routed around,
which is R9.2c restated one turn later.

So the refusal went **in front of the read the callers were already doing**: `corpus_localize.load_raw`
(the whole artefact), `load_verses` (the `["verses"]` sub-map every bypasser reached for), and
`iter_localizations` (the sweep route, which drops `none`-scope volumes and **prints** the drop before
the first yield — a caveat that arrives after the number it qualifies is not a caveat). The gated route
is now the *cheapest* one available. That, not the guard, is what keeps it the only one.

**Data-neutral, verified rather than asserted**: for all ten admitted volumes `load_verses(od)` is `==`
the raw read (21,437 spans compared). Only `jp2-S06ot` (4,045) and `jp2-S08` (2,334) are refused.

### The exemption is now checked, not trusted

`source_inventory_audit` globs the artefact *filenames* and never opens one, so it is exempt with
`integrity_sweep`. But an exemption resting on *"this read is bookkeeping, not evidence"* is a claim,
and the standing lesson here is that **a filter cannot enforce a distinction it cannot express**. This
one is expressible: scoring a verse needs its **`text`**; reconciling one needs only its key and `page`
(which is all `integrity_sweep`'s C10 reads). The guard now voids any exemption whose module reads a
verse `text` field. Injection: adding `rec["text"]` to `integrity_sweep` → exit 1 naming the forfeit.

⚠️ **The guard's first version was tripped by its own documentation** — a docstring recording a reader's
conversion *away* from the path quoted the glob it had removed. A check a comment can trip is one that
gets satisfied by rewording, and it then measures vocabulary instead of call sites. It now counts string
constants via `ast` with docstrings excluded, and falls back to the raw regex on a file that will not
parse, because an unreadable file must not come back clean.

### 🔴 A CONTAINMENT FACT WAS BEING READ AS A SCORING PERMISSION

Routing `book_audit` through the gate made it **raise**, which is the finding. `witnesses_for_book`
derived its witness set from `witness_inventory.tomes` — a statement about which books a volume's leaves
*carry* — and both callers used it to decide what may be *scored*. So `OT-1635-M` and `NT-1582-X` were
still being handed to the scorers after R9.4 had removed them everywhere else.

**This is R7.5a-3's category error with the arrow reversed.** There, a scoring rule (`drop_tomes`) was
read as a containment claim and force-fitted 800 NT leaves onto Old Testament books. Containment and
admissibility are different questions and `tomes` only answers the first, so they now have separate
accessors (`for_scoring=`) rather than one that has to be interpreted correctly.

Paired run, same tree, only the gate differing, all five pilot books: **every surviving witness
byte-identical, `all_pass`/`split`/`all_fail` unchanged on every book.** The dropped witness contributed
`localized 0, passed 0` and a 100% localization-miss list. It was an empty shell in the set.

### 🔴🔴 THE PARITY SPREAD WAS THE BEST WITNESS'S OWN PASS RATE, ON ALL FIVE PILOT BOOKS

That empty shell put a `0.0` in the floor, so `max − min` reduced to `max − 0`:

| book | reported "parity spread" | best witness's pass rate | equal? |
|---|---|---|---|
| genesis | 0.7601 | 0.7601 (S9) | **yes** |
| psalms | 0.6330 | 0.6330 | **yes** |
| matthew | 0.7594 | 0.7594 | **yes** |
| john | 0.6507 | 0.6507 | **yes** |
| apocalypse | 0.5728 | 0.5728 | **yes** |

**A metric that measures nothing still produces a ranking** — the R7.5a dead-metric lesson, except this
one restated a real number, so nothing ever looked wrong. Gate 0f removes these two volumes but **not the
mechanism**: an *admitted* witness not yet localized puts the `0.0` straight back. The spread is now taken
over witnesses with `localized > 0`, the excluded are **named** in `parity_spread_basis`, and with fewer
than two readers it is **`None` with a reason, never `0.0`** — a spread of zero and the absence of a
comparison are different claims (R1.4). Injection: adding admitted-but-unlocalized `jp2-S04` to genesis
gives 0.7601 under the old formula and 0.0842 + `excluded: ['S4']` under the new; one reader → `None`.

**Corrected spreads: genesis 8.4 · psalms 15.4 · matthew 19.5 points.** Every parity-spread figure
published before today is superseded and is registered under R10.2.

### Result

`test_verse_scope_bypass` moves from the audits block to the **guards** block. Guards **11 exit 0**;
audits `audit_gt_rasters`, `audit_s06_keys`, `audit_prereq_ceilings`, `audit_setting_points` exit 1.
`test_verification_standard` names **19** commands and exits 0 — it caught the ceiling audit's claim
going stale (`10/40` → `10/39`) the moment R9.2c moved to DONE, which is the block doing its job.

### R5.1 — the manifest landed, and one acceptance clause could not be executed

The full build completed in **48 min** (3 h ceiling not reached, so the pre-registered deferral to a
two-clause Gate 0d never fired): **3,122 leaves** — NT-1582-B 812 · OT1-1609-B 1,160 · OT2-1610-B 1,150 —
`truncated: false`. Coverage checked against `witnesses.pixel_source()` rather than assumed: **0 rasters
on disk without a manifest entry**. **3,113 leaves moved from UNKNOWN to CHECKED** on Gate 0d's dimension
clause, which the smoke run had left unmeasured. `test_raster_admissible.py` exits 0 with the dimension
clause live; the UNKNOWNs remaining in its output are its own synthetic `.tif` fixtures, which is the
behaviour being asserted.

⏳ **R5.1's determinism clause — "regenerating it twice is byte-identical" — could not be run at all**:
the output path was hard-coded, so a second build would destroy the first. Added `--out`. **An acceptance
clause that cannot be executed is not an acceptance clause**, and this one had been standing in the
roadmap unexecutable since it was written. 🟢 **The second build landed byte-identical** — 3,122 leaves, `truncated: false`, sha256 `44290ad7…f8e0`
for both, canonical file unclobbered — so **R5.1 is DONE on both halves**. ⚠️ That comparison is valid
only because the writer uses `sort_keys=True`; `coverage-audit-verse.json` is the counter-case on record,
order-nondeterministic on ties, where byte-comparing two runs proves nothing. Same test, opposite verdict,
decided by the writer rather than by the data.

Also fixed while touching the builder: the per-witness line now flushes. Without it a redirected log shows
nothing until the first 200-leaf marker, so a run that died on witness 1 looked identical to one that had
not started.

⚠️ **The §0.5 ceiling audit moved the wrong way, 25% → 17% (`10/40` → `6/35`)**, and it is recorded rather
than restated: closing R5.1/R5.2a–c/R9.2c removed four of the ten ceilings along with five OPEN steps,
because ceilings had been written for exactly the sections next touched. **R10.1's "the number must RISE"
cannot be satisfied by doing the work** — only by writing ceilings for sections nobody is about to touch.

---

## 2026-08-22 → 08-25 — R2.2m far bucket, the S6 denominator bar, and four refuted span rules

**R2.2m — a code path that could not emit a row, by construction.** `collation_read._rows_and_lines`
keyed an unexplained glyph `("far", bs, id(bx))` — unique **per glyph** — so each became a row of
one and the `len(r) >= 2` exit filter deleted it. Measured over leaves 400–419: **760 far glyphs
produced 0 rows.** What it deleted was the RUNNING HEAD — `'NVMERI'` orphaned at row 0 on five
leaves. Fixed by chaining at the same `ROW_TOL_P` the greedy branch already uses, folded forward
from that branch rather than restated beside it.

⚠️ **S2 read 20/20 throughout**, because S2 counts BODY-BLOCK rows and every shredded line was a
short one outside the body block. That is the second time in one run a criterion scoped to one
region was blind to damage in another; the first was 13 orphaned running heads. **Any row-clustering
criterion needs a companion that sees the head and note grids.**

**The S6 denominator bar.** Every criterion in `score_head_regions` was a RATE, and the scorer let a
candidate change what the rates were computed over. It cost two wrong readings: a seed finder that
discarded every short line posted accuracy 0.8760 → 0.9000 while scored pairs fell **121 → 90**; and
candidate 4's RH recall 0.9231 was summed over **13** entries where the control sums **19** — not a
worse number, a **different quantity**. `FULL_ACCOUNTING` now requires `pairs == len(entries)`;
`BAR_MAX_INK_ORPHANS` is a NON-REGRESSION bar at the control's value, **not an endorsement** — the
stated ideal is 0 and stays OPEN. Verified in both directions: control PASS/exit 0, candidate
FAIL/exit 1. ⚠️ **NOT pre-registered**, and the module says so; both values are taken from the
control and from lines the module already printed and never read.

⚠️ **`test_region_gold_addressing`'s accounting clause did not cover this**: it requires losses to be
REPORTED, not absent. Candidate 4 sheds 5 entries and reports all five (116 + 5 = 121), so the guard
is silent while the rates ride a short denominator. **Enumerative vs quantitative.**

**R2.2n — the MN gap. Four span rules, four refutations, NOT CLOSED.** `segment`, `R4_PER_SEGMENT`,
`R4_DEMOTE_UNQUALIFIED` and `flush` were each built and measured against bars pre-registered before
the first run. Every non-inert one buys ~1 MarginNote for **11–12 MainText**. `R4_PER_SEGMENT` is
**inert** — bit-identical on both arms — because `_in_body_seg` returns True for any row absent from
`body_segs`, which is precisely the unqualified row it was built to catch.

**R2.2o is the cause, and it is upstream of all four.** `region_segments` cuts wherever a gap exceeds
the line pitch. Measured: of **301** rows whose token union spans ≥0.75 of the measure, **102 (34%)
have no continuous segment reaching 0.75**; only 49% are a single segment; 2.3% of intra-row gaps
exceed one pitch. In justified setting the word space is stretched to fill the measure, so the cut
rule cannot separate a stretched space from a run out to the margin. **A fifth span rule would
inherit the same error.**

🔴 **METHOD FAILURE, MINE, RECORDED BECAUSE IT IS THE TRANSFERABLE PART.** The roadmap **already
contained** the refutation of `segment` (*"MT falls to 0.7875"*), already named the cause (*"a body
row's own VERSE NUMBER sits beyond a pitch-wide gap"*), and already specified the next candidate
(*"the extent of the region run that is FLUSH TO L OR R"*). I ran three candidates before reading
it. **That is this project's signature defect — a correct rule nothing reads — committed against the
governing document itself.** The measurement I added (34%, and the generalisation past verse numbers
to stretched word spaces) was worth having; the three runs to rediscover a written refutation were
not. ⚠️ **Read the roadmap step before building the candidate, not after refuting it.**

**Committed** `ac34ebf` — 38 files, +11,895/−201, the whole `ocr-spike/witness/` working set, because
neither fix was separable from it: `BASELINE_MODEL` and `baseline_seeds` did not exist in HEAD and
`score_head_regions` had never been committed. 21 modules were untracked, 12 of them named by the
roadmap's own verification standard, so **HEAD could not previously run its own suite**; it can now,
verified by parsing the roadmap for all 44 named commands.

**Status: candidate 4 (R2.2i+R2.2k) NOT ADOPTED, `BASELINE_MODEL` stays False. The MN gap is OPEN
and blocking. R2.2o is the next step — fix the primitive, then re-run the four candidates.**

**2026-08-25 (cont.) — R2.2o.1: answered for the head band, opened for the body.** Built
`witness/score_region_gap_pops.py`, which labels the two intra-row gap populations from GOLD-HEADBAND
and uses geometry only to address which entry a glyph belongs to. Finding: the populations **overlap**
on [0.875, 1.525] pitches, so the best possible single threshold still misclassifies. The **MN|MT**
boundary on **leaf 412** measures **0.875 pitches** — below the cut, therefore never cut — which
independently corroborates R2.2e-b's leaf-412 contiguity observation from a different instrument.
⇒ threshold retuning is **refuted** as the repair, and R2.2o.2's "second signal" requirement is now
supported by measurement rather than assumed.

⚠️ Coverage is **986 of 12,592** gaps (7.8%), top 3 rows only, holding just **2** MN|MT boundaries.
So R2.2o.1 is answered for the head band and **open for the body block** ⇒ **R2.2o.1b raised, and it
BLOCKS R2.2o.2** (a bar on n=2 is Goodhart). The seam fold was attempted and **refused by the
script's own run-time guard** (7 of 39 seams reach region-gap width), so the stricter accounting
stands and the flattering number is not reported. No production flag touched; `BASELINE_MODEL` still
False, MN 17/19 and MT 67/80 unchanged. Suite h GREEN, byte-identical to g.

⚠️ **METHOD NOTE, carried forward from this session's failure.** The four refuted rules plus this
separability result mean **five** dead ends now rest on one primitive. `region_head` is a hand-built
geometric rule system fitted to ONE witness over 20 leaves against a 19-entry MN bar. It is the
scaffold, not the deliverable — the deliverable is the archetype-first learned region model of
Masterplan §3.2a / R12 / Gate 9, of which **no layout score of any kind has ever been computed**.
R2.2o.2 as written would hand-build a column detector inside the scaffold. **Raised for Sir's ruling
2026-08-25: fire R2.2o.3's pre-authorised approach-level ALERT now rather than after a fifth rule,
demote R2.2o.2 to signal characterisation, and promote GOLD-LAYOUT + R12.1 ahead of it.** Not
recorded as decided; recorded as raised.

---

## 2026-08-25 — SIR'S RULING: the adaptive visual agent becomes the stated aim, and the docs are recalibrated to it

**The trigger was one sentence of mine**, that today's pipeline uses fixed bands rather than anything
adaptive. Sir named it project-killing and ruled: review every planning document, revise whatever runs
contrary to building an adaptive visual agent, and calibrate all of them to state that **this** is what
the workflow is for — reproducing the human act of scanning a page, identifying text-class regions by
visual cue, and handling each region as its own section with its own rules, context and gates.

**First, the sentence needed sharpening, not repeating.** `layout.py:type_lines` is not purely fixed
bands: it derives the body column from **each page's own wide lines** (median x of lines ≥ `wide_frac`),
which is genuinely per-page. The fixed parts are `wide_frac=0.50`, `margin_frac=0.06`, header `<0.15·h`,
catchword `>0.88·h`. **The real indictment is larger**: it decides from **geometry alone**, emits **4
roles** against the archetypes' full inventory, runs on **kraken's line objects** which have already
merged margin into body on ch3/ch6, and **cannot abstain** — its no-geometry branch is
`return ["body"] * len(lines)  # fail-safe toward body`, so a leaf it cannot read is emitted as entirely
scripture. That is a null with no cause established, in the shipping path.

**SIX STEPS → EIGHT.** Sir's six were kept in substance; two were added, each because this project has
already measured the cost of their absence, and two were sharpened.
* **S5 RELATE (new)** — reading order **and attachment**. This edition's scholarly value *is* a relation:
  an annotation belongs to a verse, and the 1,334 apparatus blocks are not apparatus unattached. All
  three summary documents already said *"region boundaries, archetype classification, reading order"* in
  one breath — so it was always intended and never given a step, an owner or a gate. §3.2 item 6 is the
  proof: DropCap was excluded from being a region class *because* "polygons and reading order handle
  nesting badly" — a relation problem correctly diagnosed, then routed around.
* **S8 RE-EXAMINE (new)** — the difference between a model and an **agent**, which is what was asked for.
  §3.2 item 3's residue signal already "localises a missed or clipped region" but is spent only as
  training data for the next generation. Read at **run time** it is the agent noticing it misread a page.
* **S4 sharpened** — confidence, and **abstention as a first-class output**, which retires the
  fail-safe-to-body branch above.
* **S6 sharpened** — recognition **conditioned** by region class (model, lexicon, post-rules), not merely
  cropped to it. Grounded: R2.2d measured that a row is not homogeneous in fount, and the `genesis-24`
  49-point content/surface spread is what pooling incommensurable regions costs.

**What was written.** MASTERPLAN: new **§3.0 THE ADAPTIVE VISUAL AGENT**, GOVERNING, carrying the eight
steps, a measured live-path-versus-aim comparison table, an explicit **forbidden list** (each item
something this project has already done, so a repeat is checkable rather than a judgement call), and an
honest per-step status. New **§4.0** making recognition region-conditioned. §3.2 subordinated with a note
that "shapes from ink" describes how the model is **trained**, not what it does. §3.2 items **10**
(relations) and **11** (confidence/abstention) added as model outputs. §3.2a's archetype-A estimate
*"the incumbent bands already handle it"* **withdrawn**. Gate 9 extended with **9.6 abstention · 9.7
relations · 9.8 the loop**, all three deliberately **numberless** for the same reason 9.5 is. Build order
step 10 restated as the agent.

🔴 **The ordering instruction in §3.2 was WITHDRAWN and replaced by its opposite.** It read *"do not read
§3.2a's archetype programme as the next step while this is open."* Sound while the primitive's defect
looked like a **threshold** defect — but R2.2o.1 destroyed that premise, and the repair now needs the
shape of ink beyond the gap, which is **perception**. The instruction had become *"do not build the
perceiver until the perceiver is finished."*

**ROADMAP.** R2.2o's **approach-level ALERT FIRED** (pre-authorised by R2.2o.3, fired before a fifth rule
rather than after). R2.2 **re-scoped**: `region_head`/`region_segments` go from *the region model* to the
*initialisation and plausibility clamp* of §3.2 item 5 — **characterised and willing to abstain, never
maximised** — which converts the four refuted rules and the overlap measurement from a stalled repair
into **complete characterisation work**. R2.2o.2 **demoted** from "build the rule" to "characterise the
signal". New **R14, THE ADAPTIVE VISUAL AGENT**, seven steps: R14.0 register/run/score the *already
existing, undocumented* `surya_layout_probe.py`; R14.1 archetype on the **page**; R14.2 regions with
confidence and abstention; R14.3 relations; R14.4 region-conditioned recognition (absorbing R13.1);
R14.5 the loop; R14.6 the distant-supervision **label generator**. ⚠️ **The MN gap stays OPEN and R2
still blocks Gate 0b/0c.** This is a method redesign, never an accepted gap.

⚠️ **R14 does not start from zero.** The R2.2 line produced three things it needs: the proof that no gap
constant exists; the B1/B2 distinction with a *measured* 26px gutter; and the finding that **kraken
destroys the boundary upstream**, which is a hard input constraint on R14.1 — the agent must see the
page, not kraken's lines.

**THE STALE REGISTER, FIXED THE SAME DAY.** `audit_prereq_ceilings` derives its whole denominator from a
**hand-maintained** `**OPEN** —` prose list, and that list stopped at **R2.2m** — so every step raised
since 08-22 returned **0 hits** and the `1/72` claim was intact *because the register never grew*. Filed
the six R2.2n/R2.2o steps and the seven R14 steps: **72 → 81**, claim **1/72 → 8/81**. The numerator rose
because R14 was filed **properly** — a section-level pre-registered decision rule plus a complexity class
in every row — rather than added bare; **the uncovered count held at 38, so filing 13 steps added no
ceiling debt.** The claim was re-measured and rewritten, never estimated.

**Also registered:** `witness/score_region_gap_pops.py` in the verification standard's audit block
(38 → 39 commands), which required its coverage line to print a real `986/12592` fraction, since a claim's
first fraction must be one the command actually prints.

### 2026-08-25 (later) — R14.0 DONE: the first layout score on this corpus, and two register defects

**Review of all Masterplan and Roadmap sections found three defects of one shape.** (1) **Two gate
registers named the same checks differently** — §3.2's Gate 9.1–9.8 against §7.8's rows 10a–10f — and
the document had **already contradicted itself**, §2 citing *"Gate 10c's threshold"* for the slant check
§3.2b calls 9.5. (2) **Gate 9.6/9.7/9.8, written earlier the same day, had no §7.8 row at all**, so by
§7.8's own document-level invariant they had not entered the build order. (3) **The Roadmap cited §7.8
zero times**, and the consequence was concrete: **Gate 11 — G1 recognition, the gate for the character
recognition model — had no Roadmap step of any kind**, while "what progress on the recogniser?" was
being answered from validation figures §7.8 explicitly says are *"neither Gate 11 measurements nor
layout measurements."* Fixed: §7.8 declared canonical with a binding crosswalk, rows **10d/10e/10f**
added, **R15** (one gate register, as an *executable* audit) and **R13.3** (Gate 11's first measurement)
written. ⚠️ **Instance 16 of the signature defect** — the OPEN register decayed because it was hand-
maintained; §7.8 was never wrong, it was simply never read.

**R14.0 IMPLEMENTED AND SCORED.** `witness/score_surya_layout.py`. Surya `FastLayoutPredictor` 0.21.1
against GOLD-HEADBAND, leaves 400–419, page-fraction addressed, two **declared** label maps, 121 bound,
**0 orphans**. **RunningHead 20/20 · MainText 80/80 · MarginNote 0/19 · overall 100/121 = 0.8264.**
Surya emitted **zero `Footnote`** boxes, so the charitable map was empirically identical to the strict
one — the marginalia ceiling is not a mapping artefact.

🔴 **The result is a LABELLING failure on a WORKING DETECTOR.** MarginNote entries bind to **tight**
boxes (median **0.0039** of page area), so Surya finds the notes as distinct objects and simply has no
name for them — its vocabulary is modern-document and contains no marginalia class. ⇒ **R14.1 is
redirected from "train a detector" to "class-inventory fine-tune of an existing one"**, which is
materially cheaper. ⚠️ **`LayoutPredictor` was tried first and failed**: it needs a `llama-server`
binary that is not installed (`brew install llama.cpp`, or set `LLAMA_CPP_BINARY`). `FastLayoutPredictor`
needs no such backend. Recorded rather than routed around.

⚠️ **THE ARCHITECT PASS FAILED MY OWN SCORER, TWICE, AND BOTH CATCHES CHANGED THE REPORT.** (a) The
first version bound a gold entry to **any non-zero overlap** — the exact defect R2.1i had already fixed
once in `score_head_regions` (*"a binding must be SUBSTANTIAL, not merely non-zero"*), reintroduced by
me in a fresh reimplementation. `MIN_BIND_FRAC = 0.50` of the gold entry's own area added. (b) **MainText
80/80 is CONTAINMENT, not boundary quality**: the bound boxes cover a median **0.5555 of the page**, and
a half-page block containing every body entry scores 1.0000 for free. A per-class bound-box-size report
was added so the trap is *visible* rather than arguable. **The MainText figure must never be quoted as a
win**; Gate 10b's boundary error is the check that separates them and is not measured here.

📌 **The comparison that matters, on the same gold**: Surya beats `region_head` on MainText (80/80 vs
67/80, with the containment caveat), ties RunningHead (20/20), and loses MarginNote (0/19 vs 17/19).
**Neither is adequate alone, and the hand-built geometric component is currently the only thing in the
project that can NAME a marginal note** — which is the "initialisation and plausibility clamp" role
§3.2 item 5 assigns it, now evidenced rather than asserted. ⚠️ Coverage limit: GOLD-HEADBAND labels the
top 3 rows, so every MN entry here is a **head-band** note; outer-margin notes beside the measure are
**not** covered, the same limit R2.2o.1 hit and R2.2o.1b would lift for both.

⚠️ **THIS DISCHARGES NO GATE.** Rows 10a/10b are reserved for GOLD-LAYOUT. Bars were pre-registered in
the file before the run: MN ≥ 0.50 **FAIL**, overall ≥ 0.70 **PASS**.

⚠️ **The three summary documents were the mechanism of the drift, not bystanders.** §8a already recorded
that the recogniser's status *"appears in none of the three"*. The same hole hid the aim itself. Fixed:
EXEC SUMMARY gains **§8b** with the eight-step status table; OVERVIEW's pipeline diagram now states the
agent, the abstention rule and the re-examination stage; WALKTHROUGH gains a *what the geometry stage is*
statement plus the measured contrast against the incumbent typer.

---

## 2026-08-26 — R14.6a, and the gate register becomes an instrument (R15 COMPLETE, R16 raised)

🔴 **THIS ENTRY OPENS WITH THE DEVLOG'S OWN DEFECT.** `R14.6a` was implemented, scored and **committed**
(`09e45ac`) on 2026-08-26, and this file's last entry was **2026-08-25**. The devlog is last in §0.6's
precedence order, which makes it the document that may be *overruled* — it does not make it optional.
A completed step that reaches the commit log and not the record is the same shape as every other defect
this project keeps finding: **a correct artefact that nothing reads.** Recorded here rather than
back-dated silently.

### R14.6a — every region class has an admissible label source, and the audit's own first run was wrong

`witness/audit_label_sources.py`. R14.6 rests on the claim that §3.2 item 2's text sources make the
agent's training labels affordable without a hand-labelling campaign; **that claim had never been
checked against the disk.** Result: **Marginalia is ADMISSIBLE** — `janvier/original-douay-rheims-repo`,
**3,754** verse-anchored side-note objects, **3,538** `<mn>` anchors, **53** books, OT 1609 + NT 1582,
**CC0**, *this edition* — corroborated by **165** `marginal_notes` in the odr-com apparatus scrape
already on disk. MainText **150,834** verse reads over 5 witness read-files. Argument **1,334** blocks.

🔴 **THE FIRST RUN (08-25) REPORTED A FALSE ABSENCE, AND IT IS THE MORE USEFUL FINDING.** It searched
`reconstruction/reads/` only and concluded *"no transcribed side-note corpus is on this disk"* — true
of one directory, false of the disk. **Two sibling errors have the identical shape**: the SRC clone was
sought under `ocr-spike/.scratch/` when it lives at `palimpsest/.scratch/`, and the Madueke source was
sought with `find -maxdepth 7` when it sits at **depth 8**, then reported as *"searched ALL of
`~/Claude`"*. ⚠️ **A bounded search returns "not found" in exactly the shape an exhaustive one does.**
State the bound, or do not claim the scope. Same disease as the OPEN register that counted only what
someone remembered to type into it.

**Two run-1 findings survive the correction unchanged.** (1) **§3.2 item 2 names the wrong source** —
it reads *"Marginalia from the 1,334 transcribed apparatus blocks"*, and all 1,334 are `kind='argument'`,
which is archetype C's class where a MarginNote is archetype B's. The error would have surfaced only
after training, as an unimproved marginalia score. (2) **`scan_marginal` is still poison** — it is
`layout.type_lines`' own output, so training a replacement on it teaches agreement with the instrument
being replaced, and that agreement then reads as validation. **A circular label is worse than a missing
one, because a missing one is visible.**

🎁 **Unplanned gain**: the notes arrive carrying the verse they attach to — the note-to-verse relation
**S5 / Gate 10e** exists to measure, which had been scoped as separate work. ⚠️ **Open, and R14.6c must
settle it**: janvier's notes hang off chapter *annotations*, so they may be marginalia of the annotation
pages (archetype E) rather than of the scripture pages (archetype B) the gold window holds.

⚠️ **R14.6b's ✅ IS A RE-SCOPE, NOT A DISCHARGE**, and the DONE list was one edit away from saying
otherwise. The scrape the plan called for **had already been run** — 763 files sit in
`originaldouayrheims-com/apparatus/` — so the row moved from *"scrape"* to *"ingest what is held"*. The
ingest itself is not done and the step stays **OPEN**.

### R15.1 · R15.2 · R15.3 — the crosswalk stops being a paragraph

`witness/audit_gate_register.py`. Parses §7.8's table, the crosswalk beneath it, and this Roadmap's step
ids, reporting four classes: a Masterplan clause with no canonical row · a row with no step · a gate
cited in the Roadmap that §7.8 does not define · the Roadmap not reading §7.8 at all. **Live: exit 1,
0 hard defects, `12/25` rows discharged, `13` NOT YET PLANNED.**

⚠️ **THE ACCEPTANCE WAS THE HARD PART, AND IT IS THE PART THAT WOULD HAVE BEEN SKIPPED.** R15.1 asks
that the audit *"reproduce today's three findings from the documents alone, and would have failed before
this session's edits."* The three findings were hand-fixed on 08-25, so **against the live files the
audit passes and that proves nothing.** The pre-fix document state is therefore reconstructed in the
file and the same pure `audit()` is run against it under `--selftest`: **8 hard defects**, including
`Gate 9.6 / 9.7 / 9.8` with no row and the Roadmap citing §7.8 zero times. **A guard that has never
rejected anything is not known to work** — the standing rule, applied to an audit for the first time.

🔴 **AND THE FIRST LIVE RUN FOUND TWO DEFECTS THE HAND FIX HAD MISSED.**
1. **`Gate 0e` and `Gate 0f` had NO ROW in the register declared canonical.** Both are cited throughout
   the Roadmap and §2; both are enforced by shipped guards; **Gate 0e blocks 0b and 0c and therefore all
   transcription.** §7.8 published 0a–0d and stopped. This is the **fourth instance of R15's own defect,
   inside the table R15 was written to bind**, and the 08-25 review missed it because it read the table
   looking for the *geometry* clauses. Rows **0e** and **0f** added with metric · threshold · set · n ·
   discharging step. ⚠️ Row 0e's `n` cell records R8.4a's limit rather than rounding it away: head
   criteria at ≥3 separated points, **foot criteria at ONE**, R8.4b open.
2. **One crosswalk cell read `row 3` where every other reads `10a`**, so `Gate 4.1` resolved to nothing.
   A cosmetic inconsistency in prose is a parse failure in an instrument — which is the argument for the
   instrument.

📌 **R15.2's FILL-IN IS ITSELF THE FINDING.** Ten of twenty-three rows had a step; the column made the
other thirteen sayable for the first time. Rows 12–14 *should* be unplanned this early and 10c–10f are
deliberately numberless. **Three are neither**: row **1** (drop-cap fix, 18 cells), row **2** (residue
detector), row **3** (archaic typeset census) — the Executive Summary's own three **low-to-medium
complexity, no-prerequisite** items, this project's cheapest gates, **unowned by any step while four
hand-built span rules were being refuted against one witness.** And **row 9 (GOLD frozen)** is the most
consequential: it blocks rows 10a–10f *and* row 11, i.e. **both** models §8a reports on, and R13.3
already named it as its own blocker.

⇒ **R16 filed**: R16.1 freeze GOLD-LAYOUT/GOLD-TEXT (**blocked by R12.1**) · R16.2 residue detector ·
R16.3 archaic typeset census · R16.4 drop-cap board fix. Register **86 → 87**, ceiling claim
**13/86 → 14/87**, re-measured and rewritten rather than estimated. ⚠️ **The register's own documented
trap fired during that edit**: the R16 entry was first worded *"the four unowned rows R15.2 made
visible"*, which enrolled the **closed** R15.2 as OPEN and read 88. Reworded to name the audit rather
than the step — exactly as the 08-25 caution says it must be, one day after that caution was written.

**Also fixed**: the verification standard's audit block carried **two** `audit_label_sources.py` entries,
the second holding the **superseded 08-25 claim** (*"0/2 Marginalia sources are admissible"*) beside the
corrected one. A block whose purpose is to make a claim refutable was carrying a refuted claim. Removed.

---

## 2026-08-26 (later) — Sir stopped the auditing. The agent got built.

🔴 **THE INSTRUCTION, RECORDED VERBATIM BECAUSE IT IS THE TURNING POINT OF THIS PROJECT.**
*"Honestly, this sounds like a you problem. You know the aims, so why get bogged down in this way? …
Hand-fixes are BANNED. So why do they keep cropping up? Stop hand fixing. Build the visual agent that
can AUTOMATE the text class recognition. Agent uses a visual model, takes the page, sees the text
blocks, consults archetypes, decides what each text block probably is, does some quick reading to
confirm, revises if needed, and generates the image chunks for OCR. Is that really that hard? No, it's
really not."*

**It was not.** The four span rules, five pre-registered bars and one overlap measurement that preceded
this were all searches for a **CONSTANT**. The agent needed a **FRAME**.

### R14.1 · R14.2 — the adaptive visual agent, built and scored

`witness/visual_agent.py`. S1 see the leaf → S2 archetype → S3/S4 name and bound, with confidence and
the right to abstain. On the same gold, the same 20 leaves and the same binding rule as R14.0:

| | overall | MarginNote | RunningHead | MainText |
|---|---|---|---|---|
| Surya off the shelf | 100/121 | **0/19** | 20/20 | 80/80 |
| geometric `region_head` | — | 17/19 | 20/20 | 67/80 |
| **THE AGENT** | **110/121 = 0.9091** | **13/19** | **20/20** | 77/80 |

**All three rung-0 bars, written into the file before the first run, PASS.** MN recall ≥ 0.50 →
0.6842. Overall ≥ **0.8264** — *Surya's own score on this gold*, so buying marginalia with body text
is a failure by construction, which is the trade R2.2's four refuted rules each made at ~1 MN per
11–12 MT → 0.9091. Forbidden-class emissions 0. ⚠️ **Bars applied to the WORSE of two declared
addressing rules**, never the better.

🔴 **THE IDEA: A FRAME, NOT A THRESHOLD.** R2.2o.1 proved no gap constant exists because it asked
*how FAR is this from the body*. A marginal note is not far from the body, it is **BESIDE** it — and
besideness is a fact about **the measure**, derived per leaf from that leaf's own boxes. MarginNote
0/19 → 13/19 with **no fitted constant deciding anything**, which is §3.0's rule kept rather than
argued around.

### R14.7 — draw what the agent sees, and it paid for itself in one run

`witness/agent_see.py`, on Sir's instruction. It renders the agent's **own** output onto the leaf: the
measure it derived, the head floor, every box in its class colour captioned with its confidence and a
plain-language reason, gold agreed-with in grey, **every disagreement in red**.

**The first run scored 91/121 with RunningHead 9/20, and no cell of that table said why.** One picture
of leaf 412 showed three bugs at once:
1. **The measure was being dragged into the margin** — `frame()` took the median edge of every large
   box, and on an apparatus leaf Surya emits the whole *marginal column* as one large box. Every
   besideness test downstream was asked against a frame that already contained the margin.
2. **Size was being read as the body cue** — `area >= SMALL_AREA → MainText` made that same marginal
   column body text. ⇒ **besideness outranks size**.
3. **A cue turned on a last pixel** — `y1 <= head_y` failed by **0.0015 of a page** on leaf 400, and
   eleven of twenty running heads died on that margin. ⚠️ **A cue that turns on a last pixel is a
   threshold wearing a cue's clothes.** Judge the box's mass.

Then the confusion matrix gave the fourth: **the head band holds two different things.** This edition
sets head-band notes at the *same height* as the running head, at the fore-edge, so height cannot
separate them and besideness does not fire because such a note *straddles* the edge. The cue that works
is the reader's: **a running head is CENTRED on the measure; a head-band note is pushed to a side.**

✅ **ABSTENTION IS REAL AND ITS RESIDUE IS DIAGNOSTIC.** All 6 remaining MN misses are abstentions
**carrying their cause**; **3 of the 6** are `cue says MN, but archetype A FORBIDS it`, which points the
next repair at the **archetype classifier** rather than the naming cues. Filed as **R14.9**. The
`fail-safe toward body` branch now has a replacement that says *why* instead of emitting a leaf as
entirely scripture. ⇒ **R14.8** filed to lift the head-band coverage limit.

### R9.7 — Gate 0f's last hole, closed with a proven negative

`GLYPH_BARRED` was keyed by **siglum** and held only `F` and `X`, so `glyph_source()` returned a usable
PDF path for `NT-1582-M` although its `lowres` role bars it from training data, CER and long-ſ. A bar
written in `ROLES` and enforced by nothing — the Overview had recorded it and nothing closed it.
⚠️ **A siglum key could never have closed it**: `M` is ONE file holding TWO books with different roles.
The bar is now derived **per record from the role**. `witness/test_glyph_role_bar.py` refuses **6/12**
records at glyph grain, and its proven negative removes the clause and recovers exactly
`NT-1582-M` and `OT-1635-M` — the two the Overview predicted. ⚠️ **Clause 4 protects the agent**: a
glyph-barred `lowres` record is asserted still to be a **structural** witness, because `M`'s NT is
wanted for region boundaries, archetype classification and reading order. **Closing a glyph hole by
deleting a witness would have cost the visual agent a witness.**

### R11.2e — the verification standard runs again

Filed this morning after two runs exceeded 15 minutes and were killed without a line of output.
**Resolved the same day**: the commands are mutually independent, so the subprocess fan-out is
concurrent (≤8 workers). **Full pass 8m49s, exit 0, 45 commands, every one EXECUTED** — nothing cached,
sampled, skipped or tiered. The cache candidate is struck (a cache-invalidation bug would silently pass
a stale claim); the `--fast`/`--full` split is struck outright, because without a CI `--full` it
converts *"too slow to run"* into *"not required to run."* A harness exception is now a **result**,
never a skip.

⚠️ **Ceiling register: 88 steps, claim 14/88 → 16/88** on a flat denominator — R9.7 and R11.2e closed,
R14.8 and R14.9 filed with their classes in their own rows.

---

## 2026-08-27 — R14.9 and R14.8. Two structural repairs, and the class inventory turns out to be too small

### R14.9 — the archetype classifier was reimplementing the namer, and the page has two ends

**110/121 → 115/121 = 0.9504.** MarginNote **13/19 → 16/19**, ChapterHead **0/2 → 2/2**, RunningHead
20/20, MainText 77/80, forbidden emissions 0. **Neither repair touched a threshold.**

🔴 **DEFECT 1 — TWO CODE PATHS ANSWERING ONE QUESTION.** `classify_archetype` detected apparatus with
the **besideness** cue alone, while `name_regions` has **two** cues that can produce a MarginNote —
besideness, and head-band-off-centre. On leaves whose notes are *all* head-band notes (**402 · 413 ·
415**, outside fractions **0.37 / 0.48 / 0.44**, every one under the besideness boundary) it saw no
apparatus, typed the page `A`, and `A` **FORBIDS** MarginNote — so the namer had to abstain on a note
it had correctly identified. **This project's signature defect had got as far as making the agent
contradict itself.** Both steps now call one `_cue()`, run unconstrained for the archetype and with
FORBIDS applied for the commit, so §3.2a's ordering survives and the blindness does not.

🔴 **DEFECT 2 — FOUR NAMES FOR A PAGE THAT PRINTS AT LEAST NINE.** Leaf 409 sets the gathering
signature `Z z` at the foot, centred. With no foot band the centred-heading cue fired, the agent
invented a **chapter opening**, and it propagated into the **archetype**. The frame now derives a
**foot band**, and `SG`/`CW` are named classes. ⚠️ The foot band has the head band's **nesting**
problem one end down — the body box runs to 0.906 and the signature sits at 0.885–0.904, *inside* it —
so the detector's own `PageFooter` class is the second cue, clamped by position.

🔴 **AND THE SCORE COULD NOT SEE DEFECT 2 AT ALL.** 115/121 before the foot-band repair and 115/121
after, while three leaves stopped falsely claiming a chapter opening. **It was found by DRAWING the
leaf, not by reading a number.** A repair invisible to the only scorer in play is the repair that never
gets made — which is the whole case for R14.7.

⚠️ **THE LIMIT THE SCORE HIDES, STATED.** Archetype **A never fires** on this window, so the FORBIDS
contract does **not bind** and the zero forbidden-emission count is **trivially true**. The archetype
call has **no gold** and is **unmeasured**. R14.9 removed a *demonstrated* error; it did not
demonstrate accuracy.

### R14.8 — besideness generalises, and every marginalia figure ever quoted was its worst case

GOLD-HEADBAND labels the **top three rows**, so Surya's 0/19, `region_head`'s 17/19 and the agent's
16/19 are *all* head-band notes. **GOLD-FOREEDGE** is the first gold below that band: **42 boxes over
5 declared leaves**, population defined by **geometry alone** so it cannot inherit the agent's blind
spots, adjudicated from **numbered, unlabelled** renders.

| | MarginNote recall |
|---|---|
| head band — the cue's **straddling** case | 16/19 = 0.8421 |
| **fore-edge — the cue's **clearing** case** | **18/18 = 1.0000** |

✅ **THE PREDICTION, WRITTEN BEFORE THE RUN, HELD**: *a fore-edge note CLEARS the measure where a
head-band note STRADDLES its edge, so besideness should do BETTER here.* It does. MainText 9/9,
heading 6/6. **The head-band figure was the cue's worst case, not its best**, which inverts how every
marginalia number on this corpus should be read.

🔴 **EXIT 1 IS A CLASS-INVENTORY FINDING, NOT A CUE FAILURE.** All **7** residual errors are classes
the page prints and the agent cannot name: **Argument ×4** (the italic summary under a chapter
heading, misfiled as `CH`), **PageNumber ×2**, **Annotation ×1** — leaf 417 is an archetype **F mixed
leaf** (body → ANNOTATIONS section → new chapter), and **R12 records F as "dropped WHOLE", i.e. active
data loss**, sitting inside the very 20-leaf window the whole programme has been scored on. Filed as
**R14.10a/b/c**. ⚠️ **R14.10b (PageNumber) is BLOCKED and the block is informative**: position cannot
separate a page number from a short head-band note, and *"is this a numeral"* needs the **quick read**
§3.0's S2 describes — which **R13.1's wiring does not exist**. It is the first class that genuinely
needs the recogniser.

🔴 **AND THE DISCIPLINE POINT, RECORDED BECAUSE THE TEMPTATION WAS IMMEDIATE.** Adding an `AR` cue now
would fix 4 of the 8 remaining errors **and would be fitted against the 42 boxes just adjudicated**.
`build_foreedge_gold.py` says in terms that it is *the SCORER, never the trainer*. **R14.10's cues must
be validated on leaves outside this gold's five.** ⚠️ Coverage stated: 5 of 20 leaves, one witness,
**one operator, NOT fully blind**. Discharges no gate; this gold may never be promoted.

**Suite: 47 commands, 8m52s, exit 0.** Ceiling register **88 → 89**, claim **16/88 → 17/89** — the
numerator **fell to 14 before rising to 17**, because closing two steps removes their declarations
from the OPEN population. Recorded rather than smoothed: a numerator that only ever rises is not
measuring anything.

---

## 2026-08-27b — R14.10a. The Argument, and a size prior that was choosing which wrong name a class got

**The agent has learned the ARGUMENT** — the multi-line italic prose summary this edition sets between
the chapter head and the first verse. `witness/build_fount_record.py` + `witness/score_argument_agent.py`.

### The defect was 10 of 10, not the 4 filed yesterday

Yesterday's entry above filed `AR` at **×4**, from GOLD-FOREEDGE. Scored at box grain against R2.2d's
**GOLD-ARGUMENT** (81 rows, 10 chapter openings), **every argument block in the window was misfiled** —
and `SMALL_AREA` **alone** decided which wrong name it got:

| argument box area | agent said | leaves | did any score see it? |
|---|---|---|---|
| ≥ 0.05 of the page | **`MT`** | 400 · 403 · 404 · 407 · 411 · 417 | 🔴 **no — silent** |
| < 0.05 of the page | **`CH`** | 406 · 412 · 414 · 416 | yes — yesterday's ×4 |

**Not one cue was reading the class.** A constant with no opinion about arguments was partitioning them,
and GOLD-FOREEDGE's five leaves happened to sit on the small-box side. ⚠️ **The `MT` half is the half
that matters**: MainText is **containment**, so an argument called MainText scores as *correct* against
every gold this project holds — and would have been handed to the recogniser as scripture and merged
into the verse stream. Six of ten sat there, unmeasured, for the whole programme.

*A class with no name is not a skipped box* has been measured three times now. This is the sharpest:
half of it was not merely misfiled, it was **invisible**.

### The Roadmap's own cue formulation was circular, and is struck

R14.10a was filed as *"a block … directly below a chapter heading"* — relational. **On four of the ten
leaves the argument box IS the agent's `CH` call**, so the misfiled box would have anchored the search
for itself. ⚠️ And `region_head` had **already recorded and refuted** exactly this for the row-grain
rule on 2026-08-18: *"between the ChapterHead and the first verse would be circular — it presumes the
boundary it must find, and is silent wherever the chapter head was missed."* The reasoning sat in one
file while the plan in another restated the refuted design.

**`AR` is decided on the FOUNT.** The relation to the chapter head is an **output** of the class, never
an input — and the archetype now reads an `AR` box as *evidence a chapter opens here*, so an argument
the agent can see rescues a chapter opening whose heading it missed.

⚠️ **AND THE INSTRUMENT ALREADY EXISTED.** `region_head` has defined `ARGUMENT = "AR"` with a validated
per-segment fount test since R2.2d; `collation_read` has had `row_slant`, `region_segments` and
`page_slant_mode` just as long. **No rule read any of it.** Third instance of working-code-no-rule-
governs, after Gate 0f and R13's artefact. R14.10a **wires** it; it does not build a second one.

### The five pre-registered criteria, written before the first run

| # | criterion | measured |
|---|---|---|
| **A1** | recall on the six leaves **DISJOINT** from GOLD-FOREEDGE | **6/6** |
| **A2** | precision over the whole 20-leaf window | **0 FP, 0 unadjudicated** |
| **A3** | no theft on GOLD-HEADBAND | **115/121 · MN 16/19 · RH 20/20 · MT 77/80 · CH 2/2 — EXACT** |
| **A4** | abstainable, proven by withholding the fount record | **0 `AR`, 20/20 leaves state a cause** |
| **A5** | the pre-registered out-of-sample prediction | ✅ **4/4, 34/42 → 38/42, exactly as written** |

**A3 makes it a gain, not a trade** — R2.2's four refuted span rules each bought ~1 MarginNote for
11–12 MainText; this bought a whole class for **nothing**. **A5 makes A1 mean something** — GOLD-FOREEDGE
carries 4 `AR` entries, nothing was fitted against it, and the direction was written down first.

📌 **The guards decide nothing, and the scorer prints the slack rather than asserting it**: italic share
**1.00** on all ten against a 0.50 majority, with the nearest non-argument box at **0.21**; segments
**3** against a floor of 2; measure span **0.90** against 0.60. Every one sits in an empty band.
⚠️ **Besideness still outranks the fount, and that is load-bearing** — *this edition sets its side-notes
in italic too*. Italic **alone** cannot name an argument; italic **on the measure** can.

### Two more copies of the signature defect, caught in passing

`score_foreedge.py` kept its **own copy** of the agent's class inventory so *"the agent has no name for
this"* would be a checked claim. The first run after adoption printed `AR recall 4/4` **and** `AR ⚠️ NO
NAME IN THE AGENT` about the same four boxes. **A checking claim that can drift from what it checks is
not a check** — `visual_agent.CLASSES` is now the single declaration. Separately, the
frame→archetype→name sequence had two call sites and this step would have made it three; folded into
one `settle()` **before** it cost anything, which is the only cheap time.

### It was drawn, and the drawing found the next defect

`agent_see.py` renders `AR` in **violet** — far in hue from `MT` green and `CH` orange, the two names
the class was misfiled into. On **leaf 400** the eight italic lines under `CHAP. XXII.` were solid green
before today. On **leaf 411** the eleven-line argument reads violet under an orange `CHAP. XXVII.`,
captioned *"11 of its 11 lines of type deslant as ITALIC (100%) and it is set to 99% of the measure."*

🔴 **And leaf 411 immediately showed the next one.** It sets `Z z 2` at the foot with the catchword
`Cades` beside it, and the agent calls the **signature** a **catchword**. The foot band's `SG`/`CW`
split is a single `rel_f >= 0.60` position test doing work it cannot support — the same shape as the
head band before it was found to hold two things. **Not repaired here**: it is a second class boundary,
**no gold covers either class**, and hand-fixes are banned. Filed as **R14.10d**.

⚠️ **Coverage stated.** GOLD-ARGUMENT is 81 rows over 10 openings of **one witness**; the adoption
evidence is **six** leaves. **Discharges no gate** — rows 10a/10b stay reserved for GOLD-LAYOUT (R16.1).
What it establishes is exactly: the class inventory grew by one class the page prints, validated outside
the gold that revealed the gap, at zero cost to every existing number.

**Ceiling register: 89 steps, claim 17/89 — both flat, and that is the entry.** R14.10a closed while
R14.10d was filed carrying its own class, so the two moves cancel on both axes. Recorded rather than
smoothed, for the same reason as yesterday: a register that only ever grows is not being maintained.

---

## 2026-08-27c — R14.10c BLOCKED. Two cues refuted, a second false absence, and R13.1 turns out to be the gate

**No code was adopted, and that is the result.** `AN` stays OPEN and blocks. Three independent
blockers were measured, each sufficient on its own. ⚠️ **An ALERT that the approach needs redesign
(§0.5), never an accepted gap** — and the redesign is written down below, because a blocker filed
without one is a shrug.

### Blocker 1 — two visual cues built and refuted

The obvious reading is that this edition sets annotations in smaller, tighter type than scripture.
Both halves were measured per box over all 20 leaves, from R14.10a's fount record:

| candidate | leaf 417's annotation block | what it actually separates | verdict |
|---|---|---|---|
| type height, vs the largest text block | **0.89** | marginal notes, at **0.64–0.69** | 🔴 **refuted** |
| line pitch, same normalisation | **0.84** | nothing — leaf 418's *marginal note* reads **0.84** | 🔴 **refuted** |

**Small type marks apparatus in general, not annotation in particular.** The annotation block sits
*nearer the body* than the marginalia do, so any threshold that catches it catches every side-note
first. This is R2.2o.1's shape in a new place: the populations **overlap**, so no constant exists to
be found — threshold-tuning is *refuted* as the repair, not merely unattempted.

### Blocker 2 — the only reliable anchor is a READ, and that is R13.1

The section head *is* decisive, and the census says why it cannot be used yet: **10 `SectionHeader`
boxes in the window — 9 are `CHAP. N.`, 1 is `ANNOTATIONS.`** — and geometry does not tell them apart.
*"Is this head the word ANNOTATIONS or the word CHAP."* is the quick confirming read §3.0's S2
describes, and **R13.1's wiring does not exist**.

⚠️ **So R14.10b and R14.10c are blocked on the same thing, and that changes what R13.1 is**: not one
step among many but **the step gating the agent's class inventory**. Two of the three classes the page
prints and the agent cannot name are waiting on it — a much stronger argument than R14.10b made alone.

### Blocker 3 — the population is one, and it is on the wrong leaf

GOLD-FOREEDGE holds exactly **one** `AN` box, on **leaf 417 — one of its own five**. R14.10's section
rule forbids validating a cue against the gold that revealed the gap, so even a working cue could not
be adopted here. Unlike R14.10a, which had six disjoint leaves waiting in an existing gold, **there is
no second exemplar to move to**. A cue fitted to leaf 417 would be fitted to a single page.

### And the label-source audit was blind to the field it most needed — a SECOND false absence

`audit_label_sources.py` answered *"has Annotation a source?"* from `apparatus_blocks[kind]`, where the
count is **0** — all **1,334** of those blocks are `kind='argument'`. The odr-com scrape **in the very
same documents** carries a top-level `annotations` field: **246 chapter-anchored blocks, each with its
printed `ANNOTATIONS. Chap. N.` head**. `_odrcom_notes` reads `marginal_notes` and `inline_notes` out
of those files and steps straight past it.

⚠️ **The audit's own footer already states the lesson** — *a bounded search returns "not found" in the
same shape as an exhaustive one.* **The bound was a DIRECTORY the first time and a FIELD NAME this
time.** It now carries an `Annotation` row and a fourth state:

- **246** blocks on disk, with heads ⇒ `ABSENT` is **false**
- **232** are New Testament; the OT holds **14** chapters over **2** books (Genesis, Exodus)
- 🔴 **Numbers has none** — and Numbers is where every region figure in this project is measured
  ⇒ `ADMISSIBLE` would be **worse than false**

⇒ **`🟠 PARTIAL`, blocking on the same footing as `ABSENT`.** A source that does not reach the volume
the class is needed in leaves the class unlabellable *there*; counting it as covered is laundering.
`BLOCKED classes: 1 ['Annotation']`.

📌 **This retracts one sentence from the R14.6a entry above** — *"every region class has an admissible
source"*. It was true of the eight rows that audit carried and false of the class list, because the
row for the ninth had never been written. The entry stands as recorded; this is the correction.

### The redesign

1. **R13.1 first** — wire the confirming read. It unblocks `AN` **and** `PN` together; nothing else does.
2. **Move the annotation window to Genesis or Exodus** — the only OT books the label source reaches,
   and the only place a population > 1 is buildable without hand-labelling from scratch. ⚠️ The leaf
   set changes, so **both** the perception cache and the fount record must be rebuilt.
3. **Pre-register the WIDTH cue and test it there, never here.** Leaf 417's `ANNOTATIONS.` head spans
   **0.325** of the page against the nine chapter heads' **0.203–0.241**: a longer word sets wider,
   which is a fact about the fount, not a read. ⚠️ **Derived from one exemplar** — a hypothesis to be
   tested on the wider population, and fitting it here would be fitting to a single page.

⚠️ **Why not simply widen the present window**: Numbers has no annotation label source at all, so a
wider Numbers gold would have to be hand-labelled end to end — exactly what §3.2 item 2's distant
supervision exists to avoid, and what R14.6a checked the disk for.

**Ceiling register: 89 steps, claim 17/89 — unchanged. Nothing closed, and nothing should have.**

---

## 2026-08-27d — R2.1b. The highest validation accuracy on this disk is the WORST model on a common set

**`dr_v3_armB` is SELECTED, on 7 class wins of 7. R13.1 is UNBLOCKED.**
`witness/audit_recog_holdout.py` → `witness/build_recog_gold.py` → `witness/score_recognisers.py`.

R13.1 could not proceed because R2.1b had never run, and the reason it blocked is worth restating:
*wiring an unselected model replaces "no model" with "an arbitrary model", which is the harder defect
to see.*

### The finding — the ranking everyone has been reading is backwards

| model | headline (NON-comparable) | pooled content, common set | ſ recall | class wins |
|---|---|---|---|---|
| **`dr_v3_armB`** | 0.9694 | **0.9575** | 0.9302 | 🏆 **7 / 7** |
| `reichenau_dr` | **0.9396** — *the figure every document cites* | 0.8902 | 0.9302 | 1 |
| `dr_v3_armA` | **0.9739** — *the highest on disk* | **0.8597** — *lowest un-vetoed* | 0.9302 | 0 |
| `reichenau_dr_ho` | 0.9230 | 0.8693 | **0.8372** | 🔴 VETOED |
| `dr_armA` | 0.9349 | 0.8423 | **0.6744** | 🔴 VETOED |

The Roadmap has warned since 2026-08-17 that `0.9739 > 0.9396` is not a finding, because the five are
per-arm accuracies on **different splits**. It is now measured: **the highest headline is the worst of
the three that clear the veto**, and the cited 0.9396 wins one class of seven. ⚠️ This table does not
make those headline figures comparable — it **replaces** them with a figure that is.

### The ſ veto did real work, and it disqualified the "honest generalisation" model

Applied **first and absolutely**, never as a tiebreak, at a floor of 0.90 written before the run.
It removed **`reichenau_dr_ho`** — the model built specifically to hold pages out — because it
**modernises the long s** (0.8372). Its pooled content beats `reichenau_dr`'s, and that is exactly the
trade the two-metric design exists to refuse: this edition's whole ladder is about recovering ſ.

### What no pooled figure could have said

Every model is near-perfect on MainText (0.987–0.995) and **collapses on the direction line**: `SG`
runs 0.4667–0.7500 and `CW` 0.5333–0.8000 across the five. A pooled mean would have been a scripture
benchmark wearing a per-class label. It also retro-justifies R2.1b's *original* purpose — a confidence
floor for `collation_read`'s direction-line reader is needed precisely where recognition is weakest.
⚠️ `dr_armA` falls to **0.5543** on `AR`: italic is where a modernising model fails.

### The shortcut that would have wasted the whole step

GOLD-HEADBAND carries a `text` field for all 121 entries, and it is **the incumbent recogniser's
output**, kept so a human could assign a LABEL — its own `_doc` says so. Its errors are visible on
inspection: leaf 402's running head reads `NVMENE` for **NVMERI**; leaf 400's side-note reads
`X. Og Alaine.` for **K. Og ſlaine.** Scoring five candidates against it would have measured
**agreement with the instrument being replaced** and read as validation — the identical defect
`audit_label_sources.py` records for `scan_marginal`. **So truth was keyed from the page**, diplomatic,
long-ſ preserved and the page's own typos kept (leaf 400 prints *"to fight iu Edrai"*).

### Two cutting defects found by LOOKING at the sheets, not by a number

1. The first cut was **by row**, which put a page number, a running head **and** a side-note into one
   image labelled `RH`. A row is not homogeneous in region — `region_head`'s founding observation, and
   the reason `region_segments` exists. Re-cut per segment.
2. The pad **clipped leading sorts** (`eople of Chamos`). A crop that cuts a character asks every model
   to read something the page does not print.

**12 of 63 crops remain EXCLUDED with a stated reason each** — two baselines in one image (R2.2k's
row-chaining, on italic), a clipped first or last sort, two margin columns merged — counted, never
silently dropped. ⚠️ **7 of the 12 are MarginNote**, leaving `MN` the thinnest class at 5 lines: the
cutter fails hardest on the class this edition is built around. Stated, not hidden.

⚠️ **Coverage.** 51 hand-keyed lines, 7 region classes, **one witness, one operator, not blind**.
Held out from every training manifest on disk — proven, with the bound stated: a model trained from a
manifest not on this disk is invisible to the check. **Discharges no gate**; whether the winner is
good enough is Gate 11 (R13.3), which needs GOLD-LAYOUT (R16.1).

**Ceiling register: 89 → 88 steps, claim 17/89 → 16/88 — BOTH FELL, and that is correct.** R2.1b
carries its complexity class in its own row, so closing it removed that declaration from the OPEN
population. The cleanest demonstration yet that a numerator which only ever rises is not measuring
anything.

---

## 2026-08-27e — R13.1, first half. The recogniser is loadable, and its stamp is falsifiable

**`witness/recogniser.py` + `witness/test_recogniser_provenance.py`.** 🟠 **PARTIAL, and the split is
stated rather than rounded up.** The mechanism and its proof are done; the attesting-arm conversion
is not, and it is filed as **R13.1a**.

### What R13 found, still true of the shipping path

`gen1_r3.py:666` sets `"old_text": sp.get("text", "")` — the attesting arm is the **stored corpus
OCR**. The ſ-faithful fine-tune this project spent its Rung-2 effort producing is *an artefact no
code loads*: Gate 0f's defect (a rule no code read) one level down.

### One entry point, and it stamps

The model is **read from R2.1b's selection file and never named in the module**. Hard-coding one
would re-create precisely the defect R2.1b exists to prevent, and with no selection present the
module **raises** rather than defaulting — an arbitrary model wearing the selected model's authority
is harder to see than no model at all.

The stamp carries the **digest**, not only the path: a path is a label a human chose and can point at
a file that has since been retrained; the digest is what was actually opened. Given R13's whole
finding was that a component can be pointed at and not loaded, the stamp records the opening.

### The injection proof, and the check that carries it

| # | check | result |
|---|---|---|
| 1 | with the selection hidden, reading **raises** rather than defaulting | ok |
| 2 | the stamp names R2.1b's selection (`dr_v3_armB`) | ok |
| 3 | the stamp carries the artefact's digest | ok |
| 4 | injecting another candidate changes the **name** and the **digest** | ok |
| 5 | injecting changes the **READING** — 5 of 12 crops differ | ok |

**Check 5 is the load-bearing one.** A stamp can be correctly plumbed to a recogniser that is never
actually consulted; checks 1–4 would all pass on that. When broken output equals healthy output, the
**mechanism** has to be validated, not the label. A provenance field no test can move is decoration,
and it would let a reading produced by one model be published under another's name — which is R13's
own finding one level up.

### What is NOT done, said plainly

No `gen1_*` or `s_arbiter` module imports the new entry point yet, so `old_text` is still the stored
corpus OCR. **That conversion changes campaign artefacts**, which makes it a deliberate act rather
than a side effect of a module existing. Filed as **R13.1a**. ⚠️ And R13.2 remains untouched: the
**1,142** `CONTENT OK, ſ-SURFACE OPEN` cells may **not** be reported as recovered before it runs.
Plausibly is not measurably.

### A defect the verification standard inflicted on this work, recorded because it will recur

`build_recog_gold.py` was enrolled in the block as `build_recog_gold.py --check`. **The standard runs
every command it names WITHOUT its arguments** — `run()` invokes `[PY, f"witness/{script}"]` — so the
suite ran it **bare**, took the cutting path, and rewrote all 51 hand-keyed `.gt.txt` files as empty.
The keying had to be redone. Cutting is now opt-in behind `--cut` and refuses to clobber existing
truth even then. ⚠️ **A script whose no-argument behaviour is destructive WILL be run destructively by
that block**, and nothing warned of it.

**Ceiling register: 88 → 89, claim 16/88 → 16/89** — R13.1a filed, numerator flat. ⚠️ R13.1a counts as
**INHERITED**, exactly as R13.1 and R13.2 already do: the R13 rows end in a bare class token that
`CEILING_RE` does not match. A **parser** gap in that instrument, not a gap in those rows — recorded,
not fixed here, for the reason already standing over the decimal-pair trap: changing the parser is a
change to the instrument every other number in the block is verified by.

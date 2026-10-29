# GOLD-LAYOUT — review state, R16.2, and the plan

Working state for the plate book. Lifted out of Jarvis's session scratchpad on 2026-08-29 because it
outgrew a resume doc; the scratchpad now points here. Everything below is CURRENT, not history.

⚠️ Nothing in the eye review is adjudicated. Those findings are a claim about LECTOR's claim. Only a
human verdict recorded in `review.html` settles a leaf.

## 👁️ EYE REVIEW — ✅ **208/208 DONE. 893 findings, 28 classes E1–E28, all live in the tool**
`scratchpad/overlay.py` (scratch only) draws `bundle.json` geometry over the clean plate. 🔑 **The
plate book stays CLEAN by design** — the old book burned boxes into the JPEGs and *you cannot move
ink in a photograph*. Notes → `plates/eye-findings.json` → `plate_eye_merge.py` (idempotent: drops
prior `sev:"eye"`, rewrites) → `review-flags.json`. **ONE highlight channel**, one list per leaf.
📌 1–104 by me; 105–208 by 4 parallel readers, each output **verified against its assignment list**,
merge **refuses on collision**; their strings kept VERBATIM (evidence). GOOD 172 · E2 80 · E14 74 ·
E9 65 · E3 58 · E12 44 · E15 37 · E1 35 · E6 31 · E16 26.
🔴 **DETECTION IS WORSE THAN LABELLING**: **E9** 65 notes unboxed · **E25** chapter/running heads with
NO box · **E27** signatures unboxed · **E26 THE SCRIPTURE COLUMN ITSELF unclaimed** (`OT2-1610-P_0749`
`_0821` `_1011` `_0024` `_0035`). ⚠️ **A label score is BLIND to all of these.** Open `_0749` first.
⚠️ **SCREEN SEES GEOMETRY ONLY** (leaf 417 found only by DRAWING) · **E8/E9 invisible to
GOLD-HEADBAND** · eye notes are MY claim about LECTOR's claim — only a human verdict settles a leaf.
## ✅ R16.2 DONE (UNCOMMITTED) — **PER-WITNESS PERCEPTION RECORDS**
🔑 **STANDING CORRECTION — I GOT THIS WRONG ONCE, DO NOT REPEAT IT.** E2 (80) and E14 (74) are **NOT
cue bugs and `AR` was never a dead class.** `AR` is decided on the FOUNT, `PN` on the READING, and
both records existed for **OT1-1609-B only** ⇒ the other 188 leaves **abstained WITH A STATED CAUSE**,
which is the CORRECT behaviour. I and all four readers misread honest abstention as failure.
**Repair was DATA, not a rule.** Built `fount_/skew_/reading_<wid>.json` for the other 3 witnesses.
**AR 10→90 · PN 14→115 · `??` 166→37. Not one rule changed.**
⚠️ **Scored witness bit-identical**: GOLD-HEADBAND still 117/121, AR 10, PN 14, `??` 8; fount rebuild
**byte-for-byte**; `score_argument_agent` A4 withheld negative still fires.
🔑 `VA._rec_path(kind, wid)` = **THE ONE PLACE** a record path is decided; builders + `_aux_state` ASK
it. ⚠️ It reads module globals **AT CALL TIME** because `score_argument_agent`/`score_skew_frame`
prove their negatives by REBINDING `VA.FOUNT`/`VA.SKEW` — resolve eagerly and both proofs silently
pass while testing nothing. Caches = dicts keyed by wid, tolerant of being cleared to `None`.
🔑 **`plate_book.py --rename`** re-runs NAMING from stored boxes (no Surya pass); **verified 0 box
coordinates changed** — corrections are recorded against coordinates.
⚠️ Traps: crop names `leaf5_box0.png` **COLLIDED ACROSS WITNESSES** · `_aux_state` globbed
`{kind}_{wid}_*.json`, **cannot match** the new names ⇒ `fount:False` for a record in use · `Leaf`
needs `witness=` or every leaf reads the SCORED witness's records (confident causes, wrong page).
🔴 **`PN` NOW FIRES ON 188 LEAVES AND IS UNMEASURED** — GOLD-PAGENUMBER covers OT1-1609-B only.
Plausibility only: digit rate in-family, pagination Spearman +0.47..+0.67. **Do NOT quote it as a
score.** ⚠️ kraken `bbox`-on-`baselines` warning printed throughout the reads = R13.1a touching this
path. 📌 `NT-1582-B` has leaves with roman slant ~11° ⇒ fount abstains there, with a cause.
## ✅ PIECE 1 — ONTOLOGY **DONE 2026-08-29, filed R16.5** (UNCOMMITTED)
`CLASSES` **9 → 15**: `AN` annotation · `OR` ornament · `DC` drop cap · `TB` table/index · `DT`
display title · `CO` colophon/subscription. 🔑 **EVERY NAME COMES FROM ROADMAP R12'S OWN
EIGHT-ARCHETYPE TABLE**, not minted beside it. Archetypes **4 → 8** (D/E/G/H added as R12.2's
contract-as-data); **B2 and F deliberately absent** — both are defined by a boundary WITHIN a leaf
and this agent has no representation for one.
🔑 **ADMISSION RULE = R12.1's**: declared only where the eye review ATTESTS it with exemplar leaves.
**ProseBlock, NoteRef and VerseNumber REFUSED**, refusals recorded in-source with their evidence
(preface prose already names correctly as MT; note-refs/verse numbers are below R14.15's detection
floor and have **zero** findings in 208 leaves).
⚠️ **SCORED WITNESS BIT-IDENTICAL** — 117/121, MN 18/19, RH 20/20, MT 77/80, forbidden 0, A1–A5 PASS.
**That is the point, not a disappointment: no cue emits any new class.**
🔴 **THE GREEN NUMBER, CAUGHT.** Declaring `AN` took `score_foreedge`'s *"CANNOT NAME"* 1 → 0 and
would have flipped its exit 1 → 0 **with leaf 417's box still misfiled**. It now reports **DECLARED
BUT UNREACHABLE** separately and exits 1 on either. Same guard in `visual_agent`'s new **S2b** block:
`6 declared classes with no cue at all — AN CO DC DT OR TB`; `4 of 8 archetypes UNREACHABLE`.
Both counts are **PARSED from `_cue` / `classify_archetype`**, never a hand-kept list.
✅ **SCOPE DISSOLVED: 190 IN / 18 OUT → 208 IN / 0 OUT.** Sir's DECISION untouched; his CRITERION
changed answer — 15 of the 18 said *"table and index rows have no correct answer in CLASSES"* and
those words are now false. `plate_scope` counts the 18 **apart** as READMITTED and says in terms that
they are **not leaves the agent now gets right**. 6 of them now block on **DETECTION or the FRAME**
(NT-1582-B_0034 is frame-anchor: all argument, no body to anchor on). Old reasons preserved per leaf
as `why_2026-08-28`. R16.1's ≥125 bar now MET at 208 — **a bar cleared by a GROWING denominator, so
it is reported with the readmission count beside it.**
➡️ **R16.6** = cues for the six new classes; until it lands R16.5 bought VISIBILITY ONLY.

## ✅ PIECE 3 — DETECTION **MEASURABLE 2026-08-29, filed R16.7** (UNCOMMITTED)
🔑 **THE BLIND SPOT, NAMED**: every scorer here is gold-ENTRY-driven, so it can only visit boxes that
EXIST. A never-drawn box is visited by nothing. `plate_screen` reads `bundle.json` ⇒ blind for the
same reason. **`score_detection.py` reads the IMAGE**: unclaimed ink = ink the page prints that no
region claims. `build_detection_standard.py` grades the eye review **by INK MASS** — SEVERE 7 ·
STRUCT 11 · SMALL 97 · EMPTY 4 — because one recall figure over a missing body column and a missing
catchword averages a solved problem with an impossible one.
✅ **P1 PASS** 7/7 SEVERE in the top 25 of 208, six in the top 8; `OT2-1610-P_0749` **86.2%** unclaimed.
✅ **P3 CONFIRMED NULL** (predicted to fail, in advance): SMALL precision@25 = **24.0% vs 46.6% base**
⇒ anti-correlated. **The sensitivity floor, measured.** Ink coverage CANNOT be the whole instrument.
🔴 **P2 REFUTED 2/4 — DIAGNOSED, NOT TUNED**: the two "empty" boxes hold verso SHOW-THROUGH (0.131/
0.082 ink at `INK_LEVEL` 0.55; 0.022/0.018 at 0.25). `VS.INK_LEVEL` was derived for LINE FINDING.
🔴 **P0 FAILS AND IS NOT PRE-REGISTERED** (added after the first run, marked so): **69/208 leaves lose
>20% of ink to border removal**, four lose >80% — on a tightly cropped leaf THE TYPE TOUCHES THE
FRAME. ⇒ **P1 = 5 solid + 2 unreliable, NOT 7/7** (`NT-1582-B_0321` `OT2-1610-P_0035`).
➡️ **R16.8** = the three defects R16.7 found in its own inputs. Boxes still need DRAWING for E9/E25/
E26/E27; the instrument now says WHICH leaves first.
⚠️ Standard build caught **4 LOCATOR false positives** (`verse 5` · `PSALME.` as a catchword · `body
of the leaf` · `psalm verse`) and **2 broken citations** in my own taxonomy (bare `_1011`/`_0661`
took the wrong witness prefix). 🔑 Rule that fixed it: **SEVERE needs a TOTALITY marker** — a body
noun without `entire`/`whole` is telling you WHERE the defect is, not WHAT it is.
**3 DETECTION**: Surya proposals are the binding constraint; no cue fix reaches
them. 🔑 R14.16 (learned classifier over the cascade) **fixes labelling and leaves detection
untouched** ⇒ it cannot clear a bar defined over *the apparatus on the page*.
🔑 **Reframe to consider**: one instance-segmentation task (image → {region, class}); Surya becomes a
bootstrap for ANNOTATION, not a runtime component. ⚠️ **200 leaves is a good EVAL set and a thin
TRAINING set** — R14.6 forbids the same leaves doing both. ❓ **UNVERIFIED, do not assert**: whether
Surya's layout model can be fine-tuned. Check its training code.

## 🔴🔴 R16.10 — **SURYA SEES THIS FOLIO AT 448×448, SQUARE** (2026-08-29, checked in the package)
⚠️⚠️ **ITS PREDICTION IS REFUTED AND INVERTED BY R16.12 (2026-08-30) — READ THAT FIRST.** The
resize is real and measured; the *consequence* claimed below is not. Tiling fixes **E26**, which
this section says it does not explain, and does **NOT** fix E3/E9/E25/E27, which it says it
predicts exactly. Nothing below is a licence to treat a SMALL family as resolution-caused.

`surya_layout2/config.json` → `"resolution": 448`; `common/rfdetr/predictor.py` →
`TF.resize(t, (448, 448))`. A **1600×2400 leaf is squashed 5.4× vertically and 3.6× horizontally,
ANISOTROPICALLY.** A 20px line of type lands at **~3.7px**; a catchword, a signature or a page number
lands at **1–3px**. 🔑 **R14.15's "DETECTION FLOOR" IS A RESOLUTION ARTEFACT, NOT A MODEL LIMIT** —
and it predicts exactly the eye review's biggest detection families: E3 catchword 59 · E9 note 78 ·
E25 head · E27 signature, all SMALL objects. ⚠️ E26 (body block) is NOT explained by this and stays
a genuine failure. ➡️ **TEST BEFORE TRAINING ANYTHING**: tile the leaf and run the detector per tile
at native scale, merge, re-run `score_detection.py`. No training, no gold, one afternoon.
## 🔑 R16.10b — SURYA'S CHECKPOINT IS UPSTREAM RF-DETR FORMAT
`rfdetr_layout.pth` = `{"model": <510-key state_dict>}`, `arch "rf-detr-large"`,
`class_embed.bias` **[20]**, COCO-style `categories` in `config.json`. `LARGE_ARGS` in
`predictor.py` carries the **full training config** — `set_cost_bbox 5 / set_cost_class 2 /
set_cost_giou 2`, `ia_bce_loss`, LR schedule — so Surya vendored the trainer's args and shipped only
the forward path. Apache-2.0. `reinitialize_detection_head(n)` exists ⇒ **15-class head is a
supported operation.** ⚠️ **ROUND-TRIP UNTESTED**: upstream `rfdetr` is NOT installed. Format-
compatible on every observable; that is not the same as verified.
## 🔴 R16.10c — **"SURYA AND LECTOR AGREE" IS NOT A USABLE SIGNAL**
Measured over 2,275 boxes: LECTOR consumes Surya's boxes **verbatim** ⇒ **geometry agreement is 100%
BY CONSTRUCTION**, i.e. exactly zero information about the half R16.7 proved is binding. On labels
there is **no shared vocabulary**: Surya emits 8 classes here, LECTOR 9, and `Text` splits **738→MN /
424→MT / 132→CH / 110→SG / 88→AR**. ⚠️ **AND IT IS CIRCULAR** — `b.surya in FURNITURE` is a CUE INPUT
at 3 sites, so `PageHeader→RH` 144/144 and `PageFooter→CW` are LECTOR repeating Surya, not
corroborating it. Shared-input agreement is not corroboration.
🎁 **BUT THE SAME COUNT IS A GIFT FOR R16.6**: Surya already emits **Picture ×47** and **Table ×11**
on these leaves, and LECTOR has no cue for either ⇒ every one was named something textual (E12, 51
findings). **`OR`/`DC` and `TB` cues can be written TODAY off `b.surya`** — the signal was always
there and no rule read it, the identical shape as R14.10a's fount.
## ✅ R16.9 — GOLD EXPANSION SAMPLED (`plates/gold-expansion.json`, seed 16090610)
**NT-1633-F 20** (`lowres` ⇒ role text names LAYOUT explicitly) · **NT-1582-M 10** (channel probe:
1-bit CCITT stencil, NOT new-setting coverage) · **OT-1635-M 20 HELD** — role `frontmatter`,
`verse_scope none`; that bar is on the VERSE TEXT and layout is another grain, but `frontmatter` is
an EDITION bar not a resolution bar ⇒ **Sir's call**, and S06's raster is R7.5a-2's open blocker.
**208 → 238 counted, 258 if the 1635 question resolves in favour.** Systematic (random start, fixed
stride) so the sample cannot cluster within a gathering. `split: null` on every row.

## 🧭 R16.11 — HOW THE GOLD SET GETS USED (design, 2026-08-29/30 with Sir; NOTHING BUILT)
**THE ARITHMETIC THAT GOVERNS**: corpus **12,891 leaves** over 12 witnesses; gold 208 = **1.61%**.
R14.6 forbids the same leaves training AND scoring ⇒ **GOLD IS THE EVAL SET, NOT THE TRAINING SET.**
The question is not "train on the gold" but **"manufacture ~10k training leaves the gold can judge."**
⚠️ **SETTING COVERAGE, NOT LEAF COUNT, IS THE GAP**: gold spans 3 settings (1582 NT · 1609 OT1 · 1610
OT2) of 5. **NT-1633 1,543 + OT-1635 2,071 + NT-1582-M 800 = 4,414 leaves ≈ 34% with no gold.**
R16.9 samples them. ⇒ **EVAL MUST REPORT PER-SETTING, NEVER A SINGLE MEAN** (same rule as R12.2's
per-archetype clause). A mean over settings hides the one that fails.
🔑 **BOOTSTRAP, WITH THE INSTRUMENTS AS SELECTOR**: Surya+LECTOR label the corpus → rank by
`score_detection` unclaimed ink → plus LECTOR's **abstentions WITH CAUSE** (37 leaves) → correct only
what is flagged; the rest becomes silver at stated confidence. ⚠️ **NOT "where Surya and LECTOR
agree"** — R16.10c proves that signal is 100%-by-construction on geometry and circular on labels.
⚠️ P3 says unclaimed ink is anti-correlated with SMALL misses ⇒ it may NOT be the only selector.
🔑 **ONE MODEL CANNOT DO THIS.** Sir's LECTOR = ink → rough layout → archetype → **revise boxing** →
read text in box → classify with archetype context → slice to characters. Surya is **RF-DETR: one
feed-forward pass, 300 queries, no state, no conditional logic, and NO CHANNEL to be told an
archetype at inference.** Stage shapes differ:
  1 localise (precise coords) → fine-tuned RF-DETR **at real resolution**, or **Kraken's region
    segmenter** — already in the venv, built for historical print, outputs region types natively.
    ⚠️ **RUN THEM HEAD-TO-HEAD**; Surya's choice of RF-DETR is not evidence for ours.
  2 archetype (whole page, 8-way, coarse) → thumbnail classifier or VLM. Cheap.
  3 **revise boxing given archetype** → THE AGENTIC STEP. A loop, not a model. Nothing off-the-shelf.
  4 classify region (text + archetype) → **VLM on the crop**. R14.16 already notes the TEXT is a
    strong tell consulted for exactly one class.
  5 slices → characters → SCRIBE/kraken (R13.1).
🔑 **THE ASYMMETRY THAT MAKES 4 WORK**: classification TOLERATES OCR error where transcription does
not — argument vs verse vs annotation is a REGISTER judgement (italic, indent, body size, "The
Prophet describeth…") that survives a misread long-ſ. So a VLM may do genre while kraken does glyphs.
⚠️ Recorded gotcha: `qwen3-vl:8b` unusable for OCR here (thinking cannot be disabled).
📌 **READ `AI_OCR` SKILL against these 5 stages** before committing to models — it is the maintained
method map for this ladder and outranks my recall of what is current.
✅ **ACCEPTANCE, THREE NUMBERS HELD APART**: detection recall vs drawn boxes (+ unclaimed ink) ·
per-class AND per-archetype AND **per-setting** accuracy with `n` published · forbidden emissions 0.
⚠️ **THE BAR IS THE CASCADE, NOT SURYA**: LECTOR scores 117/121. A model beating Surya and losing to
the hand-written cascade has NOT earned the swap.

## 🔴🔴 R16.12 — **R16.10 IS REFUTED, AND EXACTLY INVERTED** (2026-08-30, `tile_probe.py`, all 208 leaves)
R16.10 claimed the 448×448 squash *"predicts exactly the eye review's biggest detection families:
E3 · E9 · E25 · E27, all SMALL objects"* and that *"E26 (body block) is NOT explained by this."*
**Both halves are wrong, and the pre-registered FALSIFIER is what found it.** Same checkpoint, same
leaves, 3×4 native-scale tiles, merged; both arms scored by the SAME `score_detection.measure()` on
the SAME image, so only the boxes differ.

| grade | n | median rel. reduction in unclaimed ink | improved |
|---|---|---|---|
| **SEVERE** (E26 body block) | 5 | **+93.3%** | **5/5** |
| STRUCT (E25 head) | 8 | +3.7% | 4/8 |
| SMALL (E3/E9/E27) | 77 | **+7.3%** | 41/77 |

Every SEVERE leaf, individually: `OT1-1609-P_1011` 0.822→0.004 · `OT2-1610-P_0024` 0.764→0.107 ·
`_0026` 0.683→0.077 · `_0749` 0.862→0.004 · `_0821` 0.610→0.041. These leaves were losing **61–86%
of their entire ink** to no box at all; tiling recovers essentially all of it.

🔑 **SO THE PREPROCESSING BUG IS REAL BUT IT OWNS THE OPPOSITE DEFECT.** Tiling fixes the SEVERE
family — the most damaging detection failure in the corpus, the scripture column itself unclaimed —
completely and for free, with no training and no gold. It does **NOT** fix the small objects.
⚠️ **AND THE SMALL FLOOR IS NOT A RESOLUTION FLOOR.** In a tile the reduction is ~2.3× rather than
6.9×/9.7×, so a catchword arrives at ~17px instead of 1–2px and is *still* not emitted. **R14.15's
floor stands, and this run re-attributes its cause: the limit is SURYA'S CLASS INVENTORY, not its
pixels** — it has no catchword and no signature object to emit at any scale. That is a
fine-tuning/new-head problem (R16.10b's `reinitialize_detection_head`), not a preprocessing one.
🔑 **P6's BLOWOUT ALSO VALIDATES THE INSTRUMENT P5 FAILED ON.** The standing worry was that
unclaimed ink is confounded by the baseline's coarse boxes (one box covering 40.7% of the leaf
claims ink indiscriminately). If that confound were the whole story SEVERE could not have scored
+99%. The measure registers a genuinely recovered object; **P5's failure is therefore a finding
about small objects, not an artefact of the statistic.**
✅ **AND THE OVER-BOXING HALF MOVED THE RIGHT WAY**: median slack **0.4164 → 0.3804** (P7 bar was
"must not rise by 0.05"; it FELL by 0.035), boxes 10→22, small boxes 7→15. Tighter AND more
numerous, so the SEVERE gain is not bought by spraying boxes over the page.
⚠️ **PER SETTING, because a pooled mean hides a regression**: `NT-1582-B` unclaimed **0.0064 →
0.0417**, a 6.5× WORSENING on 11 leaves, against `OT1-1609-P` 0.0147→0.0174 and `OT2-1610-P`
0.0109→0.0213. **Tiling is not uniformly safe and must not be switched on globally on this
evidence.** 🔴 OPEN.
⚠️ 69 of 208 leaves excluded as border-mangled (P0, unchanged and still open); 121 adjudicated.
Secondary, unadjudicated: those 69 show median **−7.5%**, i.e. worse.
## 🔴 R16.12a — MY OWN GROUPING WAS MIS-ADDRESSED ON THE FIRST RUN, AND IT SILENTLY EMPTIED THE FALSIFIER
Run 1 selected groups with a **regex over the E-codes in `eye-findings.json`**. E24–E28 were minted
from the readers' verbatim strings AFTER they worked, so **no finding string carries them** — the
file's own `_provenance` says exactly this — and the SEVERE group came back **EMPTY**. Run 1
printed `P6 🔴 FAIL` for a leg that **had zero leaves in it**. ⚠️ **A LEG THAT CANNOT BE PUT AT RISK
IS NEITHER PASSED NOR FAILED**; `tile_probe.py` now carries three verdict states and a minimum-power
floor, and reads `detection-standard.json` — **running the project's own enumeration instead of
reimplementing it**, which is the same defect shape as the gold-addressing rule. The bars were not
touched by the correction; run 1's numbers are kept in the script's docstring.

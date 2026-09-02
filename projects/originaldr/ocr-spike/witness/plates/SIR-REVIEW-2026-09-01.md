# Sir's structural review, 2026-09-01 — SIX SUBAGENT FINDINGS + REPORT PLAN (IN PROGRESS)

✅ **STATE: ALL 6 AGENTS REPORTED.** Findings 1-7 below.
✅ **DELIVERABLE WRITTEN AND PUBLISHED 2026-09-01** — 2nd edition at
`/artifact/851b1c1f-4991-4bfa-b41a-1d8a628a3f08` (same URL). 17 sections + glossary, 22 rendered
plates, 8 inline SVG diagrams, 118 KB markup / 3.24 MB with images.
Build sources (session scratchpad, EPHEMERAL — copy into repo if they must survive):
`57a5a9c2-…/scratchpad/build/p0..p6.html` + `fig/*.jpg`, assembled by inline base64 substitution
into `originaldr-review-2.html`. Section map = the REPORT PLAN below, executed in full.
🔑 **PLATES ARE RE-RENDERED FROM SOURCE at w=1100 q46** by `57a5a9c2-…/scratchpad/render_hi.py`
(house style: slate boxes · rubric largest/anchor box · amber head_y/foot_y/measure; bespoke recipes
for numbered 0666, partial-overlap bands, contained-pair highlights). **That script is the thing to
keep** — it regenerates every plate at any width from `bundle.json`. Click-to-zoom overlay verified
live in Chrome (open, Esc-close, focus return, zero console errors).
🔴 **FIGURE-CAPTION CORRECTION**: the old `plates/headband-cuts.jpg` shows a **CORRECTLY** placed
frame, not a collapsed one — my 1st-edition caption misdescribed it. §XI now pairs
`OT1-1609-B_0409` (anchor area **0.609**, head 0.067 / foot 0.908 / measure 0.087–0.811) against
`OT1-1609-P_1011` (anchor area **0.022**, foot **0.201**, measure **0.795–0.936**). `HEADBAND` is
retired from the figure set. ⚠️ Caption written from a filename, not from the image — the exact
failure Sir's visual-first rule exists to prevent.
Sir: *"go overboard rather than cutting short"*, *"diagrams and figures in EVERY section"*, *"too many figures,
giving examples and counterexamples and variants"*.

## 🔴 SIR'S STANDING CORRECTIONS THIS SESSION (both saved to L2)
1. **"I can't understand what I can't look at."** → Masterplan §0.2a GOVERNING (filed) +
   `feedback_show_dont_tell_visual_first`.
2. **Prose: my ≤15-word rule collapsed into APHORISM.** Sir named the offenders ("a line is being asked to
   decide a kind", "each finding was true and locally scoped", "a capability named only inside a list…").
   **Short sentences ≠ short explanations.** Every conclusion needs its concrete case. Scope correction
   appended to `feedback_prose_style_sir`. **The report must EXPLAIN, not aphorise.**

## ✅ FINDING 1 — THE ARCHETYPE IS INERT (agent C, full 1411-line trace). THE HEADLINE.
`_cue()` (L924-1110) **never reads `lf.archetype`** — not once. `name_regions()` (L1113-1124) uses it for ONE
thing: if label ∈ archetype's `forbids`, overwrite with `??`. It can only DELETE, never inform.
🔑 **And the veto is self-satisfying ⇒ PROVABLY DEAD CODE**: archetype is derived FROM the cue counts it then
constrains. Any box cueing MN ⇒ archetype B1/BC, neither forbids MN. The 6 classes still forbiddable
(AN/ORN/DROP/TBL/DISP/CO) have **no cue that emits them**. `requires` is data with **no consumer**.
**Confirmed absent, exhaustively**: no box ever moved/resized/split/merged (x0..y1 written only in 2
constructors); **no iteration**; **no weighting** — every decision hard if/else, `b.conf` **read by no branch**;
text read for **1 class** (PN); **no expected counts**; **no verso/recto prior**; **no cue looks at another box**.
Cascade terminates in **MT default conf 0.55** = the `fail-safe toward body` the header claims to retire; MT is
containment ⇒ wrong label scores CORRECT.
📌 **CORRECTION TO MY EARLIER CLAIM**: `if off <= 0.5` is NOT a magic number. `centre_offset` is scaled by the
BOX's own width, so `off<=0.5` is the exact geometric statement *"the measure's centre-line falls inside this
box."* Retract that item from R16.13. `PIVOT_X=0.5` also provably does not affect ordering.
📌 **ROTATION ANSWERED**: `ry()` = **shear approximating page-slant rotation**, NOT rescale/squish. Nothing is
scaled; no coordinate is changed; applied at comparison time only. Angle from `gold/skew_*.json` per leaf,
range **-2.39°…+2.75°**; at +1.6° drop across the page ≈ one line of type.
📌 Order is `see → attach_skew → frame → attach_fount → attach_reading → classify_archetype → name_regions`
(skew BEFORE frame — I had it wrong).
📌 18 cue branches mapped, positional vs object-intrinsic tabulated. Only branches 1-2 (AR/fount) are
typeface-driven; only 5-7 (PN) text-driven. **Full branch table is in the agent transcript** —
`/private/tmp/claude-501/-Users-nathanielcannon-Claude-Project-Aion/a51b9eb3-76c3-44f6-a0b9-6f8a44ecd2cb/tasks/ae7a3b63499e86234.output`

## ✅ FINDING 2 — "ONLY 7 SEVERE" IS A PHRASING ARTEFACT (agent A)
`build_detection_standard.py` **never reads an image**; regexes reviewer phrasing, needs totality-word + noun
from a **scripture-only** list. `NT-1582-B_0778` (*"the entire two-column liturgical table is UNBOXED"*, 0.666
unclaimed) and `NT-1582-B_0803` (entire glossary unboxed, 0.308) excluded because *table*/*glossary* aren't in
`_BODY`. **True count ≥9/208.** Fix: add block nouns, or seed from the image measure.
**THREE SUB-CAUSES, not one**: (A) *gloss column becomes the page* — 1011/0749/0821, no body box at all, frame
anchors the marginal strip, measure width <0.30 (only 5 leaves in 208; 3 are these); on 0821 **all 15 labels =
MN**. (B) *Psalms interleaved setting collapses* — 0024/0026/0035, 4-8 boxes only. (C) 0321 drop-cap head
detached — **probably misgraded**.
🔴🔴 **THE DECISIVE CONTRAST — IT IS NOT THE RESIZE.** `OT2-1610-P_0022/0023` vs `_0024/_0026`: SAME forme, SAME
2314×2963 scan, SAME plate ⇒ **23/20 boxes vs 5/4**. Leaf 34 vs 35: 17 vs 8. Nothing about the page changed.
⇒ hypothesis = **proposal starvation / confidence-threshold collapse under RF-DETR's fixed query budget**, not
resolution. **A missing body box then MANUFACTURES a page-wide labelling defect** and the label scorers are
structurally blind to the cause.

## ✅ FINDING 3 — CONTAINED PAIRS ARE MOSTLY NOISE (agent D). CORRECTS MY "19%" FRAMING.
161 contained pairs. **≤12 (7.5%) are legitimate nesting** (drop-cap `Picture` in `Text` — verified visually,
Mark 1 initial, `NT-1582-B_0119`). **96/161 are SAME-class** (body inside body) = impossible as structure.
**39 are PIXEL-IDENTICAL rectangles emitted twice under CONFLICTING class heads** (IoU≥0.999). Families:
A exact-dup 47 (29%), B ragged same-class re-detection 48 (30%), C small-in-big 62 (38%, of which only the 12
Picture ones legitimate; the Text←Text ones are **outer-box overruns swallowing a neighbour region**).
⇒ **~59% is detector noise. Z-ordering them would be LAUNDERING.** Repair = dedup + shrink, not order.
**Sir is right: box-in-box should not exist by design, except a non-text object inside running type.**

## ✅ FINDING 4 — 0666 = ONE BOX PER VERSE, EXACTLY (agent D)
26 boxes, 22 `Text`; body carries **17**. Page prints Lam 3:58-66 (9) + CHAP head + Lam 4:1-8 (8). **9+8=17.**
Boxes abut (gaps -0.011…+0.001), heights cluster at 2-line (0.044-0.050) and 3-line (0.067-0.070). **All 17
swallow the verse number AND the marginal acrostic letter.**
🔑 **CAUSE = GRANULARITY MISMATCH: Surya `Text` is a PARAGRAPH region, not a column.** Verse-per-paragraph
setting ⇒ one box per verse. **Not rare: ≥10 Text boxes on 59/208 (28%)**; 0666 is rank 1/208 (22).
✅ **CONTROLLED PAIR**: `OT2-1610-P_0668` (2 leaves later, ch.5 set as CONTINUOUS PROSE) = **clean, ONE body
block, 9 boxes**. Same book, same setting. Rendered.

## ✅ FINDING 5 — THE PLATE TOOL IS NOT READY (agent B). THREE BLOCKERS.
1. 🔴 **NOTHING READS THE EXPORT.** `gold-layout-corrections.json` appears **once in the whole tree** —
   `review.html:395`, the write. **Zero readers.** Every consumer reads `bundle.json`. `--rename` refuses
   geometry; `--build` would silently OVERWRITE corrections. **It produces a JSON nobody reads.**
2. 🔴 **No ACCEPT state, no window datum.** Verdicts are clean/corrected/defect; `review-verdicts.json` has
   zero readers and **records no geometry**. The accepted-leaf window Sir wants **does not exist anywhere**.
3. 🔴 **Archetype, frame (head_y/foot_y/measure), skew and the class inventory are NOT editable.** 4 of 8
   archetypes are unreachable by the classifier and a human cannot override ⇒ wrong FORBIDS set inherited.
Also: **zoom broken >1.0** (`transform:scale` doesn't grow scroll extent); **only the bottom-right corner
resizes** — but PARTIAL-overlap repair is a LEFT/TOP edge move ⇒ *the tool paints the defect it cannot fix*;
**no undo**; **geometry never checkpointed** (only verdicts) ⇒ worst partial loss; checkpoint lands in
`~/Downloads` and nothing moves it; `prog()`'s "NOT YET ON DISK" alarm never resets ⇒ trains reviewer to ignore
it; **detection grade never shown** to the reviewer; no filter/sort/next-unreviewed; no merge/split.
**WINDOW hardcoded in 3 LAYERS**: (1) `VA.WITNESS`/`LEAF_LO,LEAF_HI`; (2) a 2nd copy in
`score_surya_layout.py:53` + six bare `range(400,420)`; (3) 🔴 **12 of 17 files in `witness/gold/` carry
`_400-419` IN THE FILENAME** ⇒ a DATA MIGRATION, not a code change. `skew` has no per-witness variant.
**Build list (agent's tiers)**: T0 `plates/gold-layout.json` (accepted record WITH geometry) · `plate_gold.py`
(the reader nobody wrote; reject `??`, reject non-CLASSES, refuse if bundle hash changed) · an ACCEPT verdict ·
`is_gold(witness,leaf)` replacing LEAF_LO/HI · checkpoint geometry. T1 editable archetype/frame · all-corner
resize · export validation · surface detection grade. T2 keys · filter sidebar · undo · per-class colour ·
merge/split · in-session overlap recompute · fix zoom · resolvable flags · PROPOSE-CLASS channel.

## ✅ FINDING 6 — MODEL LANDSCAPE (agent E, cited)
**RF-DETR CANNOT take priors at inference.** Queries are learned params; DAB-DETR anchors and DN-DETR
denoising are **training-time only**. `reinitialize_detection_head` **verified real** (`rfdetr/models/lwdetr.py`)
but it is fine-tuning, changing *what labels it can emit*, not *what it expects*. Known bugs: issues #51, #330,
1.6.0 fix.
**Alternatives**: Kraken `blla` + SegmOnto (fully retrainable typology, historical-print home turf; weakness =
same-class neighbours merge, which is exactly body-vs-gloss ⇒ YALTAi exists for that). PP-DocLayoutV2/V3
(RT-DETR + pointer net, **gives reading order**, OmniDocBench 93.56 vs DocLayout-YOLO 87.29). LayoutLMv3/DiT =
classifiers GIVEN boxes ⇒ natural cascade replacement. Docling reading order unreliable multi-column.
**Grounded VLMs (accept priors in the prompt, return real coords)**: Qwen2.5/3-VL (absolute-pixel `bbox_2d`),
Florence-2 (MIT, 0.23/0.77B, `<CAPTION_TO_PHRASE_GROUNDING>` = **feed a prior, get boxes**), PaliGemma 2
(`detect {desc}`), Molmo/MolmoPoint, Kosmos-2 (superseded).
🔑 **qwen3-vl thinking-lock is CHECKPOINT-TEMPLATE × SERVING-VERSION, not the model family.** `mlx-vlm` exposes
`--enable-thinking` defaulting **OFF** ⇒ **RETEST via MLX before writing Qwen off.** Update
`reference_qwen3vl_thinking_lock` when tested.
**3 candidate pipelines**: A = class-agnostic proposer + prompted VLM classifier/refiner + structural validator
(**recommended pilot**); B = Kraken blla retrained w/ SegmOnto (+YALTAi); C = hybrid, VLM only on pages failing
the validator (best economics at 12,891 leaves).
**Prior art for expected-counts**: 1990s page grammars (Conway; Krishnamoorthy least-cost parse), DocParser
(arXiv:1911.01702) grammar-repair, Detect-Order-Construct (2401.11874), UniHDSA (2503.15893), **PARL
(2601.07620) encodes "a page number sits at the layout edge" as a learned spatial prior**. ⚠️ No maintained OSS
tool does hard runtime count-CSP ⇒ build a **post-detection validator** instead.
⚠️ **UNVERIFIED**: VLM grounding accuracy on dense early-modern print. **Pilot on 10-20 gold leaves first.**

## 📐 MY OWN MEASUREMENTS THIS SESSION (not from agents)
**Positional priors, 90% containment, from the 208-leaf gold** — the empirical basis for Sir's argument:
`RH` x[.422,.576] y[.016,.062] · `PN-verso` x[.180,.252] y[.017,.057] · `PN-recto` x[.730,.822] y[.022,.066]
(**perfectly bimodal = recto/verso alternation, 61 L / 54 R**) · `CW` x[.540,.864] y[.759,.964] ·
`MT` x[.262,.672] y[.112,.832].
🔴 **PN is missing on 93/208 leaves = 45%** — for "the easiest class of all". 🔴 **>2 MT boxes on 87/208 =
41.8%**. 🔴 **Only 11/208 (5.3%) leaves are CLEAN** (0 partial pairs, unclaimed<.02, 1-2 MT, body>0.25).

## 🖼 FIGURES ALREADY RENDERED (scratchpad `/private/tmp/claude-501/-Users-nathanielcannon-Claude-Project-Aion/4f0e3081-42e6-4621-9092-e745c38866e8/scratchpad/`)
`plates/` e26-before · e26-after · headband-cuts · partial-overlap (+ `.b64` ready) ·
`severe/` all 7 SEVERE · `contrast/` 0022 vs 0024 (same forme, 23 vs 5 boxes) ·
`good/` 0668 + 1085 (counterexamples) · `diag/` q1_0666 numbered + 6 contained-pair examples +
`contained-pairs.json`. **Encode at w=720 q70 → base64 data URIs (CSP blocks external hosts).**
Old page template: `scratchpad/originaldr-review.tpl.html` (placeholders `@@NAME@@`), builder pattern in history.

## 🧭 REPORT PLAN (Sir's own six groups for next steps)
`re-align vision→capability · MVP every pipeline stage · build out Plate Tool · iterate LECTOR · manual Gold
Set · connect LECTOR→SCRIBE`.
Sections: I vision-vs-machine · II full LECTOR decision map (**needs a big SVG flow diagram**) · III archetype
inert · IV all 9 SEVERE leaves · V why the body vanishes (contrast pair) · VI paragraph≠column (0666 vs 0668) ·
VII overlaps are noise · VIII the 11 clean counterexamples · IX priors measured · X why the metric rewards
nonsense (**needs agent F**) · XI head band + rotation explained plainly · XII Plate Tool audit · XIII bounded
searches explained concretely · XIV model landscape + 3 candidate pipelines · XV the six-group plan · XVI two
decisions. **Plus a glossary rewriting each of my aphorisms into plain English.**


## 🔴🔴🔴 FINDING 7 — THE BODY BLOCK IS DETECTED, THEN DELETED BY A HARD-CODED 0.40 (agent F). **THE ROOT CAUSE.**
`surya/settings.py:136` `FAST_LAYOUT_CONFIDENCE_THRESHOLD = 0.4`; applied at `common/rfdetr/predictor.py:191`
`keep = res["scores"] > threshold`. **Every call site in this project constructs `FastLayoutPredictor()` bare** —
`visual_agent.py:1178`, `plate_book.py:185`, `score_surya_layout.py:108`, `rung1_surya.py:59`,
`tile_probe.py:241` — so **0.40 is live everywhere**.
**Agent re-ran the detector on the SEVERE leaves. THE CORRECT BODY BOX IS PRODUCED ON 5 OF 7 AND THEN CUT:**
| leaf | body box area | score | verdict |
|---|---|---|---|
| `OT1-1609-P_1011` | 0.637 | **0.393** | cut, by **0.007** |
| `OT2-1610-P_0024` | 0.733 | **0.395** | cut, by **0.005** |
| `OT2-1610-P_0821` | 0.651 | **0.394** | cut, by **0.006** |
| `OT2-1610-P_0749` | 0.804 | 0.370 | cut |
| `NT-1582-B_0321` | 0.330 | 0.319 | cut |
🔑 **THREE MISS THE FLOOR BY LESS THAN A HUNDREDTH.** `threshold=0.10` recovers all five.
🔑 **CAUSE OF THE LOW SCORE IS DOMAIN SHIFT, NOT SIZE**: same detector scores **0.919** on a modern-ish leaf
(OT1-1609-B 409). The model is **right but uncertain** on 1609 blackletter + gloss + show-through. A floor
calibrated on modern documents is a guillotine here, and it cuts the LARGEST object hardest because that is the
one whose delimitation is most ambiguous (on 0749 three nested body variants split the mass, 0.18-0.44).
🔑 **TWO-STAGE FAILURE**: floor deletes the body → `frame()`'s `max(area)` promotes a fragment → whole leaf's
labelling corrupted. On 0821 a spurious right-margin strip scores **0.533** and BEATS the true body's 0.394 ⇒
measure=(0.828,0.978) ⇒ **all 14 real regions labelled MN**.
📌 **SO: THE RESIZE EXPLAINS CATCHWORDS/SIGNATURES ONLY.** At 448 with DINOv2 `patch_size:16`, one token = ~156px
of original page; a ~30px catchword is ~3px = sub-token ⇒ genuinely unrepresentable. The body at 448 is still
~300×390px over ~19×24 tokens ⇒ **resolution was never the body's problem. Sir was right.**
📌 **NO NMS ANYWHERE**: `grep -rn "nms" surya/` = **zero matches**. Only suppression is sigmoid top-k + the floor.
📌 **`num_queries`=300, `num_select`=100 (`predictor.py:88-89`)**, and top-k is over the **flattened (query×class)
6000-cell matrix** ⇒ **one box can consume several slots under different labels**. THIS IS THE SOURCE OF THE 39
PIXEL-IDENTICAL DUPLICATE RECTANGLES in Finding 3. Cap saturates at n=100 when threshold=0.01.
📌 **19 CLASSES** (not 20; 20th logit is a spare from head re-init). Full list captured. **No catchword, no
signature, no marginalia, no verse-number class.** Catchword AND signature can only come back as `Page-Footer`.
`reinitialize_detection_head` **exists** (`common/rfdetr/models/lwdetr.py:114-127`) but **tiles/truncates existing
weights** — it is a shape-fixer for loading, not a way to add a class. Package is **inference-only**: no loss, no
matcher, no training loop shipped.
## 🔴 FINDING 7b — THE METRIC CANNOT DISTINGUISH GOOD SEGMENTATION FROM TILING (agent F)
`unclaimed` = set-union coverage recall over the MERGED mask ⇒ box identity/count/label/overlap destroyed before
the number forms. For ANY rectangle set covering the ink, unclaimed ≡ 0. **A 12×12 grid of tiles scores
unclaimed≈0, max_slack≈0, max_gutter≈0 — a PERFECT score on all three from a segmentation carrying zero
information.** Slack/gutter are **maxima over boxes and monotone-DECREASING in box count** ⇒ over-segmenting
IMPROVES them. **No term in the file is increasing in |R|.** ⇒ the instrument's gradient points at nonsense.
🔑 **The two ideas ARE crossed, exactly as Sir said**: "minimise ink not in a box" is a property of a UNION;
"one box per region, covering nothing else" is a property of a CORRESPONDENCE. No aggregate over a union can
express a matching. **Hence 0.822→0.004 is TRUE and MEANINGLESS.**
**PROPOSED REPLACEMENT — adopt PQ@IoU0.5 reported as SQ×RQ**, with fragmentation ratio φ (predictions materially
covering one gold region; ideal 1) and its dual the merge ratio (= E5/E13, catches the swallowed margin note
WITHOUT the gutter geometry P4 was refuted on twice). IoU-matched F1 also kills both degenerate cases; per-box
precision does NOT (a tile inside one gold region scores 1.0). ⚠️ **BLOCKER: PQ needs gold REGIONS and
`detection-standard.json` is a per-leaf severity GRADE with prose, not a box set.** ⇒ this is exactly what the
Plate Tool must produce. **Until then no formulation over the current standard can tell a segmentation from a
tiling** — state that plainly rather than inventing a third statistic against the same 208 leaves.
📌 Measurement bug: `claimed` uses FILLED rectangles but per-box stats use `sub=mask[...]` ⇒ overlapping boxes
double-count ink in slack/gutter/density while contributing once to the union. Not hypothetical (dup rects).
## 📌 FINDING 7c — ROTATION, ANSWERED, PLUS A REAL BUG
`ry` = **vertical shear ≈ rotation for page slant. No rescale, no squish, no coordinate changed.** Answers "how
far down the page is this, measured along the direction the TYPE runs, not the photograph's edge?" Two points on
one printed line get the same `ry`. `PIVOT_X=0.5` is the hinge where ry==y; it does not affect ordering.
Angle from `build_skew_record.py:60-89`: OLS slope of glyph **bottom edges** (baseline proxy) vs x, per row,
≥6 components/row, ≥5 rows, clamp 8°, take the **median row angle**. NOT `slant_mode` (that is glyph lean).
**BUILT record range: −0.901° (leaf 410) to +1.636° (leaf 409), median +0.14°.** At +1.6° on a 3092px width the
drop is ~86px ≈ one full line.
🔴 **(a) ROTATION IS NOT ACTIVE ON THE PLATE CORPUS.** Only `skew_OT1-1609-B_400-419.json` exists ⇒ **all 208
plates carry `skew:0.0, skew_seen:false`**, including all 7 SEVERE. So the head/foot rules that cut bodies are
PLAIN HORIZONTALS; those cuts are the frame collapse, not rotation error.
🔴 **(b) `ry` OMITS THE ASPECT FACTOR — over-rotates ~1.41×.** Angle fitted in PIXEL space; applied in
per-axis-NORMALISED space. Correct term is `tan(θ)·(W/H)·(x−0.5)`. For 3092×4367, W/H=0.708 ⇒ leaf 409's +1.64°
is applied as +2.31°, ~36px excess at the edge. Same sign as the correction so it never showed as a regression;
error factor VARIES PER WITNESS since page_px varies. **NOT APPLIED — one-term fix, needs the leaf's aspect.**
## ➡️ AGENT F'S RECOMMENDED ORDER OF ATTACK
1. **Pass `threshold=0.10-0.15` explicitly at the 5 call sites** (highest leverage in the project, one line each)
   — **AND add class-agnostic NMS at the same time**, or the lower floor hands you the duplicates.
2. Make `frame()` **fail loudly** — if the largest box covers < some share of the leaf's ink, ABSTAIN with a
   reason instead of anchoring the measure on a corner strip.
3. Fix `ry`'s aspect factor. 4. Re-express the metric as PQ (blocked on gold regions). 5. Catchwords/signatures
   need a different instrument — no class exists and at 448 they are sub-token; **that is the one place
   resolution really is the answer.**

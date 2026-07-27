# OriginalDR reOCR — Master Development Map (2026-07-22, rev 2)

**Status:** consolidates + supersedes the tactical plans. Source spec = `SIR-DIRECTIVE-2026-07-19.md`.
Rev 2 folds in Sir's 2026-07-22 directives + a corrected witness-divergence finding. Development map from
current state → a finished, tested, corpus-scale reOCR pipeline over **S1, S3, S4, S6, S8, S9 only**.
Every claim is empirically grounded this session; superseded beliefs marked **[WAS-WRONG]**.

---

## 0. What changed (rev 2)

- **[WAS-WRONG] "Witnesses are noisy (s_dismas 0.80 vs Gold)".** FALSE — it was a span/alignment artifact.
  Measured cleanly: s_dismas **contains 0.9959** of genesis-24 Gold, 0.9948 of psalms-118 Gold. Between-witness
  (full-verse, same cut): archaic↔archaic (s_dismas↔odr_com) **0.994–0.9994**; modern↔modern (janvier↔madueke)
  **0.9996–0.9999**; archaic↔modern surface ~0.95, content ~0.98. **Witnesses are ~0.99 faithful. NOTHING is
  demoted on comparison scores.** The 0.80 came from comparing page-partial Gold to full-verse witnesses without
  reconciling boundaries → the SAME alignment defect that made per-verse OCR look like 0.47.
- **[DONE] Draft-gold addresses fixed by content-anchoring:** 2esdras-07 974→**994** (0.974), colossians-3
  null→**jp2-S08 571** (0.994), proverbs-16 null→**292** (0.947, poetry layout — verify in review). Stale `raster`
  fields cleared.
- **[DONE] GT review-tool raster bug fixed** (`gt_review_server.py`): now renders the jp2 page **on-demand** from
  `(ocr_dir,page_index)` (handles int + multi-page-list), so newly-added drafts/matter display. Server restarted.
- **[DECIDED, Sir] Retire `ocr_consensus` entirely** — do not rebuild, do not use. Cross-source **divergence**
  (not a fabricated consensus text) is the routing signal. Remove it from qc_audit/report/reads.
- **[DECIDED, Sir] All 15 scripture + 31 matter GT = current-best Gold NOW.** Drafts are not gated on review;
  when Sir submits corrections, fold + re-standardize (GT-2) and rebase future rounds. 12 scripture are
  Sir-reviewed, 3 are Jarvis-draft-addressed, all count.
- **[CLARIFIED] Cross-source disagreement gates IN (flags loci needing work), never OUT (never accepts a reading).**
- **[CLARIFIED] Escalation ladder has a defined TERMINAL state** (human review + approach-redesign alert), not an
  infinite loop (see §7–8).
- **[CARRIED] six-source purge; verse-seg broken (0.96 containment hid 0.47 per-verse); fine-tune 100% S1;
  matter excluded from train/eval; janvier=`sabates_a`; S9 incomplete (OT2 un-OCR'd).**

---

## 0.5 — M2 verse-seg engine: BUILT + VALIDATED (2026-07-22, rev 3)

`verse_seg.py` (engine, VS-1..4) + `verse_seg_eval.py` (VS-5 harness) built and validated on the two gold
loci. This is the §5 linchpin, now empirically grounded. **The metric redesign caught a real defect the old
metric masked** — the whole point.

- **[PROVEN] janvier-cut removes the boundary artifact.** genesis-24 witness identity (gold↔s_dismas, hold
  text constant, vary only the cut): **OLD two-grid 0.638 → NEW janvier-cut 0.938 (+0.30)**, pass@.90 2/19→17/19.
  Psalms had little artifact to fix (short one-line verses → GT-tag ≈ native cut already; 0.9415 both).
- **[PROVEN] per-verse identity now TRACKS page quality (real R2 fine-tuned OCR, janvier-cut both sides):
  genesis-24 archaic-id 0.9557 (15/19 ≥.90); psalms-118 0.9362 (8/12).** Clean verses ~1.0, mis-RECOGNISED
  verses score low → route to R3. Psalms residual is 3 genuine R2 recognition errors ("It bridet IF", "fcete",
  dropped "ô"/truncation) + 1 catchword leak ("E Depart") — NOT segmentation. Per No Silent Degradation these
  stay OPEN → R3/M4, never masked to hit 0.95.
- **[PROVEN] VS-4 length-sanity:** genesis v30 (`24:30a`, a cross-page fragment only partly on the page)
  correctly flagged OPEN(len-short 0.29x); v12 (`24:12b`) is the matching lead fragment. All other spans clean
  (len_ratio 0.98–1.11; psalms 0/12 OPEN). gold-content vs janvier: psalms 0.982, genesis 0.98+ (ex-partials).
- **[NEW CAPABILITY 1 — acrostic paratext strip]** `sabates_a` INLINES the Hebrew-letter acrostic markers +
  gloss ("Nun. Everlasting. …") into section-initial verses (Ps 118 v=8k+1); DR witnesses+gold segregate them
  to apparatus. `strip_acrostic_paratext` normalizes the janvier grid to body-grain (closed 22-letter set,
  zero false-strip risk verified). Fixes v105/v113 (0.68→1.0). Also relevant to Ps 111/112, Lamentations, Prov 31.
- **[NEW CAPABILITY 2 — janvier-as-apparatus-filter]** `drop_apparatus`: a contiguous run of ≥N page tokens
  anchoring to NO janvier token IS interleaved apparatus (footnote/annotation) → excised. **Solves the psalms
  central-column-footnote body-isolation that pure-geometry `layout.py` cannot — WITHOUT Surya/geometry**
  (psalms R2 0.298→0.936; genesis unaffected 0.956→0.958). Partial answer to §11 SEG for the interleaved mode.
- **[FINDING — witnesses are NOT uniformly ~0.99]** contra §0/§9's "~0.99 faithful": `s_dismas` carries `\hfil`
  LaTeX artifacts from its pdftotext origin (leaked into v112 tail); `odr_com` psalms-118 versification is
  broken (175 verses spanning range 1..207 → gaps that shift janvier-cut alignment, witness-witness craters to
  0.0/0.26 at some verses). The janvier-cut METHOD is sound (gold-content 0.982); the ~0.99 witness-witness
  claim in §9 needs qualification per witness text quality. Affects DIV (§9) + divergence-as-routing (§7 alarm 2).
- **[HARDENED — code-review 2026-07-22]** Adversarial review (ran the code) found 3 real boundary-math bugs,
  all now FIXED + regression-guarded in the self-check, with the validated numbers UNCHANGED (psalms 0.9362,
  genesis 0.9557 identical pre/post): (#1, No-Silent-Degradation) un-anchored verse start was a GLOBAL
  proportion that could land inside a good neighbor and silently truncate it (v49 0.536→1.0) → now placed
  LOCALLY within the bracketing anchors, can never encroach past a real anchor; (#2) scattered high-frequency
  words ("the"/"of") let unrelated prose localize (Gen24→Ps118 gave 32 verses) → localization now requires
  CONTIGUOUS matching blocks (`block_min=3`; 32→1, no real-page regression, tuned by sweep — 4+ drops real
  verses); (#4) `segment()` now `sorted(cverses)` (was order-trusting). REMAINING (documented, not silent):
  #3-edge — on a MULTI-chapter page the first/last verse absorbs out-of-chapter lead/trail; large bleed is
  len-flagged OPEN (never silent), small (<apparatus_min) leaks are a minor edge residual → real fix is
  chapter-splitting the OCR body upstream (§11 SEG / addressing), and the single-chapter contract is documented.
- **[OPEN → next]** psalms body-isolation still leaks a 2-token catchword (layout.py §11 SEG-2 tuning); the 3
  recognition-error verses are M4 (recognizer) / M5 (R3) territory. Wiring `verse_seg` into the report pipeline
  = M3 (REP-2/3). GT-3 gold-expansion + DIV-1 witness matrix still owed for full M2.

Artifacts: `verse_seg.py`, `verse_seg_eval.py`, `.verse-seg-eval-ocr.json`. Both modules self-check (`python
verse_seg.py` / run the harness). Gold-free by construction (janvier covers 76 books); gold only validates.

---

## 1. Governing principles

- **P1 Gold-free production.** Every stage runs on any curated `(ocr_dir,page_index)`. `jp2_page.py` enforces
  `CURATED={S1,S3,S4,S6,S8,S9}` (KeyError otherwise) — keep as the hard gate. Gold used ONLY for eval + offline
  calibration.
- **P2 Six sources ONLY, everywhere** (train/test/prod/report/divergence). No S2,S5,S7,S10–S15 or derivatives.
  Physical purge preferred over pollution risk.
- **P3 No Silent Degradation.** Below-bar stays OPEN, blocks the deliverable, ALERTs for approach-redesign; never a
  terminal "accepted". Cross-source AGREEMENT is never a pass; cross-source DISAGREEMENT only routes/flags.
- **P4 ſ surface-safe.** NFC (never NFKC), no dict/LM, ſ-count companion, ſ by glyph not position.
- **P5 Metric concepts are fixed; harmonize STRUCTURE.** Two identity axes (content, surface), archaic-preeminent.
  Containment = localization guard, not identity. **Cut BOTH sides of every comparison by the same janvier grid**
  (this is the linchpin — see §5).
- **P6 janvier is the interval authority** (localization / presence / verse & apparatus boundaries), via USFM
  `\c`/`\v` — complete + machine-precise, even though modern. s_dismas/odr_com are primary for archaic
  surface/content where present; where they gap (8,384 loci / 22.6% / 17 books) janvier/madueke are primary for
  content+surface too.
- **P7 Matter is first-class** (OT1/OT2/NT front+back as "books"): GT'd, trained, eval'd, reported; apparatus-grain
  (containment), not verse-grain.
- **P8 Witnesses are faithful references** (~0.99), usable to SCORE and ACCEPT non-gold pages — gold is the
  highest-quality reference subset, not a prerequisite for scoring.

---

## 2. Source curation & purge

Curated pool (jp2 present, OCR present): **S1** 3028 (archive-ot1/ot2/nt); **S3** 2274 (pdf-S03a/b, OT); **S4**
772 (jp2-S04, 1633 NT); **S6** 2872 (jp2-S06, 1635 whole — **DROP NT pages**); **S8** 800 (jp2-S08, 1582 NT);
**S9** ~1590 but **INCOMPLETE** (NT done; OT1 partial 780/1160; **OT2 un-OCR'd 0/1150**).

- P2-1 **Delete** banned `our-ocr-diplomatic/{eebo-nt,eebo-vol1..5,pdf-S02,archive-newtestament}`; trace/remove derivatives.
- P2-2 **Allowlist guard** in `build_tome_map.py`, `qc_audit.py`, `consensus_v2.py` (refuse non-curated tomes, loudly).
- P2-3 **CI grep** for banned source ids across `*.json`/reports; fail the build on any hit.
- P2-4 **Rebuild** `tome-map.json` curated-only (drops its 8 banned sources).
- P2-5 **Retire `ocr_consensus`** (its NT axis was S5): delete `reads/ocr_consensus.json`, remove from
  `qc_audit`/report/E(v); replace its role with cross-source divergence (§7,§9).
- P2-6 **OCR S9-OT2** (kraken pass over jp2-S09ot2, ~1150pp) + S9-Psalms remedial preproc, before S9 is a full OT witness.

---

## 3. Ground-truth: state, completion (pulled forward), tooling

**Current-best GT (all count NOW):** 15 scripture (12 Sir-reviewed + 3 Jarvis-draft-addressed) + 31 matter
(OT1×10, OT2×11, NT×10; full front+back). Corrections flow: review tool → `corrections/<slug>.corrections.json`
→ `gt_apply_corrections.py` → canonical bare json (+ `.pre-review`). **Raster bug fixed** (§0). When Sir submits
corrections, fold + re-standardize (GT-2), rebase the next round.

**[COMPLIANCE GAP] SIR-DIRECTIVE §2.1 unmet:** across all gold, **S3, S4, S9 have zero pages** → gold-expansion
required (GT-3). Fine-tune is 100% S1.

**Versification is fuzzy** (body tags straddle; 2john v13 swallowed into v12; `verses_on_page`≠body tags). A
`verses_aligned` layer exists (s_dismas>odr_com>janvier cuts) ~95% reliable with cross-page gaps.

**GT work items:**
- GT-1 **[DONE]** fix 3 draft addresses by content-anchoring; **[DONE]** on-demand raster tool.
- GT-2 **Re-standardize versification to janvier boundaries** (janvier-PRIMARY cut; §5): rewrite `verses_aligned`
  for every scripture GT; reconcile `a`/`b` split verses (a cross-page verse = ONE unit = union of page fragments);
  make `verses_on_page` a derived, checked field. Re-run whenever Sir submits corrections.
- GT-3 **Gold-expansion (PULLED FORWARD — see §12):** select pages so every source S1/S3/S4/S6/S8/S9 + every
  matter "book" + every layout mode is represented; **draft from base OCR** (exists — needs NO fine-tuned
  recognizer), Jarvis visual-correct against the clearest source (rule 5), push to review tool (rules 6–7).
- GT-4 **QC gold vs janvier grid** where R2/R3 disagree; janvier defines the verse/apparatus grid the GT must be
  congruent with (Sir: even Gold isn't the localization authority — janvier is).

---

## 4. Addressing — content-anchoring (ADDR-3 primitive)

Offset arithmetic is out (offset non-constant; `page_label_printed` unreliable). Primitive = **content-anchoring**
(demonstrated: resolved all 3 drafts by max base-OCR containment of the gold body).
- ADDR-1 rebuild tome-map curated-only (keep CH_FLOOR weak-chapter recorder).
- ADDR-2 **cross-validate every gold `page_index` against tome-map** as a standing invariant (would have caught
  2esdras: book span 982–1009 excludes 974).
- ADDR-3 formalize `resolve(book,ch[,v]) → (ocr_dir,page_index)` per source (tome-map + bounded content search),
  confidence-scored; low-confidence → OPEN, never a silent guess. (Prototype exists inline; promote to a module.)

---

## 5. Metric layer — the core redesign (grounded in this session's proofs)

**Three fixed conceptual axes** (do not bend to data shape): **(I) LEVEL** content-identity (`fold_modern` vs
modern ref) AND surface-identity (`fold_archaic`/raw-ſ vs archaic ref/gold), archaic-preeminent
(`char_identity.evaluate_locus`; `floor_modern` flags where modern is an invalid yardstick — 11.4% of loci).
**(II) SPAN** same-span→symmetric `edit_ratio`; subset→containment (guard only). **(III) GRAIN** printed-line →
rolled to janvier verse.

**Containment = up-front localization GUARD** ("are the target verses present on this page?"), run in routing
BEFORE identity — catches address/segmentation errors (2esdras-class). NOT the identity metric. Remains the correct
*primary* metric for unversified **matter** (`matter_match_report` pooled containment).

**THE LINCHPIN — janvier-cut both sides.** Proof this session: s_dismas↔Gold reads 0.995 by containment but only
0.93 per-verse because gold's cut ≠ s_dismas's native cut. When BOTH texts are cut by the **same janvier grid**,
boundary fuzz cancels and per-verse identity reflects true fidelity. Every comparison (OCR, Gold, each witness) is
re-cut to janvier `\v` intervals, then scored. **This is gold-free by construction** (janvier covers all 76 books)
→ it works for ANY DR locus, gold or not; the 15+31 GT pages only *validate* it, they are not required by it.

**Verse-segmentation rebuild (VS-1..6) — critical path** (align_coords.realign drifts 2–93×, swallows marginalia):
- VS-1 **body-isolate first** (`layout.py` drop header/marginalia/catchword) BEFORE alignment.
- VS-2 **page-scope** (align only the page's verse span, via tome-map/content-anchor localization; never the whole chapter).
- VS-3 **janvier-primary boundaries** (flip `align_coords` cascade to janvier→s_dismas→odr_com for CUTS).
- VS-4 **robustify + length-sanity**: anchor-based monotonic cutting; a verse span >Nσ off the reference length →
  that verse OPEN, never a garbage span (No Silent Degradation at the sub-page grain).
- VS-5 **validate on the 15 scripture + 31 matter GT**: per-verse identity must TRACK page quality (psalms-118
  ≥0.95, clean 1-verse spans, not 0.47) — AND spot-validate on non-gold pages via witness-vs-witness janvier-cut
  identity (which must stay ~0.99, per §9), proving the method holds where no gold exists.
- VS-6 **score** per-verse dual-identity vs gold (where present) AND vs each witness (archaic-preeminent), all
  janvier-cut, ſ-count companion.

**ACCEPTANCE (gate-OUT) criterion:** a locus passes reOCR iff per-verse identity ≥ 0.90 vs the best available
reference — archaic-preeminent (s_dismas/odr_com surface where present; janvier/madueke content+surface in the
archaic-gap books), janvier-cut. Gold where present is the gold-standard reference. Below-bar → OPEN.

---

## 6. Recognizer — cross-source fine-tune

R2 trained on 311 S1 lines only; S3/S4/S6/S8/S9 (incl. 1633/1635 founts) unseen.
- REC-1 after GT-3, re-extract crops from **all six sources'** gold + **matter** (`rung2_prepare.py`: glob
  scripture+matter; handle multi-page `page_index` lists).
- REC-2 retrain via `rung2_finetune_kraken.py` (transfer from `reichenau_lat`); **measure** whether 1633(S4)/
  1635(S6) founts need per-edition heads vs one pooled model — don't presume transfer.
- REC-3 held-out eval **per source** (per-verse identity), not S1-only.
- REC-4 include apparatus founts (annotations `vv`, footnote long-ſ/f).

---

## 7. Confidence gate — four-alarm, and the escalation ladder

**Confidence origin:** kraken `softmax(logits/temperature)` per image column; per-char conf = argmax posterior over
its columns — a self-report BLIND to systematic (confident-wrong) misreads. `page_confidence` mean washes out local
catastrophe.

**Four gold-free alarms (OR → escalate = gate-IN):**
1. recognizer-internal, un-averaged: worst-line conf, low-conf-line fraction, conf variance (catches *stochastic*
   failure; blind to systematic).
2. **cross-source content disagreement — gate-IN routing** (Sir's intent, now made precise): fold R2 + the other
   curated sources' OCR of the locus to the content skeleton; sharp divergence from the independent majority
   FLAGS the locus as likely-bad → route to reOCR/escalation. Depth is realistically 3–4 (OT: S1/S3/S6/S9;
   NT: S1/S4/S8/S9). **It never accepts a reading** (agreement ≠ pass; that would be consensus-as-truth, banned).
   **[IMPLEMENTED + CALIBRATED + WIRED 2026-07-23 — `xsrc_gate.py`]** — see the calibration block below.
   **[DESIGN DECISION, flag for Sir]** the independent reference is instantiated as the reference-WITNESS
   cascade (s_dismas→odr_com archaic; sabates_a/madueke_b modern), NOT the other scan sources' base OCR.
   Rationale: No Silent Degradation demands the gate flag EVERY truly-failed verse, so the independent estimate
   of the true text must be the HIGHEST-quality one available at runtime — the witnesses are ~0.97-faithful
   (DIV-1) and cover all 76 books, a strictly better independent estimate than base OCR (~0.5). This IS
   "cross-source disagreement", instantiated with the strongest source; it is gold-free (a witness ≠ gold) and
   never accepts a reading. `coverage-audit-verse.json` stores per-source SCORES, not raw per-source OCR text,
   so the literal "fold the other sources' OCR" was not directly buildable from it anyway. Scan-source-OCR
   majority remains available as future corroboration if Sir prefers the literal reading.
3. structural/length anomaly (measured AFTER body-isolation+verse-seg so counts are apples-to-apples; vs neighbors
   + tome-map density; would have caught 2esdras).
4. **per-source-calibrated** ſ-presence (S4/S6 modernized → lower ſ-rate; global constant would false-positive).
   Sharpest = medial-f-in-ſ-position (`suspected_long_s_as_f`).

**Honest efficacy:** anti-laundering power comes almost entirely from the EXTERNAL alarms (2–4), since alarm 1 is
self-report-blind. The gate is a ROUTER; the real guarantee is the terminal OPEN state (below). Calibrate on the
GT: τ that flags EVERY known-bad page (recall=1 on knowns) at a *tolerable escalation rate* = flagged% the R3
budget can absorb (local model ~free → ceiling is throughput + the Claude-CLI residual volume). Report flagged% and
false-alarm% explicitly; if recall=1 forces flagged% too high, ALERT to redesign the gate/recognizer — never lower recall.

**[CALIBRATED 2026-07-22 — `gate_calibrate.py`, 165 gold verses, 43 known-bad R2<0.90] — the §7 thesis is now
EMPIRICAL, and it ALERTs:** recognizer confidence is self-report-BLIND — mean conf known-bad **0.9798** vs good
**0.9878** (indistinguishable); **40/43** known-bad verses have conf ≥ 0.92. The current `reocr_core` conf gate
(escalate if conf<0.92) catches **1/43** bad (recall 0.023); recall=1 on conf alone forces **88% escalation**
(useless). Internal alarms 1+3+4 (conf, length-anomaly, ſ-suspect) together catch **0** of the confident-wrong
tail. ⇒ **The gate MUST be rebuilt on alarm 2 (cross-source disagreement)** — R2 vs the independent reference,
flag divergence; this is the only signal with visibility into systematic misreads.

**[WIRED + RE-CALIBRATED 2026-07-23 — `xsrc_gate.py` (the alarm-2 module) + `reocr_core.reocr_page(locus=…)`
+ extended `gate_calibrate.py`]:** alarm 2 = R2's per-verse identity vs the reference-witness cascade,
janvier-cut, archaic-preeminent (`evaluate_locus`), GOLD-FREE. **It SEPARATES where conf is blind:** mean
`xsrc_id` known-bad **0.7143** vs good **0.9357** (gap **0.22**, vs conf's 0.008). **The confident-wrong tail
(40 verses, conf≥0.92, internal alarms catch 0/40) → alarm 2 catches 40/40.** **FULL gate (conf<0.92 OR
verse-seg-OPEN OR ſ OR xsrc<τx) reaches recall=1 (ALL 43 known-bad flagged — No Silent Degradation MET) at
τx=0.90 → 34% escalation, 13 false-alarms** (vs conf-only's 88%); alarm 2 alone gives recall=1 at 33%. **Zero
blind spots** at τx=0.90 (0 known-bad have xsrc≥0.90); the thinnest-margin known-bad is xsrc=0.8954 (margin
0.005 — a future GT-3 known-bad above τx fires the harness's ⚠ ALERT branch, never a silent miss). End-to-end
production check: `reocr_page(genesis-24, locus=("genesis",24))` gold-free recovers all 4 gold known-bad
(vv27–30) + correctly flags the cross-page fragment v12 — recall 4/4. All modules self-check
(xsrc_gate/verse_seg/char_identity PASS; calibrator reproduces identical numbers pre/post the DRY refactor that
made calibrator + production share `xsrc_gate` — no drift). **HONEST caveats:** (a) the archaic-gap
MODERN-fallback τx is UNCALIBRATED — all 5 current gold books carry s_dismas; GT-3 must add an archaic-gap book
(§12 M2). (b) the 13 false-alarms are verses where the witness itself is defective/absent (min good xsrc=0.0)
→ SAFE over-escalation (flag-IN → R3 re-reads, never wrongly accepted). The escalation gate now ROUTES the
residual (alarm 2 live); the R3 terminal (human review) still holds anything R3 can't clear (§7 ladder). NEXT:
R3 backend (§8, local vision) so flagged verses are actually re-read, + GT-3 to calibrate the archaic-gap τx.

**Escalation ladder + TERMINAL states (answers "is this an infinite loop?" — no):**
`R2 → [gate] → R3-local → R3-Claude-agent → TERMINAL`. At each rung, score vs the acceptance criterion (§5):
- **Pass at any rung → ACCEPT** that rung's output as the transcript (record which rung).
- **Fail R3-Claude-agent → TERMINAL = OPEN:** (a) not accepted (no laundering); (b) pushed to the GT editor tool
  as a human-review worklist item; (c) blocks the deliverable; (d) accumulating OPENs is an ALERT that the
  APPROACH needs redesign (recognizer/preproc/crop-geometry), not endless reprocessing. Finite: R2 → local → Claude
  → human. No rung re-runs itself.

---

## 8. Rung 3 — local vision + in-agent Claude (no paid API)

- R3-1 **Local bulk:** rewrite `reocr_r3.py` backend from `anthropic` → local. **Infra: full rein** — run models
  via the operational **Ollama** container (`qwen3-vl:8b` installed today), **MLX** (olmOCR-2-7B, CHURRO-3B), or
  **LiteLLM**; pick per measurement. Keep the ſ-safe diplomatic prompt (model-agnostic), dual-track + ſ-count gate.
  **[PARTIAL 2026-07-23]** `reocr_r3.py` refactored to a backend dispatch (`ollama` default / `claude` arbiter),
  ſ-safe prompt kept, + a No-Silent-Degradation guard (empty response → RAISE, never a silent empty transcript).
  **[MEASURED — qwen3-vl:8b UNUSABLE]:** thinking-locked (think:false / /no_think / chat all ignored), whole
  budget → `thinking`, `response` EMPTY, degenerates into a repetition loop. Superseded by olmOCR-2 below.
  **[DONE 2026-07-23 — olmOCR-2 via MLX stood up + VALIDATED as the R3-1 CONTENT rung]:**
  - **Infra:** isolated `ocr-mlx-venv` (mlx-vlm 0.3.12 + **transformers==5.1.0** — 5.2.0 has a video-processor
    registry bug that breaks Qwen2.5-VL loading; pinned to avoid destabilizing the shared infra venv). Model
    `mlx-community/olmOCR-2-7B-1025-bf16` (15GB). `mlx_ocr.py` (standalone, ocr-mlx-venv) ← subprocess ← `reocr_r3.py`
    `_r3_mlx` (default local backend now; `backend='claude'` = ſ-faithful arbiter, `'ollama'` = deprecated).
  - **CONTENT — beats R2 (the R3 lift, archaic_id / ſ-blind):** genesis-24 flagged vv27-30 R2 **0.69–0.88 →
    olmOCR-crop 0.89–1.00** (v27 1.0, v28 0.978, v29 0.990, v30 0.886) — **4/4 beat R2, 3/4 clear the 0.90 bar.**
  - **LOOP:** olmOCR repetition-loops on a full dense page (≈4 verses then repeats to the token cap; rep-penalty
    1.15 insufficient). FIX = crop/bands (`crop=` fractional box, or `_band_boxes`/`_stitch_bands` for full-page).
    A ~6-verse crop is clean (13–25s).
  - **ſ FINDING (dual-track):** olmOCR MODERNIZES ſ→s on crops and IGNORES diplomatic style prompts (Test A ==
    Test B byte-identical) — its OCR fine-tuning dominates. It preserved ſ only on the full (looping) page. So
    olmOCR is a **CONTENT rung**, not a diplomatic-surface one. ſ is glyph-driven (positional `restore_long_s`
    caps at ~90.4% — 45/56 errors are 'ſh/sh'), so a faithful ſ SURFACE must come from a visual recognizer
    (reichenau/R2, or the Claude arbiter), never a faked rule. Per No Silent Degradation the ſ-count gate flags
    olmOCR output as ſ-deficient; surface-critical verses escalate to `backend='claude'`. `restore_long_s` exists
    as a LABELED ~90% surface-completion utility, never silent.
  - **STILL OWED:** (a) verse→crop geometry (map a flagged janvier verse to its pixel band via kraken line
    bboxes) so R3 targets the flagged span precisely; (b) `mlx_vlm.server` (load-once) — the subprocess reloads
    the 15GB model per call; (c) wire `run_r3=True` in `reocr_batch` once (a)+(b) land + the ſ-escalation is set.
- R3-2 **Two-local-model agreement-gate** (qwen3-vl:8b + olmOCR-2) as a cheaper arbiter BEFORE Claude; **Surya**
  for layout-assist on multi-region pages; install **CHURRO-3B** as the historical-specialist bulk. (Sir-approved.)
- R3-3 **Peak arbiter = in-agent Claude Code** (validated 0.95–0.99, no key) for the residual the local models
  can't clear.
- R3-4 **Crop geometry per layout mode — a real experiment, not an aside** (Sir flagged this as a big deal):
  column-band/region crops differ by mode (prose 1-col, psalms 2-col apparatus, genealogy list, table grid,
  greek-margins). Build a crop-geometry harness, sweep per mode × source, VALIDATE that the vision pass improves
  with the right crop vs whole-page; record the winning geometry per (mode,source).
- R3-5 test on psalms-118 (0.9915) + 2–3 hard non-gold pages; confirm per-verse identity ≥ R2 before wiring
  `run_r3=True`. **OPEN-page ledger** format: `{locus, source, rungs_tried, best_score, reference_used, state:OPEN}`
  → the human-review worklist.

---

## 9. Divergence analysis — corrected, full matrix, recurring

**No demoting on comparison scores.** Measured cleanly this session (janvier-cut / same-span):
- modern↔modern (janvier=`sabates_a` ↔ madueke) **~0.9999** (one witness effectively).
- archaic↔archaic (s_dismas ↔ odr_com) **0.994–0.9994** (one archaic voice effectively).
- archaic↔modern surface **~0.95**, content **~0.98** (spelling differs, content agrees).
- Gold ↔ archaic witness (containment) **~0.995**.
- structural: archaic gap **8,384 loci / 22.6% / 17 books** (Ecclesiasticus, prophets, appendix) have NO archaic
  witness → janvier/madueke primary there; `floor_modern` 11.4% modern-invalid loci; `CHRONIC_DIVERGENT` books
  {acts,2-para,2-esdras,romans,mark,psalms} to re-examine with janvier-cut (likely also artifacts).
- DIV-1 **[DONE 2026-07-22 — `divergence.py`, `divergence-report.json`]** full matrix, all 4 witnesses pairwise
  + Gold vs each, janvier-cut same-span, 28 chapters. **EMPIRICAL noise floor (corrects the asserted numbers
  above — measured, not claimed):** mod↔mod (sabates_a↔madueke) content **0.9948**; arc↔arc (s_dismas↔odr_com)
  content **0.9805** surface **0.980** (NOT 0.994); mod↔arc content ~0.96–0.978 surface ~0.94–0.95; Gold↔witness
  content **0.960–0.978**. **[AXIS-AWARE τx, calibrated 2026-07-23]** the alarm-2 gate applies the τx of the
  reference axis that governs each verse: **archaic (R2 vs s_dismas surface) τx=0.90**; **modern-fallback (R2 vs
  janvier content — the 17 archaic-gap books) τx=0.92** (the archaic↔modern surface noise lifts the max known-bad
  to ~0.90, so the bar is nudged up). Confirmed on the REAL archaic-gap page **GT-3 abdias-01** (all 12 verses
  modern-axis; 3 known-bad incl. 2 confident-wrong conf≈0.99; all caught). `xsrc_gate.TAUX_ARCHAIC/TAUX_MODERN`.
  Routing (§7 alarm-2) keys on the WORST shared verse (chapter means hide craters):
  15 per-verse anomalies < 0.60 surfaced as flag-IN loci (e.g. psalms-118 v107 = 0.0 on every odr_com pair =
  odr_com's versification defect pinned; proverbs-16 v10, 2-esdras-7 v71 = s_dismas defects). Multi-page chapters
  merge gold across pages before cutting. DIV-2 re-run hook = `--sample N`.
- DIV-2 **re-run routinely** (every GT-expansion round + every reOCR iteration) to track the concrete
  between-witness noise floor; it is the yardstick for "is an OCR diff real or within witness noise."
- DIV-3 **retire the old gt_rescore 0.80 numbers** (span-artifact); recompute all divergence janvier-cut.

---

## 10. Report — curated, per-verse + guard + matter, no consensus

Rebuild `qc_audit.py → coverage-audit-verse.json → build_reocr_report.py`:
- REP-1 curated sources ONLY (purge S5/S10–S15); **remove ocr_consensus** as a witness/row.
- REP-2 R2 (and R3) as verse-segmented witness streams alongside the curated legacy scan OCR.
- REP-3 per-verse dual-identity (content+surface, archaic-preeminent), janvier-cut, line→verse rollup; containment
  as the up-front guard column.
- REP-4 Gold column where present; witness-anchored elsewhere (all references now trusted ~0.99, marked by which).
- REP-5 **matter as first-class books** (row per source × matter-book, apparatus-grain containment; flag <0.90).
- REP-6 fix prose-deflation (line grain → roll up); expand `PILOT_SCOPE` only after ADDR trust.

---

## 11. Segmentation / layout across sources (DO NOT SKIP — Sir)

Layout MODES are complete (prose, genealogy, running-poetry, table, greek-margins). The gap is **each mode ×
each source's rendering** (S1/S3/S4/S6/S8/S9 differ in res/skew/ink; `layout.py`+`blla` validated mostly on S1).
- SEG-1 sample each mode from each source; verify body-isolation + verse-seg hold.
- SEG-2 tune `layout.py` relative thresholds where a source breaks (2john marginalia over-drop known).
- SEG-3 S9 remedial preproc (spotty Psalms) + OCR S9-OT2 (§2 P2-6).
- (Feeds VS-1 and the R3 crop-geometry harness §8 R3-4.)

---

## 12. Phased plan — GT completion PULLED FORWARD (with the reasoning)

**Why pull GT forward (Sir's question):** GT is the measuring stick for every reOCR change, and it is currently
incomplete (S3/S4/S9 absent) + fuzzy (versification). Crucially, **drafting new GT needs only base OCR (exists) +
Jarvis visual correction — NOT the fine-tuned recognizer** — so no dependency forces it late. Doing it now grows
the baseline immediately and de-risks every later measurement. Keeping it in M4 would mean iterating the recognizer
against a non-compliant, mis-versified baseline. → **pull it forward.**

- **M0 — Purge & guardrails.** Delete banned OCR; allowlist guards; CI grep; retire ocr_consensus. *Gate:* zero banned refs.
- **M1 — Addressing & GT integrity.** **[DONE: 3 addresses, raster tool]**; rebuild tome-map curated; cross-validate
  all gold addresses; janvier-primary re-standardize `verses_aligned` (GT-2). *Gate:* all GT addressed+validated.
- **M2 — Verse-seg engine + GT completion (pulled forward).** **VS-1..5 [DONE+VALIDATED §0.5]** ·
  **DIV-1 [DONE — `divergence.py`, §9]** · **GT-2 [DONE — `gt2_restandardize.py`; all 15 scripture GT
  re-standardized to janvier, non-destructive+backed-up; found & verified the Ps-1 6-vs-7-verse janvier/printed
  difference]**. **GT-3 [STARTED 2026-07-23]:** first archaic-gap gold **`scripture-abdias-01`** (archive-ot2-1610
  p840, Abdias 1:1-12, diplomatic ſ-faithful, drop-cap + argument + margin apparatus) — chosen because it fills
  the archaic-gap CALIBRATION gap (no s_dismas/odr_com → exercises the modern-fallback xsrc axis; confirmed
  τx=0.92 on real data, §7). **STILL OWED:** abdias vv13-21 (p841); S3/S4/S9 SOURCE-coverage gold (SIR-DIRECTIVE
  §2.1); matter/layout-mode coverage — the labor tail (draft via olmOCR content + Jarvis ſ-correction; push to the
  fixed review tool). *Gate:* per-verse tracks page quality **[MET]**; witness noise floor **[MEASURED]**; every
  source ≥1 gold **[S3/S4/S9 still owed]**. — M2 core complete; GT-3 breadth is the continuing tail.
- **M3 — Metric + divergence + report.** **[IN PROGRESS 2026-07-22]** CORE DONE: `qc_audit.realign_vmap` swapped
  align_coords→**verse_seg** (janvier-cut; the metric now measures recognition, not boundary-spillover — genesis
  base-OCR honest 0.65, no artifact; `drop_apparatus=False` here so dropping can't inflate identity). REP-1 DONE:
  `curated_sources.filter_curated` guard in qc_audit (kills the S14 leak) + belt-and-suspenders in the renderer;
  `ocr_consensus` already zero-refs (retired). **PILOT RENDERED — v014 `reocr-report-pilot.html`, 6438 verses,
  curated-clean** (coverage promoted, old backed up `.pre-verse_seg`; base-OCR honest baseline arc ~0.36–0.70,
  1/271 chapters have any source passing → the reOCR mandate; A/B vs align_coords = same baseline ±0.02–0.05 but
  MORE-complete coverage, psalms-S9 20→2441 localized, the few dips = harder verses old engine silently dropped;
  DATA + source_fail delta both curated-clean). **REP-2 EVIDENCE DONE [`reocr_lift.py`]:** base→R2 lift on the
  gold pages, per-verse janvier-cut vs gold — **all 15pp base 0.721→R2 0.926 (+0.204), pass 40%→68%; representative
  14pp +0.210, pass 41%→73%.** Residual R2<0.90 = the R3 set (stays OPEN). 1 FLAGGED confound (colossians-3:
  base 0.72→R2 0.0) transparently separated — NOT hidden, NOT R2-recognition: it is multi-chapter GT page +
  greek-margins body-isolation dropping the gold Col-3:18 content + a suspected §4 addressing mismatch (base OCR
  of the resolved page 571 ALSO lacks "women be subject") → §4 ADDR / §11 layout work (see §13 Q5). **STILL OWED
  in-report:** wire REP-2 as a rendered R2 stream/section; REP-4 (Gold column where present), REP-5 (matter — `matter-scoring-
  summary.json` exists+curated but the renderer's V7 reads a different artifact; also swap `matter_match_report`
  align_coords→verse_seg), render+verify v010. *Gate:* curated-clean per-verse + guard + matter.
- **M4 — Cross-source recognizer.** REC-1..4 (retrain on expanded GT incl. matter; per-source held-out). *Gate:*
  per-source held-out per-verse identity measured. — **REVIEW milestone.**
- **M5 — Gate + R3.** **[GATE DONE 2026-07-23 · R3 PRODUCTIONIZED 2026-07-25]** four-alarm **calibrated + wired**
  (`xsrc_gate.py` live in `reocr_page`; recall=1 on all 46 known-bad at τx=0.90 / 33% esc, 0 blind spots). **R3
  NOW PRODUCTIONIZED (see SPRINT-STATUS 2026-07-25 + `R3-PRODUCTIONIZATION-REPORT-2026-07-25.md`):** verse→pixel
  crop geometry (`verse_geom.py`, region crops), load-once olmOCR (`mlx_client`+`mlx_ocr_server`), OPEN ledger
  (`open_ledger.py`, terminal human-review worklist), router (`r3_route.py`) with P5 janvier-cut re-scoring +
  dual-track (content vs ſ-surface). Wired in `reocr_batch(run_r3=True)`. 46 TDD tests; adversarial code-review
  (2 HIGH anti-laundering gaps fixed). Statistically validated on 13 gold pages: **prose content pass 0→76%,
  psalms 0→28% (olmOCR high-variance), and 0/23 accepted verses worse-vs-gold than R2 (No-Silent-Degradation
  proven).** *Gate:* known-bad caught **[MET]**; R3 lifts hard pages **[MET for prose; psalms = R3-4 crop lever
  owed]**; OPENs stay OPEN & surfaced **[MET — ledger built]**. **STILL OWED:** layout-aware column-band crop
  (R3-4, psalms); ſ-faithful in-agent arbiter to close ſ-surface debts; archaic-gap breadth (needs GT-3).
- **M6 — Scale-out.** gated batch on growing book/chapter subsets per source; divergence + report each round.
  *Gate:* a full book transcribed curated-clean, per-verse-scored, residual OPEN-flagged. — **REVIEW milestone.**

---

## 12.5 — REV 4 (2026-07-27): what the grammar work changed, and the autonomous-sprint target

Three findings since rev 3 reshape the remaining plan. All are measured, not proposed.

**(a) The MEASURING INSTRUMENT was biased, and every per-verse number in M5-M7 inherited it.** Per-verse gold
was cut by `verse_seg.segment` — the incumbent aligner — so a challenger was scored on the incumbent's grid.
`gold_grid.py` now cuts the gold at the PRINTED markers (98% of boundaries; the 2% janvier sets are counted).
On the fair reference the hybrid localizer worsens **ZERO** verses (the aligner-cut grid showed 11), and the
"selector cost" that §12/M7 recorded as a real defect **did not exist**. Any future A/B MUST use `gold_grid`;
`--aligner-grid` reproduces the legacy numbers for continuity only.

**(b) The gate's "recall=1" was partly an artifact of that bias. It is NOT met on the fair reference.**
Recalibrated: hybrid catches 23/24 known-bad at τx=0.90 (align catches 19/24). The single miss —
psalms-118 118:109, gold 0.0 but xsrc 0.985 and conf 0.973 — is invisible to all four alarms. **§7's gate is
therefore REOPENED**: it needs a fifth alarm, not a lowered bar (No Silent Degradation).

**(c) §11's premise was too narrow.** SEG-1..3 frames layout as "each mode × each source's rendering". The
Psalm 118 inspection (ot2-1610 pp215-236) shows the variation is finer and of a different kind: the DR prints
THREE verse-marker conventions (`N †` self-labelling, `N.` self-labelling, bare † positional), a page INSIDE a
psalm's range can carry no scripture at all, and `layout.strip_verse_numbers` deletes the strongest marker we
have on a documented but FALSE premise ("the DR body marks verses with † / ‡, never digits"). §11 is
superseded by the composable block grammar (`block_grammar.py`) + regime detection + the page-level
`coverage_alarm.py`, which turn "does this source/mode work?" into a measured, per-page question.

### SPRINT RESULT (2026-07-27) — A, B, C1 CLOSED · C2, D OPEN

    TIER A1  DONE   45 printed verse numbers recovered + cached (31% of 145 openings; regime-dependent).
                    PINNED: anchors must NOT rewrite spans (known-bad 24->45) — alarm use only.
    TIER A2  DONE   Gate MET again: four alarms, recall 1.000 @ tx=0.90 -> 24% escalation, 18 false alarms.
                    The verse it was reopened for was a REFERENCE bug, not a gate bug (see below).
                    Alarm 5 BUILT, KEPT, DEFAULT OFF (40%/44, zero extra catches).
    TIER B   DONE   All 6 curated sources, 33 pages: ot-dagger 20 / nt-numeral 7 / no-scripture 3 /
                    unmatched 3 = 9.1%. **The numeral regime appears in S1, S4 AND S6** — a regime detected
                    on one book extends across editions, which is the property the grammar was built for.
    TIER C1  DONE   block_grammar.chapter_ranges() + best_spans(line_range=). verse_seg's chapter-split
                    contract had NO caller honouring it. colossians-3 ADDR-2 page check still owed.
    TIER C2  OPEN   ſ-faithful in-agent arbiter (~21 debts) — unblocked, unchanged in scope.
    TIER D   OPEN   REP-2/4/5, production audit, report artifact, COMPLETENESS REVIEW — the deliverable.

**The most important correction this sprint made is to §7 and to how §12 gates are read.** The gate's recall
failure on the fair reference was traced to `gold_grid` mislabelling psalms-118 118:109 (it handed v109 the
text of v103): the SPAN was verbatim-correct and the REFERENCE was wrong. `gold_grid` now WITHDRAWS any label
scoring <0.35 against janvier rather than publishing it. **No Silent Degradation applies to the measuring
instrument as much as to the pipeline** — a reference that asserts a label it cannot justify corrupts every
number derived from it, and will be read as a pipeline failure, sending correct work to an expensive rung.
Any future recall/escalation number MUST be quoted against `gold_grid`; `--aligner-grid` exists only to
reproduce the legacy figures.

### Autonomous-sprint completion targets (tiered; each tier has a hard gate)

**TIER A — unblock (everything downstream depends on it).**
  A1 wire `verse_numbers.recover` → `block_grammar.dispatch` → the segmenters, so a recovered self-labelling
     number ANCHORS its verse instead of being re-derived by text matching. Re-run the fair-grid eval and the
     gate calibration. *Gate:* psalms pages detect as `psalm-numbered`; fair-grid mean and pass-rate reported.
  A2 the FIFTH ALARM for finding (b). A verse whose span disagrees with its own PRINTED number is
     structurally detectable — the alarm the four content-based alarms cannot raise. *Gate:* recall=1 restored
     on the fair reference, with the escalation cost reported; or an ALERT that the approach needs redesign.

**TIER B — regime breadth (answers the over-fitting and NT-uniformity questions).** Supersedes SEG-1/SEG-2.
  B1 sample pages across all six curated sources × layout modes; run regime detection + `coverage_alarm`.
  B2 extend the block vocabulary for whatever the sample surfaces (front/back matter, prophetic books).
  B3 tune `layout.py` thresholds only where a source demonstrably breaks (2john marginalia over-drop known).
  *Gate:* every curated source × mode either detects a regime or is reported `unmatched` WITH a reason; the
  alarm rate is quantified; **the "does the Matthew regime extend evenly across the NT?" question is ANSWERED
  with a number, not an assumption.**

**TIER C — correctness debts already itemised.**
  C1 §13 Q5 colossians-3: ADDR-2 verify the page + make `segment()` callers chapter-split a multi-chapter page.
  C2 the ſ-faithful in-agent arbiter (~21 RESCUED_CONTENT_S_OPEN debts; IN-SESSION vision, NO paid API).
  *Gate:* colossians-3 unblocked or reported with evidence; ſ debts closed or itemised in the OPEN ledger.

**TIER D — the deliverable (§10).** REP-2 R2 stream rendered · REP-4 gold column · REP-5 matter as
  first-class books · re-run the production audit (`qc_audit` curated+align) · regenerate the report artifact ·
  COMPLETENESS REVIEW. *Gate:* curated-clean per-verse + guard + matter, rendered and verified.

**EXPLICITLY OUT OF SCOPE for an autonomous sprint** (flagged rather than attempted):
  * **M4 recognizer retrain (REC-1..4)** — a REVIEW milestone that depends on expanded GT and costs hours of
    fine-tuning. Retraining against a GT baseline that Tier B may still change would be work done twice.
  * **GT ratification calls that are Sir's**: the NT roman-LOWERCASE `w` global flip; the summe-of-nt p29
    re-review (11 deferred lines).
  * **GT-3 breadth is a labor tail**, not a gate. A bounded slice (abdias vv13-21 + one gold per missing
    source S3/S4/S9) is in scope; the full matter/layout-mode sweep is not.

---

## 13. Open questions to escalate

1. **Per-edition recognizer heads?** 1633(S4)/1635(S6) vs 1582/1609/1610(S1) — decide by measurement in M4.
2. **S9-OT2 OCR** (0/1150) + S9-Psalms remedial — schedule the kraken pass (P2-6); S9 not a full OT witness until then.
3. **proverbs-16 @292** resolved at only 0.947 (poetry layout) — confirm the page in review.
4. **`page_label_printed`** is unreliable in GT — deprecate in favor of content-anchored address + a derived,
   checked printed-folio field.
5. **colossians-3 addressing + greek-margins layout (found 2026-07-22 via `reocr_lift`).** The GT is multi-chapter
   (Col 3 + Col 4) and its resolved page (jp2-S08 p571) — whose OCR (base AND R2) lacks the gold's Col-3:18
   "women be subject" content — is a suspected mis-address (ADDR-2 cross-validation would catch it). Compounded by
   greek-margins body-isolation dropping 19 lines as "marginalia". FIX: (a) ADDR-2 verify colossians-3 page;
   (b) segment() callers must chapter-split a multi-chapter page (code-review #3-edge); (c) §11 SEG greek-margins
   body-isolation. Until then colossians-3 is a FLAGGED OPEN (blocks its deliverable; not accepted).

*(Resolved this rev: ocr_consensus → retire; draft golds → count now; witness "noise" → artifact, no demoting.)*

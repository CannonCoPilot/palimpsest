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

## 12.6 — REV 5 (2026-07-28): the tiers were never the bottleneck; the INSTRUMENT was

Rev 4 closed tiers A-D and the report still showed nothing. The reason is now established and is not a tier:
**`qc_audit` — the authority behind every headline number — never consumed the improved pipeline.** It
localized with `detect_our_ocr.detect_book` and imported NONE of `verse_locate`, `xsrc_gate`, `r3_route`,
`s_arbiter`. The ladder had touched 191 of 6438 verses (3.0%), and even those were not written back. Wiring it
through (STAGE 1) moved `pass_rate_archaic` **0.1291 -> 0.5133** on the same corpus with **zero
re-recognition**, because the stored stream was already `reichenau_lat` output with per-line bboxes.

**THE PROGRAMME'S CENTRE OF GRAVITY HAS MOVED.** Of everything that has raised the corpus number since rev 4,
almost none was a recognition improvement:

    wiring the validated localizer into the audit                    0.1291 -> 0.5133
    declaring the witness inventory (S6-NT dropped, tomes fixed)     53.20% pass, out-of-tome 6 vols -> 0
    realigning the archaic reference + correcting its predicate      53.20% -> 56.60%
    heading-parser fixes (two duplicated copies)                     honest addressing 61.5% -> 94.4%

**§12 GATES ARE THEREFORE READ DIFFERENTLY FROM HERE.** A tier gate measured on the dev set is evidence about
the METHOD; it becomes evidence about the deliverable only when the corpus figure moves. The report now states
this as two tracks and badges every figure with the one it belongs to — CORPUS-WIDE (witness-anchored, the
deliverable) vs DEV-SET/GT (gold-anchored, the instrument, **3.2% of the corpus**).

### THE DEFECT CLASS THAT NOW DOMINATES, AND THE RULE THAT ANSWERS IT
Five instances to date of ONE hand-maintained rule silently disagreeing with another copy of itself: three
divergent `LOCI` dicts · the GT's `2john` vs the canon's `2-john` · `OT2_BOOKS`' `zacharie` vs the canon's
`zacharias` (which deleted a whole book from its tome) · `OT2_BOOKS` duplicated in `build_tome_map_v2` · the
roman-numeral parser duplicated in `block_grammar`. Every one was invisible until something unrelated looked
wrong. **RULE: any hand-typed list of canonical identifiers validates itself against the skeleton at import
and RAISES on an unrecognised entry.** `witness_inventory` and `gt_registry` now do; nothing else may add a
second copy of a classification that already exists.

### AND A RULE ABOUT MEASUREMENT
"100% held-out chapter accuracy" was quoted for several turns and was **circular**: the interval it checked
against was built partly from the printed heading being checked. Honest measure 61.5%, now 94.4%.
**RULE: an accuracy check may not consult any set the label helped construct.** The circular figure sat at
100% throughout every fix, which is exactly how it was detected — a statistic that cannot fall is not a
measurement.

### REFERENCE-WITNESS POLICY (Sir, 2026-07-27) — normative, encoded in `witness_inventory`
    LOCALIZATION · PRESENCE · INTERVAL ALIGNMENT · TEXT TYPE   janvier + madueke are PRIMARY.
    CONTENT · SURFACE   s_dismas + odr_com PRIMARY only where they carry this verse's OWN text; where they
        have gaps, janvier + madueke are primary for content and surface too.
    GOLD TRANSCRIPT is NOT the authority on localization / presence / interval / verse-line. It is the
        best-reviewed SUBSET and may need standardising against janvier's structure.
The day-1 rule was already implemented in `char_identity.evaluate_locus`; only its PREDICATE was wrong
("a non-empty string" rather than "this verse's own text"). `ARCHAIC_VALID_FLOOR=0.50`, calibrated.

### STATE AT REV 5
    corpus addressing   11 volumes · 12,820 pages · 100% coverage · 94.4% honest held-out (2,372 labels)
    audit               14,335 / 25,328 = 56.60% scan-verse pass · mean archaic_id 0.791 · report v026
    integrity sweep     118 findings (C1/C2/C8 = 0) — `integrity_sweep.py`, ten checks, all volumes
    tests               126 pass

### NEXT — committed order
  0. **Re-run the stale chain**: `.corpus-localize-*`, the audit and the report predate the parser fixes.
  1. **M4** delete the dead tome-map-v1 fallback import.
  2. **M3** matthew 1 unmapped in the NT volumes — a front-matter-boundary case.
  3. **M2** eleven per-volume PDF page offsets, verified BY IMAGE (no text layer; counts differ per volume).
  4. **M1** apparatus/matter loci in the address space and the tome-map. **This is the one that blocks matter
     from entering the re-OCR ladder at all**, and front/back matter is in scope at every stage per Sir.
  5. Sweep residual: C5 78 · C6 15 · C7 7 · C10 4.
  HELD by Sir: V8 apparatus detail · V9 rung/arm completeness pass · remaining-section caption sweep.

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
    TIER C2  DONE   ſ arbiter: 17 of 21 ſ debts CLOSED BY OBSERVATION (R2 surface transfer reduced 21 verses
                    to 21 residue tokens; I read all 8 crops in-session). Ledger 55 -> 38. `restore_long_s`
                    never called. TWO instrument defects found: olmOCR misreads ſ as **f** as well as
                    flattening it to s (invisible to any s-only test), and the ſ-deficiency baseline was
                    charging the verse for marginalia R3 correctly excluded. **4 debts re-opened on the
                    CONTENT axis** — reading the crops exposed token-level misreads riding through a passing
                    per-verse gate (see below).
    TIER D   DONE   Report v018. REP-2+REP-4 = V9 gold-anchored stream ladder (base 0.7213 -> R2 0.9256,
                    pass 40%->68%; representative 41%->73%); REP-5 = V10 matter as first-class books (110
                    rows, 3 pass, 107 OPEN) — the V7 "mismatch" was two DIFFERENT artifacts, both now
                    rendered and labelled; V11 = the OPEN ledger, in the report for the first time.
                    qc_audit re-run reproduces value-identical. Completeness failsafe PASS (76 books /
                    1360 chapters, no gaps). Ledger still BLOCKS the deliverable at 38.

**THE MOST IMPORTANT FINDING OF THE C2/D SPRINT IS ABOUT THE GATE'S GRAIN, AND IT IS A NEW OPEN QUESTION.**
Reading the crops to settle the ſ surface exposed four verses that PASSED the per-verse content gate while
carrying a single wrong word: abdias 1:3 `layst` for `ſayſt`, matthew 28:2 `satte` for `ſate`, proverbs 16:22
`foolcs` for `fooles`, genesis 16:6 `affliet` for `afflict`. A per-verse threshold cannot see a per-token
misread — the rest of the verse carries the score. These are not four incidents; they are one structural
limit, and they were found only because a SURFACE task forced a per-token visual read. Sub-verse gate grain
is now an open design question (§13). The four are held `CONTENT_OPEN` with the misread named.

**The most important correction the M12 sprint made is to §7 and to how §12 gates are read.** The gate's recall
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

**Q17 (2026-07-29, OPEN — the design principle, now adopted). Books and chapters are handled by VARIATIONS of
the shared logic, not by identical code.** Sir's ruling, and the evidence forced it: the four Genesis witnesses
do not share a layout and two of them are MIRROR IMAGES. On the 1609 first edition (S1/S3/S9) the main
annotation column is on the RIGHT (x .81-.99) with cross-references far left and verse numbers in a column of
their own; on the 1635 second edition (S6) the main annotation column is on the LEFT (.09-.215), the right
margin carries only sparse cross-references, and the verse numbers are INLINE. Every generic single-threshold
filter therefore scored ~42-46% recall for 17-19% of scripture lost — it was being asked to catch a left column
and a right column with one number. The generic functions in `layout`/`verse_seg`/`corpus_localize` stay as the
reference implementation; tuned logic goes in per-book modules (`gen1_pagemodel.py`, `genesis_tuned.py`).
**Overfitting to a book and a source is correct here, not a compromise.**

**Q18 (2026-07-29, RESOLVED-NEGATIVE — the warning is cosmetic). Is `reocr_core` recognizing with a
model/segmentation-type mismatch?** It is not. Probe: `kraken_segtype_probe.py`.

*What is declared.* The mismatch is ours. The base recognizer `reichenau_lat.mlmodel` declares
`seg_type: baselines`; only the FINE-TUNED `reichenau_dr.mlmodel` declares `bbox` — the signature of the
Python-API bypass the fine-tune had to use, since kraken 7.0.2's `ketos train` fails with `im_transforms=None`
on raw bboxes.

*Why inspection could not settle it.* In `rpred.mm_rpred` the warning is raised by comparing the model's
DECLARED `seg_type` against the segmentation's type and nothing else; the line-extraction path is chosen by
`bounds.type == 'baselines'`, never by the model. The declaration tells us only what the trainer wrote down —
the very thing under suspicion. The model had to be asked directly.

*The answer.* Recognizing the same `blla` lines twice — as baselines, and as a `bbox` Segmentation built from
those lines' bounding boxes — over 7 Genesis 1 leaves across all four witnesses:

| arm | mean conf | mean chapter recall |
|---|---|---|
| baselines (current) | **0.9735** | **0.4042** |
| bbox (what the metadata claims) | 0.9016 | 0.1898 (**-0.2144**) |

The bbox arm is worse on every leaf and every axis, and its token yield collapses where the leaf is warped
(`archive-holiebible-ot1` p32: 601 tokens -> 96). **The model was trained on dewarped polygons and only its
`seg_type` field is wrong.** The ladder has been running the model the way it was trained all along; no
quality figure this project has quoted is affected. Not the largest lever — not a lever.

*Remedy, deliberately not applied.* Rewrite that one metadata field on `reichenau_dr.mlmodel` so the warning
stops misdirecting future sessions. Left undone while the sprint is under a commit hold — rewriting a trained
model artifact is not a change to make unreviewed.

*A methodological note worth keeping.* The probe's first run scored both arms with `char_identity.
evaluate_locus` and got **0.000 for both**: that metric compares a verse to its own reference and returns zero
for a whole leaf against a whole chapter. A dead metric reads as a tie, and a tie would have been reported as
"mislabel" — the right verdict resting on no evidence. The conclusion above stands on a longest-common-
subsequence token recall, which moves.

**Q19 (2026-07-29, RESOLVED-NEGATIVE — record it so it is not retried). Geometry cannot separate the apparatus
from the scripture at ANY grain.** With per-character `cuts` in hand, every word on a page was labelled by
whether it anchors to the chapter's archaic reference and the geometry asked to divide them: a word-x threshold
at 0.78W catches 42-46% of apparatus for 17-19% of scripture lost, and is worse than useless on S6; intra-line
gap ratios (max/median) are only 1.1-1.9 and split in the wrong place. `blla` merges the two columns into
single lines and the apparatus words occupy the SAME x range as the scripture. This retires the widest-gap
edge, the proportional character offset, the word-x threshold and the intra-line gap. **Per-source x-BANDS
work because they encode the page; single thresholds never will.**

**Q20 (2026-07-29, OPEN). The apparatus filter must not be anchored on janvier.** Janvier is a MODERN-SPELLING
text, so the archaic readings the DR actually prints (`sone`, `therfore`, `daies`, `citie`, `geue`, `betwene`,
`darkenes`) anchor to nothing and are indistinguishable from apparatus — which is why `apparatus_min` had to
stay at 8 and is a documented no-op on Genesis. Anchoring on the ARCHAIC reference (s_dismas + odr_com) cuts
those false positives 3,282 -> 838. The run-length rule built on that anchor is still net-negative
(`min_run=2` -> Genesis all-pass 518, `min_run=3` -> 753, against a baseline of 799) because it deletes
hyphen-split scripture: "a fir. ment" is *firmament*. The ANCHOR is right; the RULE is not yet.

**Q21 (2026-07-29, OPEN). A reference-outlier detector is needed, and it must flag rather than pass.**
Genesis 1:25 is the archetype: all four witnesses read it correctly (0.93-0.97 against the modern references)
and all four FAIL, because s_dismas's *reading* diverges (0.75) and `ARCHAIC_VALID_FLOOR=0.50` lets it govern.
It is not a misalignment — offset 0 scores best. Raising the floor globally was already tested and rejected
(0.90 withdraws 754 references and LOWERS pass), so the remedy is a detector: >=3 witnesses agreeing with each
other AND with both modern references while the archaic dissents means the ARCHAIC is wrong. **Flag the locus;
never convert it to a pass.**

**Q22 (2026-07-29, RESOLVED — and it generalizes). A verse is bounded by a CHAPTER, not by a leaf.** Genesis
1:12 could not be localized by any per-page call: `And the earth brought forth` is the last line of
`archive-ot1-1609` p21 and the rest of the verse is the first line of p22, so no single page ever holds it.
Offering the localizer the chapter as one concatenated line stream ALONGSIDE the per-leaf calls, and keeping
whichever span fits janvier better — the same gold-free hybrid selection `best_spans` already uses to choose
between its two segmenters — took Genesis 1 from 29 to **31 of 31** verses at >=3/4 support.

The chapter stream wins only **7 of 124 spans (5.6%)**, and those 7 are the boundary verses. That is the point:
this is not a different transcription, it is the same one localized against the right unit of work. It also
reframes the M-series finding that all-fail verses are BOUNDARY verses (verse-1-of-chapter 4.8x,
neighbour-on-another-page 2.7x) — a real effect, but substantially an artifact of asking a page-shaped question
about a chapter-shaped object. **The live pipeline still localizes page by page; folding this in is the single
highest-value item in the fold-forward (§Q17) and should be measured corpus-wide before adoption.**

**Q23 (2026-07-29, OPEN). The remaining Genesis 1 losses are annotation words interleaved into the body's
reading order, and a margin rule cannot reach them.** `birdes` and `in` sit inside gen 1:12 in all three 1609
witnesses; `Eſa.`, `Aug`, `Gen.` and stray fragments of the left annotation column sit in S9's rows. A
per-leaf body left edge derived from the median row start removes them AND strips the first real word off some
forty rows across the four witnesses (`And it was ſo done` -> `ſo done`) — odr_com 0.928 -> 0.907, s_dismas
0.747 -> 0.725, verses at 4/4 15 -> 11. Rejected and pinned (`_trim_left_margin`,
`tests/test_gen1_pagemodel.py::test_left_margin_trim_stays_unwired`). One threshold cannot serve a ragged left
edge — the fourth incarnation of the family Q19 retired. These words are a SEGMENTATION artifact: `blla`
merged the columns and kraken emitted them in body reading order. The lever is the segmentation, not the
margin.

**Q24 (2026-07-29, RESOLVED — it was the REFERENCE, not the OCR). Why did Genesis 1 score 0.756 against
s_dismas and 0.946 against odr_com?** Because `s_dismas` is MIS-NUMBERED in Genesis 1. It splits the printed
verse 25 in two —

    s_dismas 1:25  `And God made the beaſtes of the earth ... in his kind.`                    (24 tokens)
    s_dismas 1:26  `And God ſaw that it was good,`                                             ( 7 tokens)
    odr_com  1:25  `And God made the beaſtes ... in his kind. And God ſaw that it was good.`    (31 tokens)

— and therefore runs the chapter to **32 verses** where all three other references run it to 31, with 26-31
shifted by one. `s_dismas` 1:27 matches `odr_com` 1:26 at ratio **1.000**, and the shift persists to the
chapter end. Verses 26-31 could not have reached the bar against that reference by any amount of OCR work.
Corrected non-destructively at load time in `ref_renumber.py` (source file untouched, entry removable);
detector in `ref_alignment_audit.py`. Result: **s_dismas 0.756 -> 0.947, 86/124 -> 109/124 passing.**

This is a correction to our INPUT, not a laundering of our output: the numbering claim is falsified by
unanimous corroboration, and only corroborated shifts are corrected. Keep it distinct from §13 Q21 — a
divergent READING at a correctly numbered verse (gen 1:25) is a collation judgement that must be FLAGGED.

*The detector needed fixing before it could see its own headline case.* A raw token ratio found the shift only
against `odr_com`, because `sabates_a`/`madueke_b` are modern-spelling and `heauen`/`heaven` score as different
words — so the corroboration filter dismissed a 3-witness agreement as a 1-witness disagreement. Folding the
archaic/modern spelling difference in `_norm` is what lets a shift be corroborated ACROSS that boundary.
**Two other corroborated shifts are now visible and are NOT yet corrected** (`odr_com` genesis 39 from v7,
`s_dismas` genesis 26 from v5) — re-run the audit before extending to Genesis 2-50.

**Q25 (2026-07-29, RESOLVED — each reference must be scored with ITS OWN ARM).** `char_identity.evaluate_locus`
computes two identities: `archaic_id` (via `fold_archaic`, PRESERVING archaic orthography) and `modern_id`
(via `fold_modern`, folding it away). The Genesis 1 matrix was reading `archaic_id` for all four references,
which charges a faithful transcription for every `heauen`/`heaven`, `likenes`/`likeness`, `kinde`/`kind` — a
difference of EDITION, not of recognition, worth about 0.05 per cell. Scoring `sabates_a`/`madueke_b` on the
modern arm took the matrix from 455/496 to **477/496** with no change to any transcript.

This is also the project's own documented policy, which the matrix had drifted from (QC §1.4, revised by Sir
2026-07-10): *"the archaic gate is the quality bar; modern_id is a recorded signal but does NOT gate — a
faithful 1582 OCR must not fail for diverging from a modern edition."*

**Q26 (2026-07-29, RESOLVED — the largest OCR-side lever found in the sprint). The row reference must follow
the line's slope.** These leaves are photographed off bound volumes and the lines are not level: on
`archive-holiebible-ot1` p32 a single printed line runs from y=1157 at x=336 to y=1122 at x=999 — a 35px rise
against a ~30px tolerance. Grouping words by comparing each to the row's FIRST word therefore split every line
part-way across, the spurious row collected the neighbouring line's words, and sorting by x interleaved the
two. That is the entire reason S9 gen 1:21-29 read as word salad (0.646-0.826) while S1 and S3 — flatter scans
of the SAME edition — read the same verses at 0.92-0.98. Testing against the word LAST added to the row, with
a tight drift bound, took **S9 from 24/62 to 62/62** on the archaic references. The drift bound is the
dominant term and must be tight (see the sweep table in `gen1_pagemodel.py`); loosened, the reference walks
from one line onto the next and the result collapses to 0/248.

**Q27 (2026-07-29, RESOLVED — the unit that owns a layout is the LEAF, not the witness).** `jp2-S06` p18, the
chapter-opening leaf, was never configured (`open_page: None`) and is a THREE-column page: left cross-refs at
x 229-320, body, and a continuous prose annotation down the right margin from x 1692. Its scripture runs to
x 1670 while its ordinary leaves (p19) run to x 1789, so one right bound cannot serve both — 0.825 admitted
the whole annotation column. A per-leaf `PAGE_OVERRIDE` of (0.165, 0.765) took **S6 from 22/31 to 29/31**
all-four-references. The right bound carried essentially all of it (hi 0.825 -> 44/62; hi 0.765 -> 59/62);
`chapter_open_y` measured as a NO-OP on this leaf and is recorded as such rather than left in as decoration.

**Q28 (2026-07-29, RESOLVED). Catchwords and the two-part running head.** Early-modern leaves print the first
word of the NEXT leaf at the foot as a binder's aid. Read leaf by leaf that is one stray token; read as a
CHAPTER STREAM (§13 Q22) it lands immediately before the word it duplicates, and gen 1:12 arrived as
`grene grene herbe` in all three 1609 witnesses. Cut by position — last row, one or two tokens, beginning past
the middle of the measure. Separately, the second edition sets a two-part head (`GENESIS. Creation.`) that is
only 53% capitals and slipped the ratio test, carrying `genesis`/`creation` into gen 1:11. The extra signature
must be NARROW: keyed on initial-capital alone it deleted body rows opening `And God`, so it requires every
token capitalised AND full-stopped — punctuated as a label. Together: **477 -> 485/496.**

**Q29 (2026-07-29, RESOLVED — R3 closed the residual; Genesis 1 is 496/496). The 11 open cells were the
Rung-3 rung's job, and it did them.** Backend: olmOCR-2 via MLX, LOCAL, no paid API. Module: `gen1_r3.py`.
Result: 485/496 -> **496/496 = 100%** at >=0.90 against all four references, every source. Ablate the overlay
with `gen1_matrix.py --no-r3` to see the pure page-model figure.

| cell | incumbent (gov) | after R3 | what R3 fixed |
|---|---|---|---|
| S1 v13 | 0.924 | **1.000** | recovered the dropped `was` |
| S3 v13 | 0.924 | **1.000** | recovered the dropped `was` |
| S9 v15 | 0.933 | **1.000** | dropped the margin word `firſt` |
| S9 v18 | 0.943 | **1.000** | dropped the margin words `of` and `Di` |
| S9 v21 | 0.934 | **0.989** | un-scrambled the word order, dropped `for` |
| S6 v8  | 0.895 | **0.926** | `euenins`->`euening`, `mornins`->`morning`, `firmameut`->`firmament` |

*Three localization traps had to be cleared first, and the first one nearly hid the whole result.*

1. **A VERSE CROP IS NOT A VERSE.** `verse_geom.verse_crops` returns the band of LINES a verse occupies, so the
   crop carries its neighbours. Scored whole against a single verse reference, all six re-reads returned
   **0.000** — and they were all good. That is the third time this sprint a dead metric produced a confident
   wrong verdict (cf. Q18). The R3 text is now localized before scoring, on the JANVIER grid, never on the
   scoring reference.
2. **The grid must be restricted to the verses the crop contains.** Segmenting a 2-3 verse crop against the
   whole 31-verse chapter is under-constrained: asked for gen 1:15 it returned 1:14's text. The neighbour set
   comes from the page's own geometry — which verses' lines overlap the cropped band — so it is a fact about
   which pixels were sent, not a hint about the answer.
3. **But the restricted grid alone loses gen 1:13.** That crop ends just after v14's first word, too little for
   the segmenter to claim it, so `Againe` stays attached (1.000 -> 0.883). Three candidates are therefore
   segmented — full grid, restricted grid, and the hybrid `best_spans` (whose walk arm is the only one that
   trims `Againe`) — and the best JANVIER fit is kept. Same gold-free selection `best_spans` itself uses.

**THE ſ SURFACE WAS RESTORED BY OBSERVATION, NOT BY RULE.** olmOCR modernizes ſ->s, so adopting its text raw
would have traded the diplomatic surface — the point of the project — for a content score that cannot see the
difference (`fold_archaic` folds ſ/s; measured cost of the raw adoption: **7 long-s characters**).
`s_arbiter.transfer` takes R3's CONTENT with R2's OBSERVED spelling wherever the two agree modulo the ſ-fold —
R2/reichenau is itself a ſ-faithful visual recognizer, so those glyphs are attested. That restored `ſhine`,
`ſo`, `ſawe`, `ſorte`, `ſecond`. `long_s_rule.restore_long_s` was NOT used and must not be (~90.4% on this
project's gold = about 1 invented glyph in 10 presented as the printed surface).

**One token needed an eye, and the arbiter's guard caught me trying to smuggle a content fix through it.** S6
v8 token 4: R2 read `firmameut`, R3 read `firmanent`, and **neither is right.** Rendering the leaf at
y 0.788-0.818 and reading it shows `firmament. And it was ſo done. 8. And God called the firmament,`. Offered
to `s_arbiter.arbitrate` that reading RAISED — `sirmanent, -> sirmament,` — because arbitration is a SURFACE
path and the guard refuses content changes through it. That guard is correct and load-bearing (pinned by
`test_visual_content_and_surface_are_separate_paths`). The fix is now two separate, separately-visible things:
`VISUAL_CONTENT` carries the observed n->m correction and is re-scored; `VISUAL_READINGS` answers only the
question the arbiter exists for (is that `f` a ſ? — no, `firmament` contains no s at all). All six ſ-surfaces
are **CLOSED with zero unresolved tokens.**

**Adoption is gated mechanically.** A re-read is adopted only if it beats the incumbent on the governing archaic
arm AND clears the bar; better-but-short is recorded as a partial and the cell stays OPEN. Adopted cells are
overlaid and LABELLED `r3` in the matrix's provenance column — never blended in as though the page model had
produced them.

**Q30 (2026-07-29, RESOLVED — and it invalidated a PRODUCTION selector). `verse_locate.janvier_fit` returns
0.000 for any PARTIAL span.** It delegates to `char_identity.evaluate_locus`, which compares a WHOLE verse to
its own reference. Measured on genesis 16:9 against its janvier verse:

| input | fit |
|---|---|
| identical | 1.000 |
| the whole verse in archaic spelling | 0.959 |
| tail only (`and humble thyself under her hand.`) | **0.000** |
| head only (`And the Angel of our Lord said to her:`) | **0.000** |

Spelling is not the problem — partialness is. A verse that STRADDLES TWO LEAVES appears on each leaf only as a
partial, which is precisely the case leaf selection exists for, so every candidate scored 0, `max()` chose
arbitrarily, and the R3 crop came back transcribing **Genesis 15** (`the birdes he diuided not ... a deepe
sleepe fel vpon Abram`). It happened twice, under two different leaf-selection strategies, and adding a fit
FLOOR did nothing because nothing ever cleared it.

*The replacement.* `gen1_r3.span_fit` measures the fraction of the SPAN's own tokens that occur, in order, in
the janvier verse — deliberately PRECISION-like, so a partial is not penalised for the part it lacks. It
separates the cases cleanly: Genesis 15 leaves score 0.25, the correct leaves 0.85-0.92, and it fixed the leaf
choice on all three witnesses at once.

*Why this is a §13-level entry and not a footnote.* **`verse_locate.best_spans` uses `janvier_fit` for its own
hybrid selection.** If that selector is blind whenever a verse is partial on the page, it is blind at exactly
the BOUNDARY VERSES which the M-series measured as the historic all-fail class (verse-1-of-chapter 4.8x,
neighbour-on-another-page 2.7x). That correlation was explained as a page-shaped question asked of a
chapter-shaped object (§13 Q22); this is a second, independent mechanism pointing at the same verses, and it is
**UNINVESTIGATED CORPUS-WIDE**. Measuring it is cheap relative to any model work and may be worth more.

**This is the FIFTH instance of the dead-metric pattern in this sprint** — (1) the kraken seg-type probe scored
both arms 0.000 and read as a tie; (2) the R3 crops scored 0.000 on six good re-reads; (3) the matrix read
`archaic_id` for modern-spelling references, costing ~0.05/cell; (4) a leaf-vs-chapter comparison; (5) this. The
common cause is one function: **`evaluate_locus` compares a verse to ITS OWN reference and nothing else.** The
standing rule is now: *check that the metric MOVES before believing a null.*

**Q31 (2026-07-29, RESOLVED). The corpus localizer's LEAF attribution is unreliable at chapter boundaries.**
For genesis 16:9 `.corpus-localize-*.json` names `pdf-S03a` p84 — whose span for that verse reads `And the
foules lighted vpon the carcaſſes` (Genesis 15:11) — and `archive-holiebible-ot1` p90 (`a shee goat of three
yeares`, Genesis 15:9). It is correct only on `archive-ot1-1609`. So neither the localizer alone nor a fit
search alone can choose a leaf: the anchor is a HYPOTHESIS tested against `LEAF_FIT_FLOOR` (using `span_fit`,
per Q30), and a neighbour leaf is added only on TRUNCATION EVIDENCE — the span touching the leaf's first or
last body row, which is what a verse continuing off a leaf actually looks like.

**Q32 (2026-07-29, RESOLVED — the largest single R3 lever found, and it was geometry not recognition). The R3
crop was guillotining WORD BEGINNINGS, systemically.** `verse_geom.verse_crops` unions the verse's own line
boxes and pads 2%. On a leaf whose body left edge varies down the page (`jp2-S06` p76 is indented beside its
argument) that is not enough, and the vision model faithfully transcribes the fragment it is shown. One crop,
three x0 values:

    x0 = 0.2186 (as computed)  `...they first ed in the land`       <- `dwelled` beheaded
    x0 = 0.1886 (-3%)          `...they first velled in the land`
    x0 = 0.1386 (-8%)          `...they first dwelled in the land`  <- correct

Also `ke parts` for `backe parts`, `I hold` for `Behold`. `gen1_r3.widen_to_measure` keeps the crop tight in
**y** (which selects the verse) and full-width in **x** (which keeps words whole), margin 0.06. Worth
**0.09-0.16 per verse** — v3 0.896->0.986, v5 0.853->0.983, v6 0.846->0.968, v8 0.776->0.940. No amount of
merging two beheaded transcripts would have recovered the letters.

**Q33 (2026-07-29, PARTLY RESOLVED). The token-level merge of R2 and R3, and its bound.** Diagnosis first: R3
out-reads R2 on nearly every verse, and the union beats the better single arm by only ONE OR TWO tokens on
about half the open verses — so this is a last-mile lever, not the main event (Q32 was). `gen1_r3.merge_arms`
uses only what the recognizers establish between themselves: agreement -> take it; one arm has tokens where the
other has NONE -> take them (a dropout is not a reading); genuine disagreement -> keep R3 but RECORD the
conflict, and where the pair differs only by the ſ-fold keep R2 (the ſ-faithful arm). **It may never choose by
which token matches the scoring reference** — that would manufacture a transcript neither recognizer produced,
guided by the answer. It closed both `v16` cells, where each arm held a word the other dropped. Its limit
appeared at once: on `archive-ot1-1609` 16:14 the conflict `berwen Cadeſſe, | betwen Cadelle,` has R3 right on
one token and R2 on the other, the ſ-arbiter returned ALERT, and the leaf had to be read.

**Q34 (2026-07-29, RESOLVED — GENESIS 16 IS NOW 256/256 = 100%). The chapter stream duplicated boundary text,
and ONE junction was failing in TWO independent ways.** `S3 16:9` reached content 0.933 carrying `...Returne to
thy TO THY mistresse...`. The diagnosis was right that it is a page-model fault, not an R3 one, and right about
the catchword — but the catchword was only half of it, and the half that remained was the reason removing the
duplicate first made the cell WORSE (0.933 → 0.769, `missing returne to thy mistresse and`).

**(a) The SIGNATURE shields the catchword from `_is_foot_line`.** Early-modern leaves set the binder's
signature on the same foot row as the catchword and to its LEFT, which defeats both halves of the test at once:

| leaf | foot row | why it survived |
|---|---|---|
| `pdf-S03a` p85 | `H3 to thy` | 3 tokens > `FOOT_MAX_TOKENS` 2 |
| `pdf-S03a` p83 | `H2 † Abram` | 3 tokens, AND `row[0]["x0"]` 0.499 of the page vs a 0.511 threshold |
| `archive-holiebible-ot1` p89 | `H 2 † Abram` | the letter and its number as separate tokens — 4 |
| `archive-holiebible-ot1` p91 | `H to thy` | 3 tokens |

Fixed by stripping a leading run of signature-shaped tokens (`^[A-Z][a-z]?\d?$` or a bare 1–2 digit number)
before applying either test, and testing the position of the first REMAINING token. Measured over the Genesis 16
leaves this converts exactly those four rows and leaves every other short final row as body — including
`archive-ot1-1609`'s `com` / `m` / `amomn com`, which sit at 0.17–0.28 of the measure and are garbled text, not
catchwords. It never strips the whole row, so the position test always has something to judge.

**(b) `head_frac` was deleting a BODY ROW at the same junction.** On `pdf-S03a` p86 the running head
`62 GENESIS.` sits at y=30 and the first body line — `to thy miſtreſſe, and humble thy ſelfe vnder her hand.`,
which is the continuation of 16:9 from the previous leaf — sits at y=97, under a cut at 0.055·H = 167. So the
verse lost its own text. **This is the module's own documented lesson, applied to itself: the running head
cannot be cut by `head_frac` at ANY value.** `head_frac` now only BOUNDS where a head is looked for;
`_is_running_head`'s shape test is what removes it, plus one explicit clause for a bare folio number (too few
letters for the shape test to judge). A leading row in the head zone that is neither survives.

**Result: Genesis 16 256/256 = 100%**, means 0.986/0.986/0.980/0.980 → **0.990/0.990/0.984/0.984**. Genesis 1
holds at 496/496 with its means unchanged (0.982/0.981/0.968/0.968) — so both fixes are additive, not a trade.
**Closed with no model call**: the last "recognizer" residual of two chapters was two geometry bugs. 167 tests
(4 new: signature/catchword both shapes, the short-final-line bound, the body row in the head zone, the bare
folio number).

**Q35 (2026-07-29, OPEN — the ſ cost is quantified and does not scale). Should R3 be replaced with a
ſ-faithful model?** Across Genesis 1 and 16: 60 adopted cells / 1,532 tokens, **zero left surface-open after
`s_arbiter`** — but **44 tokens needed a human eye (2.9% of adopted tokens)**. Over 50 chapters that is on the
order of a thousand hand-reads. olmOCR-2 modernizes ſ->s because its OCR fine-tuning targets normalized modern
text (no prompt overrides it), and it modernizes SPELLING too (`therefore` for `therfore`, `afflicte` for
`afflict`, `selfe` for `ſelf`), a burden the ſ-arbiter does not even cover.

Order the evidence supports: **(1) improve R2** — `reichenau_dr` is ALREADY ſ-faithful, its weaknesses were
dropouts and n/u, g/s confusions, it has the cheap `ketos` loop, and the training data exists free in
`s_arbiter`'s `R2-observed` provenance tags; **(2) LoRA an open VLM** on those same ſ-faithful pairs (olmOCR-2-7B
weights are already cached; MLX-LoRA fits a Mac Studio); **(3) survey other open VLMs** first, cheaply, since
`r3_transcribe` is backend-pluggable — `qwen3-vl:8b` is RETIRED (thinking-lock, returns empty).

**What a better R3 would NOT fix**, and this bounds the expectation: edition divergence (S6 is 1635 against
1609 references), the span-boundary faults, and the reference defects Phase 1 exists for. **NONE of (1)-(3) is
started.**

**Q36 (2026-07-29, MEASURED — Q30's open hypothesis is CONFIRMED, and it is larger than a boundary effect).
`best_spans`'s selector is dead on a THIRD of every decision it makes in the live corpus.** Q30 left the
corpus-wide question unmeasured. `selector_corpus_probe.py` replays the live localize loop (`corpus_localize`'s
own `_line_range`, both arms, writing nothing) over **all 11 witnesses, 2,767 pages, 36,833 verse-spans** of the
pilot books:

| | |
|---|---|
| arms DIFFER — the selector actually has a decision to make | 30,510/36,833 = **82.8%** |
| selector DEAD — both arms score `janvier_fit` 0.000 | 12,782/36,833 = **34.7%** |
| DEAD **and** the arms differ — a **silent coin flip** | 12,411/36,833 = **33.7%** (40.7% of real decisions) |
| of those, `span_fit` is not dead | 10,715/12,411 = 86.3% |
| of those, `partial_fit` F1 separates the arms by >0.01 | 10,509/12,411 = **84.7%** |
| `partial_fit` would prefer WALK / ALIGN / neither | 4,470 / 6,039 / 1,902 |

Production takes the ALIGNER on **every one of those 12,411**, because `0.0 > 0.0` is false — not because the
aligner won. So on ~37% of the spans where a choice existed, the documented hybrid (measured at 0.9488 vs the
incumbent's 0.9215 on the gold pages) was not operating at all; the incumbent was. `partial_fit` would move
about **4,470** of them to the walk arm, so the null is not a harmless tie.

*The same defect at the second selection site.* `corpus_localize._better` arbitrates when two overlapping pages
both offer a verse — also on `janvier_fit`, with a length-ratio tiebreak for the fit-0 case. That tiebreak, not
the selector, decides **716/9,129 = 7.8%** of contested verses, and it is a proxy: it keeps `matthew/19/9`'s
38-token span at F1 0.20 over a 23-token span at 0.51, and `genesis/21/12`'s 37-token span at 0.11 over a
22-token one at 0.57. **`archive-holiebible-ot1` genesis/16/9 is in that list** — length keeps p90 at F1 0.13
while p91 scores 0.50 — which is the SAME wrong leaf Q31 found by hand (`a shee goat of three yeares`, Genesis
15:9). Q31's "the localizer is unreliable at chapter boundaries" and this are one mechanism, not two.

*The replacement, and why it is not `span_fit`.* `verse_locate.partial_fit` returns (precision, recall, F1) over
ordered token matches. Precision alone IS `span_fit`, and alone it is unsafe here: a ONE-TOKEN span scores
1.000, and the pathology fired for real in cross-page arbitration (`genesis/3/13`: a 1-token span at 1.00
beating a 12-token span at 0.58; `john/10/3` and `apocalypse/5/9` likewise). Recall restores what `janvier_fit`'s
length-awareness was providing. Under F1 the cross-page disagreements with the length proxy fall from 46.4% to
22.6%, and the survivors are longer, better-fitting text rather than fragments.

*Scope — it RESCUES, it does not replace.* On the 14 gold pages (`selector_probe.py`, judged on gold) replacing
the selector outright is NET NEGATIVE: `span_fit` alone changes 18 verses and loses all 18 (mean 0.9629 →
0.9484); `partial_fit` alone changes 16 and loses 16 (→ 0.9547). The incumbent is right wherever it can see —
it is blind, not wrong. Rescuing only the dead rows changes **0** gold verses, so it is safe there by
construction, and the gold pages cannot validate the GAIN because they are whole-verse pages by construction
(1/165 dead rows, against 34.7% corpus-wide). **That is itself a finding: the gold set does not exercise the
failure mode it was being used to rule out.** The judge shared the defect too — `evaluate_locus` against a
per-page gold is also partial-blind, which is why the single dead gold row reads 0.000/0.000 and looks like "no
gain available" when nothing was measured; `selector_probe` now reports a partial-tolerant F1-vs-GOLD judge
alongside it.

*A THIRD site, deliberately left alone.* `gen1_pagemodel_eval.witness_spans` selects among its leaf candidates
and the chapter stream with `f > best[v]["fit"]` — the same function, so an all-zero field keeps the FIRST
candidate in page order and the chapter-stream candidate (appended last) can never win a 0–0 tie. It is not
changed here because both worked chapters now stand at 100% and there is nothing to gain against a real risk of
regression; it is recorded so the next chapter's worker knows where to look if a boundary verse behaves oddly.

*THE CORPUS A/B — RUN, AND IT SETTLES THE SIZE QUESTION AGAINST THE HYPOTHESIS.* Each arm is a full
`corpus_localize` + `book_audit genesis` + `qc_audit` over the 5 pilot books (25,472 localized cells, 6,434
verses), with the production artifacts backed up and restored. **The baseline arm re-derived all-pass 799 /
all-fail 104 exactly**, so the comparison is sound.

| | baseline | both sites (`ODR_PARTIAL_FIT=1`) |
|---|---|---|
| Genesis cross-witness all-pass / all-fail | **799 / 104** | **799 / 104** — unchanged |
| overall pass rate (archaic-preeminent gate) | 0.6220 | 0.6200 (**-0.0020**) |
| cells fail -> PASS | — | **3** |
| cells PASS -> fail | — | **0** |
| newly localized cells | — | **87**, of which **80 score archaic_id 0.000** and 1 passes |
| cells no longer localized | — | **0** |
| `verse_cover_rate` | 0.9964 | 0.9964 — unchanged |
| per-source passed counts | — | every source equal or better (S3 +2, S9 +1) |

**Read it correctly, in both directions.** Nothing regressed: no cell lost a pass, no verse lost its
attestation, and every source's absolute pass count is equal or higher. The **rate** fell only because the
challenger adds 87 attestations to the denominator and 80 of them are worthless spans — the mirror image of this
project's standing rule that an un-localized verse leaves the denominator and inflates the score.

**But the yield is 3 cells in 25,472, and that answers the question this entry opened with.** The prevalence
(33.7% of decisions) and the yield (0.01% of cells) are three orders of magnitude apart, because the coin flips
land almost entirely on verses that fail for reasons the selector cannot touch — edition divergence, reference
defects, and scans too garbled for either arm to read. **So the earlier note that this "may be worth more than
either model change" is WRONG, and is corrected here: it is not.** It is a real defect and worth fixing for the
structural reason that a production selector must not report 0.000 as a decision — but it is not the lever on
the all-fail class. The 12,411 blind decisions were mostly blind about verses that were lost anyway.

*Status.* Wired at both live sites behind **`ODR_PARTIAL_FIT`, DEFAULT OFF**. The flag takes a SITE LIST —
`spans` (= `best_spans`) and `better` (= cross-page arbitration) — because the sites do not behave alike and had
to be attributed separately. 169 tests green with the flag off and on. **NOT ADOPTED.** Outstanding before it
could be: the `spans`-only arm (in flight) to attribute the +3 and the 87, and a re-measure of the cross-page
site now that the length band is its first key rather than F1.

**Q37 (2026-07-29, RESOLVED — a DEAD END, recorded so it is not re-attempted). The fully-worked chapters
CANNOT be harvested into R2 training data.** Item 2's premise was that two chapters at 100% of cells >=0.90,
ſ-surface closed, are free in-domain training data for `reichenau_dr` — "every token R2 gets right is a token
`s_arbiter` can transfer without an eye". `rung2_chapter_pairs.py` builds it: align each leaf's rows to the
witness's validated token stream, crop the row image, emit image/target pairs. It yields 218 pairs after safety
filters. **The pairs are nearly worthless, for two independent reasons, and the second one makes them harmful.**

1. **THE SIGNAL IS 6.4%.** Of 218 pairs, **204 targets are content-identical to what R2 already reads**. Only 14
   differ, and a target that agrees with the model teaches it nothing. (It also made the evaluation nearly
   circular: `reichenau_dr` scores 99.64% content accuracy on this val set, against 93.96% on the real one,
   because 93.6% of the val targets are its own output.)
2. **SOME OF THE 14 ARE WRONG, and wrong in the direction that damages a recognizer.** `archive-ot1-1609` p22
   and `jp2-S09ot2` p32 both print `and to gouerne the day & the night` — **verified by rendering the crop and
   reading it** — while the validated target says `gouverne`. Training that pair teaches the model to insert a
   letter that is not in the ink. Another target carries `:: Heauen:and` for the printed `Heauen: and`: an
   apparatus mark inserted and a space lost.

**The root cause is a GRAIN MISMATCH, and it generalizes past this attempt.** The chapters are validated at
VERSE grain, at >=0.90, against four references. That is the right standard for the deliverable and far too
coarse to serve as line-level diplomatic ground truth for a recognizer: a verse can sit at 0.97 while carrying
exactly the one-letter deviation a recognizer would learn as truth. **Verse-grain validation cannot be
re-purposed as character-grain supervision.** The reference-derived readings inside a validated verse are the
specific hazard — they are correct as collation and wrong as ink.

*What survives.* `rung2_chapter_pairs.py` is kept, with its filters, as a CANDIDATE-WORKLIST generator: those 14
disagreements are exactly the lines worth putting in front of an eye (`gt_review_server.py` exists for this), and
its three filters are findings in their own right — `clean_tokens` drops apparatus marks that are real ink,
`rejoin_break` joins words broken at the measure (crop ends `multi-`, target says `multiplie,`), and a row bbox
plus padding frames three lines of image against one line of target. All three were found by LOOKING AT A WRITTEN
CROP, none by reading code.

**Q38 (2026-07-29, OPEN — and this is where item 2 actually is). R2 was trained on 12% of the line-level ground
truth this project already owns, and the missing 88% is missing for TWO mechanical reasons.** `ground-truth/`
holds **2,611 hand-transcribed diplomatic body lines**. `rung2_prepare.py` converted **311**. The split explains
itself once counted:

| | files | GT body lines | in multi-page files | harvested |
|---|---|---|---|---|
| `scripture-*` | 16 | **423** | 0 | **311 = 74%** |
| `matter-*` | 34 | **2,188** | 1,576 | **0** |

1. **`rung2_prepare.main` globs `scripture-*.json` only**, so all 34 matter files — prefaces, arguments,
   recapitulations, summes, tables, title pages — are never considered. 2,188 hand-made diplomatic lines.
2. **`page_lines` returns `[]` when `page_index` is a LIST.** 11 GT files are multi-page (up to 24 pages for
   `matter-ot2-historical-table`), holding 1,576 of those lines. Measured on the first 10 gold pages:
   **584 of 617 lost lines — 95% — are this one cause.** The other losses are small and ordinary: 17 to kraken
   segmenting fewer lines than the page has, 14 to the greedy 1:1 assignment, 2 under `--min-sim` 0.45.

**The scripture harvest is NOT the problem — it already yields 74%.** So the lever is matter pages, and that
carries a real caveat rather than a free win: matter is the same press, the same founts, the same ſ usage and the
right GRAIN (hand-made, per line), but its content distribution is not scripture — tables of proper names and
numerals, and title pages set in display capitals. With no dictionary and no LM in the recognizer (both banned
for surface safety) a typeface match matters more than an n-gram match, so this is worth testing and NOT worth
assuming. The experiment that settles it: fine-tune with and without matter prose, and score BOTH on the
UNCHANGED 47-line scripture val split, which neither model has trained on. Adopt only on a scripture-val gain
with no fall in ſ recall. Tables and title pages stay separately tagged so they can be ablated on their own.

`rung2_harvest_audit.py` is the instrument (attributes each page's shortfall to skipped-multipage / no-raster /
seg-shortfall / below-min-sim / lost-to-greedy). **Full audit, all 50 gold pages: 2,611 GT body lines, 928
matchable under the old per-page path = 35.5%, and 1,605 of the 1,683 lost lines are `skipped_multipage`.** The
remainder is ordinary and small: 47 under min-sim, 17 seg-shortfall, 14 to the greedy assignment.

*A THIRD cause, found while fixing the second.* The old greedy loop marked `used_s`/`used_g` and only THEN tried
to crop, `continue`-ing on failure — so a line whose boundary polygon was degenerate consumed its gold partner
permanently and neither could ever be paired again. Cropping now happens once per segmented line, before
candidate generation, so a failed crop costs only itself. Effect on the harvest that was supposedly already
working: the scripture-only yield went **311 -> 364+ pairs with no change to the matching rule at all.**

**Q47 (2026-07-30, RESOLVED — THE GOVERNING LESSON OF THE CAMPAIGN). A rule is measured by the TEXT IT CHANGES,
not by the verdicts it flips.** `split_glued` — the mirror of the accepted hyphen join, splitting `oflife` into
`of life` when the glued form is absent from the book's lexicon and both fragments are present — measured across
50 chapters as **HELPS 8 / HURTS 1, net +8 cells, sentinels unmoved**. It was minutes from adoption. Counting the
TOKENS it altered instead: **1,356 splits**, the commonest being real words torn into morphemes —

    lawful -> law ful (28x)   earthlie -> earth lie (18x)   prayeth -> pray eth (17x)
    faithful -> faith ful (14x)   offereth -> offer eth (15x)   delight -> de light (13x)

A +8 net concealed 1,356 corruptions, invisible because they were score-neutral or fell in cells that already
failed. Neither guard could save it: `lawful` is genuinely absent from the lexicon (the book sets `lawfull`), and
edit distance cannot separate the classes — at 2 edits the garble `hofore` is refused but so are `oflife` and
`pleasantto`, the only cases the rule existed for.

**`faithfulness_audit.py` makes this a standing instrument.** First full audit (50 chapters, 931 leaves, 413,814
tokens): every ON-by-default rule is faithful and the rejected one was the outlier —

| rule | tokens changed | commonest | verdict |
|---|---|---|---|
| `clean_tokens` | 7,954 (1.92%) | verse numbers, `S.`, `c.` | faithful |
| `rejoin_break` | 2,363 (0.57%) | `therfore`, `Iacob`, `proſtrate` | faithful |
| `s_arbiter` archaic-equivalence | **16 (0.03%)** | `sonnes`->`ſonnes`, `lif`->`life` | faithful |
| `s_lexicon` ſ/f closure | 104 (0.23%) | `Isaac`->`Iſaac`, `fo`->`ſo`, `vſ`->`vs` | faithful |
| `split_glued` REJECTED | **1,356** | `lawful` -> `law ful` | CORRUPTING |

*A correction this produced.* The archaic-equivalence fix was reported as the change that unblocked the surface
gate. It alters SIXTEEN tokens in 2,162 verse pairs — its effect is on DEBT ATTRIBUTION, not on text, so the
reported gain came from the lexicon closures. Recorded so the credit sits in the right place.

**Q48 (2026-07-30, PARTLY RESOLVED). The reference gaps are a PARSE failure, and genesis 46 is recovered.**
`s_dismas` is built from `02-genesis.pdf` by pdftotext-parse and produced ONE verse each for genesis 8 and 46
instead of 22 and 34 — so both scored 0/88 and 0/136, read all campaign as catastrophic OCR failure. Three
causes, each read off the extracted text:

1. **Running heads.** The PDF repeats `Chapter 8` at every page break; treating it as a chapter restart discards
   everything before it. 49 of 50 chapters carry such heads.
2. **The ARGUMENT carries verse numbers** (`6. Noe ſendeth forth a crow, 8. after him a doue, 18. laſtly...`), so
   splitting on numerals makes the argument verse 1 and its phrases verses 6, 8, 18. The body's start is now
   found by matching janvier verse 1 — content anchor, never a spelling oracle.
3. **The ANNOTATIONS cite verses** (`19 Built an Altar.) Noe without expreſſe commandment...`), injecting
   commentary AND shifting every later verse. The PDF marks the boundary with a literal `Annotations` line.

**The validation gate was wrong before the parser was** — it compared the re-parse to the MODERN references by
character ratio and scored a CORRECT parse at 0.69 (`fourtie` vs `forty`, `paſſed` vs `passed`). Under the
project's own archaic arm genesis 46 scores **0.9696**, and is applied: **0/136 -> 107/136, no longer REF-GAP.**

**GENESIS 8 IS WITHHELD.** The PDF itself is mis-numbered there: it prints `15 And God ſpake to Noe, ſaying: Goe
forth of the arke ... with thee. 16 Al cattle...`, merging DR 15 and 16 under 15 and shifting the rest. The parse
is FAITHFUL to its source; the source disagrees with the other three witnesses. That is a corroborated
`ref_renumber.CORRECTIONS` **split**, not a parser fix — NEXT ACTION, and papering over it in the parser would
hide an editorial fact behind a code change.

**Q48 (2026-07-31, RESOLVED). The reference-gap class is gone: 704 blocked cells -> 4.** Genesis 8 was blocked
TWICE OVER, by faults of different kinds that the count test could not tell apart, and the second only became
visible once the first was fixed — a pattern that then repeated at chapters 46, 30 and 44.

* **PARSE faults, which are ours to fix.** A page-foot note block spliced into the MIDDLE of a verse (two
  marginal notes, the page number, and the facing page's running head `Genesis`, between `...cogitation of`
  and `mans hart are prone to euil`) — not a suffix, so no end-of-verse trimmer could reach it. And a chapter's
  TAIL emitted behind the NEXT chapter's running head: genesis 30's verses 39–43 sit after the line
  `Chapter 31`, land in block 31, and are correctly discarded there as pre-verse-1 matter.
* **NOT parse faults.** The edition merges DR 15+16 under a printed `15` and numbers the rest one lower. The
  parse is faithful to the page; the correction is a corroborated `ref_renumber` split.
* **A HOLE IN A NEARLY-FULL CHAPTER IS INVISIBLE TO A COUNT.** Genesis 30 held 42 of janvier's 43 and passed
  `h >= 0.9 * jn` while its verse 6 read `...geuing me againe Bala conceauing bare an other`. The repair
  criterion is now "the re-parse carries verses the stored reads LACK", judged by the cross-reference gate.
* **A MERGE LEAVES ONE OF TWO WOUNDS.** Either the source renumbered everything after it one lower (genesis 8),
  or it left a HOLE and carried on correctly (odr_com genesis 34 prints verse 29 as `28`, then a correct 30 and
  31). `split` renumbered unconditionally and gave chapter 34 a verse 32 that no edition has. The reference
  says which without judgement: **if a+1 is absent, there is nothing after the merge to move.**

**Q49 (2026-07-31, RESOLVED — AND THE MOST EXPENSIVE ONE). `odr_com` lost 196 verses to one optional quote,
and the loss had been MEASURED at acquisition and never read.** The apparatus boundary was matched with
`id\s*=\s*['"]?Annotations['"]?[^>]*>`, whose optional closing quote also matches the PREFIX of
`id="Annotations2"` — and that id is not apparatus. On this site it is a STYLE whose meaning is positional:
after the ANNOTATIONS. header it wraps annotation prose, before it, plain scripture (genesis 4 carries verses
8–15 and 16–26 in two such spans). Every chapter using it was cut at its first occurrence: genesis 4, 6, 9 at
verse 7, 11 at 9, 13 at 4, 49 at 2. **Nine Genesis chapters classed REF-GAP, 596 cells outside the achievable
set, for a year of campaign work.**

The scrape manifest had recorded `verse_count_match: 37/50` for genesis and a chapter-bag agreement (0.8559)
far below the per-verse agreement (0.9292) — a gap the manifest's OWN documentation defines as isolating
"text loss". **The number was written down in July and nothing consumed it.** A measurement that no gate reads
is not a safeguard; it is a comment. Where an acquisition step reports a fidelity figure, something must FAIL
on it.

**AND THE HEADLINE RATIO FELL WHILE THIS WAS FIXED — 0.7916 -> 0.7884 — because 596 cells that had been
excluded from the denominator as unreachable were now measured.** Read the two numbers as rates over different
populations, not as progress and regress. The campaign's rate is only comparable across revisions in which the
achievable set is the same; **quote the achievable count beside the ratio, always.**

**Q50 (2026-07-31, RESOLVED — AND IT REDIRECTS THE WORK). The three S6 causes, sized separately at last.**
`s6_causes.py` classifies every open cell by the SHAPE of its alignment against the archaic reference, checks
each against an independent attribution (does the cell contain a word that appears in that chapter's apparatus
and in none of its verses?), and cuts the population a third way that needs no classifier at all.

| | S6 | S1 | S3 | S9 |
|---|---|---|---|---|
| open cells | **568** | 242 | 211 | 174 |
| INTERLEAVE | 100 (17.6%) | 25 (10.3%) | 14 (6.6%) | 35 (20.1%) |
| MISREAD | **255 (44.9%)** | 96 | 73 | 41 |
| DIVERGE | 198 | 119 | 114 | 90 |
| NO-TEXT | 14 | 2 | 10 | 8 |
| fails in this source ALONE | **399** | 40 | — | 46 |
| fails in ALL FOUR | 40 | 40 | 40 | 40 |

**EDITION DIVERGENCE IS CAPPED AT 40 CELLS, 0.65% of the book.** It is a property of the page all four sources
photographed, so it cannot fail in one source alone — the all-four-fail set is its ceiling, and no classifier
is needed to bound it. It has been carried as one of three co-equal causes since the S6 work began.

> **CORRECTION (2026-08-01). THE 40-CELL CAP IS VALID FOR S1, S3 AND S9 AND IS FALSE FOR S6. DO NOT CITE THE
> PARAGRAPH ABOVE WITHOUT THIS ONE.** Its reasoning — "a property of the page all four photographed, so it
> cannot fail in one source alone" — assumes the four sources photographed the SAME page. **S6 is the 1635
> second edition and both archaic references are 1609, so for S6 it is a DIFFERENT PAGE and its divergence can
> and does fail alone.** See `CHAPTER-WORKFLOW.md` B7 rung 2 and the signal-6 correction in its §3 router,
> where the same error cost 20 cells at the routing layer.
>
> Sized board-wide 2026-08-01 over all 6,116 cells with per-reference scores (`band-cells.json`): the arm gap
> `min(MODERN) − min(ARCHAIC)` is **-0.0110 median for S1, S3 and S9 alike** — the metric artifact, identical
> to four decimals, which is what makes the 1609 trio a clean control — and **+0.0000 median / +0.0099 mean
> for S6**. Cells an edition-correct reference could carry across the bar: **31 for S6 vs a control mean of 9**
> ⇒ **~22 cells of real edition divergence for S6, on top of the 40 all-four cells.** Above the bar a further
> **~430 S6 cells** are archaic-limited in excess of control — not board-visible, but their headroom is
> compressed by the wrong instrument.
>
> **This correction cuts both ways and a future session can be misled in either direction.** The cap is too
> LOW for S6 (it is not 0, it is ~22 board cells and ~430 masked ones), and the corrected figure is far too
> SMALL to justify a reference-acquisition push on yield grounds. **The paragraph below — "S6's excess is
> source-specific reading quality, not apparatus" — is UNAFFECTED and still holds:** 369 S6 cells sit below
> 0.876 against ~90 for each 1609 source, and no reference swap reaches them.

**S6's excess is source-specific reading quality, not apparatus.** 399 cells fail in S6 alone against 40 and 46
for S1 and S9; the excess sits in MISREAD, and S6's INTERLEAVE share (17.6%) is *below* S9's (20.1%). **A ninth
apparatus-separation attempt would target at most a fifth of S6's failures — a share S6 does not even lead.**

**THE FIRST VERSION OF THE CLASSIFIER RETURNED THE OPPOSITE ANSWER AND WAS ENTIRELY CONVINCING.** Classifying
on aggregate overlap (high recall, low precision => interleaved) it reported 4 interleaved cells against 414
divergent — because two words of marginal text pushed into a twelve-word verse move neither ratio: `the heauens
therfore the earth were fully finiſhed, and 17conſeruins al the furniture of them` scores recall 0.93 AND
precision 0.93. **A summary table is not evidence about the thing it summarises unless someone reads its
examples**; printing three per bucket is what exposed it, and the tool now says so in its own docstring.

Two caveats stand, both measured: INTERLEAVE is a LOWER BOUND (23% of DIVERGE cells also carry an attributable
apparatus word, vs 46% of INTERLEAVE and 10% of MISREAD), and DIVERGE cannot mean *edition* divergence for any
cell failing in one source alone.

**Q13 (2026-07-28, RESOLVED). Why did 659 scan-verses leave scope?** `corpus_localize._line_range` took only
the FIRST `printed-heading` pin (defect #8). A chapter owns TWO pin segments whenever its heading falls
mid-page — a `carry-in` run before it and a `printed-heading` run after — so **3,006 pages were truncated to
the post-heading lines and 67,284 body lines were discarded**, taking real, well-fitting verses out of scope
with them (`jp2-S04` p680 is Apocalypse 1 across all 83 lines with `CHA P. I.` at line 44; lines 0–43, holding
Apoc 1:11–15 at janvier fit 0.79–0.98, were thrown away). A second, opposite failure: **275 pages** whose
chapter had only a `carry-in` pin got the WHOLE page. Both are gone now that the range is the union of every
pin naming the chapter. The defect predates the heading-parser fix but was unreachable before it, because
almost no `printed-heading` pins existed to truncate on. Mechanism proven by reconstruction: restoring the old
parser reproduced v026's S4 attestation count exactly (2,325). Front matter was a red herring — an A/B with
the parser held constant moved `jp2-S04` by +1. Result: **v029 IMPROVED**, `pass_rate_archaic` 0.5902→0.5913
and `source_fail_mean` 0.4053→0.4044, both past the pre-fix baseline.

**Q14 (2026-07-28, PARTIALLY RESOLVED, still OPEN and BLOCKS). `jp2-S06` honest held-out is 52.15%.**
The residual coverage gap that pointed here is CLOSED — it was defect #9, page furniture read as a chapter
heading. `jp2-S06` p1085 line 50 of 52 reads `Pſal. 30` below the last body line, after a catchword and beside
the next leaf's `T H E B O O K` header; as decisive evidence (+4.0) it addressed the page to Psalm 30, and the
monotone chain then dragged p1086–1088 along, erasing Psalms 27–29 (content alone had them right, and p1086
carries Vulgate Ps 28:6–7 verbatim). A heading now requires a body line after it on the page (68/4,085 = 1.7%
of detections fail that). All 11 lost loci are restored and coverage is +3 above the pre-fix baseline.

**The superscription-offset hypothesis was checked and REJECTED** — psalms 26–29 sit in the realigned region,
but the cause was furniture, not versification. Record that so it is not re-proposed.

What remains: S06 is still the worst volume by a wide margin (52.15% vs ~87% next worst) and its heading-vs-DP
disagreement is 4.77% against ~1% elsewhere. Do NOT assume a single cause — characterise the remaining 4.77%
page by page before proposing one.

**Q15 (2026-07-28, RESOLVED-BY-POLICY, but record the choice). Which mode is the deliverable built from?**
Every cached `.page-address-*.json` had been built with `use_headings=False` — the held-out validation config
used as the production basis, i.e. the DP was denied the printed headings while addressing the corpus. Now:
production (`--use-headings`) writes `.page-address-<v>.json`; held-out writes `.page-address-<v>.heldout.json`
and exists ONLY to measure. If a future session sees these diverge, the production file is the deliverable.

**Q16 (2026-07-28, closed but load-bearing). Any hand-typed rule must be validated against the CORPUS, not
just against the canon.** Defect #6 was not a canon disagreement — `CHAP_HEAD` was internally consistent and
simply did not describe what the printer printed. The existing rule ("validate every hand-typed list against
the canon at import") would not have caught it. The corpus-facing analogue: for any pattern that gates
evidence, measure its HIT RATE against the corpus and treat a low rate as a defect rather than as a property
of the material.

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

6. **Apparatus / matter has no ADDRESS.** The tome-map records only `scripture` / `book-front-matter` /
   `no-scripture` page kinds, so a front-matter table or a back-matter treatise cannot be looked up, scored, or
   routed to a rung. Sir has twice stated front/back matter is in scope at every stage. **This is the M1 build
   and it blocks the matter work entirely.**
7. **No verified jp2↔PDF page mapping.** The three renderings of a volume disagree on page count and the
   deltas are not uniform (S09-OT1: OCR 1160 / jp2 1159 / PDF 1156), so no single rule maps one to the other.
   The PDFs carry no text layer, so each offset must be verified by IMAGE — eleven verifications.
8. **`jp2-S06` OCR underperforms its own PDF twin** (paired Wilcoxon p=4e-78) despite the jp2 being
   5100x6601. The comparison is CONFOUNDED — two OCR runs differing in source *and* settings — so it proves the
   stored jp2-S06 OCR is bad, not that the image is worse. Under "all OCR redone from jp2" the answer is to
   RE-OCR jp2-S06 at proper settings and re-measure, not to switch S6 to the PDF.
9. **`archive-holiebible-ot1` was 380 pages short of OCR** (a run that died and was never resumed; now
   complete at 1159/1159). Nothing reported it because a page that was never OCR'd is in no denominator —
   it is invisible rather than failing. `integrity_sweep` C9 now watches for this class.

*(Resolved this rev: ocr_consensus → retire; draft golds → count now; witness "noise" → artifact, no demoting.
Resolved rev 5: Q5 colossians-3 addressing — `jp2-S08` p571 now addresses correctly as colossians/3 once the
witness inventory replaced tome-map's metadata; Q2 S9-OT2 — `jp2-S09ot2` IS S9's OT2, jp2-mapped with a
verified -1 offset.)*

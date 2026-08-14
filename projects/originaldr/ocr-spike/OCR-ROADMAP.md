# OriginalDR — Development Roadmap

The executable counterpart to `OCR-MASTERPLAN.md`. The plan states *what must be true*; this file states
*what is built, in what order, and how each step is verified*. Every step names its deliverable, its
acceptance test, and the plan section it discharges.

**Current phase: pre-initialisation — Gate 0 (corpus).** No transcription work begins until Gate 0b and 0c
are satisfied for the leaves concerned (§2).

---

## Status index

**Sections appear below in the order they were written, which is not numeric order** — R6 and the dissolved
R3.5 sit between R4 and R5, because R5 was folded down from the former step 4 after R6 was drafted. The file
is the execution reference, so the index rather than the file order is authoritative for *what is open*.
Renumbering was considered and rejected: step ids are cited from the Masterplan, the companions, four
guards' comments and every devlog entry, so the ids are load-bearing and the ordering is not.

| section | subject | status |
|---|---|---|
| R0 | Witness identity and stable addressing | **COMPLETE** (R0.1–R0.5) |
| R1 | Physical leaf inventory — Gate 0b stage 1 | **COMPLETE** (R1.1–R1.6) |
| R2 | Structural inventory — Gate 0b stage 2 | **OPEN — IN PROGRESS 2026-08-10/11.** R2.0 instrument built in `.scratch/r2/` (probe v18; design settled, dead ends measured) — **nothing in `witness/` yet**, and it has **never been scored on R2.1's actual metric** (signature-per-recto; every panel to date counted *any token, either parity*). ~3h of the 12h ceiling. Steps R2.1a–f written 2026-08-11 |
| R3 | Cross-source leaf mapping — Gate 0c | **OPEN.** Nothing built (R3.1–R3.4) |
| R3.5 | NT's 36-leaf difference | **DISSOLVED** — the number was malformed. R3.5b, R3.5c live |
| R4 | Bibliographic completion — Gate 0a residue | **PART.** R4.1d/R4.2/R4.3/R4.4 done; R4.1e, R4.2a, R4.5, R4.6 open |
| R5 | Raster policy — **Gate 0d** | 🟢 **BUILT AND ENFORCED on all three clauses, 2026-08-10** (R5.1 · R5.2a–c). R5.1's manifest is complete — **3,122 leaves, 0 rasters unmanifested**, so the dimension clause moved UNKNOWN→CHECKED on 3,113 leaves and the pre-registered deferral never fired. Determinism proven: a second full build is byte-identical. Previously read "R5.2 has no proven negative", which described a guard that runs; **none was ever written** |
| R6 | `S06` frontmatter/backmatter collation | **PART.** R6.1–R6.3a, R6.5 done; R6.3b/c, R6.4-remainder, R6.6a–d open |
| R7 | Ground truth read from inadmissible rasters | **OPEN — 48 of 51 files.** R7.5, R7.5a, R7.5a-3, R7.5b, R7.5c, R7.5d **DISCHARGED**; R7.1–R7.4 and **R7.5a-2** (**261** derived artefacts to regenerate, was 339) open |
| R8 | `F`'s New Testament is the 1633 edition | **PART.** R8.1, R8.2, R8.4, R8.4a, R8.5, R8.8 done; R8.3, R8.4b, R8.6, R8.7 open |
| R9 | Evidential scope per witness — Gate 0f | **PART.** R9.0–R9.4b done; the gate was **enforced but bypassable** until 2026-08-10 — **R9.2c DONE** (the 9 modules that read around the read path are converted; it exposed a containment fact read as a scoring permission, and a parity metric that was restating the best witness's pass rate) — **R9.5a** (companion table disagreed with the registry) · **R9.6/R9.6a** (migrated project root restated in five modules) open |
| R10 | The constitution's own machinery — §0.5 | **PART.** 🟢 **R10.1 BUILT** — `witness/audit_prereq_ceilings.py` runs and reports **17/46** OPEN steps carrying a ceiling + rule (exit 1 = healthy; the fraction must RISE). 🟢 **29% → 36% on 2026-08-14**, again by the planning half: R11 arrived with three ceilinged OPEN steps. 🔴 **R10.2 OPEN — nothing built**, `PROVISIONAL.md` does not exist. ⚠️ This row read "Nothing built" for both until 2026-08-11 while the audit was live and listed in the verification block below — and §0.5 named it as a *guard* called `test_prereq_ceilings.py`, which has never existed |
| R11 | Tracked code only one machine can run — §0.2 rule 6 | **PART, NEW 2026-08-14.** 🟢 **R11.1 DONE** — the gold suite's harness (33 files / 432 KB) is TRACKED at `core/tests/fixtures/gold/harness/`; the three consumers run **byte-identical with the untracked original deleted**. 🟢 **R11.2 GUARD BUILT** — `test_no_scratch_deps.py` exits 0, injection-proven. 🟢 **R11.3 DONE** — the silent candidate-fallback now raises, and it exposed `MADUEKE` **already resolving to a nonexistent path**, emitting books with no Madueke text while reporting success. 🔴 **R11.2a OPEN** — `audit_scratch_data_paths.py` exits 1 → **71 data references across 38 tracked files**, twelve times the blast radius the recommendation was written for. 🔴 **R11.3a** (pin Sabates_A to a SHA) · **R11.4** (`purge_empty_ocr` → R9.6) open. **R11.5 (reclaim ~7 GB) BLOCKED BY CONSTRUCTION** |

### Open-items register

Maintained here so that "what is left" is answerable without reading 600 lines. **This register is
authoritative over prose elsewhere in the file**; where a paragraph and this table disagree, the table is
right and the paragraph is a bug to be fixed.

**Extended 2026-08-10 (Sir): the register now outranks the Master Plan's status lines and the companions
too.** Full ordering in Master Plan **§0.6 Precedence** — code and guards, then this register, then the
Master Plan, then the companions, then the devlog. The extension was made because the 2026-08-10 review
found the drift running from the top down three times in one sitting: §2 claimed Gate 0e verified on "the
full §0.3 criterion" where this register recorded the foot criteria proved at one point of three; §2 claimed
Gate 0f "discharged by R9.1–R9.4" where R9.2c recorded nine modules reading around it; and §2, this file and
the Walkthrough all described Gate 0d as a guard awaiting a negative test when **no such guard existed**.
**The thing that can refuse a claim outranks the thing that can only assert one.** A lower document that
disagrees is a defect to be fixed, not merely overruled.

⚠️ **Every OPEN step must carry an hour ceiling and a pre-registered decision rule** (§0.5). That
requirement was in the constitution from the start and **no step had ever carried either**, which is why R2
and R3 — the two sections gating everything downstream — stood at "NEXT, nothing built" indefinitely.
Ceilings are being added section by section as each is next touched; `witness/audit_prereq_ceilings.py`
**reports** (exit 1, healthy) the OPEN steps with neither — it is an **audit, not a guard**, for the
reason spelled out in R10.1, and this paragraph named a nonexistent `test_prereq_ceilings.py` until
2026-08-11. **A ceiling escalates and never closes a step**: reaching it raises an
ALERT that the *approach* needs redesign, which is the opposite of accepting a lowered result.

**OPEN** — R2.1 (R2.1a · R2.1b · R2.1c · R2.1d · R2.1e · R2.1f) · R2.2 · R2.3 · R2.4 · R3.1 · R3.2 · R3.3 · R3.4 · R3.5b · R3.5c · R4.1e · R4.2a · R4.5 ·
R4.6 · R6.3b · R6.3c · R6.4-remainder (OT2/1610 prelims,
endmatter Tables, body rewording) · R6.6a · R6.6b · R6.6c · R6.6d · R7.1 · R7.2 (1 of 4 done) · R7.3 · R7.4 ·
**R7.5a-2** (**261** artefacts, was 339) · R8.3 · **R8.4b** · R8.6 · R8.7 · **R9.5a** · **R9.6** ·
**R9.6a** · **R10.1** · **R10.2** · **R11.2a** · **R11.2b** · **R11.3a** · **R11.4** · **R11.5** (blocked)

**DONE** — R0.1–R0.5 · R1.1–R1.6 · R4.1d · R4.2 · R4.3 · R4.4 · R6.1 · R6.2 · R6.3 · R6.3a · R6.4 (tome 1) ·
R6.5 · **R7.5** · **R7.5a** · **R7.5a-3** · **R7.5b** · **R7.5c** · **R7.5d** · R8.1 · R8.2 · R8.4 · **R8.4a** · R8.5 · **R8.8** · **R9.0** · **R9.1** · **R9.2** · **R9.2a** · **R9.2b** · **R9.3** · **R9.4** · **R9.4a** · **R9.4b** · **R9.2c** (with R9.2c-1…-4) · **R5.1** · **R5.2a** · **R5.2b** · **R5.2c**

**DISSOLVED** — R3.5 (body retained, marked not to be executed)

⚠️ **Six "DONE" marks are narrower than they read**, and are spelled out where they occur rather than
here: R4.2 is done as an explicit *NOT ESTABLISHED* verdict, not as a repository found; R6.4 is done for
tome 1 only; R8.4 verified 11 of 12 witnesses and **named the twelfth unverifiable** rather than assuming it
sound; **R8.4a verified the foot criteria at ONE matched page per setting**, where the head pass used three or
more — R8.4b is the remainder and stays OPEN; **R9.4b** recomputed all 76 consensus books but the figures it
*replaced* remain quoted in the devlog and companions, which is R9.4b's labelling half and is folded into
**R10.2**; **R9.5** was marked done while the Overview still carried the pre-R9.0 role — re-opened as
**R9.5a** with a machine-checked acceptance. A register that flattened these to "done" would be doing the
laundering it exists to prevent.

🔴 **Changes in this revision (2026-08-10 review).** `R5.2` split into **R5.1 + R5.2a/b/c** because the
guard was found never to have been written, not merely untested. **R9.4a/R9.4b closed** — `X` was fused
into the consensus as an independent seventh witness and all 76 books are regenerated with the gate live
(0 now fuse an inadmissible source). **R9.5 re-opened as R9.5a.** **R9.6/R9.6a** added for the migrated
project root (and to retire an id collision: the step was briefly numbered R9.5 in two code comments).
**R10** added for the two constitutional requirements that had no steps at all.

---

## R0 — Witness identity and stable addressing

**Discharges** §1.1. **Status: COMPLETE.**

| # | step | deliverable | acceptance |
|---|---|---|---|
| R0.1 | Canonical witness registry | `witness/witnesses.py` — sigla, volume, year, role, repository, source path | registry leaf counts equal on-disk counts for all **11 files** |
| R0.2 | Stable witness tree | `sources/witnesses/<VOL>/<WID>/leaves` symlink farm + `MANIFEST.json` | every witness path resolves; leaf counts match registry (**12/12**) |
| R0.3 | Naming convention documented | §1.1 "Addressing and sigla" | a reader can map any legacy id to a witness id and back |

**Design note — symlinks, not copies.** Copying the JP2 packages would duplicate ~11 GB and create a second
artefact that can drift from the first. A symlink gives the stable path without a second copy, and a broken
link fails loudly where a stale duplicate would fail silently.

**R0.4 — reopened by §1.2: the tree points at renders for `F` and `X`.** The farm links every witness to its
JP2 package, which is correct for the six institutional captures and **wrong for the four `S01`/`S08`
files**, whose JP2s are IA renders of an uploaded PDF. Structural work is unaffected — a render preserves
page content and page order, so the R1 leaf inventory and the R2/R3 collation stand — but **no pixel-level
measurement, training crop or CER evaluation may be taken through those links.**

| # | step | deliverable | acceptance |
|---|---|---|---|
| R0.4 | Primacy recorded per witness | `witnesses.py` gains `primary: "jp2" \| "pdf"` and, for `pdf`, the page-extraction path | every witness declares its primary artefact; the field is sourced from the IA `source`/`original` chain, not guessed |
| R0.5 | Render guard | load-time assertion at the pixel-consuming entry points | a `primary: "pdf"` witness accessed through the JP2 link **raises**, proven by a negative test |

**R0.5 needs the negative test for the same reason R5.2 does.** A guard that has never rejected anything is
not known to work — and this is precisely the class of error that produced the 3334 × 4684 misreading, so
the guard exists to make that error loud rather than plausible.

---

## R1 — Physical leaf inventory (Gate 0b, stage 1)

**Discharges** §2 Gate 0b, first half. **Status: COMPLETE.**

| # | step | deliverable | acceptance |
|---|---|---|---|
| R1.1 | Per-leaf physical classifier | `witness/inventory_leaves.py` → `TEXT / BLANK / SPARSE / PLATE / BINDING` per leaf | runs over all 10 witnesses; one JSON per witness |
| R1.2 | Witness-relative thresholds | saturation judged against the witness's own distribution | a uniformly sepia rehost is not misread as 42 colour plates |
| R1.3 | Leaf-count reconciliation | §1.1 table: every leaf-count difference attributed | each difference expressed as binding + blanks + duplicates + supplied + genuine textual difference |

**Design note — why thresholds must be relative.** Absolute saturation cannot separate a marbled endpaper
from a warm-toned scan: a sepia rehost saturates as strongly as a colour plate. What marks a plate is
standing out *against its own book*, so the cut is taken from each witness's own distribution.

**R1.4 — the same argument applies to ink, and applying it to saturation alone was a bug.** The first
reconciliation reported **zero** lead, trail and interior blanks for all three `F` witnesses, which reads
as the finding *"the rehost stripped its blanks"*. It is not a finding. A contrast-boosted rehost raises
its background everywhere, and the `F` ink floor is **0.196** against a BLANK cut of 0.010 — above the `B`
witnesses' **median** of 0.25. `BLANK` and `SPARSE` could never fire on those witnesses, so the zero was
the threshold's shape, not the book's.

| # | step | deliverable | acceptance |
|---|---|---|---|
| R1.4 | Resolvability check before classification | `label()` tests each witness's ink floor **against the cut it is about to apply** and emits `TEXT?` where blanks are indistinguishable | the four re-uploads report **UNRESOLVABLE**, the six genuine captures are unaffected |
| R1.5 | Summaries account for every leaf | per-kind counts printed for kinds *present*, with `sum == n` asserted | a new kind cannot drop out of the summary while `n` stays correct |
| R1.6 | Offline relabelling | `witness/relabel.py` re-applies `label()` to stored features | a threshold revision costs seconds, not a ~40-minute image pass over eleven witnesses |

**The criterion had to be corrected once, and how it failed is worth keeping.** The first version asked
whether the ink floor was a small fraction of the *median*, and that split the three `F` witnesses
inconsistently — `OT1` tripped at 0.196/0.350 while `NT` passed at 0.193/0.409 — although not one of them
has a single leaf below ink 0.06. The median is a property of the *text*, so a ratio against it measures
contrast rather than detectability. The question is only ever **"could a blank leaf be caught by the cut
about to be applied?"**, so the floor is compared to `BLANK_CUT`. That separates the corpus exactly:

| class | ink floor | witnesses |
|---|---|---|
| genuine capture | **0.0000** | `B` ×3, `P` ×2, `R` |
| re-upload | **14–20× the cut** (0.141–0.196) | `F` ×3, **`X`** |

**`NT-1582-X` was the fourth, and it was not predicted** — the check found it. And `NT-1633-R` sits in the
genuine class *because* its original was acquired (R4.4), so this is a fourth corroboration of the primacy
split of §1.2, arrived at from an unrelated measurement.

**Why this is R1.4 and not a footnote.** Zero is a measurement; *unmeasurable* is not, and the two must not
print the same. The failure mode is the one this project keeps meeting — a derived or degraded artefact
returning a well-formed number that reads as evidence. R1.5 exists because the summary enumerated a fixed
list of kinds, so `TEXT?` would have vanished from the totals while `n` stayed right: the unresolved leaves
would have looked accounted for.

**Consequence for `F`.** This is a **second and independent limit** on these witnesses, and it is narrower
than the resolution one: it bars them from **completeness** questions specifically. They carry **page
order**, but whether a leaf is wanting, blank or supplied is not recoverable from them, because their
processing raises the whole leaf and no blank can be distinguished from a lightly-printed one.
Completeness rests on the `B` and `P` witnesses. Note this is a limit on *these files*, not the
withdrawn "structure only" verdict on the copies (§1.1a).

---

## R2 — Structural inventory (Gate 0b, stage 2)

**Discharges** §2 Gate 0b, second half. **Status: NEXT.**

| # | step | deliverable | acceptance |
|---|---|---|---|
| R2.1 | Signature reader | OCR the signature line (`A ij`, `Aaa 4`) from the foot of each recto | ~~≥95% of rectos yield a parsed signature on the base exemplars~~ **WITHDRAWN — UNSATISFIABLE BY CONSTRUCTION, see R2.1-CRIT below.** Replaced by R2.1d′; failures listed, never guessed |
| R2.2 | Printed-page-number reader | OCR the head of each leaf | ≥95% on the base exemplars; both readers abstain rather than emit a low-confidence value |
| R2.3 | Collation model | expected gathering structure per volume, derived from observed signatures | the derived collation reproduces the observed sequence with no unexplained gaps |
| R2.4 | Defect report per witness | wanting / duplicated / misbound / made-up leaves, each named | every leaf either fits the collation or appears in the defect report — **no leaf unaccounted** |

**Sequencing note.** R2.1/R2.2 are OCR tasks on a tiny, highly regular target (a short line in a fixed
position), not the edition's recognition problem. They must not wait on the recognizer, and their failures
must abstain: a mis-read signature would corrupt the collation that everything else is checked against.

🔴 **R2 IS THE CORPUS'S CRITICAL PATH, NOT ITS HOUSEKEEPING (stated 2026-08-10).** §2 rules that *"no
transcription of any leaf begins before 0b, 0c and 0e are satisfied for that leaf."* R2 is Gate 0b's second
stage and R3 is Gate 0c, and **both are "nothing built"** — while `ground-truth/` already holds **51
transcribed files**. Every one of them was transcribed ahead of the rule. This is a *separate* defect from
R7: R7 asks which photograph a reading was taken from, R2/R3 ask whether the leaf is the leaf it was called
— a duplicate, a misbinding or a made-up supply is invisible to R7's raster test, and §1.4 proves it is not
hypothetical (three of four NT files are made up). The 51 files are **PROVISIONAL** until the leaves they
rest on are collated: usable, **not citable**, and **no gate closes on them** (§0.5).

**Hour ceiling: 12h to a first end-to-end R2.1→R2.4 pass on ONE volume (`OT1-1609-B`). Decision rule,
pre-registered, written before the work starts:**
- If the signature reader cannot reach **≥95%** parsed rectos in 6h, it does **not** get a lowered target.
  The band is re-cut once (R8.4a proved the foot band is the hard part and cost four failed designs), and
  if that fails the step **ALERTS that the approach needs redesign** — hand-reading a stratified sample to
  establish the collation is the fallback *method*, not a lowered *bar*.
- Abstention is not failure: a reader that abstains on 8% and is right on 92% passes; a reader that emits
  92% correct and 8% confident-wrong **fails**, because the collation cannot detect the difference.
- 🔴 **The ceiling exists to force a start, not to license a stop.** §0.5 names *unstartability* as
  producing the same observable outcome as preserving the status quo, and R2 has been marked **NEXT** since
  the roadmap was written without a line of code — which is that failure mode, in this file, uncaught for
  the whole life of the project. A ceiling that expires escalates; it never closes the step.

### R2.0 — Direction-line instrument: STARTED 2026-08-10/11, ~3h of the 12h ceiling

**R2 is no longer "nothing built".** An instrument exists in `.scratch/r2/` (probes v1–v18, logs beside
them). It is **not yet a deliverable** — nothing is written to `witness/` — but the design is settled and
the dead ends are measured, so they are recorded here to stop them being re-walked.

**The design of record is `.scratch/r2/probe_v18.py` + `run_v18.py`:** bound the search below the last
full text line → find type by **connected components** (`scipy.ndimage.label`), never by a row profile →
split the row into **tokens** → **recognise each token separately** → **then** apply one accept-test to
the tokens that actually read.

| finding | evidence | consequence |
|---|---|---|
| A row profile **cannot** find a direction line | leaf 400: strip ink rises monotonically 0.0071→0.0507 toward the leaf edge (page-curl shadow) while the catchword `face` sits at 0.03–0.04 — **the catchword is below the shadow in ink**; edge columns read 0.352/0.274/0.957 | 4th instance of *a filter cannot enforce a distinction it cannot express*. Components carry height, width and border-contact; a 1-D profile carries none of them |
| A 1400px mostly-blank row is **not a line** | fed whole to `rpred` it returns one stray glyph; split into tokens the same pixels read `ſtoode`@1.00 | recognise tokens, never the row |
| The accept-test must run **after** recognition | a token that reads `''` is not type, yet it dragged leaf 700's row extent to 1.01× the measure and caused a false refusal | one reordering fixed a false accept (901) and a false reject (700) together |
| A guard on one route of two guards nothing | v15 guarded only the fallback; leaf 901 read its last text line `'auekabylon.'@0.80` as a direction line | **the only confident-wrong found; now refused** |
| `VS.line_pitch` returns `None` and every call site said `p = pitch or 30.0` | leaf 600's 5 text lines collapse to 1 run; true pitch ≈40 | a magic constant standing in for a failed measurement — replaced by a measured relation, `PITCH_PER_GLYPH = 2.21 ± 0.27` |

**Measured and rejected, do not re-walk:** `blla.segment` on a band (21.7s/37.5s per leaf ⇒ ~13h > the
whole ceiling); `FOOT_BELOW_PITCHES=8.0` (a longer tail reaches the leaf edge and 3 leaves collapse to a
0–7px strip); a global absolute ink floor (leaf 401's *blank* rows are inked 0.0443 vs leaf 400's
text-adjacent 0.020 — no global threshold separates them on any leaf); `type_scale` = median text-run
height as the yardstick (returns 17–40 across leaves of near-identical pitch — it tracks contrast, not
type size); extent-alone without the bound (leaf 500 reads `'conteiming the Lam.'@0.97`).

🔴 **THE INSTRUMENT HAS NEVER BEEN SCORED ON R2.1's ACTUAL METRIC.** Every panel so far counted *any
token read, either parity*. **R2.1 asks for signatures on rectos.** Most reads to date are *catchwords*,
which R2.1 does not ask for at all, and leaf 851 is the proof of the gap: catchword `† And`@0.99 read,
signature `Ggggg 2` **missed** — a success under my scoring and a **failure** under R2.1's. The panel
numbers below are therefore **PROVISIONAL and non-citable** (§0.5, R10.2): tuning 6/8 · held-out 6/12 ·
fresh 11/16, on *token-read*, not on *signature-per-recto*.

### R2.1 — execution steps (written 2026-08-11, before the work)

| # | step | deliverable | acceptance |
|---|---|---|---|
| R2.1a | **Parity, measured** | for a stratified sample of `OT1-1609-B`, the leaf-index parity that carries signatures, established from **where tokens land** (signature centre-left ~x 0.48–0.55, catchword right ~x 0.75–0.87) | parity is **reported with its evidence**, never assumed from index parity; if both parities carry signatures the sample is widened, not the claim narrowed |
| R2.1b | **Recogniser selection, measured** | the probes run `models/reichenau_dr.mlmodel`; `models/dr_v3_armA.mlmodel` and `dr_v3_armB` exist and are later. Score all three on ONE fixed token set with hand-keyed truth | the model is chosen **on measured CER over direction-line tokens**, not on impression; the losing models and their scores are recorded (§0.2 rule 1's discipline, applied to a component) |
| R2.1c | **`witness/collation_read.py`** | the probe promoted to a module: `read_direction_line(witness, leaf) -> {signature, catchword, x_positions, confidence, abstain_reason}`; **separate** signature and catchword fields | abstains with a **stated reason** and never guesses; a confidence floor is applied and its value is justified by R2.1b's CER curve, not chosen |
| R2.1d′ | **The R2.1 metric run — RESTATED, see R2.1-CRIT** | **two** measurements, because the old one was unsatisfiable: **(A) catchword continuity** — `catchword(leaf N)` vs the first word of `leaf N+1`, over a consecutive run; **(B) signature-sequence monotonicity** — parsed signatures must ascend in signature order (`Y · Y2 · Y3 · Z · Aa …`) with no descent | **(A) ≥95% agreement on leaf pairs where both leaves yield a reading**, Wilson CI, lower bound above the bar — not the point estimate; **(B) zero descents** unexplained by the collation. A descent is a defect report entry (R2.4), never a discarded reading. Failures listed by leaf |
| R2.1e | **Pair completeness** | signature and catchword scored **independently**, never "≥1 token read = success" | leaf 851's failure mode (catchword read, signature missed) is visible in the score by construction |
| R2.1f | **Apply the pre-registered rule** | either proceed to R2.3, or fire the escalation | ≥95% (CI lower bound) ⇒ R2.3. Below ⇒ **band re-cut ONCE**, then **ALERT that the approach needs redesign**. Confident-wrong at any rate ⇒ **FAIL regardless of the parsed rate**, because the collation cannot detect the difference |

**Hours: ~3.5h of 12h consumed (R2.0 + R2.1a). Remaining ceiling 8.5h.** Sub-ceilings: R2.1b 1h ·
R2.1c 2h · R2.1d′ 2h. **If R2.1d′ cannot be run inside the remaining ceiling, R2.1f fires — the ceiling
is not extended.**

### 🔴 R2.1-CRIT — R2.1's acceptance criterion was UNSATISFIABLE BY CONSTRUCTION (found 2026-08-11)

**R2.1 has read "≥95% of rectos yield a parsed signature" since this file was written. No reader can ever
achieve it, because most rectos carry no signature at all.** Signatures are set on the rectos of the
**first half of each gathering** only — the compositor's binding instruction, not a page label — so the
criterion demands a reading from leaves that print nothing to read.

**Measured on `OT1-1609-B`, leaves 400–431 consecutive** (`.scratch/r2/r2_1a_parity.py`, log beside it;
consecutive rather than stratified **because the question is periodicity, which a stratified sample
destroys**):

```
signature present on   401 'Yy' · 403 'Yy' · 405 'y' · 417 'a' · 419 'A' · 425 'Bbb' · 427 'Bb b'
                       = 7 of the 16 rectos in the run (44%), ALL at odd leaf index
catchword present on   essentially EVERY leaf, BOTH parities (400 'face' · 401 'ſtoode' · 404 'God' …)
```

**Three results, and each changes the plan:**

1. **R2.1a is DONE: parity is measured, not assumed.** Odd leaf index = recto for this witness, evidenced
   by every one of the seven signatures landing on an odd index, at x 0.49–0.57 (centre-left), while
   catchwords land at x 0.70–0.84. ⚠️ This is a per-witness fact and must be re-measured per witness —
   it is a property of where the scan starts, not of the book.
2. **A ~44% signature incidence cannot be distinguished from a 44%-recall reader by the old criterion.**
   That is the deeper defect: the criterion could not tell *"the leaf prints no signature"* from *"the
   reader missed it"* — the two produce the identical observable. **A criterion that cannot separate
   absence from failure is not a test**, and this is the same shape as R1.4 and as `_empty_because`
   (§1.4): a null needs its cause established, not assumed.
3. 🟢 **The catchword is the DENSE signal and it is SELF-CHECKING — this is the better instrument.**
   A catchword prints on every leaf and its correctness is verifiable **without human ground truth**:
   `catchword(leaf N)` must equal the first word of `leaf N+1`. That single relation simultaneously
   (a) scores the reader, (b) proves leaf order, and (c) detects a wanting, duplicated or misbound leaf
   **at every leaf boundary**, where signatures test only ~44% of rectos — roughly one boundary in five.
   **Gate 0b's collation should rest primarily on catchword continuity, with signatures as the coarse
   gathering index**, which is the reverse of the emphasis R2.1/R2.2 were written with.

⚠️ **What this does NOT license.** The bar is not lowered — it is **restated onto a measurement that can
carry it**, and the new one (R2.1d′) is *stricter*: it demands agreement against an independent fact (the
next leaf's first word) rather than mere parse success, which is why it can be run without a hand-keyed
gold set. Reaching it is R2.1f's decision, unchanged.

### 🔴 R2.1-CRIT-2 — R2.1d′(A) AS WRITTEN VIOLATES R2's OWN SEQUENCING RULE (found in implementation, same day)

**The step I wrote three hours earlier is wrong, and building it is what showed why.** R2.1d′(A) compares
`catchword(N)` to the **first word of leaf N+1** — and the first word of a leaf is **body text**. R2's own
sequencing note says R2.1/R2.2 *"are OCR tasks on a tiny, highly regular target … They must not wait on
the recognizer."* A metric that requires reading body text **makes R2 wait on the recognizer**, which is
the one thing this section is written not to do. The error is mine, in Step 4 of this review.

**Measured anyway, because the number is informative even though the metric is wrong**
(`.scratch/r2/r2_1d_continuity.py`, leaves 400–419): **agreement 4/18 = 0.222, Wilson95 [0.090, 0.452]**.
🔴 **This figure is PROVISIONAL and it is NOT a collation finding** (§0.5, R10.2). It measures a
*compound* — catchword read × first-line read × recogniser quality on body text — and the failures are
dominated by the last term, not by leaf order:

```
401->402  catch 'ſtoode'   first 'hoode in the ſtreicttes…'   <- 'hoode' IS 'ſtoode' misrecognised
409->410  catch 'wl'       first 'whom is the familie…'       <- catchword truncated, line read fine
```
**Not one disagreement in the run has been shown to be a real discontinuity.** Reporting 0.222 as a
leaf-order result would be exactly the error §1.4 warns about — a null whose cause was assumed.

🟢 **REMEDY — R2.1d″: compare the two as IMAGES, not as text.** The catchword of leaf N and the first
word of leaf N+1 are *the same word set in the same fount*. Block-registered normalised correlation
answers "is this the same word?" **without recognising either**, which keeps R2 off the recogniser's
critical path exactly as its sequencing note requires. **The method already has precedent in this
project**: §1.4 identified the fourth frontmatter source at **+0.424/+0.398 against 0.000–0.036** on
every cross-pairing — a separation of an order of magnitude, on the same kind of comparison.

| # | step | deliverable | acceptance |
|---|---|---|---|
| R2.1d″ | Catchword continuity **by image correlation** | for each leaf boundary, the catchword crop of N registered against the first-word crop of N+1; correlation reported per boundary with the **cross-pairing baseline** (N against N+2, N+3) as the negative control | **≥95% of scored boundaries separate from the baseline** by the §1.4 margin, Wilson CI lower bound above the bar. A boundary that does not separate is a **defect-report candidate (R2.4)**, never a discarded reading. ⚠️ The negative control is mandatory: a correlation figure without it cannot distinguish "same word" from "same fount, same size, same paper" |

🔴 **R2.1d″ BUILT AND MEASURED THE SAME DAY — AND IT FAILS. The negative control is what says so.**
`.scratch/r2/r2_1d2_correlation.py` (leaves 400–415, 15 boundaries, each catchword also correlated
against the first word of N+2 and N+3):

```
matched pairs   n=15   mean +0.264   median +0.254
controls        n=30   mean +0.247   max +0.631     <- a CONTROL scores higher than any but two matches
boundaries separating from the control baseline: 4/15
```

**The match distribution is indistinguishable from the control distribution.** Two short words set in
the same fount at the same size on the same paper correlate ~0.25 whether or not they are the same word:
mean-subtracted stroke patterns at this scale carry almost no word identity.

⚠️ **Why §1.4's precedent did not transfer, stated so it is not tried a third time.** §1.4 separated
+0.424/+0.398 from 0.000–0.036 by registering a **whole page block** — hundreds of glyphs, with layout,
line breaks and margins all contributing. A catchword is **4–8 glyphs, ~40px tall**. The signal scales
with the area being matched, and the discriminating power went with it. *A method's separation is a
property of the evidence it was demonstrated on, not of the method.*

🟢 **THE CONTROL IS THE RESULT.** Without it this run reports "mean correlation +0.264, continuity
confirmed" and a false collation enters Gate 0b — the precise failure R2.4 exists to catch, arriving
through R2.1's own instrument. The mandatory-control clause was written into R2.1d″ one edit before it
was run, and it earned itself immediately.

**Where this leaves R2.1's metric — two of three candidates are now refuted by measurement:**

| candidate | verdict |
|---|---|
| signature parsed / recto (original) | 🔴 **UNSATISFIABLE** — ~44% of rectos print no signature (R2.1-CRIT) |
| catchword continuity, as TEXT (R2.1d′A) | 🔴 **OUT OF SCOPE** — couples R2 to the recogniser; measured 0.222 compound, not a collation fact |
| catchword continuity, by IMAGE (R2.1d″) | 🔴 **NO SEPARATION FROM CONTROL** — matches +0.264 vs controls +0.247 |
| **signature-sequence monotonicity (R2.1d′B)** | 🟢 **STANDS — the only surviving candidate.** Reads only signatures (the tiny regular target R2 is scoped to), needs no gold set, and the observed run `Y · Y · y · a · A · Bbb · Bb b` over leaves 401–427 is already consistent with it |

⚠️ **R2's pre-registered rule is now live and must be honoured.** ~4h of the 12h ceiling is spent and no
metric has cleared. The rule permits **one band re-cut**, then **ALERT for approach redesign** — and it
names the fallback *method* explicitly: **hand-reading a stratified sample to establish the collation.**
That fallback is a change of method, not a lowered bar, and on this evidence it is now the likely route
for the *catchword* half. **No metric may be adopted without a negative control**, on the strength of
what this run just demonstrated.

⚠️ **R2.1d′(A) is retained above, struck, rather than deleted** — the record that a plausible metric was
written into this file and then refuted by building it is worth more than a clean table (§0.6, and the
devlog convention). R2.1d′(B), signature-sequence monotonicity, is **unaffected** and stands: it reads
only signatures, which are the tiny regular target R2 is scoped to.

⚠️ **Consequence for R2.3/R2.4, folded in rather than deferred.** The collation model must accept
signatures as a **sparse, periodic** index (present on the first half of each gathering) and must *not*
treat an unsigned recto as a defect. R2.4's "no leaf unaccounted" is unaffected — every leaf still fits
the collation or appears in the defect report — but the evidence reaching it is now catchword continuity
at every boundary plus signatures at gathering starts.

⚠️ **R2.1a–f do not require the direction-line reader to be perfect.** R2.3's collation model is where
the **redundancy** lives: signatures run in a known sequence at a known gathering size, so a leaf the
reader *abstains* on is recoverable by interpolation, while a leaf it reads *wrongly* corrupts the
structure everything else is checked against. That asymmetry is the whole reason the decision rule reads
"abstention passes, confident-wrong fails" — and it is why further recall tuning is **not** on R2's
critical path once the metric clears.

---

## R3 — Cross-source leaf mapping (Gate 0c)

**Discharges** §2 Gate 0c.

| # | step | deliverable | acceptance |
|---|---|---|---|
| R3.1 | Leaf key | `(volume, printed page, signature, side)` as the addressing key — **never file index** | key is stable across witnesses by construction |
| R3.2 | Correspondence table | every admitted leaf → its leaf index in each witness of that volume | 100% of admitted leaves addressable in every witness that has them |
| R3.3 | Absence register | leaves present in one witness and absent in another, with cause | each absence classed: not in copy · not scanned · dropped in derivation |
| R3.4 | Verification by image | sampled correspondences confirmed by correlation | sampled pairs correlate far above the unrelated-page baseline |

**Why this cannot be skipped or deferred.** §1.4 established that leaf indices do **not** correspond between
files of the same volume — the NT witnesses differ by up to 47 leaves before any text is compared. Until
R3.2 exists, "the same page in another witness" is not a well-formed request, and no collation of readings
is possible.

---

## R4 — Bibliographic completion (Gate 0a residue)

Runs in parallel with R2/R3; it constrains citation, not imaging.

| # | step | deliverable | acceptance |
|---|---|---|---|
| R4.1 | STC/ESTC verification | STC and ESTC numbers for all copies, cross-checked against held OCLC numbers | each number resolves at an authority; **unverified leads are recorded as leads, never promoted** |
| R4.2 | Repository for `F` and `X` files | repository + shelfmark, or an explicit NOT ESTABLISHED | no field silently blank — **DONE**, see below |
| R4.2a | Physical copy behind the three `F` volumes | repository + shelfmark, by a route other than catalogue metadata | a named copy, or a published statement of what was tried and why it failed |
| R4.3 | Identify `NT-1582-X`'s supplied leaves | the fourth source of the Censure and Preface p.1 | source named, or its candidate set narrowed and published |
| R4.4 | **Acquire `newtestamentofie00engl`** — `NT-1633-R`'s original digitisation | the Princeton capture in continuous tone, replacing the binarised re-upload | **DONE** — 778 leaves, NCC 0.990 vs the superseded render, 190–228 grey levels |

**R4.4 blocked any *reading* from `NT-1633-R`, and is now discharged** (§1.2a). The witness previously held
was a user re-upload of IA's MRC PDF whose text layer is a **1-bit JBIG2 mask** — and `NT-1633-R` exists in
the corpus precisely to supply the Censure and Preface leaves, the two with no genuine 1582 reading
anywhere (§1.4). The original was on IA under a different identifier with full Princeton provenance, so
this was an acquisition rather than a research problem; `witnesses.py` now resolves `NT-1633-R` to it and
keeps the superseded package addressable as `superseded` for audit.

**R4.2 is discharged** (§1.3). All four items were traced to their IA records and read: every one is a
**user upload to `folkscanomy`** with no `scanningcenter`, `contributor`, `call_number` or
`external-identifier` — so no repository is recoverable from the catalogue, and the field is recorded
**NOT ESTABLISHED** with the evidence for that verdict rather than left blank. `NT-1582-X` is the exception
that proves it: its repository *is* known — **BPL G.404.12** — but by identity with `NT-1582-B`, since its
uploaded PDF carries that capture at that capture's own raster (§1.2). It is provenance inherited, not
provenance of its own.

**R4.2a is what remains, and it is deliberately not folded back into R4.2.** The digitisation provenance of
the `F` set is settled (`fatimamovement.com`, uploaded 2014-07-28); the *physical copies* are not, and the
catalogue route to them is exhausted. Recording that as done would convert a real gap into a false
closure. Because `F` is barred from glyph-level work by its resolution (§1.2), this blocks **citation**,
not imaging — but it stays **OPEN**.

**R4.3 is DISCHARGED, and not where it was expected.** The fourth source is the **1582 setting witnessed by
`NT/S06`** — the file the plan had excluded as "a modern facsimile" (§1.1, §1.4). Block-registered
correlation gives +0.424 / +0.398 on the matching pair against 0.000–0.036 on every cross-pairing, and the
visual agreement is line-for-line including the S. Augustine quotation absent from the 1633 setting.

**R4.1 — the ESTC authority is still down, but the route that worked was never the ESTC.** `estc.bl.uk`
redirects to CERL and the ESTC beta returns **`no such index [estc]`** for every query; USTC 404s, Virginia
is JS-only, Jisc 403s, LC's `search.catalog.loc.gov` 403s. Every *catalogue-interface* route is exhausted.
**The numbers came instead from the holding library's own MARC, which we already held locally** — see R4.1d.
**One institutional authority is in hand; the two-authority rule stands, so nothing is promoted into §1.3.**

| # | step | deliverable | acceptance |
|---|---|---|---|
| R4.1a | Automated ESTC retry | a scheduled probe of the CERL ESTC index that reports when it answers | the probe distinguishes "index down" from "record absent"; a passing probe re-opens R4.1 automatically |
| R4.1b | Fallback authorities, in order | Folger *Hamnet* (the STC authority of record) → USTC → Bodleian/Oxford SOLO → Harvard HOLLIS | a number is promoted only when **two independent authorities agree**, and the S102419/S102491 split is resolved explicitly, not silently picked |
| R4.1c | Record the disagreement, not just the answer | concordance carries the rejected variant and why | a later reader can see that a one-digit variant existed and was adjudicated |
| R4.1d | **Holding-library MARC via the IA item record** — DONE, and this is the route that worked | `curl -sL https://archive.org/metadata/<id>` → `metadata.references` carries the contributing library's own catalogue citations | numbers are read from a named institution's MARC, not from a dealer or auction listing |
| R4.1e | **Authority #2** — a second *institution's* record | Princeton's MARC for `holiebiblefaithf01engl` / `thenewtestamento00rhei` by the R4.1d route, or OpenLibrary JSON, or a Folger/Bodleian record | two institutions, independently, before any number enters §1.3 |

**R4.1d result — Boston Public Library's own MARC**, via `metadata.references` on the IA items:

| witness set | IA identifier | citations, verbatim from BPL's MARC |
|---|---|---|
| NT 1582 | `nevvtestamentofi00mart` (BPL, call no. `BS2080 1582`) | `ESTC S102491; STC (2nd ed.), 2884; Darlow & Moule (2001 reprint ed.), 134; Herbert, A.S. Engl. Bible, 177; Allison & Rogers. Engl. Counter-Reformation, II, 173` |
| OT 1609–10 | `holiebiblefaithf00mart_0` (BPL, call no. `BS180 1609`) | `STC (2nd ed.) 2207; ESTC S101944; Darlow & Moule 300` |

Both strings re-fetched and diffed against the live IA records on 2026-08-07 before being written here. The
first transcription of the NT row, made from working notes, had silently normalised the punctuation and
abbreviated *Herbert, A.S. Engl. Bible* and *Allison & Rogers. Engl. Counter-Reformation* — small, but a
row labelled **verbatim** that is not verbatim is the same defect class as a stale count. Fetch, don't recall.

⇒ **The one-digit split is adjudicated: it is `S102491`, not `S102419`.** R4.1c is satisfied on this point by
recording *why*: `S102491` comes from the holding library's catalogue record for the very copy we hold as
`NT-1582-B`, while `S102419` traces to dealer and auction listings — secondary descriptions of other copies.
The rejected variant is kept here deliberately so a later reader can see it existed and was decided.

**Method note, and the reason R4.1 sat "BLOCKED EXTERNALLY" longer than it needed to.** The block was real
but mis-scoped: it was a statement about *ESTC's search interface*, and it was allowed to stand for "the
bibliographic numbers are unobtainable." The numbers were sitting in an IA field we had already downloaded
for other purposes. **An external blocker names one route; it does not bound the space of routes** — the same
shape of error as R4.5's exclusion-by-description.

**Why two authorities and not one.** The failure mode here is not "no number found" but "a plausible number
found and propagated." A one-digit difference between two live-looking identifiers is precisely what a
single source cannot catch, and a misattributed ESTC number in a documentary edition is a defect that
survives every later correction.

| # | step | deliverable | acceptance |
|---|---|---|---|
| R4.5 | **Re-examine every excluded file before any "survives nowhere" claim** | each exclusion carries measured grounds — edition, date, printer, raster, and what its prelims contain — not a one-line description | no file is excluded on a description that has not been checked against its own leaves; `S06` is the worked example |
| R4.6 | Ask the Fatima Movement for a higher-resolution capture | a direct enquiry, and its answer recorded either way | if a higher-resolution capture of the `F` copy exists, `F`'s role changes from low-resolution to full witness (§1.1a); if not, the negative is recorded so it is not re-asked |

**R4.5 exists because an exclusion is a claim.** `S06` was set aside as "a modern facsimile, not a witness
to the setting." Its OT is a **1635 Rouen Cousturier** printing, its NT a **1582 Rheims Fogny**, and its
prelims hold the only genuine 1582 Censure and Preface p.1 in the corpus. The description was wrong about
the date, the printer and the nature of the artefact, and because it was never re-tested it produced a
false "no genuine 1582 reading survives anywhere" verdict at the single most consequential point in the NT.
**An exclusion inherits the evidential standard of any other claim**, and the cost of a wrong one is
silence rather than error — which is why it must be checked rather than trusted.

---

## R6 — `S06` and the frontmatter/backmatter collation

`S06` is **excluded from the verse text and admitted for prelims and endmatter** (§1.1). Its value is that
it holds two settings the rest of the corpus does not: a **1635 Rouen OT** and a **1582 Rheims NT** whose
frontmatter is complete.

> 🔴 **OPEN (R7.5a-3, 2026-08-08) — this sentence and the registry now disagree, and the registry moved.**
> The `drop_tomes: ["NT"]` scoring rule is **RETIRED** (Sir): `NT-1582-M` is a genuine 1582 Rheims setting
> and the second witness to a setting the New Testament otherwise holds once, so it is not the redundant
> repeat the drop assumed. `jp2-S06nt` localizes **2,344 pilot-book verses** and now attests in
> `coverage-audit-verse.json` (matthew 1,067 · john 877 · apocalypse 400).
> Two consequences must be settled, not assumed:
> 1. **The "frontmatter witness" role (§1.1, `OCR-MASTERPLAN.md`, `OCR-OVERVIEW.md`) says "no verse of
>    scripture."** `M` is filed under it. For the NT half that is no longer what the corpus does.
> 2. **The OT half already contradicted it, and had for longer.** `jp2-S06ot` attests psalms 2,515 and
>    genesis 1,530 in the same audit, under an editorial rationale — 1635 Rouen is a different edition —
>    that the role text does not state. That contradiction predates the retirement and was not created
>    by it.
> Restate the role per half, or restate the rule. Do not let the sentence above and the audit both stand.

| # | step | deliverable | acceptance |
|---|---|---|---|
| R6.1 | Address `S06`'s two halves separately | registry entries `NT-1582-M` (leaves 2072–2871) and, if wanted, `OT-1635-M` (leaves 0–2070) | the OT/NT boundary at the blank leaf 2071 is asserted, not assumed; each half declares its own edition |
| R6.2 | Extract the 1582 prelims | `NT-1582-M` leaves 2072–2076: title, Censure, Preface pp. 1–3 | each leaf named and its setting identified against `S04` (1633) and `S08` (supplied) — **DONE**, see below |
| R6.3 | **Transcribe the Censure and Preface p.1 from `M`** | the two leaves the base exemplar lacks, as 1582 readings | transcribed with `M` named as the supplying copy and its ~380 ppi bitonal raster recorded as the limiting factor — **DONE**, see below |
| R6.4 | Collate 1635 prelims against 1609/1610 | a difference report: what the second edition adds, drops and rewords in Approbatio, Preface, Tables, errata | every difference cited to a leaf in each edition; **no difference asserted from memory of the text** — **DONE**, report at `COLLATION-1635-vs-1609.md`; OT2/1610 prelims outstanding |
| R6.5 | Record the 1634 privilege | *Extraict du Privilege du Roy*, Paris, 3 Aug 1634, to Jean le Cousturier, ten years, to reprint *"de l'edition de Laurens Kellam Imprimeur de Douay"* | quoted verbatim from leaf 2070 with a transcription of the French — **DONE**, `ground-truth/matter-ot2-privilege-du-roi.json`, re-read on the primary raster; see below |

**R6.5 was already transcribed on 2026-07-20 — and the transcription was made on a derived image.** The
existing file read leaf 2070 from the `S06` **jp2** at 5100×6601. The per-item primacy finding later
established that `M` is **PDF-primary**: the PDF holds the real ~2955×4206 CCITT and the jp2 is a **1.73×
render of it**. The 2026-07-20 word zooms at 5× were therefore operating at roughly **8.6× the real
raster**. The transcription has been re-read from the embedded CCITT XObject directly.

**Three readings change, and two of them are the very spans the original file flagged as unresolvable.**

| line | was | now | how it was settled |
|---|---|---|---|
| 3 | `d. Roüen` | **`de Roüen`** | the `d`→`R` gap is **46 px**; word spaces on that line are 27/29/27 px and the line's own `e` is 22 px wide (22+27≈49). The gap holds an `e` *plus* a space. **Negative control**: a real period on this page is **10×12 px**; the mark in the gap is **3×2 px**, 1/25 the area, sitting at the baseline where an `e` bowl bottoms out. It is not a period — the `e` failed to ink |
| 5 | `Marchans` | **`Marchands`** | between `n` and `s`: a baseline blob 8×7 px **plus a 6×42 px full-ascender stroke**. An i-height stroke cannot reach ascender height; this is a `d`'s ascender and the foot of its bowl, bowl failed. Agrees with singular `Marchand` on line 2 |
| 9 | `Donnees` | **`Données`** | not previously flagged; the acute is solidly inked and well clear of the letter |

**This is the third instance of one defect class, and the mechanism is now explicit: upscaling manufactures
the feature the call depends on.** Interpolation rounds a 3×2 speck into a plausible point (`d.`) and smears
a failed `d` bowl into a point-plus-stroke (`Marchans`). In R6.6 it closed the gap between two `v` sorts and
produced a `w`. In each case **the rule was right, the observer was careful, and the image was derived**.
The prior observer here even enumerated the correct alternative — "or the word could be `de Roüen` with a
broken `e`" — and could not choose, because the evidence that chooses had been interpolated away.
⇒ **Before any glyph-level call, check `PRIMARY` for the witness.** `pixel_source()` already enforces this
for the five renders; the lesson is that a *transcription* must consult it too, not only a pipeline.

Backups retained as `*.pre-primary-raster`, on the R6.6c principle: the backup records what an observer
saw, the current file records what a measurement produced.

**R6.4 is DISCHARGED for the first tome; the report is `COLLATION-1635-vs-1609.md`.** Headline results:

- **Section for section, note for note, the 1635 adds nothing and drops nothing.** The adds/drops question
  was closed for the *whole* Preface by collating its **marginal note sequence** — ~24 notes corresponding
  one to one in the same order — rather than by a word-by-word read of 22 pages.
- **The Approbatio is reprinted verbatim, retaining `Duaci 8. Nouembris. 1609`.** The Rouen edition does
  not re-approve itself; the approbation dates the *text*, not the book.
- **What changed is orthography and typography** — dominated by `-ie`→`-y`, dropped terminal `-e`,
  increased capitalisation, and `VV`→`W` — plus one silent correction of a first-edition error
  (`to large`→`too large`).
- **It is not a modernisation programme**, and several changes run the other way (`AVTHOR`→`AVTHOVR`,
  `Goſpel`→`Ghoſpel`, `authors`→`authours`, `dearly`→`dearely`). The `ai`/`ay` digraph moves in **both**
  directions within the same edition.
- **The 1635 founts have a `W` sort and the Douai founts do not** (`VVELBELOVED` → `WELBELOVED`), and the
  1609 prose is itself mixed on a single page at ~545 ppi. This corroborates R6.6 on an admissible raster.

**Registered for this step**: `OT-1635-M` (package pages 0–2070). It is **not** a witness to either OT
tome's setting and may never supply an OT verse reading — it exists so a difference can be **cited to a
leaf** rather than described.

**Outstanding and named**: word-level rewording in the bodies beyond the collated samples · the endmatter
Tables · **the OT2/1610 prelims**, which sit further into `M`'s package and are not yet located. None of
these blocks the edition — `M` supplies no verse reading, so this is scholarly yield, not critical path.


**R6.4 is the deliverable that answers "what differs between the editions."** The privilege at R6.5 is what
makes it interesting rather than merely descriptive: the 1635 edition states on its own back matter that it
reprints the Kellam Douai edition, so **every difference in its prelims is a deliberate editorial act by
the Rouen house**, not an independent transmission. That makes the difference report evidence about how the
edition was understood in 1635, and it is the only such evidence the corpus contains.


**R6.2 and R6.3 are DISCHARGED, and doing so exposed a defect in existing ground truth.**

`witness/extract_pdf_leaves.py` extracts leaves from a PDF-primary witness by pulling the **embedded
XObject** rather than rasterising the page, with the slice offset read from the registry in one place. All
five prelim leaves are named: title page · **Censure and Approbation** · Preface p. 1 · two Preface
openings. The Censure carries the two-line heading, no headpiece and no *"of the first Edition"* subtitle
— the 1582 setting, exactly as the correlation evidence predicted.

| # | step | deliverable | acceptance |
|---|---|---|---|
| R6.3a | **Reclassify `matter-nt-preface.json`** | the file is the **1633** setting, not the 1582 Preface it was filed as | **DONE** — reclassified, kept as the only 1633 Preface p.1 we hold, and barred from citation as a 1582 reading |
| R6.3b | Sir to adjudicate `aliiíque` | a minim call that revises a correction Sir applied on the 138 ppi substitute | **OPEN** — flagged in the file, not silently changed |
| R6.3c | Sir to note the **mixed `w`/`vv` prelims face** | the NT prelims prose face sets BOTH a real `w` and `vv` | **OPEN** — a blanket `vv`→`w` pass over the NT prelims would be wrong in both directions |

**The ground-truth defect.** `matter-nt-preface.json` was filed as the NT Preface and transcribes the
**1633 setting**: it was read from `NT-1582-F` page 4, and F's Preface p. 1 is one of the two leaves F does
not natively own — proven by blank-margin foxing to be the 1633 Princeton copy's. The text settles it
independently of the foxing: **`ancient` for `auncient`, `manner` for `maner`**, a different display break
and a different headpiece. Letter-count differences cannot come from two impressions of one forme. This is
exactly the contamination §1.4 exists to catch, and it was sitting in ground truth **unflagged** — because
it was made when the plan believed no 1582 Preface p. 1 survived anywhere, so there was nothing to compare
it against. **A false "survives nowhere" verdict does not merely leave a gap; it removes the control that
would have caught a misfiling.** That is a second, sharper cost of the `S06` exclusion (R4.5).

**What `M` resolved that the substitute could not.** The Censure had been transcribed from `NT-1582-X`'s
138 ppi spliced substitute — the same setting, at the worst raster in the corpus for that leaf. `M` carries
it ~3.4× larger and settles three flagged uncertainties: **`vitǽque`** (acute clear), **`lib. 1. c. 3.`**,
and the minim count in **`aliiíque`** — three i-strokes, measured by connected-component count in the
diacritic band rather than judged by eye. The last revises a correction Sir applied, and is flagged for him
rather than changed silently.

**What `M` cannot resolve, and why it stays that way.** The `w`/`vv` discrimination on these leaves is at
the raster's limit and **cannot be improved by any acquisition**: the base exemplar lacks the leaves, `X`'s
copy is the spliced substitute, and `M` has no continuous-tone original. This is a genuine ceiling, recorded
as one — not a pending task.

### R6.6 — the `w`/`vv` flip was adjudicated on a raster that cannot resolve it

**Sir's ruling (2026-08-06): mixed `w`, `vv`, `VV` and `Vv` are likely on a variety of leaves. Do not
exclude the possibility, and be cautious about global flips lest original variants be overwritten.**

`GUIDELINES.md` §w-regime already states the right rule — **per-instance, decided by stroke connectivity,
never by the word** — and its priors are sound. The defect is not the rule. It is **where the rule was
applied**.

A global `vv`→`w` pass changed **33 lines** across three files (backups survive as `*.pre-vvfix`), and the
STATUS note records it as *"now VISUALLY VERIFIED (2026-07-18)"*. **Every one of those three files was read
from `NT-1582-F`.**

| file | witness | source raster | lines flipped |
|---|---|---|---|
| `matter-nt-title.json` | `F` | 800 × 1124 (**~168 ppi**), read at a 400-dpi *render* | 7 |
| `matter-nt-table.json` | `F` | same | 13 |
| `matter-nt-preface.json` | `F` | same — **and the 1633 setting** (R6.3) | 13 |

**The call is beneath the raster's limit.** `F` is barred from glyph-level work because the long-ſ nub —
3–6 px at the base exemplar's ~545 ppi — spans **under 1.6 px** at 168 (§1.2). **The gap that separates two
`v` sorts from one joined `w` is a finer feature than that nub.** So the 2026-07-18 verification could not
have resolved what it reports resolving: it was performed on an *upscaled render*, where interpolation
smooths precisely the gap the test depends on and makes separate sorts *look* joined. That is a mechanism
that biases the error **in the observed direction** — toward `w` — which is exactly the flip that was made.

**Independent evidence that the flip is not safe.** R6.3 read the same two frontmatter leaves in the 1582
setting from `M` at ~380 ppi, and found the prelims prose face setting **both** forms: `VVhich` as a
cap-height `V` plus an x-height `v` with a clear gap, and `word` as a single joined sort — **on the same
line as a two-sort `vve`**.

| # | step | deliverable | acceptance |
|---|---|---|---|
| R6.6a | Re-adjudicate the 33 lines on an **admissible raster** | each `w`/`vv` decided at 2–4× on `B` (~545 ppi) where `B` has the leaf, or on `M` (~380 ppi) where it does not | **no line decided on `F`** — it is inadmissible for this call by the plan's own resolution finding |
| R6.6b | No global pass in **either** direction | the flip is not simply reverted | wholesale reversion repeats the error with the opposite sign; the priors say roman body really is predominantly `w` |
| R6.6c | Retain every `*.pre-vvfix` backup until adjudicated | the observer's record is preserved | the backup is **what was seen**; the current file is **what a rule produced**. Where they disagree the observation is evidence and the rule is inference |
| R6.6d | Amend the §w-regime STATUS note | the ratification is scoped to the raster it was made on | a future observer must not read "visually verified" as covering a witness that cannot support the test |

**`matter-nt-title.json` first.** Its line 6 flips `Vvith`→`With` in **display matter**, where §w-regime
records that the large-capital fount **has no `W` sort at all**. If that holds, the pass manufactured a sort
the page cannot contain — and it did so on the one file whose fount the guidelines already single out as
always `VV`.

**Sequencing.** R6.2 and R6.3 are on the critical path — they close a gap in the NT that the plan wrongly
believed unclosable. R6.4 and R6.5 are not: they are scholarly yield, and they must not delay the base
transcription.

---

## R3.5 — Attribute the New Testament's 36-leaf difference — **DISSOLVED (R8)**

> **This step asked a malformed question and is closed without being completed.** It sought to attribute the
> 765 vs 801 leaf difference between `F` and `B` leaf by leaf. They are **different editions** (§1.1c), and
> a leaf-count difference between editions attributes nothing. The live successors are **R3.5b** (the OT2
> endmatter spread, 1128/1135/1137, a real same-setting question) and **R8.4** (verify every witness's
> setting). Retained here because a step that was open for weeks should not vanish silently.
>
> **R3.5c (NEW).** Grouping the reconcile deltas by setting did not merely delete the malformed −36; it
> produced a **well-formed** replacement. Within the 1633 setting, **`F`'s block is 5 leaves short of `R`'s**
> (765 against 770). *That* is the attributable question the old step was reaching for — two copies of **one**
> edition, so every leaf of the difference has a nameable cause. It inherits R3.5's acceptance criterion
> unchanged, against `R` instead of `B`.

*Everything below is the step as it stood, retained unaltered for provenance. **It is not to be executed.**
`NT-1582-F` is the siglum this step used; the witness is now `NT-1633-F`, which is the whole reason the step
dissolved.*

**Discharges** §1.1b, second half. Depends on the leaf map (R3.2).

| # | step | deliverable | acceptance |
|---|---|---|---|
| R3.5 | Account for `NT-1582-F` 765 vs `NT-1582-B` 801 | every one of the 36 leaves assigned to a named cause | each leaf classed **wanting in the copy** · **back matter absent from `F`** · **dropped in digitisation**, by printed page number and signature |

**Do not shortcut this to "the Fatima copy is defective."** `F` closes on an errata leaf where `B` closes
on *Hard Wordes Explicated*, which points at back matter rather than at missing text — but pointing is not
attributing, and the same 36 leaves are equally consistent with a digitisation that stopped early. The
distinguishing evidence is the **printed page numbers and signatures at the join**, which the leaf map
produces as a by-product. **Until R3.5 runs, no claim is made in either direction about NT completeness**,
and §1.1b says so explicitly rather than leaving a silence a reader would fill with the unflattering
reading.

---

## R5 — Raster policy (folded down from former step 4)

Formerly a full build step; the binarisation work it existed to support was withdrawn when the JP2 packages
were found to be continuous tone (§1.2, §3.1). What remains is small and belongs with Gate 0.

🔴 **CORRECTED 2026-08-10 — R5.2 was never written.** This section, the Master Plan §2 Gate 0d note and the
Walkthrough all described a guard that *ran but had never refused anything*. A search for any bit-depth,
grey-level, `.mode` or dimension assertion across every module returns **nothing**; the only occurrence of
the string `R5.2` in the codebase is a comment in `test_setting_verified.py` asserting that R5.2 is held to
a standard it is not held to. The devlog additionally recorded Session 13 as *"Discharges … Gate 0d"*,
which is false. **"No proven negative" and "does not exist" are different states and must never again be
written as the same one** — the first is a missing test, the second is a missing gate.

**Hour ceiling: 6h across R5.1–R5.2c. Decision rule, pre-registered:** if the three base exemplars'
manifests cannot be produced inside 3h, R5.2a/b ship on the two witness-independent clauses (bit depth,
grey levels) with the dimension clause explicitly **DEFERRED and named in the guard's own output**, and
R5.1 continues as its own step. The guard must not wait on the manifest, because a two-thirds guard that
runs beats a three-thirds guard that does not exist — which is the state this section has been in.

| # | step | deliverable | acceptance |
|---|---|---|---|
| R5.1 | Raster manifest per witness | `witness/build_raster_manifest.py` → `witness/raster-manifest.json`: per leaf, the resolved path, native dimensions, mode/bit depth, distinct grey levels, and a content checksum, keyed by witness id | manifest complete for the three base exemplars, **built through `witnesses.pixel_source()`** so it cannot describe a raster the corpus would not serve; regenerating it twice is byte-identical — 🟢 **COVERAGE DONE 2026-08-10**: 48 min (3 h ceiling not reached), **3,122 leaves** — NT-1582-B 812 · OT1-1609-B 1,160 · OT2-1610-B 1,150 — `truncated: false`, and **0 rasters on disk without an entry**, checked against `pixel_source()` rather than assumed. **3,113 leaves moved UNKNOWN→CHECKED** on the dimension clause. 🟢 **DETERMINISM PROVEN 2026-08-10**: a second full build (3,122 leaves, `truncated: false` — a real run, not an early exit) is **byte-identical**, sha256 `44290ad7…f8e0` for both, and the canonical file was not clobbered. `--out` was added to make this runnable at all: the single hard-coded output path meant the second run destroyed the first — **an acceptance clause that cannot be executed is not an acceptance clause**, and this one had stood unexecutable since it was written. ⚠️ The byte comparison is only valid because the writer uses `sort_keys=True`; `coverage-audit-verse.json` is the standing counter-case, order-nondeterministic on ties, where the same test would prove nothing |
| R5.2a | **Build** the derivative-contamination guard (Gate 0d) | `witnesses.assert_admissible_raster(wid, path)` — bit depth > 1 · distinct grey levels > 64 · dimensions match R5.1's manifest where it exists, and say so where it does not | called at the pixel-consuming entry points; a witness with no manifest entry yields **UNKNOWN, printed**, never a silent pass (R1.4) |
| R5.2b | Prove the negative | `witness/test_raster_admissible.py` feeds it (i) `M`'s 1-bit CCITT leaf, (ii) a PDF render of a known-good leaf, (iii) a dimension-mismatched leaf | each **raises**, each for the stated clause; the known-good base leaf passes — a guard that refuses everything passes (i)–(iii) for the wrong reason |
| R5.2c | Wire it to the chain, and prove the wiring | the assertion is reached from the real read path, not only from the test | injecting a rendered leaf into an actual recognition call **raises**; asserted by calling the entry point, not by reading it — the R9.3 pattern |

**R5.2b needs a negative test, not just a passing one.** A guard that has never rejected anything is not
known to work; the test must feed it a PDF-derived leaf and require the exception.

⚠️ **R5.1 blocks only R5.2a's third clause, and this dependency was unstated in both documents.** The
dimension check compares against a manifest that did not exist, so Gate 0d could never have been fully
enforced even had the guard been written. The other two clauses need no manifest and are the ones that
would have caught `X` and `S06`'s JPEG render.

⚠️ **`M` is the deliberate exception and the guard must not "fix" it.** `NT-1582-M` is genuinely 1-bit
CCITT and is genuinely admitted — at `collation` scope, never for a glyph call (Gate 0f, `GLYPH_BARRED`).
Gate 0d therefore refuses it **for the recognition chain** while the corpus still reads it for attestation.
A guard that simply banned bitonal rasters would silently retire the only second witness the NT has.

---

## R7 — The existing ground truth was read from inadmissible rasters (NEW, 2026-08-06)

Fixing one file under R6.5 raised the obvious question — how many others? **Audited all 51 ground-truth
files by the witness and raster each declares.** The answer is not one file.

| what the file was read from | files | why it is inadmissible |
|---|---|---|
| `F` (legacy `S1`), via its JP2 package | **39** | `F` is **~168 ppi in all three volumes** and is barred from glyph-level work by §1.2 — the long-ſ nub spans under 1.6 px. Its OT JP2 is additionally a **4.17× render** of that 800×1124 source |
| `X` (legacy `S8`), via its JP2 package | **6** | `X` is the **excluded** witness: a 2.00× upscale of `B`-NT carrying **zero** real detail beyond it (measured: 0.0002 energy above `B`'s Nyquist, against 0.0093 in `B`'s own top band) |
| `M` (legacy `S6`), via its JP2 package | **3** | `M` is PDF-primary; the JP2 is a **1.73× render** of the ~2955×4206 CCITT |
| `M`, via the primary CCITT | 3 | admissible — R6.2/R6.3, plus the privilege re-read under R6.5 |
| **`B` (~545 ppi) or `P` (~411 ppi)** | **0** | — |

**48 of 51 inadmissible**, reproducible on demand: `python3 witness/audit_gt_rasters.py` (exit 1 while any
remain). The count was 49 before the R6.5 re-read; it is the audit's own regression test that it fell by one.

**Not one ground-truth file was read from the base exemplar or its surrogate.** `pixel_source()` raises for
every witness in the top three rows; it guards *pipelines*, and a human transcription walks straight past it.

### The claim, stated precisely

This does **not** say 48 files are wrong. It says **their glyph-level calls are unverified**, and that
re-reading on an admissible raster reliably moves the epistemic state. Two spot-checks, moving both ways:

- **`M`, the 1634 privilege (R6.5).** Three readings **changed** — `d. Roüen`→`de Roüen`,
  `Marchans`→`Marchands`, `Donnees`→`Données` — and two of them were spans the file had itself flagged as
  unresolvable at the raster it had.
- **`B`, `matter-ot1-approbatio` (read from `F`).** Both flagged uncertainties **resolved and confirmed**:
  the worn `r` of `Vniuerſitate` is plainly present at 545 ppi, and `Duacena` is genuine, not a worn
  `Duacenſi`. The transcription was right; it was merely **unverifiable**.

Confirmation and correction are both results. What is not a result is a call left resting on an image that
cannot carry it.

### The remedy is in-corpus — no acquisition is required

| files read from | re-read on | note |
|---|---|---|
| `F` (OT) | `B` ~545 ppi, or `P` ~411 ppi | both already held and jp2-primary |
| `X` (NT) | `B`-NT 2955×4343 | `X` **is** `B`-NT upscaled, so `B` is simply the same scan at its true raster |
| `M` | the embedded CCITT, via `witness/extract_pdf_leaves.py` | as done for R6.5 |

The only genuine ceiling is the two NT leaves `B` lacks — the Censure and Preface p. 1 — where `M`'s
~380 ppi CCITT is the best that exists. That limit is already recorded and is not new.

| # | step | deliverable | acceptance |
|---|---|---|---|
| R7.1 | Re-read the 6 `X`-based NT files on `B` | same loci, admissible raster | every changed reading carries its measurement; `*.pre-primary-raster` backups retained |
| R7.2 | Re-read the 4 `M`-based files on the CCITT | as R6.5 | one is DONE (`matter-ot2-privilege-du-roi`) |
| R7.3 | Re-read the 39 `F`-based files on `B`/`P` | the bulk of the corpus | prioritise files whose loci `B` or `P` actually hold; report any locus neither holds rather than substituting `F` silently |
| R7.4 | Move the guard to where the reading happens | a ground-truth field asserting the raster against `PRIMARY`, checked by a test | a file declaring a render-derived raster **fails the test**, proven by a negative case |
| R7.5 | Retire `jp2_page.py`'s routing table | `OCR_DIR_TO_JP2` **deleted**; `OCR_DIR_TO_WITNESS` maps a legacy `ocr_dir` to a witness and the witness resolves its own raster via new `witnesses.glyph_source()`; `test_raster_routing.py` | no second raster mapping exists; barred witnesses **raise** on the pixel route and still serve the structure route; the verified `jp2-S09ot2` −1 offset survives | **DONE 2026-08-07** — see below |
| R7.5a | Re-key the `ocr_dir` values the routing fix exposed as ill-formed | `jp2-S06` names a FILE spanning two settings 53 years apart, not a witness; `jp2-S06nt` / `jp2-S06ot` are the well-formed ids | every record names a witness and a setting; `jp2-S06` raises until they do | **DONE 2026-08-08** — corpus, ground truth and addressing split; boundary READ, not inferred; an unrecorded off-by-one removed |
| R7.5a-2 | Regenerate the derived artefacts that predate the split | **261 files / 70,855 occurrences** still carry `jp2-S06` (was 339 / 91,490, and 347 / 95,548 before that) — the 77-file `consensus-full/` set was regenerated 2026-08-09 under R9.4b — coverage audits, consensus, QC probes | `audit_s06_keys.py` exits 0 | **OPEN and BLOCKING.** They are REGENERATED, never edited: patching a derived file is how a stale artefact acquires the look of a current one (R7.5d) |
| R7.5a-3 | The addressing declaration, and the scoring rule that was hiding inside it | `witness_inventory` S6 declared no NT, so `volume_books()` gave the addressing DP an OT-only state space and force-fitted 800 NT leaves onto OT books — median fit 0.156, **zero** records above 0.5 against 44.8–76.7% everywhere else. The OT half was damaged the same way and the R7.5a split preserved it: 291 of 2,071 pages change book on regeneration, the OT tail smeared onto `daniel` | S6 declares its NT; both halves regenerated (not transformed); every volume clears the 0.5 fit floor; `test_drop_rule_enforced.py` exits 0 | **DONE 2026-08-08** — `drop_tomes` was a SCORING rule read as a CONTAINMENT claim. **Retired (Sir):** its premise (S6's NT repeats an edition A/B/C already hold) died with the 1633 finding — `NT-1582-M` is the second witness to a setting the NT holds once. No scorer ever read it; the addressing defect was the only thing enforcing it. `jp2-S06nt` localizes **2,344** pilot-book verses, was recorded as **zero** with a hand-written "known absence" note, and now attests matthew 1,067 · john 877 · apocalypse 400 |
| R7.5b | Update the modules calling `jp2_page` to declare which route they need | each call site passes `structure=True` or uses `pixel_path()` deliberately | no caller receives a render while believing it has a capture; the strict default means an un-updated caller **fails loudly** rather than silently succeeding on the wrong pixels | **DONE 2026-08-08** — all six; every one was STRUCTURE, and saying so is the point |
| R7.5c | Retire `curated_sources.py`'s parallel map | its comment says the map *"must stay in sync with `jp2_page.OCR_DIR_TO_JP2`"* — a **third** copy of the same mapping, kept in sync by hand | the curated set is derived from the registry, not restated | **DONE 2026-08-08** — derived; the allowlist can no longer disagree with the registry |
| R7.5d | Retire the routing table's **surviving OUTPUT** | `tome-map-v2.json` (2026-07-28, 4.7 MB, tracked) embedded all four wrong routes as literal `jp2_dir` / `jp2_file` strings. Deleting the table left its output routing, one indirection further out and with no guard on it | no tracked artefact carries an `ocr_dir` → raster path; addresses are witness + leaf index | **DONE 2026-08-08** — deleted (unbuildable until R7.5a); `master-source-list.json`'s one vestigial `jp2_dir` stripped; guarded |

> **R7.5a DISCHARGED 2026-08-08 — and the boundary was READ, not inferred.**
>
> The arithmetic does not settle this question and it is worth seeing why. The registry gives `OT-1635-M`
> 2,071 leaves and `NT-1582-M` 800; the package holds 2,872. **One leaf is unaccounted for**, and no count
> can say which testament it belongs to — only which side of the ledger is short. All three candidate leaves
> were rendered from `S06.pdf`, M's primary artefact, and read:
>
> | package leaf | what is printed on it | verdict |
> |---|---|---|
> | 2070 | `FAVLTS ESCAPED IN THE PRINTING`, and below it `EXTRAICT DV PRIVILEGE DV ROY` — granted to Iean le Cousturier at Rouen, dated **1634** | **last OT leaf** |
> | 2071 | nothing. **0.00% ink** against 4–9% on its neighbours | **blank divider — in NEITHER witness** |
> | 2072 | `THE NEVV TESTAMENT OF IESVS CHRIST` … `PRINTED AT RHEMES, by Iohn Fogny. 1582.`, in its woodcut border | **first NT leaf** |
>
> 2,071 + 1 + 800 = 2,872, with nothing left over. The registry's ranges were right; the missing leaf is a
> blank sheet between two testaments, and `witnesses.s06_volume()` **raises** for it rather than folding it
> into whichever side is convenient. A leaf in neither setting is a third answer, and collapsing a third
> answer into a binary is exactly how a boundary quietly moves.
>
> **An unrecorded off-by-one was sitting underneath the re-key.** The OCR corpus for S06 was **1-based**
> (`S06_0001`…`S06_2872`) while every rendering of it — JP2 package, JPEG re-acquisition, PDF — is
> **0-based**. So OCR page N was package leaf N−1, and `JP2_INDEX_OFFSET` had **no entry for `jp2-S06`**,
> which asserts alignment. Text and image disagreed by one leaf on all 2,872 pages, silently — the same
> defect `jp2-S09ot2` carries an offset to prevent. Verified at two points ~1,000 leaves apart on
> unmistakable content: OCR `S06_2071` is `FAVLTS ESCAPED`, which is package **2070**; OCR `S06_1029` is
> `THE SECOND TOME OF THE HOLIE BIBLE`, which is package **1028**.
>
> The fix does **not** add two offset entries. The files are **renumbered 0-based and witness-relative**,
> like every other volume, so the offset no longer exists rather than being recorded. *An offset that does
> not need to exist is one that cannot be dropped in a later refactor.*
>
> ⚠ **A dead metric was tried first and would have given the wrong answer.** Correlating per-leaf ink
> fraction against per-page OCR character count returns r ≤ 0.13 at **every** offset from −3 to +3 — no
> signal at all — and its argmax is **+1**, the opposite of the truth. On bitonal CCITT with noisy OCR that
> metric measures nothing. It is recorded because a null from a dead metric is not evidence, and this one
> was ready to be read as evidence.
>
> Scope stated plainly: the **authoritative** record sets are re-keyed — the OCR corpus (2,071 + 1 + 800),
> the three ground-truth files, and both addressing artefacts. **347 derived artefacts still carry the old
> id and are R7.5a-2, OPEN and blocking.** They are regenerated, not edited. `audit_s06_keys.py` exits **2**
> for a regression in the authoritative sets and **1** while the backlog stands, so the two are never
> confused for one another.
>
> Negatives proven by injection: the divider being given a setting; a ground-truth file reverting to the
> ambiguous id (exit 2, not 1); a half losing a leaf (exit 2).

**The six call sites R7.5 breaks, named rather than left to be discovered.** These read
`jp2_page.OCR_DIR_TO_JP2` at runtime and now raise:

| module | use | what it needs instead |
|---|---|---|
| `ocr_complete_volume.py` | `.get(ocr_dir)` | `witness_of()` + `pixel_path()` / `structure_path()` |
| `integrity_sweep.py` | `.get(ocr_dir)` | as above |
| `build_tome_map_v2.py` | `.get(od)` | **structure** — a tome map is page order, so `structure_path()` |
| `tome_map_audit.py` | `.get(ocr_dir)` | **structure** |
| `source_inventory_audit.py` | `set(...)` — wants the *set of known ids* | `OCR_DIR_TO_WITNESS` |
| `curated_sources.py` | comment only, but restates the map | R7.5c |

> **DISCHARGED 2026-08-08 (R7.5b · R7.5c · R7.5d).** All six sites updated, and the result is the
> finding: **every one of them was STRUCTURE.** Not a single caller of the retired table wanted pixels.
> They were counting leaves, aligning indices, detecting un-OCR'd pages, addressing a tome map. The
> table's whole load-bearing use was page bookkeeping — and it was handing out raster DIRECTORIES to do
> it, which is why glyph work could reach the wrong image through a door built for counting.
>
> They share one new accessor, `jp2_page.structure_leaves()`, which returns the LEAVES rather than the
> directory. Handing back a directory is what made the table a route; a caller that receives leaves can
> count them and cannot open the wrong ones.
>
> **The count of duplicated maps went from one to four while discharging this step**, and each was
> invisible because the copies happened to agree:
>
> | map | second copy | had it drifted? |
> |---|---|---|
> | which witnesses are barred | `audit_gt_rasters.py` | no — caught at R7.5 |
> | `ocr_dir` → witness | `audit_gt_rasters.py` | **YES** — it resolved `jp2-S06` to `OT` where the registry *refuses* |
> | the verified `jp2-S09ot2 = −1` offset | `tome_map_audit.py` | no — and the audit would have certified an alignment the resolver did not use |
> | `ocr_dir` → curated source | `curated_sources.py` | no, and its comment said *"must stay in sync"* |
>
> The `jp2-S06` drift is the one that matters. The registry refuses that identifier *because* guessing which
> of two settings 53 years apart a leaf belongs to is the four-month error; the audit's private copy guessed
> it anyway, and nothing could see the disagreement because only one of the two was ever consulted per call.
> **A duplicate is not dangerous when it drifts — it is dangerous from the moment it exists, because from
> then on the agreement is a coincidence nobody is checking.** The test now fails on a second *literal*
> definition of any of the four, and separately fails if the GT audit's legitimate extension SHADOWS a
> registry entry rather than extending it.
>
> **R7.5d is the half worth keeping.** `tome-map-v2.json` was built by the table on 2026-07-28 and still
> held all four wrong routes as literal strings — `jp2-S04` → the retired MRC composite, the three
> `archive-*` volumes → `F`'s renders. Deleting the code left its **output** routing, one indirection
> further away and behind no guard at all. It is deleted rather than corrected: it cannot be rebuilt until
> R7.5a re-keys `jp2-S06`, and a tome map short by 2,872 leaves looks exactly like a tome map. The builder
> now **refuses to write** in that state and exits 1, naming the volume and the page count it could not
> place, instead of emitting a ten-volume map that reports "all addressed". A guard is not finished when the
> code is fixed; it is finished when the artefacts the bad code produced are gone too.
>
> Negatives proven by injection, exit 1 each: a revived second `ocr_dir` map; a curated map drifted from the
> registry; the GT audit shadowing a registry entry; an artefact re-acquiring a `jp2_dir`; the dropped
> S09ot2 offset.

**The attribute is retired with its reason attached, not merely deleted.** A bare
`AttributeError: module 'jp2_page' has no attribute 'OCR_DIR_TO_JP2'` tells the next reader nothing about why
the name went or what replaces it, and an uninformative failure invites the *fastest* repair rather than the
right one — most probably putting the table back. A module `__getattr__` raises an error naming the defect,
the four wrong entries, the replacement API and this roadmap step. **Failing loudly and failing informatively
are different properties, and the guard only bought the first.**

**R7.5 is the mechanism, not a tidying job — and it was verified, not assumed.** `jp2_page.py`'s
`OCR_DIR_TO_JP2` keys **are** the `ocr_dir` values the ground-truth files carry, so this table is literally
what routed 48 transcriptions to the wrong image. It is not only the docstring that is stale:

| `ocr_dir` | routes to | should be |
|---|---|---|
| `archive-nt-1582`, `archive-ot1-1609`, `archive-ot2-1610` | `S01` JP2 | `F` is PDF-primary **and barred** — these loci belong on `B`/`P` |
| `jp2-S08` | `S08` JP2 | `X` is PDF-primary and **excluded**; the locus belongs on `B`-NT |
| `jp2-S06` | `S06` **JPEG** (2550×3301, a 300 dpi render) | the CCITT inside `S06.pdf` |
| `jp2-S04` | `S04_1633-rheims-nt/…_jp2` — the **retired MRC composite** | `newtestamentofie00engl_jp2`, the Princeton original, which is what `pixel_source()` returns |

So a caller using `witnesses.pixel_source()` and a caller using `jp2_page.py` get **different rasters for
the same witness**, and only one of them is guarded. Two routes to the pixels is the defect; the fix is one
route. This is the same shape as the `role="structure"` leak — a retracted decision still live in code —
except that here the code disagrees with the guard rather than merely with the plan.

> **DISCHARGED 2026-08-07.** `OCR_DIR_TO_JP2` is **deleted**, not corrected: a second mapping is the defect,
> because any second mapping can drift from the registry, and a table that is right today is a table that is
> unguarded tomorrow. An `ocr_dir` now resolves to a *witness* and the witness resolves its own raster.
>
> Four things the fix had to get right, none of which a simple deletion would have:
>
> - **`M` had to be re-routed, not un-routed.** Its JP2 package is genuinely corrupt (`..._jp2_broken`) and
>   its PDF holds the real CCITT stencils, so the PDF *is* its primary artefact. Deleting the `jp2-S06` entry
>   would have left `M` with no pixel route at all, which reads as "this witness has no rasters." New
>   `witnesses.glyph_source()` returns `("pdf", …)` for it and `jp2_page` extracts **per leaf, on demand** —
>   `M`'s PDF is 2,872 pages and listing all of them to answer one index is how a guarded route becomes slow
>   enough that someone routes around it.
> - **`glyph_source()` is not `pixel_source()`.** `pixel_source()` answers a narrower question — *is this
>   witness's JP2 package the capture, or an IA render?* — and therefore refuses `M`, whose JP2 is neither.
>   Routing glyph work through it would have barred the one witness holding the only genuine 1582 Censure and
>   Preface leaves. The two functions answer two questions and both are kept.
> - **The bar list had to move.** `BARRED` lived in `audit_gt_rasters.py`; it is now `witnesses.GLYPH_BARRED`
>   beside the registry and the audit imports it. Two copies of *which witnesses are barred* is R7.5 one level
>   up, and `test_raster_routing.py` fails if a second definition appears anywhere in the tree.
> - **`jp2-S06` names a file, not a witness**, and it is on **113,514 records**. `S06` is one volume carrying
>   the 1635 Rouen OT *and* the 1582 Rheims NT — two settings 53 years apart — so resolving it to either is a
>   guess of exactly the kind that cost four months. It now **raises** and names `jp2-S06nt` / `jp2-S06ot`.
>   The records are re-keyed by R7.5a; the ambiguity is surfaced rather than silently resolved.
>
> The `jp2-S09ot2 = −1` offset is carried across unchanged and is asserted by the test: it is a verified
> off-by-one, and losing it in a refactor silently returns the next leaf for every page of S9's entire OT
> volume 2.
>
> **The default is strict.** `jp2_path()` now takes the guarded pixel route unless the caller passes
> `structure=True`. Roughly twenty modules call this API and they split between legitimate structural use
> (page order, counts, collation — admissible for every witness, since a render preserves page order) and
> pixel use. They are **not** silently patched: the strict default makes each one fail loudly and say which it
> is (R7.5b). The previous behaviour was silent success on the wrong pixels, and the only honest replacement
> for silent success is a loud failure.
>
> **A gap this found in its own guard, recorded because it is the more instructive half.** The first version
> of `test_raster_routing.py` checked that whatever was barred refused pixels and whatever was not resolved
> cleanly — and **passed** when `F` was deleted from the bar list, because un-barring `F` simply moved it to
> the other branch. A self-consistent check constrains nothing. It now asserts the bar set is exactly
> `{F, X}`, so un-barring a witness is a deliberate edit to a test rather than a silent widening. This is the
> same shape as the original error — the independence test that contrasted `F` against `B` could only ever
> license *"`F` is not `B`"* — and **it was found by injection, not by reading the code.**

**R7.4 is the one that stops this recurring.** Three instances now share a single shape — the vv→w flip,
`d. Roüen`, `Marchans` — and in all three the rule was right, the observer was careful, and only the image
was wrong. A guard that lives in `pixel_source()` cannot catch a human reading a PNG. It has to sit on the
ground-truth record itself.

⚠ **This re-opens ratified ground truth and is flagged, not actioned silently.** No transcription is being
withdrawn on suspicion — each stands until re-read.

---

## R8 — `F`'s New Testament is the 1633 edition (NEW, 2026-08-06)

**A load-bearing claim was wrong for four months.** `NT/S01` was registered as `NT-1582-F`, an independent
witness to the 1582 Rhemes New Testament. Its body is the **1633 Rouen** setting — page for page and line
for line with `NT-1633-R` at a constant leaf offset of **+4**, including the shared misprint `Iralie` for
`Italie`, while the genuine 1582 (`B`) puts Apocalypse ch. XXII on printed **743** against `F`'s **692**.
Full evidence at masterplan §1.1c.

**Consequences, in order of severity:**

1. **The New Testament has ONE witness to its own setting**, `B` — not two. `X` was already known to be `B`
   upscaled; `F` is a different edition; `M` is bitonal and prelims-only. Every redundancy assumption for
   the NT is void.
2. **`F`'s OT1 and OT2 are unaffected** — checked at three separated points each, same setting as `B` and
   `P`. The defect is confined to one file.
3. **§1.4's cross-edition "contamination" becomes a same-edition supply.** The foxing result stands; the
   inference drawn from it does not.
4. **R3.5 is DISSOLVED, not completed.** It asked for the 36-leaf `F`/`B` difference to be attributed leaf
   by leaf. The question was malformed: they are different editions, and a leaf-count difference between
   editions attributes nothing.

| # | step | deliverable | acceptance | status |
|---|---|---|---|---|
| R8.1 | Correct the registry | `year=1633`, `wid → NT-1633-F`, evidence in the record | tree rebuilds, 12/12 verified | **DONE** |
| R8.2 | Guard the class of error | `setting()`, `witnesses_to()`, `assert_same_setting()` | `test_setting_guard.py` — cross-setting collation **refused**, both directions exercised | **DONE** |
| R8.3 | Attribute `F`'s 1582 title page | it is the genuine 1582 Rhemes setting, **duplicated at leaves 0 and 2**, on a 1633 body | blank-paper correlation against `B`'s title page: a match ⇒ spliced from `B`'s scan; control-level ⇒ the copy is a made-up one. **State which, or state that neither is supported** | OPEN |
| R8.4 | Re-audit **every** witness for setting, not just the suspected one | printed page + running head at ≥3 separated points per witness, against a known-good partner in its claimed setting | a table covering all twelve records; **any witness whose setting was never checked is named as unchecked, not assumed sound** | **DONE** — 11/12 verified, `OT-1635-M` named unverifiable; §1.1b |
| R8.4a | **Verify the FOOT criteria §0.3 names and R8.4 never read** — signature and catchword | `verify_setting.py` gains a foot band anchored on the text block; readings in `setting-readings.json` under `foot_readings`/`foot_pairs`/`foot_negative_controls`; enforced by `test_setting_verified.py` | every setting agrees on **signature, catchword and last line** at a matched page, and a **negative control across two settings differs**; negatives proven by injection | **DONE** — 11/11 partnered witnesses agree; `B` @147 `T ij`/`30. Paſſing` vs `R` @147 `CHAP.` separates 1582 from 1633; §1.1b R8.4a |
| R8.4b | Extend the foot criteria from one matched page to **≥3 separated points**, matching the head pass | additional foot probes per setting, recorded as data | **`witness/audit_setting_points.py` exits 0.** Machine-checked, not asserted in prose (see below) — each setting agrees on signature and catchword at ≥3 **separated** printed pages, adjacent leaves counting once, **and** the foot negative controls rise with the positive side | OPEN — until then the foot criteria **corroborate the head result at one point**, they are not an independent three-point verification. Currently **8 shortfalls**: 7 pairs at 1 point of 3, plus 1 negative control of 3 |

**R8.4b's acceptance is now machine-checked, at Sir's instruction (2026-08-10).** It had been held by
a **prose status line** in Master Plan §2 — and that line had already flattened to *"the full §0.3
criterion"* within four days of the §0.3 rewrite whose entire occasion was an audit that came out
*"stronger on one axis and silently weaker on two."* **A correction is not self-enforcing**; prose is
precisely what let the flattening happen the first time, so the distinction now lives in a check.

🔴 **SEPARATED points, not matched pages — a hole found while writing the check.** `test_setting_verified`
counted page *entries* against the ≥3 criterion. `OT1-1609-P` vs `F` records **seven** head pages, but
they are `[222,223,224] · [457] · [918,919,920]` — **three locations read three times each**. Three
*adjacent* leaves would have satisfied the old count while saying nothing about the volume's span,
which is a criterion weaker than §0.3's *"spread through the volume"* and **reads identical in the
output**. Both numbers are now printed (`3 separated / 7 page(s)`). `MIN_SEPARATION = 50` printed
pages is the weakest value that separates the clusters actually recorded; it is not tuned, and
widening it can only make the criterion stricter.

⚠️ **The check is split across a guard and an audit, deliberately.** `test_setting_verified.py`
(guard, exit 0) asserts the **head** criteria at ≥3 separated points, so the standing result cannot
erode. `audit_setting_points.py` (audit, exit 1) carries the **foot** shortfall. Folding the foot
requirement into the guard would turn it red, which in this project's grammar reads as a regression
rather than an open remedy — and the pressure would then be to weaken the number rather than read
two more pages.
| R8.5 | Bind the plan's counts to the registry | `test_counts_vs_doc.py` | doc/registry disagreement **fails**, proven by a negative case | **DONE** |
| R8.8 | **Bind the roadmap's own verification standard to reality** | `test_verification_standard.py` — parses the command block, checks every command exists, every `-> N/M` claim matches what the command prints, every guard on disk is documented, guards exit 0 and open audits exit non-zero | a stale count, an undocumented guard, a named-but-missing command, or the section being renamed away each **fail**; all four proven by injection | **DONE** — this file's block claimed `10/10` while the tree verified `12/12`, and listed none of the guards |
| R8.6 | Re-examine every ground-truth file taken from `NT/S01` | 9 files (`matter-nt-*`, `nt-marke-*`, `scripture-2john`, `scripture-matthew-28`) | each re-filed as **1633** or re-read on `B`; **none silently left labelled 1582** | OPEN — overlaps R7.3 |

**R8.4 was the one that mattered most, and it is now run.** The error was not found by a test; it was found
by chasing an unrelated leaf-count discrepancy. **No witness's setting had ever been verified against a
same-setting partner** — the concordance verified *title pages*, and a title page is exactly what `F` turns
out to have borrowed. Eleven records were **unchecked**, not sound. `F` was simply the one that happened to
be looked at.

**Outcome (2026-08-06): eleven of twelve verified; no second mis-filing.** Every witness now agrees with a
partner in its claimed setting at three or more separated printed pages — page number, running head,
sidehead, text and line breaks together, marginal apparatus included. Full report and evidence at **§1.1b**
(the acceptance criterion said §1.1c; the report went to §1.1b because that section already owns
cross-witness comparison, and §1.1c stays the narrative of the `F` finding itself). The audit also supplies
its own **negative control**: at printed p.147 under the identical running head *ACCORDING TO S. LVKE*, `B`
prints Luke 4:31 and `F`/`R` print Luke 7:44 — the method visibly separates settings, so its positives are
worth something.

**The twelfth is `OT-1635-M`, and it is not verified — it is unverifiable by this method.** It is the sole
record of the 1635 Rouen setting, so no partner exists. Its date rests on internal evidence: its own
colophon *M.DC.XXXV* and the 1634 privilege it prints. That is stated, not glossed, and
`witness/test_setting_verified.py` holds it in an explicit `SOLE_WITNESS` list which **fails if a partner
ever appears** and is not then collated.

**What now stops recurrence.** `test_setting_verified.py` fails when a registered witness has **no readings
at all** — absence presents as absence rather than passing silently, which is the R1.4 rule applied to
provenance. Both branches are proven by injection: a dropped witness and a verification standing on one
matched page each fail the run, and exit code 1 is checked, not assumed.

| # | step | deliverable | acceptance | status |
|---|---|---|---|---|
| R8.7 | Settle whether `NT-1582-M` and `NT-1582-X` share a source | they have the **same leaf count (800) and the same leaf→printed-page map at every probe**, while `B` runs 5 leaves later; same-setting does not require that | a stated verdict — **same source · independent copies · not resolvable on available evidence** — with the discriminator named. ⚠ **`M` is bitonal CCITT: grayscale NCC against a continuous-tone scan is a DEAD METRIC (0.067 for two genuine 1582 title pages) and a null from it is not evidence.** Use physical accident that survives binarisation, or argue from structure | OPEN |

**R8.7 matters for a specific reason, not as tidiness.** §1.4 credits `M` with the corpus's only genuine
1582 Censure and Preface p.1, and identifies it as the source of `X`'s two supplied leaves. If `M` and `X`
shared a source that claim needs restating. **The existing evidence already argues against it and should be
weighed first**: `B` lacks both leaves, `M` carries them, and a file cannot supply what it was derived from.
That is an argument from the record, not a new measurement, and R8.7 should start by testing whether it
holds rather than by reaching for a correlation.

**R8.6 is the ground-truth blast radius.** Nine of the files audited under R7 declare `ocr_dir:
archive-nt-1582` — that is `F`. They were read from a 1633 book while being recorded as 1582 readings. This
compounds with R7: those files are on an inadmissible raster **and** the wrong edition. They must be
re-filed before any of them is cited.

**`audit_gt_rasters.py` now detects this rather than relying on this paragraph.** The audit previously
reported those nine under `F`'s *resolution* bar, because `BARRED` was keyed on the **siglum alone** — the
same assumption that produced the original error, that a copy has one character across all volumes. `F` is
low-resolution in the OT and **a different edition** in the NT, and only the second is fatal: re-reading a
1633 leaf at 545 ppi fixes nothing. The registry now carries `TRANSCRIBED` (the edition each volume is a
transcript *of*) and `attests_transcribed_setting()`, and the audit reports **`WRONG SETTING` first**, ahead
of the resolution and render reasons. It returns `None`, not `False`, for the whole-Bible `OT` pseudo-volume
behind `M`'s 1635 prelims — admitted *because* it is another edition — and the test asserts that
distinction, since collapsing "not the text" into "not applicable" is how `NT-F` stayed admissible.
Verified: **9 files flagged, no others.**

### Why this was missed — a method note, not an apology

The test that established `F` as an independent copy was run **against `B`** and correctly returned noise at
every offset. It was read as *"`F` is an independent copy of the 1582"* when it licensed only *"`F` is not
`B`."* The visual note recorded at the time — *"different text, different signature series"* — is this
finding, written down and misread as evidence of a different **copy** rather than a different **setting**.
`R` was never tested against `F`, because `R` had been filed as "the other edition" and so was not a
candidate partner.

⇒ **A test distinguishes exactly the hypotheses it contrasts, and filing a witness under a label removes it
from the candidate set.** Both are now structural: `witnesses_to(vol, year)` enumerates candidate partners
from the registry rather than from memory of how things were filed.

---

## R9 — Evidential scope, declared per witness and read by a scorer (NEW, 2026-08-08)

**Discharges** §2 **Gate 0f**. **Status: OPEN.** Raised by Sir's instruction to restate `M`'s role per
half, which exposed that the role limits §1.1a has always stated were **enforced nowhere**.

### The finding

`OT-1635-M` is excluded from the verse text in prose, in four documents, and has been attesting **psalms
2,515 · genesis 1,530** in `coverage-audit-verse.json` for as long as the audit has run. `NT-1582-M` was
barred from the verse text by the same prose and is a witness to the base exemplar's own setting, so the
one term was **over-restricting one half and under-restricting the other at the same time**.

Three separate defects, and they must not be conflated:

1. **A role name doing two jobs.** *frontmatter witness* meant "different edition" for the OT half and was
   read as "bad raster" for the NT half. Split in §1.1a into **frontmatter witness (different edition)**
   and **independent witness, low-resolution scan**. This is the `structure only` error repeating — a limit
   on one *digitisation* stated as a property of the *copy* — on a different witness, four rows below the
   table that records the first retirement.
2. **No consumer.** No code has ever read a role. The nearest thing was `witness_inventory.drop_tomes`,
   which named the right file for the wrong reason, was read by exactly one consumer as a *containment*
   claim, and produced the R7.5a-3 addressing defect. Retired at Sir's instruction; `test_drop_rule_enforced.py`
   now fails if a scoping rule is ever again declared without one.
3. **The gate's grain was coarser than the distinction.** The audit's admission filter is
   `curated_sources`, which answers *"may material from acquisition S6 be used?"* — and S6 is one
   acquisition holding two witnesses with two roles. **A filter cannot enforce a distinction it cannot
   express.** Scope is therefore declared and filtered at **witness** grain, beside curation and not inside
   it.

| # | step | deliverable | acceptance |
|---|---|---|---|
| R9.0 | Move `NT-1582-M` between roles in the registry | `witnesses.py`: `("NT","M")` role `frontmatter` → `lowres`; `("OT","M")` stays `frontmatter` | the registry says what §1.1a says; `test_counts_vs_doc.py` exits 0 against the revised §1.1 table |
| R9.1 | **Derive** `verse_scope` from the role — do not hand-assign it | `witnesses.verse_scope(vol, sig)` from a single `ROLE_VERSE_SCOPE` table: `base`/`surrogate` → **full** · `lowres`/`support` → **collation** · `frontmatter`/`excluded` → **none** | a role with no scope entry **raises** — a role added later cannot default into admission. Hand-assignment is refused precisely because that is how §1.1a and the code would drift apart again |
| R9.2 | Make the read path refuse, not merely the sweep | `corpus_localize.load()` **raises** `VerseScopeError` for a `none` witness, naming the role and Gate 0f. Opt out only by explicit `scope_check=False`, for tooling that audits the artefact itself | a consumer reaching `load()` fails loudly rather than quietly scoring an inadmissible witness. **Strict-by-default, the pattern R7.5b established for `jp2_page`** — **DONE** |
| R9.2c | **Close the bypass `load()` does not cover** | ⚠️ The draft of R9.2 asserted `load()` was *"the function every verse consumer already goes through"*. **It is not, and the claim was checked only against module imports rather than call sites.** Nine modules read `.corpus-localize-<dir>.json` **directly** — `book_audit`, `integrity_sweep`, `gen1_rescore`, `gen1_r3`, `gen1_rerecog_eval`, `gen1_wordboxes`, `allfail_anatomy`, `split_confusions` — so the strict default guards `qc_audit` and nothing else. Route each through `load()`, or through a new `load_admitted()` for the sweeps | `witness/test_verse_scope_bypass.py` exits 0 only when no module outside `corpus_localize` reads the artefact path directly. **Exit 1 is the healthy state until they are converted** — an audit that starts passing before its remedy lands has stopped looking. **DONE 2026-08-10 — see R9.2c-1 … R9.2c-4 below** |
| R9.2c-1 | ⚠️ **`load()` was the wrong conversion target, and converting to it would have re-made the defect** | `load()` returns `{(book, ch, verse): text}` and discards `page`/`fit` — which is precisely what every direct reader wanted. Converting them would have meant re-deriving `page` elsewhere, i.e. **making the gate cost evidence**, and a gate that costs evidence is routed around. NEW `corpus_localize.load_raw` / `load_verses` (whole artefact / the `["verses"]` sub-map, Gate 0f in front) and `iter_localizations` (the sweep route, which drops `none` volumes and **prints** the drop above the caller's figures) | seven evidential readers converted — `allfail_anatomy`, `gen1_rescore`, `split_confusions`, `gen1_rerecog_eval`, `book_audit`, `gen1_r3`, `gen1_wordboxes`; `audit_diagnose` to `iter_localizations`. **DATA-NEUTRAL, verified**: for all 10 admitted volumes `load_verses(od)` is `==` the raw read (21,437 spans compared); only `jp2-S06ot` (4,045) and `jp2-S08` (2,334) are refused. **The gated route is the cheapest one available, which is the property that keeps it the only one** |
| R9.2c-2 | `source_inventory_audit` exempted, and **the exemption is machine-checked** | it globs the artefact FILENAMES to inventory which volumes are localized and never opens one. But an exemption resting on *"this read is bookkeeping, not evidence"* is a claim, and this project's standing lesson is that **a filter cannot enforce a distinction it cannot express**. Here it IS expressible: scoring a verse needs its **`text`**; reconciling or counting one does not (`integrity_sweep` reads `key` + `rec["page"]` only) | the guard now voids any exemption whose module reads a verse `text` field. **Injection-proven**: adding `rec["text"]` to `integrity_sweep` → exit 1 naming the forfeit; removed → 0. The guard also now counts string constants via `ast` with docstrings excluded, because its first version fired on a docstring quoting the glob it had removed — **a check a comment can trip measures vocabulary, not call sites** |
| R9.2c-3 | 🔴 **A CONTAINMENT FACT WAS BEING READ AS A SCORING PERMISSION** (found by routing through the gate, not by reading) | `book_audit.witnesses_for_book` derived its witness set from `witness_inventory.tomes` — which says which books a volume's leaves **carry** — and both callers used it to decide what may be **scored**. So it was still handing `jp2-S06ot` and `jp2-S08` to the scorers, and the conversion raised `VerseScopeError` rather than passing. **This is R7.5a-3's category error with the arrow reversed**: there a scoring rule (`drop_tomes`) was read as containment and force-fitted 800 NT leaves onto OT books | `for_scoring=True` (default) filters by `witnesses.verse_admitted` and **prints** the drop; `for_scoring=False` for bookkeeping. **Paired run, same tree, only the gate differing, all 5 pilot books: every surviving witness byte-identical; `all_pass`/`split`/`all_fail` unchanged on every book.** The dropped witness contributed `localized 0, passed 0` and a 100% miss list — it was an empty shell in the set |
| R9.2c-4 | 🔴🔴 **THE PARITY SPREAD WAS THE BEST WITNESS'S OWN PASS RATE, ON ALL FIVE PILOT BOOKS** | that empty shell put a `0.0` in the floor, so `max − min` reduced to `max − 0`. genesis **0.7601** = S9's 0.7601 · psalms **0.633** · matthew **0.7594** · john **0.6507** · apocalypse **0.5728** — each **exactly equal** to that book's best pass rate. **A metric that measures nothing still produces a ranking** (the R7.5a dead-metric lesson, restating a real number so plausibly that nothing looked wrong). Gate 0f removes these two but NOT the mechanism: an *admitted* witness not yet localized puts the `0.0` straight back | the spread is now taken over witnesses with `localized > 0`, the excluded are **named** in `parity_spread_basis`, and with fewer than two readers it is **`None` with a reason, never `0.0`** — a spread of zero and the absence of a comparison are different claims (R1.4). **Injection-proven**: adding admitted-but-unlocalized `jp2-S04` to genesis → old formula 0.7601, new 0.0842 + `excluded: ['S4']`; one reader → `None` + why. **Corrected spreads: genesis 8.4 · psalms 15.4 · matthew 19.5 points.** ⚠️ **Every published parity-spread figure is superseded and belongs in R10.2's register** |
| R9.2a | Make the sweep skip cleanly, so the refusal is never load-bearing | `qc_audit.scan_ocr_dirs()` drops `none` volumes **before** calling `load()`, and prints what it dropped | `OT-1635-M` contributes zero attestations and the audit says so on stdout; a drop that printed nothing would be indistinguishable from a witness that had no data |
| R9.2b | Leave the **structural** sweeps alone, deliberately | `integrity_sweep`, `tome_map_audit`, `build_tome_map_v2`, `make_witness_tree` keep counting all 12 volumes | scope governs **evidence**, not **bookkeeping**. `OT-1635-M`'s 2,071 leaves stay in every denominator — dropping them would hide an inadmissible volume instead of excluding it, which is R7.5d's lesson (`integrity_sweep` prints UNCHECKED, never 0) |
| R9.3 | Guard it, with proven negatives | `witness/test_verse_scope.py`: (a) every one of the 12 records resolves a scope; (b) scope agrees with the §1.1a role table; (c) the audit's choke point excludes `none` — asserted by **calling** `scan_ocr_dirs`, not by reading it; (d) `load()` raises for a `none` witness | flipping `OT-1635-M` to `collation` **fails**; flipping `NT-1582-M` to `none` **fails**; deleting a `ROLE_VERSE_SCOPE` entry **fails**; all restored to exit 0 |
| R9.4 | Regenerate what the unenforced rule contaminated | `coverage-audit-verse.json` re-run with the gate live, and the **before/after delta reported per book and per source** | **DONE 2026-08-08.** Removed: `psalms/S6`, `genesis/S6` (`OT-1635-M`) and `matthew/S8`, `john/S8`, `apocalypse/S8` (`NT-1582-X`). **Added: none. Changed among survivors: none — not one attested or passed count moved by one.** That invariant is the test; it distinguishes "the gate fired" from "something else changed too" |
| R9.4a | ⚠️ **`X` was attesting too, and that was not in the plan for this step** | Building the scope table showed `NT-1582-X` — `B` re-wrapped and upscaled 2.000×, NCC 0.9847 — reaching the audit as `S8` with matthew 1,067 · john 876 · apocalypse 391, beside `B`'s own `S9` rows. **Every NT cross-source agreement figure computed before 2026-08-08 counted the base exemplar twice.** §1.1a said admitting `X` "would double-count `B` under a second name" and nothing enforced it | the NT figures must be **re-read** wherever a cross-source agreement or witness count was quoted from them — see R9.4b — **DONE 2026-08-09 as to the corpus**: `X` is refused by `coverage-audit-verse` (R9.4) and by the consensus fusion (R9.4b), and no artefact now counts `B` twice. **The already-published figures are a separate obligation and are R10.2**, not this row; closing R9.4a on the corpus while the old numbers stand quoted in the devlog would be exactly the laundering the register warns about |
| R9.4b | Re-state every NT figure that rested on `S8` | any report, devlog entry or companion claim quoting NT cross-source agreement, witness counts or consensus built before this gate | each such figure either recomputed or marked as **computed with `B` double-counted**; none left standing unlabelled — **DONE 2026-08-09 for the recomputation; the labelling half is R10.2** |

**R9.4b as executed (2026-08-09).** `consensus_v2.load_all_streams` discovered its sources by **globbing a
directory** — the exact re-entry route `curated_sources` was written to close, whose docstring names
`consensus_v2` as a builder that MUST filter and which **did not import it at all**. `consensus-full/matthew.json`
recorded `scan_sources` including `eebo-nt`, `eebo-vol1` (BANNED, S10–S15), `jp2-S08` (`X` = `B` double-counted)
and `jp2-S06` (the retired ambiguous id). Across the old 76-book set: **`jp2-S06` in all 76 · `eebo-nt` in 27 ·
`jp2-S08` in 27 · `eebo-vol1` in 1** — the 27 being the NT books.

*Why the module's own de-duplication could not have caught it, which is the reusable part:* supersession is
keyed on the **filename** (`jp2-<key>` supersedes `pdf-/eebo-/archive-<key>`). `X` is `jp2-S08` and `B` is
`pdf-S09nt` — **the same physical copy under two unrelated keys** — so the key test cannot express the
relation. Third instance of *a filter cannot enforce a distinction it cannot state*; the scope gate is keyed
on the **witness**, which can.

*The delta, measured so it is attributable.* Comparing against the stored `consensus-full` would have
confounded three simultaneous changes (the filter, the `2633cbb` migration, the R7.5a re-key), so the
pre-filter code was run against the **same tree**: on `matthew`, modern **0.9268 → 0.9367**, archaic
**0.9317 → 0.9321**, conservation **0.8370 → 0.8399**, verses 1070 both. Dropped `jp2-S06ot`, `jp2-S08`,
`pdf-S06`; added none. **Both directions were reportable and this is the direction that happened** —
removing a duplicate of `B` raised agreement slightly. Corpus-wide the archaic gate flipped on four books,
**in both directions**: `1-esdras`, `4-kings`, `1-paralipomenon` False→True and `2-thessalonians`
True→False (an NT book, the honest direction). All 76 regenerated; **0 books now fuse an inadmissible
source**; R7.5a-2 drew down **339 → 262**.

⚠️ **`eebo-nt`/`eebo-vol1` are absent from the migrated tree, so the BANNED branch never fires on live
data.** Its correctness would otherwise rest on the absence of the input rather than the presence of the
filter, so `witness/test_consensus_sources.py` proves it **by injection** against a synthetic source tree
with a symlinked real control that must survive. The guard's own negative is injection-proven twice: the
per-branch cases, and wholesale removal of the filter — which first died of a raw `AttributeError` deep in
a helper, *a non-zero exit naming a missing attribute rather than a missing gate*, and now reports that the
fusion is a bare glob again.
| R9.5 | State the consequence in the companions | §1.1/§1.1a, Overview, Walkthrough, Exec Summary carry the per-half roles and the corrected witness counts | the four documents agree with each other and with the registry |
| R9.5a | 🔴 **RE-OPENED 2026-08-10 — R9.5 was marked DONE and the Overview never agreed** | `OCR-OVERVIEW.md`'s witness table left the **low-resolution witness column empty for NT 1582** and filed `NT-1582-M` under *other · frontmatter* — the pre-R9.0 role — while the registry said `role=lowres` **and the Overview's own prose, ninety lines later, described it correctly**. The row is corrected | the acceptance is **machine-checked, not read**: extend `test_counts_vs_doc.py` to parse the companions' witness tables and compare role-by-role against the registry, so a table that disagrees with `witnesses.py` **fails** |
| R11.4 | ⚠️ **A SIXTH restatement, found 2026-08-14 (R11)** — `acquisition/purge_empty_ocr.py:23` reaches the same dead tree by **relative traversal** (`../../../../../.scratch/originaldr-project/sources/our-ocr-diplomatic`) rather than by naming the root, which is why the R9.6 sweep — written against modules that *restate* the root — did not see it. **A search shaped by the fix's vocabulary finds only the instances that share it.** | folded into R9.6's module list; `witness/test_project_root.py` must cover the traversal form too | OPEN |
| R9.6 | The migrated project root, restated in six modules | ⚠️ **This step was briefly numbered R9.5 in two code comments, colliding with the DONE step above; renumbered here and in `detect_our_ocr.py`.** Commit `2633cbb` moved the OCR project out of gitignored scratch into `projects/originaldr/`, and `detect_our_ocr.SCRATCH` was not moved with it. Both anchor reads resolved into a deleted tree, `load_anchor` skipped them with `continue`, and `run_book` reported the well-formed `{"verses_scored": 0, "error": "no anchor text"}` for **every book**. Fixed 2026-08-09 (`ORIGINALDR` + a raise). **Five modules still restate the root**: `detect_ocr_consensus:72` · `detect_sources:34` · `detect_s_dismas:53` · `build_modern_standard:28` · `build_consensus:41` | one derived root, imported not restated; **`witness/test_project_root.py` fails if any module names the old path**. 🔴 `detect_sources` and `detect_s_dismas` **`mkdir(parents=True)` and WRITE the anchor reads** — running either recreates the dead tree and writes the anchor where nothing reads it, silently |
| R9.6a | `madueke-b/merged.txt` did not migrate | `ocr_sample.MADB` points into the dead tree. A same-named file exists at `imports/Scripture/…/madueke/raw-b-extract/merged.txt` | **not repointed on resemblance** — checksum or line-count agreement against what the reads were built from, or the path is declared broken and the consumer made to raise. `MADB.exists()` currently degrades to an empty set silently (R1.4) |

**Acceptance for R9 as a whole:** `audit_gt_rasters`-style honesty — the audit's NT figures must **rise**
by `NT-1582-M`'s admission and its OT figures must **fall** by `OT-1635-M`'s exclusion, and both deltas
must be reported. A change that moved only the flattering direction would be evidence the gate is not
actually running.

⚠️ **`collation` scope is not a licence to train.** `NT-1582-M` is bitonal at ~380 ppi. R7's finding stands
in full: a glyph call made on it is unverified, and `witnesses.GLYPH_BARRED` is unchanged by R9. R9 governs
**attestation**, which is a different question from **adjudication**, and the whole point of the three-value
scope is that the corpus can now say so.

---

## R10 — The constitution's own machinery (NEW, 2026-08-10)

**Discharges** §0.5. **Status: PART — R10.1 BUILT (audit live, 6/35), R10.2 OPEN (nothing built).**

⚠️ **This line read "OPEN. Nothing built." until 2026-08-11**, while R10.1's own row below described a
working audit and the verification block ran it. The section's status line contradicted its own table —
the §0.6 failure mode, inside the section written to catch that failure mode.

### The finding

§0.5 has required two things since it was written, and **neither had a single roadmap step, acceptance
test, or line of code**:

1. *"Every prerequisite carries a **stated hour ceiling and a pre-registered decision rule** before it
   starts."*
2. *"Where a number must be reported before properly-sized evidence exists, it is reported with its
   confidence interval and the label **PROVISIONAL / non-citable**, and no gate closes on it."*

The first is not a bookkeeping nicety. §0.5 names **unstartability** as a forbidden failure mode precisely
because it *"produces the same observable outcome as preserving the status quo"* — and **R2 and R3, the two
sections on which Gate 0b and Gate 0c depend and therefore on which all transcription depends, have been
marked NEXT since this file was created with nothing built.** That is the named failure mode, sitting in
this document, uncaught for the life of the project because the rule that forbids it had no consumer. It is
the same shape as Gate 0f (a correct rule nothing read) and as Gate 0d (a rule nothing implemented), and it
is the third instance found in one review.

The second matters immediately: the **51 ground-truth files** were transcribed before Gates 0b and 0c
existed in any form (§2), and there has been no label available to say so. They are neither sound nor
discardable; they are *provisional*, and without the word they read as evidence.

| # | step | deliverable | acceptance |
|---|---|---|---|
| R10.1 | Ceilings and decision rules, enforced | every **OPEN** step carries an hour ceiling and a decision rule written **before** work starts; `witness/audit_prereq_ceilings.py` parses this file's step tables and section prose and lists the OPEN steps carrying neither | ⚠️ **This is an AUDIT, not a guard, and the distinction is load-bearing.** Only R2, R5 and R10 carry ceilings today, so it exits **1 over ~30 steps** — and **exit 1 is the healthy state until each section is next touched.** Filing it as a guard would force one of the two things this project forbids: bulk-inventing ceilings nobody reasoned about, or weakening the check until it passes. Coverage is reported as a **fraction that must rise**, never as a pass. Proven by injection: strip R2's ceiling → the count rises by one and R2 is named; restore → it falls back. ⚠️ **Reaching a ceiling ALERTS that the approach needs redesign and never closes the step** (§0.5) |


⚠️ **THE FRACTION FELL, 25% → 17%, and that is a real signal rather than a bookkeeping artefact (2026-08-10).** It read `10/40` and then **`6/35`**: five OPEN steps closed (R5.1, R5.2a/b/c, R9.2c) and **four of the ceilings went with them**, because §0.5 ceilings had been added precisely to the sections that were next touched. So the ceilinged pool is depleted by progress, and the OPEN remainder is *more* unceilinged than before, not less. **R10.1's rule "the number must RISE" is therefore not satisfied by doing the work — only by writing ceilings for sections nobody is about to touch**, which is the harder half and is exactly what the audit is for. Recorded rather than restated: a metric that moves the wrong way when the project progresses is worth understanding before it is corrected.

🟢 **AND THEN IT ROSE, 17% → 29% (`6/35` → `12/41`), 2026-08-11 — by the harder half, exactly as predicted.** Writing R2.1a–f as six sub-steps *inside a section that already carries a ceiling and a decision rule* added six OPEN steps and six ceilinged ones at once. That is the intended mechanism and it is worth naming: **the fraction rises when work is PLANNED under a ceiling, not when work is COMPLETED.** Closing steps lowers it; planning them properly raises it. A coverage metric that rewards planning and penalises completion is behaving correctly here only because the thing being covered is *the plan*, and R10.1 should not be "fixed" to reward completion instead. ⚠️ The corollary is a real risk: the fraction could be inflated by decomposing a ceilinged section into ever-finer sub-steps. It is a coverage number, not a progress number, and must never be read as the latter.
| R10.2 | The PROVISIONAL convention, and the register that uses it | a stated form for a non-citable figure (value · CI · what is undersized · what would settle it), plus **`PROVISIONAL.md`**: every figure and artefact currently standing on undersized or pre-gate evidence, named | the 51 ground-truth files are listed with the gates they precede; **every NT cross-source figure published before 2026-08-09 is listed or recomputed** (R9.4b's labelling half); **every parity-spread figure published before 2026-08-10 is listed or restated** (R9.2c-4 — they were the best witness's own pass rate, not a spread); no listed figure is cited in a companion without the label |

**Hour ceiling for R10 itself: 4h. Decision rule:** R10.1's guard ships parsing only the step tables if
prose parsing exceeds 2h — a ceiling on a ceiling-checker is not a joke, it is the first test of whether
the rule can be obeyed by the document that states it.

⚠️ **R10.2 is not a licence to publish provisional numbers more freely.** The label exists so that a figure
which *must* be quoted before its evidence is sized carries its own limits with it. A figure that need not
be quoted yet should simply not be quoted.

---

## R11 — Tracked code that only one machine can run (NEW, 2026-08-14)

**Discharges** §0.2 rule 6, *"every reading is addressable and checkable"*.
**Status: PART — R11.1 🟢 DONE · R11.2 🟢 GUARD BUILT AND ENFORCED · R11.3 🟢 DONE ·
R11.2a OPEN (audit live, 71/38) · R11.3a OPEN (nothing built) · R11.4 OPEN.**

Raised by Sir 2026-08-14 from an assessment of `.scratch/`, approved in full the same day.

### The finding

**The gold verification suite — three tracked, committed scripts — imported a harness that existed on
exactly one machine, in a gitignored directory.** `gold_verify.py`, `gold_ratify.py` and `a3_score.py`
each did `sys.path.insert(0, REPO / ".scratch" / "mask-eval")` and then `from harness import …`. The
harness was 15 KB of code with no copy anywhere else — not in git, not in any backup the repo knows about.

**Nothing said so, and nothing could.** The import resolved locally and the suite passed, so the defect
was invisible *precisely on the machine where the work was done* and total everywhere else. This is the
Gate 0f shape one level up: there, a rule existed that no code read; here, a verifier exists that no
other machine can run. **A verifier only one machine can execute is checkable by nobody**, which is what
§0.2 rule 6 forbids — and the gold set is what every downstream mask-detection claim is scored against.

⚠️ **The disk was the single point of failure for the evidence base, not for a convenience.** Losing it
would not have lost a tool; it would have lost the ability to re-verify any gold-derived number ever
published.

### Steps

**§0.5 compliance.** Every OPEN step below carries an **hour ceiling** and a **decision rule**
pre-registered before the work: **R11.2a 6h · R11.2b 2h · R11.3a 3h · R11.4 1h**. R11.5 is blocked by construction
and takes a ceiling when it unblocks, not before — a ceiling on work that cannot start would inflate
R10.1's coverage fraction without anyone having reasoned about the step, which is the corollary risk
R10.1 names. **Reaching any ceiling ALERTS that the approach needs redesign; it never closes the step
and never accepts the shortfall.**

| # | step | deliverable | acceptance | hour ceiling + decision rule (§0.5) |
|---|---|---|---|---|
| R11.1 | **Track the harness CODE**, not its outputs | 33 files / 432 KB moved `\.scratch/mask-eval/` → `core/tests/fixtures/gold/harness/`. The ~2 GB of `ws/`, `diagnostics/`, `text/` stay machine-local behind `MASK_EVAL_DATA`, defaulting to `.scratch/mask-eval` and **raising with the path named** when absent | the three consumers run to **byte-identical output** with the untracked original **deleted** | 🟢 **DONE 2026-08-14.** ~1.5h |
| R11.2 | **Guard: tracked code may not IMPORT from `.scratch/`** | `core/tests/fixtures/gold/test_no_scratch_deps.py` — `sys.path` mutations found via `ast`, docstrings excluded, unparseable files fall back to regex rather than passing | exits 0; **injection-proven** | 🟢 **DONE 2026-08-14.** ~1h |
| R11.2a | **Disposition the 71 gitignored DATA references** | `audit_scratch_data_paths.py` — each reference resolved to (a) machine-local root made env-overridable **and raising**, (b) dead tree → R9.6, or (c) should be tracked → R11.1 | audit exits 0 | **OPEN. Ceiling 6h.** Below-baseline progress at 6h ⇒ **ALERT that the approach needs redesign** — the remainder is *not* accepted, and entries are **never** added to `SANCTIONED` to make the number fall |
| R11.3 | **`gen_dr_original`'s silent fallback → an explicit raise** | `_require()` names every path tried; resolution is **lazy** (PEP 562 module `__getattr__`) so importers wanting only slug lists are unaffected | `MADUEKE` raises; `import gen_dr_original` still succeeds | 🟢 **DONE 2026-08-14.** ~0.5h |
| R11.3a | **Pin the Sabates_A acquisition** | clone `janvier-s/original-douay-rheims` at a **recorded SHA** into a tracked location, or a tracked acquisition script that does | the SHA is in the repo; a fresh checkout can obtain the source without asking a person | **OPEN. Ceiling 3h.** If the upstream SHA cannot be established, **ALERT** — do not substitute "whatever HEAD is today", which would make the apparatus unreproducible |
| R11.4 | **Fold `purge_empty_ocr.py:23` into R9.6** | R9.6's module list named five restatements of the migrated root; this is a **sixth**, and it reaches the dead tree by relative traversal (`../../../../../.scratch/…`) rather than by naming it, which is why the original sweep missed it | `witness/test_project_root.py` covers it | **OPEN. Ceiling 1h** (it is one line, inside R9.6's ceiling) |
| R11.5 | **Reclaim the ~7 GB** | delete what is provably regenerable from `.scratch/` | **BLOCKED BY R11.1–R11.3 BY CONSTRUCTION** — see below | **OPEN, blocked.** No ceiling until unblocked |

### 🔴 R11.5 is ordered last, and the ordering IS the recommendation

The 7 GB is what makes the directory look like cleanup-fodder, and it is also what would have destroyed
the harness. **Until R11.1–R11.3 are done, deleting `.scratch/` is destructive in a way `git status`
cannot show**, because the thing at risk is invisible to git by definition. R11.1 and R11.3 are now done;
R11.2a still holds 71 references whose disposition is unknown, so **R11.5 stays blocked**.

### What R11.2 found that R11.2 was not looking for

Scoping the guard to `sys.path` was not the first design. The first version flagged **every** string
constant naming a `.scratch` path and reported **71 references across 38 tracked files** — twelve times
the blast radius the recommendation was written for. Those are not all defects: a 2 GB ingest cache and a
regenerable sqlite basis-db are legitimately machine-local. But some are R9.6 dead trees that
`mkdir(parents=True)` and **write** where nothing reads.

**Telling them apart requires reading each one, so a single pass/fail would have forced one of the two
things this project forbids** — a bulk rewrite nobody reasoned about, or a threshold weakened until it
passed. Split instead, on the R10.1 precedent:

* **`test_no_scratch_deps.py` — GUARD.** Executable dependency: importing code out of gitignored space.
  Unambiguously wrong, now **zero**, exit 0, injection-proven.
* **`audit_scratch_data_paths.py` — AUDIT.** Data references. **Exit 1 is the healthy state and the
  count must FALL** (baseline **71 refs / 38 files**, 2026-08-14).

⚠️ **The audit flagged ITSELF on first run** — its own detection regex is a `.scratch` string constant.
That is R9.2c's docstring defect one level up (*a check a comment can trip measures vocabulary, not call
sites*), and the two detectors are excluded by name. **Nothing else may be added to that exclusion**: a
count that falls by exemption rather than by disposition is the metric measuring the wrong thing again.

### 🔴 What R11.3 exposed: a source that was ALREADY resolving to a dead path

`MADUEKE = next((p for p in _MAD_CANDIDATES if p.exists()), _MAD_CANDIDATES[0])` returns **candidate[0]
when none of them exists**. Measured 2026-08-14: **both Madueke candidates are absent on this machine.**
So `MADUEKE.glob("*.html")` was iterating a nonexistent directory, yielding nothing, and the caller
emitted a book with **no Madueke scripture text while reporting success** — the authoritative verse
witness, silently absent.

**This is the same defect as R9.6's `detect_our_ocr` (`{"verses_scored": 0, "error": "no anchor text"}`
for every book) and as R9.6a's `MADB.exists()` degrading to an empty set.** Three sites, one shape: *a
missing source producing an empty result that is then reported as a clean one.* R1.4 and `_empty_because`
(§1.4) say a null needs its cause established; a candidate list with a silent tail-default is a machine
for erasing the cause.

⚠️ **`SRC` still resolves**, to `.scratch/original-douay-rheims`. It is a real read, and it is exactly
the kind of reference R11.3a must pin — the apparatus is currently reproducible only from an unpinned
clone on one disk.

---

## Verification standard for this roadmap

A step is **DONE** when its acceptance test runs and passes on demand — not when the code exists.
Every step above that is marked COMPLETE has a command that reproduces its result.

Run everything with the project interpreter — `../ocr-venv/bin/python` from `ocr-spike/`. The block below
was itself found stale on 2026-08-07 (it claimed `10/10` and listed none of the guards) and is now bound to
reality by `witness/test_verification_standard.py`, which parses this block and fails if a command named
here does not exist or if a count asserted here disagrees with what the command prints.

**Registry and structure** — all exit 0:

```
../ocr-venv/bin/python witness/witnesses.py             # registry: 12 records over 11 files
../ocr-venv/bin/python witness/make_witness_tree.py     # build + verify tree  -> 12/12 witnesses verified
../ocr-venv/bin/python witness/inventory_leaves.py      # full-corpus leaf inventory
../ocr-venv/bin/python witness/reconcile_counts.py      # leaf-count reconciliation, grouped BY SETTING
```

**The guards** — each carries a proven negative case; all exit 0:

```
../ocr-venv/bin/python witness/test_primacy_guard.py       # R0.5  a render-primary witness raises on pixel access
../ocr-venv/bin/python witness/test_setting_guard.py       # R8.2  cross-setting collation is REFUSED
../ocr-venv/bin/python witness/test_counts_vs_doc.py       # R8.2  §1.1 table agrees with the registry (12/12)
../ocr-venv/bin/python witness/test_setting_verified.py    # R8.4  no witness may lack setting readings
../ocr-venv/bin/python witness/test_raster_routing.py      # R7.5  ONE route to the pixels, and the guard is on it
../ocr-venv/bin/python witness/test_drop_rule_enforced.py  # R7.5a-3 a declared scoring drop must have a consumer
../ocr-venv/bin/python witness/test_verse_scope.py         # R9.3  Gate 0f: scope declared, and two consumers enforce it
../ocr-venv/bin/python witness/test_consensus_sources.py   # R9.4b the fusion admits only curated, verse-admitted sources
../ocr-venv/bin/python witness/test_raster_admissible.py   # R5.2b Gate 0d REFUSES a derivative leaf, and admits a real one
../ocr-venv/bin/python witness/test_verse_scope_bypass.py  # R9.2c Gate 0f has ONE route; each exemption still earns itself
../ocr-venv/bin/python witness/test_verification_standard.py  # this block agrees with reality
../../../../core/tests/fixtures/gold/test_no_scratch_deps.py  # R11.2 no tracked module imports code out of gitignored .scratch/
```

⚠️ The R11 guard and audit live under `core/tests/fixtures/gold/`, not `witness/`, because they scan
**every** tracked `.py` in the repo — the defect they prevent is not OCR-specific. Run them with the repo
`.venv`, not the OCR venv.

🔴 **KNOWN GAP, stated rather than papered over.** `test_verification_standard.py` parses only
`witness/`-prefixed commands, so it reports **19** and does **not** cover the two R11 entries above. They
are listed here and run manually. That is exactly the shape this block exists to prevent — a claim in a
document with nothing able to refuse it — so it is recorded as **R11.2b: extend the standard's parser to
repo-root-relative commands and their venv. Hour ceiling 2h; if the parser cannot be extended without
weakening its existing checks, ALERT rather than dropping the two entries from the block.**

**The audits** — these are *expected to fail while their step is open*, and that is the point:

```
../ocr-venv/bin/python witness/audit_gt_rasters.py      # R7: exits 1 -> 48 of 51 GT files inadmissible, 9 WRONG SETTING
../ocr-venv/bin/python witness/audit_s06_keys.py        # R7.5a-2: exits 1 -> 261 derived artefacts still keyed `jp2-S06`
../ocr-venv/bin/python witness/audit_prereq_ceilings.py # R10.1: exits 1 -> 17/46 OPEN steps carry a §0.5 ceiling; the fraction must RISE
../ocr-venv/bin/python witness/audit_setting_points.py  # R8.4b: exits 1 -> foot criteria proved at 1 separated point of the 3 §0.3 requires
./.venv/bin/python core/tests/fixtures/gold/audit_scratch_data_paths.py  # R11.2a: exits 1 -> 71 gitignored DATA refs across 38 tracked files; the number must FALL
```

A guard exiting 0 and an audit exiting 1 are both healthy states. An audit that exits 0 before its remedy
is done would mean the audit stopped looking, not that the corpus got better.

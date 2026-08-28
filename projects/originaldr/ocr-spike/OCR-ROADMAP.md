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
| R2 | Structural inventory — Gate 0b stage 2 | 🚨 **OPEN — R2.1f FIRED 2026-08-14, ALERT: THE APPROACH NEEDS REDESIGN.** R2.1c DONE (instrument promoted to TRACKED `witness/collation_read.py`, with signature/catchword as separate fields and stated abstain reasons). R2.1d'(A) measured **three** times: **0.222 → 0.312 → 0.312**, Wilson95 lower bound **0.142** against a 0.95 bar. **The ACCEPTANCE RULE fired, not a budget.** The catchword half reads at 0.87–1.00 and is correct; **every failure is on the head side**. 🔴 **The third run corrected the scorer defect and the rate DID NOT MOVE — which is the finding**: 3 of the 5 AGREEs are whole-line blobs passing the ≥4-char prefix rule, so the head reader fails in **both** directions and **0.312 is not a conservative floor but two opposing biases of unknown relative size** (R2.1f, 2026-08-15). 🟢 **REDESIGN DECIDED: option (1)**, first baseline via the running-head leading gap, built as a reusable region-typing primitive — see R2.1g. **R2.2 is promoted to the pivot** (R2.2a): it is the same head-band instrument and it also supplies a signature-independent component of R3.1's key, so **R2 and R3 interleave rather than sequence**. R2 continues to BLOCK Gate 0b/0c and all transcription. Prior state: R2.0 instrument built in `.scratch/r2/` (probe v18; design settled, dead ends measured), never scored on R2.1's original metric. Steps R2.1a–f written 2026-08-11; **R2.1g · R2.2a · R2.5 added 2026-08-17**; **R12 (layout typology) raised**. 🚨 **2026-08-25 — R2.2's APPROACH-LEVEL ALERT FIRED, R2.2 RE-SCOPED**: after four refuted span rules, R2.2o.1 measured that the gap populations OVERLAP (0.875 vs 1.525 pitches), so **no constant exists**, and `region_head`/`region_segments` are re-scoped from *the region model* to *the initialisation and plausibility clamp* of Masterplan §3.2 item 5 — characterised and willing to abstain, never maximised. Region typing moves to **R14, the adaptive visual agent (§3.0)**. ⚠️ The MN gap stays OPEN and R2 still BLOCKS Gate 0b/0c: a method redesign, never an accepted gap |
| R3 | Cross-source leaf mapping — Gate 0c | **OPEN.** Nothing built (R3.1–R3.4). **R3.6 · R3.7 raised 2026-08-17** — `F`-vs-`B`/`P` alignment with a named-leaf supply for OT1/OT2, and the 1633 NT matter as addenda. ⚠️ **R3.6's OT1 half is expected to return empty**: §1.2 already aligned `F` against `P` leaf for leaf (book block **1132 = 1132**, *"not one leaf of text"*), so the open OT1 work is `B`, which has only ever been attributed by count; OT2's live half is **R3.5b**, not a new audit |
| R3.5 | NT's 36-leaf difference | **DISSOLVED** — the number was malformed. R3.5b, R3.5c live |
| R4 | Bibliographic completion — Gate 0a residue | **PART.** R4.1d/R4.2/R4.3/R4.4 done; R4.1e, R4.2a, R4.5, R4.6 open |
| R5 | Raster policy — **Gate 0d** | 🟢 **BUILT AND ENFORCED on all three clauses, 2026-08-10** (R5.1 · R5.2a–c). R5.1's manifest is complete — **3,122 leaves, 0 rasters unmanifested**, so the dimension clause moved UNKNOWN→CHECKED on 3,113 leaves and the pre-registered deferral never fired. ⚠️ **3,113 of 3,122 is not 3,122, and the row said so only by arithmetic** (corrected 2026-08-17): **9 leaves carry no dimension check**. Which nine, and why, is **R5.3** — a residue named is a residue that can be closed; a residue left to subtraction is one that silently becomes "all" the next time this row is quoted. Determinism proven: a second full build is byte-identical. Previously read "R5.2 has no proven negative", which described a guard that runs; **none was ever written** |
| R6 | `S06` frontmatter/backmatter collation | **PART.** R6.1–R6.3a, R6.5 done; R6.3b/c, R6.4-remainder, R6.6a–d open |
| R7 | Ground truth read from inadmissible rasters | **OPEN — 48 of 51 files.** R7.5, R7.5a, R7.5a-3, R7.5b, R7.5c, R7.5d **DISCHARGED**; R7.1–R7.4 and **R7.5a-2** (**261** derived artefacts to regenerate, was 339) open |
| R8 | `F`'s New Testament is the 1633 edition | **PART.** R8.1, R8.2, R8.4, R8.4a, R8.5, R8.8 done; R8.3, R8.4b, R8.6, R8.7 open |
| R9 | Evidential scope per witness — Gate 0f | **PART.** R9.0–R9.4b done; the gate was **enforced but bypassable** until 2026-08-10 — **R9.2c DONE** (the 9 modules that read around the read path are converted; it exposed a containment fact read as a scoring permission, and a parity metric that was restating the best witness's pass rate) — **R9.5a** (companion table disagreed with the registry) open; 🟢 **R9.6 + R9.6a DONE 2026-08-14** — the root was restated in **20** modules, not five, and four of them WROTE into the dead tree; **R9.6b** raised (madueke-b's `merged.txt` is a pre-de-interleaving dump, refuted at 2.05%) |
| R10 | The constitution's own machinery — §0.5 | **PART.** 🟢 **R10.1 BUILT** — `witness/audit_prereq_ceilings.py` runs and reports **18/44** OPEN steps carrying a ceiling + rule (exit 1 = healthy; the fraction must RISE). 🟢 **29% → 40% on 2026-08-14** (`12/41` → `18/44`), again by the planning half: R11 and R9.6b arrived with their ceilings written before the work. 🔴 **R10.2 OPEN — nothing built**, `PROVISIONAL.md` does not exist. ⚠️ This row read "Nothing built" for both until 2026-08-11 while the audit was live and listed in the verification block below — and §0.5 named it as a *guard* called `test_prereq_ceilings.py`, which has never existed |
| R11 | Tracked code only one machine can run — §0.2 rule 6 | **PART, NEW 2026-08-14.** 🟢 **R11.1 DONE** — the gold suite's harness (33 files / 432 KB) is TRACKED at `core/tests/fixtures/gold/harness/`; the three consumers run **byte-identical with the untracked original deleted**. 🟢 **R11.2 GUARD BUILT** — `test_no_scratch_deps.py` exits 0, injection-proven. 🟢 **R11.3 DONE** — the silent candidate-fallback now raises, and it exposed `MADUEKE` **already resolving to a nonexistent path**, emitting books with no Madueke text while reporting success. 🔴 **R11.2a OPEN** — `audit_scratch_data_paths.py` exits 1 → **71 data references across 38 tracked files**, twelve times the blast radius the recommendation was written for. 🟢 **R11.3a + R11.4 DONE** — Sabates_A pinned at `0bf4218b` with per-tree content hashes, verified against the live remote. **R11.5 (reclaim ~7 GB) BLOCKED BY CONSTRUCTION** |

| R12 | Layout typology — the archetype census and classifier | **OPEN.** R12.1–R12.3, nothing built. ⚠️ **R16.1 is BLOCKED BY R12.1** — a per-archetype quota cannot be filled before the archetypes are enumerated, which makes R12.1 a prerequisite of §7.8 row 9 and therefore of **both** Gate 10a–10f and Gate 11 |
| R13 | The trained recogniser is not in the path that needs it | **OPEN.** R13.1 (wiring, ✅ **UNBLOCKED 2026-08-27c** — R2.1b selected `dr_v3_armB` on 7 class wins of 7) · R13.2 (the ſ-surface measurement) · **R13.3** (Gate 11's first measurement, **BLOCKED BY R16.1** and by R13.1). ⚠️ **The 0.9396 validation accuracy is not a Gate 11 measurement** and §7.8 refuses the substitution by name |
| R14 | **THE ADAPTIVE VISUAL AGENT** — Masterplan §3.0, GOVERNING | **PART.** 🟢 **R14.0 DONE 2026-08-25** — the first layout score ever computed on this corpus: Surya `FastLayoutPredictor` on the 121-entry head-band gold, overall **100/121**, RunningHead 20/20, MainText 80/80 (⚠️ **CONTAINMENT** — median bound box 0.5555 of the page, Gate 10b unmeasured), **MarginNote 0/19**. The MN entries bind to **tight** boxes (0.0039 of page area), so the detector **localises** the notes and lacks only a **name** ⇒ R14.1 redirected from *train a detector* to *class-inventory fine-tune*. 🟢 **R14.6a DONE 2026-08-26** — every region class now has an admissible label source (janvier: **3,754** verse-anchored side-notes, 53 books, CC0, this edition), and the audit's own first run reported a **false absence** by searching one directory. 🔴 **OPEN**: R14.1–R14.5 · **R14.6b** (ingest; ✅ is a RE-SCOPE, not a discharge) · R14.6c. **S2, S4, S5, S8 still have no code** |
| R15 | ONE GATE REGISTER, and it must be READ | 🟢 **COMPLETE 2026-08-26** (R15.1 · R15.2 · R15.3). `witness/audit_gate_register.py` binds §7.8 to §3.2's clauses and to this file's step ids; `--selftest` replays the **pre-fix** documents and reproduces all three 2026-08-25 findings, which is the only available proof that an audit written after a hand-repair would have caught it. Live: exit 1, **0 hard defects**, **12/25** rows discharged, **13** NOT YET PLANNED. ⚠️ Its first live run found **two more**: `Gate 0e` and `Gate 0f` had **no row in the register declared canonical** (added), and one crosswalk cell read `row 3` where the rest read `10a` (normalised) |
| R16 | The four unowned §7.8 gate rows | **OPEN, NEW 2026-08-26, nothing built.** R16.1 (freeze GOLD-LAYOUT/GOLD-TEXT — §7.8 row 9, the blocker under **both** models) · R16.2 (residue detector, row 2) · R16.3 (archaic typeset census, row 3 / Gate 4.1) · R16.4 (drop-cap board fix, row 1). 🔴 **Three of the four are low-to-medium complexity with no prerequisite but the corpus**, and had no step for the life of the project |

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

⚠️ **Every OPEN step must carry a COMPLEXITY CLASS, a candidate list, and a pre-registered decision rule**
(§0.5). That requirement was in the constitution from the start and **no step had ever carried either**,
which is why R2 and R3 — the two sections gating everything downstream — stood at "NEXT, nothing built"
indefinitely. Ceilings are being added section by section as each is next touched;
`witness/audit_prereq_ceilings.py` **reports** (exit 1, healthy) the OPEN steps with neither — it is an
**audit, not a guard**, for the reason spelled out in R10.1, and this paragraph named a nonexistent
`test_prereq_ceilings.py` until 2026-08-11. **A ceiling escalates and never closes a step**: reaching it
raises an ALERT that the *approach* needs redesign, which is the opposite of accepting a lowered result.

### 🔴 HOURS ARE ABOLISHED AS A UNIT (Sir's instruction, 2026-08-17)

**No step, phase or estimate in this project is denominated in hours** — not the analyst's, not mine, not a
script's wall-clock. Every former hour ceiling is restated as a **complexity class** plus a **candidate
list**. The escalation semantics of §0.5 are **unchanged in every respect**: a below-bar result stays
**OPEN**, still **blocks**, and still **ALERTS that the approach needs redesign**. Only the unit changes.

**Why the unit was wrong, stated so it is not reintroduced.** An hour ceiling measures the wrong quantity
twice over. It invites a spent budget to be read as a licence to stop — the exact laundering §0.5 exists to
prevent, and R2 has already had to write "**the ceiling did NOT fire, the ACCEPTANCE RULE did**" to hold
the line. And it ranks a cheap path above a dear one when the cheap path carries nothing forward, which is
how R2's option (2) nearly got taken (R2.1g). **Complexity is the decision-relevant quantity: what has to
be designed, what is unknown, how many parts interact, and what could invalidate the approach.**

| class | meaning | what "done" requires | what failure means |
|---|---|---|---|
| **C1 — mechanical** | the method is known and already proven **on this data**; only application remains | the application, and a guard that would catch its absence | a bug, fixed in place — not an approach question |
| **C2 — assembly** | the parts are known, the composition is new; the unknowns live in how they interact | the composition, plus the interaction that was NOT obvious stated in the record | one named part is wrong; re-class that part, not the step |
| **C3 — instrument design** | a new measurement must be designed, and its **negative control** established before any number it produces means anything | the instrument, the control, and the refutation the control makes possible | the instrument is refuted; the step re-opens at C3 with the refuted candidate struck |
| **C4 — open problem** | no method in hand is known to reach the bar | first deliverable is a **candidate method plus the test that would refute it** — never an attempt | the candidate list is exhausted ⇒ ALERT, and escalation must name a **different resource class** (§7.7) |

**The trigger that replaces the ceiling is CANDIDATE EXHAUSTION, and it is strictly better.** Each step
names its candidate approaches **before work starts**; when every candidate is refuted **by measurement**,
the step ALERTS. This is evidence-driven where an hour count was arbitrary, and it cannot be satisfied by
waiting: an unrefuted candidate keeps the step live no matter how long it has been open, and a refuted one
closes off no matter how quickly it fell. ⚠️ **A candidate may be struck only by a measurement with a
negative control** (R2.1d″ is the standing precedent — it was the control that refuted image correlation,
and without it the run reported "continuity confirmed").

⚠️ **`witness/audit_prereq_ceilings.py` PARSES this file for hour ceilings and will now under-report.**
That is a live defect the moment this section lands, not a cosmetic one — the audit is R10.1's only
instrument and it would silently score every restated step as *carrying nothing*. Raised as **R10.3**; the
audit is not to be deleted or its threshold relaxed in the interim, and its exit-1 count is **not citable**
until R10.3 lands.

⚠️ **Machine throughput is not exempt but it is not the same thing either.** Where a per-leaf cost is the
*evidence* for rejecting a method (R2.0 rejected `blla.segment` on it), state the **per-unit cost and the
ratio to the alternative** — a fact about the method — never a projected total against a budget.

**OPEN** — R2.1 (R2.1a · R2.1c · R2.1d · R2.1e · R2.1f · **R2.1h** · **R2.1k**) · **R2.2** · **R2.2a** · **R2.2b** · **R2.2c** (BLOCKING) · **R2.2d** · **R2.2e** · **R2.2f** (NEW) · **R2.2g** (NEW) · **R2.2h** (NEW) · **R2.2i** (NEW) · **R2.2j** (NEW) · **R2.2k** (NEW) · **R2.2m** (NEW) · **R11.2d** (NEW) · R2.3 · R2.4 · **R2.5** · R3.1 · R3.2 · R3.3 · R3.4 · R3.5b · R3.5c · **R3.6** · **R3.7** · R4.1e · R4.2a · R4.5 ·
**R4.7** · **R5.3** · R6.3b · R6.3c · R6.4-remainder (OT2/1610 prelims,
endmatter Tables, body rewording) · R6.6a · R6.6b · R6.6c · R6.6d · R7.1 · R7.2 (1 of 4 done) · R7.3 · R7.4 ·
**R7.5a-2** (**261** artefacts, was 339) · R8.3 · **R8.4b** · R8.6 · R8.7 · **R9.5a** · **R9.6** ·
**R9.6b** · **R9.8** · **R10.1** · **R10.2** · **R10.3** · **R11.2a** · **R11.2b** · **R11.2c** (NEW) · **R11.5** (blocked) ·
**R12.1 · R12.2 · R12.3** (layout typology, NEW) · **R13.1 · R13.2** (the recogniser is not in the path, NEW) ·
**R2.2n · R2.2o · R2.2o.1b · R2.2o.2 · R2.2o.3 · R2.2o.4** (filed 2026-08-25, see the register note below) ·
**R14.1 · R14.2 · R14.3 · R14.4 · R14.5 · R14.6 · R14.6b · R14.6c** (THE ADAPTIVE VISUAL AGENT, NEW — Masterplan §3.0) ·
**R14.6b · R14.6c** (filed 2026-08-25 by the label-source audit: Marginalia has NO admissible source) ·
**R13.3** (Gate 11 has never had a step, NEW) ·
**R13.1a** (the recogniser's provenance mechanism is proven but no consumer imports it — the attesting-arm conversion, NEW 2026-08-27d) ·
**R16.1 · R16.2 · R16.3 · R16.4** (the four unowned §7.8 gate rows the crosswalk audit made visible,
NEW 2026-08-26 — GOLD frozen · residue detector · archaic typeset census · drop-cap board fix) ·
**R14.10b · R14.10c** (the class inventory is smaller than the page — PageNumber · Annotation, NEW 2026-08-27) ·
**R14.10d** (the foot band's signature/catchword split is one position test and leaf 411 prints both, NEW 2026-08-27 — found by DRAWING the leaf, not by reading a number) ·
**R11.2f** (the verification standard's guard inventory is a `test_*.py` glob, so it cannot notice a new scorer — a false absence in the CHECKER, NEW 2026-08-27. **C2 — assembly**) ·
**R14.11 · R14.12 · R14.13** (no fixed measure may DECIDE — 5 of 12 did, **3 of 12 now** · the LAMINATION, 99 overlapping box pairs on 20 leaves · the full-leaf gold review, NEW 2026-08-27 — each row carries its own complexity class) ·
**R14.14 · R14.15 · R14.16 · R14.17 · R14.18** (the agent has NO ANGLE and a horizontal head line cuts 41 boxes · the DETECTION FLOOR, classes smaller than any box · LECTOR is a decision procedure not a model · the review toolkit · gold expansion to 188 leaves, NEW 2026-08-27 — each row carries its own complexity class)

🔴 **NEW OPEN STEPS RAISED 2026-08-17, each from a finding rather than from a plan review.** **R2.1g**
(head-side redesign, option 1) · **R2.2a** (head-band region primitive — the R2/R3 interleave pivot) ·
**R2.5** (multi-signal collation) · **R4.7** (the §10 citation that has never had an id) · **R5.3** (the
9-leaf dimension residue) · **R10.3** (the ceiling audit must parse complexity classes) · **R12** (layout
typology) · **R13** (the trained recogniser is absent from the path that needs it).

🔴 **THE REGISTER ABOVE IS STALE, AND `audit_prereq_ceilings` IS THEREFORE AUDITING A POPULATION THAT
EXCLUDES THIS MONTH'S WORK — found 2026-08-25.** The register is HAND-MAINTAINED and stops at
**R2.2m**. `audit_prereq_ceilings` derives its whole denominator from it (`OPEN_BLOCK`), so
**R2.2n · R2.2o · R2.2o.1 · R2.2o.1b · R2.2o.2 · R2.2o.3 · R2.2o.4** — every step raised since 08-22,
i.e. the steps the project has actually been working on — return **0 hits** in the audit and are
covered by nothing. The `1/72` claim is NOT stale, because the register never grew; that is precisely
the failure. An audit whose denominator only moves when someone remembers to edit a prose list will
report health for exactly the steps nobody filed.

✅ **FIXED THE SAME DAY, as a DELIBERATE denominator move.** The six R2.2n/R2.2o steps and the seven
R14 steps were filed, taking the register **72 → 81** and the claim **1/72 → 8/81**. The numerator rose
because R14 was filed *properly* — a section-level pre-registered decision rule plus a complexity class
in every row — rather than added bare; **the uncovered count held at 38, so filing 13 steps added no
ceiling debt.** The audit's published claim was re-measured and rewritten, never estimated. ⚠️ **Same shape as this
project's signature defect** — a correct rule that nothing reads — with the twist that here the rule
reads a list, and the list is the thing that decayed. **See R10.3**, which already asks the ceiling
audit to parse classes; this says the audit must also derive its register from the document rather
than from a curated copy of it.

### 🔴 Ledger review 2026-08-17 — what the status column was rounding up

**Every row below was readable as more closed than it is.** None of these is a new failure; each is a
status line that lost a qualifier. They are recorded here because the §0.6 precedence rule makes this
register the thing that must be right.

| carried as | actually | consequence |
|---|---|---|
| Gate 0d **"BUILT AND ENFORCED on all three clauses"** | the dimension clause is checked on **3,113 of 3,122** leaves | **R5.3** raised. "All three clauses" is true of the *guard*, not of the *coverage* |
| Gate 0e **enforced** (R6) | R6 is **PART** — R6.3b, R6.3c, **R6.4-remainder (the OT2/1610 prelims, which are not yet located)** and R6.6a–d are open | §2 requires 0e **before** 0b and 0c *"since 0b's collation and 0c's leaf map are both statements about a particular setting"*. **An OT2 collation rests on an OT2 setting proof that is outstanding** |
| Gate 0f **PART** | R9.5a (companion table vs registry) and R9.6b (five consumers on an interleaved dump) open | unchanged, but the two are of different kinds: R9.5a is a disagreement, R9.6b is **five consumers reading a source of unknown fitness** |
| R7.5a-2 **open** | **not started, deliberately** — the 261 artefacts come from many different generators (coverage audits, consensus, QC probes), not one command | the next action is a **producer-per-artefact survey**, then regenerate — **never edit** (R7.5d). Launching an unmapped bulk regeneration would be a blind write over derived evidence |
| R11.2a **"71 references across 38 files"** | **33 references across 23 files** after R11.2a's first pass | the row understates the progress and overstates the remainder — the opposite of the usual drift, and still a stale number |
| **R11.2f** (NEW 2026-08-27f) | 🔴 **the standard's guard inventory is `GUARD_GLOB = "test_*.py"`, so it STRUCTURALLY CANNOT NOTICE A NEW SCORER.** `witness/score_pagenumber_agent.py` and `witness/build_reading_record.py` were added and the standard reported no gap; its own rule 3 says *"the block names every guard that exists — so adding a guard and forgetting to document it is caught"*, and that holds for `test_*.py` alone | **a fourth false absence of the same shape**, and this one is in the CHECKER: `audit_label_sources.py` bounded by a directory, then by a field name, R14.10b's own probe bounded by a band, and now the standard bounded by a filename glob. ⚠️ Filed rather than fixed inline for the reason already standing over the `CEILING_RE` gap — changing this parser changes the instrument every other number in the block is verified by, and it earns its own step. **C2 — assembly** |
| R11.2b | the verification standard parses only **`witness/`-prefixed** commands, so the **repo-root R11 entries sit in the block uncovered** | a verification block that silently skips entries is worse than one that omits them |
| — (unrecorded anywhere) | 🔴 **the repo declares pre-commit hooks that are NOT installed**: `.pre-commit-config.yaml` runs ruff over `^core/`, and `.git/hooks/` holds only samples. A manual run gives **24 unfixable ruff errors + a 429-line reformat** | a declared-but-absent hook is the Gate 0d shape again — **a rule with nothing implementing it**. Raised for Sir; not silently fixed, because the reformat is a decision about the codebase, not a lint |
| — (unrecorded anywhere) | ⚠️ the verification standard now **runs** `r2_1d_continuity.py`, so the block performs OCR and **will exceed a 120 s limit** | a standard that times out is a standard that gets skipped. 🔴 **PREDICTION CONFIRMED AND NOW OWNED, 2026-08-26: the full suite was launched twice and did not complete in over 15 minutes either time**, so the block could not be run end-to-end to verify the day's own registration. The entry was verified instead by driving the suite's own `commands()` parser and `run()` directly on the one line — parsed once, flagged as an audit, first fraction `12/25`, exit 1, fraction present in output — which is the right fallback and is **not** the same thing as the suite passing. Filed as **R11.2e**; until it lands, every claim in the block is verified by a standard nobody can afford to run |
| **R2.2c** and **R2.1k** carried as OPEN *in their own sections* | 🔴 **neither was in the OPEN register at all** (found 2026-08-18) — R2.2c is the step that BLOCKS every region number transferring to the reader, and the register is what §0.6 makes precedence-bearing | **the signature defect one level up**: a correct rule (the section) that the thing which reads the register never sees. Both added. ⚠️ `test_open_register_consistency` cannot catch this — it checks that a **closed** step is absent from the register, never that an **open** one is present, so the register can silently under-report forever. That converse check is **R11.2c**'s neighbour and is named here so it is not lost |

**DONE** — R0.1–R0.5 · R1.1–R1.6 · **R2.2l** (2026-08-21, the sixth sink; guard exit 0) · R4.1d · R4.2 · R4.3 · R4.4 · R6.1 · R6.2 · R6.3 · R6.3a · R6.4 (tome 1) ·
R6.5 · **R7.5** · **R7.5a** · **R7.5a-3** · **R7.5b** · **R7.5c** · **R7.5d** · R8.1 · R8.2 · R8.4 · **R8.4a** · R8.5 · **R8.8** · **R9.0** · **R9.1** · **R9.2** · **R9.2a** · **R9.2b** · **R9.3** · **R9.4** · **R9.4a** · **R9.4b** · **R9.2c** (with R9.2c-1…-4) · **R5.1** · **R5.2a** · **R5.2b** · **R5.2c** ·
**R14.0** (2026-08-25) · **R14.6a** (2026-08-26) · **R15.1 · R15.2 · R15.3** (2026-08-26) ·
**R9.7 · R11.2e** (2026-08-26) · **R14.1 · R14.2 · R14.7 · R14.8 · R14.9** (2026-08-27)

⚠️ **R14.6b IS NOT ON THAT LIST, DELIBERATELY.** Its row carries a ✅ for being **RE-SCOPED** — from
*"scrape the corpus"* to *"ingest the corpora already on disk"* — and a re-scope is a change to the
step, **never a discharge of it**. The deliverable (ingest `janvier` and the odr-com apparatus as
`apparatus_blocks` with `kind='annotation'`, pinned under R11.3a) has not been shown done, so the step
stays **OPEN**. A green tick on a re-scope reading as a completion is exactly the shape §0.5 forbids,
and it was one edit away from happening here.

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

**Complexity: C3 — instrument design** (restated from a 12h ceiling, 2026-08-17; see *Hours are abolished*
above). Target: a first end-to-end R2.1→R2.4 pass on ONE volume (`OT1-1609-B`). **Decision rule,
pre-registered, written before the work starts and unchanged in force:**
- The reader does **not** get a lowered target if it cannot reach its bar. The band is re-cut **once**
  (R8.4a proved the foot band is the hard part and cost four failed designs), and if that fails the step
  **ALERTS that the approach needs redesign** — hand-reading a stratified sample to establish the collation
  is the fallback *method*, not a lowered *bar*.
- Abstention is not failure: a reader that abstains on 8% and is right on 92% passes; a reader that emits
  92% correct and 8% confident-wrong **fails**, because the collation cannot detect the difference.
- 🔴 **The escalation exists to force a start, not to license a stop.** §0.5 names *unstartability* as
  producing the same observable outcome as preserving the status quo, and R2 has been marked **NEXT** since
  the roadmap was written without a line of code — which is that failure mode, in this file, uncaught for
  the whole life of the project. **An exhausted candidate list escalates; it never closes the step.**

**Candidate list for R2.1's metric, and its state.** This is the thing that fires the escalation now:

| candidate | class | state |
|---|---|---|
| signature parsed per recto | C3 | 🔴 **REFUTED — unsatisfiable by construction** (R2.1-CRIT) |
| catchword continuity as TEXT | C3 | 🔴 **BELOW BAR at 0.312**, and the instrument is refuted in both directions (R2.1f) |
| catchword continuity by IMAGE | C3 | 🔴 **REFUTED by its own negative control** (R2.1d″) |
| signature-sequence monotonicity | C2 | 🟡 **LIVE, unrefuted** — reads only signatures, needs no gold set |
| **multi-signal collation** | C3 | 🟢 **NEW, LIVE — R2.5.** Ten signals of differing coverage and differing failure modes |

⚠️ **The list is not exhausted, so R2 does not escalate past ALERT** — two candidates are live and neither
has been measured. R2.1f fired on *the catchword instrument*, which is a candidate, not on R2.

### R2.0 — Direction-line instrument: STARTED 2026-08-10/11 (C3)

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

**Measured and rejected, do not re-walk:** `blla.segment` on a band (**21.7 s and 37.5 s per leaf, measured**
— a per-leaf cost that does not survive multiplication by a 1,160-leaf volume, let alone a 3,122-leaf corpus;
⚠️ restated 2026-08-17 from a projected total against an hour budget. The per-leaf cost is the evidence and is
a property of the method; the ratio to the component-and-gap route was never measured and is **not** claimed
here); `FOOT_BELOW_PITCHES=8.0` (a longer tail reaches the leaf edge and 3 leaves collapse to a
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

### 🚨 R2.1f HAS FIRED — ALERT: THE APPROACH NEEDS REDESIGN (2026-08-14)

**This is an ALERT, not an acceptance.** R2 stays OPEN and continues to block Gate 0b stage 2,
R3, and all transcription. Nothing below lowers the bar, and no result is being recorded as
"good enough" (§0.5, and the No-Silent-Degradation rule).

**The pre-registered rule ran exactly as written.** R2.1f: *"Below ⇒ band re-cut ONCE, then ALERT
that the approach needs redesign."* The one permitted re-cut was made and measured:

| run | instrument | agreement | Wilson95 lower | bar |
|---|---|---|---|---|
| 2026-08-11 | `.scratch/r2/r2_1d_continuity.py` (gitignored probe) | 0.222 (4/18) | 0.090 | 0.95 |
| 2026-08-14 | `witness/collation_read.py` (tracked, word gap re-cut) | **0.312 (5/16)** | **0.142** | 0.95 |
| 2026-08-15 | same, **scorer defect 2 corrected** (multi-word catchwords) | **0.312 (5/16)** | **0.142** | 0.95 |

⚠️ **The ACCEPTANCE RULE fired, and no budget was involved.** The distinction mattered when this
read "the ceiling did NOT fire" and it matters more now that hours are abolished as a unit: what
forbids a second re-cut is R2.1f's own text, not an exhausted allowance.

#### 🔴 THE THIRD RUN IS THE IMPORTANT ONE, AND IT MOVED NOTHING (2026-08-15)

Defect 2 below — a catchword can be more than one word — was corrected properly: `read_first_words(model,
leaf, k)` now returns **k** head tokens, **k is taken from the FOOT side** (`len(norm_words(catchword))`),
and a row offering fewer than k tokens **abstains** rather than short-reading. **The rate did not move.**

The defect was real and load-bearing on **exactly one pair**, which fails anyway for an honest reason:
`414→415` corrected reads `'of flowre'` against `'of fowre'` — `offlowre` vs `offowre`, a dropped `l`, a
genuine recogniser error. **What the null bought is the thing worth having**: 0.312 is now the *honest*
rate for this instrument rather than a number "depressed by an unknown amount".

🔴 **AND IT EXPOSED A SECOND, OPPOSITE DEFECT NOBODY HAD RECORDED. Three of the five AGREEs are earned
against whole-line blobs, not first words:**

```
400->401  catch 'face'     first 'faceof the earth, ſit tinga'          AGREE
403->404  catch 'Returne'  first 'Returne to Balac and thus thou shalt' AGREE
408->409  catch 'familie'  first 'familie of the Machitites'            AGREE
```

The `len(spans) < 2` guard **passes** — the row does split — but `spans[0]` is still multi-word, and the
**≥4-character prefix rule in `agrees()`** then counts any line that merely *begins with* the catchword as
agreement. The word-gap re-cut cleared the guard without yielding a word.

⚠️ **CONSEQUENCE, and it is the load-bearing sentence of this whole section: 0.312 IS NOT A CONSERVATIVE
FLOOR.** The head reader fails in **both** directions at once — it misses lines (deflating the rate) *and*
over-matches whole lines when it hits (inflating it). The observed rate is **two opposing biases of unknown
relative size**, and the true value is not bounded by it in either direction. Every prior sentence in this
file that treated 0.312 as a lower bound on the catchword approach is superseded.

🟢 **This is why a fix that changes no number is still worth running.** A single scalar hid two defects
pulling opposite ways; only correcting one of them and watching the scalar *not* move made the other
visible. Filed with the R7.5a dead-metric lesson: a metric that produces a plausible number is not thereby
measuring the thing, and one that survives a real fix unchanged is wearing the strongest available disguise.

#### 🟢 R2.1g — THE REDESIGN IS DECIDED: OPTION (1), AND THE REASON IS THE CARRY-FORWARD (2026-08-17)

Both options below close the head-side defect. They differ entirely in **what survives afterwards**, and
that — not cost — is the deciding criterion.

| | option (2) — character window | option (1) — first baseline ✅ **TAKEN** |
|---|---|---|
| mechanism | compare the catchword against the first *n* **characters** of the next leaf's text block | find the first **baseline** via the running-head leading gap, then read the first word from it |
| effect on the defect | **deletes** the head tokeniser from the measurement path | **fixes** the RunningHead/MainText separation the tokeniser is failing on |
| complexity | C2 — assembly | C3 — instrument design |
| carries into Gate 9 | 🔴 **nothing.** Routes *around* the layout defect to make a gate metric pass | 🟢 **a region primitive.** RunningHead/MainText separation is a Gate 9 region class |

⚠️ **Option (2) was the earlier recommendation in this file and it was wrong.** It is cheaper, and under an
hour ceiling that made it look correct — which is one of the two reasons hours are now abolished. It would
have closed R2 while leaving the running-head confusion entirely untouched, and that confusion is the
**documented cause of the recogniser's surface-score collapse** (`RUNG-PIPELINE-STATUS-2026-07-21.md`:
*"the recogniser emits running-header/marginalia the gold body excludes; that is Rung-1's layout-separation
job"* — genesis-24 content **0.9448** against surface **0.451**). The cheap path routed around the single
highest-value defect in the corpus.

| # | step | deliverable | acceptance |
|---|---|---|---|
| R2.1g | **Head-side redesign, option (1)** — and built as a **reusable region-typing primitive**, not a probe local to `collation_read.py` | a RunningHead/MainText separator taking the leading gap as its signal, exposed so R2.2, R12 and the Gate 9 region model consume the same one; re-measured on the SAME window (leaves 400–419) so the number is directly comparable to 0.312 | the separator is scored **on RunningHead/MainText assignment**, not only through the continuity rate it enables — a component that is only ever measured through a downstream metric cannot be debugged when that metric moves. ⚠️ **No second band re-cut**: R2.1f pre-registered exactly one and it is spent. **C3** |

##### 🟢 R2.1g EXECUTED 2026-08-17 — the primitive PASSES, and it FALSIFIED ITS OWN STATED MECHANISM

⚠️ **Option (1) was pre-registered as "find the first baseline via the RUNNING-HEAD LEADING GAP".
That mechanism is falsified on the FIRST leaf of the window.** Leaf 400's running head sits at
ext=0.95 of the measure with a lead of **40.0px to the body — exactly the body pitch**. There is no
gap to find. Leaf 403's running head *does* carry a 52px lead. So the signal is present on some
leaves and absent on others, and an instrument resting on it would fail **silently** on the leaves
where it is absent — returning a body line rather than abstaining. The redesign was executed on two
signals that are properties of the EDITION rather than of the error, per the anti-circularity rule:

1. **The setting is justified.** Body lines are flush to a left AND a right edge that dozens of
   lines share; a running head is centred and reaches neither. The measure is therefore the **MODE**
   of line edges, and "is this a body line" becomes "does it reach the measure".
2. **The head of the page is a HEADLINE BAND, not a line** — running head flanked by side-notes
   (leaf 400: `NVMERI` + `Og Alaine. Bal-`; leaf 410: `NVMERE.` + `Leuites n`). A row is **not
   homogeneous**, so region typing here is per **TOKEN**. A row-level separator cannot express it.

🔴 **THE 411→412 FAILURE WAS MIS-DIAGNOSED IN THIS FILE AND IN R2.1f.** It is recorded as `Cades`
vs `'Temporal'` = *"a RUNNING HEAD"*. It is **not**. Leaf 412's body row reads
`aTemporal | Cades of the deſert Sin | To whom Moyſes anſwered` — `Temporal` is a **MARGINAL NOTE**
sharing a baseline with the body line, and the true answer `Cades` is the very next token. The cause
is measurable: `text_measure` takes rows wider than `0.75 × max(extent)`, so a row carrying a
side-note **inflates the maximum and drags the left edge outward**. Leaves 400 and 410 measure
L=215 and L=248; **leaf 412 measures L=40**. With the measure widened the note falls inside it,
`in_measure` cannot exclude it, and it is read as the first word. **The head-side defect is a
MEASURE-CONTAMINATION defect**, fixed by a statistic a side-note cannot move — a mode, not a max.

**Deliverable, tracked.** `witness/region_head.py` (RunningHead · MarginNote · MainText ·
ChapterHead, per token, rules R1–R7 pre-registered in the module before it was scored) ·
`witness/score_head_regions.py` · `witness/gold/head_regions_OT1-1609-B_400-419.json` (121 tokens
hand-labelled **from what each token SAYS, never from where it sits** — `NVMERI` is the book's name;
4 genuinely ambiguous tokens are excluded **with stated reasons** rather than silently labelled).

| region assignment, leaves 400–419 | value |
|---|---|
| **instrument** | **0.8760** |
| ALL-MT control (majority-class floor) | 0.6612 |
| ROW0-RH control (*the rule a reader would write unaided*) | 0.8017 |
| **RunningHead recall** | **1.0000 (20/20)** — bar 0.90 ✅ |
| MarginNote recall | 0.8947 (17/19) — bar 0.75 ✅ |
| MainText recall | 0.8375 (67/80) |
| leaves abstained | 0 |

**Both controls are reported and neither is optional.** A region accuracy alone means nothing on a
set dominated by MainText; the instrument had to beat *"row 0 is the running head"* to have earned
its complexity, and it does.

##### 🔴 BUT THE CONTINUITY RATE DID NOT RISE — AND THAT IS THE MORE USEFUL RESULT

| head reader | agreement | Wilson95 lower | note |
|---|---|---|---|
| `legacy` (the reader that scored 0.312) | **0.312** (5/16) | 0.142 | reproduced EXACTLY after refactor — the control that makes the rest comparable |
| `typed` (region primitive, **frozen band**) | **0.176** (3/17) | 0.062 | 🔴 **WORSE** |
| `typed-anchored` (⚠️ **DIAGNOSTIC ONLY**, band moved too) | 0.250 (4/16) | 0.102 | not comparable to 0.312 — changes two things at once |

⚠️ **A redesign that made the number WORSE is the `chapter_model_derive` shape, and it was caught by
the consumer rather than by the region score** — the sixth-instance pattern again, a rule only
tested once something reads it. Two causes, one mine:

* **A tolerance bug.** `in_block` used `0.35p` while the flush test used `max(0.35p, 0.03·measure)`
  — two tolerances for ONE edge. A body line starting slightly left of the modal `L` was *flush* by
  one test and *outside the block* by the other, so its opening token was labelled MarginNote and
  the reader fell through to an interior word (`'nes I ma'`). Fixed; region accuracy 0.8678→0.8760.
* 🔴 **A methodological error of mine: I scored the primitive on a `0.0–0.35h` band and deployed it
  on the frozen `0.06–0.30h` band.** Row indices and the measure differ between them, so the thing
  validated was not the thing run. **Recorded rather than quietly re-scored.**

**The frozen bound was NOT crossed to make the number better.** R2.1f pre-registered exactly one
band re-cut and it is spent; `head_band(frac=…)` exists solely to run the R2.2b diagnostic and is
labelled at every point it prints or writes. **Reporting both numbers is the non-laundering move;
adopting the anchored one silently would have been the laundering one.**

🟢 **What R2.1g genuinely bought is ATTRIBUTION, which is what R2.1f said was missing.** The joint
metric now decomposes into named, separately-owned causes: the unanchored band (**R2.2b**),
whole-line token blobs (**R2.1h**), catchword-side misreads (`'Abiton'` for *Abiron*, `'wl'` for
*whom*), and residual region misses (leaf 412's `Temporal` is still labelled MainText). Before
R2.1g the 0.312 was, in this file's own words, *"two opposing biases of unknown relative size"*.

| # | step | deliverable | acceptance |
|---|---|---|---|
| R2.1h | 🔴 **THE HEAD TOKENISER STILL RETURNS WHOLE LINES ON SOME ROWS** (measured 2026-08-17) | `_tokens_in_row` splits leaf 415's row into 10 clean words but leaves leaf 414's as ONE 37-glyph token — `'two, † euerie lambe the tenth part of a tenth, which to.'`. ⚠️ **This is the defect R2.1f named and it is NOT fixed**: *"3 of the 5 AGREEs are whole-line blobs passing the ≥4-char prefix rule"*. The 2-means word gap fixed it on the rows it fires on and is inert on the rest | split scored **per row against hand-counted word counts**, not through the continuity rate; and the ≥4-char prefix rule re-examined, since it is what lets a blob score as an agreement. ⚠️ A blob that AGREES and a blob that DISAGREES are the two opposing biases — fixing one alone moves the rate in an uninterpretable direction. **C3** |

##### 🟡 R2.1h WORKED 2026-08-17 — the BLOB is GONE, the step STAYS OPEN, and the ceiling is NOT the print

**Cause, measured and exact.** `_word_gap` ran a 1-D 2-means on ONE ROW's gaps. That row's gaps have
**three** scales, not two — intra-word (0–5px), word space (8–25px), and a single run out to a
marginal note (60–350px). With two clusters for three populations the lone region run captures the
high cluster and **every word space collapses into the low one**, so the threshold lands above every
real space and the line survives as one token. Leaf 414 row 1: threshold **38px** against word
spaces of 8–16. Leaf 400 row 1: **92px** against 10–17. The blob was a consequence of `k=2`.

| leaf.row | word spaces | region run | threshold | tokens |
|---|---|---|---|---|
| 414.1 | 8–16 | **72** | 38 | 2 🔴 |
| 400.1 | 10–17 | **179** | 92 | 2 🔴 |
| 415.2 | 8–15 | *none* | 6 | 10 🟢 |

**Deliverable, tracked.** `witness/gold/head_wordcounts_OT1-1609-B_400-419.json` (32 rows, counts
**hand-adjudicated**, basis stated: each row read as ONE crop by the recogniser — a *different*
instrument from the splitter under test — then adjudicated against the per-token readings, because
neither is authoritative. On 415.2 the whole-row read dropped `of flowre` entirely while the tokens
recovered it; on 414.0 the whole-row read missed the side-note. A gold built on either alone is
wrong in opposite directions) · `witness/score_head_tokens.py` · `witness/audit_prefix_rule.py`.

| splitter, 32 gold rows | exact | MAE | blob |
|---|---|---|---|
| ONE-TOKEN control | 0.0938 | 5.97 | 0.6250 |
| LEGACY-GAP control (pre-R2.1f rule) | 0.2812 | 4.78 | 0.3750 |
| PER-ROW-2M (**what R2.1f shipped**) | 0.2812 | 3.50 | 0.2500 |
| LEAF-POOLED (gaps pooled over the band) | **0.3125** | 2.56 | **0.0000** |
| QUANTILE (per-row, Q=0.80) | 0.2500 | **1.44** | **0.0000** |
| ⚠️ **ORACLE** — best threshold chosen WITH the gold | **0.8750** | **0.12** | 0.0000 |

🔴 **R2.1f's word-gap fix bought less than it appeared to**: PER-ROW-2M matches the rule it replaced
on exact accuracy (0.2812 = 0.2812) and beats it only on MAE. That was never measured at the time
because the only number available was the joint continuity rate.

🟢 **THE ORACLE IS THE RESULT.** A per-row threshold **exists** that gets 28 of 32 rows exactly
right, so **the ceiling is in the ESTIMATOR, not in the print.** My own hypothesis — that the
setting joins words too tightly to separate (`againſtme`, `whomis`, `oftwo`) — is **refuted**.

**What the oracle threshold IS, expressed without the gold:** `threshold / pitch` ranges 0.07–0.35
and is useless; the threshold as a **QUANTILE of the row's own gaps** is tight — median **0.794**,
p10 0.731, p90 0.936. ⚠️ Not a curve fit: in a line of N components carrying W words, ~W−1 gaps are
word spaces and the rest fall inside words; words in this setting run ~4–5 sorts, so ~4 gaps in 5
are intra-word and the word space sits at the ~0.8 quantile **by construction** — a property of the
setting's average word length, which is why it holds where a multiple of the type size does not.
Q was derived from this window, so the halves are reported apart: **0.809** (400–409) and **0.792**
(410–419) independently.

| ✅ **RECOGNISER — word boundaries from the model's decoded spaces** (R2.1h redesign, adopted) | **0.8125** | **0.25** | **0.0000** |

## R2.1h REDESIGN — ADOPTED. The split comes from the recogniser's character positions

**The ALERT above named a different RESOURCE CLASS and that is what closed it, not a better
threshold.** `reichenau_dr.mlmodel` carries a 233-symbol codec that **contains the space**, and
kraken's record returns a per-character `x` (`.cuts`) beside the prediction. The word boundary stops
being a threshold estimated from ~30 gaps and becomes **a symbol the model decoded**, positioned by
the same pass that read the letters. `witness/collation_read.py`: `recogniser_split`,
`region_segments`, `make_recogniser_split`, `gap_split`, `head_tokens`.

**It clears all three pre-registered bars, none of them relaxed**: exact **0.8125** ≥ 0.75 · blob
**0.0000** ≤ 0.05 · beats both controls. Halves 0.9375 / 0.6875, and unlike Q=0.80 the splitter was
in no way derived from this gold — the model was trained before the gold existed.

⚠️ **THREE THINGS IT COST, MEASURED, NONE OF THEM GUESSED:**
1. **A NEW FAILURE MODE.** A gap rule can never truncate a row; the recogniser can stop early and
   can drop a space (`'OgAlaine'`, `'whomis'`). Both UNDER-count. `coverage` is returned on every
   call and reported per row, so truncation is visible rather than inferred from a count.
2. **TRUNCATION IS CAUSED BY CROSSING A REGION BOUNDARY** and was fixed by composition, not tuning.
   Read as one crop, leaf 414 row 0 (running head → white → side-note) returned `'NVMERI.'` at
   coverage 0.50, merging every trailing sort into one token spanning x 249–1347; the RunningHead
   gold bound to it and the REGION score fell to RH **0.7895** with 29 orphans. Cutting the row on
   the **already-justified `REGION_GAP_P` rule** before recognising — a gap wider than the line
   pitch is a run to another region, not a word space — took word count 0.7500 → **0.8125** and
   restored RH to **1.0000**.
3. **IT COUPLES BOTH HALVES OF THE CONTINUITY MEASURE.** Catchword reader and head reader now share
   a model on the split *and* the read, where the split used to be independent geometry. A
   systematic recogniser fault can no longer disagree with itself. Paid knowingly, recorded here.

🔴 **AND IT EXPOSED THAT THE REGION SCORER COULD NOT RANK SPLITTERS AT ALL — raised as R2.1j.**

🔴 **STATUS: the quantile splitter is still NOT adopted.** It removes the blob outright
(0.2500 → **0.0000**), more than halves the error (MAE 3.50 → **1.44**) and removes the bias
(baseline 21 UNDER of 23; now 11 OVER / 13 UNDER) — but it scores **exact 0.2500 against a
pre-registered bar of 0.75**, and below LEAF-POOLED's 0.3125. ⚠️ **A change that fails its own
acceptance is not admitted**, the same rule that keeps `chapter_model_derive` pinned OFF at net −6.
**The bar is not lowered and the metric is not swapped to MAE after the fact.** ALERT: the
*approach* — a single scalar gap threshold per row — needs redesign. Named candidate, and a
different resource class rather than more tuning: **take the split from the recogniser's own
character positions**, so word boundaries come from the model that already reads the line correctly,
instead of from a geometric threshold estimated on 30 numbers.

## R2.2c 🔴 OPEN, BLOCKING — the reader's band does not contain the running head, on 20 of 20 leaves

**Found 2026-08-17 by RENDERING leaf 414 and seeing no running head in it** — not by any score.
`witness/render_pipeline.py` (NEW, tracked) draws each pipeline stage onto the actual scan.

* Production reader: `CR.head_band` = **0.06h .. 0.30h** (frozen, R2.1f's one spent re-cut).
* Both scorers (`score_head_regions.py`, `score_head_tokens.py`) and the **121-token region gold**:
  **0 .. 0.35h**. A DIFFERENT CROP, with its own row indices.
* Measured over leaves 400–419 the running head sits at **0.027h .. 0.071h** ⇒ **INSIDE the production
  band on 0 of 20 leaves.**

🔴 **So "RunningHead recall 20/20 = 1.0000" is measured in conditions the reader never meets.** The
separator is not wrong — it is **scored where its main job exists and deployed where it does not**.
⚠️ **EIGHTH INSTANCE OF THE SIGNATURE DEFECT: a correct rule that nothing downstream reads.** It is
also why R2.2b (band not anchored to the type block) is now the blocking geometry step rather than a
noted imperfection — the scorers quietly worked AROUND the frozen band instead of measuring it.
**Acceptance: the scorers and the gold must address the SAME band the reader receives, or the band
must be anchored so that it contains what the gold labels. C2. Until then no region number transfers
to the reader.**

### ✅ THE ADDRESS IS BUILT AND THE GUARD HAS LANDED — 2026-08-18. The STEP STAYS OPEN.

**`witness/test_band_agreement.py` (NEW, tracked, exits 1)** is the guard R2.2c said must land with
the fix. **`witness/gold_rekey_pagefrac.py` (NEW, tracked, exits 0)** is what made the question
askable: the gold's address was `(row, l, r)` in band pixels, and **`row` is AGAIN AN ORDINAL** —
this time into a list the BAND controls, exactly the shape R2.1i removed for the splitter and R2.1j
removed for token coarseness. **Third time, same lesson: replace an index into something a stage
controls with a measurement of the PAGE.** Every entry now also carries `y0f/y1f/xlf/xrf`, page
fractions; the band-pixel fields are KEPT so 0.8760 stays reproducible. **125/125 placed, 0
unplaced.** `CR.band_frame` / `to_page_frac` / `from_page_frac` are the one shared definition;
`CR.head_band` is re-expressed on them and verified **pixel-identical on all 20 leaves**.

⚠️ **The measured geometry that makes this cheap, and which nobody had stated**: every band this
project cuts is FULL PAGE WIDTH resized to 1400, so two bands of one leaf share an x-scale EXACTLY
(0.452781 on OT1-1609-B) and differ by a **constant y offset of 118.63px**. The gold's `l`/`r` were
never band-dependent. Only the row ordinal ever was.

🔴 **AND THE GUARD MEASURED MORE THAN THIS STEP WAS RAISED ON. The consolation does not hold.**
R2.2c was written as a RunningHead finding, softened by "in deployment the job that actually runs is
MainText-vs-MarginNote". Measured against the reader's band:

| gold entries INSIDE the reader's band | | |
|---|---|---|
| RunningHead | **0 / 20** | as R2.2c recorded |
| MarginNote | **2 / 19** | 🔴 NEW — the MT-vs-MN job is *also* scored outside deployment |
| MainText | 66 / 80 | |
| ChapterHead | 2 / 2 | |

⇒ **51 of 121 entries — 42% — lie outside the band the reader receives**, and the MN recall the
suite reports (0.8947) rests on 17 entries the reader cannot see. **The fallback position was
itself unmeasured.**

🔴 **C4 COVERAGE, the converse question, and it is NOT the same question.** C3 asks whether the
reader's band contains what the gold labels. C4 asks whether the gold says anything about what that
band CONTAINS. The gold's ink spans **0.0268h..0.1113h**; the reader's band is 0.06h..0.30h ⇒ **the
gold speaks to 21.4% of the band the reader actually reads.** Even the 66 MT entries counted INSIDE
sit in its top fifth; the rest is unlabelled territory typed on every leaf. **Reported, deliberately
NOT pass/fail** — closing it means labelling more of the page, which must not hide inside a band
fix. It stays OPEN and named.

⚠️ **THE GUARD IS ITSELF CHECKED, because a test that does not move is not evidence until it is
shown it COULD have moved** (two injection tests were mis-designed this session). C3 is re-run
against the band the gold was LABELLED in, where it returns **121/121**. So the failure is a fact
about the reader's band and not an arithmetic error in the new address.

**WHAT IS DELIBERATELY NOT DONE HERE: `HEAD_BAND` IS NOT WIDENED.** R2.1f pre-registered exactly one
band re-cut and it is spent on the word-gap fix; widening it to make a new guard pass would be that
re-cut under another name, and would convert a below-threshold result into an accepted one. The
guard reports the **SHORTFALL — 0.0332h at the top** — in the vocabulary a fix must satisfy.
**Choosing the band is R2.2b, which this now blocks on rather than replaces.**

## R2.1k 🔴 OPEN — a body row fails R3 by 12px because the SPLITTER improved

**Also found by rendering** (leaf 414's whole first body row typed MarginNote under the new splitter).
`region_head.SPAN_MODE` (default `"tokens"` = unchanged) exists only to measure the candidates.

**CAUSE, exact.** R3's span clause measures a row's reach over tokens with `n_glyphs >= MIN_GLYPHS`.
**`MIN_GLYPHS` is a SPECK FILTER doing duty as a SPAN ESTIMATOR** — a 2-component word like `of` is
not a speck. Leaf 414 row 1: blob splitter ⇒ one 37-component token, span **851px** vs requirement
**677px**, passes trivially. Recogniser splitter ⇒ **5 real in-block words drop out** (rightmost at
r=1086), span collapses to **696px**, while finer tokens push `block_measure` R 1142→1184 so the
requirement **RISES** to **708px**. The bar went up as the measurement came down; the row fails by
**12px** and every word in it is relabelled with nothing about the page changed.

**ALL THREE CANDIDATES REFUTED, measured on all 121 gold tokens under 5 splitters:**

| R3 span from | overall | RH | MN | MT | verdict |
|---|---|---|---|---|---|
| `tokens` (shipped) | 0.8760 | 1.0000 | 0.8421 | 0.8500 | splitter-dependent — the defect |
| `ink` | 0.9091 | **0.7500** | 0.8421 | 0.9625 | 🔴 REFUTED |
| `segment` (longest region run) | 0.8430 | 1.0000 | **0.9474** | **0.7875** | 🔴 REFUTED |

* 🔴 **`ink` fails because A HEADLINE BAND IS NOT A LINE.** Leaf 414 row 0 is `382 … NVMERI. …
  Sacrifices for` — three separate elements whose COMBINED extent spans nearly the measure though none
  approaches it. Every running head then looks like a full justified line: RH falls to 0.7500 under
  **every** splitter. It trades R3's current failure for the one the span clause was added to prevent.
* 🔴 **`segment` fails from the other side**: it holds RH 1.0000 and gives the best MN recall measured
  (**0.9474** on three splitters), but a body row's own VERSE NUMBER sits beyond a pitch-wide gap, so
  the body line is cut short of the measure and MT falls to 0.7875.
* ➡️ **NEXT CANDIDATE, from reading the two refutations together**: the extent of the region run that
  is **FLUSH TO L OR R**, not the longest — continuous like a justified line, anchored like one, and
  computed on GLYPH BOXES so no splitter can move it. **C2.** Nothing adopted until it clears a
  pre-registered bar; `SPAN_MODE` stays `"tokens"`.
* 🔴 **BUILT AND REFUTED 2026-08-25 — `SPAN_MODE="flush"`, `region_head.classify`.** It is the best
  span rule measured and it still fails: control MT **0.8375 → 0.7750 (62/80)** against S-A's
  do-no-harm, and it moves the candidate arm **not at all**. Kept, DEFAULT OFF, because the
  refutation is the finding. See **R2.2n** below for the four-candidate table and **R2.2o** for why
  none of them could have worked.

---

## R2.2n 🔴 OPEN — THE MN GAP. Four span rules, four refutations, one cause upstream of all of them

**Raised 2026-08-25 while closing candidate 4's last failing criterion.** `witness/region_head.py`.
**Status: OPEN. `BASELINE_MODEL` stays False; candidate 4 (R2.2i+R2.2k) stays UNADOPTED.**

### The defect

Candidate 4 loses two margin notes the control gets right — **410.0.2** (gold MN → got MT) and
**419.0.0** (gold MN → got RH). Neither token moved: 410.0.2's x-centre is `+0.929` under both arms.
**The label changed because a different token joined its row.** Measured, leaf 410 row 0:

| arm | tokens in row 0 | x-extent | labels |
|---|---|---|---|
| control | 2 | 0.444–0.837 | `RH@0.51` `MN@0.78` — both correct |
| candidate | 3 | 0.171–0.837 | `MT@0.19` `MT@0.51` `MT@0.78` — **all three wrong** |

The third token is a real line of type that the R2.2m far-chaining fix recovered (the `far` bucket
had been deleting it). With `SPAN_MODE="tokens"` a row's span is the **union of its token extents**,
so that token drags the union to the left edge; R3 finds the row flush and ≥ `BODY_SPAN_M × measure`,
promotes it to a body row, and R4 sweeps every token in it into MainText.

⚠️ **`region_head` line 444 already records this failure with a different cause** — *"leaf 406's
headline row was promoted to a body row by a 3-glyph UNREAD speck… and the running head was then
labelled MainText."* The span clause was added to stop **specks**, and `MIN_GLYPHS` filters specks.
This intruder is not a speck, so nothing filters it. **The row model got better and the classifier's
weakest assumption became load-bearing.**

⚠️ **419.0.0 IS A DIFFERENT CAUSE AND WAS INITIALLY CONFLATED WITH 410.** Leaf 419 drops 24 → 21
rows, and its row 0 holds entirely different tokens. The seeded model is **separating the margin
column onto its own baseline** — control row `212.0 n=42 x 0.120–0.925` becomes candidate rows
`211.0 n=9 x 0.813–0.891` **plus** `214.5 n=34 x 0.120–0.904`. That is physically *more* correct;
the relabelling follows because **R3/R4 reason about regions using the ROW as the unit**, which is
this module's founding observation (*"a row is not homogeneous in REGION"*) applied to the one place
the module still assumes it is.

### Pre-registered acceptance (written before the first run; unchanged across all four candidates)

| id | criterion |
|---|---|
| **S-A** | CONTROL DO-NO-HARM at `BASELINE_MODEL=False`: RH ≥ 1.0000, MN ≥ 0.8947, MT ≥ 0.8375, CH ≥ 1.0000. A fix for the candidate may not be bought with production's numbers. |
| **S-B** | THE TARGET: candidate MN ≥ 0.8947 — it must stop being worse than the control on the region this is meant to fix. |
| **S-C** | DENOMINATOR (the 2026-08-22 bar): control keeps `pairs == 121` with 0 sinks; candidate sinks ≤ 5. |
| **S-D** | THE NAMED ENTRIES: 410.0.2 **and** 419.0.0 both come out MN under the candidate. A rate that improves without fixing the two cases the change was written for is fixing something else. |
| **S-E** | NO SILENT TRADE: RH and CH must not fall under either arm. |

### The four candidates, all measured, all refuted

| candidate | ctl RH | ctl MN | ctl MT | cand MN | verdict |
|---|---|---|---|---|---|
| `SPAN_MODE="tokens"` (incumbent) | 1.0000 | 0.8947 | **0.8375** (67/80) | 0.7895 | status quo |
| `SPAN_MODE="segment"` | 1.0000 | 0.9474 | 0.7000 (56/80) | 0.8947 | 🔴 S-A, S-D |
| `R4_PER_SEGMENT=True` | 1.0000 | 0.8947 | 0.8375 | 0.7895 | 🔴 **INERT** — see below |
| `R4_DEMOTE_UNQUALIFIED=True` | 1.0000 | 0.9474 | 0.6875 (55/80) | 0.8947 | 🔴 S-A, S-D |
| `SPAN_MODE="flush"` (R2.2n-b) | 1.0000 | 0.9474 | 0.7750 (62/80) | 0.7895 | 🔴 S-A, S-B, S-D |

🔴 **`R4_PER_SEGMENT` IS INERT AND THAT IS ITS OWN FINDING.** Flipping it changes RH, MN, MT, pairs
and sinks **not at all**, on both arms. `_in_body_seg` returns `True` whenever the row is absent from
`body_segs`, and a row where no segment qualifies is never put there — so the rule is bypassed in
exactly the case it was built to see. ⚠️ **A candidate that cannot move a number cannot be validated
by failing to regress one**; anyone who had "tested" R2.2f by flipping it and observing no regression
would have called it safe. Same shape as Gate 0f, Gate 0d and R13: the thing exists and nothing
consumes it.

⚠️ **S-B PASSED FOR TWO CANDIDATES THAT S-D FAILED**, which is exactly why S-D was pre-registered:
MN reached the target rate while one of the two entries the change was written for stayed broken.

---

## R2.2o 🚨 **APPROACH-LEVEL ALERT FIRED 2026-08-25 — R2.2 IS RE-SCOPED, NOT CONTINUED**

🚨 **THE ALERT R2.2o.3 PRE-AUTHORISED HAS BEEN FIRED, BY SIR'S RULING, BEFORE A FIFTH RULE WAS BUILT.**
R2.2o.3 reads: *"if none does, R2.2n escalates as an approach-level ALERT, not an accepted gap."* Four
candidates were refuted, and R2.2o.1 then showed **why a fifth must fail**: the gap populations overlap
(0.875 pitches against 1.525 on one page), so **no constant exists to be found**. Building the fifth to
watch it fail would have been ceremony.

⚠️ **THIS IS A REDESIGN OF THE METHOD, NOT A LOWERED AIM, AND THE MN GAP STAYS OPEN.** Per the No
Silent Degradation rule: *"the method can't reach it" always means "redesign the method"*. Nothing
below accepts a sub-threshold result. `BASELINE_MODEL` stays False and every candidate flag stays off.

**THE RE-SCOPE**, per Masterplan §3.0 which now governs:

| | before | after |
|---|---|---|
| what `region_head` / `region_segments` **is** | the region-typing model, scored on MN/MT recall | the **initialisation and plausibility clamp** of §3.2 item 5 — the agent's floor, not the agent |
| what "done" means for it | MN recall ≥ 0.8947 **and** MT ≥ 0.8375 simultaneously | **characterised, and willing to abstain**: it knows the leaves and rows where it is out of its depth, and says so |
| the four refuted rules + R2.2o.1 | a stalled repair | ✅ **COMPLETE CHARACTERISATION WORK** — they establish precisely where geometry alone cannot decide, which is what a clamp must know |
| the 19-entry MN bar | an adoption bar | a **characterisation** set. ⚠️ R2.2o.4 disputes its correctness, and one may not adopt against a disputed 19-entry denominator on one witness |

⇒ **R2.2o.2 is DEMOTED from "build the cut rule" to "characterise the signal"** (see its row). Its
second-signal hypothesis — *ink beyond the gap that is itself column-like* — is a good **feature
description for a learned model** and an unsafe hand-tuned constant at n=2.
⇒ **R2.2o.1b is retained** but is no longer a blocker on a rule nobody will now build; it becomes the
body-block characterisation input to **R14**.
⇒ **The work moves to R14**, the adaptive visual agent.

---

### R2.2o's original finding (retained — it is the evidence the re-scope rests on)

🔴 **OPEN, was BLOCKING R2.2n** — `region_segments` mis-cuts a third of the body

### The finding

The three non-inert candidates each buy ~1 MN for **11–12 MainText**, the *same* trade from three
different directions. That is one refutation, not three: all of them rest on `CR.region_segments`,
which cuts a row wherever a gap exceeds the **line pitch**, on the rule *"a gap wider than the line
pitch is a run to another region, not a word space"*.

**Measured over the control's rows, leaves 400–419** (`.scratch/r2/probe_v25.py`), restricted to rows
whose token union spans ≥ 0.75 of the measure — i.e. genuine body lines:

| quantity | value |
|---|---|
| body-like rows examined | 301 |
| rows with **NO** continuous segment reaching `BODY_SPAN_M` (0.75) | **102 (34%)** |
| rows that are a single segment | 147 (49%) |
| median segments per row | 2 |
| intra-row gaps exceeding 1 pitch | 261 of 11,298 (**2.3%**) |

⚠️ **In JUSTIFIED setting the word space is stretched to fill the measure.** 2.3% of gaps is enough
to shred a third of the body. The roadmap already knew one instance of this — *"a body row's own
VERSE NUMBER sits beyond a pitch-wide gap"* — and the measurement generalises it: the verse number is
one case of a rule that cannot separate a stretched word space from a run out to the margin.
**Every rule built on this primitive inherits the error, so a fifth span rule would inherit it too.**

### Steps

| # | step | deliverable | acceptance |
|---|---|---|---|
| R2.2o.1 | **Characterise the two gap populations before choosing a rule** | over leaves 400–419, every intra-row gap labelled from the GOLD as a word space or a region gap, with the two distributions published in pitches | the populations are shown **separated or overlapping**, with the overlap quantified. ⚠️ If they overlap, no single threshold can work and the rule must use a second signal — say so rather than tuning the threshold. **C2** | ✅ **ANSWERED FOR THE HEAD BAND, 🔴 OPEN FOR THE BODY** — result block below |
| R2.2o.2 | 🚨 **DEMOTED 2026-08-25 to CHARACTERISE THE SIGNAL, not build the rule** (see the ALERT above). Measure how separable *"the ink beyond the gap forms a column-like run"* is, and hand the measurement to **R14** as a feature. **Do NOT adopt a constant from it.** Original text follows — **A cut rule that uses what a margin actually is** | a region gap is a **sustained** gap with ink beyond it that is itself column-like — not a single wide space. Candidate: cut only where the gap exceeds the pitch **and** the ink to its right forms a run narrower than `1 − BODY_SPAN_M` of the measure | pre-registered against the R2.2n table: control MT ≥ 0.8375 **and** control MN ≥ 0.8947 simultaneously. Neither alone; the whole point is that every candidate so far traded one for the other. **C3** |
| R2.2o.3 | **Re-run the four R2.2n candidates against the repaired primitive** | the R2.2n table regenerated | any candidate clearing all five bars is adopted; if none does, R2.2n escalates as an approach-level ALERT, not an accepted gap. **C2** |

### R2.2o.1 RESULT — the populations OVERLAP, and the gold cannot see where it matters

**`witness/score_region_gap_pops.py`, leaves 400–419, 2026-08-25.** Every intra-row gap labelled from
GOLD-HEADBAND's hand-assigned region labels; geometry used only to ADDRESS which entry a glyph belongs
to (`ink2d` vertical ink overlap + centre containment, the R2.2j / R2.1j address). ⚠️ **The labels are
not geometric**: calling a gap a region gap BECAUSE IT IS WIDE would score the cut rule against its own
signal, the circularity the gold's own `labelling_basis` forbids.

| population | n | median | p90 | p99 | max |
|---|---|---|---|---|---|
| word space (both glyphs, SAME gold entry) | 970 | 0.075 | 0.275 | 0.602 | **1.525** |
| region gap (entries of DIFFERENT labels) | 16 | 7.127 | 10.756 | 11.628 | 11.662 |
| same-label seam (different entries, same label) | 39 | 0.400 | 1.051 | 1.529 | 1.718 |

Widths in PITCHES. Denominator **986 labelled gaps of 12,592 examined**; 11,533 unlabelled, 34
ambiguous-excluded — counted, never dropped (R1.4).

🔴 **THE POPULATIONS OVERLAP on [0.875, 1.525] pitches.** The narrowest true region gap is NARROWER
than the widest true word space. 6 of 970 word spaces and 1 of 16 region gaps fall in the overlap. The
best achievable single threshold (gap > 1.525) still misclassifies 1 of 986; the incumbent (gap > 1.0)
misclassifies 5 — 4 word spaces wrongly cut, 1 region gap missed.

⚠️ **THE AGGREGATE IS CARRIED BY THE EASY PAIR.** 14 of the 16 region gaps are **MN|RH** — running head
against side-note, median **7.3** pitches, separated by the whole head of the page, which no rule has
ever got wrong. Only **2** are **MN|MT**, the boundary the MN gap is actually about:

| leaf | gap | verdict under the incumbent rule |
|---|---|---|
| 412 | **0.875** pitches | 🔴 BELOW the cut — **NEVER CUT**. `'aTemporal'` \| `'Cades of the deſert Sin'` |
| 412 | 2.250 pitches | cut |

🔴 **INDEPENDENT CORROBORATION OF R2.2e-b, FROM A DIFFERENT INSTRUMENT.** `region_head` L164–170 records
leaf 412 as the leaf where *"the marginal column and the measure are contiguous"* — the founding
observation behind R2.2o.4's warning. This measurement reaches leaf 412 by a route that knows nothing
of that note: it labels gaps from the gold's TEXT and finds the MN|MT separation there is **0.875
pitches, below the cut**. Two instruments, different inputs, the same leaf, the same mechanism.

⇒ **"RETUNE THE THRESHOLD" IS REFUTED AS THE REPAIR.** Where the marginal column abuts the measure, no
width threshold can exist, because the region gap there is narrower than a stretched word space
elsewhere on the same page. R2.2o.2's requirement that the rule consult **what lies beyond the gap** is
now SUPPORTED by measurement rather than assumed. Its second signal must not be a better number.

⚠️ **AND THE MEASUREMENT CANNOT SEE THE BODY.** GOLD-HEADBAND labels the **TOP 3 ROWS** of each leaf.
R2.2o's damage figure — 102 of 301 body-like rows with no run reaching the measure — is over the WHOLE
band. The labelled denominator is **7.8%** of gaps and holds **2** MN|MT boundaries. A low
misclassification rate here is evidence about the HEAD BAND and nothing else. **No number from this
scorer may be quoted as "the cut rule is 99.5% correct".** ⇒ **R2.2o.1b**.

⚠️ **The seam fold was ATTEMPTED AND REFUSED, by the script, at run time.** The primitive decides "cut
here?", not "different entries?", so a same-label seam is a must-NOT-cut gap and belongs with the word
spaces — but only if no seam spans the text block (two MN entries either side of the body are
same-label yet genuinely separate). **7 of 39 seams** are as wide as the narrowest region gap, so the
check refuses the fold and the stricter entry-level accounting stands. The looser number is not
reported. A check with no live way to say no is not a check.

| # | step | deliverable | acceptance |
|---|---|---|---|
| R2.2o.1b | **A gap gold for the BODY BLOCK** — R2.2o.1 is unanswerable where the defect lives | region labels for the gaps of body rows outside the top 3, adjudicated from what the row SAYS (the `build_region_gap_gold` basis), NEVER from position | the MN\|MT population reaches **n ≥ 20** and the overlap is re-measured on it. ⚠️ **R2.2o.2 CANNOT BE PRE-REGISTERED UNTIL THIS EXISTS** — its bar would rest on 2 boundaries, which is Goodhart at n=2. **C2, and it BLOCKS R2.2o.2** |

⚠️ **R2.2o.4 — THE BAR MAY BE ANCHORED TO A WRONG NUMBER.** `region_head` line 169 records that the
gold's **MN 0.8947 "was resting on" two cancelling errors** — leaf 412's note scored MarginNote only
because its row was broken, and repairing the row exposed the second error. S-A and S-B are both
anchored to 0.8947. **Before R2.2o.2's bar is used to adopt anything, re-audit the 19 MN gold entries
and establish what MN recall a correct reader would score.** Adopting against a number built on
cancelling errors is Goodhart with extra steps. **C2, and it gates R2.2o.2's acceptance.**

⚠️ **R2.2o.1 has now corroborated the leaf-412 mechanism from a SECOND instrument** (result block
above: the MN|MT separation there is 0.875 pitches, below the cut, so the row is never cut). The
re-audit of the 19 MN gold entries is not optional bookkeeping — the cancelling-errors account now has
two independent witnesses, and the 0.8947 bar rests on 19 entries of one witness over 20 leaves.

## R2.1j — the region scorer could not rank splitters, and one binding rule flattered a broken one

**Raised and closed in the same pass, 2026-08-17. `witness/score_head_regions.py`: `contain`,
`ink_bind`.** R2.1i re-keyed the gold by band-pixel SPAN so a splitter change would stop reading as
a region regression. That fixed *how an entry addresses a token*. It did not fix that **an entry can
be COARSER than a token**: 43 of the 121 entries (**35.5%**) carry more than one word, because they
were hand-labelled while the splitter still blobbed. `match` requires the bound token to cover
**half the gold span**, which no single word can do against a twelve-word entry — under the
recogniser splitter **31 of 121 entries went orphan with nothing about any region having changed.**

🔴 **AND THE SAME MEASUREMENT INDICTS THE NUMBERS R2.1i REPORTED.** A deliberately broken splitter
(`fine ×0.4`) posts the **HIGHEST** max-overlap accuracy on this gold, **0.9479**, by orphaning 25
entries — the ones it cannot bind are the hard ones, so discarding them *raises* the score. **A
binding rule that drops entries cannot rank splitters**, and R2.1i's "0.9474 under the quantile
splitter, 26 withheld" must be read as **part selection, not improvement alone**.

🔴 **MY FIRST REPLACEMENT ALSO FAILED ITS OWN PRE-REGISTRATION, and the failure is kept.**
CONTAINMENT (every token whose centre lies in the gold span takes its label) was pre-registered as
"every entry binds ≥1 token under every splitter". Orphans measured: baseline 0 · quantile 6 ·
coarse ×1.6 **33** · fine ×0.4 0 · recogniser 4. It breaks in the direction *opposite* to
max-overlap — merge two tokens and the merged centre leaves a small span. **One rule fails as tokens
get finer, the other as they get coarser, and both let the DENOMINATOR move with the splitter**,
which is the whole reason splitters could not be compared.

✅ **WHAT SURVIVES — bind by INK.** An entry takes the label holding the most overlapping ink, so
every entry with ink under it binds at any token size and **the denominator is 121 for every
splitter**. Merging still costs (a coarse token straddling two entries is wrong for one); shattering
still costs and is separately visible as **purity**. Pre-registered accounting — 121 scored, 0
orphans, under every splitter — **holds on all five**, including the two deliberately broken ones.

| splitter | max-overlap acc | n | orph | **INK acc** | **n** | **orph** | purity | RH | MN | MT |
|---|---|---|---|---|---|---|---|---|---|---|
| baseline (per-row 2M) | 0.8760 | 121 | 0 | **0.8760** | 121 | 0 | 1.0000 | 1.0000 | 0.8947 | 0.8375 |
| R2.1h quantile | 0.9474 | 95 | 21 | **0.9504** | 121 | 0 | 0.9927 | 1.0000 | 0.8421 | 0.9625 |
| coarse ×1.6 | 0.7957 | 93 | 0 | **0.8264** | 121 | 0 | 1.0000 | 0.9500 | 0.8421 | 0.7875 |
| ⚠️ fine ×0.4 (deliberately broken) | **0.9479** | 96 | 25 | **0.8926** | 121 | 0 | 0.9949 | 0.8500 | 0.8421 | 0.9125 |
| RECOGNISER (adopted) | 0.8876 | 89 | 31 | **0.8760** | 121 | 0 | 0.9775 | 1.0000 | 0.8421 | 0.8500 |

🟢 **Once survivorship is removed the ranking is interpretable.** `fine ×0.4` falls to 0.8926 with RH
collapsing to 0.85 — the shattering becomes *visible* instead of hiding among the entries it could
not bind. **The recogniser splitter is adopted at region PARITY** (0.8760, RH 1.0000 held), so R2.1h
costs R2.1g nothing. And the quantile splitter's region gain turns out to be **real** — 0.9504 on
all 121 at purity 0.9927 — which is a finding about *regions*, not a licence to adopt a splitter
that fails its own word-count bar at 0.2500.

⚠️ **OPEN, and it is a limit of the GOLD, not of the scorer**: 43 entries are phrase-length, so the
gold cannot distinguish a splitter that gets every word boundary right from one that gets the
*region* right and the words wrong. Word-grain re-labelling of those 43 entries is **R2.1j-b, C2**.

🔴 **The prefix rule is a SECOND, SEPARATE cause, proven by injection** (`audit_prefix_rule.py`,
exit 1 while it stands): `norm()` strips spaces, so a blob collapses to one string, and `agrees()`
requires the shorter side to be ≥4 characters. The **same blob shape** therefore scores in opposite
directions according to the catchword's letter count — `'face'` vs blob → **AGREE**, `'two,'` (three
letters after normalisation) vs blob → **DISAGREE**. ⚠️ **The catchword's length is not a property of
the instrument**, so the rate mixes an instrument property with the book's vocabulary. ⚠️ **Do NOT
close this by lowering the 4-character floor** — it was raised in R2.1d′ precisely because a
2-character misread (`'wl'`) matched almost anything. The head side must present WORDS. **The two
halves of R2.1h must therefore close TOGETHER**: fixing the splitter alone moves the rate in an
uninterpretable direction, because the two biases would stop cancelling at the same rate.

🟡 **HALF-CLOSED, AND THE AUDIT'S EXIT CONDITION WAS REBUILT (2026-08-17).** The direction-dependence
of `agrees()` will **never** stop reproducing — a prefix test with a minimum length *is*
length-dependent by construction — so an exit condition asserting it had changed would have been
asserting something that must not happen. That demonstration is now a **regression check on the
scorer**, and what closes the audit is the other end: **the rule mis-scores BLOBS, so it stops
mattering when the READER stops producing them**, measured on the production reader over leaves
400–419 via the same `head_tokens` the reader itself uses.

Under R2.1h's splitter: **17 words · 2 blobs · 1 abstention**, so the audit **stays OPEN at exit 1**
— correctly. ⚠️ **My first version of this criterion was unfalsifiable in the direction that
counts**: it tested only for an internal space, which a whole-line token passes whenever the
recogniser decodes **no** space at all (leaf 417, `'hpromiſſe,hal'`). A blob was never defined by
whitespace but by a token spanning the LINE, so the token's SPAN is now tested against its row
(>50% ⇒ blob) — and that test is what catches leaf 416 (`'.'`, **100%** of its row) and 417 (54%).
Abstentions are counted separately and are **not** successes, so a reader that closed this audit by
refusing to read would be visible.

| # | step | deliverable | acceptance |
|---|---|---|---|
| R2.1i | 🔴 **THE REGION GOLD IS KEYED BY TOKEN ORDINAL, SO ANY SPLITTER CHANGE SILENTLY RENUMBERS IT** (measured 2026-08-17) | Wiring R2.1h's splitter into `region_head` collapsed the R2.1g score — MarginNote recall **0.8947 → 0.5263**, unlabelled **80 → 212** — while **nothing about the regions changed**. ⚠️ Every future tokenisation improvement will read as a REGION REGRESSION until this is fixed, which is an instrument that punishes progress. Deliverable: re-key `head_regions_*.json` to address a token by **(row, x-centre at labelling time)** and match by containment, not by ordinal | injection-proven: perturb the splitter and the region score must be UNCHANGED. ⚠️ A gold label must be *addressed* geometrically but never *adjudicated* geometrically — addressing is not adjudication, the same distinction the registry already draws for training crops. Merge collisions (two labels landing in one token) must be REPORTED, never silently scored. **C2 — assembly.** ⚠️ This BLOCKS R2.1h: until it is done, no splitter change can be evaluated at all |

##### 🟢 R2.1i DONE 2026-08-17 — and it corrected ITS OWN pre-registered acceptance TWICE, in the open

**Re-key.** `head_regions_*.json` v2: a label is addressed by its **band-pixel span** within a row,
never by a token ordinal, and scoring binds each label to the token of maximal overlap. The
`ambiguous` list is re-keyed too — left on ordinals an exclusion would drift independently of the
labels and silently re-admit the very token it was written to exclude. 121 labels re-keyed with
**0 span drift** against a live re-derivation (the dump was cross-checked, not trusted — R11.3a's
*"the commit is not the pin"*). ✅ **The re-key is faithful**: unperturbed score is **0.8760 / RH
1.0000 / MN 0.8947 / 121 scored / 0 collisions / 0 orphans — identical to v1.**

🔴 **THE PRE-REGISTERED ACCEPTANCE WAS WRONG, AND SO WAS ITS FIRST REPLACEMENT. Both are recorded.**

* **As written** — *"perturb the splitter and the region score must be UNCHANGED"* — is
  **unachievable, and not because the addressing is bad.** Rule R5 asks where a token's CENTRE sits,
  so cutting `NVMERI.` into `NVME` + `RI.` moves both fragments' centres. Measured: under a 0.4×
  splitter, scored count / collisions / orphans were **all unchanged (121 / 0 / 0, every label
  bound)** while RH recall still moved. Nothing was misaddressed.
* **First replacement** — *"same token ⇒ same label"* — **also failed**, on tokens the splitter had
  NOT re-cut, and the flips were cases where the perturbed splitter produced the **better** label.
  Cause: `block_measure` estimates the measure **from token edges**, so a splitter change moves the
  measure and with it every in-block decision, including for tokens it never touched.
* ⚠️ **The lesson, and it generalises: the region OUTPUT cannot be stable under a splitter change,
  because the splitter is one of the region model's INPUTS.** Any acceptance demanding output
  stability was testing the model while claiming to test the address. Two versions of this step's
  own acceptance conflated them.

**What IS well-posed, and is now the acceptance** (`witness/test_region_gold_addressing.py`,
guard, exit 0):
| | criterion | result |
|---|---|---|
| **A** | **BINDING FIDELITY** — every SCORED entry binds to a token overlapping ≥50% of the gold span. ⚠️ Checked **without reference to any region label**, which is what makes it a test of the ADDRESS rather than of the model. **v1 had no such clause at all** | ✅ 0 weak bindings under all 3 perturbations |
| **B** | **ACCOUNTING** — any change in scored count is **fully explained** by reported collisions and orphans. A gold may lose a label to a merge; it may not lose one to bookkeeping | ✅ 26=26 · 28=28 · 25=25 |

**Perturbations: the real one (R2.1h's quantile splitter) plus a deliberate over-merge (×1.6, forces
collisions) and over-split (×0.4, forces orphans), so both clauses are actually exercised.**

🟢 **THE POINT, MEASURED.** Under R2.1h's splitter the region score is now **0.9474 / RH 1.0000**,
with 26 labels **honestly withheld** as 5 collisions + 21 orphans. **Under v1 the identical change
read as MN recall 0.5263.** The instrument no longer converts tokenisation work into a region
regression — which was the whole defect.

⚠️ **R2.1i unblocks EVALUATION of a splitter change, not ADOPTION of one.** R2.1h remains OPEN and
blocking: its quantile splitter still scores exact 0.2500 against a 0.75 bar, and the fact that it
now makes the region number look better is **not** grounds to admit it — that is scoring a component
through a downstream metric, which is the practice R2.1g exists to end.


| R2.2b | 🔴 **THE HEAD BAND IS A FIXED FRACTION OF PAGE HEIGHT AND IS NOT ANCHORED TO THE TYPE BLOCK** (measured 2026-08-17) | `0.06h..0.30h` opens **below** leaf 400's running head and **above** leaf 403's. Where the running head falls inside the band therefore varies per leaf, which is why the head reader failed in BOTH directions. Deliverable: a band bound **anchored to the top of the type**, derived from the same region primitive rather than from a page fraction | the bound is scored on **whether the band contains the first body line**, per leaf, against the hand-labelled set — directly, not through continuity. ⚠️ **This step is what makes a second band change legitimate**: it replaces a heuristic with a measured anchor and is pre-registered as such, rather than being a re-cut of the same knob to chase a rate. **C3** |


| R2.2d | 🔴 **THERE IS NO REGION TYPE FOR THE CHAPTER ARGUMENT, AND IT IS BEING TYPED AS SCRIPTURE** (measured 2026-08-18, R2.2b/A1) | this edition sets a multi-line **italic ARGUMENT** between `CHAP. XXVII.` and the first verse — 4 detected rows on leaf 403, **11** on leaf 411. It is justified to the full measure, so R3's body-row test passes and `region_head` labels it **MainText**: leaf 411 rows 3–7, leaf 403 rows 6–7. **The head reader therefore returns the ARGUMENT's opening as the leaf's first line of scripture on every chapter-opening leaf.** Deliverable: an `ARGUMENT` region in the R1–R6 rules, separated by a property of the SETTING (it is set in ITALIC, at the same measure, between a ChapterHead and the first verse) rather than by position | scored on the region gold **extended to label argument lines** — ⚠️ **the current gold CANNOT test this**: on leaves 403 and 411 it labels no MainText at all (2 and 4 entries), because the labeller had no admissible label. **That sparseness is the fossil of the missing category and the blind spot sits on the same leaves as the defect.** Acceptance: argument rows labelled ARGUMENT on both chapter-opening leaves, MainText recall NOT reduced elsewhere, and the head reader's opening word on those leaves becomes the verse, not the argument. **C3** |

| R2.2e | 🔴 **A ROW SWALLOWED INTO ONE TOKEN IS TYPED MarginNote — 49 rows, 44 of them SCRIPTURE** (measured 2026-08-19, with `ARGUMENT_RULE` OFF, i.e. the SHIPPING pipeline) | the tokeniser sometimes emits ONE token covering a whole printed line (leaf 412 r33: 63 glyphs, 90% of the row). `in_block` tests `l < L or r > R`, so **a token spanning the measure necessarily fails it** and is labelled MarginNote — `† And Moyses referred their people` and 43 more body lines typed as marginalia. 🔴 **Two splitters disagree about one row and the COARSER one decides the label**: `region_segments` cuts r33 correctly into side-note + argument, but the label rides on the unsplit token. ⚠️ **The 121-token region gold cannot see any of it** — it lives in the 3-row head band and these rows are mid-page, so **0.8760 is not evidence against this**. Residual population after R2.1h fixed the blob's `k=2` cause; the R3-side view of the same handoff is R2.1k | Deliverable: `in_block` must not be decidable by a token the tokeniser failed to split — run the block test at `region_segments` grain, or split a row-spanning token before labelling. Acceptance: row-spanning out-of-block tokens go to **0** on the 20 leaves with the region gold's four numbers NOT falling. **C2** |

| R2.2f | 🔴 **R4 ASSIGNS BY ROW MEMBERSHIP, SO A MARGINAL NOTE ON A BODY LINE'S BASELINE IS TYPED MainText** (measured 2026-08-20, R2.2e-b) | leaf 412 r2's note `pinces are` is 142px against a 1110px measure and sits INSIDE the block bounds (the marginal column and the measure are contiguous on that leaf, so modal `L=48` is left of it). It scored MarginNote **only because its ROW was broken**; repair the row and R4 sweeps it into MainText. ⚠️ This is `region_head`'s founding observation — *a row is not homogeneous, label per TOKEN* — on a THIRD axis: it holds for region and (R2.2d) for FOUNT, but not for R4's own row-to-token inheritance. 🔴 **The gold's MN 0.8947 was RESTING on the defect**: two errors cancelled, so the number looked stable until the first genuine repair exposed the second | **PREREQUISITE for R2.2e-b and R2.2g**: no repair of the swallowed rows can pass F2 until R4 labels per token, because every repair turns a broken row into a body row. Acceptance: MN recall NOT below 0.8947 with the span qualifier ON, and no MainText entry lost. **C2** 🔴 **CANDIDATE 1 REFUTED 2026-08-20** (`R4_PER_SEGMENT`, per-region-segment R4, `witness/score_r4_segment.py`, OFF): G3 exact and G5 reach **35 rows demoted at zero cost**, but **G1 fails — the rule cannot reach its own witness**. ⚠️ **AND THE PREREQUISITE DIRECTION ABOVE IS BACKWARDS: R2.2g GOES FIRST.** Leaf 412 r2's body segment is FULL (931 of an 832 bar) but overshoots the modal edge by **45px against a 33px tolerance**, so no segment qualifies, the row falls back and the note keeps MainText. Both directions hold at once and the chain has a CYCLE; see § "R2.2f RESULT" |
| R2.2g | 🔴 **R3's FLUSH TEST INHERITS THE SAME MODAL-EDGE ASSUMPTION R2 DOES** (measured 2026-08-20, R2.2e-b) | with the span qualifier on, **20 of the 43** swallowed body rows are in-block yet still come back `CH`/`MN`: a line whose ink overshoots the modal edge is not FLUSH at that edge, and its left end sits at a marginal note, so R3 refuses it as a body row and the label falls through to R5/R6. The modal edge is a MODE over many lines — an individual justified line exceeding it is ordinary | Acceptance: those 20 rows carry MainText with the region gold's four numbers NOT falling. ⚠️ Same family as R2.1k, and the two must be resolved together rather than each patching the other's symptom. **C2** 🔴 **PROMOTED TO FIRST OF THE THREE OPEN LINKS 2026-08-20** by R2.2f's refutation: R4-per-segment cannot identify a body segment that overshoots the modal edge, so **R2.2g is R2.2f's prerequisite, not the other way round**. Independent corroboration of the count from the same run: switching the span qualifier on moves R2.2f's no-qualifying-segment fallback **160 → 180**, i.e. the same **20** rows | 🔴 **CANDIDATE 1 REFUTED 2026-08-20** (`FLUSH_MODE`, one-sided flushness, `witness/score_flush_reach.py`, stays `"both"`): H2/H3/H5 pass and **H4 RESOLVES THE CYCLE** — all three flags on returns the entry to MarginNote with MN **0.8947**, RH 1.0000, MT **0.9000**, acc **0.9174** — but **H1 is 37/43** (`"reach"`; 33/43 for `"reach_right"`), so the chain's 23+20=43 was wrong, 6 rows are a FOURTH cause (**R2.2h**), and NEITHER R2.2g NOR R2.2f is adopted. The `"reach"` vs `"reach_right"` trade is recorded, not resolved: +4 consumer rows for acc 0.9174 → 0.9091 |
| R2.2h | 🔴 **THE MODAL EDGE IS ESTIMATED WITH A TOLERANCE HALF THE SIZE OF THE ONE IT IS TESTED WITH** (measured 2026-08-20, R2.2g) | `block_measure` takes the mode over row edges with `EDGE_TOL_P * p` (**13px** at pitch 38), and `classify` then decides in-block with `max(0.35p, 0.03 * measure)` (**27px**). The true scatter of justified line-starts in this edition is a SMEAR ~80px wide, so the mode lands in one bin of it and whole body lines fall outside the block: on leaf 403 **17 rows start left of the modal L against 17 within tolerance**; on 411 **20 rows end right of R**. Three of the 6 R2.2g survivors have NO in-block solid token at all; two more carry their scripture in a 496px segment that is out-of-block on the LEFT while a 78px tail is inside. ⚠️ **Two tolerances for one edge — the defect this module's header records having ALREADY paid for once** (continuity 0.312 → 0.176); the R2.1 fix unified them inside `classify` and never touched the estimator producing the edge. **Twelfth instance of the signature defect** | Deliverable: the edge estimator and the edge test must use ONE tolerance, which requires a fixed point (`classify`'s tolerance depends on the measure the estimator produces) — take a provisional mode at `0.35p`, derive a provisional measure, re-take the mode at `max(0.35p, 0.03 * measure)`. Acceptance: the 6 R2.2g survivors carry MainText, H1 reaches **43/43**, and the region gold's four numbers do NOT fall. ⚠️ Resolve WITH R2.2g and R2.2f — R2.2g's H4 showed these links are only scorable together. **C2** 🔴 **CANDIDATE 1 (`EDGE_FIXED_POINT`) SCORED 2026-08-20, `witness/score_edge_chain.py`, OFF**: J2–J6 PASS (out-of-block rows 403 **11 → 8** left and **3 → 0** right, 411 **14 → 10** right; zero abstentions; D1 **52 → 54** alone and **57/81** on the full chain, the highest recorded) but **J1 does not move: 37/43, the same number R2.2g reached without it**. The defect is real and is NOT the survivors' cause ⇒ **R2.2i** |
| R2.2i | 🔴 **A PRINTED LINE WHOSE BASELINE TILTS ACROSS THE MEASURE IS CUT INTO TWO ROWS, AND NEITHER HALF CAN BE A BODY ROW** (measured 2026-08-20, R2.2h) | `CR._rows_and_lines` clusters glyphs onto baselines; on a leaf with ~1° of scan tilt the right-hand end of a line sits 13–22px below its left-hand end, and the line is emitted as TWO rows — leaf 409 r36 `x 155..808` and r37 `x 689..1103` at **Δbaseline +15**, complementary in x and together spanning the whole measure. **Neither half reaches R3's `0.75 × measure`, so neither can be a body row however the block edge is estimated**, and the halves read with stray leading glyphs (`itwo`, `isthe`, `ranhom`). Census over the 20 leaves (`.scratch/r2/probe_split_census.py`): **22 split pairs in 1242 rows (1.8%)**, concentrated — 409 **8**, 419 **5**, 403 **3**, 411 **2**, singles on 407/410/415/417 — and **every leaf carrying an R2.2g/R2.2h survivor is on that list**, with 409 supplying 4 of the 6. Tilt is signed and consistent WITHIN a leaf (409 ≈ −20, 403 ≈ +14), i.e. per-leaf scan rotation, not noise. ⚠️ **The spike has carried a `deskew.py` throughout and no part of this chain consults it.** ⚠️ Found only after a SKEW hypothesis was tested and wrongly refuted by a probe that correlated over the corrupted row list itself — the defect diluted its own signal | Deliverable: rows are clustered against a per-leaf baseline MODEL rather than a horizontal band, or the leaf is deskewed before `_rows_and_lines`. Acceptance: split pairs go to **0** over the 20 leaves, the 6 R2.2g/R2.2h survivors carry MainText (J1 **43/43**), and the region gold's four numbers do NOT fall. ⚠️ This is UPSTREAM of R2.2e–R2.2h: it corrupts the row list every later rule reads. ⚠️ **BLOCKED BY R2.2j** — the gold addresses entries by ROW ORDINAL, so a row-clustering change renumbers every key and the score would collapse for reasons that have nothing to do with regions. **C2** |
| R2.2j | 🔴 **THE REGION GOLD ADDRESSES BY ROW ORDINAL, AND A ROW ORDINAL IS AN INDEX INTO A LIST THE CLUSTERER CONTROLS** (found 2026-08-20 while scoping R2.2i) | `gold/head_regions_*.json` carries `row` per entry and `score_head_regions.match`/`contain`/`ink_bind` all filter `t["row"] == e["row"]`. R2.2i changes how glyphs are clustered onto baselines, so it RENUMBERS ROWS — and every gold entry would then bind to the wrong row or to none, exactly as R2.1i measured when a splitter change renumbered token ordinals and MN recall fell **0.8947 → 0.5263 with nothing about any region having changed**. ⚠️ **This is R2.1i's defect ONE LEVEL UP**, and it was invisible until a candidate proposed to change the row list — the gold has been addressed this way since it was built, and every number this project has recorded against it assumed the clusterer was fixed. ⚠️ The gold ALREADY carries a band-independent address (`y0f`/`y1f` page fractions, added at R2.2c) which no scorer reads | Deliverable: bind gold entries to tokens by **y-band overlap** (`y0f`/`y1f` against the token's row band) rather than by row ordinal, with the addressing failure reported SEPARATELY from the region score — the discipline `score_argument_region.best_overlap` already follows. Acceptance: the four gold numbers are EXACTLY unmoved under the re-keyed scorer with the row clusterer unchanged (the control that proves the re-key is not itself a change), and non-zero addressing failures are reported. ⚠️ **PREREQUISITE for R2.2i**: a row-clustering change cannot be scored on a gold whose address it moves. **C1** |
| R2.2k | 🔴 **THE ROW CLUSTERER CHAINS AGAINST A RUNNING MEDIAN AND WALKS UP THE TILT ONTO THE NEXT BASELINE** (found 2026-08-20, R2.2i candidate 1) | `CR._rows_and_lines` appends a glyph when it lies within `ROW_TOL_P * p` of the **running median of the row being built**, and appending then MOVES that median. On a tilted leaf the median creeps with each glyph, so the row walks diagonally off its own baseline and onto the one below, emitting rows that cross several printed lines. ⚠️ **This is the OPPOSITE failure to R2.2i** — R2.2i cuts one line into two, R2.2k merges parts of many into one — and the two coexist on the same leaf, which is why the row count is simultaneously too HIGH (1242 against 827 printed lines) and contains rows spanning more than one line. 🔴 **It is what corrupted four of the five slope instruments**: a least-squares fit over rows spanning ≥0.75 of the measure returned **+0.030 with IQR +0.0262..+0.0322** on leaf 409, a slope at which no whole line could have survived clustering at all — the fitted objects were diagonal chains and their apparent slope is one pitch per span, i.e. the alias. ⚠️ **A tight interval on a circular instrument**; precision is not independence. Distinct from R2.2i: a correct per-leaf slope does not remove it, because the chaining rule is unchanged by straightening the coordinate | Deliverable: cluster against a FIXED baseline estimate per row rather than a running median that the row's own members move — e.g. seed from the strip line count and assign each glyph to its nearest seeded baseline. Acceptance: no row spans more than one printed line, verified against the strip line count of `probe_r22i_linecount.py`, and the four gold numbers do NOT fall. ⚠️ Resolve WITH R2.2i — candidate 3's named risk records that a correct `s` may not be sufficient while this stands. **C2** |
| ~~R2.2l~~ ✅ **RESOLVED 2026-08-21** (see the R2.2l RESULT §; guard exits 0, four gold numbers unmoved) | 🔴 **THE ADOPTED `ink2d` ADDRESSING LOSES A TOKEN WITHOUT REPORTING IT — A REGRESSION IN THE ONLY CHANGE ADOPTED ON 2026-08-20** (found 2026-08-20, running the suite after R2.2j) | `witness/test_region_gold_addressing.py` is a **GUARD (must exit 0)** and it now **exits 1**. It asserts the accounting invariant `lost <= collisions + orphans`: every entry that stops being scored must be reported as one or the other. Under the **R2.1h-quantile splitter** the adopted path gives **lost 27, accounted 26 (coll 5 + orph 21) — 1 token lost silently**. Run under all three settings in one process: **`ordinal` exits 0, `ink2d` exits 1**; the other two perturbations (`coarse x1.6`, `fine x0.4`) balance exactly, so it is one entry on one axis, not a broken scheme. ⚠️ **R2.2j's own criteria (L1–L4, M1–M3) perturb the ROW CLUSTERER; this guard perturbs the SPLITTER**, an axis none of them touched — and the guard is PRE-EXISTING, written for R2.1i. ⚠️ **The regression violates R2.2j's own stated deliverable**, which was to report addressing failure SEPARATELY from the region score; the adoption satisfies its criteria and breaks its principle. ⚠️ **`match` is NOT the leak** — its three outcomes are exhaustive, so `bound + coll + orph = len(entries)` identically; the drop is downstream in the `contain` / `ink_bind` path. ⚠️ **NOT to be fixed by reverting to `ordinal`**: M1 showed the ordinal address collapses under a pure renaming (acc 0.4667, 90 of 121 orphaned), so reverting would trade a correct scheme for a green suite | Deliverable: find the unreported drop in the `contain`/`ink_bind` path under `ink2d` and report it as a collision or an orphan. Acceptance: the guard exits **0** under `ink2d` with the four gold numbers unmoved, and R2.2j's L1–L4 re-run clean. ⚠️ **BLOCKS the suite** — the verification standard is RED until this closes, and that is the correct state. **C1** |
| R2.2m | 🔴 **THE CONTAINMENT PATH DROPS OBSERVATIONS WITH THE SAME UNCOUNTED IDIOM R2.2l WAS** (found 2026-08-21, fixing R2.2l) | `score_head_regions.main` builds `cpairs` as `[(g, pr) for g, pr, _e, t in cobs if id(t) not in cexcl]` — the containment observations are filtered by the ambiguous-entry exclusion set **with no counter and no print**, exactly the idiom that made R2.2l invisible in the `pairs` path. The reported containment numbers (`c_acc`, `c_obs`, `c_orph`) can therefore understate silently. ⚠️ **No guard fails today**: nothing asserts an accounting invariant over `c_obs`, and R2.1j containment is a REFUTED binding kept only for reporting — which is precisely why it is the sort of thing that sits unnoticed. ⚠️ Note the accounting is NOT 1:1 there: `contain` may emit several observations per entry (one per hit token), so the count is over OBSERVATIONS, not entries, and a naive copy of R2.2l's fix would mis-state it | Deliverable: count and print the `cexcl` drops as R2.2l does for `ambcoll`, in observation units, and extend `test_region_gold_addressing` with an accounting clause over `c_obs` so the invariant has a consumer. Acceptance: the guard still exits 0, the containment numbers are unmoved or their change is explained by the newly-counted drops, and the four gold numbers do NOT fall. **C1** |
| R11.2d | 🔴 **THE OPEN REGISTER'S PARSER CANNOT SEE A LETTER-SUFFIXED STEP ID, SO SUCH A STEP SILENTLY LEAVES THE REGISTER** (found 2026-08-20 while registering R2.2f/R2.2g) | `audit_prereq_ceilings.STEP_RE` is `R\d+(\.\d+)*[a-z]?(-\d+)?` — the suffix branch is **digits only**, so `R2.2e-c` matches as `R2.2e`, collides with the existing id and is DEDUPED AWAY. The register would have read 66 ids while the audit counted **64**, and §0.6 makes the register precedence-bearing. ⚠️ Same family as R11.2c: an id convention the enforcing parser cannot read. **Worked around at the call site** by naming the steps R2.2f and R2.2g — ids the parser can see — exactly as R11.2c worded a claim around the digit-only fraction regex | Deliverable: the parser accepts letter suffixes, **or refuses an id it cannot parse** rather than silently folding it into another. ⚠️ Silent folding is the worst of the three behaviours: the step does not appear as missing, it appears as ALREADY THERE. **C1** |
##### R2.2d PRE-REGISTRATION — written 2026-08-18 BEFORE the discriminator was built or measured

⚠️ **Written first and not edited afterwards**, on the same terms as R2.2b's block above — whose `N`
the book then refuted, which is the outcome this discipline exists to make possible.

**THE DISCRIMINATOR MUST BE A PROPERTY OF THE SETTING, NOT A POSITION.** "Whatever lies between the
ChapterHead and the first verse" would be *definitionally* correct and *diagnostically worthless*:
it presumes the boundary it is supposed to find, and it cannot fire on a leaf whose chapter head was
missed. The book's own distinction is a **FOUNT**: the argument is set in **ITALIC**, the scripture
in roman, at the same measure. So the named candidate is **SLANT, measured from glyph geometry per
row, relative to the page's OWN modal slant** — a page-relative measure, so a leaf photographed
askew does not read as all-italic. ⚠️ Anti-circularity again (Sir's ruling): *italic* is a word the
BOOK uses about itself; *"the block that confuses the head reader"* is a word the ERROR uses.

⚠️ **The candidate may be refuted, and a refutation is a result, not a failure** — R2.1k has three
recorded. If slant does not separate, the finding is reported with the numbers and the next
candidate named; what may NOT happen is falling back on the positional rule because it scores well.

**PRE-REGISTERED ACCEPTANCE.** D1–D4 together; any one failing means ARGUMENT is not adopted and
`region_head` keeps its four labels, with the failure reported as the finding.

| | criterion | bar |
|---|---|---|
| **D1** | RECALL — every gold ARGUMENT row is labelled ARGUMENT | **all of them**. A partial rule leaves the head reader returning an argument on the leaves it misses, which is the defect unfixed |
| **D2** | PRECISION — no non-argument row anywhere in the window is labelled ARGUMENT | **0 false positives over all 20 leaves**. 16 of the 20 carry no argument at all and are the real test: a rule that paints scripture as argument destroys the reading it was built to protect |
| **D3** | NO REGRESSION on the region gold's existing numbers: accuracy **0.8760**, RH **1.0000**, MN **0.8947**, MT **0.8375** | none may FALL. ⚠️ The 121-token gold contains **no** argument rows, so it cannot reward this change — it can only detect collateral damage, which is exactly what it is for here |
| **D4** | THE CONSUMER — on every chapter-opening leaf the head reader's first MainText token is the **VERSE**, not the argument | **all such leaves**. R2.2b/A1's lesson: a region rule nobody reads is the defect, so the acceptance runs the consumer |

⚠️ **NON-CRITERION: the continuity rate**, on the same terms as R2.2b. Any number it produces here is
a diagnostic and may not be quoted as this step's result.

⚠️ **A NEW GOLD IS REQUIRED AND ITS ABSENCE IS THE POINT.** Measured: all four chapter heads in the
window (leaves **403, 411, 414, 416**) sit at detected rows 3, 2, 6 and 12, so **every argument row
lies OUTSIDE the region gold's 3-row window** — that gold cannot score D1 or D2 at any bar. The new
file is scoped like GOLD-FIRSTBODY and must not disturb the 121-token gold's denominator.

##### 🔴 R2.2d RESULT 2026-08-18 — the rule WORKS on the defect and is NOT ADOPTED

**`witness/score_argument_region.py` · `region_head` R3b + `ARGUMENT` · `CR.row_slant` /
`page_slant_mode` · `witness/gold/argument_rows_OT1-1609-B_400-419.json`**

| | | |
|---|---|---|
| **D3** NO REGRESSION | ✅ **PASS, EXACTLY** | acc **0.8760**, RH **1.0000**, MN **0.8947**, MT **0.8375** — *identical to four decimals* with the rule on. A fifth region type was added and no recorded number moved |
| **D4** CONSUMER | 🔴 **FAIL, but 46 → 2** | tokens on gold argument rows still typed MainText fall from **46/89 to 2/89**. The defect is 96% removed and the bar is 0 |
| **D1** RECALL | 🔴 **FAIL** | **16/24** gold argument rows carry an ARGUMENT token |
| **D2** PRECISION | 🔴 **FAIL** | **2** false positives on the 4 row-by-row adjudicated leaves |

**SLANT SEPARATES, MEASURED OVER 520 ROWS**: argument rows **12–18°** (median 14), everything else
median **0°**. The populations do not overlap. The discriminator is sound; what fails is its grain
and the gold's coverage.

🔴 **THE ROW-LEVEL FOUNT TEST WAS BUILT, MEASURED AND REFUTED — and it is `region_head`'s OWN
FOUNDING OBSERVATION RETURNING ON A NEW AXIS.** This module opens by establishing that *"a row is
NOT homogeneous and region typing here must be per TOKEN"*, because a headline band carries a
running head flanked by side-notes. **I then rebuilt exactly that assumption in the fount test.**
This edition sets its side-notes in ITALIC beside roman scripture, so a row-level slant is an
AVERAGE: leaf 405's verse `† How beautiful are thy tabernacles ô Iacob` shares its baseline with the
note `Manie do prophecie, and cast out diuels` and averages to 8° — firing the rule on scripture.
Leaves 403, 406 and 412 fail identically. ⇒ **A row is not homogeneous in FOUNT either.** Moving the
test to `region_segments` (the R2.1h primitive that cuts a row where a gap exceeds the line pitch)
cleared 5 of those false positives; `in_block` cleared the rest.

⚠️ **AND GATING THE FOUNT TEST ON `body_rows` WAS A SECOND VERSION OF THE SAME ERROR.** It reached
only **9 of 24** gold rows: an argument's short last line (`Collection.`, `and the people.`) and its
indented lines fail R3's span/flush test, so they never reached the fount test at all. **A fount is
a property of the setting, not of whether a line happens to be justified** — conditioning it on
justification imports R3's question into a rule that is not asking it. Ungated: recall **9 → 16**,
D3 unchanged, and **2 new false positives** on in-block italic that is not an argument. Both numbers
are reported; neither variant passes, and the bar is not moved to fit either.

🔴 **THE GOLD IS THE BINDING CONSTRAINT, AND THE RULE IS WHAT PROVED IT.** Building the argument gold
by hand found four chapter openings. **The slant census then found a fifth — leaf 406's `CHAP. XXV.`
with a three-line argument — that the recogniser's whole-page census ALSO missed** (it misread the
head). A whole-page sweep now puts argument blocks on **~10 of the 20 leaves**; the gold covers 4.
⇒ **D2 is measured on a subset**, and the 46 further rows the rule labels ARGUMENT on unlabelled
leaves are reported as **UNADJUDICATED — truth unknown, counted neither as correct nor as errors.**
Counting them either way would misstate the rule, so they are named instead.

**NEXT, in order**: (1) extend GOLD-ARGUMENT to every chapter opening in the window — the census and
the CHAP. census corroborate each other on 9 of 12 leaves, so the enumeration is nearly complete;
(2) recover the short argument segments D1 misses without re-admitting the side-note false positives
— they are below `ARGUMENT_MIN_COMPONENTS`, and the fix is likely CONTIGUITY (a short segment
between two italic segments of one block is italic) rather than a lower component floor;
(3) only then re-run D1–D4. **`ARGUMENT_RULE` stays `False` throughout.**

##### ✅ R2.2d STEP (1) DONE 2026-08-19 — GOLD-ARGUMENT covers EVERY chapter opening; D2 is no longer a subset

**`witness/build_argument_gold.py` (NEW, tracked — its `BLOCKS`/`NEGATIVES` tables ARE the
adjudication) · `witness/gold/argument_rows_OT1-1609-B_400-419.json` REWRITTEN: 24 → 81 argument
rows over 4 → 10 chapter openings, plus 15 rows adjudicated NOT-ARGUMENT · `score_argument_region.py`
re-keyed to overlap addressing.** `ARGUMENT_RULE` **stays `False`** — nothing here adopts the rule.

| | before (4-leaf gold) | after (10-leaf gold) |
|---|---|---|
| **D3** no regression | ✅ PASS exactly | ✅ **PASS EXACTLY, again** — 0.8760 / RH 1.0000 / MN 0.8947 / MT 0.8375. The gold TRIPLED and no recorded number moved |
| **D1** recall | 🔴 16/24 | 🔴 **52/81** |
| **D2** precision | 🔴 2 FPs on 4 leaves | 🔴 **13 FPs, WHOLE WINDOW** |
| **D4** consumer | 🔴 2/89 MainText | 🔴 **3/327** MainText (46 with the rule off) |
| unadjudicated | **46 rows** | **0** |

⚠️ **D2 got numerically WORSE and that is the step working.** 2-of-4-leaves was a subset result that
flattered the rule; 13 false positives over the whole window is the same rule finally being seen. No
bar moved to absorb it.

**THE ENUMERATION TOOK THREE CENSUSES, AND EVERY DISAGREEMENT BETWEEN THEM WAS REAL.** A CHAP-head
census over the whole page (the earlier one read only a leaf's first 8 rows), the row-slant census,
and — the one that was missing — **the RULE ITSELF at a widened net** (`probe_seg_census_all.py`,
slant ≥ 6 / ≥ 6 components against the shipping 8 / 8).

* 🔴 **A ROW-LEVEL CENSUS CANNOT PROVE ABSENCE, and "this leaf carries no argument" is exactly a
  claim of absence.** The rule fires per SEGMENT, so a row averaging upright can still hold an
  italic run. ⚠️ The first attempt hand-rolled the segment test and returned **25 candidates, all
  marginal notes the rule could never emit** — the copy had dropped `in_block`. Running the rule
  itself and widening its two constants makes the enumerator's output equal to what the rule can
  emit, by construction, rather than by a resemblance argument.
* **406** slant-only ⇒ a TRUE chapter opening whose head row *reads as its own side-note*
  (`ap: 4. v. CHAXXV.`), which is why a text census cannot see it.
* **410** head-only ⇒ `CHAP` at the page FOOT is the **CATCHWORD** for leaf 411. No chapter opens.
* **417** two heads ⇒ `CHAP. XXX.` at r33 heads the **ANNOTATIONS**; the real head is `CHAP. XXXI.`.

🔴 **FOUNT IS REGION-DEPENDENT AND THE RULE DOES NOT KNOW IT — a limit no threshold can reach.** In
the body, italic marks the ARGUMENT and roman the scripture. Inside leaf 417's ANNOTATIONS the
relation **INVERTS**: roman is the commentary and the italic is **QUOTED SCRIPTURE** (`( Leuit. 23.
v. 29. ) Euerie soule that is not afflicted … shal perish out of his people.`). Those 3 rows are 3 of
the 13 false positives, and **no setting of `ARGUMENT_SLANT_MIN` can separate them** — an italic
fount test alone cannot tell an argument from an annotation's quotation. ⇒ ANNOTATIONS is a region
the taxonomy lacks, in the same way ARGUMENT was. The other **11 of 13** are marginal italic — the
edition sets its patristic citations in italic (`S. Hierom. de mans.`, `S. Greg. li. 33. c. 17.
Moral.`, `Theodoret. q. 40. Procopius.`) — falling just inside `in_block`'s edge tolerance.

🔴 **THE SCORER WAS ADDRESSING THE GOLD BY EXACT FLOAT EQUALITY, AND IT FAILED ON ITS FIRST RUN WITH
THE LARGER GOLD.** The gold stores `round(y, 6)`; the scorer compared `round(that, 4)` against
`round(y, 4)` recomputed from the page. Leaf 417 r51 sits at **0.66504975**, which rounds *directly*
to `0.6650` but rounds *through 6 dp* to `0.66505 → 0.6651`. **One row in 81** fell down that crack —
and the old code would have counted it as a **RECALL MISS**, the rule blamed for an arithmetic
defect. ⚠️ The gold's own `address` note already prescribed the fix (*"score by page-fraction
overlap, never by an equality"*) — **the rule was right and the thing reading it was not: the
signature defect, in the scorer this time.** Now matched by **BEST overlap** (not *any*: curvature
makes 39/140 consecutive row-pairs overlap >50%, so *any* would let a neighbour satisfy a gold row
and inflate D1), with **ADDRESSING FAILURE** and **ADDRESSING COLLISION** reported SEPARATELY from
D1 — both **0** on the current gold. The re-keyed run also showed 417 r51 was a genuine **miss**, so
the crack had been concealing a failure, not a pass.

**D1's 29 MISSES SPLIT BY MEASURED CAUSE, and only one population is the fount's problem:**

| population | n | cause |
|---|---|---|
| fragment rows below `ARGUMENT_MIN_COMPONENTS` | **20** | the contiguity case already named as step (2) |
| full rows where the segment DOES fire | **6** | 🔴 **not a fount failure at all** — see R2.2e |
| full rows whose largest segment is 6–8 components | **3** | the component floor again, at row scale |

**NEXT**: step (2) unchanged — recover the 20 short segments by CONTIGUITY, not by lowering the
component floor, which would re-admit the marginal-italic false positives measured above. ⚠️ **D2
now has a floor of 3 that contiguity cannot touch**: the ANNOTATIONS quotations need a region, not a
threshold.

##### 🔴 R2.2e NEW 2026-08-19 — 49 rows are SWALLOWED WHOLE into one token and typed MarginNote, 44 of them SCRIPTURE

**Found while diagnosing D1's full-row misses; measured with `ARGUMENT_RULE` OFF, i.e. this is the
SHIPPING pipeline's behaviour today and R2.2d is not in the picture.**
`.scratch/r2/probe_unsplit_rows.py`.

The tokeniser sometimes emits **ONE token covering an entire printed line** — leaf 412 r33 is 63
glyphs spanning `l=56..r=1215`, 90% of the row. `in_block` tests `l < L` or `r > R`, so **a token
that spans the measure NECESSARILY fails it** and is labelled **MarginNote**. An entire line of
scripture is typed as marginalia: `† And Moyses referred their people`, `the familie of the
Noemanites. † The`, and 42 more.

* **49 rows over the 20 leaves; 44 are ordinary body text**, 5 inside an argument block.
* 🔴 **TWO SPLITTERS DISAGREE ABOUT ONE ROW AND THE COARSER ONE DECIDES THE LABEL.**
  `region_segments` cuts leaf 412 r33 correctly into `n=10 @ 1°` (the roman side-note) + `n=53 @ 11°`
  (the argument), so the fount grain is right — but the token that carries the label is the whole
  row, already typed MarginNote before the fount test can matter. **A correct rule nothing reads:
  the signature defect, 10th instance**, and the first found in the SPLITTER/label handoff.
* ⚠️ **THE 121-TOKEN REGION GOLD CANNOT SEE ANY OF THIS** — it lives in the 3-row head band and
  these rows are mid-page. Same shape as the ARGUMENT fossil: the gold's blind spot and the defect
  sit in the same place. **So 0.8760 is not evidence against this.**
* Relation to existing steps: R2.1h fixed the `k=2` CAUSE of the blob and is still OPEN; this is the
  measured **residual population** after that fix, plus its consequence, which was not counted.
  R2.1k is the same handoff seen from R3's side (`MIN_GLYPHS` as a span estimator).
* **Deliverable**: `in_block` must not be decidable by a token the tokeniser failed to split — either
  the block test runs at `region_segments` grain, or a row-spanning token is split before labelling.
  **Acceptance**: the count of row-spanning out-of-block tokens goes to **0** on the 20 leaves with
  the region gold's four numbers NOT falling. **C2.**

##### R2.2e PRE-REGISTRATION — written 2026-08-20 BEFORE the candidate was built or measured

⚠️ **This block is written first ON PURPOSE and is not edited afterwards.** What the run produces is
recorded in the section BELOW it, and any criterion this block got wrong is reported as wrong rather
than amended. Same discipline as R2.2b and R2.2d.

**THE CANDIDATE, stated before it is tested: A TOKEN MAY NEVER SPAN A REGION GAP.** `region_segments`
already defines one — a gap wider than the line pitch is *not a word space, it is a run out to
another region* — and that rule is stated in the vocabulary of the BOOK, not of the error (Sir's
anti-circularity ruling). Whatever `split_fn` returns is therefore cut at those gaps before any
label is decided. ⚠️ It is a POST-CONDITION ON TOKENISATION, not a new splitter: it cannot merge
anything, only cut, and it leaves every token that already lies inside one segment untouched.

**MEASURED BASELINE, before any criterion** (`.scratch/r2/probe_region_gap_tokens.py`, rule OFF):
**142 tokens span a region gap, over 127 rows** — `MN` 66 · `CH` 39 · `MT` 37. ⚠️ **The blast radius
is far wider than the 49-row defect that raised this step, and it reaches every label.** The widest
gap inside a single token is **223px** where the same token's word spaces run ~3px, so these are not
close calls — but a change touching 127 rows may not be adopted on that ground alone.

| | criterion | bar |
|---|---|---|
| **E1** | THE DEFECT — no token spans a gap wider than the line pitch | **0** of the 142 |
| **E2** | NO REGRESSION on the 121-token region gold: acc **0.8760**, RH **1.0000**, MN **0.8947**, MT **0.8375** | none may FALL; orphan/unlabelled counts reported either way |
| **E3** | THE CONSUMER — of the 49 rows swallowed whole, the **44 that are not argument rows** must carry at least one **MainText** token instead of being typed MarginNote | **all 44** |
| **E4** | GOLD-ARGUMENT D1 recall (currently **52/81**) may not FALL; the **6** misses attributed to R2.2e are expected to clear | **>= 52**, and the number is reported |

**Adoption requires E1–E4 TOGETHER.** `region_head.REGION_GAP_TOKENS` stays `False` until they all
hold — turning it on silently would restate R2.1g's headline numbers under a rule that has not been
accepted, the same rule that keeps `chapter_model_derive` pinned OFF at net −6.

⚠️ **NON-CRITERION**: the continuity rate, on the same terms as R2.2b and R2.2d — it is a joint
measure over two readers and a scorer, so it cannot arbitrate a change to one of them.

⚠️ **NAMED RISK, so that it is not discovered as a surprise and reported as a success.** `CH` is 39 of
the 142: this edition sets `CHAP. XXVIII.` with wide spacing, so a chapter head may itself contain a
gap wider than the pitch and be cut in two. If that moves RunningHead or ChapterHead recall, **E2
fails and the candidate is refuted** — a head cut into two correct pieces is still a regression
against a gold that binds one span, and R2.1i is the step that exists because a splitter change
silently renumbered that gold. The converse must also be watched: `block_measure` takes L and R from
token edges, so cutting tokens can MOVE THE MEASURE and change R3 for rows this rule never touched.

##### 🔴 R2.2e RESULT 2026-08-20 — the candidate is REFUTED, and it refuted MY DIAGNOSIS with it

**`witness/score_region_gap_tokens.py` (NEW, exits 1) · `witness/build_region_gap_gold.py` (NEW) ·
`witness/gold/region_gap_rows_OT1-1609-B_400-419.json` (NEW, 49 rows) · `region_head.
REGION_GAP_TOKENS` + `_cut_at_region_gaps`, DEFAULT OFF.**

| | criterion | result |
|---|---|---|
| **E1** | no token spans a region gap | ✅ **PASS** — **142 → 0** |
| **E2** | no regression on the region gold | ✅ **PASS, EXACTLY** — 0.8760 / RH 1.0000 / MN 0.8947 / MT 0.8375, unmoved |
| **E3** | the swallowed body rows carry MainText | 🔴 **FAIL, 0 of 43. Not one row moved.** |
| **E4** | GOLD-ARGUMENT D1 may not fall | ✅ **PASS** — 52/81, unchanged |

⚠️ **E3's BAR WAS WRITTEN AS 44 AND THE MEASURED SET IS 43** — one of the 49 rows I had counted as
body is an argument row, established by page-fraction overlap against GOLD-ARGUMENT rather than by
my eye. The pre-registration is not edited; the criterion is reported as WRONG BY ONE. It does not
change the verdict: the result is 0.

🔴 **0-of-43 IS TOO CLEAN TO BE A RULE FAILING, AND IT WAS NOT ONE — IT IS MY DIAGNOSIS FAILING.**
Leaf 400 r46 is the counter-example: its 46-glyph token spans `l=238..r=1174` and is **byte-identical
with the rule on and off**, because IT CONTAINS NO REGION GAP. It is out of block for an entirely
different reason — the modal right edge is `R=1132` and the tolerance is 27px, so the line's ink ends
**42px past the edge** and R2 types a full line of scripture as a marginal note.

**THE 43 BODY ROWS, SPLIT BY MEASURED CAUSE** (`.scratch/r2/probe_e3_cause.py`):

| cause | n |
|---|---|
| **OVERSHOOT** — one continuous token, most of the measure, poking past L or R | **41** |
| BOTH overshoot and merge | 2 |
| **MERGED only** — the defect the candidate was built for | **0** |

**Their median share of the measure is 0.90, and many exceed 1.00** (1.03, 1.05, 1.06 — the token is
LONGER than the block). ⇒ 🔴 **THE REAL DEFECT IS THAT R2's BLOCK TEST HAS NO SIZE QUALIFICATION AT
ALL: it is a pure EDGE test, so a token spanning the whole measure is relabelled MarginNote by a
26–42px overshoot against a ~27px tolerance.** A marginal note in this edition is set in a narrow
column beside the measure — *a thing that spans the measure cannot be one.* The modal edge is a MODE
over many lines, so an individual justified line exceeding it is ORDINARY, not anomalous. Same family
as R2.1k: a threshold answering a question it was not built for.

**WHAT THE CANDIDATE ACTUALLY DID.** It removed a real and separate defect — 142 tokens spanning a
region gap, over 127 rows, at **zero cost on the region gold** (E2 exact). ⚠️ **It is still NOT
ADOPTED**, on the same rule that keeps R2.1h's quantile splitter and `chapter_model_derive` off: a
change that fails its own pre-registered bar is not adopted, however good its other numbers look.
`REGION_GAP_TOKENS` stays `False`. Its value is now as a **PRECONDITION** for the real fix — see
below, because the two rules interact and the interaction must be measured, not assumed.

##### R2.2e-b PRE-REGISTRATION — written 2026-08-20 BEFORE the second candidate was built or measured

⚠️ Written first ON PURPOSE and not edited afterwards. This is the SECOND candidate for one step; the
first is recorded above as refuted, and this block does not inherit its numbers.

**THE CANDIDATE: A TOKEN THAT SPANS THE MEASURE IS IN THE BLOCK, whatever it does at the edges.**
`in_block` becomes `not (l < L - tol or r > R + tol)` **OR** `(r - l) >= BODY_SPAN_M * measure` —
reusing R3's EXISTING constant (0.75) rather than minting a second one, because it is the same idea
("a justified line is FULL") and this project has already paid once for two tolerances on one edge.
⚠️ Nameable in the vocabulary of the BOOK (anti-circularity): marginalia is set in a NARROW COLUMN
BESIDE the measure, so a run of type that spans the measure is a line of the text block.

⚠️ **THE TWO RULES INTERACT AND THAT IS WHY BOTH ARE MEASURED.** A token merged across a region gap
(body + marginal note) ALSO spans the measure, so the span qualifier alone would call the merge
in-block and MASK the merge defect that E1 measured. The region-gap cut is therefore the
**precondition**: cut first, so that a token spanning the measure is genuinely ONE piece of setting.

| | criterion | bar |
|---|---|---|
| **F1** | THE CONSUMER — of the 43 swallowed body rows, each must carry at least one **MainText** token | **all 43** |
| **F2** | NO REGRESSION on the 121-token region gold: acc 0.8760, RH 1.0000, MN 0.8947, MT 0.8375 | none may FALL |
| **F3** | GOLD-ARGUMENT D1 recall (**52/81**) may not FALL | **>= 52**, number reported |
| **F4** | THE INTERACTION — F1/F2/F3 reported for the span qualifier ALONE and COMPOSED with the region-gap cut, and **the merge count (142 → ?) reported in both** | reported; a composition adopted only if it beats the qualifier alone on F1 **without** losing F2 |

**Adoption requires F1–F3 TOGETHER**, with F4 deciding WHICH of the two configurations is adopted.
`BLOCK_SPAN_QUALIFIES` stays `False` until then.

⚠️ **NAMED RISK.** The gold's MarginNote recall is 0.8947 over 19 entries; if any gold MN token spans
>= 0.75 of the measure it flips to in-block and **F2 fails**. That is the criterion doing its job —
a marginal note that spans three quarters of the measure would be evidence the constant is wrong,
not evidence the gold is.

##### 🔴 R2.2e-b RESULT 2026-08-20 — REFUTED on its bar, and it uncovered a defect the gold was RESTING ON

**`witness/score_block_span.py` (NEW, exits 1) · `region_head.BLOCK_SPAN_QUALIFIES`, DEFAULT OFF.**

| | criterion | qualifier ALONE | COMPOSED with the region-gap cut |
|---|---|---|---|
| **F1** | 43 swallowed body rows carry MainText | 🔴 **23/43** | 🔴 **23/43** |
| **F2** | region gold, none may fall | 🔴 **FAIL** — acc **0.8760 → 0.9174**, MT **0.8375 → 0.9125**, RH 1.0000, but **MN 0.8947 → 0.8421** | 🔴 same |
| **F3** | GOLD-ARGUMENT D1 >= 52 | ✅ **55/81** | ✅ **54/81** |
| **F4** | merges | 🔴 **142** (masked) | ✅ **0** |

⚠️ **THE HEADLINE NUMBER ROSE FURTHER THAN ANY CHANGE IN THIS PROJECT HAS MOVED IT — acc 0.8760 →
0.9174, MainText recall 0.8375 → 0.9125 — AND IT IS STILL NOT ADOPTED.** One MarginNote entry fell,
the bar says none may fall, and a rule that trades a labelled entry for a better average is precisely
what "no silent degradation" forbids. `BLOCK_SPAN_QUALIFIES` stays `False`.

✅ **F4 DID ITS JOB.** The qualifier ALONE leaves all **142** merged tokens in place and calls them
in-block — a merged token spans the measure too, so the qualifier MASKS the defect E1 measured.
Composed with the region-gap cut the count is **0** at identical F1/F2. ⇒ **the cut is a genuine
precondition, not a companion**, and had only one configuration been run this masking would have
been invisible.

🔴 **THE LOST MarginNote ENTRY EXONERATES THE CONSTANT AND CONVICTS SOMETHING ELSE.** The
pre-registration named the deciding evidence in advance: a gold MN token spanning >= 0.75 of the
measure would mean the constant is wrong. **It does not.** The entry is leaf 412 r2 `pinces are`, and
it is **142px wide against a 1110px measure** — it cannot qualify and never did. What happened is
this, measured token by token:

| leaf 412 r2 | rule OFF | rule ON |
|---|---|---|
| `pinces are` (left note, 142px) | in_block **True**, label **MN** | in_block True, label **MT** |
| the body line (931px) | in_block **False**, label MN | in_block **True**, label MT |

The note was ALREADY inside the block bounds — on this leaf the marginal column and the measure are
contiguous, so the modal `L=48` sits LEFT of the note. It was labelled MarginNote **only because its
ROW was broken**: the row was not a body row, so nothing on it could be MainText. Repair the row and
**R4 labels EVERY in-block token on a body row MainText**, sweeping the note in with it.

⇒ 🔴 **R2.2f, NEW: R4 ASSIGNS BY ROW MEMBERSHIP, SO A MARGINAL NOTE SHARING A BASELINE WITH A BODY
LINE AND SITTING INSIDE THE BLOCK BOUNDS IS TYPED MainText.** This is `region_head`'s founding
observation — *a row is NOT homogeneous, so label per TOKEN* — returning on a THIRD axis. It already
holds for region (that is why labels are per token) and for FOUNT (R2.2d, measured); it does not yet
hold for the **row-to-token inheritance in R4 itself**.

⚠️ **AND THE GOLD'S MN 0.8947 WAS RESTING ON THE DEFECT.** That entry scored correct only because a
second defect was breaking its row. Two errors were cancelling, so the number looked stable — and the
first genuine repair exposed the second. ⚠️ **No repair of the swallowed rows can pass F2 until R4
labels per token**, because every such repair turns a broken row into a body row and sweeps in
whatever notes lie inside the bounds. That is a PREREQUISITE relation, not a coincidence.

**F1's 20 REMAINING MISSES ARE A THIRD LINK.** They now come back labelled `CH`/`MN`, not MainText:
the rows are in-block but still fail **R3's flush test**, because a line that overshoots the modal
edge is not flush at that edge and its left end sits at a marginal note. ⇒ **R2.2g, NEW: R3's flush
test inherits the same modal-edge assumption R2 does.**

**⇒ R2.2e IS A CHAIN OF FOUR LINKS, NOT ONE TEST**, and this run measured which link each row hangs
on: tokenise (**0** of 43) → `in_block` edge test (**23** of 43, R2.2e-b) → R3 flush (**20** of 43,
R2.2e-d) → R4 row inheritance (the **1** MN entry, R2.2e-c). ⚠️ **A candidate that fixes one link and
reports the headline number is how a chain gets mistaken for a bug.** The three open links are
registered separately and each carries its own pre-registration. ⚠️ **The two ids in the line above
were written `R2.2e-c` / `R2.2e-d` and are the steps now registered as `R2.2f` / `R2.2g`** — renamed
the same day because the OPEN register's parser folds a letter suffix away silently (R11.2d). The
mapping is recorded rather than the numbers rewritten: `R2.2e-c` = R4 row inheritance = **R2.2f**;
`R2.2e-d` = R3's flush test = **R2.2g**.

##### R2.2f PRE-REGISTRATION — written 2026-08-20 BEFORE the candidate was built or measured

⚠️ Written first ON PURPOSE and not edited afterwards. R2.2f is the **PREREQUISITE** link of the
R2.2e chain, not a peer of it: every repair of a swallowed row turns a broken row into a body row, and
R4 then sweeps whatever lies inside the block bounds on that baseline into MainText. So no candidate
for the other links can pass its own F2 until this one holds. It is measured **with the span
qualifier ON**, i.e. in the configuration that failed F2, because that is the configuration whose
failure it must explain.

**THE CANDIDATE: R4 LABELS PER REGION SEGMENT, NOT PER ROW.** Today R4 reads *in a body row, every
in-block token is MainText*. It becomes *in a body row, an in-block token is MainText iff it lies in a
**region segment that is itself a body segment***, where a body segment is one meeting R3's own test —
span `>= BODY_SPAN_M * measure` and flush at `L` or at `R`, the same two clauses and the same
constants R3 already uses. A token in any other segment of that row falls through to R5 exactly as it
would in a non-body row.

⚠️ **Nameable in the vocabulary of the BOOK** (anti-circularity): this edition sets marginalia in a
narrow column BESIDE the measure, separated from the text block by a run wider than the line pitch.
`CR.region_segments` is that primitive and is already relied on by R2.1h, R2.2d and `band_word_gap` —
no new threshold is minted here. Computed on GLYPH BOXES, so no splitter can move it.

⚠️ **THE RULE MAY ONLY DEMOTE, AND NEVER ON A ROW IT CANNOT READ.** If NO segment of a body row
qualifies, the row keeps today's behaviour and every in-block token stays MainText. A row can qualify
under R3's token-union span while no single segment does, and stripping MainText from such a row would
be this rule deciding a question it was not asked. The count of rows taking that fallback is REPORTED
(G5) — a fallback that is not counted is how a rule's reach stops being knowable.

| | criterion | bar |
|---|---|---|
| **G1** | THE ENTRY — leaf 412 r2's note `pinces are` (142px against a 1110px measure), the one gold entry the span qualifier flipped, must come back **MarginNote** with the qualifier ON | **MN**, and its label printed in every configuration |
| **G2** | THE BAR R2.2e-b FAILED — with the span qualifier ON, the region gold must reach **MN >= 0.8947** while acc, RH and MT do not fall below the qualifier-ON numbers already measured (**acc 0.9174 · RH 1.0000 · MT 0.9125**) | all four |
| **G3** | NO REGRESSION ON THE SHIPPED PIPELINE — with the span qualifier OFF (both flags off, i.e. what ships today), the four gold numbers **0.8760 / 1.0000 / 0.8947 / 0.8375** must be EXACTLY unmoved | exact |
| **G4** | THE CONSUMER — the swallowed-body-row count must not fall below the **23/43** the qualifier alone reached; per-token R4 must not cost the rows the qualifier gained | **>= 23**, number reported |
| **G5** | REACH — rows where the rule DEMOTED at least one token, and rows that took the no-qualifying-segment fallback, both reported | reported |

**Adoption requires G1–G4 TOGETHER.** `R4_PER_SEGMENT` stays `False` until then. ⚠️ Passing G1–G4
adopts R2.2f **only**; it does NOT adopt `BLOCK_SPAN_QUALIFIES`, whose own F1 bar (43/43) is a
different link of the chain and is not reached by this rule.

⚠️ **NAMED RISK, and it is the mirror of R2.2e-b's.** A justified line can carry a word space wider
than the line pitch — this edition's justification is loose — and such a line would cut into two
segments, neither spanning 0.75 of the measure. Under G5's fallback that row keeps its labels, so the
visible cost is not a lost row but a rule with no reach: **if the demotion count is 1 (the gold entry
alone) the rule is fitted to its own witness**, and that reads as a failure of the mechanism whatever
G1–G4 say. The demotion count is therefore reported, not just the bars.

##### 🔴 R2.2f RESULT 2026-08-20 — REFUTED, and it REVERSES the prerequisite direction the register asserts

**`witness/score_r4_segment.py` (NEW, exits 1) · `region_head.R4_PER_SEGMENT`, DEFAULT OFF.**
Log `.scratch/r2/r4seg-20260820b.log`.

| | criterion | bar | result |
|---|---|---|---|
| **G1** | leaf 412 r2 `pinces are` → MarginNote, qualifier ON | MN | 🔴 **MT** — the rule never reached the row |
| **G2** | MN >= 0.8947 · acc/RH/MT >= 0.9174/1.0000/0.9125 | all four | 🔴 **MN 0.8421**, exactly where R2.2e-b left it (acc 0.9174 · RH 1.0000 · MT 0.9125 all held) |
| **G3** | shipped pipeline unmoved | exact | ✅ per-segment ALONE **0.8760 / 1.0000 / 0.8947 / 0.8375**, exact; baseline exact |
| **G4** | consumer >= 23/43 | >= 23 | ✅ **23/43**, D1 **55/81** |
| **G5** | reach | reported | **35 rows demoted**, 160 on the fallback (180 with the qualifier on) |

**1. THE RULE WORKS AND CANNOT REACH ITS OWN WITNESS.** G5 was written to catch a rule fitted to the
single entry that motivated it — *"if the demotion count is 1 the rule is fitted to its own witness."*
It demotes **35 rows**, overwhelmingly left-margin side-notes at `l≈80–290` sharing a body baseline,
and the shipped four numbers are EXACTLY unmoved (G3), so per-token R4 is doing real work at no cost.
It fails on the one row it was built for.

**2. WHY, IN ONE LINE OF THE LOG.** Leaf 412 r2 against `L=39 R=1149 measure=1110 flush_tol=33
span_bar=832`:

| segment | span | flush |
|---|---|---|
| `l=31 r=173` (the note `pinces are`) | 142 — **short** | dL=**8** — FLUSH |
| `l=263 r=1194` (the body line) | 931 — **FULL** | dR=**45** — **NOT FLUSH** |

The body segment is full but overshoots the modal right edge by **45px against a 33px tolerance**. So
NO segment qualifies, the row takes G5's fallback, and the note keeps MainText. ⚠️ **That 12px is
R2.2g.** The overshoot that makes a justified line fail the flush test is the same modal-edge
assumption R2.2g names — and note the second row of the table: the marginal note is FLUSH TO `L`,
which is leaf 412's measure contamination (this module's header: *leaf 412 measures L=40*) still
visible in the geometry.

**3. ⇒ THE PREREQUISITE DIRECTION IN THE REGISTER IS BACKWARDS, AND THE CHAIN HAS A CYCLE.** R2.2f is
registered as *"PREREQUISITE for R2.2e-b and R2.2g"*. Measured: **R2.2g is the prerequisite for
R2.2f.** A body segment that overshoots the modal edge is not identifiable as a body segment, so
per-token R4 cannot fire on exactly the rows that need it. Both statements are true at once — every
repair of a swallowed row does sweep notes into MainText (that is why R2.2f exists), AND R2.2f cannot
reach those rows until the flush test stops treating an overshoot as disqualifying. **Neither link
can be scored to its bar while the other is open**, so R2.2g goes first and R2.2f is re-scored after
it, unchanged. The register rows for both are corrected to say so.

**4. CORROBORATION NOBODY DESIGNED IN.** The fallback count moves **160 → 180** when the span
qualifier is switched on: 20 rows become body rows and immediately land on the fallback. **20** is
the count the chain already attributes to R3's flush test (20 of 43). Two independently-derived
numbers naming the same rows from opposite sides.

**5. 🔴 AND A DEFECT IN MY OWN SCORER, CAUGHT BY A CRITERION THAT CANNOT MOVE.** The first run
(`.scratch/r2/r4seg-20260820.log`) reported G3 as **MOVED on the BASELINE** — both flags off, the
identical code path, a configuration this candidate cannot reach. Cause: live floats compared to the
**4-decimal literals transcribed from this document** at `1e-9`. That is a criterion no run can ever
pass, and had G1 passed it would have read as a real regression against a bar that was only ever a
rounded transcription. Fixed to compare at the precision the bars are recorded at, and the same
latent fault was present in G2's comparisons. ⚠️ **It was only visible because one configuration in
the table was known-immovable.** A scorer whose configurations can all legitimately move has no such
control, which is the argument for printing the baseline row even when it is uninteresting.

##### R2.2g PRE-REGISTRATION — written 2026-08-20 BEFORE the candidate was built or measured

⚠️ Written first ON PURPOSE and not edited afterwards. R2.2g is run FIRST of the three open links
**on measurement, not on plan**: R2.2f was attempted first, as the register directed, and its
refutation showed the dependency runs the other way. This block therefore also carries the criterion
that tests the CHAIN (H4), because a link scored alone is how a cycle stays invisible.

**THE CANDIDATE: FLUSHNESS IS ONE-SIDED. A justified line REACHES its edge; overshooting it is not a
failure to be flush.** R3 today asks `abs(a - L) <= tol or abs(b - R) <= tol` — a SYMMETRIC WINDOW,
which refuses a line for having too MUCH ink at the edge as readily as too little. It becomes
`a <= L + tol` (flush left) or `b >= R - tol` (flush right): falling SHORT of the measure by more
than the tolerance is unjustified, running PAST it is not.

⚠️ **Nameable in the vocabulary of the BOOK** (anti-circularity): justification is a compositor
setting each line OUT TO the measure. A line's ink may exceed the modal edge by a hair of bearing,
by a hyphen, by a swash — the modal edge is a MODE OVER MANY LINES and no single line is obliged to
sit inside it. Same family as R2.1k and R2.2e-b: a threshold answering a question it was not built
for. The tolerance and both constants are R3's existing ones; nothing new is minted.

⚠️ **THE DANGEROUS HALF IS THE LEFT EDGE, and it is why both variants are measured.** `a <= L + tol`
is satisfied by ANY row whose leftmost ink lies in the left margin — which is every row carrying a
marginal note. Combined with R3's span clause such a row could be promoted to a body row, and the
running head is the region this project has already lost once to a promoted row (`SPAN_MODE = "ink"`,
RunningHead 1.0000 → 0.7500). `FLUSH_MODE` therefore has THREE settings and all three are reported:
`"both"` (today), `"reach"` (one-sided at both edges), `"reach_right"` (one-sided at R, unchanged
symmetric test at L).

| | criterion | bar |
|---|---|---|
| **H1** | THE CONSUMER, span qualifier ON — of the 43 swallowed body rows, each carries a **MainText** token. The chain predicts **23 + 20 = 43** | **all 43** |
| **H2** | NO REGRESSION on the region gold, reported for every `FLUSH_MODE` in both qualifier states, against the shipped **0.8760 / 1.0000 / 0.8947 / 0.8375** | acc, RH, MT may not fall; **MN is exempted ONLY to the 1 entry R2.2f owns**, and H4 must then recover it |
| **H3** | THE RUNNING HEAD — the named risk. RH recall with the flush change and the qualifier OFF | **1.0000**, no exception |
| **H4** | THE CHAIN — with `FLUSH_MODE` + `BLOCK_SPAN_QUALIFIES` + `R4_PER_SEGMENT` ALL ON: leaf 412 r2 `pinces are` is **MarginNote** and MN recall **>= 0.8947** | both, or the cycle is not resolved |
| **H5** | GOLD-ARGUMENT D1 recall (**52/81**, **55/81** with the qualifier on) may not FALL | **>= 52**, reported |

**Adoption of `FLUSH_MODE` requires H1 + H2 + H3 + H5.** H4 additionally decides whether **R2.2f** may
be adopted alongside it — R2.2f is re-scored by `score_r4_segment.py` UNCHANGED against its own
G1–G5, which is the point of leaving that scorer in the standard rather than deleting a refuted one.

⚠️ **NAMED RISK BEYOND H3.** If `"reach"` passes H1 by promoting rows that are not body rows at all,
H2's MainText recall is the number that should catch it — MT can rise while ACCURACY falls, because
mislabelled marginalia is scored somewhere. **Accuracy and MT are therefore both reported, and a
configuration that raises MT while lowering acc is NOT adopted** whatever H1 says.

##### 🔴 R2.2g RESULT 2026-08-20 — REFUTED on H1, but **H4 RESOLVES THE CYCLE** and the survivors are a FOURTH cause

**`witness/score_flush_reach.py` (NEW, exits 1) · `region_head.FLUSH_MODE`, DEFAULT `"both"`.**
Log `.scratch/r2/flushreach-20260820.log`.

| | criterion | `"reach"` | `"reach_right"` |
|---|---|---|---|
| **H1** | consumer, bar **43/43** | 🔴 **37/43** | 🔴 **33/43** |
| **H2** | acc/RH/MT not falling | ✅ 0.9174 / 1.0000 / 0.9125 | ✅ same |
| **H3** | RH, qualifier OFF | ✅ **1.0000** | ✅ **1.0000** |
| **H4** | THE CHAIN, all three flags ON | ✅ entry **MN**, MN **0.8947**, acc 0.9091, MT 0.8875 | ✅ entry **MN**, MN **0.8947**, acc **0.9174**, MT **0.9000** |
| **H5** | D1 | ✅ 52 off / 55 on | ✅ 52 off / 55 on |

**1. 🔴 THE CYCLE IS REAL AND IT RESOLVES — H4, the criterion R2.2f's refutation forced into being.**
With `FLUSH_MODE` + `BLOCK_SPAN_QUALIFIES` + `R4_PER_SEGMENT` all on, leaf 412 r2 `pinces are` returns
to **MarginNote** and MN recall recovers **0.8421 → 0.8947**, the shipped number, with RH holding
1.0000 and MainText **0.8375 → 0.9000**. ⚠️ **Each link scored alone reads as a regression; the three
together read as a repair.** No single-flag scorer in this project could have shown that, and two of
them (E1–E4, F1–F4) reported a refutation that was partly the OTHER links' doing.

**2. 🔴 BUT H1 IS 37/43, SO THE CHAIN'S OWN ARITHMETIC WAS WRONG.** The chain predicted 23 + 20 = 43.
One-sided flushness adds **14**, not 20. **6 rows survive**, and they come back `CH`/`MN` — still not
body rows. ⚠️ **Per §0.2 the step stays OPEN and BLOCKS**: neither `FLUSH_MODE` nor `R4_PER_SEGMENT`
is adopted, even though the three-flag configuration beats the shipped pipeline on every one of the
four gold numbers. A configuration that is better on every number it is scored on is exactly the
shape that gets adopted on a headline and audited later.

**3. THE NAMED LEFT-EDGE RISK MATERIALISED, AND IT IS MEASURABLE.** `"reach"` reaches 37 where
`"reach_right"` reaches 33 — and pays for it in the chain configuration, **acc 0.9091 vs 0.9174**
with MT 0.8875 vs 0.9000. Promoting rows on a left edge that any marginal note satisfies buys
consumer rows and loses accuracy, precisely as the pre-registration warned. `"reach_right"` is the
better-behaved variant on every gold number and the worse one on the consumer; **neither is adopted,
and the trade is recorded rather than resolved by preference.**

**4. ⇒ R2.2h, NEW: THE MODAL EDGE IS ESTIMATED WITH A DIFFERENT TOLERANCE THAN IT IS USED WITH.**
The 6 survivors are not flush failures at all. Probed (`.scratch/r2/probe_reach6.py`,
`probe_l409_measure.py`): three rows have **NO in-block solid token whatever** (leaf 403 r19, 409 r52,
411 r34 — `† And Moyſes referred their people`), and two more (409 r36, r44) have their body segment
**out of block on the LEFT** — row ink `155..808` against `L=200`, so the 496px segment carrying the
scripture is outside the block and only a 78px tail is inside. Then the distribution:

| leaf | modal L | rows within tol | **rows starting LEFT of L** | rows ending RIGHT of R |
|---|---|---|---|---|
| 403 | 192 | 17 | **17** | 9 |
| 409 | 200 | 19 | **12** | 12 |
| 411 | 193 | 20 | 9 | **20** |

**On leaf 403 as many rows start left of the modal edge as agree with it.** The left-edge histogram is
a SMEAR ~80px wide (bins 143/169/182/195/208/221 all populated), and the cause is exact:
`block_measure` takes the mode with `EDGE_TOL_P * p` = **13px**, while `classify` then tests in-block
with `max(0.35p, 0.03 * measure)` = **27px**. **The estimator's window is half the consumer's.** ⚠️
This is *two tolerances for one edge* — **the identical defect this module's header records having
paid for once already** (`edge_tol`/`flush_tol`, continuity 0.312 → 0.176) — surviving in the one
place the R2.1 fix did not reach, because that fix unified the two tolerances INSIDE `classify` and
left the estimator that produces the edge alone. **Twelfth instance of the signature defect.**

##### R2.2h PRE-REGISTRATION — written 2026-08-20 BEFORE the candidate was built or measured

⚠️ Written first ON PURPOSE and not edited afterwards. ⚠️ **THIS BLOCK ABANDONS THE ONE-LINK-AT-A-TIME
FORM, on evidence.** R2.2f and R2.2g were each scored alone, each was refuted alone, and R2.2g's H4
then showed the three together produce a repair on every gold number. A criterion set that varies one
flag cannot see a cycle, so the acceptance below is stated over the **FULL CHAIN** and the
single-flag numbers are reported as diagnosis, not as bars.

**THE CANDIDATE: ONE TOLERANCE FOR ONE EDGE, REACHED BY A FIXED POINT.** `block_measure` takes its
mode with `EDGE_TOL_P * p`; `classify` tests in-block with `max(0.35p, 0.03 * measure)`, which is
twice as wide at this edition's pitch. They become the same number by iterating: take a provisional
mode at `0.35p`, derive a provisional measure, re-take the mode at `max(0.35p, 0.03 * measure)`, and
repeat to a fixed point (cap the iterations and ABSTAIN rather than guess if it does not settle — R7).

⚠️ **Nameable in the vocabulary of the BOOK** (anti-circularity): the block edge is where the
compositor's lines start, and "how close is close enough to count as the same edge" is one question
about one page. Answering it one way to FIND the edge and another way to TEST membership is not two
facts about the book, it is one fact and one accident. ⚠️ **This is not a widened tolerance.** The
estimator's window rises to what the test already uses; nothing loosens the test itself, and if the
fixed point moves `L`/`R` far enough to change the measure, `MIN_EDGE_SUPPORT` still governs
abstention.

| | criterion | bar |
|---|---|---|
| **J1** | THE CONSUMER over the FULL CHAIN (`R2.2h` + `FLUSH_MODE` + span qualifier + per-segment R4): every one of the 43 swallowed body rows carries **MainText** | **43/43** — the bar R2.2g reached 37 of |
| **J2** | THE REGION GOLD over the full chain, against shipped **0.8760 / 1.0000 / 0.8947 / 0.8375** | **none may fall**, and acc must EXCEED 0.8760 |
| **J3** | THE RUNNING HEAD — RH recall with `R2.2h` alone, every other flag OFF | **1.0000**, no exception |
| **J4** | THE ESTIMATOR ITSELF — rows starting left of the modal `L` / ending right of `R`, per leaf, before and after. Leaf 403's **17 left-of-L against 17 within** must fall | reported, and the out-of-block row count must DROP on 403, 409 and 411 |
| **J5** | ABSTENTIONS — leaves where the fixed point fails to settle or edge support falls below `MIN_EDGE_SUPPORT` | **0**, or each is named and its leaf reported |
| **J6** | GOLD-ARGUMENT D1 (**52/81** shipped) may not fall | **>= 52**, reported |
| **J7** | ATTRIBUTION — J1/J2 reported for `R2.2h` ALONE and for each of the 4 flag combinations, so a repair cannot be credited to the wrong link | reported |

**Adoption of the CHAIN requires J1–J6 TOGETHER**, and adopts all four flags as ONE change or none of
them. ⚠️ `FLUSH_MODE`'s two candidate settings are BOTH carried through J1/J2/J7; the `"reach"` vs
`"reach_right"` trade R2.2g measured (+4 consumer rows for acc 0.9174 → 0.9091) is decided HERE, on
the full chain, by J2 first and J1 second — accuracy outranks the consumer count, because a promoted
row raises the consumer while corrupting the label.

⚠️ **NAMED RISK.** A wider estimator window can swallow the MARGINAL COLUMN into the block on leaves
where note and measure are contiguous — leaf 412 is the known one, and its `L=39` is already left of
a marginal note. If that happens `MN` falls and J2 fails; that would be evidence the fixed point
needs a support-weighted mode, not evidence the bar is wrong. ⚠️ **A SECOND, worse risk: the fixed
point may not be unique.** A wider window can move the mode, which widens the window further. J5 is
the criterion that exposes it, and a candidate that oscillates is REFUTED, not damped.

##### 🔴 R2.2h RESULT 2026-08-20 — J2–J6 PASS, **J1 does not move at all**, and that is the finding

**`witness/score_edge_chain.py` (NEW, exits 1) · `region_head.EDGE_FIXED_POINT`, DEFAULT OFF.**
Log `.scratch/r2/edgechain-20260820.log`.

| combination | acc | RH | MN | MT | consumer | D1 |
|---|---|---|---|---|---|---|
| shipped | 0.8760 | 1.0000 | 0.8947 | 0.8375 | 0/43 | 52/81 |
| **R2.2h ALONE** | 0.8760 | 1.0000 | 0.8947 | 0.8375 | **4/43** | **54/81** |
| h + reach | 0.8760 | 1.0000 | 0.8947 | 0.8375 | 4/43 | 54/81 |
| h + reach + span | 0.9174 | 1.0000 | 0.8421 | 0.9125 | 37/43 | 57/81 |
| **FULL CHAIN `reach`** | 0.9091 | 1.0000 | **0.8947** | 0.8875 | **37/43** | **57/81** |
| **FULL CHAIN `reach_right`** | **0.9174** | 1.0000 | **0.8947** | **0.9000** | 33/43 | **57/81** |

**J1 🔴 37/43 · J2 ✅ · J3 ✅ 1.0000 · J4 ✅ · J5 ✅ none · J6 ✅ 57/81 · J7 reported above.**

**1. THE FIX IS REAL AND TOO SMALL.** J4 passes: out-of-block rows drop on all three probed leaves
(403 **11 → 8** left and **3 → 0** right; 411 **14 → 10** right), the fixed point settles everywhere
(J5 zero abstentions), and R2.2h ALONE moves the consumer **0 → 4** and D1 **52 → 54** with the four
gold numbers EXACTLY unmoved. The full chain reaches **D1 57/81**, the highest this project has
recorded. **And J1 is 37/43 — the identical number R2.2g reached WITHOUT R2.2h.**

**2. ⚠️ THE SURVIVORS ARE THE SAME ROWS, SO THE FOURTH CAUSE IS NOT THE ESTIMATOR.** I diagnosed the
6 survivors as an estimator defect, built the estimator fix, and the estimator fix repaired 4
DIFFERENT rows while leaving the 6 where they were. ⚠️ **A repair that moves a number is not evidence
it touched the defect it was built for** — the E3 lesson, arriving from the other direction and
against a candidate I was confident in. R2.2h stands as a real defect with its own evidence (J4), and
it is NOT the reason those rows fail.

**3. WHAT THE SURVIVORS ACTUALLY LOOK LIKE.** Leaf 409's `itwo thouſand fiue hundred.† Theſe` has row
ink `155..808` against `L=200 R=1093`: its scripture sits in a **496px segment out-of-block on the
LEFT** while a 78px tail is inside, and `region_segments` finds NO gap wider than the pitch inside
that 496px run.

⚠️ **RESOLVED THE SAME DAY, AND THE FIRST ANSWER WAS A FALSE NEGATIVE.** I hypothesised PAGE SKEW and
tested it by correlating row index against row-left (`.scratch/r2/probe_skew.py`). It came back weak
and inconsistent in sign, WEAKEST on the three leaves carrying the survivors (403 −0.155, 409 −0.280,
411 +0.105), and I recorded skew as refuted. **It was refuted by an instrument sitting downstream of
the defect.** `.scratch/r2/probe_rowsplit.py` shows leaf 409 r36 `x 155..808` and r37 `x 689..1103`
at **Δbaseline +15** — under 0.6 pitch, horizontally complementary, together spanning the whole
measure. **One printed line is cut into TWO ROWS**, and the same pattern repeats at r34/r35, r42/r43,
r44/r45, r52/r53. Leaf 409 carries **82 rows** for a page of roughly 45 printed lines. So the row list
I correlated over was ALTERNATING LEFT-HALVES AND RIGHT-HALVES — the defect diluted the very
correlation that would have revealed it. ⚠️ **A negative result is only as good as the instrument's
independence from the thing under test**, and this one had none. ⇒ **R2.2i, NEW.**

**4. THE FLUSH_MODE TRADE, DECIDED BY J2 AS PRE-REGISTERED.** `reach_right` is the better
configuration — acc **0.9174 vs 0.9091**, MT **0.9000 vs 0.8875**, same MN and RH — at 33/43 against
37/43 on the consumer. Accuracy outranks the consumer count, so `reach_right` would be the adopted
setting **if the chain were adopted, which it is not**: J1's bar is all 43 and the chain reaches 37.
⚠️ **Four flags now sit OFF while a configuration exists that beats the shipped pipeline on every one
of the four gold numbers and takes D1 from 52 to 57.** That is uncomfortable and it is correct: §0.2's
bar is the consumer, and the consumer is what still fails.

##### R2.2j PRE-REGISTRATION — written 2026-08-20 BEFORE the re-key was built or measured

⚠️ Written first ON PURPOSE and not edited afterwards. R2.2j is an INSTRUMENT change, not a rule
change, and it carries the strictest possible bar for that reason: **a re-keyed scorer that moves any
number has changed the measurement, and every figure this project has recorded against this gold
would become incomparable.**

**THE CANDIDATE: BIND BY Y-BAND OVERLAP, NOT BY ROW ORDINAL.** `match`, `contain` and `ink_bind` all
begin `t["row"] == e["row"]`. The row ordinal is an index into a list `CR._rows_and_lines` controls,
so it is not an address — R2.1i established exactly this for TOKEN ordinals, where a splitter change
renumbered every key and MN recall fell 0.8947 → 0.5263 with no region having changed. The gold has
carried `y0f`/`y1f` page fractions since R2.2c and **no scorer reads them**. An entry binds to the
token row whose y-band it OVERLAPS MOST, by `score_argument_region.best_overlap` — the rule this
project already adopted for the argument gold — and an entry that overlaps no row is reported as an
ADDRESSING FAILURE, separately from the region score.

| | criterion | bar |
|---|---|---|
| **K1** | THE CONTROL — with the row clusterer UNCHANGED, the four gold numbers under the re-keyed scorer | **EXACTLY 0.8760 / 1.0000 / 0.8947 / 0.8375**; any movement means the re-key is itself a change and it is REFUTED |
| **K2** | ACCOUNTING — entries bound, and addressing failures, reported separately from accuracy | **0 addressing failures**, or each is named with its leaf and text |
| **K3** | INVARIANCE — the four numbers under a DELIBERATELY PERTURBED row clusterer (baseline tolerance ×0.6 and ×1.6), old scorer vs new | old scorer moves, new scorer does **not**; if BOTH move the re-key has not achieved independence and is REFUTED |
| **K4** | the token-side addressing (band-pixel `l`/`r`) is NOT touched | asserted in the diff; R2.1i's span keying stays exactly as it is |

**Adoption requires K1–K4 TOGETHER.** ⚠️ **K3 IS THE CRITERION THAT MATTERS AND IT IS THE ONE I WOULD
HAVE OMITTED.** K1 alone shows the re-key changes nothing today; it cannot show the re-key achieves
what it is FOR, which is surviving a change to the row clusterer. A criterion that only proves "no
harm now" would let R2.2i be scored on an instrument still keyed to the thing R2.2i moves. Two
perturbations, opposite directions, and the OLD scorer must be shown to break — otherwise the test
never had the power to fail (`.scratchpad` standing rule: a test that doesn't move is not evidence
until you confirm it COULD have moved).

⚠️ **NAMED RISK.** `y0f`/`y1f` were written by `gold_rekey_pagefrac.py` against the band the gold was
built in; if that mapping is wrong for any entry, K1 exposes it as a moved number and the fault is in
the RE-KEY DATA, not in the binding rule. That distinction must be reported, because "the gold is
wrong" and "the scorer is wrong" call for opposite repairs.

##### 🔴 R2.2j CANDIDATE 1 RESULT 2026-08-20 — K1/K2 PASS **exactly**, K3 FAILS: a ROW is not an address either

**`witness/score_row_address.py` (NEW, exits 1) · `score_head_regions.ROW_ADDRESS`, DEFAULT
`"ordinal"`.** Log `.scratch/r2/rowaddr-20260820.log`.

| | criterion | result |
|---|---|---|
| **K1** | control, clusterer unchanged | ✅ **0.8760 / 1.0000 / 0.8947 / 0.8375**, 121 bound, 0 orphans — bit-for-bit the shipped numbers |
| **K2** | addressing failures | ✅ **0** |
| **K3** | invariance under `ROW_TOL_P` ×0.6 / ×1.6 | 🔴 **both scorers move** |

**1. THE CRITERION HAD POWER AND IT USED IT.** The old scorer moves hard under perturbation (×0.6:
acc 0.8760 → 0.8393, **41 orphans**; ×1.6: acc → 0.9158, 9 orphans), so K3 was not vacuous. The
y-band scorer moves too — 0.8281 and 0.9231 — and by the pre-registered bar that REFUTES the re-key.
`ROW_ADDRESS` stays `"ordinal"`.

**2. IT IS STRICTLY MORE ROBUST, AND THAT IS NOT ENOUGH.** Entries bound / orphans, old vs new:
**56/41 → 64/38** at ×0.6 and **95/9 → 104/3** at ×1.6. The re-key recovers real ground on both
perturbations. ⚠️ **A partial fix scored against an invariance bar is a FAIL, and recording it as
"improved robustness" would be exactly the laundering §0.2 forbids.**

**3. WHY IT CANNOT REACH THE BAR — the diagnosis, which is the deliverable of this run.** Binding by
y-band still makes each entry choose **ONE row**, and when the clusterer splits a printed line
(R2.2i) the entry's ink lies across **TWO**. Whichever row it picks, the tokens in the sibling row
are unreachable, so the denominator still moves with the clusterer. ⇒ **A ROW IS NOT AN ADDRESS
EITHER.** R2.1i retired the token ordinal, R2.2j retired the row ordinal, and the same argument
retires the row itself: **the address is the ink's position on the page, in BOTH axes.**

**⇒ CANDIDATE 2, pre-registered below:** bind entries to TOKENS by 2-D overlap and let row membership
out of the instrument entirely.

##### R2.2j CANDIDATE 2 PRE-REGISTRATION — written 2026-08-20 BEFORE it was built or measured

⚠️ Written first ON PURPOSE and not edited afterwards. Candidate 1 is recorded above as refuted and
this block does not inherit its numbers.

**THE CANDIDATE: 2-D INK ADDRESSING.** A gold entry names a rectangle of ink. A token binds to it iff
their **y-bands overlap** by at least half the shorter of the two AND their x-spans overlap; the row
is never consulted. This requires tokens to carry their own y-extent, which they do not today —
`region_head.tokens` keeps `l`/`r` and a `base` but discards the vertical extent of the glyphs it
covered. That extent is a property of the INK and no clusterer or splitter can move it, which is the
same invariance argument R2.1j's ink binding won on.

| | criterion | bar |
|---|---|---|
| **L1** | CONTROL — clusterer unchanged, four gold numbers | **EXACTLY 0.8760 / 1.0000 / 0.8947 / 0.8375** |
| **L2** | INVARIANCE — `ROW_TOL_P` ×0.6 and ×1.6, the bar candidate 1 failed | the four numbers **do not move**; the OLD scorer must be seen to move in the same run |
| **L3** | ACCOUNTING — entries bound, orphans, addressing failures, at every perturbation | **121 bound, 0 orphans** at every setting |
| **L4** | the y-extent added to tokens must not change any REGION rule's behaviour | region numbers under `ROW_ADDRESS="ordinal"` EXACTLY unmoved |

**Adoption requires L1–L4 TOGETHER.** ⚠️ **NAMED RISK.** A 2-D rule can bind one entry to tokens on
two ADJACENT printed lines where the setting is tight and the ink of ascenders and descenders
interleaves — the opposite failure to candidate 1's. L3's orphan/collision accounting is where that
would show, and a rule that binds more entries by binding them WRONGLY is refuted by L1, which is why
L1 demands bit-equality rather than "no worse".

##### 🔴 R2.2j CANDIDATE 2 RESULT 2026-08-20 — L1/L3/L4 PASS, L2 fails, and **L2 IS MIS-SPECIFIED**

Log `.scratch/r2/rowaddr2-20260820.log`. `ROW_ADDRESS` stays `"ordinal"`; **neither candidate adopted.**

| | `ordinal` | `yband` | `ink2d` |
|---|---|---|---|
| **L1** control | 0.8760 / 1.0000 / 0.8947 / 0.8375 | ✅ identical | ✅ identical |
| **L3** accounting | 121 bound, 0 orphans | ✅ 121, 0 | ✅ 121, 0 |
| **L2** ×0.6 | acc 0.8393, **41 orphans** | 0.8281, 38 | **0.8281, 37** |
| **L2** ×1.6 | acc 0.9158, **9 orphans** | 0.9231, 3 | **0.9231, 2** |
| **L4** y-extent inert | — | — | ✅ region numbers exact |

**1. TWO UNRELATED ADDRESSING SCHEMES PRODUCED THE SAME NUMBERS.** `ink2d` throws the row away
entirely and lands within one orphan of `yband` at both perturbations, with **identical accuracies**.
⚠️ **When a change of mechanism does not change the result, the mechanism is not what moves the
result.** The movement is not addressing.

**2. WHAT IT ACTUALLY IS.** `CR._rows_and_lines` feeds `region_head.tokens`. Perturbing `ROW_TOL_P`
changes WHICH GLYPHS ARE IN A ROW, so the TOKENS themselves change shape — a split line yields two
half-length token sets — and the gold's x-span then over- or under-covers real ink. **No addressing
scheme can be invariant to that, because the clusterer changes the OBJECTS BEING LABELLED, not
merely their names.**

**3. 🔴 AND THIS PROJECT HAD ALREADY WRITTEN THE RULE DOWN.** `score_head_regions`, § R2.1j, records:
*"The region ACCURACY under different splitters is MODELLING information and is NOT a pass/fail
criterion. R2.1i established why: the splitter is an INPUT to the region rules, so a criterion
demanding an unchanged score is unachievable and **was twice wrongly pre-registered**."* **I have now
pre-registered it a third time, one level up, for the row clusterer** — the same unachievable demand
against a different input. ⚠️ **Thirteenth instance of the signature defect: a correct rule that
nothing reads, this time inside my own acceptance criteria, in a file whose docstring states it.**

**4. WHAT L2 SHOULD HAVE ASKED, and it is sharper than what it did ask.** To test an ADDRESS, change
the row's NAME and not its CONTENT: apply a PERMUTATION to the row indices, leaving every glyph,
token and coordinate untouched. A true address is exactly invariant under a renaming; the ordinal
address must break completely. That criterion is decisive in both directions, unlike a perturbation
that changes the ink's grouping. Pre-registered below as M1–M3. ⚠️ **L1–L4 are NOT amended** — a
mis-specified criterion is reported as mis-specified, and the replacement is registered beside it.

##### R2.2j CANDIDATE 3 CRITERIA — M1–M3, written 2026-08-20 BEFORE the permutation test was built

⚠️ Written first ON PURPOSE and not edited afterwards. These REPLACE L2's question; L1, L3 and L4
stand as passed and are re-asserted here unchanged.

**THE TEST: PERMUTE THE ROW NAMES, CHANGE NOTHING ELSE.** After `classify` returns, the scorer applies
a deterministic permutation to every token's `row` field and to the row-band map, together. No glyph
moves, no token changes shape, no coordinate changes; only the LABEL of each row changes. This is a
pure renaming, so it isolates exactly the property an address must have.

| | criterion | bar |
|---|---|---|
| **M1** | POWER — under the permutation, the `ordinal` scorer must BREAK | its four numbers must MOVE, or the test has no power and proves nothing |
| **M2** | INVARIANCE — under the same permutation, the candidate's four numbers | **EXACTLY unmoved**, and orphans/addressing failures unmoved too |
| **M3** | the permutation must be shown to be a pure renaming — token count, total ink, and the multiset of token `(l, r, y0, y1)` identical before and after | asserted in the run, printed |

**Adoption of `ROW_ADDRESS` requires L1 + L3 + L4 + M1 + M2 + M3.** ⚠️ M3 is not ceremony: a
"permutation" that dropped or duplicated a row would make M2 trivially passable, and a test whose
own fixture is unverified is how a criterion becomes decorative. ⚠️ **M1 IS THE CONTROL AND IT IS THE
ONE THAT MAKES M2 MEAN ANYTHING** — the third time in two days that the deciding criterion has been
the one asking whether the instrument could have failed at all.

##### ✅ R2.2j RESULT 2026-08-20 — **ADOPTED**: `ROW_ADDRESS = "ink2d"`. The first adoption in this chain

**`witness/score_row_address.py` (NEW, exits 0) · `score_head_regions.ROW_ADDRESS`.**
Log `.scratch/r2/rowaddr4-20260820.log`.

| | criterion | result |
|---|---|---|
| **L1** | control, clusterer unchanged | ✅ **0.8760 / 1.0000 / 0.8947 / 0.8375**, 121 bound, 0 orphans — bit-identical for BOTH candidates |
| **L3** | accounting | ✅ 0 addressing failures, 0 orphans |
| **L4** | token y-extent changes no region rule | ✅ region numbers exact |
| **M1** | POWER — `ordinal` must break under a pure renaming | ✅ **acc 0.4667 · RH 0.0000 · MN 0.0000 · 90 orphans** |
| **M2** | candidate invariant under the renaming | ✅ **EXACTLY unmoved**, both candidates, orphans included |
| **M3** | the fixture is a pure renaming | ✅ token `(l, r, y0, y1)` multiset identical |
| L2 | clusterer perturbation | 🔴 both move — **MIS-SPECIFIED, excluded from the verdict**, see the candidate-2 result above |

**1. M1 IS WHY THIS RESULT MEANS ANYTHING.** Renaming rows destroys the ordinal address completely —
RunningHead and MarginNote recall both to **0.0000**, 90 of 121 entries orphaned — while both
candidates are bit-for-bit unmoved. ⚠️ That contrast is the whole finding: **every region number this
project has recorded was resting on a convention that a renaming annihilates**, and nothing had ever
tested it because the clusterer never changed. R2.2i is the change that would have.

**2. THE TIE-BREAK WAS A DEFECT IN MY OWN DECISION RULE, and it is recorded rather than quietly
fixed.** Both candidates pass every criterion identically, the pre-registration names no tie-break,
and the first run picked `yband` **because it was declared first in a tuple**. That is not a reason.
`ink2d` is adopted on the requirement that motivated the step: R2.2i splits a printed line across TWO
rows, `yband` must still choose ONE and would lose the sibling's tokens, and `ink2d` never consults a
row at all. The perturbation orphan counts agree (**37 vs 38** and **2 vs 3**, ink2d lower at both),
but the argument is the requirement, not the margin.

**3. WHAT IS NOW UNBLOCKED.** R2.2i may be scored: the instrument no longer moves when the row list
does. ⚠️ **And the standing lesson is one level more general than R2.1i's.** R2.1i: a token ordinal is
not an address. R2.2j candidate 1: a row ordinal is not an address. R2.2j candidate 2, adopted: **a
ROW is not an address — the address is the ink's position on the page, in both axes.** Each was
invisible until something proposed to change the thing the address secretly depended on.

##### R2.2i PRE-REGISTRATION — written 2026-08-20 BEFORE the candidate was built or measured

⚠️ Written first ON PURPOSE and not edited afterwards. R2.2i is the ROOT of the R2.2e chain and is
upstream of R2.2f–R2.2h, all of which are refuted and OFF; this block inherits none of their numbers.

**TWO PRE-EXISTING COMPONENTS LOOK LIKE THE FIX AND NEITHER IS.** Both were read before this block
was written, and reading them is what set the candidate's shape.

* 🔴 **`deskew.py` CANNOT REPAIR THIS, BY EXPLICIT DESIGN.** The register's own note for R2.2i says
  "the spike has carried a `deskew.py` throughout and no part of this chain consults it", which reads
  as an accusation that calling it is the remedy. It is not. `apply_theta` moves **only `x0`/`x1`**,
  and its docstring states the reason: *"leaving y alone keeps every row-grouping and line-splitting
  decision downstream bit-identical to the un-deskewed run."* Deskewing before `_rows_and_lines`
  would change **nothing whatsoever** about which glyphs land in which row. ⚠️ A component whose name
  matches the defect is not a consumer of it — the fourteenth instance would have been calling it and
  reporting the null.
* 🔴 **`line_split.leaf_skew` IS CIRCULAR HERE.** It takes `rows: list[list[dict]]` and medians a
  per-row fit. It consumes the row list that R2.2i corrupts in order to produce the slope that would
  repair it. ⚠️ **This is instrument-failure #2 of 2026-08-20 as a reusable component** — the skew
  hypothesis was already once wrongly refuted by a probe correlating over the corrupted rows.
* ⚠️ **AND THE CENSUS SHARES THE FLAW.** `probe_split_census.py` reports tilt as `+nan` on all 12
  leaves with zero split pairs, because it measures tilt **from the split pairs**. It cannot separate
  "this leaf is straight" from "this leaf tilts less than `ROW_TOL_P`". The census is a valid count of
  the defect and is NOT a measurement of tilt.

**THE CANDIDATE: A PER-LEAF BASELINE MODEL, ESTIMATED ROW-FREE (`BASELINE_MODEL`, default OFF).**
A leaf carries one slope `s`. `_rows_and_lines` clusters on the **residual** `y_bottom − s·(x_c − x_c̄)`
instead of on `y_bottom`, leaving `ROW_TOL_P` at 0.30 — the window is not widened, the coordinate is
straightened. `s` is estimated by the projection-profile criterion `deskew._score` already owns,
**transposed to the other axis**: sweep `s`, histogram the residual bottoms, score by sum of squared
bin counts, take the argmax. Straight baselines stack into tall narrow bins; tilted ones smear. It
consults **glyph boxes only** — no rows, no tokens, no splitter — which is the one property both
components above lack.

| | criterion | bar |
|---|---|---|
| **N1** | CONTROL — flag OFF | split pairs **22**, J1 **37/43**, four gold numbers **exactly** 0.8760 / 1.0000 / 0.8947 / 0.8375 |
| **N2** | PRIMARY — flag ON, the register's bar | split pairs **0** over the 20 leaves |
| **N3** | CONSUMER — the number the whole chain exists to move | J1 **43/43** |
| **N4** | GOLD does not fall | each of the four **≥** its N1 value |
| **N5** | 🔴 **INSTRUMENT-COULD-FAIL — SYNTHETIC TILT.** Rotate the glyph coordinates of the 12 leaves that show **zero** split pairs by a known ±0.5° and ±1.0° | under the **OLD** clusterer split pairs must **RISE far above 0**, and the estimator must recover the injected slope to within **±15%**; under the NEW clusterer they must return to **0** |
| **N6** | ESTIMATOR INDEPENDENCE | `s` is **bit-identical** at `ROW_TOL_P` ×0.6 and ×1.6 — the test `leaf_skew` is built to fail |
| **N7** | NO OVER-MERGING — the named risk | rows after clustering = **1220** (1242 − 22), not fewer; a merged pair of genuinely adjacent lines is a FAILURE, not a saving |

**Adoption requires N1–N7 TOGETHER.**

⚠️ **N5 IS THE DECIDING CRITERION and it can refute the step outright.** Every other row asks whether
my mechanism does what I said. N5 asks whether **tilt is the cause at all**: it manufactures the
defect on leaves that do not have it, from a rotation and nothing else. If injected tilt does NOT
split rows under the old clusterer, then tilt is not the mechanism, the 22 pairs have another cause,
and R2.2i is refuted **whatever N2 reports**. Three days running — E3, G5, M1 — the criterion that
decided the verdict was the one asking whether the instrument could fail; N5 is that link, written in
deliberately before the numbers exist.

⚠️ **NAMED RISK.** One global slope per leaf assumes pure rotation. A leaf with page **curvature**
near the gutter tilts by different amounts at top and bottom, and a single `s` under-corrects there
while over-correcting elsewhere; a leaf with few glyphs gives a noisy argmax. N2's bar is **0**, not
"fewer", precisely so a partial correction cannot be read as a success — and N7 is where an `s` large
enough to force N2 to 0 by collapsing real lines together would show.

##### 🔴 R2.2i CANDIDATE 1 RESULT 2026-08-20 — N1 PASSES, **N2 and N7 FAIL**, and the estimator is measuring a PERIOD ALIAS

Logs `.scratch/r2/r22i-stage1.log`, `r22i-sweep.log`. `BASELINE_MODEL` stays **False**; **not adopted.**

| | bar | result | |
|---|---|---|---|
| **N1** CONTROL, flag OFF | 1242 rows, 22 pairs, four gold numbers exact | **1242 rows, 22 pairs** | ✅ the residual path is bit-identical at `s=0` |
| **N2** PRIMARY, flag ON | split pairs **0** | **2** | ❌ |
| **N7** NO OVER-MERGING | rows **1220** | **1111** | ❌ **109 real lines destroyed** |
| **N3–N6** | — | not reached | N2/N7 fail first |

**1. THE ESTIMATOR LOCKS ONTO A PERIOD ALIAS, AND THE CURVE SHOWS IT.** `.scratch/r2/probe_r22i_curve.py`
prints profile sharpness against slope. On leaf 409 the argmax sits at **s=+0.0325** where the profile
occupies **134 bins**, against **358 bins at s=0**, on a leaf holding **82 rows** — the winning slope
is folding baselines onto each other. One period is `pitch/span = 38/1070 = 0.0355`; the argmax is at
**0.92 of a period**. 🔴 **The transposition of `deskew._score` to the y axis was wrong for a
STRUCTURAL reason, not a tuning one.** `deskew` works on x because vertical structure is APERIODIC —
a margin column, a numeral column, a few distinct stacks. Baselines are PERIODIC, and sum-of-squared
bin counts rewards concentration without regard to HOW MANY baselines were concentrated, so its
global maximum is always the shear that folds the page onto itself. ⚠️ **This is R2.2j's lesson one
level down, inside the instrument: a shear of exactly one pitch is indistinguishable from renumbering
the lines.** No scoring function fixes it — the ambiguity is in the data.

**2. FIVE INSTRUMENTS, FOUR ANSWERS, AND ONLY LOOKING AT THE PAGE SETTLED IT.** For leaf 409:

| instrument | slope | verdict |
|---|---|---|
| census split-pair Δbaseline (`probe_split_census.py`) | **−0.037** | magnitude right, **SIGN WRONG** |
| profile sharpness / cluster count / strip cross-correlation | **+0.032** | sign right, **~2× too large** |
| least-squares fit on "whole" rows (`probe_r22i_truth.py`) | **+0.030** | ditto — and circular, see below |
| ruled onto the scan and read by eye (`probe_r22i_zoom.png`) | ~+0.014 | **sign right, magnitude ~2× too SMALL — see the correction below** |
| 🔴 **row count against the strip line count** (`r22i-cand1-rescored.log`) | **+0.0315** | leaf 409 clusters to **44 body rows against 43 printed lines** |

🔴 **CORRECTION, SAME DAY: THE EYEBALL READING WAS THE WEAKEST INSTRUMENT AND I WEIGHTED IT MOST.**
The ladder image put five rules within a few px of each other at the right-hand edge; reading which
one stayed glued to the baseline was a judgement about a crowded picture, and I recorded "≈ +0.014"
as though it were a measurement. The decisive number is the ROW COUNT against an independently
measured line count: at **s=+0.0315** leaf 409 yields **44 body rows against a strip count of 43**,
and 419 yields **46 against 43**. ⚠️ **What I called "the collapse" — 82 rows falling to 44 — was the
step working**, and I read it as failure only because N7's bar said 74. **The estimators' +0.03 was
right and the census's magnitude was the artifact.** ⚠️ Occupancy said so from the start and I read it
backwards: 134 occupied bins at the argmax is **48 baselines × ~3 bins**, i.e. SHARP, against 358
smeared bins at s=0. **"Looking at the page" is only decisive when the thing looked at resolves the
question; here the page was zoomed to a scale at which two candidate slopes were indistinguishable.**

⚠️ **THE DIRECT FIT WAS CIRCULAR AND I NEARLY BANKED IT.** It fitted only rows spanning ≥0.75 of the
measure, on the argument that a split half cannot reach that span. But at +0.030 a line drops 28px
across the measure, **five times the 11.4px tolerance** — so a genuinely whole line could not have
survived as one row at `s=0` either. What those 31 "whole rows" are is **diagonal chains**: the greedy
`_rows_and_lines` compares each glyph to the RUNNING MEDIAN of the row it is building, so on a tilted
leaf it walks up the tilt from one baseline onto the next. Their apparent slope is ≈ one pitch per
span, which is the alias. **Instrument-failure #2 for the third time in one day, and it produced a
tight IQR (+0.0262..+0.0322) while doing it** — precision is not independence.
⚠️ **Agreement between instruments is not corroboration when they share an input.** Four of the five
read the s=0 row list or a global profile of it; all four inherit the same alias. The fifth reads the
scan. **The census's magnitude (~15-20px) and the estimators' sign (+) were each half right**, and
nothing in the criterion set would have caught it — the ladder-on-the-scan was not pre-registered.

**3. 🔴 N2 IS VERY NEARLY UNFALSIFIABLE, AND I MADE IT THE PRIMARY CRITERION.** The sweep prints split
pairs against slope for five leaves. Pairs reach **0** across almost the whole range, including
plainly absurd values — leaf 403 shows **0 pairs at s=−0.045**, having lost 2 rows, and **0 pairs at
s=+0.045**, having lost 22. The reason is mechanical: a large shear smears the baselines, the greedy
median chaining in `_rows_and_lines` then links everything in residual order, and rows so merged
contain no split PAIR because they contain no pair. ⚠️ **A metric that a wrong answer satisfies as
readily as a right one is not a bar.** N7 — the row count, written in as a guard against a named
risk — is the criterion actually carrying the verdict. **The roles are the reverse of how they were
pre-registered**, and that is only visible because N7 was written down before the run.

**4. 🔴 N7's BAR IS MIS-SPECIFIED, AND THE "FAILURE" IT RECORDED IS LARGELY THE FIX WORKING.** N7
demanded **1220 rows = 1242 − 22**, on the assumption that the census's 22 split pairs are the whole
of the over-segmentation. They are not. Ink height over pitch gives the printed-line count directly,
and it is nowhere near the row count:

| leaf | pitch | ink height | lines expected | rows at s=0 | excess |
|---|---|---|---|---|---|
| 409 | 38 | 1773px | **~48** | **82** | +34 |
| 419 | 39 | 1678px | ~44 | 78 | +34 |
| 403 | 38 | 1774px | ~48 | 76 | +28 |
| 401 | 34 | 1692px | ~51 | 83 | +32 |

The census sees 8 of leaf 409's 34 extra rows because its definition requires **two complementary
halves, each under 0.75 measure, jointly over it** — ordinary over-segmentation never matches that
shape. ⚠️ **So 1111 rows is plausibly CLOSER to correct than 1220**, and at the visually-measured
slope leaf 409 yields **46 rows against ~48 expected**. What N7 recorded as "109 real lines destroyed"
was in substantial part the step doing its job. **The bar was transcribed from an instrument that
sees a fraction of the defect it was being used to bound** — the L2/K3 failure of 2026-08-20 exactly,
and the third bar-no-run-can-pass in two days. ⚠️ **R2.2i CANDIDATE 2 IS WITHDRAWN UNRUN**: its P2
promotes this same bar to PRIMARY, and its "body block only" support correction is refuted in advance
by `probe_r22i_bridge.py` (in-block-only clusters leaf 409 to the same 44 rows). Re-pre-register
against a line count measured from the page, not from the census.

**5. WHAT REMAINS TRUE.** N1 confirms the harness: 22 split pairs at s=0, and a
per-leaf slope exists for every leaf tried that reaches 0 pairs with the row count intact (409 at
−0.0270 → 74 rows; 403 at −0.0300 → 74 of a target 73; 419 at −0.0150 → 74 of 73). **The step's
deliverable is reachable; candidate 1's estimator cannot find it.**

##### R2.2i CANDIDATE 2 PRE-REGISTRATION — written 2026-08-20 BEFORE it was built or measured

⚠️ Written first ON PURPOSE. Candidate 1 is recorded above as refuted and this block does not inherit
its numbers or its criteria.

**THE CANDIDATE: NYQUIST-BOUNDED SEARCH ON THE BODY BLOCK ALONE.** Two independent corrections, both
diagnosed above rather than tuned:

* **The bound.** The sweep is restricted to `|s| * span <= 0.5 * pitch`. Inside that range a period
  alias **cannot exist**, because no shear can move a baseline as far as its neighbour. This is not a
  clamp chosen to exclude a bad answer; it is the range over which the slope is IDENTIFIABLE at all.
* **The support.** The estimate is taken over the **body block only** (`block_measure`'s L..R), not
  the whole leaf. A leaf carrying marginal notes has TWO baseline grids at different pitches, and a
  profile mixing them has no single period — the note column is a second signal, not noise.

⚠️ **NAMED RISK, AND IT MAY REFUTE THE WHOLE APPROACH.** Leaf 409's target slope is **−0.0270** and
its Nyquist bound is `0.5 * 38 / 1070 = 0.0178`. **The answer the consumer wants lies OUTSIDE the
range in which it is identifiable.** The sweep shows −0.0150 also reaches 0 pairs at 77 rows against
a target of 74, so a bounded estimate may be good enough — or may not. If it is not, then a single
global slope per leaf is the wrong object and the deliverable is a piecewise or per-block baseline
model. **That is a real possible outcome of this run and is written down before it.**

| | criterion | bar |
|---|---|---|
| **P1** | CONTROL — flag OFF, unchanged from candidate 1 | 1242 rows, **22** pairs, four gold numbers **exactly** 0.8760 / 1.0000 / 0.8947 / 0.8375 |
| **P2** | 🔴 **PRIMARY — NO OVER-MERGING.** Promoted from N7: rows, not pairs, is the criterion the data can falsify | rows **exactly 1220** (1242 − 22) |
| **P3** | split pairs | **0** — retained, but **secondary**, and a pass here means nothing without P2 |
| **P4** | CONSUMER | J1 **43/43** |
| **P5** | GOLD does not fall | each of the four **≥** its P1 value |
| **P6** | ESTIMATOR INDEPENDENCE | `s` **bit-identical** at `ROW_TOL_P` ×0.6 and ×1.6 |
| **P7** | 🔴 **INSTRUMENT-COULD-FAIL — SIGN RECOVERY AGAINST AN INDEPENDENT MEASUREMENT.** For the 8 leaves the census measured, the estimator's SIGN must match | **8/8**, and the estimator must be seen to get **fewer than 8** when the Nyquist bound is lifted — the alias must be shown to be what the bound removes |

**Adoption requires P1–P7 TOGETHER.** ⚠️ **P7 is the deciding criterion.** Candidate 1 failed on
sign against the census and I did not find that out from any of its own criteria — I found it from a
sweep run afterwards. P7 puts that comparison INSIDE the run, and its second clause makes the bound
itself falsifiable: if sign recovery is 8/8 with the bound lifted, then the alias was not the cause
and this candidate's diagnosis is wrong even if every other row passes.

##### 🔴 R2.2i — AN INDEPENDENT LINE COUNT, AND THE REAL SIZE OF THE DEFECT (measured 2026-08-20)

`.scratch/r2/probe_r22i_linecount.py`. Count peaks in the horizontal ink profile of a **150px vertical
strip**: across 150px a tilt of 0.015 moves a baseline ~2px, so the profile stays sharp and its peaks
are printed lines. Median over the strips spanning the block. Consults **no row list, no census, no
slope estimate**. ⚠️ **Independence checked, not assumed** — the block's `L..R` comes from
`block_measure`, which reads tokens, which read `_rows_and_lines`, so the count was re-taken over a
FIXED central range (0.20W..0.80W) that consults nothing: **identical on 17 of 20 leaves and off by
one on the other three.** The dependency is inert and the count can serve as a bar.

**BODY-BLOCK PRINTED LINES: 827. ROWS EMITTED AT s=0: 1242. EXCESS: +415, of which the census sees 22.**

Per leaf the count is tight (**39–43** everywhere) and the excess tracks tilt as the mechanism
predicts: **401 +40 · 409 +39 · 403 +35 · 419 +35 · 411 +33 · 417 +33 · 407 +32**, against **413 +3 ·
408 +5 · 410 +7 · 414 +7** on the leaves that lie flat. 🔴 **Leaf 401 carries +40 excess rows and
ZERO census split pairs.** The census is not a small undercount of this defect; it detects the one
narrow shape it was written for and is blind to the rest. ⚠️ **R2.2i is roughly 1.5× over-segmentation
across the window, not "22 split pairs, 1.8% of rows"** — the register's own framing of the step
understates it by an order of magnitude, and every bar derived from it (N7, and P2 after it) inherits
that. **The census stays valid as a count of its own shape and is retired as a measure of the step.**

##### R2.2i CANDIDATE 3 PRE-REGISTRATION — written 2026-08-20 BEFORE it was built or measured

⚠️ Written first ON PURPOSE. Candidate 1 is refuted above; candidate 2 was withdrawn unrun. This
block inherits neither's criteria, and in particular **does not inherit the 1220 bar**.

**THE CANDIDATE: RESOLVE THE ALIAS WITH THE INDEPENDENTLY MEASURED LINE COUNT.** The whole difficulty
is that a shear of one pitch across the page folds baseline *k* onto *k+1*, so every profile
criterion has a second, usually larger, maximum there. That ambiguity is a property of the data and
cannot be scored away. But it has a signature: **the alias halves the number of baselines.** The
strip counter measures that number independently. So sweep `s`, and accept only slopes whose
FULL-WIDTH sheared profile resolves into the strip-measured line count for that leaf; among those,
take the sharpest. The alias is excluded because it produces about half as many peaks, not because a
bound was placed where the wrong answer happened to be.

| | criterion | bar |
|---|---|---|
| **Q1** | CONTROL — flag OFF | 1242 rows, 22 pairs, four gold numbers **exactly** 0.8760 / 1.0000 / 0.8947 / 0.8375 |
| **Q2** | 🔴 **PRIMARY — the row count matches the PAGE.** Body-block rows per leaf vs the strip count | within **±2 on ≥18 of 20 leaves**, and the 20-leaf body-block total within **±10 of 827** |
| **Q3** | split pairs | **0** — retained, SECONDARY, and worthless alone (candidate 1 showed a wrong slope reaches 0) |
| **Q4** | CONSUMER | J1 **43/43** |
| **Q5** | GOLD does not fall | each of the four **≥** its Q1 value |
| **Q6** | ESTIMATOR INDEPENDENCE | `s` **bit-identical** at `ROW_TOL_P` ×0.6 and ×1.6 |
| **Q7** | 🔴 **INSTRUMENT-COULD-FAIL — AGAINST THE SCAN, AND THE ALIAS MUST BE SEEN TO BITE.** (a) On leaves 409 and 419 the estimate must match the slope ruled onto the scan (`r22i-zoom.png`, **≈ +0.014**) to within **±0.004**. (b) With the line-count constraint DISABLED the estimator must be seen to jump to **≈ +0.03** on those same leaves | both clauses |

**Adoption requires Q1–Q7 TOGETHER.**

⚠️ **Q7(b) is what makes this candidate falsifiable rather than merely tuned.** The claim is not "this
slope works" but "the alias is what was wrong, and this constraint is what removes it." If the
estimator lands on +0.014 with the constraint disabled too, then the constraint is decorative and the
diagnosis is wrong even if Q2–Q5 all pass. Candidate 1 had no criterion of this shape and that is why
its sign error survived the whole run and was caught only by a probe written afterwards.

⚠️ **NAMED RISK — ONE SLOPE PER LEAF MAY NOT BE THE OBJECT.** The strip counter is stable (39–43) but
`ink height / pitch` disagreed with it by up to 15 on leaf 407 (55 vs 40), which is what a leaf with
a **second pitch** — the marginal-note column — or with **curvature** looks like. If Q2 passes on the
flat leaves and fails on 407/409/419, the deliverable is a per-block or piecewise baseline model and
a single global `s` is refuted as the object, not merely as the value. **Written before the run.**

⚠️ **A SECOND DEFECT IS ALREADY VISIBLE AND IS NOT THIS STEP'S.** `_rows_and_lines` chains against the
RUNNING MEDIAN of the row being built, so on a tilted leaf it walks from one baseline onto the next
and emits diagonal rows crossing several printed lines. That is what corrupted four of the five slope
instruments. It is a distinct mechanism from "a tilted line is cut in two" — the opposite failure —
and is registered separately as **R2.2k**; a correct `s` may not be sufficient while it stands.

##### 🔴 R2.2i CANDIDATE 3 RESULT 2026-08-20 — **Q7 REFUTES IT, AND ITS PREMISE IS FALSE**

Log/probe `.scratch/r2/probe_r22i_cand3.py`. Not adopted; the constraint is not merely unhelpful, it
is **inert**.

| | bar | result |
|---|---|---|
| **Q7(a)** | estimate within ±0.004 of the scan on 409/419 | **0/2** |
| **Q7(b)** | unconstrained estimator must JUMP to the alias | **2/2** — but see below |
| constrained vs unconstrained slope | should differ | **identical on 18 of 20 leaves** |

🔴 **THE PREMISE "THE ALIAS HALVES THE BASELINES" IS SIMPLY WRONG.** At a shear of one pitch, residual
levels are still spaced one pitch apart and there are still ~48 of them — each now holding pieces of
two different printed lines. **The COUNT is preserved; only the MEMBERSHIP changes.** So a line-count
constraint cannot discriminate the alias, and it did not: it changed the answer on 2 leaves of 20.
⚠️ **Q7(b) "passed" and the pass is worthless** — I wrote it to show the constraint was load-bearing,
but it only shows the unconstrained estimator reaches +0.03, which the constrained one also does.
**A criterion comparing a mechanism to itself cannot fail.** The falsifier I actually needed was the
one in the table above it: constrained vs unconstrained must DIFFER, and it is the line I did not
pre-register as a bar.

⚠️ **AND Q7(a)'s BAR WAS WRONG, NOT THE ESTIMATOR.** It demanded ±0.004 of the eyeballed +0.014. The
row count against the strip line count says +0.0315 is right for 409. **Candidate 3 was scored
against a number I had misread off a picture** — the same failure as N7, one instrument later.

##### 🔴 R2.2i CANDIDATE 1 RESCORED AGAINST THE CORRECT BAR — a real but PARTIAL improvement

`.scratch/r2/r22i-cand1-rescored.log`. Body-block rows against the strip line count, 20 leaves:

| | strip lines | rows OFF | rows ON | total error |
|---|---|---|---|---|
| totals | **827** | 1214 | **1073** | **+387 → +246** |

**Within ±2 on 3 of 20 leaves** (bar for Q2 was ≥18), within ±3 on eight — **409 +1 · 415 +0 ·
413 +1 · 419 +3 · 410 +3 · 408 +3 · 416 +3**. So the flag removes **36% of the excess** and is
nowhere near the bar. ⚠️ **The residual is concentrated exactly where the slope comes out ≈ 0**:
**407 +31 at s=0.0000 · 401 +29 at s=+0.0435 · 405 +24 · 412 +23 · 402 +24**. A leaf that the
estimator declares flat is left with all its excess, which is **R2.2k** — the running-median chaining
over-segments whether or not the leaf is tilted. **R2.2i and R2.2k are not separable by this bar and
must be scored together**, the same cycle H4/J7 exposed between R2.2f and R2.2g.

**VERDICT UNCHANGED — `BASELINE_MODEL` stays False** — but the REASON is now correct: not "it
destroys 109 lines" (it does not; that reading came from the census bar) but **"it fixes a third of
the over-segmentation and cannot reach the bar while R2.2k stands."**

##### ✅ R2.2l RESULT 2026-08-21 — THE SIXTH SINK. Guard exits 0, four gold numbers unmoved.

**THE LEAK, AND IT WAS NOT WHERE I SAID IT WAS.** The register row and my own notes said the drop was
"downstream in the `contain`/`ink_bind` path". **Both of those are clean** — `contain` puts every
entry in `obs` or `orphans`, and an `ink_bind` entry whose tokens are all excluded ends with an empty
weight map and is reported as an orphan. The leak is in `score_head_regions.main`, in the loop that
builds `pairs`:

```
for e, t in bound:
    if (t["row"], t["tok"]) in excl:
        continue          # <-- an entry vanishes here, counted by nothing
```

`excl` holds the tokens bound by AMBIGUOUS gold entries. When a labelled entry binds a token an
ambiguous entry also binds, it is dropped rather than scored — **which is the same event as a
collision**, the splitter having merged two labelled spans into one token. 🔴 **`main` reports five
sinks — `unlabelled`, `ambiguous`, `collisions`, `orphans`, `abstained` — and this sixth one had no
counter and no print.** The guard asserts `lost <= collisions + orphans`, so every drop through it
read as a token disappearing for no stated reason.

**THE FIX.** `main` now counts the sink as `ambcoll`, prints it beside the other five, and returns it;
the guard counts it in `accounted` and names it in its criterion B, its failure message and its
success message. ⚠️ **THIS IS AN ENUMERATION FIX, NOT A RELAXED BAR.** The invariant was always
"nothing disappears UNREPORTED", and the list of reported categories was incomplete in BOTH the
scorer and the guard. **Measured before the change was made**, across both addresses × three
splitters:

| | quantile | coarse ×1.6 | fine ×0.4 |
|---|---|---|---|
| `ordinal` — gap / `ambcoll` | 0 / **0** | 0 / **0** | 0 / **0** |
| `ink2d` — gap / `ambcoll` | **+1 / 1** | 0 / **0** | 0 / **0** |

`ambcoll` is **1 in the single failing cell and 0 in the other five**, so counting it closes that gap
and loosens nothing that already balanced. A real silent loss still fails: there is exactly one
increment site and it prints.

**VERIFIED.** Guard **exits 0**; quantile now balances **lost 27 / accounted 27**, coarse 28/28, fine
25/25, `weak 0` everywhere. Four gold numbers **exactly unmoved — 0.8760 / 1.0000 / 0.8947 / 0.8375**,
baseline `ambcoll` 0.

⚠️ **WHY R2.2j's OWN CRITERIA COULD NOT HAVE CAUGHT IT.** L1–L4 and M1–M3 perturb the ROW CLUSTERER
and the row NAMES. This sink only opens when the SPLITTER re-cuts a token so that a labelled and an
ambiguous entry land on the same one, and under `ordinal` those two entries addressed different rows
so they never collided. **The adopted change did not create the sink; it made an existing silent sink
reachable** — the bug is as old as the exclusion filter, and `ink2d` is what walked into it.

⚠️ **A LATENT SIBLING, NOT FIXED, RECORDED.** `main` line ~385 filters the CONTAINMENT observations by
`cexcl` with the same uncounted `if ... not in cexcl` idiom. Nothing checks `c_obs`, so no guard fails
today, and the containment binding is a REFUTED approach kept only for reporting (R2.1j). **It is the
same defect one path over and it should be counted when that path is next touched.**

##### R2.2i + R2.2k CANDIDATE 4 PRE-REGISTRATION — written 2026-08-21 BEFORE it was built or measured

⚠️ Written first ON PURPOSE. Candidates 1 and 3 are refuted above, candidate 2 was withdrawn unrun,
and this block inherits none of their bars — in particular **not the 1220 row count**, which came
from the census and was the reason candidate 1 read as a catastrophe rather than a partial fix.

**WHY THE TWO STEPS ARE ONE CANDIDATE.** Candidate 1 removed 36% of the over-segmentation and left
the rest concentrated on the leaves where its slope estimate came out ≈ 0: **407 +31 at s=0.0000 ·
401 +29 · 405 +24 · 412 +23 · 402 +24**. A leaf the estimator calls flat keeps ALL its excess, so the
residue is not tilt at all — it is **R2.2k**, the running-median chaining, which over-segments a
straight leaf as readily as a crooked one. Scoring either alone measures the other's failure. This is
the H4/J7 cycle between R2.2f and R2.2g, one level up.

**THE CANDIDATE: ALIAS-FREE SLOPE + SEEDED ASSIGNMENT.** Two changes, one per defect:

* **R2.2i — the slope comes from STRIP CROSS-CORRELATION, not a global profile.** Correlate the y
  profiles of adjacent 1/8-page strips and take the lag maximising each pair, bounded to **half a
  pitch**; the median of the per-pair slopes is the leaf's tilt. ⚠️ **This estimator CANNOT alias, by
  construction**: across a strip the baselines shift ~4px against a 19px bound, so the lag is unique,
  and summing across strips unwraps a total that may exceed a pitch. Candidate 1's sum-of-squares had
  its global maximum AT the alias and no bound could remove it.
* **R2.2k — glyphs are assigned to FIXED SEEDS, not chained onto a running median.** Take the
  residual `y − s·(x − x̄)`, find the baseline peaks in its profile ONCE, and assign each glyph to its
  nearest seed within `ROW_TOL_P·p`. A glyph reaching no seed starts a singleton, which the existing
  `len(r) >= 2` filter drops. ⚠️ **Nothing a row accumulates can move the row's own address**, which
  is the whole of R2.2k: today the median creeps with every append, so a row walks off its baseline.

| | criterion | bar |
|---|---|---|
| **S1** | CONTROL — flag OFF | 1242 rows, 22 pairs, four gold numbers **exactly** 0.8760 / 1.0000 / 0.8947 / 0.8375 |
| **S2** | 🔴 **PRIMARY — the row count matches the PAGE.** Body-block rows vs the strip line count | within **±2 on ≥18 of 20 leaves**, and the 20-leaf total within **±10 of 827** |
| **S3** | 🔴 **DO NO HARM.** The four leaves already close (413 +3 · 408 +5 · 410 +7 · 414 +7) | each leaf's \|error\| **must not increase**. A mean improvement bought by wrecking the good leaves FAILS |
| **S4** | split pairs | **0** — kept for continuity only; candidate 1 showed a wrong slope reaches 0, so a pass here is worth nothing alone |
| **S5** | CONSUMER | J1 **43/43** |
| **S6** | GOLD does not fall | each of the four **≥** its S1 value |
| **S7** | ESTIMATOR INDEPENDENCE | `s` **bit-identical** at `ROW_TOL_P` ×0.6 and ×1.6 |
| **S8** | 🔴 **DECIDING — SYNTHETIC TILT, GROUND TRUTH BY CONSTRUCTION** (see below) | all three clauses |

**S8, in full.** Take the four flattest leaves and rotate their glyph coordinates by a known
`θ ∈ {±0.010, ±0.020}`, changing nothing else:
  **(a)** the estimator must recover `θ` to within **±0.003** of the un-injected leaf's own estimate;
  **(b)** the body-block row count under injection must equal the un-injected count to within **±1**;
  **(c)** ⚠️ **with the flag OFF the injected leaves must show a LARGE row-count change.** If they do
  not, the injection is too weak to manufacture the defect, **S8 is VOID and proves nothing** — and
  that is written down before the run rather than discovered as a convenient null afterwards.

**Adoption requires S1–S8 TOGETHER.**

⚠️ **WHY S8 IS THE DECIDING LINK.** Every other row is scored against the strip line counter, which is
an instrument I built two days ago and which the whole result now leans on. S8's ground truth is a
rotation *I applied*, so it is known independently of the counter, of the census, of the gold, and of
the row list. Four days running, the criterion that decided the verdict was the one that could fail
for a reason outside the rule under test — E3, G1, M1, and the strip count. This is that link, and
clause (c) makes the TEST ITSELF falsifiable, which is the check candidate 3's Q7(b) lacked when it
compared a mechanism to itself and "passed" meaninglessly.

⚠️ **NAMED RISKS.** (1) Seed-finding can UNDER-segment, merging two genuinely adjacent lines into one
seed — S2's per-leaf ±2 and S3 are where that shows, which is why S2 is per-leaf and not a total.
(2) A leaf carrying marginal notes has TWO baseline grids at different pitches and one seed set is
wrong for both; if S2 passes on the note-free leaves and fails on 407/417/419, the deliverable is a
per-BLOCK seed set and a single leaf-wide model is refuted as the object. (3) The strip estimator was
measured once, on 20 leaves, agreeing with the census sign on 6 of 8 — it is **not** established, and
S8(a) is what would expose it.

##### 🔴 R2.2i + R2.2k CANDIDATE 4 RESULT 2026-08-21 — S1–S4, S7, S8 PASS. **S6 FAILS. NOT ADOPTED.**

Logs `.scratch/r2/{cand4c,cand4-s8b}.log`. `BASELINE_MODEL` stays **False**. This is by a wide margin
the best the chain has produced and it is still refused, on the criterion that protects the gold.

| | criterion | bar | result | |
|---|---|---|---|---|
| **S1** | CONTROL, flag OFF | 1242 rows, 22 pairs | 1242 / 22 | ✅ |
| **S2** | body rows vs strip count | ±2 on ≥18/20; total ±10 | **20/20**, total **793 vs 790 = +3** | ✅ |
| **S3** | do no harm to the flat leaves | no \|error\| increase | none | ✅ |
| **S4** | split pairs | 0 | **0** | ✅ |
| **S5** | J1 | 43/43 | **not measured — S6 refutes first** | — |
| **S6** | four gold numbers do not fall | each ≥ its S1 value | **RH 1.0000→0.9231, MN 0.8947→0.8235** | 🔴 |
| **S7** | estimator independence | bit-identical at ×0.6/×1.6 | **20/20** | ✅ |
| **S8** | synthetic tilt | (a) ±0.003 (b) ±1 row (c) potent | **16/16 · 16/16 · 10/16 potent** | ✅ |

**1. THE STEP'S OWN NUMBER IS NOW ESSENTIALLY EXACT.** Body-block rows land within ±2 of the strip
line count on **all twenty leaves**, thirteen of them exactly, against candidate 1's **3 of 20** and a
total error of +246. The two mechanisms are doing what the register asked: **407, which candidate 1
left at +31 with a slope of 0.0000, is now +2** — that residue was never tilt, it was the chaining,
and only the seeded assignment reaches it. **R2.2i and R2.2k are confirmed inseparable and jointly
sufficient for the row count.**

**2. 🔴 THE BAR ITSELF WAS WRONG AGAIN, AND THE RULE AGAINST IT IS IN THIS MODULE.** S2 first read
792 against 827 — a flat **−35**, near −2 on every leaf. A constant offset is a definitional
mismatch, not a clustering failure. Diagnosed: the strip counter took every profile run, including
**two per leaf that start at y=0 and end at y=H** — the page-edge shadow. `collation_read.text_runs`
already states the rule (*"a run that reaches the band's BOTTOM EDGE is the leaf edge / gutter
shadow, not type"*) and my counter reimplemented run-detection without reading it. ⚠️ **The 827 bar
that refuted candidate 1 was inflated by ~39.** Corrected to **790**, and the rule reads the ink
profile alone, so it is not a bar tuned to a candidate.

**3. 🔴 S8(a) FAILED FIRST, AND THE FAULT WAS MY BAR AGAINST MY OWN INSTRUMENT'S RESOLUTION.** Leaf
414 missed by 0.0037 and 0.0051 against ±0.003. The correlation peak was taken at an **integer pixel
lag** over strip centroids ~150px apart, so the estimator's slope quantum is **1/150 = 0.0067**, more
than twice the tolerance. I demanded sub-quantum accuracy from an instrument that cannot express it,
without ever computing its resolution. **Fixed the INSTRUMENT, not the bar**: a parabola through the
peak and its neighbours gives the fractional lag, and recovery errors fell to **≤0.0004**, 16/16.

**4. 🔴 S6 FAILS, AND THE FIRST VERSION OF THE FAILURE WAS A GOODHART I ALMOST BANKED.** The first
S6 run posted **acc 0.8760→0.9000 and MT 0.8375→0.9178, both UP**, while scored pairs fell **121→90
with 27 orphans**. Three of four numbers improved by discarding a quarter of the gold — the exact
pattern `score_head_regions`' own header records ("the broken splitter posts the HIGHEST accuracy,
0.9479, by orphaning 25"). ⚠️ **S6 as pre-registered checks four RATES and never checks the
DENOMINATOR**, so it could have been passed by a candidate that orphaned its way there. Any successor
must bar on `pairs` as well.

**5. WHY IT ORPHANED, AND WHAT IS LEFT.** Orphans by label at first: **RH 13/20 · MN 9/19 · CH 2/2 ·
MT 3/80** — every SHORT line, the body untouched. Cause: seeds were kept above `0.25 × profile
maximum`, and the maximum is set by the densest full body line, so a running head never reaches a
quarter of it. ⚠️ **S2 scored a perfect 20/20 while this was happening, because S2 counts BODY-BLOCK
rows — the long lines that survive.** A criterion scoped to the body cannot see a defect that only
destroys heads and notes. Replaced with **prominence-based peak detection** (a short line is low but
stands clear of its neighbourhood), floor tied to this module's own "a row needs ≥2 glyphs" rule.
Orphans **27 → 10** and pairs **90 → 109**, both chapter heads recovered. **Remaining: RH 6 · MN 2 ·
MT 2, on leaves 418(3), 406(2), 404/407/408/409/416.** Still short lines. ⚠️ **Tuning the seed finder
further against the gold would be fitting to the score and was stopped here deliberately.**

**NEXT.** The row count is solved; the short-line seeds are not. A successor should seed **per block**
rather than leaf-wide — the head, the body and the note column are three grids — and must be scored
against an S6 that bars on `pairs` as well as on the four rates.

##### R2.2b PRE-REGISTRATION — written 2026-08-18 BEFORE the anchor was built or measured

⚠️ **This block is written first ON PURPOSE and is not edited afterwards.** R2.2b is the step that makes
a second band change legitimate; a criterion written after seeing the anchor's numbers would make it a
re-cut of the same knob wearing a new name. What the run produced is recorded in the section BELOW this
one, and any criterion this block got wrong is reported as wrong rather than amended.

**THE MECHANISM, stated before it is tested.** The band is taken from **the rows of type themselves**:
detect connected components over the **WHOLE PAGE** — no top fraction, no search window, no page
fraction anywhere in the derivation — cluster them onto baselines with the existing `_rows_and_lines`,
and cut the band from **the first `N` rows of type on the page**, padded by a fraction of the measured
line pitch. The bound therefore MOVES with the type on each leaf, which is the entire content of
"anchored". ⚠️ **`N` is stated in the vocabulary of the BOOK, not of the error** (Sir's anti-circularity
ruling): the head of a page in this edition carries at most a running head, a chapter head (`CHAP.` /
`XXVII.`) and its flanking side-notes before the first line of scripture — **three** non-body rows by
the edition's own design. **`N = 6` doubles that**, and is fixed here before any leaf is measured.
Choosing `N` by looking at where the first body line happened to fall would be fitting the band to the
window it is scored on.

**PRE-REGISTERED ACCEPTANCE.** Adoption requires A1–A4 together; any one failing means the anchored
band is NOT adopted and `HEAD_BAND` stays frozen, with the failure reported as the finding.

| | criterion | bar |
|---|---|---|
| **A1** | R2.2b's own: the band **contains the first body line**, per leaf, against the hand-labelled set — directly, never through continuity | **20/20**. A containment property, not a rate: one leaf short means a leaf whose scripture the reader cannot see at all |
| **A2** | R2.2c's C3, inherited: the band **contains every labelled gold entry** | **121/121**, and **RunningHead 20/20** — the number that is 0/20 today |
| **A3** | the anchor is **genuinely anchored**: no page fraction in its derivation, and the resulting bounds **differ across leaves** | bounds constant across leaves ⇒ FAIL. A "measured" anchor that lands in the same place every time is a fraction with extra steps |
| **A4** | the reader is **not made worse**: `read_first_words_typed` abstains no more often on the anchored band than on the frozen one | abstentions **≤** the frozen band's, both reported |

⚠️ **EXPLICIT NON-CRITERION: the continuity rate is NOT the acceptance and may not be quoted as one.**
R2.1f fired precisely because 0.312 is a joint measure of two readers and a scorer. Any continuity
number produced while testing this band is a **diagnostic**, labelled as such at every point it prints.
**A band that raises the continuity rate while failing A1–A4 is refused**, and a band that passes A1–A4
while the rate falls is still adopted — the rate is not what this step is about.

⚠️ **A2 IS THE HARDER BAR AND IS EXPECTED TO BE THE ONE THAT BINDS.** The gold labels three rows of the
0..0.35h crop; a band of the first 6 rows of type must contain them all. If A2 fails while A1 passes,
that is informative and is reported as such: it would mean the band can serve the READER without
serving the SCORER, which is the split R2.2c exists to close and would leave R2.2c open.

##### 🔴 R2.2b RESULT 2026-08-18 — the anchor is NOT ADOPTED, and the mechanism is REFUTED BY THE BOOK

**`witness/score_band_anchor.py` · `CR.anchored_head_band` · `witness/gold/first_body_line_OT1-1609-B_400-419.json`**

| | | |
|---|---|---|
| **A3** ANCHORED | ✅ **PASS** | 20 distinct bounds over 20 leaves; top spread **0.0253h**, bottom spread **0.0582h**, against a frozen bound identical on every leaf |
| **A2** GOLD CONTAINMENT | ✅ **PASS** | **121/121** — RH **20/20**, MN 19/19, MT 80/80, CH 2/2. Against the frozen band's **70/121** with RH **0/20** |
| **A1** FIRST BODY LINE | 🔴 **FAIL** | **18/20**. Misses leaf 403 (body line 0.1654h..0.1917h vs band 0.0354h..0.1360h) and leaf 411 (0.2432h..0.2691h vs 0.0291h..0.1565h) |
| **A4** READER | not run | moot while A1 fails; adoption needs A1–A4 together and three of four is not a pass |

🔴 **THE PRE-REGISTRATION'S JUSTIFICATION FOR `N` WAS WRONG ABOUT THE BOOK, and the book is what
refuted it.** It read: *"the head of a page carries at most a running head, a chapter head and its
flanking side-notes before the first line of scripture — three non-body rows by the edition's own
design."* **False.** This edition sets a multi-line **italic ARGUMENT** between the chapter head and
the first verse — **4 detected rows on leaf 403, 11 on leaf 411**. ✅ **This is Sir's anti-circularity
ruling paying for itself**: because `N` was justified in the vocabulary of the BOOK, the book was
able to contradict it. An `N` sized from where the first body line happened to fall would have fitted
the window and nothing could have refused it.

🟢 **THE FAILURE DECOMPOSES THE STEP, WHICH IS WORTH MORE THAN A PASS WOULD HAVE BEEN.**
* **The TOP is solved and measured.** Anchoring lifts gold containment from **70/121 to 121/121** and
  RunningHead from **0/20 to 20/20**. ⇒ **An anchored top CLOSES R2.2c's C3**, demonstrated rather
  than argued.
* **The BOTTOM cannot come from a ROW COUNT.** The number of non-scripture rows before the first
  verse is a property of the PAGE'S STRUCTURE — 0 on a continuation leaf, **11** on a chapter opening
  — not a constant of the edition. ⚠️ And the frozen band, for all its faults, **contains the first
  body line on BOTH leaves the anchored band misses**, because 0.30h reaches further down the sheet.
  A band change that fixed the head and truncated the foot would have been a regression sold as a fix.
* ⚠️ **A ROW IS NOT A LINE AT WHOLE-PAGE SCALE.** Measured: **39 of 140 consecutive row-pairs overlap
  by more than half a row-height** — `_rows_and_lines` fragments single lines because across the full
  page width a curved leaf's baseline drifts more than its `0.30 × pitch` clustering tolerance (leaf
  409's `'egat Galaad, of whom'` is the right-hand half of the line above it). So `N = 6` rows can be
  **3–4 real lines**. Any later rule counting rows over a whole page inherits this.

🔴 **NINTH INSTANCE OF THE SIGNATURE DEFECT, AND IT IS THE REAL FINDING: THERE IS NO REGION TYPE FOR
THE ARGUMENT.** Raised as **R2.2d**. `region_head` labels leaf 411's argument rows **3–7 MainText**
and leaf 403's rows **6–7 MainText**, because the argument is justified to the full measure and R3's
body-row test passes on it. ⇒ **On a chapter-opening leaf the head reader returns the ARGUMENT's
opening words as the leaf's first line of scripture.** ⚠️ **The region gold cannot see this: on
exactly those leaves it labels no MainText at all** — leaf 403 carries 2 entries and leaf 411 carries
4, because the labeller had no admissible label for an argument line. **The gold's sparseness on
those two leaves is a FOSSIL of the missing category**, and the blind spot sits on the same leaves as
the defect. It also gives the 0.312 continuity rate another named cause: on a chapter opening the
head reader compares the catchword against an ARGUMENT line, which cannot agree.

**NEW TRACKED EVIDENCE.** `witness/gold/first_body_line_OT1-1609-B_400-419.json` — the first line of
scripture per leaf, in page fractions, 20 leaves. 18 entries come from the region gold's first
MainText row; **2 were adjudicated from the RENDERED leaf together with a whole-row recogniser read**,
a different instrument from the classifier under test. ⚠️ **No entry is derived from the band being
tested** — identifying the first body line by asking where a candidate band puts it would make A1 the
band grading its own homework. Its `_doc` records the limitation that the 18 inherit the region
gold's window and must be re-checked on any leaf carrying a `CHAP.` head.

⚠️ **`HEAD_BAND` IS UNCHANGED AND R2.1f's SINGLE RE-CUT IS STILL UNSPENT-ON-THIS.** The anchored band
lives beside it, default OFF, until it passes. A1 is not lowered to 18/20 to let it in.

⚠️ **The constraint that must survive into every later instrument: the comparison width comes from the
FOOT side, never the head side.** Let the head reader choose how much of itself to be scored on and it will
pick the crop that flatters it. `k` is `len(norm_words(catchword))` for exactly this reason. **The same
trap reappears one level up in the geometry model** — a boxer evaluated on the boxes it proposed always
looks excellent — which is why Gate 9 measures against GOLD-LAYOUT **with the recogniser frozen**.

#### What the re-cut fixed, and what it proved

`_group` scaled the word-space threshold by `max(pitch, glyph_height*1.3)` — correct for the FOOT
band, where a handful of tokens sit in white space. Applied to the dense justified HEAD band it
exceeded every word space, so the row never split and `first_word()` returned **the whole line**.
The threshold is now measured from the row's own gap distribution (1-D 2-means over observed
inter-glyph gaps), and several pairs now split correctly (`'with oile in'`, `'two,'`, `'of'`).

🟢 **It also confirmed the metric was never the problem.** The catchwords read at **0.87–1.00**
and are plainly right: `face` · `ſtoode` · `Returne` · `God` · `familie` · `Cades` · `reuenge` ·
`worke` · `abide`. **Every failure is on the head side.**

#### The residual, which is THREE defects and not one

1. 🔴 **The head band does not reliably yield the first line of TEXT.** `411→412` compares
   catchword `Cades` against `'Temporal'` — a **running head**, not the first text line. `401→402`
   reads `'ode'` for a line opening `ſtoode` (left-edge truncation). `415→416` and `416→417` take
   the wrong line entirely. The `0.06–0.30` band plus "first full-measure line" is not an
   instrument for finding the first line; it is a guess that usually lands near it.
2. 🟢 **FIXED 2026-08-15, and the fix moved nothing — see the third run above.** *The comparison
   unit is wrong: a catchword can be MORE THAN ONE WORD.* `414→415` read catchword `'of flowre'`
   against first word `'of'` — a true agreement scored as a disagreement. ⚠️ The prediction
   attached to this entry — *"it depresses the rate by an unknown amount"* — was **wrong in
   magnitude**: the amount was **one pair**, and that pair fails on a genuine recogniser error
   once corrected. Left standing as written, because a defect that was real and yet not
   load-bearing is exactly the kind of thing this file exists to record honestly.
3. 🔴 **NEW, and the opposite defect: the head reader OVER-matches.** Three of the five AGREEs are
   whole-line blobs accepted by the `≥4-char` prefix rule (see above). This entry did not exist
   when the residual was called "three defects"; it is why the residual is not a floor.
4. 🟡 Genuine recogniser error, the smallest share: `'wl'` for *whom*, `'mi'` for *ni*.

#### What redesign should address — ✅ **DECIDED 2026-08-17, option (1); see R2.1g above**

**The head-side reader needs to be a different instrument, not a re-tuned one.** The foot band
works because a direction line is *sparse type in white space*; the head band is *dense justified
text*, and the same component-and-gap machinery is being asked to answer a question it cannot
express — **the fourth instance of this project's recurring shape**. Candidates, in the order I
would measure them:

* **Find the first BASELINE, not the first "full-measure line"** — the running head is separated
  from the text block by a measurably larger leading; that gap is a property of the setting and is
  the thing being looked for, rather than a proxy for it.
* **Score the catchword against the first *n* characters of the next leaf's text block**, not
  against a tokenised first word — it dissolves defect 2 entirely and removes the head-side
  tokeniser from the measurement path.
* **Re-measure with defect 2 corrected before any redesign is chosen**, so the redesign is aimed
  at the real residual rather than at an artefact of the scorer.

⚠️ **Do not read 0.312 as "the catchword approach scores 0.31."** It is a JOINT measure of two
readers and a scorer, with two known defects in the non-catchword half. The catchword half is
the part that works.

### R2.1 — execution steps (written 2026-08-11, before the work)

| # | step | deliverable | acceptance |
|---|---|---|---|
| R2.1a | **Parity, measured** | for a stratified sample of `OT1-1609-B`, the leaf-index parity that carries signatures, established from **where tokens land** (signature centre-left ~x 0.48–0.55, catchword right ~x 0.75–0.87) | parity is **reported with its evidence**, never assumed from index parity; if both parities carry signatures the sample is widened, not the claim narrowed |
| R2.1b | ✅ **DONE 2026-08-27c — `dr_v3_armB` SELECTED on 7 class wins of 7, and THE MEASUREMENT INVERTED THE HEADLINE RANKING.** `witness/audit_recog_holdout.py` → `witness/build_recog_gold.py` → `witness/score_recognisers.py`. See the result section below. ⚠️ The original note is kept because it is the reasoning the step rested on: **NOT DONE — and stated rather than quietly folded into R2.1c.** Sir's order was b→c→d′; I ran c and d′ first because d′ is the acceptance metric, then R2.1f fired on it. R2.1b's purpose was to justify R2.1c's confidence floor from a measured CER curve, and the observed failure is **not** confidence-floor-related — it is the head-side instrument — so running it first would not have changed the outcome. It remains OPEN (**C1 — mechanical**: the models exist, the method is standard; only the fixed token set has to be keyed). ⚠️ It should be run **after** the redesign decision, not before: scoring models against a head reader that is about to be replaced would measure the wrong thing. **Recogniser selection, measured** | 🔴 **The inventory is wider than this row said, verified on disk 2026-08-17**: `reichenau_dr/best_0.9396` (the one every document cites) · `dr_v3_armA/best_0.9739` · `dr_v3_armB/best_0.9694` · `dr_armA/best_0.9349` · `reichenau_dr_ho/best_0.9230`. Score **all five** on ONE fixed token set with hand-keyed truth | the model is chosen **on measured CER over direction-line tokens**, not on impression; the losing models and their scores are recorded (§0.2 rule 1's discipline, applied to a component). ⚠️ **`0.9739 > 0.9396` IS NOT A FINDING AND MUST NOT BE QUOTED AS ONE.** These are per-arm validation accuracies whose splits have **not** been shown to be the same; a number that is higher on a different held-out set is not a better model. **Comparability is UNKNOWN, and establishing it is precisely what this step is for** — which is also why the cited headline figure for this project's recogniser (0.9396) may be neither the best nor the right one to cite |
| R2.1c | **`witness/collation_read.py`** | the probe promoted to a module: `read_direction_line(witness, leaf) -> {signature, catchword, x_positions, confidence, abstain_reason}`; **separate** signature and catchword fields | abstains with a **stated reason** and never guesses; a confidence floor is applied and its value is justified by R2.1b's CER curve, not chosen |
| R2.1d′ | **The R2.1 metric run — RESTATED, see R2.1-CRIT** | **two** measurements, because the old one was unsatisfiable: **(A) catchword continuity** — `catchword(leaf N)` vs the first word of `leaf N+1`, over a consecutive run; **(B) signature-sequence monotonicity** — parsed signatures must ascend in signature order (`Y · Y2 · Y3 · Z · Aa …`) with no descent | **(A) ≥95% agreement on leaf pairs where both leaves yield a reading**, Wilson CI, lower bound above the bar — not the point estimate; **(B) zero descents** unexplained by the collation. A descent is a defect report entry (R2.4), never a discarded reading. Failures listed by leaf |
| R2.1e | **Pair completeness** | signature and catchword scored **independently**, never "≥1 token read = success" | leaf 851's failure mode (catchword read, signature missed) is visible in the score by construction |
| R2.1f | **Apply the pre-registered rule** | either proceed to R2.3, or fire the escalation | ≥95% (CI lower bound) ⇒ R2.3. Below ⇒ **band re-cut ONCE**, then **ALERT that the approach needs redesign**. Confident-wrong at any rate ⇒ **FAIL regardless of the parsed rate**, because the collation cannot detect the difference |

**Complexity per sub-step** (restated 2026-08-17 from sub-ceilings in hours): **R2.1b C1** — the models and
the method exist, only the fixed token set must be keyed · **R2.1c C2** — assembly of measured parts ·
**R2.1d′ C3** — a new measurement, and it required a negative control to be trusted · **R2.1g C3** — a new
instrument, and the one now being built. **R2.1f fires on candidate exhaustion, not on elapsed effort**,
and the candidate table in the section head is where that is tracked.

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

⚠️ **R2's pre-registered rule is now live and must be honoured.** Three metric candidates are refuted and
none has cleared. The rule permits **one band re-cut**, then **ALERT for approach redesign** — and it
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

### 🔴 R2.2 IS THE PIVOT, AND R2/R3 ARE RECIPROCALLY GATING (found 2026-08-17)

**This file has sequenced R2 before R3 since it was written. That ordering is not wrong so much as
incomplete, and the incompleteness is why both have stalled.**

**The argument, in three steps.**

1. **Every R2.1 failure is head-side, and the head side is a region-typing problem.** `411→412` compares
   catchword `Cades` against `'Temporal'` — and `'Temporal'` is a **running head**. That is not an OCR
   error; it is a **region misassignment**, and `RunningHead` is one of Gate 9's own classes.
2. **R3.1's addressing key is `(volume, printed page, signature, side)` — and it has two independent
   readable components, not one.** The **signature** component needs R2.1, which is stalled. The
   **printed page number** component needs **R2.2**, which is *unstarted* — and R2.2 is a reader of the
   **head band**: the same instrument R2.1's head side needs and R2.1g is now building.
3. **Therefore one build discharges three obligations.** The head-band RunningHead/MainText separator
   yields (a) R2.1's head side, (b) R2.2's page-number reader, and (c) **a signature-independent component
   of R3.1's key** — which means R3 can begin without waiting on the collation that is stalled.

🟢 **So R2 and R3 INTERLEAVE. Stated precisely, because "interleave" is otherwise an excuse:**

| R3 step | needs | can start on R2.2a alone? |
|---|---|---|
| R3.1 leaf key | the key's *definition*; page number readable per leaf | 🟢 **YES** — the key may be defined on `(volume, printed page, side)` with signature as an **optional** component. ⚠️ It must be recorded that the signature slot is optional-by-evidence (~44% of rectos), not optional-by-convenience |
| R3.2 correspondence table | page numbers readable across witnesses of one volume | 🟢 **YES for the volumes where the head band reads.** Coverage is reported per witness and abstentions are named (R1.4) |
| R3.3 absence register | R3.2, plus a cause per absence | 🟡 **PARTLY** — absences are detectable from R3.2; *classing* them (not in copy · not scanned · dropped in derivation) needs R2.3's collation for the first class |
| R3.4 verification by image | R3.2 sample + the §1.4 correlation method | 🟢 **YES** — and note it is the one R3 step whose method is already proven at page-block scale (+0.424/+0.398 vs 0.000–0.036) rather than at catchword scale, where R2.1d″ refuted it |
| **full Gate 0c closure** | R3.2 **and** R2.3/R2.4 | 🔴 **NO.** A correspondence table over leaves whose collation is unestablished maps leaves that may be duplicates or made-up supplies |

⚠️ **What this does NOT license.** Gate 0c does not close early, and no transcription is unblocked by R3.2
alone — §2's rule is 0b **and** 0c. The reordering buys **evidence**, not permission: cross-witness
correspondence is itself one of R2.5's collation signals, so R3.2 feeds back into the section that gates it.
**That is the reciprocity, and it is why strict sequencing was the wrong shape.**

| # | step | deliverable | acceptance |
|---|---|---|---|
| R2.2a | **The head-band region primitive** — extracted from R2.1g rather than duplicated | one module answering *where does the running head end and the text block begin, on this leaf* — consumed by R2.1g, R2.2, R12.2 and, later, the Gate 9 region model | scored **directly** on RunningHead/MainText assignment against hand-checked leaves, and **separately** from any downstream continuity or page-number rate. ⚠️ A primitive measured only through its consumers cannot be debugged when a consumer moves. **C3** |

### R2.5 — Multi-signal collation (NEW 2026-08-17)

🔴 **THE DEEPER DIAGNOSIS OF R2.1f: R2 REST ON ONE SIGNAL, AND ONE SIGNAL CANNOT CARRY A COLLATION.**
R2.1-CRIT already retired signatures as the primary signal because they print on only ~44% of rectos, and
replaced them with catchword continuity — **a second single signal**, which then failed. The pattern is the
error, not either signal: **a collation is a redundancy problem, and this section has been treating it as a
recognition problem.**

**Ten signals, with differing coverage and — the point — differing failure modes:**

| # | signal | grain / coverage | fails when |
|---|---|---|---|
| a | catchword → first word of next leaf | ~every leaf boundary | the head band mis-types a region; multi-word catchwords; recogniser error |
| b | signature | ~44% of rectos, first half of each gathering | absent by design on most leaves — **abstention, not failure** |
| c | **printed page number, monotone** | ~every leaf that prints one | a leaf's head is damaged or the number is unset; **most universal signal available** |
| d | verse-number continuity across the boundary | leaves carrying scripture | prelims, tables, annotation leaves carry none |
| e | expected-next chapter / book, canonical order | every book and chapter boundary | says nothing *within* a chapter |
| f | running-head continuity — a change must coincide with a book boundary | ~every leaf with a running head | recto/verso running heads may differ by design; must be modelled per witness |
| g | cross-witness correspondence (R3.2) | leaves present in ≥2 witnesses | NT is depth-1 for glyph work — this signal is **thin exactly where the corpus is thinnest** |
| h | **physical evidence — blank-margin foxing correlation** | any leaf pair worth the crop | needs blank paper in the crop; ⚠️ proven at **+0.769/+0.694 vs +0.045/+0.044 controls** (§1.4) at *page-block* scale, and **refuted at catchword scale** (R2.1d″) — coverage is a property of the AREA matched |
| i | gathering arithmetic / conjugate leaves | structural, whole-gathering | needs the gathering size, which R2.3 derives — partly circular, so it **confirms** rather than **establishes** |
| j | alignment to the archaic reference text | books with a reference | **null on the 8,383 loci with no reference** — the same blind spot §3.2 names for the residue signal |

| # | step | deliverable | acceptance |
|---|---|---|---|
| R2.5 | **Collation by agreement across independent signals** | per leaf boundary, each applicable signal reports **AGREE · DISAGREE · ABSTAIN with a stated reason**, into one table keyed by leaf boundary; signals are **never** collapsed into a single score before disagreements are read | every boundary is confirmed by **≥k independent signals**, k pre-registered per witness before the run; **every disagreement is named and enters the R2.4 defect report** — never averaged away. A boundary that no signal reaches is an **abstention that blocks**, not a pass. **C3** |
| R2.5a | **Signal independence, demonstrated not assumed** | for each pair of signals, the failure modes that would take them down together — shared recogniser, shared band geometry, shared reference text | ⚠️ **k independent signals is a lie if they share an instrument.** (a), (c), (d) and (f) all read through the head or foot band and would fall together on a band defect; (j) and (e) share the reference. Independence is **stated per pair with its coupling named**, or the count k is not what it appears |

⚠️ **THIS IS NOT A RELAXATION OF THE 0.95 BAR, AND THE DISTINCTION IS THE WHOLE POINT.** The bar stays
exactly where it is. What is corrected is the **assumption that one instrument would carry the whole
collation** — an assumption this file made twice, first with signatures and then with catchwords. R2.4 has
required *"every leaf either fits the collation or appears in the defect report — no leaf unaccounted"*
since it was written, and **that is already a multi-signal acceptance**; R2.5 supplies the signals it was
always going to need.

⚠️ **ABSTENTION AND FAILURE ARE DIFFERENT, AND CONFLATING THEM IS THE ORIGINAL R2 DEFECT.** A leaf that
prints no signature is not a leaf where the signature reader failed — that confusion is exactly what made
R2.1's first criterion unsatisfiable (R2.1-CRIT), and it is the same shape as R1.4's assumed null. Every
signal in R2.5 reports abstention **with a cause**, and an abstention never counts toward k.

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
| R3.6 | **`F` against `B` and `P`, leaf by leaf, for OT1 and OT2 — and a named-leaf supply where `F` alone holds a leaf** (NEW 2026-08-17, Sir's instruction) | a whole-volume alignment classing every leaf **present in all three · `F` only · `B`/`P` only · absent everywhere**, with each absence carrying one of R3.3's three causes | no leaf classed by arithmetic; every `F`-only leaf either promoted to a named supply or shown to be a capture artefact. **See the prose below before executing — OT1 is already largely answered, and the answer is negative** |
| R3.7 | **The 1633 NT witnesses' frontmatter and backmatter, transcribed as addenda** (NEW 2026-08-17, Sir's instruction) | `F` and `R`'s prelims and endmatter OCR'd and published as **1633 addenda to the 1582 transcript**, never merged into it | every addendum leaf carries its witness siglum and the year **1633** in the artefact itself, not only in a header; no addendum is addressable as 1582 text by any route |

🔴 **R3 IS NO LONGER STRICTLY DOWNSTREAM OF R2 — see "R2.2 is the pivot" above (2026-08-17).** R3.1's key
has a **signature** component (needs R2.1, stalled) and a **printed page number** component (needs R2.2, a
head-band reader). R3.1, R3.2 and R3.4 can start on R2.2a alone; R3.3 partly; **full Gate 0c closure still
requires R2.3/R2.4**, because a correspondence table over uncollated leaves maps leaves that may be
duplicates or made-up supplies. The per-step breakdown is tabulated in R2, not repeated here.

**Why this cannot be skipped or deferred.** §1.4 established that leaf indices do **not** correspond between
files of the same volume. Until R3.2 exists, "the same page in another witness" is not a well-formed
request, and no collation of readings is possible.

⚠️ **The "47 leaves" figure that stood in this paragraph is withdrawn (2026-08-17).** Master Plan §1.2
retired it in terms: *"the plan's early 'the NT witnesses differ by up to 47 leaves' was a statement about
scanning practice, not about textual completeness."* A library capture opens on binding boards, bookplate
and colour targets; a privately made scan opens on the title page. Quoting the raw spread here made a
photographic convention argue for a textual defect — **the precise reasoning error R3.6 below exists to
prevent**, left standing in the section that raises it. The point the paragraph was making survives intact
without it: indices do not correspond, whatever the totals.

### R3.6 — `F` against `B` and `P`, and what the existing evidence already says

**Complexity: C2 — assembly.** The alignment machinery is R3.2's; what this step adds is a second axis
(three witnesses rather than two) and a disposition per unmatched leaf. **Decision rule, pre-registered:**
if a leaf cannot be classed into one of R3.3's three causes on the leaves themselves, it is recorded
**UNRESOLVED and named**, never assigned to the likeliest cause — an unattributed leaf is a smaller defect
than a misattributed one, because only the first stays visible.

🔴 **Read this before executing: for OT1 the audit has effectively already been run, and it came back
negative.** Master Plan §1.2 carries a leaf-by-leaf table under the heading *"`F` and `P` are the same book,
leaf for leaf"*. Both close on the same words at the same printed page, and the **book blocks are equal at
1132 against 1132**. The entire 11-leaf total difference is 5 leaves of library apparatus at the front
(binding boards, the Lenox bookplate, flyleaves), 6 of binding and imaging targets at the back, less one
duplicate title page and one fewer terminal blank in `F` — and, in the section's own words, **"not one leaf
of text."** The single `F`-only leaf in that table is a **duplicate title page**, explicitly *"a re-processed
second capture of the same leaf"*: a capture artefact, not content `P` lacks.

**So the OT1 expectation that `F` supplies something is contradicted by evidence already in hand, and this
step must not be run as though the question were open there.** What remains genuinely open for OT1 is
narrower and should be stated as the deliverable it is: **`B` has never been aligned against either of them
leaf by leaf.** §1.2 describes `B`'s 1160 only in aggregate — *"12 leaves of leading apparatus, 2 trailing,
and 10 interior binding/target leaves"* — which is a count-level attribution, not an alignment. That is the
OT1 work.

**OT2 is the volume where the question is live, and it already has a step.** §1.2's OT2 table is count-level
throughout, and it puts `F` at or below the others in every category: leading apparatus **0** against `P`'s 2
and `B`'s 11; trailing **0** against 9 and 2; book block **1128** against **1135** and **1137**. There is no
category in which `F` exceeds. The residual block spread is attributed to **endmatter tables, which the three
copies carry to different extents** — and attributing that spread leaf by leaf is **already R3.5b**, which is
OPEN. ⚠️ **R3.6 does not duplicate R3.5b and must not restate its work**: R3.5b attributes the OT2 endmatter
spread; R3.6 consumes R3.5b's output and asks the separate question of whether any leaf it attributes falls
to `F` alone. If R3.5b closes with no `F`-only leaf, R3.6's OT2 half closes with it.

**The supply mechanism is the registry's existing one, not a new one.** Where a leaf is confirmed present in
`F` and absent from both `B` and `P`, `F` supplies it under the semantics `support` already defines — *"a
reading where the base has NO leaf at all, flagged as supplied with its source named."* Per named leaf,
recorded with its source, and the supplied leaf is a witness **to the copy it came from**, not to the copy it
is filed beside.

⚠️ **A supply permission does not lift a single existing bar, and the distinction decides what a supplied
leaf is worth.** `F` is in `GLYPH_BARRED` on resolution (~168 ppi; the long-ſ nub spans under 1.6 px) and is
PDF-primary, so its JP2 package is an IA render and `pixel_source()` refuses it. A supplied `F` leaf is
therefore admissible for **structure, page order, presence, and the wording of the leaf at the grain the
raster can carry** — and it may **not** ground a glyph-level call, a `ſ`/`f` adjudication, a training crop,
or CER evaluation. In practice a supplied leaf is a leaf we can say **exists and roughly what it says**,
which for endmatter tables is most of their value and for scripture would not be.

⚠️ **`F` is a PDF-primary IA render, so "dropped in derivation" is a live third cause for it specifically**
and may not collapse into "not in the copy". A leaf absent from `F` may be absent from the Fatima book, absent
from the photography, or lost when IA rendered the upload. R3.3's three causes exist for this, and `F` is the
witness most likely to exercise the third.

### R3.7 — the 1633 New Testament matter, as addenda

**Complexity: C2 — assembly.** Ordinary OCR of a bounded, mostly-prose body of leaves; the design content is
in the labelling contract, not the recognition. **Decision rule, pre-registered:** if a 1633 addendum leaf
cannot be shown to be 1633 matter on its own evidence, it is **not published** — an addendum whose setting is
uncertain is worse than an absent one, because it invites exactly the merge this step forbids.

**Why the NT is treated differently from OT1/OT2, and it is not a matter of degree.** `F`'s and `R`'s New
Testaments are the **1633 Rouen** setting (§1.1c, R8), not the 1582 Rhemes setting being transcribed. A
different edition cannot supply the text at any grain — that is what `assert_same_setting()` refuses, and
what R3.5 dissolved for. **No leaf of a 1633 NT witness may be supplied into the 1582 transcript**, and the
supply rule of R3.6 is therefore not extended here.

**But their prelims and endmatter are documentary evidence in their own right, and nothing currently captures
them.** They record what the 1633 Rouen printing said about itself — its approbations, privileges, tables and
errata — for an edition the corpus otherwise holds only as a body of scripture it may not read. They are
published as **1633 addenda**: a parallel artefact, sigil and year carried on every leaf, addressable only as
1633 matter.

⚠️ **Cross-references, and one that must not be contradicted.** R6 is the existing frontmatter/backmatter
collation section and owns the method; R3.7 is its 1633 NT extension and should reuse it rather than restate
it. **R9.7** (raised the same day) holds that `NT-1633-F` is filed as `lowres` when the registry's own
criterion makes it `support` — and R3.7's premise is exactly R9.7's argument, that `F`'s NT is a different
edition. The two are consistent and must stay so: **if R9.7's correction is made, R3.7's framing is
unaffected; if R3.7 were ever read as admitting 1633 matter into the 1582 text, R9.7 is the reason it may
not be.**

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
| R4.6 | ~~Ask the Fatima Movement for a higher-resolution capture~~ — **CLOSED 2026-08-17, NOT ATTEMPTED, on Sir's ruling** | 🔴 **Struck rather than deleted, so it is not re-proposed.** Sir has ruled that no better scan is obtainable and no further copy will be found. The step is therefore not deferred, not blocked and not pending — it is **out of the realm of possibility**, and a step whose deliverable cannot be procured is not an OPEN step. ⚠️ **The consequence is architectural, not merely administrative**: `F` stays `lowres`/`GLYPH_BARRED` permanently, so OT1 and OT2 hold glyph-capable depth **2** and the NT holds **1**, for good. **The depth we have is the depth we design for**, and any plan whose viability rests on acquiring a witness is not a plan. This ruling is also what forces §7.7's escalation to route into **pipeline capability** — with acquisition closed, building the mechanism is the only escalation resource class left, which is why that redesign was not optional | **CLOSED — not a completion.** Recorded so the negative is not re-asked, per R4.6's own original acceptance (*"if not, the negative is recorded so it is not re-asked"*), which is satisfied by a ruling as much as by a reply |
| R4.7 | 🔴 **The §10 citation that has never had an id** (NEW 2026-08-17) | §10 *Blocking* has carried *"one citation carried unverified from earlier work and **load-bearing for §3.2's gate** — resolve or delete"* with **no R-number**, so it appears in no step table, no OPEN list, and no audit. §3.2's gate is **Gate 9 — the geometry gate**, which makes this an unverified citation under the model this project is now prioritising | the citation is **resolved against its source or deleted**, and §3.2's gate is restated without it either way. ⚠️ **An unnumbered blocker is a blocker that cannot be tracked** — this one survived because "Blocking" prose is not parsed by anything, which is the §0.6 failure mode reaching the constitution's own open list. **C1** |

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
| R6.4 | Collate 1635 prelims against 1609/1610 | a difference report: what the second edition adds, drops and rewords in Approbatio, Preface, Tables, errata | every difference cited to a leaf in each edition; **no difference asserted from memory of the text** — 🟡 **PARTIAL, NOT DONE.** The 1635-vs-1609 half is complete, report at `COLLATION-1635-vs-1609.md`; **OT2/1610 prelims are outstanding and this step stays OPEN until they are collated.** ⚠️ Relabelled 2026-08-17: the row previously carried a bare completion marker with the outstanding half in a trailing clause, so it scanned as complete while blocking work remained — and it was the FIRST thing `test_open_register_consistency.py` caught on its first run, having been written for a different conflict entirely. **A completion marker qualified by a later clause is still a completion claim; the qualifier does not travel with the word** |
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

**Complexity: C1 across R5.1–R5.2c** (restated 2026-08-17 from a 6h ceiling) — the assertions are
mechanical once the manifest exists, and the manifest is a traversal. **Decision rule, pre-registered and
unchanged:** if the three base exemplars' manifests cannot be produced, R5.2a/b ship on the two
witness-independent clauses (bit depth,
grey levels) with the dimension clause explicitly **DEFERRED and named in the guard's own output**, and
R5.1 continues as its own step. The guard must not wait on the manifest, because a two-thirds guard that
runs beats a three-thirds guard that does not exist — which is the state this section has been in.

| # | step | deliverable | acceptance |
|---|---|---|---|
| R5.1 | Raster manifest per witness | `witness/build_raster_manifest.py` → `witness/raster-manifest.json`: per leaf, the resolved path, native dimensions, mode/bit depth, distinct grey levels, and a content checksum, keyed by witness id | manifest complete for the three base exemplars, **built through `witnesses.pixel_source()`** so it cannot describe a raster the corpus would not serve; regenerating it twice is byte-identical — 🟢 **COVERAGE DONE 2026-08-10**: **3,122 leaves** — NT-1582-B 812 · OT1-1609-B 1,160 · OT2-1610-B 1,150 — `truncated: false`, and **0 rasters on disk without an entry**, checked against `pixel_source()` rather than assumed. **3,113 leaves moved UNKNOWN→CHECKED** on the dimension clause. 🟢 **DETERMINISM PROVEN 2026-08-10**: a second full build (3,122 leaves, `truncated: false` — a real run, not an early exit) is **byte-identical**, sha256 `44290ad7…f8e0` for both, and the canonical file was not clobbered. `--out` was added to make this runnable at all: the single hard-coded output path meant the second run destroyed the first — **an acceptance clause that cannot be executed is not an acceptance clause**, and this one had stood unexecutable since it was written. ⚠️ The byte comparison is only valid because the writer uses `sort_keys=True`; `coverage-audit-verse.json` is the standing counter-case, order-nondeterministic on ties, where the same test would prove nothing |
| R5.2a | **Build** the derivative-contamination guard (Gate 0d) | `witnesses.assert_admissible_raster(wid, path)` — bit depth > 1 · distinct grey levels > 64 · dimensions match R5.1's manifest where it exists, and say so where it does not | called at the pixel-consuming entry points; a witness with no manifest entry yields **UNKNOWN, printed**, never a silent pass (R1.4) |
| R5.2b | Prove the negative | `witness/test_raster_admissible.py` feeds it (i) `M`'s 1-bit CCITT leaf, (ii) a PDF render of a known-good leaf, (iii) a dimension-mismatched leaf | each **raises**, each for the stated clause; the known-good base leaf passes — a guard that refuses everything passes (i)–(iii) for the wrong reason |
| R5.2c | Wire it to the chain, and prove the wiring | the assertion is reached from the real read path, not only from the test | injecting a rendered leaf into an actual recognition call **raises**; asserted by calling the entry point, not by reading it — the R9.3 pattern |
| R5.3 | 🔴 **Name the 9 leaves the dimension clause never checked** (NEW 2026-08-17) | R5.1 moved **3,113** leaves UNKNOWN→CHECKED against a manifest of **3,122**. The status row reported the manifest as complete and left the 9-leaf gap to be noticed by subtraction | the nine leaves are **listed with the reason each was not checked**, and each resolves to CHECKED or to a stated, permanent exemption. ⚠️ **A residue that only exists as the difference between two numbers is a residue that becomes zero the next time either number is quoted** — Gate 0d is currently carried as "enforced on all three clauses" on this basis. **C1** |

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
| R9.6 | 🟢 **DONE 2026-08-14 — and the six were TWENTY.** One derived root, `originaldr_reconstruction/project_root.py`, imported by every consumer. Measured before the fix: **20 modules / 33 literals** named the dead root, and `core/.scratch/originaldr-project` was **absent in its entirety** while `projects/originaldr/reconstruction/{reads,consensus}` held 10 and 76 entries. ⚠️ **FOUR modules `mkdir(parents=True)` and WRITE** — `detect_sources`, `detect_s_dismas`, `detect_ocr_consensus`, `build_consensus` — not the two recorded; running any would have recreated the dead tree and written the anchor reads into it, leaving a directory that looks populated and current. `witness/test_project_root.py` exits 0, **injection-proven on all three checks** (restated literal · relative traversal · resurrected tree) |
| R9.6a | 🟢 **DONE 2026-08-14 — and BOTH Madueke sources were resolved by measurement, not by name.** They did not migrate with the project; they live under `imports/.../transcriptions/madueke/`. **`madueke-a` CONFIRMED**: all 1334 chapter `<title>`s match `madueke_a.json`'s loci and **all 35,809 recorded verses appear verbatim (100.0000%, whole corpus)** once `<sup>` verse markers and the `^` annotation anchors are stripped — the same characters the reads strip. 🔴 **`madueke-b` REFUTED**: the same-named `merged.txt` matches only **2.05%**. `madueke_b.json` records `locus: madueke-b/pdf`, `method: pdf-bbox-two-column` — it was built from the PDF by de-interleaving the columns, exactly as `ingest_madueke_b.py` documents. **`merged.txt` is the RAW `pdftotext` dump taken BEFORE de-interleaving**, so its verse text is spliced across columns (*"In the beginning God created heaven and **fruit after his kind**..."*). ⚠️ **This is precisely the failure R9.6a was written to prevent**: repointing on the matching filename would have fed column-interleaved text to five consumers and every comparison would have silently degraded. Raised as **R9.6b** |
| R9.6b | **Five consumers read `madueke-b/merged.txt`** — `ocr_sample`, `build_apparatus_gapfill`, `build_apparatus_attestation`, `collate_witnesses`, `ocr_validate` — for apparatus gap-fill and collation, not for the verse reads. Whether the interleaved dump is fit for THAT purpose is a separate question per consumer and is **not yet answered** | each consumer either re-pointed at a de-interleaved extract or documented as tolerant of interleaving, with the evidence stated | **OPEN. C2 — assembly** (five consumers, each a separate fitness question; restated from a 3h ceiling 2026-08-17); if a consumer's fitness cannot be established, it is made to RAISE rather than left reading a source of unknown fitness — a decision rule pre-registered before the work |
| R9.7 | 🔴 **`NT-1633-F` IS FILED UNDER THE WRONG ROLE, AND THE REGISTRY IS THE SIDE THAT IS WRONG** (raised 2026-08-17, found while reconciling the companion docs) | `witnesses.py` gives `("NT","F")` `year=1633, role="lowres"`. But the registry's OWN definitions separate the two roles by *setting*, not by resolution alone: `lowres` is **"a genuinely independent copy whose DIGITISATION resolves too little"** — a poor capture **of the setting being transcribed** — while `support` is **"a copy of a DIFFERENT edition, admitted for named leaves only"**. `F`'s New Testament is the **1633 Rouen** setting throughout (§1.1c, R8); the transcribed NT setting is **1582**. By the registry's own criterion it is `support`. ⚠️ **`OCR-OVERVIEW.md` and `OCR-WALKTHROUGH.md` both describe it as support, with reasoning — the two documents were RIGHT and the registry is the outlier.** The companion-doc pass deliberately did **not** edit them to match, which would have propagated the error into the only places that had it correct | (1) the registry record is corrected to `role="support"`; (2) `test_counts_vs_doc.py` is extended to compare **role-by-role** against the registry — which is what **R9.5a already promised and does not do**: it compares leaf counts and primary raster, reads §1.1's table rather than the companions', and exits 0 today, so R9.5a's own acceptance is **unmet and R9.5a stays OPEN**; (3) a guard proves a cross-setting collation partner is refused | **OPEN. C2 — assembly.** ⚠️ **Why this is live rather than cosmetic, and why it lands on R2/R3 specifically:** `ROLE_VERSE_SCOPE` gives `lowres` the scope `"collation"`. Collation is precisely the work R2 and R3 are doing now, so the wrong role does not merely mislabel `F` — it **admits a 1633 book as a collation witness to the 1582 setting**, which is the conflation `assert_same_setting()` exists to refuse. It is masked today only because the guards refuse `F` on the *identifier* and on `GLYPH_BARRED`, i.e. for reasons unrelated to the defect: **the right answer is currently being produced by the wrong mechanism**, which is the condition under which a change elsewhere silently unmasks it. `attests_transcribed_setting()` already records the near-miss in its own docstring — *"collapsing them is how NT-F stayed admissible"* — so the failure mode was seen and the role was not corrected. Decision rule, pre-registered: if correcting the role changes any published figure, that figure is **superseded and re-derived**, never annotated |
| R9.8 | 🔴 **`lowres`'s GLYPH BAR IS WRITTEN IN PROSE AND ENFORCED BY NOTHING** (verified 2026-08-17) | `ROLES["lowres"]` states the bar in terms — *"NOT training data, NOT CER evaluation, and it may not adjudicate long-s against f"* — but `GLYPH_BARRED` holds only `F` and `X`. Measured, not inferred: `glyph_source("NT","M")` **returns a usable PDF path with no refusal**, and `admissible("NT")` answers `['NT-1582-B', 'NT-1582-M', 'NT-1633-R']`. ⚠️ **Two distinct defects in one call.** (a) `M` is `lowres` and is named as glyph-admissible, so the ſ/f bar can be walked straight past. (b) `NT-1633-R` is a **different setting** and is named as admissible for the 1582 volume, which `assert_same_setting()` exists to refuse — `admissible()` is answering *"not barred by resolution or derivation"* while its name, and every caller, reads it as *"may carry a glyph call for this setting"* | (1) the role's glyph bar is derived from the ROLE rather than restated in a second table — `GLYPH_ROLES = {base, surrogate, support}` is the shape already proven in `glyph_witnesses()`; (2) `admissible(vol)` takes a **setting**, not a volume, or is renamed to say what it actually computes; (3) injection-proven on both defects: a `lowres` witness must be refused a training crop, and a cross-setting witness must not appear in an admissible list | **OPEN. C2 — assembly.** ⚠️ **This is the SIXTH instance of the project's signature defect** — a correct rule with nothing reading it (Gate 0f · Gate 0d · §7.7's escalation ladder · `audit_prereq_ceilings` string granularity · its section granularity · this). It was found the same way as four of the others: **by building the consumer**. `glyph_witnesses()` was written to answer depth honestly, returned the wrong answer on its first run, and the wrong answer came from the registry rather than from the new code. Decision rule, pre-registered: if closing the hole changes what any consumer may read, every figure derived through that consumer is **superseded and re-derived**, never annotated. ⚠️ Do **not** weaken `ROLES`, `GLYPH_BARRED` or `ROLE_VERSE_SCOPE` to make the call agree — the prose is right and the enforcement is missing, which is the direction the fix must run |

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
   starts."* ⚠️ **The UNIT in this clause is superseded as of 2026-08-17** — hours are abolished
   project-wide and the requirement is now a **complexity class + candidate list + decision rule** (see
   the Open-items register). The *force* of the clause is untouched. ⚠️ **This note said the Master Plan's
   §0.5 "still says hour ceiling" and was already stale when written** — the two files were being revised
   in the same sitting, and this sentence described §0.5 as it stood at the start of it. §0.5 now carries
   the C1–C4 scale itself. Corrected 2026-08-17. **The pattern is worth keeping**: a cross-file assertion
   about another document's *current* wording is a measurement, and it goes stale exactly as fast as the
   other file changes. Assert the rule, cite the section, do not quote its state.
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
| R10.1 | Ceilings and decision rules, enforced | every **OPEN** step carries a **complexity class + candidate list** and a decision rule written **before** work starts (⚠️ **was "an hour ceiling" until 2026-08-17**); `witness/audit_prereq_ceilings.py` parses this file's step tables and section prose and lists the OPEN steps carrying neither | ⚠️ **This is an AUDIT, not a guard, and the distinction is load-bearing.** Only R2, R5 and R10 carry ceilings today, so it exits **1 over ~30 steps** — and **exit 1 is the healthy state until each section is next touched.** Filing it as a guard would force one of the two things this project forbids: bulk-inventing ceilings nobody reasoned about, or weakening the check until it passes. Coverage is reported as a **fraction that must rise**, never as a pass. Proven by injection: strip R2's ceiling → the count rises by one and R2 is named; restore → it falls back. ⚠️ **Reaching a ceiling ALERTS that the approach needs redesign and never closes the step** (§0.5) |


⚠️ **THE FRACTION FELL, 25% → 17%, and that is a real signal rather than a bookkeeping artefact (2026-08-10).** It read `10/40` and then **`6/35`**: five OPEN steps closed (R5.1, R5.2a/b/c, R9.2c) and **four of the ceilings went with them**, because §0.5 ceilings had been added precisely to the sections that were next touched. So the ceilinged pool is depleted by progress, and the OPEN remainder is *more* unceilinged than before, not less. **R10.1's rule "the number must RISE" is therefore not satisfied by doing the work — only by writing ceilings for sections nobody is about to touch**, which is the harder half and is exactly what the audit is for. Recorded rather than restated: a metric that moves the wrong way when the project progresses is worth understanding before it is corrected.

🟢 **AND THEN IT ROSE, 17% → 29% (`6/35` → `12/41`), 2026-08-11 — by the harder half, exactly as predicted.** Writing R2.1a–f as six sub-steps *inside a section that already carries a ceiling and a decision rule* added six OPEN steps and six ceilinged ones at once. That is the intended mechanism and it is worth naming: **the fraction rises when work is PLANNED under a ceiling, not when work is COMPLETED.** Closing steps lowers it; planning them properly raises it. A coverage metric that rewards planning and penalises completion is behaving correctly here only because the thing being covered is *the plan*, and R10.1 should not be "fixed" to reward completion instead. ⚠️ The corollary is a real risk: the fraction could be inflated by decomposing a ceilinged section into ever-finer sub-steps. It is a coverage number, not a progress number, and must never be read as the latter.
⚠️ **The two paragraphs above sat BETWEEN two rows of one table** until 2026-08-17, which silently
terminated it and left R10.2 rendering as a headerless fragment. Repaired by giving the remaining rows
their own header. A file whose own status table does not render is the §0.6 failure mode in typography.

| # | step | deliverable | acceptance |
|---|---|---|---|
| R10.2 | The PROVISIONAL convention, and the register that uses it | a stated form for a non-citable figure (value · CI · what is undersized · what would settle it), plus **`PROVISIONAL.md`**: every figure and artefact currently standing on undersized or pre-gate evidence, named | the 51 ground-truth files are listed with the gates they precede; **every NT cross-source figure published before 2026-08-09 is listed or recomputed** (R9.4b's labelling half); **every parity-spread figure published before 2026-08-10 is listed or restated** (R9.2c-4 — they were the best witness's own pass rate, not a spread); no listed figure is cited in a companion without the label. ⚠️ **Add to the register: 0.312 must never be cited as a lower bound** (R2.1f) and **0.9396 must never be cited as this project's best recogniser** until R2.1b establishes comparability |
| R10.3 | 🔴 **The ceiling audit must parse complexity classes** (NEW 2026-08-17) | `witness/audit_prereq_ceilings.py` currently matches hour-ceiling phrasing. With hours abolished it will score every restated step as carrying **nothing**, and the fraction will collapse for a reason that is the opposite of the truth | the audit recognises **complexity class + candidate list + decision rule**; **injection-proven both ways** — strip a class → the step is named; restore → it is not. ⚠️ Until this lands the audit's exit-1 count is **NOT CITABLE**, and the audit is **not** to be deleted, silenced or have its threshold relaxed in the interim — that would be fixing the instrument by removing it. **C1** |

**Complexity for R10 itself: C2.** **Decision rule:** R10.1's audit ships parsing only the step tables if
prose parsing proves the harder half — a decision rule on a rule-checker is not a joke, it is the first test of whether
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

**§0.5 compliance.** Every OPEN step below carries a **complexity class** and a **decision rule**
pre-registered before the work (⚠️ restated 2026-08-17 from hour ceilings **6h · 2h · 3h · 1h**):
**R11.2a C2** — 33 references across 23 files, each its own disposition question · **R11.2b C1** — extend a
parser that already runs · **R11.3a C2** — a pin plus a content hash per tree · **R11.4 C1**. R11.5 is
blocked by construction and takes a class when it unblocks, not before — classing work that cannot start
would inflate R10.1's coverage fraction without anyone having reasoned about the step, which is the
corollary risk R10.1 names. **Exhausting a candidate list ALERTS that the approach needs redesign; it never
closes the step and never accepts the shortfall.**

| # | step | deliverable | acceptance | complexity + decision rule (§0.5) |
|---|---|---|---|---|
| R11.1 | **Track the harness CODE**, not its outputs | 33 files / 432 KB moved `\.scratch/mask-eval/` → `core/tests/fixtures/gold/harness/`. The ~2 GB of `ws/`, `diagnostics/`, `text/` stay machine-local behind `MASK_EVAL_DATA`, defaulting to `.scratch/mask-eval` and **raising with the path named** when absent | the three consumers run to **byte-identical output** with the untracked original **deleted** | 🟢 **DONE 2026-08-14.** C2 |
| R11.2 | **Guard: tracked code may not IMPORT from `.scratch/`** | `core/tests/fixtures/gold/test_no_scratch_deps.py` — `sys.path` mutations found via `ast`, docstrings excluded, unparseable files fall back to regex rather than passing | exits 0; **injection-proven** | 🟢 **DONE 2026-08-14.** C1 |
| R11.2a | **Disposition the 71 gitignored DATA references** | `audit_scratch_data_paths.py` — each reference resolved to (a) machine-local root made env-overridable **and raising**, (b) dead tree → R9.6, or (c) should be tracked → R11.1 | audit exits 0 | **OPEN. C2 — assembly** (restated from a 6h ceiling 2026-08-17). Candidate list exhausted without the audit reaching 0 ⇒ **ALERT that the approach needs redesign** — the remainder is *not* accepted, and entries are **never** added to `SANCTIONED` to make the number fall |
| R11.3 | **`gen_dr_original`'s silent fallback → an explicit raise** | `_require()` names every path tried; resolution is **lazy** (PEP 562 module `__getattr__`) so importers wanting only slug lists are unaffected | `MADUEKE` raises; `import gen_dr_original` still succeeds | 🟢 **DONE 2026-08-14.** C1 |
| R11.3a | 🟢 **DONE 2026-08-14.** **Pin the Sabates_A acquisition** | clone `janvier-s/original-douay-rheims` at a **recorded SHA** into a tracked location, or a tracked acquisition script that does | `acquisition/sabates-a-pin.json` + `acquire_sabates_a.py --clone/--verify/--repin`. Pin: `janvier-s/original-douay-rheims` @ **`0bf4218b`** (2026-04-18, CC0). **Verified on the live remote**: `ls-remote` shows that SHA at both `HEAD` and `refs/heads/main`, **0 commits behind**, local tree clean | 🟢 **DONE. C2.** ⚠️ **The commit alone is not the pin** — it proves which revision was *requested*, not which bytes *arrived*. The pin also carries a content hash per tree actually read (`bible/raw` 77 files · `reference` 26 · `annotations` 394), taken over sorted `(relpath, sha256)` so it is order-stable and content-exact. **Injection-proven on the case a SHA cannot catch**: one byte appended with the commit unchanged → FAIL on both the dirty-tree check and the `reference` hash; restore → exit 0. `--repin` is a separate explicit action, because re-pinning to today's HEAD is the very unreproducibility this step removes |
| R11.4 | 🟢 **DONE 2026-08-14.** **Fold `purge_empty_ocr.py:23` into R9.6** | R9.6's module list named five restatements of the migrated root; this is a **sixth**, and it reaches the dead tree by relative traversal (`../../../../../.scratch/…`) rather than by naming it, which is why the original sweep missed it | `witness/test_project_root.py` covers it, and the guard's second check is the traversal form specifically | 🟢 **DONE.** C1. ⚠️ **The lesson generalises beyond the one line**: R9.6 recorded six restatements because it searched for the root's *name*; the true count was twenty, and the traversal form was invisible to that search entirely |
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

## R12 — Layout typology, the prerequisite nobody had written (NEW, 2026-08-17)

**Discharges** §3.2, and it is a **prerequisite of Gate 9** rather than a part of it. **Status: OPEN,
nothing built.**

### The finding

**§3.2 specifies which region classes the geometry model must emit. It does not specify how the model knows
which classes are ON THE PAGE IN FRONT OF IT** — and those are different problems. A model asked to find
`Marginalia` on a title page, or `VerseNumber` on the Approbatio, is being asked to find something that is
not there; §3.2's own rule 7 already records what that costs, in the one case where it was noticed:

> **Marginalia negatives are mined explicitly** — only leaves with confirmed apparatus coverage contribute
> Marginalia-negative pixels, or every unlabelled marginal block becomes an implicit negative and teaches
> the model to suppress the class.

⚠️ **That rule is the general problem stated for one class.** Every class has the same failure: a leaf that
does not print class `C` contributes evidence *against* `C` unless the model knows the leaf is not a leaf
that prints `C`. **The classifier must run first, and its output must be checkable — which means each page
type has to carry its REQUIRED and FORBIDDEN classes, hardened before the model is trained.**

### The eight archetypes, each grounded in evidence already in this project

⚠️ **These are proposed from the documented evidence, and the frequency of each in the corpus is
UNMEASURED.** R12.1 exists to measure it; until it runs, this list is a hypothesis about the book's
structure, not a census of it.

| id | archetype | required classes | forbidden / absent | grounding |
|---|---|---|---|---|
| **A** | plain text page | MainText · RunningHead · Catchword | Marginalia · ChapterHeading · Argument | the R2 working case, leaves 400–431 |
| **B1** | text + **disjoint** marginal apparatus | MainText · Marginalia · RunningHead · Catchword | — | `gutter_probe.py`: `jp2-S06` p74 body line-ends `x1≤1647`, margin `x0≥1673`, **a real 26px gutter**; the bound adopted at **0.746, the measured gutter midpoint**, lifted ch15 **64→66** |
| **B2** | text + **interleaved** marginal apparatus | MainText · Marginalia | — | 🔴 `gutter_probe` reports **OVERLAP on all eight** ch3/ch6 leaves. Kraken merged margin text **into the body line object**: `ch3 p26 "gaueſt me to be my fellow companion, gaue me of the tree, & I did eate. the diuel that"`. **No x-threshold can split words that arrived inside one line object** — B2 is not a tuning of B1, it is a different problem |
| **C** | chapter opening | ChapterHeading · Argument · DropCap · MainText | — | `chapter_open_probe.py` locates *"the printed heading, in display capitals the recognizer mangles"*, the italic argument, and verse 1 |
| **D** | book opening | BookTitle · Argument · MainText | VerseNumber (above the opening) | `COLLATION-1635-vs-1609.md` §1: *The Argument of the Book of Genesis* is **its own leaf** (1609 leaf 29) |
| **E** | annotation leaf | Annotation · NoteRef · RunningHead | VerseNumber | §4.2's inventory: note-reference marks `*` `†` `‡` `¶`, patristic citations (`Theod.`, `S. Aug. Pſal 52`, `Greg. ho.`), **Greek and Hebrew sorts**; *"the apparatus is roughly half the book"* |
| **F** | 🔴 **MIXED LEAF** | two archetypes on one leaf, with a boundary | — | `chapter_open_probe.py`: *"MIXED LEAF: annotations above, this chapter's opening below — **dropped WHOLE today**"* |
| **G** | prelims | DisplayTitle **or** ProseBlock · RunningHead | VerseNumber · Catchword (varies) | title page · APPROBATIO · Preface · Proemial Annotations (`COLLATION-1635-vs-1609.md` §1) |
| **H** | tabular matter | TableBlock · Brace · Rule | MainText · VerseNumber | *The Summe and Partition of the Holy Bible* · endmatter Tables · errata; §4.2 lists **braces and printers' rules** as sorts the transcript must carry |

### 🔴 F IS THE EXPENSIVE ONE, AND IT IS CURRENTLY DATA LOSS

`_is_annotation_leaf` **excludes a whole leaf** when a leaf carries annotation matter, so a mixed leaf —
annotations above, a chapter opening below — is **dropped entire**, discarding the scripture on it. This is
not a bug in that function; it is the correct behaviour *for a system with no layout typology*, because
without one there is no way to keep the bottom half. **F is therefore both the strongest argument for R12
and the first thing R12 should pay for.** ⚠️ **How many leaves are dropped this way is UNMEASURED** —
R12.1 must count them before anyone estimates the value of fixing it.

### Steps

| # | step | deliverable | acceptance |
|---|---|---|---|
| R12.1 | **Census the archetypes before modelling them** | over a stratified leaf sample per volume, each leaf assigned an archetype **by hand**, with the count of mixed leaves (F) and the count currently dropped whole reported separately | every archetype either **ATTESTED with a frequency and exemplar leaves**, or **NOT FOUND in this volume** — no archetype carried on plausibility. ⚠️ Same discipline as §4.1's type census: *a class the model never sees cannot be output, and a class asserted but not present invites the model to hallucinate it*. **C2** |
| R12.2 | **The classifier, and its REQUIRED/FORBIDDEN contract** | page-type classification emitting an archetype per leaf, and for each archetype the required and forbidden region classes as **data, not prose** — so a region model's output can be checked against its own page type | classification accuracy on a **held-out, never-trained-on** leaf set, reported **per archetype** — never as a single mean, which would hide the rare archetypes that are precisely the ones causing the losses. A forbidden class emitted on an archetype is a **hard failure**, not a scored error. **C3** |
| R12.3 | **Mixed leaves become splittable, not droppable** | archetype F carries a boundary, and the matter on each side is routed to its own archetype | the leaves currently dropped whole by `_is_annotation_leaf` are **measured before and after**, and the scripture recovered is reported per leaf. ⚠️ A recovered leaf is only recovered if the recovered text is **evaluated**, not merely emitted. **C3** |

⚠️ **R12 gates Gate 9, and Gate 9's thresholds cannot be read without it.** Gate 9 sets *marginalia recall
≥0.85 / precision ≥0.90*. **On which pages?** Marginalia recall over a corpus that is ~half apparatus means
something entirely different from marginalia recall over archetype-B leaves only, and the two numbers are
not comparable. **The threshold is not well-defined until the denominator is** — which is R12.1.

---

## R2.1b RESULT — ✅ DONE 2026-08-27c. The highest headline accuracy is the WORST model here

**`witness/audit_recog_holdout.py` → `witness/build_recog_gold.py` → `witness/score_recognisers.py`.**
R13.1 was blocked on this step because *wiring an unselected model replaces "no model" with "an
arbitrary model", which is the harder defect to see.* A model is now selected on measured evidence.

🔴 **THE FINDING: THE HEADLINE RANKING IS BACKWARDS, AND IT IS NOW MEASURED RATHER THAN SUSPECTED.**
This row has warned since 2026-08-17 that *"`0.9739 > 0.9396` IS NOT A FINDING"* because the five
figures are per-arm accuracies on **different splits**. Scored on ONE set held out from all five:

| model | headline (NON-comparable) | pooled content, common set | ſ recall | class wins |
|---|---|---|---|---|
| **`dr_v3_armB`** | 0.9694 | **0.9575** | 0.9302 | 🏆 **7 of 7** |
| `reichenau_dr` | **0.9396** — *the figure every document cites* | 0.8902 | 0.9302 | 1 |
| `dr_v3_armA` | **0.9739** — *the highest on disk* | **0.8597** — *the lowest un-vetoed* | 0.9302 | 0 |
| `reichenau_dr_ho` | 0.9230 | 0.8693 | **0.8372** | 🔴 **VETOED** |
| `dr_armA` | 0.9349 | 0.8423 | **0.6744** | 🔴 **VETOED** |

**The model with the highest validation accuracy on this disk is the worst of the three that clear
the veto.** The cited 0.9396 wins one class of seven. ⚠️ **`0.9739` and `0.9396` must still never be
quoted as a ranking** — this table does not make them comparable, it replaces them with a figure that is.

⚠️ **THE ſ-SURFACE VETO IS APPLIED FIRST AND ABSOLUTELY, NEVER AS A TIEBREAK**, and it earned itself:
it disqualified **`reichenau_dr_ho`**, the model built specifically for honest generalisation, which
**modernises the long s**. Its pooled content (0.8693) beats `reichenau_dr`'s — and that is precisely
the trade the two-metric design exists to refuse. This edition's entire re-OCR ladder is about
recovering ſ; a recogniser that silently drops it scores well on content and is useless here.

📌 **AND THE PER-CLASS BREAKDOWN SAYS SOMETHING NO POOLED FIGURE COULD.** Every model is near-perfect
on MainText (0.987–0.995) and collapses on the direction line — `SG` runs **0.4667–0.7500** and `CW`
**0.5333–0.8000** across the five. **A pooled mean would have been a scripture benchmark wearing a
per-class label.** It also retro-justifies R2.1b's original purpose: a confidence floor for
`collation_read`'s direction-line reader is needed precisely because that is where recognition is
weakest. ⚠️ `dr_armA` collapses to **0.5543** on `AR` — italic is where a modernising model fails.

**THE SELECTION RULE WAS PRE-REGISTERED** in `score_recognisers.py` before its first run: a ſ veto at
0.90 applied first; selection on **class wins**, not a pooled mean (R14.4's policy); ties broken on
pooled accuracy; and **NO SELECTION is a permitted outcome** if the top two tie — picking a winner
out of a tie would be choosing on noise and calling it a measurement. No tie arose: 7–1–0.

⚠️ **THE SET, AND ITS LIMITS, STATED.** 51 hand-keyed lines over 7 region classes from OT1-1609-B
leaves 400-419, **one witness, one operator, not blind**. Truth was keyed **from the page** and is
diplomatic — long-ſ preserved, the page's own typos kept (leaf 400 prints *"to fight iu Edrai"*).

🔴 **AND THE OBVIOUS SHORTCUT WAS POISON.** GOLD-HEADBAND carries a `text` field for all 121 entries
and it is **the incumbent recogniser's output**, kept so a human could assign a LABEL — its own
`_doc` says so, and its errors are visible: leaf 402's running head reads `NVMENE` for **NVMERI**,
leaf 400's side-note `X. Og Alaine.` for **K. Og ſlaine.** Scoring five candidates against it would
have measured **agreement with the instrument being replaced** and read as validation — the identical
defect `audit_label_sources.py` records for `scan_marginal`.

⚠️ **TWO CUTTING DEFECTS WERE FOUND BY LOOKING AT THE SHEETS, NOT BY A NUMBER.** (1) The first cut was
**by row**, which put a page number, a running head **and** a side-note into one image labelled `RH`
— a row is not homogeneous in region, which is `region_head`'s founding observation and the reason
`region_segments` exists. (2) The pad clipped leading sorts (`eople of Chamos`). Both fixed before
keying. **12 of 63 crops are still EXCLUDED with a stated reason each** — two baselines in one image
(the R2.2k row-chaining defect, on italic), a clipped first or last sort, or two margin columns
merged — counted, never silently dropped. ⚠️ **7 of the 12 are MarginNote**: the cutter fails hardest
on the class this edition is built around, leaving `MN` the thinnest class at 5 lines. Said, not hidden.

⚠️ **IT DISCHARGES NO GATE.** It establishes a comparable ranking on one held-out set, per region
class, with the losers published. Whether the winner is good enough is Gate 11 (**R13.3**), which
needs GOLD-LAYOUT (**R16.1**). ⇒ **R13.1 is UNBLOCKED.**

---

## R13 — The trained recogniser is not in the path that needs it (NEW, 2026-08-17)

**Complexity per sub-step**: declared in each row, C1–C4. **The pre-registered decision rule for
this section**: *a wiring step is DONE when a reading's provenance names its model and a model swap
changes that name (injection-proven); a measurement step is DONE when it reports against a threshold
written BEFORE it ran, and a null result is published rather than retried into significance.*

**Discharges** §4 in the negative: it names a defect in the *plumbing* between components, not in either
component. **Status: OPEN, verified on disk.**

### The finding

🔴 **`grep` over `gen1_*.py`, `s_arbiter.py` and `chapter_campaign.py` returns NOTHING for
`reichenau_dr` or `dr_v3_armA`.** Verified 2026-08-17. The ſ-faithful fine-tune this project spent its
Rung-2 effort producing **is not referenced by the modules that consume recognition output**; per
`CAMPAIGN-STATUS.md`, *"the attesting arm is the base scan OCR, not the fine-tuned recognizer"* —
`gen1_r3` passes `t["old_text"]`, the incumbent page-model text from the stored corpus OCR.

**Why this is the same shape as Gate 0f and Gate 0d, one level down.** Gate 0f was a rule no code read.
Gate 0d was a rule no code implemented. **R13 is an artefact no code loads.** In all three the component
exists, the document says it is in force, and nothing consumes it — and in all three the defect was
invisible precisely *because* the thing existed and could be pointed at.

⚠️ **What is NOT established, and must not be asserted while it is unestablished.** That wiring the
fine-tune into the attesting arm would improve the board is **a hypothesis, not a finding**.
`CAMPAIGN-STATUS.md` reports **1,142 cells** that R3 has already read correctly and that are refused for
one reason — `CONTENT OK, ſ-SURFACE OPEN` — and those cells are plausibly reachable by an attesting arm
that can see ſ. **Plausibly is not measurably.** R13.1 is a wiring step and R13.2 is the measurement; the
cell count is **not** claimable until R13.2 runs.

| # | step | deliverable | acceptance |
|---|---|---|---|
| R13.1 | **Wire the selected recogniser into the attesting arm** | the model chosen by **R2.1b** (not assumed — see the comparability warning there) reachable by `s_arbiter`/`gen1_*`, with the model id **recorded in the artefact** so a reading can always name the recogniser that produced it | a reading's provenance names its model; **injection-proven** — swap the model, and the artefact says so. ⚠️ **BLOCKED BY R2.1b**: wiring an unselected model in would replace "no model" with "an arbitrary model", which is the harder defect to see. **C2** |
| R13.1a | 🟠 **PARTIAL 2026-08-27d — the mechanism and its proof are DONE; the arm conversion is NOT** | `witness/recogniser.py`: one entry point, model read from R2.1b's selection file and never named in the module, every reading stamped with the model id **and the artefact's digest**, and a **refusal** rather than a default when no selection exists. `witness/test_recogniser_provenance.py`: the injection proof | ✅ 5 of 5 — swapping the model changes the name, the digest **and the reading** (5 of 12 crops), and hiding the selection raises. 🔴 **STILL OPEN**: no `gen1_*` or `s_arbiter` module imports it yet, so `old_text` remains the stored corpus OCR. **That conversion changes campaign artefacts and is a deliberate act, not a side effect.** **C2** |
| R13.2 | **Measure the ſ-surface effect, with the cells counted before and after** | the `CONTENT OK, ſ-SURFACE OPEN` population re-run through the wired arm | the change is reported **per cell class** and against the pre-registered δ; **a null result is published, not retried into significance** (§7.6's regression rule). ⚠️ **Do not report the 1,142 figure as recovered cells in advance of this step.** **C3** |

---

## R14 — THE ADAPTIVE VISUAL AGENT (NEW, 2026-08-25, by Sir's ruling)

**Complexity per sub-step**: declared in each row below, C1–C4. **The pre-registered decision rule for
this section**, written before any step runs: *a step is ADOPTED only when its own Gate 9 clause passes
on a held-out set it was not built against; a step that misses its clause is OPEN and blocks the
deliverable; no step may be closed by lowering its clause, and no clause may be written after seeing
the result it will judge.* ⚠️ Gate 9.6, 9.7 and 9.8 carry no numbers precisely so that this rule has
something to bind: each number is written from its characterisation run, before the step it judges.

**Discharges Masterplan §3.0, which GOVERNS.** R14 is the work R2.2's re-scope hands off to, and it is
where R12 (archetype) and R13 (recogniser wiring) become steps of one pipeline rather than three
separate open items. **Status: OPEN. S2, S4, S5, S8 have no code at all.**

### Why this section exists

The aim — *an agent that scans a page as a literate human does, sees the text classes by visual cue,
bounds them, and reads each as its own kind of thing* — was present in this project only in fragments:
"archetype first" in §3.2a, "reading order" inside a list in three summary documents, "shapes from ink"
as a section title. **A project whose aim lives in fragments optimises the nearest fragment**, and this
one did: four hand-built geometric span rules and five pre-registered bars against a 19-entry gold on
one witness, while S2, S4, S5 and S8 had no code. §3.0 states the aim once; R14 is its work plan.

⚠️ **R14 does not start from zero, and pretending otherwise would discard real evidence.** The R2.2
line produced three things the agent needs and could not have assumed: **(a)** the proof that no gap
constant exists (R2.2o.1 — populations overlap 0.875 vs 1.525); **(b)** the B1-vs-B2 distinction with a
*measured* 26 px gutter on `jp2-S06` p74, which is why disjoint and interleaved apparatus must route to
different machinery rather than to one parameter; **(c)** the finding that **kraken destroys the
boundary upstream** by merging margin text into body line objects (ch3 p26, ch6 p36), which no
downstream boxer of any kind can undo. **(c) is a hard constraint on R14.1: the agent must see the
page, not kraken's lines.**

### Steps

| # | step | deliverable | acceptance |
|---|---|---|---|
| R14.0 | ✅ **DONE** 2026-08-25 — see the RESULT block below. **Register, run and score the layout probe that already exists** | `surya_layout_probe.py` — a learned layout model covering S3/S4, present in the repo and named in **none** of the five governing documents — run on a stratified leaf set, with its output scored or its refusal recorded | the probe is **either** scored against hand-checked leaves **or** explicitly refused with a reason. ⚠️ **An unattempted tool produces no signal**; and per §3.0's forbidden-list item 3 this is the same defect shape as §3.2b's slant — working code that no rule governs. **C1 — probe**, and it is the cheapest step here |
| R14.1 | **S1→S2: the archetype classifier, on the PAGE.** ⚠️ **REDIRECTED by R14.0**: Surya's detector already localises the regions and only lacks NAMES for them, so this is a **class-inventory fine-tune of an existing detector**, not a detector built from scratch | R12.1's census then R12.2's classifier, taking **the leaf image**, not kraken's lines | Gate 9.1 — per-archetype accuracy, **forbidden-class emission = 0**. ⚠️ **Input constraint from (c) above**: a classifier reading line objects inherits a boundary that was already destroyed. **C3 — model** |
| R14.2 | **S3→S4: regions with confidence, and the right to abstain** | typed polygons with a confidence per region and an explicit abstention path; **`layout.py:type_lines`'s `fail-safe toward body` branch is retired** by this step, not before | Gate 9.3, 9.4, and **9.6 whose rate is pre-registered from R14.2's own characterisation, never asserted**. ⚠️ An abstention silently defaulted to any class is a hard failure. **C3 — model** |
| R14.3 | **S5: relations — reading order and ATTACHMENT** | which note attaches to which verse, which numeral governs which text, which catchword predicts which leaf | Gate 9.7, scored **separately from boxing**. ⚠️ This is the edition's scholarly payload: an unattached marginal transcript is not apparatus, and §8 assumes the link exists. **C3 — model** |
| R14.4 | **S6: recognition CONDITIONED by region class** | the region class selects model, lexicon and post-rules; **R13.1's wiring is the first instance of this**, not a separate errand | recognition reported **per region class**, never as one page figure. ⚠️ Grounded, not assumed: R2.2d measured that a row is not homogeneous in fount, and the `genesis-24` 49-point content/surface spread is what pooling costs. **C3 — assembly** |
| R14.5 | **S8: the re-examination loop** | a failed §6–§8 check re-opens S2–S5 for that leaf; §3.2 item 3's residue signal, currently spent only as training data, is read **at run time** as the trigger | Gate 9.8 — repairs **and** regressions published separately, **never netted**. ⚠️ Permitted terminal states are *repaired* or *abstained with a cause*; **never** *accepted below threshold*. **C4 — open** |
| R14.6 | **The label generator — what makes R14.1–R14.4 affordable** | distant supervision per §3.2 items 2, 3, 7: MainText from archaic-reference alignment, **Argument** from the **1,334** transcribed apparatus blocks (⚠️ **CORRECTED 2026-08-25 by R14.6a — this row said *Marginalia*, and all 1,334 blocks are in fact `kind='argument'`; MARGINALIA HAS NO SOURCE, see R14.6b**), RunningHead/Catchword/Signature from self-verifying tests, VerseNumber from numeral-matches-adjacent-verse | training labels generated at corpus scale **without** a hand-labelling campaign, with §3.2 item 8's quota for books that generate none. ⚠️ **GOLD-LAYOUT is the SCORER, not the trainer** — conflating them is what makes this programme look like it needs 125 hand-labelled pages before it can start. **C3 — assembly** |

### R14.0 RESULT — ✅ DONE 2026-08-25. The first layout score ever computed on this corpus

**`witness/score_surya_layout.py`**, Surya `FastLayoutPredictor` 0.21.1 against the 121-entry
GOLD-HEADBAND over leaves 400–419, addressed by **page fraction** (R2.2c), labels mapped by **two
declared maps** so no map could be chosen after seeing the numbers. **121 bound, 0 orphans.**

| gold class | recall | bound-box size, median share of PAGE area |
|---|---|---|
| RunningHead | **20/20 = 1.0000** | 0.0035 |
| MainText | **80/80 = 1.0000** | **0.5555** ⚠️ |
| MarginNote | **0/19 = 0.0000** | 0.0039 |
| ChapterHead | 0/2 = 0.0000 | 0.0060 |
| **overall** | **100/121 = 0.8264** | |

Surya emitted `Text` 79 · `PageHeader` 61 · `SectionHeader` 11 · `PageFooter` 9 — and **zero
`Footnote`**, so MAP_CHARITABLE was *empirically identical* to MAP_STRICT and the MN ceiling is not a
mapping artefact. Confusion: **MN → PageHeader 15, MN → Text 4**.

🔴 **THE FINDING IS A LABELLING FAILURE ON TOP OF A WORKING DETECTOR, WHICH IS FAR BETTER NEWS THAN
`MN 0.0000` LOOKS.** The MarginNote entries bind to **tight** boxes — median **0.0039** of page area,
not to the half-page `Text` block — so Surya **localises the notes as distinct objects**. What it lacks
is a *name* for them: its vocabulary is modern-document (Caption · Footnote · PageHeader · PageFooter ·
SectionHeader · Text · Table · Code · Form · ChemicalBlock · Bibliography …) and contains **no
marginalia / side-note class**. ⇒ **The repair is a CLASS-INVENTORY fine-tune — keep the detector, teach
it this book's classes — not a detector trained from scratch.** That is materially cheaper than R14.1
assumed, and it is exactly what §3.2a's REQUIRES/FORBIDS contract already specifies.

⚠️ **THE MainText 1.0000 IS NOT A WIN, AND MUST NEVER BE QUOTED AS ONE.** Its bound boxes cover a
median **0.5555 of the page**. A half-page block containing every body entry scores 1.0000 by
**containment**. Gate **10b**'s boundary error (≤8 px median, ≤25 px p95) is the check that separates
containment from boundary quality, and this run does **not** measure it. ⚠️ **This was caught by the
Senior Architect pass on the scorer's own first version, which bound on any non-zero overlap** — the
defect R2.1i had already fixed once in `score_head_regions`. `MIN_BIND_FRAC = 0.50` of the gold entry's
own area was added, and the containment check was added to make the trap visible rather than arguable.

⚠️ **COVERAGE LIMIT.** GOLD-HEADBAND labels the **top 3 rows**, so every MN entry scored here is a
**head-band** note. That Surya localises notes running down the **outer margin beside the measure** is
**not shown** by this run — the same coverage limit R2.2o.1 hit, and R2.2o.1b would lift for both.

⚠️ **THIS DISCHARGES NO GATE.** Rows 10a/10b are reserved for GOLD-LAYOUT (≥125 pages, per-archetype
quota, recogniser frozen). This is 121 entries over 20 leaves of one witness, and it answers only the
rung-0 question *is this model worth building on*. Bars were pre-registered **in the file before the
run**: MN recall ≥ 0.50 (**FAIL**, 0.0000) and overall ≥ 0.70 (**PASS**, 0.8264).

📌 **AND THE COMPARISON THAT MATTERS.** Against the incumbent geometric `region_head` on the same gold:
**Surya wins MainText 80/80 vs 67/80 (with the containment caveat above), ties RunningHead 20/20, and
loses MarginNote 0/19 vs 17/19.** Neither is adequate alone. The hand-built geometric component is
currently **the only thing in the project that can name a marginal note**, which is precisely the
"initialisation and plausibility clamp" role §3.2 item 5 assigns it — now evidenced rather than asserted.

### R14.1 · R14.2 · R14.7 RESULT — ✅ **THE AGENT IS BUILT, DRAWN, AND PASSES ITS RUNG-0 BARS** (2026-08-26)

🔴 **THIS SECTION EXISTS BECAUSE SIR STOPPED THE AUDITING.** *"You know the aims, so why get bogged
down in this way? … Build the visual agent that can AUTOMATE the text class recognition. Agent uses a
visual model, takes the page, sees the text blocks, consults archetypes, decides what each text block
probably is, does some quick reading to confirm, revises if needed, and generates the image chunks for
OCR. Is that really that hard? No, it's really not."* **It was not.** The four span rules, five
pre-registered bars and one overlap measurement that preceded this were all attempts to find a
CONSTANT. The agent needed a **frame**.

**`witness/visual_agent.py`** — S1 see → S2 archetype → S3/S4 name-and-bound with confidence and
abstention. **`witness/agent_see.py`** (R14.7) draws the agent's own decisions onto the leaf.

| | same gold · same window · same binding | overall | MN | RH | MT |
|---|---|---|---|---|---|
| | Surya off the shelf (R14.0) | 100/121 | **0/19** | 20/20 | 80/80 |
| | geometric `region_head` (R2.1g) | — | 17/19 | 20/20 | 67/80 |
| ⇒ | **THE AGENT** | **110/121 = 0.9091** | **13/19** | **20/20** | 77/80 |

**Rung-0 bars, written into the file before the first run — all three PASS.** MN recall ≥ 0.50 →
**0.6842**. Overall ≥ **0.8264**, *which is Surya's own score on this gold*, so buying marginalia with
body text is a **failure** by construction — the exact trade R2.2's four refuted rules each made at
~1 MN per 11–12 MT → **0.9091**. Forbidden-class emissions = 0. ⚠️ **The bars are applied to the WORSE
of the two declared addressing rules**, never the better.

**THE ONE IDEA THAT MADE IT WORK — a FRAME, not a threshold.** R2.2o.1 proved no gap constant exists
because it was asking *how far is this from the body*. A marginal note is not **far from** the body,
it is **BESIDE** it — and besideness is a fact about **the measure**, which is derived per leaf from
that leaf's own boxes. That single reframing takes MarginNote from 0/19 to 13/19 with **no fitted
constant deciding anything**, satisfying §3.0's rule that a constant may initialise or clamp and may
never decide.

🔴 **AND THE PICTURE FOUND THREE BUGS THAT THE NUMBERS DID NOT — THIS IS R14.7's WHOLE JUSTIFICATION.**
The first run scored **91/121 with RH 9/20**, and no cell of that table said why.
1. **The measure was being dragged into the margin.** `frame()` took the median edge of every large
   box; on an apparatus leaf Surya emits the whole **marginal column** as one large box — it is tall,
   so it clears any area prior. Every besideness test downstream was then asked against a frame that
   already contained the margin. ⇒ anchor on the single largest box, widen only by boxes sharing
   ≥50% of its column.
2. **Size was being read as the body cue.** `area >= SMALL_AREA → MainText` made that same marginal
   column *body text*, so every head-band note inside it scored MT. ⇒ **besideness outranks size**.
3. **A cue was turning on a last pixel.** `y1 <= head_y` asked *does the running head entirely clear
   the body block*, and on leaf 400 it failed by **0.0015 of a page**. Eleven of twenty running heads
   died on that margin. ⇒ judge on the box's **mass**, not its last pixel. ⚠️ **A cue that turns on a
   last pixel is a threshold wearing a cue's clothes.**

Then one more, from the confusion matrix: **the head band holds two different things.** This edition
sets head-band notes at the *same height* as the running head, out at the fore-edge, so height cannot
separate them and besideness does not fire because such a note *straddles* the measure's edge. The cue
that works is the one a reader uses: **a running head is CENTRED on the measure; a head-band note is
pushed to a side.** MN 4/19 → 13/19.

✅ **ABSTENTION IS REAL, AND ITS RESIDUE IS DIAGNOSTIC.** All **6** remaining MN misses are
abstentions **carrying their cause**, not silent errors — and **3 of the 6 are archetype
contradictions** (`cue says MN, but archetype A forbids it`), which points the next repair at **the
archetype classifier**, not at the naming cues. §3.0 S4's clause is doing exactly the work it was
written for, and `layout.py:type_lines`'s `fail-safe toward body` branch now has a replacement that
says *why* instead of emitting a leaf as entirely scripture.

⚠️ **THIS DISCHARGES NO GATE, AND THE LIMITS ARE THE SAME THREE R14.0 CARRIED.** 121 entries, 20
leaves, **one witness**, **head band only** — so every MN scored here is a head-band note, and that the
agent names notes running down the **outer margin beside the measure** is **not shown**. MainText
remains **containment** (the body block is one box); Gate 10b's boundary error is what separates
containment from boundary quality and is not measured. Rows 10a/10b stay reserved for GOLD-LAYOUT
(**R16.1**).

### R14.9 RESULT — ✅ **DONE 2026-08-27. Two structural repairs, no threshold touched: 110/121 → 115/121**

| | overall | MN | RH | MT | CH |
|---|---|---|---|---|---|
| before R14.9 | 110/121 = 0.9091 | 13/19 | 20/20 | 77/80 | **0/2** |
| **after** | **115/121 = 0.9504** | **16/19** | 20/20 | 77/80 | **2/2** |

**1. THE ARCHETYPE CLASSIFIER HAD REIMPLEMENTED A SUBSET OF THE NAMING CUES.** It detected apparatus
with the **besideness** cue alone, while `name_regions` has **two** cues that can produce a
MarginNote — besideness, and head-band-off-centre. So on leaves whose notes are *all* head-band notes
(**402 · 413 · 415**, outside fractions **0.37 / 0.48 / 0.44**, all under the besideness boundary) it
saw no apparatus, typed the page `A`, and `A` **FORBIDS** MarginNote — forcing the namer to abstain on
a note it had correctly identified. ⚠️ **Two code paths answering one question is this project's
signature defect, and here it had got as far as making the agent contradict itself.** Both steps now
call one `_cue()`; the archetype is derived from an **unconstrained** pass over it and still fixes
before any region is committed, so §3.2a's ordering is kept while the blindness is gone.

**2. THE AGENT HAD NAMES FOR FOUR CLASSES ON A PAGE THAT PRINTS AT LEAST NINE.** Leaf 409 sets the
gathering signature `Z z` at the foot, centred; with no foot band the centred-heading cue fired, the
agent invented a **chapter opening**, and that propagated into the **archetype** (BC instead of B1).
⇒ the frame now derives a **foot band** as well as a head band, and `SG` (signature) and `CW`
(catchword) are named classes. ⚠️ **The foot band has the head band's nesting problem one end down** —
the body `Text` box runs to 0.906 and the signature sits at 0.885–0.904, *inside* it — so position
alone never fires; the detector's own `PageFooter` class is the second cue, clamped by position.

🔴 **AND THE HEAD-BAND GOLD COULD NOT SEE REPAIR 2 AT ALL. The score was UNCHANGED by it** (115/121
before and after), while three leaves stopped falsely claiming a chapter opening. **It was found by
DRAWING the leaf (R14.7), not by reading a number.** A repair invisible to the only scorer in play is
exactly the repair that never gets made.

⚠️ **AND THE HONEST LIMIT, WHICH THE SCORE HIDES.** Archetype **A never fires** on this window, so the
FORBIDS contract does **not currently bind** and the zero forbidden-emission count is **trivially
true**. **The archetype call itself has no gold and is unmeasured** — Gate 10a needs GOLD-LAYOUT
(**R16.1**). R14.9 removed a *demonstrated* archetype error; it did not demonstrate archetype accuracy.

### R14.8 RESULT — ✅ **DONE 2026-08-27. Besideness GENERALISES, and every MN figure ever quoted was its WORST case**

**`witness/build_foreedge_gold.py` + `witness/score_foreedge.py`.** GOLD-HEADBAND labels the **top
three rows**, so Surya's 0/19, `region_head`'s 17/19 and the agent's 16/19 are *all* head-band notes.
**GOLD-FOREEDGE** is the first gold below that band: **42 boxes over 5 declared leaves**, the
population defined by **geometry alone** (every detector box whose mass sits below the head band), so
it cannot inherit the agent's blind spots, and adjudicated from **numbered, unlabelled** renders.

| | MarginNote recall |
|---|---|
| head band (GOLD-HEADBAND) — the cue's **straddling** case | 16/19 = 0.8421 |
| **fore-edge (GOLD-FOREEDGE)** — the cue's **clearing** case | **18/18 = 1.0000** |

✅ **THE PRE-REGISTERED PREDICTION HELD.** It was written before the run: *besideness should do BETTER
on fore-edge notes, because such a note CLEARS the measure where a head-band note STRADDLES its edge.*
It does. MainText **9/9**, heading **6/6**. **The head-band figure was the cue's worst case, not its
best** — which inverts how every marginalia number on this corpus should be read.

🔴 **AND EXIT 1 IS A CLASS-INVENTORY FINDING, NOT A CUE FAILURE.** All **7** residual errors are
classes the page prints and the agent **has no name for**: **Argument ×4** (the italic prose summary
under a chapter heading — archetype C's class, misfiled as `CH`), **PageNumber ×2**, **Annotation ×1**
(leaf 417 is an archetype **F mixed leaf**: body, then an ANNOTATIONS section, then a new chapter).
Plus one `SG → CW` on the foot band's centred/outer boundary. ⇒ **R14.10**, below.

🔴 **AND A DISCIPLINE POINT, RECORDED BECAUSE THE TEMPTATION WAS IMMEDIATE.** Adding an `AR` cue now
would fix 4 of the 8 remaining errors — **and it would be fitted against the 42 boxes just
adjudicated.** `build_foreedge_gold.py` states in terms that it is *the SCORER, never the trainer*.
**R14.10's cues must be validated on leaves outside this gold's five**, or the next score means
nothing. ⚠️ Coverage stated: 5 of 20 leaves, one witness, **one operator, NOT fully blind** (the
agent's aggregate calls had been seen before adjudication). Discharges **no** gate; this gold may
**never** be promoted to GOLD-LAYOUT.

---

## R14.10 — The class inventory is smaller than the page (NEW, 2026-08-27, measured by R14.8)

**Complexity: C2 — assembly.** **The pre-registered decision rule**: *a new class is ADOPTED only when
its cue is scored on leaves OUTSIDE GOLD-FOREEDGE's five; a cue fitted against the gold that revealed
the gap is not evidence. A class must also be ABSTAINABLE — adding a name must not add a confident
wrong answer.*

🔴 **A CLASS WITH NO NAME IS NOT A SKIPPED BOX. IT IS MISFILED into the nearest name the agent does
have** — measured twice now, at both ends of the leaf: a gathering signature became a *chapter
heading* (R14.9, leaf 409) and an italic Argument becomes one too (R14.8, ×4). **The error is
confident, not silent**, which is the worst combination.

| # | step | deliverable | acceptance |
|---|---|---|---|
| R14.10a | ✅ **DONE 2026-08-27 — Argument** (`AR`). ⚠️ **The defect was 10 of 10, not the 4 this table was filed with** | a block set to the measure whose type **deslants as italic** — a FOUNT cue, wired to §3.2b's existing instrument (`CR.row_slant` / `CR.region_segments` / `CR.page_slant_mode`), which R2.2d built and **no rule read**. ⚠️ **The "directly below a chapter heading" formulation was REJECTED on measurement, not taste** — see the result below | ✅ all five pre-registered criteria hold: **A1 6/6** on the six leaves DISJOINT from GOLD-FOREEDGE, **A2 0** false positives window-wide, **A3** every GOLD-HEADBAND number EXACTLY held, **A4** the cue proven abstainable by a withheld-record negative, **A5** the out-of-sample prediction held at **4/4**. `witness/score_argument_agent.py` · `witness/build_fount_record.py`. **C2 — assembly** |
| R14.10b | 🟠 **ADOPTED, STEP STILL OPEN 2026-08-27f — PageNumber** (`PN`), and it is the **first class in this agent decided by a READ** | a small head-band box at an extreme of the measure **whose confirming read returns digits**. ⚠️ **The row's POSITIONAL formulation is refuted** — the box CENTRE overlaps on both sides (page numbers 0.000-0.043 / 0.812-0.972 of the measure, notes 0.010-0.110 / 0.857-1.072). 🔴 **But this step over-generalised that to ALL of position, and 2026-08-27g refutes the generalisation: WIDTH separates cleanly** — 0.0442-0.0546 against 0.0757-0.3028, an empty band **2.0× the PN spread** — and **geometry alone scores 20/20 with 0 FP where the read scores 14/20, so the read DEGRADES the result here** | 🔴 **The defect was 20 of 20 and ENTIRELY SILENT** — every page number misfiled, 15 as `MN` and 4 as `MT`, and **no gold entry binds to any of them**, so `MN` recall could not fall when the agent invented notes and `MT` is containment so those scored correct. **`MN` precision had never been measured.** B1 14/20 (floor 12) · B2 0 FP · B3 GOLD-HEADBAND EXACT · B4 withheld-record negative 0/20 · **B5 FAILS 1/20 and is NOT relaxed** (leaf 403 reads `37T`). Out-of-sample: **GOLD-FOREEDGE `PN` 2/2, 38/42 → 40/42**. `witness/score_pagenumber_agent.py` · `witness/build_reading_record.py`. **C3 — instrument design** |
| R14.10c | 🔴 **Annotation** (`AN`) — **BLOCKED 2026-08-27b, on THREE measured counts, and the block is the finding** | an annotation block under an `ANNOTATIONS` section head. ⚠️ **Two candidate visual cues were built and REFUTED** (type height, line pitch) and the only reliable anchor needs the head to be **READ** — see the result below | ⚠️ **F is currently DATA LOSS** (R12: *"dropped WHOLE"*), and the apparatus is **roughly half the book**; an agent that cannot name it cannot read half the edition. **BLOCKED ON R13.1** (the confirming read), **on population** (one exemplar, and it is on a GOLD-FOREEDGE leaf) and **on its label source** (`PARTIAL` — the corpus does not reach this volume). **C3 — model** |

⚠️ **ORDERING**: R14.10a first — it has a gold already. R14.10c is the largest and is the one that
turns the agent from a scripture-page reader into a reader of this edition. **R14.10b waits on R13.1.**

### R14.11 · R14.12 · R14.13 — the three steps Sir's 2026-08-27 review raised

**Pre-registered decision rule for this group** (§0.5): each step below states its acceptance
BEFORE implementation, and each is scored by a command enrolled in the verification standard. None
may be closed by a document edit. **Complexity per sub-step: declared in each row.**

| step | what it is | the rule | acceptance | class |
|---|---|---|---|---|
| R14.11 | 🔴 **NO FIXED MEASURE MAY DECIDE** — `audit_fixed_measures.py` sweeps every constant in the agent and reports the band over which the full label vector is unchanged. **First run: 5 of 12 DECIDE** (`OUTSIDE_FRAC` 0.04× · `THIN_MARGIN` 0.06× · `PN_MAX_AREA` 0.25× · `FOOT_CATCHWORD_REL` 0.03× · `CENTRED_LO/HI` **0.00×**). 🟠 **2026-08-28: 3 of 12** — `CENTRED_LO/HI` RETIRED and `THIN_MARGIN` released to a 2.25× guard by that retirement alone | each DECIDING constant is either **derived from the leaf** or **retired**. ⚠️ Derivation means computed from *this leaf's own boxes or ink*, not re-fitted on the window — re-fitting reproduces the defect with a larger sample | `audit_fixed_measures.py` reports **0 deciding**, and GOLD-HEADBAND, GOLD-FOREEDGE and GOLD-PAGENUMBER each hold or improve. ⚠️ A constant may NOT be retired by widening its sweep range | **C3 — instrument design** |
| R14.12 | 🔴 **THE LAMINATION** (Masterplan §3.0, added 2026-08-27) — S4 emits an ordered stack of typed regions where a region OWNS the ink inside it that no higher region claims, and **no region contains ink lying inside another at the same or higher z-order**. Measured motivation: **99 overlapping box pairs over 158 boxes on 20 leaves, every leaf affected** | boundaries are adjusted until the ink invariant holds; where it cannot, **abstain with a cause**. ⚠️ The invariant is over **INK, never rectangles** — two boxes may overlap in white space, because a page is not tiled by its type | (1) **ink-overlap violations → 0** on all 20 leaves, or every survivor carries a cause; (2) GOLD-HEADBAND **exactly unchanged**; (3) the **two rival binding rules COLLAPSE TO ONE** — under a lamination `BIND_OVERLAP` and `BIND_TIGHTEST` must agree on every entry, and that agreement is the proof the concept was the missing one; (4) a withheld negative: with lamination off, the violations return | **C4 — architecture** |
| R14.13 | **FULL-LEAF GOLD REVIEW** — every leaf of the scoring window rendered with all boxes, classes, the frame and the archetype, for leaf-by-leaf inspection before further cue work. Built 2026-08-27; **the review itself is not yet done** | garbage-in/garbage-out check: confirm no cue is being built on a mis-detected or mis-framed input | a recorded per-leaf verdict for all 20 leaves, each either CLEAN or carrying a filed defect id. ⚠️ It may NOT be closed by "the plates were produced" — the plates are the instrument, the verdicts are the step | **C2 — assembly** |

| R14.14 | 🔴 **THE AGENT HAS NO ANGLE AT ALL** — every box is axis-aligned, the head and foot lines are HORIZONTAL and the measure edges VERTICAL, while the leaves are genuinely tilted. Measured 2026-08-27: real baseline tilt runs **-2.39° to +2.75°**, varies per leaf (400 is -0.34°, 409 is +1.64°), and at +1.6° the drop across a page is **about one full line-height**. Consequence, counted: **the horizontal head line CUTS THROUGH 41 BOXES** and the foot line through 7 | the frame is a **rotated** frame: estimate this leaf's own baseline angle from its own row geometry, and express the head line, foot line and measure in that rotated space. ⚠️ `fount_*.json`'s `slant_mode` is **NOT this quantity** — it is GLYPH slant (italic vs roman), quantised to whole degrees, and reads 0.00 on all 20 leaves; using it as a skew estimate would be a dead metric impersonating a measurement | 🔴 **ACCEPTANCE REWRITTEN 2026-08-28 — THE STEP'S OWN PREMISE WAS REFUTED BY BUILDING IT.** Clause (1) was *straddles 41 → 0*; the rotated frame moved the count **41 → 50**, and **corr(|skew|, straddles) = +0.051** over 20 leaves, with nearly-flat leaves cut 2.50 times on average against tilted leaves 2.44. **The angle does not cause the cutting** — the head line is the extreme edge of the BODY BLOCK and furniture sits at overlapping heights, so any scalar boundary is straddled whatever its angle. **The 41 boxes belong to R14.12.** Clause (1) is RETIRED as unreachable here, never reinterpreted. Clause (3) was CIRCULAR — the estimator *is* the row tilt. Live acceptance: **S1** angle measured on 20/20 and varying (-0.901°…+1.636°) · **S2** GOLD-HEADBAND **exactly** unchanged (115/121, MN 16/19) · **S3** the refutation, reported as one · **S4** withheld-record negative 0/20 · **S5 OPEN** — the defect the tilt *does* cause is BOX INFLATION (an axis-aligned box round a tilted line is taller by width·tan θ: **17% of a median box height on leaf 409**), which is a BOUNDARY error under Gate 9.3 that **no gold here can see**, because every gold scores labels | **C3 — instrument design** |
| R14.15 | 🔴 **THE DETECTION FLOOR — classes smaller than anything the agent has ever seen.** Sir, 2026-08-27: *what about verse numbers? very small brief marginal notes? a single-character signature?* The agent names only boxes Surya emits, so a class Surya does not localise is **invisible to every instrument here** — not misfiled, absent. ⚠️ And the claim "the page number is the smallest box" is **REFUTED**: on leaves 401 and 409 the catchword (0.00072) and signature (0.00073) are smaller than the page number | census the smallest objects the page actually prints against what the detector emits. Verse numbers are the critical case: this edition sets them **inline within the body block**, so they are not separate boxes at all and no box-level class can reach them | a measured inventory: for each candidate class, how many the page prints, how many the detector localises, how many the agent names. ⚠️ **A zero in column two is a DETECTOR gap and must be filed as such**, never reported as a naming result | **C3 — instrument design** |
| R14.16 | 🔴 **LECTOR IS A DECISION PROCEDURE, NOT A MODEL, AND THAT IS THE DESIGN GAP.** It performs no inference, consults no prompt, and does not read text. §3.0 asks for an agent that decides *"by visual cue"* conditioned on archetype; what exists is a hand-written ordered cascade over a detector's boxes, five of whose constants DECIDE (R14.11) | evaluate replacing the cascade with a **learned region classifier** over features the cascade already computes — position in the rotated frame, size, aspect, fount slant, detector class — **plus text features from the confirming read**, conditioned on archetype. ⚠️ Sir's point: the TEXT is a strong tell for the class and is currently consulted for exactly one class | a like-for-like comparison against the cascade on GOLD-HEADBAND and GOLD-FOREEDGE, with the cascade as the **bar**, not the baseline. ⚠️ It may NOT be adopted on aggregate accuracy alone — per-class, and the abstention behaviour must be preserved | **C4 — architecture** |
| R14.17 | **THE REVIEW TOOLKIT** — the plate book made interactive: adjust boxes, margins and the frame, reassign classes, add class types, and export the result as a gold candidate | an inspection and correction surface for R14.13, so a human verdict produces a *corrected artefact* rather than a note | every edit round-trips to a gold file the scorers already read; no edit path may write a label the agent's declared inventory does not contain | **C2 — assembly** |
| R14.18 | **GOLD EXPANSION — 188 leaves requested by Sir 2026-08-27**, verified present on disk: 60 from OT1 vol1 (S03 / witness `P`), 73 from OT2 vol2 (S03 / `P`), 55 from NT (S09 / `B`) | extend the boxing gold beyond the 20-leaf Numbers window. ⚠️ **THE CURRENT GOLD IS WITNESS `OT1-1609-B` (S09) AND SIR'S OT1 LEAVES ARE FROM `OT1-1609-P` (S03)** — different scans with different leaf counts (1160 vs 1146), so **there is no fixed offset between their leaf ordinals** and a mapping needs the PRINTED PAGE NUMBER, which is exactly what R14.10b's `PN` class now supplies | a decision recorded on whether the gold is single-witness or multi-witness, THEN the leaves cut and adjudicated. ⚠️ Mixing witnesses in one gold silently changes what every score means; it may be right, but it may not be done by accident | **C2 — assembly** |

🔴 **R14.11 IS A PREREQUISITE OF R14.12, AND THE ORDER IS NOT ARBITRARY.** A lamination adjusts
boundaries until an invariant holds; if the cues that decide *what a region is* still turn on
undeclared constants, the lamination will faithfully enforce ownership over **wrongly typed**
regions. Fixing the geometry under a bad naming layer hides the naming defect inside a tidier
structure. ⚠️ Same shape as R2.2f/R2.2g, where the prerequisite ran the wrong way round and was
found only by measuring.

⚠️ **AND R14.13 SHOULD PRECEDE BOTH.** The plates already surfaced one defect that no number
reported: on leaf 417 the annotation block is boxed as `MT` (MainText), which is containment and
therefore scores as correct — **R14.10c's data loss, visible at a glance and invisible to every
score**. A review that finds one such defect before the derivation work begins is cheaper than
deriving constants against inputs nobody has looked at.

📌 **WHY `CENTRED_LO/HI` AT ZERO SLACK IS THE SHARPEST OF THE FIVE.** It is the band that separates
a RUNNING HEAD (centred on the measure) from a head-band NOTE (pushed to a side) — the cue that
recovered 14 of 19 marginal notes and is quoted throughout this document. **Its shipped value has no
slack at all**: move it by one sweep step in either direction and the label vector changes. So the
single most load-bearing cue in the head band is sitting exactly on a cliff edge, and nothing said
so until it was swept. ⚠️ **The derivation is available and was never taken**: a running head's
centredness should be judged against *this leaf's own* distribution of head-band box centres, not
against a fixed fraction of the measure.

🟢 **PRE-REGISTERED DERIVATION FOR `CENTRED_LO/HI`, WRITTEN 2026-08-28 BEFORE THE AGENT WAS RUN
AGAINST ANY GOLD UNDER IT.** The Roadmap's own suggestion above — judge against *this leaf's own
distribution of head-band centres* — is **NOT the derivation taken**, and the reason is worth
recording: a leaf carries only two to five head-band boxes, so a distribution over them is a
statistic with a sample size of three, and on a leaf whose head band holds nothing but notes it
would centre the band on the notes. **A distribution that small is a fitted number wearing a
derivation's clothes.**

The derivation taken instead is **parameter-free, and it retires the constant rather than
re-deriving it**. Define, for a head-band box, the offset of its centre from the measure's centre
**in units of the box's own width**:

`off = |(b.cx - measure_centre)| / box_width`

Then `off <= 0.5` is not a threshold at all — it is the exact statement **"the measure's centre-line
falls inside this box"**, which is what a compositor means by setting a running head *on the
measure*. It contains no fitted quantity: the measure comes from this leaf's body block, the width
and centre come from the box.

⚠️ **The supporting measurement was taken before this was written, and it is the basis of the
derivation, not a tuning of it.** Over the 20-leaf window, 46 head-band boxes: running heads run
`off` **0.004–0.419**, chapter headings **0.008–0.165**, marginal notes **1.023–6.576**, page
numbers **5.738–7.740**. The empty band between the centred classes and the notes is **0.604 wide,
which is 1.44× the entire running-head spread** — where the shipped `CENTRED_LO/HI` had **zero**.

📌 **PREDICTION, RECORDED BEFORE SCORING** — the two rules induce the same partition on every box in
the window, so **GOLD-HEADBAND is predicted EXACTLY unchanged at 115/121, MN 16/19, RH 20/20,
MT 77/80, CH 2/2**, and the `audit_fixed_measures.py` deciding count is predicted to fall by one.
⚠️ **A prediction of "no change" is the correct prediction here and it is a WEAK result by
construction** — it is evidence the derivation is faithful to the shipped behaviour, never evidence
that either rule is right. What earns the change is that one of them contains a number that decides
and the other contains no number at all.

⚠️ **THE OPEN SUB-PROBLEM IS THE ABSTENTION, NOT THE CUE.** The shipped code abstains when the box
lies within `THIN_MARGIN` of the centred boundary, and `THIN_MARGIN` is itself one of the five
deciding constants. A geometric predicate has no tolerance band to abstain over, so retiring
`CENTRED_LO/HI` naively **deletes an abstention path rather than deriving it** — which would trade a
measured defect for a silent one. This is filed as part of this step and must be answered by
measurement, not by dropping the branch.

### R14.11 RESULT (PART 1) — 🟠 2026-08-28. `CENTRED_LO/HI` retired; **5 of 12 → 3 of 12**; step OPEN

**Acceptance is ZERO deciding constants. Three still decide, so this step is NOT closed.**

| | before | after |
|---|---|---|
| deciding fixed measures | 5 of 12 | **3 of 12** |
| `CENTRED_LO/HI` | 0.00× — **DECIDING** | **retired; the cue has no constant** |
| `THIN_MARGIN` | 0.06× — **DECIDING** | **2.25× — GUARD, and it was never edited** |
| `CENTRED_ABSTAIN` (new) | — | 9.12× — guard, ⚠️ **unexercised here** |
| GOLD-HEADBAND | 115/121 · MN 16/19 | **117/121 · MN 18/19** · RH 20/20 · MT 77/80 · CH 2/2 |
| head-band abstentions | 3/121 | **1/121** |
| GOLD-FOREEDGE | 40/42 · MN 18/18 | **40/42 · MN 18/18** — unchanged |
| GOLD-PAGENUMBER | B1 14/20 · B5 1/20 | **unchanged** |

🔴 **THE PRE-REGISTERED PREDICTION WAS REFUTED AND THE REFUTATION IS THE RESULT.** The derivation
was written down predicting GOLD-HEADBAND **exactly unchanged**, on the reasoning that the two rules
induce the same partition on every box in the window. **They do not.** The agent improved by two,
and an improvement against a written prediction of no-change is a **failed prediction**, not a gain
to bank. What the two boxes were is the whole finding: leaves 400 and 411 were **abstentions** under
the retired band, and they sit **1.476** and **0.877** box-widths clear of the centre-line — boxes
the measure's centre-line plainly misses. The old rule was declining to call boxes that were never
ambiguous. ⚠️ **Leaf 411 abstained by 0.079 against a `THIN_MARGIN` of 0.080 — one thousandth of the
measure.** That is the last-pixel failure mode `visual_agent.py` already records twice.

🔑 **RETIRING ONE CONSTANT RELEASED A SECOND THAT WAS NEVER TOUCHED.** `THIN_MARGIN` went from
DECIDING to a 2.25× guard because its only remaining deciding use *was* the head-band centred
boundary. Nothing in the agent, and nothing in this document, said those two numbers were coupled.
**Only re-running the sweep showed it** — which is the argument for the sweep being a standing
instrument rather than a one-off census.

🚫 **THE DERIVATION THIS DOCUMENT ITSELF PROPOSED WAS REJECTED, AND THE REASON GENERALISES.** The
suggestion above was to judge centredness against *this leaf's own distribution of head-band
centres*. A leaf carries two to five head-band boxes, so that distribution has a sample size of
about three, and on a leaf whose head band holds only notes it would centre the band **on the
notes**. **"Derived from the leaf" is not automatically safer than "fitted to the corpus"** — a
per-leaf statistic over three objects is a fitted number with a smaller sample. The test that
matters is whether the rule contains a *quantity to choose at all*, and the one adopted does not.

🔴 **FOUR STALE PINNED COPIES OF ONE NUMBER, ALL EXPOSED BY MOVING IT.** `115/121` was restated as a
literal in three scorers and `16/19` in a fourth, and improving the agent surfaced every one at
once. The instructive ranking is by **how loudly each failed**:
1. `score_skew_frame.S2_EXPECT` — **a FALSE FAIL.** S2 claimed to test *does the rotation move a
   label* and actually tested *does the vector equal a literal frozen on 2026-08-28*, so it blamed
   the rotation for R14.11's improvement. **Replaced with the honest instrument**: label the window
   twice in one run, rotation on and rotation withheld, and require the vectors identical — 160
   boxes, 0 moved. No frozen number, and **stricter**, since it compares every box rather than the
   121 the gold binds.
2. `score_foreedge.HEADBAND_MN = 16 / 19` — silently compared the fore-edge against a figure the
   head band no longer scored, while printing "(16/19)" beside it.
3. `score_pagenumber_agent.B3_EXPECT = "115/121"` — **only ever printed, never compared, so nothing
   could catch it.** A stale number that is only printed is worse than one that is tested.
4. `score_argument_agent.A3_BARS` — **correct as it stands and deliberately left alone.** It is a
   `>=` FLOOR, not an equality; 117 ≥ 115 and 18 ≥ 16 still pass. **Ratcheting a pre-registered bar
   to the new figure would change what that step tested.**
✅ Fix: `visual_agent.headband_score()` is now **the one place the head-band score is computed**, and
both scorers import it. ⚠️ Exactly the defect `score_foreedge.py`'s own docstring already records one
level up, where its restated copy of `CLASSES` scored `AR 4/4` while printing "NO NAME IN THE AGENT"
about those same four boxes. **A measured figure restated in a second file will drift, and it drifts
silently, because both copies keep printing.**

⚠️ **R14.8's BESIDENESS MARGIN NARROWED AND THE CLAIM IS THINNER FOR IT.** The pre-registered
comparison is fore-edge MarginNote recall against the head band's: it was 1.0000 against 0.8421 and
is now 1.0000 against **0.9474**. The prediction still holds, on **less** headroom.

➡️ **REMAINING FOR THIS STEP**: `OUTSIDE_FRAC` (0.04×), `FOOT_CATCHWORD_REL` (0.03×) and
`PN_MAX_AREA` (0.25×, sitting exactly **on** the definition's edge). ⚠️ `OUTSIDE_FRAC` is the
besideness boundary and therefore the agent's most-quoted cue; `FOOT_CATCHWORD_REL` is the single
position test R14.10d already records as wrong on leaf 411, so **that constant may be retired by
R14.10d rather than derived here**, and the two steps should be checked against each other before
either is worked.

### R14.10b RESULT — 🟠 2026-08-27. The class is adopted; the step stays OPEN on one box

**`witness/build_reading_record.py` + `witness/score_pagenumber_agent.py` + GOLD-PAGENUMBER.**
The agent now names the PAGE NUMBER, and it is the first class here that **a cue cannot decide and
only a reading can**.

🔴 **FINDING 1 — THE DEFECT WAS 20 OF 20, AND EVERY ONE OF THEM WAS FREE.** Measured at box grain
over leaves 400-419, *every* page number in the window was misfiled:

| the agent called it | how many | visible to a score? |
|---|---|---|
| `MN` — marginal note | 15 | 🔴 **NO** — no gold entry binds to the box |
| `MT` — main text | 4 | 🔴 **NO** — MainText is containment, so it scores as **correct** |
| `??` — abstained | 1 | reported |

⚠️ **AND THE CLASS IT WAS MISFILED INTO IS THE ONE THE EDITION IS BUILT AROUND.** `MN` recall is
this agent's headline bar, and **recall is gold-driven** — `visual_agent._bind` walks the gold and
binds each entry to a box, so a box no entry binds to is never scored at all. **The agent could
manufacture marginal notes at no cost, and did, at roughly three-quarters of a note per leaf.** No
instrument in this project measured `MN` **precision** until this class made the gap visible. This
is R14.10a's silent `MT` half one class over, and it is larger: there the silence hid six boxes of
ten, here it hid twenty of twenty.

🔴 **FINDING 2 — THE ROW'S POSITIONAL FORMULATION IS REFUTED — AND SO, ON 2026-08-27g, IS THE
JUSTIFICATION THIS STEP REPLACED IT WITH.** The row filed `PN` as *"a head-band box at the extreme
fore-edge, **beyond** where a note sits"*. That is dead: page numbers sit at **0.000-0.043** and
**0.812-0.972** of the measure, head-band notes at **0.010-0.110** and **0.857-1.072** — the box
CENTRE **overlaps on both sides**, and so does outsideness.

⚠️ **BUT THIS STEP THEN GENERALISED ONE STATISTIC INTO A CLAIM ABOUT ALL OF POSITION, AND THAT IS
WRONG.** Measured over all **65** head-band boxes in the window:

| statistic | page numbers | everything else | verdict |
|---|---|---|---|
| **width** | 0.0442-0.0546 | 0.0757-0.3028 | ✅ **SEPARATES** — empty band **2.0× the PN spread** |
| **area** | 0.0008-0.0012 | 0.0018-0.0095 | ✅ **SEPARATES** — 1.5× |
| **aspect** | 2.01-2.73 | 3.17-10.25 | ✅ **SEPARATES** |
| `rel_h` (centre) | 0.000-0.995 | -0.055-1.072 | 🔴 OVERLAP (36 inside) |
| `out_frac` | 0.000-0.497 | 0.000-1.000 | 🔴 OVERLAP (36 inside) |
| `height` | 0.0179-0.0232 | 0.0213-0.0314 | 🔴 OVERLAP (21 inside) |

🔴 **AND THE COUNTERFACTUAL IS DECISIVE: GEOMETRY ALONE SCORES 20/20 WITH 0 FALSE POSITIVES ON THIS
WINDOW, AND THE READ SCORES 14/20 PLUS 5 ABSTENTIONS AND 1 `MN`. The confirming read MEASURABLY
DEGRADES the result here.** B2's zero is therefore not evidence that the read discriminates — it was
never asked to reject a note. ⚠️ **The right reading of the page is that a page number is not
distinguished from a side-note by WHERE it sits, but by being a SHORT, SQUAT OBJECT** — two or three
sorts against a phrase. That is a fact about what the book sets, of exactly the kind R14.10a used for
the ARGUMENT, and this step walked past it because it had already decided the answer was a read.

➡️ **WHERE THE READ DOES EARN ITS PLACE, PRE-REGISTERED HERE FOR THE STEP THAT TESTS IT.** Width runs
~0.0165 of the page per digit, so a **four-digit** page number measures ~0.059-0.073 against a note
floor of 0.0757: **the empty band shrinks to almost nothing later in the volume.** So the defensible
design is the INVERSE of the one shipped — **width is the cue, and the read is the CHECK on a
geometric margin known to close** — and `PN` remains the concrete argument for R13.1, but as a
guard rather than as the decider. ⚠️ **Not rewired here.** The failing box is now known, so any
redesign must be pre-registered with its own out-of-sample check before it runs.

🔴 **FINDING 3 — THIS STEP PRODUCED A FALSE ABSENCE, AND A GOLD BUILT FOR ANOTHER STEP CAUGHT IT.**
The first run reported *"4 of 20 leaves carry no page-number box"* and filed it as a **detector**
gap. **There is no detector gap.** The candidate test was bounded by `mass_y <= head_y`, and on
leaves 401, 402, 409 and 417 the number's mass sits **~0.005 of a page below** the head line — which
the **body block** defines, not the furniture. All four were silently named `MT`. ⚠️ **A bounded
search returns "not found" in exactly the shape an exhaustive one does** — the third recorded
instance here, after `audit_label_sources.py` bounded by a directory and then by a field name, and
this time the bound was **a band**. It was caught by **GOLD-FOREEDGE**, which is not band-limited and
carries a `PN` entry on two of the four. ⚠️ **The repair is the one CUE 2b already made at the other
end of the page**: the detector's own `PageHeader` judgement as a second cue, position-clamped —
this file's standing rule that **no cue may turn on a last pixel**, violated once more.

✅ **THE FIVE PRE-REGISTERED CRITERIA — FOUR HOLD, ONE FAILS, AND THE STEP STAYS OPEN.**

| | criterion | result |
|---|---|---|
| **B1** | `PN` named on ≥ 12 leaves | ✅ **14/20** |
| **B2** | zero `PN` on a non-page-number | ✅ **0** |
| **B3** | GOLD-HEADBAND **exactly** unchanged | ✅ 115/121 · MN 16/19 · RH 20/20 · MT 77/80 · CH 2/2 · forbidden 0 |
| **B4** | withheld-record negative | ✅ **0/20** fire; all 20 name the absence |
| **B5** | spurious `MN` falls to 0 | 🔴 **1/20** — leaf 403 reads `37T` |

⚠️ **B5 IS NOT RELAXED, AND THAT IS THE POINT.** One misread sort turns a numeral into a "lettered
reading", which the pre-registered rule routes to the note logic. Widening the predicate to
*predominantly digits* would be **a rule edited after seeing which box it fails on**. The residual is
worth more as a measured limit of the confirming read than as a passing number, so **`PN` is adopted
and R14.10b remains OPEN**.

📌 **THE OUT-OF-SAMPLE CHECK NOBODY BUILT FOR THIS STEP.** GOLD-FOREEDGE — built for R14.8, never
touched here — carries two `PN` entries. The agent scores them **2/2** and that gold rises
**38/42 → 40/42**. Both sit on leaves this step had itself declared empty.

⚠️ **AND THE READ IS A MEASURED LIMIT, NOT A PASSING INSTRUMENT.** `dr_v3_armB` returns the *exact*
printed number on **4 of 16** of the original crops and **empty on 5**. Three redesigns were tried
and all three are **refuted**: more padding and 3× upscaling collapse it to **0/16**; a tighter crop,
predicted from kraken's line-height normalisation, is **worse** (6/16 at zero padding against 10/16
at the shipped padding); and matching the model's declared `bbox` segmentation type — kraken warns
about the mismatch on **every read this project makes** — gives **0/16**, which incidentally
confirms the existing baseline path is the right one and leaves R2.1b's numbers intact. ⚠️ **This
corroborates R2.1b's own per-class finding rather than contradicting it**: all five candidates
collapse on the direction line (`SG` 0.47-0.75, `CW` 0.53-0.80), and a page number is an object of
that scale. **R14.10b is the first consumer to hit that collapse in production**, which turns a
per-class caveat into a blocking limit and is an **ALERT on the approach**, never a licence to lower
the bar.

⚠️ **IT DISCHARGES NO GATE** — 20 leaves of ONE witness, one operator, and the operator adjudicating
the printed numbers is the same agent that wrote the cue. Rows 10a/10b stay reserved for GOLD-LAYOUT.

### R14.10a RESULT — ✅ DONE 2026-08-27. A size prior was choosing which wrong name the class got

**`witness/build_fount_record.py` + `witness/score_argument_agent.py`.** The agent now names the
ARGUMENT — the multi-line italic prose summary this edition sets between the chapter head and the
first verse — and it does so by reading the fount, which is what the book itself distinguishes.

🔴 **FINDING 1 — THE DEFECT WAS 10 OF 10, AND THIS TABLE WAS FILED SAYING 4.** Measured at box grain
over R2.2d's GOLD-ARGUMENT, every argument block in the window was misfiled, and **`SMALL_AREA` alone
decided which wrong name it got**:

| argument box area | agent called it | leaves | visible to a score? |
|---|---|---|---|
| ≥ 0.05 of the page | **`MT`** | 400 · 403 · 404 · 407 · 411 · 417 | 🔴 **NO — silent** |
| < 0.05 of the page | **`CH`** | 406 · 412 · 414 · 416 | yes — R14.8's ×4 |

**Not one cue was reading the class. A constant with no opinion about arguments was partitioning
them.** GOLD-FOREEDGE's five leaves happened to fall on the small-box side, which is the whole reason
R14.8 saw four. ⚠️ **And the `MT` half is the half that matters**, because **MainText is containment**:
an argument called MainText scores as *correct* against every gold this project holds, and would have
been handed to the recogniser as scripture and merged into the verse stream. Six of the ten sat in
that state, unmeasured, for the whole programme. This is the sharpest instance yet of *a class with
no name is not a skipped box* — half of it was not merely misfiled but **invisible**.

🔴 **FINDING 2 — THE ROADMAP'S OWN CUE FORMULATION WAS CIRCULAR, AND IS STRUCK.** This table filed
`AR` as *"a block … directly below a chapter heading"*, a relational cue. **On four of these ten
leaves the argument box IS the agent's `CH` call** — so the misfiled box would have become the anchor
used to find itself. ⚠️ It is also the objection `region_head` had **already recorded and refuted**
for the row-grain rule in 2026-08-18: *"between the ChapterHead and the first verse would be circular
— it presumes the boundary it must find, and is silent wherever the chapter head was missed."* The
reasoning existed in one file and the plan in another restated the refuted design. **`AR` is decided
on the FOUNT; the relation to the chapter head is an OUTPUT of the class, never an input to it** —
and the archetype now reads an `AR` box as *evidence that a chapter opens here*, so an argument the
agent can see rescues a chapter opening whose heading it missed.

✅ **THE FIVE PRE-REGISTERED CRITERIA, all written into `score_argument_agent.py` before its first run.**

| # | criterion | bar | measured |
|---|---|---|---|
| **A1** | recall on the leaves **DISJOINT** from GOLD-FOREEDGE (400 · 403 · 404 · 407 · 411 · 416) | all | **6/6** |
| **A2** | precision over the **whole 20-leaf window** | 0 FP | **0**, and **0 unadjudicated** |
| **A3** | no theft on GOLD-HEADBAND | nothing falls | **115/121 · MN 16/19 · RH 20/20 · MT 77/80 · CH 2/2 — EXACT** |
| **A4** | **abstainable, proven by a negative** — fount record withheld | 0 `AR` | **0 `AR`, 20/20 leaves carry a stated cause** |
| **A5** | the **pre-registered out-of-sample** prediction | 4/4, 34/42 → 38/42 | ✅ **4/4, 38/42 — exactly as written** |

**A3 is the one that makes this a gain rather than a trade.** R2.2's four refuted span rules each
bought ~1 MarginNote for 11–12 MainText; this bought a whole class for **nothing** — every
GOLD-HEADBAND figure is unchanged to the entry.

**A5 is what makes A1 mean anything.** GOLD-FOREEDGE carries 4 `AR` entries and **nothing was fitted
against it**; the direction was written down first. A1 passing while A5 failed would have meant a cue
fitted to six leaves, and the file says so and re-opens the step on that outcome.

📌 **THE GUARDS DECIDE NOTHING, AND THE SCORER PRINTS THE SLACK RATHER THAN ASSERTING IT** — because a
guard that decides is a threshold wearing a cue's clothes:

| guard | set to | observed worst case | in an empty band? |
|---|---|---|---|
| italic share | 0.50 (a majority) | **1.00** on all ten; nearest non-argument box **0.21** | yes, 0.21 → 1.00 |
| segments | 2 (multi-line by definition) | **3** | yes |
| measure span | 0.60 | **0.90** | yes |

⚠️ **AND THE BAND IS RE-MEASURED ON THE ADOPTION POPULATION ALONE, BECAUSE THE GUARDS WERE SET AFTER
LOOKING AT ALL TEN BLOCKS.** Four of those ten sit on GOLD-FOREEDGE's leaves, so *"they decide
nothing"* has to hold **without** them or it is a claim about the wrong population. On the disjoint
six, the nearest non-argument box clearing the other two guards reads **0.00** italic against the
argument blocks' **1.00** — a wholly empty band, wider than on all ten. The scorer prints this rather
than the file asserting it, so a future run that narrows the band becomes visible instead of silent.

⚠️ **BESIDENESS STILL OUTRANKS THE FOUNT, AND THAT IS LOAD-BEARING**: *this edition sets its
side-notes in italic too* (`region_head`, measured on leaf 405). Italic **alone** cannot name an
argument; italic **on the measure** can. Removing the `out < OUTSIDE_FRAC` guard would hand every
italic side-note the `AR` label.

⚠️ **A FOURTH INSTANCE OF THE SIGNATURE DEFECT WAS CAUGHT BY THIS WORK AND IS RECORDED, NOT
QUIETLY FIXED.** `score_foreedge.py` kept its **own copy** of the agent's class inventory so that
*"the agent has no name for this"* would be a checked claim — a good instinct that became a second
source of truth, and the first run after adoption printed `AR recall 4/4` and `AR ⚠️ NO NAME IN THE
AGENT` **about the same four boxes**. **A checking claim that can drift from what it checks is not a
check.** `visual_agent.CLASSES` is now the single declaration. Likewise the frame→archetype→name
sequence had two call sites and R14.10a would have made it three; it is now one `settle()`.

🖼️ **AND IT WAS DRAWN, per Sir's standing instruction.** `agent_see.py` renders `AR` in violet —
chosen far in hue from both `MT` green and `CH` orange, the two names the class was misfiled into, so
the correction is legible at a glance. On **leaf 400** the eight italic lines under `CHAP. XXII.` were
solid green before today. On **leaf 411** the eleven-line argument now reads violet under an orange
`CHAP. XXVII.`, with the plain-language caption *"11 of its 11 lines of type deslant as ITALIC (100%)
and it is set to 99% of the measure."*

⚠️ **AND THE DRAWING IMMEDIATELY SHOWED THE NEXT DEFECT, WHICH IS LEFT OPEN RATHER THAN HAND-FIXED.**
Leaf 411 sets `Z z 2` at the foot with the catchword `Cades` beside it, and the agent calls the
**signature** a **catchword** — the same `SG → CW` boundary error GOLD-FOREEDGE already records once.
The foot band's centred/outer split is doing work it cannot support. It is **not** repaired here: it
is a second class boundary, it has no gold, and a hand-fix is banned. ⇒ **R14.10d**, filed below.

⚠️ **COVERAGE, STATED.** GOLD-ARGUMENT is 81 rows over 10 chapter openings of **ONE witness**, and
the adoption evidence is **six** of those leaves. It **discharges no gate**; rows 10a/10b remain
reserved for GOLD-LAYOUT (R16.1). What it establishes is exactly this: the agent's class inventory
grew by one class the page prints, validated outside the gold that revealed the gap, at zero cost to
every existing number.

| # | step | deliverable | acceptance |
|---|---|---|---|
### R14.10c RESULT — 🔴 BLOCKED 2026-08-27b. Two cues refuted, and R13.1 is now gating the inventory

**No code was adopted, and that is the correct outcome rather than a stalled one.** Three independent
blockers were measured, each of which alone would prevent adoption. ⚠️ **This is an ALERT that the
approach needs redesign (§0.5), never an accepted gap** — `AN` stays OPEN and blocks.

🔴 **BLOCKER 1 — TWO VISUAL CUES BUILT AND REFUTED. A negative result, recorded because it is one.**
The obvious reading is that this edition sets its annotations in smaller, tighter type than its
scripture. Both halves were measured over all 20 leaves, per box, from the R14.10a fount record:

| candidate cue | leaf 417's annotation block | what it actually separates | verdict |
|---|---|---|---|
| **type height**, vs the page's largest text block | **0.89** | marginal notes, at **0.64–0.69** — every box it flags is an `MN` | 🔴 **REFUTED** |
| **line pitch**, same normalisation | **0.84** | nothing — leaf 418's *marginal note* reads **0.84** exactly | 🔴 **REFUTED** |

**Small type marks APPARATUS IN GENERAL, not annotation in particular.** The annotation block sits at
0.89/0.84 — nearer the body than the marginalia — so a threshold that catches it catches every side-
note first. ⚠️ This is R2.2o.1's finding in a new place: **the two populations overlap, so no constant
exists to be found**, and threshold-tuning is refuted as the repair rather than merely unattempted.

🔴 **BLOCKER 2 — THE ONLY RELIABLE ANCHOR REQUIRES A READ, WHICH IS R13.1.** The section head *is*
decisive, and the census says exactly why it cannot be used yet — **10 `SectionHeader` boxes in the
window, 9 of them `CHAP. N.` and 1 of them `ANNOTATIONS.`**, and geometry does not tell them apart:

    leaf 400 · 403 · 404 · 406 · 407 · 412 · 414 · 416 · 417(2nd)   -> block below is an ARGUMENT
    leaf 417 (first head)                                           -> block below is the ANNOTATIONS

*"Is this head the word ANNOTATIONS or the word CHAP."* is the **quick confirming read** §3.0's S2
describes, and **R13.1's wiring does not exist**. ⚠️ **So R14.10b and R14.10c are blocked on the SAME
thing**, and that changes what R13.1 is: not one step among many, but **the step gating the agent's
class inventory**. Two of the three classes the page prints and the agent cannot name are waiting on
it. That is a far stronger argument for R13.1 than R14.10b made alone.

🔴 **BLOCKER 3 — THE POPULATION IS ONE, AND IT IS ON THE WRONG LEAF.** GOLD-FOREEDGE holds exactly
**one** `AN` box, on **leaf 417 — one of its own five**. R14.10's section rule forbids validating a
cue against the gold that revealed the gap, so even a working cue **could not be adopted on this
window**. ⚠️ Unlike R14.10a, which had six disjoint leaves waiting in an existing gold, there is no
second exemplar to move to. **A cue fitted to leaf 417 would be fitted to a single page.**

⚠️ **AND THE LABEL-SOURCE AUDIT WAS BLIND TO THE FIELD IT MOST NEEDED — a SECOND false absence, in the
shape it already documents.** `audit_label_sources.py` answered *"has Annotation a source?"* from
`apparatus_blocks[kind]`, where the count is **0** because all **1,334** of those blocks are
`kind='argument'`. The odr-com scrape **in the very same documents** carries a top-level `annotations`
field — **246 chapter-anchored blocks, each with its printed `ANNOTATIONS. Chap. N.` head** — and
`_odrcom_notes` reads `marginal_notes` and `inline_notes` out of those files and steps straight past
it. The audit's own footer already states the lesson: *a bounded search returns "not found" in the
same shape as an exhaustive one.* **The bound was a DIRECTORY the first time and a FIELD NAME this
time.** ⇒ the audit now carries an **`Annotation`** row and a fourth state:

| | |
|---|---|
| **246** annotation blocks on disk, with their heads | so `ABSENT` is **false** |
| **232** of them are **NEW TESTAMENT** | |
| the Old Testament holds **14** chapters over **2** books (Genesis, Exodus) | |
| 🔴 **NUMBERS HAS NONE** — and Numbers is where every region figure in this project is measured | so `ADMISSIBLE` is **worse than false** |

⇒ **`🟠 PARTIAL`, and it BLOCKS on the same footing as `ABSENT`.** A source that exists but does not
reach the volume the class is needed in leaves the class unlabellable *there*, and a status line
counting it as covered is the laundering §0.5 exists to prevent. `BLOCKED classes: 1 ['Annotation']`.

✅ **THE REDESIGN, since a blocker must come with one.** Three moves, in dependency order:

| # | move | why it is the right one |
|---|---|---|
| 1 | **R13.1 first** — wire the confirming read | it unblocks `AN` **and** `PN` together; nothing else does |
| 2 | **move the annotation window to GENESIS or EXODUS** | the only OT books where the label source reaches, and the only place a population > 1 can be built without hand-labelling from scratch. ⚠️ New perception + fount records; the leaf set changes, so both caches rebuild |
| 3 | **pre-register the WIDTH cue and test it there, never here** | leaf 417's `ANNOTATIONS.` head spans **0.325** of the page against the nine chapter heads' **0.203–0.241** — a longer word sets wider, which is a fact about the fount and not a read. ⚠️ **Derived from ONE exemplar**, so it is a HYPOTHESIS to be tested on the wider population, and fitting it here would be fitting to a single page |

⚠️ **WHY NOT SIMPLY WIDEN THE PRESENT WINDOW.** Numbers has no annotation label source at all, so a
wider Numbers gold would have to be hand-labelled end to end — which is precisely what §3.2 item 2's
distant supervision exists to avoid, and what R14.6a checked the disk for.

| # | step | deliverable | acceptance |
|---|---|---|---|
| R14.10d | **The foot band's `SG` / `CW` split** (NEW 2026-08-27, found by DRAWING leaf 411) | the two foot-furniture classes are separated by a single `rel_f >= 0.60` position test, and leaf 411 prints **both** — signature `Z z 2` inside the measure, catchword `Cades` out at the fore-edge — so position alone cannot carry it. ⚠️ Same shape as the head band, which needed a **second** cue (the detector's own class) once it was found to hold two things | a foot-band gold exists and both classes are scored; neither may steal from the other. ⚠️ **Currently NO GOLD covers either class**, so `SG`/`CW` figures are unadjudicated wherever GOLD-FOREEDGE does not reach. **C2 — assembly** |

### R14.6a RESULT — ✅ DONE 2026-08-26. Every class has a source, and the audit's own first run was wrong

**`witness/audit_label_sources.py`.** R14.6 rests on the claim that §3.2 item 2's text sources make the
agent's labels affordable without hand-labelling. **That claim had never been checked against the disk.**

| class | state | evidence |
|---|---|---|
| MainText | ✅ ADMISSIBLE | **150,834** verse reads across **5** witness read-files |
| **Marginalia** | ✅ **ADMISSIBLE** | **3,754** side-note objects, **3,538** `<mn>` anchors, **53** books — `janvier/original-douay-rheims-repo`, OT 1609 + NT 1582, **CC0**, **this edition** |
| Marginalia (2nd) | ✅ ADMISSIBLE | **165** `marginal_notes` + **266** `inline_notes`, 41 books — the odr-com scrape, **already on disk**. ⚠️ **corroboration, not volume** |
| Marginalia (alt) | 🟡 **CIRCULAR** | `scan_marginal`, 214,453 words — **the incumbent typer's own output** |
| Argument | ✅ ADMISSIBLE | **1,334** blocks, every one `kind='argument'` |
| RunningHead · Catchword · Signature | ✅ ADMISSIBLE | self-verifying positional-and-text tests |
| VerseNumber | ✅ ADMISSIBLE | numeral-matches-adjacent-verse |

🔴 **THE AUDIT'S FIRST RUN (08-25) REPORTED A FALSE ABSENCE, AND THAT IS THE MORE USEFUL FINDING.** It
searched `reconstruction/reads/` **only**, found no side-note text, and concluded *"no transcribed
side-note corpus is on this disk."* True of one directory, false of the disk. **Two sibling errors have
the identical shape**: the SRC clone was sought under `ocr-spike/.scratch/` when it lives at
`palimpsest/.scratch/`; and the Madueke source was sought with `find -maxdepth 7` when it sits at
**depth 8**, then reported as *"searched ALL of `~/Claude`."*

⚠️ **A BOUNDED SEARCH RETURNS "NOT FOUND" IN EXACTLY THE SHAPE AN EXHAUSTIVE ONE DOES** — no error, no
warning, nothing separating *"it is not there"* from *"I stopped before I reached it."* **State the
bound, or do not claim the scope.** Same disease as the OPEN register that counted only what someone
remembered to type into it: a limit that does not announce itself. The Executive Summary already
records this project excluding a witness on a mistaken one-line description and producing a false
*"nothing survives"* verdict at the most consequential point in the New Testament. **An absence is a
claim and inherits the evidential standard of any other claim.**

⚠️ **`.scratch/original-douay-rheims` IS A BYTE-IDENTICAL COPY OF `janvier`** — 394 files, **0**
differences — so treating it as a second witness would have double-counted one corpus. The audit reads
the **tracked homes** under `imports/…/sources/transcriptions/`, not working copies.

⚠️ **TWO RUN-1 FINDINGS SURVIVE THE CORRECTION UNCHANGED.**
1. **§3.2 item 2 NAMES THE WRONG SOURCE.** It reads *"Marginalia from the 1,334 transcribed apparatus
   blocks"*; all 1,334 are `kind='argument'` — the italic prose summary before a chapter. An Argument
   is archetype C's class, a MarginNote archetype B's. **The right source was never the one the plan
   named**, and the error would have surfaced only after training, as an unimproved marginalia score.
2. **`scan_marginal` IS STILL POISON.** It is `margin_by_page`, the output of `layout.type_lines`.
   Training a replacement on its predecessor teaches agreement with the instrument being replaced, and
   that agreement then reads as validation. **A circular label is worse than a missing one, because a
   missing one is visible.**

🎁 **AN UNPLANNED GAIN: the notes arrive carrying the verse they attach to.** That is the note-to-verse
relation **S5 / Gate 10e** exists to measure, which had been scoped as separate work.

⚠️ **AND THE OPEN QUESTION R14.6c MUST SETTLE.** These are verse- and chapter-addressed transcriptions,
never leaf- or pixel-addressed. Alignment is what turns them into layout labels, and it is also what
keeps the supervision non-circular. ⚠️ **Unresolved: janvier's notes hang off chapter ANNOTATIONS, so
they may be marginalia of the annotation pages (archetype E) rather than of the scripture pages
(archetype B) our gold window holds.** R14.6c's scoring against the 19 hand-labelled MN entries is
exactly the check that would catch it — do not assume it either way.

| # | step | deliverable | acceptance |
|---|---|---|---|
| R14.6b | ✅ **RE-SCOPED 2026-08-26 from "scrape" to "INGEST THE LOCAL CORPORA" — no scrape was performed** | ingest `janvier` (primary) and `originaldouayrheims-com/apparatus` (corroborating) as `apparatus_blocks` with `kind='annotation'`, pinned under R11.3a to their tracked `imports/…/transcriptions/` homes | Marginalia reads ADMISSIBLE from a **tracked, pinned** path rather than a scratch copy. ⚠️ **The scrape the plan called for had ALREADY BEEN RUN** — 763 files sit in `originaldouayrheims-com/apparatus/`; the cross-map note *"odr_com apparatus = raw scrape follow-up (not in `odr_com.json`)"* meant *not folded into that file*, **not** *never fetched*. An outward-facing fetch of data already held would have been redundant. **C2 — acquisition** |
| R14.6c | **Generate and VALIDATE the seven admissible classes** | labels for MainText · Marginalia · Argument · RunningHead · Catchword/Signature · VerseNumber, over leaves 400–419 first | scored **against the 121-entry hand gold on that window** before any corpus-scale run, following `score_surya_layout`'s discipline: page-fraction addressing, binding by best overlap, **orphans reported separately**, label map declared before the run. ⚠️ **The hand gold is the generator's SCORER, never its trainer.** **C3 — assembly** |

| R14.7 | ✅ **DONE 2026-08-26 — DRAW WHAT THE AGENT SEES, on the leaf** (Sir's instruction) | `witness/agent_see.py`: the measure the agent derived, the head floor, every box in its class colour captioned with confidence and a **plain-language reason**, gold agreed-with in grey, every disagreement in red, archetype and its evidence at the head | it reads `visual_agent`'s **own** output, never a reimplementation — a second code path that can silently disagree with the first is the defect this project keeps finding. ⚠️ **It earned itself immediately**: the frame bug that cost 11 of 20 running heads was invisible in every number and obvious in one picture. **C1 — instrument** |
| R14.8 | **Lift the head-band coverage limit — score the agent on notes beside the MEASURE** | the gold extended below the top 3 rows on the same 20 leaves (R2.2o.1b's window), so outer-margin notes running down the fore-edge are scored | MN recall reported **separately for head-band and fore-edge notes**, since only the first is measured today. ⚠️ **The besideness cue is expected to do BETTER here, not worse** — a fore-edge note clears the measure outright where a head-band note straddles it — and writing that expectation down before the run is what makes a null informative. **C2 — assembly** |
| R14.9 | **Repair the archetype classifier, which the agent's own abstentions localise** | 3 of the 6 residual MN misses are `cue says MN, but archetype A FORBIDS it` on leaves 402/413/415 — leaves that plainly carry apparatus and were typed `A` | archetype accuracy on the 20-leaf window, and those 3 abstentions resolved **by fixing the archetype**, never by relaxing the FORBIDS contract. ⚠️ **The contract is the thing that made the defect visible**; weakening it would trade a reported error for a silent one. **C2 — assembly** |

⚠️ **ORDERING.** R14.0 first, because it is nearly free and may change every estimate below it. R14.6
runs alongside R14.1 because it is the input to everything after. **R14.5 is last and is the only C4**:
a re-examination loop built before its stages can be measured would be a loop with no way to tell a
repair from a regression.

🔴 **WHAT R14 MAY NOT DO.** §3.0's forbidden list applies in full and is checkable: no hand-tuned
constant as the deciding signal for a boundary; no rule perfected against one witness on one window; no
capability outside the plan; no scheduling of prior-repair ahead of agent-building. ⚠️ **And no gate
number invented in advance** — 9.6, 9.7 and 9.8 are deliberately unwritten, exactly as 9.5 is, because
§0.5 forbids a threshold not derived from evidence. **Each is written after its characterisation runs.**

---

## R15 — ONE GATE REGISTER, and it must be READ (NEW, 2026-08-25)

**Complexity per sub-step**: declared in each row, C1–C4. **The pre-registered decision rule for
this section**: *a register defect is closed only when an EXECUTABLE check would have caught it; a
crosswalk written in prose and maintained by hand is the defect restated, not the remedy.*

### The finding

**Measured 2026-08-25 while reviewing all sections.** Three defects, one shape.

1. 🔴 **TWO GATE REGISTERS NAMED THE SAME CHECKS DIFFERENTLY.** Masterplan §3.2 publishes the geometry
   gate as **Gate 9** with clauses 9.1–9.8; §7.8's table publishes the same checks as rows **10a–10f**.
   **The document had already contradicted itself**: §2 reads *"Gate 10c's threshold cannot yet be
   written (§3.2b)"* while §3.2b calls that identical check **9.5**. Reconciled in §7.8, which is now
   declared canonical, with §3.2's numbers demoted to aliases that must carry their row id.
2. 🔴 **THREE CLAUSES HAD NO ROW AT ALL.** Gate 9.6 (abstention), 9.7 (relations) and 9.8 (the loop)
   were written into §3.2 earlier today and existed nowhere in §7.8 — so by §7.8's **own** document-level
   invariant (*"no step enters the build order until its row carries metric · threshold · named set · n
   · pre-registered effect size"*) they had not entered the build order. Rows **10d · 10e · 10f** added.
3. 🔴 **THE ROADMAP CITED §7.8 ZERO TIMES.** The canonical gate register was invisible to the work plan.
   The consequence is not abstract: **Gate 11 — G1 recognition, the gate for the character recognition
   model — had NO Roadmap step of any kind**, while "what progress on the recogniser?" was a live
   question being answered from validation figures that §7.8 explicitly says are *"neither Gate 11
   measurements nor layout measurements."*

⚠️ **Same shape as the stale OPEN register found the same day, and as this project's signature defect
(now 16 instances): a correct register that nothing reads.** The OPEN register decayed because it was a
hand-maintained prose list; §7.8 was never wrong, it was simply never consulted. **Both failure modes are
invisible to a reader and both are trivially visible to a parser.**

### Steps

| # | step | deliverable | acceptance |
|---|---|---|---|
| R15.1 | **The crosswalk becomes an executable check, not a paragraph** | `witness/audit_gate_register.py`: parses §7.8's table and §3.2's clause table from the Masterplan and the step ids from the Roadmap, and reports (a) any §3.2 clause with no §7.8 row, (b) any §7.8 row with no Roadmap step, (c) any gate id cited in the Roadmap that §7.8 does not define | the audit **reproduces today's three findings from the documents alone**, and would have failed before this session's edits. ⚠️ **A crosswalk maintained by hand is the defect restated** — the prose table in §7.8 is for readers; this is what binds it. **C2 — instrument** |
| R15.2 | **Every §7.8 row carries the Roadmap step that discharges it** | a `discharged by` column, or an equivalent mapping the audit reads, covering rows 0a–14 | **every row maps to a step or is explicitly marked NOT YET PLANNED** — the second is an acceptable state and a silent absence is not. ⚠️ Expect rows to be genuinely unplanned; **naming them is the deliverable**, not eliminating them. **C2 — assembly** |
| R15.3 | **Register the audit in the verification standard** | the command added to the audit block with a claim whose first fraction the command prints | the suite runs it; exit 1 while rows remain unplanned is the **healthy** state, as with `audit_prereq_ceilings`. **C1 — wiring** |

⚠️ **R15 MAY NOT "FIX" ITS FINDINGS BY DELETING THEM.** An unplanned §7.8 row is closed by *planning
it*, never by removing the row or by marking it out of scope without a stated reason. The audit exists
to keep that pressure visible, which is why exit 1 is healthy.

### R15.1 · R15.2 · R15.3 RESULT — ✅ **ALL THREE DONE 2026-08-26.** The crosswalk is an instrument, and its first run found two more

**`witness/audit_gate_register.py`** parses §7.8's table, the crosswalk beneath it, and the Roadmap's
step ids, and reports four classes: (a) a Masterplan clause with no canonical row, (b) a row with no
step, (c) a gate cited in the Roadmap that §7.8 does not define, (d) the Roadmap not reading §7.8 at
all. **Live: exit 1, 0 hard defects, `12/25` rows discharged, `13` NOT YET PLANNED.**

**R15.1's acceptance was the hard part, and it is met by `--selftest`.** The acceptance reads *"the
audit reproduces today's three findings from the documents alone, and would have failed before this
session's edits."* The second half **cannot be shown against the live files, because the live files
were already fixed by hand on 08-25** — an audit written after a hand-repair always passes, and a
passing run proves nothing about whether it would have caught anything. So the **pre-fix document
state is reconstructed in the file** and the same pure `audit()` function is run against it: it
returns **8 hard defects**, including `Gate 9.6 / 9.7 / 9.8` with no row and the Roadmap citing §7.8
zero times. ⚠️ **A guard that has never rejected anything is not known to work** — the standing rule
in this project, applied to an audit for the first time.

🔴 **THE FIRST LIVE RUN FOUND TWO DEFECTS THAT HAD SURVIVED THE HAND FIX, AND ONE IS SUBSTANTIVE.**

1. 🔴 **`Gate 0e` and `Gate 0f` HAD NO ROW IN THE CANONICAL REGISTER.** Both are cited throughout
   this Roadmap and throughout §2; both are enforced by shipped guards (`test_setting_verified.py`,
   `test_verse_scope.py`, `test_verse_scope_bypass.py`); Gate 0e **blocks 0b and 0c**, and therefore
   all transcription. §7.8 published rows 0a–0d and stopped. **This is the fourth instance of R15's
   own defect, sitting inside the table R15 was written to bind** — and it was invisible to the
   2026-08-25 review, which read the table and reconciled the *geometry* clauses it was looking for.
   ⇒ Rows **0e** and **0f** added, each carrying metric · threshold · set · n · discharging step, per
   §7.8's document-level invariant. ⚠️ **Row 0e's `n` cell records the R8.4a limit rather than
   rounding it away**: head criteria at ≥3 separated points, **foot criteria at ONE**, R8.4b open.
2. **The crosswalk wrote one row id as `row 3` where every other cell reads `10a`**, so the archaic
   typeset census clause (`Gate 4.1`) resolved to nothing and the audit reported it hard. A cosmetic
   inconsistency in prose is a parse failure in an instrument — which is the argument for the
   instrument. Normalised to `3`.

📌 **R15.2's FILL-IN IS ITSELF THE FINDING, AND IT IS NOT A HAPPY ONE.** Ten of twenty-three rows had
a step; the column made the other thirteen sayable for the first time. Rows 12–14 *should* be
unplanned this early and rows 10c–10f are deliberately numberless. **Three of the thirteen are
neither**: row **1** (drop-cap fix, 18 cells), row **2** (residue detector) and row **3** (archaic
typeset census) are the Executive Summary's own three **low-to-medium-complexity, no-prerequisite**
items — this project's cheapest gates, unowned by any step, while four hand-built span rules were
being refuted against one witness. **Row 9 (GOLD frozen) is the most consequential**: it blocks rows
10a–10f *and* row 11, i.e. **both** models whose status §8a reports, and R13.3 already names it as
its own blocker. ⇒ Those four are the subject of **R16**, filed below. Naming them was R15.2's
deliverable; **planning them is the only permitted way to close them.**

⚠️ **The bare family ids `Gate 0` and `Gate 9` are EXCLUDED from finding (c) by a declared constant**,
not by a quietly permissive regex. They name a gate, not a check. The exclusion is written in the
file with its reason, because an undeclared exclusion is R14.6a's bounded search reporting itself as
exhaustive.

---

## R16 — The four unowned gate rows R15.2 made visible (NEW, 2026-08-26, found by R15.1)

**Complexity per sub-step**: declared in each row, **C1–C3**. **The pre-registered decision rule for
this section**: *a row is discharged only by a measurement against the threshold §7.8 already
publishes for it; those thresholds were written before any measurement here and may not be revised in
light of one. A row that misses its threshold stays OPEN and blocks — it is never closed by
re-scoping the row.*

**Discharges** §7.8 rows 1, 2, 3 and 9. **Status: OPEN, nothing built.**

🔴 **WHY THESE FOUR AND NOT THE OTHER NINE.** The other nine unplanned rows are unplanned *correctly*:
rows 4–8 depend on the pilot and the reference-text work, rows 12–14 are generation-2 and publication,
and row 10c cannot have a threshold until a hand-measured slant set exists. **These four are the ones
whose absence is not explained by their prerequisites.** Rows 1–3 need nothing but the corpus, which
Gate 0 has largely delivered; row 9 is a **prerequisite of the two rows this project's Primary Question
is about**, and had no owner.

| # | step | deliverable | acceptance |
|---|---|---|---|
| R16.1 | **Freeze GOLD-LAYOUT and GOLD-TEXT** — §7.8 row 9, and the blocker under both models | sha-pinned sets with a **gathering-level split** and a **per-archetype quota** (§3.2a), per-class **and** per-archetype `n` published | row 9's threshold as published: *frozen; per-class AND per-archetype n published*. ⚠️ **BLOCKED BY R12.1** — a per-archetype quota cannot be filled before the archetype census names the archetypes. ⚠️ **The 121-entry GOLD-HEADBAND is NOT GOLD-LAYOUT** and may not be renamed into it: 20 leaves, one witness, top 3 rows (R14.0's coverage limit). **C3 — assembly** |
| R16.2 | **The residue detector** — §7.8 row 2 | the ranked defect queue of §4.2 / Overview §4.2: fraction of a chapter's reference text matched by **no** recognised line, ranked across leaves, **plus** the reference-independent variant for the 8,383 loci with no archaic witness | row 2's threshold as published: **leaf-ranking precision@50 ≥ 0.6** against known defects, n = 50 leaves. ⚠️ Uses the incumbent **as a detector, never as a generator**, so its bias does not propagate. **C2 — assembly**; the Executive Summary ranks it **low** complexity and *"the first real improvement to ship"*, and it has had no step for the life of the project |
| R16.3 | **The archaic typeset census** — §7.8 row 3, alias Gate 4.1 (§4.1) | every requested sort resolved **ATTESTED or NOT FOUND, per volume**, with an exemplar image and a frequency count; closes the tall-s/long-s, **crossbar-long-ſ allograph**, `ꝛ` and brevigraph/blackletter questions together | row 3's threshold as published: **100% resolved; exemplar image + frequency per attested class**, on a stratified per-volume page set. ⚠️ **This gates the CODEC**, and §4.1 is explicit that a class asserted but absent invites hallucination out of damaged type. ⚠️ The crossbar allograph is the one that **defeats nub-based ſ/f discrimination silently across a whole volume** — a NOT FOUND here is as load-bearing as an ATTESTED. **C3 — instrument design**: the adjudication of ambiguous sorts is the difficulty, not the enumeration |
| R16.4 | **Drop-cap board fix + page axis** — §7.8 row 1 | the 18 cells §7.8 names, moved against a **frozen** board | row 1's threshold as published: **18 cells moving to OPEN, against a frozen board, never netted**. ⚠️ **Never netted** is the whole of it: a repair count published against a regression count that is not published is the laundering §7.6's regression rule forbids. **C1 — mechanical** |

⚠️ **ORDERING.** R16.2 and R16.3 are independent of R14 and of each other and may run in any order.
**R16.1 is ordered after R12.1** and is the one that unblocks Gate 11 (R13.3) and rows 10a–10f. R16.4
is mechanical and is ordered last **only** because it is mechanical — not because it is optional.

🔴 **R16 MAY NOT BE CLOSED BY R14.** R14 builds the agent; R16.1 builds the set that **scores** it.
Filing the scorer's set under the model's programme is how a model comes to be evaluated on data it
was built against, which §7.1's three tiers exist to prevent.

---

## R13.3 — Gate 11 has never had a Roadmap step (NEW, 2026-08-25, found by R15)

**Complexity: C3 — measurement.** **The pre-registered decision rule**: *Gate 11's thresholds are
already published in §7.8 (CER-folded ≤1.0%, CER-diplomatic floor+δ, per-class published, abstention
reported); they were written before any measurement and may not be revised in light of one.*

🔴 **THE PRIMARY QUESTION ASKED WHAT PROGRESS HAS BEEN MADE ON THE CHARACTER RECOGNITION MODEL, AND THE
HONEST ANSWER IS THAT ITS GATE HAS NEVER BEEN PLANNED.** R13.1 wires the recogniser in; R13.2 measures
the ſ-surface effect on the `CONTENT OK, ſ-SURFACE OPEN` cells. **Neither is Gate 11.** Gate 11 is
CER-folded and CER-diplomatic against GOLD-TEXT with a cluster bootstrap, and it is the row that says
whether the recognition model is good enough — a question the 0.9396 validation accuracy and the
`genesis-24` 0.9448 content score **do not answer**, as §7.8 states in terms.

| # | step | deliverable | acceptance |
|---|---|---|---|
| R13.3 | **Gate 11's first measurement, once GOLD-TEXT is frozen (§7.8 row 9)** | CER-folded and CER-diplomatic over GOLD-TEXT, per class, with abstention reported, by the §7.2 cluster bootstrap | the published thresholds are met **or the gap is reported as OPEN**. ⚠️ **BLOCKED BY row 9** (GOLD-TEXT frozen) and by **R13.1** (a gate measured on an unwired model measures the wrong model). ⚠️ **Do not substitute validation accuracy** — a model's own validation split is not GOLD-TEXT, and §7.8 already refuses that substitution by name. **C3 — measurement** |

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
../ocr-venv/bin/python witness/test_glyph_role_bar.py      # R9.7  Gate 0f's last hole: the ROLE bar on glyph work is ENFORCED -> 6/12 records refused at glyph grain, and the bar is grain-specific. GLYPH_BARRED was keyed by SIGLUM and held only F and X, so glyph_source returned a usable PDF path for NT-1582-M although its lowres role bars it from training data, CER and long-s adjudication -- a bar written in ROLES and enforced by nothing. A siglum key could never have closed it: M is ONE file holding TWO books with DIFFERENT roles. The proven negative removes the role clause and NT-1582-M and OT-1635-M leak, exactly the two records the Overview predicted. Clause 4 asserts the bar costs the visual agent nothing: a glyph-barred lowres record is STILL a structural witness for layout and geometry
../ocr-venv/bin/python witness/test_project_root.py         # R9.6/R11.4 one derived root; the legacy tree is not named, traversed to, or resurrected
./.venv/bin/python core/tests/fixtures/gold/mask_engine/originaldr_reconstruction/acquisition/acquire_sabates_a.py --verify  # R11.3a the apparatus clone is the pinned commit AND the pinned bytes
../ocr-venv/bin/python witness/test_region_gold_addressing.py  # R2.1i a splitter change must not MISBIND a gold label
../ocr-venv/bin/python witness/test_open_register_consistency.py # a step marked done must not remain in the OPEN register
../ocr-venv/bin/python witness/score_head_regions.py       # R2.1g: exits 0 -> head-band region assignment, RunningHead recall 20/20; accuracy 0.8760 against controls of 0.6612 and 0.8017
../ocr-venv/bin/python witness/score_head_tokens.py        # R2.1h: exits 0 -> head-band word split, RECOGNISER exact 0.8125 >= bar 0.75, blob 0.0000, beats both controls
../ocr-venv/bin/python witness/gold_rekey_pagefrac.py      # R2.2c: exits 0 -> the region gold's page-anchored address is TOTAL, 125 / 125 entries placed and 0 unplaced (report-only; --write rebuilds it)
../ocr-venv/bin/python witness/build_argument_gold.py --check # R2.2d: exits 0 -> 81 argument rows over 10 leaves and 15 adjudicated negatives, every address reproducible from the page
../ocr-venv/bin/python witness/build_region_gap_gold.py --check # R2.2e: exits 0 -> 49 rows are swallowed whole into one out-of-block token, 43 of them BODY, and every address reproduces from the page
../ocr-venv/bin/python witness/score_row_address.py       # R2.2j: exits 0 -> ADOPTED ink2d. Under a PURE RENAMING of rows, which moves no glyph, token or coordinate, the old ordinal address COLLAPSES (RunningHead and MarginNote recall both to zero, 90 of the 121 entries orphaned) while ink2d is bit-for-bit unmoved with 121 bound and 0 orphans. NB no N-slash-M fraction belongs in this claim: the checker takes the FIRST one, and a decimal pair like acc-slash-RH would parse as a fraction the scorer never prints
../ocr-venv/bin/python witness/audit_recog_holdout.py # R2.1b PREREQUISITE: exits 0 -> the selection set is HELD OUT from all five recognisers, proven against every training manifest on disk before any score is taken. All 5 models exist; no training slug names NUMBERS and no training page falls in leaves 400-419, the training corpus spanning pages 18-92 over genesis, psalms, matthew, 2john, 2esdras and proverbs. ⚠️ THIS IS NOT A FORMALITY: the five headline accuracies are per-arm figures on DIFFERENT splits, so a selection made on a set some model has seen would select that model and look exactly like a measurement. ⚠️ The BOUND is stated rather than the scope claimed -- this proves the leaves appear in no manifest ON THIS DISK, and a model trained from a manifest not on this disk is invisible to the check, which is said because a bounded search returns 'not found' in the same shape an exhaustive one does
../ocr-venv/bin/python witness/build_recog_gold.py # R2.1b: exits 0 -> ⚠️ THIS COMMAND IS DELIBERATELY THE NO-ARGUMENT ONE AND THAT IS A FINDING THIS BLOCK PAID FOR: the standard runs every command it names WITHOUT its arguments, so when this file was enrolled as `build_recog_gold.py --check` the suite ran it BARE, took the CUTTING path, and rewrote all 51 hand-keyed truth files as empty -- the keying had to be redone. Cutting is now opt-in behind --cut and refuses to clobber existing truth even then. A script whose no-argument behaviour is destructive WILL be run destructively by this block. The check reports the fixed selection set is fully keyed: 51 lines keyed, 0 pending, 12 EXCLUDED with a stated reason each, of 63 crops cut over 7 region classes from OT1-1609-B leaves 400-419. Truth is HAND-KEYED FROM THE PAGE and diplomatic, long-s preserved and the page's own typos kept. ⚠️ IT IS NOT TAKEN FROM GOLD-HEADBAND's `text` FIELD, which is the INCUMBENT RECOGNISER'S OUTPUT carried so a human could assign a LABEL -- leaf 402's running head reads NVMENE there for NVMERI and leaf 400's side-note reads X. Og Alaine. for K. Og slaine. -- so scoring candidates against it would measure agreement with the instrument being replaced, the identical defect audit_label_sources records for scan_marginal. ⚠️ Crops are cut per REGION SEGMENT, not per row: cutting by row put a page number, a running head AND a side-note in one image labelled RH, because a row is not homogeneous in region. ⚠️ The 12 exclusions are CROP defects -- two baselines in one image, a clipped first or last sort, two margin columns merged -- counted and reasoned, never silently dropped, and 7 of them are MarginNote, the class this edition is built around and the one the cutter fails hardest on
../ocr-venv/bin/python witness/score_recognisers.py # R2.1b: exits 0 -> dr_v3_armB is SELECTED on 7 class wins of 7 over a set held out from all five, pooled content 0.9575 against reichenau_dr 0.8902 and dr_v3_armA 0.8597, with dr_armA and reichenau_dr_ho VETOED on the long s at 0.6744 and 0.8372 against a pre-registered floor of 0.90. 🔴 AND THE MEASUREMENT INVERTS THE HEADLINE RANKING, WHICH IS EXACTLY WHAT THIS STEP EXISTED TO TEST: dr_v3_armA carries the HIGHEST validation accuracy on this disk at 0.9739 and comes LAST of the three un-vetoed models here, while reichenau_dr -- the 0.9396 every document in this project cites -- wins ONE class of seven. A number that is higher on a different held-out set is not a better model, and that is now measured rather than merely suspected. ⚠️ The s-surface veto is applied FIRST and absolutely, never as a tiebreak: this edition's whole ladder exists to recover the archaic long s, so a recogniser that silently modernises it is useless here whatever its content score -- and it disqualified reichenau_dr_ho, the model built specifically for honest generalisation. ⚠️ Losers are published, per 0.2 rule 1. ⚠️ It establishes a COMPARABLE ranking on ONE held-out set of ONE witness, per region class; it does NOT discharge a gate, and those five headline accuracies remain non-comparable and must still never be quoted as a ranking
../ocr-venv/bin/python witness/recogniser.py # R13.1: exits 0 -> the SELECTED recogniser is reachable through ONE entry point and every reading it produces carries the model id AND the artefact's sha256 digest, because a path is a label a human chose and can point at a file that has since been retrained while the digest is what was actually opened. The model is READ FROM R2.1b's selection file, never named in this module: hard-coding one would re-create the exact defect R2.1b exists to prevent, and with the selection absent the module RAISES rather than falling back, since an arbitrary model wearing the selected model's authority is harder to see than no model at all. ⚠️ WHAT IS WIRED AND WHAT IS NOT IS STATED BY THE COMMAND ITSELF: gen1_r3.py still sets old_text from the stored corpus OCR, so the attesting-arm conversion is the REMAINDER of R13.1 and it changes campaign artefacts, which makes it a deliberate act rather than a side effect. ⚠️ R13.2 is a SEPARATE step and the 1142 CONTENT OK, s-SURFACE OPEN cells may NOT be reported as recovered before it runs -- plausibly is not measurably
../ocr-venv/bin/python witness/test_recogniser_provenance.py # R13.1 ACCEPTANCE: exits 0 -> the injection proof passes all 5 checks, so the provenance stamp is shown to TRACK the model rather than merely to be present. Swapping to another candidate changes the model name, changes the digest, and CHANGES THE READING on 5 of 12 crops -- and that last check is the load-bearing one, because a stamp can be correctly plumbed to a recogniser that is never actually consulted, and when broken output equals healthy output the MECHANISM must be validated rather than the label. With the selection file hidden the module RAISES rather than defaulting, and restoring returns the stamp to R2.1b's choice. ⚠️ A provenance field that no test can move is decoration, and it would let a reading produced by one model be published under another's name -- which is R13's own finding one level up, where a fine-tuned recogniser was pointed at in five documents and loaded by no code
../ocr-venv/bin/python witness/visual_agent.py            # R14.1/R14.2/R14.9: exits 0 -> THE ADAPTIVE VISUAL AGENT names 117/121 head-band gold entries on OT1-1609-B leaves 400-419 under BOTH declared addressing rules, with the bars applied to the WORSE of the two. All three rung-0 bars pass: MarginNote recall 18 of 19 against a bar of 0.50 where Surya off the shelf scores 0 of 19; overall 0.9669 against a bar of 0.8264 which IS Surya's own score on this gold, so buying marginalia with body text would FAIL; forbidden-class emissions 0. RunningHead is exact at 20 of 20, ChapterHead at 2 of 2, MainText 77 of 80. R14.9 raised it from 110/121 by two structural repairs, neither a threshold: the archetype classifier had REIMPLEMENTED a subset of the naming cues and so was blind to head-band notes, which made it type three apparatus leaves as plain text and forced the namer to abstain on notes it had correctly identified -- both steps now call ONE `_cue()`; and the agent gained the FOOT BAND with the gathering-signature and catchword classes, because a class with no name is not skipped but MISFILED, which is how leaf 409's `Z z` had become a chapter heading and pulled the whole leaf to archetype BC. ⚠️ The head-band gold could not see that error at all -- the score was unchanged by the foot-band repair -- so it was found by DRAWING the leaf, not by reading a number. ⚠️ Archetype A never fires on this window, so the FORBIDS contract does not currently bind and the zero forbidden-emission count is trivially true; the archetype call itself has NO GOLD and is unmeasured. R14.11 then raised it 115/121 to 117/121 WITHOUT touching a cue's meaning, by RETIRING the constant CENTRED_LO/HI: the running-head test is now the parameter-free predicate that the measure's centre-line falls INSIDE the box, measured as the offset of the box's centre from the measure's centre in units of the BOX'S OWN WIDTH. The two boxes gained were both ABSTENTIONS under the retired band, on leaves 400 and 411, and they sit 1.476 and 0.877 box-widths clear of the centre-line, so the old rule was declining to call boxes the centre-line plainly misses. ⚠️ Leaf 411 abstained by 0.079 against a THIN_MARGIN of 0.080, ONE THOUSANDTH of the measure -- the last-pixel failure mode this file already records twice. ⚠️ AND A PRE-REGISTERED PREDICTION WAS REFUTED HERE: the derivation was written down predicting GOLD-HEADBAND EXACTLY unchanged at 115/121, on the reasoning that the two rules induce the same partition. They do not, and the improvement is reported as a refutation of that prediction rather than banked as a gain. It DISCHARGES NO GATE: rows 10a and 10b are reserved for GOLD-LAYOUT and MainText here is containment
../ocr-venv/bin/python witness/build_skew_record.py # R14.14: exits 0 -> reports the per-leaf BASELINE ANGLE record standing behind the rotated frame, 20 of 20 leaves measured, range -0.901 to +1.636 degrees with median +0.131. The angle is fitted through the bottom edges of each row's glyph components and is measured PER LEAF because it varies per leaf -- a single corpus angle could not describe this window. ⚠️ IT IS NOT THE FOUNT RECORD'S `slant_mode`, and confusing them would be a dead metric impersonating a measurement: that quantity is GLYPH slant, the lean of the strokes that separates italic from roman, it is quantised to whole degrees, and it reads 0.00 on every leaf here, so read as skew it reports these pages as square. ⚠️ A leaf whose angle cannot be measured carries a null and a stated cause, and the agent falls back to an UNROTATED frame AND SAYS SO -- an unmeasured page and a square page are different states and a silent zero collapses them. ⚠️ Its no-argument behaviour is the REPORT, never the build
../ocr-venv/bin/python witness/build_reading_record.py # R14.10b: exits 0 -> reports the CONFIRMING READ record standing behind the PageNumber class -- 20 readings over leaves 400-419, each stamped with the model id AND the artefact sha256 that produced it. ⚠️ Its no-argument behaviour is the REPORT, never the build, which is the lesson build_recog_gold.py paid for: this block runs every command WITHOUT ITS ARGUMENTS, so a script whose bare invocation is destructive WILL be run destructively. Building is --build. ⚠️ The stamp is checked rather than trusted -- attach_reading REFUSES a record whose digest does not match the currently selected model, because a cached reading that outlives its model carries the selected model's authority while holding another's output, which is R13.1's defect mirrored
../ocr-venv/bin/python witness/score_argument_agent.py # R14.10a: exits 0 -> the agent has learned the ARGUMENT, the italic prose summary this edition sets between the chapter head and the first verse, and all five pre-registered criteria hold. A1 recall is 6/6 argument blocks on the SIX leaves DISJOINT from GOLD-FOREEDGE -- leaves 400, 403, 404, 407, 411 and 416 -- which is the whole of the evidence for adoption, because R14.10's section rule forbids validating a cue against the gold that revealed the gap. A2 precision is 0 false positives over the WHOLE 20-leaf window with 0 unadjudicated. A3 no-theft holds every GOLD-HEADBAND number EXACTLY -- 115/121 overall, MarginNote 16/19, RunningHead 20/20, MainText 77/80, ChapterHead 2/2 -- so the class was bought with nothing. A4 proves the cue ABSTAINABLE by a negative: with the fount record withheld the agent emits 0 argument boxes and all 20 leaves carry a stated cause, never a silent fall-through. A5 was the PRE-REGISTERED out-of-sample prediction, written before the run -- all four held-out ARGUMENT entries in GOLD-FOREEDGE should flip -- and it HELD exactly, 4/4, taking that gold from 34/42 to 38/42. ⚠️ THE DEFECT WAS 10 OF 10, NOT THE 4 R14.8 RECORDED, and the extra six are the informative half: measured at box grain, `SMALL_AREA` ALONE decided which wrong name the class got, six argument boxes above 0.05 of page area becoming MainText and four below it becoming ChapterHead. The MainText half is SILENT -- MainText is containment, so an argument called MainText scores as correct against every gold this project holds -- and it would have entered the verse stream as scripture. ⚠️ The cue reads the FOUNT, never the position: gating it on a detected chapter head is circular here in the strongest form, since on four of the ten leaves the argument box IS the agent's chapter-head call. ⚠️ It DISCHARGES NO GATE -- 10 leaves of ONE witness, and rows 10a/10b stay reserved for GOLD-LAYOUT
../ocr-venv/bin/python witness/build_foreedge_gold.py --check # R14.8: exits 0 -> GOLD-FOREEDGE, 42/42 adjudicated boxes reproduce their address from the page. The population is every detector box whose MASS sits BELOW the head band -- i.e. exactly what GOLD-HEADBAND cannot see -- and it is defined by GEOMETRY ALONE, never by the agent's label, so the gold cannot inherit the agent's blind spots. Adjudicated from `see/blind/*.png`, boxes NUMBERED and UNLABELLED. COVERAGE DECLARED: 5 of 20 leaves, ONE witness, ONE operator, NOT fully blind. It is the SCORER and may NEVER be promoted to GOLD-LAYOUT
../ocr-venv/bin/python witness/agent_see.py               # R14.7: draws the agent's OWN decisions onto the leaf -- the measure it derived, the head floor, every box in its class colour captioned with its confidence and its plain-language reason, the gold it agreed with in grey and every disagreement in red. Reads `visual_agent`'s output directly rather than reimplementing it, because a second code path that can silently disagree with the first is the defect this project keeps finding. The frame bug that cost 11 of 20 running heads was found by LOOKING at leaf 412, not by reading a number
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
repo-root-relative commands and their venv. C1; if the parser cannot be extended without
weakening its existing checks, ALERT rather than dropping the two entries from the block.**

🔴 **R11.2c — TWO MORE PARSER GAPS, found 2026-08-18 while registering R2.2c's commands. C1.**
1. **A claim is only enforced when the line contains `->`.** Both scorers — the modules carrying
   this project's headline numbers — were listed here with no `->`, so the standard reported them
   as `(not executed: no claim to check)` and **never ran them.** ⚠️ That is the very failure this
   block exists to prevent: a claim in a document with nothing able to refuse it, and it was sitting
   inside the instrument built to catch it. Their lines above now carry `->` and both are executed.
2. **The fraction regex is digit-only, so it misparses DECIMALS.** `0.6612 / 0.8017` parses as the
   pattern `6612/0` — so writing `score_head_regions`'s claim in its natural order would have
   manufactured a FALSE failure rather than a check. Its claim is therefore worded so the first
   fraction is the real one (`20/20`). ⚠️ **That is a workaround at the call site, not a fix**: the
   next person to write a decimal pair into a claim hits it again. The parser must either understand
   decimals or refuse a claim it cannot parse — silently matching `6612/0` is the worst of the three
   behaviours. **Not fixed here** because changing the parser is a change to the instrument every
   other number in this block is verified by, and it earns its own step.

✅ **R11.2e — RESOLVED THE SAME DAY. Full pass: 9m05s wall, exit 0, all 42 commands EXECUTED.**
Candidate **(2)** was adopted: the commands are mutually independent — no command reads another's
output and each is a separate interpreter — so the subprocess fan-out is concurrent
(`ThreadPoolExecutor`, ≤8 workers) instead of serial. 409% CPU, and **nothing is cached, sampled,
skipped or tiered**: every claim in the block still executes, which was the pre-registered rule.
Candidate **(1)**, a content-keyed result cache, is **struck** — correct in principle but a new
instrument, and a cache-invalidation bug here would silently pass a stale claim, which is a worse
failure than slowness. Candidate **(3)**, the `--fast`/`--full` split, is **struck outright** for the
reason written before the work: without the CI half it converts *"too slow to run"* into *"not
required to run."* ⚠️ A harness exception is now recorded as a **result** (`__HARNESS_ERROR__`), never
as a skip — a command that crashes the runner must not vanish from the tally.

<details><summary>The finding as originally filed (retained — it is the evidence the fix rests on)</summary>

🔴 **R11.2e — THE STANDARD CANNOT BE RUN. C2 — assembly.** (NEW 2026-08-26, and it is the third parser
defect in the same instrument, which is why it is filed rather than worked around again.) The block now
names 40 commands, several of which perform OCR — `r2_1d_continuity.py` above all — so a full run
**exceeded 15 minutes on two consecutive attempts** and was killed both times without producing a line
of output. ⚠️ **This is worse than a slow test.** Every headline number in this project is held honest by
this block; a block that cannot be executed holds nothing honest, and the failure mode is *silence*, not
a red result. **The pre-registered decision rule**: *the standard must complete a full pass, and the pass
must still EXECUTE every claim it prints — a tier that skips the expensive commands is the defect
restated.* Candidates, to be refuted by measurement rather than chosen by taste: **(1)** cache each
command's `(argv, input-sha) -> (exit, stdout)` so an unchanged command with unchanged inputs is not
re-run, with the cache keyed on content and **never** on time; **(2)** parallelise the subprocess fan-out,
which is bounded by CPU rather than by any ordering between commands; **(3)** split into `--fast` and
`--full` **only if** `--full` runs in CI on every commit, since a tier nobody runs is how this defect was
reached. ⚠️ **(3) alone, without the CI half, is forbidden** — it converts "too slow to run" into "not
required to run", which is the laundering §0.5 exists to prevent.

</details>

**The audits** — these are *expected to fail while their step is open*, and that is the point:

```
../ocr-venv/bin/python witness/audit_gt_rasters.py      # R7: exits 1 -> 48 of 51 GT files inadmissible, 9 WRONG SETTING
../ocr-venv/bin/python witness/audit_s06_keys.py        # R7.5a-2: exits 1 -> 261 derived artefacts still keyed `jp2-S06`
../ocr-venv/bin/python witness/audit_prereq_ceilings.py # R10.1: exits 1 -> STRICT: 24/98 step(s) declare a complexity class in their OWN row; the fraction must RISE -- but NOT MONOTONICALLY. 2026-08-27i moved both axes together again, 93 -> 98 and 19 -> 24, as Sir's second review filed R14.14 (the agent has NO ANGLE: real baseline tilt runs -2.39 to +2.75 degrees and the HORIZONTAL head line cuts through 41 boxes), R14.15 (the DETECTION FLOOR -- verse numbers, brief marginal notes and single-character signatures are classes the detector may not localise at all, and the claim that the page number is the smallest box is REFUTED, the catchword on leaf 401 and the signature on leaf 409 both being smaller), R14.16 (LECTOR is a hand-written decision procedure performing no inference and consulting no prompt, which is the largest design gap in the agent), R14.17 (the review toolkit) and R14.18 (gold expansion to 188 verified leaves, which raises an unmade decision about mixing witnesses). Earlier 2026-08-27h moved 90 -> 93 and 16 -> 19 as R14.11, R14.12 and R14.13 were filed. 2026-08-27h moved BOTH axes together, 90 -> 93 and 16 -> 19, as Sir's review filed R14.11 (no fixed measure may DECIDE), R14.12 (the LAMINATION) and R14.13 (the full-leaf gold review), each carrying its own complexity class. ⚠️ AND THE FILING HIT THIS AUDIT'S OWN PARSER, which is worth recording because it is the same shape the register trap already documents: own_rows matches `|` then a BARE step id, so the three rows were first written as `| **R14.11** |` and read as INHERITED rather than covered -- the numerator held at 16 while three properly classed rows sat in the document. Unbolding the id fixed it. A declaration the instrument cannot parse is indistinguishable from a declaration nobody made. Earlier 2026-08-27f moved the denominator 89 -> 90 with the numerator HELD at 16, and it is a piece of ceiling DEBT recorded rather than dressed up: R11.2f was filed because the verification standard's guard inventory is the glob `test_*.py`, so the standard STRUCTURALLY CANNOT NOTICE A NEW SCORER -- two were added that day and it reported no gap, while its own rule 3 promises that adding a guard and forgetting to document it is caught. Like its R11.2b and R11.2c neighbours its class sits in PROSE rather than in a table row, so the STRICT numerator does not move and the uncovered count rises by one; R11 is a prose section throughout, and converting it to rows is a change to a section, not a change to a step. ⚠️ It is the FOURTH false absence of one shape -- a bounded search returning not-found in exactly the shape an exhaustive one does -- after audit_label_sources.py bounded by a directory and then by a field name, and R14.10b's own candidate test bounded by the head band, which reported four detector gaps that were not there and was caught by a gold built for another step. 2026-08-27f moved the denominator 89 -> 90 with the numerator HELD at 16, and it is a piece of ceiling DEBT recorded rather than dressed up: R11.2f was filed because the verification standard's guard inventory is the glob `test_*.py`, so the standard STRUCTURALLY CANNOT NOTICE A NEW SCORER -- two were added that day and it reported no gap, while its own rule 3 promises that adding a guard and forgetting to document it is caught. Like its R11.2b and R11.2c neighbours its class sits in PROSE rather than in a table row, so the STRICT numerator does not move and the uncovered count rises by one; R11 is a prose section throughout, and converting it to rows is a change to a section, not a change to a step. ⚠️ It is the FOURTH false absence of one shape -- a bounded search returning not-found in exactly the shape an exhaustive one does -- after audit_label_sources.py bounded by a directory and then by a field name, and R14.10b's own candidate test bounded by the head band, which reported four detector gaps that were not there and was caught by a gold built for another step. Earlier, 2026-08-27c is the cleanest demonstration the register has produced: R2.1b CLOSED, and because R2.1b carries its complexity class in its OWN row, closing it REMOVED that declaration from the OPEN population, so the denominator fell 89 -> 88 and the numerator fell 17 -> 16 together. A numerator that only ever rises is not measuring anything. R2.1b's close is the recogniser SELECTION: dr_v3_armB chosen on 7 class wins of 7 over a set held out from all five models, which INVERTED the headline ranking -- the highest validation accuracy on disk, dr_v3_armA at 0.9739, is the WORST of the three that clear the long-s veto. That UNBLOCKS R13.1, whose mechanism half then landed the same day and filed R13.1a for the remainder, taking the denominator back 88 -> 89 while the numerator HELD at 16. ⚠️ R13.1a is counted INHERITED rather than covered, exactly as R13.1 and R13.2 already are: the R13 section declares `Complexity per sub-step: declared in each row` and its rows end in a bare class token that CEILING_RE does not match, so all three inherit from the section instead of declaring. That is a PARSER gap in this instrument, not a gap in those rows, and it is recorded rather than fixed here for the reason already standing over the decimal-pair trap below -- changing the parser is a change to the instrument every other number in this block is verified by, and it earns its own step. Earlier on 2026-08-27 the register moved twice and NETTED TO ZERO on both axes, which is worth stating because a register that only ever grows is not being maintained: R14.10a CLOSED as the agent learned the ARGUMENT class -- removing its declaration from the OPEN population -- while R14.10d was filed in the same edit, carrying its own complexity class, so 89 stayed 89 and 17 stayed 17. R14.10d was NOT found by a number: the foot band's signature/catchword split is a single position test, and leaf 411 prints a signature INSIDE the measure with its catchword out at the fore-edge, which the DRAWING showed at a glance and no gold covers at all. Earlier the same day (88 -> 89 as R14.8 and R14.9 CLOSED -- the archetype classifier no longer reimplements a subset of the naming cues, and the agent gained a FOOT BAND -- and R14.10a-c were filed from R14.8's class-inventory finding, each row carrying its own class, so the numerator rose 16 -> 14 -> 17: it FELL first because closing two steps removes their declarations from the OPEN population, which is the audit working correctly and is worth stating, since a numerator that only ever rises is not measuring anything. Earlier on 2026-08-26, four moves that NET to zero: R9.7 and R11.2e both CLOSED -- the Gate 0f role bar is now enforced with a proven negative, and the verification standard runs to completion in 9m13s by concurrent fan-out with every command still EXECUTING -- while R14.8 and R14.9 were filed from the agent's own residue, both carrying their complexity class in their own row, so the numerator rose 14 -> 16 on a flat denominator. Earlier the same day, in two moves. 87 -> 88 was R11.2e, the verification standard being unrunnable, and it is the day's ONE piece of ceiling DEBT: its class and decision rule are written in PROSE like its R11.2b/R11.2c neighbours rather than in a table row, so the STRICT numerator does not move and the uncovered count rises by one. Recorded as debt rather than dressed up -- R11 is a prose section throughout, and converting it to rows is a change to a section, not a change to a step. 86 -> 87 was R15.1-R15.3 CLOSING and R16.1-R16.4 being filed from the gate-register audit's first live run, numerator 13 -> 14 because all four R16 rows carry their own complexity class under a section-level pre-registered decision rule -- the uncovered count HELD, so a net +1 step added no ceiling debt; ⚠️ AND THE REGISTER'S OWN DOCUMENTED TRAP FIRED DURING THAT EDIT: the R16 entry was first worded as "the four unowned rows R15.2 made visible", which enrolled the CLOSED R15.2 as OPEN and read 88; the attribution was reworded to name the audit rather than the step, exactly as the 2026-08-25 caution below says it must be. Earlier history: denominator 59 -> 63 on 2026-08-18: R2.1k, R2.2c, R11.2c and R2.2d were added to the register; 63 -> 64 on 2026-08-19: R2.2e; 64 -> 67 on 2026-08-20: R2.2f, R2.2g and R11.2d; 67 -> 68 later the same day: R2.2h, the modal-edge estimator tolerance; 68 -> 69: R2.2i, tilted lines cut into two rows; 69 -> 70: R2.2j, the gold's row-ordinal addressing; 70 -> 71: R2.2k, the row clusterer chaining against a running median and walking up the tilt onto the next baseline; 71 -> 72: R2.2l, the adopted ink2d addressing losing a token without reporting it; R2.2l CLOSED on 2026-08-21 and R2.2m opened the same day for the same uncounted idiom in the containment path, so the denominator is unchanged at 72; **72 -> 81 on 2026-08-25** — the register was found STALE, having stopped at R2.2m while the project worked on steps it could not see, so R2.2n, R2.2o and its four sub-steps were filed along with the seven R14 steps of the adaptive visual agent, and the numerator rose 1 -> 8 because R14 was filed WITH a section-level pre-registered decision rule and per-row complexity classes rather than added bare; the uncovered count held at 38, so the filing added no debt; **81 -> 84 later the same day** as R13.3 and R15.1-R15.3 were filed and R14.0 CLOSED, numerator 8 -> 11; **84 -> 86 on 2026-08-26** as R14.6b and R14.6c were filed, numerator 11 -> 13 -- and the filing exposed that the R13 SECTION carried neither a ceiling line nor a decision rule, so R13.1 and R13.2 had been uncovered since 2026-08-17 and are now inherited; note also that the R15 ceiling line was invisible until a literal C-token was added to it, since CEILING_RE requires the class on the same line as the Complexity heading; **84 -> 86 on 2026-08-25** as R14.6b and R14.6c were filed from the label-source audit's finding, numerator 11 -> 13 because both rows carry their own complexity class under R14's existing decision rule, so the uncovered count HELD at 36 and the filing added no debt. ⚠️ A caution learned in that same edit: the register block is parsed for step ids, so naming a CLOSED step in the register's own prose — even parenthetically, as attribution — enrols it as OPEN. The denominator read 87 until the attribution was reworded)
../ocr-venv/bin/python witness/r2_1d_continuity.py          # R2.1d'(A): exits 1 -> catchword continuity 0.312, Wilson95 lower 0.142 vs bar 0.95; R2.1f has FIRED
../ocr-venv/bin/python witness/score_argument_region.py # R2.2d: exits 1 -> on the gold extended to ALL 10 chapter openings D1 recall is 52/81 rows and D2 has 13 false positives over the WHOLE window with 0 unadjudicated, while D3 still costs NOTHING (exact) and argument tokens still typed MainText are 3/327 against 46 with the rule off; NOT adopted
../ocr-venv/bin/python witness/score_region_gap_tokens.py # R2.2e: exits 1 -> E3 is 0/43 -- the swallowed rows are OVERSHOOT, not merges, so the region-gap cut is REFUTED and NOT adopted, though it takes every merged token to zero at no cost on the region gold (E2 exact) and GOLD-ARGUMENT D1 holds at 52/81
../ocr-venv/bin/python witness/score_block_span.py # R2.2e-b: exits 1 -> qualifying a token that spans the measure lifts the region gold to acc 0.9174 and MainText 0.9125 and takes the consumer 0/43 -> 23/43, but MarginNote falls 0.8947 -> 0.8421 on 1 entry whose row the repair fixed, so it is REFUTED and NOT adopted
../ocr-venv/bin/python witness/score_r4_segment.py # R2.2f: exits 1 -> the consumer holds at 23/43 and per-segment R4 demotes 35 rows with the shipped gold EXACTLY unmoved, but G1 fails -- leaf 412 r2's body segment is FULL yet overshoots the modal edge by 45px against a 33px tolerance, so the row takes the fallback and the note keeps MainText: R2.2g is R2.2f's PREREQUISITE, not the reverse, and R4_PER_SEGMENT stays False
../ocr-venv/bin/python witness/score_flush_reach.py # R2.2g: exits 1 -> one-sided flushness takes the consumer 23/43 -> 37/43 and H4 RESOLVES THE CYCLE (all three flags on: the entry returns to MarginNote, MN recovers 0.8421 -> 0.8947, RH holds 1.0000, MT 0.8375 -> 0.9000), but H1's bar is all 43 and 6 rows survive as a FOURTH cause, so FLUSH_MODE stays "both" and NEITHER R2.2g NOR R2.2f is adopted
../ocr-venv/bin/python witness/score_edge_chain.py # R2.2h: exits 1 -> the full chain reaches 37/43 on the consumer with the region gold at acc 0.9174 RH 1.0000 MN 0.8947 MT 0.9000 and D1 57/81, and J2-J6 all pass, but J1's bar is all 43 and the estimator fix does NOT move it -- the 6 survivors are R2.2i (tilted lines cut into two rows), so all four flags stay OFF and the chain is NOT adopted
../ocr-venv/bin/python witness/score_band_anchor.py     # R2.2b: exits 1 -> the anchored band passes A2 (gold containment 121/121, RH 20/20) and A3, but FAILS A1 on 18/20 leaves -- it misses the first body line on both CHAPTER-OPENING leaves; NOT adopted
../ocr-venv/bin/python witness/test_band_agreement.py   # R2.2c: exits 1 -> the reader's band contains 0/20 RunningHead and 2/19 MarginNote gold entries, and BOTH scorers cut a different band; the guard's own control passes 121/121
../ocr-venv/bin/python witness/audit_label_sources.py # R14.6a: exits 1 -> of the 3 Marginalia label sources on disk 2/3 are ADMISSIBLE and the third is CIRCULAR and must never be substituted. The janvier corpus gives 3754 verse-anchored side-note objects over 53 books (OT 1609 + NT 1582, CC0, this edition), corroborated by 165 marginal_notes in the odr-com apparatus scrape that was already on disk; scan_marginal is the incumbent region typer's own output. 🔴 ANNOTATION IS THE ONE BLOCKED CLASS, added as a row on 2026-08-27b by R14.10c and reported 🟠 PARTIAL: 246 chapter-anchored annotation blocks are on disk carrying their printed ANNOTATIONS. Chap. N. heads, but 232 are NEW TESTAMENT and the Old Testament holds only 14 chapters across 2 books, Genesis and Exodus -- NUMBERS HAS NONE, and Numbers is the volume every region figure in this project is measured on. PARTIAL blocks on the same footing as ABSENT, because a source that does not reach the volume the class is needed in leaves the class unlabellable there and counting it as covered would be laundering. ⚠️ AND FINDING THAT ROW REQUIRED THIS AUDIT TO STOP REPEATING ITS OWN DOCUMENTED MISTAKE: it had answered the Annotation question from apparatus_blocks[kind], where the count is 0 because all 1334 of those blocks are kind='argument', while the odr-com scrape IN THE SAME DOCUMENTS carries a top-level `annotations` field that _odrcom_notes reads straight past. That would have been a SECOND false absence -- and this audit's OWN FIRST RUN reported a false absence by searching one directory, so the lesson was already written at the foot of its own output: a bounded search returns 'not found' in the same shape an exhaustive one does. The bound was a DIRECTORY the first time and a FIELD NAME this time. Exit 1 stands while the circular source sits unguarded beside the real one and while any class is blocked
../ocr-venv/bin/python witness/score_surya_layout.py # R14.0: exits 1 -> the first layout score ever computed on this corpus. Surya FastLayoutPredictor against the 121-entry head-band gold over leaves 400-419, page-fraction addressed, 121 bound and 0 orphans: overall 100/121, of which MarginNote is 0 of 19 -- the class this edition is built around. RunningHead is exact at 20 of 20 and MainText at 80 of 80. It emitted no Footnote box at all, so the charitable label map was identical to the strict one and the marginalia ceiling is not a mapping artefact. The MarginNote entries bind to TIGHT boxes (median 0.0039 of page area), so the detector LOCALISES the notes and only lacks a NAME for them -- a labelling failure on a working detector, repairable by class-inventory fine-tune. The MainText figure is CONTAINMENT in a half-page block (median bound box 0.5555 of the page), not a boundary result, and Gate 10b is not measured here. Exit 1 is the rung-0 admissibility verdict, not a crash
../ocr-venv/bin/python witness/score_region_gap_pops.py # R2.2o.1: exits 1 -> 986/12592 intra-row gaps are labelled from the GOLD (top 3 rows only), and the two populations OVERLAP on 0.875 to 1.525 pitches -- the narrowest true region gap is NARROWER than the widest true word space, so the best possible single threshold still misclassifies and threshold-retuning is REFUTED as the repair. Both MN-against-MT boundaries are on leaf 412, the leaf region_head already records as the one where the marginal column abuts the measure, and the narrower of them sits BELOW the cut so it is never cut at all. Exit 1 is the FINDING, not a failure: it is the measurement that fired R2.2o's approach-level ALERT and re-scoped R2.2 to a clamp
../ocr-venv/bin/python witness/audit_gate_register.py # R15.1/R15.3: exits 1 -> 12/25 canonical §7.8 gate rows name the Roadmap step that discharges them and 13 read NOT YET PLANNED, with 0 HARD defects. Its FIRST live run found two, both fixed rather than tolerated: `Gate 0e` and `Gate 0f` were CITED throughout the Roadmap and had NO ROW in the register declared canonical -- a fourth instance of R15's own defect, inside the table R15 exists to bind -- and the crosswalk wrote one row id as `row 3` where every other reads `10a`, so the archaic-census clause resolved to nothing. Rows 0e and 0f are now in the table. --selftest replays the PRE-FIX documents and reproduces all three of the 2026-08-25 findings, which is the only way to show an audit written AFTER a hand-fix would have caught it. Exit 1 is the healthy state while any row is unplanned; R15 may not close a row by deleting it
../ocr-venv/bin/python witness/score_skew_frame.py # R14.14: exits 1 -> S3 corr between skew and head-line straddles +0.051, WHICH IS THE REFUTATION OF THIS STEP'S OWN PREMISE AND IS THE HEADLINE RESULT. The step was filed because a HORIZONTAL head line cut through 41 boxes and the cutting was attributed to the agent having no angle. Both halves were tested by building it. The tilt is REAL and per-leaf, -0.901 to +1.636 degrees, and it is not the fount record's slant_mode which reads 0.00 everywhere. But the tilt DOES NOT CAUSE THE CUTTING: rotating the frame moved the count 41 to 50, the wrong way, and nearly-flat leaves are straddled 2.50 times on average against 2.44 for tilted ones, which is indistinguishable. The head line is the extreme edge of the BODY BLOCK and page furniture sits at overlapping heights, so ANY scalar boundary between them is straddled whatever its angle -- those 41 boxes need ownership of INK and belong to R14.12, the lamination, not to trigonometry. The original acceptance clause is RETIRED as unreachable rather than reinterpreted into something this step happens to satisfy. S1 passes with 20 of 20 leaves measured and varying, and S2 passes with 0/160 labels moved so the rotation is LABEL-NEUTRAL -- which is evidence it breaks nothing, never evidence it helps -- while S4's withheld-record negative has 0 of 20 leaves claiming an angle without the record. 🔴 S2 ITSELF WAS THE WRONG INSTRUMENT UNTIL R14.11 EXPOSED IT AND IT HAS BEEN REPLACED. It used to compare the agent against the literal 115/121 frozen on 2026-08-28, which does not test whether the ROTATION moves a label; it tests whether the label vector still equals a number written down on a particular day. So when R14.11 retired CENTRED_LO/HI and GOLD-HEADBAND rose 115/121 to 117/121, S2 reported that the rotation had broken neutrality -- a FALSE FAIL attributing another step's result to this one. S2 now labels the window twice in ONE run, with the skew record present and with it withheld, and requires the two label vectors to be identical: 160 boxes compared, 0 moved. That form needs no frozen number, is immune to every unrelated improvement, and is STRICTER than what it replaced, since it compares every box rather than only the 121 the gold binds to. ⚠️ Same shape as this step's own S3: a criterion can look rigorous and still not test the thing it names. ⚠️ S5 IS THE DEFECT THE TILT ACTUALLY CAUSES AND IT REMAINS UNMEASURED BY ANY GOLD: an axis-aligned box around a tilted line is taller than its type by width times tan of the angle, which is 17 percent of a median box height on leaf 409 and 16 percent on 419, and that is a BOUNDARY error under Gate 9.3 while every gold this project holds scores LABELS. Exit 1 stands
../ocr-venv/bin/python witness/audit_fixed_measures.py # R14.11: exits 1 -> fixed measures that DECIDE 3/12. Sweeps EVERY fixed number in the adaptive visual agent and reports the band over which the FULL label vector -- every box on every leaf -- is unchanged. A constant with wide slack is a guard; a constant whose invariant band is narrower than a quarter of its own value is DECIDING and is a threshold wearing a cue's clothes. 🔴 THE AGENT'S OWN DOCSTRING CLAIMS `nothing here is a corpus-fitted number` AND THAT CLAIM IS NOW MEASURED AND FALSE: the first run measured OUTSIDE_FRAC holding over 0.04x its value, THIN_MARGIN 0.06x, FOOT_CATCHWORD_REL 0.03x, PN_MAX_AREA 0.25x, and CENTRED_LO/HI -- the band separating a RUNNING HEAD from a head-band NOTE, the single most load-bearing cue in the head band -- at ZERO SLACK. 🟢 TWO OF THE FIVE ARE NOW GONE AND ONLY ONE OF THEM WAS TOUCHED. CENTRED_LO/HI was RETIRED rather than re-derived, replaced by the parameter-free predicate that the measure's centre-line falls inside the box; and THIN_MARGIN then moved 0.06x DECIDING to 2.25x GUARD WITHOUT BEING EDITED, because its only remaining deciding use had been that same head-band boundary. Nothing in the agent said those two numbers were coupled, and only re-running the sweep showed it. The replacement abstention tolerance CENTRED_ABSTAIN measures 9.12x, the widest guard in the agent, and ⚠️ it is UNEXERCISED on this window and therefore UNTESTED, which the constant's own comment states. Three still DECIDE -- OUTSIDE_FRAC 0.04x, FOOT_CATCHWORD_REL 0.03x and PN_MAX_AREA 0.25x, the last sitting exactly ON the definition's edge -- so the step's acceptance of ZERO deciding is NOT met. Masterplan §3.0 permits a fitted constant to INITIALISE or CLAMP and forbids it to DECIDE, and that permission had been asserted in comments throughout the agent and never tested. ⚠️ Four literals were NAMED to make this audit possible at all -- COLUMN_OVERLAP, CENTRED_LO/HI, HEADING_LO/HI and FOOT_CATCHWORD_REL were spelled inline inside the cues that used them, so no instrument could sweep them and no reader could find them: an unnamed literal cannot be audited. ⚠️ SLACK IS NOT A CERTIFICATE -- a wide empty band on twenty leaves of one witness is evidence about this window and nothing more. Exit 1 stands while any constant DECIDES
../ocr-venv/bin/python witness/score_pagenumber_agent.py # R14.10b: exits 1 -> the PageNumber class is ADOPTED and the step REMAINS OPEN, which is the honest pair. B1 names PN on 14/20 leaves against a floor of 12, B2 has 0 false positives, B3 holds every GOLD-HEADBAND number EXACTLY at 115/121 with MarginNote 16/19, and B4's withheld-record negative emits 0 with all 20 candidates naming the absence. B5 FAILS AT 1 of 20 and is not relaxed: leaf 403's crop reads 37T, so one misread sort turns a numeral into a lettered reading and the pre-registered rule routes it to the note logic. Widening the predicate to predominantly-digits would be a rule edited after seeing which box it fails on. 🔴 THE DEFECT THIS CLASS CLOSED WAS 20 OF 20 AND ENTIRELY SILENT: every page number in the window was misfiled, 15 as MarginNote and 4 as MainText, and NO GOLD ENTRY BINDS TO ANY OF THEM -- so MarginNote recall, the headline bar, could not fall when the agent invented notes, and MainText is containment so the other 4 scored as CORRECT. The agent's MarginNote PRECISION had never been measured by any instrument in this project. ⚠️ THE ROW'S POSITIONAL FORMULATION IS REFUTED -- the box CENTRE overlaps on both sides -- BUT THIS STEP OVER-GENERALISED THAT TO ALL OF POSITION AND 2026-08-27g REFUTES THE GENERALISATION: over all 65 head-band boxes WIDTH separates the populations cleanly at 0.0442-0.0546 against 0.0757-0.3028, an empty band 2.0x the page-number spread, and so do area and aspect. GEOMETRY ALONE WOULD SCORE 20/20 WITH 0 FALSE POSITIVES ON THIS WINDOW WHERE THE READ SCORES 14/20 PLUS 5 ABSTENTIONS, so the confirming read MEASURABLY DEGRADES the result here and B2's zero is not evidence that it discriminates. A page number is distinguished from a side-note by being a SHORT SQUAT OBJECT, not by where it sits. The read still earns a place as the CHECK on a margin known to close -- width runs ~0.0165 of the page per digit, so a four-digit number at ~0.059-0.073 nearly meets the note floor of 0.0757 later in the volume -- but as a guard, not as the decider. ⚠️ AND THIS STEP PRODUCED A FALSE ABSENCE OF ITS OWN, corrected rather than quietly fixed: it first reported 4 detector gaps, which were its own candidate test bounded by the head band, and GOLD-FOREEDGE caught it. A bounded search returns not-found in exactly the shape an exhaustive one does
../ocr-venv/bin/python witness/score_foreedge.py # R14.8/R14.10a: exits 1 -> the agent scores 40/42 below the head band, up from 38/42 as the PAGENUMBER class was adopted and from 34/42 when the ARGUMENT class was, and the PRE-REGISTERED prediction HELD: fore-edge MarginNote recall is 18 of 18 exact against 16 of 19 on the head band, because a fore-edge note CLEARS the measure where a head-band note STRADDLES its edge. So the besideness cue GENERALISES and every MarginNote figure ever quoted on this corpus was measured on the cue's WORST case. MainText is 9 of 9, heading 6 of 6, and Argument 4 of 4 since R14.10a. ⚠️ Exit 1 REMAINS THE HEALTHY STATE and is still the CLASS-INVENTORY finding, not a cue failure: the residual errors are classes the page prints and the agent has NO NAME for -- Annotation x1 (R14.10c) -- since R14.10b the agent NAMES the page number and scores PageNumber 2 of 2 here, which is this project's cleanest out-of-sample check to date: both entries sit on leaves 401 and 417, the very leaves R14.10b's own probe had reported as carrying NO page number, so a gold built for a different step caught a FALSE ABSENCE that step had produced -- plus one gathering signature read as a catchword on the foot band's centred/outer boundary. A class with no name is not skipped, it is MISFILED into the nearest name the agent does have. ⚠️ And no cue for those classes may be fitted against THIS gold: R14.10a was validated on the six leaves DISJOINT from it and this gold's four Argument entries were held out as the out-of-sample check, which is the only reason the 4 of 4 above means anything. ⚠️ `AGENT_CLASSES` is now IMPORTED from the agent rather than restated here, because the restated copy went stale the instant a class was added -- the first run after adoption scored Argument at 4 of 4 and printed NO NAME IN THE AGENT about the same four boxes
../ocr-venv/bin/python witness/audit_prefix_rule.py     # R2.1h: exits 1 -> reader still returns 2 whole-line tokens of 20 leaves (17 words, 1 abstain); the >=4-char rule's length-dependence is real and STAYS
../ocr-venv/bin/python witness/audit_setting_points.py  # R8.4b: exits 1 -> foot criteria proved at 1 separated point of the 3 §0.3 requires
./.venv/bin/python core/tests/fixtures/gold/audit_scratch_data_paths.py  # R11.2a: exits 1 -> 33 gitignored DATA refs across 23 tracked files (was 71/38); the number must FALL
```

A guard exiting 0 and an audit exiting 1 are both healthy states. An audit that exits 0 before its remedy
is done would mean the audit stopped looking, not that the corpus got better.

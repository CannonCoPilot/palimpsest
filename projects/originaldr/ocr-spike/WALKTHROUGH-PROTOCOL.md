# THE GENESIS WALKTHROUGH — standing order, 2026-08-01 (Sir)

> **Every chapter of Genesis under 100% gets at least one — preferably two — FULL chapter-workflow efforts.**
> R2, R3 and any other approach may run in the background and are encouraged. **They do not substitute for the
> per-chapter walkthrough and cannot mark a chapter worked.**

**READ THIS FIRST IF YOU ARE RESUMING.** State lives in `.campaign/walkthrough.json` and is enforced by
`walkthrough.py`, not by memory or by anything written in prose. Start every session with:

```
../ocr-venv/bin/python walkthrough.py --status      # where the walkthrough actually is
../ocr-venv/bin/python walkthrough.py --next        # the chapter to work now
```

`--next` is **worst-first within the least-walked tier**: no chapter gets a second pass while any chapter
still lacks a first. Pure worst-first would pour every pass into the bottom of the board and leave the 90%
band untouched, which is not what completeness means.

---

## WHAT ONE PASS IS — all seven steps, in order, with artifacts

A pass is not "I read the matrix and formed a view". `walkthrough.py --record` refuses a pass that cannot name
the signals it triaged on and the diagnostics it ran.

**0. `--start N`** — captures the before-rate from the matrix. Do this BEFORE touching anything; a pass whose
before-rate is typed in afterwards cannot be shown to have changed anything.

**1. MEASURE** — `chapter_campaign.py --chapters N --phase measure`. Read `n_pass`, `src_rates`, `ref_gaps`,
`n_all_fail`, and the open list. Quote the ACHIEVABLE count beside the rate, always.

**2. TRIAGE BY SIGNAL, NOT BY SCORE** — `CHAPTER-WORKFLOW.md` §3 router, in order:

| # | signal | tool |
|---|---|---|
| 1 | `ref_gaps` non-empty | **UNREACHABLE by OCR.** Document, raise ACQUISITION, keep the cell OPEN. Still walk the chapter. |
| 2 | cells with NO TEXT | `leaf_diag.py`, `chapter_open_probe.py` |
| 3 | one reference's mean far below the other three | `ref_alignment_audit.py` |
| 4 | one source far below its own median here | `leaf_diag.py`, **then `left_strip_probe.py`** |
| 5 | a source low everywhere | `s6_causes.py --source SX --examples 3` |
| 6 | all four sources fail the same verse | the SPLIT TEST — one reference binding while the other three pass is a REFERENCE defect |

**A chapter's score tells you how much is wrong, never what is wrong.** Every large win in this campaign came
from a signal.

**3. RUN THE DIAGNOSTICS THE SIGNAL DEMANDS.** Read their examples, not their summary tables — the S6 cause
classifier returned the exactly-opposite answer in its first version and was entirely convincing.

**4. SCOPE EVERY CANDIDATE FIX BOTH WAYS** — measure it scoped to its defect class AND applied globally.
Adopt per-leaf on a probe's verdict where the population is mixed; change a DEFAULT only when the population
is not.

**5. `faithfulness_audit.py` ON ANYTHING THAT EDITS TEXT, INCLUDING YOUR OWN FIXES.** Then read what it
changed. Then diff the actual verse text before/after and read every ADDED and REMOVED token. `--record`
refuses `--changed-text` without `--audited`.

**6. RE-MEASURE ALL 50.** Knock-on gains are the point. Report regressions explicitly; never net them away.

**7. `--record N`** with signals, diagnostics, and either `--rule` or `--alert`.

---

## THE THREE RULES THAT STOP THIS BECOMING THEATRE

**A. A PASS ENDS IN A RULE OR AN ALERT — never in "nothing to do here".** `CHAPTER-WORKFLOW.md` B5: "stop
when hand-work stops producing rules" is a silent-degradation trap. No rule found is an **ALERT that the
APPROACH needs redesign**, the chapter stays OPEN, and it still blocks the deliverable.

**B. "IT IS RECOGNIZER DAMAGE" IS A CONCLUSION THAT HAS BEEN WRONG TWICE, AT THE SAME SITE.** ch41's
right-margin audit concluded RECOGNIZER *by elimination* and quoted `Seuon cares` and `blaſled vith adulon` as
proof of misread glyphs. Those were tokens the LEFT bound was dropping — the one bound it never varied — and
fixing it was worth +19 there and **+57 book-wide**. An elimination that varies one thing can only ever return
the cause it did not test. **Before concluding "recognizer", list what you did NOT vary.**

**C. WHEN A TABLE VARIES ON ONE AXIS AND IS CONSTANT ON ANOTHER, THE CONSTANT AXIS WAS NEVER TESTED.** It was
not measured and found correct. Ten `PAGE_OVERRIDE` entries carried right bounds tuned to four decimals beside
an identical default left bound, and that constant was the biggest single lever on the board.

---

## WHAT COUNTS AS THE SECOND PASS

The second walk must **differ from the first** — `--record` refuses a repeat that ran the same diagnostics on
the same signals and moved nothing. The second pass is worth having because it happens AFTER other chapters'
systemic fixes have landed, so it should begin by re-measuring and asking what the accumulated rules changed
here. If the first pass ended in an ALERT, the second must try a **different approach**, not the same one
harder.

---

## BACKGROUND WORK IS ENCOURAGED AND IS NOT A SUBSTITUTE

Start R3/R2 passes first — they are unattended and serialized behind `.campaign/r3-runner.lock` (one 17GB
olmOCR at a time; `r3-runner-v3.sh` takes an explicit chapter list). Then do the attention-bound walk while
they run. Do not measure a chapter that a pass is actively writing: read the ledger, not a PID.

> ⚠️ **`R2`/`R3` here are the RECOGNITION RUNGS** — the fine-tuned recognizer and the vision-LLM — **not**
> the roadmap's `R2`/`R3`, which are Gate 0b stage 2 (collation) and Gate 0c (the leaf map). Both usages are
> live in this directory. A background "R2 pass" in this protocol never advances the roadmap's R2.

---

## STANDING ITEMS THAT ARE NOT CHAPTER WORK

* **ch8/8:14** — needs a POLICY decision from Sir, open since 2026-07-31 through four sessions. The plate is
  read correctly; no reading of those pixels satisfies both a 1609 and a 1635 reference.
* **ch23 / `odr_com` gen 23:20** — ACQUISITION, not OCR.
* **B7 rung 2 (a 1635 reference)** — sized 2026-08-01 at **~22 board cells**, plus ~430 above-bar cells whose
  headroom it would unmask. A validity build, not a yield build.
* **The report bridge** — no campaign fix reaches anything below the live board (`qc_audit.py` carries its own
  layout model). Unbuilt.

# OriginalDR — Development Log

What was actually built, measured, and decided, in order, with the evidence. The plan states what must be
true and the roadmap states what will be built; **this file records what happened**, including the things
that turned out wrong.

A retraction here is not an embarrassment to be minimised — it is the most useful kind of entry, because
every one of them marks a place where a plausible reading survived until something measured it. They are
kept in full, with what produced them.

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

# FABLE COLD READ, ROUND 3 — 10 more tough leaves (2026-09-04)

**Sample.** `random.seed(20260907)`, 10 of the 163 remaining leaves in `tough_leaves.txt`. All in
the 208-plate set. Regions in `cold-read-10.json` — 117 regions. Same rule: image only, nothing
else consulted first. Scored afterwards by `compare_gold.py cold-read-10.json`.

**The six moves held again.** Nothing in this round needed a seventh. What this round added is a
layer BELOW the page: things in the image that are not the page at all.

---

## NEW IN ROUND 3

**1. Scan-level phenomena — four kinds, none of them page content.**
| code | what | leaf |
|---|---|---|
| `XP` | off-page pixels: black scanner surround, book edge, gutter shadow | 0035 (the whole frame) |
| `AP` | adjacent-page bleed: the FACING leaf's marginal ink visible at the edge | 0035, left edge |
| `ST` | show-through: mirror-image ghost of the verso's running head | 0275, top |
| `CT` | crop-truncation: the last line runs off the scan; the catchword is not on the image | 0119 |

A reader sees all four instantly and discounts them. A detector that has no name for them will
box the bleed as a marginal note (0035), OCR the ghost (0275), and search a truncated leaf for a
catchword that is not there (0119). **These belong in move 1**, before orientation: *what part of
this image is the leaf?*

**2. The NT chapter running-head has a rule.** Across all four NT leaves now read (0562, 0564
verso; 0119, 0777 recto): `CHA. n.` sits at the **gutter** side and the page number at the
**fore-edge**. Verso → `CR` right; recto → `CR` left. That is a per-setting layout fact a director
can carry as an expectation.

**3. The gloss-key column can be on either side.** 0022/0024 had `GK` on the left with `IG` glosses
set left. 0035 has `GK` on the RIGHT with `IG` glosses right-indented into the margin. Same
structure, mirrored; a position rule for it would need the recto/verso decision first.

**4. Signatures are not always at the foot.** 0777 sets `Bbbbb` directly under the last text line at
y≈0.47, then a tailpiece, then blank. "Foot band" is the wrong frame for it; "immediately below
the last line of the measure" is the right one.

**5. Two more end-markers and a two-line annotation header.** `THE END OF THE FIRST TOME.` (1136)
joins `FINIS.` as `FN`. `ANNOTATIONS / CHAP. XXII.` (0777) is the annotation header set over two
lines.

**6. A plain leaf exists.** 0346 is Numbers with no apparatus at all — six regions. It is the
control: the simplest page kind, and the live pipeline still misses the verse numbers and the
catchword on it.

---

## RESULT vs THE LIVE PIPELINE, scripted

117 regions: **48 agree · 46 disagree · 23 no box.** Worst: 0035 (1 of 21 — the scan surround and
the bleed produce boxes everywhere; the live frame is nonsense on it). Best: 0119 (8 of 17), 1130
(7 of 12), 0007 (7 of 12), 0275 (7 of 13).

Mislabelled, by my class: VN 6 · BT 5 · DC 4 · MN 4 · OR 3 · AN 3 · CH 3 · PN 3 · CR 2 · RL 2 ·
MT 2 · RH 2 · AR 2 · IX 2 · SG 1 · FN 1 · ST 1. Same shape as rounds 1-2.

---

## THE THREE ROUNDS TOGETHER — 35 leaves, 392 regions

| class | regions | on leaves | | class | regions | on leaves |
|---|---|---|---|---|---|---|
| MN | 106 | 30 | | BT | 10 | 9 |
| PN | 32 | 32 | | OR | 9 | 9 |
| RH | 32 | 28 | | IX | 4 | 2 |
| MT | 31 | 21 | | CR | 4 | 4 |
| CW | 26 | 26 | | XP | 4 | 1 |
| VN | 20 | 17 | | IG | 3 | 3 |
| CH | 16 | 14 | | GK | 3 | 3 |
| AR | 16 | 16 | | TB | 3 | 1 |
| DC | 15 | 15 | | HD | 2 | 2 |
| SG | 13 | 13 | | LM | 2 | 2 |
| AN | 13 | 12 | | FN | 2 | 2 |
| RL | 11 | 7 | | MS · AT · CT · AP · ST | 1 each | 1 each |
| ?? | 10 | 9 | | | | |

Thirty classes were needed to describe 35 hand-picked hard leaves without forcing anything. The
inventory the cascade works with has eleven, and its scorer sees four.

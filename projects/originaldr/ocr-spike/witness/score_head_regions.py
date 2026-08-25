"""R2.1g acceptance -- score `region_head` DIRECTLY on region assignment.

⚠️ This is the point of R2.1g. The separator is NOT scored only through the continuity rate it
enables. R2.1f's whole finding was that a joint measure of two readers and a scorer moved for
reasons nobody could attribute; a component measured only through a downstream metric cannot be
debugged when that metric moves. So the primitive gets its own number against
`gold/head_regions_OT1-1609-B_400-419.json`, on the SAME window R2.1d'(A) scored 0.312 on.

TWO NEGATIVE CONTROLS, printed alongside and NOT optional. A region accuracy means nothing on its
own, because the gold set is dominated by MainText: a scorer that labels everything MainText already
gets most of it right. Both controls are reported so the reader can see what the instrument adds
over doing nothing.
  * ALL-MT   -- label every token MainText. The majority-class floor.
  * ROW0-RH  -- label row 0 RunningHead and everything else MainText. The rule a reader would
                write from the observation "row 0 is the running head on 20 of 20 leaves", and the
                one this module has to beat to have earned its complexity.

Exit 0 when the instrument beats both controls on OVERALL accuracy AND reaches the pre-registered
bar on RunningHead recall; exit 1 otherwise. Abstentions and unlabelled tokens are counted and
reported, never dropped (R1.4).
"""

import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(_HERE.parent))

from PIL import Image
import witnesses as W
import collation_read as CR
import region_head as RH

GOLD = _HERE / "gold/head_regions_OT1-1609-B_400-419.json"
TOP_FRAC = 0.35
NROWS = 3

# PRE-REGISTERED, written before the first run of this scorer.
BAR_RH_RECALL = 0.90    # the running head is the region R2's head side is actually confused by
BAR_MN_RECALL = 0.75    # side-notes are the confusion that produced 'Temporal'; lower bar, they vary
# R2.1i. A gold span must overlap the token it binds to by at least this much of ITS OWN width,
# or the binding is refused and reported as an orphan. See `match`.
MIN_BIND_FRAC = 0.50

# ══════════════════════════════════════════════════════════════════════════════
# THE DENOMINATOR BAR -- added 2026-08-22, and NOT pre-registered. Read that clause.
# ══════════════════════════════════════════════════════════════════════════════
# 🔴 WHY. Every bar above this line is a RATE, and a rate is a ratio whose denominator this scorer
# lets a candidate change. That is not hypothetical here. Twice in one run:
#
#   * A seed finder that discarded every short line posted accuracy UP 0.8760 -> 0.9000 and MainText
#     UP 0.8375 -> 0.9178 while scored pairs fell 121 -> 90 with 27 orphans. Three of four numbers
#     improved BY DISCARDING A QUARTER OF THE GOLD. This module's own header already records the
#     same shape -- a broken splitter posting the highest max-overlap accuracy, 0.9479, by orphaning
#     25 -- so the trap was documented here and still caught the next candidate.
#   * The inverse, which is subtler and cost a wrong reading in the other direction: candidate 4's
#     RH recall 0.9231 was summed over 13 entries where the control sums 19. It was not a worse
#     number than the control's 1.0000, it was a DIFFERENT QUANTITY, and comparing them at all was
#     the error. A fix that RESTORES a denominator makes some rates fall while being strictly better.
#
# ⚠️ WHY `test_region_gold_addressing`'s CRITERION B DOES NOT COVER THIS, having been read first:
# that clause requires any change in scored tokens to be FULLY ACCOUNTED FOR by reported drops --
# it polices WHERE entries went, not HOW MANY. Candidate 4 sheds 5 entries and reports every one
# (2 collisions + 3 orphans; 116 + 5 = 121), so its accounting balances exactly and the guard is
# silent while the rates ride a short denominator. That invariant is ENUMERATIVE; this hole is
# QUANTITATIVE. Reported loss is still loss.
#
# ⚠️ NOT PRE-REGISTERED, and it must not be dressed up as if it were. BAR_RH_RECALL and BAR_MN_RECALL
# above were written before this scorer first ran; these two were written after seeing the numbers.
# What keeps that honest is that BOTH ARE TAKEN FROM THE CONTROL AND FROM THIS MODULE'S OWN STATED
# CRITERIA, never from the candidate: the control scores 121 of 121 entries with 0 collisions,
# 0 orphans and 0 ambiguous-collisions, and lines further down already assert "must be 0" and "must
# be {len(entries)} under EVERY splitter". So this bar enforces what the module always claimed and
# never checked -- the signature defect of this project, a correct rule that nothing reads.
FULL_ACCOUNTING = True   # every gold entry must reach the max-overlap sum: pairs == len(entries),
                         # i.e. collisions + orphans + ambiguous-collisions == 0. The CONTROL meets
                         # this exactly, so it is a bar the instrument is known to be able to clear.
BAR_MAX_INK_ORPHANS = 1  # 🔴 NON-REGRESSION, NOT AN ENDORSEMENT. The stated ideal below is 0 and the
                         # control sits at 1, so barring at 0 would fail the control and barring at 1
                         # accepts a known gap. It is set to the control's value to stop the gap
                         # WIDENING, and the gap itself stays OPEN -- see the ink-binding block.


def top_band(leaf_path):
    im = Image.open(str(leaf_path))
    im.draft("RGB", (2800, 3920))
    im = im.convert("RGB")
    w, h = im.size
    crop = im.crop((0, 0, w, int(h * TOP_FRAC)))
    return crop.resize((1400, max(1, int(crop.height * 1400 / w))), Image.LANCZOS)


# ══════════════════════════════════════════════════════════════════════════════
# R2.2j -- A ROW ORDINAL IS NOT AN ADDRESS. DEFAULT "ordinal" (unchanged) until K1-K4 pass.
# ══════════════════════════════════════════════════════════════════════════════
# 🔴 THE DEFECT, found 2026-08-20 while scoping R2.2i. Every binding below filters
# `t["row"] == e["row"]`, and the row ordinal is an index into a list `CR._rows_and_lines` controls.
# R2.2i proposes to change that clusterer, which RENUMBERS EVERY ROW -- and R2.1i already measured
# what that costs one level down: keying by TOKEN ordinal made a splitter change read as a region
# collapse, MN recall 0.8947 -> 0.5263 with nothing about any region having changed.
# ⚠️ The gold has carried a band-independent address since R2.2c (`y0f`/`y1f`, page-height fractions)
# and NO SCORER READS IT. An entry binds to the row whose y-band it overlaps most; an entry
# overlapping none is an ADDRESSING FAILURE, reported separately from the region score -- never
# folded into accuracy, which is the discipline `score_argument_region` already follows.
ROW_ADDRESS = "ink2d"       # ✅ ADOPTED 2026-08-20 | "ordinal" (former) | "yband" (cand. 1)
# ✅ ADOPTED on L1+L3+L4+M1+M2+M3 (`witness/score_row_address.py`, exit 0). The deciding evidence is
# M1: under a PURE RENAMING of rows -- every glyph, token and coordinate untouched -- the `ordinal`
# address collapses to acc 0.4667 with RunningHead and MarginNote recall both 0.0000 and 90 of 121
# entries orphaned, while `ink2d` is bit-for-bit unmoved. Every region number this project has
# recorded was resting on a convention a renaming annihilates, and nothing had tested it because the
# row clusterer had never changed. R2.2i is the change that would have.
# ⚠️ `ink2d` over `yband` is a DECISION, not a tuple order: R2.2i splits a printed line across TWO
# rows and `yband` must still choose ONE, losing the sibling's tokens. See `score_row_address`.
# R2.2j CANDIDATE 2 -- 2-D INK ADDRESSING. Candidate 1 bound by y-band but still made each entry
# choose ONE row, and when the clusterer splits a printed line (R2.2i) the entry's ink lies across
# TWO -- so the denominator still moved with the clusterer and K3 refuted it. ⇒ A ROW IS NOT AN
# ADDRESS EITHER. R2.1i retired the token ordinal, candidate 1 retired the row ordinal, and this
# retires the row itself: a token is on an entry's line iff their INK OVERLAPS VERTICALLY, by at
# least this fraction of the shorter of the two. Ink is what no clusterer or splitter can move.
INK_Y_FRAC = 0.50

# R2.2j M1-M3 -- TEST HOOK, off in every normal run. A pure RENAMING of rows: every token's `row`
# field and the row-band map are permuted together, and nothing else is touched. An ADDRESS must be
# exactly invariant under this; the row ordinal must break completely. It replaces the L2
# perturbation, which changed the ink's grouping and therefore the OBJECTS being labelled -- a
# criterion this project's own docstring (§ R2.1j below) records as unachievable and twice wrongly
# pre-registered before I did it a third time.
PERMUTE_ROWS = False


def _permute(toks, bands):
    """-> (toks, bands, proof). Rename row j -> (j + 1) % n, together, changing nothing else."""
    n = max([t["row"] for t in toks] + list(bands)) + 1 if (toks or bands) else 0
    before = sorted((t["l"], t["r"], t.get("y0"), t.get("y1")) for t in toks)
    for t in toks:
        t["row"] = (t["row"] + 1) % n
    bands = {(j + 1) % n: v for j, v in bands.items()}
    after = sorted((t["l"], t["r"], t.get("y0"), t.get("y1")) for t in toks)
    return toks, bands, (len(before) == len(after) and before == after)


def _row_bands(band, p):
    """-> {row ordinal: (y0, y1)} in BAND pixels, from the same clustering the tokens came from."""
    rows = CR._rows_and_lines(CR.glyph_boxes(band, 0, p), p)
    return {j: (min(g[0] for g in r), max(g[1] for g in r)) for j, r in enumerate(rows)}


def _entry_band(e, band_h):
    """-> (y0, y1) of a gold entry in BAND pixels.

    `y0f`/`y1f` are fractions of PAGE height; this band is the top `TOP_FRAC` of the page resized to
    width 1400, so a page fraction maps to `yf * band_h / TOP_FRAC` without needing the page size --
    the band's own height already carries the scale.
    """
    k = band_h / TOP_FRAC
    return (e["y0f"] * k, e["y1f"] * k)


def _on_line(band_h, bands):
    """-> callable(entry, token) -> bool. THE ADDRESS, in whichever of the three forms is selected.

    One predicate for all three bindings below. They filtered by `t["row"] == e["row"]` in three
    separate places, and three copies of one rule is how a splitter and a scorer drift apart -- the
    defect this project has now recorded twelve times.
    """
    def row_of(e):
        want = _entry_band(e, band_h)
        best, bov = None, 0.0
        for j, yb in bands.items():
            ov = _overlap(want, yb)
            if ov > bov:
                best, bov = j, ov
        return best

    cache = {}

    def of(e, t):
        if ROW_ADDRESS == "ordinal" or "y0f" not in e:
            return t["row"] == e["row"]
        if ROW_ADDRESS == "yband":
            if id(e) not in cache:
                cache[id(e)] = row_of(e)
            return cache[id(e)] is not None and t["row"] == cache[id(e)]
        # "ink2d" -- vertical INK overlap, the row never consulted
        ey0, ey1 = _entry_band(e, band_h)
        ty0, ty1 = t.get("y0", ey0), t.get("y1", ey1)
        ov = _overlap((ey0, ey1), (ty0, ty1))
        return ov >= INK_Y_FRAC * max(1.0, min(ey1 - ey0, ty1 - ty0))

    of.row_of = row_of
    return of


def _overlap(a, b):
    return max(0.0, min(a[1], b[1]) - max(a[0], b[0]))


def match(entries, toks, on_line=None):
    """R2.1i -- bind each gold entry to the token it OVERLAPS MOST, per row.

    ⚠️ Replaces indexing by token ordinal. An ordinal is an index into a list whose length depends
    on the splitter, so it is not an address: changing the splitter renumbered every key and the
    score collapsed with no region having changed. Overlap degrades gracefully in both directions --
    a token that SPLITS leaves one part unlabelled, and two entries landing in one MERGED token
    collide. Both are REPORTED. Silently scoring a collision would let a splitter change quietly
    delete a label and call the result an improvement.
    """
    bound, collisions, orphans = [], [], []
    claimed = {}
    on_line = on_line or (lambda e, t: t["row"] == e["row"])          # R2.2j
    for e in entries:
        cands = [t for t in toks if on_line(e, t)]
        best, bov = None, 0.0
        for t in cands:
            ov = _overlap((e["l"], e["r"]), (t["l"], t["r"]))
            if ov > bov:
                best, bov = t, ov
        # ⚠️ A BINDING MUST BE SUBSTANTIAL, not merely non-zero. This is the clause v1 lacked
        # entirely: it bound by ordinal and never checked that the token it landed on had anything
        # to do with the label. A label read off 'NVMERI' was compared against a token reading
        # 'deuoured Ar of the Moabites' and the disagreement was scored as a region error.
        # Below the threshold the splitter has re-cut the token past recognition, and the entry is
        # an ORPHAN -- reported and unscored, never bound to whatever happens to be nearest.
        if best is None or bov < MIN_BIND_FRAC * max(1.0, e["r"] - e["l"]):
            orphans.append(e)
            continue
        tid = (best["row"], best["tok"])
        if tid in claimed:
            collisions.append((e, claimed[tid]))
            continue
        claimed[tid] = e
        bound.append((e, best))
    return bound, collisions, orphans


# ══════════════════════════════════════════════════════════════════════════════
# R2.1j -- CONTAINMENT binding, because a gold ENTRY may be coarser than a TOKEN
# ══════════════════════════════════════════════════════════════════════════════
# ⚠️ MEASURED, and it is the reason this exists. 43 of the 121 gold entries (35.5%) carry more than
# one word, because they were hand-labelled while the splitter still blobbed -- entries like
# 'deuoured Ar of the Moabites, and the inhabitantes of the' are line-length. `match` binds an entry
# to the token it overlaps MOST and requires that overlap to reach MIN_BIND_FRAC OF THE GOLD SPAN.
# That clause is right for one-entry-to-one-token, and it is unsatisfiable the moment the splitter
# gets FINER THAN THE LABELLER WAS: no single word can cover half a twelve-word span. Under R2.1h's
# recogniser splitter 31 of 121 entries went ORPHAN for exactly this reason and nothing about any
# region had changed -- the same shape of defect as R2.1i's ordinal keying, one level up.
#
# THE FIX IS NOT A LOWER MIN_BIND_FRAC. Lowering it would re-admit the failure the clause was written
# to catch (a label binding to a token it has nothing to do with) and would still pick ONE token to
# carry a label the entry asserts over several. The fix is that A REGION LABEL IS A PROPERTY OF A
# REGION, NOT OF A TOKEN: an entry spanning N words asserts that all ink in that span is that region.
# So every token whose CENTRE lies inside the gold span takes the entry's label, and each such token
# is one scored observation. This reduces to `match` when an entry covers one token, and unlike
# max-overlap it does not depend on token size -- which is the invariance R2.1i went looking for and
# could not get while one entry had to choose one token.
#
# PRE-REGISTERED, written before this was first run:
#   * ACCOUNTING  -- every gold entry must bind at least one token under EVERY splitter tested.
#                    An entry binding none is reported as an orphan and the criterion FAILS.
#   * The region ACCURACY under different splitters is MODELLING information and is NOT a
#     pass/fail criterion. R2.1i established why: the splitter is an INPUT to the region rules
#     (R5 reads a token's centre, `block_measure` reads the justified edges off token edges), so a
#     criterion demanding an unchanged score is unachievable and was twice wrongly pre-registered.
#
# 🔴 THAT PRE-REGISTERED CRITERION FAILED, MEASURED, AND THE FAILURE IS KEPT HERE RATHER THAN THE
# CRITERION BEING RELAXED. Orphans by splitter: baseline 0 · R2.1h-quantile 6 · coarse x1.6 33 ·
# fine x0.4 0 · recogniser 4. Containment breaks in the direction opposite to max-overlap: MERGE two
# tokens and the merged token's CENTRE leaves a small gold span, so the entry binds nothing. One rule
# fails as tokens get finer, the other as they get coarser, and BOTH let the DENOMINATOR move with
# the splitter -- which is the whole reason splitters could not be compared.
#
# ⚠️ AND THE SAME MEASUREMENT INDICTS THE MAX-OVERLAP NUMBERS ABOVE. `fine x0.4` -- a deliberately
# broken splitter -- posts the HIGHEST max-overlap accuracy on this gold, 0.9479, by orphaning 25
# entries: the entries it cannot bind are the hard ones, so discarding them raises the score. R2.1i's
# reported "0.9474 under the quantile splitter, 26 withheld" must therefore be read as PART
# SELECTION, not as improvement alone. A binding rule that drops entries cannot rank splitters.
#
# ✅ WHAT SURVIVES BOTH FAILURES -- bind by INK. An entry's prediction is the label holding the most
# OVERLAPPING INK, so every entry with any ink under it binds, at any token size, and the denominator
# is 121 for every splitter. Merging still costs: a coarse token straddling two differently-labelled
# entries binds to both and is wrong for one. Shattering still costs, and is separately visible as
# PURITY -- the ink fraction of an entry carrying its winning label -- so a splitter that dissolves
# an entry into disagreeing pieces cannot hide inside a majority vote.
# PRE-REGISTERED for the ink rule, before it was run:
#   * ACCOUNTING -- scored entries == 121 under EVERY splitter, orphans 0. (An orphan is now only
#     possible when a row yields NO tokens at all, which is a reportable abstention, not a binding.)
#   * accuracy and purity are MODELLING information, reported, never a pass/fail on the splitter.

def contain(entries, toks, on_line=None):
    """-> (list of (gold_label, predicted_label, entry, token), orphans). See the block above."""
    obs, orphans = [], []
    on_line = on_line or (lambda e, t: t["row"] == e["row"])          # R2.2j
    for e in entries:
        hit = [t for t in toks
               if on_line(e, t) and e["l"] <= (t["l"] + t["r"]) / 2.0 <= e["r"]]
        if not hit:
            orphans.append(e)
            continue
        for t in hit:
            # `.get` because AMBIGUOUS entries carry no label -- they are run through this same
            # function to EXCLUDE the tokens they cover, and must address them the same way.
            obs.append((e.get("label"), t["label"], e, t))
    return obs, orphans


def ink_bind(entries, toks, exclude=(), on_line=None):
    """-> (list of (gold_label, predicted_label, purity, entry), orphans). See the block above.

    An entry's prediction is the label carrying the most OVERLAPPING INK; `purity` is that label's
    share of the entry's bound ink. `exclude` holds token ids covered by an ambiguous entry.
    """
    ex = set(exclude)
    obs, orphans = [], []
    on_line = on_line or (lambda e, t: t["row"] == e["row"])          # R2.2j
    for e in entries:
        w = {}
        for t in toks:
            if not on_line(e, t) or id(t) in ex:
                continue
            ov = _overlap((e["l"], e["r"]), (t["l"], t["r"]))
            if ov > 0:
                w[t["label"]] = w.get(t["label"], 0.0) + ov
        if not w:
            orphans.append(e)
            continue
        tot = sum(w.values())
        best = max(w, key=lambda k: w[k])
        obs.append((e.get("label"), best, w[best] / tot, e))
    return obs, orphans


def recall(pairs, lab):
    tot = sum(1 for g, _ in pairs if g == lab)
    hit = sum(1 for g, p in pairs if g == lab and p == lab)
    return (hit / tot if tot else None), hit, tot


def main(gap_fn=None, split_of=None, quiet=False) -> int:
    """`gap_fn(row, pitch) -> threshold px` perturbs the TOKENISATION only.

    R2.1i's acceptance runs this scorer twice with different `gap_fn` and requires the region
    numbers to hold. If they move, the gold is still addressing tokens by something the splitter
    controls, and the instrument would keep reading tokenisation work as region regressions.

    `split_of(band) -> split_fn(row, pitch) -> [[l, r], ...]` is the general form, added at R2.1h's
    redesign. It takes the BAND because the recogniser splitter has to read from the image, which a
    threshold never did -- a splitter is not always a number.
    """
    if gap_fn is not None and split_of is not None:
        raise ValueError("pass gap_fn or split_of, not both")
    g = json.loads(GOLD.read_text())
    entries, ambig = g["labels"], g["ambiguous"]
    if isinstance(entries, dict):
        print("🔴 gold is still v1 (ordinal-keyed) -- run the R2.1i re-key first")
        return 1
    vol, sig = [k for k in W.WITNESSES if W.wid(*k) == "OT1-1609-B"][0]
    leaves = W.leaves(vol, sig)

    pairs, ctl_all, ctl_row0 = [], [], []
    cpairs, corph = [], []                       # R2.1j containment binding -- FAILED, kept reported
    ipairs, iorph, purity = [], [], []           # R2.1j ink binding -- the rule that survived
    bind = {}
    unlabelled = abstained = ncoll = norph = naddr = nambcoll = 0
    misses = []
    addr_fail = []
    permute_impure = 0
    for i in range(400, 420):
        band = top_band(leaves[i])
        p, psrc = CR.scale(band)
        if p is None:
            abstained += 1
            if not quiet:
                print(f"  ABSTAIN leaf {i}: no type scale ({psrc})")
            continue
        toks, why = RH.classify(band, p, nrows=NROWS, gap_fn=gap_fn,
                                split_fn=None if split_of is None else split_of(band))
        if toks is None:
            abstained += 1
            if not quiet:
                print(f"  ABSTAIN leaf {i}: {why}")
            continue

        mine = [e for e in entries if e["leaf"] == i]
        amb = [a for a in ambig if a["leaf"] == i]
        # R2.2j -- the ADDRESS. Under "ordinal" this is the shipped `e["row"]`; under "yband" the
        # entry is placed by the y-band it overlaps, so a change to the ROW CLUSTERER cannot
        # renumber it. Addressing failures are counted here and reported apart from accuracy.
        rowbands = _row_bands(band, p)
        if PERMUTE_ROWS:                                   # R2.2j M1-M3, test hook
            toks, rowbands, pure = _permute(toks, rowbands)
            if not pure:
                print(f"  🔴 leaf {i}: the permutation was NOT a pure renaming — M3 FAILS")
                permute_impure += 1
        rof = _on_line(band.height, rowbands)
        if ROW_ADDRESS == "yband":
            for e in mine:
                if rof.row_of(e) is None:
                    naddr += 1
                    addr_fail.append((i, e.get("text", "?")))
        bound, coll, orph = match(mine, toks, on_line=rof)
        # Ambiguous entries bind too, so the tokens they name are EXCLUDED rather than scored.
        excl = {(t["row"], t["tok"]) for _, t in match(amb, toks, on_line=rof)[0]}
        ncoll += len(coll)
        norph += len(orph)
        for e, t in coll:
            if not quiet:
                print(f"  ⚠️ COLLISION leaf {i} row {t['row']}: {e['text']!r} and "
                      f"{t['text']!r} both bind one token -- the splitter MERGED two labelled "
                      f"tokens; NOT scored")
        for e in orph:
            if not quiet:
                print(f"  ⚠️ ORPHAN leaf {i} row {e['row']}: {e['text']!r} overlaps no token -- "
                      f"NOT scored")

        # R2.1j -- the same gold, bound by CONTAINMENT. Ambiguous entries exclude by containment too,
        # for the same reason R2.1i re-keyed them: an exclusion that addresses differently from the
        # labels drifts away from them and silently re-admits the token it was written to exclude.
        cexcl = {id(t) for _, _, _, t in contain(amb, toks, on_line=rof)[0]}
        cobs, co = contain(mine, toks, on_line=rof)
        corph.extend((i, e) for e in co)
        cpairs.extend((g, pr) for g, pr, _e, t in cobs if id(t) not in cexcl)

        iobs, io = ink_bind(mine, toks, exclude=cexcl, on_line=rof)
        iorph.extend((i, e) for e in io)
        ipairs.extend((g, pr) for g, pr, _pu, _e in iobs)
        purity.extend(pu for _g, _p, pu, _e in iobs)

        got = {(t["row"], t["tok"]) for _, t in bound}
        unlabelled += sum(1 for t in toks
                          if (t["row"], t["tok"]) not in got and (t["row"], t["tok"]) not in excl)
        for e, t in bound:
            if (t["row"], t["tok"]) in excl:
                # R2.2l. 🔴 THE SIXTH SINK, AND IT WAS THE ONLY SILENT ONE. A labelled entry bound a
                # token that an AMBIGUOUS entry also binds, so it is dropped rather than scored. That
                # is the SAME event as a collision -- the splitter merged two labelled spans into one
                # token -- but it was neither counted nor printed, while `unlabelled`, `ambiguous`,
                # `collisions`, `orphans` and `abstained` all were. The accounting guard
                # `test_region_gold_addressing` asserts `lost <= collisions + orphans`, so every drop
                # through here read as a token vanishing for no stated reason.
                nambcoll += 1
                if not quiet:
                    print(f"  ⚠️ AMBIGUOUS-COLLISION leaf {i} row {t['row']}: {e['text']!r} binds a "
                          f"token an AMBIGUOUS gold entry also binds -- NOT scored")
                continue
            bind[(i, e["row"], e["l"], e["r"])] = (t["l"], t["r"], t["label"])
            pairs.append((e["label"], t["label"]))
            ctl_all.append((e["label"], RH.MAIN_TEXT))
            ctl_row0.append((e["label"], RH.RUNNING_HEAD if t["row"] == 0 else RH.MAIN_TEXT))
            if e["label"] != t["label"]:
                misses.append((f"{i}.{t['row']}.{t['tok']}", e["label"], t["label"],
                               round(t["x_centre"], 3), t["n_glyphs"]))

    if not pairs:
        print("no scored tokens -- no gold span overlapped any token")
        return 1

    acc = sum(1 for a, b in pairs if a == b) / len(pairs)
    a_all = sum(1 for a, b in ctl_all if a == b) / len(ctl_all)
    a_row0 = sum(1 for a, b in ctl_row0 if a == b) / len(ctl_row0)

    c_acc = (sum(1 for a, b in cpairs if a == b) / len(cpairs)) if cpairs else 0.0
    i_acc = (sum(1 for a, b in ipairs if a == b) / len(ipairs)) if ipairs else 0.0

    if quiet:
        return {"acc": acc, "pairs": len(pairs), "coll": ncoll, "orph": norph, "bind": bind,
                "ambcoll": nambcoll,                              # R2.2l, the sixth sink
                "addr_fail": naddr, "addr_fail_list": addr_fail,   # R2.2j, K2
                "permute_impure": permute_impure,                 # R2.2j, M3
                "rh": recall(pairs, RH.RUNNING_HEAD)[0],
                "mn": recall(pairs, RH.MARGIN_NOTE)[0],
                "mt": recall(pairs, RH.MAIN_TEXT)[0],
                "c_acc": c_acc, "c_obs": len(cpairs), "c_orph": len(corph),
                "c_rh": recall(cpairs, RH.RUNNING_HEAD)[0],
                "c_mn": recall(cpairs, RH.MARGIN_NOTE)[0],
                "c_mt": recall(cpairs, RH.MAIN_TEXT)[0],
                "i_acc": i_acc, "i_obs": len(ipairs), "i_orph": len(iorph),
                "i_purity": (sum(purity) / len(purity)) if purity else 0.0,
                "i_rh": recall(ipairs, RH.RUNNING_HEAD)[0],
                "i_mn": recall(ipairs, RH.MARGIN_NOTE)[0],
                "i_mt": recall(ipairs, RH.MAIN_TEXT)[0]}
    print(f"\nR2.1g -- head-band region assignment, OT1-1609-B leaves 400-419")
    print(f"  scored tokens          {len(pairs)}")
    print(f"  unlabelled (skipped)   {unlabelled}   -- <3 glyphs or unread; counted, not dropped")
    print(f"  ambiguous (excluded)   {len(ambig)}   -- listed with reasons in the gold file")
    print(f"  collisions             {ncoll}   -- gold spans merged into one token; NOT scored")
    print(f"  orphans                {norph}   -- gold spans overlapping no token; NOT scored")
    print(f"  ambiguous-collisions   {nambcoll}   -- bound a token an AMBIGUOUS entry also binds; NOT scored")
    print(f"  leaves abstained       {abstained}")
    print(f"\n  ACCURACY  instrument  {acc:.4f}")
    print(f"            ALL-MT ctl   {a_all:.4f}   (majority-class floor)")
    print(f"            ROW0-RH ctl  {a_row0:.4f}   (the rule a reader would write unaided)")

    print("\n  per-region recall:")
    ok = True
    for lab, bar in ((RH.RUNNING_HEAD, BAR_RH_RECALL), (RH.MARGIN_NOTE, BAR_MN_RECALL),
                     (RH.MAIN_TEXT, None), (RH.CHAPTER_HEAD, None)):
        r, hit, tot = recall(pairs, lab)
        if r is None:
            print(f"    {lab}  -- not present in gold")
            continue
        flag = ""
        if bar is not None:
            flag = "  ok" if r >= bar else f"  BELOW BAR {bar:.2f}"
            ok = ok and r >= bar
        print(f"    {lab}  {r:.4f}  ({hit}/{tot}){flag}")

    if misses:
        print(f"\n  MISASSIGNED ({len(misses)}) -- key, gold, got, x_centre, glyphs:")
        for m in misses:
            print(f"    {m[0]:12} gold={m[1]} got={m[2]}  x={m[3]:+.3f} n={m[4]}")

    # R2.1j -- reported ALONGSIDE, not instead of. The max-overlap number above is the one 0.8760 was
    # recorded against and stays comparable; this one is the number a FINER splitter can be scored
    # on at all. Its denominator is TOKENS OBSERVED, not entries, so the two are not interchangeable.
    print(f"\n  R2.1j CONTAINMENT binding -- every token whose centre lies in a gold span takes")
    print(f"  that span's label. Unlike max-overlap this does not require an entry to be no coarser")
    print(f"  than a token, which 43 of {len(entries)} entries (35.5%) are not.")
    print(f"    observations         {len(cpairs)}   (tokens, not entries)")
    print(f"    entries binding none {len(corph)}   -- ACCOUNTING criterion: must be 0")
    for _i, e in corph:
        print(f"      ⚠️ leaf {_i} row {e['row']}: {e['text']!r}")
    print(f"    ACCURACY             {c_acc:.4f}")
    for lab in (RH.RUNNING_HEAD, RH.MARGIN_NOTE, RH.MAIN_TEXT, RH.CHAPTER_HEAD):
        r, hit, tot = recall(cpairs, lab)
        if r is not None:
            print(f"      {lab}  {r:.4f}  ({hit}/{tot})")
    print("    🔴 CONTAINMENT FAILED ITS PRE-REGISTERED ACCOUNTING on coarser splitters "
          "(33 orphans at\n       x1.6). Reported, not relaxed -- see the block above this "
          "function.")

    print(f"\n  R2.1j INK binding -- an entry takes the label holding the most overlapping ink.")
    print(f"    scored entries       {len(ipairs)}   (must be {len(entries)} under EVERY splitter)")
    print(f"    entries binding none {len(iorph)}   -- ACCOUNTING criterion: must be 0")
    for _i, e in iorph:
        print(f"      ⚠️ leaf {_i} row {e['row']}: {e['text']!r}")
    print(f"    ACCURACY             {i_acc:.4f}")
    print(f"    mean purity          {(sum(purity)/len(purity)) if purity else 0.0:.4f}   "
          f"-- 1.0 = every entry's ink carried ONE label; below 1 the splitter\n"
          f"                              cut across a labelled region and the majority hid it")
    for lab in (RH.RUNNING_HEAD, RH.MARGIN_NOTE, RH.MAIN_TEXT, RH.CHAPTER_HEAD):
        r, hit, tot = recall(ipairs, lab)
        if r is not None:
            print(f"      {lab}  {r:.4f}  ({hit}/{tot})")

    # ── THE DENOMINATOR BAR. Every criterion above this point is a rate; this one bars what those
    # rates are computed OVER, so a candidate cannot raise one by shrinking the other. See the block
    # at the top of this module for why the accounting guard in `test_region_gold_addressing` does
    # not already cover it: that clause requires losses to be REPORTED, not to be absent.
    sinks = ncoll + norph + nambcoll
    print(f"\n  DENOMINATOR -- what the rates above are computed over:")
    print(f"    gold entries         {len(entries)}")
    print(f"    scored (max-overlap) {len(pairs)}   + {sinks} in reported sinks "
          f"(coll {ncoll}, orph {norph}, ambcoll {nambcoll})")
    # An enumeration check, not a bar: if these do not sum, an entry left the denominator without
    # passing through any reported sink, and every number in this report is then unsafe.
    if len(pairs) + sinks != len(entries):
        print(f"    🔴 ACCOUNTING DOES NOT CLOSE: {len(pairs)} + {sinks} != {len(entries)}. "
              f"An entry left the sum unreported -- NO number above is trustworthy.")
    full = (len(pairs) == len(entries)) if FULL_ACCOUNTING else True
    ink_ok = len(iorph) <= BAR_MAX_INK_ORPHANS
    if not full:
        print(f"    🔴 BELOW BAR: {sinks} gold entr{'y' if sinks == 1 else 'ies'} did not reach the "
              f"sum. The control scores all {len(entries)}, so the rates above are NOT comparable\n"
              f"       to it -- they are computed over a different set. A rate that rose here may "
              f"have risen BY the discarding.")
    else:
        print(f"    ok -- all {len(entries)} entries scored; the rates are comparable to the control")
    if not ink_ok:
        print(f"    🔴 BELOW BAR: ink binding left {len(iorph)} entries unbound, above the control's "
              f"{BAR_MAX_INK_ORPHANS}. The ideal is 0 and stays OPEN.")

    beats = acc > a_all and acc > a_row0
    if not beats:
        print("\n  🔴 THE INSTRUMENT DOES NOT BEAT ITS CONTROLS. Its complexity is unearned; the "
              "finding is that the simple rule is as good, and that is the result to report.")
    good = ok and beats and full and ink_ok
    print(f"\n  verdict: {'PASS' if good else 'FAIL'}")
    return 0 if good else 1


if __name__ == "__main__":
    raise SystemExit(main())

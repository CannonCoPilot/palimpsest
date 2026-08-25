"""R2.2f ACCEPTANCE -- score PER-SEGMENT R4 against G1-G5, pre-registered in OCR-ROADMAP.md
§ "R2.2f PRE-REGISTRATION" and reproduced here verbatim:

  G1  THE ENTRY      -- leaf 412 r2's note `pinces are`, the one gold entry the span qualifier
                        flipped, must come back MarginNote with the qualifier ON.   bar: MN
  G2  THE BAR R2.2e-b FAILED -- with the span qualifier ON: MN >= 0.8947 while acc, RH and MT do
                        not fall below the qualifier-ON numbers 0.9174 / 1.0000 / 0.9125
  G3  NO REGRESSION ON THE SHIPPED PIPELINE -- the four gold numbers 0.8760 / 1.0000 / 0.8947 /
                        0.8375 exactly unmoved                                      bar: exact
  G4  THE CONSUMER   -- not below the 23/43 the qualifier alone reached.            bar: >= 23
  G5  REACH          -- rows DEMOTED and rows taking the no-qualifying-segment fallback, reported

**Adoption requires G1-G4 TOGETHER**, and adopts `R4_PER_SEGMENT` ONLY -- not `BLOCK_SPAN_QUALIFIES`,
whose own F1 bar (43/43) is a different link of the chain.

⚠️ G3 IS SCORED ON THE STRICTER OF ITS TWO READINGS. As worded it says "with the span qualifier OFF
(both flags off, i.e. what ships today)", which describes the BASELINE -- a configuration this
candidate cannot move, so the criterion would be vacuous. The configuration that actually ships if
R2.2f is adopted is `R4_PER_SEGMENT` ON with the qualifier OFF, so the verdict is taken on THAT and
both numbers are printed. Reporting the wording's own number too, rather than quietly substituting
one for the other, is the R11.2c discipline: do not amend the instrument mid-flight.

⚠️ NOTHING HERE RE-DERIVES A RULE IT SCORES. The consumer count and the merge count come from
`score_block_span._consumer_and_merges`, D1 from `score_region_gap_tokens._argument_recall`, and the
gold numbers from `score_head_regions.main` -- the same functions the earlier links were scored with.
A scorer holding its own copy of a rule measures the copy (R2.2e, §"the splitter/label handoff").
"""

import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(_HERE.parent))

import witnesses as W
import collation_read as CR
import region_head as RG
import score_head_regions as SR
import score_region_gap_tokens as SG
import score_block_span as SB

GOLD = SR.GOLD
ENTRY = {"leaf": 412, "row": 2, "text": "pinces are"}       # G1, named before the run
SHIPPED = {"acc": 0.8760, "rh": 1.0000, "mn": 0.8947, "mt": 0.8375}
QUALIFIER_ON = {"acc": 0.9174, "rh": 1.0000, "mn": 0.8947, "mt": 0.9125}   # MN is the bar it FAILED
D1_BAR = 52
CONSUMER_BAR = 23

# (name, BLOCK_SPAN_QUALIFIES, R4_PER_SEGMENT)
CONFIGS = (
    ("BASELINE          (both off -- what ships today)", False, False),
    ("R2.2e-b ALONE     (span qualifier on)", True, False),
    ("R2.2f ALONE       (per-segment R4 on -- SHIPS if adopted)", False, True),
    ("R2.2f + R2.2e-b   (the prerequisite relation under test)", True, True),
)


def _entry_label(leaves):
    """-> (label, reason, diagnosis). What the pipeline calls G1's gold entry, bound the gold's own way.

    Uses `score_head_regions.match` -- the binding the gold's four numbers are measured with -- so
    G1 cannot disagree with G2 about which token the entry is.

    ⚠️ `diagnosis` reports the token's R2.2f FATE and every region segment of its row against R3's
    two clauses. A criterion that says only PASS/FAIL cannot distinguish "the rule declined this
    token" from "the rule never reached this row", and those call for opposite next steps.
    """
    g = json.loads(GOLD.read_text())
    want = [e for e in g["labels"]
            if e["leaf"] == ENTRY["leaf"] and e["row"] == ENTRY["row"]
            and ENTRY["text"] in e["text"]]
    if len(want) != 1:
        return None, f"G1's entry is not uniquely addressable: {len(want)} candidates", []
    band = SR.top_band(leaves[ENTRY["leaf"]])
    p, why = CR.scale(band)
    if p is None:
        return None, f"no type scale on leaf {ENTRY['leaf']} ({why})", []
    toks, why = RG.classify(band, p, nrows=SR.NROWS)
    if toks is None:
        return None, why, []
    bound, _coll, orph = SR.match(want, toks)
    if not bound:
        return None, f"entry is an ORPHAN ({len(orph)}) -- it overlaps no token", []
    tok = bound[0][1]
    diag = [f"fate {tok.get('r4_seg', '(rule off)')}"]
    # The row's segments against R3's own two clauses, recomputed from the SAME primitive the rule
    # uses. `classify` pops `_row`, so the geometry is taken from a fresh tokenise of the same band.
    allt, _why = RG.tokens(band, p)
    row = next((t["_row"] for t in allt if t["row"] == tok["row"]), None)
    LR, _why = RG.block_measure(allt, p)
    if row and LR:
        L, R = LR
        measure = R - L
        ftol = max(RG.FLUSH_TOL_P * p, RG.FLUSH_TOL_M * measure)
        diag.append(f"L={L:.0f} R={R:.0f} measure={measure:.0f} flush_tol={ftol:.0f} "
                    f"span_bar={RG.BODY_SPAN_M * measure:.0f}")
        for seg in CR.region_segments(row, p):
            a, b = min(gg[2] for gg in seg), max(gg[3] for gg in seg)
            diag.append(f"segment l={a:.0f} r={b:.0f} span={b - a:.0f} "
                        f"{'FULL' if (b - a) >= RG.BODY_SPAN_M * measure else 'short'} · "
                        f"dL={abs(a - L):.0f} dR={abs(b - R):.0f} "
                        f"{'FLUSH' if (abs(a - L) <= ftol or abs(b - R) <= ftol) else 'not flush'}")
    return tok["label"], None, diag


def _reach(leaves):
    """-> (rows demoted, rows on the fallback, samples). G5, read off `r4_seg` in the labels."""
    demoted, fallback, samples = set(), set(), []
    for i in range(400, 420):
        band, _frame = CR.band_frame(leaves[i], 0.0, 1.0)
        p, _src = CR.scale(band)
        if p is None:
            continue
        toks, _why = RG.classify(band, p)
        if toks is None:
            continue
        for t in toks:
            fate = t.get("r4_seg")
            if fate == "demoted":
                demoted.add((i, t["row"]))
                if len(samples) < 8:
                    samples.append((i, t["row"], t["l"], t["r"], t["label"]))
            elif fate == "fallback":
                fallback.add((i, t["row"]))
    return demoted, fallback, samples


def main() -> int:
    g = json.loads(GOLD.read_text())
    del g
    gap = json.loads(SB.GOLD.read_text())
    want = {}
    for e in gap["rows"]:
        if not e["is_argument_row"]:
            want.setdefault(e["leaf"], []).append((e["y0f"], e["y1f"], e["read"]))
    vol, sig = [k for k in W.WITNESSES if W.wid(*k) == "OT1-1609-B"][0]
    leaves = W.leaves(vol, sig)
    was = (RG.BLOCK_SPAN_QUALIFIES, RG.REGION_GAP_TOKENS, RG.R4_PER_SEGMENT, RG.ARGUMENT_RULE)

    print("\nR2.2f -- R4 labels PER REGION SEGMENT, not per row. OT1-1609-B leaves 400-419")
    print("  rule: in a body row, an in-block token is MainText iff it lies in a region segment that\n"
          "  itself meets R3's test (span >= BODY_SPAN_M x measure AND flush at L or R). A row with\n"
          "  NO qualifying segment keeps today's labels -- the rule may only DEMOTE.")
    print(f"  R4_PER_SEGMENT is currently {RG.R4_PER_SEGMENT}")

    rows = {}
    for name, span_on, seg_on in CONFIGS:
        RG.BLOCK_SPAN_QUALIFIES, RG.R4_PER_SEGMENT = span_on, seg_on
        RG.REGION_GAP_TOKENS = RG.ARGUMENT_RULE = False
        reg = SR.main(quiet=True)
        hit, tot, miss, _merges = SB._consumer_and_merges(leaves, want)
        lab, why, diag = _entry_label(leaves)
        dem, fb, samples = _reach(leaves) if seg_on else (set(), set(), [])
        RG.ARGUMENT_RULE = True
        d1 = SG._argument_recall(leaves)
        RG.ARGUMENT_RULE = False
        rows[name] = (reg, hit, tot, lab, why, dem, fb, samples, d1, miss, diag)
        print(f"\n  ── {name} ──")
        print(f"     region gold  acc {reg['acc']:.4f}  RH {reg['rh']:.4f}  MN {reg['mn']:.4f}  "
              f"MT {reg['mt']:.4f}")
        print(f"     consumer {hit}/{tot} swallowed body rows carry MainText   D1 {d1}/81")
        print(f"     G1 entry `{ENTRY['text']}` (leaf {ENTRY['leaf']} r{ENTRY['row']}): "
              f"{lab if lab else '🔴 ' + str(why)}")
        for line in diag:
            print(f"        {line}")
        if seg_on:
            print(f"     G5 reach: {len(dem)} row(s) DEMOTED at least one token, "
                  f"{len(fb)} row(s) on the no-qualifying-segment fallback")
            for i, j, l, r, lb in samples:
                print(f"        demoted leaf {i} r{j}  l={l:.0f} r={r:.0f} -> {lb}")

    RG.BLOCK_SPAN_QUALIFIES, RG.REGION_GAP_TOKENS, RG.R4_PER_SEGMENT, RG.ARGUMENT_RULE = was

    both = rows[CONFIGS[3][0]]
    seg_only = rows[CONFIGS[2][0]]
    base = rows[CONFIGS[0][0]]
    reg = both[0]
    tol = 5e-5                  # see the note under G3 -- the bars are 4-dp transcriptions
    g1 = both[3] == RG.MARGIN_NOTE
    g2 = (reg["mn"] >= QUALIFIER_ON["mn"] - tol
          and all(reg[k] >= QUALIFIER_ON[k] - tol for k in ("acc", "rh", "mt")))
    # ⚠️ COMPARED AT THE PRECISION THE NUMBERS ARE RECORDED AT. First written at 1e-9 against these
    # 4-dp literals, and the BASELINE -- a configuration this candidate cannot reach, both flags off
    # and the identical code path -- came back "MOVED". The recorded bar is a rounded transcription
    # of a float; demanding bit-equality to it makes a criterion that no run can ever pass, which is
    # a scorer defect wearing the costume of a finding.
    g3_ships = all(abs(seg_only[0][k] - SHIPPED[k]) < tol for k in SHIPPED)
    g3_worded = all(abs(base[0][k] - SHIPPED[k]) < tol for k in SHIPPED)
    g4 = both[1] >= CONSUMER_BAR
    g5 = len(both[5])

    print("\n  ══ VERDICT ══")
    print(f"     G1 the entry            {both[3]}   {'PASS' if g1 else '🔴 FAIL (bar MN)'}")
    print(f"     G2 gold, qualifier ON   acc {reg['acc']:.4f} RH {reg['rh']:.4f} "
          f"MN {reg['mn']:.4f} MT {reg['mt']:.4f}   {'PASS' if g2 else '🔴 FAIL'}")
    print(f"     G3 shipped pipeline     per-segment alone {'exact' if g3_ships else '🔴 MOVED'} "
          f"· baseline {'exact' if g3_worded else '🔴 MOVED'}   "
          f"{'PASS' if g3_ships and g3_worded else '🔴 FAIL'}")
    print(f"     G4 consumer             {both[1]}/{both[2]} (bar {CONSUMER_BAR})   "
          f"{'PASS' if g4 else '🔴 FAIL'}")
    print(f"     G5 reach                {g5} row(s) demoted, {len(both[6])} on the fallback"
          f"{'   ⚠️ FITTED TO ITS OWN WITNESS' if g5 <= 1 else ''}")
    ok = g1 and g2 and g3_ships and g3_worded and g4
    print(f"\n  verdict: {'PASS -- adopt R4_PER_SEGMENT (and R4_PER_SEGMENT ONLY)' if ok else 'FAIL'}"
          f"{'' if ok else '  -- R4_PER_SEGMENT stays False; the candidate is NOT adopted'}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

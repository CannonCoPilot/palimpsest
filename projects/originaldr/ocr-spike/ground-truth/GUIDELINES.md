# Ground-truth transcription guidelines (Jarvis, 2026-07-12)

Per AI_OCR skill and No-Silent-Degradation, an "undocumented reference is an undefined target."
These guidelines govern every ground-truth file in this directory.

## The one rule that governs everything

**Diplomatic — reproduce what is PRINTED, not what should have been printed.**
Modernization is silently corrupting. When in doubt, transcribe what your eye sees; flag rather
than guess.

## Glyphs preserved exactly (as-printed)

| Glyph | Treatment | Example |
|---|---|---|
| long-ſ | preserve `ſ` (U+017F) **only where the compositor actually set it** — NOT by position rule (see §long-ſ below) | `beſeech`, `maiſter` |
| u/v | preserve period-swap: `vpon`, `vnderſtand`, `geue`, `haue` | (medial `v`→`u`, initial `u`→`v`) |
| i/j | preserve: `Iſaac`, `iourney`, `IESVS` | (no `j` in typical positions) |
| æ / œ | preserve as printed; do NOT expand to `ae`/`oe` | `Iudæa`, `pœnitence` |
| **`w`** | **PER-REGION (Sir, 2026-07-12).** The BODY sets a REAL `w` sort → transcribe `w`. The FOOTNOTES / ANNOTATIONS set `vv` → transcribe `vv` (see §footnote-typeface). Do NOT assume one rule for the whole page. | body `wordes`, `drawe`; footnote `vvhich`, `lavv`, `forthvvith` |
| verse markers `†` `‡` | preserve — these ARE printed glyphs. Verse NUMBERS are NOT body text (see §body-excludes). | `† For inheritance` |
| footnote/marginal anchor `‖` `*` `°` | preserve when visible | `into ‖ her mothers houſe` |
| inline reference-letter (`a`…`z`) | an annotation KEY, NOT scripture — do NOT put in body text (see §body-excludes). Record in `ref_letter`. | `I b ſware` → body `I ſware`, `ref_letter:"b"` |
| ligatures (ſt, ſh, ct, st) | transcribe **component letters** (`ſt`→`ſ`+`t`, `ſh`→`ſ`+`h`, `ct`→`c`+`t`) — no distinct codepoint and the metric folds them anyway. The ligature's presence is what tells you the `s` is a LONG-ſ (see §long-ſ). | `vnderſtand` (ſt), `prote**ct**our` (ct) |
| **French spacing** | this edition sometimes sets a **space before high punctuation** (`:` `;` `?` `!`). Preserve it as printed. | `ſaid : Geue me`, `anſwered :` |
| typos | **PRESERVE printer's errors exactly as printed** — diplomatic fidelity includes mistakes (see §typos). | `carelettes` (printed error for *earelettes*) |
| hyphenation at line-end | preserve the hyphen; join with `-\n` | `Abra-\nham` |

## §long-ſ — the rule is GLYPH-DRIVEN, not positional (Sir, 2026-07-12)

The common heuristic "long-ſ at word start/middle, round-s at end" is **WRONG for this edition** and
will make you over-produce ſ. This compositor mixes forms — most visibly in `sh` clusters:

- Where a genuine **ſh LIGATURE** (or a plainly long-ſ) is set, transcribe `ſh`: e.g. `I ſhal vnderſtand`.
- Where the compositor set a **round `s` + `h`** as two separate sorts, transcribe `sh`: e.g. `ſhal ſay`
  is actually `shal ſay`, `ſhe ſhal anſwere` is `she shal anſwere`.

The SAME word (`shal`) appears both ways on one page. **Read every `s` and transcribe the glyph you
see, not the glyph the position predicts.** (My first Gen 24 pass invented ~11 long-ſ this way: 62 vs
the true 51. The OCR's ſ-count was closer to truth than my transcription.)

## §typos — preserve, don't correct

If the plate prints an error, transcribe the error. `carelettes` (a `c` for `e`) stays `carelettes`,
NOT silently fixed to `earelettes`. If you're unsure whether it's a typo or your misread, flag
`⟨?⟩` and note both readings — but never "correct" a genuine printed error into the intended word.

## §catchwords — EXCLUDE from body (Sir, 2026-07-12)

A **catchword** is a right-justified word or short phrase at the FOOT of a page that anticipates the
first word(s) of the NEXT page (a reader/binder convenience). It is **duplicated** at the top of the
following page. Therefore:
- Mark it `"role": "catchword"` in the body array (keep the physical line — it IS on the page and the
  segmenter must learn to classify it), but **exclude it from the scripture-body concatenation**, or
  page-joining will double-count it.
- The `gt_apply_corrections.py` heuristic auto-tags a trailing, excluded, ≤3-word line as a catchword.
- **Pipeline consequence**: the OCR segmentation/consensus stages MUST detect and strip catchwords
  (foot-of-page, right-justified, matches next-page head). Logged for Phase 2a.

## §body-excludes — verse numbers & reference-letters are NOT scripture body (Sir, 2026-07-12)

The `body[].text` field is the SCRIPTURE SURFACE only. Two things printed *in the body's visual flow*
are apparatus, not scripture, and must be kept OUT of the text:

- **Leading verse numbers** (`103`, `105`, `106`…): record in `verse_number_printed`, never in `text`.
  (My first Psalms pass wrongly baked `103 c How ſweete…` into the text; correct is `How ſweete…`.)
- **Inline reference-letters** (`a`…`z` keying a verse to its footnote): record in `ref_letter`, never
  in `text`. `106 b I b ſware…` → text `I ſware…`, `verse_number_printed:"106"`, `ref_letter:"b"`.

Rationale: these tokens are not in the reference (s_dismas) and pollute recall scoring. Removing them
from Psalms 118 raised GT-vs-s_dismas 0.8824 → 0.9223 — proof they were noise, not signal. `†` verse
markers, by contrast, ARE printed scripture punctuation and stay in the text.

## §footnote-typeface — annotations are set in a DIFFERENT face than the body (Sir, 2026-07-12)

The italic annotations/footnotes do NOT share the body's typographic conventions. In the footnote face:
- **`w` is set as `vv`** (body uses a real `w`): `vvhich`, `lavv`, `forthvvith`, `vvorkes`, `revvard`.
- **long-ſ is used for `s`** (do not misread it as `f`), and **a long-`f` is used for `f`**. Read the
  descender/crossbar carefully: `ſ` (s) has no crossbar; `f` does. Footnote type is small — slow down.
- Everything else (u/v swap, ligatures→components, typos-preserved) still applies.

So a single page carries TWO glyph regimes: body (`w`) and apparatus (`vv`). Transcribe each region by
its own face. Flag `role`/region on every apparatus element so the recognizer can be told which face
to expect.

## §w-regime — PER-INSTANCE visual call (Sir ruled 2026-07-18; supersedes any "uniform roman=w")

**There is NO lexical or positional rule for `w` vs `vv`.** Sir's hand-adjudication of the Genesis 16
annotation (genesis-16-p082, ~40 instances) proves it: the SAME word is set both ways on the same page —
`law`/`lawful` is `w` in some lines and `vv` in others; so is `which`; so is `were` (L43 keeps `vvere`
but changes `vviues→wiues` on ONE line). The compositor simply grabbed whichever sort was in the case.
**Decide every instance by the glyph on the page, never by the word.**

THE CALL (visual, per glyph):
- **Joined / overlapping strokes** (the two v-elements share the middle, no gap) → a real `w` sort → `w`.
- **Two clearly separate strokes with a gap** → two `v` sorts → `vv`.
- Zoom **2–5× on BODY-size type** (gestalt). Do NOT over-zoom past ~5× at 400 DPI — the sort pixelates
  and the gap becomes unreadable (over-zooming caused a wrong "unresolvable" call on 2026-07-15). Small
  footnote/marginal type is near the 400 DPI limit; flag low-confidence rather than guess.

EMPIRICAL TENDENCIES (PRIORS only — the pixels decide, never these):
- Roman body/prose is **predominantly `w`** (~85% in Sir's genesis-16 pass). Agents over-produced `vv`,
  so the common error is a real `w` mis-set as `vv`. Default suspicion: a `vv` in roman body is probably `w`.
- **Genuine `vv` clusters at**: word-initial CAPITALS (`VVhich`, `VVhereof`); DISPLAY titling caps
  (`NEVV TESTAMENT`, `IESVS` with V=U — that fount has NO W sort, always `VV`, KEEP it); and (weakly)
  line-ends where the w-sort ran short.
- Italic: NT arguments/annotations use real `w` (`Whoſe`); OT italic annotations use genuine `vv`.

FOR THE OCR PASS (Sir's ask — "a rule-based approach for higher accuracy"):
- The classifier must make a **per-glyph visual `w`-vs-`vv` decision on stroke connectivity**. It must
  **NOT dictionary-normalize** — that erases the genuine `vv` minority Sir preserves.
- Priors above may bias a low-confidence glyph; pixel evidence wins. Emit confidence; route low-confidence
  `w`/`vv` to human review.

STATUS AMENDMENT (Sir, 2026-08-06): **mixed `w`, `vv`, `VV` and `Vv` are likely on a variety of leaves.
Do not exclude the possibility, and be cautious about global flips lest original variants be overwritten.**
The rule below is unchanged and correct; what follows is a scope limit on one ratification.

**The matter-nt front-matter ratification is WITHDRAWN pending re-adjudication (roadmap R6.6).** It was
made on `NT-1582-F` — an 800x1124 (~168 ppi) source, read at a 400-dpi *render*. `F` is barred from
glyph-level work because the long-ſ nub spans under 1.6 px there, and **the gap distinguishing two `v`
sorts from one joined `w` is a finer feature than that nub**. Worse, upscaling interpolates precisely that
gap, so the render makes separate sorts look joined — biasing the call toward `w`, which is the direction
the flip went. Reading "the matter-nt prose fount is uniformly connected-`w`" as settled is therefore not
supported by the image it was settled on.

Counter-evidence from a raster that CAN carry the call: the same two frontmatter leaves in the 1582 setting,
read from `NT-1582-M` at ~380 ppi (R6.3), show the prelims prose face setting BOTH forms — `VVhich` as a
cap-height `V` plus an x-height `v` with a clear gap, and `word` as a single joined sort, **on the same line
as a two-sort `vve`**. Note also that `matter-nt-preface.json` is the **1633** setting, not the 1582 one, so
any fount claim drawn from it never described the 1582 prelims at all.

Practical consequence: **never decide `w`/`vv` on `F`.** Use `B` (~545 ppi) where it has the leaf, `M`
(~380 ppi) where it does not, and flag rather than guess. Retain `*.pre-vvfix` backups — they record what
an observer saw; the current files record what a rule produced.

STATUS (2026-07-18): pages Sir hand-adjudicated (genesis-16 p081/p082; psalms 1/74/115-116/118/150) are
AUTHORITATIVE and applied. mt28-p102 (my 2026-07-15 vv→w) was re-reviewed by Sir with 0 w/vv changes →
RATIFIED. matter-nt front-matter (my 2026-07-15 blanket vv→w) is now VISUALLY VERIFIED (2026-07-18): the preface
body paragraph shows `Which / we / alwayes / were / knowen / were` all as **connected `w`** — the matter-nt
prose fount is uniformly connected-`w`, so the conversions stand and nothing reverts. Body-text capitals use
a real W (`Which`), unlike the display titling fount (`NEVV` = gapped VV, correctly kept). Genuine lowercase
`vv` lives in the small ANNOTATION fount (e.g. genesis-16 annotations), not the clean prose founts.

## §markers, verse/line structure & earmarking (Sir, 2026-07-18)

Priority #1 is the ACCURATE TEXT of every element (body, headings, arguments, footnotes, marginalia).
Relational fidelity only needs to be **chapter-level**; the end goal is text Palimpsest can detect &
MASK by type (book / chapter / verse / apparatus). So every apparatus element must be EARMARKED (kept,
tagged with the chapter+verse it hangs off) — but a fully-relational verse↔footnote DB is NOT required.

- **Leading verse numbers** — NOT body text. Strip from the line, record in `verse_number_printed`.
  (Sir's pass left many in, inconsistently — normalise: strip all; keep the number in the field.)
- **Inline footnote/annotation keys** (`a`…`z`, incl. the mid-text `q r ſ t v w x y` in Psalm 74) — NOT
  body text. Strip from the body, record the key in `ref_letter`/apparatus, and EARMARK it to its
  chapter+verse so the annotation can be re-attached at mask time. Do not silently drop — earmark.
- **`†` verse markers — DECIDED (Sir 2026-07-18): detect but strip.** `†` (and `‡`) are printed verse
  dividers — the OCR/segmenter SHOULD learn to detect their visual presence (a verse-boundary cue), but the
  produced **output/core text STRIPS them** (verse boundaries are already carried by verse numbering). The GT
  archaic `text` keeps `†` as printed; `glyph_map.to_core()` strips it for the core. Consistent everywhere.
- **Lines vs verses cross-cut** (Gen 24, 2 John) — a printed LINE often spans a verse boundary and a verse
  spans several lines. The GT must carry BOTH a `line_index` per body line (for line-by-line OCR/review)
  AND a resolvable verse span (`verse`/`verses_on_page`) so post-processing can serve either grain. Do NOT
  force line breaks onto verse breaks. 2 John lines explicitly cross verses: preserve as printed, tag spans.

## §glyph-repertoire — ligatures & s-variants (Sir's proof-reading, 2026-07-18)

Diplomatic capture must preserve TYPESET LIGATURES and s-form variants, not only the letters.

| Feature | On the page (example) | Unicode | Notes |
|---|---|---|---|
| long-ſ + t ligature | `vnderſtand` (Gen 24:14) | `ﬅ` U+FB05 | a real single ſt-sort; there was no distinct glyph in GT before — add it |
| round s + t ligature | `st` clusters | `ﬆ` U+FB06 | only where the ſt ligature is not the sort used |
| **ct ligature** | `protection`, `doctrine` — Sir: "ALL `ct` are always ligatures" | *(none)* | no standard Unicode; see encoding decision below |
| **ſh ligature** vs **s+h** | Gen 24:14: `ſhall vnderſtand` is a tied `ſh` sort, but `shal say` / `she shal anſwere` on the SAME verse are round-`s`+`h` | ſh / sh | the word `shal` appears BOTH ways on one page — read the glyph, don't normalize |
| **tall-ſ vs long-ſ** | `neither ſpoke againſt God`: the `s` in *ſpoke* is TALL (ascender only); the `s` in *againſt* is LONG (ascender **and** descender) | ſ U+017F for both, for now | two variant long-s sorts; the LETTER is identical (`s`) |
| footnote `s`/`f` | footnote face | ſ / f | footnotes use a real long-ſ for `s` and a long-`f` for `f` — NOT a diplomatic-`f` standing in for `s`. Crossbar: ſ has none, f has one |

**Encoding — DECIDED (Sir 2026-07-18): option (B), implemented in `glyph_map.py`.**
The GT `text` fields stay the **archaic** source of truth (ſ, æ, †, ⟨?⟩, u/v, i/j as printed). A reversible
mapping derives the two views Palimpsest needs:
- **core** = MODERN BASE CHARACTERS, archaic SPELLING preserved (`vnderſtand`→`vnderstand`, `diſpēſeth`→
  `dispenseth`, `Æthiopians`→`Aethiopians`). This is what search / embeddings / edit-distance run on.
- **archaic** = re-emittable exactly from `(core, variants)` for other projects.

`glyph_map.py`: `encode(archaic)->(core,variants)`, `decode(core,variants)->archaic`, `to_core(archaic)`.
Round-trip is verified EXACT on all 830 GT fields; core contains no unmapped non-ASCII. The comprehensive
map: `ſ→s`, `ﬅ/ﬆ→st`, `æ→ae` `Æ→Ae`, `œ→oe`, macron/tilde vowel→vowel+n (nasal abbrev, `ē→en`), accents
ASCII-folded, `⟨X?⟩`→guess `X`. Markers `† ‡ ‖ ″` are STRIPPED from core (recorded for reversal). `u/v` and
`i/j` are NOT mapped — they are archaic spelling, kept verbatim. Do NOT add MUFI/PUA display glyphs inline
(option A rejected) — `ﬅ`/`ﬆ` are the only ligature chars used, and only because they have real Unicode.

## Uncertain glyphs

If you cannot read a glyph with 100% confidence:
- Use `⟨?⟩` for a single unclear character: `car⟨?⟩letres`
- Use `⟨WORD?⟩` for a fully uncertain word: `⟨earelettes?⟩`
- Use `⟨...?⟩` for illegible/damaged text spans
- ALWAYS prefer flagging over guessing — "silently guessed" ground truth POISONS the training set.

## Reference use (content anchor ONLY, never spelling oracle)

You may consult the modern DR (janvier / Madueke) to confirm which verses are on the page and to
catch dropped lines. You may NOT copy modernized spelling from it. If the printed page says
`beſeech` and janvier says `beseech`, you write `beſeech`. If the printed page says a word you
cannot read at all, you flag `⟨...?⟩` — you do NOT fill it in from janvier.

## Structure of a ground-truth JSON

```json
{
  "locus": "scripture/genesis/24",
  "page_index": 99,
  "ocr_dir": "archive-ot1-1609",
  "scan": "S1",
  "raster": "diag-reocr/gen24-S1-p99-400dpi.png",
  "raster_dpi": 400,
  "page_label_printed": "79",
  "running_header": {"left": "Abraham.", "center": "GENESIS.", "right": "79"},
  "verses_on_page": ["24:12b", "...", "24:30a"],
  "body": [
    {"verse": "24:12b", "line_index": 0, "text": "I beſeech thee, and doe mercifully with my maiſter Abra-", "line_end_hyphen": true},
    {"verse": "24:13",  "line_index": 1, "text": "ham. † Behold I ſtand nigh to the fountaine of water, and", "verse_marker": "†"},
    ...
  ],
  "marginalia": [
    {"anchor_verse": "24:28", "anchor_glyph": "‖", "text": "Her father hauing per-\nhaps manie wiues and ſe-\nuerall houſes..."}
  ],
  "sfoot_glyphs": {"long_s_count": 60, "u_swap_count": 8, "i_swap_count": 3},
  "uncertain": [
    {"line_index": 26, "span": "careletres", "note": "letter shapes could be car⟨e⟩letres or ear⟨e⟩lettes; sweep OCR reads careletres, v30 uses earelettes for same referent"}
  ],
  "observer": "jarvis",
  "observed_at": "2026-07-12",
  "method": "visual-multimodal-read + Sabates/Madueke as content anchor only"
}
```

## What goes in `uncertain`

EVERY flagged `⟨?⟩` in body / marginalia should have a corresponding entry in `uncertain` with:
- `line_index` — which body/marginalia line
- `span` — the specific text
- `note` — WHY it's uncertain, plus what other evidence (other scans, sweep OCR, etc.) suggests

Uncertain entries are a first-class part of the ground truth. They tell downstream models "this
page has these known ambiguities — don't be penalized for the ambiguous glyphs during fine-tune."

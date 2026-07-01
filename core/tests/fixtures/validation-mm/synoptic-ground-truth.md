# Synoptic Ground Truth — Matthew ↔ Mark

Pericope-level oracle for the standing Matthew-Mark validation collection. Both members
(DR-MM, Geneva-MM) contain the same two gospels in different English translations, so this
mapping is translation-independent — it grounds *what should and should not align* between
Matthew and Mark.

The machine-readable form is `synoptic-ground-truth.json`; this file is its human-readable
companion.

## How to use it as a TP/TN oracle

| Set | Source list | Expectation for a correct cross-text analysis |
|---|---|---|
| **True positives** | `shared_pericopes` (101) | Mt and Mk both contain the passage → a correct Mt↔Mk analysis links them (**off-diagonal** correspondence in a single-book alignment; a shared homology node in the corpus graph). |
| **True negatives** | `matthew_unique` (41) ∪ `mark_unique` (10) | No counterpart in the other gospel → a correct analysis leaves them **unlinked** (a `singleton` in the corpus graph; no cross alignment record). |

`tradition` (triple = Mt+Mk+Lk; double = Mt+Mk not Lk) is retained for scholarly completeness
but is **orthogonal** to the Mt↔Mk TP/TN judgement — both triple and double pericopes are Mt↔Mk
true-positives. `confidence: medium` marks boundary-debated or partial-echo pericopes; weight
them lower when scoring precision/recall.

## Provenance

Compiled from standard synoptic scholarship and cross-verified across independent sources:

- Aland, *Synopsis Quattuor Evangeliorum* (13th ed.) — via bible-researcher.com/parallels.html
- Stephen C. Carlson, *Parallel Synoptic Table*, hypotyposeis.org (2004, based on Aland)
- Supporting boundary checks: Wikipedia (Synoptic Gospels; Blind man of Bethsaida; Deaf-mute of
  Decapolis; Naked fugitive)

Versification is KJV/RSV-standard (Nestle-Aland chapter:verse), which the Douay-Rheims and 1599
Geneva NT gospels follow without shift.

## Summary counts

| Category | Count | Notes |
|---|---|---|
| Shared pericopes (TP) | 101 | ~90% of Mark is paralleled in Matthew — Mark is the near-subset |
| Matthew-unique (TN) | 41 | Infancy (1–2), Sermon on the Mount (5–7), M-parables, ch. 23 woes, guard/commission |
| Mark-unique (TN) | 10 | Seed growing secretly (4:26–29), deaf-mute (7:31–37), blind of Bethsaida (8:22–26), naked youth (14:51–52), widow's mite (12:41–44) |

## Expected signal in the validation collection

The word-overlap alignment runs **per book within each translation pair** (DR-Mt↔Geneva-Mt is
the strong translation-equivalence diagonal). The synoptic signal is the **weaker off-diagonal**:
Matthew passages that resemble Mark passages (and vice versa) because they narrate the same
pericope. A faithful pipeline should:

1. Surface the dense translation diagonal (DR↔Geneva, same book) as high-similarity.
2. Surface shared-pericope Mt↔Mk pairs as detectable-but-weaker off-diagonal correspondences.
3. Leave `matthew_unique` / `mark_unique` passages without a cross-gospel partner.

Failure modes this oracle catches: a silent alignment cap or insufficient traceback masking that
collapses coverage onto one book (leaving most of Mark unaligned); an over-eager anchor that links
a unique pericope to unrelated material (false positive against the TN set).

## Boundary flags (from source reconciliation)

- **Anointing at Bethany** (Mt 26:6–13 / Mk 14:3–9): listed `triple` because Lk 7:36–50 is
  commonly tabled as a parallel, though many treat Lk 7 as an independent story → would make it
  `double`. Mt↔Mk TP either way.
- **Death of John the Baptist** (Mt 14:3–12 / Mk 6:17–29): `triple` via Lk 3:19–20 (imprisonment
  only); the full execution narrative is Mt+Mk → arguably `double`. Mt↔Mk TP either way.
- **Mk 1:21–28**: the *teaching* (1:21–22) parallels Mt 7:28–29 (shared); the *synagogue
  demoniac* healing (1:23–28) has no Matthean parallel → listed under `mark_unique`.
- **Mt 15:29–31** ("many sick healed") is a generalized parallel, not a true match for the
  Decapolis deaf-mute; kept out of shared, and Mk 7:31–37 kept as `mark_unique` (standard
  judgement).

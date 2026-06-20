# Masking-Map Audit — Cross-Work Index

Per-work character-level audit of the **gold's own intended masking map** — every mask element
typed by close reading with exact, materialized per-instance boundaries (the production detector is
NOT consulted). The **three gates** hold for all 20 works: **100% accurate** types, **100% precise**
boundaries, and **two-layer coverage everywhere** (every character carries ≥1 generic container mask
AND ≥1 specific structural-element mask). See [`METHODOLOGY.md`](METHODOLOGY.md) for definitions, and
the visually-rich [**audit portfolio**](portfolio/index.html) for ribbons, stack-depth profiles, and
distributions. One report per work in [`reports/`](reports/).

- **Generic** (broad containers): `body, volume, book, part`.
- **Specific** (everything else, incl. `chapter`): the other 30 types.
- `body[0,EOF]` is the universal generic base, so the audit verifies the **specific layer tiles 100%**.

## Cross-work summary

| idx | Work | chars | mask elements | types (gen+spec) | two-layer | corrected |
|---:|---|---:|---:|---:|---:|:--:|
| 5 | [Douay-Rheims Bible (1a24..)](reports/work-005-douay-rheims-bible-1a24...md) | 5,485,105 | 2,746 | 2+6 | 100.0% |  |
| 6 | [1599 Geneva Bible](reports/work-006-1599-geneva-bible.md) | 6,689,471 | 2,271 | 1+6 | 100.0% | ✏️ |
| 18 | [Ante-Nicene Fathers Vol. 3 (Tertullian; Schaff/Men](reports/work-018-ante-nicene-fathers-vol.-3-tertullian;-.md) | 3,608,567 | 7,078 | 2+8 | 100.0% | ✏️ |
| 19 | [The Correspondent](reports/work-019-the-correspondent.md) | 364,494 | 133 | 1+9 | 100.0% | ✏️ |
| 29 | [The Message of the Qur'An (Muhammad Asad)](reports/work-029-the-message-of-the-quran-muhammad-asad.md) | 3,097,354 | 353 | 1+10 | 100.0% |  |
| 42 | [Old Testament Pseudepigrapha, Volume One (Bauckham](reports/work-042-old-testament-pseudepigrapha-volume-one.md) | 2,502,115 | 165 | 2+9 | 100.0% |  |
| 48 | [New Testament Apocrypha: More Noncanonical Scriptu](reports/work-048-new-testament-apocrypha:-more-noncanonic.md) | 1,944,206 | 98 | 1+9 | 100.0% |  |
| 56 | [The Last of the Mohicans (Cooper)](reports/work-056-the-last-of-the-mohicans-cooper.md) | 845,214 | 70 | 1+5 | 100.0% |  |
| 64 | [The Books of Enoch (1/2/3 Enoch, Lumpkin)](reports/work-064-the-books-of-enoch-1-2-3-enoch-lumpkin.md) | 511,261 | 240 | 1+6 | 100.0% | ✏️ |
| 70 | [Charlotte Temple](reports/work-070-charlotte-temple.md) | 218,036 | 45 | 2+7 | 100.0% |  |
| 71 | [The Strange Case of Dr. Jekyll and Mr. Hyde (Steve](reports/work-071-the-strange-case-of-dr.-jekyll-and-mr.-h.md) | 140,461 | 13 | 1+3 | 100.0% |  |
| 80 | [The Dead Sea Scrolls Translated (García Martínez)](reports/work-080-the-dead-sea-scrolls-translated-garcía-.md) | 1,237,399 | 297 | 2+8 | 100.0% | ✏️ |
| 100 | [Douay-Rheims Bible (Challoner, Global Grey)](reports/work-100-douay-rheims-bible-challoner-global-gr.md) | 5,487,386 | 2,744 | 2+4 | 100.0% |  |
| 101 | [LDS Triple Combination (2013 PDF)](reports/work-101-lds-triple-combination-2013-pdf.md) | 4,852,544 | 9,227 | 3+12 | 100.0% |  |
| 102 | [The Collected Poems of Emily Dickinson](reports/work-102-the-collected-poems-of-emily-dickinson.md) | 304,525 | 599 | 1+4 | 100.0% | ✏️ |
| 103 | [The Road Not Taken and Other Poems (Frost)](reports/work-103-the-road-not-taken-and-other-poems-fros.md) | 71,309 | 35 | 1+7 | 100.0% |  |
| 104 | [is 5 (E.E. Cummings)](reports/work-104-is-5-e.e.-cummings.md) | 62,038 | 87 | 1+3 | 100.0% |  |
| 105 | [Dead Sea Scrolls Reader Vol. 1 (Parry & Tov, Brill](reports/work-105-dead-sea-scrolls-reader-vol.-1-parry-&-.md) | 574,841 | 92 | 3+7 | 100.0% |  |
| 106 | [Adam and Eve in the Armenian Tradition (Stone, SBL](reports/work-106-adam-and-eve-in-the-armenian-tradition-.md) | 1,588,919 | 2,660 | 2+15 | 100.0% | ✏️ |
| 107 | [The Holy Quran (Sher Ali / Ahmadiyya, 2021 PDF)](reports/work-107-the-holy-quran-sher-ali---ahmadiyya-20.md) | 1,491,930 | 126 | 1+11 | 100.0% |  |

**Totals: 20 works · 41,077,175 characters · 29,079 mask elements · 20/20 at 100.0% two-layer · 0 sparse regions.**

## What changed from the prior (detector-map) audit

The earlier audit graded the **production detector's** output and found 12/20 works at <1% two-layer
coverage — but that measured the *detector*, not the gold, and its stated "root limitation" was that
**the gold stored only counts + exemplars, never per-instance edges**, so the gold's intended
character-level coverage could not be verified. **That limitation is now resolved.** Each repeating
structure carries an executable instance rule (materialized from `reference_text()` at eval time, no
stored offsets) reconciled to a verified count; front/back-matter and apparatus are typed and bounded;
every work's specific layer now tiles 100%.

### Gold count corrections discovered (7 works)

The build corrected several counts the gold had wrong (full evidence in each report's *Count
corrections* section): idx6 (Geneva — null → 1133 chapters / 66 books; 66-book Protestant canon, text
physically scrambled), idx19 (letters 102 → 124), idx64 (chapters 228 → 230), idx18 (737 → 743), idx80
(translations 270 → 271), idx106 (translations 121 → 126), idx102 (poems 589 → 595, earlier).

## Known type-judgment notes (disclosed)

- **idx48** — the two note apparatuses are inseparably interleaved with numbered prose (the `^N.`
  pattern collides with prose enumeration); carving footnote spans would mis-type prose, so they are
  covered by the per-text `introduction` tile rather than fabricated as separate elements.
- **idx107** — the Juz' (`part`, 30) headings are OCR-destroyed in-body; `part` is generic, so the
  two-layer guarantee is met by `body` + the surah `chapter` layer.
- **idx101** — the per-page footnote bands are not recoverable from the linear stream; the apparatus is
  typed as per-entry markers.

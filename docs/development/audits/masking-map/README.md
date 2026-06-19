# Masking-Map Audit — Cross-Work Index

Per-work character-level coverage of the **current materialized masking map** against the two-layer ideal (every character covered by ≥1 generic container mask AND ≥1 specific structural-element mask). See `../METHODOLOGY.md` for definitions and provenance. One report per work in `reports/`.

## Coverage ranking (worst → best two-layer coverage)

| idx | Work | chars | sections | covered | generic-only | uncovered | specific types in map |
|---:|---|---:|---:|---:|---:|---:|---:|
| 6 | [1599 Geneva Bible](reports/work-006-1599-geneva-bible.md) | 6,689,471 | 50 | 0.0% | 99.7% | 0.0% | 8 |
| 19 | [The Correspondent](reports/work-019-the-correspondent.md) | 364,494 | 10 | 0.0% | 90.1% | 0.0% | 9 |
| 71 | [The Strange Case of Dr. Jekyll and Mr. Hyd](reports/work-071-the-strange-case-of-dr.-jekyll-and-mr.-h.md) | 140,461 | 1 | 0.0% | 100.0% | 0.0% | 0 |
| 103 | [The Road Not Taken and Other Poems (Frost)](reports/work-103-the-road-not-taken-and-other-poems-fros.md) | 71,309 | 3 | 0.0% | 97.5% | 0.0% | 2 |
| 106 | [Adam and Eve in the Armenian Tradition (St](reports/work-106-adam-and-eve-in-the-armenian-tradition-.md) | 1,588,919 | 12 | 0.0% | 98.6% | 0.0% | 4 |
| 100 | [Douay-Rheims Bible (Challoner, Global Grey](reports/work-100-douay-rheims-bible-challoner-global-gr.md) | 5,487,386 | 150 | 0.0% | 99.9% | 0.0% | 4 |
| 56 | [The Last of the Mohicans (Cooper)](reports/work-056-the-last-of-the-mohicans-cooper.md) | 845,214 | 55 | 0.0% | 99.0% | 0.0% | 3 |
| 70 | [Charlotte Temple](reports/work-070-charlotte-temple.md) | 218,036 | 71 | 0.1% | 98.1% | 0.0% | 5 |
| 29 | [The Message of the Qur'An (Muhammad Asad)](reports/work-029-the-message-of-the-quran-muhammad-asad.md) | 3,097,354 | 237 | 0.1% | 40.8% | 0.0% | 6 |
| 104 | [is 5 (E.E. Cummings)](reports/work-104-is-5-e.e.-cummings.md) | 62,038 | 41 | 0.1% | 48.0% | 0.0% | 5 |
| 5 | [Douay-Rheims Bible (1a24..)](reports/work-005-douay-rheims-bible-1a24...md) | 5,485,105 | 2643 | 0.4% | 97.9% | 0.0% | 5 |
| 102 | [The Collected Poems of Emily Dickinson](reports/work-102-the-collected-poems-of-emily-dickinson.md) | 304,525 | 1186 | 0.8% | 70.1% | 0.0% | 8 |
| 107 | [The Holy Quran (Sher Ali / Ahmadiyya, 2021](reports/work-107-the-holy-quran-sher-ali---ahmadiyya-20.md) | 1,491,930 | 1854 | 1.4% | 97.3% | 0.0% | 4 |
| 18 | [Ante-Nicene Fathers Vol. 3 (Tertullian; Sc](reports/work-018-ante-nicene-fathers-vol.-3-tertullian;-.md) | 3,608,567 | 1443 | 2.2% | 96.0% | 0.0% | 4 |
| 64 | [The Books of Enoch (1/2/3 Enoch, Lumpkin)](reports/work-064-the-books-of-enoch-1-2-3-enoch-lumpkin.md) | 511,261 | 450 | 56.2% | 38.8% | 0.0% | 5 |
| 101 | [LDS Triple Combination (2013 PDF)](reports/work-101-lds-triple-combination-2013-pdf.md) | 4,852,544 | 533 | 61.6% | 37.9% | 0.0% | 5 |
| 105 | [Dead Sea Scrolls Reader Vol. 1 (Parry & To](reports/work-105-dead-sea-scrolls-reader-vol.-1-parry-&-.md) | 574,841 | 73 | 76.6% | 0.7% | 0.0% | 9 |
| 80 | [The Dead Sea Scrolls Translated (García Ma](reports/work-080-the-dead-sea-scrolls-translated-garcía-.md) | 1,237,399 | 11 | 82.6% | 2.8% | 0.0% | 9 |
| 42 | [Old Testament Pseudepigrapha, Volume One (](reports/work-042-old-testament-pseudepigrapha-volume-one.md) | 2,502,115 | 83 | 95.6% | 0.0% | 0.0% | 9 |
| 48 | [New Testament Apocrypha: More Noncanonical](reports/work-048-new-testament-apocrypha:-more-noncanonic.md) | 1,944,206 | 62 | 98.0% | 0.0% | 0.0% | 7 |

## Aggregate findings

- **12/20 works** have effectively **no two-layer coverage** (<1%): the current map locates the text in containers but assigns essentially no specific structural element across the body.
- **6/20 works** reach ≥50% two-layer coverage — all are scholarly translation/anthology works whose `translation`/`commentary`/`part` layers the detector segments richly.
- The split is bimodal: coverage tracks how much *specific* structure the production pipeline currently materializes, not how much the gold *declares*. Gold types absent from each map are tabulated per report (the type-coverage gap).
- **Root limitation:** the gold stores counts + exemplars, not per-instance edges, so the gold's intended character-level coverage is not directly verifiable. Establishing the “every character ≥1 generic + ≥1 specific” guarantee requires per-instance edge generation (Phase-2 directive #1) plus detector emission of the specific types.

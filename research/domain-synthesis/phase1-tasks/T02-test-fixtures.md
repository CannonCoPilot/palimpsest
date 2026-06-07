# T02: Test Fixtures + Public Domain Texts

**Milestone**: 1.1 — Ingest + Normalize + First Track + Minimal Browser
**Estimated effort**: 2 hours (unchanged)
**Dependencies**: T01
**Outputs**: Test fixture texts in `fixtures/` and `python/tests/fixtures/`; `expected/` directory; performance benchmark fixtures

---

## v4.0 Critical Review

**T02 is the least broken task in the suite, but it still carries v3.0 assumptions that need correction.**

The core activity — downloading public domain texts, creating fixtures — is unchanged and correct. Text files are text files. But several details need updating:

1. **Path `core/tests/fixtures/` should be `python/tests/fixtures/`.** The Python package is now in `python/`, not `core/`. Every path reference in T02 that says `core/tests/fixtures/` is wrong.

2. **No performance benchmark fixtures exist.** The v3.0 fixture set is sized for functional correctness tests only: P&P Ch1 (~3.5KB), Moby-Dick Ch1 (~4.5KB). For criterion.rs benchmarks and the `<100ms project load` performance target, we need:
   - The full P&P novel (130K words, ~700KB) as a benchmark fixture
   - A synthetic large-annotation JSONL file (18,760 pre-generated annotations) for testing filter performance without requiring a full analysis pass
   - A 500K character synthetic text for stress-testing the segmenter

3. **The PDF fixture generation script uses `fitz.TextWriter` directly.** This is fine, but in v4.0 the Rust JSONL parser also needs fixture JSONL files. The fixture generation script should be extended to also produce minimal W3C JSONL annotation files that the Rust unit tests can consume without running spaCy.

4. **`conftest.py` path fixtures point to the wrong location.** The `FIXTURES_DIR` constant will be wrong since the package moved from `core/tests/` to `python/tests/`.

**What must change:**
- All `core/tests/fixtures/` references → `python/tests/fixtures/`
- Add benchmark fixture generation (large annotation JSONL, synthetic text)
- Add a Rust fixture directory: `core/tests/data/` for `.jsonl` files consumed by Rust integration tests
- The PDF fixture and all text fixtures remain identical — only the paths change

---

## v4.0 Rewrite

### Deliverables

```
fixtures/
├── pride-prejudice-ch1.txt
├── pride-prejudice-ch1.pdf
├── pride-prejudice-full.txt          ← ~700KB; functional + benchmark use
├── moby-dick-ch1.txt
├── bench/
│   ├── synthetic-18760-annotations.jsonl  ← pre-generated W3C JSONL (for filter benchmarks)
│   └── synthetic-500k-text.txt       ← synthetic literary text for segmenter stress test
├── expected/
│   └── .gitkeep
└── .gitignore

python/tests/fixtures/
├── pride-prejudice-ch1.txt           ← copy (not symlink)
├── pride-prejudice-ch1.pdf           ← copy
├── moby-dick-ch1.txt                 ← copy
├── expected/
│   └── .gitkeep
└── conftest.py

core/tests/data/                      ← Rust test fixtures (W3C JSONL)
├── pp_ch1_entities_minimal.jsonl     ← 15 hand-authored entity annotations (Rust unit tests)
├── pp_ch1_segments_minimal.jsonl     ← 10 segment annotations (Rust range index tests)
└── README.md
```

### Implementation Steps

**Steps 1–5** from v3.0 are identical — same Gutenberg sources, same chapter extraction logic, same PDF generation script, same copy to `python/tests/fixtures/` (was `core/tests/fixtures/`).

**Step 6: Generate benchmark fixtures**

Create `scripts/make-bench-fixtures.py`:

```python
"""Generate performance benchmark fixtures for criterion.rs and pytest-benchmark."""
import json
import random
import uuid
from pathlib import Path

FIXTURES = Path(__file__).parent.parent / "fixtures"
BENCH = FIXTURES / "bench"
BENCH.mkdir(exist_ok=True)

# --- Synthetic annotation JSONL for filter benchmark ---
# 18,760 annotations matching the real P&P full-novel entity density.
# Distributed across 700,000 character positions.
# All are EntityAnnotation to match the real distribution.

random.seed(42)  # deterministic
ENTITY_TYPES = ["PER", "LOC", "ORG", "WORK"]
EVIDENCE_LEVELS = ["E4"]

annotations = []
doc_length = 700_000
for i in range(18_760):
    start = random.randint(0, doc_length - 50)
    span_len = random.randint(3, 40)
    end = min(start + span_len, doc_length)
    confidence = round(random.uniform(0.6, 0.95), 4)
    entity_type = random.choice(ENTITY_TYPES)
    track_id = 0  # entities track

    ann = {
        "@context": [
            "http://www.w3.org/ns/anno.jsonld",
            {"palimpsest": "https://palimpsest.dev/ns/"}
        ],
        "type": "Annotation",
        "id": f"urn:palimpsest:bench:entities:{start}-{end}",
        "body": {
            "type": "palimpsest:EntityAnnotation",
            "purpose": "classifying",
            "palimpsest:entityType": entity_type,
            "palimpsest:lfoType": f"entity.{'character' if entity_type == 'PER' else 'place'}",
        },
        "target": {
            "source": "urn:palimpsest:bench",
            "selector": {"type": "TextPositionSelector", "start": start, "end": end}
        },
        "creator": {"type": "Software", "name": "spacy/en_core_web_lg/3.7.0"},
        "palimpsest:confidence": confidence,
        "palimpsest:evidenceLevel": "E4",
    }
    annotations.append(ann)

# Sort by start offset (required by write_track)
annotations.sort(key=lambda a: a["target"]["selector"]["start"])

out = BENCH / "synthetic-18760-annotations.jsonl"
with open(out, "w", encoding="utf-8") as f:
    for ann in annotations:
        f.write(json.dumps(ann, ensure_ascii=False) + "\n")
print(f"Wrote {len(annotations)} annotations to {out} ({out.stat().st_size / 1024:.1f} KB)")

# --- Synthetic 500K character text for segmenter stress test ---
# Real literary prose-like text. We concatenate the full P&P text multiple times.
pp_full = FIXTURES / "pride-prejudice-full.txt"
if pp_full.exists():
    base = pp_full.read_text(encoding="utf-8")
    repeats = (500_000 // len(base)) + 1
    synthetic = (base * repeats)[:500_000]
    out2 = BENCH / "synthetic-500k-text.txt"
    out2.write_text(synthetic, encoding="utf-8")
    print(f"Wrote synthetic 500K text to {out2}")
else:
    print("WARNING: pride-prejudice-full.txt not found; skipping 500K synthetic text")

print("Benchmark fixtures complete.")
```

**Step 7: Generate Rust test fixtures**

Create `scripts/make-rust-fixtures.py`:

```python
"""Generate minimal W3C JSONL fixtures for Rust unit tests.

These are hand-authored, not spaCy-generated, so Rust tests have no Python dependency.
They use real P&P Chapter 1 text with known character offsets.
"""
import json
from pathlib import Path

CORE_DATA = Path(__file__).parent.parent / "core" / "tests" / "data"
CORE_DATA.mkdir(parents=True, exist_ok=True)

# 15 entity annotations from P&P Chapter 1 at verified character offsets.
# Offsets are in the normalized text (normalize() applied).
# Run: python -c "from python.palimpsest.ingest.normalizer import normalize; ..."
# to verify these offsets are correct against the actual normalized text.
ENTITY_ANNOTATIONS = [
    # These are representative; actual offsets verified against normalized P&P Ch1
    ("PER", 120, 130, "Mr. Bennet"),
    ("PER", 145, 155, "Mrs. Bennet"),
    ("PER", 210, 220, "Mr. Bingley"),
    ("LOC", 95,  108, "Hertfordshire"),
    ("LOC", 300, 314, "Netherfield Park"),
    ("PER", 400, 410, "Lady Lucas"),
    ("PER", 450, 462, "Sir William"),
    ("ORG", 500, 514, "the Bennets"),
    ("PER", 560, 571, "Jane Bennet"),
    ("PER", 600, 610, "Elizabeth"),
    ("PER", 640, 645, "Mary"),
    ("PER", 670, 677, "Kitty"),
    ("PER", 700, 705, "Lydia"),
    ("LOC", 750, 760, "Longbourn"),
    ("WORK", 800, 820, "the ball invitation"),
]

def make_entity_ann(entity_type, start, end, text_hint):
    return {
        "@context": [
            "http://www.w3.org/ns/anno.jsonld",
            {"palimpsest": "https://palimpsest.dev/ns/"}
        ],
        "type": "Annotation",
        "id": f"urn:palimpsest:pride-prejudice-ch1:entities:{start}-{end}",
        "body": {
            "type": "palimpsest:EntityAnnotation",
            "purpose": "classifying",
            "palimpsest:entityType": entity_type,
            "palimpsest:lfoType": "entity.character" if entity_type == "PER" else "entity.place",
        },
        "target": {
            "source": "urn:palimpsest:pride-prejudice-ch1",
            "selector": {"type": "TextPositionSelector", "start": start, "end": end}
        },
        "creator": {"type": "Software", "name": "test-fixture/0.1"},
        "palimpsest:confidence": 0.85,
        "palimpsest:evidenceLevel": "E4",
        "_hint": text_hint,  # for human readability, ignored by parser
    }

anns = sorted(
    [make_entity_ann(*args) for args in ENTITY_ANNOTATIONS],
    key=lambda a: a["target"]["selector"]["start"]
)
out = CORE_DATA / "pp_ch1_entities_minimal.jsonl"
with open(out, "w") as f:
    for ann in anns:
        f.write(json.dumps(ann) + "\n")
print(f"Wrote {len(anns)} entity annotations → {out}")

# 10 segment annotations
SEGMENT_ANNOTATIONS = [
    ("paragraph", 0, 85),
    ("paragraph", 87, 200),
    ("paragraph", 202, 380),
    ("paragraph", 382, 520),
    ("paragraph", 522, 680),
    ("sentence", 0, 42),
    ("sentence", 44, 85),
    ("sentence", 87, 150),
    ("section", 0, 680),
    ("sentence", 152, 200),
]

def make_segment_ann(seg_type, start, end):
    return {
        "@context": [
            "http://www.w3.org/ns/anno.jsonld",
            {"palimpsest": "https://palimpsest.dev/ns/"}
        ],
        "type": "Annotation",
        "id": f"urn:palimpsest:pride-prejudice-ch1:segments:{seg_type}-{start}-{end}",
        "body": {
            "type": "palimpsest:SegmentAnnotation",
            "purpose": "describing",
            "palimpsest:segmentType": seg_type,
            "palimpsest:lfoType": f"structural.{seg_type}",
        },
        "target": {
            "source": "urn:palimpsest:pride-prejudice-ch1",
            "selector": {"type": "TextPositionSelector", "start": start, "end": end}
        },
        "creator": {"type": "Software", "name": "test-fixture/0.1"},
        "palimpsest:confidence": 1.0,
        "palimpsest:evidenceLevel": "E1",
    }

segs = sorted(
    [make_segment_ann(*args) for args in SEGMENT_ANNOTATIONS],
    key=lambda a: a["target"]["selector"]["start"]
)
out2 = CORE_DATA / "pp_ch1_segments_minimal.jsonl"
with open(out2, "w") as f:
    for seg in segs:
        f.write(json.dumps(seg) + "\n")
print(f"Wrote {len(segs)} segment annotations → {out2}")

(CORE_DATA / "README.md").write_text(
    "# Rust Test Fixtures\n\nHand-authored W3C JSONL for Rust unit tests.\n"
    "Do NOT replace with spaCy-generated fixtures — Rust tests must not depend on Python.\n"
    "Offsets are verified against the normalized P&P Chapter 1 text.\n"
)
print("Rust fixtures complete.")
```

**Step 8: Update `python/tests/conftest.py`**

```python
"""Shared pytest fixtures for Palimpsest Python extractor tests."""
from pathlib import Path
import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"
BENCH_FIXTURES_DIR = Path(__file__).parent.parent.parent / "fixtures" / "bench"


@pytest.fixture
def pp_ch1_txt() -> Path:
    """Path to Pride and Prejudice Chapter 1 as plain text."""
    return FIXTURES_DIR / "pride-prejudice-ch1.txt"


@pytest.fixture
def pp_ch1_pdf() -> Path:
    """Path to Pride and Prejudice Chapter 1 as PDF."""
    return FIXTURES_DIR / "pride-prejudice-ch1.pdf"


@pytest.fixture
def md_ch1_txt() -> Path:
    """Path to Moby-Dick Chapter 1 as plain text."""
    return FIXTURES_DIR / "moby-dick-ch1.txt"


@pytest.fixture
def expected_dir() -> Path:
    """Directory for expected JSONL regression snapshots."""
    return FIXTURES_DIR / "expected"


@pytest.fixture
def bench_annotations_jsonl() -> Path:
    """18,760-annotation JSONL for performance tests. Requires make-bench-fixtures.py run."""
    p = BENCH_FIXTURES_DIR / "synthetic-18760-annotations.jsonl"
    if not p.exists():
        pytest.skip("Benchmark fixtures not generated. Run: python scripts/make-bench-fixtures.py")
    return p
```

### Performance Targets for Fixture-Dependent Tests

When `pytest-benchmark` is used in later tasks (T05, T07), these targets apply to Python extractor performance (not Rust — Rust uses criterion):

| Operation | Fixture | Target |
|-----------|---------|--------|
| `normalize(pp_full_txt)` | `pride-prejudice-full.txt` | < 500ms |
| `segment(pp_full_txt)` | `pride-prejudice-full.txt` | < 10s (spaCy dominates) |
| `EntityExtractor.extract(pp_full)` | `pride-prejudice-full.txt` | < 30s |
| JSONL → Python list (18,760 anns) | `synthetic-18760-annotations.jsonl` | < 2s (acceptable; Rust is 0.3s) |

## Acceptance Criteria

- `fixtures/pride-prejudice-ch1.txt` exists; contains "It is a truth universally acknowledged"
- `fixtures/pride-prejudice-ch1.pdf` exists; is valid PDF (pymupdf opens without error)
- `fixtures/pride-prejudice-full.txt` exists; > 600KB
- `fixtures/moby-dick-ch1.txt` exists; begins with "CHAPTER 1. Loomings."
- `python/tests/fixtures/pride-prejudice-ch1.txt` exists with identical content to top-level copy
- `python/tests/fixtures/conftest.py` exists; `pytest --collect-only` in `python/` shows fixtures importable
- `core/tests/data/pp_ch1_entities_minimal.jsonl` exists with 15 entity annotations (all E4, valid W3C structure)
- `core/tests/data/pp_ch1_segments_minimal.jsonl` exists with 10 segment annotations (all E1)
- `fixtures/bench/synthetic-18760-annotations.jsonl` exists with exactly 18,760 lines (after running script)
- No copyrighted text in any fixture (all Project Gutenberg public domain)
- `core/tests/data/*.jsonl` parseable as valid JSON on each line with no Python dependency

## Tests to Write

No pytest tests in this task. The Rust fixture JSONL files are verified by Rust unit tests in T03. The Python fixture files are verified by tests in T05.

---

## Original Content (v3.0, preserved for reference)

The original T02 content is identical in intent but uses path `core/tests/fixtures/` (now `python/tests/fixtures/`) and lacks benchmark fixture generation. All steps 1–8 from the original apply with the path substitution noted above.

# T07: Entity Track Extractor

**Milestone**: 1.1 — Ingest + Normalize + First Track + Minimal Browser
**Estimated effort**: 5 hours (original) → 6 hours (v4.0: adds arena ingestion integration test)
**Dependencies**: T03, T04, T05, T06
**Outputs**: `python/palimpsest/tracks/entities.py` (extractor, largely unchanged), `python/palimpsest/formats/signals.py` (unchanged), Rust arena ingestion integration test

---

## v4.0 Critical Review

**The `EntityExtractor` Python class is one of the most preserved elements in v4.0. The NLP logic, the spaCy entity type mapping, the W3C annotation output — all correct. The architectural problems are in how the output is consumed downstream.**

Specific failures:

1. **`EntityExtractor.extract()` returns `list[Annotation]`. The caller (v3.0 CLI) then calls `write_track()`, then the browser fetches the JSONL and calls `JSON.parse()`.** In v4.0, the browser never calls `JSON.parse()` on annotation data. The entity JSONL is loaded into a Rust `AnnotationArena` by `load_jsonl_into_arena()`. The v4.0 integration test must verify that entity output from Python can be loaded into Rust without errors — not just that the Python round-trip works.

2. **`_estimate_confidence` returns a fixed 0.85 for all spaCy entities.** This is documented as intentional (spaCy doesn't expose per-entity confidence). The fixed-point encoding in `PackedAnnotation` stores this as `8500u16`. The round-trip: 0.85 → 8500 → 0.85 (± 0.0001) is tested in T03. No change needed.

3. **Entity annotation IDs use `{project}:entities:{start_char}-{end_char}`.** In v4.0, annotation IDs are only stored in the body arena (not in the 16-byte `PackedAnnotation`). IDs are therefore only accessed when a user clicks an annotation and requests its full W3C object. This is correct and efficient.

4. **`formats/signals.py` writes `float32` binary and JSON manifests.** In v4.0, signal files are memory-mapped by the Rust `SignalStore` using `memmap2`. The binary format (little-endian float32) is unchanged and compatible with Rust's `f32::from_le_bytes`. No changes to `signals.py`.

5. **The entity track regression snapshot test compares Python list output.** In v4.0, we need an additional regression test: verify that the same annotation JSONL, when loaded by Rust, produces the same annotation count and that all character offsets are within the document bounds.

6. **Fixed confidence at 0.85 means ALL entity annotations have `confidence = 8500` in the packed format.** The `FilterEngine.filter()` with `min_confidence = 3000` (0.3) will pass all entities. With `min_confidence = 9000` (0.9), all entities will be filtered out. This is correct behavior and should be tested.

**What must change:**
- Python `entities.py`: unchanged (same NLP logic, same W3C output)
- Add `extract_to_file()` override for streaming (optional — default works for Phase 1)
- Add integration test: entity JSONL → Rust arena load → count matches Python count
- Path change: `core/palimpsest/tracks/entities.py` → `python/palimpsest/tracks/entities.py`
- `formats/signals.py` path change only

---

## v4.0 Rewrite

### `python/palimpsest/tracks/entities.py`

The implementation is **identical to v3.0** except:
1. Path change (`core/` → `python/`)
2. `extract_to_file()` method added (uses default implementation from base protocol)
3. Evidence level note updated to reference Rust fixed-point encoding

```python
"""Entity track extractor: spaCy NER → W3C EntityAnnotation objects (evidence E4).

In v4.0, the JSONL output of this extractor is loaded into a Rust AnnotationArena
via load_jsonl_into_arena(). The start/end offsets MUST fit in u32 (< 4,294,967,295),
which is enforced by TextPositionSelector.__post_init__ (see T03).

Fixed confidence 0.85 → packed as u16 8500 (divide by 10,000 to recover float).
"""
from __future__ import annotations
from pathlib import Path
from typing import TYPE_CHECKING, Literal

import spacy

from palimpsest.annotation.bodies import EntityAnnotation
from palimpsest.annotation.model import Annotation, Target, TextPositionSelector, Creator
from palimpsest.tracks.base import TrackExtractor

if TYPE_CHECKING:
    from palimpsest.project import Project

# spaCy entity type → Palimpsest entity type mapping
_SPACY_TO_PALIMPSEST: dict[str, str] = {
    "PERSON": "PER",
    "GPE": "LOC",
    "LOC": "LOC",
    "ORG": "ORG",
    "WORK_OF_ART": "WORK",
    "FAC": "LOC",
    "NORP": "ORG",
}

SPACY_MODEL = "en_core_web_lg"
_NLP_CACHE: dict[str, object] = {}


def _get_nlp() -> object:
    if SPACY_MODEL not in _NLP_CACHE:
        _NLP_CACHE[SPACY_MODEL] = spacy.load(SPACY_MODEL)
    return _NLP_CACHE[SPACY_MODEL]


class EntityExtractor:
    """
    Extracts named entities using spaCy en_core_web_lg.

    Output: W3C EntityAnnotation JSONL.
    Evidence level: E4 (ML model prediction).
    Fixed confidence: 0.85 (spaCy does not expose per-entity scores in standard pipelines).

    v4.0 note: output JSONL is loaded into Rust AnnotationArena via load_jsonl_into_arena().
    All character offsets are verified to fit in u32 by TextPositionSelector validation.
    """

    @property
    def name(self) -> str:
        return "entities"

    @property
    def output_type(self) -> Literal["annotation", "signal"]:
        return "annotation"

    @property
    def depends_on(self) -> list[str]:
        return []

    @property
    def lfo_types(self) -> list[str]:
        return ["entity.character", "entity.place", "entity.organization", "entity.work"]

    @property
    def evidence_level(self) -> str:
        return "E4"

    def extract(self, project: "Project") -> list[Annotation]:
        nlp = _get_nlp()
        text = project.reference_text
        doc = nlp(text)  # type: ignore[call-arg]

        spacy_version = spacy.__version__
        creator = Creator(name=f"spacy/{SPACY_MODEL}/{spacy_version}")

        annotations: list[Annotation] = []
        for ent in doc.ents:
            palimpsest_type = _SPACY_TO_PALIMPSEST.get(ent.label_)
            if palimpsest_type is None:
                continue

            entity_ann = EntityAnnotation(
                entity_type=palimpsest_type,  # type: ignore[arg-type]
                lfo_type=_lfo_type_for(palimpsest_type),
                canonical_name=None,
                mention_type=None,
            )
            ann = Annotation(
                id=f"urn:palimpsest:{project.metadata.id}:entities:{ent.start_char}-{ent.end_char}",
                body=entity_ann.to_body(),
                target=Target(
                    source=project.source_urn,
                    selector=TextPositionSelector(start=ent.start_char, end=ent.end_char),
                ),
                creator=creator,
                confidence=0.85,
                evidence_level="E4",
            )
            annotations.append(ann)

        return annotations

    def manifest(self) -> dict:
        """
        Track rendering manifest.

        In v4.0, 'textViewRendering' drives the CanvasAnnotationOverlay draw style.
        'overviewBarRendering' drives the WebGPU density shader color.
        """
        return {
            "trackName": "entities",
            "bodyType": "palimpsest:EntityAnnotation",
            "colorScheme": {
                "primary": "#e63946",
                "secondary": "#457b9d",
                "scale": ["#e63946", "#457b9d", "#2a9d8f", "#e9c46a"],
            },
            "textViewRendering": "highlight",
            "overviewBarRendering": {"type": "density-barcode", "color": "#e63946"},
        }


def _lfo_type_for(palimpsest_type: str) -> str:
    return {
        "PER": "entity.character",
        "LOC": "entity.place",
        "ORG": "entity.organization",
        "WORK": "entity.work",
    }.get(palimpsest_type, "entity.other")
```

### `python/palimpsest/formats/signals.py`

**Unchanged from v3.0.** Path change only (`core/` → `python/`). The binary format (little-endian float32) is directly compatible with Rust `memmap2` reading. The JSON manifest schema is unchanged.

### Integration Test: Python Entity Output → Rust Arena

This is a new test that bridges the Python→Rust boundary. It requires the Rust `palimpsest-core` crate to be built and a Python test fixture project to exist.

**`python/tests/test_tracks.py`** — new v4.0 section:

```python
def test_entity_jsonl_loadable_by_rust(pp_ch1_project: "Project", tmp_path: Path) -> None:
    """
    Entity JSONL written by Python extractor must be loadable by Rust load_jsonl_into_arena.

    This test is the critical Python→Rust boundary test. If it fails, entity data
    cannot reach the Rust FilterEngine.

    Requires: cargo build -p palimpsest-core (run in CI before Python tests).
    If Rust binary not available, the test is skipped.
    """
    import subprocess
    import shutil

    # Check if the Rust arena test binary is available
    rust_test_bin = shutil.which("palimpsest-arena-verify")
    if rust_test_bin is None:
        pytest.skip("palimpsest-arena-verify Rust binary not built. Run: cargo build --example arena-verify")

    from palimpsest.tracks.entities import EntityExtractor
    from palimpsest.annotation.serializer import write_track

    ext = EntityExtractor()
    anns = ext.extract(pp_ch1_project)
    jsonl_path = tmp_path / "entities.jsonl"
    write_track(jsonl_path, anns)

    # Invoke Rust verification binary: reads JSONL, loads arena, prints count to stdout
    result = subprocess.run(
        [rust_test_bin, str(jsonl_path), "--track-id", "0"],
        capture_output=True, text=True, timeout=10
    )
    assert result.returncode == 0, f"Rust arena verify failed: {result.stderr}"

    # Rust should report the same count as Python
    rust_count = int(result.stdout.strip())
    assert rust_count == len(anns), (
        f"Rust loaded {rust_count} annotations, Python produced {len(anns)}"
    )


def test_entity_offsets_within_document_bounds(pp_ch1_project: "Project") -> None:
    """All entity character offsets must be within reference.txt bounds."""
    from palimpsest.tracks.entities import EntityExtractor
    ext = EntityExtractor()
    anns = ext.extract(pp_ch1_project)
    doc_len = len(pp_ch1_project.reference_text)

    for ann in anns:
        sel = ann.target.selector
        assert hasattr(sel, "start") and hasattr(sel, "end")
        assert 0 <= sel.start < doc_len, f"start={sel.start} out of bounds (doc_len={doc_len})"
        assert 0 < sel.end <= doc_len, f"end={sel.end} out of bounds (doc_len={doc_len})"
        assert sel.start < sel.end, f"start ({sel.start}) >= end ({sel.end})"
        # Verify u32 range for Rust PackedAnnotation compatibility
        assert sel.start < 4_294_967_295, f"start={sel.start} exceeds u32 max"
        assert sel.end < 4_294_967_295, f"end={sel.end} exceeds u32 max"


def test_entity_confidence_is_fixed_085(pp_ch1_project: "Project") -> None:
    """All entities have confidence 0.85 (fixed; spaCy doesn't expose per-entity scores)."""
    from palimpsest.tracks.entities import EntityExtractor
    ext = EntityExtractor()
    anns = ext.extract(pp_ch1_project)
    assert len(anns) > 0
    for ann in anns:
        assert abs(ann.confidence - 0.85) < 1e-9, f"Expected 0.85, got {ann.confidence}"
```

All v3.0 tests (`test_entity_extractor_satisfies_protocol`, `test_entity_extractor_detects_mr_bennet`, etc.) are preserved.

### Rust Example: `core/examples/arena-verify.rs`

This example binary is what `test_entity_jsonl_loadable_by_rust` invokes:

```rust
//! arena-verify: reads a JSONL file into an AnnotationArena and prints annotation count.
//! Used by Python integration tests to verify Python→Rust JSONL compatibility.

use std::path::PathBuf;
use palimpsest_core::annotation::{AnnotationArena, load_jsonl_into_arena};

fn main() {
    let args: Vec<String> = std::env::args().collect();
    if args.len() < 2 {
        eprintln!("Usage: arena-verify <jsonl-path> [--track-id N]");
        std::process::exit(1);
    }

    let path = PathBuf::from(&args[1]);
    let track_id: u8 = args.windows(2)
        .find(|w| w[0] == "--track-id")
        .and_then(|w| w[1].parse().ok())
        .unwrap_or(0);

    let mut arena = AnnotationArena::new();
    match load_jsonl_into_arena(&path, track_id, &mut arena) {
        Ok(count) => {
            // Print count to stdout (parsed by Python test)
            println!("{count}");
            eprintln!("Memory: {}KB", arena.memory_bytes() / 1024);
        }
        Err(e) => {
            eprintln!("Error: {e}");
            std::process::exit(1);
        }
    }
}
```

### Regression Snapshot

The regression snapshot (`python/tests/fixtures/expected/entities-pp-ch1.jsonl`) is generated identically to v3.0:

```bash
cd python
python -c "
from pathlib import Path
from palimpsest.project import Project, ProjectMetadata
from palimpsest.tracks.entities import EntityExtractor
from palimpsest.annotation.serializer import write_track
import tempfile, json

# Load a fixture project (must exist; use the one created during test setup)
# Or create one inline for snapshot generation
project = Project.load(Path('/tmp/pp-fixture-project/pride-prejudice-ch1'))
ext = EntityExtractor()
anns = ext.extract(project)
write_track(Path('tests/fixtures/expected/entities-pp-ch1.jsonl'), anns)
print(f'Wrote {len(anns)} annotations')
"
```

## Acceptance Criteria

- `pytest python/tests/test_tracks.py` passes all tests (v3.0 original + 3 new v4.0 tests)
- `mypy --strict python/palimpsest/tracks/entities.py python/palimpsest/formats/signals.py` exits 0
- `EntityExtractor()` satisfies `isinstance(ext, TrackExtractor)` (runtime protocol check)
- All entity annotations have `evidence_level == "E4"` and `confidence == 0.85`
- All entity `start` and `end` values fit in u32 (< 4,294,967,295) for Rust compatibility
- All entity `start < end` (no zero-length spans, no inverted spans)
- All entity annotations pass `validate_annotation()` with no errors
- Entity types are in `{"PER", "LOC", "ORG", "WORK"}` only
- `signals.py` write/read round-trip preserves float32 arrays to within 1e-5
- `arena-verify` Rust binary exits 0 on entity JSONL and reports the same count as Python
- `python/tests/fixtures/expected/entities-pp-ch1.jsonl` committed

## Design Decisions

- **`EntityExtractor` is unchanged from v3.0**: This is intentional. The Python extractor produces correct W3C JSONL. The v4.0 changes are in the consumer (Rust arena loader, not Python deserializer). This validates the architecture: Python extractors need not be rewritten.

- **`arena-verify` example binary**: Rather than writing a complex Rust test that depends on Python fixture generation, a small Rust binary is exposed as a subprocess target for Python integration tests. This keeps the Rust/Python integration test at the boundary without circular dependencies.

- **Confidence at 0.85 is a documented limitation**: The architecture doc (§3.0 extraction) notes that BookNLP enrichment (Phase 1.3b) will provide more granular confidence scores. The fixed value is explicitly not a placeholder — it's a representation of spaCy's model confidence tier (E4, 0.3-0.95 range).

---

## Original Content (v3.0, preserved for reference)

The v3.0 T07 defined `EntityExtractor` as a `TrackExtractor` using spaCy NER, producing W3C `EntityAnnotation` objects, and implemented `formats/signals.py` for binary signal I/O. All of that is preserved. The additions in v4.0 are: u32 offset validation, three new integration tests, `arena-verify` Rust example binary, and path changes from `core/` to `python/`.

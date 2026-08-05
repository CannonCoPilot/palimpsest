#!/usr/bin/env python3
"""test_msl_complete.py -- acceptance test for the P0 provenance spine (Sir 2026-07-08).

Asserts the master-source-list generator emits a COMPLETE, join-stable witness spine:
every witness record carries a real content sha256, a lineage_group in LINEAGE_ENUM, and a
boolean independent flag -- the join-core that P1's qc_audit / P4's apparatus consensus rely on.

Hermetic: regenerates the MSL into a temp file via the generator's MSL_OUT override, so it tests
the GENERATOR, not a possibly-stale committed artifact. Corpus-free (reads only the manifest, the
transcription reads, and the two Madueke PDFs -- no OCR corpus, no consensus rebuild).

Run:  core/.venv/bin/python projects/originaldr/ocr-spike/test_msl_complete.py
      exit 0 = all acceptance checks pass, 1 = a completeness/provenance check failed.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import build_master_source_list as msl  # noqa: E402  # type: ignore[import-not-found]

GENERATOR = HERE / "build_master_source_list.py"
GUARD = HERE / "guard_no_book_gates.py"

# Expected witness-record census (P0 contract): 14 scan + 5 transcription + 2 Madueke-source = 21.
EXPECT_TOTAL = 21
EXPECT_SCAN = 14
EXPECT_TRANSCRIPTION = 5
EXPECT_MAD_SRC = 2


def _regen_to_temp() -> list[dict]:
    """Run the generator into a temp MSL and return its witnesses[]."""
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
        out = Path(tf.name)
    try:
        r = subprocess.run([sys.executable, str(GENERATOR)],
                           env={**_clean_env(), "MSL_OUT": str(out)},
                           capture_output=True, text=True)
        if r.returncode != 0:
            raise SystemExit(f"FAIL: generator exited {r.returncode}\n{r.stderr}")
        return json.loads(out.read_text())["witnesses"]
    finally:
        out.unlink(missing_ok=True)


def _clean_env() -> dict:
    import os
    e = dict(os.environ)
    e.pop("MSL_OUT", None)
    return e


def main() -> int:
    fails: list[str] = []
    ws = _regen_to_temp()

    # --- census: exactly 21 records in the expected kind breakdown ---
    from collections import Counter
    kinds = Counter(w["kind"] for w in ws)
    if len(ws) != EXPECT_TOTAL:
        fails.append(f"witness count {len(ws)} != {EXPECT_TOTAL}")
    if kinds.get("scan", 0) != EXPECT_SCAN:
        fails.append(f"scan count {kinds.get('scan', 0)} != {EXPECT_SCAN}")
    if kinds.get("transcription", 0) != EXPECT_TRANSCRIPTION:
        fails.append(f"transcription count {kinds.get('transcription', 0)} != {EXPECT_TRANSCRIPTION}")
    if kinds.get("scan-source-of-transcription", 0) != EXPECT_MAD_SRC:
        fails.append(f"madueke-source count {kinds.get('scan-source-of-transcription', 0)} != {EXPECT_MAD_SRC}")

    # --- provenance spine: every record carries the full join-core ---
    for w in ws:
        src = w.get("source", "<no-source>")
        if not w.get("sha256"):
            fails.append(f"{src}: null/empty sha256")
        if w.get("lineage_group") not in msl.LINEAGE_ENUM:
            fails.append(f"{src}: lineage_group {w.get('lineage_group')!r} not in LINEAGE_ENUM")
        if not isinstance(w.get("independent"), bool):
            fails.append(f"{src}: independent {w.get('independent')!r} is not a bool")

    # --- the 14 print scans specifically must all carry a propagated content hash ---
    scans_with_sha = [w for w in ws if w["kind"] == "scan" and w.get("sha256")]
    if len(scans_with_sha) != EXPECT_SCAN:
        fails.append(f"scans with sha256 {len(scans_with_sha)} != {EXPECT_SCAN}")

    # --- anti-drift guard must be clean (no book-level gate has crept back) ---
    g = subprocess.run([sys.executable, str(GUARD)], capture_output=True, text=True)
    if g.returncode != 0:
        fails.append(f"guard_no_book_gates exited {g.returncode}: {g.stdout.strip()} {g.stderr.strip()}")

    if fails:
        print("FAIL: P0 provenance-spine acceptance checks failed:")
        for f in fails:
            print(f"  - {f}")
        return 1
    print(f"PASS: {len(ws)} witnesses ({EXPECT_SCAN} scan + {EXPECT_TRANSCRIPTION} transcription + "
          f"{EXPECT_MAD_SRC} madueke-source), all with sha256 + lineage_group∈enum + independent(bool); "
          f"guard clean.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

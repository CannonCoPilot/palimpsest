"""Collections tier — phase C2 backend completions: PAF export (FR-36), dotplot score thresholding
(FR-40), score distribution, and comparison discovery. The pairwise matrix + Smith-Waterman + Gumbel
machinery already existed; these tests cover the gaps that complete C2's done-criteria."""
from __future__ import annotations

import json
from pathlib import Path

from palimpsest.alignment.records import (
    AlignmentRecord,
    records_to_paf,
    write_alignment_records,
    write_paf,
)


def _records() -> list[AlignmentRecord]:
    return [
        AlignmentRecord("a", 0, 100, "b", 0, 90, score=9.0, p_value=0.001, identity=0.8),
        AlignmentRecord("a", 200, 260, "b", 180, 240, score=5.0, p_value=0.02, identity=0.5),
        AlignmentRecord("a", 400, 420, "b", 360, 380, score=1.0, p_value=0.40, identity=0.1),
    ]


def _make_comparison(workspace: Path, q: str = "a", t: str = "b") -> Path:
    (workspace / q).mkdir(parents=True, exist_ok=True)
    (workspace / t).mkdir(parents=True, exist_ok=True)
    (workspace / q / "metadata.json").write_text(json.dumps({"id": q, "character_count": 1000}))
    (workspace / t / "metadata.json").write_text(json.dumps({"id": t, "character_count": 900}))
    comp = workspace / ".comparisons" / f"{q}_vs_{t}"
    write_alignment_records(comp / "alignment.jsonl", _records())
    (comp / "metadata.json").write_text(json.dumps(
        {"query_id": q, "target_id": t, "method": "semantic", "record_count": 3}))
    return comp


# ── PAF writer (FR-36) ────────────────────────────────────────────────────────────────────────────

def test_records_to_paf_format() -> None:
    lines = records_to_paf(_records(), query_len=1000, target_len=900)
    assert len(lines) == 3
    cols = lines[0].split("\t")
    # 12 mandatory PAF columns + 4 tags
    assert cols[0] == "a" and cols[1] == "1000" and cols[2] == "0" and cols[3] == "100"
    assert cols[4] == "+" and cols[5] == "b" and cols[6] == "900"
    assert cols[7] == "0" and cols[8] == "90"
    block = max(100, 90)
    assert cols[10] == str(block)  # block length = longer span
    assert int(cols[9]) == round(0.8 * block)  # residue matches ≈ identity × block
    assert 0 <= int(cols[11]) <= 255  # mapping quality in range
    tags = lines[0].split("\t")[12:]
    assert any(t.startswith("AS:i:") for t in tags)
    assert any(t.startswith("pv:f:") for t in tags)
    assert any(t.startswith("mt:Z:semantic") for t in tags)


def test_write_paf_roundtrip(tmp_path: Path) -> None:
    out = tmp_path / "x.paf"
    write_paf(out, _records(), query_len=1000, target_len=900)
    body = out.read_text(encoding="utf-8")
    assert body.endswith("\n") and len(body.strip().splitlines()) == 3
    write_paf(out, [], query_len=10, target_len=10)
    assert out.read_text(encoding="utf-8") == ""  # empty record set → empty file


# ── Endpoints: thresholded records, score distribution, PAF export, discovery ─────────────────────

def _client(workspace: Path):
    from fastapi.testclient import TestClient

    from palimpsest.server import create_app

    return TestClient(create_app(workspace))


def test_records_threshold_and_scores(tmp_path: Path) -> None:
    _make_comparison(tmp_path)
    client = _client(tmp_path)

    assert len(client.get("/api/alignment/a/b/records").json()) == 3
    # dotplot cutoff: only high-scoring alignments
    hi = client.get("/api/alignment/a/b/records?min_score=4").json()
    assert len(hi) == 2 and all(r["score"] >= 4 for r in hi)
    sig = client.get("/api/alignment/a/b/records?max_p_value=0.01").json()
    assert len(sig) == 1 and sig[0]["pValue"] <= 0.01

    scores = client.get("/api/alignment/a/b/scores").json()
    assert scores["count"] == 3 and scores["min"] == 1.0 and scores["max"] == 9.0
    assert scores["suggested_threshold"] is not None

    assert client.get("/api/alignment/a/ghost/records").status_code == 404


def test_export_paf_endpoint(tmp_path: Path) -> None:
    _make_comparison(tmp_path)
    client = _client(tmp_path)
    resp = client.get("/api/alignment/a/b/export.paf")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/x-paf")
    lines = resp.text.strip().splitlines()
    assert len(lines) == 3 and lines[0].split("\t")[0] == "a"
    # thresholded export
    resp2 = client.get("/api/alignment/a/b/export.paf?min_score=4")
    assert len(resp2.text.strip().splitlines()) == 2


def test_list_comparisons(tmp_path: Path) -> None:
    client = _client(tmp_path)
    assert client.get("/api/comparisons").json() == []  # none yet
    _make_comparison(tmp_path)
    comps = client.get("/api/comparisons").json()
    assert len(comps) == 1
    assert comps[0]["id"] == "a_vs_b" and comps[0]["has_records"] is True
    assert comps[0]["query_id"] == "a" and comps[0]["record_count"] == 3


def test_cli_align_paf(tmp_path: Path) -> None:
    from click.testing import CliRunner

    from palimpsest.cli import main

    _make_comparison(tmp_path)
    res = CliRunner().invoke(main, ["align-paf", str(tmp_path), "a", "b"])
    assert res.exit_code == 0
    assert len(res.output.strip().splitlines()) == 3
    res2 = CliRunner().invoke(main, ["align-paf", str(tmp_path), "a", "b", "--min-score", "4"])
    assert res2.exit_code == 0 and len(res2.output.strip().splitlines()) == 2

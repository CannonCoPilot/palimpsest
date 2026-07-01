"""Collections tier — phase C2 backend completions: PAF export (FR-36), dotplot score thresholding
(FR-40), score distribution, and comparison discovery. The pairwise matrix + Smith-Waterman + Gumbel
machinery already existed; these tests cover the gaps that complete C2's done-criteria."""
from __future__ import annotations

import json
from pathlib import Path

from palimpsest.alignment.records import (
    AlignmentRecord,
    comparison_dir,
    comparison_dirname,
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
    comp = comparison_dir(workspace, q, t)
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


def test_scores_reports_scale_free_identity_distribution(tmp_path: Path) -> None:
    # Raw score is length-proportional (a sum over the alignment) → not comparable across pairs. The
    # endpoint must also surface identity ∈ [0,1] (scale-free) + say so, so a client thresholds right.
    _make_comparison(tmp_path)
    scores = _client(tmp_path).get("/api/alignment/a/b/scores").json()  # identities: 0.1, 0.5, 0.8
    ident = scores["identity"]
    assert ident["min"] == 0.1 and ident["max"] == 0.8 and ident["median"] == 0.5
    assert "identity" in scores["note"] and "not comparable" in scores["note"]


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


def test_list_comparisons_scoped_to_collection(tmp_path: Path) -> None:
    """``?collection_id=`` returns only comparisons whose *both* endpoints are members, so a scoped
    collection view isn't polluted by unrelated cross-text results elsewhere in the workspace."""
    from palimpsest.collections import create_collection

    _make_comparison(tmp_path, "a", "b")  # both will be members
    _make_comparison(tmp_path, "a", "c")  # c is NOT a member
    client = _client(tmp_path)

    assert len(client.get("/api/comparisons").json()) == 2  # unfiltered = workspace-global

    cid = create_collection(tmp_path, "Pair", "", ["a", "b"], kind="manual")["id"]
    scoped = client.get(f"/api/comparisons?collection_id={cid}").json()
    assert [c["id"] for c in scoped] == ["a_vs_b"]  # a_vs_c dropped (c not a member)

    # Unknown collection → 404 (honest), not a silently-empty list.
    assert client.get("/api/comparisons?collection_id=ghost").status_code == 404


def test_matrix_bin_has_self_describing_headers(tmp_path: Path) -> None:
    """matrix.bin carries X-Matrix-Rows/Cols/Dtype (parity with the embedding heatmap.bin) so a client
    decodes the flat little-endian Float32 [rows x cols] buffer without a second /matrix JSON fetch."""
    import numpy as np

    comp = _make_comparison(tmp_path)  # a_vs_b
    matrix = np.arange(6, dtype=np.float32).reshape(2, 3)
    (comp / "cross_similarity.bin").write_bytes(matrix.tobytes())
    (comp / "cross_similarity.json").write_text(json.dumps({"dimensions": [2, 3]}))

    resp = _client(tmp_path).get("/api/alignment/a/b/matrix.bin")
    assert resp.status_code == 200
    assert resp.headers["X-Matrix-Rows"] == "2"
    assert resp.headers["X-Matrix-Cols"] == "3"
    assert resp.headers["X-Matrix-Dtype"] == "float32-le"
    got = np.frombuffer(resp.content, dtype="<f4").reshape(2, 3)
    assert np.array_equal(got, matrix)


def test_cli_align_paf(tmp_path: Path) -> None:
    from click.testing import CliRunner

    from palimpsest.cli import main

    _make_comparison(tmp_path)
    res = CliRunner().invoke(main, ["align-paf", str(tmp_path), "a", "b"])
    assert res.exit_code == 0
    assert len(res.output.strip().splitlines()) == 3
    res2 = CliRunner().invoke(main, ["align-paf", str(tmp_path), "a", "b", "--min-score", "4"])
    assert res2.exit_code == 0 and len(res2.output.strip().splitlines()) == 2


# ── Regressions: live HTTP pipeline (these failure modes only surface over the wire) ──────────────

def test_run_alignment_accepts_json_body(tmp_path: Path) -> None:
    """POST /api/alignment/run must parse its Pydantic body. ``AlignmentRequest`` was defined inside
    ``create_app``; under ``from __future__ import annotations`` FastAPI could not resolve the
    stringized hint against module globals and silently demoted ``request`` to a query param, so every
    POST 422'd. Guard the contract: a valid body is accepted, an incomplete one is a 422."""
    _make_comparison(tmp_path)  # creates loadable-enough 'a' and 'b' project dirs
    client = _client(tmp_path)

    ok = client.post("/api/alignment/run", json={"query_id": "a", "target_id": "b", "method": "word"})
    assert ok.status_code == 200, ok.text
    assert ok.json()["status"] == "started"

    bad = client.post("/api/alignment/run", json={"query_id": "a"})  # missing target_id
    assert bad.status_code == 422
    # the failure must be about the missing body field, NOT a phantom 'request' query param
    assert any(err["loc"][-1] == "target_id" for err in bad.json()["detail"])


def test_semantic_alignment_is_congruence_gated(tmp_path: Path) -> None:
    """Semantic (embedding) alignment on members that share no congruent embedding space fails fast
    with 409 (FR-27) instead of dispatching a job that dies mid-run with FileNotFoundError. Token
    methods (word/alphabet) need no embeddings and are unaffected."""
    _make_comparison(tmp_path)  # 'a','b' are loadable but NOT embedded
    client = _client(tmp_path)

    gated = client.post(
        "/api/alignment/run", json={"query_id": "a", "target_id": "b", "method": "semantic"})
    assert gated.status_code == 409
    assert "embedding" in gated.json()["detail"].lower()

    ok = client.post(
        "/api/alignment/run", json={"query_id": "a", "target_id": "b", "method": "word"})
    assert ok.status_code == 200


def test_comparison_dirname_is_length_bounded() -> None:
    """Long edition slugs joined by ``_vs_`` exceed the 255-byte filesystem component limit and raise
    Errno 63 at write time. Short pairs keep the readable name; long pairs collapse to a stable hash."""
    assert comparison_dirname("a", "b") == "a_vs_b"  # short → readable + back-compatible

    q, t = "q" * 150, "t" * 150  # 304-byte natural name
    name = comparison_dirname(q, t)
    assert len(name.encode("utf-8")) <= 200 and name.startswith("cmp-")
    assert comparison_dirname(q, t) == name  # deterministic
    assert comparison_dirname(t, q) != name  # order-sensitive (query vs target)


def test_long_id_pair_roundtrips_through_endpoints(tmp_path: Path) -> None:
    """End-to-end guard for the Errno 63 fix: a comparison between two long-id projects must write,
    list, and export without tripping the filename-length limit."""
    q, t = "douay" + "x" * 140, "geneva" + "y" * 140
    _make_comparison(tmp_path, q, t)  # uses comparison_dir → no OSError
    client = _client(tmp_path)

    assert len(client.get(f"/api/alignment/{q}/{t}/records").json()) == 3
    paf = client.get(f"/api/alignment/{q}/{t}/export.paf")
    assert paf.status_code == 200 and len(paf.text.strip().splitlines()) == 3

    comps = client.get("/api/comparisons").json()
    assert len(comps) == 1 and comps[0]["query_id"] == q and comps[0]["record_count"] == 3

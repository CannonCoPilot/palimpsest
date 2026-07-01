"""Recall-dial sweep + resumable run journal (C6c, FR-35).

Real member projects (``reference.txt`` paragraphs → true ``Project.paragraphs()``) so the token/word
dial primitive is exercised end-to-end. Asserts the dial (dense vs pruned + forced-exhaustive escape),
the honest reporting (pruned counts + estimated recall, never silent), the congruence gate for
embedding metrics, and journal resume (done member pairs are skipped on re-run).
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from palimpsest import collections as cs
from palimpsest import collections_sweep as sweep


def _member(workspace: Path, pid: str, paragraphs: list[str]) -> str:
    pdir = workspace / pid
    pdir.mkdir(parents=True, exist_ok=True)
    text = "\n\n".join(paragraphs) + "\n"
    (pdir / "metadata.json").write_text(json.dumps({
        "id": pid, "title": pid, "language": "en", "source_format": "txt",
        "source_file": f"{pid}.txt", "ingest_date": "2026-06-30", "palimpsest_version": "0",
        "reference_sha256": f"sha-{pid}", "word_count": len(text.split()),
        "paragraph_count": len(paragraphs), "section_count": 0,
        "sentence_count": len(paragraphs), "character_count": len(text),
    }), encoding="utf-8")
    (pdir / "reference.txt").write_text(text, encoding="utf-8")
    (pdir / "reference.sha256").write_text(f"sha-{pid}", encoding="utf-8")
    return pid


@pytest.fixture
def corpus(tmp_path: Path) -> tuple[Path, str]:
    _member(tmp_path, "alpha", [
        "In the beginning the word went forth across the waters and the land.",
        "Alpha alone speaks of secret groves and hidden alpha streams at dawn.",
        "And the people gathered to hear the telling of the ancient days.",
    ])
    _member(tmp_path, "beta", [
        "In the beginning the word went forth across the waters and the land.",
        "Beta alone recounts the northern winds over the wide beta fields.",
        "And the people gathered to hear the telling of the ancient days.",
    ])
    _member(tmp_path, "gamma", [
        "In the beginning the word went forth across the waters and the land.",
        "Gamma alone tells of desert stars and the long gamma silence.",
        "And the people gathered to hear the telling of the ancient days.",
    ])
    col = cs.create_collection(tmp_path, "Sweep", "recall-dial sweep corpus", ["alpha", "beta", "gamma"])
    return tmp_path, col["id"]


# ── the dial ──────────────────────────────────────────────────────────────────────────────────────

def test_small_sweep_is_dense_full_recall(corpus: tuple[Path, str]) -> None:
    ws, cid = corpus
    res = sweep.sweep_pairwise(ws, cid, metric="word_overlap", mode="high-recall")
    assert res["n_member_pairs"] == 3  # C(3,2)
    assert res["n_pruned"] == 0 and res["mean_estimated_recall"] == 1.0
    assert all(p["dense"] for p in res["pairs"])  # tiny paragraph counts → auto-dense


def test_low_threshold_prunes_and_reports_recall(corpus: tuple[Path, str]) -> None:
    ws, cid = corpus
    res = sweep.sweep_pairwise(ws, cid, metric="word_overlap", mode="high-recall", dense_threshold=0)
    assert res["n_pruned"] > 0  # dial actually pruned the pair space
    assert not any(p["dense"] for p in res["pairs"])
    # recall is a measured number in [0, 1], never a silent cap
    assert res["mean_estimated_recall"] is not None and 0.0 <= res["mean_estimated_recall"] <= 1.0
    for p in res["pairs"]:
        assert p["n_candidates"] + p["n_pruned"] == p["n_pairs_total"]  # nothing lost silently


def test_force_exhaustive_escape_beats_the_dial(corpus: tuple[Path, str]) -> None:
    ws, cid = corpus
    res = sweep.sweep_pairwise(
        ws, cid, metric="word_overlap", mode="fast", dense_threshold=0, force_exhaustive=True)
    assert res["force_exhaustive"] is True
    assert res["n_pruned"] == 0 and all(p["dense"] for p in res["pairs"])  # escape overrides mode+threshold


# ── the run journal + resume ──────────────────────────────────────────────────────────────────────

def test_sweep_writes_resumable_journal(corpus: tuple[Path, str]) -> None:
    ws, cid = corpus
    res = sweep.sweep_pairwise(ws, cid, metric="word_overlap", mode="high-recall", dense_threshold=0)
    journal = sweep.read_sweep_journal(ws, cid, res["run_id"])
    assert journal is not None
    assert journal["progress"]["pairs_done"] == 3
    assert all(p["done"] for p in journal["pairs"].values())
    # a pruned pair persisted its candidate index list (needed to resume the scoring stage)
    assert any(p["candidates"] for p in journal["pairs"].values())


def test_resume_skips_done_pairs(corpus: tuple[Path, str]) -> None:
    ws, cid = corpus
    sweep.sweep_pairwise(ws, cid, metric="word_overlap", mode="high-recall", dense_threshold=0)

    labels: list[str] = []
    sweep.sweep_pairwise(
        ws, cid, metric="word_overlap", mode="high-recall", dense_threshold=0,
        resume=True, progress_cb=lambda d, t, label: labels.append(label))
    assert labels and all("cached" in label for label in labels)  # every pair was already done


def test_no_resume_recomputes(corpus: tuple[Path, str]) -> None:
    ws, cid = corpus
    sweep.sweep_pairwise(ws, cid, metric="word_overlap", mode="high-recall", dense_threshold=0)

    labels: list[str] = []
    sweep.sweep_pairwise(
        ws, cid, metric="word_overlap", mode="high-recall", dense_threshold=0,
        resume=False, progress_cb=lambda d, t, label: labels.append(label))
    assert labels and not any("cached" in label for label in labels)


def test_run_id_is_param_addressed(corpus: tuple[Path, str]) -> None:
    ws, cid = corpus
    a = sweep.sweep_pairwise(ws, cid, metric="word_overlap", mode="high-recall")
    b = sweep.sweep_pairwise(ws, cid, metric="word_overlap", mode="fast")
    assert a["run_id"] != b["run_id"]  # different dial → different journal → no cross-contamination


# ── gates ─────────────────────────────────────────────────────────────────────────────────────────

def test_embedding_sweep_gate_fails_loud_without_embeddings(corpus: tuple[Path, str]) -> None:
    from palimpsest.collections_ops import MetricCongruenceError

    ws, cid = corpus
    with pytest.raises(MetricCongruenceError):  # members have no embedding layer → never a silent skip
        sweep.sweep_pairwise(ws, cid, metric="cosine", mode="high-recall")


def test_sweep_needs_two_members(tmp_path: Path) -> None:
    _member(tmp_path, "solo", ["only one member here"])
    col = cs.create_collection(tmp_path, "Solo", "", ["solo"])
    with pytest.raises(ValueError, match="two members|>= 2"):
        sweep.sweep_pairwise(tmp_path, col["id"], metric="word_overlap")


def test_sweep_unknown_collection(tmp_path: Path) -> None:
    with pytest.raises(KeyError):
        sweep.sweep_pairwise(tmp_path, "no-such", metric="word_overlap")


# ── CLI + HTTP parity ─────────────────────────────────────────────────────────────────────────────

def test_sweep_cli(corpus: tuple[Path, str]) -> None:
    from click.testing import CliRunner

    from palimpsest.cli import main

    ws, cid = corpus
    result = CliRunner().invoke(
        main, ["collections", "sweep", str(ws), cid, "--metric", "word_overlap", "--dense-threshold", "0"])
    assert result.exit_code == 0, result.output
    # progress lines then the JSON roll-up; parse the JSON object at the tail
    payload = json.loads(result.output[result.output.index("{"):])
    assert payload["n_pruned"] > 0 and "run_id" in payload


def test_sweep_endpoint_and_journal_roundtrip(corpus: tuple[Path, str]) -> None:
    from fastapi.testclient import TestClient

    from palimpsest.server import create_app

    ws, cid = corpus
    client = TestClient(create_app(ws))
    resp = client.post(f"/api/collections/{cid}/sweep",
                       json={"metric": "word_overlap", "mode": "high-recall", "dense_threshold": 0})
    assert resp.status_code == 200, resp.text
    run_id = resp.json()["run_id"]
    journal = client.get(f"/api/collections/{cid}/sweep/{run_id}")
    assert journal.status_code == 200
    assert journal.json()["progress"]["pairs_done"] == 3

    # embedding sweep with no embeddings → congruence gate → 409, not a silent partial run
    bad = client.post(f"/api/collections/{cid}/sweep", json={"metric": "cosine"})
    assert bad.status_code == 409


# ── run/version manager: list + delete (C7, FR-35) ─────────────────────────────────────────────────

def test_list_and_delete_sweep_runs(corpus: tuple[Path, str]) -> None:
    ws, cid = corpus
    res = sweep.sweep_pairwise(ws, cid, metric="word_overlap", dense_threshold=0)
    run_id = res["run_id"]

    runs = sweep.list_sweep_runs(ws, cid)
    assert len(runs) == 1
    headline = runs[0]
    assert headline["run_id"] == run_id
    assert "pairs" not in headline                       # headline omits per-pair detail
    assert headline["progress"]["pairs_done"] == 3
    assert headline["n_pruned"] == res["n_pruned"]

    assert sweep.delete_sweep_run(ws, cid, run_id) is True
    assert sweep.list_sweep_runs(ws, cid) == []
    assert sweep.delete_sweep_run(ws, cid, run_id) is False  # second delete: gone


def test_list_sweeps_empty_when_none(tmp_path: Path) -> None:
    _member(tmp_path, "a", ["one two three four five"])
    _member(tmp_path, "b", ["five six seven eight nine"])
    col = cs.create_collection(tmp_path, "AB", "", ["a", "b"])
    assert sweep.list_sweep_runs(tmp_path, col["id"]) == []


def test_sweeps_list_and_delete_http(corpus: tuple[Path, str]) -> None:
    from fastapi.testclient import TestClient

    from palimpsest.server import create_app

    ws, cid = corpus
    client = TestClient(create_app(ws))
    run_id = client.post(f"/api/collections/{cid}/sweep",
                         json={"metric": "word_overlap", "dense_threshold": 0}).json()["run_id"]

    listing = client.get(f"/api/collections/{cid}/sweeps")
    assert listing.status_code == 200
    runs = listing.json()["runs"]
    assert len(runs) == 1 and runs[0]["run_id"] == run_id

    deleted = client.delete(f"/api/collections/{cid}/sweep/{run_id}")
    assert deleted.status_code == 200 and deleted.json()["deleted"] == run_id
    assert client.get(f"/api/collections/{cid}/sweeps").json()["runs"] == []
    assert client.delete(f"/api/collections/{cid}/sweep/{run_id}").status_code == 404


def test_sweeps_list_cli(corpus: tuple[Path, str]) -> None:
    from click.testing import CliRunner

    from palimpsest.cli import main

    ws, cid = corpus
    sweep.sweep_pairwise(ws, cid, metric="word_overlap", dense_threshold=0)
    result = CliRunner().invoke(main, ["collections", "sweeps", str(ws), cid])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output[result.output.index("{"):])
    assert len(payload["runs"]) == 1

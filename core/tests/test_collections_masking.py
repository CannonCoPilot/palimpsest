"""Collections tier — phase C5 (cross-text masking, corpus repeats & liftover assembler).

``collections_masking`` composes existing leaves against a real workspace, so these tests fabricate a
contract-accurate 3-member collection (real ``reference.txt`` paragraphs → true ``Project.paragraphs()``
char spans, plus pairwise comparison dirs written exactly as ``POST /api/alignment/run`` writes them)
and assert the cross-member repeat tally, singleton-derived low correspondence, mask union, the
mask-changes-an-alignment property, and block-granular liftover with drop reporting.

Fixture topology (paragraph index in brackets):

    A: [0] "eternal covenant endures forever" (shared, all)   [1] alpha-unique   [2] shared refrain (A,B)
    B: [0] "eternal covenant endures forever" (shared, all)   [1] beta-unique    [2] shared refrain (A,B)
    C: [0] "eternal covenant endures forever" (shared, all)   [1] gamma-unique

    edges  A↔B: (0,0),(2,2)   A↔C: (0,0)   B↔C: (0,0)   → core {A,B,C} p0, shell {A,B} p2, 3 singletons p1
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from palimpsest import collections as cs
from palimpsest import collections_masking as cm
from palimpsest import corpus_graph as cg
from palimpsest.alignment.records import AlignmentRecord, comparison_dir, write_alignment_records
from palimpsest.project import Project

SHARED = "The eternal covenant endures forever"
REFRAIN = "A shared refrain of light and water flows here"


def _member(workspace: Path, pid: str, paragraphs: list[str]) -> str:
    pdir = workspace / pid
    pdir.mkdir(parents=True, exist_ok=True)
    text = "\n\n".join(paragraphs) + "\n"
    (pdir / "metadata.json").write_text(
        json.dumps({
            "id": pid, "title": pid, "language": "en", "source_format": "txt",
            "source_file": f"{pid}.txt", "ingest_date": "2026-06-30", "palimpsest_version": "0",
            "reference_sha256": f"sha-{pid}", "word_count": len(text.split()),
            "paragraph_count": len(paragraphs), "section_count": 0,
            "sentence_count": len(paragraphs), "character_count": len(text),
        }),
        encoding="utf-8",
    )
    (pdir / "reference.txt").write_text(text, encoding="utf-8")
    (pdir / "reference.sha256").write_text(f"sha-{pid}", encoding="utf-8")
    return pid


def _comparison(workspace: Path, q: str, t: str, pairs: list[tuple[int, int, int, int]]) -> Path:
    records = [
        AlignmentRecord(query_id=q, query_start=qs, query_end=qe,
                        target_id=t, target_start=ts, target_end=te, score=30.0)
        for qs, qe, ts, te in pairs
    ]
    d = comparison_dir(workspace, q, t)
    d.mkdir(parents=True, exist_ok=True)
    write_alignment_records(d / "alignment.jsonl", records)
    (d / "metadata.json").write_text(json.dumps({"query_id": q, "target_id": t}), encoding="utf-8")
    return d


@pytest.fixture
def corpus(tmp_path: Path) -> tuple[Path, str]:
    a = _member(tmp_path, "alpha", [
        f"{SHARED}, said the prophet alpha to the gathered.",
        "Alpha alone speaks of secret groves and hidden alpha streams.",
        f"{REFRAIN} in the alpha telling.",
    ])
    b = _member(tmp_path, "beta", [
        f"{SHARED}, wrote the scribe beta upon the tablet.",
        "Beta alone recounts the northern winds over the beta fields.",
        f"{REFRAIN} in the beta telling.",
    ])
    c = _member(tmp_path, "gamma", [
        f"{SHARED}, sang the poet gamma beneath the boughs.",
        "Gamma alone tells of desert stars and gamma silence.",
    ])
    _comparison(tmp_path, a, b, [(0, 1, 0, 1), (2, 3, 2, 3)])
    _comparison(tmp_path, a, c, [(0, 1, 0, 1)])
    _comparison(tmp_path, b, c, [(0, 1, 0, 1)])
    col = cs.create_collection(tmp_path, "Corpus", "cross-text masking corpus", [a, b, c])
    return tmp_path, col["id"]


def _within(interval: list[int], paras, idx: int) -> bool:
    s, e = interval
    return paras[idx][0] <= s and e <= paras[idx][1]


def test_corpus_repeats_detects_cross_member_phrase(corpus: tuple[Path, str]) -> None:
    workspace, cid = corpus
    cr = cm.corpus_repeats(workspace, cid, min_members=2)

    # The phrase recurs once per member — invisible to single-text detect_repeats, found here.
    joined = " ".join(cr["phrases"])
    assert "eternal covenant endures forever" in joined
    assert "shared refrain" in joined  # present in alpha + beta only, still >= 2 members

    paras = Project.load(workspace / "alpha").paragraphs()
    alpha_iv = cr["intervals"]["alpha"]
    assert alpha_iv, "alpha must carry corpus-repeat intervals"
    # gamma lacks the refrain paragraph, so its intervals sit only in p0.
    assert all(_within(iv, paras, 0) or _within(iv, paras, 2) for iv in alpha_iv)


def test_corpus_repeats_min_members_gate(corpus: tuple[Path, str]) -> None:
    workspace, cid = corpus
    # Requiring all 3 members keeps only the phrase shared by all three (drops the A/B refrain).
    cr3 = cm.corpus_repeats(workspace, cid, min_members=3)
    joined = " ".join(cr3["phrases"])
    assert "eternal covenant endures forever" in joined
    assert "shared refrain" not in joined


def test_low_correspondence_from_singletons(corpus: tuple[Path, str]) -> None:
    workspace, cid = corpus
    cg.write_corpus_graph(workspace, cid, cg.build_corpus_graph(workspace, cid))

    low = cm.low_correspondence_intervals(workspace, cid)
    paras = Project.load(workspace / "alpha").paragraphs()
    # alpha's unique middle paragraph (p1) is the singleton region.
    assert low["alpha"], "alpha has an unaligned singleton paragraph"
    assert all(_within(iv, paras, 1) for iv in low["alpha"])


def test_low_correspondence_requires_graph(corpus: tuple[Path, str]) -> None:
    workspace, cid = corpus
    with pytest.raises(ValueError, match="build it first"):
        cm.low_correspondence_intervals(workspace, cid)


def test_cross_text_mask_unions_sources(corpus: tuple[Path, str]) -> None:
    workspace, cid = corpus
    cg.write_corpus_graph(workspace, cid, cg.build_corpus_graph(workspace, cid))

    mask = cm.cross_text_mask(workspace, cid, "alpha")
    assert mask["sources"]["repeats"], "repeat spans present"
    assert mask["sources"]["low_correspondence"], "singleton spans present"
    # Union covers >= the larger source and is merged/disjoint.
    ivs = mask["intervals"]
    assert ivs == sorted(ivs)
    assert all(a[1] <= b[0] for a, b in zip(ivs, ivs[1:])), "merged, disjoint"
    assert mask["masked_chars"] == sum(e - s for s, e in ivs)


def test_cross_text_mask_changes_alignment(corpus: tuple[Path, str]) -> None:
    workspace, cid = corpus
    a = Project.load(workspace / "alpha")
    b = Project.load(workspace / "beta")

    unmasked = cm.masked_cross_similarity(a, b, metric="word_overlap")
    mask_a = [(s, e) for s, e in cm.cross_text_mask(
        workspace, cid, "alpha", include_low_correspondence=False)["intervals"]]
    assert mask_a, "need a non-empty mask to demonstrate the effect"
    masked = cm.masked_cross_similarity(a, b, mask_a=mask_a, metric="word_overlap")

    # Excising alpha's shared phrases changes its paragraph token-sets → the matrix must differ.
    assert masked.shape != unmasked.shape or not np.array_equal(masked, unmasked)


def test_liftover_projects_aligned_interval(corpus: tuple[Path, str]) -> None:
    workspace, cid = corpus
    a_paras = Project.load(workspace / "alpha").paragraphs()
    b_paras = Project.load(workspace / "beta").paragraphs()

    # An interval inside alpha p0 lifts to beta p0's whole span (block-granular).
    inside_p0 = (a_paras[0][0] + 4, a_paras[0][0] + 20)
    res = cm.lift_intervals_across(workspace, "alpha", "beta", [inside_p0])
    assert res["lifted"] == [[b_paras[0][0], b_paras[0][1]]]
    assert res["dropped"] == []


def test_liftover_reports_dropped_unaligned(corpus: tuple[Path, str]) -> None:
    workspace, cid = corpus
    a_paras = Project.load(workspace / "alpha").paragraphs()
    # alpha p1 aligns to nothing on beta → dropped, not silently mis-projected.
    inside_p1 = (a_paras[1][0] + 2, a_paras[1][0] + 10)
    res = cm.lift_intervals_across(workspace, "alpha", "beta", [inside_p1])
    assert res["lifted"] == []
    assert res["dropped"] == [[inside_p1[0], inside_p1[1]]]


def test_liftover_reverse_orientation(corpus: tuple[Path, str]) -> None:
    workspace, cid = corpus
    a_paras = Project.load(workspace / "alpha").paragraphs()
    b_paras = Project.load(workspace / "beta").paragraphs()
    # Only alpha_vs_beta is stored; lifting beta→alpha must use the target axis.
    inside_b_p2 = (b_paras[2][0] + 3, b_paras[2][0] + 12)
    res = cm.lift_intervals_across(workspace, "beta", "alpha", [inside_b_p2])
    assert res["lifted"] == [[a_paras[2][0], a_paras[2][1]]]


def test_liftover_missing_pair_raises(corpus: tuple[Path, str]) -> None:
    workspace, cid = corpus
    with pytest.raises(ValueError, match="No alignment"):
        cm.lift_intervals_across(workspace, "alpha", "delta", [(0, 5)])


def test_cross_text_track_conservation_on_root_lens(corpus: tuple[Path, str]) -> None:
    workspace, cid = corpus
    cg.write_corpus_graph(workspace, cid, cg.build_corpus_graph(workspace, cid))

    track = cm.cross_text_track(workspace, cid, "alpha")
    assert track["root"] == "alpha" and track["member_total"] == 3
    assert track["rendering"]["track_view"] == "root-conservation-lane"

    paras = Project.load(workspace / "alpha").paragraphs()
    by_class = {s["classification"]: s for s in track["segments"]}
    # core passage (p0) is shared by all three members → conservation 1.0, on alpha's p0 char span.
    assert by_class["core"]["conservation"] == 1.0
    assert [by_class["core"]["char_start"], by_class["core"]["char_end"]] == list(paras[0][:2])
    # shell (p2, {alpha,beta}) → 2/3; alpha's own singleton (p1) → 1/3.
    assert by_class["shell"]["conservation"] == pytest.approx(2 / 3)
    assert by_class["singleton"]["conservation"] == pytest.approx(1 / 3)

    # Only alpha-present components appear (beta/gamma singletons are absent from the alpha frame).
    assert len(track["segments"]) == 3
    offsets = track["segment_offsets"]
    assert offsets == sorted(offsets)
    assert track["values"] == [s["conservation"] for s in track["segments"]]


def test_cross_text_track_guards(corpus: tuple[Path, str]) -> None:
    workspace, cid = corpus
    with pytest.raises(ValueError, match="build it first"):
        cm.cross_text_track(workspace, cid, "alpha")
    cg.write_corpus_graph(workspace, cid, cg.build_corpus_graph(workspace, cid))
    with pytest.raises(ValueError, match="not a member"):
        cm.cross_text_track(workspace, cid, "delta")


def test_write_cross_text_track_persists_in_collection_tier(corpus: tuple[Path, str]) -> None:
    workspace, cid = corpus
    cg.write_corpus_graph(workspace, cid, cg.build_corpus_graph(workspace, cid))
    track = cm.cross_text_track(workspace, cid, "alpha")
    path = cm.write_cross_text_track(workspace, cid, track)
    assert path == workspace / "collections" / cid / "tracks" / "conservation_alpha.json"
    assert path.exists()
    assert json.loads(path.read_text())["root"] == "alpha"


def test_persist_lifted_track_versions_and_staleness(corpus: tuple[Path, str]) -> None:
    workspace, cid = corpus
    a_paras = Project.load(workspace / "alpha").paragraphs()
    res = cm.lift_intervals_across(
        workspace, "alpha", "beta", [(a_paras[0][0] + 4, a_paras[0][0] + 20)])

    v1 = cm.persist_lifted_track(workspace, cid, res, kind="mask")
    assert v1["version_id"] == "v1"
    payload = workspace / "collections" / cid / "liftover" / "beta" / v1["metadata"]["payload"]
    assert payload.exists()
    assert not cm.lifted_track_is_stale(workspace, cid, res, kind="mask")

    # A different source lift → different identity → the prior version is now stale.
    changed = {**res, "lifted": [[0, 3]]}
    assert cm.lifted_track_is_stale(workspace, cid, changed, kind="mask")


# ── HTTP + CLI parity (FR-37) ─────────────────────────────────────────────────────────────────────

def _client(workspace: Path):
    from fastapi.testclient import TestClient

    from palimpsest.server import create_app

    return TestClient(create_app(workspace))


def test_http_c5_endpoints(corpus: tuple[Path, str]) -> None:
    workspace, cid = corpus
    client = _client(workspace)

    # corpus-repeats needs no graph.
    cr = client.get(f"/api/collections/{cid}/corpus-repeats?min_members=2")
    assert cr.status_code == 200 and cr.json()["phrases"]

    # graph-dependent endpoints 400 until the graph is built.
    assert client.get(f"/api/collections/{cid}/low-correspondence").status_code == 400
    assert client.get(f"/api/collections/{cid}/root-track?root=alpha").status_code == 400

    client.post(f"/api/collections/{cid}/corpus-graph")

    low = client.get(f"/api/collections/{cid}/low-correspondence")
    assert low.status_code == 200 and low.json()["alpha"]

    mask = client.get(f"/api/collections/{cid}/cross-text-mask/alpha")
    assert mask.status_code == 200 and mask.json()["intervals"]

    rt = client.get(f"/api/collections/{cid}/root-track?root=alpha")
    assert rt.status_code == 200 and rt.json()["member_total"] == 3
    assert client.get(f"/api/collections/{cid}/root-track?root=delta").status_code == 400

    a_paras = Project.load(workspace / "alpha").paragraphs()
    b_paras = Project.load(workspace / "beta").paragraphs()
    lift = client.post(f"/api/collections/{cid}/liftover", json={
        "source_id": "alpha", "target_id": "beta",
        "intervals": [[a_paras[0][0] + 4, a_paras[0][0] + 20]], "persist": True,
    })
    assert lift.status_code == 200
    body = lift.json()
    assert body["lifted"] == [[b_paras[0][0], b_paras[0][1]]]
    assert body["version"]["version_id"] == "v1"

    # a missing pair 400s.
    assert client.post(f"/api/collections/{cid}/liftover", json={
        "source_id": "alpha", "target_id": "delta", "intervals": [[0, 5]]}).status_code == 400


def test_cli_c5(corpus: tuple[Path, str]) -> None:
    from click.testing import CliRunner

    from palimpsest.cli import main

    workspace, cid = corpus
    cg.write_corpus_graph(workspace, cid, cg.build_corpus_graph(workspace, cid))
    runner = CliRunner()

    res = runner.invoke(main, ["collections", "corpus-repeats", str(workspace), cid])
    assert res.exit_code == 0 and "eternal covenant endures forever" in res.output

    res = runner.invoke(main, ["collections", "cross-text-mask", str(workspace), cid, "alpha"])
    assert res.exit_code == 0 and '"intervals"' in res.output

    res = runner.invoke(main, ["collections", "root-track", str(workspace), cid, "--root", "alpha"])
    assert res.exit_code == 0 and '"root": "alpha"' in res.output

    a_paras = Project.load(workspace / "alpha").paragraphs()
    res = runner.invoke(main, [
        "collections", "liftover", str(workspace), "alpha", "beta",
        "--interval", f"{a_paras[0][0] + 4}:{a_paras[0][0] + 20}",
    ])
    assert res.exit_code == 0 and '"lifted"' in res.output

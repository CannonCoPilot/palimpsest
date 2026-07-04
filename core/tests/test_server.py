"""Tests for the FastAPI server."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from palimpsest.annotation.serializer import write_track
from palimpsest.project import ingest_file
from palimpsest.server import create_app
from palimpsest.tracks.entities import EntityExtractor


@pytest.fixture
def workspace_with_project(pp_ch1_txt: Path, tmp_path: Path):
    """Create a workspace with one ingested + analyzed project."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    project = ingest_file(pp_ch1_txt, workspace, title="PP Server Test")
    anns = EntityExtractor().extract(project)
    write_track(project.path / "tracks" / "entities.jsonl", anns)
    return workspace


@pytest.fixture
def client(workspace_with_project):
    app = create_app(workspace_with_project)
    return TestClient(app)


class TestProjectsAPI:
    def test_list_projects(self, client):
        response = client.get("/api/projects")
        assert response.status_code == 200
        projects = response.json()
        assert len(projects) >= 1
        assert projects[0]["title"] == "PP Server Test"

    def test_list_projects_has_word_count(self, client):
        projects = client.get("/api/projects").json()
        assert projects[0]["word_count"] > 0

    def test_list_tracks(self, client):
        projects = client.get("/api/projects").json()
        project_id = projects[0]["id"]
        response = client.get(f"/api/projects/{project_id}/tracks")
        assert response.status_code == 200
        tracks = response.json()
        assert isinstance(tracks, list)
        assert "segments" in tracks
        assert "entities" in tracks


class TestSummarizeAPI:
    # Calls Ollama for a real summary when the service is up (cold model load can
    # take ~30s); returns ollama_available=False and stays fast when it is down.
    @pytest.mark.external
    def test_summarize_valid_request(self, client):
        passage = (
            "It is a truth universally acknowledged, that a single man "
            "in possession of a good fortune, must be in want of a wife."
        )
        response = client.post("/api/summarize", json={
            "passage": passage,
            "model": "qwen3:8b",
        })
        assert response.status_code == 200
        data = response.json()
        assert "ollama_available" in data
        assert "model" in data
        assert data["model"] == "qwen3:8b"
        if data["ollama_available"]:
            assert data["summary"] is not None
        else:
            assert data["summary"] is None

    def test_summarize_invalid_model_rejected(self, client):
        response = client.post("/api/summarize", json={
            "passage": "Some valid passage text that is long enough.",
            "model": "../../etc/passwd",
        })
        assert response.status_code == 422

    def test_summarize_passage_too_short(self, client):
        response = client.post("/api/summarize", json={
            "passage": "Short",
            "model": "qwen3:8b",
        })
        assert response.status_code == 422


class TestSearchAPI:
    def test_search_no_embeddings(self, client):
        projects = client.get("/api/projects").json()
        project_id = projects[0]["id"]
        response = client.get(f"/api/search?project={project_id}&query=wife")
        assert response.status_code == 200
        data = response.json()
        assert data["embedding_available"] is False
        assert data["results"] == []

    def test_search_invalid_project(self, client):
        response = client.get("/api/search?project=nonexistent&query=test")
        assert response.status_code == 200
        data = response.json()
        assert data["embedding_available"] is False

    def test_search_rejects_path_traversal(self, client):
        # /api/search takes a raw query param (no Pydantic pattern), so _safe_project_dir is the guard:
        # a '..' segment is a hard 400, never a silent empty result that could mask a traversal attempt.
        response = client.get("/api/search?project=../secret&query=test")
        assert response.status_code == 400


class TestEndpointGuards:
    def test_explain_unknown_project_is_404(self, client):
        # _safe_project_dir now backs /api/explain: a pattern-valid but absent project is a clean 404,
        # not a 500 from loading a missing directory.
        response = client.post("/api/explain", json={"project": "no-such-project", "state_id": 0})
        assert response.status_code == 404
        assert response.json()["detail"] == "Project not found"

    def test_corpus_graph_unknown_collection_says_collection_not_found(self, client):
        # 404-ordering: check the collection exists before the graph. A missing collection must not
        # masquerade as an un-built graph ("Corpus graph not built") — that misdirects the caller.
        response = client.get("/api/collections/no-such-collection/corpus-graph")
        assert response.status_code == 404
        assert response.json()["detail"] == "Collection not found"


class TestStaticServing:
    def test_serve_reference_txt(self, client):
        projects = client.get("/api/projects").json()
        project_id = projects[0]["id"]
        response = client.get(f"/data/{project_id}/reference.txt")
        assert response.status_code == 200
        assert "Mr. Bennet" in response.text

    def test_serve_metadata_json(self, client):
        projects = client.get("/api/projects").json()
        project_id = projects[0]["id"]
        response = client.get(f"/data/{project_id}/metadata.json")
        assert response.status_code == 200
        meta = response.json()
        assert meta["title"] == "PP Server Test"

    def test_serve_entities_jsonl(self, client):
        projects = client.get("/api/projects").json()
        project_id = projects[0]["id"]
        response = client.get(f"/data/{project_id}/tracks/entities.jsonl")
        assert response.status_code == 200
        lines = response.text.strip().split("\n")
        assert len(lines) > 0
        first = json.loads(lines[0])
        assert first["type"] == "Annotation"

    def test_path_traversal_blocked(self, client):
        response = client.get("/data/../../../etc/passwd")
        assert response.status_code in (400, 404)

    def test_nonexistent_file_404(self, client):
        projects = client.get("/api/projects").json()
        project_id = projects[0]["id"]
        response = client.get(f"/data/{project_id}/nonexistent.txt")
        assert response.status_code == 404


# A syntactically-valid P7 inputs bundle. The labels need not resolve to real layers for endpoint
# tests that only assert the synchronous validate_params outcome (200 + echo, or a 400) — layer
# binding happens later in the async extract job.
_SS_INPUTS = json.dumps([{"chunk_label": "ck", "repeat_mask_label": "ck_rp"}])


class TestSelfSimilarityEndpoints:
    """Coverage for the self-similarity cs/* endpoints (audit E-NEW4) including
    the route-ordering regression and W7 metric-allowlist validation."""

    def _pid(self, client):
        return client.get("/api/projects").json()[0]["id"]

    def test_alignments_route_not_shadowed_by_metric_route(self, client):
        # Regression: the generic /cs/{cs}/{metric} route must be declared AFTER
        # the literal /cs/{cs}/alignments route, else "alignments" is treated as a
        # metric and rejected by W7 validation (400) instead of returning records.
        pid = self._pid(client)
        r = client.get(f"/api/projects/{pid}/self_similarity/cs/17/alignments")
        assert r.status_code == 200
        assert r.json() == []

    def test_per_metric_alignments_valid_metric(self, client):
        pid = self._pid(client)
        r = client.get(f"/api/projects/{pid}/self_similarity/cs/17/alignments/cosine")
        assert r.status_code == 200
        assert r.json() == []

    def test_per_metric_alignments_invalid_metric_rejected(self, client):
        pid = self._pid(client)
        r = client.get(f"/api/projects/{pid}/self_similarity/cs/17/alignments/bogus")
        assert r.status_code == 400

    def test_chunk_data_invalid_metric_rejected(self, client):
        # W7: unknown metric must be rejected, not used to build a file path.
        pid = self._pid(client)
        r = client.get(f"/api/projects/{pid}/self_similarity/cs/17/bogus")
        assert r.status_code == 400

    def test_chunk_data_valid_metric_missing_file_404(self, client):
        # A valid metric passes W7 validation but 404s when no data exists.
        pid = self._pid(client)
        r = client.get(f"/api/projects/{pid}/self_similarity/cs/17/cosine")
        assert r.status_code == 404

    def test_chunk_sizes_empty_for_fresh_project(self, client):
        pid = self._pid(client)
        r = client.get(f"/api/projects/{pid}/self_similarity/chunk_sizes")
        assert r.status_code == 200
        assert r.json()["chunk_sizes"] == []

    def test_auto_run_endpoint_removed(self, client):
        # The hidden-default auto-run endpoint was removed: analysis only runs on explicit request.
        pid = self._pid(client)
        r = client.post(f"/api/projects/{pid}/analyze/self_similarity/auto_run")
        assert r.status_code in (404, 405)  # no POST auto-run endpoint anymore

    def test_self_similarity_rejects_missing_required_params(self, client):
        # P7: `inputs` (the explicit layer bundles) is the required param with no default — omitting it
        # is a 400, not a silently-defaulted run.
        pid = self._pid(client)
        r = client.post(f"/api/projects/{pid}/analyze/self_similarity")
        assert r.status_code == 400
        assert "inputs" in r.json()["detail"].lower()

    def test_analyzable_sep_defaults_to_empty_and_is_echoed(self, client):
        # R2: the analyzable-stream separator is a runtime param, never a hidden default. Omitting it
        # resolves to "" (pure excision) and the resolved value is echoed back. A word_overlap run needs
        # no embedding service; the endpoint returns 200 once validate_params passes (the named layers
        # are bound later in the async job), and the 200 carries the echo.
        pid = self._pid(client)
        r = client.post(
            f"/api/projects/{pid}/analyze/self_similarity",
            params={"inputs": _SS_INPUTS, "metrics": "word_overlap"},
        )
        assert r.status_code == 200, r.text
        assert r.json()["analyzable_sep"] == ""

    def test_analyzable_sep_explicit_value_echoed_verbatim(self, client):
        # R2: an explicit separator (here " | ") is reflected verbatim, so the caller can confirm
        # exactly how the masked-resolved analyzable stream was assembled.
        pid = self._pid(client)
        r = client.post(
            f"/api/projects/{pid}/analyze/self_similarity",
            params={"inputs": _SS_INPUTS, "metrics": "word_overlap", "analyzable_sep": " | "},
        )
        assert r.status_code == 200, r.text
        assert r.json()["analyzable_sep"] == " | "

    def test_delimiters_accepts_multi_char_list_param(self, client):
        # R4: delimiters is a repeated (list) query param — each entry is a full, possibly multi-char
        # delimiter, not one string split into characters. Under P7, delimiters belongs to the chunking
        # layer (self_similarity no longer chunks), so this exercises the `chunking` track in
        # punctuation mode. The resolved-params echo proves both multi-char entries survive intact (not
        # split into single characters).
        pid = self._pid(client)
        r = client.post(
            f"/api/projects/{pid}/analyze/chunking",
            params={"chunk_mode": "punctuation", "delimiters": ["||", "--"]},
        )
        assert r.status_code == 200, r.text
        assert r.json()["resolved_params"]["delimiters"] == ["||", "--"]

    def test_unknown_metric_rejected_with_400(self, client):
        # R6: a typo'd metric is rejected (400) with the offending value named — not silently
        # dropped (which previously fell back to silently running every metric).
        pid = self._pid(client)
        r = client.post(
            f"/api/projects/{pid}/analyze/self_similarity",
            params={"inputs": _SS_INPUTS, "metrics": "word_overlap,cosin"},
        )
        assert r.status_code == 400, r.text
        detail = r.json()["detail"].lower()
        assert "unknown" in detail and "cosin" in detail


class TestTrackParamEndpoints:
    """R8: non-chunking tracks reject out-of-range/unknown runtime params at the API (400) instead
    of silently clamping or dropping them."""

    def _pid(self, client):
        return client.get("/api/projects").json()[0]["id"]

    def test_lithmm_out_of_range_n_states_rejected(self, client):
        pid = self._pid(client)
        r = client.post(f"/api/projects/{pid}/analyze/lithmm?n_states=100")
        assert r.status_code == 400, r.text
        assert "n_states" in r.json()["detail"]

    def test_topics_unknown_method_rejected(self, client):
        pid = self._pid(client)
        r = client.post(f"/api/projects/{pid}/analyze/topics?method=bogus")
        assert r.status_code == 400, r.text
        assert "method" in r.json()["detail"].lower()


class TestJobErrorPropagation:
    """G5/B2: a failed analysis job carries its real message end-to-end. The status endpoint must
    surface ``failed`` + the error, not mask every present job as ``running`` (which then silently
    reverts to ``pending`` after the 30s cleanup), and must never relabel the error "Matrix too large".

    The status-derivation policy is a pure function (``_job_display_status``); the background job
    itself cannot run under ``TestClient`` (the anyio portal only advances the loop during a request,
    so a fire-and-forget ``asyncio.create_task`` never progresses), so the policy is tested directly."""

    def _pid(self, client):
        return client.get("/api/projects").json()[0]["id"]

    def test_failed_job_surfaces_failed_and_error(self):
        from palimpsest.server import _job_display_status
        job = {"status": "failed", "track": "self_similarity",
               "error": "ConnectError: All connection attempts failed"}
        status, error = _job_display_status(job, output_exists=False)
        assert status == "failed"
        assert error == "ConnectError: All connection attempts failed"

    def test_failed_job_error_passed_through_verbatim_not_relabeled(self):
        # The old code relabeled EVERY extract ValueError as "Matrix too large". The error must now
        # reach the user as whatever actually happened.
        from palimpsest.server import _job_display_status
        job = {"status": "failed", "track": "self_similarity",
               "error": "LayerResolutionError: no chunk layer satisfies {'overlapping': False}"}
        _, error = _job_display_status(job, output_exists=False)
        assert error is not None
        assert "Matrix too large" not in error
        assert "LayerResolutionError" in error

    def test_running_job_reports_running_without_error(self):
        from palimpsest.server import _job_display_status
        status, error = _job_display_status({"status": "running", "track": "x"}, output_exists=False)
        assert status == "running"
        assert error is None

    def test_completed_job_maps_to_computed_when_output_exists(self):
        # The job dict says "completed" (vocabulary the UI doesn't know); it maps to "computed".
        from palimpsest.server import _job_display_status
        status, error = _job_display_status({"status": "completed", "track": "x"}, output_exists=True)
        assert status == "computed"
        assert error is None

    def test_no_job_maps_to_computed_or_pending_by_output(self):
        from palimpsest.server import _job_display_status
        assert _job_display_status(None, output_exists=True) == ("computed", None)
        assert _job_display_status(None, output_exists=False) == ("pending", None)

    def test_self_similarity_status_payload_has_no_error_when_idle(self, client):
        # End-to-end: a fresh project has no running job; the status entries carry no error field.
        pid = self._pid(client)
        rows = client.get(f"/api/projects/{pid}/analysis/status").json()
        ss = next(t for t in rows if t["name"] == "self_similarity")
        assert ss["status"] in ("pending", "computed")
        assert "error" not in ss


class TestTrackRunInfo:
    """§5: the status payload surfaces per-track run provenance the data layer records but the UI
    could not see — the record-effective clamp (ran vs requested) and lithmm's actual method/posterior
    type (an HMM may have silently fallen back to KMeans, B5). Pure function, tested directly."""

    def _write_run(self, project_dir: Path, track: str, record: dict) -> None:
        manifests = project_dir / "manifests"
        manifests.mkdir(parents=True, exist_ok=True)
        (manifests / f"{track}.run.json").write_text(json.dumps(record))

    def test_none_when_no_provenance(self, tmp_path):
        from palimpsest.server import _track_run_info
        assert _track_run_info(tmp_path, "topics") is None

    def test_unclamped_run_adds_no_payload(self, tmp_path):
        from palimpsest.server import _track_run_info
        self._write_run(tmp_path, "topics", {"parameters": {"n_topics": 10}})
        assert _track_run_info(tmp_path, "topics") is None  # no `clamped` → nothing to surface

    def test_clamped_run_reports_effective_and_requested(self, tmp_path):
        from palimpsest.server import _track_run_info
        self._write_run(tmp_path, "topics", {
            "parameters": {"n_topics": 4, "n_topics_requested": 25},
            "clamped": ["n_topics"],
        })
        info = _track_run_info(tmp_path, "topics")
        assert info["clamped"] == ["n_topics"]
        assert info["effective"] == {"n_topics": 4}
        assert info["requested"] == {"n_topics": 25}

    def test_lithmm_surfaces_kmeans_fallback_method(self, tmp_path):
        from palimpsest.server import _track_run_info
        signals = tmp_path / "signals"
        signals.mkdir(parents=True, exist_ok=True)
        (signals / "lithmm_meta.json").write_text(json.dumps({
            "method": "KMeans-fallback",
            "posterior_type": "hard-assignment",
        }))
        info = _track_run_info(tmp_path, "lithmm")
        assert info["method"] == "KMeans-fallback"
        assert info["posteriorType"] == "hard-assignment"

    def test_lithmm_clamp_and_method_combine(self, tmp_path):
        from palimpsest.server import _track_run_info
        self._write_run(tmp_path, "lithmm", {
            "parameters": {"n_states": 3, "n_states_requested": 10},
            "clamped": ["n_states"],
        })
        signals = tmp_path / "signals"
        signals.mkdir(parents=True, exist_ok=True)
        (signals / "lithmm_meta.json").write_text(json.dumps({
            "method": "GaussianHMM", "posterior_type": "probabilistic",
        }))
        info = _track_run_info(tmp_path, "lithmm")
        assert info["requested"] == {"n_states": 10}
        assert info["method"] == "GaussianHMM"


class TestDeriveContainerScope:
    """HTTP-layer coverage for W1 container-scoped subtext derivation.

    The ``derive_subtext`` function is unit-tested in test_derive.py; this exercises the
    FastAPI wiring (``DeriveRequest.include_container_ids`` + ValueError->400) end-to-end."""

    def _scoped_workspace(self, tmp_path):
        from palimpsest.layout import LayoutConfig, LayoutSection, save_layout
        from palimpsest.project import ingest_file

        workspace = tmp_path / "ws"
        workspace.mkdir()
        text = "MAINBODYAAAAAAAAAA" + "APPENDIXBBBBBBBBBB"  # two contiguous 18-char halves
        src = tmp_path / "src.txt"
        src.write_text(text, encoding="utf-8")
        project = ingest_file(src, workspace, title="Scope HTTP Test")
        full = project.reference_text()
        m0, a0 = full.index("MAINBODY"), full.index("APPENDIX")
        end = a0 + len("APPENDIXBBBBBBBBBB")

        def _sec(id, type, start, end, parent_id=None):
            return LayoutSection(id=id, type=type, start=start, end=end, parent_id=parent_id)

        sections = [
            _sec("mainbook", "book", m0, a0),
            _sec("mc1", "chapter", m0, m0 + 9, "mainbook"),
            _sec("mc2", "chapter", m0 + 9, a0, "mainbook"),
            _sec("apx", "appendix", a0, end),
            _sec("ac1", "chapter", a0, a0 + 9, "apx"),
            _sec("ac2", "chapter", a0 + 9, end, "apx"),
        ]
        save_layout(project.path, LayoutConfig(sections=sections, applied=True, parents_computed=True))
        return workspace, project.metadata.id

    def test_derive_endpoint_scopes_to_container(self, tmp_path):
        from palimpsest.server import create_app

        workspace, pid = self._scoped_workspace(tmp_path)
        client = TestClient(create_app(workspace))

        full = client.post(f"/api/projects/{pid}/derive", json={"extraction_types": ["chapter"]})
        assert full.status_code == 200, full.text
        scoped = client.post(
            f"/api/projects/{pid}/derive",
            json={"extraction_types": ["chapter"], "include_container_ids": ["apx"]},
        )
        assert scoped.status_code == 200, scoped.text
        body = scoped.json()
        assert body["container_ids"] == ["apx"]
        # The param must actually change the output: appendix-only is strictly smaller than the
        # whole work, proving the scope threaded through FastAPI rather than being a no-op echo.
        assert 0 < body["char_count"] < full.json()["char_count"]

    def test_derive_endpoint_unknown_container_is_400(self, tmp_path):
        from palimpsest.server import create_app

        workspace, pid = self._scoped_workspace(tmp_path)
        client = TestClient(create_app(workspace))
        resp = client.post(
            f"/api/projects/{pid}/derive",
            json={"extraction_types": ["chapter"], "include_container_ids": ["nope"]},
        )
        assert resp.status_code == 400
        assert "Unknown or empty container" in resp.json()["detail"]

    def _read_sse(self, client, pid, body):
        """POST to the streamed derive endpoint and collect the parsed SSE events."""
        events = []
        with client.stream("POST", f"/api/projects/{pid}/derive/stream", json=body) as resp:
            assert resp.status_code == 200, resp.read()
            for line in resp.iter_lines():
                if line.startswith("data:"):
                    events.append(json.loads(line[5:].strip()))
        return events

    def test_derive_stream_emits_monotonic_progress_then_done(self, tmp_path):
        from palimpsest.server import create_app

        workspace, pid = self._scoped_workspace(tmp_path)
        client = TestClient(create_app(workspace))

        events = self._read_sse(client, pid, {"extraction_types": ["chapter"]})
        progress = [e for e in events if e["type"] == "progress"]
        done = [e for e in events if e["type"] == "done"]

        assert progress, "expected at least one progress event before completion"
        pcts = [e["pct"] for e in progress]
        assert pcts == sorted(pcts), f"progress pct must be monotonic non-decreasing, got {pcts}"
        assert all(0 <= p <= 100 for p in pcts)
        assert len(done) == 1, "exactly one terminal done event"
        d = done[0]
        assert d["project_id"] and d["char_count"] > 0 and d["collection_id"]

    def test_derive_stream_unknown_container_emits_error_event(self, tmp_path):
        from palimpsest.server import create_app

        workspace, pid = self._scoped_workspace(tmp_path)
        client = TestClient(create_app(workspace))

        events = self._read_sse(
            client, pid, {"extraction_types": ["chapter"], "include_container_ids": ["nope"]}
        )
        errors = [e for e in events if e["type"] == "error"]
        assert len(errors) == 1
        assert errors[0]["status"] == 400
        assert "Unknown or empty container" in errors[0]["detail"]
        assert not [e for e in events if e["type"] == "done"]


class TestGoldAPI:
    """First-class gold endpoints: GET /api/gold (registry) + POST /api/gold/{idx}/apply.

    The happy-path apply (ingest + reference_sha256 verify) needs the copyrighted,
    never-committed source binary, so it is a machine-local check (see the plan's curl
    verification) — the same reason ``_apply_gold_map``'s sha tie is not CI-runnable.
    Here we cover the hermetic surface: the registry read and the two 404 paths."""

    def test_list_gold_enumerates_registry(self, client):
        res = client.get("/api/gold")
        assert res.status_code == 200, res.text
        data = res.json()
        # scope/count/bibles keep their original Bible-only meaning (backward compatible).
        assert data["scope"] == "bibles"
        assert data["count"] == len(data["bibles"]) >= 19
        by_id = {b["id"]: b for b in data["bibles"]}
        # Every sub-kind is registered and its masking contract is committed here.
        for idx in (5, 6, 100, 108, 216, 219):
            assert idx in by_id, f"Bible {idx} missing from /api/gold"
            assert by_id[idx]["map_present"] is True
            assert by_id[idx]["validated"] == {"cli": True, "api": True, "ui": True}
        assert by_id[216]["translation"].startswith("King James")

    def test_list_gold_enumerates_nonbible_works(self, client):
        # The additive `works` array exposes the sibling non-Bible registry alongside
        # the Bibles, each flagged with map_present, without disturbing `bibles`.
        data = client.get("/api/gold").json()
        assert data["works_count"] == len(data["works"]) >= 17
        works_by_id = {w["id"]: w for w in data["works"]}
        # A Qur'an, a novel, and the flagged LDS work span the non-Bible kinds.
        for idx in (29, 107, 101):
            assert idx in works_by_id, f"work {idx} missing from /api/gold works"
            assert works_by_id[idx]["map_present"] is True

    def test_apply_gold_unknown_idx_is_404(self, client):
        res = client.post("/api/gold/999/apply", json={})
        assert res.status_code == 404
        assert "no gold work" in res.json()["detail"]

    def test_apply_gold_source_absent_is_404(self, tmp_path):
        # An empty imports corpus is the "preserve, don't push" state: the map is
        # committed but the source binary isn't here, so apply must 404 cleanly rather
        # than half-ingesting. Deterministic regardless of the machine's real corpus.
        workspace = tmp_path / "ws"
        workspace.mkdir()
        empty = tmp_path / "empty"
        empty.mkdir()
        client = TestClient(create_app(workspace, imports_dir=empty))
        res = client.post("/api/gold/216/apply", json={})
        assert res.status_code == 404
        assert "not present locally" in res.json()["detail"]

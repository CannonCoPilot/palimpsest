"""Tests for the CLI."""


import json

import pytest
from click.testing import CliRunner

from palimpsest.cli import main

# Project slug derives from the source filename stem (one project per source
# file, commit 1f48084), not from --title. The pp_ch1_txt fixture is
# pride-prejudice-ch1.txt, so every ingest of it lands here regardless of title.
PP_CH1_SLUG = "pride-prejudice-ch1"


@pytest.fixture
def runner():
    return CliRunner()


class TestCliIngest:
    def test_ingest_creates_project(self, runner, pp_ch1_txt, tmp_path):
        result = runner.invoke(main, [
            "ingest", str(pp_ch1_txt),
            "--workspace", str(tmp_path),
            "--title", "PP Test",
        ])
        assert result.exit_code == 0, result.output
        assert "Project created" in result.output

    def test_ingest_same_file_replaces(self, runner, pp_ch1_txt, tmp_path):
        # One project per source file: re-ingesting the same file is a clean
        # replace (exit 0), not a duplicate failure (commit 1f48084).
        first = runner.invoke(main, [
            "ingest", str(pp_ch1_txt),
            "--workspace", str(tmp_path),
            "--title", "First Title",
        ])
        assert first.exit_code == 0, first.output
        second = runner.invoke(main, [
            "ingest", str(pp_ch1_txt),
            "--workspace", str(tmp_path),
            "--title", "Second Title",
        ])
        assert second.exit_code == 0, second.output
        # Exactly one project dir for this source, named by its slug.
        project_dirs = [p for p in tmp_path.iterdir() if p.is_dir()]
        assert project_dirs == [tmp_path / PP_CH1_SLUG]


class TestCliInfo:
    def test_info_shows_metadata(self, runner, pp_ch1_txt, tmp_path):
        runner.invoke(main, [
            "ingest", str(pp_ch1_txt),
            "--workspace", str(tmp_path),
            "--title", "Info Test",
        ])
        project_dir = tmp_path / PP_CH1_SLUG
        result = runner.invoke(main, ["info", str(project_dir)])
        assert result.exit_code == 0, result.output
        assert "Info Test" in result.output


# These classes invoke `analyze`/`export`, which run the full extraction pipeline
# end-to-end (LDA topics, self-similarity, RQA, …) — genuine 7-11s compute the
# model cache cannot shortcut. Excluded from the `fast` subset; the default runs them.
@pytest.mark.slow
class TestCliAnalyze:
    def test_analyze_runs_entity_track(self, runner, pp_ch1_txt, tmp_path):
        runner.invoke(main, [
            "ingest", str(pp_ch1_txt),
            "--workspace", str(tmp_path),
            "--title", "Analyze Test",
        ])
        project_dir = tmp_path / PP_CH1_SLUG
        result = runner.invoke(main, ["analyze", str(project_dir)])
        assert result.exit_code == 0, result.output
        assert "Done" in result.output

        # Verify entities.jsonl was written by the pipeline
        entities_path = project_dir / "tracks" / "entities.jsonl"
        assert entities_path.exists()
        lines = entities_path.read_text().strip().split("\n")
        assert len(lines) > 0
        first = json.loads(lines[0])
        assert first["type"] == "Annotation"

        pipeline_run = json.loads((project_dir / "pipeline_run.json").read_text())
        assert "entities" in pipeline_run["tracks_computed"]
        assert pipeline_run["annotation_format"] == "W3C Web Annotation JSON-LD (JSONL)"

        # Verify provenance fields (I-5 fix)
        assert "python_version" in pipeline_run
        assert isinstance(pipeline_run["python_version"], str)
        assert "spacy_model" in pipeline_run
        assert isinstance(pipeline_run["booknlp_available"], bool)

    def test_analyze_routes_through_extract_masked(self, runner, pp_ch1_txt, tmp_path, monkeypatch):
        """FR-12 (CLI/HTTP parity): `analyze` runs every text-deriving extractor through the
        shared ``runner.extract_masked`` (character-level masking + analyzable→original remap) —
        the same code path the HTTP server uses — not ``extractor.extract(project)`` directly.

        Before the fix the CLI called ``extract`` directly, so a masked project analyzed from the
        CLI left masked spans in and produced wrong coordinates. The spy below fails loudly if a
        future change reverts the CLI to the unmasked path."""
        import palimpsest.runner as runner_mod

        runner.invoke(main, [
            "ingest", str(pp_ch1_txt),
            "--workspace", str(tmp_path),
            "--title", "Parity Test",
        ])
        project_dir = tmp_path / PP_CH1_SLUG

        seen: list[str] = []
        real = runner_mod.extract_masked

        def spy(project, extractor, sep=""):
            seen.append(extractor.name)
            return real(project, extractor, sep)

        # cli.analyze does `from palimpsest.runner import extract_masked` at call time, so patching
        # the module attribute is picked up by the command's local import.
        monkeypatch.setattr(runner_mod, "extract_masked", spy)

        result = runner.invoke(main, ["analyze", str(project_dir)])
        assert result.exit_code == 0, result.output
        assert seen, "analyze must route extractors through extract_masked (CLI/HTTP parity)"
        assert "entities" in seen, "the text-deriving entities track should run via the masked path"

        # Parity must hold for EVERY extractor, not just one: a partial revert that routed only
        # some tracks through extract_masked would be a silent coordinate-correctness hole. A
        # freshly-ingested project has nothing cached, so the analyze loop attempts every
        # registered track, and the spy records each name before delegating (so a track that
        # raises inside extract_masked still counts as routed-through).
        from palimpsest.tracks.registry import TrackRegistry

        expected = {cls().name for cls in TrackRegistry.discover().dependency_order()}
        assert set(seen) == expected, (
            "CLI/HTTP parity: every registered extractor must route through extract_masked. "
            f"missing from masked path: {sorted(expected - set(seen))}; "
            f"unexpected: {sorted(set(seen) - expected)}"
        )

    def test_analyze_writes_output_files(self, runner, pp_ch1_txt, tmp_path):
        runner.invoke(main, [
            "ingest", str(pp_ch1_txt),
            "--workspace", str(tmp_path),
            "--title", "Output Test",
        ])
        project_dir = tmp_path / PP_CH1_SLUG
        runner.invoke(main, ["analyze", str(project_dir)])
        assert (project_dir / "tracks" / "entities.jsonl").exists()
        assert (project_dir / "pipeline_run.json").exists()
        # G3/C1: each track run leaves a resolved-params record on disk via the shared writer the
        # HTTP path also uses — not just the CLI-only aggregate pipeline_run.json.
        run_prov = project_dir / "manifests" / "entities.run.json"
        assert run_prov.exists()
        prov = json.loads(run_prov.read_text())
        assert prov["track"] == "entities"
        assert "parameters" in prov and "run_id" in prov and "timestamp" in prov

    def test_analyze_skips_existing(self, runner, pp_ch1_txt, tmp_path):
        runner.invoke(main, [
            "ingest", str(pp_ch1_txt),
            "--workspace", str(tmp_path),
            "--title", "Skip Test",
        ])
        project_dir = tmp_path / PP_CH1_SLUG
        runner.invoke(main, ["analyze", str(project_dir)])
        result = runner.invoke(main, ["analyze", str(project_dir)])
        assert result.exit_code == 0
        pipeline_run = json.loads((project_dir / "pipeline_run.json").read_text())
        assert pipeline_run["tracks_computed"] == []


@pytest.mark.slow
class TestCliExport:
    def test_export_w3c(self, runner, pp_ch1_txt, tmp_path):
        runner.invoke(main, [
            "ingest", str(pp_ch1_txt),
            "--workspace", str(tmp_path),
            "--title", "Export Test",
        ])
        project_dir = tmp_path / PP_CH1_SLUG
        runner.invoke(main, ["analyze", str(project_dir)])
        result = runner.invoke(main, ["export", str(project_dir), "--format", "w3c"])
        assert result.exit_code == 0, result.output
        assert "Exported to" in result.output

        export_dir = project_dir / "exports" / "w3c"
        assert export_dir.is_dir()
        exported_files = list(export_dir.glob("*.json"))
        assert len(exported_files) >= 1

        for ef in exported_files:
            data = json.loads(ef.read_text())
            assert data["type"] == "AnnotationCollection"
            assert "items" in data
            assert data["total"] >= 0

    def test_export_custom_output(self, runner, pp_ch1_txt, tmp_path):
        runner.invoke(main, [
            "ingest", str(pp_ch1_txt),
            "--workspace", str(tmp_path),
            "--title", "Custom Export",
        ])
        project_dir = tmp_path / PP_CH1_SLUG
        runner.invoke(main, ["analyze", str(project_dir)])
        custom_dir = tmp_path / "my-exports"
        result = runner.invoke(main, [
            "export", str(project_dir), "--format", "w3c", "-o", str(custom_dir),
        ])
        assert result.exit_code == 0
        assert custom_dir.is_dir()

    def test_export_w3c_has_id_field(self, runner, pp_ch1_txt, tmp_path):
        runner.invoke(main, [
            "ingest", str(pp_ch1_txt),
            "--workspace", str(tmp_path),
            "--title", "W3C ID Test",
        ])
        project_dir = tmp_path / PP_CH1_SLUG
        runner.invoke(main, ["analyze", str(project_dir)])
        result = runner.invoke(main, ["export", str(project_dir), "--format", "w3c"])
        assert result.exit_code == 0

        export_dir = project_dir / "exports" / "w3c"
        for ef in export_dir.glob("*.json"):
            data = json.loads(ef.read_text())
            assert "id" in data, f"Missing @id in {ef.name}"
            assert data["id"].startswith("urn:palimpsest:")

    def test_export_csv(self, runner, pp_ch1_txt, tmp_path):
        runner.invoke(main, [
            "ingest", str(pp_ch1_txt),
            "--workspace", str(tmp_path),
            "--title", "CSV Test",
        ])
        project_dir = tmp_path / PP_CH1_SLUG
        runner.invoke(main, ["analyze", str(project_dir)])
        result = runner.invoke(main, ["export", str(project_dir), "--format", "csv"])
        assert result.exit_code == 0, result.output
        assert "Exported to" in result.output

        export_dir = project_dir / "exports" / "csv"
        assert export_dir.is_dir()
        csv_files = list(export_dir.glob("*.csv"))
        assert len(csv_files) >= 1

        import csv as csv_mod

        for cf in csv_files:
            with cf.open() as f:
                reader = csv_mod.reader(f)
                header = next(reader)
                assert "id" in header
                assert "track" in header
                assert "start" in header
                assert "confidence" in header
                rows = list(reader)
                assert len(rows) > 0

    def test_export_paf(self, runner, pp_ch1_txt, tmp_path):
        runner.invoke(main, [
            "ingest", str(pp_ch1_txt),
            "--workspace", str(tmp_path),
            "--title", "PAF Test",
        ])
        project_dir = tmp_path / PP_CH1_SLUG
        result = runner.invoke(main, ["export", str(project_dir), "--format", "paf"])
        assert result.exit_code == 0
        assert "segments.paf" in result.output
        paf_file = project_dir / "exports" / "paf" / "segments.paf"
        assert paf_file.exists()
        lines = paf_file.read_text().strip().split("\n")
        assert lines[0].startswith("#")


class TestCliGold:
    """The `gold` command group — registry list, from-JSON verify, and apply error paths.

    list/verify are hermetic (no source text). The happy-path apply needs the copyrighted
    source binary, so it is a machine-local check (verified live); here we cover the two
    guarded exits — unknown id and source-absent — the latter via an empty imports dir."""

    def test_gold_list(self, runner):
        res = runner.invoke(main, ["gold", "list"])
        assert res.exit_code == 0, res.output
        assert "Gold Set" in res.output
        assert "216" in res.output  # a Bible
        assert "101" in res.output  # a non-Bible work — the registry is unified

    def test_gold_verify_single(self, runner):
        res = runner.invoke(main, ["gold", "verify", "216"])
        assert res.exit_code == 0, res.output
        assert "work-216" in res.output
        assert "verified" in res.output

    def test_gold_verify_all(self, runner):
        res = runner.invoke(main, ["gold", "verify"])
        assert res.exit_code == 0, res.output
        assert "work-107" in res.output  # a non-Bible work is in the unified registry
        assert "All 37 gold map(s) verified." in res.output

    def test_gold_apply_unknown_idx(self, runner, tmp_path):
        res = runner.invoke(main, ["gold", "apply", "999", str(tmp_path / "ws")])
        assert res.exit_code == 1
        assert "No gold work" in res.output

    def test_gold_apply_source_absent(self, runner, tmp_path, monkeypatch):
        empty = tmp_path / "empty"
        empty.mkdir()
        monkeypatch.setattr("palimpsest.server._default_imports_dir", lambda: empty)
        res = runner.invoke(main, ["gold", "apply", "216", str(tmp_path / "ws")])
        assert res.exit_code == 1
        assert "not present locally" in res.output

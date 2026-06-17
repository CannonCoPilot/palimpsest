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

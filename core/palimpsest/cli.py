"""Palimpsest CLI — ingest, analyze, info, serve, export."""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

from palimpsest import __version__
from palimpsest.project import Project, ingest_file
from palimpsest.tracks.registry import TrackRegistry

console = Console()


def _probe_embedding_dim() -> int | None:
    """Probe MLX or Ollama for embedding dimension. Returns dim or None."""
    import httpx

    # Try MLX first (much faster on Apple Silicon)
    try:
        resp = httpx.post(
            "http://localhost:8000/embed",
            json={"text": "probe"},
            timeout=3.0,
        )
        if resp.status_code == 200 and "embedding" in resp.json():
            return len(resp.json()["embedding"])
    except (httpx.ConnectError, httpx.TimeoutException):
        pass

    # Fall back to Ollama
    try:
        from palimpsest.services.manager import OllamaManager

        mgr = OllamaManager()
        client = mgr.embedding_client()
        probe = client.embed_one("probe")
        if probe is not None:
            return len(probe)
    except Exception:
        pass

    return None


@click.group()
@click.version_option(version=__version__)
def main() -> None:
    """Palimpsest — Computational Literary Analysis Platform."""


@main.command()
@click.argument("file", type=click.Path(exists=True, path_type=Path))
@click.option("--title", default="", help="Text title")
@click.option("--author", default="", help="Author name")
@click.option("--year", default=0, type=int, help="Year of publication")
@click.option("--workspace", default="projects", type=click.Path(path_type=Path))
def ingest(file: Path, title: str, author: str, year: int, workspace: Path) -> None:
    """Ingest a text file into a new project."""
    workspace.mkdir(parents=True, exist_ok=True)
    try:
        project = ingest_file(file, workspace, title=title, author=author, year=year)
        console.print(f"[green]Project created:[/green] {project.path}")
        console.print(f"  ID: {project.metadata.id}")
        console.print(f"  Words: {project.metadata.word_count:,}")
        console.print(f"  Paragraphs: {project.metadata.paragraph_count}")
        console.print(f"  Sentences: {project.metadata.sentence_count}")
    except FileExistsError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1) from e


@main.command()
@click.argument("project_dir", type=click.Path(exists=True, path_type=Path))
def info(project_dir: Path) -> None:
    """Show project metadata and track inventory."""
    project = Project.load(project_dir)
    m = project.metadata

    console.print(f"[bold]{m.title}[/bold]")
    if m.author:
        console.print(f"  Author: {m.author}")
    console.print(f"  Words: {m.word_count:,}")
    console.print(f"  Paragraphs: {m.paragraph_count}")
    console.print(f"  Sentences: {m.sentence_count}")
    console.print(f"  Sections: {m.section_count}")
    console.print(f"  SHA-256: {m.reference_sha256[:16]}...")

    tracks_dir = project_dir / "tracks"
    if tracks_dir.exists():
        track_files = sorted(tracks_dir.glob("*.jsonl"))
        console.print(f"\n[bold]Tracks ({len(track_files)}):[/bold]")
        for tf in track_files:
            line_count = sum(1 for line in tf.open() if line.strip())
            console.print(f"  {tf.name}: {line_count} annotations")

    signals_dir = project_dir / "signals"
    if signals_dir.exists():
        signal_files = sorted(signals_dir.glob("*.json"))
        if signal_files:
            console.print(f"\n[bold]Signals ({len(signal_files)}):[/bold]")
            for sf in signal_files:
                console.print(f"  {sf.stem}")


@main.command()
@click.argument("project_dir", type=click.Path(exists=True, path_type=Path))
@click.option("--force", is_flag=True, help="Recompute all tracks")
def analyze(project_dir: Path, force: bool) -> None:
    """Run track extraction on a project."""
    project = Project.load(project_dir)
    registry = TrackRegistry.discover()

    if not registry.all():
        console.print("[yellow]No track extractors registered.[/yellow]")
        return

    ordered = registry.dependency_order()
    computed_tracks: list[str] = []
    computed_signals: list[str] = []
    all_params: dict[str, Any] = {}
    start_time = datetime.now(UTC)

    # Embed paragraphs via MLX (preferred, ~14x faster) or Ollama (fallback)
    embeddings_db = project_dir / "cache" / "embeddings.db"
    if force or not embeddings_db.exists():
        try:
            from palimpsest.services.embedding import embed_paragraphs
            from palimpsest.vectorstore.sqlite_vec import SqliteVecStore

            dim = _probe_embedding_dim()
            if dim is not None:
                store = SqliteVecStore(embeddings_db, dim=dim)
                console.print(f"  Embedding paragraphs (dim={dim})...")
                count, backend = embed_paragraphs(
                    project, store, batch_size=32, max_concurrent=4,
                )
                store.close()
                if count > 0:
                    console.print(
                        f"  [green]Embedded {count} paragraphs via {backend}[/green]"
                    )
                else:
                    console.print("  Embeddings already up to date")
            else:
                console.print(
                    "  [yellow]No embedding service available "
                    "(need MLX on :8000 or Ollama on :11434)[/yellow]"
                )
        except Exception as e:
            console.print(f"  [yellow]⚠ Embedding skipped: {e}[/yellow]")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        for extractor_cls in ordered:
            extractor = extractor_cls()
            name = extractor.name

            output_exists = False
            if extractor.output_type == "annotation":
                output_exists = (project_dir / "tracks" / f"{name}.jsonl").exists()
            elif extractor.output_type == "signal":
                output_exists = (project_dir / "signals" / f"{name}.json").exists()

            if not force and output_exists:
                continue

            task_id = progress.add_task(f"  {name}", total=None)
            try:
                result = extractor.extract(project)
            except Exception as e:
                progress.update(task_id, completed=True)
                console.print(f"  [yellow]⚠ {name}: skipped ({type(e).__name__}: {e})[/yellow]")
                continue

            if extractor.output_type == "annotation":
                if not isinstance(result, list):
                    console.print(
                        f"  [yellow]⚠ {name}: unexpected return type "
                        f"({type(result).__name__}), skipping[/yellow]"
                    )
                    progress.update(task_id, completed=True)
                    continue
                from palimpsest.annotation.serializer import write_track

                track_path = project_dir / "tracks" / f"{name}.jsonl"
                write_track(track_path, result)
                computed_tracks.append(name)
            else:
                computed_signals.append(name)

            manifest_dir = project_dir / "manifests"
            manifest_dir.mkdir(exist_ok=True)
            manifest_path = manifest_dir / f"{name}.manifest.json"
            manifest_path.write_text(
                json.dumps(extractor.manifest(), indent=2),
                encoding="utf-8",
            )

            all_params.update(extractor.parameters())
            progress.update(task_id, completed=True)

    # Detect side-effect signals written by annotation tracks (e.g., topics_dist)
    signals_dir = project_dir / "signals"
    if signals_dir.is_dir():
        for sig_file in signals_dir.glob("*.json"):
            sig_name = sig_file.stem
            if sig_name not in computed_signals:
                computed_signals.append(sig_name)

    elapsed = (datetime.now(UTC) - start_time).total_seconds()

    booknlp_available = False
    try:
        import booknlp  # noqa: F401

        booknlp_available = True
    except ImportError:
        pass

    pipeline_run = {
        "run_id": uuid.uuid4().hex,
        "timestamp": datetime.now(UTC).isoformat(),
        "palimpsest_version": __version__,
        "python_version": sys.version.split()[0],
        "spacy_model": all_params.get("entities.spacy_model", "en_core_web_lg"),
        "booknlp_available": booknlp_available,
        "annotation_format": "W3C Web Annotation JSON-LD (JSONL)",
        "tracks_computed": computed_tracks,
        "signals_computed": computed_signals,
        "parameters": all_params,
        "elapsed_seconds": round(elapsed, 1),
    }

    (project_dir / "pipeline_run.json").write_text(
        json.dumps(pipeline_run, indent=2),
        encoding="utf-8",
    )

    total = len(computed_tracks) + len(computed_signals)
    console.print(
        f"[green]Done:[/green] {total} tracks computed in {elapsed:.1f}s"
    )
    console.print("[green]Pipeline run saved:[/green] pipeline_run.json")


@main.command()
@click.argument("project_dir", type=click.Path(exists=True, path_type=Path))
@click.option("--format", "fmt", type=click.Choice(["w3c", "paf", "csv"]), default="w3c")
@click.option("--output", "-o", type=click.Path(path_type=Path), default=None)
def export(project_dir: Path, fmt: str, output: Path | None) -> None:
    """Export annotations in the specified format."""
    Project.load(project_dir)  # validate project exists
    export_dir = output or (project_dir / "exports" / fmt)
    export_dir.mkdir(parents=True, exist_ok=True)

    tracks_dir = project_dir / "tracks"
    if not tracks_dir.exists():
        console.print("[yellow]No tracks to export.[/yellow]")
        return

    if fmt == "w3c":
        from palimpsest.annotation.serializer import read_track

        for track_file in sorted(tracks_dir.glob("*.jsonl")):
            anns = read_track(track_file)
            project_id = project_dir.name
            collection = {
                "@context": [
                    "http://www.w3.org/ns/anno.jsonld",
                    {"palimpsest": "https://palimpsest.dev/ns/"},
                ],
                "id": f"urn:palimpsest:{project_id}:collection:{track_file.stem}",
                "type": "AnnotationCollection",
                "label": track_file.stem,
                "total": len(anns),
                "items": [a.to_jsonld() for a in anns],
            }
            out_path = export_dir / f"{track_file.stem}.json"
            out_path.write_text(json.dumps(collection, indent=2, ensure_ascii=False))
            console.print(f"  {out_path.name}: {len(anns)} annotations")
    elif fmt == "paf":
        from palimpsest.annotation.serializer import read_track as read_track_paf

        for track_file in sorted(tracks_dir.glob("*.jsonl")):
            anns = read_track_paf(track_file)
            if not anns:
                continue
            out_path = export_dir / f"{track_file.stem}.paf"
            with out_path.open("w") as f:
                f.write(
                    "#annotation_id\ttrack\tlfo_type\tstart\tend\t"
                    "confidence\tevidence_level\tcreator\tvalue\tattributes\n"
                )
                for a in anns:
                    sel = a.target.selector
                    start = getattr(sel, "start", 0)
                    end = getattr(sel, "end", 0)
                    attrs = ";".join(
                        f"{k.replace('palimpsest:', '')}={v}"
                        for k, v in sorted(a.body.extra.items())
                    ) or "."
                    value = (a.body.value or ".")[:200]
                    f.write(
                        f"{a.id}\t{a.track_name}\t{a.body.lfo_type}\t"
                        f"{start}\t{end}\t{a.confidence}\t{a.evidence_level}\t"
                        f"{a.creator.name}\t{value}\t{attrs}\n"
                    )
            console.print(f"  {out_path.name}: {len(anns)} annotations")
    elif fmt == "csv":
        import csv

        from palimpsest.annotation.serializer import read_track as read_track_csv

        for track_file in sorted(tracks_dir.glob("*.jsonl")):
            anns = read_track_csv(track_file)
            if not anns:
                continue
            out_path = export_dir / f"{track_file.stem}.csv"
            with out_path.open("w", newline="") as f:
                writer = csv.writer(f)
                extra_keys = sorted(
                    {k for a in anns for k in a.body.extra}
                )
                header = [
                    "id", "track", "type", "start", "end",
                    "confidence", "evidence_level", "creator",
                    "value", *[k.replace("palimpsest:", "") for k in extra_keys],
                ]
                writer.writerow(header)
                for a in anns:
                    sel = a.target.selector
                    start = getattr(sel, "start", "")
                    end = getattr(sel, "end", "")
                    row = [
                        a.id,
                        a.track_name,
                        a.body.type.replace("palimpsest:", ""),
                        start,
                        end,
                        a.confidence,
                        a.evidence_level,
                        a.creator.name,
                        (a.body.value or "")[:200],
                        *[a.body.extra.get(k, "") for k in extra_keys],
                    ]
                    writer.writerow(row)
            console.print(f"  {out_path.name}: {len(anns)} rows")

    console.print(f"[green]Exported to:[/green] {export_dir}")


def _pidfile(port: int) -> Path:
    """Return the PID file path for a given port."""
    return Path.home() / ".palimpsest" / f"serve-{port}.pid"


def _kill_port(port: int) -> bool:
    """Kill any process on the given port. Returns True if something was killed."""
    result = subprocess.run(
        ["lsof", "-ti", f":{port}"],
        capture_output=True, text=True,
    )
    pids = [int(p) for p in result.stdout.strip().split("\n") if p.strip()]
    killed = False
    for pid in pids:
        try:
            os.kill(pid, signal.SIGTERM)
            killed = True
        except ProcessLookupError:
            pass
    if killed:
        time.sleep(0.5)
    return killed


@main.command()
@click.argument("workspace", type=click.Path(exists=True, path_type=Path))
@click.option("--port", default=8080, help="Server port")
def serve(workspace: Path, port: int) -> None:
    """Start the browser server (auto-kills previous instance on same port)."""
    from palimpsest.server import run_server

    pidfile = _pidfile(port)

    # Kill any previous palimpsest server on this port
    if pidfile.exists():
        try:
            old_pid = int(pidfile.read_text().strip())
            os.kill(old_pid, signal.SIGTERM)
            console.print(f"[yellow]Stopped previous server[/yellow] (PID {old_pid})")
            import time
            time.sleep(0.5)
        except (ProcessLookupError, ValueError, OSError):
            pass
        pidfile.unlink(missing_ok=True)

    # If port is still occupied (non-palimpsest process), kill it
    if _kill_port(port):
        console.print(f"[yellow]Killed stale process on port {port}[/yellow]")

    # Write PID file
    pidfile.parent.mkdir(parents=True, exist_ok=True)
    pidfile.write_text(str(os.getpid()))

    console.print(f"[green]Serving[/green] {workspace} on http://127.0.0.1:{port}")
    console.print("Press Ctrl+C to stop.")
    try:
        run_server(workspace, port=port)
    finally:
        pidfile.unlink(missing_ok=True)


@main.command()
@click.option("--port", default=8080, help="Server port to stop")
@click.option("--all", "stop_all", is_flag=True, help="Stop all palimpsest servers")
def stop(port: int, stop_all: bool) -> None:
    """Stop a running palimpsest server."""
    piddir = Path.home() / ".palimpsest"
    if not piddir.exists():
        console.print("[yellow]No servers running.[/yellow]")
        return

    targets = []
    if stop_all:
        targets = list(piddir.glob("serve-*.pid"))
    else:
        pf = _pidfile(port)
        if pf.exists():
            targets = [pf]

    if not targets:
        # Fall back to killing by port
        if _kill_port(port):
            console.print(f"[green]Killed process on port {port}[/green]")
        else:
            console.print(f"[yellow]No server found on port {port}.[/yellow]")
        return

    for pf in targets:
        try:
            pid = int(pf.read_text().strip())
            srv_port = pf.stem.replace("serve-", "")
            os.kill(pid, signal.SIGTERM)
            console.print(f"[green]Stopped server on port {srv_port}[/green] (PID {pid})")
        except (ProcessLookupError, ValueError, OSError):
            console.print(f"[dim]Stale PID file removed: {pf.name}[/dim]")
        pf.unlink(missing_ok=True)


@main.command()
def doctor() -> None:
    """Check system dependencies and report status."""
    checks: list[tuple[str, str, str]] = []

    # Python version
    checks.append(("Python", sys.version.split()[0], "ok"))

    # spaCy
    try:
        import spacy
        checks.append(("spaCy", spacy.__version__, "ok"))
        try:
            spacy.load("en_core_web_sm")
            checks.append(("  en_core_web_sm", "installed", "ok"))
        except OSError:
            checks.append(("  en_core_web_sm", "missing", "warn"))
        try:
            spacy.load("en_core_web_lg")
            checks.append(("  en_core_web_lg", "installed", "ok"))
        except OSError:
            checks.append(("  en_core_web_lg", "missing", "warn"))
    except ImportError:
        checks.append(("spaCy", "not installed", "error"))

    # ebooklib
    try:
        import ebooklib  # noqa: F401
        checks.append(("ebooklib", "installed", "ok"))
    except ImportError:
        checks.append(("ebooklib", "not installed", "warn"))

    # hmmlearn
    try:
        import hmmlearn  # noqa: F401
        checks.append(("hmmlearn", "installed", "ok"))
    except ImportError:
        checks.append(("hmmlearn", "not installed", "warn"))

    # BookNLP
    try:
        import booknlp  # noqa: F401
        checks.append(("BookNLP", "installed", "ok"))
    except ImportError:
        checks.append(("BookNLP", "not installed", "info"))

    # Ollama
    try:
        import httpx
        resp = httpx.get("http://localhost:11434/api/tags", timeout=3.0)
        if resp.status_code == 200:
            models = [m["name"] for m in resp.json().get("models", [])]
            checks.append(("Ollama", f"running ({len(models)} models)", "ok"))
        else:
            checks.append(("Ollama", "not responding", "warn"))
    except Exception:
        checks.append(("Ollama", "not running", "warn"))

    # MLX embeddings
    try:
        import httpx as httpx2
        resp = httpx2.post("http://localhost:8000/embed", json={"text": "probe"}, timeout=3.0)
        if resp.status_code == 200:
            dim = len(resp.json().get("embedding", []))
            checks.append(("MLX Embeddings", f"running (dim={dim})", "ok"))
        else:
            checks.append(("MLX Embeddings", "not responding", "warn"))
    except Exception:
        checks.append(("MLX Embeddings", "not running", "info"))

    # Browser dist
    browser_dist = Path(__file__).parent.parent.parent / "browser" / "dist"
    if browser_dist.is_dir() and (browser_dist / "index.html").exists():
        checks.append(("Browser dist", "built", "ok"))
    else:
        checks.append(("Browser dist", "not built (run: cd browser && npm run build)", "warn"))

    icons = {"ok": "[green]OK[/green]", "warn": "[yellow]WARN[/yellow]", "error": "[red]MISSING[/red]", "info": "[dim]optional[/dim]"}
    console.print("\n[bold]Palimpsest Doctor[/bold]\n")
    for name, status, level in checks:
        icon = icons.get(level, "")
        console.print(f"  {icon:>20s}  {name}: {status}")

    errors = [c for c in checks if c[2] == "error"]
    warns = [c for c in checks if c[2] == "warn"]
    if errors:
        console.print(f"\n[red]{len(errors)} critical issues.[/red] Fix these before using Palimpsest.")
    elif warns:
        console.print(f"\n[yellow]{len(warns)} warnings.[/yellow] Some features may be limited.")
    else:
        console.print("\n[green]All checks passed.[/green]")

    if any(c[0] == "  en_core_web_sm" and c[2] == "warn" for c in checks):
        console.print("\n  Fix: python -m spacy download en_core_web_sm")
    if any(c[0] == "Ollama" and c[2] == "warn" for c in checks):
        console.print("  Fix: ollama serve")


@main.command()
@click.argument("file", type=click.Path(exists=True, path_type=Path))
def validate(file: Path) -> None:
    """Validate a PAF file against the v0.1 spec."""
    valid_evidence = {"E1", "E2", "E3", "E4", "E5"}
    lfo_path = Path(__file__).parent.parent.parent / "specs" / "lfo-v0.1.json"
    valid_lfo: set[str] = set()
    if lfo_path.exists():
        lfo_data = json.loads(lfo_path.read_text())
        valid_lfo = set(lfo_data.get("terms", {}).keys())

    errors: list[str] = []
    line_count = 0

    with file.open() as f:
        for lineno, line in enumerate(f, 1):
            line = line.rstrip("\n")
            if line.startswith("#") or not line.strip():
                continue
            line_count += 1
            cols = line.split("\t")
            if len(cols) != 10:
                errors.append(f"  Line {lineno}: expected 10 columns, got {len(cols)}")
                continue

            _, _, lfo_type, start_s, end_s, conf_s, evidence, _, _, _ = cols

            if valid_lfo and lfo_type not in valid_lfo:
                errors.append(f"  Line {lineno}: unknown LFO type '{lfo_type}'")

            try:
                start_i, end_i = int(start_s), int(end_s)
                if start_i < 0 or end_i < 0:
                    errors.append(f"  Line {lineno}: negative offset")
                elif start_i >= end_i:
                    errors.append(f"  Line {lineno}: start >= end ({start_i} >= {end_i})")
            except ValueError:
                errors.append(f"  Line {lineno}: non-integer offsets")

            try:
                conf = float(conf_s)
                if not 0.0 <= conf <= 1.0:
                    errors.append(f"  Line {lineno}: confidence {conf} out of [0,1]")
            except ValueError:
                errors.append(f"  Line {lineno}: non-float confidence")

            if evidence not in valid_evidence:
                errors.append(f"  Line {lineno}: invalid evidence level '{evidence}'")

    if errors:
        console.print(f"[red]INVALID[/red] — {len(errors)} errors in {line_count} records:")
        for e in errors[:20]:
            console.print(e)
        if len(errors) > 20:
            console.print(f"  ... and {len(errors) - 20} more")
        raise SystemExit(1)
    else:
        console.print(f"[green]VALID[/green] — {line_count} records, no errors")

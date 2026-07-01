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
from palimpsest.atomic import atomic_write_text, write_run_provenance
from palimpsest.project import Project, ingest_file
from palimpsest.tracks.params import track_clamps, track_provenance
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
@click.option("--content-profile", "profile_name", default=None, help="Content filter profile (e.g., bible-kjv, bible-tyndale)")
def ingest(file: Path, title: str, author: str, year: int, workspace: Path, profile_name: str | None) -> None:
    """Ingest a text file into a new project."""
    workspace.mkdir(parents=True, exist_ok=True)
    profile = None
    if profile_name:
        from palimpsest.ingest.content_filters import get_profile
        profile = get_profile(profile_name)
    try:
        project = ingest_file(file, workspace, title=title, author=author, year=year, content_profile=profile)
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
    from palimpsest.runner import extract_masked

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
                result = extract_masked(project, extractor)
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
            atomic_write_text(
                manifest_dir / f"{name}.manifest.json",
                json.dumps(extractor.manifest(), indent=2),
            )
            # Per-track resolved-params record (C1), via the same writer the HTTP path uses.
            # `clamped` flags any param whose effective value differed from the request.
            clamped = track_clamps(extractor)
            write_run_provenance(
                manifest_dir, name, track_provenance(extractor),
                extra={"clamped": clamped} if clamped else None,
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

    atomic_write_text(
        project_dir / "pipeline_run.json",
        json.dumps(pipeline_run, indent=2),
    )

    total = len(computed_tracks) + len(computed_signals)
    console.print(
        f"[green]Done:[/green] {total} tracks computed in {elapsed:.1f}s"
    )
    console.print("[green]Pipeline run saved:[/green] pipeline_run.json")


@main.command(name="run-track")
@click.argument("project_dir", type=click.Path(exists=True, path_type=Path))
@click.argument("track_name")
@click.option(
    "--param", "-p", "param_pairs", multiple=True, metavar="KEY=VALUE",
    help="Track parameter as key=value (repeatable); coerced and validated by the track.",
)
@click.option(
    "--sep", "analyzable_sep", default="",
    help="Separator inserted between kept (unmasked) spans in the analyzable stream "
    "(default: '' — pure excision).",
)
def run_track(
    project_dir: Path, track_name: str, param_pairs: tuple[str, ...], analyzable_sep: str
) -> None:
    """Run a SINGLE track with explicit params — the CLI mirror of the HTTP per-track endpoint.

    For layer tracks (chunking, embedding) the produced layer is content-addressed, so a CLI run
    ACCUMULATES alongside layers produced from the UI: identical params yield the same label
    (idempotent, byte-identical artifact), different params yield a new label that coexists. Params
    are generic ``key=value`` pairs coerced and validated by the track itself — unknown keys and bad
    values are rejected — so no per-track flags are needed.
    """
    from palimpsest.runner import extract_masked, persist_track_outputs

    project = Project.load(project_dir)
    registry = TrackRegistry.discover()
    by_name = {cls().name: cls for cls in registry.dependency_order()}
    if track_name not in by_name:
        valid = ", ".join(sorted(by_name)) or "(none)"
        raise click.ClickException(f"Unknown track: {track_name!r}. Available: {valid}")
    extractor = by_name[track_name]()

    params: dict[str, Any] = {}
    for pair in param_pairs:
        if "=" not in pair:
            raise click.ClickException(f"Invalid -p {pair!r}: expected KEY=VALUE")
        key, value = pair.split("=", 1)
        params[key.strip()] = value

    # The same store-raw → coerce-and-validate flow the HTTP handler uses, so the CLI rejects unknown
    # keys, failed coercions, and missing required params identically (an HTTP 400 there is a non-zero
    # ClickException exit here). resolve_params coerces each string via the declared Param.type, which
    # is why generic key=value pairs suffice — no per-track typed options.
    if params and hasattr(extractor, "set_params"):
        try:
            extractor.set_params(params)
        except (ValueError, TypeError) as exc:
            raise click.ClickException(str(exc)) from exc
    resolved: dict[str, Any] | None = None
    if hasattr(extractor, "validate_params"):
        try:
            resolved = extractor.validate_params()
        except ValueError as exc:
            raise click.ClickException(str(exc)) from exc

    result = extract_masked(project, extractor, analyzable_sep)
    pname = persist_track_outputs(project_dir, extractor, result)

    console.print(f"  analyzable_sep: {analyzable_sep!r}")
    if resolved:
        console.print(f"  params: {resolved}")
    if isinstance(result, Path):
        label = pname[len(track_name) + 1:] if pname.startswith(f"{track_name}_") else pname
        console.print(f"[green]Layer produced:[/green] {track_name} (label {label})")
        console.print(f"  {result}")
    elif isinstance(result, list):
        console.print(
            f"[green]Done:[/green] {track_name} — {len(result)} annotations "
            f"-> tracks/{track_name}.jsonl"
        )
    else:
        console.print(f"[green]Done:[/green] {track_name} (signal)")
    console.print(f"  provenance: manifests/{pname}.run.json")


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
        checks.append(("spaCy", spacy.__version__, "ok"))  # pyright: ignore[reportPrivateImportUsage]
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
        import hmmlearn  # type: ignore[import-not-found]  # noqa: F401
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


@main.command(name="dedup-ids")
@click.argument("workspace", type=click.Path(exists=True, path_type=Path))
@click.option("--apply", "apply_changes", is_flag=True, help="Apply the renames (default: dry-run)")
def dedup_ids(workspace: Path, apply_changes: bool) -> None:
    """Migrate legacy project IDs to deterministic source-file slugs.

    Earlier imports derived a project's ID from its title, so the same source file
    could land under two different IDs (a duplicate). This renames each project
    directory to the canonical slug derived from its source file and rewrites the
    baked ``urn:palimpsest:<id>`` references inside. Same-source duplicates (two
    projects whose source files slug to one ID) are reported, not deleted — resolve
    those by hand. Dry-run by default; pass --apply to make changes.
    """
    from palimpsest.project import _make_slug

    renames: list[tuple[Path, str]] = []
    conflicts: list[tuple[str, str]] = []
    claimed: set[str] = set()
    for p in sorted(workspace.iterdir()):
        meta_path = p / "metadata.json"
        if not meta_path.exists():
            continue
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        src = meta.get("source_file") or ""
        if not src:
            console.print(f"[yellow]skip[/yellow] {p.name}: no source_file recorded")
            continue
        new_slug = _make_slug(src)
        if p.name == new_slug:
            claimed.add(new_slug)
            continue
        if (workspace / new_slug).exists() or new_slug in claimed:
            conflicts.append((p.name, new_slug))
            continue
        claimed.add(new_slug)
        renames.append((p, new_slug))

    for old_dir, new_slug in renames:
        console.print(f"[cyan]rename[/cyan] {old_dir.name}\n        -> {new_slug}")
    for old_name, new_slug in conflicts:
        console.print(
            f"[red]conflict[/red] {old_name}: canonical slug already exists "
            f"(duplicate source) -> {new_slug} — resolve by hand"
        )

    if not apply_changes:
        console.print(
            f"\n[bold]Dry run[/bold]: {len(renames)} rename(s), {len(conflicts)} conflict(s). "
            f"Re-run with --apply to make changes."
        )
        return

    rewrite_suffixes = {".json", ".jsonl", ".csv"}
    for old_dir, new_slug in renames:
        old_slug = old_dir.name
        old_urn = f"urn:palimpsest:{old_slug}"
        new_urn = f"urn:palimpsest:{new_slug}"
        for f in old_dir.rglob("*"):
            if not f.is_file() or f.suffix.lower() not in rewrite_suffixes:
                continue
            try:
                content = f.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            if old_urn in content:
                f.write_text(content.replace(old_urn, new_urn), encoding="utf-8")
        meta_path = old_dir / "metadata.json"
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        meta["id"] = new_slug
        meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
        old_dir.rename(workspace / new_slug)
        console.print(f"[green]renamed[/green] {old_slug} -> {new_slug}")

    console.print(
        f"\n[green]Done[/green]: {len(renames)} renamed, {len(conflicts)} conflict(s) left for manual review."
    )


@main.group()
def collections() -> None:
    """Manage collections — named groupings of related projects (Collections tier, FR-37 parity)."""


@collections.command("list")
@click.argument("workspace", type=click.Path(exists=True, path_type=Path))
def collections_list(workspace: Path) -> None:
    """List all collections with member counts."""
    from palimpsest.collections import load_collections

    cols = load_collections(workspace)
    if not cols:
        console.print("[yellow]No collections.[/yellow]")
        return
    for c in cols:
        console.print(
            f"[cyan]{c['id']}[/cyan] ({c.get('kind', 'manual')}) — {c.get('label', c['id'])}: "
            f"{len(c.get('project_ids', []))} member(s)"
        )


@collections.command("show")
@click.argument("workspace", type=click.Path(exists=True, path_type=Path))
@click.argument("collection_id")
def collections_show(workspace: Path, collection_id: str) -> None:
    """Show a collection and its members (with collection-local roles)."""
    from palimpsest.collections import get_collection, member_role

    col = get_collection(workspace, collection_id)
    if col is None:
        console.print(f"[red]Collection '{collection_id}' not found.[/red]")
        raise SystemExit(1)
    console.print(f"[bold]{col.get('label', collection_id)}[/bold] ({col.get('kind', 'manual')})")
    for pid in col.get("project_ids", []):
        console.print(f"  - {pid} [dim]({member_role(col, pid)})[/dim]")


@collections.command("create")
@click.argument("workspace", type=click.Path(exists=True, path_type=Path))
@click.argument("label")
@click.option("--project", "projects", multiple=True, help="Member project id (repeatable)")
@click.option("--description", default="", help="Collection description")
def collections_create(workspace: Path, label: str, projects: tuple[str, ...], description: str) -> None:
    """Create a manual collection."""
    from palimpsest.collections import create_collection

    col = create_collection(workspace, label, description, list(projects))
    console.print(f"[green]Created[/green] collection [cyan]{col['id']}[/cyan] with {len(projects)} member(s).")


@collections.command("add-member")
@click.argument("workspace", type=click.Path(exists=True, path_type=Path))
@click.argument("collection_id")
@click.argument("project_id")
def collections_add_member(workspace: Path, collection_id: str, project_id: str) -> None:
    """Add a project to a collection."""
    from palimpsest.collections import add_member

    if add_member(workspace, collection_id, project_id) is None:
        console.print(f"[red]Collection '{collection_id}' not found.[/red]")
        raise SystemExit(1)
    console.print(f"[green]Added[/green] {project_id} -> {collection_id}.")


@collections.command("remove-member")
@click.argument("workspace", type=click.Path(exists=True, path_type=Path))
@click.argument("collection_id")
@click.argument("project_id")
def collections_remove_member(workspace: Path, collection_id: str, project_id: str) -> None:
    """Remove a project from a collection."""
    from palimpsest.collections import remove_member

    if remove_member(workspace, collection_id, project_id) is None:
        console.print(f"[red]Collection '{collection_id}' not found.[/red]")
        raise SystemExit(1)
    console.print(f"[green]Removed[/green] {project_id} from {collection_id}.")


@collections.command("role")
@click.argument("workspace", type=click.Path(exists=True, path_type=Path))
@click.argument("collection_id")
@click.argument("project_id")
@click.argument("role", type=click.Choice(["member", "root"]))
def collections_role(workspace: Path, collection_id: str, project_id: str, role: str) -> None:
    """Set a member's collection-local role (member | root lens)."""
    from palimpsest.collections import set_member_role

    try:
        col = set_member_role(workspace, collection_id, project_id, role)
    except ValueError as exc:
        console.print(f"[red]{exc}[/red]")
        raise SystemExit(1)
    if col is None:
        console.print(f"[red]Collection '{collection_id}' not found.[/red]")
        raise SystemExit(1)
    console.print(f"[green]Set[/green] {project_id} role -> {role} in {collection_id}.")


@collections.command("lattice")
@click.argument("workspace", type=click.Path(exists=True, path_type=Path))
@click.argument("project_id")
def collections_lattice(workspace: Path, project_id: str) -> None:
    """Show a project's membership lattice (work, parent, children, siblings, collections)."""
    from palimpsest.collections_ops import project_lattice

    try:
        lat = project_lattice(workspace, project_id)
    except (FileNotFoundError, ValueError) as exc:
        console.print(f"[red]{exc}[/red]")
        raise SystemExit(1)
    console.print(json.dumps(lat, indent=2))


@collections.command("congruence")
@click.argument("workspace", type=click.Path(exists=True, path_type=Path))
@click.argument("collection_id")
@click.option("--metric", default="cosine", help="Metric to test congruence on")
@click.option("--embedding-label", default=None, help="Specific embedding layer label")
def collections_congruence(
    workspace: Path, collection_id: str, metric: str, embedding_label: str | None
) -> None:
    """Report per-metric congruence across a collection's members (the compatibility badge data)."""
    from palimpsest.collections_ops import congruence_report

    try:
        rep = congruence_report(workspace, collection_id, metric, embedding_label)
    except KeyError:
        console.print(f"[red]Collection '{collection_id}' not found.[/red]")
        raise SystemExit(1)
    except ValueError as exc:
        console.print(f"[red]{exc}[/red]")
        raise SystemExit(1)
    badge = "[green]congruent[/green]" if rep["all_congruent"] else "[yellow]incongruent[/yellow]"
    console.print(f"metric [cyan]{metric}[/cyan]: {badge}")
    for pid in rep["members"]:
        key = rep["keys"].get(pid)
        console.print(f"  - {pid}: {key if key else '[red](missing layer)[/red]'}")


@collections.command("corpus-graph-build")
@click.argument("workspace", type=click.Path(exists=True, path_type=Path))
@click.argument("collection_id")
@click.option("--anchor-trim", type=float, default=0.0,
              help="Trim aligned blocks past boundary cells below this cross-similarity before the "
                   "homology union (C6a anchor honesty; 0 = off)")
def collections_corpus_graph_build(workspace: Path, collection_id: str, anchor_trim: float) -> None:
    """Assemble + persist the reference-free corpus graph (C3) from the collection's pairwise edges."""
    from palimpsest.corpus_graph import build_corpus_graph, write_corpus_graph

    try:
        graph = build_corpus_graph(workspace, collection_id, anchor_trim=anchor_trim)
    except ValueError as exc:
        console.print(f"[red]{exc}[/red]")
        raise SystemExit(1)
    write_corpus_graph(workspace, collection_id, graph)
    s = graph.summary
    console.print(
        f"corpus graph [cyan]{collection_id}[/cyan]: {s['n_members']} members, {s['n_nodes']} nodes, "
        f"{s['n_edges']} edges → [green]{s['core']} core[/green] / "
        f"[yellow]{s['shell']} shell[/yellow] / {s['singleton']} singleton"
    )
    if s["pairs_missing"]:
        console.print(f"  [yellow]pairs without edges:[/yellow] {s['pairs_missing']}")


@collections.command("corpus-graph-show")
@click.argument("workspace", type=click.Path(exists=True, path_type=Path))
@click.argument("collection_id")
def collections_corpus_graph_show(workspace: Path, collection_id: str) -> None:
    """Print the persisted corpus graph (nodes, edges, components, summary) as JSON."""
    from palimpsest.corpus_graph import read_corpus_graph

    graph = read_corpus_graph(workspace, collection_id)
    if graph is None:
        console.print(f"[red]No corpus graph for '{collection_id}'; run corpus-graph-build first.[/red]")
        raise SystemExit(1)
    console.print(json.dumps(graph.to_dict(), indent=2))


@collections.command("corpus-graph-project")
@click.argument("workspace", type=click.Path(exists=True, path_type=Path))
@click.argument("collection_id")
@click.option("--root", required=True, help="Member project id to project the graph onto")
def collections_corpus_graph_project(workspace: Path, collection_id: str, root: str) -> None:
    """Project the corpus graph onto a chosen root member's paragraph frame (the synteny lens)."""
    from palimpsest.corpus_graph import project_to_root, read_corpus_graph

    graph = read_corpus_graph(workspace, collection_id)
    if graph is None:
        console.print(f"[red]No corpus graph for '{collection_id}'; run corpus-graph-build first.[/red]")
        raise SystemExit(1)
    try:
        console.print(json.dumps(project_to_root(graph, root), indent=2))
    except ValueError as exc:
        console.print(f"[red]{exc}[/red]")
        raise SystemExit(1)


@collections.command("phyletic-tree")
@click.argument("workspace", type=click.Path(exists=True, path_type=Path))
@click.argument("collection_id")
@click.option("--root", default=None, help="Member to root the tree on (default: suggested backbone)")
def collections_phyletic_tree(workspace: Path, collection_id: str, root: str | None) -> None:
    """Phyletic/stemma tree over the corpus graph's distance structure (neighbor-joining + auto-root)."""
    from palimpsest.corpus_graph import phyletic_tree, read_corpus_graph

    graph = read_corpus_graph(workspace, collection_id)
    if graph is None:
        console.print(f"[red]No corpus graph for '{collection_id}'; run corpus-graph-build first.[/red]")
        raise SystemExit(1)
    try:
        console.print(json.dumps(phyletic_tree(graph, root), indent=2))
    except ValueError as exc:
        console.print(f"[red]{exc}[/red]")
        raise SystemExit(1)


@collections.command("corpus-analyses")
@click.argument("workspace", type=click.Path(exists=True, path_type=Path))
@click.argument("collection_id")
@click.option("--duplicate-threshold", type=float, default=0.15, show_default=True,
              help="Max pangenome distance to cluster members as near-duplicates")
@click.option("--top-terms", type=int, default=25, show_default=True, help="Terms to list per band")
def collections_corpus_analyses(
    workspace: Path, collection_id: str, duplicate_threshold: float, top_terms: int
) -> None:
    """Corpus analyses over the graph + member texts (C6a): boilerplate/IDF, near-duplicate clusters,
    undirected diffusion/spread."""
    from palimpsest.corpus_graph import corpus_analyses, read_corpus_graph

    graph = read_corpus_graph(workspace, collection_id)
    if graph is None:
        console.print(f"[red]No corpus graph for '{collection_id}'; run corpus-graph-build first.[/red]")
        raise SystemExit(1)
    console.print(json.dumps(corpus_analyses(
        workspace, graph, duplicate_threshold=duplicate_threshold, top_terms=top_terms), indent=2))


@collections.command("corpus-repeats")
@click.argument("workspace", type=click.Path(exists=True, path_type=Path))
@click.argument("collection_id")
@click.option("--min-members", default=2, show_default=True, help="Distinct members a phrase must span")
def collections_corpus_repeats(workspace: Path, collection_id: str, min_members: int) -> None:
    """Phrases recurring across >= min-members members, with per-member intervals (C5, FR-29)."""
    from palimpsest.collections_masking import corpus_repeats

    try:
        console.print(json.dumps(
            corpus_repeats(workspace, collection_id, min_members=min_members), indent=2))
    except ValueError as exc:
        console.print(f"[red]{exc}[/red]")
        raise SystemExit(1)


@collections.command("cross-text-mask")
@click.argument("workspace", type=click.Path(exists=True, path_type=Path))
@click.argument("collection_id")
@click.argument("member")
def collections_cross_text_mask(workspace: Path, collection_id: str, member: str) -> None:
    """A member's cross-text mask: corpus-repeat ∪ low-correspondence intervals (C5, FR-29)."""
    from palimpsest.collections_masking import cross_text_mask

    try:
        console.print(json.dumps(cross_text_mask(workspace, collection_id, member), indent=2))
    except ValueError as exc:
        console.print(f"[red]{exc}[/red]")
        raise SystemExit(1)


@collections.command("root-track")
@click.argument("workspace", type=click.Path(exists=True, path_type=Path))
@click.argument("collection_id")
@click.option("--root", required=True, help="Member to express the cross-text track on")
def collections_root_track(workspace: Path, collection_id: str, root: str) -> None:
    """A cross-text conservation track on the root member's coordinate frame (C5, FR-30)."""
    from palimpsest.collections_masking import cross_text_track

    try:
        console.print(json.dumps(cross_text_track(workspace, collection_id, root), indent=2))
    except ValueError as exc:
        console.print(f"[red]{exc}[/red]")
        raise SystemExit(1)


@collections.command("liftover")
@click.argument("workspace", type=click.Path(exists=True, path_type=Path))
@click.argument("source_id")
@click.argument("target_id")
@click.option("--interval", "intervals", multiple=True, metavar="START:END",
              help="Source char interval to project (repeatable)")
def collections_liftover(
    workspace: Path, source_id: str, target_id: str, intervals: tuple[str, ...]
) -> None:
    """Project source intervals onto the target's frame across their alignment (C5, FR-42)."""
    from palimpsest.collections_masking import lift_intervals_across

    parsed: list[tuple[int, int]] = []
    for iv in intervals:
        s, _, e = iv.partition(":")
        parsed.append((int(s), int(e)))
    try:
        console.print(json.dumps(
            lift_intervals_across(workspace, source_id, target_id, parsed), indent=2))
    except ValueError as exc:
        console.print(f"[red]{exc}[/red]")
        raise SystemExit(1)


@main.command(name="align-paf")
@click.argument("workspace", type=click.Path(exists=True, path_type=Path))
@click.argument("query_id")
@click.argument("target_id")
@click.option("--output", "-o", type=click.Path(path_type=Path), default=None, help="Write PAF here (else stdout)")
@click.option("--min-score", type=float, default=None, help="Only export records scoring >= this")
def align_paf(
    workspace: Path, query_id: str, target_id: str, output: Path | None, min_score: float | None
) -> None:
    """Export a computed pairwise alignment as minimap2 PAF (FR-36)."""
    from palimpsest.alignment.records import (
        comparison_dir,
        read_alignment_records,
        records_to_paf,
    )

    comp = comparison_dir(workspace, query_id, target_id)
    rec_path = comp / "alignment.jsonl"
    if not rec_path.exists():
        console.print(f"[red]No alignment results at {comp}[/red]")
        raise SystemExit(1)
    records = read_alignment_records(rec_path)
    if min_score is not None:
        records = [r for r in records if r.score >= min_score]

    def _cc(pid: str) -> int:
        mp = workspace / pid / "metadata.json"
        if mp.exists():
            try:
                return int(json.loads(mp.read_text(encoding="utf-8")).get("character_count", 0))
            except (ValueError, json.JSONDecodeError):
                pass
        return 0

    lines = records_to_paf(records, _cc(query_id), _cc(target_id))
    text = "\n".join(lines) + ("\n" if lines else "")
    if output:
        output.write_text(text, encoding="utf-8")
        console.print(f"[green]Wrote[/green] {len(records)} record(s) -> {output}")
    else:
        click.echo(text)

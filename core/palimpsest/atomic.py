"""Atomic filesystem writes + run-provenance records (guard-rail G3).

A truncate-in-place write (``open(path, "w")``, ``Path.write_text``) leaves a torn file if the
process dies — or the file is read — between truncating it and writing the final byte. A concurrent
reader (e.g. the analysis-status poller reading a manifest while a job rewrites it, finding C3) can
then observe half a file. These helpers write to a temporary file in the SAME directory and
``os.replace`` it into place: a reader sees either the old file or the new file, never a partial one
(``os.replace`` is atomic within a single filesystem).
"""

from __future__ import annotations

import json
import os
import tempfile
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def atomic_write_bytes(path: Path, data: bytes) -> None:
    """Write ``data`` to ``path`` atomically (temp file in the same dir, fsync, then ``os.replace``)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        # Never leave the temp file behind if the write or replace fails.
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def atomic_write_text(path: Path, text: str, *, encoding: str = "utf-8") -> None:
    """Write ``text`` to ``path`` atomically. See :func:`atomic_write_bytes`."""
    atomic_write_bytes(path, text.encode(encoding))


def write_run_provenance(
    manifest_dir: Path,
    track_name: str,
    parameters: dict[str, Any],
    *,
    extra: dict[str, Any] | None = None,
) -> Path:
    """Persist a track run's resolved parameters to ``manifests/{track}.run.json`` atomically.

    The single provenance writer shared by the HTTP and CLI run paths, so a UI-driven run is no
    longer the only entry point without a param record on disk (finding C1). The record carries
    enough to reconstruct *what ran*: the resolved parameters, a run id, a UTC timestamp, and the
    palimpsest version."""
    from palimpsest import __version__

    record: dict[str, Any] = {
        "track": track_name,
        "run_id": uuid.uuid4().hex,
        "timestamp": datetime.now(UTC).isoformat(),
        "palimpsest_version": __version__,
        "parameters": parameters,
    }
    if extra:
        record.update(extra)
    manifest_dir = Path(manifest_dir)
    manifest_dir.mkdir(parents=True, exist_ok=True)
    path = manifest_dir / f"{track_name}.run.json"
    atomic_write_text(path, json.dumps(record, indent=2, ensure_ascii=False))
    return path

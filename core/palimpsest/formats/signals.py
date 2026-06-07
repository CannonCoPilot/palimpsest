"""Signal format I/O: raw binary Float32 + JSON manifest.

Signals are non-annotation numerical data (matrices, vectors, sequences)
that don't fit the W3C annotation model. Stored as little-endian Float32
binary files alongside JSON manifests describing their shape and metadata.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np


@dataclass
class SignalManifest:
    """Metadata for a signal binary file."""

    type: str
    name: str
    source: str
    reference_sha256: str
    dimensions: list[int]
    dtype: str = "float32"
    byte_order: str = "little-endian"
    data_file: str = ""
    segment_offsets: list[list[int]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "name": self.name,
            "source": self.source,
            "reference_sha256": self.reference_sha256,
            "dimensions": self.dimensions,
            "dtype": self.dtype,
            "byte_order": self.byte_order,
            "data_file": self.data_file,
            "segment_offsets": self.segment_offsets,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> SignalManifest:
        return cls(
            type=d["type"],
            name=d["name"],
            source=d["source"],
            reference_sha256=d.get("reference_sha256", ""),
            dimensions=d["dimensions"],
            dtype=d.get("dtype", "float32"),
            byte_order=d.get("byte_order", "little-endian"),
            data_file=d.get("data_file", ""),
            segment_offsets=d.get("segment_offsets", []),
            metadata=d.get("metadata", {}),
        )


def write_signal(
    signals_dir: Path,
    data: np.ndarray,
    manifest: SignalManifest,
) -> None:
    """Write a signal as raw binary + JSON manifest."""
    signals_dir.mkdir(parents=True, exist_ok=True)

    if not manifest.data_file:
        manifest.data_file = f"{manifest.name}.bin"

    data.astype(np.float32).tofile(signals_dir / manifest.data_file)

    manifest_path = signals_dir / f"{manifest.name}.json"
    manifest_path.write_text(
        json.dumps(manifest.to_dict(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def read_signal(signals_dir: Path, manifest_name: str) -> tuple[SignalManifest, np.ndarray]:
    """Read a signal from binary + JSON manifest. Returns (manifest, data)."""
    manifest_path = signals_dir / f"{manifest_name}.json"
    manifest = SignalManifest.from_dict(json.loads(manifest_path.read_text()))

    data_path = signals_dir / manifest.data_file
    arr = np.fromfile(data_path, dtype=np.float32)

    if manifest.dimensions:
        arr = arr.reshape(manifest.dimensions)

    return manifest, arr

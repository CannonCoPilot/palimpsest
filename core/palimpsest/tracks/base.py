"""TrackExtractor protocol for Palimpsest track system.

All track extractors implement the TrackExtractor protocol via structural
subtyping — no inheritance required. The TrackRegistry discovers conforming
classes via isinstance() checks after importing track modules.

Architectural reference: JBrowse 2 TrackAdapter pattern (ADR-005).
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from palimpsest.annotation.model import Annotation


@runtime_checkable
class TrackExtractor(Protocol):
    """Protocol for all track extractors.

    Any class with these attributes/methods satisfies the protocol
    without needing to inherit from this class.
    """

    @property
    def name(self) -> str:
        """Unique track name (e.g., 'entities', 'sentiment')."""
        ...

    @property
    def output_type(self) -> str:
        """Either 'annotation' (produces JSONL) or 'signal' (produces binary + manifest)."""
        ...

    @property
    def depends_on(self) -> list[str]:
        """Track names this extractor depends on. Underscore prefix = virtual."""
        ...

    @property
    def lfo_types(self) -> list[str]:
        """LFO type strings produced by this track."""
        ...

    @property
    def evidence_level(self) -> str:
        """Default evidence level for annotations from this track."""
        ...

    def extract(self, project: Any) -> list[Annotation] | Path:
        """Run extraction. Returns annotations (for annotation tracks)
        or a signal directory path (for signal tracks)."""
        ...

    def manifest(self) -> dict[str, Any]:
        """Track rendering manifest for the browser."""
        ...

    def parameters(self) -> dict[str, Any]:
        """Return parameter dict for pipeline_run.json provenance."""
        ...

"""W3C Web Annotation model and serialization for Palimpsest."""

from palimpsest.annotation.model import (
    Annotation,
    Body,
    Creator,
    Target,
    TextPositionSelector,
    TextQuoteSelector,
)
from palimpsest.annotation.serializer import read_track, validate_annotation, write_track

__all__ = [
    "Annotation",
    "Body",
    "Creator",
    "Target",
    "TextPositionSelector",
    "TextQuoteSelector",
    "read_track",
    "validate_annotation",
    "write_track",
]

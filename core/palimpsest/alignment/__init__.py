"""Pairwise text alignment engine for Palimpsest M3.

Provides Smith-Waterman local alignment with pluggable scoring (SBERT cosine,
word overlap, narrative alphabet), Gumbel-calibrated significance testing,
and cross-text similarity matrix computation.
"""

from palimpsest.alignment.records import AlignmentRecord

__all__ = ["AlignmentRecord"]

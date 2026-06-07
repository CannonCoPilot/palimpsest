"""Shared test fixtures for Palimpsest."""

from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"
ROOT_FIXTURES_DIR = Path(__file__).parent.parent.parent / "fixtures"


@pytest.fixture
def pp_ch1_txt() -> Path:
    """Pride and Prejudice Chapter 1 as plain text."""
    p = FIXTURES_DIR / "pride-prejudice-ch1.txt"
    assert p.exists(), f"Missing fixture: {p}"
    return p


@pytest.fixture
def md_ch1_txt() -> Path:
    """Moby-Dick Chapter 1 as plain text."""
    p = FIXTURES_DIR / "moby-dick-ch1.txt"
    assert p.exists(), f"Missing fixture: {p}"
    return p


@pytest.fixture
def pp_full_txt() -> Path:
    """Full Pride and Prejudice text (root fixtures dir, for benchmarks)."""
    p = ROOT_FIXTURES_DIR / "pride-prejudice-full.txt"
    assert p.exists(), f"Missing fixture: {p}"
    return p


@pytest.fixture
def expected_dir() -> Path:
    """Directory for expected regression outputs."""
    d = FIXTURES_DIR / "expected"
    d.mkdir(exist_ok=True)
    return d

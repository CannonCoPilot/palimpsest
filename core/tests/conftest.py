"""Shared test fixtures for Palimpsest."""

from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"
ROOT_FIXTURES_DIR = Path(__file__).parent.parent.parent / "fixtures"


# These fixtures only resolve a static, read-only path, so session scope is safe
# and lets module/session-scoped fixtures (e.g. analyzed_project) depend on them.
@pytest.fixture(scope="session")
def pp_ch1_txt() -> Path:
    """Pride and Prejudice Chapter 1 as plain text."""
    p = FIXTURES_DIR / "pride-prejudice-ch1.txt"
    assert p.exists(), f"Missing fixture: {p}"
    return p


@pytest.fixture(scope="session")
def md_ch1_txt() -> Path:
    """Moby-Dick Chapter 1 as plain text."""
    p = FIXTURES_DIR / "moby-dick-ch1.txt"
    assert p.exists(), f"Missing fixture: {p}"
    return p


@pytest.fixture(scope="session")
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


# --- Auto-marking -----------------------------------------------------------
# Tests self-classify at collection time, so new tests inherit the right markers
# without manual tagging. Loading a spaCy model is the expensive, state-leaking-est
# thing a test can do, so the default classification is the heavier nlp+integration
# and we allowlist the modules that are genuinely cheap (pure functions, regex, data,
# light IO). Module/marker definitions live in pyproject.toml [tool.pytest].markers.
_UNIT_MODULES = frozenset({
    "test_self_similarity", "test_annotation", "test_alignment",
    "test_alphabet_align", "test_edition_diff", "test_content_filters",
    "test_registry", "test_vectorstore", "test_layout",
    "test_boundary_detection", "test_ingest", "test_epub_parser",
    "test_characters", "test_extractor", "test_gold_maps", "test_gold_canon",
})
_API_MODULES = frozenset({"test_server", "test_sections_api"})
_CLI_MODULES = frozenset({"test_cli"})
# Fixtures whose setup ingests text and therefore loads a spaCy model.
_NLP_FIXTURES = frozenset({
    "pp_project", "analyzed_project", "workspace_with_project",
    "client", "small_project",
})


def pytest_collection_modifyitems(config, items):
    for item in items:
        stem = item.path.stem
        fixtures = set(getattr(item, "fixturenames", ()))

        if stem in _API_MODULES:
            item.add_marker("api")
        if stem in _CLI_MODULES:
            item.add_marker("cli")

        if stem not in _UNIT_MODULES or fixtures & _NLP_FIXTURES:
            item.add_marker("nlp")
            item.add_marker("integration")
        else:
            item.add_marker("unit")

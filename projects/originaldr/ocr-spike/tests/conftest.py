# -*- coding: utf-8 -*-
"""pytest bootstrap for the OriginalDR reOCR spike test-suite.

Puts the ocr-spike dir on sys.path so `import verse_seg`, `import verse_geom`, etc. resolve exactly as the
production modules do (they `sys.path.insert(0, HERE)` themselves). Tests are hermetic where possible: the
geometry/segmentation/ledger units are exercised on synthetic dicts (no kraken, no 15GB model, no images), so
the suite runs in milliseconds; the few genuinely-integration checks (real MLX, real segmentation) are marked
`@pytest.mark.slow` and skipped by default (run with `-m slow`).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

SPIKE = Path(__file__).resolve().parent.parent
if str(SPIKE) not in sys.path:
    sys.path.insert(0, str(SPIKE))


def pytest_configure(config):
    config.addinivalue_line("markers", "slow: integration test (real MLX / kraken / images) — run with -m slow")


@pytest.fixture(scope="session")
def spike_dir() -> Path:
    return SPIKE

# -*- coding: utf-8 -*-
"""TDD spec for mlx_client.MLXWorker — the load-once MLX worker (§8 R3-1 productionization).

The current R3 MLX path subprocess-reloads the 15GB olmOCR model on EVERY crop (~30-60s each) — prohibitive for
batch R3 over many flagged verses. MLXWorker keeps ONE long-lived server process (model loaded once) and streams
per-crop requests over stdin/stdout. These tests exercise the client protocol against a pure-Python fake server
(no model, instant), so the framing / READY handshake / correlation / error / timeout+restart logic is pinned
without a 15GB load. A single real smoke test (test_mlx_server_smoke, slow) proves the real server loads once.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

import mlx_client

FAKE = str(Path(__file__).resolve().parent / "fake_mlx_server.py")
PYEXE = sys.executable          # the fake server is pure-python -> run it in the same interpreter as the tests


def _worker(**kw):
    kw.setdefault("call_timeout", 10)
    kw.setdefault("ready_timeout", 10)
    return mlx_client.MLXWorker(venv_py=PYEXE, server_script=FAKE, model="fake", **kw)


def test_worker_transcribes_and_reuses_one_process():
    """Two calls return the canned transcript AND run on the SAME pid — the load-once guarantee."""
    with _worker() as w:
        t1 = w.transcribe("/tmp/a.png", max_tokens=1234)
        pid1 = w.pid
        t2 = w.transcribe("/tmp/b.png", max_tokens=4000)
        pid2 = w.pid
        assert "TRANSCRIPT for /tmp/a.png" in t1 and "mt=1234" in t1
        assert "TRANSCRIPT for /tmp/b.png" in t2 and "mt=4000" in t2
        assert pid1 == pid2 and pid1 is not None, "the model process must be reused across calls (loaded once)"


def test_worker_strips_delimiters_and_pre_ready_noise():
    """The returned text is the payload only — no delimiters, no startup 'loading...' noise leaks in."""
    with _worker() as w:
        t = w.transcribe("/tmp/x.png", max_tokens=10)
        assert "<<<" not in t and "loading" not in t
        assert t.strip() == "TRANSCRIPT for /tmp/x.png mt=10"


def test_worker_raises_on_server_error():
    """An ERROR response must raise (No Silent Degradation — never return an empty/partial transcript as ok)."""
    with _worker() as w:
        with pytest.raises(RuntimeError, match="simulated failure"):
            w.transcribe("/tmp/BOOM.png", max_tokens=10)


def test_worker_times_out_then_auto_restarts():
    """A hung request times out; the worker recovers by respawning for the next call (a fresh pid)."""
    with _worker(call_timeout=1) as w:
        _ = w.transcribe("/tmp/warm.png")     # boot + first real response
        pid_before = w.pid
        with pytest.raises(TimeoutError):
            w.transcribe("/tmp/HANG.png")
        # after a timeout the dead/hung process is discarded; the next call transparently restarts
        t = w.transcribe("/tmp/after.png", max_tokens=7)
        assert "TRANSCRIPT for /tmp/after.png" in t
        assert w.pid is not None and w.pid != pid_before


def test_worker_restarts_if_process_died():
    with _worker() as w:
        _ = w.transcribe("/tmp/a.png")
        pid1 = w.pid
        os.kill(pid1, 9)                        # simulate a crash
        t = w.transcribe("/tmp/b.png")          # must respawn transparently
        assert "TRANSCRIPT for /tmp/b.png" in t
        assert w.pid != pid1


def test_worker_close_terminates_process():
    w = _worker()
    _ = w.transcribe("/tmp/a.png")
    pid = w.pid
    w.close()
    assert not mlx_client._pid_alive(pid), "close() must terminate the server process"
    assert w.pid is None


# --------------------------------------------------------------------------- #
# real MLX smoke (slow): the actual server loads once and serves two crops
# --------------------------------------------------------------------------- #
@pytest.mark.slow
def test_mlx_server_smoke(tmp_path):
    """Real olmOCR: one load, two tiny transcriptions on the SAME pid. Proves the productionized path works."""
    from PIL import Image
    imgs = []
    for name in ("one", "two"):
        p = tmp_path / f"{name}.png"
        Image.new("L", (320, 80), 255).save(p)      # blank strip — content irrelevant, we test the plumbing
        imgs.append(str(p))
    venv_py = str(Path(mlx_client.__file__).resolve().parent.parent / "ocr-mlx-venv" / "bin" / "python")
    server = str(Path(mlx_client.__file__).resolve().parent / "mlx_ocr_server.py")
    with mlx_client.MLXWorker(venv_py=venv_py, server_script=server,
                              ready_timeout=300, call_timeout=300) as w:
        _ = w.transcribe(imgs[0], max_tokens=32)
        pid1 = w.pid
        _ = w.transcribe(imgs[1], max_tokens=32)
        assert w.pid == pid1, "real server must serve both crops from one loaded model"

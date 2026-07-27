#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""mlx_client.py — load-once MLX worker client (§8 R3-1 productionization; runs in ocr-venv).

The one-shot `mlx_ocr.py` subprocess reloads the 15GB olmOCR model on EVERY crop (~30-60s). Over a batch of
flagged verses that dominates wall-clock. MLXWorker instead keeps ONE long-lived `mlx_ocr_server.py` process
(model loaded once) and streams per-crop requests over stdin/stdout JSONL, reading the delimited transcription
back. It is resilient by construction:

  * a background reader thread + queue gives readline-WITH-TIMEOUT on the blocking pipe, so a hung model call
    cannot wedge the batch — it times out, the process is discarded, and the next call transparently respawns;
  * a process that dies (crash / OOM / external kill) is detected (broken pipe on write, or EOF sentinel on
    read) and respawned ONCE per call — transparent recovery;
  * a per-request server ERROR is RAISED, never returned as an empty/partial transcript (No Silent Degradation);
    the server process stays up for the next request (an error is a bad crop, not a dead model).

Protocol (see mlx_ocr_server.py): server prints framework noise then `<<<MLX_READY>>>`; each request is one JSON
line `{"image","max_tokens","prompt"?,"system"?}` (or `{"cmd":"quit"}`); each response is
`<<<MLX_OCR_BEGIN>>>\\n<text>\\n<<<MLX_OCR_END>>>` or `<<<MLX_OCR_ERROR>>>\\n<msg>\\n<<<MLX_OCR_END>>>`.
"""
from __future__ import annotations

import json
import os
import queue
import subprocess
import threading
import time

BEGIN, END, ERR, READY = "<<<MLX_OCR_BEGIN>>>", "<<<MLX_OCR_END>>>", "<<<MLX_OCR_ERROR>>>", "<<<MLX_READY>>>"
_EOF = object()


def _pid_alive(pid: int | None) -> bool:
    if pid is None:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


class MLXWorker:
    """A reusable, self-healing handle to a load-once MLX OCR server process."""

    def __init__(self, venv_py: str, server_script: str, *, model: str | None = None,
                 ready_timeout: float = 300.0, call_timeout: float = 900.0, stderr_log: str | None = None):
        self.venv_py = str(venv_py)
        self.server_script = str(server_script)
        self.model = model
        self.ready_timeout = ready_timeout
        self.call_timeout = call_timeout
        self.stderr_log = stderr_log
        self._proc: subprocess.Popen | None = None
        self._q: queue.Queue | None = None
        # One model, one request at a time: serialize the write+read transaction (and spawn/close) so concurrent
        # callers on the shared get_worker() singleton can't cross-wire a response to the wrong crop or leak a
        # duplicate 15GB process (code-review MEDIUM-4). RLock, not Lock: transcribe() re-enters it on retry.
        self._lock = threading.RLock()

    # -- lifecycle ---------------------------------------------------------- #
    @property
    def pid(self) -> int | None:
        return self._proc.pid if (self._proc is not None and self._proc.poll() is None) else None

    @staticmethod
    def _pump(stream, q: queue.Queue):
        try:
            for line in stream:
                q.put(line)
        finally:
            q.put(_EOF)

    def _spawn(self):
        cmd = [self.venv_py, self.server_script] + (["--model", self.model] if self.model else [])
        stderr = open(self.stderr_log, "ab") if self.stderr_log else subprocess.DEVNULL
        self._proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                      stderr=stderr, text=True, bufsize=1)
        self._q = queue.Queue()
        threading.Thread(target=self._pump, args=(self._proc.stdout, self._q), daemon=True).start()
        deadline = time.time() + self.ready_timeout
        while True:
            line = self._get(deadline - time.time())
            if line is _EOF:
                self._kill(); raise RuntimeError("mlx server exited before READY (see stderr_log)")
            if line is None:
                self._kill(); raise TimeoutError(f"mlx server not READY within {self.ready_timeout}s")
            if line.strip() == READY:
                return                                    # model loaded; ready to serve

    def _get(self, timeout: float):
        """Next stdout line, or None on timeout, or _EOF if the stream closed."""
        try:
            return self._q.get(timeout=max(0.001, timeout))
        except queue.Empty:
            return None

    def _ensure(self):
        if self.pid is None:
            self._kill()                                  # drop any dead handle, then (re)spawn
            self._spawn()

    def _kill(self):
        p = self._proc
        if p is not None:
            try:
                if p.poll() is None:
                    p.kill(); p.wait(timeout=5)
            except Exception:
                pass
            for s in (p.stdin, p.stdout):
                try:
                    s and s.close()
                except Exception:
                    pass
        self._proc, self._q = None, None

    # -- the call ----------------------------------------------------------- #
    def transcribe(self, image_path: str, *, max_tokens: int = 4000, prompt: str | None = None,
                   system: str | None = None, _retry: bool = True) -> str:
        """Transcribe one image via the persistent model. Raises TimeoutError (call_timeout) or RuntimeError
        (server error / repeated process death). Respawns once transparently if the process had died. The whole
        write+read transaction holds `self._lock` (reentrant) so concurrent callers serialize onto the one model
        rather than cross-wiring responses (code-review MEDIUM-4)."""
        with self._lock:
            self._ensure()
            req = {"image": str(image_path), "max_tokens": int(max_tokens)}
            if prompt is not None:
                req["prompt"] = prompt
            if system is not None:
                req["system"] = system
            try:
                self._proc.stdin.write(json.dumps(req) + "\n")
                self._proc.stdin.flush()
            except (BrokenPipeError, OSError):
                self._kill()
                if _retry:
                    return self.transcribe(image_path, max_tokens=max_tokens, prompt=prompt, system=system, _retry=False)
                raise RuntimeError("mlx server pipe broken (after respawn)")

            deadline = time.time() + self.call_timeout
            state, payload = "seek", []
            while True:
                line = self._get(deadline - time.time())
                if line is _EOF:                              # process died mid-request -> respawn once
                    self._kill()
                    if _retry:
                        return self.transcribe(image_path, max_tokens=max_tokens, prompt=prompt,
                                               system=system, _retry=False)
                    raise RuntimeError("mlx server exited mid-request (after respawn)")
                if line is None:                              # timeout -> discard the hung process (No hang-wedge)
                    self._kill()
                    raise TimeoutError(f"mlx transcribe exceeded {self.call_timeout}s")
                s = line.rstrip("\n")
                if state == "seek":
                    if s == BEGIN:
                        state = "body"
                    elif s == ERR:
                        state = "error"
                    continue                                  # skip framework noise before the frame
                if s == END:
                    text = "\n".join(payload).strip()
                    if state == "error":
                        raise RuntimeError("mlx server error: " + text)   # process stays up; the crop failed, not the model
                    return text
                payload.append(s)

    # -- context management ------------------------------------------------- #
    def close(self):
        with self._lock:
            if self._proc is not None:
                try:
                    self._proc.stdin.write(json.dumps({"cmd": "quit"}) + "\n")
                    self._proc.stdin.flush()
                    self._proc.wait(timeout=3)
                except Exception:
                    pass
            self._kill()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def __del__(self):
        try:
            self._kill()
        except Exception:
            pass


# --------------------------------------------------------------------------- #
# module-level singleton so reocr_r3 reuses ONE worker across a whole batch
# --------------------------------------------------------------------------- #
_WORKER: MLXWorker | None = None


def get_worker(venv_py: str, server_script: str, *, model: str | None = None, **kw) -> MLXWorker:
    """Process-wide singleton worker (created on first use). reocr_r3 calls this so every flagged crop in a
    batch reuses the one loaded model."""
    global _WORKER
    if _WORKER is None:
        _WORKER = MLXWorker(venv_py, server_script, model=model, **kw)
    return _WORKER


def shutdown_worker():
    global _WORKER
    if _WORKER is not None:
        _WORKER.close()
        _WORKER = None

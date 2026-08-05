#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""mlx_ocr_server.py — load-once MLX OCR server (§8 R3-1 productionization; runs in ocr-mlx-venv).

Loads olmOCR-2 ONCE and then serves per-crop transcription requests over a stdin/stdout JSONL protocol, so a
batch of gate-flagged verses shares a single 15GB model load instead of reloading it per crop. Driven by
`mlx_client.MLXWorker` (which runs in ocr-venv, where kraken lives but mlx-vlm cannot).

Protocol:
  stdout : framework load noise (redirected to stderr), then `<<<MLX_READY>>>`; thereafter, per request,
           `<<<MLX_OCR_BEGIN>>>\\n<text>\\n<<<MLX_OCR_END>>>` on success or
           `<<<MLX_OCR_ERROR>>>\\n<msg>\\n<<<MLX_OCR_END>>>` on failure (incl. an EMPTY transcription — No
           Silent Degradation: a blank is an error the caller must see, never an accepted empty transcript).
  stdin  : one JSON object per line — {"image": path, "max_tokens": N, "prompt"?: str, "system"?: str}
           or {"cmd": "quit"}. EOF also exits.

All model/library stdout is redirected to stderr while loading and generating, so the ONLY thing on real
stdout is the protocol frames (the client tolerates stray noise, but this keeps the transcript payload clean).
"""
from __future__ import annotations

import argparse
import contextlib
import json
import sys
import warnings

warnings.filterwarnings("ignore")

import mlx_ocr  # noqa: E402  (same-dir import; server runs from ocr-spike)

BEGIN, END, ERR, READY = "<<<MLX_OCR_BEGIN>>>", "<<<MLX_OCR_END>>>", "<<<MLX_OCR_ERROR>>>", "<<<MLX_READY>>>"
_REAL_STDOUT = sys.stdout          # protocol frames go here; everything else is redirected to stderr


def _emit_frame(marker: str, text: str = ""):
    _REAL_STDOUT.write(f"{marker}\n{text}\n{END}\n")
    _REAL_STDOUT.flush()


def _emit_ready():
    _REAL_STDOUT.write(READY + "\n")
    _REAL_STDOUT.flush()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=mlx_ocr.MODEL)
    a = ap.parse_args()

    with contextlib.redirect_stdout(sys.stderr):        # keep shard-load progress off the protocol channel
        m, processor, cfg = mlx_ocr.load_model(a.model)
    _emit_ready()

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError as e:
            _emit_frame(ERR, f"bad json: {e}")
            continue
        if req.get("cmd") == "quit":
            return 0
        try:
            with contextlib.redirect_stdout(sys.stderr):    # any generate() chatter -> stderr, not the frame
                text = mlx_ocr.run(m, processor, cfg, req["image"],
                                   max_tokens=int(req.get("max_tokens", 4000)),
                                   prompt=req.get("prompt", mlx_ocr.PROMPT),
                                   system=req.get("system", mlx_ocr.SYSTEM))
            if not (text or "").strip():
                _emit_frame(ERR, "empty transcription")     # No Silent Degradation
            else:
                _emit_frame(BEGIN, text)
        except Exception as e:                              # a bad crop must not kill the loaded model
            _emit_frame(ERR, f"{type(e).__name__}: {e}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

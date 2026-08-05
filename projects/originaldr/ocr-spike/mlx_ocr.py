#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""mlx_ocr.py — standalone MLX vision-OCR pass for the §8 R3-1 local bulk backend (2026-07-23).

Runs in the ISOLATED `ocr-mlx-venv` (mlx-vlm 0.3.12 + transformers 5.1.0 — 5.2.0 has a video-processor bug).
kraken/coremltools live in `ocr-venv`, which can't hold mlx-vlm, so `reocr_r3._r3_mlx` subprocess-calls this
script and reads the transcription between the delimiters below. Model = olmOCR-2-7B (a non-reasoning OCR
specialist — the fix for qwen3-vl:8b, which was thinking-locked and returned empty; see reference memory).

ſ surface-safety is prompt-only (model-agnostic diplomatic instruction) + the caller's ſ-count companion check
(No Silent Degradation: a recognizer that erases ſ must be REJECTED regardless of edit_ratio, per the AI_OCR
DUAL-TRACK rule). temperature 0 for a deterministic pass.

Run: ocr-mlx-venv/bin/python ocr-spike/mlx_ocr.py --image <png> [--max-tokens 4000] [--model <repo>]
"""
from __future__ import annotations

import argparse
import sys
import time
import warnings

warnings.filterwarnings("ignore")

MODEL = "mlx-community/olmOCR-2-7B-1025-bf16"
SYSTEM = ("You are a diplomatic transcriber of early-modern printed books. Transcribe exactly as printed; "
          "never modernize.")
PROMPT = ("Transcribe the main body text of this early-modern Douay-Rheims Bible page EXACTLY as printed — a "
          "diplomatic, NOT modernized transcription. Preserve the long-s ſ wherever the letterform is printed "
          "as long-s (never convert ſ to s). Preserve original early-modern spelling (vnto, beſeech, ſonne), "
          "and u/v and i/j exactly as printed. Do not add commentary. Output ONLY the transcription text.")

BEGIN, END = "<<<MLX_OCR_BEGIN>>>", "<<<MLX_OCR_END>>>"


def load_model(model: str = MODEL):
    """Load the MLX vision-OCR model ONCE. Returns (model, processor, cfg) for reuse across many pages — the
    load-once server (mlx_ocr_server.py) calls this a single time so a batch of crops shares one 15GB load."""
    from mlx_vlm import load
    m, processor = load(model)
    return m, processor, getattr(m, "config", None)


def run(m, processor, cfg, image_path: str, *, max_tokens: int = 4000, system: str = SYSTEM,
        prompt: str = PROMPT, temperature: float = 0.0, repetition_penalty: float = 1.15) -> str:
    """One diplomatic vision-OCR pass on an ALREADY-LOADED model. Returns the raw transcription (NFC is the
    caller's job).

    repetition_penalty (>1) breaks the greedy-decoding degeneration loop VLMs fall into on a dense full page
    (olmOCR at temp 0 transcribed ~12 verses perfectly then repeated one sentence to the token limit). 1.15 +
    a modest context window penalizes recently-emitted tokens without harming legitimate archaic repetition."""
    from mlx_vlm import generate
    from mlx_vlm.prompt_utils import apply_chat_template
    messages = [{"role": "system", "content": system}, {"role": "user", "content": prompt}]
    formatted = apply_chat_template(processor, cfg, messages, num_images=1)
    res = generate(m, processor, formatted, image=[image_path], max_tokens=max_tokens,
                   temperature=temperature, repetition_penalty=repetition_penalty,
                   repetition_context_size=60, verbose=False)
    return getattr(res, "text", None) or str(res)


def transcribe(image_path: str, *, model: str = MODEL, max_tokens: int = 4000,
               system: str = SYSTEM, prompt: str = PROMPT,
               temperature: float = 0.0, repetition_penalty: float = 1.15) -> str:
    """One-shot load+run (back-compat for the CLI and reocr_r3's reload-per-call fallback). For batch work use
    the load-once mlx_ocr_server.py + mlx_client.MLXWorker instead."""
    m, processor, cfg = load_model(model)
    return run(m, processor, cfg, image_path, max_tokens=max_tokens, system=system, prompt=prompt,
               temperature=temperature, repetition_penalty=repetition_penalty)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", required=True)
    ap.add_argument("--model", default=MODEL)
    ap.add_argument("--max-tokens", type=int, default=4000)
    ap.add_argument("--prompt", default=PROMPT)
    ap.add_argument("--system", default=SYSTEM)
    ap.add_argument("--stats", action="store_true", help="print ſ-count + timing to stderr")
    a = ap.parse_args()
    t0 = time.time()
    txt = transcribe(a.image, model=a.model, max_tokens=a.max_tokens, prompt=a.prompt, system=a.system)
    # delimited so a cross-venv caller can extract cleanly even if the framework prints load/progress noise
    sys.stdout.write(f"{BEGIN}\n{txt}\n{END}\n")
    if a.stats:
        sys.stderr.write(f"[mlx_ocr] {len(txt)} chars, {txt.count(chr(0x17f))} ſ, {time.time()-t0:.0f}s\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

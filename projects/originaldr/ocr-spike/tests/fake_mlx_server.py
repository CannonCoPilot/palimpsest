#!/usr/bin/env python3
"""A pure-Python stand-in for mlx_ocr_server.py — same stdin/stdout protocol, NO model, instant.

Lets the MLXWorker client be TDD'd end-to-end (framing, READY handshake, request/response correlation, the
error path, and the timeout/restart path) without loading the 15GB olmOCR model. Behaviours keyed off the
image path so a test can drive each branch:
  * normal path            -> echoes  "TRANSCRIPT for <image> mt=<max_tokens>"  between the OCR delimiters
  * path containing 'BOOM' -> emits an ERROR response (client must raise, not hang)
  * path containing 'HANG' -> sleeps past any sane test timeout (client must time out + be able to restart)
Startup emits a noise line THEN the READY marker (the client must skip pre-READY noise).
"""
import argparse
import json
import sys
import time

BEGIN, END, ERR, READY = "<<<MLX_OCR_BEGIN>>>", "<<<MLX_OCR_END>>>", "<<<MLX_OCR_ERROR>>>", "<<<MLX_READY>>>"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="fake")
    ap.parse_args()
    # simulate framework load noise on stdout, then the ready handshake
    sys.stdout.write("loading fake model shards... done\n")
    sys.stdout.write(READY + "\n")
    sys.stdout.flush()
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            sys.stdout.write(f"{ERR}\nbad json\n{END}\n"); sys.stdout.flush(); continue
        if req.get("cmd") == "quit":
            return 0
        img = req.get("image", "")
        if "HANG" in img:
            time.sleep(30)
        if "BOOM" in img:
            sys.stdout.write(f"{ERR}\nsimulated failure for {img}\n{END}\n"); sys.stdout.flush(); continue
        text = f"TRANSCRIPT for {img} mt={req.get('max_tokens')}"
        sys.stdout.write(f"{BEGIN}\n{text}\n{END}\n")
        sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

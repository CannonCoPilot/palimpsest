#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""reocr_r3.py — Rung 3: automated vision-LLM transcription (the gated escalation executor).

GOLD-FREE. The confidence gate (reocr_core + xsrc_gate §7 alarm-2) decides WHICH pages/verses escalate; this
module transcribes them. §8 R3-1: the DEFAULT backend is now LOCAL (Ollama `qwen3-vl:8b`) — no paid API — with
the in-agent Claude arbiter (backend="claude") reserved for the peak residual (R3-3). ſ surface-safety lives
entirely in the PROMPT (model-agnostic) — transcribe exactly as printed, never modernize ſ→s — plus an NFC
normalize + the ſ-count companion check on the way out.

This is the lever that lets the ~3,028-page corpus be transcribed WITHOUT page-by-page human transcription:
R2 handles the confident majority cheaply; R3 rescues only the residual the gate flags. Per §8 R3-5 / No Silent
Degradation, a local backend is only trusted where MEASURED to reach per-verse identity ≥ R2 — otherwise it is
a finding (escalate to a stronger local model or the Claude arbiter), never a silent accept.

Run: ocr-venv/bin/python ocr-spike/reocr_r3.py <ocr_dir> <page_index> [ollama|claude]
"""
from __future__ import annotations
import sys, io, re, base64, json, unicodedata, urllib.request, warnings
from pathlib import Path
warnings.filterwarnings("ignore")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import jp2_page

MODEL = "claude-opus-4-8"                         # in-agent Claude arbiter (R3-3), ſ-faithful, peak residual
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_VISION_MODEL = "qwen3-vl:8b"              # DEPRECATED backend: thinking-locked, returns empty (see memory)
# §8 R3-1 LOCAL BULK backend = olmOCR-2 via MLX (isolated venv; kraken/coremltools can't co-exist with mlx-vlm).
# MEASURED 2026-07-23: olmOCR-crop CONTENT beats R2 on the flagged verses (archaic_id, ſ-blind: genesis-24
# vv27-30 R2 0.69-0.88 → olmOCR 0.89-1.0). It runs on CROPS without the full-page repetition loop, but
# MODERNIZES ſ→s on crops (its OCR fine-tuning ignores diplomatic prompts) — so it is a CONTENT rung; the
# ſ-faithful surface comes from the Claude arbiter (backend='claude') or R2/reichenau, never a faked ſ.
MLX_VENV_PY = str(HERE.parent / "ocr-mlx-venv" / "bin" / "python")
MLX_OCR_SCRIPT = str(HERE / "mlx_ocr.py")
MLX_OCR_SERVER = str(HERE / "mlx_ocr_server.py")        # load-once server (batch-fast; §8 R3-1 productionization)
MLX_SERVER_LOG = str(HERE / ".mlx-server.log")          # server stderr (load/generate noise) for debugging
MLX_VISION_MODEL = "mlx-community/olmOCR-2-7B-1025-bf16"
R3_MAXW = 2500  # long-edge px for the vision call (Opus 4.8 high-res ceiling is 2576; dense print wants detail)
CREDS = Path("/Users/nathanielcannon/Claude/Project_Aion/.claude/secrets/credentials.yaml")

PROMPT = """You are a diplomatic transcriber of early-modern printed books (the 1582/1609/1610 Douay-Rheims Bible).
Transcribe the MAIN BODY TEXT of this page EXACTLY as printed — a diplomatic (not modernized) transcription.

RULES (critical):
- Preserve the long-s ſ wherever the letterform is printed as long-s. NEVER convert ſ to s. This is the single
  most important rule; the whole point of this transcription is surface fidelity to the printed glyphs.
- Preserve original early-modern spelling exactly (e.g. vnto, childeren, beſeech, ſonne). Do NOT correct or modernize.
- Preserve u/v and i/j exactly as printed (e.g. "vpon", "iudge"). Preserve æ/œ ligatures, and the verse/section
  marks † and ‡ as printed.
- Preserve line breaks as spaces; keep the reading order of the main text column(s).
- Transcribe the running scripture/body text. Include the printed verse numbers inline where they appear.
- Do NOT add commentary, notes, or explanation. Output ONLY the transcription text, nothing else.
- If a glyph is genuinely illegible, use a single ? in its place rather than guessing a modern word.
"""


def _api_key():
    import yaml
    for doc in yaml.safe_load_all(CREDS.read_text()):
        d = doc or {}
        if isinstance(d, dict) and isinstance(d.get("llm"), dict) and d["llm"].get("anthropic"):
            return d["llm"]["anthropic"].strip()
    raise RuntimeError("no /llm/anthropic key in credentials.yaml")


def _page_png_b64(ocr_dir, page_index, maxw=R3_MAXW):
    from PIL import Image
    im = jp2_page.load(ocr_dir, page_index).convert("L")
    if im.width > maxw:
        im = im.resize((maxw, int(im.height * maxw / im.width)), Image.LANCZOS)
    buf = io.BytesIO(); im.save(buf, format="PNG")
    return base64.standard_b64encode(buf.getvalue()).decode("ascii")


def _render_page_png(ocr_dir, page_index, out_path, *, maxw=2000, crop=None):
    """Render a page (or a fractional crop box (x0,y0,x1,y1) in 0..1) to a PNG FILE for the MLX backend
    (mlx_vlm reads image paths, not b64). Returns out_path."""
    from PIL import Image
    im = jp2_page.load(ocr_dir, page_index).convert("L")
    if crop:
        W, H = im.size
        x0, y0, x1, y1 = crop
        im = im.crop((int(x0 * W), int(y0 * H), int(x1 * W), int(y1 * H)))
    if im.width > maxw:
        im = im.resize((maxw, int(im.height * maxw / im.width)), Image.LANCZOS)
    im.save(out_path)
    return out_path


def _mlx_worker():
    """The process-wide load-once MLX worker (olmOCR loaded ONCE, reused for every crop in a batch)."""
    import mlx_client
    return mlx_client.get_worker(MLX_VENV_PY, MLX_OCR_SERVER, model=MLX_VISION_MODEL,
                                 ready_timeout=600, call_timeout=900, stderr_log=MLX_SERVER_LOG)


def shutdown_mlx():
    """Release the load-once olmOCR process (call at the end of a batch)."""
    try:
        import mlx_client
        mlx_client.shutdown_worker()
    except Exception:
        pass


def _r3_mlx(png_path, max_tokens, *, reload_per_call=False):
    """§8 R3-1 LOCAL backend: olmOCR-2 via the isolated ocr-mlx-venv (kraken/coremltools can't co-exist with
    mlx-vlm, so this crosses venvs). DEFAULT path = the load-once worker (mlx_ocr_server, model loaded once and
    reused across crops — the productionized batch path). reload_per_call=True = a one-shot subprocess that
    reloads the 15GB model (isolated; for manual/debug runs). RAISES on empty output (No Silent Degradation —
    the caller records r3_error and keeps the page flagged; an empty 'accept' would silently destroy the verse)."""
    if not reload_per_call:
        text = _mlx_worker().transcribe(png_path, max_tokens=max_tokens)
        if not (text or "").strip():
            raise RuntimeError("mlx worker returned empty transcription")
        return text
    import subprocess
    cmd = [MLX_VENV_PY, MLX_OCR_SCRIPT, "--image", png_path, "--max-tokens", str(max_tokens)]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
    m = re.search(r"<<<MLX_OCR_BEGIN>>>\n(.*)\n<<<MLX_OCR_END>>>", r.stdout, re.S)
    if not m:
        raise RuntimeError(f"mlx_ocr produced no delimited output (rc={r.returncode}): {r.stderr[-300:]}")
    text = m.group(1).strip()
    if not text:
        raise RuntimeError("mlx_ocr returned empty transcription")
    return text


def _band_boxes(n: int, overlap: float = 0.06):
    """n horizontal band crop-boxes (fractional), with a small vertical overlap so a line straddling a band
    boundary is fully captured in at least one band. olmOCR loops on a full dense page (~18 verses) but is
    clean on a ~6-verse band, so banding is the loop-free way to cover a whole page."""
    boxes = []
    for i in range(n):
        y0 = max(0.0, i / n - (overlap if i else 0.0))
        y1 = min(1.0, (i + 1) / n + (overlap if i < n - 1 else 0.0))
        boxes.append((0.0, y0, 1.0, y1))
    return boxes


def _stitch_bands(parts):
    """Concatenate band transcriptions, removing the word-level overlap between consecutive bands (bands
    overlap vertically, so a boundary line appears in both). Matches the largest run (≤30 words) of `out`'s
    tail against the next band's head and drops the duplicate."""
    parts = [p.strip() for p in parts if p and p.strip()]
    if not parts:
        return ""
    out = parts[0].split()
    for p in parts[1:]:
        w = p.split()
        best = 0
        for k in range(min(30, len(out), len(w)), 0, -1):
            if [t.lower() for t in out[-k:]] == [t.lower() for t in w[:k]]:
                best = k
                break
        out += w[best:]
    return " ".join(out)


def _r3_ollama(b64: str, max_tokens: int) -> str:
    """§8 R3-1 LOCAL backend via direct Ollama /api/generate (no paid API), temperature 0 for a deterministic
    diplomatic pass.

    MEASURED 2026-07-23 — qwen3-vl:8b is THINKING-LOCKED in this Ollama build: `think:false` (root),
    `/no_think` (prompt), and `/api/chat think:false` are ALL ignored — the whole `num_predict` budget goes to
    the `thinking` field and `response` comes back empty (done_reason='length'). We therefore (a) request a big
    budget so reasoning can complete and the answer can still emit, and (b) if `response` is STILL empty while
    `thinking` is non-empty, RAISE — never return an empty transcription (No Silent Degradation: the caller
    records r3_error and keeps the page flagged; an empty 'accept' would silently destroy the page)."""
    payload = {
        "model": OLLAMA_VISION_MODEL, "prompt": PROMPT, "images": [b64],
        "stream": False, "think": False,
        "options": {"temperature": 0, "num_predict": max_tokens},
    }
    req = urllib.request.Request(OLLAMA_URL, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=900) as resp:
        d = json.loads(resp.read())
    text = (d.get("response") or "").strip()
    if not text:
        thinking = (d.get("thinking") or "").strip()
        raise RuntimeError(
            f"{OLLAMA_VISION_MODEL} returned empty response (done_reason={d.get('done_reason')}, "
            f"thinking={len(thinking)}c) — thinking-locked model consumed the budget. Use a non-reasoning "
            f"OCR model (MLX olmOCR-2-7B / CHURRO-3B, §8 R3-1) or the Claude arbiter (backend='claude').")
    return text


def _r3_claude(b64: str, max_tokens: int) -> str:
    """R3-3 arbiter path via the Anthropic SDK. DORMANT + GUARDED: the reOCR pipeline (run_r3 → r3_route) NEVER
    calls this — it uses only the local olmOCR backend. Per the standing no-Anthropic-API policy (Pro Max
    subscription; never call the API / touch API keys), the peak ſ-faithful arbiter (§8 R3-3) is the IN-AGENT
    Jarvis reading the crop directly in-session, NOT an SDK call. This function raises unless a human explicitly
    sets OCR_ALLOW_ANTHROPIC_API=1, so it can never fire accidentally from a batch."""
    import os
    if os.environ.get("OCR_ALLOW_ANTHROPIC_API") != "1":
        raise RuntimeError(
            "backend='claude' calls the Anthropic API — BLOCKED by the no-Anthropic-API policy. The ſ-faithful "
            "arbiter (§8 R3-3) is the in-agent Jarvis reading the crop in-session, not an SDK call. To override "
            "for a one-off human-run experiment, set OCR_ALLOW_ANTHROPIC_API=1.")
    import anthropic
    client = anthropic.Anthropic(api_key=_api_key())
    with client.messages.stream(
        model=MODEL, max_tokens=max_tokens,
        messages=[{"role": "user", "content": [
            {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": b64}},
            {"type": "text", "text": PROMPT},
        ]}],
    ) as stream:
        msg = stream.get_final_message()
    return "".join(b.text for b in msg.content if b.type == "text").strip()


def r3_transcribe(ocr_dir: str, page_index: int, *, backend: str = "mlx",
                  maxw=R3_MAXW, max_tokens=4000, crop=None, bands=4, restore_s=False,
                  reload_per_call=False) -> str:
    """Transcribe one page via a vision model. DEFAULT = 'mlx' (olmOCR-2 local, §8 R3-1); 'claude' = the
    ſ-faithful arbiter (R3-3); 'ollama' = DEPRECATED (qwen3-vl thinking-locked → empty). Returns NFC text.

    MLX specifics: olmOCR loops on a full dense page, so with crop=None the page is transcribed in `bands`
    horizontal strips and stitched (loop-free full-page coverage). Pass crop=(x0,y0,x1,y1 fractions in 0..1)
    to transcribe ONE region — the fast targeted mode for a flagged verse span (validated to beat R2 on
    content: genesis-24 vv27-30 R2 0.69-0.88 → olmOCR 0.89-1.0, archaic_id). olmOCR MODERNIZES ſ; restore_s=True
    applies the ~90% positional long_s_rule surface completion (LABELED, not observed); a ſ-faithful surface
    needs backend='claude'."""
    if backend == "mlx":
        import tempfile
        import os as _os
        r3_tmp = HERE / ".r3-tmp"          # project-local scratch (Filesystem Policy: never write /var|/tmp; LOW-6)
        r3_tmp.mkdir(exist_ok=True)
        boxes = [crop] if crop is not None else _band_boxes(bands)
        parts = []
        for box in boxes:
            fd, png = tempfile.mkstemp(suffix=".png", dir=str(r3_tmp)); _os.close(fd)
            try:
                _render_page_png(ocr_dir, page_index, png, maxw=min(maxw, 2000), crop=box)
                parts.append(_r3_mlx(png, max_tokens, reload_per_call=reload_per_call))
            finally:
                try:
                    _os.unlink(png)
                except OSError:
                    pass
        text = _stitch_bands(parts) if len(parts) > 1 else (parts[0] if parts else "")
        text = unicodedata.normalize("NFC", text)
        if restore_s:
            import long_s_rule
            text = long_s_rule.restore_long_s(text)   # LABELED ~90% surface completion, never silent-observed
        return text
    b64 = _page_png_b64(ocr_dir, page_index, maxw)
    if backend == "claude":
        text = _r3_claude(b64, max_tokens)
    elif backend == "ollama":
        text = _r3_ollama(b64, max_tokens)
    else:
        raise ValueError(f"unknown R3 backend: {backend!r} (expected 'mlx', 'claude', or 'ollama')")
    # NFC (NEVER NFKC — NFKC folds ſ→s); ſ-count companion check is the caller's/eval's job
    return unicodedata.normalize("NFC", text)


if __name__ == "__main__":
    od, pi = sys.argv[1], int(sys.argv[2])
    backend = sys.argv[3] if len(sys.argv) > 3 else "mlx"
    txt = r3_transcribe(od, pi, backend=backend)
    print(f"=== R3[{backend}] {od} p{pi}: {len(txt)} chars, {txt.count('ſ')} ſ ===")
    print(txt[:600])

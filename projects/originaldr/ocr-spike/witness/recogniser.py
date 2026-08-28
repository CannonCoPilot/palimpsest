#!/usr/bin/env python3
"""R13.1 -- THE ONE PLACE A READING IS PRODUCED, AND IT NAMES ITS MODEL.

R13's finding, verified 2026-08-17 and still true of the shipping path: `grep` over `gen1_*.py`,
`s_arbiter.py` and `chapter_campaign.py` returns NOTHING for any fine-tune. `gen1_r3.py:666` sets
`"old_text": sp.get("text", "")` -- the attesting arm is the STORED CORPUS OCR. The ſ-faithful
recogniser this project spent its Rung-2 effort producing is **an artefact no code loads**, which is
Gate 0f's defect (a rule no code read) one level down.

⚠️ WHY THIS IS A MODULE AND NOT AN EDIT IN THE ARM. The arm currently has NO recogniser to name, so
adding one there first would spread model-loading across every consumer and leave provenance as a
convention each of them could forget -- which is how the artefact became unloadable in the first
place. **One entry point, and it stamps.** A reading that cannot say which model produced it is not
a reading this project can cite (§10's provenance rule, applied to the recogniser).

⚠️ THE MODEL IS NOT CHOSEN HERE, AND IT IS NOT NAMED HERE EITHER. It is read from
`witness/recog-selection.json`, which R2.1b WROTE from a measurement -- `dr_v3_armB`, on 7 region
class wins of 7 over a set held out from all five candidates. Hard-coding a model id in this file
would re-create exactly the defect R2.1b exists to prevent: *wiring an unselected model in replaces
"no model" with "an arbitrary model", which is the harder defect to see.* If the selection file is
absent, this module REFUSES to read rather than falling back to a default.

    from witness.recogniser import read, provenance
    r = read(png_path)        # -> {"text": ..., "model": ..., "model_sha": ..., "selected_by": ...}

Run directly for a self-report:

    ../ocr-venv/bin/python witness/recogniser.py

⚠️ INJECTION IS THE PROOF, and `witness/test_recogniser_provenance.py` performs it: swap the model
and the stamp must change. A provenance field that does not move when the model moves is decoration.
"""
from __future__ import annotations

import hashlib
import json
import sys
import warnings
from functools import lru_cache
from pathlib import Path

warnings.filterwarnings("ignore")

_HERE = Path(__file__).resolve().parent
SPIKE = _HERE.parent
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(SPIKE))

SELECTION = _HERE / "recog-selection.json"


class NoSelectedModel(RuntimeError):
    """Raised when R2.1b has not selected a model. ⚠️ NEVER caught into a default."""


def selected() -> dict:
    """-> {'name', 'path', 'why'} for the model R2.1b SELECTED. Raises if there is none.

    ⚠️ NO FALLBACK, DELIBERATELY. A default here would be an unselected model wearing the selected
    model's authority, and every reading downstream would carry a provenance stamp that was true of
    the field and false of the evidence.
    """
    ov = _override()
    if ov is not None:
        return ov
    if not SELECTION.is_file():
        raise NoSelectedModel(
            "R2.1b has not run: witness/recog-selection.json is absent, so no model has been "
            "selected on evidence. Run witness/score_recognisers.py. This module will not pick "
            "one for you — an arbitrary model is harder to see than no model.")
    d = json.loads(SELECTION.read_text())
    if not d.get("selected"):
        raise NoSelectedModel(
            f"R2.1b ran and made NO SELECTION ({d.get('why')}). That is a permitted outcome and it "
            f"leaves R13.1 blocked; it is not a licence to choose.")
    return {"name": d["selected"], "path": str(SPIKE / d["rel"]), "why": d.get("why", "")}


_OVERRIDE: dict | None = None


def _override():
    return _OVERRIDE


def inject(name: str | None, path: str | None = None):
    """Swap the model, FOR THE INJECTION PROOF ONLY. Pass `None` to restore the selection.

    ⚠️ THIS EXISTS SO THE PROVENANCE CLAIM IS FALSIFIABLE. R13.1's acceptance is *"injection-proven
    -- swap the model, and the artefact says so"*, and a stamp that no test can move is decoration.
    It is not a configuration hook: nothing in the shipping path may call it.
    """
    global _OVERRIDE
    _OVERRIDE = None if name is None else {"name": name, "path": path, "why": "INJECTED"}
    read.cache_clear()
    _load.cache_clear()


@lru_cache(maxsize=4)
def _sha(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


@lru_cache(maxsize=4)
def _load(path: str):
    from kraken.lib import models
    return models.load_any(path)


def provenance() -> dict:
    """-> the stamp every reading carries. ⚠️ The SHA is here because a NAME can be reused.

    A path is a label a human chose and can point at a file that has since been retrained; the
    digest is the artefact. R13's whole finding was that a component can be pointed at and not
    loaded, so the stamp records what was actually opened.
    """
    s = selected()
    return {"model": s["name"], "model_path": str(Path(s["path"]).relative_to(SPIKE)),
            "model_sha": _sha(s["path"]), "selected_by": "R2.1b " + s["why"]}


@lru_cache(maxsize=4096)
def read(png: str) -> tuple:
    """Read ONE line crop. -> (text, provenance-json). Cached per (model, crop) by `inject`."""
    import rung2_eval_lines as EV
    s = selected()
    text = EV.read_line(_load(s["path"]), Path(png))
    return text, json.dumps(provenance(), sort_keys=True)


def read_stamped(png) -> dict:
    """The consumer-facing call: a reading that CANNOT be separated from its model id."""
    text, prov = read(str(png))
    return {"text": text, **json.loads(prov)}


def main() -> int:
    try:
        p = provenance()
    except NoSelectedModel as e:
        print(f"🔴 NO SELECTED MODEL — refusing to read.\n   {e}")
        return 1
    print("R13.1 — the recogniser the attesting arm may use, and its provenance stamp:\n")
    for k, v in p.items():
        print(f"    {k:14s} {v}")
    print("\n⚠️ WHAT IS WIRED AND WHAT IS NOT, STATED PLAINLY. This module makes the SELECTED model")
    print("   reachable and makes every reading carry its id and digest. The attesting arm in")
    print("   `gen1_r3.py` still sets `old_text` from the stored corpus OCR — converting that arm")
    print("   is the REMAINDER of R13.1 and it changes campaign artefacts, so it is a deliberate")
    print("   act, not a side effect of this file existing. ⚠️ And R13.2's ſ-surface measurement is")
    print("   a SEPARATE step: the 1,142 `CONTENT OK, ſ-SURFACE OPEN` cells may NOT be reported as")
    print("   recovered until it runs. Plausibly is not measurably.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

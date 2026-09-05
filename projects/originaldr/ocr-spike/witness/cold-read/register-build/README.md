# Class Register builder

## B rebuild (current) — `build_register_B.py`
One script, no patch step. Reads `../cold-read-B.json` + `../img-B/*.jpg`, cuts 1–2 exemplars per
class (hand picks in `PICK`, otherwise auto across volumes; 1.2 % pad, 720 px crop, 200 px locator
with the box drawn), embeds all 54 leaves at 800 px q55 for the lightbox, writes
`lector-class-register-B.html` (~12.8 MB, NOT tracked). Shared CSS in `register.css`.

    python3 build_register_B.py

Republish to the SAME artifact url `5e285c57-44a0-4f26-b6e9-639e4a70b2d1` (last: 2026-09-05,
label "B rebuild, 54 leaves"). Rulings export → `../class-rulings.json`.

Register content: 27 classes seen on B (A existing 11 · B text 11 incl. new `LR` · C non-text 5)
+ §E three reportable states `BL` blank leaf · `BP` blank lower page · `EC` empty cell (recorded as
`??` in the read) + §D sub-kinds incl. the `OR` frame/cartouche and `MS` stamp scope.
`FN` `XP` `AP` were in the P register and not met on B; listed, no exemplars.

## P-surrogate build (superseded, kept for the record)
`build_register.py` (35 P leaves; patched in place by `patch_register.py`, so it carries its
lightbox base64 inline — that is why it is 12 MB). Do not extend; use the B script.

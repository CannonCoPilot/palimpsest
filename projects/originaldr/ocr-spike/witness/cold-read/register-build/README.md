# Class Register builder (moved from session scratch 2026-09-04)

1. Regenerate exemplars: adapt the exemplar-crop step (see scratchpad history: for each class pick 1-2 regions from the cold-read JSONs, crop from img/ or img-B/ with 1.2% pad, base64 crop + 200px locator thumb with the box drawn) -> exemplars-b64.json
2. python3 build_register.py   (reads exemplars-b64.json; writes lector-class-register.html)
3. python3 patch_register.py   (adds full-leaf lightbox: embeds leaves at 900px q62 + regions JSON)
4. Republish to the SAME artifact url 5e285c57-44a0-4f26-b6e9-639e4a70b2d1

For the B rebuild: source = cold-read-B.json + img-B/; add classes LR, OR-frame, blank-leaf, empty-cell.

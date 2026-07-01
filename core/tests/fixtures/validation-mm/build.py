"""Regenerate the standing Matthew-Mark cross-translation validation collection.

Two Matthew+Mark subtexts form the collection used to validate ALL Palimpsest functionality:
  * DR-MM     — derived from the gold Douay-Rheims (inherits its polished masking).
  * Geneva-MM — derived from a freshly re-ingested COMPLETE 1599 Geneva (Tolle Lege 2013).

Run from the palimpsest repo root. Reads local sources (the gold DR in .scratch/demo and the
Geneva EPUB in imports/Scripture/Bibles — both gitignored, never committed) WITHOUT modifying
them; all outputs land in .scratch/validation-mm (gitignored). Expected metrics + provenance are
recorded in manifest.json; validate.py asserts them. See README.md for the full recipe.

Pipeline (run each step in order):
  dr               DR-MM subtext (Matthew+Mark from the gold Douay-Rheims)
  geneva-complete  re-ingest COMPLETE Geneva with the corrected content filter (restores Mt 27-28)
  geneva-layout    author the Geneva Mt+Mk layout (book containers + per-chapter heading+chapter)
  geneva-verses    build Geneva's verse-number mask layer
  geneva-mm        derive the Geneva-MM subtext
  embed            chunk + MLX-embed every collection member (optional; needs a live embed service
                   and the collection to already exist — enables cosine congruence + probe)

    core/.venv/bin/python core/tests/fixtures/validation-mm/build.py <step>

The subtext steps come first; then create the collection (see README.md). The `embed` step is
optional and runs last (it reads the collection's membership), unlocking the embedding-gated paths
(cosine congruence, cross-translation probe). Run validate.py to assert the expected metrics.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

from palimpsest.project import Project, ingest_file
from palimpsest.derive import derive_subtext
from palimpsest.server import _write_elements_track

DEMO = Path(".scratch/demo")
WS = Path(".scratch/validation-mm")
GENEVA_EPUB_GLOB = "1599 Geneva Bible*.epub"
DR_ID = "douay-rheims-bible-complete-original-unabriged-full-douay-rheims-version-2018-1a24ae78af9f25ce66b9f156d163841a-anna-s-archive"
# Matthew=book-0047, Mark=book-0048 (contiguous [4337761, 4578501]); "chapter" sections hold the
# verse text ("1:1. ..."); header/heading[=chapter argument]/footnotes are mask=true and excluded.
DR_MATTHEW_BOOK = "book-0047"
DR_MARK_BOOK = "book-0048"

# Standing collection id (created per README before the `embed` step reads its membership).
CID = "matthew-mark-validation"
# Embedding provider for the reproducible `embed` step. MLX (Qwen3-Embedding-4B, dim 2560) is the
# default; swap to the Ollama fallback (provider=ollama, endpoint=http://localhost:11434,
# model=qwen3-embedding:4b) if MLX is not running. word/100 chunking matches the layers the
# collection tier was validated against; both tracks are content-addressed, so re-running is
# idempotent (identical params -> identical labels, no duplicate layers).
CHUNK_MODE, CHUNK_SIZE = "word", "100"
EMBED_PROVIDER = "mlx"
EMBED_ENDPOINT = "http://localhost:8000"
EMBED_MODEL = "mlx-community/Qwen3-Embedding-4B-4bit-DWQ"


def build_dr_mm() -> str:
    WS.mkdir(parents=True, exist_ok=True)
    dr = Project.load(DEMO / DR_ID)
    child, child_cfg, summary = derive_subtext(
        dr,
        WS,
        extraction_types=["chapter"],
        include_container_ids=[DR_MATTHEW_BOOK, DR_MARK_BOOK],
        title="Douay-Rheims -- Matthew & Mark",
        author="Douay-Rheims (1582-1610)",
    )
    text_len = len(child.reference_text())
    n_elem = _write_elements_track(child.path, child.metadata.id, child_cfg, text_len)
    print("DR-MM child id:", child.metadata.id)
    print("summary:", summary)
    print("elements written:", n_elem)
    return child.metadata.id


def _geneva_profile():
    """Corrected Geneva filter: strip footnote/cross-ref apparatus, KEEP split_003.

    PROFILE_GENEVA skips *_split_003.html (footnotes) but those files also hold tail-chapter
    verse text (Matthew 27-28) -> truncated ingest. Instead we keep every spine file and strip
    the footnote/cross-ref paragraph classes (second_scripture/fn-sub/fn_line = footnote-only;
    midtx/midtx1/midtx2 = marginal cross-references like "a Luke 3:23"), keeping chapter-verse
    (verse text) + chapter (arguments). Plus PROFILE_GENEVA's inline note-anchor strips.
    """
    from palimpsest.ingest.content_filters import (
        ContentProfile, ElementSelector, PROFILE_GENEVA)
    note_classes = ["second_scripture", "fn-sub", "fn_line", "midtx", "midtx1", "midtx2"]
    return ContentProfile(
        name="bible-geneva-complete",
        strip_selectors=[
            *PROFILE_GENEVA.strip_selectors,
            *[ElementSelector(tag="p", classes=frozenset({c})) for c in note_classes],
        ],
        skip_file_patterns=[],  # keep split_003 (holds Matthew 27-28)
    )


def build_geneva_complete() -> str:
    """Stage A: ingest COMPLETE Geneva with the corrected filter (new sha, no gold map)."""
    WS.mkdir(parents=True, exist_ok=True)
    epub = next(Path("imports/Scripture/Bibles").glob(GENEVA_EPUB_GLOB))
    print("epub:", epub.name)
    project = ingest_file(epub, WS, overwrite=True, content_profile=_geneva_profile())
    ref = project.reference_text()
    print("ingested id:", project.metadata.id)
    print("reference chars:", len(ref), "words:", project.metadata.word_count)
    # completeness checks: Matthew 27-28 (Passion/Resurrection) now present? (Geneva wording)
    for name, phrase in [
        ("Mt1:1", "The book of the generation of Jesus Christ"),
        ("Mt27 Barabbas", "Whether of the twain will ye that I let loose"),
        ("Mt28 resurrection", "for he is risen"),
        ("Mk1:1", "The beginning of the Gospel of Jesus Christ"),
        ("Mk16 end", "preached everywhere"),
    ]:
        i = ref.find(phrase)
        print(f"  {name:20s}: {'FOUND @' + str(i) if i >= 0 else 'MISSING'}")
    # no cross-ref leakage?
    for name, phrase in [("xref 'Luke 3:23'", "Luke 3:23"), ("xref 'Gen. 21:2'", "Gen. 21:2")]:
        print(f"  {name:20s}: {'present (LEAK)' if phrase in ref else 'absent (clean)'}")
    return project.metadata.id


def _geneva_dir() -> Path:
    return next(WS.glob("1599-geneva-bible-*"))


def build_geneva_layout() -> None:
    """Stage A1: author the Matthew+Mark layout (book containers + per-chapter heading+chapter).

    Geneva prints no "Chapter N" text headings, so detect_layout can't find chapters. We parse the
    Mt/Mk regions directly: each chapter is one argument paragraph (type=heading, MASKED) followed
    by its verse paragraphs (type=chapter, verse text, unmasked). Two book containers scope the
    later derive. Verse paras match ^\\d+\\xa0 (non-breaking space); arguments start with digits +
    a regular space, so the two never collide. Chapter boundaries fall on verse-number resets to 1.
    """
    import re
    from palimpsest.layout import LayoutConfig, LayoutSection, save_layout

    p = Project.load(_geneva_dir())
    ref = p.reference_text()

    def book_region(name: str) -> tuple[int, int]:
        head = f"\n\n{name}\n\n"
        i = ref.rfind(head)
        if i < 0:
            raise SystemExit(f"book heading {name!r} not found")
        return i, i + len(head)

    mt_h, mt_body = book_region("MATTHEW")
    mk_h, mk_body = book_region("MARK")
    lk_h, _ = book_region("LUKE")
    if not (mt_h < mk_h < lk_h):
        raise SystemExit(f"heading order wrong: MATTHEW={mt_h} MARK={mk_h} LUKE={lk_h}")

    VERSE = re.compile(r"^(\d{1,3})\xa0")
    sections: list[LayoutSection] = []

    def parse_book(name: str, book_id: str, body_start: int, region_end: int, expect: int) -> int:
        bk = name.title()
        sections.append(LayoutSection(
            id=book_id, type="book", start=body_start, end=region_end,
            label=bk, name=book_id, source="user", metadata={"book": bk}))
        region = ref[body_start:region_end]
        paras: list[tuple[int, int, str]] = []
        pos = 0
        for chunk in region.split("\n\n"):
            ps = body_start + pos
            paras.append((ps, ps + len(chunk), chunk))
            pos += len(chunk) + 2
        n = len(paras)
        ch = 0
        i = 0
        while i < n:
            ps, pe, txt = paras[i]
            nxt = paras[i + 1] if i + 1 < n else None
            nxt_v1 = bool(nxt and (m := VERSE.match(nxt[2])) and int(m.group(1)) == 1)
            if txt.strip() and not VERSE.match(txt) and nxt_v1:
                ch += 1
                sections.append(LayoutSection(
                    id=f"heading-{book_id}-{ch:02d}", type="heading", start=ps, end=pe,
                    label=f"{bk} {ch} argument", name=f"heading_{ch}",
                    parent_id=book_id, source="user", metadata={"book": bk, "chapter": ch}))
                j = i + 1
                while j < n and VERSE.match(paras[j][2]):
                    j += 1
                sections.append(LayoutSection(
                    id=f"chapter-{book_id}-{ch:02d}", type="chapter",
                    start=paras[i + 1][0], end=paras[j - 1][1],
                    label=f"{bk} {ch}", name=f"chapter_{ch}",
                    parent_id=book_id, source="user", metadata={"book": bk, "chapter": ch}))
                i = j
            else:
                i += 1
        if ch != expect:
            raise SystemExit(f"{name}: parsed {ch} chapters, expected {expect}")
        return ch

    n_mt = parse_book("MATTHEW", "book-matthew", mt_body, mk_h, 28)
    n_mk = parse_book("MARK", "book-mark", mk_body, lk_h, 16)

    save_layout(p.path, LayoutConfig(sections=sections, applied=True))
    n_ch = sum(1 for s in sections if s.type == "chapter")
    n_hd = sum(1 for s in sections if s.type == "heading")
    print(f"layout: {len(sections)} sections — Mt {n_mt}ch + Mk {n_mk}ch; "
          f"books=2 chapters={n_ch} headings={n_hd}")
    print(f"saved -> {p.path / 'layout_sections.json'}")


def write_geneva_verses() -> int:
    """Stage A2: build Geneva's verse-number mask layer (Matthew + Mark).

    The gold map masks structural elements (chapter arguments) but _write_verses_track only
    parses DR's "C:V." markers, so Geneva's "N\\xa0 " verse numbers leak into analyzable text.
    Geneva prints one \\n\\n-separated paragraph per verse, line-anchored "<num>\\xa0 <prose>".
    We scan each chapter section for those markers and emit {b,c,v,ns,s,e} so masked_intervals
    unions the [ns,s) number spans — reaching DR-MM parity (verse numbers excluded from analysis).
    Scoped to Matthew+Mark (the only books derived); other books stay unmasked (unused).
    """
    import re
    import json as _json
    from palimpsest.layout import load_layout

    p = Project.load(_geneva_dir())
    ref = p.reference_text()
    cfg = load_layout(p.path)

    def hdr(name: str) -> int:
        i = ref.find(f"\n\n{name}\n\n")
        if i < 0:
            raise SystemExit(f"book heading {name!r} not found")
        return i

    mt, mk, lk = hdr("MATTHEW"), hdr("MARK"), hdr("LUKE")
    if not (mt < mk < lk):
        raise SystemExit(f"heading order wrong: MATTHEW={mt} MARK={mk} LUKE={lk}")

    chapters = sorted((s for s in cfg.sections if s.type == "chapter"), key=lambda s: s.start)
    VERSE = re.compile(r"(?m)^(\d{1,3})[\xa0 ]+")

    recs: list[dict] = []
    counts = {"Matthew": 0, "Mark": 0}
    ch_idx = {"Matthew": 0, "Mark": 0}
    for sec in chapters:
        if mt <= sec.start < mk:
            book = "Matthew"
        elif mk <= sec.start < lk:
            book = "Mark"
        else:
            continue  # outside Matthew/Mark — skip (unused book)
        ch_idx[book] += 1
        ci = ch_idx[book]
        seg = ref[sec.start:sec.end]
        marks = list(VERSE.finditer(seg))
        for j, m in enumerate(marks):
            ns = sec.start + m.start(1)
            s = sec.start + m.end()
            e = (sec.start + marks[j + 1].start(1)) if j + 1 < len(marks) else sec.end
            recs.append({"b": book, "c": ci, "v": int(m.group(1)),
                         "ns": ns, "s": s, "e": e})
            counts[book] += 1

    track_path = p.path / "tracks" / "verses.jsonl"
    track_path.write_text(
        "\n".join(_json.dumps(r, ensure_ascii=False) for r in recs) + "\n", encoding="utf-8")
    print(f"Matthew chapters={ch_idx['Matthew']} verses={counts['Matthew']}")
    print(f"Mark chapters={ch_idx['Mark']} verses={counts['Mark']}")
    print(f"total verse records: {len(recs)} -> {track_path}")

    # verify analyzable now drops verse numbers around Matthew 1:1
    atext, _ = p.analyzable_text(sep="")
    i = atext.find("The book of the generation of Jesus Christ")
    ctx = atext[i - 30:i + 60] if i >= 0 else "(phrase not found)"
    print("analyzable @ Matthew 1:1 ->", repr(ctx))
    return len(recs)


def derive_geneva_mm() -> str:
    """Stage B: derive the Matthew+Mark subtext from the complete Geneva parent.

    extraction_types=["chapter"] keeps only verse-text sections; include_container_ids scopes to
    the two gospel book containers. derive_subtext remaps layout + verses.jsonl to the child, so the
    child's verse numbers stay masked (parity with DR-MM). Arguments (type=heading) are excluded.
    """
    WS.mkdir(parents=True, exist_ok=True)
    geneva = Project.load(_geneva_dir())
    child, child_cfg, summary = derive_subtext(
        geneva,
        WS,
        extraction_types=["chapter"],
        include_container_ids=["book-matthew", "book-mark"],
        title="1599 Geneva -- Matthew & Mark",
        author="Geneva (1599)",
    )
    text_len = len(child.reference_text())
    n_elem = _write_elements_track(child.path, child.metadata.id, child_cfg, text_len)
    print("Geneva-MM child id:", child.metadata.id)
    print("summary:", summary)
    print("elements written:", n_elem)
    return child.metadata.id


def _run_track(member_dir: Path, track_name: str, params: dict[str, str]) -> str:
    """Invoke the `run-track` CLI (the venv console script) and return its stdout, or fail loud."""
    cli = Path(sys.executable).with_name("palimpsest")  # console script beside this interpreter
    cmd = [str(cli), "run-track", str(member_dir), track_name]
    for key, value in params.items():
        cmd += ["-p", f"{key}={value}"]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise SystemExit(
            f"run-track {track_name} failed for {member_dir.name}:\n{proc.stdout}\n{proc.stderr}")
    return proc.stdout


def _parse_label(stdout: str, track_name: str) -> str:
    """Pull the content-addressed layer label out of `... {track_name} (label <hex>)`."""
    m = re.search(rf"{re.escape(track_name)} \(label\s+([0-9a-f]+)\)", stdout)
    if not m:
        raise SystemExit(f"could not parse {track_name} label from run-track output:\n{stdout}")
    return m.group(1)


def embed_members() -> None:
    """Stage C (optional): chunk + embed every collection member so the embedding-gated paths work.

    Reads the standing collection's membership (created per README) and, for each member, runs the
    chunking track (word/100) then the embedding track (MLX by default) over that chunk layer. Both
    tracks are content-addressed and idempotent, so re-running reproduces the same labels rather than
    piling up duplicate layers. Requires a live embedding service; a provider/endpoint failure exits
    non-zero (no silent fallback). After this, cosine congruence is all-congruent and probe returns
    cross-translation matches.
    """
    from palimpsest.collections import get_collection

    col = get_collection(WS, CID)
    if col is None:
        raise SystemExit(
            f"collection {CID!r} not found in {WS}; create it first (see README 'Create the collection')")
    members = col.get("project_ids") or []
    if not members:
        raise SystemExit(f"collection {CID!r} has no members")
    for pid in members:
        member_dir = WS / pid
        if not member_dir.exists():
            raise SystemExit(f"member dir missing: {member_dir}")
        chunk_label = _parse_label(
            _run_track(member_dir, "chunking",
                       {"chunk_mode": CHUNK_MODE, "chunk_size": CHUNK_SIZE}),
            "chunking")
        embed_label = _parse_label(
            _run_track(member_dir, "embedding",
                       {"chunk_label": chunk_label, "embed_provider": EMBED_PROVIDER,
                        "embed_endpoint": EMBED_ENDPOINT, "embed_model": EMBED_MODEL}),
            "embedding")
        print(f"{pid}: chunk={chunk_label} embed={embed_label}")
    print(f"embedded {len(members)} member(s) via {EMBED_PROVIDER} ({EMBED_MODEL})")


if __name__ == "__main__":
    step = sys.argv[1] if len(sys.argv) > 1 else "dr"
    steps = {
        "dr": build_dr_mm,
        "geneva-complete": build_geneva_complete,
        "geneva-layout": build_geneva_layout,
        "geneva-verses": write_geneva_verses,
        "geneva-mm": derive_geneva_mm,
        "embed": embed_members,
    }
    if step not in steps:
        raise SystemExit(f"unknown step {step!r}; choose from {', '.join(steps)}")
    steps[step]()

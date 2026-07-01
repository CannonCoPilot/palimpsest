"""Regenerate the standing Matthew-Mark cross-translation validation collections.

Two collections are built from Matthew+Mark subtexts of three Bible translations:
  * matthew-mark-validation (2 members): DR-MM + Geneva-MM — the original standing collection.
  * matthew-mark-6way (6 members): Matthew-only and Mark-only subtexts of DR, Geneva, and KJV —
    the richer collection the corpus-graph over-merge, phyletic tree, and synoptic precision/recall
    oracle are validated against. A 7-member variant adds KJV Luke as a genuine phyletic outgroup.

Run from the palimpsest repo root. Reads local sources (the gold DR in .scratch/demo and the Geneva
+ KJV EPUBs in imports/Scripture/Bibles — all gitignored, never committed) WITHOUT modifying them;
all outputs land in .scratch/validation-mm (gitignored). Expected metrics + provenance are recorded
in manifest.json; validate.py + the `validate-splits` step assert them. See README.md for the recipe.

Pipeline (run each step in order):
  dr / geneva-* / geneva-mm     the 2-member standing collection's DR-MM + Geneva-MM subtexts
  kjv-complete   re-ingest the COMPLETE KJV (verse-paragraph patched so verses become paragraphs)
  kjv-layout     author the KJV Matthew+Mark+Luke layout (book containers + per-chapter sections)
  kjv-verses     build KJV's verse-number mask layer
  kjv-mm         derive the KJV Matthew+Mark subtext
  kjv-luke       derive the KJV Luke subtext (the 7-way outgroup)   [kjv-luke-validate asserts it]
  split          derive the 6 single-book members + create the matthew-mark-6way collection
  validate-splits  assert the 6 members are book-pure with the expected verse counts
  align / graph  word-align every 6-way pair + build its corpus graph (the analysis substrate the
                 synoptic scorer + corpus-graph tests consume)
  luke-collection  create the matthew-mark-luke-7way collection, align its Luke pairs, rebuild graph
  embed          chunk + MLX-embed the 2-member collection (optional; needs a live embed service)

    core/.venv/bin/python core/tests/fixtures/validation-mm/build.py <step>

After the subtexts + `split`, the collections exist; `align`/`graph` produce the pairwise + corpus
substrate, and score_synoptic.py scores cross-book detection against synoptic-ground-truth.json.
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


# ── KJV (3rd translation) — the cleanest source: labelled book/chapter headings, no footnotes ────
KJV_EPUB_GLOB = "The Holy Bible -- King James Version of 1611*.epub"
MT_CHAPTERS, MK_CHAPTERS, LK_CHAPTERS = 28, 16, 24


def _kjv_profile():
    """KEEP verse-number spans (needed for the verse layer); strip only TOC/index anchors."""
    from palimpsest.ingest.content_filters import ContentProfile, ElementSelector
    return ContentProfile(
        name="bible-kjv-complete",
        strip_selectors=[
            ElementSelector(tag="a", classes=frozenset({"index"})),
            ElementSelector(tag="a", classes=frozenset({"index2a"})),
        ],
    )


def _kjv_dir() -> Path:
    # The glob also matches derived "-chapter-in-…" children; select the parent (no derive suffix).
    return next(d for d in WS.glob("the-holy-bible-king-james-version*")
                if d.is_dir() and "-chapter-in-" not in d.name)


def _patch_epub(src: Path) -> Path:
    """Split each chapter <p> into one <p> per verse so verses become paragraphs (parity with
    DR/Geneva, which naturally have one verse per <p>). The KJV epub packs a whole chapter into a
    single <p> with inline <span class="verses">N</span> markers; prefixing each verse span with
    </p><p> turns every verse into its own paragraph. Without this the whole chapter is one paragraph
    and paragraph-vs-paragraph alignment degenerates (the granularity-mismatch bug that gave 0 records
    for every KJV pair). Ingesting the patched epub keeps reference/coordinate offsets self-consistent."""
    import zipfile
    dst = Path(".scratch/_kjv_patched.epub")
    with zipfile.ZipFile(src) as zin, zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename.lower().endswith((".xhtml", ".html", ".htm")):
                text = data.decode("utf-8", "ignore").replace(
                    '<span class="verses">', '</p><p><span class="verses">')
                data = text.encode("utf-8")
            zout.writestr(item, data)
    return dst


def build_kjv_complete() -> str:
    WS.mkdir(parents=True, exist_ok=True)
    src_epub = next(Path("imports/Scripture/Bibles").glob(KJV_EPUB_GLOB))
    epub = _patch_epub(src_epub)
    print("epub (verse-paragraph patched):", epub.name)
    # source_name pins the slug to the ORIGINAL epub filename so the verse-patched re-ingest keeps
    # the same project id (…2165f965…) and cleanly replaces the prior chapter-paragraph member,
    # rather than minting a new "kjv-patched" id that would orphan the collection membership.
    project = ingest_file(
        epub, WS, overwrite=True, content_profile=_kjv_profile(), source_name=src_epub.name
    )
    ref = project.reference_text()
    print("ingested id:", project.metadata.id)
    print("reference chars:", len(ref), "words:", project.metadata.word_count)
    for name, phrase in [
        ("Mt1:1", "The book of the generation of Jesus Christ"),
        ("Mt27 Barabbas", "Barabbas"),
        ("Mt28 resurrection", "He is not here: for he is risen"),
        ("Mk1:1", "The beginning of the gospel of Jesus Christ"),
        ("Mk16 end", "and preached every where"),
    ]:
        i = ref.find(phrase)
        print(f"  {name:20s}: {'FOUND @' + str(i) if i >= 0 else 'MISSING'}")
    return project.metadata.id


def _book_region(ref: str, name: str) -> tuple[int, int]:
    """Return (heading_start, body_start) for a book whose h1 heading is '\\n\\n{name}\\n\\n'."""
    head = f"\n\n{name}\n\n"
    i = ref.find(head)
    if i < 0:
        raise SystemExit(f"book heading {name!r} not found")
    return i, i + len(head)


def build_kjv_layout() -> None:
    """Author the SUPERSET Matthew+Mark+Luke layout (Luke kept so the 7-way outgroup is re-derivable).
    Chapter headings are explicit ('Matthew N' paragraphs); each chapter's verse text is the block
    between its heading and the next chapter heading."""
    from palimpsest.layout import LayoutConfig, LayoutSection, save_layout

    p = Project.load(_kjv_dir())
    ref = p.reference_text()

    mt_h, mt_body = _book_region(ref, "Matthew")
    mk_h, mk_body = _book_region(ref, "Mark")
    lk_h, lk_body = _book_region(ref, "Luke")
    jn_h, _ = _book_region(ref, "John")
    if not (mt_h < mk_h < lk_h < jn_h):
        raise SystemExit(f"heading order wrong: Mt={mt_h} Mk={mk_h} Lk={lk_h} Jn={jn_h}")

    sections: list[LayoutSection] = []

    def parse_book(name: str, book_id: str, body_start: int, region_end: int, expect: int) -> int:
        sections.append(LayoutSection(
            id=book_id, type="book", start=body_start, end=region_end,
            label=name, name=book_id, source="user", metadata={"book": name}))
        region = ref[body_start:region_end]
        chap_head = re.compile(rf"^{re.escape(name)} (\d{{1,3}})$")
        paras: list[tuple[int, int, str]] = []
        pos = 0
        for chunk in region.split("\n\n"):
            ps = body_start + pos
            paras.append((ps, ps + len(chunk), chunk))
            pos += len(chunk) + 2
        heads = [(int(m.group(1)), i) for i, (_, _, txt) in enumerate(paras)
                 if (m := chap_head.match(txt.strip()))]
        if [c for c, _ in heads] != list(range(1, expect + 1)):
            raise SystemExit(f"{name}: chapter headings {[c for c,_ in heads]} != 1..{expect}")
        for k, (ch, hi) in enumerate(heads):
            hp = paras[hi]
            sections.append(LayoutSection(
                id=f"heading-{book_id}-{ch:02d}", type="heading", start=hp[0], end=hp[1],
                label=f"{name} {ch} heading", name=f"heading_{ch}",
                parent_id=book_id, source="user", metadata={"book": name, "chapter": ch}))
            next_hi = heads[k + 1][1] if k + 1 < len(heads) else len(paras)
            vp = [paras[j] for j in range(hi + 1, next_hi) if paras[j][2].strip()]
            if not vp:
                raise SystemExit(f"{name} {ch}: no verse paragraphs")
            sections.append(LayoutSection(
                id=f"chapter-{book_id}-{ch:02d}", type="chapter",
                start=vp[0][0], end=vp[-1][1],
                label=f"{name} {ch}", name=f"chapter_{ch}",
                parent_id=book_id, source="user", metadata={"book": name, "chapter": ch}))
        return len(heads)

    n_mt = parse_book("Matthew", "book-matthew", mt_body, mk_h, MT_CHAPTERS)
    n_mk = parse_book("Mark", "book-mark", mk_body, lk_h, MK_CHAPTERS)
    n_lk = parse_book("Luke", "book-luke", lk_body, jn_h, LK_CHAPTERS)

    save_layout(p.path, LayoutConfig(sections=sections, applied=True))
    n_ch = sum(1 for s in sections if s.type == "chapter")
    n_hd = sum(1 for s in sections if s.type == "heading")
    print(f"layout: {len(sections)} sections — Mt {n_mt}ch + Mk {n_mk}ch + Lk {n_lk}ch; "
          f"books=3 chapters={n_ch} headings={n_hd}")
    print(f"saved -> {p.path / 'layout_sections.json'}")


def write_kjv_verses() -> int:
    """Build the verse-number mask layer. Verse numbers are inline tokens in the chapter block,
    monotonic 1..K; greedily match the next expected number so incidental digits can't mis-anchor."""
    import json as _json
    from collections import defaultdict
    from palimpsest.layout import load_layout

    p = Project.load(_kjv_dir())
    ref = p.reference_text()
    cfg = load_layout(p.path)

    chapters = sorted((s for s in cfg.sections if s.type == "chapter"), key=lambda s: s.start)
    # Verse markers are standalone digit runs not glued to a letter/digit. Red-letter verses abut the
    # prior verse's punctuation ("heaven.4 Blessed"), and some numbers are followed by "(" not space
    # ("clothed?32(For ..."), so the lookbehind allows any non-alnum and the lookahead only forbids
    # another digit. KJV spells numbers out in prose, so verse numbers are the only digit runs.
    VERSE = re.compile(r"(?<![0-9A-Za-z])(\d{1,3})(?![0-9])")
    recs: list[dict] = []
    counts: dict[str, int] = defaultdict(int)
    for sec in chapters:
        book = sec.metadata.get("book")
        ci = sec.metadata.get("chapter")
        seg = ref[sec.start:sec.end]
        marks = [(int(m.group(1)), sec.start + m.start(1), sec.start + m.end(1))
                 for m in VERSE.finditer(seg)]
        nums = [vn for vn, _, _ in marks]
        if nums != list(range(1, len(nums) + 1)):
            raise SystemExit(f"{book} {ci}: verse numbers not monotonic 1..K: {nums}")
        for j, (vn, ns, s) in enumerate(marks):
            e = marks[j + 1][1] if j + 1 < len(marks) else sec.end
            recs.append({"b": book, "c": ci, "v": vn, "ns": ns, "s": s, "e": e})
            counts[book] += 1

    track_path = p.path / "tracks" / "verses.jsonl"
    track_path.parent.mkdir(parents=True, exist_ok=True)
    track_path.write_text(
        "\n".join(_json.dumps(r, ensure_ascii=False) for r in recs) + "\n", encoding="utf-8")
    print("  ".join(f"{b} verses={counts[b]}" for b in sorted(counts)) + f"  total={len(recs)}")
    return len(recs)


def derive_kjv_mm() -> str:
    """Derive the KJV Matthew+Mark subtext (the 3rd MM parent that `split` divides into 2 members)."""
    WS.mkdir(parents=True, exist_ok=True)
    kjv = Project.load(_kjv_dir())
    child, child_cfg, summary = derive_subtext(
        kjv, WS, extraction_types=["chapter"],
        include_container_ids=["book-matthew", "book-mark"],
        title="King James -- Matthew & Mark", author="King James Version (1611/1769)",
    )
    n_elem = _write_elements_track(child.path, child.metadata.id, child_cfg, len(child.reference_text()))
    print("KJV-MM child id:", child.metadata.id, "| summary:", summary, "| elements:", n_elem)
    return child.metadata.id


def derive_kjv_luke() -> str:
    """Derive the KJV-Luke single-book subtext — a genuine outgroup for the Matthew/Mark collection.
    Requires the superset layout (run kjv-layout + kjv-verses first) so book-luke + its verses exist."""
    WS.mkdir(parents=True, exist_ok=True)
    kjv = Project.load(_kjv_dir())
    child, child_cfg, summary = derive_subtext(
        kjv, WS, extraction_types=["chapter"], include_container_ids=["book-luke"],
        title="King James -- Luke", author="King James Version (1611/1769)",
    )
    n_elem = _write_elements_track(child.path, child.metadata.id, child_cfg, len(child.reference_text()))
    print("KJV-Luke child id:", child.metadata.id, "| summary:", summary, "| elements:", n_elem)
    return child.metadata.id


def _luke_child_dir() -> Path:
    return next(d for d in WS.glob("the-holy-bible-king-james-version*chapter-in-book-luke")
                if d.is_dir())


def validate_kjv_luke() -> None:
    """Mirror the DR-MM parity checks: Luke-only, 24 chapters, analyzable drops verse numbers."""
    import json as _json
    from collections import Counter

    child = Project.load(_luke_child_dir())
    ref = child.reference_text()
    print("child id:", child.metadata.id, "| chars:", len(ref))
    print("HEAD:", repr(ref[:80]), "\nTAIL:", repr(ref[-80:]))
    verses = [_json.loads(l) for l in (child.path / "tracks" / "verses.jsonl").read_text().splitlines() if l.strip()]
    books = Counter(v["b"] for v in verses)
    chapters = sorted({v["c"] for v in verses})
    print(f"verses={len(verses)}  books={dict(books)}  chapters={len(chapters)} ({chapters[0]}..{chapters[-1]})")
    ok_book = set(books) == {"Luke"}
    ok_chap = chapters == list(range(1, LK_CHAPTERS + 1))
    print(f"CHECK books=={{Luke}}: {ok_book}   chapters==1..{LK_CHAPTERS}: {ok_chap}")
    if not (ok_book and ok_chap):
        raise SystemExit("KJV-Luke validation FAILED")
    print("KJV-Luke validation PASSED")


# ── 6-way single-book split (DR + Geneva + KJV MM subtexts → Matthew-only / Mark-only members) ────
CID_6WAY = "matthew-mark-6way"
CID_7WAY = "matthew-mark-luke-7way"

# (translation label, author suffix, MM-parent glob, Matthew container, Mark container, member number).
# The MM parents are discovered by GLOB (never hardcode content-hash ids — they change on re-ingest);
# the containers are stable structural ids inherited from each translation's layout.
MM_SOURCES = [
    ("Douay-Rheims", "(1582-1610)", "douay-rheims-*-chapter-in-book-0047-book-0048", "book-0047", "book-0048", 1),
    ("1599 Geneva", "(1599)", "1599-geneva-*-chapter-in-book-mark-book-matthew", "book-matthew", "book-mark", 2),
    ("King James", "(1611/1769)", "the-holy-bible-king-james-*-chapter-in-book-mark-book-matthew", "book-matthew", "book-mark", 3),
]
# Content-hash prefix -> translation, for id-based classification in validation/labels.
_TRANS_KEY = {"1a24ae78": "DR", "19f28a69": "Geneva", "2165f965": "KJV"}
# Per single-book member: expected verse count (DR is Vulgate, so Mt/Mk run one short of the Protestant
# versification — an intended cross-translation difference, not an error).
_EXPECTED_VERSES = {
    ("DR", "Matthew"): 1070, ("DR", "Mark"): 677,
    ("Geneva", "Matthew"): 1071, ("Geneva", "Mark"): 678,
    ("KJV", "Matthew"): 1071, ("KJV", "Mark"): 678,
}


def _mm_parent_dir(glob: str) -> Path:
    """Locate a Matthew+Mark subtext dir by glob (the derive-of-full-Bible parent to split)."""
    matches = sorted(d for d in WS.glob(glob) if d.is_dir())
    if not matches:
        raise SystemExit(f"MM subtext not found for glob {glob!r} in {WS}; run its *-mm step first")
    return matches[0]


def _member_book(mid: str) -> str:
    # A split child ends in "-chapter-in-<single-book-container>"; the DR MM parent's own id already
    # contains BOTH "book-0047" and "book-0048", so classify by the FINAL container only, not a
    # substring search over the whole id.
    tail = mid.rsplit("-chapter-in-", 1)[-1]
    return "Matthew" if tail in ("book-0047", "book-matthew") else "Mark"


def _member_trans(mid: str) -> str:
    return next((v for k, v in _TRANS_KEY.items() if k in mid), "?")


def _derive_single_book(parent_dir: Path, container_id: str, book: str, title: str, author: str) -> dict:
    """Derive a single-book child (Matthew-only or Mark-only) from an MM subtext. Idempotent: the child
    id is a function of parent + container, so re-running overwrites the same dir. Returns a summary."""
    import json as _json
    parent = Project.load(parent_dir)
    child, child_cfg, _summary = derive_subtext(
        parent, WS, extraction_types=["chapter"], include_container_ids=[container_id],
        title=title, author=author,
    )
    _write_elements_track(child.path, child.metadata.id, child_cfg, len(child.reference_text()))
    books: dict[str, int] = {}
    vpath = child.path / "tracks" / "verses.jsonl"
    if vpath.exists():
        for line in vpath.read_text(encoding="utf-8").splitlines():
            if line.strip():
                b = _json.loads(line)["b"]
                books[b] = books.get(b, 0) + 1
    return {"id": child.metadata.id, "book": book, "chars": len(child.reference_text()), "verse_books": books}


def build_splits() -> None:
    """Derive the six single-book members (Matthew/Mark × DR/Geneva/KJV) from the three MM subtexts and
    create the matthew-mark-6way collection. Each split is a derive-of-a-derive (also exercises
    derivation robustness). Requires the dr / geneva-* / kjv-* subtext steps to have run first."""
    from palimpsest.collections import create_collection, get_collection

    members: list[str] = []
    ok = True
    for label, author, glob, mt_c, mk_c, num in MM_SOURCES:
        parent_dir = _mm_parent_dir(glob)
        for book, container in (("Matthew", mt_c), ("Mark", mk_c)):
            r = _derive_single_book(parent_dir, container, book,
                                    f"{label} -- {book}", f"{label} {author}")
            members.append(r["id"])
            pure = set(r["verse_books"]) == {book}
            ok = ok and pure
            print(f"  {label:12s} {book:7s} (Matt{num}/Mark{num}): {r['chars']:>7d} chars  "
                  f"verses={r['verse_books']}  {'OK' if pure else 'BOOK LEAK!'}")
    if not ok:
        raise SystemExit("split produced a book-impure member — aborting before collection create")
    if get_collection(WS, CID_6WAY):
        print(f"{CID_6WAY} already exists; leaving membership unchanged")
    else:
        col = create_collection(
            WS, label="Matthew / Mark — 6-way cross-translation",
            description="Matthew-only and Mark-only subtexts from the Douay-Rheims, 1599 Geneva, and "
                        "KJV (6 members) — the standing collection for cross-text / corpus-graph "
                        "validation and the synoptic precision/recall oracle.",
            project_ids=members, collection_id=CID_6WAY)
        print(f"created {col['id']} with {len(col['project_ids'])} members")


def create_7way() -> None:
    """Create the 7-way collection = the six Matt/Mark members + KJV-Luke (a genuine outgroup)."""
    from palimpsest.collections import create_collection, get_collection
    six = get_collection(WS, CID_6WAY)
    if six is None:
        raise SystemExit(f"{CID_6WAY} not found; run the `split` step first")
    members = list(six["project_ids"]) + [Project.load(_luke_child_dir()).metadata.id]
    if get_collection(WS, CID_7WAY):
        print(f"{CID_7WAY} already exists; leaving membership unchanged")
        return
    col = create_collection(
        WS, label="Matthew / Mark / Luke (7-way, Luke outgroup)",
        description="The 6-way Matt/Mark members plus a KJV Luke subtext as a genuine outgroup for "
                    "phyletic stress-testing.",
        project_ids=members, collection_id=CID_7WAY)
    print(f"created {col['id']} with {len(col['project_ids'])} members")


def _align_pair(a_id: str, b_id: str) -> tuple[int, float]:
    """Word-method pairwise alignment for one member pair — mirrors POST /api/alignment/run 'word'."""
    import json as _json
    from palimpsest.alignment.cross_similarity import compute_word_overlap
    from palimpsest.alignment.smith_waterman import smith_waterman as sw_align
    from palimpsest.alignment.records import write_alignment_records, comparison_dir
    from palimpsest.formats.signals import write_signal
    pa, pb = Project.load(WS / a_id), Project.load(WS / b_id)
    comp = comparison_dir(WS, a_id, b_id)
    comp.mkdir(parents=True, exist_ok=True)
    matrix, manifest = compute_word_overlap(pa, pb)
    write_signal(comp, matrix, manifest)
    records = sw_align(matrix, a_id, b_id, "word")
    write_alignment_records(comp / "alignment.jsonl", records)
    (comp / "metadata.json").write_text(_json.dumps({
        "query_id": a_id, "target_id": b_id, "method": "word", "record_count": len(records),
    }, indent=2), encoding="utf-8")
    return len(records), float(max((r.score for r in records), default=0.0))


def _align_collection(cid: str) -> None:
    from itertools import combinations
    from palimpsest.collections import get_collection
    col = get_collection(WS, cid)
    if col is None:
        raise SystemExit(f"{cid} not found; create it first")
    pairs = list(combinations(col["project_ids"], 2))
    print(f"aligning {len(pairs)} member pairs of {cid} (word method)...")
    for a, b in pairs:
        n, top = _align_pair(a, b)
        lab_a, lab_b = f"{_member_trans(a)}-{_member_book(a)}", f"{_member_trans(b)}-{_member_book(b)}"
        print(f"  {lab_a:12s} x {lab_b:12s}: records={n:4d}  top={top:7.2f}")


def _graph_collection(cid: str) -> None:
    from collections import Counter
    from palimpsest.corpus_graph import build_corpus_graph, write_corpus_graph, phyletic_tree
    g = build_corpus_graph(WS, cid)
    write_corpus_graph(WS, cid, g)
    c = Counter(comp.classification for comp in g.components)
    print(f"corpus-graph {cid}: {len(g.nodes)} nodes, {len(g.components)} components -> "
          f"core={c.get('core', 0)} shell={c.get('shell', 0)} singleton={c.get('singleton', 0)}")
    tree = phyletic_tree(g)
    print("phyletic suggested_root:", tree.get("suggested_root"),
          "| basis:", tree.get("distance_basis"), "| warning:", tree.get("distance_warning"))


def align_6way() -> None:
    _align_collection(CID_6WAY)


def graph_6way() -> None:
    _graph_collection(CID_6WAY)


def build_luke_collection() -> None:
    """Create the 7-way outgroup collection, align its Luke pairs, and rebuild its corpus graph."""
    create_7way()
    _align_collection(CID_7WAY)
    _graph_collection(CID_7WAY)


def validate_splits() -> None:
    """Assert the six single-book members are book-pure with the expected per-book verse counts."""
    import json as _json
    from collections import Counter
    from palimpsest.collections import get_collection
    col = get_collection(WS, CID_6WAY)
    if col is None:
        raise SystemExit(f"{CID_6WAY} not found; run the `split` step first")
    failures: list[str] = []
    for mid in col["project_ids"]:
        trans, book = _member_trans(mid), _member_book(mid)
        recs = [_json.loads(l) for l in
                (WS / mid / "tracks" / "verses.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
        books = Counter(r["b"] for r in recs)
        expected = _EXPECTED_VERSES.get((trans, book))
        pure = set(books) == {book}
        count_ok = expected is None or len(recs) == expected
        status = "OK" if (pure and count_ok) else "FAIL"
        if status == "FAIL":
            failures.append(mid)
        print(f"  {trans:7s} {book:7s}: verses={len(recs)} (expected {expected})  "
              f"books={dict(books)}  [{status}]")
    if failures:
        raise SystemExit(f"split validation FAILED for: {failures}")
    print(f"all {len(col['project_ids'])} single-book members valid (book-pure + expected verse counts)")


if __name__ == "__main__":
    step = sys.argv[1] if len(sys.argv) > 1 else "dr"
    steps = {
        # 2-member standing collection (DR-MM + Geneva-MM)
        "dr": build_dr_mm,
        "geneva-complete": build_geneva_complete,
        "geneva-layout": build_geneva_layout,
        "geneva-verses": write_geneva_verses,
        "geneva-mm": derive_geneva_mm,
        # 3rd translation (KJV) subtexts, for the 6-way + Luke outgroup
        "kjv-complete": build_kjv_complete,
        "kjv-layout": build_kjv_layout,
        "kjv-verses": write_kjv_verses,
        "kjv-mm": derive_kjv_mm,
        "kjv-luke": derive_kjv_luke,
        "kjv-luke-validate": validate_kjv_luke,
        # 6-way single-book split + collection + analysis substrate
        "split": build_splits,
        "validate-splits": validate_splits,
        "align": align_6way,
        "graph": graph_6way,
        "luke-collection": build_luke_collection,
        # optional embedding (2-member standing collection; needs a live embed service)
        "embed": embed_members,
    }
    if step not in steps:
        raise SystemExit(f"unknown step {step!r}; choose from {', '.join(steps)}")
    steps[step]()

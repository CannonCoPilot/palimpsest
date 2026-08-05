"""Empirical version comparison for the OriginalDR pilot report (Sir, v8.1).

Determines whether a report version actually improved over its predecessor — EXCLUSIVELY from measured
numbers (pass rates, localization/coverage rates, books failing, per-source failing proportion, apparatus
witness/localization counts), NEVER from claimed implementations or dev-phase narrative. A build can assert
whatever it likes in its changelog; this module only believes the audit data.

The metric snapshot is derived from a report's embedded DATA object, so it works identically for the LIVE
build (pass the freshly-built `data` dict) and for any ARCHIVED report HTML (extract its `const DATA = {..}`).
That makes historical backfill exact: every version is measured the same way from its own frozen data.

Key honesty rule (No Silent Degradation): when the verse-audit INPUT is byte-identical between two versions
(same source_sha256), the verse metrics MUST be identical — a "presentation-only" build cannot have moved
them. The comparator verifies this and labels the scripture domain FROZEN rather than letting a cosmetic
change masquerade as an improvement. Apparatus metrics are compared independently (they can move when the
apparatus audit is re-run even if the verse audit is frozen).

CLI:
  version_compare.py <A> <B>            compare two versions by number (from reports-archive + versions.json)
  version_compare.py --html X.html Y.html   compare two report HTML files directly
  version_compare.py --headline               print the current-vs-prior verdict (for the report headline)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ARCHIVE = HERE / "reports-archive"
VERSIONS = ARCHIVE / "versions.json"

# metric -> +1 if higher is better, -1 if lower is better. Only RATES / PROPORTIONS drive the verdict
# (Sir's list): raw counts (worklist size, open slots, records) are coverage-confounded when the audited
# universe grows, so they are reported for context but never scored good/bad.
DIRECTION: dict[str, int] = {
    "pass_rate_archaic": +1, "pass_rate_modern": +1, "pass_rate_both": +1,
    "verse_cover_rate": +1, "chapter_cover_rate": +1, "book_cover_rate": +1,
    "books_failing_rate": -1, "source_fail_mean": -1, "source_fail_worst": -1,
    "apparatus_witness_rate": +1, "apparatus_localize_rate": +1,
}
SCRIPTURE_METRICS = ("pass_rate_archaic", "pass_rate_modern", "pass_rate_both",
                     "verse_cover_rate", "chapter_cover_rate", "book_cover_rate",
                     "books_failing_rate", "source_fail_mean", "source_fail_worst")
APPARATUS_METRICS = ("apparatus_witness_rate", "apparatus_localize_rate")
# raw counts shown as context only (not verdict-driving)
CONTEXT_METRICS = ("records", "books_failing", "apparatus_elements", "apparatus_witnesses",
                   "apparatus_localized", "apparatus_worklist", "apparatus_open_slots")


# --------------------------------------------------------------------------------------------------
# Metric extraction from a report DATA object (identical for live build and archived HTML)
# --------------------------------------------------------------------------------------------------
def metrics_from_data(data: dict[str, Any]) -> dict[str, Any]:
    """Reduce a report DATA object to the empirical metric snapshot. Missing fields -> None (honest;
    an old version that never carried a metric is not scored on it), never a fabricated default."""
    m: dict[str, Any] = {}
    rg = data.get("regimes", {}) or {}
    recs = rg.get("records") or 0
    m["records"] = recs or None
    for g in ("archaic", "modern", "both"):
        m[f"pass_{g}"] = rg.get(g)
        m[f"pass_rate_{g}"] = round(rg[g] / recs, 4) if (recs and rg.get(g) is not None) else None
    gb = data.get("grain_breakout", {}) or {}
    for lvl in ("verse", "chapter", "book"):
        pair = (gb.get(lvl, {}) or {}).get("archaic")
        hit, tot = (pair[0], pair[1]) if pair else (None, None)
        m[f"{lvl}_covered"], m[f"{lvl}_total"] = hit, tot
        m[f"{lvl}_cover_rate"] = round(hit / tot, 4) if (hit is not None and tot) else None
    books = data.get("books", []) or []
    def _book_fails(b: dict) -> bool:
        sc = [sd for sd in (b.get("sources", {}) or {}).values() if sd.get("kind") == "scan"]
        return bool(sc) and all((sd.get("pass_archaic") or 0) == 0 for sd in sc)
    m["books_total"] = len(books) or None
    m["books_failing"] = sum(1 for b in books if _book_fails(b)) if books else None
    m["books_failing_rate"] = (round(m["books_failing"] / m["books_total"], 4)
                               if (m["books_failing"] is not None and m["books_total"]) else None)
    # curated-only (REP-1): a PRE-curation prior version must not resurrect banned scan sources (S2/S5/S7/
    # S10-S15) in the delta display. Self-contained set (this module also runs standalone via --html).
    _CURATED_SCANS = {"S1", "S3", "S4", "S6", "S8", "S9"}
    srcfail: dict[str, float] = {}
    for s in data.get("sources", []) or []:
        if s.get("kind") != "scan" or s.get("id") not in _CURATED_SCANS:
            continue
        n = s.get("n_attested") or 0
        if n:
            srcfail[s["id"]] = round(1 - (s.get("pass_archaic") or 0) / n, 4)
    m["source_fail"] = srcfail
    m["source_fail_mean"] = round(sum(srcfail.values()) / len(srcfail), 4) if srcfail else None
    m["source_fail_worst"] = max(srcfail.values()) if srcfail else None
    ap = data.get("apparatus") or {}
    aps = (ap.get("summary") or {}) if isinstance(ap, dict) else {}
    els = (ap.get("elements") or {}) if isinstance(ap, dict) else {}
    # els holds only BUILT elements; E_v is each element's expected-witness count, so the built-set
    # union of E_v is the honest denominator for witness/localization RATES (raw counts are coverage-
    # confounded when the built set grows — see scope-change handling in compare()).
    m["apparatus_elements"] = aps.get("elements")
    m["apparatus_element_ids"] = sorted(els.keys()) if els else None
    m["apparatus_expected"] = sum((e.get("E_v") or 0) for e in els.values()) if els else None
    m["apparatus_witnesses"] = (sum((e.get("witness_count") or 0) for e in els.values()) if els else None)
    m["apparatus_localized"] = (sum((aps.get("scans_localized") or {}).values())
                                if aps.get("scans_localized") else None)
    _exp = m["apparatus_expected"]
    m["apparatus_witness_rate"] = (round(m["apparatus_witnesses"] / _exp, 4)
                                   if (m["apparatus_witnesses"] is not None and _exp) else None)
    m["apparatus_localize_rate"] = (round(m["apparatus_localized"] / _exp, 4)
                                    if (m["apparatus_localized"] is not None and _exp) else None)
    m["apparatus_worklist"] = aps.get("reocr_worklist")
    m["apparatus_open_slots"] = aps.get("open_slots")
    meta = data.get("meta", {}) or {}
    m["verse_input_sha"] = meta.get("source_sha256")
    m["version"] = meta.get("version")
    m["version_label"] = meta.get("version_label") or (
        str(meta.get("version")) if meta.get("version") is not None else None)
    m["n_verses"], m["n_books"] = meta.get("n_verses"), meta.get("n_books")
    m["scope_books"] = meta.get("scope_books")
    return m


def _extract_data_from_html(html: str) -> dict[str, Any] | None:
    """Pull the embedded `const DATA = {...};` object out of a built report by brace-matching (json.dumps
    emits it on one line, but scan defensively). Returns the parsed dict or None if absent/unparseable."""
    key = "const DATA = "
    i = html.find(key)
    if i < 0:
        return None
    j = html.find("{", i)
    if j < 0:
        return None
    depth, k, instr, esc = 0, j, False, False
    while k < len(html):
        ch = html[k]
        if instr:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                instr = False
        else:
            if ch == '"':
                instr = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(html[j:k + 1])
                    except json.JSONDecodeError:
                        return None
        k += 1
    return None


def metrics_from_html(path: Path) -> dict[str, Any] | None:
    data = _extract_data_from_html(path.read_text())
    return metrics_from_data(data) if data else None


# --------------------------------------------------------------------------------------------------
# Comparison
# --------------------------------------------------------------------------------------------------
def _classify(prev: Any, cur: Any, direction: int, eps: float = 1e-9) -> str:
    if prev is None or cur is None:
        return "n/a"
    d = (cur - prev) * direction
    if d > eps:
        return "improved"
    if d < -eps:
        return "regressed"
    return "flat"


def compare(prev: dict[str, Any], cur: dict[str, Any]) -> dict[str, Any]:
    """Empirical verdict for cur vs prev. Verifies the frozen-input invariant, then scores each metric and
    rolls the scripture and apparatus domains up to a verdict. Returns a JSON-serialisable structure."""
    per_metric: dict[str, Any] = {}
    for name, direction in DIRECTION.items():
        p, c = prev.get(name), cur.get(name)
        per_metric[name] = {"prev": p, "cur": c,
                            "delta": (round(c - p, 4) if (p is not None and c is not None) else None),
                            "verdict": _classify(p, c, direction)}

    # frozen-input invariant: identical verse audit sha => verse metrics cannot have moved.
    same_verse_input = (prev.get("verse_input_sha") is not None
                        and prev.get("verse_input_sha") == cur.get("verse_input_sha"))
    frozen_violation = []
    if same_verse_input:
        for name in SCRIPTURE_METRICS:
            if per_metric[name]["verdict"] not in ("flat", "n/a"):
                frozen_violation.append(name)

    def _roll(names: tuple[str, ...]) -> str:
        verdicts = [per_metric[n]["verdict"] for n in names]
        has_imp = "improved" in verdicts
        has_reg = "regressed" in verdicts
        if has_imp and has_reg:
            return "mixed"
        if has_imp:
            return "improved"
        if has_reg:
            return "regressed"
        if all(v == "n/a" for v in verdicts):
            return "n/a"
        return "flat"

    # scope-change guard: a rate delta computed over DIFFERENT universes is not a quality signal.
    # Adding John to scripture (v4->v5) drops the aggregate pass RATE because harder verses joined the
    # denominator — that is coverage, not regression. Growing the built apparatus set (v7->v8) likewise
    # changes the witness/localize denominator. When the scored set changed we refuse to call the domain
    # improved/regressed; we label it "scope-changed" and surface the raw direction as an informational note.
    def _as_set(v: Any) -> Any:
        return frozenset(v) if isinstance(v, (list, tuple)) else v
    scripture_scope_changed = _as_set(prev.get("scope_books")) != _as_set(cur.get("scope_books"))
    apparatus_scope_changed = _as_set(prev.get("apparatus_element_ids")) != _as_set(cur.get("apparatus_element_ids"))

    notes: list[str] = []
    if scripture_scope_changed:
        notes.append(f"scripture scope changed {prev.get('scope_books')} -> {cur.get('scope_books')}: "
                     "rate deltas are over different book sets (informational, not scored).")
    if apparatus_scope_changed:
        pids = set(prev.get("apparatus_element_ids") or [])
        cids = set(cur.get("apparatus_element_ids") or [])
        shape = "coverage expanded" if cids > pids else ("coverage shrank" if cids < pids else "set changed")
        pw, cw = prev.get("apparatus_witnesses"), cur.get("apparatus_witnesses")
        wdir = f"witnesses {pw}->{cw}" if (pw is not None and cw is not None) else "witness count n/a"
        notes.append(f"apparatus scope changed ({shape}): {prev.get('apparatus_element_ids')} -> "
                     f"{cur.get('apparatus_element_ids')}; {wdir} (informational, not scored).")

    if same_verse_input and not frozen_violation:
        scripture_verdict = "frozen"
    elif scripture_scope_changed:
        scripture_verdict = "scope-changed"
    else:
        scripture_verdict = _roll(SCRIPTURE_METRICS)
    apparatus_verdict = "scope-changed" if apparatus_scope_changed else _roll(APPARATUS_METRICS)

    # only cleanly-comparable domains (same universe) feed the overall improved/regressed call.
    domains = [v for v in (scripture_verdict, apparatus_verdict)
               if v not in ("n/a", "frozen", "scope-changed")]
    if frozen_violation:
        overall = "ERROR: frozen-input invariant violated"
    elif "regressed" in domains and "improved" in domains:
        overall = "mixed"
    elif "regressed" in domains:
        overall = "regressed"
    elif "improved" in domains:
        overall = "improved"
    elif scripture_verdict == "frozen" and apparatus_verdict in ("flat", "n/a"):
        overall = "no empirical change (presentation-only)"
    elif scripture_scope_changed or apparatus_scope_changed:
        overall = "scope-changed (rates over different sets; see notes)"
    else:
        overall = "flat"

    # raw counts carried for display only (never scored): worklist size, open slots, witness/element
    # counts. These are the honest "how much" behind a scope change — e.g. witnesses 0->6.
    def _ctx(n: str) -> dict[str, Any]:
        p, c = prev.get(n), cur.get(n)
        delta = round(c - p, 4) if isinstance(p, (int, float)) and isinstance(c, (int, float)) else None
        return {"prev": p, "cur": c, "delta": delta}
    context = {n: _ctx(n) for n in CONTEXT_METRICS}

    return {
        "prev_version": prev.get("version_label"), "cur_version": cur.get("version_label"),
        "same_verse_input": same_verse_input, "verse_input_sha": cur.get("verse_input_sha"),
        "scripture_scope_changed": scripture_scope_changed,
        "apparatus_scope_changed": apparatus_scope_changed,
        "scripture_verdict": scripture_verdict, "apparatus_verdict": apparatus_verdict,
        "overall": overall, "frozen_violation": frozen_violation, "notes": notes,
        "metrics": per_metric, "context": context,
    }


def summarize(cmp: dict[str, Any]) -> str:
    """One-line human summary from the comparison (empirical, no claims)."""
    def fmt(name: str) -> str:
        e = cmp["metrics"].get(name)
        scored = e is not None
        if e is None:
            e = cmp.get("context", {}).get(name, {})
        p, c, verd = e.get("prev"), e.get("cur"), e.get("verdict")
        if p is None and c is None:
            return f"{name} n/a"
        # scored metrics carry a good/bad arrow; context counts get a neutral direction only.
        arrow = ({"improved": "↑", "regressed": "↓", "flat": "=", "n/a": "·"}.get(verd, "?")
                 if scored else "→")
        return f"{name} {p}→{c} {arrow}"
    keys = ["pass_rate_archaic", "verse_cover_rate", "books_failing_rate", "source_fail_mean",
            "apparatus_witness_rate", "apparatus_witnesses", "apparatus_worklist"]
    return (f"v{cmp['prev_version']} → v{cmp['cur_version']}: {cmp['overall'].upper()} "
            f"(scripture: {cmp['scripture_verdict']}, apparatus: {cmp['apparatus_verdict']}). "
            + " · ".join(fmt(k) for k in keys))


# --------------------------------------------------------------------------------------------------
# Version resolution (manifest snapshot first, else archived HTML)
# --------------------------------------------------------------------------------------------------
def _archived_html(stage: str, version: int) -> Path | None:
    hits = sorted(ARCHIVE.glob(f"reocr-report-{stage}-v{version:03d}-*.html"))
    return hits[-1] if hits else None


def metrics_for_version(version: int, stage: str = "pilot") -> dict[str, Any] | None:
    """Prefer a stored metric snapshot in versions.json; fall back to extracting from the archived HTML."""
    if VERSIONS.exists():
        for h in json.loads(VERSIONS.read_text()).get(stage, {}).get("history", []):
            if h.get("version") == version and h.get("metrics"):
                return h["metrics"]
    html = _archived_html(stage, version)
    return metrics_from_html(html) if html else None


def _cli(argv: list[str]) -> int:
    if len(argv) >= 3 and argv[0] == "--html":
        pm, cm = metrics_from_html(Path(argv[1])), metrics_from_html(Path(argv[2]))
    elif len(argv) >= 2:
        pm, cm = metrics_for_version(int(argv[0])), metrics_for_version(int(argv[1]))
    else:
        print(__doc__)
        return 2
    if not pm or not cm:
        print("could not resolve metrics for one or both versions", file=sys.stderr)
        return 1
    cmp = compare(pm, cm)
    print(summarize(cmp))
    print(json.dumps(cmp, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli(sys.argv[1:]))

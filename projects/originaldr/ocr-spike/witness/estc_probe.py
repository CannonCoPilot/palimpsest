"""Probe the ESTC for the corpus's candidate citation numbers (roadmap R4.1a).

R4.1 is blocked externally, not by method: `estc.bl.uk` now redirects to CERL
and the ESTC beta answers every query with `no such index [estc]`.  The point of
this probe is to keep that distinction sharp.  Three outcomes are possible and
they must never be collapsed:

    INDEX_DOWN   the authority cannot answer -- says nothing about the number
    ABSENT       the authority answered and has no such record -- evidence
    FOUND        the authority answered and resolved it -- promotable

Reporting INDEX_DOWN as ABSENT would turn an outage into a finding, which is the
same failure the leaf classifier made when it printed zero blanks for a witness
whose floor made blanks undetectable.  A tool that cannot tell "no answer" from
"the answer is no" should not be trusted with either.

Usage:  python3 witness/estc_probe.py
Exit:   0 if every candidate resolved, 1 otherwise (including INDEX_DOWN).
"""
import json
import sys
import urllib.error
import urllib.request

# Candidates are LEADS, held here and not in the concordance.  The NT pair is a
# genuine disagreement between secondary sources -- one digit apart -- and is
# exactly what a single source cannot adjudicate, so both are probed.
CANDIDATES = [
    ("1582 Rheims NT (Fogny)", "STC 2884", "S102419"),
    ("1582 Rheims NT (Fogny)", "STC 2884", "S102491"),
    ("1609-10 Douai OT (Kellam)", "STC 2207", "S101944"),
]

ENDPOINT = "https://data.cerl.org/estc/_search?query={}&size=5"
TIMEOUT = 30


def probe(citation):
    """Return (status, detail) for one ESTC citation number."""
    req = urllib.request.Request(ENDPOINT.format(citation),
                                 headers={"Accept": "application/json",
                                          "User-Agent": "OriginalDR-concordance/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            body = r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return "INDEX_DOWN", f"HTTP {e.code}"
    except Exception as e:
        return "INDEX_DOWN", f"{type(e).__name__}: {e}"

    if "no such index" in body:
        return "INDEX_DOWN", "no such index [estc]"
    try:
        d = json.loads(body)
    except ValueError:
        return "INDEX_DOWN", "non-JSON response"
    # A parser rejection is not an empty result set.
    if d.get("valid") == 0:
        return "INDEX_DOWN", "query rejected (valid=0)"
    hits = d.get("hits", d.get("rows", []))
    n = d.get("total", len(hits) if isinstance(hits, list) else 0)
    return ("FOUND", f"{n} record(s)") if n else ("ABSENT", "0 records")


def main():
    print(f"probing ESTC for {len(CANDIDATES)} candidate citation numbers")
    results = []
    for what, stc, estc in CANDIDATES:
        status, detail = probe(estc)
        results.append(status)
        print(f"  {estc:9s} {stc:9s} {status:11s} {detail:28s} {what}")

    down = results.count("INDEX_DOWN")
    if down:
        print(f"\nESTC UNAVAILABLE for {down}/{len(results)} probes -- R4.1 stays BLOCKED.")
        print("This is an outage, not evidence. Do NOT record any candidate as absent,")
        print("and do NOT promote any candidate on secondary sources alone. Fall back to")
        print("the R4.1b authorities (Folger Hamnet, USTC, Bodleian SOLO, Harvard HOLLIS)")
        print("and promote only on agreement between two independent authorities.")
        return 1
    if "ABSENT" in results:
        print("\nSome candidates ABSENT -- that IS evidence. Record the rejection with its date.")
        return 1
    print("\nAll candidates resolved -- R4.1 may proceed to cross-check against OCLC.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

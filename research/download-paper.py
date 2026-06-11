#!/usr/bin/env python3
"""
Robust paper downloader for Palimpsest research corpus.

Usage:
    python3 download-paper.py --list papers-to-download.json
    python3 download-paper.py --doi "10.1038/nmeth.1906" --output genomics --name "Ernst-ChromHMM-2012"

Fallback chain: direct URL → Unpaywall OA → Europe PMC → Semantic Scholar → curl DOI redirect.
Validates downloads are real PDFs. Short filenames. Proper rate limiting.
Uses curl subprocess for reliable redirect handling.
"""

import argparse
import json
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

PAPERS_DIR = Path("/Users/nathanielcannon/Claude/Projects/palimpsest/research/papers")
MIN_PDF_SIZE = 5000
MAX_FILENAME_LEN = 120
CURL_TIMEOUT = 45
RATE_LIMIT_DELAY = 2


def validate_pdf(filepath: Path) -> bool:
    if not filepath.exists():
        return False
    size = filepath.stat().st_size
    if size < MIN_PDF_SIZE:
        print(f"  INVALID: Too small ({size} bytes)")
        return False
    with open(filepath, "rb") as f:
        header = f.read(10)
    if not header.startswith(b"%PDF"):
        if b"<html" in header.lower() or b"<!doc" in header.lower() or header.startswith(b"<"):
            print(f"  INVALID: HTML page, not PDF")
        else:
            print(f"  INVALID: Unknown format (header: {header[:20]!r})")
        return False
    return True


def safe_filename(name: str) -> str:
    name = "".join(c if c.isalnum() or c in "-_." else "-" for c in name)
    while "--" in name:
        name = name.replace("--", "-")
    name = name.strip("-")
    if len(name) > MAX_FILENAME_LEN - 4:
        name = name[:MAX_FILENAME_LEN - 4]
    return name + ".pdf"


def curl_download(url: str, output_path: Path, timeout: int = CURL_TIMEOUT) -> bool:
    """Download using curl — handles redirects, cookies, and headers properly."""
    print(f"  curl: {url[:100]}...")
    try:
        result = subprocess.run(
            ["curl", "-sL", "-f", "--max-time", str(timeout),
             "-H", "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
             "-H", "Accept: application/pdf,*/*",
             "-o", str(output_path),
             url],
            capture_output=True, text=True, timeout=timeout + 10
        )
        if result.returncode != 0:
            print(f"  curl failed (rc={result.returncode}): {result.stderr[:100]}")
            output_path.unlink(missing_ok=True)
            return False
        if validate_pdf(output_path):
            size_kb = output_path.stat().st_size / 1024
            print(f"  OK: {size_kb:.0f} KB → {output_path.name}")
            return True
        output_path.unlink(missing_ok=True)
        return False
    except (subprocess.TimeoutExpired, OSError) as e:
        print(f"  curl error: {e}")
        output_path.unlink(missing_ok=True)
        return False


def api_get_json(url: str, timeout: int = 15) -> dict | None:
    """GET JSON from an API endpoint."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except Exception:
        return None


def try_direct_url(url: str, output_path: Path) -> bool:
    if not url:
        return False
    print(f"  Strategy: Direct URL")
    return curl_download(url, output_path)


def try_unpaywall(doi: str, output_path: Path) -> bool:
    if not doi:
        return False
    print(f"  Strategy: Unpaywall OA lookup")
    data = api_get_json(
        f"https://api.unpaywall.org/v2/{urllib.parse.quote(doi, safe='')}?email=palimpsest-research@proton.me"
    )
    if not data:
        print(f"  Unpaywall: no response")
        return False

    # Try best OA location
    for loc_key in ["best_oa_location"] + [f"oa_locations"]:
        if loc_key == "oa_locations":
            locations = data.get("oa_locations", [])
        else:
            loc = data.get(loc_key)
            locations = [loc] if loc else []
        for loc in locations:
            if not loc:
                continue
            pdf_url = loc.get("url_for_pdf") or ""
            if pdf_url and curl_download(pdf_url, output_path):
                return True
            landing_url = loc.get("url", "")
            if landing_url.endswith(".pdf") and curl_download(landing_url, output_path):
                return True
    print(f"  Unpaywall: no downloadable OA PDF")
    return False


def try_europe_pmc(doi: str, output_path: Path) -> bool:
    if not doi:
        return False
    print(f"  Strategy: Europe PMC")
    data = api_get_json(
        f"https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=DOI:{urllib.parse.quote(doi)}&format=json&resultType=core"
    )
    if not data:
        print(f"  Europe PMC: no response")
        return False
    results = data.get("resultList", {}).get("result", [])
    for r in results:
        pmcid = r.get("pmcid", "")
        if pmcid:
            pmcid_num = pmcid.replace("PMC", "")
            epmc_url = f"https://europepmc.org/backend/ptpmcrender.fcgi?accid=PMC{pmcid_num}&blobtype=pdf"
            if curl_download(epmc_url, output_path):
                return True
    print(f"  Europe PMC: no PMCID or download failed")
    return False


def try_semantic_scholar(title: str, output_path: Path) -> bool:
    if not title:
        return False
    print(f"  Strategy: Semantic Scholar")
    query = urllib.parse.quote(title[:200])
    data = api_get_json(
        f"https://api.semanticscholar.org/graph/v1/paper/search?query={query}&limit=3&fields=title,openAccessPdf"
    )
    if not data:
        print(f"  S2: no response")
        return False
    for paper in data.get("data", []):
        oa_pdf = paper.get("openAccessPdf")
        if oa_pdf and oa_pdf.get("url"):
            if curl_download(oa_pdf["url"], output_path):
                return True
    print(f"  S2: no OA PDF found")
    return False


def try_doi_redirect(doi: str, output_path: Path) -> bool:
    """Follow DOI redirect and see if it lands on a PDF."""
    if not doi:
        return False
    print(f"  Strategy: DOI redirect chase")
    doi_url = f"https://doi.org/{urllib.parse.quote(doi, safe='/:')}"
    # Use curl to follow redirects and check Content-Type
    try:
        result = subprocess.run(
            ["curl", "-sI", "-L", "--max-time", "20",
             "-H", "User-Agent: Mozilla/5.0",
             "-H", "Accept: application/pdf",
             doi_url],
            capture_output=True, text=True, timeout=25
        )
        headers = result.stdout.lower()
        if "content-type: application/pdf" in headers:
            return curl_download(doi_url, output_path)
        # Check if final URL ends in .pdf
        for line in result.stdout.split("\n"):
            if line.lower().startswith("location:"):
                final_url = line.split(":", 1)[1].strip()
                if final_url.endswith(".pdf"):
                    return curl_download(final_url, output_path)
    except Exception as e:
        print(f"  DOI redirect: {e}")
    print(f"  DOI redirect: no PDF endpoint found")
    return False


def try_publisher_direct(doi: str, output_path: Path) -> bool:
    """Try known publisher PDF URL patterns based on DOI prefix."""
    if not doi:
        return False
    print(f"  Strategy: Publisher-direct URL pattern")
    patterns = []

    if "10.1371/" in doi:  # PLoS
        patterns.append(f"https://journals.plos.org/plosbiology/article/file?id={doi}&type=printable")
        patterns.append(f"https://journals.plos.org/plosone/article/file?id={doi}&type=printable")
        patterns.append(f"https://journals.plos.org/plosgenetics/article/file?id={doi}&type=printable")
    if "10.1186/" in doi:  # BioMed Central / Genome Biology
        # BMC DOIs like 10.1186/gb-2004-5-2-r12 → direct PDF
        patterns.append(f"https://doi.org/{doi}")
    if "10.1101/" in doi:  # Genome Research / Cold Spring Harbor
        # Often freely available
        patterns.append(f"https://genome.cshlp.org/content/{doi.split('/')[-1]}.full.pdf")
    if "10.1093/" in doi:  # Oxford (NAR, Bioinformatics, LLC)
        patterns.append(f"https://academic.oup.com/{doi}")

    for url in patterns:
        if curl_download(url, output_path):
            return True
    return False


def download_paper(paper: dict, base_dir: Path) -> dict:
    name = paper["name"]
    subdir = paper.get("subdir", "")
    output_dir = base_dir / subdir if subdir else base_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    filename = safe_filename(name)
    output_path = output_dir / filename

    if output_path.exists() and validate_pdf(output_path):
        print(f"[SKIP] {name} — already on disk")
        return {"name": name, "status": "exists", "filename": filename}

    print(f"\n{'='*60}")
    print(f"  {name}")
    print(f"{'='*60}")

    doi = paper.get("doi", "")
    url = paper.get("url", "")
    arxiv_id = paper.get("arxiv_id", "")
    title = paper.get("title", name)

    strategies = [
        ("direct_url", lambda: try_direct_url(url, output_path)),
        ("arxiv", lambda: curl_download(f"https://arxiv.org/pdf/{arxiv_id}", output_path) if arxiv_id else False),
        ("publisher_direct", lambda: try_publisher_direct(doi, output_path)),
        ("unpaywall", lambda: try_unpaywall(doi, output_path)),
        ("europe_pmc", lambda: try_europe_pmc(doi, output_path)),
        ("semantic_scholar", lambda: try_semantic_scholar(title, output_path)),
        ("doi_redirect", lambda: try_doi_redirect(doi, output_path)),
    ]

    for source_name, strategy in strategies:
        try:
            if strategy():
                return {"name": name, "status": "downloaded", "filename": filename, "source": source_name}
        except Exception as e:
            print(f"  {source_name} crashed: {e}")
        output_path.unlink(missing_ok=True)

    print(f"  ALL STRATEGIES EXHAUSTED — needs Anna's Archive or manual download")
    return {"name": name, "status": "failed", "filename": None, "doi": doi, "title": title}


def main():
    parser = argparse.ArgumentParser(description="Download research papers with failover chain")
    parser.add_argument("--list", help="JSON file with paper list")
    parser.add_argument("--doi", help="Single paper DOI")
    parser.add_argument("--url", help="Direct PDF URL")
    parser.add_argument("--arxiv", help="arXiv ID")
    parser.add_argument("--title", help="Paper title for search")
    parser.add_argument("--output", default="", help="Subdirectory under papers/")
    parser.add_argument("--name", default="paper", help="Short name for filename")
    args = parser.parse_args()

    if args.list:
        with open(args.list) as f:
            papers = json.load(f)

        results = []
        for i, paper in enumerate(papers, 1):
            print(f"\n[{i}/{len(papers)}]")
            result = download_paper(paper, PAPERS_DIR)
            results.append(result)
            time.sleep(RATE_LIMIT_DELAY)

        downloaded = [r for r in results if r["status"] == "downloaded"]
        existed = [r for r in results if r["status"] == "exists"]
        failed = [r for r in results if r["status"] == "failed"]

        print(f"\n{'='*60}")
        print(f"DONE: {len(downloaded)} downloaded, {len(existed)} existed, {len(failed)} failed out of {len(papers)}")
        print(f"{'='*60}")

        if failed:
            print("\nMANUAL ACQUISITION NEEDED:")
            for r in failed:
                print(f"  - {r['name']} (DOI: {r.get('doi', 'N/A')})")

            # Write failed list for Anna's Archive MCP followup
            failed_path = PAPERS_DIR / "failed-downloads.json"
            with open(failed_path, "w") as f:
                json.dump(failed, f, indent=2)
            print(f"\nFailed list saved to {failed_path}")

        results_path = PAPERS_DIR / "download-results.json"
        with open(results_path, "w") as f:
            json.dump(results, f, indent=2)

    else:
        paper = {
            "name": args.name,
            "doi": args.doi or "",
            "arxiv_id": args.arxiv or "",
            "url": args.url or "",
            "title": args.title or args.name,
            "subdir": args.output,
        }
        result = download_paper(paper, PAPERS_DIR)
        print(f"\n{json.dumps(result, indent=2)}")
        sys.exit(0 if result["status"] in ("downloaded", "exists") else 1)


if __name__ == "__main__":
    main()

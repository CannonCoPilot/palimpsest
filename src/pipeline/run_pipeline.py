#!/usr/bin/env python3
"""
Pipeline Orchestrator — run the full extract→clean→segment→signal→encode chain.

Convenience wrapper that calls each stage in sequence, passing JSON between
them in memory (no intermediate files unless --save-intermediates is set).

Usage:
    python run_pipeline.py input.pdf -o output.json
    python run_pipeline.py /path/to/books/ --recursive --level paragraph --clusters 16
    python run_pipeline.py book.epub --save-intermediates --output-dir results/
"""

import argparse
import json
import os
import sys
import time

from text_extractor import extract_file, find_files
from text_cleaner import clean_extraction
from text_segmenter import segment_extraction
from signal_extractor import process_segments
from narrative_encoder import encode_segments
from dataclasses import asdict


def run_pipeline(input_path: str, level: str = "paragraph",
                 window: int = 0, overlap: int = 0,
                 n_clusters: int = 16, use_spacy: bool = True,
                 strip_boilerplate: bool = True,
                 recursive: bool = False,
                 save_intermediates: bool = False,
                 output_dir: str = ".") -> dict:

    t0 = time.time()
    print(f"[1/5] Extracting text from {input_path}...", file=sys.stderr)

    if os.path.isdir(input_path):
        files = find_files(input_path, recursive=recursive)
        if not files:
            raise FileNotFoundError(f"No supported files in {input_path}")
        results = []
        for fp in files:
            try:
                results.append(asdict(extract_file(fp)))
                print(f"  extracted: {fp}", file=sys.stderr)
            except Exception as e:
                print(f"  FAILED: {fp} — {e}", file=sys.stderr)
        data = {"files": results, "total_files": len(results)}
    else:
        data = asdict(extract_file(input_path))

    if save_intermediates:
        _save(data, output_dir, "01_extracted.json")

    print(f"[2/5] Cleaning text...", file=sys.stderr)
    data = clean_extraction(data, strip_boilerplate=strip_boilerplate)
    if save_intermediates:
        _save(data, output_dir, "02_cleaned.json")

    print(f"[3/5] Segmenting at {level} level...", file=sys.stderr)
    data = segment_extraction(data, level, window, overlap)
    if save_intermediates:
        _save(data, output_dir, "03_segmented.json")

    print(f"[4/5] Extracting features...", file=sys.stderr)
    data = process_segments(data, use_spacy=use_spacy)
    if save_intermediates:
        _save(data, output_dir, "04_features.json")

    print(f"[5/5] Encoding narrative alphabet...", file=sys.stderr)
    data = encode_segments(data, n_clusters=n_clusters)
    if save_intermediates:
        _save(data, output_dir, "05_encoded.json")

    elapsed = time.time() - t0
    data["pipeline_elapsed_seconds"] = round(elapsed, 2)
    print(f"Pipeline complete in {elapsed:.1f}s", file=sys.stderr)

    return data


def _save(data: dict, output_dir: str, filename: str):
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"  saved: {path}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description="Run full Palimpsest text pipeline")
    parser.add_argument("input", help="File or directory to process")
    parser.add_argument("-o", "--output", help="Output JSON path (default: stdout)")
    parser.add_argument("--level", choices=["chapter", "paragraph", "sentence"],
                        default="paragraph")
    parser.add_argument("--window", type=int, default=0)
    parser.add_argument("--overlap", type=int, default=0)
    parser.add_argument("--clusters", type=int, default=16)
    parser.add_argument("--no-spacy", action="store_true")
    parser.add_argument("--keep-boilerplate", action="store_true")
    parser.add_argument("--recursive", "-r", action="store_true")
    parser.add_argument("--save-intermediates", action="store_true",
                        help="Save each pipeline stage output")
    parser.add_argument("--output-dir", default=".",
                        help="Directory for intermediate outputs")
    parser.add_argument("--compact", action="store_true")
    args = parser.parse_args()

    result = run_pipeline(
        input_path=args.input,
        level=args.level,
        window=args.window,
        overlap=args.overlap,
        n_clusters=args.clusters,
        use_spacy=not args.no_spacy,
        strip_boilerplate=not args.keep_boilerplate,
        recursive=args.recursive,
        save_intermediates=args.save_intermediates,
        output_dir=args.output_dir,
    )

    indent = None if args.compact else 2
    json_str = json.dumps(result, indent=indent, ensure_ascii=False)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(json_str)
        print(f"Final output: {args.output}", file=sys.stderr)
    else:
        print(json_str)

    return 0


if __name__ == "__main__":
    sys.exit(main())

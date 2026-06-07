#!/usr/bin/env python3
"""
Stage 3: Text Segmenter — split cleaned text into analyzable units.

Produces a hierarchy: document → chapters → paragraphs → sentences,
each with positional metadata (character offsets, indices).

Segmentation strategies:
  - chapter:   regex-based heading detection (CHAPTER, Part, Roman numerals)
  - paragraph: double-newline splitting
  - sentence:  NLTK punkt tokenizer (handles abbreviations, Mr., etc.)
  - window:    sliding window of N sentences with overlap

Input: JSON from text_cleaner (stdin or file)
Output: JSON with segmented text and position metadata

Usage:
    python text_cleaner.py cleaned.json | python text_segmenter.py --level paragraph
    python text_segmenter.py cleaned.json --level sentence --window 5 --overlap 2
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, asdict
from typing import Optional

CHAPTER_PATTERNS = [
    re.compile(r"^(?:CHAPTER|Chapter|PART|Part)\s+[\dIVXLCDMivxlcdm]+\.?\s*$", re.MULTILINE),
    re.compile(r"^(?:CHAPTER|Chapter|PART|Part)\s+[\dIVXLCDMivxlcdm]+[.:]\s+.+$", re.MULTILINE),
    re.compile(r"^\d+\.\s+[A-Z][A-Za-z\s]+$", re.MULTILINE),
    re.compile(r"^[IVXLCDMivxlcdm]+\.\s+[A-Z][A-Za-z\s]+$", re.MULTILINE),
    re.compile(r"^BOOK\s+[\dIVXLCDM]+", re.MULTILINE),
]


@dataclass
class Segment:
    index: int
    level: str
    text: str
    char_offset: int
    char_length: int
    parent_index: Optional[int]
    label: Optional[str]


def segment_sentences(text: str) -> list:
    import nltk
    try:
        tokenizer = nltk.data.load("tokenizers/punkt_tab/english.pickle")
    except LookupError:
        nltk.download("punkt_tab", quiet=True)
        tokenizer = nltk.data.load("tokenizers/punkt_tab/english.pickle")

    spans = tokenizer.span_tokenize(text)
    segments = []
    for i, (start, end) in enumerate(spans):
        sent_text = text[start:end].strip()
        if not sent_text:
            continue
        segments.append(Segment(
            index=i,
            level="sentence",
            text=sent_text,
            char_offset=start,
            char_length=end - start,
            parent_index=None,
            label=None,
        ))
    return segments


def segment_paragraphs(text: str) -> list:
    parts = re.split(r"\n\s*\n", text)
    segments = []
    offset = 0
    idx = 0
    for part in parts:
        stripped = part.strip()
        if not stripped:
            offset += len(part) + 1
            continue
        start = text.find(stripped, offset)
        if start == -1:
            start = offset
        segments.append(Segment(
            index=idx,
            level="paragraph",
            text=stripped,
            char_offset=start,
            char_length=len(stripped),
            parent_index=None,
            label=None,
        ))
        offset = start + len(stripped)
        idx += 1
    return segments


def segment_chapters(text: str) -> list:
    split_points = []
    for pattern in CHAPTER_PATTERNS:
        for match in pattern.finditer(text):
            split_points.append((match.start(), match.group().strip()))

    split_points.sort(key=lambda x: x[0])

    if not split_points:
        return [Segment(
            index=0,
            level="chapter",
            text=text.strip(),
            char_offset=0,
            char_length=len(text),
            parent_index=None,
            label="full_text",
        )]

    segments = []
    if split_points[0][0] > 0:
        preamble = text[:split_points[0][0]].strip()
        if preamble:
            segments.append(Segment(
                index=0,
                level="chapter",
                text=preamble,
                char_offset=0,
                char_length=len(preamble),
                parent_index=None,
                label="preamble",
            ))

    for i, (start, heading) in enumerate(split_points):
        end = split_points[i + 1][0] if i + 1 < len(split_points) else len(text)
        chapter_text = text[start:end].strip()
        segments.append(Segment(
            index=len(segments),
            level="chapter",
            text=chapter_text,
            char_offset=start,
            char_length=end - start,
            parent_index=None,
            label=heading,
        ))

    return segments


def apply_sliding_window(segments: list, window_size: int, overlap: int) -> list:
    if window_size <= 0 or len(segments) <= window_size:
        return segments

    step = max(1, window_size - overlap)
    windowed = []
    idx = 0
    for start in range(0, len(segments), step):
        window = segments[start:start + window_size]
        if not window:
            break
        combined_text = " ".join(s.text for s in window)
        windowed.append(Segment(
            index=idx,
            level="window",
            text=combined_text,
            char_offset=window[0].char_offset,
            char_length=sum(s.char_length for s in window),
            parent_index=None,
            label=f"window_{idx}_sentences_{start}-{start+len(window)-1}",
        ))
        idx += 1

    return windowed


def segment_text(text: str, level: str, window_size: int = 0,
                 overlap: int = 0) -> list:
    if level == "chapter":
        return segment_chapters(text)
    elif level == "paragraph":
        return segment_paragraphs(text)
    elif level == "sentence":
        segments = segment_sentences(text)
        if window_size > 0:
            segments = apply_sliding_window(segments, window_size, overlap)
        return segments
    else:
        raise ValueError(f"Unknown segmentation level: {level}")


def segment_extraction(data: dict, level: str, window_size: int = 0,
                       overlap: int = 0) -> dict:
    def process_chunks(chunks):
        all_segments = []
        for chunk_idx, chunk in enumerate(chunks):
            text = chunk.get("text", "")
            if not text.strip():
                continue
            segments = segment_text(text, level, window_size, overlap)
            for seg in segments:
                seg.parent_index = chunk_idx
            all_segments.extend(segments)
        for i, seg in enumerate(all_segments):
            seg.index = i
        return [asdict(s) for s in all_segments]

    if "files" in data:
        for file_entry in data["files"]:
            file_entry["segments"] = process_chunks(file_entry.get("chunks", []))
            file_entry["segment_count"] = len(file_entry["segments"])
            file_entry["segmentation_level"] = level
    elif "chunks" in data:
        data["segments"] = process_chunks(data.get("chunks", []))
        data["segment_count"] = len(data["segments"])
        data["segmentation_level"] = level

    data["pipeline_stage"] = "segmented"
    return data


def main():
    parser = argparse.ArgumentParser(description="Segment text into analyzable units")
    parser.add_argument("input", nargs="?", help="Input JSON (default: stdin)")
    parser.add_argument("-o", "--output", help="Output JSON path (default: stdout)")
    parser.add_argument("--level", choices=["chapter", "paragraph", "sentence"],
                        default="paragraph", help="Segmentation granularity")
    parser.add_argument("--window", type=int, default=0,
                        help="Sliding window size (sentences only)")
    parser.add_argument("--overlap", type=int, default=0,
                        help="Window overlap (sentences only)")
    parser.add_argument("--compact", action="store_true")
    args = parser.parse_args()

    if args.input:
        with open(args.input, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = json.load(sys.stdin)

    result = segment_extraction(data, args.level, args.window, args.overlap)

    indent = None if args.compact else 2
    json_str = json.dumps(result, indent=indent, ensure_ascii=False)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(json_str)
        print(f"Written to {args.output}", file=sys.stderr)
    else:
        print(json_str)

    return 0


if __name__ == "__main__":
    sys.exit(main())

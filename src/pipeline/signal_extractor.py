#!/usr/bin/env python3
"""
Stage 4: Signal Extractor — compute per-segment linguistic features.

Features extracted per segment:
  - entropy:           Shannon entropy of character/word distribution
  - lexical_diversity:  type-token ratio (unique words / total words)
  - avg_word_length:   mean word length in characters
  - avg_sentence_length: mean sentence length in words
  - dialog_ratio:      fraction of text inside quotation marks
  - question_ratio:    fraction of sentences ending with '?'
  - exclamation_ratio: fraction of sentences ending with '!'
  - ner_density:       named entities per 100 words (requires spacy)
  - pos_distribution:  part-of-speech tag distribution (requires spacy)
  - complexity_score:  composite of sentence length variance + clause depth

Input: JSON from text_segmenter (stdin or file)
Output: JSON with features attached to each segment

Usage:
    python text_segmenter.py segmented.json | python signal_extractor.py
    python signal_extractor.py segmented.json -o features.json --no-spacy
"""

import argparse
import json
import math
import re
import sys
from collections import Counter
from typing import Optional


def shannon_entropy(text: str) -> float:
    if not text:
        return 0.0
    freq = Counter(text.lower())
    total = len(text)
    return -sum((c / total) * math.log2(c / total) for c in freq.values() if c > 0)


def word_entropy(text: str) -> float:
    words = text.lower().split()
    if not words:
        return 0.0
    freq = Counter(words)
    total = len(words)
    return -sum((c / total) * math.log2(c / total) for c in freq.values() if c > 0)


def lexical_diversity(text: str) -> float:
    words = text.lower().split()
    if not words:
        return 0.0
    return len(set(words)) / len(words)


def avg_word_length(text: str) -> float:
    words = re.findall(r"\b\w+\b", text)
    if not words:
        return 0.0
    return sum(len(w) for w in words) / len(words)


def dialog_ratio(text: str) -> float:
    quoted = re.findall(r'"[^"]*"', text) + re.findall(r"'[^']*'", text)
    quoted_chars = sum(len(q) for q in quoted)
    return quoted_chars / len(text) if text else 0.0


def sentence_stats(text: str) -> dict:
    sentences = re.split(r"[.!?]+", text)
    sentences = [s.strip() for s in sentences if s.strip()]
    if not sentences:
        return {
            "avg_sentence_length": 0.0,
            "sentence_length_variance": 0.0,
            "question_ratio": 0.0,
            "exclamation_ratio": 0.0,
            "sentence_count": 0,
        }

    lengths = [len(s.split()) for s in sentences]
    avg_len = sum(lengths) / len(lengths)
    variance = sum((l - avg_len) ** 2 for l in lengths) / len(lengths) if len(lengths) > 1 else 0.0

    endings = re.findall(r"[.!?]", text)
    q_count = endings.count("?")
    e_count = endings.count("!")
    total_endings = len(endings) or 1

    return {
        "avg_sentence_length": round(avg_len, 2),
        "sentence_length_variance": round(variance, 2),
        "question_ratio": round(q_count / total_endings, 4),
        "exclamation_ratio": round(e_count / total_endings, 4),
        "sentence_count": len(sentences),
    }


def extract_basic_features(text: str) -> dict:
    words = text.split()
    word_count = len(words)

    stats = sentence_stats(text)

    return {
        "word_count": word_count,
        "char_count": len(text),
        "char_entropy": round(shannon_entropy(text), 4),
        "word_entropy": round(word_entropy(text), 4),
        "lexical_diversity": round(lexical_diversity(text), 4),
        "avg_word_length": round(avg_word_length(text), 2),
        "dialog_ratio": round(dialog_ratio(text), 4),
        **stats,
    }


def extract_spacy_features(text: str, nlp) -> dict:
    doc = nlp(text[:100000])

    ner_count = len(doc.ents)
    word_count = len([t for t in doc if not t.is_punct and not t.is_space])

    entity_types = Counter(ent.label_ for ent in doc.ents)

    pos_counts = Counter(token.pos_ for token in doc if not token.is_space)
    pos_total = sum(pos_counts.values()) or 1
    pos_distribution = {k: round(v / pos_total, 4) for k, v in pos_counts.most_common(10)}

    noun_chunks = list(doc.noun_chunks)
    avg_np_length = (sum(len(nc) for nc in noun_chunks) / len(noun_chunks)) if noun_chunks else 0.0

    return {
        "ner_density": round((ner_count / word_count) * 100, 4) if word_count else 0.0,
        "ner_count": ner_count,
        "entity_types": dict(entity_types.most_common(10)),
        "pos_distribution": pos_distribution,
        "avg_noun_phrase_length": round(avg_np_length, 2),
        "unique_entity_count": len(set(ent.text.lower() for ent in doc.ents)),
    }


def compute_complexity_score(features: dict) -> float:
    slv = features.get("sentence_length_variance", 0)
    lex_div = features.get("lexical_diversity", 0)
    avg_wl = features.get("avg_word_length", 0)

    slv_norm = min(slv / 100.0, 1.0)
    wl_norm = min(avg_wl / 10.0, 1.0)

    return round(0.4 * slv_norm + 0.3 * lex_div + 0.3 * wl_norm, 4)


def process_segments(data: dict, use_spacy: bool = True) -> dict:
    nlp = None
    if use_spacy:
        try:
            import spacy
            nlp = spacy.load("en_core_web_sm")
        except (ImportError, OSError):
            print("spacy or en_core_web_sm not available, skipping NER/POS features",
                  file=sys.stderr)
            nlp = None

    def enrich_segments(segments):
        for seg in segments:
            text = seg.get("text", "")
            if not text.strip():
                seg["features"] = {}
                continue

            features = extract_basic_features(text)
            if nlp:
                features.update(extract_spacy_features(text, nlp))
            features["complexity_score"] = compute_complexity_score(features)
            seg["features"] = features

    if "files" in data:
        for file_entry in data["files"]:
            enrich_segments(file_entry.get("segments", []))
    elif "segments" in data:
        enrich_segments(data["segments"])

    data["pipeline_stage"] = "features_extracted"
    return data


def main():
    parser = argparse.ArgumentParser(description="Extract linguistic features from segments")
    parser.add_argument("input", nargs="?", help="Input JSON (default: stdin)")
    parser.add_argument("-o", "--output", help="Output JSON path (default: stdout)")
    parser.add_argument("--no-spacy", action="store_true",
                        help="Skip spacy-dependent features (NER, POS)")
    parser.add_argument("--compact", action="store_true")
    args = parser.parse_args()

    if args.input:
        with open(args.input, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = json.load(sys.stdin)

    result = process_segments(data, use_spacy=not args.no_spacy)

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

#!/usr/bin/env python3
"""
Stage 5: Narrative Encoder — encode segments as a "narrative alphabet" sequence.

Inspired by Foldseek's 3Di structural alphabet for protein folds: just as
Foldseek encodes 3D protein structure as a 1D sequence of structural states
enabling fast search, this encoder converts per-segment feature vectors into
a compact alphabet of narrative states.

The narrative alphabet has 16 letters (A-P), each representing a cluster
in feature space. The full text becomes a string like "AABCCFFJJMMPPBA..."
enabling fast structural comparison (edit distance, motif search, alignment)
across texts without re-computing features.

Encoding dimensions (from signal_extractor features):
  - dialog_ratio      → talky (high) vs. descriptive (low)
  - lexical_diversity  → varied vocab vs. repetitive
  - complexity_score   → syntactically complex vs. simple
  - char_entropy       → information-dense vs. sparse
  - question_ratio     → interrogative vs. declarative
  - avg_sentence_length → long sentences vs. short/punchy

Input: JSON from signal_extractor (stdin or file)
Output: JSON with narrative_alphabet string + per-segment letter assignments

Usage:
    python signal_extractor.py features.json | python narrative_encoder.py
    python narrative_encoder.py features.json -o encoded.json --clusters 16
"""

import argparse
import json
import string
import sys
from typing import Optional

import numpy as np

FEATURE_KEYS = [
    "dialog_ratio",
    "lexical_diversity",
    "complexity_score",
    "char_entropy",
    "question_ratio",
    "avg_sentence_length",
]

ALPHABET = string.ascii_uppercase[:26]

CLUSTER_NAMES = {
    "A": "exposition_simple",
    "B": "exposition_complex",
    "C": "dialog_light",
    "D": "dialog_heavy",
    "E": "action_terse",
    "F": "action_detailed",
    "G": "introspection",
    "H": "interrogative",
    "I": "descriptive_lush",
    "J": "descriptive_sparse",
    "K": "transition",
    "L": "climax_build",
    "M": "climax_peak",
    "N": "denouement",
    "O": "meta_commentary",
    "P": "stylistic_break",
}


def extract_feature_vector(features: dict) -> Optional[list]:
    values = []
    for key in FEATURE_KEYS:
        val = features.get(key, None)
        if val is None:
            return None
        values.append(float(val))
    return values


def normalize_vectors(vectors: list) -> np.ndarray:
    arr = np.array(vectors, dtype=float)
    if arr.shape[0] == 0:
        return arr

    mins = arr.min(axis=0)
    maxs = arr.max(axis=0)
    ranges = maxs - mins
    ranges[ranges == 0] = 1.0
    return (arr - mins) / ranges


def quantize_to_alphabet(normalized: np.ndarray, n_clusters: int) -> list:
    if normalized.shape[0] == 0:
        return []

    try:
        from sklearn.cluster import KMeans
        n_clusters = min(n_clusters, normalized.shape[0])
        kmeans = KMeans(n_clusters=n_clusters, n_init=10, random_state=42)
        labels = kmeans.fit_predict(normalized)

        center_norms = np.linalg.norm(kmeans.cluster_centers_, axis=1)
        rank = np.argsort(center_norms)
        label_map = {old: new for new, old in enumerate(rank)}
        return [ALPHABET[label_map[l]] for l in labels]
    except ImportError:
        return quantize_uniform(normalized, n_clusters)


def quantize_uniform(normalized: np.ndarray, n_clusters: int) -> list:
    composite = normalized.mean(axis=1)
    bins = np.linspace(0, 1, n_clusters + 1)
    indices = np.digitize(composite, bins[1:])
    indices = np.clip(indices, 0, n_clusters - 1)
    return [ALPHABET[i] for i in indices]


def encode_segments(data: dict, n_clusters: int = 16) -> dict:
    def process_segment_list(segments):
        vectors = []
        valid_indices = []

        for i, seg in enumerate(segments):
            features = seg.get("features", {})
            vec = extract_feature_vector(features)
            if vec is not None:
                vectors.append(vec)
                valid_indices.append(i)

        if not vectors:
            return "", []

        normalized = normalize_vectors(vectors)
        letters = quantize_to_alphabet(normalized, n_clusters)

        for idx, letter in zip(valid_indices, letters):
            segments[idx]["narrative_letter"] = letter
            segments[idx]["narrative_cluster"] = CLUSTER_NAMES.get(letter, "unknown")

        return "".join(letters), letters

    if "files" in data:
        for file_entry in data["files"]:
            seqs, letters = process_segment_list(file_entry.get("segments", []))
            file_entry["narrative_alphabet"] = seqs
            file_entry["alphabet_length"] = len(seqs)
            file_entry["letter_distribution"] = dict(
                sorted(
                    {l: letters.count(l) for l in set(letters)}.items()
                )
            ) if letters else {}
    elif "segments" in data:
        seqs, letters = process_segment_list(data.get("segments", []))
        data["narrative_alphabet"] = seqs
        data["alphabet_length"] = len(seqs)
        data["letter_distribution"] = dict(
            sorted(
                {l: letters.count(l) for l in set(letters)}.items()
            )
        ) if letters else {}

    data["pipeline_stage"] = "encoded"
    data["encoding_config"] = {
        "n_clusters": n_clusters,
        "feature_keys": FEATURE_KEYS,
        "alphabet_size": min(n_clusters, 26),
    }
    return data


def main():
    parser = argparse.ArgumentParser(
        description="Encode segments as narrative alphabet sequence"
    )
    parser.add_argument("input", nargs="?", help="Input JSON (default: stdin)")
    parser.add_argument("-o", "--output", help="Output JSON path (default: stdout)")
    parser.add_argument("--clusters", type=int, default=16,
                        help="Number of alphabet clusters (default: 16, max: 26)")
    parser.add_argument("--compact", action="store_true")
    args = parser.parse_args()

    if args.clusters > 26:
        print("Max clusters is 26 (A-Z)", file=sys.stderr)
        return 1

    if args.input:
        with open(args.input, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = json.load(sys.stdin)

    result = encode_segments(data, n_clusters=args.clusters)

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

# Palimpsest/src/core/string_matching_analysis.py
"""
String Matching Analysis Module for Palimpsest

Implements the workflow for comparing text chunks using exact and fuzzy string matching.
Handles indexing, chunking, preliminary matching, region identification (TBD),
fuzzy matching, and result storage.
"""

import re
import numpy as np
import pandas as pd
from typing import List, Dict, Tuple, Optional, Any
import logging
from tqdm import tqdm
import random

# TODO: Import necessary fuzzy matching libraries (e.g., python-Levenshtein, py_stringmatching)
# import Levenshtein
# import py_stringmatching

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class StringMatchingAnalysis:
    def __init__(self, text_files: List[str]):
        """
        Initialize the StringMatchingAnalysis.

        Args:
            text_files (List[str]): List of paths to the input text files.
        """
        self.text_files = text_files
        self.texts_data: Dict[str, Dict[str, str]] = {} # {filepath: {index: chunk}}
        self.fast_match_scores: Optional[pd.DataFrame] = None # TBD structure
        self.fuzzy_match_scores: Optional[pd.DataFrame] = None # TBD structure

    def _parse_index(self, line: str) -> Optional[str]:
        """
        Parses a line to find a verse index (e.g., '40:001:001').

        Args:
            line (str): A line from the text file.

        Returns:
            Optional[str]: The found index string, or None.
        """
        match = re.match(r'^(\d+:\d+:\d+)\s', line)
        return match.group(1) if match else None

    def _clean_chunk(self, chunk_lines: List[str]) -> str:
        """
        Cleans a list of lines belonging to a chunk.
        Removes leading index and extra whitespace.

        Args:
            chunk_lines (List[str]): Lines belonging to a single chunk.

        Returns:
            str: The cleaned text chunk.
        """
        if not chunk_lines:
            return ""
        # Remove index from the first line
        first_line = re.sub(r'^(\d+:\d+:\d+)\s+', '', chunk_lines[0])
        # Join lines, strip whitespace from each line and the final result
        cleaned_lines = [first_line.strip()] + [line.strip() for line in chunk_lines[1:]]
        return ' '.join(cleaned_lines).strip()

    def load_and_chunk_texts(self):
        """
        Loads text files, identifies verse indices, and extracts text chunks.
        Populates self.texts_data.
        """
        logger.info("Starting text loading and chunking...")
        verse_pattern = re.compile(r'^(\d+:\d+:\d+)\s')
        book_pattern = re.compile(r'^Book\s+\d+\s+.*') # Pattern for "Book 40 Matthew" lines
        ignore_pattern = re.compile(r'^[*\s]*This eBook was produced by.*', re.IGNORECASE) # Pattern for header/footer text to ignore

        for filepath in self.text_files:
            logger.info(f"Processing file: {filepath}")
            self.texts_data[filepath] = {}
            current_index = None
            current_chunk_lines: List[str] = []

            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    for line in tqdm(f, desc=f"Chunking {filepath}"):
                        # Skip book header lines and producer lines
                        if book_pattern.match(line) or ignore_pattern.match(line):
                            continue

                        new_index = self._parse_index(line)

                        if new_index:
                            # If we have a current chunk, process and store it
                            if current_index and current_chunk_lines:
                                cleaned_chunk = self._clean_chunk(current_chunk_lines)
                                if cleaned_chunk: # Only store non-empty chunks
                                    self.texts_data[filepath][current_index] = cleaned_chunk

                            # Start a new chunk
                            current_index = new_index
                            current_chunk_lines = [line]
                        elif current_index:
                            # Continue the current chunk if it exists
                            current_chunk_lines.append(line)

                    # Store the last chunk after the loop ends
                    if current_index and current_chunk_lines:
                         cleaned_chunk = self._clean_chunk(current_chunk_lines)
                         if cleaned_chunk:
                            self.texts_data[filepath][current_index] = cleaned_chunk

                logger.info(f"Finished chunking {filepath}. Found {len(self.texts_data[filepath])} chunks.")

            except FileNotFoundError:
                logger.error(f"File not found: {filepath}")
            except Exception as e:
                logger.error(f"Error processing file {filepath}: {e}")

        logger.info("Finished loading and chunking all texts.")


    def _mask_and_subsample(self, chunk: str) -> str:
        """
        Applies word length masking and subsampling to a chunk.

        Args:
            chunk (str): The text chunk.

        Returns:
            str: The masked and subsampled chunk string.
        """
        words = chunk.split()
        # Masking: Filter words > 3 characters
        filtered_words = [word for word in words if len(word) > 3]

        # Subsampling: 10% of filtered words, minimum 3
        target_sample_size = max(3, int(len(filtered_words) * 0.1))
        if len(filtered_words) <= target_sample_size:
            subsampled_words = filtered_words
        else:
            subsampled_words = random.sample(filtered_words, target_sample_size)

        return ' '.join(subsampled_words)

    def _exact_match(self, chunk1: str, chunk2: str) -> float:
        """
        Performs a simple exact match comparison.

        Args:
            chunk1 (str): First chunk.
            chunk2 (str): Second chunk.

        Returns:
            float: 1.0 if exact match, 0.0 otherwise.
        """
        return 1.0 if chunk1 == chunk2 else 0.0

    def run_preliminary_matching(self):
        """
        Runs the preliminary fast matching stage (subsampling, masking, exact match).
        Populates self.fast_match_scores.
        """
        logger.info("Starting preliminary fast matching...")
        # This needs to handle text1_sub vs text1, text2_sub vs text2,
        # text1_sub vs text2, text2_sub vs text1 comparisons.
        # The structure of self.fast_match_scores needs careful design.
        # For now, just log a message.
        # TODO: Implement the comparison logic and score storage.

        all_results = [] # List to store comparison results

        text_keys = list(self.texts_data.keys())
        if len(text_keys) < 1:
            logger.warning("No text data loaded for preliminary matching.")
            return

        # Example: Comparing first text against itself and second text (if exists)
        text1_path = text_keys[0]
        text1_chunks = self.texts_data[text1_path]
        text1_indices = list(text1_chunks.keys())

        logger.info(f"Performing preliminary matching for {text1_path}...")

        # --- text1_sub vs text1 ---
        for idx1 in tqdm(text1_indices, desc=f"{text1_path}_sub vs {text1_path}"):
            sub_chunk1 = self._mask_and_subsample(text1_chunks[idx1])
            if not sub_chunk1: continue # Skip if subsampling results in empty string
            for idx2 in text1_indices:
                score = self._exact_match(sub_chunk1, text1_chunks[idx2])
                if score > 0: # Store only matches
                    all_results.append({'text1': text1_path, 'idx1': idx1, 'type1': 'sub',
                                        'text2': text1_path, 'idx2': idx2, 'type2': 'full',
                                        'score': score, 'stage': 'preliminary'})

        # --- text1_sub vs text2 (if text2 exists) ---
        if len(text_keys) > 1:
            text2_path = text_keys[1]
            text2_chunks = self.texts_data[text2_path]
            text2_indices = list(text2_chunks.keys())
            logger.info(f"Performing preliminary matching for {text1_path}_sub vs {text2_path}...")
            for idx1 in tqdm(text1_indices, desc=f"{text1_path}_sub vs {text2_path}"):
                sub_chunk1 = self._mask_and_subsample(text1_chunks[idx1])
                if not sub_chunk1: continue
                for idx2 in text2_indices:
                    score = self._exact_match(sub_chunk1, text2_chunks[idx2])
                    if score > 0:
                        all_results.append({'text1': text1_path, 'idx1': idx1, 'type1': 'sub',
                                            'text2': text2_path, 'idx2': idx2, 'type2': 'full',
                                            'score': score, 'stage': 'preliminary'})

            # --- text2_sub vs text1 ---
            logger.info(f"Performing preliminary matching for {text2_path}_sub vs {text1_path}...")
            for idx1 in tqdm(text2_indices, desc=f"{text2_path}_sub vs {text1_path}"):
                 sub_chunk1 = self._mask_and_subsample(text2_chunks[idx1])
                 if not sub_chunk1: continue
                 for idx2 in text1_indices:
                     score = self._exact_match(sub_chunk1, text1_chunks[idx2])
                     if score > 0:
                         all_results.append({'text1': text2_path, 'idx1': idx1, 'type1': 'sub',
                                             'text2': text1_path, 'idx2': idx2, 'type2': 'full',
                                             'score': score, 'stage': 'preliminary'})

            # --- text2_sub vs text2 ---
            logger.info(f"Performing preliminary matching for {text2_path}_sub vs {text2_path}...")
            for idx1 in tqdm(text2_indices, desc=f"{text2_path}_sub vs {text2_path}"):
                 sub_chunk1 = self._mask_and_subsample(text2_chunks[idx1])
                 if not sub_chunk1: continue
                 for idx2 in text2_indices:
                     score = self._exact_match(sub_chunk1, text2_chunks[idx2])
                     if score > 0:
                         all_results.append({'text1': text2_path, 'idx1': idx1, 'type1': 'sub',
                                             'text2': text2_path, 'idx2': idx2, 'type2': 'full',
                                             'score': score, 'stage': 'preliminary'})


        if all_results:
            self.fast_match_scores = pd.DataFrame(all_results)
            logger.info(f"Preliminary matching complete. Found {len(self.fast_match_scores)} potential matches.")
            # print(self.fast_match_scores.head()) # Optional: print head for verification
        else:
            logger.info("Preliminary matching complete. No potential matches found.")


    def identify_regions(self):
        """
        Identifies regions of high matching based on preliminary scores.
        Requires user interaction via visualization (handled separately).
        """
        logger.info("Region identification step requires user interaction (visualization module).")
        # TODO: This logic will likely be triggered *after* visualization and user input.
        pass

    def _fuzzy_match(self, chunk1: str, chunk2: str, algorithm: str = 'levenshtein') -> float:
        """
        Performs fuzzy matching between two chunks using the specified algorithm.

        Args:
            chunk1 (str): First chunk.
            chunk2 (str): Second chunk.
            algorithm (str): 'levenshtein' or 'jaro_winkler'.

        Returns:
            float: Similarity score (normalized between 0 and 1).
        """
        # TODO: Implement actual fuzzy matching logic using imported libraries
        if algorithm == 'levenshtein':
            # score = Levenshtein.ratio(chunk1, chunk2)
            score = 0.0 # Placeholder
            logger.warning("Levenshtein distance not yet implemented.")
        elif algorithm == 'jaro_winkler':
             # score = py_stringmatching.JaroWinkler().get_sim_score(chunk1, chunk2)
             score = 0.0 # Placeholder
             logger.warning("Jaro-Winkler distance not yet implemented.")
        else:
            logger.error(f"Unknown fuzzy matching algorithm: {algorithm}")
            return 0.0
        return score

    def run_fuzzy_matching(self, regions: Any, algorithm: str):
        """
        Runs the fuzzy matching stage on the identified regions.
        Populates self.fuzzy_match_scores.

        Args:
            regions (Any): Data structure representing the regions to compare. TBD.
            algorithm (str): The fuzzy matching algorithm chosen by the user.
        """
        logger.info(f"Starting fuzzy matching using {algorithm} algorithm...")
        # TODO: Implement fuzzy matching based on identified regions.
        # The structure of self.fuzzy_match_scores needs careful design.
        pass

    def save_results(self, output_dir: str):
        """
        Saves the preliminary and fuzzy matching scores to CSV files.

        Args:
            output_dir (str): The directory to save the results files.
        """
        # TODO: Ensure output_dir exists
        if self.fast_match_scores is not None:
            path = f"{output_dir}/preliminary_match_scores.csv"
            self.fast_match_scores.to_csv(path, index=False)
            logger.info(f"Preliminary match scores saved to {path}")

        if self.fuzzy_match_scores is not None:
            path = f"{output_dir}/fuzzy_match_scores.csv"
            self.fuzzy_match_scores.to_csv(path, index=False)
            logger.info(f"Fuzzy match scores saved to {path}")

    def run_analysis(self, fuzzy_algorithm: str = 'levenshtein', output_dir: str = 'analysis_results'):
        """
        Runs the full string matching analysis pipeline.

        Args:
            fuzzy_algorithm (str): The fuzzy matching algorithm to use ('levenshtein' or 'jaro_winkler').
            output_dir (str): Directory to save results.
        """
        self.load_and_chunk_texts()
        self.run_preliminary_matching()

        # --- Region Identification Placeholder ---
        # In a real scenario, this would involve showing results to the user
        # and getting threshold/region input. For now, we skip this.
        logger.warning("Skipping region identification and fuzzy matching stages as they require user interaction or further implementation.")
        # self.identify_regions() # Placeholder call
        # self.run_fuzzy_matching(regions=None, algorithm=fuzzy_algorithm) # Placeholder call

        # TODO: Create output directory if it doesn't exist
        # import os
        # os.makedirs(output_dir, exist_ok=True)

        self.save_results(output_dir)
        logger.info("String matching analysis pipeline finished.")


# Example Usage (Optional)
if __name__ == "__main__":
    # Create dummy files for testing if needed
    # with open("text1.txt", "w") as f:
    #     f.write("40:001:001 This is the first verse.\n")
    #     f.write("40:001:002 This is the second verse.\n")
    #     f.write("40:001:003 Another verse here.\n")
    # with open("text2.txt", "w") as f:
    #     f.write("41:001:001 This is the first verse of book 41.\n")
    #     f.write("41:001:002 This is the second verse, similar to text1.\n") # Intentional similarity
    #     f.write("41:001:003 A different verse.\n")

    # Example with actual project data paths (adjust as needed)
    text_paths = [
        "Palimpsest/data/gutenberg_cache/8040.txt", # Matthew
        "Palimpsest/data/gutenberg_cache/8041.txt"  # Mark
    ]

    analyzer = StringMatchingAnalysis(text_files=text_paths)
    analyzer.run_analysis(output_dir="Palimpsest/analysis_results/string_matching") # Specify output dir within project
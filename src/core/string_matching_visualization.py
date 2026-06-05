# Palimpsest/src/core/string_matching_visualization.py
"""
String Matching Visualization Module for Palimpsest

Generates heatmaps and Circos plots from string matching analysis results.
"""

import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import numpy as np
import logging
import os
from typing import Optional, Dict, List, Tuple

# TODO: Import pycircos or another Circos library if chosen
# from pycircos import Garc, Gcircle

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class StringMatchingVisualization:
    def __init__(self, results_dir: str):
        """
        Initialize the StringMatchingVisualization.

        Args:
            results_dir (str): Directory containing the analysis result CSV files.
        """
        self.results_dir = results_dir
        self.prelim_scores: Optional[pd.DataFrame] = None
        self.fuzzy_scores: Optional[pd.DataFrame] = None
        self._load_results()

    def _load_results(self):
        """Loads the preliminary and fuzzy match scores from CSV files."""
        prelim_path = os.path.join(self.results_dir, "preliminary_match_scores.csv")
        fuzzy_path = os.path.join(self.results_dir, "fuzzy_match_scores.csv") # Assuming fuzzy scores are also saved

        try:
            if os.path.exists(prelim_path):
                self.prelim_scores = pd.read_csv(prelim_path)
                logger.info(f"Loaded preliminary scores from {prelim_path}")
            else:
                logger.warning(f"Preliminary scores file not found: {prelim_path}")
        except Exception as e:
            logger.error(f"Error loading preliminary scores: {e}")

        try:
            if os.path.exists(fuzzy_path):
                self.fuzzy_scores = pd.read_csv(fuzzy_path)
                logger.info(f"Loaded fuzzy scores from {fuzzy_path}")
            else:
                logger.warning(f"Fuzzy scores file not found: {fuzzy_path}")
        except Exception as e:
            logger.error(f"Error loading fuzzy scores: {e}")

    def _create_pivot_table(self, scores_df: pd.DataFrame, text1_label: str, text2_label: str) -> Optional[pd.DataFrame]:
        """
        Creates a pivot table suitable for heatmap generation from raw scores.
        Assumes scores_df has columns like 'idx1', 'idx2', 'score'.
        Handles potential multiple scores for the same index pair by taking the max.
        """
        if scores_df is None or scores_df.empty:
            logger.warning(f"No scores data available for pivoting ({text1_label} vs {text2_label}).")
            return None

        # Filter for the specific comparison type if necessary (e.g., textA vs textB)
        # This depends on how the scores_df is structured. Assuming it contains pairs.
        # For simplicity, let's assume the input df is already filtered for the desired pair.

        try:
            # Sort indices to ensure consistent order in heatmap
            # Extract numeric parts for sorting if indices are like '40:001:001'
            def sort_key(index_str):
                parts = [int(p) for p in index_str.split(':')]
                return tuple(parts)

            unique_idx1 = sorted(scores_df['idx1'].unique(), key=sort_key)
            unique_idx2 = sorted(scores_df['idx2'].unique(), key=sort_key)

            pivot = scores_df.pivot_table(index='idx1', columns='idx2', values='score', aggfunc='max')

            # Reindex to ensure all indices are present and sorted
            pivot = pivot.reindex(index=unique_idx1, columns=unique_idx2, fill_value=0) # Fill missing pairs with 0

            return pivot

        except KeyError as e:
             logger.error(f"Missing expected columns ('idx1', 'idx2', 'score') for pivot table: {e}")
             return None
        except Exception as e:
            logger.error(f"Error creating pivot table: {e}")
            return None


    def generate_heatmap(self, comparison_type: str, output_path: str):
        """
        Generates a heatmap visualization for a specific comparison type.

        Args:
            comparison_type (str): e.g., "text1_vs_text1", "text1_vs_text2".
                                   Determines which scores (prelim or fuzzy) and which texts to use.
            output_path (str): Path to save the heatmap PNG file.
        """
        logger.info(f"Generating heatmap for {comparison_type}...")

        # Determine which dataframe and text labels to use based on comparison_type
        # This logic needs refinement based on how scores are stored (e.g., columns indicating text source)
        # Placeholder logic:
        scores_to_use = self.prelim_scores # Default to preliminary for now
        text1_label = "Text1"
        text2_label = "Text2"
        title = f"Preliminary Match Scores ({comparison_type})"

        if scores_to_use is None or scores_to_use.empty:
            logger.error(f"No data available to generate heatmap for {comparison_type}.")
            return

        # TODO: Filter scores_to_use based on comparison_type if the DataFrame contains multiple comparisons.
        # Example: filtered_scores = scores_to_use[(scores_to_use['text1'] == 'path/to/text1.txt') & (scores_to_use['text2'] == 'path/to/text2.txt')]

        pivot_table = self._create_pivot_table(scores_to_use, text1_label, text2_label)

        if pivot_table is None or pivot_table.empty:
            logger.error(f"Could not create pivot table for heatmap: {comparison_type}")
            return

        plt.figure(figsize=(12, 10)) # Adjust figure size as needed
        sns.heatmap(pivot_table, cmap="viridis", annot=False) # annot=True can be slow for large matrices
        plt.title(title)
        plt.xlabel(text2_label + " Chunk Index")
        plt.ylabel(text1_label + " Chunk Index")
        plt.xticks(rotation=90)
        plt.yticks(rotation=0)
        plt.tight_layout() # Adjust layout

        try:
            # Ensure output directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            plt.savefig(output_path)
            logger.info(f"Heatmap saved to {output_path}")
        except Exception as e:
            logger.error(f"Error saving heatmap: {e}")
        finally:
            plt.close() # Close the plot to free memory


    def _prepare_circos_data(self, scores_df: pd.DataFrame) -> Optional[Dict]:
        """
        Prepares data structures needed for pycircos or similar library.
        Extracts segments (chapters/books) and links (matches).
        """
        if scores_df is None or scores_df.empty:
            logger.warning("No scores data available for Circos plot.")
            return None

        logger.info("Preparing data for Circos plot...")
        # This requires parsing indices like '40:001:001' to get book/chapter info
        # and structuring links based on scores.

        # Example structure (adapt based on chosen library):
        circos_data = {
            "segments": {}, # { 'arc_id': (start, end, name, color) }
            "links": []     # [ (arc1_id, start1, end1, arc2_id, start2, end2, score) ]
        }

        # --- 1. Define Segments (Arcs) based on Chapters/Books ---
        # Group indices by book and chapter
        chapters = {} # { 'book_id': { 'chapter_id': [indices...] } }
        all_indices = set(scores_df['idx1'].unique()) | set(scores_df['idx2'].unique())

        for index_str in all_indices:
            try:
                book, chapter, _ = map(int, index_str.split(':'))
                book_id = f"book_{book}"
                chapter_id = f"{book_id}_ch_{chapter}"
                if book_id not in chapters:
                    chapters[book_id] = {}
                if chapter_id not in chapters[book_id]:
                    chapters[book_id][chapter_id] = []
                chapters[book_id][chapter_id].append(index_str)
            except ValueError:
                logger.warning(f"Could not parse index for Circos segments: {index_str}")
                continue

        # Create Garc objects (or equivalent) for each chapter
        # This requires assigning lengths/positions - needs careful design
        # Placeholder: Assign arbitrary lengths for now
        current_pos = 0
        segment_length = 1000 # Arbitrary length per chapter segment
        for book_id in sorted(chapters.keys()):
            for chapter_id in sorted(chapters[book_id].keys()):
                 # arc_id = chapter_id
                 # start_pos = current_pos
                 # end_pos = current_pos + segment_length
                 # circos_data["segments"][arc_id] = (start_pos, end_pos, chapter_id, "blue") # Example color
                 # current_pos = end_pos + 50 # Gap between segments
                 logger.warning("Circos segment definition is placeholder.")


        # --- 2. Define Links based on Matches ---
        # Iterate through scores and create links between corresponding segments
        for _, row in scores_df.iterrows():
             idx1 = row['idx1']
             idx2 = row['idx2']
             score = row['score']

             # Find which segments idx1 and idx2 belong to
             # arc1_id = find_segment_for_index(idx1, chapters) # Need helper function
             # arc2_id = find_segment_for_index(idx2, chapters) # Need helper function

             # Calculate positions within the segments (needs mapping logic)
             # pos1_start, pos1_end = calculate_position(idx1, arc1_id, chapters) # Need helper
             # pos2_start, pos2_end = calculate_position(idx2, arc2_id, chapters) # Need helper

             # if arc1_id and arc2_id:
             #     circos_data["links"].append((arc1_id, pos1_start, pos1_end,
             #                                  arc2_id, pos2_start, pos2_end, score))
             logger.warning("Circos link definition is placeholder.")


        logger.info("Finished preparing Circos data (placeholder implementation).")
        return circos_data


    def generate_circos_plot(self, comparison_type: str, output_path: str):
        """
        Generates a Circos-style plot visualization.

        Args:
            comparison_type (str): e.g., "text1_vs_text1", "text1_vs_text2".
            output_path (str): Path to save the Circos plot PNG file.
        """
        logger.info(f"Generating Circos plot for {comparison_type}...")

        # Use final fuzzy scores if available, otherwise preliminary
        scores_to_use = self.fuzzy_scores if self.fuzzy_scores is not None else self.prelim_scores

        if scores_to_use is None or scores_to_use.empty:
            logger.error(f"No score data available for Circos plot: {comparison_type}")
            return

        # TODO: Filter scores based on comparison_type if necessary

        circos_data = self._prepare_circos_data(scores_to_use)

        if not circos_data or not circos_data.get("segments"):
            logger.error("Failed to prepare data for Circos plot.")
            return

        # --- Actual Plotting using pycircos (or chosen library) ---
        logger.warning("Circos plot generation using pycircos is not implemented.")
        # Example structure (replace with actual pycircos calls):
        # circle = Gcircle()
        # # Add arcs (segments)
        # for arc_id, (start, end, name, color) in circos_data["segments"].items():
        #     arc = Garc(arc_id=arc_id, size=end-start, ...)
        #     circle.add_garc(arc)
        # circle.set_garcs()
        #
        # # Add links
        # for link_data in circos_data["links"]:
        #     circle.add_link(link_data)
        #
        # # Render and save
        # circle.figure.savefig(output_path)

        logger.info(f"Circos plot generation skipped (implementation pending).")


    def generate_visualizations(self, output_dir: str):
        """
        Generates all visualizations (heatmap, circos) for available comparisons.

        Args:
            output_dir (str): Directory to save the visualization files.
        """
        os.makedirs(output_dir, exist_ok=True)

        # Determine available comparisons based on loaded data
        # TODO: Add logic to figure out which comparisons (e.g., text1v1, text1v2) are possible

        # Example: Generate for text1 vs text1 and text1 vs text2 if data exists
        comparison1v1 = "text1_vs_text1"
        comparison1v2 = "text1_vs_text2"

        heatmap_path_1v1 = os.path.join(output_dir, f"heatmap_{comparison1v1}.png")
        circos_path_1v1 = os.path.join(output_dir, f"circos_{comparison1v1}.png")
        heatmap_path_1v2 = os.path.join(output_dir, f"heatmap_{comparison1v2}.png")
        circos_path_1v2 = os.path.join(output_dir, f"circos_{comparison1v2}.png")

        # Generate Heatmaps (using preliminary scores for now)
        self.generate_heatmap(comparison1v1, heatmap_path_1v1)
        self.generate_heatmap(comparison1v2, heatmap_path_1v2)

        # Generate Circos Plots (using best available scores)
        self.generate_circos_plot(comparison1v1, circos_path_1v1)
        self.generate_circos_plot(comparison1v2, circos_path_1v2)

        logger.info(f"Visualizations saved to {output_dir}")


# Example Usage (Optional)
if __name__ == "__main__":
    # Assumes analysis results are in this directory
    results_directory = "Palimpsest/analysis_results/string_matching"
    output_visualization_dir = "Palimpsest/analysis_results/string_matching/visualizations"

    # Check if results directory exists
    if not os.path.isdir(results_directory):
        logger.error(f"Results directory not found: {results_directory}")
        logger.error("Please run the string_matching_analysis.py script first.")
    else:
        visualizer = StringMatchingVisualization(results_dir=results_directory)
        visualizer.generate_visualizations(output_dir=output_visualization_dir)
# String Matching Module Refactor Plan

**Goal:** Refactor the string matching module to create separate analysis and visualization scripts, implementing a verse-based chunking and fuzzy matching workflow.

**1. `string_matching_analysis.py`**

*   **Goal:** Implement the analysis workflow for string matching.

*   **Steps:**

    *   **1.1. Indexing and Chunking (Verse-based):**
        *   Read text file.
        *   Use regex `\d+:\d+:\d+` to identify verse indices.
        *   Extract text chunks associated with each verse index.
        *   Discard header lines and pre-text content.
        *   Output: Dictionary of verse indices to text chunks.

    *   **1.2. Preliminary Fast Matching (Subsampling and Masking):**
        *   **Algorithm:** Simple character-by-character exact string matching.
        *   **Masking:** Apply word-length filter (<=3 characters) *before* subsampling.
        *   **Subsampling:** Subsample down to 10% of words, with a minimum of three words per chunk.
        *   **Store match scores from this stage.**
        *   Perform "all vs all" comparisons: text1\_sub vs text1, text2\_sub vs text2, text1\_sub vs text2, text2\_sub vs text1.

    *   **1.3. Region Identification:**
        *   Provide a heatmap graph and a histogram of the chunk-match scores to the user.
        *   The user sets a cutoff threshold for "matching" based on the histogram.
        *   Identify regions that pass the threshold.

    *   **1.4. Filtered All vs All Analysis (Fuzzy Matching):**
        *   **Algorithms (User Choice):**
            *   Levenshtein Distance
            *   Jaro-Winkler Distance
        *   Apply chosen algorithm for fuzzy matching within identified regions.

    *   **1.5. Result Storage:**
        *   Store fuzzy match scores in a NumPy matrix.
        *   Save matrix to CSV.

    *   **1.6. Analysis Progress Tracker:**
        *   Use `tqdm` for progress bars for each stage.

**2. `string_matching_visualization.py`**

*   **Goal:** Generate visualizations for string matching results.

*   **Steps:**

    *   **2.1. Heatmap Visualization:**
        *   Library: `seaborn`.
        *   Load CSV matrix using `pandas`.
        *   Generate and customize heatmap.
 	    *   The heatmap will show all matches that are the result of stage one simple matching by using one color scheme, and matches that result from the refined fussy matching by using another color scheme.
        *   Save as PNG.

    *   **2.2. Circos-Style Visualization:**
        *   Include Circos-style graphs for self vs self and textA vs textB comparisons.
        *   Use final-stage match scores to create ribbon connections between matched chunks.
        *   The user can select portions of the 'circle' which is divided by 'chapter'.
        *   When selecting a 'chapter' then those chunks within that chapter are highlighted on the 'circle' and the ribbons that represent the matches of those chunks with other chunks are highlighted.
        *   There will be a heatmap figure and a circos-style figure for each intra-textual (self v self comparison), and each intertextial (self v other) comparison.

**3. Update `Palimpsest/docs/p0_prototype_roadmap_proposal.md`**

*   Reflect the refactoring in the roadmap document.

**Analysis Workflow Diagram:**

```mermaid
graph LR
    A[Start] --> B{Read Text File};
    B --> C{Parse Indices (Regex)};
    C --> D{Extract Verse Chunks};
    D --> E{Mask Short Words};
    E --> F{Fast Match (Subsample)};
    F --> G{Store Fast Match Scores};
    G --> H{Identify High-Match Regions};
    H --> I{User Sets Threshold};
    I --> J{Fuzzy Match (Levenshtein/Jaro-Winkler)};
    J --> K{Store Fuzzy Match Scores};
    K --> L{Store Score Matrix (CSV)};
    L --> M[End Analysis Script];
    M --> N[Start Vis Script];
    N --> O{Load Score Matrix (Pandas)};
    O --> P{Generate Heatmap (Seaborn)};
    P --> Q{Generate Circos Plot};
    Q --> R[End Vis Script];
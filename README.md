# Palimpsest: Literary Text Analysis System

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)
![Development Status](https://img.shields.io/badge/status-alpha-red)

Palimpsest is an advanced computational system for analyzing and discovering connections between literary texts. The project leverages both syntactic pattern matching and semantic analysis to reveal relationships and influences across literary works.

## Overview

Palimpsest combines multiple text analysis techniques to identify both explicit and implicit connections between texts:

- **String Matching**: Identifies shared phrases, repeated patterns, and syntactic similarities between texts using suffix arrays, LSH, and other advanced string matching algorithms.
  
- **Semantic Analysis**: Discovers thematic and conceptual connections between texts through semantic embeddings, topic modeling, and contextual understanding.

- **Integrated Analysis**: Combines both approaches to provide a comprehensive understanding of textual relationships that goes beyond simple quotation or influence detection.

## Project Structure

```
palimpsest/
├── docs/                    # Project documentation
│   ├── palimpsest_prd.md          # Product Requirements Document
│   ├── palimpsest_system_design.md # System Design Document
│   ├── palimpsest_core_modules_specification.md # Module Specifications
│   ├── palimpsest_implementation_plan.md # Implementation Planning
│   └── diagrams/              # Visual documentation
│       ├── palimpsest_class_diagram.mermaid
│       └── palimpsest_sequence_diagram.mermaid
├── research/                # Research notebooks and documents
│   ├── string_semantic_matching_research.ipynb
│   └── syntactic_structural_plot_analysis_research.ipynb
├── src/                     # Source code
│   ├── core/                # Core analysis modules
│   │   ├── string_matching_module.py
│   │   └── semantic_analysis_module.py
│   └── main.py             # Application entry point
├── tests/                   # Unit tests
│   ├── test_string_matching.py
│   └── test_semantic_analysis.py
├── README.md               # This file
├── requirements.txt        # Python dependencies
├── setup.py               # Package installation configuration
├── install.sh             # Installation script
└── run_tests.sh           # Test execution script
```

## Installation

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)

### Quick Install

```bash
# Clone the repository
git clone https://github.com/yourusername/palimpsest.git
cd palimpsest

# Run the installation script
./install.sh
```

### Manual Installation

```bash
# Create and activate a virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install Palimpsest in development mode
pip install -e .
```

## Usage

### Basic Example

```python
from src.core.string_matching_module import StringMatchingModule
from src.core.semantic_analysis_module import SemanticAnalysisModule
from src.main import PalimpsestAnalyzer

# Initialize analyzer
analyzer = PalimpsestAnalyzer()

# Load texts
source_text = "Your source text here..."
target_texts = ["First comparison text", "Second comparison text"]

# Analyze relationships
results = analyzer.analyze_texts(source_text, target_texts)

# Generate report
analyzer.generate_report(results, "report.txt")
```

### Command Line Usage

```bash
# Basic usage pattern
python -m src.main source_file.txt target_file1.txt target_file2.txt --output report.txt
```

## Running Tests

```bash
# Using the test script
./run_tests.sh

# Or manually
python -m unittest discover -s tests
```

## Future Developments

- Advanced visualization of text relationships
- Web interface for interactive exploration
- Support for multiple languages and specialized corpora
- Integration with literary databases
- Enhanced machine learning models for deeper semantic understanding

## Contributing

Contributions to Palimpsest are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

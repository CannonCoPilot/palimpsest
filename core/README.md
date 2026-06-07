# Palimpsest Core

Python backend for the Palimpsest computational literary analysis platform. Provides text ingestion, multi-track feature extraction, and a FastAPI server for the browser frontend.

## Installation

```bash
cd core
pip install -e ".[dev]"
python -m spacy download en_core_web_lg
```

## Usage

```bash
palimpsest ingest <file.txt>
palimpsest analyze projects/<text-id>/
palimpsest serve projects/
```

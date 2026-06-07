"""
Palimpsest text processing pipeline.

Five-stage pipeline: extract → clean → segment → signal → encode.
Each stage is a standalone CLI tool that reads from stdin/files and writes
structured JSON, composable via pipes or the orchestrator.
"""

#!/bin/bash

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Run tests
echo "Running Palimpsest tests..."
python -m unittest discover -s tests

echo "Tests completed!"

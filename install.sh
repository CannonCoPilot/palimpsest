#!/bin/bash

echo "Installing Palimpsest..."

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install requirements
echo "Installing required packages..."
pip install -r requirements.txt

# Install package in development mode
echo "Installing Palimpsest in development mode..."
pip install -e .

echo "Installation complete!"

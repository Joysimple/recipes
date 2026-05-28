#!/bin/bash
# Format and lint Python code using Ruff
set -e

VENV_BIN="./venv/bin"

if [ ! -d "venv" ]; then
    echo "Error: Virtual environment not found. Please run 'python3 -m venv venv' first."
    exit 1
fi

echo "Formatting code..."
$VENV_BIN/ruff format generate_pdf.py

echo "Linting and fixing code..."
$VENV_BIN/ruff check --fix generate_pdf.py

echo "Success! Code is PEP 8 compliant."

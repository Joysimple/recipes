#!/bin/bash
# Format and lint Python code using Ruff
set -e

VENV_BIN="./venv/bin"

if [ ! -d "venv" ]; then
    echo "Error: Virtual environment not found. Please run 'python3 -m venv venv' first."
    exit 1
fi

echo "Formatting Python code..."
$VENV_BIN/ruff format .

echo "Linting and fixing Python code..."
$VENV_BIN/ruff check --fix .

echo "Formatting Markdown recipes..."
# Format all .md files recursively, excluding venv
find . -name "*.md" -not -path "./venv/*" -exec $VENV_BIN/mdformat --number {} +

echo "Success! Code and recipes are PEP 8 and Markdown compliant."

#!/bin/bash
set -e

VENV_BIN="./venv/bin"

if [ ! -d "venv" ]; then
    echo "Error: Virtual environment not found. Please run 'python3 -m venv venv' first."
    exit 1
fi

echo "Running style and formatting checks via pre-commit..."
# Force pre-commit to run ruff, ruff-format, and mdformat (with its plugins) on all files
$VENV_BIN/pre-commit run --all-files

echo "Success! Code and recipes are PEP 8 and Markdown compliant."


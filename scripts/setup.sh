#!/usr/bin/env bash

# Python setup
echo "Creating venv"
python3 -m venv .venv
echo "Installing deps"
./.venv/bin/python -m pip install -r requirements.txt

# Rust setup
./scripts/build.sh

echo "To run, run ./scripts/run.sh"

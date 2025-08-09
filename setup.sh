#!/usr/bin/env bash

echo "Creating venv"
python3 -m venv venv
echo "Installing deps"
./venv/bin/python -m pip install -r requirements.txt

echo "To run, run ./run.sh"

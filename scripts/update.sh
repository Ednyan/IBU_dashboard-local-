#!/usr/bin/env bash

# Update repo
git pull origin main
# Update python modules
./.venv/bin/python -m pip install --upgrade -r requirements.txt
# Rebuild custom rust modules
./scripts/build.sh
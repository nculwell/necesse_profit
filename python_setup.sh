#!/bin/bash
cd "$( dirname "$BASH_SOURCE[0]" )"
[ ! -e .venv ] && echo "Installing python in .venv" && python -m venv ./.venv
echo "Installing required packages"
.venv/bin/python -m pip install -r requirements.txt


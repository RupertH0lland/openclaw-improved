#!/bin/bash
# AI Orchestrator - One-command setup: install, configure (if needed), run
set -e
cd "$(dirname "$0")/.."
echo "AI Orchestrator - Installing..."
python3 -m venv .venv 2>/dev/null || true
. .venv/bin/activate
pip install -r requirements.txt -q
echo "Starting..."
exec python main.py

#!/bin/bash
set -e

if [ -d "venv" ]; then
    source venv/bin/activate
fi

export DEMO_MODE=simulation

echo "Starting Zero Trust Agents Demo (simulation mode)..."
echo "Open http://localhost:8000 in your browser"
echo ""

uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

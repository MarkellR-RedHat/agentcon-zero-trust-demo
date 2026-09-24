#!/bin/bash
set -e

echo "Setting up Zero Trust Agents Demo..."

if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

echo "Activating virtual environment..."
source venv/bin/activate

echo "Installing dependencies..."
pip install -r requirements.txt

if [ ! -f ".env" ]; then
    echo "Creating .env from example..."
    cp .env.example .env
fi

echo ""
echo "Setup complete!"
echo "Run: ./scripts/run-local.sh"

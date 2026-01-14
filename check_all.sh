#!/bin/bash
set -e

# Ensure we are in the repo root
cd "$(dirname "$0")"

# Setup/Activate venv
if [ ! -d ".venv" ]; then
    echo "📦 Creating .venv..."
    python3 -m venv .venv
fi
source .venv/bin/activate

# Install dependencies if black is missing or we just created venv
if ! command -v black &> /dev/null; then
    echo "⬇️  Installing dependencies..."
    pip install --upgrade pip
    pip install black
    pip install -e text_aggregator_tool
    pip install -e command_reloader_tool
fi

# Run Black
echo "🎨 Running Black..."
black .

# Run Tests
echo ""
echo "🧪 Running Tests..."

echo ">> Shell Commands Tests"
python3 -m unittest shell_commands/tests/test_shell_tools.py

echo ">> Command Reloader Tests"
python3 -m unittest discover command_reloader_tool/tests

echo ">> Text Aggregator Tests"
python3 -m unittest discover text_aggregator_tool/tests

echo ""
echo "✅ All Checks Passed!"

#!/bin/bash
# Dev Tools Setup Script

set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SHELL_RC=""

# Detect Shell
if [ -n "$BASH_VERSION" ]; then
    SHELL_RC="$HOME/.bashrc"
elif [ -n "$ZSH_VERSION" ]; then
    SHELL_RC="$HOME/.zshrc"
fi

echo "🔧 Setting up Dev Tools in $REPO_ROOT..."

# 1. Setup Shell Commands (Sourcing)
echo ""
echo "--- Shell Commands ---"
INIT_SCRIPT="$REPO_ROOT/shell_commands/init.sh"
SOURCE_CMD="source $INIT_SCRIPT"

if [ -f "$SHELL_RC" ]; then
    if grep -Fq "$INIT_SCRIPT" "$SHELL_RC"; then
        echo "✅ Shell commands already sourced in $SHELL_RC"
    else
        read -p "❓ Add shell commands to $SHELL_RC? [y/N] " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            echo "" >> "$SHELL_RC"
            echo "# Dev Tools" >> "$SHELL_RC"
            echo "$SOURCE_CMD" >> "$SHELL_RC"
            echo "✅ Added to $SHELL_RC"
        else
            echo "Skipping rc update."
        fi
    fi
else
    echo "⚠️  Could not detect .bashrc or .zshrc. Manual setup needed:"
    echo "   Add 'source $INIT_SCRIPT' to your config."
fi

# 2. Setup Text Aggregator (Dependencies)
echo ""
echo "--- Text Aggregator ---"
TA_DIR="$REPO_ROOT/text_aggregator_tool"
if [ ! -d "$TA_DIR/venv" ]; then
    echo "Dependencies need to be installed (pyperclip)."
    read -p "❓ Create venv and install dependencies for Text Aggregator? [y/N] " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        python3 -m venv "$TA_DIR/venv"
        "$TA_DIR/venv/bin/pip" install -U pip
        "$TA_DIR/venv/bin/pip" install -e "$TA_DIR"
        echo "✅ Text Aggregator installed in venv."
    fi
else
    echo "✅ venv exists for Text Aggregator."
fi

# 3. Setup Command Reloader
echo ""
echo "--- Command Reloader ---"
# No deps really, but good to check
echo "✅ Command Reloader ready (no external dependencies)."

echo ""
echo "🎉 Setup complete!"
echo "If you updated your RC file, run: source $SHELL_RC"

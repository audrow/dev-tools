#!/bin/bash

# Python Tools Aliases
# wrappers to run the python tools in this repo without global installation.

# Resolve the root directory of the repo relative to this script
# $SCRIPT_DIR is defined in init.sh
if [ -z "$SCRIPT_DIR" ]; then
    # Fallback if sourced directly
    if [ -n "$BASH_VERSION" ]; then
        SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    elif [ -n "$ZSH_VERSION" ]; then
        SCRIPT_DIR="$(cd "$(dirname "${(%):-%N}")" && pwd)"
    fi
fi

DEV_TOOLS_ROOT="$(dirname "$SCRIPT_DIR")"

# --- Text Aggregator ---
function text-aggregator() {
    local TOOL_DIR="$DEV_TOOLS_ROOT/text_aggregator_tool"
    local VENV_PYTHON="$TOOL_DIR/venv/bin/python3"

    if [ -f "$VENV_PYTHON" ]; then
        # Use venv if available
        PYTHONPATH="$TOOL_DIR" "$VENV_PYTHON" -m text_aggregator.aggregator "$@"
    else
        # Fallback to system python (might fail if dependencies missing)
        PYTHONPATH="$TOOL_DIR" python3 -m text_aggregator.aggregator "$@"
    fi
}

# --- Command Reloader ---
function command-reloader() {
    local TOOL_DIR="$DEV_TOOLS_ROOT/command_reloader_tool"
    # No dependencies, system python is usually fine
    PYTHONPATH="$TOOL_DIR" python3 -m command_reloader.reloader "$@"
}
function cr() { command-reloader "$@"; }

function command-trigger-listener() {
    local TOOL_DIR="$DEV_TOOLS_ROOT/command_reloader_tool"
    PYTHONPATH="$TOOL_DIR" python3 -m command_reloader.listener "$@"
}

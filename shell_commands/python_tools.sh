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

# Helper to find the best python interpreter
# Usage: _get_venv_python <tool_dir>
_get_venv_python() {
    local tool_dir="$1"
    local tool_venv="$tool_dir/venv/bin/python3"
    local tool_pip="$tool_dir/venv/bin/pip"
    local root_venv="$DEV_TOOLS_ROOT/.venv/bin/python3"

    # 1. Prefer tool-specific venv if it seems complete (has pip)
    if [ -f "$tool_venv" ] && [ -f "$tool_pip" ]; then
        echo "$tool_venv"
        return 0
    fi

    # 2. Fallback to root repo venv
    if [ -f "$root_venv" ]; then
        echo "$root_venv"
        return 0
    fi

    # 3. Fallback to system python
    echo "python3"
}

# --- Text Aggregator ---
function text-aggregator() {
    local TOOL_DIR="$DEV_TOOLS_ROOT/text_aggregator_tool"
    local PYTHON_CMD=$(_get_venv_python "$TOOL_DIR")

    PYTHONPATH="$TOOL_DIR" "$PYTHON_CMD" -m text_aggregator.aggregator "$@"
}

# --- Command Reloader ---
function command-reloader() {
    local TOOL_DIR="$DEV_TOOLS_ROOT/command_reloader_tool"
    local PYTHON_CMD=$(_get_venv_python "$TOOL_DIR")
    
    PYTHONPATH="$TOOL_DIR" "$PYTHON_CMD" -m command_reloader.reloader "$@"
}
function cr() { command-reloader "$@"; }

function command-trigger-listener() {
    local TOOL_DIR="$DEV_TOOLS_ROOT/command_reloader_tool"
    local PYTHON_CMD=$(_get_venv_python "$TOOL_DIR")
    
    PYTHONPATH="$TOOL_DIR" "$PYTHON_CMD" -m command_reloader.listener "$@"
}

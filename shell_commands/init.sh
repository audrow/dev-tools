#!/bin/bash

# Function to get the current script directory
get_script_dir() {
    if [ -n "$BASH_VERSION" ]; then
        echo "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    elif [ -n "$ZSH_VERSION" ]; then
        echo "$(cd "$(dirname "${(%):-%x}")" && pwd)"
    else
        # Fallback
        echo "$(cd "$(dirname "$0")" && pwd)"
    fi
}

SCRIPT_DIR=$(get_script_dir)

# Source specific tool files
if [ -f "$SCRIPT_DIR/git_aliases.sh" ]; then
    source "$SCRIPT_DIR/git_aliases.sh"
fi

if [ -f "$SCRIPT_DIR/git_worktree_tools.sh" ]; then
    source "$SCRIPT_DIR/git_worktree_tools.sh"
fi

if [ -f "$SCRIPT_DIR/git_workflow_tools.sh" ]; then
    source "$SCRIPT_DIR/git_workflow_tools.sh"
fi

if [ -f "$SCRIPT_DIR/python_tools.sh" ]; then
    source "$SCRIPT_DIR/python_tools.sh"
fi

# We can add more files here later or loop through *.sh
# for tool in "$SCRIPT_DIR"/*.sh; do
#   [ "$tool" != "$SCRIPT_DIR/init.sh" ] && source "$tool"
# done

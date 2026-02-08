#!/bin/bash

# Defensive sourcing of utils.sh
if ! command -v copy_to_clipboard >/dev/null 2>&1; then
    if [ -n "$BASH_SOURCE" ]; then
        _DEFENSIVE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    elif [ -n "$ZSH_VERSION" ]; then
        _DEFENSIVE_DIR="$(cd "$(dirname "${(%):-%x}")" && pwd)"
    else
        _DEFENSIVE_DIR="$(cd "$(dirname "$0")" && pwd)"
    fi
    if [ -f "$_DEFENSIVE_DIR/../utils.sh" ]; then
        source "$_DEFENSIVE_DIR/../utils.sh"
    fi
fi

# GEXEC: Run a command on files changed in the working tree (vs HEAD)
# Usage: gexec <command> [args...]
# Example: gexec pnpm exec prettier --write
gexec() {
    if [ $# -eq 0 ]; then
        echo "Usage: gexec <command> [args...]"
        return 1
    fi

    # Check if inside a git repo
    if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
        echo "❌ Not in a git repository."
        return 1
    fi

    # Check if there are changes first (to avoid running command on empty input)
    if git diff --quiet HEAD; then
        echo "ℹ️  No changed files found (Working Tree vs HEAD)."
        return 0
    fi
    
    local file_count=$(git diff --name-only --diff-filter=d HEAD | wc -l | tr -d ' ')
    echo "🏃 Running command on $file_count file(s)..."
    
    # Use -z for null-terminated strings and -0 for xargs to handle spaces safely
    git diff -z --name-only --diff-filter=d HEAD | xargs -0 "$@"
}

# GEXEC_MB: Run a command on files changed against merge-base
# Usage: gexec_mb [-b base] [-t target] <command> [args...]
# Example: gexec_mb eslint
#          gexec_mb -b main -t feature -- ls -l
gexec_mb() {
    local base_branch=""
    local target_ref=""
    local cmd=()
    
    while [[ "$#" -gt 0 ]]; do
        case $1 in
            -b|--base) base_branch="$2"; shift ;;
            -t|--target) target_ref="$2"; shift ;;
            --) shift; cmd+=("$@"); break ;;
            *) cmd+=("$1") ;;
        esac
        shift
    done

    if [ ${#cmd[@]} -eq 0 ]; then
        echo "Usage: gexec_mb [-b base] [-t target] <command> [args...]"
        return 1
    fi

    # Defaults
    if [ -z "$base_branch" ]; then base_branch="main"; fi
    if [ -z "$target_ref" ]; then target_ref="HEAD"; fi

    # Defensive check for gmb (defined in sync.sh)
    if ! command -v gmb >/dev/null 2>&1; then
        echo "❌ 'gmb' command not found. Is sync.sh sourced?"
        return 1
    fi

    local merge_base=$(gmb "$base_branch" "$target_ref")
    if [ -z "$merge_base" ]; then
        echo "❌ Could not find merge-base."
        return 1
    fi
    
    local files_check=$(git diff --name-only --diff-filter=d "$merge_base" "$target_ref")
    if [ -z "$files_check" ]; then
        echo "ℹ️  No changed files found ($base_branch...$target_ref)."
        return 0
    fi
    
    local file_count=$(echo "$files_check" | wc -l | tr -d ' ')
    echo "🏃 Running command on $file_count file(s)..."
    git diff -z --name-only --diff-filter=d "$merge_base" "$target_ref" | xargs -0 "${cmd[@]}"
}

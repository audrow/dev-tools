#!/bin/bash

# Directory where git diffs will be saved
GDIFF_DIR="${GDIFF_DIR:-$HOME/Downloads}"

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

# GDIFF_OUT: Diff and save to a file
# Usage: gdiff_out [git diff arguments]
gdiff_out() {
    local current_branch=$(git branch --show-current)
    if [ -z "$current_branch" ]; then
        current_branch="HEAD"
    fi
    # Replace / with -
    local safe_branch="${current_branch//\//-}"
    local outfile="${GDIFF_DIR}/git-${safe_branch}.diff"

    git diff "$@" > "$outfile"
    echo "💾 Diff saved to $outfile"
}

# Helper: Generate diff, output to file or clipboard
# Usage: _generate_and_copy_diff <base_ref> <target_ref> [diff_args...]
_generate_and_copy_diff() {
    local base_ref="$1"
    local target_ref="$2"
    shift 2
    local diff_args=("$@")

    local diff_output
    if [ -n "$base_ref" ]; then
        diff_output=$(git diff -U9999 "${diff_args[@]}" "$base_ref" "$target_ref")
    else
        # For gdo with single target or no target
        diff_output=$(git diff -U9999 "${diff_args[@]}" "$target_ref")
    fi

    if [ -z "$diff_output" ]; then
        echo "✅ No differences found."
        return 0
    fi

    # Determine safe filename
    local current_branch=$(git branch --show-current)
    if [ -z "$current_branch" ]; then current_branch="HEAD"; fi
    
    # Use target_ref name if valid and not HEAD, otherwise current branch
    local name_ref="$target_ref"
    if [ "$name_ref" == "HEAD" ] || [ -z "$name_ref" ]; then
        name_ref="$current_branch"
    fi
    local safe_name="${name_ref//\//-}"
    local outfile="${GDIFF_DIR}/git-${safe_name}.diff"

    # Check if user wants to force file output or stdin is not interactive
    # Uses caller's variable name (GDMBO_FORCE_FILE / GDO_FORCE_FILE) dynamically if needed, 
    # but here we can just use a generic override or check if any variable ends in _FORCE_FILE=1
    # For simplicity, we assume the caller handles the variable check or we check both?
    # Let's check a generic FORCE_FILE or specific ones.
    local force_file="${FORCE_FILE:-0}"
    if [ "${GDMBO_FORCE_FILE:-0}" = "1" ] || [ "${GDO_FORCE_FILE:-0}" = "1" ]; then
        force_file=1
    fi

    if [ "$force_file" = "1" ] || [ ! -t 0 ]; then
        echo "$diff_output" > "$outfile"
        echo "💾 Diff saved to $outfile"
        return 0
    fi

    # Try clipboard first
    if copy_to_clipboard "$diff_output"; then
        echo "📋 Diff copied to clipboard"
        return 0
    else
        # Fallback to file if clipboard fails
        echo "⚠️  Clipboard not available, saving to file instead..."
        echo "$diff_output" > "$outfile"
        echo "💾 Diff saved to $outfile"
        return 0
    fi
}

# GDMBO: Diff from merge-base with origin/main (or auto-detected base)
# Usage: gdmbo [target_ref] [base_branch]
gdmbo() {
    local target_ref="${1:-HEAD}"
    local base_branch="${2:-}"

    # Resolve HEAD to actual branch name for better logging/detection if possible
    if [ "$target_ref" = "HEAD" ]; then
        local current=$(git branch --show-current)
        if [ -n "$current" ]; then
            target_ref="$current"
        fi
    fi

    # 1. Auto-Detect Base if not provided
    if [ -z "$base_branch" ]; then
        echo "🔍 Auto-detecting base branch for '$target_ref'..."
        # Defensive check for detect_base_branch (defined in sync.sh)
        if command -v detect_base_branch >/dev/null 2>&1; then
            base_branch=$(detect_base_branch "$target_ref")
        else
            echo "⚠️  'detect_base_branch' not found (is sync.sh sourced?). Defaulting to 'main'."
            base_branch="main"
        fi
        echo "   -> Detected base: '$base_branch'"
    fi

    # 2. Verify we found a valid base
    if ! git rev-parse --verify "$base_branch" >/dev/null 2>&1; then
        # Try origin/$base_branch
        if git rev-parse --verify "origin/$base_branch" >/dev/null 2>&1; then
             base_branch="origin/$base_branch"
        else
            echo "❌ Base branch '$base_branch' not found. Please specify it manually."
            return 1
        fi
    fi

    # 3. Calculate Merge Base
    local merge_base
    merge_base=$(git merge-base "$base_branch" "$target_ref")

    if [ -z "$merge_base" ]; then
        echo "❌ Could not find common ancestor between $base_branch and $target_ref."
        return 1
    fi

    # 4. Generate Diff
    FORCE_FILE="${GDMBO_FORCE_FILE:-0}" _generate_and_copy_diff "$merge_base" "$target_ref"
}

# GDO: Diff against a target (or current unstaged changes)
# Usage: gdo [target] (e.g. gdo, gdo HEAD^, gdo main)
gdo() {
    local diff_args=("$@")
    
    local diff_output
    diff_output=$(git diff -U9999 "${diff_args[@]}")

    if [ -z "$diff_output" ]; then
        echo "✅ No differences found."
        return 0
    fi
    
    # Use the first arg as the "name" for the file, or current branch
    local name_ref="${1:-}"
    local current_branch=$(git branch --show-current)
    if [ -z "$current_branch" ]; then current_branch="HEAD"; fi
    if [ -z "$name_ref" ]; then name_ref="$current_branch"; fi

    local safe_name="${name_ref//\//-}"
    local outfile="${GDIFF_DIR}/git-${safe_name}.diff"

    # Check force file
    if [ "${GDO_FORCE_FILE:-0}" = "1" ] || [ ! -t 0 ]; then
        echo "$diff_output" > "$outfile"
        echo "💾 Diff saved to $outfile"
        return 0
    fi

    # Try clipboard first
    if copy_to_clipboard "$diff_output"; then
        echo "📋 Diff copied to clipboard"
        return 0
    else
        echo "⚠️  Clipboard not available, saving to file instead..."
        echo "$diff_output" > "$outfile"
        echo "💾 Diff saved to $outfile"
        return 0
    fi
}

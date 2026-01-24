#!/bin/bash

# Directory where git diffs will be saved
GDIFF_DIR="${GDIFF_DIR:-$HOME/Downloads}"

# GUPDATE: Update current branch with main (or specified branch)
# Fetches origin and merges the base branch into the current branch.
# Usage: gupdate [base_branch]
gupdate() {
    local base_branch="${1:-main}"
    local current_branch=$(git branch --show-current)

    # Check if we are on a branch
    if [ -z "$current_branch" ]; then
        echo "❌ Not currently on a branch."
        return 1
    fi

    # 1. Fetch
    echo "🔄 Fetching origin..."
    git fetch origin --quiet

    # Determine remote branch to merge
    local remote_ref="origin/$base_branch"
    
    # Check if remote branch exists
    if ! git rev-parse --verify "$remote_ref" &>/dev/null; then
         # Try master if main was default and missing
         if [ "$base_branch" == "main" ] && git rev-parse --verify "origin/master" &>/dev/null; then
             remote_ref="origin/master"
             echo "⚠️ 'origin/main' not found, using 'origin/master'."
         else
             echo "❌ Remote branch '$remote_ref' not found."
             return 1
         fi
    fi

    echo "🚀 Merging '$remote_ref' into '$current_branch'..."
    if git merge "$remote_ref"; then
        echo "✅ Merge successful."
    else
        echo "❌ Merge failed (conflict?)."
        echo "   Fix conflicts and commit the result."
        return 1
    fi
}

# GMB: Find merge-base between origin/main (or master) and HEAD
# Usage: gmb [base_branch]
gmb() {
    local base_branch="${1:-main}"
    local remote_ref="origin/$base_branch"

    if ! git rev-parse --verify "$remote_ref" &>/dev/null; then
        if [ "$base_branch" == "main" ] && git rev-parse --verify "origin/master" &>/dev/null; then
            remote_ref="origin/master"
        fi
    fi

    git merge-base "$remote_ref" HEAD
}

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

# GDMBO: Diff from merge-base with origin/main and copy to clipboard (or save to file)
# By default, copies to clipboard. If clipboard fails, saves to ~/Downloads/git-<branch>.diff
# Set GDMBO_FORCE_FILE=1 to always write to file instead of clipboard
# Usage: gdmbo [base_branch]
gdmbo() {
    local base=$(gmb "$1")
    if [ -z "$base" ]; then
        echo "❌ Could not find merge-base."
        return 1
    fi

    local current_branch=$(git branch --show-current)
    if [ -z "$current_branch" ]; then
        current_branch="HEAD"
    fi
    local safe_branch="${current_branch//\//-}"
    local outfile="${GDIFF_DIR}/git-${safe_branch}.diff"

    # Check if user wants to force file output or stdin is not interactive
    if [ "${GDMBO_FORCE_FILE:-0}" = "1" ] || [ ! -t 0 ]; then
        git diff "$base" > "$outfile"
        echo "💾 Diff saved to $outfile"
        return 0
    fi

    # Try clipboard first
    local diff_output=$(git diff "$base")
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
    
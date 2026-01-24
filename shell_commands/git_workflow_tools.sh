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

# GSKIP: Mark files as skip-worktree (ignore local changes)
# Usage: gskip [file...]
# If no files provided, uses fzf to select from tracked files
gskip() {
    if ! command -v fzf &> /dev/null; then
        echo "❌ Error: fzf is not installed. Please install fzf to use interactive selection."
        echo "   Alternatively, provide file paths as arguments: gskip <file1> [file2] ..."
        return 1
    fi

    local files=("$@")

    if [ ${#files[@]} -eq 0 ]; then
        # Interactive selection with fzf
        echo "🔍 Select files to ignore (TAB to multi-select, ENTER to confirm):"
        local selected
        selected=$(git ls-files | fzf --multi --height 40% --layout=reverse --header="Select files to skip-worktree")
        
        if [ -z "$selected" ]; then
            echo "ℹ️  No files selected."
            return 0
        fi
        
        # Convert newline-separated to array
        while IFS= read -r file; do
            files+=("$file")
        done <<< "$selected"
    fi

    local count=0
    for file in "${files[@]}"; do
        if [ -f "$file" ]; then
            git update-index --skip-worktree "$file"
            echo "🙈 Skipping: $file"
            ((count++))
        else
            echo "⚠️  File not found: $file"
        fi
    done

    if [ $count -gt 0 ]; then
        echo "✅ Marked $count file(s) as skip-worktree."
        echo "💡 Use 'gunskip' to re-enable tracking."
    fi
}

# GUNSKIP: Remove skip-worktree flag (re-enable tracking)
# Usage: gunskip [file...]
# If no files provided, uses fzf to select from currently skipped files
gunskip() {
    # Get list of skip-worktree files
    local skipped_files
    skipped_files=$(git ls-files -v | grep '^S ' | cut -c3-)

    if [ -z "$skipped_files" ]; then
        echo "ℹ️  No files are currently marked as skip-worktree."
        return 0
    fi

    local files=("$@")

    if [ ${#files[@]} -eq 0 ]; then
        if ! command -v fzf &> /dev/null; then
            echo "❌ Error: fzf is not installed. Please install fzf to use interactive selection."
            echo "   Alternatively, provide file paths as arguments: gunskip <file1> [file2] ..."
            echo ""
            echo "Currently skipped files:"
            echo "$skipped_files" | sed 's/^/   /'
            return 1
        fi

        # Interactive selection with fzf
        echo "🔍 Select files to re-enable tracking (TAB to multi-select, ENTER to confirm):"
        local selected
        selected=$(echo "$skipped_files" | fzf --multi --height 40% --layout=reverse --header="Select files to unskip")
        
        if [ -z "$selected" ]; then
            echo "ℹ️  No files selected."
            return 0
        fi
        
        # Convert newline-separated to array
        while IFS= read -r file; do
            files+=("$file")
        done <<< "$selected"
    fi

    local count=0
    for file in "${files[@]}"; do
        git update-index --no-skip-worktree "$file" 2>/dev/null
        if [ $? -eq 0 ]; then
            echo "👁️  Tracking: $file"
            ((count++))
        else
            echo "⚠️  Could not unskip: $file"
        fi
    done

    if [ $count -gt 0 ]; then
        echo "✅ Re-enabled tracking for $count file(s)."
    fi
}

# GSKIPPED: List all files marked as skip-worktree
# Usage: gskipped
gskipped() {
    local skipped_files
    skipped_files=$(git ls-files -v | grep '^S ' | cut -c3-)

    if [ -z "$skipped_files" ]; then
        echo "ℹ️  No files are currently marked as skip-worktree."
        return 0
    fi

    echo "🙈 Files with skip-worktree flag:"
    echo "$skipped_files" | sed 's/^/   /'
    echo ""
    echo "💡 Use 'gunskip' to re-enable tracking."
}
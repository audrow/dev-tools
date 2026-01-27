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
    if git merge --no-edit "$remote_ref"; then
        echo "✅ Merge successful."

        echo "⬆️ Pushing changes to origin..."
        if git push origin "$current_branch"; then
            echo "✅ Push successful."
        else
            echo "❌ Push failed."
            return 1
        fi
    else
        echo "❌ Merge failed (conflict?)."
        echo "   Fix conflicts and commit the result."
        return 1
    fi
}

# GMB: Find merge-base between origin/main (or master) and HEAD (or specified target)
# Usage: gmb [base_branch] [target_ref]
gmb() {
    local base_branch="${1:-main}"
    local target_ref="${2:-HEAD}"
    local remote_ref="origin/$base_branch"

    if ! git rev-parse --verify "$remote_ref" &>/dev/null; then
        if [ "$base_branch" == "main" ] && git rev-parse --verify "origin/master" &>/dev/null; then
            remote_ref="origin/master"
        fi
    fi

    git merge-base "$remote_ref" "$target_ref"
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
# Usage: gdmbo [base_branch] [target_ref]
#        gdmbo -t <target_ref> [base_branch]
gdmbo() {
    local base_branch=""
    local target_ref=""
    
    while [[ "$#" -gt 0 ]]; do
        case $1 in
            -t|--target) target_ref="$2"; shift ;;
            *) 
                if [ -z "$base_branch" ]; then
                    base_branch="$1"
                else
                    target_ref="$1"
                fi
                ;;
        esac
        shift
    done

    # Defaults
    if [ -z "$base_branch" ]; then base_branch="main"; fi
    if [ -z "$target_ref" ]; then target_ref="HEAD"; fi

    local base=$(gmb "$base_branch" "$target_ref")
    if [ -z "$base" ]; then
        echo "❌ Could not find merge-base."
        return 1
    fi

    local safe_branch
    if [ "$target_ref" == "HEAD" ]; then
        local current_branch=$(git branch --show-current)
        if [ -z "$current_branch" ]; then
            current_branch="HEAD"
        fi
        safe_branch="${current_branch//\//-}"
    else
        safe_branch="${target_ref//\//-}"
    fi
    
    local outfile="${GDIFF_DIR}/git-${safe_branch}.diff"

    # Check if user wants to force file output or stdin is not interactive
    if [ "${GDMBO_FORCE_FILE:-0}" = "1" ] || [ ! -t 0 ]; then
        git diff -U9999 "$base" "$target_ref" > "$outfile"
        echo "💾 Diff saved to $outfile"
        return 0
    fi

    # Try clipboard first
    local diff_output=$(git diff -U9999 "$base" "$target_ref")
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

# GDO: Diff against a target (or current unstaged changes) and copy to clipboard (or save to file)
# By default, copies to clipboard. If clipboard fails, saves to ~/Downloads/git-<branch>.diff
# Set GDO_FORCE_FILE=1 to always write to file instead of clipboard
# Usage: gdo [target] (e.g. gdo, gdo HEAD^, gdo main)
gdo() {
    local diff_args="$@"

    local current_branch=$(git branch --show-current)
    if [ -z "$current_branch" ]; then
        current_branch="HEAD"
    fi
    local safe_branch="${current_branch//\//-}"
    local outfile="${GDIFF_DIR}/git-${safe_branch}.diff"

    # Check if user wants to force file output or stdin is not interactive
    if [ "${GDO_FORCE_FILE:-0}" = "1" ] || [ ! -t 0 ]; then
        git diff -U9999 $diff_args > "$outfile"
        echo "💾 Diff saved to $outfile"
        return 0
    fi

    # Try clipboard first
    local diff_output=$(git diff -U9999 $diff_args)
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
    local files=("$@")

    if [ ${#files[@]} -eq 0 ]; then
        if ! command -v fzf &> /dev/null; then
            echo "❌ Error: fzf is not installed. Please install fzf to use interactive selection."
            echo "   Alternatively, provide file paths as arguments: gskip <file1> [file2] ..."
            return 1
        fi
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
        # Ensure the path is tracked in the git index rather than just existing on disk
        if git ls-files --error-unmatch -- "$file" >/dev/null 2>&1; then
            if git update-index --skip-worktree -- "$file"; then
                echo "🙈 Skipping: $file"
                ((count++))
            else
                echo "⚠️  Failed to mark as skip-worktree (git update-index error): $file"
            fi
        else
            if [ -e "$file" ]; then
                echo "⚠️  Path is not tracked by git (cannot set skip-worktree): $file"
            else
                echo "⚠️  Path not found in working tree or git index: $file"
            fi
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

    local files=$(git diff --name-only --diff-filter=d HEAD)
    if [ -z "$files" ]; then
        echo "ℹ️  No changed files found (Working Tree vs HEAD)."
        return 0
    fi
    
    echo "🏃 Running command on $(echo "$files" | wc -l | tr -d ' ') file(s)..."
    echo "$files" | xargs "$@"
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

    local merge_base=$(gmb "$base_branch" "$target_ref")
    if [ -z "$merge_base" ]; then
        echo "❌ Could not find merge-base."
        return 1
    fi
    
    local files=$(git diff --name-only --diff-filter=d "$merge_base" "$target_ref")
    if [ -z "$files" ]; then
        echo "ℹ️  No changed files found ($base_branch...$target_ref)."
        return 0
    fi
    
    echo "🏃 Running command on $(echo "$files" | wc -l | tr -d ' ') file(s)..."
    echo "$files" | xargs "${cmd[@]}"
}
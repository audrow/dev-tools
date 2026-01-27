#!/bin/bash

# Directory where git diffs will be saved
GDIFF_DIR="${GDIFF_DIR:-$HOME/Downloads}"

# Defensive sourcing of utils.sh
# Check if utils.sh functions are available, otherwise try to source it
if ! command -v copy_to_clipboard >/dev/null 2>&1; then
    # Try to find utils.sh relative to this script
    if [ -n "$BASH_SOURCE" ]; then
        SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    elif [ -n "$ZSH_VERSION" ]; then
        SCRIPT_DIR="$(cd "$(dirname "${(%):-%x}")" && pwd)"
    else
        SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
    fi

    if [ -f "$SCRIPT_DIR/utils.sh" ]; then
        source "$SCRIPT_DIR/utils.sh"
    else
        # Fallback if utils.sh is missing to prevent crashes
        copy_to_clipboard() {
            echo "⚠️  Clipboard tool missing. Outputting here:"
            echo "$1"
        }
    fi
fi

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

# GMB: Find merge-base between origin/main (or master/auto-detected) and HEAD (or specified target)
# Usage: gmb [base_branch] [target_ref]
gmb() {
    local base_branch="$1"
    local target_ref="${2:-HEAD}"

    # If no base provided, try to auto-detect
    if [ -z "$base_branch" ]; then
        base_branch=$(detect_base_branch "$target_ref")
    fi

    local remote_ref="origin/$base_branch"

    if ! git rev-parse --verify "$remote_ref" &>/dev/null; then
        # Check if base_branch itself exists (local)
        if git rev-parse --verify "$base_branch" &>/dev/null; then
             remote_ref="$base_branch"
        elif [ "$base_branch" == "main" ] && git rev-parse --verify "origin/master" &>/dev/null; then
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

# Helper: Auto-detect the most likely parent branch
detect_base_branch() {
    local target_branch="$1"
    local candidates=("main" "master" "develop" "next" "trunk")
    local best_base=""
    local best_timestamp=0

    for candidate in "${candidates[@]}"; do
        # Check if candidate exists locally or remotely (try local first, then origin/)
        local candidate_ref="$candidate"
        if ! git rev-parse --verify "$candidate_ref" >/dev/null 2>&1; then
             candidate_ref="origin/$candidate"
             if ! git rev-parse --verify "$candidate_ref" >/dev/null 2>&1; then
                 continue
             fi
        fi

        # Find the common ancestor (merge-base)
        local mb
        mb=$(git merge-base "$candidate_ref" "$target_branch" 2>/dev/null)
        
        if [ -n "$mb" ]; then
            # Get the commit time of the merge-base (Unix timestamp)
            local ts
            ts=$(git show -s --format=%ct "$mb")
            
            # We want the candidate with the MOST RECENT common ancestor
            if [ "$ts" -gt "$best_timestamp" ]; then
                best_timestamp=$ts
                best_base=$candidate_ref
            fi
        fi
    done

    # Fallback to 'main' if detection fails completely
    echo "${best_base:-main}"
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
        base_branch=$(detect_base_branch "$target_ref")
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
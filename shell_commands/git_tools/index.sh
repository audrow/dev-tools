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

# GSKIP: Mark files as skip-worktree (ignore local changes) OR ignore untracked files locally
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
        # 1. Tracked file: Use skip-worktree
        if git ls-files --error-unmatch -- "$file" >/dev/null 2>&1; then
            if git update-index --skip-worktree -- "$file"; then
                echo "🙈 Skipping (worktree): $file"
                ((count++))
            else
                echo "⚠️  Failed to mark as skip-worktree (git update-index error): $file"
            fi
        
        # 2. Directory with tracked files: Skip all inside
        elif [ -d "$file" ] && [ -n "$(git ls-files -- "$file")" ]; then
             echo "📂 Directory '$file' contains tracked files. Skipping them..."
             local subfiles=$(git ls-files -- "$file")
             local subcount=0
             while IFS= read -r sub; do
                 if git update-index --skip-worktree -- "$sub"; then
                     ((subcount++))
                 fi
             done <<< "$subfiles"
             echo "🙈 Skipped $subcount tracked files inside '$file'."
             ((count++))

        # 3. Untracked file/directory: Ignore locally (.git/info/exclude)
        elif [ -e "$file" ]; then
             if git check-ignore -q "$file"; then
                 echo "ℹ️  $file is already ignored."
             else
                 local exclude_file="$(git rev-parse --git-common-dir)/info/exclude"
                 # Check if already present to avoid duplicates (exact match)
                 if ! grep -Fxq "$file" "$exclude_file" >/dev/null 2>&1; then
                     echo "$file" >> "$exclude_file"
                     echo "🙈 Ignored (added to .git/info/exclude): $file"
                     ((count++))
                 else
                     echo "ℹ️  $file already in .git/info/exclude."
                 fi
             fi
        else
             echo "⚠️  Path not found: $file"
        fi
    done

    if [ $count -gt 0 ]; then
        echo "✅ Processed $count item(s)."
        echo "💡 Use 'gunskip' to re-enable tracking or un-ignore."
    fi
}

# GUNSKIP: Remove skip-worktree flag (re-enable tracking) or remove from local ignore
# Usage: gunskip [file...]
# If no files provided, uses fzf to select from currently skipped files
gunskip() {
    # Get list of skip-worktree files
    local skipped_files
    skipped_files=$(git ls-files -v | grep '^S ' | cut -c3-)

    if [ $# -eq 0 ]; then
        if [ -z "$skipped_files" ]; then
            echo "ℹ️  No files are currently marked as skip-worktree."
            # Could list ignored files too, but let's keep it simple for interactive mode
            return 0
        fi

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
        local files=()
        while IFS= read -r file; do
            files+=("$file")
        done <<< "$selected"
    else
        local files=("$@")
    fi

    local count=0
    for file in "${files[@]}"; do
        local handled=false

        # 1. Try unskipping (if tracked)
        if git ls-files --error-unmatch -- "$file" >/dev/null 2>&1; then
            git update-index --no-skip-worktree "$file" 2>/dev/null
            if [ $? -eq 0 ]; then
                echo "👁️  Tracking (worktree): $file"
                handled=true
                ((count++))
            fi
        elif [ -d "$file" ] && [ -n "$(git ls-files -- "$file")" ]; then
             local subfiles=$(git ls-files -- "$file")
             while IFS= read -r sub; do
                 git update-index --no-skip-worktree "$sub" 2>/dev/null
             done <<< "$subfiles"
             echo "👁️  Re-enabled tracking for files in: $file"
             handled=true
             ((count++))
        fi

        # 2. Try removing from .git/info/exclude
        local exclude_file="$(git rev-parse --git-common-dir)/info/exclude"
        if [ -f "$exclude_file" ] && grep -Fxq "$file" "$exclude_file"; then
             # Remove exact line. grep -v returns 1 if result is empty (all lines removed), so avoid &&
             grep -Fxv "$file" "$exclude_file" > "$exclude_file.tmp"
             mv "$exclude_file.tmp" "$exclude_file"
             echo "👁️  Un-ignored (removed from .git/info/exclude): $file"
             handled=true
             ((count++))
        fi

        if [ "$handled" = false ]; then
            echo "⚠️  Could not unskip/unignore: $file (not skipped or ignored)"
        fi
    done

    if [ $count -gt 0 ]; then
        echo "✅ Processed $count item(s)."
    fi
}

# GSKIPPED: List files marked as skip-worktree or locally ignored
# Usage: gskipped
gskipped() {
    # Check if inside a git repo
    if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
        echo "❌ Not in a git repository."
        return 1
    fi

    local list_mode=false
    local filter_worktree=false
    local filter_ignored=false

    # Parse args
    for arg in "$@"; do
        case $arg in
            --list|-l) list_mode=true ;;
            --worktree|-w) filter_worktree=true ;;
            --ignored|-i) filter_ignored=true ;;
        esac
    done

    # If neither specific filter is set, show both
    if [ "$filter_worktree" = false ] && [ "$filter_ignored" = false ]; then
        filter_worktree=true
        filter_ignored=true
    fi

    local found_any=false

    # 1. Skip-worktree files
    if [ "$filter_worktree" = true ]; then
        local skipped_files
        skipped_files=$(git ls-files -v | grep '^S ' | cut -c3-)

        if [ -n "$skipped_files" ]; then
            if [ "$list_mode" = true ]; then
                echo "$skipped_files"
            else
                echo "🙈 Files with skip-worktree flag:"
                echo "$skipped_files" | sed 's/^/   /'
                echo ""
            fi
            found_any=true
        fi
    fi

    # 2. Locally ignored files (.git/info/exclude)
    if [ "$filter_ignored" = true ]; then
        local exclude_file="$(git rev-parse --git-common-dir)/info/exclude"
        if [ -f "$exclude_file" ] && [ -s "$exclude_file" ]; then
            # Filter out comments and empty lines
            local ignored_files
            ignored_files=$(grep -vE '^\s*#|^\s*$' "$exclude_file")
            
            if [ -n "$ignored_files" ]; then
                if [ "$list_mode" = true ]; then
                    echo "$ignored_files"
                else
                    echo "🙈 Files locally ignored (.git/info/exclude):"
                    echo "$ignored_files" | sed 's/^/   /'
                    echo ""
                fi
                found_any=true
            fi
        fi
    fi

    if [ "$found_any" = false ]; then
        if [ "$list_mode" = false ]; then
            echo "ℹ️  No files are currently marked as skip-worktree or locally ignored."
        fi
        return 0
    fi

    if [ "$list_mode" = false ]; then
        echo "💡 Use 'gunskip' to re-enable tracking or un-ignore."
    fi
}

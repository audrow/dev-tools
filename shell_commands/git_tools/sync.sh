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

    # 1. Handle skipped files
    # Get list of skipped files (worktree only)
    local skipped_files=""
    if command -v gskipped >/dev/null 2>&1; then
        skipped_files=$(gskipped --list --worktree)
    else
        # Fallback if gskipped is not available
        if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
            skipped_files=$(git ls-files -v | grep '^S ' | cut -c3-)
        fi
    fi
    local stashed=0

    if [ -n "$skipped_files" ]; then
        echo "🙈 Found skipped files. Unskipping temporarily..."
        while IFS= read -r file; do
            if [ -n "$file" ]; then
                if command -v gunskip >/dev/null 2>&1; then
                    gunskip "$file"
                else
                    # Fallback
                    if git ls-files --error-unmatch -- "$file" >/dev/null 2>&1; then
                        git update-index --no-skip-worktree "$file"
                        echo "👁️  Tracking (worktree): $file"
                    fi
                fi
            fi
        done <<< "$skipped_files"
    fi

    # 2. Check for local changes (now that skipped files are visible)
    # We stash if there are ANY changes to avoid merge conflicts
    if ! git diff-index --quiet HEAD --; then
        echo "📦 Stashing local changes..."
        # We assume git stash works. If it fails, we might be in trouble, but standard flow.
        git stash push -m "gupdate_temp_stash"
        stashed=1
    fi

    # 3. Fetch
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
             # Restore state before exiting
             if [ $stashed -eq 1 ]; then
                 echo "🔙 Restoring stash..."
                 git stash pop
             fi
             if [ -n "$skipped_files" ]; then
                 echo "🙈 Re-skipping files..."
                 while IFS= read -r file; do
                     if [ -n "$file" ]; then
                         if command -v gskip >/dev/null 2>&1; then
                             gskip "$file"
                         else
                             # Fallback
                             if git ls-files --error-unmatch -- "$file" >/dev/null 2>&1; then
                                 git update-index --skip-worktree -- "$file"
                                 echo "🙈 Skipping (worktree): $file"
                             fi
                         fi
                     fi
                 done <<< "$skipped_files"
             fi
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
            # We continue to restore state even if push fails
        fi
        
        # 4. Restore State
        if [ $stashed -eq 1 ]; then
            echo "📦 Popping stash..."
            if git stash pop; then
                echo "✅ Stash restored."
            else
                echo "⚠️  Stash pop had conflicts? Resolve them manually."
                # If stash pop fails, files might be partially restored or conflict markers.
                # We should still try to reskip if possible, or maybe it's too risky?
                # Usually stash pop conflict leaves files in working tree.
                # We'll attempt reskip anyway as it just flags them.
            fi
        fi

        if [ -n "$skipped_files" ]; then
            echo "🙈 Re-skipping files..."
            while IFS= read -r file; do
                if [ -n "$file" ]; then
                    if command -v gskip >/dev/null 2>&1; then
                        gskip "$file"
                    else
                        # Fallback
                        if git ls-files --error-unmatch -- "$file" >/dev/null 2>&1; then
                            git update-index --skip-worktree -- "$file"
                            echo "🙈 Skipping (worktree): $file"
                        fi
                    fi
                fi
            done <<< "$skipped_files"
        fi

    else
        echo "❌ Merge failed (conflict?)."
        echo "   Fix conflicts and commit the result."
        
        # In case of merge failure, we do NOT pop stash or reskip automatically
        # because the user needs to resolve merge conflicts first.
        if [ $stashed -eq 1 ]; then
            echo "⚠️  Local changes are saved in stash (stash@{0}). Pop them after fixing conflicts."
        fi
        if [ -n "$skipped_files" ]; then
            echo "⚠️  Skipped files are currently unskipped. Re-skip them after fixing conflicts."
            # We could print them or just let user run 'gskip' later.
        fi
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

# Helper: Auto-detect the most likely parent branch
detect_base_branch() {
    local target_branch="$1"
    local candidates=("main" "master" "develop" "next" "trunk")
    local best_base=""
    local best_timestamp=0

    for candidate in "${candidates[@]}"; do
        # Check both local "$candidate" and "origin/$candidate"
        local refs_to_check=()
        
        if git rev-parse --verify "$candidate" >/dev/null 2>&1; then
            refs_to_check+=("$candidate")
        fi
        
        if git rev-parse --verify "origin/$candidate" >/dev/null 2>&1; then
            refs_to_check+=("origin/$candidate")
        fi

        for ref in "${refs_to_check[@]}"; do
            # Find the common ancestor (merge-base)
            local mb
            mb=$(git merge-base "$ref" "$target_branch" 2>/dev/null)
            
            if [ -n "$mb" ]; then
                # Get the commit time of the merge-base (Unix timestamp)
                local ts
                ts=$(git show -s --format=%ct "$mb")
                
                # We want the candidate with the MOST RECENT common ancestor
                if [ "$ts" -gt "$best_timestamp" ]; then
                    best_timestamp=$ts
                    best_base=$ref
                fi
            fi
        done
    done

    # Fallback to 'main' if detection fails completely
    echo "${best_base:-main}"
}

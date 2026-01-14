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

# GRESTACK: Fix stacked branches after a squash merge
# Transplants changes from the current branch onto a new base, skipping the old parent branch's commits.
# Usage: grestack <old_parent_branch> [new_base]
grestack() {
    if [ -z "$1" ]; then
        echo "Usage: grestack <old_parent_branch> [new_base]"
        echo "  <old_parent_branch>: The branch that was squash-merged (and you are currently based on)."
        echo "  [new_base]: The branch you want to move onto (default: origin/main)."
        return 1
    fi

    local old_parent="$1"
    local new_base="${2:-origin/main}"
    local current_branch=$(git branch --show-current)

    if [ -z "$current_branch" ]; then
        echo "❌ Not currently on a branch."
        return 1
    fi

    # Check for uncommitted changes
    if [ -n "$(git status --porcelain)" ]; then
        echo "❌ You have uncommitted changes. Please commit or stash them before restacking."
        return 1
    fi

    echo "🔄 Fetching origin..."
    git fetch origin --quiet

    # Resolve new_base alias to actual ref if possible (generic check)
    if [ "$new_base" == "origin/main" ] && ! git rev-parse --verify "origin/main" &>/dev/null; then
        if git rev-parse --verify "origin/master" &>/dev/null; then
            new_base="origin/master"
            echo "⚠️ 'origin/main' not found, using 'origin/master'."
        fi
    fi

    echo "✂️  Rebasing '$current_branch' onto '$new_base', cutting off history from '$old_parent'..."
    # git rebase --onto <new_base> <old_parent> <current_branch>
    if git rebase --onto "$new_base" "$old_parent" "$current_branch"; then
        echo "✅ Successfully restacked."
        echo "🚀 You likely need to force push now:"
        echo "   git push --force-with-lease"
        else
            echo "❌ Rebase failed."
            echo "   Resolve conflicts and run 'git rebase --continue' or 'git rebase --abort'."
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

# GDMB: Diff from merge-base with origin/main and save to ~/Downloads/git-<branch>.diff
# Usage: gdmb [base_branch]
gdmb() {
    local base=$(gmb "$1")
    if [ -n "$base" ]; then
        gdiff_out "$base"
    else
        echo "❌ Could not find merge-base."
        return 1
    fi
}
    
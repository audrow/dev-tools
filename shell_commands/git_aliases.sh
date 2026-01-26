#!/bin/bash

# Git log (simple)
# Usage: glog [options]
function glog() {
    git log "$@"
}

# Git status
function gst() {
    git status
}

# Git status (short alias)
function gs() {
    git status
}

# Pretty git log (one-liners)
function gl() {
    git log --oneline --graph --decorate "$@"
}

# Git branch
function gb() {
    git branch "$@"
}

# Git branch delete
function gbd() {
    git branch -d "$@"
}

# Git checkout
function gco() {
    git checkout "$@"
}

# Git commit all
function gca() {
    git commit -a "$@"
}

# Git commit with message
function gcm() {
    git commit -m "$*"
}

# Git diff
function gd() {
    git diff "$@"
}

# Git diff stat
function gds() {
    git diff --stat "$@"
}

# Git diff staged
function gdstaged() {
    git diff --staged "$@"
}

# Git diff merge-base
# Usage: gdmb [base_branch] [target_ref]
function gdmb() {
    local base_branch="${1:-main}"
    local target_ref="${2:-HEAD}"
    local merge_base=$(gmb "$base_branch" "$target_ref")
    
    if [ -n "$merge_base" ]; then
        git diff "$merge_base" "$target_ref"
    else
        echo "❌ Could not find merge-base."
        return 1
    fi
}

# Git diff merge-base stat
# Usage: gdmbs [base_branch] [target_ref]
function gdmbs() {
    local base_branch="${1:-main}"
    local target_ref="${2:-HEAD}"
    local merge_base=$(gmb "$base_branch" "$target_ref")

    if [ -n "$merge_base" ]; then
        git diff --stat "$merge_base" "$target_ref"
    else
        echo "❌ Could not find merge-base."
        return 1
    fi
}

# Git pull (now gpl to avoid conflict with gl = git log)
function gpl() {
    git pull
}

# Git push
function gp() {
    git push
}

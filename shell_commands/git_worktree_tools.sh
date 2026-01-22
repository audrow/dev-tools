#!/bin/bash

# WT: Switch Worktree
# Usage: wt
wt() {
  local selected_worktree
  
  if ! command -v fzf &> /dev/null; then
    echo "❌ Error: fzf is not installed. Please install fzf to use this command."
    return 1
  fi

  # Lists worktrees, uses fzf, and grabs the path (first column)
  # awk '{print $1}' gets the path.
  selected_worktree=$(git worktree list | fzf --height 40% --layout=reverse | awk '{print $1}')

  if [ -n "$selected_worktree" ]; then
    cd "$selected_worktree"
  fi
}

# WTA: Add Worktree
# Usage: wta <branch-name> [base-branch]
wta() {
  if [ -z "$GITHUB_USER" ]; then
    echo "❌ Error: GITHUB_USER environment variable is not set."
    echo "Please set it in your shell configuration (e.g., export GITHUB_USER=yourusername)."
    return 1
  fi

  if [ -z "$1" ]; then
    echo "Usage: wta <description|branch-name> [base-branch]"
    return 1
  fi

  # 1. AUTO-FETCH: Update knowledge of remote branches
  echo "🔄 Fetching latest from remotes..."
  git fetch --all --quiet

  # 2. ARGUMENT PARSING
  # Support "wta my feature branch" (multi-word description) vs "wta feature base"
  local args=("$@")
  local input_text=""
  local base_branch="main"

  if [ ${#args[@]} -gt 1 ]; then
    local last_arg_index=$((${#args[@]} - 1))
    local last_arg="${args[$last_arg_index]}"

    # Check if last argument is a valid branch (local or remote)
    if git rev-parse --verify "$last_arg" &>/dev/null || git rev-parse --verify "origin/$last_arg" &>/dev/null; then
       base_branch="$last_arg"
       unset 'args[$last_arg_index]'
       input_text="${args[*]}"
    else
       input_text="${args[*]}"
    fi
  else
    input_text="$1"
  fi

  local main_repo_path=$(git worktree list | head -n 1 | awk '{print $1}')
  local repo_name=$(basename "$main_repo_path")

  # 3. SLUGIFY INPUT
  # Lowercase, replace spaces with dashes, keep alphanumeric/dash/slash/underscore
  local slug=$(echo "$input_text" | tr '[:upper:]' '[:lower:]')
  slug="${slug// /-}"
  slug=$(echo "$slug" | tr -cd '[:alnum:]-_/')
  slug=$(echo "$slug" | tr -s '-')

  # 3. Sanitize path: Replace slashes with dashes for the FOLDER name
  local safe_dir_name=$(echo "$slug" | tr '/' '-')
  local target_dir="$HOME/.worktrees/$repo_name/$safe_dir_name"

  # Ensure the parent directory exists
  mkdir -p "$(dirname "$target_dir")"

  # STRATEGY 1: Try to add as an EXISTING branch (local or remote-tracking)
  # Check: exact input, slug, or $GITHUB_USER/slug
  local candidates=("$input_text" "$slug" "${GITHUB_USER}/$slug")

  for candidate in "${candidates[@]}"; do
    if git rev-parse --verify "$candidate" &>/dev/null || git rev-parse --verify "origin/$candidate" &>/dev/null; then
        if git worktree add "$target_dir" "$candidate" 2>/dev/null; then
          echo "✅ Checked out existing branch: $candidate"
          cd "$target_dir"
          return 0
        fi
    fi
  done

  # STRATEGY 2: Create a NEW branch
  # Construct new branch name with prefix
  local new_branch_name="$slug"
  if [[ "$new_branch_name" != "${GITHUB_USER}/"* ]]; then
      new_branch_name="${GITHUB_USER}/$new_branch_name"
  fi

  # Check if base branch exists on remote
  local remote_base="origin/$base_branch"
  if ! git rev-parse --verify "$remote_base" &>/dev/null; then
      # Fallback to master if main doesn't exist and base wasn't specified
      if [ "$base_branch" == "main" ] && git rev-parse --verify "origin/master" &>/dev/null; then
          remote_base="origin/master"
          base_branch="master"
      elif [ "$base_branch" == "main" ] && git rev-parse --verify "origin/main" &>/dev/null; then
          : # It is main
      else
           echo "⚠️ Base branch '$remote_base' not found. Creating off HEAD."
           remote_base="HEAD"
      fi
  fi

  echo "Branch '$new_branch_name' not found. Creating new branch off $remote_base..."
  
  # Note: --no-track ensures the new branch does NOT track origin/main (avoiding the bug where push goes to main)
  # But only if we are branching off a remote.
  local track_flag=""
  if [[ "$remote_base" == origin/* ]]; then
      track_flag="--no-track"
  fi

  if git worktree add "$target_dir" -b "$new_branch_name" "$remote_base" $track_flag; then
    echo "✨ Created new branch: $new_branch_name (based on $remote_base)"
    cd "$target_dir"
    return 0
  else
    echo "❌ Failed to create worktree."
    return 1
  fi
}

# WTP: Prune (Delete current hidden worktree & go home)
wtp() {
  local current_path=$(pwd)
  local main_repo_path=$(git worktree list | head -n 1 | awk '{print $1}')

  if [ "$current_path" = "$main_repo_path" ]; then
    echo "⚠️  You are in the main worktree. Cannot prune."
    return 1
  fi

  # Move safely back to the main repo
  echo "Moving to main repo: $main_repo_path"
  cd "$main_repo_path"

  # Remove the worktree (and the folder in ~/.worktrees)
  echo "Removing worktree: $current_path"
  # --force might be needed if there are untracked files or unmerged changes, use with caution.
  # User requested --force in their snippet, so we keep it.
  git worktree remove "$current_path" --force
}

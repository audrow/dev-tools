#!/bin/bash

# WT: Switch Worktree
# Usage: wt
wt() {
  local selected_worktree
  
  if ! command_exists fzf; then
    echo "❌ Error: fzf is not installed. Please install fzf to use this command."
    return 1
  fi

  # Lists worktrees, uses fzf, and grabs the path (first column)
  # awk '{print $1}' gets the path.
  selected_worktree=$(git worktree list | fzf --height 40% --layout=reverse | awk '{print $1}')

  if [ -n "$selected_worktree" ]; then
    echo "__BASH_CD__:$selected_worktree"
    cd "$selected_worktree"
  fi
}

# Helper function to set up a new worktree
_wta_setup_worktree() {
  local main_repo_path="$1"
  local target_dir="$2"

  # Copy all .env* files (.env, .env.local, .env.development, etc.)
  local env_files_copied=0
  for env_file in "$main_repo_path"/.env*; do
    if [ -f "$env_file" ]; then
      cp "$env_file" "$target_dir/$(basename "$env_file")"
      env_files_copied=$((env_files_copied + 1))
    fi
  done
  if [ $env_files_copied -gt 0 ]; then
    echo "📋 Copied $env_files_copied .env* file(s)"
  fi

  # Symlink node_modules if it exists (faster than copying)
  if [ -d "$main_repo_path/node_modules" ]; then
    ln -s "$main_repo_path/node_modules" "$target_dir/node_modules"
    echo "🔗 Symlinked node_modules"
  fi

  # Symlink Python .venv if it exists
  if [ -d "$main_repo_path/.venv" ]; then
    ln -s "$main_repo_path/.venv" "$target_dir/.venv"
    echo "🐍 Symlinked .venv"
  fi

  # Copy worktree path to clipboard
  if copy_to_clipboard "$target_dir"; then
    echo "📎 Copied path to clipboard"
  fi

  # Run post-setup hook if it exists
  if [ -f "$target_dir/.worktree-setup.sh" ]; then
    echo "🔧 Running .worktree-setup.sh..."
    (cd "$target_dir" && bash .worktree-setup.sh)
  elif [ -f "$main_repo_path/.worktree-setup.sh" ]; then
    echo "🔧 Running .worktree-setup.sh from main repo..."
    (cd "$target_dir" && bash "$main_repo_path/.worktree-setup.sh")
  fi

  # Open editor if USER_IDE is set
  if [ -n "$USER_IDE" ]; then
    echo "🚀 Opening $USER_IDE..."
    "$USER_IDE" "$target_dir"
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
    echo "Usage: wta <description|branch-name> [--base|-b base-branch]"
    return 1
  fi

  # 1. AUTO-FETCH: Update knowledge of remote branches
  echo "🔄 Fetching latest from remotes..."
  git fetch --all --quiet

  # 2. ARGUMENT PARSING
  local input_text=""
  local base_branch="main"
  local args=("$@")
  local description_parts=()

  local skip_next=false
  for i in "${!args[@]}"; do
    if [ "$skip_next" = true ]; then
      skip_next=false
      continue
    fi

    local arg="${args[$i]}"
    if [[ "$arg" == "--base" || "$arg" == "-b" ]]; then
      # Make sure there is a next argument
      local next_index=$((i + 1))
      if [ -n "${args[$next_index]}" ]; then
        base_branch="${args[$next_index]}"
        skip_next=true
      else
        echo "❌ Error: --base option requires an argument."
        return 1
      fi
    else
      description_parts+=("$arg")
    fi
  done

  input_text="${description_parts[*]}"

  if [ -z "$input_text" ]; then
    echo "❌ Error: No description or branch name provided."
    return 1
  fi

  local main_repo_path=$(get_main_worktree_path)
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
          echo "📂 Worktree: $target_dir"
          _wta_setup_worktree "$main_repo_path" "$target_dir"
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
    echo "📂 Worktree: $target_dir"
    _wta_setup_worktree "$main_repo_path" "$target_dir"
    return 0
  else
    echo "❌ Failed to create worktree."
    return 1
  fi
}

# WTP: Prune (Delete current hidden worktree & go home)
wtp() {
  local current_path=$(pwd)
  local main_repo_path=$(get_main_worktree_path)

  if [ "$current_path" = "$main_repo_path" ]; then
    echo "⚠️  You are in the main worktree. Cannot prune."
    return 1
  fi

  # Get current branch name for display
  local branch_name=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")

  # Confirmation prompt
  echo "⚠️  About to delete worktree:"
  echo "   Path: $current_path"
  echo "   Branch: $branch_name"
  echo ""
  read -p "Are you sure? [y/N] " confirm
  if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    return 0
  fi

  # Move safely back to the main repo
  echo "Moving to main repo: $main_repo_path"
  echo "__BASH_CD__:$main_repo_path"
  cd "$main_repo_path"

  # Remove the worktree (and the folder in ~/.worktrees)
  echo "Removing worktree: $current_path"
  # --force might be needed if there are untracked files or unmerged changes, use with caution.
  git worktree remove "$current_path" --force
  echo "✅ Worktree removed."
}

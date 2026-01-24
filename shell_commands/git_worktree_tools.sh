#!/bin/bash

# WT: Switch to Worktree (using fzf)
# Usage: wt
wt() {
  local selected_worktree
  
  if ! command_exists fzf; then
    echo "❌ Error: fzf is not installed. Please install fzf to use this command."
    return 1
  fi

  echo "📂 Select worktree to switch to..."
  # Lists worktrees, uses fzf, and grabs the path (first column)
  selected_worktree=$(git worktree list | fzf --height 40% --layout=reverse --header="Select worktree" | awk '{print $1}')

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
    echo -n "🚀 Open in $USER_IDE? [Y/n] "
    read open_ide
    # Default to yes if empty or starts with Y/y
    if [[ -z "$open_ide" || "$open_ide" =~ ^[Yy] ]]; then
      "$USER_IDE" "$target_dir"
    fi
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
  local existing_branch=""

  for candidate in "${candidates[@]}"; do
    if git rev-parse --verify "$candidate" &>/dev/null || git rev-parse --verify "origin/$candidate" &>/dev/null; then
        existing_branch="$candidate"
        break
    fi
  done

  if [ -n "$existing_branch" ]; then
    echo "⚠️  Branch '$existing_branch' already exists."
    echo -n "Force recreate? This will delete the existing branch. [y/N] "
    read force_recreate
    
    if [[ "$force_recreate" =~ ^[Yy]$ ]]; then
      echo "🗑️  Deleting existing branch '$existing_branch'..."
      # Remove worktree if it exists for this branch
      local existing_worktree=$(git worktree list | grep "$existing_branch" | awk '{print $1}')
      if [ -n "$existing_worktree" ]; then
        git worktree remove "$existing_worktree" --force 2>/dev/null
      fi
      # Delete the branch
      git branch -D "$existing_branch" 2>/dev/null
      git branch -Dr "origin/$existing_branch" 2>/dev/null
      # Continue to create new branch below
    else
      # Checkout existing branch
      if git worktree add "$target_dir" "$existing_branch" 2>/dev/null; then
        echo "✅ Checked out existing branch: $existing_branch"
        echo "📂 Worktree: $target_dir"
        _wta_setup_worktree "$main_repo_path" "$target_dir"
        return 0
      else
        echo "❌ Failed to checkout existing branch."
        return 1
      fi
    fi
  fi

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

# WTP: Prune Worktree (select with fzf, then delete)
# Usage: wtp
wtp() {
  local main_repo_path=$(get_main_worktree_path)
  
  if ! command_exists fzf; then
    echo "❌ Error: fzf is not installed. Please install fzf to use this command."
    return 1
  fi

  echo "🗑️  Select worktree to delete..."
  # Get worktree list excluding the main worktree
  local selected_line=$(git worktree list | tail -n +2 | fzf --height 40% --layout=reverse --header="Select worktree to delete")
  
  if [ -z "$selected_line" ]; then
    echo "Cancelled."
    return 0
  fi
  
  local worktree_path=$(echo "$selected_line" | awk '{print $1}')
  local branch_name=$(echo "$selected_line" | awk '{print $3}' | tr -d '[]')

  # Confirmation prompt
  echo ""
  echo "⚠️  About to delete worktree:"
  echo "   Path: $worktree_path"
  echo "   Branch: $branch_name"
  echo ""
  echo -n "Are you sure? [y/N] "
  read confirm
  if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    return 0
  fi

  # If we're currently in the worktree being deleted, move to main first
  local current_path=$(pwd)
  if [[ "$current_path" == "$worktree_path"* ]]; then
    echo "Moving to main repo: $main_repo_path"
    echo "__BASH_CD__:$main_repo_path"
    cd "$main_repo_path"
  fi

  # Remove the worktree
  echo "Removing worktree: $worktree_path"
  git worktree remove "$worktree_path" --force
  echo "✅ Worktree removed."
}

# WTO: Open Worktree in IDE (select with fzf)
# Usage: wto
wto() {
  if [ -z "$USER_IDE" ]; then
    echo "❌ Error: USER_IDE environment variable is not set."
    echo "Please set it in your shell configuration (e.g., export USER_IDE=code)."
    return 1
  fi
  
  if ! command_exists fzf; then
    echo "❌ Error: fzf is not installed. Please install fzf to use this command."
    return 1
  fi

  echo "💻 Select worktree to open in $USER_IDE..."
  local selected_worktree=$(git worktree list | fzf --height 40% --layout=reverse --header="Select worktree to open" | awk '{print $1}')

  if [ -n "$selected_worktree" ]; then
    echo "🚀 Opening $selected_worktree in $USER_IDE..."
    "$USER_IDE" "$selected_worktree"
  else
    echo "Cancelled."
  fi
}

#!/bin/bash

# Helper: Check if fzf is installed
_require_fzf() {
  if ! command_exists fzf; then
    echo "❌ Error: fzf is not installed. Please install fzf to use this command."
    return 1
  fi
  return 0
}

# Helper: Check if USER_IDE is set
_require_user_ide() {
  if [ -z "$USER_IDE" ]; then
    echo "❌ Error: USER_IDE environment variable is not set."
    echo "Please set it in your shell configuration (e.g., export USER_IDE=code)."
    return 1
  fi
  return 0
}

# Helper: Prompt for yes/no with default
# Usage: _prompt_yn "Question?" "Y" (for default yes) or "N" (for default no)
# Returns 0 for yes, 1 for no
_prompt_yn() {
  local question="$1"
  local default="${2:-N}"  # Default to N if not specified
  local prompt_suffix
  
  if [[ "$default" =~ ^[Yy]$ ]]; then
    prompt_suffix="[Y/n]"
  else
    prompt_suffix="[y/N]"
  fi
  
  # Print prompt to stderr to avoid polluting stdout
  echo -n "$question $prompt_suffix " >&2
  if [ "${PROMPT_ASSUME_YES:-0}" = "1" ]; then
    return 0
  fi

  if ! read -r response; then
    response=""
  fi
  
  # If empty, use default for TTYs, or default to "No" for non-interactive
  if [ -z "$response" ]; then
    if [ -t 0 ]; then
      response="$default"
    else
      response="N"
    fi
  fi
  
  if [[ "$response" =~ ^[Yy]$ ]]; then
    return 0
  else
    return 1
  fi
}

# Helper: Select a worktree using fzf
# Usage: _select_worktree "header text" [skip_first_line]
# Returns the selected worktree path (first column), empty if cancelled
_select_worktree() {
  local header="${1:-Select worktree}"
  local skip_first="${2:-false}"
  local worktree_list
  
  if [ "$skip_first" = "true" ]; then
    worktree_list=$(git worktree list | tail -n +2)
  else
    worktree_list=$(git worktree list)
  fi
  
  echo "$worktree_list" | fzf --height 40% --layout=reverse --header="$header" | awk '{print $1}'
}

# WT: Switch to Worktree (using fzf)
# Usage: wt
wt() {
  # Check if there are any worktrees besides the main one
  local worktree_count=$(git worktree list | wc -l | tr -d ' ')
  if [ "$worktree_count" -le 1 ]; then
    echo "ℹ️  No additional worktrees found. Only the main worktree exists."
    echo "💡 Use 'wta <description>' to create a new worktree."
    return 0
  fi
  
  _require_fzf || return 1
  
  echo "📂 Select worktree to switch to..."
  local selected_worktree=$(_select_worktree "Select worktree")

  if [ -n "$selected_worktree" ]; then
    echo "__BASH_CD__:$selected_worktree"
    cd "$selected_worktree"
  else
    echo "❌ Cancelled."
  fi
}

# Helper function to set up a new worktree
_wta_setup_worktree() {
  local main_repo_path="$1"
  local target_dir="$2"

  # Enable nullglob to handle case where no .env* files exist
  shopt -s nullglob
  
  # Copy all .env* files (.env, .env.local, .env.development, etc.)
  local env_files_copied=0
  for env_file in "$main_repo_path"/.env*; do
    if [ -f "$env_file" ]; then
      cp "$env_file" "$target_dir/$(basename "$env_file")"
      env_files_copied=$((env_files_copied + 1))
    fi
  done
  
  # Disable nullglob after use
  shopt -u nullglob
  
  if [ $env_files_copied -gt 0 ]; then
    echo "📋 Copied $env_files_copied .env* file(s)"
  fi

  # Symlink node_modules if it exists (faster than copying)
  if [ -d "$main_repo_path/node_modules" ]; then
    if [ -e "$target_dir/node_modules" ] || [ -L "$target_dir/node_modules" ]; then
      if [ -L "$target_dir/node_modules" ] && [ "$(readlink "$target_dir/node_modules")" = "$main_repo_path/node_modules" ]; then
        echo "🔗 node_modules already symlinked; skipping"
      else
        echo "⚠️  node_modules already exists in $target_dir; skipping symlink"
      fi
    else
      ln -s "$main_repo_path/node_modules" "$target_dir/node_modules"
      echo "🔗 Symlinked node_modules"
    fi
  fi

  # Symlink Python .venv if it exists
  if [ -d "$main_repo_path/.venv" ]; then
    if [ -e "$target_dir/.venv" ] || [ -L "$target_dir/.venv" ]; then
      if [ -L "$target_dir/.venv" ] && [ "$(readlink "$target_dir/.venv")" = "$main_repo_path/.venv" ]; then
        echo "🐍 .venv already symlinked; skipping"
      else
        echo "⚠️  .venv already exists in $target_dir; skipping symlink"
      fi
    else
      ln -s "$main_repo_path/.venv" "$target_dir/.venv"
      echo "🐍 Symlinked .venv"
    fi
  fi

  # Ask to copy worktree path to clipboard
  if _prompt_yn "📎 Copy path to clipboard?" "N"; then
    if copy_to_clipboard "$target_dir"; then
      echo "📎 Copied to clipboard"
    fi
  fi

  # Run post-setup hook if it exists (with security confirmation)
  local worktree_setup_script=""
  local worktree_setup_source=""
  
  if [ -f "$target_dir/.worktree-setup.sh" ]; then
    worktree_setup_script="$target_dir/.worktree-setup.sh"
    worktree_setup_source="worktree"
  elif [ -f "$main_repo_path/.worktree-setup.sh" ]; then
    worktree_setup_script="$main_repo_path/.worktree-setup.sh"
    worktree_setup_source="main repo"
  fi
  
  if [ -n "$worktree_setup_script" ]; then
    echo ""
    echo "⚠️  A .worktree-setup.sh script was found in the $worktree_setup_source:"
    echo "   $worktree_setup_script"
    if _prompt_yn "Execute this script now?" "N"; then
      echo "🔧 Running .worktree-setup.sh..."
      (cd "$target_dir" && bash "$worktree_setup_script")
      local hook_status=$?
      if [ $hook_status -ne 0 ]; then
        echo "⚠️  Warning: .worktree-setup.sh exited with status $hook_status"
      fi
    else
      echo "ℹ️  Skipped .worktree-setup.sh execution."
    fi
  fi

  # Open editor if USER_IDE is set
  if [ -n "$USER_IDE" ]; then
    if _prompt_yn "🚀 Open in $USER_IDE?" "Y"; then
      if ! command -v "$USER_IDE" >/dev/null 2>&1; then
        echo "❌ Error: USER_IDE command '$USER_IDE' not found."
        echo "   Please ensure it is installed and in your PATH."
      elif ! "$USER_IDE" "$target_dir" 2>/dev/null; then
        echo "⚠️  Warning: Failed to open IDE using '$USER_IDE'."
      fi
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
    
    if _prompt_yn "Force recreate? This will delete the existing branch." "N"; then
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
  _require_fzf || return 1
  
  local main_repo_path=$(get_main_worktree_path)
  
  echo "🗑️  Select worktree to delete..."
  # Get worktree list excluding the main worktree
  local selected_line=$(git worktree list | tail -n +2 | fzf --height 40% --layout=reverse --header="Select worktree to delete")
  
  if [ -z "$selected_line" ]; then
    echo "❌ Cancelled."
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
  
  if ! _prompt_yn "Are you sure?" "N"; then
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
  
  # Ask if user wants to delete the branch
  if [ -n "$branch_name" ]; then
    echo ""
    if _prompt_yn "🗑️  Delete branch '$branch_name'?" "Y"; then
      # Try regular delete first
      if git branch -d "$branch_name" 2>/dev/null; then
        echo "✅ Branch deleted."
      else
        # Regular delete failed, ask about force delete
        echo "⚠️  Branch '$branch_name' is not fully merged."
        if _prompt_yn "Force delete with -D?" "N"; then
          git branch -D "$branch_name"
          echo "✅ Branch force deleted."
        else
          echo "Branch kept."
        fi
      fi
    else
      echo "Branch kept."
    fi
  fi
}

# WTO: Open Worktree in IDE (select with fzf)
# Usage: wto
wto() {
  _require_user_ide || return 1
  _require_fzf || return 1

  echo "💻 Select worktree to open in $USER_IDE..."
  local selected_worktree=$(_select_worktree "Select worktree to open")

  if [ -n "$selected_worktree" ]; then
    echo "🚀 Opening $selected_worktree in $USER_IDE..."
    "$USER_IDE" "$selected_worktree"
  else
    echo "❌ Cancelled."
  fi
}

# WTLOCK: Lock root worktree to prevent commits
# Usage: wtlock
wtlock() {
  local main_repo_path=$(get_main_worktree_path)
  local hook_path="$main_repo_path/.git/hooks/pre-commit"
  
  if [ -f "$hook_path" ]; then
    # Check if it's our lock hook
    if grep -q "WORKTREE_LOCK" "$hook_path" 2>/dev/null; then
      echo "🔒 Root worktree is already locked."
      return 0
    else
      echo "⚠️  Warning: A pre-commit hook already exists at:"
      echo "   $hook_path"
      if ! _prompt_yn "Overwrite it with the lock hook?" "N"; then
        echo "❌ Cancelled."
        return 1
      fi
    fi
  fi
  
  # Create hooks directory if it doesn't exist
  mkdir -p "$main_repo_path/.git/hooks"
  
  # Create the lock hook
  cat > "$hook_path" << 'EOF'
#!/bin/bash
# WORKTREE_LOCK: Prevents commits in the root worktree
# Created by wtlock command

# Get the root worktree path
root_path=$(git worktree list | head -n 1 | awk '{print $1}')
current_path=$(git rev-parse --show-toplevel 2>/dev/null)

# Check if we're in the root worktree
if [ "$current_path" = "$root_path" ]; then
  echo ""
  echo "❌ ERROR: Commits are blocked in the root worktree!"
  echo ""
  echo "   This repository uses named worktrees for development."
  echo "   Please create a worktree with: wta <branch-name>"
  echo ""
  echo "   Current location: $current_path"
  echo "   Root worktree: $root_path"
  echo ""
  echo "   To unlock: wtunlock"
  echo ""
  exit 1
fi

exit 0
EOF
  
  chmod +x "$hook_path"
  echo "🔒 Root worktree locked! Commits are now blocked."
  echo "   Hook installed: $hook_path"
  echo "   To unlock: wtunlock"
}

# WTUNLOCK: Unlock root worktree to allow commits
# Usage: wtunlock
wtunlock() {
  local main_repo_path=$(get_main_worktree_path)
  local hook_path="$main_repo_path/.git/hooks/pre-commit"
  
  if [ ! -f "$hook_path" ]; then
    echo "ℹ️  No pre-commit hook found. Root worktree is already unlocked."
    return 0
  fi
  
  # Check if it's our lock hook
  if ! grep -q "WORKTREE_LOCK" "$hook_path" 2>/dev/null; then
    echo "⚠️  Warning: The pre-commit hook exists but wasn't created by wtlock."
    echo "   Hook location: $hook_path"
    if ! _prompt_yn "Delete it anyway?" "N"; then
      echo "❌ Cancelled."
      return 1
    fi
  fi
  
  rm "$hook_path"
  echo "🔓 Root worktree unlocked! Commits are now allowed."
}

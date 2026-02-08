#!/bin/bash
# Shared utility functions for shell commands

# Copy text to the system clipboard (cross-platform)
# Usage: copy_to_clipboard "text to copy"
# Returns: 0 if copied, 1 if no clipboard tool available
copy_to_clipboard() {
  local text="$1"
  
  if command -v pbcopy &> /dev/null; then
    # macOS
    echo -n "$text" | pbcopy 2>/dev/null
    return $?
  elif command -v xclip &> /dev/null; then
    # Linux with xclip
    echo -n "$text" | xclip -selection clipboard 2>/dev/null
    return $?
  elif command -v xsel &> /dev/null; then
    # Linux with xsel
    echo -n "$text" | xsel --clipboard --input 2>/dev/null
    return $?
  elif command -v wl-copy &> /dev/null; then
    # Wayland
    echo -n "$text" | wl-copy 2>/dev/null
    return $?
  fi
  
  return 1
}

# Get the path to the main (first) worktree
# Usage: main_repo_path=$(get_main_worktree_path)
get_main_worktree_path() {
  git worktree list | head -n 1 | awk '{print $1}'
}

# Check if a command exists
# Usage: if command_exists fzf; then ...
command_exists() {
  command -v "$1" &> /dev/null
}

# Helper: Check if fzf is installed
_require_fzf() {
  if ! command_exists fzf; then
    echo "❌ Error: fzf is not installed. Please install fzf to use this command."
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

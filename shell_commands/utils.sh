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

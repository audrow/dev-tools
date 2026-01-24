# Shell Commands & Git Tools

A collection of shell scripts and Git productivity tools designed to be easily sourced into your `bash` or `zsh` environment.

## Quickstart

1.  **Source the tools:** Add the following line to your `~/.bashrc` or `~/.zshrc`:
    ```bash
    source /path/to/dev-tools/shell_commands/init.sh
    ```
2.  **Reload your shell:**
    ```bash
    source ~/.bashrc  # or source ~/.zshrc
    ```
3.  **Try it out:**
    ```bash
    glog
    ```

## Installation

To make these commands persistent, append the sourcing command to your shell's configuration file.

### For Bash users:
```bash
echo "source $(pwd)/init.sh" >> ~/.bashrc
source ~/.bashrc
```

### For Zsh users:
```bash
echo "source $(pwd)/init.sh" >> ~/.zshrc
source ~/.zshrc
```

## Available Tools

### Git Aliases (`git_aliases.sh`)

Commonly used git commands shortened for speed.

| Command | Git Equivalent | Description |
| :--- | :--- | :--- |
| `gl` | `git log --oneline --graph --decorate` | Visual, compact git log (one-liners). |
| `glog` | `git log` | Show commit logs (full). |
| `gst` | `git status` | Show the working tree status. |
| `gs` | `git status` | Short alias for git status. |
| `gb` | `git branch` | List, create, or delete branches. |
| `gbd` | `git branch -d` | Delete a branch. |
| `gco` | `git checkout` | Checkout a branch or paths. |
| `gca` | `git commit -a` | Commit all tracked changes. |
| `gcm` | `git commit -m` | Commit with a message. |
| `gd` | `git diff` | Show changes between commits, commit and working tree, etc. |
| `gds` | `git diff --stat` | Show diff statistics. |
| `gdstaged` | `git diff --staged` | Show changes that are staged. |
| `gdmb` | diff merge-base | Show diff from merge-base with origin/main (or master). |
| `gdmbs` | diff merge-base --stat | Show diff statistics from merge-base. |
| `gpl` | `git pull` | Fetch from and integrate with another repository. |
| `gp` | `git push` | Update remote refs along with associated objects. |

### Git Worktree Tools (`git_worktree_tools.sh`)

Helpers for managing `git worktree` workflows. Uses `fzf` for fuzzy searching.

| Command | Usage | Description |
| :--- | :--- | :--- |
| `wt` | `wt` | **Switch to worktree**: Fuzzy search and switch to a worktree. Shows helpful message if only main worktree exists. |
| `wta` | `wta <desc> [--base branch]` | **Add worktree**: Create a new worktree. See details below. |
| `wtp` | `wtp` | **Prune worktree**: Select a worktree with fzf, delete it, and optionally delete the branch (with confirmation). |
| `wto` | `wto` | **Open worktree**: Select a worktree with fzf and open it in your IDE (`$USER_IDE`). |

*Note: All worktree commands require [fzf](https://github.com/junegunn/fzf) to be installed.*

#### `wta` - Add Worktree

Creates a new worktree with smart defaults and convenience features.

**Usage:**
```bash
wta <description|branch-name> [--base|-b base-branch]
```

**Features:**
- **Auto-fetch**: Fetches latest from all remotes before creating
- **Smart branch naming**: Converts descriptions to slugs and prefixes with `$GITHUB_USER/`
- **Existing branch handling**: If branch exists, prompts to checkout existing or force recreate
- **Copies all `.env*` files**: Copies `.env`, `.env.local`, `.env.development`, etc.
- **Symlinks `node_modules`**: If `node_modules` exists, it's symlinked (faster than copying)
- **Symlinks `.venv`**: Python virtual environments are symlinked too
- **Optional clipboard copy**: Prompts if you want to copy the worktree path to clipboard (defaults to no)
- **Runs post-setup hook**: Executes `.worktree-setup.sh` if it exists (for project-specific setup)
- **Opens your IDE** (with confirmation): If `USER_IDE` is set, prompts to open the worktree in your editor (defaults to yes)
- **Stays in place**: Does not change your current directory

**Environment Variables:**
- `GITHUB_USER` (required): Your GitHub username for branch prefixing
- `USER_IDE` (optional): Command to open your IDE (e.g., `code`, `cursor`, `webstorm`)

**Post-Setup Hook:**

Create a `.worktree-setup.sh` in your repo root for project-specific setup:
```bash
#!/bin/bash
# .worktree-setup.sh - runs after worktree creation
npm install        # or: pip install -e .
cp .env.example .env.local
```

**Examples:**
```bash
# Create worktree for "add login feature" -> branch: youruser/add-login-feature
wta "add login feature"

# Create worktree based on a different branch
wta "hotfix" --base release/v2

# If branch exists, you'll be prompted:
# ⚠️  Branch 'youruser/existing' already exists.
# Force recreate? This will delete the existing branch. [y/N]
# - Enter 'n' to checkout the existing branch
# - Enter 'y' to delete and recreate it fresh

# If USER_IDE=code, you'll be prompted:
# 🚀 Open in code? [Y/n]
```

#### `wtp` - Prune Worktree

Select and delete a worktree using fzf.

**Features:**
- **Fuzzy search**: Use fzf to select which worktree to delete
- **Confirmation prompt**: Shows branch name and path before deleting
- **Branch deletion**: After removing worktree, prompts to delete the branch (defaults to yes)
  - First tries `git branch -d` (safe delete)
  - If branch is not fully merged, asks if you want to force delete with `-D`
- **Safe navigation**: If you're in the worktree being deleted, automatically moves you to the main repo

**Example:**
```bash
$ wtp
🗑️  Select worktree to delete...
[fzf interface shows list of worktrees]

⚠️  About to delete worktree:
   Path: /Users/you/.worktrees/repo/my-feature
   Branch: youruser/my-feature

Are you sure? [y/N] y
Removing worktree: /Users/you/.worktrees/repo/my-feature
✅ Worktree removed.

🗑️  Delete branch 'youruser/my-feature'? [Y/n] y
✅ Branch deleted.
```

#### `wto` - Open Worktree in IDE

Select a worktree and open it in your configured IDE.

**Requirements:**
- `USER_IDE` environment variable must be set (e.g., `export USER_IDE=code`)

**Example:**
```bash
$ wto
💻 Select worktree to open in code...
[fzf interface shows list of worktrees]
🚀 Opening /Users/you/.worktrees/repo/my-feature in code...
```

### Git Workflow Tools (`git_workflow_tools.sh`)

Advanced workflow automation.

| Command | Usage | Description |
| :--- | :--- | :--- |
| `gupdate` | `gupdate [base]` | Updates your branch: **Fetch** -> **Merge** `origin/[base]` into current branch. |
| `gmb` | `gmb [base]` | Finds the merge-base between `origin/[base]` and `HEAD`. Automatically falls back to `master` if `main` is missing. |
| `gdiff_out` | `gdiff_out [args]` | Runs `git diff [args]` and saves the output to `~/Downloads/git-<branch>.diff`. Useful for copying diffs over SSH. |
| `gdmbo` | `gdmbo [base]` | Combines `gmb` and `gdiff_out`. Diffs from the merge-base of `origin/[base]` and saves to `~/Downloads/git-<branch>.diff`. |

### Python Tools Aliases (`python_tools.sh`)

Convenient wrappers for the Python tools in this repository. These allow you to run the tools without globally installing them via pip, provided you have run `./setup.sh` to create necessary environments.

| Command | Tool | Description |
| :--- | :--- | :--- |
| `text-aggregator` | Text Aggregator | Run the aggregator tool (uses local venv if present). |
| `command-reloader` / `cr` | Command Reloader | Run the reloader tool. |
| `command-trigger-listener` | Command Reloader | Run the remote listener tool. |

## How it Works

- `init.sh`: The entry point. It detects its own location and sources the other `.sh` files in the directory. Handles zsh compatibility by wrapping bash-specific functions.
- `utils.sh`: Shared utility functions (clipboard, worktree helpers).
- `git_aliases.sh`: Basic function-based aliases.
- `git_worktree_tools.sh`: Logic for worktree management, including path sanitization and tracking fixes.
- `git_workflow_tools.sh`: Multi-step git procedures.

### Utility Functions (`utils.sh`)

Shared helpers available to all scripts:

| Function | Usage | Description |
| :--- | :--- | :--- |
| `copy_to_clipboard` | `copy_to_clipboard "text"` | Copies text to clipboard (macOS/Linux). Returns 0 on success. |
| `get_main_worktree_path` | `path=$(get_main_worktree_path)` | Returns the path to the main (first) worktree. |
| `command_exists` | `if command_exists fzf; then` | Check if a command is available. |

## Customization

You can add new scripts to this directory. To make them active, ensure they are sourced in `init.sh`.

## Testing

The shell tools are tested using a Python-based test suite that verifies the functionality of the aliases and workflow scripts in a real (temporary) Git environment.

To run the tests:
```bash
python3 -m unittest tests/test_shell_tools.py
```

---

## License

This project is licensed under the MIT License - see the [LICENSE](../LICENSE) file for details.

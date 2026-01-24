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
| `wtlock` | `wtlock` | **Lock root worktree**: Install pre-commit hook to prevent commits in the root worktree. |
| `wtunlock` | `wtunlock` | **Unlock root worktree**: Remove the lock hook to allow commits again. |

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
  - ⚠️ **Note**: Symlinks use absolute paths. If you move the main repository or sync via cloud storage, symlinks will break
- **Symlinks `.venv`**: Python virtual environments are symlinked too
- **Optional clipboard copy**: Prompts if you want to copy the worktree path to clipboard (defaults to no)
- **Runs post-setup hook**: Executes `.worktree-setup.sh` if it exists, **with security confirmation** (defaults to no)
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

**Security Note**: For safety, `wta` will always prompt before executing `.worktree-setup.sh` scripts (defaults to **No**). This prevents untrusted code from running automatically when creating worktrees from branches you haven't reviewed.

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
- Requires `$USER_IDE` environment variable (e.g., `export USER_IDE=code`)

#### `wtlock` / `wtunlock` - Lock Root Worktree

Prevent accidental commits in the root/primary worktree.

**Usage:**
```bash
# Lock the root worktree (prevents commits)
wtlock

# Unlock to allow commits again
wtunlock
```

**Features:**
- **Installs pre-commit hook**: Creates a `.git/hooks/pre-commit` that blocks commits
- **Works in any worktree**: Only blocks commits in the root worktree, not in named worktrees
- **Safe overwrite check**: If a pre-commit hook already exists, prompts before overwriting
- **Clear error messages**: Shows helpful message when commit is blocked, suggesting to use `wta`

**Example workflow:**
```bash
# Lock the root worktree to enforce named worktrees
$ wtlock
🔒 Root worktree locked! Commits are now blocked.
   Hook installed: /path/to/repo/.git/hooks/pre-commit
   To unlock: wtunlock

# Try to commit in root (will be blocked)
$ git commit -m "test"

❌ ERROR: Commits are blocked in the root worktree!

   This repository uses named worktrees for development.
   Please create a worktree with: wta <branch-name>

   Current location: /path/to/repo
   Root worktree: /path/to/repo

   To unlock: wtunlock

# Commits in named worktrees still work
$ wta feature
$ git commit -m "works!"  # ✅ Success

# Unlock when needed
$ wtunlock
🔓 Root worktree unlocked! Commits are now allowed.
```

**Why use this?**
- Enforces clean git history by keeping all work in named branches
- Prevents accidental commits to main/master
- Keeps the root directory clean for reference
- Makes it obvious which branch you're working on (by the worktree path)

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
| `gdmbo` | `gdmbo [base]` | Diffs from merge-base of `origin/[base]`. **Copies to clipboard** by default, falls back to file if clipboard unavailable. Set `GDMBO_FORCE_FILE=1` to always write to file. |
| `gskip` | `gskip [file...]` | Mark files as skip-worktree (ignore local changes). Uses fzf for interactive selection if no files provided. |
| `gunskip` | `gunskip [file...]` | Remove skip-worktree flag (re-enable tracking). Uses fzf to select from skipped files if no arguments. |
| `gskipped` | `gskipped` | List all files currently marked as skip-worktree. |

**Environment Variables:**
- `GDIFF_DIR` (optional): Directory for diff output files (default: `~/Downloads`)
- `GDMBO_FORCE_FILE` (optional): Set to `1` to force `gdmbo` to always write to file instead of clipboard

#### Skip-Worktree Commands

The `gskip` family of commands helps you ignore local changes to tracked files without adding them to `.gitignore`. This is useful for:
- Configuration files with local overrides (e.g., `settings.json`)
- Files with machine-specific paths
- Temporary local modifications you don't want to commit

**Usage:**
```bash
# Mark a file as skip-worktree (interactive with fzf)
gskip

# Mark specific files
gskip settings.json .env.local

# List all skipped files
gskipped

# Re-enable tracking (interactive with fzf)
gunskip

# Re-enable tracking for specific files
gunskip settings.json
```

*Note: These commands require [fzf](https://github.com/junegunn/fzf) for interactive selection.*

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

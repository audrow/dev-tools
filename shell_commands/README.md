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
| `glog` | `git log --oneline --graph --decorate` | Visual, compact git log. |
| `gst` | `git status` | Show the working tree status. |
| `gco` | `git checkout` | Checkout a branch or paths. |
| `gl` | `git pull` | Fetch from and integrate with another repository. |
| `gp` | `git push` | Update remote refs along with associated objects. |

### Git Worktree Tools (`git_worktree_tools.sh`)

Helpers for managing `git worktree` workflows. Uses `fzf` for fuzzy searching.

| Command | Usage | Description |
| :--- | :--- | :--- |
| `wt` | `wt` | Fuzzy search and switch between existing worktrees. |
| `wta` | `wta <branch> [base]` | Create a new worktree for `<branch>` based on `[base]` (defaults to `main`). |
| `wtp` | `wtp` | Prune the current worktree (removes the directory and the worktree entry) and returns to the main repository. |

*Note: `wt` requires [fzf](https://github.com/junegunn/fzf) to be installed.*

### Git Workflow Tools (`git_workflow_tools.sh`)

Advanced workflow automation.

| Command | Usage | Description |
| :--- | :--- | :--- |
| `gupdate` | `gupdate [base]` | Safely updates your branch: **Stash** -> **Fetch** -> **Rebase** on `origin/[base]` -> **Pop Stash**. |
| `grestack` | `grestack <old_parent> [new_base]` | Fixes stacked PRs after a squash merge. Transplants commits from the current branch onto `new_base` (default: `origin/main`), skipping commits from `old_parent`. |

### Python Tools Aliases (`python_tools.sh`)

Convenient wrappers for the Python tools in this repository. These allow you to run the tools without globally installing them via pip, provided you have run `./setup.sh` to create necessary environments.

| Command | Tool | Description |
| :--- | :--- | :--- |
| `text-aggregator` | Text Aggregator | Run the aggregator tool (uses local venv if present). |
| `command-reloader` / `cr` | Command Reloader | Run the reloader tool. |
| `command-trigger-listener` | Command Reloader | Run the remote listener tool. |

## How it Works

- `init.sh`: The entry point. It detects its own location and sources the other `.sh` files in the directory.
- `git_aliases.sh`: Basic function-based aliases.
- `git_worktree_tools.sh`: Logic for worktree management, including path sanitization and tracking fixes.
- `git_workflow_tools.sh`: Multi-step git procedures.

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

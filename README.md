# Developer Tools

This repository is a collection of tools to support and streamline development workflows.

## Quick Setup

Run the interactive setup script to configure your shell and install dependencies:

```bash
./setup.sh
```

## Tools

*   [**Shell Commands**](./shell_commands/README.md): A suite of productivity aliases and functions for Git and workflow automation. Includes `glog`, `wt` (worktree manager), `gupdate`, and aliases for the Python tools below.
*   [**Text Aggregator**](./text_aggregator_tool/README.md): A command-line tool to find and combine text from multiple files into a single file or the clipboard. Designed to make working with LLMs easier.
    *   *Alias:* `text-aggregator`
*   [**Command Reloader**](./command_reloader_tool/README.md): A smart watcher that restarts a command when git-tracked files change. Features debounce, port/regex waiting, and remote trigger support.
    *   *Aliases:* `command-reloader`, `cr`, `command-trigger-listener`

## Contributing

Contributions are welcome! To ensure code quality and consistency, please run the following script before submitting any changes:

```bash
./check_all.sh
```

This script will:
1.  Set up a local development environment (`.venv`).
2.  Format the code using `black`.
3.  Run the full test suite for all shell tools and Python utilities.

### Code Style
We follow the standard [Black](https://github.com/psf/black) code style for Python.

### Adding New Tools
If you add a new tool, please:
1.  Include a `README.md` in the tool's directory.
2.  Add tests in a `tests/` subdirectory.
3.  Update `check_all.sh` to include your new tests.
4.  Update the root `README.md` and `shell_commands/` as appropriate.

## License

All tools are licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
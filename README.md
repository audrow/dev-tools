# Developer Tools

This repository is a collection of tools to support and streamline development workflows.

## Tools

*   [**Text Aggregator**](./text_aggregator_tool/README.md): A command-line tool to find and combine text from multiple files into a single file or the clipboard. Designed to make working with LLMs easier by quickly gathering context from your codebase.
*   [**Command Reloader**](./command_reloader_tool/README.md): A smart watcher that restarts a command when git-tracked files change. Features debounce, port/regex waiting, and remote trigger support for browser refreshing.

## Development

We use `black` for code formatting. You can run it on the whole repository or individual tools.

**To format the code:**

1.  **Install Black:**
    ```bash
    pip install black
    ```

2.  **Run Black:**
    ```bash
    # Run on the whole repo
    black .
    ```

## License

All tools are licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
# Text Aggregator

A simple text aggregator that takes a path (supports wildcards `**` and `*`) and file extensions to include or exclude, and puts all of the text into either a file or the user's clipboard (clipboard by default).

## Installation

### Prerequisites

You need `python3` and `pip` installed.

For Linux users (especially headless servers), you also need `xclip` or `xsel` for clipboard functionality:
```bash
sudo apt-get install -y xclip
```

### Install with pip

You can install the tool directly from the source code.

#### User Installation (Recommended)
This installs the `text-aggregator` command to your local bin directory (usually `~/.local/bin`). Ensure this is in your PATH.

```bash
pip install .
```

#### Developer Installation
If you want to modify the code, install in editable mode:

```bash
pip install -e .
```

### Managed Systems / Manual Setup

If you are on a managed system where you cannot install packages globally or prefer a manual setup, you have two options.
**Note:** Both options require `pyperclip` to be installed (e.g., `pip install --user pyperclip`) and `xclip`/`xsel` for Linux users.

#### Option 1: Copy to User Executable Folder

You can copy the script to your user's binary directory (e.g., `~/.local/bin`) so it's available in your PATH.

1.  Make the script executable:
    ```bash
    chmod +x text_aggregator/aggregator.py
    ```
2.  Copy it to your local bin folder:
    ```bash
    mkdir -p ~/.local/bin
    cp text_aggregator/aggregator.py ~/.local/bin/text-aggregator
    ```
3.  Ensure `~/.local/bin` is in your PATH. You can then run:
    ```bash
    text-aggregator "**/*.txt"
    ```

#### Option 2: Create a Bash Alias

You can create an alias in your shell configuration (e.g., `.bashrc` or `.zshrc`) that points to the script in its current location.

1.  Open your config file:
    ```bash
    nano ~/.bashrc
    ```
2.  Add the following line (replace `/path/to/...` with the actual path):
    ```bash
    alias text-aggregator="python3 /path/to/intr_dev_tools/text_aggregator_tool/text_aggregator/aggregator.py"
    ```
3.  Reload your configuration:
    ```bash
    source ~/.bashrc
    ```

## Usage

Once installed, you can use the `text-aggregator` command from your terminal.

### Basic Usage

Aggregate all `.txt` files in the current directory and subdirectories, and copy the content to your clipboard:
```bash
text-aggregator "**/*.txt"
```
*Output:*
```text
Found 2 files:
  - file1.txt
  - sub/file2.txt
--------------------
Successfully copied to clipboard (150 characters)
```

You can also pass multiple files or patterns directly (shell expansion):
```bash
text-aggregator src/*.py tests/*.py
```

### Options

| Option | Short | Description | Example |
| :--- | :--- | :--- | :--- |
| `path_patterns` | | **Required.** One or more patterns or file paths. | `"src/**/*.py"` |
| `--include-extensions` | `-i` | List of extensions to include. Leading dot is optional. | `-i py md` |
| `--exclude-extensions` | `-e` | List of extensions to exclude. Leading dot is optional. | `-e log tmp` |
| `--exclude-directories`| `-d` | List of directory names to exclude. | `-d node_modules venv` |
| `--output-file` | `-o` | Write to file instead of clipboard. | `-o combined.txt` |
| `--no-copy` | | Do not copy to clipboard. | `--no-copy` |
| `--stdout` | `-s` | Print text to stdout (implies --no-copy). | `-s` |

> **Note on Quotes:** Using quotes (e.g., `"**/*.py"`) allows the script to handle recursive globbing internally. Omitting quotes (e.g., `**/*.py`) relies on your shell's expansion, which might behave differently depending on your shell settings (like `globstar` in bash).

### Configuration File

You can customize the tool's default behavior using a `.text_aggregator.json` file. The tool looks for configuration in two locations:

1.  **Package Default:** Located within the tool's installation directory. This provides sensible defaults (like excluding `node_modules`, `venv`, etc.).
2.  **Global:** Your home directory (`~/.text_aggregator.json`). This allows you to set your personal preferences across all projects.

**Example `.text_aggregator.json`:**
```json
{
  "exclude_directories": ["node_modules", "venv", "dist", "custom_ignore"],
  "include_extensions": ["py", "md", "txt"],
  "exclude_extensions": ["log", "tmp"],
  "output_file": null,
  "no_copy": false,
  "stdout": false
}
```

*   `output_file`: (string/null) Default path to write output to.
*   `no_copy`: (boolean) If true, disables clipboard copying by default.
*   `stdout`: (boolean) If true, prints to standard output by default.

**Precedence:**
Command-line arguments **>** Global Config (`~/`) **>** Package Default.

*Note: Global configuration overrides package defaults. Configuration in the current working directory is not supported to ensure consistent behavior regardless of where you run the tool.*

### Examples

**1. Aggregate Python and Markdown files (using short flags):**
```bash
text-aggregator "**/*" -i py md
```

**2. Exclude log files and a custom directory:**
```bash
text-aggregator "logs/**" -e log -d archive
```

**3. Save to a file instead of clipboard:**
```bash
text-aggregator "src/**/*.js" -o all_scripts.js
```

### Headless Environments (VS Code Remote, SSH, Docker)

If you see `Error: Could not copy to clipboard`, your environment likely lacks a display for the clipboard.

**Workarounds:**

1.  **Print to terminal:** Use `-s` or `--stdout` and copy manually or pipe to another tool.
    ```bash
    text-aggregator "**/*.py" -s
    
    # Pipe to VS Code editor
    text-aggregator "**/*.py" -s | code -
    ```

2.  **Save to file:**
    ```bash
    text-aggregator "**/*.py" -o output.txt
    ```

3.  **Disable copy:**
    ```bash
    text-aggregator "**/*.py" --no-copy
    ```

---

## Usage as a Python Module

You can also use this tool within your Python scripts.

```python
from text_aggregator.aggregator import aggregate_text

# Aggregate all text files in current directory and subdirectories
# Note: no_copy=True prevents modifying the clipboard during script execution
text, files = aggregate_text(["**/*.txt"], no_copy=True)

# Print the aggregated text
if text:
    print(f"Aggregated {len(files)} files.")
    print(text)
```

### `aggregate_text` Function

```python
def aggregate_text(
    path_patterns: List[str],
    include_extensions: Optional[List[str]] = None,
    exclude_extensions: Optional[List[str]] = None,
    exclude_directories: Optional[List[str]] = None,
    output_file: Optional[str] = None,
    no_copy: bool = False,
) -> Tuple[Optional[str], List[str]]:
```

- **Returns:** A tuple containing:
    1. The aggregated text as a string (or `None` if `output_file` is provided).
    2. A list of processed file paths.

## Testing

The project includes a suite of unit tests. To run them, navigate to the `text_aggregator_tool` directory and use the following command:

```bash
python3 -m unittest tests/test_aggregator.py
```

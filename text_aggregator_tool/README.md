# Text Aggregator

A simple text aggregator that takes a path (supports wildcards `**` and `*`) and file extensions to include or exclude, and puts all of the text into either a file or the user's clipboard (clipboard by default).

## Quickstart

The fastest way to get running on any system:

1.  **Install Dependencies:**
    ```bash
    pip install --user pyperclip
    sudo apt-get install -y xclip  # Linux only
    ```
2.  **Add Alias:** Add this to your `~/.bashrc` (adjust the path to where you cloned this repo):
    ```bash
    alias ta="python3 /path/to/text_aggregator_tool/text_aggregator/aggregator.py"
    ```
3.  **Run:**
    ```bash
    ta -i py,md  # Aggregates all .py and .md files in the current directory tree
    ```

**Quickstart for SSH / VS Code Remote:**
If you are working remotely and want to open the result in a new VS Code tab:
```bash
ta -s | code -
```

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

### Installation on Managed Systems (e.g. Google Cloud Shell, Corporate Laptop)

If you are on a managed system where you cannot install packages globally or prefer a manual setup, you have two options.

**Recommendation:** Using a Bash Alias (Option 2) is often the easiest and least intrusive method.

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

Aggregate all files in the current directory and subdirectories (defaulting to `**/*`), and copy the content to your clipboard:
```bash
text-aggregator
```

You can also specify patterns:
```bash
text-aggregator **/*.txt
```
*Output:*
```text
Found 2 files:
  - file1.txt
  - sub/file2.txt
--------------------
Successfully copied to clipboard (150 characters)
```

### Options

| Option | Short | Description | Example |
| :--- | :--- | :--- | :--- |
| `path_patterns` | | One or more patterns or file paths. Defaults to `**/*`. | `"src/**/*.py"` |
| `--include-extensions` | `-i` | List of extensions to include. Comma-separated or space-separated. | `-i py,md,txt` |
| `--exclude-extensions` | `-e` | List of extensions to exclude. Comma-separated or space-separated. | `-e log,tmp` |
| `--exclude-directories`| `-d` | List of directory names to exclude. | `-d node_modules venv` |
| `--output-file` | `-o` | Write to file instead of clipboard. | `-o combined.txt` |
| `--no-copy` | | Do not copy to clipboard. | `--no-copy` |
| `--stdout` | `-s` | Print text to stdout (implies --no-copy). | `-s` |

### Configuration

The tool uses a hierarchical configuration system. You can customize defaults using a `.text_aggregator.json` file.

#### Configuration Locations
1.  **Package Default:** Bundled with the source code. It contains the base exclusions (like `node_modules`, `.git`).
2.  **User Global:** Located at `~/.text_aggregator.json`. This is where you should put your personal preferences.

**Quick Setup (Global Config):**
Run this command to create a basic configuration in your home directory:
```bash
cat <<EOF > ~/.text_aggregator.json
{
  "exclude_directories": ["node_modules", "venv", ".venv", "__pycache__", ".git", "build", "dist"],
  "include_extensions": [],
  "exclude_extensions": [],
  "output_file": null,
  "no_copy": false,
  "stdout": false
}
EOF
```

#### Configuration Keys
| Key | Type | Description |
| :--- | :--- | :--- |
| `exclude_directories` | `list` | Directory names to skip (e.g., `["venv", "node_modules"]`). |
| `include_extensions` | `list` | Extensions to include (e.g., `["py", "txt"]`). |
| `exclude_extensions` | `list` | Extensions to ignore (e.g., `["log"]`). |
| `output_file` | `string`\|`null` | Default file path for output. |
| `no_copy` | `boolean` | If `true`, disables clipboard copy by default. |
| `stdout` | `boolean` | If `true`, prints to terminal by default. |

**Example `~/.text_aggregator.json`:**
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

**Precedence:**
`Command-line arguments` **>** `Global Config (~/)` **>** `Package Default`

### Examples

**1. Aggregate Python and Markdown files (using comma-separated extensions):**
```bash
text-aggregator -i py,md
```

**2. Exclude log and temporary files:**
```bash
text-aggregator -e log,tmp
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

## License

This project is licensed under the MIT License - see the [LICENSE](../LICENSE) file for details.


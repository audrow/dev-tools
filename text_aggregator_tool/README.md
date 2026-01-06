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

## Usage

Once installed, you can use the `text-aggregator` command from your terminal.

### Basic Usage

Aggregate all `.txt` files in the current directory and subdirectories, and copy the content to your clipboard:
```bash
text-aggregator "**/*.txt"
```
*Note: The aggregated text is also printed to standard output.*

### Options

| Option | Description | Example |
| :--- | :--- | :--- |
| `path_pattern` | **Required.** Glob pattern to match files. | `"src/**/*.py"` |
| `--include-extensions` | List of extensions to include. | `--include-extensions .py .md` |
| `--exclude-extensions` | List of extensions to exclude. | `--exclude-extensions .log .tmp` |
| `--output-file` | Write output to a file instead of clipboard/stdout. | `--output-file combined.txt` |

### Examples

**1. Aggregate Python and Markdown files:**
```bash
text-aggregator "**/*" --include-extensions .py .md
```

**2. Exclude log files:**
```bash
text-aggregator "logs/**" --exclude-extensions .log
```

**3. Save to a file instead of clipboard:**
```bash
text-aggregator "src/**/*.js" --output-file all_scripts.js
```

---

## Usage as a Python Module

You can also use this tool within your Python scripts.

```python
from text_aggregator.aggregator import aggregate_text

# Aggregate all text files in the current directory and subdirectories
text = aggregate_text("**/*.txt")

# Print the aggregated text
if text:
    print(text)
```

### `aggregate_text` Function

```python
def aggregate_text(
    path_pattern: str,
    include_extensions: Optional[List[str]] = None,
    exclude_extensions: Optional[List[str]] = None,
    output_file: Optional[str] = None,
) -> Optional[str]:
```

- **Returns:** The aggregated text as a string if no `output_file` is provided. If `output_file` is provided, it returns `None` after writing the file.

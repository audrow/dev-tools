# Text Aggregator

A simple text aggregator that takes a path (supports wildcards `**` and `*`) and file extensions to include or exclude (optional) and puts all of the text in either a file or to the user's clipboard (clipboard by default).

## Installation for Shell Command (Managed Environments)

To use this tool as a standalone shell command, follow these steps. This is the recommended method for systems with managed Python environments that prevent global `pip` installs.

### 1. Install Dependencies

The tool requires `pyperclip`. Install it using your system's package manager:

```bash
sudo apt-get update && sudo apt-get install -y python3-pyperclip xclip
```
*Note: `xclip` is needed for clipboard functionality on headless or minimal systems.*

### 2. Make the Script Executable

Make the core `aggregator.py` script runnable:

```bash
chmod +x text_aggregator/aggregator.py
```

### 3. Move to a Directory in your PATH

Move the script to a common location for user-installed executables and rename it for easier use. `/usr/local/bin` is a standard choice.

```bash
sudo mv text_aggregator/aggregator.py /usr/local/bin/text-aggregator
```

You can now run the tool from anywhere in your shell.

## Usage (as Shell Command)

```bash
# Aggregate all .txt files and copy the result to the clipboard
text-aggregator "**/*.txt"

# Aggregate specific file types and save to a file
text-aggregator "**/*" --include-extensions ".py" ".md" --output-file "code.txt"

# Exclude certain file types
text-aggregator "**/*" --exclude-extensions ".log" ".tmp"
```

---

## Usage (as Python Module)

If you prefer to use this as a Python module within a virtual environment:

```python
from text_aggregator import aggregate_text

# Aggregate all text files in the current directory and subdirectories
text = aggregate_text("**/*.txt")

# Print the aggregated text
print(text)
```

# Documentation

## `aggregate_text`

Aggregates text from files matching a given path pattern and file extensions.

### Arguments

- `path_pattern` (str): The path pattern to search for files (e.g., "**/*.txt").
- `include_extensions` (Optional[List[str]]): A list of file extensions to include (e.g., [".txt", ".md"]).
- `exclude_extensions` (Optional[List[str]]): A list of file extensions to exclude (e.g., [".log"]).
- `output_file` (Optional[str]): The path to a file to write the aggregated text to. If None, the text is copied to the clipboard.

### Returns

- (Optional[str]): The aggregated text as a string, or None if an output file is specified.
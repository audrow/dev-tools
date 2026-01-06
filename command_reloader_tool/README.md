# Command Reloader

A simple tool that watches for changes in git-tracked files (including untracked files shown in `git status`) and restarts a specified command.

This is useful for development workflows where you want to automatically restart a server or script when you modify code, leveraging `git` to efficiently detect relevant changes.

## Quickstart

The fastest way to get running:

1.  **Install:**
    ```bash
    pip install .
    ```
2.  **Add Alias (Optional):**
    ```bash
    alias cr="command-reloader"
    ```
3.  **Run:**
    ```bash
    cr -- python my_script.py
    ```

## Installation

### Prerequisites

- Python 3.7+
- Git

### Install with pip

You can install the tool directly from the source code.

#### User Installation (Recommended)
This installs the `command-reloader` command to your local bin directory.

```bash
pip install .
```

#### Developer Installation
If you want to modify the code, install in editable mode:

```bash
pip install -e .
```

### Installation on Managed Systems

If you are on a managed system where you cannot install packages globally, you can use a Bash Alias similar to the Text Aggregator tool.

1.  **Add Alias:** Add these to your `~/.bashrc` (adjust the path):
    ```bash
    alias command-reloader="python3 /path/to/intr_dev_tools/command_reloader_tool/command_reloader/reloader.py"
    alias cr="command-reloader"
    ```
2.  **Reload:**
    ```bash
    source ~/.bashrc
    ```

## Usage

Run the `command-reloader` followed by the command you want to run. It is recommended to use `--` to separate the reloader flags from your command's flags.

### Basic Usage

Restart a script whenever git-tracked files change:
```bash
command-reloader -- python my_script.py
```

### Options

| Option | Description | Example |
| :--- | :--- | :--- |
| `command` | The command to run and restart. Use `--` before it if it has flags. | `-- python app.py` |
| `--interval` | Check interval in seconds. Defaults to `1.0`. | `--interval 2.0` |

### Examples

**1. Restart a Python script:**
```bash
command-reloader -- python my_script.py
```

**2. Restart a Bazel run command:**
```bash
command-reloader -- bazel run //my:target
```

**3. With a custom check interval (default 1.0s):**
```bash
command-reloader --interval 2.0 -- ./start_server.sh
```

## Usage as a Python Module

You can also use the `CommandReloader` class within your Python scripts.

```python
from command_reloader.reloader import CommandReloader

reloader = CommandReloader("python my_script.py", interval=2.0)
reloader.run()
```

## Testing

The project includes a suite of unit tests. To run them, navigate to the `command_reloader_tool` directory and use the following command:

```bash
python3 -m unittest tests/test_reloader.py
```

## License

This project is licensed under the MIT License - see the [LICENSE](../LICENSE) file for details.
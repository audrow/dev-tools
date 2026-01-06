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

- Python 3.8+
- Git

### Install with pip

You can install the tool directly from the source code.

#### User Installation (Recommended)
This installs `command-reloader` and `command-trigger-listener`.

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
    alias command-trigger-listener="python3 /path/to/intr_dev_tools/command_reloader_tool/command_reloader/listener.py"
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
| `--debounce` | Debounce interval in seconds. Defaults to `0.5`. | `--debounce 1.0` |
| `--wait-for-port` | Wait for a localhost TCP port to open before running hooks. | `--wait-for-port 8080` |
| `--wait-for-regex` | Wait for a regex pattern in stdout/stderr before running hooks. | `--wait-for-regex "Server started"` |
| `--on-restart` | Shell command to run after start (and port check). | `--on-restart "notify-send Restarted"` |
| `--webhook-url` | URL to GET request after start. | `--webhook-url http://localhost:9999` |

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

**4. Wait for Log Message (Regex):**
Trigger refresh only after the server prints "Listening on":
```bash
command-reloader \
  --wait-for-regex "Listening on" \
  --webhook-url http://localhost:9999 \
  -- python server.py
```

**5. Browser Refresh (Local):**
Wait for port 8080 to be ready, then trigger a browser refresh (Linux example using `xdotool`).

```bash
command-reloader \
  --wait-for-port 8080 \
  --on-restart "xdotool search --onlyvisible --class chrome windowfocus key F5" \
  -- python server.py
```

---

## Complete Remote Development Guide (Step-by-Step)

This guide shows how to set up automatic browser refreshing when you develop on a remote machine (SSH) but view the app on your local browser.

### 1. Setup Local Listener (Laptop/Desktop)

> **⚠️ VS CODE USERS: READ THIS FIRST**
>
> If you use VS Code Remote (SSH), it has a feature that **scans your terminal output** for port numbers. When you run a command mentioning port `9999` (like the examples below), VS Code aggressively auto-forwards it from Remote -> Local.
>
> This creates a conflict because we need the port open **Locally** to listen for the remote signal. The auto-forward blocks your local listener with "Address already in use".
>
> **BEFORE** running the listener:
> 1. Open the **"Ports"** tab in VS Code (bottom panel).
> 2. Find port `9999` and right-click -> **"Unforward Port."**
> 3. Ideally, disable `remote.ports.autoForward` in your settings or add `"remote.ports.attributes": { "9999": { "onAutoForward": "ignore" } }` to your `settings.json`.

You need to run a small script on your **local machine** that listens for the refresh signal.

**Option A: Install the Tool (Recommended)**
If you have Python installed locally:
```bash
pip install . 
# OR use the alias if you copied the repo locally
command-trigger-listener --port 9999 --app-port 8080
```

**Option B: No Install (Copy-Paste Scripts)**
Download or copy one of these standalone scripts:
*   **MacOS (Chrome):** [listeners/mac_listener.py](listeners/mac_listener.py)
*   **Linux (Chrome):** [listeners/linux_listener.py](listeners/linux_listener.py)

```bash
python3 mac_listener.py --app-port 8080
```

### 2. Connect via SSH
Connect to your remote machine with **Reverse Port Forwarding** (`-R`) for the listener and **Local Port Forwarding** (`-L`) for your app.

```bash
# Example: App on 8080, Listener on 9999
ssh -N -L 8080:localhost:8080 -R 9999:localhost:9999 user@remote-host
```

### 3. Run Reloader (Remote Machine)
On the remote machine, use `cr` (Command Reloader) to run your app. It will wait for the app port (8080) to be ready, then trigger the webhook (9999) to refresh your local browser.

```bash
cr --wait-for-port 8080 \
   --webhook-url http://localhost:9999 \
   -- bazel run //my:target
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
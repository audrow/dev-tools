#!/usr/bin/env python3
"""
Command Trigger Listener
------------------------
A universal listener for remote development reloading.
Run this on your LOCAL machine.

It listens for HTTP GET requests and triggers a browser refresh.
- macOS: Uses AppleScript to refresh the specific tab (background supported).
- Linux: Uses xdotool to focus Chrome and press F5.

Usage:
    command-trigger-listener --port 9999 --app-port 8080
"""

import http.server
import socketserver
import subprocess
import argparse
import sys
import os
import platform


# --- macOS Logic ---
def get_applescript(target_port):
    return f"""
    tell application "Google Chrome"
        repeat with w in windows
            repeat with t in tabs of w
                if URL of t contains ":{target_port}" then
                    reload t
                    return -- Stop after finding the first match
                end if
            end repeat
        end repeat
    end tell
    """


def trigger_mac(app_port):
    script = get_applescript(app_port)
    try:
        process = subprocess.Popen(
            ["osascript", "-"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        stdout, stderr = process.communicate(input=script)
        if process.returncode == 0:
            print(f"Triggered: Refreshed tab for port {app_port} (macOS).")
        else:
            print(f"AppleScript Error: {stderr}")
    except Exception as e:
        print(f"Error running AppleScript: {e}")


# --- Linux Logic ---
def trigger_linux(app_port):
    # Linux (xdotool) - Focus and F5
    cmd = "xdotool search --onlyvisible --class google-chrome windowactivate --sync key F5"
    try:
        subprocess.run(cmd, shell=True, check=True)
        print(f"Triggered: Refreshed Chrome active window (Linux).")
    except subprocess.CalledProcessError as e:
        print(f"Error running xdotool: {e}")
    except Exception as e:
        print(f"Error: {e}")


# --- Server Logic ---
class TriggerHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()

        system = self.server.target_os
        app_port = self.server.app_port

        if system == "darwin":
            trigger_mac(app_port)
        elif system == "linux":
            trigger_linux(app_port)
        else:
            print(f"Unsupported OS: {system}. No action taken.")

    def log_message(self, format, *args):
        pass  # Quiet


class ThreadedHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    pass


def main():
    parser = argparse.ArgumentParser(
        description="Listen for HTTP triggers and refresh browser."
    )
    parser.add_argument(
        "--port", type=int, default=9999, help="Listener port (default: 9999)."
    )
    parser.add_argument(
        "--app-port",
        type=int,
        default=8080,
        help="The port your app is running on (default: 8080).",
    )
    parser.add_argument(
        "--os", type=str, choices=["darwin", "linux"], help="Override OS detection."
    )

    args = parser.parse_args()

    target_os = args.os if args.os else platform.system().lower()

    server = ThreadedHTTPServer(("localhost", args.port), TriggerHandler)
    server.target_os = target_os
    server.app_port = args.app_port

    print(f"Listening on port {args.port}...")
    print(f"Target App Port: {args.app_port}")
    print(f"Detected OS: {target_os}")

    if target_os == "linux":
        print("Note: Requires 'xdotool' installed.")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nExiting...")
        server.server_close()
    except OSError as e:
        if e.errno == 48:
            print(f"\nError: Port {args.port} is already in use.")
            print("Tips:")
            print("  1. Check if another instance is running.")
            print(
                "  2. If using VS Code Remote, check if it's auto-forwarding this port (Ports tab)."
            )
        else:
            raise


if __name__ == "__main__":
    main()

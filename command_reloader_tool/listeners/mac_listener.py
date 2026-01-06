#!/usr/bin/env python3
"""
Mac Chrome Listener
-------------------
Run this script on your LOCAL machine (Mac).
It listens on port 9999 and refreshes Google Chrome when triggered.

Usage:
    python3 mac_listener.py
"""

import http.server
import subprocess

PORT = 9999
CMD = "osascript -e 'tell application \"Google Chrome\" to tell the active tab of its first window to reload'"

class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        try:
            subprocess.run(CMD, shell=True, check=True)
            print("Triggered: Refreshed Chrome.")
        except subprocess.CalledProcessError as e:
            print(f"Error running command: {e}")

    def log_message(self, format, *args):
        # Suppress default logging to keep output clean
        pass

if __name__ == "__main__":
    print(f"Listening on port {PORT}...")
    print(f"Target Command: {CMD}")
    try:
        http.server.HTTPServer(("localhost", PORT), Handler).serve_forever()
    except KeyboardInterrupt:
        print("\nExiting...")
    except OSError as e:
        if e.errno == 48:
            print(f"\nError: Port {PORT} is already in use.")
            print("Tips:")
            print("  1. Check if another instance of this script is running.")
            print("  2. If using VS Code Remote, check if it's auto-forwarding this port (Ports tab).")
        else:
            raise

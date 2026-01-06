#!/usr/bin/env python3
"""
Linux Chrome Listener
---------------------
Run this script on your LOCAL machine (Linux).
It listens on port 9999 and refreshes the Google Chrome window
serving your app (e.g., localhost:8080).

Prerequisites:
    sudo apt-get install xdotool

Usage:
    python3 linux_listener.py --port 9999 --app-port 8080
"""

import http.server
import subprocess
import argparse
import sys

def refresh_window(app_port):
    # Search for a Chrome window that likely contains the port in its title
    # Browsers often show "Title - Google Chrome", so this relies on the page title 
    # OR the user ensuring the port is visible/unique.
    # 
    # A more robust approach for Linux is tricky without browser extensions.
    # We will try to find a window with the class 'google-chrome' 
    # and send F5 to it. 
    #
    # Improved Strategy:
    # 1. Search for window with class 'google-chrome'
    # 2. Activate it (focus)
    # 3. Send F5
    # 4. (Optional) Switch back? That might be annoying.
    
    # Current best effort: Send F5 to the most recently used Chrome window
    # This avoids sending keys to VS Code or Terminal if they are focused.
    cmd = f"xdotool search --onlyvisible --class google-chrome windowactivate --sync key F5"
    return cmd

class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        
        # Note: Linux tab-specific reloading is hard without extensions.
        # We default to activating the main Chrome window and refreshing.
        cmd = refresh_window(self.server.app_port)
        
        try:
            subprocess.run(cmd, shell=True, check=True)
            print(f"Triggered: Refreshed Chrome (Active Window).")
        except subprocess.CalledProcessError as e:
            print(f"Error running xdotool: {e}")

    def log_message(self, format, *args):
        pass

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Listen for triggers and refresh Chrome.")
    parser.add_argument("--port", type=int, default=9999, help="Listener port (default: 9999).")
    parser.add_argument("--app-port", type=int, default=8080, help="Unused on Linux currently (placeholder).")
    
    args = parser.parse_args()
    
    server = http.server.HTTPServer(("localhost", args.port), Handler)
    server.app_port = args.app_port
    
    print(f"Listening on port {args.port}...")
    print("Mode: Activates Chrome window and presses F5.")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nExiting...")
    except OSError as e:
        if e.errno == 48:
            print(f"\nError: Port {args.port} is already in use.")
            print("Tips:")
            print("  1. Check if another instance is running.")
            print("  2. Check VS Code Ports tab for auto-forwarding.")
        else:
            raise
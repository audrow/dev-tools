#!/usr/bin/env python3
"""
Mac Chrome Listener
-------------------
Run this script on your LOCAL machine (Mac).
It listens on port 9999 and refreshes the specific Google Chrome tab
serving your app (e.g., localhost:8080), even if it's in the background.

Usage:
    python3 mac_listener.py --port 9999 --app-port 8080
"""

import http.server
import subprocess
import argparse
import sys

def get_applescript(target_port):
    # This AppleScript loops through all windows and tabs to find the one matching the port.
    # It reloads ONLY that tab.
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

class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        
        script = get_applescript(self.server.app_port)
        try:
            # Pass the script to osascript via stdin
            process = subprocess.Popen(['osascript', '-'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            stdout, stderr = process.communicate(input=script)
            
            if process.returncode == 0:
                print(f"Triggered: Refreshed tab for port {self.server.app_port}.")
            else:
                print(f"AppleScript Error: {stderr}")
                
        except Exception as e:
            print(f"Error running command: {e}")

    def log_message(self, format, *args):
        pass

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Listen for triggers and refresh specific Chrome tab.")
    parser.add_argument("--port", type=int, default=9999, help="Listener port (default: 9999).")
    parser.add_argument("--app-port", type=int, default=8080, help="The port your app is running on (to find the tab). Default: 8080.")
    
    args = parser.parse_args()
    
    server = http.server.HTTPServer(("localhost", args.port), Handler)
    server.app_port = args.app_port
    
    print(f"Listening on port {args.port}...")
    print(f"Targeting Chrome tab with URL containing ':{args.app_port}'")
    
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
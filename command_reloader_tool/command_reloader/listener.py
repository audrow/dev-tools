#!/usr/bin/env python3
import http.server
import socketserver
import subprocess
import argparse
import sys
import os

class TriggerHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Triggered")
        
        # Run the command
        cmd = self.server.trigger_command
        print(f"[TriggerListener] Received request. Executing: {cmd}")
        
        try:
            # We run without shell=True if possible, but for presets like xdotool with args, shell=True is easier
            subprocess.Popen(cmd, shell=True)
        except Exception as e:
            print(f"[TriggerListener] Failed to execute command: {e}")

    def log_message(self, format, *args):
        # Quiet logs
        pass

class ThreadedHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    pass

def main():
    parser = argparse.ArgumentParser(description="Listen for HTTP triggers and run a local command.")
    parser.add_argument("--port", type=int, default=9999, help="Port to listen on (default: 9999).")
    parser.add_argument("--command", type=str, help="Shell command to run when triggered.")
    parser.add_argument("--chrome-refresh", action="store_true", help="Preset: Refreshes the active Chrome window (Linux/xdotool).")
    
    args = parser.parse_args()
    
    command = args.command
    if args.chrome_refresh:
        command = "xdotool search --onlyvisible --class chrome windowfocus key F5"
        
    if not command:
        print("Error: Must specify --command or a preset (e.g. --chrome-refresh)")
        sys.exit(1)
        
    server = ThreadedHTTPServer(('localhost', args.port), TriggerHandler)
    server.trigger_command = command
    
    print(f"[TriggerListener] Listening on port {args.port}...")
    print(f"[TriggerListener] Command to run: {command}")
    print(f"[TriggerListener] Trigger URL: http://localhost:{args.port}")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[TriggerListener] Exiting...")
        server.server_close()

if __name__ == "__main__":
    main()

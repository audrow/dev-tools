#!/usr/bin/env python3
import subprocess
import time
import os
import argparse
import sys
import signal
import socket
import urllib.request
import urllib.error
from typing import Dict, Optional

class CommandReloader:
    def __init__(self, command: str, interval: float = 1.0, wait_for_port: Optional[int] = None, on_restart: Optional[str] = None, debounce_interval: float = 0.5, webhook_url: Optional[str] = None):
        self.command = command
        self.interval = interval
        self.wait_for_port = wait_for_port
        self.on_restart = on_restart
        self.debounce_interval = debounce_interval
        self.webhook_url = webhook_url
        
        self.process: Optional[subprocess.Popen] = None
        self.last_snapshot: Dict[str, float] = {}
        
        # State Machine Variables
        self.pending_restart = False
        self.last_change_time = 0.0
        self.post_start_state = "IDLE" # IDLE, WAITING_FOR_PORT, DONE
        self.post_start_start_time = 0.0
        self.port_timeout = 30.0

    def _get_git_root(self) -> str:
        try:
            return subprocess.check_output(
                ["git", "rev-parse", "--show-toplevel"], 
                stderr=subprocess.DEVNULL
            ).decode("utf-8").strip()
        except subprocess.CalledProcessError:
            print("Error: Current directory is not part of a git repository.")
            sys.exit(1)

    def _get_snapshot(self) -> Dict[str, float]:
        """
        Returns a dictionary of {filename: mtime} for files currently 
        showing up in git status.
        """
        snapshot = {}
        try:
            cmd = ["git", "status", "--porcelain", "-z"]
            output = subprocess.check_output(cmd, stderr=subprocess.DEVNULL)
            
            parts = output.split(b'\0')
            i = 0
            while i < len(parts):
                entry = parts[i]
                if not entry:
                    i += 1
                    continue
                
                text = entry.decode("utf-8", errors="ignore")
                if len(text) < 3:
                    i += 1
                    continue

                status = text[:2]
                path = text[3:]
                
                if status.strip().startswith("R"):
                    snapshot[f"OLD:{path}"] = -1
                    i += 1
                    if i < len(parts):
                        new_path = parts[i].decode("utf-8", errors="ignore")
                        if os.path.exists(new_path):
                            snapshot[new_path] = os.path.getmtime(new_path)
                        else:
                            snapshot[new_path] = -1
                else:
                    if os.path.exists(path):
                        snapshot[path] = os.path.getmtime(path)
                    else:
                        snapshot[path] = -1
                
                i += 1
                
        except Exception:
            pass
        return snapshot

    def _check_port(self, port: int) -> bool:
        """Checks if a TCP port is open on localhost (non-blocking)."""
        try:
            with socket.create_connection(("localhost", port), timeout=0.1):
                return True
        except (ConnectionRefusedError, socket.timeout, OSError):
            return False

    def _start_main_process(self):
        """Starts the main command process."""
        self.stop_process() # Ensure clean slate
        
        print(f"\n[CommandReloader] Starting: {self.command}")
        sys.stdout.flush()
        try:
            self.process = subprocess.Popen(
                self.command, 
                shell=True,
                preexec_fn=os.setsid
            )
        except Exception as e:
            print(f"[CommandReloader] Failed to start process: {e}")

    def _init_post_start_sequence(self):
        """Initializes the post-start sequence (waiting for port, etc)."""
        if self.wait_for_port:
            print(f"[CommandReloader] Waiting for port {self.wait_for_port}...")
            self.post_start_state = "WAITING_FOR_PORT"
            self.post_start_start_time = time.time()
        else:
            self._trigger_success_actions()
            self.post_start_state = "DONE"

    def _trigger_success_actions(self):
        """Runs webhooks and on-restart hooks."""
        # 1. Webhook
        if self.webhook_url:
            self._call_webhook()

        # 2. Shell Hook
        if self.on_restart:
            print(f"[CommandReloader] Running on-restart command: {self.on_restart}")
            try:
                subprocess.run(self.on_restart, shell=True)
            except Exception as e:
                print(f"[CommandReloader] Failed to run on-restart command: {e}")

    def _call_webhook(self):
        """Sends a GET request to the configured webhook URL."""
        print(f"[CommandReloader] Triggering webhook: {self.webhook_url}")
        try:
            with urllib.request.urlopen(self.webhook_url, timeout=2.0) as response:
                pass # Success
        except Exception as e:
            print(f"[CommandReloader] Webhook failed: {e}")

    def stop_process(self):
        if self.process:
            print(f"\n[CommandReloader] Stopping process...")
            try:
                os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
                try:
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    print(f"[CommandReloader] Process didn't exit, sending SIGKILL...")
                    os.killpg(os.getpgid(self.process.pid), signal.SIGKILL)
            except ProcessLookupError:
                pass
            except Exception as e:
                print(f"[CommandReloader] Error stopping process: {e}")
            self.process = None

    def run(self):
        self._get_git_root()
        self.last_snapshot = self._get_snapshot()
        
        # Initial trigger
        self.pending_restart = True
        self.last_change_time = time.time() - self.debounce_interval # Start immediately
        
        try:
            while True:
                time.sleep(min(self.interval, 0.1))
                
                # 1. Check for Changes
                current_snapshot = self._get_snapshot()
                if current_snapshot != self.last_snapshot:
                    print(f"\n[CommandReloader] Change detected.")
                    sys.stdout.flush()
                    
                    self.last_snapshot = current_snapshot
                    self.last_change_time = time.time()
                    self.pending_restart = True
                    
                    if self.post_start_state == "WAITING_FOR_PORT":
                         self.post_start_state = "IDLE"
                    
                    if self.process:
                         self.stop_process()

                # 2. Handle Debounce & Restart
                if self.pending_restart:
                    if time.time() - self.last_change_time >= self.debounce_interval:
                        print(f"[CommandReloader] Debounce settled. Restarting...")
                        self.pending_restart = False
                        self._start_main_process()
                        self._init_post_start_sequence()
                    else:
                        continue

                # 3. Handle Post-Start Sequence
                if self.post_start_state == "WAITING_FOR_PORT":
                    if self._check_port(self.wait_for_port):
                        print(f"[CommandReloader] Port {self.wait_for_port} is ready.")
                        self._trigger_success_actions()
                        self.post_start_state = "DONE"
                    elif time.time() - self.post_start_start_time > self.port_timeout:
                        print(f"[CommandReloader] Timed out waiting for port {self.wait_for_port}.")
                        self.post_start_state = "DONE"
                
        except KeyboardInterrupt:
            print("\n[CommandReloader] Exiting...")
            self.stop_process()

def main():
    parser = argparse.ArgumentParser(description="Watch for git file changes and restart a command.")
    parser.add_argument("--interval", type=float, default=1.0, help="Check interval in seconds (default: 1.0).")
    parser.add_argument("--debounce", type=float, default=0.5, help="Debounce interval in seconds (default: 0.5).")
    parser.add_argument("--wait-for-port", type=int, help="Wait for this TCP port on localhost to be open before running hooks.")
    parser.add_argument("--on-restart", type=str, help="Shell command to run after the main command starts (and port is ready).")
    parser.add_argument("--webhook-url", type=str, help="URL to request (GET) after successful start. Useful for remote triggers.")
    parser.add_argument("command", type=str, nargs=argparse.REMAINDER, help="The command to run.")
    
    args = parser.parse_args()
    
    if not args.command:
        print("Error: No command specified.")
        print("Usage: command-reloader [options] -- <command>")
        print("Example: command-reloader -- python main.py")
        sys.exit(1)
        
    command_str = " ".join(args.command)
    if command_str.startswith("-- "):
        command_str = command_str[3:]
    elif command_str == "--":
        print("Error: No command specified after --")
        sys.exit(1)

    reloader = CommandReloader(
        command_str, 
        interval=args.interval,
        wait_for_port=args.wait_for_port,
        on_restart=args.on_restart,
        debounce_interval=args.debounce,
        webhook_url=args.webhook_url
    )
    reloader.run()

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
import subprocess
import time
import os
import argparse
import sys
import signal
from typing import Dict, Optional

class CommandReloader:
    def __init__(self, command: str, interval: float = 1.0):
        self.command = command
        self.interval = interval
        self.process: Optional[subprocess.Popen] = None
        self.last_snapshot: Dict[str, float] = {}

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
            # git status --porcelain -z gives reliable machine-readable output
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
                
                # Handle rename: if status starts with R, the NEXT part is the new path.
                if status.strip().startswith("R"):
                    # Record the old path as part of state (it's gone/changed)
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

    def start_process(self):
        if self.process:
            self.stop_process()
        
        print(f"\n[CommandReloader] Starting: {self.command}")
        sys.stdout.flush()
        # Use shell=True to handle complex commands with pipes/args easily
        # Use preexec_fn=os.setsid to allow killing the whole process group
        try:
            self.process = subprocess.Popen(
                self.command, 
                shell=True,
                preexec_fn=os.setsid
            )
        except Exception as e:
            print(f"[CommandReloader] Failed to start process: {e}")

    def stop_process(self):
        if self.process:
            print(f"\n[CommandReloader] Stopping process...")
            try:
                # Send SIGTERM to the process group
                os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
                try:
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    print(f"[CommandReloader] Process didn't exit, sending SIGKILL...")
                    os.killpg(os.getpgid(self.process.pid), signal.SIGKILL)
            except ProcessLookupError:
                pass # Already dead
            except Exception as e:
                print(f"[CommandReloader] Error stopping process: {e}")
            self.process = None

    def run(self):
        self._get_git_root() # Ensure we are in a repo
        
        self.start_process()
        self.last_snapshot = self._get_snapshot()
        
        try:
            while True:
                time.sleep(self.interval)
                current_snapshot = self._get_snapshot()
                
                # Compare snapshots
                if current_snapshot != self.last_snapshot:
                    print(f"\n[CommandReloader] File changes detected.")
                    # Update snapshot BEFORE restarting to avoid loops if restart causes ephemeral file changes
                    # (though those should be ignored by gitignore ideally)
                    self.last_snapshot = current_snapshot
                    self.start_process()
                
        except KeyboardInterrupt:
            print("\n[CommandReloader] Exiting...")
            self.stop_process()

def main():
    parser = argparse.ArgumentParser(description="Watch for git file changes and restart a command.")
    parser.add_argument("--interval", type=float, default=1.0, help="Check interval in seconds.")
    parser.add_argument("command", type=str, nargs=argparse.REMAINDER, help="The command to run.")
    
    args = parser.parse_args()
    
    if not args.command:
        print("Error: No command specified.")
        print("Usage: command-reloader [options] -- <command>")
        print("Example: command-reloader -- python main.py")
        sys.exit(1)
        
    # Join the command parts if it was split
    command_str = " ".join(args.command)
    
    # Handle the case where the user used "--" to separate flags
    # argparse might consume "--" if it's not strictly handled, or put it in command list
    if command_str.startswith("-- "):
        command_str = command_str[3:]
    elif command_str == "--":
        print("Error: No command specified after --")
        sys.exit(1)

    reloader = CommandReloader(command_str, interval=args.interval)
    reloader.run()

if __name__ == "__main__":
    main()

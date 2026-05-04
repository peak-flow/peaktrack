#!/usr/bin/env python3
"""Daemon: check GitHub commits every 6 hours and append to commit_log.md."""

import os
import sys
import time
import subprocess
from pathlib import Path

INTERVAL_SECONDS = 6 * 60 * 60  # 6 hours
SCRIPT = Path(__file__).parent / "check_commits.py"
PID_FILE = Path(__file__).parent / "commit_watcher.pid"
LOG_FILE = Path(__file__).parent / "check_commits.log"


def run_check():
    env = os.environ.copy()
    with LOG_FILE.open("a") as log:
        result = subprocess.run(
            [sys.executable, str(SCRIPT)],
            env=env,
            stdout=log,
            stderr=log,
        )
    return result.returncode


def main():
    if "--stop" in sys.argv:
        if PID_FILE.exists():
            pid = int(PID_FILE.read_text().strip())
            try:
                os.kill(pid, 15)
                PID_FILE.unlink()
                print(f"Stopped watcher (PID {pid})")
            except ProcessLookupError:
                print("Watcher was not running.")
                PID_FILE.unlink(missing_ok=True)
        else:
            print("No PID file found — watcher may not be running.")
        return

    if "--status" in sys.argv:
        if PID_FILE.exists():
            pid = int(PID_FILE.read_text().strip())
            try:
                os.kill(pid, 0)
                print(f"Watcher is running (PID {pid})")
            except ProcessLookupError:
                print("Watcher PID file exists but process is dead.")
        else:
            print("Watcher is not running.")
        return

    if not os.environ.get("GITHUB_TOKEN"):
        print("ERROR: Set GITHUB_TOKEN before starting the watcher.")
        print("  export GITHUB_TOKEN=ghp_your_token_here")
        print("  python3 commit_watcher.py &")
        sys.exit(1)

    PID_FILE.write_text(str(os.getpid()))
    print(f"Commit watcher started (PID {os.getpid()}). Logs → {LOG_FILE}")
    print(f"Running first check now, then every {INTERVAL_SECONDS // 3600}h ...")

    try:
        while True:
            rc = run_check()
            if rc != 0:
                with LOG_FILE.open("a") as log:
                    log.write(f"[watcher] check_commits.py exited with code {rc}\n")
            time.sleep(INTERVAL_SECONDS)
    except KeyboardInterrupt:
        pass
    finally:
        PID_FILE.unlink(missing_ok=True)
        print("Watcher stopped.")


if __name__ == "__main__":
    main()

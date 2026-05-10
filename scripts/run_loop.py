#!/usr/bin/env python3
"""
Runs check_commits.py every 6 hours in the foreground.
Use inside a tmux/screen session or as a background process:

    nohup python3 scripts/run_loop.py &

Override the interval with the HOURS env var (same as check_commits.py).
"""

import os
import subprocess
import sys
import time
from pathlib import Path

HOURS = int(os.environ.get("HOURS", "6"))
INTERVAL = HOURS * 3600
SCRIPT = Path(__file__).parent / "check_commits.py"


def run_once() -> None:
    result = subprocess.run([sys.executable, str(SCRIPT)], check=False)
    if result.returncode != 0:
        print(f"[run_loop] check_commits.py exited with code {result.returncode}", flush=True)


def main() -> None:
    print(f"[run_loop] Starting — will check every {HOURS}h. Press Ctrl-C to stop.", flush=True)
    run_once()
    while True:
        print(f"[run_loop] Sleeping {HOURS}h until next check ...", flush=True)
        time.sleep(INTERVAL)
        run_once()


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Background runner: executes check_commits.py every 6 hours.
Start with: nohup python3 run_tracker.py > /tmp/tracker.log 2>&1 &
"""
import subprocess
import time
import sys
import os
from pathlib import Path

INTERVAL_HOURS = 6
SCRIPT = Path(__file__).parent / "check_commits.py"


def run_check():
    print(f"Running commit check at {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}", flush=True)
    env = os.environ.copy()
    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        env=env,
        capture_output=True,
        text=True,
    )
    print(result.stdout, flush=True)
    if result.stderr:
        print("STDERR:", result.stderr, flush=True)


if __name__ == "__main__":
    print(f"Tracker started. Running every {INTERVAL_HOURS}h. PID={os.getpid()}", flush=True)
    if not os.environ.get("GITHUB_TOKEN"):
        print("Warning: GITHUB_TOKEN not set. Only public repos will be accessible.", flush=True)

    while True:
        run_check()
        print(f"Next run in {INTERVAL_HOURS}h. Sleeping...", flush=True)
        time.sleep(INTERVAL_HOURS * 3600)

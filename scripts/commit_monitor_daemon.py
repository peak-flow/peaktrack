#!/usr/bin/env python3
"""
GitHub commit monitor daemon.
Runs check_commits.py every 6 hours, logs to scripts/daemon.log.
Start:  nohup python3 scripts/commit_monitor_daemon.py &
Stop:   kill $(cat scripts/daemon.pid)
"""

import os
import sys
import time
import signal
import subprocess
from pathlib import Path

INTERVAL_HOURS = 6
INTERVAL_SECONDS = INTERVAL_HOURS * 3600
SCRIPT_DIR = Path(__file__).parent
CHECK_SCRIPT = SCRIPT_DIR / "check_commits.py"
PID_FILE = SCRIPT_DIR / "daemon.pid"
LOG_FILE = SCRIPT_DIR / "daemon.log"


def log(msg: str):
    from datetime import datetime, timezone
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    line = f"[{ts}] {msg}\n"
    print(line, end="", flush=True)
    with open(LOG_FILE, "a") as f:
        f.write(line)


def run_check():
    log("Running commit check...")
    result = subprocess.run(
        [sys.executable, str(CHECK_SCRIPT)],
        capture_output=True,
        text=True,
        env=os.environ.copy(),
    )
    for line in result.stdout.splitlines():
        log(f"  {line}")
    if result.returncode != 0:
        for line in result.stderr.splitlines():
            log(f"  ERROR: {line}")
    log(f"Check complete (exit code {result.returncode}).")


def handle_signal(signum, frame):
    log(f"Received signal {signum}, shutting down.")
    PID_FILE.unlink(missing_ok=True)
    sys.exit(0)


def main():
    # Write PID file
    PID_FILE.write_text(str(os.getpid()))
    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    log(f"Commit monitor daemon started (PID {os.getpid()}). Interval: {INTERVAL_HOURS}h.")

    while True:
        run_check()
        log(f"Next check in {INTERVAL_HOURS} hours. Sleeping...")
        time.sleep(INTERVAL_SECONDS)


if __name__ == "__main__":
    main()

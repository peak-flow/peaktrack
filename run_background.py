#!/usr/bin/env python3
"""Run check_commits.py every 6 hours in the background.

Start with:  nohup python3 run_background.py &
Stop with:   kill $(cat .runner.pid)
"""

import os
import subprocess
import sys
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
INTERVAL_SECONDS = int(os.getenv("CHECK_HOURS", "6")) * 3600
PID_FILE = SCRIPT_DIR / ".runner.pid"


def main():
    PID_FILE.write_text(str(os.getpid()))
    print(f"Background runner started (PID {os.getpid()}). Interval: {INTERVAL_SECONDS // 3600}h")
    try:
        while True:
            print("Running commit check…", flush=True)
            subprocess.run(
                [sys.executable, str(SCRIPT_DIR / "check_commits.py")],
                check=False,
            )
            print(f"Sleeping {INTERVAL_SECONDS // 3600}h…", flush=True)
            time.sleep(INTERVAL_SECONDS)
    finally:
        PID_FILE.unlink(missing_ok=True)


if __name__ == "__main__":
    main()

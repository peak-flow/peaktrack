#!/usr/bin/env python3
"""
Polls GitHub every 6 hours, counts commits per repo, and appends a summary
to commit_log.md in the project root.

Usage:
    export GITHUB_TOKEN=ghp_...
    python3 scripts/commit_tracker_daemon.py &

Or run once:
    python3 scripts/commit_tracker_daemon.py --once
"""

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

# ── Configuration ─────────────────────────────────────────────────────────────
REPOS = [
    "peak-flow/peaktrack",
    # add more as "owner/repo"
]
INTERVAL_HOURS = 6
PROJECT_ROOT = Path(__file__).parent.parent
OUTPUT_FILE = PROJECT_ROOT / "commit_log.md"
# ─────────────────────────────────────────────────────────────────────────────


def github_get(path: str, token: str) -> list:
    url = f"https://api.github.com{path}"
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    })
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        print(f"  HTTP {e.code} for {url}", file=sys.stderr)
        return None


def count_commits(repo: str, since: datetime, until: datetime, token: str) -> int | str:
    owner, name = repo.split("/", 1)
    since_str = since.strftime("%Y-%m-%dT%H:%M:%SZ")
    until_str = until.strftime("%Y-%m-%dT%H:%M:%SZ")
    total = 0
    page = 1
    while True:
        data = github_get(
            f"/repos/{owner}/{name}/commits"
            f"?since={since_str}&until={until_str}&per_page=100&page={page}",
            token,
        )
        if data is None:
            return "error"
        total += len(data)
        if len(data) < 100:
            break
        page += 1
    return total


def run_check(token: str) -> None:
    now = datetime.now(timezone.utc)
    since = now - timedelta(hours=INTERVAL_HOURS)
    run_at = now.strftime("%Y-%m-%d %H:%M UTC")
    print(f"[{run_at}] Checking commits since {since.strftime('%H:%M UTC')} ...")

    rows: list[tuple[str, int | str]] = []
    grand_total = 0

    for repo in REPOS:
        result = count_commits(repo, since, now, token)
        rows.append((repo, result))
        print(f"  {repo}: {result}")
        if isinstance(result, int):
            grand_total += result

    lines = [
        "",
        f"## {run_at}",
        "",
        f"| Repository | Commits (last {INTERVAL_HOURS}h) |",
        "|------------|------------------------|",
    ]
    for repo, count in rows:
        lines.append(f"| `{repo}` | {count} |")
    lines.append("")
    lines.append(f"**Total: {grand_total} commit(s) across {len(REPOS)} repo(s)**")
    lines.append("")

    with OUTPUT_FILE.open("a") as f:
        f.write("\n".join(lines) + "\n")

    print(f"  Saved to {OUTPUT_FILE}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    args = parser.parse_args()

    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        print("ERROR: GITHUB_TOKEN environment variable is not set.", file=sys.stderr)
        sys.exit(1)

    if args.once:
        run_check(token)
        return

    print(f"Daemon started. Checking every {INTERVAL_HOURS} hours. Ctrl-C to stop.")
    while True:
        run_check(token)
        next_run = datetime.now(timezone.utc) + timedelta(hours=INTERVAL_HOURS)
        print(f"  Next check at {next_run.strftime('%Y-%m-%d %H:%M UTC')}")
        time.sleep(INTERVAL_HOURS * 3600)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Fetches commits from the last 6 hours for tracked GitHub repos and appends to commit-log.md."""

import json
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta

REPOS = ["peak-flow/peaktrack"]
LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "commit-log.md")
HOURS = 6


def fetch_commits(repo, since_iso, token):
    url = f"https://api.github.com/repos/{repo}/commits?since={since_iso}&per_page=100"
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "peaktrack-commit-logger",
    })
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def main():
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if not token:
        print("ERROR: GITHUB_TOKEN environment variable is not set.", file=sys.stderr)
        sys.exit(1)

    now = datetime.now(timezone.utc)
    since = now - timedelta(hours=HOURS)
    since_iso = since.strftime("%Y-%m-%dT%H:%M:%SZ")
    timestamp = now.strftime("%Y-%m-%d %H:%M UTC")

    lines = []
    for repo in REPOS:
        try:
            commits = fetch_commits(repo, since_iso, token)
        except urllib.error.HTTPError as e:
            lines.append(f"\n## {timestamp}\n")
            lines.append(f"- **Repository**: {repo}\n")
            lines.append(f"- **Error**: HTTP {e.code} — {e.reason}\n")
            continue
        except Exception as e:
            lines.append(f"\n## {timestamp}\n")
            lines.append(f"- **Repository**: {repo}\n")
            lines.append(f"- **Error**: {e}\n")
            continue

        lines.append(f"\n## {timestamp}\n")
        lines.append(f"- **Repository**: {repo}\n")
        lines.append(f"- **Commits in last {HOURS} hours**: {len(commits)}\n")
        for c in commits:
            sha = c["sha"][:7]
            author = (c.get("commit", {}).get("author") or {}).get("name", "unknown")
            message = (c.get("commit", {}).get("message") or "").splitlines()[0]
            lines.append(f"  - `[{sha}]` {author}: {message}\n")

    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, "w") as f:
            f.write("# GitHub Commit Log\n")

    with open(LOG_FILE, "a") as f:
        f.writelines(lines)

    print(f"Logged {len(REPOS)} repo(s) at {timestamp} → {LOG_FILE}")


if __name__ == "__main__":
    main()

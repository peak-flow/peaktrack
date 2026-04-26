#!/usr/bin/env python3
"""Fetch commits from the last 6 hours and append a summary to commit-log.md."""

import os
import sys
import urllib.request
import urllib.error
import json
from datetime import datetime, timezone, timedelta

LOG_FILE = os.path.join(os.path.dirname(__file__), "..", "commit-log.md")
REPOS = ["peak-flow/peaktrack"]
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_PAT")


def fetch_commits(owner: str, repo: str, since: str) -> list:
    url = f"https://api.github.com/repos/{owner}/{repo}/commits?since={since}&per_page=100"
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    if GITHUB_TOKEN:
        req.add_header("Authorization", f"Bearer {GITHUB_TOKEN}")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code} fetching {owner}/{repo}: {e.reason}", file=sys.stderr)
        return []


def build_entry(now: datetime, six_hours_ago: datetime) -> str:
    timestamp = now.strftime("%Y-%m-%d %H:%M:%S UTC")
    lines = [f"\n## {timestamp}"]

    for repo_path in REPOS:
        owner, repo = repo_path.split("/")
        commits = fetch_commits(owner, repo, six_hours_ago.strftime("%Y-%m-%dT%H:%M:%SZ"))
        lines.append(f"- **Repo**: {repo_path}")
        lines.append(f"- **Commits in last 6h**: {len(commits)}")
        if commits:
            lines.append("- **Commit SHAs and messages**:")
            for c in commits:
                sha = c["sha"][:7]
                msg = c["commit"]["message"].splitlines()[0]
                author = c["commit"]["author"]["name"]
                ts = c["commit"]["author"]["date"]
                lines.append(f"  - `{sha}` {msg} by {author} at {ts}")
        else:
            lines.append("- **Commit SHAs and messages**: *(none)*")

    return "\n".join(lines) + "\n"


def main():
    now = datetime.now(timezone.utc)
    six_hours_ago = now - timedelta(hours=6)

    entry = build_entry(now, six_hours_ago)

    log_path = os.path.abspath(LOG_FILE)
    if not os.path.exists(log_path):
        with open(log_path, "w") as f:
            f.write("# GitHub Commit Log\n")

    with open(log_path, "a") as f:
        f.write(entry)

    print(f"Appended entry to {log_path}")


if __name__ == "__main__":
    main()

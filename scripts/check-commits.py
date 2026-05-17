#!/usr/bin/env python3
"""
Checks peak-flow/peaktrack for commits in the last 6 hours and appends
a summary entry to commit-log.md.

Runs via cron: 0 */6 * * *
Uses the GitHub REST API (unauthenticated for public repos, or set GITHUB_TOKEN).
"""

import json
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta

REPO_OWNER = "peak-flow"
REPO_NAME = "peaktrack"
LOG_FILE = os.path.join(os.path.dirname(__file__), "..", "commit-log.md")
HOURS = 6


def gh_get(url: str) -> list:
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json", "User-Agent": "commit-logger/1.0"})
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code} fetching {url}: {e.reason}", file=sys.stderr)
        return []


def list_commits_since(owner: str, repo: str, branch: str, since: str) -> list:
    url = (
        f"https://api.github.com/repos/{owner}/{repo}/commits"
        f"?sha={branch}&since={since}&per_page=100"
    )
    return gh_get(url)


def list_branches(owner: str, repo: str) -> list[str]:
    url = f"https://api.github.com/repos/{owner}/{repo}/branches?per_page=100"
    data = gh_get(url)
    return [b["name"] for b in data] if isinstance(data, list) else []


def main():
    now = datetime.now(timezone.utc)
    since = (now - timedelta(hours=HOURS)).strftime("%Y-%m-%dT%H:%M:%SZ")

    branches = list_branches(REPO_OWNER, REPO_NAME)
    if not branches:
        print("No branches found or API error.", file=sys.stderr)
        sys.exit(1)

    # Collect all commits across all branches, deduplicated by SHA
    seen_shas: set[str] = set()
    all_commits: list[dict] = []

    for branch in branches:
        commits = list_commits_since(REPO_OWNER, REPO_NAME, branch, since)
        for c in commits:
            sha = c.get("sha", "")
            if sha not in seen_shas:
                seen_shas.add(sha)
                all_commits.append({
                    "sha": sha[:7],
                    "message": (c.get("commit", {}).get("message", "") or "").splitlines()[0],
                    "author": (
                        (c.get("commit", {}).get("author") or {}).get("name")
                        or (c.get("author") or {}).get("login")
                        or "unknown"
                    ),
                    "branch": branch,
                })

    count = len(all_commits)
    authors = sorted({c["author"] for c in all_commits}) or ["—"]
    messages = [f"`{c['sha']}` {c['message']} _(_{c['branch']}_)_" for c in all_commits] or ["—"]

    timestamp = now.strftime("%Y-%m-%d %H:%M UTC")
    entry_lines = [
        f"## {timestamp}",
        f"- **Repo**: {REPO_OWNER}/{REPO_NAME}",
        f"- **Commits in last {HOURS}h**: {count}",
        f"- **Authors**: {', '.join(authors)}",
        "- **Messages**:",
    ]
    for msg in messages:
        entry_lines.append(f"  - {msg}")
    entry_lines.append("")

    log_path = os.path.abspath(LOG_FILE)

    # Create file with header if missing
    if not os.path.exists(log_path):
        with open(log_path, "w") as f:
            f.write("# Commit Activity Log\n\n<!-- Auto-generated every 6 hours by check-commits.py -->\n\n")

    with open(log_path, "a") as f:
        f.write("\n".join(entry_lines) + "\n")

    print(f"[{timestamp}] Logged {count} commit(s) to {log_path}")


if __name__ == "__main__":
    main()

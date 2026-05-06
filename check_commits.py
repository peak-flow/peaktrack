#!/usr/bin/env python3
"""
check_commits.py — Fetch commits from the last 6 hours across all branches
of peak-flow/peaktrack and append a summary to commit-log.md.

Usage:
    GITHUB_TOKEN=your_token python3 check_commits.py

Or set GITHUB_TOKEN in your environment / .env file.
Cron example (every 6 hours):
    0 */6 * * * GITHUB_TOKEN=your_token /usr/bin/python3 /home/user/peaktrack/check_commits.py
"""

import os
import sys
import json
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from pathlib import Path

OWNER = "peak-flow"
REPO = "peaktrack"
LOG_FILE = Path(__file__).parent / "commit-log.md"
API_BASE = "https://api.github.com"

token = os.environ.get("GITHUB_TOKEN", "")
if not token:
    print("ERROR: GITHUB_TOKEN environment variable not set.", file=sys.stderr)
    sys.exit(1)

headers = {
    "Authorization": f"token {token}",
    "Accept": "application/vnd.github.v3+json",
    "User-Agent": "peaktrack-commit-logger",
}


def gh_get(path: str, params: dict = None) -> list | dict:
    url = f"{API_BASE}{path}"
    if params:
        query = "&".join(f"{k}={v}" for k, v in params.items())
        url = f"{url}?{query}"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code} for {url}", file=sys.stderr)
        return []


def get_branches() -> list[str]:
    branches = []
    page = 1
    while True:
        data = gh_get(f"/repos/{OWNER}/{REPO}/branches", {"per_page": "100", "page": str(page)})
        if not data:
            break
        branches.extend(b["name"] for b in data)
        if len(data) < 100:
            break
        page += 1
    return branches


def get_commits_since(branch: str, since: str) -> list[dict]:
    return gh_get(
        f"/repos/{OWNER}/{REPO}/commits",
        {"sha": branch, "since": since, "per_page": "100"},
    )


def main():
    now = datetime.now(timezone.utc)
    six_hours_ago = now - timedelta(hours=6)
    since_str = six_hours_ago.strftime("%Y-%m-%dT%H:%M:%SZ")
    now_str = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    display_now = now.strftime("%Y-%m-%d %H:%M UTC")

    print(f"Checking commits since {since_str} ...")

    branches = get_branches()
    print(f"Found {len(branches)} branches.")

    # Collect commits per branch; deduplicate by SHA across branches
    seen_shas: set[str] = set()
    branch_results: list[dict] = []
    total = 0

    for branch in branches:
        commits = get_commits_since(branch, since_str)
        if not commits:
            continue
        new_commits = [c for c in commits if c["sha"] not in seen_shas]
        if not new_commits:
            continue
        for c in new_commits:
            seen_shas.add(c["sha"])
        total += len(new_commits)
        branch_results.append({"branch": branch, "commits": new_commits})

    # Build markdown entry
    lines = [
        f"## {display_now}",
        f"",
        f"- **Repo:** {OWNER}/{REPO}",
        f"- **Commits in last 6h:** {total}",
        f"- **Window:** {since_str} → {now_str}",
    ]

    if total == 0:
        lines.append("- **Details:** No commits found in this window.")
    else:
        lines.append("- **Details:**")
        for br in branch_results:
            lines.append(f"  - **Branch `{br['branch']}`** — {len(br['commits'])} commit(s)")
            for c in br["commits"]:
                sha = c["sha"][:7]
                msg = c["commit"]["message"].splitlines()[0][:80]
                author = c["commit"]["author"]["name"]
                date = c["commit"]["author"]["date"][:16].replace("T", " ")
                lines.append(f"    - `{sha}` {date} **{author}**: {msg}")

    lines.append("")
    lines.append("---")
    lines.append("")

    entry = "\n".join(lines)
    print(entry)

    # Append to log file
    if not LOG_FILE.exists():
        LOG_FILE.write_text(
            f"# GitHub Commit Log — {OWNER}/{REPO}\n\nAuto-generated every 6 hours.\n\n---\n\n"
        )

    with LOG_FILE.open("a") as f:
        f.write(entry + "\n")

    print(f"Appended to {LOG_FILE}")


if __name__ == "__main__":
    main()

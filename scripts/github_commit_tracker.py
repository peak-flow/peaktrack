#!/usr/bin/env python3
"""
Checks GitHub for commits in the last 6 hours and appends a summary
to github_commit_log.md in the project root.

Config: scripts/github_tracker_config.json
  - github_token: your GitHub Personal Access Token
  - repos: list of "owner/repo" strings to track
  - hours: lookback window in hours (default 6)
"""

import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
import urllib.request
import urllib.error

SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
CONFIG_FILE = SCRIPT_DIR / "github_tracker_config.json"
LOG_FILE = PROJECT_DIR / "github_commit_log.md"

GITHUB_API = "https://api.github.com"


def load_config():
    if not CONFIG_FILE.exists():
        print(f"ERROR: Config file not found: {CONFIG_FILE}", file=sys.stderr)
        print("Create it with: {\"github_token\": \"YOUR_PAT\", \"repos\": [\"owner/repo\"]}", file=sys.stderr)
        sys.exit(1)
    with open(CONFIG_FILE) as f:
        return json.load(f)


def gh_get(path, token):
    url = f"{GITHUB_API}{path}"
    req = urllib.request.Request(url, headers={
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "peaktrack-commit-tracker/1.0",
    })
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"ERROR {e.code} from {url}: {body}", file=sys.stderr)
        return None


def fetch_commits_since(repo, since_iso, token):
    path = f"/repos/{repo}/commits?since={since_iso}&per_page=100"
    data = gh_get(path, token)
    if data is None:
        return []
    commits = []
    for item in data:
        sha = item["sha"][:7]
        author = (item.get("commit", {}).get("author") or {}).get("name", "unknown")
        message = (item.get("commit", {}).get("message") or "").splitlines()[0][:80]
        commits.append({"sha": sha, "author": author, "message": message})
    return commits


def ensure_log_header():
    if not LOG_FILE.exists():
        LOG_FILE.write_text("# GitHub Commit Log\n\nAuto-generated every 6 hours.\n\n")


def append_log_entry(entries):
    now = datetime.now(timezone.utc)
    lines = [f"\n## {now.strftime('%Y-%m-%d %H:%M UTC')}\n"]
    total = sum(e["count"] for e in entries)
    lines.append(f"**Total commits (last 6 h):** {total}\n")
    for entry in entries:
        lines.append(f"\n### `{entry['repo']}` — {entry['count']} commit(s)\n")
        if entry["commits"]:
            for c in entry["commits"]:
                lines.append(f"- `{c['sha']}` {c['author']}: {c['message']}\n")
        else:
            lines.append("- *(no commits)*\n")
    with open(LOG_FILE, "a") as f:
        f.writelines(lines)
    print(f"Appended entry: {total} commits across {len(entries)} repo(s).")


def main():
    cfg = load_config()
    token = cfg.get("github_token", "").strip()
    if not token or token == "YOUR_PAT_HERE":
        print("ERROR: Set 'github_token' in github_tracker_config.json", file=sys.stderr)
        sys.exit(1)

    repos = cfg.get("repos", ["peak-flow/peaktrack"])
    hours = int(cfg.get("hours", 6))
    since = (datetime.now(timezone.utc) - timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M:%SZ")

    ensure_log_header()
    entries = []
    for repo in repos:
        commits = fetch_commits_since(repo, since, token)
        entries.append({"repo": repo, "count": len(commits), "commits": commits})
        print(f"  {repo}: {len(commits)} commit(s) since {since}")

    append_log_entry(entries)


if __name__ == "__main__":
    main()

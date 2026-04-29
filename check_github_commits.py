#!/usr/bin/env python3
"""
Checks GitHub for commits in the last 6 hours across tracked repos
and appends a summary entry to github-commit-log.md.

Set GITHUB_TOKEN env var for authenticated requests (higher rate limits).
"""

import os
import sys
import json
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta

REPOS = ["peak-flow/peaktrack"]
LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "github-commit-log.md")
HOURS = 6


def github_get(path, token=None):
    url = f"https://api.github.com{path}"
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code} fetching {url}: {e.reason}", file=sys.stderr)
        return None


def get_commits_since(repo, since_iso, token=None):
    path = f"/repos/{repo}/commits?since={since_iso}&per_page=100"
    data = github_get(path, token)
    if data is None:
        return None
    commits = []
    for item in data:
        sha = item.get("sha", "")[:7]
        msg = ""
        author = ""
        if item.get("commit"):
            msg = item["commit"].get("message", "").split("\n")[0][:80]
            author = item["commit"].get("author", {}).get("name", "unknown")
        commits.append({"sha": sha, "message": msg, "author": author})
    return commits


def ensure_log_header():
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, "w") as f:
            f.write("# GitHub Commit Log\n\n")
            f.write("Automatically updated every 6 hours.\n\n")
            f.write("---\n\n")


def append_entry(now, results):
    ensure_log_header()
    timestamp = now.strftime("%Y-%m-%d %H:%M UTC")
    since = (now - timedelta(hours=HOURS)).strftime("%Y-%m-%d %H:%M UTC")
    total = sum(len(commits) for commits in results.values() if commits is not None)

    lines = [f"## {timestamp}\n"]
    lines.append(f"**Period:** {since} → {timestamp}  \n")
    lines.append(f"**Total commits:** {total}\n\n")

    for repo, commits in results.items():
        if commits is None:
            lines.append(f"### `{repo}` — ⚠️ fetch error\n\n")
            continue
        lines.append(f"### `{repo}` — {len(commits)} commit(s)\n\n")
        if commits:
            lines.append("| SHA | Author | Message |\n")
            lines.append("|-----|--------|---------|\n")
            for c in commits:
                msg = c["message"].replace("|", "\\|")
                lines.append(f"| `{c['sha']}` | {c['author']} | {msg} |\n")
        else:
            lines.append("_No commits in this period._\n")
        lines.append("\n")

    lines.append("---\n\n")

    with open(LOG_FILE, "a") as f:
        f.writelines(lines)

    print(f"[{timestamp}] Logged {total} commit(s) across {len(results)} repo(s) → {LOG_FILE}")


def load_token():
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        return token
    token_file = os.path.expanduser("~/.config/github_commit_checker/token")
    if os.path.exists(token_file):
        with open(token_file) as f:
            return f.read().strip()
    return None


def main():
    token = load_token()
    if not token:
        print("Warning: GITHUB_TOKEN not set — unauthenticated (60 req/hr limit)", file=sys.stderr)
        print("  Set token via: export GITHUB_TOKEN=<your_token>", file=sys.stderr)
        print(f"  Or save to: ~/.config/github_commit_checker/token", file=sys.stderr)

    now = datetime.now(timezone.utc)
    since = now - timedelta(hours=HOURS)
    since_iso = since.strftime("%Y-%m-%dT%H:%M:%SZ")

    results = {}
    for repo in REPOS:
        print(f"Checking {repo} since {since_iso}...")
        commits = get_commits_since(repo, since_iso, token)
        results[repo] = commits
        if commits is not None:
            print(f"  → {len(commits)} commit(s)")

    append_entry(now, results)


if __name__ == "__main__":
    main()

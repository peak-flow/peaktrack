#!/usr/bin/env python3
"""Check GitHub repos for commits in the last 6 hours and log to markdown."""

import os
import sys
import json
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta

REPOS = [
    "peak-flow/peaktrack",
]

OUTPUT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "github-commit-log.md")
WINDOW_HOURS = 6


def github_get(path, token):
    url = f"https://api.github.com{path}"
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "peaktrack-commit-checker",
    })
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def get_commits_since(repo, since_iso, token):
    path = f"/repos/{repo}/commits?since={since_iso}&per_page=100"
    try:
        commits = github_get(path, token)
        return commits if isinstance(commits, list) else []
    except urllib.error.HTTPError as e:
        print(f"  HTTP {e.code} for {repo}: {e.reason}", file=sys.stderr)
        return []


def ensure_header(path):
    if not os.path.exists(path):
        with open(path, "w") as f:
            f.write("# GitHub Commit Log\n\n")
            f.write("Auto-generated every 6 hours. Tracks commits across monitored repos.\n\n")
            f.write("---\n\n")


def append_entry(path, now, repo_data):
    total = sum(len(commits) for commits in repo_data.values())
    timestamp = now.strftime("%Y-%m-%d %H:%M UTC")
    window_start = (now - timedelta(hours=WINDOW_HOURS)).strftime("%Y-%m-%d %H:%M UTC")

    lines = [
        f"## {timestamp}\n",
        f"**Window:** {window_start} → {timestamp}  \n",
        f"**Total commits:** {total}\n\n",
    ]

    for repo, commits in repo_data.items():
        lines.append(f"### `{repo}` — {len(commits)} commit(s)\n\n")
        if commits:
            for c in commits:
                sha = c["sha"][:7]
                msg = c["commit"]["message"].splitlines()[0][:80]
                author = c["commit"]["author"]["name"]
                date = c["commit"]["author"]["date"][:10]
                lines.append(f"- `{sha}` {date} **{author}**: {msg}\n")
        else:
            lines.append("_No commits in this window._\n")
        lines.append("\n")

    lines.append("---\n\n")

    with open(path, "a") as f:
        f.writelines(lines)


def main():
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if not token:
        print("Error: GITHUB_TOKEN environment variable is not set.", file=sys.stderr)
        print("Export it before running: export GITHUB_TOKEN=your_token_here", file=sys.stderr)
        sys.exit(1)

    now = datetime.now(timezone.utc)
    since = now - timedelta(hours=WINDOW_HOURS)
    since_iso = since.strftime("%Y-%m-%dT%H:%M:%SZ")

    print(f"Checking commits since {since_iso} ...")

    repo_data = {}
    for repo in REPOS:
        print(f"  {repo} ...", end=" ", flush=True)
        commits = get_commits_since(repo, since_iso, token)
        repo_data[repo] = commits
        print(f"{len(commits)} commit(s)")

    ensure_header(OUTPUT_FILE)
    append_entry(OUTPUT_FILE, now, repo_data)

    total = sum(len(c) for c in repo_data.values())
    print(f"Done. {total} total commit(s) logged to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()

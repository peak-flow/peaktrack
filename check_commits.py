#!/usr/bin/env python3
"""Fetch commits from the last 6 hours and append a summary to commit-log.md."""

import json
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from pathlib import Path

REPOS = ["peak-flow/peaktrack"]
HOURS = 6
LOG_FILE = Path(__file__).parent / "commit-log.md"
TOKEN_FILE = Path.home() / ".github_token"

HEADER = """\
# GitHub Commit Log

Automatically tracked every 6 hours via `check_commits.py`.
Repos monitored: `peak-flow/peaktrack`

---

"""


def get_token() -> str:
    token = os.environ.get("GITHUB_TOKEN", "")
    if not token and TOKEN_FILE.exists():
        token = TOKEN_FILE.read_text().strip()
    if not token:
        print("ERROR: No GitHub token found. Set GITHUB_TOKEN or create ~/.github_token", file=sys.stderr)
        sys.exit(1)
    return token


def list_commits(owner: str, repo: str, since: str, token: str) -> list[dict]:
    commits = []
    page = 1
    while True:
        url = (
            f"https://api.github.com/repos/{owner}/{repo}/commits"
            f"?since={since}&per_page=100&page={page}"
        )
        req = urllib.request.Request(url, headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        })
        try:
            with urllib.request.urlopen(req) as resp:
                batch = json.loads(resp.read())
        except urllib.error.HTTPError as e:
            print(f"ERROR: GitHub API returned {e.code} for {owner}/{repo}", file=sys.stderr)
            sys.exit(1)
        commits.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return commits


def build_entry(repo: str, since: str, now: str, commits: list[dict]) -> str:
    lines = [
        f"## {now}",
        "",
        f"**Repo:** `{repo}`  ",
        f"**Period:** {since} → {now}  ",
        f"**Commits:** {len(commits)}",
        "",
    ]
    if not commits:
        lines.append("_No commits in this period._")
    else:
        lines += [
            "| SHA | Author | Message |",
            "|-----|--------|---------|",
        ]
        for c in commits:
            sha = c["sha"][:7]
            author = (c.get("commit", {}).get("author") or {}).get("name", "unknown")
            msg = (c.get("commit", {}).get("message") or "").split("\n")[0][:80]
            msg = msg.replace("|", "\\|")
            lines.append(f"| `{sha}` | {author} | {msg} |")
    lines += ["", "---", ""]
    return "\n".join(lines) + "\n"


def main():
    token = get_token()
    now_dt = datetime.now(timezone.utc)
    since_dt = now_dt - timedelta(hours=HOURS)
    now = now_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    since = since_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    if not LOG_FILE.exists():
        LOG_FILE.write_text(HEADER)

    for repo in REPOS:
        owner, name = repo.split("/")
        commits = list_commits(owner, name, since, token)
        entry = build_entry(repo, since, now, commits)
        with LOG_FILE.open("a") as f:
            f.write(entry)
        print(f"[{now}] {repo}: {len(commits)} commit(s) logged to {LOG_FILE}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Check GitHub commits in the last 6 hours and append results to commit_log.md."""

import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

REPOS = ["peak-flow/peaktrack"]
HOURS = 6
LOG_FILE = Path(__file__).parent / "commit_log.md"
TOKEN_FILE = Path(__file__).parent / ".github_token"


def get_token():
    token = os.environ.get("GITHUB_TOKEN", "")
    if not token and TOKEN_FILE.exists():
        token = TOKEN_FILE.read_text().strip()
    return token


def github_get(url, token):
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = Request(url, headers=headers)
    with urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def fetch_commits(repo, since_iso, token):
    url = f"https://api.github.com/repos/{repo}/commits?since={since_iso}&per_page=100"
    try:
        return github_get(url, token)
    except HTTPError as e:
        print(f"HTTP error fetching {repo}: {e.code} {e.reason}", file=sys.stderr)
        return []
    except URLError as e:
        print(f"Network error fetching {repo}: {e.reason}", file=sys.stderr)
        return []


def main():
    token = get_token()
    if not token:
        print("Warning: no GitHub token found. Rate limits may apply.", file=sys.stderr)

    now = datetime.now(timezone.utc)
    since = now - timedelta(hours=HOURS)
    since_iso = since.strftime("%Y-%m-%dT%H:%M:%SZ")
    now_str = now.strftime("%Y-%m-%d %H:%M UTC")

    lines = [f"\n## {now_str} — last {HOURS}h\n"]

    for repo in REPOS:
        commits = fetch_commits(repo, since_iso, token)
        count = len(commits)
        lines.append(f"\n### `{repo}` — {count} commit{'s' if count != 1 else ''}\n")
        if commits:
            for c in commits:
                sha = c["sha"][:7]
                msg = c["commit"]["message"].splitlines()[0]
                author = c["commit"]["author"]["name"]
                lines.append(f"- `{sha}` {msg} _(by {author})_\n")
        else:
            lines.append("_No commits in this window._\n")

    entry = "".join(lines)

    # Ensure log file has a header on first run
    if not LOG_FILE.exists():
        LOG_FILE.write_text("# Commit Log\n\n_Auto-generated every 6 hours._\n")

    with LOG_FILE.open("a") as f:
        f.write(entry)

    print(f"Logged to {LOG_FILE}")
    print(entry)


if __name__ == "__main__":
    main()

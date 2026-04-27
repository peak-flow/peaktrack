#!/usr/bin/env python3
"""
Checks one or more GitHub repos for commits made in the last 6 hours
and appends a summary to commit_log.md.

Usage:
    python commit_tracker.py                  # reads repos from config.json
    python commit_tracker.py owner/repo ...  # pass repos directly

Requires GITHUB_TOKEN env var (or ~/.github_token file).
"""

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError

HOURS = 6
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
CONFIG_FILE = SCRIPT_DIR / "config.json"
LOG_FILE = PROJECT_ROOT / "commit_log.md"


def load_token() -> str:
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if token:
        return token
    token_file = Path.home() / ".github_token"
    if token_file.exists():
        return token_file.read_text().strip()
    sys.exit("Error: set GITHUB_TOKEN env var or create ~/.github_token")


def load_repos(cli_args: list[str]) -> list[str]:
    if cli_args:
        return cli_args
    if CONFIG_FILE.exists():
        data = json.loads(CONFIG_FILE.read_text())
        return data.get("repos", [])
    sys.exit(f"No repos given and {CONFIG_FILE} not found. Create it or pass repos as arguments.")


def gh_get(path: str, token: str) -> dict | list:
    url = f"https://api.github.com{path}"
    req = Request(url, headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    })
    try:
        with urlopen(req, timeout=20) as resp:
            return json.loads(resp.read())
    except HTTPError as e:
        body = e.read().decode()
        sys.exit(f"GitHub API error {e.code} for {url}: {body}")
    except URLError as e:
        sys.exit(f"Network error for {url}: {e.reason}")


def fetch_commits_since(repo: str, since: datetime, token: str) -> list[dict]:
    since_str = since.strftime("%Y-%m-%dT%H:%M:%SZ")
    path = f"/repos/{repo}/commits?since={since_str}&per_page=100"
    commits = gh_get(path, token)
    if not isinstance(commits, list):
        print(f"  Warning: unexpected response for {repo}: {commits}")
        return []
    return commits


def format_commit(c: dict) -> str:
    sha = c["sha"][:7]
    message = c["commit"]["message"].split("\n")[0][:80]
    author = c["commit"]["author"]["name"]
    date = c["commit"]["author"]["date"][:16].replace("T", " ")
    return f"  - `{sha}` {date} **{author}**: {message}"


def build_section(results: dict[str, list[dict]], window_start: datetime, window_end: datetime) -> str:
    total = sum(len(v) for v in results.values())
    ts = window_end.strftime("%Y-%m-%d %H:%M UTC")
    start_ts = window_start.strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        f"## {ts}",
        f"",
        f"**Window:** {start_ts} → {ts} ({HOURS}h)  |  **Total commits:** {total}",
        "",
    ]
    for repo, commits in sorted(results.items()):
        count = len(commits)
        lines.append(f"### {repo} — {count} commit{'s' if count != 1 else ''}")
        if commits:
            for c in commits:
                lines.append(format_commit(c))
        else:
            lines.append("  _no commits_")
        lines.append("")
    lines.append("---")
    lines.append("")
    return "\n".join(lines)


def ensure_log_header():
    if not LOG_FILE.exists() or LOG_FILE.stat().st_size == 0:
        LOG_FILE.write_text(
            "# GitHub Commit Log\n\n"
            "Auto-generated every 6 hours. Newest entries at the top.\n\n"
            "---\n\n"
        )


def prepend_to_log(section: str):
    ensure_log_header()
    existing = LOG_FILE.read_text()
    # Insert new section after the header block (after the first "---\n\n")
    marker = "---\n\n"
    idx = existing.find(marker)
    if idx == -1:
        LOG_FILE.write_text(existing + section)
    else:
        insert_at = idx + len(marker)
        LOG_FILE.write_text(existing[:insert_at] + section + existing[insert_at:])


def main():
    token = load_token()
    repos = load_repos(sys.argv[1:])

    now = datetime.now(timezone.utc)
    since = now - timedelta(hours=HOURS)

    print(f"Checking {len(repos)} repo(s) for commits since {since.strftime('%Y-%m-%d %H:%M UTC')} ...")

    results: dict[str, list[dict]] = {}
    for repo in repos:
        print(f"  {repo} ...", end=" ", flush=True)
        commits = fetch_commits_since(repo, since, token)
        results[repo] = commits
        print(f"{len(commits)} commit(s)")

    section = build_section(results, since, now)
    prepend_to_log(section)

    total = sum(len(v) for v in results.values())
    print(f"\nDone. {total} total commit(s). Log updated: {LOG_FILE}")


if __name__ == "__main__":
    main()

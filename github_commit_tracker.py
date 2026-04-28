#!/usr/bin/env python3
"""
GitHub commit tracker — counts commits made in the last 6 hours across
configured repos and appends a summary to commit_log.md.

Usage:
    python3 github_commit_tracker.py

Required env var:
    GITHUB_TOKEN  — a personal access token with at least `repo` (or `public_repo`) scope

Optional env var:
    REPOS         — comma-separated list of "owner/repo" pairs
                    default: peak-flow/peaktrack
    HOURS_BACK    — how many hours to look back (default: 6)
    LOG_FILE      — path to the markdown log file (default: commit_log.md
                    relative to this script's directory)
"""

import os
import sys
import json
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from pathlib import Path

GITHUB_API = "https://api.github.com"


def gh_get(path: str, token: str) -> list | dict:
    url = f"{GITHUB_API}{path}"
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def fetch_commits_since(owner: str, repo: str, since: datetime, token: str) -> list:
    since_str = since.strftime("%Y-%m-%dT%H:%M:%SZ")
    path = f"/repos/{owner}/{repo}/commits?since={since_str}&per_page=100"
    try:
        commits = gh_get(path, token)
        return commits if isinstance(commits, list) else []
    except urllib.error.HTTPError as e:
        print(f"  WARNING: {owner}/{repo} — HTTP {e.code}: {e.reason}", file=sys.stderr)
        return []


def format_commit_row(c: dict) -> str:
    sha = c["sha"][:7]
    msg = (c["commit"]["message"].splitlines()[0])[:72]
    author = c["commit"]["author"]["name"]
    ts = c["commit"]["author"]["date"]
    return f"  - `{sha}` {ts[:16].replace('T', ' ')}  **{author}**  {msg}"


def build_section(repos_data: dict, window_start: datetime, window_end: datetime) -> str:
    ts_label = window_end.strftime("%Y-%m-%d %H:%M UTC")
    window_str = (
        f"{window_start.strftime('%Y-%m-%d %H:%M')} → "
        f"{window_end.strftime('%Y-%m-%d %H:%M')} UTC"
    )
    total = sum(len(v) for v in repos_data.values())

    lines = [
        f"## {ts_label}  ({total} commit{'s' if total != 1 else ''} total)",
        f"_Window: {window_str}_",
        "",
    ]

    for repo_full, commits in sorted(repos_data.items()):
        count = len(commits)
        lines.append(
            f"### {repo_full}  — {count} commit{'s' if count != 1 else ''}"
        )
        if commits:
            for c in commits:
                lines.append(format_commit_row(c))
        else:
            lines.append("  _no commits in this window_")
        lines.append("")

    lines.append("---")
    lines.append("")
    return "\n".join(lines)


def ensure_log_header(log_path: Path) -> None:
    if not log_path.exists() or log_path.stat().st_size == 0:
        log_path.write_text(
            "# GitHub Commit Log\n\n"
            "_Auto-generated every 6 hours by `github_commit_tracker.py`._\n\n"
        )


def main() -> None:
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if not token:
        sys.exit("ERROR: GITHUB_TOKEN environment variable is not set.")

    hours_back = int(os.environ.get("HOURS_BACK", "6"))
    repos_env = os.environ.get("REPOS", "peak-flow/peaktrack")
    repos = [r.strip() for r in repos_env.split(",") if r.strip()]

    script_dir = Path(__file__).parent
    log_file = Path(os.environ.get("LOG_FILE", str(script_dir / "commit_log.md")))

    now = datetime.now(timezone.utc)
    window_start = now - timedelta(hours=hours_back)

    print(f"Checking commits from {window_start.isoformat()} to {now.isoformat()}")

    repos_data: dict[str, list] = {}
    for repo_full in repos:
        parts = repo_full.split("/")
        if len(parts) != 2:
            print(f"  SKIP: invalid repo '{repo_full}' (expected owner/repo)", file=sys.stderr)
            continue
        owner, repo = parts
        print(f"  Fetching {repo_full} …", end=" ", flush=True)
        commits = fetch_commits_since(owner, repo, window_start, token)
        repos_data[repo_full] = commits
        print(f"{len(commits)} commit(s)")

    section = build_section(repos_data, window_start, now)

    ensure_log_header(log_file)
    with log_file.open("a") as f:
        f.write(section)

    print(f"\nAppended to {log_file}")


if __name__ == "__main__":
    main()

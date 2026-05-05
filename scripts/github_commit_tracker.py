#!/usr/bin/env python3
"""
Check GitHub repos for commits in the last 6 hours and append a report to a markdown file.

Usage:
    python3 github_commit_tracker.py

Required env vars:
    GITHUB_TOKEN  – personal access token with repo read scope

Optional env vars:
    GITHUB_REPOS  – comma-separated list of "owner/repo" entries
                    (defaults to the list in repos.txt next to this script)
    REPORT_FILE   – path to the markdown report file
                    (defaults to ../commit_reports/commits.md)
    LOOKBACK_HOURS – how far back to look (defaults to 6)
"""

import os
import sys
import json
import datetime
import urllib.request
import urllib.error
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
DEFAULT_REPOS_FILE = SCRIPT_DIR / "repos.txt"
DEFAULT_REPORT_FILE = SCRIPT_DIR.parent / "commit_reports" / "commits.md"
DEFAULT_LOOKBACK_HOURS = 6


def github_get(path: str, token: str) -> list | dict:
    url = f"https://api.github.com{path}"
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        body = exc.read().decode()
        print(f"  GitHub API error {exc.code} for {url}: {body}", file=sys.stderr)
        return []


def fetch_commits_since(repo: str, since: datetime.datetime, token: str) -> list[dict]:
    since_iso = since.strftime("%Y-%m-%dT%H:%M:%SZ")
    data = github_get(f"/repos/{repo}/commits?since={since_iso}&per_page=100", token)
    if not isinstance(data, list):
        return []
    results = []
    for item in data:
        commit = item.get("commit", {})
        results.append(
            {
                "sha": item.get("sha", "")[:7],
                "author": commit.get("author", {}).get("name", "unknown"),
                "message": commit.get("message", "").splitlines()[0],
                "date": commit.get("author", {}).get("date", ""),
            }
        )
    return results


def load_repos() -> list[str]:
    env_repos = os.environ.get("GITHUB_REPOS", "").strip()
    if env_repos:
        return [r.strip() for r in env_repos.split(",") if r.strip()]
    if DEFAULT_REPOS_FILE.exists():
        lines = DEFAULT_REPOS_FILE.read_text().splitlines()
        return [l.strip() for l in lines if l.strip() and not l.startswith("#")]
    print("No repos configured. Add them to scripts/repos.txt or set GITHUB_REPOS.", file=sys.stderr)
    sys.exit(1)


def build_report(results: dict[str, list], window_start: datetime.datetime, window_end: datetime.datetime) -> str:
    total = sum(len(commits) for commits in results.values())
    ts = window_end.strftime("%Y-%m-%d %H:%M UTC")
    window_label = f"{window_start.strftime('%H:%M')}–{window_end.strftime('%H:%M UTC %Y-%m-%d')}"

    lines = [
        f"## {ts}  —  {total} commit{'s' if total != 1 else ''} in the last 6 hours",
        "",
        f"**Window:** {window_label}  ",
        "",
    ]

    for repo, commits in sorted(results.items()):
        count = len(commits)
        lines.append(f"### `{repo}` — {count} commit{'s' if count != 1 else ''}")
        if commits:
            for c in commits:
                lines.append(f"- `{c['sha']}` **{c['author']}** — {c['message']}")
        else:
            lines.append("_No commits in this window._")
        lines.append("")

    lines.append("---")
    lines.append("")
    return "\n".join(lines)


def main():
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if not token:
        print("GITHUB_TOKEN env var is required.", file=sys.stderr)
        sys.exit(1)

    lookback = int(os.environ.get("LOOKBACK_HOURS", DEFAULT_LOOKBACK_HOURS))
    report_file = Path(os.environ.get("REPORT_FILE", DEFAULT_REPORT_FILE))
    repos = load_repos()

    now = datetime.datetime.utcnow()
    since = now - datetime.timedelta(hours=lookback)

    print(f"Checking {len(repos)} repo(s) for commits since {since.strftime('%Y-%m-%d %H:%M UTC')} ...")

    results: dict[str, list] = {}
    for repo in repos:
        print(f"  {repo} ...", end=" ", flush=True)
        commits = fetch_commits_since(repo, since, token)
        results[repo] = commits
        print(f"{len(commits)} commit(s)")

    report = build_report(results, since, now)

    report_file.parent.mkdir(parents=True, exist_ok=True)
    # Prepend new report so newest is at top
    existing = report_file.read_text() if report_file.exists() else ""
    report_file.write_text(report + existing)

    print(f"\nReport saved to {report_file}")


if __name__ == "__main__":
    main()

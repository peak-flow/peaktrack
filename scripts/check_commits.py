#!/usr/bin/env python3
"""
Check GitHub repositories for commits in the last 6 hours
and append a summary to commit_report.md.

Usage:
    GITHUB_TOKEN=your_token python3 check_commits.py
    GITHUB_TOKEN=your_token REPOS=owner/repo1,owner/repo2 python3 check_commits.py

Environment variables:
    GITHUB_TOKEN  (required) GitHub personal access token
    REPOS         Comma-separated list of owner/repo pairs to check
                  Defaults to WATCHED_REPOS list in this file
    HOURS         How many hours back to check (default: 6)
    REPORT_FILE   Path to the markdown report file (default: ../commit_report.md)
"""

import os
import sys
import json
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta

WATCHED_REPOS = [
    "peak-flow/peaktrack",
]

HOURS_BACK = int(os.environ.get("HOURS", "6"))
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
REPORT_FILE = os.environ.get(
    "REPORT_FILE",
    os.path.join(os.path.dirname(__file__), "..", "commit_report.md"),
)


def github_get(path: str) -> list | dict:
    url = f"https://api.github.com{path}"
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    if GITHUB_TOKEN:
        req.add_header("Authorization", f"Bearer {GITHUB_TOKEN}")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def get_commits_since(owner: str, repo: str, since: datetime) -> list[dict]:
    since_str = since.strftime("%Y-%m-%dT%H:%M:%SZ")
    results = []
    page = 1
    while True:
        data = github_get(
            f"/repos/{owner}/{repo}/commits?since={since_str}&per_page=100&page={page}"
        )
        if not data:
            break
        results.extend(data)
        if len(data) < 100:
            break
        page += 1
    return results


def format_commit_row(commit: dict) -> str:
    sha = commit["sha"][:7]
    msg = commit["commit"]["message"].splitlines()[0][:80]
    author = commit["commit"]["author"]["name"]
    date = commit["commit"]["author"]["date"][:10]
    return f"| `{sha}` | {date} | {author} | {msg} |"


def build_section(repo: str, commits: list[dict], since: datetime, until: datetime) -> str:
    owner, name = repo.split("/", 1)
    lines = [
        f"## `{repo}`",
        "",
        f"**Commits in the last {HOURS_BACK}h** "
        f"({since.strftime('%Y-%m-%d %H:%M UTC')} → {until.strftime('%Y-%m-%d %H:%M UTC')}): "
        f"**{len(commits)}**",
        "",
    ]
    if commits:
        lines += [
            "| SHA | Date | Author | Message |",
            "|-----|------|--------|---------|",
        ]
        for c in commits:
            lines.append(format_commit_row(c))
    else:
        lines.append("_No commits in this window._")
    lines.append("")
    return "\n".join(lines)


def run():
    if not GITHUB_TOKEN:
        print("ERROR: GITHUB_TOKEN environment variable is not set.", file=sys.stderr)
        sys.exit(1)

    repos_env = os.environ.get("REPOS", "")
    repos = [r.strip() for r in repos_env.split(",") if r.strip()] if repos_env else WATCHED_REPOS

    until = datetime.now(timezone.utc)
    since = until - timedelta(hours=HOURS_BACK)

    sections = []
    totals = []
    for repo in repos:
        owner, name = repo.split("/", 1)
        try:
            commits = get_commits_since(owner, name, since)
            totals.append((repo, len(commits)))
            sections.append(build_section(repo, commits, since, until))
            print(f"  {repo}: {len(commits)} commit(s)")
        except urllib.error.HTTPError as e:
            msg = f"HTTP {e.code} fetching {repo}: {e.reason}"
            print(f"  ERROR: {msg}", file=sys.stderr)
            sections.append(f"## `{repo}`\n\n**ERROR:** {msg}\n")
            totals.append((repo, -1))

    report_path = os.path.realpath(REPORT_FILE)
    now_str = until.strftime("%Y-%m-%d %H:%M UTC")
    summary_line = ", ".join(
        f"{r}: {n}" for r, n in totals if n >= 0
    )

    entry_header = f"# Commit Report — {now_str}\n\n"
    if summary_line:
        entry_header += f"**Total this window:** {summary_line}\n\n"
    entry_header += "---\n\n"

    entry = entry_header + "\n".join(sections) + "\n"

    existing = ""
    if os.path.exists(report_path):
        with open(report_path) as f:
            existing = f.read()

    with open(report_path, "w") as f:
        f.write(entry + existing)

    print(f"Report saved → {report_path}")


if __name__ == "__main__":
    run()

#!/usr/bin/env python3
"""
GitHub commit tracker — queries configured repos every 6 hours and
appends a summary to commit_log.md.

Usage:
    python github_commit_tracker.py

Required env var:
    GITHUB_TOKEN   — personal access token with repo read scope

Optional env var:
    GITHUB_REPOS   — comma-separated list of owner/repo pairs
                     (defaults to peak-flow/peaktrack)
    LOG_FILE       — path to the output markdown file
                     (defaults to commit_log.md next to this script)
"""

import os
import sys
import json
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from pathlib import Path


GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
REPOS_ENV = os.environ.get("GITHUB_REPOS", "peak-flow/peaktrack")
REPOS = [r.strip() for r in REPOS_ENV.split(",") if r.strip()]
LOG_FILE = Path(os.environ.get("LOG_FILE", Path(__file__).parent / "commit_log.md"))
HOURS_BACK = 6


def github_get(path: str) -> list | dict:
    url = f"https://api.github.com{path}"
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    if GITHUB_TOKEN:
        req.add_header("Authorization", f"Bearer {GITHUB_TOKEN}")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        print(f"  HTTP {exc.code} for {url}", file=sys.stderr)
        return []


def fetch_recent_commits(owner: str, repo: str, since: datetime) -> list[dict]:
    since_iso = since.strftime("%Y-%m-%dT%H:%M:%SZ")
    all_commits: list[dict] = []
    page = 1
    while True:
        path = f"/repos/{owner}/{repo}/commits?since={since_iso}&per_page=100&page={page}"
        data = github_get(path)
        if not isinstance(data, list) or not data:
            break
        all_commits.extend(data)
        if len(data) < 100:
            break
        page += 1
    return all_commits


def format_commit_row(commit: dict) -> str:
    sha = commit.get("sha", "")[:7]
    info = commit.get("commit", {})
    message = info.get("message", "").splitlines()[0][:80]
    author = info.get("author", {}).get("name", "unknown")
    date = info.get("author", {}).get("date", "")[:10]
    url = commit.get("html_url", "")
    return f"| `{sha}` | {date} | {author} | [{message}]({url}) |"


def ensure_log_header():
    if not LOG_FILE.exists():
        LOG_FILE.write_text("# GitHub Commit Log\n\nGenerated automatically every 6 hours.\n\n")


def append_report(report_lines: list[str]):
    ensure_log_header()
    with LOG_FILE.open("a") as fh:
        fh.write("\n".join(report_lines) + "\n\n")


def run():
    if not GITHUB_TOKEN:
        print("Warning: GITHUB_TOKEN is not set — rate limits will be strict (60 req/hr).", file=sys.stderr)

    now = datetime.now(timezone.utc)
    since = now - timedelta(hours=HOURS_BACK)
    window_label = f"{since.strftime('%Y-%m-%d %H:%M')} → {now.strftime('%Y-%m-%d %H:%M')} UTC"

    report: list[str] = [
        f"## Check at {now.strftime('%Y-%m-%d %H:%M UTC')}",
        f"_Window: last {HOURS_BACK} hours ({window_label})_",
        "",
    ]

    total = 0
    for repo_full in REPOS:
        parts = repo_full.split("/", 1)
        if len(parts) != 2:
            print(f"Skipping invalid repo entry: {repo_full}", file=sys.stderr)
            continue
        owner, repo = parts
        print(f"Fetching commits for {repo_full} …")
        commits = fetch_recent_commits(owner, repo, since)
        count = len(commits)
        total += count
        report.append(f"### {repo_full} — {count} commit{'s' if count != 1 else ''}")
        if commits:
            report += [
                "| SHA | Date | Author | Message |",
                "|-----|------|--------|---------|",
            ]
            for c in commits:
                report.append(format_commit_row(c))
        else:
            report.append("_No commits in this window._")
        report.append("")

    report.append(f"**Total across all repos: {total} commit{'s' if total != 1 else ''}**")
    report.append("")
    report.append("---")

    append_report(report)
    print(f"Done. {total} commit(s) written to {LOG_FILE}")


if __name__ == "__main__":
    run()

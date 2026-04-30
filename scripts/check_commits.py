#!/usr/bin/env python3
"""Check GitHub commits from the last 6 hours and append a summary to a markdown file."""

import os
import sys
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
import urllib.request
import urllib.error

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
REPORT_FILE = Path(__file__).parent.parent / "commit_report.md"
REPOS_FILE = Path(__file__).parent / "repos.json"
WINDOW_HOURS = 6


def github_get(url: str) -> list | dict:
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    if GITHUB_TOKEN:
        req.add_header("Authorization", f"Bearer {GITHUB_TOKEN}")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        print(f"  HTTP {e.code} for {url}", file=sys.stderr)
        return []


def load_repos() -> list[str]:
    if REPOS_FILE.exists():
        with open(REPOS_FILE) as f:
            return json.load(f)
    # Default repo; edit repos.json to add more
    return ["peak-flow/peaktrack"]


def fetch_commits(repo: str, since: datetime) -> list[dict]:
    since_iso = since.strftime("%Y-%m-%dT%H:%M:%SZ")
    url = f"https://api.github.com/repos/{repo}/commits?since={since_iso}&per_page=100"
    data = github_get(url)
    if not isinstance(data, list):
        return []
    commits = []
    for item in data:
        sha = item.get("sha", "")[:7]
        message = (item.get("commit", {}).get("message", "") or "").splitlines()[0][:80]
        author = item.get("commit", {}).get("author", {}).get("name", "unknown")
        commits.append({"sha": sha, "message": message, "author": author})
    return commits


def build_report(results: dict[str, list[dict]], since: datetime, now: datetime) -> str:
    total = sum(len(v) for v in results.values())
    window = f"{since.strftime('%Y-%m-%d %H:%M')} – {now.strftime('%Y-%m-%d %H:%M')} UTC"
    lines = [
        f"## Commit report — {now.strftime('%Y-%m-%d %H:%M UTC')}",
        "",
        f"**Window:** {window}  ",
        f"**Total commits:** {total}  ",
        "",
    ]
    for repo, commits in sorted(results.items()):
        lines.append(f"### {repo} ({len(commits)} commit{'s' if len(commits) != 1 else ''})")
        if commits:
            for c in commits:
                lines.append(f"- `{c['sha']}` {c['message']} _{c['author']}_")
        else:
            lines.append("- _(no commits)_")
        lines.append("")
    lines.append("---")
    lines.append("")
    return "\n".join(lines)


def main():
    if not GITHUB_TOKEN:
        print("Warning: GITHUB_TOKEN not set — unauthenticated requests are rate-limited to 60/hr", file=sys.stderr)

    now = datetime.now(timezone.utc)
    since = now - timedelta(hours=WINDOW_HOURS)

    repos = load_repos()
    print(f"Checking {len(repos)} repo(s) since {since.strftime('%Y-%m-%d %H:%M UTC')}...")

    results: dict[str, list[dict]] = {}
    for repo in repos:
        print(f"  {repo}...", end=" ", flush=True)
        commits = fetch_commits(repo, since)
        results[repo] = commits
        print(f"{len(commits)} commit(s)")

    report = build_report(results, since, now)

    # Prepend new report so newest is always at the top
    existing = REPORT_FILE.read_text() if REPORT_FILE.exists() else ""
    header = "# GitHub Commit Reports\n\n"
    if existing.startswith(header):
        existing = existing[len(header):]
    REPORT_FILE.write_text(header + report + existing)

    print(f"Report saved to {REPORT_FILE}")


if __name__ == "__main__":
    main()

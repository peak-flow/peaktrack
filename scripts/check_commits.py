#!/usr/bin/env python3
"""
Check peak-flow GitHub org for commits in the last N hours.
Requires GITHUB_TOKEN env var. Appends results to commit-log.md.
Usage: python3 check_commits.py [hours=6]
"""
import sys
import os
import json
import datetime
import urllib.request
import urllib.error
from pathlib import Path

ORG = "peak-flow"
HOURS = int(sys.argv[1]) if len(sys.argv) > 1 else 6
LOG_FILE = Path(__file__).parent.parent / "commit-log.md"
TOKEN = os.environ.get("GITHUB_TOKEN", "")

HEADERS = {
    "Accept": "application/vnd.github.v3+json",
    "User-Agent": "peak-flow-commit-tracker",
}
if TOKEN:
    HEADERS["Authorization"] = f"token {TOKEN}"


def gh_get(url, params=None):
    if params:
        query = "&".join(f"{k}={v}" for k, v in params.items())
        url = f"{url}?{query}"
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        print(f"  HTTP {e.code} for {url}", file=sys.stderr)
        return []


def get_recent_repos(since_str):
    repos = []
    page = 1
    while True:
        data = gh_get(
            f"https://api.github.com/orgs/{ORG}/repos",
            {"per_page": 100, "page": page, "sort": "pushed", "direction": "desc"},
        )
        if not data or not isinstance(data, list):
            break
        for repo in data:
            pushed_at = repo.get("pushed_at") or ""
            if pushed_at >= since_str:
                repos.append(repo["name"])
            else:
                return repos  # sorted desc, safe to stop
        if len(data) < 100:
            break
        page += 1
    return repos


def count_commits(repo_name, since_str):
    commits = gh_get(
        f"https://api.github.com/repos/{ORG}/{repo_name}/commits",
        {"since": since_str, "per_page": 100},
    )
    return commits if isinstance(commits, list) else []


def main():
    if not TOKEN:
        print("Warning: GITHUB_TOKEN not set. Private repos and rate limits will apply.")

    now = datetime.datetime.utcnow()
    since = now - datetime.timedelta(hours=HOURS)
    since_str = since.strftime("%Y-%m-%dT%H:%M:%SZ")
    now_display = now.strftime("%Y-%m-%d %H:%M UTC")

    print(f"Checking commits since {since_str} ...")
    recent_repos = get_recent_repos(since_str)
    print(f"  {len(recent_repos)} repos pushed in last {HOURS}h")

    results = []
    total = 0
    for repo in recent_repos:
        commits = count_commits(repo, since_str)
        if commits:
            results.append((repo, len(commits)))
            total += len(commits)
            print(f"  {repo}: {len(commits)} commit(s)")

    results.sort(key=lambda x: x[1], reverse=True)

    lines = [f"\n## {now_display}\n", f"**Total commits (last {HOURS}h): {total}**\n"]
    if results:
        lines.append("\n| Repository | Commits |")
        lines.append("|---|---|")
        for repo, count in results:
            lines.append(f"| [{repo}](https://github.com/{ORG}/{repo}) | {count} |")
    else:
        lines.append("\n_No commits in the last 6 hours._")
    lines.append("")

    entry = "\n".join(lines) + "\n"

    if not LOG_FILE.exists() or LOG_FILE.stat().st_size == 0:
        LOG_FILE.write_text("# GitHub Commit Activity — peak-flow\n")

    with LOG_FILE.open("a") as f:
        f.write(entry)

    print(f"Logged to {LOG_FILE}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Fetch GitHub commits from the last N hours and append a summary to commit_log.md."""

import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
REPOS = [r.strip() for r in os.getenv("GITHUB_REPOS", "peak-flow/peaktrack").split(",") if r.strip()]
HOURS = int(os.getenv("CHECK_HOURS", "6"))
OUTPUT_FILE = Path(__file__).parent / "commit_log.md"
PER_PAGE = 100


def gh_get(url: str) -> list | dict:
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    if GITHUB_TOKEN:
        req.add_header("Authorization", f"Bearer {GITHUB_TOKEN}")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def fetch_commits(repo: str, since: str) -> list:
    owner, name = repo.split("/", 1)
    commits = []
    page = 1
    while True:
        url = (
            f"https://api.github.com/repos/{owner}/{name}/commits"
            f"?since={since}&per_page={PER_PAGE}&page={page}"
        )
        try:
            batch = gh_get(url)
        except urllib.error.HTTPError as e:
            print(f"  HTTP {e.code} fetching {repo}: {e.reason}")
            break
        if not batch:
            break
        commits.extend(batch)
        if len(batch) < PER_PAGE:
            break
        page += 1
    return commits


def build_entry(results: list[tuple], now: datetime) -> str:
    total = sum(count for _, count, _ in results)
    ts = now.strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        f"\n## {ts}",
        f"\n**Period:** last {HOURS} hours  |  **Total commits:** {total}\n",
    ]
    for repo, count, commits in results:
        lines.append(f"\n### `{repo}` — {count} commit(s)")
        for c in commits:
            sha = c["sha"][:7]
            msg = c["commit"]["message"].splitlines()[0][:80]
            author = c["commit"]["author"]["name"]
            lines.append(f"- `{sha}` {msg} _(by {author})_")
    return "\n".join(lines) + "\n"


def main():
    now = datetime.now(timezone.utc)
    since = (now - timedelta(hours=HOURS)).isoformat()

    results = []
    for repo in REPOS:
        print(f"Checking {repo}…")
        commits = fetch_commits(repo, since)
        results.append((repo, len(commits), commits))
        print(f"  {len(commits)} commit(s)")

    entry = build_entry(results, now)

    if not OUTPUT_FILE.exists():
        OUTPUT_FILE.write_text("# GitHub Commit Log\n\n_Auto-generated every 6 hours._\n")

    with OUTPUT_FILE.open("a") as f:
        f.write(entry)

    total = sum(c for _, c, _ in results)
    print(f"\nLogged {total} commit(s) across {len(results)} repo(s) → {OUTPUT_FILE.name}")


if __name__ == "__main__":
    main()

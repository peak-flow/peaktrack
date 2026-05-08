#!/usr/bin/env python3
"""
GitHub commit tracker - runs every 6 hours and logs commits to markdown.

Requires: GITHUB_TOKEN env var for authenticated API access (5000 req/hr).
Configure GITHUB_OWNER to set the org/user whose repos to track.
"""

import os
import sys
import json
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from pathlib import Path

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_OWNER = os.environ.get("GITHUB_OWNER", "peak-flow")
CHECK_INTERVAL_HOURS = 6
OUTPUT_FILE = Path(__file__).parent.parent / "commit_log.md"
API_BASE = "https://api.github.com"


def github_get(path: str) -> list | dict:
    url = f"{API_BASE}{path}"
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    if GITHUB_TOKEN:
        req.add_header("Authorization", f"Bearer {GITHUB_TOKEN}")

    results = []
    page = 1
    while True:
        paginated = f"{url}{'&' if '?' in url else '?'}page={page}&per_page=100"
        req2 = urllib.request.Request(paginated)
        req2.add_header("Accept", "application/vnd.github+json")
        req2.add_header("X-GitHub-Api-Version", "2022-11-28")
        if GITHUB_TOKEN:
            req2.add_header("Authorization", f"Bearer {GITHUB_TOKEN}")

        try:
            with urllib.request.urlopen(req2, timeout=30) as resp:
                data = json.loads(resp.read())
                if isinstance(data, dict):
                    return data
                if not data:
                    break
                results.extend(data)
                if len(data) < 100:
                    break
                page += 1
        except urllib.error.HTTPError as e:
            body = e.read().decode()
            print(f"  HTTP {e.code} for {paginated}: {body[:200]}", flush=True)
            break

    return results


def list_repos(owner: str) -> list[str]:
    """Return repo full names for the given org or user."""
    # Try org first, fall back to user
    repos = github_get(f"/orgs/{owner}/repos?type=all")
    if isinstance(repos, dict) and repos.get("message"):
        repos = github_get(f"/users/{owner}/repos?type=all")
    return [r["full_name"] for r in repos if isinstance(r, dict)]


def count_commits_since(repo: str, since: datetime) -> tuple[int, list[str]]:
    """Return (commit_count, [author, ...]) for commits after `since`."""
    since_iso = since.strftime("%Y-%m-%dT%H:%M:%SZ")
    commits = github_get(f"/repos/{repo}/commits?since={since_iso}")
    if isinstance(commits, dict):
        return 0, []
    authors = sorted({c["commit"]["author"]["name"] for c in commits if isinstance(c, dict)})
    return len(commits), authors


def append_markdown(report_time: datetime, results: list[dict]) -> None:
    total = sum(r["count"] for r in results)
    active = [r for r in results if r["count"] > 0]

    now_str = report_time.strftime("%Y-%m-%d %H:%M UTC")
    window_start = (report_time - timedelta(hours=CHECK_INTERVAL_HOURS)).strftime("%H:%M UTC")

    lines = [
        f"\n## {now_str}  ({window_start} → now)\n",
        f"**Total commits:** {total}  |  **Active repos:** {len(active)}/{len(results)}\n",
    ]

    if active:
        lines.append("\n| Repository | Commits | Authors |\n")
        lines.append("|---|---|---|\n")
        for r in sorted(active, key=lambda x: -x["count"]):
            authors = ", ".join(r["authors"]) or "—"
            lines.append(f"| `{r['repo']}` | {r['count']} | {authors} |\n")
    else:
        lines.append("\n_No commits in this window._\n")

    lines.append("\n---\n")

    exists = OUTPUT_FILE.exists()
    with open(OUTPUT_FILE, "a") as f:
        if not exists:
            f.write("# GitHub Commit Log\n\nAuto-generated every 6 hours.\n\n---\n")
        f.writelines(lines)

    print(f"  Appended to {OUTPUT_FILE}", flush=True)


def run_check() -> None:
    now = datetime.now(timezone.utc)
    since = now - timedelta(hours=CHECK_INTERVAL_HOURS)
    print(f"[{now.strftime('%Y-%m-%d %H:%M UTC')}] Checking commits since {since.strftime('%H:%M UTC')} ...", flush=True)

    if not GITHUB_TOKEN:
        print("  WARNING: GITHUB_TOKEN not set — rate limited to 60 req/hr", flush=True)

    repos = list_repos(GITHUB_OWNER)
    if not repos:
        print(f"  No repos found for owner '{GITHUB_OWNER}'", flush=True)
        return

    print(f"  Found {len(repos)} repos", flush=True)

    results = []
    for repo in repos:
        count, authors = count_commits_since(repo, since)
        results.append({"repo": repo, "count": count, "authors": authors})
        if count:
            print(f"  {repo}: {count} commit(s)", flush=True)

    append_markdown(now, results)
    print("  Done.\n", flush=True)


def main() -> None:
    print(f"GitHub Commit Tracker started — checking every {CHECK_INTERVAL_HOURS}h", flush=True)
    print(f"Owner: {GITHUB_OWNER}  |  Output: {OUTPUT_FILE}", flush=True)
    print(f"Token: {'set' if GITHUB_TOKEN else 'NOT SET (rate limited)'}\n", flush=True)

    # Run immediately on start, then sleep
    while True:
        try:
            run_check()
        except Exception as e:
            print(f"  Error during check: {e}", flush=True)
        print(f"  Sleeping {CHECK_INTERVAL_HOURS}h until next check ...\n", flush=True)
        time.sleep(CHECK_INTERVAL_HOURS * 3600)


if __name__ == "__main__":
    main()

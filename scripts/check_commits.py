#!/usr/bin/env python3
"""Check GitHub commits in the last 6 hours and append results to a markdown log."""

import os
import sys
import json
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from pathlib import Path

GITHUB_USER = "peak-flow"
LOG_FILE = Path(__file__).parent.parent / "commit_log.md"
HOURS = 6


def github_get(path: str, token: str) -> list | dict:
    url = f"https://api.github.com{path}"
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def fetch_all_pages(path: str, token: str) -> list:
    results = []
    page = 1
    while True:
        sep = "&" if "?" in path else "?"
        data = github_get(f"{path}{sep}per_page=100&page={page}", token)
        if not data:
            break
        results.extend(data)
        if len(data) < 100:
            break
        page += 1
    return results


def main():
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("ERROR: GITHUB_TOKEN environment variable not set.", file=sys.stderr)
        sys.exit(1)

    since = datetime.now(timezone.utc) - timedelta(hours=HOURS)
    since_iso = since.strftime("%Y-%m-%dT%H:%M:%SZ")
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    print(f"Checking commits since {since_iso} ...")

    # Fetch all repos for the user
    repos = fetch_all_pages(f"/users/{GITHUB_USER}/repos?type=owner&sort=pushed", token)

    repo_results = []
    total_commits = 0

    for repo in repos:
        repo_name = repo["name"]
        full_name = repo["full_name"]
        # Skip forks optionally — remove this check to include forks
        if repo.get("fork"):
            continue

        default_branch = repo.get("default_branch", "main")

        try:
            commits = github_get(
                f"/repos/{full_name}/commits?sha={default_branch}&since={since_iso}&per_page=100",
                token,
            )
            count = len(commits) if isinstance(commits, list) else 0
        except urllib.error.HTTPError as e:
            if e.code in (404, 409):  # empty repo or not found
                count = 0
            else:
                print(f"  Warning: {full_name}: HTTP {e.code}", file=sys.stderr)
                count = 0

        if count > 0:
            authors = sorted({c["commit"]["author"]["name"] for c in commits})
            repo_results.append((repo_name, full_name, count, authors, commits[0]["html_url"]))
            total_commits += count
            print(f"  {full_name}: {count} commit(s)")

    # Build markdown section
    lines = [
        f"## {now_str}  —  last {HOURS} hours\n",
        f"**Total commits:** {total_commits}  |  **Repos with activity:** {len(repo_results)}\n",
    ]

    if repo_results:
        lines.append("\n| Repository | Commits | Authors | Latest commit |\n")
        lines.append("|---|---|---|---|\n")
        for repo_name, full_name, count, authors, latest_url in sorted(
            repo_results, key=lambda x: -x[2]
        ):
            authors_str = ", ".join(authors)
            lines.append(
                f"| [{repo_name}](https://github.com/{full_name}) "
                f"| {count} "
                f"| {authors_str} "
                f"| [view]({latest_url}) |\n"
            )
    else:
        lines.append("\n_No commits found in the last 6 hours._\n")

    lines.append("\n---\n\n")

    # Prepend to log file (newest first)
    existing = LOG_FILE.read_text() if LOG_FILE.exists() else ""
    LOG_FILE.write_text("".join(lines) + existing)

    print(f"\nDone. Appended to {LOG_FILE}")
    print(f"Total: {total_commits} commit(s) across {len(repo_results)} repo(s).")


if __name__ == "__main__":
    main()

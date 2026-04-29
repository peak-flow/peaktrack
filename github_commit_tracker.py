#!/usr/bin/env python3
"""
Checks GitHub for commits made in the last 6 hours across all accessible repos,
and appends a summary to commit_log.md.

Setup:
  export GITHUB_TOKEN=your_personal_access_token
  export GITHUB_USERNAME=your_github_username   # optional, defaults to authenticated user

Run manually:
  python3 github_commit_tracker.py

Run every 6 hours via cron:
  0 */6 * * * cd /home/user/peaktrack && python3 github_commit_tracker.py >> tracker.log 2>&1
"""

import os
import sys
import json
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_USERNAME = os.environ.get("GITHUB_USERNAME", "")
OUTPUT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "commit_log.md")
LOOKBACK_HOURS = 6


def github_get(path: str) -> list | dict:
    url = f"https://api.github.com{path}"
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {GITHUB_TOKEN}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def get_username() -> str:
    if GITHUB_USERNAME:
        return GITHUB_USERNAME
    data = github_get("/user")
    return data["login"]


def get_repos(username: str) -> list[dict]:
    repos = []
    page = 1
    while True:
        batch = github_get(f"/user/repos?per_page=100&page={page}&sort=updated&direction=desc")
        if not batch:
            break
        repos.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return repos


def get_recent_commits(owner: str, repo: str, since: datetime) -> list[dict]:
    since_iso = since.strftime("%Y-%m-%dT%H:%M:%SZ")
    try:
        commits = github_get(f"/repos/{owner}/{repo}/commits?since={since_iso}&per_page=100")
        return commits if isinstance(commits, list) else []
    except urllib.error.HTTPError as e:
        if e.code in (409, 404):  # empty repo or no access
            return []
        raise


def append_to_markdown(report: str) -> None:
    file_exists = os.path.exists(OUTPUT_FILE)
    with open(OUTPUT_FILE, "a") as f:
        if not file_exists:
            f.write("# GitHub Commit Activity Log\n\n")
        f.write(report)


def main():
    if not GITHUB_TOKEN:
        print("ERROR: GITHUB_TOKEN environment variable is not set.", file=sys.stderr)
        sys.exit(1)

    now = datetime.now(timezone.utc)
    since = now - timedelta(hours=LOOKBACK_HOURS)

    print(f"[{now.strftime('%Y-%m-%d %H:%M UTC')}] Checking commits since {since.strftime('%Y-%m-%d %H:%M UTC')}...")

    username = get_username()
    repos = get_repos(username)

    results: list[tuple[str, int, list[str]]] = []
    total_commits = 0

    for repo in repos:
        owner = repo["owner"]["login"]
        name = repo["name"]
        full_name = repo["full_name"]
        commits = get_recent_commits(owner, name, since)
        if commits:
            msgs = [c["commit"]["message"].split("\n")[0][:80] for c in commits]
            results.append((full_name, len(commits), msgs))
            total_commits += len(commits)
            print(f"  {full_name}: {len(commits)} commit(s)")

    # Build markdown section
    header = f"## {now.strftime('%Y-%m-%d %H:%M UTC')} — last {LOOKBACK_HOURS}h check\n\n"
    if results:
        summary = f"**{total_commits} commit(s)** across **{len(results)} repo(s)**\n\n"
        rows = ""
        for full_name, count, msgs in sorted(results, key=lambda x: -x[1]):
            rows += f"### `{full_name}` ({count} commit{'s' if count != 1 else ''})\n"
            for msg in msgs:
                rows += f"- {msg}\n"
            rows += "\n"
        report = header + summary + rows + "---\n\n"
    else:
        report = header + f"_No commits in the last {LOOKBACK_HOURS} hours._\n\n---\n\n"

    append_to_markdown(report)
    print(f"Done. {total_commits} commit(s) found. Report appended to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()

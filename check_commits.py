#!/usr/bin/env python3
"""Check GitHub commits from the last 6 hours and append a report to commit_log.md."""

import os
import sys
import json
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from pathlib import Path

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
OUTPUT_FILE = Path(__file__).parent / "commit_log.md"
HOURS_BACK = 6
API_BASE = "https://api.github.com"


def gh_get(path: str) -> list | dict:
    url = f"{API_BASE}{path}"
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    if GITHUB_TOKEN:
        req.add_header("Authorization", f"Bearer {GITHUB_TOKEN}")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def get_repos() -> list[dict]:
    repos = []
    page = 1
    while True:
        batch = gh_get(f"/user/repos?per_page=100&page={page}&sort=pushed&direction=desc")
        if not batch:
            break
        repos.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return repos


def get_commits_since(owner: str, repo: str, since: datetime) -> list[dict]:
    since_iso = since.strftime("%Y-%m-%dT%H:%M:%SZ")
    try:
        commits = gh_get(f"/repos/{owner}/{repo}/commits?since={since_iso}&per_page=100")
        return commits if isinstance(commits, list) else []
    except urllib.error.HTTPError as e:
        if e.code in (409, 404):  # empty repo or no access
            return []
        raise


def main():
    if not GITHUB_TOKEN:
        print("ERROR: Set the GITHUB_TOKEN environment variable to your GitHub personal access token.")
        print("  export GITHUB_TOKEN=ghp_your_token_here")
        sys.exit(1)

    now = datetime.now(timezone.utc)
    since = now - timedelta(hours=HOURS_BACK)

    print(f"Checking commits since {since.isoformat()} ...")

    try:
        me = gh_get("/user")
        username = me["login"]
    except Exception as e:
        print(f"ERROR: Could not authenticate with GitHub: {e}")
        sys.exit(1)

    repos = get_repos()
    print(f"Found {len(repos)} repos for @{username}")

    active = []
    total_commits = 0

    for repo in repos:
        owner = repo["owner"]["login"]
        name = repo["name"]
        pushed_at = repo.get("pushed_at")

        # Skip repos with no recent push activity (quick filter)
        if pushed_at:
            pushed_dt = datetime.fromisoformat(pushed_at.replace("Z", "+00:00"))
            if pushed_dt < since:
                continue

        commits = get_commits_since(owner, name, since)
        if commits:
            active.append({"repo": f"{owner}/{name}", "count": len(commits), "url": repo["html_url"]})
            total_commits += len(commits)
            print(f"  {owner}/{name}: {len(commits)} commit(s)")

    # Build markdown report section
    window_label = f"{since.strftime('%Y-%m-%d %H:%M')} – {now.strftime('%Y-%m-%d %H:%M')} UTC"
    lines = [
        f"\n## {now.strftime('%Y-%m-%d %H:%M')} UTC — {total_commits} commit(s) in the last {HOURS_BACK}h\n",
        f"_Window: {window_label}_\n",
    ]

    if active:
        lines.append("\n| Repository | Commits | Link |")
        lines.append("|---|---|---|")
        for entry in sorted(active, key=lambda x: -x["count"]):
            lines.append(f"| `{entry['repo']}` | {entry['count']} | {entry['url']} |")
    else:
        lines.append("\n_No commits found in this window._")

    report = "\n".join(lines) + "\n"

    # Initialise file with header if it doesn't exist
    if not OUTPUT_FILE.exists():
        OUTPUT_FILE.write_text("# GitHub Commit Log\n\nGenerated automatically every 6 hours.\n")

    with OUTPUT_FILE.open("a") as f:
        f.write(report)

    print(f"\nReport appended to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Fetch commits from the last 6 hours across all accessible repos and append to a markdown log."""

import os
import sys
from datetime import datetime, timedelta, timezone
from urllib.request import urlopen, Request
from urllib.error import HTTPError
import json

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
API_BASE = "https://api.github.com"
WINDOW_HOURS = 6
OUTPUT_FILE = "commit-tracker.md"


def gh_get(path, params=""):
    url = f"{API_BASE}{path}{'?' + params if params else ''}"
    req = Request(url, headers={
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    })
    with urlopen(req) as resp:
        return json.loads(resp.read())


def fetch_all_pages(path, params=""):
    results = []
    page = 1
    while True:
        sep = "&" if params else ""
        data = gh_get(path, f"{params}{sep}per_page=100&page={page}")
        if not data:
            break
        results.extend(data)
        if len(data) < 100:
            break
        page += 1
    return results


def main():
    since = datetime.now(timezone.utc) - timedelta(hours=WINDOW_HOURS)
    since_iso = since.strftime("%Y-%m-%dT%H:%M:%SZ")
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Fetch repos the authenticated user can access
    repos = fetch_all_pages("/user/repos", "affiliation=owner,collaborator,organization_member&sort=pushed")

    report_lines = []
    total_commits = 0
    active_repos = []

    for repo in repos:
        full_name = repo["full_name"]
        default_branch = repo.get("default_branch", "main")
        try:
            commits = fetch_all_pages(
                f"/repos/{full_name}/commits",
                f"sha={default_branch}&since={since_iso}"
            )
        except HTTPError as e:
            if e.code in (404, 409):  # empty or inaccessible repo
                continue
            raise

        if commits:
            count = len(commits)
            total_commits += count
            active_repos.append((full_name, count, commits))

    # Build markdown section
    report_lines.append(f"## {now_iso}  —  last {WINDOW_HOURS}h window\n")
    report_lines.append(f"**Total commits:** {total_commits}  |  **Repos with activity:** {len(active_repos)}\n")

    if active_repos:
        report_lines.append("")
        report_lines.append("| Repository | Commits |")
        report_lines.append("|------------|---------|")
        for full_name, count, commits in sorted(active_repos, key=lambda x: -x[1]):
            report_lines.append(f"| [{full_name}](https://github.com/{full_name}) | {count} |")

        report_lines.append("")
        report_lines.append("<details><summary>Commit details</summary>\n")
        for full_name, count, commits in active_repos:
            report_lines.append(f"\n**{full_name}**\n")
            for c in commits:
                sha = c["sha"][:7]
                msg = c["commit"]["message"].split("\n")[0][:100]
                author = c["commit"]["author"]["name"]
                date = c["commit"]["author"]["date"]
                report_lines.append(f"- `{sha}` {msg} — *{author}* @ {date}")
        report_lines.append("\n</details>")
    else:
        report_lines.append("\n_No commits in this window._")

    report_lines.append("\n---\n")
    section = "\n".join(report_lines)

    # Prepend to file (newest first), creating it with a header if absent
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE) as f:
            existing = f.read()
        # Strip the header line so we can rewrite it at the top
        body = existing
        if existing.startswith("# Commit Tracker"):
            body = existing[existing.index("\n") + 1:].lstrip()
        content = f"# Commit Tracker\n\n{section}\n{body}"
    else:
        content = f"# Commit Tracker\n\n{section}"

    with open(OUTPUT_FILE, "w") as f:
        f.write(content)

    print(f"Done. {total_commits} commits across {len(active_repos)} repos → {OUTPUT_FILE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

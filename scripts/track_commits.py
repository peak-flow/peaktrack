#!/usr/bin/env python3
"""
Fetch all commits made in the last 6 hours across all accessible repos
and append a summary to commit-reports/report.md.
"""

import os
import sys
from datetime import datetime, timezone, timedelta
from urllib.request import urlopen, Request
from urllib.error import HTTPError
import json

TOKEN = os.environ.get("GITHUB_TOKEN", "")
API = "https://api.github.com"
HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}
REPORT_FILE = "commit-reports/report.md"


def gh(path, params=None):
    url = f"{API}{path}"
    if params:
        qs = "&".join(f"{k}={v}" for k, v in params.items())
        url = f"{url}?{qs}"
    req = Request(url, headers=HEADERS)
    try:
        with urlopen(req, timeout=15) as r:
            return json.loads(r.read())
    except HTTPError as e:
        if e.code == 409:  # empty repo
            return []
        raise


def get_user():
    return gh("/user")["login"]


def get_repos(user):
    repos = []
    page = 1
    while True:
        page_data = gh("/user/repos", {"affiliation": "owner,collaborator", "per_page": 100, "page": page})
        if not page_data:
            break
        repos.extend(page_data)
        if len(page_data) < 100:
            break
        page += 1
    return repos


def get_commits_since(owner, repo, since_iso):
    try:
        return gh(f"/repos/{owner}/{repo}/commits", {"since": since_iso, "per_page": 100})
    except HTTPError:
        return []


def main():
    now = datetime.now(timezone.utc)
    since = now - timedelta(hours=6)
    since_iso = since.strftime("%Y-%m-%dT%H:%M:%SZ")
    window_str = f"{since.strftime('%Y-%m-%d %H:%M')} – {now.strftime('%Y-%m-%d %H:%M')} UTC"

    user = get_user()
    repos = get_repos(user)

    results = []
    total = 0

    for repo in repos:
        owner = repo["owner"]["login"]
        name = repo["name"]
        full = repo["full_name"]
        if repo.get("archived") or repo.get("disabled"):
            continue
        commits = get_commits_since(owner, name, since_iso)
        if not commits:
            continue
        count = len(commits)
        total += count
        entries = []
        for c in commits:
            sha = c["sha"][:7]
            msg = c["commit"]["message"].splitlines()[0][:80]
            author = c["commit"]["author"]["name"]
            ts = c["commit"]["author"]["date"]
            entries.append(f"  - `{sha}` **{author}** – {msg} _{ts}_")
        results.append((full, count, entries))

    results.sort(key=lambda x: -x[1])

    os.makedirs("commit-reports", exist_ok=True)

    lines = []
    lines.append(f"\n## {now.strftime('%Y-%m-%d %H:%M UTC')}  —  {total} commit{'s' if total != 1 else ''} in last 6 h\n")
    lines.append(f"_Window: {window_str}_\n")

    if not results:
        lines.append("\n_No commits found._\n")
    else:
        for full, count, entries in results:
            lines.append(f"\n### [{full}](https://github.com/{full})  ({count} commit{'s' if count != 1 else ''})\n")
            lines.extend(e + "\n" for e in entries)

    lines.append("\n---\n")

    header_needed = not os.path.exists(REPORT_FILE) or os.path.getsize(REPORT_FILE) == 0
    with open(REPORT_FILE, "a") as f:
        if header_needed:
            f.write("# Commit Activity Report\n\n")
            f.write("Auto-generated every 6 hours by GitHub Actions.\n")
        f.writelines(lines)

    print(f"Logged {total} commits across {len(results)} repos → {REPORT_FILE}")


if __name__ == "__main__":
    main()

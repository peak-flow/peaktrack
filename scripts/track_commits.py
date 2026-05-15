#!/usr/bin/env python3
"""Fetch commits from the last 6 hours across all accessible repos and append to commit-log.md."""

import os
import sys
from datetime import datetime, timezone, timedelta
from urllib.request import urlopen, Request
from urllib.error import HTTPError
import json

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
API = "https://api.github.com"
LOOKBACK_HOURS = 6
OUTPUT_FILE = "commit-log.md"


def gh(path, params=""):
    url = f"{API}{path}{'?' + params if params else ''}"
    req = Request(url, headers={
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    })
    try:
        with urlopen(req) as r:
            return json.loads(r.read())
    except HTTPError as e:
        body = e.read().decode()
        print(f"HTTP {e.code} for {url}: {body}", file=sys.stderr)
        return None


def get_repos():
    """Return list of {full_name, owner, name} for the authenticated user's repos."""
    repos = []
    page = 1
    while True:
        data = gh(f"/user/repos", f"per_page=100&page={page}&sort=pushed&affiliation=owner,collaborator")
        if not data:
            break
        repos.extend(data)
        if len(data) < 100:
            break
        page += 1
    return repos


def count_commits_since(owner, repo, since_iso):
    """Return list of commit summaries made since `since_iso`."""
    data = gh(f"/repos/{owner}/{repo}/commits", f"since={since_iso}&per_page=100")
    if not data or isinstance(data, dict):  # error dict
        return []
    return [
        {
            "sha": c["sha"][:7],
            "author": (c["commit"]["author"] or {}).get("name", "unknown"),
            "message": c["commit"]["message"].split("\n")[0][:80],
        }
        for c in data
    ]


def append_report(entries, since, until):
    """Append a markdown section to OUTPUT_FILE."""
    lines = [
        f"\n## {until.strftime('%Y-%m-%d %H:%M UTC')} — last {LOOKBACK_HOURS}h window\n",
        f"**Period:** {since.strftime('%Y-%m-%d %H:%M UTC')} → {until.strftime('%Y-%m-%d %H:%M UTC')}\n",
    ]

    total = sum(len(v) for v in entries.values())
    lines.append(f"**Total commits:** {total}\n")

    if not entries:
        lines.append("\n_No commits found._\n")
    else:
        for repo_name, commits in sorted(entries.items(), key=lambda x: -len(x[1])):
            lines.append(f"\n### `{repo_name}` — {len(commits)} commit{'s' if len(commits) != 1 else ''}\n")
            for c in commits:
                lines.append(f"- [`{c['sha']}`] **{c['author']}**: {c['message']}\n")

    lines.append("\n---\n")

    # Ensure file has a header on first write
    try:
        existing = open(OUTPUT_FILE).read()
    except FileNotFoundError:
        existing = ""

    if not existing:
        header = "# GitHub Commit Tracker\n\nAutomatically updated every 6 hours.\n"
        with open(OUTPUT_FILE, "w") as f:
            f.write(header)

    with open(OUTPUT_FILE, "a") as f:
        f.writelines(lines)

    print(f"Appended report: {total} commits across {len(entries)} repos.")


def main():
    if not GITHUB_TOKEN:
        print("GITHUB_TOKEN not set", file=sys.stderr)
        sys.exit(1)

    now = datetime.now(timezone.utc)
    since = now - timedelta(hours=LOOKBACK_HOURS)
    since_iso = since.strftime("%Y-%m-%dT%H:%M:%SZ")

    repos = get_repos()
    print(f"Scanning {len(repos)} repos since {since_iso}...")

    entries = {}
    for repo in repos:
        owner = repo["owner"]["login"]
        name = repo["name"]
        full = repo["full_name"]
        commits = count_commits_since(owner, name, since_iso)
        if commits:
            entries[full] = commits
            print(f"  {full}: {len(commits)} commit(s)")

    append_report(entries, since, now)


if __name__ == "__main__":
    main()

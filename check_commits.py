#!/usr/bin/env python3
"""
Checks peak-flow/peaktrack for commits in the last 6 hours and appends
a summary to commit_log.md. Requires GITHUB_TOKEN env var.
"""

import os
import sys
import json
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta

OWNER = "peak-flow"
REPO = "peaktrack"
LOG_FILE = os.path.join(os.path.dirname(__file__), "commit_log.md")
WINDOW_HOURS = 6


def github_get(path, token):
    url = f"https://api.github.com{path}"
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    })
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def get_branches(token):
    branches, page = [], 1
    while True:
        batch = github_get(f"/repos/{OWNER}/{REPO}/branches?per_page=100&page={page}", token)
        if not batch:
            break
        branches.extend(b["name"] for b in batch)
        page += 1
    return branches


def get_commits_since(branch, since_iso, token):
    commits, page = [], 1
    while True:
        batch = github_get(
            f"/repos/{OWNER}/{REPO}/commits?sha={branch}&since={since_iso}&per_page=100&page={page}",
            token,
        )
        if not batch:
            break
        commits.extend(batch)
        page += 1
    return commits


def fmt_dt(iso_str):
    dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
    return dt.strftime("%Y-%m-%d %H:%M")


def main():
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("ERROR: GITHUB_TOKEN environment variable not set.", file=sys.stderr)
        sys.exit(1)

    now = datetime.now(timezone.utc)
    window_start = now - timedelta(hours=WINDOW_HOURS)
    since_iso = window_start.strftime("%Y-%m-%dT%H:%M:%SZ")

    branches = get_branches(token)

    # Collect unique commits (by SHA) with their branch
    seen_shas = {}  # sha -> {branch, author, date, message}
    for branch in branches:
        commits = get_commits_since(branch, since_iso, token)
        for c in commits:
            sha = c["sha"]
            if sha not in seen_shas:
                author_name = (
                    c.get("commit", {}).get("author", {}).get("name")
                    or c.get("author", {}).get("login", "unknown")
                )
                seen_shas[sha] = {
                    "branch": branch,
                    "sha": sha[:7],
                    "author": author_name,
                    "date": fmt_dt(c["commit"]["author"]["date"]),
                    "message": c["commit"]["message"].splitlines()[0][:80],
                }

    total = len(seen_shas)
    window_label = (
        f"{window_start.strftime('%H:%M')} → {now.strftime('%H:%M')} UTC"
    )
    check_ts = now.strftime("%Y-%m-%d %H:%M UTC")

    header = f"\n## Check: {check_ts} | Window: {window_label} | Total: {total} commit{'s' if total != 1 else ''}\n"

    if total == 0:
        body = "\n_No commits in this window._\n"
    else:
        rows = "\n".join(
            f"| {v['branch']} | `{v['sha']}` | {v['author']} | {v['date']} | {v['message']} |"
            for v in seen_shas.values()
        )
        body = (
            "\n| Branch | SHA | Author | Date (UTC) | Message |\n"
            "|--------|-----|--------|------------|----------|\n"
            f"{rows}\n"
        )

    entry = header + body + "\n---\n"

    with open(LOG_FILE, "a") as f:
        f.write(entry)

    print(f"[{check_ts}] Appended {total} commit(s) to commit_log.md")


if __name__ == "__main__":
    main()

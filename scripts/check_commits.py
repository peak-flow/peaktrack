#!/usr/bin/env python3
"""Fetch commits from the last 6 hours for peak-flow/peaktrack and append to commit_log.md."""

import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

REPO = "peak-flow/peaktrack"
LOG_FILE = "/home/user/peaktrack/commit_log.md"
WINDOW_HOURS = 6

token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
BASE_HEADERS = {"Accept": "application/vnd.github.v3+json", "User-Agent": "peaktrack-commit-logger"}
if token:
    BASE_HEADERS["Authorization"] = f"token {token}"


def gh_get(url):
    req = urllib.request.Request(url, headers=BASE_HEADERS)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def paginate(url):
    results, page = [], 1
    while True:
        sep = "&" if "?" in url else "?"
        batch = gh_get(f"{url}{sep}per_page=100&page={page}")
        if not batch:
            break
        results.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return results


def main():
    now = datetime.now(timezone.utc)
    since = (now - timedelta(hours=WINDOW_HOURS)).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Collect commits across all branches, deduplicated by SHA
    try:
        branches = paginate(f"https://api.github.com/repos/{REPO}/branches")
    except urllib.error.HTTPError as e:
        print(f"Failed to list branches: {e}")
        branches = [{"name": "main"}]

    commit_map = {}   # sha -> {commit data}
    sha_branches = {}  # sha -> [branch names]

    for branch in branches:
        bname = branch["name"]
        try:
            commits = paginate(
                f"https://api.github.com/repos/{REPO}/commits?sha={bname}&since={since}"
            )
        except urllib.error.HTTPError:
            continue
        for c in commits:
            sha = c["sha"]
            if sha not in commit_map:
                commit_map[sha] = c
                sha_branches[sha] = []
            if bname not in sha_branches[sha]:
                sha_branches[sha].append(bname)

    total = len(commit_map)
    authors = list(dict.fromkeys(
        c["commit"]["author"]["name"] for c in commit_map.values()
    ))
    branches_touched = sorted({b for blist in sha_branches.values() for b in blist})

    timestamp = now.strftime("%Y-%m-%d %H:%M UTC")
    entry = (
        f"\n## {timestamp}\n"
        f"- Repo: {REPO}\n"
        f"- Commits in last {WINDOW_HOURS} hours: {total}\n"
        f"- Authors: {', '.join(authors) if authors else 'none'}\n"
        f"- Branches touched: {', '.join(branches_touched) if branches_touched else 'none'}\n"
    )

    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, "w") as f:
            f.write("# GitHub Commit Log\n\nAuto-generated every 6 hours.\n")

    with open(LOG_FILE, "a") as f:
        f.write(entry)

    print(f"[{timestamp}] Logged {total} commit(s) across {len(branches_touched)} branch(es) to {LOG_FILE}")
    if not token:
        print("Warning: No GITHUB_TOKEN set — using unauthenticated API (60 req/hr limit).")


if __name__ == "__main__":
    main()

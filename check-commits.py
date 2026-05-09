#!/usr/bin/env python3
"""Check GitHub commits across peak-flow org in the last 6 hours and log to markdown."""

import os
import json
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, timedelta, timezone

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
ORG = "peak-flow"
LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "github-commit-log.md")
HOURS_BACK = 6
HEADER = "# GitHub Commit Log — peak-flow\n\n_Auto-generated every 6 hours via check-commits.py + cron._\n\n---\n"


def github_request(url, extra_headers=None):
    headers = {
        "Accept": "application/vnd.github.cloak-preview+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "peak-flow-commit-checker",
    }
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    if extra_headers:
        headers.update(extra_headers)
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read()), int(resp.headers.get("X-RateLimit-Remaining", 999))
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        raise RuntimeError(f"GitHub API error {e.code}: {body}") from e


def fetch_all_commits(since_iso):
    """Use commit search API to find all org commits since the given timestamp."""
    query = f"org:{ORG} committer-date:>{since_iso}"
    encoded_query = urllib.parse.quote(query)
    repo_counts = {}
    page = 1

    while True:
        url = (
            f"https://api.github.com/search/commits"
            f"?q={encoded_query}&sort=committer-date&order=desc&per_page=100&page={page}"
        )
        data, remaining = github_request(url)
        items = data.get("items", [])
        for item in items:
            repo = item["repository"]["full_name"]
            repo_counts[repo] = repo_counts.get(repo, 0) + 1

        # Stop if we have all results or hit the API page cap (10 pages = 1000 results)
        total = data.get("total_count", 0)
        fetched_so_far = (page - 1) * 100 + len(items)
        if fetched_so_far >= total or len(items) < 100 or page >= 10:
            break
        page += 1

    return repo_counts, data.get("total_count", sum(repo_counts.values()))


def build_entry(now, repo_counts, api_total):
    timestamp = now.strftime("%Y-%m-%d %H:%M UTC")
    shown_total = sum(repo_counts.values())
    lines = [f"\n## {timestamp}\n\n"]

    if api_total > shown_total:
        lines.append(
            f"**Total commits in last {HOURS_BACK}h:** {api_total} "
            f"_(showing top {shown_total} from search API)_\n"
        )
    else:
        lines.append(f"**Total commits in last {HOURS_BACK}h:** {api_total}\n")

    if repo_counts:
        lines.append("\n| Repository | Commits |\n|---|---|\n")
        for repo, count in sorted(repo_counts.items(), key=lambda x: -x[1]):
            lines.append(f"| `{repo}` | {count} |\n")
    else:
        lines.append("\n_No commits found in the last 6 hours._\n")

    return "".join(lines)


def update_log(entry):
    try:
        with open(LOG_FILE, "r") as f:
            existing = f.read()
    except FileNotFoundError:
        existing = HEADER

    # Insert new entry right after the header/separator
    separator = "---\n"
    insert_pos = existing.find(separator)
    if insert_pos == -1:
        content = existing + entry
    else:
        insert_pos += len(separator)
        content = existing[:insert_pos] + entry + existing[insert_pos:]

    with open(LOG_FILE, "w") as f:
        f.write(content)


def main():
    if not GITHUB_TOKEN:
        print("WARNING: GITHUB_TOKEN not set — unauthenticated requests are rate-limited to 10/min.")

    now = datetime.now(timezone.utc)
    since = now - timedelta(hours=HOURS_BACK)
    since_iso = since.strftime("%Y-%m-%dT%H:%M:%SZ")

    print(f"Checking commits in org '{ORG}' since {since_iso} ...")
    repo_counts, api_total = fetch_all_commits(since_iso)
    entry = build_entry(now, repo_counts, api_total)
    update_log(entry)

    print(f"Done. {api_total} commit(s) across {len(repo_counts)} repo(s).")
    print(entry)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Fetch commits from the peak-flow org in the last 6 hours and append to commit-log.md."""
import json
import os
import sys
import urllib.request
import urllib.parse
from datetime import datetime, timedelta, timezone


def fetch_page(url, headers):
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code}: {e.read().decode()}", file=sys.stderr)
        return {"total_count": 0, "items": []}


def main():
    token = os.environ.get("GH_TOKEN", "")
    if not token:
        print("GH_TOKEN not set", file=sys.stderr)
        sys.exit(1)

    now = datetime.now(timezone.utc)
    since = (now - timedelta(hours=6)).strftime("%Y-%m-%dT%H:%M:%SZ")
    now_str = now.strftime("%Y-%m-%d %H:%M UTC")

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    query = f"org:peak-flow committer-date:>={since}"
    base_url = (
        "https://api.github.com/search/commits"
        f"?q={urllib.parse.quote(query)}"
        "&sort=committer-date&order=desc&per_page=100"
    )

    all_items = []
    page = 1
    while True:
        data = fetch_page(f"{base_url}&page={page}", headers)
        items = data.get("items", [])
        all_items.extend(items)
        total_count = data.get("total_count", 0)
        if len(items) < 100 or len(all_items) >= total_count:
            break
        page += 1

    repo_counts = {}
    for item in all_items:
        repo = item.get("repository", {}).get("full_name", "unknown")
        repo_counts[repo] = repo_counts.get(repo, 0) + 1

    total = sum(repo_counts.values())

    lines = [f"\n## {now_str}"]
    lines.append(f"**Total commits in last 6h: {total}**\n")

    if total == 0:
        lines.append("> _(no commits in last 6h)_\n")
    else:
        lines.append("| Repository | Commits |")
        lines.append("|---|---|")
        for repo, count in sorted(repo_counts.items(), key=lambda x: -x[1]):
            lines.append(f"| {repo} | {count} |")
        lines.append("")

    section = "\n".join(lines) + "\n"

    log_path = "commit-log.md"
    if not os.path.exists(log_path):
        with open(log_path, "w") as f:
            f.write("# Commit Activity Log\n\nTracked every 6 hours across the `peak-flow` org.\n")

    with open(log_path, "a") as f:
        f.write(section)

    print(f"Logged {total} commits across {len(repo_counts)} repos")

    env_file = os.environ.get("GITHUB_ENV", "")
    if env_file:
        top_repos = ", ".join(
            f"{r} ({c})" for r, c in sorted(repo_counts.items(), key=lambda x: -x[1])[:5]
        )
        with open(env_file, "a") as f:
            f.write(f"COMMIT_TOTAL={total}\n")
            f.write(f"COMMIT_SUMMARY={top_repos}\n")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Query GitHub for commits in the last 6 hours across the peak-flow org and append to commit-log.md."""

import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone

ORG = "peak-flow"
HOURS = 6
LOG_FILE = "commit-log.md"


def gh_search_commits(since: str, page: int = 1) -> dict:
    result = subprocess.run(
        [
            "gh", "api", "search/commits",
            "-X", "GET",
            "-f", f"q=org:{ORG} committer-date:>={since}",
            "-f", "per_page=100",
            "-f", f"page={page}",
            "-f", "sort=committer-date",
            "-f", "order=desc",
            "-H", "Accept: application/vnd.github+json",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout)


now = datetime.now(timezone.utc)
since = (now - timedelta(hours=HOURS)).strftime("%Y-%m-%dT%H:%M:%SZ")
now_str = now.strftime("%Y-%m-%d %H:%M:%S UTC")

print(f"Searching commits in org:{ORG} since {since}")

# Paginate through all results (API caps at 1000; 100 per page)
all_items = []
data = gh_search_commits(since, page=1)
total_reported = data.get("total_count", 0)
all_items.extend(data.get("items", []))

page = 2
while len(all_items) < total_reported and len(data.get("items", [])) == 100:
    data = gh_search_commits(since, page=page)
    all_items.extend(data.get("items", []))
    page += 1

# Count commits per repo
repo_counts: dict[str, int] = {}
for item in all_items:
    repo = item["repository"]["full_name"]
    repo_counts[repo] = repo_counts.get(repo, 0) + 1

total = len(all_items)
sorted_repos = sorted(repo_counts.items(), key=lambda x: -x[1])

# Build markdown section
section_lines = [
    f"\n## Check: {now_str}\n",
    f"**Total commits in last {HOURS}h:** {total}\n",
]

if total == 0:
    section_lines.append("\n_No commits found in this period._\n")
else:
    section_lines.append("\n| Repo | Commits |")
    section_lines.append("|------|---------|")
    for repo, count in sorted_repos:
        section_lines.append(f"| {repo} | {count} |")

section_lines.append("\n---\n")

with open(LOG_FILE, "a") as f:
    f.write("\n".join(section_lines) + "\n")

print(f"Done: {total} commits across {len(repo_counts)} repos")
for repo, count in sorted_repos:
    print(f"  {repo}: {count}")

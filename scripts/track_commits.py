#!/usr/bin/env python3
"""Count commits made in the last 6 hours across all accessible repos and append to a markdown log."""

import os
import sys
from datetime import datetime, timezone, timedelta
from urllib.request import urlopen, Request
from urllib.error import HTTPError
import json

TOKEN = os.environ.get("GITHUB_TOKEN", "")
ORG = os.environ.get("GITHUB_ORG", "")
HOURS = int(os.environ.get("LOOKBACK_HOURS", "6"))
OUTPUT_FILE = os.environ.get("OUTPUT_FILE", "commit_log.md")

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}


def gh_get(url):
    results = []
    while url:
        req = Request(url, headers=HEADERS)
        with urlopen(req) as resp:
            data = json.loads(resp.read())
            if isinstance(data, list):
                results.extend(data)
            else:
                return data
            link = resp.headers.get("Link", "")
            url = None
            for part in link.split(","):
                if 'rel="next"' in part:
                    url = part.split(";")[0].strip().strip("<>")
    return results


def list_repos():
    if ORG:
        return gh_get(f"https://api.github.com/orgs/{ORG}/repos?per_page=100&type=all")
    # Fall back to authenticated user's repos
    return gh_get("https://api.github.com/user/repos?per_page=100&affiliation=owner,collaborator")


def count_commits_since(repo_full_name, since_iso):
    url = f"https://api.github.com/repos/{repo_full_name}/commits?since={since_iso}&per_page=100"
    try:
        commits = gh_get(url)
        return commits if isinstance(commits, list) else []
    except HTTPError as e:
        if e.code in (409, 404):  # empty repo or no access
            return []
        raise


def main():
    now = datetime.now(timezone.utc)
    since = now - timedelta(hours=HOURS)
    since_iso = since.strftime("%Y-%m-%dT%H:%M:%SZ")

    repos = list_repos()
    if not repos:
        print("No repos found.", file=sys.stderr)
        sys.exit(1)

    results = []
    total = 0
    for repo in repos:
        name = repo["full_name"]
        commits = count_commits_since(name, since_iso)
        count = len(commits)
        if count > 0:
            results.append((name, count, commits))
            total += count

    # Build markdown section
    window_label = f"{since.strftime('%Y-%m-%d %H:%M')} UTC — {now.strftime('%Y-%m-%d %H:%M')} UTC"
    lines = [
        f"## {now.strftime('%Y-%m-%d %H:%M')} UTC  |  Last {HOURS}h window",
        "",
        f"**Period:** {window_label}  ",
        f"**Total commits:** {total}  ",
        f"**Repos with activity:** {len(results)}",
        "",
    ]

    if results:
        lines.append("| Repository | Commits |")
        lines.append("|---|---|")
        for name, count, _ in sorted(results, key=lambda x: -x[1]):
            lines.append(f"| `{name}` | {count} |")
    else:
        lines.append("_No commits in this window._")

    lines.append("")
    lines.append("---")
    lines.append("")

    block = "\n".join(lines)

    # Prepend to file (newest entry at top, header only once)
    existing = ""
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE) as f:
            existing = f.read()
        # Strip existing header so we re-add it once at the top
        existing = existing.removeprefix("# Commit Activity Log\n\n")

    with open(OUTPUT_FILE, "w") as f:
        f.write("# Commit Activity Log\n\n" + block + existing)

    print(f"Logged {total} commits across {len(results)} repos → {OUTPUT_FILE}")


if __name__ == "__main__":
    main()

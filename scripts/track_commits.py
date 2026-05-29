#!/usr/bin/env python3
"""
Query all peak-flow repos for commits in the last 6 hours and append a
Markdown report to commit-reports/COMMIT_LOG.md.
"""

import os
import sys
import requests
from datetime import datetime, timedelta, timezone

OWNER = "peak-flow"
REPORT_FILE = "commit-reports/COMMIT_LOG.md"
HOURS_BACK = 6

token = os.environ.get("GH_TOKEN", "")
if not token:
    print("ERROR: GH_TOKEN is not set.", file=sys.stderr)
    sys.exit(1)

session = requests.Session()
session.headers.update({
    "Authorization": f"Bearer {token}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
})


def paginate(url, params=None):
    """Yield all items from a paginated GitHub API endpoint."""
    params = dict(params or {})
    params.setdefault("per_page", 100)
    page = 1
    while True:
        params["page"] = page
        r = session.get(url, params=params, timeout=30)
        if r.status_code == 409:  # empty repo
            break
        r.raise_for_status()
        data = r.json()
        if not data:
            break
        yield from data
        if len(data) < params["per_page"]:
            break
        page += 1


def get_repos():
    return list(paginate(f"https://api.github.com/users/{OWNER}/repos"))


def get_commit_count(repo_name, since_iso):
    url = f"https://api.github.com/repos/{OWNER}/{repo_name}/commits"
    commits = []
    try:
        for c in paginate(url, {"since": since_iso}):
            commits.append(c)
            if len(commits) >= 500:  # hard cap per repo per window
                break
    except requests.HTTPError as e:
        if e.response.status_code in (409, 404, 403):
            return 0
        raise
    return len(commits)


def main():
    now = datetime.now(timezone.utc)
    since = now - timedelta(hours=HOURS_BACK)
    since_iso = since.strftime("%Y-%m-%dT%H:%M:%SZ")

    print(f"Scanning {OWNER} repos for commits since {since_iso} …")

    repos = get_repos()
    print(f"Found {len(repos)} repos.")

    active = []
    for repo in repos:
        name = repo["name"]
        count = get_commit_count(name, since_iso)
        if count:
            active.append({"repo": name, "count": count})
            print(f"  {name}: {count} commit(s)")

    total = sum(r["count"] for r in active)
    active.sort(key=lambda x: -x["count"])

    # Build markdown section
    header = f"## {now.strftime('%Y-%m-%d %H:%M UTC')} — last {HOURS_BACK} hours\n"
    if active:
        body = (
            f"**{total} commit(s)** across **{len(active)} repo(s)**\n\n"
            "| Repository | Commits |\n"
            "|---|---:|\n"
        )
        body += "".join(f"| `{r['repo']}` | {r['count']} |\n" for r in active)
    else:
        body = "_No commits in the last 6 hours._\n"

    entry = f"\n{header}\n{body}\n---\n"

    os.makedirs(os.path.dirname(REPORT_FILE), exist_ok=True)

    # Prepend so the newest report is always at the top
    existing = ""
    if os.path.exists(REPORT_FILE):
        with open(REPORT_FILE) as f:
            existing = f.read()

    title_block = "# Commit Activity Log\n\nNewest entries are at the top.\n"
    if existing.startswith(title_block):
        new_content = title_block + entry + existing[len(title_block):]
    else:
        new_content = title_block + entry + existing

    with open(REPORT_FILE, "w") as f:
        f.write(new_content)

    print(f"Report written to {REPORT_FILE}  ({total} total commits)")


if __name__ == "__main__":
    main()

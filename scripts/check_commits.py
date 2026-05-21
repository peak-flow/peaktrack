#!/usr/bin/env python3
"""
Fetches commits made in the last 6 hours across all accessible GitHub repos
and writes a markdown summary report.
"""

import os
import sys
import json
from datetime import datetime, timezone, timedelta
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError

GITHUB_TOKEN = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
GITHUB_API = "https://api.github.com"
REPORT_DIR = os.environ.get("REPORT_DIR", "commit-reports")
HOURS = int(os.environ.get("LOOKBACK_HOURS", "6"))


def gh_get(path, params=None):
    url = f"{GITHUB_API}{path}"
    if params:
        qs = "&".join(f"{k}={v}" for k, v in params.items())
        url = f"{url}?{qs}"
    req = Request(url, headers={
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    })
    try:
        with urlopen(req) as resp:
            return json.loads(resp.read())
    except HTTPError as e:
        print(f"  HTTP {e.code} for {url}", file=sys.stderr)
        return None


def get_repos(org=None):
    """Return list of repos — org repos if org given, else authenticated user's repos."""
    results = []
    page = 1
    if org:
        endpoint = f"/orgs/{org}/repos"
    else:
        endpoint = "/user/repos"

    while True:
        data = gh_get(endpoint, {"per_page": "100", "page": str(page)})
        if not data:
            break
        results.extend(data)
        if len(data) < 100:
            break
        page += 1
    return results


def get_commits_since(owner, repo, since_iso):
    """Return commits on the default branch since the given ISO timestamp."""
    data = gh_get(f"/repos/{owner}/{repo}/commits", {
        "since": since_iso,
        "per_page": "100",
    })
    if not data:
        return []
    return data


def build_report(since, until, repo_commits):
    lines = []
    lines.append(f"# Commit Report")
    lines.append(f"")
    lines.append(f"**Period:** {since.strftime('%Y-%m-%d %H:%M UTC')} → {until.strftime('%Y-%m-%d %H:%M UTC')}  ")
    lines.append(f"**Generated:** {until.strftime('%Y-%m-%d %H:%M UTC')}")
    lines.append(f"")

    total = sum(len(v) for v in repo_commits.values())
    active_repos = {k: v for k, v in repo_commits.items() if v}

    lines.append(f"## Summary")
    lines.append(f"")
    lines.append(f"- **Total commits:** {total}")
    lines.append(f"- **Active repos:** {len(active_repos)}")
    lines.append(f"- **Repos checked:** {len(repo_commits)}")
    lines.append(f"")

    if not active_repos:
        lines.append("_No commits in this period._")
        return "\n".join(lines)

    lines.append(f"## Commits by Repository")
    lines.append(f"")

    for full_name, commits in sorted(active_repos.items(), key=lambda x: -len(x[1])):
        lines.append(f"### `{full_name}` — {len(commits)} commit{'s' if len(commits) != 1 else ''}")
        lines.append(f"")
        lines.append(f"| SHA | Author | Message | Time |")
        lines.append(f"|-----|--------|---------|------|")
        for c in commits:
            sha = c["sha"][:7]
            author = (c.get("commit", {}).get("author") or {}).get("name", "unknown")
            msg = (c.get("commit", {}).get("message") or "").split("\n")[0][:72]
            msg = msg.replace("|", "\\|")
            ts = (c.get("commit", {}).get("author") or {}).get("date", "")[:16].replace("T", " ")
            url = c.get("html_url", "")
            lines.append(f"| [`{sha}`]({url}) | {author} | {msg} | {ts} |")
        lines.append(f"")

    return "\n".join(lines)


def main():
    if not GITHUB_TOKEN:
        print("ERROR: GH_TOKEN or GITHUB_TOKEN environment variable not set.", file=sys.stderr)
        sys.exit(1)

    org = os.environ.get("GITHUB_ORG")  # optional: limit to an org
    until = datetime.now(timezone.utc)
    since = until - timedelta(hours=HOURS)
    since_iso = since.strftime("%Y-%m-%dT%H:%M:%SZ")

    print(f"Checking commits since {since_iso} ...")

    repos = get_repos(org)
    print(f"Found {len(repos)} repos to check.")

    repo_commits = {}
    for repo in repos:
        full_name = repo["full_name"]
        owner, name = full_name.split("/", 1)
        if repo.get("archived"):
            continue
        print(f"  Checking {full_name} ...")
        commits = get_commits_since(owner, name, since_iso)
        repo_commits[full_name] = commits

    report = build_report(since, until, repo_commits)

    os.makedirs(REPORT_DIR, exist_ok=True)
    filename = f"{REPORT_DIR}/{until.strftime('%Y-%m-%d_%H%M')}.md"
    with open(filename, "w") as f:
        f.write(report)
    print(f"Report written to {filename}")

    # Also update a rolling summary index
    index_path = f"{REPORT_DIR}/README.md"
    entries = []
    if os.path.exists(index_path):
        with open(index_path) as f:
            existing = f.read()
        # Keep existing lines that aren't the header block
        for line in existing.splitlines():
            if line.startswith("- ["):
                entries.append(line)

    link = f"- [{until.strftime('%Y-%m-%d %H:%M UTC')}](./{os.path.basename(filename)}) — {sum(len(v) for v in repo_commits.values())} commits across {len([v for v in repo_commits.values() if v])} repos"
    entries.insert(0, link)
    entries = entries[:100]  # keep last 100 entries

    with open(index_path, "w") as f:
        f.write("# Commit Activity Reports\n\n")
        f.write("Auto-generated every 6 hours. Most recent first.\n\n")
        f.write("\n".join(entries) + "\n")
    print(f"Index updated at {index_path}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Fetches all commits made in the last 6 hours across accessible GitHub repos
and appends a summary to commit_log.md.
"""

import os
import sys
from datetime import datetime, timezone, timedelta
import requests

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN") or (
    open(os.path.expanduser("~/.github_token")).read().strip()
    if os.path.exists(os.path.expanduser("~/.github_token"))
    else None
)

if not GITHUB_TOKEN:
    print("ERROR: No GitHub token found. Set GITHUB_TOKEN env var or create ~/.github_token", file=sys.stderr)
    sys.exit(1)

HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}
BASE_URL = "https://api.github.com"
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "..", "commit_log.md")
WINDOW_HOURS = 6


def paginate(url, params=None):
    results = []
    while url:
        resp = requests.get(url, headers=HEADERS, params=params)
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, list):
            results.extend(data)
        else:
            results.append(data)
        url = resp.links.get("next", {}).get("url")
        params = None  # only pass params on first request
    return results


def get_repos():
    repos = paginate(f"{BASE_URL}/user/repos", params={"per_page": 100, "affiliation": "owner,collaborator,organization_member"})
    return repos


def get_commits_since(owner, repo, since_iso):
    try:
        commits = paginate(
            f"{BASE_URL}/repos/{owner}/{repo}/commits",
            params={"since": since_iso, "per_page": 100},
        )
        return commits
    except requests.HTTPError as e:
        if e.response.status_code in (409, 404):
            return []
        raise


def main():
    now = datetime.now(timezone.utc)
    since = now - timedelta(hours=WINDOW_HOURS)
    since_iso = since.strftime("%Y-%m-%dT%H:%M:%SZ")
    window_label = f"{since.strftime('%Y-%m-%d %H:%M')} UTC → {now.strftime('%Y-%m-%d %H:%M')} UTC"

    print(f"Checking commits since {since_iso} ...")

    repos = get_repos()
    print(f"Found {len(repos)} repos")

    repo_commit_data = []
    total = 0

    for repo in repos:
        owner = repo["owner"]["login"]
        name = repo["name"]
        commits = get_commits_since(owner, name, since_iso)
        if commits:
            repo_commit_data.append({
                "full_name": repo["full_name"],
                "html_url": repo["html_url"],
                "count": len(commits),
                "commits": [
                    {
                        "sha": c["sha"][:7],
                        "message": c["commit"]["message"].splitlines()[0],
                        "author": c["commit"]["author"]["name"],
                        "date": c["commit"]["author"]["date"],
                        "url": c["html_url"],
                    }
                    for c in commits
                ],
            })
            total += len(commits)

    # Build markdown section
    lines = [
        f"## {now.strftime('%Y-%m-%d %H:%M')} UTC — {total} commit{'s' if total != 1 else ''} in last {WINDOW_HOURS}h",
        f"",
        f"**Window:** {window_label}  ",
        f"**Total commits:** {total}  ",
        f"**Repos with activity:** {len(repo_commit_data)}",
        f"",
    ]

    if not repo_commit_data:
        lines.append("_No commits found in this window._")
        lines.append("")
    else:
        for r in sorted(repo_commit_data, key=lambda x: -x["count"]):
            lines.append(f"### [{r['full_name']}]({r['html_url']}) — {r['count']} commit{'s' if r['count'] != 1 else ''}")
            lines.append("")
            for c in r["commits"]:
                lines.append(f"- [`{c['sha']}`]({c['url']}) **{c['author']}** {c['date'][:16].replace('T',' ')} UTC — {c['message']}")
            lines.append("")

    lines.append("---")
    lines.append("")
    section = "\n".join(lines)

    # Prepend to file so newest entries are at the top
    output_path = os.path.realpath(OUTPUT_FILE)
    existing = ""
    if os.path.exists(output_path):
        with open(output_path) as f:
            existing = f.read()

    header = "# GitHub Commit Log\n\n"
    if existing.startswith(header):
        new_content = header + section + existing[len(header):]
    else:
        new_content = header + section + existing

    with open(output_path, "w") as f:
        f.write(new_content)

    print(f"Wrote {total} commits across {len(repo_commit_data)} repos to {output_path}")


if __name__ == "__main__":
    main()

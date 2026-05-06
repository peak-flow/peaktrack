#!/usr/bin/env python3
"""
GitHub commit tracker: counts commits across all user repos in the last N hours
and appends a summary to commit_log.md.

Usage:
    GITHUB_TOKEN=<token> python3 check_commits.py [--hours 6]

Environment variables:
    GITHUB_TOKEN  (required) Personal access token with repo read scope
    GITHUB_REPOS  (optional) Comma-separated list of "owner/repo" to check.
                  If unset, all repos visible to the token are checked.
"""

import argparse
import os
import sys
from datetime import datetime, timezone, timedelta
from urllib.request import Request, urlopen
from urllib.error import HTTPError
import json


GITHUB_API = "https://api.github.com"


def gh_get(path: str, token: str) -> list | dict:
    url = f"{GITHUB_API}{path}"
    results = []
    # Follow pagination automatically
    while url:
        req = Request(url, headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        })
        with urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
            if isinstance(data, list):
                results.extend(data)
            else:
                return data  # single-object responses (e.g. /user)
            link = resp.headers.get("Link", "")
            url = _next_link(link)
    return results


def _next_link(header: str) -> str | None:
    for part in header.split(","):
        if 'rel="next"' in part:
            return part.split(";")[0].strip().strip("<>")
    return None


def list_repos(token: str) -> list[str]:
    repos = gh_get("/user/repos?per_page=100&sort=updated", token)
    return [r["full_name"] for r in repos]


def count_commits_since(owner_repo: str, since: datetime, token: str) -> int:
    since_iso = since.strftime("%Y-%m-%dT%H:%M:%SZ")
    path = f"/repos/{owner_repo}/commits?per_page=100&since={since_iso}"
    try:
        commits = gh_get(path, token)
        return len(commits) if isinstance(commits, list) else 0
    except HTTPError as e:
        if e.code in (409, 404):  # empty repo or no access
            return 0
        raise


def build_markdown(results: list[dict], hours: int, since: datetime, now: datetime) -> str:
    total = sum(r["count"] for r in results)
    active = [r for r in results if r["count"] > 0]

    lines = [
        f"## Commit check — {now.strftime('%Y-%m-%d %H:%M UTC')}",
        f"",
        f"**Window:** last {hours} hours (since {since.strftime('%Y-%m-%d %H:%M UTC')})",
        f"**Total commits:** {total} across {len(active)} repo(s) with activity",
        f"",
    ]

    if active:
        lines += ["| Repository | Commits |", "|---|---|"]
        for r in sorted(active, key=lambda x: -x["count"]):
            lines.append(f"| `{r['repo']}` | {r['count']} |")
    else:
        lines.append("_No commits found in this window._")

    lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Track GitHub commits over a time window")
    parser.add_argument("--hours", type=int, default=6, help="Hours to look back (default: 6)")
    parser.add_argument("--output", default="commit_log.md", help="Output markdown file path")
    args = parser.parse_args()

    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("ERROR: GITHUB_TOKEN environment variable is required.", file=sys.stderr)
        sys.exit(1)

    explicit_repos = os.environ.get("GITHUB_REPOS", "").strip()
    repos = [r.strip() for r in explicit_repos.split(",") if r.strip()] if explicit_repos else None

    now = datetime.now(timezone.utc)
    since = now - timedelta(hours=args.hours)

    if repos is None:
        print("Fetching repository list…")
        repos = list_repos(token)
    print(f"Checking {len(repos)} repo(s) for commits since {since.strftime('%Y-%m-%d %H:%M UTC')}…")

    results = []
    for repo in repos:
        count = count_commits_since(repo, since, token)
        print(f"  {repo}: {count}")
        results.append({"repo": repo, "count": count})

    md_block = build_markdown(results, args.hours, since, now)

    output_path = args.output
    if not os.path.isabs(output_path):
        # resolve relative to the script's parent directory (project root)
        output_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), output_path)

    existing = ""
    if os.path.exists(output_path):
        with open(output_path) as f:
            existing = f.read()

    with open(output_path, "w") as f:
        f.write(md_block + existing)

    print(f"\nSaved to {output_path}")


if __name__ == "__main__":
    main()

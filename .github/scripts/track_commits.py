#!/usr/bin/env python3
"""
Queries the last 6 hours of commits on peak-flow/peaktrack and appends
a summary section to commit_log.md.
"""

import json
import os
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone, timedelta

REPO = os.environ.get("REPO", "peak-flow/peaktrack")
TOKEN = os.environ.get("GH_TOKEN", "")
LOG_FILE = "commit_log.md"


def gh_api(path: str) -> list:
    url = f"https://api.github.com{path}"
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    if TOKEN:
        req.add_header("Authorization", f"Bearer {TOKEN}")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def fetch_commits_since(repo: str, since: str) -> list:
    owner, name = repo.split("/")
    path = f"/repos/{owner}/{name}/commits?since={since}&per_page=100"
    return gh_api(path)


def short_sha(sha: str) -> str:
    return sha[:7]


def first_line(msg: str) -> str:
    line = msg.split("\n")[0].strip()
    # escape markdown pipe chars
    return line.replace("|", "\\|")


def build_section(now: datetime, since: datetime, commits: list) -> str:
    header_ts = now.strftime("%Y-%m-%d %H:%M UTC")
    since_ts = since.strftime("%Y-%m-%dT%H:%M:%SZ")

    lines = [
        f"## Check: {header_ts}",
        "",
        f"- **Repo:** {REPO}",
        f"- **Window:** Last 6 hours (since `{since_ts}`)",
        f"- **Commit count:** {len(commits)}",
        "",
        "<details>",
        "<summary>Commits</summary>",
        "",
        "| SHA | Author | Message | Date |",
        "|-----|--------|---------|------|",
    ]

    if commits:
        for c in commits:
            sha = short_sha(c["sha"])
            author = (c.get("author") or {}).get("login") or c["commit"]["author"]["name"]
            msg = first_line(c["commit"]["message"])
            date = c["commit"]["author"]["date"]
            lines.append(f"| `{sha}` | {author} | {msg} | {date} |")
    else:
        lines.append("| — | — | No commits in this window. | — |")

    lines += ["", "</details>", "", "---", ""]
    return "\n".join(lines)


def main():
    now = datetime.now(timezone.utc)
    since = now - timedelta(hours=6)
    since_iso = since.strftime("%Y-%m-%dT%H:%M:%SZ")

    print(f"Fetching commits for {REPO} since {since_iso} …")
    commits = fetch_commits_since(REPO, since_iso)
    print(f"Found {len(commits)} commit(s).")

    section = build_section(now, since, commits)

    with open(LOG_FILE, "a") as f:
        f.write(section)

    print(f"Appended entry to {LOG_FILE}.")


if __name__ == "__main__":
    main()

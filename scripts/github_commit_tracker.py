#!/usr/bin/env python3
"""Check all peak-flow repos for commits in the last 6 hours and append to a markdown log."""

import os
import sys
import requests
from datetime import datetime, timezone, timedelta

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_USER = "peak-flow"
LOG_FILE = os.path.join(os.path.dirname(__file__), "..", "commit_log.md")
WINDOW_HOURS = 6
PER_PAGE = 100

HEADERS = {
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}
if GITHUB_TOKEN:
    HEADERS["Authorization"] = f"Bearer {GITHUB_TOKEN}"


def gh_get(url, params=None):
    try:
        resp = requests.get(url, headers=HEADERS, params=params, timeout=30)
    except requests.exceptions.ConnectionError as e:
        print(f"  Connection error: {e}", file=sys.stderr)
        return None
    if resp.status_code in (404, 409):  # 409 = empty repo
        return None
    if resp.status_code == 403:
        print(f"  403 Forbidden — check GITHUB_TOKEN. URL: {url}", file=sys.stderr)
        sys.exit(1)
    resp.raise_for_status()
    return resp.json()


def get_all_repos():
    repos = []
    page = 1
    while True:
        data = gh_get(
            f"https://api.github.com/users/{GITHUB_USER}/repos",
            params={"per_page": PER_PAGE, "page": page, "type": "owner"},
        )
        if not data:
            break
        repos.extend(data)
        if len(data) < PER_PAGE:
            break
        page += 1
    # Also check private repos if token is present
    if GITHUB_TOKEN:
        page = 1
        while True:
            data = gh_get(
                "https://api.github.com/user/repos",
                params={
                    "per_page": PER_PAGE,
                    "page": page,
                    "type": "owner",
                    "affiliation": "owner",
                },
            )
            if not data:
                break
            seen_names = {r["full_name"] for r in repos}
            for r in data:
                if r["full_name"] not in seen_names:
                    repos.append(r)
                    seen_names.add(r["full_name"])
            if len(data) < PER_PAGE:
                break
            page += 1
    return repos


def count_recent_commits(owner, repo, since_iso):
    commits = []
    page = 1
    while True:
        data = gh_get(
            f"https://api.github.com/repos/{owner}/{repo}/commits",
            params={"since": since_iso, "per_page": PER_PAGE, "page": page},
        )
        if data is None:
            break
        if not data:
            break
        commits.extend(data)
        if len(data) < PER_PAGE:
            break
        page += 1
    return commits


def main():
    now = datetime.now(timezone.utc)
    since = now - timedelta(hours=WINDOW_HOURS)
    since_iso = since.strftime("%Y-%m-%dT%H:%M:%SZ")

    print(f"Checking commits since {since_iso} ...")

    repos = get_all_repos()
    print(f"Found {len(repos)} repos.")

    active_repos = []
    total_commits = 0

    for repo in repos:
        owner = repo["owner"]["login"]
        name = repo["name"]
        commits = count_recent_commits(owner, name, since_iso)
        if commits:
            count = len(commits)
            total_commits += count
            authors = sorted({c["commit"]["author"]["name"] for c in commits})
            active_repos.append(
                {
                    "full_name": repo["full_name"],
                    "url": repo["html_url"],
                    "count": count,
                    "authors": authors,
                    "private": repo.get("private", False),
                }
            )
            print(f"  {repo['full_name']}: {count} commit(s)")

    active_repos.sort(key=lambda r: r["count"], reverse=True)

    # Build markdown section
    timestamp = now.strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        f"## {timestamp}",
        f"",
        f"**Window:** last {WINDOW_HOURS} hours  ",
        f"**Total commits:** {total_commits}  ",
        f"**Active repos:** {len(active_repos)}",
        f"",
    ]

    if active_repos:
        lines.append("| Repository | Commits | Authors | Private |")
        lines.append("|---|---|---|---|")
        for r in active_repos:
            lock = "Yes" if r["private"] else "No"
            authors_str = ", ".join(r["authors"])
            lines.append(
                f"| [{r['full_name']}]({r['url']}) | {r['count']} | {authors_str} | {lock} |"
            )
    else:
        lines.append("_No commits in this window._")

    lines.append("")
    lines.append("---")
    lines.append("")

    section = "\n".join(lines)

    log_path = os.path.abspath(LOG_FILE)

    # Prepend to file (newest first)
    existing = ""
    if os.path.exists(log_path):
        with open(log_path, "r") as f:
            existing = f.read()

    header_needed = not existing
    with open(log_path, "w") as f:
        if header_needed:
            f.write("# GitHub Commit Activity Log\n\n")
        else:
            # Keep the top-level header
            f.write("# GitHub Commit Activity Log\n\n")
        f.write(section)
        # Write previous entries (strip old header if present)
        trimmed = existing.replace("# GitHub Commit Activity Log\n\n", "", 1).lstrip("\n")
        if trimmed:
            f.write(trimmed)

    print(f"\nLog updated: {log_path}")
    print(f"Total: {total_commits} commit(s) across {len(active_repos)} repo(s)")


if __name__ == "__main__":
    if not GITHUB_TOKEN:
        print("WARNING: GITHUB_TOKEN not set — private repos will be skipped and rate limits apply.", file=sys.stderr)
    main()

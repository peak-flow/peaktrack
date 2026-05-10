#!/usr/bin/env python3
"""
Check GitHub for commits made in the last 6 hours across configured repos
and append a summary to commit_log.md.

Usage:
    GITHUB_TOKEN=ghp_xxx python3 check_github_commits.py [--repos owner/repo ...]

Configuration:
    Set GITHUB_TOKEN env var with a personal access token (read:repo scope).
    Set GITHUB_REPOS env var as comma-separated list, e.g. "owner/repo1,owner/repo2".
    Or pass repos as command-line arguments: --repos owner/repo1 owner/repo2
"""

import os
import sys
import json
import argparse
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
LOG_FILE = SCRIPT_DIR.parent / "commit_log.md"
WINDOW_HOURS = 6


def github_get(url: str, token: str) -> list | dict:
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    req.add_header("User-Agent", "peaktrack-commit-checker")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def fetch_commits_since(owner: str, repo: str, since: datetime, token: str) -> list:
    since_iso = since.strftime("%Y-%m-%dT%H:%M:%SZ")
    url = (
        f"https://api.github.com/repos/{owner}/{repo}/commits"
        f"?since={since_iso}&per_page=100"
    )
    commits = []
    page = 1
    while True:
        paged_url = f"{url}&page={page}"
        try:
            data = github_get(paged_url, token)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                print(f"  WARNING: repo {owner}/{repo} not found or no access", file=sys.stderr)
                return []
            raise
        if not data:
            break
        commits.extend(data)
        if len(data) < 100:
            break
        page += 1
    return commits


def format_commit_row(commit: dict) -> str:
    sha = commit["sha"][:7]
    msg = commit["commit"]["message"].split("\n")[0][:80]
    author = commit["commit"]["author"]["name"]
    date = commit["commit"]["author"]["date"]
    return f"| `{sha}` | {date} | {author} | {msg} |"


def build_section(repo_full: str, commits: list, since: datetime, until: datetime) -> str:
    since_str = since.strftime("%Y-%m-%d %H:%M UTC")
    until_str = until.strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        f"### {repo_full}",
        f"- **Window:** {since_str} → {until_str}",
        f"- **Commit count:** {len(commits)}",
        "",
    ]
    if commits:
        lines += [
            "| SHA | Date | Author | Message |",
            "|-----|------|--------|---------|",
        ]
        for c in commits:
            lines.append(format_commit_row(c))
    else:
        lines.append("_No commits in this window._")
    lines.append("")
    return "\n".join(lines)


def append_to_log(sections: list[str], run_time: datetime) -> None:
    header = f"## Run: {run_time.strftime('%Y-%m-%d %H:%M UTC')}\n\n"
    block = header + "\n".join(sections) + "\n---\n\n"

    if not LOG_FILE.exists():
        LOG_FILE.write_text("# GitHub Commit Log\n\n")

    with LOG_FILE.open("a") as f:
        f.write(block)

    print(f"Appended to {LOG_FILE}")


def parse_repos(args_repos: list[str] | None) -> list[str]:
    if args_repos:
        return args_repos
    env_repos = os.environ.get("GITHUB_REPOS", "")
    if env_repos:
        return [r.strip() for r in env_repos.split(",") if r.strip()]
    print("ERROR: No repos configured. Set GITHUB_REPOS env var or pass --repos.", file=sys.stderr)
    sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Log GitHub commits from the last 6 hours.")
    parser.add_argument("--repos", nargs="+", metavar="OWNER/REPO",
                        help="Repos to check (overrides GITHUB_REPOS env var)")
    parser.add_argument("--hours", type=int, default=WINDOW_HOURS,
                        help=f"Hours to look back (default: {WINDOW_HOURS})")
    args = parser.parse_args()

    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        print("ERROR: GITHUB_TOKEN environment variable is not set.", file=sys.stderr)
        sys.exit(1)

    repos = parse_repos(args.repos)
    until = datetime.now(timezone.utc)
    since = until - timedelta(hours=args.hours)

    sections = []
    total = 0
    for repo_full in repos:
        parts = repo_full.strip("/").split("/")
        if len(parts) != 2:
            print(f"  Skipping invalid repo format: {repo_full}", file=sys.stderr)
            continue
        owner, repo = parts
        print(f"Checking {repo_full}...")
        commits = fetch_commits_since(owner, repo, since, token)
        print(f"  Found {len(commits)} commit(s)")
        sections.append(build_section(repo_full, commits, since, until))
        total += len(commits)

    print(f"\nTotal commits across all repos: {total}")
    append_to_log(sections, until)


if __name__ == "__main__":
    main()

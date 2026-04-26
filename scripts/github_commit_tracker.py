#!/usr/bin/env python3
"""
Checks GitHub for commits made in the last 6 hours across configured repos
and appends a summary to a markdown log file.

Requirements:
  pip install requests

Environment variables:
  GITHUB_TOKEN  - Personal access token (required for private repos / higher rate limits)
  GITHUB_USER   - GitHub username to scan (used when GITHUB_REPOS is not set)
  GITHUB_REPOS  - Comma-separated list of "owner/repo" to check (optional)
                  If omitted, all repos for GITHUB_USER are scanned.
  COMMIT_LOG    - Path to the output markdown file (default: ../commit_log.md)
"""

import os
import sys
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

try:
    import requests
except ImportError:
    sys.exit("Missing dependency: run  pip install requests")


GITHUB_API = "https://api.github.com"
HOURS = 6


def github_headers() -> dict:
    token = os.environ.get("GITHUB_TOKEN")
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def get_repos(session: requests.Session, user: str) -> list[str]:
    repos, page = [], 1
    while True:
        r = session.get(
            f"{GITHUB_API}/users/{user}/repos",
            params={"per_page": 100, "page": page, "type": "owner"},
        )
        r.raise_for_status()
        batch = r.json()
        if not batch:
            break
        repos.extend(repo["full_name"] for repo in batch)
        page += 1
    return repos


def count_commits(session: requests.Session, full_name: str, since: str) -> int:
    total, page = 0, 1
    while True:
        r = session.get(
            f"{GITHUB_API}/repos/{full_name}/commits",
            params={"since": since, "per_page": 100, "page": page},
        )
        if r.status_code == 409:  # empty repo
            return 0
        r.raise_for_status()
        batch = r.json()
        if not batch:
            break
        total += len(batch)
        if len(batch) < 100:
            break
        page += 1
    return total


def build_markdown_section(run_at: datetime, results: list[tuple[str, int]]) -> str:
    timestamp = run_at.strftime("%Y-%m-%d %H:%M UTC")
    active = [(repo, n) for repo, n in results if n > 0]
    total = sum(n for _, n in active)

    lines = [
        f"## {timestamp}",
        f"",
        f"**Total commits in last {HOURS} hours:** {total}  ",
        f"**Repos with activity:** {len(active)} / {len(results)}",
        "",
    ]

    if active:
        lines.append("| Repository | Commits |")
        lines.append("|---|---|")
        for repo, n in sorted(active, key=lambda x: -x[1]):
            lines.append(f"| `{repo}` | {n} |")
    else:
        lines.append("_No commits found in this window._")

    lines.append("")
    return "\n".join(lines)


def main():
    session = requests.Session()
    session.headers.update(github_headers())

    # Determine repos to check
    repos_env = os.environ.get("GITHUB_REPOS", "").strip()
    if repos_env:
        repos = [r.strip() for r in repos_env.split(",") if r.strip()]
    else:
        user = os.environ.get("GITHUB_USER", "").strip()
        if not user:
            sys.exit(
                "Set GITHUB_USER (to scan all your repos) or GITHUB_REPOS "
                "(comma-separated owner/repo list)"
            )
        print(f"Fetching repo list for user: {user}")
        repos = get_repos(session, user)

    if not repos:
        sys.exit("No repositories found to check.")

    # Time window
    now = datetime.now(timezone.utc)
    since_dt = now - timedelta(hours=HOURS)
    since_iso = since_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    print(f"Checking {len(repos)} repo(s) for commits since {since_iso} ...")

    results = []
    for repo in repos:
        try:
            n = count_commits(session, repo, since_iso)
            results.append((repo, n))
            if n:
                print(f"  {repo}: {n} commit(s)")
        except requests.HTTPError as exc:
            print(f"  {repo}: ERROR {exc.response.status_code} - skipping", file=sys.stderr)

    # Write markdown
    script_dir = Path(__file__).resolve().parent
    default_log = script_dir.parent / "commit_log.md"
    log_path = Path(os.environ.get("COMMIT_LOG", str(default_log)))

    section = build_markdown_section(now, results)

    # Prepend a header on first run
    if not log_path.exists():
        header = f"# GitHub Commit Activity Log\n\nChecked every {HOURS} hours.\n\n"
        log_path.write_text(header + section)
    else:
        existing = log_path.read_text()
        # Insert new section after the top-level header block
        split_marker = "\n## "
        if split_marker in existing:
            head, rest = existing.split(split_marker, 1)
            log_path.write_text(head + "\n" + section + split_marker + rest)
        else:
            log_path.write_text(existing + "\n" + section)

    print(f"\nLog updated: {log_path}")


if __name__ == "__main__":
    main()

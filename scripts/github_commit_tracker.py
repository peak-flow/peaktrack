#!/usr/bin/env python3
"""
GitHub Commit Tracker
Checks GitHub every 6 hours for commits made in the last 6 hours
and appends a summary to a Markdown report file.

Usage:
    python3 github_commit_tracker.py

Environment variables:
    GITHUB_TOKEN  - Personal access token (required)
    GITHUB_REPOS  - Comma-separated list of "owner/repo" to track.
                    If omitted, all repos accessible to the token owner are checked.
    REPORT_FILE   - Path to the output markdown file (default: commit_reports/report.md)
"""

import os
import sys
import json
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta


GITHUB_API = "https://api.github.com"
REPORT_FILE = os.environ.get("REPORT_FILE", os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "commit_reports", "report.md"
))


def github_get(path: str, token: str) -> list | dict:
    url = f"{GITHUB_API}{path}"
    results = []
    while url:
        req = urllib.request.Request(url, headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "github-commit-tracker/1.0",
        })
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read())
                if isinstance(data, list):
                    results.extend(data)
                    # Follow Link header pagination
                    link = resp.headers.get("Link", "")
                    url = _next_link(link)
                else:
                    return data
        except urllib.error.HTTPError as e:
            body = e.read().decode()
            print(f"  GitHub API error {e.code} for {url}: {body}", file=sys.stderr)
            return []
    return results


def _next_link(link_header: str) -> str | None:
    for part in link_header.split(","):
        part = part.strip()
        if 'rel="next"' in part:
            return part.split(";")[0].strip().strip("<>")
    return None


def get_tracked_repos(token: str, repos_env: str | None) -> list[str]:
    if repos_env:
        return [r.strip() for r in repos_env.split(",") if r.strip()]
    user = github_get("/user", token)
    username = user.get("login", "")
    print(f"  Fetching repos for user: {username}")
    repos = github_get(f"/user/repos?per_page=100&affiliation=owner,collaborator,organization_member", token)
    return [r["full_name"] for r in repos if isinstance(r, dict) and not r.get("archived")]


def get_commits_since(repo: str, since: datetime, token: str) -> list[dict]:
    since_iso = since.strftime("%Y-%m-%dT%H:%M:%SZ")
    path = f"/repos/{repo}/commits?since={since_iso}&per_page=100"
    commits = github_get(path, token)
    if not isinstance(commits, list):
        return []
    results = []
    for c in commits:
        sha = c.get("sha", "")[:7]
        message = (c.get("commit", {}).get("message") or "").splitlines()[0][:80]
        author = (
            c.get("commit", {}).get("author", {}).get("name")
            or c.get("author", {}).get("login")
            or "unknown"
        )
        committed_at = c.get("commit", {}).get("author", {}).get("date", "")
        results.append({"sha": sha, "message": message, "author": author, "date": committed_at})
    return results


def build_report_section(since: datetime, until: datetime, repo_commits: dict[str, list]) -> str:
    lines = []
    total = sum(len(v) for v in repo_commits.values())
    lines.append(f"\n## Report: {since.strftime('%Y-%m-%d %H:%M')} UTC → {until.strftime('%Y-%m-%d %H:%M')} UTC\n")
    lines.append(f"**Total commits across all repos:** {total}\n")

    active = {repo: commits for repo, commits in repo_commits.items() if commits}
    if not active:
        lines.append("\n_No commits found in this window._\n")
        return "\n".join(lines)

    for repo, commits in sorted(active.items(), key=lambda x: -len(x[1])):
        lines.append(f"\n### `{repo}` — {len(commits)} commit(s)\n")
        lines.append("| SHA | Author | Message | Date |")
        lines.append("|-----|--------|---------|------|")
        for c in commits:
            msg = c["message"].replace("|", "\\|")
            lines.append(f"| `{c['sha']}` | {c['author']} | {msg} | {c['date']} |")

    return "\n".join(lines) + "\n"


def ensure_report_header(path: str):
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        with open(path, "w") as f:
            f.write("# GitHub Commit Tracker\n\n")
            f.write("_Auto-generated report. Updated every 6 hours._\n")


def main():
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("Error: GITHUB_TOKEN environment variable is not set.", file=sys.stderr)
        sys.exit(1)

    repos_env = os.environ.get("GITHUB_REPOS")
    now = datetime.now(timezone.utc)
    six_hours_ago = now - timedelta(hours=6)

    print(f"[{now.strftime('%Y-%m-%d %H:%M:%S')} UTC] Starting commit check...")
    print(f"  Window: {six_hours_ago.strftime('%Y-%m-%d %H:%M')} → {now.strftime('%Y-%m-%d %H:%M')} UTC")

    repos = get_tracked_repos(token, repos_env)
    print(f"  Checking {len(repos)} repo(s): {', '.join(repos)}")

    repo_commits: dict[str, list] = {}
    for repo in repos:
        commits = get_commits_since(repo, six_hours_ago, token)
        repo_commits[repo] = commits
        if commits:
            print(f"  {repo}: {len(commits)} commit(s)")

    section = build_report_section(six_hours_ago, now, repo_commits)

    os.makedirs(os.path.dirname(REPORT_FILE), exist_ok=True)
    ensure_report_header(REPORT_FILE)
    with open(REPORT_FILE, "a") as f:
        f.write(section)

    total = sum(len(v) for v in repo_commits.values())
    print(f"  Done. {total} total commit(s) written to {REPORT_FILE}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Track GitHub commits every 6 hours and save to a markdown report."""

import json
import os
import sys
from datetime import datetime, timezone, timedelta
from urllib.request import urlopen, Request
from urllib.error import HTTPError

REPOS_FILE = os.path.join(os.path.dirname(__file__), "tracked_repos.json")
REPORT_FILE = os.path.join(os.path.dirname(__file__), "commit_report.md")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
WINDOW_HOURS = 6


def gh_request(path: str) -> list | dict:
    url = f"https://api.github.com{path}"
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    req = Request(url, headers=headers)
    try:
        with urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except HTTPError as e:
        print(f"  GitHub API error {e.code} for {path}: {e.reason}", file=sys.stderr)
        return []


def load_repos() -> list[str]:
    if not os.path.exists(REPOS_FILE):
        default = ["peak-flow/peaktrack"]
        with open(REPOS_FILE, "w") as f:
            json.dump({"repos": default}, f, indent=2)
        return default
    with open(REPOS_FILE) as f:
        return json.load(f).get("repos", [])


def fetch_commits_since(repo: str, since: datetime) -> list[dict]:
    since_iso = since.strftime("%Y-%m-%dT%H:%M:%SZ")
    path = f"/repos/{repo}/commits?since={since_iso}&per_page=100"
    data = gh_request(path)
    if not isinstance(data, list):
        return []
    commits = []
    for item in data:
        sha = item.get("sha", "")[:7]
        msg_lines = (item.get("commit", {}).get("message") or "").splitlines()
        msg = msg_lines[0] if msg_lines else "(no message)"
        author = (
            (item.get("commit", {}).get("author") or {}).get("name")
            or (item.get("author") or {}).get("login")
            or "unknown"
        )
        committed_at = (item.get("commit", {}).get("committer") or {}).get("date", "")
        commits.append({"sha": sha, "message": msg, "author": author, "date": committed_at})
    return commits


def build_report(results: dict[str, list[dict]], since: datetime, until: datetime) -> str:
    since_str = since.strftime("%Y-%m-%d %H:%M UTC")
    until_str = until.strftime("%Y-%m-%d %H:%M UTC")
    total = sum(len(v) for v in results.values())

    lines = [
        "# GitHub Commit Report",
        "",
        f"**Period:** {since_str} → {until_str}",
        f"**Total commits:** {total}",
        f"**Repos tracked:** {len(results)}",
        "",
        "---",
        "",
    ]

    for repo, commits in sorted(results.items()):
        lines.append(f"## `{repo}` — {len(commits)} commit(s)")
        lines.append("")
        if commits:
            lines.append("| SHA | Author | Message |")
            lines.append("|-----|--------|---------|")
            for c in commits:
                msg = c["message"].replace("|", "\\|")[:80]
                lines.append(f"| `{c['sha']}` | {c['author']} | {msg} |")
        else:
            lines.append("_No commits in this window._")
        lines.append("")

    lines.append("---")
    lines.append(f"_Generated at {until_str}_")
    lines.append("")
    return "\n".join(lines)


def append_report(new_section: str) -> None:
    existing = ""
    if os.path.exists(REPORT_FILE):
        with open(REPORT_FILE) as f:
            existing = f.read()

    # Keep only the latest 10 report blocks to avoid unbounded growth
    separator = "\n---\n_Generated at"
    parts = existing.split(separator)
    if len(parts) > 10:
        parts = parts[-10:]
        existing = separator.join(parts)

    with open(REPORT_FILE, "w") as f:
        f.write(new_section)
        if existing.strip():
            f.write("\n\n<!-- Previous reports below -->\n\n")
            f.write(existing)


def main() -> None:
    until = datetime.now(timezone.utc)
    since = until - timedelta(hours=WINDOW_HOURS)
    repos = load_repos()

    print(f"Checking {len(repos)} repo(s) for commits since {since.strftime('%Y-%m-%d %H:%M UTC')} ...")

    results: dict[str, list[dict]] = {}
    for repo in repos:
        print(f"  Fetching {repo} ...", end=" ", flush=True)
        commits = fetch_commits_since(repo, since)
        results[repo] = commits
        print(f"{len(commits)} commit(s)")

    report = build_report(results, since, until)
    append_report(report)
    print(f"Report saved to {REPORT_FILE}")

    total = sum(len(v) for v in results.values())
    print(f"\nSummary: {total} total commit(s) across {len(repos)} repo(s) in the last {WINDOW_HOURS}h")


if __name__ == "__main__":
    main()

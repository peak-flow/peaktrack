#!/usr/bin/env python3
"""
GitHub Commit Tracker
Fetches commits from the last N hours across configured repos and appends a
summary to a markdown file. Run via cron every 6 hours.
"""

import os
import sys
import json
import urllib.request
import urllib.error
from datetime import datetime, timedelta, timezone

# ── Configuration ──────────────────────────────────────────────────────────────
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
HOURS = int(os.environ.get("COMMIT_TRACKER_HOURS", "6"))
OUTPUT_FILE = os.environ.get("COMMIT_TRACKER_OUTPUT", "commit_report.md")

# Comma-separated list of owner/repo pairs, e.g. "peak-flow/peaktrack,owner/other-repo"
REPOS_ENV = os.environ.get("COMMIT_TRACKER_REPOS", "peak-flow/peaktrack")
REPOS = [r.strip() for r in REPOS_ENV.split(",") if r.strip()]
# ──────────────────────────────────────────────────────────────────────────────


def github_get(url: str, params: dict | None = None) -> tuple[list | dict | None, int]:
    if params:
        query = "&".join(f"{k}={v}" for k, v in params.items())
        url = f"{url}?{query}"
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    if GITHUB_TOKEN:
        req.add_header("Authorization", f"Bearer {GITHUB_TOKEN}")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode()), resp.status
    except urllib.error.HTTPError as e:
        return None, e.code
    except Exception as e:
        print(f"  Request error: {e}", file=sys.stderr)
        return None, 0


def get_commits(repo: str, since_iso: str) -> tuple[list, str | None]:
    """Return (commits, error_msg). Handles pagination."""
    url = f"https://api.github.com/repos/{repo}/commits"
    all_commits: list = []
    page = 1
    while True:
        data, status = github_get(url, {"since": since_iso, "per_page": "100", "page": str(page)})
        if data is None:
            return [], f"HTTP {status}"
        if not isinstance(data, list):
            return [], f"Unexpected response: {data.get('message', 'unknown')}"
        all_commits.extend(data)
        if len(data) < 100:
            break
        page += 1
    return all_commits, None


def build_report(repos: list[str], hours: int) -> str:
    now = datetime.now(timezone.utc)
    since = now - timedelta(hours=hours)
    since_iso = since.strftime("%Y-%m-%dT%H:%M:%SZ")

    lines: list[str] = [
        f"## Commit Report — {now.strftime('%Y-%m-%d %H:%M UTC')}",
        f"",
        f"**Period:** last {hours} hours  (since {since.strftime('%Y-%m-%d %H:%M UTC')})",
        f"",
    ]

    grand_total = 0
    repo_summaries: list[str] = []

    for repo in repos:
        commits, err = get_commits(repo, since_iso)
        if err:
            repo_summaries.append(f"- **{repo}** — error: {err}")
            continue
        count = len(commits)
        grand_total += count
        repo_summaries.append(f"- **{repo}** — {count} commit{'s' if count != 1 else ''}")

    lines.append(f"**Total across all repos: {grand_total} commit{'s' if grand_total != 1 else ''}**")
    lines.append("")
    lines.extend(repo_summaries)

    # Per-repo detail tables
    for repo in repos:
        commits, err = get_commits(repo, since_iso)
        if err or not commits:
            continue
        lines += ["", f"### {repo}", ""]
        lines.append("| SHA | Author | Message | Time (UTC) |")
        lines.append("|-----|--------|---------|------------|")
        for c in commits:
            sha = c["sha"][:7]
            author = c["commit"]["author"]["name"].replace("|", "\\|")
            msg = c["commit"]["message"].split("\n")[0][:72].replace("|", "\\|")
            ts = c["commit"]["author"]["date"]
            lines.append(f"| `{sha}` | {author} | {msg} | {ts} |")

    lines += ["", "---", ""]
    return "\n".join(lines)


def append_report(filepath: str, content: str) -> None:
    mode = "a" if os.path.exists(filepath) else "w"
    with open(filepath, mode, encoding="utf-8") as f:
        if mode == "w":
            f.write("# GitHub Commit Tracker Log\n\n")
        f.write(content + "\n")


def main() -> None:
    if not GITHUB_TOKEN:
        print("Warning: GITHUB_TOKEN not set — requests may be rate-limited (60/hour).", file=sys.stderr)

    print(f"Checking {len(REPOS)} repo(s) for commits in the last {HOURS} hours...")
    for r in REPOS:
        print(f"  {r}")

    report = build_report(REPOS, HOURS)
    append_report(OUTPUT_FILE, report)
    print(f"Report appended to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()

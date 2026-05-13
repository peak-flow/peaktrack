#!/usr/bin/env python3
"""
GitHub Commit Tracker
Fetches commits from the last 6 hours across configured repos and appends a
summary to commit_log.md in the project root.
"""

import os
import json
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from pathlib import Path

REPOS = [
    "peak-flow/peaktrack",
]

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
LOG_FILE = Path(__file__).parent.parent / "commit_log.md"
HOURS_BACK = 6


def github_request(url: str) -> list | dict | None:
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    if GITHUB_TOKEN:
        req.add_header("Authorization", f"Bearer {GITHUB_TOKEN}")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        print(f"  HTTP {e.code} for {url}: {e.reason}")
        return None
    except Exception as e:
        print(f"  Error fetching {url}: {e}")
        return None


def get_commits_since(repo: str, since: datetime) -> list[dict]:
    since_iso = since.strftime("%Y-%m-%dT%H:%M:%SZ")
    url = (
        f"https://api.github.com/repos/{repo}/commits"
        f"?since={since_iso}&per_page=100"
    )
    data = github_request(url)
    if not data or not isinstance(data, list):
        return []
    commits = []
    for item in data:
        sha = item.get("sha", "")[:7]
        msg = item.get("commit", {}).get("message", "").split("\n")[0]
        author = item.get("commit", {}).get("author", {}).get("name", "unknown")
        date = item.get("commit", {}).get("author", {}).get("date", "")
        commits.append({"sha": sha, "message": msg, "author": author, "date": date})
    return commits


def build_report(now: datetime, since: datetime, results: dict[str, list]) -> str:
    total = sum(len(v) for v in results.values())
    lines = [
        f"## Commit Report — {now.strftime('%Y-%m-%d %H:%M UTC')}",
        f"",
        f"**Window:** last {HOURS_BACK} hours ({since.strftime('%Y-%m-%d %H:%M UTC')} → {now.strftime('%H:%M UTC')})",
        f"**Total commits:** {total}",
        f"",
    ]

    for repo, commits in sorted(results.items()):
        count = len(commits)
        lines.append(f"### `{repo}` — {count} commit{'s' if count != 1 else ''}")
        if commits:
            for c in commits:
                lines.append(f"- [`{c['sha']}`] **{c['author']}**: {c['message']}")
        else:
            lines.append("_No commits in this window._")
        lines.append("")

    lines.append("---")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    now = datetime.now(timezone.utc)
    since = now - timedelta(hours=HOURS_BACK)

    print(f"[{now.strftime('%Y-%m-%d %H:%M UTC')}] Checking commits since {since.strftime('%H:%M UTC')} ...")

    results: dict[str, list] = {}
    for repo in REPOS:
        print(f"  {repo} ...", end=" ", flush=True)
        commits = get_commits_since(repo, since)
        results[repo] = commits
        print(f"{len(commits)} commit(s)")

    report = build_report(now, since, results)

    if LOG_FILE.exists():
        existing = LOG_FILE.read_text()
        # Insert new report after the header block (first two lines)
        lines = existing.splitlines(keepends=True)
        header_end = 0
        for i, line in enumerate(lines):
            if line.startswith("## Commit Report"):
                header_end = i
                break
        updated = "".join(lines[:header_end]) + report + "\n" + "".join(lines[header_end:])
        LOG_FILE.write_text(updated)
    else:
        LOG_FILE.write_text(
            "# GitHub Commit Log\n\nAuto-generated every 6 hours.\n\n" + report
        )

    print(f"  -> Saved to {LOG_FILE}")


if __name__ == "__main__":
    main()

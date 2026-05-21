#!/usr/bin/env python3
"""
Query GitHub for commits made in the last N hours across one or more repos,
and append a summary entry to commit_log.md.

Environment variables:
  GITHUB_TOKEN   - required; personal access token or Actions GITHUB_TOKEN
  REPOS          - comma-separated list of "owner/repo" to monitor
                   defaults to the repo this script lives in (peak-flow/peaktrack)
  HOURS          - look-back window in hours (default: 6)
  LOG_FILE       - path to the markdown log file (default: commit_log.md next to this script)
"""

import os
import sys
import json
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from pathlib import Path

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
REPOS = [r.strip() for r in os.environ.get("REPOS", "peak-flow/peaktrack").split(",") if r.strip()]
HOURS = int(os.environ.get("HOURS", "6"))
LOG_FILE = Path(os.environ.get("LOG_FILE", Path(__file__).parent.parent / "commit_log.md"))

API_BASE = "https://api.github.com"


def gh_get(path: str) -> list | dict:
    url = f"{API_BASE}{path}"
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    if GITHUB_TOKEN:
        req.add_header("Authorization", f"Bearer {GITHUB_TOKEN}")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def count_commits_since(repo: str, since: datetime) -> list[dict]:
    since_iso = since.strftime("%Y-%m-%dT%H:%M:%SZ")
    path = f"/repos/{repo}/commits?since={since_iso}&per_page=100"
    results = []
    page = 1
    while True:
        data = gh_get(f"/repos/{repo}/commits?since={since_iso}&per_page=100&page={page}")
        if not isinstance(data, list) or not data:
            break
        results.extend(data)
        if len(data) < 100:
            break
        page += 1
    return results


def append_log(entries: list[dict], now: datetime, since: datetime) -> None:
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

    # Create header if file doesn't exist yet
    if not LOG_FILE.exists():
        LOG_FILE.write_text(
            "# GitHub Commit Log\n\n"
            "Automatically updated every 6 hours.\n\n"
            "---\n\n"
        )

    total = sum(e["count"] for e in entries)
    window = f"{since.strftime('%Y-%m-%d %H:%M')} – {now.strftime('%Y-%m-%d %H:%M')} UTC"

    lines = [f"## {now.strftime('%Y-%m-%d %H:%M')} UTC  ({HOURS}h window)\n"]
    lines.append(f"**Total commits:** {total}  \n")
    lines.append(f"**Window:** {window}\n\n")

    if entries:
        lines.append("| Repository | Commits | Authors |\n")
        lines.append("|---|---|---|\n")
        for e in entries:
            authors = ", ".join(sorted(e["authors"])) if e["authors"] else "—"
            lines.append(f"| `{e['repo']}` | {e['count']} | {authors} |\n")
    else:
        lines.append("_No commits in this window._\n")

    lines.append("\n---\n\n")

    with open(LOG_FILE, "a") as f:
        f.writelines(lines)

    print(f"Appended entry to {LOG_FILE}")


def main() -> None:
    if not GITHUB_TOKEN:
        print("ERROR: GITHUB_TOKEN env var is required", file=sys.stderr)
        sys.exit(1)

    now = datetime.now(timezone.utc)
    since = now - timedelta(hours=HOURS)

    print(f"Checking commits since {since.isoformat()} across {len(REPOS)} repo(s)...")

    entries = []
    for repo in REPOS:
        try:
            commits = count_commits_since(repo, since)
            authors = {
                c["commit"]["author"]["name"]
                for c in commits
                if c.get("commit", {}).get("author", {}).get("name")
            }
            entries.append({"repo": repo, "count": len(commits), "authors": authors})
            print(f"  {repo}: {len(commits)} commit(s)")
        except urllib.error.HTTPError as exc:
            print(f"  {repo}: HTTP {exc.code} — skipping", file=sys.stderr)
            entries.append({"repo": repo, "count": 0, "authors": set()})

    append_log(entries, now, since)


if __name__ == "__main__":
    main()

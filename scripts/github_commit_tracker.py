#!/usr/bin/env python3
"""
Check GitHub for commits made in the last 6 hours across configured repos
and append a summary to a markdown log file.
"""

import os
import json
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ── Configuration ─────────────────────────────────────────────────────────────
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
# Edit this list to add repos you want to track (owner/repo format)
REPOS = [
    "peak-flow/peaktrack",
]
LOOKBACK_HOURS = 6
LOG_FILE = Path(__file__).parent.parent / "commit_log.md"
# ──────────────────────────────────────────────────────────────────────────────


def gh_get(path: str) -> list | dict:
    url = f"https://api.github.com{path}"
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    if GITHUB_TOKEN:
        req.add_header("Authorization", f"Bearer {GITHUB_TOKEN}")
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())


def fetch_commits_since(repo: str, since: datetime) -> list[dict]:
    since_iso = since.strftime("%Y-%m-%dT%H:%M:%SZ")
    commits = []
    page = 1
    while True:
        path = f"/repos/{repo}/commits?since={since_iso}&per_page=100&page={page}"
        try:
            batch = gh_get(path)
        except urllib.error.HTTPError as e:
            if e.code in (403, 404):
                print(f"  [warn] HTTP {e.code} for {repo} — check token/permissions")
                break
            raise
        if not batch:
            break
        commits.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return commits


def build_report(results: dict[str, list], window_start: datetime, window_end: datetime) -> str:
    ts_start = window_start.strftime("%Y-%m-%d %H:%M UTC")
    ts_end = window_end.strftime("%Y-%m-%d %H:%M UTC")
    total = sum(len(v) for v in results.values())

    lines = [
        f"## {ts_end} — {LOOKBACK_HOURS}h commit snapshot",
        f"",
        f"**Window:** {ts_start} → {ts_end}  ",
        f"**Total commits:** {total}",
        f"",
        f"| Repository | Commits |",
        f"|-----------|---------|",
    ]

    for repo, commits in sorted(results.items()):
        count = len(commits)
        lines.append(f"| `{repo}` | {count} |")

    # Per-repo detail
    for repo, commits in sorted(results.items()):
        if not commits:
            continue
        lines.append(f"")
        lines.append(f"### {repo}")
        for c in commits:
            sha = c["sha"][:7]
            msg = c["commit"]["message"].splitlines()[0][:80]
            author = c["commit"]["author"]["name"]
            date = c["commit"]["author"]["date"][:10]
            lines.append(f"- `{sha}` {date} **{author}**: {msg}")

    lines.append("")
    lines.append("---")
    lines.append("")
    return "\n".join(lines)


def main():
    if not GITHUB_TOKEN:
        print("[warn] GITHUB_TOKEN is not set. Private repos will return 403.")
        print("       Export GITHUB_TOKEN=<your_pat> before running, or add it to the cron env.")

    now = datetime.now(timezone.utc)
    since = now - timedelta(hours=LOOKBACK_HOURS)

    print(f"[{now.strftime('%Y-%m-%d %H:%M UTC')}] Checking {len(REPOS)} repo(s) for commits since {since.strftime('%H:%M UTC')}...")

    results: dict[str, list] = {}
    for repo in REPOS:
        print(f"  Fetching {repo}...")
        commits = fetch_commits_since(repo, since)
        results[repo] = commits
        print(f"    → {len(commits)} commit(s)")

    report = build_report(results, since, now)

    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    # Prepend to log so newest is at top
    existing = LOG_FILE.read_text() if LOG_FILE.exists() else "# GitHub Commit Log\n\n"
    # Insert after the top-level heading
    parts = existing.split("\n", 2)
    if len(parts) == 3:
        updated = parts[0] + "\n" + parts[1] + "\n" + report + parts[2]
    else:
        updated = existing + report

    LOG_FILE.write_text(updated)
    print(f"  Log updated → {LOG_FILE}")


if __name__ == "__main__":
    main()

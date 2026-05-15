#!/usr/bin/env python3
"""
Check GitHub commits made in the last 6 hours and append a summary to a markdown log.

Usage:
    GITHUB_TOKEN=<token> python3 check_commits.py
    GITHUB_TOKEN=<token> GITHUB_REPOS=owner/repo1,owner/repo2 python3 check_commits.py

Environment variables:
    GITHUB_TOKEN  - required: personal access token with repo read scope
    GITHUB_REPOS  - comma-separated list of owner/repo (defaults to peak-flow/peaktrack)
    HOURS_BACK    - how far back to look in hours (default: 6)
    LOG_FILE      - path to markdown log file (default: ../commit_log.md relative to this script)
"""

import json
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from pathlib import Path


GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
REPOS_ENV = os.environ.get("GITHUB_REPOS", "peak-flow/peaktrack")
HOURS_BACK = int(os.environ.get("HOURS_BACK", "6"))
SCRIPT_DIR = Path(__file__).parent
LOG_FILE = Path(os.environ.get("LOG_FILE", str(SCRIPT_DIR.parent / "commit_log.md")))


def github_get(path: str) -> list | dict:
    url = f"https://api.github.com{path}"
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {GITHUB_TOKEN}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def fetch_commits_since(repo: str, since: datetime) -> list[dict]:
    since_str = since.strftime("%Y-%m-%dT%H:%M:%SZ")
    commits = []
    page = 1
    while True:
        path = f"/repos/{repo}/commits?since={since_str}&per_page=100&page={page}"
        try:
            data = github_get(path)
        except urllib.error.HTTPError as e:
            print(f"  Warning: could not fetch {repo} (HTTP {e.code})", file=sys.stderr)
            break
        if not data:
            break
        commits.extend(data)
        if len(data) < 100:
            break
        page += 1
    return commits


def summarise_commits(commits: list[dict]) -> list[dict]:
    seen = set()
    rows = []
    for c in commits:
        sha = c["sha"][:7]
        if sha in seen:
            continue
        seen.add(sha)
        author = (c.get("commit", {}).get("author") or {}).get("name", "unknown")
        message = (c.get("commit", {}).get("message") or "").splitlines()[0][:80]
        ts = (c.get("commit", {}).get("author") or {}).get("date", "")
        rows.append({"sha": sha, "author": author, "message": message, "timestamp": ts})
    return rows


def build_markdown_section(run_time: datetime, since: datetime, results: dict[str, list[dict]]) -> str:
    total = sum(len(v) for v in results.values())
    lines = [
        f"## {run_time.strftime('%Y-%m-%d %H:%M UTC')} — {total} commit{'s' if total != 1 else ''} in last {HOURS_BACK}h",
        "",
        f"_Window: {since.strftime('%Y-%m-%d %H:%M UTC')} → {run_time.strftime('%Y-%m-%d %H:%M UTC')}_",
        "",
    ]

    if total == 0:
        lines += ["_No commits found._", ""]
    else:
        for repo, commits in results.items():
            count = len(commits)
            lines.append(f"### `{repo}` — {count} commit{'s' if count != 1 else ''}")
            lines.append("")
            if commits:
                lines.append("| SHA | Author | Message | Time |")
                lines.append("|-----|--------|---------|------|")
                for row in commits:
                    ts_display = row["timestamp"].replace("T", " ").replace("Z", " UTC") if row["timestamp"] else ""
                    lines.append(f"| `{row['sha']}` | {row['author']} | {row['message']} | {ts_display} |")
            lines.append("")

    lines.append("---")
    lines.append("")
    return "\n".join(lines)


def ensure_log_header(path: Path) -> None:
    if path.exists() and path.stat().st_size > 0:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "# GitHub Commit Log\n\nAuto-generated every 6 hours.\n\n---\n\n",
        encoding="utf-8",
    )


def main() -> None:
    if not GITHUB_TOKEN:
        print("Error: GITHUB_TOKEN environment variable is not set.", file=sys.stderr)
        sys.exit(1)

    repos = [r.strip() for r in REPOS_ENV.split(",") if r.strip()]
    now = datetime.now(timezone.utc)
    since = now - timedelta(hours=HOURS_BACK)

    print(f"Checking {len(repos)} repo(s) for commits since {since.strftime('%Y-%m-%d %H:%M UTC')} ...")

    results: dict[str, list[dict]] = {}
    for repo in repos:
        print(f"  Fetching {repo} ...", end=" ", flush=True)
        raw = fetch_commits_since(repo, since)
        rows = summarise_commits(raw)
        results[repo] = rows
        print(f"{len(rows)} commit(s)")

    section = build_markdown_section(now, since, results)

    ensure_log_header(LOG_FILE)
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(section)

    total = sum(len(v) for v in results.values())
    print(f"\nAppended to {LOG_FILE}  ({total} total commit(s))")


if __name__ == "__main__":
    main()

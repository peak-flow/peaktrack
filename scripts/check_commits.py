#!/usr/bin/env python3
"""
Check GitHub repos for commits in the last 6 hours and append a summary to a markdown file.
Requires GITHUB_TOKEN environment variable.
Configure REPOS list below.
"""

import os
import sys
import json
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta

# ── Configuration ──────────────────────────────────────────────────────────────
REPOS = [
    "peak-flow/peaktrack",
    # Add more "owner/repo" entries here
]

OUTPUT_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "commit_log.md")
LOOKBACK_HOURS = 6
# ───────────────────────────────────────────────────────────────────────────────

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
API_BASE = "https://api.github.com"


def github_get(path: str) -> list | dict:
    url = f"{API_BASE}{path}"
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    if GITHUB_TOKEN:
        req.add_header("Authorization", f"Bearer {GITHUB_TOKEN}")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def get_commits_since(repo: str, since: datetime) -> list[dict]:
    since_iso = since.strftime("%Y-%m-%dT%H:%M:%SZ")
    try:
        data = github_get(f"/repos/{repo}/commits?since={since_iso}&per_page=100")
        if not isinstance(data, list):
            return []
        return data
    except urllib.error.HTTPError as e:
        print(f"  Warning: {repo} returned HTTP {e.code}", file=sys.stderr)
        return []


def build_markdown_section(results: dict[str, list], window_start: datetime, window_end: datetime) -> str:
    ts = window_end.strftime("%Y-%m-%d %H:%M UTC")
    window_label = f"{window_start.strftime('%Y-%m-%d %H:%M')} – {window_end.strftime('%H:%M')} UTC"
    total = sum(len(v) for v in results.values())

    lines = [
        f"## {ts}  ({total} commit{'s' if total != 1 else ''} in last {LOOKBACK_HOURS}h)",
        f"_Window: {window_label}_",
        "",
        "| Repository | Commits | Authors |",
        "| ---------- | ------: | ------- |",
    ]

    for repo, commits in sorted(results.items()):
        count = len(commits)
        authors = sorted({c["commit"]["author"]["name"] for c in commits})
        author_str = ", ".join(authors) if authors else "—"
        lines.append(f"| `{repo}` | {count} | {author_str} |")

    lines.append("")

    # Per-repo commit details
    for repo, commits in sorted(results.items()):
        if not commits:
            continue
        lines.append(f"### {repo}")
        for c in commits:
            sha = c["sha"][:7]
            msg = c["commit"]["message"].splitlines()[0][:80]
            author = c["commit"]["author"]["name"]
            date = c["commit"]["author"]["date"][:16].replace("T", " ")
            lines.append(f"- `{sha}` {msg}  _(_{author}_, {date})_")
        lines.append("")

    lines.append("---")
    lines.append("")
    return "\n".join(lines)


def ensure_header(path: str) -> None:
    if not os.path.exists(path):
        with open(path, "w") as f:
            f.write("# GitHub Commit Log\n\nAuto-generated every 6 hours.\n\n---\n\n")


def main() -> None:
    if not GITHUB_TOKEN:
        print("Warning: GITHUB_TOKEN not set — unauthenticated requests are rate-limited to 60/hour.", file=sys.stderr)

    now = datetime.now(timezone.utc)
    since = now - timedelta(hours=LOOKBACK_HOURS)

    print(f"Checking {len(REPOS)} repo(s) for commits since {since.strftime('%Y-%m-%d %H:%M UTC')} …")

    results: dict[str, list] = {}
    for repo in REPOS:
        print(f"  {repo} … ", end="", flush=True)
        commits = get_commits_since(repo, since)
        results[repo] = commits
        print(f"{len(commits)} commit(s)")

    section = build_markdown_section(results, since, now)

    ensure_header(OUTPUT_FILE)
    with open(OUTPUT_FILE, "a") as f:
        f.write(section)

    total = sum(len(v) for v in results.values())
    print(f"\nAppended to {OUTPUT_FILE}  ({total} total commit(s))")


if __name__ == "__main__":
    main()

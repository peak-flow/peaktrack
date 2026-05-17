#!/usr/bin/env python3
"""
Check peak-flow/peaktrack for commits in the last 6 hours and append a
timestamped entry to commit-report.md.

Usage:
    GITHUB_TOKEN=ghp_... python3 check_commits.py
    python3 check_commits.py --token ghp_...
    python3 check_commits.py --hours 6   # default
"""

import argparse
import json
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from pathlib import Path

OWNER = "peak-flow"
REPO = "peaktrack"
REPORT_FILE = Path(__file__).parent / "commit-report.md"

HEADER = "# GitHub Commit Report — peak-flow/peaktrack\n\nAuto-generated every 6 hours. Run `python3 check_commits.py` to generate a new entry.\n\n---\n"


def github_get(path: str, token: str) -> list | dict:
    url = f"https://api.github.com{path}"
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def list_branches(token: str) -> list[str]:
    branches = []
    page = 1
    while True:
        data = github_get(
            f"/repos/{OWNER}/{REPO}/branches?per_page=100&page={page}", token
        )
        if not data:
            break
        branches.extend(b["name"] for b in data)
        if len(data) < 100:
            break
        page += 1
    return branches


def commits_on_branch(branch: str, since: str, token: str) -> list[dict]:
    try:
        data = github_get(
            f"/repos/{OWNER}/{REPO}/commits"
            f"?sha={urllib.parse.quote(branch, safe='')}"
            f"&since={since}&per_page=100",
            token,
        )
        return data if isinstance(data, list) else []
    except urllib.error.HTTPError:
        return []


def main():
    import urllib.parse  # noqa: needed inside commits_on_branch

    parser = argparse.ArgumentParser()
    parser.add_argument("--token", default=os.environ.get("GITHUB_TOKEN", ""))
    parser.add_argument("--hours", type=int, default=6)
    args = parser.parse_args()

    if not args.token:
        sys.exit("Error: set GITHUB_TOKEN env var or pass --token")

    now = datetime.now(timezone.utc)
    since = now - timedelta(hours=args.hours)
    since_str = since.strftime("%Y-%m-%dT%H:%M:%SZ")
    now_str = now.strftime("%Y-%m-%dT%H:%M:%SZ")

    print(f"Checking commits from {since_str} to {now_str} ...")

    branches = list_branches(args.token)
    print(f"Found {len(branches)} branches.")

    seen_shas: set[str] = set()
    branch_results: list[tuple[str, list[dict]]] = []

    for branch in branches:
        commits = commits_on_branch(branch, since_str, args.token)
        new = [c for c in commits if c["sha"] not in seen_shas]
        for c in new:
            seen_shas.add(c["sha"])
        if new:
            branch_results.append((branch, new))
            print(f"  {branch}: {len(new)} new commit(s)")

    total = sum(len(cs) for _, cs in branch_results)

    lines = [f"\n## {now_str} — Window: {since_str} → {now_str}\n"]
    lines.append("| Metric | Value |")
    lines.append("|--------|-------|")
    lines.append(f"| Total commits | {total} |")
    lines.append(f"| Active branches | {len(branch_results)} |")
    lines.append(f"| Branches scanned | {len(branches)} |\n")

    if branch_results:
        for branch, commits in branch_results:
            lines.append(f"### Branch: `{branch}` ({len(commits)} commit(s))\n")
            lines.append("| SHA | Author | Message |")
            lines.append("|-----|--------|---------|")
            for c in commits:
                sha = c["sha"][:8]
                author = (c.get("commit", {}).get("author") or {}).get("name", "unknown")
                msg = (c.get("commit", {}).get("message") or "").split("\n")[0][:80]
                msg = msg.replace("|", "\\|")
                lines.append(f"| `{sha}` | {author} | {msg} |")
            lines.append("")
    else:
        lines.append("No commits found in this window across all branches.\n")

    lines.append("---\n")

    if not REPORT_FILE.exists():
        REPORT_FILE.write_text(HEADER)

    with REPORT_FILE.open("a") as f:
        f.write("\n".join(lines))

    print(f"\nReport appended to {REPORT_FILE}")
    print(f"Total: {total} commits across {len(branch_results)} branches.")


if __name__ == "__main__":
    main()

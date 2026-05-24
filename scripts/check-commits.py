#!/usr/bin/env python3
"""
GitHub commit tracker — counts commits across all peak-flow repos in the last N hours
and appends a timestamped report to reports/commit-log.md.

Requires: GITHUB_TOKEN env var (a personal access token with repo scope)
Usage: python3 scripts/check-commits.py [--hours 6]
"""

import os
import sys
import json
import argparse
from datetime import datetime, timezone, timedelta
from urllib.request import urlopen, Request
from urllib.error import HTTPError

OWNER = "peak-flow"
REPORT_PATH = os.path.join(os.path.dirname(__file__), "..", "reports", "commit-log.md")


def gh_get(path, token, params=""):
    url = f"https://api.github.com{path}{'?' + params if params else ''}"
    req = Request(url, headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    })
    with urlopen(req) as r:
        return json.loads(r.read())


def get_all_repos(token):
    repos = []
    page = 1
    while True:
        batch = gh_get(f"/users/{OWNER}/repos", token,
                       f"per_page=100&page={page}&sort=pushed&direction=desc")
        if not batch:
            break
        repos.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return repos


def get_commits_since(owner, repo, default_branch, since_iso, token):
    try:
        commits = gh_get(
            f"/repos/{owner}/{repo}/commits",
            token,
            f"sha={default_branch}&since={since_iso}&per_page=100",
        )
        return commits if isinstance(commits, list) else []
    except HTTPError as e:
        if e.code in (409, 404, 451):  # empty repo, not found, or unavailable
            return []
        raise


def build_report(hours, since_iso, now_iso, repo_results):
    total = sum(c for _, c, _ in repo_results)
    active = [(r, c, b) for r, c, b in repo_results if c > 0]

    lines = [
        f"## {now_iso}",
        f"**Period:** last {hours} hours  (since `{since_iso}`)",
        f"**Total commits:** {total} across {len(active)} repo(s)",
        "",
    ]

    if active:
        lines.append("| Repository | Branch | Commits |")
        lines.append("|---|---|---:|")
        for repo, count, branch in sorted(active, key=lambda x: -x[1]):
            lines.append(f"| [{repo}](https://github.com/{OWNER}/{repo}) | `{branch}` | {count} |")
    else:
        lines.append("_No commits in this period._")

    lines.append("")
    lines.append("---")
    lines.append("")
    return "\n".join(lines)


def ensure_header(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not os.path.exists(path):
        with open(path, "w") as f:
            f.write(f"# Commit Log — {OWNER}\n\n")
            f.write("Auto-generated every 6 hours. Each entry covers the preceding 6-hour window.\n\n")
            f.write("---\n\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--hours", type=int, default=6)
    args = parser.parse_args()

    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("ERROR: GITHUB_TOKEN environment variable is not set.", file=sys.stderr)
        print("Add it via Claude Code settings → Environment Variables.", file=sys.stderr)
        sys.exit(1)

    now = datetime.now(timezone.utc)
    since = now - timedelta(hours=args.hours)
    since_iso = since.strftime("%Y-%m-%dT%H:%M:%SZ")
    now_iso = now.strftime("%Y-%m-%dT%H:%M:%SZ")

    print(f"Fetching repos for {OWNER}...")
    repos = get_all_repos(token)
    print(f"Found {len(repos)} repos. Checking commits since {since_iso}...")

    results = []
    for i, repo in enumerate(repos, 1):
        name = repo["name"]
        branch = repo.get("default_branch", "main")
        pushed_at = repo.get("pushed_at") or ""
        # Skip repos not pushed to since the window
        if pushed_at and pushed_at < since_iso:
            results.append((name, 0, branch))
            continue
        commits = get_commits_since(OWNER, name, branch, since_iso, token)
        count = len(commits)
        if count > 0:
            print(f"  [{i}/{len(repos)}] {name}: {count} commit(s)")
        results.append((name, count, branch))

    report = build_report(args.hours, since_iso, now_iso, results)

    report_path = os.path.abspath(REPORT_PATH)
    ensure_header(report_path)
    with open(report_path, "a") as f:
        f.write(report)

    total = sum(c for _, c, _ in results)
    active = sum(1 for _, c, _ in results if c > 0)
    print(f"\nDone. {total} commit(s) across {active} repo(s). Report appended to {report_path}")


if __name__ == "__main__":
    main()

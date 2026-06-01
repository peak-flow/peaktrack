#!/usr/bin/env python3
"""
Fetches commits from all repos in a GitHub org (or a specified list)
made in the last N hours and appends a summary to commit-log.md.
"""

import os
import sys
import json
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
ORG = os.environ.get("GITHUB_ORG", "peak-flow")
HOURS = int(os.environ.get("LOOKBACK_HOURS", "6"))
LOG_FILE = os.environ.get("LOG_FILE", "commit-log.md")


def gh_get(path: str) -> list | dict:
    url = f"https://api.github.com{path}"
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {GITHUB_TOKEN}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def list_org_repos() -> list[str]:
    repos = []
    page = 1
    while True:
        page_data = gh_get(f"/orgs/{ORG}/repos?per_page=100&page={page}&type=all")
        if not page_data:
            break
        repos.extend(r["name"] for r in page_data)
        if len(page_data) < 100:
            break
        page += 1
    return repos


def count_commits_since(repo: str, since: str) -> list[dict]:
    try:
        data = gh_get(f"/repos/{ORG}/{repo}/commits?since={since}&per_page=100")
        return [
            {
                "sha": c["sha"][:7],
                "author": (c.get("commit", {}).get("author") or {}).get("name", "unknown"),
                "message": (c.get("commit", {}).get("message") or "").splitlines()[0][:80],
                "date": (c.get("commit", {}).get("author") or {}).get("date", ""),
            }
            for c in data
        ]
    except urllib.error.HTTPError as e:
        if e.code in (404, 409):  # repo not found or empty
            return []
        raise


def build_markdown(since_dt: datetime, until_dt: datetime, results: dict[str, list]) -> str:
    total = sum(len(v) for v in results.values())
    active = {k: v for k, v in results.items() if v}

    lines = [
        f"## {until_dt.strftime('%Y-%m-%d %H:%M UTC')} — last {HOURS}h report",
        "",
        f"**Total commits:** {total}  "
        f"**Active repos:** {len(active)} / {len(results)}",
        "",
    ]

    if not active:
        lines.append("_No commits in this window._")
    else:
        for repo, commits in sorted(active.items(), key=lambda x: -len(x[1])):
            lines.append(f"### `{ORG}/{repo}` ({len(commits)} commit{'s' if len(commits) != 1 else ''})")
            for c in commits:
                lines.append(f"- [`{c['sha']}`] **{c['author']}** — {c['message']}")
            lines.append("")

    lines.append("---")
    lines.append("")
    return "\n".join(lines)


def ensure_log_header(path: str) -> None:
    if not os.path.exists(path):
        with open(path, "w") as f:
            f.write(f"# Commit Activity Log — {ORG}\n\n")
            f.write("Auto-generated every 6 hours by [commit-tracker](.github/workflows/commit-tracker.yml).\n\n")
            f.write("---\n\n")


def prepend_to_log(path: str, block: str) -> None:
    with open(path, "r") as f:
        existing = f.read()
    # Insert after the header section (first ---\n\n)
    marker = "---\n\n"
    idx = existing.find(marker)
    if idx == -1:
        with open(path, "w") as f:
            f.write(existing + block)
    else:
        insert_at = idx + len(marker)
        with open(path, "w") as f:
            f.write(existing[:insert_at] + block + existing[insert_at:])


def main():
    if not GITHUB_TOKEN:
        print("ERROR: GITHUB_TOKEN is not set", file=sys.stderr)
        sys.exit(1)

    until_dt = datetime.now(timezone.utc)
    since_dt = until_dt - timedelta(hours=HOURS)
    since_iso = since_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    print(f"Scanning {ORG} repos for commits since {since_iso} …")
    repos = list_org_repos()
    print(f"Found {len(repos)} repo(s): {', '.join(repos)}")

    results: dict[str, list] = {}
    for repo in repos:
        commits = count_commits_since(repo, since_iso)
        results[repo] = commits
        if commits:
            print(f"  {repo}: {len(commits)} commit(s)")

    block = build_markdown(since_dt, until_dt, results)

    ensure_log_header(LOG_FILE)
    prepend_to_log(LOG_FILE, block)
    print(f"Log updated: {LOG_FILE}")


if __name__ == "__main__":
    main()

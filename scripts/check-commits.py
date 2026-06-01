#!/usr/bin/env python3
"""Check GitHub for commits in the last 6 hours and append results to commit-activity.md."""

import os
import sys
import json
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta

REPOS = [
    {"owner": "peak-flow", "repo": "peaktrack"},
]

OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "..", "commit-activity.md")


def github_request(path, token):
    url = f"https://api.github.com{path}"
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    req.add_header("User-Agent", "peaktrack-commit-checker")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def get_commits_since(owner, repo, since_iso, token):
    path = f"/repos/{owner}/{repo}/commits?since={since_iso}&per_page=100"
    try:
        commits = github_request(path, token)
        return len(commits) if isinstance(commits, list) else 0
    except urllib.error.HTTPError as e:
        print(f"  ERROR fetching {owner}/{repo}: HTTP {e.code}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"  ERROR fetching {owner}/{repo}: {e}", file=sys.stderr)
        return None


def ensure_header(path):
    if not os.path.exists(path):
        with open(path, "w") as f:
            f.write("# GitHub Commit Activity\n\n")
            f.write("Auto-generated every 6 hours. Tracks commits per repo in the preceding 6-hour window.\n\n")


def append_entry(path, now, since, results):
    now_str = now.strftime("%Y-%m-%d %H:%M UTC")
    since_str = since.strftime("%Y-%m-%d %H:%M UTC")
    total = sum(c for c in results.values() if c is not None)

    entry = f"## {now_str}\n\n"
    entry += f"**Window:** {since_str} → {now_str}  \n"
    entry += f"**Total commits:** {total}\n\n"
    entry += "| Repository | Commits |\n"
    entry += "| --- | --- |\n"
    for repo_key, count in results.items():
        count_str = str(count) if count is not None else "error"
        entry += f"| `{repo_key}` | {count_str} |\n"
    entry += "\n"

    with open(path, "a") as f:
        f.write(entry)

    print(entry.strip())


def main():
    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        print("ERROR: GITHUB_TOKEN environment variable is not set.", file=sys.stderr)
        sys.exit(1)

    now = datetime.now(timezone.utc)
    since = now - timedelta(hours=6)
    since_iso = since.strftime("%Y-%m-%dT%H:%M:%SZ")

    output_path = os.path.realpath(OUTPUT_FILE)
    ensure_header(output_path)

    results = {}
    for r in REPOS:
        key = f"{r['owner']}/{r['repo']}"
        print(f"Checking {key} since {since_iso}...")
        count = get_commits_since(r["owner"], r["repo"], since_iso, token)
        results[key] = count

    append_entry(output_path, now, since, results)


if __name__ == "__main__":
    main()

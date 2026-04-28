#!/usr/bin/env python3
"""Check GitHub for commits in the last 6 hours and append a summary to github-commits-log.md."""

import json
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta

OWNER = "peak-flow"
REPO = "peaktrack"
HOURS = 6
LOG_FILE = "/home/user/peaktrack/github-commits-log.md"
TOKEN_FILE = os.path.expanduser("~/.github_token")


def get_token():
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if token:
        return token
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE) as f:
            return f.read().strip()
    return None


def github_get(path, token):
    url = f"https://api.github.com{path}"
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def fetch_commits_since(owner, repo, since_iso, token):
    """Fetch all commits across all branches since `since_iso`."""
    seen = set()
    all_commits = []

    # Get branches
    branches = github_get(f"/repos/{owner}/{repo}/branches?per_page=100", token)

    for branch in branches:
        branch_name = branch["name"]
        page = 1
        while True:
            path = (
                f"/repos/{owner}/{repo}/commits"
                f"?sha={branch_name}&since={since_iso}&per_page=100&page={page}"
            )
            try:
                commits = github_get(path, token)
            except urllib.error.HTTPError as e:
                print(f"  Warning: could not fetch {branch_name}: {e}", file=sys.stderr)
                break

            if not commits:
                break

            for c in commits:
                sha = c["sha"]
                if sha not in seen:
                    seen.add(sha)
                    all_commits.append({
                        "sha": sha[:7],
                        "branch": branch_name,
                        "message": c["commit"]["message"].splitlines()[0],
                        "author": c["commit"]["author"]["name"],
                        "date": c["commit"]["author"]["date"],
                    })

            if len(commits) < 100:
                break
            page += 1

    return all_commits, [b["name"] for b in branches]


def append_to_log(log_path, commits, branches, since_dt, now_dt):
    # Create file with header if it doesn't exist
    if not os.path.exists(log_path):
        with open(log_path, "w") as f:
            f.write("# GitHub Commit Log — peak-flow/peaktrack\n\n")
            f.write("Auto-generated every 6 hours.\n\n")

    # Group commits by branch for the summary
    by_branch = {}
    for c in commits:
        by_branch.setdefault(c["branch"], []).append(c)

    timestamp = now_dt.strftime("%Y-%m-%d %H:%M UTC")
    window_start = since_dt.strftime("%Y-%m-%d %H:%M UTC")

    lines = [
        f"## {timestamp}",
        f"",
        f"**Window:** {window_start} → {timestamp}  ",
        f"**Repo:** peak-flow/peaktrack  ",
        f"**Branches checked:** {len(branches)}  ",
        f"**Total new commits:** {len(commits)}",
        f"",
    ]

    if not commits:
        lines.append("_No commits in this window._")
    else:
        for branch, branch_commits in sorted(by_branch.items()):
            lines.append(f"### Branch: `{branch}` ({len(branch_commits)} commit{'s' if len(branch_commits) != 1 else ''})")
            lines.append("")
            for c in branch_commits:
                lines.append(f"- `{c['sha']}` {c['message']} _(by {c['author']} at {c['date']})_")
            lines.append("")

    lines.append("---")
    lines.append("")

    with open(log_path, "a") as f:
        f.write("\n".join(lines) + "\n")

    return len(commits)


def main():
    token = get_token()
    if not token:
        print(
            f"ERROR: No GitHub token found.\n"
            f"Set GITHUB_TOKEN env var or write your token to {TOKEN_FILE}",
            file=sys.stderr,
        )
        sys.exit(1)

    now = datetime.now(timezone.utc)
    since = now - timedelta(hours=HOURS)
    since_iso = since.strftime("%Y-%m-%dT%H:%M:%SZ")

    print(f"Checking peak-flow/peaktrack for commits since {since_iso}...")

    commits, branches = fetch_commits_since(OWNER, REPO, since_iso, token)
    count = append_to_log(LOG_FILE, commits, branches, since, now)

    print(f"Done. {count} commit(s) found across {len(branches)} branch(es). Log: {LOG_FILE}")


if __name__ == "__main__":
    main()

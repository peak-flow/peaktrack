#!/usr/bin/env python3
"""Check peak-flow/peaktrack for commits in the last 6 hours and append to commit-log.md."""

import json
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta

OWNER = "peak-flow"
REPO = "peaktrack"
LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "commit-log.md")
HOURS = 6


def get_token():
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        return token
    config_path = os.path.expanduser("~/.config/peaktrack/github_token")
    if os.path.exists(config_path):
        with open(config_path) as f:
            return f.read().strip()
    sys.exit("ERROR: No GitHub token found. Set GITHUB_TOKEN env var or write token to ~/.config/peaktrack/github_token")


def gh_get(path, token, params=None):
    url = f"https://api.github.com{path}"
    if params:
        url += "?" + "&".join(f"{k}={v}" for k, v in params.items())
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    })
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def get_all_branches(token):
    branches = []
    page = 1
    while True:
        page_data = gh_get(f"/repos/{OWNER}/{REPO}/branches", token, {"per_page": "100", "page": str(page)})
        if not page_data:
            break
        branches.extend(page_data)
        if len(page_data) < 100:
            break
        page += 1
    return branches


def get_commits_since(sha, since_iso, token):
    try:
        return gh_get(f"/repos/{OWNER}/{REPO}/commits", token, {
            "sha": sha,
            "since": since_iso,
            "per_page": "100",
        })
    except urllib.error.HTTPError:
        return []


def main():
    token = get_token()
    now = datetime.now(timezone.utc)
    since = now - timedelta(hours=HOURS)
    since_iso = since.strftime("%Y-%m-%dT%H:%M:%SZ")
    now_iso = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    now_label = now.strftime("%Y-%m-%d %H:%M UTC")

    print(f"Checking commits from {since_iso} to {now_iso}...")

    branches = get_all_branches(token)
    print(f"Found {len(branches)} branches")

    # Collect commits, deduplicated by SHA
    seen_shas = set()
    commit_entries = []  # list of (sha, message, author, date, branch)

    for branch in branches:
        commits = get_commits_since(branch["name"], since_iso, token)
        for c in commits:
            sha = c["sha"]
            if sha in seen_shas:
                continue
            seen_shas.add(sha)
            author = (c.get("commit", {}).get("author") or {}).get("name", "unknown")
            message = (c.get("commit", {}).get("message") or "").splitlines()[0]
            date = (c.get("commit", {}).get("author") or {}).get("date", "")
            commit_entries.append({
                "sha": sha[:7],
                "message": message,
                "author": author,
                "date": date,
                "branch": branch["name"],
            })

    total = len(commit_entries)
    print(f"Found {total} unique commit(s)")

    # Build branches summary
    branch_counts = {}
    for e in commit_entries:
        branch_counts[e["branch"]] = branch_counts.get(e["branch"], 0) + 1

    # Build markdown section
    lines = [
        f"## {now_label}",
        "",
        f"**Period:** {since_iso} → {now_iso}",
        "",
        f"**Total commits:** {total}",
        "",
    ]

    if total == 0:
        lines.append("No new commits found across all branches during this period.")
    else:
        lines.append("### By branch")
        lines.append("")
        for branch, count in sorted(branch_counts.items()):
            lines.append(f"- `{branch}`: {count} commit(s)")
        lines.append("")
        lines.append("### Commits")
        lines.append("")
        lines.append("| SHA | Branch | Author | Date | Message |")
        lines.append("|-----|--------|--------|------|---------|")
        for e in sorted(commit_entries, key=lambda x: x["date"], reverse=True):
            msg = e["message"].replace("|", "\\|")[:80]
            lines.append(f"| `{e['sha']}` | `{e['branch']}` | {e['author']} | {e['date'][:16]} | {msg} |")

    lines.append("")
    lines.append("---")
    lines.append("")

    section = "\n".join(lines)

    # Append to log file (insert after the header, before first ---)
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, "w") as f:
            f.write("# PeakTrack Commit Log\n\nAutomated 6-hour commit snapshots for `peak-flow/peaktrack`.\n\n---\n\n")

    with open(LOG_FILE, "r") as f:
        content = f.read()

    # Insert new section after the first "---\n\n"
    insert_after = "---\n\n"
    idx = content.find(insert_after)
    if idx != -1:
        insert_pos = idx + len(insert_after)
        content = content[:insert_pos] + section + "\n" + content[insert_pos:]
    else:
        content += "\n" + section + "\n"

    with open(LOG_FILE, "w") as f:
        f.write(content)

    print(f"Appended to {LOG_FILE}")


if __name__ == "__main__":
    main()

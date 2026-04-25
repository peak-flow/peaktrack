#!/usr/bin/env python3
"""
Checks GitHub for commits made in the last 6 hours across all accessible repos
and appends a summary to commit_log.md.

Requires: GITHUB_TOKEN environment variable (or edit TOKEN below).
"""

import os
import sys
import json
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta

TOKEN = os.environ.get("GITHUB_TOKEN", "")
OUTPUT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "commit_log.md")
HOURS = 6


def gh_get(path, token):
    url = f"https://api.github.com{path}"
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "peaktrack-commit-checker",
    })
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def get_all_pages(path, token):
    results = []
    page = 1
    while True:
        sep = "&" if "?" in path else "?"
        data = gh_get(f"{path}{sep}per_page=100&page={page}", token)
        if not data:
            break
        results.extend(data)
        if len(data) < 100:
            break
        page += 1
    return results


def main():
    if not TOKEN:
        print("ERROR: GITHUB_TOKEN environment variable is not set.", file=sys.stderr)
        print("Set it with: export GITHUB_TOKEN=your_token_here", file=sys.stderr)
        sys.exit(1)

    since = datetime.now(timezone.utc) - timedelta(hours=HOURS)
    since_iso = since.strftime("%Y-%m-%dT%H:%M:%SZ")
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    print(f"Checking commits since {since_iso} ...")

    # Get authenticated user
    user = gh_get("/user", TOKEN)
    username = user["login"]

    # Get all repos (owned + member of)
    repos = get_all_pages("/user/repos?affiliation=owner,collaborator,organization_member&sort=pushed", TOKEN)

    repo_summaries = []
    total_commits = 0

    for repo in repos:
        repo_name = repo["full_name"]
        # Skip repos not pushed to recently (optimization)
        pushed_at = repo.get("pushed_at", "")
        if pushed_at and pushed_at < since_iso:
            continue

        try:
            commits = get_all_pages(
                f"/repos/{repo_name}/commits?since={since_iso}&author={username}",
                TOKEN,
            )
        except urllib.error.HTTPError as e:
            if e.code in (409, 404):  # empty repo or no access
                continue
            raise

        if commits:
            count = len(commits)
            total_commits += count
            messages = [
                c["commit"]["message"].split("\n")[0][:80]
                for c in commits[:5]  # show up to 5 latest
            ]
            repo_summaries.append({
                "repo": repo_name,
                "count": count,
                "messages": messages,
            })

    # Build markdown section
    lines = [
        f"## {now_str} — last {HOURS}h",
        f"",
        f"**Total commits:** {total_commits}  ",
        f"**Repos with activity:** {len(repo_summaries)}",
        "",
    ]

    if repo_summaries:
        for entry in sorted(repo_summaries, key=lambda x: -x["count"]):
            lines.append(f"### `{entry['repo']}` — {entry['count']} commit{'s' if entry['count'] != 1 else ''}")
            for msg in entry["messages"]:
                lines.append(f"- {msg}")
            if entry["count"] > len(entry["messages"]):
                lines.append(f"- *(+{entry['count'] - len(entry['messages'])} more)*")
            lines.append("")
    else:
        lines.append("*No commits in this period.*")
        lines.append("")

    lines.append("---")
    lines.append("")
    section = "\n".join(lines)

    # Prepend to file (newest first) or create it
    header = "# GitHub Commit Log\n\n"
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "r") as f:
            existing = f.read()
        # Strip the header if present so we can re-prepend it
        if existing.startswith(header):
            existing = existing[len(header):]
        new_content = header + section + existing
    else:
        new_content = header + section

    with open(OUTPUT_FILE, "w") as f:
        f.write(new_content)

    print(f"Done. {total_commits} commit(s) across {len(repo_summaries)} repo(s).")
    print(f"Saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Counts commits across the peak-flow org made in the last 6 hours
and writes a summary to commit-report.md.

Requires: gh CLI authenticated via GH_TOKEN env var.
"""

import json
import subprocess
import datetime
import sys

ORG = "peak-flow"
HOURS = 6
REPORT_FILE = "commit-report.md"


def gh_api(endpoint: str) -> list | dict:
    result = subprocess.run(
        ["gh", "api", "--paginate", endpoint],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"  [warn] gh api {endpoint}: {result.stderr.strip()}", file=sys.stderr)
        return []
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return []


def main():
    since_dt = datetime.datetime.utcnow() - datetime.timedelta(hours=HOURS)
    since = since_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    now_str = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    print(f"Checking {ORG} repos for commits since {since} ...")

    # Fetch all repos sorted by most recently pushed — stop early once
    # pushed_at drops below our window (repos are sorted desc by pushed_at).
    repos_raw = gh_api(f"orgs/{ORG}/repos?per_page=100&sort=pushed&direction=desc")
    if not repos_raw:
        print("No repos returned — check GH_TOKEN permissions.", file=sys.stderr)
        sys.exit(1)

    active_repos = [r for r in repos_raw if r.get("pushed_at", "") >= since]
    print(f"Repos pushed in last {HOURS}h: {len(active_repos)}")

    results = []
    total_commits = 0

    for repo in active_repos:
        name = repo["full_name"]
        commits = gh_api(f"repos/{name}/commits?since={since}&per_page=100")
        count = len(commits)
        if count == 0:
            continue

        total_commits += count
        results.append(
            {
                "repo": name,
                "count": count,
                "url": repo["html_url"],
                "commits": [
                    {
                        "sha": c["sha"][:7],
                        "message": c["commit"]["message"].splitlines()[0][:80],
                        "author": c["commit"]["author"]["name"],
                        "time": c["commit"]["author"]["date"],
                    }
                    for c in commits
                ],
            }
        )
        print(f"  {name}: {count} commit(s)")

    results.sort(key=lambda x: x["count"], reverse=True)

    # Build markdown
    lines = [
        "# Commit Activity Report",
        "",
        f"**Generated:** {now_str}  ",
        f"**Period:** Last {HOURS} hours (since {since})  ",
        f"**Total commits:** {total_commits}  ",
        f"**Repos with activity:** {len(results)}",
        "",
    ]

    if results:
        lines += [
            "## Summary",
            "",
            "| Repository | Commits |",
            "|:-----------|--------:|",
        ]
        for r in results:
            lines.append(f"| [{r['repo']}]({r['url']}) | {r['count']} |")

        lines += ["", "## Commit Details", ""]
        for r in results:
            lines.append(
                f"### [{r['repo']}]({r['url']}) &mdash; {r['count']} commit(s)"
            )
            lines.append("")
            for c in r["commits"]:
                lines.append(
                    f"- `{c['sha']}` {c['time']} **{c['author']}**: {c['message']}"
                )
            lines.append("")
    else:
        lines += ["*No commits found in the last 6 hours.*", ""]

    content = "\n".join(lines)
    with open(REPORT_FILE, "w") as f:
        f.write(content)

    print(f"\nWrote {REPORT_FILE}: {total_commits} commit(s) across {len(results)} repo(s)")


if __name__ == "__main__":
    main()

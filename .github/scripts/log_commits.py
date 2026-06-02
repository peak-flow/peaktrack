#!/usr/bin/env python3
"""
Checks all peak-flow org repos for commits in the last 6 hours and
appends a new entry to commit-log.md.

Requires: GH_TOKEN env var with read:org + repo scope (set as COMMIT_LOG_TOKEN secret).
Falls back to GITHUB_TOKEN for single-repo access only.
"""
import json
import os
import subprocess
from datetime import datetime, timezone, timedelta
from pathlib import Path

ORG = os.environ.get("ORG", "peak-flow")
LOG_FILE = Path("commit-log.md")
NOW = datetime.now(timezone.utc)
SINCE = (NOW - timedelta(hours=6)).strftime("%Y-%m-%dT%H:%M:%SZ")
NOW_STR = NOW.strftime("%Y-%m-%d %H:%M:%S UTC")


def gh(*args):
    result = subprocess.run(["gh"] + list(args), capture_output=True, text=True)
    if result.returncode != 0:
        return None
    return result.stdout


def gh_json(endpoint):
    out = gh("api", "--paginate", endpoint)
    if not out:
        return []
    try:
        data = json.loads(out)
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        return []


def get_repos():
    out = gh("repo", "list", ORG, "--limit", "200", "--json", "name")
    if not out:
        return []
    try:
        return [r["name"] for r in json.loads(out)]
    except (json.JSONDecodeError, KeyError):
        return []


def main():
    if not LOG_FILE.exists():
        LOG_FILE.write_text(
            "# GitHub Commit Log\n\n"
            f"Automated log of commits across the `{ORG}` organization, updated every 6 hours.\n\n"
        )

    repos = get_repos()
    print(f"Checking {len(repos)} repos since {SINCE}...")

    repo_commits: dict[str, list] = {}
    for repo in repos:
        commits = gh_json(f"repos/{ORG}/{repo}/commits?since={SINCE}&per_page=100")
        if commits:
            repo_commits[repo] = commits
            print(f"  {repo}: {len(commits)} commit(s)")

    lines: list[str] = [f"## {NOW_STR}", ""]

    if not repo_commits:
        lines.append("No commits found in the last 6 hours.")
        lines.append("")
    else:
        total = sum(len(c) for c in repo_commits.values())
        lines.append(f"**Total commits:** {total}  ")
        lines.append(f"**Repos with activity:** {len(repo_commits)}")
        lines.append("")
        lines.append("| Repository | Commits |")
        lines.append("|---|---|")
        for repo in sorted(repo_commits):
            lines.append(f"| `{ORG}/{repo}` | {len(repo_commits[repo])} |")
        lines.append("")
        for repo in sorted(repo_commits):
            commits = repo_commits[repo]
            lines.append(f"### `{ORG}/{repo}`")
            lines.append("")
            for c in commits:
                sha = c.get("sha", "")[:7]
                author = c.get("commit", {}).get("author", {}).get("name", "unknown")
                message = c.get("commit", {}).get("message", "").split("\n")[0]
                lines.append(f"- `{sha}` **{author}**: {message}")
            lines.append("")

    new_entry = "\n".join(lines) + "\n"

    existing = LOG_FILE.read_text()

    # Insert new entry after the file header (before first existing ## entry)
    first_entry = existing.find("\n## ")
    if first_entry != -1:
        header = existing[: first_entry + 1]
        rest = existing[first_entry + 1 :]
        LOG_FILE.write_text(header + new_entry + "\n" + rest)
    else:
        LOG_FILE.write_text(existing + new_entry)

    summary = (
        "no commits found"
        if not repo_commits
        else f"{sum(len(c) for c in repo_commits.values())} commits across {len(repo_commits)} repo(s)"
    )
    print(f"Done — {summary}. Log updated at {LOG_FILE}")


if __name__ == "__main__":
    main()

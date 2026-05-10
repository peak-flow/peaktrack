#!/usr/bin/env python3
"""
Checks GitHub for commits made in the last 6 hours across all accessible repos
and appends a summary to a markdown file.

Usage:
    GITHUB_TOKEN=your_token python3 github_commit_tracker.py [--output path/to/report.md]

Required env var:
    GITHUB_TOKEN  - GitHub personal access token (needs repo scope)

Optional env vars:
    GITHUB_ORGS   - Comma-separated list of orgs to include (e.g. "myorg,anotherorg")
    GITHUB_REPOS  - Comma-separated list of specific repos to check (e.g. "owner/repo1,owner/repo2")
                    If set, only these repos are checked (overrides user/org discovery)
    REPORT_PATH   - Path to the markdown report file (default: commit_reports/github_commits.md)
"""

import os
import sys
import json
import argparse
from datetime import datetime, timezone, timedelta
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode


GITHUB_API = "https://api.github.com"
WINDOW_HOURS = 6


def gh_get(path, token, params=None):
    url = f"{GITHUB_API}{path}"
    if params:
        url += "?" + urlencode(params)
    req = Request(url, headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    })
    try:
        with urlopen(req) as resp:
            return json.loads(resp.read())
    except HTTPError as e:
        body = e.read().decode()
        print(f"  [warn] GitHub API {path} returned {e.code}: {body[:200]}", file=sys.stderr)
        return None


def paginate(path, token, params=None):
    params = dict(params or {})
    params.setdefault("per_page", 100)
    page = 1
    results = []
    while True:
        params["page"] = page
        data = gh_get(path, token, params)
        if not data:
            break
        if isinstance(data, list):
            results.extend(data)
            if len(data) < params["per_page"]:
                break
        else:
            # Some endpoints wrap results
            items = data.get("items") or data.get("repositories") or []
            results.extend(items)
            if len(items) < params["per_page"]:
                break
        page += 1
    return results


def get_repos_to_check(token):
    explicit = os.environ.get("GITHUB_REPOS", "").strip()
    if explicit:
        return [r.strip() for r in explicit.split(",") if r.strip()]

    repos = set()

    # User's own repos
    for repo in paginate("/user/repos", token, {"affiliation": "owner,collaborator,organization_member", "sort": "pushed"}):
        if not repo.get("archived"):
            repos.add(repo["full_name"])

    # Extra orgs
    orgs_env = os.environ.get("GITHUB_ORGS", "").strip()
    if orgs_env:
        for org in orgs_env.split(","):
            org = org.strip()
            if not org:
                continue
            for repo in paginate(f"/orgs/{org}/repos", token, {"type": "all"}):
                if not repo.get("archived"):
                    repos.add(repo["full_name"])

    return sorted(repos)


def get_commits_since(full_name, token, since_iso):
    owner, repo = full_name.split("/", 1)
    commits = paginate(
        f"/repos/{owner}/{repo}/commits",
        token,
        {"since": since_iso},
    )
    if commits is None:
        return []
    return commits


def build_report_section(since, until, repo_data):
    lines = []
    total = sum(len(c) for c in repo_data.values())
    lines.append(f"## Commit Report: {since.strftime('%Y-%m-%d %H:%M')} → {until.strftime('%Y-%m-%d %H:%M')} UTC")
    lines.append(f"\n**Total commits:** {total}  ")
    lines.append(f"**Repos with activity:** {sum(1 for c in repo_data.values() if c)}  ")
    lines.append(f"**Repos checked:** {len(repo_data)}  \n")

    active = [(repo, commits) for repo, commits in repo_data.items() if commits]
    if not active:
        lines.append("_No commits found in this window._\n")
    else:
        lines.append("| Repository | Commits |")
        lines.append("|------------|---------|")
        for repo, commits in sorted(active, key=lambda x: -len(x[1])):
            lines.append(f"| `{repo}` | {len(commits)} |")
        lines.append("")

        # Detailed breakdown
        lines.append("### Details\n")
        for repo, commits in sorted(active, key=lambda x: -len(x[1])):
            lines.append(f"#### `{repo}` ({len(commits)} commit{'s' if len(commits) != 1 else ''})\n")
            for commit in commits[:20]:  # cap at 20 per repo to keep file manageable
                sha = commit.get("sha", "")[:7]
                msg = (commit.get("commit", {}).get("message") or "").splitlines()[0][:80]
                author = (commit.get("commit", {}).get("author") or {}).get("name", "unknown")
                date = (commit.get("commit", {}).get("author") or {}).get("date", "")[:16].replace("T", " ")
                lines.append(f"- `{sha}` {msg} _(by {author} at {date})_")
            if len(commits) > 20:
                lines.append(f"- _...and {len(commits) - 20} more_")
            lines.append("")

    lines.append("---\n")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Track GitHub commits from the last 6 hours")
    parser.add_argument("--output", default=os.environ.get("REPORT_PATH", "commit_reports/github_commits.md"))
    args = parser.parse_args()

    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("Error: GITHUB_TOKEN environment variable is not set.", file=sys.stderr)
        sys.exit(1)

    until = datetime.now(timezone.utc)
    since = until - timedelta(hours=WINDOW_HOURS)
    since_iso = since.strftime("%Y-%m-%dT%H:%M:%SZ")

    print(f"Checking commits from {since_iso} to now...")

    repos = get_repos_to_check(token)
    print(f"Found {len(repos)} repos to check.")

    repo_data = {}
    for full_name in repos:
        print(f"  {full_name} ...", end=" ", flush=True)
        commits = get_commits_since(full_name, token, since_iso)
        repo_data[full_name] = commits
        print(f"{len(commits)} commit(s)")

    section = build_report_section(since, until, repo_data)

    output_path = args.output
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)

    # Prepend new section to keep latest at top
    existing = ""
    if os.path.exists(output_path):
        with open(output_path, "r") as f:
            existing = f.read()

    header = "# GitHub Commit Tracker\n\n" if not existing else ""
    with open(output_path, "w") as f:
        if header:
            f.write(header)
        f.write(section)
        if existing:
            # Strip old header if present so we don't duplicate it
            content = existing.removeprefix("# GitHub Commit Tracker\n\n")
            f.write(content)

    total = sum(len(c) for c in repo_data.values())
    print(f"\nDone. {total} commit(s) across {sum(1 for c in repo_data.values() if c)} repo(s) written to {output_path}")


if __name__ == "__main__":
    main()

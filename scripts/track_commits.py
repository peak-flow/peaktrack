#!/usr/bin/env python3
"""Fetch commits made in the last 6 hours across all accessible repos and write a markdown report."""

import os
import sys
import json
from datetime import datetime, timezone, timedelta
from urllib.request import Request, urlopen
from urllib.error import HTTPError


def gh_request(token, path, params=None):
    url = f"https://api.github.com{path}"
    if params:
        url += "?" + "&".join(f"{k}={v}" for k, v in params.items())
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
        print(f"GitHub API error {e.code} for {url}: {body}", file=sys.stderr)
        return None


def paginate(token, path, params=None):
    """Yield all items across pages."""
    page = 1
    while True:
        p = dict(params or {})
        p["per_page"] = "100"
        p["page"] = str(page)
        data = gh_request(token, path, p)
        if not data:
            break
        yield from data
        if len(data) < 100:
            break
        page += 1


def get_repos(token, org):
    """Return list of repo full_names for an org."""
    repos = []
    for r in paginate(token, f"/orgs/{org}/repos", {"type": "all"}):
        repos.append(r["full_name"])
    return repos


def get_commits_since(token, owner, repo, since_iso):
    commits = []
    for c in paginate(token, f"/repos/{owner}/{repo}/commits", {"since": since_iso}):
        commits.append({
            "sha": c["sha"][:7],
            "message": (c["commit"]["message"].split("\n")[0])[:80],
            "author": c["commit"]["author"]["name"],
            "date": c["commit"]["author"]["date"],
            "url": c["html_url"],
        })
    return commits


def build_report_section(window_start, window_end, results):
    lines = []
    total = sum(len(v) for v in results.values())
    lines.append(f"\n## {window_start.strftime('%Y-%m-%d %H:%M')} – {window_end.strftime('%H:%M')} UTC\n")
    lines.append(f"**Total commits:** {total}\n")

    active = {repo: commits for repo, commits in results.items() if commits}
    if not active:
        lines.append("_No commits in this window._\n")
        return "\n".join(lines)

    for repo, commits in sorted(active.items()):
        lines.append(f"\n### {repo} ({len(commits)} commit{'s' if len(commits) != 1 else ''})\n")
        for c in commits:
            lines.append(f"- [`{c['sha']}`]({c['url']}) {c['message']} — _{c['author']}_")

    return "\n".join(lines)


def main():
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        print("Error: GH_TOKEN or GITHUB_TOKEN environment variable required.", file=sys.stderr)
        sys.exit(1)

    org = os.environ.get("GH_ORG", "peak-flow")
    report_dir = os.environ.get("REPORT_DIR", "commit-reports")
    os.makedirs(report_dir, exist_ok=True)

    now = datetime.now(timezone.utc)
    window_start = now - timedelta(hours=6)
    since_iso = window_start.strftime("%Y-%m-%dT%H:%M:%SZ")

    print(f"Checking commits since {since_iso} in org '{org}'...")

    repos = get_repos(token, org)
    if not repos:
        # Fallback: just check the current repo via GITHUB_REPOSITORY
        repo_env = os.environ.get("GITHUB_REPOSITORY", "")
        if repo_env:
            repos = [repo_env]

    print(f"Found {len(repos)} repo(s): {', '.join(repos)}")

    results = {}
    for full_name in repos:
        owner, repo = full_name.split("/", 1)
        commits = get_commits_since(token, owner, repo, since_iso)
        results[full_name] = commits
        print(f"  {full_name}: {len(commits)} commit(s)")

    section = build_report_section(window_start, now, results)

    date_str = now.strftime("%Y-%m-%d")
    report_path = os.path.join(report_dir, f"{date_str}.md")

    # Create or append
    if not os.path.exists(report_path):
        header = f"# Commit Activity — {date_str}\n"
        with open(report_path, "w") as f:
            f.write(header)

    with open(report_path, "a") as f:
        f.write(section + "\n")

    print(f"\nReport written to {report_path}")


if __name__ == "__main__":
    main()

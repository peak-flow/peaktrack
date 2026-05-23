#!/usr/bin/env python3
"""
Count GitHub commits made in the last 6 hours across repos and append results to COMMIT_LOG.md.
Requires: GITHUB_TOKEN env var, optionally GITHUB_ORG or GITHUB_USER.
"""

import os
import sys
import json
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_ORG = os.environ.get("GITHUB_ORG", "peak-flow")
GITHUB_USER = os.environ.get("GITHUB_USER", "")
OUTPUT_FILE = os.environ.get("COMMIT_LOG_FILE", "COMMIT_LOG.md")
HOURS_BACK = int(os.environ.get("HOURS_BACK", "6"))


def gh_get(path, params=None):
    url = f"https://api.github.com{path}"
    if params:
        qs = "&".join(f"{k}={v}" for k, v in params.items())
        url = f"{url}?{qs}"
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"  HTTP {e.code} for {url}: {body[:200]}", file=sys.stderr)
        return None


def get_all_pages(path, params=None):
    params = dict(params or {})
    params.setdefault("per_page", "100")
    page = 1
    results = []
    while True:
        params["page"] = str(page)
        data = gh_get(path, params)
        if not data:
            break
        results.extend(data)
        if len(data) < int(params["per_page"]):
            break
        page += 1
    return results


def list_repos():
    if GITHUB_ORG:
        return get_all_pages(f"/orgs/{GITHUB_ORG}/repos", {"type": "all", "sort": "pushed"})
    elif GITHUB_USER:
        return get_all_pages(f"/users/{GITHUB_USER}/repos", {"type": "owner", "sort": "pushed"})
    else:
        return get_all_pages("/user/repos", {"affiliation": "owner,organization_member", "sort": "pushed"})


def count_commits_since(owner, repo, since_iso):
    commits = get_all_pages(
        f"/repos/{owner}/{repo}/commits",
        {"since": since_iso},
    )
    if commits is None:
        return 0, []
    authors = {}
    for c in commits:
        login = (c.get("author") or {}).get("login") or (c.get("commit", {}).get("author") or {}).get("name", "unknown")
        authors[login] = authors.get(login, 0) + 1
    return len(commits), authors


def main():
    if not GITHUB_TOKEN:
        print("ERROR: GITHUB_TOKEN is not set.", file=sys.stderr)
        sys.exit(1)

    now = datetime.now(timezone.utc)
    since = now - timedelta(hours=HOURS_BACK)
    since_iso = since.strftime("%Y-%m-%dT%H:%M:%SZ")
    window_label = f"{since.strftime('%Y-%m-%d %H:%M')} UTC — {now.strftime('%Y-%m-%d %H:%M')} UTC"

    print(f"Scanning repos for commits since {since_iso} ...")
    repos = list_repos()
    print(f"Found {len(repos)} repos.")

    repo_stats = []
    total = 0

    for repo in repos:
        full_name = repo.get("full_name", "")
        owner, name = full_name.split("/", 1)
        pushed_at = repo.get("pushed_at") or ""

        # Skip repos with no pushes in the window
        if pushed_at and pushed_at < since_iso:
            continue

        count, authors = count_commits_since(owner, name, since_iso)
        if count > 0:
            repo_stats.append((full_name, count, authors))
            total += count
            print(f"  {full_name}: {count} commit(s)")

    # Build markdown section
    lines = [
        f"## {now.strftime('%Y-%m-%d %H:%M')} UTC — {HOURS_BACK}-hour snapshot",
        "",
        f"**Window:** {window_label}  ",
        f"**Total commits:** {total}  ",
        "",
    ]

    if repo_stats:
        lines.append("| Repository | Commits | Top contributors |")
        lines.append("|---|---|---|")
        for full_name, count, authors in sorted(repo_stats, key=lambda x: -x[1]):
            top = ", ".join(f"{login} ({n})" for login, n in sorted(authors.items(), key=lambda x: -x[1])[:5])
            lines.append(f"| `{full_name}` | {count} | {top} |")
    else:
        lines.append("_No commits found in this window._")

    lines.append("")
    lines.append("---")
    lines.append("")

    section = "\n".join(lines)

    # Prepend to file (newest first)
    existing = ""
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "r") as f:
            existing = f.read()

    header = "# GitHub Commit Log\n\n"
    if existing.startswith(header):
        body = existing[len(header):]
    else:
        body = existing

    with open(OUTPUT_FILE, "w") as f:
        f.write(header + section + body)

    print(f"\nWrote results to {OUTPUT_FILE} ({total} total commits across {len(repo_stats)} repos).")


if __name__ == "__main__":
    main()

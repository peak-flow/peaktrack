#!/usr/bin/env python3
"""
Track GitHub commits across all repos for a user in the last N hours.
Appends a summary entry to a markdown log file.

Usage:
    GITHUB_TOKEN=ghp_xxx python3 track_commits.py
    python3 track_commits.py --hours 6 --output /path/to/log.md --user peak-flow
"""

import argparse
import os
import sys
import json
from datetime import datetime, timezone, timedelta
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError

GITHUB_API = "https://api.github.com"


def gh_get(path: str, token: str) -> list | dict:
    url = f"{GITHUB_API}{path}"
    req = Request(url, headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    })
    with urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def paginate(path: str, token: str, per_page: int = 100) -> list:
    results = []
    page = 1
    while True:
        sep = "&" if "?" in path else "?"
        chunk = gh_get(f"{path}{sep}per_page={per_page}&page={page}", token)
        if not chunk:
            break
        results.extend(chunk)
        if len(chunk) < per_page:
            break
        page += 1
    return results


def get_repos(user: str, token: str) -> list[dict]:
    repos = paginate(f"/users/{user}/repos?type=all&sort=pushed", token)
    # also include org repos where user is a member
    try:
        orgs = paginate(f"/user/orgs", token)
        for org in orgs:
            org_repos = paginate(f"/orgs/{org['login']}/repos?type=all&sort=pushed", token)
            # avoid duplicates
            existing = {r["full_name"] for r in repos}
            repos.extend(r for r in org_repos if r["full_name"] not in existing)
    except Exception:
        pass
    return repos


def count_commits_since(repo_full_name: str, since_iso: str, token: str) -> int:
    owner, repo = repo_full_name.split("/", 1)
    try:
        commits = paginate(
            f"/repos/{owner}/{repo}/commits?since={since_iso}",
            token,
        )
        return len(commits)
    except HTTPError as e:
        if e.code in (409, 404, 403):
            return 0
        raise


def build_markdown_entry(
    user: str,
    hours: int,
    since: datetime,
    now: datetime,
    repo_counts: dict[str, int],
) -> str:
    total = sum(repo_counts.values())
    active = {r: c for r, c in repo_counts.items() if c > 0}

    lines = [
        f"## {now.strftime('%Y-%m-%d %H:%M UTC')} — last {hours}h snapshot",
        "",
        f"**User:** `{user}`  ",
        f"**Window:** {since.strftime('%Y-%m-%d %H:%M UTC')} → {now.strftime('%Y-%m-%d %H:%M UTC')}  ",
        f"**Total commits:** {total}  ",
        f"**Active repos:** {len(active)} / {len(repo_counts)}",
        "",
    ]

    if active:
        lines.append("| Repository | Commits |")
        lines.append("|---|---|")
        for repo, count in sorted(active.items(), key=lambda x: -x[1]):
            lines.append(f"| `{repo}` | {count} |")
    else:
        lines.append("_No commits in this window._")

    lines.append("")
    lines.append("---")
    lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Track GitHub commits to a markdown log.")
    parser.add_argument("--hours", type=int, default=6, help="Look-back window in hours (default: 6)")
    parser.add_argument("--user", default="peak-flow", help="GitHub username")
    parser.add_argument(
        "--output",
        default=os.path.join(os.path.dirname(__file__), "..", "commit_log.md"),
        help="Path to the output markdown file",
    )
    args = parser.parse_args()

    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        print("ERROR: GITHUB_TOKEN environment variable is not set.", file=sys.stderr)
        sys.exit(1)

    now = datetime.now(timezone.utc)
    since = now - timedelta(hours=args.hours)
    since_iso = since.strftime("%Y-%m-%dT%H:%M:%SZ")

    print(f"Fetching repos for {args.user}…")
    repos = get_repos(args.user, token)
    print(f"Found {len(repos)} repos. Checking commits since {since_iso}…")

    repo_counts: dict[str, int] = {}
    for i, repo in enumerate(repos, 1):
        name = repo["full_name"]
        # skip archived repos that haven't been pushed to recently to save API calls
        pushed_at = repo.get("pushed_at") or ""
        if pushed_at and pushed_at < since_iso:
            repo_counts[name] = 0
            continue
        count = count_commits_since(name, since_iso, token)
        repo_counts[name] = count
        if count:
            print(f"  [{i}/{len(repos)}] {name}: {count} commit(s)")

    entry = build_markdown_entry(args.user, args.hours, since, now, repo_counts)

    output_path = os.path.realpath(args.output)
    # prepend header if file is new
    if not os.path.exists(output_path):
        header = (
            f"# GitHub Commit Log — `{args.user}`\n\n"
            f"Auto-generated every {args.hours} hours. Most recent entry first.\n\n"
            "---\n\n"
        )
        with open(output_path, "w") as f:
            f.write(header)

    # read existing content then prepend new entry (most recent first)
    with open(output_path, "r") as f:
        existing = f.read()

    # insert after the file header (first --- separator)
    insert_after = existing.find("\n\n---\n\n")
    if insert_after != -1:
        updated = existing[: insert_after + 7] + entry + existing[insert_after + 7 :]
    else:
        updated = existing + entry

    with open(output_path, "w") as f:
        f.write(updated)

    total = sum(repo_counts.values())
    active_count = sum(1 for c in repo_counts.values() if c > 0)
    print(f"\nDone. {total} total commits across {active_count} repos. Log: {output_path}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Fetch commits from the last 6 hours across the peak-flow org and
append a formatted report to commit-log.md."""

import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

ORG = "peak-flow"
LOG_FILE = "commit-log.md"
HOURS = 6


def gh_get(url: str, token: str) -> dict:
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    req.add_header("User-Agent", "peak-flow-commit-tracker/1.0")
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        print(f"HTTP {e.code} from GitHub: {body}", file=sys.stderr)
        sys.exit(1)


def fetch_commits(token: str, since: str) -> tuple[list, int]:
    """Return (items, total_count) for all commits since ISO timestamp."""
    items: list = []
    page = 1
    total_count = 0
    while True:
        url = (
            f"https://api.github.com/search/commits"
            f"?q=org:{ORG}+committer-date:>={since}"
            f"&sort=committer-date&order=desc&per_page=100&page={page}"
        )
        data = gh_get(url, token)
        total_count = data.get("total_count", 0)
        batch = data.get("items", [])
        items.extend(batch)
        if len(batch) < 100 or len(items) >= min(total_count, 1000):
            break
        page += 1
        time.sleep(1)  # stay well within rate limits
    return items, total_count


def build_section(items: list, total_count: int, since: str, now: datetime) -> str:
    now_str = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    now_display = now.strftime("%Y-%m-%d %H:%M UTC")

    # Group by repo
    repo_counts: dict[str, int] = {}
    repo_commits: dict[str, list] = {}
    for item in items:
        repo = item["repository"]["full_name"]
        repo_counts.setdefault(repo, 0)
        repo_commits.setdefault(repo, [])
        repo_counts[repo] += 1
        msg = item["commit"]["message"].split("\n")[0][:80]
        repo_commits[repo].append(
            {
                "sha": item["sha"][:7],
                "message": msg,
                "author": item["commit"]["author"]["name"],
                "date": item["commit"]["author"]["date"],
                "url": item["html_url"],
            }
        )

    sorted_repos = sorted(repo_counts.items(), key=lambda x: x[1], reverse=True)

    lines: list[str] = []
    lines.append(f"## {now_display} — {HOURS}-Hour Commit Report")
    lines.append("")
    lines.append(f"**Period:** `{since}` → `{now_str}`  ")
    lines.append(f"**Total commits:** {total_count}  ")
    lines.append(f"**Active repos:** {len(sorted_repos)}")
    lines.append("")

    if sorted_repos:
        lines.append("### Commits by Repository")
        lines.append("")
        lines.append("| Repository | Commits |")
        lines.append("| --- | ---: |")
        for repo, count in sorted_repos:
            lines.append(f"| [{repo}](https://github.com/{repo}) | {count} |")
        lines.append("")

        lines.append("### Commit Details")
        lines.append("")
        for repo, count in sorted_repos:
            plural = "s" if count != 1 else ""
            lines.append(
                f"**[{repo}](https://github.com/{repo})**"
                f" — {count} commit{plural}"
            )
            lines.append("")
            for c in repo_commits[repo]:
                lines.append(
                    f"- [`{c['sha']}`]({c['url']}) {c['message']}  "
                    f"— *{c['author']}* `{c['date']}`"
                )
            lines.append("")
    else:
        lines.append("_No commits found in this period._")
        lines.append("")

    lines.append("---")
    lines.append("")
    return "\n".join(lines)


def update_log(section: str) -> None:
    header = (
        f"# Commit Activity Log\n\n"
        f"Auto-updated every {HOURS} hours by GitHub Actions.  \n"
        f"Tracking commits across the `{ORG}` GitHub organization.\n\n"
        f"---\n"
    )
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE) as f:
            existing = f.read()
        # Insert new section right after the first --- separator
        sep = "\n---\n"
        idx = existing.find(sep)
        if idx != -1:
            before = existing[: idx + len(sep)]
            after = existing[idx + len(sep) :]
            content = before + "\n" + section + after
        else:
            content = existing + "\n" + section
    else:
        content = header + "\n" + section

    with open(LOG_FILE, "w") as f:
        f.write(content)


def main() -> None:
    # Prefer a PAT (includes private repos) over GITHUB_TOKEN (public only)
    token = os.environ.get("GH_PAT") or os.environ.get("GITHUB_TOKEN")
    if not token:
        print("Neither GH_PAT nor GITHUB_TOKEN is set.", file=sys.stderr)
        sys.exit(1)

    now = datetime.now(timezone.utc)
    since = (now - timedelta(hours=HOURS)).strftime("%Y-%m-%dT%H:%M:%SZ")

    print(f"Fetching {ORG} commits since {since} ...")
    items, total_count = fetch_commits(token, since)
    print(f"Found {total_count} commits (fetched {len(items)})")

    section = build_section(items, total_count, since, now)
    update_log(section)
    print(f"Updated {LOG_FILE}")


if __name__ == "__main__":
    main()

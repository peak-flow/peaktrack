#!/usr/bin/env python3
"""
GitHub Commit Tracker
Checks all accessible repos for commits made in the last 6 hours
and appends a summary to a markdown log file.

Requirements:
  - GITHUB_TOKEN env var set to a personal access token (repo scope)
  - Python 3.7+, standard library only

Usage:
  python3 scripts/github_commit_tracker.py
  python3 scripts/github_commit_tracker.py --hours 6 --output commit_log.md
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone


API_BASE = "https://api.github.com"
DEFAULT_OUTPUT = "commit_log.md"
DEFAULT_HOURS = 6


# ---------------------------------------------------------------------------
# GitHub API helpers
# ---------------------------------------------------------------------------

def gh_get(path: str, token: str) -> list | dict:
    """Fetch all pages of a GitHub API endpoint and return combined results."""
    results = []
    url = f"{API_BASE}{path}" if not path.startswith("http") else path
    while url:
        req = urllib.request.Request(url)
        req.add_header("Authorization", f"Bearer {token}")
        req.add_header("Accept", "application/vnd.github+json")
        req.add_header("X-GitHub-Api-Version", "2022-11-28")
        try:
            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read())
                # Some endpoints return a dict (e.g. /user)
                if isinstance(data, dict):
                    return data
                results.extend(data)
                # Follow Link: <url>; rel="next" pagination
                link_header = resp.headers.get("Link", "")
                url = _parse_next_link(link_header)
        except urllib.error.HTTPError as exc:
            body = exc.read().decode(errors="replace")
            print(f"  [warn] HTTP {exc.code} for {url}: {body[:200]}", file=sys.stderr)
            return results
    return results


def _parse_next_link(link_header: str) -> str | None:
    """Return the 'next' URL from a GitHub Link header, or None."""
    for part in link_header.split(","):
        part = part.strip()
        if 'rel="next"' in part:
            url_part = part.split(";")[0].strip()
            if url_part.startswith("<") and url_part.endswith(">"):
                return url_part[1:-1]
    return None


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def fetch_repos(token: str) -> list[dict]:
    """Return all repos the authenticated user can access."""
    repos = gh_get("/user/repos?per_page=100&sort=pushed&affiliation=owner,collaborator,organization_member", token)
    return repos if isinstance(repos, list) else []


def fetch_commits_since(owner: str, repo: str, since: datetime, token: str) -> list[dict]:
    """Return commits pushed to *any* branch after `since`."""
    since_iso = since.strftime("%Y-%m-%dT%H:%M:%SZ")
    path = f"/repos/{owner}/{repo}/commits?per_page=100&since={since_iso}"
    commits = gh_get(path, token)
    return commits if isinstance(commits, list) else []


def gather_report(token: str, hours: int) -> dict:
    """
    Collect commit counts per repo for the last `hours` hours.

    Returns:
        {
          "generated_at": <ISO string>,
          "window_hours": <int>,
          "since": <ISO string>,
          "total_commits": <int>,
          "repos": [
            {"full_name": ..., "commits": <int>, "url": ...},
            ...
          ]
        }
    """
    now = datetime.now(timezone.utc)
    since = now - timedelta(hours=hours)

    print(f"Checking commits since {since.strftime('%Y-%m-%d %H:%M UTC')} ({hours}h window)…")

    repos = fetch_repos(token)
    print(f"Found {len(repos)} accessible repos.")

    active_repos = []
    total = 0
    for repo in repos:
        full_name = repo.get("full_name", "")
        owner, name = full_name.split("/", 1)
        commits = fetch_commits_since(owner, name, since, token)
        count = len(commits)
        if count > 0:
            active_repos.append({
                "full_name": full_name,
                "commits": count,
                "url": repo.get("html_url", f"https://github.com/{full_name}"),
            })
            total += count
            print(f"  {full_name}: {count} commit(s)")

    active_repos.sort(key=lambda r: r["commits"], reverse=True)

    return {
        "generated_at": now.isoformat(),
        "window_hours": hours,
        "since": since.isoformat(),
        "total_commits": total,
        "repos": active_repos,
    }


# ---------------------------------------------------------------------------
# Markdown rendering
# ---------------------------------------------------------------------------

def render_markdown(report: dict) -> str:
    generated = report["generated_at"][:19].replace("T", " ") + " UTC"
    since = report["since"][:19].replace("T", " ") + " UTC"
    hours = report["window_hours"]
    total = report["total_commits"]
    repos = report["repos"]

    lines = [
        f"## {generated}  —  last {hours}h summary",
        "",
        f"- **Window:** {since} → {generated}",
        f"- **Total commits:** {total}",
        f"- **Active repos:** {len(repos)}",
        "",
    ]

    if repos:
        lines += [
            "| Repository | Commits |",
            "|------------|--------:|",
        ]
        for r in repos:
            name = r["full_name"]
            url = r["url"]
            count = r["commits"]
            lines.append(f"| [{name}]({url}) | {count} |")
    else:
        lines.append("_No commits found in this window._")

    lines += ["", "---", ""]
    return "\n".join(lines)


def append_to_log(output_path: str, markdown: str) -> None:
    """Prepend the new entry to the top of the log file (newest first)."""
    header = (
        "# GitHub Commit Log\n\n"
        "Auto-generated every 6 hours. Newest entries at the top.\n\n"
    )

    existing = ""
    if os.path.exists(output_path):
        with open(output_path, "r", encoding="utf-8") as fh:
            existing = fh.read()
        # Strip the static header if present so we don't duplicate it
        if existing.startswith("# GitHub Commit Log"):
            # Remove first header block (up to first '---')
            idx = existing.find("\n---\n")
            if idx != -1:
                existing = existing[idx + 4 :]  # keep everything after first divider

    with open(output_path, "w", encoding="utf-8") as fh:
        fh.write(header)
        fh.write(markdown)
        fh.write(existing)

    print(f"Log updated: {output_path}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Track GitHub commits over a time window.")
    parser.add_argument("--hours", type=int, default=DEFAULT_HOURS,
                        help=f"Look-back window in hours (default: {DEFAULT_HOURS})")
    parser.add_argument("--output", default=DEFAULT_OUTPUT,
                        help=f"Path to the markdown log file (default: {DEFAULT_OUTPUT})")
    args = parser.parse_args()

    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        print("Error: GITHUB_TOKEN environment variable is not set.", file=sys.stderr)
        print("  Create a personal access token with 'repo' scope at:", file=sys.stderr)
        print("  https://github.com/settings/tokens", file=sys.stderr)
        sys.exit(1)

    report = gather_report(token, args.hours)
    md = render_markdown(report)
    append_to_log(args.output, md)

    print(f"\nDone. {report['total_commits']} total commit(s) across "
          f"{len(report['repos'])} repo(s) in the last {args.hours}h.")


if __name__ == "__main__":
    main()

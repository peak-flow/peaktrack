#!/usr/bin/env python3
"""Fetch commits from peak-flow/peaktrack made in the last 6 hours and append to commit-log.md."""

import json
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta

REPOS = ["peak-flow/peaktrack"]
LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "commit-log.md")
HOURS = 6


def github_get(url, token=None):
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "peaktrack-commit-logger/1.0")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def fetch_commits(owner, repo, since_iso, token=None):
    url = f"https://api.github.com/repos/{owner}/{repo}/commits?since={since_iso}&per_page=100"
    try:
        return github_get(url, token)
    except urllib.error.HTTPError as e:
        if e.code == 429 or e.code == 403:
            print(
                f"Rate limited ({e.code}) fetching {owner}/{repo}. "
                "Set GITHUB_TOKEN env var to increase limits.",
                file=sys.stderr,
            )
        else:
            print(f"HTTP {e.code} fetching {owner}/{repo}: {e.reason}", file=sys.stderr)
        return None  # None = error, distinct from [] = no commits
    except Exception as e:
        print(f"Error fetching {owner}/{repo}: {e}", file=sys.stderr)
        return None


def main():
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    now = datetime.now(timezone.utc)
    since = now - timedelta(hours=HOURS)
    since_iso = since.strftime("%Y-%m-%dT%H:%M:%SZ")
    now_str = now.strftime("%Y-%m-%d %H:%M UTC")

    # Build the new markdown section
    lines = []

    total_across_repos = 0
    repo_sections = []

    for repo_full in REPOS:
        owner, repo = repo_full.split("/")
        commits = fetch_commits(owner, repo, since_iso, token)
        if commits is None:
            repo_sections.append((repo_full, None, []))
            continue

        count = len(commits)
        total_across_repos += count

        bullets = []
        for c in commits:
            sha = c.get("sha", "")[:7]
            msg = (c.get("commit", {}).get("message", "") or "").splitlines()[0]
            author = (
                c.get("commit", {}).get("author", {}).get("name", "")
                or c.get("author", {}).get("login", "unknown")
            )
            ts = c.get("commit", {}).get("author", {}).get("date", "")
            bullets.append(f"- `{sha}` **{author}** — {msg} _{ts}_")

        repo_sections.append((repo_full, count, bullets))

    # Section heading
    lines.append(f"\n## {now_str} — last {HOURS}h check\n")

    # Summary table
    lines.append("| Repository | Commits |")
    lines.append("|---|---|")
    for repo_full, count, _ in repo_sections:
        lines.append(f"| `{repo_full}` | {count} |")
    lines.append(f"| **Total** | **{total_across_repos}** |")
    lines.append("")

    # Commit details
    for repo_full, count, bullets in repo_sections:
        if count is None:
            lines.append(f"_Error fetching `{repo_full}` — check GITHUB_TOKEN and logs._\n")
        elif count == 0:
            lines.append(f"_No commits in `{repo_full}` in the last {HOURS} hours._\n")
        else:
            lines.append(f"### {repo_full}\n")
            lines.extend(bullets)
            lines.append("")

    section = "\n".join(lines)

    # Write or append to log file
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, "w") as f:
            f.write("# GitHub Commit Log\n")
            f.write(f"\n_Tracking: {', '.join(f'`{r}`' for r in REPOS)} — checked every {HOURS}h_\n")
            f.write(section)
    else:
        with open(LOG_FILE, "a") as f:
            f.write(section)

    print(f"[{now_str}] Logged {total_across_repos} commit(s) across {len(REPOS)} repo(s) → {LOG_FILE}")


if __name__ == "__main__":
    main()

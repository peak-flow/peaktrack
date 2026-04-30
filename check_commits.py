#!/usr/bin/env python3
"""
Fetches commits made in the last 6 hours for peak-flow/peaktrack
and appends a summary entry to commit-activity.md.
"""

import json
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta

REPO = "peak-flow/peaktrack"
OUTPUT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "commit-activity.md")
WINDOW_HOURS = 6

def get_token():
    # 1. Environment variable
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if token:
        return token
    # 2. .env file next to this script
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line.startswith("GITHUB_TOKEN="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None

def fetch_commits(token, repo, since_iso):
    url = f"https://api.github.com/repos/{repo}/commits?since={since_iso}&per_page=100"
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        print(f"GitHub API error {e.code}: {e.reason}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"Request failed: {e}", file=sys.stderr)
        return None

def short_sha(sha):
    return sha[:7] if sha else "unknown"

def build_entry(now, commits, repo):
    timestamp = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    lines = [f"## Check: {timestamp}\n"]

    if commits is None:
        lines.append(f"| Repo | Commits in Last {WINDOW_HOURS}h |\n")
        lines.append("|------|-------------------|\n")
        lines.append(f"| {repo} | API error — check token/connectivity |\n\n---\n")
        return "".join(lines)

    count = len(commits)
    lines.append(f"| Repo | Commits in Last {WINDOW_HOURS}h |\n")
    lines.append("|------|-------------------|\n")

    if count == 0:
        lines.append(f"| {repo} | No commits in this period. |\n\n---\n")
        return "".join(lines)

    lines.append(f"| {repo} | {count} |\n\n")
    lines.append(f"### {repo}\n")
    for c in commits[:20]:
        sha = short_sha(c.get("sha", ""))
        author = (
            (c.get("commit", {}).get("author") or {}).get("name")
            or (c.get("author") or {}).get("login")
            or "unknown"
        )
        message = (c.get("commit", {}).get("message") or "").split("\n")[0]
        lines.append(f"- `{sha}` — {author} — {message}\n")
    if count > 20:
        lines.append(f"- _…and {count - 20} more_\n")
    lines.append("\n---\n")
    return "".join(lines)

def main():
    token = get_token()
    if not token:
        print(
            "Warning: no GITHUB_TOKEN found. Set it in the .env file or as an "
            "environment variable. Unauthenticated requests are rate-limited to 60/hour.",
            file=sys.stderr,
        )

    now = datetime.now(timezone.utc)
    since = now - timedelta(hours=WINDOW_HOURS)
    since_iso = since.strftime("%Y-%m-%dT%H:%M:%SZ")

    commits = fetch_commits(token, REPO, since_iso)
    entry = build_entry(now, commits, REPO)

    with open(OUTPUT_FILE, "a") as f:
        f.write(entry)

    count = len(commits) if commits is not None else 0
    print(f"[{now.strftime('%Y-%m-%dT%H:%M:%SZ')}] {REPO}: {count} commit(s) in last {WINDOW_HOURS}h → {OUTPUT_FILE}")

if __name__ == "__main__":
    main()

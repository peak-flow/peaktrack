#!/usr/bin/env python3
"""
GitHub commit tracker — counts commits in the last 6 hours across repos
and appends a summary to commit_reports/report.md.
"""

import os
import json
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config.json")
REPORT_FILE = os.path.join(os.path.dirname(__file__), "..", "commit_reports", "report.md")
API_BASE = "https://api.github.com"
WINDOW_HOURS = 6


def load_config():
    if not os.path.exists(CONFIG_FILE):
        raise FileNotFoundError(
            f"Config file not found: {CONFIG_FILE}\n"
            "Copy scripts/config.example.json to scripts/config.json and fill it in."
        )
    with open(CONFIG_FILE) as f:
        return json.load(f)


def gh_get(path, token):
    url = f"{API_BASE}{path}"
    req = urllib.request.Request(url, headers={
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "peaktrack-commit-tracker",
    })
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        raise RuntimeError(f"GitHub API error {e.code} for {url}: {body}")


def get_repos(config, token):
    """Return list of {owner, repo} dicts to check."""
    repos = []

    for entry in config.get("repos", []):
        # explicit "owner/repo" strings
        owner, _, name = entry.partition("/")
        repos.append({"owner": owner, "repo": name})

    for org in config.get("orgs", []):
        page = 1
        while True:
            data = gh_get(f"/orgs/{org}/repos?per_page=100&page={page}", token)
            if not data:
                break
            for r in data:
                repos.append({"owner": org, "repo": r["name"]})
            page += 1
            if len(data) < 100:
                break

    for user in config.get("users", []):
        page = 1
        while True:
            data = gh_get(f"/users/{user}/repos?per_page=100&page={page}", token)
            if not data:
                break
            for r in data:
                repos.append({"owner": user, "repo": r["name"]})
            page += 1
            if len(data) < 100:
                break

    return repos


def count_commits(owner, repo, since_iso, token):
    """Return commit count for a repo since the given ISO timestamp."""
    total = 0
    page = 1
    while True:
        path = f"/repos/{owner}/{repo}/commits?since={since_iso}&per_page=100&page={page}"
        try:
            data = gh_get(path, token)
        except RuntimeError:
            return None  # repo may be empty or inaccessible
        total += len(data)
        if len(data) < 100:
            break
        page += 1
    return total


def build_report(results, window_start, window_end):
    lines = []
    total = sum(c for _, c in results if c is not None)
    lines.append(f"## {window_end.strftime('%Y-%m-%d %H:%M UTC')} — last {WINDOW_HOURS}h commit report")
    lines.append(f"**Window:** {window_start.strftime('%Y-%m-%d %H:%M UTC')} → {window_end.strftime('%Y-%m-%d %H:%M UTC')}")
    lines.append(f"**Total commits:** {total}")
    lines.append("")
    lines.append("| Repository | Commits |")
    lines.append("|-----------|---------|")
    for repo_full, count in sorted(results, key=lambda x: -(x[1] or 0)):
        display = str(count) if count is not None else "N/A"
        lines.append(f"| {repo_full} | {display} |")
    lines.append("")
    return "\n".join(lines)


def main():
    config = load_config()
    token = config.get("github_token") or os.environ.get("GITHUB_TOKEN", "")
    if not token:
        raise ValueError("No github_token in config.json and GITHUB_TOKEN env var not set.")

    now = datetime.now(timezone.utc)
    since = now - timedelta(hours=WINDOW_HOURS)
    since_iso = since.strftime("%Y-%m-%dT%H:%M:%SZ")

    repos = get_repos(config, token)
    if not repos:
        print("No repos configured. Check config.json.")
        return

    results = []
    for entry in repos:
        owner, repo = entry["owner"], entry["repo"]
        count = count_commits(owner, repo, since_iso, token)
        full = f"{owner}/{repo}"
        print(f"  {full}: {count if count is not None else 'N/A'}")
        if count is not None and count > 0 or config.get("include_zero_repos", False):
            results.append((full, count))

    # always include repos with commits; optionally all repos
    if not results:
        results = [(f"{e['owner']}/{e['repo']}", 0) for e in repos]

    report_block = build_report(results, since, now)

    os.makedirs(os.path.dirname(REPORT_FILE), exist_ok=True)
    write_header = not os.path.exists(REPORT_FILE)
    with open(REPORT_FILE, "a") as f:
        if write_header:
            f.write("# GitHub Commit Tracker\n\n")
        f.write(report_block + "\n")

    print(f"\nReport appended to {os.path.abspath(REPORT_FILE)}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Check GitHub commits in the last N hours and append to commit_activity.md."""

import os
import sys
import requests
from datetime import datetime, timezone, timedelta

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
ORG = "peak-flow"
HOURS = 6
OUTPUT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "commit_activity.md")

# Full known repo list — used as fallback when org API is unavailable
KNOWN_REPOS = [
    "playwright-deep-dive", "agent-system-mapper", "jana-laravel", "tasker",
    "centos7_ci3_apache_php56", "3dbuilder", "macbook_root_dir_backup",
    "advancedgravitycap", "newword", "meddxx-may-24", "skill-tree",
    "matrix-playground", "learn-tmux", "prompts", "peak-knowledge", "bous",
    "docker-db2", "vercel-first", "noter", "peak-ics", "dataking",
    "window-tab-manager", "VoiceDialogue-English", "peakflowness", "peak-bruno",
    "Websocketter", "Riptask", "spenderlive", "peak-threejs-playground",
    "brilliant_crm", "lovable-node-tree", "payva-clone", "claude-code-utils",
    "laravel_podcast_rss", "xamarin-edit", "codegenbase", "base-ai",
    "second-brain-mvp", "crincash", "claude-code-app", "nutrimain", "jlb",
    "laravel_basic_crud_generator", "vrlive2020z0121", "backend-tutorial",
    "dominion-dictionary", "peakflow-admin", "dave_test_local_start", "modernwrist",
    "clipview", "tyc2019", "twiliodom", "flowsync", "dom-jobs",
    "peak-terminal-codex", "nuthax", "peak-test-can-delete", "maker_forum",
    "chrome-tools", "disa-rewrites", "dom-connect01", "basephp",
    "desktop-tutorial", "VSHelloWorldApp", "wrist", "vrinner", "jarvis",
    "centos_laravel", "bocageeks", "wos-rallies", "dtr-beans",
    "flowsync-prototype", "claude-telemetry", "cornell", "udvuecrash",
    "virtual-coworkers", "idea-nexus", "temp-code-rabbit-test", "mac-sql-server-php",
    "myfirstelectron", "laradave2", "bblara", "cli-clone", "makerspace-forum",
    "linear-algebra-learn", "rack-planner", "sigcore", "game-plan", "blulara",
    "keyboard-shortcuts", "dom-virgo", "js-viz-ai-studio-google", "dave_test_start",
    "hellfire", "inadvancecalc", "jlara55", "learnedToday", "jana", "dom-tools",
    "gravagroup", "peaktrack",
]

HEADERS = {"Accept": "application/vnd.github+json"}
if GITHUB_TOKEN:
    HEADERS["Authorization"] = f"Bearer {GITHUB_TOKEN}"


def get(url, params=None):
    r = requests.get(url, headers=HEADERS, params=params, timeout=30)
    r.raise_for_status()
    return r.json()


def list_org_repos():
    repos, page = [], 1
    while True:
        batch = get(
            f"https://api.github.com/orgs/{ORG}/repos",
            params={"per_page": 100, "page": page, "sort": "pushed"},
        )
        if not batch:
            break
        repos.extend(r["name"] for r in batch)
        if len(batch) < 100:
            break
        page += 1
    return repos


def commits_since(repo, since_iso):
    results, page = [], 1
    while True:
        batch = get(
            f"https://api.github.com/repos/{ORG}/{repo}/commits",
            params={"since": since_iso, "per_page": 100, "page": page},
        )
        if not batch:
            break
        results.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return results


def ensure_header():
    if not os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "w") as f:
            f.write("# GitHub Commit Activity — peak-flow\n\n")
            f.write("Auto-generated every 6 hours by `check_commits.py`.\n\n")


def append_entry(now, since, rows):
    total = sum(r["count"] for r in rows)
    with open(OUTPUT_FILE, "a") as f:
        f.write(f"## {now.strftime('%Y-%m-%d %H:%M UTC')}\n\n")
        f.write(
            f"**Window:** {since.strftime('%Y-%m-%d %H:%M UTC')} → "
            f"{now.strftime('%Y-%m-%d %H:%M UTC')}\n\n"
        )
        if rows:
            f.write(f"**Total commits:** {total}\n\n")
            f.write("| Repository | Commits |\n")
            f.write("|---|---|\n")
            for r in sorted(rows, key=lambda x: -x["count"]):
                f.write(f"| `{ORG}/{r['repo']}` | {r['count']} |\n")
        else:
            f.write("_No commits in this window._\n")
        f.write("\n---\n\n")


def main():
    now = datetime.now(timezone.utc)
    since = now - timedelta(hours=HOURS)
    since_iso = since.strftime("%Y-%m-%dT%H:%M:%SZ")

    print(f"[{now.strftime('%Y-%m-%d %H:%M UTC')}] Checking commits since {since_iso}")

    # Try live org repo list; fall back to hardcoded list
    try:
        repo_names = list_org_repos()
        print(f"Found {len(repo_names)} repos via API.")
    except requests.HTTPError:
        repo_names = KNOWN_REPOS
        print(f"Org API unavailable — using {len(repo_names)} known repos.")

    rows = []
    for name in repo_names:
        try:
            commits = commits_since(name, since_iso)
            if commits:
                rows.append({"repo": name, "count": len(commits)})
                print(f"  {name}: {len(commits)}")
        except requests.HTTPError:
            pass  # private or deleted repo — skip silently

    ensure_header()
    append_entry(now, since, rows)

    total = sum(r["count"] for r in rows)
    print(f"Done. {total} commit(s) across {len(rows)} repo(s) → {OUTPUT_FILE}")


if __name__ == "__main__":
    main()

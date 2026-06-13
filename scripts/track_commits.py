"""
Fetch commits made in the last 6 hours across all repos in GH_ORG,
then append a summary block to commit-log.md.
"""

import os
import json
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta

TOKEN = os.environ["GH_TOKEN"]
ORG   = os.environ.get("GH_ORG", "peak-flow")
LOG   = "commit-log.md"
WINDOW_HOURS = 6


def gh_get(path: str) -> list | dict:
    url = f"https://api.github.com{path}"
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    })
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def list_repos() -> list[str]:
    repos, page = [], 1
    while True:
        batch = gh_get(f"/orgs/{ORG}/repos?per_page=100&page={page}")
        if not batch:
            break
        repos.extend(r["name"] for r in batch)
        if len(batch) < 100:
            break
        page += 1
    return repos


def count_commits_since(repo: str, since: str) -> list[dict]:
    try:
        commits = gh_get(
            f"/repos/{ORG}/{repo}/commits?since={since}&per_page=100"
        )
        return [
            {"sha": c["sha"][:7], "message": c["commit"]["message"].splitlines()[0]}
            for c in commits
        ]
    except urllib.error.HTTPError as exc:
        if exc.code in (404, 409):   # missing / empty repo
            return []
        raise


def ensure_log_header():
    if not os.path.exists(LOG):
        with open(LOG, "w") as f:
            f.write("# Commit Activity Log\n\n"
                    "Auto-generated every 6 hours by the Commit Tracker workflow.\n\n")


def append_entry(now: datetime, window_start: datetime, rows: list[dict]):
    total = sum(r["count"] for r in rows)
    lines = [
        f"## {now.strftime('%Y-%m-%d %H:%M UTC')} — last {WINDOW_HOURS} h\n",
        f"**Total commits:** {total}  \n",
        f"**Window:** {window_start.strftime('%Y-%m-%d %H:%M UTC')} → {now.strftime('%H:%M UTC')}\n\n",
    ]

    if rows:
        lines += [
            "| Repository | Commits | Recent messages |\n",
            "|---|---|---|\n",
        ]
        for r in rows:
            msgs = "; ".join(c["message"][:60] for c in r["commits"][:3])
            lines.append(f"| `{r['repo']}` | {r['count']} | {msgs} |\n")
    else:
        lines.append("_No commits found in this window._\n")

    lines.append("\n---\n\n")

    with open(LOG, "a") as f:
        f.writelines(lines)


def main():
    now          = datetime.now(timezone.utc)
    window_start = now - timedelta(hours=WINDOW_HOURS)
    since_iso    = window_start.strftime("%Y-%m-%dT%H:%M:%SZ")

    repos = list_repos()
    print(f"Scanning {len(repos)} repos since {since_iso} …")

    rows = []
    for repo in repos:
        commits = count_commits_since(repo, since_iso)
        if commits:
            rows.append({"repo": repo, "count": len(commits), "commits": commits})
            print(f"  {repo}: {len(commits)} commit(s)")

    rows.sort(key=lambda r: r["count"], reverse=True)

    ensure_log_header()
    append_entry(now, window_start, rows)
    print(f"Done. {sum(r['count'] for r in rows)} total commits logged to {LOG}.")


if __name__ == "__main__":
    main()

"""
Queries GitHub for commits made in the last 6 hours across all accessible
repos and appends a summary entry to COMMIT_LOG.md.

Requires:  GH_TOKEN env var (Personal Access Token with repo scope for
           cross-org access, or GITHUB_TOKEN for the current repo only).
"""

import os
import sys
from datetime import datetime, timezone, timedelta

import requests

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
TOKEN = os.environ.get("GH_TOKEN", "")
HOURS = 6
LOG_FILE = "COMMIT_LOG.md"
API = "https://api.github.com"

if not TOKEN:
    print("ERROR: GH_TOKEN is not set.", file=sys.stderr)
    sys.exit(1)

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def paginate(url: str, params: dict | None = None) -> list:
    """Fetch all pages from a GitHub list endpoint."""
    items = []
    params = dict(params or {})
    params.setdefault("per_page", 100)
    while url:
        r = requests.get(url, headers=HEADERS, params=params)
        r.raise_for_status()
        items.extend(r.json())
        url = r.links.get("next", {}).get("url")
        params = {}  # pagination cursor is already in the next URL
    return items


def get_accessible_repos() -> list[dict]:
    """Return repos the token has push/pull access to (user + org repos)."""
    repos = paginate(f"{API}/user/repos", {"affiliation": "owner,collaborator,organization_member"})
    return repos


def count_commits_since(repo_full_name: str, since: str) -> list[dict]:
    """Return commit summaries for a repo since the given ISO timestamp."""
    try:
        commits = paginate(
            f"{API}/repos/{repo_full_name}/commits",
            {"since": since},
        )
        return commits
    except requests.HTTPError as exc:
        if exc.response.status_code in (409, 404):
            # 409 = empty repo, 404 = no access
            return []
        raise


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

now = datetime.now(timezone.utc)
since_dt = now - timedelta(hours=HOURS)
since_iso = since_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
window_label = f"{since_dt.strftime('%Y-%m-%d %H:%M')} – {now.strftime('%Y-%m-%d %H:%M')} UTC"

print(f"Checking commits since {since_iso} …")

repos = get_accessible_repos()
print(f"Found {len(repos)} accessible repo(s).")

results: list[dict] = []
total_commits = 0

for repo in repos:
    name = repo["full_name"]
    commits = count_commits_since(name, since_iso)
    count = len(commits)
    total_commits += count
    if count > 0:
        results.append(
            {
                "repo": name,
                "count": count,
                "url": repo["html_url"],
                "commits": [
                    {
                        "sha": c["sha"][:7],
                        "message": c["commit"]["message"].splitlines()[0][:80],
                        "author": c["commit"]["author"]["name"],
                        "url": c["html_url"],
                    }
                    for c in commits
                ],
            }
        )

# ---------------------------------------------------------------------------
# Build markdown entry
# ---------------------------------------------------------------------------

lines = []
lines.append(f"## {now.strftime('%Y-%m-%d %H:%M UTC')}  —  last {HOURS} hours\n")
lines.append(f"**Window:** {window_label}  \n")
lines.append(f"**Total commits:** {total_commits}  \n")
lines.append(f"**Active repos:** {len(results)} / {len(repos)}\n")
lines.append("")

if results:
    lines.append("| Repo | Commits |")
    lines.append("|------|---------|")
    for r in sorted(results, key=lambda x: -x["count"]):
        lines.append(f"| [{r['repo']}]({r['url']}) | {r['count']} |")
    lines.append("")

    for r in sorted(results, key=lambda x: -x["count"]):
        lines.append(f"### [{r['repo']}]({r['url']})  ({r['count']} commit{'s' if r['count'] != 1 else ''})\n")
        for c in r["commits"]:
            lines.append(f"- [`{c['sha']}`]({c['url']}) {c['message']}  *(by {c['author']})*")
        lines.append("")
else:
    lines.append("_No commits in this window._\n")

lines.append("---\n")

new_entry = "\n".join(lines)

# ---------------------------------------------------------------------------
# Prepend to log file
# ---------------------------------------------------------------------------

existing = ""
if os.path.exists(LOG_FILE):
    with open(LOG_FILE, encoding="utf-8") as fh:
        raw = fh.read()
    # Strip the header if it exists so we can re-add it cleanly
    if raw.startswith("# Commit Log"):
        existing = raw[raw.index("\n") + 1:].lstrip("\n")
    else:
        existing = raw

header = "# Commit Log\n\n"
with open(LOG_FILE, "w", encoding="utf-8") as fh:
    fh.write(header + new_entry + existing)

print(f"✓ {LOG_FILE} updated — {total_commits} commit(s) across {len(results)} repo(s).")

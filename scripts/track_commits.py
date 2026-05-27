#!/usr/bin/env python3
"""
Checks all accessible GitHub repos for commits made in the last 6 hours
and saves a summary report to a markdown file.
"""
import os
import json
import urllib.request
import urllib.error
from datetime import datetime, timedelta, timezone


def github_get(path, token, params=None):
    url = f"https://api.github.com{path}"
    if params:
        query = "&".join(f"{k}={v}" for k, v in params.items())
        url = f"{url}?{query}"
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github.v3+json")
    req.add_header("User-Agent", "peaktrack-commit-tracker/1.0")
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read())
            link_header = resp.headers.get("Link", "")
            return data, link_header
    except urllib.error.HTTPError as e:
        print(f"  HTTP {e.code} for {url}: {e.reason}")
        return None, ""


def get_all_pages(path, token, params=None):
    params = dict(params or {})
    params.setdefault("per_page", "100")
    results = []
    page = 1
    while True:
        params["page"] = str(page)
        data, link = github_get(path, token, params)
        if not data:
            break
        results.extend(data if isinstance(data, list) else [data])
        if 'rel="next"' not in link:
            break
        page += 1
    return results


def count_commits_since(owner, repo, since_iso, token):
    data, _ = github_get(
        f"/repos/{owner}/{repo}/commits",
        token,
        {"since": since_iso, "per_page": "100"},
    )
    if data is None:
        return 0, []
    commits = []
    for c in data:
        msg = c.get("commit", {}).get("message", "").splitlines()[0][:80]
        author = (
            c.get("commit", {}).get("author", {}).get("name", "unknown")
        )
        sha = c.get("sha", "")[:7]
        commits.append({"sha": sha, "author": author, "message": msg})
    return len(commits), commits


def main():
    token = os.environ.get("GH_PAT") or os.environ.get("GITHUB_TOKEN")
    if not token:
        raise SystemExit("ERROR: Set GH_PAT or GITHUB_TOKEN environment variable")

    now = datetime.now(timezone.utc)
    since = now - timedelta(hours=6)
    since_iso = since.strftime("%Y-%m-%dT%H:%M:%SZ")
    report_time = now.strftime("%Y-%m-%d %H:%M UTC")
    file_date = now.strftime("%Y-%m-%d_%H-%M")

    print(f"Checking commits since {since_iso} ...")

    # Get authenticated user info
    user_data, _ = github_get("/user", token)
    username = user_data.get("login", "unknown") if user_data else "unknown"
    print(f"Authenticated as: {username}")

    # Fetch all repos the user has access to (own + org)
    repos = get_all_pages("/user/repos", token, {"affiliation": "owner,collaborator,organization_member", "sort": "pushed"})
    print(f"Found {len(repos)} repos to check")

    results = []
    total_commits = 0

    for repo in repos:
        full_name = repo.get("full_name", "")
        owner, name = full_name.split("/", 1)
        is_fork = repo.get("fork", False)
        pushed_at = repo.get("pushed_at", "")

        # Skip repos with no recent pushes (before the 6h window)
        if pushed_at and pushed_at < since_iso:
            continue

        count, commits = count_commits_since(owner, name, since_iso, token)
        if count > 0:
            print(f"  {full_name}: {count} commit(s)")
            results.append({
                "repo": full_name,
                "count": count,
                "commits": commits,
                "fork": is_fork,
                "url": repo.get("html_url", ""),
            })
            total_commits += count

    # Build markdown report
    lines = [
        f"# Commit Report — {report_time}",
        "",
        f"**Window:** Last 6 hours (since {since.strftime('%Y-%m-%d %H:%M UTC')})",
        f"**Total commits:** {total_commits}",
        f"**Repos with activity:** {len(results)}",
        "",
    ]

    if not results:
        lines.append("_No commits found in the last 6 hours._")
    else:
        lines.append("## Repositories")
        lines.append("")
        for r in sorted(results, key=lambda x: -x["count"]):
            fork_badge = " *(fork)*" if r["fork"] else ""
            lines.append(f"### [{r['repo']}]({r['url']}){fork_badge} — {r['count']} commit(s)")
            lines.append("")
            lines.append("| SHA | Author | Message |")
            lines.append("|-----|--------|---------|")
            for c in r["commits"][:20]:  # cap at 20 per repo
                msg = c["message"].replace("|", "\\|")
                lines.append(f"| `{c['sha']}` | {c['author']} | {msg} |")
            if len(r["commits"]) > 20:
                lines.append(f"| … | | *+{len(r['commits']) - 20} more* |")
            lines.append("")

    lines.append("---")
    lines.append(f"*Generated automatically by [peaktrack commit tracker](https://github.com/peak-flow/peaktrack)*")

    report_content = "\n".join(lines) + "\n"

    # Save timestamped report
    os.makedirs("commit-reports", exist_ok=True)
    timestamped_path = f"commit-reports/{file_date}.md"
    with open(timestamped_path, "w") as f:
        f.write(report_content)

    # Also overwrite the latest report
    with open("commit-reports/latest.md", "w") as f:
        f.write(report_content)

    print(f"Report saved to {timestamped_path} and commit-reports/latest.md")
    print(f"Summary: {total_commits} total commits across {len(results)} repo(s)")


if __name__ == "__main__":
    main()

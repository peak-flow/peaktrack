#!/usr/bin/env python3
"""
Check GitHub commits in the last 6 hours and save a Markdown report.

Environment variables:
  GITHUB_TOKEN   Personal access token with repo read scope (required)
  GITHUB_REPOS   Comma-separated list of "owner/repo" to monitor
                 e.g. "peak-flow/peaktrack,peak-flow/other-repo"
  GITHUB_ORG     Org name — scans all repos when GITHUB_REPOS is not set
                 e.g. "peak-flow"
  REPORT_DIR     Directory for report files (default: ./commit_reports)
  HOURS          Look-back window in hours (default: 6)
"""

import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path


def _api(token: str, path: str) -> list | dict:
    url = f"https://api.github.com{path}"
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def list_repos(token: str, repos_env: str | None, org_env: str | None) -> list[str]:
    if repos_env:
        return [r.strip() for r in repos_env.split(",") if r.strip()]
    if org_env:
        page, repos = 1, []
        while True:
            data = _api(token, f"/orgs/{org_env}/repos?per_page=100&page={page}")
            if not data:
                break
            repos.extend(f"{org_env}/{r['name']}" for r in data)
            if len(data) < 100:
                break
            page += 1
        return repos
    raise SystemExit(
        "Set GITHUB_REPOS (e.g. 'owner/repo,owner/repo2') "
        "or GITHUB_ORG (e.g. 'myorg') environment variable."
    )


def commits_since(token: str, repo: str, since_iso: str) -> list[dict]:
    try:
        data = _api(token, f"/repos/{repo}/commits?since={since_iso}&per_page=100")
        return data if isinstance(data, list) else []
    except urllib.error.HTTPError as exc:
        if exc.code in (404, 403, 451):
            return []
        raise


def build_report(
    since: datetime,
    now: datetime,
    results: list[tuple[str, list[dict]]],
    total: int,
) -> str:
    lines = [
        "# GitHub Commit Report",
        "",
        f"**Period:** {since.strftime('%Y-%m-%d %H:%M UTC')} → {now.strftime('%Y-%m-%d %H:%M UTC')}",
        f"**Total commits:** {total} across {len(results)} repo(s)",
        "",
    ]

    if not results:
        lines.append("_No commits found in this period._")
    else:
        for repo, cs in results:
            plural = "s" if len(cs) != 1 else ""
            lines += [f"## `{repo}` — {len(cs)} commit{plural}", ""]
            for c in cs:
                sha = c["sha"][:7]
                message = c["commit"]["message"].split("\n")[0][:120]
                author = c["commit"]["author"]["name"]
                date = c["commit"]["author"]["date"]
                lines.append(f"- `{sha}` {message}  _{author}_ · {date}")
            lines.append("")

    return "\n".join(lines)


def main() -> None:
    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        raise SystemExit("GITHUB_TOKEN environment variable is required.")

    repos_env = os.environ.get("GITHUB_REPOS")
    org_env = os.environ.get("GITHUB_ORG")
    report_dir = Path(os.environ.get("REPORT_DIR", "./commit_reports"))
    hours = int(os.environ.get("HOURS", "6"))

    report_dir.mkdir(parents=True, exist_ok=True)

    now = datetime.now(timezone.utc)
    since = now - timedelta(hours=hours)
    since_iso = since.strftime("%Y-%m-%dT%H:%M:%SZ")

    repos = list_repos(token, repos_env, org_env)
    print(f"Checking {len(repos)} repo(s) for commits since {since_iso} ...")

    results: list[tuple[str, list[dict]]] = []
    total = 0
    for repo in repos:
        cs = commits_since(token, repo, since_iso)
        print(f"  {repo}: {len(cs)} commit(s)")
        if cs:
            results.append((repo, cs))
            total += len(cs)

    report = build_report(since, now, results, total)

    # Timestamped snapshot
    snapshot = report_dir / f"commits_{now.strftime('%Y-%m-%d_%H-%M')}.md"
    snapshot.write_text(report, encoding="utf-8")

    # Always-current file (easy to read the latest without hunting filenames)
    latest = report_dir / "latest.md"
    latest.write_text(report, encoding="utf-8")

    # Append a one-liner to the running log
    log = report_dir / "history.md"
    entry = (
        f"| {now.strftime('%Y-%m-%d %H:%M UTC')} "
        f"| {total} commits | {len(results)} repo(s) "
        f"| [{snapshot.name}]({snapshot.name}) |\n"
    )
    if not log.exists():
        log.write_text(
            "# Commit History Log\n\n"
            "| Checked at (UTC) | Commits | Repos with activity | Report |\n"
            "|---|---|---|---|\n",
            encoding="utf-8",
        )
    with log.open("a", encoding="utf-8") as f:
        f.write(entry)

    print(f"\nSaved: {snapshot}")
    print(f"Latest: {latest}")
    print(f"Log:    {log}")
    print(f"\nTotal: {total} commit(s) across {len(results)} repo(s)")


if __name__ == "__main__":
    main()

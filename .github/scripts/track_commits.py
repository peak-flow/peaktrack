import os
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

ORG = os.environ.get('ORG', 'peak-flow')
REPORT_FILE = Path('commit-activity.md')

HEADER = """\
# Commit Activity Log

Automatically updated every 6 hours. Each entry covers the preceding 6-hour window.

"""


def run_gh(*args):
    result = subprocess.run(['gh'] + list(args), capture_output=True, text=True)
    return result.stdout.strip() if result.returncode == 0 else None


def list_repos(org):
    out = run_gh('repo', 'list', org, '--limit', '1000', '--json', 'name', '--jq', '.[].name')
    if not out:
        return []
    return [n for n in out.split('\n') if n]


def count_commits(org, repo, since):
    page, total = 1, 0
    while True:
        out = run_gh('api',
                     f'repos/{org}/{repo}/commits',
                     '-f', f'since={since}',
                     '-f', 'per_page=100',
                     '-f', f'page={page}',
                     '--jq', 'length')
        try:
            n = int(out or '0')
        except ValueError:
            break
        total += n
        if n < 100:
            break
        page += 1
    return total


now = datetime.now(timezone.utc)
since = (now - timedelta(hours=6)).strftime('%Y-%m-%dT%H:%M:%SZ')
now_str = now.strftime('%Y-%m-%d %H:%M UTC')

repos = list_repos(ORG)
rows, total_commits = [], 0

for repo in repos:
    count = count_commits(ORG, repo, since)
    if count > 0:
        rows.append((repo, count))
        total_commits += count

# Build entry
noun = lambda n, word: f'{n} {word}{"s" if n != 1 else ""}'
lines = [f'## {now_str}', '']
lines.append(f'Checked {noun(len(repos), "repository")} in `{ORG}`.')
lines.append('')

if rows:
    lines += ['| Repository | Commits |', '|---|---:|']
    for repo, count in sorted(rows, key=lambda x: -x[1]):
        lines.append(f'| [`{ORG}/{repo}`](https://github.com/{ORG}/{repo}) | {count} |')
    lines += [
        '',
        f'**Total:** {noun(total_commits, "commit")} across {noun(len(rows), "repository")}',
    ]
else:
    lines.append('*No commits in the last 6 hours.*')

lines += ['', '---', '']
new_entry = '\n'.join(lines) + '\n'

existing = REPORT_FILE.read_text() if REPORT_FILE.exists() else HEADER
body = existing[len(HEADER):] if existing.startswith(HEADER) else existing
REPORT_FILE.write_text(HEADER + new_entry + body)

print(f'Done: {noun(total_commits, "commit")} across {len(rows)}/{len(repos)} repos')

# PeakTrack — GitHub Commit Tracker

Checks GitHub every 6 hours for new commits and saves Markdown reports to `commit_reports/`.

## Quick start

```bash
export GITHUB_TOKEN=ghp_your_personal_access_token

# Monitor a specific set of repos:
export GITHUB_REPOS="peak-flow/peaktrack,peak-flow/other-repo"

# OR monitor every repo in an org:
export GITHUB_ORG="peak-flow"

python3 scripts/check_commits.py
```

Reports are written to:
| File | Contents |
|---|---|
| `commit_reports/commits_YYYY-MM-DD_HH-MM.md` | Snapshot for that run |
| `commit_reports/latest.md` | Overwritten each run (always current) |
| `commit_reports/history.md` | One-liner log of every run |

## Configuration

All config is via environment variables:

| Variable | Required | Default | Description |
|---|---|---|---|
| `GITHUB_TOKEN` | Yes | — | PAT with `repo` read scope |
| `GITHUB_REPOS` | One of these | — | Comma-separated `owner/repo` list |
| `GITHUB_ORG` | One of these | — | Org name — scans all repos |
| `REPORT_DIR` | No | `./commit_reports` | Output directory |
| `HOURS` | No | `6` | Look-back window in hours |

## Running every 6 hours

### Option A — systemd timer (recommended on Linux with a login session)

```bash
# Edit the service file to add your GITHUB_TOKEN:
nano ~/.config/systemd/user/github-commit-check.service

# Then enable:
systemctl --user daemon-reload
systemctl --user enable --now github-commit-check.timer
systemctl --user list-timers github-commit-check.timer
```

The `.service` and `.timer` unit files are in `~/.config/systemd/user/`.

### Option B — tmux / screen background loop

```bash
# Inside a tmux pane or screen session:
GITHUB_TOKEN=... GITHUB_ORG=peak-flow python3 scripts/run_loop.py

# Or detached with nohup:
GITHUB_TOKEN=... GITHUB_ORG=peak-flow nohup python3 scripts/run_loop.py &
```

### Option C — cron (if crontab is available)

```bash
crontab -e
```

Add:
```
0 */6 * * * GITHUB_TOKEN=ghp_xxx GITHUB_ORG=peak-flow /home/user/peaktrack/scripts/run_commit_check.sh >> /home/user/peaktrack/commit_reports/cron.log 2>&1
```

## Files

```
scripts/
  check_commits.py       # Core script — run directly or via wrappers
  run_commit_check.sh    # Shell wrapper (edit to set env vars)
  run_loop.py            # Infinite loop runner for tmux/nohup use
commit_reports/
  latest.md              # Latest report (overwritten each run)
  history.md             # Cumulative one-liner log
  commits_YYYY-MM-DD_HH-MM.md  # Per-run snapshots
~/.config/systemd/user/
  github-commit-check.service
  github-commit-check.timer
```

# PeakTrack — GitHub Commit Logger

Checks one or more GitHub repos every 6 hours, counts new commits, and appends a summary to `commit_log.md`.

## Setup

### 1. Configure repos and token

```bash
cp .env.example .env
```

Edit `.env`:
```
GITHUB_TOKEN=ghp_your_token_here
GITHUB_REPOS=peak-flow/peaktrack,other-owner/other-repo
CHECK_HOURS=6
```

> Your token needs the **repo** (read) scope. Create one at  
> GitHub → Settings → Developer settings → Personal access tokens.

### 2. Run once to test

```bash
./run_check.sh
```

This creates / appends to `commit_log.md`.

### 3. Schedule it to run every 6 hours

**Option A — cron (recommended on most Linux/macOS systems)**

```bash
crontab -e
# Add this line:
0 */6 * * * /home/user/peaktrack/run_check.sh >> /home/user/peaktrack/cron.log 2>&1
```

**Option B — background Python loop (no cron needed)**

```bash
nohup python3 run_background.py &
# View logs:  tail -f nohup.out
# Stop:       kill $(cat .runner.pid)
```

## Output

Each run appends a section to `commit_log.md`, e.g.:

```
## 2026-04-21 12:00 UTC

**Period:** last 6 hours  |  **Total commits:** 3

### `peak-flow/peaktrack` — 3 commit(s)
- `a1b2c3d` Fix null pointer in dashboard (by Alice)
- `d4e5f6a` Add retry logic to API client (by Bob)
- `7890abc` Update README (by Alice)
```

## Files

| File | Purpose |
|---|---|
| `check_commits.py` | Main script — fetches commits via GitHub REST API |
| `run_check.sh` | Shell wrapper that loads `.env` before running the script |
| `run_background.py` | Persistent loop runner (alternative to cron) |
| `.env.example` | Token/repo config template |
| `commit_log.md` | Auto-generated output (created on first run) |

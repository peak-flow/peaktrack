# PeakTrack

## Commit Activity Tracker

A GitHub Actions workflow that runs every 6 hours, counts commits across configured repos, and appends results to [`commit-log.md`](./commit-log.md).

### How it works

| Step | Detail |
|------|--------|
| Schedule | Every 6 hours (00:00, 06:00, 12:00, 18:00 UTC) |
| Looks back | 6 hours from run time |
| Output | `commit-log.md` — newest entries at the top |

### Adding repos to track

Edit the `TRACKED_REPOS` env var at the top of [`.github/workflows/commit-tracker.yml`](.github/workflows/commit-tracker.yml):

```yaml
env:
  TRACKED_REPOS: |
    peak-flow/peaktrack
    your-org/another-repo
    your-username/some-repo
```

> **Cross-repo access:** The default `GITHUB_TOKEN` only covers this repo.
> To track repos outside `peak-flow/peaktrack`, create a GitHub Personal Access Token
> with `repo` scope and save it as a repository secret named **`COMMIT_TRACKER_TOKEN`**.

### Manual trigger

Go to **Actions → Commit Tracker → Run workflow** and optionally set a custom look-back window (in hours).

### Output format

```markdown
## 2026-06-07 12:00 UTC

> **Window:** 2026-06-07 06:00 UTC → 2026-06-07 12:00 UTC

| Repository           | Commits |
|----------------------|--------:|
| `peak-flow/peaktrack` |       4 |

**Total:** 4 commit(s) across 1 active repo(s)
```

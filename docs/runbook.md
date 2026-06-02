# TickerTruth Operational Runbook

## 1. Prerequisites

### Required software

| Tool | Install | Version check |
|---|---|---|
| Python 3.12+ | `brew install python@3.12` | `python3 --version` |
| Dolt | `brew install dolt` | `dolt version` |
| Playwright Chromium | `playwright install chromium` | `playwright --version` |

### Environment variables (`.env` in project root)

```bash
# Cloudflare R2 (optional — only for artifact uploads)
R2_BUCKET=tickertruth-releases
R2_ENDPOINT=https://<account-id>.r2.cloudflarestorage.com
R2_ACCESS_KEY_ID=<key>
R2_SECRET_ACCESS_KEY=<secret>
```

Copy `.env.example` to `.env` and fill in values before running uploads.

### First-time Dolt setup

```bash
cd dolt/
dolt config --global --add user.name  "Your Name"
dolt config --global --add user.email "you@example.com"
dolt sql < schema.sql          # create tables (only on fresh clone)
dolt sql < seed_corporate_actions.sql  # seed dim_corporate_action_type
dolt add --all
dolt commit -m "Initial schema"
```

---

## 2. Manual Refresh Procedure

Run this sequence after any trading day to ingest new data.

### Step 1 — Activate virtualenv

```bash
cd /path/to/TickerTruth
source .venv/bin/activate
```

### Step 2 — Full pipeline run (recommended)

```bash
python pipelines/run.py --date $(date +%Y-%m-%d)
```

This runs: extract → normalize → lineage → adjust → validate → load → export → manifest → release-notes.

### Step 3 — Partial run (individual tasks)

```bash
# Skip download, use existing raw files
python pipelines/run.py --no-fetch --tasks normalize,lineage,adjust,validate

# Only generate exports (curated data must already exist)
python pipelines/run.py --tasks export,manifest,release-notes

# Dry run — everything except Dolt commit and R2 upload
python pipelines/run.py --dry-run
```

### Step 4 — Verify outputs

```bash
# Run QA checks against curated files
python pipelines/phase3_validator.py   # or:
python -m pytest pipelines/ -q

# Check Dolt history
cd dolt && dolt log --oneline | head -5

# Check curated file sizes
ls -lh data/curated/*.csv data/curated/*.parquet 2>/dev/null
```

### Step 5 — Tag and release

```bash
# Tag a release (triggers release.yml workflow if pushed)
git tag v$(date +%Y.%m.%d)
git push origin v$(date +%Y.%m.%d)

# Or run the export + manifest manually without GitHub Actions:
python pipelines/run.py --no-fetch --no-dolt-commit \
  --tasks export,manifest,release-notes
```

---

## 3. Troubleshooting

### Dolt issues

**Problem:** `dolt sql` fails with "unknown command"
```bash
# Verify Dolt binary is installed and on PATH
which dolt
dolt version
# If missing: brew install dolt
```

**Problem:** `dolt commit` fails with "nothing to commit"
- This is non-fatal; the pipeline logs a warning and continues.
- Check `dolt status` — if working tree is clean, data is already committed.

**Problem:** Dolt import fails with FK violation
```bash
cd dolt
dolt sql -q "SELECT COUNT(*) FROM dim_security_master"
# If 0: normalize pipeline did not run or curated files are missing
# Fix: run normalize first, then retry load
```

**Problem:** Rollback needed after bad import
```bash
cd dolt
dolt log --oneline          # find the last good commit hash
dolt reset --hard <hash>    # hard reset to that commit
# WARNING: this discards all uncommitted data changes
```

### NSE extraction issues

**Problem:** `fetch_nse_symbols` returns 0 rows or raises `RuntimeError`
- NSE may have changed their URL or added CAPTCHA protection.
- Check `sources.yaml` for the current URL.
- Test manually: `curl -A "Mozilla/5.0" https://www.nseindia.com/api/equity-master`
- If blocked, add a VPN or rotate user-agent in `_BROWSER_HEADERS`.

**Problem:** Playwright timeout on corporate actions page
```bash
# Test page access manually:
playwright open https://www.nseindia.com/companies-listing/corporate-filings-actions
# If CAPTCHA: NSE is blocking headless browsers. Use manual download.
```

**Problem:** Bhavcopy download returns 404
- NSE publishes bhavcopy after market close (~6 PM IST).
- Holidays and weekends have no bhavcopy file.
- Check the date: `python -c "from datetime import date; print(date.today().weekday())"` (0=Mon, 6=Sun)

### Quality validation failures

**Problem:** `check_referential_integrity` fails — orphan fact rows
```bash
python -c "
import pandas as pd
master = set(pd.read_csv('data/curated/dim_security_master.csv')['security_id'])
facts  = pd.read_csv('data/curated/fact_corporate_action_event.csv')
orphans = facts[~facts['security_id'].isin(master)]
print(orphans[['security_id', 'action_code', 'event_date']].head(10))
"
# Root cause: normalization JOIN failed for some symbols
# Fix: check if those symbols exist in nse_symbols_consolidated.csv
```

**Problem:** `check_confidence_scores` warns > 20% low-confidence rows
- Indicates high rate of normalization failures or unknown action types.
- Check `_quality_issues` column in `fact_corporate_action_event.csv`.
- Common causes: new NSE action types not in `_ACTION_TYPE_MAP` (normalizers.py).
- Fix: add new mappings to `_ACTION_TYPE_MAP` and re-run normalize.

---

## 4. Monitoring

### Key metrics to check after each run

| Metric | Expected | How to check |
|---|---|---|
| dim_security_master rows | ≥ 3,500 | `wc -l data/curated/dim_security_master.csv` |
| fact_corporate_action_event rows | > 0 | `wc -l data/curated/fact_corporate_action_event.csv` |
| Low-confidence action rows | < 20% | `python pipelines/run.py --tasks validate` |
| Dolt commit created | 1 new commit | `cd dolt && dolt log --oneline -n 1` |
| Public sample file sizes | > 1 KB | `ls -lh data/samples/public/` |

### GitHub Actions monitoring

- CI runs on every push to `main` and pull request: check **Actions** tab.
- Nightly refresh runs at 8:30 PM UTC Mon–Fri: check the latest **Nightly Data Refresh** run.
- If the nightly run fails, GitHub sends an email to the repository owner.

### Manual health check script

```bash
# Quick health check — exits 0 if all curated files look correct
python pipelines/run.py --no-fetch --no-dolt-commit --tasks validate
echo "Exit code: $?"
```

---

## 5. Failure Recovery

### Nightly pipeline fails mid-run

1. Check the GitHub Actions run log for which task failed.
2. Fix the root cause (bad data, NSE URL change, etc.).
3. Re-run only the failed task:
   ```bash
   python pipelines/run.py --no-fetch --tasks normalize,validate,load
   ```
4. If Dolt state is inconsistent, rollback and retry:
   ```bash
   cd dolt && dolt log --oneline | head -3
   dolt reset --hard <last-good-hash>
   # Then re-run load
   python pipelines/run.py --no-fetch --tasks load
   ```

### Curated files corrupted or missing

```bash
# Re-run the full normalization from staging (no network needed)
python pipelines/run.py --no-fetch --tasks normalize,lineage,adjust
```

If staging files are also missing:
```bash
# Re-run from raw files
python pipelines/run.py --no-fetch --tasks normalize,lineage,adjust
# If raw files are missing too — run full pipeline with extraction
python pipelines/run.py --date <YYYY-MM-DD>
```

### R2 upload fails

- R2 credentials are stored as GitHub repository secrets (`R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, etc.).
- Verify secrets are set: **GitHub → Repository → Settings → Secrets**.
- Test R2 access locally:
  ```bash
  pip install boto3
  python -c "
  import boto3, os
  s3 = boto3.client('s3', endpoint_url=os.environ['R2_ENDPOINT'],
                    aws_access_key_id=os.environ['R2_ACCESS_KEY_ID'],
                    aws_secret_access_key=os.environ['R2_SECRET_ACCESS_KEY'])
  print(s3.list_buckets())
  "
  ```
- If upload fails after 3 retries in the workflow, download the artifacts from the GitHub Actions run and upload manually using the script above.

---

## 6. Release Checklist

Before tagging a monthly release:

- [ ] Nightly pipeline completed without failures in the last 3 days
- [ ] `python pipelines/run.py --tasks validate` exits 0
- [ ] `cd dolt && dolt log --oneline | head -3` shows recent commits
- [ ] Public sample files in `data/samples/public/` look correct (non-zero rows)
- [ ] Release notes drafted in `releases/monthly/`
- [ ] Changelog updated in `docs/release-notes.md`

Tag and push:
```bash
git tag v$(date +%Y.%m.%d)
git push origin v$(date +%Y.%m.%d)
```
